# H2/H3/H4 note 2: the 2023-06-14 video is the 2023-07-26 press conference

Written 2026-10-04 at about 00:58 UTC, before any voice or face feature is joined to returns.

## Fact

The recording the manifest gives for the 2023-06-14 press conference (Brightcove asset 6329422013112, 674,644,353
bytes, 2,949 s) is the 2023-07-26 press conference. The ASR text says the Committee raised its policy rate a quarter
percentage point "today" (June 2023 held rates; July raised them) and that there are "eight weeks now until the
September meeting". Its first 3,000 words match the 2023-07-26 ASR at 0.981 similarity. The package flagged the
meeting on its own: the transcript-to-audio alignment failed (timing_ok false, match_frac 0.14). The transcript PDF
for 2023-06-14 is the correct June document. The HiPerGator run uses the same asset, so its tables have the same
problem.

## Consequence

- The voice and face tables filed under 20230614 describe the July meeting and are not used for June in any test,
  baseline or descriptive row.
- Under the frozen rules this changes nothing: 2023-06-14 has no captions and `drop_timing` = 1 in the events table,
  so it is already outside the timing-eligible primary sample and has no caption-timed answers for the baselines.
  The run's QA output must confirm that no 20230614 voice or face row enters a feature, baseline or fit.
- Note 1's descriptive rows "without 20230614" therefore equal the primary rows; they are still reported.
- Text-only results that use the June transcript are unaffected.
- The video should be re-sourced before any later study uses this meeting's voice or face.
