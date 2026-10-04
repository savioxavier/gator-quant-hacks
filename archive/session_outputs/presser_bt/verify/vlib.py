"""Independent verification helpers (written separately from backtest/code)."""
import numpy as np, pandas as pd
from pathlib import Path
BT = Path("<scratch>/presser_bt")
V = BT / "verify"
C = Path("<home>/.cache/gqh/presser")
NY = "America/New_York"

def load_1m():
    d = pd.read_parquet(C / "ohlcv-1m__all_2016_2026.parquet")
    d["sym"] = d.symbol.str.slice(0, 2)
    d["et"] = d.ts_event.dt.tz_convert(NY)
    d["day"] = d.et.dt.date.astype(str)
    return d.sort_values(["sym", "ts_event"]).reset_index(drop=True)

def load_bbo():
    q = pd.read_parquet(C / "bbo-1s__all_2016_2026.parquet",
                        columns=["ts_recv", "ts_event", "instrument_id", "bid_px_00", "ask_px_00", "bid_sz_00", "ask_sz_00", "symbol"])
    q["sym"] = q.symbol.str.slice(0, 2)
    q["day"] = q.ts_recv.dt.tz_convert(NY).dt.date.astype(str)
    return q.sort_values(["sym", "ts_recv"]).reset_index(drop=True)

def tick(sym, day):
    # ZT tick reduced to 1/256 effective trade date 2019-01-14 (no presser between 2018-12-19 and 2019-01-30)
    if sym == "ZT":
        return 1/128 if day < "2019-01-14" else 1/256
    return {"ZF": 1/128, "ZN": 1/64, "ES": 0.25}[sym]

PT_USD = {"ZT": 2000.0, "ZF": 1000.0, "ZN": 1000.0, "ES": 50.0}

def ts(day, hms):
    return pd.Timestamp(f"{day} {hms}").tz_localize(NY)

class Px:
    """1m lookups via explicit filtering (independent of the backtest's searchsorted code)."""
    def __init__(self, d):
        self.by = {k: g.reset_index(drop=True) for k, g in d.groupby(["day", "sym"])}
    def next_open(self, day, sym, t):
        g = self.by.get((day, sym))
        if g is None: return None, np.nan
        h = g[g.et >= t]
        if h.empty: return None, np.nan
        return h.et.iloc[0], h.open.iloc[0]
    def close_before(self, day, sym, T, lo=None):
        """close of last bar whose END (start+60s) <= T"""
        g = self.by.get((day, sym))
        if g is None: return None, np.nan
        h = g[(g.et + pd.Timedelta(seconds=60)) <= T]
        if lo is not None: h = h[h.et >= lo]
        if h.empty: return None, np.nan
        return h.et.iloc[-1], h.close.iloc[-1]

def clean_bbo(q):
    ok = (q.bid_px_00 > 0) & (q.ask_px_00 > q.bid_px_00) & (q.bid_sz_00 > 0) & (q.ask_sz_00 > 0)
    return q[ok].copy(), int((~ok).sum())

def quote_asof(qc, req):
    """req: DataFrame with sym, t (tz-aware). Returns req + bid, ask, qts (last clean record with ts_recv <= t)."""
    r = req.copy()
    r["t_utc"] = r.t.dt.tz_convert("UTC").dt.as_unit("ns")
    r = r.reset_index().rename(columns={"index": "_rid"}).sort_values("t_utc")
    qq = qc[["sym", "ts_recv", "bid_px_00", "ask_px_00"]].sort_values("ts_recv")
    out = pd.merge_asof(r, qq, left_on="t_utc", right_on="ts_recv", by="sym", direction="backward")
    out["stale_s"] = (out.t_utc - out.ts_recv).dt.total_seconds()
    # must be same ET day
    out.loc[out.ts_recv.dt.tz_convert(NY).dt.date.astype(str) != out.t.dt.tz_convert(NY).dt.date.astype(str), ["bid_px_00", "ask_px_00"]] = np.nan
    return out.sort_values("_rid").set_index("_rid").rename(columns={"bid_px_00": "bid", "ask_px_00": "ask"})


# ---------------- statistics (own implementations)
def signflip_p(y, side="greater", B=200000, seed=7):
    """Sign-flip test of mean 0. The studentised t is monotone in the mean under sign flips
    (sum of squares is invariant), so the mean is used. Exact enumeration for n <= 22, else Monte Carlo."""
    y = np.asarray(y, float); n = len(y); m0 = y.mean()
    if n <= 22:
        res = []
        for start in range(0, 2 ** n, 2 ** 18):
            k = np.arange(start, min(start + 2 ** 18, 2 ** n))
            S = ((k[:, None] >> np.arange(n)) & 1) * 2 - 1
            res.append((S * y).mean(1))
        ms = np.concatenate(res)
        if side == "greater": return float(np.mean(ms >= m0 - 1e-12))
        if side == "less": return float(np.mean(ms <= m0 + 1e-12))
        return float(np.mean(np.abs(ms) >= abs(m0) - 1e-12))
    rng = np.random.default_rng(seed)
    ms = (rng.choice([-1., 1.], size=(B, n)) * y).mean(1)
    if side == "greater": return float((1 + np.sum(ms >= m0 - 1e-12)) / (B + 1))
    if side == "less": return float((1 + np.sum(ms <= m0 + 1e-12)) / (B + 1))
    return float((1 + np.sum(np.abs(ms) >= abs(m0) - 1e-12)) / (B + 1))


def block_ci(y, B=20000, seed=11):
    y = np.asarray(y, float); n = len(y)
    b = max(2, int(round(n ** (1 / 3)))); nb = -(-n // b)
    rng = np.random.default_rng(seed)
    st = rng.integers(0, n, size=(B, nb))
    idx = ((st[:, :, None] + np.arange(b)) % n).reshape(B, -1)[:, :n]
    ms = y[idx].mean(1)
    return float(np.percentile(ms, 5)), float(np.percentile(ms, 95)), b


def summ(y):
    y = np.asarray(pd.Series(y).dropna(), float); n = len(y)
    if n < 2:
        return dict(n=n, mean=float(y.mean()) if n else np.nan)
    sd = y.std(ddof=1); t = y.mean() / (sd / np.sqrt(n)) if sd > 0 else np.nan
    lo, hi, b = block_ci(y)
    return dict(n=n, mean=float(y.mean()), sd=float(sd), t=float(t), hit=float((y > 0).mean()),
                p_one_gt=signflip_p(y, "greater"), p_two=signflip_p(y, "two"), ci90_lo=lo, ci90_hi=hi)


def cluster_summ(y, g, B=9999, seed=5):
    """Answer-level mean, CR1 cluster t, and a wild cluster bootstrap (Rademacher, null imposed) two-sided p."""
    y = np.asarray(y, float); g = np.asarray(g)
    u, gi = np.unique(g, return_inverse=True); G = len(u); n = len(y)
    m = y.mean()
    S = np.bincount(gi, weights=y - m)
    se = np.sqrt(G / (G - 1) * np.sum(S ** 2)) / n
    t = m / se if se > 0 else np.nan
    rng = np.random.default_rng(seed)
    w = rng.choice([-1., 1.], size=(B, G))
    ys = np.bincount(gi, weights=y); cnt = np.bincount(gi).astype(float)
    ms = (w @ ys) / n
    Ss = w * ys - ms[:, None] * cnt
    ses = np.sqrt(G / (G - 1) * np.sum(Ss ** 2, 1)) / n
    ts_ = ms / ses
    return dict(n=n, G=G, mean=float(m), t_cr1=float(t),
                p_two=float((1 + np.sum(np.abs(ts_) >= abs(t))) / (B + 1)))
