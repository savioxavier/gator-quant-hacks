"""Independent IEF bond-value check: sign(DGS10 - 1260-obs mean, known before d) at month-end d, filled close d+1,
10% ex-ante vol from trailing 252-day sample vol, 3 bp one-way."""
import math
from pathlib import Path

import numpy as np
import pandas as pd

D = Path("<home>/.cache/gqh")
et = pd.read_parquet(D / "etf_daily.parquet")
print(et.columns.tolist()[:10])
if "ticker" in et.columns:
    et["date"] = pd.to_datetime(et["date"])
    px = et[et.ticker == "IEF"].set_index("date").sort_index()
    col = "adj_close" if "adj_close" in px.columns else "close"
    p = px[col]
else:
    p = et["IEF"]
p = p.loc[:"2026-10-02"]
cal = p.index
rfd = pd.read_parquet(D / "rf_daily.parquet")
rfd = rfd.set_index(pd.to_datetime(rfd["date"])) if "date" in rfd.columns else rfd
rf = rfd["rf"].reindex(cal).ffill().fillna(0)
ex = p.pct_change(fill_method=None) - rf
fred = pd.read_parquet(D / "fred_daily.parquet")
fred = fred.set_index(pd.to_datetime(fred["date"])).sort_index()
s = fred["DGS10"].dropna()
dv = (s - s.rolling(1260, min_periods=1260).mean()).dropna()
pos = np.searchsorted(dv.index.values, cal.values, side="left") - 1
sig = pd.Series(np.where(pos >= 0, dv.values[np.clip(pos, 0, None)], np.nan), index=cal)
me = pd.DatetimeIndex(pd.Series(cal, index=cal).groupby([cal.year, cal.month]).max().values)
tgt = pd.Series(np.nan, index=cal)
for t in me:
    v = ex.loc[:t].tail(252).std() * math.sqrt(252)
    if np.isfinite(sig[t]) and sig[t] != 0 and np.isfinite(v) and v > 0 and ex.loc[:t].count() >= 60:
        tgt[t] = np.sign(sig[t]) * 0.10 / v
first = tgt.first_valid_index()
tgt = tgt.ffill().fillna(0)
fill = tgt.shift(1).fillna(0)
held = fill.shift(1).fillna(0)
r = ex.fillna(0)
port = held * r
drifted = held * (1 + r) / (1 + port)
cost = (fill - drifted).abs() * 3e-4
net = port - cost
for nm, a, b in (("IS", cal[cal.get_loc(first) + 2], "2024-10-02"), ("LATER", "2024-10-03", "2026-10-02"),
                 ("pre", cal[cal.get_loc(first) + 2], "2013-06-30"), ("post", "2013-07-01", "2024-10-02")):
    x = net.loc[a:b]
    print(nm, str(pd.Timestamp(a).date()), round(x.mean() / x.std() * math.sqrt(252), 3))
