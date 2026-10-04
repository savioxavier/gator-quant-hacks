# value_reversal: pre-registered specification

Written before any backtest of these rules was run (2026-10-03). Every variant listed here is computed and
reported; nothing is added or dropped after seeing results. The primary variant of each candidate is fixed
here; the other variants are sensitivity rows, and their median is reported next to the primary.

## Literature and sample

* Asness, Moskowitz and Pedersen (2013), "Value and Momentum Everywhere", Journal of Finance 68(3)
  (manuscript dated June 2012 in hand: scratchpad `vme.txt`). Samples: country equity indices 1978-2011,
  10 currencies 1979-2011, 10 government bonds 1982-2011, 27 commodities 1972-2011.
  - Commodities: value = log of the spot price five years ago divided by the most recent spot price, "essentially
    the negative of the spot return over the last five years" (manuscript lines 349-351). The published JF
    version, as we recall it, averages the spot price from 4.5 to 5.5 years ago (not verifiable from the files in
    hand, so it is labelled "as recalled").
  - Currencies: value = negative of the five-year return on the exchange rate including the interest earned
    (manuscript lines 351-355). (The published version uses a CPI-adjusted 5-year change; we have no CPI data
    in the cache.)
  - Bonds: negative of the past five-year return (manuscript) / five-year change in 10-year yields (published);
    alternative measures in Table 1 Panel C: real yield and the term spread (10-year yield minus short rate).
  - Equity indices: BE/ME (unavailable to us). The Internet Appendix repeats the analysis with value measured
    as the past five-year (60-month) return for every asset class; we use that measure.
  - Momentum: past 12-month cumulative return skipping the most recent month (MOM2-12).
  - Portfolios: weights proportional to the cross-sectional rank minus the average rank (eq. 1);
    COMBO = 0.5 VALUE + 0.5 MOMENTUM (eq. 3).
* Publication timing: SSRN working paper 2009; JF June 2013. Our cross-sectional in-sample (2016-2024) is
  entirely post-publication, so a pre/post split is impossible there; it is possible only for the long-history
  bond check on IEF (2005-2024), split at 2013-06-30.
* Independent evidence used for context only (not a test of our rules): the AQR VME factor file
  (`vme_factors.xlsx`), whose non-stock asset-class value factor had a Sharpe of about 0.2 after publication.

## Data

* Futures: `futures_daily.parquet`, 30 CME roots, fully collateralised total-return index (within-contract excess
  return + T-bill), NYSE calendar, 2010-06-07 .. 2026-10-02. Excess return = index return - T-bill (rf_daily).
* Commodity "spot" level: close of the most liquid contract (Databento volume rank 0, `<ROOT>.v.0`), unadjusted,
  from `databento_raw/glbx_ohlcv1d_v01.parquet`, mapped to the NYSE calendar (last close on or before the date,
  at most 5 sessions stale). This is AMP's "spot" (nearest / most liquid futures price).
* FX and equity "level": the cumulative excess-return index of the futures (AMP: currency return including
  interest; equity: past five-year return).
* Bond yields: FRED DGS10, DGS2 (H.15). FRED posts day d's value on the next business day, so the signal at the
  close of d uses yields up to d-1 (1-session lag).
* IEF (ETF, adjusted close, 2005-) for the long-history bond check only.
* No new data are downloaded. FRED exchange rates, CPI or long commodity spot series are not in the local cache,
  so the cross-sectional value signals cannot be extended before the futures history (stated as a limitation).

## Universe and classes

* COM (15): CL HO RB NG GC SI PL HG ZC ZS ZW ZL ZM LE HE
* FX (6): 6E 6J 6B 6A 6C 6S (all against USD)
* EQ (4): ES NQ YM RTY (RTY data start 2017-07, so it enters the value book only in 2023). Four US indices are a
  very poor substitute for AMP's 18 countries; the class is kept because the task asks for it.
* BOND: ZN (time-series only).

## Signals (decision at the close of the last NYSE session of each month, t; levels P are month-end levels)

(a) Cross-sectional value (5-year reversal), three windows:
* VW1 (primary; published definition as recalled): log(mean(P[t-66m] .. P[t-54m])) - log(P[t]) (13 month-end levels).
* VW2 (manuscript text): log(P[t-60m]) - log(P[t]).
* VW3 (task suggestion: from 5.5 years ago to 6 months ago, skipping the momentum period):
  log(P[t-66m]) - log(P[t-6m]).
A market enters when every level the window needs exists. First possible VW1 decision: 2015-12-31.

(b) Time-series bond value on ZN (sign rule, so the position is always at the 10 % ex-ante target):
* B1 (primary): sign(DGS10 - mean of DGS10 over the trailing 1,260 sessions); long ZN when the 10-year yield is
  above its 5-year average (bonds cheap).
* B2: same with the term spread DGS10 - DGS2 (AMP's alternative bond value measure).
* B1_IEF: B1 applied to IEF (2005-2026), the long-history check (ETF; pre/post publication split possible).

(c) Value + momentum (AMP COMBO), primary window VW1 and B1 only:
* MOM2-12 = log(XR[t-1m]) - log(XR[t-12m]) on the excess-return index of every market (the tradeable return).
* MOM_XS: cross-sectional rank-weighted momentum in COM, FX, EQ (the combo ingredient, reported for reference).
* COMBO_XS: within each of COM, FX, EQ: 0.5 x value sleeve + 0.5 x momentum sleeve (each at 10 % ex-ante),
  rescaled to 10 %; classes then combined with equal weights and rescaled to 10 %.
* VAL_ALL: VAL_XS classes (VW1) plus the B1 bond sleeve as a fourth class, equal risk.
* COMBO_ALL: COMBO_XS classes plus a bond class = 0.5 B1 + 0.5 time-series momentum on ZN
  (sign of its MOM2-12), equal risk across the four classes.
Cross-sectional candidates (VAL_XS, MOM_XS, COMBO_XS, VAL_ALL, COMBO_ALL) are evaluated from the first VW1
decision, so all share one window. MOM_XS is also reported from its own start (2011) as a descriptive row.

## Construction (identical for every candidate)

* Instrument volatility: EWMA of squared daily excess returns, centre of mass 60 sessions, annualised (x252).
* Rank weights within a class: raw_i = (rank_i - mean rank) / sigma_i (ranks 1..N; rank-weighted in risk units).
  A class needs at least 3 eligible markets, otherwise it is flat.
* Eligibility (as forward test 2): signal history available, EWMA vol positive, traded (volume > 0) in at least
  one of the last 10 sessions.
* Scaling: each sleeve and the final book are scaled to 10 % annualised ex-ante volatility with the sample
  covariance of the trailing 252 daily excess returns of the instruments held (min 60 observations).
  Classes are combined with equal weights (equal ex-ante risk), then the sum is rescaled to 10 %.
  Final gross notional capped at 5x NAV.
* Execution: decision at month-end close d, filled at the close of d+1 (engine `next_close`); the engine
  trades back to target weights every session (drift costs included); a futures roll charges one extra round
  trip of the position held into the roll; cash earns the T-bill.

## Costs (one-way bp of notional per unit of turnover; "realistic" map, 2x = stress)

ES NQ YM 0.75; RTY 1.0; ZT 0.3; ZF 0.5; ZN 1.0; ZB UB 1.25; 6E 6J 6B 6A 6C 6S 0.75; CL GC SI HG 1.5;
NG HO RB PL 2.5; ZC ZS ZW ZL ZM LE HE 4.0; IEF 3.0 (repo tier-1 ETF cost). Gross = no costs.

## Windows

* In-sample: first live day .. 2024-10-02 (start stated per candidate).
* Later window (already seen, descriptive only): 2024-10-03 .. 2026-10-02.

## Reported for every candidate

Net Sharpe (excess of T-bill) at 1x and 2x costs, gross Sharpe, annual return, vol, max drawdown, worst year,
% positive calendar years, rolling 504-session Sharpe 10/50/90th percentiles, turnover per year, mean gross
leverage, daily and monthly correlations with ES (F_ES excess return), S1 (forward test 2 broad trend) and
F2 (forward test 1 futures ensemble), value-momentum correlation, Newey-West t of the mean daily excess return,
paired block bootstrap (63-session circular blocks, 5,000 draws) for COMBO_XS vs MOM_XS and for
0.5 S1 + 0.5 VAL_ALL vs S1 alone.

## Verdict rule (fixed now)

* real_edge: in-sample net Sharpe (1x) >= 0.5 and NW t >= 2.0 and net Sharpe (2x) >= 0.35 and later-window
  net Sharpe (1x) > 0.
* fails: in-sample net Sharpe (1x) < 0.2 or NW t < 1.0.
* weak_or_uncertain: everything else.
A candidate's diversification value (correlation with trend) is reported separately and does not change the
verdict.
