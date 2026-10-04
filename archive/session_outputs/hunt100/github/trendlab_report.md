# TrendLab: pre-registered test of diversified ETF trend following

_Generated 2026-07-16 23:13. All numbers NET of 5bps one-way costs. No parameter was tuned on this data: the spec is fixed ex ante from Moskowitz-Ooi-Pedersen (JFE 2012), Faber (JWM 2007), Jegadeesh-Titman (JF 1993) and Antonacci (2014), citations inline in config.py. Everything after 2013 is out-of-sample by construction; a chronological holdout is tested on top of that._

## Strategy

Each month-end, for 10 asset-class ETFs: hold the sleeve if its trailing 12-month return (skipping the last 1 month) exceeds T-bills, else hold T-bills. Inverse-volatility risk budgets, capped at 25%/sleeve, no leverage, no shorting. Orders execute at the next day's close.


## Data

| ticker | asset_class | from | days |
|---|---|---|---|
| SPY | US equities | 1993-01-29 | 8416 |
| EFA | Intl developed equities | 2001-08-27 | 6251 |
| EEM | Emerging-mkt equities | 2003-04-14 | 5845 |
| IEF | US 7-10y Treasuries | 2002-07-30 | 6023 |
| TLT | US 20y+ Treasuries | 2002-07-30 | 6023 |
| LQD | IG corporate credit | 2002-07-30 | 6023 |
| HYG | High-yield credit | 2007-04-11 | 4841 |
| GLD | Gold | 2004-11-18 | 5441 |
| DBC | Broad commodities | 2006-02-06 | 5136 |
| VNQ | US REITs | 2004-09-29 | 5477 |


## Headline results (net of costs)

**Strategy: full period** (22.9y) | CAGR **+5.5%** | excess over T-bills +3.7%/yr | vol +5.4% | Sharpe **0.70** | maxDD **-16.2%** | Calmar 0.34 | +months 69% | avg exposure 0.67 | cost drag +0.11%/yr

**Strategy: holdout OOS (2018-06-28+)** (8.0y) | CAGR **+4.7%** | excess over T-bills +1.8%/yr | vol +5.7% | Sharpe **0.35** | maxDD **-16.2%** | Calmar 0.29 | +months 66% | avg exposure 0.59 | cost drag +0.11%/yr

**Strategy: post-publication (2013+)** (13.5y) | CAGR **+3.8%** | excess over T-bills +1.9%/yr | vol +5.1% | Sharpe **0.39** | maxDD **-16.2%** | Calmar 0.23 | +months 66% | avg exposure 0.63 | cost drag +0.11%/yr


Benchmarks over the same period:

**SPY buy-and-hold** (22.9y) | CAGR **+11.2%** | excess over T-bills +9.3%/yr | vol +18.6% | Sharpe **0.57** | maxDD **-55.2%** | Calmar 0.20 | +months 67% | avg exposure 1 | cost drag +0.00%/yr

**60/40 SPY/IEF** (22.9y) | CAGR **+8.6%** | excess over T-bills +6.7%/yr | vol +10.7% | Sharpe **0.66** | maxDD **-31.4%** | Calmar 0.28 | +months 69% | avg exposure 1 | cost drag +0.00%/yr

**static always-in** (22.9y) | CAGR **+6.5%** | excess over T-bills +4.6%/yr | vol +7.6% | Sharpe **0.63** | maxDD **-22.7%** | Calmar 0.28 | +months 65% | avg exposure 0.99 | cost drag +0.05%/yr

**static exposure-matched** (22.9y) | CAGR **+5.0%** | excess over T-bills +3.1%/yr | vol +5.1% | Sharpe **0.63** | maxDD **-15.7%** | Calmar 0.32 | +months 68% | avg exposure 0.67 | cost drag +0.03%/yr


## Crisis windows (the reason this premium exists)

| window | strategy | SPY buy-and-hold | 60/40 SPY/IEF | static always-in | static exposure-matched |
|---|---|---|---|---|---|
| GFC (Oct07-Mar09) | 0.069 | -0.460 | -0.225 | -0.065 | -0.034 |
| Covid crash (Feb-Mar20) | -0.076 | -0.232 | -0.112 | -0.090 | -0.060 |
| 2022 stock+bond bear | -0.032 | -0.182 | -0.164 | -0.144 | -0.092 |
| 2020 recovery (Apr-Dec20) | 0.068 | 0.469 | 0.264 | 0.163 | 0.108 |


## Gate scoreboard

- **PASS**: G1 positive out-of-sample: holdout (2018-06-28+): excess +1.8%/yr, Sharpe 0.35; post-publication (2013+): excess +1.9%/yr, Sharpe 0.39
- **FAIL**: G2 timing beats null & static: vs 1000 circular-shift nulls, post-publication (gated): p=0.443 (strategy +1.9%/yr vs null +1.8%/yr); full-sample p=0.096, holdout p=0.532; Sharpe 0.70 vs exposure-matched static 0.63
- **PASS**: G3 robust to parameter tweaks: 100% of 15 variants positive full-sample (100% OOS); no parameter was tuned, so this measures sensitivity only
- **PASS**: G4 breadth across sleeves & years: timing value positive on 6/10 sleeves; 19/24 calendar years with positive excess
- **PASS**: G5 real sample size: 98 OOS months (floor 60); 22.9y total across 10 sleeves
- **PASS**: G6 Monte Carlo CI: daily-block bootstrap, 95% CI on annualized excess [+1.7%, +5.4%]; P(excess≤0)=0.000; Sharpe CI [0.33, 1.06]; maxDD median -16.2%, bad-tail -19.1%; post-2013 CI [-0.1%, +3.9%]

## Gate 2: timing null detail

Circular-shift null preserves each sleeve's exposure fraction, switch frequency, sizing and costs, destroying only WHEN the sleeve is held. Strategy +3.7%/yr vs null mean +3.0%/yr (95th pct +3.9%); p_full=0.096, p_oos=0.532.


## Gate 3: robustness (sensitivity, not selection)

| variant | sharpe | ann_excess | max_dd | oos_ann_excess | oos_sharpe |
|---|---|---|---|---|---|
| PRE-REGISTERED (base) | 0.700 | 0.037 | -0.162 | 0.018 | 0.348 |
| lookback_months=6 | 0.568 | 0.030 | -0.167 | 0.015 | 0.287 |
| lookback_months=9 | 0.683 | 0.036 | -0.162 | 0.028 | 0.511 |
| lookback_months=15 | 0.697 | 0.037 | -0.158 | 0.024 | 0.443 |
| vol_lookback_days=30 | 0.686 | 0.036 | -0.154 | 0.018 | 0.352 |
| vol_lookback_days=90 | 0.693 | 0.037 | -0.164 | 0.018 | 0.339 |
| hurdle=zero | 0.682 | 0.037 | -0.162 | 0.023 | 0.398 |
| signal=sma | 0.671 | 0.034 | -0.104 | 0.013 | 0.282 |
| max_weight=0.2 | 0.698 | 0.036 | -0.160 | 0.019 | 0.354 |
| max_weight=0.3 | 0.698 | 0.037 | -0.162 | 0.018 | 0.342 |
| execution_lag_days=2 | 0.697 | 0.037 | -0.163 | 0.020 | 0.376 |
| rebalance +5d | 0.707 | 0.037 | -0.171 | 0.019 | 0.363 |
| rebalance +10d | 0.633 | 0.034 | -0.171 | 0.018 | 0.330 |
| rebalance +15d | 0.629 | 0.033 | -0.167 | 0.014 | 0.265 |
| costs x3 | 0.660 | 0.035 | -0.162 | 0.016 | 0.310 |
| costs x5 | 0.621 | 0.032 | -0.162 | 0.014 | 0.272 |


## Gate 4: per-sleeve timing value

| sleeve | months_live | exposure | trend_ann_excess | static_ann_excess | timing_value | trend_max_dd | static_max_dd |
|---|---|---|---|---|---|---|---|
| SPY | 277 | 0.840 | 0.092 | 0.080 | 0.012 | -0.337 | -0.482 |
| EFA | 277 | 0.670 | 0.033 | 0.043 | -0.010 | -0.395 | -0.447 |
| EEM | 268 | 0.650 | 0.045 | 0.050 | -0.004 | -0.407 | -0.480 |
| IEF | 277 | 0.570 | 0.018 | 0.010 | 0.008 | -0.104 | -0.130 |
| TLT | 277 | 0.570 | -0.003 | 0.012 | -0.015 | -0.328 | -0.285 |
| LQD | 277 | 0.650 | 0.022 | 0.017 | 0.005 | -0.218 | -0.166 |
| HYG | 220 | 0.760 | 0.031 | 0.027 | 0.003 | -0.220 | -0.267 |
| GLD | 249 | 0.670 | 0.070 | 0.059 | 0.011 | -0.294 | -0.322 |
| DBC | 234 | 0.490 | 0.007 | 0.005 | 0.002 | -0.624 | -0.462 |
| VNQ | 251 | 0.650 | 0.040 | 0.042 | -0.002 | -0.424 | -0.531 |


Per-year:

| year | return | excess | max_dd | exposure |
|---|---|---|---|---|
| 2003 | 0.105 | 0.100 | -0.012 | 0.849 |
| 2004 | 0.083 | 0.067 | -0.071 | 0.886 |
| 2005 | 0.058 | 0.025 | -0.036 | 0.835 |
| 2006 | 0.102 | 0.050 | -0.041 | 0.428 |
| 2007 | 0.104 | 0.056 | -0.033 | 0.641 |
| 2008 | 0.050 | 0.035 | -0.059 | 0.597 |
| 2009 | 0.033 | 0.032 | -0.050 | 0.552 |
| 2010 | 0.115 | 0.113 | -0.048 | 0.856 |
| 2011 | 0.047 | 0.046 | -0.063 | 0.933 |
| 2012 | 0.073 | 0.072 | -0.017 | 0.848 |
| 2013 | 0.029 | 0.028 | -0.074 | 0.683 |
| 2014 | 0.036 | 0.035 | -0.025 | 0.675 |
| 2015 | 0.009 | 0.008 | -0.045 | 0.673 |
| 2016 | -0.005 | -0.008 | -0.060 | 0.644 |
| 2017 | 0.086 | 0.075 | -0.016 | 0.707 |
| 2018 | -0.029 | -0.048 | -0.047 | 0.568 |
| 2019 | 0.113 | 0.090 | -0.019 | 0.697 |
| 2020 | 0.003 | -0.000 | -0.162 | 0.787 |
| 2021 | 0.034 | 0.034 | -0.035 | 0.737 |
| 2022 | -0.032 | -0.052 | -0.053 | 0.245 |
| 2023 | 0.049 | -0.004 | -0.032 | 0.262 |
| 2024 | 0.065 | 0.011 | -0.031 | 0.642 |
| 2025 | 0.115 | 0.070 | -0.047 | 0.674 |
| 2026 | 0.046 | 0.026 | -0.030 | 0.894 |


## Interpretation: what the gates actually say

- **The diversified portfolio premium is real.** Net excess return +3.7%/yr with a bootstrap CI that excludes zero (G6), positive out-of-sample and post-publication (G1), positive in 100% of parameter perturbations including 5x costs (G3). Nobody needed a secret signal for this part: it is multi-asset diversification plus inverse-vol sizing, harvesting ordinary risk premia.

- **The trend-timing overlay is the marginal part.** Against 1000 random-timing clones (same exposure, same sizing, same costs): post-publication p=0.443 (the gated, uncontaminated test) with full-sample p=0.096 and holdout p=0.532. Sharpe edge over the exposure-matched static portfolio: 0.70 vs 0.63. This is precisely the published critique of time-series momentum (Huang, Li, Wang & Zhou, JFE 2020) reproducing in our own data.

- **Where the timing DOES earn its keep is the tails**: through the GFC the strategy returned +6.9% while SPY lost -46.0%; 2022 was -3.2% vs -16.4% for 60/40. The price is lagging every V-shaped recovery (see 2020). Trend is honestly described as a drawdown hedge with roughly break-even expected cost, not a return enhancer.

- **Verdict rule applied mechanically, and hardened after review**: an adversarial code review moved G2's gated statistic from the full-sample p-value to the post-publication one (the pre-2013 window is the literature's own discovery sample), a strictly tougher test. Gates are never relaxed after seeing data; tightening them is fair game.


## Verdict

**VERDICT: 5/6 gates, does NOT clear the pre-registered six-gate bar.** Failed: G2 timing beats null & static. The gates that passed establish a real, robust, modest premium; the gate that failed marks the specific claim this sample cannot prove at 95% confidence. See the interpretation section, and report the numbers as they are, because moving the bar after seeing the data is how fake edges get published.


## Honest limitations

- Universe chosen at asset-class level today (mild survivorship: asset classes don't delist, but a 2003 investor might have picked different wrappers).
- Weights are reset monthly and held constant between rebalances (intra-month drift ignored; bps-level effect).
- Taxable accounts add ~1%/yr drag versus these numbers (monthly signal flips are short-term gains). Use an IRA.
- The strategy's real-world failure mode is behavioral: it lagged buy-and-hold equities for most of 2010-2019 and will again. The premium is compensation for enduring that.
- Yahoo adjusted closes embed dividend reinvestment without taxes or frictions on the reinvestment itself (standard, slightly generous to ALL variants and benchmarks equally).
