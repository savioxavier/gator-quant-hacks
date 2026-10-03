"""Fed communication v2: signal construction, sizing and evaluation helpers.

Implements research/fedspeak_v2/HYPOTHESIS_v2.md (sha256 6083d3ef...d910, with Amendment 1).
Variant A construction re-implemented from its published specification (strategies/01 HYPOTHESIS.md,
config.py, backtest.py); nothing from that folder is imported or executed.

Index conventions
-----------------
* ``cal``: NYSE sessions (engine calendar).
* "Entry-session" series (suffix ``_s``) are indexed by the session t at whose OPEN an E1 position is entered.
  A document dated d (date only, or released at any time on d) first enters the consensus at the first session
  strictly after d. So C_s[t] uses documents dated < t.
* "Decision" series (suffix ``_dec``) are indexed by decision date D = the session before t. They are what
  ``engine.simulate`` takes: E1 (exec next_open) fills w_dec[D] at the open of D+1 = t; E2 (exec next_close)
  fills w_dec[D] at the close of D+1. For both expressions a document dated d is therefore first traded in the
  session after d (open for ETFs, close for futures), never on d.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.signal import lfilter

# ----------------------------------------------------------------------------- frozen parameters (Variant A)
HALF_LIFE = 20.0
LAM = 2.0 ** (-1.0 / HALF_LIFE)
Z_MIN_OBS = 252
VOL_TARGET = 0.10
VOL_FLOOR = 0.04
GROSS_CAP = 1.5
POS_CLIP = 2.0
NO_TRADE_BAND = 0.10
FOMC_RATE_MULT = 0.5          # Variant A halves the rates leg on the FOMC announcement session
W_RATE = 0.75
W_FX = 0.25
VOL_W_SHORT = 20
VOL_W_LONG = 60
ANN = 252


@dataclass(frozen=True)
class Expr:
    name: str
    rate: str
    fx: str
    fx_sign: float            # +1: long UUP when hawkish; -1: short 6E when hawkish
    exec: str
    cost_bps: dict


EXPRS = {
    "E1": Expr("E1", "TLT", "UUP", +1.0, "next_open", {"TLT": 1.5, "UUP": 5.0}),
    "E2": Expr("E2", "F_ZN", "F_6E", -1.0, "next_close", {"F_ZN": 1.0, "F_6E": 1.0}),
}


# ----------------------------------------------------------------------------- consensus and z
def first_session_after(cal: pd.DatetimeIndex, dates) -> np.ndarray:
    return np.searchsorted(cal.values, pd.DatetimeIndex(dates).values, side="right")


def first_session_on_or_after(cal: pd.DatetimeIndex, dates) -> np.ndarray:
    return np.searchsorted(cal.values, pd.DatetimeIndex(dates).values, side="left")


def consensus_s(cal: pd.DatetimeIndex, dates, scores, half_life: float = HALF_LIFE) -> pd.Series:
    """C_s[t] = lam*C_s[t-1] + sum of scores of documents first usable at t; 0 before the first document.
    Equal weight per document (several documents on one date add up)."""
    pos = first_session_after(cal, dates)
    sc = np.asarray(scores, dtype=float)
    ok = (pos < len(cal)) & np.isfinite(sc)
    inj = np.zeros(len(cal))
    np.add.at(inj, pos[ok], sc[ok])
    lam = 2.0 ** (-1.0 / half_life)
    return pd.Series(lfilter([1.0], [1.0, -lam], inj), index=cal, name="C")


def expanding_z(c: pd.Series, clock_start: str, min_obs: int = Z_MIN_OBS) -> pd.Series:
    """Expanding z (ddof=1) over sessions on/after clock_start; NaN until min_obs and where sd == 0."""
    out = pd.Series(np.nan, index=c.index, name="z")
    m = c.index >= pd.Timestamp(clock_start)
    x = c.to_numpy()[m]
    n = np.arange(1, len(x) + 1, dtype=float)
    s1, s2 = np.cumsum(x), np.cumsum(x * x)
    with np.errstate(invalid="ignore", divide="ignore"):
        var = np.maximum((s2 - s1 * s1 / n) / (n - 1), 0.0)
        z = (x - s1 / n) / np.sqrt(var)
    z[(n < min_obs) | ~np.isfinite(z)] = np.nan
    out.iloc[np.flatnonzero(m)] = z
    return out


def rate_momentum_s(cal: pd.DatetimeIndex, dgs2: pd.Series, half_life: float = HALF_LIFE, lag: int = 2) -> pd.Series:
    """20-session-half-life change in DGS2, lagged two sessions relative to the entry session t:
    M_s[t] = sum_k lam^k * dDGS2[t-2-k]. (Identical, up to the factor lam, to DGS2 minus its EWMA.)
    DGS2 is forward-filled over sessions without a print."""
    y = dgs2.reindex(cal.union(dgs2.index)).sort_index().ffill().reindex(cal)
    dy = y.shift(lag).diff().fillna(0.0)
    lam = 2.0 ** (-1.0 / half_life)
    return pd.Series(lfilter([1.0], [1.0, -lam], dy.to_numpy()), index=cal, name="M")


def expanding_residual_z(c: pd.Series, m: pd.Series, clock_start: str, min_obs: int = Z_MIN_OBS) -> pd.DataFrame:
    """T3: point-in-time residual of C on [1, M] from an expanding OLS over sessions [clock_start, t].
    e_t = C_t - a_t - b_t*M_t with (a_t, b_t) fitted on data through t. Standardised as in Variant A's
    expanding z: z_t = (e_t - mean of the fit's residuals) / sd(ddof=1) of the fit's residuals; the residual
    mean is 0 because of the intercept, so z_t = e_t / sqrt(SSR_t/(n_t-1)). NaN until min_obs."""
    idx = c.index
    msk = idx >= pd.Timestamp(clock_start)
    y = c.to_numpy()[msk]
    x = m.reindex(idx).to_numpy()[msk]
    n = np.arange(1, len(y) + 1, dtype=float)
    sx, sy = np.cumsum(x), np.cumsum(y)
    sxx, sxy, syy = np.cumsum(x * x), np.cumsum(x * y), np.cumsum(y * y)
    with np.errstate(invalid="ignore", divide="ignore"):
        cxx = sxx - sx * sx / n
        cxy = sxy - sx * sy / n
        cyy = syy - sy * sy / n
        b = cxy / cxx
        a = sy / n - b * sx / n
        e = y - a - b * x
        ssr = np.maximum(cyy - b * cxy, 0.0)
        z = e / np.sqrt(ssr / (n - 1))
    bad = (n < min_obs) | ~np.isfinite(z)
    z[bad] = np.nan
    out = pd.DataFrame(np.nan, index=idx, columns=["resid", "beta", "alpha", "z"])
    rows = np.flatnonzero(msk)
    out.iloc[rows, 0] = np.where(bad, np.nan, e)
    out.iloc[rows, 1] = np.where(bad, np.nan, b)
    out.iloc[rows, 2] = np.where(bad, np.nan, a)
    out.iloc[rows, 3] = z
    return out


# ----------------------------------------------------------------------------- FOMC flags and vol
def fomc_day_s(cal: pd.DatetimeIndex, fomc_dates) -> pd.Series:
    """True on the session of each FOMC announcement (a non-session date maps to the next session)."""
    p = first_session_on_or_after(cal, fomc_dates)
    p = np.unique(p[p < len(cal)])
    f = np.zeros(len(cal), dtype=bool)
    f[p] = True
    return pd.Series(f, index=cal, name="fomc")


def blended_vol(mix: pd.Series) -> pd.Series:
    a = math.sqrt(ANN)
    vs = mix.rolling(VOL_W_SHORT, min_periods=VOL_W_SHORT).std(ddof=1) * a
    vl = mix.rolling(VOL_W_LONG, min_periods=VOL_W_LONG).std(ddof=1) * a
    return (0.5 * vs + 0.5 * vl).clip(lower=VOL_FLOOR)


# ----------------------------------------------------------------------------- sizing (Variant A rules)
def size(pos_raw: np.ndarray, vol: np.ndarray, fomc_hold: np.ndarray, fomc_after: np.ndarray, fx_sign: float):
    """Vol target 10% on the unit hawkish mix, gross cap 1.5, clip 2, rates leg halved over the FOMC
    announcement, relative no-trade band 10% (forced trade on the FOMC interval, the one after, and from flat).
    Where z or vol is missing, the previous weights carry forward (0 before the first valid z)."""
    pos = np.clip(pos_raw, -POS_CLIP, POS_CLIP)
    n = len(pos)
    wr, wf = np.zeros(n), np.zeros(n)
    traded = np.zeros(n, dtype=bool)
    pr = pf = 0.0
    for i in range(n):
        if np.isfinite(pos[i]) and np.isfinite(vol[i]):
            k = VOL_TARGET / vol[i]
            a = -W_RATE * pos[i] * k
            b = fx_sign * W_FX * pos[i] * k
            g = abs(a) + abs(b)
            if g > GROSS_CAP:
                a *= GROSS_CAP / g
                b *= GROSS_CAP / g
            if fomc_hold[i]:
                a *= FOMC_RATE_MULT
            held = abs(pr) + abs(pf)
            forced = fomc_hold[i] or fomc_after[i] or (held == 0.0 and abs(a) + abs(b) > 0.0)
            inside = held > 0.0 and (abs(a - pr) + abs(b - pf)) < NO_TRADE_BAND * held
            if forced or not inside:
                pr, pf = a, b
                traded[i] = True
        wr[i], wf[i] = pr, pf
    return wr, wf, traded


def weights_E1(z_s: pd.Series, opens: pd.DataFrame, fomc_s: pd.Series, ex: Expr) -> pd.DataFrame:
    """Variant A exactly: entry-session sizing with open-to-open vol (returns ending at open t), then shifted to
    decision dates (w_dec[D] = w_s[D+1])."""
    cal = z_s.index
    o = opens.reindex(cal)
    r = o.shift(-1) / o - 1.0                          # r[t] = open[t+1]/open[t] - 1
    mix = -W_RATE * r[ex.rate] + ex.fx_sign * W_FX * r[ex.fx]
    vol = blended_vol(mix.shift(1))                    # returns ending at open t
    fd = fomc_s.reindex(cal).fillna(False).to_numpy()
    fa = np.r_[False, fd[:-1]]                         # session after an FOMC session
    wr, wf, tr = size(z_s.to_numpy(), vol.to_numpy(), fd, fa, ex.fx_sign)
    w_s = pd.DataFrame({ex.rate: wr, ex.fx: wf}, index=cal)
    w_dec = w_s.shift(-1)
    w_dec.iloc[-1] = w_s.iloc[-1].to_numpy()          # last decision: hold (never filled inside the data)
    aux = pd.DataFrame({"z_entry": z_s, "vol_entry": vol, "fomc_entry": fd, "traded_entry": tr}, index=cal).shift(-1)
    return w_dec, aux


def weights_E2(z_s: pd.Series, closes: pd.DataFrame, fomc_s: pd.Series, ex: Expr) -> pd.DataFrame:
    """E2: decision at close D uses z_s[D+1] (documents dated before session D+1) and close-to-close vol through
    close D; the engine fills at the close of D+1, so the position is held over session D+2. The FOMC haircut
    applies to the position held over the announcement session (FOMC on D+2); trades are forced on that
    decision and the next."""
    cal = z_s.index
    c = closes.reindex(cal)
    r = c.pct_change(fill_method=None)
    mix = -W_RATE * r[ex.rate] + ex.fx_sign * W_FX * r[ex.fx]
    vol = blended_vol(mix)                             # returns ending at close D
    z_dec = z_s.shift(-1)                              # z_s[D+1]
    f = fomc_s.reindex(cal).fillna(False).to_numpy()
    hold = np.r_[f[2:], False, False]                  # FOMC on D+2
    after = np.r_[f[1:], False]                        # FOMC on D+1 -> this decision's interval is the one after
    wr, wf, tr = size(z_dec.to_numpy(), vol.to_numpy(), hold, after, ex.fx_sign)
    w_dec = pd.DataFrame({ex.rate: wr, ex.fx: wf}, index=cal)
    aux = pd.DataFrame({"z_dec": z_dec, "vol_dec": vol, "fomc_hold": hold, "traded": tr}, index=cal)
    return w_dec, aux


# ----------------------------------------------------------------------------- statistics
def sharpe(x: pd.Series) -> float:
    x = x.dropna()
    sd = x.std(ddof=1)
    return float(x.mean() / sd * math.sqrt(ANN)) if len(x) > 20 and sd > 0 else float("nan")


def max_dd(x: pd.Series) -> float:
    eq = (1 + x.fillna(0.0)).cumprod()
    return float((eq / eq.cummax() - 1).min())


def nw_t(x: pd.Series) -> float:
    x = x.dropna().to_numpy()
    n = len(x)
    if n < 10:
        return float("nan")
    L = int(4 * (n / 100) ** (2 / 9))
    e = x - x.mean()
    s = e @ e / n
    for k in range(1, L + 1):
        s += 2 * (1 - k / (L + 1)) * (e[k:] @ e[:-k]) / n
    return float(x.mean() / math.sqrt(s / n)) if s > 0 else float("nan")


def window_stats(ex1: pd.Series, ex2: pd.Series, exg: pd.Series, turn: pd.Series, a, b) -> dict:
    s = slice(pd.Timestamp(a), pd.Timestamp(b))
    x1, x2, xg, tv = ex1.loc[s].dropna(), ex2.loc[s].dropna(), exg.loc[s].dropna(), turn.loc[s]
    if len(x1) < 2:
        return {"n_days": len(x1)}
    yrs = len(x1) / ANN
    return {
        "start": str(x1.index[0].date()), "end": str(x1.index[-1].date()), "n_days": int(len(x1)),
        "sharpe_net1x": sharpe(x1), "sharpe_net2x": sharpe(x2), "sharpe_gross": sharpe(xg),
        "ann_excess_arith": float(x1.mean() * ANN), "ann_excess_geo": float((1 + x1).prod() ** (1 / yrs) - 1),
        "vol": float(x1.std(ddof=1) * math.sqrt(ANN)), "max_dd_excess": max_dd(x1), "nw_t": nw_t(x1),
        "turnover_per_year": float(tv.sum() / yrs),
    }
