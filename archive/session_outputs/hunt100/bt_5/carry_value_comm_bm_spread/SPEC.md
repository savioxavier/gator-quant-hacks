# carry_value_comm_bm_spread: basis-momentum spreading returns (Boons & Porras Prado 2019)

Pre-registered 2026-10-03 before any return of this strategy was computed. Common rules: ../COMMON_SPEC.md.

## Sources and their numbers

* Boons & Porras Prado (2019), "Basis-Momentum", JF 74(1) 239-279,
  https://4nations.albertjmenkveld.com/papers/boonsprado17.pdf . 21 commodities, 1960-08..2014-02. BM_t = product
  over the last 12 months of (1 + first-nearby return) minus product of (1 + second-nearby return). Monthly sort
  into High4 (4 highest BM), Mid, Low4; equal-weighted. Table 1 Panel B: High4-minus-Low4 SPREADING return
  (first-nearby minus second-nearby) 4.08 %/yr (t 6.43); Panel A nearby return 18.38 %/yr (t 6.73); "a Sharpe ratio
  of about 0.9" for both; robust pre/post 1986. Contracts expiring in month t+2 are rolled in month t.
* Independent outright-BM evidence: Sakkas & Tessaromatis (JBF 2020, 38 commodities, 1970-2018) long-short Sharpe
  0.93; Jiang & Liu (EFMA 2024, 1985-2022) 0.43; ddxmy/Basis-Momentum GitHub F0/F6 2008-01..2026-07 Sharpe 0.65
  at 5 bp, annual Sharpe 2019-2025 -1.35, 1.01, -1.04, 0.17, 0.31, 0.21, 0.76; QIS_Commodities 63-day variant
  2015-2026 -0.41. No independent test of the spread version was found.

## Rule in our words

At each month-end, for every eligible root, BM = prod over the last 252 NYSE sessions of (1 + r_near) minus
prod of (1 + r_far) (STD same-contract leg returns, invalid sessions count as 0 and need >= 200 valid sessions).
Positions are spreads: a positive spread weight means long near / short far (spread return r_near - r_far).

* V1 (primary, paper Table 1 Panel B): rank eligible COM15 roots by BM; High4 (4 highest) +1 spread unit each,
  Low4 (4 lowest) -1 spread unit each (short near / long far); each spread at 0.10 / sigma_s (sigma_s = EWMA com-60
  vol of r_near - r_far); book rescaled to 10 % ex-ante (252-session leg covariance, min 60, cap 4), per-leg cap
  3x NAV per root. If fewer than 8 roots are eligible, min(4, floor(N/2)) per side. Monthly, next-close fills.
* V2: KMPV rank weights on BM across all eligible COM15 roots (w = (rank - (N+1)/2) / sum of positive deviations,
  N >= 3), spread position w x 0.10 / sigma_s, same scaling and caps.
* V3: V1's book built separately for COM15, FX6 (6E 6J 6B 6A 6C 6S), EQ4 (ES NQ YM RTY) and RATES5 (ZT ZF ZN ZB UB)
  with min(4, floor(N_class/2)) per side (class needs N >= 2), each class book scaled to 10 % (cap 4, leg cap 3);
  global = equal-weight average of the available class books, rescaled to 10 % (cap 4), then leg cap 3.

Costs: both legs at the outright map (FX 1, ES/NQ/YM 1, RTY 2, ZT 0.5, ZF 0.7, ZN 1, ZB/UB 1.5; commodities as
COMMON_SPEC), roll round trips per leg; 2x stress.

## Adaptations and expected effects

* Far leg = later of the two most liquid contracts (paper: second-nearby with expiry after t+2). Our near leg is
  usually the volume-front contract and may be held closer to expiry than the paper's; noisier BM and spread
  returns, likely a weaker effect.
* 15 commodities (paper 21): High4/Low4 is 27 % of the cross-section per side here (19 % in the paper).
* Equal risk per spread (paper: equal weight), book vol-targeted.
* V3's FX/EQ/RATES curves are interest-rate/dividend arbitrage spreads; FX volume ranks also alternate with serial
  months, which changes the legs often. Expected weak or negative.
* Post-publication data (paper sample ends 2014-02; our in-sample 2011-2024) where outright replications show
  about 0.1.
