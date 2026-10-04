# Backtest snapshot, 2026-10-03

This is the exact code, inputs and outputs behind the results reported on 2026-10-03. It is kept frozen as a provenance record. A consolidated, maintained version of these backtests goes in `backtests/`.

## Results

| Test | Verdict | File |
|---|---|---|
| Fed communication v2 (HYPOTHESIS_v2, Amendments 1-3) | Decision rule FAILED (full in-sample Sharpe at 2x costs 0.39 < 0.5); out-of-sample not evaluated | `results_final/summary.md`, `fedspeak_v2/backtest/` |
| Press-conference BENCH-R | Continuation before 2020, reversal after; neither significant | `presser_bt/backtest/results/` |
| Press-conference H1 (G3, Powell 2023-2026) | NO-GO: +0.5 ticks/meeting gross, p = 0.45 | `results_final/summary.md`, `presser_bt/backtest/results/` |

## Layout

- `presser_bt/`: ADDENDUM (frozen; identical to `../preregistration/presser_ADDENDUM.md`), events, Q&A segmentation and timing (`text/`), chrono stance scores (`text_chrono/`), backtest code, results, tables and QA.
- `fedspeak_v2/`: v2 runner and outputs, the scored documents, and DEVIATIONS (frozen; identical to `../preregistration/DEVIATIONS.md`).
- `wire/`: adapters that feed the walk-forward chrono-BERT scores (`../nlp/`) into both backtests.
- `run_results.sh`: the one command that produced `results_final/`.

## Re-running

Set these environment variables:
- `GQH_MARKET_DIR`: the licensed Databento files. They are **not** in git: ohlcv-1m, ohlcv-1s and bbo-1s for ZT/ZF/ZN/ES, 13:30-16:30 ET on the 75 press-conference days.
- `GQH_DATA_DIR`: the gqh data cache.
- `GQH_REPO`: a clone of github.com/minh-stakc/gqh-flow-clock.
- `CHRONO_ROOT`: the chrono-BERT work root from `../nlp/run_local.py`.
- `GQH_PY` / `CHRONO_PY` / `PY`: Python interpreters.

The v2 out-of-sample lock stays in force: a re-run never evaluates the out-of-sample window once a decision record exists.

## Data licensing

The trade logs keep tick moves, returns and P&L but no Databento price levels (`entry_px`/`exit_px` removed). Fed text and recordings are public-domain US government works. The stance-model labels come from gtfintechlab/fomc_communication (CC BY-NC 4.0).
