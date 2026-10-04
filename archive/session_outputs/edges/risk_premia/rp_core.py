"""Risk-managed passive premia: weight construction shared by the futures run and the long-history proxy run.

Rules are fixed in SPEC.md (written before any result). Decision at month-end close d uses data up to d only.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<solo-repo>")
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src import calendar_utils as CU  # noqa: E402
from src import engine as E  # noqa: E402


def _forbidden(*a, **k):
    raise RuntimeError("logging / run_backtest is disabled in this study (no writes to results/)")


E.log_trial = _forbidden
E.log_trials_bulk = _forbidden
E.run_backtest = _forbidden

HERE = Path(__file__).resolve().parent
EDGES = HERE.parent
SERIES_DIR = EDGES / "series"
OUT = HERE / "out"

TARGET = 0.10
GROSS_CAP = 4.0
MM_CAP = 1.5
EWMA_COM = 60
LR_WIN = 2520
LR_MIN = 252
COR_WIN = 252
MIN_HISTORY = 300
ACTIVE_WINDOW = 10
SMA_MONTHS = 10

OVERLAYS = ["STATIC", "CV", "CVB", "MM", "FB", "FBB"]


def month_ends(cal: pd.DatetimeIndex) -> pd.DatetimeIndex:
    mo = CU.month_offsets(cal)
    return mo.index[mo["off_own"] == 0]


class Panel:
    """Excess returns, total-return closes and the derived estimators for a set of assets."""

    def __init__(self, ex: pd.DataFrame, close: pd.DataFrame, active: pd.DataFrame | None = None):
        self.ex = ex
        self.close = close.ffill()
        self.cols = list(ex.columns)
        sq = ex.pow(2)
        self.sE = np.sqrt(sq.ewm(com=EWMA_COM, min_periods=60).mean() * 252)
        self.sL = np.sqrt(sq.rolling(LR_WIN, min_periods=LR_MIN).mean() * 252)
        self.sB = 0.7 * self.sE + 0.3 * self.sL
        per = ex.index.to_period("M")
        self.rv = sq.groupby(per).transform("mean") * 252         # valid at month ends: that month's days <= d
        self.counts = ex.notna().cumsum()
        self.active = active if active is not None else pd.DataFrame(True, index=ex.index, columns=self.cols)
        self.me = month_ends(ex.index)
        mclose = self.close.loc[self.me]
        sma = mclose.rolling(SMA_MONTHS, min_periods=SMA_MONTHS).mean()
        self.trend_on = ((mclose > sma) & sma.notna()).astype(float)
        self.cap_hits = {}

    def eligible(self, t, c) -> bool:
        s = self.sE.loc[t, c]
        return bool(self.counts.loc[t, c] >= MIN_HISTORY and np.isfinite(s) and s > 0
                    and np.isfinite(self.sL.loc[t, c]) and self.sL.loc[t, c] > 0 and self.active.loc[t, c])

    # ------------------------------------------------------------------ single asset
    def single(self, asset: str, overlay: str) -> pd.DataFrame:
        w_dec = pd.DataFrame(np.nan, index=self.ex.index, columns=[asset])
        hits = 0
        n = 0
        for t in self.me:
            w = 0.0
            if self.eligible(t, asset):
                sL = self.sL.loc[t, asset]
                if overlay == "STATIC":
                    w = TARGET / sL
                elif overlay in ("CV", "FB"):
                    w = TARGET / self.sE.loc[t, asset]
                elif overlay in ("CVB", "FBB"):
                    w = TARGET / self.sB.loc[t, asset]
                elif overlay == "MM":
                    rv = self.rv.loc[t, asset]
                    w = TARGET * sL / rv if rv > 0 else 0.0
                    cap = MM_CAP * TARGET / sL
                    if w > cap:
                        w = cap
                        hits += 1
                else:
                    raise ValueError(overlay)
                if overlay in ("FB", "FBB"):
                    w *= self.trend_on.loc[t, asset]
                if w > GROSS_CAP:
                    w = GROSS_CAP
                    hits += 1 if overlay != "MM" else 0
                n += 1
            w_dec.loc[t, asset] = w
        self.cap_hits[(asset, overlay)] = (hits, n)
        return w_dec.ffill().fillna(0.0)

    # ------------------------------------------------------------------ stock/bond risk parity
    def _cov_lr(self, t, cols):
        x = self.ex.loc[:t, cols].dropna().tail(LR_WIN)
        if len(x) < LR_MIN:
            return None
        v = x.to_numpy()
        return v.T @ v / len(v) * 252

    def _cov_cv(self, t, cols, sig):
        x = self.ex.loc[:t, cols].tail(COR_WIN)
        r = x.corr(min_periods=60).to_numpy()
        if not np.all(np.isfinite(r)):
            return None
        d = np.diag(sig)
        return d @ r @ d

    def rp(self, cols: list[str], overlay: str) -> pd.DataFrame:
        w_dec = pd.DataFrame(np.nan, index=self.ex.index, columns=cols)
        hits = 0
        n = 0
        for t in self.me:
            w = np.zeros(len(cols))
            ok = all(self.eligible(t, c) for c in cols)
            if ok:
                n += 1
                if overlay in ("STATIC", "MM"):
                    sL = self.sL.loc[t, cols].to_numpy()
                    S = self._cov_lr(t, cols)
                    b = 1.0 / sL
                    var = float(b @ S @ b) if S is not None else float("nan")
                    if np.isfinite(var) and var > 0:
                        u = b * TARGET / math.sqrt(var)            # STATIC: 10 % long-run vol
                        w = u
                        if overlay == "MM":
                            per = t.to_period("M")
                            xm = self.ex.loc[:t, cols]
                            xm = xm[xm.index.to_period("M") == per].fillna(0.0).to_numpy()
                            rv_u = float(np.mean((xm @ u) ** 2) * 252) if len(xm) else float("nan")
                            k = TARGET ** 2 / rv_u if rv_u > 0 else 0.0
                            if k > MM_CAP:
                                k = MM_CAP
                                hits += 1
                            w = u * k
                elif overlay in ("CV", "CVB", "FB", "FBB"):
                    sig = (self.sE if overlay in ("CV", "FB") else self.sB).loc[t, cols].to_numpy()
                    S = self._cov_cv(t, cols, sig)
                    b = 1.0 / sig
                    var = float(b @ S @ b) if S is not None else float("nan")
                    if np.isfinite(var) and var > 0:
                        w = b * TARGET / math.sqrt(var)
                        if overlay in ("FB", "FBB"):
                            w = w * self.trend_on.loc[t, cols].to_numpy()
                else:
                    raise ValueError(overlay)
                g = np.abs(w).sum()
                if g > GROSS_CAP:
                    w = w * GROSS_CAP / g
                    if overlay != "MM":
                        hits += 1
            w_dec.loc[t] = w
        self.cap_hits[("+".join(cols), overlay)] = (hits, n)
        return w_dec.ffill().fillna(0.0)


# ---------------------------------------------------------------------- statistics

def sharpe(x: pd.Series) -> float:
    x = x.dropna()
    s = x.std()
    return float(x.mean() / s * math.sqrt(252)) if s > 0 else float("nan")


def max_dd(r: pd.Series) -> float:
    return E.max_drawdown(r.fillna(0.0)) if len(r) else float("nan")


def full_years(idx: pd.DatetimeIndex, cal_full: pd.DatetimeIndex) -> list[int]:
    """Calendar years whose every trading day (per the full calendar) lies inside idx."""
    out = []
    s = set(idx)
    for y in sorted(set(idx.year)):
        days = cal_full[cal_full.year == y]
        # the calendar itself must span the whole year (its final, partial year is not a full year)
        spans = len(days) and days.min() <= pd.Timestamp(y, 1, 8) and days.max() >= pd.Timestamp(y, 12, 20)
        if spans and all(d in s for d in days):
            out.append(y)
    return out


def window_stats(ex1: pd.Series, ex2: pd.Series, exg: pd.Series, net1: pd.Series, turn: pd.Series,
                 cal_full: pd.DatetimeIndex) -> dict:
    n = len(ex1)
    yrs = n / 252
    st = {
        "start": str(ex1.index[0].date()), "end": str(ex1.index[-1].date()), "years": round(yrs, 2),
        "sharpe_net1": sharpe(ex1), "sharpe_net2": sharpe(ex2), "sharpe_gross": sharpe(exg),
        "ann_return": float((1 + net1).prod() ** (1 / yrs) - 1) if yrs > 0 else float("nan"),
        "ann_excess": float(ex1.mean() * 252), "ann_vol": float(ex1.std() * math.sqrt(252)),
        "max_dd": max_dd(net1), "max_dd_excess": max_dd(ex1),
        "turnover_per_year": float(turn.sum() / yrs) if yrs > 0 else float("nan"),
        "nw_t": E.newey_west_tstat(ex1),
    }
    yr = (1 + ex1).groupby(ex1.index.year).prod() - 1
    fy = full_years(ex1.index, cal_full)
    yf = yr.loc[fy] if fy else pd.Series(dtype=float)
    st["n_full_years"] = len(fy)
    st["worst_year"] = float(yf.min()) if len(yf) else float("nan")
    st["worst_year_which"] = int(yf.idxmin()) if len(yf) else -1
    st["pct_positive_years"] = float((yf > 0).mean()) if len(yf) else float("nan")
    st["ret_2022"] = float(yr.get(2022, np.nan))
    roll = (ex1.rolling(504).mean() / ex1.rolling(504).std() * math.sqrt(252)).dropna()
    for q in (10, 50, 90):
        st[f"roll2y_p{q}"] = float(np.percentile(roll, q)) if len(roll) else float("nan")
    return st


def block_bootstrap_diff(a: pd.Series, b: pd.Series, block: int = 63, reps: int = 5000, seed: int = 7) -> dict:
    """Paired circular block bootstrap of Sharpe(a) - Sharpe(b) (daily excess returns, aligned)."""
    df = pd.concat([a, b], axis=1, join="inner").dropna()
    x = df.to_numpy()
    n = len(x)
    rng = np.random.default_rng(seed)
    nb = int(math.ceil(n / block))
    d = np.empty(reps)
    base = np.arange(block)
    done = 0
    while done < reps:
        m = min(500, reps - done)
        starts = rng.integers(0, n, size=(m, nb))
        idx = ((starts[:, :, None] + base[None, None, :]) % n).reshape(m, -1)[:, :n]
        xa = x[idx, 0]
        xb = x[idx, 1]
        sa = xa.mean(1) / xa.std(1, ddof=1)
        sb = xb.mean(1) / xb.std(1, ddof=1)
        d[done:done + m] = (sa - sb) * math.sqrt(252)
        done += m
    obs = sharpe(df.iloc[:, 0]) - sharpe(df.iloc[:, 1])
    p = 2 * min((d <= 0).mean(), (d >= 0).mean())
    return {"d_sharpe": obs, "ci_lo": float(np.percentile(d, 2.5)), "ci_hi": float(np.percentile(d, 97.5)),
            "p_two_sided": float(min(p, 1.0)), "n": n}
