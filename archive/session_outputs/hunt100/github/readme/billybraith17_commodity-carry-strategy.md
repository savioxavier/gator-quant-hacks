# Systematic Commodity Carry Strategy

The project builds and backtests a long-only commodity carry strategy that dynamically selects the
most attractive **liquid** maturity on each of 15 commodity futures curves and holds them
equal-weighted with a monthly rebalance.

All analysis is in [`commodity_carry_strategy.ipynb`](commodity_carry_strategy.ipynb) — the
notebook is saved with outputs, so the full analysis (tables and charts) renders directly on GitHub.

## Motivation

Most of my work has centred on equities, and I wanted to broaden my understanding of other asset classes and
corners of finance. Building a simple ETF-style strategy end-to-end seemed to be a good way to do
that — and this one in particular gave me my first hands-on exposure to futures: their term
structure, roll mechanics, and the practicalities of trading a point on a maturity curve rather than
a single spot price.

## Strategy

- **Universe:** 15 commodity futures spanning energy (WTI crude, natural gas, RBOB gasoline,
  ULS diesel), metals (gold, silver, copper, aluminium, zinc) and agriculture/livestock
  (corn, wheat, soybean, sugar, coffee, live cattle).
- **Signal — implied roll yield:** on the last trading day of each month, every maturity on each
  curve is ranked by the per-month roll yield implied by its price gap to the adjacent
  shorter-dated contract. A positive value indicates backwardation at that point of the curve:
  the contract "rolls down" toward the shorter-dated price and earns carry if the curve is static.
- **Liquidity filters:** eligible contracts must have open interest ≥ \$100m and 1-month average
  daily traded volume ≥ \$30m (both in USD notional). The highest-yielding eligible maturity is held.
- **Portfolio:** one maturity per commodity, equal weights (1/15) reset at each month-end rebalance.

## Economic intuition

- **Where the premium comes from.** A commodity futures curve reflects the balance of inventories,
  storage costs and near-term supply and demand. When physical markets are tight — low inventories,
  strong spot demand — the curve tends to be **backwardated** (nearer contracts priced above further
  ones), and a long futures position earns a positive **roll yield** as its price converges toward
  the higher spot level over time.
- **Why select the maturity, not just the front.** The steepness of the curve varies both across
  commodities and along each curve. Rather than holding fixed front-month exposure, the strategy
  harvests carry more efficiently by holding the point on each curve with the strongest implied roll
  yield, subject to liquidity.
- **When it should do well / badly.** It should perform in backwardated, supply-constrained or
  inflationary regimes (e.g. the post-pandemic squeeze), and lag in **contango** regimes driven by
  oversupply and high inventories (e.g. the 2014–16 oil glut).
- **Honest caveat.** The strategy *targets* the carry premium, but as a long-only book its realised
  risk and return are dominated by broad commodity beta — which is why the drawdowns are large and
  why a long/short variant (see [Possible extensions](#possible-extensions)) is the natural next step
  to isolate carry from that beta.

## Results (Feb 2008 – Apr 2022)

| Metric | Gross | Net (2 bps per switch) |
|---|---|---|
| CAGR | 1.9% | 1.8% |
| Annualised return | 2.9% | 2.8% |
| Annualised volatility | 14.7% | 14.7% |
| Sharpe ratio | 0.20 | 0.19 |
| Max drawdown | −52.7% | −53.2% |

Returns are excess returns on a fully collateralised basis (no collateral yield added). The
strategy performs best in backwardated regimes — tight supply, low inventories, strong spot
demand (e.g. the post-pandemic squeeze) — and lags in contango regimes driven by oversupply
(e.g. the 2014–16 oil glut). Turnover is modest: on average about half the commodities switch
maturity at a given rebalance, so transaction costs have limited long-run impact.

## Data

The underlying daily futures data is **not distributed** with this
repository. To reproduce the analysis, point `DATA_DIR` in the notebook at a folder containing:

**`contracts_prices.csv`** — one row per contract per trading day, Jan 2008 – Apr 2022:

| Column | Description |
|---|---|
| `date` | observation date |
| `contract_code` | futures contract code (e.g. `CL`, `GC`) |
| `mat_month`, `mat_year` | contract maturity |
| `close` | close price in the contract's quote currency |
| `volume` | traded volume, number of contracts |
| `oi` | open interest, number of contracts |
| `last_trade_date` | contract expiry (last trade date) |

**`contracts_info.csv`** — contract metadata: `contract_code`, long/short names,
`underlying_name`, `contract_size`, `quote_currency` (`USD` dollars / `USd` cents), `unit`.

## Running it yourself

```bash
pip install -r requirements.txt
jupyter notebook commodity_carry_strategy.ipynb
```

The notebook writes two artefacts: `optimal_maturities.csv` (the selected maturity per commodity
per month-end) and `backtest_outputs.xlsx` (daily index levels, month-end holdings, turnover and
summary statistics).

## Possible extensions

- Long/short variant (long backwardation, short contango) to isolate the carry premium from
  long-only commodity beta.
- Alternative ways to select the held maturity, rather than simply taking the highest implied roll
  yield — e.g. a blended carry-and-liquidity score, or a supervised model (gradient-boosted trees, a
  small neural network) trained to predict each contract's next-month roll return from curve shape,
  liquidity and seasonality features.
- Blend carry with momentum, or average the roll-yield signal over the month to reduce
  single-day noise.
- Per-market execution cost model and collateral (T-bill) yield for total-return reporting.

## Disclaimer

This is an independent research project intended to demonstrate quantitative research methodology.
It is not investment advice, and no claim is made that the strategy is profitable or suitable for
live trading.
