# Stance-score wiring: chrono walk-forward scores into the v2 and press-conference backtests

One command, run from Git Bash once the chrono run in `chrono/full` has finished:

```
bash <scratch>/run_results.sh
```

`--placebo` runs the same chain on random scores under `placebo_chain/` (see below).

## Steps (`run_results.sh`)

| step | what | script |
|---|---|---|
| 1 | Gate: 36/36 models done (8-epoch cap, label-year rule `true`); 12/12 years scored with full-spec metadata and newer than their models; scored documents = `docs_to_score.parquet`; `run.log` ends with run_local's "all done in ..." and has no FAILED or Traceback line | `check_chrono.py` |
| 2 | `chrono_stance.py merge --years 2015-2026 --no-publish` (fedspeak_v2 venv) | team code |
| 3a | v2 adapter, writing `fedspeak_v2/score/doc_scores.parquet` and `doc_scores_meta.json` | `adapt_v2.py` |
| 3b | press-conference adapter, writing `presser_bt/text_chrono/` (`answers.parquet`, `meetings.parquet`, `build_meta.json`, `scorer.json`) | `adapt_presser.py` |
| 4 | v2 backtest, run from the repo root with the gqh venv | `run_v2_chrono.py` |
| 5 | press-conference backtest: `presser_bt/backtest/code/run_all.sh` with `PRESSER_TEXT_DIR=text_chrono`. Before it runs, the earlier outputs (BENCH-R and the lexicon control, no stance scores) are copied once to `presser_bt/backtest_prechrono/` | presser code |
| 6 | `results_final/summary.json` and `summary.md` | `summarize.py` |

## Column mapping

**v2** (`doc_scores_lexonly.parquet` -> `doc_scores.parquet`, 1,098 documents):
- the v2 `doc_type` maps to the chrono `source`: `presser` -> `presser_doc`, the others keep their name;
- doc_id, source and date must match one to one, and each document must be scored by the model of its own year.

| v2 column | chrono source |
|---|---|
| `rob_hawk`, `rob_dove`, `rob_neut` | `share_hawk`, `share_dove`, `share_neut` |
| `rob_score` | `score` (share hawkish - share dovish) |
| `n_sentences` | chrono unit count. The v2 splitter's count is kept as `n_sentences_v2split`; `run_v2` does not read either. |
| `rob_status` | scorer id |
| `stance_model_year`, `stance_base_model`, `stance_seeds`, `stance_label_year_rule` | added |

All `lex_*` columns are copied, then checked equal to the lexicon-only file. A document with zero chrono units would
stop the adapter, because `run_v2` would refuse it anyway.

**Press conference.** The definitions are `presser_bt/text/code/build.py`'s, applied to the chrono sentence labels.

Answers:
- `hawk`, `dove`, `score`;
- `question_score`;
- `cum_mean_score`;
- added: `n_sentences_chrono`, `q_n_sentences_chrono`.

Meetings:
- `statement_hawk`, `statement_dove`, `statement_score` (roster sentence excluded);
- `statement_score_incl_roster`;
- `qa_mean_score` (answers with at least 1 chrono unit);
- `qa_mean_score_ge40w`, `qa_pooled_score`, `q_mean_score`;
- `H1 = qa_mean_score - statement_score`;
- `roberta_status` = scorer id;
- added: `statement_n_sentences_chrono`, `n_answers_scorable_chrono`.

**Kept unchanged** (checked):
- the text pipeline's own unit counts (`n_sentences`, `q_n_sentences`, `statement_n_sentences`,
  `n_answers_scorable`);
- all `lex_*` and timing columns.

That keeps the lexicon control's answer eligibility exactly as before. A stance answer also needs a finite chrono
score; that is the backtest's own rule.

`statement_score`, `qa_mean_score` and `H1` are cross-checked against the team's merged table
`scores/presser_meetings_chrono.parquet`. They must agree to 1e-9 and have the same NaN pattern.

## Changes to existing code

**`presser_bt/backtest/code/`.** The originals are kept in `wire/orig_presser_code/`.
- `lib.py`:
  - `OUT` and the text folder can be redirected with `PRESSER_OUT_DIR` and `PRESSER_TEXT_DIR`; the defaults are
    unchanged;
  - `stance_scorer()` reads `scorer.json`.
- `s01_qa.py`: the input manifest hashes the text files actually read.
- `s03_pnl.py`:
  - `run_meta.json` records the scorer id and the text and output folders;
  - H1-Q (ADDENDUM section 6, robustness only, never gated) is now computed from the H1-Q positions s02 already
    writes, where it was hard-coded "not computed".

**Regression check** (placebo run vs the existing outputs): BENCH-R trades, break statistics, cost hurdle and
spreads, the QA summary, and the lexicon control are identical. The lexicon control covers the answer selections,
the `h1answer_summary` rows, the per-meeting tables and the G3 blocks. Every one of the 3,712 non-stance rows of
`summary_long.csv` is identical too.

**`fedspeak_v2/backtest/run_v2.py`** is not modified. `run_v2_chrono.py` imports it and changes two settings from
outside:
- **Pre-registration hash.** `run_v2` pins the Amendment-1 version of HYPOTHESIS_v2.md. The file now also carries
  Amendments 2-3 and the clarification, so the wrapper checks the current sha256 (464f8a5b...).
- **Paths.** `DOC_SCORES` and the output folder (`fedspeak_v2/backtest/`, as its README says).

It then calls `run_v2`'s own `pipeline_is` and `stage_oos`, and adds the scheduled-only de-risk sensitivity of
`fedspeak_v2/DEVIATIONS.md` D-1.

A real run refuses to start when the output folder already holds `oos_chosen.json` or `oos_not_evaluated.json`,
because the out-of-sample evaluation happens once.

## Placebo test (`placebo_chain/`)

`run_results.sh --placebo` (about 4 minutes on CPU) did the following:
- built a fake chrono work root from `docs_to_score.parquet` with random sentence labels and the real schema;
- passed the same gate, merge, adapters, both backtests and the summary;
- refused any output path without "placebo".

Its v2 decision rule failed on the placebo scores, so no out-of-sample stage ran. With `--placebo` the OOS stage is
skipped in any case.

`placebo_chain/oos_codepath_test/` exercised the OOS code path (`stage_oos` and the scheduled-only OOS sensitivity)
with no out-of-sample data:
- engine period FWD redirected to IS;
- the "OOS" window set to 2023-01-03..2024-10-02;
- the decision rule forced to "passed".

Nothing in `placebo_chain/` is a result.

## Audit changes (2026-10-03)

- `check_chrono.py` also checks that every document in `<Y>_docs.parquet` is dated in year Y with `model_year` Y.
  In real mode (no `--placebo`) it refuses placebo-marked years and any base model other than
  `manelalab/chrono-bert-v1-<min(Y-1, 2024)>1231`. `run_results.sh` passes `--placebo` only in placebo mode.
- `adapt_presser.py` refuses a press-conference answer, question or statement scored by a model of a year other
  than its meeting's year.
- `run_results.sh` (real mode) refuses to start unless `fedspeak_v2/DEVIATIONS.md` exists with entries D-1 and D-2.
- Safe rerun. Once the real v2 run is complete (an `oos_chosen.json` or `oos_not_evaluated.json` exists):
  - step 3 leaves `doc_scores.parquet` byte-for-byte untouched if the rebuilt table is identical, and stops if it
    differs (`adapt_v2.py --keep-if-equal`);
  - step 4 skips, after checking that the doc_scores sha256 equals the one in `summary_is.json`
    (`run_v2_chrono.py --skip-if-complete`). The OOS is never recomputed;
  - steps 5-6 run again.
- Placebo mode removes only the chain's own subfolders, so `placebo_chain/oos_codepath_test/` is kept.
- `summarize.py`:
  - the OOS heading reads the record's `window`;
  - a missing OOS table no longer crashes it;
  - it reports the D1a label coverage and leakage counts per model year, from `data/label_year_audit.json`.
