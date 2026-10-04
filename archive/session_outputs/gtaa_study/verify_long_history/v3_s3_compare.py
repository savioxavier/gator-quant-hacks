"""Compare the long-history MA5 proxy with the tradable S3/BH5 (ETF, next-open) on the same window; US_EQ idealised vs strict."""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "<solo-repo>")
sys.path.insert(0, "<solo-repo>/src")
from src import forward2, engine  # noqa
import vcore as C
import vdata as D

s3 = forward2.returns("S3", "FWD")
b5 = forward2.returns("BH5", "FWD")
rf = engine.load_rf("FWD")
df = pd.concat([s3.rename("s3"), b5.rename("b5"), rf.rename("rf")], axis=1).dropna()
for a, b in [("2005-11-01", "2024-10-02"), ("2007-01-01", "2024-10-02"), ("2024-10-03", "2026-10-02")]:
    x = df.loc[a:b]
    e3, e5 = (x.s3 - x.rf).to_numpy(), (x.b5 - x.rf).to_numpy()
    sd = C.sharpe(e3, 252) - C.sharpe(e5, 252)
    m = (1 + x).groupby(x.index.to_period("M")).prod() - 1
    me3, me5 = (m.s3 - m.rf).to_numpy(), (m.b5 - m.rf).to_numpy()
    ci = C.boot_dsr(e3, e5, 252, 63, B=1000)
    print(f"{a}..{b}: daily S3 {C.sharpe(e3,252):.3f} BH5 {C.sharpe(e5,252):.3f} d {sd:+.3f} CI63 [{ci[0]:+.2f},{ci[1]:+.2f}]"
          f" | monthly S3 {C.sharpe(me3,12):.3f} BH5 {C.sharpe(me5,12):.3f} d {C.sharpe(me3,12)-C.sharpe(me5,12):+.3f}")

# US_EQ idealised monthly (lag 1) vs strict daily, 2007-2024 and pre-OOS, median SMA6-12
km = D.kf_monthly()
rules = ["SMA6", "SMA8", "SMA10", "SMA12"]
res = {r: C.monthly_run(km[["US_EQ"]], km["rf"], r, 1) for r in rules}
res["BH"] = C.monthly_run(km[["US_EQ"]], km["rf"], None, 1)
for a, b in [("1927-09-01", "2024-09-30"), ("2007-01-01", "2024-09-30")]:
    bh = res["BH"].loc[a:b]
    sb = C.sharpe((bh.net - bh.rf).to_numpy(), 12)
    ds = [C.sharpe((res[r].loc[a:b].net - res[r].loc[a:b].rf).to_numpy(), 12) - sb for r in rules]
    print(f"US_EQ monthly idealised {a}..{b}: BH {sb:.3f} median dSR {np.median(ds):+.3f} {np.round(ds,3)}")
