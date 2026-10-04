"""Commodities (AQR EW excess return) single-asset timing, lag 1 vs lag 2; pre-1926 cash set to 0 (signal on ER+rf level)."""
import numpy as np
import pandas as pd
import vdata as D
import vcore as C

aqr = D.aqr_commod_er().loc[:"2024-09-30"]
km = D.kf_monthly()
rf = km["rf"].reindex(aqr.index).fillna(0.0)
tr = (aqr + rf).rename("C")
rules = ["SMA6", "SMA8", "SMA10", "SMA12"]
for lag in (1, 2):
    res = {r: C.monthly_run(tr.to_frame(), rf, r, lag) for r in rules}
    res["BH"] = C.monthly_run(tr.to_frame(), rf, None, lag)
    st = max(v["net"].first_valid_index() for v in res.values())
    for a, b in [("1878-01-01", "1926-06-30"), ("1926-07-01", "1972-12-31"), ("1973-01-01", "2006-12-31"),
                 ("2007-01-01", "2024-09-30"), ("1878-01-01", "2024-09-30")]:
        a2 = max(pd.Timestamp(a), st)
        bh = res["BH"].loc[a2:b]
        sb = C.sharpe((bh.net - bh.rf).to_numpy(), 12)
        ds = [C.sharpe((res[r].loc[a2:b].net - res[r].loc[a2:b].rf).to_numpy(), 12) - sb for r in rules]
        exs = [(res[r].loc[a2:b].net - res[r].loc[a2:b].rf).to_numpy() for r in rules]
        ci = C.boot_median_dsr(exs, (bh.net - bh.rf).to_numpy(), 12, 3, B=1000)
        print(f"lag{lag} {a2.date()}..{b}: BH {sb:.3f} median dSR {np.median(ds):+.3f} CI [{ci[0]:+.2f},{ci[1]:+.2f}] {np.round(ds,3)}")
