# hunt100 / kaggle - source notes (2026-10-03)

Method: WebSearch budget for the session was already exhausted when this label started, so material was
gathered by browsing kaggle.com pages directly (competition overview, leaderboard, writeups, discussions,
notebook output iframes fetched with curl), the Hugging Face dataset API, Hull Tactical's public site, and
yfinance for one live-record check. SSRN abstract pages answered with a Cloudflare check and were not read.
No strategy was backtested here; only two context numbers were computed (ES Sharpe in the Hull private window;
HTUS live record). Raw extracts kept: macro_pressure.txt, trading_strats.txt, intro.txt (Macrosynergy
notebooks), hull_exec.pdf, hull_replicate.pdf, htus_spy_bil.csv.

## 1. Competitions screened

| Competition | Years | Scored held-out window | Transferable? | Key held-out evidence | Red flags |
|---|---|---|---|---|---|
| Hull Tactical - Market Prediction | Sep 2025 - Jun 25 2026 | ~130 trading days after Dec 15 2025 | YES (S&P 500 daily allocation 0..2) | 1st lunalu 3.845, 2nd 3.842, 3rd 3.533, 4th YannFb 3.347 (adjusted Sharpe), 3,294 teams | public LB = last 180 train rows (leak, scores ~17); 130-day window: Sharpe SE ~1.4; only the 4th place wrote up |
| MITSUI&CO. Commodity Prediction | Jul 2025 - Jan 16 2026 | ~3 months | partly (commodity/FX/LME spread ranking) | 1st 0.638, 5th 0.532, 6th 0.514, 10th 0.479 (mean/std of daily Spearman) | a pure random-number submission sat at 57th at one update; host thread "most likely completely based on luck" |
| JPX Tokyo Stock Exchange Prediction | 2022 | ~Jul-Oct 2022 | weak (daily XS rank of 2,000 Japanese stocks) | 1st 0.381; 4th 0.347 = rank by 1-day return DESCENDING; its mirror (ascending) scored -0.196 | random score ~ N(0, 0.138); 4th place authors: "mostly luck" |
| Optiver Realized Volatility | 2021 | 3 months forward | idea only (recent RV dominates) | 1st nyanp: t-SNE recovery of time-id order from tick size, neighbour RV features (RMSPE 0.21 -> 0.19) | leak-like time ordering |
| Optiver Trading at the Close | 2023-24 | forward | NO (Nasdaq auction book) | 1st hyd MAE 5.403, online-retrained GBDT | data not available |
| Jane Street RT Market Data | 2024-25 | forward | NO (anonymised features) | 1st ms capital weighted R2 0.0139 | anonymised |
| Jane Street 2020, Two Sigma 2016/2018, Ubiquant 2022, G-Research crypto 2021, DRW crypto 2025, Winton 2016 | - | - | NO | - | anonymised or crypto/news |

## 2. Hull Tactical competition details (the most relevant)

- Target: daily S&P 500 allocation in [0, 2]; metric = Sharpe of strategy excess returns divided by
  (1 + max(0, vol/market_vol - 1.2)) and by (1 + return_gap^2/100) where return_gap = annualised
  underperformance vs the market (penalty quadratic). No transaction costs in the metric.
- Train data: decades of daily rows, anonymised feature families M (market/technical), E (macro), I (rates),
  P (valuation), V (volatility), S (sentiment), MOM, D (dummies); requires accepting the rules (Kaggle login).
  Host now publishes the same daily file after each close (hulltactical.com/approach -> "DOWNLOAD").
- Context computed by us: ES excess Sharpe over 2025-12-16..2026-06-24 (130 days) = 0.97
  (Q1 2026 -1.09, Mar-Jun 2026 +1.43). A dip-then-rally window favours short-term mean reversion.
- 4th place (YannFb, writeup Jul 3 2026, "Technical Model, No Learning: Short Term Reversal"):
  sparse short-horizon mean-reversion alpha researched before the competition (exact rule withheld),
  combined by inverse-volatility weights with a few low-alpha "stabiliser" signals, then a long-window,
  periodically-updated vol-target overlay, clipped to [0, 2]; ~16 trades/yr; no grid search/CV/ensembling.
  Author's long backtest: vanilla 5.2%/yr, 7.7% vol, Sharpe 0.68, MDD -13.6%; with vol target 9.4%/yr,
  14.3% vol, Sharpe 0.66, MDD -25.8%; buy-and-hold 6.3%, 19.2% vol, Sharpe 0.33, MDD -63.8%.
- Discussion facts: AmbrosM "Stop wasting your time here" (high public-LB notebooks had negative CV R2);
  constant allocation 0.806 = 0.469 public score ("do-nothing" baseline); weekly seasonality post
  (Mon/Tue/Fri > Wed/Thu, borderline significance); host paper "Micro Alphas" (SSRN 5035294): elastic net,
  monthly expanding refit, OOS daily R2 ~1.33%; a participant says the starter ElasticNet gives ~0.55 Sharpe
  over 35 years.
- Host live record check (yfinance, adjusted): HTUS (Hull Tactical US ETF) 2015-06-25..2026-10-02 excess
  Sharpe 0.56, MDD -47.5% vs SPY 0.71, MDD -33.8%; IR vs SPY -0.07, beta 0.71. 2015-06..2024-10-02: 0.52 vs
  0.69; 2024-10-03..2026-10-02: 0.77 vs 0.83. The host's own timing models did not beat buy-and-hold live
  (fee ~0.9%/yr does not change this).
- Hull & Qiao "A Practitioner's Defense of Return Predictability" (JPM 2017; exec summary PDF on host site):
  20 predictors, correlation screening |corr| >= 0.10 with the 130-day-ahead excess return, multivariate OLS,
  10-year window refit every 20 days, SPY position proportional to forecast capped at +150%/-50%;
  2001-2015 simulated 12.11%/yr vs 5.79%, Sharpe 0.85 vs 0.21, MDD 21.1% vs 55.2%. Inputs list
  (hull_replicate.pdf) is mostly Bloomberg; ~14 have free proxies.

## 3. Mitsui commodity details

- Targets: 1-4 day log-return differences of ~424 asset pairs (LME metals, JPX futures, US stocks, FX);
  metric = mean / std of the daily Spearman correlation across targets.
- 5th (ZLF): average of a 4-day-window RNN and a 1-day MLP on raw features; "short-term history more
  valuable, longer windows add noise"; single RNN 0.509.
- 6th: LSTM feature forecasting + blend with mean of recent label lags (alpha 0.7); a pure persistence
  model (mean of last label lags) "captures a significant portion" of the score.
- 10th (miguel perez): no ML signal found; static in-sample Kelly-optimal ordering of mean ranks with a
  shrunk covariance; ~0.4 on late validation, 0.479 private.

## 4. Macrosynergy / JPMaQS (Kaggle dataset + notebooks)

- Dataset "JPMaQS Quantamental Indicators" (kaggle.com/datasets/macrosynergy/fixed-income-returns-and-macro-trends),
  224 MB, 2000-01-03..2023-05, 24 currency areas: point-in-time growth nowcast, CPI trends, inflation target,
  real IRS yields, private credit; returns DU02YXR/DU05YXR (IRS receivers), FXXR, EQXR (equity index futures),
  each also vol-targeted (_VT10). Free with Kaggle login; data card says not for trading/investment use.
- Notebook "Macro pressure and rates returns": XGCI = (excess GDP growth trend + core CPI 6m/6m saar minus
  effective target)/2; negative relation with next-month 2y receiver returns. USD: monthly accuracy 0.55,
  Pearson 0.18 (p < 0.01); panel Pearson 0.14.
- Notebook "Trading strategies with JPMaQS": XGHI = (excess growth + mean(CPI yoy, 6m/6m, 3m/3m) minus
  effective target)/2; XGHIPC adds excess private credit growth vs (5y GDP growth + target). Naive PnL,
  G2 (USD+EUR), sig_neg, zn_score_pan, cap 2, monthly, 1-day slip, 10% vol, no costs, 2000-2024 (288 months):
  long-only Sharpe 0.31, XGHIPC 0.75, XGHI 0.78; peak-to-trough -62% / -32% / -23%. Authors: value
  "strongest in the 2000s and 2020s and very faint in the 2010s".

## 5. Kaggle public notebooks that backtest ETF/futures strategies

Searched Kaggle code for trend following futures, VIX term structure, tactical asset allocation, ETF momentum,
etc. The top results are EDA/forecast demos or Hull notebooks whose 17.x public scores come from the leaked
public test set ("DSP + XGBoost = 30+ Sharpe" style titles). No credible, cost-aware ETF/futures backtest
notebook was found; none is used as evidence.

## 6. Free data that could extend our history

| Source | What | Use | Caveat |
|---|---|---|---|
| Kaggle macrosynergy JPMaQS | 2000-2023 point-in-time macro + IRS/FX/equity-future returns, 24 areas | pre-2010 rates/FX/equity returns; macro signals | Kaggle login (user downloads), research-only licence, ends 2023-05 |
| Hull Tactical daily file (Kaggle train.csv / hulltactical.com) | decades of daily S&P forward returns + ~94 anonymised features | ERP-timing features | anonymised names; rules acceptance / site download by the user |
| Kaggle guillemservera commodities/fuels/grains/metals futures | yfinance front-month (=F) 2000+ | pre-2010 commodity history | unadjusted roll gaps; CC BY-NC; same as yfinance directly |
| Kaggle brtnsmth intraday market data | 3-second /ES /NQ /RTY, SPY, QQQ, 2020-2026, weekly updates | intraday checks | starts 2020, 8 GB, login |
| Kaggle "Huge Stock Market Dataset" | US stocks/ETFs daily to 2017 | none needed (yfinance has full ETF history) | stale |
| HF THULab/fred_md, fred_md_2025 | FRED-MD monthly panel | macro features | use the St. Louis Fed FRED-MD vintage files directly for point-in-time |
| HF Chainticks/cftc-cot, Arimancy/cftc-cot-weekly, XOOMAR/cftc-commitments-of-traders | CFTC COT weekly | positioning signals | CFTC history files are free at source |
| HF Farmaanaa/us_treasury_yield_curve_daily, global_vix_volatility_index_daily | yields, VIX | already in fred_daily/index_daily | none |
| HF Khanhpham1992/es-futures-1m, msj-21/es-futures-1m, thillsss/SPX-MES-VIX-data | ES 1-minute | intraday | provenance unclear |

## 7. Candidate summary (exact rules in candidates.json / the structured return)

1. kaggle_hull4_str_es (ES short-term reversal + inverse-vol blend + vol target) - evidence 2
2. kaggle_hull_microalpha_enet (elastic-net ERP timing on free features) - evidence 2
3. kaggle_hull_cs_practitioner (correlation-screening 130-day model) - evidence 2
4. kaggle_hull_seasonal_combo (Sell in May + TOM + pre-FOMC + state momentum) - evidence 2
5. kaggle_jpmaqs_macro_pressure_ust (US macro trend pressure -> ZT/ZF/ZN) - evidence 3
6. kaggle_optiver_har_voltarget_es (HAR-RV from hourly ES for vol targeting) - evidence 3
7. kaggle_jpx_xs_1d_mom_sectors (1-day XS momentum/reversal, sector ETFs) - evidence 1
8. kaggle_mitsui_xs_shortmom_comm (4-day XS persistence, commodity futures) - evidence 1
9. kaggle_hull_dow_es (weekday seasonality) - evidence 1
10. kaggle_optiver_close_imbalance - not implementable
11. kaggle_janestreet_online_anon - not implementable
