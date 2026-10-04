# Reproducing the backtests

This guide explains what a reader needs before attempting to reproduce committed backtest results. The maintained workflow is in [`backtests/README.md`](../backtests/README.md); that file and the per-study guides are authoritative for commands and environment variables.

## What is reproducible from this repository?

The repository includes the maintained code, frozen signal inputs, result tables, and decision records. It does not include every input needed to rerun every stage. In particular, licensed Databento market files and some local research bundles are external. A run can therefore stop at a missing-input check even when the committed results remain readable and auditable.

| Workflow | Additional inputs | Instructions and committed record |
|---|---|---|
| Combined maintained suite | Python environment; licensed market data for press-conference stages; local input bundle for v2 | [`backtests/README.md`](../backtests/README.md), [`backtests/run_all_backtests.sh`](../backtests/run_all_backtests.sh) |
| v2 reproduction | `GQH_REPO`, `GQH_DATA_DIR`, `V2_WORK_ROOT` and the v2 work bundle; Python dependencies | [`backtests/v2/README.md`](../backtests/v2/README.md); committed metrics in [`backtests/results/v2/`](../backtests/results/v2/) and [`backtests/results/v2_oos/`](../backtests/results/v2_oos/) |
| Press-conference H1 | Licensed Databento 1-minute, 1-second, and BBO files described in `backtests/README.md` | [`backtests/README.md`](../backtests/README.md); results in [`backtests/results/presser_h1/`](../backtests/results/presser_h1/) |
| H2-H4 voice/face analysis | HiPerGator feature outputs or the committed reference run; see package instructions | [`hpg/fedpress_pkg/README.md`](../hpg/fedpress_pkg/README.md), [`hpg/fedpress_pkg/docs/HIPERGATOR_NOTES.md`](../hpg/fedpress_pkg/docs/HIPERGATOR_NOTES.md), and the H2-H4 results under `backtests/presser/backtest_h234/` |
| Frozen snapshot | Its archived inputs and environment, including external data where specified | [`backtest_snapshot/README.md`](../backtest_snapshot/README.md) |

## Safe starting point

1. Read [`backtests/README.md`](../backtests/README.md) to review the suite, environment variables, and data requirements.
2. Choose the specific study and follow its README. Avoid running the full suite until you have confirmed that its external inputs are available.
3. Keep rerun outputs in the documented ignored rerun directory. The maintained runner includes reproduction checks and protects the v2 out-of-sample decision record.
4. Compare any reproduction with the committed results and records. A new run does not replace the preregistered verdict or the historical record of the reported run.

## Reading historical records

[`backtest_snapshot/`](../backtest_snapshot/) is a frozen provenance record. [`backtests/`](../backtests/) is the maintained runner and result layout. A snapshot may predate later permitted reporting steps, so use the dates, preregistration, deviation record, and current report to understand which results were available at each point. The v2 out-of-sample window was evaluated once under deviation D-3 for reporting; the failed in-sample decision rule still stands.

## Data sources

Where every dataset comes from, its licence, what is committed, and how to obtain the private inputs (with the SHA-256 of the copies used): [`data/README.md`](../data/README.md). The public part of the v2 input bundle is in [`backtests/v2/inputs/`](../backtests/v2/inputs/).
