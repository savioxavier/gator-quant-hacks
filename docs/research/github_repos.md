# Review of minh-stakc public GitHub repos (quant / trading relevance)

Prepared 2026-10-03 for Gator Quant Hacks 2026, Systematic Trading track.
Clones (read-only, public HTTPS) live in the session scratchpad under `scratchpad/gh/<repo>`. I did not modify or push anything.
The repos sign the author as "Nathan Hoang", the same person as Minh Hoang (same email as the vault).

## 0. TL;DR for the competition

1. **physics-quant-research** is the only repo with a real backtest stack worth reusing. Its headline is a 4-ETF (SPY/QQQ/TLT/GLD) equal-weight basket with a per-asset "Ghost Dimension" path-geometry gate and 12% EWMA vol targeting, 2006-2024, 2 bp costs. It reports Sharpe 1.06. The repo's own permutation test (p = 0.38) and ablation show the gate adds almost nothing. Almost all of the Sharpe comes from diversification plus vol targeting.
2. **Why the gate failed** (my diagnosis below, Section 2.4). Both path statistics scale linearly with volatility, so the gate is mostly a vol-spike detector that duplicates the vol targeting. It also treats "unusually smooth" and "unusually rough" the same way, through `max(|z|)`.
3. **A novel, citable extension.** Normalise the swept area by arc length to get a **scale-free bridge-excursion ratio** `R = A / (L * sqrt(W))`. Under a random walk it converges to **pi/8 ≈ 0.393**. It rises with positively autocorrelated (trending) increments and falls with mean-reverting ones. I checked this by simulation (Section 2.5). Fitting it across several window lengths gives a Hurst-type exponent. That makes it a vol-free persistence or regime measure. It could decide, per asset and per day, how much to trust a trend sleeve versus a reversal sleeve. This keeps the user's prior idea, fixes the diagnosed flaw, and gives a falsifiable hypothesis with an economic story (under-reaction or herding produces persistence).
4. **AlgoGators** is UF's student algorithmic-trading organisation ("AlgoGators Investment Fund", tied to the Warrington Quantitative Finance track), not a competition. `algogator-apply` (Sep 2025) was an application/entry project and `algogator-tail-risk` (Mar 2026) was the fund's capstone paper. Lessons: GARCH beat HMM/EVT regime CVaR, regime models only helped in sustained stress, and the regime labels had look-ahead.
5. **Rule gaps in the prior code** that must be fixed before reuse (Section 9):
   - Sharpe is computed on total returns, not excess returns.
   - Leverage financing is ignored (mean gross exposure 1.36x).
   - DSR uses n_trials = 1 despite dozens of variants.
   - There is no once-only OOS, no 2x-cost run, no factor regression and no capacity analysis.
6. **Security.** `algogator-apply` still exposes a hardcoded Copernicus CDS API key in its public git history (`weather_crawl.py`, in the commit before `af2b0f6`). The fix commit only removed it from HEAD. Recommend rotating that key. I did not copy the value anywhere.

## 1. Inventory

The account has 32 public repos (from `api.github.com/users/minh-stakc/repos`). The finance-relevant ones:

| Repo | Lang | Last update | Relevance | Verdict |
|---|---|---|---|---|
| physics-quant-research | Python | 2026-05-22 (1 commit) | Multi-asset systematic strategies, metrics, walk-forward | **High**: reuse the backtester and metrics, extend the path-geometry idea |
| algogator-tail-risk | Python | 2026-03-20 | Regime-conditional CVaR, EVT, copulas, VaR backtests | **Medium**: Risk Management Plan tooling |
| algogator-apply | Python | 2026-03-24 (code Sep 2025) | Corn/wheat futures pairs plus weather/news sentiment | Low: idea only, the backtest is not rule-compliant |
| cb-policy-tracker | Python | 2026-03-20 | LLM hawk/dove scoring of Fed speeches plus Taylor rule | Low to medium: text-signal pipeline, no backtest |
| mev-simulator | Go | 2024-12 commits | Ethereum/Solana MEV heuristics | None for this track (placeholder heuristics, no results) |
| parameter-golf | Python (fork) | 2026-03-22 | Fork of OpenAI's 16 MB LM compression challenge | None (skimmed) |
| subscription-detector / payment-validation / expense-backend | Py / Haskell / TS | 2026-03 | Personal-finance and payments engineering | None (not trading) |

Not finance-related and skipped: ACC-*, app-ielts-*, cuesearch (C++ 9-ball physics), miniml (OCaml), FedLLM-Attack-2, leo-simulator, network-toolkit, distributed-scheduler, signature-gen, the landcover/UNet repos, threejstest, hurricane-relief, resume-tailor, test, vid-dataset, whackamole-lab10.

## 2. physics-quant-research (deep dive)

### 2.1 Idea and scope

The thesis is that physics-flavoured path features can serve as regime gates or sizing signals on liquid ETFs and crypto, evaluated with honest statistics. The repo has about 5,500 lines of Python: about 20 `run_*.py` experiments, `src/` modules, cached data and result CSVs. There is one public commit ("Initial commit", May 2026), so the commit history does not show the order of experiments.

### 2.2 Data

- **Daily data.** yfinance `auto_adjust=True` closes, which are split- and dividend-adjusted. `data/panel.csv` holds GLD, QQQ, SPY, TLT, TMF, TQQQ, UGL, UPRO for 2006-01-03 to 2024-05-30.
- **24-ETF default universe** in `src/data.py`: SPY QQQ IWM MDY, the 9 original sector SPDRs, EFA EEM EWJ, TLT IEF LQD HYG, GLD SLV USO VNQ.
- **Single stocks.** `data/stocks.csv` has 31 *current* mega-caps from 2010. This is survivorship-biased, and the README admits it.
- **Volatility.** `data/vol.csv` has SVXY, VIX and VIX9D from 2011-10.
- **Crypto.** Six coins from 2020-04 to 2024-05.
- **Intraday.** `data/intraday/*_1h_730d.csv` has 1-hour SPY/QQQ/TLT/GLD bars from 2023-06-23 to 2026-05-20 (yfinance 730-day limit).
- **IBKR.** `src/ibkr_loader.py` is an IB Gateway (`ib_insync`) loader. It is not used in any reported result.

### 2.3 Path-geometry ("Ghost Dimension") gate: exact formulas (`src/strategies/ghost_dim.py`)

Notation: x_s = ln P_s for one asset. Leg window W = 20, baseline B = 252.

**Leg.** The W+1 points x_{t-W}, …, x_t. The chord between the endpoints is

c_i = x_{t-W} + (i/W)·(x_t − x_{t-W}), for i = 0..W.

**Swept area** (L1 deviation from the chord, `np.mean` over W+1 points; the endpoints contribute 0):

A_t = (1/(W+1)) · Σ_{i=0..W} | x_{t-W+i} − c_i |

**Arc length** (just the mean absolute daily log return over the leg):

L_t = (1/W) · Σ_{i=1..W} | x_{t-W+i} − x_{t-W+i-1} |

**Trailing z-scores.** The history buffer keeps up to B values including today; today is excluded, so the baseline is at most 251 prior values. At least 30 values are required, otherwise z = 0. The std is the population std (ddof 0).

zA_t = (A_t − mean(A_{t-1..})) / std(A_{t-1..}), and likewise zL_t.

**Regime statistic:** ρ_t = max(|zA_t|, |zL_t|)

**Adaptive threshold.** τ_t = 90th percentile of the prior ρ values (at most 251 of them). At least 60 are required, otherwise the gate is 1.

**Excess and smooth gate:**

e_t = max(0, ρ_t − τ_t) / τ_t
g_t = m + (1 − m) · exp(−e_t² / (2 s²))

Defaults are s = 1.0 and m = 0. The headline `run_best.py` uses **s = 0.5 and m = 0.1**. With those values:
- ρ = 1.5·τ gives g ≈ 0.65.
- ρ = 2·τ gives g ≈ 0.22.

**Portfolio (`run_best.py` with `src/panel_backtest.py`)**

- Raw weights: u_{i,t} = (1/N) · g_{i,t−1}, with N = 4. The gate gets an extra one-day lag. Note that this is **equal weight, not inverse-vol risk parity**, despite the README wording. Inverse-vol weighting only appears in `run_risk_parity_v2.py`.
- Vol targeting: p_t = Σ_i u_{i,t−1}·r_{i,t}; σ̂²_t = EWMA_{halflife 20}(p²); k_t = clip(0.12 / (√252·σ̂_t), 0, 3).
- Applied weights: w_{i,t} = u_{i,t}·k_{t−1} (double-lagged), with 60 warm-up days at zero.
- P&L: R_{t+1} = Σ_i w_{i,t}·r_{i,t+1} − 2 bp · Σ_i |w_{i,t} − w_{i,t−1}|, with the cost booked one bar later.

The signal timing is clean: weights are chosen at the close of t and earn t to t+1, and the gate and vol scale are lagged further still.

**Other physics modules**, none of which made the headline:

- **`tunneling.py`** (WKB transmission). The barrier is the deficit d = max(0, V0 − |E|).
  - E = 0.5·z·|z|, where z = μ20/σ20.
  - V0 = 2·σ20·√252.
  - T = exp(−2·√(2·m·d)·L/ħ), with L = 0.5 and ħ = 1.
  - It is a nonlinear squash of the 20-day t-stat against annualised vol.
- **`atmospheric.py`**:
  - Level = ln(EWMA5|r| / EWMA60|r|).
  - Slope = 5-day change in level.
  - Speed = ‖Δ(level, slope)‖.
  - The gate closes when speed exceeds its trailing 92nd percentile. This is again a vol-acceleration detector.
- **`phase_coherent.py`**: a split-step Schrödinger solver over a log-return grid, with shocks planted as Gaussian packets. The signal is mode × concentration, followed by tanh(z). It is heavily parameterised (about 17 parameters) and not validated.

### 2.4 Reported results, and my audit

I recomputed these from the saved result CSVs (daily, ddof 1, after warm-up):

| Strategy (CSV) | Period | Sharpe | Ann. ret | Vol | MaxDD |
|---|---|---|---|---|---|
| best_equity (headline, gated) | 2006-03 to 2024-05 | 1.07 | 13.3% | 12.4% | −22.2% |
| ↳ train, before 2018-07-27 | | 1.01 | 12.6% | 12.4% | −22.2% |
| ↳ test, after 2018-07-27 | | 1.18 | 14.7% | 12.4% | −21.3% |
| ↳ last 2 years (2022-06 to 2024-05) | | 0.88 | 10.5% | 11.9% | −12.1% |
| ↳ calendar 2022 | | −1.32 | −16.9% cum | 13.4% | −20.0% |
| final_equity (SPY/TLT/GLD) | 2006-2024 | 0.95 | 11.3% | 12.0% | −23.7% |
| alpha_stack (+momentum tilt) | 2006-2024 | 1.06 | 19.8% | 18.6% | −32.1% |
| leveraged_rp (3x ETFs) | 2010-2024 | 1.05 | 21.8% | 20.7% | −36.1% |
| btc_equity (mixed + BTC) | 2014-2024 | 1.45 | 18.4% | 12.7% | −24.3% |
| rp_btc_eth (inverse-vol RP + BTC/ETH) | 2017-2024 | 1.32 | 16.4% | 12.4% | −23.7% |
| crypto_basket (6 coins, 20 bp) | 2020-2024 | 1.27 | 26.8% | 21.1% | −39.7% |
| dualmom (Antonacci rotation) | 2006-2024 | 0.66 | 8.4% | 12.6% | −27.0% |
| vol_carry (SVXY with VIX9D/VIX filter) | 2011-2024 | 0.50 | 7.2% | 14.5% | −44.7% |
| stat_arb (Avellaneda-Lee on 31 survivors) | 2010-2024 | **−0.40** | −4.3% | 10.8% | −51.7% |
| reversal (short-term z, SPY) | 2006-2024 | 0.01 | 0.1% | 13.0% | −38.2% |
| multi (24-ETF panel) | 2006-2024 | 0.13 | 2.1% | 15.9% | −35.9% |
| intraday (1h slow layer) | 2023-06 to 2026-05 | 1.47 | 18.3% | 12.5% | −11.7% |
| intraday_alpha (gap fade + close momentum) | same | 0.96 | 12.0% | 12.5% | −13.0% |

The repo's own diagnostics:

- **Ungated control.** Sharpe 1.009 against 1.059 gated. Permutation p = 0.38, so the gate is not significant.
- **Universe grid** (`riskparity_grid.csv`, 5 universes). The gate adds +0.02 to +0.05 Sharpe in all 5 and trims MaxDD by 1-2 points. That is consistent but tiny.
- **SPY walk-forward** (4-year train, 1-year test, 14 folds, 72-combo grid per fold). Concatenated OOS Sharpe 0.76 against 0.70 for SPY buy-and-hold. Per-fold OOS swings from −0.93 to +2.96, and the chosen parameters change between folds.

**Robustness read**

- **Not a "Sharpe > 3 bug".** About 1.0 is plausible for a vol-targeted stock/bond/gold basket over 2006-2024, which was a bond bull market. It is era-dependent: 2022, when stocks and bonds fell together, cost −17%.
- **Overstated by roughly 0.1 Sharpe.** Sharpe uses *total* returns with no risk-free deduction, and leverage financing is not charged. Mean gross exposure is 1.36x, 79% of days are above 1x, and on average 41% of NAV is borrowed. Excess return ≈ 13.3% − 1.36 × ~1.2% average T-bill rate ≈ 11.7%, so Sharpe is about **0.9-0.95 before any borrow spread**. This is my estimate, not a rerun.
- **OOS not clean.** The 2018-07-27 split is about 70/30. The gate parameters (s = 0.5, m = 0.1, q = 0.9, 12% target) were chosen after about 20 full-sample experiments, so the test set was seen.
- **DSR not deflated.** The headline uses `all_metrics(..., n_trials=1)`, so the Deflated Sharpe equals the plain PSR there. The variants actually tried: at least 20 scripts, plus a 72-combo grid × 14 folds, plus a 10-config universe grid.
- **Permutation design.** It shuffles the *gated gross-exposure* series i.i.d. against *already vol-targeted* ungated returns. That destroys autocorrelation and mixes vol-scaling into the null. A block or circular-shift permutation of only the gate series is the right null.
- **Turnover is low.** About 12x a year, so the cost drag is 0.25% a year at 2 bp. A 2x-cost run would barely move it. That is good for the Liquidity & Capital criterion.

**Why the gate adds nothing (diagnosis)**

1. L_t is literally a 20-day vol estimator (E|r| = σ·√(2/π)). A_t also scales linearly with σ (Section 2.5). Both z-scores therefore mostly track vol changes, which the halflife-20 EWMA vol target already neutralises. The gate is redundant.
2. Taking `max(|zA|, |zL|)` means an *unusually smooth* leg (a strong, quiet trend) can close the gate just like a turbulent one. The *shape* information is discarded.
3. The shape signal is weak at W = 20 for a single asset and a single window (noise numbers below). The gate cannot classify reliably per asset per day.

### 2.5 Proposed novel extension: the scale-free bridge-excursion ratio

Define

**R_t = A_t / (L_t · √W)**

This divides out the volatility scale, leaving pure path *shape*.

**Random-walk value.** Under a Gaussian random walk, the chord-detrended path is a Brownian bridge. Then E|bridge(u)| = σ√W·√(2/π)·√(u(1−u)), and ∫₀¹ √(u(1−u)) du = π/8. With E[L] = σ·√(2/π):

**R → π/8 ≈ 0.3927**

**Monte Carlo check** (20k paths each, my run). The table shows the mean of R and its 10th-90th percentile range:

| Increment process | mean R (W = 20) | p10-p90 |
|---|---|---|
| AR(1) φ = −0.3 (mean-reverting) | 0.299 | 0.17-0.47 |
| AR(1) φ = −0.1 | 0.345 | 0.20-0.54 |
| random walk | 0.371 (W = 60: 0.386, so converging to π/8) | 0.21-0.58 |
| AR(1) φ = +0.1 | 0.397 | 0.22-0.63 |
| AR(1) φ = +0.3 (trending) | 0.456 | 0.25-0.72 |

So R is a vol-free persistence statistic. It is high when increments are positively autocorrelated and the path makes long excursions from its chord. It is low when the path chops around the chord.

**Caveat (important for design).** At W = 20 the per-window dispersion (about ±0.18) dwarfs the shift from φ = ±0.1 (about ±0.03). Any usable version must pool information:
- across windows: an EWMA of R, or several W;
- across assets: the cross-section of 20-40 futures;
- or use longer legs (W = 60-120).

**Multi-scale "geometric Hurst" exponent.** For fractional Brownian motion with Hurst H, A ∝ σ·W^H while L ∝ σ, so **R(W) ∝ W^(H − 1/2)**. Regressing ln R_t(W) on ln W for W ∈ {10, 20, 40, 80, 160} on the same day gives slope = Ĥ − 1/2. Ĥ > 0.5 means persistent and Ĥ < 0.5 means anti-persistent.

**Related literature, which must be cited** (the statistic is kin to these; it is not the same thing):
- Hurst (1951) rescaled range;
- Lo (1991) modified R/S;
- Lo & MacKinlay (1988) variance ratio.

What is new: the chord-detrended path-area construction, its closed-form random-walk benchmark (π/8), the multi-scale slope, and using it to *condition* strategy sleeves rather than gate exposure.

**Optional extras from the same geometry**

- **Signed area** S_t = (1/(W+1))·Σ(x − c). This is a curvature or acceleration measure: concave (run-up then stall) versus convex (accelerating).
- **Two-asset Lévy area** ½∮(X dY − Y dX) of normalised paths. This is the signature-method lead-lag measure (Lyons rough paths; Chevyrev & Kormilitzin 2016 primer). It is a candidate cross-asset lead-lag signal.

**Candidate competition strategy** (a sketch; the main agent decides). Persistence-conditioned time-series momentum on liquid futures:

1. **Base sleeve.** Vol-scaled TSMOM per market (Moskowitz, Ooi & Pedersen 2012): sign of the blended 1/3/12-month excess return, inverse-vol sized, 10% portfolio vol target.
2. **Conditioning.** Trend weight multiplier m(P_{i,t}) = clip(1 + κ·P_{i,t}, 0, 2), where P is a lagged, smoothed z of Ĥ (or ln R) for that market. Low-persistence states can optionally go to a short-horizon reversal sleeve. Fix W, κ and the smoothing a priori and do not tune them.
3. **Pre-registered hypothesis (falsifiable).** Pooled across markets, TSMOM's next-month vol-adjusted return is higher in top-tercile persistence states than in bottom-tercile ones. R is vol-free by construction, so this is not a vol-timing effect in disguise.
4. **Headline test = the increment over plain TSMOM.** Use a block-bootstrap CI of the Sharpe difference and a circular-shift permutation of the conditioning series. This avoids repeating the p = 0.38 outcome without a proper test.
5. **Economic story.** Under-reaction and gradual information diffusion (Hong & Stein 1999), herding and slow-moving capital produce persistent increments. Path geometry measures when that persistence is present.
6. **Data.**
   - Databento CME Globex daily bars, continuous contracts with an explicit roll rule (confirm schema and symbology with the data agent).
   - Fallback: liquid ETF proxies (SPY, QQQ, IWM, EFA, EEM, TLT, IEF, GLD, SLV, USO, UNG, DBC, UUP, FXE, FXY) via a cited free source.
   - Ken French data for the factor regression (Mkt-RF, HML, UMD) and FRED T-bills for excess returns.

### 2.6 Reusable code (copy with attribution to the prior repo)

- **`src/panel_backtest.py`**: weights at close t applied to t→t+1, turnover costs, EWMA portfolio vol targeting with double lag. Add financing and excess returns, a 2x-cost switch and capacity hooks.
- **`src/metrics.py`**: Sharpe, Sortino, Calmar, MaxDD, Bailey-López de Prado DSR with skew/kurtosis and the expected-max-SR formula. Pass the real `n_trials`.
- **`run_best.py`**: `bootstrap_sharpe_ci` (stationary bootstrap, mean block 5, 3,000 draws) and `permutation_test`. Switch the latter to a block or circular-shift null.
- **`src/walkforward.py`**: rolling train/test harness with a robustified-Sharpe objective. Useful only *inside* the 80% development window.
- **`src/strategies/ghost_dim.py`**: streaming A_t and L_t. R_t is a one-line addition.
- **`src/strategies/vol_target.py` and `trend.py`** (ATR-band trend) as baselines.

## 3. algogator-tail-risk (AlgoGators capstone, March 2026)

- **Question.** Do regime-aware CVaR models (HMM and PELT regimes, then EVT/GPD tails per regime, plus copula dependence) beat static, rolling and GARCH CVaR?
- **Data.** yfinance, 2005-2024: SPY plus 9 sector SPDRs, equal-weight portfolio; VIX as an HMM feature. Train ≤ 2017, test 2018-2024 (1,760 days, 5% tail).
- **Results.**
  - GARCH(1,1) is best: 3.58% violations against 5% expected, MAE 0.0205.
  - Regime-EVT: 3.24%, MAE 0.0282.
  - **All five models reject Kupiec.** They are too conservative, with too few violations.
  - In 2022 (sustained stress), Regime-EVT had 0.40% violations against 3.59% for GARCH.
  - In COVID 2020 (sudden shock), Regime-EVT had 28.85% against 11.54% for GARCH.
  - High-vol regime CVaR is about 2.8x low-vol CVaR; GPD ξ = +0.116 against −0.073.
- **Audit.**
  - The 2-state HMM (and its `StandardScaler`) is **fit on the full 2005-2024 sample**, and the Viterbi (smoothed) labels feed the walk-forward. That is regime-label look-ahead.
  - The regime CVaR is held fixed for **63-day blocks** using the label at the forecast origin. That, more than "HMM lag", explains the COVID failure.
  - The paper itself flags full-sample PELT as look-ahead and proposes BOCPD.
- **Reusable for the Risk Management Plan.**
  - `src/evaluation.py`: Kupiec POF, Christoffersen conditional coverage, Diebold-Mariano, stress-period violation tables. Use these to backtest the *strategy's own* VaR/CVaR limits, which is a nice differentiator.
  - `src/risk_models.py`: GARCH, EVT/GPD and historical CVaR.
  - `src/copula_models.py`: Student-t and Clayton tail dependence, copula-simulated portfolio CVaR. This shows correlations spike in stress.

## 4. algogator-apply (AlgoGators application project, Sep 2025)

- **Strategy.** CBOT corn/wheat pairs.
  - Rolling 60-day OLS hedge ratio of ln(corn) on ln(wheat).
  - Spread z-score over 252 days; enter at |z| > z_entry, exit on a z rule or a holding cap.
  - Filter: a Weather Risk Index, WRI = (corn T z − corn P z + wheat T z − wheat P z − news sentiment z)/5, lagged one day, must be below a percentile threshold.
- **Data.**
  - yfinance `ZC=F` and `ZW=F` (front-month continuous, unadjusted roll gaps).
  - ERA5-Land reanalysis via the Copernicus CDS API (2 m temperature and precipitation over Corn Belt and wheat-belt boxes).
  - GDELT DOC API headlines (`gdeltdoc`, keywords like drought, frost, harvest), scored with FinBERT (`ProsusAI/finbert`).
- **Results.** It prints a 108-variant grid (3 × 3 × 3 × 4) sorted by Sharpe. There is no OOS and no costs.
- **Audit: not robust.**
  - Weather z-scores use `rolling(center=True)`, a ±15-day future leak.
  - The sentiment z and the WRI percentile threshold use full-sample statistics.
  - P&L is computed on spread differences while the hedge ratio changes daily, so it is not a tradable P&L.
  - Entry happens at the same close the signal is observed.
  - P&L is in log-spread units with no sizing; roll gaps are untreated; the best of 108 is chosen in-sample.
- **Reusable.** The ERA5 + GDELT + FinBERT ingestion pattern, and the idea of fundamental weather data as a commodity signal. Weather data could be a genuinely orthogonal input, but it needs vintage-correct timing (ERA5T has about a 5-day lag).
- **Security.** The pre-`af2b0f6` history contains a hardcoded CDS key in `weather_crawl.py`. Rotate it on the Copernicus account. HEAD now reads the `CDS_API_KEY` environment variable.

## 5. cb-policy-tracker

- **Idea.** Scrape Fed Board speeches from federalreserve.gov. <assistant> Haiku 4.5 (`<assistant>-haiku-4-5-20251001`) scores each speech −2 to +2 on overall, inflation, employment, growth and financial-stability stance as structured JSON. The tool tracks the 3-month consensus and flags members deviating more than 0.5 over 180 days. A Taylor (1993) rule gap is computed from FRED's keyless `fredgraph.csv` endpoint. Streamlit dashboard.
- **Results** (2021-2023, about 40 speeches a year). The consensus jumped from +0.25 (Q4 2021) to +1.20 (Q1 2022), ahead of the March 2022 hike. Waller was flagged as the hawkish deviant in Oct-Nov 2021.
- **Audit.**
  - **LLM knowledge leakage.** The scoring model's training data post-dates the 2022 hiking cycle, so "early detection" is look-ahead-contaminated.
  - It is one episode with a small sample and no tradable backtest (no rates or futures P&L).
  - Bug: on the live FRED path, `PCEPILFE` is used as an index *level*, not YoY %, in the Taylor rule. Only the bundled fallback CSV has YoY values.
  - The FRED CSV header name may also have changed (`DATE` versus `observation_date`); verify before reusing.
- **Reusable.**
  - The keyless FRED CSV fetcher, which is handy for T-bills, credit spreads and the 2s10s spread.
  - The structured-JSON LLM scoring pattern. It could be swapped to Gemini if the team wants the MLH Gemini prize, or pointed at 8-K text for the Massive bonus. For the Massive "Trade the 8-K" challenge, prefer the structured 8-K **item codes** (1.01, 2.02, 5.02, …) over LLM scores, to avoid the same leakage.

## 6. mev-simulator (Go)

An Ethereum/Solana RPC client plus "arbitrage, sandwich, liquidation" detectors. The logic is placeholder heuristics. For example, arbitrage profit is computed as max minus min `tx.Value` within a token-pair group, and the comments say real pool-reserve decoding would be done "in production". There is no data and there are no results. Not usable for the systematic track. At most it is tangential to the Solana / quant-puzzles MLH prize.

## 7. parameter-golf (skimmed)

A fork of OpenAI's "Parameter Golf" challenge (the best LM under 16 MB, trained in 10 minutes on 8×H100, scored in bits per byte on FineWeb). No finance content. It is only relevant as evidence of ML-systems skill.

## 8. What AlgoGators is, and what was learned

**What it is.** AlgoGators is UF's student algorithmic-trading organisation. It brands itself the "AlgoGators Investment Fund" and is linked to Warrington's Quantitative Finance track. Activities listed: algorithmic strategy workshops, quant analysis competitions, Python tools training and simulated trading. It is **not** a hackathon. The user's two repos are:
- an entry/application project (corn-wheat sentiment pairs, Sep 2025);
- the fund's capstone research paper on regime-conditional tail risk (Mar 2026, written in the AlgoGators PDF template by `generate_pdf.py`).

**Lessons carried forward**

1. Simple conditional-vol models (GARCH or EWMA) are hard to beat for risk forecasting. Use them for sizing, and use regime/EVT for stress budgets and limits.
2. Regime detection must be filtered or online (forward probabilities, BOCPD). Full-sample HMM/PELT labels leak.
3. Re-estimation frequency matters. Quarterly updates fail in sudden shocks, so update daily.
4. Diversification fails in stress because correlations rise. Plan for that in the Risk Management section, for example with a 2022-style stock-bond joint drawdown scenario.
5. Grid searches without OOS and without costs, plus centred or full-sample normalisation, are the main sources of fake edge in the user's earliest work. The later physics repo fixed most of this but still lacks deflation by the true trial count, excess returns and financing.

## 9. Mapping prior code to the GQH rules: what must change

| GQH rule | Prior state (physics repo) | Action |
|---|---|---|
| Hypothesis committed before backtests | None (single dump commit) | Commit `HYPOTHESIS.md` first, with a timestamped git commit |
| OOS = last 2 years (shorter than 20% for long histories), evaluated once | 70/30 split, seen | Hold out about Oct 2024 to Oct 2026 and touch it once at the end |
| Net of costs, state bps, show 2x | 2 bp only | Cost per instrument plus a 2x run (turnover is low, so it should be robust) |
| Deflated Sharpe with variant count | n_trials = 1 | Log every variant to a trials file and feed the count to the DSR |
| Lag every signal | Done (extra lags) | Keep |
| Sharpe > 3 = bug | Not an issue | Keep a sanity assert |
| Factor regression (market, value, momentum) | Missing | Ken French Mkt-RF, HML, UMD (daily); report alpha t-stat |
| Capacity via square-root impact | Missing | Impact = c·σ·√(Q/ADV) per market; find the AUM where net Sharpe halves |
| Survivorship and corporate actions | Adjusted ETFs fine; stock panel survivor-biased | Use futures or ETFs; avoid current-constituent stock lists |
| Excess returns and financing | Total returns, no financing | Use futures excess returns, or subtract T-bill × exposure |
| Code reproduces note numbers | Scripts exist, data cached to 2024-05 | One `make`-style entry point writes every table and figure |

## Sources

- GitHub API repo list: https://api.github.com/users/minh-stakc/repos?per_page=100
- Repos: https://github.com/minh-stakc/physics-quant-research, https://github.com/minh-stakc/algogator-tail-risk, https://github.com/minh-stakc/algogator-apply, https://github.com/minh-stakc/cb-policy-tracker, https://github.com/minh-stakc/mev-simulator, https://github.com/minh-stakc/parameter-golf
- AlgoGators description: [UF Warrington, Quantitative Finance track](https://warrington.ufl.edu/finance-insurance-and-real-estate-department/finance-professional-development/quantitative-finance/)
- Literature to cite if the extension is used:
  - Hurst (1951), Trans. ASCE;
  - Lo (1991), Econometrica, "Long-term memory in stock market prices";
  - Lo & MacKinlay (1988), RFS, variance ratio;
  - Moskowitz, Ooi & Pedersen (2012), JFE, time-series momentum;
  - Hong & Stein (1999), JF;
  - Bailey & López de Prado (2014), Deflated Sharpe Ratio;
  - Chevyrev & Kormilitzin (2016), "A primer on the signature method in machine learning".
