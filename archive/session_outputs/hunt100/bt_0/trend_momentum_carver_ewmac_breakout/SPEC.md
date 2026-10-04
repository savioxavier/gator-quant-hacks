# trend_momentum_carver_ewmac_breakout - Carver multi-speed EWMAC + breakout trend forecasts (30 CME futures)

Pre-registered 2026-10-03 before computing any return of this strategy. Common conventions: ../COMMON_SPEC.md.

## Source rule (our words)
Robert Carver's continuous-forecast trend system (Systematic Trading, 2015; Advanced Futures Trading Strategies,
2023; open-source pysystemtrade). Code checked on 2026-10-03 (copies in ../src_cache/):
* ewmac(price, vol, Lfast, Lslow) = (EMA_span=Lfast(price) - EMA_span=Lslow(price)) / vol, EMAs with min_periods 1,
  vol = robust daily price-unit volatility of the back-adjusted price: EWMA std (span 35, min 10) of daily price
  differences, floored at the rolling 500-day 5 % quantile of itself (min 100 obs) (sysquant/estimators/vol.py).
* breakout(price, N) = EWMA_span=floor(N/4) [ 40 x (price - (max_N + min_N)/2) / (max_N - min_N) ], rolling
  max/min with min_periods ceil(N/2), smoothing min_periods ceil(span/2) (systems/provided/rules/breakout.py).
* Forecast scalars (pysystemtrade chapter-15 config / Carver's published values): EWMAC 8/32 5.3, 16/64 3.75,
  32/128 2.65, 64/256 1.87; breakout 20 0.67, 40 0.70, 80 0.73, 160 0.74, 320 0.74. Each scaled forecast capped at
  +/-20; combined forecast = weighted average x forecast diversification multiplier (FDM), capped at +/-20.
* Position at forecast 10 = the instrument's average risk position; buffering: no trade while the current position
  is within +/-10 % of the average position around the target; otherwise trade to the edge of the band.
* URLs: https://raw.githubusercontent.com/robcarver17/pysystemtrade/master/systems/provided/futures_chapter15/futuresconfig.yaml ;
  https://github.com/robcarver17/pysystemtrade ; https://qoppac.blogspot.com/2025/04/annual-performance-update-returneth.html

## Source sample and reported numbers
* Carver's live futures account (blog, net of all costs, GBP, UK tax years April-April): 2014/15 59.5 %, 15/16 28.1,
  16/17 2.4, 17/18 2.0, 18/19 4.5, 19/20 33.8, 20/21 -1.7, 21/22 25.8, 22/23 -7.6, 23/24 20.6, 24/25 -14.7;
  mean 12.9 %, sd 16.8 %, Sharpe 0.76 (rf = 0), CAGR 12.0 % vs SG CTA index 6.4 %. The live system also holds carry
  and relative-value rules over 100+ instruments; Carver reported that univariate trend rules lost in 2024/25.
* Ours before: a 6-speed long-short EWMAC diagnostic about 0 IS / -0.35 later (different speeds, vol and sizing).
* Additional check computed here: our per-UK-tax-year returns next to his and their correlation (11 points).

## Our implementation
* Price p = cumulative excess-return index of the F_ series (see adaptations). Daily price-unit vol v = robust vol
  of p.diff() exactly as pysystemtrade; instrument % vol sigma_i = sqrt(252) x v / p.
* Forecasts as above, each x scalar, capped +/-20. Combined = equal-weight average over the variant's rules that
  have a value (weights renormalised over available forecasts, as pysystemtrade does) x FDM, capped +/-20.
* FDM (trailing, point-in-time): at each month end, pooled Pearson correlation of the capped scaled forecasts of
  all instruments sampled at the last session of each week over all weeks up to that month end (expanding, >= 52
  weeks), negative correlations floored at 0, FDM = 1/sqrt(w'Rw) capped at 2.5; used from the next session and
  smoothed with an EWMA of span 125 sessions (pysystemtrade's default FDM smoothing).
* Target w_i = (F_i/10) x 0.10 / sigma_i / N_t (N_t eligible instruments), daily decisions; book to 10 % ex-ante
  (trailing 252-session covariance, min 60) with gross <= 3; buffer: average position A_i = k_t x 0.10/sigma_i/N_t
  (k_t = that day's book scale), band = 0.10 x A_i; if the previous position is outside [target - band,
  target + band] it moves to the nearest edge, otherwise unchanged; ineligible -> 0. next_close fills.

## Pre-declared variants (all reported)
* V1: EWMAC only (8/32, 16/64, 32/128, 64/256), equal weights.
* V2: breakout only (20, 40, 80, 160, 320), equal weights.
* V3: all nine rules, equal weights.

## Adaptations and likely effects
* Price is the excess-return index, not the total-return index named in the candidate: futures prices contain no
  T-bill accrual, and at 5 % T-bill rates the TR index adds a drift worth up to ~20 forecast points on ZT/ZF (daily
  vol ~0.1 %), which would force spurious long short-rate positions. Using excess returns is closer to Carver.
* Ratio (multiplicative) back-adjustment instead of Carver's additive Panama adjustment: EWMAC/breakout are
  scale-free in the price, so the effect is negligible.
* 30 US-listed instruments vs Carver's 100+: fewer bets, lower Sharpe than his account.
* Book scaled to 10 % ex-ante every day instead of Carver's fixed instrument diversification multiplier: removes
  the risk variation that comes from forecast strength (Carver's risk rises with conviction). Likely a small Sharpe
  cost; risk is steadier.
* Buffering on weights (fraction of NAV) rather than whole contracts; no contract rounding (small-account effects
  absent).
* Forecast scalars taken from Carver's published defaults, not re-estimated.
