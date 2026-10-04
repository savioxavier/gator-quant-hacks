# trend_momentum_bond_tsmom: pre-registration (written 2026-10-03, before any computation of this strategy)

## Source rule (in my words)
Sources: Moskowitz, Ooi, Pedersen (2012), "Time Series Momentum", JFE (https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf);
AQR "Time Series Momentum: Factors, Monthly" dataset, fixed-income factor TSMOM^FI
(https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Time-Series-Momentum-Factors-Monthly.xlsx);
Durham, NY Fed Staff Report 657 (https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr657.pdf).
* MOP: each month, for each bond future, position = sign(past 12-month excess return) x 40% / ex-ante vol
  (ex-ante vol = annualised EWMA of squared daily returns, centre of mass 60 days); the asset-class factor is the
  equal-weighted average over the class's instruments; held one month. TSMOM^FI = the bond-futures average
  (13 global government bond futures in MOP's sample).
* Carver EWMAC (pysystemtrade chapter-15 config): raw = (EMA_fast(p) - EMA_slow(p)) / price-vol, forecast scalars
  3.75 (16/64) and 1.87 (64/256), each forecast capped at +/-20.

## Source sample and reported numbers
* AQR TSMOM^FI factor (gross; Sharpe computed by the hunt from the AQR file): 0.71 for 1985-2009, 0.33 post-
  publication 2012-05..2026-05, 0.35 for 2016-01..2024-09 (best asset class after publication), -0.54 for
  2024-10..2026-05. bt_2 also recomputes the factor on our exact in-sample and later windows (aqr_same_window.py).
* Durham SR 657: price momentum along the Treasury curve 1997-2013, information ratio up to 0.79.

## Our implementation (futures, gqh engine)
* Universe: F_ZT, F_ZF, F_ZN, F_ZB, F_UB (data from 2010-06-07).
* Month-end decisions (last NYSE session), filled next_close, held to the next month-end.
* Signal s_i:
  * V1: s = sign(cumulative excess return over the last 252 sessions).
  * V2: s = mean of sign(R_21), sign(R_63), sign(R_252) (cumulative excess returns).
  * V3: Carver forecast: p = excess-return index (cumulative product of 1 + daily excess return, i.e. a
    back-adjusted price without T-bill drift); price-vol = EWMA std (span 35) of daily changes of p;
    f1 = clip(3.75 (EMA16(p) - EMA64(p)) / price-vol, -20, 20), f2 = clip(1.87 (EMA64(p) - EMA256(p)) / price-vol,
    -20, 20); s = (f1 + f2) / 2 / 10 (equal weights, no diversification multiplier, as the card states).
* w_i = s_i * 0.40 / sigma_i / N_eligible, sigma_i = sqrt(252 EWMA(r^2, com 60)); book rescaled to 10% ex-ante vol
  with the trailing 252-session 5x5 covariance (min 60), gross <= 3.
* Eligibility: >= 260 sessions of history, positive EWMA vol, traded in the last 10 sessions.
* Costs: ZT 0.5, ZF 0.7, ZN 1, ZB 1.5, UB 1.5 bp one-way per unit notional, roll days add a round trip; 2x stress.
* Selection for the standard series: highest in-sample net Sharpe (1x costs) among V1-V3.

## Windows
In-sample: first live session (decisions from 2011-06-30) through 2024-10-02. 2024-10-03..2026-10-02 descriptive only.

## Adaptations and likely effects
* US curve only (5 highly correlated maturities, pairwise correlation 0.6-0.95) instead of 13 global bond futures:
  effectively one duration-timing bet, so expect a higher volatility of Sharpe and lower diversification than
  TSMOM^FI. The 0.40/sigma risk units plus the gross cap of 3 concentrate notional in ZT when its vol is very low
  (2011-2015, 2020-2021); the cap binds then.
* Our in-sample window (2011-2024) contains the 2022 rate shock (a large trend gain) and the 2011-2020 rally.
