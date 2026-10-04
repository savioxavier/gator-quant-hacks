# frames and face stages

`frames` (CPU) samples video frames. `face` (GPU job) measures the chair's facial behaviour on answer frames
and writes one row per frame and one row per answer and per 30/60 s window. Both stages are Powell-only by
default (`face.chairs`). Warsh is text-only. These features are proxies for facial behaviour; they are not
readings of emotion.

## 1. Defaults and options

| | Default (team plan) | plan_v0 options (config switches, off) |
|---|---|---|
| Rate | 1 fps (`frames.fps`, `face.fps`) | 2-5 fps; set `frames.store: index` so no JPEGs are written at that rate |
| Frames | JPEG zip from the CPU `frames` stage | `face.source: stream`: the face stage decodes the MP4 itself in batches (NVDEC when available) |
| Detector + landmarks | MediaPipe Face Landmarker (478 points, 52 blendshapes, head pose), CPU | `face.detector: insightface` (SCRFD + 3D-68 pose) or `pyfeat` (RetinaFace) |
| Identity gate | SFace embeddings (OpenCV Zoo, Apache-2.0), enrolled on the opening remarks | InsightFace ArcFace, py-feat ArcFace, or `geometry` (box position and size) |
| Expression | EmotiEffLib `enet_b0_8_va_mtl` (8 expressions, valence, arousal), torch on the GPU | py-feat `face_multitask_v2` (20 AU probabilities, 7 emotions, valence/arousal, gaze, pose) |
| Blendshapes | MediaPipe, from the detector | MediaPipe cross-check on the chair crop when another detector is used (`face.mediapipe.crosscheck`) |

The team plan names MediaPipe and EmotiEffLib but no identity model. The identity gate is still needed: the Fed
video cuts to the reporters, often with several faces in view, as in the 2025-09-17 clip used for the smoke
test (`identity_score` of the chair candidate during answers: chair 0.65-0.95, cutaways 0.06-0.25; threshold
0.363, OpenCV's SFace value). SFace is Apache-2.0 and runs on the CPU at about 3-9 ms per face, so the default
stack carries no extra licence restriction.

plan_v0 profile (py-feat, 5 fps; run from `env/environment-pyfeat.yml`, which has no EmotiEffLib):

```
--set frames.fps=5 --set frames.store=index --set face.fps=5 --set face.source=stream \
--set face.pyfeat.enabled=true --set face.detector=pyfeat --set "face.expression=[pyfeat]" \
--set face.emotiefflib.enabled=false
```

InsightFace profile (main env): `--set face.insightface.enabled=true --set face.detector=insightface
--set face.identity.method=insightface` (and the rate settings above).

## 2. Clock and causality

* Frame slot `k` is at `t = k / fps` media seconds. ffmpeg's `fps` filter runs with `round=up` and
  `start_time=0`, so slot `k` holds the latest source frame at or before `t`. A frame never shows content from
  after its own time stamp (`tests/test_face.py::test_decoded_slot_never_shows_later_content`).
* Frame rows have `t_start_s = t_end_s = t`; `known_at = t + anchor offset + timing.latency_s` (clock.py).
* `face_turns` rows: answer rows end at the answer end; window rows are tumbling windows from the answer start
  and end at `min(window end, answer end)`. They average only frames inside their own span.
* Enrolment uses the first `face.enroll_max_s` (180) seconds of the opening remarks, which precede every answer.
  Opening frames are not written (`face_frames` holds answer frames only).
* The track, head speed and gates use only the current and earlier frames. No value is normalised within a
  meeting. Per-chair baselines are computed at analysis time from earlier meetings only (ARCHITECTURE.md 4).

## 3. Outputs

`frames/frames_<fps>fps.zip` + `.parquet` (frame_idx, t_s, member, width, height), `frames/frames_meta.json`
(probe, output size, decode settings, `max_seconds`).

`face/face_frames.parquet`, one row per answer frame (plus the id and timing columns of every table):

| Columns | Meaning |
|---|---|
| frame_idx, t_s, turn_idx, qa_idx, segment_kind | slot index at `face.fps`, time, the answer it belongs to |
| frame_w, frame_h, n_faces, face_found | frame size; faces detected |
| box_x/y/w/h, face_h_px, det_score | chair candidate (best identity score) |
| identity_score, identity_ok | cosine to the enrolled embedding (or geometry score); `>= threshold` |
| pitch_deg, yaw_deg, roll_deg | pitch > 0 up, yaw > 0 toward the subject's right, roll > 0 tilted to the subject's right |
| blur, luma | variance of the Laplacian at a 112 px crop height; mean luminance (covariates) |
| mouth_open, mouth_open_flag | MediaPipe `jawOpen`; `> face.masks.jaw_open` (speech confound flag) |
| reading | `pitch_deg < face.masks.reading_pitch_deg` (looking down at notes) |
| eye_blink, eyes_closed | mean of `eyeBlinkLeft/Right`; `> face.masks.eyes_closed`, NaN while reading |
| track_id, track_age_s, head_speed_dps | causal track of the chair box (camera cuts break it); angular speed from the previous frame |
| gate_ok, gate_reason | identity, size (`min_face_h_px` 80), \|yaw\| <= 40, \|pitch\| <= 30, blur, detector score; failed gates |
| bs_<name> | 52 MediaPipe blendshapes |
| ex_<expression>, ex_valence, ex_arousal | EmotiEffLib probabilities and valence/arousal |
| au01..au43, pf_<emotion>, pf_valence, pf_arousal, pf_gaze_pitch/yaw, pf_pitch/yaw/roll | py-feat, when enabled |

`face/face_turns.parquet`: unit (turn, window), window_s, unit_idx, turn_idx, qa_idx, t_start_s, t_end_s,
n_frames, n_face, n_identity, n_gated, gated_frac, means over gated frames of pose, head speed, blur, luma and
the feature columns, `<col>_mc` means over gated frames with the mouth closed (`face.aggregate.mouth_closed_columns`),
eyes_closed_frac, reading_frac, mouth_open_frac, blink_rate_per_min (NaN below `face.blink_min_fps` = 10:
blinks last 100-400 ms and cannot be counted at 1-5 fps). With `face.upper_face_only: true` (default) the
feature columns are the brow, eye and cheek-squint blendshapes and AU01/02/04/05/06/07/43; whole-face
expression scores appear only as mouth-closed means. A unit with fewer than `min_gated_frames` (3) gated
frames gets NaN features and keeps its counts.

`face/enroll.json`: method, threshold, frames and faces used, kept frames, the opening self-similarity
(median and 5th percentile), the reference embedding or geometry, and the enrolment ranges.

## 4. Running

```
python -m fedpress.cli prefetch-models                 # MediaPipe, SFace and EmotiEffLib files (pinned URLs + sha256)
python -m fedpress.stages.face prefetch                # same, plus InsightFace / py-feat weights when enabled
python -m fedpress.cli launch frames --all --set compute.gpu_type=cpu      # CPU job (prep wave)
python -m fedpress.cli launch asr,turns,diarize,voice,face,text --all     # GPU job, <= 2 GPUs
python -m fedpress.cli face --index 0 --max-seconds 900  # smoke test: opening plus the first answers
```

`--max-seconds N` processes media time below N seconds only. The done-marker records the cut, downstream
full runs treat that meeting as not ready, and a later full run redoes it.

## 5. Throughput

Measured on the local RTX 5090 with one worker and one CPU thread per library, on a 195 s clip of 2025-09-17
(960x540; opening plus two answers; times exclude model loading, which takes 5-20 s per worker):

| Profile | Per frame | Frames/s per worker |
|---|---|---|
| Default, 1 fps zip: MediaPipe 5-9 ms + SFace 8.5 ms per face (1 thread; 3 ms with 4) + EmotiEffLib < 0.5 ms (GPU) | ~20 ms | ~45-50; ~78 with 4 threads (`launch`, 2 workers) |
| Default, 5 fps stream (NVDEC decode ~0.4 ms per frame) | ~20 ms | ~50 |
| py-feat, 5 fps stream: RetinaFace + multitask batch 64 bf16 ~17 ms, SFace 9 ms, MediaPipe cross-check 2 ms | ~30-35 ms | ~30 |
| InsightFace on CPU ONNX Runtime (local test only) | 80-700 ms (1-7 faces) | 2-10 |
| frames stage, 1 fps JPEG zip, 4 decoder threads | ~70x real time | ~45 s per meeting; ~110 KB per frame (~330 MB per meeting) |

Planning estimates for Powell (64 pressers, ~30 h of answers + 180 s enrolment each): ~120k frames at 1 fps,
~600k at 5 fps. The default face stage is CPU-bound (MediaPipe and SFace); EmotiEffLib keeps the GPU busy
only lightly. Estimates assume 6 workers per B200 with 2 cores each (`compute.profiles.b200`), and about 1.3x
faster cores than the local test for the per-worker rate.

| Face stage | per B200 | 2 x B200 | 1 x B200 | RTX 5090 (2 workers, 400 W cap) |
|---|---|---|---|---|
| Default, 1 fps | ~300 frames/s | 5-10 min | 10-15 min | 20-40 min |
| py-feat, 5 fps | ~150-250 frames/s | 25-45 min | 45-80 min | 3-4 h |
| InsightFace, 2 fps (ONNX Runtime CUDA) | ~200-300 frames/s, unverified on sm_100 | 15-25 min | 25-45 min | 1-1.5 h |

Replace these with the `frames_per_s` and `timings_s` values in `_done/face.json` and with `status`
`elapsed_sum` after the first HiPerGator run. The idle-GPU rule (1 h at 0 %) is not a risk for the default
profile inside the GPU wave because EmotiEffLib runs on the GPU in every batch; the stage takes minutes.

## 6. Licences

| Model / library | Use | Licence |
|---|---|---|
| MediaPipe Face Landmarker (`face_landmarker.task` float16 v1) | detector, landmarks, blendshapes, pose | Apache-2.0 |
| SFace `face_recognition_sface_2021dec` (OpenCV Zoo; HF `opencv/face_recognition_sface`) | identity gate | Apache-2.0 |
| EmotiEffLib `enet_b0_8_va_mtl` | expression, valence/arousal | code Apache-2.0; weights trained on AffectNet: non-commercial research only |
| InsightFace `buffalo_l` (SCRFD-10GF, ArcFace R50 WebFace600K, 3D-68) | option | code MIT; models non-commercial research only |
| py-feat 2.1.3 `face_multitask_v2` (`face_multitask_v28.safetensors`), RetinaFace R34, ArcFace R50 | option | code MIT; weights research-only; ArcFace weights from InsightFace (non-commercial) |
| OpenCV, ONNX Runtime, PyTorch, ffmpeg (LGPL/GPL builds as installed) | runtime | Apache-2.0 / MIT / BSD-3 / LGPL-GPL |

Non-commercial weights are allowed for this research build. Fed videos are US-government works.

## 7. Known limits (pre-register before results)

* `face.masks` and `face.gates` values are placeholders. Check them on hand-labelled frames (reading, mouth
  open, eyes closed, cutaway) before H3 and freeze them with the code hash.
* MediaPipe misses heads turned far down and small faces (the reporter wide shots); those frames are simply
  ungated. InsightFace and py-feat find more faces.
* `pitch_deg` contains the camera's elevation; `reading` uses an absolute threshold.
* EmotiEffLib's ONNX engine is CPU-only in the library; the default torch engine runs natively on sm_100.
* ONNX Runtime CUDA on the B200 (InsightFace option) relies on PTX JIT from onnxruntime-gpu 1.26 and has not
  been tested on sm_100. SFace runs on the CPU provider by default for that reason.
* py-feat downloads its RetinaFace and ArcFace weights by file name into its package directory (not pinned to
  a revision); the multitask weights are pinned. Run the prefetch in the py-feat env.
