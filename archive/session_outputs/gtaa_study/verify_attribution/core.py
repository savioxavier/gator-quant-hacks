"""Independent re-implementation of S3 (Faber GTAA) and BH5 from the raw cache, plus an explicit NAV simulator."""
import numpy as np, pandas as pd, math, os
D = os.environ.get("GQH_DATA_DIR", "<home>/.cache/gqh")
TK = ["SPY", "EFA", "IEF", "VNQ", "DBC"]
BPS = {"SPY": 3, "EFA": 3, "IEF": 3, "VNQ": 5, "DBC": 5}
START = pd.Timestamp("2005-01-03")
IS_END = pd.Timestamp("2024-10-02"); OOS_START = pd.Timestamp("2024-10-03")

def load(end=None):
    e = pd.read_parquet(f"{D}/etf_daily.parquet")
    cal = pd.DatetimeIndex(sorted(e.loc[e.ticker == "SPY", "date"].unique()))
    cal = cal[cal >= START]
    if end is not None: cal = cal[cal <= pd.Timestamp(end)]
    e = e[e.ticker.isin(TK)]
    px = {c: e.pivot(index="date", columns="ticker", values=c).reindex(cal)[TK] for c in ("open", "close")}
    rf = pd.read_parquet(f"{D}/rf_daily.parquet").set_index("date")["rf"]
    rf.index = pd.to_datetime(rf.index); rf = rf.reindex(cal).ffill().fillna(0.0)
    return px, rf

def month_ends(cal):
    s = pd.Series(cal, index=cal)
    me = s.groupby(cal.to_period("M")).max()
    # drop last month if incomplete (calendar ends before the month's final business day)
    last = cal[-1]
    if (last + pd.offsets.BDay(1)).month == last.month:
        me = me.iloc[:-1]
    return pd.DatetimeIndex(me.values)

def decisions(close, bh=False, n=10):
    cal = close.index
    me = month_ends(cal)
    mc = close.loc[me]
    out = pd.DataFrame(np.nan, index=cal, columns=close.columns)
    for i, t in enumerate(me):
        if i < n - 1:
            out.loc[t] = 0.0; continue
        window = mc.iloc[i - n + 1:i + 1]   # the n month-end closes up to and including t (known at close t)
        sma = window.mean(skipna=False)
        cur = mc.iloc[i]
        ok = sma.notna() & cur.notna()
        sig = ok if bh else (ok & (cur > sma))
        out.loc[t] = sig.astype(float).values * 0.2
    return out.ffill().fillna(0.0)

def sim_formula(w_dec, px, rf):
    """next-open: decision at close d is the target held from the open of d+1 (rebalanced to target each open)."""
    close = px["close"].ffill(limit=5); open_ = px["open"].ffill(limit=5)
    w_dec = w_dec.reindex(close.index).fillna(0.0)
    held = w_dec.shift(1).fillna(0.0).values      # target in force today (decided at yesterday's close)
    prev = w_dec.shift(2).fillna(0.0).values      # target in force yesterday
    c = close.values; o = open_.values
    rco = np.nan_to_num(o / np.vstack([np.full((1, c.shape[1]), np.nan), c[:-1]]) - 1)
    roc = np.nan_to_num(c / o - 1)
    on = (prev * rco).sum(1)
    risky = on + (1 + on) * (held * roc).sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        drift = np.nan_to_num(prev * (1 + rco) / (1 + on)[:, None])
    bps = np.array([BPS[t] for t in w_dec.columns]) / 1e4
    trade = np.abs(held - drift)
    cost_i = trade * bps
    gross = risky + (1 - held.sum(1)) * rf.values
    net = gross - cost_i.sum(1)
    idx = close.index
    return (pd.Series(net, idx), pd.DataFrame(held, idx, w_dec.columns), pd.DataFrame(cost_i, idx, w_dec.columns),
            pd.DataFrame(prev * rco, idx, w_dec.columns), pd.DataFrame((1 + on)[:, None] * held * roc, idx, w_dec.columns))

def sim_nav(w_dec, px, rf):
    """Explicit dollar simulation: positions drift intraday/overnight, rebalance to target at each open, pay costs."""
    close = px["close"].ffill(limit=5).values; open_ = px["open"].ffill(limit=5).values
    w = w_dec.reindex(px["close"].index).fillna(0.0).shift(1).fillna(0.0).values
    bps = np.array([BPS[t] for t in w_dec.columns]) / 1e4
    nav = 1.0; pos = np.zeros(len(TK)); cash = 1.0; navs = []
    for d in range(len(w)):
        if d > 0:
            ratio = np.where(np.isfinite(open_[d] / close[d - 1]), open_[d] / close[d - 1], 1.0)
            pos = pos * ratio
        nav_open = cash + pos.sum()
        tgt = w[d] * nav_open
        cost = (np.abs(tgt - pos) * bps).sum()
        pos = tgt.copy(); cash = nav_open - pos.sum() - cost
        r = np.where(np.isfinite(close[d] / open_[d]), close[d] / open_[d], 1.0)
        pos = pos * r
        cash = cash * (1 + rf.values[d])
        navs.append(cash + pos.sum())
    navs = pd.Series(navs, px["close"].index)
    return navs.pct_change().fillna(navs.iloc[0] - 1)

def sharpe(ex):
    return ex.mean() / ex.std(ddof=1) * math.sqrt(252)

def mdd(r):
    eq = (1 + r).cumprod(); return (eq / eq.cummax() - 1).min()

def periods(s, first):
    s = s[s.index >= first]
    return {"IS": s[s.index <= IS_END], "OOS": s[s.index >= OOS_START]}

def block_boot(x, y, stat, block=63, reps=5000, seed=1):
    """paired circular block bootstrap of stat(x)-stat(y)"""
    rng = np.random.default_rng(seed)
    n = len(x); x = np.asarray(x); y = np.asarray(y)
    nb = int(np.ceil(n / block)); out = np.empty(reps)
    for k in range(reps):
        st = rng.integers(0, n, nb)
        ix = ((st[:, None] + np.arange(block)[None, :]) % n).ravel()[:n]
        out[k] = stat(x[ix]) - stat(y[ix])
    return out

def sr_np(a):
    return a.mean() / a.std(ddof=1) * math.sqrt(252)
