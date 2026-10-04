"""Treasury auction cycle on futures (SPEC.md in this folder). Lou, Yan & Zhang (FMG DP684 / RFS 2013).

Run from the repository root:
  GQH_DATA_DIR=<home>/.cache/gqh PYTHONIOENCODING=utf-8 <venv python> <this file>

Writes only under scratchpad/auction/futures_test/ and scratchpad/auction/series/.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<solo-repo>")
sys.path.insert(0, str(REPO))
assert os.environ.get("GQH_OOS_UNLOCK") != "1"
from src import engine as E                       # noqa: E402
from src.strategies import ifc_treasury as TC     # noqa: E402

SP = Path("<scratch>")
OUT = SP / "auction" / "futures_test"
SER = SP / "auction" / "series"
SER.mkdir(parents=True, exist_ok=True)
HOURLY = SP / "intraday_study" / "data" / "hourly_panel.parquet"
P = "FWD"

COST = {"F_ZT": 0.5, "F_ZF": 0.7, "F_ZN": 1.0, "F_ZB": 1.5, "F_UB": 1.5, "F_ES": 1.0}
DUR = {"F_ZT": 1.9, "F_ZF": 4.2, "F_ZN": 6.3, "F_ZB": 15.0, "F_UB": 20.0}
INST = {2: "F_ZT", 3: "F_ZT", 5: "F_ZF", 7: "F_ZN", 10: "F_ZN", 20: "F_ZB", 30: "F_UB"}
HEDGE_ALL = {2: "F_UB", 5: "F_UB", 7: "F_UB", 10: "F_ZF", 20: "F_ZF", 30: "F_ZF"}
TRADED = [2, 5, 7, 10, 20, 30]
STD = [2, 3, 5, 7, 10, 20, 30]
TICKERS = ["F_ZT", "F_ZF", "F_ZN", "F_ZB", "F_UB", "F_ES"]

SEL = (pd.Timestamp("2010-06-07"), pd.Timestamp("2020-12-31"))
VAL = (pd.Timestamp("2021-01-01"), pd.Timestamp("2024-10-02"))
FULL = (pd.Timestamp("2010-06-07"), pd.Timestamp("2024-10-02"))
LATER = (pd.Timestamp("2024-10-03"), pd.Timestamp("2026-10-02"))
PRE14 = (pd.Timestamp("2010-06-07"), pd.Timestamp("2013-12-31"))
POST14 = (pd.Timestamp("2014-01-01"), pd.Timestamp("2024-10-02"))
WINDOWS = {"sel": SEL, "val": VAL, "full": FULL, "later": LATER, "pre14": PRE14, "post14": POST14}


# ------------------------------------------------------------------------------------------ data
def term_from_security_term(s: str) -> int:
    y = re.search(r"(\d+)-Year", s)
    m = re.search(r"(\d+)-Month", s)
    yrs = (int(y.group(1)) if y else 0) + (int(m.group(1)) / 12 if m else 0)
    return min(STD, key=lambda t: abs(t - yrs))


def load_data():
    ohlc = E.load_ohlc(TICKERS, P)
    rf = E.load_rf(P)
    cal = ohlc["close"].index                      # NYSE calendar from 2005 (futures NaN before 2010-06-07)
    rf = rf.reindex(cal).ffill().fillna(0.0)
    rex = ohlc["close"].pct_change(fill_method=None).sub(rf, axis=0)
    first_data = ohlc["close"]["F_ZN"].first_valid_index()
    rex.loc[rex.index <= first_data] = np.nan
    # indexing calendar: NYSE days + 25 weekdays after the end (only to index auctions beyond the data)
    tail = pd.bdate_range(cal[-1] + pd.Timedelta(days=1), periods=25)
    calx = pd.DatetimeIndex(np.concatenate([cal.values, tail.values.astype("datetime64[ns]")]))
    a = TC.load_nominal_auctions(P)
    a["term"] = a["security_term"].map(term_from_security_term)
    a = a.drop_duplicates(["term", "auction_date"]).copy()
    a["A_i"] = calx.searchsorted(a["auction_date"].to_numpy(), side="left")
    a["on_cal"] = calx[np.clip(a["A_i"], 0, len(calx) - 1)] == a["auction_date"].to_numpy()
    a["N_i"] = calx.searchsorted(a["announcemt_date"].to_numpy(), side="left")
    a["dom"] = a["auction_date"].dt.day
    a["tom"] = (a["dom"] >= 25) | (a["dom"] <= 5)
    assert a.loc[a["auction_date"] >= "2009-01-01", "on_cal"].all()
    a = a[a["auction_date"] >= "2004-06-01"].sort_values(["auction_date", "term"]).reset_index(drop=True)
    return ohlc, rf, cal, calx, rex, a


def ewma_vol(r: pd.Series) -> pd.Series:
    return np.sqrt(252 * (r ** 2).ewm(com=60, min_periods=40).mean())


# ------------------------------------------------------------------------------------------ sleeves
def sleeve_positions(ev: pd.DataFrame, inst: str, hedge: str | None, pre: tuple[int, int], post: tuple[int, int],
                     gate: bool, cal: pd.DatetimeIndex, calx: pd.DatetimeIndex, rex: pd.DataFrame, cap: float):
    """Held weights on return days (index cal) for one maturity sleeve, plus per-event unit returns.

    pre/post: inclusive event-day offsets relative to A (pre traded short, post long)."""
    n = len(calx)
    h = DUR[inst] / DUR[hedge] if hedge else 0.0
    r_unit = rex[inst] - (h * rex[hedge] if hedge else 0.0)            # unit-notional sleeve return
    sig = ewma_vol(r_unit.dropna()).reindex(cal)
    legs = []                                                             # (sign, list of day idx)
    for e in ev.itertuples():
        for sign, (lo, hi) in ((-1, pre), (1, post)):
            days = [e.A_i + k for k in range(lo, hi + 1)]
            days = [j for j in days if 0 <= j < n and ((not gate) or e.N_i <= j - 2)]
            if days:
                legs.append((sign, days, e.Index))
    flag = np.zeros(n)
    for _, days, _ in legs:
        flag[days] = 1.0
    f = pd.Series(flag, index=calx).rolling(252, min_periods=63).mean().reindex(cal)
    held = np.zeros(n)
    lmax = np.zeros(n)
    sig_v = sig.to_numpy()
    f_v = f.to_numpy()
    leg_rows = []
    pos_cal = len(cal)
    for sign, days, eidx in legs:
        d0 = days[0] - 2
        if d0 < 0 or d0 >= pos_cal:
            continue
        s, ff = sig_v[d0], f_v[d0]
        if not (np.isfinite(s) and np.isfinite(ff) and s > 0 and ff > 0):
            continue
        L = min(cap, 0.10 / (s * math.sqrt(ff)))
        held[days] += sign * L
        lmax[days] = np.maximum(lmax[days], L)
        leg_rows.append((eidx, sign, days))
    held = np.clip(held, -lmax, lmax)[:pos_cal]
    w = pd.DataFrame(0.0, index=cal, columns=TICKERS)
    w[inst] += held
    if hedge:
        w[hedge] += -h * held
    # unit-notional event returns over traded days (gross), for "bp per event"
    ru = r_unit.to_numpy()
    ev_ret = {}
    for eidx, sign, days in leg_rows:
        dd = [j for j in days if j < pos_cal]
        v = np.nansum(sign * ru[dd]) if dd else np.nan
        ev_ret[eidx] = ev_ret.get(eidx, 0.0) + v
    flag_cal = pd.Series(flag[:pos_cal], index=cal)
    return w, pd.Series(ev_ret), flag_cal, held


def combine_sleeves(sleeves: dict[str, pd.DataFrame], rex: pd.DataFrame, cal: pd.DatetimeIndex):
    """Equal risk across maturity sleeves: month-end k = min(3, 0.10/sqrt(252 w'Sw)), applied from d+2."""
    if len(sleeves) == 1:
        return next(iter(sleeves.values()))
    names = list(sleeves)
    g = pd.DataFrame({m: (sleeves[m] * rex.reindex(columns=TICKERS).fillna(0.0)).sum(axis=1) for m in names})
    active = pd.DataFrame({m: sleeves[m].abs().sum(axis=1) > 0 for m in names})
    first = {m: active[m].idxmax() if active[m].any() else None for m in names}
    X = g.copy()
    for m in names:
        if first[m] is None:
            X[m] = np.nan
        else:
            X.loc[X.index < first[m], m] = np.nan
    cnt = X.notna().cumsum()
    me = pd.Series(cal, index=cal).groupby(cal.to_period("M")).max().to_numpy()
    mult = pd.DataFrame(np.nan, index=cal, columns=names)
    for d in pd.DatetimeIndex(me):
        live = [m for m in names if cnt.loc[d, m] >= 63]
        if not live:
            continue
        H = X.loc[:d, live].tail(252)
        S = H.cov(min_periods=63).fillna(0.0).to_numpy() * 252
        w = np.full(len(live), 1.0 / len(live))
        var = float(w @ S @ w)
        if var <= 0:
            continue
        k = min(3.0, 0.10 / math.sqrt(var))
        mult.loc[d, :] = 0.0
        mult.loc[d, live] = w * k
    mult = mult.ffill().shift(2).fillna(0.0)          # decided at close d, applied to return days from d+2
    tot = sum(sleeves[m].mul(mult[m], axis=0) for m in names)
    return tot


def simulate_held(held: pd.DataFrame, ohlc, rf):
    w_dec = held.shift(-2).fillna(0.0)                # decision at close t-2 -> held on return day t
    out = {}
    for col, cm in (("net_1x", 1.0), ("net_2x", 2.0), ("gross", 0.0)):
        net, gross, to, hld, cost = E.simulate(w_dec, ohlc, rf, exec="next_close", cost_bps=COST, cost_mult=cm)
        out[col] = net - rf
        if col == "net_1x":
            out["_held"] = hld
            out["_turnover"] = to
    # check alignment: engine held == intended held
    assert np.allclose(out["_held"].to_numpy()[:-2], held.to_numpy()[:-2], atol=1e-12)
    return out


# ------------------------------------------------------------------------------------------ V5 intraday
def intraday_variant(a: pd.DataFrame, terms: list[int], cal: pd.DatetimeIndex, rex: pd.DataFrame):
    hp = pd.read_parquet(HOURLY, columns=["root", "trade_date", "hour_et", "ret_simple", "cme_non_nyse_session"])
    z = hp[(hp["root"] == "ZN") & (~hp["cme_non_nyse_session"])]
    ev = a[a["term"].isin(terms) & (a["N_i"] <= a["A_i"] - 1)]
    ev = ev[ev["auction_date"].isin(cal)].drop_duplicates("auction_date")   # one trade per day
    flag = pd.Series(0.0, index=cal)
    flag.loc[pd.DatetimeIndex(ev["auction_date"])] = 1.0                       # all event days (f uses history)
    days = pd.DatetimeIndex(ev.loc[ev["auction_date"] >= pd.Timestamp("2010-06-08"), "auction_date"])
    zz = z[z["trade_date"].isin(days)]
    default_f = len(terms) * 12 / 252
    f = flag.rolling(252, min_periods=63).mean().shift(1).fillna(default_f).clip(lower=1 / 252)
    sig = ewma_vol(rex["F_ZN"].dropna()).reindex(cal).shift(1)
    rows = []
    for d, grp in zz.groupby("trade_date"):
        hrs = set(grp["hour_et"].tolist())
        if 12 not in hrs or 15 not in hrs:
            continue
        pre = grp[grp["hour_et"].isin([9, 10, 11, 12])]["ret_simple"]
        post = grp[grp["hour_et"].isin([13, 14, 15])]["ret_simple"]
        rp = float(np.prod(1 + pre.to_numpy()) - 1)
        rq = float(np.prod(1 + post.to_numpy()) - 1)
        s, ff = sig.get(d, np.nan), f.get(d, np.nan)
        if not (np.isfinite(s) and s > 0):
            continue
        L = min(5.0, 0.10 / (s * math.sqrt(ff)))
        rows.append({"date": d, "r_pre": rp, "r_post": rq, "L": L})
    t = pd.DataFrame(rows).set_index("date")
    unit = -t["r_pre"] + t["r_post"]
    gross = (t["L"] * unit).reindex(cal).fillna(0.0)
    c = (4 * t["L"] * COST["F_ZN"] / 1e4).reindex(cal).fillna(0.0)
    out = {"gross": gross, "net_1x": gross - c, "net_2x": gross - 2 * c}
    held_gross = t["L"].reindex(cal).fillna(0.0)
    return out, t, unit, held_gross


# ------------------------------------------------------------------------------------------ stats
def sharpe(x: pd.Series) -> float:
    x = x.dropna()
    return float(x.mean() / x.std() * math.sqrt(252)) if len(x) > 20 and x.std() > 0 else float("nan")


def win(x: pd.Series, w):
    return x.loc[w[0]:w[1]].dropna()


def max_dd(ex: pd.Series) -> float:
    eq = (1 + ex.dropna()).cumprod()
    return float((eq / eq.cummax() - 1).min())


# ------------------------------------------------------------------------------------------ event study
def nw_t(x, lags=5):
    return E.newey_west_tstat(pd.Series(x), lags=lags)


def event_study(a, rex, cal):
    rows, drows = [], []
    rv = {k: rex[k].to_numpy() for k in TICKERS}
    first = rex["F_ZN"].first_valid_index()
    i0 = cal.get_loc(first) + 1
    n = len(cal)
    periods = {"2010-2013": PRE14, "2014-2024": POST14, "later_2024_2026": LATER}
    specs = [(f"{t}y", t, INST[t]) for t in STD] + [("ES_2y", 2, "F_ES")]
    for lab, term, inst in specs:
        ev = a[(a["term"] == term)]
        for pname, (p0, p1) in periods.items():
            sub = ev[(ev["auction_date"] >= p0) & (ev["auction_date"] <= p1)]
            M, dates = [], []
            for e in sub.itertuples():
                lo, hi = e.A_i - 10, e.A_i + 10
                if lo < i0 or hi >= n or cal[hi] > p1 or cal[lo] < p0:
                    continue
                v = rv[inst][lo:hi + 1]
                if np.isnan(v).any():
                    continue
                M.append(v * 1e4)
                dates.append(e.auction_date)
            if len(M) < 5:
                continue
            M = np.array(M)
            C = np.cumsum(M, axis=1)
            nn = len(M)
            for j, k in enumerate(range(-10, 11)):
                mu, sd = M[:, j].mean(), M[:, j].std(ddof=1)
                cm, cs = C[:, j].mean(), C[:, j].std(ddof=1)
                rows.append({"series": lab, "instrument": inst, "period": pname, "k": k, "n": nn,
                             "mean_bp": mu, "t": mu / (sd / math.sqrt(nn)),
                             "cum_from_m10_bp": cm, "cum_t": cm / (cs / math.sqrt(nn))})
            uncond = rex[inst].loc[p0:p1].dropna().mean() * 1e4
            d = {"series": lab, "instrument": inst, "period": pname, "n": nn, "uncond_mean_bp_per_day": uncond}
            for t in (5, 10):
                # D_t = sum(A+1..A+t) - sum(A-t+1..A); index of A is 10
                post = M[:, 11:11 + t].sum(axis=1)
                pre = M[:, 11 - t:11].sum(axis=1)
                D = post - pre
                d[f"D{t}_bp"] = D.mean()
                d[f"D{t}_nw_t"] = nw_t(D)
                d[f"pre{t}_bp"] = pre.mean()
                d[f"post{t}_bp"] = post.mean()
            d["day0_bp"] = M[:, 10].mean()
            d["day0_t"] = M[:, 10].mean() / (M[:, 10].std(ddof=1) / math.sqrt(nn))
            drows.append(d)
    return pd.DataFrame(rows), pd.DataFrame(drows)


# ------------------------------------------------------------------------------------------ main
def main():
    ohlc, rf, cal, calx, rex, a = load_data()
    print("auctions since 2010 by term:", a[a.auction_date >= "2010-06-01"].groupby("term").size().to_dict())

    # event study first (descriptive)
    es_rows, es_d = event_study(a, rex, cal)
    es_rows.to_csv(OUT / "event_study_daily.csv", index=False)
    es_d.to_csv(OUT / "event_study_spreads.csv", index=False)

    core_saved = pd.read_parquet(SP / "edges" / "series" / "PORT_core_ER_6.parquet")
    core_saved.index = pd.to_datetime(core_saved.index)
    sleeveC = pd.read_parquet(SP / "edges" / "series" / "CAL_TSY_ME_ZN.parquet")
    sleeveC.index = pd.to_datetime(sleeveC.index)
    zn_ex = rex["F_ZN"]

    def ev_of(terms, excl=False):
        e = a[a["term"].isin(terms)]
        return e[~e["tom"]] if excl else e

    def tre_sleeve(term, t, hedge_map=None, gate=True, excl=False):
        inst = INST[term]
        hedge = hedge_map.get(term) if hedge_map else None
        cap = 30.0 / DUR[inst]
        return sleeve_positions(ev_of([term], excl), inst, hedge, (-t + 1, 0), (1, t), gate, cal, calx, rex, cap)

    VARIANTS = {
        "V1_all_t5": dict(kind="tre", terms=TRADED, t=5, hedge=None, gate=True, excl=False,
                          rule="Outright: short the auctioned maturity's future over return days [A-4, A], long over [A+1, A+5]; 2y ZT, 5y ZF, 7y ZN, 10y ZN, 20y ZB, 30y UB; 10% ex-ante per maturity sleeve, equal risk, announcement-gated"),
        "V1_all_t10": dict(kind="tre", terms=TRADED, t=10, hedge=None, gate=True, excl=False,
                           rule="As V1_all_t5 with t=10: short [A-9, A], long [A+1, A+10]"),
        "V1_2y_t10": dict(kind="tre", terms=[2], t=10, hedge=None, gate=True, excl=False,
                          rule="Outright ZT around 2-year auctions: short [A-9, A], long [A+1, A+10], 10% ex-ante, announcement-gated"),
        "V2_2y_t10": dict(kind="tre", terms=[2], t=10, hedge={2: "F_ZN"}, gate=True, excl=False,
                          rule="Paper Table V analogue: short ZT / long DV01-equal ZN (0.30 ZN per ZT) over [A-9, A], reverse over [A+1, A+10], 10% ex-ante, gated"),
        "V2_2y_t5": dict(kind="tre", terms=[2], t=5, hedge={2: "F_ZN"}, gate=True, excl=False,
                         rule="As V2_2y_t10 with t=5"),
        "V2_all_t5": dict(kind="tre", terms=TRADED, t=5, hedge=HEDGE_ALL, gate=True, excl=False,
                          rule="Each maturity DV01-hedged outside its auction cluster (2/5/7y vs UB; 10/20/30y vs ZF), t=5, equal risk, gated"),
        "V3_all_t5_x": dict(kind="tre", terms=TRADED, t=5, hedge=None, gate=True, excl=True,
                            rule="V1_all_t5 excluding auctions dated 25th..5th"),
        "V3_all_t10_x": dict(kind="tre", terms=TRADED, t=10, hedge=None, gate=True, excl=True,
                             rule="V1_all_t10 excluding auctions dated 25th..5th"),
        "V4_ES_2y": dict(kind="es", excl=False, gate=True,
                         rule="ES short [A-5, A-1], long [A+1, A+5] around 2-year auctions, 10% ex-ante (cap 3), gated"),
        "V4_ES_2y_x": dict(kind="es", excl=True, gate=True,
                           rule="V4_ES_2y excluding 2-year auctions dated 25th..5th"),
        "V5_ZN_10y_id": dict(kind="id", terms=[10],
                             rule="10-year auction days: ZN short 09:00-13:00 ET, long 13:00-16:00 ET (hourly), 4 one-way ZN costs per event, L=min(5, 0.10/(sigma sqrt f))"),
        "V5_ZN_7y10y_id": dict(kind="id", terms=[7, 10], rule="As V5 on 7-year and 10-year auction days"),
        "D1_all_t5_known": dict(kind="tre", terms=TRADED, t=5, hedge=None, gate=False, excl=False, diag=True,
                                rule="DIAGNOSTIC: V1_all_t5 without the announcement gate (calendar assumed known)"),
        "D2_2y_t10_known": dict(kind="tre", terms=[2], t=10, hedge={2: "F_ZN"}, gate=False, excl=False, diag=True,
                                rule="DIAGNOSTIC: V2_2y_t10 without the announcement gate (paper's Table V timing)"),
    }

    results, series, extra = {}, {}, {}
    comp_rows = []
    for vid, spec in VARIANTS.items():
        info = {}
        if spec["kind"] == "tre":
            sl, evr, flags, pre_share = {}, [], [], []
            for term in spec["terms"]:
                w, er, fl, held = tre_sleeve(term, spec["t"], spec["hedge"], spec["gate"], spec["excl"])
                sl[f"{term}y"] = w
                evr.append(er)
                flags.append(fl)
            tot = combine_sleeves(sl, rex, cal)
            sim = simulate_held(tot, ohlc, rf)
            ser = {k: sim[k] for k in ("net_1x", "net_2x", "gross")}
            held_gross = sim["_held"].abs().sum(axis=1)
            avg_cost = float((sim["_held"].abs() * pd.Series(COST)).sum(axis=1).sum() / max(held_gross.sum(), 1e-12))
            ev_all = pd.concat(evr)
            ev_dates = a.loc[ev_all.index, "auction_date"]
            ev_is = ev_all[(ev_dates >= FULL[0]) & (ev_dates <= FULL[1])]
            info["mean_bp_per_event"] = float(ev_is.mean() * 1e4)
            info["n_events_is"] = int(ev_is.notna().sum())
            info["event_t"] = float(ev_is.mean() / (ev_is.std(ddof=1) / math.sqrt(len(ev_is))))
            # component sleeves (each maturity alone, 10% ex-ante), descriptive
            if len(sl) > 1 and vid in ("V1_all_t5", "V1_all_t10", "V2_all_t5"):
                for m, wm in sl.items():
                    sm = simulate_held(wm, ohlc, rf)
                    x = sm["net_1x"]
                    nz = sm["_held"].abs().sum(axis=1).gt(0)
                    if not nz.any():
                        continue
                    x = x.loc[nz.idxmax():]
                    comp_rows.append({"variant": vid, "sleeve": m, **{f"{k}_net1x": sharpe(win(x, wv)) for k, wv in WINDOWS.items()},
                                      "full_gross": sharpe(win(sm["gross"].loc[nz.idxmax():], FULL)),
                                      "full_net2x": sharpe(win(sm["net_2x"].loc[nz.idxmax():], FULL))})
        elif spec["kind"] == "es":
            ev = ev_of([2], spec["excl"])
            w, er, fl, held = sleeve_positions(ev, "F_ES", None, (-5, -1), (1, 5), spec["gate"], cal, calx, rex, 3.0)
            sim = simulate_held(w, ohlc, rf)
            ser = {k: sim[k] for k in ("net_1x", "net_2x", "gross")}
            held_gross = sim["_held"].abs().sum(axis=1)
            avg_cost = COST["F_ES"]
            ev_dates = a.loc[er.index, "auction_date"]
            ev_is = er[(ev_dates >= FULL[0]) & (ev_dates <= FULL[1])]
            info["mean_bp_per_event"] = float(ev_is.mean() * 1e4)
            info["n_events_is"] = int(ev_is.notna().sum())
            info["event_t"] = float(ev_is.mean() / (ev_is.std(ddof=1) / math.sqrt(len(ev_is))))
        else:
            ser, tab, unit, held_gross = intraday_variant(a, spec["terms"], cal, rex)
            avg_cost = COST["F_ZN"]
            u_is = unit.loc[FULL[0]:FULL[1]]
            info["mean_bp_per_event"] = float(u_is.mean() * 1e4)
            info["n_events_is"] = int(len(u_is))
            info["event_t"] = float(u_is.mean() / (u_is.std(ddof=1) / math.sqrt(len(u_is))))
            tis = tab.loc[FULL[0]:FULL[1]]
            for nm, col in (("pre_09_13", "r_pre"), ("post_13_16", "r_post")):
                x = tis[col] * 1e4
                info[f"{nm}_mean_bp"] = float(x.mean())
                info[f"{nm}_t"] = float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x))))
            for pn, pw in (("pre14", PRE14), ("post14", POST14), ("later", LATER)):
                x = tab.loc[pw[0]:pw[1]]
                if len(x) > 3:
                    info[f"{pn}_pre_09_13_bp"] = float(x["r_pre"].mean() * 1e4)
                    info[f"{pn}_post_13_16_bp"] = float(x["r_post"].mean() * 1e4)
                    info[f"{pn}_n"] = int(len(x))
            info["median_L"] = float(tab["L"].median())
            tab.to_csv(OUT / f"intraday_events_{vid}.csv")
        live = held_gross.gt(0)
        start = live.idxmax()
        df = pd.DataFrame({k: v.loc[start:] for k, v in ser.items()})
        df.index.name = "date"
        series[vid] = df
        res = {"id": vid, "rule": spec["rule"], "diagnostic": bool(spec.get("diag", False)), "first_live": str(start.date())}
        for wn, wv in WINDOWS.items():
            res[f"{wn}_net1x"] = sharpe(win(df["net_1x"], wv))
            res[f"{wn}_net2x"] = sharpe(win(df["net_2x"], wv))
            res[f"{wn}_gross"] = sharpe(win(df["gross"], wv))
        res["nw_t_full"] = E.newey_west_tstat(win(df["net_1x"], FULL))
        res["nw_t_sel"] = E.newey_west_tstat(win(df["net_1x"], SEL))
        res["max_dd_full"] = max_dd(win(df["net_1x"], FULL))
        res["vol_full"] = float(win(df["net_1x"], FULL).std() * math.sqrt(252))
        res["ann_ex_full"] = float(win(df["net_1x"], FULL).mean() * 252)
        hg = held_gross.loc[start:]
        res["days_traded_share_full"] = float(win(hg.gt(0).astype(float), FULL).mean())
        res["median_gross_when_live"] = float(hg[hg > 0].median())
        res["avg_cost_bp"] = avg_cost
        x = win(df["net_1x"], FULL)
        for lab, s in (("corr_sleeve_c", sleeveC["net_1x"]), ("corr_core_er6", core_saved["net_1x"]), ("corr_zn", zn_ex)):
            j = pd.concat([x, s], axis=1, join="inner").dropna()
            res[lab] = float(j.corr().iloc[0, 1]) if len(j) > 40 else float("nan")
        res.update(info)
        results[vid] = res
        extra[vid] = {"held_gross": held_gross, "avg_cost": avg_cost}
        print(f"{vid:18s} sel {res['sel_net1x']:+.2f} val {res['val_net1x']:+.2f} (2x {res['val_net2x']:+.2f}) "
              f"full {res['full_net1x']:+.2f} g {res['full_gross']:+.2f} later {res['later_net1x']:+.2f} "
              f"pre14 {res['pre14_net1x']:+.2f} post14 {res['post14_net1x']:+.2f} t {res['nw_t_full']:+.2f} "
              f"bp/ev {res['mean_bp_per_event']:+.2f} cC {res['corr_sleeve_c']:+.2f} cP {res['corr_core_er6']:+.2f} cZN {res['corr_zn']:+.2f}")

    tab = pd.DataFrame(results.values())
    tab.to_csv(OUT / "variant_table.csv", index=False)
    pd.DataFrame(comp_rows).to_csv(OUT / "component_sleeves.csv", index=False)

    # ---------------------------------------------------------------- choice (selection window only)
    elig = tab[~tab["diagnostic"]]
    chosen = elig.loc[elig["sel_net1x"].idxmax(), "id"]
    print("CHOSEN (max selection net 1x Sharpe):", chosen)

    # ---------------------------------------------------------------- save series
    for vid, df in series.items():
        df.to_parquet(SER / f"{vid}.parquet")
        (SER / f"{vid}.json").write_text(json.dumps({
            "candidate": vid, "task_label": "futures_test", "rule": results[vid]["rule"],
            "diagnostic": results[vid]["diagnostic"],
            "columns": {"net_1x": "daily excess return over T-bill, realistic one-way costs ZT 0.5 / ZF 0.7 / ZN 1.0 / ZB, UB 1.5 / ES 1.0 bp (+ engine roll round trip)",
                        "net_2x": "same at 2x costs", "gross": "no costs"},
            "execution": "engine.simulate exec=next_close (held on return day t decided at close t-2); auctions gated by announcement date <= t-2" if not VARIANTS[vid]["kind"] == "id"
            else "hourly ZN panel, intraday only, 4 one-way costs per event",
            "avg_cost_bp": extra[vid]["avg_cost"],
            "selection_window": [str(SEL[0].date()), str(SEL[1].date())], "validation_window": [str(VAL[0].date()), str(VAL[1].date())],
            "later_descriptive": [str(LATER[0].date()), str(LATER[1].date())],
            "spec": "auction/futures_test/SPEC.md", "script": "auction/futures_test/auction_futures.py"}, indent=2))
        hg = extra[vid]["held_gross"].loc[df.index[0]:]
        hg.rename("held_gross").to_frame().to_parquet(OUT / f"held_gross_{vid}.parquet")

    summary = {"chosen": chosen, "n_eligible": int(len(elig)), "variants": results}
    (OUT / "variants_summary.json").write_text(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
