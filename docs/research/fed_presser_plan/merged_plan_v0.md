# FINAL PLAN — FOMC presser multimodal research (hardened), merged v0

Merged 2026-10-03. Sections A-E are the team's `team_FINAL_PLAN.md`, kept in its structure and wording. Where an
amendment touches a sentence, the original text is kept (struck through where it is replaced) and a marker
**[A-nn]** points to section F, "Amendments (dated 2026-10-03)". Nothing in the pre-registered family (section A.2)
is changed silently: every change is a dated correction, implementation detail or clarifying amendment, or a
separately pre-registered extension with its own id. The gap evidence and verdicts are in `GAP_REPORT.md`.

Path shorthand: `plan/` = `<solo-repo>/research/fed_presser_plan/`;
`hpg/` = `<solo-repo>/research/fed_presser_hpg/`; `<scratch>/` = the research session scratchpad
(`%LOCALAPPDATA%/Temp/<session-tool>/D--AUTOMATION/<session>/scratchpad/`).

---

Python + uv. Sample specified by the team: 88 meeting videos, 2016 through October 2026 (87 scheduled/equivalent +
extra 2–3 Mar 2020). That is 88 policy meetings, not 88 pressers. Q&A analysis is presser=1 only (~75 scheduled
pressers through Oct 2026; 74 already held as of 2026-10-03; Oct 28 is in the 88 but has not happened yet). Kevin
Warsh has been Chair since 2026-05-22. This document is the hardened plan after Phase 1 research, verification,
plan_v0, 10 critic/patch iterations, and a merge of the iteration-1 critic/research agents. Details and URLs live in
PHASE1_*.md and VERIFICATION_LOG.md. Holes: hole_register.md.

> Count note [A-06, A-11]: the Board manifest (`hpg/manifest/README.md`) lists 75 held pressers 2016-01-27..2026-09-16
> (73 scheduled + the unscheduled 2020-03-03 and 2020-03-15); 2026-10-28 is the 76th if held.

No AI attribution. No paid download until get_cost is printed and is inside remaining Databento credit.

## A. Hardened plan

### 1. Bottom line

The papers we opened do not show tradable post-answer predictability net of latency and costs.

- Gorodnichenko, Pham, Talavera (AER 2023): 36 pressers, 692 answers, 2011–2019. The ~75 bp SPY figure is a daily
  local projection over several days, not a same-minute fill. Minute-level impact is ~1 bp and imprecise. Do not cite
  75 bp as an intraday edge.
- Curti & Kazinnik (JME 2023): Azure face; contemporaneous minute-level co-movement. Exact "−0.53 bp / 3-min; dies in
  5–10 min" is from discussant slides, not opened JME tables — UNVERIFIED as published coefficients. Azure emotion
  retired 2023-06-30 (new-user cut 2022-06-21).
- Gómez-Cram & Grotteria (JFE 2022): 41 pressers through Jan 2020; 13:50–14:20 predicts the presser window (corr 0.58
  medium Eurodollars, 0.44 S&P). Narain & Sangani (IJCB 2026) show that continuation reversed under Powell after
  COVID. BENCH-R must be split pre-2020 vs 2020–26; do not treat 2011–19 continuation as a 2026 rule.
- Shah, Paturi, Chava (ACL 2023): combined F1 ≈ 0.71; presser-only F1 ≈ 0.53–0.55; CC BY-NC 4.0. QQQ story without
  fees. Hub card opened; a separate "gated weights" banner was not confirmed in the fetched page.
  **[A-28]**: the Hub API shows `gated: manual` (sha aa3bc4281fb1fe73c8872e09ad5c64b898f90d83).
- Alexopoulos et al.: testimonies, not pressers; some multi-day persistence — do not import.

strategies/01 daily hawk/dove → TLT is a NO-GO. Date-only speech HTML is not a t=0.

**Realistic objects**

- **BENCH-R** (nearest to executable): at 14:20 ET the statement-window return is known without video. Hold that sign
  through presser-end on ZT. Cost with a dollar tick table, not TLT bps: ~~ZT 1/8 of 1/32 = $15.625/contract~~
  **[A-04]** ZT 1/4 of 1/32 = $15.625 through 2019-01-11, 1/8 of 1/32 = $7.8125 from 2019-01-14; ES 0.25 = $12.50.
  Stress {2, 4} ticks/side (1 tick is a lower bound only). Replication of Gómez-Cram, not new alpha. Pre-register
  2011–19 vs 2020–26. If the Powell-era sign flips (Narain–Sangani), report the break; do not average regimes into
  one Sharpe. **[A-06, A-07, A-08, A-19]**: 2011–2015 data added with era clocks; non-blind disclosure; USMPD QA;
  costed hurdle table.
- **H1-primary** (research residual): meeting-level Q&A hawkishness minus same-day statement, frozen FOMC-RoBERTa, ZT,
  one observation per meeting. Fill on 1m data = next bar open after answer-end τ (OHLC, associational). Position is
  residualized on 13:50–14:20. 5 s / 15 s / 30 s is not a 1m backtest knob — those delays collapse to the same or
  adjacent bar. Delay is a live timing measurement. H1-answer (next-open → +1 m / +5 m, then +15 m appendix) is a
  non-overlapping diagnostic only. Confirmation 2023–2026 Powell only for P&L language.
  **[A-02, A-03, A-09, A-10, A-11]**: τ dated at the anchored upper bound; exit, sign, statistic and alpha
  clarified; residualisation and score function frozen; confirmation n = 27.

~~Weekend hackathon: event list, get_cost, two smoke meetings, write-up. Not an 88-video or ~75-presser multimodal
Sharpe.~~ **[A-35]** The hackathon entry (due 2026-10-04 10:00 ET) is a different, already-built strategy; this
project starts 2026-10-05 and is still not an 88-video or ~75-presser multimodal Sharpe.

Voice/face are Powell-only secondaries with kill switches. Warsh: text only. ~~RTX 4050, CUDA not installed: CPU
Whisper-turbo default.~~ **[A-27]** Compute: local RTX 5090 32 GB (reference path and live path) plus HiPerGator
B200 (offline batch, at most 2 GPUs per job or session); CPU path kept as a fallback for teammates.

### 2. Pre-registered family (locked)

The Spec and Role columns are the team's locked text, unchanged. The last column only points to dated amendments.

| Id | Spec | Role | Dated amendments (section F) |
|---|---|---|---|
| H1-primary | Meeting-level mean(hawk(Q&A)) − hawk(statement); Q&A only; ZT; next 1m open after τ; residual position after 13:50–14:20; chair dummy | Only residual GO/NO-GO | A-01 (ZT = `ZT.v.0`), A-02 (τ upper bound), A-03 (exit/sign/test, clarifying), A-09 (residualisation; chair dummy constant within confirmation), A-10 (score spec), A-11 (n = 27, operating characteristics), A-15 (validity diagnostic) |
| H1-answer | Next-open → +1m / +5m (then +15m appendix); non-overlapping; meeting cluster | Diagnostic only | A-22 (selection rule, inference), A-21 (mid-quote extension), A-18 (1s extension, anchored meetings only) |
| BENCH-R | Sign(13:50–14:20) from 14:20 to presser-end; ZT; {2, 4} ticks/side; split at 2020 | Replication / regime check | A-04 (tick table), A-06 (era clocks, 2011–2015 data, split at 2020-01-01, break statistic), A-07 (USMPD QA), A-08 (non-blind), A-19 (hurdle table; BENCH-R-ES extension) |
| H1-Q | H1 + question hawkishness | Robustness (collider risk) | A-10, A-15 (questions are out of the classifier's domain) |
| H2/H3 | vocal_proxy / expression_proxy; prior-meeting same-chair z; Powell only; 4-meeting burn-in; variance floor; identity gate | Secondary; off for Warsh | A-31 (vocal_proxy spec), A-32 (identity, speech confound), A-33 (A/V skew) |
| H4 | Combined vs text on 2023–2026 Powell after H1 frozen + code hash | Secondary | A-26 (training window, Clark-West), A-31 (valence excluded) |
| Lexicon | Frozen strategies/01 20+20 | Negative control | — |

Separately pre-registered extensions added by amendment (none can replace, rescue or be promoted over a locked
result): **H1-chrono** (A-14), **H1-run** (A-03), **BENCH-R-ES** (A-19), **H1-answer-1s** and **STMT-ABS** (A-18),
**H1-exec30** (A-20), **H1-answer-mid** (A-21). Diagnostics: **D-VAL** (A-15), **D-ASR** (A-16).

Opening remarks excluded. 2016–2022 RoBERTa scores are classifier-contaminated (ACL data through 2022); confirmation =
2023–2026 Powell. 2022 vs rest and SEP dummy are robustness **[A-26: 2022 split runs on 2016–2022 descriptives
only]**. Next-day not primary. No LLM in the primary path. No 1s bars without a new user-approved quote. ~~Primary
rates name = ZT.c.0.~~ **[A-01]** Primary rates name = `ZT.v.0` (volume-ranked on the previous day; same intent:
the liquid front ZT). Do not use SR3.c.0 as the Gómez-Cram 60-month Eurodollar analogue (front SR3 is ~one quarter;
dated 5th–8th SR3 post-2018 is robustness only). ~~ES window = τ → presser end; 16:00 ET is equity-only
robustness.~~ **[A-03]** ES and ZT share the H1-primary exit (close of the last 1m bar before 16:00 ET); next-day
15:00 ET ZT settlement is robustness only. No extra symbols (NQ, FX, GC) unless H1 GO.

### 3. Stack

| Channel | Primary | Cross-check | Notes |
|---|---|---|---|
| Text | gtfintechlab/FOMC-RoBERTa | ~~Moritz-Pfeifer/CentralBankRoBERTa-* (MIT);~~ Loughran-McDonald uncertainty (academic) | CC BY-NC — disclose. **[A-30]** CentralBankRoBERTa measures agent sentiment, not stance: not a stance cross-check or fallback. **[A-14]** chrono-bert walk-forward as extension scorer. **[A-28]** pin revision sha; access is gated (manual) |
| Clocks | ~~openai/whisper-large-v3-turbo via faster-whisper, CPU~~ **[A-05]** official WebVTT (after QA) + GPU forced alignment of PDF text to Fed MP4 audio; whisper-large-v3-turbo on GPU for the live path | Fed PDF; Gorodnichenko answer times (2016–2019 segmentation only) | PDF = words; ASR = time; drop bad WER-proxy meetings. **[A-05]** words = PDF, in-video time = QA'd captions / forced aligner; drop rule on alignment quality. **[A-02]** wall-clock = per-meeting anchor, τ at upper bound |
| Diarization | Transcript labels | pyannote 3.1 only if Hub terms accepted | Not required. **[A-16]** required live: ECAPA chair verification (Apache-2.0, ungated) |
| Vocal_proxy | audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim | parselmouth F0 | CC BY-NC-SA; not "emotion of the Chair". **[A-31]** arousal primary, valence excluded |
| Expression_proxy | MediaPipe + EmotiEffLib @ 1 fps | — | ~~Apache~~ **[A-30]** code Apache-2.0; EmotiEffLib weights AffectNet-trained (non-commercial); not Azure; OpenFace not in demo. **[A-32]** identity model named |

### 4. Data and clocks

Statement 14:00 ET, presser ~14:30 ET (2027 FOMC PR). **[A-06]** Exceptions: 2011–2012 statement ~12:30 / presser
14:15; 2020-03-03 10:00 / 11:00; 2020-03-15 Sunday 17:00 / 18:30. Board site public domain unless marked. C-SPAN is
not.

Databento GLBX.MDP3 ohlcv-1m, continuous ZT (primary), ZF/ZN/ES robustness, ~~13:30–16:30 ET presser days~~
**[A-06]** windows relative to each event (12:00–16:30 ET in 2011–2012, 13:30–16:30 ET otherwise, 2011–2026),
volume-max expiry check **[A-01: `.v.0` symbols; instrument_id frozen per meeting]**. Unit sheet: OHLCV-1s and 1m
both $70/GB historical — 1s is more bytes. Quote get_cost first. Fill = next minute open. Until MBP-1, all 1m results
are associational on OHLC, not executable mids. **[A-13]** bbo-1s (top of book) is enough to measure 1-lot spreads.

~~Record a start-time source per meeting (Bloomberg if available, else first PDF-matching audible open). Drop the
meeting from (P) tests if start uncertainty > 30 s.~~ **[A-02]** Record a per-meeting anchor interval (Bloomberg
first-word headlines if access is confirmed, else TV-archive caption segments); date τ at its upper bound; a meeting
with no anchor or an interval wider than 60 s goes to (C) only.

Fleming & Piazzesi: cash Treasury spreads stay wide 30 min–2 h after FOMC — the presser is still inside the 14:00
stress window. **[A-13]** (cash Treasuries, not CME futures; futures spreads are measured, not cited.) Do not reuse
strategies/01 TLT 1.5/5.0 bps. Frozen assumption until MBP-1: {2, 4} ticks/side on the dollar tick table above
**[A-04: date-dependent ZT tick; plus fees]**. No net Sharpe on H1.

### 5. Pipeline

Board video + transcript PDF
→ ~~CPU turbo word times~~ **[A-05]** QA'd WebVTT + GPU forced alignment word times **[A-02]** + per-meeting wall-clock anchor (τ upper bound)
→ Q&A segments (Chair only)
→ frozen RoBERTa on statement vs answers **[A-10 score spec]**
→ optional Powell vocal/expression proxies
→ join ZT **next 1m open after τ** **[A-01 `ZT.v.0`; A-03 exit; A-07 USMPD QA gate before outcomes]**
→ H1-primary + H1-answer diagnostic + BENCH-R (regime-split)

Live path: time ~~Fed/YouTube~~ **[A-17]** the federalreserve.gov live player (there is no YouTube live stream) vs
~~CME~~ an independent clock (NTP-queried local clock, first-word headlines, PROGRAM-DATE-TIME if present) on a held
presser; freeze delay = max(measured p90, 30 s); 60 s pessimistic appendix. If p90 > 60 s, kill live (G4/G5) and ship
measurement-only. Warsh live = half-size text **[A-17: notional/DV01 sizing on paper]**. Offline 1m tests do not
retune 5/15/30 s.

### 6. Evaluation and power

n ≈ 75 presser meetings inside the 88-meeting archive, not 2,000 iid answers and not n=88. **[A-11]** Confirmation
n = 27. Underpowered for small H2/H3. ~~Block bootstrap + wild cluster.~~ **[A-23]** Decision p = wild bootstrap
(one observation per meeting); companions reported. Holm not needed for a single primary; secondaries cannot be
promoted after looking **[A-26: Holm within the secondary family]**.

Report (A) BENCH-R costed and (B) H1 non-executable separately.

### 7. Gates and calendar

| Gate | Go | No-go |
|---|---|---|
| G0 | ~~CPU ASR~~ **[A-27]** GPU (and CPU-agreement) ASR/alignment + RoBERTa on one Powell and 2026-09-16 Warsh | No video/ASR; **[A-28]** "no model access" recorded separately |
| G1 | get_cost under credit | Shrink window/symbols; ask before 1s |
| G2 | Event list; missingness vs VIX table **[A-05: missingness = caption, alignment and anchor quality; A-07: USMPD QA gate]** | Crisis MNAR + imputed video |
| G3 | H1-primary on confirmation sample **[A-03, A-11: one-sided alpha 0.05, wild bootstrap; false-GO rate and power published first; A-15 measurement gate]** | Stop; do not mine H2 |
| G4 | H2/H3 variance/identity gates on Powell | Ship text-only |
| G5 | Paper-trade text, half-size on Warsh, only if live p90 delay ≤ 60 s **[A-17, A-25: operational pass criteria only]** | Kill live; measurement-only |

Remaining pressers: 2026-10-28, 2026-12-09; 2027-01-27, 03-17, 04-28, 06-09, 07-28, 09-15, 10-27, 12-08. **[A-34]**
2027 dates and presser flags are provisional (six-meetings-a-year proposal in the July 2026 minutes); refresh after
each meeting.

### 8. Licenses and ethics

Disclose CC BY-NC (FOMC-RoBERTa, audeering). Loughran academic. pyannote gated. OpenFace/LibreFace research-only —
not the public demo. Do not claim to read Warsh's feelings. Features are proxies. **[A-30]** EmotiEffLib and
InsightFace weights are non-commercial in effect; chrono-bert fine-tunes inherit CC BY-NC from the labels. **[A-02]**
TV-archive captions: store derived offsets only. **[A-27]** HiPerGator storage is for research and educational data
only; use it under the sponsor group's allocation and with the sponsor's agreement.

### 9. Budget

$0 APIs. Databento 1m presser windows only after quote. ~~Laptop CPU path must work without the shared 5-GPU
cluster.~~ **[A-27]** The CPU path must still work for teammates, but the reference score and time tables are computed
once on GPU, hashed and distributed. **[A-13, A-18]** Optional purchases, each after the user approves the printed
quote: bbo-1s $3.92, ohlcv-1s $5.47, MBP-1 ZT+ES $29.39, 2011–2015 ohlcv-1m about $0.04.

## B. Hole register (full)

See [hole_register.md](hole_register.md) for every id, patch, and residual. Counts below. The 2026-10-03 gap review
is in [GAP_REPORT.md](GAP_REPORT.md).

## C. Convergence (new critical+high holes per iteration)

| Iteration | New critical | New high | New C+H | Note |
|---|---|---|---|---|
| 1 | 4 | 6 | 10 | iid answers, test explosion, Warsh n, mids, 14:00 steal, 88 meetings vs ~75 pressers, CUDA, ASR/PDF, NC license, in-sample RoBERTa, opening/questions/reverse causality |
| 2 | 2 | 5 | 7 | H4 peeking; SEP; rolls; close clock; COVID face; FEDS horizon |
| 3 | 1 | 4 | 5 | burn-in z; SR3 panel; LLM lore; text-only GO |
| 4 | 1 | 3 | 4 | BENCH-R still not HFT-safe (patch: 14:20, no ASR); unscheduled; identity |
| 5 | 0 | 3 | 3 | hash freeze; missingness MNAR; collider |
| 6 | 0 | 2 | 2 | Warsh H2/H3 off; forbid 1s |
| 7 | 0 | 2 | 2 | meeting-level H1; alignment drop rule; continuation vs reversal |
| 8 | 0 | 1 | 1 | 48h vs two-week scope; two reported Sharpes |
| 9 | 0 | 1 | 1 | explicit underpower; no Warsh voice claim |
| 10 | 0 | 1 | 1 | lock delay at 30 s (no retune) |
| Gap review 2026-10-03 | 3 | 16 | 19 | roll symbol, wall-clock anchor, H1 exit (critical); see GAP_REPORT.md |

Yield fell; all 10 iterations still ran. Residual criticals from iter 1 remain structurally true (small n,
contemporaneous literature, Warsh) even after patches — that is what "residual risk" means.

## D. Top 5 residual risks

1. **Absorption vs 1-minute bars.** Literature co-moves during the answer. Next-open after τ is already 1–4 minutes
   after speech onset. 5/15/30 s cannot be identified on ohlcv-1m. If (P) next-open dies and same-minute (C) lives,
   publish no-trade. **[A-02, A-18]** Historically the clock (median anchor interval ~37 s), not the bar size, is the
   binding limit; 5–30 s delays are identifiable only on NTP-logged live meetings.
2. **Statement continuation vs reversal.** Gómez-Cram continuation is 2011–Jan 2020. Narain–Sangani: Powell
   post-COVID reversal. H1 may be zero once 14:00 is residualized; BENCH-R may be the only costed object, and its sign
   is not a 2016–2026 constant. **[A-08]** Its USMPD analogue has already been seen; BENCH-R is non-blind.
3. **Chair change.** Warsh n=3 held (4th in-window is Oct 28); voice/face off; even text H1 is a domain shift. Oct 28 /
   Dec 9 paper-trades can fail for that reason alone. **[A-34]** Warsh may also change the meeting and presser
   format.
4. **Licenses vs sponsors.** FOMC-RoBERTa and audeering are non-commercial. ~~Demo-legal fallback is MIT
   CentralBankRoBERTa + frozen lexicon, which is a weaker FOMC stance model.~~ **[A-30]** There is no permissive,
   uncontaminated stance fallback: CentralBankRoBERTa is not a stance model. A permissive path needs the team's own
   blind labels.
5. **Unmeasured costs and live delay.** No billed get_cost; no ~~4050/YouTube~~ timing; no 2024–2026 FOMC futures
   bid-ask. {2, 4} ticks/side is an assumption, not a measurement. **[A-13, A-17]** Both are measurable for a few
   dollars and on the local 5090, pending user approval.

Added by the gap review: **6. Instrument and clock errors in the inputs** (A-01, A-02, A-36): until the roll symbol,
the anchor protocol and the package defaults are fixed, any H1 or BENCH-R number would be computed partly on a dead
contract and with early timestamps.

## E. First two weeks — one-page checklist (re-dated by A-35)

**Days 1–2 (~~hackathon weekend~~ 2026-10-05..06)**

- uv project, ~~CPU torch~~ CUDA torch on the 5090 (CPU torch for teammates), ffmpeg, faster-whisper turbo
- Event spreadsheet: ~~2016–2026~~ 2011–2026 meetings, presser flag, chair, URLs, missing video **[A-06, A-07: build
  from `hpg/manifest/pressers.csv`, validated against USMPD; statement word count A-34]**
- Smoke Powell presser + 2026-09-16 Warsh: PDF + video, ~~ASR clocks~~ caption QA + forced-alignment clocks (GPU and
  CPU agreement, A-27), RoBERTa surprise table vs that day's statement
- Print Databento get_cost for 1m ZT/ZF/ZN/ES **[`.v.0`]**, ~~13:30–16:30 ET~~ era windows, presser days (no download
  if over credit); also print bbo-1s / ohlcv-1s quotes for the user (A-13, A-18)
- Write-up pages: H1 vs BENCH-R, 88 meetings vs ~75 pressers, Warsh rule, CC BY-NC, "mids ≠ fills"
- Do not expand the lexicon, call 1s, or report a multimodal Sharpe
- **Added:** user requests FOMC-RoBERTa access (A-28); apply the A-36 config changes

**Pre-freeze block (2026-10-07..09), moved ahead of any market download (A-12, A-14):**

- Team ratifies A-03 (exit, sign, statistic) in writing, dated
- Write PREREG_H1.md: family, all amendments in section F, H1-chrono / H1-run / BENCH-R-ES / extension rows, D-VAL,
  D-ASR, prior-exposure section (A-08), instrument map, anchor list and dropped list, thresholds, model shas, lock
  file, Databento request parameters, tick/cost table, statistics and decision rules; SHA-256 manifest; timestamp the
  hash (publication only with user approval)
- Run D-VAL (text-only) before any market join

**Days 3–7 (2026-10-12..16)**

- Download 1m windows if quote OK
- Align all available presser PDFs; ~~drop high-mismatch meetings~~ apply the frozen alignment and anchor rules
  (A-02, A-05)
- ~~Freeze code hash;~~ (frozen in the pre-freeze block) run H1-primary on 2016–2022 (contaminated) and 2023–2026
  Powell; run H1-chrono as registered
- BENCH-R with {2, 4} ticks/side (not TLT bps) **[A-04 tick table, A-19 hurdle table]**
- Missingness vs year/VIX **[A-05 redefinition]**
- Optional: Powell vocal_proxy variance floor check (kill or keep H2)

**Days 8–14 (2026-10-19..23)**

- H1-Q robustness; 2022 split **[2016–2022 only]**; SEP dummy — no new primaries
- H3 only if identity gate works; else skip
- Paper-trade protocol for 2026-10-28 and 2026-12-09: text surprise, half-size, timed delay, ZT; kill live if p90
  delay > 60 s **[A-16, A-17: live pipeline frozen, replay rehearsal, NTP-queried clock, hashed decision log; contracts
  ZTZ6 / ZTH7]**
- ~~Pin uv.lock; archive model hashes~~ (moved to the pre-freeze block, A-28)
- If H1 dies: submit measurement + BENCH-R replication, not a fished Sharpe
- **Added (A-35):** if G3 has not passed with a frozen hash by 2026-10-21, 2026-10-28 is measurement-only and
  2026-12-09 is the first counted paper trade

Do not do in two weeks: Qwen-Omni on 88 videos **[A-27: excluded for validity and look-ahead, no longer for
compute]**; pyannote if ungated terms unsigned; OpenFace demo; 1s bars **[unless the user approves A-18]**; Warsh
face/voice trading; reviving daily TLT lexicon.

---

## F. Amendments (dated 2026-10-03)

All amendments below are dated 2026-10-03 and were written before any H1-primary, H1-answer or BENCH-R number on
Databento data exists. Extensions are pre-registered separately and must be included in the timestamped manifest
(A-12) before their data are joined to outcomes. "Needs user approval" items are not executed until the user approves
in person.

### F.1 Corrections

**A-01 Primary rates instrument (correction).** Replace `ZT.c.0` with `ZT.v.0`; robustness `ZF.v.0`, `ZN.v.0`,
`ES.v.0`. Databento's volume rule ranks contracts by the previous day's volume, so it has no look-ahead
(https://databento.com/docs/standards-and-conventions/symbology). Evidence: on 42 of 73 scheduled presser days
2016-2026 (all Mar/Jun/Sep/Dec meetings; 13 of 13 SEP days in 2023-2026) `ZT.c.0` is the delivery-month contract with
0-50 traded seconds in 14:00-15:30 ET against 497-4,058 for `ZT.v.0` (`plan/checks_gap_exec/roll_mapping_output.txt`;
`plan/evidence/gap_data/liq_trades.csv`; `plan/checks/gap_stats_symbology.out`). `ES.c.0` differs from `ES.v.0` on
28 of 73 days. Implementation: freeze `symbology.resolve` output (instrument_id, raw symbol) per presser day into the
manifest; unit test that the event-day contract equals the highest-volume contract on day -1; flag (before outcomes)
any meeting whose window has fewer traded 1m bars than an era-relative floor (2016-2018 `ZT.v.0` has 106-120 of 120
minutes traded in 14:00-16:00, `plan/checks_gap_exec/zt_minute_coverage_output.txt`), floor fixed in PREREG_H1.md.
Paper-trade contracts named now: ZTZ6 on 2026-10-28, ZTH7 on 2026-12-09. The hypothesis instrument is still "front
ZT".

**A-04 Tick table and fees (correction).** ZT $15.625 per tick through 2019-01-11 and $7.8125 from 2019-01-14 (CME
SER-8171, https://www.cmegroup.com/notices/ser/2019/01/SER-8171.html; 1/256 prints first appear on 2019-01-14,
`plan/checks_gap_exec/tick_size_output.txt`); ZF $7.8125, ZN $15.625, ES $12.50. Add an all-in fee of $2.00 per side
per contract (UNVERIFIED; replace with the broker's schedule). The locked stress stays {2, 4} ticks/side in each era's
tick; report ticks, dollars per contract and bp of window sd.

**A-30 Licence and model-role corrections (correction).** CentralBankRoBERTa detects whether a sentence is positive or
negative for households, firms, the financial sector or the government (HF card, fetched 2026-10-03): it is agent
sentiment, so it is dropped as stance cross-check and as "demo-legal fallback". `gtfintechlab/model_WCB_stance_label`
is gated with conflicting licence metadata and trained on Fed text through 2024. EmotiEffLib weights are trained on
AffectNet (non-commercial); InsightFace buffalo_l weights are non-commercial. A permissive, uncontaminated stance path
needs the team's own blind labels. Recommendation for the user's decision (not a new rule): no real-money step until
such a path exists. Research and paper trading are unaffected.

### F.2 Clarifying amendment (team must ratify, dated, before any H1 number)

**A-03 H1-primary horizon, sign and test.** The locked text gives an entry but no exit; with a meeting-level mean,
τ is the end of the last chair answer, which coincides with video end (median gap to the last caption cue 0 s,
`plan/checks_gap_exec/presser_tail_output.txt`), so "τ → presser end" is empty, and ZT's 15:00 ET settlement precedes
the last answer in 98% of meetings (`plan/checks/gap_stats_checks.out` s4). Proposed reading, which keeps
"meeting-level mean" literally:

- τ = anchored upper bound (A-02) of the end of the last chair answer.
- Entry = open of the first `ZT.v.0` 1m bar with ts_event ≥ τ. Exit = close of the last 1m bar before 16:00 ET (the
  15:59 bar). Line 173's "16:00 ET is equity-only robustness" is amended accordingly; ES uses the same exit.
- Sign: continuation, a hawkish residual surprise predicts a fall in ZT (one-sided). Statistic: OLS slope of the
  meeting exit return on the residual surprise (A-09); p-value by wild bootstrap (A-23); G3 GO at one-sided
  alpha = 0.05 with the A-11 operating characteristics published first. If the team prefers two-sided, it says so in
  the same dated ratification.
- Next-day 15:00 ET settlement exit is robustness only.

**H1-run (separately pre-registered extension).** Running mean: at each answer end τ_k, s_k = mean hawk(A_1..A_k) −
hawk(statement), residualised as A-09; hold p_k = −s̃_k from the first open after τ_k to the first open after
τ_{k+1}; flat at the H1-primary exit. Outcome per meeting Y_m = Σ p_k r_k; one-sided test mean(Y_m) > 0, wild
bootstrap, own alpha 0.05, sample 2023-2026 Powell (27). Costs reported with about 12 netted round trips per
presser (`plan/evidence_it1_execution/extra_output.txt`). Secondary; cannot be promoted.

### F.3 Implementation details (do not change any locked hypothesis)

**A-02 Wall-clock anchor protocol.** (1) Anchor source order: Bloomberg first-word headline times if terminal access
is confirmed (unverified today), else TV News Archive caption segments (CNBC, then FBC or Bloomberg TV) matched to the
meeting's text timeline (`plan/evidence/gap_data/tv_anchor.py`, `tv_anchor.csv`, `tv_stats.out`). (2) τ_used = upper
bound of the meeting's offset interval, so clock error can only add delay. (3) Drop rule (explicit change of the
data-section threshold, not of the family): no anchor, or interval width > W = 60 s, sends the meeting to (C) only;
the dropped list is frozen in PREREG_H1.md before results (the old 30 s rule would drop nearly every meeting: median
width 36.7 s). (4) The TV estimate (median +24 s early, IQR +16..+37 s; four broken timelines 2019-05-01, 2021-03-17,
2022-11-02, 2023-02-01 off by 110-271 s) is conditional on archive start accuracy and caption lag ≤ 15 s; report
sensitivity at LAG = 5/15/30 s and calibrate on the NTP-logged 2026-10-28 and 2026-12-09 recordings before citing it
as fact. (5) Never set offsets from market data; market cross-correlation is a diagnostic only. (6) Store derived
offsets only (archive downloads are restricted). (7) Gorodnichenko answer times (video marks + scheduled 14:15/14:30)
are used only to cross-check 2016-2019 segmentation and flag broken caption files (2019-05-01: -173 s,
`plan/evidence/it1_data_eng/gpt_vs_vtt.csv`), never as a wall-clock.

**A-05 Captions and re-timing.** Segment Q&A with caption speaker labels plus PDF text. Re-time all presser audio
against the Fed MP4 with a GPU forced aligner (Qwen3-ForcedAligner-0.6B or WhisperX; numerals written out as words),
pinned version and dtype, outputs hashed. Use VTT times for τ only after per-file QA (video-end overrun, stretched
cues, agreement with the aligner); otherwise use the aligner. Measure aligner boundary error against about 10 good VTT
files first (median, p95). Flag meetings where VTT, aligner and (2016-2019) Gorodnichenko times disagree by more than
2 s. Replace "drop bad WER-proxy meetings" with an alignment confidence/coverage threshold fixed in PREREG_H1.md.
Record clock_source per meeting. Redefine the G2 missingness table on caption, alignment and anchor quality (video is
available for 95 of 95). Missing captions since 2016: 20221214, 20230614, 20230726, 20231101, 20231213, 20240320,
20251210 (`<scratch>/fedtalk/data_markets/vtt_summary.csv`).

**A-06 Event clocks, windows and BENCH-R scope.** Define windows relative to each event's release time from the event
table (`hpg/manifest/pressers.csv`, which agrees with USMPD on all 95 rows): statement window = release −10/+20 min;
BENCH-R entry = first 1m open at or after release +20 min; exit = the BENCH-R presser end below. Extend the Databento
pull to the 20 pressers of 2011-2015 (12:00-16:30 ET in 2011-2012), which implements the locked "2011–19 vs 2020–26".
Exclude 2020-03-03 and 2020-03-15 from the H1-primary and BENCH-R main tests (dated rule; reported separately).
Split at 2020-01-01 as the locked text says; reassigning Jan 2020 is a sensitivity. One break statistic: difference
in slopes, wild bootstrap p. sign(0) = no trade (any deadband or mid-quote sign is a separate variant). Presser end =
anchored upper bound of the end of the last chair answer; fallback the USMPD presser-window end. Times converted with
tz-aware America/New_York; "next 1m open after t" = first bar with ts_event ≥ t (ts_event is bar start; empty minutes
are skipped and logged).

**A-07 USMPD as event table and data-QA benchmark.** Build and validate the event list against USMPD
(https://www.frbsf.org/wp-content/uploads/USMPD.xlsx, updated 2026-09-17). Before outcomes: corr(Databento `ZT.v.0`
window return, USMPD UST2Y window change) over all meetings, statement and presser windows, must exceed 0.8 (expected
sign negative for price vs yield); flag a meeting only when abs(USMPD UST2Y) > 2 bp and ZT moves the wrong way or less
than 25% of the implied move; fix flagged meetings (roll or clock) before the freeze. Report BENCH-R on USMPD UST2Y
next to the ZT version.

**A-08 Prior-exposure disclosure.** PREREG_H1.md lists what has been seen: USMPD statement-sign correlations (SPFUT
+0.41 2011-15, +0.46 2016-19, −0.07 2020-26; UST2Y −0.06 2020-26), 2023-2026 presser-window moves and largest-move
meetings (`plan/checks_it1_econ/usmpd_eras.py`; `<scratch>/fedtalk/data_markets/notes.md` s4). BENCH-R is a non-blind
descriptive replication. The fedspeak_v2 out-of-sample result stays unopened until the H1 freeze is timestamped, or it
is declared if opened first.

**A-09 Residualisation.** Test: OLS of the A-03 exit return on the surprise with R_stmt (13:50-14:20 `ZT.v.0` log
return; era window per A-06) as a control (Frisch-Waugh). Any position, P&L or paper trade: s̃ = s − (a + b·R_stmt)
with a, b from an expanding window over prior meetings only (2016 start), never full-sample or leave-one-out. The chair
dummy is constant within the 2023-2026 Powell confirmation sample and is dropped there; kept in pooled descriptives.
For Warsh paper trades, a is estimated from his prior pressers shrunk to Powell's value with a weight fixed in
PREREG_H1.md.

**A-10 Score function.** One spec, committed with the code hash before any market join: pinned sentence splitter and
version; inclusion rule chosen now (proposal: all chair Q&A sentences of ≥ 4 words, no dictionary filter; the A1/B1
filter version is labelled robustness); sentence score = softmax P(hawkish) − P(dovish) with the label map read from
the model config (fallback LABEL_0 dovish, LABEL_1 hawkish, LABEL_2 neutral, verified); equal sentence weights; mean
over sentences per answer and per meeting; same function for statement sentences; truncation rule for > 512 tokens;
FOMC-RoBERTa revision aa3bc4281fb1fe73c8872e09ad5c64b898f90d83. Report per-meeting sentence counts. Evidence: only
18-21% of recent chair Q&A sentences pass the TDW training filter (`plan/checks_gap_models/gap_models_filter.out`).

**A-11 Confirmation sample size and G3 operating characteristics.** n = 27 (2023-02-01..2026-04-29 Powell; 21
captioned). Publish before the run: the false-GO rate of the G3 rule and its power at r = 0.2 and 0.3 (current
estimates 0.26 and 0.45 at one-sided 5%; MDE r = 0.47; `plan/checks/gap_stats_checks.out`). NO-GO means "not
detected"; report the 90% CI upper bound. P&L language always carries the one-sided p and n.

**A-12 Pre-registration record.** PREREG_H1.md with a SHA-256 manifest of inputs (hypotheses and every amendment here,
event list, instrument map, anchor and dropped lists, thresholds as numbers, model revision shas, package lock,
aggregation code, Databento request parameters, tick/cost table, statistics, sides, alpha, decision rules, extension
registrations). Frozen before the 1m download. `research/` is git-ignored (`.gitignore` line 9), so the current
"LOCKED" family has no commit or timestamp. Preferred: timestamp the manifest hash only (OpenTimestamps, embargoed OSF
or AsPredicted private). Committing with `git add -f`, tagging or pushing to the public remote needs the user's
approval. Every later amendment is dated and hashed the same way.

**A-16 Live text pipeline.** Frozen before the first paper trade, on the local RTX 5090: ASR model and precision,
chunking, sentence split, chair isolation by ECAPA verification (`speechbrain/spkrec-ecapa-voxceleb`, Apache-2.0)
against a voiceprint enrolled from earlier Warsh pressers with a fixed threshold. Paper-trade logs state that scores
are ASR-derived. **D-ASR (separately pre-registered diagnostic):** replay archived audio of the 3 Warsh and the
2025-2026 Powell pressers through the live pipeline; report meeting-level Spearman/ICC between PDF-text and ASR-text
H1 signals, share of non-chair speech admitted, end-to-end latency; the minimum agreement for using ASR text in paper
trades is fixed before results.

**A-17 Live delay and paper-trade protocol.** (1) Source: federalreserve.gov live player (Brightcove account
66043936001), recorded on the 5090 with GPU ASR. (2) Clock: log the NTP offset by query only (for example ntplib or
`w32tm /stripchart`) before and after; correct timestamps afterwards; no change to system time settings. (3) Delay =
stream lag + processing lag; stream lag from minimum lag to first-word headlines and from EXT-X-PROGRAM-DATE-TIME if
the live manifest carries it (unverified); processing lag per answer on the local clock; record a TV/cable feed in
parallel where possible; cross-correlate live audio with the later VOD to get VOD-zero wall time (this also calibrates
A-02). Rehearse by replaying 2026-09-16 at 1x before 2026-10-28. (4) Tamper-evident decision log (code and model
hashes, 14:00 statement score, frozen coefficient and threshold, timestamped decisions), hashed locally and
timestamped before any market data for that day is fetched; emailing or pushing it needs the user's approval. (5) Next
day, price fills from bbo-1s at decision time + measured delay, crossing the spread, costs per A-04 (under $1 per day;
needs the A-13 approval). (6) Size in notional or DV01 units, fractional on paper ("half-size" is impossible with one
ZT lot). (7) Pass/fail on operational criteria only (log complete, p90 delay, pricing reproducible); P&L reported, not
gated. (8) Confirm each meeting has a presser on the Fed calendar; no presser, no event.

**A-22 H1-answer selection and inference.** Greedy earliest-first non-overlapping selection over chair answers of ≥ 40
words, independently per horizon (retention 87% / 25% / 10% at +1m / +5m / +15m in 2023+); when several answers share
an entry bar, use the latest answer; wild cluster bootstrap by meeting with Webb 6-point weights; results also by
clock source.

**A-23 Inference.** Decision p for H1-primary = wild bootstrap with Rademacher weights, 9,999 draws, on the frozen
statistic. Reported, not decisive: HC3 t, permutation p (meeting signals permuted), leave-one-out range with the most
influential meeting named, and the result without the two largest abs(ZT move) meetings.

**A-24 Cost realism and decay.** Yearly gross and net tables plus ex-2022 net for BENCH-R and H1; a separate
2024-10..2026-10 decay check. Stated prior from our studies: costed rates results above a few bp per event are not
expected (ES pre-FOMC +22.8 bp, t 2.78 after 2015 vs −2.3 bp in 2024-26,
`<scratch>/intraday_study/fomc_and_hourly_trend/out_fomc/run_log.txt`; auction ZN rule net Sharpe −0.22 at 1.0
bp/side, `<scratch>/auction/verify/verify_extra.json`; strategy 01 2022 Sharpe 1.19 vs 0.065 otherwise,
`<scratch>/fedspeak/replicate/results.json`). No pre-statement leg.

**A-25 Paper-to-live stopping rule.** Warsh paper trades are operational (delay and pipeline) and support no
performance claim. Any later real-money decision follows a group-sequential O'Brien-Fleming rule at 8/16/24 frozen
events (one-sided 5%: z > 2.95/2.09/1.71) and needs at least 24 events (`plan/checks/it1_stats_checks.out` s6).

**A-26 Secondary family.** Holm within the declared secondary family. The 2022 split runs only on the 2016-2022
descriptive run. H4 trains combined weights on Powell 2018-2022 after the 4-meeting burn-in and tests on 2023-2026
with the Clark-West nested-model statistic.

**A-27 Compute (RTX 5090 + HiPerGator B200, at most 2 GPUs per session).**

- *Local:* RTX 5090 32 GB. Reference GPU path for alignment, ASR, scoring and the whole live/paper-trade path. Note the
  12VHPWR guard on this card can throttle or shut down long jobs; check its logs if a job crawls.
- *HiPerGator:* partition `hpg-b200`, GRES `gpu:b200:N` with **N ≤ 2 per job or session (team rule)**, B200 180 GB,
  14 CPU cores per GPU, investment QOS `jie.xu` (no GPU burst QOS; `jie.xu-b` for CPU-only stages), always set
  `--time/--cpus-per-task/--mem` (default walltime 10 min), job arrays throttled `%2`, caches on `/blue`, scratch
  `$TMPDIR`, GPU jobs offline (`HF_HUB_OFFLINE=1`) after a CPU prefetch job; a GPU idle for 1 h kills the job, so
  CPU stages run as separate jobs and workers share one claim queue. Fallbacks `hpg-rtx6000` (96 GB) or L4; there
  are no A100s any more. B200 queue waits can be long. Source: `hpg/docs/HIPERGATOR_NOTES.md`,
  https://docs.rc.ufl.edu/scheduler/gpu_access/, https://docs.rc.ufl.edu/resources/gpus/.
- *Use:* HiPerGator only for offline research batches (alignment of 95 videos, ASR cross-checks, H1-chrono
  walk-forward fine-tunes, voice/face features) under the sponsor group's allocation and with the sponsor's agreement;
  storage for research and educational data only. Every model in the stack fits on one GPU.
- *Package:* `hpg/` (config.yaml with every tunable, `compute.max_gpus: 2` enforced, profiles for b200 / rtx6000 / l4 /
  local5090 / cpu; manifest of 95 pressers and 148 calendar entries; `fedpress/` code in progress: clock, config,
  log, manifest modules). See A-36 for required config changes.
- *Numerics:* compute the frozen score and time tables once, recording device, dtype and compute_type (float16 on
  Blackwell; int8 only on CPU), hash them and distribute them; report CPU-vs-GPU agreement on the two smoke meetings
  (sentence argmax flips, meeting score change, τ change).
- Qwen-Omni stays excluded for look-ahead and validity reasons; compute is no longer the reason.

**A-28 Model access and pinning.** The user requests access to `gtfintechlab/FOMC-RoBERTa` (gated, manual approval)
now; accepting the conditions is the user's decision. G0 records "no model access" separately from "no video/ASR".
Pin a revision sha for every model (FOMC-RoBERTa aa3bc42…, chrono-bert per checkpoint, audeering 6eba34a…, whisper
41f01f3…, ECAPA 0f99f2d…, the chosen aligner) and archive the weights privately, all before the freeze (moved from
Days 8-14).

**A-29 Model cutoff registry.** Registry of id, revision sha, licence and training-data end (FOMC-RoBERTa labels to
2022-10-15, RoBERTa-large base pretraining to Feb 2019; chrono-bert per checkpoint; WCB to 2024). Only scorers whose
data end before a meeting may enter a confirmatory or P&L analysis of it; contaminated runs (the planned 2016-2022
FOMC-RoBERTa run) are labelled descriptive. Unknown-cutoff models are excluded from 2023-2026 everywhere, cross-checks
included.

**A-31 vocal_proxy spec (fixed before any audio is processed).** Arousal primary, dominance as the pre-named second;
valence excluded (or used only after residualising on the same chunk's text score), because valence carries lexical
content (Wagner et al., TPAMI 2023; `<scratch>/fedtalk/verify_models/wagner.txt`). Chunks 3-15 s with VAD inside
QA'd chair turns, ECAPA identity gate, median per answer and per meeting, causal prior-meeting same-chair z only.
Source invariance: ICC ≥ 0.8 under a 64 kbps re-encode, else the H2 kill switch applies.

**A-32 expression_proxy.** Name the identity model and its licence before H3 data are processed (geometry enrolment
or another permissive option, not InsightFace if a permissive path matters). Upper-face and valence/arousal outputs
with a speaking-flag covariate. fps fixed now (1 fps). Flag 2016-09-21 (640x360). Delete reporter face embeddings.

**A-33 A/V skew.** Estimate each video's audio-video offset (lip-sync cross-correlation on chair close-ups; GCG report
about 3 s, `<scratch>/fedtalk/literature/gcg_lbs.txt` line 965) and shift frame times before H3 masking; log it.

**A-34 Event list maintenance.** Refresh the event table after each meeting (dates confirmed at the preceding meeting;
presser flag only when posted). Do not assume 8 pressers a year in power or paper-trade counts. Add statement word
count; flag a Warsh-era statement-format change as a domain shift for hawk(statement). Source: July 2026 minutes,
https://www.federalreserve.gov/monetarypolicy/fomcminutes20260729.htm (six meetings a year floated; no decision; 2026
unaffected).

**A-35 Calendar.** Re-dated from 2026-10-05 (section E). Code and model hashes frozen by 2026-10-21. If G3 has not
passed with a frozen hash by then, 2026-10-28 is measurement-only (record, measure delay, log shadow decisions) and
2026-12-09 is the first counted paper trade.

**A-36 HiPerGator package defaults (found while merging).** Before `hpg/` produces any H1 input, change in
`hpg/config.yaml`:

| Key (line) | Now | Required | Why |
|---|---|---|---|
| `timing.anchor.rule` (49) | `greeting_at_scheduled` | `file` (anchors_csv from A-02, upper bounds) | putting the chair's first words at the scheduled minute moves every τ earlier than the already-early "video zero = scheduled" convention by the greeting offset (0.6-144 s), i.e. more look-ahead |
| `timing.anchor.max_uncertainty_s` (51) | 30 | 60 (interval width; meetings above go to (C)) | A-02 |
| `fetch.captions_vtt` (96) | false | true | A-05 |
| `turns.clock_source` (136) | asr | QA'd VTT with aligner fallback (a `vtt_qa_then_aligner` mode may need adding) | A-05 |
| `turns.align.method` (138) | text_match | qwen_forced_aligner or whisperx (pinned) | A-05 |
| `turns.align.max_wer_proxy` | 0.35 | alignment confidence/coverage threshold from PREREG_H1.md | A-05 |
| `text.sentence_splitter` (203) | regex (unversioned) | pinned splitter + version | A-10 |
| `text.crosschecks` (202) | centralbank_roberta, loughran_mcdonald | loughran_mcdonald (CentralBankRoBERTa only as labelled agent sentiment) | A-30 |
| `text.classifier_train_end` (207) | 2022-12-31 | 2022-10-15, plus a base-pretraining flag to 2019-02 | A-29 |
| `aggregate.min_answer_words` (216) | 0 | per A-10 (sentences) and A-22 (≥ 40-word answers for H1-answer) | A-10, A-22 |
| `text.chrono_bert.enabled` | false | true for the H1-chrono run only | A-14 |
| `voice` outputs | all three | arousal, dominance; valence off | A-31 |

`compute.max_gpus: 2` and `slurm.array_throttle: 2` already match the 2-GPU rule.

### F.4 Separately pre-registered extensions (own id, sample, decision rule; filed before results)

**A-14 H1-chrono.** Hypothesis: same as amended H1-primary (A-03, A-09, A-10), with stance from a chronologically
trained encoder. Scorer for test year Y: `manelalab/chrono-bert-v1-(Y-1)1231` (MIT, ungated; 26 checkpoints
1999-2024) fine-tuned on `gtfintechlab/fomc_communication` sentences with year < Y (CC BY-NC 4.0; 1,672 labels before
2016, 2,342 before 2022). Hyperparameters fixed in advance (TDW grid, model selection on validation F1 inside pre-Y
labels only), 5 seeds averaged. Accuracy gate on year-held-out labels fixed in PREREG_H1.md; also run D-VAL. Sample:
scheduled pressers 2016-2026 Powell + Yellen (72; 2016-2022 n = 45, 2023-2026 n = 27); reported for 2016-2022,
2023-2026 and pooled. Decision rule: one-sided alpha 0.05, wild bootstrap, own family; secondary, never replaces or
rescues the locked H1-primary GO/NO-GO, cannot be promoted. Also report a sensitivity of the contaminated
FOMC-RoBERTa 2016-2022 run that drops presser sentences appearing verbatim in fomc_communication. Must be filed before
the Days 3-7 FOMC-RoBERTa run on 2016-2022. Disclose annotator hindsight (labels made 2022-23), the inherited NC
licence and the smaller base model. Compute: minutes per fine-tune on the 5090 or one B200.

**A-18 1-second data (needs user approval of the printed quote).** Quote: ohlcv-1s for `ZT/ZF/ZN/ES.v.0` on the 75
2016+ presser windows $5.47 (`plan/evidence/gap_data/cost_2016plus.csv`), bundled with A-13. Uses:
(i) **STMT-ABS** (descriptive): share of the 14:00-14:20 move in ES and ZT bbo-1s mids realised by +5/+15/+30/+60 s
after the exact 14:00:00 release; (ii) **H1-answer-1s**: entry at τ + 30 s (the frozen live minimum; no other delays
scanned), horizons +1m/+5m, fills on bbo-1s quotes, A-22 selection and inference, one alpha, labelled diagnostic, run
only on meetings with anchor width ≤ 10 s (in practice NTP-logged live meetings from 2026-10-28); (iii) BENCH-R entry at
14:20:00 and spread profiles. The locked 1m tests are unchanged.

**A-19 BENCH-R cost hurdle and BENCH-R-ES.** BENCH-R reports the gross regime slope and break test (A-06) plus a costed
hurdle table by regime and year (ZT break-even abs(corr) 0.65 / 1.25 at 2 / 4 ticks in 2011-19, 0.20 / 0.38 in
2020-26; `plan/checks_gap_exec/benchr_cost_hurdle_output.txt`). **BENCH-R-ES**: same windows and rule on `ES.v.0`,
{2, 4} ticks/side plus fees, split 2011-19 vs 2020-26, slope-difference break statistic, own alpha; labelled a
non-blind replication (its USMPD SPFUT analogue has been seen).

**A-20 H1-exec30.** One extra row: entry at the first 1m open at or after τ_upper + 30 s, all else as H1-primary.
Reported beside the locked row; if the locked row lives and this row dies, the conclusion is no-trade.

**A-21 H1-answer-mid.** H1-answer (+1m/+5m) on bbo-1m or bbo-1s mids (cents; needs the A-13 approval); a missing bar =
first quote mid at or after the target second; trade-price version stays as locked; divergence reported by era.

**A-15 D-VAL (diagnostic, reports only).** Before any H1 result, Spearman correlation between frozen FOMC-RoBERTa
scores and the human hawkishness ratings in the Gorodnichenko-Pham-Talavera file
(`<scratch>/fedtalk/verify_literature/fomc_all.xlsx`: 692 answers, 68 statements, 36 pressers 2011-2019): answer
level (2011-2019 and 2016-2019), statement level, and meeting level (answer mean − statement). Threshold fixed now:
meeting level ρ < 0.4 or answer level ρ < 0.3 means "measurement weak", stated in the write-up and treated as a
measurement no-go, not a market result. No tuning on these labels; disclose that some 2011-2019 presser sentences may
be in TDW training data (inflates agreement) and that ratings were assigned after the fact. Same check for H1-chrono.

### F.5 New data (needs user approval of the printed quote)

**A-13 Measured spreads.** Free get_cost quotes for the 75 2016+ presser windows (13:30-16:30 ET, March 2020 shifted),
`ZT/ZF/ZN/ES.v.0`: bbo-1s $3.92, bbo-1m $0.08, ohlcv-1m $0.19; MBP-1 ZT+ES $29.39 (optional)
(`plan/evidence/gap_data/cost_2016plus.csv`; one-day check `plan/checks_gap_exec/cost_checks_output.json`). With
2011-2015 added (A-06) the bbo-1s total rises by roughly a quarter; re-print get_cost for the final window list before
asking. Remaining Databento credit is unknown. After approval: report the quoted spread distribution by era at 14:00,
14:20, each τ and the exit; add a measured-cost column (half-spread at entry and exit + 1 tick slippage) and a
quote-fill column (buy at ask / sell at bid at the first quote after τ_upper). The locked {2, 4}-tick stress and the
H1 statistic are unchanged; no net Sharpe on H1.

### F.6 Open checks (not gaps; verify before relying on them)

- Bloomberg terminal access and export limits at the UF library (A-02, A-17).
- Whether the Databento licence permits sharing raw bars among teammates; share derived tables if unsure.
- Whether the Fed live HLS manifest carries EXT-X-PROGRAM-DATE-TIME (A-17).
- Broker all-in fees per side (A-04).
