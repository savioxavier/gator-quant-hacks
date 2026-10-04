# trend_momentum_basis_momentum: basis-momentum (Boons & Porras Prado 2019)

Pre-registered 2026-10-03 before computing. Common conventions: ../COMMON_SPEC.md.

## Source rule (in our words)
Boons & Porras Prado (2019, Journal of Finance 74(1), 239-279, "Basis-momentum"): for each commodity at the end
of month t, basis-momentum BM = prod over the last 12 months of (1 + first-nearby futures return) minus prod of
(1 + second-nearby futures return) (their eq. 4). Sort commodities each month: High4 = the four with the
highest BM, Low4 = the four lowest; hold equal-weighted for month t+1; the strategy is High4 minus Low4 in
nearby (first-nearby) futures returns.

- URLs: https://ideas.repec.org/a/bla/jfinan/v74y2019i1p239-279.html ;
  https://4nations.albertjmenkveld.com/papers/boonsprado17.pdf (working-paper text checked locally, bp.txt)
- Source sample: 21 commodities, August 1960 - February 2014.
- Reported: High4-minus-Low4 average nearby return 18.38%/yr (t = 6.73) versus 15.02% (t = 4.61) for 12-month
  momentum and -10.61% for basis; spreading return 4.08% (t = 6.43); "Sharpe ratio of about 0.9"; robust pre-
  and post-1986. No post-2014 replication found by the hunt.

## Our implementation
- Universe: the same 15 CME commodities as above.
- Daily contract returns from databento_raw/glbx_ohlcv1d_v01.parquet, weekday bars only (as the F_ builder):
  for rank k in {0 (.v.0), 1 (.v.1)} on CME date t, r_k(t) = close(id_k(t), t) / close(id_k(t), t-1) - 1 where
  t-1 is the root's previous CME session in the file and close(id, t-1) is that same instrument_id's close on
  t-1 from either rank row. If the instrument_id is unchanged this is the plain return; on a roll day it is the
  newly held contract's own previous close when present; otherwise the return is 0.
- CME dates are mapped to the next NYSE session >= them and compounded within each NYSE session (exactly as
  the F_ index builder), giving r1, r2 on the NYSE calendar with the same timing as the F_ index.
- Month-end t: BM_i = prod(1 + r1) - prod(1 + r2) over the last 252 NYSE sessions.
- V1: long the 4 highest BM, short the 4 lowest (require >= 8 eligible), equal notional (+1/4, -1/4).
  V2: same names, risk units (1/sigma_i, equal risk per position).
  V3: time series: every eligible commodity w_i = sign(BM_i) * 0.40/sigma_i/N.
  All: positions in the F_ front index, book to 10% (gross cap 3), hold to next month-end, next_close.
- Headline: best in-sample net Sharpe of V1-V3.
- Diagnostic only (not a variant): share of days on which .v.1 has an earlier expiry than .v.0 (from the edge
  study's contracts.parquet symbol map), to size the volume-rank approximation.

## Adaptations and likely effect
- .v.0/.v.1 are Databento volume ranks, not expiry ranks. .v.1 is usually the next expiry but around volume
  rolls it can be the expiring (nearer) contract, and for some markets (e.g. NG, LE, HE, grains) it can be a
  deferred contract that is not the second nearby. This blurs the slope/curvature content of BM -> likely
  weaker than the source.
- 15 commodities instead of 21, 2011-2024 sample (post-publication of the 2017 working paper only from about
  2017): High4/Low4 with 15 names covers more of the cross-section (8 of 15 vs 8 of 21) -> weaker spread.
- Roll-day returns approximated (0 when the new contract's previous close is missing).

## Addendum (written after the pre-registered run, before running the check below)
The pre-registered run's diagnostics show the .v.1 leg is a poor second-nearby proxy: .v.1 changes contract
12-36 times a year per market, on 57-80% of those changes the new contract has no previous close in the file
(r2 set to 0 by the rule, about 2.5-10% of all days), and on 5-37% of days .v.1 expires BEFORE .v.0. Setting r2 = 0
on those days leaks plain front-month momentum into BM. One post-hoc data-construction check (not a variant,
never eligible as the headline, counted as an extra trial):
- r2_fix: on CME date t, r2 = the .v.1 contract's own return only when its expiry (edge study contracts.parquet
  month index) is later than the .v.0 contract's and its previous close exists; otherwise r2 = r1 (the day adds
  nothing to BM). Run only with the source's own construction (V1: High4-Low4 equal notional), everything else
  identical. Also report the average cross-sectional rank correlation of each BM version with plain 12-month
  momentum.
