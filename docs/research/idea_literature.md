# Idea and literature scan: Gator Quant Hacks 2026, Systematic Trading track

Prepared Sat 2026-10-03 (about 05:45 to 07:00 ET) as research input only. No backtests were run for this file. Every performance number below is **as reported by the cited source** (usually in-sample and gross), not our own result. Items marked *(verify)* could not be confirmed from a primary source during this scan.

---

## 0. TL;DR (recommendation)

**Build the "Institutional Flow Clock" (IFC).** It is a multi-asset strategy on CME futures (ES, ZN/ZB, 6E/6J/6B) that provides liquidity to *forced, calendar-scheduled institutional flows* around month-end. It has four sleeves, each grounded in a published mechanism with an identifiable counterparty and with parameters fixed ex-ante from the literature (0 or 1 free parameter per sleeve):

| Sleeve | Counterparty we trade against | Core paper | Our novel twist |
|---|---|---|---|
| A. Equity/bond rebalancing pressure | Pensions, TDFs and balanced funds rebalancing back to fixed stock/bond targets, about $20tn | Harvey, Mazzoleni & Melone (NBER 33554, 2025/26) | Settlement-aware timing, plus sizing by estimated dollar drift relative to futures ADV |
| B. Settlement-cycle "dash for cash" | Institutions selling to raise month-end payment cash; buying when new money clears | Etula, Rinne, Suominen & Vaittinen (RFS 2020) | **Natural experiment.** US settlement moved T+3 → T+2 (2017-09-05) → T+1 (2024-05-28). We pre-register that each move shifts the pressure and reversal windows by one day. The rules-mandated OOS window (last 2 years, about Oct 2024 to Oct 2026) falls **entirely in the T+1 regime**, so it is a structural out-of-sample test that nobody has published yet (to our knowledge) |
| C. Treasury month-end index extension | Index-benchmarked bond managers and life insurers buying duration when indices add new issues at month-end | Hartley & Schwarz (2019 WP) | Size the position by **that month's coupon issuance DV01**, which is known ex-ante from Treasury auction data, rather than a fitted constant |
| D. FX equity-hedge rebalancing at the month-end fix | International equity managers resetting FX hedge ratios at the WM/R 4pm fix | Melvin & Prins (JFM 2015); Krohn, Mueller & Whelan (JF 2024) | A **net cross-border hedge-flow** signal that weights US holdings abroad against foreign holdings of US equities, using free TIC holdings data |

**Why judges should like it:**
- *Economic foundation:* every leg names who loses and why they cannot stop (mandates, settlement plumbing, index rules).
- *Innovation:* the settlement natural experiment and quantity-based sizing are new.
- *Risk:* each sleeve is in the market only a few days per month, sleeves sit in different asset classes, and the strategy is contrarian, so its correlation to trend and momentum is low.
- *Capacity:* ES and ZN are among the deepest futures markets in the world.
- *Evidence:* a clean pre-registration exists, the free-parameter count is tiny, and the variant budget is small, which keeps the Deflated Sharpe ratio honest.
- *Sponsor fit:* the core data is Databento GLBX.MDP3 daily bars (Best Use of Databento prize). Free data (S&P index, FRED yields, FRED FX) extends the test back before 2010.

**Honest expectation:** the published standalone Sharpe ratios are about 1 (gross, in-sample). After post-publication decay (McLean & Pontiff 2016: about −58% on average), costs and lagging, a combined net Sharpe of **0.5 to 0.9** is the realistic target, which is exactly the "defensible modest Sharpe" band. Anything above about 1.5 should be treated as a bug until proven otherwise.

**Avoid as headline ideas (decayed; use them in a "graveyard" paragraph to show discipline):**
- Pre-FOMC drift: gone after 2015 (Kurov, Wolfe & Gilbert 2021).
- Overnight drift: about zero since 2021 (NY Fed Liberty Street, Jul 2026).
- Treasury auction cycle: less than half its old size after 2014 (Fleming, Liu & Nguyen 2026).
- Goldman-roll front-running: arbitraged away.

---

## 1. How the judging rules shape the choice

- **Hypothesis before backtest, OOS once.** Mechanisms with *literature-fixed* windows and signs are ideal, because we can commit the exact rule today. The OOS window is the shorter of the last 20% of history or the last 2 years. For any sample starting 2005 or 2010 that is the last 2 years (about 2024-10 to 2026-10).
- **Few free parameters plus a variant count (Deflated Sharpe).** Prefer rules where the parameters come from institutions (60/40 targets, T+k settlement, the index month-end rule) rather than from fitting.
- **Net of costs at 1x and 2x.** Prefer futures (ES about 0.25 tick, roughly 0.5 bp half-spread) and trades that happen only a few days per month.
- **Factor regression** on market, value and momentum (Ken French daily). A contrarian liquidity-provision strategy should load negatively or not at all on UMD and TSMOM. That is a feature worth showing.
- **Capacity via square-root impact.** Liquid CME futures make the capacity section easy and credible.
- **Code reproduces the note.** Daily bars and simple calendars keep the pipeline deterministic.

---

## 2. Data inventory (what we can actually get today)

| Source | Coverage | Use | Cost |
|---|---|---|---|
| **Databento GLBX.MDP3** (CME Globex), schema `ohlcv-1d` (also `ohlcv-1m`) | From **2010-06-06** for all CME futures and options on futures (legacy history backfilled from CME DataMine) | ES, NQ, ZN, ZF, ZB, UB, 6E, 6J, 6B, CL, GC. Continuous symbology (`ES.c.0`, `ES.v.0`) available; compute returns per `instrument_id` to avoid roll gaps | $125 free credits; daily bars for a dozen roots cost very little. The hackathon key is distributed via Discord. As of this scan, no `DATABENTO*`, `POLYGON*` or `MASSIVE*` variable exists in `<automation>/.env` or in this project repo |
| FRED / ALFRED | Decades | DGS2/5/10/30 (build approximate Treasury returns before 2010), DTB3 (cash), H.10 noon FX (DEXUSEU, DEXJPUS, DEXUSUK; noon NY is about 1h after the London 4pm fix), **ALFRED vintage dates = historical release dates for CPI and payrolls** | Free |
| Ken French Data Library | Daily since 1926 | MKT, SMB, HML, UMD for the factor regression | Free |
| AQR data sets | Monthly | TSMOM, BAB and value/momentum "everywhere" factors for the extra regressions | Free, with citation |
| Fiscal Data (Treasury) "Treasury Securities Auctions Data" | 1979 to present | Auction dates, offering amounts and security terms. Drives sleeve C sizing and the auction calendar | Free API |
| NY Fed Primary Dealer Statistics | Weekly since 1998 | Dealer net Treasury positions (conditioning for the auction idea) | Free |
| Treasury TIC (SHL/SHC surveys and monthly holdings) | Annual/monthly | Cross-border equity holdings for the sleeve D weights | Free |
| CFTC Commitments of Traders / TFF | Weekly since 2006 (TFF) | Asset-manager vs leveraged-fund positioning (VIX, ES, ZN, FX) | Free |
| CBOE indices and VIX futures history | VIX since 1990; VIX3M since about 2007; VIX9D since about 2011; VX settles since 2004 | VIX-premium idea | Free CSVs |
| yfinance / Stooq | ETFs since about 1993 to 2007 | SPY, IEF, TLT, EFA, country ETFs, foreign indices (^N225, ^GDAXI, ^FTSE) for pre-2010 robustness | Free |
| Binance/OKX funding history | 2019 onward | Crypto carry idea | Free |
| SEC EDGAR 8-K index | 2004 onward | Massive "Trade the 8-K" bonus | Free (options data from Massive) |
| SqueezeMetrics GEX/DIX | 2011 onward | Dealer-gamma proxy | **Paid** (about $720/month). Do not plan on it |

Survivorship is a non-issue for index futures, FX and Treasuries. That is a point in favour of macro instruments over single stocks for the "survivorship/corporate actions" rule.

---

## 3. Candidate mechanisms (14 scanned)

Each entry covers: mechanism and counterparty, key references, documented performance and decay, data, free parameters, failure modes, and our novel twist.

### 3.1 Month-end and threshold stock/bond rebalancing pressure ★

- **Mechanism / counterparty.** About $20tn of balanced money (DB pensions, target-date funds, sovereign funds, endowments) keeps fixed equity/bond weights. Rebalancing follows either a *calendar* rule (toward month- or quarter-end) or a *threshold* rule (when drift exceeds a band). After stocks beat bonds, these funds must sell equities and buy bonds regardless of price. We provide that liquidity: we buy what they must sell, or sell ahead of their selling and buy it back.
- **Why it persists:** governance. A pension roundtable told the authors it is easier to task their alpha desk with exploiting the predictability than to change the policy at the investment committee. TDF assets are growing fast (Parker, Schoar & Sun, JF 2023, show that TDF rebalancing flows move prices).
- **References.**
  - Harvey, Mazzoleni & Melone, *The Unintended Consequences of Rebalancing*, NBER WP 33554 (Mar 2025, rev. Jan 2026).
  - Parker, Schoar & Sun, *Retail Financial Innovation and Stock Market Dynamics: The Case of Target Date Funds*, JF 78(5), 2023.
- **Documented performance (from EDHEC slides, Feb 2026).**
  - Daily data 1997-09 to 2023-03 on ES and 10y note futures.
  - When stocks are overweight, next-day equity returns fall about 17 bp per unit of signal and bond returns rise about 3 bp.
  - The pressure resolves within about 2 weeks.
  - A real-time front-running strategy combining the threshold and calendar signals earns **Sharpe 1.08**, with much higher returns in high-VIX and illiquid regimes (about 18%/yr vs 4%/yr).
  - The authors say predictability has *increased* over the past two decades.
  - Published 2025, so post-publication decay is untested. That is both a risk and an opportunity.
- **Signal construction (theirs).**
  - Simulate a 60/40 ES/ZN portfolio. Distance_t = equity weight after drift − 60%.
  - Threshold signal: the drifted weight resets to 60% when |distance| ≥ δ. They average δ from 0 to 2%, which removes δ as a free parameter.
  - Calendar signal: the weight resets on the last business day of each month, and the signal is interacted with a week-4 (last trading week) dummy.
- **Data.** ES and ZN from Databento (2010+). Free S&P 500 total return plus FRED 10y yield-implied returns cover 1990–2010. **Free data suffices.**
- **Free parameters.** Effectively 0 to 1: the 60/40 target is an institutional fact; δ is averaged; the window is "week 4" as in the paper.
- **Failure modes.**
  - Crowding after the 2025 publication.
  - In positive stock/bond correlation regimes such as 2022 both legs move together, so the relative-value bet loses its hedge.
  - Contrarian losses in persistent trends (Oct 2008, Mar 2020).
  - Signal and pressure timing may have shifted with T+1.
- **Novel twist (ours).**
  1. **Settlement-aware window.** Equity-leg pressure dates should move with US settlement (T+3 → T+2 → T+1). Treasuries were already T+1, so they act as a control.
  2. **Dollar-flow sizing.** Position ∝ |drift| × (proxy for rebalancer AUM) / (ES ADV from Databento volume). That gives a capacity-consistent signal rather than a z-score.
  3. **Quarter-end amplification** with an ex-ante multiplier taken from the paper's quarter vs month evidence (if it reports one; otherwise skip to avoid adding a parameter).
  4. Report a **stock/bond correlation regime split** (ex-ante 1-year rolling correlation > 0) as a risk-management diagnostic, not as a tuned filter.

### 3.2 Turn-of-month liquidity cycle ("Dash for Cash") with the settlement natural experiment ★

- **Mechanism / counterparty.** Institutions (mutual funds, pensions paying benefits, firms paying salaries) need cash on the month-end payment date and must sell securities at least *k* trading days earlier, where *k* is the settlement lag. That produces selling pressure, then a reversal, then buying at the turn of the month as newly cleared money is invested. Liquidity providers earn the reversal. The cost falls on price-insensitive cash raisers (estimated at about $30bn/yr historically).
- **References.**
  - Etula, Rinne, Suominen & Vaittinen, *Dash for Cash: Monthly Market Impact of Institutional Liquidity Needs*, RFS 33(1) 2020, 75–111.
  - Ariel (1987, JFE); Lakonishok & Smidt (1988, RFS); Ogden (1990, JF); McConnell & Xu, *Equity Returns at the Turn of the Month*, FAJ 2008.
- **Documented performance.**
  - Under T+3 (Jul 1995 to Dec 2013), US stocks are weak from T−8 to T−4 ("selling pressure") and strong from T−3 through T+3 (T = last trading day).
  - In 2003–2013 the T−3..T−1 reversal days earned a cumulative 103% excess return (73% of the total equity excess return), while the selling-pressure days earned −31%. The correlation between the two windows is −0.54.
  - The pattern is significant in 20 of 23 equity markets.
  - **Reversals are about 2.5x larger when T falls on a Friday**, when the monthly pension cycle and the weekly payroll cycle coincide.
  - Treasuries already settle T+1: Treasury yields stay elevated until T−2.
  - The paper itself notes that the US moved to T+2 in Sep 2017. To our knowledge nobody has published the T+2 or T+1 shift test.
  - Practitioner evidence (S&P 500, 1980–2024) says the turn-of-month effect persists but has become concentrated on the first trading day in the ETF era.
- **Data.** ES (Databento) and SPY/^GSPC (free). Dates: T+2 effective 2017-09-05; T+1 effective 2024-05-28. **Free data suffices.**
- **Free parameters: 0.** The windows are a deterministic function of k: selling window [T−k−5, T−k−1], long window [T−k, T+3], and the Friday multiplier is taken from the paper.
- **Failure modes.**
  - A very old anomaly that may be partly arbitraged.
  - Effect sizes of a few bp per day need low-cost futures.
  - Shrinking reversal windows under T+1 leave fewer days to trade.
  - Alternative stories (window dressing) have similar timing. The settlement shift is exactly what tells them apart.
- **Novel twist (ours).** Pre-register three predictions:
  - (H1) The pressure and reversal windows shift one trading day later each time settlement shortens.
  - (H2) The equity pattern under T+1 converges to the Treasury pattern, which has always been T+1.
  - (H3) Friday month-ends amplify the effect.
  The OOS window (2024-10 to 2026-10) lies **entirely in the T+1 regime**, so the single OOS evaluation is also a test of a structural prediction made in advance. That is very hard to fake and judges should find it convincing.

### 3.3 Treasury month-end index extension (plus auction cycle as a secondary leg) ★

- **Mechanism / counterparty.** Bond indices (Bloomberg US Treasury/Agg, ICE) add newly issued securities only at month-end, so index duration jumps on the rebalance. Benchmarked managers and life insurers must buy duration in the last days of the month (insurer purchases spike on index-rebalance dates). We pre-position long duration and sell into their demand.
- Auction cycle: primary dealers must absorb pre-scheduled supply with limited balance sheet, so yields rise into auctions and fall afterward.
- **References.**
  - Hartley & Schwarz, *Predictable End-of-Month Treasury Returns*, WP (Wharton/Harvard), Nov 2019.
  - Lou, Yan & Zhang, *Anticipated and Repeated Shocks in Liquid Markets*, RFS 2013.
  - Fleming, Liu & Nguyen, *Intraday Price Pressure and Order Flow Around U.S. Treasury Auctions*, NY Fed Staff Report 1188 (Mar 2026, rev. Jul 2026).
- **Documented performance.**
  - End of month: 10y excess return of about 25 bp over the last 3 trading days, 1990–2018. **Sharpe about 1** across maturities, with returns positive 55 to 70% of the time. The effect is also present in Treasury futures (annualized return above 3pp for the longest contracts held only over the last few days) and in swaps. Weaker but still significant in 2015–2018.
  - Caveat: a CXO test on **TLT** did *not* corroborate the effect, likely because TLT's own index rebalances at month-end. Use futures.
  - Auction cycle: LYZ (1980–2008) find +2 to 3 bp of yield before the auction and about −2 bp after. Fleming et al. find the effect **less than half as large after 2014** (statistically significant decline) because non-dealers now absorb supply. Treat the auction leg as weak.
- **Data.** ZN/ZF/ZB/UB from Databento (2010+). FRED CMT yields give approximate returns for 1990–2010 via duration × Δyield + carry. Fiscal Data auctions API. NY Fed dealer positions. **Free data suffices.**
- **Free parameters.** 1: the window length, fixed at 3 days from the paper.
- **Failure modes.**
  - Very well known to rates desks (EOM extension is printed in sell-side calendars).
  - The effect is small in absolute terms, so the leg's risk contribution needs vol scaling.
  - Duration crashes (2022) can swamp a 3-day window.
- **Novel twist (ours).**
  - **Issuance-sized month-end leg.** Position ∝ DV01 of coupon securities issued during month m (from the auctions data, known before T−3) relative to its trailing 12-month median. This is a free, ex-ante proxy for the index duration extension that drives the forced buying.
  - Optional auction leg (pre-registered as secondary): short duration only when NY Fed primary dealer net coupon positions (lagged one week) are above their trailing median, which is exactly the "dealer constraint" channel in Fleming et al.

### 3.4 FX equity-hedge rebalancing at the month-end fix ★

- **Mechanism / counterparty.** International equity managers keep benchmark FX hedge ratios and reset them mostly at the WM/R London 4pm fix on the *last* trading day of the month.
  - If foreign equities rose in local currency, a US manager's unhedged FX exposure grew, so the manager sells more foreign currency forward and that currency depreciates into the fix.
  - Symmetrically, foreign holders of US equities sell USD forward after US stocks rally.
  - Dealers warehouse this price-insensitive flow at the fix. The W-shaped intraday dollar pattern around fixes is consistent with dealer inventory risk.
- **References.**
  - Melvin & Prins, *Equity Hedging and Exchange Rates at the London 4 p.m. Fix*, J. Financial Markets 22 (2015) 50–72.
  - Krohn, Mueller & Whelan, *Foreign Exchange Fixings and Returns Around the Clock*, JF 79(1) 2024, 541–578.
- **Documented performance.** Equity appreciation over the month predicts currency depreciation before the month-end fix (Melvin & Prins; Sharpe not recorded here *(verify)*). Fix-related reversals are pervasive across the 9 most traded currencies over 21 years (KMW). Post-2015 fix reform (wider calculation window) may have diluted the effect *(verify)*.
- **Data.** 6E, 6J, 6B, 6C, 6A futures (Databento 2010+). FRED H.10 noon rates from 1999 for EUR (earlier for JPY and GBP); noon NY is close to the 11am ET fix. Local equity indices via yfinance. TIC cross-border holdings. **Free data suffices** (timing is approximate on daily bars).
- **Free parameters.** 1 to 2: the entry day (T−2 or T−3, to be fixed ex-ante) and hedge-ratio weights (taken from TIC/surveys, not fitted).
- **Failure modes.**
  - The flow is small relative to FX turnover.
  - Bank month-end models are published in the press (investingLive/ForexLive), so the trade is crowded.
  - Daily bars cannot isolate the fix minute.
- **Novel twist (ours).** A **net cross-border hedge-flow** signal per currency c: NetUSDdemand_c ∝ H^US→c · r^c_equity,local − H^c→US · r^US_equity, where H are TIC cross-border equity holdings. Most practitioner models use only one side of the flow.

### 3.5 Scheduled macro-announcement premium (FOMC, CPI, NFP)

- **Mechanism / counterparty.** Investors demand compensation for bearing the resolution of macro uncertainty on scheduled days (generalized risk sensitivity; Ai & Bansal 2018). The counterparty is risk-averse holders who de-risk into announcements.
- **References.**
  - Savor & Wilson, JFQA 2013.
  - Lucca & Moench, *The Pre-FOMC Announcement Drift*, JF 2015.
  - Ai & Bansal, Econometrica 2018.
  - Ai, Bansal & Guo, *Macroeconomic Announcement Premium*, NBER 31923 (2023).
  - Cieslak, Morse & Vissing-Jorgensen, *Stock Returns over the FOMC Cycle*, JF 74(5) 2019.
  - Kurov, Wolfe & Gilbert, *The Disappearing Pre-FOMC Announcement Drift*, FRL 2021.
- **Documented performance.**
  - 1961–2023: 10.68 bp on announcement days vs 0.93 bp otherwise. The 44 announcement days earn about 4.65%/yr, roughly 71% of the equity premium.
  - Back-of-envelope Sharpe (ours): 0.107%/1.1% × √44 ≈ **0.64 gross**.
  - The pre-FOMC drift disappeared after 2015.
  - The FOMC-cycle "even weeks" result covers 1994–2016; its post-publication record is unverified.
- **Data.** ALFRED vintage dates (CPI, payrolls), FOMC calendars (federalreserve.gov), ES/SPY. **Free data suffices.**
- **Free parameters.** 1 to 2: the event set and the holding window, both fixed ex-ante.
- **Failure modes.**
  - In the 2022 inflation regime, CPI days were often sharply negative.
  - Low time in market means a modest Sharpe.
  - Decay in the FOMC component.
- **Novel twist.** Scale exposure by the **ex-ante event-implied variance** (the VIX9D minus VIX term-structure "kink", available since 2011). It also works as an overlay on the IFC.

### 3.6 VIX futures premium / term-structure carry, timed

- **Mechanism / counterparty.** Hedgers (institutions, retail VIX ETP longs) overpay for convex crash protection, so VIX futures trade above the expected VIX and roll down. Short-vol sellers earn the premium but bear crash risk.
- **References.**
  - Simon & Campasano, *The VIX Futures Basis: Evidence and Trading Strategies*, J. Derivatives 2014.
  - Johnson, *Risk Premia and the VIX Term Structure*, JFQA 2017.
  - Cheng, *The VIX Premium*, RFS 32(1) 2019.
  - Eraker & Wu, JFE 2017.
- **Documented performance.**
  - Basis (contango vs backwardation) predicts futures returns. A hedged short-contango strategy was profitable after costs, 2006–2011.
  - Cheng: the ex-ante premium predicts ex-post returns with a coefficient near 1. The premium *falls* when risk rises, so selling vol when the premium is low is dangerous.
  - Real-world blowups: XIV (Feb 2018), Mar 2020, Aug 2024.
- **Data.** CBOE VX settlement CSVs (2004+) and VIX/VIX3M/VIX9D, all free. **Free data suffices.**
- **Free parameters.** 2 to 4.
- **Failure modes.** Fat left tail. VX costs of 10 to 20 bp per side. Capacity limited by VX ADV.
- **Novel twist.** Measure the ex-ante premium as the front future minus a HAR-RV forecast of VIX, and condition on the CFTC asset-manager VIX position (Cheng's hedging-demand channel). Hedge delta with ES. This is risky for a judging rubric that weighs risk management heavily.

### 3.7 End-of-day LETF and dealer-gamma flows / market intraday momentum

- **Mechanism / counterparty.** Leveraged and inverse ETFs must trade AUM × L(L−1) × r_day near the close, *in the direction* of the day's move. Short-gamma option dealers hedge the same way. Both create late-day momentum that reverts at the next open. The counterparty is LETF holders (mostly retail) and option end-users.
- **References.**
  - Cheng & Madhavan (2009, J. Investment Management).
  - Shum, Hejazi, Haryanto & Rodier (2016, Rev. Finance) *(verify venue)*.
  - Gao, Han, Li & Zhou, *Market Intraday Momentum*, JFE 2018.
  - Baltussen, Da, Lammers & Martens, *Hedging Demand and Market Intraday Momentum*, JFE 2021.
  - Barbon, Beckmeyer, Buraschi & Moerke, *The Role of Leveraged ETFs and Option Market Imbalances on End-of-Day Price Dynamics* (WP 2021).
  - Barbon & Buraschi, *Gamma Fragility* (WP).
  - Zarattini, Aziz & Barbon, *Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)*, SFI WP 24-97 (2024).
- **Documented performance.**
  - SPY 1993–2013: the last half-hour earns 6.3%/yr gross when the first half-hour is positive.
  - Intraday momentum appears in more than 60 futures from 1974 to 2020 and reverts over the next days.
  - LETF imbalance effects are larger than the options channel.
  - Zarattini et al.: **Sharpe 1.33 net**, 2007–2024.
- **Data.** Needs intraday bars: Databento ES `ohlcv-1m` (2010+; cheap, and strong for the Databento prize). Historical LETF AUM is *not* freely available in bulk.
- **Free parameters.** 2 to 3.
- **Failure modes.**
  - Daily round trips mean cost drag of roughly 2 to 4 bp per day.
  - The 0DTE era (2022+) changed dealer gamma dynamics.
  - Well mined by practitioners.
- **Novel twist.** Scale the late-day position by an estimated LETF rebalancing notional relative to ES minute volume, and trade the *next-open reversal* as a second leg. This is the best "Databento showcase" option, but it is intraday rather than daily and adds pipeline risk.

### 3.8 Overnight drift / night vs day returns (graveyard candidate)

- **Mechanism.** Dealers absorb the end-of-day sell imbalance in the US and offload it when Europe opens (the 2:00 to 3:00 ET window). Separately, CAPM beta is priced overnight but not intraday.
- **References.**
  - Boyarchenko, Larsen & Whelan, *The Overnight Drift*, RFS 2023.
  - Lou, Polk & Skouras, *A Tug of War*, JFE 2019.
  - Hendershott, Livdan & Rösch, *Asset Pricing: A Tale of Night and Day*, JFE 2020.
  - Cooper, Cliff & Gulen (2008).
- **Decay.** The 2–3am window earned about 3.7%/yr before 2021 and has **averaged about zero since 2021**. Its link to end-of-day order imbalance broke down as end-of-day imbalances compressed by more than half (NY Fed Liberty Street, *The Disappearing Overnight Drift*, Jul 2026).
- **Use.** Cite as an example of an effect that died after publication, which justifies our conservative Sharpe expectations. Do not build on it.

### 3.9 Time-series momentum with volatility scaling; trend plus carry

- **References.**
  - Moskowitz, Ooi & Pedersen, JFE 2012.
  - Hurst, Ooi & Pedersen, JPM 2017.
  - Koijen, Moskowitz, Pedersen & Vrugt, *Carry*, JFE 2018.
  - Moreira & Muir, JF 2017.
  - Critiques: Huang, Li, Wang & Zhou, *Time Series Momentum: Is It There?*, JFE 2020 (little asset-level predictability; profits similar to a sample-mean strategy). Cederburg, O'Doherty, Wang & Yan, JFE 2020 (vol-managed portfolios underperform out of sample in 72 of 103 cases).
- **Assessment.** Data is easy and the strategy is robust, but judges will score **innovation low** ("plain textbook momentum"). Use TSMOM as a *factor in the regression* and as a diversification partner: our contrarian flow strategy should be negatively correlated with it.

### 3.10 Commodity index roll front-running and intermediate reversals

- **References.** Mou, *Limits to Arbitrage and Commodity Index Investment: Front-Running the Goldman Roll* (SSRN 2011). Henderson, Pearson & Wang (RFS 2015).
- **Documented performance.** Sharpe ratios up to 4.39 for 2000–2010, decreasing with arbitrage capital. Later work finds no abnormal profit after costs.
- **Assessment.** Decayed. A Sharpe above 3 would trip the "bug" rule. Curve construction from Databento futures is a lot of work for 24h. Graveyard.

### 3.11 Crypto carry / perpetual funding

- **References.** Schmeling, Schrimpf & Todorov, *Crypto Carry*, BIS WP 1087 (2023, rev. Oct 2025). He, Manela, Ross & von Wachter, *Fundamentals of Perpetual Futures* (WP 2022).
- **Documented performance.**
  - Carry averages above 10%/yr and sometimes exceeds 40%.
  - The cause is trend-chasing retail demand for leverage combined with limited arbitrage capital.
  - High carry predicts crashes.
- **Assessment.**
  - The sample is short (2019+), so the 2-year OOS is about 30% of the data.
  - Exchange counterparty risk (FTX) and Sharpe values above 3 in basis trades make it a judge red flag.
  - Capacity is limited.
- **Twist.** Use carry as a *crash-timing* signal for spot exposure rather than harvesting it. Interesting, but weak on the capacity and robustness criteria.

### 3.12 Stock/bond correlation regime (risk overlay, not alpha)

- **References.** Brixton, Brooks, Hecht, Ilmanen, Maloney & McQuinn, *A Changing Stock–Bond Correlation: Drivers and Implications*, JPM 2023. Campbell, Pflueger & Viceira, JPE 2020.
- **Use.** The correlation is positive when inflation is high and volatile. Going from −0.5 to +0.5 raises 60/40 volatility by about 20%. Use it for the IFC risk section (sleeve A's hedge weakens when correlation is above 0) and as a stress scenario. Not a standalone strategy.

### 3.13 Options-expiration week (OPEX) effect

- **References.** Stivers & Sun, *Returns and Option Activity over the Option-Expiration Week for S&P 100 Stocks* (2013) *(verify venue)*. Ni, Pearson & Poteshman (JFE 2005) on price clustering at expiration.
- **Documented performance.** For 1996–2008, OPEX-week returns averaged 0.45% vs 0.12% in other weeks, with a reversal the following week. Practitioner data says the four-day window around OPEX has been *negative* since 2020.
- **Assessment.** The sign is unstable across regimes and the theory is ambiguous (charm/vanna effects can go either way). Weak.

### 3.14 Massive "Trade the 8-K" bonus (optional add-on)

- **References.** Lerman & Livnat, *The New Form 8-K Disclosures*, Review of Accounting Studies 15(4) 2010. All 8-K items carry abnormal volume and volatility, and some items show post-filing drift.
- **Idea.** Implied volatility likely underprices *unscheduled* item categories (for example 5.02 executive departure, 4.02 non-reliance, 1.03 bankruptcy, 2.06 impairment). Buy short-dated straddles after filings in historically high realized/implied volatility categories (2022+ sample per the challenge), or sell implied volatility after low-information categories (8.01, 7.01).
- **Assessment.** Separate data pipeline (EDGAR plus Massive options), a short sample and option costs. Only pursue it if a second teammate has spare time.

---

## 4. Ranking (expected judge score = rationale × novelty × feasibility in 24h × robustness, each 1 to 5)

| # | Mechanism | Rationale | Novelty | Feasibility (24h) | Robustness | **Product** | Note |
|---|---|---|---|---|---|---|---|
| 1 | 3.1 Stock/bond rebalancing pressure (with settlement and dollar-flow twist) | 5 | 4 | 5 | 4 | **400** | 2025 paper, Sharpe 1.08 reported, effect said to be strengthening; ES/ZN only |
| 2 | 3.2 Dash for Cash plus T+3→T+2→T+1 natural experiment | 5 | 5 | 5 | 3 | **375** | Zero free parameters; OOS = pure T+1 regime; risk is a small effect |
| 3 | 3.3 Treasury month-end extension with issuance-DV01 sizing | 5 | 4 | 4 | 3 | **240** | Futures evidence exists; weaker after 2015; TLT failed, so use ZN/ZB |
| 4 | 3.4 FX hedge rebalancing with net TIC-weighted flow | 4 | 4 | 3 | 3 | **144** | Daily bars only approximate the fix; data alignment work |
| 5 | 3.7 LETF/gamma intraday momentum (Databento 1-min) | 5 | 3 | 3 | 3 | **135** | Best Databento showcase; intraday costs and 0DTE regime risk |
| 6 | 3.5 Macro announcement premium | 4 | 2 | 5 | 3 | 120 | Good overlay; low novelty |
| 7 | 3.6 VIX premium timing | 4 | 3 | 4 | 2 | 96 | Tail risk hurts the risk-management score |
| 8 | 3.9 TSMOM / trend plus carry | 4 | 1 | 5 | 4 | 80 | Use as benchmark and regression factor |
| 9 | 3.11 Crypto carry | 4 | 3 | 3 | 2 | 72 | Short sample, counterparty risk |
| 10 | 3.13 OPEX week | 3 | 2 | 5 | 1 | 30 | Unstable sign |
| 11 | 3.8 Overnight drift | 4 | 2 | 3 | 1 | 24 | Dead since 2021 |
| 12 | 3.10 Goldman roll | 4 | 2 | 2 | 1 | 16 | Arbitraged |
| — | 3.12 Correlation regime; 3.14 8-K | — | — | — | — | — | Overlay / bonus |

**Top 5 in one line each:**
1. **Rebalancing pressure:** strongest recent evidence, a clear counterparty (pensions/TDFs), capacity in the billions, and contrarian (diversifies trend).
2. **Settlement-cycle dash for cash:** the most *novel* claim we can make, with literally zero fitted parameters and a structural OOS test.
3. **Treasury EOM extension:** a classic forced flow from index rules. Issuance-DV01 sizing is our contribution and the rates leg diversifies equities.
4. **FX hedge rebalancing:** the same month-end institutional logic in a third asset class, strengthening the "flow clock" story.
5. **LETF/gamma intraday momentum:** strong mechanism plus the sponsor prize, but intraday and more crowded. Keep it as a stretch goal or a separate Databento appendix.

**Synthesis:** #1 to #4 share one economic story ("price-insensitive institutions trade on a calendar; we are paid to be the other side") and one data source (CME futures via Databento). Combine them as sleeves of a single strategy, the **Institutional Flow Clock**. That makes "Innovation" an architectural contribution (a unified counterparty map, settlement-aware timing, quantity-based sizing) rather than one tweak.

---

## 5. Suggested IFC specification (for the pre-registration commit)

**Universe.** ES (equity), ZN plus ZB (rates; DV01-weighted), and 6E, 6J, 6B (FX), all from Databento GLBX.MDP3 daily bars, 2010-06 to present. Pre-2010 robustness uses free proxies (S&P 500 index plus FRED Treasury yields for 1990–2010; FRED FX).

**Calendar primitives.** T = last trading day of the month (NYSE calendar for equities, SIFMA for rates). k = equity settlement lag: 3 before 2017-09-05, 2 until 2024-05-28, 1 afterwards. Treasury k = 1 throughout.

**Sleeves (signs and windows fixed from the literature).**
- **A Rebalance:** Signal = −(average over δ∈{0,0.5,1,1.5,2%} of the threshold drift) − (calendar drift × last-week dummy), computed on a simulated 60/40 ES/ZN portfolio. Position in ES minus duration-matched ZN.
- **B Dash:** long ES over [T−k, T+3]; flat or short over [T−k−5, T−k−1]; ×2.5 on Friday-T months (the multiplier comes from the paper; also report it unscaled).
- **C Treasury EOM:** long ZN/ZB over [T−3, T], sized by month-m coupon issuance DV01 relative to its trailing 12-month median (capped 0.5x to 2x).
- **D FX hedge:** for each currency, enter at T−2 and exit at T. The sign is the TIC-weighted net hedge flow based on month-to-date equity returns.

**Execution and lag.** The signal uses the close of day t−1 or earlier; enter at close t. As a conservative sensitivity, add a further one-day delay. All windows are known in advance because they depend only on the calendar plus lagged returns.

**Combination and risk.**
- Risk-parity across sleeves using 1-year trailing volatility of *sleeve P&L* (lagged).
- Portfolio vol target 8 to 10%; gross leverage cap.
- Per-sleeve stop: none. Pre-committed stops are another source of free parameters; report drawdown statistics instead.
- Stress tests: 2008, 2020-03, 2022 (positive stock/bond correlation), 2024-08.

**Costs (state in the note, then 2x).** ES 1 bp per side; ZN 1 bp; ZB 1.5 bp; 6E/6J/6B 1 bp; plus roll costs (each roll is an extra round trip). Pre-2010 proxies with SPY/IEF use 2 bp.

**Capacity.** Square-root impact: cost ≈ Y·σ_daily·√(Q/ADV) with Y ≈ 0.5 to 1 (Almgren et al. 2005; Tóth et al. 2011). Compute ADV *from the Databento volume field* rather than quoting it, and report the AUM at which impact eats 50% of the gross edge per sleeve. ES and ZN should support billions; FX sleeves are lower.

**Variant budget (for the Deflated Sharpe).** Pre-register about 8 to 12 variants and report all of them:
- Main spec.
- One-day extra lag.
- No Friday multiplier.
- No issuance sizing.
- Equal weight instead of risk parity.
- Without sleeve D.
- Fixed T+3 windows (the "no natural experiment" counterfactual).
- Calendar-only and threshold-only versions of A.
- Proxy-data 1990–2010 version.

**Evaluation.**
- In-sample 2010-06 to 2024-09, with the 1990–2010 proxy sample as a pre-sample check.
- **OOS 2024-10 to 2026-10, evaluated once.**
- Report the Sharpe ratio with Lo (2002) standard errors, the Deflated Sharpe (Bailey & López de Prado 2014), the Harvey, Liu & Zhu (2016) t > 3 hurdle, and the factor regression on MKT, HML and UMD (Ken French) plus AQR TSMOM.
- Per-sleeve attribution and a parameter-plateau plot (window ±2 days, δ range) to show robustness rather than to pick parameters.

**Draft hypothesis text (to commit before any backtest):**
> H0: Returns of liquid futures in calendar windows defined ex ante by institutional rebalancing rules, settlement lags and index month-end rules are no different from other days.
>
> H1 (rebalancing): after stocks outperform bonds, ES underperforms ZN over the next days, concentrated in the last trading week.
>
> H2 (settlement): US equity month-end selling pressure ends k trading days before month-end, where k is the settlement lag. The pattern shifts one day later in Sep 2017 and again in May 2024. Effects are larger when month-end is a Friday.
>
> H3 (index extension): Treasury futures earn positive excess returns over the last 3 trading days, increasing in that month's coupon issuance.
>
> H4 (FX hedging): currencies whose net cross-border hedge flow implies selling depreciate over [T−2, T].
>
> The out-of-sample period is the most recent 2 years and is evaluated once.

---

## 6. Key risks to flag in the note

- **Post-publication decay** (McLean & Pontiff, JF 2016: about 26% lower OOS and about 58% lower post-publication on average). The overnight drift, pre-FOMC and auction-cycle cases show this can go all the way to zero.
- **Crowding at month-end.** Sell-side desks publish rebalancing estimates, so the edge may have moved earlier in the month. The settlement analysis partly addresses this.
- **Concentration in time.** All sleeves trade around month-end, so a single bad month-end (for example a crisis turn) hits several sleeves at once. Mitigants: different asset classes, vol targeting, and a gross cap.
- **Regime risk.** Positive stock/bond correlation (2022) weakens sleeve A's hedge, and rate shocks hit sleeve C.
- **Execution realism.** Daily bars cannot capture the 4pm London fix or the exact close. Always report a one-day-extra-lag sensitivity.

---

## 7. References (with links used in this scan)

1. Harvey, Mazzoleni, Melone (2025, rev. 2026). *The Unintended Consequences of Rebalancing*. NBER WP 33554. https://www.nber.org/papers/w33554 ; slides (EDHEC, Feb 2026): https://www.edhec.edu/sites/default/files/2026-03/slides_EDHEC_Michele%20Mazzoleni%20%281%29.pdf ; Duke summary: https://www.fuqua.duke.edu/duke-fuqua-insights/what-do-pensions-lose-from-rebalancing
2. Etula, Rinne, Suominen, Vaittinen (2020). *Dash for Cash: Monthly Market Impact of Institutional Liquidity Needs*. RFS 33(1):75–111. https://acris.aalto.fi/ws/portalfiles/portal/40965155/hhz054.pdf
3. Hartley, Schwarz (2019). *Predictable End-of-Month Treasury Returns*. WP. https://rodneywhitecenter.wharton.upenn.edu/wp-content/uploads/2019/12/17-19.Schwarz.pdf ; CXO review (TLT caveat): https://www.cxoadvisory.com/bonds/term-premium-end-of-month-effect/
4. Lou, Yan, Zhang (2013). *Anticipated and Repeated Shocks in Liquid Markets*. RFS. https://ideas.repec.org/p/fmg/fmgdps/dp684.html
5. Fleming, Liu, Nguyen (2026). *Intraday Price Pressure and Order Flow Around U.S. Treasury Auctions*. NY Fed SR 1188. https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr1188.pdf
6. Melvin, Prins (2015). *Equity Hedging and Exchange Rates at the London 4 p.m. Fix*. JFM 22:50–72. https://ideas.repec.org/a/eee/finmar/v22y2015icp50-72.html
7. Krohn, Mueller, Whelan (2024). *Foreign Exchange Fixings and Returns Around the Clock*. JF 79(1):541–578. https://wrap.warwick.ac.uk/id/eprint/177333
8. Parker, Schoar, Sun (2023). *Retail Financial Innovation and Stock Market Dynamics: The Case of Target Date Funds*. JF 78(5). https://www.nber.org/papers/w28028
9. Savor, Wilson (2013), JFQA; Ai, Bansal (2018), Econometrica; Ai, Bansal, Guo (2023), *Macroeconomic Announcement Premium*, NBER 31923. https://www.nber.org/papers/w31923
10. Lucca, Moench (2015), JF; Kurov, Wolfe, Gilbert (2021), *The Disappearing Pre-FOMC Announcement Drift*, FRL 40. https://ideas.repec.org/a/eee/finlet/v40y2021ics1544612320315956.html
11. Cieslak, Morse, Vissing-Jorgensen (2019). *Stock Returns over the FOMC Cycle*. JF 74(5). https://papers.ssrn.com/abstract=2687614
12. Boyarchenko, Larsen, Whelan (2023). *The Overnight Drift*. RFS. https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf ; decay: https://libertystreeteconomics.newyorkfed.org/2026/07/the-disappearing-overnight-drift/
13. Hendershott, Livdan, Rösch (2020). *Asset Pricing: A Tale of Night and Day*. JFE. Lou, Polk, Skouras (2019). *A Tug of War*. JFE.
14. Gao, Han, Li, Zhou (2018). *Market Intraday Momentum*. JFE. Baltussen, Da, Lammers, Martens (2021). *Hedging Demand and Market Intraday Momentum*. JFE. https://www3.nd.edu/~zda/intramom.pdf
15. Barbon, Beckmeyer, Buraschi, Moerke (2021). *The Role of Leveraged ETFs and Option Market Imbalances on End-of-Day Price Dynamics*. WP. https://www.alexandria.unisg.ch/publications/264338 ; Barbon, Buraschi, *Gamma Fragility*. https://abarbon.com/papers/gamma-fragility
16. Zarattini, Aziz, Barbon (2024). *Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)*. SFI RP 24-97. https://ideas.repec.org/p/chf/rpseri/rp2497.html
17. Simon, Campasano (2014). *The VIX Futures Basis: Evidence and Trading Strategies*. J. Derivatives. Johnson (2017), JFQA. Cheng (2019). *The VIX Premium*. RFS 32(1):180–227. https://ideas.repec.org/a/oup/rfinst/v32y2019i1p180-227..html
18. Moskowitz, Ooi, Pedersen (2012), JFE; Hurst, Ooi, Pedersen (2017), JPM; Koijen, Moskowitz, Pedersen, Vrugt (2018), JFE; Moreira, Muir (2017), JF; Huang, Li, Wang, Zhou (2020), JFE 135(3) https://ideas.repec.org/a/eee/jfinec/v135y2020i3p774-794.html ; Cederburg, O'Doherty, Wang, Yan (2020), JFE 138(1) https://ideas.repec.org:443/a/eee/jfinec/v138y2020i1p95-117.html
19. Mou (2011). *Limits to Arbitrage and Commodity Index Investment: Front-Running the Goldman Roll*. https://papers.ssrn.com/abstract=1716841
20. Schmeling, Schrimpf, Todorov (2023, rev. 2025). *Crypto Carry*. BIS WP 1087. https://www.bis.org/publ/work1087.htm
21. Brixton, Brooks, Hecht, Ilmanen, Maloney, McQuinn (2023). *A Changing Stock–Bond Correlation: Drivers and Implications*. JPM.
22. Stivers, Sun (2013). *Returns and Option Activity over the Option-Expiration Week for S&P 100 Stocks* *(verify venue)*.
23. Lerman, Livnat (2010). *The New Form 8-K Disclosures*. RAST 15(4):752–778. https://ideas.repec.org/a/spr/reaccs/v15y2010i4d10.1007_s11142-009-9114-7.html
24. McLean, Pontiff (2016). *Does Academic Research Destroy Stock Return Predictability?* JF 71(1). Bailey, López de Prado (2014). *The Deflated Sharpe Ratio*. JPM. Harvey, Liu, Zhu (2016). *…and the Cross-Section of Expected Returns*. RFS. Almgren, Thum, Hauptmann, Li (2005), *Direct Estimation of Equity Market Impact*; Tóth et al. (2011), *Anomalous Price Impact and the Critical Nature of Liquidity*, PRX.
25. Databento CME history from 2010-06-06: https://databento.com/blog/CME-history-extended-to-2010 ; dataset docs: https://databento.com/docs/venues-and-datasets/glbx-mdp3
