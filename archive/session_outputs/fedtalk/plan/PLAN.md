# Fed Press Conference Signals: Research Plan

Checked 2026-10-03. Numbers in [brackets] point to the sources at the end. [L] means our own computation; the notes are in `scratchpad/fedtalk/` (data_markets, verify_literature, verify_models).

## 0. Two facts that change the premise

- **Powell is no longer chair.** His last press conference was 2026-04-29. Kevin Warsh gave the 2026-06-17, 07-29 and 09-16 press conferences, according to the official transcripts and the Board page [12]. News reports say he was sworn in on 2026-05-22, but no Fed release confirms that date. They also say he has dropped forward guidance and may not hold a press conference after every meeting. Face and voice baselines for the current chair rest on 3 events.
- **The sample is 95 press conferences, not about 110.** They run from 2011-04-27 to 2026-09-16: Bernanke 12, Yellen 16, Powell 64, Warsh 3. Two of them were unscheduled, in March 2020, so 93 were scheduled [5][L]. Together they hold about 2,226 chair answers of 40 words or more [L].

## 1. Bottom line

**What is known.** The press conference moves markets while the chair speaks, and since 2022 it has carried more policy news than the statement: surprise volatility is 4.1 bp for the press conference against 3.5 bp for the statement [5]. Text tone, voice and face each show small effects measured during the event:

- **Face:** 1 SD of negative expression goes with about -0.5 bp in SPY over the next 3 minutes, and the effect is gone within 5-10 minutes [1].
- **Voice:** about 1 bp on impact, then nothing more in the following minute [2].
- **Daily drifts:** the multi-day face and voice drifts rest on 32-36 events with 90% confidence intervals and have never been tested out of sample [2][3].

**What is not known.** No study shows a predictive signal from face, voice or text that survives costs. The one published press-conference timing rule with a P&L is Gomez-Cram and Grotteria's [4]: trade in the direction of the statement-window move through the press conference. It earned about 12.7 bp per event gross on stocks over 2011-2020, with no costs modelled, and it stopped working after that [6][7]. Our rerun on USMPD gives an S&P futures correlation of +0.46 for 2011-19 and -0.07 for 2020-26 [L].

**Speed.** Prices react to scheduled macro releases within milliseconds [9]. A student pipeline will sit roughly 8-20 s behind the room. That figure is an estimate and has not been measured. Only continuation that lasts past about 30-60 s, or that carries into the close or the next day, is worth testing.

**A plausible edge.** At best a text-led, chair-normalised measure of how far the press conference departs from the statement. Trade it in ES, where one round trip costs about 3% of a 2-minute standard deviation, against 31-54% in ZT, ZF, ZN and SR3 [L]. Face and voice will probably add little and should have to earn their place.

**Key risk.** At n=93 the smallest correlation we can detect is 0.29, and t=2 needs a per-event Sharpe of 0.21. Confirming a Sharpe of 0.2 live would take about 100 events, or 12.5 years [L]. Pre-registration and a sealed test set are what keep this honest.

## 2. Pre-registered hypotheses

Freeze these in a git commit and on OSF before anyone looks at the sealed test set (2024-01 onward, about 22 press conferences).

- **H1 (primary).** Hawkishness surprise per answer: the answer's stance minus the same-day statement's stance, z-scored within chair. It predicts the ES return from answer end +30 s to +5 min, with a negative sign, net of one tick plus fees. Controls: the statement-window move and the ES move during the answer.
- **H2.** The text gap aggregated over the whole press conference predicts the ES and 2-year-yield return from press-conference end to 16:00 ET, and to the next day's close.
- **H3.** Vocal arousal adds to H1. Arousal is measured against the chair's own past Q&A, with the word content regressed out.
- **H4.** Upper-face negative affect adds to H1. This is tested only if the Curti-Kazinnik same-window association replicates first.
- **H5.** The combined model beats text-only out of sample.
- **Benchmarks:** the statement-window rule [4], and the USMPD statement surprise [5].

H1 is the only primary test. It must clear t > 3 [18]. Every other hypothesis gets Holm correction.

## 3. Model stack

Ids are as listed on Hugging Face (huggingface.co/&lt;id&gt;). NC means non-commercial. All of these run on the RTX 5090, one at a time.

| Modality | Primary (licence, size) | Cross-check | Features | Normalisation |
|---|---|---|---|---|
| Timing | Official Fed WebVTT captions (83/95) [L]; `Qwen/Qwen3-ForcedAligner-0.6B` (apache-2.0, 0.92B; vendor-reported 37.5 ms timing error, 5-min chunks) for the other 12 | WhisperX 3.8.6 | Answer start/end, word times | Wall-clock offset per meeting |
| Live ASR | `openai/whisper-large-v3-turbo` (MIT, 0.81B) via faster-whisper | `nvidia/parakeet-tdt-0.6b-v2` (CC-BY-4.0; needs WSL2) | Live words | Long-form earnings WER is about 13 for both [21] |
| Chair isolation | Transcript speaker labels | `pyannote/speaker-diarization-community-1` (CC-BY-4.0, gated) + `speechbrain/spkrec-ecapa-voxceleb` (apache-2.0) | Chair-only segments | Drop chunks where the sources disagree |
| Voice | `audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim` (CC-BY-NC-SA, 165M) | `3loi/SER-Odyssey-Baseline-WavLM-Multi-Attributes` (MIT); `emotion2vec/emotion2vec_plus_large` | Arousal, dominance, valence; pitch in semitones and speech rate/pauses via praat-parselmouth (GPL-3.0); um/uh via `nyralabs/CrisperWhisper` (NC) | z vs the chair's past Q&A (median/MAD); valence with word content regressed out (valence mostly re-reads the words [14]) |
| Face | `py-feat/face_multitask_v2` via py-feat 2.1.3 (research-only weights) after InsightFace `buffalo_l` chair ID (NC models) | OpenFace 3.0 (CMU NC); MediaPipe Face Landmarker (Apache-2.0, CPU) | Upper-face AU1/2/4/5/6/7, valence-arousal, head pose, blink rate gated on head pitch | Speech/reading masks; residualise on pose and lighting; z vs the chair's past pressers; partial pooling for Warsh |
| Text stance | `manelalab/chrono-bert-v1-<Y-1>1231` (MIT, 150M), fine-tuned walk-forward on `gtfintechlab/fomc_communication` (CC BY-NC) + ~300 of our own blind-labelled answers | `gtfintechlab/FOMC-RoBERTa` (CC BY-NC, gated; F1 only 0.55 on presser sentences [8]); `Moritz-Pfeifer/CentralBankRoBERTa-sentiment-classifier` (MIT); Loughran-McDonald word lists | (hawkish - dovish)/sentences per answer; gap vs statement and vs previous presser | Within chair; changes, not levels |
| Text extras | `Qwen/Qwen3-Embedding-8B` (apache-2.0) | `FutureMa/Eva-4B-V2` evasiveness (apache-2.0; vendor-reported), checked against FOMCBench human-labelled splits | Novelty vs statement diff; evasiveness | Within chair |

Rules:

- **Local LLM scorers.** A scorer such as Qwen3.8-27B may score only meetings after its measured knowledge cutoff. Masking does not stop hindsight [13].
- **Face API.** The Azure emotion API used in [1] is retired [20], so the face results are rebuilt with open tools, not replicated exactly.
- **FOMC labels.** The Hugging Face copy of the labelled FOMC data has no document-type column. Take the press-conference subset from the GitHub repo.

## 4. Data plan

- **Video and transcripts.** All 95 MP4s are on federalreserve.gov (Brightcove, mostly 960x540, 82.4 h, about 65 GB) and are public domain [17][L]. The 95 transcript PDFs and 83 WebVTT files are already on disk. Do not download from YouTube (its terms forbid it) or C-SPAN (non-commercial only).
- **2011-2019 answers.** The answer-level wall-clock times for 692 answers, plus voice and text scores, are in the Gorodnichenko replication data [2][23]. Use them as an alignment check.
- **Event labels.** USMPD (free) gives statement windows (-10/+20 min) and press-conference windows (-10/+60 min) for every event [5].
- **Market data.** Databento GLBX.MDP3, volume-ranked `.v.0` continuous contracts, 13:30-16:30 ET on all event days. Use 12:00-16:15 for 2011-12, when the statement came out at about 12:30. Shift the window for the two 2020 special days. Free cost queries give [L]:
  - ohlcv-1s for ES, ZN, ZT, ZF, 6E and SR3: **$8.60**.
  - ohlcv-1m for the same contracts: $0.33.
  - bbo-1s for ES, ZN and ZT, to measure spreads during the press conference: $3.6.
  - The full bundle, adding SR3/GE strips, NQ/6J/GC and VX 1-minute: **about $28**.
  - Use GE before 2018-05. Skip tbbo and MBO until a signal survives.
- **Alignment.** There is no official wall-clock anchor. Published work assumes video zero = 14:30:00: Gomez-Cram and Grotteria's timestamps equal the caption cue plus 14:30 [4][L]. The greeting falls 0.6-144 s into the video, so estimate an offset per meeting from headline timestamps (Bloomberg at the UF library), using the minimum lag across several quotes. Use market cross-correlation only as a diagnostic, because setting offsets from it would leak the target. Run the main tests on 1-minute data.
- **Event list.** Build it from the USMPD press-conference sheet, joined to the Fed calendar [11].

## 5. Pipeline

1. **Ingest.** MP4 to a 16 kHz mono WAV plus frames at 10-15 fps. Log the source, codec and bitrate. Bitrate alone explained 32% of loudness in one public repo [16].
2. **Segment.** Split into opening statement and question/answer turns using caption cues and transcript labels. The 12 videos without captions get forced alignment plus diarization.
3. **Features.** Compute voice features on 3-15 s chair chunks, face features on chair frames that pass the quality gates, and text features per sentence. Everything must be causal: no whole-video normalisation and no centred smoothing.
4. **Aggregate.** Per answer, and per rolling 30 s and 60 s window. Each row is stamped with the time it became known, which is the segment end plus the measured latency.
5. **Store.** Parquet, one row per meeting × segment. Pin model hashes and package versions. A `config.yaml` drives each run, the git commit ID is written into every output, and features are rebuilt from raw files in one command.
6. **Real time (later).** Record federalreserve.gov/live-broadcast.htm on an NTP-synced PC, then run streaming ASR (about 3.3 s latency [25]), then text scoring. Voice and face features join on 2-3 s windows. The output is a paper-trade log.

## 6. Evaluation

- **Targets.** Two kinds, kept apart:
  - *Contemporaneous:* the return over each answer window. This is a validity check, not a trading result.
  - *Predictive:* the return from end + L to end + L + H, with latency L ∈ {10, 30, 60 s} and horizon H ∈ {1, 5, 15 min, press-conference end, 16:00 close, next-day close}.
- **Splits.** Use leave-one-meeting-out on 2011-2023, fitting every scaler, baseline and threshold inside each fold. Also run leave-one-chair-out, testing on Warsh. The sealed 2024-26 set is opened once.
- **Inference.**
  - Meeting-block bootstrap or wild cluster bootstrap. The answers are clustered, so the effective sample is closer to 93 events than to 2,226.
  - Holm correction for secondary tests, and the deflated Sharpe ratio for anything chosen by search [18].
  - Placebos: shift timestamps by ±2/5/10 min, shuffle answers within each meeting, and score the reporters' voices.
- **Costs and latency.** Assume one ES tick of about 0.32 bp at 7,776.5 plus fees, so a round trip is about 0.35-0.5 bp, plus measured bbo-1s spreads and one extra tick of slippage. ES depth drops sharply around FOMC releases [24].
- **Benchmarks.** The statement-window rule, the 14:00-14:30 ES move, the USMPD statement surprise, and text-only versus combined.
- **Power.** On the sealed set (n≈22), t=2 needs a per-event Sharpe of about 0.43. Treat the sealed test as a sign check, not as proof [L].

## 7. Roadmap and gates

- **Weeks 1-2 (Oct 5-16).**
  - Set up the venv, download 10 press conferences, run the pipeline end to end.
  - Run a free meeting-level text test against the USMPD moves.
  - **Gate 1:** at least 98% of chair-labelled seconds really are the chair; word boundaries are within 50 ms of the captions; features have ICC ≥ 0.8 between the original and a 64 kbps re-encode.
- **Oct 28.** Record the live Warsh press conference to measure stream delay and check for PROGRAM-DATE-TIME tags. Do not trade it.
- **Weeks 3-4 (Oct 19-30).** Run all 95 press conferences and buy the Databento bundle after you confirm the spend. Rate 200-300 voice and face chunks blind to the market.
  - **Gate 2:** text stance lines up with the answer-window ES move. If face fails to replicate [1], drop face. If any measure scores below CCC 0.3 against the human ratings, drop it.
- **Week 5 (Nov 2-6).** Freeze the pre-registration and run H1-H5.
  - **Gate 3:** H1 reaches t > 3 net of costs under leave-one-meeting-out, and the sealed set shows the same sign with a positive net mean. Otherwise, write it up as research and stop the trading work.
- **Paper trading.** Remaining 2026 meetings: Oct 27-28 and Dec 8-9. 2027 meetings: Jan 26-27, Mar 16-17, Apr 27-28, Jun 8-9, Jul 27-28, Sep 14-15, Oct 26-27, Dec 7-8 [11]. Warsh may skip press conferences at some meetings, so check each one.
  - **Gate 4:** no real money before at least 8 frozen paper-traded events with a positive net mean. Even then, use one-contract size, since live proof takes years.

## 8. Risks and mitigations

- **Overfitting and forking paths.** Use one primary test, a sealed set, the deflated Sharpe ratio and placebos. A related warning from our own data: the hourly pre-FOMC drift scored 0.49 Sharpe in-sample, depended on 2020 and 2022, and was negative in 2024-26. The literature also finds that drift faded after 2015 [10].
- **Post-publication decay.** Check every result by year. Expect regime flips like the one after 2020 [6][7].
- **LLM look-ahead.** Use time-stamped ChronoBERT models. Only use an LLM score for meetings after that model's measured cutoff. The 2022 labels carry the annotators' hindsight, so report results with and without our own blind labels.
- **Measurement validity.** Emotion models are trained on podcasts or acted speech, and LLM-judged "emotion" had little grounding in the acoustics [15]. Facial expressions are not reliable readouts of emotion [19], so model facial behaviour, not "fear". Mask speech and reading, and require human-rating checks.
- **Broadcast delay and alignment.** Measure the delay live, estimate an offset per meeting, and test at a 1-minute resolution.
- **Chair change.** Build per-chair baselines with partial pooling and a leave-one-chair-out test. Text is the only channel likely to transfer across chairs. Face and voice for Warsh stay exploratory until he has 8 or more press conferences.
- **Ethics and law.**
  - Use Fed videos only; they are public domain, cite the Board [17].
  - Identify only the chair's face and voice, and throw away reporter embeddings.
  - Most face, voice and text weights are research-only or non-commercial (NC). Before trading real money, switch to the permissive path: Whisper, Qwen, the 3loi WavLM model, emotion2vec+, parselmouth, MediaPipe, ChronoBERT and CentralBankRoBERTa. This is not legal advice.

## 9. Budget and first steps

**Budget:**
- Databento: about $28 one-off. Cost queries are free; do the purchase yourself.
- Compute: local GPU. My rough estimate is about 6 GPU-hours for face at 10 fps, plus a few hours for ASR and voice.
- APIs: $0. No cloud model is needed.
- Disk: about 70 GB.
- Run `C:\LLM\unload.cmd` before GPU jobs.

**Tomorrow:**
1. Create a new venv (torch 2.8 cu128, whisperx, py-feat, praat-parselmouth) and put ffmpeg on PATH. Only the 5090 is visible to nvidia-smi.
2. Download 10 press conference MP4s from federalreserve.gov: 5 Powell, 3 Warsh, 2 Yellen.
3. Score text stance on the 95 transcripts and regress it on the USMPD press-conference-window moves (free, about one day).
4. Draft the H1 pre-registration.
5. Decide on the $28 Databento bundle.

## Sources

[1] Curti & Kazinnik WP: https://conference.nber.org/conf_papers/f156264/f156264.pdf
[2] Gorodnichenko, Pham & Talavera: https://eml.berkeley.edu/~ygorodni/VoiceMP.pdf
[3] Alexopoulos et al.: https://www.bankofcanada.ca/wp-content/uploads/2022/05/swp2022-20.pdf
[4] Gomez-Cram & Grotteria: https://lbsresearch.london.edu/id/eprint/2203/1/SSRN-id3613702.pdf
[5] USMPD: https://www.frbsf.org/wp-content/uploads/wp2025-30.pdf, https://www.frbsf.org/wp-content/uploads/USMPD.xlsx
[6] Narain & Sangani: https://www.ijcb.org/journal/v22n1/market-impact-fed-communications-role-press-conference
[7] Byun, Fees, Jacobson & Walker: https://margaretjacobson.github.io/CV/BFJW-Fed-Fine-Tune.pdf
[8] Trillion Dollar Words: https://arxiv.org/abs/2305.07972
[9] Chordia, Green & Kottimukkalur: https://ideas.repec.org/a/oup/rfinst/v31y2018i12p4650-4687..html
[10] Kurov, Wolfe & Gilbert: https://ideas.repec.org/a/eee/finlet/v40y2021ics1544612320315956.html
[11] FOMC calendar: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
[12] https://www.federalreserve.gov/aboutthefed/bios/board/default.htm, https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20260617.pdf
[13] Lopez-Lira, Tang & Zhu: https://arxiv.org/html/2504.14765v2
[14] Wagner et al.: https://arxiv.org/abs/2203.07378
[15] Listening to the Fed (abstract only): https://doi.org/10.3390/jrfm19080613
[16] https://github.com/LucasKSJang/fomc-voice-volatility
[17] https://www.federalreserve.gov/disclaimer.htm
[18] Harvey, Liu & Zhu: https://www.nber.org/papers/w20592; deflated Sharpe: https://papers.ssrn.com/abstract=2460551
[19] Barrett et al.: https://www.psychologicalscience.org/publications/emotional-expressions-reconsidered-challenges-to-inferring-emotion-from-human-facial-movements.html
[20] Azure Face retirement: https://learn.microsoft.com/javascript/api/overview/azure/cognitiveservices-face-readme?view=azure-node-latest
[21] Open ASR long-form: https://huggingface.co/datasets/hf-audio/leaderboard_longform
[23] Replication data mirror: https://github.com/reecehuff/Lets-Face-It
[24] Rosa: https://ideas.repec.org/a/eee/ecolet/v138y2016icp5-8.html
[25] Whisper-Streaming: https://arxiv.org/abs/2307.14743

Unverified: the 8-20 s latency, broker fees, Warsh's swearing-in date and his communication changes (news reports only), and all vendor-reported model numbers.
