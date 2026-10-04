# Sharpe ratios: one page

All Sharpe ratios are net of costs, annualised from daily excess returns over the T-bill. In-sample is
2016-01-04..2024-10-02; out-of-sample is 2024-10-03..2026-10-02 (evaluated once under deviation D-3). Every number
below was computed on the local PC and reproduced on HiPerGator (`backtests/results/v2_oos/hpg_reproduction/`,
`backtests/results/v2_d4/hpg_reproduction/`).

## Main strategy and portfolio

| Strategy | In-sample, net / 2x costs | Out-of-sample, net / 2x costs | Source |
|---|---|---|---|
| v2 T4xE1, as committed | 0.441 / 0.387 | **0.607 / 0.544** | `backtests/results/v2_oos/metrics.csv` |
| v2 T4xE1, both D-4 fixes | 0.446 / 0.392 | **0.621 / 0.554** | `backtests/results/v2_d4/metrics.csv` |
| core_ER_6 alone | 0.998 / 0.878 | 0.601 / 0.456 | `backtests/results/v2_oos/metrics.csv` |
| core_ER_6 + v2 T4xE1 | 1.038 / 0.909 | **0.870 / 0.703** | `backtests/results/v2_oos/metrics.csv` |
| core_ER_6 + v2 T4xE1, both D-4 fixes | 1.042 / 0.913 | 0.871 / 0.703 | `backtests/results/v2_d4/metrics.csv` |
| Walk-forward re-selection, both fixes | 0.698 / 0.670 (2021-01-04..2024-10-02) | 0.621 / 0.554 | `backtests/results/v2_d4/metrics.csv` |

## What the stance model adds (D-4, both fixes, net)

| Benchmark (same sizing and costs) | In-sample | Out-of-sample |
|---|---|---|
| Lexicon leg alone (T4's documents and processing) | 0.524 | -0.297 |
| Stance model alone (T2xE1) | 0.232 | 0.563 |
| Rate momentum alone (T3's control) | 0.569 | -0.263 |
| Long 75/25 TLT/UUP, same sizing | -0.031 | -0.838 |
| Variant A, frozen lexicon (T0fxE1) | 0.364 | -0.470 |

Source: `backtests/results/v2_d4/metrics.csv`.

## Press conference (ZT, net; D-3 presentation of pre-registered trades)

| Strategy | In-sample | Out-of-sample | Source |
|---|---|---|---|
| H1-primary | -0.17 | -1.33 | `backtests/results/presser_strategy/tables.md` |
| BENCH-R | -0.51 | 0.18 | `backtests/results/presser_strategy/tables.md` |

## Read the headline with these facts

- v2 failed its pre-registered decision rule: full in-sample Sharpe at 2x costs 0.387 (0.392 with the fixes), below
  the required 0.5. That verdict stands; the out-of-sample window was opened once, for reporting only (D-3).
- The out-of-sample gain is not statistically significant (Newey-West t 0.84) and comes from the last months:
  -0.36 over the 409 Powell sessions, about 0 without the last 20 sessions.
- In-sample, the lexicon leg alone and plain rate momentum both beat T4; out-of-sample both lose money and the stance
  model leg carries T4's result. The stance model's incremental value is not established.
- The press-conference strategies do not cover their costs in-sample; G3 for H1 is NO-GO.

Full detail: `docs/results/strategy-results.md`, `backtests/results/v2_d4/README.md`, and `docs/report/REPORT.md` sections 5.2-5.8.
