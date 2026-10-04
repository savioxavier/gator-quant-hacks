"""Shared helpers for the calendar-effect study (SPEC.md in this folder). Read-only use of the repository code."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dateutil.easter import easter

REPO = Path("<solo-repo>")
sys.path.insert(0, str(REPO))
from src import calendar_utils as CU  # noqa: E402
from src import engine as E  # noqa: E402

HERE = Path(__file__).resolve().parent
SERIES_DIR = HERE.parent / "series"
IS_END = pd.Timestamp("2024-10-02")
LATER_START = pd.Timestamp("2024-10-03")
LATER_END = pd.Timestamp("2026-10-02")
TD = 252

COST_REAL = {"ES16": 0.75, "F_ES": 0.75, "ZN16": 1.0, "F_ZN": 1.0}
TARGET_VOL = 0.10
CAP = 5.0
EWMA_COM = 60
F_WINDOW = 252


# --------------------------------------------------------------------------- calendars

def nyse_calendar(period: str = "FWD") -> pd.DatetimeIndex:
    return E.trading_calendar(period)


def standard_holiday_dates(years) -> set:
    """Nominal and weekend-adjusted dates of standard US exchange holidays (superset; only dates that are
    actually closed weekdays are used)."""
    out = set()

    def add_fixed(d):
        d = pd.Timestamp(d)
        out.add(d)
        if d.dayofweek == 5:
            out.add(d - pd.Timedelta(days=1))
        if d.dayofweek == 6:
            out.add(d + pd.Timedelta(days=1))

    def nth_weekday(y, m, wd, n):
        d = pd.Timestamp(year=y, month=m, day=1)
        d += pd.Timedelta(days=(wd - d.dayofweek) % 7)
        return d + pd.Timedelta(weeks=n - 1)

    def last_weekday(y, m, wd):
        d = pd.Timestamp(year=y, month=m, day=1) + pd.offsets.MonthEnd(0)
        return d - pd.Timedelta(days=(d.dayofweek - wd) % 7)

    for y in years:
        add_fixed(f"{y}-01-01")
        if y >= 1998:
            out.add(nth_weekday(y, 1, 0, 3))                      # MLK
        add_fixed(f"{y}-02-12")                                    # Lincoln (harmless if open)
        if y <= 1970:
            add_fixed(f"{y}-02-22")
        else:
            out.add(nth_weekday(y, 2, 0, 3))                      # Presidents Day
        out.add(pd.Timestamp(easter(y)) - pd.Timedelta(days=2))   # Good Friday
        if y <= 1970:
            add_fixed(f"{y}-05-30")
        else:
            out.add(last_weekday(y, 5, 0))                        # Memorial Day
        if y >= 2022:
            add_fixed(f"{y}-06-19")                               # Juneteenth
        add_fixed(f"{y}-07-04")
        out.add(nth_weekday(y, 9, 0, 1))                          # Labor Day
        add_fixed(f"{y}-10-12")                                    # Columbus (harmless if open)
        out.add(nth_weekday(y, 11, 0, 1) + pd.Timedelta(days=1))  # Election Day (closed <=1968, 72/76/80)
        add_fixed(f"{y}-11-11")                                    # Veterans (harmless if open)
        out.add(nth_weekday(y, 11, 3, 4))                         # Thanksgiving
        add_fixed(f"{y}-12-25")
    return out


def classify_closures(cal: pd.DatetimeIndex):
    """Weekdays without a session inside the calendar span, split into scheduled holidays and the rest."""
    cal = pd.DatetimeIndex(cal)
    wk = pd.bdate_range(cal[0], cal[-1])
    missing = wk.difference(cal)
    std = standard_holiday_dates(range(cal[0].year, cal[-1].year + 1))
    sched = pd.DatetimeIndex([d for d in missing if d in std])
    unsched = pd.DatetimeIndex([d for d in missing if d not in std])
    return sched, unsched


def pre_holiday_mask(cal: pd.DatetimeIndex, sched: pd.DatetimeIndex) -> pd.Series:
    """True on the last session before each scheduled holiday."""
    cal = pd.DatetimeIndex(cal)
    pos = cal.searchsorted(sched, side="left") - 1
    m = pd.Series(False, index=cal)
    pos = pos[(pos >= 0)]
    m.iloc[np.unique(pos)] = True
    return m


def fomc_cycle_day(cal: pd.DatetimeIndex, day0: pd.DatetimeIndex) -> pd.Series:
    """Sessions since the most recent scheduled announcement day (0 on it); -1 on the session before one."""
    cal = pd.DatetimeIndex(cal)
    d0 = pd.DatetimeIndex(day0)
    d0 = d0[(d0 >= cal[0]) & (d0 <= cal[-1])]
    missing = d0.difference(cal)
    if len(missing):
        raise ValueError(f"FOMC day 0 not a session: {list(missing)}")
    idx0 = cal.get_indexer(d0)
    i = np.arange(len(cal))
    last = np.full(len(cal), -1)
    last[idx0] = idx0
    last = pd.Series(last).replace(-1, np.nan).ffill().to_numpy()
    k = i - last
    k[np.isnan(last)] = np.nan
    pre = np.zeros(len(cal), dtype=bool)
    pre[idx0[idx0 >= 1] - 1] = True
    k = np.where(pre, -1, k)
    return pd.Series(k, index=cal)


def fomc_even_mask(cal: pd.DatetimeIndex, day0: pd.DatetimeIndex) -> pd.Series:
    k = fomc_cycle_day(cal, day0)
    even = k.between(-1, 3) | k.between(9, 13) | k.between(19, 23) | k.between(29, 33)
    return even.fillna(False).astype(bool)


def load_fomc_day0() -> pd.DatetimeIndex:
    df = pd.read_csv(HERE / "fomc_scheduled.csv", parse_dates=["day0"])
    return pd.DatetimeIndex(df["day0"])


# --------------------------------------------------------------------------- rules -> engine

def runs_start(ind: np.ndarray) -> np.ndarray:
    """Index of the first day of the run each True day belongs to (-1 where False)."""
    out = np.full(len(ind), -1)
    start = -1
    for j, v in enumerate(ind):
        if v:
            if j == 0 or not ind[j - 1]:
                start = j
            out[j] = start
    return out


def instrument_frame(inst: str, period: str = "FWD"):
    ohlc = E.load_ohlc([inst], period)
    rf = E.load_rf(period)
    close = ohlc["close"][inst]
    rfi = rf.reindex(close.index).ffill().fillna(0.0)
    ex = close.pct_change(fill_method=None) - rfi
    sigma = np.sqrt(ex.pow(2).ewm(com=EWMA_COM, min_periods=60).mean() * TD)
    return ohlc, rf, ex, sigma


def build_hold(ind_planned: pd.Series, sigma_real: pd.Series, cal_real: pd.DatetimeIndex, scaled: bool = True,
               mult_planned: pd.Series | None = None, cap: float = CAP) -> tuple[pd.DataFrame, pd.Series]:
    """Holdings per real return day for a calendar rule given on the planned calendar.

    Within each run of window days, L = min(cap, 0.10 / (sigma_hat * sqrt(f_hat))) is fixed from the decision date
    two planned sessions before the run's first return day (sigma from the last real session on or before it).
    mult_planned (e.g. issuance q) multiplies L per day (NaN -> no position).
    """
    planned = ind_planned.index
    ind = ind_planned.to_numpy().astype(bool)
    f_hat = ind_planned.astype(float).rolling(F_WINDOW, min_periods=126).mean().to_numpy()
    sig_p = sigma_real.reindex(planned).ffill().to_numpy()    # closure days carry the last real value
    rs = runs_start(ind)
    L = np.zeros(len(planned))
    for j in np.where(ind)[0]:
        d = rs[j] - 2
        if d < 0:
            continue
        s, f = sig_p[d], f_hat[d]
        if not (np.isfinite(s) and s > 0 and np.isfinite(f) and f > 0):
            continue
        L[j] = min(cap, TARGET_VOL / (s * math.sqrt(f))) if scaled else 1.0
        if mult_planned is not None:
            mval = mult_planned.iloc[j]
            L[j] = 0.0 if not np.isfinite(mval) else (min(cap, L[j] * mval) if scaled else mval)
    hold_p = pd.DataFrame({"w": L}, index=planned)
    hold_r = CU.planned_to_realized(hold_p, cal_real)
    return hold_r, pd.Series(f_hat, index=planned)


def simulate_hold(hold_r: pd.DataFrame, inst: str, ohlc: dict, rf: pd.Series, cost_bp: float):
    h = hold_r.rename(columns={"w": inst})
    w_dec = CU.hold_to_decision(h, "next_close")
    net, gross, to, held, costs = E.simulate(w_dec, ohlc, rf, exec="next_close", cost_bps={inst: cost_bp})
    rfi = rf.reindex(net.index).ffill().fillna(0.0)
    return net - rfi, held[inst], to


def run_rule(ind_planned: pd.Series, inst: str, period: str = "FWD", mult_planned=None, cost_real=None) -> dict:
    """Scaled (10 % ex-ante) and unscaled series for one rule at realistic, 2x and zero cost."""
    ohlc, rf, ex, sigma = instrument_frame(inst, period)
    cal_real = ex.index
    c = COST_REAL[inst] if cost_real is None else cost_real
    out = {"inst": inst, "ex_inst": ex, "sigma": sigma}
    for scaled in (True, False):
        hold_r, f_hat = build_hold(ind_planned, sigma, cal_real, scaled=scaled, mult_planned=mult_planned)
        key = "sc" if scaled else "u1"
        series = {}
        for lab, cb in (("net_1x", c), ("net_2x", 2 * c), ("gross", 0.0)):
            x, held, to = simulate_hold(hold_r, inst, ohlc, rf, cb)
            series[lab] = x
            if lab == "net_1x":
                out[f"{key}_held"], out[f"{key}_turnover"] = held, to
        out[key] = pd.DataFrame(series)
        out["f_hat"] = f_hat
    return out


# --------------------------------------------------------------------------- statistics

def sharpe(x: pd.Series) -> float:
    x = x.dropna()
    return float(x.mean() / x.std() * math.sqrt(TD)) if len(x) > 2 and x.std() > 0 else float("nan")


def max_dd(x: pd.Series) -> float:
    eq = (1 + x.fillna(0.0)).cumprod()
    return float((eq / eq.cummax() - 1).min())


def yearly(x: pd.Series, min_days: int = 126) -> pd.Series:
    g = x.groupby(x.index.year)
    yr = (1 + x).groupby(x.index.year).prod() - 1
    return yr[g.size() >= min_days]


def rolling_sharpe_pct(x: pd.Series, win: int = 504) -> tuple[float, float, float]:
    m = x.rolling(win).mean()
    s = x.rolling(win).std()
    rs = (m / s * math.sqrt(TD)).dropna()
    if len(rs) == 0:
        return (float("nan"),) * 3
    return tuple(float(v) for v in rs.quantile([0.1, 0.5, 0.9]))


def hac_reg(y: pd.Series, xcols: pd.DataFrame, lags: int = 5) -> dict:
    import statsmodels.api as sm

    df = pd.concat([y.rename("y"), xcols], axis=1, join="inner").dropna()
    fit = sm.OLS(df["y"], sm.add_constant(df.drop(columns="y"))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return {"alpha_ann": float(fit.params["const"] * TD), "alpha_t": float(fit.tvalues["const"]),
            **{f"beta_{k}": float(v) for k, v in fit.params.drop("const").items()},
            **{f"t_{k}": float(v) for k, v in fit.tvalues.drop("const").items()}, "n": int(fit.nobs)}


def dummy_test(r: pd.Series, mask: pd.Series, lags: int = 5) -> dict:
    """Mean daily return inside vs outside a calendar mask; OLS on a dummy with Newey-West errors."""
    import statsmodels.api as sm
    from scipy import stats as st

    df = pd.DataFrame({"y": r, "d": mask.reindex(r.index).fillna(False).astype(float)}).dropna()
    if df["d"].sum() < 5 or (1 - df["d"]).sum() < 5:
        return {}
    fit = sm.OLS(df["y"], sm.add_constant(df["d"])).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    inw, outw = df.loc[df["d"] == 1, "y"], df.loc[df["d"] == 0, "y"]
    timed = df["y"] * df["d"]
    tot = df["y"].sum()
    return {
        "n_days": int(len(df)), "n_in": int(len(inw)), "share_in": float(df["d"].mean()),
        "mean_in_bp": float(inw.mean() * 1e4), "mean_out_bp": float(outw.mean() * 1e4),
        "mean_all_bp": float(df["y"].mean() * 1e4),
        "diff_bp": float(fit.params["d"] * 1e4), "diff_t_nw": float(fit.tvalues["d"]),
        "diff_t_welch": float(st.ttest_ind(inw, outw, equal_var=False).statistic),
        "in_mean_t_nw": float(E.newey_west_tstat(inw)),
        "timed_sharpe": sharpe(timed), "bh_sharpe": sharpe(df["y"]),
        "share_of_total_excess_in_window": float(inw.sum() / tot) if tot != 0 else float("nan"),
        "hit_rate_in": float((inw > 0).mean()),
    }


def stationary_bootstrap_sharpe_diff(a: pd.Series, b: pd.Series, n_boot: int = 2000, mean_block: int = 21,
                                     seed: int = 7) -> dict:
    """Paired stationary block bootstrap of Sharpe(a) - Sharpe(b); one-sided p = P(diff <= 0)."""
    df = pd.concat([a, b], axis=1, join="inner").dropna()
    x = df.to_numpy()
    n = len(x)
    rng = np.random.default_rng(seed)
    p = 1.0 / mean_block
    diffs = np.empty(n_boot)
    t = np.arange(n)
    for k in range(n_boot):
        jumps = rng.random(n) < p
        jumps[0] = True
        bstart_t = np.maximum.accumulate(np.where(jumps, t, 0))       # time index where the current block began
        starts = rng.integers(n, size=n)
        idx = (starts[bstart_t] + (t - bstart_t)) % n
        s = x[idx]
        m, sd = s.mean(axis=0), s.std(axis=0, ddof=1)
        sr = m / sd * math.sqrt(TD)
        diffs[k] = sr[0] - sr[1]
    obs = sharpe(df.iloc[:, 0]) - sharpe(df.iloc[:, 1])
    return {"obs_diff": float(obs), "p_one_sided": float((diffs <= 0).mean()),
            "ci90": [float(np.quantile(diffs, 0.05)), float(np.quantile(diffs, 0.95))]}


def window_stats(x: pd.Series, held: pd.Series | None, turnover: pd.Series | None, bench: pd.DataFrame,
                 start, end) -> dict:
    """Headline statistics of a daily excess-return series over [start, end]."""
    sl = slice(pd.Timestamp(start), pd.Timestamp(end))
    x = x.loc[sl].dropna()
    if len(x) < 20:
        return {}
    yrs = len(x) / TD
    yr = yearly(x)
    p10, p50, p90 = rolling_sharpe_pct(x)
    out = {
        "start": str(x.index[0].date()), "end": str(x.index[-1].date()), "years": round(yrs, 2),
        "sharpe": sharpe(x), "ann_ret": float(x.mean() * TD), "ann_vol": float(x.std() * math.sqrt(TD)),
        "max_dd": max_dd(x), "nw_t": float(E.newey_west_tstat(x)),
        "worst_year": float(yr.min()) if len(yr) else float("nan"),
        "worst_year_label": int(yr.idxmin()) if len(yr) else None,
        "pct_pos_years": float((yr > 0).mean()) if len(yr) else float("nan"), "n_years": int(len(yr)),
        "roll2y_p10": p10, "roll2y_p50": p50, "roll2y_p90": p90,
        "skew": float(x.skew()), "hit_rate": float((x > 0).mean()),
    }
    if turnover is not None:
        out["turnover_per_year"] = float(turnover.loc[sl].sum() / yrs)
    if held is not None:
        h = held.loc[sl]
        out["share_days_invested"] = float((h.abs() > 0).mean())
        out["mean_lev_when_invested"] = float(h[h.abs() > 0].abs().mean()) if (h.abs() > 0).any() else float("nan")
        out["share_invested_days_at_cap"] = float((h[h.abs() > 0].abs() >= CAP - 1e-9).mean()) if (h.abs() > 0).any() else float("nan")
    b = bench.loc[sl]
    for col in b.columns:
        pair = pd.concat([x, b[col]], axis=1, join="inner").dropna()
        out[f"corr_{col}"] = float(pair.corr().iloc[0, 1]) if len(pair) > 20 else float("nan")
        wk = pair.resample("W-FRI").sum()
        out[f"corr_w_{col}"] = float(wk.corr().iloc[0, 1]) if len(wk) > 20 else float("nan")
    return out
