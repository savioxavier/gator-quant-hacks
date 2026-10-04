# Google Scholar and Hugging Face: what we can actually use

*Gator Quant Hacks 2026, Systematic Trading track. Compiled Sat 2026-10-03, about 12:15 ET. The submission deadline is Sun 2026-10-04 10:00 ET.*

**Inputs:**
- Three literature passes: (1) robust strategies and backtest decay; (2) text, alternative data and LLM look-ahead; (3) ETF- and futures-specific signals.
- Two Hugging Face surveys: (1) prices, fundamentals and event data; (2) text corpora and models.

**Reconciled with:**
- `research/high_sharpe_literature.md`, the parallel review. It did not exist when this synthesis started and appeared at 12:04 ET. It has been read and is reconciled below.
- The frozen `FORWARD_TEST.md` (tag `forward-test-2026-10-03`).
- `note/quant_note.tex` and `research/idea_literature.md`.

**Source flags used in the tables:**
- **[F]** full text read;
- **[A]** abstract only;
- **[S]** secondary summary (blog, CXO, Alpha Architect, slides, search snippet).

Numbers marked [S] were not checked against the paper.

---

## 1. Bottom line

**Nothing new can be validated before the deadline.**
- **The holdout is used up.** The 2024-10-03 to 2026-10-02 window has been seen, so any idea scored on it is in-sample.
- **Clean data starts on 2026-10-06.** Even then the standard error of an annualised Sharpe is about √(252/n): about 2.0 after 3 months and 0.71 after 24 months.
- **So a new idea can only enter the submission as a frozen protocol,** never as evidence.

**Usable before the deadline:**
1. **Literature to sharpen the note's out-of-sample discussion.** One sentence plus references; the references do not count toward the five pages (section 5.5).
2. **A second forward-test file,** frozen before any post-2026-10-02 price is seen (section 5).

**Usable only later:** everything else, including the two candidates in section 5. They can be judged only on data from 2026-10-06 on, and realistically only after 24 months or more.

**Google Scholar was reachable, but not usable for systematic search.**
- **What Scholar returned.** Four WebFetch attempts across three passes hit no block or CAPTCHA:
  - one returned 10 results, among them Basis-Momentum with 193 citations;
  - two queries returned mostly low-citation student or SSRN items;
  - one returned a single snippet.
- **Where the systematic search ran instead:**
  - OpenAlex worked for about 40 lookups, then returned HTTP 429 for the rest of the day;
  - the Semantic Scholar Graph API returned 429, though one pass got through by retrying with pauses;
  - Crossref worked;
  - the arXiv API worked;
  - open PDFs were read locally (NBER, an AQR white-paper copy, Notre Dame, City University, Reading, EFMA, the Wharton discussant slides).
- **Blocked:** SSRN and ScienceDirect returned 403.
- **Conduct:** no CAPTCHA was solved or bypassed, and no gated dataset's terms were accepted.

**Is Hugging Face better for data? For this project, mostly not.**
- **Prices, futures, options, ETFs and factor returns.** The Hub mostly holds survivor-biased or unlicensed re-hosts of what Yahoo, Databento, Cboe and the Ken French library provide directly.
  - Verified: SIVB, FRC, TWTR, ATVI, XLNX and CELG are missing from the two most-downloaded stock-price sets.
  - The largest set's own card admits that only 3.5% of its symbols are delisted, against about 44% of US common stocks that ever traded.
- **HF is better in three narrow places:**
  - **Point-in-time event data.** The new ZipLime family: EDGAR acceptance-second timestamps, macro first prints with embargo times, CFTC Commitments of Traders (COT) release dates, FOMC release instants. The information is the same as from SEC, BLS, CFTC and the Fed, but the timing is already engineered. These sets are one month old and unaudited.
  - **Leakage-free language models.** ChronoBERT and ChronoGPT yearly vintages (1999-2024), DatedGPT (2013-2024), and FinBERT, trained before 2019. For these models HF *is* the primary source.
  - **A factor-construction multiverse** for robustness checks (tidy-finance/factor-library).
- **Neither forward-test candidate in section 5 needs HF data.** HF supplies only an optional event-day diagnostic.

**The best-evidenced idea is already in our test.**
- **Trend is already there.** Volatility-scaled time-series momentum (TSMOM) is a sleeve of F1, and on 20 CME futures it is the frozen TSMOM_F benchmark.
- **Candidate 1 is the increment.** It is the published 1/3/12-month trend blend on a broader futures set, identical to the parallel review's S1.
- **Candidate 2 is the one new information source:** market intraday momentum on ES and ZN from Databento 1-minute bars (Baltussen et al. 2021). The parallel review did not assess this.
- **Not recommended** (section 5.4): stand-alone carry, text or LLM sentiment, and macro timing.

**Our out-of-sample failure is the base rate, not an anomaly.**
- **F1's gross Sharpe fell 72%,** from 1.35 to 0.38.
- **Bank risk-premia indices fell a median 73%** from backtest to live (Suhonen et al. 2017).
- **Published predictors lose 26% of their returns after the sample ends and 58% after publication** (McLean & Pontiff 2016).
- **Systematic strategies keep about half their in-sample performance** (Falck, Rej & Thesmar).
- **Calendar effects tradable with daily data die fastest.** The pre-FOMC drift was gone after 2015 (Kurov et al. 2021).
- **This is the strongest use of the literature for the note today.**

---

## 2. Papers worth using

### 2a. Priors for the note: decay base rates and statistics

| Paper | Idea | Out-of-sample evidence | Data needed | Usable by us? |
|---|---|---|---|---|
| McLean & Pontiff 2016, *J. Finance* | How 97 published predictors perform after their sample ends and after publication | Returns 26% lower out of sample, 58% lower after publication; bigger in-sample returns decay more [A] | None | **Yes.** Already cited in the note |
| Falck, Rej & Thesmar, *Quantitative Finance* 2022 ("When do systematic strategies decay?"; the parallel review cites the arXiv 2105.01380 version, assumed to be the same work, not verified) | What predicts decay: overfitting versus arbitrage capital | About 50% of in-sample performance survives out of sample (72 strategies); the parallel review gives about 0.57×. Complexity and outlier sensitivity predict decay; arbitrage proxies are marginal [A/S] | None | **Yes.** Base rate plus design rule: simple, outlier-robust signals |
| Suhonen, Lennkh & Perez 2017, *JPM* | Backtest versus live Sharpe of 215 bank "alternative beta" indices | Median Sharpe 1.20 in backtest, 0.31 live (−73%). The most complex strategies lost 30 percentage points more than the simplest [S] (both reviews agree on the figures) | None | **Yes.** F1's −72% gross drop matches the median |
| Jensen, Kelly & Pedersen 2023, *J. Finance* | Bayesian re-test of 153 equity factors | Most replicate and work across 93 countries; alpha is about 47% lower after the original samples (per the parallel review) [A] | JKP factors (free) | Partly: a prior only |
| Goyal, Welch & Zafirov 2024, *RFS* | Re-test of 46 equity-premium predictors through 2021 | More than a third of the new variables are no longer significant even in sample; half of the rest fail out of sample [A] | FRED | Partly: warns off macro timing |
| Kurov, Wolfe & Gilbert 2021, *FRL* | Post-publication check of the pre-FOMC drift | Essentially gone after 2015 [A] | None | **Yes.** The closest analogue to F1's calendar-flow sleeves |
| Huang, Li, Wang & Zhou 2020, *JFE* | Is TSMOM real predictability? | Little asset-by-asset evidence; profits about equal to a sample-mean strategy [A] | Futures | **Yes.** Benchmark choice for any trend claim |
| Marshall, Cahan & Cahan 2008, *JBF* | 7,846 technical rules on 15 commodity futures | After a data-snooping correction, profits vanish in 14 of 15 [S]. Szakmary et al. 2010 disagree, so the evidence is mixed | None | Yes, for framing |
| Hollstein, Prokopczuk & Tharann 2021, *QJF* | Equity-style anomalies in 26 commodity futures | Commodity momentum is clearly weaker after 2000 [F] | None | Partly |
| Ilmanen, Israel, Moskowitz, Thapar & Lee 2021, *JOIM* | Factor premia over a century; factor timing | Premia about 30% lower out of sample. Timing shows modest predictability that frictions likely erase [S] | AQR datasets | **Yes.** Argues against timing overlays |

### 2b. Strategy evidence for futures and ETFs

| Paper | Idea | Out-of-sample evidence | Data needed | Usable by us? |
|---|---|---|---|---|
| Hurst, Ooi & Pedersen 2017, *JPM* (AQR white paper 2014) | 1/3/12-month volatility-scaled TSMOM across 67 markets | **1880-2013:** net Sharpe 0.77 after simulated costs and 2/20 fees, positive in every decade; 0.62 in 2000-13 [F, 2014 version]. **Parallel review:** 0.41 for 2010-16; AQR's TSMOM factor earned 0.39 gross after May 2012 (verifier's calculation). One pass read the authors' advice to plan on about 0.4; the parallel review lists that statement as unverified | Databento daily futures | **Yes → candidate 1** |
| Moskowitz, Ooi & Pedersen 2012, *JFE* | 12-month TSMOM | See the row above | Same | Already in F1 and TSMOM_F |
| Baltussen, Da, Lammers & Martens 2021, *JFE* | The return from the previous close to 30 minutes before the close predicts the last 30 minutes (hedging demand from dealers and leveraged ETFs) | Dec 1974-May 2020, Table 6, gross, equal-weight within class: **equity-index futures 6.86%/yr at 3.96% volatility, Sharpe 1.73; government bonds 1.62**; 0.87-1.73 across classes. Regressions similar in 1974-99 and 2000-20. Authors say 1 tick on S&P futures still leaves a positive net Sharpe. No post-2020 test [F] | Databento `ohlcv-1m` for ES and ZN | **Yes → candidate 2** |
| Gao, Han, Li & Zhou 2018, *JFE* | The first half-hour predicts the last half-hour (SPY) | 1993-2013 Sharpe 1.08 gross [S]; both reviews flag it unverified | Intraday bars | Partly |
| Li, Sakkas & Urquhart, *J. Financial Markets* | Intraday momentum in 16 countries | Recursive out-of-sample test from Oct 2010 works in most; global portfolio 1.12-1.77 gross [F] | Non-US intraday data | No (cash indices, not tradable) |
| Koijen, Moskowitz, Pedersen & Vrugt 2018, *JFE* | Carry across asset classes | **In sample:** diversified carry 1.41 gross (2012 working paper, through 2011); 1.20 in the published version per the parallel review. **After:** AQR's four-asset futures carry earned **0.07 gross from Jan 2012 to Feb 2026** (parallel verifier's calculation), and the live G10 carry ETF (DBV) lost money | Databento front and second contracts plus expiries | **Not as a stand-alone strategy** (section 5.4) |
| Fuertes, Miffre & Rallis 2010, *JBF* | Commodity momentum × term structure | 22-month holdout (2007-08): reward-to-risk 0.86-1.23 [F] | Databento | Low priority (momentum weaker after 2000) |
| Boons & Porras Prado 2019, *J. Finance* | Basis-momentum in 21 commodities | 18.38%/yr high-minus-low (1959-2014). Out-of-sample tests on FX and stock indexes; no post-publication test found [F] | Databento | Low priority (about 4 names per leg, monthly) |
| Pitkäjärvi, Suominen & Vaittinen 2020, *JFE* | Cross-asset TSMOM: bonds predict stocks | Sharpe more than 40% above plain TSMOM, in sample 1980-2016 [A]. The stock-bond correlation has been positive since 2021 | ES/ZN or SPY/IEF | Later, maybe |
| Harvey et al. 2018, *JPM* | Volatility targeting on 60 assets, 1926-2017 | Raises the Sharpe only for risk assets; cuts tails in every class [A] | None | **Yes.** Supports the note's plain 8% target |
| Cederburg, O'Doherty, Wang & Yan 2020, *JFE* | Real-time test of volatility-managed portfolios | They do not beat unmanaged portfolios out of sample [A] | None | **Yes.** Supports "no brake" |
| Ehsani & Linnainmaa 2022, *J. Finance*; Gupta & Kelly 2019, *JPM* | Factor momentum | Gross Sharpe 0.98 (1964-2015) [F] and 0.84 [S], both in sample | French or JKP factors; factor ETFs untested | Not now |
| Keloharju, Linnainmaa & Nyberg 2016, *J. Finance* | Same-calendar-month seasonality | Commodities 0.93%/month (t = 1.93), 2-3 names per leg [F] | None | No (no power in a forward test) |
| Simon & Campasano 2014, *J. Derivatives* | VIX futures basis | 2006-11, 82 short trades, short-volatility tail risk [F] | Cboe VX | No |
| Durham 2013, NY Fed SR 657 | Treasury curve momentum | Information ratio "up to" 0.79-1.01 [A] | None | No |

### 2c. Text, alternative data and LLM look-ahead

| Paper | Idea | Out-of-sample evidence | Data needed | Usable by us? |
|---|---|---|---|---|
| Tetlock 2007, *J. Finance* | WSJ pessimism predicts next-day index returns | In sample; the effect reverses within days [A] | Paid text | No |
| Garcia 2013, *J. Finance* | NYT word sentiment, 1905-2005 | 12 bp per standard deviation, in recessions only [A] | Paid text | No |
| Ke, Kelly & Xiu 2019, NBER 26186 (SESTM) | Supervised news sentiment | Rolling out-of-sample test 2004-17: gross Sharpe 4.29 equal-weight vs **1.33 value-weight**. Large caps finish reacting within one day. Net equal-weight peak 2.30 [F] | Paid Dow Jones newswire (FNSPID is a free proxy) | Partly. Large-cap entry at the daily close is weak |
| Chen, Kelly & Xiu 2022, SSRN 4416687 | LLM embeddings of news | Net Sharpe about 1.5 per discussant slides; lower for large firms [S] | Firm news | Partly |
| Lopez-Lira & Tang, arXiv 2304.07619 / *JFE* 2026 | ChatGPT headline scores | Sample is after the model's knowledge cutoff. Gross Sharpe **decayed from 6.54 (2021Q4) to 1.22 (Jan-May 2024)**; 1.29 at 10 bp; unprofitable at 20 bp round trip [F] | Firm headlines | Partly. A clean example of decay |
| Chen, Tang, Zhou & Zhu 2025, arXiv 2502.10008 | GPT-3.5 on WSJ headlines, monthly | Out-of-sample R² 1.17%; timing Sharpe 0.51 vs 0.30, mostly inside the model's training window [F] | Paid headlines | No |
| Adämmer & Schüssler 2020, *Rev. Finance* | News topics forecast the monthly equity premium | R²_OOS 6.52% (1999-2018) [A] | Newspaper archive | No (monthly horizon) |
| Cohen, Malloy & Nguyen 2020, *J. Finance* ("Lazy Prices") | Year-over-year change in 10-K/10-Q text | Up to 188 bp/month alpha (1995-2014), in sample [A] | EDGAR | No (quarterly horizon) |
| Jiang, Kelly & Xiu 2023, *J. Finance* | CNN on price charts | Large-cap gross Sharpe about 1 [S] | Survivorship-free OHLCV | No |
| Lachanski & Pav 2017, *Econ Journal Watch* | Replication of "Twitter mood predicts the stock market" | Failed, and adding 2007 kills the effect [F] | None | Yes, as a caution |
| Glasserman & Lin 2024, *JFDS*; Sarkar & Vafa 2024; Lopez-Lira, Tang & Zhu 2025; He, Lv, Manela & Wu 2025 (Chrono models); Yan et al. 2026 (DatedGPT); Gao, Jiang & Yan 2025 (LAP) | Look-ahead and memorization in LLMs, and how to fix them | See section 4.1 | None | **Yes.** Methods only |

**Text-signal verdict.** For large caps and indices at daily frequency after costs, the evidence is discouraging:
- **Firm-news alpha sits in small caps and in the first minutes to hours** after the news.
- **Index-level text signals work mainly at monthly horizons and in down markets.**
- **Expect no reliable daily index edge from news sentiment.**

---

## 3. Hugging Face datasets worth using

Every dataset below was checked through the Hub API and datasets-server, or by sampling files. Download counts are 30-day figures inflated by bots, so they are not a quality signal.

### 3a. Event and point-in-time data: worth using, always with a primary-source fallback

| Dataset | Content | Coverage & updates | License | Point-in-time quality | Verdict |
|---|---|---|---|---|---|
| [ZipLime/us-economic-events](https://huggingface.co/datasets/ZipLime/us-economic-events) | First-print and revised US macro releases (NFP, CPI, PPI, claims, GDP, PCE and others) with embargo-lift time and BLS archive links | 12 release families, 55 series. Datasets-server shows knowledge dates from 2010-01-07 to **2026-10-02 12:30 UTC**, so the jobs report was ingested the same day. (The text survey read the card as ending 2026-09-10; the server stats are the more direct check.) | apache-2.0 | **Good.** March 2020 NFP vintages −701k, −881k, −1,373k and −1,683k, each linked to BLS, match the record. 2026 vintages could not be verified | **Use** for candidate 2's macro-day diagnostic, with the BLS calendar and ALFRED as fallback. No consensus forecasts are described, so it cannot measure "surprises" without our own forecast |
| [ZipLime/fomc-events](https://huggingface.co/datasets/ZipLime/fomc-events) | FOMC statements, minutes, SEP/dots and press conferences as separate information arrivals; decisions, votes, dissents; 414 full texts | Jan 2007 to now, with meetings scheduled through Dec 2027. Updated 2026-10-02 | apache-2.0 | **Excellent.** Uses the printed embargo time where one exists (141 exact); otherwise the timestamp is set to 23:59:59 Washington time, so it can be late but never early. Minutes get their own release instant (median 21 days after the meeting) | **Use** as the FOMC calendar for the diagnostic (federalreserve.gov fallback) |
| [ZipLime/sec-8k-events](https://huggingface.co/datasets/ZipLime/sec-8k-events) | 8-K items, earnings releases (item 2.02 plus EX-99 text), CIK-to-ticker map with validity dates | Metadata from 2004-08-23; **item text only from 2026-01-01**. Cron twice a day | apache-2.0 on the compilation | **Excellent.** Timestamps to the EDGAR acceptance second; documents and fixes EDGAR's ambiguous "Z" times | The best live HF feed for any forward text test. Not used in the candidates (section 5.4) |
| [ZipLime/earnings-calendar](https://huggingface.co/datasets/ZipLime/earnings-calendar) | Earnings releases detected from 8-Ks, with XBRL figures and a seasonal SUE (no analyst consensus) | 2003-04-25 to 2026-09-04; rebuilt weekly | apache-2.0 | Acceptance time to the second, first tradeable session, ticker as of the filing day | Research only. Post-earnings drift would need survivorship-free stock prices, which no free HF set has |
| [ZipLime/company-fundamentals](https://huggingface.co/datasets/ZipLime/company-fundamentals) | As-filed XBRL fundamentals with restatements kept | 2009-04-15 to 2026-06-30 (card); weekly | apache-2.0 (SEC DERA source) | knowledge_date is the EDGAR acceptance time. Values must be coalesced column by column, not taken from the latest row | Not needed for ETFs or futures |
| [ZipLime/security-master](https://huggingface.co/datasets/ZipLime/security-master) | Ticker-to-CIK history and CUSIP bridge | Mostly 2006 onward | apache-2.0 | Partly (filing-based dates). The TWTR ticker-reuse spot check passed | Only for single-stock work |
| [ZipLime/commitments-of-traders](https://huggingface.co/datasets/ZipLime/commitments-of-traders) | CFTC COT positions with the actual release time | 2010-01-05 to 2026-09-08 (card); 762 markets | apache-2.0 | Handles late releases, e.g. the 30 Sep 2025 report published 19 Nov 2025 after the shutdown | Optional positioning diagnostic |
| [ZipLime/us-treasury-events](https://huggingface.co/datasets/ZipLime/us-treasury-events) | Treasury auctions and yield curves | Auctions from 1979 (minute precision since 2008) | apache-2.0 | Good since 2008 | Cross-check for sleeve C's Fiscal Data auction record |
| ZipLime/insider-trading, ZipLime/congress-trading | Form 4 trades; STOCK Act trade reports | Insider data stops at 2026-06-30. Congress data runs from 2013 with paper filings missing | apache-2.0 / cc0 | Keyed on filing date | Not timely, or too thin |
| [tidy-finance/factor-library](https://huggingface.co/datasets/tidy-finance/factor-library) | 179 equity signals × 4.1M portfolio-construction choices, monthly | 1960-01 to 2024-12; static | cc0 | Not applicable (monthly returns, survivorship-free by construction) | Research: a multiverse check for factor ideas. Not applicable to F1 |
| incrediblecrab/federal-reserve-beige-book; vtasca/fomc-statements-minutes | Fed text | Live | other / cc | Day precision | Only one Beige Book (2026-10-14) falls in the early forward window |

### 3b. Text corpora

| Dataset | Content | Coverage & updates | License | Point-in-time quality | Verdict |
|---|---|---|---|---|---|
| AlphaDojo/dojo_stock_news | Ticker-tagged headlines via nasdaq.com | 3.98M rows; US history from about Jan 2025. Live: re-uploaded daily (one survey saw about 09:20 and 22:40 UTC), overwriting in place | apache-2.0 declared over third-party content | **Weak.** US dates are day-only; the same headline appears under unrelated symbols; heavy duplication | Only with our own archived daily snapshots. Not recommended |
| openalphalab/gdelt-news | GDELT news reconstruction | Live from 2026-09-22; backfill gap from 2020-01 to 2026-04 | Unspecified | Minute-level observation time, which is not a publication time | No |
| Brianferrell787/financial-news-multisource (ungated mirror: idleengine) | 24 news corpora, 57M rows, 1990-2025 | Static | Gated, non-commercial, no redistribution | Mixed; day-level rows carry a next-open guard | Historical exploration only. Terms not accepted |
| Zihan1004/FNSPID | 15.7M news records, 4,775 S&P 500 firms, 1999-2023 | Static | CC BY-NC 4.0 | Mixed; many rows have no article body | Historical only |
| kurry/sp500_earnings_transcripts | 33,362 call transcripts, 2005-10 to 2025-05 | Static | MIT declared, doubtful (Capital IQ IDs) | Call time given; universe is S&P 500 as of May 2025, so survivor-biased | Historical only |
| TeraflopAI/SEC-EDGAR | 8.06M filings, about 295 GB | Static (2026-04-17) | apache-2.0 | Filing date only | No (size and timestamps) |
| BatuhanECB/sec-filings-forward-return-2026 | Filing text with forward-return labels | Static | other | Card flags survivorship | A sobering prior: TF-IDF text gets AUC 0.500 and IC −0.006 for 20-day excess returns in 2023-26 |
| emilpartow/reddit_finance_posts_sp500 | 432k Reddit posts, 2008-2025 | Static | cc-by-4.0 | Scores are July 2025 snapshots, so using them is look-ahead | No |

### 3c. Models (HF is the primary source here)

| Model | Training data | License | Leakage | Verdict |
|---|---|---|---|---|
| [ProsusAI/finbert](https://huggingface.co/ProsusAI/finbert) | Reuters TRC2 2008-10, Financial PhraseBank, BERT's pre-2019 corpus | Not stated | Clean for a 2026 forward test; mild leakage in 2006-24 backtests | The safest cheap scorer |
| [manelalab Chrono models](https://huggingface.co/manelalab/chrono-bert-v1-20241231) (ChronoBERT, ChronoGPT and instruct versions; 78 models) | One vintage per year-end, 1999-2024 | MIT | None if year Y is scored with vintage Y−1 | The right tool for any historical text backtest |
| datedgpt/datedgpt-{2013..2024}-{base,instruct} | 1.3B models trained from scratch, ~100B tokens each, annual cutoffs | Not seen | None by construction | Alternative vintages; also the LAP diagnostic paper |
| FinText Chronos/TimesFM vintages (360 models) | Excess-return series up to year YYYY | apache-2.0 | None if a vintage before the test year is used | Low priority |
| gtfintechlab/FOMC-RoBERTa | FOMC text up to about 2022 | cc-by-nc-4.0, gated | Look-ahead before 2023 | Forward use only |
| NeoQuasar/Kronos-base | 12B+ K-line bars; cutoff not stated | MIT | Unknown, so backtests may be contaminated | Low priority |

### 3d. Prices and market data: not better than primary sources

| Dataset | Content | Coverage & updates | License | Point-in-time quality | Verdict |
|---|---|---|---|---|---|
| defeatbeta/yahoo-finance-data | Yahoo scrape: prices, statements, news, transcripts | Updated daily; price depth unmeasured | odc-by over Yahoo content | Statements keyed on period end, not filing date; today's tickers (FB absent, META present); delisted names missing | Use Yahoo directly |
| paperswithbacktest/Stocks-Daily-Price | US OHLCV, 7,764 symbols, 1962 to 2026-08 | Monthly | other (subscription) | Card admits 3.5% delisted symbols vs about 44% in reality | No |
| AYUSHKHAIRE/all-stock-market-data-daily-updates | 17,683 ticker CSVs, 2010-2026 | Daily | cc0, source unstated | Survivor-biased (SIVB, FRC, TWTR, LEH and others missing) | No |
| thillsss/SPX-MES-VIX-data | VIX daily from 1990; SPX/MES/MNQ 1-minute bars | Current | None | Roll method undocumented | No (Cboe and Databento are better) |
| lynx1231/historical-futures-data-sample; Khanhpham1992/msj-21 es-futures-1m | Vendor sample; ES 1-minute bars with no dataset card | Static | None | Chicago wall-clock stored as epoch ms; provenance unknown | No (Databento) |
| gauss314/options-IV-SP500 | Daily implied-volatility summaries | 2019-10-14 to 2023-07-28; static | apache-2.0 | Dirty historical-volatility columns | No |
| voigtstefan/sp500 | SPY order-book aggregates at 5-second intervals | 2007-06 to 2025-10; static | MIT | Good, but a single instrument | No (ends before the forward window) |
| jwigginton/index-constituents-sp500 | 503-row S&P 500 snapshot (about Feb 2024) | Static | None | Survivor-biased | No |
| HaiwenWang/sp500-pit-benchmark | Point-in-time S&P 500 bars | Gated; card forbids redistribution (CRSP-derived) | Restricted | Unverifiable | **Do not use** |
| krishnakamath/fama_french_data | Stale factor copy to 2025-11 | Static | None | None | No (Ken French library) |

### 3e. Hugging Face versus primary sources

| Need | Primary source | Best HF option | Which to use |
|---|---|---|---|
| ETF and stock daily prices | Yahoo (yfinance), logging retrieval time | defeatbeta, AYUSHKHAIRE, paperswithbacktest | **Primary.** HF copies are survivor-biased re-hosts of unknown provenance that add a middleman |
| CME futures, daily and intraday | Databento GLBX.MDP3 (already in the pipeline) | Vendor samples and unlicensed text files | **Primary** |
| VIX and VX futures | Cboe | thillsss | **Primary** |
| Macro releases | FRED/ALFRED, BLS | ZipLime/us-economic-events | **HF adds exact release times** (ALFRED vintages are day-dated). Shorter history (2010 on), new pipeline. Use both |
| SEC filings and fundamentals | EDGAR (free) | ZipLime 8-K, fundamentals, earnings | Same information. **HF saves the engineering and gets acceptance timing right.** Spot-check it |
| COT positioning | CFTC | ZipLime COT | HF aligns release dates. Either works |
| Factor returns | Ken French, AQR Data Library, JKP | tidy-finance (multiverse), krishnakamath (stale) | **Primary for returns.** tidy-finance is unique as a robustness grid |
| News text | No free primary source with history | FNSPID, multisource (static); AlphaDojo (live, weak) | HF is the only free option. Quality and non-commercial licences limit it |
| Language models | n/a | ChronoBERT, DatedGPT, FinBERT | **HF is the primary source** |

**Search tip.** The `/api/datasets?search=` endpoint matches repository names only and missed most useful sets. The full-text endpoint (`https://huggingface.co/api/search/full-text?q=...&type=dataset`) found ZipLime, tidy-finance and the point-in-time sets.

---

## 4. Look-ahead traps for text/LLM signals and HF datasets, and how to avoid them

### 4.1 Model training-data leakage

**What the papers find:**
- **Memorization.** LLMs recall exact pre-cutoff economic values. "Pretend it is year X" prompts and entity masking do not stop this, because models reconstruct dates and firms from context. Embeddings are affected too. Inside the training window, skill cannot be separated from memory (Lopez-Lira, Tang & Zhu 2025). No recall is observed after the cutoff.
- **Direct lookahead tests** find bias in earnings-call and election tasks. The recommended fix is models pretrained only on text from before the analysis period (Sarkar & Vafa 2024).
- **Distraction.** General knowledge of a named firm skews its sentiment score, more so for large caps. Replacing names with a placeholder improved results in and out of sample (Glasserman & Lin 2024). This is in partial tension with the memorization finding: masking helps against distraction, not against recall.
- **The size of the bias depends on the task.**
  - DatedGPT finds that models whose training covers the outcome period earn a "lookahead premium" of 26.4 bp per standard deviation (significant at 1%).
  - The Chrono paper finds the bias modest in its news-return test: ChronoBERT 4.80 vs Llama 3.1-8B 4.90, not significantly different.
  - Do not assume either way; use vintage models.

**How to avoid it:**
1. **Evaluate only after the training cutoff.** A forward test on data from 2026-10-06 meets this for every model, provided the weights, prompt and code hash are frozen. Use a fixed-weight local model, because API models change silently.
2. **For any historical check, score year-Y text with a vintage whose cutoff is the end of year Y−1:** ChronoBERT/ChronoGPT (1999-2024) or DatedGPT (2013-2024).
3. **Mask firm names and tickers** to reduce distraction. Do not treat masking as a fix for memorization.
4. **Run the Lookahead Propensity (LAP) diagnostic** (Gao, Jiang & Yan 2025) on any backtest that uses a modern LLM.
5. **Treat LLM-scored datasets as contaminated.** HYL/NASDAQ-News-Multi-LLM-Scores, for example, re-scores FNSPID articles with LLMs trained after those articles were written.
6. **The same applies to time-series foundation models.** Kronos, chronos-2 and timesfm have undocumented cutoffs; FinText's yearly vintages avoid the problem.
7. **FinBERT** (Reuters 2008-10 plus PhraseBank) leaks only mildly into 2006-24 backtests and is clean for the forward test.

### 4.2 Timestamps and back-filled data

- **EDGAR "Z" times.** Many acceptanceDateTime values marked "Z" are actually Eastern time. Read as UTC, they date filings 4-5 hours early. Use the SGML ACCEPTANCE-DATETIME field or ZipLime's corrected knowledge_date.
- **Date-only feeds.** These include AlphaDojo's US news, Yahoo news, TeraflopAI filing dates and Beige Book edition dates. Lag them to the next session after the stated date.
- **FOMC minutes** are filed under the meeting date but released about 21 days later (range 19-60).
- **COT** is dated Tuesday but released Friday, and sometimes weeks late (the 2025 shutdown backlog).
- **Insider and congress trades.** Key on filing date, not transaction date. The House Clerk also rewrites its historical catalogs: 4,305 filings vanished between April and August 2026.
- **Macro revisions.** Use first prints: March 2020 NFP was first printed at −701k and later revised to −1,683k.
- **Fundamentals.** Key on filing (acceptance) date, not period end; defeatbeta's statements use period end.
- **Engagement counts** such as Reddit score and comment counts are scrape-time snapshots.
- **Observation time is not publication time.** GDELT observation times are not publication times, and its backfill is still running, so rows appear later than their timestamps suggest. **General rule: record the first-seen time yourself.**
- **HF datasets are mutable.** AlphaDojo overwrites itself; ZipLime rebuilds weekly. When loading, pin the dataset revision (commit hash) with the `revision=` argument. For anything used in a forward test, archive a daily snapshot with retrieval time and SHA-256. Yahoo and the Ken French library also revise history; `FORWARD_TEST.md` already notes this for Yahoo.

### 4.3 Survivorship and universe construction

- **Price re-hosts miss delisted names.** HF price sets omit them (verified above), and one card admits 3.5% delisted symbols against about 44% in reality.
- **No usable point-in-time S&P 500 membership exists on HF.** Every "constituents" set is a current snapshot; the one true point-in-time set is gated and forbids redistribution.
- **Today's ticker maps leak.** FB is absent and only META is present. Tickers get reused: TWTR belonged to another company before Twitter. Use CIK histories (ZipLime/security-master) for any single-stock work.
- **Transcript and filing benchmarks use present-day universes.** One transcript set uses S&P 500 membership as of May 2025. One filing benchmark uses current large caps, and its 120-day excess return drifts to about +2.6% purely from survivorship.
- **Our project avoids most of this** by trading ETFs and futures, and the forward test fixes its universe at the freeze.

---

## 5. Recommendation

### 5.1 Ground rules

**Nothing here can be validated on the 2024-2026 window.** It has been seen and was used to judge F1. Anything chosen or tuned on 2024-26 performance is in-sample, and 2006-2024 has been studied closely too. The only clean evidence starts 2026-10-06.

**Files:**
- **Do not touch forward test 1.** Its files are `src/forward.py` and `scripts/run_forward.py`, under tag `forward-test-2026-10-03`.
- **Put the new test in new files:** `FORWARD_TEST_2.md`, `src/forward2.py` and `scripts/run_forward2.py`.

**When to freeze:**
- **The parallel review says** to freeze before the Mon 2026-10-05 close.
- **I recommend a stricter cutoff:** commit and tag before CME Globex reopens on Sun 2026-10-04 at 18:00 ET. In practice, freeze with the hackathon submission before 10:00 ET.
- **Why:** this way nobody has seen any post-Oct-2 price when the rules are chosen.
- **Both candidates count returns from Tue 2026-10-06,** the same first day as forward test 1.

**History comes after the freeze.** Compute historical context (2010-06 to 2026-10) only in a later commit, labelled as context, exactly as `forward/historical_context.json` did for F2.

**Multiple testing.**
- Within the new file, use α = 0.05 divided by the number of hypotheses in it.
- A claim that spans both forward tests uses α = 0.05 divided by the total: 3 hypotheses in test 1 plus those in test 2.
- Realistically nothing will reach significance in 24 months: a true Sharpe of 0.5 over 2 years gives t ≈ 0.7.

**Pick at most two strategies in total.** The parallel review proposes three (S1 trend, S2 equity plus trend, S3 Faber GTAA). I recommend **S1 plus intraday momentum**:
- S2 contains S1;
- S3 overlaps trend;
- intraday momentum is the only candidate that adds a different information source.

If the user prefers S2, because equity beta is acceptable to the judges, it **replaces** candidate 1 rather than adding to it.

### 5.2 Candidate 1: broad CME trend, 1/3/12-month blend (identical to the parallel review's S1)

**Rule sketch** (freeze exact values in `FORWARD_TEST_2.md`):

- **Universe (Databento GLBX.MDP3, `ohlcv-1d`, continuous `.v.0/.v.1`):**
  - The 20 TSMOM_F roots: ES NQ RTY YM ZT ZF ZN ZB CL NG GC SI HG 6E 6J 6B 6A 6C ZC ZS.
  - Plus UB HO RB PL ZW ZL ZM LE HE 6S.
  - Before freezing, confirm each added root has daily bars; drop and record any that do not.
  - Delisting rule: as in forward test 1.
- **Returns:** the existing within-contract construction. Roll on the vendor's front-contract change, charge one round trip per roll, and treat the position as fully collateralised at the T-bill rate (FRED DTB3).
- **Signal:** at each month-end close, s = (sign(r₂₁) + sign(r₆₃) + sign(r₂₅₂)) / 3, where r_k is the cumulative futures excess return over the past k trading days.
- **Sizing:**
  - wᵢ = sᵢ × (0.40/σᵢ)/N, where σᵢ is an annualised EWMA daily volatility (centre of mass 60 days).
  - Scale the book to 10% ex-ante volatility using the trailing 252-day covariance.
  - Cap gross exposure at 3×.
- **Execution and costs:**
  - Trade at the next session's close.
  - One-way costs: 1.5 bp; 5 bp for NG, RTY, ZC, ZS, 6A, 6C and every added root except UB and 6S.
  - Also report the result at 2× costs.
- **Tracked benchmarks (no hypothesis):**
  - the frozen TSMOM_F;
  - a volatility-scaled long-only book on the same universe, because Huang et al. (2020) show trend profits look like a long-bias or sample-mean rule.

**Hypotheses:**
- **H-S1:** forward net Sharpe > 0.
- **Secondary:** the paired difference from TSMOM_F. It is not expected to be detectable, since the two are highly correlated.

**Data:** Databento daily bars already in the pipeline; the extra roots need one small pull (check `metadata.get_cost` first). FRED for the T-bill. **No Hugging Face data is needed.**

**Why this one:**
- **The best long-horizon and post-publication record of any premium in either review.**
  - Every decade since 1880 was positive.
  - 2000-13: 0.62 net (Hurst et al.).
  - 2010-16: 0.41 net of fees (parallel review).
  - AQR's TSMOM factor: 0.39 gross after May 2012 (parallel verifier's calculation).
- **It differs from the frozen TSMOM_F where the literature says it matters:** breadth and the multi-horizon signal.
- **It keeps to the simplicity rule** from Falck et al. and Suhonen et al.: no fitted parameters.

**Expected realistic net Sharpe: 0.2-0.5, central about 0.3-0.4.**
- **Parallel review:** 0.2-0.6, central 0.4.
- **Our own anchor argues for the lower half.** TSMOM_F, run on 20 of the same contracts, earned **0.28 in-sample (2011-2024) and 0.14 out-of-sample**.
- **The 24-month interval is wide.** At a true Sharpe of 0.4, a 24-month Sharpe falls between about −0.8 and +1.6 with 90% probability.

### 5.3 Candidate 2: market intraday momentum on ES and ZN (Baltussen, Da, Lammers & Martens 2021)

**Rule sketch:**

- **Instruments:** ES and ZN, front contract by volume (`.v.0`), with the same roll handling.
- **Data:** Databento GLBX.MDP3 `ohlcv-1m`, forward window only, pulled after each checkpoint (check `metadata.get_cost` first). Convert UTC to America/New_York. The existing pipeline has only `ohlcv-1h` for ES and ZN, which cannot form a 30-minute window.
- **Windows** (the paper's underlying-market hours):

  | | Reference close | Signal time | Trade window (ET) |
  |---|---|---|---|
  | ES | 16:00 ET on the previous NYSE session | 15:30 | 15:30-16:00 |
  | ZN | 15:00 ET on the previous session | 14:30 | 14:30-15:00 |

- **Signal:** r_ROD = ln(P_signal / P_reference), using bar closes. Position = sign(r_ROD). The position is zero if r_ROD = 0 or a required bar is missing.
- **Execution:**
  - Enter at the close of the first 1-minute bar after the signal time (a one-minute delay, which is conservative).
  - Exit at the close of the bar ending at the window end.
  - No overnight position.
- **Exclusions:** early-close sessions and CME/NYSE holidays (fixed list in the file).
- **Sizing:**
  - Scale each instrument by 1/σᵢ, where σᵢ is the standard deviation of its last-window returns over the prior 63 sessions.
  - Give each instrument 50% of the risk. (Sharpe is scale-free; leverage matters only for combination with other streams.)
- **Costs:**
  - At least 1 tick per side, taken from Databento `definition` `min_price_increment`, plus a fixed per-contract fee written into the file.
  - Report at 2× costs.

**Hypotheses:**
- **H-M1:** forward net Sharpe > 0.
- **Secondary:** the slope β > 0 in r_last = α + β·r_ROD, pooled across both instruments with Newey-West errors.

**Pre-registered diagnostics (no hypothesis):**
- **Event days versus other days.** Separate:
  - macro-release days, from ZipLime/us-economic-events embargo times with the BLS calendar as fallback;
  - FOMC days, from ZipLime/fomc-events with federalreserve.gov as fallback.

  The intraday-momentum papers report stronger effects on macro-news days. This is the one honest use of HF data in this plan.
- **Correlation** with F1 and with candidate 1.

**Why this one:**
- **It uses a different information source:** intraday hedging flows by dealers and leveraged ETFs, rather than daily trend or month-end flows. So it should be close to uncorrelated with F1 and with trend. This is expected, not verified.
- **It trades every day,** so a month of forward data holds about 21 independent bets per instrument.
- **The paper's evidence is broad:** 46 years, more than 60 futures, and similar regressions in 1974-99 and 2000-20.
- **The earlier idea scan agrees.** `idea_literature.md` already ranked it 5th and called it the best Databento showcase.

**Risks, stated in advance:**
- **No post-2020 evidence.** The mechanism depends on dealer gamma positioning, which changes over time (`idea_literature.md` flags the 0DTE era).
- **A related strategy reportedly stopped working.** The SPY intraday breakout rule of Zarattini et al. 2024 claims net Sharpe 1.33, but it reportedly earned about 0 in 2025-26 in an unreviewed independent replication (parallel review). That is a different rule, but the same family.
- **Costs are large relative to a 30-minute move.**
- **Gao et al.'s 1.08 is unverified.**

**Expected realistic net Sharpe: 0.0-0.5, central about 0.2.**
- **The published figures carry more breadth than we have.** Baltussen et al.'s gross 1.73 (equity) and 1.62 (bonds) are equal-weight portfolios of many markets; two instruments carry far less breadth.
- **The haircut and costs cut it further.** Apply the 50-75% backtest-to-live haircut, then subtract at least two ticks a day.
- **The standard error is the same as candidate 1's.** It is about 0.71 after 24 months, because more trades do not shrink the Sharpe's standard error below √(252/n).

### 5.4 Considered and not chosen

- **Stand-alone carry** (Koijen et al.; commodity term structure; basis-momentum):
  - in-sample Sharpe was 1.2-1.4 gross before 2012;
  - AQR's four-asset futures carry earned about 0.07 gross over 2012-Feb 2026 (parallel verifier's calculation);
  - the live G10 carry ETF lost money and closed;
  - carry crashes in recessions;
  - the commodity curve signals rebalance monthly with about 4 names per leg, so a forward test sees few observations.

  This reverses the robust-strategies pass, which proposed pairing carry with trend before the post-2012 numbers were known.
- **Equity plus trend (parallel S2) and Faber GTAA (parallel S3).** Both are defensible, but S2 contains candidate 1 and S3 overlaps it. Use S2 instead of candidate 1, not in addition.
- **An earnings-season 8-K text signal** (ZipLime/sec-8k-events EX-99 releases scored with FinBERT, entered at the next open).
  - **For:** it is the HF-native option with the most statistical power in a short window, with hundreds of releases per earnings season.
  - **Against:**
    - large-cap news edge after costs is weak (Ke-Kelly-Xiu value-weighted gross 1.33, with the reaction finished within a day; Lopez-Lira-Tang unprofitable at 20 bp; the HF filing benchmark's text IC is −0.006);
    - it is a single-stock strategy outside the ETF and futures design.
  - **If pursued anyway:** pre-register it as an event study (mean next-open-to-day-5 abnormal return by tone tercile), not as a strategy claim.
- **Macro-surprise timing on ES/ZN.**
  - ZipLime/us-economic-events, as described, has first prints and revisions but no consensus forecasts, so a "surprise" would need our own forecast.
  - Each release family gives about one event a month.
  - Goyal-Welch-Zafirov warn against macro timing.
- **Other ideas set aside:** factor momentum through ETFs (untested in the papers), same-month seasonality, the VIX basis (short-volatility tail risk), the pre-FOMC drift (dead), and social-media mood (failed replication).

### 5.5 What can strengthen the current quant note today

The note already discusses decay (citing McLean & Pontiff), selection (the Deflated Sharpe Ratio, DSR) and noise (a two-year standard error of about 0.7). The literature adds two things: **base rates for the size of the drop**, and **support for the risk-management choices**. Suggested text follows. The body must stay within five pages, so recompile and check the page count; references do not count toward it.

1. **Section 5, after "decay (... McLean \& Pontiff 2016)".** One sentence:
   > The size of the drop is typical: F1's gross Sharpe fell 72\% (\ISgross{} to \OOSgross), against a median fall of 73\% from backtest to live for 215 bank risk-premia indices (Suhonen, Lennkh \& Perez 2017) and roughly half of in-sample performance for published systematic strategies, more for complex ones (Falck, Rej \& Thesmar 2022); a comparable liquid-futures calendar effect, the pre-FOMC drift, disappeared after 2015 (Kurov, Wolfe \& Gilbert 2021).
2. **Section 6 (risk management), optional.** One clause:
   > volatility targeting raises the Sharpe only for risk assets but trims tails everywhere (Harvey et al. 2018), and regression-fitted volatility timing fails in real time (Cederburg et al. 2020), so we use a plain 8\% target and no brake.
3. **Section 8, optional, only if `FORWARD_TEST_2.md` is committed before submission.** Add one clause pointing to it. Do not add any new strategy results to the note.

**Caveats:**
- The Suhonen and Falck figures come from abstracts and summaries (SSRN returned 403). Both reviews agree on the Suhonen figure.
- Do not change any number in the results.

---

## 6. References and links

**Decay, overfitting and statistics**
- McLean & Pontiff (2016), *J. Finance*. https://doi.org/10.1111/jofi.12365
- Falck, Rej & Thesmar (2022), *Quantitative Finance* 22(11). https://doi.org/10.1080/14697688.2022.2098810 ; arXiv version cited by the parallel review: https://arxiv.org/abs/2105.01380
- Suhonen, Lennkh & Perez (2017), *JPM* 43(2). https://doi.org/10.3905/jpm.2017.43.2.090
- Jensen, Kelly & Pedersen (2023), *J. Finance*. https://doi.org/10.1111/jofi.13249 ; data: https://jkpfactors.com
- Ilmanen, Israel, Moskowitz, Thapar & Lee (2021), *JOIM*. https://www.aqr.com/Insights/Research/Journal-Article/How-Do-Factor-Premia-Vary-Over-Time-A-Century-of-Evidence
- Baltussen, Swinkels & van Vliet (2021), *JFE*. https://doi.org/10.1016/j.jfineco.2021.06.030
- Goyal, Welch & Zafirov (2024), *RFS* 37(11). https://doi.org/10.1093/rfs/hhae044
- Kurov, Wolfe & Gilbert (2021), *FRL* 40. https://doi.org/10.1016/j.frl.2020.101781
- Bailey & López de Prado (2014), The Deflated Sharpe Ratio, *JPM*. https://doi.org/10.3905/jpm.2014.40.5.094
- Marshall, Cahan & Cahan (2008), *JBF* 32(9). https://ideas.repec.org/a/eee/jbfina/v32y2008i9p1810-1819.html
- Hollstein, Prokopczuk & Tharann (2021), *QJF*. https://centaur.reading.ac.uk/100920/1/SSRN-id3567629.pdf

**Trend, carry and intraday momentum**
- Hurst, Ooi & Pedersen (2017), *JPM* 44(1). https://doi.org/10.3905/jpm.2017.44.1.015
- Moskowitz, Ooi & Pedersen (2012), *JFE*. https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf
- Huang, Li, Wang & Zhou (2020), *JFE*. https://doi.org/10.1016/j.jfineco.2019.08.004
- Koijen, Moskowitz, Pedersen & Vrugt (2018), *JFE* 127(2). https://doi.org/10.1016/j.jfineco.2017.11.002
- Baltussen, Da, Lammers & Martens (2021), *JFE* 142(1). https://academicweb.nd.edu/~zda/intramom.pdf
- Gao, Han, Li & Zhou (2018), *JFE*. https://doi.org/10.1016/j.jfineco.2018.05.009
- Li, Sakkas & Urquhart, *J. Financial Markets*. https://centaur.reading.ac.uk/95566/1/Accepted-Version.pdf
- Zarattini, Aziz & Barbon (2024), Beat the Market. https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download
- Fuertes, Miffre & Rallis (2010), *JBF* 34(10). https://openaccess.city.ac.uk/id/eprint/6416/1/Fuertes_Miffre_Rallis_JBF2010(CRO).pdf
- Boons & Porras Prado (2019), *J. Finance* 74(1). https://doi.org/10.1111/jofi.12738
- Pitkäjärvi, Suominen & Vaittinen (2020), *JFE*. https://doi.org/10.1016/j.jfineco.2019.02.011
- Keloharju, Linnainmaa & Nyberg (2016), *J. Finance*. https://www.nber.org/papers/w20815.pdf
- Ehsani & Linnainmaa (2022), *J. Finance*. https://doi.org/10.1111/jofi.13131
- Gupta & Kelly (2019), *JPM* 45(3). https://doi.org/10.3905/jpm.2019.45.3.013
- Harvey et al. (2018), *JPM* 45(1). https://doi.org/10.3905/jpm.2018.45.1.014
- Cederburg, O'Doherty, Wang & Yan (2020), *JFE* 138. https://doi.org/10.1016/j.jfineco.2020.04.015
- Simon & Campasano (2014), *J. Derivatives*. https://www.efmaefm.org/0EFMAMEETINGS/EFMA%20ANNUAL%20MEETINGS/2013-Reading/papers/EFMA2013_0164_fullpaper.pdf
- Durham (2013), NY Fed SR 657. https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr657.pdf
- AQR data library (TSMOM factors; Century of Factor Premia): https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Time-Series-Momentum-Factors-Monthly.xlsx

**Text, LLMs and look-ahead**
- Tetlock (2007), *J. Finance*. https://doi.org/10.1111/j.1540-6261.2007.01232.x
- Garcia (2013), *J. Finance*. https://doi.org/10.1111/jofi.12027
- Ke, Kelly & Xiu (2019), NBER WP 26186. https://www.nber.org/papers/w26186
- Chen, Kelly & Xiu (2022), SSRN 4416687. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4416687
- Lopez-Lira & Tang (2023/2026). https://arxiv.org/abs/2304.07619
- Chen, Tang, Zhou & Zhu (2025). https://arxiv.org/abs/2502.10008
- Adämmer & Schüssler (2020), *Rev. Finance*. https://doi.org/10.1093/rof/rfaa007
- Cohen, Malloy & Nguyen (2020), *J. Finance*. https://doi.org/10.1111/jofi.12885
- Jiang, Kelly & Xiu (2023), *J. Finance*. https://doi.org/10.1111/jofi.13268
- Lachanski & Pav (2017), *Econ Journal Watch*. https://econjwatch.org/articles/shy-of-the-character-limit-twitter-mood-predicts-the-stock-market-revisited
- Glasserman & Lin (2024), *JFDS*. https://arxiv.org/abs/2309.17322
- Sarkar & Vafa (2024). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4754678
- Lopez-Lira, Tang & Zhu (2025), The Memorization Problem. https://arxiv.org/abs/2504.14765
- He, Lv, Manela & Wu (2025), Chronologically Consistent LLMs. https://arxiv.org/abs/2502.21206
- Yan, Tang, Gao, Jiang & Lu (2026), DatedGPT. https://arxiv.org/abs/2603.11838 ; Gao, Jiang & Yan (2025), LAP: https://arxiv.org/abs/2512.23847
- FinBERT paper: https://arxiv.org/abs/1908.10063 ; FNSPID paper: https://arxiv.org/abs/2402.06698

**Hugging Face (datasets and models named above)**
- https://huggingface.co/datasets/ZipLime/us-economic-events
- https://huggingface.co/datasets/ZipLime/fomc-events
- https://huggingface.co/datasets/ZipLime/sec-8k-events
- https://huggingface.co/datasets/ZipLime/earnings-calendar
- https://huggingface.co/datasets/ZipLime/company-fundamentals
- https://huggingface.co/datasets/ZipLime/security-master
- https://huggingface.co/datasets/ZipLime/commitments-of-traders
- https://huggingface.co/datasets/ZipLime/us-treasury-events
- https://huggingface.co/datasets/tidy-finance/factor-library
- https://huggingface.co/datasets/AlphaDojo/dojo_stock_news
- https://huggingface.co/datasets/defeatbeta/yahoo-finance-data
- https://huggingface.co/datasets/paperswithbacktest/Stocks-Daily-Price
- https://huggingface.co/datasets/Zihan1004/FNSPID
- https://huggingface.co/datasets/Brianferrell787/financial-news-multisource
- https://huggingface.co/datasets/kurry/sp500_earnings_transcripts
- https://huggingface.co/datasets/BatuhanECB/sec-filings-forward-return-2026
- https://huggingface.co/datasets/HaiwenWang/sp500-pit-benchmark (do not use)
- https://huggingface.co/ProsusAI/finbert
- https://huggingface.co/manelalab/chrono-bert-v1-20241231
- https://huggingface.co/FinText
- https://huggingface.co/NeoQuasar/Kronos-base

**Primary data sources**
- Databento GLBX.MDP3 (already in `data/download_databento.py`)
- Yahoo Finance via yfinance
- FRED / ALFRED
- Cboe (VIX, VX futures)
- Ken French Data Library
- SEC EDGAR
- CFTC COT
- U.S. Treasury Fiscal Data

**Project cross-references**
- `research/high_sharpe_literature.md` (parallel review)
- `research/idea_literature.md`
- `FORWARD_TEST.md`
- `forward/historical_context.json`
- `note/quant_note.tex`

**Working files.** Scratch files from the literature passes (PDF text extracts, OpenAlex scripts) are in this session's scratchpad: `<scratch>`. They are not part of the repository.
