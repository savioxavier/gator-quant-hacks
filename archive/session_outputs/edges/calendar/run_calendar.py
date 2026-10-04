"""Calendar-effect study on CME futures (rules fixed in SPEC.md before this script was run).

Outputs (this folder): variants_table.csv, long_history_evidence.csv, splits_table.csv, summary.json,
variant_series.parquet; and edges/series/<candidate>.parquet + .json for the four base candidates.
Run from the repository root with GQH_DATA_DIR set. Never logs trials, never touches results/.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

import calcommon as K
from calcommon import CU, E

BENCH = pd.read_parquet(K.HERE / "bench.parquet")
BENCH_COLS = BENCH[["ES16", "S1", "F2"]]
FF = pd.read_parquet("<home>/.cache/gqh/ff_daily.parquet").set_index("date")
FF.index = pd.to_datetime(FF.index)


# --------------------------------------------------------------------------- masks on a planned calendar

def rule_masks(cal_real: pd.DatetimeIndex) -> dict[str, pd.Series]:
    planned = CU.planned_calendar(cal_real)
    sched, unsched = K.classify_closures(planned)
    assert len(unsched) == 0, unsched
    tom_base = CU.window_mask(planned, -1, 3)
    pre = K.pre_holiday_mask(planned, sched)
    return {
        "tom_base": tom_base,
        "tom_v1": CU.window_mask(planned, 0, 3),
        "tom_v2": CU.window_mask(planned, 0, 4),
        "tsy_base": CU.window_mask(planned, -2, 0),
        "tsy_v2": CU.window_mask(planned, -1, 0),
        "prehol_base": pre,
        "prehol_v1": pre & ~tom_base,
        "fomc_base": K.fomc_even_mask(planned, K.load_fomc_day0()),
    }


def issuance_q(planned: pd.DatetimeIndex, period: str = "FWD") -> pd.Series:
    from src.strategies import ifc_treasury as T

    mt = T.monthly_issuance(period, ticker="ZN16", window=(-2, 0), issuance_sizing=True)
    qd = mt["q"].to_dict()
    return pd.Series([qd.get(p, np.nan) for p in planned.to_period("M")], index=planned, dtype=float)


VARIANTS = [  # (candidate, variant, instrument, mask key, multiplier)
    ("CAL_TOM_ES", "base_T-1..T+3", "ES16", "tom_base", None),
    ("CAL_TOM_ES", "V1_T..T+3", "ES16", "tom_v1", None),
    ("CAL_TOM_ES", "V2_T..T+4", "ES16", "tom_v2", None),
    ("CAL_TSY_ME_ZN", "base_T-2..T", "ZN16", "tsy_base", None),
    ("CAL_TSY_ME_ZN", "V1_issuance_q", "ZN16", "tsy_base", "q"),
    ("CAL_TSY_ME_ZN", "V2_T-1..T", "ZN16", "tsy_v2", None),
    ("CAL_PREHOL_ES", "base_H-1", "ES16", "prehol_base", None),
    ("CAL_PREHOL_ES", "V1_ex_TOM", "ES16", "prehol_v1", None),
    ("CAL_FOMC_EVEN_ES", "base_even_weeks", "ES16", "fomc_base", None),
    ("CAL_TOM_ES", "timing_F_ES", "F_ES", "tom_base", None),
    ("CAL_TSY_ME_ZN", "timing_F_ZN", "F_ZN", "tsy_base", None),
    ("CAL_PREHOL_ES", "timing_F_ES", "F_ES", "prehol_base", None),
    ("CAL_FOMC_EVEN_ES", "timing_F_ES", "F_ES", "fomc_base", None),
]

PUB_SPLITS = {   # in-sample split dates (publication or end of the source sample)
    "CAL_TOM_ES": None,                                    # whole futures sample is after 2008
    "CAL_TSY_ME_ZN": pd.Timestamp("2019-01-01"),           # Hartley & Schwarz sample ends 2018
    "CAL_PREHOL_ES": None,                                 # whole futures sample is after 1990
    "CAL_FOMC_EVEN_ES": pd.Timestamp("2017-01-01"),        # CMVJ sample ends 2016
}

LIT = {
    "CAL_TOM_ES": "Lakonishok & Smidt (1988, RFS; DJIA 1897-1986); McConnell & Xu (2008, FAJ; CRSP 1926-2005); "
                  "Ariel (1987, JFE)",
    "CAL_TSY_ME_ZN": "Hartley & Schwarz (2019, Predictable End-of-Month Treasury Returns; 1990-2018); "
                     "repository sleeve C (HYPOTHESES.md s.1)",
    "CAL_PREHOL_ES": "Ariel (1990, JF; CRSP 1963-1982); Lakonishok & Smidt (1988)",
    "CAL_FOMC_EVEN_ES": "Cieslak, Morse & Vissing-Jorgensen (2019, JF; 1994-2016); post-sample reversal 2017-2021 "
                        "(Knox & Vissing-Jorgensen 2026, FEDS 2026-023)",
}

RULE_TEXT = {
    "CAL_TOM_ES": "Long ES16 from the close of T-2 to the close of T+3 (return days T-1..T+3), flat otherwise",
    "CAL_TSY_ME_ZN": "Long ZN16 over return days T-2..T (enter close T-3, exit close T), no issuance sizing",
    "CAL_PREHOL_ES": "Long ES16 over the last session before each scheduled NYSE holiday (enter close H-2)",
    "CAL_FOMC_EVEN_ES": "Long ES16 on FOMC-cycle even-week days k in {-1..3, 9..13, 19..23, 29..33}, day 0 = "
                        "scheduled announcement day",
}


def first_live(held: pd.Series) -> pd.Timestamp:
    live = held.abs() > 0
    return live.idxmax()


def main() -> None:
    cal = K.nyse_calendar("FWD")
    masks = rule_masks(cal)
    planned = masks["tom_base"].index
    q = issuance_q(planned, "FWD")
    rows, split_rows, ev_rows = [], [], []
    store, summary = {}, {"variants": {}, "notes": []}

    for cand, var, inst, mk, mult in VARIANTS:
        r = K.run_rule(masks[mk], inst, "FWD", mult_planned=(q if mult == "q" else None))
        sc, u1 = r["sc"], r["u1"]
        start = first_live(r["sc_held"])
        is_win, later_win = (start, K.IS_END), (K.LATER_START, K.LATER_END)
        store[f"{cand}|{var}"] = sc.loc[start:]
        ex_inst = r["ex_inst"]
        vsum = {"instrument": inst, "start": str(start.date())}
        for wlab, (a, b) in (("IS", is_win), ("later", later_win)):
            for clab in ("net_1x", "net_2x", "gross"):
                st = K.window_stats(sc[clab], r["sc_held"], r["sc_turnover"], BENCH_COLS, a, b)
                rows.append({"candidate": cand, "variant": var, "instrument": inst, "window": wlab,
                             "cost": clab, "scaling": "10vol", **st})
            # unscaled (1 unit when in window) extras, net 1x
            st_u = K.window_stats(u1["net_1x"], r["u1_held"], r["u1_turnover"], BENCH_COLS, a, b)
            sl = slice(a, b)
            held_u = r["u1_held"].loc[sl]
            xu = u1["net_1x"].loc[sl]
            bh = ex_inst.loc[sl].dropna()
            inv = held_u.abs() > 0
            extra = {
                "mean_bp_per_invested_day": float(xu[inv].mean() * 1e4) if inv.any() else float("nan"),
                "bh_mean_bp_per_day": float(bh.mean() * 1e4),
                "bh_sharpe": K.sharpe(bh),
                "bh_ann_ret": float(bh.mean() * K.TD),
                "timed_ann_ret_1unit": float(xu.mean() * K.TD),
                "bh_ann_ret_at_same_exposure": float(bh.mean() * K.TD * inv.mean()),
                "bh_max_dd_at_same_exposure": K.max_dd(bh * inv.mean()),
            }
            rows.append({"candidate": cand, "variant": var, "instrument": inst, "window": wlab, "cost": "net_1x",
                         "scaling": "1unit", **st_u, **extra})
            # alpha vs ES16 (scaled net 1x)
            reg = K.hac_reg(sc["net_1x"].loc[sl], BENCH[["ES16"]].loc[sl])
            boot = K.stationary_bootstrap_sharpe_diff(xu, bh) if inst in ("ES16", "F_ES", "ZN16", "F_ZN") else {}
            vsum[wlab] = {"alpha_vs_ES16": reg, "boot_timed_minus_bh_sharpe": boot, **extra}
        # pre/post publication split of the in-sample period
        sp = PUB_SPLITS[cand]
        subs = [("IS_all", start, K.IS_END)]
        if sp is not None:
            subs += [("IS_pre_" + str(sp.date()), start, sp - pd.Timedelta(days=1)), ("IS_post_" + str(sp.date()), sp, K.IS_END)]
        subs += [("later", K.LATER_START, K.LATER_END)]
        for slab, a, b in subs:
            st = K.window_stats(sc["net_1x"], r["sc_held"], r["sc_turnover"], BENCH_COLS, a, b)
            ind_real = CU.planned_to_realized(masks[mk].astype(float).to_frame("m"), cal)["m"] > 0
            dt = K.dummy_test(ex_inst.loc[a:b], ind_real.loc[a:b])
            split_rows.append({"candidate": cand, "variant": var, "instrument": inst, "split": slab,
                               "net1x_sharpe": st.get("sharpe"), "net1x_nw_t": st.get("nw_t"),
                               "net1x_ann_ret": st.get("ann_ret"), "net1x_max_dd": st.get("max_dd"),
                               **{f"ev_{k}": v for k, v in dt.items()}})
        summary["variants"][f"{cand}|{var}"] = vsum
        print(f"done {cand} {var}")

    vt = pd.DataFrame(rows)
    vt.to_csv(K.HERE / "variants_table.csv", index=False)
    pd.DataFrame(split_rows).to_csv(K.HERE / "splits_table.csv", index=False)
    pd.concat(store, axis=1).to_parquet(K.HERE / "variant_series.parquet")

    # ------------------------------------------------------------------ IS-period equivalence check (TOM base)
    cal_is = K.nyse_calendar("IS")
    m_is = rule_masks(cal_is)
    r_is = K.run_rule(m_is["tom_base"], "ES16", "IS")
    a = r_is["sc"]["net_1x"].loc[:K.IS_END]
    b = store["CAL_TOM_ES|base_T-1..T+3"]["net_1x"].loc[:K.IS_END]
    both = pd.concat([a, b], axis=1, join="inner").dropna()
    maxdiff = float((both.iloc[:, 0] - both.iloc[:, 1]).abs().max())
    summary["is_equivalence_check_tom_base_max_abs_diff"] = maxdiff
    assert maxdiff < 1e-12, maxdiff

    # ------------------------------------------------------------------ ETF comparator for the Treasury sleeve
    from src.strategies import ifc_treasury as T

    rf = E.load_rf("FWD")
    comp = {}
    for lab, ov in (("ETF_C_issuance_IEF_3bp", {}), ("ETF_C_q1_IEF_3bp", {"issuance_sizing": False})):
        w = T.decision_weights("FWD", **{**{k: v for k, v in T.BASE_PARAMS.items()}, **ov})
        ohlc = E.load_ohlc(["IEF"], "FWD")
        net, *_ = E.simulate(w, ohlc, rf, exec="next_close")
        x = net - rf.reindex(net.index).ffill().fillna(0.0)
        st_is = K.window_stats(x, None, None, BENCH_COLS, "2010-09-01", K.IS_END)
        st_is_full = K.window_stats(x, None, None, BENCH_COLS, "2005-04-01", K.IS_END)
        st_l = K.window_stats(x, None, None, BENCH_COLS, K.LATER_START, K.LATER_END)
        comp[lab] = {"IS_2010-09_on": {k: st_is[k] for k in ("sharpe", "nw_t", "max_dd", "ann_vol")},
                     "IS_2005_on": {k: st_is_full[k] for k in ("sharpe", "nw_t", "max_dd", "ann_vol")},
                     "later": {k: st_l[k] for k in ("sharpe", "nw_t", "max_dd", "ann_vol")}}
    summary["treasury_etf_comparator"] = comp

    # ------------------------------------------------------------------ long-history evidence (gross, unscaled)
    ffr = FF["Mkt_RF"].dropna()
    ffcal = ffr.index
    ff_sched, ff_unsched = K.classify_closures(ffcal)
    ff_masks = {
        "tom_base": CU.window_mask(ffcal, -1, 3), "tom_v1": CU.window_mask(ffcal, 0, 3),
        "tom_v2": CU.window_mask(ffcal, 0, 4),
        "prehol_base": K.pre_holiday_mask(ffcal, ff_sched),
        "fomc_base": K.fomc_even_mask(ffcal[ffcal >= "1994-01-01"], K.load_fomc_day0()).reindex(ffcal).fillna(False),
    }
    ff_masks["prehol_v1"] = ff_masks["prehol_base"] & ~ff_masks["tom_base"]
    idx = pd.read_parquet("<home>/.cache/gqh/index_daily.parquet")
    gspc = idx[idx["ticker"] == "^GSPC"].set_index("date")["close"].sort_index()
    gspc.index = pd.to_datetime(gspc.index)
    rf_all = E.load_rf("FWD")
    gr = (gspc.pct_change(fill_method=None) - rf_all.reindex(gspc.index).ffill().fillna(0.0)).dropna()
    gcal = gr.index
    g_sched, g_unsched = K.classify_closures(CU.planned_calendar(gcal))
    gpl = CU.planned_calendar(gcal)
    g_masks_p = {
        "tom_base": CU.window_mask(gpl, -1, 3), "tom_v1": CU.window_mask(gpl, 0, 3), "tom_v2": CU.window_mask(gpl, 0, 4),
        "prehol_base": K.pre_holiday_mask(gpl, g_sched),
        "fomc_base": K.fomc_even_mask(gpl, K.load_fomc_day0()),
    }
    g_masks_p["prehol_v1"] = g_masks_p["prehol_base"] & ~g_masks_p["tom_base"]
    g_masks = {k: (CU.planned_to_realized(v.astype(float).to_frame("m"), gcal)["m"] > 0) for k, v in g_masks_p.items()}
    ff_splits = {
        "tom": [("1963-07..1987-12 pre-LS", "1963-07-01", "1987-12-31"),
                ("1988-01..2007-12 post-LS pre-MX", "1988-01-01", "2007-12-31"),
                ("2008-01..2024-10-02 post-MX", "2008-01-01", "2024-10-02"),
                ("2024-10-03..2026-08 later", "2024-10-03", "2026-08-31"),
                ("1963-07..2024-10-02 all IS", "1963-07-01", "2024-10-02")],
        "prehol": [("1963-07..1982-12 Ariel sample", "1963-07-01", "1982-12-31"),
                   ("1983-01..1990-12 pre-pub", "1983-01-01", "1990-12-31"),
                   ("1991-01..2024-10-02 post-pub", "1991-01-01", "2024-10-02"),
                   ("2024-10-03..2026-08 later", "2024-10-03", "2026-08-31")],
        "fomc": [("1994-01..2016-12 CMVJ sample", "1994-01-01", "2016-12-31"),
                 ("2017-01..2024-10-02 post-sample", "2017-01-01", "2024-10-02"),
                 ("2024-10-03..2026-08 later", "2024-10-03", "2026-08-31")],
    }
    g_splits = {
        "tom": [("2003..2007", "2003-01-02", "2007-12-31"), ("2008-01..2024-10-02", "2008-01-01", "2024-10-02"),
                ("2024-10-03..2026-10-02 later", "2024-10-03", "2026-10-02")],
        "prehol": [("2003-01..2024-10-02", "2003-01-02", "2024-10-02"), ("2024-10-03..2026-10-02 later", "2024-10-03", "2026-10-02")],
        "fomc": [("2003..2016", "2003-01-02", "2016-12-31"), ("2017-01..2024-10-02", "2017-01-01", "2024-10-02"),
                 ("2024-10-03..2026-10-02 later", "2024-10-03", "2026-10-02")],
    }
    for src_lab, ser, mk_all, splits in (("FF_Mkt_RF", ffr, ff_masks, ff_splits), ("GSPC_price_ex_rf", gr, g_masks, g_splits)):
        for mk, m in mk_all.items():
            fam = mk.split("_")[0]
            for slab, a, b in splits[fam]:
                dt = K.dummy_test(ser.loc[a:b], m.loc[a:b])
                ev_rows.append({"source": src_lab, "rule": mk, "split": slab, **dt})
    # futures-era ES16 / ZN16 evidence for completeness (gross instrument returns, whole IS)
    ev = pd.DataFrame(ev_rows)
    ev.to_csv(K.HERE / "long_history_evidence.csv", index=False)
    summary["ff_unscheduled_closures_excluded"] = [str(d.date()) for d in ff_unsched]
    summary["ff_scheduled_holidays_count"] = int(len(ff_sched))

    # ------------------------------------------------------------------ candidate series (base, ES16/ZN16)
    K.SERIES_DIR.mkdir(parents=True, exist_ok=True)
    base_of = {"CAL_TOM_ES": "base_T-1..T+3", "CAL_TSY_ME_ZN": "base_T-2..T", "CAL_PREHOL_ES": "base_H-1",
               "CAL_FOMC_EVEN_ES": "base_even_weeks"}
    for cand, var in base_of.items():
        s = store[f"{cand}|{var}"][["net_1x", "net_2x", "gross"]]
        s.index.name = "date"
        s.to_parquet(K.SERIES_DIR / f"{cand}.parquet")
        inst = "ZN16" if "ZN" in cand else "ES16"
        side = {
            "candidate": cand, "rule": RULE_TEXT[cand], "literature": LIT[cand], "instrument": inst,
            "columns": {"net_1x": f"daily excess return over T-bill, net of realistic one-way cost "
                                  f"{K.COST_REAL[inst]} bp per unit notional (+ engine roll round trip)",
                        "net_2x": "same at 2x costs", "gross": "no costs"},
            "scaling": "L = min(5, 0.10 / (sigma_hat * sqrt(f_hat))) inside windows, fixed per window from the decision "
                       "date two sessions before the first return day; sigma_hat = sqrt(252*EWMA_com60(r^2)) of the "
                       "instrument's daily excess returns; f_hat = share of trailing 252 sessions in the rule's windows",
            "execution": "engine.simulate exec=next_close (weight held over day t decided at close t-2); calendar "
                         "offsets on the planned NYSE calendar",
            "is_window": [str(s.index[0].date()), str(K.IS_END.date())],
            "later_window": [str(K.LATER_START.date()), str(K.LATER_END.date())],
            "spec": "edges/calendar/SPEC.md", "script": "edges/calendar/run_calendar.py",
        }
        (K.SERIES_DIR / f"{cand}.json").write_text(json.dumps(side, indent=2))

    (K.HERE / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print("wrote outputs")


if __name__ == "__main__":
    main()
