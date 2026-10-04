# Stance-score wiring

Scripts that feed the walk-forward chrono stance scores (`nlp/`) into the two text backtests.

| script | where | what |
|---|---|---|
| `backtests/wire/check_chrono.py` | `backtests/wire/` | gate: the chrono run finished cleanly (36/36 models, 12/12 years scored with full-spec metadata, the scored documents are `data/text_corpus/docs_to_score.parquet`, model Y scores year Y only, `run.log` ends cleanly) |
| `adapt_v2.py` | `backtests/v2/` | chrono document scores -> v2 `score/doc_scores.parquet` |
| `adapt_presser.py` | `backtests/presser/` | chrono sentence labels -> press-conference text label (`backtests/presser/text_chrono/`: answers, meetings, build_meta, scorer) |
| `run_v2_chrono.py` | `backtests/v2/` | the v2 run on chrono scores (one-shot OOS lock) |
| `backtests/wire/summarize.py` | `backtests/wire/` | combined `summary.json` / `summary.md` from what the two backtests wrote |
| `backtests/wire/wirelib.py` | `backtests/wire/` | shared paths and helpers |

`bash backtests/run_all_backtests.sh chrono` (with `CHRONO_ROOT` set) runs the gate and both adapters into
`backtests/rerun/chrono_inputs/` and compares the rebuilt tables with the committed frozen inputs. If the merged scores
are missing it first runs `nlp/chrono_stance.py --root $CHRONO_ROOT merge --years 2015-2026 --no-publish`.
The history of these scripts (placebo chain test, audit changes) is in `backtest_snapshot/wire/README.md`.

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

**Press conference.** The definitions are `presser/text/code/build.py`'s, applied to the chrono sentence labels.

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

