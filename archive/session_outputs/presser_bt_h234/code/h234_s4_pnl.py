"""H2/H3/H4 step 4 (prereg 6.1-6.4, 7): one run from the frozen features, positions and H4 fit.

Execution, ticks, costs and bootstraps reuse the ADDENDUM code (lib.py). Every table carries the label
"exploratory, post-NO-GO; cannot rescue G3; no trading claim"."""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
from scipy import stats as sps

from lib import (B, COST_ROWS, SEED, TZ, WEBB, Bars, Quotes, answer_summary, check_addendum, cluster_t, sha256,
                 summarize, trade)
from h234_lib import (A29_NOTE, H1_CODE, HYP, LABEL, MEETING_COL, OUT, PREREG_SHA, SYMS, TEXT_CHRONO,
                      check_manifest, check_prereg, cr1_coef, dump, holm, load_provenance, lomo, wild_cluster_coef)

check_addendum()
check_prereg()
F, P, W, R = OUT / "features", OUT / "positions", OUT / "h4_fit", OUT / "results"
check_manifest(F, "features")
check_manifest(P, "positions")
h, f_ = (W / "fit.sha256").read_text().split()
if sha256(W / f_) != h:
    raise SystemExit("H4 fit changed after its freeze")
PROV = load_provenance()                           # checks the qa manifest; placebo label from step 1, not the env
fit = json.loads((W / "fit.json").read_text())
# the fit must have been made from exactly these positions, features and qa outputs, the frozen H1 code and label
for key, path in [("positions_manifest_sha256", P / "manifest_sha256.txt"),
                  ("features_manifest_sha256", F / "manifest_sha256.txt"),
                  ("qa_manifest_sha256", OUT / "qa" / "manifest_sha256.txt"),
                  ("text_chrono_answers_sha256", TEXT_CHRONO / "answers.parquet")]:
    if fit.get(key) != sha256(path):
        raise SystemExit(f"H4 fit was made from a different {key.replace('_sha256', '')}; re-run steps 2-3 first")
if fit["h1_code_sha256"] != {p.name: sha256(p) for p in sorted(H1_CODE.glob("*")) if p.is_file()}:
    raise SystemExit("H1 code changed after the H4 fit")
if bool(fit.get("placebo_features")) != bool(PROV["placebo"]):
    raise SystemExit("H4 fit and features disagree on placebo/real")
R.mkdir(parents=True, exist_ok=True)
PLACEBO = bool(PROV["placebo"])
TAG = "PLACEBO FEATURES (synthetic; not a result)" if PLACEBO else "real features"
T = lambda d, s: pd.Timestamp(f"{d} {s}", tz=TZ)
kill = json.loads((OUT / "qa" / "kill_switches.json").read_text())
bars = Bars()
quotes = Quotes()
PRIMARY = "primary_2023_2026"


def load_sel(k, hh):
    s = pd.read_csv(P / f"answer_sel_{k}_h{hh}.csv", dtype={"date": str, "answer_id": str})
    for c in ["t0", "tau_k_upper"]:
        s[c] = pd.to_datetime(s[c], utc=True, format="ISO8601").dt.tz_convert(TZ)
    return s


def one_trade(r, sym, pos, t_entry, hh):
    e_ts, e_px = bars.next_open(r.date, sym, t_entry, tag="h234_entry")
    if e_ts is None:
        return None
    x_ts, x_px = bars.close_at(r.date, sym, e_ts + pd.Timedelta(minutes=hh), lo=e_ts, tag=f"h234_h{hh}")
    if x_ts is None:
        return None
    tr = trade(r.date, sym, pos, e_ts, e_px, x_ts, x_px, e_ts, x_ts + pd.Timedelta(minutes=1), quotes)
    tr["logret_bp"] = 1e4 * math.log(x_px / e_px)
    return tr


# ======================================================================== answer-level trades
rows = []
for k in HYP:
    for hh in [1, 5, 15]:
        sel = load_sel(k, hh)
        for r in sel.itertuples():
            for sym in SYMS:
                pos = getattr(r, f"{k}__pos_{sym}")
                if not np.isfinite(pos) or pos == 0:
                    continue
                variants = [("base", r.t0)]
                if sym == "ZT":
                    variants.append(("entry_plus30s", r.tau_k_upper + pd.Timedelta(seconds=30)))
                for var, te in variants:
                    tr = one_trade(r, sym, pos, te if var != "base" else r.t0, hh)
                    if tr is None:
                        continue
                    tr.update(key=k, h=hh, variant=var, answer_id=r.answer_id, meeting=r.meeting, sample=r.sample,
                              year=int(r.date[:4]), ex_2020_2021=bool(r.ex_2020_2021), sens1_drop=bool(r.sens1_drop),
                              sens2_drop=bool(r.sens2_drop), sens3_keep=bool(r.sens3_keep), s_tilde=r.s_tilde,
                              R_ZT=r.R_ZT, M=r.M, feature=getattr(r, HYP[k]["col"]))
                    rows.append(tr)
AT = pd.DataFrame(rows)
AT.to_csv(R / "answer_trades.csv", index=False)


def samples(df):
    """(sample label, frame, cluster column) per prereg 6.3."""
    out = [(PRIMARY, df[df["sample"] == PRIMARY], "meeting"),
           ("additional_2018_2022", df[df["sample"] == "additional_2018_2022"], "meeting"),
           ("additional_2018_2022|year_cluster", df[df["sample"] == "additional_2018_2022"], "year"),
           ("pooled_2018_2026", df[df["sample"].isin([PRIMARY, "additional_2018_2022"])], "meeting"),
           ("pooled_ex_2020_2021", df[df["sample"].isin([PRIMARY, "additional_2018_2022"]) & df.ex_2020_2021], "meeting")]
    p = df[df["sample"] == PRIMARY]
    out += [(f"{PRIMARY}|sens1_drop_text_flags", p[~p.sens1_drop], "meeting"),
            (f"{PRIMARY}|sens2_drop_degraded", p[~p.sens2_drop], "meeting"),
            (f"{PRIMARY}|sens3_unc_le10", p[p.sens3_keep], "meeting")]
    return out


summ = []
for (k, hh, sym, var), g in AT.groupby(["key", "h", "sym", "variant"]):
    for smp, d, cl in (samples(g) if var == "base" else [(PRIMARY, g[g["sample"] == PRIMARY], "meeting")]):
        if len(d) == 0:
            continue
        for cost in COST_ROWS:
            col = f"{cost}_ticks" if d.tick_era.nunique() == 1 else f"{cost}_usd"
            yy = d[[col, "meeting", "date", "year"]].dropna()
            if len(yy) == 0:
                continue
            row = dict(key=k, kind=HYP[k]["kind"], what=HYP[k]["what"], h=hh, sym=sym, variant=var, sample=smp,
                       cluster=cl, cost=cost,
                       unit=col.split("_")[-1], **answer_summary(yy[col].values, yy[cl].values, yy.date.values))
            if cost == "C0" and cl == "meeting":
                row.update(lomo(yy[col].values, yy.meeting.values, yy.date.values))
            row["designated_primary"] = (k in ("H2", "H3") and hh == 1 and sym == "ZT" and var == "base"
                                         and smp == PRIMARY and cost == "C0")
            row["a29_note"] = A29_NOTE.get(smp.split("|")[0], "")
            row["label"], row["features"] = LABEL, TAG
            summ.append(row)
AS = pd.DataFrame(summ)
AS.to_csv(R / "answer_summary.csv", index=False)

# spread summary at the answer entries (ADDENDUM 7)
sp = (AT[(AT.variant == "base") & AT.hs_entry_ticks.notna()].groupby(["key", "h", "sym", "sample"]).hs_entry_ticks
      .agg(n="size", median="median", p90=lambda s: s.quantile(0.9)).reset_index())
sp.to_csv(R / "spreads_at_answer_entries.csv", index=False)

# ======================================================================== companion slopes (6.3)
feat = pd.read_parquet(F / "answers_h234.parquet")
slopes = []
z1 = AT[(AT.h == 1) & (AT.sym == "ZT") & (AT.variant == "base")]
for k in HYP:
    d0 = z1[z1.key == k]
    for smp, d, cl in samples(d0)[:5]:
        cols = ["feature", "s_tilde", "R_ZT"] + (["M"] if k == "H3" else [])
        d = d.dropna(subset=cols + ["logret_bp"])
        if d.meeting.nunique() < 3:
            continue
        X = np.column_stack([np.ones(len(d))] + [d[c].to_numpy(float) for c in cols])
        res = wild_cluster_coef(d.logret_bp.to_numpy(float), X, d[cl].to_numpy(), 1)
        slopes.append(dict(key=k, kind=HYP[k]["kind"], sample=smp, cluster=cl,
                           regressors="const + " + " + ".join(["z" if c == "feature" else c for c in cols]),
                           **res, label=LABEL, features=TAG))
# Tier-3 named descriptive face features (4.4): coefficient and CR1 t only, no p-value counted
d3 = z1[z1.key == "H3"].merge(feat[["answer_id", "zBD", "zBI", "zES", "zBOU", "zEW", "zCS", "zNEG", "zEXV", "zEXA",
                                    "Unr"]], on="answer_id", how="left")
for c in ["zBD", "zBI", "zES", "zBOU", "zEW", "zCS", "zNEG", "zEXV", "zEXA", "Unr"]:
    for smp in [PRIMARY, "additional_2018_2022"]:
        d = d3[d3["sample"] == smp].dropna(subset=[c, "s_tilde", "R_ZT", "M", "logret_bp"])
        if d.meeting.nunique() < 3:
            continue
        X = np.column_stack([np.ones(len(d)), d[c], d.s_tilde, d.R_ZT, d.M])
        coef, se, t, G = cr1_coef(d.logret_bp.to_numpy(float), X, d.meeting.to_numpy(), 1)
        slopes.append(dict(key=f"tier3:{c}", kind="descriptive (no p-value counted)", sample=smp, cluster="meeting",
                           regressors=f"const + {c} + s_tilde + R_ZT + M", coef=coef, se_cr1=se, t_cr1=t, n=len(d),
                           n_clusters=G, label=LABEL, features=TAG))
pd.DataFrame(slopes).to_csv(R / "companion_slopes.csv", index=False)

# descriptive distributions of every named feature (answer and meeting level)
mfeat = pd.read_parquet(F / "meetings_h234.parquet")
desc = []
for c in ["zA", "zD", "zVres", "U", "Unr", "M", "zBD", "zBI", "zES", "zBOU", "zEW", "zCS", "zNEG", "zEXV", "zEXA"]:
    for lvl, df, col in [("answer", feat, c), ("meeting", mfeat, f"{c}_m")]:
        if col not in df.columns:
            continue
        v = df[col].dropna()
        desc.append(dict(feature=c, level=lvl, n=len(v), mean=v.mean(), sd=v.std(), p10=v.quantile(0.1),
                         median=v.median(), p90=v.quantile(0.9), features=TAG))
pd.DataFrame(desc).to_csv(R / "feature_distributions.csv", index=False)

# ======================================================================== meeting level (6.1, as H1-primary)
mp = pd.read_csv(P / "meetings_h234_positions.csv", dtype={"date": str})
mp["tau_end_upper"] = pd.to_datetime(mp.tau_end_upper, utc=True, format="ISO8601").dt.tz_convert(TZ)
mrows = []
for k in HYP:
    el = mp[mp[f"{k}__meligible"].astype(bool)]
    for r in el.itertuples():
        for sym in SYMS:
            pos = getattr(r, f"{k}__mpos_{sym}")
            if not np.isfinite(pos) or pos == 0:
                continue
            for clock, tau in [("primary", r.tau_end_upper), ("exec30", r.tau_end_upper + pd.Timedelta(seconds=30))]:
                e_ts, e_px = bars.next_open(r.date, sym, tau, tag=f"h234m_{clock}")
                if e_ts is None or e_ts >= T(r.date, "15:59:00"):
                    continue
                exits = [("exit_1600", T(r.date, "16:00:00"))] + ([("exit_1630", T(r.date, "16:30:00"))]
                                                                   if clock == "primary" else [])
                for ex, TT in exits:
                    x_ts, x_px = bars.close_at(r.date, sym, TT, lo=e_ts, tag=f"h234m_{ex}")
                    if x_ts is None:
                        continue
                    tr = trade(r.date, sym, pos, e_ts, e_px, x_ts, x_px, e_ts, x_ts + pd.Timedelta(minutes=1), quotes)
                    tr.update(key=k, clock=clock, exit=ex, meeting=r.meeting, sample=r.sample,
                              ex_2020_2021=bool(r.ex_2020_2021), sens1_drop=bool(r.sens1_drop),
                              sens2_drop=bool(r.sens2_drop), sens3_keep=bool(r.sens3_keep),
                              feature=getattr(r, MEETING_COL[HYP[k]["col"]]),
                              logret_bp=1e4 * math.log(x_px / e_px),
                              es_halt_exit=(sym == "ES" and ex == "exit_1630" and x_ts < T(r.date, "16:15:00")))
                    mrows.append(tr)
MT = pd.DataFrame(mrows)
MT.to_csv(R / "meeting_trades.csv", index=False)
msumm = []
for (k, sym, clock, ex), g in MT.groupby(["key", "sym", "clock", "exit"]):
    sm_list = [(PRIMARY, g[g["sample"] == PRIMARY]), ("additional_2018_2022", g[g["sample"] == "additional_2018_2022"]),
               ("pooled_2018_2026", g[g["sample"].isin([PRIMARY, "additional_2018_2022"])]),
               ("pooled_ex_2020_2021", g[g["sample"].isin([PRIMARY, "additional_2018_2022"]) & g.ex_2020_2021])]
    p = g[g["sample"] == PRIMARY]
    sm_list += [(f"{PRIMARY}|sens1_drop_text_flags", p[~p.sens1_drop]), (f"{PRIMARY}|sens2_drop_degraded", p[~p.sens2_drop]),
                (f"{PRIMARY}|sens3_unc_le10", p[p.sens3_keep])]
    for smp, d in sm_list:
        for cost in COST_ROWS:
            col = f"{cost}_ticks" if d.tick_era.nunique() == 1 else f"{cost}_usd"
            dd = d.sort_values("date").dropna(subset=[col])
            y = dd[col]
            if len(y) == 0:
                continue
            row = dict(key=k, kind=HYP[k]["kind"], what=HYP[k]["what"], sym=sym, clock=clock, exit=ex, sample=smp,
                       cost=cost, unit=col.split("_")[-1], **summarize(y.values))
            if cost == "C0":
                row.update(lomo(y.values, dd.meeting.values, dd.date.values))
            row.update(a29_note=A29_NOTE.get(smp.split("|")[0], ""), label=LABEL, features=TAG)
            msumm.append(row)
pd.DataFrame(msumm).to_csv(R / "meeting_summary.csv", index=False)

# ======================================================================== H4 (6.4)


def predict(df, fd, model, feats):
    X = np.column_stack([np.ones(len(df))] + [(df[c].to_numpy(float) - fd["standardise_mean"][c]) /
                                               fd["standardise_sd"][c] for c in feats])
    b = np.array([fd[f"coef_{model}"][c] for c in ["const"] + feats])
    return X @ b


def ols_fit(df, y, feats):
    mu = {c: float(df[c].mean()) for c in feats}
    sd = {c: float(df[c].std(ddof=1)) for c in feats}
    X = np.column_stack([np.ones(len(df))] + [(df[c].to_numpy(float) - mu[c]) / sd[c] for c in feats])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    return dict(standardise_mean=mu, standardise_sd=sd, coef=dict(zip(["const"] + feats, map(float, b))))


def predict_free(df, fd, feats):
    X = np.column_stack([np.ones(len(df))] + [(df[c].to_numpy(float) - fd["standardise_mean"][c]) /
                                               fd["standardise_sd"][c] for c in feats])
    return X @ np.array([fd["coef"][c] for c in ["const"] + feats])


def cw(y, yT, yC, g, se="cr1"):
    """Clark-West: f = (y - yT)^2 - [(y - yC)^2 - (yT - yC)^2]; one-sided (C better) p from t(G-1)."""
    f = (y - yT) ** 2 - ((y - yC) ** 2 - (yT - yC) ** 2)
    out = dict(n=len(f), mean_f=float(np.mean(f)) if len(f) else np.nan)
    if se == "cr1":
        G = len(np.unique(g))
        if G < 3:
            return out
        m, s, t, _ = cluster_t(f, g)
    else:                                              # HC3 for one observation per meeting
        G = len(f)
        if G < 3:
            return out
        m = f.mean()
        s = math.sqrt(np.sum((f - m) ** 2 / (1 - 1 / G) ** 2)) / G
        t = m / s if s > 0 else np.nan
    out.update(se=s, t=t, n_clusters=G, df=G - 1, p_one=float(1 - sps.t.cdf(t, G - 1)),
               p_two=float(2 * (1 - sps.t.cdf(abs(t), G - 1))))
    if se == "cr1":                                    # wild cluster bootstrap of mean(f), Webb, centred
        codes, gi = np.unique(g, return_inverse=True)
        rng = np.random.default_rng(SEED)
        w = rng.choice(WEBB, size=(B, G))
        fc = f - m
        n = len(f)
        ys = w[:, gi] * fc[None, :]
        ms = ys.mean(1)
        S = np.zeros((B, G))
        for j in range(G):
            S[:, j] = (ys[:, gi == j] - ms[:, None]).sum(1)
        ses = np.sqrt((G / (G - 1)) * (S ** 2).sum(1) / n ** 2)
        ts = ms / ses
        out.update(wcb_p_one=float((1 + np.sum(ts >= t)) / (B + 1)),
                   wcb_p_two=float((1 + np.sum(np.abs(ts) >= abs(t))) / (B + 1)))
    out["oos_r2_C_vs_T"] = float(1 - np.sum((y - yC) ** 2) / np.sum((y - yT) ** 2))
    out["oos_r2_C_vs_zero"] = float(1 - np.sum((y - yC) ** 2) / np.sum(y ** 2))
    out["oos_r2_T_vs_zero"] = float(1 - np.sum((y - yT) ** 2) / np.sum(y ** 2))
    nz = y != 0
    out["sign_hit_C"] = float(np.mean(np.sign(yC[nz]) == np.sign(y[nz]))) if nz.any() else np.nan
    out["sign_hit_T"] = float(np.mean(np.sign(yT[nz]) == np.sign(y[nz]))) if nz.any() else np.nan
    return out


h4 = dict(label=LABEL, features=TAG, fit_sha256=sha256(W / "fit.json"))
sel4 = load_sel("H4", 1)
FA, FM = ["s_tilde", "zA", "U"], ["s_tilde_m", "zA_m", "U_m"]
h4rows = []
for sym in ["ZT", "ES"]:
    ys, keep = [], []
    for r in sel4.itertuples():
        tr = one_trade(r, sym, 1, r.t0, 1)
        ys.append(tr["logret_bp"] if tr else np.nan)
    d = sel4.assign(y=ys).dropna(subset=["y"] + FA)
    fd = fit["fits"][f"answer_{sym}"]
    d["yT"] = predict(d, fd, "T", ["s_tilde"])
    d["yC"] = predict(d, fd, "C", FA)
    d["sym"] = sym
    h4rows.append(d)
    te = d[d["sample"] == PRIMARY]
    tr_ = d[d["sample"] == "additional_2018_2022"]
    blk = {"frozen_fit": cw(te.y.values, te.yT.values, te.yC.values, te.meeting.values)}
    blk["frozen_fit"]["designated_primary"] = sym == "ZT"
    # P&L of sign(yC) and sign(yT) positions at +1 min (gross, C2, C4 and the other cost rows)
    for mdl in ["C", "T"]:
        pr = []
        for r in te.itertuples():
            pos = np.sign(getattr(r, f"y{mdl}"))
            if pos == 0:
                continue
            t_ = one_trade(r, sym, pos, r.t0, 1)
            if t_:
                t_.update(meeting=r.meeting)
                pr.append(t_)
        pr = pd.DataFrame(pr)
        if len(pr):
            blk[f"pnl_sign_{mdl}"] = {c: answer_summary(pr[f"{c}_ticks" if pr.tick_era.nunique() == 1 else f"{c}_usd"]
                                                        .values, pr.meeting.values, pr.date.values)
                                      for c in ["C0", "C2", "C4"]}
    # expanding window: refit before each test meeting on all earlier meetings (not decisive)
    pe = []
    for mtg, g in te.sort_values("date").groupby("meeting", sort=False):
        past = d[d.date < g.date.iloc[0]]
        fT, fC = ols_fit(past, past.y.values, ["s_tilde"]), ols_fit(past, past.y.values, FA)
        pe.append(g.assign(yT_e=predict_free(g, fT, ["s_tilde"]), yC_e=predict_free(g, fC, FA)))
    pe = pd.concat(pe) if pe else te.iloc[0:0]
    blk["expanding_window"] = cw(pe.y.values, pe.yT_e.values, pe.yC_e.values, pe.meeting.values) if len(pe) else {}
    # leave-one-meeting-out within each sample (labelled: not point-in-time)
    for nm, dd in [("lomo_2023_2026_not_point_in_time", te), ("lomo_2018_2022_not_point_in_time", tr_)]:
        pl = []
        for mtg, g in dd.groupby("meeting"):
            rest = dd[dd.meeting != mtg]
            if len(rest) < 5:
                continue
            fT, fC = ols_fit(rest, rest.y.values, ["s_tilde"]), ols_fit(rest, rest.y.values, FA)
            pl.append(g.assign(yT_l=predict_free(g, fT, ["s_tilde"]), yC_l=predict_free(g, fC, FA)))
        pl = pd.concat(pl) if pl else dd.iloc[0:0]
        blk[nm] = cw(pl.y.values, pl.yT_l.values, pl.yC_l.values, pl.meeting.values) if len(pl) else {}
    h4[f"answer_{sym}"] = blk
pd.concat(h4rows).to_csv(R / "h4_answer_rows.csv", index=False)
# meeting-level version (HC3), ZT and ES
m4 = mp[mp["H4__meligible"].astype(bool)].copy()
for sym in ["ZT", "ES"]:
    ys = []
    for r in m4.itertuples():
        e_ts, e_px = bars.next_open(r.date, sym, r.tau_end_upper, tag="h4m_entry")
        if e_ts is None or e_ts >= T(r.date, "15:59:00"):
            ys.append(np.nan)
            continue
        x_ts, x_px = bars.close_at(r.date, sym, T(r.date, "16:00:00"), lo=e_ts, tag="h4m_exit")
        ys.append(1e4 * math.log(x_px / e_px) if x_ts is not None else np.nan)
    d = m4.assign(y=ys).dropna(subset=["y"] + FM)
    fd = fit["fits"][f"meeting_{sym}"]
    te = d[d["sample"] == PRIMARY]
    h4[f"meeting_{sym}"] = cw(te.y.values, predict(te, fd, "T", ["s_tilde_m"]), predict(te, fd, "C", FM),
                              te.meeting.values, se="hc3")

# ======================================================================== family (7)
fam = {}
for k in ["H2", "H3"]:
    row = AS[AS.designated_primary & (AS.key == k)]
    p_raw = float(row.wcb_p_two.iloc[0]) if len(row) and pd.notna(row.wcb_p_two.iloc[0]) else None
    status = "killed" if kill[k]["killed"] else ("unrunnable" if p_raw is None else "run")
    fam[k] = dict(status=status, p_raw=p_raw if status == "run" else None, p_used=p_raw if status == "run" else 1.0,
                  n_answers=int(row.n_answers.iloc[0]) if len(row) else 0,
                  n_meetings=int(row.n_meetings.iloc[0]) if len(row) and pd.notna(row.n_meetings.iloc[0]) else 0,
                  mean_ticks=float(row["mean"].iloc[0]) if len(row) else None,
                  bb_ci90=[row.bb_ci90_lo.iloc[0], row.bb_ci90_hi.iloc[0]] if len(row) else None,
                  reasons=kill[k]["reasons"], labels=kill[k]["labels"])
c4 = h4["answer_ZT"]["frozen_fit"]
p4 = c4.get("p_one")
fam["H4"] = dict(status="run" if p4 is not None else "unrunnable", p_raw=p4, p_used=p4 if p4 is not None else 1.0,
                 n_answers=c4.get("n"), n_meetings=c4.get("n_clusters"), labels=[LABEL])
adj = holm({k: v["p_used"] for k, v in fam.items()})
for k in fam:
    fam[k]["p_holm"] = adj[k]
    fam[k]["holm_significant_at_0.05"] = bool(adj[k] <= 0.05)
    fam[k]["wording"] = ("exploratory association, post-NO-GO" if adj[k] <= 0.05 else
                         "not detected (see the 90% CI upper bound)")
fam["note"] = ("Holm m = 3 across H2, H3, H4 (new exploratory family; the locked register keeps them at p = 1, "
               "R2-26). A killed or unrunnable primary enters with p = 1.")
fam["features"] = TAG
dump(R / "h4_results.json", h4)
dump(R / "family_holm.json", fam)
pd.DataFrame(bars.log).to_csv(R / "bar_log.csv", index=False)
dump(R / "run_meta.json", dict(label=LABEL, features=TAG, placebo_tree=PLACEBO, fedpress_root=PROV["fedpress_root"],
                               seed=SEED, draws=B, prereg_sha256=PREREG_SHA, addendum_code="lib.py (ADDENDUM 1, 7, 8)",
                               features_manifest=(F / "manifest_sha256.txt").read_text(),
                               positions_manifest=(P / "manifest_sha256.txt").read_text(),
                               fit_sha256=sha256(W / "fit.json"), bad_quote_records_skipped=quotes.n_bad))
print(json.dumps(fam, indent=1, default=str))
print(json.dumps({k: {kk: v.get(kk) for kk in ("n", "n_clusters", "mean_f", "t", "p_one", "oos_r2_C_vs_T")}
                  for k, v in [("answer_ZT", h4["answer_ZT"]["frozen_fit"]), ("answer_ES", h4["answer_ES"]["frozen_fit"]),
                               ("meeting_ZT", h4["meeting_ZT"]), ("meeting_ES", h4["meeting_ES"])]}, indent=1, default=str))
