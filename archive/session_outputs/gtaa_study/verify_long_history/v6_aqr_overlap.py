"""AQR commodity proxy over the futures overlap, monthly idealised, to compare with v5 (our CME futures)."""
import numpy as np, pandas as pd
import vdata as D, vcore as C
aqr = D.aqr_commod_er().loc[:"2024-09-30"]; km = D.kf_monthly()
rf = km["rf"].reindex(aqr.index).fillna(0.0); tr = (aqr + rf).to_frame("C")
rules = ["SMA6","SMA8","SMA10","SMA12"]
res = {r: C.monthly_run(tr, rf, r, 1) for r in rules}; res["BH"] = C.monthly_run(tr, rf, None, 1)
for a in ["2011-06-01", "2013-01-01"]:
    bh = res["BH"].loc[a:]; sb = C.sharpe((bh.net-bh.rf).to_numpy(), 12)
    ds = [C.sharpe((res[r].loc[a:].net-res[r].loc[a:].rf).to_numpy(), 12) - sb for r in rules]
    print(a, "AQR BH", round(sb,3), "dSR", np.round(ds,3), "median", round(float(np.median(ds)),3))
