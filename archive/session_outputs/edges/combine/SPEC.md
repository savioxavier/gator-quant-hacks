# Combine: rule-based portfolios of the verified sleeves (SPEC, written before any portfolio result)

Written 2026-10-03 before computing any combination. The single-sleeve results of the four analyst
studies and their verifications were known when this was written (they are the inputs); no
portfolio, ablation or correlation of sleeves had been computed.

## 1. Sleeves

Eligibility follows the VERIFIER verdict where analyst and verifier disagree.

### Core (verifier real_edge + trend + equity premium)

| sleeve | family | source | why |
|---|---|---|---|
| rpm_ES_MM | equity premium | edges/series/rpm_ES_MM.parquet | equity premium; the verifier names it "the defensible building block"; analyst's in-sample pick among the 4 real_edge ES variants (all are the same premium; one sleeve per premium) |
| CAL_TSY_ME_ZN | calendar | edges/series/CAL_TSY_ME_ZN.parquet | only real_edge outside the equity premium (Hartley-Schwarz 2019) |
| S1 | trend | forward2 S1 decisions, re-simulated at realistic costs | the forward-test-2 trend book (Hurst-Ooi-Pedersen 1/3/12 blend), the literature's crisis diversifier |

Every other real_edge row of the verifiers is the same equity premium (rpm_ES_STATIC, rpm_ES_CV,
rpm_ES_CVB) and is not added as a second sleeve.

### Broad (core + verifier weak_or_uncertain, deduplicated) - reported separately

Dedup rules fixed here: (a) robustness twins (*_CVB, *_FBB) are dropped; (b) overlays of a premium
already held (rpm_ES_FB, rpm_ES_FBB) are dropped; (c) mixtures of premia already held as sleeves
(rpm_SB_*: ES + ZN) are dropped, the bond premium enters once as rpm_ZN_FB; (d) the composite
carry_ts_global is dropped in favour of its weak class books (it also contains the failed TS fx and
TS rates books); (e) F2's C_F stream is dropped because CAL_TSY_ME_ZN is the same sleeve (corr 0.97).

| sleeve | family | verdict basis |
|---|---|---|
| rpm_ZN_FB | bonds | verifier weak |
| carry_xs_rates | carry | verifier weak |
| carry_xs_comm | carry | verifier weak |
| carry_ts_comm | carry | verifier weak |
| carry_ts_eq | carry | verifier weak (equity timing; kept in the carry family by origin) |
| CAL_PREHOL_ES | calendar | verifier weak |
| TSMOM_F | trend | existing benchmark; weak by earlier evidence (0.28 in-sample / 0.14 later) |
| A_F (F2 month-end rebalancing stream, ES16/ZN16) | calendar | existing; weak by earlier evidence (F1/F2 out-of-sample about -0.1) |

Value family: no sleeve is eligible (every value_reversal row fails), so the value family is empty.

## 2. Existing series computed here (realistic costs)

Realistic one-way cost map (bp of notional): ES 0.75 (matches the risk-premia and calendar studies),
NQ/YM 0.75, RTY 1.0; ZT 0.3, ZF 0.5, ZN 1.0, ZB 1.25, UB 1.5; 6E 0.5, 6J/6B/6A/6C 0.75, 6S 1.0;
CL/GC/SI/HG 1.5; NG/HO/RB/PL 2.5; ZC/ZS/ZW/ZL/ZM/LE/HE 4.0; ES16 0.75, ZN16 1.0. 2x stress doubles
every cost. Roll days: one extra round trip (engine). ETFs (S3) use the project ETF costs.

- S1: forward2.s1_decisions("FWD") simulated with engine.simulate(next_close) and the map above.
  Natively 10 % ex-ante (instrument EWMA vol + trailing 252-day covariance), so no extra scaling.
- TSMOM_F: forward.py's pct decisions on its 20 futures, re-simulated with the map; then scaled.
- A_F, C_F: forward.stream_frames("F2") decision weights, re-simulated with the map; then scaled.
- F2 (native frozen costs, forward.returns("F2","FWD")) for correlations; also a scaled copy.
- Sleeve scaler for series that are not natively at 10 %: k_d = min(4, 0.10 / sigma_d), sigma_d =
  annualised std of the unscaled stream's trailing 252 daily excess returns (min 126), set at each
  month-end close d, applied to return days from d+2 (next-close convention). Changing k is a trade:
  cost |dk| x stream gross x average one-way cost of the stream (gross-weighted over its instruments).
- Comparators: S2, S3, ES_10VOL from forward2 at their frozen costs (as forward test 2 reports
  them), plus S2 and ES_10VOL at the realistic map.

## 3. Portfolio construction (no optimisation on returns)

Sleeve input = daily excess return (net_1x; net_2x for the 2x run; gross for gross), each at about
10 % ex-ante vol. Decisions at each month-end close d using sleeve returns up to d; multipliers apply
to return days from d+2. A sleeve is live at d if it has >= 126 non-missing returns up to d.

1. ER (equal risk): w_s = 1/N over live sleeves.
2. IV (inverse vol): w_s proportional to 1 / std of the sleeve's trailing 252 daily returns, sum 1.
3. FAM (equal risk per family): within each family equal weights, the family sub-book rescaled to
   10 % with its trailing 252-day covariance (family scale capped at 3); families equal-weighted.
   For the core, families = sleeves, so FAM = ER up to the family rescale (each a single sleeve).

Portfolio scale k_d = target / sqrt(252 w' S w), S = trailing 252-day sample covariance of live
sleeves (min 126 obs, pairwise, NaN -> 0). Targets: 6 % and 10 %.

Leverage cap 4 on summed instrument gross: G_t = sum_s |k w_s| g_s,t; if G_t > 4 every multiplier is
multiplied by 4 / G_t on that day (g_s,t of day t is the sleeve's held gross, which is decided at
t-2 under next_close, so the cap is point-in-time). Netting across sleeves is ignored (conservative).
Sleeve gross g_s,t: single-instrument sleeves (rpm_ES_MM on F_ES, rpm_ZN_FB on F_ZN, CAL_TSY_ME_ZN on
ZN16, CAL_PREHOL_ES on ES16): |gross sleeve excess return / instrument excess return| on days where
|instrument excess| > 1e-6, otherwise carried forward (monthly / window-fixed positions make this
near exact); carry books: constant median gross from carry/book_diagnostics_summary.csv (C1 monthly:
xs_rates 10.07, xs_comm 1.17, ts_comm 1.13, ts_eq 0.54); series computed here: exact held gross.

Overlay cost (changing a sleeve's multiplier is a real trade): sum_s |m_s,t - m_s,t-1| x g_s,t x c_s,
c_s = sleeve average one-way cost (rpm_ES_MM 0.75, CAL_TSY_ME_ZN 1.0, rpm_ZN_FB 1.0, CAL_PREHOL_ES
0.75, carry_xs_rates 0.6, carry_xs_comm / carry_ts_comm 2.9, carry_ts_eq 0.8, own-computed sleeves
gross-weighted from their holdings), doubled in the 2x run, zero in the gross run.

## 4. Variants (all reported)

Main grid: {core, broad} x {ER, IV, FAM} x {6 %, 10 %} = 12.
Diagnostics (ER, 10 %): core without trend; core without CAL_TSY_ME_ZN; core without rpm_ES_MM;
core with rpm_ES_CV (= ES_10VOL rule) instead of rpm_ES_MM; core with TSMOM_F instead of S1 = 5.
Total portfolio variants: 17. Study-wide trial count for the Deflated Sharpe: 40 (carry) + 36 (risk
premia) + 13 (calendar) + 11 (value) + 17 (here) = 117 (earlier project trials are not added).
"Best portfolio" for DSR = highest in-sample net 1x Sharpe among the 12 main-grid portfolios.

## 5. Windows and statistics

In-sample = common start (first return day on which every core and broad sleeve is live, i.e.
decision + 2 sessions) .. 2024-10-02. Later window 2024-10-03 .. 2026-10-02 is descriptive only and
is not used for any choice. Also in-sample halves split at 2018-01-01.

Per portfolio: net Sharpe (1x, 2x), gross Sharpe, annual return (geometric, total incl. T-bill)
and annual excess return, vol, max drawdown (total return; excess drawdown also), worst calendar
year, % positive years (full years only), rolling 504-day Sharpe p10/p50/p90, longest drawdown
duration (sessions, excess-return equity), Newey-West t, turnover (overlay + sleeve-gross proxy
not available for analyst sleeves; overlay turnover reported), median gross, share of days the cap
binds, correlation with ES (F_ES excess), S1 and F2. Correlation matrix of sleeves (in-sample);
diversification ratio = sum_s std(m_s x_s) / std(portfolio) (realised, in-sample) and median
ex-ante DR. Deflated Sharpe (engine.deflated_sharpe; var of Sharpe across trials = cross-sectional
variance of in-sample Sharpe of all saved edge series plus these portfolios). CSCV PBO (src/pbo.py,
16 blocks) across the 12 main-grid rules and across all 17. Paired block bootstrap (63-day blocks,
5000 draws) of the best portfolio vs ES_10VOL, vs rpm_ES_MM alone and vs S2 on the in-sample window.

Verdict rule for a portfolio (fixed here): real_edge if in-sample net 1x Sharpe NW t >= 2, 2x Sharpe
> 0, positive in both halves, >= 60 % positive years, and max drawdown at 10 % vol shallower than
-20 %; fails if net 1x Sharpe <= 0 or t < 1; otherwise weak_or_uncertain. The later window is
reported, never used for the verdict, but discussed.
