"""Independent re-implementation of the risk_premia futures variants (no engine.simulate, no rp_core).

Reads the cached parquet files directly; builds weights with numpy loops; simulates two ways:
  sim_daily : constant target weights re-traded every session (same convention the study claims)
  sim_drift : trade only at the monthly rebalance and on roll days, positions drift in between
Costs: one-way bp x |notional traded|; roll day = one extra round trip of the held position.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

D = Path("<home>/.cache/gqh")
END_FWD = pd.Timestamp("2026-10-02")
IS_END = pd.Timestamp("2024-10-02")
LATER_START = pd.Timestamp("2024-10-03")
A_END = pd.Timestamp("2016-12-30")
COST = {"F_ES": 0.75, "F_ZN": 1.0, "F_GC": 1.5}
TICK = ["F_ES", "F_ZN", "F_GC"]


def load():
    fut = pd.read_parquet(D / "futures_daily.parquet")
    fut = fut[fut.ticker.isin(TICK)]
    etf = pd.read_parquet(D / "etf_daily.parquet")
    cal = pd.DatetimeIndex(sorted(etf.loc[etf.ticker == "SPY", "date"].unique()))
    cal = cal[(cal >= pd.Timestamp("2005-01-03")) & (cal <= END_FWD)]
    close = fut.pivot(index="date", columns="ticker", values="close").reindex(cal)[TICK]
    vol = fut.pivot(index="date", columns="ticker", values="volume").reindex(cal)[TICK]
    roll = fut.pivot(index="date", columns="ticker", values="roll").reindex(cal)[TICK].fillna(0.0)
    rf = pd.read_parquet(D / "rf_daily.parquet").set_index("date")["rf"]
    rf.index = pd.to_datetime(rf.index)
    rf = rf.reindex(cal).ffill().fillna(0.0)
    first = close.dropna(how="all").index[0]
    close, vol, roll, rf = close.loc[first:], vol.loc[first:], roll.loc[first:], rf.loc[first:]
    rtot = close.ffill().pct_change()
    ex = rtot.sub(rf, axis=0)
    ex.iloc[0] = np.nan
    return close, vol, roll, rf, ex, rtot


def month_end_days(idx: pd.DatetimeIndex) -> list:
    s = pd.Series(idx, index=idx)
    last = s.groupby(idx.to_period("M")).max()
    out = list(last.values)
    # drop the final month if the data stops before the calendar month ends
    if pd.Timestamp(out[-1]) == idx[-1]:
        nxt = idx[-1] + pd.offsets.BDay(1)
        if nxt.month == idx[-1].month:
            out = out[:-1]
    return [pd.Timestamp(x) for x in out]


def ewma_var(x: np.ndarray, com: float = 60, minp: int = 60) -> np.ndarray:
    """EWMA of x^2 with pandas adjust=True semantics written out by hand (NaNs skipped)."""
    a = 1.0 / (1.0 + com)
    out = np.full(len(x), np.nan)
    num = 0.0
    den = 0.0
    n = 0
    for i, v in enumerate(x):
        num *= (1 - a)
        den *= (1 - a)
        if np.isfinite(v):
            num += v * v
            den += 1.0
            n += 1
        if n >= minp and den > 0:
            out[i] = num / den
    return out


def trailing_ms(x: np.ndarray, win: int = 2520, minp: int = 252) -> np.ndarray:
    out = np.full(len(x), np.nan)
    for i in range(len(x)):
        seg = x[max(0, i - win + 1): i + 1]
        seg = seg[np.isfinite(seg)]
        if len(seg) >= minp:
            out[i] = np.mean(seg ** 2)
    return out


class Est:
    def __init__(self, ex: pd.DataFrame, close: pd.DataFrame, vol: pd.DataFrame):
        self.ex = ex
        self.idx = ex.index
        self.me = month_end_days(self.idx)
        self.sE = pd.DataFrame({c: np.sqrt(252 * ewma_var(ex[c].to_numpy())) for c in ex}, index=self.idx)
        self.sL = pd.DataFrame({c: np.sqrt(252 * trailing_ms(ex[c].to_numpy())) for c in ex}, index=self.idx)
        self.sB = 0.7 * self.sE + 0.3 * self.sL
        self.nobs = ex.notna().cumsum()
        traded = (vol.fillna(0) > 0).astype(int)
        self.active = traded.rolling(10, min_periods=1).max() > 0
        # Faber: month-end TR close vs mean of last 10 month-end closes (incl. current)
        mc = close.ffill().loc[self.me]
        self.faber = (mc > mc.rolling(10, min_periods=10).mean()).astype(float)
        self.faber[mc.rolling(10, min_periods=10).mean().isna()] = 0.0

    def ok(self, t, c):
        return (self.nobs.at[t, c] >= 300 and np.isfinite(self.sE.at[t, c]) and self.sE.at[t, c] > 0
                and np.isfinite(self.sL.at[t, c]) and self.sL.at[t, c] > 0 and bool(self.active.at[t, c]))

    def rv_month(self, t, cols, u=None):
        m = self.ex.loc[:t]
        m = m[m.index.to_period("M") == t.to_period("M")][cols].fillna(0.0).to_numpy()
        if u is None:
            return 252 * np.mean(m ** 2, axis=0)
        return 252 * np.mean((m @ u) ** 2)

    def single(self, c, ov, target=0.10, cap_mm=1.5, gcap=4.0, mm_cap=True):
        w = {}
        for t in self.me:
            x = 0.0
            if self.ok(t, c):
                sL = self.sL.at[t, c]
                if ov == "STATIC":
                    x = target / sL
                elif ov in ("CV", "FB"):
                    x = target / self.sE.at[t, c]
                elif ov in ("CVB", "FBB"):
                    x = target / self.sB.at[t, c]
                elif ov == "MM":
                    rv = float(self.rv_month(t, [c])[0])
                    x = target * sL / rv if rv > 0 else 0.0
                    if mm_cap:
                        x = min(x, cap_mm * target / sL)
                if ov in ("FB", "FBB"):
                    x *= self.faber.at[t, c]
                x = min(x, gcap)
            w[t] = {c: x}
        return pd.DataFrame.from_dict(w, orient="index")

    def sb(self, ov, cols=("F_ES", "F_ZN"), target=0.10, gcap=4.0):
        cols = list(cols)
        w = {}
        for t in self.me:
            x = np.zeros(2)
            if all(self.ok(t, c) for c in cols):
                if ov in ("STATIC", "MM"):
                    sL = self.sL.loc[t, cols].to_numpy()
                    h = self.ex.loc[:t, cols].dropna().tail(2520).to_numpy()
                    S = h.T @ h / len(h) * 252
                    b = 1 / sL
                    u = b * target / math.sqrt(b @ S @ b)
                    x = u
                    if ov == "MM":
                        rvu = self.rv_month(t, cols, u)
                        x = u * min(target ** 2 / rvu, 1.5)
                else:
                    sig = (self.sE if ov in ("CV", "FB") else self.sB).loc[t, cols].to_numpy()
                    R = self.ex.loc[:t, cols].tail(252).corr().to_numpy()
                    S = np.diag(sig) @ R @ np.diag(sig)
                    b = 1 / sig
                    x = b * target / math.sqrt(b @ S @ b)
                    if ov in ("FB", "FBB"):
                        x = x * self.faber.loc[t, cols].to_numpy()
                g = np.abs(x).sum()
                if g > gcap:
                    x = x * gcap / g
            w[t] = dict(zip(cols, x))
        return pd.DataFrame.from_dict(w, orient="index")


def sim_daily(wme: pd.DataFrame, rtot: pd.DataFrame, rf: pd.Series, roll: pd.DataFrame, mult=1.0):
    """Target decided at close t (month end) traded at close t+1, earns from t+2; re-traded daily to target."""
    cols = list(wme.columns)
    idx = rtot.index
    tgt = wme.reindex(idx).ffill().fillna(0.0)
    held = tgt.shift(2).fillna(0.0)                      # weight earning the return on day i
    r = rtot[cols].fillna(0.0)
    cb = np.array([COST[c] for c in cols]) * mult / 1e4
    H = held.to_numpy()
    Rr = r.to_numpy()
    RL = roll[cols].to_numpy()
    rfa = rf.to_numpy()
    net = np.zeros(len(idx))
    gross = np.zeros(len(idx))
    turn = np.zeros(len(idx))
    for i in range(len(idx)):
        g = H[i] @ Rr[i] + (1 - H[i].sum()) * rfa[i]
        # trade executed at close i-1 to go from drifted(i-1) to H[i]
        if i >= 1:
            port = H[i - 1] @ Rr[i - 1] + (1 - H[i - 1].sum()) * rfa[i - 1]
            drift = H[i - 1] * (1 + Rr[i - 1]) / (1 + port) if (1 + port) != 0 else H[i - 1]
            tr = np.abs(H[i] - drift)
        else:
            tr = np.abs(H[i])
        tr = tr + 2 * np.abs(H[i]) * RL[i]
        c = tr @ cb
        gross[i] = g
        net[i] = g - c
        turn[i] = tr.sum()
    return pd.Series(net, idx), pd.Series(gross, idx), pd.Series(turn, idx)


def sim_drift(wme: pd.DataFrame, rtot: pd.DataFrame, rf: pd.Series, roll: pd.DataFrame, mult=1.0):
    """Trade to target only at close t+1 after each month-end decision t; positions (notional / NAV) drift between."""
    cols = list(wme.columns)
    idx = rtot.index
    r = rtot[cols].fillna(0.0).to_numpy()
    RL = roll[cols].to_numpy()
    rfa = rf.to_numpy()
    cb = np.array([COST[c] for c in cols]) * mult / 1e4
    pos = {idx.get_loc(t) + 1: wme.loc[t].to_numpy() for t in wme.index if idx.get_loc(t) + 1 < len(idx)}
    h = np.zeros(len(cols))
    net = np.zeros(len(idx))
    gross = np.zeros(len(idx))
    for i in range(len(idx)):
        excess_i = r[i] - rfa[i]
        g = rfa[i] + h @ excess_i                 # fully collateralised: cash earns rf, futures earn excess
        cost = (2 * np.abs(h) * RL[i]) @ cb
        gross[i] = g
        nav_ret = g - cost
        net[i] = nav_ret
        # drift notional/NAV
        h = h * (1 + excess_i) / (1 + nav_ret)
        if i in pos:                               # rebalance at close i
            tgt = pos[i]
            tr = np.abs(tgt - h)
            # charge rebalance trade on the next day's return (cost known at close i) -> charge now
            net[i] -= tr @ cb
            h = tgt.copy()
    return pd.Series(net, idx), pd.Series(gross, idx)


def sharpe(x):
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * math.sqrt(252))


def nw_t(x, lags=None):
    x = pd.Series(x).dropna().to_numpy()
    n = len(x)
    lags = lags or int(4 * (n / 100) ** (2 / 9))
    e = x - x.mean()
    s = e @ e / n
    for k in range(1, lags + 1):
        s += 2 * (1 - k / (lags + 1)) * (e[k:] @ e[:-k]) / n
    return float(x.mean() / math.sqrt(s / n))


def mdd(r):
    eq = (1 + pd.Series(r).fillna(0)).cumprod()
    return float((eq / eq.cummax() - 1).min())
