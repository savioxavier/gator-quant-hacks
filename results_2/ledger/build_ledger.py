"""Variant ledger (reviewer item 5): every variant and comparison of the project, with its role and result.

Read-only: it reads committed result files and writes only results_2/ledger/VARIANT_LEDGER.csv and
results_2/ledger/trial_counts_by_scope.csv. It runs no backtest. Run it from the repository root:

    python results_2/ledger/build_ledger.py

It exits with status 2 when a committed input is missing or when it is started elsewhere.

The solo repository (github.com/minh-stakc/gqh-flow-clock) is not part of this repository. Its trial-log counts are
recorded below from results/trials.csv at commit 1587f25 (file sha256 5a57b85a...526c). If GQH_REPO points at a clone,
the script re-counts that file and stops if its hash differs; without GQH_REPO the recorded counts are used and the
output says so.

Roles (relative to the main strategy, v2 T4xE1):
  selection candidate            one of the 8 registered combinations the selection rule chose from
  prespecified robustness        registered before any v2 return (references, sensitivities, falsifiers, DSR,
                                 portfolio test, by-chair split)
  post-result diagnostic         decided after v2 results had been seen (D-3 out-of-sample opening, D-4 benchmarks,
                                 walk-forward, descriptive splits)
  implementation correction      a fix or a pipeline change (D-4 fixes, stance-model substitution, placebo pipeline
                                 tests, stage fixes)
  independent failed or exploratory study   any other family (press conference, strategy 01, edge study, solo
                                 repository, earlier screens)
`role_in_family` gives the row's role inside its own family (for example the press-conference gated primary).
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import hashlib
import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path.cwd()
OUT = ROOT / "results_2" / "ledger"

F = {
    "prereg_v2": "preregistration/HYPOTHESIS_v2.md",
    "dev_v2": "preregistration/DEVIATIONS.md",
    "d3": "preregistration/v2_DEVIATION_D3_OOS.md",
    "d4": "preregistration/v2_DEVIATION_D4_FIXES.md",
    "prereg_log": "preregistration/PREREG_LOG.md",
    "pc_plan": "preregistration/presser_team_FINAL_PLAN.md",
    "pc_addendum": "preregistration/presser_ADDENDUM.md",
    "pc_d1": "preregistration/presser_DEVIATION_D1.md",
    "h234": "preregistration/presser_H2H3H4_EXPLORATORY.md",
    "note1": "preregistration/presser_H2H3H4_NOTE1.md",
    "note2": "preregistration/presser_H2H3H4_NOTE2.md",
    "note3": "preregistration/presser_H2H3H4_NOTE3.md",
    "v2_windows": "backtests/results/v2/windows_all.csv",
    "v2_summary": "backtests/results/v2/summary_is.json",
    "v2_sens_is": "backtests/results/v2/sens_scheduled_only_is.csv",
    "v2_portfolio": "backtests/results/v2/portfolio.csv",
    "v2_chair_is": "backtests/results/v2/by_chair_is.csv",
    "v2_failed": "backtests/results/v2/oos_not_evaluated.json",
    "oos_metrics": "backtests/results/v2_oos/metrics.csv",
    "oos_sens": "backtests/results/v2_oos/run/sens_scheduled_only_oos.csv",
    "oos_chair": "backtests/results/v2_oos/run/by_chair_oos.csv",
    "oos_chosen": "backtests/results/v2_oos/run/oos_chosen.json",
    "oos_conc": "backtests/results/v2_oos/oos_concentration.csv",
    "d4_metrics": "backtests/results/v2_d4/metrics.csv",
    "d4_wf": "backtests/results/v2_d4/walk_forward_picks.csv",
    "d4_readme": "backtests/results/v2_d4/README.md",
    "pc_key": "backtests/results/presser_h1/key_results.json",
    "pc_long": "backtests/results/presser_h1/summary_long.csv",
    "pc_answer": "backtests/results/presser_h1/h1answer_summary.csv",
    "pc_sweep": "backtests/results/presser_h1/h1answer_1s_sweep_summary.csv",
    "pc_break": "backtests/results/presser_h1/benchr_break_stats.csv",
    "pc_strategy": "backtests/results/presser_strategy/metrics.csv",
    "h234_holm": "backtests/presser/backtest_h234/results/family_holm.json",
    "h234_h4": "backtests/presser/backtest_h234/results/h4_results.json",
    "h234_answers": "backtests/presser/backtest_h234/results/answer_summary.csv",
    "h234_slopes": "backtests/presser/backtest_h234/results/companion_slopes.csv",
    "h234_local": "docs/results/h234-local-summary.md",
    "s01_log": "strategies/01/trials/log.csv",
    "s01_log_v2": "backtests/v2/inputs/work/savio_gqh/strategies/01/trials/log.csv",
    "s01_hyp": "strategies/01/HYPOTHESIS.md",
    "s01_verdict": "strategies/01/review/VERDICT.md",
    "s01_predeclared": "strategies/01/review/analyse/PREDECLARED.md",
    "s01_t1": "strategies/01/review/analyse/t1_results_all.csv",
    "s01_t4": "strategies/01/review/analyse/t4_futures_summary.csv",
    "s01_t5": "strategies/01/review/analyse/t5_portfolio_test.csv",
    "e_carry_spec": "archive/session_outputs/edges/carry/SPEC.md",
    "e_carry": "archive/session_outputs/edges/carry/carry_all_variants.csv",
    "e_carry_sel": "archive/session_outputs/edges/carry/selection.json",
    "e_rp_spec": "archive/session_outputs/edges/risk_premia/SPEC.md",
    "e_rp": "archive/session_outputs/edges/risk_premia/out/all_variants.csv",
    "e_rp_verdicts": "archive/session_outputs/edges/risk_premia/out/verdicts.csv",
    "e_cal_spec": "archive/session_outputs/edges/calendar/SPEC.md",
    "e_cal": "archive/session_outputs/edges/calendar/variants_table.csv",
    "e_val_spec": "archive/session_outputs/edges/value_reversal/SPEC.md",
    "e_val": "archive/session_outputs/edges/value_reversal/value_reversal_table.csv",
    "e_comb_spec": "archive/session_outputs/edges/combine/SPEC.md",
    "e_comb": "archive/session_outputs/edges/combine/portfolio_table.csv",
    "e_comb_summary": "archive/session_outputs/edges/combine/summary.json",
    "solo_before": "archive/session_outputs/before/trials.csv",
    "solo_pct_before": "archive/session_outputs/pct_review/before/trials_before.csv",
    "hunt100": "archive/session_outputs/hunt100",
    "auction_spec": "archive/session_outputs/auction/futures_test/SPEC.md",
    "gtaa": "archive/session_outputs/gtaa_study",
    "intraday": "archive/session_outputs/intraday_study",
    "kit_native": "archive/session_outputs/kit_native",
    "placebo": "archive/session_outputs/placebo_chain",
    "report": "docs/report/REPORT.md",
}

# solo repository results/trials.csv at commit 1587f25 (counted on 2026-10-04 from the public repository)
SOLO = {
    "url": "github.com/minh-stakc/gqh-flow-clock",
    "commit": "1587f25",
    "file": "results/trials.csv",
    "sha256": "5a57b85ac7488aa6d5e3fc5eceebdadf4469c544c9aa72322834f50fa141526c",
    "rows": 3159, "names": 1479, "params_hashes": 1501, "is_rows": 3134, "oos_rows": 25,
    "families": {  # rows, distinct names, distinct parameter hashes, IS rows, OOS rows
        "FTE": (2890, 1405, 1404, 2888, 2),
        "IFC": (146, 35, 48, 138, 8),
        "IFC_EXPLORATORY": (20, 7, 8, 16, 4),
        "IFC_F": (13, 11, 13, 11, 2),
        "PCT": (75, 15, 19, 69, 6),
        "PCT_F": (15, 6, 9, 12, 3),
    },
}

OBS_V2_IS = ("market data and strategy 01's results over 2012..2024-10 had been seen; no v2 return existed when the rule "
             "was registered (19:52 UTC 2026-10-03); Amendments 2-3 followed strategy 01's out-of-sample verdict")
OBS_V2_OOS = ("window's market data had been seen (strategy 01 out-of-sample verdict committed 20:26 UTC 2026-10-03; edge "
              "study later window); v2's own out-of-sample returns were computed once, 01:23 UTC 2026-10-04 (D-3)")
OBS_POST = "yes: v2 in-sample (about 23:10 UTC 2026-10-03) and D-3 out-of-sample results had been seen"
OBS_D4 = "yes: written 05:30 UTC 2026-10-04 after the in-sample and D-3 out-of-sample results and two external reviews"
WIN_IS = "selection 2016-01-04..2020-12-31; validation 2021-01-04..2024-10-02; full IS 2016-01-04..2024-10-02"
WIN_OOS = "out-of-sample 2024-10-03..2026-10-02"
ROLE = ("selection candidate", "prespecified robustness", "post-result diagnostic", "implementation correction",
        "independent failed or exploratory study")


def die(msg: str) -> None:
    print(f"build_ledger: {msg}", file=sys.stderr)
    sys.exit(2)


def f3(x) -> str:
    return "nan" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.3f}"


def pct(x) -> str:
    return f"{100 * x:.2f}%"


def main() -> None:
    if not (ROOT / "backtests").is_dir() or not (ROOT / "preregistration").is_dir():
        die("run from the repository root (backtests/ and preregistration/ not found here)")
    P = {k: ROOT / v for k, v in F.items()}
    missing = [v for k, v in F.items() if not P[k].exists()]
    if missing:
        die("missing input(s): " + ", ".join(missing))

    # ---------------- solo repository: recorded counts, re-counted when a clone is given ----------------
    solo_note = "recorded from the public repository at commit 1587f25; not re-counted in this run (GQH_REPO not set)"
    if os.environ.get("GQH_REPO"):
        sp = Path(os.environ["GQH_REPO"]) / SOLO["file"]
        if not sp.exists():
            die(f"GQH_REPO is set but {SOLO['file']} is missing there")
        if hashlib.sha256(sp.read_bytes()).hexdigest() != SOLO["sha256"]:
            die("GQH_REPO results/trials.csv differs from the recorded commit-1587f25 file")
        st = pd.read_csv(sp)
        fam = st.groupby("family").agg(rows=("name", "size"), names=("name", "nunique"),
                                       hashes=("params_hash", "nunique"))
        for k, v in SOLO["families"].items():
            if (int(fam.at[k, "rows"]), int(fam.at[k, "names"]), int(fam.at[k, "hashes"])) != v[:3]:
                die(f"solo family {k} counts differ from the recorded ones")
        solo_note = "re-counted from GQH_REPO in this run; equal to the recorded commit-1587f25 counts"

    # ---------------- load ----------------
    W = pd.read_csv(P["v2_windows"])
    S = json.loads(P["v2_summary"].read_text(encoding="utf-8"))
    sens_is = pd.read_csv(P["v2_sens_is"])
    port = pd.read_csv(P["v2_portfolio"])
    chair_is = pd.read_csv(P["v2_chair_is"])
    om = pd.read_csv(P["oos_metrics"])
    sens_oos = pd.read_csv(P["oos_sens"])
    chair_oos = pd.read_csv(P["oos_chair"])
    conc = pd.read_csv(P["oos_conc"])
    d4 = pd.read_csv(P["d4_metrics"])
    wf = pd.read_csv(P["d4_wf"])
    key = json.loads(P["pc_key"].read_text(encoding="utf-8"))
    pl = pd.read_csv(P["pc_long"])
    pa = pd.read_csv(P["pc_answer"])
    ps = pd.read_csv(P["pc_sweep"])
    pst = pd.read_csv(P["pc_strategy"])
    holm = json.loads(P["h234_holm"].read_text(encoding="utf-8"))
    h4 = json.loads(P["h234_h4"].read_text(encoding="utf-8"))
    h2a = pd.read_csv(P["h234_answers"])
    slopes = pd.read_csv(P["h234_slopes"])
    s01 = pd.read_csv(P["s01_log"])
    # compared ignoring line endings: git stores strategies/01 with LF and the v2 inputs byte-identical (CRLF)
    if P["s01_log"].read_bytes().replace(b"\r\n", b"\n") != P["s01_log_v2"].read_bytes().replace(b"\r\n", b"\n"):
        die("strategy 01 trial log differs between strategies/01 and the v2 inputs")
    t1 = pd.read_csv(P["s01_t1"])
    carry = pd.read_csv(P["e_carry"])
    rp = pd.read_csv(P["e_rp"])
    rpv = pd.read_csv(P["e_rp_verdicts"])
    cal = pd.read_csv(P["e_cal"])
    val = pd.read_csv(P["e_val"])
    comb = pd.read_csv(P["e_comb"])
    combs = json.loads(P["e_comb_summary"].read_text(encoding="utf-8"))
    sb = pd.read_csv(P["solo_before"])
    spb = pd.read_csv(P["solo_pct_before"])

    def w(combo: str, window: str, col: str = "sharpe_net1x") -> float:
        r = W[(W.combo == combo) & (W.window == window)]
        if len(r) != 1:
            die(f"windows_all.csv: no unique row for {combo} {window}")
        return float(r[col].iloc[0])

    def win3(combo: str) -> str:
        return (f"Sharpe net 1x: selection {f3(w(combo, 'selection'))}, validation {f3(w(combo, 'validation'))}, "
                f"full IS {f3(w(combo, 'full_is'))}; full IS 2x {f3(w(combo, 'full_is', 'sharpe_net2x'))}")

    def oos(series: str, basis: str = "net_1x", col: str = "sharpe") -> float:
        r = om[(om.series == series) & (om.window == "oos") & (om.basis == basis)]
        if len(r) != 1:
            die(f"v2_oos metrics: no unique row for {series} {basis}")
        return float(r[col].iloc[0])

    def d4v(series: str, variant: str, window: str, col: str = "sharpe_net1x") -> float:
        r = d4[(d4.series == series) & (d4.variant == variant) & (d4.window == window)]
        if len(r) != 1:
            die(f"v2_d4 metrics: no unique row for {series} {variant} {window}")
        return float(r[col].iloc[0])

    def d4txt(series: str, variant: str) -> str:
        return (f"Sharpe net 1x / 2x: full IS {f3(d4v(series, variant, 'full_is'))} / "
                f"{f3(d4v(series, variant, 'full_is', 'sharpe_net2x'))}; out-of-sample "
                f"{f3(d4v(series, variant, 'oos'))} / {f3(d4v(series, variant, 'oos', 'sharpe_net2x'))}")

    def plrow(test: str, variant: str, sample: str, sym: str = "ZT", cost: str = "C0", unit: str = "usd") -> pd.Series:
        r = pl[(pl.test == test) & (pl.variant == variant) & (pl["sample"] == sample) & (pl.sym == sym) &
               (pl.cost == cost) & (pl.unit == unit)]
        if len(r) != 1:
            die(f"summary_long: no unique row for {test} | {variant} | {sample} | {sym} | {cost} | {unit}")
        return r.iloc[0]

    def pltxt(test: str, variant: str, sample: str, sym: str = "ZT") -> str:
        r = plrow(test, variant, sample, sym)
        return f"{sample}: n {int(r.n)}, mean ${r['mean']:+.2f} per contract gross, t {f3(r.t)}"

    def strat(strategy: str, sym: str, window: str) -> float:
        r = pst[(pst.strategy == strategy) & (pst.sym == sym) & (pst.window == window) & (pst.role == "headline") &
                (pst.cost == "net1x") & (pst.variant == "all")]
        if len(r) != 1:
            die(f"presser_strategy metrics: no unique row for {strategy} {sym} {window}")
        return float(r.sharpe.iloc[0])

    rows: list[dict] = []

    def add(**k) -> None:
        if k["role"] not in ROLE:
            die(f"bad role {k['role']}")
        rows.append(k)

    # ================= v2 (main strategy) =================
    sig = {"T1": "chrono stance score, Board speeches only",
           "T2": "chrono stance score, speeches + statements + minutes + press conferences, equal weight",
           "T3": "T2 orthogonalised on the 20-session-half-life DGS2 change, lagged 2 days (expanding OLS)",
           "T4": "mean of z(lexicon consensus) and z(stance consensus) on T2's documents"}
    expr = {"E1": "75% TLT / 25% UUP, next-open fills, 1.5 / 5 bp, 30 bp/yr borrow",
            "E2": "75% ZN / 25% short 6E, next-close fills, 1 bp each, a round trip per roll"}
    chosen = S["chosen"]
    for i, (t, e) in enumerate([(t, e) for t in ("T1", "T2", "T3", "T4") for e in ("E1", "E2")], 1):
        c = f"{t}x{e}"
        add(id=f"V2-C{i}", family="v2 Fed communication", parent="HYPOTHESIS_v2 (8 registered combinations)",
            variant=c + (" (chosen)" if c == chosen else ""),
            parameters=f"{sig[t]}; {expr[e]}; half-life 20, expanding z (min 252), clip 2, 10% vol target, floor 4%, "
                       "cap 1.5, band 0.10, FOMC de-risk (101 dates)",
            purpose="registered selection candidate",
            role=ROLE[0], role_in_family="selection candidate (max selection-window net 1x Sharpe)",
            evaluation_period=WIN_IS, period_already_observed=OBS_V2_IS,
            result=win3(c) + ("; chosen; decision rule FAILED (full IS 2x < 0.5)" if c == chosen else ""),
            counted_in="v2 DSR (11)", source=F["v2_windows"])
    dsr = S["dsr"]
    add(id="V2-R1", family="v2 Fed communication", parent="HYPOTHESIS_v2 reference", variant="Variant A frozen (T0fxE1)",
        parameters="strategy 01's frozen speech lexicon, z clock from 2011, E1", purpose="pre-declared reference",
        role=ROLE[1], role_in_family="reference (not selectable)", evaluation_period=WIN_IS + "; " + WIN_OOS,
        period_already_observed=OBS_V2_IS + " | OOS: " + OBS_V2_OOS,
        result=win3("T0fxE1") + f"; out-of-sample net 1x {f3(oos('VariantA_frozen(T0fxE1)'))} (D-3)",
        counted_in="its 3 logged strategy-01 trials are in the v2 DSR; this harness run is not",
        source=F["v2_windows"] + "; " + F["oos_metrics"])
    add(id="V2-R2", family="v2 Fed communication", parent="HYPOTHESIS_v2 reference (implementation choice 14)",
        variant="Variant A with 2015 warm-up (T0v2xE1)", parameters="frozen lexicon on speeches, 2015 warm-up, E1",
        purpose="reference on the same warm-up as v2", role=ROLE[1], role_in_family="reference (not selectable)",
        evaluation_period=WIN_IS, period_already_observed=OBS_V2_IS, result=win3("T0v2xE1"),
        counted_in="none", source=F["v2_windows"])
    r101 = sens_is[sens_is.derisk_list == "scheduled_only_93_dates"].set_index("window")
    add(id="V2-R3", family="v2 Fed communication", parent="DEVIATIONS D-1 (before any v2 return)",
        variant="T4xE1, scheduled-only FOMC de-risk list (93 dates)", parameters="as T4xE1, 8 unscheduled dates removed",
        purpose="sensitivity to the unscheduled de-risk dates", role=ROLE[1],
        role_in_family="registered sensitivity (never used for selection)", evaluation_period=WIN_IS + "; " + WIN_OOS,
        period_already_observed=OBS_V2_IS + " | OOS: evaluated after oos_chosen.json, under D-3",
        result=(f"Sharpe net 1x selection {f3(r101.at['selection', 'sharpe_net1x'])}, validation "
                f"{f3(r101.at['validation', 'sharpe_net1x'])}, full IS {f3(r101.at['full_is', 'sharpe_net1x'])} "
                f"(2x {f3(r101.at['full_is', 'sharpe_net2x'])}); out-of-sample "
                f"{sens_oos.loc[sens_oos.derisk_list == 'scheduled_only_93_dates', 'sharpe_net1x'].iloc[0]:.4f} vs "
                f"{sens_oos.loc[sens_oos.derisk_list == 'registered_101_dates', 'sharpe_net1x'].iloc[0]:.4f} registered"),
        counted_in="none", source=F["v2_sens_is"] + "; " + F["oos_sens"])
    ci = chair_is.set_index(["series", "chair"]).sharpe_net1x
    co = chair_oos.set_index(["series", "chair"]).sharpe_net1x
    add(id="V2-R4", family="v2 Fed communication", parent="HYPOTHESIS_v2 Amendment 1 (added reporting)",
        variant="T4xE1 and Variant A by Fed chair", parameters="Yellen to 2018-02-03, Powell to 2026-05-21, Warsh after",
        purpose="descriptive split, not used for selection", role=ROLE[1], role_in_family="registered descriptive split",
        evaluation_period=WIN_IS + "; " + WIN_OOS, period_already_observed=OBS_V2_IS + " | OOS: " + OBS_V2_OOS,
        result=(f"T4xE1 net 1x: IS Yellen {f3(ci['T4xE1', 'Yellen'])}, Powell {f3(ci['T4xE1', 'Powell'])}; "
                f"OOS Powell {f3(co['T4xE1', 'Powell'])}, Warsh {f3(co['T4xE1', 'Warsh'])}"),
        counted_in="none", source=F["v2_chair_is"] + "; " + F["oos_chair"])
    fz = S["falsifiers"]
    add(id="V2-R5", family="v2 Fed communication", parent="HYPOTHESIS_v2 falsifiers", variant="falsifier checks of T4xE1",
        parameters="selection Sharpe <= 0.2; validation <= 0; > half of IS P&L from 2022; T3 ~ 0 while T1/T2 good; "
                   "2x Sharpe <= 0",
        purpose="registered falsifiers", role=ROLE[1], role_in_family="registered falsifiers",
        evaluation_period=WIN_IS, period_already_observed=OBS_V2_IS,
        result=(f"selection <= 0.2 fired ({f3(S['selection_sharpe_net1x'])}); 2022 share "
                f"{pct(fz['share_full_is_pnl_from_2022'])} fired; validation and 2x falsifiers did not fire; "
                f"T3 tracks T2 (not rate momentum)"),
        counted_in="none", source=F["v2_summary"])
    add(id="V2-R6", family="v2 Fed communication", parent="HYPOTHESIS_v2 multiple testing",
        variant="Deflated Sharpe of the chosen combination",
        parameters=f"{dsr['n_trials']} trials: 8 combinations (selection Sharpe) + Variant A's 3 logged rows "
                   "(row 3 repeats row 2, n = 10 as sensitivity)",
        purpose="registered multiple-testing adjustment", role=ROLE[1], role_in_family="registered statistic",
        evaluation_period="selection window and full IS", period_already_observed=OBS_V2_IS,
        result=(f"DSR selection {f3(dsr['selection_window']['dsr'])}, full IS {f3(dsr['full_is']['dsr'])} "
                f"(SR0 {f3(dsr['selection_window']['sr0_ann'])})"),
        counted_in="defines the v2 DSR count (11)", source=F["v2_summary"])
    pi = port.set_index(["portfolio", "window"]).sharpe_net1x
    add(id="V2-R7", family="v2 Fed communication", parent="HYPOTHESIS_v2 portfolio test (pre-declared)",
        variant="core_ER_6 + T4xE1 vs core_ER_6",
        parameters="T4xE1 as a fourth equal-risk sleeve, 6% target, trailing 252-day covariance, combine.build",
        purpose="pre-declared portfolio test", role=ROLE[1], role_in_family="pre-declared secondary test",
        evaluation_period=WIN_IS, period_already_observed=OBS_V2_IS + "; core_ER_6's returns came from the edge study",
        result=(f"Sharpe net 1x full IS {f3(pi['core_ER_6', 'full_is'])} -> {f3(pi['core_ER_6+T4xE1', 'full_is'])}; "
                f"selection {f3(pi['core_ER_6', 'selection'])} -> {f3(pi['core_ER_6+T4xE1', 'selection'])}; "
                f"validation {f3(pi['core_ER_6', 'validation'])} -> {f3(pi['core_ER_6+T4xE1', 'validation'])}"),
        counted_in="none", source=F["v2_portfolio"])
    add(id="V2-D1", family="v2 Fed communication", parent="deviation D-3 (after the failed rule, before any OOS return)",
        variant="T4xE1 out-of-sample, evaluated once", parameters="frozen code, signals, parameters, costs",
        purpose="report the out-of-sample window the competition requires", role=ROLE[2],
        role_in_family="one-shot out-of-sample opened by deviation (verdict unchanged)", evaluation_period=WIN_OOS,
        period_already_observed=OBS_V2_OOS,
        result=(f"Sharpe net 1x {f3(oos('T4xE1'))}, 2x {f3(oos('T4xE1', 'net_2x'))}, gross {f3(oos('T4xE1', 'gross'))}; "
                f"NW t {f3(oos('T4xE1', col='nw_t'))}"),
        counted_in="none", source=F["oos_metrics"] + "; " + F["oos_chosen"])
    add(id="V2-D2", family="v2 Fed communication", parent="deviation D-3", variant="Variant A out-of-sample",
        parameters="as V2-R1", purpose="reference in the out-of-sample window", role=ROLE[2],
        role_in_family="one-shot out-of-sample reference", evaluation_period=WIN_OOS,
        period_already_observed=OBS_V2_OOS + "; strategy 01's own OOS (same rule) was already known",
        result=f"Sharpe net 1x {f3(oos('VariantA_frozen(T0fxE1)'))}, 2x {f3(oos('VariantA_frozen(T0fxE1)', 'net_2x'))}",
        counted_in="none", source=F["oos_metrics"])
    add(id="V2-D3", family="v2 Fed communication", parent="deviation D-3", variant="portfolio test out-of-sample",
        parameters="as V2-R7", purpose="pre-declared portfolio test in the out-of-sample window", role=ROLE[2],
        role_in_family="one-shot out-of-sample portfolio test", evaluation_period=WIN_OOS,
        period_already_observed=OBS_V2_OOS + "; core_ER_6's OOS returns had appeared in earlier portfolio work",
        result=(f"Sharpe net 1x {f3(oos('core_ER_6'))} -> {f3(oos('core_ER_6+T4xE1'))}; 2x "
                f"{f3(oos('core_ER_6', 'net_2x'))} -> {f3(oos('core_ER_6+T4xE1', 'net_2x'))}"),
        counted_in="none", source=F["oos_metrics"])
    cc = conc[conc.series == "T4xE1"].set_index("subset")
    add(id="V2-D4", family="v2 Fed communication", parent="describe_v2_oos (written after the result)",
        variant="T4xE1 out-of-sample concentration and splits",
        parameters="drop last 1/5/10/20 sessions; Powell vs Warsh; calendar years; 5 best days", purpose="describe "
        "where the out-of-sample result comes from", role=ROLE[2], role_in_family="descriptive, post-result",
        evaluation_period=WIN_OOS, period_already_observed=OBS_POST,
        result=(f"without last 20 sessions Sharpe {f3(cc.at['oos without its last 20 days', 'sharpe'])}; Powell months "
                f"{f3(cc.at['oos, Powell (to 2026-05-21)', 'sharpe'])}, Warsh months "
                f"{f3(cc.at['oos, Warsh (from 2026-05-22)', 'sharpe'])}; 5 best days carry "
                f"{pct(cc.at['share of the oos daily-return sum from its 5 best days', 'value'])} of the daily-return sum"),
        counted_in="none", source=F["oos_conc"])
    for vid, var, desc in (("V2-F1", "fix1", "sizing vol ends at open t-1 (not the fill price)"),
                           ("V2-F2", "fix2", "holdings carried as shares and cash through the overnight drift"),
                           ("V2-F3", "both", "fix 1 and fix 2")):
        add(id=vid, family="v2 Fed communication", parent="deviation D-4 (implementation defects confirmed in code)",
            variant=f"T4xE1 {var}", parameters=desc, purpose="correct an implementation defect (descriptive)",
            role=ROLE[3], role_in_family="implementation correction (committed results stay first)",
            evaluation_period=WIN_IS + "; " + WIN_OOS, period_already_observed=OBS_D4, result=d4txt("T4xE1", var),
            counted_in="none", source=F["d4_metrics"])
    add(id="V2-F4", family="v2 Fed communication", parent="deviation D-4 (fix-1 reading)",
        variant="T4xE1 both fixes, vol from close-to-close returns ending at close t-1",
        parameters="alternative lag of fix 1 (also changes the return definition)",
        purpose="sensitivity of the corrected figure to the fix-1 reading", role=ROLE[3],
        role_in_family="implementation sensitivity (independent check, not a separate run)",
        evaluation_period=WIN_IS + "; " + WIN_OOS, period_already_observed=OBS_D4,
        result="Sharpe net / 2x: full IS 0.402 / 0.346; out-of-sample 0.500 / 0.435 (as stated in the D-4 README)",
        counted_in="none", source=F["d4_readme"])
    add(id="V2-F5", family="v2 Fed communication", parent="deviation D-4", variant="Variant A (T0fxE1) with fixes",
        parameters="fix1 / fix2 / both", purpose="same corrections on the reference", role=ROLE[3],
        role_in_family="implementation correction", evaluation_period=WIN_IS + "; " + WIN_OOS,
        period_already_observed=OBS_D4, result="both: " + d4txt("T0fxE1", "both"), counted_in="none",
        source=F["d4_metrics"])
    add(id="V2-F6", family="v2 Fed communication", parent="deviation D-4",
        variant="core_ER_6 + T4xE1 with the corrected sleeve", parameters="fix1 / fix2 / both; core sleeves as committed",
        purpose="portfolio test with the corrected sleeve", role=ROLE[3], role_in_family="implementation correction",
        evaluation_period=WIN_IS + "; " + WIN_OOS, period_already_observed=OBS_D4,
        result="both: " + d4txt("core_ER_6+T4xE1", "both"), counted_in="none", source=F["d4_metrics"])
    for vid, ser, desc, purpose in (
            ("V2-B1", "LEXALLxE1", "all-document lexicon z that T4 averages (lex_score, keep H+D >= 5), E1",
             "matched benchmark: lexicon leg alone"),
            ("V2-B2", "T2xE1", "all-document stance z (= V2-C3), E1", "matched benchmark: stance model alone"),
            ("V2-B3", "T0v2xE1", "Variant A lexicon with the 2015 warm-up (= V2-R2), E1",
             "matched benchmark: lexicon reference"),
            ("V2-B4", "MxE1", "expanding z of T3's rate momentum M, E1 sizing and costs",
             "simple benchmark: rate momentum alone"),
            ("V2-B5", "BH7525volxE1", "long 75/25 TLT/UUP with E1 sizing", "simple benchmark: long-only, same sizing")):
        add(id=vid, family="v2 Fed communication", parent="deviation D-4 benchmarks", variant=ser, parameters=desc,
            purpose=purpose, role=ROLE[2], role_in_family="benchmark computed after the results (descriptive)",
            evaluation_period=WIN_IS + "; " + WIN_OOS, period_already_observed=OBS_D4,
            result="original: " + d4txt(ser, "original") + " | both fixes: " + d4txt(ser, "both"),
            counted_in="none", source=F["d4_metrics"])
    add(id="V2-B6", family="v2 Fed communication", parent="deviation D-4 benchmarks", variant="BH7525hold",
        parameters="75/25 TLT/UUP bought at the first E1 open, never rebalanced, unlevered",
        purpose="simple benchmark: buy-and-hold", role=ROLE[2], role_in_family="benchmark computed after the results",
        evaluation_period=WIN_IS + "; " + WIN_OOS, period_already_observed=OBS_D4,
        result=(f"Sharpe net 1x full IS {f3(d4v('BH7525hold', 'hold', 'full_is'))}, out-of-sample "
                f"{f3(d4v('BH7525hold', 'hold', 'oos'))}"),
        counted_in="none", source=F["d4_metrics"])
    picks = wf[wf.picked].groupby("universe").apply(lambda g: ", ".join(f"{r.year_end[:4]}:{r.combo}"
                                                                         for r in g.itertuples()))
    for vid, var, uni in (("V2-W1", "original", "original"), ("V2-W2", "fixed", "fixed")):
        add(id=vid, family="v2 Fed communication", parent="deviation D-4 (robustness, post hoc)",
            variant=f"walk-forward selection ({var} universe)",
            parameters="each year-end from 2020, the registered combination with the highest trailing net Sharpe "
                       "from 2016, traded the next calendar year",
            purpose="does a rolling choice differ from the registered one", role=ROLE[2],
            role_in_family="post hoc robustness", evaluation_period="2021-01-04..2024-10-02 and " + WIN_OOS,
            period_already_observed=OBS_D4,
            result=(f"picks {picks.get(uni, '')}; Sharpe net 1x 2021..2024-10-02 "
                    f"{f3(d4v('WF_max_trailing_sharpe', var, 'wf_is'))}, out-of-sample "
                    f"{f3(d4v('WF_max_trailing_sharpe', var, 'oos'))}"),
            counted_in="none", source=F["d4_metrics"] + "; " + F["d4_wf"])
    add(id="V2-I1", family="v2 Fed communication", parent="HYPOTHESIS_v2 Amendments 2-3, presser D1/D1a",
        variant="walk-forward chrono-BERT stance model replaces the gated FOMC-RoBERTa",
        parameters="model Y = chrono-bert-v1-<Y-1>, fine-tuned on labels dated before Y; 12 years x 3 seeds = 36 "
                   "fine-tunes; labels re-dated from source documents",
        purpose="registered scorer unavailable (gated)", role=ROLE[3],
        role_in_family="pre-result substitution (FOMC-RoBERTa never run)", evaluation_period="none (scorer)",
        period_already_observed="before any v2 return; after strategy 01's OOS verdict",
        result="no trading result of its own; validation macro-F1 0.545-0.684", counted_in="none (not a trading trial)",
        source=F["prereg_v2"])
    add(id="V2-I2", family="v2 Fed communication", parent="pipeline tests",
        variant="placebo runs on random scores and positive controls",
        parameters="v2 code path on fake scores (smoke placebo, placebo chain)",
        purpose="test the pipeline before real scores existed", role=ROLE[3],
        role_in_family="pipeline test (carries no information about the hypothesis)", evaluation_period="IS and OOS code paths",
        period_already_observed="before any real v2 return", result="no information by construction",
        counted_in="none (not a trial)", source=F["placebo"] + "; " + F["dev_v2"])
    add(id="V2-I3", family="v2 Fed communication", parent="reproductions",
        variant="HiPerGator reproduction and switch-off reproduction of the committed run",
        parameters="same code and inputs; no new choice", purpose="check that committed numbers reproduce",
        role=ROLE[3], role_in_family="reproduction (no new variant)", evaluation_period=WIN_IS + "; " + WIN_OOS,
        period_already_observed=OBS_POST, result="PASS, max abs difference 1.8e-15 (HiPerGator) and 0.0 (switch off)",
        counted_in="none", source=F["d4_readme"] + "; " + F["report"])

    # ================= press-conference family =================
    pc_obs_h1 = ("H1 blind when the ADDENDUM was written (no stance score joined to returns); 12 of the 20 G3 meetings "
                 "lie in the calendar out-of-sample window and were reported on 2026-10-03")
    pc_obs_br = "non-blind: BENCH-R era correlations had been seen before the ADDENDUM (section 12)"
    pc_obs_h234 = ("post-G3 (after the H1 NO-GO); gate outcomes seen in a no-price diagnostic before the fix (Note 3); "
                   "2019-05-01 and 2020-03-03 development tables written before the pre-registration (Note 1)")
    win_conf = "confirmation 2023-02-01..2026-04-29 (20 timing-eligible meetings); 2016-2022; Warsh 2026"
    h1 = key["H1-primary (stance)"]
    add(id="PC-01", family="press conference (H1 family)", parent="presser_team_FINAL_PLAN + ADDENDUM + D1 (G3 gate)",
        variant="H1-primary: Q&A stance minus statement stance, residualised; short ZT on hawkish, next 1m open to 16:00",
        parameters="ZT.v.0, primary clock (TV-anchored, answer end + start uncertainty), one contract, 8-meeting burn-in",
        purpose="the single gated primary (G3)", role=ROLE[4], role_in_family="gated primary",
        evaluation_period=win_conf, period_already_observed=pc_obs_h1,
        result=(f"G3 NO-GO: n {h1['n']}, mean {h1['mean']:+.2f} ticks (${h1['mean_usd']:+.2f}), t {f3(h1['t'])}, "
                f"one-sided sign-flip p {h1['wb_p_one']:.4f}; 90% block CI [{h1['bb_ci90_lo']:.2f}, "
                f"{h1['bb_ci90_hi']:.2f}] ticks"),
        counted_in="press-conference gate (single primary, no multiplicity adjustment)", source=F["pc_key"])
    add(id="PC-02", family="press conference (H1 family)", parent="ADDENDUM section 2", variant="H1-primary, other samples",
        parameters="2016-2022 sample (positions from 2018-03-21; D1-clean) and the 3 Warsh meetings",
        purpose="descriptive samples, never part of G3", role=ROLE[4], role_in_family="descriptive",
        evaluation_period="2016-2022; Warsh 2026", period_already_observed=pc_obs_h1,
        result=pltxt("H1-primary[H1]", "primary|exit_1600", "2016-2022") + "; " +
        pltxt("H1-primary[H1]", "primary|exit_1600", "warsh"), counted_in="none", source=F["pc_long"])
    add(id="PC-03", family="press conference (H1 family)", parent="ADDENDUM 3.6 and section 10",
        variant="H1-primary extra rows: exit 16:30, exec+30 s, point clock, convention clock",
        parameters="one change each against the primary row", purpose="registered extra rows, never decisive",
        role=ROLE[4], role_in_family="prespecified robustness", evaluation_period=win_conf,
        period_already_observed=pc_obs_h1,
        result="; ".join(f"{v.split('|')[0] if 'primary' not in v else v.split('|')[1]}: "
                         + pltxt("H1-primary[H1]", v, "confirmation").split(': ', 1)[1]
                         for v in ("primary|exit_1630", "exec30|exit_1600", "point_clock|exit_1600",
                                   "convention_clock|exit_1600")),
        counted_in="none", source=F["pc_long"])
    add(id="PC-04", family="press conference (H1 family)", parent="ADDENDUM section 2 sensitivities",
        variant="H1-primary sensitivities 1-3", parameters="drop text-flag meetings; drop degraded data days; "
        "start uncertainty <= 10 s", purpose="registered sensitivities", role=ROLE[4],
        role_in_family="prespecified robustness", evaluation_period="confirmation", period_already_observed=pc_obs_h1,
        result=(f"n 18 mean {h1['sens1_drop_text_flags_mean']:+.2f} ticks (p {h1['sens1_drop_text_flags_wb_p_one']}); "
                f"n 18 {h1['sens2_drop_degraded_mean']:+.2f} (p {h1['sens2_drop_degraded_wb_p_one']}); "
                f"n 3 {h1['sens3_unc_le10_mean']:+.2f} (p {h1['sens3_unc_le10_wb_p_one']})"),
        counted_in="none", source=F["pc_key"])
    add(id="PC-05", family="press conference (H1 family)", parent="ADDENDUM (robustness symbols)",
        variant="H1-primary on ZF, ZN, ES", parameters="same positions, other contracts", purpose="robustness symbols",
        role=ROLE[4], role_in_family="prespecified robustness", evaluation_period="confirmation",
        period_already_observed=pc_obs_h1,
        result="; ".join(f"{s}: " + pltxt("H1-primary[H1]", "primary|exit_1600", "confirmation", s).split(': ', 1)[1]
                         for s in ("ZF", "ZN", "ES")),
        counted_in="none", source=F["pc_long"])
    add(id="PC-06", family="press conference (H1 family)", parent="ADDENDUM 3.7", variant="H1 companion slope",
        parameters="OLS of the ZT exit return on s_m with R_m control; HC3 t", purpose="registered companion statistic",
        role=ROLE[4], role_in_family="prespecified, not decisive", evaluation_period="confirmation",
        period_already_observed=pc_obs_h1, result=f"slope HC3 t {f3(h1['slope_t_hc3'])}, two-sided p {h1['slope_p_two']}",
        counted_in="none", source=F["pc_key"])
    add(id="PC-07", family="press conference (H1 family)", parent="ADDENDUM section 7",
        variant="cost grid C0, C2, C4, CM, CQ, C2F, C4F, CMF", parameters="the same trades at each cost level",
        purpose="costs, not separate trials", role=ROLE[4], role_in_family="prespecified cost rows",
        evaluation_period=win_conf, period_already_observed=pc_obs_h1,
        result=(f"H1 confirmation CM {plrow('H1-primary[H1]', 'primary|exit_1600', 'confirmation', 'ZT', 'CM')['mean']:+.2f}"
                f", C2 {plrow('H1-primary[H1]', 'primary|exit_1600', 'confirmation', 'ZT', 'C2')['mean']:+.2f}, "
                f"C4 {plrow('H1-primary[H1]', 'primary|exit_1600', 'confirmation', 'ZT', 'C4')['mean']:+.2f} $ per contract"),
        counted_in="none (cost levels of the same trades)", source=F["pc_long"])
    hq = key["H1-Q"]
    add(id="PC-08", family="press conference (H1 family)", parent="ADDENDUM section 6",
        variant="H1-Q (question stance added to the residual regression)", parameters="as H1-primary plus q_m",
        purpose="robustness (collider risk)", role=ROLE[4], role_in_family="prespecified robustness, not gated",
        evaluation_period="confirmation; 2016-2022", period_already_observed=pc_obs_h1,
        result=(f"confirmation two-sided p {hq['ZT_primary_exit1600_C0_confirmation']['wb_p_two']}, 2016-2022 "
                f"two-sided p {hq['ZT_primary_exit1600_C0_2016-2022']['wb_p_two']}"),
        counted_in="none", source=F["pc_key"])
    lx = key["lexicon lex_H1_raw G3-rule replica (control, two-sided reading)"]
    add(id="PC-09", family="press conference (H1 family)", parent="ADDENDUM section 6",
        variant="lexicon negative control: frozen lex_H1 and ungated lex_H1_raw",
        parameters="the H1 pipelines on strategy 01's frozen lexicon scores", purpose="negative control (expected null)",
        role=ROLE[4], role_in_family="prespecified negative control", evaluation_period=win_conf,
        period_already_observed=pc_obs_h1,
        result=(f"lex_H1 not estimable (defined for 4 of 75 meetings); lex_H1_raw confirmation n {lx['n']}, "
                f"${lx['mean_usd']:+.2f} per contract, t {f3(lx['t'])}, two-sided p {lx['wb_p_two']}"),
        counted_in="none", source=F["pc_key"])
    hans = pa[(pa.signal == "H1") & (pa.cost == "C0") & (pa.split == "all") & (pa["sample"] == "confirmation")]
    add(id="PC-10", family="press conference (H1 family)", parent="ADDENDUM section 4",
        variant="H1-answer (answer-level surprise; +1, +5 min; +15 min appendix), H1 and lex_H1_raw",
        parameters="entry next 1m open after the answer end; greedy non-overlap selection", purpose="diagnostic only",
        role=ROLE[4], role_in_family="prespecified diagnostic", evaluation_period=win_conf,
        period_already_observed=pc_obs_h1,
        result="confirmation two-sided wild-cluster p: " + ", ".join(
            f"+{int(r.h)} min {r.wcb_p_two:.4f} (n {int(r.n_answers)})" for r in hans.itertuples()),
        counted_in="none", source=F["pc_answer"])
    add(id="PC-11", family="press conference (H1 family)", parent="ADDENDUM 4.4",
        variant="H1-answer 1-second latency sweep",
        parameters="L in {0, 5, 15, 30} s, exits +60/+300 s, mid / quote / 2 / 4 ticks, ZT (ZN, ES robustness), split "
                   "by start uncertainty", purpose="labelled diagnostic, not a retune", role=ROLE[4],
        role_in_family="prespecified diagnostic", evaluation_period=win_conf, period_already_observed=pc_obs_h1,
        result=f"{len(ps)} rows; no row changes any H1 definition", counted_in="none", source=F["pc_sweep"])
    add(id="PC-12", family="press conference (BENCH-R)", parent="ADDENDUM section 5",
        variant="BENCH-R: sign of the 13:50-14:20 ZT move held 14:20 to the H1 entry bar",
        parameters="ZT.v.0, eras 2016-2019 (one-sided) and 2020-2026 (two-sided), never averaged",
        purpose="non-blind descriptive replication (Narain and Sangani)", role=ROLE[4],
        role_in_family="descriptive replication", evaluation_period="2016-2019; 2020-2026",
        period_already_observed=pc_obs_br,
        result=pltxt("BENCH-R", "exit_tau_upper", "era_2016-2019") + "; " +
        pltxt("BENCH-R", "exit_tau_upper", "era_2020-2026"), counted_in="none", source=F["pc_long"])
    add(id="PC-13", family="press conference (BENCH-R)", parent="ADDENDUM section 5",
        variant="BENCH-R robustness exits and subsets",
        parameters="exit 15:30; timing-eligible; ex-Warsh; ex-2022; January 2020 early; yearly; 2024-10..2026-09 decay",
        purpose="registered robustness", role=ROLE[4], role_in_family="prespecified robustness",
        evaluation_period="2016-2026", period_already_observed=pc_obs_br,
        result=("exit 15:30 " + pltxt("BENCH-R", "exit_1530", "era_2020-2026") + "; ex-2022 " +
                pltxt("BENCH-R", "exit_tau_upper|ex_2022", "era_2020-2026") + "; decay " +
                pltxt("BENCH-R", "exit_tau_upper|decay_2024-10_2026-09", "decay")),
        counted_in="none", source=F["pc_long"])
    add(id="PC-14", family="press conference (BENCH-R)", parent="ADDENDUM section 5 (A-19, appendix)",
        variant="BENCH-R on ES (own sign), ZF, ZN; USMPD UST2Y version; break statistics and cost hurdle",
        parameters="same rule on other instruments; USMPD statement sign on the conference window",
        purpose="robustness and context", role=ROLE[4], role_in_family="prespecified robustness",
        evaluation_period="2016-2019; 2020-2026", period_already_observed=pc_obs_br,
        result="ES " + pltxt("BENCH-R", "exit_tau_upper", "era_2016-2019", "ES"),
        counted_in="none", source=F["pc_long"] + "; " + F["pc_break"])
    add(id="PC-15", family="press conference (strategy series)", parent="deviation D-3 (presentation)",
        variant="H1-primary and BENCH-R as daily strategy series on ZT, ZF, ZN, ES",
        parameters="frozen positions, N contracts for 10% in-sample gross vol on $10m, gross / net / 2x / fixed costs",
        purpose="present pre-registered trades as strategies", role=ROLE[4], role_in_family="post-result presentation",
        evaluation_period="IS to 2024-10-02; OOS 2024-10-03..2026-10-02 (calendar split, not a fresh holdout)",
        period_already_observed="yes: positions and per-trade P&L were already reported",
        result=(f"net 1x Sharpe IS / OOS: H1 ZT {f3(strat('H1-primary', 'ZT', 'IS'))} / "
                f"{f3(strat('H1-primary', 'ZT', 'OOS'))}; BENCH-R ZT {f3(strat('BENCH-R', 'ZT', 'IS'))} / "
                f"{f3(strat('BENCH-R', 'ZT', 'OOS'))}; BENCH-R ES {f3(strat('BENCH-R', 'ES', 'IS'))} / "
                f"{f3(strat('BENCH-R', 'ES', 'OOS'))}"),
        counted_in="none", source=F["pc_strategy"])
    for vid, k, desc in (("PC-16", "H2", "answer-level vocal arousal z; long ZT on high arousal, +1 min"),
                         ("PC-17", "H3", "upper-face composite (brow lowering, inner-brow raise, eye squint), +1 min"),
                         ("PC-18", "H4", "text + arousal + upper face vs text only, frozen OLS on 2018-2022, Clark-West")):
        hv = holm[k]
        raw = "none (killed, enters at p = 1)" if hv["p_raw"] is None else f"{hv['p_raw']:.4f}"
        res = (f"status {hv['status']}; raw p {raw}, Holm p {hv['p_holm']:.4f} (m = 3); n "
               f"{hv['n_answers']} answers in {hv['n_meetings']} meetings")
        if hv.get("reasons"):
            res += "; " + "; ".join(hv["reasons"])
        add(id=vid, family="press conference (H2/H3/H4)", parent="presser_H2H3H4_EXPLORATORY + notes 1-3",
            variant=k, parameters=desc, purpose="exploratory voice/face test (cannot rescue G3)", role=ROLE[4],
            role_in_family="exploratory primary (Holm family of 3)", evaluation_period="2023-2026 test meetings (10)",
            period_already_observed=pc_obs_h234, result=res, counted_in="exploratory Holm family (3)",
            source=F["h234_holm"])
    n_sec = int(len(h2a))
    add(id="PC-19", family="press conference (H2/H3/H4)", parent="presser_H2H3H4_EXPLORATORY",
        variant="H2/H3 secondary rows, H2D dominance, tier-3 face features",
        parameters="horizons 5/15 min, ZF/ZN/ES, entry +30 s, samples 2018-2022 / pooled / ex-2020-21, sensitivities; "
                   "tier-3 companion slopes without counted p-values", purpose="secondary and descriptive rows",
        role=ROLE[4], role_in_family="secondary / descriptive", evaluation_period="2018-2026",
        period_already_observed=pc_obs_h234,
        result=f"{n_sec} answer-summary rows and {len(slopes)} companion slopes; none counted in Holm",
        counted_in="none", source=F["h234_answers"] + "; " + F["h234_slopes"])
    mz = h4["meeting_ZT"]
    add(id="PC-20", family="press conference (H2/H3/H4)", parent="presser_H2H3H4_EXPLORATORY",
        variant="H4 other rows: meeting level, expanding window, leave-one-meeting-out, ES",
        parameters="same frozen fit", purpose="descriptive, outside Holm", role=ROLE[4], role_in_family="descriptive",
        evaluation_period="2023-2026", period_already_observed=pc_obs_h234,
        result=(f"meeting-level ZT t {f3(mz['t'])} (n {mz['n']}; out-of-sample R^2 vs zero {f3(mz['oos_r2_C_vs_zero'])}); "
                "not findings"), counted_in="none", source=F["h234_h4"])
    add(id="PC-21", family="press conference (H2/H3/H4)", parent="NOTE1 (run order) and NOTE3 (stage-1 fix)",
        variant="local RTX 5090 replication; stage-1 WAV-length fix; source-invariance check",
        parameters="same code and model revisions; 64 kbps re-encode check could not run",
        purpose="replication and implementation", role=ROLE[4],
        role_in_family="implementation correction / replication", evaluation_period="2018-2026",
        period_already_observed=pc_obs_h234,
        result="local replication H2 p 0.438, H3 killed, H4 p 0.244 (HiPerGator governs); invariance not checked",
        counted_in="none", source=F["h234_local"] + "; " + F["note3"])

    # ================= strategy 01 =================
    for i, r in enumerate(s01.itertuples(index=False), 1):
        add(id=f"S01-T{i}", family="strategy 01 (Variant A)",
            parent="strategies/01 HYPOTHESIS (Variant A, trial log)",
            variant=f"log row {i}: trial id {r.trial} ({r.ts_utc})" + (" (repeats row 2)" if i == 3 else ""),
            parameters=str(r.reason), purpose="the predecessor's logged in-sample trials", role=ROLE[4],
            role_in_family="logged trial", evaluation_period=f"IS {r.first_z}..{r.last_ret}",
            period_already_observed="in-sample only; the author's log is dated 2026-10-03, when later years existed",
            result=f"Sharpe 1x {f3(r.sharpe_1x)}, 2x {f3(r.sharpe_2x)}, gross {f3(r.sharpe_gross)}",
            counted_in="strategy 01 log (3) and v2 DSR (11)", source=F["s01_log"])
    t1o = t1[(t1.strategy == "tone") & (t1.window == "OOS")].set_index("series").sharpe
    add(id="S01-R1", family="strategy 01 (Variant A)", parent="strategies/01/review (independent review)",
        variant="replication and frozen-rule out-of-sample", parameters="frozen rule, 203 later speeches scored",
        purpose="clean out-of-sample test of the frozen rule", role=ROLE[4], role_in_family="review: replication + OOS",
        evaluation_period="IS 2011-12-30..2024-10-02; OOS 2024-10-03..2026-10-02",
        period_already_observed="OOS market data not used by the frozen rule; verdict committed 20:26 UTC 2026-10-03",
        result=(f"OOS Sharpe net 1x, excess over T-bill {f3(t1o['ex_net1x'])} (review engine with rf = 0: "
                f"{f3(t1o['rf0_net1x'])}); verdict drop"),
        counted_in="none", source=F["s01_t1"] + "; " + F["s01_verdict"])
    add(id="S01-R2", family="strategy 01 (Variant A)", parent="strategies/01/review/analyse/PREDECLARED.md",
        variant="rate-momentum control, orthogonalised tone, futures version, portfolio test",
        parameters="as written before any post-cut result (control, z_orth, ZN + short 6E, core_ER_6 sleeve)",
        purpose="review analyses", role=ROLE[4], role_in_family="prespecified review analyses",
        evaluation_period="IS, holdout 2021..2024-10, OOS",
        period_already_observed="written before any post-cut result of these analyses",
        result="alpha over the DGS2 control 2.3%/yr (t 0.84); futures IS 0.36 / OOS 0.10; core_ER_6 change OOS "
               "-0.37 (ETF) / -0.03 (ZN)", counted_in="none", source=F["s01_predeclared"] + "; " + F["s01_verdict"])

    # ================= edge / portfolio study (117 documented trials) =================
    edge_obs = ("in-sample through 2024-10-02 used for every choice; the later window 2024-10-03..2026-10-02 was "
                "descriptive and already seen by the project")
    ci_ = carry[carry.window == "IS"]
    rpf = rp[(rp.source == "futures") & (rp.window == "IS")]
    cali = cal[(cal.window == "IS") & (cal.cost == "net_1x") & (cal.scaling == "10vol")]
    vali = val[(val.window == "IS") & (val.kind == "variant")]
    combi = comb[comb.window == "IS"]
    edge_counts = {"carry": int(ci_.series.nunique()), "risk_premia": int(rp.name.nunique()),
                   "calendar": int(cali.groupby(["candidate", "variant", "instrument"]).ngroups),
                   "value": int(vali.candidate.nunique()), "combine": int(combi.portfolio.nunique())}
    if sum(edge_counts.values()) != combs["dsr"]["n_trials"]:
        die(f"edge study component counts {edge_counts} do not add up to {combs['dsr']['n_trials']}")
    vc = rpv.verdict.value_counts().to_dict()
    for eid, comp, spec, par, res in (
            ("E-1", "carry", F["e_carry_spec"], "signal {C1, C12} x rebalance {monthly, weekly} x {XS, TS} = 8 global "
             "books + 32 class books", f"IS net 1x Sharpe {f3(ci_.sharpe_net_1x.min())}..{f3(ci_.sharpe_net_1x.max())}"
             f" ({int((ci_.sharpe_net_1x > 0).sum())} of 40 positive)"),
            ("E-2", "risk_premia", F["e_rp_spec"], "4 sleeves x 6 overlays = 24 futures variants + 12 long-history "
             "proxy variants (not tradeable)", f"futures IS net 1x {f3(rpf.sharpe_net1.min())}..{f3(rpf.sharpe_net1.max())};"
             f" verdicts real_edge {vc.get('real_edge', 0)}, weak {vc.get('weak_or_uncertain', 0)}, fails {vc.get('fails', 0)}"),
            ("E-3", "calendar", F["e_cal_spec"], "TOM 3, TSY 3, PREHOL 2, FOMC 1, futures timing 4",
             f"IS net 1x (10% vol) {f3(cali.sharpe.min())}..{f3(cali.sharpe.max())}"),
            ("E-4", "value", F["e_val_spec"], "11 value/momentum variants (11 diagnostics not counted)",
             f"IS net 1x {f3(vali.net_sharpe_1x.min())}..{f3(vali.net_sharpe_1x.max())}; no sleeve eligible"),
            ("E-5", "combine", F["e_comb_spec"], "{core, broad} x {ER, IV, FAM} x {6%, 10%} = 12 + 5 diagnostics",
             f"IS net 1x {f3(combi.sharpe_net1x.min())}..{f3(combi.sharpe_net1x.max())}; best {combs['dsr']['best']} "
             f"{f3(combs['dsr']['is_sharpe'])}, DSR {f3(combs['dsr']['dsr'])} with 117 trials")):
        add(id=eid, family="edge / portfolio study", parent=f"archive edges/{comp} SPEC (written before results)",
            variant=f"{comp}: {edge_counts[comp]} variants", parameters=par, purpose="earlier edge and portfolio research",
            role=ROLE[4], role_in_family="trial set of the study", evaluation_period="IS about 2011/2012..2024-10-02; "
            "later window 2024-10-03..2026-10-02", period_already_observed=edge_obs, result=res,
            counted_in=f"edge study 117 ({edge_counts[comp]})", source=spec)
    ce = comb[comb.portfolio == "core_ER_6"].set_index("window").sharpe_net1x
    add(id="E-6", family="edge / portfolio study", parent="combine main grid",
        variant="core_ER_6 (rpm_ES_MM, CAL_TSY_ME_ZN, S1 trend; equal risk, 6%)",
        parameters="the portfolio v2's portfolio test extends", purpose="baseline of the v2 portfolio test",
        role=ROLE[4], role_in_family="one of the 17 portfolios", evaluation_period="IS 2012-05-02..2024-10-02; later",
        period_already_observed=edge_obs,
        result=f"Sharpe net 1x IS {f3(ce['IS'])}, later window {f3(ce['later'])}",
        counted_in="edge study 117 (within combine 17)", source=F["e_comb"])

    # ================= solo repository =================
    for fam, (n_rows, n_names, n_hash, n_is, n_oos) in SOLO["families"].items():
        add(id=f"SOLO-{fam}", family="solo repository (gqh-flow-clock)",
            parent=f"{SOLO['url']} HYPOTHESES.md (commit {SOLO['commit']})", variant=f"trial family {fam}",
            parameters=f"{n_names} distinct names, {n_hash} distinct parameter hashes",
            purpose="the author's earlier pre-registered strategy search (IFC, PCT, FTE ensemble, futures replications)",
            role=ROLE[4], role_in_family="logged trials", evaluation_period="IS and OOS per that repository's protocol",
            period_already_observed="its OOS rows were logged on 2026-10-03 (11:46 UTC)",
            result=f"{n_rows} logged rows ({n_is} IS, {n_oos} OOS)", counted_in=f"solo trials.csv ({n_rows} rows)",
            source=f"{SOLO['url']} {SOLO['file']} @ {SOLO['commit']} ({solo_note})")
    add(id="SOLO-ARCHIVE", family="solo repository (gqh-flow-clock)", parent="archive copies",
        variant="partial earlier snapshots of the solo trial log",
        parameters=f"before/trials.csv {len(sb)} rows; pct_review/before/trials_before.csv {len(spb)} rows",
        purpose="snapshots kept in the archive", role=ROLE[4], role_in_family="duplicate snapshots (not extra trials)",
        evaluation_period="IS", period_already_observed="-", result="subsets of the solo log; not added",
        counted_in="none (duplicates)", source=F["solo_before"] + "; " + F["solo_pct_before"])

    # ================= earlier screens that cannot be counted exactly =================
    hunt_specs = sorted(p for p in P["hunt100"].glob("bt_*/*/SPEC.md"))
    hunt_series = sorted(P["hunt100"].glob("series/*.json"))
    auc = P["auction_spec"].read_text(encoding="utf-8")
    m = re.search(r"Variants \((\d+) eligible \+ (\d+) diagnostics\)", auc)
    add(id="X-1", family="earlier screens", parent="archive hunt100 (bt_0..bt_5 COMMON_SPEC)",
        variant=f"100-strategy screen: {len(hunt_specs)} backtested strategy specs",
        parameters="each spec: a base rule plus three pre-declared variants (COMMON_SPEC)",
        purpose="earlier literature screen", role=ROLE[4], role_in_family="screen",
        evaluation_period="IS to 2024-10-02; later window already seen", period_already_observed="later window seen",
        result=f"at most {4 * len(hunt_specs)} variant runs if every spec ran all four; {len(hunt_series)} series "
               "archived (large files were dropped)", counted_in="not countable exactly", source=F["hunt100"])
    add(id="X-2", family="earlier screens", parent="archive auction/futures_test SPEC",
        variant="Treasury auction cycle", parameters=f"{m.group(1)} eligible variants + {m.group(2)} diagnostics" if m
        else "see SPEC", purpose="earlier study", role=ROLE[4], role_in_family="study",
        evaluation_period="IS to 2024-10-02", period_already_observed="-", result="rejected (report section 8)",
        counted_in=f"documented in its SPEC ({m.group(1)} + {m.group(2)})" if m else "see SPEC",
        source=F["auction_spec"])
    add(id="X-3", family="earlier screens", parent="archive gtaa_study, intraday_study, kit_native; solo forward tests",
        variant="tactical allocation, intraday/overnight effects, starter-kit runs, forward tests",
        parameters="no trial log with a count", purpose="earlier studies", role=ROLE[4], role_in_family="studies",
        evaluation_period="various", period_already_observed="-",
        result="rejected for costs or decay (report section 8); ideas also documented outside this repository",
        counted_in="not countable exactly", source=F["gtaa"] + "; " + F["intraday"] + "; " + F["kit_native"])

    df = pd.DataFrame(rows)[["id", "family", "parent", "variant", "parameters", "purpose", "role", "role_in_family",
                             "evaluation_period", "period_already_observed", "result", "counted_in", "source"]]
    if df.id.duplicated().any():
        die("duplicate ledger ids")
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "VARIANT_LEDGER.csv", index=False, lineterminator="\n")

    # ---------------- documented counts per scope ----------------
    counts = [
        dict(scope="v2 Deflated Sharpe trial set", documented_count=int(dsr["n_trials"]),
             distinct=int(dsr["n_trials"]) - 1,
             includes="8 registered combinations (selection-window Sharpe) + Variant A's 3 logged trials",
             excludes="references, D-1 sensitivity, D-3, D-4 fixed rows, benchmarks, walk-forward, placebo runs",
             exact="yes", source=F["v2_summary"] + "; " + F["prereg_v2"]),
        dict(scope="v2 family rows in this ledger", documented_count=int((df.family == "v2 Fed communication").sum()),
             distinct=np.nan, includes="every v2 variant and comparison listed here",
             excludes="cost multiples and windows of the same series", exact="yes (ledger rows, not trials)",
             source="VARIANT_LEDGER.csv"),
        dict(scope="v2 D-4 metric rows", documented_count=int(len(d4)),
             distinct=int(d4.groupby(["series", "variant"]).ngroups),
             includes="series x variant x window rows of the D-4 run", excludes="-", exact="yes (rows, not trials)",
             source=F["d4_metrics"]),
        dict(scope="strategy 01 trial log", documented_count=int(len(s01)), distinct=2,
             includes="trial 1 (z-clock bug), trial 2 (spec fix), trial 3 (rerun of trial 2)",
             excludes="the independent review's analyses", exact="yes", source=F["s01_log"]),
        dict(scope="strategy 01 review analysis rows", documented_count=int(len(t1)), distinct=np.nan,
             includes="strategy x window x series rows", excludes="-", exact="yes (rows, not trials)",
             source=F["s01_t1"]),
        dict(scope="press conference: gated primary", documented_count=1, distinct=1,
             includes="H1-primary on the 20 confirmation meetings", excludes="every other row (not gated)",
             exact="yes (ADDENDUM 8.3: single primary, no multiplicity adjustment)", source=F["pc_addendum"]),
        dict(scope="press conference: H1/BENCH-R/H1-Q/lexicon summary rows", documented_count=int(len(pl)),
             distinct=int(pl.groupby(["test", "variant"]).ngroups),
             includes="test x variant x sample x symbol x cost x unit", excludes="-", exact="yes (rows, not trials)",
             source=F["pc_long"]),
        dict(scope="press conference: H1-answer and sweep rows", documented_count=int(len(pa) + len(ps)),
             distinct=np.nan, includes=f"{len(pa)} answer rows + {len(ps)} sweep rows", excludes="-",
             exact="yes (rows, not trials)", source=F["pc_answer"] + "; " + F["pc_sweep"]),
        dict(scope="press conference: exploratory Holm family", documented_count=3, distinct=3,
             includes="H2, H3 (killed), H4", excludes=f"{n_sec} secondary answer rows, {len(slopes)} companion slopes",
             exact="yes", source=F["h234_holm"]),
        dict(scope="edge / portfolio study", documented_count=int(combs["dsr"]["n_trials"]), distinct=np.nan,
             includes=" + ".join(f"{v} {k}" for k, v in edge_counts.items()),
             excludes="11 value diagnostics; earlier project trials (SPEC: 'earlier project trials are not added'); "
                      "12 of the 36 risk-premia variants are long-history proxies, not tradeable",
             exact="yes", source=F["e_comb_spec"] + "; " + F["e_comb_summary"]),
        dict(scope="solo repository trials.csv", documented_count=SOLO["rows"], distinct=SOLO["names"],
             includes="; ".join(f"{k} {v[0]}" for k, v in SOLO["families"].items()),
             excludes="forward tests and screens outside the log",
             exact=f"yes for the file ({solo_note})", source=f"{SOLO['url']} {SOLO['file']} @ {SOLO['commit']}"),
        dict(scope="hunt100 screen", documented_count=np.nan, distinct=len(hunt_specs),
             includes=f"{len(hunt_specs)} strategy specs, base + 3 declared variants each; {len(hunt_series)} series "
                      "archived", excludes="-", exact="no (outputs partly dropped from the archive)",
             source=F["hunt100"]),
        dict(scope="auction study", documented_count=int(m.group(1)) + int(m.group(2)) if m else np.nan,
             distinct=int(m.group(1)) if m else np.nan, includes="eligible variants + diagnostics", excludes="-",
             exact="yes for its SPEC", source=F["auction_spec"]),
        dict(scope="whole project", documented_count=np.nan, distinct=np.nan,
             includes="all of the above plus gtaa, intraday, starter-kit and forward-test work and ideas documented "
                      "outside this repository",
             excludes="-", exact="no: scopes overlap (Variant A's trials are in strategy 01 and the v2 DSR; core_ER_6 "
                                 "is one of the 117 and the v2 portfolio base; its S1 trend sleeve comes from the solo "
                                 "repository's forward test 2) and some scopes have no trial log",
             source=F["report"]),
    ]
    pd.DataFrame(counts).to_csv(OUT / "trial_counts_by_scope.csv", index=False, lineterminator="\n")
    print(df.groupby(["family", "role"]).size().to_string())
    print(f"wrote {OUT / 'VARIANT_LEDGER.csv'} ({len(df)} rows) and {OUT / 'trial_counts_by_scope.csv'}")
    print("solo repository:", solo_note)


if __name__ == "__main__":
    main()
