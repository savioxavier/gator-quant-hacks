# Calendar effects on CME futures: pre-declared specification

Written on 2026-10-03, before any backtest or return statistic of the rules below was computed in
this study. Everything here is fixed. Every declared variant is run and reported (CSV table),
including the ones that look bad. The headline for each candidate is its declared base case, never
the best variant. The median across a candidate's variants is reported as well.

## 0. Common definitions (all candidates)

* **Instruments.** `ES16` and `ZN16` from `futures_1600.parquet`: the volume-ranked front CME
  contract, returns computed within one contract, last trade before 16:00 ET (aligned with the NYSE
  close), on the NYSE session calendar, a fully collateralised total-return index (futures excess
  return plus the T-bill). Daily excess return `r_t = close_t / close_{t-1} - 1 - rf_t`.
  Timing robustness only: the same base rule on `F_ES` / `F_ZN` (`futures_daily.parquet`, whose
  close is the last trade of the UTC day, about 19:00-20:00 ET).
* **Calendar.** NYSE sessions (SPY dates). `T` = last session of a month, `T-j` = j-th session
  before it, `T+j` = j-th session of the next month. Offsets are counted on the planned calendar
  (realised sessions plus the unscheduled closures 2012-10-29/30, 2018-12-05, 2025-01-09; the
  repository's `calendar_utils.planned_calendar`) and mapped back to real sessions with
  `planned_to_realized` (a trade planned on a closure is filled at the next real close).
* **Timing.** "Return day t" is close(t-1) -> close(t). A rule that holds over return days
  [s, e] enters at the close of s-1 and exits at the close of e. The engine runs with
  `exec="next_close"`: the weight held over return day t is the decision taken at the close of t-2.
  All window sizes use information up to the close of s-2 (two sessions before the first return
  day). The calendars used (month ends, scheduled holidays, the scheduled FOMC calendar) are public
  long before the trade.
* **Sizing (10 % ex-ante annualised volatility, trailing data only).**
  `L = min(5, 0.10 / (sigma_hat * sqrt(f_hat)))` while inside a window, 0 otherwise, held constant
  over a window.
  * `sigma_hat` = `sqrt(252 * EWMA(r^2))`, EWMA centre of mass 60 sessions (at least 60
    observations), of the instrument's daily excess returns through the decision date (the
    estimator of forward test 2's S1).
  * `f_hat` = share of the trailing 252 NYSE sessions (calendar from 2005) that fall inside the
    rule's windows, at the decision date. The calendar is known in advance, so this uses no
    future information.
  * The book's ex-ante volatility is then `sigma_hat * sqrt(f_hat) * L = 10 %` (assumes a
    window day is as volatile as an average day; the realised volatility is reported).
  * The gross cap of 5x notional/NAV is a margin-feasibility cap: ES initial margin is about
    5-7 % of notional.
  * Unscaled diagnostics use `L = 1` (one unit of notional per unit of NAV in the window).
* **Costs.** Realistic one-way cost per unit of notional traded: ES 0.75 bp, ZN 1.0 bp (centre of
  the stated realistic ranges ES 0.5-1, ZN 0.7-1.4). Stress = 2x (ES 1.5, ZN 2.0). Gross = 0.
  The engine also charges one extra round trip of any position held into a front-contract roll
  day. That is conservative, since a trader would simply enter the new contract.
* **Windows.** In-sample (IS) = first position (after the 60-session warm-up, about 2010-09) to
  2024-10-02. Later = 2024-10-03 to 2026-10-02 (already seen, descriptive only). Data loaded with
  period "FWD". Every signal is causal, so the IS slice is identical to a run with period "IS"
  (checked by assertion for one candidate).
* **Statistics** (net 1x, net 2x, gross).
  * Sharpe of daily excess returns x sqrt(252), annual return, volatility, max drawdown.
  * Worst calendar year, share of positive calendar years (years with at least 126 sessions).
  * Rolling 504-session Sharpe 10th/50th/90th percentiles (IS).
  * Turnover per year.
  * Correlation of daily returns with ES16 excess, with S1 (forward2) and with F2 (forward), plus
    weekly correlations.
  * Newey-West t of the mean (engine default lags).
  * HAC alpha and beta versus ES16 excess.
  * Low-exposure extras: share of days invested, mean excess return per invested day versus the
    buy-and-hold mean per day, and the timed strategy's Sharpe versus buy-and-hold of the same
    asset over the same window (a constant exposure f has the same Sharpe as buy-and-hold).
  * Paired stationary block bootstrap (mean block 21 sessions, 2,000 draws) of the Sharpe
    difference, timed minus buy-and-hold.
* **Output series.** `edges/series/<name>.parquet` (columns net_1x, net_2x, gross; daily excess
  over T-bill; FWD range), with a sidecar json.

## 1. CAL_TOM_ES: turn of the month in US equities

* **Literature.**
  * Ariel (1987, JFE): CRSP indices, 1963-1981.
  * Lakonishok & Smidt (1988, RFS, "Are seasonal anomalies real? A ninety-year perspective"):
    DJIA 1897-1986. Turn of the month = the last trading day plus the first three trading days.
  * McConnell & Xu (2008, FAJ, "Equity returns at the turn of the month"): CRSP 1926-2005 and 35
    countries. The whole market excess return accrues over days -1..+3, and the effect persisted
    after Lakonishok & Smidt's sample.
  * Expected decay (literature review): reported gone in the US after about 2001 (Han, Han &
    Tian 2025) and concentrated on the first day in the ETF era.
* **Base (declared first).** Long ES16 from the close of T-2 to the close of T+3: return days
  T-1..T+3 (5 sessions a month).
* **V1.** From the close of T-1 to the close of T+3: return days T..T+3. This is the exact
  Lakonishok-Smidt / McConnell-Xu definition (4 sessions).
* **V2.** From the close of T-1 to the close of T+4: return days T..T+4 (5 sessions).
* **Long-history evidence** (gross, unscaled, `L = 1`, not traded). Same three windows on:
  * Fama-French `Mkt_RF` (CRSP value-weighted market excess return, 1963-07..2026-08), split into
    1963-07..1987-12 (before Lakonishok-Smidt), 1988-01..2007-12 (after it, before
    McConnell-Xu), 2008-01..2024-10-02 (after McConnell-Xu) and 2024-10-03..2026-08-31 (later);
  * `^GSPC` (price index, 2003-01..), split into 2003-2007, 2008-01..2024-10-02 and later.

  Reported per split:
  * mean daily excess inside and outside the window, with the difference and its NW t;
  * timed Sharpe versus buy-and-hold Sharpe;
  * share of the total excess return earned inside the window.

## 2. CAL_TSY_ME_ZN: Treasury month-end extension on ZN futures

* **Literature.**
  * Hartley & Schwarz (2019, "Predictable End-of-Month Treasury Returns", Treasury data
    1990-2018). Excess returns over the last 2-5 days of the month are significantly positive and
    approximately zero otherwise. A long position over the last few days has a Sharpe ratio of
    about 1, best over the final 2-3 days. The proposed driver is index rebalancing and
    window-dressing demand (insurers buy on index rebalancing dates).
  * This is sleeve C of the submission (HYPOTHESES.md section 1, window [T-2, T]).
* **Base.** Long ZN16 over return days T-2..T (enter at the close of T-3, exit at the close of T),
  with no issuance sizing.
* **V1.** Base multiplied by sleeve C's issuance factor q (`ifc_treasury.monthly_issuance`,
  cut-off T-4, clip 0.5-2.0). Mean q is about 1, so the ex-ante volatility is only approximately
  10 %.
* **V2.** Return days T-1..T (Hartley-Schwarz "final two days").
* **Comparator** (not a variant). The repository's ETF sleeve C on IEF (issuance-sized, and q = 1),
  at its 3 bp ETF cost, through the same engine. Its Sharpe is compared.
* **Publication split.** IS before / from 2019-01-01 (the Hartley-Schwarz sample ends in 2018).

## 3. CAL_PREHOL_ES: pre-holiday effect in equities

* **Literature.**
  * Ariel (1990, JF, "High stock returns before holidays: existence and evidence on possible
    causes"): CRSP indices 1963-1982. The mean pre-holiday return is many times that of an
    ordinary day.
  * Lakonishok & Smidt (1988): DJIA 1897-1986.
* **Holiday definition.** A scheduled NYSE full-day holiday is a weekday without a session that
  coincides with the observed date of a standard exchange holiday:
  * New Year; MLK Day from 1998; Washington's Birthday / Presidents Day; Good Friday; Memorial Day;
    Juneteenth from 2022; Independence Day; Labor Day; Thanksgiving; Christmas;
  * Election Day through 1968 and in 1972/1976/1980; Lincoln's Birthday;
  * fixed-date holidays move Saturday -> Friday and Sunday -> Monday.

  Weekdays without a session that match no standard holiday count as unscheduled (funerals,
  weather, 9/11, the 1968 Wednesday closures). They are printed and never traded. Early-close
  days are sessions.
* **Base.** Long ES16 over the return day H-1 (the last session before a scheduled holiday): enter
  at the close of H-2, exit at the close of H-1.
* **V1** (overlap diagnostic). Base minus pre-holiday days that also fall in the TOM base window
  (T-1..T+3).
* **Long-history evidence** (gross, unscaled).
  * FF `Mkt_RF`: 1963-07..1982-12 (Ariel's sample), 1983-01..1990-12 (before publication),
    1991-01..2024-10-02 (after publication) and later.
  * `^GSPC`: 2003..2024-10-02 and later.

## 4. CAL_FOMC_EVEN_ES: FOMC-cycle even weeks

* **Literature.**
  * Cieslak, Morse & Vissing-Jorgensen (2019, JF, "Stock Returns over the FOMC Cycle"; sample
    1994-2016). The equity excess return is earned in even weeks of FOMC cycle time.
  * Week 0 = days -1..3, week 2 = 9..13, week 4 = 19..23, week 6 = 29..33, where day 0 is the
    scheduled FOMC announcement day.
  * Knox & Vissing-Jorgensen (2026, FEDS 2026-023) report a significant opposite cycle in
    2017-2021. This candidate is expected to fail. It is tested only because it was pre-declared
    and the dates are free.
* **Dates.**
  * Scheduled FOMC meetings come from federalreserve.gov: `fomchistorical{YYYY}.htm` up to 2020
    and `fomccalendars.htm` for 2021-2026. Day 0 = the last day of the scheduled meeting (the
    statement day).
  * Unscheduled meetings and conference calls are excluded: they were not known in advance.
* **Cycle day.** k = sessions since the most recent scheduled announcement day (0 on that day).
  The session immediately before a scheduled announcement day has k = -1.
* **Base.** Long ES16 on return days with k in {-1..3, 9..13, 19..23, 29..33}, flat otherwise.
  No variants.
* **Splits.**
  * IS 2010-09..2016-12 (inside the CMVJ sample) and 2017-01..2024-10-02 (after it), plus later.
  * FF `Mkt_RF` 1994-2016 / 2017-2024-10-02 / later.

## 5. Variant count

| Candidate | Variants |
|---|---|
| TOM | 3 (base, V1, V2) |
| TSY | 3 (base, V1, V2) |
| PREHOL | 2 (base, V1) |
| FOMC | 1 |
| F_ES / F_ZN timing robustness of each base | 4 |

That is **13** futures variants in total. The long-history FF / ^GSPC tables are evidence on the
same rules (gross), not extra tradeable variants.

## 6. Verdict rule (declared before results)

* **real_edge** requires all of the following:
  * IS net-1x NW t >= 2;
  * IS net-2x Sharpe > 0;
  * for equity timing rules, an alpha versus ES16 with HAC t >= 2, or a bootstrap p < 0.10 that
    timed beats buy-and-hold;
  * the long-history in-window-minus-out-of-window difference keeps its sign after publication.
* **fails**: IS net-1x NW t < 1, or the post-publication long-history evidence is about zero or
  reversed.
* **weak_or_uncertain**: everything in between.
* The later window is descriptive: two years of a low-exposure rule cannot confirm or reject.
