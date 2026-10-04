# Fed communication v2 backtest

Pre-registration: `../../preregistration/HYPOTHESIS_v2.md` (Amendments 1-3 and the clarification, sha256
464f8a5b...8a2e; the Amendment-1 version the runner originally pinned was 6083d3ef...d910). Deviations:
`../../preregistration/DEVIATIONS.md` (D-1, D-2), written before any return on real stance scores.

## Verdict: decision rule FAILED; out-of-sample evaluated once, for reporting only (deviation D-3)

| | value |
|---|---|
| Chosen combination (max net 1x Sharpe, selection 2016-01-04..2020-12-31) | T4xE1 |
| Selection Sharpe, net 1x | 0.154 |
| Validation Sharpe, net 1x (2021-01-01..2024-10-02) | 0.687 (target 0.7) |
| Full in-sample Sharpe at 2x costs (rule: > 0.5) | 0.387 |
| Decision rule (validation > 0 and full-IS 2x > 0.5) | **FAILED**; the verdict stands |
| Out-of-sample (2024-10-03..2026-10-02) | evaluated **once**, for reporting only, under deviation D-3 (2026-10-04 01:22:57 UTC): Sharpe 0.607 net 1x, 0.544 net 2x. It cannot reverse the verdict and is never evaluated again |

The decision record of the rule is `../results/v2/oos_not_evaluated.json`. Deviation D-3
(`../../preregistration/v2_DEVIATION_D3_OOS.md`) allowed one out-of-sample evaluation for reporting, with nothing
re-chosen; its record is `../results/v2_oos/run/oos_chosen.json`, and its results and run log are in
`../results/v2_oos/`. Full in-sample tables: `../results/v2/` and `../results/summary.md`.

## One-shot out-of-sample lock

The out-of-sample window is evaluated at most once, and it was, under D-3. Every new run is refused; the one
exception is `run_v2_chrono.py --reproduce` (below), which recomputes the committed D-3 run, compares it with the
committed files and evaluates nothing new. While `../results/v2/oos_chosen.json` or
`../results/v2/oos_not_evaluated.json` exists:
- `run_v2_chrono.py` refuses to run (with `--skip-if-complete` it exits 0 after checking that the document scores
  are the file the completed run used), whatever `--out` is given;
- `run_v2.py run` refuses before gqh-flow-clock or any data is loaded;
- `stage_oos` refuses as well (defence in depth);
- the D-3 unlock (`V2_OOS_DEVIATION`) wrote only to `../results/v2_oos/run`, and the record there refuses any further
  D-3 run;
- `../run_all_backtests.sh` reproduces the D-3 run (below) when the v2 inputs are set; otherwise it prints the records
  and skips the stage.

## Reproducing the committed run

```
cd <GQH_REPO>
GQH_REPO=<root>/v2/gqh-flow-clock GQH_DATA_DIR=<root>/v2/data V2_WORK_ROOT=<root>/v2/work PYTHONIOENCODING=utf-8 \
  python <team repo>/backtests/v2/run_v2_chrono.py --reproduce
```

On HiPerGator, `sbatch hpg/v2_oos.sbatch` from the repo root does the same (a small CPU job; it needs the v2 input
bundle in the home directory and no market files; see its header).

`--reproduce` recomputes the committed in-sample run and the one D-3 out-of-sample evaluation with the same code
path (`pipeline_is`, `stage_oos`), the same inputs, the committed combination T4xE1 and the same windows. It never
evaluates the window:
- it refuses unless `../results/v2_oos/run/oos_chosen.json` and the failed-rule record
  `../results/v2/oos_not_evaluated.json` (`oos_evaluated` false) exist, and refuses `V2_OOS_DEVIATION`;
- it clears and writes only `$BACKTEST_RERUN_DIR/v2_reproduce` (default `../rerun/v2_reproduce`, git-ignored). It
  refuses a folder not named `v2_reproduce`, one that is or contains `../results`, `..` or the repo root, one below
  `../results`, and an explicit `BACKTEST_RERUN_DIR` inside this repository (other than `../rerun`) or above it. It
  writes no decision record (the out-of-sample record is `oos_reproduced.json`, the failed-rule record
  `oos_not_evaluated_reproduced.json`);
- it chooses nothing: the in-sample selection must give T4xE1, the decision rule must fail, as committed, and the
  in-sample files must agree with `../results/v2/` before the out-of-sample stage runs. If they differ, the verdict is
  FAIL and nothing is computed on the out-of-sample window.

It compares every number with fixed file sets of the committed tree (commit 6a61ef9, listed in `RUN_LOG.md`; a
missing file is a difference): the 7 in-sample files of `../results/v2/` and its failed-rule record, the 18 files of
`../results/v2_oos/run/` (out-of-sample, portfolio, Variant A; `run_stdout.log` left out) and
`../results/v2_oos/metrics.csv` and `daily_returns.parquet` (rebuilt with `report_v2_oos.py`'s functions). The
tolerance is rtol 1e-9 / atol 1e-12 (`../tools/compare_results.py`). It prints PASS or FAIL and a headline block
(reproduced next to committed: T4xE1's selection, validation and full in-sample Sharpe at net 1x and 2x; its
out-of-sample Sharpe net 1x, net 2x and gross, annualised return, vol and maximum drawdown; the out-of-sample Sharpe of
core_ER_6 and core_ER_6+T4xE1). It writes `reproduce_report.json` (verdict, headline, comparisons, chosen combination,
code and input sha256 against `RUN_LOG.md`) and exits 1 on any difference. The code hashes in `RUN_LOG.md` are those
of the files committed at 6a61ef9; only `run_v2.py` and `run_v2_chrono.py` are expected to differ (this mode was added
after the D-3 run).

## Files

| file | what |
|---|---|
| `run_v2.py` | the runner (modes `check`, `smoke`, `run`); paths come from environment variables |
| `v2lib.py` | signals, weights, simulation and statistics helpers |
| `run_v2_chrono.py` | the entry point of the reported run: run_v2's own pipeline on the chrono stance scores, with the current pre-registration hash and the D-1 scheduled-only sensitivity; `--reproduce` recomputes the committed D-3 run |
| `report_v2_oos.py`, `describe_v2_oos.py` | the D-3 report (metrics, daily returns, equity curves) and its descriptive split, from `../results/v2_oos/run` |
| `adapt_v2.py` | chrono walk-forward document scores -> `score/doc_scores.parquet` |
| `score/doc_scores.parquet` | the document scores the reported run used (sha256 0e0c1ca7...3ba0, recorded in `summary_is.json`) |
| `score/doc_scores_lexonly.parquet` | the same 1,098 documents with the lexicon columns only (adapter input) |

Shared wiring (`check_chrono.py`, `wirelib.py`, `summarize.py`) is in `../wire/`.

## Inputs that are not in git

`run_v2.py check|smoke|run` also needs, under `V2_WORK_ROOT`, the files of the original work root:
`fedspeak_v2/corpus/fomc_dates.csv` and `fomc_dates_variantA_style.csv`, the strategy-01 FOMC dates and trial log
(`savio_gqh/strategies/01/...`), `fedspeak/extend/speech_scores_2011_2026.csv`, `fedspeak/replicate/signal.parquet`,
and `edges/combine/combine.py` with `edges/series/PORT_core_ER_6.parquet`. It also needs a clone of
gqh-flow-clock (`GQH_REPO`, for `src.engine`) and its data cache (`GQH_DATA_DIR`). They are needed only for
`check`, `smoke` and `--reproduce`. The v2 input bundle `gqh_v2_bundle.tgz` holds all of them (`v2/gqh-flow-clock`,
`v2/data`, `v2/work`, checked by `v2/MANIFEST.sha256`; its `v2/README.txt` explains the layout);
`../../hpg/backtest_all.sbatch` (and `../../hpg/v2_oos.sbatch`, which runs only this stage) unpacks it on
HiPerGator.

## Implementation choices (fixed before any return was computed)
1. **Timing.**
   - Every document dated d, whatever its release time, first enters the consensus at the first session strictly
     after d. This applies equally to 14:00 statements and minutes, the 11:00 and 08:00 unscheduled 2019/2020
     statements, timed speeches, weekends and holidays.
   - E1 fills at that session's open (engine `next_open`). E2 fills at that session's close (engine `next_close`).
2. **Variant A parameters, frozen:**
   - consensus half-life 20 sessions, equal weight per document;
   - expanding z with ddof 1 and a minimum of 252 observations;
   - 10% vol target on the unit hawkish mix, vol floor 4%, gross cap 1.5, clip 2;
   - no-trade band of 10% of current gross, with a trade forced on the FOMC interval, the interval after it, and
     when the book is flat;
   - FOMC dates in Variant A's style: strategy 01's list before 2015, the corpus list from 2015. The two lists
     agree exactly for 2015 to 2024-10.
3. **z clock and start date.**
   - The z clock counts sessions from 2015-01-02, the first session of the corpus. The first valid z is
     2015-12-31.
   - E1 holds its first position from the open of 2015-12-31. E2's first held return is on 2016-01-04.
   - So the selection window is not delayed: it starts 2016-01-04 for every combination.
   - Window statistics never include days before the first position.
4. **T1 and T2 (FOMC-RoBERTa).**
   - Document score = share hawkish minus share dovish. There is no hit-count keep rule: every document injects.
   - T1 uses speeches only. T2 uses speeches, statements, minutes and press conferences.
5. **T3 (T2 orthogonalised to rate momentum).**
   - Momentum M_t is the decayed sum (half-life 20) of daily DGS2 changes, with DGS2 lagged two sessions from
     the entry session. It equals DGS2 minus its EWMA, up to the constant factor lambda.
   - Each day, C_T2 is regressed on [1, M] by expanding OLS over sessions from 2015-01-02 to t. The residual on t
     is standardised by the sd (ddof 1) of that fit's residuals, whose mean is 0. This is Variant A's expanding z
     applied point in time, with a minimum of 252 observations.
6. **T4.**
   - T4 = 0.5 x (z of the lexicon consensus + z of the RoBERTa consensus), on T2's document set. It is not
     re-standardised before the clip at 2.
   - The lexicon leg uses the primary `lex_score` and the frozen keep rule (H+D >= 5). As the scoring notes
     notes, almost no statements pass that rule after 2017.
7. **E1:**
   - Variant A exactly: 75% TLT / 25% UUP, vol from open-to-open returns ending at the entry open.
   - Costs 1.5 / 5 bp per unit traded, plus the engine's 30 bp/yr borrow on short ETF weights.
8. **E2:**
   - 75% F_ZN / 25% short F_6E.
   - Vol from close-to-close returns ending at the decision close (strictly point in time).
   - The rates leg is halved for the position held over the announcement session.
   - Costs 1 bp each, plus one extra round trip on each roll day (the engine's roll flags). There is no borrow on
     futures.
9. **Returns and costs.** Returns are excess over the T-bill, from the engine. "2x" sets cost_mult = 2, which
   doubles trading and roll costs but not the borrow fee.
10. **Selection and decision rule.**
    - Selection: the maximum net 1x Sharpe over 2016-01-04..2020-12-31.
    - Decision rule: validation (2021-01-01..2024-10-02) net Sharpe > 0, AND net Sharpe at 2x costs over the
      full in-sample period (2016-01-04..2024-10-02) > 0.5.
    - The validation Sharpe is also reported against the 0.7 target.
11. **Deflated Sharpe.**
    - 11 trials: the 8 combinations' selection-window Sharpes plus the `sharpe_1x` of Variant A's 3 logged rows.
      Row 3 repeats row 2, so n = 10 is reported as a sensitivity.
    - DSR is computed on the selection window and on the full in-sample period.
12. **Portfolio test.**
    - Built by `combine.build` verbatim: equal risk, 6% target, trailing 252-day covariance (minimum 126
      observations), month-end decisions applied from d+2, leverage cap 4, overlay costs.
    - The fourth sleeve's series starts on its first held day. Its instrument gross is the sum of |held weights|.
    - Overlay cost: 2.375 bp for E1 (the 75/25 blend), 1.0 bp for E2.
13. **Chairs** (federalreserve.gov Board membership page, cached in the corpus build):
    - Yellen 2014-02-03 to 2018-02-03;
    - Powell 2018-02-05 to 2026-05-22;
    - Kevin Warsh from 2026-05-22. That day is assigned to Warsh.
14. **Variant A reference.** Reported two ways:
    - as frozen (strategy 01 corpus from 2011, z clock from 2011-01-03);
    - with the v2 2015 warm-up.

    Neither is used for selection. In OOS, Variant A is computed only for the per-chair table, and only after the
    chosen combination's OOS record has been written.

