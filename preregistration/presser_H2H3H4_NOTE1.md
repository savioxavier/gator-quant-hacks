# H2/H3/H4 note 1: facts and open choices fixed before the join

Written 2026-10-04 at about 00:50 UTC. At this time voice and face tables exist for every Powell press conference,
and none of them has been read together with market data. This note changes nothing in
`presser_H2H3H4_EXPLORATORY.md` (sha256 e030af98...a6d0). It records facts found after that file was committed and
fixes choices the file leaves open. Every result is reported as exploratory, post-G3; G3 stays NO-GO.

## 1. Disclosure: development tables written before the pre-registration

The package's throughput timings (fedpress_pkg README section 9) were measured on two Powell meetings in a scratch
folder used during package development. That run wrote voice and face tables for:

| Meeting | voice_chunks written (UTC, 2026-10-03) | face tables written (UTC, 2026-10-03) |
|---|---|---|
| 20190501 | 22:20:40 | 22:21:14 |
| 20200303 | 22:15:03 | 22:38:10 |

This was before the pre-registration commit (64ceb24, 23:26:20 UTC). The pre-registration's statement that no
voice or face feature existed, and the machine search it reports, missed this folder. The tables were never joined
to market data. We cannot rule out that summary values were printed during that development run.

- 20200303 is excluded by the pre-registration anyway (unscheduled meeting).
- 20190501 stays in the 2018-2022 training sample. The tables used in the run come from the fresh computation
  below, not from the development folder. Every H4 result is also reported without 20190501, as a descriptive row.

## 2. Platforms and which run governs

- **Local tables.** All 64 Powell meetings were computed on one RTX 5090 between 2026-10-03 23:45:57 and
  2026-10-04 00:44:44 UTC, after the pre-registration was on origin (checked 23:44:30). The run used the default
  config; overrides set only the compute type and batch sizes. Code version 0.1.0+src.df22a2d52e78. Model
  revisions match sections 3 and 4: ECAPA 0f99f2d0, audeering 6eba34a2, MediaPipe 64184e22, SFace 0ba9fbfa,
  emotiefflib 1.1.1. Whisper 0a363e91.
- **HiPerGator tables.** Same code and model revisions. Speech ran on B200 GPUs; face ran on CPUs
  (`FACE_ON_CPU=1`). The pre-registration does not fix the face device; this difference is recorded here.
- **Order.** The pre-registration names HiPerGator as the reference platform and asks a local replication to
  report agreement. The local tables are run first, as the replication, with output in
  `backtests/presser/backtest_h234_local`. The reference run uses the default folder
  `backtests/presser/backtest_h234`.
- **What governs.** Both runs are reported, with their agreement. Where they disagree, the HiPerGator run governs.
  If the HiPerGator tables cannot be copied back before the report deadline (2026-10-04 10:00 ET), the local run is
  reported as the only run, labelled as such.

## 3. Meetings with weak alignment

- **20230614** (primary 2023-2026 sample): the turns alignment failed (timing_ok false, match_frac 0.14), although
  the ASR text matches the transcript PDF.
- **20200315**: face enrolment failed. The meeting is excluded anyway (unscheduled).

No exclusion is added beyond the frozen gates and QA of sections 3.4, 3.7, 4.2 and 4.3. Whatever those decide for
20230614 stands. A descriptive row without 20230614 is reported for every primary test.

## 4. H4 when H2 or H3 is killed

The pre-registration does not say whether H4 runs when a kill switch stops H2 or H3. As built, H4 runs on the same
features either way. Its result is reported with the kill-switch status of H2 and H3 next to it, naming any killed
component. Holm is unchanged (m = 3; a killed test enters with p = 1).

## 5. Source invariance

The 64 kbps re-encode check of section 3.7 (2019-01-30, 2019-03-20, 2019-06-19) is run before the join if it can be
done in time. If it has not run, H2 carries the label "source invariance not checked", as the pre-registration
provides.
