# carry_value_comm_value_ma: commodity value from deviations to 1-5 year moving averages

Pre-registered 2026-10-03 before any return of this strategy was computed. Common rules: ../COMMON_SPEC.md.

## Sources and their numbers

* QIS_Commodities (GitHub, jjj1231978) value sleeve, https://github.com/jjj1231978/QIS_Commodities : 17 CME roots,
  signal from the deviation of price to its 1-5 year moving averages, 6 long / 6 short, 2015-06..2026-05, net:
  Sharpe 0.64, 6.7 %/yr, max DD -23.1 %.
* Asness, Moskowitz & Pedersen (2013), "Value and Momentum Everywhere", JF 68(3); AQR VME factor data
  https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Value-and-Momentum-Everywhere-Factors-Monthly.xlsx :
  commodity value = log of the average spot price 4.5-5.5 years ago over today's price. Verifier calculation on AQR
  data: Sharpe 0.27 pre-publication (1972-2013-06), 0.57 post-publication (2013-07..2025-01).
* Sakkas & Tessaromatis (JBF 2020, 1970-2018): commodity value long-short Sharpe 0.14.
* Edge-study verifier diagnostic (not a declared series): commodity-only AMP value sleeve 0.45 in-sample (t 1.28) /
  -0.63 later.

## Rule in our words

P = unadjusted close of the STD near contract on NYSE sessions (last valid near close within 5 sessions at the
decision). At each month-end t, for w in {1,2,3,4,5} years: dev_w = P_t / mean(P over the last 252w NYSE sessions)
- 1, computed only if at least 126w valid prices are in the window. Signal = minus the average of the available
dev_w (cheap = high). Positions in F_<root> (futures_daily P&L), monthly, next-close fills, commodity cost map.

* V1 (primary): long the 4 highest-signal and short the 4 lowest-signal eligible COM15 roots, each +-0.10/sigma_i;
  book rescaled to 10 % ex-ante (252-session covariance, min 60, cap 4). If fewer than 8 are eligible,
  min(4, floor(N/2)) per side.
* V2: AMP signal log(mean of month-end P over month-ends t-66..t-54) - log(P_t), requiring at least 7 of the 13
  month-end prices; same 4/4 legs. (Starts about 2015-2016 because of the 5.5-year lookback.)
* V3: V1 signal with KMPV rank weights across all eligible roots (N >= 3), position = w x 0.10/sigma_i, book as V1.

## Adaptations and expected effects

* Near-contract unadjusted price as the spot proxy (as AMP); contract switches add small jumps (contango/
  backwardation steps) into the level series, a mild carry tilt.
* 15 roots, 4/4 legs (source 17 roots, 6/6); equal risk per name.
* Our data starts 2010-06, so the 4- and 5-year averages appear only from 2014-2015 (the signal averages whatever
  windows have half their data); V2 cannot start before about mid-2015.
