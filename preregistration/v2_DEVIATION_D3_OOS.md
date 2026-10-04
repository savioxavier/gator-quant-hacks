# v2 deviation D-3: out-of-sample evaluated once for reporting, although the decision rule failed

Written 2026-10-04 at about 01:15 UTC, after the v2 in-sample results and before any out-of-sample (2024-10-03 ..
2026-10-02) return of v2 or of its portfolio test has been computed or viewed.

## Why

HYPOTHESIS_v2.md (sha256 464f8a5b...) evaluates the out-of-sample window only if the chosen combination passes the
decision rule. T4xE1 passed the validation gate (net Sharpe 0.687 > 0) but failed the 2x-cost gate (full in-sample
net Sharpe at 2x costs 0.387 < 0.5), so the out-of-sample window was not evaluated
(`backtests/results/v2/oos_not_evaluated.json`).

The Gator Quant Hacks Systematic Trading rules require in-sample and out-of-sample results, reported separately and
net of costs (and at 2x costs), for the strategy a team submits. At the team's request, v2 is presented with full
results.

## What changes

- The out-of-sample window 2024-10-03 .. 2026-10-02 is evaluated ONCE, with the frozen code, signals, parameters,
  costs and data rules of HYPOTHESIS_v2.md (Amendments 1-3) and DEVIATIONS.md (D-1, D-2), for:
  - the chosen combination T4xE1 (and Variant A as the pre-declared reference), at 1x and 2x costs;
  - the pre-declared portfolio test (T4xE1 added to core_ER_6 as a fourth sleeve at equal risk, same 6% overlay and
    trailing covariance).
- Reported metrics in every window: annualised return, volatility, Sharpe (net 1x, net 2x, gross), maximum drawdown,
  turnover, and the equity curve.

## What does not change

- The decision rule failed, and that verdict stands. v2 is reported as a strategy that failed its own pre-registered
  2x-cost gate. The out-of-sample result cannot reverse that verdict, whatever it shows.
- No combination is re-chosen and no parameter changes after the out-of-sample result is seen. It is reported
  whatever it shows.
- The in-sample results and the Deflated Sharpe (11 trials) are unchanged.

## Press-conference results shown as a strategy

The press-conference trades (BENCH-R, H1-primary and, once run, the exploratory H4) are also shown as
strategy-level series: the frozen positions and per-trade P&L, net of measured spreads and fees (and at 2x),
summarised as annualised return, volatility, Sharpe, maximum drawdown and turnover, split at 2024-10-03 into
in-sample and out-of-sample as the competition defines them. This is a presentation of results already fixed by
their own pre-registrations (ADDENDUM, note 1, note 2). No position, sample or rule changes. G3 stays NO-GO.
