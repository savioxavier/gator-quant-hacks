"""Adversarial cross-check of PCT base (independent implementation, plain pandas/numpy).

Does NOT import src.strategies.pct for the signal; reads the parquet files directly.
Then compares (a) decision weights and (b) gross returns against the module + engine.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("<solo-repo>")
sys.path.insert(0, str(ROOT))
DATA = Path(os.environ["GQH_DATA_DIR"])
IS_START, IS_END = pd.Timestamp("2005-01-03"), pd.Timestamp("2024-10-02")
TICK = ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "IEF", "LQD", "HYG", "TIP", "GLD", "SLV", "DBC", "UUP", "VNQ"]
OUT = Path(__file__).parent

# ------------------------------------------------------------------ data (direct)
df = pd.read_parquet(DATA / "etf_daily.parquet")
spy_dates = pd.DatetimeIndex(sorted(df.loc[df.ticker == "SPY", "date"].unique()))
cal = spy_dates[(spy_dates >= IS_START) & (spy_dates <= IS_END)]
d = df[df.ticker.isin(TICK) & (df.date >= IS_START) & (df.date <= IS_END)]
close = d.pivot(index="date", columns="ticker", values="close").reindex(index=cal, columns=TICK)
open_ = d.pivot(index="date", columns="ticker", values="open").reindex(index=cal, columns=TICK)
rf = pd.read_parquet(DATA / "rf_daily.parquet").set_index("date")["rf"]
rf.index = pd.to_datetime(rf.index)
rf = rf.loc[:IS_END].reindex(cal).ffill().fillna(0.0)

# ------------------------------------------------------------------ independent null
def my_null(W, legs, n=100_000, seed=12345):
    rng = np.random.default_rng(seed)
    vals = np.empty(n)
    bs = 10_000
    for s in range(0, n, bs):
        inc = rng.standard_normal((bs, legs * W))
        p = np.concatenate([np.zeros((bs, 1)), np.cumsum(inc, axis=1)], axis=1)
        rs = []
        for k in range(legs):
            seg = p[:, k * W: k * W + W + 1]
            t = np.linspace(0.0, 1.0, W + 1)
            ch = seg[:, [0]] + t * (seg[:, [-1]] - seg[:, [0]])
            A = np.abs(seg - ch).mean(axis=1)
            L = np.abs(np.diff(seg, axis=1)).mean(axis=1)
            rs.append(A / (L * math.sqrt(W)))
        vals[s:s + bs] = np.mean(rs, axis=0)
    return vals.mean(), vals.std(ddof=1), vals.std(ddof=1) / math.sqrt(n)

mu0, sd0, se = my_null(63, 4)
print(f"independent null W63x4: mu0={mu0:.5f} sd0={sd0:.5f} (MC se of mean {se:.5f})")

# ------------------------------------------------------------------ month ends
s = pd.Series(cal, index=cal)
month_last = s.groupby(cal.to_period("M")).max()
month_last = month_last[month_last.index != pd.Period("2024-10", "M")]   # incomplete final month
dec_dates = pd.DatetimeIndex(month_last.values)

ret = close.pct_change(fill_method=None)
logp = np.log(close)
nvalid = close.notna().cumsum()

def weights_at(T, mu0, sd0, rf_shift=0):
    i = cal.get_loc(T)
    elig = [t for t in TICK if nvalid.at[T, t] >= 300 and close[t].iloc[i - 252: i + 1].notna().all()]
    if not elig:
        return None, None
    rows = {}
    rf_use = rf.shift(rf_shift).fillna(0.0) if rf_shift else rf
    for t in elig:
        c = close[t].iloc[i - 252: i + 1]
        tr = c.iloc[-1] / c.iloc[0] - 1
        rfw = (1 + rf_use.iloc[i - 251: i + 1]).prod() - 1
        sg = np.sign(tr - rfw)
        vol = ret[t].iloc[i - 62: i + 1].std(ddof=1) * math.sqrt(252)
        lp = logp[t].iloc[i - 252: i + 1].to_numpy()
        Rs = []
        for k in range(4):
            seg = lp[63 * k: 63 * k + 64]
            ch = np.linspace(seg[0], seg[-1], 64)
            Rs.append(np.mean(np.abs(seg - ch)) / (np.mean(np.abs(np.diff(seg))) * math.sqrt(63)))
        z = (np.mean(Rs) - mu0) / sd0
        m = 1 + min(max(z, -1.0), 1.0)
        rows[t] = dict(s=sg, vol=vol, z=z, m=m)
    g = pd.DataFrame(rows).T
    raw = g.s * g.m * 0.40 / g.vol / len(g)
    R = ret[elig].iloc[i - 251: i + 1]
    cov = np.cov(R.to_numpy(), rowvar=False, ddof=1) * 252
    v = float(raw.to_numpy() @ cov @ raw.to_numpy())
    w = raw * (0.10 / math.sqrt(v)) if v > 0 else raw * 0
    if w.abs().sum() > 3:
        w = w * 3 / w.abs().sum()
    return w.reindex(TICK).fillna(0.0), g

W_dec = pd.DataFrame(np.nan, index=cal, columns=TICK)
signs_shift_changes = 0
for T in dec_dates:
    w, g = weights_at(T, mu0, sd0)
    if w is None:
        continue
    W_dec.loc[T] = w.values
W_dec = W_dec.ffill().fillna(0.0)
W_dec.to_pickle(OUT / "xcheck_wdec.pkl")

# rf timing check: sign with rf lagged one day (DTB3 for day T is published after T's close)
from collections import Counter
chg = 0; tot = 0
for T in dec_dates:
    i = cal.get_loc(T)
    for t in TICK:
        if nvalid.at[T, t] >= 300 and close[t].iloc[i - 252: i + 1].notna().all():
            c = close[t].iloc[i - 252: i + 1]
            tr = c.iloc[-1] / c.iloc[0] - 1
            a = np.sign(tr - ((1 + rf.iloc[i - 251: i + 1]).prod() - 1))
            b = np.sign(tr - ((1 + rf.shift(1).fillna(0).iloc[i - 251: i + 1]).prod() - 1))
            tot += 1; chg += int(a != b)
print(f"rf-lag-1 sign changes: {chg} of {tot}")

# ------------------------------------------------------------------ independent returns
rco = (open_ / close.shift(1) - 1).fillna(0.0)
roc = (close / open_ - 1).fillna(0.0)
w_new = W_dec.shift(1).fillna(0.0)   # traded at the open of the day after the decision
w_old = W_dec.shift(2).fillna(0.0)
# simple additive approximation (no overnight compounding cross-term)
gross_simple = (w_old * rco).sum(axis=1) + (w_new * roc).sum(axis=1) + (1 - w_new.sum(axis=1)) * rf
# monthly buy-and-hold (no intra-month rebalancing): open(T+1) -> open(Tnext+1)
mrows = []
for k in range(len(dec_dates) - 1):
    T, Tn = dec_dates[k], dec_dates[k + 1]
    i0, i1 = cal.get_loc(T) + 1, cal.get_loc(Tn) + 1
    if i1 >= len(cal):
        break
    w = W_dec.loc[T]
    if w.abs().sum() == 0:
        continue
    r = (open_.iloc[i1] / open_.iloc[i0] - 1).fillna(0.0)
    rfp = (1 + rf.iloc[i0:i1]).prod() - 1   # approx: return days T+1..Tn
    mrows.append({"date": T, "r": float((w * r).sum() + (1 - w.sum()) * rfp), "rf": rfp})
mon = pd.DataFrame(mrows).set_index("date")

live = w_new.abs().sum(axis=1) > 0
first = live.idxmax()
gs = gross_simple.loc[first:]
ex = gs - rf.loc[first:]
sr_simple = ex.mean() / ex.std() * math.sqrt(252)
mex = mon.r - mon.rf
sr_month = mex.mean() / mex.std() * math.sqrt(12)
print(f"first live day {first.date()}  n={len(gs)}")
print(f"INDEPENDENT gross Sharpe (daily, additive) = {sr_simple:.4f}  ann mean ex = {ex.mean()*252:.5f}")
print(f"INDEPENDENT gross Sharpe (monthly buy&hold, x sqrt12) = {sr_month:.4f}  ann mean ex = {mex.mean()*12:.5f}")
gs.to_pickle(OUT / "xcheck_gross_simple.pkl")
mon.to_pickle(OUT / "xcheck_monthly.pkl")
