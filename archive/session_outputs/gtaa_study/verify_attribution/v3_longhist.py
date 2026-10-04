import os, sys, math, numpy as np, pandas as pd
os.chdir(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ".")
from core import block_boot, sr_np, month_ends
f = pd.read_parquet("<home>/.cache/gqh/ff_daily.parquet").set_index("date"); f.index = pd.to_datetime(f.index)
f = f.loc[:"2004-12-31"]
lvl = (1 + f.Mkt_RF + f.RF).cumprod()
me = month_ends(f.index)
sma = lvl.loc[me].rolling(10).mean()
sig = (lvl.loc[me] > sma).astype(float).where(sma.notna())
dec = sig.reindex(f.index).ffill()
held = dec.shift(2)          # decided at close d, traded at close d+1, earns from d+2
trade = held.diff().abs().fillna(0)
ex_t = held * f.Mkt_RF - trade * 5e-4
ex_u = f.Mkt_RF.copy()
st = held.first_valid_index(); st = held.index[held.index.get_loc(st) + 1]
st = max(st, pd.Timestamp("1964-05-01"))
a = ex_t.loc[st:].dropna(); b = ex_u.loc[a.index]
print("window", a.index[0].date(), a.index[-1].date(), "timed SR %.3f untimed SR %.3f diff %.3f" % (sr_np(a.values), sr_np(b.values), sr_np(a.values) - sr_np(b.values)))
bs = block_boot(a.values, b.values, sr_np, 63, 3000)
print("CI", np.percentile(bs, [2.5, 97.5]).round(3), "exdiff/yr %.4f" % ((a - b).mean() * 252))
yr = (a - b).groupby(a.index.year).sum()
print("years timing helped frac %.2f; top3" % (yr > 0).mean(), yr.sort_values().tail(3).round(3).to_dict(), "sum ex top3 %.3f" % yr.sort_values().iloc[:-3].sum())
# check: lag sensitivity (same-day close trading would be lookahead; show what it does)
held0 = dec.shift(1); ex0 = held0 * f.Mkt_RF - held0.diff().abs().fillna(0) * 5e-4
print("next-close (d+1 return) variant SR %.3f" % sr_np(ex0.loc[a.index].values))
