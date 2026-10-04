# allocation_rotation: research notes (2026-10-03)

Scope: tactical and strategic asset allocation rules with public rules (Allocate Smartly catalogue style).
Output: 30 candidates (all implementable on our ETF/futures/FRED data, some with a stated small adaptation).
Nothing was backtested on our engine in this step; no SPEC.md yet (pre-registration happens per strategy before computing).

## Files here
- URLS.txt: every source used.
- txt/keller_baa_4166845.txt: full text of Keller (2022) BAA paper (rules + PAA/BAA tables, in-sample/out-of-sample split).
- txt/faber_gtaa_2013.txt: Faber JPM 2018 revisit of GTAA (QTAA Aggressive = top 3 of 5 by average 1/3/6/12-month return with 10-month SMA filter).
- pytaa_strategy_README.md: rule summaries from the pyTAA package (Ivy, RAA, diversified GEM, VAA, KDA, GPM, TIOF, DAA, PAA, AAA, GEM, Quint, CDM).
- pdb/*.html, pdb_annual.json, pdb_postpub_summary.csv: PortfolioDB third-party ETF backtests (annual returns 1970..2026 YTD), parsed; post-publication CAGR and an annual-return Sharpe (mean/std of annual excess return over our T-bill series; crude, 7-18 annual points).
- web/as_urls.txt: Allocate Smartly post list (sitemap).

## Main evidence takeaways
1. Post-publication decay is the rule. On PortfolioDB's uniform ETF backtests, almost every TAA rule lagged a 60/40 portfolio on CAGR after its publication year (table below). Allocate Smartly members-only numbers were not accessible; public pages give rules and some backtest stats only.
2. 2022 broke bond-defensive TAA: strategies whose risk-off asset is IEF/TLT lost 8-24% in 2022 (Allocate Smartly 2022 review: TAA max DD -12.1% vs -2.8% in 2000-02 and -7.1% in 2007-08; low-rate-exposure strategies -8.0% vs -17.3%). BAA/HAA added DBC/TIP/BIL to the defensive menu after that, i.e. in-sample to 2022.
3. Best post-publication risk-adjusted records among the tracked set: GPM (2017-2025 CAGR 7.8%, annual SR 0.71 vs 60/40 9.7%/0.65), Tactical Permanent Portfolio (2016-2025 6.7%/0.68 vs 9.5%/0.68), Ivy/GTAA rotation types, KDA (2020-2025 7.8%/0.58 vs 9.2%/0.54). Worst: Quint Switching (2019-2025 1.1%, SR -0.13), Trend-is-our-Friend global (2.7%/0.17), VAA (G12 4.4%/0.20, G4 4.8%/0.28), Novell bond rotation (3.5%/0.21).
4. GEM: Petit (2026) free-data replication 1971-2026: CAGR 15.18%, Sharpe 0.83, MDD -21.66%, but all outperformance comes 1971-2009; 2010-2026 it lags the S&P 500 by 4.8 pp/yr.
5. Already tested by us and overlapping: S3 Faber GTAA (0.51 IS / 0.70 later) = GTAA5/Ivy timing; risk-parity long 30 futures (-0.09 / 0.34); 5 ETFs held (0.39 / 0.82); edge-study rpm_SB_* (ES+ZN stock/bond risk parity with static/CV/Faber/Moreira-Muir overlays, verified).
6. Execution caveat for every candidate: sources trade at the same month-end close as the signal; we decide at close d and fill at close d+1 (exec=next_close). Allocate Smartly reports a 1-day lag costs a little; month-end timing luck is material (consider tranching only as a pre-declared variant).

## PortfolioDB post-publication summary (third-party ETF backtests; annual-return Sharpe is crude)
| strategy | pub | post window | post CAGR | post annual SR | 60/40 same window | 2008-2024 CAGR / annual SR |
|---|---|---|---|---|---|---|
| GEM | 2012 | 2013-2025 | 8.3% | 0.54 | 9.5% / 0.79 | 6.7% / 0.51 |
| Diversified GEM | 2016 | 2017-2025 | 8.0% | 0.46 | 9.7% / 0.65 | 6.9% / 0.56 |
| Accelerating DM | 2018 | 2019-2025 | 10.3% | 0.51 | 10.9% / 0.69 | 12.1% / 0.88 |
| Composite DM | 2012 | 2013-2025 | 5.1% | 0.41 | 9.5% / 0.79 | 4.9% / 0.49 |
| VAA-G4 | 2017 | 2018-2025 | 4.8% | 0.28 | 9.2% / 0.57 | 6.2% / 0.53 |
| VAA-G12 | 2017 | 2018-2025 | 4.4% | 0.20 | 9.2% / 0.57 | 4.8% / 0.49 |
| DAA | 2018 | 2019-2025 | 7.0% | 0.40 | 10.9% / 0.69 | 6.4% / 0.58 |
| PAA | 2016 | 2017-2025 | 6.5% | 0.43 | 9.7% / 0.65 | 5.6% / 0.59 |
| GPM | 2016 | 2017-2025 | 7.8% | 0.71 | 9.7% / 0.65 | 6.6% / 0.73 |
| KDA | 2019 | 2020-2025 | 7.8% | 0.58 | 9.2% / 0.54 | 6.6% / 0.84 |
| AAA | 2012 | 2013-2025 | 6.9% | 0.62 | 9.5% / 0.79 | 7.6% / 0.79 |
| GTAA5 | 2007 | 2008-2025 | 4.7% | 0.50 | 8.1% / 0.66 | 4.4% / 0.47 |
| GTAA Agg 3 | 2013 | 2014-2025 | 7.4% | 0.51 | 9.0% / 0.72 | 7.2% / 0.61 |
| GTAA Agg 6 | 2013 | 2014-2025 | 6.5% | 0.50 | 9.0% / 0.72 | 6.8% / 0.58 |
| Ivy timing | 2009 | 2010-2025 | 4.8% | 0.56 | 9.7% / 0.93 | 4.4% / 0.43 |
| Ivy rotation | 2009 | 2010-2025 | 8.4% | 0.68 | 9.7% / 0.93 | 10.0% / 0.81 |
| Permanent | 1981 | 1982-2025 | 7.9% | 0.58 | 10.4% / 0.66 | 6.0% / 0.66 |
| Tactical Permanent | 2015 | 2016-2025 | 6.7% | 0.68 | 9.5% / 0.68 | 6.0% / 0.85 |
| Golden Butterfly | 2016 | 2017-2025 | 7.9% | 0.56 | 9.7% / 0.65 | 6.5% / 0.65 |
| All Weather | 2014 | 2015-2025 | 5.4% | 0.36 | 8.7% / 0.66 | 6.0% / 0.54 |
| Trend is our Friend (global) | 2013 | 2014-2025 | 2.7% | 0.17 | 9.0% / 0.72 | 2.5% / 0.29 |
| Novell bond rotation | 2015 | 2016-2025 | 3.5% | 0.21 | 9.5% / 0.68 | 4.2% / 0.46 |
| Quint Switching Filtered | 2018 | 2019-2025 | 1.1% | -0.13 | 10.9% / 0.69 | 5.1% / 0.42 |
| Papa Bear (Livingston) | 2018 | 2019-2025 | 10.1% | 0.55 | 10.9% / 0.69 | 7.3% / 0.56 |
| 60/40 | - | 2008-2024 | 7.8% | 0.63 | - | - |

## Data adaptations used across candidates
- VEA -> EFA, VWO -> EEM, BND -> AGG (BND from 2007), GSG/PDBC -> DBC, EZU -> VGK, RWO -> VNQ, BIL -> our T-bill series (rf_daily) when BIL is a comparator (extends start before 2007-05).
- Not in etf_daily, fetch free daily adjusted closes via yfinance if wanted: SCZ (ADM), IWN (Golden Butterfly, RAA), IWD (LAA), REM (Composite DM), RWX (AAA, KDA), BWX/BNDX (TIOF global, Novell). Each candidate states a no-fetch fallback.
- FRED side data (free CSV): UNRATE, RRSFS, INDPRO, BAA (Moody's Baa yield); use as of release (UNRATE: first Friday of next month; RRSFS ~mid next month; INDPRO ~mid next month) i.e. at month-end t use the value for month t-1 only (t-2 for RRSFS/INDPRO to be safe). Shiller monthly earnings (free) for the equity premium, lagged 4 months.

## Not included (considered)
Quint Switching (weak post-pub, rule fragile per Allocate Smartly), FAA (Keller & van Putten 2012; numbers not re-verifiable here), CAA (Keller/Butler/Kipnis), Faber 12-month high switch, RAA (Keller 2020), Papa/Mama Bear, Universal Investment Strategy (rules not verified), Fama-French alpha sector rotation (Allocate Smartly found no predictive ability).

Web search budget for the session ran out mid-task; remaining evidence came from direct fetches of known pages, the PortfolioDB pages and the GitHub API.
