"""Shared builders for the Variant A analysis (PREDECLARED.md).

Reuses replicate/fedsignal.py (signal, sizing) and replicate/common.py (paths, engine access) unchanged.
Adds: the extended speech scores, the extended FOMC calendar, the DGS2 rate-momentum control, the
tone-orthogonalised signal, the futures version, engine runs in both Sharpe definitions and statistics.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import lfilter

HERE = Path(__file__).resolve().parent
REP = HERE.parent / "replicate"
EXT = HERE.parent / "extend"
EDGES = HERE.parents[1] / "edges"
sys.path.insert(0, str(REP))
import common as K      # noqa: E402
import fedsignal as F   # noqa: E402

E = K.engine()
SPEC = F.Spec()
END = "2026-10-02"
IS_END = K.IS_END
CLOCK = SPEC.z_clock_start
LAM = 2.0 ** (-1.0 / SPEC.half_life)
WIN = {"IS": ("2011-12-30", IS_END), "HOLDOUT": ("2021-01-01", IS_END),
       "OOS": ("2024-10-03", END), "FULL": ("2011-12-30", END)}
COST_ETF = {"TLT": 1.5, "UUP": 5.0}
COST_FUT = {"F_ZN": 1.0, "F_ZB": 1.5, "F_6E": 1.0}


# ----------------------------------------------------------------------------------------- inputs
def scores_ext() -> pd.DataFrame:
    return F.load_kept_scores(EXT / "speech_scores_2011_2026.csv", end=END)


def fomc_ext() -> pd.Series:
    theirs = K.their_fomc()
    sched = pd.read_csv(EDGES / "calendar" / "fomc_scheduled.csv", parse_dates=["day0"])["day0"]
    post = sched[(sched > pd.Timestamp(IS_END)) & (sched <= pd.Timestamp(END))]
    out = pd.concat([theirs[theirs <= pd.Timestamp(IS_END)], post]).drop_duplicates().sort_values()
    return out.reset_index(drop=True).rename("fomc_date")


def _trunc(ohlc: dict, end: str = END) -> dict:
    return {k: v.loc[:pd.Timestamp(end)] for k, v in ohlc.items()}


def etf_market():
    ohlc = _trunc(E.load_ohlc(["TLT", "UUP"], "FWD"))
    o = ohlc["open"]
    cal = o.index[o.index >= pd.Timestamp(K.MARKET_START)]
    o = o.loc[cal]
    r_t, r_u = K.open_to_open(o["TLT"]), K.open_to_open(o["UUP"])
    rf = E.load_rf("FWD").loc[:pd.Timestamp(END)]
    return cal, ohlc, o, r_t, r_u, rf


def dgs2_on(cal: pd.DatetimeIndex) -> pd.Series:
    d = E.load_series("fred_daily.parquet", "FWD")["DGS2"].dropna()
    return d.reindex(d.index.union(cal)).ffill().reindex(cal)


# ----------------------------------------------------------------------------------------- signals
def tone_consensus(cal, scores) -> pd.Series:
    return F.consensus(cal, scores, SPEC.half_life)


def ctl_consensus(cal, dgs2_cal: pd.Series) -> pd.Series:
    """Decayed sum (half-life 20) of the daily DGS2 change two sessions before the entry session."""
    inj = (dgs2_cal.shift(2) - dgs2_cal.shift(3)).fillna(0.0).to_numpy()
    return pd.Series(lfilter([1.0], [1.0, -LAM], inj), index=cal, name="consensus_ctl")


def expanding_orth_z(c_tone: pd.Series, c_ctl: pd.Series, clock: str = CLOCK, min_obs: int = SPEC.z_min_obs) -> pd.Series:
    """Point-in-time residual of C_tone on C_ctl (expanding OLS with intercept), scaled by the fit's residual std."""
    out = pd.Series(np.nan, index=c_tone.index, name="z_orth")
    m = c_tone.index >= pd.Timestamp(clock)
    y = c_tone.to_numpy()[m]
    x = c_ctl.to_numpy()[m]
    n = np.arange(1, len(y) + 1, dtype=float)
    sx, sy = np.cumsum(x), np.cumsum(y)
    sxx, sxy, syy = np.cumsum(x * x), np.cumsum(x * y), np.cumsum(y * y)
    with np.errstate(invalid="ignore", divide="ignore"):
        xb, yb = sx / n, sy / n
        cxx = sxx - n * xb * xb
        cxy = sxy - n * xb * yb
        cyy = syy - n * yb * yb
        b = cxy / cxx
        a = yb - b * xb
        sse = np.maximum(cyy - b * cxy, 0.0)
        s = np.sqrt(sse / (n - 2))
        z = (y - a - b * x) / s
    z[(n < min_obs) | ~np.isfinite(z)] = np.nan
    out.iloc[np.flatnonzero(m)] = z
    return out


def size(z: pd.Series, vol: pd.Series, fd: pd.Series, fn: pd.Series) -> pd.DataFrame:
    return F.size_positions(z, vol, fd, fn, SPEC)


def build_all(scores=None, fomc=None):
    """Session-indexed (entry session t) frame with tone, control and orthogonalised signals and weights."""
    cal, ohlc, o, r_t, r_u, rf = etf_market()
    scores = scores_ext() if scores is None else scores
    fomc = fomc_ext() if fomc is None else fomc
    dg = dgs2_on(cal)
    c_t = tone_consensus(cal, scores)
    c_c = ctl_consensus(cal, dg)
    z_t = F.expanding_z(c_t, CLOCK, SPEC.z_min_obs)
    z_c = F.expanding_z(c_c, CLOCK, SPEC.z_min_obs).rename("z_ctl")
    z_o = expanding_orth_z(c_t, c_c)
    vol = F.mix_vol(r_t, r_u, SPEC)
    fd, fn = F.fomc_flags(cal, fomc)
    w_t = size(z_t, vol, fd, fn)
    w_c = size(z_c, vol, fd, fn)
    w_o = size(z_o, vol, fd, fn)
    sig = pd.DataFrame({"C_tone": c_t, "C_ctl": c_c, "z_tone": z_t, "z_ctl": z_c, "z_orth": z_o, "vol": vol,
                        "fomc_day": fd, "fomc_next": fn, "dgs2": dg,
                        "tone_TLT": w_t["w_TLT"], "tone_UUP": w_t["w_UUP"],
                        "ctl_TLT": w_c["w_TLT"], "ctl_UUP": w_c["w_UUP"],
                        "orth_TLT": w_o["w_TLT"], "orth_UUP": w_o["w_UUP"]})
    return dict(cal=cal, ohlc=ohlc, open=o, r_t=r_t, r_u=r_u, rf=rf, sig=sig, fomc=fomc, scores=scores)


def weights_of(sig: pd.DataFrame, prefix: str) -> pd.DataFrame:
    return sig[[f"{prefix}_TLT", f"{prefix}_UUP"]].rename(columns={f"{prefix}_TLT": "TLT", f"{prefix}_UUP": "UUP"})


# ----------------------------------------------------------------------------------------- engine runs
def run_engine(w_sess: pd.DataFrame, ohlc, rf: pd.Series, cost_bps: dict, exec: str = "next_open", legs: bool = True,
               shift: int | None = None) -> dict:
    """Engine runs in both Sharpe definitions. w_sess is indexed by the day the weight is HELD
    (entry session for next_open, holding day for next_close); w_dec is shifted accordingly."""
    sh = shift if shift is not None else (1 if exec == "next_open" else 2)
    w_dec = w_sess.shift(-sh)
    zero = pd.Series(0.0, index=rf.index)
    out = {}
    for lab, rate in (("rf0", zero), ("ex", rf)):
        for mult in (1.0, 2.0):
            net, gross, turn, held, cost = E.simulate(w_dec, ohlc, rate, exec=exec, cost_mult=mult, cost_bps=cost_bps)
            r = rate.reindex(net.index).ffill().fillna(0.0)
            m = "1x" if mult == 1.0 else "2x"
            out[f"{lab}_net{m}"] = net - r if lab == "ex" else net
            if mult == 1.0:
                out[f"{lab}_gross"] = gross - r if lab == "ex" else gross
                if lab == "ex":
                    out["turnover"], out["held"], out["cost"], out["rf"] = turn, held, cost, r
                    out["total_net1x"] = net
    if legs:
        for leg in w_sess.columns:
            for lab, rate in (("rf0", zero), ("ex", rf)):
                net, *_ = E.simulate(w_dec[[leg]], ohlc, rate, exec=exec, cost_bps=cost_bps)
                r = rate.reindex(net.index).ffill().fillna(0.0)
                out[f"{lab}_leg_{leg}"] = net - r if lab == "ex" else net
    return out


# ----------------------------------------------------------------------------------------- statistics
def sharpe(r: pd.Series) -> float:
    r = r.dropna()
    sd = r.std(ddof=1)
    return float(r.mean() / sd * math.sqrt(252)) if len(r) > 20 and sd > 0 else float("nan")


def max_dd(r: pd.Series) -> float:
    eq = (1 + r.dropna()).cumprod()
    return float((eq / eq.cummax() - 1).min()) if len(eq) else float("nan")


def sl(s: pd.Series, a: str, b: str) -> pd.Series:
    return s.loc[pd.Timestamp(a):pd.Timestamp(b)]


def series_stats(r: pd.Series, turnover: pd.Series | None = None, total: pd.Series | None = None) -> dict:
    r = r.dropna()
    yrs = len(r) / 252
    d = {"start": str(r.index[0].date()), "end": str(r.index[-1].date()), "n_days": int(len(r)),
         "sharpe": sharpe(r), "ann_mean": float(r.mean() * 252),
         "cagr": float((1 + r).prod() ** (1 / yrs) - 1) if yrs > 0 else float("nan"),
         "vol": float(r.std(ddof=1) * math.sqrt(252)), "max_dd": max_dd(r), "nw_t": E.newey_west_tstat(r, 5),
         "skew": float(r.skew()), "hit_rate": float((r > 0).mean())}
    if turnover is not None:
        t = turnover.reindex(r.index)
        d["turnover_per_year"] = float(t.sum() / yrs)
    if total is not None:
        d["max_dd_total"] = max_dd(total.reindex(r.index))
    return d


def yearly_sharpe(r: pd.Series) -> pd.Series:
    r = r.dropna()
    return r.groupby(r.index.year).apply(sharpe)


def yearly_sum(r: pd.Series) -> pd.Series:
    r = r.dropna()
    return (1 + r).groupby(r.index.year).prod() - 1


def block_boot_sharpe(r: pd.Series, block: int = 63, n: int = 10_000, seed: int = 7) -> dict:
    x = r.dropna().to_numpy()
    T = len(x)
    rng = np.random.default_rng(seed)
    nb = int(math.ceil(T / block))
    out = np.empty(n)
    ar = np.arange(block)
    for i in range(n):
        st = rng.integers(0, T, nb)
        idx = ((st[:, None] + ar[None, :]).ravel()[:T]) % T
        y = x[idx]
        out[i] = y.mean() / y.std(ddof=1) * math.sqrt(252)
    return {"block": block, "draws": n, "sharpe": float(x.mean() / x.std(ddof=1) * math.sqrt(252)),
            "p05": float(np.quantile(out, 0.05)), "p50": float(np.quantile(out, 0.5)), "p95": float(np.quantile(out, 0.95)),
            "share_le_0": float((out <= 0).mean())}


def ols_hac(y: pd.Series, X: pd.DataFrame, lags: int) -> dict:
    import statsmodels.api as sm
    df = pd.concat([y.rename("y"), X], axis=1, join="inner").dropna()
    fit = sm.OLS(df["y"], sm.add_constant(df.drop(columns="y"))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return {"n": int(fit.nobs), "r2": float(fit.rsquared),
            **{f"b_{k}": float(v) for k, v in fit.params.items()}, **{f"t_{k}": float(v) for k, v in fit.tvalues.items()},
            "resid_std": float(np.std(fit.resid, ddof=df.shape[1]))}


def partial_corr(a: pd.Series, b: pd.Series, Z: pd.DataFrame) -> float:
    df = pd.concat([a.rename("a"), b.rename("b"), Z], axis=1, join="inner").dropna()
    Xz = np.column_stack([np.ones(len(df)), df[Z.columns].to_numpy()])
    ra = df["a"].to_numpy() - Xz @ np.linalg.lstsq(Xz, df["a"].to_numpy(), rcond=None)[0]
    rb = df["b"].to_numpy() - Xz @ np.linalg.lstsq(Xz, df["b"].to_numpy(), rcond=None)[0]
    return float(np.corrcoef(ra, rb)[0, 1])


# ----------------------------------------------------------------------------------------- futures version
def futures_weights(sig: pd.DataFrame, bond: str, rf: pd.Series):
    """Holding-day weights for the futures version (PREDECLARED section 4) and the futures OHLC."""
    fo = _trunc(E.load_ohlc([bond, "F_6E"], "FWD"))
    cal = sig.index
    close = fo["close"].reindex(cal)
    rfc = rf.reindex(cal).ffill().fillna(0.0)
    r_ex = close.pct_change(fill_method=None).sub(rfc, axis=0)
    mix = -SPEC.w_tlt * r_ex[bond] - SPEC.w_uup * r_ex["F_6E"]
    a = math.sqrt(SPEC.ann)
    v_s = mix.rolling(SPEC.vol_w_short, min_periods=SPEC.vol_w_short).std(ddof=1) * a
    v_l = mix.rolling(SPEC.vol_w_long, min_periods=SPEC.vol_w_long).std(ddof=1) * a
    vol_dec = (0.5 * v_s + 0.5 * v_l).clip(lower=SPEC.vol_floor)       # known at close d
    z_hold = sig["z_tone"].shift(2)                                     # decision at close h-2 uses z of session h-2
    vol_hold = vol_dec.shift(2)
    w = size(z_hold, vol_hold, sig["fomc_day"], sig["fomc_next"])
    w_hold = pd.DataFrame({bond: w["w_TLT"], "F_6E": -w["w_UUP"]}, index=cal)
    return w_hold, fo, vol_dec
