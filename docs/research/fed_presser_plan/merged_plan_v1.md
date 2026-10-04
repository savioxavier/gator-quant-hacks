# FINAL PLAN — FOMC presser multimodal research (hardened), merged v1

Merged 2026-10-03; revised the same day after review round 1 (label `r1_patch`). Sections A-E are the team's
`team_FINAL_PLAN.md`, kept in its structure and wording. Where an amendment touches a sentence, the original text is
kept (struck through where it is replaced) and a marker **[A-nn]** points to section F, "Amendments (dated
2026-10-03)". Nothing in the pre-registered family (section A.2) is changed silently: every change is a dated
correction, implementation detail or clarifying amendment, or a separately pre-registered extension with its own id.
The gap evidence and verdicts are in `GAP_REPORT.md`. Round 1 rewrote many v0 amendments in place (each marked
**(revised r1)** or **(r1)**), added A-37..A-44 and A-46..A-50, an enumerated test register (A-45, section G) and the
round-1 change list (section H).
No amendment here was written after any H1-primary, H1-answer or BENCH-R number on Databento data existed.

**Round-1 headline for the reader.** (1) The confirmation clock is weaker than v0 assumed: the Fed MP4 is cut before
the last chair answer at several meetings, the TV anchor covers only the first half hour, and only 20 of 27
confirmation meetings currently have a valid anchor (A-02, A-05, A-11). (2) The v0 decision p-value over-rejected
(size about 0.13 at nominal 0.05); it is now a restricted wild bootstrap of an HC3 t (A-23). (3) The locked signal
"Q&A minus statement" may mostly measure the statement; diagnostics, a Q&A-only extension and fixed interpretation
rules are added (A-10, A-37, A-38). (4) If official FOMC-RoBERTa weights are not in hand by 2026-10-14, H1-primary is
postponed, never replaced (A-40). (5) 2026-10-28 is measurement-only; paper trades count only after a G3 GO (A-43).
(6) HiPerGator use is limited to the research arm and to at most 2 GPUs per user at any time (A-48).

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
  costed hurdle table. **(r1)** One video-free exit for every era (presser start + 60 min), per-regime sign-trade
  means with the slope as companion, 2011-2012 entry at 14:20 after the 14:00 SEP release, sub-tick events reported.
- **H1-primary** (research residual): meeting-level Q&A hawkishness minus same-day statement, frozen FOMC-RoBERTa, ZT,
  one observation per meeting. Fill on 1m data = next bar open after answer-end τ (OHLC, associational). Position is
  residualized on 13:50–14:20. 5 s / 15 s / 30 s is not a 1m backtest knob — those delays collapse to the same or
  adjacent bar. Delay is a live timing measurement. H1-answer (next-open → +1 m / +5 m, then +15 m appendix) is a
  non-overlapping diagnostic only. Confirmation 2023–2026 Powell only for P&L language.
  **[A-02, A-03, A-09, A-10, A-11]**: τ dated at the anchored upper bound; exit, sign, statistic and alpha
  clarified; residualisation and score function frozen; ~~confirmation n = 27~~ **(r1)** confirmation n = the
  realised anchored count (20 of 27 today), published before any market join. **[A-23, A-37, A-38, A-40]** (r1):
  restricted wild bootstrap of the HC3 t; statement-dominance and in-presser-price checks; model-access contingency.

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
| H1-primary | Meeting-level mean(hawk(Q&A)) − hawk(statement); Q&A only; ZT; next 1m open after τ; residual position after 13:50–14:20; chair dummy | Only residual GO/NO-GO | A-01 (ZT = `ZT.v.0`), A-02 (τ upper bound; bins, margin; r1), A-03 (exit/sign/test, clarifying; sidedness r1), A-05 (clock source per meeting; r1), A-09 (residualisation; r1), A-10 (score spec, retyped clarifying; r1), A-11 (realised n, operating characteristics; r1), A-15 (validity diagnostic; r1), A-23 (restricted wild bootstrap; r1), A-37/A-38/A-39 (interpretation diagnostics; r1), A-40 (access contingency; r1), A-46 (interpretation labels; r1) |
| H1-answer | Next-open → +1m / +5m (then +15m appendix); non-overlapping; meeting cluster | Diagnostic only | A-22 (signal, sample, selection rule, inference; r1), A-21 (mid-quote extension; r1), A-18 (1s extension; r1) |
| BENCH-R | Sign(13:50–14:20) from 14:20 to presser-end; ZT; {2, 4} ticks/side; split at 2020 | Replication / regime check | A-04 (tick table), A-06 (era clocks, video-free exit, statistic, sidedness; r1), A-07 (USMPD QA, re-sequenced; r1), A-08 (non-blind), A-19 (hurdle table; BENCH-R-ES extension) |
| H1-Q | H1 + question hawkishness | Robustness (collider risk) | A-10, A-15 (questions are out of the classifier's domain) |
| H2/H3 | vocal_proxy / expression_proxy; prior-meeting same-chair z; Powell only; 4-meeting burn-in; variance floor; identity gate | Secondary; off for Warsh | A-31 (vocal_proxy spec), A-32 (identity, speech confound), A-33 (A/V skew), A-16 (ECAPA threshold; r1) |
| H4 | Combined vs text on 2023–2026 Powell after H1 frozen + code hash | Secondary | A-26 (training window, Clark-West), A-31 (valence excluded) |
| Lexicon | Frozen strategies/01 20+20 | Negative control | A-39 (r1: same statistic; fixed interpretation; read as a weak-measure comparison, not a null) |

Separately pre-registered extensions added by amendment (none can replace, rescue or be promoted over a locked
result): **H1-chrono** (A-14), **H1-run** (A-03), **BENCH-R-ES** (A-19), **H1-answer-1s** and **STMT-ABS** (A-18),
**H1-exec30** and **H1-exec-live** (A-20), **H1-answer-mid** (A-21); added in round 1: **H1-A** (A-37), **H1-PX**
and **PP-MKT** (A-38), placebos **P1/P3** (A-39), **H1-replica** (A-40), **H1-P** (prospective, A-41), **H1-post**
(A-08), **H1-primary-FC** (A-02) and the A-50 robustness rows. Diagnostics: **D-VAL** (A-15), **D-ASR** (A-16),
**D-DOM** and **D-DECOMP** (A-37), **D-VAL-W** (A-47). Every test has one tier in the register (section G).

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
with no anchor or an interval wider than 60 s goes to (C) only. **(r1)** The locked 30 s rule is kept as written,
read as a half-width (equivalent to width ≤ 60 s), applied to the anchor bin that contains τ, with a 30 s safety
margin added to τ; v0's "explicit change of the data-section threshold" is withdrawn.

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
→ join ZT **next 1m open after τ** **[A-01 `ZT.v.0`; A-03 exit; ~~A-07 USMPD QA gate before outcomes~~ (r1) A-07
statement-window QA after download, flags only, no clock edits; A-12 order: the H1-primary script is the first to read
any 2023-2026 bar after 14:20 ET; A-36 join on t_end_utc_hi, never on known_at]**
→ H1-primary + H1-answer diagnostic + BENCH-R (regime-split)

Live path: time ~~Fed/YouTube~~ **[A-17]** the federalreserve.gov live player (there is no YouTube live stream) vs
~~CME~~ an independent clock (NTP-queried local clock, first-word headlines, PROGRAM-DATE-TIME if present) on a held
presser; freeze delay = max(measured p90, 30 s); 60 s pessimistic appendix. If p90 > 60 s, kill live (G4/G5) and ship
measurement-only. Warsh live = half-size text **[A-17: notional/DV01 sizing on paper]**. Offline 1m tests do not
retune 5/15/30 s. **(r1) [A-17, A-42, A-43, A-44]** The paper-traded object is H1-primary (one entry per meeting,
after a live end-of-presser event); delay is measured as an upper bound against independent references; 2026-10-28
is measurement-only; presser-day runbook for the shared 5090.

### 6. Evaluation and power

n ≈ 75 presser meetings inside the 88-meeting archive, not 2,000 iid answers and not n=88. **[A-11]** Confirmation
n = 27 **(r1: realised anchored n, 20 today)**. Underpowered for small H2/H3. ~~Block bootstrap + wild cluster.~~
**[A-23]** Decision p = ~~wild bootstrap~~ **(r1)** restricted wild bootstrap of the HC3 t (one observation per
meeting); companions reported. Holm not needed for a single primary; secondaries cannot be promoted after looking
**[~~A-26: Holm within the secondary family~~ (r1) section G: enumerated register, Tier 1 and Tier 2 Holm with m
fixed, Tier 3 descriptive]**.

Report (A) BENCH-R costed and (B) H1 non-executable separately.

### 7. Gates and calendar

| Gate | Go | No-go |
|---|---|---|
| G0 | ~~CPU ASR~~ **[A-27]** GPU (and CPU-agreement) ASR/alignment + RoBERTa on one Powell and 2026-09-16 Warsh | No video/ASR; **[A-28]** "no model access" recorded separately |
| G1 | get_cost under credit | Shrink window/symbols; ask before 1s |
| G2 | Event list; missingness vs VIX table **[A-05: missingness = caption, alignment and anchor quality; A-07: USMPD QA gate]** | Crisis MNAR + imputed video |
| G3 | H1-primary on confirmation sample **[A-03, A-11: ~~one-sided~~ alpha 0.05 (r1: sidedness ratified, default two-sided), ~~wild bootstrap~~ restricted wild bootstrap of HC3 t (A-23 r1); false-GO rate and power of that exact procedure published first at the realised n; ~~A-15 measurement gate~~ A-15/A-46 labels attach to the verdict and never flip it; A-40: run once, from the frozen hash, only with verified official weights]** | Stop; do not mine H2 **(r1, A-43: all live events measurement-only)** |
| G4 | H2/H3 variance/identity gates on Powell | Ship text-only |
| G5 | Paper-trade text, half-size on Warsh, only if live p90 delay ≤ 60 s **[A-17, ~~A-25~~ A-43: operational pass criteria only; (r1) delay = upper bound vs an independent reference; the H1-primary entry lag is reported beside the locked per-answer p90; counted only after a G3 GO and never on 2026-10-28]** | Kill live; measurement-only |

Remaining pressers: 2026-10-28, 2026-12-09; 2027-01-27, 03-17, 04-28, 06-09, 07-28, 09-15, 10-27, 12-08. **[A-34]**
2027 dates and presser flags are provisional (six-meetings-a-year proposal in the July 2026 minutes); refresh after
each meeting.

### 8. Licenses and ethics

Disclose CC BY-NC (FOMC-RoBERTa, audeering). Loughran academic. pyannote gated. OpenFace/LibreFace research-only —
not the public demo. Do not claim to read Warsh's feelings. Features are proxies. **[A-30]** EmotiEffLib and
InsightFace weights are non-commercial in effect; chrono-bert fine-tunes inherit CC BY-NC from the labels. **[A-02]**
TV-archive captions: store derived offsets only. **[A-27]** HiPerGator storage is for research and educational data
only; use it under the sponsor group's allocation and with the sponsor's agreement. **(r1) [A-48]** UF Policy 12-002
(amended 2026-03-24) bars UF IT resources for "personal financial or other gain": HiPerGator serves the research arm
only, after written sponsor confirmation; nothing that feeds a paper or real-money trade runs there. **[A-43]** The
real-money event count is kept per scorer, and only a scorer with a permissive licence path can support real money;
"paper trading unaffected" (A-30) is an UNVERIFIED legal reading.

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
contract and with early timestamps. **(r1)** The Fed MP4 lacks the last chair answer at several meetings
(20240131, 20240918; 7 confirmation meetings have ≥ 10 s of caption chair speech after the MP4 end), the TV anchor
covered only the first 30 presser minutes, and the anchor's upper-bound property rests on the archive time base
(A-02, A-05).

Added in round 1:

7. **The locked signal may be a statement-level variable.** Human ratings (2011-2019) and a lexicon proxy (2023-2026)
   both say the statement term carries most of the variance of s (corr(s, −S) = 0.98 on the lexicon proxy,
   `plan/checks_r1_econ/r1_econ_checks.out` s1). A GO could then be a statement-tone or policy-cycle association,
   and post-presser drift can also load on the in-presser price move. A-37/A-38 add diagnostics and fixed labels.
8. **Model access.** FOMC-RoBERTa is gated with manual approval; without verified official weights H1-primary is
   postponed, not replaced (A-40). Its weights were last modified on 2023-09-12, inside the confirmation window.
9. **No blind confirmation.** 2023-2026 presser-window moves have been seen and overlap the first 25% of the H1
   outcome window (A-08); only post-freeze events (A-41) are fully blind, and they are all Warsh events.

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
- **Added (r1):** install ffmpeg on the 5090 host (absent today); ask the sponsor for written confirmation that this
  is UF research with academic outputs before any HiPerGator job (A-48); run `showQos jie.xu`; add the per-user
  2-GPU pre-submit guard (A-48); start blind D-VAL-W labelling (A-47); ask the user once about OpenTimestamps digests
  and a standing presser-day bbo-1s cap (A-17)

**Pre-freeze block (2026-10-07..09), moved ahead of any market download (A-12, A-14):**

- Team ratifies A-03 (exit, sign, statistic) in writing, dated
- Write PREREG_H1.md: family, all amendments in section F, H1-chrono / H1-run / BENCH-R-ES / extension rows, D-VAL,
  D-ASR, prior-exposure section (A-08), instrument map, anchor list and dropped list, thresholds, model shas, lock
  file, Databento request parameters, tick/cost table, statistics and decision rules; SHA-256 manifest; timestamp the
  hash (publication only with user approval)
- Run D-VAL (text-only) before any market join **(r1: after the PREREG timestamp; its result cannot change A-10)**
- **Added (r1), all outcome-free and on the local 5090 (A-48 keeps HiPerGator off this path):** aligner on all
  2016+ MP4s; MP4-completeness check and the 120 s tail check of 20240131 / 20240918 (A-05); aligner-timeline TV
  anchors with 14:00 and 15:00 ET items, 10-minute bins and the drift gate (A-02); frozen clock_source per meeting;
  realised (P) n, dropped list and simulated operating characteristics of the A-23 procedure (A-11); reproduction of
  the published labels on 63 pressers (A-10, A-40); D-DOM (A-37); concurrent-news flag list (A-50); topic lexicon
  (A-50); provenance table (A-08); test register (section G); run the smoke meetings twice (A-49)
- **Added (r1):** if verified official FOMC-RoBERTa weights are not in hand by 2026-10-14, H1-primary is postponed
  (A-40); the freeze and the 1m download then slip together, never a partial freeze

**Days 3–7 (2026-10-12..16)**

- Download 1m windows if quote OK
- Align all available presser PDFs; ~~drop high-mismatch meetings~~ apply the frozen alignment and anchor rules
  (A-02, A-05)
- **(r1)** Statement-window QA script, flags only, hashed QA addendum before any outcome script (A-07)
- ~~Freeze code hash;~~ (frozen in the pre-freeze block) run H1-primary on 2016–2022 (contaminated) and 2023–2026
  Powell; run H1-chrono as registered **(r1: the H1-primary 2023-2026 script runs first, once, from the frozen hash;
  then the Tier 1-3 rows of section G)**
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
- ~~**Added (A-35):** if G3 has not passed with a frozen hash by 2026-10-21, 2026-10-28 is measurement-only and
  2026-12-09 is the first counted paper trade~~ **(r1, A-35/A-43)** 2026-10-28 is measurement-only in every case
  (capture, PDT check, stream lag, end-event detection, shadow decisions). The first counted paper trade is the first
  presser after both a G3 GO and 2026-10-28 (2026-12-09 at the earliest). After a G3 NO-GO no paper trade is counted.
- **(r1)** Rehearse the 2026-09-16 replay under the A-44 presser-day runbook; file D-VAL-W results and H1-P before
  2026-10-28 (A-41, A-47)

Do not do in two weeks: Qwen-Omni on 88 videos **[A-27: excluded for validity and look-ahead, no longer for
compute]**; pyannote if ungated terms unsigned; OpenFace demo; 1s bars **[unless the user approves A-18]**; Warsh
face/voice trading; reviving daily TLT lexicon.

---

## F. Amendments (dated 2026-10-03)

All amendments below are dated 2026-10-03 and were written before any H1-primary, H1-answer or BENCH-R number on
Databento data exists. Extensions are pre-registered separately and must be included in the timestamped manifest
(A-12) before their data are joined to outcomes. "Needs user approval" items are not executed until the user approves
in person. Amendments marked **(revised r1)** were changed in review round 1 on the same day; v0's text is in
`merged_plan_v0.md` and the reasons are in section H. None of the v0 amendments had been timestamped, so revising them
changes no registered record.

Round-1 evidence lives in `plan/checks_r1_stats/`, `plan/checks_r1_execution/`, `plan/checks_r1_data_eng/`,
`plan/checks_r1_validity/` and `plan/checks_r1_econ/` (scripts next to their outputs).

### F.1 Corrections

**A-01 Primary rates instrument (correction; test revised r1).** Replace `ZT.c.0` with `ZT.v.0`; robustness `ZF.v.0`,
`ZN.v.0`, `ES.v.0`. Databento's volume rule ranks contracts by the previous day's volume, so it has no look-ahead
(https://databento.com/docs/standards-and-conventions/symbology). Evidence: on 42 of 73 scheduled presser days
2016-2026 (all Mar/Jun/Sep/Dec meetings; 13 of 13 SEP days in 2023-2026) `ZT.c.0` is the delivery-month contract with
0-50 traded seconds in 14:00-15:30 ET against 497-4,058 for `ZT.v.0` (`plan/checks_gap_exec/roll_mapping_output.txt`;
`plan/evidence/gap_data/liq_trades.csv`; `plan/checks/gap_stats_symbology.out`). `ES.c.0` differs from `ES.v.0` on
28 of 73 days. Implementation: freeze `symbology.resolve` output (instrument_id, raw symbol) per presser day into the
manifest. ~~Unit test that the event-day contract equals the highest-volume contract on day -1~~ **(r1)** That test is
a tautology for `.v.0`. Replace it with an event-afternoon check from free `get_record_count`: trades(`.v.0`) ≥ 2 ×
trades(`.v.1`) between the statement-window start and the exit, frozen per meeting; a failure is flagged before
outcomes and handled only by the A-07 instrument rule. No failure exists today: on all 58 quarterly-month presser days
2011-2026 ZT `.v.1` never exceeds 50% of `.v.0`; ES `.v.1/.v.0` trade ratios are 0.15-0.31 on the five closest
roll-week days (`plan/checks_r1_execution/roll_week_and_bbo_density_output.txt`, `es_roll_trades_output.txt`). Flag
(before outcomes) any meeting whose window has fewer traded 1m bars than an era-relative floor (2016-2018 `ZT.v.0` has
106-120 of 120 minutes traded in 14:00-16:00, `plan/checks_gap_exec/zt_minute_coverage_output.txt`), floor fixed in
PREREG_H1.md. Paper-trade contracts named now: ZTZ6 on 2026-10-28, ZTH7 on 2026-12-09. The hypothesis instrument is
still "front ZT".

**A-04 Tick table and fees (correction).** ZT $15.625 per tick through 2019-01-11 and $7.8125 from 2019-01-14 (CME
SER-8171, https://www.cmegroup.com/notices/ser/2019/01/SER-8171.html; 1/256 prints first appear on 2019-01-14,
`plan/checks_gap_exec/tick_size_output.txt`); ZF $7.8125, ZN $15.625, ES $12.50. Add an all-in fee of $2.00 per side
per contract (UNVERIFIED; replace with the broker's schedule). The locked stress stays {2, 4} ticks/side in each era's
tick; report ticks, dollars per contract and bp of window sd.

**A-24 Cost realism and decay (correction, revised r1).** Net tables (gross, {2, 4} ticks/side plus fees, ex-2022)
only for BENCH-R and BENCH-R-ES. ~~Yearly gross and net tables plus ex-2022 net for BENCH-R and H1~~ **(r1)** H1
yearly tables are gross, with a cost-hurdle line in bp of window sd and no net P&L or Sharpe (locked: "No net Sharpe
on H1"; section A.6 "(B) H1 non-executable"). A separate 2024-10..2026-10 decay check. Stated prior from our studies:
costed rates results above a few bp per event are not expected (ES pre-FOMC +22.8 bp, t 2.78 after 2015 vs −2.3 bp in
2024-26, `<scratch>/intraday_study/fomc_and_hourly_trend/out_fomc/run_log.txt`; auction ZN rule net Sharpe −0.22 at
1.0 bp/side, `<scratch>/auction/verify/verify_extra.json`; strategy 01 2022 Sharpe 1.19 vs 0.065 otherwise,
`<scratch>/fedspeak/replicate/results.json`). No pre-statement leg.

**A-30 Licence and model-role corrections (correction; r1 note).** CentralBankRoBERTa detects whether a sentence is
positive or negative for households, firms, the financial sector or the government (HF card, fetched 2026-10-03): it
is agent sentiment, so it is dropped as stance cross-check and as "demo-legal fallback".
`gtfintechlab/model_WCB_stance_label` is gated with conflicting licence metadata and trained on Fed text through 2024.
EmotiEffLib weights are trained on AffectNet (non-commercial); InsightFace buffalo_l weights are non-commercial. A
permissive, uncontaminated stance path needs the team's own blind labels. Recommendation for the user's decision (not
a new rule): no real-money step until such a path exists. ~~Research and paper trading are unaffected.~~ **(r1)**
Research is unaffected. Whether paper trading that builds the evidence for a real-money decision is "directed towards
commercial advantage" under CC BY-NC 4.0 s1(i) is an UNVERIFIED legal reading; A-43 keeps the real-money count per
scorer for that reason.

### F.2 Clarifying amendments (team must ratify, dated, before any H1 number)

**A-03 H1-primary horizon, sign and test (revised r1).** The locked text gives an entry but no exit; with a
meeting-level mean, τ is the end of the last chair answer, which coincides with video end (median gap to the last
caption cue 0 s, `plan/checks_gap_exec/presser_tail_output.txt`; **r1:** measured on the last caption cue, not the MP4
end, see A-05), so "τ → presser end" is empty, and ZT's 15:00 ET settlement precedes the last answer in 98% of
meetings (`plan/checks/gap_stats_checks.out` s4; **r1:** all 27 Powell confirmation pressers, but not 1 of the 3
Warsh pressers, `plan/checks_r1_validity/r1_counts_timing_power.out`). Proposed reading, which keeps "meeting-level
mean" literally:

- τ = ~~anchored upper bound (A-02) of the end of the last chair answer~~ **(r1)** τ_used of A-02 (bin upper bound
  plus margin) for the end of the last chair answer, on the clock source frozen by A-05.
- Entry = open of the first `ZT.v.0` 1m bar with ts_event ≥ τ_used. Exit = close of the last 1m bar before 16:00 ET
  (the 15:59 bar). Line 173's "16:00 ET is equity-only robustness" is amended accordingly; ES uses the same exit.
- Sign: continuation means a hawkish residual surprise predicts a fall in ZT. ~~(one-sided)~~ **(r1) Sidedness.**
  The plan's own residual risk 2 says the sign "is not a 2016–2026 constant", USMPD statement-to-presser correlations
  are −0.07 (SPFUT) and −0.06 (UST2Y) in 2020-26 (A-08), and Narain-Sangani report reversal after March 2022
  (`<scratch>/fedtalk/literature/narain.txt` near line 925). Recommendation: two-sided alpha 0.05 with the direction
  reported. Default if the team has not ratified by the freeze: two-sided. If the team chooses one-sided continuation,
  PREREG_H1.md records that a reversal edge is untestable in this family and no later sign flip is allowed. Power at
  n = 27: two-sided 0.17 / 0.33 at r = 0.2 / 0.3 (MDE 0.517) vs one-sided 0.26 / 0.45 (MDE 0.468); at n = 20:
  two-sided 0.13 / 0.25, one-sided 0.21 / 0.36 (`plan/checks_r1_econ/r1_econ_checks.out` s4).
- Statistic: ~~OLS slope of the meeting exit return on the residual surprise (A-09); p-value by wild bootstrap
  (A-23)~~ **(r1)** HC3 t of the surprise coefficient in exit return ~ 1 + s + R_stmt (A-09); decision p by the
  restricted wild bootstrap of A-23. G3 GO at alpha = 0.05 (sidedness as ratified) with the A-11 operating
  characteristics of this exact procedure published first.
- Next-day 15:00 ET settlement exit is robustness only.

**H1-run (separately pre-registered extension; revised r1).** Running mean: at each answer end τ_k, s_k = cumulative
mean hawk over the qualifying chair Q&A sentences of answers 1..k (the A-10 aggregation) − hawk(statement),
residualised as s̃_k = s_k − (â + b̂·R_stmt) with â, b̂ from the meeting-level regression of s on R_stmt in the same
sample; hold p_k = −s̃_k (times the ratified sign) from the first open after τ_k to the first open after τ_{k+1}.
~~flat at the H1-primary exit~~ **(r1)** Y_m = Σ over k < K of p_k·r_k, flat at the first open after τ_K, so H1-run
tests only intra-presser updating and its last leg is not the H1-primary trade (v0's last leg reproduced the H1-primary
position and about half of all H1-run holding time). The overlap-inclusive version is Tier 3. Test: mean(Y_m) = 0,
studentised sign-flip (restricted wild) bootstrap, sidedness as A-03; Tier 2 (section G). Sample: confirmation
meetings that pass the A-02 gates in every answer's bin. Costs reported per chair (about 12 netted round trips per
Powell presser, `plan/evidence_it1_execution/extra_output.txt`; fewer for Warsh, 15-21 answers). Cannot be promoted.

**A-10 Score function (retyped r1: clarifying amendment, ratified with A-03).** v0 called this an implementation
detail; it fixes the measured construct, so the team ratifies it with a date. One spec, committed with the code hash
before any market join. **(r1) Primary (default if not ratified by the freeze), chosen from training-domain fit and
not from any result:** a TDW-faithful pipeline. Pinned `nltk.sent_tokenize` (version pinned); chair Q&A sentences
without "?"; the TDW A1/B1 dictionary filter applied to both the Q&A and the statement; the TDW clause split
(but / however / even though / although / while / ";" with a keyword on each side); max_length 256 tokens with the
tail truncated and the count logged; sentence score = softmax P(hawkish) − P(dovish) with the label map read from the
model config and verified against the published labels (fallback LABEL_0 dovish, LABEL_1 hawkish, LABEL_2 neutral).
**Aggregation (r1):** meeting Q&A score = mean over all qualifying chair Q&A sentences of the meeting (sentence-pooled,
as in the authors' `code_market_analysis/aggregate_measure.py`); statement score = mean over qualifying statement
sentences; s = difference. Answers with no qualifying sentence contribute nothing; per-meeting counts are logged and a
meeting with fewer than 10 qualifying Q&A or 3 qualifying statement sentences is flagged (never dropped; Tier 3
sensitivity without flagged meetings). Robustness (Tier 3): the unfiltered version (v0's proposal: all chair Q&A
sentences of ≥ 4 words), the answer-weighted mean of answer means, and the argmax-count measure.
FOMC-RoBERTa revision aa3bc4281fb1fe73c8872e09ad5c64b898f90d83 (subject to A-40).

Why (r1): FOMC-RoBERTa was trained only on filtered, clause-split sentences (TDW s3.1,
`<scratch>/fedtalk/literature/tdw.txt` l.115-126 and 211-230; `fomc_communication` has 2,480 rows, the after-split
total, `plan/checks_gap_models/gap_models_ds3.out`). The filter passes 0.50-0.77 of statement sentences
(`plan/checks_r1_validity/stmt_filter_share.out`) but only 0.14-0.32 (median 0.20) of chair Q&A sentences
(`plan/checks_r1_validity/warsh_vocab.out`; `plan/checks_gap_models/gap_models_filter.out`). Unfiltered, about 80% of
the Q&A term would be out of domain against about 30% of the statement term, shrinking the Q&A term towards zero and
making s mostly −hawk(statement). The aggregation follows the authors' measure; v0's answer-weighted reading would be
unstable when most answers have 0-2 qualifying sentences.

Before any market join, with no outcomes: (a) reproduce the repository's published labels and scores for 63
pressers 2011-04-27..2022-09-21 (github.com/gtfintechlab/fomc-hawkish-dovish, `labeled_*presconf*_select_filtered`,
`plan/checks_r1_validity/tdw_repo_check.out`): argmax agreement ≥ 0.98 and max |Δ published score| ≤ 0.01, which
verifies revision, tokenizer and label map; (b) D-DOM (A-37). Same function for H1-Q question sentences (out of domain;
A-15).

### F.3 Implementation details (do not change any locked hypothesis)

**A-02 Wall-clock anchor protocol (revised r1).**

1. *Sources.* Bloomberg first-word headline times if terminal access and its academic terms are confirmed
   (unverified today; A-48), else TV News Archive caption segments: the 14:00 ET item (CNBC Power Lunch) and
   **(r1)** the 15:00 ET items (CNBC Closing Bell, then FBC Claman Countdown; FBC or Bloomberg TV as alternates). v0's
   builder kept only items starting 0-7200 s before the presser (`plan/evidence/gap_data/tv_anchor.py`), so it
   anchored only presser minutes 0-30; a median 42% of each video lies after 15:00 ET
   (`plan/checks_r1_data_eng/tvcov_output.txt`).
2. *Same clock as τ (r1).* Anchors are matched against the media timeline that τ uses, i.e. the aligner word timeline
   of A-05 for every 2016+ meeting, captioned or not, with VTT times mapped onto it where A-05 selects VTT. v0's
   VTT-relative offsets become diagnostics. This lets uncaptioned meetings be anchored and stops a VTT-relative offset
   being applied to aligner times (v0 would have dated τ about 110-146 s early at 20230201, whose VTT timeline is
   broken; `plan/evidence/gap_data/tv_stats.out`).
3. *Bins (r1).* Offset intervals in 10-minute media bins; per matched cue lo = seg0 − LAG − conv, hi = seg0 + 60 −
   conv (the `tv_anchor.py` convention), intersected within the bin. The bin containing τ is used (for H1-answer and
   H1-run, each answer's bin). Observed drift justifies this: 20251029 shifts in its final ~10 minutes and 20240918 has
   a local +27 s excursion in minutes 20-30 (`plan/checks_r1_data_eng/tvlate_output.txt`).
4. *τ_used (r1)* = τ_media + scheduled-zero conversion + hi(τ bin) + M, with a fixed safety margin **M = 30 s** for
   archive time-base error ε. Clock error can only add delay, conditional on ε ≤ M. The cost is small against a 22-60
   minute hold (`plan/checks_r1_execution/post_presser_hold_output.txt`).
5. *Drop rule (r1: the locked text, read literally).* "Start uncertainty" = half-width of the τ-bin interval. A
   meeting goes to (C) only if: half-width > 30 s (width > 60 s); no valid anchor in the τ bin; fewer than 5 matched
   cues within 15 minutes of τ; or the drift gate fires (hi of the first bin and hi of the τ bin differ by > 10 s).
   This withdraws v0's "explicit change of the data-section threshold": the locked 30 s read as a half-width equals
   v0's 60 s width (median width 36.7 s). The dropped list, the realised (P) n and its composition are frozen in
   PREREG_H1.md before any market join (A-11).
6. *H1-primary-FC (Tier 3 sensitivity, r1).* Meetings dropped under (5) that still have a valid media τ get τ_used =
   τ_media + scheduled-zero conversion + 180 s + M (the largest observed upper bound is +121.4 s, 20260429; p95
   +70.5 s; `plan/evidence/gap_data/tv_anchor.csv`), flagged `clock_source=fallback_constant`. Reported beside the
   locked row; never decides G3; excluded from H1-answer and H1-run.
7. *ε calibration (r1).* LAG enters only lo, so the v0 LAG sensitivity cannot detect an early archive start time;
   it is kept only for its effect on the drop list. Estimate ε from NTP-logged cable recordings of both the 14:00 and
   15:00 ET items on 2026-10-28 and 2026-12-09 (A-17, relative to reference R with allowance L_ref) and from a
   historical one-sided check (the 14:00:00 statement headline inside the 2016-2018 two-hour Power Lunch items). Report
   now the share of meetings whose entry bar changes at ε = M + 15 s and M + 30 s. Pre-declared consequence: if the
   calibrated ε exceeds M, H1-primary is re-run with τ_used + (ε − M) as a registered sensitivity and the G3 verdict is
   reported both ways; if they differ in sign, or one is significant and the other not, the A-46 label "not robust to
   clock" attaches. G3 is not re-decided.
8. Never set offsets from market data; market cross-correlation is a diagnostic only.
9. Store derived numbers only (archive downloads are restricted), but keep per-cue match tables without caption text
   (media time, item id, segment offset, trigram count, page SHA-256 and retrieval time) so anchors can be rebuilt
   and audited (A-49).
10. Gorodnichenko answer times (video marks + scheduled 14:15/14:30) are used only to cross-check 2016-2019
    segmentation and flag broken caption files (2019-05-01: −173 s, `plan/evidence/it1_data_eng/gpt_vs_vtt.csv`),
    never as a wall-clock.

**A-05 Captions, re-timing and clock source per meeting (revised r1).**

- *Aligner (r1).* Primary: CTC forced alignment with `jonatasgrosman/wav2vec2-large-xlsr-53-english` (Apache-2.0,
  revision 569a623, the WhisperX English default) through WhisperX 3.8.6, pinned. ~~Qwen3-ForcedAligner-0.6B or
  WhisperX~~ Qwen3-ForcedAligner-0.6B builds on the Qwen3-Omni foundation model, has no stated training data and takes
  at most 5 minutes of audio (model card); it is a cross-check outside the primary path, consistent with "No LLM in the
  primary path" and A-27. Any capped aligner uses ≤ 5 min windows with fixed overlap and boundary tie-break. Full PDF
  text (chair and reporters) aligned to the MP4 audio; numerals written as words; version, dtype and outputs hashed.
- *MP4 completeness (r1).* The Fed MP4/HLS ends before the last chair answer at 20240131 (video end 2968.7 s, last
  chair label 2988.1 s, answer to ~3039 s) and 20240918 (2985.7 s vs 2988.9 s, to ~3021 s); the HLS sum equals the
  MP4 duration, so no complete rendition exists, and Brightcove `updated_at` is 9-26 days after each event
  (`plan/checks_r1_data_eng/vtt_tail_output.txt`, `hls_output.txt`). Caption cues after the MP4 end match the CNBC
  15:00 ET captions with the same offset as earlier in the presser, so the answer aired live and the VTT is on wall
  time (`tv_after_video_end_output.txt`). 29 of 68 captioned 2016+ pressers have caption chair speech after the MP4
  end, ≥ 10 s on 13, of which 7 are confirmation meetings: 20230201, 20230920, 20240131, 20240918, 20241107, 20250319,
  20251029 (`vtt_tail_all_output.txt`). A forced aligner fed the full text would squeeze the missing answer into the
  last audio seconds and date τ about 70 s (20240131) and 35 s (20240918) early, more than the anchor half-width.
- *Clock-source rule, frozen per meeting before any market join (r1).*
  (a) MP4 complete (aligner coverage of the last chair answer ≥ 90% and its last word ≥ 1 s before the MP4 end) and
  aligner QA passes → `clock_source = aligner`.
  (b) MP4 truncated at the last answer and a VTT exists → fit VTT to aligner word times on the overlap (robust linear
  fit, residual ≤ 1 s); `clock_source = vtt_mapped`; τ from the mapped VTT, valid only if the 15:00-item TV offset of
  the cues around τ agrees with the τ-bin anchor within 5 s.
  (c) Otherwise → (C) only.
  Unit test: a meeting where both paths are valid and τ_wall differs by > 2 s fails the build.
- *Checks before the freeze (r1).* Extract the final 120 s of audio of the 20240131 and 20240918 MP4s and confirm the
  last answer is absent; run the completeness check on the 7 uncaptioned meetings (20221214, 20230614, 20230726,
  20231101, 20231213, 20240320, 20251210, `<scratch>/fedtalk/data_markets/vtt_summary.csv`).
- Segment Q&A with caption speaker labels plus PDF text. Measure aligner boundary error against about 10 good VTT files
  first (median, p95). Flag meetings where VTT, aligner and (2016-2019) Gorodnichenko times disagree by more than 2 s.
  Replace "drop bad WER-proxy meetings" with an alignment confidence/coverage threshold fixed in PREREG_H1.md.
- G2 missingness table on caption, alignment, anchor quality and **(r1)** "MP4 contains all chair answer text"
  (replacing v0's "video available 95 of 95"); MNAR check on outcome-free covariates only (year, SEP, answer count).

**A-06 Event clocks, windows and BENCH-R scope (revised r1).** Windows relative to each event's release time from the
event table (`hpg/manifest/pressers.csv`, which agrees with USMPD on all 95 rows): statement window = release −10/+20
min. Extend the Databento pull to the 20 pressers of 2011-2015 (12:00-16:30 ET in 2011-2012), which implements the
locked "2011–19 vs 2020–26". Exclude 2020-03-03 and 2020-03-15 from the H1-primary and BENCH-R main tests (dated rule;
reported separately). Split at 2020-01-01 as the locked text says; reassigning Jan 2020 is a sensitivity. Times
converted with tz-aware America/New_York; "next 1m open after t" = first bar with ts_event ≥ t (ts_event is bar
start; empty minutes are skipped and logged).

- *Entry (r1).* First 1m open at or after 14:20 ET in every era, the locked clock. In 2011-2012 the statement came at
  about 12:30, the economic projections with the dots at 14:00 and the briefing at 14:15
  (https://www.federalreserve.gov/newsevents/pressreleases/monetary20121212b.htm); v0's "release + 20" entry (12:50)
  put the SEP release inside the hold for all 8 pressers. Signal = statement window (12:20-12:50 in 2011-2012).
  Sensitivity excluding 2011-2012.
- *Exit (r1).* ~~Anchored upper bound of the end of the last chair answer; fallback the USMPD presser-window end~~ One
  video-free rule for every era: open of the first 1m bar at or after scheduled presser start + 60 min (the USMPD
  presser-window end; for 14:30 pressers 15:30 ET). It restores the team's iteration-4 "14:20, no ASR" design, matches
  the A-19 hurdle window and the A-07 benchmark window, and avoids two exit rules that differ by era and caption
  availability. The anchored last-answer-end exit is a Tier 3 sensitivity on the anchored subset.
- *Statistic and sidedness (r1).* Per regime: mean of sign(R_stmt)·R_hold in ZT ticks, gross and at {2, 4}
  ticks/side plus fees, with the slope as companion. 2011-19: one-sided continuation. 2020-26 and the break (difference
  of regime means): two-sided. Restricted wild bootstrap (A-23). Tier 1 Holm m = 3, labelled non-blind (section G).
- *Sub-tick events (r1).* sign(0) = no trade; report the effective n after sign(0) per regime and the share of
  |R_stmt| < 1 ZT tick: 12.5% of 2011-19 events and 18.9% of 2020-26 on USMPD UST2Y with DV01 about $38
  (`plan/checks_r1_execution/benchr_tick_resolution_output.txt`); 44% in 2020-01..2022-02
  (`plan/checks_r1_econ/r1_econ_checks.out` s5). On trade prices a sub-tick sign is bid-ask bounce, which pulls the
  2020-26 mean towards zero, the direction of a "break". Registered variants (Tier 3): as-of bbo mid sign with a 1-tick
  deadband (after A-13 approval); the break without sub-tick events; `ZF.v.0`; three descriptive periods 2011-19,
  2020-01..2022-02, 2022-03..2026. The write-up attributes no cause to a break: chair change (2018-02), COVID, the
  lower bound, the ZT tick cut (2019-01-14) and the Gómez-Cram & Grotteria publication (2022) are not separately
  identified. BENCH-R power recomputed on the effective n (about 35 of 40 pre-2020) and published with A-11.

**A-07 USMPD as event table and data-QA benchmark (revised r1: re-sequenced).** Build and validate the event list
against USMPD (https://www.frbsf.org/wp-content/uploads/USMPD.xlsx, updated 2026-09-17). ~~Before outcomes: corr over
statement and presser windows ... must exceed 0.8 ... fix flagged meetings (roll or clock) before the freeze~~ v0's
gate needed outcome-window prices before the freeze (A-12), allowed clock edits from market data (A-02(8) forbids
them), used a USMPD presser window (14:20-15:30) that overlaps the H1 outcome window (median 9.6 of 38.6 min,
`plan/checks_r1_econ/r1_econ_checks.out` s3), and was mis-signed (price vs yield correlates near −0.9). Order now:

1. PREREG_H1.md is timestamped first, with the QA rule written as corr(ZT log return, −ΔUST2Y) ≥ 0.8 on USMPD-identical
   statement windows (13:50-14:20; 2011-2012 12:20-12:50).
2. Before the freeze, outcome-free only: event dates and times vs USMPD; instrument identity from definitions and the
   A-01 record-count check; bar-count coverage from free record counts (counts, not returns).
3. After the download, a frozen QA script loads statement windows only and writes flags only. Flag a meeting when
   abs(ΔUST2Y) > 2 bp and ZT moves the wrong way or less than 25% of the implied move.
4. Allowed fixes: instrument or roll by rule (instrument_id not the day −1 volume leader, or the A-01 check fails, or
   below the bar-count floor) and vendor gaps. A clock is never changed from market data. A flagged meeting without an
   instrument error stays in, flagged, with a Tier 3 sensitivity that excludes flagged meetings.
5. Fixes go into a dated, hashed QA addendum written before any outcome script runs; outcome scripts read only hashed
   inputs.
6. Presser-window comparison with USMPD (USMPD-identical 14:20-15:30; 2011-2012 14:05-15:15) runs for 2011-2022
   before the H1 run (BENCH-R context only) and for 2023-2026 only after the H1-primary run, as a reported diagnostic.
   BENCH-R is reported on USMPD UST2Y next to the ZT version on the same windows.

**A-08 Prior-exposure disclosure (revised r1).** PREREG_H1.md lists what has been seen: USMPD statement-sign
correlations (SPFUT +0.41 2011-15, +0.46 2016-19, −0.07 2020-26; UST2Y −0.06 2020-26), 2023-2026 presser-window moves
and largest-move meetings (`plan/checks_it1_econ/usmpd_eras.py`; `<scratch>/fedtalk/data_markets/notes.md` s4).
**(r1) Added:** (i) the seen USMPD presser window ends at 15:30 and overlaps the first part of the H1 outcome window in
20 of 20 anchored confirmation meetings (median 9.6 of 38.6 min, 25%; `plan/checks_r1_econ/r1_econ_checks.out` s3),
listed by meeting; (ii) the pooled hourly FOMC-day profile for ES and ZN including the 15:00-16:00 ET event-day bar
(`<scratch>/intraday_study/fomc_and_hourly_trend/fomc_drift.py`); (iii) any fedspeak_v2 selection or validation
result seen before the H1 timestamp (v2 Amendment 2 scores press-conference answers with walk-forward chrono-bert), not
only its out-of-sample result; if v2 runs first, that is declared and its chrono checkpoints are hashed for reuse
(A-14). The H1 confirmation result is labelled "pre-registered after partial outcome exposure". A provenance table in
PREREG_H1.md gives the source of each numeric choice (pre-2023 literature, data quality, or "chosen after exposure").
Access rule, frozen now: no further presser-window or post-14:20 ET market statistic for 2023-2026 is computed until the
manifest hash is timestamped. **H1-post (Tier 3, r1):** entry at the first 1m open at or after max(τ_used, scheduled
start + 60 min), exit as A-03; the only segment of the outcome window no one has seen. BENCH-R is a non-blind
descriptive replication. The fedspeak_v2 out-of-sample result stays unopened until the H1 freeze is timestamped, or it
is declared if opened first.

**A-09 Residualisation (revised r1).** Test: the A-03 regression with R_stmt (13:50-14:20 `ZT.v.0` log return; era
window per A-06) as a control (Frisch-Waugh). The chair dummy is constant within the 2023-2026 Powell confirmation
sample and is dropped there; kept in pooled descriptives and in H1-chrono (A-14). ~~Any position, P&L or paper trade:
s̃ with a, b from an expanding window over prior meetings only (2016 start)~~ **(r1)** For any position, P&L or paper
trade: s̃ = s − (a + b·R_stmt) with a, b from an expanding window over prior meetings scored without contamination and
after the 2020 break only (FOMC-RoBERTa: 2023+), a = b = 0 until 8 such meetings exist; never full-sample or
leave-one-out. v0's 2016 start mixed contaminated 2016-2022 scores (A-29) and crossed the break BENCH-R tests. A
"trade-implied" statistic (t of the expanding out-of-sample s̃ P&L on the same meetings) is reported beside G3 and
labelled; G3 is decided on the A-03 regression. For Warsh paper trades, a is estimated from his prior pressers shrunk
to the 2023-2026 Powell estimate with a weight fixed in PREREG_H1.md. Position mapping: A-42.

**A-11 Confirmation sample size and G3 operating characteristics (revised r1).** ~~n = 27 (21 captioned)~~ The
confirmation pool is 27 Powell pressers (2023-02-01..2026-04-29); the decision n is the realised count that passes
A-02/A-05. With the v0 VTT-based anchors it is 20 (2023: 3 of 8, 2024: 7, 2025: 7, 2026: 3); not anchored: 20230201
(broken timeline) and the 6 uncaptioned 20230614, 20230726, 20231101, 20231213, 20240320, 20251210
(`plan/checks_r1_data_eng/anchor_eligibility_output.txt`; `plan/checks_r1_econ/r1_econ_checks.out` s3). The A-02
aligner-timeline anchors may recover some of them. Before any market join, publish in PREREG_H1.md: the realised n and
its per-year composition, the dropped list, the MNAR check on outcome-free covariates (year, SEP, chair answer count;
never outcomes by drop status), and the false-GO rate, power at r = 0.2 and 0.3 and MDE **of the exact A-23 procedure,
by simulation**, for the ratified sidedness, using the simulation design of `plan/checks_r1_stats/r1_boot_size.py`
(t4 noise, t3 surprises with leverage, the confirmation volatility profile; top 5 of 27 meetings carry 54% of the sum
of squares, Kish n_eff 9.9, `plan/checks/gap_stats_checks.out` s3). Reference values (Fisher z): n = 27 one-sided
0.26 / 0.45, MDE 0.47; n = 20 one-sided 0.21 / 0.36, MDE 0.54. PREREG states that a NO-GO at n of about 20 is
uninformative. NO-GO means "not detected"; report the 90% CI upper bound. P&L language always carries the p, the
sidedness and n.

**A-12 Pre-registration record (revised r1: sequencing).** PREREG_H1.md with a SHA-256 manifest of inputs (hypotheses
and every amendment here, event list, instrument map, anchor and dropped lists, clock_source per meeting, thresholds as
numbers, model revision shas and weight file hashes, package locks, aggregation code, Databento request parameters,
tick/cost table, statistics, sides, alpha, decision rules, the section G register, extension registrations, the
provenance table). Frozen before the 1m download. The QA rules are frozen, not their results (A-07). **(r1) Order of
outcome scripts:** the H1-primary 2023-2026 script is the first script to read any 2023-2026 bar after 14:20 ET;
BENCH-R 2020-26, H1-answer, the Tier 2/3 rows and the A-07 presser-window diagnostic for 2023-2026 run after it.
`research/` is git-ignored (`.gitignore` line 9), so the current "LOCKED" family has no commit or timestamp. Preferred:
timestamp the manifest hash only (OpenTimestamps, embargoed OSF or AsPredicted private). Committing with `git add -f`,
tagging or pushing to the public remote needs the user's approval. Every later amendment is dated and hashed the same
way.

**A-15 D-VAL (diagnostic; revised r1).** After the PREREG timestamp and before any H1 result, Spearman correlation
between the frozen A-10 scores and the human ratings in the Gorodnichenko-Pham-Talavera file
(`<scratch>/fedtalk/verify_literature/fomc_all.xlsx`: 692 answers, 68 statements, 36 pressers 2011-2019). **(r1)**
(1) Sign: the human `avr_score` runs from −10 (very hawkish) to +10 (very dovish)
(`<scratch>/fedtalk/literature/gpta.txt` l.478-479; 2011 statements average +6.0, 2018 −0.69,
`plan/checks_r1_stats/r1_misc.out` (d)), so ρ is computed between the hawk score and −avr_score, for answers,
statements and the meeting-level difference alike. Read literally, v0 would have failed a correct model. (2) Deciding
sample: 2011-2019 (meeting level n = 36; answer level 692); 2016-2019 reported only. (3) Rule: "measurement weak" if
the one-sided 95% Fisher-z lower bound of meeting-level ρ is below 0.1, or the meeting-cluster bootstrap lower bound of
answer-level ρ is below 0.1. The v0 point thresholds (0.4 / 0.3) are reported with their misclassification table (at
n = 36 a true ρ of 0.45 falls below 0.4 with probability 0.36, `r1_misc.out` (b)). (4) For FOMC-RoBERTa D-VAL is
in-sample (TDW covers 2011-2019 pressers): a pass is labelled "not falsified (in-sample)"; only a fail is informative.
H1-chrono is judged on its walk-forward scores. (5) The headline excludes answers containing any TDW training sentence,
matched on the unsplit `lab-manual-pc` train/test files (about 5 per presser; `fomc_communication` holds split clauses
and would undercount); the full set is reported beside it. (6) D-VAL cannot change A-10. If it fails, H1-primary still
runs and is reported with the A-46 label "measurement weak". No tuning on these labels; ratings were assigned after the
fact.

**A-16 Live text pipeline (revised r1: ECAPA).** Frozen before the first paper trade, on the local RTX 5090: ASR model
and precision, chunking, sentence split, chair isolation by ECAPA verification (`speechbrain/spkrec-ecapa-voxceleb`,
Apache-2.0). **(r1)** Voiceprints are enrolled from prior meetings only (Warsh: 2026-06-17 and 2026-07-29); the
verification threshold is a fixed number per chair set from prior meetings only (Powell: 2025 pressers; Warsh: the two
enrolment pressers), frozen in PREREG_H1.md and recorded in every done-marker. The same code path and threshold run
offline and live. The package default (`hpg/config.yaml` l.150-154: enrol from the same meeting's opening, threshold
null, calibrated per meeting from reporter turns) uses information unavailable live and is changed (A-36); the same
meeting's opening remarks are allowed only as a causal check. Non-chair voice embeddings are deleted after each run.
Paper-trade logs state that scores are ASR-derived. **D-ASR (separately pre-registered diagnostic; r1: out-of-sample
only):** replay archived audio through the live pipeline for Warsh 2026-09-16 and Powell 2026-01-28, 03-18 and 04-29
(none used for enrolment or thresholds); report meeting-level Spearman/ICC between PDF-text and ASR-text H1 signals,
share of non-chair speech admitted, end-to-end latency; the minimum agreement for using ASR text in paper trades is
fixed before results.

**A-17 Live delay and paper-trade protocol (revised r1).**

1. *Source and recording.* federalreserve.gov live player (Brightcove account 66043936001). **(r1)** Two independent
   recorders from 13:45 ET, each stamping NTP-corrected wall time: an HLS dump that saves the live master and media
   playlists (this records whether EXT-X-PROGRAM-DATE-TIME exists; the VOD has none,
   `<scratch>/fedtalk/data_markets/notes.md` s3), run as a CPU-only stream-copy process separate from GPU ASR; and OS
   loopback capture of the browser audio. A second machine if a teammate has one. No live Fed stream exists before
   2026-10-28 to test against (https://www.federalreserve.gov/live-broadcast.htm, fetched 2026-10-03), and VOD/MP4
   URLs are signed and expire after about 6 h (`hpg/manifest/README.md`).
2. *Clock.* Log the NTP offset by query only (for example ntplib or `w32tm /stripchart`) before and after; correct
   timestamps afterwards; no change to system time settings.
3. *Delay as an upper bound (r1).* Headlines, broadcast feeds and the later VOD are all downstream of the room, so
   delay measured against them is a lower bound. Use delay_upper = t_decision − t_ref + L_ref, where t_ref is the
   earliest arrival among independent references and L_ref is that reference's pre-stated latency allowance: live PDT
   encoder stamp +3 s; broadcast or cable captured with a tuner +10 s; first-word headline +30 s. With no reference,
   G5 cannot pass and live is measurement-only. Processing lag is reported separately. The A-02 ε is reported relative
   to reference R with allowance L_ref.
4. *Two latencies (r1).* (i) The locked per-answer p90 (G5 as locked) and (ii) the H1-primary entry lag = live end
   event E (A-42) + processing − true last-answer end from the hashed live recording. Both are reported; the counted
   paper trade uses (ii).
5. *Decision log (r1).* Tamper-evident log (code and model hashes, statement score, frozen a, b, σ and mapping of
   A-42, R_stmt window definition, timestamped decisions; "threshold" deleted, H1-primary has none), hashed locally
   before any market data timestamped after 14:20 ET that day is fetched. R_stmt and the position are computed
   deterministically the next day from as-of quotes at 13:49:59 and 14:19:59 (public at 14:20, before any entry after
   14:58 ET, so no look-ahead). A real-money version would need a real-time or 10-minute-delayed ZT quote before τ (not
   bought now). The user is asked once whether SHA-256 digests (only) may be submitted to OpenTimestamps after each
   presser; otherwise the log is labelled "self-attested". Emailing or pushing it needs the user's approval.
6. *Fills (r1).* Fill time = NTP-corrected wall time of the decision record + 1 s routing allowance; the measured
   delay is reported, never added (it is already inside the decision time). Prices from bbo-1s as-of quotes (A-21),
   crossing the spread, costs per A-04, cost = |p| × the per-contract cost. Needs the A-13 approval; the user is asked
   once for a standing cap (ZT+ES bbo-1s, ≤ $1 per presser day, 2026-10..12) or a fresh quote each day.
7. *Size.* A-42 mapping in ZT DV01 contract units, fractional on paper.
8. *Pass/fail* on operational criteria only (log complete, both latencies, pricing reproducible); P&L reported, not
   gated. Aborts only from a frozen list (stream failure, recorder failure, GPU or power event per A-44), timestamped;
   no discretionary kills.
9. Confirm each meeting has a presser on the Fed calendar; no presser, no event. BENCH-R decisions are logged too, as
   an operational check that needs no ASR.
10. Rehearse by replaying 2026-09-16 at 1x under the A-44 runbook before 2026-10-28; the VOD-zero calibration uses the
    hashed live recording, not a VOD that may later be trimmed.

**A-21 H1-answer-mid and bbo semantics (revised r1).** H1-answer (+1m/+5m) on bbo-1m or bbo-1s mids (cents; needs the
A-13 approval); trade-price version stays as locked; divergence reported by era. ~~A missing bar = first quote mid at
or after the target second~~ **(r1)** In Databento BBO records `ts_recv` is the end of the interval
(`databento_dbn` `_lib.pyi` line 3758), and records are sparse and era-dependent (ZT 15:00-16:00 ET: records on 51-71%
of seconds in 2016-2018, 104-112% in 2023-2026; `plan/checks_r1_execution/roll_week_and_bbo_density_output.txt`). The
quote state at instant t = the last record with ts_recv ≤ t, carried forward, flagged if older than 5 s (ZT) or 1 s
(ES); several records with one ts_recv → the last. The bbo-1m 15:59 exit is the record with ts_recv = 16:00:00 (the
OHLCV 15:59 bar is stamped 15:59:00). "First record after t" selects on movement and is allowed only as a labelled
delayed-fill variant. Before freezing the join code, check record multiplicity and timestamp monotonicity on one
purchased day (about $0.06, within the A-13 approval); unit tests with synthetic ohlcv and bbo records. A-13, A-17 and
A-18 use the same rule.

**A-22 H1-answer signal, sample, selection and inference (revised r1).** Signal = hawk(answer) − hawk(statement) with
the A-10 function, residualised as A-09; answers with no qualifying sentence are excluded. Sample = confirmation
meetings whose answer bins pass A-02 (never H1-primary-FC meetings). Sidedness as ratified for A-03. +1m is the
reported row; +5m and +15m descriptive. Greedy earliest-first non-overlapping selection over chair answers of ≥ 40
words, independently per horizon (retention 87% / 25% / 10% at +1m / +5m / +15m in 2023+); when several answers share
an entry bar, use the latest answer; restricted wild cluster bootstrap by meeting with Webb 6-point weights; results
also by clock source. Tier 3.

**A-23 Inference (revised r1: correction to the decision procedure; the hypothesis is unchanged).** v0 bootstrapped
the raw slope with unrestricted residuals. Simulated at n = 27 with the confirmation volatility profile, t4 noise, t3
surprises with leverage and the R_stmt control, the one-sided 5% empirical size is 0.126 for that procedure, 0.080 for
the restricted slope bootstrap, 0.061 for the unrestricted HC3 t, and 0.051 for the restricted HC3 t (WRE)
(`plan/checks_r1_stats/r1_boot_size.py`, `.out`). Now:

- Frozen statistic: HC3 t of the surprise coefficient in y ~ 1 + s + R_stmt (confirmation sample; chair dummy dropped
  per A-09).
- Decision p: restricted wild bootstrap (WRE). Fit the null model y ~ 1 + R_stmt; draw y* = fitted0 + e0·w with
  Rademacher w, 9,999 draws, seed fixed in PREREG_H1.md; refit the full model; one-sided p = share(t* ≥ t_obs) in the
  ratified direction, two-sided p = share(|t*| ≥ |t_obs|).
- The same restricted-t scheme for H1-chrono, H1-A, H1-PX, H1-replica, H1-post, BENCH-R and BENCH-R-ES; a studentised
  sign-flip version for mean tests (H1-run, BENCH-R regime means); the cluster version with Webb weights for H1-answer.
- Reported, not decisive: HC3 t with normal reference; Freedman-Lane permutation p (permute the residuals of y on
  R_stmt; v0's "meeting signals permuted" ignored the control); leave-one-out range with the most influential meeting
  named; the result without the two largest abs(ZT move) meetings; Kish n_eff.
- A-11 operating characteristics come from a simulation of exactly this procedure on the realised n.

**A-25 Paper-to-live stopping rule (replaced r1).** Replaced by A-43, which keeps v0's O'Brien-Fleming looks at 8/16/24 events and the 24-event minimum but defines which events count and studentises the boundaries.

**A-26 Secondary family (revised r1).** ~~Holm within the declared secondary family~~ The enumerated register in section G replaces this sentence. Unchanged: the 2022 split runs only on the 2016-2022 descriptive run; H4 trains combined weights on Powell 2018-2022 after the 4-meeting burn-in and tests on 2023-2026 with the Clark-West nested-model statistic.

**A-27 Compute (RTX 5090 + HiPerGator B200, at most 2 GPUs per session) (revised r1).**

- *Local:* RTX 5090 32 GB. Reference platform for every frozen table (alignment, anchors, scores; A-49) and the whole
  live/paper-trade path. The card is shared with the local LLM stack and has a 12VHPWR guard that can throttle or shut
  down the PC; presser days follow A-44.
- *HiPerGator:* partition `hpg-b200`, GRES `gpu:b200:N` with **N ≤ 2 (the user's rule), counted per user across all
  running and pending jobs, not per job (r1, A-48)**, B200 180 GB, 14 CPU cores per GPU, investment QOS `jie.xu` (no
  GPU burst QOS; `jie.xu-b` for CPU-only stages), always set `--time/--cpus-per-task/--mem` (default walltime 10 min),
  job arrays throttled `%2`, caches on `/blue` (private mode, A-48), scratch `$TMPDIR`, GPU jobs offline
  (`HF_HUB_OFFLINE=1`) after a CPU prefetch job; a GPU idle for 1 h kills the job, so CPU stages run as separate jobs
  and workers share one claim queue. Fallbacks `hpg-rtx6000` (96 GB) or L4; there are no A100s any more. B200 queue
  waits can be long. Source: `hpg/docs/HIPERGATOR_NOTES.md`, https://docs.rc.ufl.edu/scheduler/gpu_access/,
  https://docs.rc.ufl.edu/resources/gpus/.
- *Use (r1):* ~~alignment of 95 videos, ASR cross-checks,~~ H1-chrono walk-forward fine-tunes, voice/face features and
  replications of local tables, only after the A-48 sponsor confirmation, under the sponsor group's allocation; storage
  for research and educational data only. The freeze critical path (alignment, anchors, D-VAL, scoring) stays on the
  local 5090. Every model in the stack fits on one GPU.
- *Package:* `hpg/` (config.yaml with every tunable, `compute.max_gpus: 2`, profiles for b200 / rtx6000 / l4 /
  local5090 / cpu; manifest of 95 pressers and 148 calendar entries; `fedpress/` code in progress). See A-36.
- *Numerics:* see A-49; report CPU-vs-GPU agreement on the two smoke meetings (sentence argmax flips, meeting score
  change, τ change).
- Qwen-Omni stays excluded for look-ahead and validity reasons; compute is no longer the reason.

**A-28 Model access and pinning (r1: see A-40).** The user requests access to `gtfintechlab/FOMC-RoBERTa` (gated,
manual approval) now; accepting the conditions is the user's decision. G0 records "no model access" separately from
"no video/ASR". Pin a revision sha for every model (FOMC-RoBERTa aa3bc42…, chrono-bert per checkpoint 2015-2024,
audeering 6eba34a…, whisper 41f01f3…, ECAPA 0f99f2d…, wav2vec2 aligner 569a623…) and archive the weights privately
(A-40(h), A-48), all before the freeze.

**A-29 Model cutoff registry (revised r1).** Registry of id, revision sha, licence and training-data end
(FOMC-RoBERTa labels to 2022-10-15, RoBERTa-large base pretraining to Feb 2019; chrono-bert per checkpoint; WCB to
2024). **(r1)** Cutoff = the stated data end, else the first public release date as an upper bound. (i) Semantic
models (stance, embeddings, vocal and facial affect) may enter a confirmatory or P&L analysis of a meeting only if
their cutoff precedes the meeting; contaminated runs (the planned 2016-2022 FOMC-RoBERTa run) are labelled descriptive.
(ii) Transcription, alignment, VAD and speaker-verification models are exempt from (i), because they output words and
times checked against the PDF, the captions and the anchors (A-05); they stay in the registry. ~~Unknown-cutoff models
are excluded from 2023-2026 everywhere, cross-checks included~~ (read literally this removed the aligner, live ASR,
H2/H3 and H4). (iii) A-29 never enlarges the locked confirmation sample: 2022-11-02 and 2022-12-14 stay out of
confirmation even though they follow the 2022-10-15 label end.

**A-31 vocal_proxy spec (fixed before any audio is processed).** Arousal primary, dominance as the pre-named second;
valence excluded (or used only after residualising on the same chunk's text score), because valence carries lexical
content (Wagner et al., TPAMI 2023; `<scratch>/fedtalk/verify_models/wagner.txt`). Chunks 3-15 s with VAD inside
QA'd chair turns, ECAPA identity gate (A-16 threshold), median per answer and per meeting, causal prior-meeting
same-chair z only. Source invariance: ICC ≥ 0.8 under a 64 kbps re-encode, else the H2 kill switch applies.

**A-32 expression_proxy.** Name the identity model and its licence before H3 data are processed (geometry enrolment
or another permissive option, not InsightFace if a permissive path matters). Upper-face and valence/arousal outputs
with a speaking-flag covariate; **(r1)** the upper-face composite is the single Tier 2 H3 output (section G), the
others Tier 3. fps fixed now (1 fps). Flag 2016-09-21 (640x360). Delete reporter face embeddings.

**A-33 A/V skew.** Estimate each video's audio-video offset (lip-sync cross-correlation on chair close-ups; GCG report
about 3 s, `<scratch>/fedtalk/literature/gcg_lbs.txt` line 965) and shift frame times before H3 masking; log it.

**A-34 Event list maintenance.** Refresh the event table after each meeting (dates confirmed at the preceding meeting;
presser flag only when posted). Do not assume 8 pressers a year in power or paper-trade counts. Add statement word
count; flag a Warsh-era statement-format change as a domain shift for hawk(statement). Source: July 2026 minutes,
https://www.federalreserve.gov/monetarypolicy/fomcminutes20260729.htm (six meetings a year floated; no decision; 2026
unaffected).

**A-35 Calendar (revised r1).** Re-dated from 2026-10-05 (section E). Official FOMC-RoBERTa weights verified by
2026-10-14, else A-40(a). Code and model hashes frozen by 2026-10-21. ~~If G3 has not passed with a frozen hash by
then, 2026-10-28 is measurement-only and 2026-12-09 is the first counted paper trade.~~ **(r1)** 2026-10-28 is
measurement-only whatever G3 shows; counting rules are in A-43 (no counted paper trade without a G3 GO). v0's wording
counted 2026-12-09 even after a NO-GO, against G3's "Stop".

**A-36 HiPerGator package defaults (revised r1).** Before `hpg/` produces any H1 input, change in `hpg/config.yaml`
and the `fedpress/` code:

| Key (line) | Now | Required | Why |
|---|---|---|---|
| `timing.anchor.rule` (49) | `greeting_at_scheduled` | `file` (anchors_csv from A-02) | the chair's first words at the scheduled minute moves every τ earlier by the greeting offset (0.6-144 s) |
| `timing.anchor.max_uncertainty_s` (51) | 30 | ~~60 (interval width)~~ **(r1)** 30 on the half-width of the τ bin | A-02(5); 60 on a half-width would be an effective 120 s width rule |
| anchors_csv columns (`clock.py` `_csv_override`) | anchor_media_s, anchor_wall_utc, uncertainty_s | **(r1)** per bin: media start/end, anchor_wall_lo_utc, anchor_wall_hi_utc, halfwidth_s, n_cues, item ids | A-02(3); "upper bound" exists only in prose today |
| `timing.latency_s` (39) | 30.0 (`known_at = t_end_utc + latency_s`, `clock.py` l.3, 113-134) | **(r1)** 0 for frozen H1 tables; emit `t_end_utc_lo`, `t_end_utc_hi`, `known_at_locked = t_end_utc_hi + M`, `known_at_exec30 = known_at_locked + 30 s` as separate columns | a join on `known_at` would silently run H1-exec30 as the locked row |
| `fetch.captions_vtt` (96) | false | true | A-05 |
| `turns.clock_source` (136) | asr | per-meeting frozen `aligner` / `vtt_mapped` / (C) (A-05 rule) | A-05 |
| `turns.align.method` (138) | text_match | ~~qwen_forced_aligner or whisperx~~ **(r1)** whisperx CTC, wav2vec2 569a623, pinned | A-05, "No LLM in the primary path" |
| `turns.align.max_wer_proxy` | 0.35 | alignment confidence/coverage threshold from PREREG_H1.md | A-05 |
| `text.sentence_splitter` (203) | regex (unversioned) | pinned `nltk.sent_tokenize` + version | A-10 |
| `text.max_length` (206) / text filter | 256 / none | **(r1)** 256 with tail truncation logged; TDW A1/B1 filter + clause split on Q&A and statement | A-10 |
| `aggregate` meeting score (219) | mean(hawk(answers)) − hawk(statement) (answer-weighted) | **(r1)** sentence-pooled mean over qualifying sentences (A-10); answer-weighted as robustness | A-10 |
| `text.crosschecks` (202) | centralbank_roberta, loughran_mcdonald | loughran_mcdonald (CentralBankRoBERTa only as labelled agent sentiment) | A-30 |
| `text.classifier_train_end` (207) | 2022-12-31 | 2022-10-15, plus a base-pretraining flag to 2019-02 | A-29 |
| `aggregate.min_answer_words` (216) | 0 | per A-10 (sentences) and A-22 (≥ 40-word answers for H1-answer) | A-10, A-22 |
| `text.chrono_bert.enabled` | false | true for the H1-chrono run only; checkpoints 2015-2024 pinned | A-14 |
| `voice` outputs | all three | arousal, dominance; valence off | A-31 |
| `diarize.ecapa.enroll_from` / `threshold` (150-154) | opening / null (per meeting) | **(r1)** prior meetings / fixed number per chair from PREREG_H1.md | A-16 |
| `fedpress/gpu.py` `device()` (84-93) | silent CPU fallback | **(r1)** fail in frozen runs; record device, compute_type, batch_size, library and driver versions | A-49 |
| `fedpress/io.py` `try_claim`, `claim_ttl_s` | 21,600 s TTL or dead PID on the same host | **(r1)** heartbeat every 5 min, TTL 20 min, or dead when its SLURM job id is not in `squeue` | A-48 |
| `env/activate.sh` | chmod only on the token | **(r1)** `umask 077`, `chmod 700 $FEDPRESS_ROOT`; `doctor.py` fails if root or cache is group-readable | A-48 |
| `compute.max_gpus` / launcher | 2 per job | **(r1)** plus a pre-submit guard on the user's total running + pending GPU GRES ≤ 2 | A-48 |

Unit tests (r1): on a synthetic meeting the H1-primary entry bar is the first with ts_event ≥ known_at_locked and the
H1-exec30 bar the first with ts_event ≥ known_at_exec30, both instrument and bar ids written to the manifest; a meeting
with halfwidth > 30 s in its τ bin is excluded from (P).

**A-42 Live decision object, end detection and position map (new r1; implementation detail).**

1. *Object.* The paper-traded object is H1-primary as ratified: one entry per meeting. H1-run and H1-answer are
   shadow-logged only. v0's section E protocol never named the object.
2. *Live end event E.* Live, the last answer is known only when the presser ends. E = the earliest of: the stream
   switches to slate or ends; the chair's closing phrase (list frozen in PREREG_H1.md) with no question for 30 s; no
   chair speech for T = 90 s. Evidence: a "no chair speech for T s" detector falsely ends 100% / 84% / 53% / 10% of
   pressers at T = 30 / 45 / 60 / 90 s; answer-to-next-answer gaps have p99 73.5 s and max 280.7 s
   (`plan/checks_r1_execution/end_detection_gap_output.txt`). A false end is logged, and the decision uses the answers
   up to E.
3. *Position map.* p = −k · sign_G3 · clip(s̃ / σ, −2, 2) in ZT DV01 contract units, where s̃ follows A-09, σ is the
   expanding sd of s̃ over prior uncontaminated meetings (A-09), k = 0.5 for Warsh (the locked half-size) and 1
   otherwise, and sign_G3 = +1 for continuation (−1 only if a two-sided G3 GO found reversal; frozen at G3).
4. *Warsh timing.* Warsh pressers are shorter (2557, 2704 and 1722 s vs a Powell 2023-2026 median of 2960 s,
   `hpg/manifest/pressers.csv`; 15-21 answers vs 31). If τ_used falls in 14:58-15:02 ET (the ZT 15:00 settlement),
   the paper entry is the first bar at or after 15:01 ET, with the locked "next open after τ" logged beside it. Log
   τ, answers, qualifying sentences and hold minutes per event; report P&L raw and per square-root hold minute.
5. *Feasible offset.* H1-exec-live (A-20) uses τ_used + 90 s + 30 s, the earliest live-feasible entry.

**A-44 Presser-day runbook for the shared RTX 5090 (new r1; implementation detail, no change to system or guard
settings).** The card serves llama-swap models of 17.8-27.4 GB (models unload only after a 600 s idle TTL) and the
autonomous worker's own llama-server (the user's local LLM-stack notes and the AUTOMATION repository instructions,
`<automation>/`, top-level instructions file); the 12VHPWR guard (`C:/12vhpwr_guard`, logs there) locks the GPU to
180 MHz after 15 s at ≥ 9.5 A on any pin and forces a shutdown 10 s later. From 13:30 to 16:30 ET: pause the autonomous worker and the
coding harnesses; run `C:/LLM/unload.cmd` by 13:45 and load nothing until 16:30; check and log free VRAM (≥ 16 GB) with
an `nvidia-smi` query; run the recorder as a CPU-only process separate from GPU ASR (a GPU stall then loses ASR, not the
recording); log GPU clocks; copy the guard log into the day's hashed decision log. A GPU, guard, OOM or power event
makes the day "infrastructure failure" (measurement void), not a delay sample and not a p90 kill. ffmpeg is installed
now (absent on the host today).

**A-46 Interpretation labels (new r1; clarifying, filed before results).** The G3 verdict is computed only by the
locked rule (A-03, A-23). Diagnostics and extensions never flip it; they attach fixed labels to the write-up. Counted
paper trades need a G3 GO only (A-43). Labels:

| Condition (fixed now) | Label attached to the H1 result |
|---|---|
| D-VAL "measurement weak" (A-15) | "measurement weak" |
| D-DOM corr(s, −S) ≥ 0.8 and H1-A not same-sign with one-sided p ≤ 0.10 (A-37) | "statement-level association", not a Q&A text signal |
| H1-PX text slope p > 0.10 or more than halved with R_pc carrying the effect, or PP-MKT abs(t) ≥ H1 abs(t) (A-38) | "not separable from the in-presser price move" |
| A placebo with the same sign and one-sided p < 0.05 (A-39) | "clock, leakage or regime confound not excluded" + dated investigation note |
| Lexicon slope same sign with p < 0.05 (A-39) | "not specific to the stance model" |
| H1-exec-live slope of opposite sign or below 50% of the locked slope (A-20) | "not robust to execution delay" |
| ε-shifted rerun disagrees (A-02(7)) | "not robust to clock" |
| Post-freeze bug fix changes the verdict (A-40(g)) | "verdict depends on a post-freeze fix" |
| D-VAL-W fails for Warsh (A-47) | Warsh events "measurement weak" (measurement-only, A-43) |

**A-48 HiPerGator governance (new r1; implementation detail plus a policy check).**

1. *2-GPU rule per user (the user's instruction: at most 2 GPUs per session).* `fedpress/gpu.py` `plan_slots` caps
   only the GPUs visible to one job, so a 2-GPU job, a `%2` array and an interactive `srun` could run together. A
   pre-submit guard sums the user's running and pending GPU GRES (`squeue -u $USER -h -t R,PD -o %b`) and refuses any
   job that would take the total above 2. Never run Pattern A (one 2-GPU job) and Pattern B (array `%2`) together; no
   interactive GPU shell while a GPU batch job runs. Run `showQos jie.xu` first; default to 1-GPU shards if the group's
   GPU limit is below 2.
2. *Claims.* Heartbeat claims (A-36) replace the 6 h TTL, which blocked meetings after the 1 h idle-GPU killer or the
   4 h walltime ended a job.
3. *Critical path.* Alignment, anchors, D-VAL and FOMC-RoBERTa scoring run on the local 5090 (audio-only HLS pulls
   suffice); Duo-gated logins and long B200 queues (`hpg/docs/HIPERGATOR_NOTES.md` item 10) stay off the freeze path.
   If the critical path is late, the freeze and the download slip together.
4. *Acceptable use.* UF Policy 12-002 (amended 2026-03-24, https://policy.ufl.edu/policy/acceptable-use-policy,
   fetched 2026-10-03): "UF IT resources may not be used for personal commercial purposes or for personal financial
   or other gain." Before any HiPerGator job, obtain written confirmation from the sponsor (and UFRC if the sponsor
   asks) that the project is UF research with academic outputs. HiPerGator serves only the research arm (descriptive
   tables, H1 and H1-chrono statistics, the paper). The live pipeline, H1-P scoring used for sizing and the A-43 counts
   run on the user's own 5090. Check the UF library Bloomberg academic terms before using it as an anchor source.
5. *Permissions.* `/blue/jie.xu` is group-readable by default (`HIPERGATOR_NOTES.md` line 357). `umask 077` and
   `chmod 700` on the project root; gated FOMC-RoBERTa weights only in the approved user's private directory (teammates
   get score tables or their own access); no Databento raw data on HiPerGator (derived tables only) until the F.6
   licence check is resolved.

**A-49 Reproducibility of frozen tables (new r1; implementation detail, all in the A-12 manifest).** (1) One reference
platform per frozen table: the local 5090 for τ, anchors and scores (the live path runs there); HiPerGator results are
replications reported as agreement. (2) Aligner pinned (A-05). (3) Fail fast on any device fallback; record device,
compute_type, batch_size, ctranslate2 / torch / CUDA / driver, ffmpeg version and resampler in each done-marker; frozen
ASR tables use a fixed batch size (batched decoding depends on batch composition, `hpg/config.yaml` l.127-129). (4)
Content-addressed seed: SHA-256 of every MP4, VTT, PDF and statement HTML plus Brightcove `updated_at`, frozen (assets
change after posting; the manifest today checks MP4 byte size only); HiPerGator verifies SHA-256. (5) Hash the whole
`fedpress` tree, `config.yaml`, the anchor builder and a per-platform lock file (uv.lock on Windows, pip freeze on
HiPerGator); `research/` is git-ignored, so hashes are the record. (6) Anchor per-cue match tables (A-02(9)). (7) The
A-17 VOD-zero calibration uses the hashed live recording. (8) Run the two smoke meetings twice and require identical τ
and argmax.

**A-50 Econ robustness rows (new r1; all Tier 3, fixed now, no tuning).**

- *Outgoing chair.* H1-primary excluding Powell pressers after Warsh's nomination on 2026-01-30
  (https://axios.com/2026/01/30/trump-warsh-federal-reserve-chair-pick): drops 2026-03-18 and 2026-04-29.
- *Concurrent news.* Before outcomes, a flag list of scheduled or public events between 13:50 and 16:00 ET on each
  presser day (Treasury and White House schedules, other central banks, scheduled data), from timestamped public
  sources only, frozen in PREREG_H1.md, nothing added later; H1 and BENCH-R reported without flagged meetings. Example:
  on 2023-03-22 Treasury Secretary Yellen testified on deposit insurance during the presser afternoon
  (https://americanbanker.com/articles/yellen-says-u-s-not-considering-blanket-bank-deposit-insurance).
- *Topic mix (D-TOPIC).* A frozen topic lexicon (inflation, labour, financial stability, policy path, other) tags each
  answer; meeting topic shares reported; a robustness row adds topic-share controls and a within-topic score (each
  answer minus the chair's prior same-topic mean, prior meetings only). Lexicon proxy: inflation answers average
  net-hawk 0.51 vs 0.23 (`plan/checks_it1_econ/question_answer_lexicon.py`).
- *Exit noise.* ES robustness exit at the 15:49 bar close (closing-auction imbalance publication starts 15:50); ZT
  exit-bar emptiness and staleness logged; ZT 15:49 sensitivity.
- *Post-publication subsample.* 2024-05-01..2026-04-29 (after the Narain-Sangani sample, which ends 2024-03-20,
  `<scratch>/fedtalk/literature/narain.txt` lines 136-141), descriptive.
- *Mechanism.* The write-up states one discriminating prediction, reported and not gated: slow diffusion predicts an
  effect concentrated in the first 10 minutes after τ with continuation sign; overreaction predicts reversal.

### F.4 Separately pre-registered extensions (own id, sample, decision rule; filed before results)

**A-14 H1-chrono (revised r1).** Hypothesis: same as amended H1-primary (A-03, A-09, A-10), with stance from a
chronologically trained encoder. **(r1)** Sample: the 70 scheduled pressers 2016-2026 Powell + Yellen (43 + 27; v0's
"72, 2016-2022 n = 45" counted the two unscheduled March 2020 events that A-06 excludes,
`plan/checks/gap_stats_checks.out` s1), realised anchored n reported (58 with today's anchors; MDE r about 0.32 vs
0.295 at 70; `plan/checks_r1_data_eng/anchor_eligibility_output.txt`, `r1_counts_timing_power.out`). Scorer for test
year Y: `manelalab/chrono-bert-v1-<min(Y−1, 2024)>1231` (MIT, ungated; there is no 2025 checkpoint) fine-tuned on
`gtfintechlab/fomc_communication` rows with year ≤ Y−1 (CC BY-NC 4.0; labels end in 2022, so every Y ≥ 2023 uses all
labels). Training settings = fedspeak_v2 Amendment 2 exactly (15% stratified validation split, seed 0; lr 2e-5, batch
16, max length 256, at most 8 epochs, patience 2, weight decay 0.01, 10% warmup; seeds 42, 43, 44 with class
probabilities averaged; `<solo-repo>/research/fedspeak_v2/HYPOTHESIS_v2.md` lines 64-70), so one set
of hashed checkpoints serves both projects; H1-chrono applies the A-10 filter, clause split and P(h) − P(d)
aggregation to their averaged probabilities (v2 uses an argmax share, which H1 does not). v0's "TDW grid, 5 seeds" is
withdrawn. Each test-year model's s is standardised by that model's score sd on a fixed causal reference set
(pre-2016 statement sentences). Accuracy gate: one rolling-origin macro-F1 over the 2016-2022 held-out label years
(year-Y labels scored by model Y), pooled, threshold 0.55 (TDW presser-only F1 about 0.53-0.55); a fail cancels
H1-chrono entirely (no per-year dropping). Decision: the single test is the pooled sample with a chair dummy (Yellen vs
Powell), restricted wild bootstrap of the HC3 t (A-23), sidedness as ratified for A-03; Tier 2 (section G); the
2016-2022 and 2023-2026 sub-samples are descriptive. No P&L language outside 2023-2026 Powell. Also run D-VAL on the
walk-forward scores. Contamination sensitivity for the FOMC-RoBERTa 2016-2022 run: drop presser sentences appearing in
the unsplit `lab-manual-pc` files (A-15(5)). Pin every checkpoint 2015-2024 by sha. Must be filed before the Days 3-7
FOMC-RoBERTa run on 2016-2022. Disclose annotator hindsight (labels made 2022-23), the inherited NC licence and the
smaller base model. Compute: minutes per fine-tune on the 5090 or one B200 (A-48).

**A-18 1-second data (needs user approval of the printed quote; revised r1).** Quote: ohlcv-1s for `ZT/ZF/ZN/ES.v.0`
on the 75 2016+ presser windows $5.47 (`plan/evidence/gap_data/cost_2016plus.csv`), bundled with A-13. Uses:
(i) **STMT-ABS** (descriptive): share of the 14:00-14:20 move in ES and ZT bbo-1s mids realised by +5/+15/+30/+60 s
after the exact 14:00:00 release; (ii) **H1-answer-1s**: entry at τ_used + 30 s (the frozen live minimum; no other
delays scanned), horizons +1m/+5m, fills on bbo-1s as-of quotes (A-21), A-22 selection and inference, run only on
meetings with anchor width ≤ 10 s; ~~one alpha~~ **(r1)** descriptive (Tier 3, no alpha) while its sample is
Warsh-only (no historical meeting qualifies: minimum width about 28 s, `plan/evidence/gap_data/tv_anchor.csv`);
(iii) BENCH-R entry at 14:20:00 and spread profiles. The locked 1m tests are unchanged.

**A-19 BENCH-R cost hurdle and BENCH-R-ES (r1: aligned with A-06).** BENCH-R reports the per-regime statistic and
break test of A-06 plus a costed hurdle table by regime and year (ZT break-even abs(corr) 0.65 / 1.25 at 2 / 4 ticks in
2011-19, 0.20 / 0.38 in 2020-26; `plan/checks_gap_exec/benchr_cost_hurdle_output.txt`, computed on the USMPD start +
60 window, which is now also the A-06 exit). **BENCH-R-ES**: same windows, exit and statistic on `ES.v.0`, {2, 4}
ticks/side plus fees, split 2011-19 vs 2020-26; ~~own alpha~~ its break test is in Tier 2 (section G); labelled a
non-blind replication (its USMPD SPFUT analogue has been seen).

**A-20 H1-exec30 and H1-exec-live (revised r1).** H1-exec30: entry at the first 1m open at or after τ_used + 30 s, all
else as H1-primary. **(r1)** H1-exec-live: entry at τ_used + 120 s (A-42(5)). Both Tier 3 with no decision role. ~~If
the locked row lives and this row dies, the conclusion is no-trade.~~ v0's veto changed the locked G3 rule through an
extension and left "dies" undefined; read as a second significance test it vetoes 2-9% of true GOs by noise and catches
only 49-58% of first-minute effects, because +30 s moves the entry bar in about half the meetings
(`plan/checks_r1_execution/exec30_veto_sim_output.txt`). Now an effect-size label only (A-46): "not robust to execution
delay" if the H1-exec-live slope has the opposite sign or is below 50% of the locked slope. H1-answer-1s keeps +30 s.

**A-37 Statement dominance: D-DOM, D-DECOMP and H1-A (new r1).** The locked s averages hundreds of Q&A sentences
against about 15 mostly repeated statement sentences, so the statement term may carry the variation. Human ratings, 36
pressers 2011-2019: sd of the answer mean 0.61 vs statement 2.67, var(S)/var(s) 1.42, AR(1) of s 0.94, year dummies
explain 94% of s. Lexicon proxy, 27 Powell confirmation pressers: corr(s, −S) = +0.98, corr(s, answer mean) = +0.13;
median 72% of statement sentences repeat the previous statement verbatim
(`plan/checks_r1_econ/r1_econ_checks.out` s1a/s1b; statements in `plan/checks_r1_econ/statements_2023_2026.json`).
R_stmt is a price return and does not remove the text level S, and under Powell after COVID the statement move
reverses (Narain-Sangani), which −S could pick up with H1's continuation sign. Filed before any market join; the
locked statistic is unchanged.

- **D-DOM (diagnostic, text-only):** on the frozen A-10 scores 2016-2026: sd and AR(1) of A_m (Q&A term), S_m and
  s_m; corr(s, −S); corr(s, A); var(S)/var(s); mean |P(h) − P(d)| for filtered vs unfiltered sentences. Published in a
  PREREG addendum before the market join. If var(S) exceeds 50% of var(s), PREREG says that H1 largely tests statement
  tone.
- **D-DECOMP (Tier 3):** exit return on A_m and S_m entered separately, with R_stmt as control, always reported beside
  H1.
- **H1-A (Tier 2):** exit return on A_m with S_m and R_stmt as controls; same sample, exit, statistic and inference as
  H1-primary; sidedness as A-03.
- Interpretation (A-46): if corr(s, −S) ≥ 0.8, a G3 GO is reported as a "statement-level association" unless H1-A has
  the same sign with one-sided p ≤ 0.10; H1-run is labelled statement-dominated under the same condition. Paper trades
  may still run (they are operational) but carry the label.

**A-38 In-presser price move: H1-PX and PP-MKT (new r1).** Reporters ask the chair about live market pricing (22 of
881 reporter turns since 2023, `plan/checks_r1_econ/r1_econ_checks.out` s2), answers track earlier answers
(`plan/checks_it1_econ/question_answer_lexicon.py`), and presser-window moves are one factor across assets
(`<scratch>/fedtalk/data_markets/notes.md` s4b). A post-τ continuation or reversal of the in-presser move would load on
s with no text information. Define R_pc = `ZT.v.0` log return from the 14:20 open to the H1 entry open (no gap with
R_stmt).

- **H1-PX (Tier 2):** the A-03/A-09 regression with R_pc as a second control; same statistic and inference.
- **PP-MKT (Tier 3):** price-only benchmark, slope of the exit return on R_pc alone, same sample and inference.
- Descriptive: corr(s, R_qa), with R_pc split into R_open (presser start to first question) and R_qa (first question to
  τ_used).
- Interpretation (A-46): "not separable from the in-presser price move" if the text slope in H1-PX has p > 0.10 or
  falls by more than half while R_pc carries the effect, or if PP-MKT's |t| is at least H1's.

**A-39 Placebos and the lexicon row (new r1; clarifying for the locked lexicon row).** (1) The lexicon row runs the
same A-03/A-09 statistic with the frozen 20+20 surprise. A hawk/dove lexicon measures the same construct less
precisely (net count vs human answer ratings ρ = 0.032, `plan/checks_gap_models/gap_models_human.out`), so it is read
as a weak-measure comparison, not a null; expected sign as H1. Label (A-46): same-sign slope with p < 0.05 → "not
specific to the stance model". Its locked role ("Negative control") is unchanged. (2) Placebos (Tier 3, same
statistic and inference): **P1** the `ZT.v.0` return over a window of the same length as that meeting's outcome window,
ending 13:50 ET the same day; **P3** the τ_used..15:59 clock window on the previous trading day. A placebo with the
same sign and one-sided p < 0.05 attaches "clock, leakage or regime confound not excluded" and triggers a dated
investigation note; G3 is not re-decided. Rejected: a previous-meeting-signal placebo (s has AR(1) about 0.94, so a
real effect would also load on lagged s).

**A-40 Model-access contingency and weight verification (new r1; filed before any market join).** FOMC-RoBERTa is
gated with manual approval (`plan/checks_gap_models/gap_models_hf.out`); fedspeak_v2 Amendment 2 (2026-10-03, about
21:20 UTC) records that this machine has no approved access and bans unofficial re-uploads. Without a rule, a missing
model at the freeze would force a choice between postponing, promoting H1-chrono or using a re-upload while able to see
which looks better.

- (a) If the official weights at sha aa3bc42 are not obtained through the gated route and verified locally by
  2026-10-14, H1-primary is postponed, not replaced: G3 is not run, and live events are measurement-only. H1-chrono
  runs as registered and stays non-promotable.
- (b) Unofficial re-uploads are never used (as in v2).
- (c) **H1-replica (Tier 2, registered now):** `FacebookAI/roberta-large` (pinned sha) fine-tuned with the TDW script
  on the training file matching A-10 (lab-manual-split-combine), TDW hyperparameters, 3 seeds averaged; accepted only
  if its argmax agrees ≥ 0.90 with the published labels on the 63 pressers, otherwise recorded "not run". It can never
  become the primary; any primary built on it needs a new id and its own G3, filed before results.
- (d) On access: list the repository commits and record the LFS oid of the weight file at each. The model was last
  modified on 2023-09-12, inside the confirmation window (`gap_models_hf.out` line 123). If the weights changed after
  2023-02-01, pin the last earlier commit that passes (e), or treat the meetings before the change date as
  contaminated (Tier 3 sensitivity without them).
- (e) Verification: the A-10 reproduction (argmax agreement ≥ 0.98 with the published labels on 63 pressers).
- (f) Dry-run the frozen scorer text-only on the two smoke meetings before the freeze.
- (g) Single shot: G3 is executed once from the frozen hash. A bug found after the market join is fixed in a dated,
  hashed note; the frozen result is the G3 verdict, the fixed result is reported beside it, and if they disagree the
  A-46 label applies.
- (h) Weights stay in the approved user's private directory (A-48(5)).

**A-41 H1-P: prospective confirmation (new r1).** No blind confirmation sample exists (A-08), and every free choice in
the amendments was made after that exposure. H1-P applies the frozen offline pipeline (A-03, A-09, A-10 as ratified;
PDF text after the event; A-02 clock from the NTP-logged live recording; no live-delay constraint) to every presser
after the PREREG timestamp, starting 2026-10-28, whoever chairs (chair recorded; Warsh domain shift disclosed).
Test: the A-03 slope at looks after 8, 16 and 24 events with the studentised O'Brien-Fleming rule of A-43, sidedness as
ratified, parameters never changed. Own family (Tier P, section G). It cannot rescue a G3 NO-GO: after a NO-GO it is
reported as a prospective replication attempt; after a GO it is the confirmation. Scoring for sizing and counts runs on
the local 5090 (A-48).

**A-43 Counted paper trades and the sequential rule (new r1; replaces A-25 and the last sentence of A-35).** v0's A-25
said Warsh paper trades "support no performance claim" while every future event is a Warsh event, and A-35 counted
2026-12-09 even after a NO-GO.

- 2026-10-28 is measurement-only whatever G3 shows: capture, PDT check, stream lag, end-event detection and shadow
  decisions logged with a frozen 60 s delay. The capture code has never met a live Fed stream.
- A counted paper trade is a frozen-hash H1-primary decision on a presser after both a G3 GO and 2026-10-28, with the
  delay frozen from 2026-10-28 as max(p90 of delay_upper, 30 s). After a G3 NO-GO, or while G3 is postponed (A-40),
  every live presser is measurement-only (shadow decisions logged, never counted, no P&L language). If D-VAL-W fails
  (A-47), Warsh events are measurement-only too.
- Sequential rule: the counted trades, whoever chairs, with the chair domain shift stated. Looks after 8 / 16 / 24
  events; a studentised statistic compared with t_{k−1} quantiles at the O'Brien-Fleming nominal one-sided levels
  (z 2.95 / 2.09 / 1.71). v0's z-boundaries with an estimated sd have simulated size 0.067 (normal) and 0.061 (t3)
  against 0.05 (`plan/checks_r1_stats/r1_obf_t.py`, `.out`); the simulated size of the studentised rule is published
  before the first counted event. Power at a per-event Sharpe of 0.2 is about 0.25 (`plan/checks/it1_stats_checks.out`
  s6). Expected calendar: 24 events take about 3-4 years at 6-8 pressers a year (A-34).
- The count is kept per scorer. Only a scorer with a permissive licence path can support a real-money step: a
  permissive shadow scorer (MIT `chrono-bert-v1-20241231` fine-tuned on the team's own blind labels of pre-2023 Fed
  text) runs on every counted event once it exists, unless gtfintechlab grants written commercial permission. A-30 and
  A-48 block real money independently.

**A-47 D-VAL-W: Warsh-era text validity (new r1; separately pre-registered diagnostic, filed before 2026-10-28).**
D-VAL covers 2011-2019 only, yet every live decision is a Warsh decision. Warsh uses explicit rate-stance words in
1.6-1.8% of Q&A sentences against 2.8-14% in every 2023-2026 Powell presser, gives 15-21 answers against a Powell median
of 31, and his statements have 7-10 sentences against 12-16 (`plan/checks_r1_validity/warsh_vocab.out`,
`stmt_filter_share.out`). Two team members label blind (TDW Table 10 guide, no market data open) a fixed random sample
(seed in PREREG) of 200 chair Q&A sentences plus all statement sentences from the 3 held Warsh pressers, and the same
from 3 matched 2025 Powell pressers. Report macro-F1 and Cohen's kappa of the frozen A-10 pipeline per chair. Rule
fixed now: Warsh macro-F1 < 0.45, or more than 0.10 below Powell, makes Warsh events "measurement weak"
(measurement-only, A-43, A-46). These labels never train or tune any scorer evaluated on 2023-2026. Log the P(neutral)
distribution, qualifying-sentence counts and statement length for each Warsh meeting.

### F.5 New data (needs user approval of the printed quote)

**A-13 Measured spreads (r1: as-of quote rule).** Free get_cost quotes for the 75 2016+ presser windows (13:30-16:30
ET, March 2020 shifted), `ZT/ZF/ZN/ES.v.0`: bbo-1s $3.92, bbo-1m $0.08, ohlcv-1m $0.19; MBP-1 ZT+ES $29.39 (optional)
(`plan/evidence/gap_data/cost_2016plus.csv`; one-day check `plan/checks_gap_exec/cost_checks_output.json`). With
2011-2015 added (A-06) the bbo-1s total rises by roughly a quarter; re-print get_cost for the final window list before
asking. Remaining Databento credit is unknown. After approval: report the quoted spread distribution by era at 14:00,
14:20, each τ_used and the exit; add a measured-cost column (half-spread at entry and exit + 1 tick slippage) and a
quote-fill column (buy at the as-of ask / sell at the as-of bid at τ_used, per A-21; ~~first quote after τ_upper~~).
The locked {2, 4}-tick stress and the H1 statistic are unchanged; no net Sharpe on H1.

### F.6 Open checks (not gaps; verify before relying on them)

- Bloomberg terminal access, export limits and academic-licence terms at the UF library (A-02, A-17, A-48).
- Whether the Databento licence permits sharing raw bars among teammates; share derived tables if unsure.
- Whether the Fed live HLS manifest carries EXT-X-PROGRAM-DATE-TIME (A-17; recorded on 2026-10-28).
- Broker all-in fees per side (A-04).
- **(r1)** Written sponsor confirmation of research status before any HiPerGator job (A-48).
- **(r1)** Whether the 7 uncaptioned meetings' MP4s are complete (A-05).
- **(r1)** FOMC-RoBERTa commit history and weight hashes once access is granted (A-40(d)).

---

## G. Test register (A-45, new r1; frozen in PREREG_H1.md, replaces v0's A-26 "Holm within the declared secondary family")

v0 left the Holm family unnamed while several extensions carried their "own alpha"; counted together there were more
than 20 p-values. Every test now has exactly one tier. "Own alpha" anywhere above means the tier rule below. A test in a
Holm tier that is not run (for example H1-replica when access exists) enters with p = 1; m does not change.

| Tier | Rule | Tests |
|---|---|---|
| 0 | alpha 0.05, sidedness as ratified (A-03); the only GO/NO-GO | H1-primary |
| 1 | Holm, m = 3; labelled non-blind replication | BENCH-R ZT: 2011-19 regime mean (one-sided continuation); 2020-26 regime mean (two-sided); break (two-sided) |
| 2 | Holm, m = 9 | H1-chrono pooled 70 (A-14); H1-A (A-37); H1-PX (A-38); H1-run (A-03); H1-replica (A-40); BENCH-R-ES break (A-19); H2 arousal (A-31); H3 upper-face composite (A-32); H4 Clark-West (A-26) |
| P | own alpha 0.05, studentised O'Brien-Fleming looks at 8/16/24 events | H1-P (A-41); the counted paper-trade sequence (A-43) is reported on the same looks and supports no claim beyond A-43 |
| 3 | descriptive; p-values printed, no claims from them | H1-answer (+1m; +5m, +15m), H1-answer-mid, H1-answer-1s, STMT-ABS, H1-exec30, H1-exec-live, H1-post, H1-primary-FC, PP-MKT, D-DECOMP, placebos P1/P3, lexicon comparison, H1-Q, 2022 split (2016-2022), SEP dummy, H1-chrono sub-samples, H2 dominance, other H3 outputs, A-10 variants (unfiltered, answer-weighted, argmax count, flagged-count exclusion), BENCH-R variants (anchored exit, mid-sign deadband, without sub-tick events, ZF, USMPD UST2Y, three periods, without 2011-2012), A-50 rows (outgoing chair, news-flag exclusion, topic controls, 15:49 exits, post-publication subsample), QA-flag exclusion (A-07), ε-shifted rerun (A-02), trade-implied statistic (A-09), overlap-inclusive H1-run, contaminated 2016-2022 FOMC-RoBERTa run and its overlap sensitivity |
| D | diagnostics; fixed labels only (A-46) | D-VAL, D-VAL-W, D-ASR, D-DOM |

Interpretation labels from Tier 3 and D rows are listed in A-46 and never change a Tier 0-2 decision.

---

## H. Changes in round 1 (`r1_patch`, 2026-10-03)

Round 1 received 76 hole reports from five lenses (statistics 18, execution 14, data engineering 12, validity 13,
economics 19). After deduplication they are 51 distinct holes (2 critical, 20 high, 22 medium, 7 low); all 51 are
addressed below. Sub-claims rejected after checking are noted. "Revised" means a v0 amendment was rewritten in place;
v0's text is kept in `merged_plan_v0.md`.

**Critical**

1. MP4 ends before the last chair answer; clock source chosen by VTT overrun could date τ 35-70 s early → A-05
   (completeness check, per-meeting clock-source rule, unit test, tail check), A-02(2) (anchors on τ's clock), A-03
   note. [data_eng]
2. The locked "Q&A minus statement" signal is mostly the statement term → A-37 (D-DOM, D-DECOMP, H1-A, label), A-10
   (filter on both terms), A-46. Locked statistic unchanged. [econ; related validity hole in item 9]

**High**

3. Decision p over-rejects (unrestricted slope bootstrap, size 0.126) → A-23 revised (restricted wild bootstrap of HC3
   t, Freedman-Lane companion), A-03, A-11. [stats]
4. A-07 QA needed outcome-window prices before the freeze, allowed clock edits from market data, and was mis-signed
   (reported by all five lenses) → A-07 revised (sequence, statement windows only, flags only, hashed addendum), A-12
   (order of outcome scripts). [stats, execution, data_eng, validity, econ]
5. Only 20 of 27 confirmation meetings anchored; v0's n = 27, power and H1-chrono n = 72 wrong → A-02(2) aligner-
   timeline anchors, A-02(5)-(6) locked drop rule kept with FC sensitivity, A-11 revised (realised n, simulated
   operating characteristics, "NO-GO at n ≈ 20 uninformative"), A-14 (70 scheduled). Rejected sub-claim: 2026-04-29 is
   eligible (`r1_econ_checks.out` s3 lists 2026 as 3 of 3); the stats lens's "21 anchored" counts the broken 20230201.
   [stats, data_eng, econ]
6. TV anchor covered only presser minutes 0-30 and assumed a constant offset → A-02(1),(3),(5) (15:00 ET items,
   10-minute bins, drift gate). [data_eng]
7. No contingency if FOMC-RoBERTa access never arrives; weights modified 2023-09-12 → A-40 (postpone not replace;
   H1-replica as Tier 2; commit and hash check; single-shot rule). Chose postponement over the validity lens's
   "replica becomes primary", which would replace a locked scorer. [stats, validity]
8. D-VAL scale inverted, deciding sample unnamed, n = 36 gate noisy → A-15 revised. [stats, validity, econ]
9. A-10's unfiltered inclusion rule makes the two terms incomparable → A-10 retyped as clarifying, TDW-faithful
    primary, label reproduction on 63 pressers. [validity]
10. No in-presser price control or price-only benchmark → A-38 (H1-PX Tier 2, PP-MKT Tier 3, label). [stats,
    execution, econ]
11. One-sided continuation test against the plan's own regime evidence → A-03 sidedness (recommend two-sided; default
    two-sided if not ratified; consequences recorded if one-sided). [econ]
12. No blind confirmation; H1 partly non-blind → A-08 revised (overlap by meeting, provenance table, access rule,
    H1-post), A-41 H1-P prospective. [validity, econ, stats]
13. Trading residualiser crossed the 2020 break and used contaminated scores → A-09 revised (2023+ only, 8-meeting
    start, trade-implied statistic). [econ]
14. BENCH-R exit depended on video anchors → A-06 revised (start + 60 min for every era; anchored exit Tier 3). [econ,
    data_eng]
15. 2011-2012 SEP release inside the BENCH-R hold → A-06 entry at 14:20 in every era. [econ]
16. Paper-trade position needed same-day data A-17(4) forbade; mapping undefined → A-17(5) reworded, A-42(3) map.
    [execution]
17. G5 delay measured the wrong latency; no live end detection; traded object unnamed → A-42(1)-(2), A-17(4), A-20.
    [execution]
18. Stream lag unidentifiable with downstream references → A-17(3) delay_upper with L_ref allowances; no reference →
    G5 cannot pass. [execution]
19. 2026-10-28 could count before any live delay measurement → A-35, A-43 (measurement-only; two recorders, A-17(1)).
    [execution]
20. G3, A-35 and A-25 contradicted each other on counting; OBF z-boundaries oversized → A-43 (counted only after a GO,
    studentised looks, calendar, per-scorer count). [execution, stats]
21. No Warsh-era text validity evidence → A-47 D-VAL-W. [validity]
22. HiPerGator vs UF acceptable-use policy (quote verified 2026-10-03) → A-48(4), section A.8. [validity]

**Medium**

23. known_at = t_end + 30 s would silently run H1-exec30 as primary; anchors_csv lacks bounds; effective 120 s rule
    → A-36 rows and unit tests. [execution, data_eng]
24. ε (archive time base) unmeasured; calibration after G3 with no consequence → A-02(4),(7) (M = 30 s, pre-declared
    rerun and label). [data_eng, stats]
25. A-20 veto changed G3 via an extension; "dies" undefined → A-20 revised, A-46 effect-size label. [execution, stats,
    econ]
26. bbo timestamps mark interval ends; "first record after t" selects on movement → A-21 revised, A-13, A-17(6).
    [execution]
27. Shared 5090 with the LLM stack and the 12VHPWR guard → A-44 runbook. [execution, data_eng]
28. Frozen tables not reproducible (two devices, silent CPU fallback, batch-dependent decoding, mutable assets,
    unversioned code) → A-49, A-36 rows. [data_eng]
29. ECAPA threshold per meeting from offline information; D-ASR in-sample → A-16 revised. Merged the two conflicting
    suggestions: prior-meeting enrolment (data_eng) with out-of-sample D-ASR meetings (execution, validity). [data_eng,
    validity, execution]
30. 2-GPU cap enforced per job, not per user; 6 h claim TTL; HiPerGator on the freeze path → A-48(1)-(3), A-36, A-27.
    [data_eng]
31. H1-run's last leg was the H1-primary trade → H1-run revised. [stats]
32. Multiplicity rules contradicted each other → section G register. H1-chrono decision sample: pooled 70 (stats,
    validity) over 2016-2022 only (econ), for power. [stats, econ]
33. Lexicon control had no decision rule; no placebo → A-39 (label; P1, P3). Rejected sub-claim: previous-meeting-
    signal placebo (invalid with AR(1) 0.94). [stats, econ]
34. H1-chrono spec open (n, 2026 checkpoint, gate, scales, chair dummy, v2 divergence) → A-14 revised (v2 training
    settings and shared hashed checkpoints, pooled gate, per-model standardisation). [stats, validity]
35. Meeting aggregation ambiguous → A-10 (sentence-pooled, the authors' measure, given the filter), A-36 line 219,
    H1-run. Chose sentence-pooled over the stats lens's answer-weighted proposal because most answers have 0-2
    qualifying sentences after the A-10 filter. [stats]
36. A-29 read literally excluded the aligner, ASR, H2-H4 from 2023-2026 → A-29 revised. [validity]
37. Primary-path aligner from the Qwen3-Omni family → A-05 (CTC wav2vec2 primary), A-36. [validity]
38. Warsh pressers shorter; settlement and hold assumptions are Powell-era → A-42(4), A-03 note. [validity]
39. Real-money count would accrue on non-commercial models → A-43 per-scorer count, A-30 note. [validity]
40. BENCH-R statistic, sidedness and exit not uniform across eras → A-06 revised. [stats]
41. BENCH-R sub-tick signals and confounded break → A-06 (sub-tick share, deadband variant, three periods, no causal
    attribution). [execution, econ]
42. Outgoing-chair Powell pressers → A-50. [econ]
43. Concurrent non-Fed news → A-50 flag list. [econ]
44. Topic mix drives answer hawkishness → A-50 D-TOPIC. [econ]

**Low**

45. A-24 extended net tables to H1 → A-24 revised (gross only for H1). [stats]
46. H1-answer signal, sample and sidedness unspecified → A-22 revised. [stats]
47. Paper-log details (double-counted delay, no external timestamp, approvals, overrides) → A-17(5),(6),(8). [execution]
48. A-01 roll unit test tautological → A-01 revised. [execution]
49. /blue default group-read exposes gated weights → A-48(5), A-36. [data_eng]
50. 15:59 exit carries closing-auction and post-settlement noise → A-50 exit rows. [econ]
51. The construct is published; 10 of 27 confirmation meetings are in that paper's sample → A-50 post-publication
    subsample and mechanism paragraph. [econ]


**Not changed.** The locked family table text (section A.2, Spec and Role columns), the locked {2, 4}-tick stress,
"No net Sharpe on H1", "No LLM in the primary path", "No 1s bars without a new user-approved quote", the 15:59 exit of
A-03, and the H2/H3/H4 specifications. Items that need people rather than text: the team's dated ratification of A-03
and A-10; the user's FOMC-RoBERTa access request and its approval by the authors; written sponsor confirmation for
HiPerGator; the user's decisions on the A-13/A-18 quotes, the presser-day bbo cap and OpenTimestamps digests.
