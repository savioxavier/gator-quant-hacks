# trend_momentum_xsmom_futures_amp: pre-registration (written 2026-10-03, before any computation of this strategy)

## Source rule (in my words)
Sources: Asness, Moskowitz, Pedersen (2013), "Value and Momentum Everywhere", JF
(https://www.johnhcochrane.com/s/Value-and-Momentum-Everywhere.pdf, read: section D eq. 1-2 and the diversified
portfolio paragraph); AQR "Value and Momentum Everywhere: Factors, Monthly" and "Century of Factor Premia" datasets.
* Momentum signal MOM2-12: cumulative raw return over the past 12 months skipping the most recent month.
* Within each asset class, weight w_i = c_t (rank(S_i) - average rank), so weights sum to zero; c_t scales the
  portfolio to one dollar long and one dollar short; monthly rebalancing.
* Diversified portfolio across asset classes: each class weighted by the inverse of its ex-post sample volatility
  so that each contributes roughly equally to risk.
* Non-stock universe: 18 country equity index futures, 10 government 10-year bonds, 10 currencies (forwards vs
  USD), 27 commodity futures (1972-2011).

## Source sample and reported numbers
* AQR VME MOM^AA (all non-stock asset classes, gross; Sharpe computed by the hunt from the AQR file): 0.43 for
  1972-01..2011-07, -0.08 post-publication 2013-07..2026, -0.38 for 2016-01..2024-09.
* AQR Century "All Macro Momentum" (gross): 0.58 for 1981-2011, -0.01 for 2012-2026.
* bt_2 also recomputes MOM^AA and the Century series on our exact in-sample and later windows (aqr_same_window.py).

## Our implementation (futures, gqh engine)
* Universe and classes: equity (F_ES, F_NQ, F_RTY, F_YM), rates (F_ZT, F_ZF, F_ZN, F_ZB, F_UB), FX (F_6E, F_6J,
  F_6B, F_6A, F_6C, F_6S), commodities (F_CL, F_HO, F_RB, F_NG, F_GC, F_SI, F_PL, F_HG, F_ZC, F_ZS, F_ZW, F_ZL, F_ZM,
  F_LE, F_HE).
* Month-end decisions (last NYSE session), filled next_close, held to the next month-end.
* Signal: cumulative excess return of the F_ index from the close of session t-252 to the close of session t-21.
* Within each class with >= 2 eligible instruments: w_i = rank_i - mean rank (zero-sum, notional), scaled to one
  unit long / one unit short; each class sleeve then rescaled to the same ex-ante vol (10%) with the trailing
  252-session covariance (min 60); the sum of the sleeves rescaled to 10% ex-ante vol, gross <= 3.
* Eligibility: >= 260 sessions of history, positive EWMA vol, traded in the last 10 sessions.
* Costs: realistic one-way map of the hunt task, roll days add a round trip; 2x stress reported.

## Pre-declared variants (all reported)
* V1: as stated (rank of the raw 12-1 return, class-neutral, equal ex-ante class risk).
* V2: as V1 but ranking the vol-adjusted signal (12-1 return / sigma_i, sigma = sqrt(252 EWMA(r^2, com 60))).
* V3: one pooled ranking across all eligible futures (no class neutrality), rank weights in notional scaled to one
  unit long / one unit short, then book to 10% ex-ante, gross <= 3.
* Selection for the standard series: highest in-sample net Sharpe (1x costs).

## Windows
In-sample: first live session (decisions from 2011-06-30) through 2024-10-02. 2024-10-03..2026-10-02 descriptive only.

## Adaptations and likely effects
* 4 US equity indices (correlation > 0.85) instead of 18 countries: the equity sleeve is mostly NQ vs RTY size/
  growth noise; 5 US Treasury maturities instead of 10 countries: the rates sleeve is a curve-steepness bet;
  6 FX futures instead of 10 forwards; 15 instead of 27 commodities. Expect a noisier and probably weaker result
  than MOM^AA, which itself was negative after publication.
* Ex-ante (trailing) class risk equalisation instead of ex-post inverse-vol weights: removes look-ahead.
* Excess-return index of the front contract (includes roll yield) as the return series, as AMP use futures excess returns.
* V3 pooled notional ranking lets high-vol commodities dominate the risk; reported as the source-faithful
  'no class neutrality' check.
