# Projects / datasets / repos for FOMC press-conference analysis (part 1)

Checked 2026-10-03 via GitHub API, raw.githubusercontent, Hugging Face API.

## A. Multimodal FOMC press conference repos

### reecehuff/Lets-Face-It
- https://github.com/reecehuff/Lets-Face-It  stars 3, created 2023-03-23, pushed 2023-04-11, no license file.
- Unofficial (student) replication of Curti & Kazinnik (2023, JME 139:110-126) "Let's Face It".
- Code: core/face.py uses DeepFace emotion (7 classes) + DeepFace.verify Facenet cosine to keep only frames where the chair's identity is verified; yt_2_frames.py samples a frame every 2 s from YouTube videos (pytube); emotions_vs_returns.py joins with SPY 1-min Kaggle data.
- Bundles the data part of the Gorodnichenko-Pham-Talavera "Voice of Monetary Policy" (AER 2023) package: TVOMP/Main/data/raw/fomc_all.xlsx, FED_QA_timing.dta, media_all.xlsx, policyshocks_swanson.xlsx, shadowrate.xls. Original package: openICPSR project 178302 (https://www.openicpsr.org/openicpsr/project/178302/version/V1/view) -- returned HTTP 403 to fetch, UNVERIFIED directly.
- Downloaded and inspected fomc_all.xlsx + FED_QA_timing.dta (scratch raw/):
  - QA_identifier: 692 answers, 36 press conferences 2011-04-27 .. 2019-06-19 (Bernanke 12, Yellen 16, Powell 8), YouTube video_id, press_conf_time, datetime_start/datetime_end per answer (wall clock ET).
  - per-answer text scores: hawkish/dovish word counts, BERT, FinBERT probs, RoBERTa, cosine, human avg score; answers_emotion = per-answer voice emotion label (happy 375, sad 282, neutral 30, angry 3).
  - statement and remarks level scores too; fomc_policy sheet: 68 meetings 2011-2019 with target change and chair.
- Reusable: answer-level timestamps 2011-2019 = ready-made alignment table to join with Databento 1-s bars; DeepFace pipeline as baseline.

### LucasKSJang/fomc-voice-volatility
- https://github.com/LucasKSJang/fomc-voice-volatility  MIT, stars 0, created/pushed 2026-09-28.
- 30 Powell pressers 2022-01-26..2025-12-10, Fed YouTube "Introductory Statement" audio 16 kHz; 68 acoustic features (RMS, ZCR, centroid, band energies, Praat F0, MFCC) for first 10 s / 60 s; SPY 1-s bars (Polygon, not redistributed).
- Headline r=0.42 (loudness vs 60-s realized vol) vanished: placebo pre-speech vol r=0.45; controlling for pre-speech vol coef 0.25 -> 0.02 (p=0.62); family-wise max-T p=0.27; yearly corr flips sign; YouTube encode bitrate (about 100 vs 190 kbps Opus) explains 32% of loudness variance; start-time clock assumed.
- Reusable: config/events.csv (YouTube IDs + measured bitrate), robustness scripts (placebo window, max-T permutation), list of pitfalls. Strong negative-result template.

### matibonfanti/fomc-thesis ("Beyond Words")
- https://github.com/matibonfanti/fomc-thesis  no license ("not currently licensed for reuse"), created 2025-06-04, pushed 2026-08-03, stars 0.
- Bocconi BSc thesis 2025. Pipeline: yt-dlp download -> faster-whisper large-v3 word timestamps -> diarization -> ~20 s speaker-consistent clips -> emotion2vec/emotion2vec_plus_large (speech emotion) + R1-Omni (HumanMLLM, audio+video emotion) -> join to ES, ZT, ZQ futures ticks; ZQ policy-surprise control; horizon sweep. Results not published.
- Reusable (read-only, ask author): stage layout, ZQ surprise construction, horizon sweep design.

### marcus800/Money-Talks-Can-Transformers-Listen
- https://github.com/marcus800/Money-Talks-Can-Transformers-Listen  no license, stars 0, single push 2024-03-22.
- "A New High-Frequency Dataset, Task, and Analysis" predicting FOMC press conference influence on S&P and FX; built from fomc-hawkish-dovish + MONOPOLY; price data from Dukascopy. Contains LLMSuite (LSTM, softmax regression, GPT-3.5, TinyLlama/Llama2 fine-tune + DPO data), train/eval CSVs for FX and S&P.
- Reusable: instruction-format training CSVs (check provenance), evaluation harness. Low maturity.

### monopoly-monitory-policy-calls/MONOPOLY
- https://github.com/monopoly-monitory-policy-calls/MONOPOLY  stars 6, created 2022-07-14, pushed 2022-10-30, no license file.
- ACM Multimedia 2022 (Mathur et al.). Videos of monetary policy press conferences from 6 central banks (Fed, BoE, BoC, ECB, RBNZ, SARB), 2009-2022, Google Drive links per bank; "price data" CSVs per country (US only as .numbers); dataloader.py, main.py (MPCNet baseline). Dataset said to be 180 GB (search-result summary of Adobe/UMD pages, not opened).
- Reusable: Fed video set (convenience mirror), multi-bank data for pretraining/transfer; labels are daily-ish risk/price-movement, coarse.
