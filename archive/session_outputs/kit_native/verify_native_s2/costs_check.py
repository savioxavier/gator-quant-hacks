"""Scratch: rebuild net weight, commissions, slippage and roll debits from the fill log; compare with the harness."""
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("<solo-repo>")
sys.path.insert(0, str(ROOT))
from src import engine as E
from src import forward2 as F2

V = Path(__file__).resolve().parent
NS = V.parent / "native_s2"
T = F2.S1_TICKERS
ohlc = E.load_ohlc(T, "FWD")
close = ohlc["close"][T].ffill().bfill()
roll = ohlc["roll"][T].fillna(0.0)

for tag, costs, ref in (("proj_none", "project", "s2_close_project"), ("la_none", "guide", "s2_close_guide")):
    log = pickle.load(open(V / f"{tag}_log.pkl", "rb"))
    s = pd.read_csv(V / f"{tag}.csv", index_col=0, parse_dates=True)
    b = pd.read_csv(NS / f"{ref}.csv", index_col=0, parse_dates=True)
    print(tag, "same series as builder's", ref, float((s["ret"] - b["ret"]).abs().max()))
    f = pd.DataFrame([x for x in log["fills"] if "refused" not in x])
    f["executed"] = pd.to_datetime(f["executed"])
    idx = s.index
    fills = f.pivot_table(index="executed", columns="name", values="size", aggfunc="sum").reindex(idx).fillna(0.0)
    fills = fills.reindex(columns=T).fillna(0.0)
    pos_end = fills.cumsum()                        # shares after close fills of day t
    held = pos_end.shift(1).fillna(0.0)             # shares held over return day t
    nav = 1e9 * (1 + s["ret"]).cumprod()
    c = close.reindex(idx)
    val_prev = held * c.shift(1)
    nw = (val_prev.sum(axis=1) / nav.shift(1)).fillna(0.0)
    print("  net weight max diff:", float((nw - s["net_weight"]).abs().max()))
    # return identity: ret_t = (sum held * dclose - comm_t - extra_t) / nav_{t-1}
    pnl = (held * c.diff()).sum(axis=1)
    comm = f.groupby("executed")["comm"].sum().reindex(idx).fillna(0.0)
    rate = (f["comm"] / (f["size"].abs() * f["price"]))
    bps = {t: (10.0 if costs == "guide" else F2.S1_COST_BPS[t]) for t in T}
    exp_rate = f["name"].map(bps) / 1e4 / (2 if costs == "guide" else 1)
    print("  commission rate max |actual - expected|:", float((rate - exp_rate).abs().max()))
    # extra costs: roll on day t = 2 |held_t * close_{t-1}| * side_bps; slippage on close fills at t (guide only)
    sb = pd.Series(bps) / 1e4
    roll_t = (2 * val_prev.abs() * roll.reindex(idx) * sb).sum(axis=1)
    slip = 0.0
    if costs == "guide":
        f["notional"] = f["size"].abs() * f["price"] * 0.0005
        slip = f.groupby("executed")["notional"].sum().reindex(idx).fillna(0.0)
    pred = (pnl - comm - roll_t - slip) / nav.shift(1)
    d = (pred - s["ret"]).iloc[1:]
    print("  return identity max |pred - harness| (bp):", float(d.abs().max() * 1e4), "mean", float(d.abs().mean() * 1e4))
    yrs = len(idx) / 252
    print(f"  per year / NAV: comm {float((comm / nav.shift(1)).sum() / yrs):.4%} roll {float((roll_t / nav.shift(1)).sum() / yrs):.4%}"
          f" slip {float((slip / nav.shift(1)).sum() / yrs) if costs == 'guide' else 0:.4%}")
