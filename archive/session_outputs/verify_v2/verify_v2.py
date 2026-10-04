"""Independent recomputation of the v2 D-3 OOS report and the IS reproduction claim.

Reads saved daily series only (backtests/results/v2_oos/daily_returns.{csv,parquet} and run/*.parquet),
the committed IS tables (backtests/results/v2) and the frozen snapshot. Writes nothing into the repo.
Own numpy implementations (no v2lib import).
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

REPO = Path(sys.argv[1])
OUTDIR = Path(sys.argv[2])
R = REPO / "backtests/results/v2_oos"
RUN = R / "run"
C = REPO / "backtests/results/v2"
SNAP = REPO / "backtest_snapshot/fedspeak_v2/backtest"
ANN = 252.0
TOL = 1e-6

WINDOWS = {"selection": ("2016-01-04", "2020-12-31"), "validation": ("2021-01-01", "2024-10-02"),
           "full_is": ("2016-01-04", "2024-10-02"), "oos": ("2024-10-03", "2026-10-02")}
BASES = ("net_1x", "net_2x", "gross")
mismatches: list[dict] = []
checks = {"n_compared": 0}


def cmp(label, mine, rep, tol=TOL):
    checks["n_compared"] += 1
    mine, rep = float(mine), float(rep)
    if math.isnan(mine) and math.isnan(rep):
        return 0.0
    ad = abs(mine - rep)
    rel = ad / abs(rep) if rep != 0 else ad
    if not (ad <= 1e-12 or rel <= tol):
        mismatches.append({"what": label, "mine": mine, "reported": rep, "rel": rel})
    return rel


def cmp_printed(label, mine, printed: str, scale=1.0):
    """printed is a rounded string (e.g. '0.607', '-6.6', '108'); check rounding consistency."""
    checks["n_compared"] += 1
    p = float(printed)
    dec = len(printed.split(".")[1]) if "." in printed else 0
    half = 0.5 * 10 ** (-dec) + 1e-12
    if abs(mine * scale - p) > half:
        mismatches.append({"what": f"printed: {label}", "mine": mine * scale, "reported": printed,
                           "rel": abs(mine * scale - p) / max(abs(p), 1e-12)})


# ---------------------------------------------------------------- own metric functions
def sharpe(x):
    x = np.asarray(x, float)
    return x.mean() / x.std(ddof=1) * math.sqrt(ANN)


def maxdd(x, with_start_peak=False):
    eq = np.cumprod(1 + np.asarray(x, float))
    if with_start_peak:
        eq = np.concatenate([[1.0], eq])
    peak = np.maximum.accumulate(eq)
    return (eq / peak - 1).min()


def nw_t(x):
    x = np.asarray(x, float)
    n = len(x)
    lag = math.floor(4 * (n / 100.0) ** (2.0 / 9.0))
    d = x - x.mean()
    g0 = np.dot(d, d) / n
    lrv = g0 + sum(2 * (1 - k / (lag + 1)) * np.dot(d[k:], d[:-k]) / n for k in range(1, lag + 1))
    return x.mean() / math.sqrt(lrv / n)


def nw_t_statsmodels(x):
    import statsmodels.api as sm
    x = np.asarray(x, float)
    n = len(x)
    lag = math.floor(4 * (n / 100.0) ** (2.0 / 9.0))
    res = sm.OLS(x, np.ones(n)).fit(cov_type="HAC", cov_kwds={"maxlags": lag, "use_correction": False})
    return float(res.tvalues[0])


def geo(x):
    x = np.asarray(x, float)
    return math.exp(np.log1p(x).sum() * ANN / len(x)) - 1


def stats(x, turn=None, rf=None, fedturn=None):
    x = np.asarray(x, float)
    yrs = len(x) / ANN
    out = {"n_days": len(x), "ann_return_arith": x.mean() * ANN, "ann_return_geo": geo(x),
           "ann_vol": x.std(ddof=1) * math.sqrt(ANN), "sharpe": sharpe(x), "max_drawdown": maxdd(x),
           "max_drawdown_with_start_peak": maxdd(x, True), "hit_rate": float((x > 0).mean()), "nw_t": nw_t(x)}
    if rf is not None:
        out["ann_total_return_geo"] = geo(x + np.asarray(rf, float))
    if turn is not None:
        out["turnover_per_year"] = float(np.nansum(turn) / yrs)
    if fedturn is not None:
        out["fed_sleeve_turnover_per_year"] = float(np.nansum(fedturn) / yrs)
    return out


def win(df, w, first=None):
    a, b = WINDOWS[w] if isinstance(w, str) else w
    a = pd.Timestamp(a)
    if first is not None:
        a = max(a, first)
    return df.loc[a:pd.Timestamp(b)]


# ---------------------------------------------------------------- load saved series
dp = pd.read_parquet(R / "daily_returns.parquet")
dc = pd.read_csv(R / "daily_returns.csv", index_col="date", parse_dates=True)
t4 = pd.read_parquet(RUN / "daily_T4xE1_full.parquet")
va = pd.read_parquet(RUN / "daily_VariantA_frozen_T0fxE1_full.parquet")
pf = pd.read_parquet(RUN / "daily_portfolio_full.parquet")
report = {}

# csv vs parquet
num = [c for c in dp.columns if c != "window"]
d = (dp[num] - dc[num]).abs()
rel = (d / dp[num].abs().where(dp[num].abs() > 1e-9)).max().max()
report["csv_vs_parquet"] = {"max_abs": float(d.max().max()), "max_rel(|x|>1e-9)": float(rel),
                            "same_index": bool(dp.index.equals(dc.index)),
                            "window_labels_equal": bool((dp["window"] == dc["window"]).all())}

# daily_returns.parquet vs run parquets
first_t4 = t4.index[t4["gross_exposure"] > 0][0]
first_va = va.index[va["gross_exposure"] > 0][0]
report["first_position"] = {"T4xE1": str(first_t4.date()), "VariantA": str(first_va.date())}
src = {}
for name, s, f in (("T4xE1", t4, first_t4), ("VariantA_frozen(T0fxE1)", va, first_va)):
    s = s.loc[f:"2026-10-02"]
    src[name] = pd.DataFrame({"net_1x": s["ex1"], "net_2x": s["ex2"], "gross": s["exg"], "turnover": s["turnover"],
                              "rf": s["rf"]})
for name in ("core_ER_6", "core_ER_6+T4xE1"):
    df = pd.DataFrame({b: pf[f"{name}|{b}"] for b in BASES}).dropna(subset=["net_1x"])
    df["turnover"] = pf[f"{name}|overlay_turnover"].reindex(df.index)
    # rf: last available T-bill day on or before the date (own asof join)
    rfs = t4["rf"].sort_index()
    pos = rfs.index.searchsorted(df.index, side="right") - 1
    df["rf"] = np.where(pos >= 0, rfs.to_numpy()[np.clip(pos, 0, None)], 0.0)
    if name != "core_ER_6":
        m = pf[f"{name}|m_FED_T4xE1"].reindex(df.index).fillna(0.0)
        df["fed_turnover"] = m * t4["turnover"].reindex(df.index).fillna(0.0)
    src[name] = df

dd = {}
for name in src:
    for b in BASES:
        col = f"{name}|{b}"
        a = dp[col].dropna()
        bb = src[name][b].reindex(a.index)
        dd[col] = float((a - bb).abs().max())
dd["T4xE1|turnover"] = float((dp["T4xE1|turnover"] - src["T4xE1"]["turnover"].reindex(dp.index)).abs().max())
report["daily_returns_vs_run_parquets_max_abs"] = dd
report["daily_returns_last_date"] = str(dp.index.max().date())
for col in num:
    a = dp[col].dropna()
    if len(a) and a.index.max() > pd.Timestamp("2026-10-02"):
        mismatches.append({"what": f"{col} has data after 2026-10-02"})

# window labels
lab = pd.Series("pre_selection", index=dp.index)
for w in ("selection", "validation", "oos"):
    a, b = WINDOWS[w]
    lab[(dp.index >= a) & (dp.index <= b)] = w
report["window_labels_ok"] = bool((lab == dp["window"]).all())

# ---------------------------------------------------------------- 1) metrics.csv recompute
mcsv = pd.read_csv(R / "metrics.csv")
mine_rows = []
for _, r in mcsv.iterrows():
    name, w, b = r["series"], r["window"], r["basis"]
    first = first_t4 if name == "T4xE1" else first_va if name.startswith("VariantA") else None
    sub = win(src[name], w, first)
    x = sub[b].dropna()
    sub = sub.loc[x.index]
    st = stats(x, sub["turnover"], sub["rf"], sub["fed_turnover"] if "fed_turnover" in sub else None)
    # same from the CSV / parquet of daily_returns (for return metrics)
    xp = win(dp[f"{name}|{b}"].dropna(), w, first)
    xc = win(dc[f"{name}|{b}"].dropna(), w, first)
    stp, stc = stats(xp), stats(xc)
    mine_rows.append({"series": name, "window": w, "basis": b, **st})
    lbl = f"metrics.csv {name}/{w}/{b}"
    if str(x.index[0].date()) != r["start"] or str(x.index[-1].date()) != r["end"] or len(x) != r["n_days"]:
        mismatches.append({"what": f"{lbl} window", "mine": [str(x.index[0].date()), str(x.index[-1].date()), len(x)],
                           "reported": [r["start"], r["end"], int(r["n_days"])]})
    for k in ("ann_return_arith", "ann_return_geo", "ann_total_return_geo", "ann_vol", "sharpe", "max_drawdown",
              "hit_rate", "turnover_per_year", "nw_t"):
        cmp(f"{lbl} {k}", st[k], r[k])
    if not pd.isna(r.get("fed_sleeve_turnover_per_year")):
        cmp(f"{lbl} fed_sleeve_turnover_per_year", st["fed_sleeve_turnover_per_year"], r["fed_sleeve_turnover_per_year"])
    for k in ("ann_return_arith", "ann_return_geo", "ann_vol", "sharpe", "max_drawdown", "hit_rate", "nw_t"):
        cmp(f"{lbl} {k} [from daily_returns.parquet]", stp[k], r[k])
        cmp(f"{lbl} {k} [from daily_returns.csv]", stc[k], r[k], tol=1e-6)
mine = pd.DataFrame(mine_rows)
mine.to_csv(OUTDIR / "metrics_recomputed.csv", index=False)

# NW t cross-check with statsmodels
nwx = {}
for name in src:
    for w in WINDOWS:
        first = first_t4 if name == "T4xE1" else first_va if name.startswith("VariantA") else None
        x = win(src[name], w, first)["net_1x"].dropna()
        nwx[f"{name}/{w}"] = abs(nw_t(x) - nw_t_statsmodels(x))
report["nw_t_own_vs_statsmodels_max_abs"] = max(nwx.values())

# drawdown definition sensitivity (start peak at 1.0 vs first day's equity)
ddiff = mine.assign(diff=(mine["max_drawdown_with_start_peak"] - mine["max_drawdown"]).abs())
report["maxdd_start_peak_sensitivity"] = ddiff.loc[ddiff["diff"] > 1e-12, ["series", "window", "basis", "max_drawdown",
                                                                           "max_drawdown_with_start_peak"]].to_dict("records")

# metrics.md rounding
md = (R / "metrics.md").read_text(encoding="utf-8")
cur = None
mi = mine.set_index(["series", "window", "basis"])
for line in md.splitlines():
    if line.startswith("## "):
        cur = line[3:].strip()
        continue
    m = re.match(r"\| (selection|validation|full_is|oos) \| (net_1x|net_2x|gross) \|(.*)\|$", line)
    if m and cur:
        w, b = m.group(1), m.group(2)
        cells = [c.strip() for c in m.group(3).split("|")]
        row = mi.loc[(cur, w, b)]
        keys = [("sharpe", 1), ("ann_return_arith", 100), ("ann_return_geo", 100), ("ann_vol", 100),
                ("max_drawdown", 100), ("turnover_per_year", 1), ("hit_rate", 100)]
        for (k, sc), cell in zip(keys, cells):
            cmp_printed(f"metrics.md {cur}/{w}/{b} {k}", row[k], cell.rstrip("%"), sc)

# ---------------------------------------------------------------- 2) run/ outputs
oc = json.loads((RUN / "oos_chosen.json").read_text(encoding="utf-8"))
o1, o2, og = (mi.loc[("T4xE1", "oos", b)] for b in BASES)
for k, v in (("sharpe_net1x", o1["sharpe"]), ("sharpe_net2x", o2["sharpe"]), ("sharpe_gross", og["sharpe"]),
             ("ann_excess_arith", o1["ann_return_arith"]), ("ann_excess_geo", o1["ann_return_geo"]),
             ("vol", o1["ann_vol"]), ("max_dd_excess", o1["max_drawdown"]), ("nw_t", o1["nw_t"]),
             ("turnover_per_year", o1["turnover_per_year"]), ("n_days", o1["n_days"])):
    cmp(f"oos_chosen.json {k}", v, oc[k])

po = pd.read_csv(RUN / "portfolio_oos.csv").set_index("portfolio")
for n in po.index:
    a = mi.loc[(n, "oos", "net_1x")]
    cmp(f"portfolio_oos.csv {n} sharpe_net1x", a["sharpe"], po.loc[n, "sharpe_net1x"])
    cmp(f"portfolio_oos.csv {n} sharpe_net2x", mi.loc[(n, "oos", "net_2x"), "sharpe"], po.loc[n, "sharpe_net2x"])
    cmp(f"portfolio_oos.csv {n} ann_excess_geo", a["ann_return_geo"], po.loc[n, "ann_excess_geo"])
    cmp(f"portfolio_oos.csv {n} vol", a["ann_vol"], po.loc[n, "vol"])
    cmp(f"portfolio_oos.csv {n} max_dd_excess", a["max_drawdown"], po.loc[n, "max_dd_excess"])

CHAIRS = {"Yellen": ("2014-02-03", "2018-02-03"), "Powell": ("2018-02-05", "2026-05-21"),
          "Warsh": ("2026-05-22", "2099-12-31")}


def chair_check(path, lo, hi, seriesmap, tag):
    t = pd.read_csv(path)
    for _, r in t.iterrows():
        if r["series"] not in seriesmap:
            continue
        df, first = seriesmap[r["series"]]
        a, b = CHAIRS[r["chair"]]
        a, b = max(a, lo), min(b, hi)
        sub = win(df, (a, b), first)
        x = sub["net_1x"].dropna()
        st = stats(x, sub["turnover"].loc[x.index] if "turnover" in sub else None)
        lbl = f"{tag} {r['series']}/{r['chair']}"
        if len(x) != r["n_days"] or str(x.index[0].date()) != r["start"] or str(x.index[-1].date()) != r["end"]:
            mismatches.append({"what": f"{lbl} window", "mine": len(x), "reported": int(r["n_days"])})
        cmp(f"{lbl} sharpe_net1x", st["sharpe"], r["sharpe_net1x"])
        if "net_2x" in sub:
            cmp(f"{lbl} sharpe_net2x", sharpe(sub["net_2x"].dropna()), r["sharpe_net2x"])
            cmp(f"{lbl} sharpe_gross", sharpe(sub["gross"].dropna()), r["sharpe_gross"])
            cmp(f"{lbl} turnover_per_year", st["turnover_per_year"], r["turnover_per_year"])
        for k, kk in (("ann_return_arith", "ann_excess_arith"), ("ann_return_geo", "ann_excess_geo"), ("ann_vol", "vol"),
                      ("max_drawdown", "max_dd_excess"), ("nw_t", "nw_t")):
            cmp(f"{lbl} {kk}", st[k], r[kk])


chair_check(RUN / "by_chair_oos.csv", "2024-10-03", "2026-10-02",
            {"T4xE1": (src["T4xE1"], first_t4), "VariantA_frozen(T0fxE1)": (src["VariantA_frozen(T0fxE1)"], first_va)},
            "by_chair_oos.csv")

sens = pd.read_csv(RUN / "sens_scheduled_only_oos.csv")
r = sens[sens["derisk_list"] == "registered_101_dates"].iloc[0]
for k, kk in (("sharpe", "sharpe_net1x"), ("ann_return_arith", "ann_excess_arith"), ("ann_return_geo", "ann_excess_geo"),
              ("ann_vol", "vol"), ("max_drawdown", "max_dd_excess"), ("nw_t", "nw_t"), ("turnover_per_year", "turnover_per_year")):
    cmp(f"sens_scheduled_only_oos registered {kk}", o1[k], r[kk])
cmp("sens_scheduled_only_oos registered sharpe_net2x", o2["sharpe"], r["sharpe_net2x"])
cmp("sens_scheduled_only_oos registered sharpe_gross", og["sharpe"], r["sharpe_gross"])

# ---------------------------------------------------------------- 3) oos_concentration.csv
conc = pd.read_csv(R / "oos_concentration.csv")
conc_mine = {}
for name in src:
    first = first_t4 if name == "T4xE1" else first_va if name.startswith("VariantA") else None
    x = win(src[name], "oos", first)["net_1x"].dropna()
    subsets = {"oos, all days": x}
    for k in (1, 5, 10, 20):
        subsets[f"oos without its last {k} days"] = x.iloc[:-k]
    subsets["oos, Powell (to 2026-05-21)"] = x.loc[:"2026-05-21"]
    subsets["oos, Warsh (from 2026-05-22)"] = x.loc["2026-05-22":]
    for y in (2024, 2025, 2026):
        subsets[f"oos, calendar {y}"] = x.loc[str(y)]
    for sname, s in subsets.items():
        row = conc[(conc["series"] == name) & (conc["subset"] == sname)].iloc[0]
        lbl = f"oos_concentration {name}/{sname}"
        cum = float(np.prod(1 + s.to_numpy()) - 1)
        conc_mine[f"{name}/{sname}"] = {"n": len(s), "cum": cum, "sharpe": sharpe(s), "arith": s.mean() * ANN,
                                        "sum": float(s.sum())}
        if len(s) != row["n_days"]:
            mismatches.append({"what": f"{lbl} n_days", "mine": len(s), "reported": row["n_days"]})
        cmp(f"{lbl} cum_excess_return", cum, row["cum_excess_return"])
        cmp(f"{lbl} ann_return_arith", s.mean() * ANN, row["ann_return_arith"])
        cmp(f"{lbl} sharpe", sharpe(s), row["sharpe"])
    top = x.sort_values(ascending=False).iloc[:5]
    share = float(top.sum() / x.sum())
    row = conc[(conc["series"] == name) & conc["subset"].str.startswith("share of")].iloc[0]
    cmp(f"oos_concentration {name} top5 share", share, row["value"])
    if set(row["days"].split()) != {str(t.date()) for t in top.index}:
        mismatches.append({"what": f"oos_concentration {name} top5 days", "mine": [str(t.date()) for t in top.index],
                           "reported": row["days"]})
    conc_mine[f"{name}/top5"] = {"share": share, "days": [str(t.date()) for t in top.index]}

# ---------------------------------------------------------------- 4) consistency.json + IS vs committed
cj = json.loads((R / "consistency.json").read_text(encoding="utf-8"))
wa = pd.read_csv(C / "windows_all.csv").set_index(["combo", "window"])
is_diffs = []
for name, combo, first in (("T4xE1", "T4xE1", first_t4), ("VariantA_frozen(T0fxE1)", "T0fxE1", first_va)):
    for w in ("selection", "validation", "full_is"):
        c = wa.loc[(combo, w)]
        sub = win(src[name], w, first)
        st1 = stats(sub["net_1x"], sub["turnover"])
        lbl = f"committed windows_all {combo}/{w}"
        pairs = {"sharpe_net1x": st1["sharpe"], "sharpe_net2x": sharpe(sub["net_2x"]), "sharpe_gross": sharpe(sub["gross"]),
                 "ann_excess_arith": st1["ann_return_arith"], "ann_excess_geo": st1["ann_return_geo"], "vol": st1["ann_vol"],
                 "max_dd_excess": st1["max_drawdown"], "nw_t": st1["nw_t"], "turnover_per_year": st1["turnover_per_year"],
                 "n_days": st1["n_days"]}
        for k, v in pairs.items():
            cmp(f"{lbl} {k}", v, c[k])
            is_diffs.append(abs(v - c[k]))
report["IS_full_series_vs_committed_windows_all_max_abs"] = max(is_diffs)

# all 10 combos (net 1x) from the run's IS combo parquet, vs committed windows_all
ac = pd.read_parquet(RUN / "daily_excess_all_combos_is.parquet")
summ = json.loads((C / "summary_is.json").read_text(encoding="utf-8"))
fpd = summ["first_position_dates"]
for combo in ac.columns:
    for w in ("selection", "validation", "full_is"):
        x = win(ac[combo], w, pd.Timestamp(fpd[combo])).dropna()
        c = wa.loc[(combo, w)]
        lbl = f"committed windows_all {combo}/{w} [from all_combos parquet]"
        cmp(f"{lbl} sharpe_net1x", sharpe(x), c["sharpe_net1x"])
        cmp(f"{lbl} ann_excess_arith", x.mean() * ANN, c["ann_excess_arith"])
        cmp(f"{lbl} ann_excess_geo", geo(x), c["ann_excess_geo"])
        cmp(f"{lbl} vol", x.std(ddof=1) * math.sqrt(ANN), c["vol"])
        cmp(f"{lbl} max_dd_excess", maxdd(x), c["max_dd_excess"])
        cmp(f"{lbl} nw_t", nw_t(x), c["nw_t"])
        if len(x) != c["n_days"]:
            mismatches.append({"what": f"{lbl} n_days", "mine": len(x), "reported": int(c["n_days"])})

# full-run series IS part vs IS-only run series, and vs the frozen snapshot
t4is = pd.read_parquet(RUN / "daily_T4xE1_is.parquet")
snap_t4 = pd.read_parquet(SNAP / "daily_T4xE1_is.parquet")
snap_ac = pd.read_parquet(SNAP / "daily_excess_all_combos_is.parquet")
snap_sig = pd.read_parquet(SNAP / "signals_entry_session.parquet")
run_sig = pd.read_parquet(RUN / "signals_entry_session.parquet")


def frame_diff(a, b):
    if not a.index.equals(b.index) or list(a.columns) != list(b.columns):
        return {"same_shape": False, "a": list(a.shape), "b": list(b.shape)}
    d = (a - b).abs()
    nan_mismatch = int((a.isna() != b.isna()).sum().sum())
    return {"same_shape": True, "max_abs": float(np.nanmax(d.to_numpy())) if d.notna().any().any() else 0.0,
            "nan_pattern_mismatch": nan_mismatch}


report["run_T4xE1_full_IS_part_vs_run_T4xE1_is"] = frame_diff(t4.loc[:"2024-10-02"], t4is)
report["run_T4xE1_is_vs_snapshot"] = frame_diff(t4is, snap_t4)
report["run_all_combos_is_vs_snapshot"] = frame_diff(ac, snap_ac)
report["run_signals_vs_snapshot"] = frame_diff(run_sig, snap_sig)
report["VariantA_full_ex1_vs_all_combos_T0fxE1"] = float((va["ex1"].reindex(ac.index) - ac["T0fxE1"]).abs().max())
report["T4xE1_full_ex1_vs_all_combos_T4xE1"] = float((t4["ex1"].reindex(ac.index) - ac["T4xE1"]).abs().max())

# committed files vs run IS files and snapshot (byte/number level)
filecmp = {}
for f in ("windows_all.csv", "selection.csv", "portfolio.csv", "by_chair_is.csv", "sens_scheduled_only_is.csv",
          "portfolio_info.json"):
    for other, tag in ((RUN, "run"), (SNAP, "snapshot")):
        a, b = C / f, other / f
        if f.endswith(".csv"):
            x, y = pd.read_csv(a), pd.read_csv(b)
            nums = x.select_dtypes("number").columns
            same_non_num = bool(x.drop(columns=nums).astype(str).equals(y.drop(columns=nums).astype(str)))
            filecmp[f"{f} vs {tag}"] = {"same_shape": x.shape == y.shape, "non_numeric_equal": same_non_num,
                                        "max_abs": float((x[nums] - y[nums]).abs().max().max())}
        else:
            filecmp[f"{f} vs {tag}"] = {"equal": json.loads(a.read_text()) == json.loads(b.read_text())}
report["committed_vs_run_and_snapshot_files"] = filecmp


def flat(d, p=""):
    o = {}
    for k, v in d.items():
        if isinstance(v, dict):
            o.update(flat(v, f"{p}{k}."))
        else:
            o[f"{p}{k}"] = v
    return o


s_run = flat(json.loads((RUN / "summary_is.json").read_text(encoding="utf-8")))
s_com = flat(summ)
s_snap = flat(json.loads((SNAP / "summary_is.json").read_text(encoding="utf-8")))
report["summary_is_run_vs_committed_differing_keys"] = sorted(k for k in set(s_run) | set(s_com) if s_run.get(k) != s_com.get(k))
report["summary_is_snapshot_vs_committed_differing_keys"] = sorted(k for k in set(s_snap) | set(s_com) if s_snap.get(k) != s_com.get(k))

# portfolio IS vs committed portfolio.csv
pc = pd.read_csv(C / "portfolio.csv").set_index(["portfolio", "window"])
for n in ("core_ER_6", "core_ER_6+T4xE1"):
    for w in ("selection", "validation", "full_is"):
        c = pc.loc[(n, w)]
        sub = win(src[n], w)
        x1 = sub["net_1x"].dropna()
        lbl = f"committed portfolio.csv {n}/{w}"
        cmp(f"{lbl} sharpe_net1x", sharpe(x1), c["sharpe_net1x"])
        cmp(f"{lbl} sharpe_net2x", sharpe(sub["net_2x"].dropna()), c["sharpe_net2x"])
        cmp(f"{lbl} ann_excess_geo", geo(x1), c["ann_excess_geo"])
        cmp(f"{lbl} vol", x1.std(ddof=1) * math.sqrt(ANN), c["vol"])
        cmp(f"{lbl} max_dd_excess", maxdd(x1), c["max_dd_excess"])
        if len(x1) != c["n_days"]:
            mismatches.append({"what": f"{lbl} n_days", "mine": len(x1), "reported": int(c["n_days"])})

# by_chair_is.csv (T4xE1, VariantA frozen from full series; T0v2xE1 net 1x only from the combo parquet)
t0v2 = pd.DataFrame({"net_1x": ac["T0v2xE1"]})
chair_check(C / "by_chair_is.csv", "2016-01-04", "2024-10-02",
            {"T4xE1": (src["T4xE1"], first_t4), "VariantA_frozen(T0fxE1)": (src["VariantA_frozen(T0fxE1)"], first_va),
             "VariantA_2015warmup(T0v2xE1)": (t0v2, pd.Timestamp(fpd["T0v2xE1"]))}, "committed by_chair_is.csv")

# summary_is.json numbers
g = wa
cmp("summary_is selection_sharpe_net1x", sharpe(win(src["T4xE1"], "selection", first_t4)["net_1x"]), summ["selection_sharpe_net1x"])
cmp("summary_is validation_sharpe_net1x", sharpe(win(src["T4xE1"], "validation", first_t4)["net_1x"]), summ["validation_sharpe_net1x"])
cmp("summary_is full_is_sharpe_net2x", sharpe(win(src["T4xE1"], "full_is", first_t4)["net_2x"]), summ["full_is_sharpe_net2x"])
sel_sr = {k: sharpe(win(ac[k], "selection", pd.Timestamp(fpd[k])).dropna()) for k in
          ("T1xE1", "T1xE2", "T2xE1", "T2xE2", "T3xE1", "T3xE2", "T4xE1", "T4xE2")}
chosen_mine = max(sel_sr, key=sel_sr.get)
if chosen_mine != summ["chosen"]:
    mismatches.append({"what": "chosen combo", "mine": chosen_mine, "reported": summ["chosen"]})
val_mine = sharpe(win(src["T4xE1"], "validation", first_t4)["net_1x"])
full2x_mine = sharpe(win(src["T4xE1"], "full_is", first_t4)["net_2x"])
passed_mine = bool(val_mine > 0 and full2x_mine > 0.5)
if passed_mine != summ["decision_rule_passed"]:
    mismatches.append({"what": "decision_rule_passed", "mine": passed_mine, "reported": summ["decision_rule_passed"]})
cmp("summary_is validation_vs_target_0.7", val_mine - 0.7, summ["validation_vs_target_0.7"])
for k in sel_sr:
    cmp(f"summary_is dsr trial sharpe {k}", sel_sr[k], summ["dsr"]["trial_sharpes_used"][list(sel_sr).index(k)])
x_full = win(src["T4xE1"], "full_is")["net_1x"]
pnl22, tot = float(x_full.loc["2022"].sum()), float(x_full.sum())
fz = summ["falsifiers"]
cmp("summary_is falsifiers share_full_is_pnl_from_2022", pnl22 / tot, fz["share_full_is_pnl_from_2022"])
cmp("summary_is falsifiers full_is_pnl_sum", tot, fz["full_is_pnl_sum"])
cmp("summary_is falsifiers pnl_2022_sum", pnl22, fz["pnl_2022_sum"])
for k, v in fz["T3_vs_T1_T2"].items():
    for w, val in v.items():
        cmp(f"summary_is falsifiers T3_vs_T1_T2 {k}/{w}", sharpe(win(ac[k], w, pd.Timestamp(fpd[k])).dropna()), val)
zz = run_sig[["z_T2", "z_T3"]].loc["2016-01-04":"2024-10-02"].dropna()
cmp("summary_is corr_zT2_zT3_full_is", np.corrcoef(zz["z_T2"], zz["z_T3"])[0, 1], fz["corr_zT2_zT3_full_is"])
cm = run_sig[["C_T2", "M_dgs2"]].loc["2016-01-04":"2024-10-02"].dropna()
cmp("summary_is corr_CT2_M_full_is", np.corrcoef(cm["C_T2"], cm["M_dgs2"])[0, 1], fz["corr_CT2_M_full_is"])
cmp("summary_is T3_beta_last", run_sig["T3_beta"].dropna().iloc[-1], fz["T3_beta_last"])
both = pd.concat([t4["ex1"], src["core_ER_6"]["net_1x"]], axis=1).loc["2016-01-04":"2024-10-02"].dropna()
cmp("summary_is corr_chosen_vs_core_ER_6_full_is", np.corrcoef(both.iloc[:, 0], both.iloc[:, 1])[0, 1],
    summ["corr_chosen_vs_core_ER_6_full_is"])
both_o = pd.concat([t4["ex1"], src["core_ER_6"]["net_1x"]], axis=1).loc["2024-10-03":"2026-10-02"].dropna()
corr_oos = float(np.corrcoef(both_o.iloc[:, 0], both_o.iloc[:, 1])[0, 1])

# DSR (Bailey & Lopez de Prado), own implementation
srs = summ["dsr"]["trial_sharpes_used"]
var = float(np.var(srs, ddof=1))
cmp("summary_is dsr var_sr_ann", var, summ["dsr"]["var_sr_ann"])
EG = 0.5772156649015329


def dsr(x, n, v, bias=True):
    x = np.asarray(x, float)
    T = len(x)
    sr0 = math.sqrt(v) * ((1 - EG) * norm.ppf(1 - 1 / n) + EG * norm.ppf(1 - 1 / (n * math.e))) if n > 1 else 0.0
    srd = x.mean() / x.std(ddof=1)
    d = x - x.mean()
    m2 = (d ** 2).mean()
    g3 = (d ** 3).mean() / m2 ** 1.5
    g4 = (d ** 4).mean() / m2 ** 2
    if not bias:
        from scipy.stats import kurtosis, skew
        g3 = skew(x, bias=False)
        g4 = kurtosis(x, fisher=False, bias=False)
    z = (srd - sr0 / math.sqrt(ANN)) * math.sqrt(T - 1) / math.sqrt(1 - g3 * srd + (g4 - 1) / 4 * srd ** 2)
    return float(norm.cdf(z)), sr0


x_sel = win(src["T4xE1"], "selection")["net_1x"]
var8 = float(np.var(list(sel_sr.values()), ddof=1))
dsr_mine = {}
for bias in (True, False):
    dsr_mine[f"bias={bias}"] = {
        "selection_window": dsr(x_sel, 11, var, bias), "full_is": dsr(x_full, 11, var, bias),
        "sens_n10_dedup": dsr(x_sel, 10, var, bias), "sens_var_from_8_combos_only": dsr(x_sel, 11, var8, bias),
        "psr_vs_0_selection": dsr(x_sel, 1, var, bias)}
best = None
for tag, dm in dsr_mine.items():
    err = max(abs(dm[k][0] - summ["dsr"][k]["dsr"]) / summ["dsr"][k]["dsr"] for k in dm)
    if best is None or err < best[1]:
        best = (tag, err)
report["dsr_recompute"] = {t: {k: {"dsr": v[0], "sr0_ann": v[1]} for k, v in dm.items()} for t, dm in dsr_mine.items()}
report["dsr_best_convention"] = {"convention": best[0], "max_rel_err": best[1]}
for k, (vv, sr0) in dsr_mine[best[0]].items():
    cmp(f"summary_is dsr {k} dsr", vv, summ["dsr"][k]["dsr"])
    cmp(f"summary_is dsr {k} sr0_ann", sr0, summ["dsr"][k]["sr0_ann"])

# ---------------------------------------------------------------- 5) printed claims (README / build report / summary.md)
T = lambda w, b="net_1x", s="T4xE1": mi.loc[(s, w, b)]
claims = [
    # T4xE1 table rows: Sharpe 1x/2x/gross, arith %, vol %, maxDD %, turnover, hit %
    *[(f"T4xE1 {w} {k}", v, p, sc) for w, vals in {
        "selection": ("0.154", "0.053", "0.269", "1.25", "8.11", "-16.1", "35.0", "49.4"),
        "validation": ("0.687", "0.664", "0.721", "10.00", "14.56", "-17.8", "15.9", "50.4"),
        "full_is": ("0.441", "0.387", "0.507", "5.00", "11.33", "-18.8", "26.8", "49.8"),
        "oos": ("0.607", "0.544", "0.687", "3.82", "6.30", "-6.6", "17.7", "49.9")}.items()
      for k, v, p, sc in zip(("sharpe1x", "sharpe2x", "sharpeg", "arith", "vol", "maxdd", "turn", "hit"),
                             (T(w)["sharpe"], T(w, "net_2x")["sharpe"], T(w, "gross")["sharpe"], T(w)["ann_return_arith"],
                              T(w)["ann_vol"], T(w)["max_drawdown"], T(w)["turnover_per_year"], T(w)["hit_rate"]),
                             vals, (1, 1, 1, 100, 100, 100, 1, 100))],
    ("T4xE1 oos 2x arith", T("oos", "net_2x")["ann_return_arith"], "3.42", 100),
    ("T4xE1 oos 2x maxdd", T("oos", "net_2x")["max_drawdown"], "-6.8", 100),
    ("T4xE1 oos summary 3.8% excess", T("oos")["ann_return_arith"], "3.8", 100),
    ("T4xE1 oos summary 6.3% vol", T("oos")["ann_vol"], "6.3", 100),
    ("T4xE1 oos total return incl T-bill (geo)", T("oos")["ann_total_return_geo"], "7.9", 100),
    ("T4xE1 oos NW t", T("oos")["nw_t"], "0.84", 1),
    *[(f"{s} {w} {b} sharpe", T(w, b, s)["sharpe"], p, 1) for s, w, vals in (
        ("core_ER_6", "full_is", ("0.998", "0.878", "1.118")), ("core_ER_6", "oos", ("0.601", "0.456", "0.746")),
        ("core_ER_6+T4xE1", "full_is", ("1.038", "0.909", "1.173")), ("core_ER_6+T4xE1", "oos", ("0.870", "0.703", "1.043")),
        ("VariantA_frozen(T0fxE1)", "full_is", ("0.355", "0.312", "0.411")),
        ("VariantA_frozen(T0fxE1)", "oos", ("-0.454", "-0.502", "-0.399"))) for b, p in zip(BASES, vals)],
    ("core_ER_6 oos arith", T("oos", s="core_ER_6")["ann_return_arith"], "3.45", 100),
    ("core_ER_6 oos vol", T("oos", s="core_ER_6")["ann_vol"], "5.74", 100),
    ("core_ER_6 oos maxdd", T("oos", s="core_ER_6")["max_drawdown"], "-4.7", 100),
    ("core+T4 oos arith", T("oos", s="core_ER_6+T4xE1")["ann_return_arith"], "4.97", 100),
    ("core+T4 oos vol", T("oos", s="core_ER_6+T4xE1")["ann_vol"], "5.72", 100),
    ("core+T4 oos maxdd", T("oos", s="core_ER_6+T4xE1")["max_drawdown"], "-5.3", 100),
    ("VariantA oos arith", T("oos", s="VariantA_frozen(T0fxE1)")["ann_return_arith"], "-4.95", 100),
    ("VariantA oos vol", T("oos", s="VariantA_frozen(T0fxE1)")["ann_vol"], "10.9", 100),
    ("VariantA oos maxdd", T("oos", s="VariantA_frozen(T0fxE1)")["max_drawdown"], "-15.6", 100),
    ("VariantA oos summary -0.45", T("oos", s="VariantA_frozen(T0fxE1)")["sharpe"], "-0.45", 1),
    ("overlay turnover OOS", T("oos", s="core_ER_6+T4xE1")["turnover_per_year"], "0.3", 1),
    ("fed sleeve turnover OOS", T("oos", s="core_ER_6+T4xE1")["fed_sleeve_turnover_per_year"], "5.8", 1),
    ("corr T4xE1 vs core IS", summ["corr_chosen_vs_core_ER_6_full_is"], "0.025", 1),
    ("corr T4xE1 vs core OOS", corr_oos, "-0.16", 1),
    ("share IS P&L from 2022 (74%)", pnl22 / tot, "74", 100),
    ("DSR selection 0.2225", dsr_mine[best[0]]["selection_window"][0], "0.2225", 1),
    ("DSR full IS 0.4361", dsr_mine[best[0]]["full_is"][0], "0.4361", 1),
    ("D-1 scheduled-only OOS 0.6076 (from csv)", float(sens.iloc[1]["sharpe_net1x"]), "0.6076", 1),
    ("registered OOS 0.6073", o1["sharpe"], "0.6073", 1),
]
cm_ = conc_mine
for nm, key, n, cum, sr in (("whole OOS", "T4xE1/oos, all days", 501, "7.5", "0.61"),
                            ("Powell", "T4xE1/oos, Powell (to 2026-05-21)", 409, "-3.1", "-0.36"),
                            ("Warsh", "T4xE1/oos, Warsh (from 2026-05-22)", 92, "10.9", "2.81"),
                            ("no last 10", "T4xE1/oos without its last 10 days", 491, "1.7", "0.17"),
                            ("no last 20", "T4xE1/oos without its last 20 days", 481, "-0.5", "-0.01")):
    claims += [(f"split {nm} cum", cm_[key]["cum"], cum, 100), (f"split {nm} sharpe", cm_[key]["sharpe"], sr, 1)]
    if cm_[key]["n"] != n:
        mismatches.append({"what": f"split {nm} days", "mine": cm_[key]["n"], "reported": n})
claims += [("top5 share 108%", cm_["T4xE1/top5"]["share"], "108", 100),
           ("core Powell", cm_["core_ER_6/oos, Powell (to 2026-05-21)"]["sharpe"], "0.97", 1),
           ("core+T4 Powell", cm_["core_ER_6+T4xE1/oos, Powell (to 2026-05-21)"]["sharpe"], "0.94", 1),
           ("core Warsh", cm_["core_ER_6/oos, Warsh (from 2026-05-22)"]["sharpe"], "-1.34", 1),
           ("core+T4 Warsh", cm_["core_ER_6+T4xE1/oos, Warsh (from 2026-05-22)"]["sharpe"], "0.53", 1)]
for lbl, v, p, sc in claims:
    cmp_printed(lbl, v, p, sc)
if not {"2026-09-23", "2026-09-24"} <= set(cm_["T4xE1/top5"]["days"]):
    mismatches.append({"what": "README: 2026-09-23 and 2026-09-24 among the five best days", "mine": cm_["T4xE1/top5"]["days"]})

# short-TLT claim on those two days (weights, not prices)
wr = t4["w_rate"]
report["w_rate_on_2026-09-23_24_and_prior_day"] = {str(k.date()): float(v) for k, v in wr.loc["2026-09-21":"2026-09-24"].items()}
report["w_rate_abs_max_full"] = float(wr.abs().max())
report["w_rate_min_oos"] = float(wr.loc["2024-10-03":"2026-10-02"].min())

# summary.md v2 section printed values (3 decimals)
smd = (REPO / "backtests/results/summary.md").read_text(encoding="utf-8")
sec = smd.split("## Fed communication v2")[1].split("## Press-conference")[0]
for line in sec.splitlines():
    m = re.match(r"\| (T\dxE\d) \| (\d{4}-\d\d-\d\d) \| (.*)\|$", line)
    if m:
        if m.group(2) != fpd[m.group(1)]:
            mismatches.append({"what": f"summary.md first_position_date {m.group(1)}", "mine": fpd[m.group(1)],
                               "reported": m.group(2)})
        cells = [c.strip() for c in m.group(3).split("|")]
        c = wa.loc[(m.group(1), "selection")]
        for k, cell in zip(("sharpe_net1x", "sharpe_net2x", "sharpe_gross", "ann_excess_arith", "vol", "max_dd_excess",
                            "turnover_per_year"), cells):
            x = win(ac[m.group(1)], "selection", pd.Timestamp(fpd[m.group(1)])).dropna()
            mine_v = {"sharpe_net1x": sharpe(x), "ann_excess_arith": x.mean() * ANN, "vol": x.std(ddof=1) * math.sqrt(ANN),
                      "max_dd_excess": maxdd(x)}.get(k, c[k])
            cmp_printed(f"summary.md selection {m.group(1)} {k}", mine_v, cell)
    m = re.match(r"\| (core_ER_6(?:\+T4xE1)?) \| (selection|validation|full_is) \| (.*)\|$", line)
    if m:
        cells = [c.strip() for c in m.group(3).split("|")]
        sub = win(src[m.group(1)], m.group(2))
        x1 = sub["net_1x"]
        for v, cell in zip((sharpe(x1), sharpe(sub["net_2x"]), geo(x1), x1.std(ddof=1) * math.sqrt(ANN), maxdd(x1)), cells):
            cmp_printed(f"summary.md portfolio {m.group(1)}/{m.group(2)}", v, cell)
for lbl, v, p in (("summary.md selection 0.154", sel_sr["T4xE1"], "0.154"), ("summary.md validation 0.687", val_mine, "0.687"),
                  ("summary.md full IS 2x 0.387", full2x_mine, "0.387"), ("summary.md diff -0.013", val_mine - 0.7, "-0.013"),
                  ("summary.md DSR sel 0.223", dsr_mine[best[0]]["selection_window"][0], "0.223"),
                  ("summary.md DSR full 0.436", dsr_mine[best[0]]["full_is"][0], "0.436"),
                  ("summary.md DSR n10 0.232", dsr_mine[best[0]]["sens_n10_dedup"][0], "0.232"),
                  ("summary.md PSR 0.634", dsr_mine[best[0]]["psr_vs_0_selection"][0], "0.634"),
                  ("summary.md 2022 share 0.739", pnl22 / tot, "0.739")):
    cmp_printed(lbl, v, p)

report["consistency_json"] = cj
report["n_compared"] = checks["n_compared"]
report["n_mismatches"] = len(mismatches)
report["mismatches"] = mismatches
report["max_rel_metrics_csv"] = None
(OUTDIR / "verify_report.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
print(json.dumps({k: v for k, v in report.items() if k not in ("dsr_recompute",)}, indent=1, default=str))
