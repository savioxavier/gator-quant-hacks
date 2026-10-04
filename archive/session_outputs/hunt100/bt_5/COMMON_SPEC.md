# bt_5 common specification (pre-registered 2026-10-03, before any strategy return was computed)

Applies to the four strategies of this batch. Each strategy folder has its own SPEC.md with the source rule,
the three pre-declared variants and the source numbers. Only data plumbing was examined before writing this
(coverage of the two volume-ranked contracts per root, delivery-month gaps, how often the legs change).

## Data

* Front total-return index: `futures_daily.parquet` via `engine.load_ohlc(["F_<root>"], "FWD")`; daily excess
  return = index return minus the T-bill (`load_rf`). Used for eligibility, instrument volatility and the P&L of
  outright books (double sort, value).
* Two volume-ranked contracts per root: `edges/carry/contracts.parquet` (raw Databento GLBX.MDP3 ohlcv-1d closes of
  `.v.0` / `.v.1`, instrument id mapped to raw CME symbol and delivery month by the free symbology endpoint).

## Near / far legs (the hunt's STD convention, implemented as written)

1. Raw CME dates on weekdays only (Saturday/Sunday-evening bars dropped, as in the futures_daily builder).
2. On a raw date where both ranks printed with positive closes, different delivery months and a gap of at most
   12 months: near = earlier delivery, far = later delivery. Otherwise the legs are undefined that day.
3. Same-contract leg return on raw date t = close_t / close_{t-1} - 1 of the leg's instrument, where close_{t-1}
   is that instrument's close on the previous raw date of the root (in either rank). If either leg's return is
   missing, BOTH leg returns are set to 0 that day (spread return 0) and the day is flagged invalid.
4. A leg "rolls" on raw date t when its instrument differs from the last defined instrument of that leg.
5. Mapping to NYSE sessions exactly like futures_daily: each raw date goes to the first NYSE session on or after it;
   leg returns are compounded within the NYSE session; roll flags take the max; a session is valid if at least one
   valid raw date fell in it. Leg total-return index = 100 x cumprod(1 + leg excess return + T-bill), stored as
   synthetic engine tickers `F_<root>_N` (near) and `F_<root>_D` (far) with open = high = low = close and the roll
   flag, so `engine.simulate` charges one extra round trip per leg on its roll days and no short borrow.
6. Daily carry observation (positive = backwardation): c = (P_near / P_far)^(1/dt) - 1 with dt = month gap / 12,
   last observation per NYSE session. Near-contract price level: last near close per NYSE session.

Timing: the raw daily bar of date d closes at or before 00:00 UTC of d+1, before the close of d+1 at which a
decision taken at d is filled (`exec="next_close"`, held from the close of d+1). Signals use data through the
decision session only; no extra lag is added (the futures_daily index uses the same bar closes).

## Portfolio conventions (STD)

* Instrument volatility sigma_i: EWMA (centre of mass 60 sessions, min 60 observations) of squared daily excess
  returns, annualised x sqrt(252). For spreads sigma_s is the same estimator applied to the spread return on valid
  sessions only.
* Eligibility at a decision date (forward test 2's S1 rule): >= 300 sessions of F_<root> index history, positive
  finite EWMA volatility, volume > 0 in at least one of the last 10 sessions, plus a valid signal. Spread books
  also need a finite sigma_s and at least one valid spread session in the last 10.
* Book scaling: ex-ante volatility of the target weights from the trailing 252-session sample covariance of daily
  excess returns of the held instruments (min 60 pairwise observations; for spread books the covariance is taken
  at the leg level, which for equal and opposite legs equals the spread covariance); scale = min(0.10 / vol, 4).
  Spread books then cap each leg at 3x NAV per root (if a root's larger leg exceeds 3, both legs of that root are
  scaled down together, preserving the hedge ratio).
* Decisions at the close of the last NYSE session of each month (`forward2._month_ends`), `exec="next_close"`;
  between decisions the engine trades back to the targets daily (drift costs included).

## Costs (one-way bps per unit notional, each leg at the outright rate)

ES/NQ/YM 1, RTY 2, ZT 0.5, ZF 0.7, ZN 1, ZB/UB 1.5, FX futures 1, CL/GC/SI/HG 2, NG/HO/RB/PL 3,
ZC/ZS/ZW/ZL/ZM/LE/HE 4. Roll days: one extra round trip of the held leg (engine). Stress: 2x. Gross also reported.
No calendar-spread exchange discount is assumed.

## Windows, selection, statistics

* In-sample: first session with a position through 2024-10-02 (each variant's own start, stated). Later window
  2024-10-03 .. 2026-10-02: descriptive only, never used for any choice.
* Three pre-declared variants per strategy, all reported. Headline = the variant with the highest in-sample net
  Sharpe at realistic costs; the deflated Sharpe over the 3 variants is reported with it. V1 (the hunt's primary)
  is reported in full whatever the choice.
* Statistics on daily excess returns (net_1x, net_2x, gross): annualised Sharpe, annualised mean (x252) and
  volatility, max drawdown of the compounded net excess curve, worst calendar year and % positive years (years
  with >= 126 sessions), 10th percentile of the rolling 504-session Sharpe, turnover per year (sum of |trades| incl.
  roll trades), Newey-West t of the mean (engine lag rule), daily correlations with ES excess, S1 trend
  (`forward2.returns("S1","FWD")` minus rf) and F2 (`forward.returns("F2","FWD")` minus rf).
* Series: `hunt100/series/<id>.parquet` (headline variant, columns net_1x, net_2x, gross = daily excess returns)
  plus `<id>.json`; every variant's series also under the strategy folder.
* Read-only use of the repo: no engine.run_backtest / log_trial, no OOS unlock, nothing written under results/.
