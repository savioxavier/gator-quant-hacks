# Stance-model backtests: results

## Stance model (chrono walk-forward)

- Work root: `<work>\chrono\full`
- Years merged: [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]; label-year rule: true; documents: 5225
- Non-full-spec years: none

| year | n_docs | n_sentences | val_macro_f1_by_seed | seed_label_agreement |
|---|---|---|---|---|
| 2015 | 74 | 8595 | 0.568, 0.564, 0.598 | 0.851 |
| 2016 | 222 | 8906 | 0.631, 0.625, 0.599 | 0.892 |
| 2017 | 251 | 10279 | 0.599, 0.613, 0.621 | 0.863 |
| 2018 | 278 | 9145 | 0.608, 0.573, 0.571 | 0.851 |
| 2019 | 571 | 14145 | 0.580, 0.611, 0.545 | 0.897 |
| 2020 | 439 | 13505 | 0.629, 0.619, 0.623 | 0.875 |
| 2021 | 494 | 15314 | 0.654, 0.650, 0.647 | 0.883 |
| 2022 | 462 | 12762 | 0.645, 0.623, 0.571 | 0.858 |
| 2023 | 629 | 16186 | 0.653, 0.650, 0.653 | 0.884 |
| 2024 | 658 | 18750 | 0.660, 0.649, 0.684 | 0.865 |
| 2025 | 702 | 20078 | 0.659, 0.669, 0.655 | 0.901 |
| 2026 | 445 | 11688 | 0.659, 0.669, 0.653 | 0.907 |

Label coverage and leakage per model year (D1a / Amendment 3; rule `true`; every training row's source document is dated before Y by construction). `verbatim >= Y` = training rows whose sentence also appears verbatim in a scored document dated Y or later; `first >= Y` = rows whose first verbatim corpus occurrence is dated Y or later:

| model_year | train_rows | verbatim >= Y | first >= Y |
|---|---|---|---|
| 2015 | 1606 | 21 | 21 |
| 2016 | 1673 | 18 | 3 |
| 2017 | 1738 | 23 | 2 |
| 2018 | 1836 | 23 | 2 |
| 2019 | 1901 | 29 | 2 |
| 2020 | 2016 | 24 | 2 |
| 2021 | 2184 | 30 | 2 |
| 2022 | 2344 | 12 | 1 |
| 2023 | 2480 | 8 | 1 |
| 2024 | 2480 | 6 | 0 |
| 2025 | 2480 | 5 | 0 |
| 2026 | 2480 | 4 | 0 |

## Fed communication v2 (HYPOTHESIS_v2, Amendments 1-3)

- Chosen combination (max net 1x Sharpe, selection 2016-01-04..2020-12-31): **T4xE1**
- Selection Sharpe (net 1x): 0.154
- Validation Sharpe (net 1x, 2021-01-01..2024-10-02): 0.687 (target 0.7; difference -0.013)
- Full in-sample Sharpe at 2x costs: 0.387
- Decision rule (validation > 0 and full-IS 2x > 0.5): **FAILED**

Selection window, all 8 combinations:

| combo | first_position_date | sharpe_net1x | sharpe_net2x | sharpe_gross | ann_excess_arith | vol | max_dd_excess | turnover_per_year |
|---|---|---|---|---|---|---|---|---|
| T1xE1 | 2015-12-31 | -0.582 | -0.645 | -0.501 | -0.051 | 0.088 | -0.275 | 25.162 |
| T1xE2 | 2016-01-04 | -0.358 | -0.456 | -0.259 | -0.016 | 0.043 | -0.124 | 42.885 |
| T2xE1 | 2015-12-31 | -0.346 | -0.425 | -0.248 | -0.032 | 0.092 | -0.253 | 31.696 |
| T2xE2 | 2016-01-04 | -0.177 | -0.299 | -0.055 | -0.008 | 0.045 | -0.126 | 54.715 |
| T3xE1 | 2015-12-31 | -0.205 | -0.281 | -0.113 | -0.021 | 0.102 | -0.244 | 33.658 |
| T3xE2 | 2016-01-04 | -0.065 | -0.176 | 0.046 | -0.003 | 0.050 | -0.137 | 55.063 |
| T4xE1 | 2015-12-31 | 0.154 | 0.053 | 0.269 | 0.012 | 0.081 | -0.161 | 35.047 |
| T4xE2 | 2016-01-04 | 0.151 | 0.018 | 0.284 | 0.006 | 0.043 | -0.124 | 57.175 |

- Deflated Sharpe (11 trials): selection window 0.223, full in-sample 0.436; n = 10 sensitivity 0.232; PSR vs 0 (selection) 0.634

Falsifiers:

- selection Sharpe <= 0.2: True; validation <= 0: False; net 2x <= 0: False
- share of full-IS P&L from 2022: 0.739 (> half: True)
- corr(z_T2, z_T3) full IS: 0.975; corr(C_T2, M) full IS: 0.186

Portfolio test (core_ER_6 + chosen sleeve), in-sample:

| portfolio | window | sharpe_net1x | sharpe_net2x | ann_excess_geo | vol | max_dd_excess |
|---|---|---|---|---|---|---|
| core_ER_6 | selection | 1.062 | 0.940 | 0.065 | 0.061 | -0.073 |
| core_ER_6+T4xE1 | selection | 0.928 | 0.778 | 0.057 | 0.062 | -0.062 |
| core_ER_6 | validation | 0.912 | 0.795 | 0.056 | 0.062 | -0.075 |
| core_ER_6+T4xE1 | validation | 1.185 | 1.083 | 0.074 | 0.062 | -0.077 |
| core_ER_6 | full_is | 0.998 | 0.878 | 0.061 | 0.062 | -0.075 |
| core_ER_6+T4xE1 | full_is | 1.038 | 0.909 | 0.064 | 0.062 | -0.077 |

By chair, in-sample:

| series | chair | start | end | n_days | sharpe_net1x | sharpe_net2x | sharpe_gross |
|---|---|---|---|---|---|---|---|
| T4xE1 | Yellen | 2016-01-04 | 2018-02-02 | 526 | 0.031 | -0.073 | 0.151 |
| T4xE1 | Powell | 2018-02-05 | 2024-10-02 | 1676 | 0.537 | 0.494 | 0.592 |
| VariantA_frozen(T0fxE1) | Yellen | 2016-01-04 | 2018-02-02 | 526 | -0.624 | -0.681 | -0.549 |
| VariantA_frozen(T0fxE1) | Powell | 2018-02-05 | 2024-10-02 | 1676 | 0.618 | 0.579 | 0.669 |
| VariantA_2015warmup(T0v2xE1) | Yellen | 2016-01-04 | 2018-02-02 | 526 | -0.285 | -0.338 | -0.217 |
| VariantA_2015warmup(T0v2xE1) | Powell | 2018-02-05 | 2024-10-02 | 1676 | 0.597 | 0.559 | 0.647 |

Sensitivity (DEVIATIONS.md D-1, not used for selection): FOMC de-risk list registered vs scheduled-only:

| derisk_list | window | n_days | sharpe_net1x | sharpe_net2x | ann_excess_arith |
|---|---|---|---|---|---|
| registered_101_dates | selection | 1259 | 0.154 | 0.053 | 0.012 |
| registered_101_dates | validation | 943 | 0.687 | 0.664 | 0.100 |
| registered_101_dates | full_is | 2202 | 0.441 | 0.387 | 0.050 |
| scheduled_only_93_dates | selection | 1259 | 0.156 | 0.057 | 0.013 |
| scheduled_only_93_dates | validation | 943 | 0.687 | 0.664 | 0.100 |
| scheduled_only_93_dates | full_is | 2202 | 0.442 | 0.388 | 0.050 |

Out-of-sample: not evaluated (decision rule failed (validation net Sharpe <= 0 or full-IS 2x Sharpe <= 0.5)).

## Press-conference H1 (ADDENDUM, D1/D1a stance scores)

- Stance scorer recorded by the run: chrono walk-forward stance model (DEVIATION_D1 + D1a = HYPOTHESIS_v2 Amendments 2-3; model Y scores year Y; 3-seed mean probabilities, argmax; label-year rule true)

- **G3 (confirmation sample, Powell 2023-2026, ZT, primary clock, 16:00 exit, gross): NO-GO: not detected (90% block-bootstrap CI upper bound 5.30 ticks)**
- n = 20, mean = 0.500 ticks (3.91 USD), sign-flip wild bootstrap p (one-sided) = 0.4505, block-bootstrap 90% CI [-4.055, 5.300], permutation p = 0.6677
- exec30 mean = 0.500; leave-one-out range [-1.263, 2.053]; companion slope 0.00056 (HC3 t 0.547)

H1-primary and H1-Q, ZT, per meeting in USD (2016-2022 is the additional sample reported beside the confirmation sample; never part of G3):

| test | variant | sample | cost | n | mean | hit | t | wb_p_one | bb_ci90_lo | bb_ci90_hi |
|---|---|---|---|---|---|---|---|---|---|---|
| H1-primary[H1] | exec30|exit_1600 | 2016-2022 | C0 | 31 | 3.276 | 0.484 | 0.311 | 0.390 | -11.089 | 17.137 |
| H1-primary[H1] | exec30|exit_1600 | 2016-2022 | C2 | 31 | -32.006 | 0.226 | -2.909 | 0.996 | -48.891 | -16.129 |
| H1-primary[H1] | exec30|exit_1600 | 2016-2022 | C4 | 31 | -67.288 | 0.097 | -5.724 | 1 | -87.702 | -48.891 |
| H1-primary[H1] | primary|exit_1600 | 2016-2022 | C0 | 31 | 2.520 | 0.452 | 0.245 | 0.414 | -11.089 | 15.373 |
| H1-primary[H1] | primary|exit_1600 | 2016-2022 | C2 | 31 | -32.762 | 0.226 | -3.060 | 0.998 | -48.891 | -17.893 |
| H1-primary[H1] | primary|exit_1600 | 2016-2022 | C4 | 31 | -68.044 | 0.129 | -5.957 | 1 | -87.450 | -50.655 |
| H1-primary[H1] | primary|exit_1630 | 2016-2022 | C0 | 31 | -7.056 | 0.516 | -0.619 | 0.731 | -25.202 | 8.569 |
| H1-primary[H1] | primary|exit_1630 | 2016-2022 | C2 | 31 | -42.339 | 0.194 | -3.647 | 0.999 | -62.248 | -24.950 |
| H1-primary[H1] | primary|exit_1630 | 2016-2022 | C4 | 31 | -77.621 | 0.065 | -6.402 | 1 | -99.798 | -57.964 |
| H1-primary[H1] | exec30|exit_1600 | confirmation | C0 | 20 | 3.906 | 0.500 | 0.168 | 0.452 | -33.594 | 42.578 |
| H1-primary[H1] | exec30|exit_1600 | confirmation | C2 | 20 | -27.344 | 0.150 | -1.179 | 0.880 | -64.844 | 11.328 |
| H1-primary[H1] | exec30|exit_1600 | confirmation | C4 | 20 | -58.594 | 0.150 | -2.526 | 0.990 | -96.094 | -19.922 |
| H1-primary[H1] | primary|exit_1600 | confirmation | C0 | 20 | 3.906 | 0.550 | 0.170 | 0.451 | -31.680 | 41.406 |
| H1-primary[H1] | primary|exit_1600 | confirmation | C2 | 20 | -27.344 | 0.200 | -1.188 | 0.882 | -62.930 | 10.156 |
| H1-primary[H1] | primary|exit_1600 | confirmation | C4 | 20 | -58.594 | 0.150 | -2.546 | 0.991 | -94.180 | -21.094 |
| H1-primary[H1] | primary|exit_1630 | confirmation | C0 | 20 | -11.328 | 0.400 | -0.556 | 0.724 | -37.891 | 14.844 |
| H1-primary[H1] | primary|exit_1630 | confirmation | C2 | 20 | -42.578 | 0.250 | -2.091 | 0.977 | -69.141 | -16.406 |
| H1-primary[H1] | primary|exit_1630 | confirmation | C4 | 20 | -73.828 | 0.100 | -3.626 | 0.999 | -100.391 | -47.656 |
| H1-primary[H1] | exec30|exit_1600 | warsh | C0 | 3 | -41.667 | 0.333 | -0.739 | 0.749 | -106.771 | 23.438 |
| H1-primary[H1] | exec30|exit_1600 | warsh | C2 | 3 | -72.917 | 0.333 | -1.293 | 0.871 | -138.021 | -7.812 |
| H1-primary[H1] | exec30|exit_1600 | warsh | C4 | 3 | -104.167 | 0.000 | -1.847 | 1 | -169.271 | -39.062 |
| H1-primary[H1] | primary|exit_1600 | warsh | C0 | 3 | -36.458 | 0.333 | -0.703 | 0.749 | -96.354 | 23.438 |
| H1-primary[H1] | primary|exit_1600 | warsh | C2 | 3 | -67.708 | 0.333 | -1.305 | 0.871 | -127.604 | -7.812 |
| H1-primary[H1] | primary|exit_1600 | warsh | C4 | 3 | -98.958 | 0.000 | -1.907 | 1 | -158.854 | -39.062 |
| H1-primary[H1] | primary|exit_1630 | warsh | C0 | 3 | -33.854 | 0.333 | -0.529 | 0.745 | -106.771 | 39.062 |
| H1-primary[H1] | primary|exit_1630 | warsh | C2 | 3 | -65.104 | 0.333 | -1.017 | 0.871 | -138.021 | 7.812 |
| H1-primary[H1] | primary|exit_1630 | warsh | C4 | 3 | -96.354 | 0.333 | -1.506 | 0.871 | -169.271 | -23.438 |
| H1-Q[H1Q] | exec30|exit_1600 | 2016-2022 | C0 | 31 | -6.300 | 0.355 | -0.600 | 0.726 | -21.169 | 8.317 |
| H1-Q[H1Q] | exec30|exit_1600 | 2016-2022 | C2 | 31 | -41.583 | 0.194 | -3.870 | 0.999 | -57.460 | -25.706 |
| H1-Q[H1Q] | exec30|exit_1600 | 2016-2022 | C4 | 31 | -76.865 | 0.097 | -6.798 | 1 | -95.262 | -58.720 |
| H1-Q[H1Q] | primary|exit_1600 | 2016-2022 | C0 | 31 | -6.552 | 0.355 | -0.640 | 0.739 | -21.421 | 7.560 |
| H1-Q[H1Q] | primary|exit_1600 | 2016-2022 | C2 | 31 | -41.835 | 0.194 | -4.009 | 0.999 | -57.460 | -26.714 |
| H1-Q[H1Q] | primary|exit_1600 | 2016-2022 | C4 | 31 | -77.117 | 0.097 | -7.034 | 1 | -95.010 | -59.980 |
| H1-Q[H1Q] | primary|exit_1630 | 2016-2022 | C0 | 31 | -10.585 | 0.387 | -0.936 | 0.823 | -28.982 | 6.048 |
| H1-Q[H1Q] | primary|exit_1630 | 2016-2022 | C2 | 31 | -45.867 | 0.194 | -4.061 | 1.000 | -64.768 | -28.478 |
| H1-Q[H1Q] | primary|exit_1630 | 2016-2022 | C4 | 31 | -81.149 | 0.032 | -6.994 | 1 | -101.562 | -62.248 |
| H1-Q[H1Q] | exec30|exit_1600 | confirmation | C0 | 20 | 5.469 | 0.250 | 0.236 | 0.425 | -40.234 | 56.641 |
| H1-Q[H1Q] | exec30|exit_1600 | confirmation | C2 | 20 | -25.781 | 0.200 | -1.112 | 0.864 | -71.484 | 25.391 |
| H1-Q[H1Q] | exec30|exit_1600 | confirmation | C4 | 20 | -57.031 | 0.200 | -2.460 | 0.989 | -102.734 | -5.859 |
| H1-Q[H1Q] | primary|exit_1600 | confirmation | C0 | 20 | 4.688 | 0.300 | 0.204 | 0.435 | -39.062 | 54.688 |
| H1-Q[H1Q] | primary|exit_1600 | confirmation | C2 | 20 | -26.562 | 0.250 | -1.155 | 0.871 | -70.312 | 23.438 |
| H1-Q[H1Q] | primary|exit_1600 | confirmation | C4 | 20 | -57.812 | 0.200 | -2.513 | 0.991 | -101.562 | -7.812 |
| H1-Q[H1Q] | primary|exit_1630 | confirmation | C0 | 20 | -6.641 | 0.350 | -0.324 | 0.640 | -46.094 | 37.891 |
| H1-Q[H1Q] | primary|exit_1630 | confirmation | C2 | 20 | -37.891 | 0.200 | -1.851 | 0.960 | -77.344 | 6.641 |
| H1-Q[H1Q] | primary|exit_1630 | confirmation | C4 | 20 | -69.141 | 0.150 | -3.378 | 0.998 | -108.594 | -24.609 |
| H1-Q[H1Q] | exec30|exit_1600 | warsh | C0 | 3 | -41.667 | 0.333 | -0.739 | 0.749 | -106.771 | 23.438 |
| H1-Q[H1Q] | exec30|exit_1600 | warsh | C2 | 3 | -72.917 | 0.333 | -1.293 | 0.871 | -138.021 | -7.812 |
| H1-Q[H1Q] | exec30|exit_1600 | warsh | C4 | 3 | -104.167 | 0.000 | -1.847 | 1 | -169.271 | -39.062 |
| H1-Q[H1Q] | primary|exit_1600 | warsh | C0 | 3 | -36.458 | 0.333 | -0.703 | 0.749 | -96.354 | 23.438 |
| H1-Q[H1Q] | primary|exit_1600 | warsh | C2 | 3 | -67.708 | 0.333 | -1.305 | 0.871 | -127.604 | -7.812 |
| H1-Q[H1Q] | primary|exit_1600 | warsh | C4 | 3 | -98.958 | 0.000 | -1.907 | 1 | -158.854 | -39.062 |
| H1-Q[H1Q] | primary|exit_1630 | warsh | C0 | 3 | -33.854 | 0.333 | -0.529 | 0.745 | -106.771 | 39.062 |
| H1-Q[H1Q] | primary|exit_1630 | warsh | C2 | 3 | -65.104 | 0.333 | -1.017 | 0.871 | -138.021 | 7.812 |
| H1-Q[H1Q] | primary|exit_1630 | warsh | C4 | 3 | -96.354 | 0.333 | -1.506 | 0.871 | -169.271 | -23.438 |

H1-answer (diagnostic), ZT, gross:

| sample | h | unit | n_answers | n_meetings | mean | t_cr1 | wcb_p_two | mtg_mean | mtg_wb_p_two |
|---|---|---|---|---|---|---|---|---|---|
| 2016-2022 | 1 | usd | 685 | 31 | 0.456 | 0.570 | 0.632 | 0.464 | 0.597 |
| 2016-2022 | 5 | usd | 249 | 31 | 3.389 | 1.469 | 0.156 | 3.732 | 0.133 |
| 2016-2022 | 15 | usd | 100 | 31 | 0.234 | 0.032 | 0.974 | 0.882 | 0.917 |
| confirmation | 1 | ticks | 548 | 20 | -0.135 | -1.253 | 0.234 | -0.144 | 0.226 |
| confirmation | 5 | ticks | 163 | 20 | 0.129 | 0.519 | 0.611 | 0.170 | 0.483 |
| confirmation | 15 | ticks | 62 | 20 | 0.177 | 0.156 | 0.883 | 0.267 | 0.827 |
| warsh | 1 | ticks | 59 | 3 | 0.068 | 0.147 | 0.771 | 0.112 | 0.742 |
| warsh | 5 | ticks | 19 | 3 | 0.474 | 0.292 | 0.669 | 0.543 | 0.742 |
| warsh | 15 | ticks | 8 | 3 | -0.500 | -0.090 | 0.947 | 0.389 | 1 |

Inputs:

- v2 outputs: `<work>\fedspeak_v2\backtest`
- press-conference outputs: `<work>\presser_bt\backtest`
- press-conference text with stance columns: `<work>\presser_bt\text_chrono`
