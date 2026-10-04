# fedpress architecture

`fedpress` turns the official FOMC press-conference videos and transcripts into per-meeting feature tables:
the chair's text stance, voice and face. Every row carries `known_at`, the UTC time at which a live observer
could have known it. The defaults implement `research/fed_presser_plan/team_FINAL_PLAN.md`. The richer options
from `plan_v0.md` are config switches and are off by default.

| | Default (team plan) | Options, off by default (plan_v0) |
|---|---|---|
| Sample | Pressers at the 2016-01..2026-10 meetings: 75 held today, 2026-10-28 joins after a manifest rebuild | 2011-2015 calibration pressers (`sample.include_calibration`) |
| Clock | Whisper large-v3-turbo via faster-whisper gives the times; the transcript PDF gives the words | Official WebVTT captions (`turns.clock_source: vtt`; 83/95 meetings, 7 of the default 75 have none); WhisperX or Qwen forced alignment |
| Chair segments | Transcript speaker labels, checked by an ECAPA chair-voice gate | pyannote 3.1 / community-1 (gated; Hub terms first) |
| Text | Stance on the statement, answers and questions from the walk-forward ChronoBERT models (deviation D1: FOMC-RoBERTa is gated and inaccessible; D1a: training labels re-dated to their source documents, `manifest/label_dates.parquet`), trained by `python -m fedpress.train.stance_walkforward`; FOMC-RoBERTa as a cross-check once accessible; Loughran-McDonald, hedges, lexical novelty; CentralBankRoBERTa as agent sentiment (docs/TEXT.md) | Embedding novelty (Qwen3-Embedding), team-labelled training CSV |
| Voice (Powell only) | audeering wav2vec2 A/D/V + parselmouth F0 on chair answer chunks | emotion2vec+, 3loi WavLM, openSMILE eGeMAPS |
| Face (Powell only) | MediaPipe landmarks/blendshapes + EmotiEffLib at 1 fps; SFace identity gate (the video cuts to reporters) | py-feat (separate env), InsightFace, at 2-5 fps (docs/FACE.md) |
| Excluded | Opening remarks (used only to enrol the chair's voice and face), any LLM, Warsh voice and face | |

## 1. Layout and run model

```
fed_presser_hpg/                 the package (copy to HiPerGator)
  config.yaml                    every tunable; `--set key=value` overrides one run
  manifest/pressers.csv          95 pressers 2011-04-27..2026-09-16 (ids, clocks, Brightcove ids, sizes)
  manifest/meetings.csv          148 calendar entries (the 88-meeting panel uses has_presser)
  manifest/anchors.csv           optional per-meeting wall-clock anchors (you create it; see section 4)
  fedpress/                      config, manifest, io, log, clock, gpu, stage, models, doctor, cli
  fedpress/stages/<name>.py      one module per stage
  env/                           conda env (+ py-feat env), post-install fix-ups, activate script, Apptainer def
$FEDPRESS_ROOT  (default /blue/jie.xu/$USER/fedpress)
  meetings/<presser_id>/{raw,audio,frames,asr,turns,diarize,voice,face,text,features}/
  meetings/<presser_id>/_done/<stage>.json      done-marker (written last)
  meetings/<presser_id>/_claims/<stage>.claim   held while a worker runs that stage for that meeting
  panel/   logs/<stage>/<presser_id>.jsonl   logs/launch/<run_id>/   cache/ (HF_HOME, TORCH_HOME, models_lock.json)
```

* **Unit of work = one stage × one meeting.** `python -m fedpress.cli <stage> --index N | --date D | --id ID | --all`.
  `--index` counts within the configured sample (see `list`), so a Slurm array task maps to a meeting.
* **Idempotent.** A meeting is skipped when `_done/<stage>.json` exists and every output it lists still exists.
  `--force` redoes it. If the stage's config section (or a model it uses, or `timing`) changed since the marker
  was written, the run logs `stage.stale` and still skips. You decide whether to `--force`.
* **Requirements.** A stage runs for a meeting only when its upstream stages are done there. A disabled
  upstream stage, or one marked not applicable, counts as done. Otherwise the result is `blocked`, which is
  not an error.
* **Failures stay local.** An exception writes `_done/<stage>.failed.json` with the traceback. The run then
  moves on to the next meeting and exits with code 1 at the end. `runtime.fail_fast` makes it stop instead.
* **Shared queue.** `--claim` makes each worker take a meeting only after it creates
  `_claims/<stage>.claim` atomically (O_EXCL). Any number of workers on up to two GPUs therefore drain one
  queue, and both GPUs finish within about one meeting of each other. A claim is taken over when it is
  older than `runtime.claim_ttl_s` or when its process on the same host has died.
* **Provenance.** Each parquet file's metadata holds the stage, run id, config hash, stage fingerprint, code
  version (package version plus a hash of `fedpress/*.py`) and model revisions. The done-marker holds the same,
  plus output sizes and sha256 hashes, row counts, elapsed seconds, host and GPU.

## 2. Stages

| Stage | Res. | Requires | Reads | Writes (`io.FILES` key: path) |
|---|---|---|---|---|
| fetch | net | - | manifest row; Brightcove playback API (re-resolved: manifest URLs are signed and expired) | `video`: raw/video.mp4 (size must equal `mp4_bytes`), `transcript_pdf`, `statement_html`, [`captions_vtt`], `fetch_meta`: raw/fetch.json |
| audio | cpu | fetch | raw/video.mp4 | `audio_wav`: audio/audio_16k.wav (16 kHz mono PCM, no loudness normalisation), `audio_meta` (codec, bitrate, duration) |
| frames | cpu | fetch | raw/video.mp4 | `frames_zip`: frames/frames_<fps>fps.zip, `frames_index`: frames/frames_<fps>fps.parquet, `frames_meta`: frames/frames_meta.json (chairs in `face.chairs` only) |
| asr | gpu | audio | audio wav | `asr_words`, `asr_segments`, `asr_meta` (model, revision, parameters, RTF) |
| turns | cpu | fetch, asr (or vtt) | transcript PDF, ASR words or VTT | `turns`, `words` (aligned transcript words), `anchor`: turns/anchor.json |
| diarize | gpu | audio, turns | audio, turns | `chair_check`: diarize/chair_check.parquet |
| voice | gpu | audio, turns, diarize | audio, turns, chair_check | `voice_chunks` (chairs in `voice.chairs` only; others get a not-applicable marker) |
| face | gpu | frames, turns | frames zip (or the video, `face.source: stream`), turns | `face_frames`, `face_turns`: face/face_turns.parquet, `face_enroll`: face/enroll.json (chairs in `face.chairs` only) |
| text | gpu | fetch, turns | statement HTML, turns, words, walk-forward stance models (`fedpress.train.stance_walkforward`, run first in the GPU job) | `text_sentences`, `text_units`, `text_vectors` |
| aggregate | cpu | turns, text (+ voice, face when done, n/a, disabled or failed; waits while pending) | the above | `answers`: features/answers.parquet, `meeting`: features/meeting.parquet, `windows`: features/windows.parquet; `finalize` writes panel/*.parquet (`fedpress.dataset`) |

Resources: `net` means outbound HTTPS. Run it in a CPU job or an `srundev` session (`waves.prep`). `cpu`
stages go to CPU jobs, except `turns`, which takes seconds per meeting and runs inside the GPU wave. `gpu`
stages run in one job holding at most 2 GPUs (`waves.gpu`). They run offline (`HF_HUB_OFFLINE=1`), so
`prefetch-models` must have run first.

## 3. Table schemas

Every table goes through `ctx.write_table`, which adds the id columns and refuses a table that lacks the
timing columns or has a null `known_at`.

**Common columns (all tables from `turns` on):**

| Column | Type | Meaning |
|---|---|---|
| presser_id | str | `YYYYMMDD` |
| meeting_date | str | ISO date of the meeting's last day |
| chair | str | Bernanke, Yellen, Powell, Warsh |
| sample_role | str | study, calibration, outside |
| t_start_s, t_end_s | float64 | media seconds (video time); NaN for statement rows |
| t_end_utc | timestamp[us, UTC] | wall clock of `t_end_s` (or the statement release) |
| known_at | timestamp[us, UTC] | `t_end_utc + latency_s` |
| latency_s | float64 | `timing.latency_s` used |
| anchor_source | str | scheduled_start, video_zero_scheduled, anchors_csv:<source>, statement_release |
| anchor_unc_s | float64 | anchor uncertainty in seconds; NaN = unknown |

`fetch`, `audio`, `frames` and `asr` write raw media artefacts (`StageSpec.stamped=False`). Their tables carry
the id columns and media times but no `known_at`, because the anchor exists only after `turns`. `turns`
re-emits the timed words with `known_at` (`turns/words.parquet`). Analysis code reads only stamped tables.

**Stage-specific columns** (add others as needed and document them in the module docstring):

* `frames_index`: frame_idx, t_s, member (name inside the zip), width, height. The `face` stage records frame size on every row.
* `asr_words`: word_idx, word, t_start_s, t_end_s, prob, seg_idx. `asr_segments`: seg_idx, t_start_s, t_end_s, text,
  avg_logprob, no_speech_prob, compression_ratio. `asr_meta`: model, revision, device, compute type, decoding
  parameters, real-time factor.
* `audio_meta` (audio/audio.json): input codec, bitrate, sample rate, channels (ffprobe, else parsed `ffmpeg -i`),
  ffmpeg version and filter, output frames/duration, manifest duration gap, whole-file peak/RMS/clipping and EBU
  R128 loudness (measured, never applied). `fetch_meta` (raw/fetch.json): per file source (download, seed,
  existing), URL without its token, bytes, sha256, expected values, warnings.
* `turns`: turn_idx, speaker (label as printed), role (chair, moderator, reporter, other), is_chair, segment_kind
  (opening, question, answer, moderator, closing, other), qa_idx (question/answer pair, -1 outside Q&A), text,
  n_words, n_matched, clock_source (asr, vtt, forced), match_frac, timing_ok. A chair turn that follows a moderator
  interjection continues the current answer; reporter follow-ups get their own qa_idx.
* `words`: word_idx, turn_idx, word (transcript spelling), matched (every token matched a clock word exactly),
  timed_by (match, sub = one-to-one substitution, interp = placed between neighbours, forced), t_start_s, t_end_s,
  prob (ASR word probability).
* `anchor.json`: media_s, wall_utc, source, uncertainty_s, rule. Meeting QA goes in the turns done-marker notes:
  greeting_media_s, greeting_word, greeting_timed_by, wer_proxy, match_frac, timing_ok, clock_source, n_answers,
  vtt_check (ASR vs caption start times on words matched by both: median offset, median and p90 absolute).
* `chair_check`: chunk_idx, turn_idx, qa_idx, role, segment_kind, dur_s, label_is_chair, method, score (ECAPA cosine
  to the opening voiceprint), threshold, ecapa_ok, pyannote_speaker, pyannote_chair_frac, pyannote_ok,
  chair_verified (label says chair and every enabled voice check agrees), agree. 3 s windows tiling every turn
  that starts after the opening; known_at = window end + latency. Done-marker notes: threshold and its source,
  enrolment seconds, leave-one-out score quantiles, score medians by role, label disagreement rate.
* `voice_chunks`: chunk_idx, turn_idx, qa_idx, dur_s, identity_frac, identity_ok, identity_source, arousal,
  dominance, valence (model scale, about 0..1), f0_median_st, f0_iqr_st, f0_p10_st, f0_p90_st, voiced_frac,
  intensity_db, hnr_db, n_words, speech_rate_wps, articulation_rate_wps, pause_frac, n_pauses; options add
  `e2v_<class>`, `egemaps_<feature>` and `ser3_<dimension>`.
* `face_frames`: frame_idx, turn_idx, qa_idx, frame_w, frame_h, n_faces, face_found, box_x/y/w/h, face_h_px,
  yaw_deg, pitch_deg, roll_deg, identity_score, identity_ok, gate_ok, `bs_<blendshape>`, ex_valence,
  ex_arousal, `ex_<expression>` probabilities. A frame row has t_start_s = t_end_s = frame time. Also
  segment_kind, det_score, blur, luma, mouth_open, mouth_open_flag, reading, eye_blink, eyes_closed, track_id,
  track_age_s, head_speed_dps, gate_reason and, with py-feat, `au<NN>` and `pf_*`. `face_turns` averages gated
  chair frames per answer and per 30/60 s window (unit, window_s, unit_idx). Full list: docs/FACE.md.
* `text_sentences`, `text_units`, `text_vectors`, `answers`, `meeting`, `windows` and the panel tables are
  specified in docs/TEXT.md section 4. In short: per sentence, `<p>_p_<label>` for each scorer (`cwf`
  walk-forward ChronoBERT, `fomc` FOMC-RoBERTa, `cbr` CentralBankRoBERTa sentiment), dictionary counts and
  word-based times (known_at = sentence end + latency); per unit, `hawk` = share hawkish - share dovish of the
  primary scorer (D1), the other scores, `<p>_in_train` contamination flags (A-29) and novelty vs the
  statement; per answer, the gaps to the statement, the question score (H1-Q), running means and voice
  medians / face means; per meeting, `h1_gap` = mean answer hawk - statement hawk, with t_end_s = end of the
  last answer, so known_at is the end of Q&A plus latency.
* `panel/answers.parquet`, `panel/meetings.parquet` (the 88-meeting calendar with has_presser),
  `panel/windows.parquet`, `panel/text_units.parquet`, `panel/*_causal_z.parquet`, `panel/status.parquet`.

## 4. The known_at rule and causality

```
t_end_utc = anchor.wall_utc + (t_end_s - anchor.media_s)
known_at  = t_end_utc + timing.latency_s                    (default 30 s)
statement rows: t_end_utc = scheduled statement release (ET -> UTC, DST-aware)
```

* **One implementation.** All of it is in `fedpress/clock.py`. Stages call `ctx.stamp(df)` (media-time rows)
  or `ctx.stamp_statement(df)`. `t_end_s` is the end of whatever the row summarises: segment, chunk, frame,
  window or answer.
* **Anchor.** The video has no wall clock: the greeting comes 0.6-144 s into the video, and the streams carry
  no PROGRAM-DATE-TIME tags. `turns` writes `turns/anchor.json` with `timing.anchor.rule`:
  * `greeting_at_scheduled` (default): the media time of the chair's first transcript words, as matched to
    the audio, is set to the scheduled presser minute. This is the team plan's fallback, "first PDF-matching
    audible open". Use the ASR clock for it: on 2025-09-17 the official captions put "Good afternoon" at
    17.5 s, but the audio energy and Whisper both put it at 13.2-13.5 s. The captions' title cue absorbs the
    first seconds, so caption-based greeting times (the manifest's 0.6-144 s, median 11.8 s) run late by a few
    seconds, while later caption words agree with ASR (median offset -0.09 s, p90 0.6 s on that meeting).
  * `video_zero_at_scheduled`: video time 0 is the scheduled minute (Gómez-Cram & Grotteria).
  * A row in `manifest/anchors.csv` overrides either rule for its meeting. Columns: presser_id,
    anchor_media_s, anchor_wall_utc (ISO with offset), source, uncertainty_s. Use it for a Bloomberg headline
    time, for example.
* **Uncertainty.** Scheduled-minute anchors have unknown uncertainty (`anchor_unc_s` = NaN). The plan drops a
  meeting from predictive tests when uncertainty exceeds `timing.anchor.max_uncertainty_s` (30 s). The package
  only flags; analysis applies the filter.
* **Latency.** `latency_s` is the frozen live delay. Rows also carry `t_end_utc`, so the 60 s appendix
  (`timing.appendix_latencies_s`) needs no rerun.
* **Causality rules every stage follows:**
  1. No whole-video normalisation, smoothing centred on future data, or two-pass statistics inside a meeting.
     For example, audio is not loudness-normalised and OpenFace-style per-video calibration is not allowed.
  2. Chair enrolment (ECAPA voice embedding, face geometry) uses the opening remarks only. They precede every
     Q&A row, so enrolment never uses later material.
  3. Rolling or window features use trailing windows. A row's `t_end_s` is the window's end.
  4. Per-chair baselines (prior-meeting same-chair z-scores, 4-meeting burn-in, variance floor, robust
     median/MAD; `aggregate.baselines`) are computed at analysis time from strictly earlier meetings,
     ordered by the meeting's last `known_at`. They are never computed inside per-meeting outputs.
  5. Labels and filters that need the future (WER-proxy, timing_ok, in_classifier_train) are flags. Nothing is
     deleted.

## 5. Compute: at most 2 GPUs at once

HiPerGator facts (docs/HIPERGATOR_NOTES.md):

* B200 nodes are in `hpg-b200` with `--gres=gpu:b200:N`. HiPerGator has had no A100s since 2025-06. The
  fallbacks are `rtx6000` and `l4` (`compute.gpu_type`).
* GPUs run only under the investment QOS `jie.xu`; the group's pool counts GPUs of any type.
* A job is killed if any one of its GPUs sits at 0 % for an hour.

The package never uses more than `min(compute.max_gpus, 2, visible GPUs)` GPUs. `max_gpus > 2` is rejected
when the config is loaded.

* **Pattern A (default): one job holding up to 2 GPUs.** `python -m fedpress.cli launch asr,turns,diarize,voice,face,text --all`.
  It starts `workers_per_gpu` processes on each GPU (6 on B200, 4 on RTX PRO 6000, 2 on L4). Each process
  pins one GPU through `CUDA_VISIBLE_DEVICES` and runs `<stage> --all --claim`. The stages run one after
  another, and each stage drains the shared queue before the next one starts. The models are small (0.1-1.6
  GB of weights each), so 6 workers on a 180 GB B200 is a memory non-issue. CUDA MPS stays off
  (`compute.mps`) until `nvidia-smi` in a job shows it is usable.
* **CPU waves use the same launcher.** `launch fetch,audio,frames --all --set compute.gpu_type=cpu` runs 8
  CPU workers (profile `cpu`) on one claim queue in a CPU job or dev session.
* **Pattern B: array of 1-GPU shards.** `--array=0-K%2` (`slurm.array_throttle: 2`). Each task runs
  `<stage> --all --shard slurm` or `--all --claim`. A finished shard frees its GPU at once.

**Job scripts.** `slurm/submit_all.sh` submits the chain 01 fetch (CPU array) → 02 audio+frames (CPU array,
`aftercorr`) → 03 speech (asr, turns, diarize, voice) → 04 face → 05 stance training + text → 06 aggregate,
each later step `afterok` on the whole previous one. GPU steps run one after another (an `aftercorr` between
two GPU arrays could hold 4 GPUs at once). Each GPU step is an array of one-GPU tasks throttled to `%2`, every
task draining its group of meetings (`--shard i/N`, passed on to the launcher's workers), or with
`GPU_LAYOUT=job` one job holding `GPUS` <= 2. Settings are environment variables (`slurm/common.sh`).

**Wall-clock.** Measured on the local RTX 5090 and projected to 1 and 2 B200s in README section 9: about
30-40 min of GPU steps on 2 B200s and 45-65 min on 1 B200 for the default 75 meetings, plus queue waits.
Measured per meeting on the 5090 (2019-05-01, 41 min of video, one process, imports and model loads
included): audio 17.9 s, frames 24.7 s, asr 13.0 s, turns 0.6 s, diarize 7.9 s, voice 8.1 s, face 32.8 s;
text 7.3 s (2020-03-03); one stance fine-tune 40-69 s.

B200 queue waits are long ("expect long pending times"). With a 2-GPU cap the run is limited by the queue,
not by compute. `rtx6000` or `l4` with the same commands is the practical fallback.

## 6. Environment

* `env/environment.yml` (conda) + `env/post_install.sh`, or `uv pip install -e ".[torch,asr,turns,voice,diarize,face,text,options]"`
  with the cu128 index declared in `pyproject.toml`. `env/fedpress.def` is the Apptainer image of the same pins.
* **PyTorch 2.8.0+cu128** has native kernels for sm_100 (B200) and sm_120 (RTX PRO 6000, local RTX 5090), so
  the local smoke test exercises the same CUDA 12.8 stack. The 2.8 pin comes from whisperx (torch~=2.8) and
  pyannote 4.0 (torch>=2.8).
* **onnxruntime-gpu 1.26.0.** Its PyPI CUDA 12.8 Linux build carries compute_90 PTX, which the driver
  JIT-compiles on sm_100 (cached in `$CUDA_CACHE_PATH`). From 1.28 the CUDA 12.8 Linux builds drop that PTX
  and ship no sm_100 code; the packaging PR says sm_100 users are expected to run CUDA 13 builds. No default
  stage needs ORT on the GPU: EmotiEffLib falls back to the CPU provider.
* **CTranslate2 4.8.2** (faster-whisper) is built with CUDA 12.8. Use float16 on Blackwell; int8 GEMMs fail on
  some sm_120 shapes.
* **transformers 4.57.6 / huggingface-hub 0.36.2**: whisperx needs hub < 1.0, and transformers 5.x needs hub >= 1.31.
* **py-feat 2.x** needs torch >= 2.11 and timm >= 1.0, so it lives in `env/environment-pyfeat.yml`.
* `python -m fedpress.cli doctor` checks Python, the config, the manifest, imports, a CUDA matmul, CTranslate2
  CUDA, an ORT CUDA MatMul, ffmpeg, the HF token (presence and mode only, never the value) and the model cache.

## 7. Models and licences

The registry with pinned revisions is `config.yaml` → `models:`. `prefetch-models` records what it fetched in
`<root>/cache/models_lock.json`.

| Model | Use | Licence |
|---|---|---|
| openai/whisper-large-v3-turbo (CTranslate2: mobiuslabsgmbh/faster-whisper-large-v3-turbo) | clocks | MIT |
| manelalab/chrono-bert-v1-<year>1231, fine-tuned walk-forward on gtfintechlab/fomc_communication | primary stance (deviation D1) | MIT base; CC BY-NC 4.0 labels, so the fine-tunes are non-commercial |
| gtfintechlab/FOMC-RoBERTa | stance cross-check (registered model, inaccessible) | CC BY-NC 4.0, **gated (manual approval)** |
| Moritz-Pfeifer/CentralBankRoBERTa-sentiment-classifier | agent sentiment, not stance (A-30) | MIT |
| Loughran-McDonald Master Dictionary | cross-check | free for academic use |
| audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim | vocal_proxy | CC BY-NC-SA 4.0 |
| speechbrain/spkrec-ecapa-voxceleb | chair voice check | Apache-2.0 |
| pyannote/speaker-diarization-3.1 (+ segmentation-3.0, wespeaker) / community-1 | optional diarization | MIT / CC BY 4.0, gated |
| MediaPipe Face Landmarker | expression_proxy | Apache-2.0 |
| SFace (OpenCV Zoo, face_recognition_sface_2021dec) | chair face identity gate | Apache-2.0 |
| EmotiEffLib enet_b0_8_va_mtl | expression_proxy | code Apache-2.0; weights trained on AffectNet (non-commercial) |
| py-feat face_multitask_v2, InsightFace buffalo_l | options | research-only / non-commercial weights |
| emotion2vec_plus_large, 3loi WavLM, Qwen3-Embedding / all-MiniLM-L6-v2, Qwen3-ForcedAligner, wav2vec2-xlsr-53-english | options | FunASR model licence / MIT / Apache-2.0 / Apache-2.0 / Apache-2.0 |
| Libraries: faster-whisper, CTranslate2 (MIT), whisperx (BSD-2), pyannote.audio (MIT), speechbrain, transformers (Apache-2.0), praat-parselmouth (GPL-3.0), openSMILE (audEERING research licence) | | |

Non-commercial models are allowed for this research build. Fed videos and transcripts are US-government works
in the public domain; the Board asks for attribution. YouTube and C-SPAN copies are not used.

## 8. Checklist for a stage module

1. Create `fedpress/stages/<name>.py` with a `SPEC = StageSpec(...)` and `run(ctx) -> StageResult`. Optionally
   add `applies(ctx)`, which returns a reason to skip (for example `"chair Warsh not in voice.chairs"`), and
   `finalize(cfg, meetings, log)`.
2. Read inputs only through `ctx.out(<FILES key>)` and other stages' tables. Read settings only from
   `ctx.scfg` / `ctx.cfg`. Hard-coded tunables are not allowed.
3. Import heavy libraries inside `run`. For GPU work, call `fedpress.gpu.preload_cuda_libs()` first. Use
   `fedpress.gpu.device(ctx.scfg.get("device", "cuda"))` and load models from
   `fedpress.models.local_path(cfg, key)` with the pinned revision.
4. Stamp with `ctx.stamp(df)` / `ctx.stamp_statement(df)`. Write with `ctx.write_table(df, key, models=(...))`.
   Register non-table outputs with `ctx.add_output(path)`. Put intermediate files in `ctx.scratch()`.
5. Log with `ctx.log.info("event", **fields)`. Put quality numbers (thresholds chosen, match fractions,
   counts) in `ctx.result.notes`; they end up in the done-marker.
6. Raise on anything that makes the outputs wrong. The runner records the failure for that meeting only.
