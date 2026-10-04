# Hourly ES / ZN panel

Shared hourly panel for the intraday study. Built only from the cached Databento GLBX.MDP3 `ohlcv-1h` file
(`GQH_DATA_DIR/databento_raw/glbx_ohlcv1h_v01_es_zn.parquet`). The build makes no API calls and buys no new data.

```
cd /d/AUTOMATION/gqh-systematic && GQH_DATA_DIR=<home>/.cache/gqh PYTHONIOENCODING=utf-8 \
  <home>/.venvs/gqh-systematic/Scripts/python.exe <this folder>/build_hourly_panel.py
```

| file | content |
|---|---|
| `hourly_panel.parquet` | the panel: ES and ZN stacked in long format, 193,708 rows (ES 97,300, ZN 96,408) |
| `nyse_calendar_offsets.parquet` | NYSE trading days (SPY dates in `etf_daily`) with `month_T`, `me_off_own`, `me_off_prev`. Use it to label any other date column, e.g. `ret_date_1600` |
| `validation_daily.parquet` | per NYSE day: compounded hourly returns next to the daily reference returns |
| `validation_summary.csv` | correlation, mean absolute difference, share of days with \|diff\| > 5 bp, per comparison and sample |
| `validation_residuals.csv` | every like-for-like day with \|diff\| > 5 bp, with its cause |
| `nonroutine_gaps.csv` | the 18 gaps that are not a weekend, daily break, holiday or early close |
| `build_log.txt` | counts from the last run |

## Grain and source

- One row per front-contract (`.v.0`) hourly bar that had at least one trade. Databento writes no bar for an hour
  without trades, and the panel does not forward-fill. Coverage is bar starts 2010-06-06 20:00 ET to
  2026-10-02 16:00 ET.
- `.v.0` / `.v.1` are Databento's volume-ranked continuous symbols (front and second contract). The `.v.0` mapping
  changes at 00:00 UTC (19:00 ET in winter, 20:00 ET in summer) inside the evening session. When the change falls
  on a weekend date it happens at the Sunday 18:00 ET reopen. There are 66 ES rolls and 65 ZN rolls.
- `ts_event` is the bar START. The bar starting 15:00 ET covers [15:00, 16:00) and its `close` is the last trade
  before 16:00 ET.

## Columns

| column | meaning |
|---|---|
| `root` | `ES` or `ZN` |
| `bar_start_utc`, `bar_end_utc` | bar start / end (end = start + 1 h), tz-aware UTC |
| `bar_start_et`, `bar_end_et` | the same in America/New_York (DST-aware) |
| `date_et`, `hour_et`, `dow_et` | ET calendar date, hour (0-23) and weekday (Mon=0) of the bar START |
| `trade_date` | CME session date on the NYSE calendar. A bar starting at or after the 18:00 ET reopen goes to the next NYSE day. Any other bar goes to the first NYSE day on or after its ET date, so the morning sessions CME runs on NYSE holidays roll forward. The 16:00 and 17:00 ET bars stay on the same day |
| `ret_date_1600` | NYSE day d whose 16:00-to-16:00 ET return contains the bar: bar END in (16:00 ET of the previous NYSE day, 16:00 ET of d]. The 16:00-17:00 bar therefore goes to the NEXT day. NaT only for the last bar (2026-10-02 16:00 ET start) |
| `cme_non_nyse_session` | bar (before 18:00 ET) on a weekday the NYSE was closed: holiday morning sessions, Good Friday payroll sessions (ES 1,301 bars, ZN 1,327) |
| `new_session` | first bar of a new `trade_date` |
| `month_T` | last NYSE trading day of `trade_date`'s month |
| `me_off_own` | trading-day offset to own month end: 0 on T, -k on T-k (from `src/calendar_utils.month_offsets`). NaN for October 2026, an incomplete month |
| `me_off_prev` | k on T+k: the k-th trading day of the month, counted from the previous month's T |
| `in_sample` | `trade_date <= 2024-10-02`. For 16:00-to-16:00 work use `ret_date_1600 <= 2024-10-02` instead (the 2024-10-02 16:00-17:00 bar is in-sample by trade date but belongs to the 2024-10-03 return day) |
| `instrument_id` | front contract's Databento instrument id |
| `open`, `high`, `low`, `close`, `volume` | front-contract bar OHLC (index points for ES, price points for ZN) and contracts traded |
| `instrument_id_v1`, `close_v1`, `volume_v1` | second contract at the same timestamp (NA if it did not trade that hour) |
| `prev_bar_start_utc` | start of the previous front bar (the reference bar for the return) |
| `prev_close_same_id` | close of THIS bar's contract at `prev_bar_start_utc`: the `.v.0` close when the contract is unchanged, the `.v.1` close at a roll, NaN otherwise |
| `prev_close_source` | `v0`, `v1` (roll bars: all 131) or `none` (only the first bar of each root) |
| `ret_simple`, `ret_log` | within-contract return `close / prev_close_same_id - 1` and its log. It runs from the previous available bar, so after a gap it spans the whole gap |
| `hours_since_prev` | hours between this bar's start and the previous front bar's start |
| `is_gap` | `hours_since_prev > 1` |
| `gap_type` | `none`, `daily_break` (17:00-18:00 ET CME break), `weekend`, `holiday_closure`, `early_close_reopen` (session halted early, normal 18:00 reopen), `other_missing` (vendor hole or outage, see below), `first_bar` |
| `is_roll` | the front `instrument_id` differs from the previous front bar's |

## Conventions and rules

- Returns never cross a roll. Never difference or divide `close` across rows: compound `ret_simple` (or sum
  `ret_log`). The futures return is already an excess return. Add the T-bill (`rf_daily`) only for a
  total-return series.
- Point in time: information available at a bar's `bar_end` can only earn the return of a LATER bar. Shift the signal
  by at least one row within a root, i.e. earn from the bar whose `bar_start` equals the signal's time onward.
- Daily 16:00 ET close-to-close return of day d: `prod(1 + ret_simple) - 1` over bars with `ret_date_1600 == d`.
  This reproduces ES16/ZN16 (see Validation). ZN16 is also sampled at 16:00 ET, one hour after the ZN settlement
  window (about 15:00 ET).
- To reproduce `futures_daily` (F_ES, F_ZN): group by the first NYSE day on or after the bar's UTC start date.
- The data has no 30-minute boundaries. Gao et al.'s first half-hour return (previous 16:00 close to 10:00) is exact:
  bars with `ret_date_1600 == d` and `bar_end_et <= 10:00`. The last half-hour (15:30-16:00) is NOT available: the
  closest proxy is the 15:00-16:00 bar. Likewise Baltussen et al.'s rest-of-day return (to 15:30) becomes previous
  close to 15:00. The 09:00-10:00 bar straddles the 09:30 cash open, so the overnight-versus-intraday split must use
  09:00 or 10:00. Label all of these as hourly approximations.
- DST: every US clock change falls inside the weekend closure (Sunday 02:00), so no ET hour is duplicated or missing
  in the data. ET hours shift by one hour against UTC across the change, which the ET columns handle.
- A normal trade date has 23 bars (18:00 ET to the 16:00-17:00 bar). Until late 2015, ES (and ZN in 2010-11) also traded
  into the 17:00 ET hour, so the 17:00 to 18:00 step is not flagged as a gap. Use `new_session` for session
  boundaries, not `is_gap`.

## Gaps

| gap_type | ES | ZN |
|---|---|---|
| none | 94,197 | 92,382 |
| daily_break | 2,129 | 3,057 |
| weekend | 817 | 817 |
| early_close_reopen | 99 | 90 |
| holiday_closure | 49 | 51 |
| other_missing | 8 | 10 |
| first_bar | 1 | 1 |

`other_missing` (`nonroutine_gaps.csv`) contains:
- Vendor holes that are also missing from the daily `ohlcv-1d` file:
  - ES 2014-06-11 17:00 to 2014-06-15 18:00 ET (no bars on 06-12 or 06-13)
  - ES 2014-09-22 17:00 to 2014-09-26 07:00 ET
  - ES 2014-12-30 17:00 to 2015-01-01 18:00 ET (no bars on 12-31)
  - ZN 2014-09-22 16:00 to 2014-09-23 07:00 ET
  - ZN 2014-10-02 17:00 to 2014-10-05 18:00 ET (no bars on Friday 10-03, a payroll day)
  - ZN 2020-02-26/28 (several hours missing in each of four places)
  - ZN 2020-06-30 10:00 to 20:00 ET
- The CME Globex outage of 2025-11-27 21:00 to 2025-11-28 08:00 ET.
- Short holes inside a session: a late evening reopen on 2015-06-30 (the leap-second night) and on 2020-06-30 (ES),
  missing evening hours on 2019-02-26 (both roots), and a 16:00 ET bar after the 13:15 early close on 2012-07-03 (ES).

The return on the bar after any of these gaps spans the whole gap. Exclude those bars, or treat them as multi-hour
returns, in any test keyed to a time of day.

## Validation

Compounded hourly returns against the daily references, per NYSE day. Reference excess return = `pct_change` of the
level minus `rf_daily`. Sample: 2010-06-08 to 2026-10-02. The first panel day is dropped.

| comparison | root | days | corr | MAD (bp) | share \|diff\| > 5 bp | max \|diff\| (bp) |
|---|---|---|---|---|---|---|
| hourly 16:00->16:00 vs ES16 / ZN16 | ES | 4,103 | 0.99999 | 0.032 | 0.15% (6 days) | 16.4 |
| | ZN | 4,106 | 0.99996 | 0.024 | 0.05% (2 days) | 10.0 |
| hourly 16:00->16:00 vs F_ES / F_ZN | ES | 4,103 | 0.938 | 20.8 | 78.1% | 754 |
| | ZN | 4,106 | 0.959 | 6.4 | 45.8% | 115 |
| hourly 00:00 UTC->00:00 UTC vs F_ES / F_ZN | ES | 4,100 | 0.999999 | 0.014 | 0 | 3.8 |
| | ZN | 4,105 | 0.999996 | 0.005 | 0 | 2.4 |
| ES16 / ZN16 vs F_ES / F_ZN (the references against each other) | ES | 4,103 | 0.938 | 20.8 | 78.0% | 754 |
| | ZN | 4,106 | 0.959 | 6.4 | 45.8% | 115 |

The in-sample and later windows behave the same way. The 16:00 match in the later window has MAD 0.008 bp (ES) and
0.020 bp (ZN), with 0 days above 5 bp. The median absolute difference is 0.000 bp in both like-for-like comparisons.

Residual differences:
- **F_ES / F_ZN are not settlement-based.** Databento `ohlcv-1d` bars are UTC days: their volume equals the sum of
  the hourly volumes for 100% of the sampled days. So the daily close is the last trade before 00:00 UTC, which is
  19:00 ET in winter and 20:00 ET in summer and falls inside the next evening session. The 16:00 vs F_ gap is
  therefore a 3-4 hour window mismatch, not a data error. ES16 vs F_ shows the same numbers. Compounded on the
  matching UTC-midnight window, the hourly panel reproduces F_ to machine precision on every non-roll day
  (max 2e-11 bp).
- **Roll days.** ES16 and ZN16 switch to the new contract for the whole 16:00-to-16:00 day, while the hourly chain
  and F_ switch at 00:00 UTC. The difference is the change in the calendar spread between 16:00 ET and 19:00/20:00 ET
  the evening before. The two ES days above 5 bp are rolls: 2012-09-17 (-5.0 bp) and 2020-03-18 (-9.4 bp). Excluding
  roll days, the like-for-like UTC match is exact.
- **Vendor holes.** In the 2014 holes the hourly 16:00-17:00 bars of the last day before the hole fall on the next
  NYSE day, while the reference books the entire move on the first day after the hole. Those days come in
  offsetting pairs:
  - ES 2014-09-23/26 and 2014-12-31/2015-01-02
  - ZN 2014-10-03/06
  The cumulative difference over a 7-day window around each pair is 0.0 bp. NYSE days with no hourly bar at all
  (comp NaN, reference 0):
  - ES 2014-06-13, 09-24 and 09-25 on the 16:00 window
  - ES 2014-06-12/13, 09-23/24/25 and 12-31 on the UTC window
  - ZN 2014-10-03 on the UTC window
- **NaN returns.** Each root has exactly one, its first bar. Every roll bar found the new contract in `.v.1` at the
  previous timestamp.
- **Total drift over 16.3 years** (sum of daily log returns, hourly minus reference): ES16 -3.4 bp, ZN16 +6.7 bp,
  F_ES +14.1 bp and F_ZN -2.4 bp (UTC window), all from roll days.

## Known limitations

- Hourly resolution only: no 09:30 or 15:30 boundary, and no settlement prices. The 15:00-16:00 ES bar's close is
  a last trade, not the CME settlement VWAP.
- The sessions after Christmas and New Year from 2011-12 to 2014-01 start at 06:00 ET in the data (12 bars), for both roots. It is
  unclear whether that reflects the CME schedule or the vendor. They are labelled `holiday_closure`.
- `volume` counts contracts in the front month only. The `.v.1` volume is given separately.
