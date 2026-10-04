# EXPLORATORY, POST-G3: voice (H2), face (H3) and combined (H4) tests

Written Sat 2026-10-03, about 23:25 UTC (19:25 ET). **No voice or face feature exists when this file is written.**
The feature package (`hpg/fedpress_pkg`, commit 436a351) has not been run on HiPerGator. A search of this machine
found no `voice_chunks`, `face_frames` or `face_turns` table. The package README reports throughput runs on the local
GPU (2019-05-01, 2020-03-03, a 195 s clip of 2025-09-17). Their outputs are not on this machine, the author of this
file has seen no value from them, and nothing from them has been joined to any return.

## 0. Status: what this file can and cannot do

- **Exploratory, post-G3.** The press-conference H1-primary test returned G3 = NO-GO. The locked plan
  (`presser_team_FINAL_PLAN.md`, section 7) then says "Stop; do not mine H2". The merged amendments (R2-26) say that
  after a NO-GO, H2, H3 and H4 do not run and enter the register with p = 1.
- **This file does not change that.** In the locked family's register H2, H3 and H4 stay at p = 1, and G3 stays
  NO-GO. Nothing below can overturn G3, rescue H1 or support a trading claim. Every result carries the label
  "exploratory, post-NO-GO; cannot rescue G3; no trading claim".
- **What the tests are for:**
  1. To describe the voice and face channels on Powell's press conferences (do they vary, and do they line up
     with short-horizon rates moves beyond the text?).
  2. To fix definitions, code and weights before the 2026-10-28 meeting, so nothing is tuned after that date.
- **The limit on the 2026-10-28 forward test.** The 2026-10-28 meeting is Warsh's. Voice and face are off for
  Warsh in the locked plan, and Warsh has 3 earlier pressers, so a 4-meeting burn-in would not be complete
  until after 2026-10-28. On 2026-10-28 the forward test is therefore the locked text paper test only.
  - This file adds the frozen measurement protocol (section 2 to 4) and the frozen H4 weights (section 6).
  - Applying any of it to Warsh needs a separate team decision and its own pre-registration before
    2026-10-28 14:00 ET. Even then 2026-10-28 would be Warsh burn-in meeting 4: no z-score and no position.
- **No forward Powell data will ever exist.** Powell's chair tenure has ended, so a significant result here can
  only motivate a new pre-registered test on another chair. It cannot be confirmed on Powell.

## 1. Inputs and the rules they keep

| Source | What it fixes here |
|---|---|
| `presser_team_FINAL_PLAN.md` section 2 (locked) | H2/H3: vocal_proxy and expression_proxy; prior-meeting same-chair z; Powell only; 4-meeting burn-in; variance floor; identity gate; off for Warsh. H4: combined vs text on 2023-2026 Powell after H1 is frozen and its code hash recorded. |
| `MERGED_FINAL_PLAN.md` 3.7, A-16, A-26, A-29, A-31..A-33, R2-14, R3-42 | Arousal primary, dominance second, valence excluded or used only after residualising on the same chunk's text score. Median per answer and meeting. ECAPA identity gate. Upper-face composite is the single H3 output. Speaking-flag covariate. Identity model named before processing. H4 trained on Powell 2018-2022 after burn-in, on walk-forward chrono text scores, and tested on 2023-2026 with Clark-West. Joins never on the package `known_at`. |
| `presser_ADDENDUM.md` (frozen) | Clock, τ, entry and exit, contracts, ticks, costs, samples, timing eligibility, answer selection, bootstrap settings and seed. Everything in this file uses it unchanged unless a row in section 8 says otherwise. |
| `hpg/fedpress_pkg` at commit 436a351 | The exact feature columns (read from `fedpress/stages/voice.py`, `face.py`, `_face_models.py`, `diarize.py`, `aggregate.py`, `fedpress/baselines.py`, `config.yaml`, `docs/ARCHITECTURE.md`, `docs/FACE.md` and the tests). |

## 2. Samples

**Meetings used for baselines.** Every scheduled Powell press conference, 2018-03-21 to 2026-04-29, whose feature
passes the gates of section 3 or 4. The two unscheduled 2020 meetings (2020-03-03, 2020-03-15) are excluded
everywhere, as in the ADDENDUM. Timing-dropped meetings still enter baselines, because baselines need no market
clock.

**Burn-in.** The first 4 Powell meetings with a valid feature, in date order, carry no z-score and no position.
If all are valid, these are 2018-03-21, 2018-06-13, 2018-09-26 and 2018-12-19. Burn-in is counted separately
for each feature.

**Test samples.** A market-joined test also needs the meeting to be timing-eligible (events.csv `drop_timing` =
0, ADDENDUM section 2) and the answer to be caption-timed (`timing_source` = vtt).

| Sample | Meetings (timing-eligible, after burn-in) | Role |
|---|---|---|
| Primary: Powell 2023-03-22..2026-04-29 | The ADDENDUM's 20 confirmation meetings | H2, H3 and H4 primary tests (section 7) |
| Additional: Powell 2018-2022 | 31 timing-eligible scheduled meetings minus burn-in: 27 if the burn-in is the four 2018 meetings | H4 training; H2/H3 reported beside the primary, no Holm |
| Pooled 2018-2026 | both | Descriptive only |
| Warsh | none | Off |

**Why the 2023-2026 sample is primary for H2/H3.** It is the ADDENDUM's only sample that may carry P&L language.
It also meets A-29 (the model's training data predate the meeting) for both affect models without exception
(section 5).

## 3. H2: vocal proxy

### 3.1 Input

Read `voice/voice_chunks.parquet` per meeting, which is Powell only. Its columns:
- chunk_idx, turn_idx, qa_idx, dur_s, identity_frac, identity_ok, identity_source;
- arousal, dominance, valence (audeering `wav2vec2-large-robust-12-ft-emotion-msp-dim`, revision 6eba34a2, model
  scale about 0..1);
- f0_*, voiced_frac, intensity_db, hnr_db, n_words, speech_rate_wps, articulation_rate_wps, pause_frac,
  n_pauses;
- the common id and timing columns.

**Chunking.** The package default: non-overlapping 8 s windows inside each chair answer turn. A tail shorter than
3 s is dropped. Each chunk is normalised on its own audio only.

`features/answers.parquet` (`voice_arousal` and others) serves only as a cross-check, because its turns end on the
package's ASR clock and not on the caption clock used for fills.

### 3.2 Features

- **Primary: arousal.**
- **Pre-named second (descriptive): dominance.**
- **Valence:** excluded from every test. One descriptive row uses residualised valence (3.6).

### 3.3 Unit and the media-time cut

- **Unit:** the chair's Q&A answer as the frozen text label defines it (`text_chrono/answers.parquet`). Opening
  remarks and closing turns are never used.
- **Answer end** in caption media time: E_k = `t_end_video_s`_k + `end_cue_dur`_k. This is the same E_k inside the
  ADDENDUM's τ_k,upper.
- **A chunk belongs to answer k** if:
  - its midpoint lies in [`t_start_video_s`_k, E_k];
  - its `t_end_s` <= E_k;
  - it comes from a package turn with segment_kind = answer and is_chair = true.
- **Why this is causal.** τ_k,upper = W_m(E_k) + `start_unc_s`_m >= W_m(E_k), so every chunk used was audible
  before the entry decision.
- **The package `known_at` is never used for a fill.** It is the greeting anchor plus 30 s. It is recorded as a QA
  comparison only.

### 3.4 Gates (identity and quality), fixed now

**A chunk is valid** only if all of these hold:
- identity_ok = true. This means identity_frac = 1.0: the whole chunk lies inside diarize windows with
  chair_verified.
- dur_s >= 3.0.
- voiced_frac >= 0.25. This stands in for the merged plan's VAD, which the package does not run inside answers.
- arousal is not missing.

**The identity gate is the package's ECAPA check** (`speechbrain/spkrec-ecapa-voxceleb`, revision 0f99f2d0):
- the voiceprint is enrolled from the same meeting's opening remarks;
- the threshold is set from the opening alone: max(0.30, q0.02 of leave-one-out opening scores - 0.10).
- The opening precedes every answer, so the rule is causal and could run live. See section 8 for the
  difference from A-16.

**An answer feature exists** if at least 2 valid chunks belong to the answer:
- A_k = the median of arousal over them (A-31: median per answer);
- D_k = the median of dominance over them.

**A meeting is excluded from H2,** with the reason logged, in any of these cases:
- diarize failed, or its opening enrolment is below `min_enroll_s` = 60 s;
- valid chunks cover less than 50% of the meeting's answer-chunk seconds;
- the QA of section 3.7 fails.

### 3.5 Normalisation

**z_A,k = (A_k - c) / s.** It uses `fedpress.baselines.causal_z`:
- chair = Powell;
- pool = rows: the answer-level A values of all strictly earlier baseline meetings form the reference;
- robust: c = median, s = max(1.4826 x MAD, floor);
- burn_in = 4;
- order by meeting date;
- the meeting's own rows are never in its baseline.

**Variance floor (fixed now, in model units):** 0.01 for arousal and dominance. The package default (variance_floor =
1e-6) is replaced at analysis time. No feature is recomputed.

**Clipping:** z is clipped to [-5, 5].

**Meeting feature:** z_A,m = the mean of z_A,k over the meeting's valid answers.

### 3.6 Descriptive valence row (not tested)

1. For each chunk, the text score is computed from the package's `text/text_sentences` rows whose word-time
   midpoint lies inside the chunk: the primary `cwf` share hawkish minus share dovish, and `cbr` positive minus
   negative.
2. Chunk valence is regressed on those two scores by OLS on the strictly earlier Powell baseline meetings' chunks
   (expanding, same 4-meeting burn-in).
3. The residual's answer median is z-scored as in 3.5.

The row is labelled "valence, residualised on the same chunk's words (A-31); descriptive".

### 3.7 Feature QA before any market join (no returns read)

Per meeting:
- the ASR-vs-caption median offset from the turns done-marker (`vtt_check`). If |offset| > 2 s, or the check is
  missing, the meeting is out of H2 and H3 joins.
- WAV duration vs the text label's `video_duration_s`. If they differ by more than 2 s, out.
- identity coverage, n chunks, enrolment seconds and the ECAPA threshold.

**Source invariance (A-31 kill switch).**
- On 2019-01-30, 2019-03-20 and 2019-06-19 the audio is re-encoded at 64 kbps AAC and the voice stage is
  re-run.
- If the ICC(3,1) of answer-level A_k between the two runs is < 0.8, H2 is killed (p = 1).
- If this check has not run before the join, H2 carries the label "source invariance not checked".

**Variance gate (G4).** If the floor binds (s = floor) for more than 25% of post-burn-in Powell meetings, H2 is
killed (p = 1, "no usable within-chair variation").

## 4. H3: facial expression proxy

### 4.1 Input

Read `face/face_frames.parquet`, Powell only, at 1 fps. The package writes answer frames only. Columns used:
- frame_idx, t_s, turn_idx, segment_kind;
- face_found, face_h_px, det_score, blur, yaw_deg, pitch_deg, identity_score, identity_ok, gate_ok, gate_reason;
- mouth_open, mouth_open_flag, reading;
- `bs_<name>`: the 52 MediaPipe Face Landmarker blendshapes, float16 v1, sha256 64184e22;
- `ex_<expression>`, ex_valence, ex_arousal: EmotiEffLib `enet_b0_8_va_mtl`, sha256 b7b9522e. The expression
  names are taken from the library's `idx_to_emotion_class`, lower-cased. They are expected to be anger,
  contempt, disgust, fear, happiness, neutral, sadness and surprise. The realised list is recorded before any
  join.

**Identity model (named now, A-32):** SFace (OpenCV Zoo `face_recognition_sface_2021dec`, Apache-2.0, sha256
0ba9fbfa):
- enrolled from the first 180 s of the same meeting's opening remarks;
- robust mean embedding; enrolment needs at least 10 frames with cosine >= 0.5 to the mean;
- identity_ok = cosine >= 0.363 (OpenCV's SFace value).

### 4.2 Frame gates (the package's `gate_ok`, frozen at the config values of commit 436a351)

A frame is gated in only if all of these hold:
- a face is found and identity_ok;
- face_h_px >= 80;
- |yaw| <= 40 degrees and |pitch| <= 30 degrees;
- blur (Laplacian variance) >= 20;
- detector score >= 0.5.

`docs/FACE.md` calls these values placeholders to be checked on hand-labelled frames. They are frozen here as they
stand. Any change is a dated deviation note written before the join.

### 4.3 Primary H3 feature: upper-face composite U

The upper face is used because speech moves the lower face (`face.upper_face_only`).

**Frames of answer k:** gated frames with t_s in [`t_start_video_s`_k, E_k). An answer feature needs at least 5 gated
frames.

**Three components,** each the mean over those frames:
- BD_k = (bs_browDownLeft + bs_browDownRight) / 2: brow lowering, the AU4-like movement;
- BI_k = bs_browInnerUp: inner-brow raise, AU1-like;
- ES_k = (bs_eyeSquintLeft + bs_eyeSquintRight) / 2: lid tightening, AU7-like.

**The composite:**
- Each component is z-scored as in 3.5: Powell baseline meetings, pool = rows, robust, burn-in 4, clip ±5.
- The variance floor is 0.005 in blendshape units.
- U_k = (z_BD,k + z_BI,k + z_ES,k) / 3. All three must be present.
- U_m = the mean of U_k over the meeting's valid answers.

**Why these three.** Together they form the brow-lowering, inner-brow-raise and lid-tightening cluster that facial
coding links to concern, effort and negative affect. Blinks, gaze (eyeLook*), wide eyes and cheek squint are
left out:
- blinks cannot be resolved at 1 fps;
- gaze follows reading the notes;
- wide eyes are surprise;
- cheek squint goes with smiling.

**Speaking-flag covariate (A-32):** M_k = the share of the answer's gated frames with mouth_open_flag (jawOpen >
0.025). It enters every H3 companion regression.

**A meeting is excluded from H3** in any of these cases:
- face enrolment failed (`enroll_ok` = false);
- fewer than 20 gated frames over its answers;
- the QA of 3.7 fails.

**Variance gate (G4).** If the floor binds for more than 25% of post-burn-in meetings for any of the three
components, H3 is killed (p = 1).

**A/V skew (A-33)** is not estimated by the package and is not corrected. A frame at media time t is on screen at
W_m(t), so any skew cannot make a frame used here unobservable by τ_k,upper. The skew only blurs the answer
boundaries.

### 4.4 Named descriptive face features (Tier 3, not tested)

Each is z-scored as in 3.5 and reported answer-level and meeting-level, with no p-value counted:
- the three components BD, BI, ES separately;
- browOuterUp (AU2-like);
- eyeWide (AU5-like);
- cheekSquint (AU6-like);
- EmotiEffLib negative affect: anger + contempt + disgust + fear + sadness, over gated mouth-closed frames;
- ex_valence and ex_arousal over gated mouth-closed frames;
- U computed without frames flagged `reading`.

## 5. Model cutoffs (A-29)

- **audeering A/D/V:** trained on MSP-Podcast. The model was released in March 2022, so its training audio
  predates every 2023-2026 meeting. For 2018-2021 meetings the cutoff cannot be verified, so those rows carry
  "cutoff not verified". They are additional-sample rows anyway.
- **EmotiEffLib:** trained on AffectNet, images collected by 2017, which predates every Powell meeting.
- **MediaPipe blendshapes, SFace, ECAPA:** geometric measurement and identity verification. They are treated
  like the exempt classes in A-29 (alignment, speaker verification).

## 6. Targets, positions and tests

### 6.1 Execution: identical to the frozen ADDENDUM

- **Clock and τ:** ADDENDUM 1.1. τ_k,upper for answers; τ_end,upper for the meeting.
- **Contracts and ticks:** ADDENDUM 1.2. Quotes: 1.3.
- **Answer-level (as H1-answer, ADDENDUM 4.2-4.3):**
  - entry at the next 1m open after τ_k,upper, bar start t0;
  - exits at the close at t0 + 1 min (primary) and t0 + 5 min;
  - +15 min appendix.
- **Answer selection:**
  1. Start from the ADDENDUM's eligible answers (section 2: timed, at least 40 words, at least one sentence unit,
     non-missing score).
  2. Additionally require the hypothesis's feature to be non-missing.
  3. Where several answers share an entry bar, keep the latest.
  4. Apply the earliest-first greedy non-overlap pass per horizon.
  Each hypothesis therefore has its own selected set, reported with its n.
- **Meeting-level (as H1-primary, ADDENDUM 3.5):**
  - entry at the next 1m open after τ_end,upper; exit at the close at 16:00:00 (last bar with `ts_event` <=
    15:59); 16:30 robustness;
  - no trade if the entry bar starts at or after 15:59;
  - signal = the meeting feature (z_A,m or U_m).
- **Symbols:** ZT.v.0 primary; ES.v.0 robustness; ZF and ZN appendix.
- **One contract per trade;** P&L per contract in ticks by era and in dollars.
- **Costs (ADDENDUM 7):**
  - C0 gross decides;
  - C2 and C4, CM (measured half-spreads at the entry and exit seconds, ZT/ZN/ES) and CQ rows are reported;
  - the F fee line ($2.00 per side, unverified) is shown separately;
  - spread summaries at the answer entries.

### 6.2 Sign hypotheses (stated before data; every test is two-sided)

| Feature | Hypothesis | Why | ZT position | ES position |
|---|---|---|---|---|
| Arousal z_A (H2) | Higher arousal than the chair's own baseline reads as agitation or concern about the outlook. That is risk-off: rates fall, equities fall. | Vocal tone of the chair moves markets (Gorodnichenko, Pham and Talavera, AER 2023). Arousal is not their measure, so the prior is weak. | p = +sign(z): long ZT | p = -sign(z): short ES |
| Dominance z_D (descriptive) | More assertive delivery reads as policy commitment, which is hawkish. | Weak prior | p = -sign(z) | p = -sign(z) |
| Upper-face U (H3) | More brow lowering, inner-brow raise and lid tightening reads as negative affect. That is risk-off. | Negative facial expression of the chair co-moves with lower stock prices (Curti and Kazinnik, JME 2023; contemporaneous, minute level) | p = +sign(U): long ZT | p = -sign(U): short ES |
| Residualised valence (descriptive) | More positive tone is risk-on. | Gorodnichenko et al. 2023 | p = -sign(z) | p = +sign(z) |

The sign fixes only which way the P&L is reported. Every p-value is two-sided except H4's Clark-West (6.4).
A zero feature means no trade.

### 6.3 H2 and H3 primary statistics

For each of H2 (z_A) and H3 (U):
- **Primary:** answer-level, ZT, +1 min, gross (C0) P&L of the 6.2 position, 2023-2026 sample.
  - Statistic: mean P&L per selected answer, with a CR1 meeting-clustered t.
  - Decision p: two-sided wild cluster bootstrap by meeting, Webb 6-point weights, null imposed (y* = w_g x y),
    9,999 draws, seed 20261003. p = (1 + #{|t*| >= |t|}) / 10,000.
- **Companion slope, reported:** OLS of the +1 min log return in bp on [z, s~_k, R_m], plus M_k for H3.
  - s~_k is the ADDENDUM 4.1 text residual, so the slope is the voice or face association beyond the words.
  - Reported with the CR1 t and the restricted wild cluster bootstrap p (null: feature coefficient = 0).
- **Reported beside the primary, outside Holm:**
  - +5 min and +15 min;
  - the meeting-averaged answer P&L (sign-flip wild bootstrap, one observation per meeting);
  - the meeting-level 16:00 exit (sign-flip wild bootstrap, two-sided) and the 16:30 exit;
  - ES; ZF and ZN;
  - the 2018-2022 additional sample (year-clustered wild bootstrap by year, Webb weights, as merged-plan Tier 2
    multi-year tests);
  - pooled 2018-2026;
  - excluding 2020-2021 (remote-format years);
  - the ADDENDUM sensitivities 1-3 (section 2) and a +30 s entry row;
  - block bootstrap 90% CI (circular, whole meetings, b = max(2, round(G^(1/3)))) on every row;
  - leave-one-meeting-out range, naming the most influential meeting.

### 6.4 H4: combined vs text-only (nested, fixed in advance)

**Unit:** answer.
- **Target:** y_k = 10,000 x ln(close at t0 + 1 min / open at t0), on ZT.
- **Selection:** answers with s~_k, z_A,k and U_k all present, then the ADDENDUM selection at h = 1 min.

**Features:**
- s~_k: the ADDENDUM 4.1 point-in-time text residual from the frozen walk-forward chrono scores. This meets R2-14.
- z_A,k and U_k.
- Each is standardised by its mean and SD in the training sample only.

**Models:**
- Text-only T: y = a + b1 s~.
- Combined C: y = a + b1 s~ + b2 z_A + b3 U.
- Both are fitted by OLS once, on the training sample. The coefficients are frozen.

**Samples:**
- Training: Powell 2018-2022, timing-eligible, after burn-in.
- Test: Powell 2023-2026 (the 20 confirmation meetings).

**Before any test-sample join:**
- the training fit is written with its hash: coefficients and standardisation constants;
- the H1 code hash (`presser_bt/backtest/code`) and the sha256 of `text_chrono/answers.parquet` are recorded.

**Primary statistic: Clark-West.**
- f_k = (y_k - ŷT_k)^2 - [(y_k - ŷC_k)^2 - (ŷT_k - ŷC_k)^2].
- t = mean(f) / SE, with a CR1 meeting-clustered SE.
- Decision p: one-sided (C better), referred to t with G - 1 degrees of freedom (G = test meetings).
- It is one-sided because the nested null is b2 = b3 = 0. A worse combined model is not a rejection.
- The two-sided p and a wild cluster bootstrap p of mean(f) (Webb, centred, 9,999 draws) are reported.

**Also reported, not decisive:**
- out-of-sample R^2 of C relative to T: 1 - Σ(y - ŷC)^2 / Σ(y - ŷT)^2, and of each relative to a zero forecast;
- sign-hit rates;
- gross, C2 and C4 P&L of sign(ŷC) and sign(ŷT) positions;
- an expanding-window variant, re-fitted before each test meeting on all earlier meetings;
- a leave-one-meeting-out version within 2023-2026 and within 2018-2022, labelled "not point-in-time";
- a meeting-level version: target = the ZT return from the next 1m open after τ_end,upper to the 16:00 close;
  features s~_m, z_A,m, U_m; same train and test split; Clark-West with HC3; ES robustness.

## 7. Inference across the family

- **Holm, m = 3,** across the three primary tests: H2 (6.3), H3 (6.3), H4 Clark-West (6.4). Family alpha 0.05.
  Adjusted and raw p are both reported.
  - This is a new exploratory family. It is not the locked register's Tier 2, where these tests stay at
    p = 1 (R2-26).
  - A killed or unrunnable primary enters with p = 1. m never changes.
- **Power is low.** With about 20 meetings, see the ADDENDUM 8.2 operating characteristics (one-sided; two-sided
  power is lower). A null result is "not detected", reported with the 90% CI upper bound.
- **Report everything.** Every row named in sections 3, 4 and 6 is reported whatever its outcome, with n, gates
  hit and killed tests.
- **No feature search.** No package column other than those named here is used as a predictor, and no window,
  threshold, horizon or weight is changed after a join.
- **Wording.** A Holm-significant primary is described as "exploratory association, post-NO-GO". It needs a new
  pre-registered test on a different chair before anything else.

## 8. Choices where the plan and the package differ

| Item | Plan text | Package (commit 436a351) | This file |
|---|---|---|---|
| Voice chunks | A-31: 3-15 s VAD chunks | fixed 8 s windows, tail >= 3 s, no VAD inside answers | package chunks + voiced_frac >= 0.25 |
| ECAPA enrolment | A-16: prior meetings, fixed threshold per chair | same-meeting opening, threshold from the opening only | package rule (causal, live-implementable); labelled |
| Variance floor | locked: "variance floor", value open | 1e-6 (effectively none) | 0.01 (A/D), 0.005 (blendshapes) at analysis time, plus the G4 25% rule |
| Upper-face composite | A-32: the single H3 output, not defined | upper-face blendshapes listed, no composite | defined in 4.3 |
| Identity model for H3 | A-32: name before processing | SFace | SFace, named here |
| A/V skew | A-33: estimate and shift | not estimated | not corrected (cannot break causality) |
| Reference platform | R3-42: local GPU; HiPerGator a replication | HiPerGator | HiPerGator is the reference here; any local replication reports agreement |
| H4 test | merged plan: Clark-West | - | Clark-West one-sided, decision p from t(G-1) |
| Gate after G3 NO-GO | R2-26: H2-H4 not run (p = 1) | - | unchanged in the register; this file runs them as exploratory only |

## 9. Order of operations

1. **This file** is hashed and committed before any voice or face feature is computed.
2. **Package runs on HiPerGator** (no market data there). The stamped tables are copied back.
3. **Feature QA, gates and kill switches** (3.4, 3.7, 4.2, 4.3) run with no return read. Their outputs and
   the hashes of the feature tables are written to `qa/`.
4. **H4 training fit:** written and hashed before any 2023-2026 join.
5. **Positions:** written with hashes before prices are joined (ADDENDUM 9.2).
6. **One run** from the frozen code, which reuses the ADDENDUM code (`presser_bt/backtest/code`, hash recorded)
   for clocks, bars, costs and bootstraps. A bug found after the join is fixed in a dated note. The first result
   is kept and shown beside the fix.
7. **Data handling.** Market data (licensed) stay in `C:/Users/hoang/.cache/gqh/presser/` and are never committed
   or copied to HiPerGator.

## 10. Prior exposure when this was written

- **H1 has been run.** BENCH-R, H1-primary (G3 NO-GO) and the H1 rows had been computed before this file.
  - The text-only arm of H4 and the answer-level target series are therefore non-blind.
  - The author of this file has seen the G3 verdict but has not opened the H1 result tables.
- **Voice and face are blind.** No voice or face feature value has been seen (see the top of the file).
- **Already seen:**
  - the literature priors in 6.2;
  - the timing and eligibility columns of events.csv (no return columns);
  - the column names of the text label.

## 11. Input manifest (SHA-256 when this was written)

```
88cc54a869e7cf540d561a257a3203524392cd1cbe18d25560f397b926651846  preregistration/presser_team_FINAL_PLAN.md
1921b2ca1dc6e646b95ee1d1bbc3e3ef7f6a864c06cd724956df7c6569de2dc4  preregistration/presser_ADDENDUM.md
ddf8ec6fb993c652c07a5e8e9ec99dfa046f13460125878cdecee703a32c5988  research/fed_presser_plan/MERGED_FINAL_PLAN.md
6c2ef2d274b52dbff0c29ca79f430fff081198ed801d4fce6fc1c7a854650031  hpg/fedpress_pkg/config.yaml
eb3a8aa4fd3e0267aad03bbe1ea2df7275af7a0630bceede603e4d3e944be18b  hpg/fedpress_pkg/fedpress/stages/voice.py
e3b641c42615219978d6683fd25806e29579aa52af3afcaab99bd0669a458acc  hpg/fedpress_pkg/fedpress/stages/face.py
babb80aebe0b923ad7bf5f3e3fe8b286740b78d60166c8c752829fae9b9142e7  hpg/fedpress_pkg/fedpress/stages/_face_models.py
a6c9f8ca099f4619ed5719688c477861ba0f98970dae1067832784617fad67f6  hpg/fedpress_pkg/fedpress/stages/diarize.py
679f5e744ae70c47ffefa5f87f250ceb98c8f0831b435115a14cd630139a2c43  hpg/fedpress_pkg/fedpress/stages/aggregate.py
81d49215e2a8683c7e3a4c3c32fc40e0d663e99914bf5e9ed2f280a740573181  hpg/fedpress_pkg/fedpress/baselines.py
13ace9983e24418ebc8c8df1cd270a24c7931d93fc82cb1790a6cf477cedbcae  presser_bt/events/events.csv
146f281ad82b6478f0955d01b6913bbc4eb7149770264b269dbb1f0a3111afd6  presser_bt/text_chrono/answers.parquet
c9196464e066b025f153f7e7e32eb275e7d6eb691dc8332c8b6ee86733bdd028  presser_bt/text_chrono/meetings.parquet
```
