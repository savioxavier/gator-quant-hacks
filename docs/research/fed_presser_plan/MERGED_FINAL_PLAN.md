# FOMC press-conference research plan: merged final

Dated 2026-10-03 (written from 18:55 EDT). Label of this pass: `final`. This is the reading copy of the plan. It merges
the team's hardened plan (`team_FINAL_PLAN.md`, whose pre-registered family is LOCKED), our independent `plan_v0.md`,
the gap review (`GAP_REPORT.md`), team deviation D1 with Update D1a (`DEVIATION_D1_stance_model.md`) and three review
rounds (`merged_plan_v1.md` r1_patch, `merged_plan_v2.md` r2_patch, `merged_plan_v3.md` r3_patch). `merged_plan_v3.md`
stays the full-text record of every amendment with its evidence; this document states the rules that are in force,
resolves the contradictions left in v3 (section 6) and adds the final-pass amendments F-01..F-11.

**How to read**

- Section 2 quotes the locked family verbatim. Nothing in it is edited. Every change elsewhere is an amendment with an
  id, the date 2026-10-03, a type and an approval need.
- Ids: `A-nn` gap review and round 1; `R2-nn` round 2; `R3-nn` round 3; `F-nn` this final pass.
- Types: **COR** correction (factual error or mis-implementation of the stated intent); **IMP** implementation detail
  (fixes a fork without altering a locked hypothesis); **CLAR** clarifying amendment (the locked text is ambiguous; the
  team ratifies one reading in writing, dated, in PREREG-R; the stated default applies irrevocably if it does not);
  **EXT** separately pre-registered extension (own id, sample and rule, filed before results; can never replace, rescue
  or be promoted over a locked result); **DIAG** diagnostic (labels only); **DATA** new data that needs the user's
  approval of a printed quote.
- Approval tags: **[T]** team ratification in PREREG-R; **[A]** written attestation by each team member; **[U]** the
  user's decision (money, publishing, pushing code, messages, compute allocations); **[S]** an external party (the
  HiPerGator sponsor, the model authors); **[–]** none beyond being recorded and hashed in the pre-registration.
- "PREREG-R" is the timestamped record of rules and ratifications, made before any stance score of a registered
  meeting is computed or viewed (R3-04, F-03). "PREREG-D" is the timestamped record of data, checkpoints, score tables
  and operating characteristics, made after PREREG-R and before any market join. "PREREG" alone means PREREG-D, except
  that every ratification belongs to PREREG-R.

**Path shorthand.** `plan/` = `<solo-repo>/research/fed_presser_plan/`; `hpg/` =
`<solo-repo>/research/fed_presser_hpg/`; `<scratch>/` = the research session scratchpad
(`%LOCALAPPDATA%/Temp/<session-tool>/D--AUTOMATION/<session>/scratchpad/`); `bt/` =
`<scratch>/presser_bt/`; `cache/` = `<home>/.cache/gqh/presser/`; `<team_push>/` = `<scratch>/team_push/`
(clone of origin/review/strategy-01); `v2/` = `<solo-repo>/research/fedspeak_v2/`.

No AI attribution. No paid download until get_cost is printed and is inside remaining Databento credit (team rule).

---

## 0. Status on 2026-10-03, 18:55-19:07 EDT (facts, not rules)

- **Timing.** The hackathon entry (a different, already-built strategy) is due 2026-10-04 10:00 ET. This project starts
  2026-10-05. Next pressers: 2026-10-28 (Warsh; measurement-only in every case) and 2026-12-09.
- **Compute.** One local RTX 5090 32 GB, the only GPU on the host (`nvidia-smi`, 18:52 EDT; 15.6 GB in use by other
  processes at that moment), shared with the local LLM stack and guarded by the 12VHPWR guard. HiPerGator partition
  `hpg-b200` (B200 180 GB) under group `jie.xu`, at most 2 GPUs per session (the user's rule).
- **Sample.** 75 held pressers 2016-2026 (Yellen 8, Powell 64, Warsh 3), i.e. 73 scheduled plus the unscheduled
  2020-03-03 and 2020-03-15 (`hpg/manifest/pressers.csv`; 95 pressers 2011-2026). Confirmation pool: 27 Powell pressers
  2023-02-01..2026-04-29. Scheduled 2016-2022 pressers: 43. Warsh pressers held: 2026-06-17, 2026-07-29, 2026-09-16.
- **Nothing decisive exists.** No stance-model H1-primary result exists. No ratification exists. The locked family has
  no commit or timestamp (`research/` is git-ignored, `.gitignore` line 9).
- **Data on disk** (R2-00). `cache/` holds ohlcv-1m and ohlcv-1s (ZT/ZF/ZN/ES) and bbo-1s (ZT/ZN/ES) for the 75
  presser days 2016-03-16..2026-09-16, 13:30-16:30 ET, written 16:42-17:06 EDT. No recorded user approval of the 1s or
  bbo-1s purchase is known to this plan.
- **Outputs that read outcomes or score presser text, all sealed** (nobody who ratifies, writes PREREG or labels for
  D-VAL-W/D-VAL-C opens them; inventories hold names, sizes, times and SHA-256 only):
  1. `bt/backtest/results/`, `tables/`, `positions/` (17:48-17:57): BENCH-R 2016-26, lexicon H1-primary and
     H1-answer (2023-2026 τ→16:00 windows read), 1 s latency sweep, spreads (R2-00, R2-03).
  2. Chrono smoke, audit, true_smoke and integration outputs (17:39-18:27) on 2017, 2020 and 20200303 presser text,
     plus production-key checkpoints trained under the dataset label rule (R3-02).
  3. **New (F-01):** `<scratch>/chrono/full/` (started 18:36 EDT from the fedspeak_v2 environment): 36 fine-tunes,
     per-calendar-year keys 2015-2026 x seeds 42-44, trained 18:37-18:53; per-year scores 2015-2026 written
     18:53-18:56, including `presser_answers_chrono.parquet` and `presser_meetings_chrono.parquet` (18:56).
     fedspeak_v2 scores every document and press-conference answer dated in year Y with model Y
     (`v2/HYPOTHESIS_v2.md` l.68), so chrono scores of 2023-2026 presser answers now exist outside the record.
  4. **New (F-01):** `<scratch>/placebo_chain/` (18:52-19:07): its README says "random stance scores, not results";
     it also wrote BENCH-R trades, break statistics, cost hurdle, USMPD and per-meeting BENCH-R tables (ZT/ZF/ZN/ES),
     per-meeting lexicon H1-primary tables, spreads by presser phase, lexicon 2016-2022 robustness, answer
     positions, fedspeak_v2 in-sample files and summaries from the real cache.
- **Package.** `hpg/` now implements the source-date label rule but keeps most other pre-amendment defaults (F-08); no
  H1 input may come from it until section 3.12's edits are made.

---

## 1. Bottom line (team text, with dated corrections in brackets)

The papers we opened do not show tradable post-answer predictability net of latency and costs.

- Gorodnichenko, Pham, Talavera (AER 2023): 36 pressers, 692 answers, 2011–2019. The ~75 bp SPY figure is a daily
  local projection over several days, not a same-minute fill. Minute-level impact is ~1 bp and imprecise. Do not cite
  75 bp as an intraday edge. [A-15: its answer-level human ratings are the D-VAL benchmark.]
- Curti & Kazinnik (JME 2023): Azure face; contemporaneous minute-level co-movement; the "−0.53 bp / 3-min" figure is
  from discussant slides, UNVERIFIED as a published coefficient. Azure emotion retired 2023-06-30.
- Gómez-Cram & Grotteria (JFE 2022): 41 pressers through Jan 2020; 13:50–14:20 predicts the presser window. Narain &
  Sangani (IJCB 2026) report reversal under Powell after COVID. BENCH-R is split pre-2020 vs 2020–26.
- Shah, Paturi, Chava (ACL 2023): combined F1 ≈ 0.71; presser-only F1 ≈ 0.53–0.55; CC BY-NC 4.0. [A-28: the Hub API
  shows `gated: manual`, sha aa3bc4281fb1fe73c8872e09ad5c64b898f90d83; no approved access exists.]
- Alexopoulos et al.: testimonies, not pressers. strategies/01 daily hawk/dove → TLT is a NO-GO.

**Realistic objects.** BENCH-R (nearest to executable; a non-blind reproduction of Gómez-Cram & Grotteria on a second
instrument, not new alpha) and H1-primary (research residual, associational on 1m OHLC, gross only). Our own studies
set the prior: costed rates and equity event edges of a few bp died after costs (ES pre-FOMC +22.8 bp, t 2.78 after 2015
vs −2.3 bp in 2024-26; auction ZN rule net Sharpe −0.22 at 1 bp/side; strategy 01 Sharpe 1.19 in 2022 vs 0.065
otherwise; A-24). [A-35: the weekend is the hackathon; this project is still not an 88-video or ~75-presser multimodal
Sharpe.] [A-27: compute is the local RTX 5090 plus HiPerGator B200, not an RTX 4050 on CPU; the CPU path stays as a
fallback for teammates.] Voice and face stay Powell-only secondaries with kill switches; Warsh is text only.

---

## 2. Locked pre-registered family (verbatim; LOCKED)

| Id | Spec | Role |
|---|---|---|
| H1-primary | Meeting-level mean(hawk(Q&A)) − hawk(statement); Q&A only; ZT; next 1m open after τ; residual position after 13:50–14:20; chair dummy | Only residual GO/NO-GO |
| H1-answer | Next-open → +1m / +5m (then +15m appendix); non-overlapping; meeting cluster | Diagnostic only |
| BENCH-R | Sign(13:50–14:20) from 14:20 to presser-end; ZT; {2, 4} ticks/side; split at 2020 | Replication / regime check |
| H1-Q | H1 + question hawkishness | Robustness (collider risk) |
| H2/H3 | vocal_proxy / expression_proxy; prior-meeting same-chair z; Powell only; 4-meeting burn-in; variance floor; identity gate | Secondary; off for Warsh |
| H4 | Combined vs text on 2023–2026 Powell after H1 frozen + code hash | Secondary |
| Lexicon | Frozen strategies/01 20+20 | Negative control |

Locked notes (verbatim): "Opening remarks excluded. 2016–2022 RoBERTa scores are classifier-contaminated (ACL data
through 2022); confirmation = 2023–2026 Powell. 2022 vs rest and SEP dummy are robustness. Next-day not primary. No LLM
in the primary path. No 1s bars without a new user-approved quote. Primary rates name = ZT.c.0. Do not use SR3.c.0 as
the Gómez-Cram 60-month Eurodollar analogue (front SR3 is ~one quarter; dated 5th–8th SR3 post-2018 is robustness
only). ES window = τ → presser end; 16:00 ET is equity-only robustness. No extra symbols (NQ, FX, GC) unless H1 GO."

Other locked rules carried unchanged: "Record a start-time source per meeting ... Drop the meeting from (P) tests if
start uncertainty > 30 s"; "Frozen assumption until MBP-1: {2, 4} ticks/side on the dollar tick table ... No net Sharpe
on H1"; "freeze delay = max(measured p90, 30 s); 60 s pessimistic appendix. If p90 > 60 s, kill live (G4/G5) and ship
measurement-only. Warsh live = half-size text. Offline 1m tests do not retune 5/15/30 s"; "Holm not needed for a single
primary; secondaries cannot be promoted after looking"; "Report (A) BENCH-R costed and (B) H1 non-executable
separately"; the G0-G5 gate table (section 3.14).

**Where the amendments touch the locked text** (the locked words still govern; the amendment fixes a reading or an
input):

| Locked item | Amendment in force | Type, approval |
|---|---|---|
| "Primary rates name = ZT.c.0" | `ZT.v.0`: `ZT.c.0` is the delivery-month contract on 42 of 73 scheduled presser days (A-01) | COR, [–] (acknowledged in PREREG-R) |
| H1-primary "frozen FOMC-RoBERTa" (section A.1 text) | Team deviation D1/D1a: walk-forward chrono-bert is the scorer of record unless the team withdraws D1 (R2-01, R3-01) | team's own dated decision; score function CLAR [T] |
| H1-primary has an entry but no exit, sign or test | Exit 15:59 bar close; HC3 t with restricted wild bootstrap; two-sided by default (A-03, A-23, R3-20) | CLAR [T] |
| "ES window = τ → presser end; 16:00 ET is equity-only robustness" | τ ≈ presser end, so that window is empty; ES uses the H1 exit (A-03) | CLAR [T] |
| "start uncertainty > 30 s" | half-width of the anchor interval in the window containing τ (A-02, R2-16) | IMP [–] |
| BENCH-R "presser-end" | scheduled start + posted MP4 duration + 60 s, from metadata (R2-19) | CLAR [T], default = locked words |
| BENCH-R "{2, 4} ticks/side" | decisive statistic gross in bp; costed versions in bp with own p-values; date-dependent tick (A-04, R3-31) | COR + CLAR [T] |
| Lexicon "Negative control" | not estimable as frozen (MIN_HD gate, n = 0): recorded as its locked result; LEX-RAW Tier 3 (R3-06) | COR + CLAR [T] |
| G5 kill | terminal after one measurement presser, as locked (R3-35) | COR [–] |
| "No net Sharpe on H1" | H1 and the counted paper series are gross; costs only as hurdle lines (A-24, R3-34) | COR [–] |
| "No 1s bars without a new user-approved quote" | 1s files on disk stay unread until the user confirms the purchase (R2-03(1)) | [U] |

---

## 3. Effective specification (as amended)

Each paragraph names the amendments it consolidates. Evidence paths are in those amendments (`merged_plan_v3.md`,
sections F.1-F.8) and in Appendix E.

### 3.1 Events and samples (A-06, A-07, A-11, A-14, A-29, A-34, R2-16, R2-21, R3-05, R3-21)

- **Event table**: `hpg/manifest/pressers.csv` (95 pressers 2011-2026; agrees with USMPD on all 95 rows), validated
  against USMPD (https://www.frbsf.org/wp-content/uploads/USMPD.xlsx, updated 2026-09-17), refreshed after each meeting;
  presser flag only when posted; statement word count and a Warsh statement-format flag. 2027 dates are provisional
  (the July 2026 minutes float six meetings a year).
- **Release times per event**: 2011-2012 statement about 12:30, SEP 14:00, presser 14:15; 2020-03-03 10:00 / 11:00;
  2020-03-15 Sunday 17:00 / 18:30; otherwise 14:00 / 14:30. The two unscheduled 2020 events are excluded from the
  H1-primary and BENCH-R main tests and reported separately (dated rule).
- **Tier 0 sample**: the 27 Powell pressers 2023-02-01..2026-04-29. The decision n is the realised count that passes
  the clock rules of 3.3, frozen in PREREG-D with its per-year composition, the dropped list and an MNAR check on
  outcome-free covariates (year, SEP, chair answer count). 2022-11-02 and 2022-12-14 stay out. Today 20 meetings are
  anchored with the v0 anchors (2023: 3, 2024: 7, 2025: 7, 2026: 3); the R2-16/R3-13 recomputation and the IA check of
  the 7 uncaptioned dates (R3-18) set the final count.
- **H1-clean** (Tier 2): the 43 scheduled 2016-2022 pressers that pass 3.3 (about 38 with today's anchors), on the
  walk-forward scores. **H1-pooled** (Tier 3): the 70 scheduled 2016-2026 Yellen and Powell pressers.
- **BENCH-R**: 2011-2019 (40 pressers) vs 2020-2026, split at 2020-01-01 as locked; Jan 2020 reassignment is a
  sensitivity. 2016-2019 instead of 2011-2019 would be a deviation.
- **Prospective (Tier P)**: every presser whose 14:00 ET release is after both the PREREG-R timestamp and the hashed
  manifest of the checkpoints that score it; earlier pressers are measurement-only (R3-05(2)).

### 3.2 Instruments, data and costs (A-01, A-04, A-13, A-18, A-21, A-24, R2-03, R2-20, R2-22..R2-24, R2-33, R2-34, R3-31, R3-33, R3-34, R3-38)

- **Instrument (COR A-01)**: `ZT.v.0` (Databento volume rule, ranked on the previous day's volume, no look-ahead);
  robustness `ZF.v.0`, `ZN.v.0`, `ES.v.0`. `symbology.resolve` output (instrument_id, raw symbol) frozen per presser day.
  Event-window check from free record counts: trades(`.v.0`) ≥ 2 x trades(`.v.1`); era-relative bar-count floor in
  PREREG-D. Paper contracts: ZTZ6 on 2026-10-28, ZTH7 on 2026-12-09. No extra symbols unless H1 GO (locked).
- **Ticks and fees (COR A-04)**: ZT $15.625 per tick through 2019-01-11, $7.8125 from 2019-01-14 (CME SER-8171); ZF
  $7.8125; ZN $15.625; ES $12.50; all-in fee $2.00 per side per contract (UNVERIFIED; replace with the broker's
  schedule, [U]).
- **Feed eras (IMP R2-22)**: CME legacy FIX/FAST history to 2017-05-20 (`F_BAD_TS_RECV`, SendingTime clock); MDP3
  2017-05-21..2019-01-11; MDP3 with the new ZT tick from 2019-01-14. Eras apply to floors, spread tables, staleness and
  costs; no spread difference across 2017-05-21 is interpreted.
- **Bar and quote conventions**: OHLCV ts_event is the bar start; "next 1m open after t" = the first bar with ts_event ≥
  t; empty minutes are skipped and logged; tz-aware America/New_York. BBO: ts_recv is the interval end; the quote at t is
  the last record with ts_recv ≤ t, carried forward, flagged when older than 5 s (ZT) or 1 s (ES); bid and ask levels
  only, never the record's price field (the last trade). Spreads are labelled "outright book, implied excluded (upper
  bound on spread)" (R3-33).
- **R_stmt (IMP R2-20)**: log close of the 14:19 bar minus log close of the 13:49 bar on `ZT.v.0` (era windows shifted:
  12:19 / 12:49 in 2011-2012), used offline, live (next day) and in BENCH-R. R_pc = 14:19 close to the close of the bar
  before the H1 entry bar.
- **Reading rules (R2-03, R3-05)**: the 1s and bbo-1s files are not read by any plan script until the user confirms
  the purchase; for the named event list (the 27 confirmation meetings, the H1-clean, H1-pooled and BENCH-R history and
  the Warsh pressers to 2026-09-16) no record of any schema after 14:20 ET is read before PREREG-D; any future request
  for those dates is split into pre-14:20 and 14:20-16:30 files. Later events follow the live rules (3.10).
- **Extras (DATA, [U])**: each gets a free printed get_cost first: 2011-2015 ohlcv-1m (about $0.04; A-06); P1 windows
  from about 13:11, the previous trading day (P3, run-up R3-28) and next-day 15:00 (R2-24); `ZF.v.0` bbo-1s for the 75
  cached days ($0.96; R3-33); optional MBP-1 ZT+ES ($29.39). Remaining Databento credit is unknown. A row whose extra is
  not approved is "not computable" in PREREG-D.
- **Costs**: H1 is gross, with a cost-hurdle line in bp of window sd and no net P&L or Sharpe (locked; A-24). BENCH-R
  is costed per 3.6. Measured spreads (A-13) and quote fills (at the locked entry instant, R2-34) follow the user's
  confirmation of the bbo-1s purchase. One paper cost model: quote fill at the as-of ask/bid + fees + 1 tick slippage
  per side in the era's tick; the {2, 4}-tick stress applies only to mid-to-mid or trade-price P&L (R2-33, R3-37(4)).
- **Vendor condition (R2-23, R3-38)**: `get_dataset_condition` is stored per event day; 2024-09-18 and 2025-09-17 are
  degraded (Tier 3 row without them). Post-PREREG pulls: no earlier than 25 h after the window end (the pull helper
  asserts request_end ≤ now_utc − 25 h), condition "available", SHA-256 stored, the first file governs, re-fetched at
  T + 30 days and hash-compared. Databento: historical data is "24 hours into the past"; intraday or delayed data need
  an exchange licence (https://databento.com/blog/introduction-market-data-licensing).

### 3.3 Clock: τ and τ_used (A-02, A-05, R2-16..R2-18, R3-13..R3-16, R3-18)

- **Words and in-video time.** Words come from the transcript PDF. In-video times come from CTC forced alignment
  (`jonatasgrosman/wav2vec2-large-xlsr-53-english`, revision 569a623, through WhisperX 3.8.6, pinned; explicitly not the
  WhisperX English default), seeded from pinned Whisper ASR and never from the captions, padded ≥ 2 s, cut at VAD
  silences. Qwen3-ForcedAligner is a cross-check outside the primary path ("No LLM in the primary path").
- **Official WebVTT** (83 files; 68 of the 75 2016+ pressers; 21 of 27 confirmation meetings; missing 20221214,
  20230614, 20230726, 20231101, 20231213, 20240320, 20251210) gives speaker labels, segmentation and the `vtt_mapped`
  clock after per-file QA. Gorodnichenko answer times are used only to cross-check 2016-2019 segmentation and flag broken
  caption files, never as a wall clock.
- **MP4 completeness on the MP4 clock (R3-15).** Decode the first and last 180 s of each MP4 with the pinned Whisper,
  measure the VTT→MP4 offset, then: complete iff the last PDF chair word is recognised (fuzzy ratio ≥ 0.8, word
  probability ≥ 0.5), ends ≤ MP4 end − 0.2 s, and its duration lies within the meeting's p1-p99. Complete →
  `clock_source = aligner`. Truncated with a VTT → `vtt_mapped`, valid only if the TV intervals before and after the MP4
  end of the same item overlap with abs(Δhi) ≤ 5 s (R2-18(3)). Otherwise (C) only. `clock_source` is frozen per meeting
  before PREREG-D.
- **Last chair answer (R3-15(3))**: the last chair turn of ≥ 20 words that follows a reporter turn; a later closing
  chair turn of < 20 words is appended; τ = the end of the appended closing.
- **Wall-clock anchor (A-02, R2-16, R3-13, R3-14).** Sources: TV News Archive and GDELT caption segments of the CNBC
  and FBC items airing at τ (14:00 ET Power Lunch; 15:00 ET Closing Bell / Claman Countdown); Bloomberg first-word
  headlines, if UF library terms allow (unverified), are a cross-check that enters H only by a dated amendment filed
  before PREREG-D. Per (source, station, item): per-cue bounds, lo = P80 and hi =
  P20 over live matches (abs(implied offset) ≤ 300 s, replays excluded); window W_τ = trailing [τ − 600 s, τ] with ≥ 20
  live cues of the item airing at τ (answer-level fallbacks: the item's leading 600 s window, then the previous item's
  trailing window).
  **τ_used = τ_media + scheduled-zero conversion + H + M**, with M = 30 s and H = the maximum over available (source ∈
  {IA, GDELT}) x (station ∈ {CNBC, FBC}) of max(hi(W_τ), hi(W_first)); cues are never mixed across source, station or
  item. A missing source or station adds Δ_missing, the frozen p90 of (H_all − H_subset) over complete 2016-2024
  meetings. GDELT is re-pulled for scheduled +30..+75 min (free API).
  **Drop rule (locked criterion)**: half-width of the W_τ interval > 30 s → (C) only; fewer than 20 cues counts as
  > 30 s. Windows of one source and station more than 60 s apart (broken timeline) → (C). Both thresholds other than
  the 30 s half-width are dated implementation details.
- **Never** set offsets from market data; market cross-correlation is a diagnostic only.
- **ε (archive time base; R2-17, A-02(7)).** Calibrate on 2026-10-28 / 2026-12-09 recordings; a caption-capture tuner
  or IPTV feed gives a one-sided bound if the user has one ([U]). Whether or not ε is calibrated, the M + 15 s and
  M + 30 s reruns are reported; the "not robust to clock" label follows R3-19; without calibration the clock is labelled
  "margin uncalibrated".
- **H1-primary-FC** (Tier 3): dropped meetings with a media τ use +180 s + M; never in G3, H1-answer or H1-run.
- **Records (A-02(9), R2-15(3), R3-18)**: per-cue match tables without caption text (media time, item id, segment
  offset, PDF word index, trigram count, page SHA-256, retrieval time). Raw caption pages stay private and sealed, never
  deleted, until the anchors and realised n are frozen in PREREG-D.
- **Live and H1-P clock (R3-16)**: τ_used = NTP-corrected arrival time of the HLS segment that contains the end of the
  last chair answer + the logged NTP uncertainty; M_live = 0; PDF text aligned only within contiguous segment runs; if
  the recording fails, the TV-archive clock is used and flagged; the event is never dropped.

### 3.4 Text scorer and score function (D1, D1a, A-10, A-14, A-29, A-30, R2-01, R2-05..R2-15, R3-01, R3-03, R3-08, R3-10..R3-12, F-02)

- **Scorer of record (default; option D1 of R2-01).** For meetings in year Y: `manelalab/chrono-bert-v1-<min(Y−1,
  2024)>1231` (MIT, ungated; ModernBERT base; loaded with `reference_compile=False` on every platform, R3-12) fine-tuned
  on `gtfintechlab/fomc_communication` rows whose **source date** is before Y-01-01, taken from the pinned
  `label_dates.parquet` at the version pinned in PREREG-R (today SHA-256 16a54100…, identical in
  `<team_push>/data/text_corpus/` (18:31) and `hpg/manifest/` (18:53); 2,480 rows, all dated; TDW commit 98646987;
  dataset revision 6b0283f5; F-11); undatable rows excluded from every model with Y ≤ 2022 (R3-01). Settings = fedspeak_v2 Amendment
  2: 15% stratified validation split (seed 0), lr 2e-5, batch 16, max length 256, at most 8 epochs, patience 2, weight
  decay 0.01, 10% warmup, seeds 42/43/44 with class probabilities averaged.
- **Keys (R2-05, R3-03(1))**: b2010_l2010..b2021_l2021 (test years 2011-2022; 2011-2014 serve D-VAL only),
  b2022_l2022 (2023), b2023_l2022 (2024), b2024_l2022 (2025, 2026 and 2027): 15 keys x 3 seeds = 45 fine-tunes; one set
  per key, shared by every year mapped to it.
- **Training (R2-05, R3-03(3))**: once, on the local 5090, float32, `torch.use_deterministic_algorithms(True)`,
  `CUBLAS_WORKSPACE_CONFIG=:4096:8`, `attn_implementation="sdpa"`, pinned torch/transformers; the fingerprint records
  host, GPU, driver/CUDA, library versions, deterministic flags, attention implementation, `reference_compile`, label
  rule, label-table hash and code tree hash; frozen runs reject checkpoints from a non-reference host. Checkpoints and
  the full sentence-score table are hashed in PREREG-D; a retrain gets a new id. HiPerGator replicates only (3.12).
  **Quarantined, never an H1 input**: every checkpoint trained under the dataset or "redated" rule, the R3-02
  smoke/integration checkpoints and the fedspeak_v2 full-run set of F-01 (F-02).
- **Score function (CLAR, [T]; default = R2-01(2)).** Pinned `nltk.sent_tokenize`; qualifying units = chair Q&A
  sentences without "?" that pass the TDW A1/B1 keyword filter, then the TDW clause split (but / however / even though /
  although / while / ";" with a keyword on each side); max length 256 with tail truncation logged; unit label = argmax
  of the averaged probabilities; term score = share hawkish − share dovish over the qualifying units pooled over the
  meeting's chair Q&A (A) and over the qualifying statement units (S); s = A − S. Opening remarks are excluded (locked).
  Meetings with < 10 qualifying Q&A or < 3 statement units are flagged, never dropped. **Construct note (R2-11, part of
  the ratification):** "hawk(statement) = tone of filtered assessment sentences; decision, guidance and balance-sheet
  sentences are excluded by the TDW rule" (rate-decision sentences pass 1 of 27 confirmation statements). Alternatives
  the team may ratify instead, in PREREG-R only: team_push's unfiltered equal-weight answer mean (the default then
  becomes the Tier 3 row) (R3-03(1)); the single `b2022_l2022` base for all of 2023-2026 (H1-1base becomes the primary,
  D1 as written Tier 3) (R2-13). Tier 3 variants: D1 literal (unfiltered), P(h) − P(d), answer-weighted mean.
- **Scaling (CLAR R3-10, [T])**: each term centred on its own document type's reference units (pre-2016 units for bases
  serving 2016+; units dated before the first test year for the 2010-2014 keys), both scaled by the sd of the pooled
  reference unit labels floored at 0.25; factors printed per base in D-VINTAGE.
- **Validity checks before any market join**: accuracy gate = pooled rolling-origin macro-F1 over the 2016-2022 source
  years ≥ 0.55, threshold confirmed in writing before any gate number exists (R3-01(3)); a fail postpones G3, no other
  scorer is swapped in (R2-01(4)); presser-domain macro-F1 on the 218 presser rows, < 0.45 labels "measurement weak
  (presser domain)" (R2-10); D-VAL-C on the three Tier 0 bases (R3-08); fill-mask cutoff probe per checkpoint (R3-12);
  D-VINTAGE (R2-13); training-row audit printing 0 rows from documents dated Y or later for every Y ≤ 2022 (R3-01(4)).
- **Option v1 (alternative, [T])**: the team withdraws D1 in a dated, hashed note before any chrono presser score is
  viewed; then frozen FOMC-RoBERTa (revision aa3bc42) is the scorer under A-40: official weights through the gated route
  verified by 2026-10-14 (identity = pinned commit + LFS oid + SHA-256; label-map agreement ≥ 0.90 on 63 published
  pressers, R2-06; weight history R3-11), else H1-primary is postponed, never replaced.
- **Other scorers**: FOMC-RoBERTa enters Tier 2 as **H1-RoBERTa** only if its weights pass R2-06 and R3-11 before
  PREREG-D (else p = 1), later Tier 3. Unofficial re-uploads are never used. CentralBankRoBERTa measures agent sentiment,
  not stance, so it is neither a cross-check nor a fallback (A-30). Loughran-McDonald stays an academic cross-check.
- **Code base (CLAR R3-03, [T]; default `hpg/fedpress`, F-06)**: the team names one code base for every Tier 0-2,
  D-VAL, gate, residualiser and live score and records its git tree hash in PREREG-R; the other is superseded and writes
  no H1 input. Smoke: `SMOKE_ID=20200303`, smoke-only models, no `h1_gap` or `hawk_statement` printouts; the text stage
  refuses a registered meeting unless a PREREG hash file lists the checkpoint; `bt` s02/s03 stop if a stance `H1`
  column holds values before a timestamped PREREG manifest exists.
- **Cutoff registry (A-29)**: semantic models (stance, embeddings, vocal and facial affect) enter a confirmatory or P&L
  analysis only if their cutoff precedes the meeting; transcription, alignment, VAD and speaker verification are exempt
  (checked against PDF, captions and anchors). The chrono tokenizer is not chronological (R2-15(1)); post-checkpoint
  token share is logged.

### 3.5 H1-primary and G3 (A-03, A-09, A-11, A-12, A-23, A-40(g), R2-26..R2-28, R3-04, R3-20, R3-22)

- **Entry**: the open of the first `ZT.v.0` 1m bar with ts_event ≥ τ_used (locked "next 1m open after τ"; for a
  meeting-level mean τ is the end of the last chair answer).
- **Exit (CLAR A-03, [T])**: the close of the 15:59 ET bar (the last bar before 16:00 ET); ES uses the same exit;
  next-day 15:00 ET settlement is robustness only.
- **Model**: y = log return entry→exit; y ~ 1 + s + R_stmt (Frisch-Waugh for the locked "residual position after
  13:50–14:20"); the chair dummy is constant in the confirmation sample and dropped there.
- **Statistic and decision p (A-23)**: HC3 t of the s coefficient; restricted wild bootstrap (null model y ~ 1 +
  R_stmt; Rademacher weights; 9,999 draws; seed in PREREG-D). v0's unrestricted slope bootstrap had size 0.126 at a
  nominal 0.05; the restricted HC3 t has 0.051.
- **Sidedness (CLAR, [T]; default two-sided)**: continuation means a hawkish residual surprise predicts a fall in ZT.
  If the team ratifies one-sided continuation, PREREG-R records that a reversal edge is untestable in this family.
- **Critical value (R3-20(1))**: G3 rejects iff the t statistic exceeds the larger of the WRE 5% critical value and the
  95% quantile of the same statistic in the fixed-design null simulation at year ICC 0.05 on the frozen s and R_stmt.
- **Published in PREREG-D before any market join**: realised n and composition, false-GO rate, power at r = 0.2 and
  0.3, MDE, the PPV of a GO at prior π = 0.1 (R2-27), and the firing rates of every label (R3-19(2)). Reference values:
  n = 20 two-sided power 0.13 / 0.25, MDE 0.59; n = 27 two-sided 0.17 / 0.33, MDE 0.52. A NO-GO at n ≈ 20 is
  uninformative ("not detected"; the 90% CI upper bound is reported).
- **Single shot**: G3 runs once, from the frozen hash, as the first PREREG-D script of the code base of record to read
  2023-2026 records after 14:20 ET (earlier parallel reads are in the access log). A bug found after the join is fixed
  in a dated note; the frozen result stays the verdict and the "verdict depends on a post-freeze fix" label applies if
  they disagree.
- **Wording**: a GO is "association detected (PPV ≈ x at π = 0.1), not an edge"; edge or real-money language needs
  H1-P's first passing look in the GO direction and a licence path (A-30, A-43). Every P&L sentence carries p,
  sidedness and n.
- **After a NO-GO (R2-26)**: Tier 1 runs; H2, H3 and H4 do not run (p = 1, the locked "do not mine H2"); H1-clean, H1-A,
  H1-PX, H1-run, H1-RoBERTa and the 2016-2022 rows run only as "post-NO-GO descriptive" with "cannot rescue G3"; Tier P
  continues; the write-up reports the G3 verdict first.
- **Trading residualiser (A-09, R3-22, R3-40)**: for positions and paper trades only, s̃ = s − (a + b·R_stmt) with a, b
  from an expanding window of prior uncontaminated meetings from 2022-03-16, a = b = 0 until 8 exist; a "trade-implied"
  t is reported beside G3 and labelled.

### 3.6 BENCH-R (A-06, A-07, A-08, A-19, R2-19, R2-20, R2-29, R3-31, R3-32, F-05)

- **Signal**: sign(R_stmt) (13:50-14:20; 12:20-12:50 in 2011-2012); sign(0) = no trade; the effective n and the share
  of sub-tick signals are reported per regime (12.5% of 2011-19 and 18.9% of 2020-26 events on USMPD UST2Y; 44% in
  2020-01..2022-02).
- **Entry**: the first 1m open at or after 14:20 ET in every era (keeps the 2011-2012 SEP release out of the hold).
- **Exit (CLAR R2-19, [T]; default = the locked "presser-end")**: the open of the first 1m bar at or after scheduled
  start + posted MP4 duration + 60 s (metadata only; defined for all 93 scheduled pressers). BENCH-R-P uses the same
  rule with the duration frozen at T + 30 days (R3-32).
- **Decisive statistic (CLAR R3-31, [T]; default)**: the gross mean of sign(R_stmt) x the log return in bp, restricted
  wild / studentised sign-flip scheme, with the covariance / drift split and an intercept companion (R2-29). The locked
  {2, 4} ticks/side are the costed versions: gross minus 2 or 4 era ticks per side plus the fee, in bp per meeting,
  each with its own p-value outside Holm; the A-19 hurdle table is computed on both exits (F-05).
- **Tier 1 (Holm m = 3)**, named "reproduction on a second instrument (ZT vs USMPD UST2Y), non-blind": the 2011-19 mean
  (one-sided continuation), the 2020-26 mean (two-sided), the break (two-sided). BENCH-R is also reported on USMPD UST2Y
  on identical windows. The write-up attributes no cause to a break (chair change, COVID, the lower bound, the 2019 tick
  cut, the 2017 feed change, SEP composition, presser length and the 2022 publication are not separately identified).
- **USMPD QA (A-07)**: after PREREG-D, a frozen script reads statement windows only and writes flags (abs(ΔUST2Y) > 2 bp
  with ZT moving the wrong way or < 25% of the implied move); fixes only for instrument or vendor errors, in a hashed QA
  addendum before any outcome script; a clock is never changed from market data.
- **Extensions**: BENCH-R-ES break (Tier 2); BENCH-R-P (Tier P, the only blind BENCH-R evidence); Tier 3 rows in 3.8.

### 3.7 The other locked rows

- **H1-answer (diagnostic only; A-22, R3-14)**: signal = hawk(answer) − hawk(statement) with the 3.4 function,
  residualised as A-09; confirmation meetings whose answer windows pass 3.3; greedy earliest-first non-overlapping
  selection over chair answers of ≥ 40 words, separately per horizon (+1m reported; +5m and +15m descriptive); restricted
  wild cluster bootstrap by meeting (Webb weights); results by clock source. H1-answer-mid (bbo mids) and H1-answer-1s
  (τ_used + 30 s, anchor width ≤ 10 s, Warsh-only in practice) are Tier 3 and need the user's confirmation of the bbo-1s
  and 1s purchase.
- **H1-Q (robustness; R2-12)**: question score over all sentences of each reporter turn including "?" sentences, the
  ratified filter and score type, meeting mean over turns; labelled out of the classifier's domain.
- **H2/H3 (secondary, Powell only, off for Warsh; A-16, A-31..A-33, R3-42)**: vocal_proxy = audeering arousal (primary)
  and dominance, valence excluded; 3-15 s VAD chunks inside chair turns that pass the ECAPA gate (threshold fixed from
  prior meetings); median per answer and meeting; causal prior-meeting same-chair z; ICC ≥ 0.8 under a 64 kbps
  re-encode or the H2 kill switch applies. expression_proxy = MediaPipe + EmotiEffLib at 1 fps, upper-face composite as
  the single Tier 2 output, speaking-flag covariate, A/V skew corrected, identity model named before processing.
  Reference platform: the local 5090; HiPerGator output is a replication with agreement reported.
- **H4 (secondary; A-26, R2-14)**: combined weights trained on Powell 2018-2022 after the 4-meeting burn-in, on
  walk-forward chrono text scores; tested on 2023-2026 with Clark-West, after H1 is frozen.
- **Lexicon (negative control; R3-06)**: the frozen strategies/01 code scores a document only if H + D ≥ 5 (MIN_HD), so
  27 of 27 confirmation statements are NaN: the locked row's result is "not estimable as frozen (n = 0)". LEX-RAW
  (pooled counts, (H − D)/(H + D + 1), no gate, the H1 statistic) is Tier 3; a same-sign LEX-RAW slope with p < 0.05
  attaches "clock, leakage or regime confound not excluded".

### 3.8 Test register (A-45 as revised by R2-01, R2-19, R3-20, R3-21; frozen in PREREG-R, values in PREREG-D)

Every test has exactly one tier. A Holm-tier test that is not run enters with p = 1; m never changes. If the team takes
option v1, Tier 2 reverts to H1-chrono (pooled) and H1-replica with the R2-21 specification; every other rule stays.

| Tier | Rule | Tests |
|---|---|---|
| 0 | alpha 0.05; sidedness as ratified (default two-sided); the only GO/NO-GO; one pre-named scorer with weight hashes; critical value per R3-20(1) | H1-primary on the scorer of record |
| 1 | Holm m = 3; "reproduction on a second instrument, non-blind"; never called a test or confirmation; gross bp statistic | BENCH-R ZT: 2011-19 mean (one-sided continuation); 2020-26 mean (two-sided); break (two-sided) |
| 2 | Holm m = 9 (unchanged since v1); confirmation-sample tests use the R3-20(1) critical value; tests spanning ≥ 5 years use a restricted wild cluster bootstrap by year (Webb weights) with i.i.d. WRE as companion | H1-clean (2016-2022, y ~ 1 + post2020 + s + R_stmt + R_stmt x post2020 + chair + SEP); H1-A (A on S and R_stmt); H1-PX (R_pc added); H1-run (intra-presser legs, R3-14); H1-RoBERTa (else p = 1); BENCH-R-ES break; H2 arousal; H3 upper-face composite; H4 Clark-West |
| P | own alpha 0.05 each; studentised O'Brien-Fleming looks at 8 / 16 / 24 events; eligibility R3-05(2) | H1-P (HC3 t of s in y ~ 1 + s + R_stmt referred to t with k − 3 df; after a GO one-sided in the GO direction at nominal p 0.00153 / 0.0181 / 0.0437; otherwise two-sided at 0.00052 / 0.0141 / 0.0451; "prospective replication (Warsh era, live clock)"); BENCH-R-P (gross bp sign-trade mean, two-sided); the counted paper series (A-43, gross, referred to t with k − 1 df), which supports no claim beyond A-43 |
| 3 | descriptive; p printed; no claims | H1-pooled 2016-2026 and its sub-periods; H1 2016-2022 with the locked covariates; 2022-03-16 break variant; ZLB-regime and volatility-scaled rows; year fixed effects; H1-1base; score variants (D1 literal unfiltered, P(h) − P(d), answer-weighted); S_new, S_all; sentences without post-checkpoint tokens; H1-replica; FOMC-RoBERTa after the freeze; H1-primary-FC; H1-post; H1-exec30, H1-exec-live (+120 s bracket and end-detector replay); τ_used-instant quote fill; CNBC-only τ_used and the 2024-10-09 / 2025-04-01 splits; M + 15 s / M + 30 s reruns; GDELT point clock and the ADDENDUM latency sweep; H1-answer, H1-answer-mid, H1-answer-1s, STMT-ABS and H1-answer without fallback windows; D-DECOMP; PP-MKT; placebos P1, P3; LEX-RAW; H1-O, H1-A-O; H1-SEP; outgoing-chair cuts (after 2026-01-30; after 2025-06-25) and s x political share; H1-RUNUP; H1-L and y/√L; topic-mix rows; concurrent-news and morning-supply exclusions; exit at 15:49; post-publication subsample 2024-05-01..2026-04-29; H1-ZF, H1-ZN, H1-ES; H1 by cycle phase; D-STMT-PATH; BENCH-R start + 60 min, in-presser and post-presser legs, BENCH-R-d10, as-of-mid R_stmt, SEP-only break, non-SEP 2019-2026, 2011-19 split at 2017-05-21, break without legacy-feed events, without degraded days, ZF.v.0, three descriptive periods, BENCH-R-P with the live end-event exit; matched-delay H1-P; sign-only and A-only H1-P companions |
| D | diagnostics; fixed labels only | D-VAL (2011-2019 human ratings, with ρ_within and statement ρ, walk-forward 2011-2015 keys), D-VAL-W, D-VAL-C, presser-domain F1, accuracy gate, D-ASR, D-DOM (covariance shares, S_repeat / S_new, Δdot, run-up, political share, L, year share), D-VINTAGE, D-OPEN, D-TOPIC, chrono cutoff probe |

### 3.9 Interpretation labels (A-46 as revised by R2-xx rows, R3-06, R3-19, R3-23; [T])

G3 is computed only by the rule in 3.5. Diagnostics and extensions never flip it; they attach fixed labels. A variant
label fires iff the paired restricted-wild-bootstrap 90% CI of (b_variant − b_primary), on the same draws and seed,
excludes 0, or the variant has the opposite sign with abs(t_variant) ≥ 1 (R3-19(1)). PREREG-D prints each label's firing
rate given a GO under H0 and at the MDE; a label with LR = P(fire | GO, H0) / P(fire | GO, MDE) below 1.5 is demoted
to a descriptive note.

| Condition (fixed now) | Label |
|---|---|
| D-VAL lower bound of meeting-level ρ (vs −avr_score) or of answer-level ρ below 0.1; or statement ρ lower bound below 0.1 | "measurement weak" |
| ρ_within lower bound below 0.1 | "Q&A term not validated" |
| presser-domain macro-F1 < 0.45 | "measurement weak (presser domain)" |
| D-VAL-C: a base's upper bound < 0.45, or 0.10 below the others with a CI excluding 0 | "measurement weak (Tier 0 checkpoint, base Y)" |
| cutoff probe: post-cutoff top-5 hit rate above control | "cutoff not verified" (H1-clean, H1-pooled, D-VAL) |
| D-DOM corr(s, −S) ≥ 0.8 and H1-A not same-sign with one-sided p ≤ 0.10 | "statement-level association" |
| share_S = −cov(s, S)/var(s) > 0.5 | PREREG-D states "H1 largely tests statement tone" |
| cov(S, S_rep_part)/var(S) > 0.5 | "statement term is repeated boilerplate" |
| H1-PX text slope falls by > half with R_pc carrying it (R3-19 rule), or PP-MKT abs(t) ≥ H1 abs(t) | "not separable from the in-presser price move" |
| H1-O: s coefficient falls by > half with O carrying it | "Q&A content previewed in the opening remarks" |
| H1-SEP: s coefficient falls by > half with Δdot carrying it | "SEP-information association" |
| H1-RUNUP: s coefficient falls by > half | "pre-meeting positioning not excluded" |
| placebo P1 or P3, or LEX-RAW, same sign with one-sided p < 0.05 | "clock, leakage or regime confound not excluded" + dated investigation note |
| end-detector H1-exec-live row differs (R3-19 rule) | "not robust to execution delay" |
| M + 15 s or M + 30 s rerun differs (R3-19 rule) | "not robust to clock"; without ε calibration also "margin uncalibrated" |
| H1-1base differs from the primary (R3-19 rule) | "not robust to scorer vintage" |
| H1-pooled sub-period slopes of opposite sign; H1 2016-2022 locked-spec sign differs from H1-clean | "regime-heterogeneous" |
| BENCH-R break differs between the presser-end and start + 60 exits (R3-19 rule) | "break confounded with hold horizon" |
| a mean statistic and its covariance term differ (R3-19 rule) | "drift times exposure, not timing" |
| D-STMT-PATH: S's coefficient on R_pc has the D-DECOMP sign with p ≤ 0.10 | "statement-text drift; Q&A not required" |
| FOMC-RoBERTa label-map agreement in [0.90, 0.98) | "published labels not reproduced exactly" |
| post-freeze bug fix changes the verdict | "verdict depends on a post-freeze fix" |
| outcome windows read by a parallel script, no viewing attested / viewing attested | "outcome windows read by a parallel script before the freeze; contents unseen by the authors of the frozen choices (attested)" / "non-blind (outcome vector viewed)" |
| fedspeak_v2 validation or presser scores opened before PREREG-R | "exposed via fedspeak_v2 validation" (2023-02-01..2024-09-18 meetings) |
| non-spec chrono 2020 H1 values viewed; gate F1 viewed before the threshold confirmation | "exposed via non-spec smoke"; "threshold confirmed after one fold was seen" |
| D-VAL-W: Warsh − Powell balanced accuracy ≤ −0.10 with upper bound < 0, or Warsh upper bound < 0.45; kappa < 0.6 | Warsh events "measurement weak" (measurement-only); D-VAL-W "uninformative" |

### 3.10 Live path and paper trades (A-16, A-17, A-41..A-44, A-47, R2-09, R2-25, R2-31..R2-34, R3-05, R3-09, R3-16, R3-34..R3-40)

- **Object (A-42)**: the paper-traded object is H1-primary, one entry per meeting after a live end event E = the
  earliest of: the stream switches to slate or ends; the frozen closing-phrase list with no question for 30 s; no chair
  speech for 90 s (a 90 s detector falsely ends 10% of pressers; a false end is logged and the decision uses the answers
  up to E). H1-run and H1-answer are shadow-logged only.
- **Live text pipeline (A-16)**: frozen before 2026-10-28 on the local 5090: ASR model and precision, chunking,
  splitter, ECAPA chair verification (`speechbrain/spkrec-ecapa-voxceleb`, Apache-2.0) with voiceprints and thresholds
  from prior meetings only (Warsh: 2026-06-17 and 2026-07-29); decoding frozen (temperature [0.0], explicit VAD,
  seeded, fixed batch sizes; R3-17). D-ASR replays Warsh 2026-09-16 and Powell 2026-01-28, 03-18 and 04-29 with the
  minimum agreement fixed before results.
- **Recording and clock (A-17, R2-32)**: federalreserve.gov live player (there is no YouTube live stream); two
  independent recorders from 13:45 ET (HLS dump with playlists, CPU-only stream copy; OS loopback audio); NTP offset by
  query only, never a system-setting change; monotonic counter mapped to UTC every 5 min; each HLS segment dated by its
  own arrival; sequence continuity checked; PDT accepted only if PDT ≤ arrival − target duration. Schedules in
  America/New_York; the scheduler is dry-run in EST before 2026-12-09.
- **Delay (A-17(3), R2-31, R3-35)**: delay_upper = t_decision − t_ref + L_ref against independent references (live PDT
  +3 s; tuner-captured broadcast +10 s; first-word headline +30 s). The reference set and L_ref values are registered by
  2026-10-21 ([U]: a UF library Bloomberg session, a tuner if the user has one); with no reference G5 cannot pass and
  live stays measurement-only. G5 passes iff the per-answer p90 of delay_upper on the measurement presser (2026-10-28)
  is ≤ 60 s and the entry lag (ii) ≤ 150 s. **A fail kills live for the project** (locked); an infrastructure void
  stamped before the first delay sample moves measurement to the next presser and is not a retry. D_frozen = max(p90,
  30 s), never re-estimated downward; after a pass G5 is re-checked on pooled answers after each presser and can only
  kill.
- **Fill (R2-31(2), R3-37)**: t_fill = max(t_decision + 1 s, τ_wall_hi + D_frozen); if t_fill ∈ [14:59:30, 15:00:00)
  then t_fill := 15:00:00 (ZT settlement window); no trade if t_fill ≥ 15:59:00. Counted fill = as-of ask (buy) or bid
  (sell) at t_fill; mid at t_fill for the statistic; the next 1m open after t_fill is a companion only. For offline 1m
  rows the settlement rule is a no-op.
- **Commit (R3-36)**: a counted decision is committed at t_fill; only a watchdog-stamped failure in the hashed log before
  t_fill voids it; later failures are notes and the position is held to the 15:59 exit.
- **Decision log (A-17(5))**: code and model hashes, statement score, frozen a, b, σ and mapping, R_stmt definition,
  timestamped decisions; hashed locally before any market data after 14:20 ET that day is fetched. R_stmt and P&L are
  computed the next day under the 25 h rule (R3-38). The user decides once whether SHA-256 digests (only) go to
  OpenTimestamps ([U]); otherwise the log is "self-attested".
- **Position (A-42(3), R3-40)**: p = −k · sign_G3 · clip(s̃/σ, −2, 2) in ZT DV01 units (fractional on paper); k = 0.5
  for Warsh (locked half-size), 1 otherwise; sign_G3 = +1 (continuation) unless a two-sided GO found reversal. Warsh:
  b from the window starting 2022-03-16; a = w·a_Warsh + (1 − w)·a_Powell2023-26 with w = n_W/(n_W + 8); σ_event =
  sqrt(max(σ²_Powell − v̄_Powell, 0.25·σ²_Powell) + v_event) with v the binomial noise variance from the meeting's own
  qualifying counts; empty statement term → the chair's prior mean, flagged; logs record counts and v_event.
- **Counting (A-43, R3-34)**: 2026-10-28 is measurement-only whatever G3 shows (shadow decisions with D_frozen := 60 s).
  A counted paper trade is a frozen-hash H1-primary decision on a Tier P eligible presser after both a G3 GO and
  2026-10-28 (2026-12-09 at the earliest). After a NO-GO, while G3 is postponed, or for Warsh events if D-VAL-W says
  "measurement weak", every presser is measurement-only. The statistic is the studentised mean of per-event gross P&L
  (mid to mid, t_fill to 16:00:00) at looks 8 / 16 / 24; net quote-fill P&L and the {2, 4}-tick stress are hurdle lines,
  never a Sharpe. About 3-4 years for 24 events. The count is kept per scorer.
- **D-VAL-W (A-47, R2-09, R3-09)**: two blind annotators (no market data and no model output for the units) label all
  qualifying units of the held Warsh pressers and of 3 seeded 2025 Powell pressers; third annotator on disagreement;
  balanced accuracy rule in 3.9; simulated false-fail rate and power published before labelling; a verdict governs only
  events whose 14:00 release follows the hashing of its labels.
- **Runbook (A-44)**: 13:30-16:30 ET on presser days: pause the autonomous worker and coding harnesses; `C:/LLM/unload.cmd`
  by 13:45 and load nothing until 16:30; log free VRAM (≥ 16 GB) and GPU clocks; the recorder runs CPU-only; copy the
  12VHPWR guard log into the hashed decision log; a GPU, guard, OOM or power event before t_fill is an infrastructure
  failure (measurement void). No change to system or guard settings. ffmpeg is installed first (absent today).
- **Rehearsal**: replay 2026-09-16 at 1x under the runbook before 2026-10-28; the VOD-zero calibration uses the hashed
  live recording.

### 3.11 Governance: records, exposure and one code path (A-08, A-12, R2-00..R2-04, R2-35, R3-02..R3-05, R3-24, F-01, F-03)

- **PREREG-R** (rules; [T]): A-03 with sidedness; the R2-01 option and score function with the R2-11 construct note;
  R3-01 date rule and the 0.55 threshold confirmation; R3-03 code base; R2-13 base rule; R2-19 exit and R3-31
  statistic; R3-06 reading; R3-10; R3-19; R3-20 rule; R3-21; R2-21; R2-25; R2-26; A-46; R2-09 / R3-09; R3-16; the
  R3-35..R3-40 live rules; the test register (3.8); the access log and attestations. Timestamped before any stance score
  of a registered meeting is computed by the code base of record and before any ratifier views such a score from any
  source (F-03). Until then D-DOM and D-VINTAGE run on 2016-2022 only. Anything not ratified takes its default
  irrevocably.
- **PREREG-D** (data; [–]): checkpoints and weight hashes, the score table, clock tables, `clock_source` per meeting,
  realised n and dropped list, thresholds as numbers, package locks, Databento request parameters and SHA-256 of every
  data file read, tick/cost table, operating characteristics (A-11, R2-28, R3-19, R3-20), PPV, label demotion list,
  D-VAL-C labels, extension registrations, the provenance table. Timestamped after PREREG-R and before any market join.
- **Publication ([U])**: preferred: timestamp the manifest hash only (OpenTimestamps, embargoed OSF or AsPredicted
  private). `git add -f`, tags or pushes to the public remote need the user's approval.
- **Exposure record**: every output listed in section 0 is in the PREREG access log with hashes. Sealed outputs stay
  unopened by everyone who ratifies, writes PREREG or labels; moving or deleting them is the team's decision. Each member
  attests in PREREG-R which sealed files they opened ([A]): the `bt` results, tables and positions, ADDENDUM s12, the
  `bt` lexicon tables and `g3_and_h1primary_extras.json`, the R3-02 chrono outputs and `meta.json` files, and the F-01
  outputs (fedspeak_v2 full-run scores, metrics and logs; placebo-chain results). Labels follow 3.9.
- **Provenance (A-08, R2-03(7), R3-24)**: each numeric choice is marked "pre-2023 literature", "data quality" or "chosen
  after exposure"; the r1 BENCH-R choices are marked as made after exposure to USMPD results on identical windows, and
  R2-19/R2-20 as made in a round in which one reviewer had read ADDENDUM s12.
- **One execution spec (R2-04)**: `bt/ADDENDUM.md` is a superseded record; where it differs (G3 statistic, sidedness,
  residualiser, aggregation, exec30 veto, BENCH-R exit and era, latency sweep, GDELT point clock, lexicon reading) this
  plan governs; `bt` market-join code may be reused only after it is changed to these rules, hashed and re-run under
  PREREG-D.
- **fedspeak_v2 (R2-35, F-01, F-02)**: no v2 validation-window or out-of-sample number and no v2 presser score is opened
  by a ratifier before PREREG-R; v2 keeps its own record and its own checkpoints.
- **Postponement (R2-02)**: while H1-primary is unratified or postponed, no script reads named-event records after 14:20
  ET; a still-postponed G3 is cancelled and logged on 2027-01-31.

### 3.12 Compute: local RTX 5090 and HiPerGator (at most 2 B200 per session) (A-27, A-36, A-44, A-48, A-49, R2-05, R2-36(2), R3-03, R3-17, R3-41, R3-42, F-04, F-08, F-09)

- **Local RTX 5090 32 GB** is the reference platform for every frozen table (alignment, anchors, completeness decodes,
  fine-tunes, scores, H2/H3 features) and the whole live path. Freeze-critical batches follow R2-36(2): media pulled once
  with SHA-256 frozen (Brightcove URLs expire after about 6 h); LLM stack unloaded, autonomous worker paused and no other
  GPU training co-scheduled (F-09: the fedspeak_v2 run used this card on 2026-10-03); atomic per-meeting outputs with
  done-markers carrying device, driver, co-resident GPU processes and a guard-log excerpt; a guard, OOM or power event
  voids only the in-flight unit, which is rerun from hashed inputs. Fail fast on any device fallback (A-49(3)).
  Compute is not the constraint: 36 chrono fine-tunes took about 17 minutes on this card (F-01 file times).
- **HiPerGator** (`hpg-b200`, B200 180 GB, investment QOS `jie.xu`, CPU burst `jie.xu-b`; fallbacks `hpg-rtx6000`, L4)
  serves the research arm only, after the sponsor's written confirmation that the project is UF research with academic
  outputs (UF Policy 12-002, amended 2026-03-24: no use "for personal financial or other gain"; [S]). Nothing that feeds
  a paper or real-money trade runs there; it is never on the freeze critical path. Uses: replication of the fine-tunes
  (into `models/stance_walkforward_hpg_replica`), of the ASR/alignment tables and of H2/H3 features, with agreement
  reports (argmax flips, meeting-score deltas, τ changes, ICCs).
- **The 2-GPU rule (R3-41, F-04)**: every HiPerGator GPU job of the user (batch, `srun`/`salloc`, Open OnDemand) runs
  under the one job name `fp-gpu` with `--dependency=singleton` and at most `--gres=gpu:b200:2`, so at most one GPU job
  and at most 2 GPUs run at any time however many are pending. No GPU job arrays (sharding inside the job,
  `GPU_LAYOUT=job`); CPU arrays (fetch, audio/frames, aggregate) are allowed. The first step of every job writes the
  summed running gres/gpu from `squeue -u $USER -h -r -t R -O JobID,Name,tres-alloc` into its done-marker and exits
  before CUDA initialisation if it exceeds 2. Training is its own `fp-gpu` job ahead of text (`afterok`), with no idle
  wait loop (the idle-GPU killer ends a job after 1 h at 0%). Run `showQos jie.xu` first; default to 1-GPU jobs if the
  group limit is below 2. A CPU-only dummy (`sbatch -J fp-lanetest --dependency=singleton --array=0-3 --wrap 'sleep 90'`)
  records whether singleton serialises array tasks; GPU arrays stay banned regardless.
- **Team runner** (`<team_push>/hpg/submit_nlp.sh`, commit 67f601b): defaults to 4 concurrent GPUs, bf16, the dataset
  label rule and the `ai-workshop` account; before anyone runs it, convert it to the `fp-gpu` pattern (or `CONC=2`, `%2`
  and no other GPU job), and check the `ai-workshop` terms or switch to `jie.xu` ([U]: pushing the fix and telling
  teammates not to run 67f601b are the user's messages). Its outputs are replication only.
- **Permissions (A-48(5))**: `umask 077` and `chmod 700` on the project root (`/blue/jie.xu` is group-readable by
  default); gated weights only in the approved user's private directory; no Databento raw data on HiPerGator (derived
  tables only); claims with 5-minute heartbeats and a 20-minute TTL; GPU jobs offline (`HF_HUB_OFFLINE=1`) after a CPU
  prefetch job.
- **Package edits before any `hpg/` output feeds H1 or touches a registered meeting (A-36 table in v3, status F-08)**:
  anchor rule `file` with per-window bound columns; `latency_s` 0 for frozen tables with `t_end_utc_lo/hi`,
  `known_at_locked = t_end_utc_hi + M` and `known_at_exec30` as separate columns (joins never on `known_at`);
  `max_uncertainty_s` 30 on the half-width; `clock_source` per meeting; aligner = WhisperX CTC with the pinned wav2vec2;
  alignment-quality threshold from PREREG-D; pinned `nltk` splitter; TDW filter and clause split; score per 3.4;
  crosschecks Loughran-McDonald only; `classifier_train_end` 2022-10-15 plus the 2019-02 base flag; ECAPA enrol from
  prior meetings with a fixed threshold; voice valence off; device fallback fails; heartbeat claims; `umask 077`;
  `label_date_rule: source_date`; local model registry; deterministic training flags; per-τ_k bound table in `clock.py`;
  smoke 20200303 with smoke-only models and no score printouts; complete fingerprint; frozen ASR decoding;
  `GPU_LAYOUT=job`, `fp-gpu` names, no `--allow-concurrent`. Code edits are the team's. Unit tests: entry bar = first
  bar with ts_event ≥ known_at_locked; exec30 bar likewise; half-width > 30 s excluded; settlement grid (R3-37(5));
  commit at t_fill (R3-36(4)); 25 h guard (R3-38); GPU audit.

### 3.13 Licences, ethics and legal (A-28, A-30, A-43, A-48, R2-15, R3-07, R3-38)

- Non-commercial components: TDW labels and the TDW repository code (CC BY-NC 4.0), every chrono fine-tune (inherits
  the labels' NC terms), FOMC-RoBERTa (CC BY-NC, gated), audeering (CC BY-NC-SA), EmotiEffLib and InsightFace weights
  (non-commercial in effect). A repository NOTICE lists them; `label_dates.parquet` is committed without the `sentence`
  and `label` columns or with a NOTICE (CC BY-NC 4.0; Shah, Paturi & Chava, ACL 2023; licence link; "re-dated by the
  team"). Pushing is the user's decision ([U]).
- Every downstream use of NC-derived scores carries the per-scorer flag: the fedspeak_v2 sleeve, its core_ER_6 test and
  any hackathon, prize or sponsor demo. Each needs a recorded user decision, written permission from gtfintechlab, or a
  permissive scorer (MIT chrono-bert fine-tuned on the team's own blind labels of federalreserve.gov text, filter and
  clause split reimplemented from the paper text). Whether a sponsor-judged entry or evidence-building paper trading is
  "commercial" under CC BY-NC 4.0 s1(i) is UNVERIFIED. No real-money step without a permissive path (A-30, A-43, A-48).
- Board of Governors media are public domain unless marked; C-SPAN is not (derived timings only, optional). TV-archive
  and GDELT caption pages: derived offsets only, raw pages private and never shared.
- Databento: derived tables only for teammates until licence terms on sharing raw bars are checked; the 24-hour
  historical boundary is enforced in code (R3-38).
- Do not claim to read Warsh's feelings; features are proxies; Warsh voice and face are off.

### 3.14 Gates and calendar (team table, effective conditions)

| Gate | Go (locked) | No-go (locked) | Effective conditions (amendments) |
|---|---|---|---|
| G0 | CPU ASR + RoBERTa on one Powell and 2026-09-16 Warsh | No video/ASR | After PREREG-R. GPU and CPU agreement; "one Powell" = 20200303 with smoke-only models; Warsh 2026-09-16 runs ASR and alignment and prints pipeline health only, its scores sealed until its D-VAL-W labels are hashed; "no model access" recorded separately (A-27, A-28, R3-03(5), R3-09) |
| G1 | get_cost under credit | Shrink window/symbols; ask before 1s | The 2016+ windows are on disk; the user confirms or denies that purchase; extras need printed quotes (R2-03, R2-24, R3-33) |
| G2 | Event list; missingness vs VIX table | Crisis MNAR + imputed video | Missingness = caption, MP4 completeness, alignment and anchor quality; MNAR on outcome-free covariates only; USMPD validation of the event table (A-05, A-07) |
| G3 | H1-primary on confirmation sample | Stop; do not mine H2 | 3.5: PREREG-R then PREREG-D; accuracy gate passed (else postponed); run once; R3-20 critical value; labels attach, never flip; post-NO-GO rules R2-26 |
| G4 | H2/H3 variance/identity gates on Powell | Ship text-only | Unchanged; H2/H3 run only after a G3 GO (R2-26) |
| G5 | Paper-trade text, half-size on Warsh, only if live p90 delay ≤ 60 s | Kill live; measurement-only | 3.10: measured on 2026-10-28 against registered references; terminal on fail; counted trades need a G3 GO and start after 2026-10-28 |

Remaining pressers: 2026-10-28, 2026-12-09; 2027 dates (01-27, 03-17, 04-28, 06-09, 07-28, 09-15, 10-27, 12-08) are
provisional (A-34). Calendar milestones: PREREG-R target 2026-10-06; checkpoint manifest hashed before 2026-10-28 13:59
ET (Tier P eligibility of 2026-10-28); live reference set registered by 2026-10-21; PREREG-D target 2026-10-16, latest
2026-10-21 (A-35); if PREREG-D slips, G3 slips with it and post-2026-09-16 records are fetched into sealed files (R3-05(3))
(F-07).

---

## 4. Amendment index (all dated 2026-10-03)

Status "active" means the amendment governs as consolidated in section 3; "→ X" names what superseded part of it. Full
texts and evidence: `merged_plan_v3.md` sections F.1-F.8 (A-nn, R2-nn, R3-nn) and section 6 here (F-nn).

**Gap review and round 1 (A-nn; v0 written 17:04 EDT, revised in r1 by 17:40 EDT)**

| Id | Type | Effect | Approval | Status |
|---|---|---|---|---|
| A-01 | COR | `ZT.v.0` replaces `ZT.c.0`; instrument_id frozen; record-count check; ZTZ6 / ZTH7 | [–] | active |
| A-02 | IMP | TV-archive wall-clock anchor; τ at an upper bound + M = 30 s; locked 30 s = half-width; FC row; ε reruns; derived tables only | [–] | active; bins and drop → R2-16; formula → R3-13 |
| A-03 | CLAR | H1 exit 15:59 close (ZT, ES); sign convention; HC3 t; sidedness default two-sided | [T] | active |
| H1-run | EXT | intra-presser running-mean legs, flat at the last answer; Tier 2 | [–] | active; windows → R3-14 |
| A-04 | COR | date-dependent ZT tick; $2.00 fee (UNVERIFIED) | [U] broker fee | active |
| A-05 | IMP | VTT QA, forced alignment, per-meeting clock source, MP4 completeness | [–] | active; tests → R2-18, R3-15 |
| A-06 | IMP | event clocks; 2011-2015 pull; 2020 unscheduled excluded; entry 14:20 every era; sub-tick rule | [U] 2011-2015 quote | active; exit → R2-19; statistic → R3-31 |
| A-07 | IMP | USMPD event table; post-PREREG statement-window QA, flags only | [–] | active |
| A-08 | IMP | prior-exposure disclosure; provenance; H1-post; access rule | [A] | active; extended by R2-03, R3-02, F-01 |
| A-09 | IMP | R_stmt control; chair dummy dropped; expanding trading residualiser | [–] | active; start → R3-22; Warsh → R3-40 |
| A-10 | CLAR | TDW-faithful filter, clause split, pooling; label reproduction | [T] | score type → R2-01(2); thresholds → R2-06 |
| A-11 | IMP | realised n; operating characteristics by simulation; NO-GO uninformative | [–] | active; → R2-28, R3-20 |
| A-12 | IMP | PREREG manifest; script order; hash timestamp; publication needs the user | [U] | active; split → R3-04 |
| A-13 | DATA | measured spreads from bbo-1s; quote-fill and measured-cost columns | [U] purchase confirmation | active; → R2-33, R2-34, R3-33 |
| A-14 | EXT | walk-forward chrono spec | [–] | under D1 the Tier 0 scorer spec; decision row → R3-21; dates → R3-01; shared-checkpoint clause withdrawn (F-02) |
| A-15 | DIAG | D-VAL vs human ratings (sign −avr_score; 2011-2019; lower-bound rule) | [–] | active; → R2-07, R2-08 |
| A-16 | IMP/DIAG | frozen live text pipeline; ECAPA from prior meetings; D-ASR | [–] | active |
| A-17 | IMP | live recording, NTP query-only, delay upper bound, decision log, next-day pricing | [U] OpenTimestamps; bbo cap | active; fills → R2-31, R3-37 |
| A-18 | EXT/DATA | 1s uses: STMT-ABS, H1-answer-1s, BENCH-R at 14:20:00 | [U] 1s purchase confirmation | active |
| A-19 | EXT | BENCH-R hurdle table; BENCH-R-ES | [–] | active; hurdle on both exits (F-05) |
| A-20 | EXT | H1-exec30, H1-exec-live; label only, no veto | [–] | active; → R3-39 |
| A-21 | EXT/IMP | H1-answer-mid; bbo as-of semantics | [U] bbo | active |
| A-22 | IMP | H1-answer signal, sample, selection, inference | [–] | active; → R3-14 |
| A-23 | COR (procedure) | restricted wild bootstrap of the HC3 t | [–] | active; → R3-20 |
| A-24 | COR | H1 gross only; stated prior; decay check | [–] | active |
| A-25 | IMP | paper-to-live stopping rule | [–] | → A-43 |
| A-26 | IMP | register replaces "Holm within secondaries"; 2022 split on 2016-2022; H4 design | [–] | active; → R2-14 |
| A-27 | IMP | compute: 5090 reference and live; HiPerGator offline, ≤ 2 GPUs | [S] | active; "arrays %2" withdrawn (F-04) |
| A-28 | IMP | FOMC-RoBERTa access request; pin every revision | [U] request | active |
| A-29 | IMP | cutoff registry; exempt model classes; no enlargement of the confirmation sample | [–] | active |
| A-30 | COR | CentralBankRoBERTa is agent sentiment; NC weights; no real money without a permissive path | [U] | active |
| A-31 | IMP | vocal_proxy spec | [–] | active |
| A-32 | IMP | expression_proxy spec | [–] | active |
| A-33 | IMP | A/V skew | [–] | active |
| A-34 | IMP | event-list maintenance; 2027 provisional | [–] | active |
| A-35 | IMP | calendar from 2026-10-05; 2026-10-28 measurement-only; hashes by 2026-10-21 | [–] | active; schedule F-07 |
| A-36 | IMP | `hpg/` package defaults table | [T] code edits | active; status F-08 |
| A-37 | EXT/DIAG | D-DOM, D-DECOMP, H1-A | [–] | active; → R2-11, R3-23 |
| A-38 | EXT | H1-PX (Tier 2), PP-MKT | [–] | active; R_pc → R2-20 |
| A-39 | EXT | placebos P1, P3; lexicon reading | [–] | item 1 → R3-06 |
| A-40 | IMP | FOMC-RoBERTa access contingency | [–] | option v1 only; under D1 items (b), (f), (g), (h) |
| A-41 | EXT | H1-P prospective replication | [–] | active; → R2-25, R3-05, R3-16 |
| A-42 | IMP | live object, end event, position map | [–] | active; → R2-31, R3-37, R3-39, R3-40 |
| A-43 | IMP | counted paper trades; studentised OBF looks; per-scorer count | [–] | active; → R3-34..R3-36 |
| A-44 | IMP | presser-day runbook for the shared 5090 | [–] | active; → R3-36 |
| A-45 | IMP | enumerated test register | [–] | section 3.8 |
| A-46 | CLAR | interpretation labels | [T] | active; → R3-19 |
| A-47 | DIAG | D-VAL-W | [–] | active; → R2-09, R3-09 |
| A-48 | IMP | HiPerGator governance: sponsor confirmation, critical path local, permissions | [S] [U] | active; guard → R3-41 |
| A-49 | IMP | reproducibility of frozen tables | [–] | active |
| A-50 | EXT | econ robustness rows (outgoing chair, news flags, topic mix, exit noise, post-publication) | [–] | active; → R3-27, R3-29 |

**Round 2 (R2-nn; written 18:00-19:00 EDT on v1)**

| Id | Type | Effect | Approval | Status |
|---|---|---|---|---|
| R2-00 | COR | data on disk and parallel `bt` outputs recorded with hashes | [–] | active; → F-01 |
| R2-01 | CLAR | scorer of record: option D1 (default) or v1; score function; H1-RoBERTa slot; gate | [T] | active |
| R2-02 | IMP | no named-event reads after 14:20 while G3 waits; cancel 2027-01-31 | [–] | active; scope → R3-05 |
| R2-03 | COR/IMP | purchase confirmation; moratorium; seals; attestations; labels; split requests | [U] [A] | active |
| R2-04 | CLAR | one execution spec (ADDENDUM superseded); one code path | [T] | active; clock → R3-13 |
| R2-05 | IMP | all checkpoints trained once on the 5090, deterministic; 45 fine-tunes | [–] | active; v2 clause withdrawn (F-02) |
| R2-06 | IMP | FOMC-RoBERTa identity vs label-map thresholds | [–] | active |
| R2-07 | DIAG | ρ_within and statement-level ρ | [–] | active |
| R2-08 | IMP | 2010-2014 keys; walk-forward D-VAL on 2011-2019 | [–] | active |
| R2-09 | CLAR | D-VAL-W unit, gold label, balanced accuracy, rule | [T] | active; → R3-09 |
| R2-10 | DIAG | presser-domain F1 | [–] | active |
| R2-11 | CLAR | statement construct note; S_repeat / S_new | [T] | active; → R3-23 |
| R2-12 | CLAR | H1-Q question score | [T] | active |
| R2-13 | CLAR/DIAG | scorer vintage; H1-1base; D-VINTAGE; single-base option | [T] | active; (iii) → R3-10; (iv) → R3-19 |
| R2-14 | CLAR | H4 training features walk-forward | [T] | active |
| R2-15 | IMP | tokenizer note; TDW code NC; caches private | [–] | active; → R3-18 |
| R2-16 | IMP | trailing anchor windows; drop on half-width only | [–] | active; formula → R3-13; answers → R3-14 |
| R2-17 | IMP | ε by station; caption capture | [U] tuner | (1)-(2) → R3-13; (3)-(4) active |
| R2-18 | IMP | aligner-independent completeness; aligner seeded from ASR | [–] | active; → R3-15 |
| R2-19 | CLAR | BENCH-R exit = presser-end from metadata; Tier 1 renamed; BENCH-R-P | [T] | active; → R3-31, R3-32 |
| R2-20 | IMP | one R_stmt (closes 14:19 − 13:49); R_pc; BENCH-R-d10 | [–] | active |
| R2-21 | CLAR | pooled specification across the 2020 break | [T] | active |
| R2-22 | IMP | legacy CME feed era | [–] | active |
| R2-23 | IMP | degraded vendor days | [–] | active |
| R2-24 | DATA | extras outside the cached window | [U] | active |
| R2-25 | CLAR | H1-P statistic, sidedness, wording | [T] | active |
| R2-26 | CLAR | execution after a NO-GO | [T] | active |
| R2-27 | IMP | PPV and GO wording | [–] | active |
| R2-28 | IMP | fixed-design operating characteristics | [–] | active; → R3-20 |
| R2-29 | IMP | covariance / drift split for mean statistics | [–] | active; criterion → R3-19 |
| R2-30 | EXT | SEP composition, D-STMT-PATH, cycle phase, H1-ZF/ZN/ES, morning supply news | [–] | active |
| R2-31 | IMP | G5 statistic, D_frozen, fill floor, Warsh settlement | [–] | (4) withdrawn → R3-35; (2), (5) → R3-37 |
| R2-32 | IMP | live references by 2026-10-21; segment clock | [U] references | active; H1-P clock → R3-16 |
| R2-33 | IMP | one paper cost model | [–] | statistic → R3-34 |
| R2-34 | IMP | quote fill at the locked entry instant | [–] | active |
| R2-35 | IMP | sequencing with fedspeak_v2 | [A] | active; → F-01 |
| R2-36 | IMP | GPU lanes; local batch runbook | [–] | (1) → R3-41; (2) active |

**Round 3 (R3-nn; written from 18:40 EDT on v2)**

| Id | Type | Effect | Approval | Status |
|---|---|---|---|---|
| R3-01 | COR | labels dated by source date (team Update D1a); reprinted counts; training-row audit | [T] threshold confirmation | active; table hash → F-11 |
| R3-02 | COR | non-spec chrono outputs inventoried, sealed, quarantined; reworded precondition | [A] | active; → F-01, F-03 |
| R3-03 | CLAR/IMP | one code base; smoke 20200303; complete fingerprint; `bt` guard | [T] [U] pushes | active; default F-06 |
| R3-04 | IMP | PREREG-R before scores, PREREG-D before outcomes | [T] | active; wording F-03 |
| R3-05 | IMP | scope of read bans; Tier P eligibility | [–] | active |
| R3-06 | COR/CLAR | lexicon not estimable as frozen; LEX-RAW; locked reading | [T] | active |
| R3-07 | IMP | NC licence handling; downstream flags | [U] | active |
| R3-08 | DIAG | D-VAL-C on the Tier 0 bases | [–] annotators | active |
| R3-09 | CLAR | D-VAL-W blind to model outputs; verdicts act forward only | [T] | active |
| R3-10 | CLAR | per-document-type centring, floored scaling | [T] | active |
| R3-11 | IMP | H1-RoBERTa needs the weight history | [–] | active |
| R3-12 | DIAG/IMP | cutoff probe; `reference_compile=False` | [–] | active |
| R3-13 | IMP | one τ_used formula | [–] | active |
| R3-14 | IMP | answer windows across 15:00 ET | [–] | active |
| R3-15 | IMP | completeness on the MP4 clock; last chair answer | [–] | active |
| R3-16 | CLAR | H1-P clock | [T] | active |
| R3-17 | IMP | frozen decoding options and batch sizes | [–] | active |
| R3-18 | IMP | raw pages sealed until PREREG-D; IA check for uncaptioned dates | [–] | active |
| R3-19 | CLAR | labels by estimate difference; LR demotion | [T] | active |
| R3-20 | COR (procedure) | size-controlled critical values | [T] rule | active |
| R3-21 | CLAR | H1-clean in Tier 2; H1-pooled Tier 3 | [T] | active |
| R3-22 | EXT/IMP | ZLB rows; residualiser from 2022-03-16 | [–] | active |
| R3-23 | CLAR | covariance-share rules | [T] | active |
| R3-24 | COR | provenance of round-2 BENCH-R choices | [A] | active |
| R3-25 | EXT/DIAG | D-OPEN, H1-O, H1-A-O | [–] | active |
| R3-26 | EXT | H1-SEP (Δdot) | [–] | active |
| R3-27 | EXT | outgoing chair from 2025-06-25; political share | [–] | active |
| R3-28 | EXT | H1-RUNUP | [U] previous-day data | active |
| R3-29 | CLAR | concurrent news: pre-treatment flags only | [T] | active |
| R3-30 | EXT | H1-L | [–] | active |
| R3-31 | CLAR | BENCH-R decisive statistic gross in bp | [T] | active |
| R3-32 | CLAR | BENCH-R-P uses the historical exit rule | [T] | active |
| R3-33 | IMP/DATA | spreads are upper bounds; ZF bbo-1s $0.96 | [U] | active |
| R3-34 | COR | A-43 statistic gross | [–] | active |
| R3-35 | COR | G5 terminal, one measurement presser | [–] | active |
| R3-36 | IMP | counted decision committed at t_fill | [–] | active |
| R3-37 | IMP | one fill instant; settlement test on t_fill | [–] | active |
| R3-38 | IMP | next-day pulls ≥ 25 h; condition check | [–] | active |
| R3-39 | EXT | H1-exec-live by end-detector replay | [–] | active |
| R3-40 | IMP/CLAR | Warsh a, σ and empty-statement rule | [T] | active |
| R3-41 | IMP | `fp-gpu` singleton, ≤ 2 GPUs, no GPU arrays, audit | [U] `ai-workshop`; team-runner push | active; → F-04 |
| R3-42 | IMP | H2/H3 reference platform | [–] | active |

**Final pass (F-nn; written from 18:55 EDT on v3)**: listed in section 6.

---

## 5. Decisions that need people (with the default that applies if nobody decides)

**Team, in PREREG-R ([T]; target 2026-10-06; before any stance score of a registered meeting is computed by the code
base of record or viewed by a ratifier)**

| # | Decision | Default if not ratified |
|---|---|---|
| T1 | Scorer of record: option D1 (walk-forward chrono-bert, team deviation D1/D1a) or option v1 (withdraw D1; FOMC-RoBERTa with the A-40 postponement rule) | D1 |
| T2 | Score function: R2-01(2) (filtered, clause-split, argmax share, pooled over the meeting) or team_push's unfiltered equal-weight answer mean; the R2-11 construct note | R2-01(2) |
| T3 | Base rule for 2023-2026: D1's per-year bases or the single `b2022_l2022` base | per-year bases (D1 as written) |
| T4 | A-03: exit at the 15:59 close for ZT and ES, sign convention, HC3 t, and sidedness | two-sided |
| T5 | R2-19 BENCH-R exit and R3-31 decisive statistic (or one named costed version in bp) | presser-end by metadata; gross bp |
| T6 | Code base of record (R3-03): `hpg/fedpress` or `<team_push>/nlp` | `hpg/fedpress` (F-06) |
| T7 | R3-01(3): the 0.55 accuracy threshold stands for a true forward test | 0.55, recorded as "not confirmed" |
| T8 | R3-06 lexicon reading | the locked "Negative control" |
| T9 | Block: A-46/R3-19 labels, R3-20, R3-21, R2-21, R2-25, R2-26, R3-10, R3-16, R2-09/R3-09, R2-12, R2-14, R3-23, R3-29, R3-32, R3-40 | as written |

**Each team member ([A], in PREREG-R)**: which sealed files they opened (section 3.11 list, including the F-01 outputs),
and for annotators that they saw no market data and no model output for the units they label.

**The user ([U])**

| # | Decision |
|---|---|
| U1 | Confirm or deny the ohlcv-1s and bbo-1s purchase found in `cache/` (schemas, dollar amount, date). Until confirmed, those files are not read |
| U2 | Approve or decline printed quotes: 2011-2015 ohlcv-1m (about $0.04), R2-24 extras (pre-13:30, previous day, next-day 15:00), `ZF.v.0` bbo-1s ($0.96), optional MBP-1 ZT+ES ($29.39); a standing presser-day bbo-1s cap (≤ $1 per day, 2026-10..12) or a fresh quote each day |
| U3 | Where the PREREG hashes are timestamped (OpenTimestamps digests only, embargoed OSF, AsPredicted private); whether anything is committed with `git add -f`, tagged or pushed |
| U4 | Send the sponsor request for written confirmation that this is UF research with academic outputs (A-48(4)); decide on the `ai-workshop` allocation; push the team-runner and NOTICE fixes and tell teammates not to run commit 67f601b (R3-07, R3-41) |
| U5 | Request FOMC-RoBERTa access on Hugging Face (manual approval by the authors); accepting the conditions is the user's decision |
| U6 | The 2026-10-28 live reference set by 2026-10-21: a UF library Bloomberg session; a tuner or IPTV caption feed if one exists |
| U7 | The fedspeak_v2 full run and the placebo chain (F-01): ask their operators to seal the outputs (no one who ratifies opens them) and to run nothing further on the named events before PREREG-R; sealing and declaration apply either way |
| U8 | The broker's all-in fee schedule (replaces the UNVERIFIED $2.00) |

**External ([S])**: the sponsor's written confirmation before any HiPerGator job; gtfintechlab's approval of
FOMC-RoBERTa access; optional written commercial permission for NC-derived scores.

---

## 6. Consistency check of this merge and final-pass amendments (F-01..F-11, dated 2026-10-03, label `final`)

The final pass re-read `team_FINAL_PLAN.md`, `merged_plan_v3.md` in full, `GAP_REPORT.md`, `DEVIATION_D1_stance_model.md`,
the `hpg/` README and key scripts, and listed (names, sizes and times only) every file written after v3 was saved
(18:49 EDT). No sealed output was opened; the only file read among the new outputs was the 55-byte
`<scratch>/placebo_chain/PLACEBO_README.txt`. Contradictions found and how this document resolves them:

**F-01 New outputs since v3 (correction to the R2-00 / R3-02 inventory; implementation detail; [A], [U]).** Two runs
wrote files after 18:49 EDT (section 0, items 3 and 4):
(a) `<scratch>/chrono/full/`, launched 18:36 EDT by a process of the fedspeak_v2 environment: `data/labels.parquet`,
`label_check.json`, `label_year_audit.json` and `base_models.json` (18:36); 36 fine-tunes `models/<year>/seed_<s>` for
years 2015-2026 and seeds 42-44 (18:37-18:53), a per-calendar-year layout that matches `<team_push>/nlp`; `scores/`
for 2015-2026 (18:53-18:56) with `presser_answers_chrono.parquet` and `presser_meetings_chrono.parquet` (18:56). Under
`v2/HYPOTHESIS_v2.md` Amendment 2 (l.68) every document and press-conference answer dated in year Y is scored by model
Y, so 2023-2026 presser answers have been scored.
(b) `<scratch>/placebo_chain/` (18:52-19:07) with `<scratch>/wire/` logs: stance inputs are random by its README, but
it also wrote `presser_out/results/benchr_trades.csv`, `benchr_break_stats.csv`, `benchr_cost_hurdle.csv`,
`benchr_usmpd_ust2y.csv`, `spreads_by_presser_phase.csv`, `summary_long.csv`, `h1primary_*_2016_2022_robustness.json`,
`presser_out/tables/benchr_per_meeting_{ES,ZF,ZN,ZT}.csv`, `lexicon_h1primary_per_meeting_{ES,ZF,ZN,ZT}.csv`,
positions and QA files, `results_final/summary.{json,md}`, an `oos_codepath_test/` tree and `v2_out/` in-sample files
from the real cache;
its `chrono/scores/` holds files named as per-year document scores 2015-2026 and presser answer and meeting scores
(random stance values according to its README; not verified, because the files were not opened).
Rules: both trees enter the PREREG access log with SHA-256; they are sealed under R2-03(3); their checkpoints get
quarantine ids; nobody who ratifies, writes PREREG or labels opens them; each member attests (3.11). The v2 presser
scores fall under R2-35 and R3-04 ("scored first by fedspeak_v2: sealed and declared"). Reading 2020-2026 records after
14:20 ET in the placebo chain happened after the R2-03(2) moratorium was written (v2, 18:15 EDT); file names indicate
BENCH-R over the cached history, so the record notes a further non-blind BENCH-R computation; BENCH-R's label
("non-blind reproduction") does not change. What the v2 operator does next is the user's decision (U7); this plan does not stop
other processes.

**F-02 The "one checkpoint set serves both projects" clause is withdrawn (correction to A-14 and R2-05).** A-14 and
R2-05 assumed the H1 fine-tunes would also serve fedspeak_v2, trained once on the 5090 under R2-05. v2 has now trained
its own per-calendar-year set (separate 2025 and 2026 fits; label rule and training flags not verified here). H1's
checkpoints of record are only those trained under R2-05, R3-01 and R3-03(1),(3) and hashed in PREREG-D; v2's set is
quarantined for every H1 input; R2-05's v2 sentence becomes a recommendation for v2's own record. Side fact: 36
fine-tunes took about 17 minutes on the 5090, so the 45 deterministic H1 fine-tunes are an hour-scale local job.

**F-03 PREREG-R precondition reworded (clarifying; [T]).** R3-04(1) says PREREG-R precedes scoring of 2023-2026 presser
text "by any scorer", which is already untrue for the lexicon (R2-00) and is becoming untrue for fedspeak_v2 (F-01);
A-12 says the H1-primary script is the first to read 2023-2026 records after 14:20 ET, untrue since 17:48 EDT. Read
both as: PREREG-R is timestamped before any stance score of a registered-sample meeting is computed by the code base of
record and before any ratifier views such a score from any source (consistent with R3-02(2)); G3 is the first PREREG-D
script of the code base of record to read those records. The sealed exceptions are listed in section 0. Default if not
ratified: this reading.

**F-04 GPU arrays (correction of residual text).** A-27 still said "job arrays throttled %2" and A-48(1) described a
pre-submit guard, while R3-41 bans GPU arrays and enforces the rule with one `fp-gpu` singleton job; `hpg/README.md`
and `slurm/common.sh` (default `GPU_LAYOUT=array`, `--allow-concurrent`) also describe the old pattern. R3-41 governs:
no GPU arrays, at most one `fp-gpu` job holding ≤ 2 GPUs; CPU arrays stay allowed.

**F-05 BENCH-R hurdle window (correction).** A-19 says its hurdle table uses "the USMPD start + 60 window, which is now
also the A-06 exit"; since R2-19 the exit is presser-end from metadata. The hurdle table is computed on both exits and
the decisive statistic is R3-31's.

**F-06 Default code base (clarifying; [T]).** R3-03 asks the team to name one code base but gives no default, while R3-04
makes every unratified item take its default; without one, no H1 input could be produced. Default: `hpg/fedpress`,
which R2-04 already designates as the producer of every H1 text and clock input; `<team_push>/nlp` is then superseded
and its unfiltered answer mean is the Tier 3 row "D1 literal, answer-weighted".

**F-07 Schedule (implementation detail).** v3's checklist put the outcome-free freeze work on 2026-10-07..09 while A-35
freezes hashes by 2026-10-21 and D-VAL-W / D-VAL-C need blind human labels. Milestones (3.14): PREREG-R target
2026-10-06; checkpoint manifest hashed before 2026-10-28 13:59 ET; live references by 2026-10-21; PREREG-D target
2026-10-16, latest 2026-10-21; G3 only after PREREG-D; no partial freeze. Appendix D replaces section E of v3.

**F-08 `hpg/` package status (implementation detail; code edits are the team's).** The package was still being edited
during this pass (trainer, labels, doctor, docs and a label-date builder 18:53-19:06 EDT). As of 19:07 EDT: the
source-date rule is implemented and enabled (`train.stance_walkforward.data.redate`, table `manifest/label_dates.parquet`
with its SHA-256 in `config.yaml`) and training and scoring default to float32, so R3-01's code requirement is met in
`hpg/fedpress`; still open are `SMOKE_ID=20250917` in `slurm/smoke.sbatch` (a confirmation meeting and a degraded vendor
day), production-key training inside the smoke job with `h1_gap` printed, `GPU_LAYOUT=array` with `%2` and
`--allow-concurrent` (`slurm/common.sh`, `submit_all.sh`), `clock_source: asr`, `anchor.rule: greeting_at_scheduled`,
`latency_s: 30` (`known_at`), the `/blue` model registry and the R2-05 deterministic flags (no
`use_deterministic_algorithms` or `attn_implementation` setting found); `fetch.captions_vtt` is already `true`. The
README (sections 5-6) still describes the old defaults. No `hpg/` run produces an H1 input or touches a registered
meeting until the 3.12 edits and the R3-03(2) refusal are in the code; until then the README's smoke and full-run steps
are not followed as written. Every edit is re-hashed into PREREG-R (code tree hash).

**F-09 Shared GPU during freeze batches (implementation detail).** The 5090 is the only local GPU and was running the
fedspeak_v2 training while this pass ran. Freeze-critical batches run only with no other GPU training or LLM model
resident; each done-marker records `nvidia-smi --query-compute-apps` output; a co-resident process found afterwards
voids that unit, which is rerun from hashed inputs (extends R2-36(2) and A-49(3)).

**F-10 Two-week checklist (implementation detail).** Appendix D replaces section E; it uses the local 5090 for every
frozen table and the live path, and HiPerGator (one `fp-gpu` job, ≤ 2 B200) for replication only after [S].

**F-11 Label-date table version (correction to R3-01's hash).** R3-01 pinned `label_dates.parquet` by SHA-256
48f1215f…, the version round 3 checked. The team's table was rewritten at 18:31 EDT and now hashes 16a54100…, identical
to the copy that `hpg/manifest/` builds and pins (18:53). Rule: PREREG-R pins one version by SHA-256 (default: the
current 16a54100… version, which both code bases read); 48f1215f… is recorded as superseded; the R3-01(3) counts and the
R3-01(4) training-row audit are recomputed on the pinned version before any gate number exists; no model trained on an
unpinned version feeds an H1 input.

**Other residual contradictions resolved in section 3 without a new amendment** (the governing amendment is named):
A-42(4)'s 15:01 Warsh rule (deleted; R2-31(5), R3-37); A-46's lexicon label (R3-06); A-11's one-sided reference values
beside a two-sided default (both printed; R2-25(4)); A-43 "t with k − 1 df" vs H1-P "k − 3 df" (different statistics: a
mean vs a three-parameter regression; 3.8); A-27 "voice/face features on HiPerGator" vs R3-42 (HiPerGator replicates;
the 5090 is the reference); A-09 "FOMC-RoBERTa 2023+ / D1 from 2020" vs R3-22 (from 2022-03-16 for any scorer, and from
the first uncontaminated meeting under option v1); A-10's FOMC-RoBERTa P(h) − P(d) vs D1's argmax share (R2-01(2)
default; P(h) − P(d) is Tier 3); A-02(3),(5) and R2-17(1) (replaced by R2-16 and R3-13); R2-31(4)'s retry (withdrawn;
R3-35); R2-33's net statistic (R3-34). Checked and consistent: Tier 2 holds exactly nine tests; Tier 1 three; the
locked Spec and Role text, the {2, 4}-tick stress, "No net Sharpe on H1", "No LLM in the primary path" and "No 1s bars
without a new user-approved quote" are unchanged.

---

## Appendix A. Gap report (team plan vs our research; verdicts as finally effective)

Severity as in `GAP_REPORT.md`: critical = the locked primary is undefined, look-ahead-prone or on the wrong instrument
as written; high = a decision-relevant number would be wrong or non-blind; medium = robustness, validity or execution;
low = narrow. Evidence paths are in `GAP_REPORT.md` and the cited amendments.

**A.1 Candidate gaps G1-G8**

| Candidate | Verdict | Evidence | Amendment |
|---|---|---|---|
| G1 Official WebVTT captions as a better clock than CPU Whisper | Confirmed for in-video time and speaker labels, corrected: captions are video-relative, not wall-clock; 83 files cover 68 of 75 2016+ pressers and 21 of 27 confirmation meetings; 4-7 files need QA; the MP4 is truncated before the last answer at some meetings, so τ comes from a forced aligner or mapped VTT on a per-meeting rule | `<scratch>/fedtalk/data_markets/vtt_summary.csv`; `plan/evidence/it1_data_eng/vtt_quality.csv`; `plan/checks_r1_data_eng/vtt_tail_all_output.txt` | A-05, R2-18, R3-15 |
| G2 USMPD as a benchmark for BENCH-R and the statement residual | Confirmed as event table, data-QA benchmark (statement windows only, flags only) and second instrument for BENCH-R; its statement-sign correlations were already seen, so BENCH-R is non-blind | https://www.frbsf.org/wp-content/uploads/USMPD.xlsx; `plan/checks_it1_econ/usmpd_eras.py` | A-07, A-08, R2-19(4) |
| G3 Gorodnichenko answer times as an alignment check | Rejected as a wall-clock check (YouTube marks plus the scheduled start); kept to cross-check 2016-2019 segmentation and flag broken captions (2019-05-01 at −173 s); its human ratings became D-VAL | `plan/evidence/it1_data_eng/gpt_vs_vtt.csv`; `<scratch>/fedtalk/verify_literature/fomc_all.xlsx` | A-02(10), A-15 |
| G4 Chronological encoders for an uncontaminated 2016-2022 sample | Confirmed (`manelalab/chrono-bert-v1-*`, MIT, ungated); the team then adopted it as its scorer (D1). Gain 27 → 70 scheduled meetings, not "triple" of 22; the dataset `year` field is shuffled, so labels must be dated by source document (D1a, R3-01); the disjoint 2016-2022 sample is Tier 2 H1-clean | `plan/checks_gap_models/gap_models_hf.out`, `gap_models_ds3.out`; `plan/checks_r3_validity/r3_label_dates.out` | A-14, R2-01, R3-01, R3-21 |
| G5 Measure spreads with bbo-1s | Confirmed (about $3.6-3.9 for the fronts on 75 days); data now on disk, purchase awaiting the user's confirmation; spreads are outright-book upper bounds | `plan/evidence/gap_data/cost_2016plus.csv`; `plan/checks_r3_execution/r3_free_checks_output.txt` | A-13, R2-03, R3-33 |
| G6 1s bars for 5-30 s delay identification | Partial: cheap (about $5.5 for four fronts, $8.6 with 6E and SR3), but the historical clock (median anchor interval about 37 s), not bar size, is the binding limit; 1s only for clock-exact objects and NTP-logged live meetings | `plan/evidence/gap_data/tv_anchor.csv`; `<scratch>/fedtalk/data_markets/notes.md` | A-18 |
| G7 Compute assumptions outdated | Confirmed: local RTX 5090 is the reference and live platform; HiPerGator B200 replicates, ≤ 2 GPUs per session enforced by one singleton job name | `hpg/docs/HIPERGATOR_NOTES.md`; https://docs.rc.ufl.edu/resources/gpus/ | A-27, R2-05, R3-41 |
| G8 H1-primary horizon ambiguous | Confirmed and critical: the meeting-level mean is known only at the last answer, so "τ → presser end" is empty and ZT's 15:00 settlement precedes τ in 98% of meetings; exit = 15:59 close, exact residualisation, statistic and sidedness fixed | `plan/checks_gap_exec/presser_tail_output.txt`; `plan/checks/gap_stats_checks.out` s4 | A-03, A-09, A-23 |

**A.2 The 36 gap-review amendments (A-01..A-36)**

| Id | Gap | Severity | Verdict |
|---|---|---|---|
| A-01 | `ZT.c.0` is the delivery-month contract on 42 of 73 scheduled presser days (13 of 13 SEP days 2023-2026), 0-50 traded seconds vs 497-4,058 for `ZT.v.0` | critical | confirmed |
| A-02 | No wall-clock anchor; the "audible open" is a video time; the convention dates speech a median +24 s early | critical | partial (anchor protocol; 30 s rule kept as half-width) |
| A-03 | H1-primary has an entry but no exit, sign, statistic or alpha | critical | confirmed |
| A-04 | ZT tick $7.8125 from 2019-01-14 (team: $15.625); fees absent | high | confirmed |
| A-05 | Official WebVTT absent from the plan; G2 measured video availability, which is complete | high | confirmed / partial |
| A-06 | Hard-coded clocks break on 10 events; 2011-2015 data missing for the locked 2011-19 regime | high | confirmed / partial |
| A-07 | USMPD not used | high | confirmed / partial |
| A-08 | Prior exposure (USMPD correlations, presser-window moves) undisclosed | high | confirmed |
| A-09 | Residualisation unspecified; chair dummy constant in the confirmation sample | high | partial |
| A-10 | Score function not frozen; TDW filter passes 14-32% of chair Q&A sentences | high | confirmed |
| A-11 | Confirmation sample is 27 (realised about 20), not about 22; no operating characteristics | high | confirmed |
| A-12 | LOCKED family has no commit or timestamp; freeze after the download | high | confirmed |
| A-13 | Costs assumed; Fleming-Piazzesi concerns cash Treasuries, not futures | high | confirmed |
| A-14 | Chronological encoders give an uncontaminated 2016-2022 sample | high | confirmed |
| A-15 | No measurement-validity check although human ratings exist | high | confirmed |
| A-16 | Live train/serve skew (PDF vs unlabelled ASR text) | high | confirmed |
| A-17 | No YouTube live stream exists; no ground-truth clock, fill source or tamper-evident log | high | confirmed |
| A-18 | 1s cheap, but clock-limited | medium | partial |
| A-19 | Costed ZT BENCH-R is decided by cost/volatility (break-even abs(corr) 0.65/1.25 pre-2020 at 2/4 ticks) | high | partial |
| A-20 | 1m fill ignores the frozen live delay | medium | partial |
| A-21 | ZT 1m trade prices dominated by bounce pre-2019; missing minutes | medium | confirmed |
| A-22 | H1-answer "non-overlapping" has no selection rule | medium | confirmed |
| A-23 | "Block bootstrap + wild cluster" ill-defined with one observation per meeting | medium | confirmed (and corrected again in r1) |
| A-24 | Our studies: few-bp event edges died after costs | medium | confirmed |
| A-25 | No paper-to-live stopping rule | medium | confirmed (now A-43) |
| A-26 | No multiplicity rule; 2022 split impossible in 2023-2026; H4 design open | low | partial |
| A-27 | Compute outdated | medium | confirmed |
| A-28 | FOMC-RoBERTa gated; pinning after the H1 run | medium | confirmed |
| A-29 | No cutoff registry | medium | partial |
| A-30 | CentralBankRoBERTa is not a stance model; NC weights | medium | confirmed |
| A-31 | vocal_proxy under-specified; valence lexical | medium | confirmed |
| A-32 | expression_proxy identity model unnamed | low | confirmed |
| A-33 | Video lags audio about 3 s | low | confirmed |
| A-34 | 2027 calendar treated as fixed | medium | confirmed |
| A-35 | Calendar assumed the Fed work was the hackathon entry | low | confirmed |
| A-36 | `hpg/` defaults implement the pre-amendment plan; `greeting_at_scheduled` worsens look-ahead | high | confirmed |

**A.3 Gaps the team plan missed that surfaced only in the review rounds** (most important; details in Appendix B):
MP4 truncation before the last answer (r1); the locked signal is mostly the statement term (corr(s, −S) = 0.98 on the
lexicon proxy; r1); the v0 bootstrap over-rejected (size 0.126; r1); UF acceptable-use policy for HiPerGator (r1); data
bought and outcome windows read by a parallel pipeline before any freeze (r2); two scorer records (D1 vs FOMC-RoBERTa;
r2); the TDW filter drops rate-decision sentences from hawk(statement) (r2); the dataset `year` field is shuffled, so
walk-forward training leaked (r3, critical); the locked lexicon control is not estimable as frozen (r3); the 2-GPU rule
was not enforced by the package or the team runner (r3); next-day Databento pulls must wait 25 h (r3); a fedspeak_v2
full run is scoring presser answers before PREREG-R (final, F-01).

---

## Appendix B. Changes made by the three review rounds

Each round ran five lenses (statistics, execution, data engineering, validity, economics), merged duplicates, checked
evidence and patched every hole with a dated amendment; no round edited the locked Spec or Role text.

**Round 1 (`r1_patch`, v1 at 17:40 EDT): 76 reports → 51 holes (2 critical, 20 high, 22 medium, 7 low), all patched.**

| Severity | Hole | Change |
|---|---|---|
| critical | Fed MP4 ends before the last chair answer; a VTT-overrun rule could date τ 35-70 s early | A-05 per-meeting clock source, completeness and tail checks; A-02 anchors on τ's own clock |
| critical | "Q&A minus statement" is mostly the statement term | A-37 D-DOM, D-DECOMP, H1-A, label; A-10 filter on both terms |
| high | v0 decision p over-rejects (0.126) | A-23 restricted wild bootstrap of the HC3 t |
| high | USMPD QA needed outcome prices, edited clocks from market data, was mis-signed | A-07 re-sequenced: statement windows, flags only, hashed addendum |
| high | Only 20 of 27 confirmation meetings anchored | A-11 realised n; "NO-GO at n ≈ 20 uninformative"; A-14 n = 70 |
| high | TV anchor covered only the first 30 presser minutes | A-02 15:00 ET items, windows |
| high | No contingency for missing FOMC-RoBERTa access | A-40 postpone, never replace (later option v1 only) |
| high | D-VAL scale inverted; deciding sample unnamed | A-15 revised |
| high | Score inclusion rule made the two terms incomparable | A-10 TDW-faithful pipeline; label reproduction |
| high | No in-presser price control | A-38 H1-PX, PP-MKT |
| high | One-sided continuation against the plan's own regime evidence | A-03 two-sided default |
| high | No blind confirmation | A-08 provenance, H1-post; A-41 H1-P |
| high | Trading residualiser crossed the 2020 break on contaminated scores | A-09 revised |
| high | BENCH-R exit depended on video; 2011-2012 SEP inside the hold | A-06 entry 14:20 every era (exit later R2-19) |
| high | Live position, end detection, delay object and counting undefined | A-17, A-42, A-43; 2026-10-28 measurement-only |
| high | No Warsh-era validity evidence | A-47 D-VAL-W |
| high | HiPerGator vs UF Policy 12-002 | A-48(4) sponsor confirmation, research arm only |
| medium/low (29) | `known_at` +30 s trap, ε, exec30 veto, bbo timestamps, shared 5090, reproducibility, ECAPA, GPU cap per user, H1-run last leg, register, lexicon/placebos, H1-chrono spec, aggregation, A-29 scope, aligner from an LLM family, Warsh timing, per-scorer real-money count, BENCH-R statistic and sub-tick, outgoing chair, news, topic mix, net tables, H1-answer spec, log details, roll test, `/blue` permissions, exit noise, post-publication | A-36 rows, A-02(4),(7), A-20, A-21, A-44, A-49, A-16, A-48, H1-run, section G, A-39, A-14, A-10, A-29, A-05, A-42, A-43, A-06, A-50, A-24, A-22, A-17, A-01 |

**Round 2 (`r2_patch`, v2 at 18:15 EDT): 63 reports → 48 holes (3 critical, 12 high, 24 medium, 9 low), all patched.**

| Severity | Hole | Change |
|---|---|---|
| critical | Two scorer records: team deviation D1 vs v1's FOMC-RoBERTa rules (two-scorer false GO 0.079-0.097) | R2-01 option D1 default, score function, H1-RoBERTa slot, gate; m kept at 9 |
| critical | A second execution spec (`bt/ADDENDUM.md`) and code path | R2-04 supersession table; one code path |
| critical | Paid 1m/1s/bbo-1s on disk; parallel BENCH-R and lexicon H1 results written before any freeze | R2-00 inventory; R2-03 purchase confirmation, moratorium, seals, attestations, labels |
| high | A postponed G3 would turn non-blind | R2-02 read ban; cancellation 2027-01-31 |
| high | D-VAL-W prevalence-dependent; sample did not exist | R2-09 |
| high | BENCH-R exit changed by an "implementation detail" | R2-19 presser-end from metadata; Tier 1 renamed; BENCH-R-P |
| high | Live delay had no single meaning | R2-31 |
| high | ADDENDUM τ not an upper bound | R2-04 clock fork |
| high | r1 anchor rules cut n from 20 to 16 by non-locked criteria | R2-16 locked half-width only |
| high | ε station-specific and uncalibrated | R2-17 |
| high | Clock-source tests could not fail | R2-18 |
| high | Checkpoints feeding paper trades trained on HiPerGator without determinism | R2-05 local 5090, deterministic, 45 fine-tunes |
| high | TDW filter removes decision, guidance and balance-sheet sentences from S | R2-11 construct note |
| high | Official weights may never pass the reproduction gate | R2-06 |
| high | D1's base switches inside the confirmation sample | R2-13 H1-1base, D-VINTAGE |
| medium/low (33) | ρ_within, 2011-2015 keys, H1-P statistic, pooled break, BENCH-R non-blind Tier 1, Warsh settlement, legacy feed, quote timing, live references, R_stmt, double-counted costs, squeeze guard, degraded days, extras, batch runbook, statement domain, presser-domain F1, H1-Q, v2 sequencing, H4 training, SEP composition, NO-GO execution, PPV, D-STMT-PATH, fixed-design OCs, drift split, caches, tokenizer, TDW code licence, cycle phase, ZF/ZN/ES rows, morning supply news | R2-07, R2-08, R2-10, R2-12, R2-14, R2-15, R2-20..R2-30, R2-32..R2-36 |

**Round 3 (`r3_patch`, v3 at 18:49 EDT): 52 reports → 42 holes (1 critical, 11 high, 18 medium, 12 low), all patched.**

| Severity | Hole | Change |
|---|---|---|
| critical | Training keyed on the shuffled dataset `year`; team Update D1a not adopted | R3-01 source-date rule, audit, threshold confirmed before any gate number |
| high | R2-31(4) turned the terminal G5 into a retry loop | R3-35 locked kill restored |
| high | Labels fired on "one significant, the other not" | R3-19 estimate-difference rule, LR demotion |
| high | Sidedness and base could be ratified after 2023-2026 scores | R3-04 PREREG-R / PREREG-D |
| high | Failures declared after the fill could void counted trades | R3-36 commit at t_fill |
| high | Next-day pulls could fall inside the licensed intraday window | R3-38 25 h rule in code |
| high | 2-GPU rule not enforced (lanes allow 3-4; team runner 4 GPUs, bf16, `ai-workshop`) | R3-41 one `fp-gpu` singleton job, no GPU arrays, audit |
| high | Non-spec chrono scores and checkpoints on presser text | R3-02 seal and quarantine; R3-03 smoke and fingerprint |
| high | Three τ_used definitions | R3-13 one formula |
| high | A third D1 implementation wired into `bt` | R3-03 one code base; `bt` guard |
| high | Tier 0 checkpoints never validated | R3-08 D-VAL-C |
| high | Lexicon control not estimable as frozen | R3-06 |
| medium/low (30) | answer windows at 15:00, H1-clean vs H1-pooled, size control, net statistic, D-VAL-W blindness, read-ban scope, fill instant, BENCH-R statistic, end-detector replay, Warsh a/σ, completeness on the MP4 clock, H1-P clock, licences, covariance shares, opening remarks, ZLB, SEP/dots, outgoing chair, centring, provenance, spreads, BENCH-R-P exit, decoding, raw pages, H2/H3 platform, weight history, cutoff probe, run-up, news flags, window length | R3-05, R3-07, R3-09..R3-12, R3-14..R3-18, R3-20..R3-34, R3-37, R3-39, R3-40, R3-42 |

Hole counts fell from 22 to 15 to 12 critical-plus-high across the rounds; residual structural risks remain (Appendix C).

---

## Appendix C. Top 5 residual risks

1. **The signal may not be a Q&A signal.** The statement term carries most of the variance of s (corr(s, −S) = 0.98 on
   the lexicon proxy; human ratings 2011-2019 give var(S)/var(s) 1.42 and AR(1) of s 0.94), the TDW filter keeps 14-32%
   of chair Q&A sentences, opening remarks preview Q&A tone in 2016-2022, and post-τ drift can load on the in-presser
   price move. A GO may be a statement-tone, policy-cycle or price-continuation association. Mitigation: D-DOM, H1-A,
   H1-PX, H1-O, H1-SEP and fixed labels (3.9); none can flip G3.
2. **Power and inference.** The realised confirmation n is about 16-20 (two-sided power 0.13-0.25 at r = 0.2-0.3; MDE
   about 0.59; top 5 meetings carry 54% of the sum of squares; Kish n_eff about 10), so a NO-GO is uninformative and the
   PPV of a GO at π = 0.1 is 0.22-0.42. The BENCH-R sign is not constant across 2011-2026 (continuation before 2020,
   reversal reported after). Mitigation: size-controlled critical values, published operating characteristics, GO
   wording "association, not an edge", H1-clean and Tier P evidence.
3. **Clock and bars.** τ depends on archive time bases with an uncalibrated error ε (M = 30 s assumed), on MP4
   truncation handling and on 20 of 27 confirmation meetings having anchors today; 1m bars and a median 37 s anchor
   interval cannot identify 5-30 s delays, and the literature's co-movement is contemporaneous. If the next-open effect
   is zero and only same-minute co-movement exists, the answer is no-trade. Mitigation: upper-bound τ_used, M ± reruns,
   2026-10-28 / 12-09 calibration, H1-exec-live replay.
4. **Blindness and governance.** Outcome windows have been read and stance scores on presser text produced by parallel
   pipelines (`bt`, chrono smoke and integration, the fedspeak_v2 full run, the placebo chain) before any ratification;
   blindness of the frozen choices rests on seals, the PREREG-R timestamp and attestations. Only H1-P and BENCH-R-P are
   fully blind, and they accrue 6-8 Warsh-era events a year (24 events take 3-4 years). Mitigation: section 3.11; one
   code base; labels for any attested viewing.
5. **Chair change, live path and licences.** Every future event is a Warsh event (shorter pressers, 1.6-1.8% explicit
   rate-stance sentences vs 2.8-14% for Powell, 4-6 qualifying statement sentences); the live delay and stream-lag
   references are unmeasured and G5 is terminal after one presser; costs are assumed until measured; the scorers are
   non-commercial, so no real-money step exists without the team's own permissive labels. Mitigation: D-VAL-W with
   forward-only verdicts, R3-40 sizing, measurement-only 2026-10-28, per-scorer counts.

---

## Appendix D. Two-week checklist (2026-10-05..10-18, then to 2026-10-28)

Tags: **[5090]** local reference platform; **[HPG]** HiPerGator, one `fp-gpu` singleton job with at most 2 B200 (never
before the sponsor's written confirmation); **[CPU]**; **[T]/[A]/[U]/[S]** as in "How to read". Order rule:
PREREG-R → stance scoring of registered meetings → outcome-free tables → PREREG-D → market join.

**Before Monday (2026-10-03 evening and 2026-10-04; hackathon due 10:00 ET)**
- [U] Read section 5; act on U7 (seal the fedspeak_v2 full-run and placebo-chain outputs). Nobody opens any section 0
  output.
- Nothing from this project runs on the 5090 until the hackathon is submitted.

**Week 1**

*Mon 2026-10-05: people and setup*
- [T][A] Team session (about 60 min): PREREG-R decision sheet T1-T9 with defaults; attestations; name the code base.
- [U] Sponsor request for written confirmation (A-48(4)); FOMC-RoBERTa access request if not yet sent (U5); answer U1
  (purchase) and U3 (timestamp route); decide `ai-workshop` and the team-runner push (U4).
- [5090] Install ffmpeg. Create the uv environment: CUDA torch build that supports the 5090, pinned transformers,
  faster-whisper 1.2.1, WhisperX 3.8.6, pinned `nltk`; record driver and library versions.
- [T] Team applies the 3.12 package edits in the code base of record (anchor file, bound columns, `latency_s` 0,
  per-meeting `clock_source`, local registry (the source-date label rule is already in `hpg/fedpress`), deterministic flags, smoke 20200303 with no
  score printouts, refusal of registered meetings without a PREREG hash file, complete fingerprint, frozen decoding,
  `GPU_LAYOUT=job`, `fp-gpu` names, no `--allow-concurrent`) and the unit tests (entry bar, exec30 bar, half-width drop,
  settlement grid, commit at t_fill, 25 h guard, GPU audit). `pytest` passes before any run.
- [CPU] Pull all 2016+ media once (MP4 or HLS audio, VTT, PDFs, statement HTML); freeze SHA-256 and Brightcove
  `updated_at`. IA item-existence check for the 7 uncaptioned confirmation dates (R3-18). GDELT re-pull for scheduled
  +30..+75 min, 2016-2024 (R3-13(4)). Free get_cost printouts for every extra (U2).

*Tue 2026-10-06: PREREG-R*
- [T] Write, hash and timestamp PREREG-R (rules, ratifications, register, access log including F-01, attestations).
- [5090] After the timestamp: G0 on 20200303 with smoke-only models (GPU and CPU agreement; run twice, identical τ and
  argmax). G0 on Warsh 2026-09-16: ASR and alignment, pipeline health only; text scores to a sealed file.
- [People] D-VAL-W and D-VAL-C annotators receive unit lists (filter and clause-split output, no model scores, no market
  data); publish the simulated false-fail rate and power first (R2-09(6)); labelling starts.

*Wed 2026-10-07 to Fri 2026-10-09: outcome-free freeze work, local 5090 under R2-36(2) and F-09 (LLM stack unloaded,
autonomous worker paused, no other GPU training resident)*
- [5090] 45 deterministic fine-tunes (15 keys x 3 seeds, source-date labels, float32, `reference_compile=False`); expect
  about 1-2 h. Training-row audit; accuracy gate and presser-domain F1 (threshold already confirmed in PREREG-R); cutoff
  probe. Hash checkpoints → checkpoint manifest (this hash, with PREREG-R, makes 2026-10-28 Tier P eligible if done
  before 2026-10-28 13:59 ET).
- [5090] Completeness decodes (first and last 180 s) and VTT→MP4 offsets; forced alignment of all 2016+ MP4s (hours);
  freeze `clock_source` per meeting.
- [CPU] Per-cue anchor tables, τ_used per R3-13/R3-14, Δ_missing; realised n and dropped list.
- [HPG, after [S]] `bash slurm/00_setup.sh info`; `showQos jie.xu`; inside `srundev`: `00_setup.sh env`, `models`,
  `check`; `umask 077`, `chmod 700`; `gpu_check` submitted as `fp-gpu --dependency=singleton` on 1 B200; CPU dummy
  singleton-array test (R3-41(2)). No GPU array is ever submitted.

*Sat-Sun 2026-10-10..11*: buffer; no presser.

**Week 2**

*Mon 2026-10-12 to Tue 2026-10-13*
- [5090] Score table for every registered meeting with the frozen checkpoints; D-VAL on 2011-2019 (ρ_within, statement
  ρ, walk-forward 2011-2015 keys); D-DOM, D-VINTAGE, D-OPEN, Δdot, political share and L on 2016-2026; D-VAL-C labels
  hashed.
- [CPU] Simulations: A-11 / R2-28 fixed-design operating characteristics, R3-20 critical values, R3-19 label firing
  rates and demotion list, R2-27 PPV, R2-25 H1-P size and look-1 power, A-43 studentised OBF size.
- [HPG] One `fp-gpu` job with 2 B200 and in-job sharding: replicate the 45 fine-tunes into
  `models/stance_walkforward_hpg_replica` and the ASR / alignment tables; agreement report (argmax flips, meeting-score
  deltas, τ changes). Not on the freeze path; a late or failed HPG job delays nothing.

*Wed 2026-10-14 to Fri 2026-10-16: PREREG-D and, only then, outcomes*
- [T] Assemble, hash and timestamp PREREG-D (checkpoints, score table, clock tables, realised n, operating
  characteristics, PPV, demotion list, D-VAL-C labels, data hashes; 1s and bbo-1s files only if U1 confirmed).
- [5090/CPU] After the timestamp: A-07 statement-window QA → hashed QA addendum; H1-primary 2023-2026 once from the
  frozen hash (G3); then Tier 1, Tier 2, Tier 3 and D rows in register order; BENCH-R tables; spreads if U1 confirmed.
- If PREREG-D slips, G3 slips with it (no partial freeze); the live preparation below continues.

*Sat-Sun 2026-10-17..18*: buffer.

**To 2026-10-28**
- [5090] Freeze the live text pipeline (ECAPA thresholds from prior meetings, end detector, closing-phrase list); D-ASR
  replays (Warsh 2026-09-16; Powell 2026-01-28, 03-18, 04-29); 1x replay rehearsal of 2026-09-16 under the A-44
  runbook; scheduler dry-run in EST before 2026-12-09.
- [U] By 2026-10-21: register the reference set and L_ref values (U6); standing bbo cap or per-day quotes (U2);
  OpenTimestamps answer (U3).
- [T] Confirm the checkpoint manifest hash is timestamped before 2026-10-28 13:59 ET.
- [HPG, optional] H2/H3 feature replication on Powell meetings in the same `fp-gpu` pattern; the 5090 tables remain the
  reference.
- 2026-10-28 (measurement-only): runbook from 13:30 ET; both recorders from 13:45 ET; shadow decision with D_frozen :=
  60 s; decision log hashed before any fetch; G5 measured against the registered references (a fail is terminal); the
  first market pull no earlier than 17:30 ET on 2026-10-29 (25 h rule).

Do not do in two weeks: Qwen-Omni or any LLM on the videos; pyannote without signed terms; OpenFace demo; reading the 1s
files before U1; Warsh face or voice; reviving daily TLT lexicon; any GPU array or second concurrent GPU job on
HiPerGator; opening any sealed output.

---

## Appendix E. Evidence index

- Team records: `plan/team_FINAL_PLAN.md`; `plan/DEVIATION_D1_stance_model.md` (D1, D1a); `v2/HYPOTHESIS_v2.md`
  (Amendments 2 and 3).
- Our records: `plan/plan_v0.md`; `plan/GAP_REPORT.md`; `plan/merged_plan_v0.md`..`merged_plan_v3.md` (full amendment
  texts; sections H, I, J list each round's holes).
- Check outputs: `plan/checks/`, `plan/checks_gap_exec/`, `plan/checks_gap_models/`, `plan/checks_it1_econ/`,
  `plan/evidence/`, `plan/evidence_it1_execution/`, `plan/checks_r1_*`, `plan/checks_r2_*` (including
  `checks_r2_merge/exposure_inventory_20261003.txt`), `plan/checks_r3_*`.
- Research notes: `<scratch>/fedtalk/` (literature, voice, face, nlp, data_markets with `vtt_summary.csv`, cost queries,
  transcripts, 84 WebVTT files, Brightcove config; verify_literature with `fomc_all.xlsx`; verify_models).
- Empirical studies (prior only): `<scratch>/intraday_study/fomc_and_hourly_trend/out_fomc/run_log.txt`;
  `<scratch>/auction/verify/verify_extra.json`; `<scratch>/fedspeak/replicate/results.json`.
- Package: `hpg/README.md`, `hpg/config.yaml`, `hpg/docs/HIPERGATOR_NOTES.md`, `hpg/manifest/pressers.csv`,
  `hpg/slurm/`.
- External: USMPD (https://www.frbsf.org/wp-content/uploads/USMPD.xlsx); CME SER-8171
  (https://www.cmegroup.com/notices/ser/2019/01/SER-8171.html); Databento symbology and licensing
  (https://databento.com/docs/standards-and-conventions/symbology,
  https://databento.com/blog/introduction-market-data-licensing, https://databento.com/blog/CME-history-extended-to-2010);
  UF Policy 12-002 (https://policy.ufl.edu/policy/acceptable-use-policy); Slurm sbatch singleton
  (https://slurm.schedmd.com/sbatch.html); UFRC GPU docs (https://docs.rc.ufl.edu/scheduler/gpu_access/).
