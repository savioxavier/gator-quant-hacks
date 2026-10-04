# risk_premia: risk-managed passive premia on CME futures (pre-registered spec)

Written 2026-10-03 BEFORE any backtest of these rules was run. Nothing below may be changed after results are
seen; every variant listed here is computed and reported (CSV), none is dropped.

## 1. Literature basis (rule source and its sample)

| Element | Source | Sample in the source | What the source claims |
|---|---|---|---|
| Equity premium, long ES | Dimson, Marsh & Staunton (2002, yearbooks to 2024); Fama & French (1993) market factor | 1900-2024 (DMS); 1926- (FF) | US equity excess return about 5-7 %/yr, Sharpe about 0.4 |
| Term premium, long 10-year Treasuries | Ilmanen (2011) *Expected Returns*; Asness, Frazzini & Pedersen (2012) | 1926-2010 | Treasury excess return positive, Sharpe 0.2-0.5, inflated by the 1981-2020 yield decline |
| Gold | Erb & Harvey (2013) "The Golden Dilemma" FAJ | 1975-2012 | No reliable long-run premium; diversifier only (expect a weak or zero premium) |
| Stock/bond risk parity | Asness, Frazzini & Pedersen (2012) "Leverage Aversion and Risk Parity" FAJ | 1926-2010 | Equal-risk stocks/bonds levered to target vol beats 60/40 on Sharpe (about 0.5 vs 0.35, US) |
| Constant-vol targeting | Harvey, Hoyle, Korgaonkar, Rattray, Sargaison & Van Hemert (2018) "The Impact of Volatility Targeting" JPM; Moskowitz, Ooi & Pedersen (2012) estimator (EWMA com 60) | 1926-2017 (60+ assets) | Raises Sharpe for equities/credit (leverage effect), about neutral for bonds/FX/commodities; cuts left tail and vol-of-vol everywhere |
| Volatility-managed (1/variance) | Moreira & Muir (2017) "Volatility-Managed Portfolios" JF | 1926-2015 (market factor) | f_sigma,t = (c / RV_{t-1}) f_t, RV = realized variance of daily returns in the previous month, monthly rebalance; market alpha about 4.9 %/yr, Sharpe up; robust to a 1.5x leverage cap. Counter-evidence: Cederburg, O'Doherty, Wang & Yan (2020) JFE (real-time market 0.42 managed vs 0.46 unmanaged), Liu, Tang & Zhou (2019) |
| 10-month long/flat filter | Faber (2007) "A Quantitative Approach to Tactical Asset Allocation" JWM; 2013 update | 1901/1973-2012 | Similar return, much lower drawdown; our GTAA study: drawdown about 60 % of buy-and-hold at matched vol, Sharpe gain about +0.1, not significant |

Publication split: Moreira & Muir circulated 2016, published 2017; Harvey et al. 2018. In-sample sub-periods are
therefore reported as A = start..2016-12-30 and B = 2017-01-03..2024-10-02 (pre/post the vol-management papers).
Faber (2007) and AFP (2012) predate the whole futures sample, so every futures date is post-publication for them.

## 2. Data and windows

* Futures: `futures_daily.parquet` F_ES, F_ZN, F_GC (fully collateralised total-return index; excess return =
  daily index return minus the daily T-bill `rf_daily`). Loaded with `engine.load_ohlc(..., "FWD")`.
* Bond sleeve choice (fixed now): **long F_ZN alone** (10-year note, the most liquid Treasury future and the
  standard "bond" leg in the risk-parity literature). The ZF/ZN/ZB basket is NOT run.
* Eligibility as in forward2: >= 300 sessions of history, finite positive EWMA vol, traded in the last 10 sessions.
* In-sample (IS): first return day of the strategies (the first month-end with 300 sessions of all three
  contracts, plus the next_close lag; expected September 2011) through 2024-10-02. Later window 2024-10-03 ..
  2026-10-02 is descriptive only and is never used to choose anything.
* Point-in-time: decision at month-end close d uses data up to d only; fills at the next session's close
  (`exec="next_close"`, held from close d+1); the engine trades back to the targets every session (drift costs
  included). A check reruns everything with period "IS" and requires the IS slice to match the "FWD" run.

## 3. Costs (realistic map, one-way bp of notional traded; a roll day charges one extra round trip)

F_ES 0.75 bp, F_ZN 1.0 bp, F_GC 1.5 bp (midpoints of the realistic ranges: ES/NQ/YM 0.5-1, ZN 0.7-1.4,
CL/GC/SI/HG 1-2). Stress = 2x (1.5 / 2.0 / 3.0 bp). Gross = 0.

## 4. Sleeves and overlays (all monthly decisions)

Volatility estimators (daily excess returns r, data up to d):
* `ewma`: sigma_E = sqrt(252 * EWMA(r^2, com 60, min 60 obs)).
* `lr` (long run): sigma_L = sqrt(252 * mean(r^2 over the trailing 2520 sessions, min 252)).
* `blend`: sigma_B = 0.7 * sigma_E + 0.3 * sigma_L.
* `rv` (Moreira-Muir): RV = 252 * mean(r^2 over the sessions of the month ending at d) (annualised realized variance).

Target 10 % annualised; gross notional cap 4 (sum |w|) on every sleeve.

Sleeves: ES, ZN, GC (single asset) and SB = stock/bond risk parity (ES + ZN, equal risk).

Overlays:
* `STATIC` (the unmanaged comparator, as in Moreira-Muir): single w = 0.10 / sigma_L. SB: b_i = 1/sigma_L,i,
  scaled so that sqrt(b' S_L b) = 10 %, S_L = trailing 2520-session (min 252) second-moment matrix x 252.
* `CV` (constant-vol target, estimator ewma) and `CVB` (estimator blend): single w = 0.10 / sigma.
  SB: b_i = 1/sigma_i, scaled to 10 % with S = D R D, D = diag(sigma_i), R = trailing 252-session correlation.
* `MM` (Moreira-Muir): single w = 0.10 * sigma_L / RV, capped at 1.5 x (0.10 / sigma_L) (the paper's 1.5
  leverage constraint relative to the unmanaged weight). SB: u = STATIC SB weights (10 % long-run vol);
  multiplier k = 0.10^2 / RV_u, RV_u = 252 * mean((u . r)^2) over the month's sessions with the current u;
  k capped at 1.5. The paper's full-sample constant c is replaced by the trailing sigma_L (point-in-time).
* `FB` (Faber filter on CV) and `FBB` (on CVB): each asset's CV/CVB weight times 1{month-end close > mean of
  the last 10 month-end closes incl. d}, closes = the total-return index; flat leg earns T-bill; SB legs are
  filtered separately and the surviving leg is NOT re-levered.

Variant count: 4 sleeves x 6 overlays (STATIC, CV, CVB, MM, FB, FBB) = 24 futures variants. Primary estimator
for CV and FB is `ewma` (fixed now); CVB/FBB are reported as robustness, never chosen on results.

## 5. Long-history proxy check (descriptive, same rules, proxy data)

Equity = Ken French daily market (Mkt-RF) 1926-07..2026-08 (file from the earlier GTAA study,
`gtaa_study/long_history/data/daily_us_eq.parquet`); bond = constant-maturity 10-year par bond rebuilt from
FRED DGS10, 1962..2026-10 (`daily_us_10y.parquet`). Cash = rf_daily. Overlays STATIC, CV, MM, FB on EQ, BOND
and SB = 12 variants. Costs as ES/ZN with a quarterly roll charge. IS = through 2024-10-02. Splits: EQ
1927-2015 (Moreira-Muir sample) vs 2016-2024; all three by decade. Not tradeable history; it shows whether the
futures-sample numbers are typical.

Total variants computed: 36.

## 6. Statistics (IS and later window, net 1x unless stated)

Net Sharpe 1x and 2x, gross Sharpe (daily excess over T-bill, x sqrt 252), annual return (compound total
net) and mean excess, vol, max drawdown of the total net return, worst calendar year and % positive full
calendar years (excess), 2022, rolling 504-session Sharpe 10/50/90th percentiles, turnover per year, daily
correlation with ES excess return, with forward2 S1 trend and with forward F2, sub-periods A/B, Newey-West t of
the mean daily excess return. Paired circular block bootstrap (block 63 sessions, 5000 draws) of Sharpe
differences: CV vs STATIC, MM vs STATIC, MM vs CV, FB vs CV, CVB vs CV per sleeve; SB vs ES and SB vs ZN.

## 7. Verdict rule (fixed now)

* `real_edge`: IS net-1x NW t >= 2.0, IS net-2x Sharpe > 0, positive Sharpe in both IS sub-periods A and B,
  >= 60 % positive full calendar years, AND the long-history proxy (where one exists) has Sharpe > 0.2 over
  its full IS span.
* `fails`: IS net-1x Sharpe <= 0.1 or NW t < 1.0.
* `weak_or_uncertain`: everything else.
* An overlay "adds value" only if its bootstrap Sharpe difference vs its base has p < 0.05, or (for
  drawdown control) it cuts IS max drawdown by >= 25 % while costing <= 0.1 Sharpe.
