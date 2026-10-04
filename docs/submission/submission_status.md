# Submission status

Gator Quant Hacks 2026, Systematic Trading track. Devpost is due Sunday 2026-10-04, 10:00 ET.

**Statuses:**
- `DONE`.
- `MISSING`.
- `WAITING FOR INPUT`.
- `LIMITATION DISCLOSED`.

## What is submitted

- **Main strategy:** v2 T4xE1 with both D-4 implementation fixes.
- **Supporting evidence:** core_ER_6 alone against core_ER_6 + v2.
- **Failed and exploratory research:** H1 (press conference) and H2-H4 (voice, face, combined).
- **Overall reading:** mixed to negative.
  - v2 failed its pre-registered in-sample rule, and that verdict stands.
  - The out-of-sample result was opened once (D-3) and is not significant.
  - The portfolio gain is not distinguishable from zero under a paired bootstrap.

## Status by item

| Item | Status | Where |
|---|---|---|
| Full report (hypothesis, data, method, results, risk, capacity, limitations) | DONE | `docs/report/REPORT.md` |
| Five-page quant note | not produced (team decision); the report is the write-up | - |
| Final PDF | WAITING FOR INPUT (the team compiles it) | compile command at the top of `docs/report/REPORT.md` |
| Devpost text: elevator pitch, story, built-with tags | DONE | `devpost_description.md` |
| Devpost submission itself | WAITING FOR INPUT (the team submits) | - |
| Drawdown with the starting NAV included | DONE | `results_2/metrics/` |
| Full v2 metrics table and equity figures | DONE | `results_2/metrics/v2_metrics.csv`, `equity_v2.png`, `equity_portfolio.png` |
| Transcript provenance | DONE; the source-equivalence assumption is LIMITATION DISCLOSED for 17 conferences | `docs/results/transcript-provenance.md` |
| Public saved-result replay | DONE (all 7 items pass) | `results_2/replay/replay.py` |
| Full backtest reproduction | DONE on two platforms; LIMITATION DISCLOSED (needs licensed data) | `reproduction_commands.md` |
| Variant ledger and trial counts | DONE; the project-wide total is LIMITATION DISCLOSED | `docs/results/variant-ledger.md` |
| Factor attribution and paired bootstrap | DONE (exploratory) | `results_2/attribution/` |
| Turnover labels, capacity screen, risk controls | DONE; total portfolio turnover and validated capacity are LIMITATION DISCLOSED | `results_2/turnover_capacity/` |
| Result-source manifest | DONE | `results_2/MANIFEST.csv` |
| Reviewer gap map | DONE | `docs/results/reviewer-gap-coverage.md` |

## Reporting conventions

**Report headline and corrected results.** The report's Summary leads with the original (D-3) out-of-sample numbers:
Sharpe 0.61 / 0.54, and a maximum drawdown of -6.6% under the old convention. Its Section 5.8 gives the D-4
corrections, and Sections 5.2 and 6 give the drawdown from the starting NAV (-7.4%). The corrected results with both
fixes are in `results_2/metrics/v2_metrics.csv`:
- Sharpe 0.621 / 0.554;
- maximum drawdown -7.19% from the starting NAV.

If the PDF leads with D-4, use those numbers and keep the original ones beside them.

**Wording rules:**
- The hit rate is the share of positive-excess days, not a per-trade win rate.
- The portfolio's 0.307x is overlay-only turnover.
- The UUP comparison is a daily-volume screen, not a validated capacity.

## Provenance of the submission

| What | Commit |
|---|---|
| Original v2 results (D-3 out-of-sample) | `88ce3ab` |
| D-4 corrections (the main strategy's results) | `ba16940`, runner `6629abf` |
| HiPerGator full rerun | `cdb2be6` |
| Reviewer-gap analyses, docs layout and these files | the commit that adds this file |
| Final submission release | the merge of `review/strategy-01` into `main` that carries this file. Tag it when the team submits, for example `git tag submission-2026-10-04 <merge commit> && git push origin submission-2026-10-04` |
