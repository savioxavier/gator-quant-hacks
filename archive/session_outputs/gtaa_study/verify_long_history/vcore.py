"""Independent implementation of the timing rules, execution, stats and bootstrap."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

COST = 0.0010


def month_signal(lvl: np.ndarray, rf_m: np.ndarray, rule: str) -> np.ndarray:
    """lvl: month-end levels, rf_m: monthly cash returns (same index). Returns 1/0/nan per month."""
    n = len(lvl)
    s = np.full(n, np.nan)
    if rule.startswith("SMA"):
        k = int(rule[3:])
        for t in range(k - 1, n):
            s[t] = 1.0 if lvl[t] > lvl[t - k + 1:t + 1].mean() else 0.0
    elif rule == "MOM12":
        for t in range(12, n):
            cash = np.prod(1 + rf_m[t - 11:t + 1]) - 1
            s[t] = 1.0 if lvl[t] / lvl[t - 12] - 1 > cash else 0.0
    return s


def daily_strict(R: pd.Series, rf: pd.Series, rule: str | None, cost: float = COST) -> pd.DataFrame:
    """Signal at the last session T of each month; trade at the close of T+1; earns from T+2."""
    df = pd.concat([R.rename("R"), rf.rename("rf")], axis=1).dropna()
    idx = df.index
    n = len(idx)
    pos = np.full(n, np.nan)
    dec_i = np.full(n, -1)
    if rule is None:
        pos[:] = 1.0
    else:
        lvl = np.cumprod(1 + df["R"].to_numpy())
        per = idx.to_period("M")
        last_i = np.flatnonzero(per[:-1] != per[1:])          # last session of each complete month
        rf_m = (1 + df["rf"]).groupby(per).prod().to_numpy() - 1
        # month index of each last_i
        mcodes = pd.Index(per.unique())
        mi = mcodes.get_indexer(per[last_i])
        sig = month_signal(lvl[last_i], rf_m[mi], rule)
        for j, iT in enumerate(last_i):
            a = iT + 2
            b = last_i[j + 1] + 2 if j + 1 < len(last_i) else n
            if a < n:
                pos[a:min(b, n)] = sig[j]
                dec_i[a:min(b, n)] = iT
        # point-in-time check: every return day uses a decision at least 2 sessions old
        used = np.flatnonzero(dec_i >= 0)
        assert (used - dec_i[used] >= 2).all()
    p = pd.Series(pos, index=idx)
    sw = p.diff().abs().fillna(0.0)
    gross = p * df["R"] + (1 - p) * df["rf"]
    return pd.DataFrame({"R": df["R"], "rf": df["rf"], "pos": p, "sw": sw, "gross": gross,
                         "net": gross - cost * sw})


def monthly_run(Rdf: pd.DataFrame, rf: pd.Series, rule: str | None, lag: int = 1, cost: float = COST) -> pd.DataFrame:
    """1/N sleeves monthly; sleeve in cash when its own signal (lagged `lag` months) is off."""
    df = pd.concat([Rdf, rf.rename("rf")], axis=1).dropna()
    A = list(Rdf.columns)
    N = len(A)
    if rule is None:
        P = pd.DataFrame(1.0, index=df.index, columns=A)
    else:
        P = pd.DataFrame({a: month_signal(np.cumprod(1 + df[a].to_numpy()), df["rf"].to_numpy(), rule)
                          for a in A}, index=df.index).shift(lag)
    W = P / N
    R = df[A]
    gross = (W * R).sum(axis=1, min_count=N) + (1 - W.sum(axis=1, min_count=N)) * df["rf"]
    drift = (W.shift(1) * (1 + R.shift(1))).div(1 + gross.shift(1), axis=0)
    turn = (W - drift).abs().sum(axis=1, min_count=N)
    net = gross - cost * turn.fillna(0.0)
    return pd.DataFrame({"rf": df["rf"], "gross": gross, "net": net, "pos": W.sum(axis=1, min_count=N),
                         "turn": turn})


def sharpe(ex: np.ndarray, f: float) -> float:
    return float(ex.mean() / ex.std(ddof=1) * math.sqrt(f))


def mdd(r: pd.Series) -> float:
    e = (1 + r).cumprod()
    return float((e / e.cummax() - 1).min())


def stats(df: pd.DataFrame, f: float) -> dict:
    ex = (df["net"] - df["rf"]).to_numpy()
    yrs = len(df) / f
    return {"sharpe": sharpe(ex, f), "cagr": float((1 + df["net"]).prod() ** (1 / yrs) - 1),
            "vol": float(df["net"].std(ddof=1) * math.sqrt(f)), "mdd": mdd(df["net"]), "years": yrs}


def boot_dsr(a: np.ndarray, b: np.ndarray, f: float, L: int, B: int = 2000, seed: int = 11):
    """Paired circular block bootstrap of SR(a)-SR(b). Returns (lo, hi, se, p<=0)."""
    n = len(a)
    rng = np.random.default_rng(seed)
    nb = -(-n // L)
    out = np.empty(B)
    for i in range(B):
        st = rng.integers(0, n, nb)
        ii = ((st[:, None] + np.arange(L)[None, :]).ravel()[:n]) % n
        x, y = a[ii], b[ii]
        out[i] = (x.mean() / x.std(ddof=1) - y.mean() / y.std(ddof=1)) * math.sqrt(f)
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)), float(out.std(ddof=1)), float((out <= 0).mean())


def boot_median_dsr(exs: list[np.ndarray], bex: np.ndarray, f: float, L: int, B: int = 2000, seed: int = 5):
    n = len(bex)
    rng = np.random.default_rng(seed)
    nb = -(-n // L)
    out = np.empty(B)
    for i in range(B):
        st = rng.integers(0, n, nb)
        ii = ((st[:, None] + np.arange(L)[None, :]).ravel()[:n]) % n
        y = bex[ii]
        sb = y.mean() / y.std(ddof=1)
        out[i] = np.median([(x[ii].mean() / x[ii].std(ddof=1) - sb) for x in exs]) * math.sqrt(f)
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))
