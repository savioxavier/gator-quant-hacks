# Gator Quant Hacks

This repository contains research, preregistered tests, and backtests for a systematic trading project on Federal Reserve communications. The work studies whether Fed text and press-conference features help explain or predict moves in interest rates and the US dollar. The reported strategies did not pass all of their preregistered decision rules; see the report for results and limitations.

## Start here

- [Full team report](report/REPORT.md) — research questions, data, methods, results, and limitations.
- [Documentation index](docs/README.md) — guided path through the study and its research notes.
- [Reproduction guide](docs/reproduction.md) — backtest inputs, requirements, and result records.
- [Results guide](docs/results-guide.md) — explains key metrics and how to read the findings.
- [Preregistration log](preregistration/PREREG_LOG.md) — timeline and record of preregistered plans and amendments.
- [Backtest overview](backtests/v2/README.md) — v2 decision rule, results, and reproduction notes.
- [Backtest results](backtests/results/summary.md) — summary of committed results.
- [Frozen backtest snapshot](backtest_snapshot/README.md) — provenance and reproduction information for the archived snapshot.
- [Massive 8-K challenge](massive-8k/README.md) — separate sponsor challenge (notebook + write-up). Not part of the Fed study.

## Repository layout

| Directory | Contents |
|---|---|
| `backtests/` | Maintained backtest code, wiring, and results. |
| `backtest_snapshot/` | Frozen snapshot of code, inputs, and outputs used for reported results. |
| `data/` | Data documentation and committed project data. |
| `docs/research/` | Literature reviews, feasibility checks, planning, and review notes. |
| `hpg/` | HiPerGator job and package documentation. |
| `nlp/` | Walk-forward stance-model documentation and pipeline. |
| `preregistration/` | Hypotheses, amendments, deviations, and the preregistration log. |
| `report/` | The full report and supporting material. |
| `strategies/` | Initial strategy hypothesis and review. |
| `massive-8k/` | Massive 8-K options challenge. Independent of the Fed study. |

Some reproduction workflows require licensed market data or local input bundles that are not committed. See the relevant backtest README before attempting a run.
