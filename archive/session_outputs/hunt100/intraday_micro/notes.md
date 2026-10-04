# intraday_micro: research notes (2026-10-03)

Scope: intraday and short-horizon futures/ETF rules that our hourly ES/ZN bars (and daily futures) can test.
Candidate list: candidates.json (built by build_candidates.py; 25 candidates, 24 implementable). Sources: urls.txt.
Nothing was backtested here; SPEC.md files must be written per strategy before any computation.

## Common implementation conventions (referenced by the rules)
- C1 time: glbx_ohlcv1h_v01_es_zn.parquet ts_event is the UTC bar START. Convert to America/New_York.
  P(H:00) = close of the bar that starts at (H-1):00 ET. ES session close = P(16:00) (CME equity settlement 15:00 CT);
  ZN session close = P(15:00) (CBOT settlement 14:00 CT). Coverage checked: about 4,200 sessions 2010-06-07 .. 2026-10-02,
  all 23 hourly slots present for ES.v.0 and ZN.v.0 (17:00 ET maintenance hour mostly empty).
- C2 contracts: hold the instrument_id that is .v.0 at entry; take the exit price from whichever of .v.0/.v.1 carries
  that id (.v.1 is in the file). Window return = P_exit/P_entry - 1 = excess return.
- C3 execution: a rule never trades at the price that defines its signal unless a realistic order type exists
  (16:00 ES settlement via TAS/MOC). Event calendars must be known before entry (FOMC schedule csv, Treasury
  announcemt_date, BLS/BEA schedules published in advance).
- C4 costs: per side per unit notional: ES 1 bp intraday and daily; ZN 1.5 bp intraday, 1 bp daily; other roots per the
  task table; report 2x as stress. Intraday rules pay a round trip every active session.
- C5 sizing: unit raw position, then L_d = min(5, 0.10/sigma_hat_{d-1}), sigma_hat = sqrt(252*EWMA(com 60) of raw daily
  strategy return^2) using data through d-1. Sparse event rules: L = min(5, 0.10/(sigma_active*sqrt(f))) as in the edges
  calendar study (f = share of active days in the trailing 252).
- C6 booking: a window's return is booked on the session date of its exit mark (overnight windows on the next session).

## Cost reality check (most important finding)
Published intraday edges are gross or use ETF costs of a few hundredths of a bp. Our 1 bp/side ES (1.5 bp ZN) is large
relative to them:
- Gao first-half-hour timing: 6.67%/yr on 252 days = 2.6 bp/day gross vs 2 bp round trip.
- Baltussen ROD equity futures: 6.86%/yr = 2.7 bp/day gross vs 2 bp; bond futures 2.16%/yr = 0.9 bp/day vs 3 bp (ZN).
- Overnight drift 02:00-03:00: authors' own net Sharpe -0.5 after bid-ask; 01:30-03:30 net 0.3.
- Close-to-open ES: about 2.6%/yr gross vs about 5%/yr cost at one round trip per day.
- Beat the Market: paper cost about 0.1-0.2 bp/side; replications show the edge compressing since 2024-2025.
So filters that cut the number of traded days (thresholds, sell-off conditioning, GEX, event days) are the realistic path.
Daily event rules (macro announcement premium, auction cycle, FOMC windows, OpEx week) pay costs only on event days.

## Data notes
- SqueezeMetrics GEX/DIX daily history downloaded free to squeeze_DIX.csv (2011-05-02 .. 2026-10-02). It is a vendor
  model estimate; history may have been recomputed, so treat as not certified point-in-time; use the value dated d-1.
- FOMC schedule: reuse edges/calendar/fomc_scheduled.csv. Statement times: 14:15 ET to 2012, 12:30 ET for press-conference
  meetings Apr 2011 - Dec 2012, 14:00 ET from 2013.
- Treasury auctions: treasury_auctions.parquet has auction_date and announcemt_date (point-in-time start of pre-auction
  windows). Coupon auction results 13:00 ET.
- Release dates (NFP, CPI, PPI, GDP): BLS schedule archives or ALFRED first-vintage dates (free download, no key).
  ISM manufacturing: first business day, 10:00 ET.
- GSCI roll: needs contract-month mapping via the free databento symbology.resolve call; only .v.0/.v.1 closes exist.
- Minute data would be needed for: faithful last-half-hour windows, 09:30 open anchors, 5-minute ORB, 1-minute VWAP,
  30-minute noise-area checks. Commodity/FX intraday momentum needs intraday bars for other roots (not available).

## Overlaps and reuse
- No identical verified series exists in edges/series (CAL_* are daily turn-of-month, pre-holiday, FOMC even-week and
  Treasury month-end rules); macro announcement and FOMC-window rules are related but different.
- intraday_micro_eu_open_window_es and intraday_micro_overnight_drift_selloff_es V1 overlap heavily (02:00-03:00 is inside
  00:00-04:00). intraday_micro_letf_close_es is a filtered relative of intraday_micro_imom_rod_es.
- intraday_micro_hour_periodicity V1 will likely rediscover the EU-open window; useful as a data-driven check.

## Not found / gaps
- No robust published lunchtime or afternoon index return premium (only volatility/volume U-shapes); the closest documented
  pattern is the negative US-open window (Bondarenko-Muravyev), included as a variant.
- Pre-announcement drift before macro releases (Kurov et al.) needs minute data and the surprise sign; not included.
- The FOMC-day reversal source could not be opened (403); evidence score 1.
- Web search budget for this session ran out late in the hunt; GitHub API searches were used for replications.
