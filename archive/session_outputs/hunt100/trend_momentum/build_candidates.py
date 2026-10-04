# Builds candidates.json, SPEC.md (pre-registration of rules and variants) and urls.txt for the trend_momentum hunt.
import json, os

OUT = os.path.dirname(os.path.abspath(__file__))

CONV = ("Common conventions unless a rule says otherwise: decisions at the close of day d with data through d; futures fill "
        "next_close, ETFs next_open; 'month-end' = last NYSE session of the month; returns are daily excess returns of the "
        "F_ total-return index (index return minus T-bill); sigma_i = sqrt(252*EWMA(r^2, com=60)); 'risk unit' weight = "
        "0.40/sigma_i/N_eligible; 'book to 10%' = rescale the weight vector so trailing-252-session covariance (min 60) gives "
        "10% annualised ex-ante vol, gross <= 3 (futures) or <= 2 (ETFs); eligibility = >= 260 sessions of history, positive "
        "sigma, traded in the last 10 sessions (as S1). Costs: the task's realistic one-way map, 2x stress; ETF shorts pay 30 bp/yr.")

FUT30 = "30 CME futures (F_ES F_NQ F_RTY F_YM F_ZT F_ZF F_ZN F_ZB F_UB F_CL F_HO F_RB F_NG F_GC F_SI F_PL F_HG F_ZC F_ZS F_ZW F_ZL F_ZM F_LE F_HE F_6E F_6J F_6B F_6A F_6C F_6S)"
COMM15 = "15 commodity futures (F_CL F_HO F_RB F_NG F_GC F_SI F_PL F_HG F_ZC F_ZS F_ZW F_ZL F_ZM F_LE F_HE)"
SECT9 = "9 SPDR sector ETFs (XLB XLE XLF XLI XLK XLP XLU XLV XLY)"

U = {
 'mop': "https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf",
 'aqr_tsmom': "https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Time-Series-Momentum-Factors-Monthly.xlsx",
 'hop17': "https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/AQR-JPM-Fall-2017.pdf",
 'hop13': "https://www.aqr.com/Insights/Research/Journal-Article/Demystifying-Managed-Futures",
 'babu_te': "https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/AQR-Trends-Everywhere_JOIM.pdf",
 'babu_ycat': "https://www.aqr.com/Insights/Research/Journal-Article/You-Cant-Always-Trend-When-You-Want",
 'invesco': "https://invesco.com/content/dam/invesco/emea/en/pdf/RRE_2024_Q2_NavigatingMomentum.pdf",
 'carver_live': "https://qoppac.blogspot.com/2025/04/annual-performance-update-returneth.html",
 'carver_cfg': "https://raw.githubusercontent.com/robcarver17/pysystemtrade/master/systems/provided/futures_chapter15/futuresconfig.yaml",
 'carver_repo': "https://github.com/robcarver17/pysystemtrade",
 'bk': "https://spiral.imperial.ac.uk/handle/10044/1/41472",
 'bk_ssrn': "https://papers.ssrn.com/abstract=2140091",
 'qc_bk': "https://www.quantconnect.com/learning/articles/investment-strategy-library/improved-momentum-strategy-on-commodities-futures",
 'lemp': "https://arxiv.org/abs/1404.3274",
 'turtle': "https://oxfordstrat.com/coasdfASD32/uploads/2016/01/turtle-rules.pdf",
 'szak': "https://ideas.repec.org/a/eee/jbfina/v34y2010i2p409-426.html",
 'clenow': "https://oreilly.com/library/view/following-the-trend/9781118410844",
 'lp16': "https://research.cbs.dk/en/publications/which-trend-is-your-friend/",
 'mtp': "https://benny.aeaweb.org/conference/2021/preliminary/paper/492Ds6fk",
 'ghm': "https://people.duke.edu/~charvey/Research/Published_Papers/P167_Breaking_bad_trends.pdf",
 'cxo_ghm': "https://www.cxoadvisory.com/technical-trading/mitigating-impact-of-price-turning-points-on-trend-following/",
 'dudler': "https://ideas.repec.org/p/chf/rpseri/rp1471.html",
 'durham': "https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr657.pdf",
 'amp': "https://www.johnhcochrane.com/s/Value-and-Momentum-Everywhere.pdf",
 'aqr_vme': "https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Value-and-Momentum-Everywhere-Factors-Monthly.xlsx",
 'aqr_century': "https://www.aqr.com/Insights/Datasets/Century-of-Factor-Premia-Monthly",
 'mr07': "https://risk.edhec.edu/publications/momentum-strategies-commodity-futures",
 'hpt': "https://centaur.reading.ac.uk/ (Hollstein, Prokopczuk & Tharann 2021, Quarterly Journal of Finance 11(4); SSRN 3567629)",
 'clare': "https://openaccess.city.ac.uk/id/eprint/17846/1/COMMODITY%20pAPER.pdf",
 'zu': "https://ideas.repec.org/a/eme/rbfpps/rbf-05-2019-0067.html",
 'bp': "https://ideas.repec.org/a/bla/jfinan/v74y2019i1p239-279.html",
 'bp_pdf': "https://4nations.albertjmenkveld.com/papers/boonsprado17.pdf",
 'msss': "https://www.bis.org/publ/work366.pdf",
 'cxo_fx': "https://www.cxoadvisory.com/momentum-investing/momentum-investing-for-currencies",
 'faber_rs': "https://c.mql5.com/forextsd/forum/213/Relative%20Strength%20Strategies%20for%20Investing.pdf",
 'french_ind': "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/10_Industry_Portfolios_CSV.zip",
 'zaremba_am': "https://gcris.yasar.edu.tr/handle/123456789/7291",
 'zaremba_var': "https://gcris.yasar.edu.tr/handle/123456789/7197",
 'bhv': "https://alphaarchitect.com/swedroe-spotlight-enhancing-momentum-strategies-via-idiosyncratic-momentum/",
 'bvd': "https://www3.nd.edu/~zda/Indexing.pdf",
 'wy': "https://ideas.repec.org/a/eee/jbfina/v28y2004i6p1337-1361.html",
 'qp_rev': "https://quantpedia.com/strategies/short-term-reversal-with-futures",
 'rzz_cxo': "https://www.cxoadvisory.com/commodity-futures/commodity-futures-term-structure-reversals",
 'rzz_rep': "https://quantreturns.substack.com/p/when-futures-overreact-a-weekly-edge",
 'za': "https://cmtassociation.org/wp-content/uploads/2026/02/Dow-Winner-A-Century-of-Profitable-Trends.pdf",
 'za_rep': "https://arxiv.org/abs/2412.14361",
 'faber07': "https://www.trendfollowing.com/whitepaper/CMT-Simple.pdf",
}

C = []
def add(**k):
    C.append(k)

add(id="trend_momentum_mop_tsmom12", name="Moskowitz-Ooi-Pedersen 12-month time-series momentum (30 futures)", family="time-series trend",
    sources=[U['mop'], U['aqr_tsmom'], U['hop13']], source_types=["journal", "dataset", "live fund"],
    exact_rule=("Month-end: for each eligible future, s_i = sign(cumulative excess return over the last 252 sessions). "
                "w_i = s_i * 0.40/sigma_i / N. Book to 10%. Hold to next month-end, next_close fills. Variants (pre-declared): "
                "V1 as stated; V2 skip-month 12-1 (sessions t-252..t-21); V3 no vol scaling (w_i = s_i/N equal notional, then book to 10%) "
                "to test the Kim-Tse-Wald (2016) claim that vol scaling drives TSMOM."),
    instruments=FUT30, data_needed="futures_daily close/volume, rf_daily",
    external_evidence=("MOP 2012: 58 futures 1985-2009, diversified TSMOM strongly significant. AQR TSMOM factor (gross, our calc from AQR file): "
                       "Sharpe 1.41 1985-2009, 0.39 post-publication 2012-05..2026-05, 0.03 for 2016-01..2024-09, 0.97 for 2024-10..2026-05. "
                       "Live: AQR Managed Futures fund AQMIX about 0.26 net since 2010; SG Trend Index 0.30 net 2000-2024 (0.41 2000-09, 0.21 2010-19). "
                       "Ours: TSMOM 12-month on 20 futures 0.28 IS / 0.14 later (old cost map)."),
    evidence_score=5, implementable=True,
    adaptation_note="Universe 30 CME futures instead of 58 global; already tested on 20 futures (TSMOM_F) - this reruns on 30 with the realistic cost map so it can sit in the top-10 table.",
    reuse_existing_series="")

add(id="trend_momentum_hop_1_3_12", name="Hurst-Ooi-Pedersen 1/3/12-month trend blend (century of trend)", family="time-series trend",
    sources=[U['hop17'], U['hop13'], U['babu_ycat'], U['invesco']], source_types=["journal", "practitioner", "live index"],
    exact_rule=("Month-end: s_i = mean(sign(R_21), sign(R_63), sign(R_252)) of cumulative excess returns; w_i = s_i*0.40/sigma_i/N; book to 10%, "
                "gross<=3, next_close. Variants: V1 monthly (identical to forward2 S1 rule); V2 weekly decisions (Friday close); "
                "V3 continuous horizon signals: each horizon h contributes clip(R_h/(sigma_daily*sqrt(h)), -1, 1) instead of the sign."),
    instruments=FUT30, data_needed="futures_daily, rf_daily",
    external_evidence=("HOP 2017: 67 markets 1880-2016, positive net Sharpe every decade; about 0.76 net of costs and 2/20 fees overall, 0.41 for 2010-16. "
                       "Babu et al. 2020: about 0.32 for 2010-18. Live: SG Trend 0.30 net (Dec 1999-Feb 2024), BTOP50 0.50 net 1987-2012. "
                       "Ours: S1 -0.13 IS / 0.14 later (S1 cost map 1.5/5 bp)."),
    evidence_score=5, implementable=True,
    adaptation_note="V1 gross is identical to forward2 S1 (src/forward2.py s1_decisions); only the cost map differs, so recompute net with the realistic map or reuse S1 gross.",
    reuse_existing_series="")

add(id="trend_momentum_carver_ewmac_breakout", name="Carver multi-speed EWMAC + breakout trend forecasts", family="time-series trend (continuous forecasts)",
    sources=[U['carver_cfg'], U['carver_repo'], U['carver_live']], source_types=["open-source code", "book", "live account blog"],
    exact_rule=("Daily on each future, price p = F_ total-return index level, price vol sigma_p = p * EWMA std of daily returns (span 35). "
                "EWMAC(f,s) raw = (EMA_f(p) - EMA_s(p))/sigma_p for (8,32),(16,64),(32,128),(64,256) with forecast scalars 5.3, 3.75, 2.65, 1.87. "
                "Breakout(N) raw = 40*(p - (max_N+min_N)/2)/(max_N-min_N), smoothed by EWMA span N/4, N in {20,40,80,160,320}, scalars 0.67, 0.70, 0.73, 0.74, 0.74. "
                "Each scaled forecast capped at +/-20; combined forecast = equal-weight average * FDM (FDM = 1/sqrt(w'Rw) from expanding forecast correlations, min 1y, cap 2.5), capped +/-20. "
                "w_i = (F_i/10) * 0.10/sigma_i / N, book to 10%; trade only when |target - current| > 10% of the average absolute position (buffer). "
                "Variants: V1 EWMAC only (4 speeds); V2 breakout only (5 lookbacks); V3 all 9 rules."),
    instruments=FUT30, data_needed="futures_daily close, rf_daily",
    external_evidence=("Carver live futures account (blog, net of all costs): UK tax years 2014/15-2024/25 returns 59.5, 28.1, 2.4, 2.0, 4.5, 33.8, -1.7, 25.8, -7.6, 20.6, -14.7%; "
                       "mean 12.9%, sd 16.8%, Sharpe 0.76 (rf=0), CAGR 12.0% vs SG CTA 6.4%; live system also holds carry and relative-value rules, and univariate trend rules lost in 2024/25. "
                       "Ours: long-short EWMAC about 0 IS / -0.35 later (V1 may coincide)."),
    evidence_score=4, implementable=True,
    adaptation_note="Uses the F_ total-return index as the back-adjusted price (adds T-bill drift, negligible for the signal); 30 instruments vs Carver's 100+; forecast scalars taken from pysystemtrade defaults, not refitted.",
    reuse_existing_series="")

add(id="trend_momentum_carver_staunch_trend_carry", name="Carver 'staunch systems trader' EWMAC + carry system", family="trend + carry composite",
    sources=[U['carver_cfg'], U['carver_live'], U['carver_repo']], source_types=["open-source code", "book", "live account blog"],
    exact_rule=("Forecasts per pysystemtrade chapter-15 config: EWMAC16/64 (scalar 3.75), EWMAC32/128 (2.65), EWMAC64/256 (1.87) as in the EWMAC candidate; "
                "carry raw = annualised roll yield between front (.v.0) and second (.v.1) contract / annualised price vol, smoothed EWMA 90 days, scalar 30; "
                "each capped +/-20; combined with weights 0.21/0.08/0.21/0.50 and FDM 1.31, capped +/-20; w_i = (F_i/10)*0.10/sigma_i/N, book to 10%, daily with 10% buffer. "
                "Variants: V1 as configured; V2 equal 0.25 weights on the four rules (FDM refit in-sample); V3 trend-only sub-portfolio of V1 (weights renormalised) to measure the carry contribution."),
    instruments=FUT30, data_needed="futures_daily; databento_raw glbx_ohlcv1d_v01 front/second closes + expiry months via free symbology.resolve (or reuse the edges carry C1 signal)",
    external_evidence=("Same live record as above (Sharpe 0.76 rf=0, 2014-2025, net); config is Carver's published example system. "
                       "Carry sleeves in our edge study are separate series (edges/series/carry_ts_global)."),
    evidence_score=4, implementable=True,
    adaptation_note="Carry from adjacent-contract prices in databento_raw; annualise with the month gap between the two contract codes. Overlaps the edge-search carry sleeve; this tests Carver's fixed combination, not a new carry signal.",
    reuse_existing_series="")

add(id="trend_momentum_bk_trend_tstat_cf", name="Baltas-Kosowski TREND t-stat signal, Yang-Zhang vol and correlation factor", family="time-series trend (trend-strength filter, correlation-adjusted)",
    sources=[U['bk'], U['bk_ssrn'], U['qc_bk']], source_types=["journal/working paper", "independent replication (QuantConnect)"],
    exact_rule=("Month-end, each future: regress log(F_ index) on a time index over the last 252 sessions; X_i = +1 if Newey-West t(slope) > 2, -1 if < -2, else 0 (TREND rule). "
                "Vol = Yang-Zhang estimator on 63 sessions of OHLC. Correlation factor CF = sqrt(N/(1+(N-1)*rho_bar)), rho_bar = average pairwise correlation of the "
                "signed daily returns X_j*r_j over the trailing 126 sessions (active instruments). w_i = X_i * (0.10*CF)/sigma_i^YZ / N (natural sizing, no covariance rescale), gross<=3. "
                "Variants: V1 TREND+YZ+CF; V2 TREND+YZ with CF=1 then book to 10%; V3 SIGN(12m)+EWMA vol+CF (isolates the correlation adjustment)."),
    instruments=FUT30, data_needed="futures_daily OHLC, rf_daily",
    external_evidence=("B&K (2015 version): 75 futures 1974-2013; full-sample TSMOM Sharpe 1.04 vs 1.05 with CF; post-GFC 2009-01..2013-02 0.14 -> 0.29 gross, "
                       "0.12 -> 0.26 at 10 bp and 0.05 -> 0.14 at 50 bp costs; YZ cuts turnover about 8%, YZ+TREND by more than one third without significant performance loss. "
                       "Replicated in the QuantConnect strategy library (commodities)."),
    evidence_score=3, implementable=True,
    adaptation_note="NW lag = 21 sessions (paper does not fix it in the extract read); YZ on total-return-index OHLC; 30 instead of 75 instruments.",
    reuse_existing_series="")

add(id="trend_momentum_lemperiere_ema", name="Lemperiere et al. 'Two centuries of trend following' EMA-deviation signal", family="time-series trend",
    sources=[U['lemp']], source_types=["journal (Journal of Investment Strategies)", "arXiv"],
    exact_rule=("Month-end closes of the F_ index p. pbar_n = EMA of past month-end prices excluding the current one, decay n months (alpha=1/n); "
                "sigma_n = EMA (decay n) of |monthly price changes|. s = (p_t - pbar_n,t)/sigma_n,t. w_i = sign(s_i)*0.40/sigma_i/N, book to 10%, next_close, hold one month. "
                "Variants: V1 n=5 months; V2 n=10; V3 saturating w_i proportional to tanh(s_i) (paper's saturation finding) with n=5."),
    instruments=FUT30, data_needed="futures_daily, rf_daily",
    external_evidence=("Futures 1960-2013 (n=5): Sharpe about 0.8 gross, t=5.9 (de-biased 5.0); decades 0.66, 1.15, 1.05, 1.12 and 0.75 after 2000; Sharpe 0.57-0.83 for n=2..10. "
                       "Spot data 1800-2013 Sharpe 0.72, t=10.5. Paper's own Figure 6: strategy virtually flat since 2011; a 3-day trend disappeared after 2003. No costs modelled."),
    evidence_score=4, implementable=True,
    adaptation_note="Paper sizes in contract units by 1/sigma_n; here sized by EWMA return vol to sit on the common risk framework.",
    reuse_existing_series="")

add(id="trend_momentum_turtle_donchian", name="Turtle Donchian breakout (System 1 20/10, System 2 55/20) with N-based units", family="breakout",
    sources=[U['turtle'], U['szak'], U['carver_repo']], source_types=["public trading rules", "journal", "open-source code"],
    exact_rule=("Daily on each future (F_ index OHLC). N = Wilder 20-day EMA of true range. Unit weight = 0.01/(N/close) of equity. "
                "System 2: long when close > highest close of the prior 55 sessions, short when < lowest of prior 55; exit long at a 20-session low close, exit short at a 20-session high close; "
                "2N protective stop from the entry price. System 1: 20-session entry / 10-session exit, skip an entry if the previous System-1 signal in that market would have been a winner. "
                "Book rescaled to 10% ex-ante at each decision, gross<=3, next_close. Variants: V1 System 2 single unit; V2 System 1 with skip filter, single unit; "
                "V3 System 2 with pyramiding (add 1 unit per +N/2, max 4 units per market, stops moved to 2N below the latest unit)."),
    instruments=FUT30, data_needed="futures_daily OHLC, rf_daily",
    external_evidence=("Rules: originalturtles.org (2003). Szakmary-Shen-Sharma 2010: channel and dual-MA rules net of costs positive in at least 22 of 28 commodity markets over 48 years, robust to subperiods and data-mining adjustments. "
                       "Breakout is one of the live rule families in Carver's account (Sharpe 0.76 2014-2025, multi-rule). Lemperiere et al.: very short trends (3-day) died after 2003 - System 1 at risk."),
    evidence_score=3, implementable=True,
    adaptation_note="Close-based channels on the total-return index instead of intraday highs/lows of the outright contract; the 1%-per-N sizing is replaced by the 10% book scaling.",
    reuse_existing_series="")

add(id="trend_momentum_clenow_core", name="Clenow 'Following the Trend' core model (EMA filter + 50-day breakout + 3 ATR stop)", family="breakout",
    sources=[U['clenow']], source_types=["practitioner book"],
    exact_rule=("Daily. Filter: long trades only if EMA50 > EMA100, short only if EMA50 < EMA100 (F_ index). Entry long when close equals the highest close of 50 sessions and the filter is long; "
                "short when close equals the 50-session lowest close and filter short. Exit: trailing stop 3*ATR(100) from the highest close since entry (long) or lowest (short). "
                "Size: weight_i = 0.002/(ATR100_i/close_i) (0.2% of equity per ATR), natural sizing, gross<=3, next_close. "
                "Variants: V1 as stated; V2 no EMA filter; V3 100-session breakout with the same filter and stop."),
    instruments=FUT30, data_needed="futures_daily OHLC, rf_daily",
    external_evidence=("Author's backtest on about 50 futures 1990-2011 (first edition) and year-by-year attribution 2002-2021 in the second edition; no independent post-publication record found (book numbers not verified here)."),
    evidence_score=2, implementable=True,
    adaptation_note="Clenow trades ~50 global futures; we use 30 CME. Natural ATR sizing kept; report realised vol, and a 10%-scaled copy for comparison.",
    reuse_existing_series="")

add(id="trend_momentum_dual_sma", name="Moving-average trend rules (50/200 crossover, price vs 10-month SMA, channel midpoint)", family="time-series trend",
    sources=[U['szak'], U['clare'], U['lp16']], source_types=["journal"],
    exact_rule=("Each future, risk unit 0.40/sigma_i/N, book to 10%. V1 weekly (Friday close): s = +1 if SMA50 > SMA200 of the F_ index else -1. "
                "V2 monthly: s = +1 if month-end price > average of the last 10 month-end prices else -1. "
                "V3 weekly channel: s = sign(close - (max_250 + min_250)/2)."),
    instruments=FUT30, data_needed="futures_daily, rf_daily",
    external_evidence=("Szakmary et al. 2010 (JBF): all dual-MA and channel parameterisations net-positive in >= 22 of 28 commodities, 1959-2007. Clare et al. 2014: 6-12 month MA trend filters "
                       "raise commodity Sharpe vs long-only and momentum (1992-2011). Levine & Pedersen 2016: MA crossovers and TSMOM are near-equivalent linear filters."),
    evidence_score=3, implementable=True,
    adaptation_note="Weekly decisions limit turnover; the rule set is a classic benchmark family and overlaps S1 conceptually (expect correlation > 0.7).",
    reuse_existing_series="")

add(id="trend_momentum_turning_points", name="Momentum turning points: slow/fast blend (Garg et al.; Goulding-Harvey-Mazzoleni 'Breaking Bad Trends')", family="time-series trend (dynamic speed)",
    sources=[U['mtp'], U['ghm'], U['cxo_ghm']], source_types=["journal (JFE 2023; FAJ 2024)", "summary"],
    exact_rule=("Month-end per future: slow = sign(R_12m), fast = sign(R_kf) with kf months. State: Bull (both >= 0), Bear (both < 0), Correction (slow>=0, fast<0), Rebound (slow<0, fast>=0). "
                "Position x = +1 Bull, -1 Bear, 1-2*a_Co after Correction, 2*a_Re-1 after Rebound. Dynamic a's (GHM eq. 8-10, expanding window of prior months): "
                "a_Co = 0.5*(1 - (1/C)*AVG(r|Co)/AVG(r^2|Co)), a_Re = 0.5*(1 + (1/C)*AVG(r|Re)/AVG(r^2|Re)), C = FREQ(Bu)/FREQ(Bu or Be)*AVG(r|Bu)/AVG(r^2|Bu) - FREQ(Be)/FREQ(Bu or Be)*AVG(r|Be)/AVG(r^2|Be), "
                "r = next-month excess return, clipped to [0,1]; until 48 months exist, a = 0.5. w_i = x_i*0.40/sigma_i/N, book to 10%. "
                "Variants: V1 static MED (a=0.5, kf=1); V2 static MED with kf=2; V3 dynamic with kf=2, a's estimated pooled across all 30 futures (more data)."),
    instruments=FUT30, data_needed="futures_daily, rf_daily",
    external_evidence=("Garg et al.: US equity market, MED (a=0.5) highest Sharpe 0.51 vs about 0.38 for slow 12m (gross), dynamic speed efficient out of sample over the last 50 years. "
                       "GHM 2024: 55 assets 1990-2022 at 10% vol, static 12m trend 6.4%/yr full period but 0.3%/yr in 2009-19, dynamic 3.4%/yr in 2009-19 (CXO: 30y 7.5% vs 9.4%, 10y 1.8% vs 4.3%); gross; costs below about 29 bp keep the dynamic edge."),
    evidence_score=3, implementable=True,
    adaptation_note="Dynamic a's need long state histories; our futures start 2010-06, so V3 pools states across instruments and uses a=0.5 until 48 pooled months.",
    reuse_existing_series="")

add(id="trend_momentum_ramom", name="Risk-adjusted time-series momentum (RAMOM, Dudler-Gmur-Malamud)", family="time-series trend (risk-adjusted signal)",
    sources=[U['dudler']], source_types=["working paper (Swiss Finance Institute)"],
    exact_rule=("Month-end per future: z_L = sum of the last L daily excess returns / (std of those returns * sqrt(L)) (t-stat of the mean). "
                "x_i = clip(z_L/2, -1, 1); w_i = x_i*0.40/sigma_i/N; book to 10%, next_close. Variants: V1 L=252; V2 L=63; V3 average of x over L in {21,63,126,252}."),
    instruments=FUT30, data_needed="futures_daily, rf_daily",
    external_evidence=("64 liquid futures: RAMOM beats MOP TSMOM for almost all look-back/holding combinations, about 40% lower dollar turnover, lower MKT/HML/UMD exposure (SFI RP 14-71, 2015). No post-publication record found."),
    evidence_score=2, implementable=True,
    adaptation_note="Continuous clipped signal is our implementation of 'average past returns normalised by vol'; scale constant 2 fixed a priori.",
    reuse_existing_series="")

add(id="trend_momentum_bond_tsmom", name="Time-series momentum on US Treasury futures only", family="time-series trend (bonds)",
    sources=[U['aqr_tsmom'], U['mop'], U['durham']], source_types=["dataset", "journal", "central bank staff report"],
    exact_rule=("Universe ZT, ZF, ZN, ZB, UB. Month-end: V1 s = sign(R_252); V2 s = mean of signs over 21/63/252; V3 Carver forecast (EWMAC16/64 + EWMAC64/256, equal weight, scalars 3.75/1.87, cap 20)/10. "
                "w_i = s_i*0.40/sigma_i/N, book to 10% with the 5x5 covariance, gross<=3, next_close."),
    instruments="F_ZT F_ZF F_ZN F_ZB F_UB", data_needed="futures_daily, rf_daily",
    external_evidence=("AQR TSMOM^FI factor (gross, our calc): 0.71 for 1985-2009, 0.33 post-publication 2012-05..2026-05, 0.35 for 2016-01..2024-09 (best asset class after publication), "
                       "-0.54 for 2024-10..2026-05. Durham (NY Fed SR 657): price momentum along the Treasury curve 1997-2013, IR up to 0.79."),
    evidence_score=4, implementable=True,
    adaptation_note="AQR uses 13 global bond futures; ours is the US curve only (pairwise correlations 0.6-0.95), so effectively one duration-timing bet.",
    reuse_existing_series="")

add(id="trend_momentum_durham_curve_xsmom", name="Duration-neutral cross-sectional momentum along the Treasury curve (Durham)", family="cross-sectional momentum (bonds)",
    sources=[U['durham']], source_types=["central bank staff report"],
    exact_rule=("Month-end over ZT, ZF, ZN, ZB, UB: signal = cumulative excess return over months t-12..t-2 (skip the most recent month) divided by trailing 252-session vol. "
                "Long the top 2, short the bottom 2, each leg risk-parity weighted (1/sigma) and the legs scaled to equal ex-ante vol so net duration risk is about zero; book to 10%, next_close. "
                "Variants: V1 2-12 window top2/bottom2; V2 5-12 window (paper's best lag); V3 demeaned z-score weights over all five instead of ranks."),
    instruments="F_ZT F_ZF F_ZN F_ZB F_UB", data_needed="futures_daily, rf_daily",
    external_evidence=("Durham 2013 (US Treasury duration buckets, Dec 1996-Jul 2013): duration-neutral long-only momentum up to 120 bp/yr, IR up to 0.79; 2-12 month window 150 bp, IR 0.64 (t 8.8); "
                       "long-short with no duration risk up to 207 bp, IR 1.01. Gross; costs break-even analysed. Post-2013 is out of sample; no later study found."),
    evidence_score=2, implementable=True,
    adaptation_note="Paper uses Bloomberg/Barclays maturity-bucket indices with an optimiser; we use the 5 futures and a rank rule, vol-matched legs instead of exact DV01.",
    reuse_existing_series="")

add(id="trend_momentum_xsmom_futures_amp", name="Cross-sectional 12-1 momentum within futures asset classes (Asness-Moskowitz-Pedersen)", family="cross-sectional momentum",
    sources=[U['amp'], U['aqr_vme'], U['aqr_century']], source_types=["journal", "dataset"],
    exact_rule=("Month-end, within each class (equity 4, rates 5, FX 6, commodities 15): signal = cumulative excess return over t-252..t-21 sessions; w_i proportional to rank_i - mean rank (zero-sum within class); "
                "each class sleeve scaled to equal ex-ante vol, total book to 10%, next_close. Variants: V1 as stated; V2 rank of vol-adjusted signal (return/sigma); V3 pooled ranking across all 30 (no class neutrality)."),
    instruments=FUT30, data_needed="futures_daily, rf_daily",
    external_evidence=("AQR VME MOM^AA (non-stock asset classes, gross, our calc): 0.43 for 1972-2011, -0.08 post-publication 2013-07..2026, -0.38 for 2016-01..2024-09; "
                       "Century 'All Macro Momentum' 0.58 (1981-2011) vs -0.01 (2012-2026). Edge study's value_reversal_MOM_XS (MOM2-12, from 2016) is related but uses different costs/window."),
    evidence_score=3, implementable=True,
    adaptation_note="Equity class has only 4 highly correlated US indices; expect the equity sleeve to be noise. Post-publication evidence is negative - include as an honest baseline.",
    reuse_existing_series="")

add(id="trend_momentum_commodity_xsmom", name="Commodity cross-sectional momentum (Miffre-Rallis 12/1)", family="cross-sectional momentum (commodities)",
    sources=[U['mr07'], U['hpt'], U['aqr_vme'], U['zu']], source_types=["journal", "post-publication study", "dataset"],
    exact_rule=("Month-end over the 15 commodities: rank on the 12-month cumulative excess return; long the top 3 (quintile), short the bottom 3; hold one month; next_close; book to 10%. "
                "Variants: V1 equal weight within legs; V2 inverse-vol (1/sigma_i) weights; V3 6-month formation."),
    instruments=COMM15, data_needed="futures_daily, rf_daily",
    external_evidence=("Miffre & Rallis 2007 (31 commodities 1979-2004): 13 profitable momentum strategies; 12m/1m best at 14.6%/yr, vol 25.6%. Hollstein-Prokopczuk-Tharann 2021: 1-year momentum 7.44%/yr significant full sample "
                       "but 'much attenuated' post-financialisation. AQR VME commodity momentum 0.52 (1972-2011) vs -0.20 post-publication; Century commodities momentum -0.02 (2012-2026)."),
    evidence_score=3, implementable=True,
    adaptation_note="15 instead of 27-31 commodities (no softs, no LME metals).",
    reuse_existing_series="")

add(id="trend_momentum_commodity_dual_mom_clare", name="Trend-filtered commodity momentum (Clare-Seaton-Smith-Thomas)", family="cross-sectional momentum with trend filter",
    sources=[U['clare']], source_types=["journal (IRFA 2014)"],
    exact_rule=("Month-end over the 15 commodities: winners = top third by 12-month return, losers = bottom third. Hold a winner long only if its month-end price > its 7-month SMA of month-end prices; "
                "short a loser only if price < its 7-month SMA; otherwise that slot is in cash. Weights proportional to 1/sigma_60d (risk parity); book to 10%, next_close. "
                "Variants: V1 winners-minus-losers, 7-month MA; V2 long-only filtered winners; V3 12-month MA."),
    instruments=COMM15, data_needed="futures_daily, rf_daily",
    external_evidence=("Clare et al. 2014 (1992-2011, gross): trend-filtered winner-loser portfolio 15.94%/yr excess, Sharpe 0.82, positive in the 2008 crisis; trend filter cuts momentum drawdowns and negative skew. No post-publication record found."),
    evidence_score=2, implementable=True,
    adaptation_note="Paper's universe is broader (S&P GSCI components); ours 15 CME commodities.",
    reuse_existing_series="")

add(id="trend_momentum_commodity_52wk_high", name="52-week-high momentum in commodity futures (George-Hwang adapted)", family="cross-sectional momentum (anchoring)",
    sources=[U['zu']], source_types=["journal (Review of Behavioral Finance 2020)"],
    exact_rule=("Month-end over the 15 commodities: signal = F_ index close / max(F_ close over the last 252 sessions). Long top 3, short bottom 3, inverse-vol weights, hold one month, book to 10%, next_close. "
                "Variants: V1 monthly; V2 6-month overlapping holding (six monthly cohorts, 1/6 each); V3 applied within each class of all 30 futures (zero-sum within class)."),
    instruments=COMM15, data_needed="futures_daily, rf_daily",
    external_evidence=("Zhang & Urquhart 2020: across 189 formation-holding windows, conventional and 52-week-high momentum earn statistically and economically significant profits in commodity futures; no reversal profits; crashes partly predictable. No post-publication record."),
    evidence_score=2, implementable=True,
    adaptation_note="Uses the total-return index (roll-adjusted) rather than outright prices, since outright 52-week highs are distorted by rolls.",
    reuse_existing_series="")

add(id="trend_momentum_basis_momentum", name="Basis-momentum (Boons-Prado): front minus second-contract 12-month momentum", family="curve momentum",
    sources=[U['bp'], U['bp_pdf']], source_types=["journal (Journal of Finance 2019)"],
    exact_rule=("Daily front (.v.0) and second (.v.1) contract returns from databento_raw, each computed only when the instrument_id is unchanged from the previous session (roll days use the held contract's own previous close when present, else 0). "
                "Month-end: BM_i = prod(1+r1 over 12 months) - prod(1+r2 over 12 months). Cross-section over the 15 commodities: long the 4 highest BM, short the 4 lowest, positions in the F_ front index, "
                "hold one month, next_close, book to 10%. Variants: V1 equal weight High4-Low4; V2 inverse-vol weights; V3 time-series sign(BM_i) per commodity, risk units, book to 10%."),
    instruments=COMM15 + "; databento_raw front/second closes", data_needed="databento_raw/glbx_ohlcv1d_v01.parquet (.v.0/.v.1 close, instrument_id), futures_daily",
    external_evidence=("Boons & Prado 2019: 21 commodities 1960-2014, High4-Low4 nearby return 18.38%/yr (t 6.73), Sharpe about 0.9, robust pre/post 1986, beats basis and momentum; predicts out of sample in 48 currencies. "
                       "Hollstein et al. 2021 cite it; no post-2014 replication found."),
    evidence_score=2, implementable=True,
    adaptation_note="Databento .v.1 is the second-highest-volume contract, usually the next expiry; returns on .v.1 roll days are approximated.",
    reuse_existing_series="")

add(id="trend_momentum_fx_xsmom", name="Currency momentum across G10 FX futures (Menkhoff-Sarno-Schmeling-Schrimpf)", family="cross-sectional momentum (FX)",
    sources=[U['msss'], U['cxo_fx'], U['aqr_vme']], source_types=["journal (JFE 2012)", "dataset"],
    exact_rule=("Month-end over 6E, 6J, 6B, 6A, 6C, 6S: rank by past excess return; long the top 2, short the bottom 2, equal risk (1/sigma), hold one month, book to 10%, next_close. "
                "Variants: V1 1-month formation (MSSS strongest); V2 3-month; V3 12-month."),
    instruments="F_6E F_6J F_6B F_6A F_6C F_6S", data_needed="futures_daily, rf_daily",
    external_evidence=("MSSS 2012: 48 currencies 1976-2010, winner-loser spread up to 10%/yr gross, best strategy about 4%/yr after transaction costs, profits concentrated in less liquid currencies. "
                       "AQR VME FX momentum 0.33 (1972-2011) vs -0.04 post-publication; Century currencies momentum -0.14 (2012-2026)."),
    evidence_score=3, implementable=True,
    adaptation_note="Only 6 G10 USD crosses (MSSS effect is weakest in G10).",
    reuse_existing_series="")

add(id="trend_momentum_sector_rs", name="Sector relative strength rotation (Faber 2010) on SPDR sector ETFs", family="cross-sectional momentum (ETF sectors)",
    sources=[U['faber_rs'], U['french_ind']], source_types=["practitioner paper (SSRN)", "dataset (our post-publication calc)"],
    exact_rule=("Month-end: rank the 9 sector ETFs by the average of trailing 1, 3, 6, 9 and 12-month total returns (adjusted closes); hold the top 3 equally weighted for one month; next_open; ETF cost map. "
                "Variants: V1 long-only top 3 (natural sizing, 100% invested); V2 V1 but in T-bills when SPY's month-end close is below its 10-month SMA; V3 top 3 minus bottom 3 (shorts pay 30 bp/yr), book to 10%."),
    instruments=SECT9 + " (+SPY for V2)", data_needed="etf_daily, rf_daily",
    external_evidence=("Faber 2010: French 10 industries 1928-2009, relative-strength portfolios beat buy-and-hold in about 70% of years. Our calc on French 10 VW industries (gross): top3 minus equal-weight Sharpe 0.43 for 1928-2009, "
                       "0.30 for 2010-01..2026-08 (post-publication), 0.47 for 2016-01..2024-09; top3 excess Sharpe 0.89 vs EW10 0.84 post-2010; Moskowitz-Grinblatt 6m top3-bottom3 0.42 in 1963-95 vs 0.25 after 1999-08."),
    evidence_score=3, implementable=True,
    adaptation_note="9 SPDR sectors (from 1998/2003 in etf_daily) instead of French 10 industries.",
    reuse_existing_series="")

add(id="trend_momentum_country_etf_xsmom", name="Regional equity index momentum with ETFs", family="cross-sectional momentum (ETF countries)",
    sources=[U['amp'], U['aqr_vme'], U['aqr_century']], source_types=["journal", "dataset"],
    exact_rule=("Month-end over SPY, VGK, EWJ, EEM (EFA excluded as the sum of VGK and EWJ): signal = 12-1 month return (t-252..t-21 sessions). "
                "V1 long top 2 / short bottom 2, inverse-vol weights, shorts pay 30 bp/yr, book to 10%; V2 6-month formation; V3 long-only top 2 minus equal-weight of the four (relative return), book to 10%. next_open."),
    instruments="SPY VGK EWJ EEM", data_needed="etf_daily, rf_daily",
    external_evidence=("AQR VME country-index momentum (18 equity index futures, gross, our calc): 0.58 for 1972-2011 vs 0.13 post-publication 2013-07..2026; Century equity-indices momentum 0.72 (1981-2011) vs 0.35 (2012-2026), 0.02 for 2016-2024."),
    evidence_score=2, implementable=True,
    adaptation_note="Only four regions - very thin cross-section; results will be dominated by US vs rest-of-world.",
    reuse_existing_series="")

add(id="trend_momentum_residual_sector_mom", name="Residual (alpha) momentum on sector ETFs (Blitz-Huij-Martens / Zaremba VARMOM)", family="residual momentum",
    sources=[U['zaremba_am'], U['zaremba_var'], U['bhv']], source_types=["journal", "practitioner summary"],
    exact_rule=("Month-end: for each sector ETF regress daily excess returns on SPY excess returns over the trailing 756 sessions (min 504); residual momentum = sum of residuals over sessions t-252..t-21 divided by their std (volatility-adjusted residual momentum). "
                "Long the top 3, short the bottom 3, leg weights set so the net SPY beta is zero, shorts pay 30 bp/yr, book to 10%, next_open. Variants: V1 VARMOM 12-1; V2 raw residual sum; V3 6-1 window."),
    instruments=SECT9 + " + SPY", data_needed="etf_daily, rf_daily",
    external_evidence=("Zaremba-Umutlu-Karathanasopoulos 2019: 51 country indices 1973-2018, short-term alpha momentum predicts returns and subsumes return momentum; Zaremba-Umutlu-Maydybura: VARMOM in 51 country and 888 industry indices gives Sharpe 2-3x standard momentum. "
                       "Blitz-Hanauer-Vidojevic 2020: idiosyncratic momentum robust across developed and emerging stock markets."),
    evidence_score=2, implementable=True,
    adaptation_note="Industry-level evidence is from broad global industry panels; 9 US sectors is a narrow adaptation.",
    reuse_existing_series="")

add(id="trend_momentum_residual_futures_mom", name="Idiosyncratic momentum within futures asset classes", family="residual momentum",
    sources=[U['bhv'], U['zaremba_var']], source_types=["journal (equity evidence, adapted)"],
    exact_rule=("Month-end: for each future regress daily excess returns over the trailing 252 sessions on its class factor (equal-weight average of the other members of its class: commodities, FX, rates, equity); "
                "signal = sum of residuals over t-252..t-21 / their std. Within-class zero-sum rank weights, class sleeves equal vol, book to 10%, next_close. "
                "Variants: V1 commodities only; V2 all four classes; V3 factor = first principal component of the 30 futures (trailing 252 sessions)."),
    instruments=FUT30, data_needed="futures_daily, rf_daily",
    external_evidence=("No direct futures study found; adaptation of stock-level residual momentum (Blitz et al. 2011, 2020) and country/industry VARMOM (Zaremba et al.)."),
    evidence_score=1, implementable=True,
    adaptation_note="Pure adaptation; treat as exploratory.",
    reuse_existing_series="")

add(id="trend_momentum_index_mac5_reversal", name="Equity index short-term reversal (Baltussen-van Bekkum-Da MAC(5))", family="short-term reversal",
    sources=[U['bvd']], source_types=["journal (JFE 2019)"],
    exact_rule=("Daily on ES, NQ, RTY, YM: x_i = -(4 r_t + 3 r_{t-1} + 2 r_{t-2} + r_{t-3})/(10*sigma_daily) with r = daily excess returns through close d; position clip(x_i, -2, 2)*0.10/sigma_i/4; book to 10%. "
                "Variants: V1 next_close fills (one-day implementation lag); V2 next_open fills; V3 weekly: position = -sign(5-session return), decided Friday close, next_close."),
    instruments="F_ES F_NQ F_RTY F_YM", data_needed="futures_daily, rf_daily",
    external_evidence=("BvD: index serial dependence turned negative after the 2000s in 20 indices; a strategy trading against MAC(5) earns Sharpe 0.63 (all indices) and 0.67 (S&P 500) after 1999-03 to 2016, gross, no lag. "
                       "With a one-day implementation lag the pooled post-1999 coefficient is -0.016 (t -0.60), i.e. insignificant; authors warn costs may eliminate it."),
    evidence_score=2, implementable=True,
    adaptation_note="Our engine cannot fill at the same close that generates the signal; V1/V2 are the implementable lagged versions, which the paper itself shows are much weaker.",
    reuse_existing_series="")

add(id="trend_momentum_weekly_xs_reversal", name="Weekly cross-sectional reversal in futures (Wang-Yu)", family="short-term reversal",
    sources=[U['wy'], U['qp_rev'], U['zu']], source_types=["journal", "strategy database"],
    exact_rule=("Each Friday close: past-week return (Fri-to-Fri) and past-week volume relative to its 52-week average for each future. Among futures with above-median relative volume, "
                "long the third with the lowest past-week return, short the third with the highest; inverse-vol weights; hold one week; next_close; book to 10%. "
                "Variants: V1 high-volume half of all 30; V2 no volume condition; V3 ranks within asset class (zero-sum per class)."),
    instruments=FUT30, data_needed="futures_daily close and volume, rf_daily",
    external_evidence=("Wang & Yu 2004: 24 US futures, strong weekly return reversals, strongest with high volume and falling open interest. Contrary: Miffre-Rallis 2007, Bianchi et al. 2015 and Zhang-Urquhart 2020 (189 windows) find no reversal profits; Hollstein et al. 2021: reversal unpriced."),
    evidence_score=1, implementable=True,
    adaptation_note="Open interest is not in our data, so the OI-decline condition is replaced by relative volume.",
    reuse_existing_series="")

add(id="trend_momentum_basis_reversal", name="Short-term basis reversal (Rossi-Zhang-Zhu): weekly F1-F2 spread reversal", family="short-term reversal (curve)",
    sources=[U['rzz_cxo'], U['rzz_rep']], source_types=["working paper 2025 (summary)", "independent replication (blog)"],
    exact_rule=("Each Friday close: weekly spread return S_i = r_F1(week) - r_F2(week) from .v.0/.v.1 closes (same instrument ids within the week). Long the F_ front index of the 4 futures with the most negative S, "
                "short the 4 with the most positive S, inverse-vol weights, hold one week, next_close, book to 10%. Variants: V1 15 commodities; V2 commodities + 4 equity index futures (as in the replication); V3 time-series: x_i = -sign(S_i) per commodity in risk units."),
    instruments=COMM15 + " (+F_ES F_NQ F_RTY F_YM in V2)", data_needed="databento_raw glbx_ohlcv1d_v01 (.v.0/.v.1 close, instrument_id), futures_daily",
    external_evidence=("Rossi-Zhang-Zhu 2025: 22 commodities 1980-2022, spread reversal predictable, unexplained by carry or momentum, strongest in high volatility; summaries quote 17.6%/yr and Sharpe 1.42. "
                       "Independent replication (QuantReturns, 2007-2025, commodities + equity index futures, 4/4 weekly): 9.68%/yr, Sharpe 0.92, max DD -17%, beta about 0, gross."),
    evidence_score=2, implementable=True,
    adaptation_note="Paper may trade the spread or nearby contract; we trade the front total-return index only (engine has no second-contract positions).",
    reuse_existing_series="")

add(id="trend_momentum_trends_everywhere_etf", name="Trends Everywhere: 1/3/12 trend on ETF asset classes missing from our futures", family="time-series trend (new asset classes)",
    sources=[U['babu_te']], source_types=["journal (JOIM 2020)"],
    exact_rule=("Month-end over EEM, VGK, EWJ, VNQ, HYG, LQD, EMB, TIP and the 9 sector ETFs: s_i = mean(sign(R_21), sign(R_63), sign(R_252)) of excess returns; w_i = s_i*0.40/sigma_i/N; shorts pay 30 bp/yr; book to 10%, gross<=2, next_open. "
                "Variants: V1 ETFs only; V2 equal-risk combination of V1 and the 30-futures 1/3/12 book; V3 long-or-cash version of V1 (s clipped at 0)."),
    instruments="EEM VGK EWJ VNQ HYG LQD EMB TIP XLB XLE XLF XLI XLK XLP XLU XLV XLY", data_needed="etf_daily, futures_daily (V2), rf_daily",
    external_evidence=("Babu et al. 2020: 156 instruments 1985-2017 incl. credit, EM, equity sectors/factors, combined trend Sharpe 1.60 gross; trend works out of sample across new asset sets (1.34 and 0.95 gross) but no net or post-publication record."),
    evidence_score=3, implementable=True,
    adaptation_note="Credit via HYG/LQD and EM via EEM/EMB instead of CDS indices and EM FX/swaps. F1's 12m TSMOM on 15 ETFs overlaps partially.",
    reuse_existing_series="")

add(id="trend_momentum_industry_channel_trend", name="Industry trend following with Keltner/Donchian bands (Zarattini-Antonacci)", family="breakout (long-only sectors)",
    sources=[U['za'], U['za_rep']], source_types=["practitioner paper (2025 Dow Award)", "independent replication (arXiv)"],
    exact_rule=("Daily per sector ETF (adjusted close): UpperBand = min(Donchian max close 20, EMA20 + 2*1.4*mean|daily change| over 20); enter long when close > UpperBand. "
                "LowerBand = max(Donchian min close 40, EMA40 - 2*1.4*mean|daily change| over 40); trailing stop = max(previous stop, LowerBand); exit when close < stop. "
                "Weight per held sector = (1.5%/N)/sigma_14d (daily vol), gross <= 200%, idle capital in T-bills, daily rebalance, next_open. "
                "Variants: V1 9 SPDR sectors; V2 9 sectors + SPY, QQQ, IWM, MDY; V3 V1 with the book scaled to 10% ex-ante."),
    instruments=SECT9 + " (+SPY QQQ IWM MDY in V2)", data_needed="etf_daily, rf_daily",
    external_evidence=("Zarattini & Antonacci (48 US industries 1926-2024): 18.2%/yr, vol 12.6%, Sharpe 1.39 vs market 0.63 (in-sample design). Independent replication (arXiv 2412.14361, data 2000-2024): walk-forward out-of-sample cumulative performance fell short of the market; in-sample refinements failed to generalise."),
    evidence_score=2, implementable=True,
    adaptation_note="9 SPDR sectors instead of 48 French industries; long-only so returns are equity-beta heavy.",
    reuse_existing_series="")

add(id="trend_momentum_es_trend_timing", name="Equity index trend timing on ES (10-month SMA, turning-points MED, 12m TSMOM)", family="time-series trend (equity timing)",
    sources=[U['faber07'], U['mtp'], U['aqr_tsmom']], source_types=["practitioner paper", "journal", "dataset"],
    exact_rule=("ES sized at 10% ex-ante vol (EWMA com 60) when the signal is on, T-bill otherwise; month-end decisions, next_close. V1 long when the month-end ES index > its 10-month SMA of month-end closes, else flat; "
                "V2 MED turning points: +1 if signs of R_12m and R_1m both positive, -1 if both negative, 0 if they disagree; V3 12-month TSMOM long/short sign(R_252)."),
    instruments="F_ES", data_needed="futures_daily, rf_daily",
    external_evidence=("Faber 2007/2013: 10-month SMA timing on the S&P 500 since 1901 kept equity-like returns with lower vol and drawdown. Garg et al.: MED speed Sharpe 0.51 on US equity vs about 0.38 slow. "
                       "AQR TSMOM^EQ: 0.83 for 1985-2009, 0.19 post-publication, -0.20 for 2016-2024. Ours: ES at 10% vol unfiltered 0.77 IS / 0.50 later - the bar to beat."),
    evidence_score=3, implementable=True,
    adaptation_note="Single-instrument timing; compare against the tested ES 10% vol benchmark, not cash.",
    reuse_existing_series="")

notes = (
 "Search budget: about 20 web searches plus direct fetches before the session-wide WebSearch cap was reached; remaining facts came from already-downloaded papers (scratchpad) and direct URL fetches. "
 "Post-publication numbers from AQR datasets and French industries are our own gross calculations (scripts aqr_subperiods.py, faber_rs_postpub.py in this folder). "
 "Pattern in the evidence: time-series trend (MOP, HOP, Carver live) has the only long live/post-publication record (about 0.25-0.4 net industry, 0.76 rf=0 for Carver's diversified multi-rule account); "
 "cross-sectional momentum in futures (all classes, commodities, FX) has been about zero or negative in AQR's own data since publication; bond TSMOM held up best by asset class; "
 "short-term reversal in futures is contested (BvD lagged version insignificant; most commodity studies find no reversal) except the new curve-based basis reversal (2025, one blog replication). "
 "Already-tested overlaps: trend_momentum_mop_tsmom12 (TSMOM_F on 20 futures), trend_momentum_hop_1_3_12 V1 (= S1 rule), trend_momentum_carver_ewmac_breakout V1 (likely = our long-short EWMAC). "
 "Allocation/rotation strategies (GEM dual momentum, Keller VAA/DAA/BAA, Faber GTAA) are left to the allocation_rotation label; intraday momentum (Gao-Han-Li-Zhou, ES hourly) and macro/economic trend (Brooks) are outside this label. "
 "Data caveat: futures history starts 2010-06-07, so 12-month signals start about 2011-06; dynamic turning-point estimates need pooling."
)

json.dump({'candidates': C, 'notes': notes, 'conventions': CONV}, open(os.path.join(OUT, 'candidates.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)

# SPEC.md: pre-registration of each candidate's rule and variants, written before any backtest on our framework.
lines = ["# trend_momentum hunt: pre-registered rules (written 2026-10-03, before any backtest on the gqh engine)", "",
         CONV, "", "In-sample window: futures from the first eligible decision (about 2011-06) to 2024-10-02; ETFs from the first eligible decision to 2024-10-02. "
         "2024-10-03..2026-10-02 is descriptive only. At most 3 variants per candidate, all reported; any choice among variants uses in-sample data only.", ""]
for c in C:
    lines += [f"## {c['id']}: {c['name']}", f"- Family: {c['family']}", f"- Instruments: {c['instruments']}", f"- Data: {c['data_needed']}",
              f"- Rule and variants: {c['exact_rule']}", f"- Source evidence (to report next to ours): {c['external_evidence']}",
              f"- Adaptation: {c['adaptation_note']}", f"- Sources: " + "; ".join(c['sources']), ""]
open(os.path.join(OUT, 'SPEC.md'), 'w', encoding='utf-8').write("\n".join(lines))

urls = sorted(set(U.values()))
extra = ["https://arxiv.org/pdf/1404.3274", "https://www3.nd.edu/~zda/Indexing.pdf", "https://arxiv.org/pdf/2412.14361",
         "https://www.york.ac.uk/media/economics/documents/discussionpapers/2012/1228.pdf",
         "https://spiral.imperial.ac.uk/server/api/core/bitstreams/93f06c22-150a-4240-8115-912988dd2c67/content",
         "https://benny.aeaweb.org/conference/2021/preliminary/powerpoint/ihbRDkeH",
         "https://qoppac.blogspot.com/2015/04/futures-trading-performance-year-one.html",
         "https://qoppac.blogspot.com/2017/04/investment-and-trading-performance-year.html",
         "https://qoppac.blogspot.com/2019/04/trading-and-investing-performance-year.html",
         "https://ideas.repec.org/a/eee/finana/v31y2014icp1-12.html",
         "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_CSV.zip",
         "https://www.cxoadvisory.com/technical-trading/trend-following-over-the-very-long-run/",
         "https://quantpedia.com/strategies/sector-momentum-rotational-system"]
open(os.path.join(OUT, 'urls.txt'), 'w', encoding='utf-8').write("\n".join(sorted(set(urls + extra))) + "\n")
print(len(C), 'candidates;', sum(c['implementable'] for c in C), 'implementable')
