import sys, numpy as np, pandas as pd
sys.path.insert(0, "<solo-repo>")
from src import engine as E, forward as F, ensemble as EN, config as C
from src.strategies import pct
o = E.load_ohlc(pct.TICKERS, "FWD")
cl = o["close"]
print("cal", cl.index[0], cl.index[-1], len(cl))
for t in pct.TICKERS:
    s = cl[t]; fv = s.first_valid_index()
    gaps = s.loc[fv:].isna().sum()
    og = o["open"][t].loc[fv:].isna().sum()
    print(t, fv.date(), "missing closes after start", gaps, "missing opens", og)
fr = F.stream_frames("F1", "FWD")
labels = list(fr["ex"].columns)
print(labels)
out = EN.combine(fr["ex"], fr["gr"], fr["rf"], labels, "minvar_lw", 0.08, False)
lam = out["lam"]; k = out["k"]
print("start", out["net"].index[0])
# leverage cap binding
exl, grl = fr["ex"][labels].fillna(0), fr["gr"][labels]
lamf = EN.stream_weights(fr["ex"], fr["gr"], labels, "minvar_lw")
c = (lamf * exl).sum(axis=1)
var = (c**2).ewm(span=63, min_periods=63).mean()
sig = np.sqrt(var*252).shift(2)
k0 = (0.08/sig).clip(upper=4)
grc = np.maximum(grl, grl.shift(1).fillna(0))
gs = (lamf*grc).sum(axis=1)
lev = (4/(k0*gs)).clip(upper=1).fillna(1)
idx = out["net"].index
print("days lev cap binds", int((lev.reindex(idx) < 1).sum()), "of", len(idx), " k at vol cap 4:", int((k0.reindex(idx) >= 4).sum()))
print("k quantiles", k.reindex(idx).describe())
print("lam head", lam.loc[idx[0]:].head(3))
W = None
for s in labels:
    h = fr["held"][s]
    print(s, "held cols", list(h.columns))
# gross of book
print(out["net"].head())
