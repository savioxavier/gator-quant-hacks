# Sharpe 1.0 in and out of sample: what the published evidence says

*Research synthesis for the Gator Quant Hacks 2026 Systematic Trading entry, compiled 2026-10-03.*

**The question.** Why can't we find a strategy that "consistently gets Sharpe 1.0 or more, both in-sample and out-of-sample"? Our pre-registered strategy is F1: sleeve A (rebalancing pressure), sleeve C (Treasury month-end), and TSMOM on 15 ETFs. Net of costs, it earned a Sharpe of 0.98 in-sample (2006-05 to 2024-10) and −0.12 on its two-year holdout (2024-10 to 2026-10).

**How this was done.** Seven research passes covered:
- trend following;
- multi-asset style premia;
- equity anomalies and machine learning;
- volatility strategies;
- calendar and flow effects;
- carry, macro and crypto;
- meta-studies of how backtests decay.

A separate adversarial verifier then checked each candidate claim against primary sources: papers, fund pages and index factsheets. This report uses only numbers the verifiers confirmed or that I recomputed. Everything else is marked *unverified*.

**Conventions.**
- **Gross** means before transaction costs and fees. **Net** means after them.
- **Out-of-sample (OOS) evidence, strongest first:** (1) a live or real-money record; (2) post-publication performance measured by others; (3) independent replication on new markets or periods; (4) the paper's own holdout. In-sample (IS) backtests alone do not count.
- **"Our calculation"** is arithmetic done for this report. It assumes iid returns unless stated otherwise.
- **"Verifier's calculation"** is a sub-period Sharpe that a verifier computed from AQR's public factor datasets. These are gross paper portfolios.

---

## 1. Bottom line

No. A Sharpe of 1.0 or more held both in-sample and out-of-sample, net of costs, with daily data in liquid markets, is not a realistic target: across about 100 candidate claims in seven families we found no such strategy with a verified net out-of-sample Sharpe of 1.0 or more over a full market cycle. Every Sharpe of 1 or more we found was a gross backtest, a capacity-limited microstructure or arbitrage niche we cannot trade, or a short favourable window. The longest live records cluster at about 0.25-0.6 net (AQR's managed-futures fund 0.26 since 2010, the SG Trend Index 0.30 over 2000-2024, BTOP50 0.40-0.50, AQR Style Premia 0.46 since 2013, AQR Equity Market Neutral about 0.59 since 2014), while the S&P 500 itself earned 0.61 over 2007-2026.

The backtest-to-live haircut is large and consistent: bank risk-premia indices fell from a median Sharpe of 1.20 in backtest to 0.31 live (−73%), published equity anomalies keep about 0.57 times their in-sample Sharpe after publication, and across 888 Quantopian algorithms backtest Sharpe explained only 1-2% of the variation in out-of-sample Sharpe. An honest in-sample Sharpe of about 1.0 should therefore be expected to deliver roughly 0.3-0.6 afterwards, and our own F1 lost 72% of its gross Sharpe (1.35 to 0.38), almost exactly the bank-index median.

Two years is also far too short to judge: the standard error of a two-year annualised Sharpe is about 0.71-0.87, so a strategy whose true Sharpe is exactly 1.0 prints below 1.0 half the time and below zero 8-12% of the time, and our −0.12 is about a 1-in-10 outcome even at a true Sharpe of 0.98 (1-in-5 at 0.5). Demanding 1.0 or more in both samples therefore rejects most genuinely good strategies and rewards overfitting. Any strategy chosen now because it looks good over 2024-26 has turned that window into in-sample data.

### 1.1 Why two years cannot tell 0.4 from 1.0

These are our calculations, using SE ≈ √((1 + SR²/2)/T) (Lo 2002, iid returns), with T = 2 years.

| True Sharpe | SE of a 2-year Sharpe | P(2-year Sharpe ≤ −0.12) | P(2-year Sharpe < 0) | P(2-year Sharpe ≥ 1.0) |
|---|---|---|---|---|
| 0.0 | 0.71 | 43% | 50% | 8% |
| 0.4 (typical live trend) | 0.73 | 24% | 29% | 21% |
| 0.5 | 0.75 | 20% | 25% | 25% |
| 1.0 | 0.87 | 10% | 12% | 50% |

The daily-sampling variant, SE ≈ √(1/T), gives 0.71 and P(<0 | true 1.0) = 7.9%. Fat tails, negative skew and regime clustering make the true uncertainty wider, not narrower. The consequences:

- **The in-sample number is noisy too.** The in-sample 0.98 covers 18.35 years, so its standard error is about 0.28. The gap from 0.98 to −0.12 is only about 1.2-1.5 standard errors.
- **Pooling the two windows by precision gives about 0.83.** That assumes the in-sample estimate has no selection bias. The note's own diagnostics say it has some. CSCV cut 0.98 to 0.75. The Deflated Sharpe Ratio, which is a probability, is 0.40 under the pre-registered trial count.
- **Passing one window takes a very high true Sharpe.** To have a 90% chance of printing 1.0 or more in a single two-year window, a strategy needs a true Sharpe of about 3.3.
- **"Consistently" is out of reach even for a true 1.0.** A strategy with a true Sharpe of 1.0 clears 1.0 in all ten non-overlapping two-year windows with probability 0.1%. It stays positive in all ten only 27% of the time.
- **Small true Sharpes take decades to confirm.** Separating a true Sharpe of 0.4 from zero at t = 2 needs about (2/0.4)² = 25 years of data. Separating 1.0 from zero takes 4 years at t = 2 and 9 years at t = 3.
- **Searching for a strategy that passes both windows manufactures false positives.** A strategy with a true Sharpe of 0.5 has about a 25% chance of a two-year Sharpe of 1.0 or more. It has about a 2% chance of a 19-year in-sample Sharpe of 1.0 or more. So about 0.5% of such strategies pass both by luck. Screen 200 independent ones and the chance that at least one "passes" is about 64%; screen 500 and it is 92%. Correlated trials reduce the effective count, but the direction holds. Our trial log already has 1,467 distinct specifications.

### 1.2 The backtest-to-live haircut

| Evidence | Backtest or in-sample | Out-of-sample or live | Change | Evidence type |
|---|---|---|---|---|
| 215 bank risk-premia indices (Suhonen, Lennkh & Perez 2017) | median Sharpe 1.20 | median 0.31 (average 4.6 live years) | −73% | live |
| 1,726 bank QIS strategies (Liu 2026, preprint) | about 0.41 (12 months before launch) | about 0.10 (first 12 months live), gross | about −75% | live |
| 72 replicated equity anomalies (Falck, Rej & Thesmar 2021) | mean Sharpe 0.98 | about 0.57 × in-sample after publication | −43% | post-publication, gross |
| 97 predictors (McLean & Pontiff 2016) | n/a | returns 26% lower post-sample, 58% lower post-publication | −58% (returns) | post-publication, gross |
| 153 factors in 93 countries (Jensen, Kelly & Pedersen 2023) | alpha 0.49%/month | 0.26%/month after the original sample | −47% | post-sample, gross |
| 355 Quantpedia strategies | median Sharpe 1.18 | median 0.66 | −44% | post-sample (not post-publication); costs not addressed |
| 888 Quantopian algorithms (Wiecki et al. 2016) | n/a | in-sample Sharpe explains 1-2% of out-of-sample Sharpe (R² 0.01-0.02) | n/a | frozen-code forward test |
| AQR multi-style composite → live QSPIX | 1.74 simulated, gross (1990-2013) | 0.46 net, live (Oct 2013-2026) | −74% | live |
| AQR managed-futures blend → live AQMIX | 1.79 gross (1985 to Jun 2012) | 0.26 net, live (2010-2026); about 0.39 before the 1.25% fee (our arithmetic) | −78% to −85% | live |
| **Our F1, gross** | **1.35 (2006-2024)** | **0.38 (2024-26)** | **−72%** | own holdout |

Two caveats on the fund rows:
- **QSPIX.** About half of its gap reflects weaker premia in 2013-2026, not implementation. AQR's own gross paper multifactor portfolio earned about 0.78 over the same window (verifier's calculation).
- **AQMIX.** The comparison mixes a gross backtest with net live returns.

### 1.3 Our result is the base rate

Both F1 flow sleeves kept their sign out of sample, but shrank:
- The rebalancing spread fell from 11.0 to 2.5 bp/day.
- The Treasury month-end IEF return fell from 7.2 to 3.0 bp/day.

F1's gross Sharpe fell from 1.35 to 0.38, which is the median haircut in the bank-index study. These two sleeves correspond to the two calendar/flow candidates that the verifiers rated "no out-of-sample evidence yet": Harvey, Mazzoleni & Melone (2025) and Hartley & Schwarz (2019).

Our plain trend benchmark (TSMOM_F: 12-month signal, 20 CME futures) earned 0.28 in-sample over 2011-2024. That matches the trend industry's 2010s:
- SG Trend: 0.21 over 2010-19.
- AQR's TSMOM factor: 0.40 gross over 2010 to May 2026 (verifier's calculation).

Industry trend over our holdout was mixed: SG Trend lost 10.48% in H1 2025, while BTOP50 gained 3.06% in 2025 and an estimated 14.78% in 2026 year-to-date. No source gave an industry Sharpe for exactly Oct 2024 to Oct 2026.

---

## 2. The strongest candidates

"Verdict" is the adversarial verifier's label:
- **below 1:** confirmed, and the out-of-sample Sharpe is below 1.
- **overstated:** the claimed out-of-sample number is mislabelled or too high.
- **unverified:** no out-of-sample evidence that could be checked.
- **plausible ~1:** close to 1, but only in the authors' own backtest.

| # | Strategy | Key source | In-sample Sharpe | Out-of-sample or live Sharpe (type, period, net?) | Verdict | Buildable with free or Databento daily data? |
|---|---|---|---|---|---|---|
| 1 | Live trend (CTA) indices | Invesco 2024 (SG Trend); Hurst-Ooi-Pedersen (HOP) 2013 Table 3 (BTOP50); Dickens 2026 | n/a (live) | SG Trend 0.30 net (live, Dec 1999-Feb 2024): 0.41 in 2000-09, 0.21 in 2010-19. BTOP50 0.50 net (live, 1987-Jun 2012). BTOP50+SG spliced 0.40 (1987-2024). Live funds trailed AQR's backtest by just under 4 pp/yr | below 1 | partly (CME subset) |
| 2 | AQR 1/3/12-month trend blend, about 58 markets | HOP 2013; AQMIX | 1.79 gross (1985 to Jun 2012) | AQMIX 0.26 net (live, Jan 2010-2026), about 0.39 before fee (our arithmetic). Total return about 0.4%/yr Jan 2010-Sep 2021 (verifier's calculation), then 15.04%/yr Sep 2021-Sep 2026 | below 1 | partly |
| 3 | 12-month TSMOM | Moskowitz-Ooi-Pedersen (MOP) 2012 | "greater than one", gross (1985-2009); 1.1 gross on 1966-85 (referee-requested test; authors had seen pre-1985 data) | AQR TSMOM factor 0.39 gross after May 2012 and 0.24 since 2017 (verifier's calculation). HOP 2017: 0.41 net of costs and 2/20 fees, about 0.77 net of costs only (2010-16) | below 1 | partly |
| 4 | Century of trend (67 markets, 1880-2016) | HOP 2017 | about 1.86 gross, about 1.13 net of costs, 0.76 net of costs and 2/20 fees (our arithmetic from Exhibit 1) | Net Sharpe positive in every decade, ranging 0.13-1.70; 2000-09 0.61; 2010-16 0.41 (net of 2/20). Babu et al.: about 1.0 for 1880-2018 vs about 0.32 for 2010-18, read off a chart | below 1 | partly |
| 5 | Trends Everywhere (156 instruments, incl. swaps, CDS, EM FX) | Babu et al. 2020 | 1.60 gross combined (1985-2017) | Out of sample across new assets (1.34 and 0.95 gross) but not through time; no net figure | unverified | no |
| 6 | 50/50 US equities + live trend index | Dickens 2026, Table 1 (BTOP50 before 1999, SG Trend after) | n/a (live indices) | 0.72 (1987-2024) vs 0.55 for equities alone and 0.40 for trend alone; trend leg net of fees | confirmed (secondary source) | yes (ES or SPY plus a trend sleeve) |
| 7 | Faber GTAA (10-month SMA on 5 asset classes) | Faber 2007/2013, via CXO | 0.73 gross (1973-2012) vs 0.44 buy-and-hold | 0.61 gross after publication (2006-12) vs 0.16 buy-and-hold; short window dominated by 2008 | below 1 | yes (Yahoo ETFs) |
| 8 | Global multi-asset carry | Koijen-Moskowitz-Pedersen-Vrugt (KMPV) 2018; Ilmanen et al. 2021 | 1.20 gross (about 1983-2012; ex-post volatility weights; put-option sleeve 1.80 falls to 0.42 at 1 half-spread) | Ilmanen et al., gross: 0.72 before the original sample, 0.73 after (the "after" period overlaps KMPV's sample). AQR four-asset futures carry 0.07 gross, Jan 2012-Feb 2026 (verifier's calculation) | below 1 / overstated | partly |
| 9 | G10 currency carry | Menkhoff et al. 2012; DBV ETF | 0.56 net of bid-ask, developed markets (1983-2009) | DBV G10 carry ETF −0.26%/yr total return (live, Sep 2006-Mar 2020), i.e. a negative excess return; delisted Mar 2023 | below 1 | yes |
| 10 | Multi-style premia (value, momentum, carry, defensive) | Asness et al. 2015; QSPIX | 1.74 simulated, gross (1990-2013) | QSPIX 0.46 net (live, Oct 2013-2026), about 0.58 before the 1.53% fee (our arithmetic). Returns −12.35% (2018), −8.20% (2019) and −21.96% (2020), then +24.83% and +30.64% | below 1 | partly (stock sleeve: no) |
| 11 | Century multifactor, all assets | Ilmanen et al. 2021 | 1.46 gross (1926-2020) | 0.67 gross after the paper (Dec 2020-Feb 2026). Futures-only "All Macro" multi-style: 1.35 (1981-2011), 0.32 (2012-Feb 2026), 0.08 since 2017 (verifier's calculation) | overstated | partly |
| 12 | Value + momentum everywhere | Asness-Moskowitz-Pedersen 2013 | 1.42 gross (1972-2011) | 0.57 gross, Aug 2011-Jul 2026; futures-only half 0.78 → 0.19 (verifier's calculation from AQR data) | below 1 | partly |
| 13 | Diversified equity anomaly basket | Jensen-Kelly-Pedersen 2023 | alpha 0.49%/month | Gross CAPM-alpha information ratio 0.93 US and 1.10 ex-US (1990-2020; confirmed by one verifier from the published version); alpha −47% after the original samples | below 1 | no |
| 14 | Cost-aware ML portfolio, US large caps | Jensen-Kelly-Malamud-Pedersen (RFS 2026) | n/a | 1.38 net (authors' own holdout 1981-2020; 3.6x gross leverage; costs calibrated, not measured); no independent or live record | plausible ~1 | no |
| 15 | Live equity market neutral | AQR QMNIX | n/a (live) | 0.59 net (live, Oct 2014-Sep 2026, computed from NAV). Sub-periods: 1.80 (2014-17), −2.60 (2018-20), 1.33 (Dec 2020-Sep 2026); max drawdown −38% | below 1 | no |
| 16 | S&P 500 put-writing | Cboe PUT factsheet | n/a | 0.52 gross (live index, Jan 2007-Aug 2026) vs 0.61 for S&P 500 TR; skew −2.09 (1986-2018) | below 1 | partly (the index level is free; trading needs SPX options) |
| 17 | Volatility-managed momentum and factors | Barroso & Santa-Clara 2015; Cederburg et al. 2020 | momentum 0.48 → 0.99 when vol-managed, gross (1927-2016) | Real-time gross: momentum 0.92, ROE 1.13, BAB 1.09. After costs, no alpha except for the market (Barroso & Detzel 2021). Market itself: 0.42 managed vs 0.46 unmanaged | below 1 | partly (French factors are not tradable) |
| 18 | Rebalancing front-running (ES vs ZN) | Harvey-Mazzoleni-Melone 2025 | 1.11 gross, net "close to 1" (1997-2023); 0.90 excluding GFC and COVID; skew 5.2 | No independent OOS. A backward holdout (1961-97) found nothing. Our sleeve A spread fell from 11.0 to 2.5 bp/day out of sample | unverified | yes |
| 19 | Treasury month-end | Hartley & Schwarz 2019 | 0.85-1.11 gross (1990-2018; fitted-curve zero-coupon returns) | Nothing after 2018. Our sleeve C fell from 7.2 to 3.0 bp/day out of sample | unverified | yes |
| 20 | Macro momentum / "economic trend" | Brooks 2017; AQR 2023 | 1.2 gross (1970-2016) | 0.7 gross (AQR's own holdout, 2017-2022); 0.4 for 2010-19; no independent replication | below 1 | partly |
| 21 | Crypto perpetual funding carry | Schmeling-Schrimpf-Todorov 2023; Borri et al. 2026 | n/a | 6.45 gross (BTC, Aug 2020-May 2025), 4.06 from 2024, negative in 2025 | overstated | no |

How to read the table:
- **Rows 1-4 and 15 are live or genuinely post-publication.** None reaches 1.0.
- **Rows 5, 13 and 14 do reach about 1, but on weaker evidence.** Each is gross, measured in the authors' own backtest, or depends on breadth we do not have: swaps and CDS, or thousands of single stocks.
- **The futures-only multi-asset composites are the closest analogues to what we can build (rows 8, 11, 12).** All of them lost most of their Sharpe after 2012 in AQR's own updated data.
- **Row 6 is the highest live-supported Sharpe that liquid daily data can reproduce.** It is a combination of an equity premium and trend, not a market-neutral alpha.

---

## 3. What actually produces durable high Sharpe

### 3.1 Breadth: many uncorrelated premia

Every paper Sharpe of about 1 or more in liquid markets is built from breadth. Ilmanen et al. (2021, gross, 1926-2020) show the ladder directly:

| Construction | Average Sharpe |
|---|---|
| One factor, one asset class | 0.40 |
| One factor, across all asset classes | 0.60 |
| All factors, within one asset class | 0.81 |
| All four factors across six asset classes | 1.46 |

Trend works the same way:
- **Per-market Sharpe is small.** The average single-market trend Sharpe is about 0.3 (Babu et al. 2019) to about 0.4 gross (HOP 2017).
- **Diversification multiplies it.** Diversifying across about 60 or more markets multiplies that by about 3.8x (full sample) to 4.1x (2010-18).
- **Going higher needs markets we do not have.** Trends Everywhere reaches 1.60 gross only with 156 instruments, including swaps, CDS indices, EM FX and equity factors.

The fundamental law of active management makes the same point. IR ≈ IC × √(breadth), so the information coefficient needed for IR = 1 is:
- about 0.29 with 12 independent bets a year;
- about 0.063 with 252;
- about 0.041 with 600.

Correlated markets and persistent positions reduce effective breadth.

The catch is that breadth raises the paper Sharpe but does not stop it decaying. The futures-only version of the four-factor composite fell from 1.35 (1981-2011) to 0.32 (2012-Feb 2026) gross in AQR's own updated data (verifier's calculation). The data cannot tell a long bad regime apart from permanent decay.

### 3.2 Speed and capacity-limited niches

Very high Sharpe ratios do exist, but in places we cannot reach:

- **Renaissance Medallion.** Reported average returns are about 66% a year gross and 39% net since 1988 (Zuckerman, via Wikipedia; a tertiary source). It has been closed to outsiders since 1993. Renaissance's own outside funds trailed it by about 17-19 points (April 2020). Its Sharpe ratio was not found.
- **Crypto perpetual funding carry.** Sharpe 6.45 gross (2020-25), turning negative in 2025 as arbitrage capital arrived. It also carries exchange and collateral tail risk.
- **Perpetual-futures arbitrage.** Sharpe 3.35 for BTC at retail fees, in-sample (2020-24); the authors say deviations "diminish over time".
- **Short-term stock reversal.** Gross Sharpe 8.44 at transaction prices (Nagel 2012). This is the return to market making, now competed away by HFT.
- **Overnight "buy-the-dip" in ES.** 1.10 net in-sample, but it needs signed closing order flow, and the link weakened after publication.

What these have in common: small capacity, intraday or venue-specific data, fast decay once publicised, and tail or counterparty risk. None is buildable from Yahoo, FRED, Cboe or Databento daily bars.

### 3.3 Cost-aware single-stock selection

The one liquid-market area where paper net Sharpe exceeds 1 in a large-cap universe is cost-aware machine-learning portfolio choice: 1.38 net (Jensen-Kelly-Malamud-Pedersen, own backtest). Its live analogue, AQR's equity market-neutral fund, earned about 0.59 net over 2014-2026. It needs CRSP/Compustat-type data across about 1,000 or more stocks, plus shorting, which is outside the track's data.

### 3.4 Why a 0.4-0.6 strategy can still be worth having

Passive equity is a hard bar:
- S&P 500 TR: 0.61 over Jan 2007-Aug 2026.
- MSCI USA: 0.60 since 1988 and 0.84 over the last 10 years.

Most live "alternative" strategies did not beat that Sharpe on their own. Their value is low or negative correlation. Combining US equities with live trend raised the Sharpe from 0.55 to 0.72 over 1987-2024. A strategy with a modest Sharpe but crisis convexity (trend gained in 2008 and 2022) is useful inside a portfolio even though it fails a stand-alone "1.0 or more" test.

### 3.5 What it would take in our setting

- **Breadth.** We have about 20-30 liquid CME contracts across four asset classes, about 15 Yahoo ETFs, and FRED/Cboe series. Equity indices move together, rate futures largely share one curve, and much of FX is a dollar factor, so the number of effective independent bets is much smaller than the contract count.
- **Signals.** Trend has the strongest live record. Carry, value and multi-style composites built from futures alone have been near zero since 2012 in AQR's own data. Seasonality has no evidence after 2016.
- **Realistic target.** Net Sharpe of about 0.3-0.6 for diversified CME trend, and about 0.5-0.7 for an equity-plus-trend blend.
- **A durable net Sharpe of 1 or more would need one of three things.** (a) Breadth we lack: single stocks with fundamentals, swaps, CDS, EM FX. (b) A capacity-limited niche with intraday or venue data. (c) A lucky window. QSPIX, QMNIX and AQMIX all had five-year live windows near or above 1 (2021-26) inside full records of 0.26-0.59. Favourable windows like those are what tends to be marketed.

---

## 4. Strategies that failed out of sample after publication

| Strategy | Claimed (in-sample) | What happened afterwards | Evidence type |
|---|---|---|---|
| Pre-FOMC announcement drift | Sharpe 1.14 gross for 2pm-to-2pm, 0.84 close-to-close (1994-2011) | "Essentially disappeared after 2015" (Kurov et al. 2021). 2011-2023 coefficient 0.16% (t = 1.5) vs 0.49% before, about 0.4 gross (verifier's derivation) | post-publication, independent |
| FOMC even-week cycle | 0.88 gross (1994-2015, CXO replication) | Opposite cycle in 2017-2021: −12.0 bp/day on even weeks (t = −1.84), reported by one of the original authors | post-publication |
| Overnight drift in ES (2-3am ET) | 1.10 gross but −0.54 net (2004-2020) | Averaged close to zero since 2021 (the same authors, 2026) | post-publication |
| US turn-of-the-month | about 1.04 gross (1926-2005; Quantpedia's calculation, total return) | Gone after 2001 (Han, Han & Tian 2025); largely gone in US ETFs over the past decade | post-publication |
| S&P 500 index-inclusion effect | +7.4% abnormal return (1990s) | Under 1% in the 2010s (Greenwood & Sammon 2025) | post-publication |
| Daily contrarian / reversal | 1.38%/day (1995) | 0.13%/day by 2007 (Khandani & Lo) | decay within the papers' samples |
| Inverse VIX ETN (XIV) | live Sharpe 0.649 net before the crash (2010-17; blog calculation) | Lost 96% in one day on 5 Feb 2018 and was liquidated (exact index values not re-verified) | live |
| G10 FX carry ETF (DBV) | 0.56-1.02 in academic samples | −0.26%/yr total return, Sep 2006-Mar 2020; delisted 2023 | live |
| Bank risk-premia indices | median backtest 1.20 | median live 0.31; 65 of 215 negative live | live |
| Quantopian crowd-sourced fund | backtest Sharpe barely predictive (R² 0.01-0.02) | Up to $250M committed (2016); returned investor capital for underperformance in 2020 | live |
| AQR futures-only multi-style ("All Macro") | 1.35 gross (1981-2011) | 0.32 (2012-Feb 2026), 0.08 since 2017, gross (verifier's calculation) | post-publication |
| Global futures carry (four asset classes) | 0.88 gross (1981-2011) | 0.07 gross, 2012-Feb 2026 (verifier's calculation) | post-publication |
| Betting against beta | 0.78 gross (1926-2012) | About $1.05 per $1 sits in the bottom 1% of market cap; costs cut profit by about 60%, giving roughly 0.3 (verifier's derivation); no FF5 alpha | independent replication |
| Short index straddles and strangles | 1.19-1.69 gross at mid prices | Real spreads plus margin rules cut most strategies to about 0.3-0.45 annualised. Live blow-ups: Niederhoffer (Oct 1997); LJM in 2018 (LJM figures unverified) | implementation test, live |
| Neural-network stock selection (Gu-Kelly-Xiu) | 1.35 value-weighted, 2.45 equal-weighted, gross | Independent re-test 0.94 value-weighted, 0.64 excluding microcaps (gross); one-month ML "close to zero" net after 2004 (Blitz et al.) | independent replication |
| Volatility-managed market portfolio | 0.51 in-sample | Real-time 0.42 vs 0.46 unmanaged (Cederburg et al.) | real-time re-test |
| Factor timing | IR 0.89 with full-sample coefficients | Out-of-sample IR about 0.3; static Sharpe rises only from 1.48 to 1.51, with break-even costs of about 1.8 bp | own holdout |
| "Beat the Market" SPY intraday breakout | 1.33 net, but only after design steps on a 0.61 base | About 0 in 2025-26 (unreviewed independent replication) | post-publication, weak |
| Published equity anomalies (base rate) | various | Returns −26% post-sample and −58% post-publication; Sharpe about 0.57 × in-sample | post-publication |
| **Our F1** | **0.98 net, 1.35 gross** | **−0.12 net, 0.38 gross** | own holdout |

The patterns:

1. **Calendar and timing effects that anyone with daily data can trade die fastest once publicised.** Examples: pre-FOMC drift, the FOMC cycle, turn-of-the-month, and the overnight drift.
2. **Flow and mechanism effects decay too.** The index effect, overnight inventory and reversal all did. The verifier rejected the claim that flow effects "survive better": the flow effects that look alive (rebalancing, Treasury month-end) simply have no out-of-sample test yet. Our holdout is now one: both kept their sign and shrank 58-77%.
3. **Going from gross to net kills microstructure-sized edges.** The overnight drift goes from 1.10 gross to −0.54 net.
4. **Negatively skewed carry and short-volatility trades look fine until they don't.** Examples: XIV, DBV, short straddles.
5. **Complexity and specification search predict decay.** "Beat the Market" went from 0.61 to 1.33 through design steps. Complex bank indices decayed about 30 percentage points more than simple ones.
6. **Broad multi-asset premia shrank rather than vanished.** Trend's net Sharpe by decade was 0.61 in the 2000s and 0.41 in 2010-16, while every decade since 1880 was positive.

---

## 5. Recommendation: a second forward test

### 5.1 Ground rules

- **These cannot be validated on 2024-10 to 2026-10.** We have already seen that window, and it was used to judge F1. Anything chosen or tuned because of its 2024-26 performance is in-sample. The same applies to 2006-2024, which we have studied closely. The only clean evidence is data on or after **2026-10-06**.
- **Forward test 1 is already frozen** (tag `forward-test-2026-10-03`). It covers F1, F2 and F3, with TSMOM_F as a benchmark. Its files (`src/forward.py`, `scripts/run_forward.py`) must not change. Put the second test in new files, e.g. `FORWARD_TEST_2.md`, `src/forward2.py` and `scripts/run_forward2.py`. Commit and tag them, e.g. `forward-test-2-2026-10-05`, before the Monday 2026-10-05 close. Decide positions from data through Fri 2026-10-02 and trade at the Oct 5 close, so the first counted return day is Oct 6, the same as forward test 1.
- **Compute history only after the freeze,** in a separate commit, as was done for F2. Report it as context only.
- **Treat multiple testing honestly.** These are three new hypotheses, so α = 0.05/3 within this family, or 0.05/6 for any claim that spans both forward tests. Realistically, nothing will reach significance in 24 months: a true Sharpe of 0.5 over 2 years gives t ≈ 0.7.
- **Judge with intervals and benchmark tracking, not a 1.0 bar.** A 24-month Sharpe of 1.0 or more should be read as luck-assisted, not as validation. A result below the 5th percentile of the pre-registered interval is evidence against the build.
- **These are paper evaluations,** not investment advice.

The three candidates were chosen because they have the best out-of-sample evidence that our data can reproduce. They are not independent: S2 contains S1, and S3 is a long-biased trend filter. Count them as one family.

### 5.2 S1: broad CME trend, published 1/3/12-month blend

**Why.** Trend has the strongest live record of any premium in this review:
- SG Trend: 0.30 net over 24 years.
- BTOP50: 0.40-0.50 net over 25-37 years.
- AQMIX: 0.26 net, about 0.39 before fees.
- A net-positive Sharpe in every decade since 1880.
- In the bank-index study, trend was among the least-decaying styles.

It is also the leg of F1 that made money out of sample.

S1 differs from TSMOM_F in two ways that the literature says matter:
- **Breadth.** About 30 markets instead of 20.
- **The published multi-horizon signal** (HOP 2013) instead of a 12-month-only signal. Live AQR funds trade a blend in this spirit.

Do not expect to detect the S1-minus-TSMOM_F difference within 24 months. The two are highly correlated.

**Rule sketch.** Freeze exact values in `FORWARD_TEST_2.md`.
- **Universe (Databento GLBX.MDP3).** The 20 TSMOM_F contracts (ES NQ RTY YM ZT ZF ZN ZB CL NG GC SI HG 6E 6J 6B 6A 6C ZC ZS) plus UB, HO, RB, PL, ZW, ZL, ZM, LE, HE and 6S. Before freezing, confirm that each has daily bars, and drop and record any that do not. Delisting rule: as in forward test 1.
- **Returns.** Use the existing PCT-F engine conventions: within-contract returns, roll on the vendor's front-contract change with one round trip charged per roll, fully collateralised at the T-bill rate.
- **Signal.** At each month-end close, for each market and each k ∈ {21, 63, 252} trading days, take sᵏ = sign(cumulative futures return over the past k days). The position signal is s = (s²¹ + s⁶³ + s²⁵²)/3.
- **Sizing.** Reuse the TSMOM_F sizing engine unchanged: wᵢ = sᵢ × (0.40/σᵢ)/N. Here σᵢ is an EWMA estimate of daily volatility (center of mass 60 days, as in MOP 2012), annualised. Scale the book to 10% ex-ante volatility with the trailing 252-day covariance, and cap gross exposure at 3.
- **Execution and costs.** Trade at the next session's close (`next_close`). Costs are 1.5 bp one-way, and 5 bp for NG, RTY, ZC, ZS, 6A, 6C and every added contract except UB and 6S. Also report the result at 2x costs.
- **Data.** Databento daily bars, already in the pipeline, plus the FRED T-bill.

**Expected net Sharpe.** About 0.2-0.6 over the long run, with 0.4 as the central case. Our universe is narrower than AQR's 58-67 markets, so lean toward the lower half. The 90% interval for a 24-month Sharpe, if the true value is 0.4, is about −0.8 to +1.6.

**Implementation check.** Pre-register the correlation of S1's weekly returns with DBMF and AQMIX, both free on Yahoo. This checks whether we built the premium the evidence is about, and it is informative over months rather than decades. We suggest flagging the build if the correlation falls below 0.5 in a six-month block. That threshold is our choice, not a figure from the literature.

### 5.3 S2: equity plus trend, equal-risk blend (recommended primary)

**Why.** This is the highest Sharpe in the review that is backed by long live data and buildable with daily liquid data. A 50/50 mix of US equities and live trend indices earned 0.72 over 1987-2024, against 0.55 for equities and 0.40 for trend alone (trend leg net of fees). The mechanism is simple and has held up live: trend's crisis convexity (2008, 2022) offsets equity drawdowns.

**Rule sketch.**
- **Two sleeves, each scaled to 10% ex-ante volatility** using the same EWMA estimator. The equity sleeve is long ES (front contract, same engine). The trend sleeve is the S1 book.
- **Combination.** Take 0.5 × each sleeve, then rescale the sum to 10% ex-ante volatility using the trailing 252-day covariance of the two sleeves' returns. Cap gross exposure at 3. Rebalance monthly, same execution and costs as S1.
- **Data.** Databento ES plus the S1 inputs. A free cross-check is SPY plus DBMF on Yahoo.

**Expected net Sharpe.** About 0.4-0.7, with 0.6 as the central case. It is lower if the equity premium is weaker than in 1987-2024. The 90% interval for a 24-month Sharpe, if the true value is 0.6, is about −0.7 to +1.9.

**Caveats.**
- S2 is not market-neutral. Its beta to the S&P 500 is about 0.4 (our estimate, assuming about 16% S&P volatility and near-zero trend-equity correlation). Report beta and alpha against SPY.
- If the track scores market-neutral alpha, S1 should be the primary instead.

### 5.4 S3: Faber GTAA on free data

**Why.** It is a simple rule, published in 2006/2007 and unchanged since, with a post-publication record. It uses free data and trades only 3-4 round trips a year. The record: 0.61 gross over 2006-12 against 0.16 for buy-and-hold, and 0.73 against 0.44 over 1973-2012. It is a free-data, long-only cousin of S2.

**Rule sketch.**
- **Universe.** Equal 20% in SPY, EFA, IEF, VNQ and DBC (GSG tracks Faber's GSCI more closely; pick one before freezing).
- **Signal.** At each month-end close, hold an ETF if its adjusted month-end close is above the simple average of its last 10 month-end closes. Otherwise hold that 20% in T-bills (FRED accrual).
- **Execution and costs.** Trade at the next session's open (`next_open`, the project's ETF convention) with the project's ETF costs. The first decision uses the 2026-09-30 month-end and is traded on Oct 5.

**Expected net Sharpe.** About 0.3-0.6. The 90% interval for a 24-month Sharpe, if the true value is 0.45, is roughly −0.75 to +1.7.

**Caveats.** The post-publication window is short and dominated by 2008, and all figures are gross. CXO flags possible data snooping in the 10-month window. A third-party 2007-2025 figure of 0.68 is unverified.

### 5.5 What not to pre-register, and why

- **More calendar or flow sleeves.** F1 and F2 already carry sleeves A and C. Pre-FOMC drift, the FOMC cycle, US turn-of-the-month and the overnight drift have all died after publication.
- **Stand-alone carry.** Futures carry in AQR's own data has been about 0 gross since 2012, the live G10 carry ETF lost money and closed, and carry is negatively skewed. It is defensible only as a small diversifying sleeve, reported separately.
- **Short volatility.** The put-write index trailed the S&P 500's Sharpe live, XIV blew up, and option data is outside our set.
- **Equity anomalies and ML.** They need CRSP/Compustat-type data, and net returns in liquid names are near zero after 2005.
- **Crypto funding carry.** It is outside the allowed data and decaying.
- **Anything chosen using its 2024-10 to 2026-10 performance.**

---

## Limits of this review

- **The search was not exhaustive.** The verifiers exhausted their web-search budgets and finished by fetching known URLs. Industry indices such as HFRI and the Fung-Hsieh trend factor were not retrieved. No primary quotes from Man AHL or Two Sigma were obtained.
- **AQR dataset sub-periods are our own calculations.** The post-publication figures from AQR's public datasets (TSMOM, Century of Factor Premia, Value and Momentum Everywhere) are verifier calculations, not published numbers. The scripts (`vme_oos.py`, `century_oos.py`, `tsmom_oos.py`) sit in this session's temporary scratchpad and should be copied into the repo if these numbers are reused.
- **Single-source or secondary items:**
  - the JKP information ratios (0.93 and 1.10), confirmed by one verifier from the published version, while a second could see only the working paper;
  - the Dickens 50/50 table (a transparent but secondary blog);
  - the XIV live Sharpe (a blog calculation);
  - the Medallion returns (tertiary);
  - the Liu (2026) and Chen-Welch (2026) results (unrefereed preprints).
- **Unverified:**
  - the Uppal FOMC-cycle results;
  - Hutchinson & O'Brien (2014);
  - the Russell reconstitution figures;
  - the NightShares return figures;
  - the exact XIV and LJM crash values;
  - Gao et al.'s 1.08;
  - the Baltas-Kosowski in-sample figure above 1.20;
  - the SG Trend calendar returns for 2020, 2023 and 2025;
  - the QSPIX −41% drawdown;
  - AQR's "0.4 net" forward-case statement;
  - the Arnott-Harvey-Markowitz quote;
  - Lo's "up to 65%" serial-correlation overstatement;
  - the VIX-basis out-of-sample backtest (Sharpe 0.126).
- **All sampling arithmetic assumes iid returns.** Skew, fat tails and regime clustering widen every interval quoted here.

---

## 6. References

**Meta-evidence on backtest decay and statistics**
- Suhonen, Lennkh & Perez (2017), "Quantifying Backtest Overfitting in Alternative Beta Strategies," *Journal of Portfolio Management* 43(2). Summary: https://www.cxoadvisory.com/big-ideas/live-performance-of-alternative-beta-products/ ; abstract: https://research.aalto.fi/en/publications/quantifying-backtest-overfitting-in-alternative-beta-strategies/ ; https://hedgefundalpha.com/strategies/alternative-beta-strategies-complexity-magical-backtests/
- Liu (2026), "Evaluating Structured Strategy Backtests," arXiv:2604.18821. https://arxiv.org/abs/2604.18821
- Wiecki, Campbell, Lent & Stauth (2016), "All That Glitters Is Not Gold," SSRN 2745220. http://ssrn.com/abstract=2745220 ; https://www.cxoadvisory.com/big-ideas/in-sample-vs-out-of-sample-performance-of-888-trading-strategies ; https://en.wikipedia.org/wiki/Quantopian
- McLean & Pontiff (2016), "Does Academic Research Destroy Stock Return Predictability?" *Journal of Finance* 71(1). https://www.gwern.net/doc/economics/2016-mclean.pdf
- Falck, Rej & Thesmar (2021), "Why and How Systematic Strategies Decay," arXiv:2105.01380. https://arxiv.org/abs/2105.01380
- Quantpedia (2023), "In-Sample vs. Out-of-Sample Analysis of Trading Strategies." https://quantpedia.com/in-sample-vs-out-of-sample-analysis-of-trading-strategies/
- Chen & Zimmermann (2022), "Open Source Cross-Sectional Asset Pricing," *Critical Finance Review*. https://cfr.ivo-welch.info/published/papers/chen2021open.pdf
- Chen, Lopez-Lira & Zimmermann (2024), "Does Peer-Reviewed Research Help Predict Stock Returns?" https://arxiv.org/abs/2212.10317
- Hou, Xue & Zhang (2020), "Replicating Anomalies," *Review of Financial Studies* 33(5). https://www.nber.org/papers/w23394 ; https://ideas.repec.org/a/oup/rfinst/v33y2020i5p2019-2133..html
- Jensen, Kelly & Pedersen (2023), "Is There a Replication Crisis in Finance?" *Journal of Finance* 78(5). https://research-api.cbs.dk/ws/portalfiles/portal/95651880/theis_ingerslev_jensen_et_al_is_there_a_replication_crisis_in_finance_publishersversion.pdf ; https://www.nber.org/papers/w28432
- Chen & Velikov (2023), "Zeroing In on the Expected Returns of Anomalies," *JFQA* 58(3). https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/zeroing-in-on-the-expected-returns-of-anomalies/945133D5A3ECEEAF466AEE91551FD225 ; https://www.federalreserve.gov/econres/feds/files/2020039pap.pdf
- Chen & Welch (2026), "What Useful Alphas?" arXiv:2607.06502. https://arxiv.org/abs/2607.06502
- Harvey & Liu (2015), "Backtesting," *Journal of Portfolio Management*. https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF
- Harvey, Liu & Zhu (2016), "...and the Cross-Section of Expected Returns," *Review of Financial Studies*. https://people.duke.edu/~charvey/Research/Published_Papers/P118_and_the_cross.PDF
- Bailey, Borwein, López de Prado & Zhu (2014), "Pseudo-Mathematics and Financial Charlatanism," *Notices of the AMS* 61(5). https://www.ams.org/notices/201405/rnoti-p458.pdf
- Bailey & López de Prado (2014), "The Deflated Sharpe Ratio," *Journal of Portfolio Management* 40(5). https://papers.ssrn.com/abstract=2460551
- Lo (2002), "The Statistics of Sharpe Ratios," *Financial Analysts Journal* 58(4). Formula used; not re-fetched.
- Renaissance Technologies (secondary summary of Zuckerman 2019 and Bloomberg 2015). https://en.wikipedia.org/wiki/Renaissance_Technologies

**Trend following**
- Moskowitz, Ooi & Pedersen (2012), "Time Series Momentum," *JFE* 104. https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf
- Hurst, Ooi & Pedersen (2013), "Demystifying Managed Futures," *JOIM* 11(3). https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/Demystifying-Managed-Futures.pdf
- Hurst, Ooi & Pedersen (2017), "A Century of Evidence on Trend-Following Investing," *JPM* 44(1). https://fairmodel.econ.yale.edu/ec439/hurst.pdf ; https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/AQR-JPM-Fall-2017.pdf ; 2014 version: https://oxfordstrat.com/coasdfASD32/uploads/2016/03/A-Century-of-Evidence-on-Trend-Following-Investing.pdf
- Babu, Hoffman, Levine, Ooi, Schroeder & Stamelos (2020), "You Can't Always Trend When You Want," *JPM* 46(4). https://www.belmontinvestments.com/cimg/file/articles/53/pdf/190425aqrtrendfollowing.pdf ; https://www.aqr.com/Insights/Research/Journal-Article/You-Cant-Always-Trend-When-You-Want
- Babu, Levine, Ooi, Pedersen & Stamelos (2020), "Trends Everywhere," *JOIM* 18(1). https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/AQR-Trends-Everywhere_JOIM.pdf
- Lempérière, Deremble, Seager, Potters & Bouchaud (2014), "Two Centuries of Trend Following." https://arxiv.org/abs/1404.3274
- NBIM Discussion Note 1/2014, time-series momentum. https://www.nbim.no/globalassets/documents/news/2014/discussionnote_time_series_momentum_latest.pdf
- Invesco (2024), "Navigating Momentum Crashes," *Risk & Reward* Q2 2024. https://invesco.com/content/dam/invesco/emea/en/pdf/RRE_2024_Q2_NavigatingMomentum.pdf
- Goulding, Harvey & Mazzoleni (2024), "Breaking Bad Trends," *FAJ* 80(1). https://people.duke.edu/~charvey/Research/Published_Papers/P167_Breaking_bad_trends.pdf
- Robertson (Man AHL) via AIMA (2023), "Trend-Following: What's Not to Like?" https://www.aima.org/article/trend-following-what-s-not-to-like.html
- Dickens (2026), "Contra 'Time Series Momentum: Is It There?'" https://buttondown.com/mdickens/archive/contra-time-series-momentum-is-it-there/
- BarclayHedge BTOP50 index page. https://portal.barclayhedge.com/cgi-bin/indices/displayHfIndex.cgi?indexCat=Barclay-Investable-Benchmarks&indexName=BTOP50-Index
- New Jersey Division of Investment, Winton Futures Fund memo (2015). https://www.nj.gov/treasury/doinvest/pdf/AlternativeInvestments/HedgeFund/WintonFutures.pdf
- AQR Managed Futures Strategy Fund (AQMIX). https://funds.aqr.com/funds/aqr-managed-futures-strategy-fund
- AQR Time Series Momentum factors dataset. https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Time-Series-Momentum-Factors-Monthly.xlsx
- SG Trend reports: https://thefullfx.com/year-end-drop-fails-to-dampen-stellar-2022-for-trend-followers/ ; https://www.alternativeswatch.com/2025/07/01/trend-following-hedge-funds-loss-h1-societe-generale-index/
- DBMF. https://stockanalysis.com/etf/dbmf
- Faber (2007), "A Quantitative Approach to Tactical Asset Allocation." https://www.trendfollowing.com/whitepaper/CMT-Simple.pdf ; 2018 revisit: https://allocatortraining.com/wp-content/uploads/2023/06/A-Quantitative-Approach-to-Tactical-Asset-Allocation.pdf ; CXO summary: https://www.cxoadvisory.com/technical-trading/long-term-outperformance-from-trends-defined-by-moving-averages/

**Style premia and carry**
- Asness, Moskowitz & Pedersen (2013), "Value and Momentum Everywhere," *Journal of Finance* 68(3). https://www.johnhcochrane.com/s/Value-and-Momentum-Everywhere.pdf ; AQR dataset: https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Value-and-Momentum-Everywhere-Factors-Monthly.xlsx
- Koijen, Moskowitz, Pedersen & Vrugt (2018), "Carry," *JFE* 127(2). https://research-api.cbs.dk/ws/files/57294842/lasse_heje_pedersen_et_al_carry_acceptedmanuscript.pdf ; https://www.nber.org/papers/w19325
- Ilmanen, Israel, Lee, Moskowitz & Thapar (2021), "How Do Factor Premia Vary Over Time? A Century of Evidence," *JOIM* 19(4). https://www.aqr.com/-/media/AQR/Documents/Journal-Articles/JOIM_How-Do-Factor-Premia-Vary-Over-Time.pdf ; AQR dataset: https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Century-of-Factor-Premia-Monthly.xlsx
- Baltussen, Swinkels & Van Vliet (2021), "Global Factor Premiums," *JFE* 142(3). https://papers.ssrn.com/abstract=3325720 ; https://www.institutional-investment.de/uploads/media/Robeco_Study_Global-Factor-Premiums.pdf
- Asness, Ilmanen, Israel & Moskowitz (2015), "Investing with Style," *JOIM* 13(1). https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/JOIM-Investing-With-Style.pdf
- AQR Style Premia Alternative Fund (QSPIX). https://funds.aqr.com/funds/aqr-style-premia-alternative-fund
- Allspring Alternative Risk Premia Fund. https://www.allspringglobal.com/investments/multi-asset/mutual-funds/alternative-risk-premia/ ; Risk.net (2020): https://www.risk.net/investing/7422001/how-diversifying-too-far-weakened-alt-risk-premias-rebound
- Fan, Li, Liao & Liu (2022), "A Reexamination of Factor Momentum," *Financial Review*. https://pureadmin.qub.ac.uk/ws/portalfiles/portal/532038294/A_reexamination_of_factor_momentum.pdf
- Haddad, Kozak & Santosh (2020), "Factor Timing," *RFS*. https://www.nber.org/system/files/working_papers/w26708/w26708.pdf
- Menkhoff, Sarno, Schmeling & Schrimpf (2012), "Carry Trades and Global FX Volatility," *Journal of Finance*. https://openaccess.city.ac.uk/id/eprint/3391/1/CTVOL_R3_v4_paper.pdf
- Daniel, Hodrick & Lu (2017), "The Carry Trade: Risks and Drawdowns." https://www.nber.org/papers/w20433
- Invesco DB G10 Currency Harvest Fund (DBV), SEC filing (2020). https://www.sec.gov/Archives/edgar/data/1354730/000119312520124811/d903986dfwp.htm
- Doskov & Swinkels (2015), "Empirical Evidence on the Currency Carry Trade, 1900-2012." https://ideas.repec.org/a/eee/jimfin/v51y2015icp370-389.html
- Beekhuizen, Duyvesteyn, Martens & Zomerdijk (2019), "Carry Investing on the Yield Curve." https://www.efmaefm.org/0EFMAMEETINGS/EFMA%20ANNUAL%20MEETINGS/2017-Athens/papers/EFMA2017_0407_fullpaper.pdf
- Fuertes, Miffre & Rallis (2010), commodity momentum and term structure, *JBF*. https://openaccess.city.ac.uk/id/eprint/6416/1/Fuertes_Miffre_Rallis_JBF2010(CRO).pdf
- Bianchi, Fan, Miffre & Zhang (2023), "Exploiting the Dynamics of Commodity Futures Curves." https://arxiv.org/abs/2308.00383
- Brooks (2017), "A Half Century of Macro Momentum," AQR. https://www.aqr.com/Insights/Research/White-Papers/A-Half-Century-of-Macro-Momentum ; "Economic Trend" (2023): https://www.aqr.com/-/media/AQR/Documents/White-Papers/Economic-Trend_.pdf

**Equity anomalies and machine learning**
- Novy-Marx & Velikov (2016), "A Taxonomy of Anomalies and Their Trading Costs," *RFS*. https://mysimon.rochester.edu/novy-marx/research/ToAatTC.pdf
- DeMiguel, Martín-Utrera, Nogales & Uppal (2020), "A Transaction-Cost Perspective on the Multitude of Firm Characteristics," *RFS*. https://lbsresearch.london.edu/id/eprint/1124/1/DeMiguel_TransactionCostPerspective.pdf
- Gu, Kelly & Xiu (2020), "Empirical Asset Pricing via Machine Learning," *RFS*. https://www.nber.org/papers/w25398
- Chen, Pelger & Zhu (2024), "Deep Learning in Asset Pricing," *Management Science*. https://arxiv.org/abs/1904.00745
- Avramov, Cheng & Metzker (2023), "Machine Learning vs. Economic Restrictions," *Management Science*. https://si-cheng.net/wp-content/uploads/2023/05/2023-ms-avramov_cheng_metzker-machine-learning-vs.-economic-restrictions.pdf
- Blitz, Hanauer, Hoogteijling & Howard (2023), "The Term Structure of Machine Learning Alpha." https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4474637
- Azevedo, Hoegner & Velikov, "The Expected Returns on Machine-Learning Strategies." https://afajof.org/management/viewp.php?n=75544
- Jensen, Kelly, Malamud & Pedersen (2026), "Machine Learning and the Implementable Efficient Frontier," *RFS* 39(10). https://academic.oup.com/rfs/article/39/10/3035/8524346 ; working paper: https://afajof.org/management/viewp.php?n=32368
- AQR Equity Market Neutral Fund (QMNIX). https://funds.aqr.com/funds/aqr-equity-market-neutral-fund
- AI Powered Equity ETF (AIEQ). https://finance.yahoo.com/quote/AIEQ

**Volatility and low risk**
- Cboe PutWrite Index factsheet. https://cdn.cboe.com/resources/indices/factsheet/CboeGlobalIndices_PUT-Index.pdf ; Bondarenko via CXO: https://cxoadvisory.com/?p=28335
- Cboe BuyWrite Index factsheet. https://cdn.cboe.com/resources/indices/factsheet/CboeGlobalIndices_BXM-Index.pdf
- MSCI USA Minimum Volatility Index factsheet. https://www.msci.com/documents/10199/d60451b0-d1b7-4473-b842-2bb8bc83c6f1
- Early Retirement Now (2017), XIV statistics. https://earlyretirementnow.com/2017/10/25/returned-over-100-percent-year-to-date-still-not-buying-it/
- Santa-Clara & Saretto (2009), "Option Strategies: Good Deals and Margin Calls." https://conference.nber.org/confer/2005/bfs05/saretto.pdf
- Dew-Becker, Giglio, Le & Rodriguez (2017), "The Price of Variance Risk." https://www.nber.org/papers/w21182
- Cao, Han, Tong & Zhan (2022), "Option Return Predictability." https://www.mcgill.ca/desautels/files/desautels/option_return_predictability_0.pdf
- Cederburg, O'Doherty, Wang & Yan (2020), "On the Performance of Volatility-Managed Portfolios," *JFE*. https://www.lehigh.edu/~xuy219/research/COWY.pdf
- Barroso & Detzel (2021), *JFE*. https://ideas.repec.org/a/eee/jfinec/v140y2021i3p744-767.html
- Barroso & Santa-Clara (2015), "Momentum Has Its Moments." https://ciencia.ucp.pt/en/publications/momentum-has-its-moments/
- Harvey et al. (2018), "The Impact of Volatility Targeting," *JPM*. https://people.duke.edu/~charvey/Research/Published_Papers/P135_The_impact_of.pdf
- Frazzini & Pedersen (2014), "Betting Against Beta." https://pages.stern.nyu.edu/~lpederse/papers/BettingAgainstBeta.pdf ; Novy-Marx & Velikov (2022), "Betting Against Betting Against Beta": https://mysimon.rochester.edu/novy-marx/research/BABAB.pdf

**Calendar and flow effects**
- Lucca & Moench (2015), "The Pre-FOMC Announcement Drift." https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr512.pdf
- Kurov, Wolfe & Gilbert (2021), "The Disappearing Pre-FOMC Announcement Drift." https://ideas.repec.org/a/eee/finlet/v40y2021ics1544612320315956.html
- Knox & Vissing-Jorgensen (2025), FEDS 2026-023. https://www.federalreserve.gov/econres/feds/files/2026023pap.pdf
- CXO Advisory, FOMC even weeks. https://www.cxoadvisory.com/calendar-effects/hold-stocks-only-during-fomc-even-weeks ; Nagel & Xu (2024): https://nber.org/papers/w32884
- McConnell & Xu (2008), turn of the month. https://ideas.repec.org/a/taf/ufajxx/v64y2008i2p49-64.html ; Han, Han & Tian (2025): https://ideas.repec.org/a/eee/finlet/v71y2025ics1544612324014909.html ; https://www.quantseeker.com/p/turn-of-the-month-strategies-do-they ; https://quantpedia.com/strategies/turn-of-the-month-in-equity-indexes
- Boyarchenko, Larsen & Whelan (2023), "The Overnight Drift." https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf ; "The Disappearing Overnight Drift" (2026): https://libertystreeteconomics.newyorkfed.org/?p=43261
- NightShares ETFs liquidation filing. https://www.sec.gov/Archives/edgar/data/1199046/000158064223003676/nightshares497s.htm
- Baltussen, Da, Lammers & Martens (2021), "Hedging Demand and Market Intraday Momentum." https://www3.nd.edu/~zda/intramom.pdf
- Zarattini, Aziz & Barbon (2024), "Beat the Market." https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download ; replication: https://github.com/codecat-ops/zarattini-2024-momentum-spy
- Greenwood & Sammon (2025), "The Disappearing Index Effect." https://www.nber.org/system/files/working_papers/w30748/w30748.pdf
- Harvey, Mazzoleni & Melone (2025/2026), "The Unintended Consequences of Rebalancing." https://www.nber.org/papers/w33554 ; https://www.edhec.edu/sites/default/files/2026-03/Scientific%20paper.%20ssrn-5122748.pdf
- Hartley & Schwarz (2019), "Predictable End-of-Month Treasury Returns." https://rodneywhitecenter.wharton.upenn.edu/wp-content/uploads/2019/12/17-19.Schwarz.pdf
- Nagel (2012), "Evaporating Liquidity." https://www.nber.org/papers/w17653 ; Khandani & Lo (2007): https://www.newyorkfed.org/medialibrary/media/research/conference/2007/liquidity/Khandani_Lo.pdf ; de Groot, Huij & Zhou (2012): https://repub.eur.nl/pub/25718/AnotherLook_2011.pdf

**Crypto**
- Schmeling, Schrimpf & Todorov (2023), "Crypto Carry," BIS WP 1087. https://www.bis.org/publications/working-paper-1087-crypto-carry
- Borri, Liu, Tsyvinski & Wu (2026), "Cryptocurrency as an Investable Asset Class: Coming of Age." https://arxiv.org/abs/2510.14435
- He, Manela, Ross & von Wachter, "Fundamentals of Perpetual Futures." https://arxiv.org/abs/2212.06888
- Zarattini, Pagani & Barbon (2025), "Catching Crypto Trends." https://ideas.repec.org/p/chf/rpseri/rp2580.html
