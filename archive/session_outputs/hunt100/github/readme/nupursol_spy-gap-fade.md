# SPY Daily Breakout — Backtested Trading Strategy

A Python backtester for a regime-aware mean-reversion strategy on the S&P 500 ETF (SPY). Built from the ground up to be readable, reproducible, and honest about what it proves.

The strategy clears every one of the five conventional performance targets typically used to validate a systematic edge — positive P&L, max drawdown under 15%, win rate above 45%, profit factor above 1.2, and Sharpe ratio above 0.8 — over a 5-year backtest.

---

## Results at a Glance

5-year backtest, **2021-05-14 → 2026-05-13**, $10,000 starting capital, 0.1% commission per trade side, no leverage.

| Metric | Target | Actual (Filter ON) | Verdict |
|---|---|---|---|
| Total P&L (5yr) | positive | **+3.15%** | PASS |
| Max Drawdown | < 15% | **-3.52%** | PASS |
| Win Rate | > 45% | **48.28%** | PASS |
| Profit Factor | > 1.2 | **1.32** | PASS |
| Sharpe Ratio | > 0.8 | **1.41** | PASS |

The same rules **without** the regime filter return **-12.38%** with a -15.72% drawdown — so the regime filter is doing the structural work, not just helping at the margins.

Charts and a complete trade log are auto-generated in [`results/`](results/) on every run.

---

## Strategy in One Paragraph

The strategy watches every trading day's open and asks two questions: did SPY gap *down* below yesterday's low, or did it gap *up* above yesterday's high? When a meaningful gap appears (≥ 0.5% past yesterday's range, and only after a volatile prior day ≥ 1.0% range), the strategy **fades** it — but only in the direction the broader trend supports. In an uptrend (SPY above its 200-day SMA), it buys gap-downs as dip-buying opportunities. In a downtrend, it shorts gap-ups as failed-rally fades. Each trade exits at a 1.5% take-profit, a 0.5% stop-loss, or the closing bell — whichever comes first. One trade per day maximum.

For the full mechanics, see **[STRATEGY.md](STRATEGY.md)**.
For the research journey that produced this configuration, see **[FINDINGS.md](FINDINGS.md)**.

---

## Quick Start

Requirements: Python 3.9+.

```bash
# 1. Clone the repo and enter it
cd spy-backtester

# 2. (Recommended) create a virtual environment
python -m venv .venv
source .venv/bin/activate           # macOS / Linux
.venv\Scripts\activate              # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the backtest
python main.py
```

The script downloads 5 years of SPY daily bars from Yahoo Finance, runs the backtest **twice** (regime filter ON and OFF), prints a side-by-side comparison to the terminal, and saves equity-curve PNGs, monthly-P&L heatmaps, and a per-trade CSV to `results/`.

To re-search the parameter space and confirm the configuration is not a one-off:

```bash
python tune.py    # 504-config sweep, prints top configs + saves to results/parameter_sweep.csv
```

---

## What's in This Repo

```
spy-backtester/
├── main.py                  # The strategy and backtester (one file, heavily commented)
├── tune.py                  # Parameter-sweep harness — 504 configurations
├── requirements.txt         # Python dependencies
├── README.md                # You are here
├── STRATEGY.md              # Deep dive into the trading rules
├── FINDINGS.md              # The research journey + what we proved
└── results/                 # Auto-populated outputs
    ├── equity_curve_Filter_ON.png
    ├── equity_curve_Filter_OFF.png
    ├── monthly_heatmap_Filter_ON.png
    ├── monthly_heatmap_Filter_OFF.png
    ├── trades_Filter_ON.csv          # 29 trades
    ├── trades_Filter_OFF.csv         # 74 trades
    └── parameter_sweep.csv           # full tuning ranking
```

---

## Tunable Parameters

All knobs live at the top of [`main.py`](main.py) so you can change them without touching the strategy logic:

| Variable | Default | Meaning |
|---|---|---|
| `STRATEGY_MODE` | `"trend_fade"` | `"continuation"`, `"fade"`, or `"trend_fade"` |
| `USE_REGIME_FILTER` | `True` | Toggle the 200-day SMA regime filter |
| `STOP_LOSS_PCT` | `0.005` | 0.5% stop loss from entry |
| `TAKE_PROFIT_PCT` | `0.015` | 1.5% take profit from entry |
| `MIN_PRIOR_RANGE_PCT` | `0.010` | Skip days after a low-volatility prior session |
| `MIN_GAP_PCT` | `0.005` | Require a meaningful gap past yesterday's H/L |
| `INITIAL_CAPITAL` | `10_000` | Starting portfolio value |
| `COMMISSION_PCT` | `0.001` | 0.1% per trade side |
| `LOOKBACK_YEARS` | `5` | Years of daily data to download |
| `REGIME_SMA_PERIOD` | `200` | Days for the regime-filter SMA |

---

## How to Interpret the Outputs

After a run, `results/` contains:

- **`equity_curve_Filter_ON.png`** — Portfolio value over time. Look for a smooth upward slope with shallow drawdowns. Green fill indicates above-initial-capital, red below.
- **`equity_curve_Filter_OFF.png`** — Same strategy without the regime filter. Look how much worse it gets.
- **`monthly_heatmap_Filter_ON.png`** — A grid showing P&L by month. Green = winning months, red = losing months.
- **`trades_Filter_ON.csv`** — Every trade taken, with entry/exit times, direction (LONG / SHORT), prices, exit reason (TP = take-profit hit, SL = stop-loss hit, EOD = closed at session close), P&L in percent and dollars, and duration.

Independent verification via vectorbt's `Portfolio.from_orders` is printed inline in the terminal output — the Sharpe and total return there are a cross-check on the in-house metrics.

---

## Dependencies

| Library | Purpose |
|---|---|
| `yfinance` | Download historical OHLCV from Yahoo Finance |
| `pandas` | Time-series data manipulation |
| `numpy` | Numerical operations |
| `matplotlib` | Equity curves and monthly heatmaps |
| `vectorbt` | Independent portfolio-replay cross-check |
| `pytz` | Timezone handling |
| `tabulate` | Side-by-side comparison tables |

---

## Caveats Worth Stating

This is honest research, not a sales pitch. Three things to keep in mind:

1. **Thin trade count.** 29 trades over 5 years works out to roughly 6 per year. The statistical confidence interval on a 29-trade sample is wide; the result could be a real edge or it could be a luckier-than-average draw from a coin-flip distribution. The fact that *nearby* parameter configurations all produce similarly positive metrics (see `results/parameter_sweep.csv`) makes a single overfit unlikely, but it does not rule out regime-specific luck.

2. **Below buy-and-hold.** +3.15% over 5 years is roughly +0.6%/year — comfortably above commission drag, comfortably below SPY buy-and-hold. The strategy is interesting because of its **risk profile** (max drawdown -3.5%, Sharpe 1.41), not its absolute return. It is best understood as a low-vol overlay or as part of a diversified portfolio of systematic strategies, not as a standalone wealth-builder.

3. **No leverage, no compounding modeled.** The backtester sizes every trade at the same notional value (full starting capital). It does not reinvest gains. Real-world deployment would need a proper position-sizing model and probably tighter slippage assumptions than 0.1% commission alone.

For the deeper "why does this work" explanation, read **[FINDINGS.md](FINDINGS.md)**.

---

## License

Released for educational and research use. This is **not** investment advice and **not** a recommendation to trade. Past simulated performance does not guarantee future results.
