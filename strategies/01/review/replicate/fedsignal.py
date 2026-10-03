"""Fed Board speech-tone consensus: signal, sizing and an open-to-open simulator.

Independent implementation of the published "Variant A" specification
(strategies/01 of savioxavier/gator-quant-hacks). Nothing here imports or calls
the third-party code; their processed CSVs are used only as data.

Conventions
-----------
* ``cal`` is a sorted DatetimeIndex of trading sessions.
* "Session" arrays are indexed by the session t whose OPEN the position is
  entered at; that position is held open(t) -> open(t+1).  A speech dated d
  (date only) first enters the consensus at the first session strictly after d.
* Returns ``r[t] = open[t+1] / open[t] - 1`` on adjusted opens.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.signal import lfilter


@dataclass(frozen=True)
class Spec:
    half_life: float = 20.0
    z_min_obs: int = 252
    z_clock_start: str = "2011-01-03"
    vol_target: float = 0.10
    vol_floor: float = 0.04
    gross_cap: float = 1.5
    w_tlt: float = 0.75
    w_uup: float = 0.25
    vol_w_short: int = 20
    vol_w_long: int = 60
    pos_clip: float = 2.0
    no_trade_band: float = 0.10
    fomc_tlt_mult: float = 0.5
    cost_bps: dict = field(default_factory=lambda: {"TLT": 1.5, "UUP": 5.0})
    ann: int = 252


# --------------------------------------------------------------------------- inputs

def load_kept_scores(path: str, end: str | None = None) -> pd.DataFrame:
    sc = pd.read_csv(path, parse_dates=["speech_date"])
    keep = sc["kept"].astype(bool) & sc["speech_date"].notna() & sc["s"].notna()
    sc = sc.loc[keep, ["slug", "speech_date", "H", "D", "HD", "s"]].copy()
    if end is not None:
        sc = sc[sc["speech_date"] <= pd.Timestamp(end)]
    return sc.sort_values(["speech_date", "slug"]).reset_index(drop=True)


def first_session_after(cal: pd.DatetimeIndex, dates) -> np.ndarray:
    """Position in ``cal`` of the first session strictly after each date (len(cal) if none)."""
    return np.searchsorted(cal.values, pd.DatetimeIndex(dates).values, side="right")


def first_session_on_or_after(cal: pd.DatetimeIndex, dates) -> np.ndarray:
    return np.searchsorted(cal.values, pd.DatetimeIndex(dates).values, side="left")


# --------------------------------------------------------------------------- signal

def consensus(cal: pd.DatetimeIndex, scores: pd.DataFrame, half_life: float) -> pd.Series:
    """C_t = lam * C_{t-1} + sum of s for docs whose first usable session is t (C=0 before)."""
    pos = first_session_after(cal, scores["speech_date"])
    ok = pos < len(cal)
    inj = np.zeros(len(cal))
    np.add.at(inj, pos[ok], scores["s"].to_numpy()[ok])
    lam = 2.0 ** (-1.0 / half_life)
    c = lfilter([1.0], [1.0, -lam], inj)
    return pd.Series(c, index=cal, name="consensus")


def expanding_z(c: pd.Series, clock_start: str, min_obs: int) -> pd.Series:
    """Expanding z of C using only sessions on/after ``clock_start`` (ddof=1, NaN until min_obs)."""
    out = pd.Series(np.nan, index=c.index, name="z")
    m = c.index >= pd.Timestamp(clock_start)
    x = c.to_numpy()[m]
    n = np.arange(1, len(x) + 1, dtype=float)
    s1 = np.cumsum(x)
    s2 = np.cumsum(x * x)
    mean = s1 / n
    with np.errstate(invalid="ignore", divide="ignore"):
        var = (s2 - s1 * s1 / n) / (n - 1)
        var = np.where(var < 0, 0.0, var)
        sd = np.sqrt(var)
        z = (x - mean) / sd
    z[(n < min_obs) | ~np.isfinite(z)] = np.nan
    # an exactly constant history (sd == 0) yields NaN, never +/-inf
    out.iloc[np.flatnonzero(m)] = z
    return out


def mix_vol(r_tlt: pd.Series, r_uup: pd.Series, spec: Spec) -> pd.Series:
    """Blended 20/60-session vol of the unit hawkish mix, using returns ending at open t."""
    mix = -spec.w_tlt * r_tlt + spec.w_uup * r_uup
    past = mix.shift(1)
    a = math.sqrt(spec.ann)
    v_s = past.rolling(spec.vol_w_short, min_periods=spec.vol_w_short).std(ddof=1) * a
    v_l = past.rolling(spec.vol_w_long, min_periods=spec.vol_w_long).std(ddof=1) * a
    return (0.5 * v_s + 0.5 * v_l).clip(lower=spec.vol_floor).rename("vol")


def fomc_flags(cal: pd.DatetimeIndex, fomc_dates) -> tuple[pd.Series, pd.Series]:
    """(announcement session, session after it). A non-session date maps to the next session."""
    p = first_session_on_or_after(cal, fomc_dates)
    p = np.unique(p[p < len(cal)])
    day = np.zeros(len(cal), dtype=bool)
    day[p] = True
    nxt = np.zeros(len(cal), dtype=bool)
    q = p + 1
    nxt[q[q < len(cal)]] = True
    return pd.Series(day, index=cal, name="fomc_day"), pd.Series(nxt, index=cal, name="fomc_next")


def size_positions(z: pd.Series, vol: pd.Series, fomc_day: pd.Series, fomc_next: pd.Series,
                   spec: Spec) -> pd.DataFrame:
    """Vol-targeted TLT/UUP weights with gross cap, FOMC TLT haircut and a relative no-trade band."""
    pos = z.clip(-spec.pos_clip, spec.pos_clip).to_numpy()
    v = vol.reindex(z.index).to_numpy()
    fd = fomc_day.reindex(z.index).fillna(False).to_numpy()
    fn = fomc_next.reindex(z.index).fillna(False).to_numpy()
    n = len(pos)
    wt = np.zeros(n)
    wu = np.zeros(n)
    traded = np.zeros(n, dtype=bool)
    pt = pu = 0.0
    for i in range(n):
        if np.isfinite(pos[i]) and np.isfinite(v[i]):
            k = spec.vol_target / v[i]
            a = -spec.w_tlt * pos[i] * k
            b = spec.w_uup * pos[i] * k
            g = abs(a) + abs(b)
            if g > spec.gross_cap:
                a *= spec.gross_cap / g
                b *= spec.gross_cap / g
            if fd[i]:
                a *= spec.fomc_tlt_mult
            held = abs(pt) + abs(pu)
            forced = fd[i] or fn[i] or (held == 0.0 and abs(a) + abs(b) > 0.0)
            inside_band = held > 0.0 and (abs(a - pt) + abs(b - pu)) < spec.no_trade_band * held
            if forced or not inside_band:
                pt, pu = a, b
                traded[i] = True
        wt[i], wu[i] = pt, pu
    return pd.DataFrame({"w_TLT": wt, "w_UUP": wu, "traded": traded, "pos": pos}, index=z.index)


def build(cal, scores, fomc_dates, r_tlt, r_uup, spec: Spec = Spec(), z_clock_start: str | None = None):
    c = consensus(cal, scores, spec.half_life)
    z = expanding_z(c, z_clock_start or spec.z_clock_start, spec.z_min_obs)
    vol = mix_vol(r_tlt.reindex(cal), r_uup.reindex(cal), spec)
    fd, fn = fomc_flags(cal, fomc_dates)
    w = size_positions(z, vol, fd, fn, spec)
    return pd.concat([c, z, vol, fd, fn, w], axis=1)


# --------------------------------------------------------------------------- open-to-open simulator (rf = 0)

def sim_open_to_open(sig: pd.DataFrame, r_tlt: pd.Series, r_uup: pd.Series, spec: Spec = Spec()) -> pd.DataFrame:
    wt, wu = sig["w_TLT"], sig["w_UUP"]
    dt_ = wt.diff().fillna(wt).abs()
    du_ = wu.diff().fillna(wu).abs()
    ct = dt_ * spec.cost_bps["TLT"] / 1e4
    cu = du_ * spec.cost_bps["UUP"] / 1e4
    rt, ru = r_tlt.reindex(sig.index), r_uup.reindex(sig.index)
    out = pd.DataFrame(index=sig.index)
    out["gross"] = wt * rt + wu * ru
    out["cost"] = ct + cu
    out["net1"] = out["gross"] - out["cost"]
    out["net2"] = out["gross"] - 2 * out["cost"]
    out["tlt1"] = wt * rt - ct
    out["uup1"] = wu * ru - cu
    out["turn"] = dt_ + du_
    out["ret_ok"] = rt.notna() & ru.notna()
    return out


def eval_mask(sig: pd.DataFrame, sim: pd.DataFrame) -> pd.Series:
    first = sig["z"].first_valid_index()
    return sim["ret_ok"] & sig["z"].notna() & (sig.index >= first)


# --------------------------------------------------------------------------- statistics

def max_dd(r: pd.Series) -> float:
    eq = (1 + r.fillna(0)).cumprod()
    return float((eq / eq.cummax() - 1).min())


def sharpe(r: pd.Series, ann: int = 252) -> float:
    r = r.dropna()
    sd = r.std(ddof=1)
    return float(r.mean() / sd * math.sqrt(ann)) if len(r) > 1 and sd > 0 else float("nan")


def stats(r: pd.Series, ann: int = 252) -> dict:
    r = r.dropna()
    return {"n": int(len(r)), "ann_mean": float(r.mean() * ann), "vol": float(r.std(ddof=1) * math.sqrt(ann)),
            "sharpe": sharpe(r, ann), "maxdd": max_dd(r)}


def yearly_sharpe(r: pd.Series, ann: int = 252) -> pd.Series:
    return r.dropna().groupby(r.dropna().index.year).apply(lambda x: sharpe(x, ann))
