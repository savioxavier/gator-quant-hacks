"""Shared helpers for the GTAA (S3) attribution study. Read-only use of the repo: imports src.engine / src.forward2,
never calls run_backtest / log_trial, never writes under the repo, never unlocks the OOS loader."""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<solo-repo>")
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

if os.environ.get("GQH_OOS_UNLOCK") == "1":
    raise SystemExit("refusing to run with GQH_OOS_UNLOCK=1")

from src import calendar_utils as CU  # noqa: E402
from src import config as C  # noqa: E402
from src import engine as E  # noqa: E402
from src import forward2 as F2  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

IS_END = "2024-10-02"
OOS_START = "2024-10-03"
OOS_END = "2026-10-02"
TICK = list(F2.S3_TICKERS)          # SPY EFA IEF VNQ DBC
TD = 252


# ----------------------------------------------------------------------------- data

_CACHE: dict = {}


def data():
    """ohlc (FWD = every cached date, OOS loader stays locked), rf on the same calendar."""
    if "ohlc" not in _CACHE:
        ohlc = E.load_ohlc(TICK, "FWD")
        rf = E.load_rf("FWD").reindex(ohlc["close"].index).ffill().fillna(0.0)
        _CACHE["ohlc"], _CACHE["rf"] = ohlc, rf
    return _CACHE["ohlc"], _CACHE["rf"]


def month_ends(cal: pd.DatetimeIndex) -> pd.DatetimeIndex:
    mo = CU.month_offsets(cal)
    return mo.index[mo["off_own"] == 0]


def sma_decisions(close: pd.DataFrame, n_months: int = 10, timed=None, weight: float = 0.20) -> pd.DataFrame:
    """Replica of forward2.s3_decisions with a lookback parameter. timed: set of tickers that are timed; the rest
    are held at `weight` once their n-month SMA exists (BH5 rule). timed=None -> all timed; timed=set() -> BH5."""
    tick = list(close.columns)
    timed = set(tick) if timed is None else set(timed)
    me = month_ends(close.index)
    mclose = close.loc[me]
    sma = mclose.rolling(n_months, min_periods=n_months).mean()
    elig = mclose.notna() & sma.notna()
    on = (mclose > sma) & sma.notna()
    sig = pd.DataFrame({t: (on[t] if t in timed else elig[t]) for t in tick}).astype(float) * weight
    w = pd.DataFrame(np.nan, index=close.index, columns=tick)
    w.loc[me] = sig.values
    return w.ffill().fillna(0.0)


# ----------------------------------------------------------------------------- simulation with per-ticker pieces

def decompose_next_open(w_dec: pd.DataFrame, ohlc: dict, rf: pd.Series, cost_bps=None) -> dict:
    """Exact per-ticker split of engine.simulate(exec="next_open") for a long-only ETF book (no borrow, no rolls).

    gross_risky_t = sum_i [ w_old_i r_co_i + (1 + on_t) w_new_i r_oc_i ]  ->  contrib_i (sums exactly)
    net_t - rf_t  = sum_i [ contrib_i - held_i rf_t - cost_i ]               ->  ex_contrib_i (sums exactly)
    """
    tickers = list(w_dec.columns)
    close = ohlc["close"][tickers].ffill(limit=5)
    idx = close.index
    w_dec = w_dec.reindex(idx).ffill().fillna(0.0)
    rf = rf.reindex(idx).ffill().fillna(0.0)
    cb = pd.Series({t: (cost_bps or {}).get(t, C.cost_bps(t)) for t in tickers}) / 1e4
    open_ = ohlc["open"][tickers].ffill(limit=5)
    r_co = (open_ / close.shift(1) - 1).fillna(0.0)
    r_oc = (close / open_ - 1).fillna(0.0)
    w_new = w_dec.shift(1).fillna(0.0)        # decided at close d-1, traded at the open of d
    w_old = w_dec.shift(2).fillna(0.0)        # held overnight into the open of d
    on = (w_old * r_co).sum(axis=1)
    contrib = w_old * r_co + w_new.mul(r_oc).mul(1 + on, axis=0)
    drifted = w_old.mul(1 + r_co).div((1 + on).replace(0, np.nan), axis=0).fillna(0.0)
    trade = (w_new - drifted).abs()
    switch_trade = (w_new - w_old).abs()      # the part of the trade due to a changed decision
    cost = trade * cb
    switch_cost = switch_trade * cb
    ex_contrib = contrib - w_new.mul(rf, axis=0) - cost
    net = contrib.sum(axis=1) + (1 - w_new.sum(axis=1)) * rf - cost.sum(axis=1)
    return {"contrib": contrib, "ex_contrib": ex_contrib, "cost": cost, "switch_cost": switch_cost,
            "trade": trade, "held": w_new, "w_old": w_old, "net": net, "rf": rf, "r_co": r_co, "r_oc": r_oc,
            "open": open_, "close": close, "r_cc": close.pct_change(fill_method=None).fillna(0.0), "w_dec": w_dec}


def sim(w_dec: pd.DataFrame, ohlc: dict, rf: pd.Series) -> pd.Series:
    net, *_ = E.simulate(w_dec, {k: v[list(w_dec.columns)] for k, v in ohlc.items()}, rf, exec="next_open")
    return net


# ----------------------------------------------------------------------------- statistics

def stats(net: pd.Series, rf: pd.Series) -> dict:
    net = net.dropna()
    ex = net - rf.reindex(net.index).ffill().fillna(0.0)
    n = len(net)
    yrs = n / TD
    eq = (1 + net).cumprod()
    sd = ex.std()
    sr = float(ex.mean() / sd * math.sqrt(TD)) if sd > 0 else float("nan")
    return {"start": str(net.index[0].date()), "end": str(net.index[-1].date()), "n_days": n, "years": yrs,
            "ann_return": float(eq.iloc[-1] ** (1 / yrs) - 1), "ann_excess_arith": float(ex.mean() * TD),
            "ann_vol": float(net.std() * math.sqrt(TD)), "sharpe": sr, "max_drawdown": E.max_drawdown(net),
            "sharpe_se": sharpe_se(sr, yrs)}


def sharpe_se(sr: float, years: float) -> float:
    return math.sqrt((1 + sr ** 2 / 2) / years)


def sr_of(x: np.ndarray, axis=-1) -> np.ndarray:
    return x.mean(axis=axis) / x.std(axis=axis, ddof=1) * math.sqrt(TD)


def circular_block_indices(n: int, block: int, reps: int, rng: np.random.Generator) -> np.ndarray:
    nb = int(math.ceil(n / block))
    starts = rng.integers(0, n, size=(reps, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]) % n
    return idx.reshape(reps, -1)[:, :n]


def paired_bootstrap(a: pd.Series, b: pd.Series, block: int, reps: int = 10000, seed: int = 7) -> dict:
    """Paired circular block bootstrap of daily excess returns a (strategy) and b (benchmark)."""
    j = pd.concat([a, b], axis=1, join="inner").dropna()
    x, y = j.iloc[:, 0].to_numpy(), j.iloc[:, 1].to_numpy()
    n = len(x)
    rng = np.random.default_rng(seed)
    d_sr, s_a, s_b, d_mu = [], [], [], []
    for chunk in range(0, reps, 1000):
        k = min(1000, reps - chunk)
        idx = circular_block_indices(n, block, k, rng)
        xa, yb = x[idx], y[idx]
        sa, sb = sr_of(xa), sr_of(yb)
        s_a.append(sa)
        s_b.append(sb)
        d_sr.append(sa - sb)
        d_mu.append((xa.mean(axis=1) - yb.mean(axis=1)) * TD)
    d_sr, s_a, s_b, d_mu = map(np.concatenate, (d_sr, s_a, s_b, d_mu))
    obs_a, obs_b = float(sr_of(x)), float(sr_of(y))

    def q(v):
        return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]

    return {"block_days": block, "reps": reps, "n_days": n,
            "sr_a": obs_a, "sr_b": obs_b, "d_sr": obs_a - obs_b, "d_sr_ci95": q(d_sr), "d_sr_boot_se": float(d_sr.std()),
            "p_boot_d_sr_le_0": float((d_sr <= 0).mean()),
            "sr_a_ci95": q(s_a), "sr_a_boot_se": float(s_a.std()), "sr_b_ci95": q(s_b), "sr_b_boot_se": float(s_b.std()),
            "d_mean_excess_ann": float((x.mean() - y.mean()) * TD), "d_mean_excess_ci95": q(d_mu)}


def memmel_se_diff(a: pd.Series, b: pd.Series) -> float:
    """Jobson-Korkie / Memmel (2003) asymptotic SE of SR_a - SR_b (annualised), iid normal returns."""
    j = pd.concat([a, b], axis=1, join="inner").dropna()
    x, y = j.iloc[:, 0], j.iloc[:, 1]
    n = len(j)
    s1, s2 = x.mean() / x.std(), y.mean() / y.std()
    rho = x.corr(y)
    v = (2 - 2 * rho + 0.5 * (s1 ** 2 + s2 ** 2 - 2 * s1 * s2 * rho ** 2)) / n
    return float(math.sqrt(v) * math.sqrt(TD))


def nw_lags(n: int) -> int:
    return int(4 * (n / 100) ** (2 / 9))


def ols_nw(y: pd.Series, X: pd.DataFrame, lags: int | None = None) -> dict:
    import statsmodels.api as sm

    df = pd.concat([y.rename("y"), X], axis=1, join="inner").dropna()
    lags = nw_lags(len(df)) if lags is None else lags
    fit = sm.OLS(df["y"], sm.add_constant(df.drop(columns="y"))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    out = {"n": int(fit.nobs), "nw_lags": lags, "r2": float(fit.rsquared)}
    for k in fit.params.index:
        out[f"{k}_coef"] = float(fit.params[k])
        out[f"{k}_t"] = float(fit.tvalues[k])
    return out, fit


def monthly(net: pd.Series) -> pd.Series:
    return (1 + net).resample("ME").prod() - 1


def capture(strat_m: pd.Series, bench_m: pd.Series) -> dict:
    j = pd.concat([strat_m, bench_m], axis=1, join="inner").dropna()
    s, b = j.iloc[:, 0], j.iloc[:, 1]
    out = {}
    for lab, m in (("up", b > 0), ("down", b < 0)):
        n = int(m.sum())
        if n == 0:
            out[f"{lab}_capture_geo"] = float("nan")
            continue
        gs = (1 + s[m]).prod() ** (1 / n) - 1
        gb = (1 + b[m]).prod() ** (1 / n) - 1
        out[f"{lab}_months"] = n
        out[f"{lab}_capture_geo"] = float(gs / gb)
        out[f"{lab}_capture_arith"] = float(s[m].mean() / b[m].mean())
    return out
