"""Shared helpers for the fomc_and_hourly_trend study (statistics, costs, loading)."""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), 'data')
PANEL = os.path.join(DATA, 'hourly_panel.parquet')
GQH = os.environ.get('GQH_DATA_DIR', '<home>/.cache/gqh')

IS_END = pd.Timestamp('2024-10-02')
LATER_START = pd.Timestamp('2024-10-03')
LATER_END = pd.Timestamp('2026-10-02')
COST = {'ES': 1.0e-4, 'ZN': 1.5e-4}       # one-way, per unit notional traded


def load_panel():
    p = pd.read_parquet(PANEL)
    p = p.sort_values(['root', 'bar_start_utc']).reset_index(drop=True)
    return p


def nyse_days():
    c = pd.read_parquet(os.path.join(DATA, 'nyse_calendar_offsets.parquet'))
    return pd.DatetimeIndex(pd.to_datetime(c['date'])).sort_values()


def nw_tstat(x, lags=None):
    """Newey-West t-stat of the mean of x (Bartlett kernel)."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 3:
        return np.nan, np.nan
    if lags is None:
        lags = int(np.floor(4 * (n / 100.0) ** (2.0 / 9.0)))
    m = x.mean()
    e = x - m
    s = e @ e / n
    for L in range(1, lags + 1):
        w = 1 - L / (lags + 1)
        s += 2 * w * (e[L:] @ e[:-L]) / n
    se = np.sqrt(s / n)
    return m / se if se > 0 else np.nan, se


def nw_regression(y, X, lags):
    """OLS with Newey-West covariance. Returns beta, se, t."""
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    n, k = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ y
    u = y - X @ b
    Xu = X * u[:, None]
    S = Xu.T @ Xu / n
    for L in range(1, lags + 1):
        w = 1 - L / (lags + 1)
        G = Xu[L:].T @ Xu[:-L] / n
        S += w * (G + G.T)
    V = n * XtX_inv @ S @ XtX_inv
    se = np.sqrt(np.diag(V))
    return b, se, b / se


def sharpe_stats(daily, periods_per_year=252):
    """Annualised Sharpe of a daily return series with its approximate standard error."""
    d = pd.Series(daily).dropna()
    if len(d) < 20 or d.std() == 0:
        return dict(n_days=len(d), years=len(d) / periods_per_year, mean_ann=np.nan, vol_ann=np.nan,
                    sharpe=np.nan, sharpe_se=np.nan, t_nw=np.nan)
    yrs = len(d) / periods_per_year
    sr = d.mean() / d.std() * np.sqrt(periods_per_year)
    t, _ = nw_tstat(d.values, lags=10)
    return dict(n_days=len(d), years=yrs, mean_ann=d.mean() * periods_per_year,
                vol_ann=d.std() * np.sqrt(periods_per_year), sharpe=sr,
                sharpe_se=np.sqrt((1 + sr ** 2 / 2) / yrs), t_nw=t)


def block_bootstrap_idx(n, block, rng):
    """Indices for one moving-block bootstrap resample of length n."""
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=nb)
    idx = (starts[:, None] + np.arange(block)[None, :]).ravel()[:n]
    return idx


def paired_block_bootstrap_sharpe_diff(a, b, block=20, reps=5000, seed=7):
    """Paired moving-block bootstrap of Sharpe(a) - Sharpe(b) on aligned daily series."""
    df = pd.concat([pd.Series(a), pd.Series(b)], axis=1).dropna()
    x = df.values
    n = len(x)
    rng = np.random.default_rng(seed)

    def sr(v):
        s = v.std(axis=0, ddof=1)
        return v.mean(axis=0) / s * np.sqrt(252)

    base = sr(x)
    diffs = np.empty(reps)
    for r in range(reps):
        i = block_bootstrap_idx(n, block, rng)
        s = sr(x[i])
        diffs[r] = s[0] - s[1]
    d0 = base[0] - base[1]
    p = 2 * min((diffs <= 0).mean(), (diffs >= 0).mean())
    return dict(sr_a=base[0], sr_b=base[1], diff=d0, ci_lo=np.percentile(diffs, 2.5),
                ci_hi=np.percentile(diffs, 97.5), p_two_sided=p, n_days=n)
