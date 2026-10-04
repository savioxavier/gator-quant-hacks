"""Run every variant of the long-history SMA / absolute-momentum timing study and write the full table.

Outputs (./out):
  variants_full_table.csv  one row per (series, rule, period) - EVERY variant computed, BH rows included
  medians_by_period.csv    median across SMA 6/8/10/12 and across all five rules, per series and period
  yearly_diff.csv          calendar-year return of timed minus buy-and-hold, every (series, rule)
  returns_monthly.parquet  monthly net returns of every variant (daily ones compounded)
  checks.txt               point-in-time checks and data validation notes
"""
from __future__ import annotations

import json
import sys
import zlib
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lh_core as L  # noqa: E402

DATA = HERE / "data"
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

PRE_OOS_END_M = pd.Timestamp("2024-09-30")
PRE_OOS_END_D = pd.Timestamp("2024-10-02")


def periods(idx: pd.DatetimeIndex, monthly: bool, extra: dict | None = None) -> list[tuple[str, pd.Timestamp, pd.Timestamp, str]]:
    end_pre = PRE_OOS_END_M if monthly else PRE_OOS_END_D
    p4_start = pd.Timestamp("2024-10-31") if monthly else pd.Timestamp("2024-10-03")
    out = [
        ("P0_pre1926", pd.Timestamp("1800-01-01"), pd.Timestamp("1926-06-30"), "main"),
        ("P1_1926_1972", pd.Timestamp("1926-07-01"), pd.Timestamp("1972-12-31"), "main"),
        ("P2_1973_2006_faber", pd.Timestamp("1973-01-01"), pd.Timestamp("2006-12-31"), "main"),
        ("P3_2007_2024_postpub", pd.Timestamp("2007-01-01"), end_pre, "main"),
        ("P3b_2009_2024_postpub_ex2008", pd.Timestamp("2009-01-01"), end_pre, "main"),
        ("PRE_OOS_all", pd.Timestamp("1800-01-01"), end_pre, "main"),
        ("P4_2024_10_latest_descriptive", p4_start, pd.Timestamp("2100-01-01"), "main"),
        ("FULL_incl_P4", pd.Timestamp("1800-01-01"), pd.Timestamp("2100-01-01"), "main"),
    ]
    for dec in range(1870, 2030, 10):
        a = pd.Timestamp(f"{dec}-01-01")
        b = min(pd.Timestamp(f"{dec + 9}-12-31"), end_pre)
        out.append((f"D{dec}s", a, b, "decade"))
    for k, (a, b) in (extra or {}).items():
        out.append((k, pd.Timestamp(a), pd.Timestamp(b), "calibration"))
    return out


def main(B: int = 1000) -> None:
    t0 = time.time()
    m = pd.read_parquet(DATA / "monthly.parquet")
    deq = pd.read_parquet(DATA / "daily_us_eq.parquet")
    dbd = pd.read_parquet(DATA / "daily_us_10y.parquet")
    rf = m["rf"]
    checks = []

    series = [
        # name, kind, payload, lag, note
        ("US_EQ_D", "daily", (deq["US_EQ"], deq["rf"]), None, "Ken French market TR, daily, strict next-close execution"),
        ("US_EQ_M", "monthly", m["US_EQ"], 1, "Ken French market TR, monthly, idealised month-end execution"),
        ("US_10Y_D", "daily", (dbd["US_10Y"], dbd["rf"]), None, "10y CMT TR rebuilt from DGS10, daily, strict next-close"),
        ("US_10Y_M", "monthly", m["US_10Y"], 1, "10y CMT TR rebuilt from DGS10, monthly, idealised"),
        ("GOLD_AVG_L2", "monthly", m["GOLD_AVG"], 2, "gold, World Bank monthly AVERAGE prices, lag 2 (bias-free, conservative)"),
        ("GOLD_AVG_L1", "monthly", m["GOLD_AVG"], 1, "gold, monthly AVERAGE prices, lag 1 (BIASED upward; calibration only)"),
        ("GOLD_ME_GLD", "monthly", m["GOLD_ME"], 1, "gold via GLD month-end closes, 2005+, idealised"),
        ("COMMOD_M", "monthly", m["COMMOD"], 1, "AQR equal-weight commodity futures ER + cash (1877-2025-05), our 15-future EW after; idealised"),
        ("REIT_M", "monthly", m["REIT"], 1, "FTSE Nareit All Equity REITs TR, idealised"),
        ("INTL_M", "monthly", m["INTL"], 1, "Ken French Ind_all USD (1975-1990-06) then Developed ex US, idealised"),
        ("US_EQ_SHA_L2", "monthly", m["US_EQ_SHA"], 2, "Shiller S&P composite, monthly AVERAGE prices + dividends, lag 2 (bias-free)"),
        ("US_EQ_SHA_L1", "monthly", m["US_EQ_SHA"], 1, "Shiller S&P composite, AVERAGE prices, lag 1 (BIASED; calibration only)"),
        ("MA2_EQ_COMMOD", "multi", m[["US_EQ", "COMMOD"]], 1, "1/2 US equity + 1/2 commodities, monthly, idealised"),
        ("MA2_EQ_BOND", "multi", m[["US_EQ", "US_10Y"]], 1, "1/2 US equity + 1/2 US 10y, monthly, idealised"),
        ("MA3_EQ_BOND_COMMOD", "multi", m[["US_EQ", "US_10Y", "COMMOD"]], 1, "1/3 each, monthly, idealised"),
        ("MA5_FABER_LIKE", "multi", m[["US_EQ", "INTL", "US_10Y", "COMMOD", "REIT"]], 1,
         "1/5 each of US eq, intl eq, US 10y, commodities, REITs (Faber's five classes), monthly, idealised"),
    ]
    calib = {
        "GOLD_AVG_L2": {"CAL_GLD_overlap": ("2006-02-01", "2024-09-30")},
        "GOLD_AVG_L1": {"CAL_GLD_overlap": ("2006-02-01", "2024-09-30")},
        "GOLD_ME_GLD": {"CAL_GLD_overlap": ("2006-02-01", "2024-09-30")},
        "US_EQ_SHA_L2": {"CAL_FF_overlap": ("1927-09-01", "2023-06-30")},
        "US_EQ_SHA_L1": {"CAL_FF_overlap": ("1927-09-01", "2023-06-30")},
        "US_EQ_M": {"CAL_FF_overlap": ("1927-09-01", "2023-06-30")},
        "MA5_FABER_LIKE": {"CAL_S3_IS_window": ("2005-11-01", "2024-09-30")},
    }

    rows, yearly, monthly_rets = [], [], {}
    for name, kind, payload, lag, note in series:
        res = {}
        if kind == "daily":
            R, rfd = payload
            for rule in [None] + L.RULES:
                res[rule or "BH"] = L.run_daily_strict(R, rfd, rule)
        elif kind == "monthly":
            for rule in [None] + L.RULES:
                res[rule or "BH"] = L.run_monthly(payload, rf, rule, lag=lag)
        else:
            for rule in [None] + L.RULES:
                res[rule or "BH"] = L.run_multi_monthly(payload, rf, rule, lag=lag)
        # common evaluation window: every rule has a position (and the multi BH is defined)
        start = max(r["pos"].first_valid_index() for r in res.values())
        if kind == "multi":
            start = max(start, max(r["net"].first_valid_index() for r in res.values()))
            # the first month of a multi run has no prior weights for turnover: start one month later
            idx_all = res["BH"].index
            start = idx_all[idx_all.get_loc(start) + 1]
        res = {k: v.loc[start:] for k, v in res.items()}
        for k, v in res.items():
            assert v["pos"].notna().all(), (name, k)
        monthly_flag = kind != "daily"
        bh = res["BH"]
        f_nom = 12 if monthly_flag else 252
        Lb = 3 if monthly_flag else 63
        Lb12 = 12 if monthly_flag else 252

        # ---------------- point-in-time checks
        if kind == "monthly":
            lvl = (1 + pd.concat([payload, rf], axis=1).dropna().iloc[:, 0]).cumprod()
            rfx = rf.reindex(lvl.index)
            for rule in L.RULES:
                bad = L.truncation_test(lvl, rfx, rule)
                r = res[rule]
                sig_shift_ok = bool(((r["pos"] - r["sig"].shift(lag)).abs().fillna(0) == 0).all())
                checks.append(f"{name:20s} {rule:6s} truncation mismatches={bad}  pos==sig.shift({lag}): {sig_shift_ok}")
        elif kind == "daily":
            R, rfd = payload
            full = res["SMA10"]
            for D in ["1931-06-15", "1987-10-20", "2008-10-01", "2020-03-16", "2024-10-02"]:
                Dt = pd.Timestamp(D)
                if Dt < R.index[0] + pd.Timedelta(days=500) or Dt > R.index[-1]:
                    continue
                for rule in ["SMA10", "MOM12"]:
                    tr = L.run_daily_strict(R.loc[:Dt], rfd.loc[:Dt], rule)
                    a = tr["pos"].loc[start:Dt]
                    b = res[rule]["pos"].loc[start:Dt]
                    checks.append(f"{name:20s} {rule:6s} truncated at {D}: positions identical up to D: "
                                  f"{bool((a.fillna(-1) == b.fillna(-1)).all())}")
            lag_ok = []
            for rule in L.RULES:
                r = res[rule]
                dd = r["dec_date"].dropna()
                ii = pd.Series(np.arange(len(r)), index=r.index)
                # sessions between decision date and the first return day using it (within the eval window)
                dd = dd[dd >= r.index[0]]
                lag_ok.append(int((ii.loc[dd.index].to_numpy() - ii.loc[pd.DatetimeIndex(dd.values)].to_numpy()).min()))
            checks.append(f"{name:20s} min sessions from decision close to first return day using it: {lag_ok} (must be >= 2)")

        # ---------------- statistics per period
        idx = bh.index
        for plabel, a, b, ptype in periods(idx, monthly_flag, calib.get(name)):
            sel = (idx >= a) & (idx <= b)
            if sel.sum() == 0:
                continue
            n_months = sel.sum() if monthly_flag else (idx[sel][-1] - idx[sel][0]).days / 30.44
            if plabel.startswith("P4"):
                pass
            elif n_months < 24:
                continue
            bsub = bh.loc[sel]
            for rule in ["BH"] + L.RULES:
                rsub = res[rule].loc[sel]
                st = L.stats(rsub, monthly_flag, None if rule == "BH" else bsub)
                row = {"series": name, "kind": kind, "rule": rule, "period": plabel, "period_type": ptype,
                       "exec": ("strict next-close (daily)" if kind == "daily" else
                                f"monthly lag {lag}" + (" (avg-price data)" if "AVG" in name or "SHA" in name else "")),
                       "note": note}
                row.update(st)
                if rule != "BH":
                    ex_a = (rsub["net"] - rsub["rf"]).to_numpy()
                    ex_b = (bsub["net"] - bsub["rf"]).to_numpy()
                    f = len(ex_a) / L.years_of(rsub.index, monthly_flag)
                    bt = L.block_boot(ex_a, ex_b, f, Lb, B=B, seed=zlib.crc32(f'{name}|{rule}|{plabel}'.encode()))
                    row.update({k + f"_blk{Lb}": v for k, v in bt.items()})
                    if ptype == "main":
                        bt12 = L.block_boot(ex_a, ex_b, f, Lb12, B=B, seed=zlib.crc32(f'{name}|{rule}|{plabel}|12'.encode()))
                        row.update({k + f"_blk{Lb12}": v for k, v in bt12.items()})
                rows.append(row)

        # ---------------- yearly differences and monthly return archive
        for rule in L.RULES:
            r = res[rule]
            yt = (1 + r["net"]).groupby(r.index.year).prod() - 1
            yb = (1 + bh["net"]).groupby(bh.index.year).prod() - 1
            for y in yt.index:
                yearly.append({"series": name, "rule": rule, "year": int(y), "timed": float(yt[y]),
                               "bh": float(yb[y]), "diff": float(yt[y] - yb[y]),
                               "pct_invested": float(r["pos"][r.index.year == y].mean())})
        for rule in ["BH"] + L.RULES:
            r = res[rule]
            mr = r["net"] if monthly_flag else (1 + r["net"]).groupby(r.index.to_period("M")).prod() - 1
            if not monthly_flag:
                mr.index = mr.index.to_timestamp(how="end").normalize()
            monthly_rets[f"{name}|{rule}"] = mr
        print(f"{name:20s} done  eval start {start.date()}  ({time.time() - t0:.0f}s)", flush=True)

    tab = pd.DataFrame(rows)
    tab.to_csv(OUT / "variants_full_table.csv", index=False, float_format="%.6g")
    pd.DataFrame(yearly).to_csv(OUT / "yearly_diff.csv", index=False, float_format="%.6g")
    pd.DataFrame(monthly_rets).to_parquet(OUT / "returns_monthly.parquet")

    # medians across SMA lengths (no picking) and across all five rules
    med_rows = []
    cols = ["sharpe", "d_sharpe", "cagr", "d_cagr", "ann_vol", "max_dd", "d_max_dd", "worst_month",
            "pct_invested", "switches_per_year", "exposure_matched_alpha", "timing_contrib_ann_gross"]
    for (s, p), g in tab[tab.rule != "BH"].groupby(["series", "period"], sort=False):
        bhrow = tab[(tab.series == s) & (tab.period == p) & (tab.rule == "BH")].iloc[0]
        for lab, sub in [("median_SMA6-12", g[g.rule.str.startswith("SMA")]), ("median_all5", g)]:
            r = {"series": s, "period": p, "agg": lab, "n_rules": len(sub), "years": float(bhrow["years"]),
                 "bh_sharpe": float(bhrow["sharpe"]), "bh_cagr": float(bhrow["cagr"]),
                 "bh_max_dd": float(bhrow["max_dd"]), "bh_worst_month": float(bhrow["worst_month"])}
            for c in cols:
                r[c] = float(sub[c].median())
            r["min_d_sharpe"] = float(sub["d_sharpe"].min())
            r["max_d_sharpe"] = float(sub["d_sharpe"].max())
            r["n_rules_d_sharpe_pos"] = int((sub["d_sharpe"] > 0).sum())
            med_rows.append(r)
    pd.DataFrame(med_rows).to_csv(OUT / "medians_by_period.csv", index=False, float_format="%.6g")
    (OUT / "checks.txt").write_text("\n".join(checks) + "\n", encoding="utf-8")
    n_var = tab[tab.rule != "BH"].groupby(["series", "rule"]).ngroups
    n_bh = tab[tab.rule == "BH"].groupby(["series"]).ngroups
    meta = {"timed_variants": n_var, "bh_baselines": n_bh, "rows": len(tab), "bootstrap_reps": B,
            "seconds": round(time.time() - t0, 1)}
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1))
    print(meta)


if __name__ == "__main__":
    main()
