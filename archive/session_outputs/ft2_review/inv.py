import sys, os
sys.path.insert(0, r"<solo-repo>")
import numpy as np, pandas as pd
from src import engine as E, forward2 as F2, config as C
print("DATA_DIR", C.DATA_DIR, "data_end FWD", E.data_end("FWD"))
fd = pd.read_parquet(C.DATA_DIR / "futures_daily.parquet")
print("futures tickers", sorted(fd.ticker.unique()))
missing = sorted(set(F2.S1_TICKERS) - set(fd.ticker.unique()))
print("missing S1 tickers:", missing)
g = fd.groupby("ticker")
summ = pd.DataFrame({"first": g.date.min(), "last": g.date.max(), "n": g.size(),
                     "zero_vol_days": g.apply(lambda d: int((d.volume == 0).sum())),
                     "rolls": g.roll.sum()})
print(summ.loc[F2.S1_TICKERS].to_string())
ohlc = E.load_ohlc(F2.S1_TICKERS, "FWD")
c = ohlc["close"]
print("close NaN after first valid per ticker:")
for t in F2.S1_TICKERS:
    s = c[t]; fv = s.first_valid_index()
    print(t, int(s.loc[fv:].isna().sum()), end="; ")
print()
_, rf, ex = F2._futures_panel(F2.S1_TICKERS, "FWD")
# near-zero excess return days and longest runs
for t in F2.S1_TICKERS:
    s = ex[t].dropna()
    z = (s.abs() < 1e-12)
    runs = (z != z.shift()).cumsum()
    lr = z.groupby(runs).sum().max()
    exact0 = int((s == 0).sum())
    vv = ohlc["volume"][t].loc[s.index]
    zv = (vv == 0)
    rz = (zv != zv.shift()).cumsum(); lzv = zv.groupby(rz).sum().max()
    print(f"{t}: nearzero={int(z.sum())} exact0={exact0} longest_run={int(lr)} zero_vol={int(zv.sum())} longest_zero_vol_run={int(lzv)} last_close_date={c[t].last_valid_index().date()}")
etf = E.load_ohlc(F2.S3_TICKERS, "FWD")["close"]
print("ETF first/last:", {t: (str(etf[t].first_valid_index().date()), str(etf[t].last_valid_index().date()), int(etf[t].loc[etf[t].first_valid_index():].isna().sum())) for t in F2.S3_TICKERS})
rfs = E.load_rf("FWD"); print("rf last", rfs.index[-1].date(), "rf NaN", int(rfs.isna().sum()))
