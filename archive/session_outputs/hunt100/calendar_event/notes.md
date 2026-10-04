# calendar_event: search notes (2026-10-03)

Candidate list with exact rules: `candidates.json` (28 candidates, 27 implementable). Sources: `urls.txt`.
Papers read in full text are cached as PDF/TXT in `papers/` (Etula et al., Hartley-Schwarz, Ko-Yang,
Savor-Wilson 2013, Mueller-Tahbaz-Salehi-Vedolin, Lou-Yan-Zhang, Boyarchenko-Larsen-Whelan,
Baltussen-Da-Lammers-Martens, Melvin-Prins, Knox-Vissing-Jorgensen 2026 survey).
No backtest was computed here. SPEC.md must be written per candidate before any computation.

## Common conventions used in the rules
- T = last NYSE session of month (planned calendar, edges/calendar/calcommon.py). Return day t = close t-1 to close t.
  "Hold over return days [s,e]" = enter close s-1, exit close e.
- Calendar-known rules: engine exec=next_close with the decision dated two sessions before the first return day
  (same as the edge-search calendar study). Data-dependent signals use information through the decision close only.
- Sizing where no natural sizing: L = min(5, 0.10/(sigma*sqrt(f))), sigma = sqrt(252*EWMA_com60(r^2)) of the
  instrument's daily excess returns, f = trailing-252-session share of days inside the rule's windows.
- Intraday rules use databento hourly ES/ZN (.v.0, UTC bar start, 2010-06..2026-10) converted to America/New_York,
  simulated outside engine.simulate with per-side costs (ES 1 bp, ZN 1.5 bp) and booked to the daily series.
- FOMC dates: edges/calendar/fomc_scheduled.csv (scheduled only). Statement times: 14:15 ET before 2013,
  14:00 ET after; 2011-04..2012-12 press-conference meetings released at 12:30 ET (rules adjust the hourly window).
- Macro release dates: BLS archive pages (empsit, cpi, ppi), free.

## Overlap with the parallel edge search (not yet verifier-confirmed)
- calendar_event_tom_es base == edges CAL_TOM_ES; calendar_event_fomc_cycle_even_weeks == CAL_FOMC_EVEN_ES;
  tsy_month_end_curve V1 == CAL_TSY_ME_ZN; preholiday_rty V1 == CAL_PREHOL_ES. Reuse those series once verified.
- rebalancing_flow_es_zn is related to (not identical with) the F1/F2 month-end rebalancing sleeve.

## Evidence quality summary (post-publication / out-of-sample)
- Strongest long-history OOS: Halloween (Andrade et al. 2013 OOS 1998-2012; Jacobsen-Zhang 300+ years), but
  Dichtl-Drobetz find no net benefit recently. Only ~14 winters in our IS window.
- Documented post-publication decay or reversal: pre-FOMC drift (gone after 2015 per Kurov et al.; ~20 bp
  overnight-before persists 2011-2023 per Knox & Vissing-Jorgensen), FOMC cycle (opposite cycle 2017-2021),
  pre-holiday (only small caps after 1990, Ko-Yang CFR replication), Goldman roll (negative roll-period
  impact 2004-2010), TOM (weaker after ~1990-2001 in futures), OpEx week (practitioner: weak last 4 years),
  commodity seasonality (arXiv 2026 OOS 2016-2024 null).
- Mechanism-based with natural experiments: dash for cash (settlement-cycle shifts 2017 T+2, 2024 T+1 give
  genuine OOS tests), Treasury month-end (index extension), rebalancing flows (HMM 2025 with independent
  replication), auction cycle (LYZ; Sigaux mechanism evidence), intraday momentum (gamma hedging; 60 futures).
- Cost-dominated: overnight drift (BLW: net Sharpe -0.5 unconditional, 0.3 for 01:30-03:30), intraday
  momentum (net positive only at one-tick cost), FX month-end hedge (effect lives in one hour).

## Considered and not listed (reason)
- Single-commodity practitioner seasonals (natural gas winter, RBOB spring, lean hogs spring/July): spot-price
  seasonals that futures curves already price; continuous-chart "evidence" mixes roll gaps; no peer-reviewed
  futures-return evidence found. Covered by the same-month seasonality candidates (time-series variant).
- Weekend/Monday effect: disappeared or reversed in large caps after 1987 (multiple studies).
- Presidential cycle, Santa Claus rally: too few events, overlaps TOM/pre-holiday/turn-of-year.
- TIPS index-ratio seasonality: no clean return evidence found.
- Price drift before macro news (Kurov et al. 2019): needs the sign of the surprise, not tradable ex ante.

## Process notes
- WebSearch session budget (200 calls, shared) ran out near the end; the Mou (2011) roll-strategy timing could not
  be confirmed and is flagged in that candidate.
- GitHub repository search (unauthenticated API) found only small replication repos (4 pre-FOMC, 1 dash-for-cash)
  with no performance evidence. Kaggle not useful for this family (no curated event-date datasets beyond public sources).
