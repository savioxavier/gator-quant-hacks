# trend_momentum_dual_sma (pre-registered 2026-10-03, before computing)

Common conventions: ../COMMON_SPEC.md.

## Source rules (in my words)
- Szakmary, Shen and Sharma (2010), "Trend-following trading strategies in commodity futures: A re-examination",
  JBF 34(2), https://ideas.repec.org/a/eee/jbfina/v34y2010i2p409-426.html: dual moving-average crossover and channel
  rules on 28 commodity futures 1959-2007; long when the short MA is above the long MA (short otherwise); channel
  rules long/short on breakouts of the n-day range. Reported: all dual-MA and channel parameterisations net of costs
  positive in at least 22 of 28 markets; robust to subperiods and data-snooping adjustments.
- Clare, Seaton, Smith and Thomas (2014), "Trend following, risk parity and momentum in commodity futures",
  https://openaccess.city.ac.uk/id/eprint/17846/1/COMMODITY%20pAPER.pdf: monthly 'price above its 10-month (6-12
  month) moving average' trend filter; reported: trend filters raise commodity Sharpe vs long-only and vs momentum
  (1992-2011).
- Levine and Pedersen (2016), "Which trend is your friend?", https://research.cbs.dk/en/publications/which-trend-is-
  your-friend/: MA crossovers and TSMOM are near-equivalent linear filters of past returns.

## Our implementation
Each future, signal s in {+1, -1}; w_i = s_i * 0.40 / sigma_i^EWMA / N_t, book to 10% (common spec), next_close.
Price = excess-return index.
- V1 weekly (decision at the last NYSE session of each calendar week, normally Friday): s = +1 if SMA50 > SMA200 of
  the daily price (both including the decision close), else -1.
- V2 monthly (month-end NYSE session): s = +1 if the month-end price > mean of the last 10 month-end prices
  (including the current one), else -1.
- V3 weekly channel: s = sign(close - (max_250 + min_250) / 2), max/min of the last 250 closes including today
  (s = -1 if exactly equal).
Weights held between decisions (targets fixed; engine rebalances drift daily).

## Variants (all reported; headline = best in-sample net Sharpe 1x): V1, V2, V3 as above.

## Adaptations and likely effect
- Applied to all 30 futures (the sources are commodity-only for Szakmary/Clare) with risk-parity sizing and a 10%
  book; the 1959-2007 / 1992-2011 source windows precede ours (2011-2024).
- Long/short (Clare's filter is long/flat for commodities): symmetric long/short matches Szakmary.
- Weekly decisions limit turnover vs daily crossovers. Expected correlation with S1 > 0.7.
