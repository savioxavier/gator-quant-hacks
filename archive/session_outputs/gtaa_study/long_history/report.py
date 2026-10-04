"""Summaries on top of run_study.py output (no new strategy variants are chosen here).

  summary_median_ci.csv     bootstrap CI of the MEDIAN dSharpe across SMA 6/8/10/12 (paired, all four
                            rules resampled together) per key series and main period
  summary_out_state.csv     buy-and-hold excess return while each rule is OUT (what a short leg would earn),
                            with Newey-West t-stat
  summary_decades.csv       median-of-SMA dSharpe / dMaxDD by decade, key series
  summary_year_contrib.csv  calendar-year (timed - BH) for SMA10, top-5-year share of the cumulative gap
  summary_sign_counts.csv   how many asset x period cells have dSharpe > 0 (non-overlapping clean series)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lh_core as L  # noqa: E402
from run_study import PRE_OOS_END_D, PRE_OOS_END_M  # noqa: E402

DATA = HERE / "data"
OUT = HERE / "out"
SMAS = ["SMA6", "SMA8", "SMA10", "SMA12"]


def nw_t(x: np.ndarray, lags: int) -> float:
    x = np.asarray(x, float)
    n = len(x)
    if n < 10:
        return float("nan")
    e = x - x.mean()
    v = e @ e / n
    for k in range(1, lags + 1):
        w = 1 - k / (lags + 1)
        v += 2 * w * (e[k:] @ e[:-k]) / n
    return float(x.mean() / math.sqrt(v / n)) if v > 0 else float("nan")


def build():
    m = pd.read_parquet(DATA / "monthly.parquet")
    deq = pd.read_parquet(DATA / "daily_us_eq.parquet")
    dbd = pd.read_parquet(DATA / "daily_us_10y.parquet")
    rf = m["rf"]
    spec = {
        "US_EQ_D": ("daily", (deq["US_EQ"], deq["rf"]), None),
        "US_10Y_D": ("daily", (dbd["US_10Y"], dbd["rf"]), None),
        "GOLD_AVG_L2": ("monthly", m["GOLD_AVG"], 2),
        "COMMOD_M": ("monthly", m["COMMOD"], 1),
        "REIT_M": ("monthly", m["REIT"], 1),
        "INTL_M": ("monthly", m["INTL"], 1),
        "US_EQ_SHA_L2": ("monthly", m["US_EQ_SHA"], 2),
        "MA2_EQ_COMMOD": ("multi", m[["US_EQ", "COMMOD"]], 1),
        "MA2_EQ_BOND": ("multi", m[["US_EQ", "US_10Y"]], 1),
        "MA3_EQ_BOND_COMMOD": ("multi", m[["US_EQ", "US_10Y", "COMMOD"]], 1),
        "MA5_FABER_LIKE": ("multi", m[["US_EQ", "INTL", "US_10Y", "COMMOD", "REIT"]], 1),
    }
    out = {}
    for name, (kind, payload, lag) in spec.items():
        res = {}
        for rule in [None] + L.RULES:
            if kind == "daily":
                res[rule or "BH"] = L.run_daily_strict(*payload, rule)
            elif kind == "monthly":
                res[rule or "BH"] = L.run_monthly(payload, rf, rule, lag=lag)
            else:
                res[rule or "BH"] = L.run_multi_monthly(payload, rf, rule, lag=lag)
        start = max(r["pos"].first_valid_index() for r in res.values())
        if kind == "multi":
            start = max(start, max(r["net"].first_valid_index() for r in res.values()))
            idx_all = res["BH"].index
            start = idx_all[idx_all.get_loc(start) + 1]
        out[name] = (kind, {k: v.loc[start:] for k, v in res.items()})
    return out


MAIN = lambda monthly: [  # noqa: E731
    ("P0_pre1926", "1800-01-01", "1926-06-30"),
    ("P1_1926_1972", "1926-07-01", "1972-12-31"),
    ("P2_1973_2006_faber", "1973-01-01", "2006-12-31"),
    ("P3_2007_2024_postpub", "2007-01-01", str((PRE_OOS_END_M if monthly else PRE_OOS_END_D).date())),
    ("P3b_2009_2024_postpub_ex2008", "2009-01-01", str((PRE_OOS_END_M if monthly else PRE_OOS_END_D).date())),
    ("PRE_OOS_all", "1800-01-01", str((PRE_OOS_END_M if monthly else PRE_OOS_END_D).date())),
    ("P4_2024_10_latest_descriptive", "2024-10-03", "2100-01-01"),
]


def median_ci(res: dict, monthly: bool, a: str, b: str, B: int = 2000, seed: int = 11) -> dict:
    bh = res["BH"].loc[a:b]
    if len(bh) < 12 or (len(bh) < (24 if monthly else 400) and not a.startswith("2024")):
        return {}
    exb = (bh["net"] - bh["rf"]).to_numpy()
    exs = np.vstack([(res[r].loc[a:b]["net"] - res[r].loc[a:b]["rf"]).to_numpy() for r in SMAS])
    n = len(exb)
    f = n / L.years_of(bh.index, monthly)
    Lb = 3 if monthly else 63
    def dsr(ix=None):
        xb = exb if ix is None else exb[ix]
        sb = xb.mean(axis=-1) / xb.std(axis=-1, ddof=1)
        vals = []
        for k in range(4):
            xs = exs[k] if ix is None else exs[k][ix]
            vals.append(xs.mean(axis=-1) / xs.std(axis=-1, ddof=1) - sb)
        return np.median(np.vstack(vals), axis=0) * math.sqrt(f)
    point = float(np.ravel(dsr())[0])
    rng = np.random.default_rng(seed)
    nb = int(math.ceil(n / Lb))
    reps = []
    for s in range(0, B, 100):
        st = rng.integers(0, n, size=(100, nb))
        ix = ((st[:, :, None] + np.arange(Lb)[None, None, :]).reshape(100, -1)[:, :n]) % n
        reps.append(dsr(ix))
    reps = np.concatenate(reps)
    return {"median_d_sharpe": point, "ci_lo": float(np.percentile(reps, 2.5)),
            "ci_hi": float(np.percentile(reps, 97.5)), "boot_se": float(reps.std(ddof=1)),
            "boot_frac_le0": float((reps <= 0).mean()), "years": round(L.years_of(bh.index, monthly), 2)}


def main() -> None:
    runs = build()
    rows_ci, rows_out, rows_dec, rows_year = [], [], [], []
    for name, (kind, res) in runs.items():
        monthly = kind != "daily"
        for plab, a, b in MAIN(monthly):
            a2 = a if not (plab.startswith("P4") and monthly) else "2024-10-31"
            r = median_ci(res, monthly, a2, b)
            if r:
                rows_ci.append({"series": name, "period": plab, **r})
            # out-state BH excess (single-asset only)
            if kind != "multi":
                bh = res["BH"].loc[a2:b]
                if len(bh) < (24 if monthly else 400):
                    continue
                exb = (bh["net"] - bh["rf"]).to_numpy()
                f = len(exb) / L.years_of(bh.index, monthly)
                for rule in L.RULES:
                    pos = res[rule].loc[a2:b]["pos"].to_numpy()
                    o = pos < 0.5
                    if o.sum() < (6 if monthly else 120):
                        continue
                    # monthly-aggregate the daily series for the t-stat to reduce microstructure noise
                    rows_out.append({"series": name, "period": plab, "rule": rule, "frac_out": float(o.mean()),
                                     "bh_ex_ann_out": float(exb[o].mean() * f),
                                     "t_out": nw_t(exb[o], 3 if monthly else 21),
                                     "bh_ex_ann_in": float(exb[~o].mean() * f),
                                     "t_in": nw_t(exb[~o], 3 if monthly else 21),
                                     "bh_vol_out": float(exb[o].std(ddof=1) * math.sqrt(f)),
                                     "bh_vol_in": float(exb[~o].std(ddof=1) * math.sqrt(f)),
                                     "long_short_ann_ex": float((np.where(o, -1.0, 1.0) * exb).mean() * f)})
        # decades
        idx = res["BH"].index
        for dec in range(1870, 2030, 10):
            a = pd.Timestamp(f"{dec}-01-01")
            b = min(pd.Timestamp(f"{dec + 9}-12-31"), PRE_OOS_END_M if monthly else PRE_OOS_END_D)
            sel = (idx >= a) & (idx <= b)
            if sel.sum() < (24 if monthly else 500):
                continue
            bh = res["BH"].loc[sel]
            sb = L.stats(bh, monthly)
            ds, dd, dc = [], [], []
            for rule in SMAS:
                st = L.stats(res[rule].loc[sel], monthly, bh)
                ds.append(st["d_sharpe"]); dd.append(st["d_max_dd"]); dc.append(st["d_cagr"])
            st10 = L.stats(res["SMA10"].loc[sel], monthly, bh)
            stm = L.stats(res["MOM12"].loc[sel], monthly, bh)
            rows_dec.append({"series": name, "decade": f"{dec}s", "years": sb["years"], "bh_sharpe": sb["sharpe"],
                             "bh_cagr": sb["cagr"], "bh_max_dd": sb["max_dd"],
                             "median_SMA_d_sharpe": float(np.median(ds)), "median_SMA_d_cagr": float(np.median(dc)),
                             "median_SMA_d_max_dd": float(np.median(dd)), "SMA10_d_sharpe": st10["d_sharpe"],
                             "SMA10_sharpe_se": st10["sharpe_se"], "MOM12_d_sharpe": stm["d_sharpe"],
                             "SMA10_pct_invested": st10["pct_invested"]})
        # calendar-year contributions for SMA10 (pre-OOS)
        r10 = res["SMA10"]
        bh = res["BH"]
        end = PRE_OOS_END_M if monthly else PRE_OOS_END_D
        yt = (1 + r10["net"].loc[:end]).groupby(r10["net"].loc[:end].index.year).prod() - 1
        yb = (1 + bh["net"].loc[:end]).groupby(bh["net"].loc[:end].index.year).prod() - 1
        diff = (yt - yb).sort_values(ascending=False)
        total = float(np.log1p(yt).sum() - np.log1p(yb).sum())
        top5 = diff.head(5)
        top5_log = float((np.log1p(yt[top5.index]) - np.log1p(yb[top5.index])).sum())
        rows_year.append({"series": name, "years_n": len(diff), "cum_log_gap_preOOS": total,
                          "top5_years": ";".join(f"{y}:{v:+.3f}" for y, v in top5.items()),
                          "top5_log_gap": top5_log,
                          "gap_ex_top5": total - top5_log,
                          "worst5_years": ";".join(f"{y}:{v:+.3f}" for y, v in diff.tail(5).items()),
                          "frac_years_timed_beats_bh": float((diff > 0).mean())})
        print(name, "done", flush=True)
    pd.DataFrame(rows_ci).to_csv(OUT / "summary_median_ci.csv", index=False, float_format="%.5g")
    pd.DataFrame(rows_out).to_csv(OUT / "summary_out_state.csv", index=False, float_format="%.5g")
    pd.DataFrame(rows_dec).to_csv(OUT / "summary_decades.csv", index=False, float_format="%.5g")
    pd.DataFrame(rows_year).to_csv(OUT / "summary_year_contrib.csv", index=False, float_format="%.5g")

    # sign counts over non-overlapping clean single-asset cells (main pre-OOS periods)
    tab = pd.read_csv(OUT / "variants_full_table.csv")
    clean = {"US_EQ_D": None, "US_10Y_D": None, "GOLD_AVG_L2": None, "COMMOD_M": None, "REIT_M": None,
             "INTL_M": None, "US_EQ_SHA_L2": ["P0_pre1926"]}
    per = ["P0_pre1926", "P1_1926_1972", "P2_1973_2006_faber", "P3_2007_2024_postpub"]
    sc = []
    for rule in L.RULES:
        sub = tab[(tab.rule == rule) & tab.period.isin(per) & tab.series.isin(clean.keys())]
        sub = sub[[clean[s] is None or p in clean[s] for s, p in zip(sub.series, sub.period)]]
        sub = sub[sub.years >= 8]
        for p in per + ["ALL_4"]:
            ss = sub if p == "ALL_4" else sub[sub.period == p]
            sc.append({"rule": rule, "period": p, "cells": len(ss), "d_sharpe_pos": int((ss.d_sharpe > 0).sum()),
                       "median_d_sharpe": float(ss.d_sharpe.median()) if len(ss) else float("nan"),
                       "d_maxdd_better": int((ss.d_max_dd > 0).sum()),
                       "median_d_cagr": float(ss.d_cagr.median()) if len(ss) else float("nan")})
    pd.DataFrame(sc).to_csv(OUT / "summary_sign_counts.csv", index=False, float_format="%.5g")


if __name__ == "__main__":
    main()
