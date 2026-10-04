# Variant ledger (reviewer item 5)

This ledger lists every variant and comparison the project computed, the role each played, its result, and whether
its evaluation period had already been seen. It also gives the documented trial counts of each scope, without adding
them together.

- **`results_2/ledger/VARIANT_LEDGER.csv`** has 78 rows, one per variant or comparison.
  - **Descriptive columns:** `id`, `family`, `parent`, `variant`, `parameters`, `purpose`, `evaluation_period`.
  - **Role columns:** `role` (one of the five roles below) and `role_in_family` (the row's role inside its own family).
  - **Evidence columns:** `period_already_observed`, `result`, `counted_in` (which documented trial count includes the
    row) and `source` (the committed file the result is read from).
- **`results_2/ledger/trial_counts_by_scope.csv`** has the documented counts per scope.
- **`results_2/ledger/build_ledger.py`** builds both files from committed files. Run it from the repository root. It exits 2 if an
  input is missing, and it writes nothing outside `results_2/ledger/`.

Nothing here reruns a strategy. Every result string is read from a committed results file. The two exceptions are
quoted from committed documents: the D-4 fix-1 alternative lag (V2-F4, from `backtests/results/v2_d4/README.md`) and
the strategy 01 review figures (S01-R2, from `strategies/01/review/VERDICT.md`).

## Roles

The main strategy is v2 T4xE1. Each row has one role relative to it.

| Role | Meaning | Rows |
|---|---|---|
| selection candidate | one of the 8 registered combinations the selection rule chose from | 8 |
| prespecified robustness | registered before any v2 return: references, the D-1 sensitivity, the falsifiers, the Deflated Sharpe, the portfolio test, the by-chair split | 7 |
| post-result diagnostic | decided after v2 results had been seen: the D-3 out-of-sample opening, the D-4 benchmarks, walk-forward selection, descriptive splits | 12 |
| implementation correction | a fix or a pipeline change: the D-4 fixes and their variants, the stance-model substitution, placebo pipeline tests, reproductions | 9 |
| independent failed or exploratory study | any other family: press conference (21 rows), strategy 01 (5), edge and portfolio study (6), solo repository (7), earlier screens (3) | 42 |

Inside the press-conference family, `role_in_family` separates:
- the one gated primary (H1-primary, G3);
- the prespecified robustness rows, diagnostics and negative control;
- the non-blind BENCH-R replication;
- the post-result strategy-series presentation;
- the exploratory H2/H3/H4 family (Holm, m = 3) and its secondary rows.

## Documented counts per scope

These counts come from different scopes. They overlap and cannot be added into a single project-wide number of trials
(last row).

| Scope | Documented count | Distinct | What it includes | Source |
|---|---|---|---|---|
| v2 Deflated Sharpe trial set | **11** | 10 | the 8 registered combinations (selection-window Sharpe) + Variant A's 3 logged trials. Row 3 of the log repeats row 2, so n = 10 is the reported sensitivity | `backtests/results/v2/summary_is.json`; `preregistration/HYPOTHESIS_v2.md` (Multiple testing) |
| v2 rows in this ledger | 36 | - | every v2 variant and comparison. These are ledger rows, not trials; 28 of them are outside the DSR set | `results_2/ledger/VARIANT_LEDGER.csv` |
| v2 D-4 metric rows | 148 | 38 series x variant | the D-4 run's rows | `backtests/results/v2_d4/metrics.csv` |
| Strategy 01 trial log | **3** | 2 | trial 1 (z-clock bug), trial 2 (spec fix), row 3 (rerun of trial 2) | `strategies/01/trials/log.csv` (byte-identical to the v2 input copy) |
| Strategy 01 review analysis rows | 280 | - | strategy x window x series rows of the independent review | `strategies/01/review/analyse/t1_results_all.csv` |
| Press conference, gated | **1** | 1 | H1-primary on the 20 confirmation meetings. ADDENDUM section 8.3: a single primary, so no multiplicity adjustment; nothing may be promoted | `preregistration/presser_ADDENDUM.md` |
| Press conference, H1/BENCH-R/H1-Q/lexicon rows | 5,700 | 36 test x variant groups | samples, symbols, cost levels and units of those groups | `backtests/results/presser_h1/summary_long.csv` |
| Press conference, H1-answer and 1 s sweep rows | 2,162 | - | 433 answer rows + 1,729 sweep rows (diagnostics) | `h1answer_summary.csv`, `h1answer_1s_sweep_summary.csv` |
| Press conference, exploratory family | **3** | 3 | H2, H3 (killed, enters at p = 1), H4; Holm m = 3. 2,160 secondary answer rows and 35 companion slopes are not counted | `backtests/presser/backtest_h234/results/family_holm.json` |
| Earlier edge and portfolio study | **117** | - | 40 carry + 36 risk premia + 13 calendar + 11 value + 17 portfolios. 12 of the 36 risk-premia variants are long-history proxies, not tradeable; 11 value diagnostics are not counted; "earlier project trials are not added" | `archive/session_outputs/edges/combine/SPEC.md` section 4; `combine/summary.json` (`dsr.n_trials` 117); component SPECs in `edges/{carry,risk_premia,calendar,value_reversal}/SPEC.md` |
| Solo repository trial log | **3,159 rows** | 1,479 names; 1,501 parameter hashes | FTE 2,890; IFC 146; IFC_EXPLORATORY 20; IFC_F 13; PCT 75; PCT_F 15 (3,134 IS rows, 25 OOS rows) | github.com/minh-stakc/gqh-flow-clock `results/trials.csv` at commit 1587f25 (sha256 5a57b85a...526c). Not in this repository: the counts are recorded in `results_2/ledger/build_ledger.py` and re-checked when `GQH_REPO` points at a clone (checked on 2026-10-04: equal) |
| Auction-cycle study | 14 | 12 eligible | 12 eligible variants + 2 diagnostics | `archive/session_outputs/auction/futures_test/SPEC.md` |
| hunt100 screen | **not countable exactly** | 24 specs | 24 backtested strategy specs, each a base rule plus 3 pre-declared variants (at most 96 runs); only 29 series are archived because large files were dropped | `archive/session_outputs/hunt100/bt_*/COMMON_SPEC.md` |
| Whole project | **not countable exactly** | - | all of the above, plus the tactical-allocation, intraday/overnight, starter-kit and forward-test work, and ideas documented outside this repository (report section 8) | see below |

**Why the counts cannot be summed.**
- **Overlapping scopes.**
  - Variant A's 3 trials appear in both the strategy 01 log and the v2 DSR set.
  - core_ER_6 is one of the edge study's 117 trials and is also the base of v2's portfolio test.
  - core_ER_6's trend sleeve S1 comes from the solo repository's forward test 2, whose search is part of that
    repository's log.
- **Different units.** The solo log counts rows: one variant appears once per period and cost multiple.
- **No trial log at all** for the gtaa, intraday, starter-kit and forward-test work.

The defensible statements are per scope: the v2 selection used 11 trials (10 distinct), the press-conference gate
used 1, and the edge study used 117. The project as a whole examined more than any one of these; its exact total is
unknown.

## v2 (main strategy)

| id | Variant | Role | Result (Sharpe, excess over T-bill) |
|---|---|---|---|
| V2-C1..C8 | T1-T4 x E1-E2 | selection candidate | T4xE1 chosen: selection 0.154, validation 0.687, full IS 0.441 (2x 0.387 < 0.5, rule FAILED); T4xE2 selection 0.151 |
| V2-R1, R2 | Variant A frozen; Variant A with 2015 warm-up | prespecified robustness (references) | full IS 0.355 and 0.400; Variant A out-of-sample -0.454 |
| V2-R3 | D-1 scheduled-only de-risk list | prespecified robustness | full IS 0.442; out-of-sample 0.6076 vs 0.6073 |
| V2-R4 | by chair | prespecified robustness | IS Yellen 0.031, Powell 0.537; OOS Powell -0.364, Warsh 2.809 |
| V2-R5 | falsifiers | prespecified robustness | selection <= 0.2 fired; 2022 share 73.93% fired |
| V2-R6 | Deflated Sharpe (11 trials) | prespecified robustness | 0.223 selection, 0.436 full IS (sensitivities: n = 10, 0.232; variance from the 8 combinations only, 0.280) |
| V2-R7 | portfolio test, in-sample | prespecified robustness | full IS 0.998 -> 1.038 |
| V2-D1..D4 | D-3 out-of-sample (T4xE1, Variant A, portfolio) and concentration splits | post-result diagnostic | T4xE1 0.607 / 2x 0.544, NW t 0.842; portfolio 0.601 -> 0.870; -0.011 without the last 20 sessions |
| V2-F1..F6 | D-4 fix 1, fix 2, both; fix-1 alternative lag; fixed Variant A; fixed portfolio | implementation correction | T4xE1 both fixes: full IS 0.446 / 0.392, OOS 0.621 / 0.554; alternative lag OOS 0.500 / 0.435 |
| V2-B1..B6 | LEXALL, T2, T0v2, rate momentum M, long 75/25 with sizing, buy-and-hold | post-result diagnostic | OOS (original): -0.302, 0.559, -0.454, -0.276, -0.881, -0.921 |
| V2-W1, W2 | walk-forward selection, original and fixed universes | post-result diagnostic | OOS 0.558 and 0.621; picks T4xE1 except T4xE2 for 2023 (and 2024 in the original universe) |
| V2-I1..I3 | stance-model substitution (36 fine-tunes, not trading trials); placebo pipeline tests; reproductions | implementation correction | no trading result; reproductions PASS |

**Was the evaluation period already seen?**
- **The 8 candidates and the prespecified rows.** Market data for 2016..2024-10 had been seen, and so had strategy 01's
  results over it. No v2 return existed when the rule was registered (19:52 UTC, 2026-10-03). Amendments 2-3 were
  written after strategy 01's out-of-sample verdict (20:26 UTC).
- **The out-of-sample window.** Its market data had been seen through strategy 01 and the edge study's later window.
  v2's own out-of-sample returns were computed once, at 01:23 UTC on 2026-10-04 (D-3), after the failed in-sample rule.
- **D-4 rows.** Everything under D-4 (05:30 UTC) was decided with every window's v2 result known.

## Press-conference family (independent of v2; G3 NO-GO)

- **H1-primary (PC-01),** the only gated test: 20 confirmation meetings, +0.50 ticks (+$3.91 per contract), t 0.170,
  one-sided p 0.4505. NO-GO.
- **Prespecified rows:**
  - the 2016-2022 and Warsh samples (PC-02);
  - exit 16:30, +30 s entry, point clock and convention clock (PC-03);
  - sensitivities 1-3 (PC-04);
  - ZF, ZN and ES (PC-05);
  - the companion slope (PC-06);
  - the cost grid (PC-07: cost levels of the same trades, not trials);
  - H1-Q (PC-08: two-sided p 0.858 confirmation, 0.555 for 2016-2022);
  - the lexicon negative control (PC-09: lex_H1 not estimable; lex_H1_raw -$32.03, p 0.170);
  - the H1-answer diagnostic (PC-10: confirmation p 0.234 / 0.611 / 0.883 at +1 / +5 / +15 min);
  - the 1 s latency sweep (PC-11: 1,729 diagnostic rows).
- **BENCH-R (PC-12 to PC-14).** This replication is non-blind: its era correlations had been seen before the ADDENDUM.
  - Gross per contract: +$27.73 (t 0.942) in 2016-2019 and -$35.31 (t -1.150) in 2020-2026.
  - Robustness exits, subsets and symbols are listed as separate rows.
- **Strategy series (PC-15).** A post-result presentation of the frozen trades. Net Sharpe in-sample / out-of-sample:
  H1 ZT -0.171 / -1.330, BENCH-R ZT -0.510 / 0.181, BENCH-R ES 0.115 / 0.712.
- **H2/H3/H4 (PC-16 to PC-21).** Exploratory and run after G3. Holm p: H2 0.878, H3 killed (p = 1), H4 0.728. The
  secondary, tier-3 and meeting-level rows are descriptive. The local replication, the stage-1 fix and the
  source-invariance check (not run) are implementation rows.

Observation status:
- H1 was blind when the ADDENDUM was written.
- 12 of the 20 confirmation meetings fall in the calendar out-of-sample window and were reported on 2026-10-03.
- The H2-H4 gate outcomes were seen in a no-price diagnostic before the stage-1 fix (Note 3).

## Strategy 01, edge study, solo repository, earlier screens

- **Strategy 01 (S01-T1..T3, S01-R1, S01-R2).**
  - The three logged trials have Sharpe 1x 0.413, 0.205 and 0.205. They enter the v2 DSR.
  - The independent review found an out-of-sample Sharpe of -0.456 for the frozen rule, net and in excess of the
    T-bill (verdict: drop).
  - The review's prespecified analyses (rate-momentum control, futures version, portfolio test) are one row.
- **Edge and portfolio study (E-1..E-6).** 117 documented trials, with each component's SPEC written before its
  results.
  - Best portfolio: broad_IV_6, IS Sharpe 1.178, DSR 0.493 with 117 trials.
  - core_ER_6: IS 0.977, later window 0.601. That later window is v2's out-of-sample window, and it had been seen.
- **Solo repository (SOLO-*).** 3,159 logged rows in six families. The archived snapshots (67 and 83 rows) are
  subsets, not additional trials.
- **Earlier screens (X-1..X-3).** hunt100 (24 specs, at most 96 runs), the auction cycle (12 + 2), and tactical,
  intraday and starter-kit work. All were rejected (report section 8). Only the auction study has an exact count.
