"""Drawdown at matched realized volatility (ex-post rescale of the overlay to its base's IS vol; descriptive only)."""
import pandas as pd, numpy as np
from pathlib import Path
H = Path(__file__).resolve().parent
S = H.parent / "series"
IS_END = "2024-10-02"
def mdd(x):
    eq = (1 + x).cumprod(); return float((eq / eq.cummax() - 1).min())
rows = []
for s in ["ES", "ZN", "GC", "SB"]:
    for a, b in [("FB", "CV"), ("MM", "STATIC"), ("MM", "CV"), ("CV", "STATIC")]:
        xa = pd.read_parquet(S / f"rpm_{s}_{a}.parquet")["net_1x"].loc[:IS_END]
        xb = pd.read_parquet(S / f"rpm_{s}_{b}.parquet")["net_1x"].loc[:IS_END]
        k = xb.std() / xa.std()
        rows.append({"source": "futures_IS", "sleeve": s, "overlay": a, "base": b, "vol_a": xa.std()*252**.5, "vol_b": xb.std()*252**.5,
                     "mdd_a_raw": mdd(xa), "mdd_a_matched": mdd(xa * k), "mdd_b": mdd(xb)})
lh = pd.read_parquet(H / "out" / "longhist_series.parquet")
for s, start in [("EQ", "1927-08-02"), ("EQ", "1963-04-02"), ("SB", "1963-04-02"), ("BOND", "1963-04-02")]:
    for a, b in [("FB", "CV"), ("MM", "STATIC"), ("MM", "CV"), ("CV", "STATIC")]:
        xa = lh[f"LH_{s}_{a}|net_1x"].loc[start:IS_END]; xb = lh[f"LH_{s}_{b}|net_1x"].loc[start:IS_END]
        k = xb.std() / xa.std()
        rows.append({"source": f"longhist_{start[:4]}", "sleeve": s, "overlay": a, "base": b, "vol_a": xa.std()*252**.5, "vol_b": xb.std()*252**.5,
                     "mdd_a_raw": mdd(xa), "mdd_a_matched": mdd(xa * k), "mdd_b": mdd(xb)})
t = pd.DataFrame(rows); t["dd_cut_matched"] = 1 - t.mdd_a_matched / t.mdd_b
t.to_csv(H / "out" / "matched_vol_dd.csv", index=False)
print(t.round(3).to_string(index=False))
