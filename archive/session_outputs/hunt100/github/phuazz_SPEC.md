# SPEC — the program being replicated

Faithful extraction of the methodology from *Beyond Passive Investing*, "Trend following (1/4):
Replicating your own program" (30 May 2026). This is the citable specification the code in
`scripts/` implements. Where the article is silent on an exact value, the assumption is marked
**[ASSUMED]** and must be reconciled before any number is trusted.

## Universe

- The 62 most liquid futures contracts, spanning six asset classes (equities, fixed income,
  currencies, energy, metals, grains, softs, livestock, cryptocurrency) organised into the
  **10 CFTC sectors**, across five exchanges (CME, EUREX, COMEX, NYMEX, ICE).
- Composition reflects accessibility and data history, not economic theory. Crypto is included
  despite short histories ("excluding on duration alone would be motivated reasoning given how
  much trend signal it provided since 2020") — note this is a **hindsight inclusion**.
- `scripts/config.py` encodes the sector structure faithfully but holds a **provisional** contract
  list — not yet two-source verified against the article's 62-name figure.

## Signal (held fixed throughout the series — Clenow 2013, Carver 2023)

Per contract, per trading day:

1. Four price-change z-scores over lookbacks of **1, 3, 6, 12 months** (≈ 21, 63, 126, 252 trading
   days). Each = (L-day price move) / (expected L-day move volatility), where the volatility comes
   from the estimator below. "Trend score = price move / market volatility."
2. **Average** the four forecasts.
3. **Clip** the average to a cap (forecast clipping) so no single market accumulates an enormous
   position after a large move. Cap value **[ASSUMED ±2]** — reconcile if the article's companion
   code specifies otherwise.

## Volatility estimator

- Trailing **63-day standard deviation of the contract's daily price *changes*** (≈ a quarter
  year) — **not** percentage returns. This is internally consistent with point-based back-adjusted
  continuous series (see Data) and is the same estimator used across the author's carry/trend work
  so signals remain comparable when combined.

## Volatility normalisation — two levels, order matters

1. **Contract.** Size each position so one unit of forecast corresponds to one unit of risk
   (position ∝ forecast / contract daily vol).
2. **Sector.** Aggregate contracts within their CFTC sector; rescale the sector basket to **4%**
   annualised vol using the basket's own 63-day realised vol.
3. **Portfolio.** Sum the ten sector baskets; rescale the portfolio to **10%** annualised vol.

A single portfolio-level rescaling alone would let energy noise dominate during commodity vol
spikes — hence sector-first. Normalising by CFTC sector (rather than a discovered grouping) is
itself a design choice the article revisits in Part 2.

## Execution

- **Cadence: weekly**, applied after settlement in each contract's home market. "Weekly rebalance"
  means *after this week's prices are final everywhere* — futures settle at different exchange-local
  times. Weekly is the compromise between daily (marginally higher Sharpe, much higher turnover)
  and monthly (loses signal stability).
- **One-day execution delay** between signal and fill.
- **Single-market notional cap: 5× NAV** — a live guard against pinned-rate regimes where
  short-rate contracts (SR3, ZQ, LEU) would demand huge notional vs near-zero realised vol. The
  **baseline backtest does not enforce the cap** (negligible aggregate Sharpe impact); a live
  implementation needs it.
- **Idle cash earns Fed Funds** (per the author's public description; not detailed in the PDF body
  — **[ASSUMED]** for any total-return figure).

## Data

- **Norgate Data**: per-contract OHLCV + pre-built continuous series.
- Continuous series are **arithmetically back-adjusted (point-based)**: at each roll the historical
  portion is shifted by the price difference between new and old front month, so the splice has no
  artificial gap. *This is why the vol estimator uses price changes, not percentage returns* —
  point-adjusted levels can be distorted (even negative) far back, but their day-to-day **changes**
  are clean.
- Rolls: cash-settled contracts on the business day before final trading; deliverables on the
  business day before First Notice Day.
- `Close` is the official **exchange settlement price**, not the last-trade print — which is what
  margin and risk calculations clear against.

## Published results (the reconciliation targets)

| Metric | Value | Note |
|---|---|---|
| Sample | 1995 – Apr 2026 | ~30y, deliberately drops the 1980s–90s "golden era" (Sharpe ~2.1 in the 1990s alone). Do **not** quote pre-1995 as representative. |
| Sharpe (gross) | 1.03 | gross of costs |
| Sharpe (net) | ~1.00 | after cost drag below; consistent with SG-Trend Index over the same window |
| CAGR | 11.3% | from the published equity curve / author's summary |
| Max drawdown | ~23% | full 62-market book |
| Turnover | 6–10× / year | continuous-trend program |
| Slippage | 2–3 bps one-way | lower for index/UST, higher for thin softs/metals |
| Cost drag | 30–50 bps / year | → Sharpe deduction of 0.03–0.04 |

## The three ways this backtest can be silently wrong

(Per vault rule — state these before trusting any number.)

1. **Roll / back-adjustment contamination.** Improperly rolled continuous series inject false
   breakouts. Proof point already in the vault: `commodity-futures-trend` shows a Donchian L/S
   booking **−92% on cocoa** over a window in which cocoa *trended +~300%* — the data, not the
   strategy, drove it. Mitigation: ratio- or point-back-adjusted vendor data with an explicit roll;
   and because the series are point-adjusted, normalise by **price changes, not % returns**. A naive
   percentage-return vol on point-adjusted levels is silently wrong.
2. **Look-ahead via settlement timing and rebalance lag.** "Weekly = after every market's close is
   final everywhere" plus a one-day execution delay. The leak is using the same-day close for both
   the signal and the fill, or ignoring exchange-local settlement times across time zones. Mitigation:
   lag signals and vol, apply weights to the *next* period's returns, and respect the one-day delay.
3. **Survivorship / hindsight universe.** Crypto is included only post-2020 "because it had trend",
   and the 62-name selection reflects *today's* liquidity and data availability. Both mildly flatter
   the headline. Mitigation: report the result with and without the hindsight-included sleeves, and
   never present the in-sample-favourable universe as a clean OOS claim.

## References (from the article)

Butler, Gordillo & Philbrick (2023); Carver (2023); Clenow (2013); DeMiguel, Garlappi & Uppal
(2009); Hurst, Ooi & Pedersen (2017); Michaud (1989); Moskowitz, Ooi & Pedersen (2012).
