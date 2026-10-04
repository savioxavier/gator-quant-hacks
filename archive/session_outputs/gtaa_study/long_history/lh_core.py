"""Core of the long-history timing study: signals, point-in-time execution, statistics, bootstrap.

Conventions
* level L_t: total-return index at the close of month t (last trading day for daily data).
* SMA_n:  s_t = 1 if L_t > mean(L_{t-n+1}, ..., L_t)  (Faber: current month included), else 0.
* MOM12:  s_t = 1 if L_t / L_{t-12} - 1 > prod_{k=t-11..t}(1 + rf_k) - 1  (12-month return above T-bill).
* monthly execution, lag 1 ("idealised", Faber's convention): s_t sets the position for month t+1. This
  assumes the trade at (or minutes before) the month-end close; with index data the gap to the next open
  cannot be measured. lag 2 is used for MONTHLY-AVERAGE data (gold, Shiller): the signal from the average of
  month t-1 sets the exposure earned by avg(t+1)/avg(t), which an investor could replicate by trading at
  the average price of month t (TWAP), i.e. strictly after the signal.
* daily execution ("strict"): the signal from the close of the month's last session T is traded at the
  CLOSE of T+1 (first session of the new month); the new position earns returns from T+2 on.
* out of the market = T-bill. Cost: 10 bp of NAV per unit of turnover (one switch in or out = 10 bp).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

COST = 0.0010
RULES = ["SMA6", "SMA8", "SMA10", "SMA12", "MOM12"]


# ----------------------------------------------------------------------------- signals
def signal(level: pd.Series, rf_m: pd.Series, rule: str) -> pd.Series:
    """Month-end signal (1 invest / 0 cash / NaN warm-up) from month-end levels and monthly cash returns.
    Uses only level[:t] and rf[:t] for the value at t (backward-looking rolling windows)."""
    level = level.astype(float)
    if rule.startswith("SMA"):
        n = int(rule[3:])
        sma = level.rolling(n, min_periods=n).mean()
        s = (level > sma).astype(float)
        s[sma.isna()] = np.nan
        return s
    if rule == "MOM12":
        r12 = level / level.shift(12) - 1
        c12 = (1 + rf_m.reindex(level.index).fillna(0.0)).rolling(12, min_periods=12).apply(np.prod, raw=True) - 1
        s = (r12 > c12).astype(float)
        s[r12.isna() | c12.isna()] = np.nan
        return s
    raise ValueError(rule)


def truncation_test(level: pd.Series, rf_m: pd.Series, rule: str, n_checks: int = 40, seed: int = 1) -> int:
    """Recompute the signal on data truncated at T for random T; return the number of mismatches."""
    full = signal(level, rf_m, rule).dropna()
    rng = np.random.default_rng(seed)
    picks = rng.choice(len(full), size=min(n_checks, len(full)), replace=False)
    bad = 0
    for i in picks:
        T = full.index[i]
        part = signal(level.loc[:T], rf_m.loc[:T], rule)
        if part.iloc[-1] != full.iloc[i]:
            bad += 1
    return bad


# ----------------------------------------------------------------------------- execution
def run_monthly(R: pd.Series, rf: pd.Series, rule: str | None, lag: int = 1, cost: float = COST) -> pd.DataFrame:
    """Single asset, monthly bars. rule None = buy and hold."""
    df = pd.concat([R.rename("R"), rf.rename("rf")], axis=1).dropna()
    if rule is None:
        pos = pd.Series(1.0, index=df.index)
        sig = pos
    else:
        level = (1 + df["R"]).cumprod()
        sig = signal(level, df["rf"], rule)
        pos = sig.shift(lag)
    # point-in-time: the position for month t comes from a signal dated at least `lag` months earlier
    sw = pos.diff().abs()
    gross = pos * df["R"] + (1 - pos) * df["rf"]
    net = gross - cost * sw.fillna(0.0)
    out = pd.DataFrame({"R": df["R"], "rf": df["rf"], "sig": sig, "pos": pos, "switch": sw,
                        "gross": gross, "net": net})
    return out


def month_end_days(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = pd.Series(idx, index=idx)
    per = idx.to_period("M")
    last = s.groupby(per).max()
    # drop the final month if the data stops mid-month
    lastday = idx.max()
    if (lastday + pd.offsets.BDay(1)).to_period("M") == lastday.to_period("M"):
        last = last.iloc[:-1]
    return pd.DatetimeIndex(last.values)


def run_daily_strict(R: pd.Series, rf: pd.Series, rule: str | None, cost: float = COST) -> pd.DataFrame:
    """Single asset, daily bars, month-end signal traded at the close of the next session."""
    df = pd.concat([R.rename("R"), rf.rename("rf")], axis=1).dropna()
    idx = df.index
    if rule is None:
        pos = pd.Series(1.0, index=idx)
        dec_date_used = pd.Series(pd.NaT, index=idx)
    else:
        level = (1 + df["R"]).cumprod()
        T = month_end_days(idx)
        rf_m = (1 + df["rf"]).groupby(idx.to_period("M")).prod() - 1
        t_of = dict(zip(T.to_period("M"), T))
        rf_m = pd.Series(rf_m.values, index=[t_of.get(p, pd.NaT) for p in rf_m.index])
        rf_m = rf_m[rf_m.index.notna()]
        lvl_m = level.loc[T]
        s_m = signal(lvl_m, rf_m.reindex(lvl_m.index), rule)
        dec = s_m.reindex(idx).ffill()                 # decision in force from the close of T
        pos = dec.shift(2)                             # traded at close of T+1, earns from T+2
        dd = pd.Series(pd.NaT, index=idx)
        dd.loc[T] = T
        dec_date_used = dd.ffill().shift(2)
        # ---- explicit point-in-time assertion: position on day t uses a decision dated <= t-2 sessions
        pos_i = pd.Series(np.arange(len(idx)), index=idx)
        ok = dec_date_used.dropna()
        lag_sessions = pos_i.loc[ok.index].to_numpy() - pos_i.loc[pd.DatetimeIndex(ok.values)].to_numpy()
        assert (lag_sessions >= 2).all(), "lookahead in daily execution"
    sw = pos.diff().abs()
    gross = pos * df["R"] + (1 - pos) * df["rf"]
    net = gross - cost * sw.fillna(0.0)
    return pd.DataFrame({"R": df["R"], "rf": df["rf"], "pos": pos, "switch": sw, "gross": gross,
                         "net": net, "dec_date": dec_date_used})


def run_multi_monthly(Rdf: pd.DataFrame, rf: pd.Series, rule: str | None, lag: int = 1,
                      cost: float = COST) -> pd.DataFrame:
    """Equal-weight 1/N sleeves; a timed sleeve sits in T-bills when its own signal is off.
    Monthly rebalancing to target; cost on drift-adjusted turnover (risky sleeves only)."""
    df = pd.concat([Rdf, rf.rename("rf")], axis=1).dropna()
    assets = list(Rdf.columns)
    N = len(assets)
    if rule is None:
        pos = pd.DataFrame(1.0, index=df.index, columns=assets)
    else:
        pos = pd.DataFrame({a: signal((1 + df[a]).cumprod(), df["rf"], rule).shift(lag) for a in assets})
    valid = pos.notna().all(axis=1)
    w = pos / N
    R = df[assets]
    gross = (w * R).sum(axis=1) + (1 - w.sum(axis=1)) * df["rf"]
    # drift: weights at the end of month t-1 after returns, vs targets for month t
    drifted = (w.shift(1) * (1 + R.shift(1))).div(1 + gross.shift(1), axis=0)
    turn = (w - drifted).abs().sum(axis=1)
    turn[~valid | ~valid.shift(1, fill_value=False)] = np.nan
    net = gross - cost * turn.fillna(0.0)
    out = pd.DataFrame({"rf": df["rf"], "gross": gross, "net": net, "turnover": turn,
                        "pos": w.sum(axis=1) * 1.0, "switch": (pos.diff().abs().sum(axis=1))})
    out.loc[~valid, ["gross", "net", "pos"]] = np.nan
    # BH-equivalent market for timing decomposition: the untimed EW portfolio's return
    return out


# ----------------------------------------------------------------------------- statistics
def max_dd(r: pd.Series) -> float:
    eq = (1 + r).cumprod()
    return float((eq / eq.cummax() - 1).min())


def years_of(idx: pd.DatetimeIndex, monthly: bool) -> float:
    if monthly:
        return len(idx) / 12.0
    return (idx[-1] - idx[0]).days / 365.25 + 1.0 / 252


def sharpe(ex: np.ndarray, f: float) -> float:
    s = ex.std(ddof=1)
    return float(ex.mean() / s * math.sqrt(f)) if s > 0 else float("nan")


def stats(res: pd.DataFrame, monthly: bool, bh: pd.DataFrame | None = None) -> dict:
    net = res["net"]
    rf = res["rf"]
    ex = (net - rf).to_numpy()
    gx = (res["gross"] - rf).to_numpy()
    n = len(net)
    yrs = years_of(net.index, monthly)
    f = n / yrs
    sr = sharpe(ex, f)
    eq = (1 + net).prod()
    mret = net if monthly else (1 + net).groupby(net.index.to_period("M")).prod() - 1
    out = {
        "start": str(net.index[0].date()), "end": str(net.index[-1].date()), "years": round(yrs, 2),
        "cagr": float(eq ** (1 / yrs) - 1),
        "ann_excess": float(ex.mean() * f),
        "ann_vol": float(net.std(ddof=1) * math.sqrt(f)),
        "sharpe": sr,
        "sharpe_gross": sharpe(gx, f),
        "sharpe_se": math.sqrt((1 + sr ** 2 / 2) / yrs) if not math.isnan(sr) else float("nan"),
        "max_dd": max_dd(net),
        "worst_month": float(mret.min()),
        "pct_invested": float(res["pos"].mean()),
        "switches": float(res["switch"].fillna(0).sum()),
        "switches_per_year": float(res["switch"].fillna(0).sum() / yrs),
        "cost_drag_ann": float((res["gross"] - res["net"]).sum() / yrs),
    }
    if "turnover" in res:
        out["turnover_per_year"] = float(res["turnover"].fillna(0).sum() / yrs)
    if bh is not None:
        bex = (bh["net"] - bh["rf"]).to_numpy()
        out["bh_sharpe"] = sharpe(bex, f)
        out["d_sharpe"] = sr - out["bh_sharpe"]
        out["bh_cagr"] = float((1 + bh["net"]).prod() ** (1 / yrs) - 1)
        out["d_cagr"] = out["cagr"] - out["bh_cagr"]
        out["bh_ann_excess"] = float(bex.mean() * f)
        out["bh_ann_vol"] = float(bh["net"].std(ddof=1) * math.sqrt(f))
        out["bh_max_dd"] = max_dd(bh["net"])
        out["d_max_dd"] = out["max_dd"] - out["bh_max_dd"]
        bm = bh["net"] if monthly else (1 + bh["net"]).groupby(bh.index.to_period("M")).prod() - 1
        out["bh_worst_month"] = float(bm.min())
        # decomposition of the excess-return difference (gross of costs): timed - BH = -(BH excess while out)
        pos = res["pos"].to_numpy()
        out_mask = pos < 0.5 if "turnover" not in res else None
        if out_mask is not None and out_mask.any() and (~out_mask).any():
            out["bh_ex_ann_when_out"] = float(bex[out_mask].mean() * f)
            out["bh_ex_ann_when_in"] = float(bex[~out_mask].mean() * f)
            out["bh_vol_when_out"] = float(bex[out_mask].std(ddof=1) * math.sqrt(f)) if out_mask.sum() > 2 else float("nan")
            out["bh_vol_when_in"] = float(bex[~out_mask].std(ddof=1) * math.sqrt(f)) if (~out_mask).sum() > 2 else float("nan")
        out["timing_contrib_ann_gross"] = float(gx.mean() * f - bex.mean() * f)
        out["exposure_matched_alpha"] = float(ex.mean() * f - res["pos"].mean() * bex.mean() * f)
        # OLS alpha/beta of timed excess on BH excess, Newey-West t for alpha
        try:
            import statsmodels.api as sm
            X = sm.add_constant(bex)
            lags = 3 if monthly else 21
            m = sm.OLS(ex, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
            out["reg_alpha_ann"] = float(m.params[0] * f)
            out["reg_alpha_t"] = float(m.tvalues[0])
            out["reg_beta"] = float(m.params[1])
        except Exception:
            pass
        mu_t, mu_b = ex.mean(), bex.mean()
        out["ret_ratio"] = float(mu_t / mu_b) if mu_b != 0 else float("nan")
        out["vol_ratio"] = float(ex.std(ddof=1) / bex.std(ddof=1))
    return out


def block_boot(a: np.ndarray, b: np.ndarray, f: float, L: int, B: int = 1000, seed: int = 7,
               chunk: int = 100) -> dict:
    """Paired circular block bootstrap of (SR_a - SR_b) and (mean_a - mean_b), annualised."""
    n = len(a)
    if n < 3 * L:
        return {}
    rng = np.random.default_rng(seed)
    nb = int(math.ceil(n / L))
    dsr, dmu = [], []
    ar = np.arange(L)
    for start in range(0, B, chunk):
        bc = min(chunk, B - start)
        st = rng.integers(0, n, size=(bc, nb))
        idx = ((st[:, :, None] + ar[None, None, :]).reshape(bc, -1)[:, :n]) % n
        A = a[idx]
        Bm = b[idx]
        sa = A.std(axis=1, ddof=1)
        sb = Bm.std(axis=1, ddof=1)
        dsr.append(A.mean(axis=1) / sa * math.sqrt(f) - Bm.mean(axis=1) / sb * math.sqrt(f))
        dmu.append((A.mean(axis=1) - Bm.mean(axis=1)) * f)
    dsr = np.concatenate(dsr)
    dmu = np.concatenate(dmu)
    return {"d_sharpe_lo": float(np.percentile(dsr, 2.5)), "d_sharpe_hi": float(np.percentile(dsr, 97.5)),
            "d_sharpe_bse": float(dsr.std(ddof=1)), "p_d_sharpe_le0": float((dsr <= 0).mean()),
            "d_excess_lo": float(np.percentile(dmu, 2.5)), "d_excess_hi": float(np.percentile(dmu, 97.5))}
