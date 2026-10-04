"""Build the github-label candidate list (research notes only, nothing computed)."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent

COMMON_SCALE = ("Where the rule has no natural sizing, scale the book to 10% annualised ex-ante vol "
                "with trailing data only (EWMA/sample covariance of daily excess returns).")

C = []

def add(**k):
    k.setdefault("reuse_existing_series", "")
    k.setdefault("implementable", True)
    C.append(k)

# 1 ------------------------------------------------------------------------------------------
add(
    id="github_sepp_european_ls250_20",
    name="Sepp-Lucic European trend system LS(250,20) (with TSMOM and American variants)",
    family="trend_following",
    source_types=["github", "paper"],
    sources=[
        "https://github.com/ArturSepp/TrendFollowingSystems (README; src/trendfollowing/systems/european.py, tsmom.py, american.py; examples/backtest_european_system.py)",
        "https://github.com/ArturSepp/QuantInvestStrats src/qis/models/linear/ewm.py (compute_ewm_long_short: unit-variance band-pass)",
        "https://ssrn.com/abstract=3167787 (Sepp & Lucic, The Science and Practice of Trend-Following Systems; arXiv 2607.19497)",
    ],
    exact_rule=(
        "Daily, each of the 30 futures. r_t = daily excess return of the total-return index; sigma_t = EWMA std of r "
        "(span 33, lambda=1-2/34) using data through t; z_t = r_t / sigma_{t-1}. Band-pass signal: "
        "s_t = wL*kL*EWMA250(z)_t - wS*kS*EWMA20(z)_t, EWMA recursion x_t = lam*x_{t-1} + (1-lam)*z_t, lam = 1-2/(span+1), "
        "k = sqrt((1+lam)/(1-lam)), wL = 1/(sqrt(1-lamL^2)*C), wS = 1/(sqrt(1-lamS^2)*C), "
        "C = sqrt(1/(1-lamL^2) + 1/(1-lamS^2) - 2/(1-lamL*lamS)) (unit variance for white-noise z); clip s to [-3, 3]. "
        "Instrument weight w = (0.30 / (sqrt(260)*sigma_t)) * s_t. Portfolio rescaled daily to the target vol "
        "(source 15%, ours 10%) with a 63-span EWMA covariance of instrument returns; 250-day warm-up. "
        "Decide at close d, engine exec=next_close, daily rebalance. Pre-declared variants: V1 = LS(250,20) European (headline); "
        "V2 = Sepp TSMOM: signs of z averaged inside 22-day blocks (times sqrt(22)), then the mean of the last 12 block values times sqrt(12), "
        "weight = vol_target/vol * signal, rebalanced at block ends; V3 = Sepp American: binary long (short) when the 20-day price EWMA "
        "exceeds (is below) the 250-day price EWMA by more than 5 ATR, 5-ATR trailing stop, size fixed at entry inversely to vol "
        "(risk multiplier 1%, |w| <= 10), then the same portfolio vol targeting."
    ),
    instruments="30 CME futures in futures_daily (ES NQ RTY YM ZT ZF ZN ZB UB CL HO RB NG GC SI PL HG ZC ZS ZW ZL ZM LE HE 6E 6J 6B 6A 6C 6S)",
    data_needed="futures_daily total-return indices and rf (have); for V3 daily high/low from load_ohlc for ATR",
    external_evidence=(
        "Repo example: LS(250,20) on 84 liquid futures, net of volume-based costs, gross of fees, realised vol 15.2%: Sharpe 1.10 over 1960-2026. "
        "At matched lookbacks the European, American and TSMOM systems give Sharpe 0.47, 0.50 and 0.55 (monthly, net of costs and 2/20 fees) "
        "against 0.47 for the live SG Trend Index, average correlation about 80% with it. The closed-form Sharpe predicted from each contract's "
        "autocorrelation and drift matches realised per-contract Sharpe (pooled correlation 0.99; ES1 predicted 0.227 vs realised 0.206). "
        "Red flags: 1.10 is full-sample and includes the 1960s-1990s trend golden era; no post-publication split; our own trend tests on these 30 "
        "futures were weak in 2010-2024 (S1 -0.13 IS, TSMOM-12 0.28, long-short EWMAC about 0)."
    ),
    evidence_score=4,
    adaptation_note=(
        "Source universe has 84 global contracts incl. non-US equity indices, bunds/JGBs and STIR; ours is 30 US-listed. Use our TR-index returns "
        "instead of their roll-adjusted series and our cost map instead of volume-based costs. The long-minus-short band-pass is trend net of the "
        "last month's move, a different filter from the EWMAC/S1 rules we already tested."
    ),
)

# 2 ------------------------------------------------------------------------------------------
add(
    id="github_beyondpassive_4h_sector_trend",
    name="Four-horizon z-score trend with CFTC-sector then portfolio vol targeting (Beyond Passive program)",
    family="trend_following",
    source_types=["github", "practitioner_article"],
    sources=[
        "https://github.com/phuazz/trend-replication-lab (SPEC.md, README)",
        "Beyond Passive Investing, 'Trend following (1/4): Replicating your own program', beyondpassive.substack.com, 30 May 2026",
    ],
    exact_rule=(
        "Per contract, daily: z_L = (cumulative excess return over L sessions) / (sigma63 * sqrt(L)) for L = 21, 63, 126, 252, "
        "sigma63 = trailing 63-session std of daily returns (source: of daily price changes on point-adjusted series). "
        "Forecast f = clip(mean(z_21, z_63, z_126, z_252), -2, +2) (cap assumed +-2 in the replication SPEC). Contract position = f / sigma_daily. "
        "Sector baskets (equity ES NQ RTY YM; rates ZT ZF ZN ZB UB; FX 6E 6J 6B 6A 6C 6S; energy CL HO RB NG; metals GC SI PL HG; "
        "grains ZC ZS ZW ZL ZM; livestock LE HE) each rescaled to 4% annualised vol using the basket's own trailing 63-session realised vol; "
        "sum of sectors rescaled to 10% annualised vol using the portfolio's trailing 63-session realised vol. Weekly rebalance: signal at the "
        "last session of the week, one-day execution delay (fill at the close of the next session after the decision day, i.e. next_close plus "
        "one extra session). Variants: V1 as stated; V2 daily rebalance with the same one-day delay; V3 single-level portfolio vol target "
        "(no sector step)."
    ),
    instruments="30 CME futures grouped into 7 sectors",
    data_needed="futures_daily TR indices (have)",
    external_evidence=(
        "Article: 62 markets in 10 CFTC sectors, 1995 to Apr 2026: Sharpe 1.03 gross, about 1.00 net (cost drag 30-50 bp/yr, slippage 2-3 bp one-way), "
        "CAGR 11.3%, max drawdown about 23%, turnover 6-10x a year; consistent with SG Trend over the same window. "
        "Red flags: the GitHub replication is a scaffold verified only on synthetic data (no independent real-data number); the 62-name universe "
        "reflects today's liquidity and includes crypto from 2020 'because it had trend' (hindsight); clip value assumed; pre-1995 dropped."
    ),
    evidence_score=3,
    adaptation_note=(
        "No crypto, softs, STIR or non-US contracts in our set; 7 sectors instead of 10. Using percentage returns on our TR index is the consistent "
        "analogue of the source's price-change vol on point-adjusted prices. Signal overlaps Hurst-Ooi-Pedersen 1/3/12 (trend_momentum sibling); "
        "the distinct parts are averaging four clipped horizons and the sector-first vol normalisation."
    ),
)

# 3 ------------------------------------------------------------------------------------------
add(
    id="github_kestner_cta_replication",
    name="Kestner (2020) CTA positioning replication ensemble (SG Trend clone)",
    family="trend_following",
    source_types=["github", "paper"],
    sources=[
        "https://github.com/hobinkwak/CTA-Position-Monitoring (ctarep/config.py, README)",
        "Kestner (2020) 'Replicating CTA Positioning: An Improved Method', https://ssrn.com/abstract=3674828",
    ],
    exact_rule=(
        "Weekly at the Friday close. For each market and lookback L in {16, 32, 52} weeks: normalised momentum m_L = (return over L weeks) / "
        "(sigma_week * sqrt(L)), sigma_week = std of daily returns over the last 90 days (repo default 60) times sqrt(5). "
        "Position_L = clip(m_L, -1, +1) (cap 1.0, i.e. a t-stat of 1 gives a full position). Market weight_L = position_L / sigma_annual "
        "(equal risk per market). Ensemble = average of the three lookbacks. Portfolio rescaled to 10% ex-ante vol with trailing covariance "
        "(repo rescales to the SG Trend benchmark vol). Fill at next_close after the Friday decision. "
        "Variants: V1 ensemble 16/32/52, cap 1, 90-day vol; V2 best single model 32 weeks / cap 1 / 60-day vol; "
        "V3 V1 with sector risk parity (each market weight divided by the number of active markets in its sector)."
    ),
    instruments="30 CME futures (paper's 16 markets: ES Z VG NK TY G RX JB EC BP JY AD CL GC HG S; our overlap ES ZN 6E 6B 6J 6A CL GC HG ZS)",
    data_needed="futures_daily TR indices (have); optional SG Trend index level for tracking diagnostics (not required)",
    external_evidence=(
        "Kestner (2020): the 16/32/52-week ensemble with cap 1.0 and 90-day vol explains more than 75% of weekly SG Trend Index returns (R-squared). "
        "SG Trend Index is a live investable-manager record since 2000 (Sharpe roughly 0.4-0.5 net of fees). "
        "Red flags: replicating positioning implies inheriting SG Trend's flat 2011-2019; the cap/lookback grid was fitted to the index."
    ),
    evidence_score=3,
    adaptation_note="Half of the paper's markets are non-US; run on all 30 of ours (V1/V3) and report the 10-market overlap subset as a diagnostic only.",
)

# 4 ------------------------------------------------------------------------------------------
add(
    id="github_carver_assettrend",
    name="Carver asset-class trend (EWMAC on the asset-class normalised price)",
    family="trend_following",
    source_types=["github", "blog"],
    sources=[
        "https://github.com/pst-group/pysystemtrade systems/provided/rob_system/config.yaml (assettrend2..64), systems/rawdata.py (normalised_price_for_asset_class), systems/provided/rules/ewmac.py",
        "https://qoppac.blogspot.com/2021/12/my-trading-system.html",
    ],
    exact_rule=(
        "For each asset class (equity, rates, FX, energy, metals, ags incl. livestock) build an index = cumulative sum of the cross-sectional "
        "mean of daily vol-normalised returns r_i,t / sigma_i,t-1 (sigma = EWMA std, span 35) of the instruments in that class. "
        "Every instrument in the class gets forecast = EWMAC(Lfast, 4*Lfast) of that class index divided by the index's own daily vol "
        "(ewmac_calc_vol), times a forecast scalar so mean |f| = 10 (scalar estimated on trailing data), capped at +-20. "
        "Position = f/10 * (instrument vol target / instrument vol); equal risk per instrument; portfolio scaled to 10% vol; daily, next_close, "
        "10% position buffer. Variants: V1 average of Lfast = 16, 32, 64; V2 Lfast = 64 only; V3 Lfast = 32 only."
    ),
    instruments="30 CME futures by asset class",
    data_needed="futures_daily TR indices (have)",
    external_evidence=(
        "Carver Dec 2021 crude pooled Sharpe (instrument-equal-weighted, pre-cost, up to 146 instruments, multi-decade back-test): assettrend "
        "variants from -0.94 (fastest) to 0.70 (slow ones 0.62-0.70); EWMAC up to 0.78; whole system Sharpe 1.31 daily / 1.14 monthly, costs "
        "1.06%/yr. Red flags: pooled pre-cost per-rule numbers; Carver's system weights chosen in-sample; our long-short EWMAC on 30 futures was "
        "about 0 in-sample."
    ),
    evidence_score=3,
    adaptation_note="Asset classes have 2-6 members here, so the class index is noisier than Carver's; livestock pooled with grains.",
)

# 5 ------------------------------------------------------------------------------------------
add(
    id="github_carver_normmom",
    name="Carver normalised momentum (EWMAC on cumulative vol-normalised returns)",
    family="trend_following",
    source_types=["github", "blog"],
    sources=[
        "https://github.com/pst-group/pysystemtrade systems/provided/rob_system/config.yaml (normmom2..64), systems/rawdata.py (get_cumulative_daily_vol_normalised_returns)",
        "https://qoppac.blogspot.com/2021/12/my-trading-system.html",
    ],
    exact_rule=(
        "For each instrument: normalised price N_t = cumulative sum of r_t / sigma_{t-1} (sigma = EWMA std of daily returns, span 35). "
        "Forecast = EWMAC(Lfast, 4*Lfast) on N divided by N's own daily vol, scaled to mean |f| = 10 with a trailing scalar, capped +-20. "
        "Position = f/10 * vol target / instrument vol; equal risk per instrument; portfolio 10% vol; daily, next_close, 10% buffer. "
        "Variants: V1 Lfast = 16, 32, 64 averaged; V2 Lfast = 64; V3 Lfast = 8, 16, 32 averaged."
    ),
    instruments="30 CME futures",
    data_needed="futures_daily TR indices (have)",
    external_evidence=(
        "Carver Dec 2021 crude pooled pre-cost Sharpe: normmom variants from -1.23 (fastest) to 0.82, the highest of his trend rules. "
        "Red flags: same as assettrend; normmom is a close cousin of EWMAC, which was about 0 on our 30 futures in-sample, so the prior is low."
    ),
    evidence_score=2,
    adaptation_note="Differs from price EWMAC only through vol normalisation of each day's move; worth testing mainly as a check of whether vol-normalised trend survives where price trend did not.",
)

# 6 ------------------------------------------------------------------------------------------
add(
    id="github_carver_skewabs",
    name="Carver skew rule (long negative-skew instruments, time-series and asset-relative)",
    family="risk_premia_skew",
    source_types=["github", "blog"],
    sources=[
        "https://github.com/pst-group/pysystemtrade systems/provided/rob_system/rawdata.py (skew, neg_skew, get_demeanded_factor_value, historic_average_factor_value_all_assets), systems/provided/rules/factors.py (factor_trading_rule)",
        "https://qoppac.blogspot.com/2021/12/my-trading-system.html",
    ],
    exact_rule=(
        "For each instrument daily: neg_skew_t = -(sample skewness of daily percentage returns over the last 365 calendar days). "
        "skewabs: demean by the 15-year EWMA (span 260*15 sessions) of the cross-sectional average neg_skew over all instruments. "
        "Normalise the demeaned factor by its own robust vol (EWMA std span 35 with a floor at the 5th percentile of its history), smooth with an "
        "EWMA of span 90, scale to mean |f| = 10 (trailing scalar), cap +-20. Position = f/10 * vol target / instrument vol; equal risk per "
        "instrument; portfolio 10% vol; daily, next_close, 10% buffer. Variants: V1 skewabs365; V2 skewabs180 (180-day skew, smoothing span 45, "
        "assumed); V3 skewrv365 (demean by the current average neg_skew of the instrument's asset class instead)."
    ),
    instruments="30 CME futures",
    data_needed="futures_daily TR indices (have)",
    external_evidence=(
        "Carver Dec 2021 crude pooled pre-cost Sharpe: skewabs 0.42-0.52, skewrv 0.22-0.33, low correlation with his trend rules. "
        "Supporting literature: commodity skewness premium (Fernandez-Perez et al. 2018 JBF) and the skew-Sharpe link across risk premia "
        "(Lemperiere et al. 2017). Red flags: rule details are only in code/book; pooled crude statistics; tilting into negative skew adds crash exposure."
    ),
    evidence_score=3,
    adaptation_note="Skew is estimated on our TR-index returns; roll days are clean in the TR index, so no roll-jump contamination of skew.",
)

# 7 ------------------------------------------------------------------------------------------
add(
    id="github_qc_skewness_xs_commodities",
    name="Cross-sectional skewness effect in commodity futures (QuantConnect / Quantpedia)",
    family="cross_sectional_commodities",
    source_types=["github", "quantconnect", "paper"],
    sources=[
        "https://github.com/paperswithbacktest/awesome-systematic-trading static/strategies/skewness-effect-in-commodities.py (README table, 2024 version)",
        "https://quantpedia.com/strategies/skewness-effect-in-commodities/",
        "Fernandez-Perez, Frijns, Fuertes, Miffre (2018), The skewness of commodity futures returns, Journal of Banking & Finance 86; SSRN 2671165",
    ],
    exact_rule=(
        "Monthly at the last session: for each of our 15 commodity futures compute the skewness of daily excess returns over the trailing 252 sessions; "
        "rank; long the 3 lowest-skew (bottom quintile), short the 3 highest-skew (top quintile), equal weight within legs; hold one month; "
        "next_close; book scaled to 10% ex-ante vol. Variants: V1 quintiles equal weight (source); V2 terciles (5 v 5) inverse-vol weighted; "
        "V3 rank weights across all 15."
    ),
    instruments="CL HO RB NG GC SI PL HG ZC ZS ZW ZL ZM LE HE",
    data_needed="futures_daily TR indices (have)",
    external_evidence=(
        "QuantConnect implementation on 27 continuous commodity futures (start 2000, gross): Sharpe 0.482, vol 17.7%. The paper reports a significant "
        "low-minus-high skewness premium, robust to carry, momentum and hedging-pressure controls (1987-2014). "
        "Red flags: only 3 names per leg with our 15 commodities; QC table period and costs unstated."
    ),
    evidence_score=3,
    adaptation_note="Universe 15 vs 27; no softs/oats/feeder cattle. Cross-sectional cousin of github_carver_skewabs.",
)

# 8 ------------------------------------------------------------------------------------------
add(
    id="github_qc_return_asymmetry_commodities",
    name="Return-asymmetry (IE) effect in commodity futures (QuantConnect / Quantpedia)",
    family="cross_sectional_commodities",
    source_types=["github", "quantconnect", "paper"],
    sources=[
        "https://github.com/paperswithbacktest/awesome-systematic-trading static/strategies/return-asymmetry-effect-in-commodity-futures.py",
        "https://quantpedia.com/strategies/return-asymmetry-effect-in-commodity-futures/ (source paper SSRN 3918896)",
    ],
    exact_rule=(
        "Monthly at the last session: for each commodity, over the last 260 daily returns, IE = count(r > mean + 2*sd) - count(r < mean - 2*sd) "
        "(mean and sd from the same 260 days). Long the 5 lowest-IE, short the 5 highest-IE of our 15 commodities (source: 7 of 22), equal weight, "
        "hold one month, next_close, book scaled to 10% vol. Variants: V1 5/5; V2 3/3; V3 rank-weighted all 15."
    ),
    instruments="CL HO RB NG GC SI PL HG ZC ZS ZW ZL ZM LE HE",
    data_needed="futures_daily TR indices (have)",
    external_evidence="QuantConnect implementation on 22 commodities (start 2000, gross): Sharpe 0.239, vol 13.4%. Red flags: weak headline, count statistic is coarse with 260 obs.",
    evidence_score=2,
    adaptation_note="Universe 15 vs 22; tail counts are small integers, so ties are frequent (break ties by 12-month skewness).",
)

# 9 ------------------------------------------------------------------------------------------
add(
    id="github_qc_paired_switching",
    name="Paired switching: hold last quarter's winner of stocks vs Treasuries",
    family="tactical_allocation",
    source_types=["github", "quantconnect", "paper"],
    sources=[
        "https://github.com/paperswithbacktest/awesome-systematic-trading static/strategies/paired-switching.py",
        "https://github.com/QuantConnect/Tutorials '04 Strategy Library/33 Paired Switching'",
        "Maewal & Bock (2011), Paired-Switching for Tactical Portfolio Allocation, SSRN 1917044",
    ],
    exact_rule=(
        "At each quarter-end (last session of Mar, Jun, Sep, Dec) compare total returns of the equity and bond asset over the prior 63 sessions; "
        "hold 100% of the winner for the next quarter; decision at close, fill next_close. Variants: V1 SPY vs TLT (closest to the paper's VFINX/VUSTX); "
        "V2 SPY vs AGG (QuantConnect code); V3 ES vs ZN futures, each scaled to equal ex-ante vol (10%)."
    ),
    instruments="SPY, TLT, AGG (etf_daily); ES, ZN (futures)",
    data_needed="etf_daily adjusted closes, futures_daily (have)",
    external_evidence=(
        "QuantConnect/Quantpedia SPY/AGG (code start 2004, gross): Sharpe 0.691, vol 9.5%. Paper: VFINX/VUSTX switching beat both funds and a static mix "
        "over its sample. Red flags: one binary decision per quarter (about 56 in our IS); relies on negative stock-bond correlation (2022 hurt both)."
    ),
    evidence_score=2,
    adaptation_note="Natural sizing is 100% notional; also report the 10%-vol-scaled series for comparability.",
)

# 10 -----------------------------------------------------------------------------------------
add(
    id="github_trendlab_etf_12_1_longflat",
    name="TrendLab pre-registered long/flat 12-1 absolute momentum on 10 asset-class ETFs",
    family="tactical_allocation",
    source_types=["github"],
    sources=["https://github.com/akadigari/trendlab (README, config.py, reports/report.md)"],
    exact_rule=(
        "Month-end: for SPY EFA EEM IEF TLT LQD HYG GLD DBC VNQ compute the total return from t-252 to t-21 sessions (12-1); hold a sleeve if it beats "
        "the T-bill return over the same window, else T-bills. Inverse-vol risk budgets (trailing 60-session vol) over held sleeves, capped at 25% each, "
        "no leverage, no shorts, unallocated weight in T-bills. Signal at the month-end close, fill next_close, 5 bp one-way (our ETF cost map). "
        "Variants: V1 pre-registered; V2 9-month lookback (12-1 replaced by 9-1); V3 V1 scaled to 10% ex-ante vol with leverage cap 2."
    ),
    instruments="SPY EFA EEM IEF TLT LQD HYG GLD DBC VNQ (all in etf_daily)",
    data_needed="etf_daily adjusted closes, rf (have)",
    external_evidence=(
        "Net of 5 bp: full sample 2003-2026 Sharpe 0.70 (excess +3.7%/yr, vol 5.4%, maxDD -16.2%); hold-out from 2018-06 Sharpe 0.35; "
        "post-publication 2013+ Sharpe 0.39; fails its own timing-null gate (circular-shift p = 0.44 post-2013) and only modestly beats an "
        "exposure-matched static mix (0.63). Honest, pre-registered, everything after 2013 out-of-sample by construction."
    ),
    evidence_score=3,
    adaptation_note="Close to S3 Faber GTAA (0.51 IS / 0.70 later) and to sibling trend_momentum_trends_everywhere_etf; distinct in the 12-1 vs T-bill hurdle, 10-ETF set and 25% inverse-vol caps.",
)

# 11 -----------------------------------------------------------------------------------------
add(
    id="github_ibs_spy_meanrev",
    name="Internal Bar Strength (IBS) mean reversion on SPY",
    family="short_term_mean_reversion",
    source_types=["github", "practitioner_paper"],
    sources=[
        "https://github.com/toniker10/SPY-IBS-Mean-Reversion-Strategy",
        "Pagonidis (2014), The IBS Effect: Mean Reversion in Equity ETFs (NAAIM Wagner Award paper)",
        "Counterpoint: https://github.com/akrabolsa/IBS-trading-strategy ('not as promising as mentioned')",
    ],
    exact_rule=(
        "IBS_t = (Close_t - Low_t) / (High_t - Low_t) from adjusted daily OHLC. If flat and IBS_t < 0.20, buy at the next open; if long and IBS_t > 0.80, "
        "sell at the next open; otherwise keep the position. Long/flat, 1x notional (also report scaled to 10% vol). Engine exec=next_open. "
        "Variants: V1 SPY (source); V2 same rule run separately on SPY, QQQ, IWM, DIA and averaged equal weight; V3 SPY with next_close fills."
    ),
    instruments="SPY (V2 adds QQQ IWM DIA); costs at ETF cost map, stress also at ES 1 bp per side",
    data_needed="etf_daily adjusted OHLC (have)",
    external_evidence=(
        "Repo, SPY 1993-01-29 to 2026-09-11, zero commission, Sharpe without risk-free subtraction: CAGR 12.67% vs 10.83% buy-and-hold, Sharpe 0.97 vs 0.65, "
        "maxDD -26% vs -55%, 989 trades, win rate 69%, profit factor 1.93; no out-of-sample split. Pagonidis (2014) documents the IBS reversal across "
        "equity ETFs. Red flags: costs ignored (about 30 round trips a year); open prices from Yahoo can be stale; single parameter set; one negative replication."
    ),
    evidence_score=3,
    adaptation_note="Daily OHLC from etf_daily (RTH bars). ES daily bars span the 23-hour session, so IBS on ES is not the same signal; keep SPY for the signal and use ES only as a cost stress.",
)

# 12 -----------------------------------------------------------------------------------------
add(
    id="github_lean_ibs_xs_country_etf",
    name="Cross-sectional IBS reversal across global equity ETFs (Lean benchmark alpha)",
    family="short_term_mean_reversion",
    source_types=["github", "quantconnect", "book"],
    sources=[
        "https://github.com/QuantConnect/Lean Algorithm.Python/Alphas/GlobalEquityMeanReversionIBSAlpha.py",
        "Kakushadze & Serur (2018), 151 Trading Strategies, ch. 4 (ETFs)",
    ],
    exact_rule=(
        "Daily: IBS for each ETF from the day's OHLC; short the 2 highest-IBS ETFs, long the 2 lowest-IBS ETFs, equal weight, hold one day. "
        "Source trades at the signal close; we decide at close d and fill next_close (one-day lag, pre-declared). Book scaled to 10% vol. "
        "Variants: V1 Lean universe of 32 country/regional ETFs (ECH EEM EFA EPHE EPP EWA EWC EWG EWH EWI EWJ EWL EWM EWO EWP EWQ EWS EWT EWU EWY EWZ EZA FXI GXG IDX ILF QQQ RSX SPY THD, via yfinance); "
        "V2 our own equity ETFs (SPY EFA EEM VGK EWJ IWM MDY QQQ VTI DIA); V3 the 9 sector SPDRs."
    ),
    instruments="country ETFs (yfinance), equity and sector ETFs in etf_daily",
    data_needed="etf_daily OHLC (have); yfinance OHLC for the country ETFs (free)",
    external_evidence="Lean ships it as a benchmark alpha with zero fees and no published statistics; Kakushadze-Serur list it without a backtest.",
    evidence_score=1,
    adaptation_note=(
        "Red flags: country ETFs trade while their home markets are closed (stale-price effect); spreads 5-20 bp per side on small country ETFs with ~200% daily "
        "turnover make it cost-dominated; RSX was halted in 2022 (survivorship). Include mainly as a cheap check of the IBS family beyond SPY."
    ),
)

# 13 -----------------------------------------------------------------------------------------
add(
    id="github_connors_rsi2",
    name="Connors RSI(2) pullback in an uptrend (with Double-7s variant)",
    family="short_term_mean_reversion",
    source_types=["github", "book"],
    sources=[
        "https://github.com/Dimas-100/webull-trading-system (live RSI2 swing system with backtest scripts)",
        "https://github.com/0xWick/Pine-Strategy-RSI2 ; https://github.com/vishalagar/india-trading-bot",
        "Connors & Alvarez (2008/2009), Short Term Trading Strategies That Work",
    ],
    exact_rule=(
        "Daily on SPY (or ES TR index): RSI(2) with Wilder smoothing on closes. Enter long when close > 200-session SMA and RSI(2) < 5; exit when close > "
        "5-session SMA. Source fills at the signal close; we decide at close d and fill next_close. Long/flat, 1x (also 10%-vol scaled). "
        "Variants: V1 RSI(2) < 5, exit close > SMA5 (book); V2 RSI(2) < 10, same exit; V3 Double-7s: enter when close is the lowest of the last 7 closes and "
        "close > SMA200, exit when close is the highest of the last 7 closes."
    ),
    instruments="SPY (etf_daily) or ES",
    data_needed="etf_daily adjusted closes / futures_daily (have)",
    external_evidence=(
        "Book back-tests on the S&P 500 (1995-2007 era) report high win rates with holding periods of a few days; the GitHub repos implement the rule "
        "but publish no out-of-sample statistics (one runs it live, backtest archive private). Red flags: in-sample book statistics, signal-close fills."
    ),
    evidence_score=2,
    adaptation_note="Engine next_close adds a one-day delay versus the book's same-close fills; report this lag explicitly.",
)

# 14 -----------------------------------------------------------------------------------------
add(
    id="github_vix_percentile_contrarian",
    name="VIX 2-year percentile contrarian equity timing (QuantConnect 'VIX predicts stock index returns')",
    family="volatility_timing",
    source_types=["github", "quantconnect"],
    sources=[
        "https://github.com/QuantConnect/Tutorials '04 Strategy Library/58 VIX Predicts Stock Index Returns'",
        "https://quantpedia.com/strategies/vix-predicts-stock-index-returns/",
    ],
    exact_rule=(
        "Daily: window = last 504 VIX closes including today. If VIX_t > 90th percentile of the window (top two of the twenty 5% boxes, includes new 2-year highs) "
        "go long ES 1x (source: OEF); if VIX_t < 10th percentile go short ES 1x. Decide at close d, fill next_close. Variants: V1 hold until the opposite "
        "signal; V2 flat when VIX is between the 10th and 90th percentiles; V3 long-only (long when > 90th percentile, else flat). Also report 10%-vol scaled."
    ),
    instruments="ES (futures_daily); ^VIX (index_daily)",
    data_needed="index_daily ^VIX, futures_daily ES (have)",
    external_evidence=(
        "QuantConnect tutorial (OEF, 2006-2018) presents the rule; no Sharpe in the extracted text. Literature: high implied-vol percentiles are followed by "
        "above-average index returns (e.g. Giot 2005). Red flags: shorting at low VIX loses in calm bull markets; the long leg buys into crash regimes (2008, 2020)."
    ),
    evidence_score=2,
    adaptation_note="Distinct from macro_regime_vix_stretch (Connors) and VIX-managed sizing: a percentile-box state rule.",
)

# 15 -----------------------------------------------------------------------------------------
add(
    id="github_overnight_trend_vix_filter",
    name="Filtered overnight S&P holding (SPY above SMA20 and VIX below SMA20)",
    family="intraday_overnight",
    source_types=["github", "quantconnect"],
    sources=[
        "https://github.com/paperswithbacktest/awesome-systematic-trading static/strategies/market-sentiment-and-an-overnight-anomaly.py (quantpedia 'market sentiment and an overnight anomaly')",
        "https://github.com/QuantConnect/Tutorials '04 Strategy Library/16 Overnight Anomaly'",
        "https://github.com/NafizNoor1/overnight-anomaly (SPY 1993-2026 decomposition, cost sweep)",
    ],
    exact_rule=(
        "At each close d: if SPY close > its 20-session SMA and VIX close < its 20-session SMA (the source's third condition, Brain Market Sentiment > SMA20, "
        "is proprietary and dropped), hold the S&P from close d to the open of d+1, flat intraday. Return = adjusted SPY open_{d+1}/close_d - 1, cost charged "
        "as ES 1 bp per side (futures execution), 2x stress. Variants: V1 filter as stated; V2 unfiltered overnight benchmark; V3 overnight only after a down "
        "day (close_d < close_{d-1})."
    ),
    instruments="SPY adjusted OHLC (signal and returns), ^VIX; execution proxy ES",
    data_needed="etf_daily SPY OHLC, index_daily ^VIX (have); optional databento hourly ES for an ES close(16:00 ET)-to-09:00 ET check",
    external_evidence=(
        "Quantpedia/QuantConnect with the sentiment filter: Sharpe 0.369, vol 3.6%. NafizNoor1, SPY Feb 1993-Jul 2026: overnight 10.0%/yr, Sharpe 0.95 gross; "
        "0.71 at 1 bp round trip, 0.48 at 2 bp, 0 at about 4 bp; 2010-2026 overnight Sharpe 0.82 gross; overnight leg lost in the 2020 crash and in 2022; "
        "overnight return about +8 bp after down days vs -7.4 bp after >2% up days. Red flag: NY Fed Liberty Street (2026-07) 'disappearing overnight drift'."
    ),
    evidence_score=2,
    adaptation_note="V2 duplicates intraday_micro_overnight_hold_es (sibling); the filter (V1) and after-down-day conditioning (V3) cut the daily round-trip cost load.",
)

# 16 -----------------------------------------------------------------------------------------
add(
    id="github_qc_fed_model_timing",
    name="Fed model (yield gap) equity timing by expanding regression",
    family="valuation_timing",
    source_types=["github", "quantconnect", "paper"],
    sources=[
        "https://github.com/paperswithbacktest/awesome-systematic-trading static/strategies/fed-model.py (quantpedia 'Fed model')",
        "Maio (2013), The 'Fed Model' and the Predictability of Stock Returns, Review of Finance 17",
        "Counter-evidence: https://github.com/jacobmorrisva/yield-gap-fed-model-replication",
    ],
    exact_rule=(
        "Month-end t: YG_t = ln(1 + E/P) - ln(1 + Y10), E/P = Shiller S&P 500 trailing 12-month earnings / price with earnings lagged 4 months for release, "
        "Y10 = DGS10 at the month-end. Regress next-month S&P excess return on YG using all monthly data up to t (expanding, from 1962); forecast t+1; "
        "long ES 1x if the forecast > 0, else T-bills; fill next_close. Variants: V1 expanding regression; V2 rolling 20-year regression; V3 long iff YG_t > its "
        "expanding median."
    ),
    instruments="ES (futures_daily); Shiller monthly data; FRED DGS10; ff_daily/rf for excess returns",
    data_needed="Shiller ie_data (free HTTP), fred_daily DGS10 (have), futures_daily ES",
    external_evidence=(
        "QuantConnect/Quantpedia SPY/SHY (code start 2000, gross): Sharpe 0.369, vol 14.3%. jacobmorrisva replication of Maio (2013) on 2005-2025: yield gap "
        "positive but insignificant at 1-12 month horizons, R-squared < 1%."
    ),
    evidence_score=1,
    adaptation_note="Near-permanent long in 2009-2021 (low yields) so it mostly measures equity beta; overlaps macro sibling valuation timing rules.",
)

# 17 -----------------------------------------------------------------------------------------
add(
    id="github_qc_january_barometer",
    name="January barometer (stay long Feb-Dec only after a positive January)",
    family="calendar",
    source_types=["github", "quantconnect", "paper"],
    sources=[
        "https://github.com/paperswithbacktest/awesome-systematic-trading static/strategies/january-barometer.py",
        "https://github.com/QuantConnect/Tutorials '04 Strategy Library/113 January Barometer'",
        "Cooper, McConnell & Ovtchinnikov (2006), The other January effect, Journal of Financial Economics 82",
    ],
    exact_rule=(
        "Hold ES throughout January; at the last session of January, if January's ES excess return > 0 stay long ES February-December, otherwise hold T-bills "
        "February-December; fills next_close. Sizing: 10% ex-ante vol (also 1x). Variants: V1 source; V2 February-December only (no January holding); "
        "V3 equal-risk basket of ES NQ RTY YM with the barometer read on ES."
    ),
    instruments="ES (V3 adds NQ RTY YM)",
    data_needed="futures_daily (have)",
    external_evidence=(
        "QuantConnect/Quantpedia SPY (code start 2000, gross): Sharpe 0.365, vol 7.4%. Cooper et al. (2006): 1857-2005 returns after positive Januaries "
        "exceed those after negative ones. Red flags: only about 14 annual signals in our in-sample window; mostly 'long in most years'."
    ),
    evidence_score=2,
    adaptation_note="Not in the calendar sibling list (it has Halloween, TOM, OpEx, payday, seasonality).",
)

# 18 -----------------------------------------------------------------------------------------
add(
    id="github_qc_crude_oil_predicts_equity",
    name="Lagged oil return predicts equities (QuantConnect 'Can crude oil predict equity returns')",
    family="macro_timing",
    source_types=["github", "quantconnect", "paper"],
    sources=[
        "https://github.com/QuantConnect/Tutorials '04 Strategy Library/06 Can Crude Oil Predict Equity Returns'",
        "https://github.com/paperswithbacktest/awesome-systematic-trading static/strategies/crude-oil-predicts-equity-returns.py",
        "Driesprong, Jacobsen & Maat (2008), Striking oil: another puzzle?, Journal of Financial Economics 89",
    ],
    exact_rule=(
        "Month-end t: OLS of monthly S&P excess return (t) on the previous month's oil return (t-1) over all available months (expanding; oil = FRED DCOILWTICO "
        "from 1986, or CL TR index after 2010); predicted return for t+1 from this month's oil return. Long ES 1x if the prediction exceeds the monthly T-bill "
        "rate, else T-bills; fill next_close. Variants: V1 expanding OLS; V2 rolling 120-month OLS; V3 simple sign rule: long iff last month's oil return < 0."
    ),
    instruments="ES; WTI (FRED DCOILWTICO) or CL",
    data_needed="FRED DCOILWTICO (free CSV), futures_daily (have)",
    external_evidence=(
        "QuantConnect tutorial 2010-2017: Sharpe 0.72 vs 0.60 for the benchmark, but the tutorial itself notes most monthly regressions are not significant; "
        "awesome-systematic-trading table: Sharpe 0.599, vol 11.5%. Paper: oil changes negatively predict returns in 48 markets 1973-2003."
    ),
    evidence_score=2,
    adaptation_note="Likely the same rule as macro_regime_oil_shock_equity (sibling); keep only one after dedup.",
)

# 19 -----------------------------------------------------------------------------------------
add(
    id="github_dual_thrust_es_hourly",
    name="Dual Thrust / volatility-breakout day trading on ES (hourly adaptation)",
    family="intraday_breakout",
    source_types=["github", "quantconnect"],
    sources=[
        "https://github.com/QuantConnect/Tutorials '04 Strategy Library/05 Dual Thrust Trading Algorithm'",
        "https://github.com/QuantConnect/Lean Algorithm.Python/Alphas/VIXDualThrustAlpha.py (k1 = k2 = 0.63, 20-bar range)",
        "https://github.com/je-suis-tm/quant-trading (Dual Thrust backtest.py); Larry Williams volatility breakout (https://github.com/SC4RECOIN/simple-crypto-breakout-strategy)",
    ],
    exact_rule=(
        "ES hourly bars (UTC start, converted to New York time), session 09:00-16:00 ET. Range = max(HH - LC, HC - LL) over the previous N = 4 sessions "
        "(HH/LL = highest high/lowest low, HC/LC = highest/lowest close of those sessions). Upper = session open + k1*Range, lower = open - k2*Range, k1 = k2 = 0.5. "
        "On an hourly close above upper go long (reverse if short), below lower go short; flat at the 16:00 ET close. Cost ES 1 bp per side. Variants: V1 Dual "
        "Thrust N = 4, k = 0.5; V2 Larry Williams: long only when price > open + 0.5*(previous session high - low), exit at the close; V3 Lean parameters "
        "k1 = k2 = 0.63 with a 20-session range."
    ),
    instruments="ES (databento hourly ES)",
    data_needed="databento_raw/glbx_ohlcv1h_v01_es_zn.parquet (have)",
    external_evidence="No published risk-adjusted statistics in the QuantConnect tutorial, Lean alpha or je-suis-tm script (educational; the tutorial says it 'beat the market' on SPY in one window).",
    evidence_score=1,
    adaptation_note="Hourly bars only approximate intraday breakout triggers; overlaps intraday_micro_orb_es_hourly (sibling). Keep as a low-prior check.",
)

# 20 -----------------------------------------------------------------------------------------
add(
    id="github_dynamic_breakout_ii",
    name="Dynamic Break Out II (adaptive-lookback channel + Bollinger filter) on futures",
    family="trend_following",
    source_types=["github", "quantconnect", "book"],
    sources=[
        "https://github.com/QuantConnect/Tutorials '04 Strategy Library/04 The Dynamic Breakout II Strategy'",
        "Pruitt, Hill & Russak (2012), Building Winning Trading Systems, p.126; Pruitt (1996), Futures Magazine",
    ],
    exact_rule=(
        "Daily per futures contract: sigma_t = 30-session std of closes; lookback N_t = round(N_{t-1} * (1 + (sigma_t - sigma_{t-1})/sigma_t)), clipped to [20, 60], N_0 = 20. "
        "Bollinger bands = N_t-session SMA +- 2 std. Enter long when close > highest high of the last N_t sessions and close > upper band; enter short when close < "
        "lowest low of the last N_t sessions and close < lower band; exit longs when close < N_t-session SMA, shorts when close > SMA. Equal ex-ante vol per "
        "position (EWMA vol), book scaled to 10%; decide close, fill next_close. Variants: V1 bounds [20, 60]; V2 bounds [10, 40]; V3 V1 without the Bollinger condition."
    ),
    instruments="30 CME futures",
    data_needed="load_ohlc daily high/low/close (have)",
    external_evidence="QuantConnect: EURUSD and GBPUSD over 6 years, 'drawdown of 20%', profitable in trending markets; no Sharpe given. Book results (1990s futures) not reproduced here.",
    evidence_score=1,
    adaptation_note="An adaptive Donchian; related to sibling turtle/Clenow breakouts but with volatility-driven lookback and SMA exit.",
)

# 21 -----------------------------------------------------------------------------------------
add(
    id="github_lev_above_ma200_es",
    name="Leverage the S&P uptrend: 2x ES above the 200-day SMA, 1x below",
    family="equity_trend_timing",
    source_types=["github"],
    sources=["https://github.com/Taff1887/leveraged-trend-following (README, reports/research_paper.md)"],
    exact_rule=(
        "Daily: if the S&P (^GSPC, or ES TR index) close > its 200-session SMA, hold 2x ES notional, else 1x ES; decide at close, fill next_close; costs ES 1 bp per "
        "unit of notional traded. Variants: V1 2x above / 1x below; V2 3x above / 1x below; V3 1x above / T-bills below (the Faber move-to-cash twin, benchmark)."
    ),
    instruments="ES (futures_daily); ^GSPC (index_daily) for the signal",
    data_needed="futures_daily, index_daily (have)",
    external_evidence=(
        "S&P total return 1928-2026 net of costs: buy-and-hold Sharpe 0.43 (maxDD -84%); MA200 to cash Sharpe 0.63 (maxDD -46%, information ratio vs S&P about 0, "
        "recently negative); 2x above MA Sharpe 0.51 with information ratio 0.53; 4x above MA Sharpe 0.56, IR 0.57. Red flags: Sharpe gain over buy-and-hold is "
        "small; the edge is in IR vs the index, not in absolute Sharpe."
    ),
    evidence_score=3,
    adaptation_note="Overlaps sibling trend_momentum_es_trend_timing for V3; V1/V2 (leveraged uptrend) are distinct. Report both raw and 10%-vol scaled.",
)

for c in C:
    assert c["id"].startswith("github_")

(OUT / "candidates.json").write_text(json.dumps({"label": "github", "candidates": C}, indent=1), encoding="utf-8")
print(len(C), "candidates written")
