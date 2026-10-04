# trend_momentum_commodity_xsmom: commodity cross-sectional momentum (Miffre-Rallis 12/1)

Pre-registered 2026-10-03 before computing. Common conventions: ../COMMON_SPEC.md.

## Source rule (in our words)
Miffre & Rallis (2007, Journal of Banking and Finance 31(6), "Momentum strategies in commodity futures
markets"): at the end of each month rank the commodity futures on their past R-month return (R = 1, 3, 6, 12);
buy the top quintile ("winners") and sell the bottom quintile ("losers") with equal weights, hold H months
(H = 1, 3, 6, 12), fully collateralised. The 12-month formation / 1-month holding strategy is the best one.

- URL: https://risk.edhec.edu/publications/momentum-strategies-commodity-futures
- Source sample: 31 US commodity futures, January 1979 - September 2004 (nearest contract, rolled before expiry).
- Reported: 13 of 16 momentum strategies profitable; 12/1 earns about 14.6%/yr with about 25.6% vol (Sharpe
  about 0.57 on the long-short; gross, no costs).
- Post-publication evidence: Hollstein, Prokopczuk & Tharann (2021, QJF 11(4); SSRN 3567629): 1-year
  momentum 7.44%/yr significant over the full sample but much attenuated after financialisation (2004+).
  AQR VME commodity momentum (gross, our calc): Sharpe 0.52 1972-2011, -0.20 post-publication 2013-07..2026;
  AQR Century commodities momentum -0.02 for 2012-2026.

## Our implementation
- Universe: F_CL F_HO F_RB F_NG F_GC F_SI F_PL F_HG F_ZC F_ZS F_ZW F_ZL F_ZM F_LE F_HE (15).
- Month-end t: eligible commodities (common eligibility); require >= 6 eligible, else flat.
- Signal: cumulative excess return of the F_ index over the formation window (no skip month):
  prod(1 + r_i) - 1 over the last 252 sessions (V1, V2) or 126 sessions (V3).
- Long the 3 highest, short the 3 lowest (top/bottom quintile of 15). Ties broken by ticker order.
- Weights: V1 and V3 equal notional within legs (+1/3, -1/3); V2 risk units (+/- 0.40/sigma_i/6) i.e. 1/sigma_i
  weighting with equal risk per position. Then book to 10% (gross cap 3). Hold to next month-end, next_close.
- Variants (pre-declared, all reported): V1 12-month EW; V2 12-month inverse-vol; V3 6-month EW.
- Headline: best in-sample net Sharpe of V1-V3.

## Adaptations and likely effect
- 15 CME commodities instead of 31 (no softs, no LME metals, no feeders/lumber): fewer independent bets, the
  quintile is only 3 names, so idiosyncratic noise is higher -> lower Sharpe than the source and more
  sensitivity to energy (4 of 15 names, highly correlated CL/HO/RB).
- Sample 2011-2024 is entirely post-publication and post-financialisation, where the source evidence says the
  effect is attenuated or gone.
- Vol-targeted to 10% (source: equal-weight notional, about 25% vol): Sharpe is unaffected by the level but
  time-varying scaling can change it slightly.
