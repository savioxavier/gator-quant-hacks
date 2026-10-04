# H2/H3/H4 note 3: code fix found before the join

Written 2026-10-04 at about 01:35 UTC. No voice or face feature has been joined to market data: the first local run
stopped in stage 1 (`h234_s1_features.py`), which reads no prices, and wrote no output file.

## The bug

`h234_s1_features.py` read the WAV length for the section 3.7 check from `audio/audio.json["duration_s"]`. The
package (commit 436a351, `fedpress/stages/audio.py`) writes it at `audio/audio.json["output"]["duration_s"]`. The
value was therefore missing for every meeting, every meeting failed the WAV check, no meeting passed the gates and
stage 1 crashed (KeyError) at 2026-10-04 01:04:45 UTC. The stage had been tested only on placebo trees, which
carried the key at the top level.

## The fix

- Read `output.duration_s`, then a top-level `duration_s`, then the audio done-marker's `notes.duration_s`. The
  check itself (WAV length within 2 s of the text label's video length) is unchanged.
- Provenance only: the source-invariance re-runs (`H234_SI_ROOT`) were recorded in `qa/input_hashes.json` under the
  same keys as the original tables, overwriting them. They are now recorded under `si/<presser_id>/...`.
- No gate, threshold, feature, sample, target, cost or test changes.

Pre-registration section 9 keeps the first result when a bug is found after the join. There is no first result
here: the bug was found before the join and no output was written.

## What was seen before this fix was committed (no returns)

To locate the bug, stage 1 was run in memory with the corrected key, into a scratch folder, without market data.
That showed the frozen gate outcomes before this note:
- The caption check of 3.7 (|ASR vs caption median offset| <= 2 s) excludes 36 of 62 baseline meetings. 10 of the
  20 timing-eligible 2023-2026 meetings and 16 of 31 in 2018-2022 pass.
- H3 is killed by G4: the browInnerUp floor binds in 22 of 22 post-burn-in meetings.
- H2 is not killed, and carries "source invariance not checked": 20190619, one of the three re-encode meetings,
  fails the caption check, so the ICC is not computed.
These gates stay exactly as pre-registered.

The source-invariance task also displayed the package's done-marker notes for 20190130, 20190320 and 20190619,
which include per-meeting medians of arousal, dominance and valence. No market data were involved. This is
disclosed because section 10 states voice and face were blind.
