# carry_value_comm_curve_spread: commodity curve carry spread (long deferred, short front)

Pre-registered 2026-10-03 before any return of this strategy was computed. Common rules: ../COMMON_SPEC.md.

## Sources and their numbers

* Szymanowska, de Roon, Nijman & van den Goorbergh (2014), "An Anatomy of Commodity Futures Risk Premia", JF 69(1),
  https://ideas.repec.org/a/bla/jfinan/v69y2014i1p453-482.html . Term premia earned by spreading positions
  (long a deferred, short a nearer contract) of roughly 1-3 %/yr, 1986-2010.
* QIS_Commodities (GitHub, jjj1231978), carry sleeve, https://github.com/jjj1231978/QIS_Commodities : static long F3 /
  short F0 in 17 CME BCOM roots with BCOM weights, Databento data, 2015-06-08..2026-05-04, net of modelled costs:
  Sharpe 1.15, 7.7 %/yr, vol 6.7 %, max DD -7.2 %. The repo quotes an unnamed bank QIS report: F3-F0 1.75,
  F6-F0 1.58, F6-F0 beta-hedged 1.86.
* Boons & Porras Prado (2019), JF 74(1) (definition of spreading returns), Two Sigma Street View Oct 2017
  ("roll return tax" of long-only front-month commodity exposure).

## Rule in our words

Hold, in every eligible commodity, a calendar spread long the later-delivery contract and short the earlier-delivery
contract of the two most liquid; the daily spread return is s = r_far - r_near (the T-bill cancels). Monthly decisions
at the last NYSE session, next-close fills.

* V1 (primary): every eligible COM15 root; spread notional per root = (0.10 / N) / sigma_s (N = eligible roots,
  sigma_s = EWMA com-60 vol of s); book rescaled to 10 % ex-ante vol (252-session leg covariance, min 60), scale cap
  4, then per-leg cap 3x NAV per root.
* V2: as V1 but a root is held only if its 21-session mean annualised carry (P_near/P_far)^(1/dt) - 1 (mean of valid
  daily observations over the last 21 NYSE sessions, at least 10 valid) is negative (contango); N = number of roots
  held; otherwise flat.
* V3: beta-hedged: far leg +w, near leg -beta x w, beta = OLS slope of r_far on r_near over the trailing 252 NYSE
  sessions (valid sessions only, at least 126; root skipped if beta is not finite or <= 0). The root's risk unit uses
  the hedged return h = r_far - beta r_near: sigma_h from the EWMA (com 60) second moments of the legs with the
  current beta; w = (0.10/N)/sigma_h; book scaling and caps as V1 (cap scales both legs together).

Universe COM15: CL HO RB NG GC SI PL HG ZC ZS ZW ZL ZM LE HE. Costs: each leg at the outright one-way rate
(CL/GC/SI/HG 2, NG/HO/RB/PL 3, grains/livestock 4 bp), one extra round trip per leg on its roll days; 2x stress.

## Adaptations and expected effects

* Deferred leg = later of the two most liquid contracts (no F3/F6 in our data). Often this is F1, sometimes a
  December or other high-open-interest month. Smaller term premium per unit of spread than F3-F0, so lower
  expected return per unit risk than the source.
* Volume ranks change composition (the second most liquid contract alternates between deferred months), so each leg
  rolls more often than the listed cycle; those changes are charged as rolls. Expected effect: higher costs than a
  scheduled F3-F0 roll; the gross Sharpe isolates it.
* Equal risk per root (STD) instead of BCOM weights; per-leg notional cap 3x NAV (metals spreads have 1-3 %/yr vol).
* Our sample starts 2010-06 (first position about 2011-08), source 2015-06; the 2011-2015 part is extra.
