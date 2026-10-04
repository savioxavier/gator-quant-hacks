"""Scratch: run gqh_equity_trend in the harness with all data after a cut perturbed; log orders, fills, decisions.

usage: lookahead_run.py <cut|none> <seed> <out_prefix> [book] [fill] [costs]
"""
import json
import pickle
import sys
from pathlib import Path

ROOT = Path("<solo-repo>")
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import backtrader as bt

from src import engine as E
from validation.starter_kit import base as B
from validation.starter_kit import run_in_starter as H

cut_s, seed, prefix = sys.argv[1], int(sys.argv[2]), sys.argv[3]
book = sys.argv[4] if len(sys.argv) > 4 else "S2"
fill = sys.argv[5] if len(sys.argv) > 5 else "next_close"
costs = sys.argv[6] if len(sys.argv) > 6 else "guide"

orig_ohlc, orig_rf = E.load_ohlc, E.load_rf
if cut_s != "none":
    cut = pd.Timestamp(cut_s)

    def load_ohlc(tickers=None, period="IS"):
        out = orig_ohlc(tickers, period)
        rng = np.random.default_rng(seed)
        after = out["close"].index > cut
        n = int(after.sum())
        for col in ("open", "high", "low", "close"):
            px = out[col].copy()
            noise = np.exp(np.cumsum(rng.normal(0, 0.02, size=(n, px.shape[1])), axis=0))
            base = px.loc[~after].ffill().iloc[-1].fillna(100.0).to_numpy()
            px.loc[after] = base * noise
            out[col] = px
        v = out["volume"].copy()
        v.loc[after] = v.loc[after].fillna(0.0) * (rng.random((n, v.shape[1])) < 0.5)   # kill half of later volume
        out["volume"] = v
        r = out["roll"].copy()
        r.loc[after] = (rng.random((n, r.shape[1])) < 0.02).astype(float)
        out["roll"] = r
        return out

    def load_rf(period="IS"):
        s = orig_rf(period).copy()
        rng = np.random.default_rng(seed + 7)
        m = s.index > cut
        s.loc[m] = s.loc[m] * rng.uniform(0, 3, m.sum()) + 1e-4
        return s

    E.load_ohlc, E.load_rf = load_ohlc, load_rf

ORDERS, FILLS = [], []
_order_shares = B.WeightStrategy.order_shares
_notify = B.WeightStrategy.notify_order


def order_shares(self, data, delta, exec):
    ORDERS.append((str(data.datetime.date(0)), data._name, float(delta), exec))
    return _order_shares(self, data, delta, exec)


def notify_order(self, order):
    if order.status == order.Completed:
        d = order.data
        FILLS.append(dict(created=str(bt.num2date(order.created.dt).date()), executed=str(d.datetime.date(0)),
                          name=d._name, size=float(order.executed.size), price=float(order.executed.price),
                          bar_open=float(d.open[0]), bar_close=float(d.close[0]),
                          exectype=bt.Order.ExecTypes[order.exectype], comm=float(order.executed.comm)))
    if order.status in (order.Margin, order.Rejected, order.Canceled):
        FILLS.append(dict(refused=order.getstatusname(), created=str(bt.num2date(order.created.dt).date()),
                          name=order.data._name))
    return _notify(self, order)


B.WeightStrategy.order_shares = order_shares
B.WeightStrategy.notify_order = notify_order

dec = f"{prefix}_dec.csv"
out = H.main(["--strategy", "gqh_equity_trend", "--costs", costs, "--params", f"book={book},fill={fill},decisions={dec}",
              "--json", f"{prefix}.json", "--series", f"{prefix}.csv"])
with open(f"{prefix}_log.pkl", "wb") as fh:
    pickle.dump({"orders": ORDERS, "fills": FILLS}, fh)
print("done", prefix, len(ORDERS), len(FILLS))
