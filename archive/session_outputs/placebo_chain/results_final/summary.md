# Stance-model backtests: PLACEBO CHAIN TEST (random scores; these numbers are not results)

**PLACEBO.** Every stance score here is random. This file only shows that the chain runs end to end.
No number below says anything about the strategies.

## Stance model (chrono walk-forward)

- Work root: `<scratch>\placebo_chain\chrono`
- Years merged: [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]; label-year rule: true; documents: 5225
- Non-full-spec years: none

| year | n_docs | n_sentences | val_macro_f1_by_seed | seed_label_agreement |
|---|---|---|---|---|
| 2015 | 74 | 9633 | n/a | n/a |
| 2016 | 222 | 9315 | n/a | n/a |
| 2017 | 251 | 10660 | n/a | n/a |
| 2018 | 278 | 8724 | n/a | n/a |
| 2019 | 571 | 13321 | n/a | n/a |
| 2020 | 439 | 12725 | n/a | n/a |
| 2021 | 494 | 14069 | n/a | n/a |
| 2022 | 462 | 10741 | n/a | n/a |
| 2023 | 629 | 14270 | n/a | n/a |
| 2024 | 658 | 16828 | n/a | n/a |
| 2025 | 702 | 17575 | n/a | n/a |
| 2026 | 445 | 9665 | n/a | n/a |

Label coverage and leakage audit (D1a): `data/label_year_audit.json` not found under the work root.

## Fed communication v2 (HYPOTHESIS_v2, Amendments 1-3)

- Chosen combination (max net 1x Sharpe, selection 2016-01-04..2020-12-31): **T4xE1**
- Selection Sharpe (net 1x): 0.317
- Validation Sharpe (net 1x, 2021-01-01..2024-10-02): 0.667 (target 0.7; difference -0.033)
- Full in-sample Sharpe at 2x costs: 0.419
- Decision rule (validation > 0 and full-IS 2x > 0.5): **FAILED**

Selection window, all 8 combinations:

| combo | first_position_date | sharpe_net1x | sharpe_net2x | sharpe_gross | ann_excess_arith | vol | max_dd_excess | turnover_per_year |
|---|---|---|---|---|---|---|---|---|
| T1xE1 | 2015-12-31 | -0.460 | -0.539 | -0.368 | -0.038 | 0.082 | -0.262 | 28.745 |
| T1xE2 | 2016-01-04 | -0.841 | -0.946 | -0.735 | -0.038 | 0.045 | -0.187 | 47.142 |
| T2xE1 | 2015-12-31 | 0.040 | -0.031 | 0.123 | 0.004 | 0.097 | -0.225 | 30.056 |
| T2xE2 | 2016-01-04 | -0.314 | -0.408 | -0.220 | -0.016 | 0.050 | -0.130 | 46.889 |
| T3xE1 | 2015-12-31 | 0.122 | 0.034 | 0.221 | 0.012 | 0.099 | -0.228 | 37.635 |
| T3xE2 | 2016-01-04 | -0.403 | -0.515 | -0.291 | -0.020 | 0.050 | -0.147 | 56.379 |
| T4xE1 | 2015-12-31 | 0.317 | 0.243 | 0.400 | 0.028 | 0.088 | -0.203 | 28.285 |
| T4xE2 | 2016-01-04 | -0.059 | -0.157 | 0.040 | -0.003 | 0.048 | -0.111 | 47.089 |

- Deflated Sharpe (11 trials): selection window 0.242, full in-sample 0.328; n = 10 sensitivity 0.255; PSR vs 0 (selection) 0.762

Falsifiers:

- selection Sharpe <= 0.2: False; validation <= 0: False; net 2x <= 0: False
- share of full-IS P&L from 2022: 0.116 (> half: False)
- corr(z_T2, z_T3) full IS: 0.967; corr(C_T2, M) full IS: -0.079

Portfolio test (core_ER_6 + chosen sleeve), in-sample:

| portfolio | window | sharpe_net1x | sharpe_net2x | ann_excess_geo | vol | max_dd_excess |
|---|---|---|---|---|---|---|
| core_ER_6 | selection | 1.062 | 0.940 | 0.065 | 0.061 | -0.073 |
| core_ER_6+T4xE1 | selection | 1.062 | 0.923 | 0.066 | 0.062 | -0.063 |
| core_ER_6 | validation | 0.912 | 0.795 | 0.056 | 0.062 | -0.075 |
| core_ER_6+T4xE1 | validation | 1.142 | 1.018 | 0.071 | 0.062 | -0.105 |
| core_ER_6 | full_is | 0.998 | 0.878 | 0.061 | 0.062 | -0.075 |
| core_ER_6+T4xE1 | full_is | 1.096 | 0.963 | 0.068 | 0.062 | -0.105 |

By chair, in-sample:

| series | chair | start | end | n_days | sharpe_net1x | sharpe_net2x | sharpe_gross |
|---|---|---|---|---|---|---|---|
| T4xE1 | Yellen | 2016-01-04 | 2018-02-02 | 526 | -0.465 | -0.538 | -0.382 |
| T4xE1 | Powell | 2018-02-05 | 2024-10-02 | 1676 | 0.754 | 0.698 | 0.819 |
| VariantA_frozen(T0fxE1) | Yellen | 2016-01-04 | 2018-02-02 | 526 | -0.624 | -0.681 | -0.549 |
| VariantA_frozen(T0fxE1) | Powell | 2018-02-05 | 2024-10-02 | 1676 | 0.618 | 0.579 | 0.669 |
| VariantA_2015warmup(T0v2xE1) | Yellen | 2016-01-04 | 2018-02-02 | 526 | -0.285 | -0.338 | -0.217 |
| VariantA_2015warmup(T0v2xE1) | Powell | 2018-02-05 | 2024-10-02 | 1676 | 0.597 | 0.559 | 0.647 |

Sensitivity (DEVIATIONS.md D-1, not used for selection): FOMC de-risk list registered vs scheduled-only:

| derisk_list | window | n_days | sharpe_net1x | sharpe_net2x | ann_excess_arith |
|---|---|---|---|---|---|
| registered_101_dates | selection | 1259 | 0.317 | 0.243 | 0.028 |
| registered_101_dates | validation | 943 | 0.667 | 0.623 | 0.068 |
| registered_101_dates | full_is | 2202 | 0.478 | 0.419 | 0.045 |
| scheduled_only_93_dates | selection | 1259 | 0.360 | 0.287 | 0.032 |
| scheduled_only_93_dates | validation | 943 | 0.667 | 0.623 | 0.068 |
| scheduled_only_93_dates | full_is | 2202 | 0.501 | 0.442 | 0.048 |

Out-of-sample: not evaluated (decision rule failed (validation net Sharpe <= 0 or full-IS 2x Sharpe <= 0.5)).

## Press-conference H1 (ADDENDUM, D1/D1a stance scores)

- Stance scorer recorded by the run: PLACEBO random scores (wiring test only)

- **G3 (confirmation sample, Powell 2023-2026, ZT, primary clock, 16:00 exit, gross): NO-GO: not detected (90% block-bootstrap CI upper bound 4.96 ticks)**
- n = 20, mean = -0.400 ticks (-3.12 USD), sign-flip wild bootstrap p (one-sided) = 0.5514, block-bootstrap 90% CI [-5.950, 4.955], permutation p = 0.5155
- exec30 mean = -1.200; leave-one-out range [-1.947, 1.368]; companion slope 0.00002 (HC3 t 0.030)

H1-primary and H1-Q, ZT, per meeting in USD (2016-2022 is the additional sample reported beside the confirmation sample; never part of G3):

| test | variant | sample | cost | n | mean | hit | t | wb_p_one | bb_ci90_lo | bb_ci90_hi |
|---|---|---|---|---|---|---|---|---|---|---|
| H1-primary[H1] | exec30|exit_1600 | 2016-2022 | C0 | 31 | 12.349 | 0.419 | 1.196 | 0.129 | -6.578 | 33.518 |
| H1-primary[H1] | exec30|exit_1600 | 2016-2022 | C2 | 31 | -22.933 | 0.258 | -2.162 | 0.980 | -42.843 | -0.756 |
| H1-primary[H1] | exec30|exit_1600 | 2016-2022 | C4 | 31 | -58.216 | 0.161 | -5.192 | 1 | -80.393 | -34.526 |
| H1-primary[H1] | primary|exit_1600 | 2016-2022 | C0 | 31 | 13.609 | 0.419 | 1.360 | 0.099 | -5.292 | 34.778 |
| H1-primary[H1] | primary|exit_1600 | 2016-2022 | C2 | 31 | -21.673 | 0.258 | -2.111 | 0.979 | -41.331 | 0.756 |
| H1-primary[H1] | primary|exit_1600 | 2016-2022 | C4 | 31 | -56.956 | 0.226 | -5.246 | 1 | -78.629 | -33.014 |
| H1-primary[H1] | primary|exit_1630 | 2016-2022 | C0 | 31 | 11.593 | 0.419 | 1.029 | 0.170 | -7.560 | 31.754 |
| H1-primary[H1] | primary|exit_1630 | 2016-2022 | C2 | 31 | -23.690 | 0.226 | -2.056 | 0.977 | -42.843 | -3.276 |
| H1-primary[H1] | primary|exit_1630 | 2016-2022 | C4 | 31 | -58.972 | 0.129 | -4.884 | 1 | -79.889 | -37.298 |
| H1-primary[H1] | exec30|exit_1600 | confirmation | C0 | 20 | -9.375 | 0.450 | -0.406 | 0.655 | -51.562 | 30.469 |
| H1-primary[H1] | exec30|exit_1600 | confirmation | C2 | 20 | -40.625 | 0.200 | -1.757 | 0.957 | -82.812 | -0.781 |
| H1-primary[H1] | exec30|exit_1600 | confirmation | C4 | 20 | -71.875 | 0.150 | -3.109 | 0.999 | -114.062 | -32.031 |
| H1-primary[H1] | primary|exit_1600 | confirmation | C0 | 20 | -3.125 | 0.500 | -0.136 | 0.551 | -46.484 | 38.711 |
| H1-primary[H1] | primary|exit_1600 | confirmation | C2 | 20 | -34.375 | 0.250 | -1.493 | 0.926 | -77.734 | 7.461 |
| H1-primary[H1] | primary|exit_1600 | confirmation | C4 | 20 | -65.625 | 0.150 | -2.851 | 0.997 | -108.984 | -23.789 |
| H1-primary[H1] | primary|exit_1630 | confirmation | C0 | 20 | -16.797 | 0.400 | -0.833 | 0.797 | -58.203 | 22.305 |
| H1-primary[H1] | primary|exit_1630 | confirmation | C2 | 20 | -48.047 | 0.200 | -2.383 | 0.986 | -89.453 | -8.945 |
| H1-primary[H1] | primary|exit_1630 | confirmation | C4 | 20 | -79.297 | 0.100 | -3.933 | 1.000 | -120.703 | -40.195 |
| H1-primary[H1] | exec30|exit_1600 | warsh | C0 | 3 | 52.083 | 0.667 | 1.004 | 0.253 | -7.812 | 111.979 |
| H1-primary[H1] | exec30|exit_1600 | warsh | C2 | 3 | 20.833 | 0.667 | 0.402 | 0.375 | -39.062 | 80.729 |
| H1-primary[H1] | exec30|exit_1600 | warsh | C4 | 3 | -10.417 | 0.333 | -0.201 | 0.753 | -70.312 | 49.479 |
| H1-primary[H1] | primary|exit_1600 | warsh | C0 | 3 | 46.875 | 0.667 | 0.986 | 0.253 | -7.812 | 101.562 |
| H1-primary[H1] | primary|exit_1600 | warsh | C2 | 3 | 15.625 | 0.667 | 0.329 | 0.375 | -39.062 | 70.312 |
| H1-primary[H1] | primary|exit_1600 | warsh | C4 | 3 | -15.625 | 0.333 | -0.329 | 0.753 | -70.312 | 39.062 |
| H1-primary[H1] | primary|exit_1630 | warsh | C0 | 3 | 2.604 | 0.667 | 0.038 | 0.504 | -70.312 | 75.521 |
| H1-primary[H1] | primary|exit_1630 | warsh | C2 | 3 | -28.646 | 0.667 | -0.419 | 0.624 | -101.562 | 44.271 |
| H1-primary[H1] | primary|exit_1630 | warsh | C4 | 3 | -59.896 | 0.333 | -0.877 | 0.745 | -132.812 | 13.021 |
| H1-Q[H1Q] | exec30|exit_1600 | 2016-2022 | C0 | 31 | 7.812 | 0.484 | 0.746 | 0.242 | -2.520 | 18.397 |
| H1-Q[H1Q] | exec30|exit_1600 | 2016-2022 | C2 | 31 | -27.470 | 0.258 | -2.696 | 0.995 | -36.794 | -17.641 |
| H1-Q[H1Q] | exec30|exit_1600 | 2016-2022 | C4 | 31 | -62.752 | 0.097 | -6.114 | 1 | -73.337 | -52.167 |
| H1-Q[H1Q] | primary|exit_1600 | 2016-2022 | C0 | 31 | 7.056 | 0.452 | 0.690 | 0.262 | -2.520 | 16.885 |
| H1-Q[H1Q] | primary|exit_1600 | 2016-2022 | C2 | 31 | -28.226 | 0.226 | -2.827 | 0.995 | -37.046 | -19.153 |
| H1-Q[H1Q] | primary|exit_1600 | 2016-2022 | C4 | 31 | -63.508 | 0.161 | -6.286 | 1 | -73.841 | -53.427 |
| H1-Q[H1Q] | primary|exit_1630 | 2016-2022 | C0 | 31 | -2.016 | 0.452 | -0.176 | 0.571 | -15.373 | 10.837 |
| H1-Q[H1Q] | primary|exit_1630 | 2016-2022 | C2 | 31 | -37.298 | 0.161 | -3.335 | 0.999 | -50.907 | -25.202 |
| H1-Q[H1Q] | primary|exit_1630 | 2016-2022 | C4 | 31 | -72.581 | 0.065 | -6.465 | 1 | -87.702 | -59.728 |
| H1-Q[H1Q] | exec30|exit_1600 | confirmation | C0 | 20 | -9.375 | 0.450 | -0.406 | 0.661 | -34.766 | 17.578 |
| H1-Q[H1Q] | exec30|exit_1600 | confirmation | C2 | 20 | -40.625 | 0.150 | -1.757 | 0.955 | -66.016 | -13.672 |
| H1-Q[H1Q] | exec30|exit_1600 | confirmation | C4 | 20 | -71.875 | 0.150 | -3.109 | 0.997 | -97.266 | -44.922 |
| H1-Q[H1Q] | primary|exit_1600 | confirmation | C0 | 20 | -4.688 | 0.500 | -0.204 | 0.588 | -27.734 | 20.703 |
| H1-Q[H1Q] | primary|exit_1600 | confirmation | C2 | 20 | -35.938 | 0.200 | -1.562 | 0.936 | -58.984 | -10.547 |
| H1-Q[H1Q] | primary|exit_1600 | confirmation | C4 | 20 | -67.188 | 0.150 | -2.921 | 0.996 | -90.234 | -41.797 |
| H1-Q[H1Q] | primary|exit_1630 | confirmation | C0 | 20 | -3.516 | 0.500 | -0.171 | 0.580 | -29.688 | 27.344 |
| H1-Q[H1Q] | primary|exit_1630 | confirmation | C2 | 20 | -34.766 | 0.300 | -1.695 | 0.947 | -60.938 | -3.906 |
| H1-Q[H1Q] | primary|exit_1630 | confirmation | C4 | 20 | -66.016 | 0.100 | -3.219 | 0.998 | -92.188 | -35.156 |
| H1-Q[H1Q] | exec30|exit_1600 | warsh | C0 | 3 | 52.083 | 0.667 | 1.004 | 0.253 | -7.812 | 111.979 |
| H1-Q[H1Q] | exec30|exit_1600 | warsh | C2 | 3 | 20.833 | 0.667 | 0.402 | 0.375 | -39.062 | 80.729 |
| H1-Q[H1Q] | exec30|exit_1600 | warsh | C4 | 3 | -10.417 | 0.333 | -0.201 | 0.753 | -70.312 | 49.479 |
| H1-Q[H1Q] | primary|exit_1600 | warsh | C0 | 3 | 46.875 | 0.667 | 0.986 | 0.253 | -7.812 | 101.562 |
| H1-Q[H1Q] | primary|exit_1600 | warsh | C2 | 3 | 15.625 | 0.667 | 0.329 | 0.375 | -39.062 | 70.312 |
| H1-Q[H1Q] | primary|exit_1600 | warsh | C4 | 3 | -15.625 | 0.333 | -0.329 | 0.753 | -70.312 | 39.062 |
| H1-Q[H1Q] | primary|exit_1630 | warsh | C0 | 3 | 2.604 | 0.667 | 0.038 | 0.504 | -70.312 | 75.521 |
| H1-Q[H1Q] | primary|exit_1630 | warsh | C2 | 3 | -28.646 | 0.667 | -0.419 | 0.624 | -101.562 | 44.271 |
| H1-Q[H1Q] | primary|exit_1630 | warsh | C4 | 3 | -59.896 | 0.333 | -0.877 | 0.745 | -132.812 | 13.021 |

H1-answer (diagnostic), ZT, gross:

| sample | h | unit | n_answers | n_meetings | mean | t_cr1 | wcb_p_two | mtg_mean | mtg_wb_p_two |
|---|---|---|---|---|---|---|---|---|---|
| 2016-2022 | 1 | usd | 684 | 31 | 0.320 | 0.457 | 0.668 | 0.242 | 0.739 |
| 2016-2022 | 5 | usd | 249 | 31 | -0.753 | -0.179 | 0.874 | -0.636 | 0.907 |
| 2016-2022 | 15 | usd | 100 | 31 | 2.969 | 0.350 | 0.732 | 2.268 | 0.802 |
| confirmation | 1 | ticks | 545 | 20 | -0.020 | -0.215 | 0.830 | -0.044 | 0.687 |
| confirmation | 5 | ticks | 162 | 20 | 0.346 | 1.141 | 0.269 | 0.297 | 0.377 |
| confirmation | 15 | ticks | 62 | 20 | 1.371 | 1.355 | 0.184 | 1.317 | 0.220 |
| warsh | 1 | ticks | 59 | 3 | 0.475 | 1.747 | 0.358 | 0.422 | 0.506 |
| warsh | 5 | ticks | 19 | 3 | -0.263 | -0.145 | 0.775 | -0.619 | 0.756 |
| warsh | 15 | ticks | 8 | 3 | 3.750 | 1.707 | 0.382 | 3.167 | 0.506 |

Inputs:

- v2 outputs: `<scratch>\placebo_chain\v2_out`
- press-conference outputs: `<scratch>\placebo_chain\presser_out`
- press-conference text with stance columns: `<scratch>\placebo_chain\presser_text`
