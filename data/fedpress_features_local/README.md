# Press-conference voice, face and speech features (local run, 64 Powell meetings)

Per-meeting tables written by the feature package `hpg/fedpress_pkg` (code version 0.1.0+src.df22a2d52e78) for
every Powell press conference from 2018-03-21 to 2026-04-29. They were computed on one local RTX 5090 between
2026-10-03 23:45:57 and 2026-10-04 00:44:44 UTC, after the exploratory H2/H3/H4 pre-registration was public (see
`preregistration/presser_H2H3H4_NOTE1.md`). They feed the **local replication** of H2/H3/H4
(`backtests/presser/H234_LOCAL_SUMMARY.md`). The HiPerGator tables, which feed the reference run
(`backtests/presser/backtest_h234/`), were produced by the same code and model revisions and stay on HiPerGator; the
two runs agree (H2 p 0.438 vs 0.439, H4 p 0.244 vs 0.243).

## Layout

`meetings/<presser_id>/` holds, per meeting:

| Folder | Tables | What |
|---|---|---|
| `asr/` | `words.parquet`, `segments.parquet`, `asr.json` | Whisper large-v3-turbo transcript with word times |
| `turns/` | `turns.parquet`, `words.parquet`, `anchor.json` | speaker turns aligned to the transcript PDF; clock anchor; `known_at` |
| `diarize/` | `chair_check.parquet` | ECAPA check that a window is the chair's voice |
| `voice/` | `voice_chunks.parquet` | 8 s chunks of the chair's answers: arousal, dominance, valence, prosody, identity flags |
| `face/` | `face_frames.parquet`, `face_turns.parquet`, `enroll.json` | 1 fps chair frames: blendshapes, expression scores, identity and quality gates |
| `_done/` | one JSON per stage | status, outputs with sha256, code version, config hash, overrides |

`MANIFEST.sha256` lists every file; `models_lock.json` lists the model revisions (Whisper 0a363e91, ECAPA 0f99f2d0,
audeering 6eba34a2, MediaPipe face landmarker 64184e22, EmotiEffLib enet_b0_8_va_mtl b7b9522e, SFace 0ba9fbfa).
Settings: the package's default config (voice and face for Powell only, face at 1 fps); the only overrides were the
compute type and batch sizes (see each `_done/*.json`). Every table carries `known_at`, the time the row could have
been known live.

## Known issues

- **2023-06-14:** the recording the Federal Reserve publishes for this meeting is the 2023-07-26 press conference,
  so these tables describe the July meeting (`preregistration/presser_H2H3H4_NOTE2.md`). Do not use them for June.
- **2020-03-03 and 2020-03-15** are unscheduled meetings; on 2020-03-15 face enrolment failed (no usable frames).
- Fifteen meetings, mostly 2018-2020, have lower voice identity (0.81-0.90) and face gate (0.75-0.89) rates; use the
  tables' own gate columns.

## Sources and licences

The videos, captions and transcripts are works of the US federal government (public domain). The features come from
these models: Whisper (MIT), SpeechBrain ECAPA (Apache-2.0), audeering wav2vec2 MSP-dim (CC BY-NC-SA 4.0, so these
voice features are for non-commercial use), MediaPipe (Apache-2.0), EmotiEffLib (Apache-2.0) and OpenCV SFace
(Apache-2.0). No market data are in this folder.
