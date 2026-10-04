# trend_momentum_trends_everywhere_etf - pre-registration (written 2026-10-03 15:02 ET, before any computation)

## Source
- Babu, Levine, Ooi, Pedersen and Stamelos (2020), "Trends Everywhere", Journal of Investment Management. https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/AQR-Trends-Everywhere_JOIM.pdf
- Source rule (in my words): time-series trend (1-, 3- and 12-month lookbacks blended, positions inversely proportional to volatility) applied beyond the classic futures universe: credit (CDS indices), emerging-market equity/FX/rates, equity sectors and factors, etc.; trend profits appear in each of these "new" asset sets.
- Source sample and reported numbers (as listed by the hunt): 156 instruments 1985-2017; combined trend Sharpe about 1.60 gross; trend in the new asset sets out of sample 1.34 and 0.95 gross; no net or post-publication record.

## Our rule (common conventions of the trend_momentum hunt)
- Universe: EEM, VGK, EWJ, VNQ, HYG, LQD, EMB, TIP and the 9 sector SPDRs XLB XLE XLF XLI XLK XLP XLU XLV XLY (ETF total-return adjusted closes).
- At each month-end (last NYSE session): s_i = mean(sign(R_21), sign(R_63), sign(R_252)) of compounded daily excess returns (ETF return minus T-bill) through the close.
- sigma_i = sqrt(252 * EWMA(r^2, com=60)); w_i = s_i * 0.40 / sigma_i / N_eligible.
- Book to 10% ex-ante vol with the trailing 252-session covariance (min 60); gross <= 2.
- Eligibility: >= 260 sessions of returns, sigma > 0, a close on the decision date.
- Held until the next month-end (engine re-trades to target daily, drift costs included); next_open fills.
- Costs: config ETF tiers (EEM/HYG/LQD 3 bp; VGK/EWJ/VNQ/EMB/TIP/sectors 5 bp), shorts pay 30 bp/yr borrow; 2x stress.

## Variants (pre-declared, all reported)
- V1: ETFs only, long/short as above.
- V2: equal-risk combination of V1 and the 30-futures 1/3/12 book (the S1 rule, src/forward2.py s1_decisions): w = 0.5 * w_V1 + 0.5 * w_S1 (each already at 10%), rescaled to 10% ex-ante vol with the trailing 252-session covariance of all 47 instruments, gross <= 3. ETF legs next_open with ETF costs, futures legs next_close with the realistic futures map (ES/NQ/YM 1, RTY 2, ZT 0.5, ZF 0.7, ZN 1, ZB/UB 1.5, FX 1, CL/GC/SI/HG 2, NG/HO/RB/PL 3, grains/livestock 4 bp); combined daily net = net_ETF + net_FUT - rf (exact under the engine's linear accounting). Window starts with the first S1 decision (about 2011-08).
- V3: long-or-cash V1 (s clipped at 0, T-bills otherwise), book to 10% (gross <= 2).

## Selection and windows
- In-sample: first held position (ETFs about 2006; V2 about 2011) to 2024-10-02; variant selection = highest in-sample net Sharpe on the common window (V2 start to 2024-10-02). Later window descriptive.
- Adaptation: credit via HYG/LQD and EM via EEM/EMB rather than CDS indices and EM FX/swaps; sectors via SPDRs. F1's 12-month TSMOM on 15 ETFs overlaps partially (HYG, LQD, EEM, VNQ, TIP...). Likely effect: ETF credit/EM trends are dominated by equity beta, so diversification gain is smaller than with CDS/FX.
