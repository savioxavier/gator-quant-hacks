"""Point-in-time checks.

1. Truncation test: every decision builder is recomputed on data cut at date t; its row t must equal the row t of
   the full-sample run (a builder that peeks past t would differ).
2. Fill-lag test: an impulse decision at close d0 must first be held on return day d0+2 under next_close (traded at
   the close of d0+1) and on d0+1 open->close under next_open; it must earn nothing on d0's own return or earlier.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import lib as L
from src import engine as E
from src import forward2 as F


def trunc(ohlc, t):
    return {k: v.loc[:t] for k, v in ohlc.items()}


def month_end_ok(cal, t):
    # month_offsets treats a series ending on t as an incomplete month if t + 1 business day is in the same month
    return (t + pd.offsets.BDay(1)).to_period("M") != t.to_period("M")


def main():
    ohlc, rf, ex = L.futures_panel("FWD")
    cal = ex.index
    me = F._month_ends(cal)
    tests = [t for t in me if t.year in (2012, 2015, 2018, 2020, 2022, 2024) and t.month in (3, 9)]
    tests = [t for t in tests if month_end_ok(cal, t)]
    report = {"truncation": [], "fill_lag": {}}

    on_full, valid_full = L.month_end_sma_signal(ohlc["close"])
    full = {
        "A1_long_only": L.rp_decisions(ohlc, ex),
        "B1_gtaa_fixed": L.rp_decisions(ohlc, ex, on_full, "fixed"),
        "B2_gtaa_rescale": L.rp_decisions(ohlc, ex, on_full, "rescale"),
        "C1_fut5": L.fut5_decisions(ohlc["close"], 0.20, "gtaa"),
    }
    for t in tests:
        o_t = trunc(ohlc, t)
        ex_t = ex.loc[:t]
        on_t, _ = L.month_end_sma_signal(o_t["close"])
        part = {
            "A1_long_only": L.rp_decisions(o_t, ex_t),
            "B1_gtaa_fixed": L.rp_decisions(o_t, ex_t, on_t, "fixed"),
            "B2_gtaa_rescale": L.rp_decisions(o_t, ex_t, on_t, "rescale"),
            "C1_fut5": L.fut5_decisions(o_t["close"], 0.20, "gtaa"),
        }
        for k in full:
            d = float((full[k].loc[t] - part[k].loc[t]).abs().max())
            report["truncation"].append({"builder": k, "date": str(t.date()), "max_abs_diff": d})

    # EWMAC: daily decisions, test arbitrary days (path-dependent buffer included)
    ew_full = L.Ewmac(ohlc, rf, ex)
    w_full = {"slow_ls": ew_full.weights(L.EWMAC_SLOW, 0.20, True),
              "fast_lf": ew_full.weights(L.EWMAC_FAST, 0.25, False, floor0=True)}
    for t in [pd.Timestamp(x) for x in ("2013-05-15", "2016-11-09", "2020-03-16", "2023-07-20")]:
        t = cal[cal.get_indexer([t], method="pad")[0]]
        ew_t = L.Ewmac(trunc(ohlc, t), rf.loc[:t], ex.loc[:t])
        part = {"slow_ls": ew_t.weights(L.EWMAC_SLOW, 0.20, True),
                "fast_lf": ew_t.weights(L.EWMAC_FAST, 0.25, False, floor0=True)}
        for k in w_full:
            d = float((w_full[k].loc[t] - part[k].loc[t]).abs().max())
            report["truncation"].append({"builder": f"EWMAC_{k}", "date": str(t.date()), "max_abs_diff": d})

    # ETF builder
    eo = E.load_ohlc(F.S3_TICKERS, "FWD")
    e_full = L.etf_decisions(eo["close"], 0.20, "gtaa")
    me_e = F._month_ends(eo["close"].index)
    for t in [x for x in me_e if x.year in (2008, 2013, 2019, 2023) and x.month == 6]:
        part = L.etf_decisions(eo["close"].loc[:t], 0.20, "gtaa")
        d = float((e_full.loc[t] - part.loc[t]).abs().max())
        report["truncation"].append({"builder": "ETF_gtaa", "date": str(t.date()), "max_abs_diff": d})

    # 2. fill-lag impulse test
    d0 = pd.Timestamp("2019-03-12")
    i0 = cal.get_loc(d0)
    imp = pd.DataFrame(0.0, index=cal, columns=["F_ES"])
    imp.iloc[i0:i0 + 1] = 1.0                       # decision only at close d0 (zero again from d0+1)
    imp_o = {k: v[["F_ES"]] for k, v in ohlc.items()}
    _, _, _, held_c, _ = E.simulate(imp, imp_o, rf, exec="next_close", cost_bps={"F_ES": 0.0})
    first_c = held_c.index[held_c["F_ES"].abs() > 0][0]
    report["fill_lag"]["next_close"] = {
        "decision_date": str(d0.date()), "first_return_day_held": str(first_c.date()),
        "sessions_after_decision": int(cal.get_loc(first_c) - i0), "required": 2,
    }
    eo1 = {k: v[["SPY"]] for k, v in eo.items()}
    cal_e = eo["close"].index
    j0 = cal_e.get_loc(d0)
    imp_e = pd.DataFrame(0.0, index=cal_e, columns=["SPY"])
    imp_e.iloc[j0:j0 + 1] = 1.0
    _, _, _, held_o, _ = E.simulate(imp_e, eo1, rf, exec="next_open", cost_bps={"SPY": 0.0})
    first_o = held_o.index[held_o["SPY"].abs() > 0][0]
    report["fill_lag"]["next_open"] = {
        "decision_date": str(d0.date()), "first_day_held_from_open": str(first_o.date()),
        "sessions_after_decision": int(cal_e.get_loc(first_o) - j0), "required": 1,
    }
    mx = max(r["max_abs_diff"] for r in report["truncation"])
    report["truncation_max_abs_diff"] = mx
    report["truncation_n_tests"] = len(report["truncation"])
    report["pass"] = bool(mx < 1e-10 and report["fill_lag"]["next_close"]["sessions_after_decision"] == 2
                          and report["fill_lag"]["next_open"]["sessions_after_decision"] == 1)
    (L.OUT / "pit_checks.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({k: v for k, v in report.items() if k != "truncation"}, indent=1))
    bad = [r for r in report["truncation"] if r["max_abs_diff"] >= 1e-10]
    print("failures:", bad)


if __name__ == "__main__":
    main()
