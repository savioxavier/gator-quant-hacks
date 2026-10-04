# trend_momentum_bk_trend_tstat_cf (pre-registered 2026-10-03, before computing)

Common conventions: ../COMMON_SPEC.md.

## Source rule (in my words)
Baltas and Kosowski, "Demystifying Time-Series Momentum Strategies: Volatility Estimators, Trading Rules and Pairwise
Correlations" (version of October 1, 2015). URLs: https://spiral.imperial.ac.uk/handle/10044/1/41472,
https://papers.ssrn.com/abstract=2140091; replication in the QuantConnect strategy library:
https://www.quantconnect.com/learning/articles/investment-strategy-library/improved-momentum-strategy-on-commodities-futures
- Monthly rebalancing. Generalised TSMOM: r = (1/N_t) sum_i X_i * (sigma_tgt / sigma_i) * r_i.
- TREND rule (eq. 23-24): regress the daily log futures price on a time trend over the past 12 months; X = +1 if the
  Newey-West t-statistic of the slope > +2, -1 if < -2, else 0 (stay out).
- Volatility: Yang-Zhang (2000) estimator, YZ^2 = overnight variance + k * open-to-close variance + (1-k) * Rogers-
  Satchell, k = 0.34 / (1.34 + (n+1)/(n-1)); the paper fixes a three-month estimation window (section 4.1.2).
- Correlation factor (eq. 18-19): CF = sqrt(N / (1 + (N-1) * rho_bar)); per-asset target = sigma_P,tgt * CF;
  the paper estimates average pairwise correlations on a six-month rolling window and uses sigma_P,tgt = 12%.
- Source sample and reported numbers: 75 futures, 1974-2013 (Table IV): full-sample TSMOM Sharpe 1.04 without vs 1.05
  with CF; post-GFC 2009-01..2013-02 gross 0.14 -> 0.29, at 10 bp costs 0.12 -> 0.26, at 50 bp 0.05 -> 0.14. YZ cuts
  TSMOM turnover by about 8%; TREND is about one third of SIGN's turnover with a similar (insignificantly different)
  gross Sharpe; TREND+YZ reduces turnover by more than one third without significant loss.

## Our implementation
Month-end decisions (last NYSE session), next_close. Price = excess-return index (see common spec).
- TREND: OLS of log p on t = 1..252 over the last 252 sessions; Newey-West (Bartlett) variance of the slope with
  lag 21 sessions (the paper does not state the lag); X = sign if |t| > 2 else 0.
- YZ volatility: 63 NYSE sessions of the aggregated front-contract OHLC (common spec), annualised x 252, lagged one
  session; requires >= 40 valid overnight observations.
- rho_bar: average pairwise correlation of the signed daily excess returns X_j * r_j over the trailing 126 sessions,
  computed over the instruments with X != 0 (needs >= 2 such instruments, else rho_bar = 0); CF uses N = N_t, the
  number of eligible instruments (the paper's N_t), so months with many X = 0 run below target (as in the paper).
- w_i = X_i * (0.10 * CF) / sigma_i / N_t; gross <= 3 (pro-rata cut). Natural sizing, no covariance rescale.

## Variants (all reported; headline = best in-sample net Sharpe 1x)
- V1: TREND + YZ + CF (the paper's full proposal, 10% portfolio target instead of 12%).
- V2: TREND + YZ, CF = 1, then book to 10% (trailing covariance rescale, gross <= 3).
- V3: SIGN(12-month excess return) + EWMA vol (com 60) + CF (isolates the correlation adjustment on standard TSMOM).

## Adaptations and likely effect
- 30 instead of 75 futures and 2011-2024 instead of 1974-2013: fewer independent bets; the window is the post-GFC
  regime in which the paper itself found TSMOM weak (expect Sharpe well below 1).
- NW lag 21 assumed; a longer lag gives fewer active signals (more zeros).
- YZ from front-contract UTC-day OHLC (open is 00:00 UTC, overnight gap is the CME daily halt); YZ is then close to
  Rogers-Satchell + open-to-close variance; effect: volatility level similar, slightly smoother.
- The paper's eq. 20 text names close-to-close variance; we use Yang-Zhang's original open-to-close term.
- Signed-return correlation (consistent with eq. 12 for long/short books); the paper's Figure 7 plots unsigned
  correlations. 10% instead of 12% target only scales returns.
