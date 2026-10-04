# Time-Series Momentum Backtester

A research-inspired Python project for testing simple time-series momentum and trend-following rules on liquid ETF data.

The project starts with a SPY 12-month momentum baseline, then expands into reusable backtesting utilities for parameter robustness, transaction costs, and multi-asset ETF trend following.

This is not financial advice. It is a reproducible research and software engineering project.

## Motivation

Time-series momentum asks whether an asset's own past return contains useful information about its next-period exposure. A simple long/cash rule is:

1. Compute an asset's trailing return over a lookback window.
2. Hold the asset when the trailing return is positive.
3. Move to cash, or a defensive proxy in extended variants, when the trailing return is negative.
4. Shift the signal by one trading day before applying it to returns.
5. Subtract transaction costs when the position changes.

The one-day shift is central. A signal computed with today's close cannot be used to earn today's return. In this project, the strategy position for today's return is based on yesterday's signal by default.

## Research Background

The implementation is inspired by:

- Moskowitz, Ooi, and Pedersen, "Time Series Momentum", Journal of Financial Economics, 2012.
- Hurst, Ooi, and Pedersen, "A Century of Evidence on Trend-Following Investing", 2017.

Those papers study diversified futures trend-following strategies. This repository is not an exact replication. It uses ETFs as accessible proxies and focuses on reproducible signal construction, backtesting discipline, transaction-cost handling, and robustness testing.

## Methodology

For each asset:

- Download adjusted close prices with `yfinance`.
- Compute daily percentage returns.
- Compute trailing momentum as `close / close.shift(lookback) - 1`.
- Create a binary signal: `1` if trailing return is above the threshold, else `0`.
- Shift the signal by one day before applying it to returns.
- Apply transaction costs in basis points when exposure changes.
- Compare strategy equity against buy-and-hold.

The default baseline is a 252 trading-day SPY lookback, roughly one trading year.

## Project Structure

```text
src/tsmom/
  data.py        # yfinance download/cache helpers
  signals.py     # trailing-return and moving-average signals
  backtest.py    # single-asset long/cash backtests
  metrics.py     # CAGR, volatility, Sharpe, drawdown, Calmar, hit rate
  portfolio.py   # equal-weight and multi-asset trend-following portfolios
  robustness.py  # parameter sweeps and walk-forward tests
  plotting.py    # report figures
  cli.py         # command-line workflows
```

## Quick Start

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m compileall src scripts
python -m tsmom.cli --help
```

Run the SPY baseline:

```bash
python scripts/run_spy_baseline.py --cost-bps 5
```

Run robustness tests:

```bash
python scripts/run_parameter_sweep.py
```

Run the multi-asset ETF portfolio:

```bash
python scripts/run_multi_asset_portfolio.py
```

Generated metrics are written to `reports/`. Figures are written to `reports/figures/`.

## Example Outputs

The scripts produce reproducible artifacts such as:

- `reports/spy_metrics.csv`
- `reports/parameter_sweep.csv`
- `reports/multi_asset_metrics.csv`
- `reports/figures/spy_equity_curve.png`
- `reports/figures/parameter_heatmap.png`
- `reports/figures/multi_asset_exposures.png`

The figures below use Yahoo Finance adjusted daily SPY closes from January 3, 2000 through September 30, 2026. The baseline uses a 252 trading-day lookback, a one-day signal lag, 5 bps per position change, and zero cash return. The sweep uses the same price history.

SPY momentum strategy versus buy-and-hold, shown as growth of $1:

![SPY cumulative strategy and buy-and-hold equity curves](reports/figures/spy_cumulative.png)

Annualized Sharpe ratios across momentum lookbacks and transaction costs:

![SPY parameter sweep Sharpe ratio heatmap](reports/figures/parameter_sweep.png)

The exact numbers depend on the data available from Yahoo Finance at run time, the sample period, transaction-cost assumptions, and selected parameters.

## Robustness Tests

`scripts/run_parameter_sweep.py` evaluates:

- Lookbacks: 21, 63, 126, 189, 252 trading days.
- Transaction costs: 0, 5, 10, 25 bps.

The resulting grid and heatmap help show whether performance is concentrated in one fragile parameter choice or is more stable across reasonable settings.

## Multi-Asset ETF Trend Following

The multi-asset script uses:

`SPY, QQQ, IWM, TLT, IEF, GLD, DBC, EFA, EEM, VNQ`

Signals are generated independently for each ETF. Active ETFs receive equal weight after signals are shifted. If no ETF is active, the strategy holds cash. The benchmark is an equal-initial-weight buy-and-hold basket over the common ETF history.

## Limitations

- This is not financial advice.
- ETF backtests are not exact replications of futures-based academic studies.
- Results depend on sample period, lookback, transaction costs, data quality, and asset universe.
- Trend following can underperform in sideways or sharply reversing markets.
- Backtests are historical simulations and do not guarantee future performance.
- Yahoo Finance data can be revised, missing, delayed, or adjusted differently over time.

## References

- Moskowitz, Tobias J., Yao Hua Ooi, and Lasse Heje Pedersen. "Time Series Momentum." Journal of Financial Economics, 2012.
- Hurst, Brian, Yao Hua Ooi, and Lasse Heje Pedersen. "A Century of Evidence on Trend-Following Investing." AQR Capital Management, 2017.
