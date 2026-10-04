"""Headline table: SMA10, MOM12 and the median across SMA lengths per series and main period, with CIs."""
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out"
t = pd.read_csv(OUT / "variants_full_table.csv")
ci = pd.read_csv(OUT / "summary_median_ci.csv")
md = pd.read_csv(OUT / "medians_by_period.csv")
main = ["P0_pre1926", "P1_1926_1972", "P2_1973_2006_faber", "P3_2007_2024_postpub",
        "P3b_2009_2024_postpub_ex2008", "PRE_OOS_all", "P4_2024_10_latest_descriptive"]
rows = []
for (s, p), g in t[t.period.isin(main)].groupby(["series", "period"], sort=False):
    bh = g[g.rule == "BH"].iloc[0]
    daily = bh["kind"] == "daily"
    blk = "63" if daily else "3"
    for rule in ["SMA10", "MOM12"]:
        r = g[g.rule == rule].iloc[0]
        rows.append({"series": s, "period": p, "what": rule, "years": bh.years, "bh_sharpe": bh.sharpe,
                     "sharpe": r.sharpe, "d_sharpe": r.d_sharpe, "ci_lo": r[f"d_sharpe_lo_blk{blk}"],
                     "ci_hi": r[f"d_sharpe_hi_blk{blk}"], "bh_cagr": bh.cagr, "cagr": r.cagr,
                     "bh_vol": bh.ann_vol, "vol": r.ann_vol, "bh_max_dd": bh.max_dd, "max_dd": r.max_dd,
                     "bh_worst_month": bh.worst_month, "worst_month": r.worst_month,
                     "pct_invested": r.pct_invested, "switches": r.switches, "switches_per_year": r.switches_per_year,
                     "cost_drag_ann": r.cost_drag_ann, "sharpe_gross": r.sharpe_gross})
    m = md[(md.series == s) & (md.period == p) & (md["agg"] == "median_SMA6-12")]
    c = ci[(ci.series == s) & (ci.period == p)]
    if len(m):
        m = m.iloc[0]
        rows.append({"series": s, "period": p, "what": "median_SMA6-12", "years": bh.years, "bh_sharpe": bh.sharpe,
                     "sharpe": m.sharpe, "d_sharpe": m.d_sharpe,
                     "ci_lo": c.ci_lo.iloc[0] if len(c) else np.nan, "ci_hi": c.ci_hi.iloc[0] if len(c) else np.nan,
                     "bh_cagr": bh.cagr, "cagr": m.cagr, "bh_vol": bh.ann_vol, "vol": m.ann_vol,
                     "bh_max_dd": bh.max_dd, "max_dd": m.max_dd, "bh_worst_month": bh.worst_month,
                     "worst_month": m.worst_month, "pct_invested": m.pct_invested,
                     "switches_per_year": m.switches_per_year})
h = pd.DataFrame(rows)
h.to_csv(OUT / "headline.csv", index=False, float_format="%.4g")
pd.set_option("display.width", 300); pd.set_option("display.max_rows", 1000); pd.set_option("display.max_columns", 30)
h2 = h.copy(); h2["period"] = h2.period.str.slice(0, 12)
print(h2.drop(columns=["switches", "sharpe_gross"]).round(3).to_string(index=False))
