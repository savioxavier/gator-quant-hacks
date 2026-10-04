"""Independent re-implementation of the GTAA grid (verification). Read-only w.r.t. the repo."""
import os, sys, math, itertools
import numpy as np, pandas as pd
REPO = "<solo-repo>"
sys.path.insert(0, REPO)
assert os.environ.get("GQH_OOS_UNLOCK") != "1"
from src import engine as E

UNI = {"frozen5": ["SPY", "EFA", "IEF", "VNQ", "DBC"],
       "broad10": ["SPY", "EFA", "EEM", "IEF", "TLT", "LQD", "TIP", "VNQ", "GLD", "DBC"],
       "eq4": ["SPY", "EFA", "EEM", "VNQ"]}
SIGS = ["SMA6", "SMA8", "SMA10", "SMA12", "MOM12", "SMA10_D1"]
WTS = ["equal", "invvol63"]
ROFF = ["tbill", "IEF"]
TICK = sorted(set(sum(UNI.values(), [])))


def complete_month_ends(cal, data_end):
    """Last session of each calendar month; the final month only if the calendar month is over."""
    s = pd.Series(cal, index=cal)
    last = s.groupby(cal.to_period("M")).max()
    me = pd.DatetimeIndex(last.values)
    # drop final month if data ended before the month was over (no later session in the same month known)
    if me[-1] == cal[-1]:
        nxt = cal[-1] + pd.offsets.BDay(1)
        if nxt.month == cal[-1].month:   # month not finished yet
            me = me[:-1]
    return me


def signal_monthly(close_m, rf_growth_m, sig):
    if sig.startswith("SMA") and not sig.endswith("D1"):
        n = int(sig[3:])
        out = pd.DataFrame(np.nan, index=close_m.index, columns=close_m.columns)
        arr = close_m.to_numpy()
        for i in range(len(arr)):
            if i + 1 < n:
                continue
            win = arr[i + 1 - n:i + 1]
            ok = ~np.isnan(win).any(0)
            m = win.mean(0)
            out.iloc[i] = np.where(ok, (arr[i] > m).astype(float), np.nan)
        return out
    if sig == "MOM12":
        r12 = close_m / close_m.shift(12) - 1
        tb = rf_growth_m / rf_growth_m.shift(12) - 1
        out = (r12.gt(tb, axis=0)).astype(float)
        return out.where(r12.notna() & tb.notna().values[:, None])
    raise ValueError(sig)


def signal_daily_band(close, me, band=0.01, n=10):
    cm = close.loc[me]
    sma = cm.rolling(n, min_periods=n).mean()
    # SMA known at a month-end close and kept until next month-end
    sma_d = sma.reindex(close.index, method=None).ffill()
    out = pd.DataFrame(np.nan, index=close.index, columns=close.columns)
    for c in close.columns:
        st = np.nan
        p = close[c].to_numpy(); s = sma_d[c].to_numpy(); res = np.full(len(p), np.nan)
        for i in range(len(p)):
            if np.isnan(s[i]) or (np.isnan(p[i]) and np.isnan(st)):
                continue
            if np.isnan(st):
                st = float(p[i] > s[i])
            elif not np.isnan(p[i]):
                if st == 1.0 and p[i] < s[i] * (1 - band): st = 0.0
                elif st == 0.0 and p[i] > s[i] * (1 + band): st = 1.0
            res[i] = st
        out[c] = res
    return out


def build_decisions(key, close, rf, me, start_dec, timed=True):
    sig, uni, wt, ro = key
    tk = UNI[uni]
    cal = close.index
    if wt == "equal":
        bw = pd.DataFrame(1.0 / len(tk), index=me, columns=tk)
        bw = bw.where(close.loc[me, tk].notna().all(1), np.nan, axis=0)
    else:
        r = np.log(close[tk]).diff()  # use log returns for vol: independent choice, near-identical
        r = close[tk].pct_change(fill_method=None)
        v = r.rolling(63, min_periods=63).std().loc[me]
        iv = 1 / v
        bw = iv.div(iv.sum(1, skipna=False), axis=0)
    if not timed:
        on_m = bw.notna().astype(float).where(bw.notna())
        on = on_m.reindex(cal).ffill()
    elif sig == "SMA10_D1":
        on = signal_daily_band(close[tk], me)
    else:
        growth = (1 + rf.reindex(cal).fillna(0.0)).cumprod().loc[me]
        on = signal_monthly(close.loc[me, tk], growth, sig).reindex(cal).ffill()
    bwd = bw.reindex(cal).ffill()
    won = bwd * on
    valid = won.notna().all(1)
    cols = tk + (["IEF"] if ro == "IEF" and "IEF" not in tk else [])
    W = pd.DataFrame(0.0, index=cal, columns=cols)
    W[tk] = won.fillna(0.0)
    if ro == "IEF":
        W["IEF"] = W["IEF"] + (bwd * (1 - on)).sum(1)
    W[~valid] = 0.0
    W[W.index < start_dec] = 0.0
    return W, valid


def first_valid(key, close, rf, me, timed=True):
    W, valid = build_decisions(key, close, rf, me, pd.Timestamp("1900-01-01"), timed)
    v = valid.loc[me]
    return v[v].index[0]


def sharpe(ex):
    ex = pd.Series(ex).dropna()
    return float(ex.mean() / ex.std() * math.sqrt(252))


def mdd(r):
    eq = (1 + r).cumprod(); return float((eq / eq.cummax() - 1).min())


def boot_idx(T, L, B, seed):
    rng = np.random.default_rng(seed)
    nb = int(math.ceil(T / L))
    st = rng.integers(0, T, size=(B, nb))
    idx = (st[:, :, None] + np.arange(L)[None, None, :]) % T
    return idx.reshape(B, -1)[:, :T]


def boot_sharpes(X, L=63, B=1000, seed=11, chunk=20):
    X = np.asarray(X, float); T, N = X.shape
    idx = boot_idx(T, L, B, seed)
    out = np.empty((B, N))
    for a in range(0, B, chunk):
        Y = X[idx[a:a + chunk]]  # c x T x N
        out[a:a + chunk] = Y.mean(1) / Y.std(1, ddof=1) * math.sqrt(252)
    return out
