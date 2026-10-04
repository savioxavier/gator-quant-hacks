"""Monthly / weekly sign-trend decision builders (MOP 2012, HOP 2017) on the 30 CME futures."""
from __future__ import annotations

import numpy as np
import pandas as pd

import common as K


def cum_ret(hist: pd.DataFrame, k: int, skip: int = 0) -> pd.Series:
    """Compounded excess return over the last k sessions, optionally excluding the last `skip` sessions."""
    h = hist.tail(k).fillna(0.0)
    if skip:
        h = h.iloc[:-skip]
    return (1 + h).prod() - 1


def decisions(dates: pd.DatetimeIndex, signal_fn, vol_scaled: bool = True, raw_scale: float = 0.40) -> pd.DataFrame:
    P = K.panel()
    ex, vol, elig = P["ex"], P["vol60"], P["elig60"]
    w_dec = pd.DataFrame(np.nan, index=ex.index, columns=K.TICK)
    for t in dates:
        el = [c for c in K.TICK if bool(elig.loc[t, c])]
        w = pd.Series(0.0, index=K.TICK)
        if el:
            hist = ex.loc[:t, el]
            sig = signal_fn(hist, vol.loc[t, el])
            if vol_scaled:
                w[el] = sig * (raw_scale / vol.loc[t, el]) / len(el)
            else:
                w[el] = sig / len(el)
            w = K.scale_to_target(w, ex.loc[:t])
        w_dec.loc[t] = w.values
    return w_dec.ffill().fillna(0.0)


def sig_sign(k: int, skip: int = 0):
    def f(hist, vol):
        return np.sign(cum_ret(hist, k, skip))
    return f


def sig_blend_sign(ks=(21, 63, 252)):
    def f(hist, vol):
        s = 0.0
        for k in ks:
            s = s + np.sign(cum_ret(hist, k))
        return s / len(ks)
    return f


def sig_blend_cont(ks=(21, 63, 252)):
    def f(hist, vol):
        sd = vol / np.sqrt(252)
        s = 0.0
        for k in ks:
            s = s + (cum_ret(hist, k) / (sd * np.sqrt(k))).clip(-1, 1)
        return s / len(ks)
    return f
