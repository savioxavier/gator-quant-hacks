"""EWMAC engine for hourly and daily bars (Carver-style), with a position buffer and costs.

Conventions
- Forecast = scalar * (EMA_fast(X) - EMA_slow(X)) / sigma, X = cumulative within-contract log return
  (a roll-safe back-adjusted log price), sigma = EWMA std of the per-bar log return. Capped at +-20.
- Position (fraction of capital, notional) = forecast/10 * tau / sigma_ann, tau = 10% per market.
  sigma_ann = EWMA (span 35 days) std of the 16:00->16:00 daily return, known at the previous day's
  16:00 close (one day stale inside the day: point-in-time safe).
- Buffer: no trade while |pos - target| <= 10% of tau/sigma_ann (the position at forecast 10);
  otherwise trade to the nearer edge of the buffer.
- Point in time: the position decided at the close of bar k earns bar k+lag (lag 1 = the next bar,
  the README convention; lag 2 = execution one bar later).
- Costs: |trade| * one-way cost, plus 2 * |pos| * cost on each roll bar (closing the old and opening
  the new contract; conservative versus trading the calendar spread).
"""
import numpy as np
import pandas as pd

TAU = 0.10


def ewm_std(x, span):
    x = pd.Series(x)
    return np.sqrt((x ** 2).ewm(span=span, adjust=False, min_periods=span).mean())


def raw_ewmac(X, fast, slow, sigma):
    X = pd.Series(X)
    return (X.ewm(span=fast, adjust=False).mean() - X.ewm(span=slow, adjust=False).mean()).values / sigma


def run_positions(target, buf, decision):
    """Buffered position path. target/buf arrays per bar; decision: bool array, True where the
    position may be revised. Returns the position held after the close of each bar."""
    n = len(target)
    pos = np.zeros(n)
    p = 0.0
    for k in range(n):
        if decision[k]:
            t = target[k]
            b = buf[k]
            if t == t and b == b:         # not NaN
                lo, hi = t - b, t + b
                if p < lo:
                    p = lo
                elif p > hi:
                    p = hi
        pos[k] = p
    return pos


def pnl_from_positions(pos, r, roll, cost, lag=1):
    """Gross PnL and cost per bar. pos[k] is decided at the close of bar k. With lag L the
    position held during bar j is pos[j-L]; trades happen at the close of bar j-L+... (the
    executed position path is pos shifted by L-1 bars)."""
    n = len(pos)
    exe = np.r_[np.zeros(lag - 1), pos[:n - (lag - 1)]] if lag > 1 else pos.copy()   # position after close of bar k, as executed
    held = np.r_[0.0, exe[:-1]]                                                         # position during bar j
    gross = held * np.nan_to_num(r)
    trades = np.abs(np.diff(np.r_[0.0, exe]))
    c = trades * cost + roll.astype(float) * 2 * np.abs(held) * cost
    return gross, c, held, trades
