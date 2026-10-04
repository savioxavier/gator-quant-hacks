# Cross-Asset Momentum / Trend-Following Strategy

**[🌐 Live Site →](https://spencerpain.github.io/cross-asset-momentum/)**

A full systematic implementation of time-series momentum (TSMOM) across equities, bonds, commodities, and FX — replicating the approach published by AQR / Man AHL and documented in Moskowitz, Ooi & Pedersen (2012).

## What it does

| Stage | Detail |
|---|---|
| **Universe** | 19 ETF proxies spanning 4 asset classes |
| **Signal** | 1M / 3M / 12M lookback returns → composite momentum score |
| **Sizing** | Per-instrument volatility scaling (15% target vol each) |
| **Portfolio** | Target-vol scaling to 10% annualized |
| **Backtest** | Walk-forward, monthly rebalance, 10bps transaction costs |
| **Analytics** | Sharpe, Sortino, max drawdown, Calmar, crisis alpha |
| **Plots** | 5 publication-quality charts |

## Universe

| Class | Instruments |
|---|---|
| **Equities** | SPY, EEM, EWJ, EZU, IWM, VGK |
| **Bonds** | TLT, IEF, IGOV, EMB |
| **Commodities** | GLD, SLV, USO, DBC |
| **FX** | FXE, FXY, FXA, FXC, UUP |

Data sourced from Yahoo Finance via `yfinance`.

## Project structure

```
cross-asset-momentum/
├── config.py               ← instruments, params, dates
├── main.py                 ← entry point
├── data/
│   └── loader.py           ← Yahoo Finance download + caching
├── signals/
│   └── momentum.py         ← 1M/3M/12M TSMOM signal generation
├── portfolio/
│   ├── sizing.py           ← per-asset vol-scaled weights
│   └── construction.py     ← portfolio target-vol scalar
├── backtest/
│   └── engine.py           ← monthly walk-forward backtest engine
├── analysis/
│   ├── performance.py      ← Sharpe, Sortino, drawdown, CAGR, etc.
│   └── regime.py           ← crisis alpha, NBER recession overlay
└── visualization/
    └── plots.py            ← all five charts
```

## Quick start

```bash
# Install dependencies
pip install -r requirements.txt

# Run (downloads data, caches to .cache/, writes results/ to disk)
python main.py

# Force re-download
python main.py --no-cache

# Custom output folder
python main.py --output results/myrun
```

## Output

All plots and CSVs are written to `results/` (configurable via `--output`):

| File | Description |
|---|---|
| `01_equity_curves.png` | Cumulative P&L vs 60/40 + drawdown + annual bars |
| `02_rolling_sharpe.png` | Rolling 12-month Sharpe ratio |
| `03_asset_class_contrib.png` | Stacked annual contribution by sleeve |
| `04_signal_heatmap.png` | Long / Flat / Short heatmap across time |
| `05_crisis_alpha.png` | Performance during GFC, COVID, 2022 rate shock |
| `performance_summary.csv` | Summary table: Sharpe, DD, CAGR, Sortino, Calmar |
| `crisis_alpha.csv` | Crisis-period breakdown |
| `backtest_returns.csv` | Daily return series (gross, net, benchmark) |
| `equity_curves.csv` | Cumulative equity curves |
| `weights.csv` | Daily final portfolio weights |
| `signals.csv` | Raw momentum direction (+1 / −1 / NaN) |
| `asset_class_contributions.csv` | Annual contribution by asset class |

## Configuration

All key parameters live in `config.py`:

```python
TARGET_PORTFOLIO_VOL   = 0.10   # 10% annualized portfolio vol target
TARGET_ASSET_VOL       = 0.15   # 15% per-instrument vol target
VOL_LOOKBACK_DAYS      = 20     # rolling window for realized vol
TRANSACTION_COST_BPS   = 10     # one-way cost per trade
MAX_LEVERAGE           = 3.0    # cap on portfolio scalar
MOMENTUM_WEIGHTS       = {"1M": 0.25, "3M": 0.25, "12M": 0.50}
```

## Methodology notes

- **12-1 momentum**: the 12-month lookback skips the most recent month (Jegadeesh & Titman 1993) to avoid the short-term reversal contamination.
- **Volatility scaling**: the per-instrument weight is `direction × (target_vol / realized_vol)`, so a quiet bond and a volatile commodity each contribute equal standalone risk.
- **Portfolio vol targeting**: after summing all scaled weights, a second scalar adjusts portfolio-level vol to the 10% target, accounting for cross-asset correlations.
- **Transaction costs**: 10bps one-way on the absolute weight change at each monthly rebalance — conservative enough to be realistic, loose enough to not distort the signal.

## References

- Moskowitz, T., Ooi, Y. H., & Pedersen, L. H. (2012). *Time Series Momentum*. Journal of Financial Economics.
- Hurst, B., Ooi, Y. H., & Pedersen, L. H. (2017). *A Century of Evidence on Trend-Following Investing*. AQR Capital Management.
- Jegadeesh, N., & Titman, S. (1993). *Returns to Buying Winners and Selling Losers*. Journal of Finance.
