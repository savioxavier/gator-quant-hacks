# trend_momentum_index_mac5_reversal - pre-registration (written 2026-10-03 15:02 ET, before any computation)

## Source
- Baltussen, van Bekkum and Da (2019), "Indexing and stock market serial dependence around the world", Journal of Financial Economics. https://www3.nd.edu/~zda/Indexing.pdf
- Source rule (in my words): MAC(5) is the daily return of a position proportional to the weighted sum of the last four index returns, r_t * (4 r_{t-1} + 3 r_{t-2} + 2 r_{t-3} + r_{t-4}) / (5 sigma^2). Since index serial dependence turned negative after about 1999, the profitable trade is AGAINST this weighted past return (short after up days, long after down days). The position held over day t uses returns through the close of t-1 (no implementation lag). A one-day-lag version uses returns through t-2.
- Source sample: 20 major equity indexes (plus their futures and ETFs), up to 2016; post-1999 subsample from 1999-03-02.
- Reported numbers: a strategy trading against MAC(5) earns an annual Sharpe ratio of 0.63 on all indexes pooled and 0.67 on the S&P 500 alone after 1999-03-02 (gross, no implementation lag, no costs); serial dependence becomes indistinguishable from zero with a one-day implementation lag (hunt list quotes pooled post-1999 lagged coefficient -0.016, t -0.60). Authors note transaction costs could eliminate profits.

## Our rule (common conventions of the trend_momentum hunt)
- Instruments: F_ES, F_NQ, F_RTY, F_YM (CME front total-return index; RTY data from 2017-07).
- r_t = daily excess return of the index (index return minus T-bill) through the close of decision day d.
- sigma_i = sqrt(252 * EWMA(r^2, com=60)), min 60 obs; sigma_daily = sigma_i / sqrt(252).
- x_i = -(4 r_d + 3 r_{d-1} + 2 r_{d-2} + r_{d-3}) / (10 * sigma_daily_i).
- Raw weight w_i = clip(x_i, -2, 2) * 0.10 / sigma_i / N_eligible (N = 4 when all are eligible).
- Book to 10%: rescale the weight vector so that the trailing 252-session covariance (min 60) of daily excess returns gives 10% annualised ex-ante volatility; gross <= 3 (futures), <= 2 (ETFs).
- Eligibility: >= 260 sessions of returns, sigma > 0, traded (volume > 0) in the last 10 sessions.
- Daily decisions at the close of d.
- Costs (one-way, per unit notional): ES/NQ/YM 1 bp, RTY 2 bp; stress 2x. ETFs: config tier (SPY/QQQ/IWM/DIA = 3 bp) + 30 bp/yr borrow on shorts.

## Variants (pre-declared, all reported)
- V1: futures, next_close fills (decision at close d, filled at close d+1, earns from d+2) = the paper's one-day implementation lag.
- V2: next_open fills. ADAPTATION: our futures panels have open = close (built from daily closes only), so next_open on F_ tickers is identical to next_close. V2 therefore uses the ETF proxies SPY (S&P 500), QQQ (Nasdaq 100), IWM (Russell 2000), DIA (Dow) with true NYSE opens: signal from ETF close-to-close excess returns, fill at the open of d+1 (loses only the overnight gap of d+1). ETF costs/borrow apply; ETF data start 2005, so V2 has a longer own window. Likely effect: closer to the paper's no-lag version than V1, but pays 3 bp per side plus borrow.
- V3: weekly. At the last NYSE session of each week, w_i = -sign(5-session compounded excess return) * 0.10 / sigma_i / N, book to 10%, hold to next weekly decision, futures, next_close.

## Selection and windows
- In-sample: from each variant's first held position to 2024-10-02. Variant selection = highest in-sample net Sharpe (realistic costs) on the COMMON window (from the latest variant start, the futures V1 start, to 2024-10-02). 2024-10-03..2026-10-02 is descriptive only.
- Adaptation noted in the task: the engine cannot fill at the same close that produced the signal, so the paper's no-lag 0.63/0.67 is not reachable; V1 is the lagged version the paper itself shows to be insignificant.
- Expected: weak or negative after costs (daily sign flips -> high turnover).
