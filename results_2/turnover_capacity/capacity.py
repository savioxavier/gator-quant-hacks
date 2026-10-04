"""Item 7: turnover labels, a daily-volume screen built from the actual v2 trades, and risk controls.

Reads committed derived artifacts only: no prices, no asset return series, no strategy rerun. Run from the repository
root:

    python results_2/turnover_capacity/capacity.py

Writes turnover_labels.csv, trade_size_screen.csv and TURNOVER_CAPACITY.md into results_2/turnover_capacity/ and
nothing else. Exits with status 2 if an input is missing and 3 if a cross-check against the committed metrics fails.
No random numbers are drawn.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path("results_2/turnover_capacity")
IN = {
    "t4_daily": Path("backtests/results/v2_oos/run/daily_T4xE1_full.parquet"),
    "port_daily": Path("backtests/results/v2_oos/run/daily_portfolio_full.parquet"),
    "oos_metrics": Path("backtests/results/v2_oos/metrics.csv"),
    "is_windows": Path("backtests/results/v2/windows_all.csv"),
    "d4_daily": Path("backtests/results/v2_d4/daily_returns.parquet"),
    "d4_metrics": Path("backtests/results/v2_d4/metrics.csv"),
    "capacity": Path("backtests/results/capacity/capacity_stats.csv"),
    "rp_table": Path("archive/session_outputs/edges/risk_premia/out/futures_table.csv"),
    "cal_table": Path("archive/session_outputs/edges/calendar/variants_table.csv"),
    "existing_meta": Path("archive/session_outputs/edges/combine/existing_meta.json"),
    "port_table": Path("archive/session_outputs/edges/combine/portfolio_table.csv"),
    "existing": Path("backtests/v2/inputs/work/edges/combine/existing.parquet"),
    "existing_gross": Path("backtests/v2/inputs/work/edges/combine/existing_gross.parquet"),
    "ser_rpm": Path("backtests/v2/inputs/work/edges/series/rpm_ES_MM.parquet"),
    "ser_cal": Path("backtests/v2/inputs/work/edges/series/CAL_TSY_ME_ZN.parquet"),
    "ser_port": Path("backtests/v2/inputs/work/edges/series/PORT_core_ER_6.parquet"),
}
WINDOWS = {"selection": ("2016-01-04", "2020-12-31"), "validation": ("2021-01-04", "2024-10-02"),
           "full_is": ("2016-01-04", "2024-10-02"), "oos": ("2024-10-03", "2026-10-02")}
SCREEN_WINDOWS = ("oos", "full_is")
VARIANTS = ("original", "fix1", "fix2", "both")
ANN = 252
CAPITALS = (10.0, 50.0, 100.0)          # USD m
GROSS_CAP, W_RATE, W_FX = 1.5, 0.75, 0.25   # preregistration/HYPOTHESIS_v2.md (Variant A sizing)
TOL = 1e-9
EPS = 1e-12


def fail(code: int, msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def check(ok: bool, msg: str) -> None:
    if not ok:
        fail(3, f"cross-check failed: {msg}")


def per_year(turn: pd.Series, idx: pd.DatetimeIndex) -> float:
    return float(turn.reindex(idx).fillna(0.0).sum() / (len(idx) / ANN))


def win_index(s: pd.Series, w: str) -> pd.DatetimeIndex:
    a, b = WINDOWS[w]
    return s.loc[a:b].dropna().index


def stats(x: pd.Series) -> dict:
    v = x.dropna().to_numpy(float)
    if len(v) == 0:
        return {"n_obs": 0}
    return {"n_obs": int(len(v)), "median": float(np.percentile(v, 50)), "p90": float(np.percentile(v, 90)),
            "p99": float(np.percentile(v, 99)), "max": float(v.max()), "mean": float(v.mean())}


def main() -> None:
    missing = [p.as_posix() for p in IN.values() if not p.exists()]
    if missing:
        fail(2, "missing inputs (run from the repository root):\n  " + "\n  ".join(missing))
    OUT.mkdir(parents=True, exist_ok=True)

    t4 = pd.read_parquet(IN["t4_daily"])
    port = pd.read_parquet(IN["port_daily"])
    d4 = pd.read_parquet(IN["d4_daily"])
    for df in (t4, port, d4):
        df.index = pd.to_datetime(df.index)
    m4 = pd.read_csv(IN["d4_metrics"])
    moos = pd.read_csv(IN["oos_metrics"])
    mis = pd.read_csv(IN["is_windows"])
    cap = pd.read_csv(IN["capacity"])

    def d4row(group, series, variant, window):
        r = m4[(m4.group == group) & (m4.series == series) & (m4.variant == variant) & (m4.window == window)]
        check(len(r) == 1, f"one metrics.csv row for {group}/{series}/{variant}/{window}")
        return r.iloc[0]

    # the committed original daily turnover in the D-3 run equals the D-4 file's 'original' column
    j = pd.concat([t4["turnover"], d4["T4xE1|original|turnover"]], axis=1, join="inner")
    check(float((j.iloc[:, 0] - j.iloc[:, 1]).abs().max()) <= TOL, "D-3 and D-4 original daily turnover agree")

    labels = []

    def lab(**k):
        labels.append(k)

    src_d4 = IN["d4_metrics"].as_posix()
    src_d4d = IN["d4_daily"].as_posix()

    # ------------------------------------------------------------------ (a1) v2 instrument turnover
    for v in VARIANTS:
        for w in WINDOWS:
            idx = win_index(d4[f"T4xE1|{v}|net_1x"], w)
            re = per_year(d4[f"T4xE1|{v}|turnover"], idx)
            r = d4row("strategy", "T4xE1", v, w)
            check(int(r.n_days) == len(idx), f"T4xE1 {v} {w} n_days")
            check(abs(re - r.turnover_per_year) <= TOL, f"T4xE1 {v} {w} turnover recompute")
            lab(quantity="v2_instrument_turnover", series="T4xE1", variant=v, window=w, start=r.start, end=r.end,
                n_days=int(r.n_days), value=r.turnover_per_year, unit="x v2 NAV per year (one-way)",
                status="measured", recomputed_from_daily=re, abs_diff=abs(re - r.turnover_per_year),
                source=f"{src_d4} turnover_per_year; daily {src_d4d} T4xE1|{v}|turnover",
                definition=("sum over TLT and UUP of |weight after the open trade - weight held before it|, "
                            "summed over the window's sessions and divided by years (sessions/252); "
                            "standalone v2 strategy, its own NAV"))
    # frozen original records (first reported results)
    for w in ("selection", "validation", "full_is"):
        r = mis[(mis.combo == "T4xE1") & (mis.window == w)].iloc[0]
        ref = d4row("strategy", "T4xE1", "original", w)
        check(abs(r.turnover_per_year - ref.turnover_per_year) <= TOL, f"frozen IS record {w} equals D-4 original")
        lab(quantity="v2_instrument_turnover", series="T4xE1", variant="original_frozen_record", window=w,
            start=r.start, end=r.end, n_days=int(r.n_days), value=r.turnover_per_year,
            unit="x v2 NAV per year (one-way)", status="measured (frozen first record)", recomputed_from_daily=np.nan,
            abs_diff=abs(r.turnover_per_year - ref.turnover_per_year), source=f"{IN['is_windows'].as_posix()} turnover_per_year",
            definition="as above; the committed in-sample record, unchanged")
    r = moos[(moos.series == "T4xE1") & (moos.window == "oos") & (moos.basis == "net_1x")].iloc[0]
    ref = d4row("strategy", "T4xE1", "original", "oos")
    check(abs(r.turnover_per_year - ref.turnover_per_year) <= TOL, "frozen OOS record equals D-4 original")
    lab(quantity="v2_instrument_turnover", series="T4xE1", variant="original_frozen_record", window="oos",
        start=r.start, end=r.end, n_days=int(r.n_days), value=r.turnover_per_year,
        unit="x v2 NAV per year (one-way)", status="measured (frozen first record)", recomputed_from_daily=np.nan,
        abs_diff=abs(r.turnover_per_year - ref.turnover_per_year), source=f"{IN['oos_metrics'].as_posix()} turnover_per_year",
        definition="as above; the committed D-3 out-of-sample record, unchanged")

    # ------------------------------------------------------------------ (a2) per-leg split, original path
    w_tlt, w_uup = t4["w_rate"], t4["w_fx"]
    dw = pd.DataFrame({"TLT": w_tlt.diff().fillna(w_tlt.abs()).abs(), "UUP": w_uup.diff().fillna(w_uup.abs()).abs()})
    for w in WINDOWS:
        idx = win_index(d4["T4xE1|original|net_1x"], w)
        yrs = len(idx) / ANN
        legs = {k: float(dw[k].reindex(idx).sum() / yrs) for k in ("TLT", "UUP")}
        tot = per_year(t4["turnover"], idx)
        a, b = str(idx[0].date()), str(idx[-1].date())
        for k in ("TLT", "UUP"):
            lab(quantity=f"v2_leg_target_change_turnover_{k}", series="T4xE1", variant="original", window=w, start=a,
                end=b, n_days=len(idx), value=legs[k], unit="x v2 NAV per year (one-way)",
                status="measured from committed held weights (target-to-target)", recomputed_from_daily=legs[k],
                abs_diff=np.nan, source=f"{IN['t4_daily'].as_posix()} w_rate / w_fx",
                definition=(f"sum of |change in the {k} weight held after the open trade| / years; excludes the "
                            "engine's daily rebalancing of overnight drift back to target (not split by leg in any "
                            "committed file)"))
        lab(quantity="v2_drift_rebalance_residual", series="T4xE1", variant="original", window=w, start=a, end=b,
            n_days=len(idx), value=tot - legs["TLT"] - legs["UUP"], unit="x v2 NAV per year (one-way)",
            status="derived residual", recomputed_from_daily=np.nan, abs_diff=np.nan,
            source=f"{IN['t4_daily'].as_posix()} turnover - (TLT + UUP target changes)",
            definition=("engine one-way turnover minus the two legs' target-to-target changes: the net effect of "
                        "rebalancing overnight drift (both legs combined; can be offset by drift towards target)"))

    # ------------------------------------------------------------------ (a3) portfolio overlay and v2 sleeve
    m_fed = port["core_ER_6+T4xE1|m_FED_T4xE1"]
    for series, variants in (("core_ER_6", ("as_committed",)), ("core_ER_6+T4xE1", VARIANTS)):
        for v in variants:
            for w in WINDOWS:
                idx = win_index(d4[f"{series}|{v}|net_1x"], w)
                re = per_year(d4[f"{series}|{v}|turnover"], idx)
                r = d4row("portfolio", series, v, w)
                check(int(r.n_days) == len(idx), f"{series} {v} {w} n_days")
                check(abs(re - r.turnover_per_year) <= TOL, f"{series} {v} {w} overlay turnover recompute")
                lab(quantity="portfolio_overlay_turnover", series=series, variant=v, window=w, start=r.start,
                    end=r.end, n_days=int(r.n_days), value=r.turnover_per_year,
                    unit="x portfolio NAV per year (one-way)", status="measured (overlay only)",
                    recomputed_from_daily=re, abs_diff=abs(re - r.turnover_per_year),
                    source=f"{src_d4} turnover_per_year; daily {src_d4d} {series}|{v}|turnover",
                    definition=("sum over sleeves of |change in sleeve multiplier| x sleeve instrument gross "
                                "(combine.build); counts only multiplier changes, NOT the trading inside any sleeve; "
                                "not total portfolio turnover"))
                if series == "core_ER_6":
                    continue
                fed = float(r.fed_sleeve_turnover_per_year)
                if v == "original":
                    re_f = per_year(m_fed * t4["turnover"], idx)
                    check(abs(re_f - fed) <= TOL, f"fed sleeve turnover recompute {w}")
                    note = ("m_FED (committed daily multiplier) x T4xE1 daily turnover; recomputed exactly")
                    ad = abs(re_f - fed)
                else:
                    re_f = per_year(m_fed * d4[f"T4xE1|{v}|turnover"], idx)
                    note = ("daily multipliers of the corrected portfolio are not committed; the recompute uses the "
                            "original multipliers with this variant's daily turnover (approximate check only)")
                    ad = abs(re_f - fed)
                lab(quantity="v2_sleeve_internal_turnover_in_portfolio", series=series, variant=v, window=w,
                    start=r.start, end=r.end, n_days=int(r.n_days), value=fed,
                    unit="x portfolio NAV per year (one-way)", status="measured (v2 sleeve only)",
                    recomputed_from_daily=re_f, abs_diff=ad,
                    source=f"{src_d4} fed_sleeve_turnover_per_year; {note}",
                    definition=("v2 sleeve multiplier m_t x the v2 strategy's own daily one-way turnover, summed / "
                                "years: the v2 sleeve's weighted internal trading inside core_ER_6+T4xE1; excludes "
                                "the three core sleeves' internal trading"))
                lab(quantity="overlay_plus_v2_sleeve_partial", series=series, variant=v, window=w, start=r.start,
                    end=r.end, n_days=int(r.n_days), value=float(r.turnover_per_year) + fed,
                    unit="x portfolio NAV per year (one-way)", status="partial sum, not total portfolio turnover",
                    recomputed_from_daily=np.nan, abs_diff=np.nan, source=src_d4,
                    definition=("overlay turnover + v2 sleeve internal turnover, added without netting; still excludes "
                                "the core sleeves' internal trading, so it is not the portfolio's turnover"))

    # ------------------------------------------------------------------ (a4) core sleeves
    rp = pd.read_csv(IN["rp_table"])
    for wn, wl in (("IS", "edges_is"), ("LATER", "later (= v2 oos dates)")):
        r = rp[(rp.name == "rpm_ES_MM") & (rp.window == wn)].iloc[0]
        lab(quantity="core_sleeve_standalone_turnover", series="rpm_ES_MM", variant="as_committed", window=wl,
            start=r.start, end=r.end, n_days=np.nan, value=float(r.turnover_per_year),
            unit="x sleeve's own NAV per year (one-way)", status="committed summary (standalone)",
            recomputed_from_daily=np.nan, abs_diff=np.nan, source=f"{IN['rp_table'].as_posix()} turnover_per_year",
            definition=("equity sleeve (long F_ES, Moreira-Muir vol timing) traded alone at its own 10% vol "
                        "target; no daily trade or turnover series is committed"))
    cal = pd.read_csv(IN["cal_table"])
    for wn, wl in (("IS", "edges_is"), ("later", "later (= v2 oos dates)")):
        r = cal[(cal.candidate == "CAL_TSY_ME_ZN") & (cal.variant == "base_T-2..T") & (cal.scaling == "10vol")
                & (cal.cost == "net_1x") & (cal.window == wn)].iloc[0]
        lab(quantity="core_sleeve_standalone_turnover", series="CAL_TSY_ME_ZN", variant="as_committed", window=wl,
            start=r.start, end=r.end, n_days=np.nan, value=float(r.turnover_per_year),
            unit="x sleeve's own NAV per year (one-way)", status="committed summary (standalone)",
            recomputed_from_daily=np.nan, abs_diff=np.nan, source=f"{IN['cal_table'].as_posix()} turnover_per_year",
            definition=("Treasury month-end sleeve (long ZN16 over days T-2..T at up to 5x leverage, 10% vol "
                        "scaling) traded alone; no daily trade or turnover series is committed"))
    meta = json.loads(IN["existing_meta"].read_text())
    lab(quantity="core_sleeve_standalone_turnover", series="S1", variant="as_committed",
        window="whole engine run (not split)", start=meta["S1"]["start"], end="2026-10-02", n_days=np.nan,
        value=float(meta["S1"]["turnover"]), unit="x sleeve's own NAV per year (one-way)",
        status="committed summary (standalone; window not split)", recomputed_from_daily=np.nan, abs_diff=np.nan,
        source=f"{IN['existing_meta'].as_posix()} S1.turnover",
        definition=("trend sleeve S1 at its native 10% ex-ante vol; engine turnover summed over the whole simulated "
                    "calendar divided by its length in years (includes sessions before the first decision), so it "
                    "is not comparable window by window; no daily trade series is committed"))
    pt = pd.read_csv(IN["port_table"])
    r = pt[(pt.portfolio == "core_ER_6") & (pt.window == "IS")].iloc[0]
    mm = json.loads(r.mean_mult)
    std_is = {"rpm_ES_MM": float(rp[(rp.name == "rpm_ES_MM") & (rp.window == "IS")].turnover_per_year.iloc[0]),
              "CAL_TSY_ME_ZN": float(cal[(cal.candidate == "CAL_TSY_ME_ZN") & (cal.variant == "base_T-2..T")
                                         & (cal.scaling == "10vol") & (cal.cost == "net_1x")
                                         & (cal.window == "IS")].turnover_per_year.iloc[0]),
              "S1": float(meta["S1"]["turnover"])}
    ind_total = 0.0
    for n, t in std_is.items():
        val = float(mm[n]) * t
        ind_total += val
        lab(quantity="core_sleeve_internal_turnover_in_portfolio", series=n, variant="as_committed",
            window="edges_is", start=r.start, end=r.end, n_days=np.nan, value=val,
            unit="x portfolio NAV per year (one-way)", status="indicative only, not measured",
            recomputed_from_daily=np.nan, abs_diff=np.nan,
            source=f"{IN['port_table'].as_posix()} mean_mult ({mm[n]}) x standalone turnover above",
            definition=("in-sample mean multiplier x standalone in-sample turnover: an order of magnitude, not a "
                        "measurement (mean of a product is not the product of means; windows differ; no netting of "
                        "ZN trades across sleeves); the daily multipliers and trades of the core sleeves are not "
                        "committed"))
    lab(quantity="core_sleeve_internal_turnover_in_portfolio", series="core sleeves, sum", variant="as_committed",
        window="edges_is", start=r.start, end=r.end, n_days=np.nan, value=ind_total,
        unit="x portfolio NAV per year (one-way)", status="indicative only, not measured",
        recomputed_from_daily=np.nan, abs_diff=np.nan, source="sum of the three indicative rows",
        definition="as above, summed without netting")
    # scan the committed sleeve series for any trade / weight / turnover column
    cols = set()
    for k in ("ser_rpm", "ser_cal", "ser_port", "existing"):
        c = pd.read_parquet(IN[k]).columns
        cols |= {str(x[-1] if isinstance(x, tuple) else x) for x in c}
    trade_cols = sorted(c for c in cols if any(s in c.lower() for s in ("turn", "trade", "weight", "w_", "pos")))
    gross_cols = list(pd.read_parquet(IN["existing_gross"]).columns)
    for q, d_ in (("core_sleeve_internal_turnover_in_portfolio", "measured daily core-sleeve trading inside "
                   "core_ER_6"), ("total_portfolio_turnover", "total turnover of core_ER_6 or core_ER_6+T4xE1 "
                                  "(overlay + every sleeve's internal trading, netted by instrument)")):
        lab(quantity=q, series="core_ER_6 / core_ER_6+T4xE1", variant="all", window="all", start="", end="",
            n_days=np.nan, value=np.nan, unit="", status="unavailable", recomputed_from_daily=np.nan,
            abs_diff=np.nan,
            source=("committed core-sleeve series carry only columns " + ", ".join(sorted(cols)) +
                    f"; trade/turnover/weight columns found: {trade_cols or 'none'}; existing_gross.parquet holds "
                    f"held instrument gross (holdings, not trades) for {', '.join(gross_cols)}"),
            definition=d_ + ": needs each sleeve's daily instrument weights (or trades) and the daily multipliers")

    lab_df = pd.DataFrame(labels)
    lab_df.to_csv(OUT / "turnover_labels.csv", index=False, float_format="%.10g")

    # ------------------------------------------------------------------ (b) trade-size screen
    def mddv(inst: str) -> float:
        r = cap[cap["item"].str.startswith(f"{inst} median daily dollar volume")]
        check(len(r) == 1 and r.iloc[0].unit == "USD m", f"median daily dollar volume for {inst}")
        return float(r.iloc[0].value)
    MDDV = {"TLT": mddv("TLT"), "UUP": mddv("UUP")}
    MDDV_N = int(cap[cap["item"].str.startswith("TLT median daily dollar volume")].n_days.iloc[0])
    # registered-cap reference reproduces the committed capacity rows
    for inst, w_ in (("TLT", W_RATE), ("UUP", W_FX)):
        r = cap[cap["item"].str.startswith(f"{inst} largest E1 position")]
        check(abs(round(100 * GROSS_CAP * w_ * 10 / MDDV[inst], 2) - float(r.iloc[0].value)) <= 0.011,
              f"registered-cap holding vs capacity_stats for {inst}")

    sgn = np.sign(w_tlt)
    flip = (sgn != sgn.shift(1)) & (sgn != 0) & (sgn.shift(1) != 0)
    chg = dw.sum(axis=1) > EPS
    rows = []

    def add(path, window, instrument, quantity, basis, x, label, capital_basis="v2 strategy NAV", single=False):
        st = {"n_obs": 1, "value": float(x.iloc[0])} if single else stats(x)
        for k in (("value",) if single else ("median", "p90", "p99", "max", "mean")):
            if k not in st:
                continue
            v = st[k]
            row = {"path": path, "window": window, "start": WINDOWS[window][0], "end": WINDOWS[window][1],
                   "instrument": instrument, "quantity": quantity, "days": basis, "n_obs": st["n_obs"],
                   "statistic": k, "share_of_nav": v, "capital_basis": capital_basis}
            for c in CAPITALS:
                row[f"usd_m_at_{int(c)}m"] = v * c
            for c in CAPITALS:
                ok = window == "oos" and instrument in MDDV
                row[f"pct_median_daily_volume_at_{int(c)}m"] = 100 * v * c / MDDV[instrument] if ok else np.nan
            row["label"] = label
            rows.append(row)

    LBL = ("daily-volume screen: trade size vs the OOS median daily dollar volume of the ETF; NOT an opening-auction "
           "capacity estimate (E1 trades at the open)")
    for w in SCREEN_WINDOWS:
        idx = win_index(d4["T4xE1|original|net_1x"], w)
        ch, fl = chg.reindex(idx), flip.reindex(idx)
        for inst in ("TLT", "UUP"):
            x = dw[inst].reindex(idx)
            add("original_committed_weights", w, inst, "target_change_trade", "all sessions", x,
                LBL + "; zero on no-trade-band sessions; excludes drift rebalancing")
            add("original_committed_weights", w, inst, "target_change_trade", "target-change sessions", x[ch], LBL)
            add("original_committed_weights", w, inst, "reversal_trade", "sign-flip sessions", x[fl],
                LBL + "; sessions where the held position changes sign")
            hw = (w_tlt if inst == "TLT" else w_uup).abs().reindex(idx)
            add("original_committed_weights", w, inst, "holding_abs", "all sessions", hw,
                "holding (position size) vs daily volume: liquidity screen, not validated capacity")
        tv = t4["turnover"].reindex(idx)
        add("original_engine_total", w, "TLT+UUP", "engine_one_way_turnover", "all sessions", tv,
            "total of both legs; includes drift rebalancing; not comparable to one ETF's volume")
        add("original_engine_total", w, "TLT+UUP", "engine_one_way_turnover", "no-target-change sessions",
            tv[~ch], "drift rebalancing only (target unchanged inside the no-trade band)")
        add("original_engine_total", w, "TLT+UUP", "engine_one_way_turnover", "sign-flip sessions", tv[fl],
            "total of both legs on reversal sessions")
        t4b = d4["T4xE1|both|turnover"].reindex(idx)
        add("d4_both_engine_total", w, "TLT+UUP", "engine_one_way_turnover", "all sessions", t4b,
            "corrected path (both D-4 fixes); total of both legs; per-leg split not committed")
        add("d4_both_engine_total", w, "TLT+UUP", "engine_one_way_turnover", "sign-flip sessions", t4b[fl],
            "corrected path on the original path's sign-flip sessions (the fixes do not change the signal's sign)")
        for inst, share in (("TLT", W_RATE), ("UUP", W_FX)):
            add("d4_both_split_estimate", w, inst, "estimated_leg_trade", "all sessions", share * t4b,
                LBL + f"; ESTIMATE: {share:.2f} x corrected total (exact 75/25 for target changes outside FOMC "
                "sessions; the drift part's split is unknown)")
            add("d4_both_split_estimate", w, inst, "estimated_leg_trade", "sign-flip sessions", share * t4b[fl],
                LBL + f"; ESTIMATE: {share:.2f} x corrected total")
            add("d4_both_upper_bound", w, inst, "upper_bound_leg_trade", "all sessions", t4b,
                LBL + "; UPPER BOUND: the whole corrected total assigned to this leg")
            add("d4_both_upper_bound", w, inst, "upper_bound_leg_trade", "sign-flip sessions", t4b[fl],
                LBL + "; UPPER BOUND")
    # portfolio context: the v2 sleeve inside core_ER_6+T4xE1 (original multipliers), OOS
    idx = win_index(port["core_ER_6+T4xE1|net_1x"], "oos")
    mo = m_fed.reindex(idx).fillna(0.0)
    for inst in ("TLT", "UUP"):
        x = dw[inst].reindex(idx) * mo
        add("portfolio_context_original_m", "oos", inst, "target_change_trade", "target-change sessions",
            x[chg.reindex(idx)], LBL + "; v2 sleeve trade x its multiplier m_FED, as a share of PORTFOLIO NAV",
            capital_basis="core_ER_6+T4xE1 portfolio NAV")
        add("portfolio_context_original_m", "oos", inst, "reversal_trade", "sign-flip sessions",
            x[flip.reindex(idx)], LBL + "; share of PORTFOLIO NAV", capital_basis="core_ER_6+T4xE1 portfolio NAV")
        hw = (w_tlt if inst == "TLT" else w_uup).abs().reindex(idx) * mo
        add("portfolio_context_original_m", "oos", inst, "holding_abs", "all sessions", hw,
            "holding vs daily volume, share of PORTFOLIO NAV: liquidity screen",
            capital_basis="core_ER_6+T4xE1 portfolio NAV")
    # registered cap (largest possible holding) as a reference row
    for inst, w_ in (("TLT", W_RATE), ("UUP", W_FX)):
        add("registered_cap_reference", "oos", inst, "max_holding_at_gross_cap", "-",
            pd.Series([GROSS_CAP * w_]), "registered maximum holding (gross cap 1.5 x leg weight); as in "
            "backtests/results/capacity/capacity_stats.csv", single=True)
    scr = pd.DataFrame(rows)
    check(not scr.duplicated(subset=["path", "window", "instrument", "quantity", "days", "statistic"]).any(),
          "screen rows are unique")
    scr.to_csv(OUT / "trade_size_screen.csv", index=False, float_format="%.10g")

    # ------------------------------------------------------------------ figures used in the write-up
    def L(q, s, v, w):
        r = lab_df[(lab_df.quantity == q) & (lab_df.series == s) & (lab_df.variant == v) & (lab_df.window == w)]
        check(len(r) == 1, f"label row {q}/{s}/{v}/{w}")
        return float(r.value.iloc[0])

    def S(path, w, inst, q, days, stat, col="share_of_nav"):
        r = scr[(scr.path == path) & (scr.window == w) & (scr.instrument == inst) & (scr.quantity == q)
                & (scr.days == days) & (scr.statistic == stat)]
        check(len(r) == 1, f"screen row {path}/{w}/{inst}/{q}/{days}/{stat}")
        return float(r[col].iloc[0])

    def N(path, w, inst, q, days):
        r = scr[(scr.path == path) & (scr.window == w) & (scr.instrument == inst) & (scr.quantity == q)
                & (scr.days == days)]
        return int(r.n_obs.iloc[0])

    oos_idx = win_index(d4["T4xE1|original|net_1x"], "oos")
    nav = (1 + t4["net"].reindex(oos_idx)).cumprod()
    nav_lo, nav_hi = float(min(1.0, nav.min())), float(nav.max())
    top_uup = dw["UUP"].reindex(oos_idx).nlargest(5)
    n_top_flip = int(flip.reindex(top_uup.index).sum())
    big_flip = t4["turnover"].reindex(oos_idx)[flip.reindex(oos_idx)].idxmax()
    big_trade = t4["turnover"].reindex(oos_idx).idxmax()
    big_trade_d4 = d4["T4xE1|both|turnover"].reindex(oos_idx).idxmax()
    big_trade_d4_flip = bool(flip.get(big_trade_d4, False))
    # UUP share of the two legs' target changes (original path, OOS target-change sessions)
    ch_oos = chg.reindex(oos_idx)
    share_uup = (dw["UUP"] / dw.sum(axis=1)).reindex(oos_idx)[ch_oos]
    n_share_exact = int((share_uup - W_FX).abs().le(1e-9).sum())
    # the 0.25 x total estimate, tried on the original path where the UUP leg is known
    est_o = W_FX * t4["turnover"].reindex(oos_idx)
    act_o = dw["UUP"].reindex(oos_idx)
    est_chk = {k: (float(np.percentile(est_o, q)), float(np.percentile(act_o, q))) for k, q in
               (("p90", 90), ("p99", 99))}
    est_chk["max"] = (float(est_o.max()), float(act_o.max()))
    # capital at which a trade equals a given share of the median UUP day (illustrative thresholds)
    THRESH = (0.01, 0.05, 0.10, 0.25)
    n_flip_oos = int(flip.reindex(oos_idx).sum())
    n_flip_is = int(flip.reindex(win_index(d4["T4xE1|original|net_1x"], "full_is")).sum())
    n_chg_oos = int(chg.reindex(oos_idx).sum())
    m_med = float(m_fed.reindex(idx).median())

    def pct(x, nd=2):
        return f"{100 * x:.{nd}f}%"

    def f(x, nd=2):
        return f"{x:,.{nd}f}"

    def mtab(rows_):
        return "\n".join("| " + " | ".join(r) + " |" for r in rows_)

    # table (a) summary
    ta = [["quantity", "what it counts", "scope / unit", "original OOS", "both fixes OOS", "original full IS",
           "both fixes full IS"], ["---"] * 7]
    ta.append(["v2 instrument turnover (T4xE1)", "both legs' one-way trades of the standalone v2 strategy",
               "x v2 NAV / yr", f(L("v2_instrument_turnover", "T4xE1", "original", "oos")),
               f(L("v2_instrument_turnover", "T4xE1", "both", "oos")),
               f(L("v2_instrument_turnover", "T4xE1", "original", "full_is")),
               f(L("v2_instrument_turnover", "T4xE1", "both", "full_is"))])
    for k in ("TLT", "UUP"):
        ta.append([f"  of which {k} target changes", "|change in held weight|, original path only",
                   "x v2 NAV / yr", f(L(f"v2_leg_target_change_turnover_{k}", "T4xE1", "original", "oos")), "n/a",
                   f(L(f"v2_leg_target_change_turnover_{k}", "T4xE1", "original", "full_is")), "n/a"])
    ta.append(["  of which drift rebalancing (residual)", "total minus the two legs' target changes",
               "x v2 NAV / yr", f(L("v2_drift_rebalance_residual", "T4xE1", "original", "oos")), "n/a",
               f(L("v2_drift_rebalance_residual", "T4xE1", "original", "full_is")), "n/a"])
    ta.append(["portfolio overlay turnover, core_ER_6+T4xE1", "multiplier changes x sleeve gross only",
               "x portfolio NAV / yr", f(L("portfolio_overlay_turnover", "core_ER_6+T4xE1", "original", "oos"), 3),
               f(L("portfolio_overlay_turnover", "core_ER_6+T4xE1", "both", "oos"), 3),
               f(L("portfolio_overlay_turnover", "core_ER_6+T4xE1", "original", "full_is"), 3),
               f(L("portfolio_overlay_turnover", "core_ER_6+T4xE1", "both", "full_is"), 3)])
    ta.append(["portfolio overlay turnover, core_ER_6 alone", "multiplier changes x sleeve gross only",
               "x portfolio NAV / yr", f(L("portfolio_overlay_turnover", "core_ER_6", "as_committed", "oos"), 3),
               "(same series)", f(L("portfolio_overlay_turnover", "core_ER_6", "as_committed", "full_is"), 3),
               "(same series)"])
    ta.append(["v2 sleeve internal turnover inside core_ER_6+T4xE1", "m_FED x v2 daily turnover",
               "x portfolio NAV / yr",
               f(L("v2_sleeve_internal_turnover_in_portfolio", "core_ER_6+T4xE1", "original", "oos"), 3),
               f(L("v2_sleeve_internal_turnover_in_portfolio", "core_ER_6+T4xE1", "both", "oos"), 3),
               f(L("v2_sleeve_internal_turnover_in_portfolio", "core_ER_6+T4xE1", "original", "full_is"), 3),
               f(L("v2_sleeve_internal_turnover_in_portfolio", "core_ER_6+T4xE1", "both", "full_is"), 3)])
    ta.append(["core sleeves' internal turnover inside the portfolio", "daily trades of rpm_ES_MM, CAL_TSY_ME_ZN, S1",
               "x portfolio NAV / yr", "unavailable", "unavailable", "unavailable", "unavailable"])
    ta.append(["total portfolio turnover", "overlay + all sleeves' trading, netted", "x portfolio NAV / yr",
               "unavailable", "unavailable", "unavailable", "unavailable"])

    tcore = [["core sleeve (standalone, own NAV)", "edges in-sample", "later (2024-10-03..2026-10-02)",
              "indicative weight in portfolio (IS mean multiplier x IS turnover)"], ["---"] * 4]
    for n in ("rpm_ES_MM", "CAL_TSY_ME_ZN"):
        tcore.append([n, f(L("core_sleeve_standalone_turnover", n, "as_committed", "edges_is")),
                      f(L("core_sleeve_standalone_turnover", n, "as_committed", "later (= v2 oos dates)")),
                      f(L("core_sleeve_internal_turnover_in_portfolio", n, "as_committed", "edges_is"))])
    tcore.append(["S1", f"{f(L('core_sleeve_standalone_turnover', 'S1', 'as_committed', 'whole engine run (not split)'))}"
                  " (whole run, not split)", "not committed",
                  f(L("core_sleeve_internal_turnover_in_portfolio", "S1", "as_committed", "edges_is"))])
    tcore.append(["sum (no netting)", "", "", f(ind_total)])

    # table (b) screen, OOS, original committed weights
    tb = [["leg, OOS", "trade", "sessions", "share of v2 NAV", "$10m", "$50m", "$100m", "% med. day $10m",
           "% med. day $50m", "% med. day $100m"], ["---"] * 10]
    P = "original_committed_weights"
    for inst in ("TLT", "UUP"):
        for q, days, nm in (("target_change_trade", "target-change sessions", "target change"),
                            ("reversal_trade", "sign-flip sessions", "reversal")):
            for st in ("median", "p90", "p99", "max"):
                if q == "reversal_trade" and st in ("p90", "p99"):
                    continue
                tb.append([inst, f"{nm}, {st}", str(N(P, "oos", inst, q, days)), pct(S(P, "oos", inst, q, days, st)),
                           f"${S(P, 'oos', inst, q, days, st, 'usd_m_at_10m'):.2f}m",
                           f"${S(P, 'oos', inst, q, days, st, 'usd_m_at_50m'):.2f}m",
                           f"${S(P, 'oos', inst, q, days, st, 'usd_m_at_100m'):.2f}m",
                           pct(S(P, "oos", inst, q, days, st, "pct_median_daily_volume_at_10m") / 100),
                           pct(S(P, "oos", inst, q, days, st, "pct_median_daily_volume_at_50m") / 100),
                           pct(S(P, "oos", inst, q, days, st, "pct_median_daily_volume_at_100m") / 100)])
        tb.append([inst, "holding, max", str(N(P, "oos", inst, "holding_abs", "all sessions")),
                   pct(S(P, "oos", inst, "holding_abs", "all sessions", "max")),
                   f"${S(P, 'oos', inst, 'holding_abs', 'all sessions', 'max', 'usd_m_at_10m'):.2f}m",
                   f"${S(P, 'oos', inst, 'holding_abs', 'all sessions', 'max', 'usd_m_at_50m'):.2f}m",
                   f"${S(P, 'oos', inst, 'holding_abs', 'all sessions', 'max', 'usd_m_at_100m'):.2f}m",
                   pct(S(P, "oos", inst, "holding_abs", "all sessions", "max", "pct_median_daily_volume_at_10m") / 100),
                   pct(S(P, "oos", inst, "holding_abs", "all sessions", "max", "pct_median_daily_volume_at_50m") / 100),
                   pct(S(P, "oos", inst, "holding_abs", "all sessions", "max", "pct_median_daily_volume_at_100m") / 100)])

    tc = [["series, OOS", "sessions", "median", "p90", "p99", "max"], ["---"] * 6]
    for path, days, nm in (("original_engine_total", "all sessions", "original, engine total"),
                           ("original_engine_total", "no-target-change sessions", "original, drift-only sessions"),
                           ("d4_both_engine_total", "all sessions", "both fixes, engine total"),
                           ("d4_both_engine_total", "sign-flip sessions", "both fixes, reversal sessions")):
        tc.append([nm, str(N(path, "oos", "TLT+UUP", "engine_one_way_turnover", days))] +
                  [pct(S(path, "oos", "TLT+UUP", "engine_one_way_turnover", days, st)) for st in
                   ("median", "p90", "p99", "max")])
    td = [["both fixes, UUP leg, OOS", "sessions", "share of v2 NAV", "% med. day $10m", "% med. day $50m",
           "% med. day $100m"], ["---"] * 6]
    for path, q, nm in (("d4_both_split_estimate", "estimated_leg_trade", "estimate (0.25 x total)"),
                        ("d4_both_upper_bound", "upper_bound_leg_trade", "upper bound (whole total)")):
        for days in ("all sessions", "sign-flip sessions"):
            for st in ("p99", "max"):
                td.append([f"{nm}, {st}", days, pct(S(path, "oos", "UUP", q, days, st)),
                           pct(S(path, "oos", "UUP", q, days, st, "pct_median_daily_volume_at_10m") / 100),
                           pct(S(path, "oos", "UUP", q, days, st, "pct_median_daily_volume_at_50m") / 100),
                           pct(S(path, "oos", "UUP", q, days, st, "pct_median_daily_volume_at_100m") / 100)])
    PC = "portfolio_context_original_m"
    te = [["v2 leg inside core_ER_6+T4xE1, OOS", "share of portfolio NAV", "% med. day $10m", "% med. day $50m",
           "% med. day $100m"], ["---"] * 5]
    for inst in ("TLT", "UUP"):
        for q, days, nm in (("target_change_trade", "target-change sessions", "target change, max"),
                            ("reversal_trade", "sign-flip sessions", "reversal, max"),
                            ("holding_abs", "all sessions", "holding, max")):
            te.append([f"{inst} {nm}", pct(S(PC, "oos", inst, q, days, "max")),
                       pct(S(PC, "oos", inst, q, days, "max", "pct_median_daily_volume_at_10m") / 100),
                       pct(S(PC, "oos", inst, q, days, "max", "pct_median_daily_volume_at_50m") / 100),
                       pct(S(PC, "oos", inst, q, days, "max", "pct_median_daily_volume_at_100m") / 100)])

    uup_max = S(P, "oos", "UUP", "target_change_trade", "target-change sessions", "max")
    uup_p99 = S(P, "oos", "UUP", "target_change_trade", "target-change sessions", "p99")
    uup_med = S(P, "oos", "UUP", "target_change_trade", "target-change sessions", "median")
    tlt_max = S(P, "oos", "TLT", "target_change_trade", "target-change sessions", "max")
    is_uup_max = S(P, "full_is", "UUP", "target_change_trade", "target-change sessions", "max")
    is_tlt_max = S(P, "full_is", "TLT", "target_change_trade", "target-change sessions", "max")
    capk = {c: 100 * uup_max * c / MDDV["UUP"] for c in CAPITALS}
    top_txt = ", ".join(f"{d.date()} {pct(v)}{' (reversal)' if bool(flip.get(d, False)) else ''}"
                        for d, v in top_uup.items())
    d4_rev_max = S("d4_both_engine_total", "oos", "TLT+UUP", "engine_one_way_turnover", "sign-flip sessions", "max")
    d4_all_max = S("d4_both_engine_total", "oos", "TLT+UUP", "engine_one_way_turnover", "all sessions", "max")
    o_all_max = S("original_engine_total", "oos", "TLT+UUP", "engine_one_way_turnover", "all sessions", "max")
    if big_trade == big_trade_d4 == big_flip and big_trade_d4_flip:
        busiest = (f"The busiest OOS session on both paths was the reversal of {big_trade.date()}: "
                   f"{pct(o_all_max)} of NAV traded across both legs (original), {pct(d4_all_max)} (corrected).")
    else:
        busiest = (f"The busiest OOS session was {big_trade.date()} on the original path ({pct(o_all_max)} of NAV) and "
                   f"{big_trade_d4.date()} on the corrected path ({pct(d4_all_max)}, "
                   f"{'a reversal' if big_trade_d4_flip else 'not a reversal'}); the largest original-path reversal "
                   f"session was {big_flip.date()} and the largest corrected-path reversal traded {pct(d4_rev_max)}.")
    tt = [["trade (UUP leg, original path, OOS)", "share of v2 NAV"] +
          [f"capital at which it is {int(100 * t)}% of a median UUP day" for t in THRESH], ["---"] * (2 + len(THRESH))]
    for nm, v in (("median target change", uup_med), ("p99 target change", uup_p99), ("largest trade", uup_max),
                  ("largest holding", S(P, "oos", "UUP", "holding_abs", "all sessions", "max"))):
        tt.append([nm, pct(v)] + [f"${t * MDDV['UUP'] / v:,.1f}m" for t in THRESH])
    tchk = [["original path, UUP leg, OOS, all sessions", "0.25 x engine total (the estimate)",
             "actual target change"], ["---"] * 3]
    for k in ("p90", "p99", "max"):
        tchk.append([k, pct(est_chk[k][0]), pct(est_chk[k][1])])

    risk = [["control", "status", "where", "what it does / what it does not do"], ["---"] * 4,
            ["z clip at +/-2", "implemented, registered", "v2lib.size (POS_CLIP)", "caps signal-driven position size"],
            ["10% vol target, blended 20/60-day vol, 4% vol floor", "implemented, registered", "v2lib.size, "
             "blended_vol", "scales the unit hawkish mix; floor limits leverage in calm markets"],
            ["gross cap 1.5x (at most 112.5% NAV in TLT, 37.5% in UUP)", "implemented, registered", "v2lib.size "
             "(GROSS_CAP)", "hard limit on holdings; binding in the OOS window (held TLT reached "
             f"{pct(S(P, 'oos', 'TLT', 'holding_abs', 'all sessions', 'max'), 1)}, UUP "
             f"{pct(S(P, 'oos', 'UUP', 'holding_abs', 'all sessions', 'max'), 1)}); limits holdings, not trade size"],
            ["10% relative no-trade band; forced trades on FOMC session, the session after, and from flat",
             "implemented, registered", "v2lib.size (NO_TRADE_BAND)", "skips small target changes; the engine "
             "still rebalances drift every session (charged)"],
            ["rates leg halved over each FOMC announcement session (8 unscheduled actions included, D-1)",
             "implemented, registered", "v2lib.size (FOMC_RATE_MULT)", "event-risk haircut; not a stop"],
            ["next-session execution; vol for sizing known before the close of t-1 (D-4 fix 1)",
             "implemented (fix 1 is a D-4 implementation correction)", "v2lib.weights_E1, run_v2_d4.py",
             "removes look-ahead; not a risk limit"],
            ["costs 1.5 bp TLT / 5 bp UUP one-way, 30 bp/yr borrow on shorts; 2x cost gate in the decision rule",
             "implemented, registered", "v2lib.EXPRS, engine", "flat cost model: no market impact, no "
             "auction-size dependence, no borrow availability"],
            ["portfolio: equal risk, 6% target vol, 252-day covariance, month-end decisions applied d+2, "
             "leverage cap 4 on summed sleeve gross", "implemented", "combine.build", "portfolio-level sizing; "
             "multiplier changes are the only portfolio trades counted (overlay turnover)"],
            ["drawdown stop / de-risking rule", "proposed, not implemented, not pre-registered", "-",
             "none exists (report, Section 6); would need registration before any live use"],
            ["live monitoring rule (signal decay, tracking vs backtest)", "proposed, not implemented", "-",
             "none exists; v2 failed its decision rule and is not deployed"],
            ["participation cap per trade (share of opening-auction / first-minutes volume), trade splitting "
             "over sessions", "proposed, not implemented", "-", "needs opening-auction and quote data (not in "
             "the repository); would change fills and costs, so it needs a new registered test"],
            ["UUP notional limit or futures expression (E2: ZN and 6E)", "proposed, not implemented", "-",
             "E2 was not chosen and has no OOS row"],
            ["reversal throttling (stage sign flips over several opens)", "proposed, not implemented", "-",
             f"the largest OOS trading session on the corrected path ({big_trade_d4.date()}, {pct(d4_all_max, 1)} of "
             f"NAV) {'was' if big_trade_d4_flip else 'was not'} a reversal; staging changes the strategy"],
            ["borrow availability / recall check for short TLT and UUP", "proposed, not implemented", "-",
             "the backtest assumes 30 bp/yr and unlimited borrow"]]

    sel = (lab_df.quantity == "v2_sleeve_internal_turnover_in_portfolio") & (lab_df.variant != "original")
    approx_max = float(lab_df.loc[sel, "abs_diff"].max())
    o_oos = L("v2_instrument_turnover", "T4xE1", "original", "oos")
    b_oos = L("v2_instrument_turnover", "T4xE1", "both", "oos")
    ov_b = L("portfolio_overlay_turnover", "core_ER_6+T4xE1", "both", "oos")
    fed_b = L("v2_sleeve_internal_turnover_in_portfolio", "core_ER_6+T4xE1", "both", "oos")
    fed_o = L("v2_sleeve_internal_turnover_in_portfolio", "core_ER_6+T4xE1", "original", "oos")

    md = f"""# Turnover and capacity (item 7)

Descriptive. Every number comes from committed derived files (daily strategy returns, held weights, turnover and
multipliers; committed summary tables); no strategy is rerun and no price or asset return series is read or
written. Generated by `capacity.py` (run from the repository root: `python results_2/turnover_capacity/capacity.py`),
which also writes `turnover_labels.csv` and `trade_size_screen.csv`; it exits non-zero if an input is missing or a
recomputed turnover disagrees with the committed metrics. Every exactly recomputable figure (v2 instrument turnover,
overlay turnover, the original v2-sleeve turnover) agrees to within 1e-9; the corrected v2-sleeve figures can only be
checked approximately, because the corrected portfolio's daily multipliers are not committed (largest difference
{approx_max:.4f}x a year, using the original multipliers).

## Definitions (fixed in capacity.py)

- **Instrument turnover**: sum over instruments of |weight after the trade - weight held before it|, one-way, as a
  fraction of the NAV the weights refer to, summed over the window's sessions and divided by years (sessions/252).
  This is the engine's daily `turnover`, as in `backtests/v2/v2lib.py` (`window_stats`).
- **Overlay turnover** (`combine.build`): sum over sleeves of |change in sleeve multiplier| x that sleeve's
  instrument gross. It counts only multiplier changes, never the trading inside a sleeve.
- **v2 sleeve internal turnover inside the portfolio**: the v2 sleeve multiplier m_FED x the v2 strategy's own daily
  turnover (`fed_sleeve_turnover_per_year`).
- **Trade size (screen)**: for each leg, |change in the held weight| from one session to the next, using the committed
  held weights of T4xE1 (`w_rate` = TLT, `w_fx` = UUP after the open trade; original path). This is the
  target-to-target trade; the engine also trades overnight drift back to target every session (both legs, not split
  by leg in any committed file). Percentiles: linear interpolation (numpy default).
- **Reversal**: a session on which the held TLT position changes sign (both sessions non-zero; the UUP leg always has
  the opposite sign, so it flips on the same session). {n_flip_oos} in the OOS window, {n_flip_is} in full in-sample.
- **Dollars**: share of NAV x capital ($10m, $50m, $100m), with NAV held at the starting capital. Within the OOS window
  the T4xE1 total-return NAV (original path) ranged from {nav_lo:.3f} to {nav_hi:.3f} times its start, so actual dollar
  trades were between {nav_lo:.3f} and {nav_hi:.3f} times the figures shown.
- **Median daily dollar volume** (committed `backtests/results/capacity/capacity_stats.csv`, close x shares, OOS window
  2024-10-03..2026-10-02, {MDDV_N} sessions): TLT ${MDDV['TLT']:,.1f}m, UUP ${MDDV['UUP']:,.1f}m. Shares of it are given
  for the OOS window only.

## (a) Every turnover quantity, labelled

Full table (every variant and window, sources, recompute differences): `turnover_labels.csv`.

{mtab(ta)}

Windows: OOS 2024-10-03..2026-10-02 (501 sessions); full in-sample 2016-01-04..2024-10-02 (2,202). "original" is the
committed code path (identical to the frozen records in `backtests/results/v2/` and `backtests/results/v2_oos/`;
the CSV carries those frozen rows separately); "both fixes" is D-4 (`backtests/results/v2_d4/`).

How to read it:
- **{f(b_oos)}x (both fixes) / {f(o_oos)}x (original) is v2 instrument turnover**: the standalone v2 strategy's trades
  in TLT and UUP per year, as a multiple of v2's own NAV.
- **{f(ov_b, 3)}x is overlay-only turnover** of core_ER_6+T4xE1 (both fixes, OOS): it counts only month-end multiplier
  changes. It is not the portfolio's trading and must not be quoted as portfolio turnover.
- **{f(fed_b, 3)}x (both fixes; {f(fed_o, 3)}x original) is the v2 sleeve's weighted internal turnover inside the
  portfolio**: v2's own trading scaled by its multiplier (median {m_med:.3f} in the OOS window).
- **Core sleeves' internal turnover inside the portfolio is unavailable**: the committed core-sleeve series
  (`backtests/v2/inputs/work/edges/series/*.parquet`, `combine/existing.parquet`) carry only net_1x, net_2x and gross
  returns; `existing_gross.parquet` holds held gross (positions, not trades); no daily trades, weights or multipliers of
  the core sleeves are committed. So **total portfolio turnover is unavailable**. Committed standalone summaries
  exist and show that the core sleeves trade far more than the overlay suggests:

{mtab(tcore)}

The last column is an order of magnitude only (mean multiplier x mean turnover, mismatched windows, no netting of
ZN trades across sleeves); it is not a measurement and must not be quoted as portfolio turnover. It does show that the
overlay figure (0.3x to 0.6x a year) understates the portfolio's trading by about two orders of magnitude, mostly
through the Treasury month-end sleeve.

## (b) Trade sizes from the actual v2 trades: a daily-volume screen

Full distributions (all sessions, target-change sessions, reversals, holdings; OOS and full in-sample; original,
corrected totals, estimates and bounds; portfolio context): `trade_size_screen.csv`.

**Original path, committed held weights, OOS** ({n_chg_oos} of 501 sessions change the target):

{mtab(tb)}

**Engine totals (both legs, includes drift rebalancing), OOS, share of v2 NAV:**

{mtab(tc)}

The D-4 files commit only the corrected total turnover, not per-leg weights. Except on FOMC announcement sessions
and the session after (rates leg halved), the two legs' target changes split exactly 75/25, because both legs scale
with the same position x vol factor; in the original path the UUP share of target changes is exactly 0.25 on
{n_share_exact} of {n_chg_oos} OOS target-change sessions. So 0.25 x the corrected total estimates the UUP trade, and
the whole total is a hard upper bound. Sign-flip sessions are taken from the original weights: the fixes change the
vol scale (fix 1) and the holdings path (fix 2), not the signal, so the sign changes fall on the same sessions.

{mtab(td)}

The estimate, tried on the original path where the UUP leg is known:

{mtab(tchk)}

**Context: the v2 sleeve inside core_ER_6+T4xE1** (original multipliers m_FED, OOS; dollar columns refer to
portfolio capital):

{mtab(te)}

Reading:
- **TLT is not the constraint at these sizes.** The largest single TLT target change in the OOS window is
  {pct(tlt_max)} of NAV ({pct(is_tlt_max)} in full in-sample); even at $100m that is
  {pct(tlt_max * 100 / MDDV['TLT'])} of a median TLT day.
- **UUP is.** The median UUP target change is {pct(uup_med)} of NAV, p99 {pct(uup_p99)}, max {pct(uup_max)}
  ({pct(is_uup_max)} in full in-sample); the largest is {pct(capk[10.0] / 100)} of a median UUP day at $10m,
  {pct(capk[50.0] / 100)} at $50m and {pct(capk[100.0] / 100)} at $100m. Largest OOS UUP trades: {top_txt}
  ({n_top_flip} of the 5 on reversal sessions). {busiest}
- The report's "about $10m" capacity (Section 7) rests on the largest possible UUP holding at the gross cap
  (37.5% of NAV, 11.5% of a median UUP day at $10m). Holdings vs daily volume is a liquidity screen, not validated
  capacity; the trade-based screen above is the more relevant one, because every trade is executed at the open.

Capital at which a UUP trade of a given size reaches a given share of a median UUP day (original path, OOS; the
thresholds are illustrations, not validated participation limits, and a full day's volume overstates what is
available at the open):

{mtab(tt)}

**What this screen is not.** It compares trades with a full day's median dollar volume, but E1 trades at the open, so
the relevant liquidity is the opening auction and the first minutes of continuous trading, which are a fraction of
the day. It is therefore a daily-volume screen, not an opening-auction capacity estimate, and it says nothing about
market impact. The cost model (flat 1.5 bp TLT / 5 bp UUP) does not depend on size. To turn it into a capacity
estimate one would need: opening-auction volumes and imbalances for TLT and UUP on the trade sessions; NBBO quotes and
displayed depth for the first minutes after the open; intraday trade prints to estimate impact by participation rate;
borrow availability and recall history for short positions; and, for UUP, the ETF's creation/redemption capacity (or the
futures expression E2, which has no OOS row). None of these is in the repository.

## (c) Risk controls: implemented vs proposed

{mtab(risk)}

"Implemented" means present in the committed code and every reported backtest; "proposed" means not implemented, not
tested and not pre-registered. Nothing proposed here has been run.

## Files

| file | what |
|---|---|
| `capacity.py` | computes everything here from committed files; fails on a missing input or a failed cross-check |
| `turnover_labels.csv` | every turnover quantity: quantity, series, variant, window, dates, sessions, value, unit, status, source, recompute, definition |
| `trade_size_screen.csv` | trade-size and holding distributions (median, p90, p99, max, mean) as a share of NAV, in dollars at $10m/$50m/$100m and as % of the OOS median daily dollar volume |
"""
    (OUT / "TURNOVER_CAPACITY.md").write_text(md, encoding="utf-8")
    print(f"wrote {OUT / 'turnover_labels.csv'} ({len(lab_df)} rows), {OUT / 'trade_size_screen.csv'} "
          f"({len(scr)} rows), {OUT / 'TURNOVER_CAPACITY.md'}")


if __name__ == "__main__":
    main()
