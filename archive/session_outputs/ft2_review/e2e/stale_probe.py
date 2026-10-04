import sys; sys.path.insert(0, sys.argv[1])
import pandas as pd
from src import config as C, engine as E, forward2 as F2
print("DATA_DIR", C.DATA_DIR, "data_end", E.data_end("FWD"))
rf = E.load_rf("FWD")
for n in F2.SPECS:
    fn, tk, ex, cost = F2.SPECS[n]
    w = fn("FWD"); ohlc = E.load_ohlc(tk, "FWD")
    net, gross, to, held, costs = E.simulate(w, ohlc, rf, exec=ex, cost_bps=cost)
    sl = slice("2026-10-06", None)
    risky = (gross - (1 - held.sum(axis=1)) * rf.reindex(gross.index).ffill()).loc[sl]
    lastvol = {t: str(ohlc["volume"][t][ohlc["volume"][t] > 0].last_valid_index().date()) for t in tk[:3]}
    print(f"{n}: forward days {len(net.loc[sl])}, days with zero risky P&L {(risky.abs() < 1e-12).sum()}, "
          f"mean gross exposure {held.loc[sl].abs().sum(axis=1).mean():.2f}, last close/vol>0 date of first tickers {lastvol}, "
          f"last non-NaN close {[str(ohlc['close'][t].last_valid_index().date()) for t in tk[:3]]}")
