# v2 out-of-sample, evaluated once under deviation D-3

**The decision rule FAILED and that verdict stands.** T4xE1 failed its own pre-registered 2x-cost gate (full in-sample
Sharpe at 2x costs 0.387 <= 0.5). Deviation D-3 (`../../../preregistration/v2_DEVIATION_D3_OOS.md`, sha256
97585d3c...af1c69) allows the out-of-sample window 2024-10-03..2026-10-02 to be evaluated **once, for reporting
only**. The code, signals, parameters, costs and windows were frozen. Nothing was re-chosen, and the result cannot
reverse the verdict.

- Run: 2026-10-04 01:22:55-01:22:57 UTC, exit 0. Command, code and input hashes: `RUN_LOG.md`.
- The run's lock record is `run/oos_chosen.json`. Any further run is refused, D-3 included.

## Results (daily excess returns over the 3-month T-bill)

**T4xE1, the chosen combination** (TLT/UUP, entry at the next open):

| window | days | Sharpe net 1x | net 2x | gross | ann. return (arith, net 1x) | vol | max DD | turnover/yr | hit rate |
|---|---|---|---|---|---|---|---|---|---|
| selection 2016-01-04..2020-12-31 | 1259 | 0.154 | 0.053 | 0.269 | 1.25% | 8.11% | -16.1% | 35.0 | 49.4% |
| validation 2021-01-01..2024-10-02 | 943 | 0.687 | 0.664 | 0.721 | 10.00% | 14.56% | -17.8% | 15.9 | 50.4% |
| full IS 2016-01-04..2024-10-02 | 2202 | 0.441 | **0.387** | 0.507 | 5.00% | 11.33% | -18.8% | 26.8 | 49.8% |
| **OOS 2024-10-03..2026-10-02** | 501 | **0.607** | **0.544** | 0.687 | 3.82% | 6.30% | -6.6% | 17.7 | 49.9% |

OOS at 2x costs: 3.42% a year, max drawdown -6.8%. OOS total return including the T-bill: 7.9% a year (geometric).
The Newey-West t of the OOS mean is 0.84.

**Portfolio test** (T4xE1 as a fourth sleeve of core_ER_6, equal risk, 6% target, trailing covariance):

| | full IS Sharpe net 1x / 2x / gross | OOS Sharpe net 1x / 2x / gross | OOS ann. return (net 1x) | OOS vol | OOS max DD |
|---|---|---|---|---|---|
| core_ER_6 alone | 0.998 / 0.878 / 1.118 | 0.601 / 0.456 / 0.746 | 3.45% | 5.74% | -4.7% |
| core_ER_6 + T4xE1 | 1.038 / 0.909 / 1.173 | **0.870 / 0.703** / 1.043 | 4.97% | 5.72% | -5.3% |

The correlation of T4xE1 with core_ER_6 was 0.025 in sample and -0.16 out of sample. core_ER_6's own returns over
this window were not new information: they appear in the earlier portfolio work (its "later" window).

**Variant A as frozen (T0fxE1), reference:** full IS 0.355 / 0.312 / 0.411, OOS **-0.454 / -0.502 / -0.399** (net
1x / net 2x / gross). Its OOS return was -4.95% a year, with vol 10.9% and max drawdown -15.6%.

## Read the OOS number with this

The positive OOS Sharpe of T4xE1 comes from the end of the window. The table below is from `oos_concentration.csv`
and the pre-declared `run/by_chair_oos.csv`; it is descriptive and was written after the result was seen.

| T4xE1, net 1x | days | cumulative excess return | Sharpe |
|---|---|---|---|
| whole OOS | 501 | +7.5% | 0.61 |
| Powell, 2024-10-03..2026-05-21 | 409 | -3.1% | -0.36 |
| Warsh, 2026-05-22..2026-10-02 | 92 | +10.9% | 2.81 |
| OOS without its last 10 sessions | 491 | +1.7% | 0.17 |
| OOS without its last 20 sessions | 481 | -0.5% | -0.01 |

- The five best days carry 108% of the OOS daily-return sum. Two of them are 2026-09-23 and 2026-09-24, while the
  book held its capped short-TLT position.
- The portfolio gain is also a late-window effect. Over the Powell months, adding T4xE1 moved core_ER_6's Sharpe from
  0.97 to 0.94. Over the Warsh months, it moved it from -1.34 to 0.53.
- The in-sample record had the same feature: 74% of full-IS P&L came from 2022 (`../v2/summary_is.json`, falsifiers).
- The Deflated Sharpe with 11 trials is unchanged: 0.223 on the selection window and 0.436 on full IS.
- The D-1 scheduled-only de-risk list gives the same OOS result (0.6076 vs 0.6073; `run/sens_scheduled_only_oos.csv`).

## Cost assumptions

- **T4xE1 and Variant A** (75% TLT / 25% UUP):
  - trading costs of 1.5 bp (TLT) and 5 bp (UUP) per unit of NAV traded, one way;
  - a 30 bp a year borrow fee on short ETF weights;
  - cash earns the T-bill.
- **The three bases:**
  - **net 2x** doubles the trading costs, but not the borrow fee (`cost_mult` 2);
  - **gross** has no trading cost and no borrow.
- **Portfolio:**
  - each sleeve is net of its own costs;
  - overlay costs apply to multiplier changes: 2.375 bp for the T4xE1 sleeve, 0.75 bp for rpm_ES_MM, 1.0 bp for
    CAL_TSY_ME_ZN and 1.07 bp for S1;
  - net 2x doubles the sleeve and overlay costs, and gross has neither;
  - month-end decisions apply from d+2, under a leverage cap of 4.

## Metric definitions

| metric | definition |
|---|---|
| Sharpe | mean / sd x sqrt(252) |
| ann. return (arith) | mean x 252; `metrics.csv` also has the geometric and total-return versions |
| vol | sd x sqrt(252) |
| max DD | on the compounded excess-return curve |
| hit rate | share of days with a return above 0 |
| turnover/yr (strategies) | sum of daily one-way trades as a fraction of NAV (roll trades included), divided by years |
| turnover/yr (portfolio rows of `metrics.csv`) | overlay turnover only: 0.3 a year OOS. `fed_sleeve_turnover_per_year` is the T4xE1 sleeve's own trading times its multiplier: 5.8 a year OOS |

Windows never include days before a strategy's first position, which is 2015-12-31 for T4xE1.

## Checks

- **Before any OOS computation:** the in-sample run was reproduced exactly with the same code path and inputs.
  - Max abs difference 0 on all 7 committed files of `../v2/` and on the 3 frozen daily series of
    `backtest_snapshot/`.
  - T4xE1 was chosen, with 0.154 / 0.687 / 0.387 and DSR 0.2225 / 0.4361.
- **The D-3 run's own in-sample files** agree with `../v2/` (7/7 files) and the snapshot (10/10)
  (`backtests/tools/compare_results.py`).
- **The full-period series** reproduce every committed in-sample number to 1e-16 (`consistency.json`), and
  `is_consistency_max_abs_diff` is 0.
- **No licensed price levels:** the files hold returns, turnover, weights and signals only.

## Files

| file | content |
|---|---|
| `metrics.csv`, `metrics.md` | every series x window x basis |
| `daily_returns.csv`, `daily_returns.parquet` | daily excess returns (net 1x, net 2x, gross) of the four series, and T4xE1 turnover, 2015-12-31..2026-10-02 |
| `equity_T4xE1.png`, `equity_portfolio.png`, `equity_VariantA_T0fxE1.png` | equity curves, in sample and out of sample shaded, 1x and 2x |
| `oos_concentration.csv` | the descriptive split above |
| `consistency.json` | the checks above |
| `RUN_LOG.md` | the run record |
| `run/` | the frozen pipeline's own outputs (`run_v2_chrono.py`, D-3), including `run_stdout.log` |

To rebuild everything here from `run/`, without recomputing the backtest:

```
python backtests/v2/report_v2_oos.py && python backtests/v2/describe_v2_oos.py
```

`report_v2_oos.py` was written and tested on synthetic series before the run, and its hash is in `RUN_LOG.md`.
`describe_v2_oos.py` was written after the run.
