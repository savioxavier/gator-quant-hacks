# Fed communication v2: deviations and readings logged before any return

Pre-registration: `D:/AUTOMATION/gqh-systematic/research/fedspeak_v2/HYPOTHESIS_v2.md`
(current sha256 464f8a5bad37e6466ccde42e8941fa1836323600324792d4d53dcc0c50eb8a2e, with Amendments 1-3 and the
clarification to Amendment 2).

Both entries below were written on Sat 2026-10-03 at about 22:40 UTC. At that time:
- no v2 return had been computed on real stance scores in any window (selection, validation or out-of-sample);
- the walk-forward chrono stance model (Amendment 2/3) was still training, so no real stance score existed.

The only v2 returns computed so far are placebo runs on random scores (`backtest/smoke_placebo/` and the placebo
chain test), which carry no information.

The stance-model substitution itself is not listed here: Amendment 2 (with its clarification) and Amendment 3
register it.

## D-1 (2026-10-03, about 22:40 UTC): unscheduled dates in the FOMC de-risk list

**What was registered.** "FOMC de-risk as in Variant A". The backtest uses Variant A's style of date list:
strategy 01's list before 2015 and `corpus/fomc_dates_variantA_style.csv` from 2015.

**What the list contains.** From 2015 it has 101 dates: the 93 scheduled meeting dates (`corpus/fomc_dates.csv`)
plus 8 unscheduled announcement dates:

| Date | Event |
|---|---|
| 2019-10-11 | statement after the October 4 unscheduled meeting |
| 2020-03-03 | statement after the March 2 unscheduled meeting |
| 2020-03-15 | March 15 unscheduled meeting (a Sunday) |
| 2020-03-19 | notation vote |
| 2020-03-23 | notation vote |
| 2020-03-31 | notation vote |
| 2020-08-27 | notation vote |
| 2025-08-22 | notation vote |

Sources: `verify/date_checks.json` (key `derisk_dates_not_scheduled_meetings`) and the federalreserve.gov calendar
headings in `corpus/fomc_events_all.csv`.

**Decision.** The list is kept exactly as registered and as already used in every check. Selection, the decision
rule, the out-of-sample evaluation, the portfolio test and the per-chair table all use the 101-date list.

**Added report (a sensitivity, never used for selection or the decision rule).** The chosen combination is
re-simulated with a scheduled-only de-risk list: strategy 01's list before 2015 plus the 93 scheduled dates. That
removes the de-risk on the 8 dates above. Reported:
- in-sample, for the selection, validation and full in-sample windows;
- out-of-sample only if the decision rule passed, and only after `oos_chosen.json` has been written.

## D-2 (2026-10-03, about 22:40 UTC): how T3 is scaled

**What was registered.**
- T3 is "T2 orthogonalised to rate momentum": each day, the residual of the consensus on the 20-session-half-life
  change in DGS2, lagged two days, from an expanding regression (point in time).
- The registration does not say how the residual is scaled before it enters Variant A's sizing (clip at 2,
  10% vol target).

**Reading used.** It is fixed in `backtest/v2lib.py` and described in `backtest/README.md`, items 3 and 5.
- **Momentum.** M_t = sum over k of lam^k x dDGS2[t-2-k], with lam = 2^(-1/20) and DGS2 forward-filled over
  sessions without a print.
  - This equals DGS2 minus its 20-session-half-life EWMA, up to the constant factor lam.
  - Rescaling M by a constant changes only the slope. The residual, and therefore T3, are unchanged.
- **Regression.** On each day t, C_T2 is regressed on [1, M] by OLS over the sessions from 2015-01-02 to t,
  using only data known at t.
- **Scaling.** The residual on t is divided by the sd (ddof 1) of that same fit's residuals. Their mean is 0
  because of the intercept.
  - This is Variant A's expanding z, applied point in time to the residual.
  - It needs at least 252 observations, on the same z clock as T1, T2 and T4.
  - It is not standardised a second time.
  - The result goes into the same clip at 2 and the same sizing as the other signals.
- **Checks.** The expanding OLS matches statsmodels to 2e-15 on three dates (`backtest/check/check.json`), and the
  T3 series is prefix-invariant (causal).

**Other readings, not run.** Neither of these is computed or reported:
- an expanding z of the raw residual series;
- the unscaled residual.
