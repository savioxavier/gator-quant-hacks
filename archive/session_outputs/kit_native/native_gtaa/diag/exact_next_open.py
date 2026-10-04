"""Scratch: next_open returns with weights drifting from the open fill to the close (engine.simulate takes the
targets as the weights held overnight). Compared with the open-sized backtrader runs (rf = 0, no costs / project)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "<solo-repo>")
from src import config as C, engine as E, forward2 as F2   # noqa: E402

D = Path(__file__).resolve().parent


def exact(w_dec, ohlc, cost_bps):
    t = list(w_dec.columns)
    close, open_ = ohlc["close"][t].ffill(limit=5), ohlc["open"][t].ffill(limit=5)
    r_co = (open_ / close.shift(1) - 1).fillna(0.0).to_numpy()
    r_oc = (close / open_ - 1).fillna(0.0).to_numpy()
    w_new = w_dec.shift(1).fillna(0.0).to_numpy()
    cb = np.array([cost_bps.get(x, C.cost_bps(x)) for x in t]) / 1e4
    u = np.zeros(len(t))                 # weights at the previous close (drifted)
    out = np.zeros(len(w_dec))
    for i in range(len(w_dec)):
        on = u @ r_co[i]
        drifted = u * (1 + r_co[i]) / (1 + on)
        cost = np.abs(w_new[i] - drifted) @ cb
        day = w_new[i] @ r_oc[i]
        out[i] = (1 + on) * (1 - cost + day) - 1
        u = w_new[i] * (1 + r_oc[i]) / (1 - cost + day)
    return pd.Series(out, index=w_dec.index)


ohlc = E.load_ohlc(F2.S3_TICKERS, "FWD")
rf0 = E.load_rf("FWD") * 0.0
for name, bh in (("S3", False), ("BH5", True)):
    w = F2.s3_decisions("FWD", buy_and_hold=bh)
    for costs in ("none", "project"):
        cmap = {x: 0.0 for x in F2.S3_TICKERS} if costs == "none" else {}
        ex = exact(w, ohlc, cmap)
        eng = E.simulate(w, ohlc, rf0, exec="next_open", cost_bps=cmap or None)[0]
        bt_ = pd.read_csv(D / f"{name}_{costs}_open_sized.csv", index_col=0, parse_dates=True)["ret"]
        for lo, hi in (("2005-11-01", "2024-10-02"), ("2024-10-03", "2026-10-02")):
            b, x, e = bt_.loc[lo:hi], ex.loc[lo:hi], eng.loc[lo:hi]
            print(f"{name} {costs:7s} {lo[:4]}  bt-exact mad {((b - x).abs().mean() * 1e4):.4f} bp  "
                  f"engine-exact mad {((e - x).abs().mean() * 1e4):.4f} bp  engine-exact mean {(e - x).mean() * 252 * 1e4:.2f} bp/yr")
