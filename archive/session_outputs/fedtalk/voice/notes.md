# Voice track: models and toolkits for FOMC press-conference audio (checked 2026-10-03)

Status key: [V] opened and checked at the URL; [S] secondary source only; [U] could not open / not checked.

## 0. Facts that change the plan

- The chair is no longer Powell. Powell's term as chair ended 2026-05-15 (Fed release:
  https://www.federalreserve.gov/newsevents/pressreleases/other20260515a.htm [V]). Kevin Warsh was sworn in
  2026-05-22 [S: https://seekingalpha.com/news/4596371-kevin-warsh-is-sworn-in-as-federal-reserve-chair].
  The Jul-29 and Sep-16 2026 transcripts are titled "Chairman Warsh's Press Conference"
  (https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20260916.pdf,
  https://www.federalreserve.gov/mediacenter/files/FOMCpresconf20260729.pdf [V]). Sep-16 2026: +25 bp to 3.75-4.00%.
  The FOMC calendar lists a press conference for every 2026 meeting so far (Jan, Mar, Apr, Jun, Jul, Sep); next meetings
  Oct 27-28 and Dec 8-9 (https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm [V]). Press coverage says
  Warsh may not hold a press conference after every meeting [S: https://www.jpmorgan.com/insights/markets-and-economy/economy/kevin-warsh-first-federal-reserve-meeting-as-chair-june-2026].
  Result: a per-speaker baseline for the CURRENT chair rests on 3 press conferences. Powell has about 66
  (2018 quarterly, then every meeting through Apr 2026). This is a cold-start problem.
- Official transcripts label every turn ("CHAIR POWELL.", "CHAIRMAN WARSH.", "MICHELLE SMITH.", reporter names) [V, same PDFs].
  Aligning the official text to the audio gives chair-vs-reporter labels almost for free. Diarization then becomes a cross-check.
- The transcripts are edited: 0 occurrences of "um"/"uh" in the Sep-2025 or Sep-2026 transcripts [V, local grep].
  Measuring disfluency therefore needs verbatim ASR.
- Warsh press conferences are shorter: 4,623 words (Sep-2026) and 7,008 (Jul-2026), against 8,957 for Powell Sep-2025.
  That is 18 / 23 / 36 chair turns [V, local count].
- Video: the Fed page embeds a Brightcove player (account 66043936001; Sep-2025 video id 6379710022112) and links the Fed YouTube
  channel [V, page HTML https://www.federalreserve.gov/monetarypolicy/fomcpresconf20250917.htm]. yt-dlp is installed locally.
  ffmpeg is NOT on PATH.
- Local machine right now: nvidia-smi shows only an RTX 5090 32 GB (driver 616.92). The gqh-systematic venv has no audio stack
  (no torch, transformers, pyannote, opensmile and so on). Build a separate venv.

## 1. Prior Fed voice work (only what the voice method needs)

- Gorodnichenko, Pham, Talavera, "The Voice of Monetary Policy", AER 113(2) 2023 [S: https://ideas.repec.org/p/nbr/nberwo/28592.html].
  Method from the working paper (local copy literature/gpt_voice_berkeley.txt) [V]:
  - 180 librosa features (128 mel, 40 MFCC, 12 chroma) fed to an MLP.
  - Trained on ACTED RAVDESS+TESS: 84% in-domain accuracy, 5 classes.
  - 692 answers from Bernanke, Yellen and Powell, Apr 2011 to Jun 2019; 12-26 answers per press conference (mean 19).
  Modern models trained on naturalistic speech should be strictly better than this measurement.
- Alexopoulos, Han, Kryvtsov, Zhang (BoC SWP 2022-20, local copy) [V]: voice index = mean Praat F0 per sentence, de-meaned per
  speaker. This supports per-speaker normalisation of F0. The same paper cites Curti & Kazinnik, who did not find significant voice or face effects.

## 2. ASR with word timestamps

Primary benchmark source: the Open ASR Leaderboard results CSVs pulled from the space's own data repos.
- https://huggingface.co/datasets/hf-audio/open-asr-leaderboard-results (english_short_latest.csv) [V]
- https://huggingface.co/datasets/hf-audio/leaderboard_longform (longform_latest.csv) [V]

The short-form numbers use the leaderboard's newer "cleaned" sets, so they differ from older model-card numbers.
Long-form earnings21/22 (earnings calls) is the closest public proxy for press conferences.

| model (HF id) | license | size | short avg WER | long-form earnings21 / earnings22 | RTFx (long) | last modified | Windows |
|---|---|---|---|---|---|---|---|
| openai/whisper-large-v3 | apache-2.0 | 1.54B | 5.78 | 9.71 / 13.16 | 68.6 | 2024-08-12 | yes (faster-whisper/CTranslate2) |
| openai/whisper-large-v3-turbo | mit | 0.81B | 6.36 | 9.84 / 13.10 | 148 | 2024-10-04 | yes |
| nvidia/parakeet-tdt-0.6b-v2 | cc-by-4.0 | 0.6B | 4.70 | 10.75 / 13.25 | 956 | 2026-06-29 | NeMo: Linux-first, use WSL2/Docker; no Windows statement found |
| nvidia/parakeet-tdt-0.6b-v3 | cc-by-4.0 | 0.6B | 4.86 | 9.96 / 14.58 | 1003 | 2026-08-05 | same |
| nvidia/canary-qwen-2.5b | cc-by-4.0 | 2.5B | 4.43 | 9.60 / 13.59 | 16 | 2026-04-21 | same; trained on clips of at most 40 s (card) |
| nvidia/canary-1b-v2 | cc-by-4.0 | 1.0B | 5.71 | n/a | n/a | 2026-08-31 | same |
| Qwen/Qwen3-ASR-1.7B | apache-2.0 | 2.35B (HF total) | 4.31 (-hf variant) | not on long-form board | n/a | released 2026-01-28 | transformers backend yes; vLLM needs WSL2 |
| CohereLabs/cohere-transcribe-03-2026 | apache-2.0 | 2B | 4.67 | 8.70 / 12.66 (best open long-form) | 418 | not checked | [U] |

Model-card numbers (older protocol):
- parakeet-tdt-0.6b-v2 card: avg WER 6.05, Earnings-22 11.15; single pass up to 24 min [V].
- parakeet-tdt-0.6b-v3 card: 6.34 / 11.42 [V].
- canary-qwen-2.5b card: 5.63 / 10.42 [V].
https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2 , https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3 , https://huggingface.co/nvidia/canary-qwen-2.5b

Conclusion: on long-form earnings calls the open models sit within about 1.5 WER points of each other. Pick by
tooling and timestamps, not by WER.

### Toolkits
- WhisperX v3.8.6 (2026-05-25), BSD-2-Clause, 24k stars. https://github.com/m-bain/whisperX [V]
  - Pipeline: batched faster-whisper, then wav2vec2 phoneme forced alignment, then pyannote diarization (needs an HF token and
    acceptance of speaker-diarization-community-1).
  - PyPI pins torch~=2.8.0, pyannote-audio>=4, ctranslate2>=4.5 [V: https://pypi.org/pypi/whisperx/json].
  - Limitation: tokens like "2014." or "£13.60" do not align. Fed speech is full of numbers, so normalise numbers to words before alignment.
  - README speed claim: 70x real time for large-v2, under 8 GB VRAM.
- faster-whisper v1.2.1 (2025-10-31), MIT. https://github.com/SYSTRAN/faster-whisper [V]
  - README benchmark, large-v2 on an RTX 3070 Ti: fp16 1m03s / 4.5 GB, against openai/whisper 2m23s; int8 batch 8 takes 16 s.
  - Needs CUDA 12 + cuDNN 9. Has word_timestamps=True and a Silero VAD filter. Windows NVIDIA libraries come via Purfview's whisper-standalone-win.
- RTX 50xx (sm_120): use CUDA 12.8+ builds. Older CTranslate2/cuBLAS raise CUBLAS_STATUS_NOT_SUPPORTED. WhisperX upgraded to
  torch 2.7.1 / CUDA 12.8 / CTranslate2 >= 4.5 for Blackwell [S: https://github.com/m-bain/whisperX/issues/1211].
- Qwen/Qwen3-ForcedAligner-0.6B (apache-2.0, 0.92B HF total, 2026-01-30): word timestamps for up to 5 min per call.
  The vendor table reports accumulated average shift (ms, lower is better). English: 37.5 against WhisperX 92.1 and NeMo NFA 107.5.
  On 300 s concatenations: 58.6 against 227.2 and 226.7. https://huggingface.co/Qwen/Qwen3-ASR-1.7B [V]
  This is the best way to time-stamp the official transcript chunk by chunk.
- Verbatim (fillers): nyrahealth/CrisperWhisper is cc-by-nc-4.0 and transcribes um/uh with word timestamps. The card says it is
  superseded by nyralabs/CrisperWhisper2.0_large (license "other", 2026-08-13).
  https://huggingface.co/nyrahealth/CrisperWhisper [V card text]
- Montreal Forced Aligner: conda-forge install; Windows appears to go through Docker [V: https://montreal-forced-aligner.readthedocs.io/en/latest/installation.html]. Not needed if the Qwen aligner works.
- NeMo moved to NVIDIA-NeMo/Speech, v3.0.0. Python >= 3.12, PyTorch >= 2.7. Docs focus on Linux and make no Windows statement
  [V: https://github.com/NVIDIA/NeMo redirect page]. PyPI classifier says "OS Independent" [V].

## 3. Diarization / isolating the chair

- pyannote/speaker-diarization-community-1: CC-BY-4.0, gated (clicking through shares contact information; free), pyannote.audio 4.x, last modified 2025-09-29.
  DER (%) for 3.1 / community-1 / precision-2 (cloud, paid):
  - AMI-IHM 18.8 / 17.0 / 12.9
  - DIHARD3 21.4 / 20.2 / 14.7
  - VoxConverse 11.2 / 11.2 / 8.5
  - AliMeeting 24.5 / 20.3 / 15.2
  - AISHELL-4 12.2 / 11.7 / 11.4
  Offers "exclusive" diarization (no overlaps) designed for merging with ASR. Runs offline from a local clone.
  https://huggingface.co/pyannote/speaker-diarization-community-1 [V]
- pyannote.audio 4.0.7 (2026-06-30), MIT. Needs ffmpeg and torchcodec; Python >= 3.10, torch >= 2.8.
  Speed on an H100: community-1 takes 31 s per hour of audio (AMI); precision-2 takes 14 s.
  https://github.com/pyannote/pyannote-audio , https://pypi.org/pypi/pyannote.audio/json [V]
- pyannote/speaker-diarization-3.1: MIT, gated, pure PyTorch (no onnxruntime). DER: VoxConverse 11.3, AMI 18.8, DIHARD3 21.7. https://huggingface.co/pyannote/speaker-diarization-3.1 [V]
- pyannote/speaker-diarization-precision: cloud API only (pyannoteAI key). Not local. https://huggingface.co/pyannote/speaker-diarization-precision [V]
- nvidia/diar_streaming_sortformer_4spk-v2 (cc-by-4.0) and diar_sortformer_4spk-v1 (cc-by-nc-4.0): capped at 4 speakers
  [V card]. A press conference has 15-25 speakers, so Sortformer is not suitable here.
- Speaker verification for "is this the chair?": speechbrain/spkrec-ecapa-voxceleb, apache-2.0, EER 0.80% on VoxCeleb1-test.
  https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb [V]
  Enrol the chair from his opening statements and accept a chunk only if cosine similarity is above a calibrated threshold.

## 4. Speech emotion recognition (SER)

Dimensional models (arousal / valence / dominance), all trained on MSP-Podcast (naturalistic podcasts). These are the most relevant.

- audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim. https://huggingface.co/audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim [V]
  - cc-by-nc-sa-4.0, "research purpose only". 165M params; HF last modified 2024-09-19; 447k downloads.
  - MSP-Podcast v1.7. Outputs A/D/V in about 0..1 plus a 1024-d pooled embedding. ONNX export on Zenodo 6221127.
  - Paper: Wagner et al., TPAMI 45(9) 2023, https://arxiv.org/abs/2203.07378 [V PDF]
    - Released 12-layer model: valence CCC .638.
    - 24-layer parent: arousal .745, dominance .634 on MSP-Podcast; cross-corpus IEMOCAP arousal .663, dominance .518, valence .448.
  - Key caveats from the same paper:
    - Valence success comes from IMPLICIT LINGUISTIC information. It works on TTS-synthesised speech without emotional intonation.
    - Models are fair across gender groups but NOT across individual speakers.
    Both caveats argue for speaker normalisation and a lexical control.
- 3loi/SER-Odyssey-Baseline-WavLM-Multi-Attributes. https://huggingface.co/3loi/SER-Odyssey-Baseline-WavLM-Multi-Attributes [V]
  - MIT, 0.32B, 2024-06-12. Odyssey 2024 challenge baseline.
  - CCC Test3: V .577, D .577, A .405. Development set: V .652, D .688, A .579.
- tiantiaf/wavlm-large-msp-podcast-emotion-dim (Vox-Profile). https://huggingface.co/tiantiaf/wavlm-large-msp-podcast-emotion-dim [V]
  - OpenRAIL; the card's out-of-scope list includes "No commercial use". 0.32B, 2025-08-10.
  - Accepts clips of 3-15 s at 16 kHz.
  - Vox-Profile paper, https://arxiv.org/abs/2505.14648 [V raw HTML], Table 4, MSP-Podcast v1.12 dev (A / V CCC):
    - WavLM-L .585 / .665
    - Whisper-L .588 / .645
    - HuBERT-L .585 / .650
  - The training pipeline is the top solution of IS2025 SER. Sibling models: tiantiaf/whisper-large-v3-msp-podcast-emotion-dim (1.54B),
    tiantiaf/wavlm-large-voice-quality (labels incl. hesitant, monotone, authoritative, booming, staccato),
    tiantiaf/wavlm-large-speech-flow (fluency F1 .806, disfluency-type F1 .691 in Table 4).
- Interspeech 2025 challenge (MSP-Podcast), attribute track. https://lab-msp.com/MSP-Podcast_Competition/IS2025/ [V]
  - Best average CCC .6076 (SAIL: V .683, A .642, D .498); baseline .5797.
  - Categorical track: best macro-F1 .4316 (NTUA); baseline .3293.
  The state of the art for naturalistic speech is therefore CCC of about .64 arousal and .68 valence, and macro-F1 of about 0.43 for categories.

Categorical models.
- emotion2vec/emotion2vec_plus_large. https://huggingface.co/emotion2vec/emotion2vec_plus_large [V]
  - About 300M params; FunASR model license, which is permissive with attribution (https://raw.githubusercontent.com/modelscope/FunASR/main/MODEL_LICENSE [V]).
  - 9 classes: angry, disgusted, fearful, happy, neutral, other, sad, surprised, unknown. Fine-tuned on 42,526 h of pseudo-labelled data.
  - No numeric emotion2vec+ table, only a radar chart ("details will be announced later").
  - The emotion2vec base paper (https://arxiv.org/abs/2312.15185 [V]) reports IEMOCAP 4-class leave-one-session-out linear probe WA 71.79 / UA 72.69.
  - Gives utterance embeddings and frame embeddings at 50 Hz. Install with pip funasr (v1.4.16, MIT).
- speechbrain/emotion-recognition-wav2vec2-IEMOCAP: apache-2.0, IEMOCAP test accuracy 78.7% (avg 75.3). Acted / scripted dyadic data. Low priority.
  https://huggingface.co/speechbrain/emotion-recognition-wav2vec2-IEMOCAP [V]
- AVOID popular acted-speech models:
  - ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition: RAVDESS only, 82% accuracy.
  - firdhokk/speech-emotion-recognition-with-openai-whisper-large-v3: RAVDESS/SAVEE/TESS, 92%.
  High in-domain accuracy on actors does not transfer to a calm official at a podium [V cards].

## 5. Prosody / paralinguistic features

- openSMILE (opensmile-python 2.6.0). https://audeering.github.io/opensmile-python/ , https://pypi.org/pypi/opensmile/json [V]
  - win_amd64 wheel on PyPI.
  - eGeMAPSv02 = 88 functionals plus LLDs: F0 in semitones, jitter, shimmer, HNR, loudness, spectral slope, formants, voiced/unvoiced segment rates.
  - LICENSE is the audEERING Research License: non-commercial only, with "personal experimentation" allowed. Commercial gain needs a licence
    (https://raw.githubusercontent.com/audeering/opensmile/master/LICENSE [V]).
  - GeMAPS paper: Eyben et al., IEEE TAC, DOI 10.1109/TAFFC.2015.2457417 [U: IEEE page blank; DOI resolves].
- Parselmouth (praat-parselmouth 0.4.7, 2025-11-27), GPL-3.0, Windows wheels. https://pypi.org/pypi/praat-parselmouth/json [V]
  Covers Praat pitch, intensity, HNR, jitter, shimmer and formants.
- Speech rate and pauses: compute from aligned word timestamps (words/s, syllables/s via a pronouncing dictionary, pause lengths
  and counts above 250 ms, articulation rate excluding pauses). This is simpler than syllable-nuclei scripts.
- Measurement robustness:
  - MP3 at 56-320 kbps keeps F0 mean and range errors below 2%; F0 skewness errors are about 7% (Fuchs & Maxwell, Speech Prosody 2016,
    https://www.isca-archive.org/speechprosody_2016/fuchs16b_speechprosody.html [V]).
  - Lossy codecs and VoIP inflate jitter and shimmer [S: https://www.science.gov/topicpages/j/jitter+percent+shimmer].
  Treat jitter and shimmer as low-trust on streamed or YouTube audio.

## 6. Audio LLMs (zero-shot tone description)

- Qwen/Qwen2-Audio-7B-Instruct: apache-2.0, 8.4B, 2025-01-12. MELD accuracy .553 (from the Qwen2.5-Omni card table). https://huggingface.co/Qwen/Qwen2-Audio-7B-Instruct [V]
- Qwen/Qwen2.5-Omni-7B: apache-2.0 (license file), 10.7B, 2025-04-30.
  - MELD .570, against WavLM-large .542.
  - Minimum GPU memory in BF16: 31.11 GB for a 15 s video. Qwen/Qwen2.5-Omni-7B-AWQ and GPTQ-Int4 exist.
  https://huggingface.co/Qwen/Qwen2.5-Omni-7B [V]
- Qwen/Qwen3-Omni-30B-A3B-Instruct: apache-2.0, 35.3B total / 3B active, 2025-09-22.
  - MMAU-v05.15.25 77.5; VoiceBench MMSU 68.1; standalone MMSU 69.0.
  - BF16 minimum 78.85 GB, so quantise. ggml-org/Qwen3-Omni-30B-A3B-Instruct-GGUF: Q4_K_M 18.56 GB + mmproj Q8_0 1.33 GB, for llama-server.
  - Audio input through llama.cpp mtmd is not tested here [U].
  https://huggingface.co/Qwen/Qwen3-Omni-30B-A3B-Instruct [V]
- Qwen/Qwen3-Omni-30B-A3B-Captioner: audio-only input, no text prompt; describes speaker emotions. The card recommends clips of 30 s or less.
  AWQ 4-bit available (cyankiwi/...).
- stepfun-ai/Step-Audio-2-mini: apache-2.0, 8.3B, 2026-02-14. https://huggingface.co/stepfun-ai/Step-Audio-2-mini [V]
  On the vendor's own StepEval-Audio-Paralinguistic benchmark: avg 80.0 (emotion 82, pitch 82, speed 74).
  Comparison averages: GPT-4o Audio 43.45, Kimi-Audio 49.64, Qwen-Omni 44.18.
- nvidia/audio-flamingo-3-hf and nvidia/audio-flamingo-next-hf (up to 30 min of audio): NVIDIA OneWay Noncommercial License [V cards].
- mistralai/Voxtral-Mini-3B-2507: apache-2.0, about 9.5 GB in bf16. Up to 40 min for understanding. No paralinguistic benchmark on the card [V].
- Evidence that audio LLMs remain weak on paralinguistics: SpeechParaling-Bench (arXiv 2604.20842) reports paralinguistic
  misinterpretation as 43.3% of errors in situational dialogue [V abstract]. Use audio LLMs only for qualitative labels and audit, not as the numeric signal.

## 7. Licence summary for a trading use

Permissive: whisper, parakeet/canary (CC-BY-4.0), Qwen3-ASR/aligner, pyannote community-1 (CC-BY-4.0), ECAPA, emotion2vec+ (attribution),
3loi WavLM (MIT), Qwen2-Audio/2.5-Omni/3-Omni, Step-Audio-2-mini.

Non-commercial: audeering msp-dim (CC-BY-NC-SA), Vox-Profile (no commercial use), openSMILE (research licence), CrisperWhisper v1,
Audio Flamingo. MSP-Podcast itself is distributed under an academic agreement [U].

Personal research is fine. Trading real money on outputs is arguably "commercial gain". Keep a fully permissive path:
3loi WavLM + emotion2vec+ + parselmouth (GPL is fine for private use) + librosa.

## 8. Recommended stacks

Environment: create a new venv (Python 3.11/3.12) with torch 2.8 cu128 wheels for the RTX 5090 (sm_120). Add ffmpeg
full-shared on PATH (needed by torchcodec/pyannote 4). Run NeMo models only under WSL2 or Docker.

PRIMARY (offline, per press conference)
1. Audio: yt-dlp from the Fed Brightcove/YouTube page. Keep the original file; make a 16 kHz mono WAV for models. Log the source, codec and bitrate.
2. Text and timing: official transcript PDF. Normalise numbers to words. Align with Qwen3-ForcedAligner-0.6B in chunks of 5 min or less,
   anchored on a faster-whisper large-v3 pass run through WhisperX 3.8.6. The transcript speaker labels give the chair's turns.
3. Chair check: pyannote speaker-diarization-community-1 (exclusive mode) plus ECAPA verification against a voiceprint enrolled from
   the opening statement. Drop chunks where the labels disagree.
4. Chunking: split each chair answer into 3-15 s VAD-bounded chunks, the input length the SER models were trained on. Aggregate per answer
   (median) and keep the chunk time series.
5. SER dimensions: audeering w2v2-L-robust-12 msp-dim (A/D/V plus a 1024-d embedding). Also store the embeddings for linear probes.
6. Prosody: per chunk, parselmouth F0 (median, 10-90 range in semitones), intensity, HNR; speech/articulation rate and pause statistics
   from word times; openSMILE eGeMAPSv02 functionals (88).
7. Categorical: emotion2vec_plus_large posteriors as a permissive-licence second view.
GPU: everything fits on the 5090 sequentially (each model under 6 GB). One press conference (about 45-60 min) should take minutes, not hours [estimate, not measured].

CROSS-CHECK
- SER: 3loi WavLM multi-attribute (MIT) and Vox-Profile WavLM / Whisper dimensional models. Report the per-chunk agreement of z-scores.
  Use a feature only if at least two models agree in sign and rank.
- ASR: nvidia/parakeet-tdt-0.6b-v2 (WSL2) or Qwen3-ASR-1.7B. Verbatim fillers: CrisperWhisper (NC licence) for um/uh rate.
- Diarization: pyannote 3.1 legacy pipeline; the transcript labels are the ground truth.
- Audio LLM audit: Qwen2.5-Omni-7B (AWQ) or Step-Audio-2-mini locally, or Qwen3-Omni GGUF Q4 through llama-server.
  Give it 30 s clips, a fixed JSON schema (confidence / hesitancy / tension / assertiveness, 1-5) and temperature 0.
  Run it twice and measure test-retest agreement. Never let it drive the numeric signal.

## 9. Per-speaker normalisation

- Normalise within each chair, separately for the scripted opening statement and for spontaneous Q&A. Read and spontaneous speech differ in rate, F0 range and SER scores.
- Baseline = the chair's Q&A chunks in the previous K press conferences (expanding window, never including the current one):
  z = (x - median_base) / MAD_base.
  - F0 in semitones relative to the baseline median.
  - Also compute within-conference deviations (x minus the conference median) for intra-conference dynamics.
- A "neutral" reference set: the chair's answers to procedural or low-stakes questions (balance sheet mechanics, etc.), chosen by
  topic from the transcript before seeing any market data. Use these to estimate the speaker's neutral point and spread.
- Cold start for Warsh (3 conferences): pool across chairs with chair fixed effects; use within-conference z-scores only. Optionally
  add pre-chair Warsh audio (2026 confirmation hearing, TV interviews) for the speaker baseline only, flagged as a different channel [U: availability not checked].
- Channel control: era dummies (2018-19 in the room; 2020-21 virtual or limited press; 2022+; the Warsh era). Check spectral features against
  codec and source changes. F0 and rate are robust; jitter, shimmer and spectral tilt are not.
- Lexical control: residualise valence on text sentiment of the same chunk, from the NLP track. TTS control: synthesise the same
  sentence with one fixed neutral TTS voice, run the SER, and subtract. The residual is "how it was said". Arousal and dominance are mostly acoustic;
  valence leaks content (Wagner et al.).
- Covariates: answer length, position in the conference (fatigue drift), question topic, reporter.

## 10. Validation on Fed audio (before touching returns)

1. Pipeline accuracy on 3 conferences checked by hand: purity of chair-labelled seconds of at least 98%; median word-boundary error
   under 50 ms on 100 spot-checked words; WER against the official text (an edited transcript inflates it).
2. Source invariance: the same conference from Brightcove, YouTube and C-SPAN, plus a 64 kbps re-encode. Keep only features with chunk-level
   ICC of at least 0.8 across sources.
3. Synthetic sanity checks: pitch shift ±2 semitones, time-stretch ±10%, gain ±6 dB. Arousal should move with pitch and rate and stay flat with gain.
4. Human ratings: 200-300 chair chunks stratified by conference, rated by 3 raters blind to markets on 1-9 SAM arousal/valence/dominance.
   Inter-rater ICC is the ceiling; report the model-vs-mean CCC. If CCC is below about 0.3, treat the measure as noise.
5. Convergent validity: audeering vs 3loi vs Vox-Profile vs an eGeMAPS-based ridge model. Opening statement vs Q&A contrast.
6. Placebo: the same features computed for reporters (and for the moderator Michelle Smith) must not "predict" anything.
7. Only then link to markets, separating:
   (a) contemporaneous: minute or second returns inside each answer window;
   (b) predictive: features available at t + latency (streamed audio is several seconds or more behind; pipeline about 1 s per 10 s chunk;
       measure both) predicting returns after t, net of costs. Also conference-level features predicting next-day returns.
   Use a time split (Powell 2018-2023 to fit, 2024-2026 to test) and conference-clustered errors. The effective N is about 70 conferences, not about 1,500 answers.
