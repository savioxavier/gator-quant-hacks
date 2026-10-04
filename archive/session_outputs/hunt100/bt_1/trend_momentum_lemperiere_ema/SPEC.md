# trend_momentum_lemperiere_ema (pre-registered 2026-10-03, before computing)

Common conventions: ../COMMON_SPEC.md.

## Source rule (in my words)
Lemperiere, Deremble, Seager, Potters, Bouchaud, "Two centuries of trend following", Journal of Investment Strategies
(2014); https://arxiv.org/abs/1404.3274.
- Monthly closes p. Reference level pbar_n(t) = exponential moving average of past monthly prices excluding p(t),
  decay n months. sigma_n(t) = exponential moving average (decay n) of absolute monthly price changes.
  Signal at the start of month t: s_n(t) = (p(t-1) - pbar_n(t-1)) / sigma_n(t-1) (eq. 1).
- Fictitious constant-risk P&L: buy/sell sign(s_n) times 1/sigma_n contracts, hold one month (eq. 2). No costs.
- Saturation: monthly price change vs s_n is best fitted by a tanh with scale about 0.89 (eq. 3, Fig. 5).
- Source sample and reported numbers: 27 futures (7 commodities, 7 bond, 7 index, 6 FX), 1960-2013, n = 5:
  Sharpe about 0.8 (no costs), t = 5.9 (5.0 after removing the long bias); by decade 0.66, 1.15, 1.05, 1.12 and 0.75
  after 2000; Sharpe 0.57-0.83 for n = 2..10. Spot data 1800-2013 Sharpe 0.72, t = 10.5. The paper's Fig. 6 shows
  the strategy flat since about 2011.

## Our implementation
- p = excess-return index sampled at month-end NYSE sessions. pbar(t) = EWM(alpha = 1/n, adjust=True) of monthly p
  through month t-1 (shifted one month); sigma_n(t) = EWM(alpha = 1/n, adjust=True) of |p(t) - p(t-1)| through month t.
  s(t) = (p(t) - pbar(t)) / sigma_n(t), computed at each month-end with data through that close.
- Weights: w_i = sign(s_i) * 0.40 / sigma_i^EWMA / N_t, book to 10% (common spec), next_close, monthly targets.
- Requires at least 6 month-end prices for a signal (plus common eligibility of 260 sessions).

## Variants (all reported; headline = best in-sample net Sharpe 1x)
- V1: n = 5 months (the paper's main choice).
- V2: n = 10 months.
- V3: n = 5, saturating weights w_i proportional to tanh(s_i) * 0.40 / sigma_i / N_t, then book to 10%.

## Adaptations and likely effect
- The paper sizes in contracts by 1/sigma_n (price-change units); we size by EWMA return volatility and rescale the
  book to 10% with the trailing covariance: puts the rule on the common risk framework; small effect on Sharpe.
- 30 CME futures 2011-2024 vs 27 global futures 1960-2013; the paper itself reports the flat period since 2011, so
  expect a low Sharpe. Costs are charged (the paper has none); monthly sign changes keep turnover moderate.
- tanh(s) with unit scale (the paper's fitted scale 0.89 is close to 1).
