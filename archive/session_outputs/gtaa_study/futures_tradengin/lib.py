"""Builders and statistics for the futures GTAA / trade-ngin study.

Conventions follow the repo engine: a decision weight at date d uses data up to the close of d only;
futures are simulated with exec="next_close" (decision at close d, traded at close d+1, earns from d+2)
and the forward-test-2 futures cost map; ETFs with exec="next_open" and the default ETF costs.
Nothing here calls run_backtest / log_trial or writes to the repo.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

REPO = r"<solo-repo>"
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import numpy as np
import pandas as pd

from src import engine as E
from src import forward2 as F

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

IS_WIN = ("2011-09-02", "2024-10-02")      # common in-sample window of every futures variant (S1's first traded day)
OOS_WIN = ("2024-10-03", "2026-10-02")     # already seen: descriptive only
ETF_IS_WIN = ("2005-11-01", "2024-10-02")  # S3's own in-sample window

CLASS_OF = {}
for cls, roots in {
    "equity": ["ES", "NQ", "RTY", "YM"],
    "rates": ["ZT", "ZF", "ZN", "ZB", "UB"],
    "energy": ["CL", "HO", "RB", "NG"],
    "metals": ["GC", "SI", "PL", "HG"],
    "ags": ["ZC", "ZS", "ZW", "ZL", "ZM"],
    "livestock": ["LE", "HE"],
    "fx": ["6E", "6J", "6B", "6A", "6C", "6S"],
}.items():
    for r in roots:
        CLASS_OF[f"F_{r}"] = cls
BROAD = {"equity": "equity", "rates": "rates", "energy": "commodities", "metals": "commodities",
         "ags": "commodities", "livestock": "commodities", "fx": "fx"}
ETF_BROAD = {"SPY": "equity", "EFA": "equity", "IEF": "rates", "VNQ": "equity(REIT)", "DBC": "commodities"}


# --------------------------------------------------------------------------- data

def futures_panel(period: str = "FWD"):
    """(ohlc, rf, ex) for the 30 S1 futures; ex = daily excess return of the fully collateralised index."""
    return F._futures_panel(F.S1_TICKERS, period)


def month_end_sma_signal(close: pd.DataFrame, n: int = 10):
    """(on, valid) at month-ends: on = month-end close > mean of the last n month-end closes (incl. this one),
    exactly the S3 rule. Uses only closes up to each month-end."""
    me = F._month_ends(close.index)
    mc = close.loc[me]
    sma = mc.rolling(n, min_periods=n).mean()
    valid = sma.notna() & mc.notna()
    on = (mc > sma) & valid
    return on.astype(float), valid


# --------------------------------------------------------------------------- futures risk-parity family

def rp_decisions(ohlc: dict, ex: pd.DataFrame, sig_me: pd.DataFrame | None = None, mode: str = "fixed",
                 class_equal: bool = False) -> pd.DataFrame:
    """Monthly decisions on the NYSE calendar, built exactly like forward2.s1_decisions:
    eligibility (>= MIN_HISTORY sessions, positive EWMA vol, traded in the last ACTIVE_WINDOW sessions),
    raw weight RAW_SCALE / sigma_i / N (or equal risk per asset class when class_equal), book scaled to
    TARGET_VOL with the trailing 252-day covariance, gross <= GROSS_CAP.

    sig_me (month-end x ticker, values in [-1, 1]) multiplies the weights:
      mode="fixed":   scale the all-long book first, then multiply by the signal (Faber: an 'off' slot sits in cash,
                      the risk budget of the 'on' slots is unchanged) -> GTAA = 0.5 x long-only + 0.5 x long-short.
      mode="rescale": multiply first, then rescale the filtered book to TARGET_VOL (like S1 does with its signals).
    sig_me=None gives the long-only risk-parity book (identical to forward2 LONG_ONLY_F when class_equal=False).
    """
    tick = list(ex.columns)
    active = F._active(ohlc)[tick]
    vol = np.sqrt(ex.pow(2).ewm(com=F.EWMA_COM, min_periods=60).mean() * 252)
    counts = ex.notna().cumsum()
    w_dec = pd.DataFrame(np.nan, index=ex.index, columns=tick)
    for t in F._month_ends(ex.index):
        hist = ex.loc[:t]
        elig = [c for c in tick if counts.loc[t, c] >= F.MIN_HISTORY and np.isfinite(vol.loc[t, c])
                and vol.loc[t, c] > 0 and active.loc[t, c]]
        w = pd.Series(0.0, index=tick)
        if elig:
            if class_equal:
                cls = pd.Series({c: CLASS_OF[c] for c in elig})
                ncls = cls.nunique()
                share = cls.map(1.0 / (ncls * cls.value_counts()))
                base = share * F.RAW_SCALE / vol.loc[t, elig]
            else:
                base = F.RAW_SCALE / vol.loc[t, elig] / len(elig)
            w[elig] = base.values
            if sig_me is None:
                w = F._scale_to_target(w, hist)
            else:
                s = sig_me.loc[t].reindex(tick).fillna(0.0)
                if mode == "fixed":
                    w = F._scale_to_target(w, hist) * s
                elif mode == "rescale":
                    w = F._scale_to_target(w * s, hist)
                else:
                    raise ValueError(mode)
        w_dec.loc[t] = w.values
    return w_dec.ffill().fillna(0.0)


# --------------------------------------------------------------------------- 5-market futures GTAA (mirror of S3)

FUT5_COM = ["F_CL", "F_GC", "F_HG", "F_ZC"]
FUT5_TICKERS = ["F_ES", "F_ZN"] + FUT5_COM


def fut5_decisions(close: pd.DataFrame, slot_w: float = 0.20, mode: str = "gtaa") -> pd.DataFrame:
    """S3 mirrored on futures. Sleeves: ES, ZN, and a commodity basket (equal-weight, daily-rebalanced CL GC HG ZC
    index, one SMA filter on the basket like DBC). No world-equity (EFA) or REIT (VNQ) future exists among the 30:
    with slot_w=0.20 those two slots are always T-bills; with slot_w=1/3 the three sleeves share the book.
    mode: "gtaa" (long-or-flat), "bh" (always long once the SMA exists), "ls" (+slot / -slot)."""
    c = close[FUT5_TICKERS].ffill(limit=5)
    r = c.pct_change(fill_method=None)
    com_r = r[FUT5_COM].mean(axis=1, skipna=False)
    com_lvl = (1 + com_r.fillna(0.0)).cumprod().where(r[FUT5_COM].notna().all(axis=1).cumsum() > 0)
    lvl = pd.DataFrame({"ES": c["F_ES"], "ZN": c["F_ZN"], "COM": com_lvl})
    on, valid = month_end_sma_signal(lvl)
    if mode == "gtaa":
        s = on
    elif mode == "bh":
        s = valid.astype(float)
    elif mode == "ls":
        s = valid.astype(float) * (2 * on - 1)
    else:
        raise ValueError(mode)
    w_me = pd.DataFrame(0.0, index=s.index, columns=FUT5_TICKERS)
    w_me["F_ES"] = slot_w * s["ES"]
    w_me["F_ZN"] = slot_w * s["ZN"]
    for t in FUT5_COM:
        w_me[t] = slot_w / len(FUT5_COM) * s["COM"]
    w_dec = pd.DataFrame(np.nan, index=close.index, columns=FUT5_TICKERS)
    w_dec.loc[w_me.index] = w_me.values
    return w_dec.ffill().fillna(0.0)


# --------------------------------------------------------------------------- ETF GTAA family

def etf_decisions(close: pd.DataFrame, slot_w: float, mode: str = "gtaa") -> pd.DataFrame:
    """Per-ETF 10-month SMA rule; mode gtaa (S3 rule), bh (BH5 rule) or ls (+slot / -slot, shorts pay borrow)."""
    on, valid = month_end_sma_signal(close)
    if mode == "gtaa":
        s = on
    elif mode == "bh":
        s = valid.astype(float)
    elif mode == "ls":
        s = valid.astype(float) * (2 * on - 1)
    else:
        raise ValueError(mode)
    w_dec = pd.DataFrame(np.nan, index=close.index, columns=close.columns)
    w_dec.loc[s.index] = (s * slot_w).values
    return w_dec.ffill().fillna(0.0)


# --------------------------------------------------------------------------- trade-ngin-style EWMAC (own implementation)

EWMAC_SLOW = [(2, 8), (4, 16), (8, 32), (16, 64), (32, 128), (64, 256)]   # TREND_FOLLOWING config windows
EWMAC_FAST = [(1, 4), (2, 8), (4, 16), (8, 32), (16, 64)]                 # TREND_FOLLOWING_FAST config windows


class Ewmac:
    """Carver-style EWMAC as configured in trade-ngin's base portfolio (6 or 5 crossover speeds, 70/30 blended
    short/long vol, forecasts scaled to mean |f| = 10 and capped at +-20, IDM 2.5, position buffering on the slow
    system only). Written from the published method, not from trade-ngin's source. floor0=True clips the combined
    forecast at 0: the 'long-or-flat' version of the same system."""

    def __init__(self, ohlc: dict, rf: pd.Series, ex: pd.DataFrame, vol_short: int = 32):
        self.tick = list(ex.columns)
        self.ex = ex
        self.active = F._active(ohlc)[self.tick]
        self.px = (1 + ex.fillna(0)).cumprod()
        ret_sd = ex.ewm(span=vol_short, min_periods=vol_short).std()
        self.sd = 0.7 * ret_sd + 0.3 * ret_sd.rolling(252, min_periods=60).mean()
        self.price_sd = self.sd * self.px
        self.ok = self.active & self.sd.notna() & (ex.notna().cumsum() >= F.MIN_HISTORY)

    def forecast(self, speeds) -> pd.DataFrame:
        fc = []
        for f, s in speeds:
            raw = (self.px.ewm(span=f, min_periods=s).mean() - self.px.ewm(span=s, min_periods=s).mean()) / self.price_sd
            scal = 10 / raw.abs().stack().groupby(level=0).mean().expanding(250).mean().shift(1)   # lagged: no lookahead
            fc.append(raw.mul(scal, axis=0).clip(-20, 20))
        comb = sum(fc) / len(fc)
        fdm = 10 / comb.abs().stack().groupby(level=0).mean().expanding(250).mean().shift(1)
        return comb.mul(fdm, axis=0).clip(-20, 20)

    def weights(self, speeds, target: float, buffer: bool, floor0: bool = False) -> pd.DataFrame:
        comb = self.forecast(speeds)
        if floor0:
            comb = comb.clip(lower=0.0)
        n = self.ok.sum(axis=1).replace(0, np.nan)
        avg_pos = (target / (self.sd * np.sqrt(252))).mul(2.5 / n, axis=0)   # position at forecast 10
        tgt = (comb / 10 * avg_pos).where(self.ok, 0.0).fillna(0.0)
        if not buffer:
            return tgt
        T, A = tgt.to_numpy(), avg_pos.fillna(0).to_numpy()
        cur = np.zeros(T.shape[1])
        out = np.zeros_like(T)
        for i in range(len(T)):
            band = 0.1 * np.abs(A[i])
            cur = np.clip(cur, T[i] - band, T[i] + band)
            cur = np.where(T[i] == 0, 0.0, cur)
            out[i] = cur
        return pd.DataFrame(out, index=tgt.index, columns=self.tick)


# --------------------------------------------------------------------------- simulation and statistics

def run(w_dec: pd.DataFrame, ohlc: dict, rf: pd.Series, exec: str, cost: dict | None):
    net, gross, turnover, held, costs = E.simulate(w_dec, ohlc, rf, exec=exec, cost_bps=cost)
    return {"net": net, "gross": gross, "turnover": turnover, "held": held, "w_dec": w_dec}


def sharpe(x: pd.Series) -> float:
    x = x.dropna()
    return float(x.mean() / x.std() * math.sqrt(252)) if x.std() > 0 else float("nan")


def sr_se(sr: float, years: float) -> float:
    return math.sqrt((1 + sr ** 2 / 2) / years)


def window_stats(res: dict, rf: pd.Series, win: tuple[str, str]) -> dict:
    sl = slice(pd.Timestamp(win[0]), pd.Timestamp(win[1]))
    n = res["net"].loc[sl]
    g = res["gross"].loc[sl]
    r = rf.reindex(n.index).ffill().fillna(0.0)
    xn, xg = n - r, g - r
    years = len(n) / 252
    sr = sharpe(xn)
    out = {
        "start": str(n.index[0].date()), "end": str(n.index[-1].date()), "years": round(years, 2),
        "sharpe": sr, "sharpe_se": sr_se(sr, years), "sharpe_gross": sharpe(xg),
        "ann_return": float((1 + n).prod() ** (1 / years) - 1), "ann_excess": float(xn.mean() * 252),
        "ann_vol": float(n.std() * math.sqrt(252)), "max_dd": E.max_drawdown(n),
        "cost_drag": float((g - n).mean() * 252),
    }
    if "turnover" in res and res["turnover"] is not None:
        out["turnover_yr"] = float(res["turnover"].loc[sl].sum() / years)
    if "held" in res and res["held"] is not None:
        h = res["held"].loc[sl]
        out["avg_gross_exp"] = float(h.abs().sum(axis=1).mean())
        out["avg_net_exp"] = float(h.sum(axis=1).mean())
        out["frac_days_invested"] = float((h.abs().sum(axis=1) > 1e-9).mean())
    return out


def block_bootstrap_sharpes(X: pd.DataFrame, L: int = 63, B: int = 2000, seed: int = 7) -> np.ndarray:
    """Paired moving-block bootstrap of daily excess returns (rows = days). Returns a B x k array of annual Sharpes."""
    A = X.to_numpy()
    n, k = A.shape
    nb = int(math.ceil(n / L))
    rng = np.random.default_rng(seed)
    out = np.empty((B, k))
    base = np.arange(L)
    for b in range(B):
        st = rng.integers(0, n - L + 1, size=nb)
        idx = (st[:, None] + base[None, :]).ravel()[:n]
        Y = A[idx]
        out[b] = Y.mean(axis=0) / Y.std(axis=0, ddof=1) * math.sqrt(252)
    return out


def drift_timing(held: pd.DataFrame, ex_inst: pd.DataFrame, groups: dict, win: tuple[str, str]) -> pd.DataFrame:
    """E[w r] = E[w] E[r] (static exposure x drift) + Cov(w, r) (timing). Annualised, per group of instruments."""
    sl = slice(pd.Timestamp(win[0]), pd.Timestamp(win[1]))
    H = held.loc[sl]
    R = ex_inst.reindex(index=H.index, columns=H.columns).fillna(0.0)
    tot = (H * R).mean() * 252
    drift = H.mean() * R.mean() * 252
    df = pd.DataFrame({"total": tot, "drift": drift})
    df["timing"] = df["total"] - df["drift"]
    df["avg_weight"] = H.mean()
    df["group"] = [groups.get(c, "other") for c in df.index]
    g = df.groupby("group")[["total", "drift", "timing", "avg_weight"]].sum()
    g.loc["ALL"] = g.sum()
    return g
