# trend_momentum_mop_tsmom12 - Moskowitz-Ooi-Pedersen 12-month time-series momentum (30 CME futures)

Pre-registered 2026-10-03 before computing any return of this strategy. Common conventions: ../COMMON_SPEC.md.

## Source rule (our words)
Moskowitz, Ooi & Pedersen (2012), "Time Series Momentum", Journal of Financial Economics 104(2), 228-250.
For every futures contract, at each month end go long if its excess return over the past 12 months is positive and
short if negative; hold for one month. Each position is sized to 40 % annualised ex-ante volatility
(sigma^2 = 261 x EWMA of squared daily excess returns, centre of mass 60 days), and the diversified TSMOM portfolio
is the equal-weighted average across all available contracts (weight 0.40/sigma_i/N_t).
* URL: https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf
* Factor data: https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Time-Series-Momentum-Factors-Monthly.xlsx
* Practitioner/live: https://www.aqr.com/Insights/Research/Journal-Article/Demystifying-Managed-Futures

## Source sample and reported numbers
* 58 liquid futures/forwards (24 commodities, 12 currency pairs, 9 equity indices, 13 bond futures), 1965 (main
  results 1985) - 2009. Diversified 12-month TSMOM: strongly significant, Sharpe above 1 gross.
* AQR TSMOM factor (gross, computed by the hunt from AQR's file): Sharpe 1.41 1985-2009; 0.39 post-publication
  2012-05..2026-05; 0.03 for 2016-01..2024-09; 0.97 for 2024-10..2026-05.
* Live: AQR Managed Futures (AQMIX) about 0.26 net since 2010; SG Trend Index 0.30 net 2000-2024 (0.41 2000-09,
  0.21 2010-19).
* Ours before: TSMOM_F 12-month on 20 futures 0.28 IS / 0.14 later (old cost map).
* Additional check computed here: the AQR TSMOM factor's Sharpe over our IS months and the monthly correlation of
  our V1 with it (fidelity of the universe adaptation).

## Our implementation (V1 = source rule)
Month-end decisions (last NYSE session of each month): for each eligible future s_i = sign(prod(1+r) - 1 over the
last 252 sessions); w_i = s_i x 0.40 / sigma_i / N, sigma_i = sqrt(252 x EWMA(r^2, com=60)) (min 60 obs);
book to 10 % (trailing 252-session covariance, min 60), gross <= 3; held to the next month end; next_close fills.

## Pre-declared variants (all reported)
* V1: as stated (12-month lookback, vol-scaled).
* V2: skip-month 12-1: s_i = sign of the cumulative excess return over sessions t-252 .. t-21 (excludes the last 21).
* V3: no vol scaling: w_i = s_i / N (equal notional), then book to 10 % (tests Kim, Tse & Wald 2016, "Time series
  momentum and volatility scaling", J. Financial Markets, who argue vol scaling drives TSMOM's performance).

## Adaptations and likely effects
* 30 CME futures (no non-US equity indices, no non-US bonds, 6 FX vs 12, 15 commodities) instead of 58: fewer
  independent bets -> lower diversified Sharpe than the paper; US-heavy rates/equity.
* Book scaled to 10 % ex-ante with a 252-day covariance (MOP's headline portfolio is not vol-targeted at the book
  level; AQR's factor is scaled ex post). Leaves Sharpe roughly unchanged, stabilises risk.
* Sample starts 2011-08 (data from 2010-06 + warm-up), entirely post-sample for MOP (ended 2009).
* sqrt(252) instead of sqrt(261) annualisation: a constant, no effect after book scaling.
