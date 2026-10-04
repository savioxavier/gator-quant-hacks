"""Carver-style continuous forecasts (pysystemtrade rules) on the 30 CME futures, as declared in the SPEC.md files of
trend_momentum_carver_ewmac_breakout and trend_momentum_carver_staunch_trend_carry."""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

import common as K

CAP = 20.0
EWMAC_SCALARS = {(8, 32): 5.3, (16, 64): 3.75, (32, 128): 2.65, (64, 256): 1.87}
BREAKOUT_SCALARS = {20: 0.67, 40: 0.70, 80: 0.73, 160: 0.74, 320: 0.74}
CARRY_SCALAR = 30.0
CARRY_COM = 90
FDM_CAP = 2.5
FDM_SPAN = 125
BUFFER = 0.10
INSTR_VOL = 0.10
CONTRACTS = Path("<scratch>"
                 "/scratchpad/edges/carry/contracts.parquet")


# ------------------------------------------------------------------------------------------- prices / vol

@lru_cache(maxsize=1)
def price_and_vol():
    P = K.panel()
    ex = P["ex"]
    started = ex.notna().cumsum() > 0
    px = (1 + ex.fillna(0.0)).cumprod().where(started)
    # robust_vol_calc (pysystemtrade sysquant/estimators/vol.py) on daily price differences
    d = px.diff()
    v = d.ewm(span=35, min_periods=10, adjust=True).std()
    v = v.where(v >= 1e-10, 1e-10).where(v.notna())
    floor = v.rolling(500, min_periods=100).quantile(0.05)
    floor = floor.fillna(0.0)  # zero until 100 observations exist (pysystemtrade: first value 0 then ffill)
    v = np.maximum(v, floor).where(v.notna())
    sigma = v / px * math.sqrt(252)          # annualised % vol of the instrument
    return px, v, sigma


# ------------------------------------------------------------------------------------------- rules

def ewmac(f: int, s: int) -> pd.DataFrame:
    px, v, _ = price_and_vol()
    fast = px.ewm(span=f, min_periods=1).mean()
    slow = px.ewm(span=s, min_periods=1).mean()
    raw = (fast - slow) / v.ffill()
    return (raw * EWMAC_SCALARS[(f, s)]).clip(-CAP, CAP)


def breakout(n: int) -> pd.DataFrame:
    px, _, _ = price_and_vol()
    smooth = max(int(n / 4.0), 1)
    mp = int(math.ceil(n / 2.0))
    rmax = px.rolling(n, min_periods=mp).max()
    rmin = px.rolling(n, min_periods=mp).min()
    mid = (rmax + rmin) / 2.0
    out = 40.0 * (px - mid) / (rmax - rmin)
    out = out.replace([np.inf, -np.inf], np.nan)
    sm = out.ewm(span=smooth, min_periods=int(math.ceil(smooth / 2.0))).mean()
    return (sm * BREAKOUT_SCALARS[n]).clip(-CAP, CAP)


@lru_cache(maxsize=1)
def carry_ann_roll() -> pd.DataFrame:
    """Annualised roll (fraction of the held .v.0 price per year), NYSE calendar, lagged one extra session."""
    P = K.panel()
    cal = P["ex"].index
    c = pd.read_parquet(CONTRACTS)
    p = c.pivot_table(index=["root", "date"], columns="rank", values=["close", "month_index"], aggfunc="first")
    p.columns = [f"{a}{b}" for a, b in p.columns]
    p = p.reset_index()
    ok = (p["close0"] > 0) & (p["close1"] > 0) & p["month_index0"].notna() & p["month_index1"].notna()
    p = p[ok].copy()
    dm = (p["month_index1"] - p["month_index0"])
    p = p[(dm != 0) & (dm.abs() <= 12)].copy()
    near0 = p["month_index0"] < p["month_index1"]
    p_near = np.where(near0, p["close0"], p["close1"])
    p_far = np.where(near0, p["close1"], p["close0"])
    dt = (p["month_index1"] - p["month_index0"]).abs() / 12.0
    p["ann_roll"] = (p_near - p_far) / p["close0"] / dt
    pos = cal.searchsorted(p["date"].values, side="left")
    keep = pos < len(cal)
    o = p[keep].copy()
    o["nyse"] = cal[pos[keep]]
    o = o.sort_values(["root", "date"]).groupby(["root", "nyse"]).last().reset_index()
    wide = o.pivot(index="nyse", columns="root", values="ann_roll").reindex(index=cal)
    wide = wide.reindex(columns=K.ROOTS)
    wide.columns = [f"F_{r}" for r in wide.columns]
    return wide.shift(1)


def carry() -> pd.DataFrame:
    _, _, sigma = price_and_vol()
    ann = carry_ann_roll()
    raw = ann / sigma
    sm = raw.ewm(com=CARRY_COM).mean()
    fresh = raw.notna().astype(float).rolling(21, min_periods=1).max() > 0
    sm = sm.where(fresh)
    return (sm * CARRY_SCALAR).clip(-CAP, CAP)


# ------------------------------------------------------------------------------------------- combination

def fdm_trailing(forecasts: dict, weights: dict) -> pd.Series:
    """Pooled, expanding, weekly-sampled forecast correlation -> FDM, month-end estimates used from the next
    session, EWMA span 125 smoothing, cap 2.5."""
    names = list(forecasts)
    cal = forecasts[names[0]].index
    we = K.week_ends(cal)
    w = np.array([weights[n] for n in names], dtype=float)
    w = w / w.sum()
    # stack weekly samples: rows (week, instrument), cols rules
    arr = np.stack([forecasts[n].reindex(we).to_numpy() for n in names], axis=-1)   # (W, I, R)
    me = K.month_ends(cal)
    est = {}
    for m in me:
        k = int(np.searchsorted(we.values, np.datetime64(m), side="right"))
        if k < 52:
            continue
        x = arr[:k].reshape(-1, len(names))
        x = x[np.isfinite(x).all(axis=1)]
        weeks_ok = np.isfinite(arr[:k]).all(axis=-1).any(axis=1).sum()
        if weeks_ok < 52 or len(x) < 100:
            continue
        R = np.corrcoef(x, rowvar=False)
        R = np.clip(R, 0.0, None)
        val = float(1.0 / math.sqrt(w @ R @ w))
        est[m] = min(val, FDM_CAP)
    s = pd.Series(est, dtype=float)
    daily = s.reindex(cal).shift(1).ffill()
    return daily.ewm(span=FDM_SPAN, min_periods=1).mean().where(daily.notna())


def combine(forecasts: dict, weights: dict, fdm) -> pd.DataFrame:
    names = list(forecasts)
    num = None
    den = None
    for n in names:
        f = forecasts[n]
        a = f.notna().astype(float) * weights[n]
        term = f.fillna(0.0) * weights[n]
        num = term if num is None else num + term
        den = a if den is None else den + a
    comb = num / den.replace(0.0, np.nan)
    if isinstance(fdm, pd.Series):
        comb = comb.mul(fdm, axis=0)
    else:
        comb = comb * float(fdm)
    return comb.clip(-CAP, CAP)


# ------------------------------------------------------------------------------------------- positions

@lru_cache(maxsize=1)
def cov_cube() -> np.ndarray:
    """Trailing 252-session sample covariance (min 60 obs per pair, NaN -> 0) for every session; (T, I, I)."""
    P = K.panel()
    ex = P["ex"][K.TICK]
    T, I = ex.shape
    out = np.zeros((T, I, I))
    for i in range(T):
        lo = max(0, i - K.COV_WINDOW + 1)
        out[i] = ex.iloc[lo:i + 1].cov(min_periods=60).fillna(0.0).to_numpy()
    return out


def positions(comb: pd.DataFrame, buffer: bool = True) -> tuple[pd.DataFrame, pd.Series]:
    """Daily decision weights with book scaling to 10 % ex-ante (gross <= 3) and Carver's 10 % buffer."""
    P = K.panel()
    _, _, sigma = price_and_vol()
    ok = P["base_elig"] & np.isfinite(sigma) & (sigma > 0) & comb.notna()
    n = ok.sum(axis=1)
    F = comb.where(ok, 0.0).fillna(0.0).to_numpy()
    sig = sigma.where(ok).to_numpy()
    nn = n.to_numpy().astype(float)
    cov = cov_cube()
    T, I = F.shape
    out = np.zeros((T, I))
    kser = np.full(T, np.nan)
    cur = np.zeros(I)
    okv = ok.to_numpy()
    for t in range(T):
        if nn[t] <= 0:
            cur = np.zeros(I)
            out[t] = cur
            continue
        base = np.where(okv[t], INSTR_VOL / sig[t] / nn[t], 0.0)        # position at forecast 10, unscaled
        u = F[t] / 10.0 * base
        if not np.any(u != 0):
            cur = np.where(okv[t], cur, 0.0) * 0.0
            out[t] = cur
            continue
        var = float(u @ cov[t] @ u) * 252
        if not np.isfinite(var) or var <= 0:
            cur = np.zeros(I)
            out[t] = cur
            continue
        k = TARGET = K.TARGET_VOL / math.sqrt(var)
        g = np.abs(k * u).sum()
        if g > K.GROSS_CAP:
            k = K.GROSS_CAP / np.abs(u).sum()
        kser[t] = k
        tgt = k * u
        if buffer:
            band = BUFFER * k * base
            cur = np.clip(cur, tgt - band, tgt + band)
            cur = np.where(okv[t], cur, 0.0)
        else:
            cur = tgt
        out[t] = cur
    return pd.DataFrame(out, index=comb.index, columns=K.TICK), pd.Series(kser, index=comb.index)
