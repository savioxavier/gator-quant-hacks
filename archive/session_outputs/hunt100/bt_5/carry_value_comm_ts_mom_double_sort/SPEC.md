# carry_value_comm_ts_mom_double_sort: term structure x momentum double sort (Fuertes, Miffre & Rallis 2010)

Pre-registered 2026-10-03 before any return of this strategy was computed. Common rules: ../COMMON_SPEC.md.

## Sources and their numbers

* Fuertes, Miffre & Rallis (2010), "Tactical allocation in commodity futures markets: combining momentum and term
  structure signals", JBF 34(10), https://openaccess.city.ac.uk/id/eprint/6416/1/Fuertes_Miffre_Rallis_JBF2010(CRO).pdf .
  37 commodities, 1979-2007. Section 5.1: at each month-end compute roll returns R = (ln P_near - ln P_second) x
  365 / (N_d - N_n), split into thirds (Low, Med, High); split High into High-Winner / High-Loser and Low into
  Low-Winner / Low-Loser by mean return over the past R months; buy High-Winner, short Low-Loser, hold one month,
  equal weights. Table 6 (L-S): TS1-Mom12-1 mean 18.81 %/yr (t 3.65), vol 26.8 %, reward/risk 0.70, net 18.25 %;
  TS1-Mom3-1 21.28 %, vol 27.9 %, reward/risk 0.76, net 20.69 %; TS1-Mom1-1 23.55 %, vol 27.6 %, reward/risk 0.85,
  net 22.88 %. Average of the 6 double sorts 21.32 %/yr versus 10.53 % momentum-only and 12.28 % TS-only. A
  2007-2008 hold-out gave reward-to-risk 0.86-1.23 (paper's robustness section).
* Quantpedia "Term structure effect in commodities" (FMR TS1, 1979-2004): Sharpe 0.49.
* Post-publication context: AQR VME commodity momentum 2013-07..2025-01 Sharpe -0.20; edge study's commodity carry
  XS_comm_C1_M 0.21 in-sample / 1.04 later (net).

## Rule in our words

Monthly at the last NYSE session; exec next_close.
1. Roll return RR_i = (P_near / P_far)^(1/dt) - 1 from the STD near/far legs: the last valid daily observation within
   the last 5 NYSE sessions up to the decision date.
2. Eligible COM15 roots (STD eligibility, valid RR, full momentum window of futures_daily returns) are sorted by RR;
   High = the k = floor(n/3) highest RR, Low = the k lowest (5/5/5 when n = 15).
3. Momentum = mean daily excess return of F_<root> (futures_daily) over the sessions after the month-end R months
   earlier through the decision date. High-Winner = the floor(k/2) roots of High with the highest momentum;
   Low-Loser = the floor(k/2) roots of Low with the lowest momentum.
4. Long High-Winner at +0.10/sigma_i each, short Low-Loser at -0.10/sigma_i each; book rescaled to 10 % ex-ante
   (252-session covariance of F_ excess returns, min 60, cap 4). P&L from futures_daily with the commodity cost map.

* V1 (primary): R = 12 months (TS1-Mom12-1). V2: R = 3. V3: R = 1.

## Adaptations and expected effects

* 15 commodities (FMR 37): legs of 2 names (FMR about 6), so far more idiosyncratic risk; lower Sharpe expected.
* Equal risk per name (FMR equal weights) and a 10 % vol-targeted book (FMR's book ran at about 27 % vol).
* Roll return from the two most liquid contracts (FMR: nearest and second nearest by maturity).
* Our sample is entirely post-publication (in-sample 2011-2024).
