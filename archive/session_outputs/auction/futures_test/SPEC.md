# Treasury auction cycle on futures (SPEC, written before any return was computed)

Written 2026-10-03, before any strategy return, event-study return or portfolio of this study was
computed. Already known when it was written: the paper (Lou, Yan & Zhang, FMG DP684 / RFS 2013), the
repository's sleeve E result on IEF (in-sample 0.16, 0.57 before 2014, -0.18 after), the month-end
sleeve C / CAL_TSY_ME_ZN result and the core_ER_6 portfolio. The only data inspected so far are the
auction table (counts, terms, announcement lags, day of month; no prices) and the column layout of
the hourly panel.

## 1. Data and conventions

* Auctions: `treasury_auctions.parquet` filtered by the repository loader
  `src/strategies/ifc_treasury.load_nominal_auctions("FWD")` (Notes and Bonds; FRNs dropped = no high
  yield; TIPS dropped = real-yield gap > 0.7 pp against the FRED nominal curve). Read-only import.
* Maturity of an auction = nearest standard term in {2, 3, 5, 7, 10, 20, 30} to its `security_term`
  (remaining term auctioned), NOT `original_security_term`. Reason: Treasury sometimes issues a new
  2-year (or 5-year) as a reopening of an old 5-year (or 7-year) note with the same maturity date;
  the original term would mislabel these as 5-/7-year auctions (19 rows since 2010, e.g. 2015-05-26).
  Reopenings (10-, 20-, 30-year) are auctions of their maturity (they are new supply).
* Instrument per maturity (deliverable baskets):
  * 2-year -> F_ZT (ZT basket: original term <= 5y3m, remaining 1y9m-2y; the new 2-year is CTD-like).
  * 5-year -> F_ZF (ZF basket: original term <= 5y3m, remaining >= 4y2m).
  * 7-year -> F_ZN. A 7-year note is NOT deliverable into ZF (original term > 5y3m) but is deliverable
    into ZN (remaining 6.5-10y) and sits at ZN's cheapest-to-deliver end. So 7-year and 10-year
    auctions both trade ZN.
  * 10-year (new and reopenings) -> F_ZN (the Ultra 10 is not in the cache).
  * 20-year -> F_ZB (ZB basket: remaining 15-25y).
  * 30-year -> F_UB (UB basket: remaining >= 25y; ZB's CTD is the 15-20y sector).
  * 3-year: not deliverable into any contract. Event study only (on F_ZT), never traded.
* Daily returns: `engine.load_ohlc(..., "FWD")` closes (total-return index = futures excess return +
  T-bill, NYSE calendar, 2010-06-07..2026-10-02); excess return = pct_change - rf_daily. The F_ daily
  bar ends at 00:00 UTC (19:00/20:00 ET), so day A's return contains the 13:00 ET auction.
* Point in time: the holding on return day t is decided at the close of t-2 (engine `next_close`).
  An auction may contribute to return day t only if its announcement date (mapped to the first NYSE
  day on or after `announcemt_date`) is on or before t-2. This is applied per return day, so a
  pre-auction window is traded only from the second session after the announcement (announcement
  lags since 2010: median 3 sessions for 2-year, 4 for 5-/10-/20-year, 5 for 7-/30-year). The
  tentative quarterly schedule is not in the cache, so it is not used (diagnostics D1/D2 show what it
  would add).
* Costs (one-way, bp of notional): ZT 0.5, ZF 0.7, ZN 1.0, ZB 1.5, UB 1.5, ES 1.0; 2x stress doubles
  all; gross = 0. Roll days cost one extra round trip of the position held into the roll (engine).
* Durations for DV01 matching (fixed, years): ZT 1.9, ZF 4.2, ZN 6.3, ZB 15, UB 20. DV01 of a futures
  position = notional x duration, so a DV01-neutral hedge of notional N in contract a with contract b
  is -N x D_a / D_b. Fixed durations are an approximation (ZN's CTD duration moved roughly 5.5-7 over
  2010-2026); the residual level exposure is reported as the correlation with F_ZN.

## 2. Event windows (paper alignment)

The paper's day 0 is the auction day. Table V: "On the t-th day before each auction, we construct a
hedge portfolio ... hold until the auction day, and then reverse". Read with close-to-close returns,
the position opened at the close of day -t earns return days -t+1..0, so the auction day belongs to
the PRE window; Figure 1 agrees (yields peak at the day-0 close, Y(t) - Y(0) < 0 on both sides). Hence
for every Treasury variant:

* pre window  = return days [A-t+1, A]  (t days, auction day included), position SHORT the auctioned
  maturity (or short it against the hedge);
* post window = return days [A+1, A+t]  (t days), position LONG.

ES (V4) follows the paper's Table X definition (t days after minus t days before, auction day left
out): short [A-5, A-1], long [A+1, A+5].

Overlapping windows of the same maturity add and the sum is clipped to [-1, 1] per instrument leg.
Different maturities trading the same contract (7- and 10-year on ZN) are separate sleeves whose
positions net in the combined book.

## 3. Sizing

Per maturity sleeve m on instrument i (or spread for hedged sleeves):

* L = min(cap, 0.10 / (sigma x sqrt(f))), fixed for each leg (pre or post) of each auction at the
  decision date of the leg's first traded return day.
* sigma = sqrt(252 x EWMA_com60(r^2)) of the instrument's daily excess returns (for a hedged sleeve:
  of the DV01-hedged spread r_a - (D_a/D_b) r_b), using data up to the decision date, min 40 obs.
* f = share of the trailing 252 return days (up to the decision date) on which sleeve m held a
  position (flags from the rule and the announcement gate, which do not depend on L); min 63 days.
* cap: 30 duration-years on the traded leg (ZT 15.8x, ZF 7.1x, ZN 4.8x, ZB 2.0x, UB 1.5x notional).
* No position before the first decision date with valid sigma and f (about 2010-09).

Combination of maturity sleeves (V1_all, V2_all, V3): equal risk. At each month-end close d,
w = 1/N over live sleeves (live = at least 63 return days since the sleeve's first position), S =
trailing 252-day covariance of the sleeves' unscaled gross daily returns (min 63 obs, pairwise, NaN ->
0), k = min(3, 0.10 / sqrt(252 w' S w)), applied to decision weights from d (return days from d+2).
Instrument weights = sum over sleeves of k x w_m x sleeve weights (netted), simulated once with
`engine.simulate(exec="next_close")`, so turnover, netting and roll costs are exact.

## 4. Variants (12 eligible + 2 diagnostics)

| id | rule |
|---|---|
| V1_all_t5 | outright, maturities 2/5/7/10/20/30 (ZT/ZF/ZN/ZN/ZB/UB), t = 5, equal risk across maturity sleeves |
| V1_all_t10 | same, t = 10 |
| V1_2y_t10 | outright F_ZT around 2-year auctions only, t = 10 (paper's maturity and headline t) |
| V2_2y_t10 | paper's Table V analogue: 2-year auctions, short ZT / long DV01-equal ZN over pre, reverse over post, t = 10 |
| V2_2y_t5 | same, t = 5 |
| V2_all_t5 | every maturity DV01-hedged with a contract outside its own auction cluster: end-of-month cluster (2/5/7-year) hedged with UB (30-year auctions fall in the second week), mid-month cluster (10/20/30-year) hedged with ZF (5-year auctions fall in the last week); t = 5; equal risk |
| V3_all_t5_x | V1_all_t5 dropping every auction dated on the 25th..31st or 1st..5th (paper's turn-of-month exclusion; removes most 2/5/7-year auctions and the overlap with sleeve C) |
| V3_all_t10_x | V1_all_t10 with the same exclusion |
| V4_ES_2y | F_ES short [A-5, A-1], long [A+1, A+5] around 2-year auctions; L = min(3, 0.10/(sigma sqrt f)) |
| V4_ES_2y_x | V4_ES_2y dropping 2-year auctions dated 25th..5th |
| V5_ZN_10y_id | hourly: on each 10-year auction day, ZN short from the last trade before 09:00 ET to the last trade before 13:00 ET, long from there to the last trade before 16:00 ET (hourly panel, bars starting 09-12 and 13-15 ET, trade_date = A, CME-only sessions excluded) |
| V5_ZN_7y10y_id | same on 7-year and 10-year auction days |
| D1_all_t5_known | DIAGNOSTIC, not eligible: V1_all_t5 with the announcement gate removed (assumes the auction calendar is known 5+ sessions ahead) |
| D2_2y_t10_known | DIAGNOSTIC, not eligible: V2_2y_t10 with the announcement gate removed (closest to the paper's Table V, which assumes the date is known 10 days ahead) |

V5 specifics: an auction day is used only if it was announced at least one NYSE day before and the
bars starting 12:00 and 15:00 ET exist. Return of a span = product of (1 + ret_simple) over its bars.
Position size L = min(5, 0.10 / (sigma_ZN x sqrt(f))) with sigma_ZN the daily EWMA vol up to A-1 and f
= share of trailing 252 NYSE days that were event days (min 63; default 12/252 or 24/252). Costs: four
one-way units per event (enter 09:00, flip at 13:00 = 2, exit 16:00) x L x 1.0 bp (2.0 bp at 2x). The
daily series is the intraday P&L on event days and 0 otherwise (no overnight position, no roll cost).

## 5. Windows, statistics, choice

* Selection: 2010-06-07..2020-12-31. Validation: 2021-01-01..2024-10-02. Full in-sample:
  2010-06-07..2024-10-02. Later (already seen, descriptive only): 2024-10-03..2026-10-02.
  Decay split: ..2013-12-31 vs 2014-01-01..2024-10-02. Every window starts at the variant's first
  live day; Sharpe = mean / std x sqrt(252) of daily excess returns including flat days.
* Per variant: net Sharpe at 1x (all windows), 2x (all windows), gross (full in-sample), Newey-West t
  of daily net 1x excess (engine default lags) on the full in-sample window and on selection, max
  drawdown of the excess-return equity (full in-sample), mean gross bp per event (unit notional on the
  auctioned leg, hedge leg by DV01, over the traded days of the event; V4 unit ES, V5 unit ZN),
  share of window days traded, correlation of daily net 1x excess with CAL_TSY_ME_ZN (sleeve C) and
  PORT_core_ER_6 over their common in-sample days, and correlation with F_ZN excess (level exposure).
* CHOICE (fixed here): the eligible variant with the highest selection-window net 1x Sharpe. Nothing
  else enters the choice; validation and later windows are never used to choose.
* ADOPTION (fixed here): the chosen variant is worth adding only if (a) validation net 1x Sharpe > 0,
  (b) validation net 2x Sharpe > 0 and (c) core_ER_6 + chosen has a higher validation net 1x Sharpe
  than core_ER_6 alone. Selection-window NW t >= 2 is reported as a separate flag.

## 6. Event study (descriptive, no gating, unit notional)

Per maturity (2y ZT, 3y ZT, 5y ZF, 7y ZN, 10y ZN, 20y ZB, 30y UB) and for F_ES around 2-year
auctions: daily excess returns on event days k = -10..+10 (bp), auctions grouped by date into
2010-06..2013-12, 2014-01..2024-10-02 (A+10 inside) and the later window 2024-10-03..2026-10-02
(descriptive). Reported: mean daily return per k with i.i.d. t across auctions; mean cumulative return
from A-10 through k with its t; the paper's spread D_t = sum(A+1..A+t) - sum(A-t+1..A) for t = 5 and 10
with a Newey-West t (5 lags) over the date-ordered auctions; the unconditional mean daily return of the
instrument in the same period for reference.

## 7. Portfolio test (pre-declared)

core_ER_6 + the CHOSEN variant at equal risk, built with the combine study's own `build()` (ER
weights 1/4, 6 % target from the trailing 252-day covariance of sleeve net 1x returns, month-end
decisions applied from d+2, min 126 obs, leverage cap 4 on summed instrument gross, overlay cost on
multiplier changes at the sleeve's gross-weighted average one-way cost). The new sleeve enters with
its net_1x / net_2x / gross columns, its daily held gross, and its average cost. core_ER_6 alone is
rebuilt with the same function and checked against the saved PORT_core_ER_6 series. Reported for both
on selection, validation, full in-sample and later windows (common start): net 1x and 2x Sharpe, vol,
max drawdown (excess equity). The same test is also run for every other eligible variant and
reported as descriptive only.

## 8. Outputs

`auction/futures_test/` (scripts, tables, event study, summary.json) and `auction/series/<id>.parquet`
(columns net_1x, net_2x, gross = daily excess returns; json sidecar). Nothing in the repository is
modified; no OOS unlock; no engine.run_backtest / log_trial; nothing written to results/.
