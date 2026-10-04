# Walk-forward stance model (hawkish / dovish / neutral)

`nlp/` trains the stance model that replaces the gated FOMC-RoBERTa, then scores every Fed document the
strategies use with it. The spec was fixed before any v2 or H1 return was computed:

- `preregistration/HYPOTHESIS_v2.md`, Amendment 2 (with its clarification on 2015) and Amendment 3 (corrected
  label dates)
- `preregistration/presser_DEVIATION_D1.md` (the stance-model deviation), including Update D1a

## What it does

For each model year Y from 2015 to 2026 (2016-2026 are the test years; model 2015 scores the v2 warm-up documents,
per the clarification to Amendment 2):

1. **Base model:** `manelalab/chrono-bert-v1-<min(Y-1, 2024)>1231` (MIT licence). It is a ModernBERT-base encoder,
   pretrained only on text up to the end of that year. A new 3-class classification head is added.
2. **Labels:** `gtfintechlab/fomc_communication` (CC BY-NC 4.0, not gated), train and test splits combined.
   Only rows whose source document is dated before Y-01-01 are used (Amendment 3; see "Label years" below). The
   labels end in 2022, so 2023-2026 all use the full 2,480 rows.
3. **Training:**
   - 15% stratified validation split (seed 0), used for early stopping on macro-F1;
   - lr 2e-5, batch 16, max length 256, at most 8 epochs, patience 2, weight decay 0.01, 10% warmup;
   - seeds 42, 43 and 44, so 36 models in total.
4. **Scoring:** a document dated in year Y is scored only by model Y.
   - Class probabilities are averaged across the three seeds.
   - Sentence label = argmax.
   - Document score = share hawkish - share dovish.

**Label ids:** LABEL_0 = dovish, LABEL_1 = hawkish, LABEL_2 = neutral. They come from the dataset card.
`prepare` re-reads the card and cross-checks it against cue words in the labelled sentences:

- sentences with hawkish cues ("tighten", "firming", "remove accommodation", "raise the target") are mostly label 1 (51 of 71);
- sentences with dovish cues ("lower the target", "asset purchases", "downside risks", "easing", "stimulus") are mostly label 0 (60 of 114).

If the check fails, `prepare` stops.

**Choices fixed in code before any scoring** (the spec leaves them open):

- Training rows are sorted canonically before the split. Per class, round(15%) of rows go to validation, drawn with RandomState(0).
- AdamW without decay on biases and norm weights; gradient clipping at 1.0; the linear schedule spans 8 epochs. These are the Hugging Face Trainer defaults.
- Training uses bf16 autocast; scoring runs in fp32.
- The kept checkpoint is the epoch with the best validation macro-F1.
- **Sentence splitter:** the team's fedspeak_v2 rule, NLTK 3.10.3 Punkt (`punkt_tab`, English), applied per paragraph:
  - stage directions are removed;
  - footnote digits are stripped;
  - short unpunctuated headings are dropped;
  - a unit needs at least 3 words of 2+ letters.

  On the 2020 press conferences it gives the same number of units as the H1 text pipeline for 99.4% of answers and for all statements.
- Statement voting-roster sentences ("Voting for ...") are flagged and scored both ways.

## Label years: source-document dates (default rule `true`)

The dataset's `year` column is not the year of the sentence's source document. Every labelled row was traced to its
source document in the authors' own repository (github.com/gtfintechlab/fomc-hawkish-dovish, commit `9864698`):

- 2,336 of the 2,480 rows carry a dataset year that differs from the source document's year;
- the median gap is 7 years, and the gap runs from -26 to +26 years;
- the correlation between the two years is 0.10.

The column looks shuffled across rows, while its year histogram stays almost the same as the source years'.
Example: a February 2022 Board speech sentence ("the Fed hasn't started raising rates or reducing the balance
sheet") carries 2004.

**The rule (Amendment 3, D1a):** model Y trains only on rows whose source document is dated before Y-01-01.

- When a sentence occurs in several documents, the earliest date counts.
- Rows without a source date are left out of the 2015-2022 models and kept for 2023+ (all labels predate 2023).
- Currently every row has a date, so no row is left out.

**`data/text_corpus/label_dates.parquet`** (committed) has one row per dataset row:

- the dataset's own columns: `row, split, index, orig_index, sentence, label, dataset_year`;
- the source: `source_type` (mm / pc / sp), `source_doc_id`, `source_date` (YYYY-MM-DD), `match_method`,
  `n_source_docs`;
- audit columns: `source_doc_type`, `source_meeting_date`, `first_same_type_date`, `last_source_date`,
  `source_doc_ids`.

`label_dates_meta.json` records the commit of the authors' repository, the label revision, the coverage and the
file's sha256. Build both with:

```
git clone --depth 1 --filter=blob:none --sparse https://github.com/gtfintechlab/fomc-hawkish-dovish.git tdw
git -C tdw sparse-checkout set data
python nlp/build_label_dates.py --tdw-repo tdw
```

How it matches:

- **Source type:** the authors' annotated sheets `annotated_data/manual-{mm,pc,sp}-split.xlsx` together hold exactly
  the 2,480 dataset rows.
  - The dataset's `index` is the sheet row, and its `orig_index` is the row of the unsplit sheet
    `manual-{mm,pc,sp}.xlsx`.
  - Every dataset row matches exactly one sheet.
  - The sheets carry no document id or date; their `year` equals the dataset's.
- **Documents:** the per-document files under `filtered_data/` (and the `*_labeled` copies) and `raw_data/`.
  - Minutes are dated by their release date, about three weeks after the meeting, from
    `master_files/master_mm_final_Oct_2024.xlsx`. `docs_to_score.parquet` dates minutes the same way.
  - Press conferences and speeches are dated by the date in the file name, cross-checked against
    `master_pc_final.xlsx` and `master_speech_final.csv`.
- **Comparison:** text is lower-cased, line-break hyphenation is joined ("modera- tion" becomes "moderation"), and
  every run of punctuation, quotes or whitespace becomes one space.
  `match_method` gives the strongest evidence found:

  | method | rows | what matched |
  |---|---|---|
  | `exact` | 2,281 | the raw sentence equals a sentence of a document file |
  | `normalised-whitespace` | 7 | equal after normalisation |
  | `annotated-sheet join` | 192 | the row is a fragment of a split sentence; the full sentence (via `orig_index`) is in a document |
  | `substring`, `none` | 0 | not needed |

**Coverage:** all 2,480 rows are dated:

- all 1,132 minutes rows, 322 press-conference rows and 1,026 speech rows;
- every dataset year from 1996 to 2022.

Two rows have their earliest occurrence in a document of a different type from their sheet.

**Cross-check:** 802 rows also occur in `docs_to_score.parquet`, which covers 2015-2026.

- For 783 of them, the corrected year equals the year of their first corpus document.
- For 18, an earlier occurrence exists in the authors' files.
- One row, a December 2015 statement sentence repeated in the minutes, is dated by the minutes' release
  (2016-01-06). That date is later, so the error is on the strict side.

**Training rows per model year** (`true` vs the literal `dataset` rule):

| Y | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023-2026 |
|---|---|---|---|---|---|---|---|---|---|
| `true` | 1,606 | 1,673 | 1,738 | 1,836 | 1,901 | 2,016 | 2,184 | 2,344 | 2,480 |
| `dataset` | 1,608 | 1,672 | 1,737 | 1,836 | 1,898 | 2,014 | 2,172 | 2,342 | 2,480 |
| rows that differ (only in `true` / only in `dataset`) | 532 / 534 | 515 / 514 | 491 / 490 | 457 / 457 | 423 / 420 | 379 / 377 | 268 / 256 | 128 / 126 | 0 / 0 |

The totals are almost the same, but about 500 rows per year differ.

**Leakage audit** (`prepare` writes `data/label_year_audit.json`). A training row of model Y counts as a leak when its
text (4+ words) also appears verbatim in a `docs_to_score.parquet` document dated Y or later.

| Y | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `true` | 21 | 18 | 23 | 23 | 29 | 24 | 30 | 12 | 8 | 6 | 5 | 4 |
| `dataset` | 491 | 473 | 455 | 422 | 392 | 353 | 251 | 130 | 8 | 6 | 5 | 4 |

Under `true`, every one of these rows comes from a document dated before Y; the sentence is simply repeated later.
They are 60 distinct sentences, 55 after normalising case and punctuation (the full list is in the audit file), of
three kinds:

- statement and directive boilerplate quoted again in later minutes, for example "Consistent with its statutory
  mandate, the Committee seeks to foster maximum employment and price stability.";
- stock minutes phrases, for example "Market-based measures of inflation compensation remained low";
- Vice Chair Clarida repeating his 2020 framework-review sentences in 2021 speeches.

The audit also counts rows whose earliest corpus occurrence is dated Y or later (`first_<rule>`). Under `true` there
are 1-3 per year for 2016-2023 and none after, all generic phrases whose source is an older document outside the
corpus. For 2015 that count equals the leak count and says nothing, because the corpus starts in 2015.

**Other rules**, kept for comparison:

- `dataset`: dataset year <= Y-1 (Amendment 2 taken literally);
- `redated`: max(dataset year, first `docs_to_score.parquet` year, 2020 for COVID sentences) <= Y-1 (the interim
  audit rule).

Select one with `--label-year`, or set `CHRONO_LABEL_YEAR`:

- local: `python nlp/run_local.py --label-year dataset`
- HiPerGator: `CHRONO_LABEL_YEAR=dataset bash hpg/submit_nlp.sh`

Models, scores and merged tables record the rule. Models trained under another rule are retrained, and `merge`
refuses to mix rules.

**Checks.** `prepare` stops when:

- `label_dates.parquet` is missing (under `true`);
- its row count differs from the dataset's;
- any dataset row (split, index, orig_index, sentence) is missing from it or matches more than once;
- its label or year disagrees with the dataset's.

`submit_nlp.sh` checks that the file is present before it queues anything. Each model's `metrics.json` records:

- `label_selection`: the rows used, the dated and undated rows used or excluded, the latest source date used, and
  the leakage count;
- the sha256 of `label_dates.parquet`.

## Documents scored: `data/text_corpus/docs_to_score.parquet`

5,225 documents, 4 MB. Columns: `doc_id, source, date, year, text, meeting, n_words`.

| source | text | n |
|---|---|---|
| speech | Board speeches (body before the footnotes) | 828 |
| statement | FOMC statement release body | 97 |
| minutes | FOMC minutes, substantive sections | 94 |
| presser_doc | press-conference transcript, Chair's turns | 79 |
| presser_answer | one Chair answer in the Q&A (`doc_id` = answer_id) | 2,026 |
| presser_question | the reporter question(s) before that answer (`q_<answer_id>`, for H1-Q) | 2,026 |
| presser_statement | the same-day statement (identical to the `statement` row) | 75 |

The 2015 documents (74) exist only to warm up the v2 signal; model 2015 scores them. See "2015" below.

The file was built with `export`, from the v2 corpus (`speeches.parquet`, `fomc_docs.parquet`) and the
press-conference segmentation (`answer_map.parquet`, `statements.parquet`, `meetings.parquet`):

```
python nlp/chrono_stance.py export --v2-corpus <dir with speeches.parquet> --presser-text <dir with answer_map.parquet>
```

## Run it on HiPerGator: one command

Do this once (log in yourself; Duo):

```bash
ssh <gatorlink>@hpg.rc.ufl.edu
```

```bash
mkdir -p /blue/ai-workshop/$USER && cd /blue/ai-workshop/$USER
```

```bash
git clone -b review/strategy-01 https://github.com/savioxavier/gator-quant-hacks.git && cd gator-quant-hacks
```

If the clone already exists (for example from the audio job), update it instead:

```bash
cd /blue/ai-workshop/$USER/gator-quant-hacks && git pull
```

Then train and score everything:

```bash
bash hpg/submit_nlp.sh
```

That submits four chained jobs, each starting only if the previous one succeeded (`--dependency=afterok`):

| job | where | what |
|---|---|---|
| `chrono_prepare` | CPU, hpg-default | builds the conda env on /blue if missing (`hpg/setup_nlp.sh`), downloads the labels, checks the label ids and `label_dates.parquet`, caches the 11 base models (2014-2024; 2014 is the base of model 2015) and the Punkt data |
| `chrono_train` | GPU array 0-35, 4 at a time, 1 RTX PRO 6000 each | one (year, seed) fine-tune per task, 2015-2026 x 3 seeds |
| `chrono_score` | GPU array 0-11, 4 at a time | one year per task, 2015-2026 |
| `chrono_merge` | CPU | merged tables |

Options:

- B200 instead of RTX PRO 6000: `GPU_PROFILE=b200 bash hpg/submit_nlp.sh` (B200 queue is long)
- fewer GPUs at once: `CONC=2 bash hpg/submit_nlp.sh`
- other paths: export `CHRONO_ROOT`, `HF_HOME`, `CHRONO_ENV` or `NLP_GROUP` first (see `hpg/nlp_env.sh`)

Defaults: account and QOS `ai-workshop`; env `/blue/ai-workshop/$USER/envs/chrono` (Python 3.12, torch 2.11.0
cu128, transformers 5.18.0, the same versions as the local smoke test); outputs `/blue/ai-workshop/$USER/chrono`;
Hugging Face cache `/blue/ai-workshop/$USER/hf`. GPU jobs run with `HF_HUB_OFFLINE=1`.

Watch: `squeue -u $USER`; logs are in `nlp/logs/`. Rerunning `bash hpg/submit_nlp.sh` is safe: finished models are
skipped and only missing ones train. To build the env by hand first:

```bash
srun --account=ai-workshop --qos=ai-workshop --partition=hpg-default --cpus-per-task=4 --mem=16gb --time=01:00:00 bash hpg/setup_nlp.sh
```

## Run it on the local RTX 5090

From the repo root, with a Python that has torch (cu128), transformers 5.18, nltk 3.10.3, pandas and pyarrow:

```
python nlp/run_local.py
```

It runs `prepare`, then the 36 fine-tunes, 2 processes at a time on the one GPU (`--concurrency N` to change),
then scores each year and merges. It is resumable; rerun the same command after an interruption. Outputs go to
`nlp/work/` (git-ignored) unless `CHRONO_ROOT` or `--root` says otherwise. Set `HF_HOME` if the Hugging Face
cache should not live in the user profile.

The power-limit guard on the 5090: training draws about 250-300 W with two processes (peak 476 W for a few
seconds while scoring). Capping the card at 450 W (`nvidia-smi -pl 450`, needs an administrator shell) is optional
and is left to the machine's owner.

Single steps, for debugging:

```
python nlp/chrono_stance.py prepare
python nlp/chrono_stance.py train --year 2020 --seed 42
python nlp/chrono_stance.py score --year 2020
python nlp/chrono_stance.py merge
```

## Runtimes

Measured on the RTX 5090 (smoke test, 2026-10-03, year 2020 under the earlier `dataset` rule, 1,712 training and
302 validation sentences):

- one epoch takes about 9 s per process with two processes sharing the GPU;
- loading and saving add about 7 s per model;
- scoring one year's documents (439 documents, 13,505 sentences) takes about 5 s per seed in fp32.

Projected full runs:

| | fine-tunes (36, at most 8 epochs each) | scoring (12 years) | total |
|---|---|---|---|
| local 5090, 2 processes | about 15-25 min | about 5 min | about 20-30 min |
| HiPerGator, 4 RTX PRO 6000 | about 10-20 min of GPU time after the jobs start | about 5 min | about 30-45 min including env build and downloads (first run), plus queue time |

Early stopping usually ends a run before epoch 8, so expect the low end.

## Outputs (under the work root)

| file | content |
|---|---|
| `data/labels.parquet`, `data/label_check.json` | the labelled sentences with their source dates, the label-id evidence, the label-dates check, training rows per year |
| `data/label_year_audit.json` | training rows and leakage counts per model year under each rule, and the leaked sentences under the rule in use |
| `models/<Y>/seed_<S>/` | fine-tuned model (safetensors) and `metrics.json`: train rows, label years, base model and revision, validation macro-F1, best epoch, epoch history |
| `scores/<Y>.parquet` | one row per sentence: averaged and per-seed probabilities, label, roster flag |
| `scores/<Y>_docs.parquet` | one row per document: `n_sentences, share_hawk, share_dove, share_neut, score`, plus `score_excl_roster` |
| `scores/doc_scores_chrono.parquet` | all years concatenated (the v2 T1-T4 input) |
| `scores/presser_answers_chrono.parquet` | per answer: `score`, `hawk`, `dove`, `neut`, `question_score` |
| `scores/presser_meetings_chrono.parquet` | per meeting: `statement_score` (roster excluded, as registered), `qa_mean` (answers with at least one sentence), `H1 = qa_mean - statement_score`, plus `statement_score_incl_roster`, `qa_mean_ge40w`, `qa_pooled`, `q_mean` |

`merge` also copies the three merged tables and `merge_meta.json` to `data/text_corpus/chrono_scores/`. It refuses
to do so when any merged year was scored with fewer seeds, fewer epochs or a document subset (a smoke test); use
`--no-publish` for those.

## 2015

The v2 corpus includes 2015 only to warm up the decay and z-score. The clarification to Amendment 2 scores those
documents by the same rule with Y = 2015: base `chrono-bert-v1-20141231`, labels whose source document is dated
before 2015-01-01 (1,606 rows under `true`). 2015 is therefore part of every default run (local and HiPerGator).
To run only the test years 2016-2026:

- locally: `python nlp/run_local.py --years 2016-2026`
- on HiPerGator: `YEAR0=2016 bash hpg/submit_nlp.sh`
