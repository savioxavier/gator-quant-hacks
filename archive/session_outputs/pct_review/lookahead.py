"""Perturbation lookahead test for every PCT variant: scramble all data after a cut date
(close/open/rf replaced with random walks) and check decision weights at dates <= cut are unchanged.
No backtest / no performance numbers are produced here."""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "<solo-repo>")
from src.strategies import pct as P  # noqa: E402

orig_ohlc, orig_rf = P._data("IS", tuple(P.TICKERS))
P._data.cache_clear()

def make_perturbed(cut):
    rng = np.random.default_rng(1)
    o = {k: v.copy() for k, v in orig_ohlc.items()}
    after = o["close"].index > cut
    n = int(after.sum())
    for k in ("open", "high", "low", "close"):
        noise = np.exp(np.cumsum(rng.normal(0, 0.05, size=(n, o[k].shape[1])), axis=0))
        o[k].loc[after] = o[k].loc[after].to_numpy() * noise * 3.0
    rf = orig_rf.copy()
    rf.loc[rf.index > cut] = rng.uniform(0, 0.01, size=int((rf.index > cut).sum()))
    return o, rf

base_fn = P._data
res = {}
for cut in [pd.Timestamp("2009-03-09"), pd.Timestamp("2015-06-15"), pd.Timestamp("2020-03-16")]:
    o, rf = make_perturbed(cut)
    for name in ["base"] + [k for k in P.VARIANTS if k != "cost2x"]:
        p, _ = P._variant_params(name)
        P._data = base_fn
        w0 = P.decision_weights("IS", list(P.TICKERS), **p)
        P._data = lambda period, tickers, o=o, rf=rf: (o, rf)
        w1 = P.decision_weights("IS", list(P.TICKERS), **p)
        P._data = base_fn
        upto = w0.index <= cut
        d_before = float((w0[upto] - w1[upto]).abs().max().max())
        d_after = float((w0[~upto] - w1[~upto]).abs().max().max())
        res[(str(cut.date()), name)] = (d_before, d_after)
for k, v in res.items():
    print(k, "max|dw| <= cut: %.3e   after cut: %.3e" % v)
assert all(v[0] == 0.0 for v in res.values()), "LOOKAHEAD"
print("OK: no decision at or before the cut changes when post-cut data is scrambled")
