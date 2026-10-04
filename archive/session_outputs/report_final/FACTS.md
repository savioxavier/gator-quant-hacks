# FACTS: every number the final quant note may quote, with its source

Built 2026-10-04 (UTC) read-only from the team repo clone, branch `review/strategy-01`. HEAD when read: `c13c1bf`
(two commits after `8a4d3be`: `0a941c6` H2/H3/H4 local summary, `c13c1bf` local feature tables; neither changes a
result file used here). All paths are repo-relative. No price level appears in this file.

**How to read a row.** `Source` is the committed file; `Field` is the JSON key, CSV row/column or document section.
**[D]** = derived here by simple arithmetic or a filter on a committed file (the method is given; nothing was
re-estimated). **[X]** = committed in the repo but outside the source set named for this task (strategy 01 review,
nlp, frozen positions); usable, but say where it comes from. Values are given at full precision where useful and
with the rounding the note should use.

Abbreviations: IS = in-sample, OOS = out-of-sample (2024-10-03..2026-10-02, 501 sessions), 1x / 2x = net of 1x / 2x
costs, NW t = Newey-West t of the mean daily return, DD = drawdown, CM = measured half-spread at entry + exit
(no fee), CMF = CM + $2.00/side fee, C2/C4 = 2/4 ticks per side, HPG = HiPerGator.

---

## 0. What changed against REPORT_DRAFT.md v1 (read first)

1. **v2 OOS now exists.** Deviation D-3 opened the OOS window once, for reporting only. Every "OOS not evaluated"
   phrase in the draft (Summary headline, Table 1 OOS row, Fig. 1 caption, s5, s8 failed ideas, A2, checklist) is
   now wrong and must become "evaluated once under D-3; the failed decision rule stands" (s7 below).
2. **H1 G3 = NO-GO** is computed and committed (s11). All H1 placeholders can be filled; the "no H1 stance result is
   quoted" exposure box is obsolete.
3. **H2/H3/H4 were run** as exploratory, post-NO-GO tests pre-registered after G3 (s15). The draft's "run only if
   G3 = GO" must change to that label.
4. **Press-conference trades now have IS/OOS strategy metrics** (Sharpe, DD, turnover) under D-3's last section
   (s13). The draft's "Annualised Sharpe is withheld (ADDENDUM s5)" must be reworded: the plan withheld it; D-3 shows
   it as a presentation with no inferential weight.
5. Corrections to specific draft numbers and claims are listed in s20.

---

## 1. Statements the note must make (honesty list)

| ID | Statement (quote-ready) | Source | Field |
|---|---|---|---|
| H-1 | v2 (T4xE1) failed its own pre-registered decision rule: full in-sample Sharpe at 2x costs 0.387, below the 0.5 gate (validation 0.687 > 0 passed). The verdict stands. | `backtests/results/v2/summary_is.json` | `full_is_sharpe_net2x` 0.38717, `validation_sharpe_net1x` 0.68683, `decision_rule_passed` false; `backtests/results/v2/oos_not_evaluated.json` |
| H-2 | Deviation D-3 opened the OOS window once, for reporting only; it cannot reverse the verdict; nothing was re-chosen. | `preregistration/v2_DEVIATION_D3_OOS.md`; `backtests/results/v2_oos/run/oos_chosen.json` | `authorised_by`, `evaluated_once_utc` 2026-10-04T01:22:57Z |
| H-3 | OOS Sharpe 0.607 net 1x / 0.544 net 2x / 0.687 gross is not significant (NW t 0.84). | `backtests/results/v2_oos/metrics.csv` | T4xE1, oos, `sharpe`, `nw_t` 0.8418 |
| H-4 | The OOS gain comes from the last months: -0.36 over the 409 Powell sessions, +2.81 over the 92 Warsh sessions, -0.01 without the last 20 sessions; five days carry 108% of the OOS daily-return sum. | `backtests/results/v2_oos/oos_concentration.csv`; `run/by_chair_oos.csv` | rows "oos, Powell", "oos, Warsh", "without its last 20 days", "share ... 5 best days" 1.0792 |
| H-5 | The portfolio gain (core_ER_6 0.601 -> 0.870 at 1x) is also a Warsh-months effect: Powell months 0.97 -> 0.94, Warsh months -1.34 -> 0.53. | `backtests/results/v2_oos/oos_concentration.csv` | core_ER_6 / core_ER_6+T4xE1, Powell and Warsh rows |
| H-6 | H1-primary G3 = NO-GO: n = 20, mean +0.50 ticks gross ($3.91), one-sided sign-flip p 0.45, 90% block-bootstrap CI [-4.06, +5.30] ticks. | `backtests/results/presser_h1/key_results.json` | `H1-primary (stance)`: `n`, `mean`, `mean_usd`, `wb_p_one`, `bb_ci90_lo/hi`, `decision` |
| H-7 | H2 (voice) not detected; H3 (face) killed by its G4 variance gate; H4 (combined vs text) not detected (Clark-West t 0.73, one-sided p 0.24, OOS R^2 vs text-only -0.004). | `backtests/presser/backtest_h234/results/family_holm.json`, `results/h4_results.json`, `qa/kill_switches.json` | s15 |
| H-8 | The meeting-level H4 row (t 2.39, n = 10) is descriptive, outside Holm, and both meeting-level models forecast worse than zero; it is not a finding. | `backtests/presser/backtest_h234/results/h4_results.json` | `meeting_ZT`: `t` 2.3875, `n` 10, `oos_r2_C_vs_zero` -0.489, `oos_r2_T_vs_zero` -1.513 |
| H-9 | Neither press-conference strategy covers its costs in sample on its designated instrument (ZT): H1 net 1x Sharpe -0.17 IS / -1.33 OOS; BENCH-R -0.51 IS / +0.18 OOS (-0.02 at 2x). | `backtests/results/presser_strategy/key_metrics.json`, `tables.md` | s13 |
| H-10 | H2/H3/H4 are exploratory, pre-registered after the G3 NO-GO; in the locked register they stay at p = 1; they cannot rescue G3 or support a trading claim. | `preregistration/presser_H2H3H4_EXPLORATORY.md` s0; `family_holm.json` `note` | label text |
| H-11 | The press-conference "OOS" is a calendar split, not a fresh holdout: 12 of the 20 G3 meetings fall in it and were reported on 2026-10-03. | `backtests/results/STRATEGY_RESULTS.md` s1; `backtests/results/presser_strategy/README.md` | "calendar split" bullet |
| H-12 | BENCH-R is non-blind (its era correlations were seen before the ADDENDUM). | `preregistration/presser_ADDENDUM.md` s12 | "BENCH-R is non-blind" |
| H-13 | Disclosures: (a) the public commit of the pre-registration (537c483) came after the v2 in-sample run and before any H1 result was viewed; (b) development voice/face tables for 20190501 and 20200303 were written 22:15-22:38 UTC, before the H2-H4 pre-registration; (c) the 2023-06-14 video asset is the 2023-07-26 conference; (d) a stage-1 bug (WAV length key) was fixed before any join, gates unchanged; (e) v2 OOS opened once under D-3 although the rule failed. | `preregistration/PREREG_LOG.md`; `presser_H2H3H4_NOTE1.md` s1; `NOTE2.md`; `NOTE3.md`; `v2_DEVIATION_D3_OOS.md` | timeline rows |
| H-14 | v2 Amendments 2 and 3 were written after strategy 01's OOS verdict was committed (bf880da), so the team knew how a lexicon signal did in 2024-26 before those amendments. | `preregistration/PREREG_LOG.md`; git `bf880da` 2026-10-03 20:26:48 UTC | timeline |
| H-15 | AI disclosure, exact text: "AI coding assistants were used; the team reviewed and is responsible for all code and claims." | task rules | - |

---

## 2. Protocol timeline and hashes

Git commit times converted from -04:00 to UTC (`git log`); file-stated times from the files themselves.

| ID | Event | Time (UTC) | Source |
|---|---|---|---|
| T-1 | v2 pre-registration written (HYPOTHESIS_v2.md) | 2026-10-03 19:52 | `preregistration/PREREG_LOG.md` |
| T-2 | Amendment 1 (2016+ windows, by-chair reporting) | 19:53 | PREREG_LOG |
| T-3 | Strategy 01 replication and OOS verdict committed | 20:26:48 | git `bf880da` |
| T-4 | Amendment 2 + press-conference Deviation D1 (chrono-BERT replaces gated FOMC-RoBERTa) | 21:12 logged (file text "about 21:20") | PREREG_LOG; `HYPOTHESIS_v2.md` |
| T-5 | Clarification (2015 warm-up scored by model 2015) | 21:35 | PREREG_LOG |
| T-6 | Press-conference ADDENDUM written (no return computed) | 21:45 | PREREG_LOG; `presser_ADDENDUM.md` header |
| T-7 | Amendment 3 + D1a (labels re-dated from source documents) | 21:50 | PREREG_LOG |
| T-8 | Amendment 3 code committed | 22:37:01 | git `0fd707f` |
| T-9 | DEVIATIONS.md D-1, D-2 (before any v2 return on real scores) | 22:40 | PREREG_LOG; `DEVIATIONS.md` |
| T-10 | v2 in-sample run; rule failed | about 23:10 | PREREG_LOG |
| T-11 | Public commit of the pre-registration records | 23:11:18 (PREREG_LOG says "about 23:15") | git `537c483` |
| T-12 | H2/H3/H4 exploratory pre-registration (post-G3) | 23:26:20 | git `64ceb24`; NOTE1 s1 |
| T-13 | Local voice/face tables computed (64 Powell meetings) | 23:45:57 .. 00:44:44 (10-04) | NOTE1 s2 |
| T-14 | Note 1 / Note 2 committed | 00:49:41 / 00:55:16 (Note 2 file says "about 00:58") | git `815e574`, `e08cc71` |
| T-15 | D-3 committed, before any OOS return | 01:10:04 (file says "about 01:15") | git `ee28b16`; STRATEGY_RESULTS s9 item 13 |
| T-16 | Note 3 (stage-1 fix) committed | 01:16:17 (file and PREREG_LOG say "about 01:35"; see s20) | git `1c8c9e1` |
| T-17 | H2/H3/H4 local run, once | 01:18:57 .. 01:19:35, exit 0 | `backtests/presser/H234_LOCAL_SUMMARY.md` s1 |
| T-18 | v2 OOS run, once | 01:22:55 .. 01:22:57, exit 0 | `backtests/results/v2_oos/RUN_LOG.md` "Run" |
| T-19 | Full strategy results committed | 01:43:18 | git `6a61ef9` |
| T-20 | H2/H3/H4 HiPerGator reference results committed | 02:16:27 | git `69839cf` |
| T-21 | v2 reproduced on HiPerGator (PASS) | 02:44:51; committed 02:49:16 | `v2_oos/hpg_reproduction/reproduce_report.json` `reproduced_utc`; git `8a4d3be` |

| ID | File | SHA-256 (cite first 8) | Source |
|---|---|---|---|
| T-22 | HYPOTHESIS_v2.md (Amendments 1-3) | 464f8a5b...8eb2e | PREREG_LOG; `summary_is.json` `prereg_sha256_checked` |
| T-23 | v2_DEVIATION_D3_OOS.md | 97585d3c...af1c69 | PREREG_LOG; RUN_LOG |
| T-24 | presser_ADDENDUM.md | 1921b2ca...2dc4 | PREREG_LOG; `presser_h1/run_meta.json` `addendum_sha256` |
| T-25 | presser_team_FINAL_PLAN.md | 88cc54a8...51846 | PREREG_LOG |
| T-26 | presser_DEVIATION_D1.md (with D1a) | 660d06a8...9ebd79 | PREREG_LOG |
| T-27 | DEVIATIONS.md | 48e6643d...e4796a | PREREG_LOG |
| T-28 | presser_H2H3H4_EXPLORATORY.md | e030af98...dca6d0 | PREREG_LOG; `backtest_h234/results/run_meta.json` `prereg_sha256` |
| T-29 | v2 document scores (doc_scores.parquet) | 0e0c1ca7...ba0 | `summary_is.json` `doc_scores_sha256` |

---

## 3. Data and universe counts

| ID | Fact | Value | Source | Field |
|---|---|---|---|---|
| D-1 | v2 documents scored | 1,098: 828 speeches, 97 FOMC statements, 94 minutes, 79 press-conference transcripts | `backtests/results/summary.json` | `stance_model.v2_adapter.n_docs`, `docs_by_type` |
| D-2 | Scored text units | 5,225: 2,026 Chair answers, 2,026 questions, 828 speeches, 97 statements, 94 minutes, 79 presser docs, 75 presser statements | `summary.json` | `stance_model.merge_meta.docs_by_source` |
| D-3 | Sentences scored (all years) | 159,353 [D: sum of `n_sentences`] | `summary.json` | `stance_model.years.*.n_sentences` |
| D-4 | Press conferences / answers | 75 meetings; 2,026 answers; 1,977 scorable by the chrono model | `summary.json` | `presser_adapter.n_meetings`, `n_answers`, `n_answers_scorable_chrono` |
| D-5 | Meetings with H1 defined by sample | confirmation (Powell 2023-26) 27, 2016-2022 45, Warsh 3 | `summary.json` | `presser_adapter.H1_by_sample.count` |
| D-6 | Meeting list [X] | 75 meetings: 73 scheduled + 2 unscheduled (2020-03-03, 2020-03-15, outside the market window); chairs Powell 64, Yellen 8, Warsh 3 | `backtests/presser/backtest/positions/meetings_positions.csv` | `scheduled`, `market_window_covers_event`, `chair` |
| D-7 | Timing-eligible meetings [X] | 62 of 75 (13 dropped); 2016-2022 39 of 45, confirmation 20 of 27, Warsh 3 of 3 | `meetings_positions.csv`; `preregistration/presser_ADDENDUM.md` s2 | `drop_timing`, `sample_role` |
| D-8 | Confirmation drops (7) | distorted captions 2023-02-01; no captions 2023-06-14, 2023-07-26, 2023-11-01, 2023-12-13, 2024-03-20, 2025-12-10 | `presser_ADDENDUM.md` s2 | "Confirmation drops" |
| D-9 | Confirmation timing-eligible (20) | 2023: 03-22, 05-03, 09-20; 2024: 01-31, 05-01, 06-12, 07-31, 09-18, 11-07, 12-18; 2025: 01-29, 03-19, 05-07, 06-18, 07-30, 09-17, 10-29; 2026: 01-28, 03-18, 04-29 | `presser_ADDENDUM.md` s2 | list |
| D-10 | Warsh conferences | 2026-06-17, 2026-07-29, 2026-09-16 (text only, descriptive) | `presser_ADDENDUM.md` s2 | Samples table |
| D-11 | Degraded Databento days (registered sensitivity) | 2024-09-18, 2025-09-17 | `presser_ADDENDUM.md` s2; `meetings_positions.csv` `databento_degraded_day` | - |
| D-12 | Caption-video zero minus scheduled start [D][X] | median 28.8 s, n = 63, range -15.2..110.0 s | `meetings_positions.csv` | `v0_minus_sched_tv_s` |
| D-13 | Start uncertainty on eligible meetings [D][X] | median 9.3 s, range 8.5-17.7 s (n = 62) | `meetings_positions.csv` `start_unc_s`; ADDENDUM 1.1 states 8.5-17.7 s | - |
| D-14 | TV delay assumption | 11 s assumed (plausible 3-20 s); no true wall clock | `presser_ADDENDUM.md` s11, s1.1 | - |
| D-15 | Market data | Databento GLBX.MDP3 ohlcv-1m and ohlcv-1s for ZT/ZF/ZN/ES, bbo-1s for ZT/ZN/ES, 13:30-16:30 ET on the 75 presser days; no ZF quotes; no MBP-1 depth; no 2011-2015 pressers | `presser_ADDENDUM.md` s0, s1.3, s11 | - |
| D-16 | Bad quote records skipped | 1,593 | `backtests/results/presser_h1/run_meta.json` | `bad_quote_records_skipped` |
| D-17 | ZT tick and contract | 1/128 point ($15.625) through the 2018-12-19 presser; 1/256 ($7.8125) from the 2019-01-30 presser; CME cut on trade date 2019-01-14 (SER-8171); $200k face. ZF $7.8125, ZN $15.625, ES $12.50 per tick | `presser_ADDENDUM.md` s1.2 | tick table |
| D-18 | ZT has a 15:59 bar on 74 of 74 trading days; a 16:29 bar on 65 of 74 | | `presser_ADDENDUM.md` s3.5 | - |
| D-19 | v2 window lengths (sessions) | selection 1,259; validation 943; full IS 2,202; OOS 501 | `backtests/results/v2_oos/metrics.csv` | `n_days` |
| D-20 | First position / first valid z | T4xE1 2015-12-31; T0f (Variant A frozen) z from 2011-12-30; T1-T4, T0v2 from 2015-12-31 | `backtests/results/v2/summary_is.json` | `first_position_dates`, `first_valid_z` |
| D-21 | Chair tenures used in code | Yellen 2014-02-03..2018-02-03; Powell 2018-02-05..2026-05-21; Warsh from 2026-05-22 | `backtests/results/v2/check/check.json` | `chairs` |
| D-22 | Chair split of sessions | IS: Yellen 526, Powell 1,676; OOS: Powell 409, Warsh 92 | `v2/by_chair_is.csv`; `v2_oos/run/by_chair_oos.csv` | `n_days` |
| D-23 | FOMC de-risk list | 101 dates from 2015: 93 scheduled + 8 unscheduled (2019-10-11; 2020-03-03, 03-15, 03-19, 03-23, 03-31, 08-27; 2025-08-22) | `preregistration/DEVIATIONS.md` D-1 | table |
| D-24 | Speech counts per year (strategy 01 corpus) [X] | 44 (2016) -> 117 (2025); kept speeches 27 -> 47 a year (IS -> OOS mean) | `strategies/01/review/extend/counts_per_year.csv` `n_docs`; `strategies/01/review/analyse/x2_speech_volume.csv` `kept_docs_per_year` 26.96 / 46.60 | - |
| D-25 | Recordings archived for H2/H3 [X] | 95 meetings, 82.4 video-hours, 62.8 GiB | `hpg/fedpress_pkg/manifest/README.md` "All" row | - |
| D-26 | USMPD check, statement window [D] | corr(ZT 13:50-14:20 return, USMPD statement-window UST2Y change) = -0.9955, n = 70 traded meetings | `presser_h1/tables/benchr_per_meeting_ZT.csv` `R` joined to `presser_h1/benchr_usmpd_ust2y.csv` `usmpd_stmt_UST2Y` | - |

---

## 4. Stance-model diagnostics

Source for every row: `backtests/results/summary.json` (`stance_model.years`, `stance_model.label_audit_D1a`) and the
same table in `backtests/results/summary.md`. 3 seeds (42, 43, 44) x 12 years = 36 fine-tunes.

| Model year | Docs | Sentences | Val macro-F1 by seed | Mean F1 [D] | Seed label agreement | Train rows | Verbatim in docs dated >= Y | First seen >= Y |
|---|---|---|---|---|---|---|---|---|
| 2015 | 74 | 8,595 | 0.568, 0.564, 0.598 | 0.577 | 0.851 | 1,606 | 21 | 21 |
| 2016 | 222 | 8,906 | 0.631, 0.625, 0.599 | 0.618 | 0.892 | 1,673 | 18 | 3 |
| 2017 | 251 | 10,279 | 0.599, 0.613, 0.621 | 0.611 | 0.863 | 1,738 | 23 | 2 |
| 2018 | 278 | 9,145 | 0.608, 0.573, 0.571 | 0.584 | 0.851 | 1,836 | 23 | 2 |
| 2019 | 571 | 14,145 | 0.580, 0.611, 0.545 | 0.579 | 0.897 | 1,901 | 29 | 2 |
| 2020 | 439 | 13,505 | 0.629, 0.619, 0.623 | 0.624 | 0.875 | 2,016 | 24 | 2 |
| 2021 | 494 | 15,314 | 0.654, 0.650, 0.647 | 0.650 | 0.883 | 2,184 | 30 | 2 |
| 2022 | 462 | 12,762 | 0.645, 0.623, 0.571 | 0.613 | 0.858 | 2,344 | 12 | 1 |
| 2023 | 629 | 16,186 | 0.653, 0.650, 0.653 | 0.652 | 0.884 | 2,480 | 8 | 1 |
| 2024 | 658 | 18,750 | 0.660, 0.649, 0.684 | 0.664 | 0.865 | 2,480 | 6 | 0 |
| 2025 | 702 | 20,078 | 0.659, 0.669, 0.655 | 0.661 | 0.901 | 2,480 | 5 | 0 |
| 2026 | 445 | 11,688 | 0.659, 0.669, 0.653 | 0.660 | 0.907 | 2,480 | 4 | 0 |

| ID | Fact | Value | Source | Field |
|---|---|---|---|---|
| S-1 | Validation macro-F1 range over 36 models | 0.545-0.684 [D: min/max of the seed values] | `summary.json` | `years.*.seed_val_macro_f1` |
| S-2 | Label rows dated from source documents | 2,480 of 2,480: exact 2,281; annotated-sheet join 192; normalised-whitespace 7 | `summary.json` | `label_audit_D1a.label_dates.by_method` |
| S-3 | Label rule in use | "true" (source-document date) | `summary.json` | `label_audit_D1a.rule_in_use` |
| S-4 | Dataset year disagrees with source-document year [X] | 2,336 of 2,480 rows | `nlp/README.md` (also `hpg/fedpress_pkg/docs/TEXT.md`) | - |
| S-5 | Model-2015 training rows found verbatim in later documents: literal dataset years vs corrected dates [X] | 491 vs 21 | `nlp/README.md` table (row `dataset`, 2015) vs `summary.json` `per_model_year.2015.verbatim_in_corpus_doc_dated_ge_Y` | - |
| S-6 | Reference F1 for FOMC-RoBERTa (combined) | about 0.71 (presser-only about 0.53-0.55) | `preregistration/presser_team_FINAL_PLAN.md` s1 (citing Shah, Paturi and Chava 2023) | - |
| S-7 | Fixed training settings | 15% stratified validation (seed 0); lr 2e-5; batch 16; max length 256; <= 8 epochs, patience 2 on macro-F1; weight decay 0.01; 10% warmup; seeds 42/43/44; base manelalab/chrono-bert-v1-<min(Y-1,2024)>1231 (ModernBERT-base, about 150M parameters) | `preregistration/HYPOTHESIS_v2.md` Amendment 2 and clarification | - |
| S-8 | Mean stance score by document type (descriptive) | statements -0.193, minutes -0.080, pressers -0.053, speeches -0.035 | `summary.json` | `v2_adapter.rob_score_mean_by_type` |
| S-9 | Cross-check of presser scores vs team merge | max abs diff 0.0 on all 7 score columns | `summary.json` | `presser_adapter.crosscheck_vs_team_merge` |

---

## 5. v2 in-sample: all combinations

Source: `backtests/results/v2/windows_all.csv` (selection rows identical to `v2/selection.csv`). Sharpe = net excess
over T-bill, mean/sd x sqrt(252).

| Combo | Selection 1x | Validation 1x | Full IS 1x | Full IS 2x | Full IS gross |
|---|---|---|---|---|---|
| T1xE1 | -0.582 | 0.974 | 0.196 | 0.150 | 0.256 |
| T1xE2 | -0.358 | 0.660 | 0.197 | 0.132 | 0.263 |
| T2xE1 | -0.346 | 0.825 | 0.246 | 0.194 | 0.312 |
| T2xE2 | -0.177 | 0.456 | 0.171 | 0.097 | 0.245 |
| T3xE1 | -0.205 | 0.804 | 0.269 | 0.212 | 0.339 |
| T3xE2 | -0.065 | 0.635 | 0.298 | 0.222 | 0.373 |
| **T4xE1 (chosen)** | **0.154** | **0.687** | **0.441** | **0.387** | **0.507** |
| T4xE2 | 0.151 | 0.707 | 0.453 | 0.377 | 0.528 |
| T0fxE1 = Variant A frozen (reference) | -0.013 | 0.691 | 0.355 | 0.312 | 0.411 |
| T0v2xE1 = Variant A, 2015 warm-up (reference, IS only) | 0.153 | 0.638 | 0.400 | 0.358 | 0.454 |

| ID | Fact | Value | Source | Field |
|---|---|---|---|---|
| V-1 | Selection rule | highest net 1x Sharpe in selection window 2016-01-04..2020-12-31 -> T4xE1 | `summary_is.json` | `chosen` |
| V-2 | All six stance-model-only combos (T1-T3) negative in selection | -0.582 .. -0.065 | `v2/selection.csv` | `sharpe_net1x` |
| V-3 | Validation vs the team's 0.7 target | 0.687, short by 0.013 | `summary_is.json` | `validation_vs_target_0.7` -0.01317 |
| V-4 | T4xE2 full IS detail (scalable alternative) | 1x 0.453, 2x 0.377; ann. return (arith) 2.75%; vol 6.08%; max DD -12.4%; turnover 46.0x/yr | `v2/windows_all.csv` | T4xE2, full_is |
| V-5 | T4 validation equals the frozen lexicon's | T4xE1 0.687 vs Variant A 0.691 | `v2/windows_all.csv` | validation rows |

### 5a. T4xE1 by window and cost basis (IS)

Source: `backtests/results/v2_oos/metrics.csv` (rows T4xE1; IS rows reproduce `v2/windows_all.csv` to 1e-16, per
`v2_oos/consistency.json`). Max DD here is the `metrics.csv` convention (from the first day's close); see V-30.

| Window | Basis | Ann. return arith | geo | Vol | Sharpe | Max DD | Hit | Turnover/yr | NW t |
|---|---|---|---|---|---|---|---|---|---|
| Selection 2016-01-04..2020-12-31 | 1x | 1.25% | 0.92% | 8.11% | 0.154 | -16.1% | 49.4% | 35.0 | 0.37 |
| | 2x | 0.43% | 0.10% | 8.11% | 0.053 | -17.1% | 48.9% | 35.0 | 0.13 |
| | gross | 2.18% | 1.87% | 8.11% | 0.269 | -15.05% | 49.9% | 35.0 | 0.65 |
| Validation 2021-01-04..2024-10-02 | 1x | 10.00% | 9.35% | 14.56% | 0.687 | -17.8% | 50.4% | 15.9 | 1.45 |
| | 2x | 9.67% | 8.99% | 14.56% | 0.664 | -17.8% | 50.3% | 15.9 | 1.40 |
| | gross | 10.50% | 9.90% | 14.56% | 0.721 | -17.7% | 50.4% | 15.9 | 1.52 |
| Full IS 2016-01-04..2024-10-02 | 1x | 5.00% | 4.45% | 11.33% | 0.441 | -18.8% | 49.8% | 26.8 | 1.41 |
| | 2x | 4.39% | 3.82% | 11.33% | **0.387** | -21.7% | 49.5% | 26.8 | 1.24 |
| | gross | 5.74% | 5.24% | 11.33% | 0.507 | -17.7% | 50.1% | 26.8 | 1.62 |

(The registered validation window starts 2021-01-01; its first session is 2021-01-04. `v2_oos/README.md` and
`reproduce_report.json` print 2021-01-01; `metrics.csv` prints 2021-01-04. Both are right.)

---

## 6. v2 falsifiers, Deflated Sharpe, diagnostics, sensitivities

| ID | Fact | Value | Source | Field |
|---|---|---|---|---|
| V-6 | Falsifier: selection Sharpe <= 0.2 | FIRES (0.154) | `v2/summary_is.json` | `falsifiers.selection_sharpe_le_0.2` true |
| V-7 | Falsifier: validation <= 0 | does not fire (0.687) | same | `validation_le_0` false |
| V-8 | Falsifier: > half of IS P&L from 2022 | FIRES: 73.9% (0.3227 of 0.4365 summed daily P&L) | same | `share_full_is_pnl_from_2022` 0.73929, `pnl_2022_sum`, `full_is_pnl_sum` |
| V-9 | Falsifier: T3 (momentum-orthogonal) ~ 0 while T1/T2 good | does not fire: T3 tracks T2 (corr of z 0.975); full IS T3xE1 0.269 vs T2xE1 0.246, T1xE1 0.196 | same | `corr_zT2_zT3_full_is` 0.97541; `T3_vs_T1_T2` |
| V-10 | Falsifier: net Sharpe <= 0 at 2x | does not fire (0.387) | same | `net2x_le_0` false |
| V-11 | corr(C_T2, rate momentum M), full IS | 0.186 | same | `corr_CT2_M_full_is` 0.18617 |
| V-12 | T3 momentum beta at last IS date | 0.434 | same | `T3_beta_last` |
| V-13 | Deflated Sharpe, 11 trials (8 combos + Variant A's 3 logged trials) | selection window 0.223; full IS 0.436 (SR0 0.495 annualised; var of trial SRs 0.0932) | same | `dsr.selection_window.dsr` 0.22251, `dsr.full_is.dsr` 0.43606, `sr0_ann`, `var_sr_ann` |
| V-14 | DSR sensitivities | n = 10 dedup 0.232; variance from 8 combos only 0.280; PSR vs 0 (selection) 0.634 | same | `dsr.sens_n10_dedup`, `sens_var_from_8_combos_only`, `psr_vs_0_selection` |
| V-15 | DSR unchanged by D-3 | 0.2225 / 0.4361 | `v2_oos/README.md` "Read the OOS number with this" | - |
| V-16 | IS correlation of T4xE1 with core_ER_6 | 0.025 | `summary_is.json` | `corr_chosen_vs_core_ER_6_full_is` 0.0250 |
| V-17 | By chair, IS (descriptive) | T4xE1: Yellen 0.031 (2x -0.073), Powell 0.537 (2x 0.494); Variant A frozen: Yellen -0.624, Powell 0.618 | `v2/by_chair_is.csv` | `sharpe_net1x`, `sharpe_net2x` |
| V-18 | D-1 sensitivity, scheduled-only de-risk list (93 dates), IS | selection 0.156, validation 0.687, full IS 0.442 (2x 0.388) vs registered 0.154 / 0.687 / 0.441 (0.387) | `v2/sens_scheduled_only_is.csv` | `sharpe_net1x`, `sharpe_net2x` |

---

## 7. v2 out-of-sample (D-3, evaluated once)

| ID | Fact | Value | Source | Field |
|---|---|---|---|---|
| V-19 | T4xE1 OOS Sharpe 1x / 2x / gross | 0.6073 / 0.5435 / 0.6866 -> **0.607 / 0.544 / 0.687** | `v2_oos/run/oos_chosen.json`; `v2_oos/metrics.csv` | `sharpe_net1x`, `sharpe_net2x`, `sharpe_gross` |
| V-20 | OOS ann. excess return (arith) 1x / 2x / gross | 3.82% / 3.42% / 4.32% (geo 3.69% / 3.28% / 4.21%) | `v2_oos/metrics.csv` | `ann_return_arith`, `ann_return_geo` |
| V-21 | OOS vol | 6.30% | same | `ann_vol` 0.06297 |
| V-22 | OOS max DD (metrics.csv convention) 1x / 2x / gross | -6.65% / -6.78% / -6.51% | same | `max_drawdown` |
| V-23 | OOS max DD from starting NAV (STRATEGY_RESULTS convention) 1x / 2x / gross | -7.4% / -7.5% / -7.2% (T4xE1 lost 0.78% on 2024-10-03) | `backtests/results/STRATEGY_RESULTS.md` s3.1 dagger note, s9 item 2 | - |
| V-24 | OOS turnover | 17.7x NAV a year (one-way, roll trades included) | `v2_oos/metrics.csv` | `turnover_per_year` 17.66 |
| V-25 | OOS hit rate | 49.9% (1x) | same | `hit_rate` |
| V-26 | OOS NW t 1x / 2x / gross | 0.84 / 0.75 / 0.95 | same | `nw_t` |
| V-27 | OOS total return incl. T-bill (geo) | 7.9% a year | same | `ann_total_return_geo` 0.0788 |
| V-28 | OOS compounded excess return | +7.5% (whole window) | `v2_oos/oos_concentration.csv` | "oos, all days" `cum_excess_return` 0.0748 |
| V-29 | OOS by chair (pre-declared) | Powell 2024-10-03..2026-05-21: 409 days, Sharpe -0.364 (2x -0.453), cum -3.1%; Warsh 2026-05-22..2026-10-02: 92 days, Sharpe 2.809 (2x 2.788), cum +10.9% | `v2_oos/run/by_chair_oos.csv`; `oos_concentration.csv` | `sharpe_net1x`, `cum_excess_return` |
| V-30 | Drop-last-sessions check (descriptive, written after the result) | without last 1: 0.588; last 5: 0.410; last 10: 0.170 (cum +1.7%); last 20: -0.011 (cum -0.5%) | `oos_concentration.csv` | rows "without its last N days" |
| V-31 | OOS by calendar year (descriptive) | Q4 2024 (62 days): cum -6.5%, Sharpe -3.32; 2025: cum +2.0%, 0.58; 2026 to 10-02: cum +12.7%, 2.02 | `oos_concentration.csv` | "oos, calendar 2024/2025/2026" |
| V-32 | Five best OOS days | 108% of the OOS daily-return sum; dates 2026-09-23, 2025-10-10, 2024-11-25, 2026-09-24, 2026-09-10; two of them (09-23, 09-24) while the book held its capped short-TLT position | `oos_concentration.csv` `value` 1.0792, `days`; `v2_oos/README.md` | - |
| V-33 | OOS sensitivity, scheduled-only de-risk list | 0.6076 vs 0.6073 | `v2_oos/run/sens_scheduled_only_oos.csv` | `sharpe_net1x` |
| V-34 | OOS correlation of T4xE1 with core_ER_6 | -0.16 | `v2_oos/README.md` (portfolio paragraph) | text |
| V-35 | Run lock | any further run refused (tested after the run: exit 1) | `v2_oos/README.md`; STRATEGY_RESULTS s8 | - |

---

## 8. References: Variant A (frozen strategy 01) and strategy 01

| ID | Fact | Value | Source | Field |
|---|---|---|---|---|
| V-36 | Variant A frozen (T0fxE1), full IS 2016-01-04..2024-10-02 | ann. 4.18%, vol 11.77%, Sharpe 0.355 / 0.312 / 0.411 (1x / 2x / gross), max DD -20.7%, turnover 23.2 | `v2_oos/metrics.csv` | VariantA_frozen(T0fxE1), full_is |
| V-37 | Variant A frozen, OOS (v2 harness) | ann. -4.95% (2x -5.47%), vol 10.90%, Sharpe -0.454 / -0.502 / -0.399, max DD -15.6% (start-NAV convention -16.6%), turnover 23.7, NW t -0.66 | `v2_oos/metrics.csv`; STRATEGY_RESULTS s3.2 | oos rows |
| V-38 | Variant A frozen, OOS by chair | Powell -0.744; Warsh +2.341 | `v2_oos/run/by_chair_oos.csv` | `sharpe_net1x` |
| V-39 | Strategy 01, own engine, IS 2011-12-30..2024-10-02 [X] | ann. 2.34%, vol 11.16%, Sharpe 0.210 / 0.162 (1x / 2x), gross 0.272, max DD -33.5%, turnover 24.5 | `strategies/01/review/analyse/t1_results_all.csv` | tone, IS, `ex_net1x`, `ex_net2x`, `ex_gross` |
| V-40 | Strategy 01, OOS 2024-10-03..2026-10-02 [X] | ann. -4.97%, vol 10.91%, Sharpe -0.456 / -0.502, max DD -15.6%, turnover 23.3 | same | tone, OOS, `ex_net1x`, `ex_net2x` |
| V-41 | Strategy 01, other verdict numbers [X] | IS ex-2022 0.060; 2022 supplies 75% of IS P&L; IS bootstrap 90% [-0.20, 0.60]; OOS 90% interval [-1.2, 0.3]; Q4 2024 -11.8% (book about 0.96 long TLT while 2-year yields rose 62 bp); OOS Sharpe without that quarter 0.14; consensus corr 0.53 with the 2-year yield; alpha over DGS2-change control 2.3%/yr, t 0.84, beta 0.31; futures version IS 0.36 / OOS 0.10 (ZN leg 0.005), gross cap binds 54% of days | `strategies/01/review/VERDICT.md` | text and table |

Note: strategy 01 OOS -0.456 (own engine, z clock from 2011) and Variant A frozen OOS -0.454 (v2 harness) are the
same frozen rule in two harnesses. Use -0.454 next to v2 rows and -0.456 for the strategy 01 verdict, and say which.

---

## 9. Portfolio test (core_ER_6 + T4xE1, pre-declared)

Source: `backtests/results/v2_oos/metrics.csv` (rows core_ER_6, core_ER_6+T4xE1); IS rows equal `v2/portfolio.csv`;
OOS rows equal `v2_oos/run/portfolio_oos.csv`. Fourth sleeve, equal risk, 6% target, trailing covariance, leverage
cap 4, month-end decisions applied from d+2.

| Window | core_ER_6 Sharpe 1x / 2x / gross | + T4xE1 Sharpe 1x / 2x / gross | core ann. / vol / max DD | + T4xE1 ann. / vol / max DD |
|---|---|---|---|---|
| Selection | 1.062 / 0.940 / 1.183 | 0.928 / 0.778 / 1.084 | 6.52% / 6.15% / -7.3% | 5.76% / 6.20% / -6.2% |
| Validation | 0.912 / 0.795 / 1.030 | 1.185 / 1.083 / 1.293 | 5.63% / 6.17% / -7.5% | 7.31% / 6.17% / -7.7% |
| Full IS | 0.998 / 0.878 / 1.118 | 1.038 / 0.909 / 1.173 | 6.14% / 6.16% / -7.5% | 6.42% / 6.19% / -7.7% |
| **OOS** | **0.601 / 0.456** / 0.746 | **0.870 / 0.703** / 1.043 | 3.45% / 5.74% / -4.7% | 4.97% / 5.72% / -5.3% |

| ID | Fact | Value | Source | Field |
|---|---|---|---|---|
| V-42 | OOS NW t | core 0.95; core + T4xE1 1.32 | `v2_oos/metrics.csv` | `nw_t` |
| V-43 | OOS max DD, start-NAV convention | core + T4xE1 -5.9% / -6.4% (1x / 2x) vs metrics.csv -5.3% / -5.7%; adding T4xE1 deepens OOS DD from -4.7% to -5.9% | STRATEGY_RESULTS s3.4 dagger note | - |
| V-44 | OOS by chair | Powell months: core 0.974 -> 0.942 with T4xE1; Warsh months: -1.342 -> 0.535 | `v2_oos/oos_concentration.csv` | Powell/Warsh rows |
| V-45 | OOS five best days share | core + T4xE1 62%; core alone 91% | `oos_concentration.csv` | `value` |
| V-46 | Turnover | overlay 0.3x/yr OOS (0.6 IS); T4xE1 sleeve's own trading x multiplier 5.8x/yr OOS (7.7 IS) | `v2_oos/metrics.csv` | `turnover_per_year`, `fed_sleeve_turnover_per_year` |
| V-47 | core_ER_6 OOS returns are not new information (they appeared in earlier portfolio work) | | `v2_oos/README.md`; STRATEGY_RESULTS s1 | - |
| V-48 | core_ER_6 composition | vol-managed ES, month-end ZN, broad trend | `preregistration/HYPOTHESIS_v2.md` "Portfolio test" | - |

---

## 10. v2 costs and their justification

| ID | Fact | Value | Source | Field |
|---|---|---|---|---|
| C-1 | E1 trading cost | 1.5 bp (TLT) and 5 bp (UUP) per unit of NAV traded, one way; blended 2.375 bp at 75/25 | `v2_oos/README.md` "Cost assumptions"; STRATEGY_RESULTS s5; `HYPOTHESIS_v2.md` E1 | - |
| C-2 | E1 borrow | 30 bp a year on short ETF weights; cash earns the T-bill; returns are excess of the T-bill | same | - |
| C-3 | 2x convention | doubles trading costs, not the borrow fee (`cost_mult` 2); gross = no trading cost and no borrow | same | - |
| C-4 | Justification as committed | Variant A's (strategy 01) cost assumptions carried into HYPOTHESIS_v2 unchanged and fixed before any v2 return, so not tuned to the result. No measured TLT/UUP spread sample is committed. | STRATEGY_RESULTS s5 "Why these numbers" | - |
| C-5 | E2 costs | ZN 1 bp, 6E 1 bp per leg, roll = one extra round trip; next-close fills | `HYPOTHESIS_v2.md` E2 | - |
| C-6 | ZN measured half-spread on presser days (supports the E2 1 bp) | median 0.5 tick (p90 0.5) at 14:20, 16:00 and at every answer entry, 2016-2026 | `backtests/results/presser_h1/spreads_at_fill_points.csv` | ZN rows `median`, `p90` |
| C-7 | Price-free conversion of C-6 [D] | 0.5 ZN tick = $7.8125 per $100,000 face = 0.78 bp of face; 1 bp is about 1.3 such half-spreads of face | ADDENDUM 1.2 tick table x C-6 | arithmetic |
| C-8 | Portfolio overlay costs | 2.375 bp (T4xE1 sleeve), 0.75 bp (ES sleeve), 1.0 bp (ZN sleeve), 1.07 bp (trend sleeve) on multiplier changes; 2x doubles sleeve and overlay costs; `combine.build` used as-is | `v2_oos/README.md`; STRATEGY_RESULTS s5 | - |
| C-9 | Why a 2x row | competition rule, and for v2 also the registered gate (full IS 2x > 0.5) | STRATEGY_RESULTS s5 | - |

---

## 11. Press conference: H1-primary, H1-Q, lexicon control

### 11a. G3 (decision row): confirmation sample, ZT, primary clock, 16:00 exit, gross

Source: `backtests/results/presser_h1/key_results.json` key `H1-primary (stance)` (identical to
`g3_and_h1primary_extras.json` `H1` and `summary.json` `presser_H1.G3_H1_primary_confirmation_2023_2026`).

| ID | Fact | Value | Field |
|---|---|---|---|
| P-1 | Decision | NO-GO: not detected (90% block-bootstrap CI upper bound 5.30 ticks) | `decision` |
| P-2 | n | 20 (rule needs >= 15) | `n` |
| P-3 | Mean gross | +0.50 ticks = +$3.91 per contract per meeting | `mean`, `mean_usd` 3.90625 |
| P-4 | sd / median / hit | 13.17 ticks / +1.5 ticks / 55% | `sd`, `median`, `hit` |
| P-5 | t | 0.17 | `t` 0.1697 |
| P-6 | Sign-flip wild bootstrap p (decision) | one-sided 0.4505; two-sided 0.8822 | `wb_p_one`, `wb_p_two` |
| P-7 | Block bootstrap | 90% CI [-4.06, +5.30] ticks; one-sided p 0.431; agrees with the decision | `bb_ci90_lo` -4.055, `bb_ci90_hi` 5.30, `bb_p_one` 0.4307, `block_boot_agrees` |
| P-8 | Permutation p | 0.668 | `perm_p_one` 0.6677 |
| P-9 | Leave-one-out range | [-1.26, +2.05] ticks; most influential 2023-05-03 | `loo_min`, `loo_max`, `loo_most_influential` |
| P-10 | Without the 2 largest-move meetings (2023-05-03, 2024-07-31) | mean +0.28 ticks, p 0.467 | `drop_top2_mean`, `drop_top2_wb_p_one` |
| P-11 | Companion slope (HC3) | coef 0.00056, t 0.547, two-sided p 0.519 | `slope_coef`, `slope_t_hc3`, `slope_p_two` |
| P-12 | Extra clocks | exec30 mean +0.50; point clock +0.75; 14:30 convention clock +0.60 (all n = 20) | `exec30_mean`, `point_clock_mean`, `convention_clock_mean` |
| P-13 | Registered sensitivities | drop text flags (n 18) -0.94, p 0.626; drop degraded days (n 18) +0.56, p 0.454; start uncertainty <= 10 s (n 3) +1.0, p 0.253 | `sens1_*`, `sens2_*`, `sens3_*` |
| P-14 | Sidedness | NO-GO under the ADDENDUM's one-sided test (p 0.45) and under a two-sided reading (p 0.88); no PREREG-R ratification file exists in `preregistration/` | fields above; repo listing |

### 11b. H1-primary, ZT, USD per contract per meeting, by sample and cost (primary clock, 16:00 exit)

Source: `backtests/results/presser_h1/summary_long.csv`, rows `test` = H1-primary[H1], `variant` = primary|exit_1600,
`sym` = ZT, `unit` = usd; [D] rows filtered from `presser_h1/h1primary_trades.csv` (signal H1, clock primary,
exit_1600, ZT).

| Sample | n | Gross C0 | CM | CMF | C2 | C4 | t (C0) |
|---|---|---|---|---|---|---|---|
| Confirmation 2023-02-01..2026-04-29 (G3) | 20 | +$3.91 | -$3.91 | -$7.91 | -$27.34 | -$58.59 | 0.17 |
| 2016-2022 clean sample (positions from 2018-03-21) | 31 | +$2.52 | -$6.30 | -$10.30 | -$32.76 | -$68.04 | 0.25 |
| Warsh (3, descriptive) | 3 | -$36.46 | -$44.27 | -$48.27 | -$67.71 | -$98.96 | -0.70 |
| OOS slice, no Warsh [D] | 12 | -$8.46 | -$16.28 | -$20.28 | -$39.71 | -$70.96 | -0.80 |
| OOS slice incl. Warsh [D] | 15 | -$14.06 | -$21.88 | -$25.88 | -$45.31 | -$76.56 | -1.12 |
| IS to 2024-10-02 [D] | 39 | +$6.61 | -$2.00 | -$6.00 | -$27.84 | -$62.30 | 0.48 |

| ID | Fact | Value | Source | Field |
|---|---|---|---|---|
| P-15 | 16:30 exit, confirmation | -$11.33 gross (t -0.56) | `summary.md` H1 table | primary\|exit_1630, confirmation, C0 |
| P-16 | H1 robustness symbols, confirmation, gross | ZF +$7.03 (t 0.28), ZN +$14.06 (t 0.41), ES -$235.63 (t -0.69) | `summary_long.csv` | H1-primary[H1], primary\|exit_1600, confirmation, C0, usd |
| P-17 | 2016-2022 robustness (HC3) | 2022 vs rest -$25.73 (t -0.53); SEP vs non-SEP -$11.69 (t -0.54); companion slope with chair dummy t -0.86 | `presser_h1/h1primary_H1_2016_2022_robustness.json` | `coef`, `t_hc3` |
| P-18 | H1 zero-move trades | 6 of 54 H1 ZT trades moved 0 ticks [D] | `h1primary_trades.csv` `C0_ticks`; README "zero_share" | - |
| P-19 | H1-Q (robustness only, not gated) | confirmation n 20, mean +0.60 ticks ($4.69), p 0.435; 2016-2022 n 31, -0.77 ticks (-$6.55), p 0.738 | `key_results.json` | `H1-Q` |
| P-20 | H1-answer diagnostic, ZT gross, confirmation | +1 min: 548 answers, -0.135 ticks, p 0.234; +5 min: 163, +0.129, p 0.611; +15 min: 62, +0.177, p 0.883 | `backtests/results/summary.md` H1-answer table | `wcb_p_two` |
| P-21 | Lexicon control, frozen rule (MIN_HD = 5) | not estimable: defined for 4 of 75 meetings; none passes the 8-meeting burn-in | `key_results.json` | `lexicon frozen lex_H1` |
| P-22 | Lexicon control, lex_H1_raw (not the frozen spec), confirmation, ZT | NO-GO, n 20, mean -4.1 ticks (-$32.03), t -1.47, one-sided p 0.916, 90% CI upper 0.60 ticks | `key_results.json` | `lexicon lex_H1_raw G3-rule replica ...` |
| P-23 | Lexicon control costs (confirmation, USD) | C0 -$32.03; CM -$39.84; CMF -$43.84; C2 -$63.28; C4 -$94.53 | `summary_long.csv` | H1-primary[lexH1raw], primary\|exit_1600, confirmation, ZT |
| P-24 | Burn-in | no position until 8 prior meetings; the eight 2016-17 Yellen meetings carry none; positions start 2018-03-21 | `presser_ADDENDUM.md` s3.3 | - |

---

## 12. Press conference: BENCH-R (ZT, 14:20 -> next 1m open after conference end)

Source unless stated: `backtests/results/presser_h1/key_results.json` key `BENCH-R` and `summary_long.csv` rows
BENCH-R, `variant` exit_tau_upper (the primary exit), ZT, usd. USD per contract per meeting.

| Sample | n | Gross C0 | CM | CMF | C2 | C4 | t (C0) | Two-sided p (C0) |
|---|---|---|---|---|---|---|---|---|
| Era 2016-2019 (one-sided > 0) | 20 | +$27.73 | +$15.23 | +$11.23 | -$22.27 | -$72.27 | 0.94 | 0.390 (one-sided 0.190) |
| Era 2020-2026 | 50 | -$35.31 | -$43.13 | -$47.13 | -$66.56 | -$97.81 | -1.15 | 0.256 |
| 2020-2026 ex-2022 | 42 | +$8.93 | +$1.12 | -$2.88 | -$22.32 | -$53.57 | 0.39 | 0.708 |
| 2020-2026 ex-Warsh | 47 | -$49.54 | -$57.35 | -$61.35 | -$80.79 | -$112.04 | -1.57 | 0.125 |
| Jan 2020 in early era: 2016-2020Jan / 2020Mar-2026 | 21 / 49 | +$21.21 / -$33.80 | | | | | 0.74 / -1.08 | |
| Timing-eligible 2016-2019 / 2020-2026 | 19 / 41 | +$50.58 / -$33.92 | +$37.83 / -$41.73 | | | | 2.58 / -1.01 | 0.020 / 0.329 |
| Decay / OOS slice 2024-10..2026-09 (incl. 3 Warsh) | 15 | +$22.40 | +$14.58 | +$10.58 | -$8.85 | -$40.10 | 0.52 | 0.617 |
| Warsh only [D] | 3 | +$187.50 | +$179.69 | +$175.69 | +$156.25 | +$125.00 | n/r | n/r |

| ID | Fact | Value | Source | Field |
|---|---|---|---|---|
| B-1 | Sample | 73 scheduled meetings with market data: 20 in 2016-2019, 53 in 2020-2026 (incl. 3 Warsh); split at 2020-01-01; 70 ZT trades (three zero statement-window signs take no trade: 2020-09-16, 2023-07-26, 2026-01-28 [D]) | `presser_ADDENDUM.md` s2, s5; `presser_h1/tables/benchr_per_meeting_ZT.csv` (70 rows) vs `benchr_usmpd_ust2y.csv` (73 dates) | - |
| B-2 | Break test, mean gross 2020-26 minus 2016-19 | -$63.05, HC3 t -1.46, two-sided p 0.146 (one-sided lower 0.075) | `presser_h1/benchr_break_stats.csv` | exit_tau_upper, ZT, `mean_gross_usd_diff_late_minus_early` |
| B-3 | Slope of hold return on R_m | 2016-19 +0.193 (t 1.39, n 20); 2020-26 -0.096 (t -0.49, n 50); difference -0.289 (t -1.20, p 0.215) | same | `slope_hold_ret_on_R_*`, `slope_diff_*` |
| B-4 | corr(R_m, hold move) | 2016-19 +0.197; 2020-26 -0.090 | same | `corr_R_vs_hold_move_*` |
| B-5 | Break-even cost per side, pre-2020 | 1.0 tick = $15.63 (2016-18, n 12); 1.44 ticks = $11.23 (2019, n 8); post-2020 negative (-2.26 ticks, -$17.66) | `presser_h1/benchr_cost_hurdle.csv` | exit_tau_upper, ZT, `breakeven_ticks_per_side`, `breakeven_usd_per_side` |
| B-6 | 2022 alone | -34.25 ticks gross = -$267.58 per meeting (n 8) [D: ticks x $7.8125] | `benchr_cost_hurdle.csv` | exit_tau_upper, ZT, year_2022, `mean_gross_ticks` |
| B-7 | Measured half-spread at BENCH-R fills | median 0.5 tick in every era (at 14:20 and at the exit second) | `benchr_cost_hurdle.csv` `median_measured_halfspread_ticks`; `spreads_at_fill_points.csv` | - |
| B-8 | USMPD version (UST2Y, statement sign on the conference-window change) | 2016-19 +1.08 bp (t 1.39, n 20); 2020-26 -0.85 bp (t -1.06, n 52) | `summary_long.csv` | usmpd_UST2Y_stmt_sign_on_pc_window |
| B-9 | 15:30 exit robustness, break p | ZT mean diff -$61.41, t -1.31, p 0.187 | `benchr_break_stats.csv` | exit_1530, ZT |
| B-10 | ES robustness (own sign), gross | 2016-19 +$205.63 (t 1.53); 2020-26 +$122.06 (t 0.52) | `key_results.json` | `BENCH-R` ES keys |
| B-11 | Max DD of cumulative P&L per contract, by era [D] | 2016-19: gross -$523, CM -$594, C2 -$914, C4 -$1,711; 2020-26: gross -$2,672, CM -$2,852, C2 -$3,836, C4 -$5,266 (cumulative: 2016-19 gross +$555, CM +$305; 2020-26 gross -$1,766, CM -$2,156) | `presser_h1/tables/benchr_per_meeting_ZT.csv` | cumulative sum of `C0_usd` / `CM_usd` / `C2_usd` / `C4_usd` in date order within era; DD = min(cum - running peak, start 0) |
| B-12 | Trades per year | 4 a year 2016-2018, 8 a year from 2019 (2020: 6, 2023: 7, 2026: 5) [D] | `benchr_per_meeting_ZT.csv` | count by year of `date` |
| B-13 | Prior exposure | ZT era correlations +0.19 (2016-19) / -0.09 (2020-26) and ES +0.46 / -0.02 were seen before the ADDENDUM | `presser_ADDENDUM.md` s12 | - |
| B-14 | Plan rules for BENCH-R | eras never averaged into one number; no annualised Sharpe (ADDENDUM); D-3 shows Sharpes as presentation only | `presser_ADDENDUM.md` s5; `presser_strategy/README.md` | - |

---

## 13. Press-conference trades as strategy series (D-3 presentation, no inferential weight)

Source: `backtests/results/presser_strategy/tables.md` and `key_metrics.json`; conventions in
`presser_strategy/README.md`. $10m capital; N contracts constant per strategy and symbol, sized so IS gross vol is
10% (`sizing.csv`); return 0 on non-trade days; additive equity; Sharpe daily x sqrt(252). Net 1x = CMF (measured
half-spreads + $2/side fee); net 2x = twice that.

| Strategy, ZT | Window | Trades | Ann. return gross / 1x / 2x | Vol 1x | Sharpe gross / 1x / 2x | Max DD gross / 1x / 2x | Hit 1x | Contracts/yr; x capital/yr |
|---|---|---|---|---|---|---|---|---|
| H1-primary (N 4,788) | IS 2018-03-21..2024-10-02 | 39 | 1.9% / -1.7% / -5.3% | 10.0% | 0.19 / **-0.17** / -0.52 | -12.7% / -16.5% / -36.1% | 46% | 57,212; 1,144 |
| | 2016-2022 sample | 31 | 0.8% / -3.2% / -7.2% | 7.0% | 0.11 / -0.45 / -0.95 | -10.3% / -16.4% / -34.6% | 42% | 62,081; 1,242 |
| | G3 sample (spans IS/OOS) | 20 | 1.2% / -2.3% / -5.9% | 12.0% | 0.10 / -0.20 / -0.48 | -15.3% / -22.7% / -30.8% | 50% | 59,364; 1,187 |
| | OOS 2024-10-03..2026-10-02 | 15 | -5.1% / -9.3% / -13.6% | 7.0% | -0.79 / **-1.33** / -1.73 | -15.3% / -20.8% / -28.6% | 40% | 72,250; 1,445 |
| | OOS ex-Warsh | 12 | -2.4% / -5.9% / -9.3% | 4.8% | -0.57 / -1.23 / -1.66 | -7.6% / -11.8% / -18.4% | 42% | 57,800; 1,156 |
| BENCH-R (N 1,916) | IS pooled (format only) 2016-03-16..2024-10-02 | 55 | -3.5% / -5.1% / -6.8% | 10.1% | -0.35 / **-0.51** / -0.67 | -46.3% / -54.9% / -64.6% | 44% | 24,680; 494 |
| | IS era 2016-2019 | 20 | 2.8% / 1.1% / -0.5% | 5.7% | 0.48 / 0.20 / -0.09 | -9.2% / -11.1% / -13.3% | 60% | 20,202; 404 |
| | IS era 2020..2024-10-02 | 35 | -8.5% / -10.2% / -11.8% | 12.5% | -0.69 / -0.81 / -0.93 | -51.2% / -56.4% / -61.6% | 34% | 28,259; 565 |
| | OOS | 15 | 3.2% / 1.5% / -0.2% | 8.4% | 0.38 / **0.18** / -0.02 | -10.7% / -11.7% / -12.7% | 47% | 28,912; 578 |
| | OOS ex-Warsh | 12 | -2.2% / -3.5% / -4.9% | 7.3% | -0.30 / -0.48 / -0.66 | -10.7% / -11.7% / -12.7% | 33% | 23,130; 463 |

| ID | Fact | Value | Source | Field |
|---|---|---|---|---|
| R-1 | Per-trade net 1x t-statistic, H1 ZT | IS -0.43; OOS -2.06 (matches [D] CMF t in s11b) | `presser_strategy/README.md` "Sample size"; STRATEGY_RESULTS s3.6 | - |
| R-2 | Per-trade Sharpe, BENCH-R ZT net 1x (not annualised) | IS -0.20; OOS 0.06 | `tables.md` | `per-trade Sharpe` |
| R-3 | Mean $ per contract per trade | H1 ZT IS gross +6.6, net1x -6.0; OOS gross -14.1, net1x -25.9; BENCH-R ZT IS gross -28.1, net1x -41.6; OOS gross +22.4, net1x +10.6 | `tables.md` | `mean $/contract/trade` |
| R-4 | Fixed-tick rows (harsher) | H1 ZT IS fixed1x (C2+F) Sharpe -0.85; BENCH-R ZT IS fixed1x -0.83, OOS -0.22 | `tables.md` fixed-tick tables | - |
| R-5 | Robustness symbols, Sharpe IS 1x / OOS 1x | H1: ZF -0.68 / -1.64; ZN -0.13 / -0.94; ES -0.37 / -0.38. BENCH-R: ZF -0.45 / -0.43; ZN -0.27 / -0.34; ES 0.12 / 0.71 (only series positive at 1x in and out of sample; one of eight series; no inferential weight) | `tables.md` "Sharpe by symbol" | - |
| R-6 | Sharpe standard error | about 0.7 over the 2-year OOS (15-16 trades); about 0.35-0.4 over 6.5-8.5 IS years | `presser_strategy/README.md` "Sample size" | - |
| R-7 | N per strategy/symbol | H1: ZT 4,788, ZF 4,033, ZN 3,072, ES 343; BENCH-R: ZT 1,916, ZF 1,827, ZN 1,413, ES 265 | `presser_strategy/sizing.csv`; `run_meta.json` `N_contracts` | - |
| R-8 | Full-period cumulative P&L, BENCH-R ZT (% of $10m) | gross -23.2%, net 1x -40.8%, net 2x -58.5% | `presser_strategy/equity_benchr_ZT.png` (annotation) | - |
| R-9 | Checks | positions match the frozen file; gross = suite C0; net 1x = suite CM + fee; fixed1x = suite C2F; G3 reproduced (n 20, mean +0.50); BENCH-R era means reproduced; rebuild of 200 metrics rows (5,272 values) and 528 key_metrics values, max rel. diff 4.6e-6 | `presser_strategy/qa.json`; STRATEGY_RESULTS s8 | - |
| R-10 | Warsh half-size live rule not applied (frozen positions are +/-1) | | `presser_strategy/README.md` "Positions" | - |

---

## 14. Press-conference costs and their justification

| ID | Fact | Value | Source | Field |
|---|---|---|---|---|
| PC-1 | Cost rows (per side, per contract) | C0 gross trade prints (associational, not executable mids); C2 / C4 = 2 / 4 ticks per side; CM = measured half-spread at entry + exit second from bbo-1s; CQ = quote fills; F = $2.00/side fee (A-04, UNVERIFIED broker estimate) | `presser_ADDENDUM.md` s7 | - |
| PC-2 | Round-trip $ at C2 / C4 | ZT 2019+ $31.25 / $62.50; ZT 2016-18 $62.50 / $125; ZF $31.25 / $62.50; ZN $62.50 / $125; ES $50 / $100 | `presser_ADDENDUM.md` s7 | - |
| PC-3 | ZT net 1x per round trip | 1 tick + $4: $11.81 from 2019; $19.63 for 2016-2018 tick era (the README's "in 2018" holds for H1; for BENCH-R it is 2016-2018) | `presser_strategy/README.md` "Costs"; STRATEGY_RESULTS s9 item 7 | - |
| PC-4 | ZT one tick wide at every fill | median and p90 half-spread 0.5 tick at 14:20, 16:00, tau_end and answer entries; ZT 2019-26 answer entries n 1,266, mean 0.518 tick; no quote older than 60 s at these points | `presser_h1/spreads_at_fill_points.csv` | `median`, `p90`, `mean`, `stale_gt60` |
| PC-5 | ZT half-spread around the conference (2019-26) | median 0.5 tick in every phase bucket -60..+90 min; p99 1.0 tick | `presser_h1/spreads_by_presser_phase.csv` | ZT 2019-2026 rows |
| PC-6 | ZN / ES at fills | ZN 1 tick + $4 at every fill; ES 1-2.5 ticks (mean 1.1) + $4 | `presser_strategy/README.md` "Costs" | - |
| PC-7 | ZF | no quotes; ZF "net 1x" = C2 + F (2 ticks/side + $2/side) | `presser_strategy/README.md`; ADDENDUM s1.3 | - |
| PC-8 | Justification as committed | measuring the spread at the actual fill seconds is the most direct cost estimate; fixed in the ADDENDUM before any return; fee unverified | STRATEGY_RESULTS s5 | - |
| PC-9 | Limitation | top-of-book cost for a small order; at the stated N no market impact is included, so net rows are optimistic | STRATEGY_RESULTS s5, s9 item 3 | - |
| PC-10 | Plan rule | H1 net rows descriptive only; the plan calls H1 non-executable and rules out a net Sharpe; BENCH-R is the costed object | `presser_ADDENDUM.md` s7 | - |
| PC-11 | Events-label half-spreads seen before the ADDENDUM | median $3.99 (2019+), $7.89 (2016-18) | `presser_ADDENDUM.md` s12 | - |

---

## 15. H2 / H3 / H4 (exploratory, post-NO-GO): HiPerGator reference run governs

| ID | Fact | Value (HPG reference) | Local replication | Source (HPG) | Field |
|---|---|---|---|---|---|
| E-1 | H2 (voice arousal, long ZT on +sign(z), +1 min, gross, 2023-2026) | not detected: n 269 answers / 10 meetings, mean -0.0855 ticks, CR1 t -0.81, 90% CI [-0.262, +0.068], wild-cluster p 0.4389 (two-sided), Holm 0.8778 | n 268, mean -0.0858, p 0.4382, Holm 0.8764 | `backtests/presser/backtest_h234/results/family_holm.json` `H2`; `results/answer_summary.csv` (H2, ZT, h 1, primary_2023_2026, C0) | `p_raw`, `p_holm`, `mean_ticks`, `bb_ci90`, `t_cr1` |
| E-2 | H2 label | "source invariance not checked" (re-encode meeting 2019-06-19 fails the caption check, offset -2.79 s; ICC not computed) | same | `qa/kill_switches.json` `H2.source_invariance`; H234_LOCAL_SUMMARY s2 | - |
| E-3 | H2 G4 variance gate | not killed: arousal floor binds in 0 of 22 post-burn-in meetings | same | `qa/kill_switches.json` | `g4_share_arousal` 0.0, `g4_n_post_burnin` 22 |
| E-4 | H3 (upper-face composite) | KILLED by G4: browInnerUp floor binds in 22 of 22 (100%) post-burn-in meetings; enters Holm at p = 1 (computed for the record only: n 272, mean +0.011 ticks, CI [-0.176, +0.217]) | same | `qa/kill_switches.json` `H3.g4.BI.share` 1.0; `family_holm.json` `H3` | - |
| E-5 | H4 (combined vs text-only, Clark-West, frozen 2018-2022 fit, ZT +1 min) | not detected: n 269 / 10 meetings, mean f 0.00833, SE 0.01145, **t 0.727** (df 9), **one-sided p 0.2427** (two-sided 0.485; wild 0.257), **Holm 0.728**; OOS R^2 C vs T **-0.0041**, C vs zero -0.0291, T vs zero -0.0249; sign hits C 0.502 / T 0.488 | t 0.722, p 0.2442, Holm 0.7327, R^2 -0.0043 | `results/h4_results.json` `answer_ZT.frozen_fit`; `family_holm.json` `H4` | - |
| E-6 | H4 component status | uses U (from the killed H3) and z_A (H2, "source invariance not checked") | same | H234_LOCAL_SUMMARY s3; NOTE1 s4 | - |
| E-7 | H4 other rows (not decisive) | expanding window t 0.548 (p 0.298); leave-one-meeting-out 2023-26 t -0.885; ES frozen t -0.939 (p 0.814) | similar | `h4_results.json` | `expanding_window`, `lomo_2023_2026_not_point_in_time`, `answer_ES.frozen_fit` |
| E-8 | H4 meeting level (descriptive, n 10, outside Holm; NOT a finding) | ZT t 2.387, p one-sided 0.0204 / two-sided 0.0407, OOS R^2 C vs T +0.407 but C vs zero -0.489 and T vs zero -1.513; ES t 2.08 | ZT t 2.389 | `h4_results.json` | `meeting_ZT`, `meeting_ES` |
| E-9 | H4 trade P&L, sign(y_hat C), ZT +1 min | gross -0.019 ticks (hit 0.394), C2 -4.02, C4 -8.02; sign(y_hat T) gross -0.152 | -0.026 | `h4_results.json` | `answer_ZT.pnl_sign_C`, `pnl_sign_T` |
| E-10 | H2 costs, same trades | C0 -0.086; CM -1.108; CMF -1.620; C2 -4.086; C4 -8.086 ticks; measured spreads cost about 1.02 ticks a round trip [D: CM - C0] | identical | `results/answer_summary.csv` | H2, ZT, h 1, primary_2023_2026 |
| E-11 | H2 meeting-averaged / LOMO | meeting-averaged mean -0.117 ticks (sign-flip p 0.345); LOMO range [-0.146, -0.028], most influential 2025-09-17 | -0.116 (p 0.352) | `answer_summary.csv` | `mtg_mean`, `mtg_wb_p_two`, `lomo_*` |
| E-12 | Holm family | m = 3 (H2, H3, H4), family alpha 0.05; killed test enters at p = 1; none significant | same | `family_holm.json` `note`; EXPLORATORY s6.5 | - |
| E-13 | Samples | 62 baseline meetings; caption check passes 26 (36 excluded: 29 QA failed, 7 also no caption-timed answers); burn-in 4 meetings (2018-03-21, 2019-01-30, 2019-03-20, 2019-07-31); 22 post-burn-in = 12 training (2019-10-30..2022-05-04) + 10 test | same | `qa/meeting_qa.csv` (`h2_ok`, `h2_exclusion`); H234_LOCAL_SUMMARY s2 | - |
| E-14 | Test meetings (10) | 2023-09-20, 2024-06-12, 2024-11-07, 2024-12-18, 2025-01-29, 2025-03-19, 2025-06-18, 2025-07-30, 2025-09-17, 2026-01-28 | same | H234_LOCAL_SUMMARY s2 | - |
| E-15 | H4 fit | OLS once on Powell 2018-2022: 247 answers / 12 meetings; train end 2022-12-31; written before any test join | - | `backtest_h234/h4_fit/fit.json` | `fits.answer_ZT.n`, `train_end`, `written_before_test_join` |
| E-16 | Answer counts (H2 primary) | eligible 542 (primary 287); +1 min selections 516 (primary 269, 10 meetings); +5 min 81; +15 min 31 | - | `backtest_h234/positions/positions_status.json` | `H2` |
| E-17 | Joins never on the package known_at | voice tau falls a median 20.0 s and face 18.2 s after the package known_at | same | `positions_status.json` `known_at_qa` | - |
| E-18 | Strategy-level metrics of H2/H4 test trades (local run only) | N 7,036 (H2), 8,245 (H4 C), 6,941 (H4 T); competition OOS Sharpe gross / 1x / 2x: H2 -0.77 / -2.00 / -2.01, H4 C -0.71 / -1.97 / -2.00; net 1x loses 1.4-1.7 ticks per trade; about 140-165x capital per one-minute trade; "these rows describe costs, not a strategy" | - | `backtests/presser/H234_LOCAL_SUMMARY.md` s6 | - |
| E-19 | Local verification | 110 checks, 0 mismatches (max rel. diff 7.5e-15); HPG job emulated on the PC reproduces every table and verdict | - | H234_LOCAL_SUMMARY s7 | - |

Draft-required agreement sentence: "HiPerGator reference and local replication agree: H2 p 0.439 vs 0.438, H3 killed
in both, H4 p 0.243 vs 0.244; 269 vs 268 answers." Source: `backtests/presser/H234_LOCAL_SUMMARY.md` header.

---

## 16. Reproduction and verification facts

| ID | Fact | Value | Source | Field |
|---|---|---|---|---|
| X-1 | v2 HiPerGator reproduction | PASS: IS 7/7 files agree (max abs diff 4.4e-16); failed-rule record 1/1; D-3 run 18/18 (5.9e-16); D-3 report 2/2 (1.8e-15); chosen T4xE1, rule passed false in both; tolerance rtol 1e-9, atol 1e-12 | `v2_oos/hpg_reproduction/reproduce_report.json` | `verdict`, `comparisons`, `decision_rule_passed` |
| X-2 | Code vs RUN_LOG hashes at reproduction | 17 of 19 equal; run_v2.py and run_v2_chrono.py differ only because `--reproduce` was added afterwards | same | `code_and_inputs_vs_run_log`, `run_log_note` |
| X-3 | IS reproduction before any OOS computation | max abs diff 0 on all 7 committed v2 files and the 3 frozen daily series | `v2_oos/README.md` "Checks" | - |
| X-4 | Full-period series vs committed IS | max abs diff 9.4e-17 (strategies), 1.1e-16 (portfolio); OOS rows vs oos_chosen.json 0.0 | `v2_oos/consistency.json` | all keys |
| X-5 | Independent v2 recomputation (numpy, no v2lib) | 2,192 comparisons, none > 1e-6 relative; NW t vs statsmodels HAC 3e-15; DSR 2e-16 | STRATEGY_RESULTS s8 | - |
| X-6 | Unlock scope | two files (run_v2.py, run_v2_chrono.py), +52/-3 lines; opens only for the pinned D-3 hash and output folder; a second run is refused | STRATEGY_RESULTS s8 | - |
| X-7 | v2 causality checks (pre-Amendment-2 check run) | prefix invariance max abs diff 0.0 for every z and weight series; T3 OLS vs statsmodels <= 2e-15 on 3 dates; T0f vs strategy 01 replicate max abs diff 6.4e-15 over 3,711 dates | `v2/check/check.json` (pinned to the Amendment-1 hash 6083d3ef; it predates real stance scores) | `prefix_invariance_max_abs_diff`, `T3_vs_statsmodels`, `T0f_vs_replicate_*` |
| X-8 | Press-conference suite re-run on HiPerGator | reproduces committed results: H1 results 13 files agree, per-meeting tables 8, frozen H1 positions 13; G3 NO-GO unchanged | `backtests/presser/backtest_h234/hpg_run_all_backtests.log` | "press-conference suite" block |
| X-9 | BENCH-R trade counts across symbols | ZT 70, ZF 72, ZN 72, ES 71 (285 total) | STRATEGY_RESULTS s8 "Samples" | - |

---

## 17. Liquidity and capacity

### 17a. Sourced in committed results

| ID | Fact | Value | Source | Field |
|---|---|---|---|---|
| L-1 | v2 sizing limits | 10% vol target (vol floor 4%), z clip 2, gross cap 1.5x, no-trade band 0.10 | `preregistration/HYPOTHESIS_v2.md` "Signal and execution" | - |
| L-2 | Max UUP / TLT weight at the cap [D] | 1.5 x 25% = 37.5% of NAV in UUP; 1.5 x 75% = 112.5% in TLT | L-1 x E1 weights | arithmetic |
| L-3 | v2 turnover | 26.8x (IS) / 17.7x (OOS) NAV a year | `v2_oos/metrics.csv` | `turnover_per_year` |
| L-4 | H1 ZT displayed size vs N | N 4,788 vs median 518 contracts displayed at entry (p10 95, p90 6,120), 1,332 at exit; size >= N at 14.8% of entries | `presser_strategy/capacity_top_of_book.csv` | H1-primary, ZT, all |
| L-5 | BENCH-R ZT displayed size vs N | N 1,916 vs median 616.5 at entry, 593 at exit; size >= N at 27.1% of entries | same | BENCH-R, ZT, all |
| L-6 | ES displayed size | H1 ES N 343 vs median 21.5 at entry; BENCH-R ES N 265 vs 31 | same | ES rows |
| L-7 | Face notional per trade | H1 ZT 4,788 x $200k = $958m = 96x capital; BENCH-R ZT 38x; margin not modelled | `presser_strategy/README.md` "Capacity and realism" | - |
| L-8 | One contract per trade is the registered size; P&L and costs are linear in N, so Sharpe does not depend on N | | ADDENDUM s1.2; presser_strategy README "Sizing" | - |
| L-9 | 26 ZT contracts = $5.2m face [D] | 26 x $200,000 | ADDENDUM 1.2 face value | arithmetic |

Note: `capacity_top_of_book.csv` is derived from the licensed bbo-1s file (sizes, not prices). STRATEGY_RESULTS s9
item 11 asked the team to decide whether it goes to git; it was committed in `6a61ef9`.

### 17b. In the draft, with NO committed source (do not quote until a committed script/output exists)

- TLT about $2.75bn and UUP about $33m daily dollar volume; "UUP 3.75m = 11% of a day"; capacity "roughly $10m".
- ZN about $184bn and 6E about $22bn median daily front-contract volume; "0.06% and 0.17% of a median day";
  "$112.5m of ZN (about 1,000 contracts)" (the contract count needs a price level).
- ZT median 2,108 contracts per minute (p10 529), 14:30-16:00, 2023-26; "one tick wide 97.0% of the time".
- ZN and 6E initial margins (CME page, no value or date committed).

---

## 18. Power and operating characteristics

| ID | Fact | Value | Source | Field |
|---|---|---|---|---|
| O-1 | G3 rule | GO only if n >= 15, mean gross > 0 and one-sided sign-flip p <= 0.05 | `presser_ADDENDUM.md` s8.2 | - |
| O-2 | P(GO) at n = 20 (Gaussian / t4) | rho 0: 0.047 / 0.048; rho 0.1: 0.09 / 0.10; rho 0.2: 0.17 / 0.19; rho 0.3: 0.29 / 0.31; rho 0.47: 0.55 / 0.60 | `presser_ADDENDUM.md` s8.2 table | - |
| O-3 | Reading | "At these power levels, a NO-GO is weak evidence that there is no effect." | same | - |
| O-4 | Live gate (G5) | paper-trade text only, half size on Warsh, only if measured live p90 delay <= 60 s; frozen delay = max(measured p90, 30 s) | `preregistration/presser_team_FINAL_PLAN.md` (G5 row; "Live path") | - |
| O-5 | No forward Powell data will exist; any H2-H4 signal could only motivate a new pre-registered test on another chair | | `presser_H2H3H4_EXPLORATORY.md` s0 | - |

---

## 19. Literature numbers the draft quotes (secondary source in repo; check against the papers)

| ID | Claim | Repo text | Source |
|---|---|---|---|
| Lit-1 | Gorodnichenko, Pham and Talavera (AER 2023): 36 pressers, 692 answers, 2011-2019; about 75 bp (S&P) over several days; minute-level about 1 bp, imprecise | "do not cite 75 bp as an intraday edge" | `presser_team_FINAL_PLAN.md` s1 |
| Lit-2 | Gomez-Cram and Grotteria (JFE 2022): 41 pressers to Jan 2020; 13:50-14:20 predicts the presser window, corr 0.58 (Eurodollars), 0.44 (S&P) | | same |
| Lit-3 | Narain and Sangani (IJCB 2026): continuation reversed under Powell after COVID | | same |
| Lit-4 | Shah, Paturi and Chava (ACL 2023): combined F1 about 0.71; presser-only 0.53-0.55; CC BY-NC 4.0 | | same |
| Lit-5 | Curti and Kazinnik: "-0.53 bp / 3-min" is from discussant slides, UNVERIFIED as a published coefficient | | same |

---

## 20. Draft claims to correct or source (draft v1 vs committed files)

1. **OOS "not evaluated"** (Summary headline, s5, Table 1 row, Fig. 1 caption, s8, A2 row, checklist): superseded
   by D-3; use s7 numbers with H-2/H-3/H-4 wording.
2. **Max DD convention.** `v2_oos/metrics.csv` measures from the window's first close (T4xE1 OOS -6.6%);
   STRATEGY_RESULTS uses the starting NAV (-7.4%). Pick one, state it in a footnote; the start-NAV figure is the
   more conservative. Same issue for Variant A OOS (-15.6% vs -16.6%) and core + T4xE1 OOS (-5.3% vs -5.9%).
3. **Strategy 01 vs Variant A OOS**: -0.456 (strategy 01's own engine) vs -0.454 (v2 harness). Label which (s8 note).
4. **Chair dates**: code uses Powell to 2026-05-21, Warsh from 2026-05-22 (draft: Powell "..2026-05-22").
5. **"Measured cost" column** in draft Table 2 is CM (half-spreads, no fee). The strategy series' "net 1x" is CMF
   (with the $2/side fee). Label both.
6. **"about 8 round trips a year"** for BENCH-R: 4 a year in 2016-18, 8 from 2019 (B-12).
7. **USMPD correlations**: statement window -0.995 reproduces (D-26, n 70); the draft's conference-window -0.983 has
   no committed source (the BENCH-R hold window gives -0.979 [D], a different window); ADDENDUM s12 quotes the
   events label's -0.976 / -0.986. Quote only -0.995 (statement window) or source the other.
8. **Price levels in the draft**: s4 "0.5 tick at about 111 points" (ZN) and "one tick is about 0.45 bp at 1.10"
   (6E), and s7 "about 1,000 contracts" of ZN. Replace with the price-free C-7 wording or drop.
9. **E1 cost justification**: the draft's PENDING "measured TLT/UUP quoted spreads" does not exist in the repo; the
   committed justification is C-4 (Variant A's assumptions, fixed before any v2 return).
10. **"2x rows double trading and roll costs"**: for E1 the borrow fee is not doubled (C-3); say so.
11. **Placebo claim** (s4: "40-seed random-score placebo, best-of-eight averages 0.198, 90th percentile 0.833"): no
    committed source found. Drop or commit its output.
12. **Timing claim** (s4: "precedes our upper-bound bar on 40 of 62 meetings"): no committed source found. The
    median 28.8 s (n 63) and median start uncertainty 9.3 s are sourced (D-12, D-13).
13. **"ZT.c.0 is the illiquid delivery-month contract on 42 of 73 meeting days"**: no committed source found.
14. **Databento cost $8.53, audio 9.7 GB, video 65/67.4 GB**: no committed source in the listed set (video hours and
    62.8 GiB are in `hpg/fedpress_pkg/manifest/README.md`, D-25).
15. **Failed-ideas list (A2, s8)**: only v2, strategy 01 (VERDICT.md, t1_results_all.csv) and the press-conference
    rows have committed team-repo sources. Overnight drift, intraday momentum, pre-FOMC drift, hourly trend,
    month-end ZN timing, auction cycle, GTAA, carry, value, EWMAC, turn-of-month and "a team member's separate
    entry (0.28 IS / -1.05 OOS)" have no source in this repo. Either cite the other repository by URL or drop them.
    New rows to add from committed results: H1-primary G3 NO-GO (P-1..P-7); H2 not detected; H3 killed; H4 not
    detected (s15); v2 OOS fragile (V-29, V-30).
16. **A4 "two independent v2 implementations agree to about 1e-15 on placebo scores ... data cut at 2019-06-28"**: not
    in committed sources; use X-4, X-5, X-7 instead (prefix invariance 0.0 is committed; the cut date is not).
17. **Draft s4 cites `MERGED_FINAL_PLAN.md` s3.11 (R2-04)**: that file is not in the team repo (only its hash appears
    in `presser_H2H3H4_EXPLORATORY.md` s13). No PREREG-R ratification file exists. G3 was computed under ADDENDUM
    s8.2; it is NO-GO under one- or two-sided readings (P-14). Cite only committed files.
18. **PREREG_LOG times vs git**: 537c483 committed 23:11:18 UTC (log "about 23:15"); D-3 01:10:04 (file "about
    01:15"); Note 2 00:55:16 (file "about 00:58"); Note 3 01:16:17 although the file and the log say "about 01:35".
    In the note, use git commit times; the Note 3 discrepancy (stated time later than its commit) should be
    acknowledged or left out of the note.
19. **Local paths**: `preregistration/DEVIATIONS.md`, `presser_ADDENDUM.md`, `v2_oos/RUN_LOG.md`,
    `reproduce_report.json` and the HPG logs contain local or cluster paths. Never copy them into the note.
20. **Exposure box and "No H1 stance result is quoted"**: obsolete once G3 is reported; delete.
21. **"OOS shorter than 20% of about 10.75 years"**: 2 years / 10.75 = 18.6% [D]; fine as written.
22. **"Two of four registered falsifiers fire"**: correct (V-6..V-10); share is 73.9% (draft "74%" is fine).

---

## 21. Figures already committed (usable as Fig. 1 / Fig. 2)

| File | Content |
|---|---|
| `backtests/results/v2_oos/equity_T4xE1.png` | T4xE1 growth of 1 (excess of T-bill), net 1x, net 2x, gross; IS selection / validation / OOS shaded; lower panel OOS rebased to 1. Title states "decision rule FAILED; out-of-sample reported under D-3". |
| `backtests/results/v2_oos/equity_portfolio.png` | core_ER_6 vs core_ER_6 + T4xE1, IS and OOS shaded. |
| `backtests/results/v2_oos/equity_VariantA_T0fxE1.png` | Variant A frozen. |
| `backtests/results/presser_strategy/equity_benchr_ZT.png` | BENCH-R ZT cumulative P&L, % of $10m at N = 1,916, gross / net 1x / net 2x, OOS shaded; footer "Sharpe net 1x: IS -0.51, OOS 0.18; presentation of pre-registered trades; G3 stays NO-GO". |
| `backtests/results/presser_strategy/equity_h1primary_ZT.png` | H1-primary ZT, same layout. |
| `backtests/results/presser_strategy/equity_benchr_all_symbols.png`, `equity_h1primary_all_symbols.png` | ZT/ZF/ZN/ES small multiples. |
