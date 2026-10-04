# Reviewer gaps: what was resolved and where

This page lists the reporting and reproducibility gaps raised by the external review of commit `d6b68b4`, the
files that resolve each one, and a status.

All of this work lives in `results_2/`. None of it ran a new backtest: every number is recomputed from committed
signals, positions and daily returns. The frozen results stay untouched:
- `backtests/results/v2/` and `backtests/results/v2_oos/` (the original run and its one D-3 out-of-sample
  evaluation);
- `backtests/results/v2_d4/` (the D-4 corrections).

The failed pre-registered verdict for v2 stands. The D-4 out-of-sample window had already been seen when D-4 was
written, so it is reported as a historical out-of-sample period, not a fresh holdout.

**Statuses:**
- `DONE`: resolved from committed outputs.
- `LIMITATION DISCLOSED`: a part cannot be resolved without data or work outside scope. The gap is stated in the
  linked file and in the report.
- `MISSING`: not done.
- `WAITING FOR INPUT`: needs something only the team can supply.

| # | Gap | Status | Files |
|---|---|---|---|
| 1 | Drawdown must include the starting NAV | DONE | `results_2/metrics/v2_metrics.csv`, `results_2/metrics/metrics.md`, `results_2/metrics/test_drawdown.py` |
| 2 | Full v2 metrics table and equity figure | DONE | `results_2/metrics/v2_metrics.csv`, `results_2/metrics/equity_v2.png`, `results_2/metrics/equity_portfolio.png` |
| 3b | Transcript provenance | DONE, with the source-equivalence assumption stated for the 17 conferences that cannot be checked against speech | [transcript-provenance.md](transcript-provenance.md), `results_2/provenance/` |
| 4 | Practical, honest reproduction | DONE (public replay, full-run instructions); LIMITATION DISCLOSED (full rerun needs licensed data) | `results_2/replay/replay.py`, [saved-result-replay.md](../guides/saved-result-replay.md), [reproduction_commands.md](../submission/reproduction_commands.md) |
| 5 | Variant ledger and trial counts | DONE; the project-wide total is LIMITATION DISCLOSED (not countable exactly) | [variant-ledger.md](variant-ledger.md), `results_2/ledger/` |
| 6 | Factor attribution and paired bootstrap | DONE (exploratory, specification fixed first) | `results_2/attribution/SPEC.md`, `results_2/attribution/ATTRIBUTION.md`, `results_2/attribution/*.csv` |
| 7 | Turnover, risk and capacity claims | DONE; total portfolio turnover and a validated capacity are LIMITATION DISCLOSED | `results_2/turnover_capacity/TURNOVER_CAPACITY.md`, `results_2/turnover_capacity/*.csv` |
| 8 | Submission files and source manifest | DONE | `docs/submission/`, `results_2/MANIFEST.csv` |

## 1. Drawdown convention

**What changed.** The committed v2 metrics start the running peak after the first day's return (`v2lib.max_dd`), so
a loss on day one is never counted. `results_2/metrics/v2_metrics.csv` carries both conventions:
- `max_dd_from_first_close`: the old numbers, kept for comparison;
- `max_dd_incl_start_nav`: the corrected numbers, with the starting NAV of 1 in the running peak.

Both are compounded **excess-return** drawdowns and restart in each window. A total-account drawdown is a separate
column: excess return plus the T-bill, from the public `rf_daily.parquet`.

**Where it matters.** The two conventions differ only when a window stays below its start from the first day to its
trough. That happens out of sample for T4xE1 and core_ER_6 + T4xE1, and in no in-sample window.

| Out-of-sample, 2024-10-03..2026-10-02 | Old convention | Starting NAV included | Total account (with T-bill) |
|---|---|---|---|
| v2 T4xE1, both D-4 fixes | -6.4333% | **-7.1896%** (trough 2025-01-13) | -6.07% |
| v2 T4xE1, original (D-3) | -6.6477% | -7.3782% | |
| core_ER_6 + T4xE1, both fixes | -5.2824% | **-5.9187%** (trough 2025-04-08) | |
| core_ER_6 + T4xE1, original | -5.3177% | -5.9420% | |
| core_ER_6 alone | -4.7476% | -4.7476% | |

In-sample drawdowns are identical under both conventions; T4xE1 with both fixes is -18.51%. `test_drawdown.py`
passes 9/9. It includes a series whose first return is negative, the reviewer's two out-of-sample figures (to 1e-6),
and a check that the old convention still reproduces the committed numbers (to 1e-12).

## 2. Metrics table and figure

`v2_metrics.csv` has 20 rows covering selection, validation, full in-sample and out-of-sample for five series:
- T4xE1, original and both D-4 fixes;
- core_ER_6;
- core_ER_6 + T4xE1, original and both fixes.

Each row has:
- exact first and last dates and the observation count;
- arithmetic and geometric excess return, and total return including the T-bill;
- volatility;
- Sharpe at net 1x, net 2x and gross;
- both drawdowns, with peak and trough dates;
- labelled turnover;
- hit rate;
- Newey-West t with its lag.

**Definitions:**
- **Hit rate** is the share of days with a positive daily excess return. It is not a per-trade win rate.
- **Newey-West** uses a Bartlett kernel with lag floor(4(n/100)^(2/9)): 7 for selection, 6 for validation, 7 for full
  in-sample and 5 out of sample.

All 426 values that also appear in committed metrics files match them, with a largest difference of 3.55e-15.

| v2 T4xE1, both D-4 fixes | Full in-sample (2,202 days) | Out-of-sample (501 days) |
|---|---|---|
| Sharpe net 1x / 2x / gross | 0.4463 / 0.3919 / 0.5130 | 0.6206 / 0.5538 / 0.7028 |
| Excess return, arithmetic / geometric (annual) | 5.07% / 4.52% | 3.90% / 3.77% |
| Total return including T-bill (geometric, annual) | 6.52% | 7.96% |
| Volatility | 11.35% | 6.28% |
| Maximum drawdown, excess (starting NAV included) / total account | -18.51% / -17.58% | -7.19% / -6.07% |
| One-way instrument turnover per year | 27.24x | 18.46x |
| Hit rate (positive excess days) | 49.68% | 49.90% |
| Newey-West t (lag) | 1.42 (7) | 0.86 (5) |

The equity figures `equity_v2.png` and `equity_portfolio.png` are drawn from the same series, with the out-of-sample
window shaded. Original and corrected rows are kept separate.

## 3b. Transcript provenance

Full write-up: [transcript-provenance.md](transcript-provenance.md).

**What v2 scores.** One document per press conference: the Chair's turns of the official transcript, 79 conferences.
- 99.73% of the scored tokens lie in Chair turns.
- 99.31% of the Chair's transcript tokens are scored.
- Each document becomes tradable at the first session after the conference date. This rebuilds the committed
  in-sample signal to 2.2e-16.

**Checked against speech.** For the 62 conferences whose recording matches the transcript, an independent Whisper
transcript of the official video contains a median 94.3% of the scored tokens (range 88.8%-97.3%). The unmatched
passages of 8 or more tokens make up 0.85% of the scored tokens; 168 of their 212 passages fall where the ASR returned
nothing over audible speech. No unheard passage outside an audio gap contains a lexicon word.

**Defects in how the scored text was built:**
- 11 written footnote corrections are scored as if spoken, in 10 conferences.
- 721 tokens of reporter or moderator text are scored as the Chair's.
- 2,569 Chair tokens are missing, including the whole 2018-09-26 opening statement.
- 282 editor's bracketed insertions are scored.

Treating each affected sentence as flipped, the worst-case change in a document score is 0.328 (2018-09-26). The
bound is zero for 45 of the 79 documents. The standard deviation of the scores is 0.068.

**Not checkable against speech:** 17 conferences, namely Yellen 2015-2017, Warsh 2026, the 2023-06-14 video (it
shows the July conference) and the partial 2020-03-15 recording. For these, v2 relies on the source-equivalence
assumption stated in the write-up.

No live wall-clock timestamp is claimed. v2 uses document dates, not word times.

## 4. Reproduction

**Two paths:**
- **Public saved-result replay:** `python results_2/replay/replay.py`. It recomputes seven items from committed
  derived files and needs no licensed data. All pass, with 8,422 comparisons and a largest relative difference of
  4.65e-6. The press-conference files are written to 6 significant digits; every other item matches to 1e-9 or
  better.
- **Full backtest reproduction:** `bash backtests/run_all_backtests.sh`, or `sbatch hpg/backtest_all.sbatch`. It
  needs the private price files and the engine at a pinned commit.

Both are pinned to `hpg/backtest_requirements.txt`. Both return a non-zero exit when a required input is missing,
write outside the frozen folders, and do not count a skipped stage as a reproduction.

**Verification:**
- The replay was run from a fresh copy of the tracked files and passed. Its regenerated metrics table was
  byte-identical.
- The full path reproduced on HiPerGator: v2 to 1.8e-15, D-4 5/5 files, press conference 13 + 8 + 13 files, and
  H2/H3/H4 identical.

**Limits:**
- Arithmetic replay does not validate signal construction or execution.
- The reviewer's `backtests/tools/review_d4_submission.py` was not supplied to this repository. `replay.py`'s D-4 item
  covers the same table with 1,781 comparisons.
- Multimedia features stay exploratory. The published local tables (`data/fedpress_features_local/`, 64 Powell
  conferences) reproduce H2 and H4 to within 0.001 of the private HiPerGator reference tables. The v2 submission
  does not need them.

Commands: [reproduction_commands.md](../submission/reproduction_commands.md).

## 5. Variant ledger

Full write-up: [variant-ledger.md](variant-ledger.md).

`VARIANT_LEDGER.csv` has 78 rows. Each row is classed as one of:
- selection candidate (8);
- prespecified robustness (7);
- post-result diagnostic (12);
- implementation correction (9);
- independent failed or exploratory study (42).

Each row also records whether its evaluation period had already been observed.

The documented counts are kept by scope:
- the v2 Deflated Sharpe used 11 trials (10 distinct);
- the press-conference gate used 1;
- the exploratory Holm family used 3;
- the earlier edge and portfolio study used 117.

The scopes overlap, so no project-wide total is claimed.

## 6. Attribution and bootstrap (exploratory)

`SPEC.md` was written and hashed before computing, and `attribution.py` refuses to run if it changes.

**Factor attribution.** Duration and dollar exposure, and rate momentum, each explain little of v2. In every window
and variant, the R-squared of each of those single factors is below 0.16. On full in-sample, v2 is mostly its own
lexicon leg (R-squared 0.82). Out of sample, the joint fit (R-squared 0.60) reflects a collinearity between the
duration and lexicon factors: their correlation is 0.735 out of sample against -0.181 in sample.

**Paired block bootstrap** of Sharpe(core_ER_6 + v2) minus Sharpe(core_ER_6). The method is circular blocks of 20,
10,000 resamples and seed 20261004.
- **Out of sample:** the difference is +0.271 with both fixes, with a 90% interval of [-0.116, +0.705]. 12.7% of
  resamples are at or below zero.
- **Across the sensitivities** (block 10 and 40, net 2x): none of the 24 configurations has a 90% interval that
  excludes zero.

This is different from the portfolio's own Newey-West t (1.33 out of sample), which tests whether the portfolio's
mean is positive, not whether v2 added to it.

## 7. Turnover, risk and capacity

**Turnover, labelled by type** (`turnover_labels.csv`):
- v2 instrument turnover is 18.46x a year out of sample with both fixes (17.66x original).
- The portfolio's 0.307x is overlay-only: month-end multiplier changes.
- The v2 sleeve's own trading inside the portfolio is 6.03x.
- The core sleeves' internal trades are not committed, so total portfolio turnover is reported as unavailable.

**Capacity** is a daily-volume screen, not a validated capacity estimate. The median daily dollar volumes are TLT
$2,753.4m and UUP $32.6m. Out of sample, the largest UUP trade is 25.5% of NAV, which would be 7.8% of a median UUP
day at $10m. The largest UUP trade reaches 10% of a median day at about $12.8m.
`TURNOVER_CAPACITY.md` lists the data a real estimate would need:
- opening-auction volume and imbalances;
- depth after the open;
- intraday trades;
- UUP creation and redemption capacity.

**Risk controls.** The 8 controls implemented in the committed code are listed separately from 6 proposed controls,
which are not implemented, tested or pre-registered.

## 8. Submission files

In `docs/submission/`:
- `submission_status.md`;
- `devpost_description.md`;
- `reproduction_commands.md`.

`results_2/MANIFEST.csv` maps every headline number and figure to its file and SHA-256.
