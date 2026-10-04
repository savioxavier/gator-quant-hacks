import sys; sys.path.insert(0, sys.argv[1])
import numpy as np, pandas as pd
from src import config as C, engine as E, forward2 as F2
# simulate vendor coverage of F_LE ending after 2026-10-20, exactly as download_databento._to_nyse pads it
p = C.DATA_DIR / "futures_daily.parquet"
f = pd.read_parquet(p); rf = E.load_rf("FWD")
m = (f.ticker == "F_LE")
le = f[m].set_index("date").sort_index()
cut = pd.Timestamp("2026-10-20")
lvl = le["close"].copy()
for i, d in enumerate(lvl.index):
    if d > cut:
        lvl.iloc[i] = lvl.iloc[i - 1] * (1 + rf.reindex([d]).ffill().iloc[0])
le["close"] = le["open"] = le["high"] = le["low"] = lvl
le.loc[le.index > cut, ["volume", "roll"]] = 0.0
f = pd.concat([f[~m], le.reset_index()[f.columns]], ignore_index=True); f.to_parquet(p, index=False)
w = F2.s1_decisions("FWD"); s2 = F2.s2_decisions("FWD")
for t in ["2026-09-30", "2026-10-30", "2026-11-30", "2026-12-31"]:
    print(t, "S1 w[F_LE]=%.3f  S1 gross=%.2f  S2 w[F_LE]=%.3f" % (w.loc[t, "F_LE"], w.loc[t].abs().sum(), s2.loc[t, "F_LE"]))
_, _, ex = F2._futures_panel(F2.S1_TICKERS, "FWD")
vol = np.sqrt(ex.pow(2).ewm(com=F2.EWMA_COM, min_periods=60).mean() * 252)
print("EWMA vol F_LE at 10-20 %.4f, 12-31 %.4f" % (vol.loc["2026-10-20", "F_LE"], vol.loc["2026-12-31", "F_LE"]))
# extrapolate: zero returns for 12 more months -> vol multiplier
print("vol multiplier after 252 zero days: %.3f" % (60/61) ** (252/2))
