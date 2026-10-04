"""Step 6: is 0.51 -> 0.70 evidence that the timing works?  Sharpe standard errors, paired block-bootstrap intervals for
S3 minus BH5 in each period, the in-sample distribution of 2-year S3 - BH5 Sharpe differences, and a comparison of
the OOS numbers with what the in-sample estimates predict.  Writes out/s5_*."""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
from scipy import stats as sps

import lib as L

ohlc, rf = L.data()
d = pd.read_csv(L.OUT / "s1_daily_net_S3_BH5.csv", index_col=0, parse_dates=True)
s3, bh = d["S3"].dropna(), d["BH5"].dropna()
rfx = rf.reindex(s3.index)
ex = pd.DataFrame({"S3": s3 - rfx, "BH5": bh - rfx})
PER = {"IS": ("2005-11-01", L.IS_END), "OOS": (L.OOS_START, L.OOS_END)}

out = {"analytic": {}, "bootstrap": [], "memmel_se_diff": {}}
for p, (lo, hi) in PER.items():
    e = ex.loc[lo:hi]
    yrs = len(e) / 252
    for k in ("S3", "BH5"):
        sr = float(L.sr_of(e[k].to_numpy()))
        out["analytic"][f"{k}_{p}"] = {"sharpe": sr, "years": yrs, "se": L.sharpe_se(sr, yrs),
                                       "ci95": [sr - 1.96 * L.sharpe_se(sr, yrs), sr + 1.96 * L.sharpe_se(sr, yrs)]}
    out["memmel_se_diff"][p] = L.memmel_se_diff(e["S3"], e["BH5"])
    out["analytic"][f"corr_S3_BH5_{p}"] = float(e["S3"].corr(e["BH5"]))
    for block in (21, 63):
        res = L.paired_bootstrap(e["S3"], e["BH5"], block=block, reps=10000, seed=2024 + block)
        res["period"] = p
        out["bootstrap"].append(res)

# generic SE of a 2-year Sharpe at the S3 numbers
out["se_2y_sharpe"] = {f"SR={sr:.2f}": L.sharpe_se(sr, 2.0) for sr in (0.0, 0.51, 0.70, 0.82)}

# How surprising is the OOS S3 Sharpe given the IS estimate?  (difference of two independent estimates)
is_sr, oos_sr = out["analytic"]["S3_IS"]["sharpe"], out["analytic"]["S3_OOS"]["sharpe"]
se_comb = math.sqrt(out["analytic"]["S3_IS"]["se"] ** 2 + out["analytic"]["S3_OOS"]["se"] ** 2)
out["oos_vs_is_S3"] = {"diff": oos_sr - is_sr, "se": se_comb, "z": (oos_sr - is_sr) / se_comb}
is_b, oos_b = out["analytic"]["BH5_IS"]["sharpe"], out["analytic"]["BH5_OOS"]["sharpe"]
se_b = math.sqrt(out["analytic"]["BH5_IS"]["se"] ** 2 + out["analytic"]["BH5_OOS"]["se"] ** 2)
out["oos_vs_is_BH5"] = {"diff": oos_b - is_b, "se": se_b, "z": (oos_b - is_b) / se_b}
# change of the S3 - BH5 gap between periods (bootstrap SEs, 63-day blocks, independent periods)
b63 = {r["period"]: r for r in out["bootstrap"] if r["block_days"] == 63}
gap_change = b63["OOS"]["d_sr"] - b63["IS"]["d_sr"]
gap_se = math.sqrt(b63["OOS"]["d_sr_boot_se"] ** 2 + b63["IS"]["d_sr_boot_se"] ** 2)
out["gap_change_OOS_minus_IS"] = {"value": gap_change, "se": gap_se, "z": gap_change / gap_se}

# rolling 2-year (504-day) windows inside the in-sample period, stepped monthly (21 days): S3 SR, BH5 SR, difference
e = ex.loc[PER["IS"][0]:PER["IS"][1]]
win, step = 504, 21
rows = []
for s in range(0, len(e) - win + 1, step):
    blk = e.iloc[s:s + win]
    a, b = float(L.sr_of(blk["S3"].to_numpy())), float(L.sr_of(blk["BH5"].to_numpy()))
    rows.append({"start": blk.index[0].date(), "end": blk.index[-1].date(), "S3": a, "BH5": b, "diff": a - b})
roll = pd.DataFrame(rows)
roll.to_csv(L.OUT / "s5_rolling_2y_IS.csv", index=False)
oos = {"S3": out["analytic"]["S3_OOS"]["sharpe"], "BH5": out["analytic"]["BH5_OOS"]["sharpe"]}
oos["diff"] = oos["S3"] - oos["BH5"]
out["rolling_2y_IS"] = {
    "n_windows_overlapping": len(roll),
    "S3_sharpe_pct": {q: float(roll["S3"].quantile(q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)},
    "BH5_sharpe_pct": {q: float(roll["BH5"].quantile(q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)},
    "diff_pct": {q: float(roll["diff"].quantile(q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)},
    "frac_windows_S3_sharpe_ge_oos": float((roll["S3"] >= oos["S3"]).mean()),
    "frac_windows_diff_le_oos": float((roll["diff"] <= oos["diff"]).mean()),
    "frac_windows_S3_beats_BH5": float((roll["diff"] > 0).mean()),
    "frac_windows_BH5_sharpe_ge_oos": float((roll["BH5"] >= oos["BH5"]).mean()),
    "sd_S3_sharpe": float(roll["S3"].std()), "sd_diff": float(roll["diff"].std()),
}
# non-overlapping 2-year blocks (Nov 2005 onward), the honest count
nb = []
for s in range(0, len(e) - win + 1, win):
    blk = e.iloc[s:s + win]
    a, b = float(L.sr_of(blk["S3"].to_numpy())), float(L.sr_of(blk["BH5"].to_numpy()))
    nb.append({"start": str(blk.index[0].date()), "end": str(blk.index[-1].date()), "S3": a, "BH5": b, "diff": a - b})
out["nonoverlap_2y_IS"] = nb
# the IS advantage with and without the 2007-10..2009-12 crisis window
mask = ~((e.index >= "2007-10-01") & (e.index <= "2009-12-31"))
e2 = e[mask]
res = L.paired_bootstrap(e2["S3"], e2["BH5"], block=63, reps=10000, seed=99)
out["IS_ex_GFC_2007-10_2009-12"] = {k: res[k] for k in ("sr_a", "sr_b", "d_sr", "d_sr_ci95", "p_boot_d_sr_le_0",
                                                           "d_mean_excess_ann", "d_mean_excess_ci95")}
res = L.paired_bootstrap(e["S3"].loc["2007-10-01":"2009-12-31"], e["BH5"].loc["2007-10-01":"2009-12-31"],
                         block=63, reps=10000, seed=98)
out["IS_GFC_only_2007-10_2009-12"] = {k: res[k] for k in ("sr_a", "sr_b", "d_sr", "d_sr_ci95", "d_mean_excess_ann")}

(L.OUT / "s5_uncertainty.json").write_text(json.dumps(out, indent=1, default=str))
print(json.dumps({k: v for k, v in out.items() if k not in ("nonoverlap_2y_IS",)}, indent=1, default=str))
print(pd.DataFrame(nb).round(3).to_string(index=False))
