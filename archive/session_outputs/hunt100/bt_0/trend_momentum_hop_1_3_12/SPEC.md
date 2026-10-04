# trend_momentum_hop_1_3_12 - Hurst-Ooi-Pedersen 1/3/12-month trend blend (century of trend), 30 CME futures

Pre-registered 2026-10-03 before computing any return of this strategy with the realistic cost map. Common
conventions: ../COMMON_SPEC.md. (V1's gross weights equal forward test 2's S1, already known: -0.13 IS / 0.14
later with S1's cost map; that number is not a choice input here.)

## Source rule (our words)
Hurst, Ooi & Pedersen (2017), "A Century of Evidence on Trend-Following Investing", Journal of Portfolio Management
44(1). At each month end, for each market, three time-series momentum signals: the sign of the past 1-, 3- and
12-month excess return; each signal's position is sized to a constant 40 % ex-ante volatility; the strategy is the
equal-weighted combination of the three horizons across all available markets; the portfolio is scaled to 10 %
ex-ante volatility (they use a 3-year rolling covariance of monthly returns for the book scaling).
Equivalent per market: s_i = mean(sign(R_21), sign(R_63), sign(R_252)), w_i = s_i x 0.40/sigma_i/N.
* URL: https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/AQR-JPM-Fall-2017.pdf
* Also: https://www.aqr.com/Insights/Research/Journal-Article/Demystifying-Managed-Futures ;
  https://www.aqr.com/Insights/Research/Journal-Article/You-Cant-Always-Trend-When-You-Want ;
  https://invesco.com/content/dam/invesco/emea/en/pdf/RRE_2024_Q2_NavigatingMomentum.pdf

## Source sample and reported numbers
* 67 markets (29 commodities, 11 equity indices, 15 bond markets, 12 currency pairs), 1880-2016, monthly.
  Net of simulated costs and 2/20 fees: about 11 % a year at 9.7 % vol, Sharpe about 0.76-0.77 net over the full
  sample (14.9 % gross of fees 1880-2013), positive every decade; about 0.41 net for 2010-2016.
* Babu et al. (2020, "You Can't Always Trend When You Want"): about 0.32 for 2010-2018.
* Live: SG Trend Index 0.30 net (Dec 1999 - Feb 2024); BTOP50 0.50 net 1987-2012.
* Ours before: S1 (= V1 rule) -0.13 IS / 0.14 later with S1's cost map (1.5 / 5 bp).
* Additional check computed here: the AQR TSMOM factor's Sharpe over our IS months and our monthly correlation with it.

## Our implementation
* V1 monthly: exactly forward2.s1_decisions (month-end decisions, sigma_i = sqrt(252 x EWMA(r^2, com 60)),
  w_i = s_i x 0.40/sigma_i/N, book to 10 % with the trailing 252-session daily covariance, gross <= 3, next_close),
  re-simulated with the realistic cost map. Also cross-checked against an independent re-implementation.
* V2 weekly: the same rule with decisions at the last NYSE session of each week (Friday close or the last session
  before a Friday holiday).
* V3 continuous horizon signals: s_i = mean over h in {21, 63, 252} of clip(R_h / (sigma_daily_i x sqrt(h)), -1, 1),
  with R_h the cumulative excess return over the last h sessions and sigma_daily_i = sigma_i / sqrt(252); monthly
  decisions, otherwise as V1.

## Adaptations and likely effects
* 30 CME futures instead of 67 global markets: fewer independent bets, lower Sharpe than the paper.
* Book scaling with a 252-session daily covariance instead of a 3-year monthly covariance: faster risk response,
  similar Sharpe.
* No fees: our numbers are net of trading costs only (the paper's 0.76 is net of 2/20 fees, about 3-4 % a year).
* Sample 2011-08 .. 2024-10 (data constraint), mostly post-publication.
