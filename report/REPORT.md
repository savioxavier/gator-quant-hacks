# Reading the Fed: Stance, Press-Conference Surprise and the Rates/USD Complex

**Gator Quant Hacks 2026, Systematic Trading track. Team report, full version (2026-10-04).**
Code, data and results: https://github.com/savioxavier/gator-quant-hacks (branch `review/strategy-01`, merged into `main`).

> **For the team (how to compile).** This file is the long version; cut it to the 5-page quant note (11pt) for the
> submission. Figures are relative links to committed PNGs. From the `report/` folder:
> `pandoc REPORT.md -o report.pdf --resource-path=.:.. -V fontsize=11pt -V geometry:margin=1in --toc`
> (add `--pdf-engine=xelatex` if a font is missing). Every number below is in a committed file; Appendix H maps
> each table to its source. Sections 1-8 follow the competition blueprint; References and Appendices come after.

---

## 1. Summary

We trade the stance of the Federal Reserve's own words. Every Board speech, FOMC statement, set of minutes and
press-conference transcript from 2015 to 2026 (1,098 documents) is scored hawkish or dovish by language models
retrained each year only on text published before that year; the scores decay into a daily consensus that, averaged
with a frozen speech lexicon, sets a 75% TLT / 25% UUP position at the next open, sized to 10% volatility (v2, signal
T4 with expression E1). The edge is economic: the Fed reveals its policy path gradually, through hundreds of dated
remarks that no single release summarises, so rates and the dollar absorb it over days rather than seconds, and the
signal is nearly uncorrelated with our existing core portfolio (0.03 in-sample). Out-of-sample (2024-10-03 to
2026-10-02, evaluated once), the strategy earned a Sharpe of 0.61 net of costs and 0.54 at double costs (3.8% a year
at 6.3% volatility, maximum drawdown -6.6%), and adding it to the core portfolio raised that portfolio's
out-of-sample Sharpe from 0.60 to 0.87 (0.46 to 0.70 at double costs). These results have limits: the strategy failed
its own pre-registered in-sample cost test (Sharpe 0.39 at double costs, below the 0.5 required), so its
out-of-sample window was opened only by a dated deviation, and the out-of-sample gain is not statistically
significant (Newey-West t = 0.84) and comes mostly from the final months.

## 2. Economic Hypothesis

**Claim (pre-registered).** Fed communication carries information about the future policy path that Treasuries and
the dollar absorb over days, not seconds: a hawkish consensus should predict falling Treasury prices and a rising
dollar beyond what recent rate momentum explains.

**Who is on the other side.** Mostly investors who hold duration and dollars for reasons unrelated to Fed speeches:
liability-matching pension funds and insurers, index and benchmark-tracking bond funds, foreign reserve managers,
bank securities portfolios, and retail holders of TLT and UUP. They keep their exposure through a hawkish turn
because their mandate, benchmark or liabilities require it, not because they disagree with our reading.

**Why the opportunity can persist.**

- **Behavioural bias: limited attention to gradual information.** The Committee's centre of gravity moves through
  hundreds of speeches, minutes and conference answers a year, often dated only by day, and no single release
  summarises it. Investors underreact to information that arrives continuously in small pieces (Da, Gurun and
  Warachka, 2014) and anchor on the statement and the dots; voice tone in press conferences moves equities over days,
  not minutes (Gorodnichenko, Pham and Talavera, 2023).
- **Structural and institutional constraints.** Benchmark and liability mandates limit tactical duration and currency
  bets; Fed blackout periods and day-level dating make the signal slow and noisy, which deters short-horizon capital;
  and a usable signal needs a stance model that never sees future text. Most off-the-shelf language models are
  trained on data that postdates the documents they score, and the standard labelled dataset mis-dates most of its
  sentences, a hurdle we had to fix ourselves (Section 4.1).
- **Risk premium.** The position is short duration when the Fed sounds hawkish, so it loses when policy surprises the
  other way. Part of any return is likely compensation for bearing that policy-path risk, which predicts returns
  concentrated in policy-turning regimes (such as 2022) rather than spread evenly; we treat such concentration as a
  warning sign, not as evidence.
- **Capacity.** The chosen expression uses UUP, whose daily volume limits the sleeve to about $10m, so funds large
  enough to arbitrage the effect cannot use it at size (the futures version is a different trade; Section 7).
- **Liquidity provision: not claimed.** We trade at the next open in deep markets (TLT, Treasury futures) and take
  liquidity at low cost; no part of the hypothesis relies on being paid for supplying liquidity.

**Press conferences (H1, H2-H4).** If the Chair's answers carry policy information the statement lacked and markets
absorb it over minutes, a Q&A surprise should predict the 2-year futures move after the conference; the other side
would be traders who priced the statement and react slowly to the answers. But speed competition is intense for
exactly this information, and the statement-to-conference continuation reversed after 2020 (Narain and Sangani,
2026), so we stated a low prior and treated it as a measurement with one go/no-go gate, not as an expected edge.

**What would falsify it (registered before any result).** A selection Sharpe at or below 0.2 or a validation Sharpe at
or below 0; more than half of in-sample P&L from 2022; a momentum-orthogonalised signal near zero while the raw
signals look good; a net Sharpe at or below 0 at double costs.

## 3. Data & Universe

**Text.** From federalreserve.gov, with release times from the site's JSON feeds: 828 Board speeches
(2015-01-01..2026-10-02), 97 FOMC statements, 94 sets of minutes and 79 press-conference transcripts. Q&A: 2,026
Chair answers from 75 press conferences (2016-2026), of which 1,977 are scorable by the stance model. Chair tenures used
in the code: Yellen 2014-02-03..2018-02-03, Powell 2018-02-05..2026-05-21, Warsh from 2026-05-22. Stance labels:
gtfintechlab/fomc_communication (Shah, Paturi and Chava, 2023; 2,480 sentences; CC BY-NC 4.0). Base models:
manelalab/chrono-bert-v1 yearly checkpoints (He et al., 2025; ModernBERT-base, about 150M parameters; MIT).

**Recordings (H2-H4).** 95 press-conference recordings (82.4 video-hours, 62.8 GiB) with captions and transcripts,
archived from the Board's site; 64 Powell conferences (2018-03-21..2026-04-29) carry voice and face features.

**Markets.** Daily: TLT and UUP (Yahoo Finance, adjusted), Databento GLBX.MDP3 futures (ZN, 6E, ES; volume-ranked front
contract, back-adjusted at rolls), FRED DTB3 (T-bill) and DGS2 (2-year yield). Intraday, 13:30-16:30 ET on the 75
press-conference days: Databento 1-minute and 1-second bars for ZT, ZF, ZN and ES, and 1-second best bid/offer for ZT,
ZN and ES (no ZF quotes, no depth). ZT's tick fell from 1/128 to 1/256 of a point ($15.625 to $7.8125 per contract;
CME SER-8171, trade date 2019-01-14); costs use the tick of the day. ZT 13:50-14:20 returns correlate -0.995 with the
USMPD statement-window 2-year yield change (n = 70; Acosta et al., 2025), a check on our clock and contract choice.

**Hygiene.**
- *Survivorship.* Instruments fixed in advance and trading throughout; documents are a census of official Board and
  FOMC text, not a selection.
- *Corporate actions.* ETFs are total-return adjusted; futures returns are computed within one contract, with an extra
  round trip charged on roll days; intraday, one instrument per window.
- *Missing data.* Nothing is filled with later data. DGS2 is forward-filled from past values only and lagged two
  sessions. Missing minutes are skipped (1,593 bad quote records were dropped). Press conferences without captions
  (7 in 2023-26), with distorted caption timelines, or outside the market window (2 unscheduled meetings in March 2020)
  are dropped from the timing tests, leaving 62 of 75. Two degraded Databento days (2024-09-18, 2025-09-17) are kept,
  with a registered sensitivity that drops them.
- *Known data error.* The recording the Board publishes for 2023-06-14 is the 2023-07-26 press conference (the speech
  says rates rose "today" and that there are "eight weeks until the September meeting"); its voice and face tables are
  not used for June (Note 2). The June transcript is correct.

**Windows.** In-sample 2016-01-04..2024-10-02 (selection 2016-01-04..2020-12-31, 1,259 sessions; validation
2021-01-01..2024-10-02, 943 sessions); out-of-sample 2024-10-03..2026-10-02 (501 sessions), the last two years, which is
shorter than 20% of the sample (2 / 10.75 years = 18.6%), as the competition defines it.

## 4. Methodology

### 4.1 Walk-forward stance model

A document dated in year *Y* is scored only by model *Y*: the chrono-BERT checkpoint pretrained on text up to 31
December of *Y*-1 (capped at 2024), fine-tuned only on labelled sentences whose **source document** predates *Y*. The
labelled dataset's year column disagrees with the source document's year for 2,336 of 2,480 rows, so every row was
re-dated from the authors' per-document files (2,281 exact matches, 192 via an annotated-sheet join, 7 after whitespace
normalisation). Under the literal dataset years, 491 training rows of model 2015 reappear verbatim in documents dated
2015 or later; under the corrected dates, 21 do, all sentences first published earlier and repeated later. Settings,
fixed in advance: 15% stratified validation split (seed 0), learning rate 2e-5, batch 16, maximum length 256, at most 8
epochs with patience 2 on macro-F1, weight decay 0.01, 10% warm-up, seeds 42/43/44 averaged (12 years x 3 seeds = 36
fine-tunes). A document's score is the share of hawkish minus the share of dovish sentences. Validation macro-F1 ranges
0.545-0.684 across the 36 models (Appendix C), below the about 0.71 reported for FOMC-RoBERTa (Shah et al., 2023),
whose gated weights we could not obtain in time (Deviation D1).

### 4.2 v2 signals, expressions and costs

- **Consensus.** C_t = lambda C_{t-1} + sum of the scores first usable at t, lambda = 2^(-1/20) (a 20-session
  half-life), as in strategy 01 except that every document injects; expanding z-score with a minimum of 252
  observations; a document dated *d* enters at the first session after *d*.
- **Signals.** T1 speeches only; T2 all documents; T3 T2 orthogonalised each day on the decayed, two-day-lagged DGS2
  change (expanding point-in-time OLS); T4 the mean of the lexicon and stance-model z-scores. Variant A (strategy 01's
  frozen lexicon, T0f) is the pre-declared reference.
- **Expressions.** E1: 75% TLT / 25% UUP, next-open fills. E2: 75% ZN / 25% short 6E, next-close fills. 4 signals x 2
  expressions = 8 combinations.
- **Sizing and limits.** z clipped at +/-2; 10% annualised volatility target (mean of 20- and 60-day realised vol, 4%
  floor); gross cap 1.5x; no-trade band 0.10; the rates leg is halved over each FOMC announcement session (101 dates
  from 2015, including 8 unscheduled ones; Deviation D-1).
- **Costs.** E1: 1.5 bp (TLT) and 5 bp (UUP) per unit of NAV traded, one way (2.375 bp blended), plus 30 bp a year on
  short ETF weights; cash earns the T-bill and returns are reported in excess of it. These are strategy 01's cost
  assumptions, carried into the pre-registration unchanged before any v2 return, so they were not tuned to the result;
  no measured TLT/UUP spread sample is committed. E2: 1 bp per leg, a round trip per roll; the measured ZN half-spread
  on press-conference days is 0.5 tick (median and p90), which is 0.78 bp of face, so 1 bp is about 1.3 such
  half-spreads. **2x rows double trading and roll costs** (for E1 the borrow fee is not doubled); gross rows have no
  trading cost and no borrow.

### 4.3 Protocol and portfolio test

We choose the combination with the highest net Sharpe in the selection window and proceed only if its validation
Sharpe is above 0 **and** its full in-sample Sharpe at 2x costs is above 0.5. The out-of-sample window is evaluated
once, only for the chosen combination, only if both gates pass. The Deflated Sharpe uses 11 trials (the 8 combinations
plus Variant A's 3 logged trials; Bailey and Lopez de Prado, 2014). The **pre-declared portfolio test** adds the chosen
sleeve to core_ER_6 as a fourth sleeve at equal risk. core_ER_6 holds three sleeves (a volatility-managed S&P 500
futures position, the month-end Treasury trade in ZN and the trend sleeve S1) combined at equal risk with a 6%
volatility target, trailing 252-day covariance (minimum 126 observations), month-end decisions applied two sessions
later, leverage cap 4 and overlay costs.

**Deviation D-3.** v2 failed the 2x gate, so under the rule its out-of-sample window stayed closed. Because the
competition requires in- and out-of-sample results for the submitted strategy, deviation D-3 (committed at 01:10 UTC on
2026-10-04, before any out-of-sample return existed) opened the window **once**, for T4xE1, Variant A and the portfolio
test, with the frozen code, signals, parameters and costs. The failed verdict stands and cannot be reversed by the
out-of-sample result. The code refuses any second evaluation; a separate reproduction mode recomputes the one
evaluation from scratch and compares it with the committed files (Section 5.7).

### 4.4 Press-conference clock, H1 and BENCH-R

- **Clock.** Conferences are anchored to live TV captions (GDELT TV API for CNBC and FOX Business; Internet Archive),
  not to the 14:30 convention: the Board's caption video starts a median 28.8 s after the scheduled time (n = 63, range
  -15.2 to 110 s). The decision time is the answer end plus the start uncertainty (median 9.3 s, range 8.5-17.7 s), and
  an 11 s TV delay is assumed (plausible 3-20 s; there is no true wall clock).
- **H1-primary.** The surprise is the meeting's mean Q&A stance minus the statement's stance, residualised on the
  13:50-14:20 ZT move with chair intercepts; the trade is short ZT on a hawkish residual (long on dovish), from the next
  1-minute open after the conference to 16:00 ET, one contract. No position until 8 prior meetings exist, so positions
  start 2018-03-21. **G3** (the decision): GO only if n >= 15 confirmation meetings (Powell, 2023-02-01..2026-04-29,
  timing-eligible), mean gross P&L > 0 and one-sided sign-flip wild-bootstrap p <= 0.05.
- **BENCH-R.** Holds the sign of the 13:50-14:20 ZT move from 14:20 to the next 1-minute open after the conference ends,
  split at 2020-01-01 (the reported eras are never averaged). It is non-blind: its era correlations were seen before
  the plan was written.
- **Costs.** C0 gross (trade prints); C2/C4 = 2/4 ticks per side; CM = measured half-spread at the entry and exit
  seconds from 1-second quotes; F = $2.00 per side fee (an unverified broker estimate). ZT was one tick wide at every
  fill point (median and p90 half-spread 0.5 tick; no quote older than 60 s). "Net 1x" in the strategy series is CM + F
  ($11.81 per ZT round trip from 2019; $19.63 in the 2016-2018 tick era).

### 4.5 Voice, face and their combination (H2-H4)

A feature package (`hpg/fedpress_pkg`) turns each recording into time-stamped tables: Whisper large-v3-turbo transcript
aligned to the official transcript; ECAPA speaker verification enrolled on the Chair's opening remarks; 8-second chunks
of the Chair's answers scored for arousal, dominance and valence (audeering wav2vec2 MSP-dim); 1 frame per second of the
Chair's face with MediaPipe blendshapes, EmotiEffLib expression scores and an SFace identity gate. Every row carries
`known_at`, the time it could have been known live, but the tests never join on it: a chunk counts only if it ends by
the caption answer end.

- **H2 (voice).** Answer-level arousal z-score (robust, against the Chair's strictly earlier meetings, 4-meeting
  burn-in); long ZT on high arousal, entry at the next 1-minute open after the answer, +1 minute exit, gross.
- **H3 (face).** Upper-face composite (brow lowering, inner-brow raise, eye squint), same design.
- **H4 (combined).** Text-only vs text + arousal + upper-face models, fitted once by OLS on 2018-2022 (247 answers in 12
  meetings) and frozen before any 2023-2026 join; one-sided Clark-West test on meeting-clustered errors.
- **Gates.** Caption-offset check (ASR vs captions within 2 s), WAV-length check, identity gates; kill switches G4
  (variance floor binding in more than 25% of meetings) and source invariance (a 64 kbps re-encode of three 2019
  meetings, ICC >= 0.8). Holm correction across H2, H3 and H4 (m = 3); a killed test enters at p = 1.
- **Platforms.** The package ran on HiPerGator (speech on B200 GPUs, face on CPUs), the reference run, and on one
  local RTX 5090, the replication. Where they disagree, HiPerGator governs (Note 1).

### 4.6 Governance

Every hypothesis, amendment and deviation was written, hashed and timestamped before the result it governs, and
committed publicly; the log (`preregistration/PREREG_LOG.md`, Appendix A) also records five disclosures where the
record was imperfect (Appendix B). Licensed market data never enter the repository: results keep returns, ticks, P&L
and spreads in ticks, and every price-level file is git-ignored.

## 5. Results

### 5.1 v2: selection across the eight combinations

**Table 1. v2 in-sample Sharpe ratios (net excess over T-bill; annualised daily).**

| Combination | Selection (1x) | Validation (1x) | Full IS (1x) | Full IS (2x) | Full IS (gross) |
|---|---|---|---|---|---|
| T1xE1 | -0.582 | 0.974 | 0.196 | 0.150 | 0.256 |
| T1xE2 | -0.358 | 0.660 | 0.197 | 0.132 | 0.263 |
| T2xE1 | -0.346 | 0.825 | 0.246 | 0.194 | 0.312 |
| T2xE2 | -0.177 | 0.456 | 0.171 | 0.097 | 0.245 |
| T3xE1 | -0.205 | 0.804 | 0.269 | 0.212 | 0.339 |
| T3xE2 | -0.065 | 0.635 | 0.298 | 0.222 | 0.373 |
| **T4xE1 (chosen)** | **0.154** | **0.687** | **0.441** | **0.387** | **0.507** |
| T4xE2 | 0.151 | 0.707 | 0.453 | 0.377 | 0.528 |
| Variant A, frozen lexicon (reference) | -0.013 | 0.691 | 0.355 | 0.312 | 0.411 |

T4xE1 had the highest selection Sharpe (0.154). It passed validation (0.687 > 0, 0.013 short of the team's 0.7 target)
but failed the 2x gate (0.387 < 0.5): **the decision rule failed**. All six combinations that use the stance model
without the lexicon (T1-T3) were negative in selection, and T4's validation Sharpe equals the frozen lexicon's (0.687
vs 0.691), so the stance model added little return; our contribution is methodological.

**Falsifiers.** Two of the four fire: the selection Sharpe is at most 0.2 (0.154), and 73.9% of in-sample P&L comes
from 2022. It is not rate momentum: T3 tracks T2 (z-score correlation 0.975; full in-sample T3xE1 0.269 vs T2xE1
0.246), and the net Sharpe at 2x stays positive. **Deflated Sharpe** (11 trials): 0.223 for the selection window and
0.436 for the full in-sample period (SR0 0.495; sensitivities 0.232 and 0.280).

### 5.2 v2 T4xE1: in-sample vs out-of-sample

**Table 2. T4xE1 by window (excess over T-bill; arithmetic annualised return; max drawdown from the window's first
close).**

| Window | Basis | Ann. return | Vol | Sharpe | Max DD | Turnover (x NAV/yr) | Hit rate | Newey-West t |
|---|---|---|---|---|---|---|---|---|
| Selection 2016-01-04..2020-12-31 | net | 1.25% | 8.11% | 0.154 | -16.1% | 35.0 | 49.4% | 0.37 |
| | 2x | 0.43% | 8.11% | 0.053 | -17.1% | 35.0 | 48.9% | 0.13 |
| Validation 2021-01-04..2024-10-02 | net | 10.00% | 14.56% | 0.687 | -17.8% | 15.9 | 50.4% | 1.45 |
| | 2x | 9.67% | 14.56% | 0.664 | -17.8% | 15.9 | 50.3% | 1.40 |
| Full in-sample 2016-01-04..2024-10-02 | net | 5.00% | 11.33% | 0.441 | -18.8% | 26.8 | 49.8% | 1.41 |
| | 2x | 4.39% | 11.33% | **0.387** | -21.7% | 26.8 | 49.5% | 1.24 |
| | gross | 5.74% | 11.33% | 0.507 | -17.7% | 26.8 | 50.1% | 1.62 |
| **Out-of-sample 2024-10-03..2026-10-02 (D-3)** | net | 3.82% | 6.30% | **0.607** | -6.65% | 17.7 | 49.9% | 0.84 |
| | 2x | 3.42% | 6.30% | **0.544** | -6.78% | 17.7 | - | 0.75 |
| | gross | 4.32% | 6.30% | 0.687 | -6.51% | 17.7 | - | 0.95 |

Max drawdown measured from the starting NAV instead (so that a loss on a window's first day counts): out-of-sample
-7.4% net, -7.5% at 2x, -7.2% gross (T4xE1 lost 0.78% on 2024-10-03).

![Figure 1. T4xE1 growth of 1 (excess of T-bill), net, 2x and gross; selection, validation and out-of-sample shaded.](../backtests/results/v2_oos/equity_T4xE1.png)

*Figure 1. v2 T4xE1. The decision rule failed; the out-of-sample segment is reported under D-3.*

**Read the out-of-sample number with these facts.** It is not significant (Newey-West t 0.84). It comes from the last
months: over the 409 Powell sessions (2024-10-03..2026-05-21) the Sharpe is -0.36 (cumulative -3.1%); over the 92
Warsh sessions it is 2.81 (cumulative +10.9%). Without the last 20 sessions it is -0.01; the five best days carry 108%
of the out-of-sample daily-return sum (2026-09-23, 2025-10-10, 2024-11-25, 2026-09-24, 2026-09-10). By calendar year:
Q4 2024 -6.5% (Sharpe -3.32), 2025 +2.0% (0.58), 2026 to date +12.7% (2.02). A scheduled-only FOMC de-risk list gives
0.6076 instead of 0.6073. The out-of-sample correlation with core_ER_6 is -0.16.

### 5.3 Portfolio test: core_ER_6 + T4xE1

**Table 3. core_ER_6 alone and with T4xE1 as a fourth equal-risk sleeve (6% target).**

| Window | core_ER_6: Sharpe net / 2x / gross | + T4xE1: Sharpe net / 2x / gross | core_ER_6: ann. / vol / max DD | + T4xE1: ann. / vol / max DD |
|---|---|---|---|---|
| Selection | 1.062 / 0.940 / 1.183 | 0.928 / 0.778 / 1.084 | 6.52% / 6.15% / -7.3% | 5.76% / 6.20% / -6.2% |
| Validation | 0.912 / 0.795 / 1.030 | 1.185 / 1.083 / 1.293 | 5.63% / 6.17% / -7.5% | 7.31% / 6.17% / -7.7% |
| Full in-sample | 0.998 / 0.878 / 1.118 | 1.038 / 0.909 / 1.173 | 6.14% / 6.16% / -7.5% | 6.42% / 6.19% / -7.7% |
| **Out-of-sample** | **0.601 / 0.456** / 0.746 | **0.870 / 0.703** / 1.043 | 3.45% / 5.74% / -4.7% | 4.97% / 5.72% / -5.3% |

![Figure 2. core_ER_6 alone and with T4xE1, in-sample and out-of-sample shaded.](../backtests/results/v2_oos/equity_portfolio.png)

*Figure 2. Portfolio test.*

Adding T4xE1 raised the out-of-sample Sharpe from 0.601 to 0.870 (0.456 to 0.703 at 2x; Newey-West t 0.95 to 1.32),
but this too is a late effect: in the Powell months the portfolio went from 0.974 to 0.942, in the Warsh months from
-1.342 to 0.535. Measured from the starting NAV, adding T4xE1 deepens the out-of-sample drawdown from -4.7% to -5.9%.
core_ER_6's own out-of-sample returns are not new information: they appeared in earlier portfolio work. Overlay
turnover is 0.3x a year out-of-sample (0.6 in-sample); the T4xE1 sleeve's own trading times its multiplier is 5.8x a
year (7.7 in-sample).

### 5.4 References: Variant A and strategy 01

| Series | Window | Ann. return | Vol | Sharpe net / 2x / gross | Max DD | Turnover |
|---|---|---|---|---|---|---|
| Variant A, frozen lexicon (v2 harness) | full IS 2016-01-04..2024-10-02 | 4.18% | 11.77% | 0.355 / 0.312 / 0.411 | -20.7% | 23.2 |
| Variant A, frozen lexicon (v2 harness) | out-of-sample | -4.95% | 10.90% | -0.454 / -0.502 / -0.399 | -15.6% | 23.7 |
| Strategy 01 (own engine) | IS 2011-12-30..2024-10-02 | 2.34% | 11.16% | 0.210 / 0.162 / 0.272 | -33.5% | 24.5 |
| Strategy 01 (own engine) | out-of-sample | -4.97% | 10.91% | -0.456 / -0.502 / - | -15.6% | 23.3 |

Variant A and strategy 01 are the same frozen rule in two harnesses (-0.454 vs -0.456 out-of-sample). Strategy 01's
worst quarter was Q4 2024 (-11.8%, the book about 0.96 long TLT while 2-year yields rose 62 bp); without that quarter
its out-of-sample Sharpe is 0.14. Its consensus correlated 0.53 with the 2-year yield; its alpha over a DGS2-change
control was 2.3% a year (t 0.84). Variant A's equity curve: `backtests/results/v2_oos/equity_VariantA_T0fxE1.png`.

### 5.5 Press-conference study: H1 and BENCH-R

**G3 decision: NO-GO.** H1-primary on the 20 timing-eligible confirmation meetings (ZT, primary clock, 16:00 exit,
gross): mean +0.50 ticks (+$3.91 per contract per meeting), sd 13.17 ticks, hit rate 55%, t 0.17; one-sided sign-flip
p 0.45 (two-sided 0.88); 90% block-bootstrap CI [-4.06, +5.30] ticks; permutation p 0.67; leave-one-out range [-1.26,
+2.05] ticks. It is NO-GO under a one-sided or a two-sided reading. At n = 20 the gate has little power (P(GO) 0.29
even at a true correlation of 0.3), so this NO-GO is weak evidence that no effect exists.

**Table 4. Press-conference tests, ZT, USD per contract per meeting.** CM = measured half-spreads, no fee.

| Test (sample) | n | Gross | CM | C2 | C4 | t (gross) | Status |
|---|---|---|---|---|---|---|---|
| H1-primary, confirmation 2023-02-01..2026-04-29 | 20 | +$3.91 | -$3.91 | -$27.34 | -$58.59 | 0.17 | **G3 NO-GO** |
| H1-primary, 2016-2022 (positions from 2018-03-21) | 31 | +$2.52 | -$6.30 | -$32.76 | -$68.04 | 0.25 | descriptive |
| H1-primary, out-of-sample slice (no Warsh) | 12 | -$8.46 | -$16.28 | -$39.71 | -$70.96 | -0.80 | descriptive |
| H1-primary, Warsh conferences | 3 | -$36.46 | -$44.27 | -$67.71 | -$98.96 | -0.70 | descriptive |
| Lexicon control (raw lexicon H1), confirmation | 20 | -$32.03 | -$39.84 | -$63.28 | -$94.53 | -1.47 | NO-GO, as expected |
| BENCH-R 2016-2019 | 20 | +$27.73 | +$15.23 | -$22.27 | -$72.27 | 0.94 | non-blind |
| BENCH-R 2020-2026 | 50 | -$35.31 | -$43.13 | -$66.56 | -$97.81 | -1.15 | non-blind |
| BENCH-R 2020-2026 ex-2022 | 42 | +$8.93 | +$1.12 | -$22.32 | -$53.57 | 0.39 | non-blind |
| BENCH-R out-of-sample slice (incl. 3 Warsh) | 15 | +$22.40 | +$14.58 | -$8.85 | -$40.10 | 0.52 | non-blind; not a holdout |

BENCH-R reproduces the pre-2020 continuation in sign, not significance, then reverses (2022 alone -$267.58 per
meeting); the break has Narain and Sangani's sign but p = 0.146 (HC3 t -1.46). Pre-2020 break-even cost is $15.63 per
side (1.0 tick, 2016-18) and $11.23 (1.44 ticks, 2019), against a measured half-spread of half a tick. Three meetings
with a zero statement-window sign take no trade (2020-09-16, 2023-07-26, 2026-01-28). H1's companion slope is null
(HC3 t 0.55); H1-Q (questions instead of answers) is null in both samples (p 0.44, 0.74); the answer-level H1
diagnostic is null at +1, +5 and +15 minutes (p 0.23, 0.61, 0.88). The frozen lexicon control is not estimable (defined
for 4 of 75 meetings).

**Press-conference trades as strategy series (D-3 presentation, no inferential weight).** The frozen positions were
turned into daily return series on $10m, with N contracts per trade chosen so the in-sample gross volatility is 10%
(H1 ZT N = 4,788; BENCH-R ZT N = 1,916), zero on non-trade days, Sharpe from daily returns.

**Table 5. Press-conference strategy series, ZT.**

| Strategy | Window | Trades | Ann. return gross / net / 2x | Sharpe gross / net / 2x | Max DD gross / net / 2x |
|---|---|---|---|---|---|
| H1-primary | IS 2018-03-21..2024-10-02 | 39 | 1.9% / -1.7% / -5.3% | 0.19 / **-0.17** / -0.52 | -12.7% / -16.5% / -36.1% |
| H1-primary | out-of-sample | 15 | -5.1% / -9.3% / -13.6% | -0.79 / **-1.33** / -1.73 | -15.3% / -20.8% / -28.6% |
| BENCH-R | IS 2016-03-16..2024-10-02 (pooled, format only) | 55 | -3.5% / -5.1% / -6.8% | -0.35 / **-0.51** / -0.67 | -46.3% / -54.9% / -64.6% |
| BENCH-R | IS era 2016-2019 | 20 | 2.8% / 1.1% / -0.5% | 0.48 / 0.20 / -0.09 | -9.2% / -11.1% / -13.3% |
| BENCH-R | IS era 2020..2024-10-02 | 35 | -8.5% / -10.2% / -11.8% | -0.69 / -0.81 / -0.93 | -51.2% / -56.4% / -61.6% |
| BENCH-R | out-of-sample | 15 | 3.2% / 1.5% / -0.2% | 0.38 / **0.18** / -0.02 | -10.7% / -11.7% / -12.7% |

![Figure 3. BENCH-R ZT cumulative P&L, % of $10m, gross / net / 2x; out-of-sample shaded.](../backtests/results/presser_strategy/equity_benchr_ZT.png)

*Figure 3. BENCH-R on ZT. Presentation of pre-registered trades; G3 stays NO-GO.*

![Figure 4. H1-primary ZT cumulative P&L, same layout.](../backtests/results/presser_strategy/equity_h1primary_ZT.png)

*Figure 4. H1-primary on ZT.*

Neither press-conference strategy covers its costs in-sample on ZT. The press-conference "out-of-sample" is a calendar
split, not a fresh holdout: 12 of the 20 G3 meetings fall in it and were reported on 2026-10-03. The standard error of
a Sharpe over 15-16 trades is about 0.7. Robustness symbols (ZF, ZN, ES) are in Appendix E; only BENCH-R on ES is
positive net in and out of sample (0.12 / 0.71), one series of eight, with no inferential weight.

### 5.6 Voice, face and combined (H2, H3, H4)

**Table 6. Exploratory H2/H3/H4 (HiPerGator reference run; 2023-2026 test meetings; ZT, +1 minute, gross).**

| Test | n answers / meetings | Statistic | Raw p | Holm p (m = 3) | Status |
|---|---|---|---|---|---|
| H2, vocal arousal | 269 / 10 | mean -0.086 ticks; 90% CI [-0.262, +0.068]; CR1 t -0.81 | 0.439 (two-sided) | 0.878 | not detected; "source invariance not checked" |
| H3, upper-face composite | 272 / 10 | killed: the inner-brow-raise floor binds in 22 of 22 post-burn-in meetings | 1 (killed) | 1.0 | killed by G4 |
| H4, text + voice + face vs text | 269 / 10 | Clark-West t 0.73 (df 9); out-of-sample R^2 vs text-only -0.004 | 0.243 (one-sided) | 0.728 | not detected; includes the killed H3 composite |

**Local replication agrees** (RTX 5090 features): H2 p 0.438 (n 268), H3 killed, H4 p 0.244; the reference run has one
more answer (269 vs 268). **Samples.** 62 baseline meetings; 26 pass the caption-offset check (the 2 s gate excludes
36); burn-in 4 meetings; 22 post-burn-in meetings = 12 training (2019-10-30..2022-05-04) + 10 test (2023-09-20,
2024-06-12, 2024-11-07, 2024-12-18, 2025-01-29, 2025-03-19, 2025-06-18, 2025-07-30, 2025-09-17, 2026-01-28). The source
invariance check could not run because one re-encode meeting (2019-06-19) fails the caption check (offset -2.79 s).

**Not findings.** The meeting-level H4 row (t 2.39, n = 10) is descriptive and outside Holm, and both meeting-level
models forecast worse than zero (out-of-sample R^2 -0.49 and -1.51). Traded, the combined signal makes -0.02 ticks gross
per answer and loses about 4 ticks at 2 ticks per side; measured spreads alone cost about 1 tick a round trip.
Strategy-level rows for the H2/H4 test trades (local run) describe costs, not a strategy: out-of-sample Sharpe about
-2.0 net.

### 5.7 Reproducibility

- **One runner.** `backtests/run_all_backtests.sh` re-runs every stage and compares with the committed files.
- **HiPerGator.** The press-conference suite re-run on HiPerGator reproduced all committed files (13 result files, 8
  per-meeting tables, 13 frozen position files). The v2 in-sample run and its one D-3 out-of-sample evaluation were
  recomputed from scratch on HiPerGator (`hpg/v2_oos.sbatch`): PASS, in-sample 7/7 files, both decision records,
  out-of-sample 18/18 + 2/2 files, maximum absolute difference 1.8e-15, the same chosen combination and the same
  failed decision rule. The reproduction mode refuses to run without the committed decision records and recomputes the
  out-of-sample window only after the in-sample files agree.
- **Independent checks.** v2 metrics recomputed with separate numpy code (2,192 comparisons, none above 1e-6 relative);
  Newey-West t against statsmodels to 3e-15; prefix invariance (rebuilding with data cut early changes no earlier
  signal or weight, max difference 0.0); press-conference strategy series rebuilt (5,272 values, max relative
  difference 4.6e-6); H2/H3/H4 local verification 110 checks, no mismatch.

### 5.8 External review, implementation fixes and benchmarks (deviation D-4)

Two external reviews of the code found two implementation defects and several limits of the signal construction.
Deviation D-4 (committed 2026-10-04 05:30 UTC, before any of the following was computed) fixes the defects behind
switches and adds matched and simple benchmarks and a walk-forward selection. Everything here is descriptive: the
committed results remain the first, reported results, and the verdict stands.

**Defects (confirmed in the code).**
1. *Sizing timing.* The volatility used to size the position entered at the open of session t included the
   open-to-open return ending at that open, which is the fill price (`backtests/v2/v2lib.py`, `weights_E1`;
   inherited from strategy 01). Fix 1: size with returns ending at the open of session t-1.
2. *Overnight drift.* The shared engine applied the previous open's target weights to the overnight return, ignoring
   the drift from that day's intraday move, an uncharged rebalance at every close (example: $50 of $100 rising 10%
   intraday and 10% overnight gives $110.50, the engine $110.25). Fix 2: a simulator that carries shares and cash
   (`backtests/v2/sim_fixed.py`, unit-tested against an explicit share ledger to 1e-12).

**Table 7. Sharpe ratios with the fixes (net / 2x costs).**

| Series | Variant | Full in-sample | Out-of-sample |
|---|---|---|---|
| T4xE1 (registered) | original | 0.441 / 0.387 | 0.607 / 0.544 |
| | fix 1 | 0.438 / 0.384 | 0.625 / 0.559 |
| | fix 2 | 0.450 / 0.395 | 0.603 / 0.539 |
| | both | **0.446 / 0.392** | **0.621 / 0.554** |
| core_ER_6 + T4xE1 | original / both | 1.038 / 0.909 -> 1.042 / 0.913 | 0.870 / 0.703 -> 0.871 / 0.703 |
| Variant A (T0fxE1) | original / both | 0.355 -> 0.364 | -0.454 -> -0.470 |

The fixes move the Sharpe by about 0.01-0.02; at 2x costs the corrected full in-sample Sharpe is 0.392, still below
the 0.5 the rule required. The corrected out-of-sample value depends on how fix 1 lags volatility: close-to-close
returns ending at the close of t-1 give 0.402 / 0.346 in-sample and 0.500 / 0.435 out-of-sample. The core_ER_6
sleeves were not re-simulated with the fixes (they come from other pipelines).

**Table 8. What the stance model adds: matched and simple benchmarks (same sizing and costs; Sharpe net, both
fixes).**

| Benchmark | Selection | Validation | Full in-sample | Out-of-sample |
|---|---|---|---|---|
| T4xE1 (lexicon + stance model) | 0.158 | 0.695 | 0.446 | 0.621 |
| Lexicon leg alone (LEXALL, T4's documents and processing) | 0.251 | 0.789 | 0.524 | -0.297 |
| Stance model alone (T2xE1) | -0.341 | 0.795 | 0.232 | 0.563 |
| Lexicon reference with the same 2015 warm-up (T0v2xE1) | 0.128 | 0.663 | 0.402 | -0.483 |
| Rate momentum alone (T3's control, M) | 0.597 | 0.547 | 0.569 | -0.263 |
| Long 75/25 TLT/UUP, same sizing | 0.487 | -0.657 | -0.031 | -0.838 |
| Buy-and-hold 75/25, unlevered | 0.500 | -0.694 | -0.051 | -0.921 |

In-sample, the lexicon leg alone and plain rate momentum both beat T4; out-of-sample both lose money and the stance
model alone (0.563) carries T4's result. Regressed on the lexicon reference, T4's extra return is 1.0% a year
(t 0.56). The stance model's contribution is therefore not established: it rests on two out-of-sample years and the
late months.

**Walk-forward selection.** At each year-end from 2020, the registered combination with the highest trailing net
Sharpe (from 2016) is picked and traded the next year; the chain is simulated as one weight path per expression, so
switches are filled at each expression's registered timing. Picks: T4xE1 in 2021-2022 and 2025-2026, T4xE2 in 2023
(and in 2024 without the fixes). Chained Sharpe, 2021-01-04..2024-10-02 / out-of-sample: 0.683 / 0.558 original and
0.698 / 0.621 with the fixes, against 0.687 / 0.607 and 0.695 / 0.621 for the registered T4xE1. The walk-forward
choice tracks the registered one; it adds nothing, and its 2020 pick is the same near tie (T4xE1 0.1537 vs T4xE2
0.1511). These values were reproduced independently.

**Signal-construction limits (confirmed).**
- *Silence.* 45 of 98 in-sample sign changes (6 of 17 out-of-sample) happen with no new document, all from dovish to
  hawkish: with negative average scores, the decaying consensus drifts above its expanding mean in quiet periods, a
  built-in hawkish tilt. These flips are small (under 2% of turnover).
- *Volume.* Same-day scores add up (27% of document days carry 2-4 documents); no day- or meeting-normalised variant
  was tested.
- *Format.* Scores count neutral sentences in the denominator, so formats differ in scale (mean absolute score:
  statements 0.224, minutes 0.109, speeches 0.072, press conferences 0.068); the lexicon leg keeps 14 of 97
  statements (none after 2021) but 93 of 94 minutes and 78 of 79 press conferences.
- *Classifier.* Hard labels discard confidence; seeds agree with each other on 72-85% of sentences (all three on
  64-76%); yearly models are not on a common scale (mean score -0.155 in 2021, +0.035 in 2026); validation splits
  sentences, not documents (371 of 373 validation rows of the 2023-26 model share a source document with training),
  so the reported F1 is optimistic, though scored documents never overlap training labels.
- *Expression.* The text lines up best with 2-year yields (+3.45 bp per unit z over 20 sessions, t 2.19), which E1
  does not trade, and most of that link is shared with rate momentum (t 1.14 after the control).

Reading: a fragile, regime-dependent duration and dollar timing strategy whose signal is partly communication
intensity and classifier composition. It failed its own selection and cost gates, its out-of-sample gain is late and
concentrated, and its incremental value over a lexicon and over rate momentum is not established.

## 6. Risk Management

- **Position limits (fixed before testing).** z clipped at +/-2; 10% volatility target with a 4% floor; gross cap 1.5x
  (at most 112.5% of NAV in TLT and 37.5% in UUP); rebalances below 10% of gross skipped except on FOMC days, the day
  after and from flat.
- **Event risk.** The rates leg is halved over each FOMC announcement session. Eight unscheduled actions (2019-10-11,
  six dates in 2020, 2025-08-22) are also de-risked as registered; they were not announced in advance, a small use of
  hindsight (Deviation D-1). A scheduled-only list changes the full in-sample Sharpe from 0.441 to 0.442 and the
  out-of-sample Sharpe from 0.6073 to 0.6076.
- **Model risk.** T3 guards against rate momentum (strategy 01's consensus correlated 0.53 with the 2-year yield); v2's
  T3 tracks T2, so that falsifier does not fire. Three seeds limit fine-tuning noise. The 2x gate and the Deflated
  Sharpe guard against cost and selection optimism, and they rejected v2. The 2022 concentration falsifier fired
  (73.9%).
- **Drawdown and stress.** Worst in-sample drawdown -18.8% net (-21.7% at 2x); out-of-sample -6.65% (-7.4% from the
  starting NAV). Stress case: strategy 01's worst out-of-sample quarter (Q4 2024, -11.8%), when a long-duration book met
  rising 2-year yields; v2 itself lost 6.5% that quarter.
- **Diversification.** In-sample correlation with core_ER_6 0.025, out-of-sample -0.16; this is why the fourth sleeve
  can raise the portfolio Sharpe despite a modest standalone Sharpe.
- **Press-conference trades.** One contract, entered after the upper-bound decision time, flat by 16:00, no trade on a
  zero statement-window sign. Live use was gated (G5): paper trading only after a G3 GO, only if the measured live p90
  delay is at most 60 s, at half size under a new Chair. G3 failed, so nothing goes live.
- **Not pre-registered.** There is no drawdown stop and no monitoring rule, because v2 failed its decision rule and is
  not deployed.

## 7. Liquidity & Capacity

- **v2 E1 (chosen).** Median daily dollar volume over the out-of-sample window: TLT $2.75bn, UUP $32.6m. At the 1.5x
  cap, $10m of capital holds at most 0.41% of a median TLT day but 11.5% of a median UUP day, so UUP binds capacity at
  roughly $10m. Turnover is 26.8x NAV a year in-sample and 17.7x out-of-sample.
- **v2 E2 (scalable alternative).** T4xE2 is similar in-sample (selection 0.151, validation 0.707, full 0.453, 2x 0.377;
  2.75% a year at 6.08% volatility, max drawdown -12.4%, turnover 46.0x) and trades only ZN and 6E futures, far deeper
  markets than UUP, with futures margin and the rest earning the T-bill. It was not chosen by the pre-registered rule
  and has no out-of-sample row.
- **Press-conference trades.** ZT traded a median 2,108 contracts per minute (10th percentile 529) from 14:30 to 16:00
  ET on 30 conference days in 2023-2026, and was one tick wide at every fill point. One contract (the registered size)
  is negligible. The strategy series' sizing (N = 4,788 H1 contracts, $958m of face, 96x capital) is far above the
  median displayed size at entry (518 contracts; at least N at 14.8% of entries), so its net rows, which include no
  market impact and no margin, are optimistic.
- Capacity statistics: `backtests/results/capacity/capacity_stats.csv` (script beside it); displayed sizes at the
  fills: `backtests/results/presser_strategy/capacity_top_of_book.csv` (contract counts from the quote file, no prices).

## 8. Limitations & Next Steps

**Known risks to the claim.**
- *Fragile out-of-sample.* v2's out-of-sample Sharpe is not significant and comes from the Warsh months; without the
  last 20 sessions it is about zero. It was opened only under D-3, after the rule failed.
- *Volume drift.* v2 keeps the decayed sum that sank strategy 01; speech counts rose from 44 (2016) to 117 (2025) and
  every document injects.
- *Power.* With 20 meetings, P(GO) for H1 is 0.29 even at a true correlation of 0.3; a NO-GO is weak evidence.
- *Labels.* Annotated in 2022-23 with hindsight; labels and fine-tuned models are non-commercial (CC BY-NC 4.0); the
  voice model is CC BY-NC-SA.
- *Timing.* No true wall clock (TV delay assumed 11 s); H1 fills use 1-minute trade prints, not quotes.
- *Exposure.* BENCH-R is non-blind; v2 Amendments 2 and 3 were written after strategy 01's out-of-sample verdict was
  known; the press-conference out-of-sample slice had been reported the day before.
- *Signal construction.* The consensus tilts hawkish in quiet periods, adds up same-day documents, mixes formats on different scales, and rests on hard-label yearly classifiers that are not on a common scale; the stance model's value over a lexicon or rate momentum is not established (Section 5.8).
- *Sample.* H2-H4 rest on 10 test meetings, because the 2 s caption gate removes 36 of 62 baseline meetings; source
  invariance was not checked; the face composite was killed by its variance gate.

**Failed ideas (net of costs, sources in the repository).**

| Idea | Key numbers | Why it failed |
|---|---|---|
| v2 T4xE1 (pre-registered) | selection 0.154, validation 0.687, full IS 0.441 (2x 0.387 < 0.5); out-of-sample 0.607 under D-3 | decision rule failed; 73.9% of IS P&L from 2022; out-of-sample gain late and not significant |
| v2 stance-model-only signals (T1-T3) | selection -0.582 to -0.065 | negative in selection |
| Strategy 01 (speech lexicon, TLT/UUP) | IS 0.210 (0.060 ex-2022), out-of-sample -0.456 | speech volume drove the decayed sum; 75% of IS P&L from 2022; alpha over rate momentum t 0.84 |
| Strategy 01, futures version | IS 0.36, out-of-sample 0.10 (ZN leg 0.005) | the gross cap bound on 54% of days |
| H1-primary (press-conference stance surprise) | +$3.91 per contract per meeting gross, p 0.45 | G3 NO-GO; loses after measured costs |
| Lexicon control | -$32.03 per contract per meeting gross | expected null |
| BENCH-R after 2020 | -$35.31 per contract per meeting | regime reversal |
| H2 / H3 / H4 (voice, face, combined) | p 0.44 / killed / p 0.24 | not detected; costs of about 1 tick per round trip dominate |

Other ideas explored before this project (overnight and intraday momentum, pre-FOMC drift, hourly trend, Treasury
auction cycle, tactical allocation timing, carry, value and trend variants) were rejected for costs or decay; they are
documented outside this repository and are not part of this submission's evidence.

**Next steps.**
- Record the 2026-10-28 and 2026-12-09 conferences with network-time logging to measure the clock and live delay.
- A consensus normalised by document count, testable only on data after 2026-10 (it would be post hoc on today's
  sample).
- Re-source the 2023-06-14 recording; run the 64 kbps source-invariance check on meetings that pass the caption gate.
- Repair the signal: point-in-time demeaning or within-type standardisation of document scores, a day-normalised consensus, soft (probability) scores with more seeds, a document-level validation split, an anchor set scored by every yearly model; then test the text against front-end rates first, before choosing an expression.
- FOMC-RoBERTa as a second scorer if access is granted.
- Any voice or face signal could only motivate a new pre-registered test on a new Chair; no forward Powell data exist.

*AI coding assistants were used; the team reviewed and is responsible for all code and claims.*

---

## References

**Papers**
- Acosta, M., et al. (2025). U.S. Monetary Policy Event-Study Database (USMPD). Federal Reserve Bank of San Francisco Working Paper 2025-30.
- Bailey, D. H., Lopez de Prado, M. (2014). The deflated Sharpe ratio. *Journal of Portfolio Management* 40(5).
- Byun, R., Fees, B., Jacobson, M. M., Walker, T. B. (2026). The Fed's fine-tune: Coarse statements and predictive pressers. Working paper.
- Curti, F., Kazinnik, S. (2023). Let's face it: Quantifying the impact of nonverbal communication in FOMC press conferences. *Journal of Monetary Economics* 139.
- Da, Z., Gurun, U. G., Warachka, M. (2014). Frog in the pan: Continuous information and momentum. *Review of Financial Studies* 27(7).
- Gomez-Cram, R., Grotteria, M. (2022). Real-time price discovery via verbal communication: Method and application to Fedspeak. *Journal of Financial Economics* 143(3).
- Gorodnichenko, Y., Pham, T., Talavera, O. (2023). The voice of monetary policy. *American Economic Review* 113(2).
- He, S., Lv, L., Manela, A., Wu, J. (2025). Chronologically consistent large language models. arXiv:2502.21206.
- Narain, N., Sangani, K. (2026). The market impact of Fed communications: The role of the press conference. *International Journal of Central Banking* 22(1).
- Newey, W., West, K. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica* 55(3).
- Shah, A., Paturi, S., Chava, S. (2023). Trillion dollar words: A new financial dataset, task & market analysis. *Proceedings of ACL 2023*.

**Data**
- Board of Governors of the Federal Reserve System: speeches, FOMC statements, minutes, press-conference transcripts, videos, WebVTT captions, calendars, JSON feeds (US government works, public domain).
- CME Group (2019). Notice SER-8171: ZT minimum tick change.
- Databento: CME Globex MDP 3.0 (GLBX.MDP3) ohlcv-1d, ohlcv-1m, ohlcv-1s, bbo-1s (licensed; not redistributed).
- Federal Reserve Bank of St. Louis: FRED series DTB3, DGS2.
- Federal Reserve Bank of San Francisco: USMPD.
- GDELT Project: Television API 2.0; Internet Archive TV News Archive.
- gtfintechlab: fomc_communication dataset (CC BY-NC 4.0).
- manelalab: chrono-bert-v1 yearly checkpoints (MIT).
- Yahoo Finance (via yfinance): TLT, UUP, adjusted daily prices and volumes.

**Models (H2-H4 features)**
- Whisper large-v3-turbo (MIT); SpeechBrain ECAPA speaker verification (Apache-2.0); audeering wav2vec2-large-robust MSP-dim (CC BY-NC-SA 4.0); MediaPipe face landmarker (Apache-2.0); EmotiEffLib (Apache-2.0); OpenCV SFace (Apache-2.0).

---

## Appendix A. Pre-registration timeline (UTC; git commit times where they exist)

| Time | Event |
|---|---|
| 2026-10-03 19:52 | v2 pre-registration written (HYPOTHESIS_v2.md) |
| 19:53 | Amendment 1: 2016+ windows (2015 warm-up), by-chair reporting |
| 20:26 | Strategy 01 replication and out-of-sample verdict committed (bf880da) |
| 21:12 | Amendment 2 and press-conference Deviation D1: walk-forward chrono-BERT replaces the gated FOMC-RoBERTa |
| 21:35 | Clarification: 2015 warm-up documents scored by the 2015 model |
| 21:45 | Press-conference ADDENDUM written (no return computed) |
| 21:50 | Amendment 3 and D1a: labels re-dated from source documents |
| 22:37 | Amendment 3 code committed (0fd707f) |
| 22:40 | DEVIATIONS.md D-1 (unscheduled de-risk dates kept as registered), D-2 (T3 scaling) |
| about 23:10 | v2 in-sample run; decision rule failed |
| 23:11 | Public commit of the pre-registration records (537c483) |
| 23:26 | Exploratory H2/H3/H4 pre-registration (64ceb24), after the H1 NO-GO, before any voice/face feature |
| 23:46 - 00:45 (10-04) | Local voice/face features computed for 64 Powell meetings |
| 2026-10-04 00:49 | Note 1 (815e574): disclosure, platform order, weak-alignment meetings |
| 00:55 | Note 2 (e08cc71): the 2023-06-14 video is the July conference |
| 01:10 | Deviation D-3 (ee28b16): v2 out-of-sample opened once for reporting |
| 01:16 | Note 3 (1c8c9e1): stage-1 bug fixed before any join (the note's text says "about 01:35"; the commit time governs) |
| 01:19 | H2/H3/H4 local replication run, once |
| 01:23 | v2 out-of-sample run, once |
| 02:16 | H2/H3/H4 HiPerGator reference results committed (69839cf) |
| 02:45 | v2 reproduced on HiPerGator: PASS (committed 8a4d3be) |
| 05:30 | Deviation D-4 (ea90ef7): implementation fixes, matched benchmarks and walk-forward selection, before any was computed |

File hashes (SHA-256, first 8): HYPOTHESIS_v2.md 464f8a5b; DEVIATIONS.md 48e6643d; v2_DEVIATION_D3_OOS.md 97585d3c;
presser_team_FINAL_PLAN.md 88cc54a8; presser_DEVIATION_D1.md 660d06a8; presser_ADDENDUM.md 1921b2ca;
presser_H2H3H4_EXPLORATORY.md e030af98; v2 document scores 0e0c1ca7. Full hashes: `preregistration/PREREG_LOG.md`.

## Appendix B. Deviations and disclosures

- **D1 / D1a (Amendments 2-3).** The registered scorer (FOMC-RoBERTa) is gated and access was not granted; the
  walk-forward chrono-BERT replaced it before any return, and its labels were re-dated from source documents.
- **D-1.** Eight unscheduled FOMC dates stay in the de-risk list as registered (small hindsight; sensitivity reported).
- **D-2.** T3 scaling clarified before any v2 return.
- **D-3.** v2's out-of-sample window opened once for reporting although the rule failed; the verdict stands.
- **D-4.** Two implementation defects (sizing timing, overnight drift) fixed behind switches after external
  reviews; corrected rows, matched and simple benchmarks and a walk-forward selection reported beside the committed
  results, all descriptive.
- **Note 1.** Development voice/face tables for 2019-05-01 and 2020-03-03 had been written (22:15-22:38 UTC) during
  package development, before the H2-H4 pre-registration; they were never joined to returns; summary values may have
  been printed. The local run is the replication and HiPerGator governs.
- **Note 2.** The 2023-06-14 recording is the July meeting; its voice/face tables are not used for June.
- **Note 3.** Stage 1 read the WAV length from the wrong field, so every meeting failed a check and the stage crashed;
  fixed before any join, gates unchanged. A diagnostic without prices had shown the gate outcomes (caption gate
  excludes 36 of 62 meetings; H3 killed; H2 source invariance not checked) before the fix was committed. The
  source-invariance step displayed per-meeting arousal medians of three meetings.
- **Public commit timing.** The pre-registration records were committed publicly after the v2 in-sample run and before
  any H1 result was viewed.
- **Exposure.** v2 Amendments 2-3 followed strategy 01's out-of-sample verdict; BENCH-R's era correlations were seen
  before the ADDENDUM.
- **Licensed data.** One file with a few price levels per event was committed by mistake and has been removed from the
  repository history.

## Appendix C. Stance-model diagnostics

| Model year | Documents | Sentences | Validation macro-F1 (3 seeds) | Mean F1 | Seed label agreement | Training rows | Training rows verbatim in docs dated >= Y |
|---|---|---|---|---|---|---|---|
| 2015 | 74 | 8,595 | 0.568, 0.564, 0.598 | 0.577 | 0.851 | 1,606 | 21 |
| 2016 | 222 | 8,906 | 0.631, 0.625, 0.599 | 0.618 | 0.892 | 1,673 | 18 |
| 2017 | 251 | 10,279 | 0.599, 0.613, 0.621 | 0.611 | 0.863 | 1,738 | 23 |
| 2018 | 278 | 9,145 | 0.608, 0.573, 0.571 | 0.584 | 0.851 | 1,836 | 23 |
| 2019 | 571 | 14,145 | 0.580, 0.611, 0.545 | 0.579 | 0.897 | 1,901 | 29 |
| 2020 | 439 | 13,505 | 0.629, 0.619, 0.623 | 0.624 | 0.875 | 2,016 | 24 |
| 2021 | 494 | 15,314 | 0.654, 0.650, 0.647 | 0.650 | 0.883 | 2,184 | 30 |
| 2022 | 462 | 12,762 | 0.645, 0.623, 0.571 | 0.613 | 0.858 | 2,344 | 12 |
| 2023 | 629 | 16,186 | 0.653, 0.650, 0.653 | 0.652 | 0.884 | 2,480 | 8 |
| 2024 | 658 | 18,750 | 0.660, 0.649, 0.684 | 0.664 | 0.865 | 2,480 | 6 |
| 2025 | 702 | 20,078 | 0.659, 0.669, 0.655 | 0.661 | 0.901 | 2,480 | 5 |
| 2026 | 445 | 11,688 | 0.659, 0.669, 0.653 | 0.660 | 0.907 | 2,480 | 4 |

Mean stance score by document type (descriptive): statements -0.193, minutes -0.080, press conferences -0.053, speeches
-0.035. 159,353 sentences scored in total.

## Appendix D. v2 details

- By chair, in-sample (descriptive): T4xE1 Yellen 0.031 (2x -0.073), Powell 0.537 (2x 0.494); Variant A Yellen -0.624,
  Powell 0.618. Out-of-sample: T4xE1 Powell -0.364, Warsh 2.809; Variant A Powell -0.744, Warsh 2.341.
- Drop-last-sessions check (descriptive, written after the result): without the last 1 / 5 / 10 / 20 sessions the
  out-of-sample Sharpe is 0.588 / 0.410 / 0.170 / -0.011.
- corr(C_T2, rate momentum), full in-sample: 0.186; T3 momentum beta at the last in-sample date 0.434.
- First positions: T4xE1 2015-12-31; Variant A's z-score from 2011-12-30.

## Appendix E. Press-conference details

**H1-primary, ZT, USD per contract per meeting, by sample and cost (CMF = measured half-spreads + $2/side fee).**

| Sample | n | Gross | CM | CMF | C2 | C4 | t |
|---|---|---|---|---|---|---|---|
| Confirmation (G3) | 20 | +$3.91 | -$3.91 | -$7.91 | -$27.34 | -$58.59 | 0.17 |
| 2016-2022 | 31 | +$2.52 | -$6.30 | -$10.30 | -$32.76 | -$68.04 | 0.25 |
| In-sample to 2024-10-02 | 39 | +$6.61 | -$2.00 | -$6.00 | -$27.84 | -$62.30 | 0.48 |
| Out-of-sample slice incl. Warsh | 15 | -$14.06 | -$21.88 | -$25.88 | -$45.31 | -$76.56 | -1.12 |

H1 registered sensitivities: drop text flags (n 18) -0.94 ticks (p 0.63); drop degraded days (n 18) +0.56 (p 0.45);
start uncertainty at most 10 s (n 3) +1.0 (p 0.25). H1 robustness symbols, confirmation, gross: ZF +$7.03 (t 0.28), ZN
+$14.06 (t 0.41), ES -$235.63 (t -0.69).

**BENCH-R details.** Slope of the hold return on the statement-window return: 2016-19 +0.193 (t 1.39), 2020-26 -0.096
(t -0.49). Trades: 4 a year in 2016-18, 8 a year from 2019. Max drawdown of cumulative P&L per contract: 2016-19 gross
-$523 (CM -$594); 2020-26 gross -$2,672 (CM -$2,852). USMPD version (2-year yield, conference window): 2016-19 +1.08 bp
(t 1.39), 2020-26 -0.85 bp (t -1.06). ES robustness, gross: 2016-19 +$205.63 (t 1.53), 2020-26 +$122.06 (t 0.52).

**Strategy series, Sharpe by symbol (net, in-sample / out-of-sample).** H1: ZT -0.17 / -1.33, ZF -0.68 / -1.64, ZN
-0.13 / -0.94, ES -0.37 / -0.38. BENCH-R: ZT -0.51 / 0.18, ZF -0.45 / -0.43, ZN -0.27 / -0.34, ES 0.12 / 0.71. Figures:
`backtests/results/presser_strategy/equity_*_all_symbols.png`.

## Appendix F. H2/H3/H4 details

- H2 costs (same trades, ticks per answer): gross -0.086; measured spreads -1.108; measured spreads + fee -1.620; 2
  ticks/side -4.086; 4 ticks/side -8.086. Meeting-averaged mean -0.117 (sign-flip p 0.35); leave-one-meeting-out range
  [-0.146, -0.028].
- H4 other rows (not decisive): expanding window t 0.548 (p 0.30); leave-one-meeting-out 2023-26 t -0.885; ES t -0.94.
- H4 fit: OLS once on Powell 2018-2022, 247 answers in 12 meetings, written and hashed before any test join.
- Answer counts (H2 primary): 542 eligible (287 in the test years); 269 selected at +1 minute in 10 meetings.
- Voice chunks used end a median 20 s (face frames 18 s) after the package's own `known_at`; the tests never join on it.
- Feature tables (64 Powell meetings, local run): `data/fedpress_features_local/`.

## Appendix G. Repository map and how to reproduce

| Path | Content |
|---|---|
| `preregistration/` | all pre-registrations, deviations, notes, PREREG_LOG.md |
| `backtests/run_all_backtests.sh` | one runner for every backtest (v2, press-conference suite, H2/H3/H4) |
| `backtests/results/` | v2 (in-sample), v2_oos (D-3 out-of-sample, HiPerGator reproduction), v2_d4 (D-4 fixes, benchmarks, walk-forward), presser_h1, presser_strategy, capacity, STRATEGY_RESULTS.md |
| `backtests/presser/backtest_h234/` | H2/H3/H4 HiPerGator reference run; `H234_LOCAL_SUMMARY.md` is the local replication |
| `nlp/` | walk-forward stance model (training, scoring, label re-dating) |
| `hpg/` | HiPerGator jobs: feature chain (`run_everything.sbatch`), full backtest (`backtest_all.sbatch`), v2 out-of-sample reproduction (`v2_oos.sbatch`), feature package `fedpress_pkg/` |
| `data/` | transcripts, captions, text corpus, voice/face feature tables |
| `strategies/01/` | strategy 01 review (the lexicon predecessor) |
| `docs/research/` | planning, review and research notes |
| `archive/` | every other shareable working output of the project (exploratory, superseded and failed work; see its README) |

Reproduce: `bash backtests/run_all_backtests.sh` with `PY`, `GQH_MARKET_DIR` (licensed Databento files, not in git)
and optionally `FEDPRESS_ROOT` (feature tables) set; v2 additionally needs `GQH_REPO`, `GQH_DATA_DIR` and
`V2_WORK_ROOT` (see `backtests/v2/README.md`). On HiPerGator: `sbatch hpg/backtest_all.sbatch` and
`sbatch hpg/v2_oos.sbatch`.

## Appendix H. Sources of the numbers

| Report item | Committed source |
|---|---|
| Table 1, falsifiers, Deflated Sharpe | `backtests/results/v2/windows_all.csv`, `summary_is.json` |
| Table 2, out-of-sample facts, Figure 1 | `backtests/results/v2_oos/metrics.csv`, `oos_concentration.csv`, `run/oos_chosen.json`, `run/by_chair_oos.csv`, `equity_T4xE1.png`; `backtests/results/STRATEGY_RESULTS.md` (start-NAV drawdowns) |
| Table 3, Figure 2 | `backtests/results/v2_oos/metrics.csv`, `run/portfolio_oos.csv`, `v2/portfolio.csv`, `equity_portfolio.png` |
| Section 5.4 | `backtests/results/v2_oos/metrics.csv`; `strategies/01/review/VERDICT.md`, `strategies/01/review/analyse/t1_results_all.csv` |
| Table 4, G3, Appendix E | `backtests/results/presser_h1/key_results.json`, `summary_long.csv`, `benchr_break_stats.csv`, `benchr_cost_hurdle.csv`, `spreads_at_fill_points.csv`, `tables/`; `preregistration/presser_ADDENDUM.md` |
| Table 5, Figures 3-4 | `backtests/results/presser_strategy/tables.md`, `key_metrics.json`, `sizing.csv`, equity PNGs |
| Table 6, Appendix F | `backtests/presser/backtest_h234/results/family_holm.json`, `h4_results.json`, `answer_summary.csv`, `qa/kill_switches.json`, `qa/meeting_qa.csv`, `positions/positions_status.json`, `h4_fit/fit.json`; `backtests/presser/H234_LOCAL_SUMMARY.md` |
| Section 5.8, Tables 7-8 | `backtests/results/v2_d4/metrics.csv`, `walk_forward_picks.csv`, `consistency.json`, `README.md`; `preregistration/v2_DEVIATION_D4_FIXES.md` |
| Section 5.7 | `backtests/results/v2_oos/hpg_reproduction/reproduce_report.json`, `consistency.json`; `backtests/presser/backtest_h234/hpg_run_all_backtests.log` |
| Section 7 | `backtests/results/capacity/capacity_stats.csv`; `backtests/results/presser_strategy/README.md` |
| Appendix C, data counts | `backtests/results/summary.json`, `summary.md` |
| Appendices A, B | `preregistration/PREREG_LOG.md` and the files it lists |
