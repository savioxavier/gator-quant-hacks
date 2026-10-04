"""GTAA on futures vs long-only risk parity vs long-short trend (S1, trade-ngin-style EWMAC).

Every variant computed here is written to out/variants_full.csv (both windows). No variant is selected on the
2024-10-03..2026-10-02 window; comparisons and the bootstrap use 2011-09-02..2024-10-02 only.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

import lib as L
from src import engine as E
from src import forward as FW
from src import forward2 as F

ETF_COST = None   # engine default ETF costs (3 bp SPY/IEF/EFA, 5 bp VNQ/DBC)


def sub(ohlc, cols):
    return {k: v[cols] for k, v in ohlc.items()}


def main():
    ohlc, rf, ex = L.futures_panel("FWD")
    close = ohlc["close"]
    T30 = F.S1_TICKERS
    FC = F.S1_COST_BPS
    V = {}          # name -> dict(res, family, desc, kind, eligible)

    def add(name, res, family, desc, kind="futures", eligible=True):
        V[name] = {"res": res, "family": family, "desc": desc, "kind": kind, "eligible": eligible}

    # ---------------- signals
    on, valid = L.month_end_sma_signal(close)
    ls = valid.astype(float) * (2 * on - 1)

    # ---------------- (a) long-only risk parity
    wA1 = L.rp_decisions(ohlc, ex)
    w_lo = F.s1_decisions("FWD", long_only=True)
    chk_lo = float((wA1 - w_lo.reindex_like(wA1)).abs().max().max())
    add("A1_RP_LONG_INSTR", L.run(wA1, ohlc, rf, "next_close", FC), "a_long_only",
        "30 futures long-only, equal risk per instrument, 10% ex-ante vol, monthly (= forward2 LONG_ONLY_F)")
    wA2 = L.rp_decisions(ohlc, ex, class_equal=True)
    add("A2_RP_LONG_CLASS", L.run(wA2, ohlc, rf, "next_close", FC), "a_long_only",
        "30 futures long-only, equal risk per asset class (7 classes), equal within class, 10% vol")
    eqr = [t for t in T30 if L.CLASS_OF[t] in ("equity", "rates")]
    wP2 = L.rp_decisions(sub(ohlc, eqr), ex[eqr])
    add("P2_RP_LONG_EQ_RATES", L.run(wP2, sub(ohlc, eqr), rf, "next_close", FC), "drift_benchmark",
        "long-only equal risk over the 9 equity-index and Treasury futures only, 10% vol")
    wP1 = L.rp_decisions(sub(ohlc, ["F_ES", "F_ZN"]), ex[["F_ES", "F_ZN"]])
    add("P1_RP_LONG_ES_ZN", L.run(wP1, sub(ohlc, ["F_ES", "F_ZN"]), rf, "next_close", FC), "drift_benchmark",
        "long-only equal risk ES + ZN, 10% vol")

    # eligibility sanity: every eligible instrument at a decision has a valid SMA
    miss = 0
    for t in F._month_ends(ex.index):
        if t not in valid.index:
            continue
        held_names = wA1.loc[t][wA1.loc[t] != 0].index
        miss += int((~valid.loc[t, held_names]).sum())

    # ---------------- (b) GTAA on futures
    wB1 = L.rp_decisions(ohlc, ex, on, "fixed")
    add("B1_GTAA_FUT_INSTR_FIXED", L.run(wB1, ohlc, rf, "next_close", FC), "b_gtaa_futures",
        "A1 x 10-month SMA long-or-flat filter per instrument; off slots in T-bills (risk budget of on slots unchanged)")
    wB2 = L.rp_decisions(ohlc, ex, on, "rescale")
    add("B2_GTAA_FUT_INSTR_RESCALE", L.run(wB2, ohlc, rf, "next_close", FC), "b_gtaa_futures",
        "same filter, filtered book rescaled to 10% ex-ante vol (gross <= 3)")
    wB3 = L.rp_decisions(ohlc, ex, on, "fixed", class_equal=True)
    add("B3_GTAA_FUT_CLASS_FIXED", L.run(wB3, ohlc, rf, "next_close", FC), "b_gtaa_futures",
        "A2 (equal risk per class) x SMA long-or-flat filter, off slots in T-bills")
    wE1 = L.rp_decisions(ohlc, ex, ls, "fixed")
    add("E1_LS_SMA10_INSTR", L.run(wE1, ohlc, rf, "next_close", FC), "e_long_short_same_signal",
        "A1 x (+1 above SMA / -1 below): the long-short twin of B1 (B1 = 0.5 A1 + 0.5 E1 exactly, gross)")
    wE2 = L.rp_decisions(ohlc, ex, ls, "fixed", class_equal=True)
    add("E2_LS_SMA10_CLASS", L.run(wE2, ohlc, rf, "next_close", FC), "e_long_short_same_signal",
        "A2 x (+1/-1): long-short twin of B3")
    # added after the first run (post hoc, still judged on 2011-2024 only): the filter on the drift assets alone
    wB4 = L.rp_decisions(sub(ohlc, eqr), ex[eqr], on[eqr], "fixed")
    add("B4_GTAA_FUT_EQ_RATES_FIXED", L.run(wB4, sub(ohlc, eqr), rf, "next_close", FC), "post_hoc_b",
        "ADDED AFTER FIRST RUN: P2 (9 equity-index + Treasury futures, equal risk) x SMA long-or-flat filter")
    wE4 = L.rp_decisions(sub(ohlc, eqr), ex[eqr], ls[eqr], "fixed")
    add("E4_LS_SMA10_EQ_RATES", L.run(wE4, sub(ohlc, eqr), rf, "next_close", FC), "post_hoc_b",
        "ADDED AFTER FIRST RUN: long-short twin of B4")

    # ---------------- (c) 5-market futures GTAA mirroring S3
    for nm, sw, mode, desc in [
        ("C1_FUT5_GTAA_20", 0.20, "gtaa", "S3 on futures: ES, ZN, CL/GC/HG/ZC basket at 20% notional each when above SMA; "
                                          "EFA and VNQ slots have no future -> permanently T-bills"),
        ("C2_FUT5_GTAA_THIRDS", 1 / 3, "gtaa", "same 3 sleeves at 1/3 notional each"),
        ("C3_FUT5_BH_20", 0.20, "bh", "buy-and-hold twin of C1 (20/20/20, 40% T-bills)"),
        ("C4_FUT5_BH_THIRDS", 1 / 3, "bh", "buy-and-hold twin of C2"),
        ("C5_FUT5_LS_20", 0.20, "ls", "long-short twin of C1 (+-20% per sleeve)"),
    ]:
        w = L.fut5_decisions(close, sw, mode)
        add(nm, L.run(w, sub(ohlc, L.FUT5_TICKERS), rf, "next_close", FC), "c_fut5", desc)

    # ---------------- ETF bridges (S3 and relatives)
    eo = E.load_ohlc(F.S3_TICKERS, "FWD")
    e_close = eo["close"]
    w_s3 = F.s3_decisions("FWD")
    w_s3_mine = L.etf_decisions(e_close, 0.20, "gtaa")
    chk_s3 = float((w_s3 - w_s3_mine.reindex_like(w_s3)).abs().max().max())
    add("ETF_S3", L.run(w_s3, eo, rf, "next_open", ETF_COST), "etf_bridge", "frozen S3 (Faber GTAA, 5 ETFs)", "etf")
    add("ETF_BH5", L.run(F.s3_decisions("FWD", buy_and_hold=True), eo, rf, "next_open", ETF_COST), "etf_bridge",
        "frozen BH5 (20% each, daily rebalanced)", "etf")
    add("ETF_LS5", L.run(L.etf_decisions(e_close, 0.20, "ls"), eo, rf, "next_open", ETF_COST), "etf_bridge",
        "long-short twin of S3 (+-20% per ETF, shorts pay 30 bp/yr borrow)", "etf")
    e3 = ["SPY", "IEF", "DBC"]
    eo3 = sub(eo, e3)
    add("ETF_S3_3SLEEVE_20", L.run(L.etf_decisions(e_close[e3], 0.20, "gtaa"), eo3, rf, "next_open", ETF_COST),
        "etf_bridge", "S3 rule on SPY/IEF/DBC only at 20% each (ETF analogue of C1)", "etf")
    add("ETF_S3_3SLEEVE_THIRDS", L.run(L.etf_decisions(e_close[e3], 1 / 3, "gtaa"), eo3, rf, "next_open", ETF_COST),
        "etf_bridge", "S3 rule on SPY/IEF/DBC at 1/3 each (ETF analogue of C2)", "etf")

    # ---------------- (d) long-short trend references
    w_s1 = F.s1_decisions("FWD")
    rS1 = L.run(w_s1, ohlc, rf, "next_close", FC)
    chk_s1 = float((rS1["net"] - F.returns("S1", "FWD")).abs().max())
    add("D1_S1_LS_SIGN_TREND", rS1, "d_long_short",
        "frozen forward-test-2 S1: sign of 21/63/252-day returns, 0.40/sigma/N, 10% ex-ante vol, monthly")
    from src.strategies import pct
    p = {k: v for k, v in pct.BASE_PARAMS.items() if k != "cost_mult"}
    p.update({"measure": "none", "tickers": FW.FUT_TICKERS})
    w_ts = pct.decision_weights(period="FWD", **p)
    rTS = L.run(w_ts, E.load_ohlc(FW.FUT_TICKERS, "FWD"), rf, "next_close", FW.FUT_COST_BPS)
    chk_ts = float((rTS["net"] - FW.returns("TSMOM_F", "FWD")).abs().max())
    add("D2_TSMOM_F", rTS, "d_long_short", "frozen forward-test-1 TSMOM_F benchmark (20 futures)")
    add("REF_ES_10VOL", L.run(F.es_sleeve_decisions("FWD"), sub(ohlc, ["F_ES"]), rf, "next_close", FC),
        "drift_benchmark", "frozen ES_10VOL: long ES at 10% ex-ante vol, monthly")

    ew = L.Ewmac(ohlc, rf, ex)
    ew_w = {}
    for tag, floor0 in (("LS", False), ("LF", True)):
        slow = ew.weights(L.EWMAC_SLOW, 0.20, True, floor0)
        fast = ew.weights(L.EWMAC_FAST, 0.25, False, floor0)
        combo = 0.7 * slow + 0.3 * fast
        ew_w[tag] = combo
        what = "long-short" if tag == "LS" else "long-or-flat (combined forecast floored at 0)"
        add(f"D_EWMAC_SLOW_{tag}", L.run(slow, ohlc, rf, "next_close", FC), "d_ewmac",
            f"trade-ngin TREND_FOLLOWING-style EWMAC, 6 speeds, 20% risk target, buffered, daily, {what}")
        add(f"D_EWMAC_FAST_{tag}", L.run(fast, ohlc, rf, "next_close", FC), "d_ewmac",
            f"trade-ngin TREND_FOLLOWING_FAST-style EWMAC, 5 speeds, 25% risk target, unbuffered, daily, {what}")
        add(f"D_EWMAC_7030_{tag}", L.run(combo, ohlc, rf, "next_close", FC), "d_ewmac",
            f"trade-ngin BASE_PORTFOLIO-style 70% slow + 30% fast, {what}")

    # return-level mix: 'long-or-flat S1' proxy
    a, d = V["A1_RP_LONG_INSTR"]["res"], V["D1_S1_LS_SIGN_TREND"]["res"]
    mix = {"net": 0.5 * a["net"] + 0.5 * d["net"], "gross": 0.5 * a["gross"] + 0.5 * d["gross"],
           "turnover": 0.5 * (a["turnover"] + d["turnover"]), "held": 0.5 * (a["held"] + d["held"])}
    add("MIX_50A1_50S1", mix, "mix", "daily 50/50 mix of A1 and S1 returns (a long-or-flat version of S1 at the "
        "return level; turnover shown is an upper bound)")

    # ---------------- diagnostics: trade-ngin's backtest fills at the close of the signal bar
    for base, w, o in [("B1_GTAA_FUT_INSTR_FIXED", wB1, ohlc), ("D1_S1_LS_SIGN_TREND", w_s1, ohlc),
                       ("D_EWMAC_7030_LS", ew_w["LS"], ohlc), ("D_EWMAC_7030_LF", ew_w["LF"], ohlc),
                       ("C1_FUT5_GTAA_20", L.fut5_decisions(close, 0.20, "gtaa"), sub(ohlc, L.FUT5_TICKERS))]:
        add(f"DIAG_SAMECLOSE_{base}", L.run(w.shift(-1), o, rf, "next_close", FC), "diagnostic_lookahead",
            "NOT TRADEABLE: decision filled at the close that produced it (trade-ngin backtest convention); "
            "measures how much that convention flatters " + base, eligible=False)

    # ---------------- stats table
    rows = []
    for nm, v in V.items():
        wins = [("IS_2011_2024", L.IS_WIN), ("OOS_2024_2026", L.OOS_WIN)]
        if v["kind"] == "etf":
            wins.append(("ETF_IS_2005_2024", L.ETF_IS_WIN))
        for wl, win in wins:
            st = L.window_stats(v["res"], rf, win)
            rows.append({"variant": nm, "family": v["family"], "eligible": v["eligible"], "window": wl, **st,
                         "description": v["desc"]})
    tab = pd.DataFrame(rows)
    tab.to_csv(L.OUT / "variants_full.csv", index=False)
    daily = {}
    for nm, v in V.items():
        daily[(nm, "net")] = v["res"]["net"]
        daily[(nm, "gross")] = v["res"]["gross"]
    daily = pd.DataFrame(daily)
    daily[("rf", "rf")] = rf.reindex(daily.index).ffill().fillna(0.0)
    daily.columns = [f"{a}|{b}" for a, b in daily.columns]
    daily.to_parquet(L.OUT / "daily_returns.parquet")
    pd.DataFrame([{"variant": n, "family": v["family"], "kind": v["kind"], "eligible": v["eligible"],
                   "description": v["desc"]} for n, v in V.items()]).to_csv(L.OUT / "variant_list.csv", index=False)

    # ---------------- identities (gross excess, IS window)
    def gx(nm, win=L.IS_WIN):
        r = V[nm]["res"]
        sl = slice(*map(pd.Timestamp, win))
        return (r["gross"] - rf.reindex(r["gross"].index).ffill().fillna(0)).loc[sl]

    ident = {
        "B1_minus_half_A1_plus_E1_max_abs_daily": float((gx("B1_GTAA_FUT_INSTR_FIXED") - 0.5 * (gx("A1_RP_LONG_INSTR") + gx("E1_LS_SMA10_INSTR"))).abs().max()),
        "C1_minus_half_C3_plus_C5_max_abs_daily": float((gx("C1_FUT5_GTAA_20") - 0.5 * (gx("C3_FUT5_BH_20") + gx("C5_FUT5_LS_20"))).abs().max()),
        "S3_minus_half_BH5_plus_LS5_max_abs_daily_2005_2024": float((gx("ETF_S3", L.ETF_IS_WIN) - 0.5 * (gx("ETF_BH5", L.ETF_IS_WIN) + gx("ETF_LS5", L.ETF_IS_WIN))).abs().max()),
        "A1_equals_forward2_LONG_ONLY_F_weights_max_abs": chk_lo,
        "S3_rebuild_equals_frozen_weights_max_abs": chk_s3,
        "S1_rebuild_equals_frozen_returns_max_abs": chk_s1,
        "TSMOM_F_rebuild_equals_frozen_returns_max_abs": chk_ts,
        "eligible_instruments_without_valid_SMA": miss,
    }

    # ---------------- drift / timing decomposition
    dec_rows = []
    fut_groups = {t: L.BROAD[L.CLASS_OF[t]] for t in T30}
    for nm in ["A1_RP_LONG_INSTR", "A2_RP_LONG_CLASS", "B1_GTAA_FUT_INSTR_FIXED", "B2_GTAA_FUT_INSTR_RESCALE",
               "B3_GTAA_FUT_CLASS_FIXED", "E1_LS_SMA10_INSTR", "D1_S1_LS_SIGN_TREND", "D_EWMAC_7030_LS",
               "D_EWMAC_7030_LF", "C1_FUT5_GTAA_20", "C2_FUT5_GTAA_THIRDS", "C3_FUT5_BH_20", "C5_FUT5_LS_20",
               "P2_RP_LONG_EQ_RATES", "B4_GTAA_FUT_EQ_RATES_FIXED", "E4_LS_SMA10_EQ_RATES"]:
        h = V[nm]["res"]["held"]
        for wl, win in (("IS_2011_2024", L.IS_WIN), ("OOS_2024_2026", L.OOS_WIN)):
            g = L.drift_timing(h, ex, fut_groups, win)
            for grp, r in g.iterrows():
                dec_rows.append({"variant": nm, "window": wl, "group": grp, **r.to_dict()})
    e_ex = e_close.pct_change(fill_method=None).sub(rf.reindex(e_close.index).ffill().fillna(0), axis=0)
    for nm in ["ETF_S3", "ETF_BH5", "ETF_LS5"]:
        h = V[nm]["res"]["held"]
        for wl, win in (("IS_2011_2024", L.IS_WIN), ("ETF_IS_2005_2024", L.ETF_IS_WIN), ("OOS_2024_2026", L.OOS_WIN)):
            g = L.drift_timing(h, e_ex, L.ETF_BROAD, win)
            for grp, r in g.iterrows():
                dec_rows.append({"variant": nm, "window": wl, "group": grp, **r.to_dict()})
    dec = pd.DataFrame(dec_rows)
    dec.to_csv(L.OUT / "drift_timing_decomposition.csv", index=False)

    # ---------------- bootstrap (IS window, paired, 63- and 21-day blocks)
    def xret(nm):
        r = V[nm]["res"]["net"]
        return r - rf.reindex(r.index).ffill().fillna(0)

    elig = [n for n, v in V.items() if v["eligible"]]
    pairs = [
        ("B1_GTAA_FUT_INSTR_FIXED", "D1_S1_LS_SIGN_TREND"),
        ("B1_GTAA_FUT_INSTR_FIXED", "A1_RP_LONG_INSTR"),
        ("B1_GTAA_FUT_INSTR_FIXED", "E1_LS_SMA10_INSTR"),
        ("B2_GTAA_FUT_INSTR_RESCALE", "D1_S1_LS_SIGN_TREND"),
        ("B3_GTAA_FUT_CLASS_FIXED", "D1_S1_LS_SIGN_TREND"),
        ("B1_GTAA_FUT_INSTR_FIXED", "P2_RP_LONG_EQ_RATES"),
        ("C1_FUT5_GTAA_20", "D1_S1_LS_SIGN_TREND"),
        ("C1_FUT5_GTAA_20", "C3_FUT5_BH_20"),
        ("C1_FUT5_GTAA_20", "ETF_S3_3SLEEVE_20"),
        ("C1_FUT5_GTAA_20", "ETF_S3"),
        ("C1_FUT5_GTAA_20", "B1_GTAA_FUT_INSTR_FIXED"),
        ("ETF_S3", "ETF_LS5"),
        ("ETF_S3", "ETF_BH5"),
        ("ETF_S3", "D1_S1_LS_SIGN_TREND"),
        ("D_EWMAC_7030_LF", "D_EWMAC_7030_LS"),
        ("D_EWMAC_SLOW_LF", "D_EWMAC_SLOW_LS"),
        ("D_EWMAC_7030_LF", "B1_GTAA_FUT_INSTR_FIXED"),
        ("MIX_50A1_50S1", "D1_S1_LS_SIGN_TREND"),
        ("B1_GTAA_FUT_INSTR_FIXED", "REF_ES_10VOL"),
        ("B4_GTAA_FUT_EQ_RATES_FIXED", "P2_RP_LONG_EQ_RATES"),
        ("B4_GTAA_FUT_EQ_RATES_FIXED", "E4_LS_SMA10_EQ_RATES"),
        ("B4_GTAA_FUT_EQ_RATES_FIXED", "D1_S1_LS_SIGN_TREND"),
    ]
    boot_rows = []
    for wl, win in (("IS_2011_2024", L.IS_WIN), ("OOS_2024_2026", L.OOS_WIN), ("ETF_IS_2005_2024", L.ETF_IS_WIN)):
        if wl == "ETF_IS_2005_2024":
            names = ["ETF_S3", "ETF_BH5", "ETF_LS5", "ETF_S3_3SLEEVE_20"]
            prs = [("ETF_S3", "ETF_LS5"), ("ETF_S3", "ETF_BH5"), ("ETF_BH5", "ETF_LS5")]
        else:
            names, prs = elig, pairs
        X = pd.DataFrame({n: xret(n) for n in names}).loc[win[0]:win[1]].dropna()
        for Lb in (63, 21):
            S = L.block_bootstrap_sharpes(X, L=Lb, B=2000, seed=11)
            point = X.mean() / X.std() * math.sqrt(252)
            col = {n: i for i, n in enumerate(X.columns)}
            for a_, b_ in prs:
                dlt = S[:, col[a_]] - S[:, col[b_]]
                boot_rows.append({"window": wl, "block": Lb, "a": a_, "b": b_,
                                  "sr_a": float(point[a_]), "sr_b": float(point[b_]),
                                  "diff": float(point[a_] - point[b_]), "boot_se": float(dlt.std()),
                                  "ci95_lo": float(np.percentile(dlt, 2.5)), "ci95_hi": float(np.percentile(dlt, 97.5)),
                                  "p_diff_le_0": float((dlt <= 0).mean())})
            for n in X.columns:
                boot_rows.append({"window": wl, "block": Lb, "a": n, "b": "(single)", "sr_a": float(point[n]),
                                  "sr_b": float("nan"), "diff": float(point[n]), "boot_se": float(S[:, col[n]].std()),
                                  "ci95_lo": float(np.percentile(S[:, col[n]], 2.5)),
                                  "ci95_hi": float(np.percentile(S[:, col[n]], 97.5)),
                                  "p_diff_le_0": float((S[:, col[n]] <= 0).mean())})
    boot = pd.DataFrame(boot_rows)
    boot.to_csv(L.OUT / "bootstrap.csv", index=False)

    # ---------------- yearly excess returns
    key = ["A1_RP_LONG_INSTR", "B1_GTAA_FUT_INSTR_FIXED", "E1_LS_SMA10_INSTR", "D1_S1_LS_SIGN_TREND",
           "D_EWMAC_7030_LS", "D_EWMAC_7030_LF", "C1_FUT5_GTAA_20", "C3_FUT5_BH_20", "P2_RP_LONG_EQ_RATES",
           "B4_GTAA_FUT_EQ_RATES_FIXED", "REF_ES_10VOL", "ETF_S3", "ETF_BH5", "ETF_LS5"]
    yr = {}
    for n in key:
        x = xret(n).loc["2005-11-01":L.OOS_WIN[1]]
        if V[n]["kind"] == "futures":
            x = x.loc[L.IS_WIN[0]:]
        yr[n] = (1 + x).groupby(x.index.year).prod() - 1
    yearly = pd.DataFrame(yr)
    yearly.to_csv(L.OUT / "yearly_excess_returns.csv")

    # ---------------- regimes (IS window, monthly)
    me_x = {n: (1 + xret(n).loc[L.IS_WIN[0]:L.IS_WIN[1]]).resample("ME").prod() - 1 for n in key if V[n]["kind"] == "futures" or True}
    M = pd.DataFrame(me_x).dropna(how="all")
    es_m = (1 + ex["F_ES"].fillna(0)).resample("ME").prod() - 1
    zn_m = (1 + ex["F_ZN"].fillna(0)).resample("ME").prod() - 1
    com_m = (1 + ex[[t for t in T30 if L.BROAD[L.CLASS_OF[t]] == "commodities"]].fillna(0).mean(axis=1)).resample("ME").prod() - 1
    es12 = (1 + es_m).rolling(12).apply(np.prod, raw=True).shift(1) - 1     # known at the start of the month
    zn12 = (1 + zn_m).rolling(12).apply(np.prod, raw=True).shift(1) - 1
    com12 = (1 + com_m).rolling(12).apply(np.prod, raw=True).shift(1) - 1
    states = {
        "ES_month_up": es_m > 0, "ES_month_down": es_m <= 0,
        "ES_month_worst10pct": es_m <= es_m.loc[M.index].quantile(0.10),
        "ES_trailing12m_up": es12 > 0, "ES_trailing12m_down": es12 <= 0,
        "ZN_trailing12m_up": zn12 > 0, "ZN_trailing12m_down": zn12 <= 0,
        "COMM_trailing12m_up": com12 > 0, "COMM_trailing12m_down": com12 <= 0,
        "ES_and_ZN_month_both_down": (es_m <= 0) & (zn_m <= 0),
    }
    reg_rows = []
    for sname, mask in states.items():
        m = mask.reindex(M.index).fillna(False).astype(bool)
        for n in M.columns:
            x = M.loc[m, n].dropna()
            reg_rows.append({"state": sname, "n_months": int(m.sum()), "variant": n,
                             "mean_monthly_excess_ann": float(x.mean() * 12),
                             "hit_rate": float((x > 0).mean()) if len(x) else float("nan")})
    regimes = pd.DataFrame(reg_rows)
    regimes.to_csv(L.OUT / "regimes_IS.csv", index=False)

    # ETF long window regimes incl. 2008 (S3 vs BH5 vs LS5)
    xE = pd.DataFrame({n: xret(n) for n in ["ETF_S3", "ETF_BH5", "ETF_LS5"]}).loc[L.ETF_IS_WIN[0]:L.ETF_IS_WIN[1]]
    ME = (1 + xE).resample("ME").prod() - 1
    spy_x = e_ex["SPY"].loc[L.ETF_IS_WIN[0]:L.ETF_IS_WIN[1]]
    spy_m = (1 + spy_x.fillna(0)).resample("ME").prod() - 1
    spy12 = (1 + spy_m).rolling(12).apply(np.prod, raw=True).shift(1) - 1
    reg2 = []
    for sname, mask in {"SPY_trailing12m_up": spy12 > 0, "SPY_trailing12m_down": spy12 <= 0,
                        "SPY_month_up": spy_m > 0, "SPY_month_down": spy_m <= 0}.items():
        m = mask.reindex(ME.index).fillna(False).astype(bool)
        for n in ME.columns:
            reg2.append({"state": sname, "n_months": int(m.sum()), "variant": n,
                         "mean_monthly_excess_ann": float(ME.loc[m, n].mean() * 12)})
    pd.DataFrame(reg2).to_csv(L.OUT / "regimes_ETF_2005_2024.csv", index=False)

    # ---------------- regressions (IS, daily, HAC)
    fx = pd.DataFrame({"ES": ex["F_ES"], "ZN": ex["F_ZN"]})
    regs = {}
    regs["B1_on_A1_E1"] = E.factor_regression(xret("B1_GTAA_FUT_INSTR_FIXED").loc[L.IS_WIN[0]:L.IS_WIN[1]],
                                              pd.DataFrame({"A1": xret("A1_RP_LONG_INSTR"), "E1": xret("E1_LS_SMA10_INSTR")}))
    regs["B1_on_A1_S1"] = E.factor_regression(xret("B1_GTAA_FUT_INSTR_FIXED").loc[L.IS_WIN[0]:L.IS_WIN[1]],
                                              pd.DataFrame({"A1": xret("A1_RP_LONG_INSTR"), "S1": xret("D1_S1_LS_SIGN_TREND")}))
    for n in ["B1_GTAA_FUT_INSTR_FIXED", "C1_FUT5_GTAA_20", "D1_S1_LS_SIGN_TREND", "E1_LS_SMA10_INSTR",
              "A1_RP_LONG_INSTR", "D_EWMAC_7030_LS", "D_EWMAC_7030_LF", "ETF_S3"]:
        regs[f"{n}_on_ES_ZN"] = E.factor_regression(xret(n).loc[L.IS_WIN[0]:L.IS_WIN[1]], fx)
    regs["C1_on_ES_ZN_COM"] = E.factor_regression(
        xret("C1_FUT5_GTAA_20").loc[L.IS_WIN[0]:L.IS_WIN[1]],
        pd.DataFrame({"ES": ex["F_ES"], "ZN": ex["F_ZN"], "COM": ex[L.FUT5_COM].mean(axis=1)}))
    regs["ETF_S3_on_ES_ZN_DBC_EFA_VNQ"] = E.factor_regression(
        xret("ETF_S3").loc[L.IS_WIN[0]:L.IS_WIN[1]], e_ex[["SPY", "EFA", "IEF", "VNQ", "DBC"]])

    # monthly correlation (IS)
    corr = M.corr()
    corr.to_csv(L.OUT / "monthly_corr_IS.csv")

    summary = {"n_variants": len(V), "n_eligible": len(elig), "identities": ident, "regressions": regs}
    (L.OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=float))

    pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_rows", 200)
    show = tab[["variant", "window", "sharpe", "sharpe_se", "sharpe_gross", "ann_return", "ann_excess", "ann_vol",
                "max_dd", "turnover_yr", "avg_gross_exp", "avg_net_exp"]]
    print(show.round(3).to_string(index=False))
    print(json.dumps(ident, indent=1))


if __name__ == "__main__":
    main()
