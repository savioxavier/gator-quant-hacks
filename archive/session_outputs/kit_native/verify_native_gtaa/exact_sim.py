"""Share-level next_open simulation (fractional shares, cash at the T-bill) to test the engine-approximation claim,
plus an independent month-end decision check from my own probe run."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("<solo-repo>")
sys.path.insert(0, str(ROOT))
from src import config as C  # noqa: E402
from src import engine as E  # noqa: E402
from src import forward2 as F2  # noqa: E402

T = F2.S3_TICKERS
ohlc = E.load_ohlc(T, "FWD")
cal = ohlc["close"].index
rf = E.load_rf("FWD").reindex(cal).ffill().fillna(0.0).to_numpy()
close = ohlc["close"][T].ffill(limit=5)
open_ = ohlc["open"][T].ffill(limit=5).fillna(close)
cb = np.array([C.cost_bps(t) for t in T]) / 1e4


def sh(x):
    return x.mean() / x.std(ddof=1) * np.sqrt(252)


for name, bh in (("S3", False), ("BH5", True)):
    w = F2.s3_decisions("FWD", buy_and_hold=bh).reindex(cal).ffill().fillna(0.0).to_numpy()
    c, o = close.to_numpy(), open_.to_numpy()
    shares, cash, nav_prev = np.zeros(len(T)), 1.0, 1.0
    out = np.zeros(len(cal))
    for i in range(len(cal)):
        if i > 0:
            cash *= 1 + rf[i]                                   # T-bill accrues on the cash held over the day
            po = np.nan_to_num(o[i])
            nav_open = cash + shares @ po
            tgt = np.where(po > 0, w[i - 1] * nav_open / np.where(po > 0, po, 1), 0.0)
            trade = tgt - shares
            cost = np.abs(trade * po) @ cb
            cash -= trade @ po + cost
            shares = tgt
        nav = cash + shares @ np.nan_to_num(c[i])
        out[i] = nav / nav_prev - 1
        nav_prev = nav
    r = pd.Series(out, index=cal)
    ref = F2.returns(name, "FWD")
    rfs = pd.Series(rf, index=cal)
    for lo, hi in (("2005-11-01", "2024-10-02"), ("2024-10-03", "2026-10-02")):
        a, b = r.loc[lo:hi], ref.loc[lo:hi]
        print(name, lo, f"share-level ours {sh(a - rfs.loc[lo:hi]):.4f}  engine ours {sh(b - rfs.loc[lo:hi]):.4f}  "
              f"mad {((a - b).abs().mean() * 1e4):.3f} bp  max {((a - b).abs().max() * 1e4):.1f} bp  "
              f"ann diff {(((1 + b).prod() ** (252 / len(b))) - ((1 + a).prod() ** (252 / len(a)))) * 1e4:.2f} bp")
    if name == "S3":
        print("2008-09-19:", f"share-level {r.loc['2008-09-19'] * 1e4:.1f} bp, engine {ref.loc['2008-09-19'] * 1e4:.1f} bp")
