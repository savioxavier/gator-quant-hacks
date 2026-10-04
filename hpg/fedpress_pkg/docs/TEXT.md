# Text stance, aggregation and the walk-forward stance models

This page covers `fedpress/stages/text.py`, `fedpress/stages/aggregate.py`, `fedpress/train/` (the stance
models), `fedpress/baselines.py` (causal per-chair z-scores) and `fedpress/dataset.py` (the cross-meeting
panel). The stage contract, the `known_at` rule and the 2-GPU run model are in `ARCHITECTURE.md`.

## 1. What the defaults implement

| Plan item | Default here | Config |
|---|---|---|
| Stance model (team plan: frozen FOMC-RoBERTa) | **Deviation D1 (2026-10-03):** FOMC-RoBERTa is gated with manual approval and no access exists, so the stance scorer is the walk-forward ChronoBERT. Pressers in year Y are scored by `manelalab/chrono-bert-v1-<min(Y-1, 2024)>1231` fine-tuned on labelled sentences whose source document is dated before Y-01-01 (D1a re-dating, section 3), 3 seeds averaged | `text.primary: chrono_wf` |
| FOMC-RoBERTa | Cross-check, scored automatically once its weights are in the cache (after access is granted and `prefetch-models` has run); otherwise recorded as unavailable. Under D1 it is a robustness rerun only | `text.stance_models` |
| Unit score (A-10, D1) | Chair sentences of >= 4 words, equal weights. `hawk` = share hawkish - share dovish (argmax of the averaged seed probabilities). `<p>_hawk_prob` = mean P(hawkish) - P(dovish) is stored too | `text.score`, `text.sentences.min_words` |
| Splitter (A-10, A-36) | Pinned regex splitter `fedpress-regex-1` (abbreviations, initials, decimals); the id is on every sentence row | `text.sentences.splitter` |
| TDW keyword filter (A-10) | Not the inclusion rule; `tdw_filter` per sentence and `<p>_hawk_share_tdw` per unit as the labelled robustness version | |
| CentralBankRoBERTa (A-30) | Agent sentiment (positive/negative for households, firms, ...), stored as `cbr_sentiment`; never a stance fallback | `text.sentiment_models` |
| Loughran-McDonald | Uncertainty, weak/strong modal, negative, positive, constraining counts per 100 words. The dictionary is not shipped (academic licence): set `FEDPRESS_LM_CSV`; without it the columns are NaN and the done-marker says so | `text.loughran_mcdonald` |
| Hedges | Phrase list in the config (`i think`, `perhaps`, `data dependent`, ...), counted per unit | `text.hedges.phrases` |
| Opening remarks | Not scored; not in `answers` (team plan). Add `opening` to `text.units` / `aggregate.segments` for descriptive use | |
| H1-Q | Reporters' questions are scored; `hawk_question` per answer, `hawk_question_mean` per meeting | `text.units` |
| Contamination (A-29) | `<p>_in_train` per unit from the registry `data_end` (FOMC-RoBERTa labels end 2022-10-15; base pretraining to 2019-02). Walk-forward models are never in-train by construction. `in_tdw_labels` per sentence flags presser sentences that appear verbatim in the TDW labels (the A-14 drop-verbatim sensitivity) | `models.*.data_end` |
| Novelty | Lexical (hashed term counts, nothing fitted): each unit vs the same day's statement (`nov_stmt_lex`), and in the panel each answer and meeting vs the previous presser (`nov_prev_lex`, `stmt_nov_prev_lex`). Embedding novelty (Qwen3-Embedding or any sentence-transformers model) is a plan_v0 option, off | `text.novelty.embeddings`, `aggregate.novelty_prev` |
| Meeting score (A-10) | `h1_gap` = hawk of all chair Q&A sentences pooled with equal weights - statement hawk; the answer-weighted mean is kept as `hawk_qa_answer_mean`; running means follow the same weighting | `aggregate.h1_weighting` |
| H1-answer selection (A-22) | `h1_answer_eligible` = answer of >= 40 words; nothing is dropped | `aggregate.h1_answer_min_words` |
| vocal_proxy (A-31) | Per-answer and per-meeting **median** of arousal, dominance, F0, voicing, intensity, rate, pauses over identity-verified chunks; valence excluded unless added | `aggregate.voice.columns` |
| Windows (plan_v0) | Trailing 30 s and 60 s windows every 10 s through the Q&A (`features/windows.parquet`) | `aggregate.windows_s`, `window_step_s` |
| Baselines | Raw values only in every table. `fedpress.baselines.causal_z` computes prior-meeting, same-chair z (4-meeting burn-in, variance floor, median/MAD) at analysis time; `aggregate --all` also writes `panel/*_causal_z.parquet` | `aggregate.baselines` |
| No LLM | None in the primary path | `text.llm.enabled: false` |

## 2. Commands

```bash
# 1. prep wave (CPU job or srundev; needs outbound HTTPS)
python -m fedpress.train.stance_walkforward prepare     # labels: HF copy + doc types from GitHub (+ team CSV)
python -m fedpress.cli prefetch-models                  # includes 15 ChronoBERT checkpoints (~9 GB), CentralBankRoBERTa,
                                                        # FOMC-RoBERTa (reports an error until access is granted)
# 2. GPU job (<= 2 GPUs, offline): stance models first, then the GPU stages
python -m fedpress.train.stance_walkforward train --all --gpus 2      # 10 models x 3 seeds, shared claim queue
python -m fedpress.train.stance_walkforward status
python -m fedpress.cli launch asr,turns,diarize,voice,face,text --all
# 3. post wave (CPU)
python -m fedpress.cli aggregate --all                  # per-meeting tables, then the panel (finalize)
python -m fedpress.cli aggregate --all --finalize       # rebuild only the panel
```

Training runs inside the GPU job so the GPUs are busy from the start (idle-GPU rule). `train --years 2016-2018`
trains a subset; `--force` retrains. A job whose labels or settings changed is reported as stale and kept until
`--force`. The text stage refuses models trained with other labels or settings, and smoke models made with
`--max-rows/--max-epochs` unless `text.chrono_wf.allow_smoke=true`.

In Python:

```python
from fedpress.config import load
from fedpress.dataset import load_panel
from fedpress.baselines import causal_z, meeting_order
cfg = load()
answers, meetings = load_panel(cfg, "answers"), load_panel(cfg, "meetings")
z = causal_z(answers, ["voice_arousal", "voice_dominance"], order=meeting_order(meetings.dropna(subset=["known_at"])))
```

## 3. Walk-forward stance models (`fedpress/train/stance_walkforward.py`)

* **Labels** (`prepare`): `gtfintechlab/fomc_communication` train.csv + test.csv at dataset revision
  `6b0283f5` (2,480 rows, 1996-2022). Document types come from the authors' annotated files at GitHub commit
  `98646987` (`manual-{mm,pc,sp}-split.xlsx`): 959 minutes, 950 speeches, 309 press-conference sentences
  matched, 187 unknown. 5 sentences with conflicting labels are dropped and exact duplicates kept once: 2,405
  rows (`<root>/train/labels_meta.json` records counts and file hashes). An optional team CSV
  (`FEDPRESS_TEAM_LABELS`: sentence, label, date or year, doc_type) is appended; only blind labels belong there.
* **Label dates (deviation D1a = fedspeak_v2 Amendment 3, `train.stance_walkforward.data.redate`, on by
  default):** the dataset's `year` column differs from the source document's year for 2,336 of 2,480 rows (a
  2022 speech sentence can carry 2004), so the "labels <= Y-1" rule on that column let 126 (model 2022) to 514 (model 2016) rows from
  documents dated Y or later into the 2016-2022 models (checks_r3_validity/r3_label_dates.out). `prepare` therefore re-dates every row to the earliest
  source document containing it, from the team's table `manifest/label_dates.parquet` (sha256 pinned in the
  config; rebuilt with `manifest/build_label_dates.py` from the authors' per-document files at commit `98646987`;
  all 2,480 rows dated). `year` becomes the source year and `dataset_year` keeps the original; model Y trains on
  rows with source date before Y-01-01, and the held-out gate uses the rows of year Y by source date. Rows that
  cannot be dated get `year = 2022` (out of the 2015-2022 models, kept for 2023+). Labels built without
  re-dating are refused by the trainer and the text stage (`prepare --force` rebuilds them).
* **Models:** key `b<base>_l<label_end>`; base = min(Y-1, 2024), label_end = min(Y-1, 2022). The 2016-2026
  sample needs 10 keys (2025 and 2026 share `b2024_l2022`); the 2011-2015 calibration years add 5 (base 2010-2014).
* **Fixed settings (Amendment 2):** 15 % stratified validation split (seed 0), early stopping on macro-F1,
  lr 2e-5, batch 16, max length 256, <= 8 epochs, patience 2, weight decay 0.01 (not on bias/norm weights),
  10 % linear warmup, seeds 42/43/44, float32 without TF32 by default.
* **Accuracy gate (A-14):** each model is evaluated on the labels of its own test year (never seen in its
  training), overall and on the press-conference subset (`heldout` in `meta.json` and `registry.json`).
  `train.stance_walkforward.gate.min_heldout_macro_f1` must be fixed in the pre-registration before scores are
  joined to returns; the package only reports.
* **Outputs:** `<root>/models/stance_walkforward/<key>/seed<s>/` (safetensors, tokenizer, `meta.json` with base
  revision, label hash, rows, history, held-out scores, device, dtype, versions) and `registry.json`.

## 4. Tables

Every table carries the common columns of `ARCHITECTURE.md` section 3 (ids, `t_start_s`, `t_end_s`,
`t_end_utc`, `known_at`, `latency_s`, `anchor_source`, `anchor_unc_s`). Prefixes: `cwf` walk-forward ChronoBERT,
`fomc` FOMC-RoBERTa, `cbr` CentralBankRoBERTa.

| Table | One row per | Key columns | known_at |
|---|---|---|---|
| `text/text_sentences.parquet` | sentence of the statement, each answer, each question | unit, turn_idx, qa_idx, sent_idx, text, n_words, included, tdw_filter, time_method (words / words_prop / interp / statement), splitter, `<p>_p_<label>`, `<p>_label`, `<p>_truncated`, lm_*, hedge_count, in_tdw_labels | sentence end (from the word times) + latency; statement: release + latency |
| `text/text_units.parquet` | statement, answer turn, question turn | n_sentences, n_included, n_words, hawk, hawk_model, hawk_method, stance_model_id, `<p>_hawk_share`, `_hawk_prob`, `_hawk_share_tdw`, `_n_<label>`, `<p>_in_train`, cbr_sentiment, lm_*_per100, hedge_count, hedge_per100, nov_stmt_lex, [nov_stmt_emb], in_classifier_train | unit end + latency |
| `text/text_vectors.parquet` | unit | tf_idx, tf_val (hashed term counts), [emb] | unit end + latency |
| `features/answers.parquet` | chair answer turn | the unit's text columns, hawk_statement, `*_gap` (answer - statement for every stance score), question_turn_idx, hawk_question, hawk_qa_running, hawk_gap_running, n_answers_so_far, h1_answer_eligible, voice_* (median), voice_n_chunks, face_* (mean), face_n_frames, face_ok_frac, voice_state, face_state, timing_ok | answer end + latency |
| `features/meeting.parquet` | meeting | n_answers, n_sentences_qa, hawk_statement, hawk_qa_sent, hawk_qa_answer_mean, hawk_qa_mean (per h1_weighting), **h1_gap**, `<p>_hawk_*_qa_sent`, `<p>_hawk_*_gap`, hawk_question_mean, statement_words (A-34), voice_*/face_* over all Q&A, turns QA notes, statement_utc, presser_start_utc | last answer end + latency |
| `features/windows.parquet` | (window length, grid time) | window_s, chair_speech_s, n_sentences, hawk_share, hawk_prob, voice_*, face_* | window end + latency |
| `panel/answers.parquet`, `windows`, `text_units` | as above, all meetings | + calibration_only, in_study, prev_presser_id, nov_prev_lex, [nov_prev_emb] | unchanged |
| `panel/meetings.parquet` | policy meeting of the windows (88 for 2016-01..2026-10) | calendar (kind, has_presser, held) + meeting features; nov_prev_lex, stmt_nov_prev_lex | unchanged |
| `panel/*_causal_z.parquet` | as answers / meetings | `z_<col>`, baseline_n_meetings | unchanged |

Causality: sentence times come from the word table; an unmatched word takes the next known time, so a time
can only move later. Running means use answers that have ended. Novelty and z-scores look only at earlier
meetings. The previous presser for novelty is the preceding manifest row; if its outputs are missing the value
is NaN, never a comparison with an older meeting.

## 5. Wall clock

Measured on the local machine (CPU only, smoke models): text stage 10-17 s per meeting with one ChronoBERT
seed and CentralBankRoBERTa (440 sentences); aggregate 0.1-0.4 s per meeting; a 300-row, 1-epoch fine-tune
about 40 s. The GPU rows below are planning estimates, not measurements; replace them with `status` and the
`seconds` field of each `meta.json` after the first run.

| Step | 2 x B200 | 1 x B200 | RTX 5090 (400 W cap) |
|---|---|---|---|
| labels `prepare` (CPU, network) | < 1 min | same | same |
| `train --all`: 30 fine-tunes (10 keys x 3 seeds, ~2,000 rows, <= 8 epochs) | ~5 min (12 workers) | ~10 min (6 workers) | ~20-30 min (2 workers) |
| text, 75 meetings (~30k sentences; 3 seeds + CentralBankRoBERTa [+ FOMC-RoBERTa]) | ~2-3 min, model loading dominates | ~4-5 min | ~10-15 min |
| aggregate + panel (CPU) | < 2 min | same | same |

On CPU only, the full training would take roughly 10 hours; use a GPU.

## 6. Licences

| Item | Licence | Note |
|---|---|---|
| manelalab/chrono-bert-v1-* | MIT | base checkpoints |
| gtfintechlab/fomc_communication and the GitHub annotated files | CC BY-NC 4.0 | the fine-tuned walk-forward models inherit the non-commercial restriction |
| gtfintechlab/FOMC-RoBERTa | CC BY-NC 4.0, gated (manual) | cross-check; request access on the Hub |
| Moritz-Pfeifer/CentralBankRoBERTa-sentiment-classifier | MIT | agent sentiment |
| Loughran-McDonald Master Dictionary | free for academic use | not redistributed |
| Qwen3-Embedding-0.6B / 8B, all-MiniLM-L6-v2 | Apache-2.0 | options; training-data cutoffs not published (A-29) |
