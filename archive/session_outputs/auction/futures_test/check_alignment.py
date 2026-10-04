"""Spot-check of event alignment, gating, sizing and net duration exposure (no new variants)."""
import sys, os
sys.path.insert(0, "<solo-repo>")
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, pandas as pd
import auction_futures as AF
ohlc, rf, cal, calx, rex, a = AF.load_data()
pd.set_option("display.width", 250)
# 2y auction 2017-09-26 (announced 2017-09-21)
ev = a[a.term == 2]
w, er, fl, held = AF.sleeve_positions(ev, "F_ZT", None, (-9, 0), (1, 10), True, cal, calx, rex, 30 / 1.9)
e = ev[ev.auction_date == "2017-09-26"].iloc[0]
i = e.A_i
win = cal[i - 12:i + 13]
print("auction", e.auction_date.date(), "announced", e.announcemt_date.date(), "N_i-A_i", e.N_i - e.A_i)
print(pd.DataFrame({"k": np.arange(-12, 13), "held_ZT": w["F_ZT"].reindex(win).round(2).values}, index=win.date).T.to_string())
w2, *_ = AF.sleeve_positions(ev, "F_ZT", "F_ZN", (-9, 0), (1, 10), True, cal, calx, rex, 30 / 1.9)
print(pd.DataFrame({"ZT": w2["F_ZT"].reindex(win).round(2).values, "ZN": w2["F_ZN"].reindex(win).round(2).values}, index=win.date).T.to_string())
# engine turnover/cost for chosen and V1_all_t5
for vid in ["V1_all_t5", "V3_all_t10_x", "V1_all_t10", "V2_2y_t10"]:
    hg = pd.read_parquet(os.path.join(os.path.dirname(__file__), f"held_gross_{vid}.parquet"))["held_gross"]
    s = pd.read_parquet(f"{AF.SER}/{vid}.parquet")
    c = (s["gross"] - s["net_1x"]).loc[:"2024-10-02"]
    print(vid, "mean gross when live", round(hg[hg > 0].mean(), 2), "annual cost (1x) %", round(c.mean() * 252 * 100, 2),
          "annual gross excess %", round(s["gross"].loc[:"2024-10-02"].mean() * 252 * 100, 2),
          "vol %", round(s["net_1x"].loc[:"2024-10-02"].std() * np.sqrt(252) * 100, 2))
