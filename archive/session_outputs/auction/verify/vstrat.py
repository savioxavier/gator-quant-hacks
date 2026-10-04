"""Independent re-implementation of the auction-cycle variants (verification)."""
from __future__ import annotations

import json
import math
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"<scratch>/auction/verify")
import vdata as V  # noqa: E402

COST = {"F_ZT": 0.5, "F_ZF": 0.7, "F_ZN": 1.0, "F_ZB": 1.5, "F_UB": 1.5, "F_ES": 1.0}
DUR = {"F_ZT": 1.9, "F_ZF": 4.2, "F_ZN": 6.3, "F_ZB": 15.0, "F_UB": 20.0}
INST = {2: "F_ZT", 3: "F_ZT", 5: "F_ZF", 7: "F_ZN", 10: "F_ZN", 20: "F_ZB", 30: "F_UB"}
HEDGE_ALL = {2: "F_UB", 5: "F_UB", 7: "F_UB", 10: "F_ZF", 20: "F_ZF", 30: "F_ZF"}
TRADED = [2, 5, 7, 10, 20, 30]
W = {"sel": ("2010-06-07", "2020-12-31"), "val": ("2021-01-01", "2024-10-02"), "full": ("2010-06-07", "2024-10-02"),
     "later": ("2024-10-03", "2026-10-02"), "pre14": ("2010-06-07", "2013-12-31"), "post14": ("2014-01-01", "2024-10-02")}

cal, rex, roll, rf = V.returns()
A = V.auctions()
A, calx = V.index_events(A, cal)
NC = len(cal)
NX = len(calx)


def vol(r):
    return np.sqrt(252 * (r ** 2).ewm(com=60, min_periods=40).mean())


def sleeve(ev, inst, hedge, t_pre, t_post, gate, cap, pre_excl_day0=False):
    """Held weights (return-day index cal) for one maturity sleeve.

    Pre window: return days A-t_pre+1 .. A  (or A-t_pre .. A-1 for ES), short.  Post: A+1 .. A+t_post, long.
    Gate: return day j usable only if announcement session N <= j-2 (decision at close j-2)."""
    h = DUR[inst] / DUR[hedge] if hedge else 0.0
    ru = rex[inst] - (h * rex[hedge] if hedge else 0)
    sig = vol(ru.dropna()).reindex(cal).to_numpy()
    legs = []
    flag = np.zeros(NX)
    for e in ev.itertuples():
        pre = range(-t_pre, 0) if pre_excl_day0 else range(-t_pre + 1, 1)
        for sgn, offs in ((-1, pre), (1, range(1, t_post + 1))):
            js = [e.A + k for k in offs if 0 <= e.A + k < NX and ((not gate) or e.N <= e.A + k - 2)]
            if js:
                legs.append((sgn, js))
                flag[js] = 1
    f = pd.Series(flag).rolling(252, min_periods=63).mean().to_numpy()
    pos = np.zeros(NX)
    lim = np.zeros(NX)
    for sgn, js in legs:
        d = js[0] - 2
        if d < 0 or d >= NC or not (np.isfinite(sig[d]) and np.isfinite(f[d]) and sig[d] > 0 and f[d] > 0):
            continue
        L = min(cap, 0.10 / (sig[d] * math.sqrt(f[d])))
        pos[js] += sgn * L
        lim[js] = np.maximum(lim[js], L)
    pos = np.clip(pos, -lim, lim)[:NC]
    w = pd.DataFrame(0.0, index=cal, columns=V.TICK)
    w[inst] += pos
    if hedge:
        w[hedge] -= h * pos
    return w


def combine(sl):
    if len(sl) == 1:
        return next(iter(sl.values()))
    names = list(sl)
    R = rex.fillna(0.0)
    g = pd.DataFrame({m: (sl[m] * R).sum(axis=1) for m in names})
    for m in names:
        act = sl[m].abs().sum(axis=1) > 0
        g.loc[g.index < (act.idxmax() if act.any() else g.index[-1] + pd.Timedelta(days=1)), m] = np.nan
    cnt = g.notna().cumsum()
    me = pd.Series(cal, index=cal).groupby(cal.to_period("M")).max()
    mult = pd.DataFrame(np.nan, index=cal, columns=names)
    for d in me:
        live = [m for m in names if cnt.loc[d, m] >= 63]
        if not live:
            continue
        S = g.loc[:d, live].tail(252).cov(min_periods=63).fillna(0.0).to_numpy() * 252
        w = np.ones(len(live)) / len(live)
        v = w @ S @ w
        if v <= 0:
            continue
        mult.loc[d] = 0.0
        mult.loc[d, live] = w * min(3.0, 0.10 / math.sqrt(v))
    mult = mult.ffill().shift(2).fillna(0.0)
    return sum(sl[m].mul(mult[m], axis=0) for m in names)


def pnl(held, cm=1.0):
    """Daily excess return of held weights (return-day indexed): own cost model, no drift adjustment."""
    R = rex.fillna(0.0)
    gross = (held * R).sum(axis=1)
    c = pd.Series(COST)[V.TICK] / 1e4 * cm
    trade = held.diff().abs().fillna(held.abs()) + 2 * held.abs() * roll
    return gross - (trade * c).sum(axis=1)


def sharpe(x):
    x = x.dropna()
    return float(x.mean() / x.std() * math.sqrt(252)) if len(x) > 20 and x.std() > 0 else float("nan")


def nw_t(x, lags=None):
    x = pd.Series(x).dropna().to_numpy()
    n = len(x)
    if lags is None:
        lags = int(math.floor(4 * (n / 100) ** (2 / 9)))
    u = x - x.mean()
    s = u @ u / n
    for l in range(1, lags + 1):
        s += 2 * (1 - l / (lags + 1)) * (u[l:] @ u[:-l]) / n
    return float(x.mean() / math.sqrt(s / n))


def evsel(terms, excl=False):
    e = A[A.term.isin(terms)]
    return e[~e.tom] if excl else e


def build_variant(vid):
    p = vid.split("_")
    if vid.startswith(("V1", "V3", "D1", "V2", "D2")):
        terms = [2] if "_2y_" in vid else TRADED
        t = 10 if "t10" in vid else 5
        gate = not vid.startswith("D")
        excl = vid.startswith("V3")
        hedge = None
        if vid.startswith(("V2", "D2")):
            hedge = {2: "F_ZN"} if terms == [2] else HEDGE_ALL
        sl = {}
        for m in terms:
            inst = INST[m]
            sl[m] = sleeve(evsel([m], excl), inst, hedge.get(m) if hedge else None, t, t, gate, 30.0 / DUR[inst])
        return combine(sl)
    if vid.startswith("V4"):
        return sleeve(evsel([2], vid.endswith("_x")), "F_ES", None, 5, 5, True, 3.0, pre_excl_day0=True)
    raise ValueError(vid)


DAILY = ["V1_all_t5", "V1_all_t10", "V1_2y_t10", "V2_2y_t10", "V2_2y_t5", "V2_all_t5", "V3_all_t5_x", "V3_all_t10_x",
         "V4_ES_2y", "V4_ES_2y_x", "D1_all_t5_known", "D2_2y_t10_known"]


def stats_of(held):
    live = held.abs().sum(axis=1) > 0
    start = live.idxmax()
    s = {k: pnl(held, k_)[start:] for k, k_ in (("n1", 1.0), ("n2", 2.0), ("g", 0.0))}
    out = {"start": str(start.date())}
    for wn, (a, b) in W.items():
        out[f"{wn}_n1"] = sharpe(s["n1"][a:b])
        out[f"{wn}_n2"] = sharpe(s["n2"][a:b])
        out[f"{wn}_g"] = sharpe(s["g"][a:b])
    out["nw_sel"] = nw_t(s["n1"][W["sel"][0]:W["sel"][1]])
    out["nw_full"] = nw_t(s["n1"][W["full"][0]:W["full"][1]])
    out["long_days_full"] = int((held.sum(axis=1)[:"2024-10-02"] > 1e-12).sum())
    out["short_days_full"] = int((held.sum(axis=1)[:"2024-10-02"] < -1e-12).sum())
    return out, s


if __name__ == "__main__":
    res, ser = {}, {}
    for vid in DAILY:
        held = build_variant(vid)
        st, s = stats_of(held)
        res[vid] = st
        ser[vid] = pd.DataFrame(s)
        ser[vid].to_parquet(V.OUT / f"v_{vid}.parquet")
        held.to_parquet(V.OUT / f"held_{vid}.parquet")
        print(f"{vid:16s} sel {st['sel_n1']:+.3f} val {st['val_n1']:+.3f} (2x {st['val_n2']:+.3f}) full {st['full_n1']:+.3f} "
              f"g {st['full_g']:+.3f} later {st['later_n1']:+.3f} pre14 {st['pre14_n1']:+.3f} post14 {st['post14_n1']:+.3f} "
              f"nwsel {st['nw_sel']:+.2f} nwfull {st['nw_full']:+.2f} L/S days {st['long_days_full']}/{st['short_days_full']}")
    (V.OUT / "verify_variants.json").write_text(json.dumps(res, indent=1))
