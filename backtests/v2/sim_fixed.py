"""Deviation D-4 fix 2: a next-open simulator that carries holdings as shares and cash.

The shared engine (gqh-flow-clock src/engine.py, simulate, exec="next_open") computes session t's return as

    r_t = on + (1 + on) * sum(w_new * r_oc) + cash_w * rf - costs,   on = sum(w_old * r_co)

with w_old = the target traded at the previous open. Between that open and the previous close the holdings moved
with the intraday returns, so the weights held over the close-to-open segment are not w_old: the engine silently
rebalances back to target at every close, without a cost, and measures the next open's trade from the target
drifted over the overnight segment only.

This module keeps the engine's formula and bookkeeping and changes only the holdings it is applied to:

* the target set for session t is bought at the open of t (shares = w_new x NAV at the open / open price);
* the shares drift with the open-to-close move of t and the close-to-open move into t+1;
* the overnight return of t+1 is earned on those drifted holdings (u, as a fraction of the NAV at the close of t),
  and the trade at the open of t+1 (and its cost) is measured from them, drifted again over the overnight segment;
* the T-bill on the cash weight (1 - sum of the weights held after the open trade), the borrow fee on short ETF
  weights, the trading costs (one-way bp per unit traded) and the roll round trip are booked exactly as the engine
  books them (fractions of the previous close's NAV).

So   u_i(close t) = w_new_i * (1 + on_t) * (1 + r_oc_i,t) / (1 + net_t),
     on_{t+1}    = sum_i u_i(close t) * r_co_i,t+1,
     trade_{t+1} = |w_new_{t+1} - u(close t) * (1 + r_co_{t+1}) / (1 + on_{t+1})|,
which is a share-and-cash ledger (see test_sim_fixed.py, which checks it against an explicit one). With no intraday
moves, no T-bill and no costs it equals the engine exactly. The reviewer's example: $100 with $50 in an asset that
rises 10% intraday and 10% overnight is worth $110.50 at the next open here and $110.25 in the engine.

Only exec="next_open" (E1) is corrected; exec="next_close" (E2) already measures each day's trade from the holdings
drifted over the one close-to-close segment, so it is not handled here.

Returns the engine's tuple (net, gross, turnover, held weights after the open trade, costs). "gross" is the return
before costs on the same path (as in the engine; the path itself depends on costs through the NAV, at second order).
The engine's constants (default cost bp, borrow fee, trading days, futures flag) are read from gqh-flow-clock's
src/config.py, which must be importable (run_v2.py puts GQH_REPO on sys.path); nothing in gqh-flow-clock is changed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _config():
    from src import config as C  # gqh-flow-clock (GQH_REPO on sys.path)
    return C


def simulate(
    w_dec: pd.DataFrame,
    ohlc: dict,
    rf: pd.Series,
    exec: str = "next_open",
    cost_mult: float = 1.0,
    cost_bps: dict | None = None,
    config=None,
):
    """Drop-in for engine.simulate(..., exec="next_open") with holdings carried as shares and cash.
    Returns (net, gross, turnover, held_weights, costs) daily series on the close panel's calendar."""
    if exec != "next_open":
        raise ValueError("sim_fixed corrects exec='next_open' only (next_close already carries the drift)")
    C = config or _config()
    tickers = list(w_dec.columns)
    close = ohlc["close"][tickers].ffill(limit=5)        # as the engine: bridge isolated missing prints only
    idx = close.index
    w_dec = w_dec.reindex(idx).ffill().fillna(0.0)
    rf = rf.reindex(idx).ffill().fillna(0.0)
    cb = pd.Series({t: (cost_bps or {}).get(t, C.cost_bps(t)) for t in tickers}) * cost_mult / 1e4
    borrow = pd.Series({t: 0.0 if C.is_future(t) else C.SHORT_BORROW_BPS_PER_YEAR for t in tickers}) / 1e4 / C.TRADING_DAYS
    roll = ohlc.get("roll")
    roll = roll[tickers].reindex(idx).fillna(0.0) if roll is not None else pd.DataFrame(0.0, index=idx, columns=tickers)
    open_ = ohlc["open"][tickers].ffill(limit=5)
    r_co = (open_ / close.shift(1) - 1).fillna(0.0)
    r_oc = (close / open_ - 1).fillna(0.0)
    w_new = w_dec.shift(1).fillna(0.0)                   # traded at today's open (as the engine)

    W, RCO, ROC = w_new.to_numpy(float), r_co.to_numpy(float), r_oc.to_numpy(float)
    RF, ROLL = rf.to_numpy(float), roll.to_numpy(float)
    CB, BR = cb.to_numpy(float), borrow.to_numpy(float)
    n, k = W.shape
    net, gross, turn, cost = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
    u = np.zeros(k)                                      # holdings at the previous close, fraction of that close's NAV
    for i in range(n):
        w = W[i]
        on = float(u @ RCO[i])                           # overnight return on the drifted holdings
        drifted = u * (1.0 + RCO[i]) / (1.0 + on) if (1.0 + on) != 0.0 else np.zeros(k)  # weights at the open, pre-trade
        g = on + (1.0 + on) * float(w @ ROC[i]) + (1.0 - w.sum()) * RF[i]
        tr = np.abs(w - drifted) + 2.0 * np.abs(w) * ROLL[i]
        c = float(tr @ CB) + float(np.abs(np.minimum(w, 0.0)) @ BR)
        r = g - c
        net[i], gross[i], turn[i], cost[i] = r, g, tr.sum(), c
        u = w * (1.0 + on) * (1.0 + ROC[i]) / (1.0 + r) if (1.0 + r) != 0.0 else np.zeros(k)
    return (pd.Series(net, index=idx), pd.Series(gross, index=idx), pd.Series(turn, index=idx), w_new,
            pd.Series(cost, index=idx))
