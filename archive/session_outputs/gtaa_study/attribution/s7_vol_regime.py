"""Where does the IS Sharpe gain come from: return or volatility?  Per ETF, realised volatility and mean excess return
on days the filter was out vs in (IS and OOS), trailing 63-day vol known at each decision (point-in-time), and S3
compared with BH5 de-levered to S3's volatility.  Writes out/s7_*.csv."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

import lib as L

ohlc, rf = L.data()
close = ohlc["close"][L.TICK]
w_s3 = L.F2.s3_decisions("FWD")
w_bh = L.F2.s3_decisions("FWD", buy_and_hold=True)
held_s3 = w_s3.shift(1).fillna(0.0)
held_bh = w_bh.shift(1).fillna(0.0)
r = close.pct_change(fill_method=None)
ex = r.sub(rf, axis=0)
trail = r.rolling(63).std().shift(1) * math.sqrt(252)        # known before the day's return
PER = {"IS": ("2005-11-01", L.IS_END), "OOS": (L.OOS_START, L.OOS_END)}
rows = []
for p, (lo, hi) in PER.items():
    for t in L.TICK:
        el = held_bh.loc[lo:hi, t] > 0
        inn = (held_s3.loc[lo:hi, t] > 0) & el
        out = (held_s3.loc[lo:hi, t] == 0) & el
        e = ex.loc[lo:hi, t]
        rows.append({"period": p, "ticker": t, "days_in": int(inn.sum()), "days_out": int(out.sum()),
                     "vol_in": float(e[inn].std() * math.sqrt(252)), "vol_out": float(e[out].std() * math.sqrt(252)) if out.sum() > 1 else float("nan"),
                     "mean_ex_in_ann": float(e[inn].mean() * 252), "mean_ex_out_ann": float(e[out].mean() * 252) if out.any() else float("nan"),
                     "sharpe_in": float(e[inn].mean() / e[inn].std() * math.sqrt(252)),
                     "sharpe_out": float(e[out].mean() / e[out].std() * math.sqrt(252)) if out.sum() > 1 else float("nan"),
                     "trailing63_vol_in": float(trail.loc[lo:hi, t][inn].mean()),
                     "trailing63_vol_out": float(trail.loc[lo:hi, t][out].mean()) if out.any() else float("nan"),
                     "share_of_variance_in_out_days": float((e[out] ** 2).sum() / (e[el] ** 2).sum()) if out.any() else 0.0})
vr = pd.DataFrame(rows)
vr.to_csv(L.OUT / "s7_vol_regime_in_vs_out.csv", index=False)

d = pd.read_csv(L.OUT / "s1_daily_net_S3_BH5.csv", index_col=0, parse_dates=True)
s3, bh = d["S3"].dropna(), d["BH5"].dropna()
rfx = rf.reindex(s3.index)
cmp = []
for p, (lo, hi) in PER.items():
    a, b = (s3 - rfx).loc[lo:hi], (bh - rfx).loc[lo:hi]
    k = a.std() / b.std()
    b_lev = b * k                                         # BH5 excess scaled to S3's realised vol (ex post)
    nb = b_lev + rfx.loc[lo:hi]
    cmp.append({"period": p, "S3_vol": float(a.std() * math.sqrt(252)), "BH5_vol": float(b.std() * math.sqrt(252)),
                "scale_k": float(k), "S3_mean_ex_ann": float(a.mean() * 252), "BH5_scaled_mean_ex_ann": float(b_lev.mean() * 252),
                "S3_mdd": L.E.max_drawdown(s3.loc[lo:hi]), "BH5_scaled_mdd": L.E.max_drawdown(nb),
                "S3_avg_exposure": float(held_s3.loc[lo:hi].sum(axis=1).mean())})
pd.DataFrame(cmp).to_csv(L.OUT / "s7_S3_vs_vol_matched_BH5.csv", index=False)
pd.set_option("display.width", 250)
print(vr.round(3).to_string(index=False))
print(pd.DataFrame(cmp).round(4).to_string(index=False))
