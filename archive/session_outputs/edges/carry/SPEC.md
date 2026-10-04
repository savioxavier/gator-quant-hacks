# Futures carry: pre-declared specification

Written 2026-10-03 before any strategy return was computed. Only data plumbing (the instrument-id to contract
mapping and a count of how often the front and second contracts both print) was looked at before this file.

## Literature

* Koijen, Moskowitz, Pedersen & Vrugt (2018), "Carry", Journal of Financial Economics 127(2), 197-225
  (NBER WP 19325, July 2013). Carry = the return of a futures position if prices stay unchanged:
  C = (S - F) / F, with S the nearer and F the held contract, interpolated to a one-month horizon. Rank-weighted
  long/short within each asset class (their Eq. 19: w_i = z (rank(C_i) - (N+1)/2), z so that longs sum to +1 and
  shorts to -1), monthly rebalance. Two signals: current carry ("carry1m") and the 12-month moving average
  ("carry1-12"), which removes the seasonal component of commodity and equity carry.
  Sample: November 1983 (equities/bonds/FX/commodities from various starts, commodities 1980s) to September 2012.
  Their Sharpe ratios (carry1m / carry1-12, gross, ex-post volatility scaling): global equities 0.91 / 0.58,
  10-year bonds 0.52 / 0.46, US Treasuries across maturities 0.68 / 0.78, commodities 0.60 / 0.65,
  currencies 0.68 / 0.55; all-asset global carry factor 1.20 / 1.12.
* Asness, Moskowitz & Pedersen (2013), "Value and Momentum Everywhere", JF: the same rank weighting.
* Post-sample evidence already collected (research/high_sharpe_literature.md): AQR's four-asset futures carry is
  about 0.07 gross Jan 2012 - Feb 2026; the live G10 carry ETF (DBV) had a negative excess return 2006-2020.
  Prior expectation: the global carry composite is close to zero after 2012; commodity carry is the most likely
  survivor; US-only equity "carry" is a dividend-yield (value vs growth) tilt, not the paper's country strategy.

## Data

* Returns: futures_daily.parquet, F_<root> fully collateralised total-return index of the volume-ranked front
  contract (.v.0); daily excess return = index return minus the T-bill return (load_rf).
* Carry: raw Databento GLBX.MDP3 ohlcv-1d closes of the volume-ranked .v.0 and .v.1 contracts, with each
  instrument_id mapped to its raw CME symbol and delivery month by the free symbology endpoint (date-aware, since
  CME recycles ids). Script: build_contracts.py -> contracts.parquet.

## Carry signal

1. Daily observation for root i on raw CME date tau, only when both ranks printed that day with positive closes,
   different delivery months and a gap of at most 12 months: near = earlier delivery, far = later delivery,
   dt = (month_far - month_near)/12 years, c = (P_near / P_far)^(1/dt) - 1.
   Sign: positive = backwardation = a long earns roll yield. FX (USD per foreign unit): c = r_foreign - r_USD.
   Equity indices: c = dividend yield - r. Treasury futures: c = coupon/roll-down minus repo of the CTD
   (also contains delivery-option and CTD-switch effects; noted as a data caveat).
2. Raw dates are mapped to the next NYSE session on or after them (as in the return builder); the last
   observation per NYSE session is kept.
3. Two pre-declared smoothings (both computed only from observations up to the decision close):
   * C1 ("carry1m" analog): mean of valid observations over the last 21 NYSE sessions, at least 10 valid.
   * C12 ("carry1-12" analog): mean of valid observations over the last 252 NYSE sessions, at least 126 valid.
     This is the paper's own seasonality fix and is the relevant one for LE, HE, NG, RB, HO and grains.

## Universe and classes

* FX (6): 6E 6J 6B 6A 6C 6S
* Rates (5): ZT ZF ZN ZB UB (one curve: the paper's "US Treasuries across maturities" class)
* Commodities (15): CL HO RB NG GC SI PL HG ZC ZS ZW ZL ZM LE HE
* Equity indices (4): ES NQ YM RTY (all US; RTY data starts 2017)

Eligibility at a decision date (same as forward test 2's S1): >= 300 sessions of index history, a positive
EWMA volatility, at least one traded session in the last 10, plus a valid signal.

## Portfolio construction (no parameter fitted on returns)

* Instrument volatility sigma_i: EWMA of squared daily excess returns, centre of mass 60 days, annualised (S1).
* (a) Cross-sectional (XS), per class with N >= 3 eligible: KMPV rank weights on the carry signal (ties get the
  average rank), each rank unit vol-normalised: position_i = w_i x 0.10 / sigma_i.
* (b) Time-series (TS), per class with N >= 1 eligible: position_i = sign(C_i) x 0.10 / sigma_i / N.
* Class book scaling: each class book is rescaled to 10 % annualised ex-ante volatility with the trailing 252-day
  sample covariance of daily instrument excess returns (min 60 observations); the scale factor is capped at 4.
* (c) Global: equal risk per class = (1/K) x sum of the K available class books (each at 10 %), rescaled to
  10 % ex-ante volatility with the same covariance estimator, scale factor capped at 4. Done separately for XS
  and TS. No notional cap (the gross notional is reported; ZT's low volatility implies large notional).
* Rebalance: monthly (last NYSE session of the month) and a weekly variant (last NYSE session of the week).
  Next-close fills: decision at the close of d, traded at the close of d+1 (engine.simulate exec="next_close").
  Between decisions the engine trades back to the target weights daily (drift costs included).

## Costs

Realistic one-way bps per unit of turnover (midpoints of the stated ranges; RTY, not listed, at 1.0):
ES 0.5, NQ 0.75, YM 0.75, RTY 1.0; ZT 0.3, ZF 0.5, ZN 1.0, ZB 1.25, UB 1.5; 6E 0.5, 6J 0.75, 6B 0.75, 6A 0.75,
6C 0.75, 6S 1.0; CL 1.5, GC 1.5, SI 1.5, HG 1.5; NG 2.5, HO 2.5, RB 2.5, PL 2.5; ZC ZS ZW ZL ZM 4.0; LE HE 4.0.
Roll days charge one extra round trip of the position held (engine). Stress: 2x the map. Gross also reported.

## Variants (all reported)

signal {C1, C12} x rebalance {monthly, weekly} x construction {XS, TS} = 8 global books, plus the 4 class books
of each (32 class-level series) = 40 series. Selection rule: for each construction, the global variant with the
highest in-sample net Sharpe at realistic costs is the headline candidate; the median of its four variants is
also reported. Class-level series are written for the headline variant only (no per-class selection).

## Windows

* In-sample: first decision with positions (about 2011-09, set by the 300-session warm-up from 2010-06) through
  2024-10-02. Pre/post publication split inside it at 2013-07-31 (NBER WP), noting the paper's sample ended
  2012-09, so nearly all of our window is post-sample.
* Later window 2024-10-03 .. 2026-10-02: descriptive only, never used for any choice.

## Reported statistics

Net Sharpe (excess over T-bill) at 1x and 2x costs, gross Sharpe, annualised mean excess and CAGR of excess,
volatility, max drawdown of the excess-return equity curve, worst calendar year, % positive calendar years,
rolling 504-session Sharpe 10th/50th/90th percentiles, turnover per year, mean gross notional, correlations with
ES excess, S1 trend (forward2) and F2 (forward), Newey-West t of the mean excess, circular block bootstrap
(63-day blocks) Sharpe interval and paired difference vs S1, deflated Sharpe over the 8 global variants.

## Verdict rule (fixed now)

* real_edge: in-sample net Sharpe at 1x with NW t >= 2.0, still positive at 2x, >= 60 % positive years, and the
  rolling 2-year Sharpe 10th percentile above -0.5.
* weak_or_uncertain: positive in-sample net Sharpe at 1x but failing one of the above.
* fails: in-sample net Sharpe at 1x <= 0.
