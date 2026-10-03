# Walk-forward stance model (hawkish / dovish / neutral)

This folder trains the stance model that replaces the gated FOMC-RoBERTa, then scores every Fed document the
strategies use with it. The spec was fixed before any v2 or H1 return was computed:

- `research/fedspeak_v2/HYPOTHESIS_v2.md`, Amendment 2
- `research/fed_presser_plan/DEVIATION_D1_stance_model.md`

## What it does

For each test year Y from 2016 to 2026:

1. **Base model:** `manelalab/chrono-bert-v1-<min(Y-1, 2024)>1231` (MIT licence). It is a ModernBERT-base encoder,
   pretrained only on text up to the end of that year. A new 3-class classification head is added.
2. **Labels:** `gtfintechlab/fomc_communication` (CC BY-NC 4.0, not gated), train and test splits combined.
   Only rows with year <= Y-1 are used. The labels end in 2022, so 2023-2026 all use the full 2,480 rows.
3. **Training:**
   - 15% stratified validation split (seed 0), used for early stopping on macro-F1;
   - lr 2e-5, batch 16, max length 256, at most 8 epochs, patience 2, weight decay 0.01, 10% warmup;
   - seeds 42, 43 and 44, so 33 models in total.
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

## Label years (read before the full run)

The dataset's `year` column is not the year of the sentence's source document for most rows. Examples: sentences
about COVID-19 carry years 1998-2014, and a sentence from a February 2022 Board speech ("the Fed hasn't started
raising rates or reducing the balance sheet") carries 2004. `prepare` matches every labelled sentence (8+ words)
verbatim against `docs_to_score.parquet` and writes `data/label_year_audit.json`. Under the literal rule
(`dataset`), the rows with dataset year <= Y-1 whose text first appears in a document dated Y or later are:

| test year | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024-2026 |
|---|---|---|---|---|---|---|---|---|---|
| rows | 453 of 1,672 | 431 | 401 | 365 | 330 | 220 | 118 | 1 | 0 |

So under `dataset` the 2016-2022 models have seen labelled sentences from later documents, including sentences of
the documents they score, and cannot be called walk-forward clean. 2023-2026 are unaffected (one row, a December
2022 minutes sentence released in January 2023).

The `redated` rule uses max(dataset year, year of the first corpus document containing the sentence, 2020 for
COVID/coronavirus sentences). It only removes rows, and it errs on the strict side: a generic sentence (for example "Broad equity price indexes fell sharply over the intermeeting period on net.") that also appeared before 2015 is moved to its first corpus year. It cannot find sentences whose source document is outside the
corpus (the corpus covers 2015-2026 statements, minutes, press conferences and Board speeches). Choosing it is a
team decision for the deviation log. Select it with `CHRONO_LABEL_YEAR=redated` (local:
`CHRONO_LABEL_YEAR=redated python nlp/run_local.py`; HiPerGator: `CHRONO_LABEL_YEAR=redated bash hpg/submit_nlp.sh`).
Models, scores and merged tables record the rule; models trained under the other rule are retrained, and `merge`
refuses to mix rules.

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

The 2015 documents (74) exist only to warm up the v2 signal. The registered model years are 2016-2026, so by
default nothing scores them. See "2015" below.

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
| `chrono_prepare` | CPU, hpg-default | builds the conda env on /blue if missing (`hpg/setup_nlp.sh`), downloads the labels, checks the label ids, caches the 11 base models (2014-2024; 2014 only for the optional 2015 year) and the Punkt data |
| `chrono_train` | GPU array 0-32, 4 at a time, 1 RTX PRO 6000 each | one (year, seed) fine-tune per task |
| `chrono_score` | GPU array 0-10, 4 at a time | one year per task |
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

It runs `prepare`, then the 33 fine-tunes, 2 processes at a time on the one GPU (`--concurrency N` to change),
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

Measured on the RTX 5090 (smoke test, 2026-10-03, year 2020, 1,712 training and 302 validation sentences):

- one epoch takes about 9 s per process with two processes sharing the GPU;
- loading and saving add about 7 s per model;
- scoring one year's documents (439 documents, 13,505 sentences) takes about 5 s per seed in fp32.

Projected full runs:

| | fine-tunes (33, at most 8 epochs each) | scoring (11 years) | total |
|---|---|---|---|
| local 5090, 2 processes | about 15-25 min | about 5 min | about 20-30 min |
| HiPerGator, 4 RTX PRO 6000 | about 10-20 min of GPU time after the jobs start | about 5 min | about 30-45 min including env build and downloads (first run), plus queue time |

Early stopping usually ends a run before epoch 8, so expect the low end.

## Outputs (under the work root)

| file | content |
|---|---|
| `data/labels.parquet`, `data/label_check.json` | the labelled sentences, the label-id evidence, rows per year |
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

The v2 corpus includes 2015 only to warm up the decay and z-score. The amendment names test years 2016-2026, so
by default 2015 documents get no score. The same rule extends to 2015 without change: base
`chrono-bert-v1-20141231`, labels up to 2014. If the team decides to use it:

- locally: `python nlp/run_local.py --years 2015-2026`
- on HiPerGator: `YEAR0=2015 sbatch --array=0-2 hpg/train_nlp.sbatch`, then `YEAR0=2015 sbatch --array=0 hpg/score_nlp.sbatch`, then `MERGE_YEARS=2015-2026 sbatch hpg/merge_nlp.sbatch` (the prepare job already caches the 2014 base model)
