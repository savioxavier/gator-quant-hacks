# bt_0 common conventions (pre-registered 2026-10-03, before any strategy return of this batch was computed)

Applies to all four strategy folders in bt_0. Each folder's SPEC.md states the source rule, the URL, the source
sample and reported numbers, the three pre-declared variants and the adaptations.

## Data and point-in-time rules
* Universe: the 30 CME roots F_ES F_NQ F_RTY F_YM F_ZT F_ZF F_ZN F_ZB F_UB F_CL F_HO F_RB F_NG F_GC F_SI F_PL F_HG
  F_ZC F_ZS F_ZW F_ZL F_ZM F_LE F_HE F_6E F_6J F_6B F_6A F_6C F_6S (futures_daily, 2010-06-07 .. 2026-10-02).
* Daily excess return r_i,t = F_ total-return index return minus the T-bill return (load_rf). The "price" used by
  continuous-forecast rules is the cumulative EXCESS-return index prod(1 + r) (a ratio back-adjusted futures price
  without the T-bill accrual that real futures prices do not contain).
* Data are loaded once with period "FWD" (all data through 2026-10-02). Every estimator is trailing (uses only data
  up to the decision close). Decisions at the close of d; engine.simulate exec="next_close" (traded at the close of
  d+1, earning from d+2). Between decisions the engine trades back to the targets daily (drift costs included);
  roll days charge one extra round trip.
* Eligibility of a future at a decision (identical to forward test 2's S1): >= 300 sessions of history, a finite
  positive volatility estimate, and >= 1 traded session (volume > 0) in the last 10 sessions.
* Book scaling ("book to 10%"): the weight vector is rescaled to 10 % annualised ex-ante volatility with the trailing
  252-session sample covariance of daily excess returns (min 60 observations, NaN -> 0), then capped at gross
  notional 3 (same function as forward2._scale_to_target).

## Costs (one-way, bp per unit of notional traded)
ES NQ YM 1; RTY 2; ZT 0.5; ZF 0.7; ZN 1; ZB UB 1.5; 6E 6J 6B 6A 6C 6S 1; CL GC SI HG 2; NG HO RB PL 3;
ZC ZS ZW ZL ZM LE HE 4. Stress = 2x the map. Gross = before costs.

## Windows
* In-sample (IS): first session with a non-zero held position (about 2011-08/09, set by the 300-session warm-up from
  2010-06) through 2024-10-02. All choices (headline variant) use IS only.
* Later window 2024-10-03 .. 2026-10-02: already seen by the project, reported as descriptive only.

## Metrics (per variant)
IS net Sharpe at 1x and 2x and gross (daily excess over T-bill, x sqrt(252)); annualised mean excess (net 1x) and
CAGR of excess; annualised volatility; max drawdown of the net-1x excess-return equity curve; worst calendar year
and % positive calendar years (IS calendar years, the partial first and last years included); 10th percentile of the
rolling 504-session Sharpe inside IS; turnover per year (sum of |trades| incl. roll trades, fraction of NAV);
Newey-West t of the mean daily excess (lags 4(n/100)^(2/9)); daily correlations inside IS with ES excess returns
(F_ES), with S1 (forward2.returns("S1","FWD") minus rf) and with F2 (forward.returns("F2","FWD") minus rf);
later-window net Sharpe (1x) and max drawdown. Source numbers are printed next to ours.

## Headline selection (fixed now)
For each strategy the headline row is the pre-declared variant with the highest IS net Sharpe at 1x (choice on IS
only); variants = 3 is reported so the selection can be deflated. All three variants are reported. The source's own
rule (V1) is always reported alongside.

## Outputs
Standard headline series: hunt100/series/<id>.parquet (columns net_1x, net_2x, gross = daily EXCESS returns, on the
NYSE calendar from the IS start through 2026-10-02) and <id>.json sidecar. Variant series under
bt_0/<id>/variants/. Nothing is written to the repo; no trial logging; the OOS lock is never released.
