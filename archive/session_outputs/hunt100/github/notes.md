# github label: search notes (2026-10-03)

Candidates with exact rules: `candidates.json` (21, built by `build_candidates.py`). Nothing was backtested here;
a SPEC.md per candidate must be written before any computation. No repo files touched.

## How the search ran
- GitHub search API, unauthenticated, 50 queries spaced 7 s (`search.sh`, `search2.sh`, `search3.sh`; raw JSON in `gh/`).
  Topic searches return mostly student repos with no results; the useful material came from a few well-documented repos,
  QuantConnect's strategy library and pysystemtrade.
- WebSearch was unavailable (session budget of 200 searches already used). Known URLs were read with WebFetch/curl only
  (Carver blog posts, raw READMEs, QuantConnect Tutorials HTML).
- Read in full or in the relevant part: 52 READMEs (`readme/`), 36 QuantConnect strategy-library write-ups (`qclib/*.txt`),
  28 QuantConnect/Quantpedia implementations listed by paperswithbacktest (`pwb/`, header comments only),
  Lean alpha docstrings (`lean/`), pysystemtrade rule files and rob_system config (`pstrules/`, `pst_rob_*`),
  Sepp's European/TSMOM/American system docstrings and qis `compute_ewm_long_short` (`sepp_*.py`, `qis_ewm.py`),
  the Beyond Passive replication SPEC (`phuazz_SPEC.md`), the Kestner replication config (`kestner_config.py`),
  the TrendLab pre-registered report (`trendlab_report.md`). Code was read for rules only; nothing is reused.

## Best-documented sources found
| Source | What it documents | Numbers |
|---|---|---|
| ArturSepp/TrendFollowingSystems | European LS(250,20), American, TSMOM systems on 84 futures | SR 1.10 net of costs 1960-2026; matched-lookback 0.47/0.50/0.55 net of 2/20 vs SG Trend 0.47 |
| phuazz/trend-replication-lab (Beyond Passive article) | 4-horizon clipped z-score trend, sector 4% then portfolio 10% vol, weekly | SR 1.03 gross / ~1.00 net, 1995-2026, 62 markets (scaffold not run on real data) |
| pysystemtrade + qoppac Dec 2021 | per-rule pooled pre-cost SR | carry 0.90-0.95, normmom up to 0.82, EWMAC up to 0.78, assettrend up to 0.70, skewabs 0.42-0.52, skewrv 0.22-0.33, relcarry 0.37, accel 0.06-0.18, relmomentum <=0.13, mr-wings -0.94, cs-mr -0.63; system SR 1.31 |
| akadigari/trendlab | pre-registered 10-ETF 12-1 long/flat | SR 0.70 net 2003-2026, 0.35 hold-out 2018+, 0.39 post-2013, fails timing null |
| toniker10/SPY-IBS | IBS<0.2 / >0.8 on SPY | SR 0.97 raw, 1993-2026, no costs, no OOS |
| hobinkwak/CTA-Position-Monitoring | Kestner (2020) SG Trend replication | 16/32/52-week ensemble, cap 1, R-squared > 75% vs SG Trend |
| QuantConnect strategy library / paperswithbacktest table | Quantpedia replications | TSMOM 0.576, paired switching 0.691, crude-oil 0.599, skewness commodities 0.482, Fed model 0.369, overnight+sentiment 0.369, January barometer 0.365, sector momentum 0.401, asset-class trend 0.502, return asymmetry 0.239, FX carry 0.254, commodity momentum 0.14, term structure 0.128, STR futures -0.05, WTI-Brent -0.199 |

## Evidence useful to sibling labels (not duplicated as candidates here)
- Zarattini-Aziz-Barbon intraday momentum (noise area, SPY): paper 2007-2024 SR 1.33; PazSheimy in-sample 2015-2024 SR 1.34, out-of-sample
  May 2024-Mar 2026 SR 0.39 (decline p < 0.001); giovannibrusco SPY+ES SR 1.11 2020-2026 with SR about 0 since 2025, walk-forward re-selection
  destroys value (0.57 vs 0.92), ES vs SPY correlation 0.97; francesco-nicolo: blackswan S4 SR 1.04, edge gone at 2.2 bp extra slippage per trade.
  (intraday_micro_noise_area_es)
- Overnight SPY 1993-2026: SR 0.95 gross, 0.71 at 1 bp round trip, 0 at about 4 bp; 2010-2026 SR 0.82; lost in 2020 and 2022 (NafizNoor1).
  (intraday_micro_overnight_hold_es)
- ETF cointegration pairs: DevMindset21 best of 6 variants SR 0.89 but Deflated Sharpe 0.48, NW t 0.99, negative at 20 bp; jen-dan 25 ETFs
  2010-2025 only 4 of top 10 pairs positive after costs, best XLB-XLI SR 0.39. Pairs trading not proposed.
- Databento CME futures (AJYS-Arc): absolute 12-month vol-adjusted trend SR 0.33 vs sector-neutral relative trend SR -0.16 (same engine, our kind
  of data). Corroborates weak post-2010 trend on CME-only universes.
- Commodity long-only best-maturity carry (billybraith17) 2008-2022: SR 0.19-0.20, maxDD -53%; carry already covered by edges carry_* series.
- Carver EWMAC on CFDs (ilahuerta-IA): SR 0.31 gross, 0.22 net of spread, negative after swap. Not applicable to futures.
- Fed model / yield gap: insignificant 2005-2025 (jacobmorrisva).

## Considered and not proposed
- Already covered by sibling labels or our own tests: TSMOM-12 (tested), Faber GTAA (S3), turtle/Clenow/Lemperiere/Baltas-Kosowski
  (trend_momentum), FX/commodity carry and term structure (edges carry_*), momentum x term structure (carry_value), COT pressure (carry_value),
  TOM / pre-holiday / OpEx / payday / FOMC / Treasury month-end (calendar_event, edges CAL_*), Keller/Antonacci TAA (allocation_rotation),
  VIX term structure, VIX stretch, oil shock (macro_regime), Gao and Zarattini intraday momentum, ORB, overnight (intraday_micro).
- Not implementable on our data: VIX futures basis (QC 198), VIX ETP strategies (LSV/HLSV), WTI-Brent spread, London breakout (needs hourly FX),
  Oil Money (NOK), options straddles, short-term reversal with futures volume/open interest filters.
- Documented negative or too weak: Carver mean reversion in the wings / cross-sectional mean reversion (negative standalone), relative momentum,
  acceleration; Lemperiere FX skew premia (QC -0.7%/yr); value-and-momentum across asset classes (0.155); gold Fed-model timing (no statistics,
  long gold through the low-yield era by construction); Lean lunch-break reversal, gas-leads-crude, mortgage-rate REIT alphas (no statistics).

## Red flags common to the GitHub record
- Most repo numbers are gross, raw Sharpe without risk-free subtraction, signal-close fills, single in-sample run.
- QuantConnect table numbers do not state the period; implementations start 2000 or 2004 and run to about 2023, gross.
- Honest repos (TrendLab, PazSheimy, giovannibrusco, DevMindset21) all show large post-publication or hold-out decay.

URLs: `URLS.txt`.
