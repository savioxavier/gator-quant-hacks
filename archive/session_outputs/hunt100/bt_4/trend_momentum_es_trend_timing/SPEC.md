# trend_momentum_es_trend_timing - pre-registration (written 2026-10-03 15:02 ET, before any computation)

## Sources
- Faber (2007/2013), "A Quantitative Approach to Tactical Asset Allocation", https://www.trendfollowing.com/whitepaper/CMT-Simple.pdf : buy when the monthly close is above the 10-month simple moving average, move to cash when below. Reported (Table 2, S&P 500 total returns 1900-2005): timing CAGR 10.66% vs 9.75%, vol 15.38% vs 19.91%, Sharpe 0.43 vs 0.29 (4% rf, yearly), max DD -49.98% vs -83.66%, 70% time in market.
- Garg, Goulding, Harvey and Mazzoleni, "Momentum Turning Points" (AEA 2021 preliminary paper), https://benny.aeaweb.org/conference/2021/preliminary/paper/492Ds6fk : MED speed = average of SLOW (12-month sign) and FAST (1-month sign): +1 when both agree long, -1 when both agree short, 0 when they disagree. Reported on the US equity market: Sharpe SLOW 0.41, intermediate 0.48, MED 0.51, then 0.44, FAST 0.34 (their Table 7 first row).
- AQR TSMOM factor dataset (equity sleeve), https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Time-Series-Momentum-Factors-Monthly.xlsx : hunt calculation of TSMOM^EQ gross Sharpe 0.83 for 1985-2009, 0.19 post-publication, -0.20 for 2016-2024.
- Our yardstick: ES at 10% vol, unfiltered (forward2 ES_10VOL): 0.77 in-sample / 0.50 later (old cost map). The bar to beat is this benchmark, not cash.

## Our rule
- F_ES front total-return index; r = daily excess return; sigma = sqrt(252 * EWMA(r^2, com=60)).
- Month-end decisions (last NYSE session); position = signal * 0.10 / sigma (capped at 3x notional); T-bills for the rest; held until next month-end (engine re-trades to target daily); next_close fills; cost 1 bp one-way (2x stress); roll days charge an extra round trip.
- Eligibility: >= 260 sessions of returns, sigma > 0, traded in the last 10 sessions.

## Variants (pre-declared, all reported)
- V1: signal = 1 if the month-end F_ES index level > mean of the last 10 month-end levels (current included), else 0 (long or flat).
- V2: MED turning points: signal = +1 if sign(R_252) and sign(R_21) both positive, -1 if both negative, 0 if they disagree (compounded excess returns).
- V3: 12-month TSMOM: signal = sign(R_252), long/short.
- Benchmark (not a variant): signal = 1 always (ES at 10% vol, realistic 1 bp cost) on the same window.

## Selection and windows
- In-sample: from the first held position (about 2011-06, needs 260 sessions and 10 month-ends after 2010-06) to 2024-10-02; selection = highest in-sample net Sharpe on the common window. Later window descriptive.
- Adaptation: the F_ES index is excess return + T-bill (a fully collateralised total-return proxy for the S&P 500 with dividends embedded in the futures price), vol-scaled rather than 100% notional as in Faber. Likely effect: vol scaling already captures part of the drawdown protection, so the filter has less to add than in Faber's unscaled tests.
