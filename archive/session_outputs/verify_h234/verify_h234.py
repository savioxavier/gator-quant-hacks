"""Independent verification of the local H2/H3/H4 replication run (backtest_h234_local).

Written from the pre-registration text (sections 3.5, 6.1-6.4) and the run's frozen tables, without importing the
stage code (lib.py, h234_lib.py, h234_s*.py). Market data are read in memory only; nothing written here holds a price
level (only ticks, log returns in bp, statistics, counts, hashes and timestamps).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sps

SCR = Path(__file__).resolve().parent.parent
REPO = SCR / "team_push"
BT = REPO / "backtests" / "presser"
RUN = BT / "backtest_h234_local"
MKT = Path("<home>/.cache/gqh/presser")
OUTD = Path(__file__).resolve().parent / "out"
OUTD.mkdir(parents=True, exist_ok=True)

SEED, NB = 20261003, 9999
WEBB = np.array([-math.sqrt(1.5), -1.0, -math.sqrt(0.5), math.sqrt(0.5), 1.0, math.sqrt(1.5)])
REL_TOL = 1e-6
PRIMARY = "primary_2023_2026"
TRAIN = "additional_2018_2022"
TZ = "America/New_York"

report: dict = {"checks": [], "mismatches": []}


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(a, b):
    a, b = float(a), float(b)
    if a == b:
        return 0.0
    return abs(a - b) / max(abs(a), abs(b), 1e-300)


def cmp(name, mine, theirs, tol=REL_TOL):
    r = rel(mine, theirs) if (theirs is not None and np.isfinite(float(theirs))) else float("nan")
    ok = bool(np.isfinite(r) and r <= tol)
    report["checks"].append(dict(name=name, mine=float(mine), run=None if theirs is None else float(theirs),
                                 rel_diff=r, ok=ok))
    if not ok:
        report["mismatches"].append(name)
    return ok


def flag(name, ok, detail=None):
    report["checks"].append(dict(name=name, ok=bool(ok), detail=detail))
    if not ok:
        report["mismatches"].append(name)


def mtime(p: Path) -> str:
    return datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat(timespec="microseconds")


# ======================================================================== inputs
feat = pd.read_parquet(RUN / "features" / "answers_h234.parquet")
mfeat = pd.read_parquet(RUN / "features" / "meetings_h234.parquet")
chunks = pd.read_parquet(RUN / "features" / "voice_chunks_assigned.parquet")
sel2 = pd.read_csv(RUN / "positions" / "answer_sel_H2_h1.csv", dtype={"date": str, "answer_id": str})
sel3 = pd.read_csv(RUN / "positions" / "answer_sel_H3_h1.csv", dtype={"date": str, "answer_id": str})
sel4 = pd.read_csv(RUN / "positions" / "answer_sel_H4_h1.csv", dtype={"date": str, "answer_id": str})
fit = json.loads((RUN / "h4_fit" / "fit.json").read_text())
fam = json.loads((RUN / "results" / "family_holm.json").read_text())
h4res = json.loads((RUN / "results" / "h4_results.json").read_text())
asum = pd.read_csv(RUN / "results" / "answer_summary.csv", low_memory=False)
h1pos = pd.read_csv(BT / "backtest" / "positions" / "answers_positions.csv", dtype={"date": str, "answer_id": str})

for s in (sel2, sel3, sel4):
    s["t0_utc"] = pd.to_datetime(s.t0, utc=True, format="ISO8601")

# ---- 1m bars, my own lookup (bar start ts_event, UTC)
bars = pd.read_parquet(MKT / "ohlcv-1m__all_2016_2026.parquet", columns=["ts_event", "open", "close", "symbol"])
bars["root"] = bars.symbol.str.slice(0, 2)
bars["d_et"] = bars.ts_event.dt.tz_convert(TZ).dt.date.astype(str)
BAR = {}
for (d, r), g in bars.groupby(["d_et", "root"]):
    g = g.sort_values("ts_event")
    BAR[(d, r)] = (g.ts_event.dt.as_unit("ns").astype("int64").to_numpy(), g.open.to_numpy(), g.close.to_numpy())
MIN_NS = 60 * 10 ** 9


def fill(date, root, t0_utc, h):
    """Entry: open of the first bar starting at or after t0. Exit: close of the last bar starting no later than
    entry + (h - 1) min (the bar ending at entry + h min), and not before the entry bar."""
    k = (date, root)
    if k not in BAR:
        return None
    ts, op, cl = BAR[k]
    t = pd.Timestamp(t0_utc).value
    i = int(np.searchsorted(ts, t, side="left"))
    if i >= len(ts):
        return None
    e_ts = ts[i]
    j = int(np.searchsorted(ts, e_ts + (h - 1) * MIN_NS, side="right")) - 1
    if j < i:
        return None
    return e_ts, op[i], ts[j], cl[j]


def zt_tick(date):
    return 1 / 128 if date <= "2018-12-31" else 1 / 256


# ======================================================================== statistics (written independently)
def cr1_mean(y, g):
    """Mean and CR1 cluster SE of an intercept-only OLS, via the sandwich (X'X)^-1 X'uu'X (X'X)^-1 * G/(G-1)*(n-1)/(n-k)."""
    y = np.asarray(y, float)
    g = np.asarray(g)
    n = len(y)
    m = y.sum() / n
    u = y - m
    clusters = sorted(set(g.tolist()))
    G = len(clusters)
    meat = sum((u[g == c].sum()) ** 2 for c in clusters)
    var = (G / (G - 1)) * ((n - 1) / (n - 1)) * meat / n ** 2
    return m, math.sqrt(var), G


def wild_p(y, g, seed=SEED, draws=NB, centre=False):
    """Webb wild cluster bootstrap of the mean's CR1 t. Null imposed: y* = w_g * y (centre=False, as prereg 6.3)
    or y* = w_g * (y - mean) (centre=True, as the CW mean(f) bootstrap of 6.4). Weight matrix drawn as
    rng.choice(WEBB, size=(draws, G)) with clusters in sorted order. Returns (t, p_two, p_upper)."""
    y = np.asarray(y, float)
    g = np.asarray(g)
    clusters = sorted(set(g.tolist()))
    G = len(clusters)
    gi = np.array([clusters.index(c) for c in g])
    m, se, _ = cr1_mean(y, g)
    t = m / se
    base = y - m if centre else y
    rng = np.random.default_rng(seed)
    W = rng.choice(WEBB, size=(draws, G))
    n = len(y)
    tst = np.empty(draws)
    for b in range(draws):
        ys = W[b, gi] * base
        mb = ys.mean()
        S = np.bincount(gi, weights=ys - mb, minlength=G)
        tst[b] = mb / math.sqrt((G / (G - 1)) * (S ** 2).sum() / n ** 2)
    return t, (1 + np.sum(np.abs(tst) >= abs(t))) / (draws + 1), (1 + np.sum(tst >= t)) / (draws + 1)


# ======================================================================== A. positions re-derived from features
fz = feat.set_index("answer_id")
RT = {k: pd.read_csv(RUN / "positions" / f"answer_sel_{k}_h1.csv", dtype={"date": str, "answer_id": str},
                     float_precision="round_trip") for k in ["H2", "H3", "H4"]}
dev = {}
for k, s_, col in [("H2", sel2, "zA"), ("H3", sel3, "U"), ("H4", sel4, "zA"), ("H4", sel4, "U")]:
    a_ = fz.loc[s_.answer_id, col].to_numpy(float)
    dev[f"{k}.{col}"] = float(np.nanmax(np.abs(a_ - s_[col].to_numpy(float)) / np.maximum(np.abs(a_), 1e-300)))
report["csv_default_parser_max_rel_dev"] = dev
for name, s, col in [("H2", sel2, "zA"), ("H3", sel3, "U")]:
    fv = fz.loc[s.answer_id, col].to_numpy(float)
    flag(f"{name}: feature {col} in the selection table equals answers_h234.parquet (exact, round-trip parse)",
         np.array_equal(fv, RT[name][col].to_numpy(float)))
    pos = np.sign(fv)                                  # prereg 6.2: ZT long when feature > 0
    flag(f"{name}: ZT position = +sign({col}) for all {len(s)} selected answers",
         np.array_equal(pos, s[f"{name}__pos_ZT"].to_numpy(float)))
for col in ["zA", "U"]:
    flag(f"H4: {col} in answer_sel_H4_h1 equals the feature table (exact, round-trip parse)",
         np.array_equal(fz.loc[sel4.answer_id, col].to_numpy(float), RT["H4"][col].to_numpy(float)))
h1r = h1pos.set_index("answer_id")
flag("H4: s_tilde equals the frozen H1 H1__resid (exact)",
     np.array_equal(h1r.loc[sel4.answer_id, "H1__resid"].to_numpy(float), sel4.s_tilde.to_numpy(float)))

# selection re-derived from the frozen H1 table + features (prereg 6.1: eligible, feature present, latest per entry
# bar, earliest-first non-overlap)
h1pos["t0_utc"] = pd.to_datetime(h1pos.t0, utc=True, format="ISO8601")
base = h1pos[(h1pos.chair == "Powell") & h1pos.H1__eligible.astype(bool)].copy()
base = base.merge(feat[["answer_id", "zA", "U"]], on="answer_id", how="left")


def my_select(df, h):
    out = []
    for _, g in df.groupby("meeting"):
        g = g.sort_values(["t0_utc", "answer_no"])
        g = g.drop_duplicates("t0_utc", keep="last")
        last = None
        for aid, t in zip(g.answer_id, g.t0_utc):
            if last is None or (t - last) >= pd.Timedelta(minutes=h):
                out.append(aid)
                last = t
    return set(out)


for name, s, need in [("H2", sel2, ["zA"]), ("H3", sel3, ["U"])]:
    el = base[np.isfinite(base[need].astype(float)).all(1)]
    flag(f"{name}: selection re-derived (h=1) equals answer_sel_{name}_h1 ({len(s)} answers)",
         my_select(el, 1) == set(s.answer_id))
el4 = base[np.isfinite(base[["zA", "U"]].astype(float)).all(1) & np.isfinite(base.H1__resid.astype(float))]
flag(f"H4: selection re-derived equals answer_sel_H4_h1 ({len(sel4)} answers)", my_select(el4, 1) == set(sel4.answer_id))

# ======================================================================== B. H2 primary (and H3 numbers) recomputed
trades_run = pd.read_csv(RUN / "results" / "answer_trades.csv", low_memory=False)
gross = {}
for name, s in [("H2", sel2), ("H3", sel3)]:
    p = s[s["sample"] == PRIMARY].copy()
    out = []
    for r in p.itertuples():
        f = fill(r.date, "ZT", r.t0_utc, 1)
        pos = getattr(r, f"{name}__pos_ZT")
        if f is None or pos == 0 or not np.isfinite(pos):
            continue
        e_ts, e_px, x_ts, x_px = f
        out.append(dict(answer_id=r.answer_id, meeting=r.meeting, date=r.date, pos=pos,
                        ticks=pos * (x_px - e_px) / zt_tick(r.date), e_ts=e_ts, x_ts=x_ts, e_px=e_px, x_px=x_px))
    d = pd.DataFrame(out)
    m, se, G = cr1_mean(d.ticks, d.meeting)
    t, p2, _ = wild_p(d.ticks.to_numpy(), d.meeting.to_numpy())
    _, p2_alt, _ = wild_p(d.ticks.to_numpy(), d.meeting.to_numpy(), seed=1, draws=99999)
    row = asum[(asum.key == name) & (asum.h == 1) & (asum.sym == "ZT") & (asum.variant == "base") &
               (asum["sample"] == PRIMARY) & (asum.cost == "C0")].iloc[0]
    cmp(f"{name} primary n answers", len(d), row.n_answers)
    cmp(f"{name} primary n meetings", G, row.n_meetings)
    cmp(f"{name} primary mean gross ticks (ZT, +1 min)", m, row["mean"])
    cmp(f"{name} primary CR1 SE", se, row.se_cr1)
    cmp(f"{name} primary CR1 t", t, row.t_cr1)
    cmp(f"{name} primary wild-cluster p two-sided (seed {SEED}, 9,999 draws)", p2, row.wcb_p_two)
    report[f"{name}_primary"] = dict(n=len(d), meetings=G, mean_ticks=m, sum_ticks=float(d.ticks.sum()),
                                     mean_usd=m * 2000 / 256, se_cr1=se, t_cr1=t, wcb_p_two=p2,
                                     wcb_p_two_other_seed_99999_draws=p2_alt,
                                     run=dict(mean=row["mean"], t=row.t_cr1, p=row.wcb_p_two))
    if name == "H2":
        cmp("H2 Holm input p_raw = recomputed p", p2, fam["H2"]["p_raw"])
        cmp("H2 family mean_ticks = recomputed mean", m, fam["H2"]["mean_ticks"])
    # per-trade comparison with the run's trade log (prices compared in memory only, never written)
    tr = trades_run[(trades_run.key == name) & (trades_run.h == 1) & (trades_run.sym == "ZT") &
                    (trades_run.variant == "base") & (trades_run["sample"] == PRIMARY)].copy()
    tr["answer_id"] = tr.answer_id.astype(str)
    mm = d.merge(tr[["answer_id", "entry_px", "exit_px", "C0_ticks", "pos"]], on="answer_id", how="outer",
                 suffixes=("", "_run"), indicator=True)
    flag(f"{name}: same trade set as the run's trade log ({len(d)} vs {len(tr)})", (mm._merge == "both").all())
    both = mm[mm._merge == "both"]
    flag(f"{name}: per-trade entry/exit prices, position and gross ticks equal the run's trade log",
         bool(np.allclose(both.e_px, both.entry_px, rtol=0, atol=1e-12) and
              np.allclose(both.x_px, both.exit_px, rtol=0, atol=1e-12) and
              np.array_equal(both.pos.to_numpy(float), both.pos_run.to_numpy(float)) and
              np.allclose(both.ticks, both.C0_ticks, rtol=1e-9, atol=1e-9)))
    gross[name] = d

# ======================================================================== C. H4: training refit + Clark-West
rows = []
for r in sel4.itertuples():
    f = fill(r.date, "ZT", r.t0_utc, 1)
    if f is None:
        rows.append(np.nan)
        continue
    rows.append(1e4 * math.log(f[3] / f[1]))
sel4["y"] = rows
FA = ["s_tilde", "zA", "U"]
d4 = sel4.dropna(subset=["y"] + FA).copy()
trn = d4[d4["sample"] == TRAIN]
fz_ = fit["fits"]["answer_ZT"]
cmp("H4 training n answers", len(trn), fz_["n"])
cmp("H4 training n meetings", trn.meeting.nunique(), fz_["n_meetings"])
flag("H4 training meetings equal fit.json list", sorted(trn.date.unique()) == fz_["meetings"])
flag("H4 training dates all <= 2022-12-31", bool((trn.date <= "2022-12-31").all()))
mu = {c: trn[c].mean() for c in FA}
sd = {c: trn[c].std(ddof=1) for c in FA}
for c in FA:
    cmp(f"H4 fit standardise mean {c}", mu[c], fz_["standardise_mean"][c])
    cmp(f"H4 fit standardise sd {c}", sd[c], fz_["standardise_sd"][c])


def design(df, feats, mu_, sd_):
    return np.column_stack([np.ones(len(df))] + [(df[c].to_numpy(float) - mu_[c]) / sd_[c] for c in feats])


for mdl, fs in [("T", ["s_tilde"]), ("C", FA)]:
    X = design(trn, fs, mu, sd)
    b = np.linalg.solve(X.T @ X, X.T @ trn.y.to_numpy())   # normal equations (stage used lstsq)
    for c, v in zip(["const"] + fs, b):
        cmp(f"H4 fit coef_{mdl}.{c} (refit from market data)", v, fz_[f"coef_{mdl}"][c])

te = d4[d4["sample"] == PRIMARY].copy()
# forecasts from the FROZEN fit.json (not the refit)
smu, ssd = fz_["standardise_mean"], fz_["standardise_sd"]
te["yT"] = design(te, ["s_tilde"], smu, ssd) @ np.array([fz_["coef_T"][c] for c in ["const", "s_tilde"]])
te["yC"] = design(te, FA, smu, ssd) @ np.array([fz_["coef_C"][c] for c in ["const"] + FA])
y, yT, yC = te.y.to_numpy(), te.yT.to_numpy(), te.yC.to_numpy()
fcw = (y - yT) ** 2 - ((y - yC) ** 2 - (yT - yC) ** 2)
m, se, G = cr1_mean(fcw, te.meeting.to_numpy())
tcw = m / se
p_one = 1 - sps.t.cdf(tcw, G - 1)
p_two = 2 * sps.t.sf(abs(tcw), G - 1)
_, wp2, wp1 = wild_p(fcw, te.meeting.to_numpy(), centre=True)
_, wp2_alt, wp1_alt = wild_p(fcw, te.meeting.to_numpy(), seed=1, draws=99999, centre=True)
r2_ct = 1 - np.sum((y - yC) ** 2) / np.sum((y - yT) ** 2)
r2_c0 = 1 - np.sum((y - yC) ** 2) / np.sum(y ** 2)
r2_t0 = 1 - np.sum((y - yT) ** 2) / np.sum(y ** 2)
nz = y != 0
hitC = np.mean(np.sign(yC[nz]) == np.sign(y[nz]))
hitT = np.mean(np.sign(yT[nz]) == np.sign(y[nz]))
ff = h4res["answer_ZT"]["frozen_fit"]
cmp("H4 test n answers", len(te), ff["n"])
cmp("H4 test n meetings (G)", G, ff["n_clusters"])
cmp("H4 CW mean f", m, ff["mean_f"])
cmp("H4 CW CR1 SE", se, ff["se"])
cmp("H4 CW t", tcw, ff["t"])
cmp("H4 CW p one-sided t(G-1)", p_one, ff["p_one"])
cmp("H4 CW p two-sided t(G-1)", p_two, ff["p_two"])
cmp("H4 CW wild bootstrap p one-sided", wp1, ff["wcb_p_one"])
cmp("H4 CW wild bootstrap p two-sided", wp2, ff["wcb_p_two"])
cmp("H4 OOS R2 C vs T", r2_ct, ff["oos_r2_C_vs_T"])
cmp("H4 OOS R2 C vs zero", r2_c0, ff["oos_r2_C_vs_zero"])
cmp("H4 OOS R2 T vs zero", r2_t0, ff["oos_r2_T_vs_zero"])
cmp("H4 sign hit C", hitC, ff["sign_hit_C"])
cmp("H4 sign hit T", hitT, ff["sign_hit_T"])
cmp("H4 Holm input p_raw = recomputed CW p one-sided", p_one, fam["H4"]["p_raw"])
# compare the test-sample y and forecasts with the run's h4_answer_rows (log returns, no prices)
h4r = pd.read_csv(RUN / "results" / "h4_answer_rows.csv", dtype={"answer_id": str, "date": str})
h4r = h4r[(h4r.sym == "ZT")]
mm = te.merge(h4r[["answer_id", "y", "yT", "yC"]], on="answer_id", suffixes=("", "_run"))
flag(f"H4: per-answer y, yT, yC equal h4_answer_rows (n matched {len(mm)} of {len(te)})",
     len(mm) == len(te) and bool(np.allclose(mm.y, mm.y_run, rtol=1e-9, atol=1e-12) and
                                 np.allclose(mm.yT, mm.yT_run, rtol=1e-9, atol=1e-12) and
                                 np.allclose(mm.yC, mm.yC_run, rtol=1e-9, atol=1e-12)))
report["H4_primary"] = dict(n=len(te), G=G, mean_f=m, se_cr1=se, t=tcw, df=G - 1, p_one=p_one, p_two=p_two,
                            wcb_p_one=wp1, wcb_p_two=wp2, wcb_p_one_other_seed_99999=wp1_alt,
                            wcb_p_two_other_seed_99999=wp2_alt, oos_r2_C_vs_T=r2_ct, oos_r2_C_vs_zero=r2_c0,
                            oos_r2_T_vs_zero=r2_t0, sign_hit_C=hitC, sign_hit_T=hitT, n_nonzero_y=int(nz.sum()))

# H4 sign-position gross P&L at +1 min (ZT)
for mdl in ["C", "T"]:
    out = []
    for r in te.itertuples():
        pos = np.sign(getattr(r, f"y{mdl}"))
        if pos == 0:
            continue
        f = fill(r.date, "ZT", r.t0_utc, 1)
        out.append(dict(meeting=r.meeting, ticks=pos * (f[3] - f[1]) / zt_tick(r.date)))
    dd = pd.DataFrame(out)
    mm_, se_, G_ = cr1_mean(dd.ticks, dd.meeting)
    t_, p2_, _ = wild_p(dd.ticks.to_numpy(), dd.meeting.to_numpy())
    run_ = h4res["answer_ZT"][f"pnl_sign_{mdl}"]
    cmp(f"H4 sign(y{mdl}) gross mean ticks", mm_, run_["C0"]["mean"])
    cmp(f"H4 sign(y{mdl}) gross wild p two-sided", p2_, run_["C0"]["wcb_p_two"])
    cmp(f"H4 sign(y{mdl}) C2 mean ticks", mm_ - 4, run_["C2"]["mean"])
    cmp(f"H4 sign(y{mdl}) C4 mean ticks", mm_ - 8, run_["C4"]["mean"])
    report[f"H4_sign_{mdl}_gross"] = dict(n=len(dd), meetings=G_, mean_ticks=mm_, sum_ticks=float(dd.ticks.sum()),
                                         t_cr1=t_, wcb_p_two=p2_, hit=float((dd.ticks > 0).mean()))

# Holm recomputed
pv = {"H2": report["H2_primary"]["wcb_p_two"], "H3": 1.0, "H4": p_one}
order = sorted(pv, key=pv.get)
adj, run = {}, 0.0
for i, k in enumerate(order):
    run = max(run, min(1.0, (3 - i) * pv[k]))
    adj[k] = run
for k in pv:
    cmp(f"Holm adjusted p {k}", adj[k], fam[k]["p_holm"])
report["holm"] = adj

# ======================================================================== D. order of operations: manifests and mtimes
mans = {k: RUN / k / "manifest_sha256.txt" for k in ["qa", "features", "positions"]}
for k, p in mans.items():
    bad = []
    for line in p.read_text().splitlines():
        h, f = line.split("  ")
        if sha(RUN / k / f) != h:
            bad.append(f)
    flag(f"{k}: every file still matches its manifest hash", not bad, bad or None)
man_sha = {k: sha(p) for k, p in mans.items()}
report["manifest_sha256"] = man_sha
flag("fit.json records the current positions manifest hash", fit["positions_manifest_sha256"] == man_sha["positions"],
     man_sha["positions"])
flag("fit.json records the current features manifest hash", fit["features_manifest_sha256"] == man_sha["features"],
     man_sha["features"])
flag("fit.json records the current qa manifest hash", fit["qa_manifest_sha256"] == man_sha["qa"], man_sha["qa"])
fsha = sha(RUN / "h4_fit" / "fit.json")
flag("fit.sha256 file matches fit.json", (RUN / "h4_fit" / "fit.sha256").read_text().split()[0] == fsha, fsha)
rm = json.loads((RUN / "results" / "run_meta.json").read_text())
flag("run_meta and h4_results carry the same fit hash", rm["fit_sha256"] == fsha and h4res["fit_sha256"] == fsha)
flag("run_meta positions/features manifests equal the frozen manifests",
     rm["positions_manifest"] == mans["positions"].read_text() and rm["features_manifest"] == mans["features"].read_text())
flag("fit.json text_chrono answers hash equals the pre-registered 146f281a...",
     fit["text_chrono_answers_sha256"] == "146f281ad82b6478f0955d01b6913bbc4eb7149770264b269dbb1f0a3111afd6"
     == sha(BT / "text_chrono" / "answers.parquet"))
code_now = {f: sha(BT / "backtest" / "code" / f) for f in fit["h1_code_sha256"]}
flag("H1 code files unchanged since the fit", code_now == fit["h1_code_sha256"])

# mtimes (UTC): qa < features manifest < positions manifest < fit < first results file
tl = {"qa/manifest": mans["qa"], "features/manifest": mans["features"],
      "positions/manifest": mans["positions"], "h4_fit/fit.json": RUN / "h4_fit" / "fit.json",
      "h4_fit/fit.sha256": RUN / "h4_fit" / "fit.sha256"}
res_files = sorted((RUN / "results").glob("*"), key=lambda p: p.stat().st_mtime)
tl["results first (" + res_files[0].name + ")"] = res_files[0]
tl["results last (" + res_files[-1].name + ")"] = res_files[-1]
pos_files = list((RUN / "positions").glob("*"))
tl["positions latest file"] = max(pos_files, key=lambda p: p.stat().st_mtime)
report["mtimes_utc"] = {k: mtime(p) for k, p in tl.items()}
mt = {k: p.stat().st_mtime for k, p in tl.items()}
flag("mtime order: features manifest < positions manifest < fit.json <= fit.sha256 < every results file",
     mt["features/manifest"] < mt["positions/manifest"] < mt["h4_fit/fit.json"] <= mt["h4_fit/fit.sha256"]
     < min(p.stat().st_mtime for p in res_files))
flag("positions manifest is the last file written in positions/",
     mt["positions/manifest"] >= mt["positions latest file"])
flag("no file in qa/, features/, positions/, h4_fit/ modified after the first results file",
     max(p.stat().st_mtime for k in ["qa", "features", "positions", "h4_fit"] for p in (RUN / k).glob("*"))
     < min(p.stat().st_mtime for p in res_files))
# code-level: which steps can read prices
code = {f: (BT / "backtest" / "code" / f).read_text(encoding="utf-8") for f in
        ["h234_s1_features.py", "h234_s2_positions.py", "h234_s3_h4train.py", "h234_s4_pnl.py"]}
flag("s1 and s2 never construct Bars/Quotes (no market data before positions are hashed)",
     all("Bars(" not in code[f] and "Quotes(" not in code[f] and "GQH_MARKET_DIR" not in code[f]
         for f in ["h234_s1_features.py", "h234_s2_positions.py"]))
flag("s3 evaluates bars only for rows with sample additional_2018_2022 (asserted <= 2022-12-31)",
     'tr = sel[sel["sample"] == "additional_2018_2022"]' in code["h234_s3_h4train.py"]
     and "assert (tr.date <= TRAIN_END).all()" in code["h234_s3_h4train.py"]
     and "assert (mtr.date <= TRAIN_END).all()" in code["h234_s3_h4train.py"])
bl = pd.read_csv(RUN / "results" / "bar_log.csv", dtype={"date": str})
trn_tags = bl[bl.tag.str.startswith("h4") & bl.tag.str.contains("train")]
flag("bar_log: every h4 training-tag bar event is dated <= 2022-12-31",
     bool((trn_tags.date <= "2022-12-31").all()), dict(n_train_tag_events=len(trn_tags)))
log = (REPO / "backtests" / "rerun" / "h234_run_all_stdout.log").read_text(encoding="utf-8", errors="replace")
i_fit = log.find("fit sha256 " + fsha)
i_holm = log.find('"p_holm"')
flag("stage log prints the fit hash before the Holm family output", 0 <= i_fit < i_holm, dict(i_fit=i_fit, i_holm=i_holm))

# ======================================================================== E. excluded meetings contribute no voice/face row
ev = pd.read_csv(BT / "events" / "events.csv", dtype={"date": str})
warsh = sorted(ev.loc[ev.chair == "Warsh", "date"].str.replace("-", "").tolist())
EXCL = ["20230614", "20190501", "20200303", "20200315"] + warsh
report["excluded_meetings_checked"] = EXCL
meta_cols = ["nV", "nF", "nF_mouth_closed", "nF_not_reading", "nVres", "voice_media_end_s", "face_media_end_s",
             "voice_known_at_pkg_max", "face_known_at_pkg_max"]
vf = ["A_raw", "D_raw", "BD_raw", "BI_raw", "ES_raw", "BOU_raw", "EW_raw", "CS_raw", "M", "NEG_raw",
      "EXV_raw", "EXA_raw", "BDnr_raw", "BInr_raw", "ESnr_raw", "Vres_raw", "zA", "zD", "zVres", "zBD", "zBI", "zES",
      "zBOU", "zEW", "zCS", "zNEG", "zEXV", "zEXA", "zBDnr", "zBInr", "zESnr", "U", "Unr"]
mcols = [c for c in mfeat.columns if c.endswith("_m")]
qa = pd.read_csv(RUN / "qa" / "meeting_qa.csv", dtype={"presser_id": str})
bs = pd.read_csv(RUN / "qa" / "baseline_stats.csv", dtype={"presser_id": str})
posA = pd.read_csv(RUN / "positions" / "answers_h234_positions.csv", dtype={"answer_id": str}, low_memory=False)
posM = pd.read_csv(RUN / "positions" / "meetings_h234_positions.csv", dtype={"presser_id": str}, low_memory=False)
mtr = pd.read_csv(RUN / "results" / "meeting_trades.csv", low_memory=False)
ih = json.loads((RUN / "qa" / "input_hashes.json").read_text())
fit_meetings = {m.replace("-", "") for v in fit["fits"].values() for m in v["meetings"]}
excl_detail = {}
for pid in EXCL:
    fa = feat[feat.presser_id.astype(str) == pid]
    ch = chunks[chunks.presser_id.astype(str) == pid]
    ent = dict(
        feature_answer_rows=len(fa),
        feature_answer_rows_with_any_voice_face_value=int(fa[vf].notna().any(axis=1).sum()) if len(fa) else 0,
        feature_answer_rows_with_counts_or_times_only=int(fa[[c for c in meta_cols if c in fa]].notna().any(axis=1)
                                                          .sum()) if len(fa) else 0,
        chunk_rows_valid_in_answers=int((ch.valid & ch.answer_id.notna()).sum()) if len(ch) else 0,
        meeting_feature_values=int(mfeat.loc[mfeat.presser_id.astype(str) == pid, mcols].notna().sum().sum()),
        h2_ok=qa.loc[qa.presser_id == pid, "h2_ok"].tolist(), h3_ok=qa.loc[qa.presser_id == pid, "h3_ok"].tolist(),
        chunk_record_rows=len(ch), chunk_rows_valid=int(ch.valid.sum()) if len(ch) else 0,
        chunk_rows_with_answer_id=int(ch.answer_id.notna().sum()) if len(ch) else 0,
        chunk_rows_with_valence_resid=int(ch.valence_resid.notna().sum()) if len(ch) else 0,
        baseline_rows=int((bs.presser_id == pid).sum()),
        positions_rows_with_zA_or_U=int(posA[(posA.meeting.astype(str) == pid) & (posA.zA.notna() | posA.U.notna())]
                                        .shape[0]),
        positions_meeting_feature=int(posM[(posM.presser_id == pid) & (posM.zA_m.notna() | posM.U_m.notna())].shape[0]),
        selected_rows=int(sum((s.meeting.astype(str) == pid).sum() for s in (sel2, sel3, sel4))),
        in_any_fit=pid in fit_meetings,
        answer_trades=int((trades_run.meeting.astype(str) == pid).sum()),
        meeting_trades=int((mtr.meeting.astype(str) == pid).sum()),
        h4_rows=int((h4r.answer_id.str[:8] == pid).sum()),
        package_tables_read=sorted(k for k in ih if k.split("/")[0] == pid),
    )
    excl_detail[pid] = ent
    used = (ent["feature_answer_rows_with_any_voice_face_value"] + ent["meeting_feature_values"] + ent["baseline_rows"]
            + ent["positions_rows_with_zA_or_U"] + ent["positions_meeting_feature"] + ent["selected_rows"]
            + ent["answer_trades"] + ent["meeting_trades"] + ent["h4_rows"] + ent["chunk_rows_with_valence_resid"]
            + int(ent["in_any_fit"]))
    flag(f"{pid}: no voice/face value in any feature, baseline, position, fit or trade", used == 0, ent)
report["excluded_detail"] = excl_detail
# all selection/trade tables restricted to the 26 QA-passing meetings
okm = set(qa.loc[qa.h2_ok | qa.h3_ok, "presser_id"])
used_m = set(str(x) for s in (sel2, sel3, sel4) for x in s.meeting) | set(bs.presser_id)
flag("every meeting in selections and baselines passed QA (h2_ok or h3_ok)", used_m <= okm, sorted(used_m - okm))

# ======================================================================== E2. causal z recomputed from the raw answer values
# (prereg 3.5 / 4.3: Powell, strictly earlier QA-passing meetings, pooled rows, median and 1.4826 MAD, floor, burn-in 4,
# clip +-5). Confirms numerically that no excluded meeting's rows sit in any baseline.
def my_causal_z(col, floor, okset):
    sub = feat[feat.presser_id.astype(str).isin(okset) & np.isfinite(feat[col].astype(float))]
    dates = sub.groupby(sub.presser_id.astype(str)).date.first().sort_values()
    order = list(dates.index)
    z = pd.Series(np.nan, index=feat.index)
    binds = []
    for k, pid in enumerate(order):
        if k < 4:
            continue
        ref = sub.loc[sub.presser_id.astype(str).isin(order[:k]), col].to_numpy(float)
        c = np.median(ref)
        raw = 1.4826 * np.median(np.abs(ref - c))
        sc = max(raw, floor)
        binds.append(raw <= floor)
        rows = sub.index[sub.presser_id.astype(str) == pid]
        z.loc[rows] = np.clip((sub.loc[rows, col].to_numpy(float) - c) / sc, -5, 5)
    return z, order, binds


h2ok = set(qa.loc[qa.h2_ok, "presser_id"])
h3ok = set(qa.loc[qa.h3_ok, "presser_id"])
zmine = {}
for nm, col, fl, ok in [("zA", "A_raw", 0.01, h2ok), ("zD", "D_raw", 0.01, h2ok), ("zBD", "BD_raw", 0.005, h3ok),
                        ("zBI", "BI_raw", 0.005, h3ok), ("zES", "ES_raw", 0.005, h3ok)]:
    z, order, binds = my_causal_z(col, fl, ok)
    zmine[nm] = z
    a_, b_ = z.to_numpy(float), feat[nm].to_numpy(float)
    same_nan = np.array_equal(np.isnan(a_), np.isnan(b_))
    mx = float(np.nanmax(np.abs(a_ - b_) / np.maximum(np.abs(b_), 1e-12))) if np.isfinite(b_).any() else 0.0
    flag(f"{nm}: recomputed causal z equals the feature table (rel <= 1e-9, same missing pattern)",
         same_nan and mx <= 1e-9, dict(max_rel=mx, n=int(np.isfinite(a_).sum()), burn_in=order[:4],
                                       floor_binds=f"{int(sum(binds))}/{len(binds)}"))
    report.setdefault("g4_recomputed", {})[nm] = f"{int(sum(binds))}/{len(binds)}"
    flag(f"{nm}: no excluded meeting in its baseline order", not (set(order) & set(EXCL)))
Umine = pd.concat([zmine["zBD"], zmine["zBI"], zmine["zES"]], axis=1).mean(axis=1, skipna=False)
a_, b_ = Umine.to_numpy(float), feat["U"].to_numpy(float)
flag("U recomputed = mean(zBD, zBI, zES) equals the feature table",
     np.array_equal(np.isnan(a_), np.isnan(b_)) and float(np.nanmax(np.abs(a_ - b_))) <= 1e-9)

# ======================================================================== F. price levels outside git-ignored files
lv = set()
for col in ["open", "close"]:
    lv |= set(np.round(bars[col].to_numpy(float), 9).tolist())
hl = pd.read_parquet(MKT / "ohlcv-1m__all_2016_2026.parquet", columns=["high", "low"])
lv |= set(np.round(hl.high.to_numpy(float), 9).tolist()) | set(np.round(hl.low.to_numpy(float), 9).tolist())
rates_lv = {v for v in lv if 90 < v < 140 and abs(v * 256 - round(v * 256)) < 1e-6 and (v * 32) % 1 != 0}
# ZT/ZF/ZN levels that are not multiples of 1/32 (a coincidental match with an ordinary number is then very unlikely)
rates_arr = np.array(sorted(rates_lv))
# exact entry/exit prices of every H2/H3/H4 trade (all symbols), as pandas prints them
trade_px = set()
for t_ in (trades_run, mtr):
    for c in ("entry_px", "exit_px"):
        trade_px |= set(np.round(t_[c].to_numpy(float), 9).tolist())
es_trade_px = {v for v in trade_px if v > 1000}
files = subprocess.run(["git", "-C", str(REPO), "ls-files", "-co", "--exclude-standard"], capture_output=True,
                       text=True, check=True).stdout.splitlines()
PRICE_COLS = re.compile(r"(^|_)(entry_px|exit_px|px|price|open|high|low|close|bid_px_00|ask_px_00|bid|ask)($|_)", re.I)
num_re = re.compile(rb"(?<![\w.])-?\d{2,4}\.\d{3,}(?![\w])")
hits_rates, hits_cols, hits_es, scanned = {}, {}, {}, 0
for f in files:
    p = REPO / f
    if not p.is_file():
        continue
    suf = p.suffix.lower()
    if suf in (".csv", ".json", ".md", ".txt", ".py", ".sh", ".tsv", ".yaml", ".yml", ".toml", ".sbatch"):
        b = p.read_bytes()
        scanned += 1
        n = 0
        for tok in num_re.findall(b):
            try:
                v = round(float(tok), 9)
            except ValueError:
                continue
            if v in rates_lv:
                n += 1
        if n:
            hits_rates[f] = n
        ne = 0
        for tok in re.findall(rb"(?<![\w.])\d{4}\.(?:0|25|5|75)(?![\w.])", b):
            if round(float(tok), 9) in es_trade_px:
                ne += 1
        if ne:
            hits_es[f] = ne
        if suf in (".csv", ".tsv"):
            head = b.split(b"\n", 1)[0].decode("utf-8", "replace")
            pc = [c for c in head.split(",") if PRICE_COLS.search(c.strip().strip('"'))]
            if pc:
                hits_cols[f] = pc
    elif suf == ".parquet":
        scanned += 1
        try:
            df = pd.read_parquet(p)
        except Exception as e:  # noqa: BLE001
            hits_cols[f] = [f"unreadable: {e}"]
            continue
        pc = [c for c in df.columns if PRICE_COLS.search(str(c))]
        nr = 0
        for c in df.select_dtypes("number").columns:
            v = np.round(df[c].to_numpy(float), 9)
            nr += int(np.isin(v, rates_arr).sum())
        if pc:
            hits_cols[f] = pc
        if nr:
            hits_rates[f] = nr
report["price_scan"] = dict(files_not_ignored=len(files), scanned=scanned, rates_level_value_hits=hits_rates,
                            es_trade_price_value_hits=hits_es,
                            price_like_column_names=hits_cols)
# the ignored status of the run folder and trade logs
ign = subprocess.run(["git", "-C", str(REPO), "check-ignore", "-v",
                      "backtests/presser/backtest_h234_local/results/answer_trades.csv",
                      "backtests/presser/backtest_h234_local/results/meeting_trades.csv",
                      "backtests/presser/backtest_h234/results/answer_trades.csv",
                      "backtests/presser/backtest_h234/results/meeting_trades.csv",
                      "backtests/rerun/h234_run_all_stdout.log"], capture_output=True, text=True).stdout
report["git_check_ignore"] = ign.splitlines()
flag("run folder trade logs, HiPerGator trade-log paths and rerun/ are git-ignored", len(ign.splitlines()) == 5,
     ign.splitlines())
tracked_h234 = subprocess.run(["git", "-C", str(REPO), "ls-files", "backtests/presser/backtest_h234_local",
                               "backtests/presser/backtest_h234"], capture_output=True, text=True).stdout.split()
flag("no file under backtest_h234_local or backtest_h234 is tracked", not tracked_h234, tracked_h234)
# which run-folder files (ignored as a whole) hold price-level columns: only the two trade logs expected
run_px = {}
for p in RUN.rglob("*.csv"):
    head = p.read_text(encoding="utf-8", errors="replace").split("\n", 1)[0]
    pc = [c for c in head.split(",") if c in ("entry_px", "exit_px", "open", "close", "bid", "ask")]
    if pc:
        run_px[str(p.relative_to(RUN))] = pc
report["run_folder_price_columns"] = run_px
# the worker's scratch outputs (not in git) also claimed to be price free
extra = SCR / "h234_extra" / "out"
ex_hits = {}
if extra.is_dir():
    for p in extra.glob("*"):
        if p.suffix.lower() not in (".csv", ".json", ".txt"):
            continue
        b = p.read_bytes()
        n = sum(1 for tok in num_re.findall(b) if round(float(tok), 9) in rates_lv)
        head = b.split(b"\n", 1)[0].decode("utf-8", "replace")
        pc = [c for c in head.split(",") if PRICE_COLS.search(c.strip())] if p.suffix.lower() == ".csv" else []
        if n or pc:
            ex_hits[p.name] = dict(rates_value_hits=n, price_like_columns=pc)
report["h234_extra_out_scan"] = ex_hits

# ======================================================================== write (no price levels)
report["inputs"] = dict(run=str(RUN.relative_to(SCR)), fit_sha256=fsha, market_1m_sha256=sha(MKT / "ohlcv-1m__all_2016_2026.parquet"),
                        python=sys.version.split()[0], pandas=pd.__version__, numpy=np.__version__)
report["n_checks"] = len(report["checks"])
report["n_mismatch"] = len(report["mismatches"])


def conv(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


(OUTD / "verify_report.json").write_text(json.dumps(report, indent=1, default=conv))
print(json.dumps({k: report[k] for k in ["H2_primary", "H3_primary", "H4_primary", "H4_sign_C_gross",
                                          "H4_sign_T_gross", "holm", "manifest_sha256", "mtimes_utc", "n_checks",
                                          "n_mismatch", "mismatches"]}, indent=1, default=conv))
