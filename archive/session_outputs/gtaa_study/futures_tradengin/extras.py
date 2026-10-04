"""Follow-ups on run_study outputs:
1. 'Better than ours?': paired comparison with the submitted strategy F1 and its futures twin F2 (frozen
   forward-test-1 code, read-only).
2. How unusual is a 2-year Sharpe of 0.70 for S3? Distribution of rolling 504-session Sharpes up to 2024-10-02
   (trade-ngin's default backtest covers the last 2 years: config defaults backtest.lookback_years = 2).
3. GTAA = 0.5 long-only + 0.5 long-short: correlation of the two halves and the share of the mean from each half.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

import lib as L
from src import forward as FW


def main():
    D = pd.read_parquet(L.OUT / "daily_returns.parquet")
    rf = D["rf|rf"]
    names = sorted({c.split("|")[0] for c in D.columns if c != "rf|rf"})
    X = pd.DataFrame({n: D[f"{n}|net"] - rf for n in names})
    G = pd.DataFrame({n: D[f"{n}|gross"] - rf for n in names})
    out = {}

    # 1. F1 / F2
    for nm in ("F1", "F2"):
        net = FW.returns(nm, "FWD")
        X[f"OURS_{nm}"] = net.reindex(X.index) - rf
    rows = []
    for wl, win in (("F1_own_IS_2005_2024", ("2005-01-03", L.IS_WIN[1])), ("IS_2011_2024", L.IS_WIN),
                    ("OOS_2024_2026", L.OOS_WIN)):
        for n in ["OURS_F1", "OURS_F2", "ETF_S3", "C1_FUT5_GTAA_20", "B1_GTAA_FUT_INSTR_FIXED", "D1_S1_LS_SIGN_TREND"]:
            x = X[n].loc[win[0]:win[1]].dropna()
            x = x.loc[x.ne(0).idxmax():] if (x != 0).any() else x
            yrs = len(x) / 252
            sr = L.sharpe(x)
            rows.append({"window": wl, "variant": n, "start": str(x.index[0].date()), "sharpe": sr,
                         "se": L.sr_se(sr, yrs), "ann_excess": float(x.mean() * 252),
                         "ann_vol": float(x.std() * math.sqrt(252))})
    ours = pd.DataFrame(rows)
    ours.to_csv(L.OUT / "vs_ours.csv", index=False)
    brow = []
    for wl, win in (("IS_2011_2024", L.IS_WIN), ("OOS_2024_2026", L.OOS_WIN)):
        cols = ["OURS_F1", "OURS_F2", "ETF_S3", "C1_FUT5_GTAA_20", "B1_GTAA_FUT_INSTR_FIXED"]
        Y = X[cols].loc[win[0]:win[1]].dropna()
        for Lb in (63, 21):
            S = L.block_bootstrap_sharpes(Y, L=Lb, B=2000, seed=5)
            pt = Y.mean() / Y.std() * math.sqrt(252)
            ci = {c: i for i, c in enumerate(cols)}
            for a, b in [("ETF_S3", "OURS_F1"), ("C1_FUT5_GTAA_20", "OURS_F2"), ("B1_GTAA_FUT_INSTR_FIXED", "OURS_F2"),
                         ("C1_FUT5_GTAA_20", "OURS_F1")]:
                d = S[:, ci[a]] - S[:, ci[b]]
                brow.append({"window": wl, "block": Lb, "a": a, "b": b, "diff": float(pt[a] - pt[b]),
                             "boot_se": float(d.std()), "ci95_lo": float(np.percentile(d, 2.5)),
                             "ci95_hi": float(np.percentile(d, 97.5)), "p_diff_le_0": float((d <= 0).mean())})
    pd.DataFrame(brow).to_csv(L.OUT / "vs_ours_bootstrap.csv", index=False)

    # 2. rolling 2-year Sharpe distribution (pre-OOS only)
    roll = []
    for n, start in [("ETF_S3", "2005-11-01"), ("ETF_BH5", "2005-11-01"), ("C1_FUT5_GTAA_20", L.IS_WIN[0]),
                     ("B1_GTAA_FUT_INSTR_FIXED", L.IS_WIN[0]), ("D1_S1_LS_SIGN_TREND", L.IS_WIN[0]),
                     ("D_EWMAC_7030_LS", L.IS_WIN[0])]:
        x = X[n].loc[start:L.IS_WIN[1]]
        r = (x.rolling(504).mean() / x.rolling(504).std() * math.sqrt(252)).dropna()
        oos = float(L.sharpe(X[n].loc[L.OOS_WIN[0]:L.OOS_WIN[1]]))
        roll.append({"variant": n, "n_windows": len(r), "min": float(r.min()), "p10": float(r.quantile(0.1)),
                     "median": float(r.median()), "p90": float(r.quantile(0.9)), "max": float(r.max()),
                     "oos_2y_sharpe": oos, "pct_of_IS_2y_windows_below_oos": float((r < oos).mean()),
                     "frac_2y_windows_ge_0.70": float((r >= 0.70).mean())})
    rollt = pd.DataFrame(roll)
    rollt.to_csv(L.OUT / "rolling_2y_sharpe_IS.csv", index=False)

    # 3. halves
    halves = []
    for g, lo, ls, win in [("B1_GTAA_FUT_INSTR_FIXED", "A1_RP_LONG_INSTR", "E1_LS_SMA10_INSTR", L.IS_WIN),
                           ("B4_GTAA_FUT_EQ_RATES_FIXED", "P2_RP_LONG_EQ_RATES", "E4_LS_SMA10_EQ_RATES", L.IS_WIN),
                           ("C1_FUT5_GTAA_20", "C3_FUT5_BH_20", "C5_FUT5_LS_20", L.IS_WIN),
                           ("ETF_S3", "ETF_BH5", "ETF_LS5", L.IS_WIN),
                           ("ETF_S3", "ETF_BH5", "ETF_LS5", L.ETF_IS_WIN),
                           ("C1_FUT5_GTAA_20", "C3_FUT5_BH_20", "C5_FUT5_LS_20", L.OOS_WIN),
                           ("ETF_S3", "ETF_BH5", "ETF_LS5", L.OOS_WIN)]:
        sl = slice(*win)
        mg, ml, ms = (G[c].loc[sl].mean() * 252 for c in (g, lo, ls))
        halves.append({"gtaa": g, "window": f"{win[0]}..{win[1]}", "gross_ann_excess_gtaa": mg,
                       "half_long_only": 0.5 * ml, "half_long_short": 0.5 * ms,
                       "share_from_long_half": 0.5 * ml / mg if mg != 0 else float("nan"),
                       "corr_long_vs_longshort_daily": float(G[lo].loc[sl].corr(G[ls].loc[sl])),
                       "sharpe_gtaa": L.sharpe(X[g].loc[sl]), "sharpe_long_only": L.sharpe(X[lo].loc[sl]),
                       "sharpe_long_short": L.sharpe(X[ls].loc[sl])})
    halves = pd.DataFrame(halves)
    halves.to_csv(L.OUT / "gtaa_halves.csv", index=False)

    # vol-matched IS comparison (scale each to 10% realised vol over 2011-2024; descriptive of magnitude only)
    vm = {}
    for n in ["ETF_S3", "C1_FUT5_GTAA_20", "B1_GTAA_FUT_INSTR_FIXED", "B4_GTAA_FUT_EQ_RATES_FIXED",
              "D1_S1_LS_SIGN_TREND", "D_EWMAC_7030_LS", "D_EWMAC_7030_LF", "A1_RP_LONG_INSTR", "REF_ES_10VOL"]:
        x = X[n].loc[L.IS_WIN[0]:L.IS_WIN[1]]
        s = 0.10 / (x.std() * math.sqrt(252))
        y = x * s
        eq = (1 + y + rf.loc[y.index]).cumprod()
        vm[n] = {"scale": float(s), "ann_excess_at_10vol": float(y.mean() * 252),
                 "max_dd_at_10vol": float((eq / eq.cummax() - 1).min())}
    out["vol_matched_IS"] = vm
    (L.OUT / "extras.json").write_text(json.dumps(out, indent=1))

    pd.set_option("display.width", 250, "display.max_columns", 20)
    print(ours.round(3).to_string(index=False))
    print(pd.DataFrame(brow).round(3).to_string(index=False))
    print(rollt.round(3).to_string(index=False))
    print(halves.round(4).to_string(index=False))
    print(pd.DataFrame(vm).T.round(3).to_string())


if __name__ == "__main__":
    main()
