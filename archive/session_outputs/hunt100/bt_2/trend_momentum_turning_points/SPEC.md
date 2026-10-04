# trend_momentum_turning_points: pre-registration (written 2026-10-03, before any computation of this strategy)

## Source rule (in my words)
Sources: Garg, Goulding, Harvey, Mazzoleni, "Momentum Turning Points" (AEA 2021 preliminary paper,
https://benny.aeaweb.org/conference/2021/preliminary/paper/492Ds6fk; published JFE 2023); Goulding, Harvey,
Mazzoleni, "Breaking Bad Trends" (FAJ 2024, https://people.duke.edu/~charvey/Research/Published_Papers/P167_Breaking_bad_trends.pdf,
read in full: Appendix C eq. 8-10, Table E.1); CXO summary
https://www.cxoadvisory.com/technical-trading/mitigating-impact-of-price-turning-points-on-trend-following/.

* Each month and each asset: SLOW = +1 if the trailing 12-month return is >= 0 else -1; FAST = +1 if the trailing
  k_f-month return is >= 0 else -1 (Garg et al.: k_f = 1; GHM main analysis: k_f = 2, Appendix D shows k_f = 1).
* State: Bull (SLOW=+1, FAST=+1), Correction (+1, -1), Bear (-1, -1), Rebound (-1, +1).
* Position for the next month: w = (1 - a) SLOW + a FAST. Static MED: a = 1/2 (position +1 Bull, -1 Bear, 0 after
  Correction or Rebound). Dynamic (DYN): a depends on the state; only a_Co and a_Re matter:
  a_Co = 1/2 (1 - (1/C) AVG(r|Co) / AVG(r^2|Co)),  a_Re = 1/2 (1 + (1/C) AVG(r|Re) / AVG(r^2|Re)),
  C = FREQ(Bu)/FREQ(Bu or Be) * AVG(r|Bu)/AVG(r^2|Bu or Be) - FREQ(Be)/FREQ(Bu or Be) * AVG(r|Be)/AVG(r^2|Bu or Be),
  where r is the return in the month after a month in the given state, using only months before the decision;
  estimates outside [0, 1] are set to the nearest endpoint. (The hunt card wrote AVG(r^2|Bu) and AVG(r^2|Be) in C;
  the paper uses the pooled second moment AVG(r^2|Bu or Be), identical to Garg et al. Proposition 5. I follow the paper.)
  GHM: per asset, re-estimated every 30 months from inception-to-prior-month data, >= 12 months in each phase required
  (else the asset is excluded); data before 1990 warm the estimates up.
* GHM portfolio: 43 Barchart futures (equity 11, bonds 8, commodities 24 in Appendix A), one unit long/short per asset,
  equal weight within asset class and across classes, returns scaled ex post to 10% vol, gross of all costs.

## Source sample and reported numbers
* Garg et al. (US equity market, Mkt-RF, 1969-2018 evaluation, gross): MED Sharpe about 0.51 vs SLOW about 0.38
  (hunt card); DYN out-of-sample Sharpe 0.52-0.69 over the evaluation windows of Table 6 (efficiency 0.92-0.99 of
  the ex-post optimum).
* GHM Table E.1 (multi-asset, unscaled, gross): 1990-2022 static 12m Sharpe 0.64, Avg 1/3/12 0.59, DYN 0.80;
  1990-2008: 1.07 / 0.90 / 1.20; post-GFC 2009-2022: 0.06 / 0.13 / 0.22; 2009-2019: 0.03 / 0.05 / 0.34.
  Text: static 12m 6.4%/yr at 10% vol full period vs 0.3%/yr 2009-19; dynamic edge survives average costs below 29 bp.

## Our implementation (futures, gqh engine)
* Universe: the 30 CME futures (F_ES ... F_6S); data from 2010-06-07 (RTY from 2017-07-10).
* Month-end decisions (last NYSE session), filled next_close. Monthly excess returns are compounded daily excess
  returns of the F_ index between consecutive month-ends. SLOW uses the last 12 monthly returns, FAST the last k_f.
* Eligibility (hunt convention): >= 260 sessions of history, positive EWMA vol, traded in the last 10 sessions,
  plus 12 complete monthly returns.
* Sizing: w_i = x_i * 0.40 / sigma_i / N_eligible (sigma = sqrt(252 EWMA(r^2, com 60))), book rescaled to 10%
  ex-ante vol with the trailing 252-session covariance (min 60), gross <= 3.
* Costs: realistic one-way map of the hunt task (ES/NQ/YM 1, RTY 2, ZT 0.5, ZF 0.7, ZN 1, ZB/UB 1.5, FX 1,
  CL/GC/SI/HG 2, NG/HO/RB/PL 3, grains/livestock 4 bp), roll days add a round trip; 2x stress reported.

## Pre-declared variants (all reported)
* V1: static MED, a = 0.5, k_f = 1 month.
* V2: static MED, a = 0.5, k_f = 2 months.
* V3: dynamic a_Co, a_Re with k_f = 2, estimated pooled across all eligible futures. Pooled observation = (state of
  future i at month-end m, r_{i,m+1} / sigma_{i,m}); returns are divided by the instrument's EWMA vol at the state
  date so that high-vol commodities do not dominate the moments (our positions are vol-scaled, so the vol-normalised
  return is the return being timed). Re-estimated at every month-end with an expanding window that contains only
  next-month returns completed by that month-end. a = 0.5 (identical to V2) until the pooled sample spans at least
  48 distinct state months and each of Bu, Be, Co, Re has >= 12 observations; if C <= 0 (the formula then gives a
  minimiser) a_Co = a_Re = 0.5. Clip to [0, 1].
* Non-selectable diagnostic: SLOW alone (12-month sign, same sizing) to check the source's relative claim
  (dynamic/MED vs static 12m). Not a variant, never selected.
* Selection for the standard series: the variant with the highest in-sample net Sharpe (1x costs).

## Windows
In-sample: first live session (decisions from 2011-06-30) through 2024-10-02. 2024-10-03..2026-10-02 descriptive only.

## Adaptations and likely effects
* 30 CME futures from 2010 instead of 43 global futures from 1990 (and the US market since 1926): no pre-sample
  warm-up, so V3 is V2 until about mid-2015 and its estimates are noisier; equity class is 4 correlated US indices.
* Vol-scaled risk units and a 10% ex-ante book instead of unit positions with equal class weights and ex-post
  scaling: changes the asset weighting (bonds get more notional); should raise the Sharpe of all variants similarly.
* Monthly expanding re-estimation instead of every 30 months; pooled instead of per-asset parameters.
* Costs included (the sources are gross).
