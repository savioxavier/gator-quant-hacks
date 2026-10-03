# Fed communication v2: backtest step

Pre-registration: `../../preregistration/HYPOTHESIS_v2.md`
(sha256 6083d3ef742ad67623b34337c8299ce4c7172fc1e1a786003eae4b4fb7ced910, with Amendment 1; the runner checks it).

## Status, 2026-10-03 (about 21:00 UTC): blocked, no v2 return computed
The four signals T1-T4 all need the FOMC-RoBERTa score. `score/doc_scores.parquet` does not exist, because
`gtfintechlab/FOMC-RoBERTa` is a gated Hugging Face repository. This machine has no Hugging Face login and no
local copy (see `score/README.md`). `run_v2.py run` therefore stops before it loads any market data.
- No v2 combination, and no Variant A reference, has been computed on real scores in any window.
- Nothing was substituted for the model. A replacement, for example a model retrained from the public labelled
  data, would be a deviation. It would need an entry in `research/fedspeak_v2/DEVIATIONS.md` before any affected
  return is computed.
- No deviation has been logged, because none has occurred.

Once the account holder has run `score/rob_score.py score` (instructions in `score/README.md`):

```
GQH_DATA_DIR=<data cache> PYTHONIOENCODING=utf-8 python <this folder>/run_v2.py run
```

Run it from the repo root. It writes the following to this folder:
- `selection.csv`, `windows_all.csv`, `summary_is.json` (decision rule, falsifiers, DSR);
- `portfolio.csv`, `by_chair_is.csv`;
- the daily series `daily_<combo>_is.parquet`, `daily_excess_all_combos_is.parquet` and `signals_entry_session.parquet`.

If the rule passes, it then evaluates the chosen combination once in FWD and writes `oos_chosen.json` first, then
`portfolio_oos.csv` and `by_chair_oos.csv`. If the rule fails, it writes `oos_not_evaluated.json` instead.

## Verification already done (`check/check.json`, no strategy returns)
- **T0 (frozen Variant A) vs `fedspeak/replicate/signal.parquet`:** 3,711 decision dates to 2024-10-01.
  - Max abs difference: consensus 0, z 0, w_TLT 6e-15, w_UUP 2e-15.
  - The NaN pattern of z is identical.
- **T0 on the v2 corpus (2015 warm-up) vs frozen T0:**
  - All 380 kept speeches from 2015 on are matched, and their scores agree to 1e-16.
  - One speech is dated differently: `fischer20170928a` is 2017-10-11 in strategy 01's data and 2017-09-28 in
    the v2 corpus. This causes the 0.22 maximum consensus gap.
  - The z correlation over 2016-01..2024-10 is 0.982, because the z clocks differ (2011 vs 2015).
- **Causality:** every z and weight series, for all signals and both expressions, is identical (difference 0)
  when it is rebuilt with data cut at 2019-06-28.
- **Other checks:**
  - The T3 expanding OLS matches statsmodels to 2e-15 on three dates.
  - Documents dated d first enter the consensus on the next session.
  - core_ER_6, rebuilt through `edges/combine/combine.py`'s own `load`/`build`, reproduces
    `PORT_core_ER_6.parquet` exactly (difference 0 over 3,397 days).
- **Smoke test (`smoke_placebo/`):** the whole in-sample pipeline runs on random placebo scores; every score
  column, the lexicon included, is replaced. Its numbers carry no information and are not results.

## Implementation choices (fixed before any return was computed)
1. **Timing.**
   - Every document dated d, whatever its release time, first enters the consensus at the first session strictly
     after d. This applies equally to 14:00 statements and minutes, the 11:00 and 08:00 unscheduled 2019/2020
     statements, timed speeches, weekends and holidays.
   - E1 fills at that session's open (engine `next_open`). E2 fills at that session's close (engine `next_close`).
2. **Variant A parameters, frozen:**
   - consensus half-life 20 sessions, equal weight per document;
   - expanding z with ddof 1 and a minimum of 252 observations;
   - 10% vol target on the unit hawkish mix, vol floor 4%, gross cap 1.5, clip 2;
   - no-trade band of 10% of current gross, with a trade forced on the FOMC interval, the interval after it, and
     when the book is flat;
   - FOMC dates in Variant A's style: strategy 01's list before 2015, the corpus list from 2015. The two lists
     agree exactly for 2015 to 2024-10.
3. **z clock and start date.**
   - The z clock counts sessions from 2015-01-02, the first session of the corpus. The first valid z is
     2015-12-31.
   - E1 holds its first position from the open of 2015-12-31. E2's first held return is on 2016-01-04.
   - So the selection window is not delayed: it starts 2016-01-04 for every combination.
   - Window statistics never include days before the first position.
4. **T1 and T2 (FOMC-RoBERTa).**
   - Document score = share hawkish minus share dovish. There is no hit-count keep rule: every document injects.
   - T1 uses speeches only. T2 uses speeches, statements, minutes and press conferences.
5. **T3 (T2 orthogonalised to rate momentum).**
   - Momentum M_t is the decayed sum (half-life 20) of daily DGS2 changes, with DGS2 lagged two sessions from
     the entry session. It equals DGS2 minus its EWMA, up to the constant factor lambda.
   - Each day, C_T2 is regressed on [1, M] by expanding OLS over sessions from 2015-01-02 to t. The residual on t
     is standardised by the sd (ddof 1) of that fit's residuals, whose mean is 0. This is Variant A's expanding z
     applied point in time, with a minimum of 252 observations.
6. **T4.**
   - T4 = 0.5 x (z of the lexicon consensus + z of the RoBERTa consensus), on T2's document set. It is not
     re-standardised before the clip at 2.
   - The lexicon leg uses the primary `lex_score` and the frozen keep rule (H+D >= 5). As `score/README.md`
     notes, almost no statements pass that rule after 2017.
7. **E1:**
   - Variant A exactly: 75% TLT / 25% UUP, vol from open-to-open returns ending at the entry open.
   - Costs 1.5 / 5 bp per unit traded, plus the engine's 30 bp/yr borrow on short ETF weights.
8. **E2:**
   - 75% F_ZN / 25% short F_6E.
   - Vol from close-to-close returns ending at the decision close (strictly point in time).
   - The rates leg is halved for the position held over the announcement session.
   - Costs 1 bp each, plus one extra round trip on each roll day (the engine's roll flags). There is no borrow on
     futures.
9. **Returns and costs.** Returns are excess over the T-bill, from the engine. "2x" sets cost_mult = 2, which
   doubles trading and roll costs but not the borrow fee.
10. **Selection and decision rule.**
    - Selection: the maximum net 1x Sharpe over 2016-01-04..2020-12-31.
    - Decision rule: validation (2021-01-01..2024-10-02) net Sharpe > 0, AND net Sharpe at 2x costs over the
      full in-sample period (2016-01-04..2024-10-02) > 0.5.
    - The validation Sharpe is also reported against the 0.7 target.
11. **Deflated Sharpe.**
    - 11 trials: the 8 combinations' selection-window Sharpes plus the `sharpe_1x` of Variant A's 3 logged rows.
      Row 3 repeats row 2, so n = 10 is reported as a sensitivity.
    - DSR is computed on the selection window and on the full in-sample period.
12. **Portfolio test.**
    - Built by `combine.build` verbatim: equal risk, 6% target, trailing 252-day covariance (minimum 126
      observations), month-end decisions applied from d+2, leverage cap 4, overlay costs.
    - The fourth sleeve's series starts on its first held day. Its instrument gross is the sum of |held weights|.
    - Overlay cost: 2.375 bp for E1 (the 75/25 blend), 1.0 bp for E2.
13. **Chairs** (federalreserve.gov Board membership page, cached in `corpus/raw`):
    - Yellen 2014-02-03 to 2018-02-03;
    - Powell 2018-02-05 to 2026-05-22;
    - Kevin Warsh from 2026-05-22. That day is assigned to Warsh.
14. **Variant A reference.** Reported two ways:
    - as frozen (strategy 01 corpus from 2011, z clock from 2011-01-03);
    - with the v2 2015 warm-up.

    Neither is used for selection. In OOS, Variant A is computed only for the per-chair table, and only after the
    chosen combination's OOS record has been written.

## Update, 2026-10-03 (about 22:40 UTC): wired to the chrono stance scores, no real return computed yet
- Amendments 2-3 replace FOMC-RoBERTa with the walk-forward chrono stance model; `../DEVIATIONS.md` logs D-1 (the
  unscheduled dates in the FOMC de-risk list, kept as registered, with a scheduled-only sensitivity) and D-2 (the
  T3 scaling reading). Both were written before any return on real stance scores.
- `run_v2.py` is unchanged. The run goes through `wire/run_v2_chrono.py` (scratchpad), which checks the current
  pre-registration hash (with Amendments 2-3) and adds the D-1 sensitivity. It is started by
  `scratchpad/run_results.sh` once `score/doc_scores.parquet` has been built from the chrono scores by
  `wire/adapt_v2.py`. See `wire/README.md`.
