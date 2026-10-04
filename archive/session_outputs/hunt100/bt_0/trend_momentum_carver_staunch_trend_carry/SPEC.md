# trend_momentum_carver_staunch_trend_carry - Carver "staunch systems trader" EWMAC + carry system (30 CME futures)

Pre-registered 2026-10-03 before computing any return of this strategy. Common conventions: ../COMMON_SPEC.md;
forecast machinery (price, robust vol, EWMAC, caps, FDM estimator, sizing, book scaling, buffer) identical to
../trend_momentum_carver_ewmac_breakout/SPEC.md.

## Source rule (our words)
pysystemtrade's chapter-15 example system (Carver, Systematic Trading, the "staunch systems trader" chapter):
* Rules: ewmac16_64 (forecast scalar 3.75), ewmac32_128 (2.65), ewmac64_256 (1.87), carry (smooth_days 90,
  scalar 30); forecast_cap 20.
* carry rule = raw_carry.ewm(smooth_days).mean(); raw_carry = annualised roll / (daily price vol x sqrt(256-ish
  business days)), annualised roll = (price - carry_price) / (carry_contract_date - price_contract_date in years),
  i.e. positive when the nearer contract is above the further one (backwardation).
  NOTE: pandas' first positional argument of ewm is the centre of mass, so the code smooths with com = 90
  (equivalent span 181); we follow the code.
* forecast_weights: ewmac16_64 0.21, ewmac32_128 0.08, ewmac64_256 0.21, carry 0.50;
  forecast_div_multiplier 1.31; percentage_vol_target 20 (we use 10 %; scale-free for Sharpe).
* URLs: https://raw.githubusercontent.com/robcarver17/pysystemtrade/master/systems/provided/futures_chapter15/futuresconfig.yaml ;
  https://github.com/robcarver17/pysystemtrade ; https://qoppac.blogspot.com/2025/04/annual-performance-update-returneth.html
  (code copies in ../src_cache/).

## Source sample and reported numbers
* Same live record as the EWMAC candidate (net, 2014/15-2024/25, Sharpe 0.76 at rf = 0, CAGR 12.0 %); the config is
  Carver's published example (6 instruments), not his live system.
* Our edge study's separate carry sleeves (edges/series/carry_ts_global: KMPV sign carry) gave no real edge.

## Our implementation
* Carry: from the raw Databento GLBX daily closes of the volume-ranked .v.0 and .v.1 contracts with delivery months
  from the free symbology mapping (reusing the verified edge-study table edges/carry/contracts.parquet). For each raw
  date with both closes > 0, different delivery months and a gap <= 12 months: dt = month gap / 12,
  ann_roll = (P_near - P_far) / P_v0 / dt (fraction of the held .v.0 contract price per year); raw dates mapped to
  the next NYSE session on/after them (last observation per session), then lagged one extra session (the UTC-day bar
  closes after the NYSE close). raw_carry = ann_roll / sigma_i (sigma_i = annualised robust % vol of the held series).
  Smoothed carry = ewm(com=90) of raw_carry, valid only if a raw observation exists in the last 21 sessions;
  forecast = 30 x smoothed, capped +/-20.
* Combined forecast = weighted average of the available forecasts (weights renormalised over those present that day)
  x FDM, capped +/-20. Sizing w_i = (F_i/10) x 0.10/sigma_i/N_t, book to 10 % (trailing 252-session covariance,
  gross <= 3), daily decisions, 10 % buffer to the band edge, next_close fills.

## Pre-declared variants (all reported)
* V1: as configured (weights 0.21 / 0.08 / 0.21 / 0.50, fixed FDM 1.31).
* V2: equal weights 0.25 on the four rules, FDM estimated with the trailing pooled estimator of the EWMAC candidate
  ("refit in-sample" implemented point-in-time).
* V3: trend-only sub-portfolio of V1: EWMAC weights renormalised (0.42 / 0.16 / 0.42), FDM estimated with the same
  trailing estimator; V1 minus V3 measures the carry contribution.

## Adaptations and likely effects
* Carry from the volume-ranked front/second pair rather than Carver's chosen price/carry contracts (he often holds a
  deferred contract and uses the adjacent one): carry measured nearer the front, noisier for seasonal commodities
  (the com-90 smoothing dampens this).
* Equity-index carry = dividend yield minus T-bill; FX carry = interest differential; Treasury carry includes CTD
  and delivery-option effects.
* All instruments get the same forecast weights (the config fits per instrument only through cost rules).
* Same caveats as the EWMAC candidate (excess-return price, daily book scaling instead of a fixed IDM, 30 instruments,
  weight-level buffering).
