"""Decision dates, execution lags and causality of forward test 2 on the SYNTHETIC data dir.
Prints decision/held WEIGHTS only (no performance statistic of any strategy on real history)."""
import os
import sys

sys.path.insert(0, sys.argv[1])           # repo copy
import numpy as np
import pandas as pd

from src import config as C
from src import engine as E
from src import forward2 as F2

assert "synth_data" in str(C.DATA_DIR), C.DATA_DIR
last = E.data_end("FWD")
print("data_end FWD:", last)
cal = E.trading_calendar("FWD")
print("month ends in forward window:", [str(d.date()) for d in F2._month_ends(cal) if d >= pd.Timestamp("2026-09-01")])

frozen = pd.read_csv(os.path.join(sys.argv[1], "forward", "positions2_for_2026-10-06.csv"))
for name, (fn, tickers, ex, cost) in F2.SPECS.items():
    w = fn("FWD")
    ohlc = E.load_ohlc(tickers, "FWD")
    rf = E.load_rf("FWD")
    net, gross, to, held, costs = E.simulate(w, ohlc, rf, exec=ex, cost_bps=cost)
    win = w.loc["2026-09-25":]
    chg = win.index[(win.diff().abs().sum(axis=1) > 1e-12)]
    hw = held.loc["2026-09-25":]
    hchg = hw.index[(hw.diff().abs().sum(axis=1) > 1e-12)]
    print(f"\n{name} ({ex}): decision changes on {[str(d.date()) for d in chg]}")
    print(f"{'':>{len(name)}}  held changes on     {[str(d.date()) for d in hchg]}")
    # lag check: held over t equals decision at t-2 (next_close) / t-1 (next_open)
    lag = 2 if ex == "next_close" else 1
    dec_aligned = w.reindex(held.index).ffill().fillna(0.0).shift(lag).fillna(0.0)
    print(f"{'':>{len(name)}}  max |held - decision shifted {lag}|: {float((held - dec_aligned).abs().max().max()):.2e}")
    # turnover spikes in the window (the month-end trades)
    tw = to.loc["2026-10-01":]
    print(f"{'':>{len(name)}}  top-turnover days: {[(str(d.date()), round(float(v), 3)) for d, v in tw.nlargest(4).items()]}")
    # first forward day's held weights vs the frozen positions file
    if name in F2.STRATEGIES:
        h = held.loc["2026-10-06"]
        h = h[h.abs() > 1e-12]
        fz = frozen[frozen["strategy"] == name].set_index("instrument")["weight_of_nav"]
        j = pd.concat([h.rename("held_synth"), fz.rename("frozen")], axis=1).fillna(0.0)
        print(f"{'':>{len(name)}}  held over 2026-10-06 vs frozen file: n={len(j)} max abs diff {float((j.iloc[:,0]-j.iloc[:,1]).abs().max()):.2e}")
    # roll costs charged on roll day in window
    if name in ("S1", "ES_10VOL"):
        rl = ohlc["roll"].loc["2026-10-01":]
        rd = rl.index[rl.sum(axis=1) > 0]
        print(f"{'':>{len(name)}}  roll days in window {[str(d.date()) for d in rd]}; costs there {[round(float(costs.loc[d])*1e4, 3) for d in rd]} bp")
