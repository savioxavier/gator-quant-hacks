# bt_3 common conventions (pre-registered 2026-10-03, before any backtest of these four rules)

Applies to every strategy in bt_3 unless its own SPEC.md says otherwise.

- Data: engine.load_ohlc(tickers, "FWD") and engine.load_rf("FWD") (all data through 2026-10-02). All estimators
  are trailing-only, so the in-sample numbers are computed from the same run, sliced at 2024-10-02.
- Decision dates: last NYSE session of each month (src.forward2._month_ends). Decisions use data through the
  close of that session only.
- Fills: futures `next_close` (held from the close of the next session), ETFs `next_open`. engine.simulate,
  which holds constant target weights between decisions (daily drift rebalanced and charged).
- Futures daily excess return r_i = pct change of the F_ total-return index minus the T-bill.
- sigma_i = sqrt(252 * EWMA(r_i^2, com=60)) (min 60 obs), as S1.
- Eligibility (futures): >= 260 sessions of return history, finite positive sigma_i, F_ volume > 0 in at least
  one of the last 10 sessions (as S1).
- "Risk unit" weight = 0.40 / sigma_i / N.
- "Book to 10%": scale the decision weight vector so its ex-ante annualised vol from the trailing 252-session
  sample covariance of daily excess returns (min 60 obs, NaN -> 0) is 10%; then cap gross notional at 3
  (futures) or 2 (ETFs).
- Costs, one-way per unit notional: ES/NQ/YM 1 bp, RTY 2, ZT 0.5, ZF 0.7, ZN 1, ZB/UB 1.5, FX futures 1,
  CL/GC/SI/HG 2, NG/HO/RB/PL 3, grains (ZC ZS ZW ZL ZM) and livestock (LE HE) 4; roll days cost one extra round
  trip (engine). ETFs: config.cost_bps (sector SPDRs 5 bp, SPY 3 bp); ETF shorts pay 30 bp/yr borrow
  (engine). 2x stress = cost_mult 2.
- Series columns: net_1x, net_2x, gross = daily net/gross return minus T-bill.
- Windows: in-sample = first session on which every variant of the strategy holds positions .. 2024-10-02
  (common start for the variants so they are comparable). Later window 2024-10-03..2026-10-02 is descriptive
  only and never used for any choice.
- Headline variant: the variant with the highest in-sample net (1x) Sharpe among the 3 pre-declared variants;
  all three are reported. The saved standard series is the headline variant; the other variants are saved
  under bt_3/<id>/variants/.
- Metrics (each window): Sharpe of net_1x, net_2x, gross (daily mean/std * sqrt 252); annualised arithmetic
  mean net excess return; annualised vol; max drawdown of the compounded net_1x excess series; calendar
  years with >= 126 sessions in the window: worst year return and % positive; rolling 504-session Sharpe
  10th percentile; one-way turnover per year (sum of |trade| incl. roll trades / years); Newey-West t of
  mean net_1x excess (engine default lags); correlation of daily net_1x with ES excess (F_ES), S1
  (forward2.returns("S1","FWD") - rf) and F2 (forward.returns("F2","FWD") - rf).
- Nothing is written to the repo; no trial logging; the OOS lock is never released.
