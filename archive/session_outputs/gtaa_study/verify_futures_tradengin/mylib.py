"""Independent re-implementation (own loaders, own simulator, own signals) for verifying the futures GTAA study.
Reads the cached parquet files directly; does not call the repo engine for any strategy number here."""
from __future__ import annotations

import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(os.environ.get("GQH_DATA_DIR", r"<home>/.cache/gqh"))
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

START = pd.Timestamp("2005-01-03")
END = pd.Timestamp("2026-10-02")
IS_F = ("2011-09-02", "2024-10-02")
IS_E = ("2005-11-01", "2024-10-02")
OOS = ("2024-10-03", "2026-10-02")

ROOTS = ["ES", "NQ", "RTY", "YM", "ZT", "ZF", "ZN", "ZB", "UB", "CL", "HO", "RB", "NG", "GC", "SI", "PL",
         "HG", "ZC", "ZS", "ZW", "ZL", "ZM", "LE", "HE", "6E", "6J", "6B", "6A", "6C", "6S"]
FUT = [f"F_{r}" for r in ROOTS]
CHEAP = {"ES", "NQ", "YM", "ZT", "ZF", "ZN", "ZB", "CL", "GC", "SI", "HG", "6E", "6J", "6B", "UB", "6S"}
FCOST = {f"F_{r}": (1.5 if r in CHEAP else 5.0) for r in ROOTS}
ETF5 = ["SPY", "EFA", "IEF", "VNQ", "DBC"]
ECOST = {"SPY": 3.0, "EFA": 3.0, "IEF": 3.0, "VNQ": 5.0, "DBC": 5.0}
CLS = {}
for c, rs in {"equity": ["ES", "NQ", "RTY", "YM"], "rates": ["ZT", "ZF", "ZN", "ZB", "UB"],
              "comm": ["CL", "HO", "RB", "NG", "GC", "SI", "PL", "HG", "ZC", "ZS", "ZW", "ZL", "ZM", "LE", "HE"],
              "fx": ["6E", "6J", "6B", "6A", "6C", "6S"]}.items():
    for r in rs:
        CLS[f"F_{r}"] = c


def calendar():
    e = pd.read_parquet(DATA / "etf_daily.parquet")
    cal = pd.DatetimeIndex(sorted(e.loc[e.ticker == "SPY", "date"].unique()))
    return cal[(cal >= START) & (cal <= END)]


def wide(file, tickers, cal, end=END):
    d = pd.read_parquet(DATA / file)
    d = d[d.ticker.isin(tickers) & (d.date <= end)]
    out = {}
    for col in ("open", "close", "volume", "roll"):
        if col in d.columns:
            out[col] = d.pivot(index="date", columns="ticker", values=col).reindex(index=cal, columns=tickers)
    return out


def rf_series(cal):
    r = pd.read_parquet(DATA / "rf_daily.parquet")
    if "date" in r.columns:
        r = r.set_index("date")
    r.index = pd.to_datetime(r.index)
    return r["rf"].reindex(cal).ffill().fillna(0.0)


def month_ends(cal, last_complete=True):
    s = pd.Series(cal, index=cal)
    me = s.groupby(cal.to_period("M")).max()
    me = pd.DatetimeIndex(me.values)
    # drop the final month if the calendar stops before that month is over
    if last_complete and (cal[-1] + pd.offsets.BDay(1)).month == cal[-1].month:
        me = me[me < cal[-1].to_period("M").start_time]
    return me


# ------------------------------------------------------------------ simulators (own code)

def sim_next_close(W, close, rf, cost_bps, roll=None):
    """W: decision weights at close d (from data <= d). Traded at close d+1, earns close(d+1)->close(d+2)."""
    W = W.reindex(close.index).ffill().fillna(0.0)
    px = close[W.columns].ffill(limit=5)
    r = px.pct_change(fill_method=None).fillna(0.0)
    H = W.shift(2).fillna(0.0)                       # held over return day t
    port = (H * r).sum(axis=1)
    gross = port + (1 - H.sum(axis=1)) * rf
    # trade executed at close t-1 to move from drifted H[t-1] to H[t]
    Hp = H.shift(1).fillna(0.0)
    rp = r.shift(1).fillna(0.0)
    drift = Hp * (1 + rp)
    drift = drift.div((1 + (Hp * rp).sum(axis=1)).replace(0, np.nan), axis=0).fillna(0.0)
    tr = (H - drift).abs()
    if roll is not None:
        tr = tr + 2 * H.abs() * roll[W.columns].fillna(0.0)
    cb = pd.Series(cost_bps)[W.columns] / 1e4
    cost = (tr * cb).sum(axis=1)
    return gross - cost, gross, tr.sum(axis=1), H


def sim_next_open(W, o, close, rf, cost_bps, borrow_bps=30.0):
    W = W.reindex(close.index).ffill().fillna(0.0)
    c = close[W.columns].ffill(limit=5)
    op = o[W.columns].ffill(limit=5)
    rco = (op / c.shift(1) - 1).fillna(0.0)
    roc = (c / op - 1).fillna(0.0)
    new = W.shift(1).fillna(0.0)
    old = W.shift(2).fillna(0.0)
    on = (old * rco).sum(axis=1)
    risky = on + (1 + on) * (new * roc).sum(axis=1)
    gross = risky + (1 - new.sum(axis=1)) * rf
    drift = (old * (1 + rco)).div((1 + on).replace(0, np.nan), axis=0).fillna(0.0)
    tr = (new - drift).abs()
    cb = pd.Series(cost_bps)[W.columns] / 1e4
    cost = (tr * cb).sum(axis=1) + (new.clip(upper=0).abs() * borrow_bps / 1e4 / 252).sum(axis=1)
    return gross - cost, gross, tr.sum(axis=1), new


# ------------------------------------------------------------------ stats

def sharpe(x):
    x = x.dropna()
    return float(x.mean() / x.std(ddof=1) * math.sqrt(252))


def mdd(r):
    eq = (1 + r).cumprod()
    return float((eq / eq.cummax() - 1).min())


def stats(net, rf, turnover, win):
    sl = slice(*map(pd.Timestamp, win))
    n = net.loc[sl]
    x = n - rf.loc[sl]
    yrs = len(n) / 252
    sr = sharpe(x)
    return {"sharpe": sr, "se": math.sqrt((1 + sr * sr / 2) / yrs), "ann_ret": float((1 + n).prod() ** (1 / yrs) - 1),
            "vol": float(n.std() * math.sqrt(252)), "mdd": mdd(n), "turn": float(turnover.loc[sl].sum() / yrs),
            "n": len(n)}


def block_boot(X, L=63, B=4000, seed=12345):
    """Circular paired block bootstrap, returns B x k Sharpe matrix."""
    A = np.asarray(X)
    n, k = A.shape
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / L))
    out = np.empty((B, k))
    for b in range(B):
        st = rng.integers(0, n, size=nb)
        idx = ((st[:, None] + np.arange(L)[None, :]) % n).ravel()[:n]
        Y = A[idx]
        out[b] = Y.mean(0) / Y.std(0, ddof=1) * math.sqrt(252)
    return out
