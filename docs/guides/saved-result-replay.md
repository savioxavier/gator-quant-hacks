# Saved-result replay

One command, run from the repository root of a checkout, recomputes the headline tables and figures from committed
derived artifacts only (daily strategy return series, per-trade and per-answer rows) and compares them with the
committed tables:

```
python results_2/replay/replay.py            # writes to results_2/replay/replay_out/ (git-ignored)
python results_2/replay/replay.py --out <folder>
```

It needs Python 3.10+ with numpy, pandas, pyarrow, scipy and matplotlib. It reads no licensed data, no market data
and no price level, runs no strategy and uses no network. It refuses an output folder inside `backtests/`,
`preregistration/`, `hpg/`, `data/`, `archive/`, `backtest_snapshot/` or `results_2/metrics/`.

Exit code: 0 when every item passes, 1 when a recomputed number differs from the committed one beyond the item's
tolerance, 2 when an input is missing (each missing file is named on stderr).

| item | committed numbers checked | recomputed from | tolerance |
|---|---|---|---|
| `v2_oos_metrics` | `backtests/results/v2_oos/metrics.csv`, every row and column | the frozen D-3 run's daily files in `backtests/results/v2_oos/run/` | 1e-9 |
| `v2_is_selection` | `backtests/results/v2/windows_all.csv` (net 1x columns), `selection.csv`, the chosen combination | `backtests/results/v2_oos/run/daily_excess_all_combos_is.parquet` | 1e-9 |
| `v2_d4_metrics` | `backtests/results/v2_d4/metrics.csv`, every row | `backtests/results/v2_d4/daily_returns.parquet` | 1e-9 |
| `presser_strategy` | `backtests/results/presser_strategy/metrics.csv`, `sizing.csv`, `daily_returns.csv` | `per_trade.csv` (P&L rebuilt from ticks, $ per tick, half-spreads and fees) and the trading calendar of `daily_returns.csv` | 6e-6 relative (files written with 6 significant digits) |
| `presser_g3_headline` | `backtests/results/presser_h1/key_results.json`, G3 sample: n, mean, sd, median, hit, t, mean $ | `h1primary_trades.csv` | 1e-12 |
| `h234_family_holm` | `backtest_h234/results/family_holm.json`, the H4 frozen-fit block of `h4_results.json` | `h4_answer_rows.csv` (Clark-West, CR1 clusters, Webb wild bootstrap with the run's seed), `answer_summary.csv`, `qa/kill_switches.json` | 1e-12 |
| `results_2_v2_metrics` | `results_2/metrics/v2_metrics.csv` | `results_2/metrics/compute_metrics.py` on the committed v2 daily series | 1e-11 |

Figures written to the output folder: `metrics/equity_v2.png`, `metrics/equity_portfolio.png` (from the same series
as `v2_metrics.csv`) and `presser_equity_ZT.png`. A per-item record with the comparison counts, the largest
differences and every skipped number is in `replay_report.json`.

**Not recomputable from committed files** (printed as SKIP; a SKIP is not a pass of that number):
- the v2-sleeve turnover of the D-4 portfolio rows (fix 1, fix 2, both): the D-4 multiplier path is not a committed
  file (the original rows are recomputed);
- the net 2x, gross and turnover columns of `windows_all.csv`: the all-combination in-sample file holds net 1x only;
- the ES contract notional and turnover of the press-conference series: it needs the S&P 500 index level;
- the G3 bootstrap and permutation p-values, H2's raw p-value and the H3 kill decision: they need the suite's
  resampling code or answer-level P&L built from futures prices.

## Full reproduction

The replay checks that the published tables follow from the published series. Rebuilding the series themselves needs
the licensed inputs (ETF and futures daily files, Databento intraday files) and the backtest engine at a pinned
commit; see "Putting it together for a full rerun" in `docs/guides/data.md` and `docs/guides/reproduction.md`. With those set,
`bash backtests/run_all_backtests.sh` (or `sbatch hpg/backtest_all.sbatch` on HiPerGator) re-runs every stage and
compares it with the committed files; the v2 stage's `run_v2_chrono.py --reproduce` recomputes the D-3 run without
evaluating anything new.
