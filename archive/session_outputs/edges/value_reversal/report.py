"""Statistics for every pre-declared variant of SPEC.md, series export, bootstrap comparisons."""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<solo-repo>")
sys.path.insert(0, str(REPO))
os.environ.setdefault("GQH_DATA_DIR", "<home>/.cache/gqh")
from src import engine as E  # noqa: E402

OUT = Path(__file__).resolve().parent
SER = OUT.parent / "series"
IS_END = pd.Timestamp("2024-10-02")
LATER_START = pd.Timestamp("2024-10-03")
LATER_END = pd.Timestamp("2026-10-02")
PUB = pd.Timestamp("2013-06-30")
TD = 252

R = pd.read_pickle(OUT / "results.pkl")
res, diag, VW1_START = R["results"], R["diag"], R["VW1_START"]
bench = pd.read_parquet(OUT / "bench_excess.parquet")

XS = ["VAL_XS_VW1", "VAL_XS_VW2", "VAL_XS_VW3", "MOM_XS", "COMBO_XS", "VAL_ALL", "COMBO_ALL"]

RULES = {
    "VAL_XS_VW1": "(a) primary: cross-sectional value, signal log(mean month-end level t-66..t-54 months) - log(level t); "
                  "commodities front-contract price, FX/equity excess-return index; rank weights in risk units within "
                  "COM(15)/FX(6)/EQ(4 US), each class 10% ex-ante, equal risk, book 10% ex-ante, gross<=5, monthly",
    "VAL_XS_VW2": "(a) variant: as VW1 with signal log(level t-60m) - log(level t)",
    "VAL_XS_VW3": "(a) variant: as VW1 with signal log(level t-66m) - log(level t-6m) (5.5y ago to 6m ago)",
    "MOM_XS": "reference: cross-sectional MOM2-12 (log excess-return index t-1m over t-12m), same construction, "
              "evaluated on the VW1 window",
    "MOM_XS_FULL": "reference: MOM_XS from its own first decision (2011-06)",
    "COMBO_XS": "(c) AMP combo: within COM/FX/EQ 0.5 value(VW1) + 0.5 MOM2-12 sleeves (10% each) rescaled to 10%, "
                "equal risk across classes, book 10% ex-ante",
    "VAL_ALL": "(a)+(b): VW1 classes plus the B1 bond sleeve (ZN) as a fourth equal-risk class",
    "COMBO_ALL": "(c) with bonds: COMBO_XS classes plus bond class 0.5 B1 + 0.5 sign(ZN MOM2-12), equal risk",
    "BOND_B1": "(b) primary: ZN position sign(DGS10[t-1] - mean DGS10 over trailing 1260 obs) at 10% ex-ante vol, monthly",
    "BOND_B2": "(b) variant: as B1 with the term spread DGS10 - DGS2",
    "BOND_B1_IEF": "(b) long-history check: B1 rule on IEF (ETF), 2005-2026, cost 3 bp",
}


def sharpe(x: pd.Series) -> float:
    x = x.dropna()
    return float(x.mean() / x.std() * math.sqrt(TD)) if len(x) > 20 and x.std() > 0 else float("nan")


def maxdd(x: pd.Series) -> float:
    eq = (1 + x.fillna(0.0)).cumprod()
    return float((eq / eq.cummax() - 1).min())


def yearly(x: pd.Series) -> pd.Series:
    g = x.groupby(x.index.year)
    y = g.apply(lambda s: (1 + s).prod() - 1)
    n = g.size()
    return y[n >= 126]


def monthly(x: pd.Series) -> pd.Series:
    return (1 + x).resample("ME").prod() - 1


def corr_d(a: pd.Series, b: pd.Series) -> float:
    df = pd.concat([a, b], axis=1).dropna()
    return float(df.corr().iloc[0, 1]) if len(df) > 60 else float("nan")


def corr_m(a: pd.Series, b: pd.Series) -> float:
    df = pd.concat([a, b], axis=1).dropna()
    if len(df) < 60:
        return float("nan")
    m = (1 + df).resample("ME").prod() - 1
    return float(m.corr().iloc[0, 1]) if len(m) > 12 else float("nan")


def window_stats(r: dict, start, end, ref: dict) -> dict:
    sl = slice(start, end)
    n1, n2, gr = r["net_1x"].loc[sl], r["net_2x"].loc[sl], r["gross"].loc[sl]
    turn, held = r["turnover"].loc[sl], r["held"].loc[sl]
    yrs = len(n1) / TD
    y = yearly(n1)
    roll = (n1.rolling(504).mean() / n1.rolling(504).std() * math.sqrt(TD)).dropna()
    out = {
        "start": str(n1.index[0].date()), "end": str(n1.index[-1].date()), "years": round(yrs, 2),
        "net_sharpe_1x": sharpe(n1), "net_sharpe_2x": sharpe(n2), "gross_sharpe": sharpe(gr),
        "ann_return_excess_cagr": float((1 + n1).prod() ** (1 / yrs) - 1) if yrs > 0 else float("nan"),
        "ann_mean_excess": float(n1.mean() * TD), "ann_vol": float(n1.std() * math.sqrt(TD)),
        "max_dd": maxdd(n1), "worst_year": float(y.min()) if len(y) else float("nan"),
        "worst_year_label": int(y.idxmin()) if len(y) else None,
        "pct_positive_years": float((y > 0).mean()) if len(y) else float("nan"), "n_years_counted": int(len(y)),
        "roll2y_p10": float(roll.quantile(0.10)) if len(roll) else float("nan"),
        "roll2y_p50": float(roll.quantile(0.50)) if len(roll) else float("nan"),
        "roll2y_p90": float(roll.quantile(0.90)) if len(roll) else float("nan"),
        "turnover_per_year": float(turn.sum() / yrs) if yrs > 0 else float("nan"),
        "mean_gross_leverage": float(held.abs().sum(axis=1).mean()),
        "nw_t": E.newey_west_tstat(n1),
        "skew": float(n1.skew()),
        "worst_month": float(monthly(n1).min()),
    }
    for k, s in ref.items():
        out[f"corr_d_{k}"] = corr_d(n1, s.loc[sl])
        out[f"corr_m_{k}"] = corr_m(n1, s.loc[sl])
    return out


def live_start(r: dict) -> pd.Timestamp:
    held = r["held"]
    live = held.abs().sum(axis=1) > 0
    return live.idxmax()


# reference series for correlations
ref = {"ES": bench["ES"], "S1": bench["S1"], "F2": bench["F2"]}
ref_xs = dict(ref)
ref_xs["MOM_XS"] = res["MOM_XS"]["net_1x"]
ref_xs["VAL_XS_VW1"] = res["VAL_XS_VW1"]["net_1x"]

rows = []
summary = {}
xs_start = live_start(res["VAL_XS_VW1"])
for name, r in res.items():
    start = xs_start if name in XS else live_start(r)
    for win, (a, b) in (("IS", (start, IS_END)), ("LATER", (LATER_START, LATER_END))):
        if name == "BOND_B1_IEF":
            rr = {k: v for k, v in r.items()}
            refs = ref
        else:
            rr = r
            refs = ref_xs
        st = window_stats(rr, a, b, refs)
        st.update({"candidate": name, "window": win, "kind": "variant"})
        rows.append(st)
    # pre/post publication split where possible (in-sample only)
    if start < PUB:
        for win, (a, b) in (("IS_prepub", (start, PUB)), ("IS_postpub", (PUB + pd.Timedelta(days=1), IS_END))):
            st = window_stats(r, a, b, ref)
            st.update({"candidate": name, "window": win, "kind": "variant"})
            rows.append(st)
for name, r in diag.items():
    start = xs_start if not name.startswith("BOND") else live_start(r)
    for win, (a, b) in (("IS", (start, IS_END)), ("LATER", (LATER_START, LATER_END))):
        st = window_stats(r, a, b, ref_xs)
        st.update({"candidate": f"diag_{name}", "window": win, "kind": "diagnostic"})
        rows.append(st)

tab = pd.DataFrame(rows)
front = ["candidate", "kind", "window", "start", "end", "years", "net_sharpe_1x", "net_sharpe_2x", "gross_sharpe",
         "ann_return_excess_cagr", "ann_vol", "max_dd", "worst_year", "worst_year_label", "pct_positive_years",
         "roll2y_p10", "roll2y_p50", "roll2y_p90", "turnover_per_year", "mean_gross_leverage", "nw_t"]
tab = tab[front + [c for c in tab.columns if c not in front]]
tab.to_csv(OUT / "value_reversal_table.csv", index=False, float_format="%.4f")

# value-momentum correlations inside each class (diagnostics) and across
vm = {}
for k in ("COM", "FX", "EQ"):
    a, b = diag[f"VAL_{k}"]["net_1x"], diag[f"MOM_{k}"]["net_1x"]
    vm[k] = {"IS_daily": corr_d(a.loc[xs_start:IS_END], b.loc[xs_start:IS_END]),
             "IS_monthly": corr_m(a.loc[xs_start:IS_END], b.loc[xs_start:IS_END]),
             "LATER_daily": corr_d(a.loc[LATER_START:], b.loc[LATER_START:])}
a, b = diag["BOND_B1"]["net_1x"], diag["BOND_TSMOM"]["net_1x"]
s0 = live_start(diag["BOND_B1"])
vm["BOND(B1 vs ZN TSMOM)"] = {"IS_daily": corr_d(a.loc[s0:IS_END], b.loc[s0:IS_END]),
                              "IS_monthly": corr_m(a.loc[s0:IS_END], b.loc[s0:IS_END]),
                              "LATER_daily": corr_d(a.loc[LATER_START:], b.loc[LATER_START:])}
a, b = res["VAL_XS_VW1"]["net_1x"], res["MOM_XS"]["net_1x"]
vm["ALL_XS(VAL_XS_VW1 vs MOM_XS)"] = {"IS_daily": corr_d(a.loc[xs_start:IS_END], b.loc[xs_start:IS_END]),
                                     "IS_monthly": corr_m(a.loc[xs_start:IS_END], b.loc[xs_start:IS_END]),
                                     "LATER_daily": corr_d(a.loc[LATER_START:], b.loc[LATER_START:])}


# paired circular block bootstrap of the Sharpe difference
def block_boot(a: pd.Series, b: pd.Series, block=63, n=5000, seed=7) -> dict:
    df = pd.concat([a, b], axis=1).dropna()
    x = df.to_numpy()
    T = len(x)
    rng = np.random.default_rng(seed)
    nb = int(math.ceil(T / block))
    diffs = np.empty(n)
    for i in range(n):
        st = rng.integers(0, T, nb)
        idx = (st[:, None] + np.arange(block)[None, :]).ravel()[:T] % T
        s = x[idx]
        m, sd = s.mean(0), s.std(0, ddof=1)
        sr = m / sd * math.sqrt(TD)
        diffs[i] = sr[0] - sr[1]
    obs = sharpe(df.iloc[:, 0]) - sharpe(df.iloc[:, 1])
    return {"obs_diff": float(obs), "p_diff_le_0": float((diffs <= 0).mean()),
            "ci90": [float(np.quantile(diffs, 0.05)), float(np.quantile(diffs, 0.95))], "n_days": int(T)}


boots = {}
sl = slice(xs_start, IS_END)
boots["COMBO_XS_vs_MOM_XS_IS"] = block_boot(res["COMBO_XS"]["net_1x"].loc[sl], res["MOM_XS"]["net_1x"].loc[sl])
boots["COMBO_ALL_vs_MOM_XS_IS"] = block_boot(res["COMBO_ALL"]["net_1x"].loc[sl], res["MOM_XS"]["net_1x"].loc[sl])
mixr = 0.5 * bench["S1"] + 0.5 * res["VAL_ALL"]["net_1x"]
boots["half_S1_half_VAL_ALL_vs_S1_IS"] = block_boot(mixr.loc[sl], bench["S1"].loc[sl])
mixr2 = 0.5 * bench["S1"] + 0.5 * res["VAL_XS_VW1"]["net_1x"]
boots["half_S1_half_VAL_XS_vs_S1_IS"] = block_boot(mixr2.loc[sl], bench["S1"].loc[sl])
mix_stats = {}
for lab, m in (("half_S1_half_VAL_ALL", mixr), ("half_S1_half_VAL_XS_VW1", mixr2), ("S1", bench["S1"])):
    mix_stats[lab] = {"IS_sharpe": sharpe(m.loc[sl]), "IS_maxdd": maxdd(m.loc[sl]),
                      "LATER_sharpe": sharpe(m.loc[LATER_START:LATER_END]), "LATER_maxdd": maxdd(m.loc[LATER_START:LATER_END])}

# median of the three pre-declared value windows
med = {}
for win in ("IS", "LATER"):
    sub = tab[(tab["candidate"].isin(["VAL_XS_VW1", "VAL_XS_VW2", "VAL_XS_VW3"])) & (tab["window"] == win)]
    med[win] = {"median_net_sharpe_1x": float(sub["net_sharpe_1x"].median()),
                "median_net_sharpe_2x": float(sub["net_sharpe_2x"].median())}

# ------------------------------------------------------------------ series export (daily excess returns, 3 columns)
COSTS_NOTE = ("realistic one-way bp: ES/NQ/YM 0.75, RTY 1.0, ZN 1.0, FX 0.75, CL/GC/SI/HG 1.5, NG/HO/RB/PL 2.5, "
              "ZC/ZS/ZW/ZL/ZM/LE/HE 4.0, IEF 3.0; roll days add one round trip; net_2x doubles every cost")
EXPORT = ["VAL_XS_VW1", "VAL_XS_VW2", "VAL_XS_VW3", "MOM_XS", "COMBO_XS", "VAL_ALL", "COMBO_ALL", "BOND_B1",
          "BOND_B2", "BOND_B1_IEF"]
for name in EXPORT:
    r = res[name]
    start = xs_start if name in XS else live_start(r)
    df = pd.DataFrame({"net_1x": r["net_1x"], "net_2x": r["net_2x"], "gross": r["gross"]}).loc[start:LATER_END]
    df.index.name = "date"
    stem = f"value_reversal_{name}"
    df.to_parquet(SER / f"{stem}.parquet")
    side = {
        "candidate": stem, "rule": RULES[name], "spec": "edges/value_reversal/SPEC.md",
        "columns": "daily excess return over the 3-month T-bill (futures index return includes T-bill accrual; rf subtracted)",
        "costs": COSTS_NOTE, "execution": "decision at month-end close d, filled at the close of d+1 (engine next_close)",
        "vol_scaling": "10% annualised ex-ante vol at each monthly decision using the sample covariance of the trailing "
                       "252 daily excess returns (min 60); instrument risk units use EWMA vol (centre of mass 60); gross <= 5",
        "in_sample": [str(start.date()), str(IS_END.date())], "later_window_descriptive": [str(LATER_START.date()), str(LATER_END.date())],
        "primary": name in ("VAL_XS_VW1", "COMBO_XS", "BOND_B1"),
    }
    (SER / f"{stem}.json").write_text(json.dumps(side, indent=2))

summary = {"xs_start": str(xs_start.date()), "vm_corr": vm, "bootstrap": boots, "mix_stats": mix_stats,
           "median_value_windows": med, "decision_counts": R["dec_counts"]}
(OUT / "summary.json").write_text(json.dumps(summary, indent=2))

pd.set_option("display.width", 250)
show = ["candidate", "window", "start", "years", "net_sharpe_1x", "net_sharpe_2x", "gross_sharpe", "ann_vol", "max_dd",
        "worst_year", "pct_positive_years", "roll2y_p10", "roll2y_p50", "roll2y_p90", "turnover_per_year",
        "mean_gross_leverage", "nw_t", "corr_d_ES", "corr_d_S1", "corr_d_F2", "corr_m_S1", "corr_d_MOM_XS"]
print(tab[show].round(2).to_string(index=False))
print(json.dumps(summary, indent=1))
