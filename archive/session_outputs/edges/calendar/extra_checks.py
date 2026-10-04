"""Post-hoc robustness checks, added AFTER the main results were seen (not part of SPEC.md, no selection made on them).

1. Yearly net returns of the four base candidates (10 % vol scaling, realistic costs).
2. Treasury month-end mechanism breadth: gross in-window minus out-of-window daily excess return over return days
   T-2..T on every Treasury future (F_ZT, F_ZF, F_ZN, F_ZB, F_UB; UTC-day closes) and ZN16, IS and later.
3. Correlation of the Treasury candidate with forward test 1's C_F stream (the same idea inside F2).
4. Pre-holiday events by holiday, IS, unscaled ES16 excess return on H-1.
Writes extra_checks.json and extra_evidence_curve.csv.
"""
from __future__ import annotations

import json

import pandas as pd

import calcommon as K
from calcommon import CU, E

import run_calendar as R


def main() -> None:
    out = {}
    vs = pd.read_parquet(K.HERE / "variant_series.parquet")
    yr = {}
    for cand, var in (("CAL_TOM_ES", "base_T-1..T+3"), ("CAL_TSY_ME_ZN", "base_T-2..T"), ("CAL_PREHOL_ES", "base_H-1"),
                      ("CAL_FOMC_EVEN_ES", "base_even_weeks")):
        x = vs[(f"{cand}|{var}", "net_1x")].dropna()
        x = x[x.index >= x.ne(0).idxmax()]
        yr[cand] = {int(k): round(float(v), 4) for k, v in ((1 + x).groupby(x.index.year).prod() - 1).items()}
    out["yearly_net_1x_10vol"] = yr

    cal = K.nyse_calendar("FWD")
    planned = CU.planned_calendar(cal)
    m = CU.planned_to_realized(CU.window_mask(planned, -2, 0).astype(float).to_frame("m"), cal)["m"] > 0
    rows = []
    rf = E.load_rf("FWD")
    for tk in ("F_ZT", "F_ZF", "F_ZN", "F_ZB", "F_UB", "ZN16"):
        ohlc = E.load_ohlc([tk], "FWD")
        c = ohlc["close"][tk]
        ex = (c.pct_change(fill_method=None) - rf.reindex(c.index).ffill().fillna(0.0)).dropna()
        ex = ex[ex.index >= "2010-06-08"]
        for lab, a, b in (("IS 2010-06..2024-10-02", "2010-06-08", "2024-10-02"),
                          ("IS pre-2019", "2010-06-08", "2018-12-31"), ("IS 2019..2024-10-02", "2019-01-01", "2024-10-02"),
                          ("later", "2024-10-03", "2026-10-02")):
            rows.append({"instrument": tk, "split": lab, **K.dummy_test(ex.loc[a:b], m.loc[a:b])})
    pd.DataFrame(rows).to_csv(K.HERE / "extra_evidence_curve.csv", index=False)

    from src import forward

    fr = forward.stream_frames("F2", "FWD")
    cf = fr["ex"]["C_F"]
    tsy = vs[("CAL_TSY_ME_ZN|base_T-2..T", "net_1x")]
    pair = pd.concat([tsy, cf], axis=1, join="inner").dropna()
    pis = pair.loc[:K.IS_END]
    pl = pair.loc[K.LATER_START:]
    out["corr_tsy_with_F2_C_F_stream"] = {"IS": float(pis.corr().iloc[0, 1]), "later": float(pl.corr().iloc[0, 1])}
    out["F2_C_F_stream_sharpe"] = {"IS_2010-09_on": K.sharpe(cf.loc["2010-09-28":K.IS_END]),
                                   "later": K.sharpe(cf.loc[K.LATER_START:])}

    # pre-holiday events by holiday type (IS, unscaled ES16 return on H-1)
    sched, _ = K.classify_closures(planned)
    ohlc = E.load_ohlc(["ES16"], "FWD")
    c = ohlc["close"]["ES16"]
    ex = c.pct_change(fill_method=None) - rf.reindex(c.index).ffill().fillna(0.0)
    tom = CU.window_mask(planned, -1, 3)
    ev = []
    for h in sched:
        if h < pd.Timestamp("2010-09-01") or h > K.IS_END:
            continue
        pos = planned.searchsorted(h) - 1
        d = planned[pos]
        if d not in ex.index:
            continue
        name = {1: "NewYear/MLK", 2: "Presidents", 3: "GoodFri", 4: "GoodFri", 5: "Memorial", 6: "Juneteenth",
                7: "July4", 9: "Labor", 11: "Thanksgiving", 12: "Christmas"}.get(h.month, str(h.month))
        if h.month == 1 and h.day > 7:
            name = "MLK"
        elif h.month == 1:
            name = "NewYear"
        ev.append({"holiday": str(h.date()), "type": name, "pre_day": str(d.date()), "in_tom_window": bool(tom.loc[d]),
                   "es16_excess_bp": float(ex.loc[d] * 1e4)})
    evd = pd.DataFrame(ev)
    out["prehol_by_type_IS"] = evd.groupby("type")["es16_excess_bp"].agg(["count", "mean", "median"]).round(2).to_dict(orient="index")
    out["prehol_in_vs_out_tom_IS"] = evd.groupby("in_tom_window")["es16_excess_bp"].agg(["count", "mean", "median"]).round(2).to_dict(orient="index")
    (K.HERE / "extra_checks.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=1))
    print(pd.DataFrame(rows)[["instrument", "split", "n_in", "mean_in_bp", "mean_out_bp", "diff_bp", "diff_t_nw",
                              "timed_sharpe", "bh_sharpe"]].round(2).to_string())


if __name__ == "__main__":
    main()
