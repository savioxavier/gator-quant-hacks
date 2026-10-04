"""Futures run of the 24 pre-registered variants (SPEC.md sections 2-4, 6, 7).

Usage: python rp_futures.py            # full run (period FWD, IS slice + later window), writes out/ and series/
       python rp_futures.py --check    # point-in-time check: period IS run must equal the FWD run's IS slice
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

import rp_core as R
from src import config as C
from src import engine as E

ASSETS = {"ES": "F_ES", "ZN": "F_ZN", "GC": "F_GC"}
COST = {"F_ES": 0.75, "F_ZN": 1.0, "F_GC": 1.5}
SLEEVES = ["ES", "ZN", "GC", "SB"]
IS_END = pd.Timestamp(C.IS_END)
SPLIT_A_END = pd.Timestamp("2016-12-30")
LATER_START = pd.Timestamp(C.OOS_START)


def build(period: str):
    tick = list(ASSETS.values())
    ohlc = E.load_ohlc(tick, period)
    rf = E.load_rf(period).reindex(ohlc["close"].index).ffill().fillna(0.0)
    ex = ohlc["close"].pct_change(fill_method=None).sub(rf, axis=0)
    traded = (ohlc["volume"].fillna(0.0) > 0).astype(float)
    active = traded.rolling(R.ACTIVE_WINDOW, min_periods=1).max().astype(bool)
    P = R.Panel(ex, ohlc["close"], active)
    out = {}
    for s in SLEEVES:
        for ov in R.OVERLAYS:
            if s == "SB":
                w = P.rp(["F_ES", "F_ZN"], ov)
            else:
                w = P.single(ASSETS[s], ov)
            res = {}
            for m in (1.0, 2.0, 0.0):
                net, gross, turn, held, cost = E.simulate(w, ohlc, rf, exec="next_close", cost_bps=COST, cost_mult=m)
                res[m] = (net, turn, held)
            name = f"rpm_{s}_{ov}"
            out[name] = {
                "w_dec": w, "held": res[1.0][2], "turn": res[1.0][1],
                "net1": res[1.0][0], "net2": res[2.0][0], "netg": res[0.0][0],
            }
    return out, rf, P, ohlc


def first_return_day(P: R.Panel) -> pd.Timestamp:
    for t in P.me:
        if all(P.eligible(t, c) for c in ASSETS.values()):
            i = P.ex.index.get_loc(t)
            return P.ex.index[i + 2]
    raise RuntimeError("no common start")


def check() -> None:
    fw, *_ = build("FWD")
    isr, *_ = build("IS")
    worst = 0.0
    for k in fw:
        a = fw[k]["net1"].loc[:IS_END]
        b = isr[k]["net1"].loc[:IS_END]
        diff = float((a - b).abs().max())
        worst = max(worst, diff)
        print(f"{k:18s} max|FWD-IS| over IS = {diff:.3e}")
    print("WORST", worst)
    (R.OUT / "pit_check.txt").write_text(f"max abs difference of daily net returns, FWD vs IS run, over IS: {worst:.3e}\n")


def main() -> None:
    R.OUT.mkdir(exist_ok=True)
    R.SERIES_DIR.mkdir(exist_ok=True)
    out, rf, P, ohlc = build("FWD")
    start = first_return_day(P)
    end = ohlc["close"].index[-1]
    cal_full = E.trading_calendar("FWD")
    bm = pd.read_parquet(R.OUT / "benchmarks.parquet")
    rows = []
    series = {}
    for name, d in out.items():
        sl = slice(start, end)
        rfw = rf.loc[sl]
        ex1 = (d["net1"].loc[sl] - rfw).rename("net_1x")
        ex2 = (d["net2"].loc[sl] - rfw).rename("net_2x")
        exg = (d["netg"].loc[sl] - rfw).rename("gross")
        ser = pd.concat([ex1, ex2, exg], axis=1)
        ser.index.name = "date"
        series[name] = ser
        held = d["held"].loc[sl]
        for win, a, b in (("IS", start, IS_END), ("A", start, SPLIT_A_END), ("B", SPLIT_A_END + pd.Timedelta(days=1), IS_END),
                          ("LATER", LATER_START, end)):
            w = slice(a, b)
            st = R.window_stats(ex1.loc[w], ex2.loc[w], exg.loc[w], d["net1"].loc[w], d["turn"].loc[w], cal_full)
            for k2 in ("ES", "S1", "F2"):
                st[f"corr_{k2}"] = float(pd.concat([ex1.loc[w], bm[k2].loc[w]], axis=1).dropna().corr().iloc[0, 1])
            st["avg_gross"] = float(held.loc[w].abs().sum(axis=1).mean())
            st["frac_invested"] = float((held.loc[w].abs().sum(axis=1) > 1e-9).mean())
            st.update({"name": name, "window": win})
            rows.append(st)
    tab = pd.DataFrame(rows)
    cols = ["name", "window"] + [c for c in tab.columns if c not in ("name", "window")]
    tab = tab[cols]
    tab.to_csv(R.OUT / "futures_table.csv", index=False)

    # cap binding counts
    caps = pd.DataFrame([{"key": f"{k[0]}|{k[1]}", "cap_hits": v[0], "decisions": v[1]} for k, v in P.cap_hits.items()])
    caps.to_csv(R.OUT / "cap_hits.csv", index=False)

    # yearly excess returns (net 1x), all variants
    yearly = pd.DataFrame({k: (1 + s["net_1x"]).groupby(s.index.year).prod() - 1 for k, s in series.items()})
    yearly.to_csv(R.OUT / "yearly_net1_excess.csv")

    # bootstrap comparisons on IS net 1x
    comps = []
    isl = slice(start, IS_END)
    for s in SLEEVES:
        g = lambda ov: series[f"rpm_{s}_{ov}"]["net_1x"].loc[isl]
        for a, b in (("CV", "STATIC"), ("MM", "STATIC"), ("MM", "CV"), ("FB", "CV"), ("CVB", "CV"), ("FBB", "CVB")):
            r = R.block_bootstrap_diff(g(a), g(b))
            mdd_a = R.max_dd(out[f"rpm_{s}_{a}"]["net1"].loc[isl])
            mdd_b = R.max_dd(out[f"rpm_{s}_{b}"]["net1"].loc[isl])
            comps.append({"sleeve": s, "a": a, "b": b, **r, "mdd_a": mdd_a, "mdd_b": mdd_b})
    for a, b in (("rpm_SB_CV", "rpm_ES_CV"), ("rpm_SB_CV", "rpm_ZN_CV"), ("rpm_SB_STATIC", "rpm_ES_STATIC")):
        r = R.block_bootstrap_diff(series[a]["net_1x"].loc[isl], series[b]["net_1x"].loc[isl])
        comps.append({"sleeve": "cross", "a": a, "b": b, **r,
                      "mdd_a": R.max_dd(out[a]["net1"].loc[isl]), "mdd_b": R.max_dd(out[b]["net1"].loc[isl])})
    pd.DataFrame(comps).to_csv(R.OUT / "bootstrap_is.csv", index=False)

    # series + sidecars
    rule = {
        "STATIC": "w = 10% / sigma_LR (trailing 2520-session RMS vol, min 252); SB: inverse long-run-vol legs scaled to 10% with the trailing 2520-session second-moment matrix",
        "CV": "w = 10% / sigma_EWMA (EWMA of squared daily excess returns, com 60); SB: inverse-vol legs scaled to 10% with D R D, R = trailing 252-session correlation",
        "CVB": "as CV with sigma = 0.7 sigma_EWMA + 0.3 sigma_LR",
        "MM": "Moreira-Muir: w = 10% sigma_LR / RV_month (annualised realized variance of the month's daily excess returns), capped at 1.5 x 10%/sigma_LR; SB: multiplier 0.01/RV of the STATIC SB portfolio, cap 1.5",
        "FB": "CV weights x Faber 10-month filter (month-end TR close > mean of last 10 month-end closes), per leg, flat leg in T-bills, no re-levering",
        "FBB": "CVB weights x Faber 10-month filter",
    }
    sleeve_txt = {"ES": "long F_ES", "ZN": "long F_ZN", "GC": "long F_GC", "SB": "stock/bond risk parity F_ES + F_ZN, equal risk"}
    for name, ser in series.items():
        _, s, ov = name.split("_", 2)
        ser.to_parquet(R.SERIES_DIR / f"{name}.parquet")
        meta = {
            "candidate": name, "task_label": "risk_premia", "sleeve": sleeve_txt[s], "overlay": ov, "rule": rule[ov],
            "decisions": "month-end close d, data up to d; filled at next session close (engine exec=next_close); engine re-trades to target every session",
            "target_vol": "10% annualised ex-ante; gross notional cap 4",
            "columns": {"net_1x": "daily excess return over T-bill, net of realistic costs",
                        "net_2x": "same with 2x costs", "gross": "before costs"},
            "cost_bps_one_way_realistic": COST, "roll": "one extra round trip of the held position on each roll day",
            "window": [str(ser.index[0].date()), str(ser.index[-1].date())],
            "in_sample": [str(start.date()), C.IS_END], "later_descriptive": [C.OOS_START, str(end.date())],
            "spec": "edges/risk_premia/SPEC.md", "script": "edges/risk_premia/rp_futures.py",
        }
        (R.SERIES_DIR / f"{name}.json").write_text(json.dumps(meta, indent=2))
    print("start", start, "end", end)
    show = tab[tab.window.isin(["IS", "LATER"])][["name", "window", "sharpe_net1", "sharpe_net2", "sharpe_gross", "ann_vol",
                                                  "max_dd", "worst_year", "pct_positive_years", "roll2y_p10", "nw_t", "corr_ES"]]
    with pd.option_context("display.width", 250, "display.max_rows", 200):
        print(show.round(3).to_string(index=False))


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    else:
        main()
