# bt_1 common conventions (written 2026-10-03, before any computation in bt_1)

Applies to the four strategies in this label; each strategy folder has its own SPEC.md with the rule and variants.

Universe: 30 CME futures F_ES F_NQ F_RTY F_YM F_ZT F_ZF F_ZN F_ZB F_UB F_CL F_HO F_RB F_NG F_GC F_SI F_PL F_HG
F_ZC F_ZS F_ZW F_ZL F_ZM F_LE F_HE F_6E F_6J F_6B F_6A F_6C F_6S.

Data and point-in-time rules
- Returns: daily excess return of the F_ total-return index (index return minus T-bill, rf_daily).
- Price for signals: the excess-return index p = cumprod(1 + excess) per future (a back-adjusted futures price proxy;
  the F_ total-return index itself contains T-bill accrual, which would add a spurious up-trend).
- The F_ index in futures_daily has open = high = low = close (close-only). Range-based quantities (Yang-Zhang
  volatility, Turtle true range N) therefore come from the raw Databento front-contract (.v.0) daily OHLC in
  databento_raw/glbx_ohlcv1d_v01.parquet. Those bars are UTC-day bars (incl. short Sunday-evening bars); they are
  aggregated onto the NYSE calendar exactly like the index builder (each CME bar date maps to the next NYSE date
  >= it; open = first open, high = max, low = min, close = last close), keeping only bars of the instrument that is
  front on the last CME date of the group. The overnight jump uses the previous group's close of the same
  instrument (both ranks searched); roll days without a same-contract previous close drop out of the estimator.
  Every OHLC-derived quantity is lagged one NYSE session (the UTC bar of date d ends at 19:00/20:00 ET, after the
  NYSE close), so a decision at the close of d uses bars through d-1 only.
- Decisions at the close of d with data through d; execution exec="next_close" (held from the close of d+1);
  the engine trades back to targets every session (drift costs included); roll days cost one extra round trip.
- Eligibility of a future at a decision (as S1, notes of the trend_momentum hunt): >= 260 sessions of index history,
  positive volatility estimate, traded (volume > 0) in at least one of the last 10 sessions.
- sigma_i (EWMA) = sqrt(252 * EWMA(excess^2, com=60)), min 60 observations.
- 'Book to 10%' = rescale the weight vector so that the trailing 252-session sample covariance of daily excess returns
  (min 60 obs) gives 10% annualised ex-ante volatility; then gross <= 3.

Costs (one-way, per unit notional traded): ES/NQ/YM 1 bp, RTY 2, ZT 0.5, ZF 0.7, ZN 1, ZB/UB 1.5, FX futures 1,
CL/GC/SI/HG 2, NG/HO/RB/PL 3, grains (ZC ZS ZW ZL ZM) and livestock (LE HE) 4. Stress: 2x.

Windows: in-sample = first session with a non-zero held position (about mid-2011, 12 months of history needed)
through 2024-10-02. Later window 2024-10-03..2026-10-02 = already seen, descriptive only. All estimators are trailing,
so running the decision code over all data and slicing is identical to an in-sample-only run (checked numerically
for one variant per strategy by rerunning on period="IS").

Variant choice: at most 3 pre-declared variants per strategy, all reported. The headline variant (saved as the
standard series) is the variant with the highest in-sample net Sharpe at 1x costs. No other parameter is tuned.

Metrics (in-sample unless stated): net Sharpe 1x and 2x, gross Sharpe (annualised mean / sd of daily excess x sqrt 252),
annual return (mean daily net excess x 252), annual vol, max drawdown of the compounded net excess series, worst
calendar year and % positive calendar years (compounded net excess; partial first/last years included), 10th
percentile of the rolling 504-session Sharpe, turnover (sum of one-way traded notional per year, roll trades
included), Newey-West t of mean daily net excess (engine default lag), daily correlations with ES excess, S1 excess
(forward2.returns("S1","FWD") - rf) and F2 excess (forward.returns("F2","FWD") - rf); later window net Sharpe 1x and
max drawdown.

Standard series: hunt100/series/<id>.parquet with columns net_1x, net_2x, gross (daily excess returns, all dates from
the first live session to 2026-10-02) and a <id>.json sidecar.
