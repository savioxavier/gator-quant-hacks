"""GTAA neighbourhood grid: decision builder, metrics and block bootstrap.

Everything here is read-only with respect to the repository: it imports src.engine (load_ohlc, load_rf,
simulate, perf_stats, deflated_sharpe), src.calendar_utils and src.pbo, and never calls run_backtest,
log_trial or log_trials_bulk, never writes to results/, never touches GQH_OOS_UNLOCK.

Grid (fixed before any result was computed):
  signal    : SMA6, SMA8, SMA10, SMA12   month-end close > mean of the last n month-end closes (incl. current)
              MOM12                      12-month total return (month-end to month-end) > T-bill return
                                         compounded over the same 12 months (absolute momentum)
              SMA10_D1                   10-month SMA of month-end closes, checked every session against the
                                         daily close with a +/-1% band: switch on when close > 1.01*SMA, off
                                         when close < 0.99*SMA, otherwise keep the previous state
  universe  : frozen5 = SPY EFA IEF VNQ DBC (the frozen S3 set)
              broad10 = SPY EFA EEM IEF TLT LQD TIP VNQ GLD DBC
                        (the suggested 11-ETF list minus HYG; HYG is the only member listed after Feb 2006 and
                        its Apr 2007 inception would push the common start to May 2008, after the GFC began;
                        the rule "no member may start after DBC, the binding member of the frozen set" was fixed
                        from inception dates only, before any backtest was run)
              eq4     = SPY EFA EEM VNQ (equities-only incl. REITs)
  weighting : equal (1/N of the universe per ETF) or inverse 63-day volatility (w_i ~ 1/sigma_i over all
              universe members, normalised to sum to 1, recomputed at month-end from the trailing 63 daily
              close-to-close returns ending at that month-end)
  risk-off  : T-bills (the switched-off slot stays in cash, which the engine credits with the T-bill return)
              or IEF (the switched-off slot is added to IEF unconditionally; for universes containing IEF its
              own signal is therefore moot)
  -> 6 x 3 x 2 x 2 = 72 timed variants, plus 3 x 2 = 6 untimed (always-in) benchmarks, one per
     universe/weighting, rebalanced on the same month-end weights.

Execution: decision weights at the close of a month-end (any session for SMA10_D1) are filled at the next
session's open (engine.simulate exec="next_open"), default per-ETF costs, engine rebalances to target daily
(as the frozen S3/BH5 do). Every variant and benchmark makes its first decision on the same date (the first
month-end at which every variant has a valid signal and weight for every universe member), so all are compared
on the same return days.
"""
from __future__ import annotations

import itertools
import math
import os
import sys

import numpy as np
import pandas as pd

REPO = "<solo-repo>"
if REPO not in sys.path:
    sys.path.insert(0, REPO)
assert os.environ.get("GQH_OOS_UNLOCK") != "1", "never run with the OOS lock released"

from src import calendar_utils as CU  # noqa: E402
from src import config as C  # noqa: E402
from src import engine as E  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))

SIGNALS = ["SMA6", "SMA8", "SMA10", "SMA12", "MOM12", "SMA10_D1"]
UNIVERSES = {
    "frozen5": ["SPY", "EFA", "IEF", "VNQ", "DBC"],
    "broad10": ["SPY", "EFA", "EEM", "IEF", "TLT", "LQD", "TIP", "VNQ", "GLD", "DBC"],
    "eq4": ["SPY", "EFA", "EEM", "VNQ"],
}
WEIGHTINGS = ["equal", "invvol63"]
RISKOFF = ["tbill", "IEF"]
ALL_TICKERS = sorted(set(itertools.chain.from_iterable(UNIVERSES.values())))
VOL_WINDOW = 63
BAND = 0.01
S3_KEY = ("SMA10", "frozen5", "equal", "tbill")


def grid() -> list[tuple[str, str, str, str]]:
    return list(itertools.product(SIGNALS, UNIVERSES, WEIGHTINGS, RISKOFF))


def vid(key) -> str:
    return "|".join(key)


# --------------------------------------------------------------------------- data

def load(period: str):
    ohlc = E.load_ohlc(ALL_TICKERS, period)
    rf = E.load_rf(period)
    return ohlc, rf


def month_ends(cal: pd.DatetimeIndex) -> pd.DatetimeIndex:
    mo = CU.month_offsets(cal)
    return mo.index[mo["off_own"] == 0]


# --------------------------------------------------------------------------- signals (all point-in-time)

def monthly_signal(close: pd.DataFrame, rf: pd.Series, me: pd.DatetimeIndex, signal: str) -> pd.DataFrame:
    """Boolean-or-NaN frame on the month-end dates: value at month-end t uses closes up to t only.
    NaN = not yet computable (warm-up)."""
    mclose = close.loc[me]
    if signal.startswith("SMA") and not signal.endswith("_D1"):
        n = int(signal[3:])
        sma = mclose.rolling(n, min_periods=n).mean()
        sig = (mclose > sma).astype(float).where(sma.notna() & mclose.notna())
    elif signal == "MOM12":
        growth = (1 + rf.reindex(close.index).fillna(0.0)).cumprod()
        tb = growth.loc[me] / growth.loc[me].shift(12) - 1
        mom = mclose / mclose.shift(12) - 1
        sig = mom.gt(tb, axis=0).astype(float).where(mom.notna() & tb.notna().to_numpy()[:, None])
    else:
        raise ValueError(signal)
    return sig


def daily_band_signal(close: pd.DataFrame, me: pd.DatetimeIndex, n: int = 10, band: float = BAND) -> pd.DataFrame:
    """SMA10_D1 state per session d: uses the daily close of d and the SMA of the last n month-end closes at
    or before d (on a month-end the SMA includes that day's close, as in the monthly rule). NaN in warm-up."""
    mclose = close.loc[me]
    sma_m = mclose.rolling(n, min_periods=n).mean()
    sma_d = sma_m.reindex(close.index).ffill()           # value known from the month-end close onwards
    out = pd.DataFrame(np.nan, index=close.index, columns=close.columns)
    for c in close.columns:
        px = close[c].to_numpy()
        s = sma_d[c].to_numpy()
        state = np.nan
        res = np.full(len(px), np.nan)
        for i in range(len(px)):
            if np.isnan(s[i]):
                continue
            if np.isnan(state):
                if np.isnan(px[i]):
                    continue
                state = 1.0 if px[i] > s[i] else 0.0      # first valid day: plain rule, no band
            elif not np.isnan(px[i]):
                if state == 0.0 and px[i] > s[i] * (1 + band):
                    state = 1.0
                elif state == 1.0 and px[i] < s[i] * (1 - band):
                    state = 0.0
            res[i] = state
        out[c] = res
    return out


def base_weights(close: pd.DataFrame, me: pd.DatetimeIndex, tickers: list[str], weighting: str) -> pd.DataFrame:
    """Month-end strategic weights (sum 1 over the universe), NaN in warm-up."""
    if weighting == "equal":
        avail = close.loc[me, tickers].notna()
        w = pd.DataFrame(1.0 / len(tickers), index=me, columns=tickers).where(avail.all(axis=1), np.nan, axis=0)
        return w
    if weighting == "invvol63":
        r = close[tickers].pct_change(fill_method=None)
        vol = r.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std().loc[me]
        inv = 1.0 / vol
        w = inv.div(inv.sum(axis=1, skipna=False), axis=0)
        return w
    raise ValueError(weighting)


def decisions(key, close: pd.DataFrame, rf: pd.Series, start_decision: pd.Timestamp | None,
              timed: bool = True) -> pd.DataFrame:
    """Decision weights w_dec (rows = decision dates; the engine fills row d at the open of d+1).
    Columns: universe members plus IEF if it is the risk-off asset. Zero before start_decision."""
    signal, universe, weighting, riskoff = key
    tick = UNIVERSES[universe]
    cols = list(tick) + (["IEF"] if riskoff == "IEF" and "IEF" not in tick else [])
    cal = close.index
    me = month_ends(cal)
    bw = base_weights(close, me, tick, weighting)                    # month-end
    bw_d = bw.reindex(cal).ffill()                                   # held until the next month-end
    if not timed:
        on = pd.DataFrame(1.0, index=cal, columns=tick).where(bw_d.notna())
    elif signal == "SMA10_D1":
        on = daily_band_signal(close[tick], me)
    else:
        on = monthly_signal(close[tick], rf, me, signal).reindex(cal).ffill()
    w_on = bw_d * on                                                 # NaN anywhere in warm-up
    off = (bw_d * (1 - on)).sum(axis=1, min_count=len(tick))
    w = pd.DataFrame(0.0, index=cal, columns=cols)
    w[tick] = w_on
    if riskoff == "IEF":
        w["IEF"] = w["IEF"] + off
    valid = w_on.notna().all(axis=1)
    if timed and signal != "SMA10_D1":
        # monthly rules only decide at month-ends; mark the first valid month-end
        pass
    w = w.where(valid, np.nan, axis=0)
    if start_decision is not None:
        w.loc[w.index < start_decision] = 0.0
    return w.fillna(0.0)


def first_valid_decision(key, close, rf, timed=True) -> pd.Timestamp:
    """First month-end at which the variant has a full valid weight vector."""
    signal, universe, weighting, riskoff = key
    tick = UNIVERSES[universe]
    me = month_ends(close.index)
    bw = base_weights(close, me, tick, weighting)
    if not timed:
        ok = bw.notna().all(axis=1)
    elif signal == "SMA10_D1":
        st = daily_band_signal(close[tick], me).loc[me]
        ok = bw.notna().all(axis=1) & st.notna().all(axis=1)
    else:
        sg = monthly_signal(close[tick], rf, me, signal)
        ok = bw.notna().all(axis=1) & sg.notna().all(axis=1)
    return ok[ok].index[0]


# --------------------------------------------------------------------------- metrics

def stats_row(net: pd.Series, rf: pd.Series, turnover: pd.Series, held: pd.DataFrame) -> dict:
    ex = net - rf.reindex(net.index).ffill().fillna(0.0)
    ps = E.perf_stats(net, ex, turnover)
    years = len(net) / C.TRADING_DAYS
    sr = ps["sharpe"]
    return {
        "start": ps["start"], "end": ps["end"], "years": years,
        "sharpe": sr, "sharpe_se": math.sqrt((1 + sr ** 2 / 2) / years),
        "ann_return": ps["ann_return"], "ann_vol": ps["ann_vol"], "max_dd": ps["max_drawdown"],
        "turnover_per_year": ps["turnover_per_year"], "worst_month": ps["worst_month"],
        "avg_gross_exposure": float(held.abs().sum(axis=1).mean()),
    }


def run_variant(key, ohlc, rf, start_decision, window, timed=True):
    close = ohlc["close"]
    w = decisions(key, close, rf, start_decision, timed=timed)
    net, gross, to, held, cost = E.simulate(w, ohlc, rf, exec="next_open")
    sl = slice(pd.Timestamp(window[0]), pd.Timestamp(window[1]))
    return w, net.loc[sl], gross.loc[sl], to.loc[sl], held.loc[sl]


# --------------------------------------------------------------------------- bootstrap

def block_boot_sharpe(X: np.ndarray, L: int, B: int = 2000, seed: int = 7, chunk: int = 250) -> np.ndarray:
    """Circular block bootstrap of annualised Sharpe ratios for every column of X (T x N daily excess
    returns), with the SAME resampled days for every column (paired). Returns B x N."""
    X = np.asarray(X, dtype=float)
    T, N = X.shape
    Xc = np.vstack([X, X[: L - 1]])
    z = np.zeros((1, N))
    cs1 = np.vstack([z, np.cumsum(Xc, 0)])
    cs2 = np.vstack([z, np.cumsum(Xc ** 2, 0)])
    S1 = cs1[L: L + T] - cs1[:T]
    S2 = cs2[L: L + T] - cs2[:T]
    nb = int(math.ceil(T / L))
    n = nb * L
    rng = np.random.default_rng(seed)
    out = np.empty((B, N))
    for a in range(0, B, chunk):
        b = min(B, a + chunk)
        st = rng.integers(0, T, size=(b - a, nb))
        s1 = S1[st].sum(axis=1)
        s2 = S2[st].sum(axis=1)
        m = s1 / n
        v = (s2 / n - m ** 2) * n / (n - 1)
        out[a:b] = m / np.sqrt(np.maximum(v, 1e-18)) * math.sqrt(C.TRADING_DAYS)
    return out


def ci(x: np.ndarray, lv=(0.05, 0.95)) -> tuple[float, float]:
    return float(np.quantile(x, lv[0])), float(np.quantile(x, lv[1]))
