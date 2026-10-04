# trend_momentum_basis_reversal - pre-registration (written 2026-10-03 15:02 ET, before any computation)

## Sources
- Rossi, Zhang and Zhu (2025), "Short-Term Basis Reversal" (working paper), summarised at https://www.cxoadvisory.com/commodity-futures/commodity-futures-term-structure-reversals (summary paywalled beyond the abstract).
- Independent replication: QuantReturns, "When Futures Overreact: A Weekly Edge Across the Futures Curve" (2025-07-25), https://quantreturns.substack.com/p/when-futures-overreact-a-weekly-edge
- Source rule (in my words): the weekly spread return between the first and second nearby futures, S = r_F1(week) - r_F2(week), is negatively autocorrelated: front-month outperformance this week tends to reverse next week. Replication: each Friday rank all markets (global equity index + commodity futures) by last week's F1-F2 spread return; go long the 4 with the most negative spread return and short the 4 with the most positive, equal weight, hold one week. The replication describes 8 contracts per side (i.e. it appears to trade the spread, long F1/short F2 or the reverse), and its edge test measures next-week SPREAD returns.
- Source samples and reported numbers: RZZ 22 commodities 1980-2022, spread reversal predictable, not explained by carry or momentum, stronger in high volatility; summaries quote 17.6%/yr and Sharpe 1.42. Replication 2007-2025: Low-minus-High three-bin spread about +10%/yr, t 3.91; strategy 9.68%/yr, vol 10.6%, Sharpe 0.92, max DD -17%, beta about 0, gross of costs.

## Our rule
- Spread return: at each weekly decision date t (last NYSE session of the calendar week) and the previous one t0, take the rank-0 (.v.0) and rank-1 (.v.1) instrument ids at t from databento_raw/glbx_ohlcv1d_v01; r_F1 = close(front id, t)/close(front id, t0) - 1 and r_F2 likewise for the second id, using that instrument's own close on each date whatever its rank (same instrument within the week). CME dates map to NYSE dates as in the data builder (last CME session on or before the NYSE date). Missing close for either id -> S undefined, market skipped that week.
- Universe eligibility at t (S1 conventions on futures_daily): >= 260 sessions of history, sigma > 0, traded in the last 10 sessions, and S defined.
- Cross-sectional rule: long the F_ front total-return index of the 4 markets with the most negative S, short the 4 with the most positive S; inverse-vol risk weights w_i = +/-0.40/sigma_i/8 (sigma_i = EWMA com 60 annualised vol of the F_ index excess returns); book to 10% ex-ante vol with the trailing 252-session covariance (min 60), gross <= 3; held until the next weekly decision (engine re-trades to target daily); next_close fills.
- Costs one-way: CL/GC/SI/HG 2 bp, NG/HO/RB/PL 3 bp, grains/livestock 4 bp, ES/NQ/YM 1 bp, RTY 2 bp; 2x stress; roll days charge an extra round trip (engine).

## Variants (pre-declared, all reported)
- V1: 15 commodities (CL HO RB NG GC SI PL HG ZC ZS ZW ZL ZM LE HE), 4 long / 4 short.
- V2: 15 commodities + ES NQ RTY YM (as in the replication's mixed universe), 4/4.
- V3: time series on the 15 commodities: w_i = -sign(S_i) * 0.40/sigma_i/N, book to 10%.

## Diagnostic (NOT a strategy, not eligible for selection)
- Edge test as in the replication: next-week SPREAD return (front minus second, ids fixed at t) of the Low-4 minus High-4 portfolio, equal weight, gross, V1 universe; reported with no lag (t to next t) and with a one-day lag (t+1 to next t+1). It shows whether the curve reversal exists in our data and how much the front-only adaptation dilutes it.

## Adaptation and likely effect
- We trade only the front total-return index (engine panels hold front contracts only), not the F1-F2 spread. The predicted reversal is in the spread, whose volatility is a small fraction of the outright front volatility, so even if the full spread reversal accrues to the front leg the front-only trade dilutes the Sharpe heavily (roughly by the ratio of spread vol to outright vol). Expect a much weaker result than the source.
- Futures data start 2010-06; in-sample from the first held position (about 2011-06) to 2024-10-02; later window descriptive.
- Variant selection: highest in-sample net Sharpe (realistic costs) on the common window.
