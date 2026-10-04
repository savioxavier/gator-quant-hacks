# Press-conference transcript provenance (reviewer item 3b)

**Question.** v2 scores the text of each FOMC press conference and trades it at the next session's open. Does that
text faithfully represent what was said live?

**Status.** A read-only check. Nothing here reruns a backtest or the stance model. Every number comes from committed
files, recomputed by `results_2/provenance/provenance_check.py`, which writes `results_2/provenance/provenance_by_meeting.csv` (one row per conference, 95
rows), `results_2/provenance/provenance_passages.csv` (every listed passage, with short excerpts), `results_2/provenance/document_timing_check.csv` and
`results_2/provenance/provenance_summary.json`. No wall-clock time is claimed anywhere. Times are either media seconds (seconds into a
recording) or calendar days.

## 1. Short answer

- **What v2 scores.** One document per conference, the `presser_doc` rows of `data/text_corpus/docs_to_score.parquet`:
  the Chair's turns (opening statement and answers) of the official transcript PDF, as extracted by the v2 corpus
  build. There are 79 of them, 2015-03-18 to 2026-09-16, with 505,294 tokens in total. 99.73% of the scored tokens
  match Chair turns of the official transcript, and 99.31% of the transcript's Chair tokens appear in the scored text
  (pooled). Each document enters v2's consensus at the first session strictly after the conference date. On the
  committed in-sample signal file this reproduces exactly: maximum difference 2.2e-16 over 2,453 sessions.
- **Against the speech.** 62 of the 79 conferences have a recording that matches the transcript. For those, Whisper's
  transcript of the official video contains a median 94.3% of the scored tokens (range 88.8% to 97.3%, pooled
  93.9%). Unmatched passages of 8 or more tokens cover 0.85% of the scored tokens in these conferences. 168 of their
  212 passages fall in gaps where the recording had speech but the ASR returned nothing. No passage of 8 or more
  tokens that the ASR does not hear and that lacks an audio gap contains a lexicon word.
- **Where the scored text differs from what was said.** These differences come from how the scored text was built or
  edited, not from the Fed's speech:
  - 11 written footnote corrections ("Chair Powell intended to say ...") are scored as if spoken, in 10 conferences.
  - 721 tokens of reporter or moderator speech, in 28 runs over 22 conferences, are scored as the Chair's. 6 more
    conferences carry only a stray speaker label.
  - 2,569 Chair tokens are missing, in 8 conferences. This includes the whole opening statement of 2018-09-26.
  - 282 editor insertions in square brackets appear in 53 conferences.
- **Not checkable against speech.** 15 conferences have captions only: Yellen 2015-2017 and Warsh 2026. The captions
  are the transcript text forced-aligned to the video, so they are not independent. Two recordings fail the check:
  the 2023-06-14 video is the 2023-07-26 conference (Note 2), and the 2020-03-15 ASR covers only 27% of the scored
  text.
- **Size.** Treat every affected sentence as flipped, and every missing sentence as added back with an extreme label.
  The definite text defects can then move a document's score by at most 0.328, on 2018-09-26. The bound is zero for
  45 of 79 documents and above 0.05 for 6. For scale, the standard deviation of the 79 press-conference scores is
  0.068. These are worst-case bounds; the actual effect would need a rescoring, which this check does not do.

## 2. Sources and what each can show

| Source | What it is | Independent of the transcript? | Coverage |
|---|---|---|---|
| Scored text | `presser_doc` rows of `docs_to_score.parquet`, built from the v2 corpus (`fomc_docs.parquet`, `text_core`; that builder is not in this repository) | no, it is derived from the PDF | 79 conferences |
| Transcript PDF | `data/fomc_pressers/transcripts/`; text from `backtests/presser/text/transcripts_utf8/` (2016+) or the PDF's `.txt` (before 2016); segmented into turns with the committed rules of `backtests/presser/text/code/segment.py` (the script reproduces the committed `turns.parquet` exactly for 75/75 conferences) | it is the reference | 95; 95/95 PDFs hash-identical to the manifest's copies of the Board files |
| Captions | `data/fomc_pressers/captions/<id>.vtt`, the Board's WebVTT track | **no**: it is the transcript forced-aligned to the video. It contains the title line, the speaker labels, the editor's brackets (such as "pose[s]") and 4 of the 16 footnotes of captioned scored conferences | 83 (72 of the 79); 83/83 hash-identical to the manifest |
| ASR | `data/fedpress_features_local/meetings/<id>/asr/words.parquet`: Whisper large-v3-turbo on the official video, no prompt (`initial_prompt` null), word times in media seconds | **yes**, but imperfect: the package's WER proxy against the edited transcript is 0.054-0.124 on matching recordings | 64 Powell conferences |
| Committed alignment outputs | `backtests/presser/text/align_meetings.parquet`, `turn_times.parquet` (transcript vs captions, 75 conferences); `_done/turns.json` (wer_proxy, match_frac, timed_frac, vtt_check) and `turns/words.parquet` (64 conferences) | - | reported beside the recomputation |

## 3. Method

Tokens use the feature package's normaliser (`_align.norm_tokens`), word by word. Two token lists are aligned with
`difflib.SequenceMatcher` (autojunk off). A passage is a gap of at least 8 tokens between matching blocks. The full
rule list is in the script's header.

- **Fixed before the per-meeting tables were computed:**
  - the four sources and the measures (coverage of scored text and Chair transcript text by captions and by ASR);
  - the 8-token passage rule;
  - the frozen strategy-01 lexicon as a materiality screen (40 words; no negation rule here);
  - the 0.80 ASR mismatch threshold, which is the package's own `min_matched_frac`;
  - the 2k/(N - k) score bound.
- **Seen before writing the script:**
  - the done-marker match_frac and wer_proxy of all 64 meetings, including 0.14 for 2023-06-14 and 0.41 for
    2020-03-15;
  - a text search showing "intended to say" footnotes and "MICHELLE SMITH" labels inside the scored text;
  - the inventory of bracketed insertions.
- **Added after the first full run, to describe differences more accurately:**
  - counting non-chair text only in runs of at least 4 tokens (the first version counted 1-2-token matches at turn
    boundaries);
  - treating curly double quotes like straight ones, which had hidden the 2015-09-17 footnote;
  - the explanations of unheard passages (ASR audio gap, ASR segment order) and of extra ASR words (repetition loop,
    segment order);
  - the listing of missing Chair text and of each footnote;
  - the split score bounds.

None of these choices feeds a strategy; they change only how differences are counted and labelled.

## 4. Results

### 4.1 What exactly v2 scores

| Measure | Value |
|---|---|
| Scored documents / tokens | 79 / 505,294 |
| Scored tokens in Chair turns of the transcript (pooled) | 99.73% |
| Scored tokens in reporter or moderator turns | 0.16% (721 tokens in 28 runs of at least 4 tokens) |
| Scored tokens not in any transcript turn | 0.11% (footnotes, 15 footnote-call digits, fragments) |
| Chair transcript tokens present in the scored text (pooled) | 99.31% |
| Next-session rule (in-sample consensus `C_T2`, `C_LEXALL` rebuilt from the document scores and dates) | max abs difference 2.2e-16 and 4.4e-16 over 2,453 sessions |

The press-conference study (H1 and its diagnostics) scores a different text: the answer and question rows
(`presser_answer`, `presser_question`), built from the committed segmentation. Those rows contain no speaker label
(0) and no footnote text (0), so the defects below concern v2's `presser_doc` only.

### 4.2 Coverage by captions and ASR

| Measure (scored conferences) | Value |
|---|---|
| Captions available | 72 of 79 |
| Scored text found in captions | median 99.91%, min 98.91% (lowest: 2019-06-19 98.91%, 2016-06-15 98.93%) |
| Committed transcript/caption match rate (`align_meetings.match_rate_all`, 75 conferences) | median 99.98%, min 99.41% |
| ASR available / matching the transcript | 64 / 62 |
| Scored text found in ASR, 62 matching recordings | median 94.32%, range 88.75%-97.27%, pooled 93.95% |
| Chair transcript tokens found in ASR (recomputed) | median 94.34%, range 88.68%-97.34% |
| Package `match_frac`, all transcript words (done markers) | median 93.78%, range 89.48%-96.56% |
| Package `wer_proxy` | median 0.0779, range 0.0537-0.1240 |
| Package `vtt_check`, ASR vs caption timing (media seconds, not a wall clock) | median of the meetings' median absolute offsets 2.1 s (56 meetings) |

### 4.3 Unmatched content (62 matching recordings)

**Scored words that the ASR does not have** (passages of 8 or more tokens): 212 passages, 3,477 tokens, which is 0.85%
of the 407,828 scored tokens in these conferences.

| Explanation | Passages | Notes |
|---|---|---|
| ASR audio gap: speech was present and the ASR returned nothing | 168 | text such as "how fast we go it's far more important to think what is ..." (2022-12-14) |
| Found elsewhere in the ASR (ASR segments out of order) | 5 | |
| No ASR audio gap (possibly not spoken) | 39 (555 tokens, 26 conferences) | 6 footnotes (100 tokens), 3 editor descriptions in brackets (29 tokens; for example "gesturing with hands apart equidistant from the middle", 2019-01-30), 1 moderator line (8 tokens), and 29 passages (418 tokens) that read as speech the ASR skipped while stretching word times (for example "if you if you were if you weren't"). 0 lexicon words; 10 numeric tokens |

**ASR words inside a Chair turn that the transcript does not have:** 32 passages, 555 tokens.
- 13 occur elsewhere in the transcript (ASR segment order).
- 7 are Whisper repetition loops (for example "-and we see -and we see ...").
- 12 (118 tokens) are other: false starts and repetitions removed in editing, number formats ("one and a half" for
  "1 1/2"), or ASR insertions.

Differences shorter than 8 tokens, mostly single-word ASR errors and edits, make up the rest of the roughly 6% of
scored tokens that the ASR does not match.

### 4.4 Material differences

| Type | Count | Tokens | Lexicon words | Conferences | Why |
|---|---|---|---|---|---|
| Editorial footnote scored as speech | 11 of the 16 footnotes in these transcripts | 207 | 0 | 2015-09-17, 2016-06-15, 2017-12-13 (2), 2018-03-21, 2018-06-13, 2018-12-19, 2019-06-19, 2019-09-18, 2019-12-11, 2020-06-10 | the PDF's footnote ("1 Chair Powell intended to say that the median projection is 1.9 percent next year") sits in the extracted text, spliced into a sentence; it is a written correction, not speech. Of the 7 with a recording, 6 sit where the ASR has no audio gap, which is consistent with no speech there; the 2020-06-10 footnote falls in an ASR gap |
| Reporter or moderator text scored as the Chair's | 28 runs; 40 speaker labels | 721 | 11 | 22 with runs (largest: 2019-03-20, 95 tokens of a question; 2019-10-30, 3 runs, 122 tokens; 2025-06-18, 55; 2025-03-19, 50) plus 6 with only a label | 39 of the 40 labels follow an em dash ("So—BRIAN CHEUNG."), and one has a colon ("MICHELLE SMITH:"), which the v2 extraction did not split. The text study's segmentation does split them |
| Chair text missing from the scored text | 10 passages | 2,569 | 13 | 2018-09-26 (the whole opening statement, 1,062 tokens), 2019-09-18 (2 answers, 389), 2026-03-18 (2 answers, 353), 2023-07-26 (232), 2025-10-29 (171), 2024-03-20 (131), 2024-09-18 (117), 2019-12-11 (114) | answers that follow an unsplit reporter label are lost with it; 2018-09-26 starts at an answer |
| Editor's bracketed insertions | 282 | 481 | 1 | 53 | words added for clarity ("[percent]", "[inflation]", "pose[s]"); not spoken in that form; also present in the captions |
| Recording does not match the transcript | 2 | - | - | 2023-06-14 (the published video is the 2023-07-26 conference; ASR coverage 15.3%; no captions); 2020-03-15 (ASR coverage 27.4%; 2,963 ASR words for a full-length recording of 2,536 s; cause not established) | the June 2023 transcript cannot be checked against speech |

**Bounds on a document's stance score** (share hawkish minus share dovish). With k affected and m missing sentence
units out of N, the bound is 2(k + m)/(N - k). Sentence counts are approximate (regex splitter; m from the
document's tokens per unit).

| What is counted | Median | Max | Documents above 0.05 |
|---|---|---|---|
| Definite defects: footnotes, non-chair text, missing Chair text | 0.000 | 0.328 (2018-09-26) | 6 |
| Footnotes and non-chair text only | 0.000 | 0.074 (2019-10-30) | 1 |
| Plus bracketed insertions | 0.016 | 0.128 (2021-12-15) | - |
| Plus possibly unspoken passages, 62 matching recordings | 0.022 | 0.175 (2022-06-15) | - |
| Plus every passage the ASR does not hear, 62 matching recordings | 0.040 | 0.299 (2022-06-15) | - |

For comparison, the standard deviation of the 79 v2 press-conference scores is 0.068. A bound concerns one document
out of 1,098, and its weight in the consensus decays with a 20-session half-life. The six documents with a bound above
0.05 fall in the selection window (2018-09-26, 2019-09-18, 2019-10-30), the validation window (2023-07-26,
2024-03-20) and the out-of-sample window (2026-03-18).

### 4.5 Conferences without captions or ASR

| Group | Conferences | Second source |
|---|---|---|
| No captions (7 of 79) | 2022-12-14, 2023-06-14, 2023-07-26, 2023-11-01, 2023-12-13, 2024-03-20, 2025-12-10 | ASR for all 7; 2023-06-14 is the wrong recording |
| No ASR (15 of 79) | Yellen 2015-03-18, 2015-06-17, 2015-09-17, 2015-12-16, 2016-03-16, 2016-06-15, 2016-09-21, 2016-12-14, 2017-03-15, 2017-06-14, 2017-09-20, 2017-12-13; Warsh 2026-06-17, 2026-07-29, 2026-09-16 | captions only (not independent) |
| Neither | none of the 79; among the 16 conferences before 2015, which v2 does not use, 5 Bernanke conferences (2011-04-27, 2011-11-02, 2012-01-25, 2012-06-20, 2013-12-18) | - |

Classes over the 79: 62 checked against independent ASR; 15 captions only; 2 recordings that do not match.

### 4.6 Statements, minutes and speeches

v2 dates every document and makes it tradable at the first session strictly after that date, whatever its release
time (`results_2/provenance/document_timing_check.csv`).

**Verified from committed files:**
- **Document ids and dates agree:** statements 97/97, press conferences 79/79, speeches 827/828. The exception is
  `speech_waller20260928a`, dated 2026-09-29.
- **Minutes carry their release date,** 19-24 days after the meeting (median 21).
- **The next-session rule holds on the in-sample consensus,** for both the stance and lexicon legs: 846 documents up to
  2024-10-01 rebuild `C_T2` and `C_LEXALL` to 2.2e-16 and 4.4e-16.
- **The press-conference corpus's same-day statements equal the v2 statement text** (75/75).
- **Release times:** 128 speeches were released after 16:00 ET and 25 are dated on non-session days. All of them enter
  at the next session. 2 speeches and 2 press conferences (2020-03-03, 2020-03-15) have no release time.

**Not verified:**
- the public posting time of each document. The corpus takes dates and times from the Board's feeds, which were not
  re-checked;
- the 252 documents after 2024-10-02 against a signal file, because only out-of-sample returns are committed;
- the text of statements, minutes and speeches against the Board's pages (not in the repository);
- the posting date of each transcript PDF. v2 uses the conference date, and the PDF is published later;
- that the posted video equals the live broadcast. By the Brightcove upload record (a record, not a broadcast clock),
  76 of 79 scored videos were uploaded on the conference day; 2022-06-15 was uploaded 2 days later, and 2024-03-20 and
  2025-01-29 1 day later.

## 5. The source-equivalence assumption

v2 assumes that the Chair's words in the official transcript PDF, as extracted into the v2 corpus, are the words
markets heard live at the press conference. It makes them tradable at the next session's open after the conference
date, although the PDF is an edited record published later.

- **Where the assumption is supported.** For 62 of the 79 conferences, an independent machine transcript of the
  official video supports it at the passage level.
- **Where it is untested.** For 17 conferences it is not tested here: Yellen 2015-2017, Warsh 2026, the mismatched
  2023-06-14 video and the partial 2020-03-15 recording.
- **What it does not cover.** The scored text departs from the transcript's Chair turns in documented ways: footnotes,
  reporter text, missing answers and bracketed insertions. The assumption does not cover these, and they are listed
  per conference in `results_2/provenance/provenance_by_meeting.csv` and `results_2/provenance/provenance_passages.csv`.

## 6. What remains unverified

- **Live timing.** No exact live wall-clock time is claimed. The posted video may differ from the broadcast, and the
  ASR was run on the posted video.
- **The ASR itself.** Its accuracy has no human reference. "ASR audio gap" and "no ASR audio gap" are inferences from
  word times, not proof of what was said.
- **The effect on the score.** Only bounds are given. Measuring the actual effect would mean rescoring corrected text,
  which this check deliberately does not do.
- **The cause of the defects.** The v2 corpus builder (`fomc_docs.parquet`) is not in the repository, so the cause is
  inferred from text patterns (em-dash labels, footnote placement).
- **Other documents.** Posting times and page fidelity are unverified for statements, minutes and speeches.

## 7. Files

| File | Content |
|---|---|
| `results_2/provenance/provenance_check.py` | the check; `python results_2/provenance/provenance_check.py` from the repository root; exits 2 when an input is missing or when it is started elsewhere |
| `results_2/provenance/provenance_by_meeting.csv` | 95 rows. **Main columns:** `in_v2_scored`; `scored_share_in_chair_turns`; `chair_transcript_share_in_scored`; `caption_cov_scored`; `asr_cov_scored`; `pkg_match_frac`; `pkg_wer_proxy`. **Defect counts:** `scored_footnotes_included`, `scored_leak_tokens`, `chair_tokens_missing_from_scored`, `scored_bracket_insertions`; the `chair_unheard_*` and `scored_*` passage counts by explanation. **Score bounds:** `score_change_bound_*`. **Summary:** `flags`, `provenance_class` |
| `results_2/provenance/provenance_passages.csv` | every passage: comparison (`scored_vs_asr`, `transcript_vs_asr`, `scored_vs_transcript`, `transcript_vs_scored`, `footnote`), kind, explanation, token counts, lexicon and numeric tokens, excerpts of at most 12 tokens |
| `results_2/provenance/document_timing_check.csv` | dates, release times and the next-session check by document type |
| `results_2/provenance/provenance_summary.json` | the headline numbers above |
