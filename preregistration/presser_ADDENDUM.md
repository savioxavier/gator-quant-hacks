# ADDENDUM: execution rules for the text and benchmark tests

Written Sat 2026-10-03, about 21:45 UTC (17:45 ET). No strategy return, P&L or score-to-return join had been
computed under this addendum when it was written. It fixes the execution choices still open for BENCH-R,
H1-primary, H1-answer, H1-Q (robustness only) and the lexicon negative control.

It does not change the locked family in `plan/team_FINAL_PLAN.md` section 2. Where the merged amendments
(`plan/merged_plan_v0.md` section F, `plan/GAP_REPORT.md`) differ from the locked text, the locked text wins;
section 10 lists every such choice. H2, H3 and H4 need the voice/face pipeline and are not run here.

Paths:
- `plan/` = `D:/AUTOMATION/gqh-systematic/research/fed_presser_plan/`
- `<scratch>/` = the session scratchpad (`%LOCALAPPDATA%/Temp/<session-tool>/D--AUTOMATION/d039033d-cc02-4bae-8a82-ef0f8e45749f/scratchpad/`)
- `bt/` = `<scratch>/presser_bt/`
- `cache/` = `C:/Users/hoang/.cache/gqh/presser/`

## 0. Status when this was written

- **Market data.** The data are on disk and the download log ends with DONE. They cover the 75 presser days,
  13:30-16:30 ET: ohlcv-1m and ohlcv-1s for ZT/ZF/ZN/ES.v.0, and bbo-1s for ZT/ZN/ES.v.0. This addendum buys
  nothing.
- **Stance scores: none exist yet.**
  - `gtfintechlab/FOMC-RoBERTa` is gated, so the download failed with a 401 (`bt/text/rob_status.json`).
  - Under `plan/DEVIATION_D1_stance_model.md` (team decision, about 21:20 UTC) the stance model is the
    walk-forward chrono-bert scorer of fedspeak_v2 HYPOTHESIS_v2 Amendment 2. If FOMC-RoBERTa access is granted
    later, a rerun with it is robustness only. That is Amendment 2's rule; the team should confirm it also applies
    under D1.
  - Every H1 rule below works with either scorer. It reads `score`, `statement_score`, `qa_mean_score`, `H1` and
    `q_mean_score` as rebuilt by `bt/text/code/build.py` from the designated sentence labels. The run records the
    scorer id, revision and sha256.
  - Until scores exist, H1 rows are reported as "not computed"; only BENCH-R and the lexicon control run.
- **Prior exposure:** see section 12.

## 1. Frozen conventions

### 1.1 Clock

- All times are tz-aware America/New_York. Databento `ts_event` (UTC) is the bar start. A minute or second with
  no trades has no bar.
- **"Next 1m open after t"** = the open of the first 1m bar of that symbol with `ts_event` >= t. Missing minutes
  are skipped and logged.
- **"Close at T"** = the close of the last 1m bar with `ts_event` <= T - 1 min, i.e. the last trade before T.
- **Wall clock of caption time x on meeting m:** W_m(x) = `presser_sched_et` + `v0_minus_sched_tv_s` + x
  (events.csv).
  - This is the TV-anchored caption video zero, with an assumed 11 s TV delay.
  - The 14:30:00 convention (`video_zero_et`, `t_start_et`, `t_end_et`, `*_conv_et`) is never used for a fill. It
    appears only in one labelled diagnostic row (3.6).
- **Upper-bound clock.** Every decision time adds the meeting's `start_unc_s` (8.5-17.7 s on eligible meetings),
  following the A-02 principle that clock error can only add delay.
  - **Answer k:** τ_k,upper = W_m(`t_end_video_s`_k + `end_cue_dur`_k) + `start_unc_s`_m.
    `t_end_video_s` is the interpolated end of the answer's last word inside its caption cue. Adding that cue's
    duration puts the time at or after the cue's end.
  - **Presser end:** τ_end,upper = W_m(max(`last_speech_end_s`, max_k(`t_end_video_s`_k + `end_cue_dur`_k))) +
    `start_unc_s`_m. The max guarantees that τ_end is no earlier than any answer end. On 2018-09-26 the two labels'
    last-cue times differ by 33 s.
  - **Fallback:** where `v0_minus_sched_tv_s` is missing, τ_end,upper = `presser_end_est_et` + `start_unc_s` + 1 s
    (the string times are floored to the second). This happens only on timing-dropped meetings, and only BENCH-R
    uses it.

### 1.2 Contracts, ticks, P&L units

- **Contract.** The .v.0 series: volume-ranked front, ranked on the previous day's volume (A-01). instrument_id is
  constant inside every window (checked: 0 changes).
- **Size.** One contract per trade. All P&L is per contract.
- **Tick table.** Verified in the data as the smallest price step on presser days:

| Symbol | Tick (points) | $ per point | $ per tick | Note |
|---|---|---|---|---|
| ZT | 1/128 through the 2018-12-19 presser; 1/256 from the 2019-01-30 presser | 2,000 ($200k face) | 15.625 / 7.8125 | CME cut the tick on trade date 2019-01-14 (SER-8171). "1/8 of 1/32 = $15.625" is wrong: 1/8 of 1/32 on $200k face is $7.8125. Face value is from the CME spec. |
| ZF | 1/128 | 1,000 | 7.8125 | constant 2016-2026 |
| ZN | 1/64 | 1,000 | 15.625 | constant 2016-2026 |
| ES | 0.25 | 50 | 12.50 | constant 2016-2026 |

- **P&L units.** P&L in ticks = position x (exit - entry) / that day's tick. Dollars = ticks x $ per tick. Tables
  pooled across the 2019 tick change report dollars; tick figures are reported by era.

### 1.3 Quotes

- **What a bbo-1s record means.** A record with `ts_recv` = t (a whole second) carries the top of book at t. Its
  `ts_event`, the last trade, is before t.
- **Quote at second t.** Records are not emitted every second (about 8,300 ZT rows per 3-hour window against
  10,800 seconds). So the quote at second t is the last record with `ts_recv` <= t, skipping crossed, locked or
  one-sided records.
- **Half-spread** h(t) = (ask - bid)/2.
- **Staleness.** Staleness (t minus that record's `ts_recv`) is logged. Quotes older than 60 s are flagged but
  still used.
- **Fill seconds.**
  - A 1m fill uses the bar boundary: the bar start for an open, the bar start + 60 s for a close.
  - A 1s fill uses its exact second.
- **ZF** has no bbo-1s, so no measured-cost rows exist for ZF.

## 2. Samples (e)

| Sample | Meetings | Timing-eligible (`drop_timing` = 0) | Role |
|---|---|---|---|
| Confirmation: Powell 2023-02-01..2026-04-29 | 27 | 20 | The only G3 sample (H1-primary). The only sample that may carry P&L language. |
| 2016-2022 | 45 (43 scheduled) | 39 | Descriptive. With FOMC-RoBERTa scores it is classifier-contaminated. Under D1 (chrono walk-forward) it is the additional clean sample reported next to the confirmation sample. Never part of G3. The 2022-vs-rest and SEP-dummy robustness checks run here (A-26). |
| Warsh: 2026-06-17, 2026-07-29, 2026-09-16 | 3 | 3 | Text only. Descriptive listing; no inference. |

**Timing eligibility.**
- A meeting is timing-eligible when events.csv `drop_timing` = 0. That flag applies the plan's 30 s
  start-uncertainty rule to the TV-anchored clock. It also drops meetings with no captions, a distorted caption
  timeline, or an event outside the market window.
- **Confirmation drops (7):**
  - distorted captions: 2023-02-01;
  - no captions: 2023-06-14, 2023-07-26, 2023-11-01, 2023-12-13, 2024-03-20, 2025-12-10.
- **Confirmation timing-eligible (20):**
  - 2023: 03-22, 05-03, 09-20
  - 2024: 01-31, 05-01, 06-12, 07-31, 09-18, 11-07, 12-18
  - 2025: 01-29, 03-19, 05-07, 06-18, 07-30, 09-17, 10-29
  - 2026: 01-28, 03-18, 04-29

**Inclusion rules.**
- The unscheduled 2020-03-03 and 2020-03-15 meetings are excluded everywhere: both fall outside the downloaded
  window (A-06).
- **H1-primary** needs a timing-eligible meeting, a non-missing H1, a non-missing R_m (3.2), a position after the
  burn-in, and an entry bar before 15:59.
- **H1-answer** also needs the answer to be timed (`timing_source` = vtt), at least 40 words, at least one sentence
  unit, and a non-missing score (A-22).
- **BENCH-R** needs no answer timing. It uses all 73 scheduled meetings with market data: 20 in 2016-2019 and 53 in
  2020-2026, including the 3 Warsh meetings. The split is at 2020-01-01, so 2020-01-29 falls in the later era.

**Pre-registered sensitivities** (reported, not decisive):
1. Also drop the two meetings flagged only by the text label's `drop_P_timing` (2024-01-31, 2024-09-18).
   Confirmation n becomes 18.
2. Drop the Databento degraded days 2024-09-18 and 2025-09-17. Confirmation n becomes 18.
3. Keep only meetings with `start_unc_s` <= 10 s.

## 3. H1-primary (a)

### 3.1 Signal

s_m = `H1`_m = `qa_mean_score`_m - `statement_score`_m, from meetings.parquet:
- **Answer score** = share of hawkish sentences minus share of dovish sentences.
- **`qa_mean_score`** = the equal-weight mean of answer scores over the chair's Q&A answers with at least one
  sentence unit. Opening remarks are excluded.
- **`statement_score`**: the "Voting for" roster sentence is excluded.
- `qa_mean_score_ge40w` and `qa_pooled_score` are robustness variants only.

### 3.2 Statement-window move

- R_m = the ZT.v.0 simple return from the close at 13:50:00 to the close at 14:20:00. These are the last bars with
  `ts_event` <= 13:49 and <= 14:19.
- R_m is known at 14:20:00.
- R_m is missing when there is no bar in 13:30-13:49 or none in 13:50-14:19.

### 3.3 Point-in-time residual

Chosen version: an expanding window, never full-sample or leave-one-out.

- **Fit set F_m.** All scheduled presser meetings dated before m (from 2016-03-16) with a valid s and R, whether
  timing-eligible or not.
- **Model.** s_j = α_c(j) + β R_j + e_j, by OLS. The chair fixed effects are the plan's chair dummy.
- **Intercept for m's chair c:** α~_c = (n_c α^_c + 4 α^_prev) / (n_c + 4).
  - n_c = the number of chair-c meetings in F_m.
  - α^_prev = the intercept of the preceding chair (Yellen for Powell, Powell for Warsh).
  - The α^_c term is absent when n_c = 0.
  - This is A-09's Warsh shrinkage, with the weight fixed at 4 pseudo-meetings and applied at every chair change.
- **Fitted value and residual:** ŝ_m = α~_c + β^ R_m; s~_m = s_m - ŝ_m.
- **Burn-in.** No position unless F_m has at least 8 meetings.
  - The eight Yellen meetings of 2016-2017 carry no position; positions start at 2018-03-21.
  - Every confirmation meeting has more than 40 prior meetings, over 35 of them Powell's.
  - Inside the confirmation sample the chair term is a single Powell intercept (A-09).

### 3.4 Position

- p_m = -sign(s~_m) on ZT: a hawkish residual means short ZT (continuation).
- s~_m = 0 means no trade.
- One trade per meeting, 1 contract.
- The ES, ZF and ZN robustness rows use the same p_m (hawkish means short all three).

### 3.5 Entry and exit

- **Entry:** the next 1m open after τ_end,upper.
- **Primary exit:** the close at 16:00:00, i.e. the close of the last bar with `ts_event` <= 15:59. ZT has a 15:59
  bar on 74 of 74 days.
  - This is A-03's reading. The locked "ES window = τ → presser end" is empty, because τ is the presser end, so ES
    uses the same 16:00 exit.
- **Robustness exit:** the close at 16:30:00, i.e. the last bar with `ts_event` <= 16:29.
  - ZT has a 16:29 bar on 65 of 74 days.
  - ES stops at 16:14 on 31 days before mid-2021 (the 16:15-16:30 halt). On those days the ES robustness exit is
    the 16:14 close, labelled as such.
- **Next-day close and the next-day 15:00 ET ZT settlement (A-03's robustness exit) are NOT available.** Our data
  stop at 16:30 ET on presser days. They are not computed.
- **No trade** if the entry bar would start at or after 15:59.

### 3.6 Extra rows

These are labelled, shown beside the primary row, and never decisive.
- **H1-exec30 (A-20):** entry at the next 1m open after τ_end,upper + 30 s. If the primary row passes G3 and this
  row's mean is not positive, the write-up concludes no-trade.
- **Point clock:** τ_end without the + `start_unc_s` term.
- **Convention-clock diagnostic:** entry at the next 1m open after `presser_end_conv_et` (14:30:00 convention).
  It shows the effect of the early clock.

### 3.7 Companion statistic (A-03, A-09)

Reported, not decisive.
- OLS of the ZT exit return (τ entry → 16:00) on s_m, with R_m as a control. Chair dummies are added outside the
  confirmation sample.
- Fitted on the full sample within each sample.
- Expected slope < 0.
- HC3 t, plus a restricted wild bootstrap p (Rademacher, 9,999 draws).

## 4. H1-answer (b): diagnostic only

### 4.1 Signal

- a_k = `score`_k - `statement_score`_m.
- s~_k = a_k - ŝ_m, where ŝ_m is the meeting's point-in-time fitted value from 3.3. The mean of s~_k over a
  meeting's answers therefore equals s~_m.
- p_k = -sign(s~_k).

### 4.2 Entry and exits

- **Entry:** the next 1m open after τ_k,upper. Its bar start is t0.
- **Exits:** the close at t0 + 1 min and at t0 + 5 min, i.e. the last bar with `ts_event` <= t0 + h - 1 min.
- **Appendix:** + 15 min.

### 4.3 Selection (A-22)

1. Start from the eligible answers (section 2).
2. Where several answers share an entry bar, keep the latest.
3. Apply an earliest-first greedy pass per horizon: an answer is kept only if its t0 >= the previous kept answer's
   t0 + h.

No other filter applies.

### 4.4 Latency sweep on the 1s data

Labelled diagnostic, not a retune.
- **Answers:** the same selected answers and signs as the 1m row for each horizon. Only the clock changes.
- **Entry second:** t_e = ceil(τ_k,upper + L), for L in {5, 15, 30} s. L = 0 is added as the reference row.
- **Exit seconds:** t_e + 60 s and t_e + 300 s.
- **Prices:**
  - gross: the bbo-1s mid at those seconds;
  - net (measured): quote fills, buying at the ask and selling at the bid;
  - {2, 4}-tick rows on the mid.
- **Symbols:** ZT; ZN and ES as robustness; no ZF (no quotes).
- **Split** by `start_unc_s` <= 10 s versus > 10 s.

Limits, written down now:
- If the clock is right, τ_k,upper already lies 0 to 2 x `start_unc_s` after the true answer end (about 17 to 35 s
  at most). A nominal L = 5 s is therefore effectively about 5 to 40 s, and the sweep cannot identify latency below
  about 15 s.
- The sweep's result changes nothing. The frozen live delay stays max(measured p90, 30 s) (plan section 5). No H1
  definition, selection rule or horizon is changed by it.

## 5. BENCH-R (c)

- **Signal:** sign(R_m) on ZT.v.0 (3.2). A zero sign means no trade. This is continuation: long ZT if ZT rose from
  13:50 to 14:20.
- **Entry:** the next 1m open after 14:20:00.
- **Exit:** the next 1m open after τ_end,upper. That is the H1-primary entry bar, so the two holds never overlap.
- **Robustness exits and subsets:**
  - exit at the next 1m open after 15:30:00 (the end of the USMPD press-conference window, known in advance);
  - the timing-eligible subset only.
- **ES robustness (BENCH-R-ES, A-19):** the same rule using ES's own 13:50-14:20 sign. ZF and ZN go in the
  appendix.
- **Split:** 2016-2019 (n = 20) vs 2020-2026 (n = 53).
  - The locked "2011-19" era cannot be implemented: there are no 2011-2015 data.
  - Sensitivities: January 2020 assigned to the earlier era; Warsh meetings excluded.
- **Reported:**
  - gross and net P&L by era (section 7);
  - break statistics: the difference in mean gross P&L (2020-26 minus 2016-19), and the difference in slopes of
    the 14:20 → end return on R_m (A-06);
  - a cost hurdle by era and year: break-even cost per side = mean gross P&L per trade / 2, in ticks and dollars;
  - a yearly table, an ex-2022 version, and a 2024-10..2026-09 decay check (A-24);
  - the USMPD UST2Y version: the sign of the statement-window change, applied to the press-conference-window change.
- **Labelling.** BENCH-R is labelled a non-blind descriptive replication (section 12). Eras are never averaged into
  one number, and no annualised Sharpe is reported.

## 6. H1-Q, lexicon control, not run

- **H1-Q** (robustness; collider risk):
  - Same as H1-primary, with q_m = `q_mean_score`_m - `statement_score`_m added to the point-in-time residual
    regression (s_j on chair, R_j and q_j).
  - Position = -sign(residual).
  - Reported next to H1-primary only.
- **Lexicon negative control.** The H1-primary and H1-answer pipelines are run with the frozen strategies/01
  scores. Each lexicon variant gets its own point-in-time fit.
  - **`lex_H1`** (frozen rule MIN_HD = 5): defined for only 4 of 75 meetings, so it is reported as "not estimable"
    with its n.
  - **`lex_H1_raw`**, and `lex_score_raw` minus the meeting's `lex_statement_raw` at answer level: ungated, and
    labelled NOT the frozen spec.
  - **Expected:** no effect. A significant lexicon result is read as a pipeline warning, not a finding.
- **Not run here:** H2, H3, H4, D-VAL, D-ASR, H1-run, the contemporaneous (C) tests, and a separate H1-chrono
  extension (D1 already makes the chrono scorer the primary one).

## 7. Costs (d)

Every P&L table carries these rows, per side, per contract:
- **C0, gross:** trade prints from the 1m OHLC. Associational, not executable mids.
- **C2 / C4:** 2 / 4 ticks per side in that day's tick, so 4 / 8 ticks per round trip. Round-trip dollars:
  - ZT 2019+: $31.25 / $62.50
  - ZT 2016-2018: $62.50 / $125
  - ZF: $31.25 / $62.50
  - ZN: $62.50 / $125
  - ES: $50 / $100
- **CM, measured:** the half-spread at the entry second plus the half-spread at the exit second (1.3 quote rule),
  deducted from the trade-print P&L. ZT, ZN and ES only.
- **CQ, companion:** quote fills (buy at ask, sell at bid at the entry and exit seconds) in place of trade prints.
- **F, fees:** $2.00 per side (A-04; an UNVERIFIED broker estimate). Shown as a separate labelled line on top of
  C2, C4 and CM.
- **Spread summary.** Measured spreads are also summarised by era (median, p90) at 14:20:00, at each τ_end,upper
  entry, at each answer entry and at the 16:00 exit.
- **H1 net rows are descriptive only.** The plan calls H1 non-executable and rules out a net Sharpe, so no Sharpe
  is reported for H1. BENCH-R is the costed object.

## 8. Inference and gates (f)

### 8.1 Common to every result

- Per-meeting P&L in ticks and in dollars per contract: n, mean, sd, median, hit rate and plain t.
- Seed 20261003. Every bootstrap and permutation uses 9,999 draws.
- **Block bootstrap.**
  - A circular block bootstrap over meetings in date order.
  - Block length b = max(2, round(n^(1/3))) meetings: b = 3 at n = 20, and 4 at n = 53 to 73.
  - Reported: a percentile 90% CI, and a one-sided p from studentised draws.
  - For answer-level data, each block holds whole meetings with all their answers.
- **Wild bootstrap, one observation per meeting.**
  - A studentised sign flip: Rademacher weights on Y_m, which imposes the null of a zero mean.
  - One-sided p = (1 + #{t* >= t}) / (9,999 + 1).
- **Answer level** (H1-answer and the sweep):
  - mean P&L per answer, with a t built on a CR1 meeting-clustered SE;
  - a wild cluster bootstrap by meeting, Webb 6-point weights, null imposed;
  - the meeting-averaged version, tested with the sign flip.

### 8.2 G3

G3 applies to H1-primary: confirmation sample, ZT, primary exit, gross P&L.
- **GO** if all three hold: n >= 15 valid meetings; mean gross P&L > 0; one-sided sign-flip wild bootstrap
  p <= 0.05.
- **Otherwise NO-GO,** reported as "not detected" with the upper bound of the 90% CI. Per the plan, H2 is then not
  mined. Fewer than 15 valid meetings is a NO-GO for insufficient data and is stated as such.
- **Reported but not decisive (A-23):**
  - the block bootstrap CI and p;
  - a permutation p (H1 signals permuted across confirmation meetings, positions recomputed);
  - the leave-one-out range, naming the most influential meeting;
  - the result without the two meetings with the largest |ZT move|;
  - the companion slope (3.7) and the extra rows (3.6);
  - the sensitivities (section 2), the robustness symbols and the 16:30 exit.
- If the decision p and the block bootstrap disagree, that is stated next to the GO/NO-GO.

**Operating characteristics, published before the run.** P(GO) by sample size n and true correlation ρ. Source:
`bt/addendum/g3_operating_characteristics.py`. (s, r) is bivariate with correlation ρ; returns are Gaussian or
Student-t(4); 4,000 runs x 1,999 draws. Each cell is Gaussian / t4.

| n | ρ = 0 (false GO) | ρ = 0.1 | ρ = 0.2 | ρ = 0.3 | ρ = 0.47 |
|---|---|---|---|---|---|
| 20 | 0.047 / 0.048 | 0.09 / 0.10 | 0.17 / 0.19 | 0.29 / 0.31 | 0.55 / 0.60 |
| 18 | 0.050 / 0.052 | 0.09 / 0.11 | 0.16 / 0.19 | 0.27 / 0.31 | 0.50 / 0.54 |
| 27 (if all 27 had timing) | 0.053 / 0.052 | 0.11 / 0.12 | 0.20 / 0.23 | 0.36 / 0.40 | 0.67 / 0.69 |

At these power levels, a NO-GO is weak evidence that there is no effect.

### 8.3 Other tests

- Nothing else is gated.
- BENCH-R sides: 2016-19 one-sided (> 0, continuation); 2020-26 two-sided; the break test two-sided.
- H1-answer, the sweep, H1-Q and the lexicon control: two-sided, diagnostic.
- No multiplicity adjustment, because there is a single primary. Nothing may be promoted after looking.

## 9. Order of operations

1. **QA before any P&L,** written to the run's label directory under `qa/`:
   - instrument_id per window;
   - caption-timeline agreement between events.csv and the text label: greeting and last cue within 1.5 s, else
     flag. At writing, the largest greeting difference is 1.3 s, and the one 33 s last-cue difference is covered by
     the max in 1.1;
   - τ ordering, and an entry bar for every trade;
   - the A-07 per-meeting USMPD flag: |UST2Y| > 2 bp and ZT moved the wrong way or less than 25% of the implied
     move. A flag removes a meeting only if a data error is found. The flag list is frozen before any P&L.
2. Positions and point-in-time fits are written, with hashes, before prices are joined.
3. BENCH-R and the lexicon control run now, because their inputs exist. H1 rows run once stance scores exist. G3
   comes from the frozen code.
4. The return and spread columns in events.csv serve only as reconciliation checks. All P&L is recomputed from the
   bars under this addendum.

## 10. Choices where the locked text and the amendments differ

| Item | Locked text | Amendment | This addendum |
|---|---|---|---|
| Timing drop rule | start uncertainty > 30 s → drop from (P) | A-02: interval width > 60 s | 30 s, applied to the TV-anchored clock (eligible meetings: 8.5-17.7 s) |
| Decision statistic | "residual position" | A-03: OLS slope | P&L of the sign position decides; the slope is reported |
| Inference | "Block bootstrap + wild cluster" | A-23: wild bootstrap decides | The sign-flip wild bootstrap decides for one observation per meeting. Block bootstrap reported for every result; wild cluster for answers |
| H1 exit | "τ → presser end" (empty for a meeting-level τ) | A-03: 16:00 ET | 16:00 ET; 16:30 ET robustness; next-day exits unavailable |
| Instrument | ZT.c.0 | A-01: ZT.v.0 | ZT.v.0, the only series downloaded |
| BENCH-R split | 2011-19 vs 2020-26 | A-06: add 2011-15 data | 2016-19 vs 2020-26 (no 2011-15 data) |
| ZT tick | $15.625 | A-04: date-dependent | date-dependent, verified in the data |
| Stance model | frozen FOMC-RoBERTa | D1: chrono walk-forward | D1 |
| 1s data | no 1s bars without an approved quote | A-18: restricted uses | Already on disk (the task states it is approved; nothing is bought). Used only for measured costs and the labelled latency sweep |

## 11. Not available in our data

- Next-day close and next-day 15:00 ET settlement exits.
- The 2011-2015 pressers.
- ZF quotes.
- MBP-1 depth: every 1m result is on trade prints (associational, not executable mids).
- A true wall clock: the TV delay is assumed at 11 s (range 3-20 s), and there is no Bloomberg or NTP anchor.
- Answer times for the 7 meetings without captions (no media or ASR here).
- VIX, needed for the G2 missingness table.

## 12. Prior exposure (seen before this addendum)

- **BENCH-R is non-blind.**
  - The events label reported descriptive correlations of the 13:50-14:20 move with the 14:20-to-end move: ZT
    +0.19 in 2016-19 (n = 20) and -0.09 in 2020-26 (n = 53); ES +0.46 / -0.02.
  - The merged plan (A-08) lists USMPD statement-sign correlations that had already been seen.
  - So the BENCH-R era result cannot serve as confirmation of anything.
- **Other numbers already reported by the events label:**
  - correlations of the 1m returns with USMPD (-0.976 and -0.986);
  - measured ZT half-spreads: median $3.99 for 2019+, $7.89 for 2016-18.
- **H1 is blind.** No stance score exists yet, and no text score (stance or lexicon) has been joined to any
  return.
- **What the author of this addendum saw:**
  - the events and text summaries above;
  - only the timing and QA columns of events.csv (no return, spread or USMPD values);
  - on the market data, only bar-coverage and price-grid (tick) checks.
  - No return was computed.

## 13. Input manifest (SHA-256 when this was written)

```
88cc54a869e7cf540d561a257a3203524392cd1cbe18d25560f397b926651846  plan/team_FINAL_PLAN.md
85494593c641d3bedc77e879a12ff06a5bd386ef2f44a18d0949eae0da409ac3  plan/merged_plan_v0.md
6a1f5adc488c21705431b9e06f244cd319e5d33491ba25704d2494d9b727776b  plan/GAP_REPORT.md
580279a9efe2e4650a0b9ee31e57faab56deac9a891160f6786db185f051433c  plan/DEVIATION_D1_stance_model.md
13ace9983e24418ebc8c8df1cd270a24c7931d93fc82cb1790a6cf477cedbcae  bt/events/events.csv
774758433c0e57e733fb6712000c4b6474a7ab1694ee811e135cb5531ebedad6  bt/events/events_columns.csv
b37fd1f5361b03caadc3f9832aa9d2057e4f92a42ccf717222d7065af3cd5013  bt/text/answers.parquet (pre-score)
350b05bd9db34aad8a6591b3d8385a30d765a1b13554f2d1abeb0a9f57a08821  bt/text/meetings.parquet (pre-score)
c8251485baf9b33fa36e19b9b1e03c9c4a174b50f2c03002f7a3c54f76d299fd  bt/text/build_meta.json
268aa049e1c3cc5076809d3add3e3376b49a357687c24165f75dc946818baefa  cache/ohlcv-1m__all_2016_2026.parquet
4081e89b25d0baa9841497eea2330652790b04431781816187aaf940ee4613af  cache/ohlcv-1s__all_2016_2026.parquet
8b3c1804d58bd4ff8de1f431f58fd9c2b3315e87a84b258c1b1b95eeea4c277c  cache/bbo-1s__all_2016_2026.parquet
0a71141a3541d10053ef328d35b721093fc7188fdd47b05ee768c7758b53a39f  bt/addendum/g3_operating_characteristics.py
c1ca408766b54872974d4ed6aa4b9ef948facd0982e65b03bcb777a031dbdb7b  bt/addendum/g3_operating_characteristics.json
```

The two text parquets will change when stance scores are filled in. The run records their new hashes together with
the scorer's id and sha256.
