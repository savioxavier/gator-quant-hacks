# Reading the Fed: Tone, Q&A Surprise and the Rates/USD Complex

**Gator Quant Hacks 2026, Systematic Trading track. Team quant note, DRAFT v1 (2026-10-03, review fixes applied).**
Code: https://github.com/savioxavier/gator-quant-hacks [[PENDING: final branch/tag and commit hash, after the code commit in Open items]]

---

> ## Status and page budget (delete before the PDF)
>
> **Exposure warning.** Section 5 quotes sealed press-conference outputs (BENCH-R, lexicon control) and v2 in-sample numbers. Under MERGED_FINAL_PLAN.md s3.11 (R2-35), a teammate who still has to ratify the H1 spec should not read Section 5, Table 1 or Table 2 until the ratification is recorded in PREREG-R. No H1 stance result is quoted anywhere in this draft.
>
> **Target:** 5 pages at 11pt with standard margins, including 2 figures and 2 tables. At about 560-600 words of prose per page, Tables 1-2 (about 0.65 page) and two figures (about 0.6 page) leave room for about **2,100-2,200 words of body text**. References and the appendix do not count, and judges need not read the appendix, so every required item must appear in the body.
>
> | Section | Target words | Now (v1) | Page | Rubric criterion served |
> |---|---|---|---|---|
> | Summary | 170 | 182 | 1 | all; mainly (2) Innovation |
> | Economic Hypothesis | 270 | 294 | 1 | (1) Economic foundation, (2) Innovation |
> | Data & Universe | 290 | 325 | 1-2 | (5) Evidence; data-hygiene rules |
> | Methodology | 480 | 587 | 2 | (2) Innovation, (5) Evidence |
> | Results, incl. captions (+ Table 1, Table 2, Fig. 1, Fig. 2) | 320 | 397 | 3 | (5) Evidence |
> | Risk Management | 260 | 282 | 4 | (3) Risk management |
> | Liquidity & Capacity | 200 | 187 | 4 | (4) Liquidity & capital |
> | Limitations & Next Steps (incl. failed ideas, AI line) | 270 | 297 | 5 | (5) Evidence, (1) honesty about the claim |
> | **Total body** | **~2,200** | **2,551** | | |
>
> Counts exclude tables, rubric lines, footnotes and placeholders (v0 was 2,841 on the same rule). About 350 words still have to go at layout; cut Methodology first (H1 paragraph, cost arithmetic), then Results prose, then Data. Filled placeholders will add words.
>
> **Guideline checklist**
>
> | Item | Status |
> |---|---|
> | Hypothesis written before any backtest (v2: HYPOTHESIS_v2.md; press conference: team plan + ADDENDUM + D1/D1a) | done; times and hashes in PREREG_LOG.md |
> | Pre-registration committed to git so its timestamp can be checked | done: team repo 537c483 at 23:11 UTC, after the v2 in-sample run (disclosed in PREREG_LOG.md), before any H1 result was viewed |
> | Backtest runner pinned to the current pre-registration hash and repointed to chrono scores | done: wire/run_v2_chrono.py checked 464f8a5b... (summary_is.json `prereg_sha256_checked`) |
> | Out-of-sample = last 2 years (2024-10-03..2026-10-02), not looked at, evaluated once | v2: not evaluated, decision rule failed. **PENDING team decision** on track-OOS reporting (option a or b, Open items #2) |
> | Every signal lagged (trade next bar) | done (spec and code checks) |
> | Net of commissions, spread and slippage; bps per trade stated and justified | done for the spec; press-conference fee ($2.00/side) unverified; TLT/UUP and 6E spread justification PENDING |
> | Results at 2x costs | v2 done (Table 1); BENCH-R and lexicon done (Table 2); H1 PENDING |
> | IS and OOS separately: annual return, vol, Sharpe, max DD, turnover, equity curve | v2 IS done (Table 1), OOS not evaluated; Fig. 1 to generate; BENCH-R max DD per era and Fig. 2 PENDING |
> | Failed-ideas list kept and reported | done (Section 8, Appendix A2); v2 added; some A2 rows still to trace to source files |
> | Survivorship, corporate actions, missing data addressed | done (Section 3) |
> | Every data source cited | done; CME ZT contract-spec URL, CME margin page, GDELT and Internet Archive terms PENDING |
> | **Code repo contains the code behind every result** | **PENDING, blocker:** v2 backtest, corpus builders and press-conference backtest are not in the team repo (Open items #3) |
> | Open-source libraries and published research cited | done; software versions from the lock file PENDING |
> | AI-tools disclosure | done (end of Section 8) |
> | Every team member can explain the strategy | PENDING (team walkthrough) |
> | Team ratifies which H1 execution spec governs (ADDENDUM vs MERGED_FINAL_PLAN.md s3.11, R2-04) and its sidedness | PENDING; must be recorded in PREREG-R before any H1 result is viewed |
> | Team decides whether people who opened the press-conference results/ folder can sign the attestation (merged plan R2-03) | PENDING |
> | Devpost: PDF + repo link by Sun 2026-10-04 10:00 ET; code pushes until 11:00 ET | PENDING |
>
> **Team notes on inconsistencies (resolve, then delete):**
> - Audio size: measured 9.7 GB, not the 2-3 GB in hpg/README.md.
> - Video size: team/data/fomc_pressers/README.md says about 65 GB; fetch_report.json says 67.4 GB (62.8 GiB in fed_presser_hpg/manifest/README.md). The note cites hours only; align the READMEs.
> - Databento cost: the re-priced pull cost **$8.53**. Do not cite the earlier GAP_REPORT quotes.
> - Stale text: strategies/01/review/README.md ("Next on this branch" still says FOMC-RoBERTa) and the fedspeak_v2 backtest/score READMEs (RoBERTa-blocked state, Amendment-1 hash).
> - Merged plan v2 A-35 says the hackathon entry is a different strategy and that this project starts 2026-10-05. That text predates the team's decision and should be marked superseded.
> - The ohlcv-1s / bbo-1s Databento purchase still needs the user's confirmation (merged plan v2 R2-03(1)). Check whether the Databento licence allows sharing raw bars between teammates; if not, share derived tables only.
> - No local path that contains the session scratch folder name may appear in the PDF. Use team-repo paths only.

---

## 1. Summary

*Rubric: all five criteria; foregrounds (2) Innovation. Target ~170 words.*

We test whether the Federal Reserve's own words predict US rates and the dollar after they become public. The **daily sleeve (v2)** scores every Board speech, FOMC statement, set of minutes and press-conference transcript from 2015 to 2026 (1,098 documents; 5,225 scored units including 2,026 Chair answers and the questions before them) for hawkish or dovish stance, decays the scores into a consensus and trades TLT against UUP (or 10-year Treasury futures against the euro) at the next bar. The **press-conference study** asks whether the Chair's Q&A, measured against the statement released 30 minutes earlier, moves 2-year Treasury futures after the answers end.

Three methodological extensions are new: yearly stance models trained only on text available before each year, with labels re-dated from source documents; answers timed against live TV captions instead of the 14:30 convention; press-conference costs from measured quotes. Both parts were pre-registered.

**Headline.** v2 failed its own decision rule: full in-sample net Sharpe 0.441, but 0.387 at 2x costs, below the 0.5 gate, so its out-of-sample window was not evaluated; our lexicon predecessor failed out of sample (-0.456). [[PENDING: H1 G3 GO/NO-GO and one-sentence verdict, from the ratified G3 code output]].

## 2. Economic Hypothesis

*Rubric: (1) Economic foundation, (2) Innovation. Target ~270 words.*

**Claim (v2, pre-registered).** Fed communication carries information about the future policy path that rates and the dollar absorb over days, not seconds; a hawkish consensus should predict falling Treasury futures and a rising dollar beyond what recent rate momentum explains.

**Why prices could adjust slowly.** Remarks are dated, often only by day, and hundreds of speeches a year make the Committee's centre of gravity a slow-moving state that no single release reveals. Positive voice tone in press conferences moves the S&P 500 about 75 bp per standard deviation over about five days (36 conferences, 10% significance) but only about 1 bp at the minute level (Gorodnichenko, Pham and Talavera, 2023); press-conference content correlates more strongly with the future policy rate than statements or speeches do (Byun et al., 2026). v2 replaces strategy 01's failed 40-word speech lexicon (median 3 hits per document) with a domain-trained stance model read over all official Board and FOMC text.

**Press-conference claim (H1).** Q&A answers reveal policy information the statement lacked; if markets absorb it over minutes, a Q&A hawkishness surprise should predict the 2-year futures move after the conference. The prior is low: the statement-window move predicted the press-conference move to January 2020 (correlation 0.58 for Eurodollars, 41 conferences; Gomez-Cram and Grotteria, 2022), this reversed under Powell after COVID (Narain and Sangani, 2026), and no paper we read shows predictability net of latency and costs. H1 is a measurement with one GO/NO-GO, benchmarked against a costed replication of that continuation (BENCH-R).

**Falsifiers (registered).** v2 fails if selection Sharpe ≤ 0.2 or validation Sharpe ≤ 0; if over half of in-sample P&L comes from 2022; if the momentum-orthogonalised signal (T3) is about zero while the raw ones (T1/T2) look good; or if net Sharpe ≤ 0 at 2x costs.

## 3. Data & Universe

*Rubric: (5) Evidence; survivorship, corporate actions and missing data. Target ~290 words.*

**Text.** From federalreserve.gov, with release times from the site's JSON feeds: 828 Board speeches (2015-01-01..2026-10-02; 828 of 828 index targets), 97 FOMC statements, 94 sets of minutes and 79 press-conference transcripts. Q&A: 2,026 Chair answers from the 75 transcripts of 2016-2026, timed by the Board's WebVTT captions (68 of 75); 95 conference recordings (82.4 h) are archived for H2/H3. Chair tenures (Board membership page): Yellen 2014-02-03..2018-02-03, Powell 2018-02-05..2026-05-22, Warsh from 2026-05-22. Labels: gtfintechlab/fomc_communication (Shah, Paturi and Chava, 2023; 2,480 sentences, CC BY-NC 4.0); base models: manelalab/chrono-bert-v1 yearly checkpoints (He et al., 2025; MIT); both on Hugging Face.

**Markets.** Daily: Databento GLBX.MDP3 futures (ZN, 6E, ZT, ES; volume-ranked front contract), TLT and UUP (Yahoo Finance), DTB3 and DGS2 (FRED). Intraday, 13:30-16:30 ET, on 75 press-conference dates (74 trading days with data; 73 scheduled meetings used; $8.53): Databento 1-minute and 1-second bars for ZT, ZF, ZN and ES, and 1-second best bid/offer for ZT, ZN and ES. ZT's tick fell from 1/128 to 1/256 of a point ($15.625 to $7.8125 per contract) in January 2019 (CME SER-8171); costs use the tick of the day. Our ZT moves correlate -0.995 (statement window) and -0.983 (press-conference window) with USMPD 2-year yield changes (Acosta et al., 2025).

**Hygiene.** *Survivorship:* instruments fixed in advance and trading throughout; documents are a census. *Corporate actions:* futures returns within one contract, an extra round trip charged on roll days; ETFs total-return adjusted (yfinance auto_adjust=True); intraday, one instrument per window, with ZT.c.0 replaced because it is the illiquid delivery-month contract on 42 of 73 meeting days. *Missing data:* nothing is filled with later data; the daily series have no missing closes; DGS2 is forward-filled from past values only and lagged two sessions; missing minutes are skipped. Meetings without captions (7), with distorted caption timelines (4) or outside the data window (2, March 2020) are dropped from timing tests, leaving 62 of 75. Two degraded Databento days are kept, with a registered sensitivity that drops them.

## 4. Methodology

*Rubric: (2) Innovation, (5) Evidence. Target ~480 words.*

**Stance model (walk-forward).** A document dated in year *Y* is scored only by model *Y*: the chrono-BERT checkpoint pretrained on text to 31 December of *Y*-1 (capped at 2024), fine-tuned only on labelled sentences whose *source document* predates *Y*. The dataset's year column disagrees with the source document for 2,336 of 2,480 rows; re-dating every row cuts verbatim train/test overlap for model 2015 from 491 rows to 21 (Appendix A3). Three seeds per year are averaged, with hyperparameters fixed in advance. A document's score is share-hawkish minus share-dovish over its sentences. Validation macro-F1 is 0.545-0.684 across the 36 models (A3), below the about 0.71 Shah et al. report for FOMC-RoBERTa.

**Signals and expressions (v2).** Consensus C_t = λC_{t-1} + Σ(scores first usable at t), λ = 2^(-1/20), as in strategy 01 except that every document injects (T4's lexicon leg keeps strategy 01's five-hit rule); expanding z-score, minimum 252 observations; a document dated *d* enters at the first session after *d*. **T1** speeches; **T2** all documents; **T3** T2 orthogonalised daily on the decayed, two-day-lagged DGS2 change (expanding point-in-time OLS); **T4** mean of the lexicon and model z-scores. **E1** 75% TLT / 25% UUP at the next open; **E2** 75% ZN / 25% short 6E at the next close. Eight combinations, sized to 10% volatility (Section 6).

**Costs.** E1: 1.5 bp (TLT) and 5 bp (UUP) per unit traded, plus 30 bp/yr borrow on short ETF weights [[PENDING: measured TLT/UUP quoted spreads justifying 1.5/5 bp, committed quote sample]]. E2: 1 bp per leg plus a round trip per roll; 1 bp is about 1.4 ZN half-spreads as measured around FOMC announcements (0.5 tick at about 111 points) and about four 6E half-spreads in a one-tick market (one tick is about 0.45 bp at 1.10) [[PENDING: verify against a 6E quote sample]]. The 2x rows double trading and roll costs.

**Protocol.** We choose the highest net Sharpe in the selection window (2016-01-04..2020-12-31) and proceed only if validation Sharpe (2021-01-04..2024-10-02) is above 0 and full in-sample Sharpe at 2x costs above 0.5. **Out-of-sample is the last two years, 2024-10-03..2026-10-02** (shorter than 20% of about 10.75 years), evaluated once, for the chosen combination only. The Deflated Sharpe uses 11 trials (Bailey and López de Prado, 2014). In a 40-seed random-score placebo the best-of-eight selection Sharpe averages 0.198 (90th percentile 0.833), so the validation and 2x gates do the real work. The pre-registration (sha256 464f8a5b...) and amendments were hashed before any v2 return and committed publicly (537c483, 23:11 UTC) after the v2 in-sample run and before any H1 result was viewed; Amendments 2-3 postdate strategy 01's out-of-sample verdict (A1).

**Press-conference clock and H1.** Conferences are anchored to live TV captions (GDELT TV API, CNBC and FOX Business; Internet Archive). The Board's caption video starts a median 28.8 s late (events table, n = 63), so under the 14:30:00 convention the "next bar after the answer" precedes our upper-bound bar on 40 of 62 meetings; our decision time is answer end plus start uncertainty (median 9.3 s). H1's surprise is the meeting's mean Q&A score minus the statement score, residualised on the 13:50-14:20 ZT move with chair intercepts; the trade is short ZT on a hawkish residual from the next 1-minute open after the conference to 16:00 ET. GO needs n ≥ 15 confirmation meetings, mean gross P&L above 0 and bootstrap p ≤ 0.05; MERGED_FINAL_PLAN.md s3.11 (R2-04) supersedes the ADDENDUM's one-sided sign-flip test with an HC3 t and restricted wild bootstrap, two-sided by default, and changes BENCH-R's exit and era rules [[PENDING: ratified spec and sidedness, recorded in PREREG-R before any H1 result is viewed; if both are computed, report both and name the ratified one as the decision]]. BENCH-R holds the sign of the 13:50-14:20 move from 14:20 to the conference end, split at 2020.

## 5. Results

*Rubric: (5) Performance & analytical evidence. Target ~320 words plus Tables 1-2 and Figures 1-2.*

**v2 daily sleeve.** Selection-window net Sharpes ranged from -0.582 (T1xE1) to 0.154 (T4xE1, chosen); all six combinations without the lexicon leg were negative. T4xE1 passed validation (0.687 > 0) but failed the 2x gate (full in-sample 0.387 < 0.5; gross 0.507), so the decision rule failed and the out-of-sample window was not evaluated [[PENDING: team decision on track-OOS reporting, Open items #2; any OOS row only after a dated deviation entry]]. Two of four registered falsifiers fire: selection Sharpe 0.154 ≤ 0.2, and 74% of in-sample P&L comes from 2022. It is not rate momentum (T3 tracks T2, correlation 0.975). Deflated Sharpe: 0.223 (selection), 0.436 (full in-sample). By chair (descriptive): Yellen 0.031, Powell 0.537; no Warsh days in-sample. As a fourth equal-risk sleeve of core_ER_6 it lowers the selection Sharpe (1.062 to 0.928) and raises validation (0.912 to 1.185) and full in-sample (0.998 to 1.038). The model added little: T4's validation Sharpe (0.687) equals the frozen lexicon's (Variant A, 0.691), so our contribution is methodological, not a return improvement.

**Table 1. v2 T4xE1 and references: net, excess over T-bill, 1x costs except Sharpe 2x; arithmetic annualised return.** Source: [[PENDING: repo paths of windows_all.csv and the strategy 01 review outputs]].

| Window | Ann. excess return (arith.) | Volatility | Sharpe 1x | Sharpe 2x | Max DD | Turnover (x/yr) |
|---|---|---|---|---|---|---|
| IS selection 2016-01-04..2020-12-31 | 1.25% | 8.1% | 0.154 | 0.053 | -16.1% | 35.0 |
| IS validation 2021-01-04..2024-10-02 | 10.00% | 14.6% | 0.687 | 0.664 | -17.8% | 15.9 |
| IS full 2016-01-04..2024-10-02 | 5.00% | 11.3% | 0.441 | 0.387 | -18.8% | 26.8 |
| **OOS 2024-10-03..2026-10-02** | **not evaluated; the pre-registered decision rule failed (full-IS Sharpe at 2x costs 0.387 < 0.5)** | | | | | |
| *Variant A (frozen lexicon), IS full 2016-01-04..2024-10-02* | 4.18% | 11.8% | 0.355 | 0.312 | -20.7% | 23.2 |
| *Strategy 01, IS 2011-12-30..2024-10-02* | 2.34% | 11.2% | 0.210 | 0.162 | -33.5% | 24.5 |
| *Strategy 01, OOS 2024-10-03..2026-10-02* | -4.97% | 10.9% | -0.456 | -0.502 | -15.6% | 23.3 |

**Press-conference study.** BENCH-R reproduces the pre-2020 continuation in sign, not significance (+$27.73 per contract per meeting gross, t 0.94, n = 20), then reverses (-$35.31, t -1.15, n = 50; 2022 alone -$267.58 per meeting); the break has Narain and Sangani's (2026) sign but p = 0.146. Pre-2020 break-even cost is $15.63 per side (1.0 tick, 2016-18) and $11.23 (1.4 ticks, 2019), against a measured half-spread of half a tick. The frozen-lexicon negative control is null (NO-GO; 90% CI upper bound 0.60 ticks). Annualised Sharpe is withheld by pre-registration (ADDENDUM s5) because eight events a year give a meaningless estimate; per era we report the equity curve (Fig. 2), turnover (about 8 round trips a year) and maximum drawdown [[PENDING: BENCH-R max drawdown of cumulative P&L per contract, per era, from benchr_trades.csv]]. [[PENDING: H1-primary G3 result and robustness rows, from the ratified G3 code output]]. [[PENDING: H2/H3 voice/face results, run only if G3 = GO]].

**Table 2. Press-conference tests, ZT, USD per contract per meeting.** H1 and lexicon: next 1-minute open after the conference to 16:00 ET; BENCH-R: 14:20 to conference end. H1 n are eligible meetings; no Sharpe for H1 (1-minute prints, associational). OOS slice: all eligible meetings dated 2024-10-03..2026-10-02; H1 has no Warsh rows (Warsh is text-only, descriptive). Source: [[PENDING: repo path of the press-conference backtest outputs]].

| Test (sample) | n | Gross | Measured cost | 2 ticks/side | 4 ticks/side | t (gross) | Status |
|---|---|---|---|---|---|---|---|
| H1-primary, stance (Powell confirmation 2023-02-01..2026-04-29) | 20 eligible | [[PENDING: G3 output]] | [[PENDING: G3 output]] | [[PENDING: G3 output]] | [[PENDING: G3 output]] | [[PENDING: G3 output]] | G3 decision, blind |
| H1-primary, stance, OOS slice (no Warsh rows) | 12 eligible | [[PENDING: H1 output]] | [[PENDING: H1 output]] | [[PENDING: H1 output]] | [[PENDING: H1 output]] | [[PENDING: H1 output]] | descriptive |
| H1-primary, stance, 2016-2022 clean sample (positions from 2018-03-21, after the 8-meeting burn-in) | [[PENDING: ≤31 eligible, H1 output]] | [[PENDING: H1 output]] | [[PENDING: H1 output]] | [[PENDING: H1 output]] | [[PENDING: H1 output]] | [[PENDING: H1 output]] | descriptive |
| Lexicon control (confirmation) | 20 | -$32.03 | -$39.84 | -$63.28 | -$94.53 | -1.47 | NO-GO, as expected |
| BENCH-R 2016-2019 | 20 | +$27.73 | +$15.23 | -$22.27 | -$72.27 | 0.94 | non-blind replication |
| BENCH-R 2020-2026 | 50ᵃ | -$35.31 | -$43.13 | -$66.56 | -$97.81 | -1.15 | non-blind replication |
| BENCH-R, OOS slice (incl. 3 Warsh)ᵇ | 15 | +$22.40 | +$14.58 | -$8.85 | -$40.10 | 0.52 | non-blind; not OOS |
| BENCH-R, Warsh conferences only | 3 | [[PENDING: from benchr_trades.csv]] | [[PENDING: from benchr_trades.csv]] | [[PENDING: from benchr_trades.csv]] | [[PENDING: from benchr_trades.csv]] | n/r | descriptive |

ᵃ 50 of 53 meetings; three with a zero statement-window sign (2020-09-16, 2023-07-26, 2026-01-28) take no trade. ᵇ Includes the three Warsh conferences; excludes 2026-01-28 (zero sign).

**Figure 1.** T4xE1 cumulative net excess return at 1x and 2x costs, in-sample only (selection and validation shaded), Variant A dashed; no out-of-sample segment, because the decision rule failed. [[PENDING: generate from daily_T4xE1_is.parquet; repo path of the plotting script]].

**Figure 2.** BENCH-R cumulative P&L per contract by era, gross and net of measured cost. [[PENDING: generate from benchr_trades.csv; the half-spread panel is in A5 and returns as panel (b) if space allows; replaced by the event-time ZT response if H1 passes G3]].

## 6. Risk Management

*Rubric: (3) Risk management plan. Target ~260 words.*

**Position limits (fixed before testing).** The z-score is clipped at ±2. Size targets 10% annualised volatility (mean of 20- and 60-day realised volatility of the traded mix, 4% floor). Gross exposure is capped at 1.5x capital. Rebalances under 10% of current gross are skipped, except on FOMC days, the day after, and from flat.

**Event risk.** The rates leg is halved over each FOMC announcement session. Eight unscheduled actions and releases (2019-10-11, six dates in 2020, 2025-08-22) are also de-risked, as registered. They were not announced in advance, so this is a small use of hindsight (deviation D-1); a scheduled-only list changes the full in-sample Sharpe from 0.441 to 0.442.

**Model risk.** T3 guards against rate momentum (strategy 01's consensus correlated 0.53 with the 2-year yield; alpha over it 2.3%/yr, t 0.84); v2's T3 tracks T2, so that falsifier does not fire. Three seeds limit fine-tuning noise. The 2x gate and Deflated Sharpe, which guard against cost and selection optimism, rejected v2; the 2022 concentration falsifier also fired (74%; strategy 01: 75%).

**Stress and diversification.** Worst in-sample drawdown of the chosen sleeve: -18.8%. Stress case: strategy 01's worst out-of-sample quarter (Q4 2024, -11.8%). In-sample correlation with core_ER_6 (vol-managed ES, month-end ZN and broad trend; 6% overlay, leverage cap 4): 0.025.

**Press-conference trades.** One contract, entered after the upper-bound decision time, flat by 16:00, no trade on a zero statement-window sign. Live use is gated (G5): paper trading only after a G3 GO, only if the measured live p90 delay is 60 s or less, at half size under the new Chair.

**Not pre-registered.** There is no drawdown stop and no monitoring rule, because v2 failed its decision rule and is not deployed.

## 7. Liquidity & Capacity

*Rubric: (4) Liquidity & capital deployment. Target ~200 words.*

**Chosen expression (E1).** TLT trades about $2.75bn a day but UUP only about $33m [[PENDING: committed script and output for ETF daily dollar volumes]]. At the 1.5x cap, $10m of capital holds up to $3.75m of UUP, about 11% of a day's volume, so the chosen sleeve's capacity is bound by UUP at roughly $10m. In-sample turnover was 26.8x a year.

**Scalable alternative (E2).** T4xE2 is similar in-sample (selection 0.151, validation 0.707, full 0.453, 2x 0.377; 2.75% a year at 6.1% volatility, maximum drawdown -12.4%, turnover 46.0x). Over 2024-26, median daily front-contract volume was about $184bn in ZN and $22bn in 6E [[PENDING: committed script and output, Databento daily bars]]. At the cap, $100m holds $112.5m of ZN (about 1,000 contracts) and $37.5m of 6E, 0.06% and 0.17% of a median day. E2 needs only futures margin [[PENDING: ZN and 6E initial margin, CME margin page, with retrieval date]]; the rest earns the T-bill rate, which is why returns are reported in excess of it.

**Press-conference trades.** ZT traded a median 2,108 contracts per minute (10th percentile 529) from 14:30 to 16:00 on 2023-26 conference days [[PENDING: committed script and output, 1-minute bars, 30 conference days]], and the quoted market was one tick wide [[PENDING: record-weighted share of bbo-1s quotes, ZT 2023-26; preliminary 97.0%, needs a committed script]] of the time. One contract is negligible; 5% of a 10th-percentile minute is about 26 contracts (~$5m notional) [[PENDING: depth check; no MBP-1 data were bought]].

## 8. Limitations & Next Steps

*Rubric: (5) Evidence, (1) honesty about the claim; failed-ideas rule. Target ~270 words.*

**Known risks to the claim.** *Volume drift:* v2 keeps the decayed sum that sank strategy 01; speech counts rose from 44 (2016) to 117 (2025), and every document injects. *Power:* with 20 meetings, P(GO) for H1 is 0.29 even at a true correlation of 0.3, so a NO-GO is weak evidence. *Labels:* annotated in 2022-23 with hindsight; labels and fine-tuned models are non-commercial (CC BY-NC 4.0). *Timing:* no true wall clock (TV delay assumed 11 s, plausible 3-20 s); H1 fills use 1-minute trade prints, not quotes. *Exposure and code:* BENCH-R is non-blind, a script has read the lexicon control's 2023-26 outcome windows, and ADDENDUM-path H1 code is usable only after the final plan's changes are made and hashed.

**Samples and the OOS rule.** H1's blind confirmation sample (Powell, 2023-02-01..2026-04-29, 20 eligible meetings; fixed because the originally registered scorer's labels end in 2022) overlaps v2's validation and OOS windows and is not the track's OOS window, so Table 2 reports the OOS slice and the Warsh conferences separately, as descriptive.

**Failed ideas (net; sources in Appendix A2).** v2 T4xE1 (2x 0.387 < 0.5; OOS not evaluated); strategy 01 (OOS -0.456; Q4 2024 -11.8%); overnight drift (ES; 1x 0.25, 2x -0.24); intraday momentum (ES; -0.31); pre-FOMC drift (ES; -4.3 bp per event in 2024-26); hourly trend (-0.65); Treasury auction cycle (validation -0.38); GTAA timing (beat untimed holding in 9.7% of configurations in 2024-26); futures carry, value and EWMAC trend (negative after publication or costs).

**Next steps.** NTP-logged recordings of the 2026-10-28 and 2026-12-09 conferences to measure the clock and live delay; H2/H3 only if G3 = GO; a consensus normalised by document count, testable after 2026-10; FOMC-RoBERTa if access is granted.

*AI coding assistants were used; the team reviewed and is responsible for all code and claims.*

---

## References (outside the page limit)

**Papers**
- Acosta, M., et al. (2025). U.S. Monetary Policy Event-Study Database (USMPD). Federal Reserve Bank of San Francisco Working Paper 2025-30. https://www.frbsf.org/wp-content/uploads/wp2025-30.pdf
- Asness, C., Moskowitz, T., Pedersen, L. H. (2013). Value and momentum everywhere. *Journal of Finance* 68(3).
- Bailey, D. H., López de Prado, M. (2014). The deflated Sharpe ratio. *Journal of Portfolio Management* 40(5).
- Baltussen, G., Da, Z., Lammers, S., Martens, M. (2021). Hedging demand and market intraday momentum. *Journal of Financial Economics* 142(1).
- Boyarchenko, N., Larsen, L., Whelan, P. (2020). The overnight drift. Federal Reserve Bank of New York Staff Report 917.
- Byun, R., Fees, B., Jacobson, M. M., Walker, T. B. (2026). The Fed's fine-tune: Coarse statements and predictive pressers. Working paper, July 2026. https://margaretjacobson.github.io/CV/BFJW-Fed-Fine-Tune.pdf
- Curti, F., Kazinnik, S. (2023). Let's face it: Quantifying the impact of nonverbal communication in FOMC press conferences. *Journal of Monetary Economics* 139: 110-126. [[PENDING: numbers verified on the 2021 working paper only; check against the published version]]
- Faber, M. (2007). A quantitative approach to tactical asset allocation. *Journal of Wealth Management* 9(4).
- Fleming, M., Liu, W., Nguyen, G. (2026). Intraday price pressure and order flow around U.S. Treasury auctions. Federal Reserve Bank of New York Staff Report 1188. doi:10.59576/sr.1188
- Gao, L., Han, Y., Li, S. Z., Zhou, G. (2018). Market intraday momentum. *Journal of Financial Economics*.
- Gomez-Cram, R., Grotteria, M. (2022). Real-time price discovery via verbal communication: Method and application to Fedspeak. *Journal of Financial Economics* 143(3): 993-1025. doi:10.1016/j.jfineco.2021.12.004
- Gorodnichenko, Y., Pham, T., Talavera, O. (2023). The voice of monetary policy. *American Economic Review* 113(2): 548-584. doi:10.1257/aer.20220129
- Hartley, J., Schwarz, K. (2019). Predictable end-of-month Treasury returns. Working paper.
- He, S., Lv, L., Manela, A., Wu, J. (2025). Chronologically consistent large language models. arXiv:2502.21206.
- Hurst, B., Ooi, Y. H., Pedersen, L. H. (2017). A century of evidence on trend-following investing. *Journal of Portfolio Management* 44(1).
- Koijen, R., Moskowitz, T., Pedersen, L. H., Vrugt, E. (2018). Carry. *Journal of Financial Economics* 127(2).
- Kurov, A., Wolfe, M. H., Gilbert, T. (2021). The disappearing pre-FOMC announcement drift. *Finance Research Letters* 40. doi:10.1016/j.frl.2020.101781
- Lou, D., Yan, H., Zhang, J. (2013). Anticipated and repeated shocks in liquid markets. *Review of Financial Studies* 26(8).
- Lucca, D. O., Moench, E. (2015). The pre-FOMC announcement drift. *Journal of Finance* 70(1).
- McLean, R. D., Pontiff, J. (2016). Does academic research destroy stock return predictability? *Journal of Finance* 71(1). doi:10.1111/jofi.12365
- Narain, N., Sangani, K. (2026). The market impact of Fed communications: The role of the press conference. *International Journal of Central Banking* 22(1): 313-389.
- Newey, W., West, K. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica* 55(3).
- Shah, A., Paturi, S., Chava, S. (2023). Trillion dollar words: A new financial dataset, task & market analysis. *Proceedings of ACL 2023*. doi:10.18653/v1/2023.acl-long.368

**Data sources**
- Board of Governors of the Federal Reserve System (2026). Speeches, FOMC statements, minutes, press-conference transcripts, videos and WebVTT captions; FOMC calendars; JSON feeds ne-speeches.json and ne-press.json. https://www.federalreserve.gov (retrieved 2026-10-03; US government works, public domain).
- Board of Governors of the Federal Reserve System (2026). Board membership page (chair tenures). https://www.federalreserve.gov/aboutthefed/bios/board/boardmembership.htm (retrieved 2026-10-03).
- CME Group (2019). Notice SER-8171: ZT minimum tick change. https://www.cmegroup.com/notices/ser/2019/01/SER-8171.html
- CME Group (2026). 2-Year T-Note futures (ZT) contract specifications ($200,000 face value; tick values $15.625 and $7.8125). [[PENDING: URL and retrieval date]]
- CME Group (2026). Margins for ZN and 6E. [[PENDING: URL, retrieval date and values]]
- Databento (2026). CME Globex MDP 3.0 (GLBX.MDP3): ohlcv-1d, ohlcv-1m, ohlcv-1s, bbo-1s. https://databento.com/docs/schemas-and-data-formats/ohlcv (licensed; not redistributed).
- Federal Reserve Bank of St. Louis (2026). FRED series DTB3, DGS2. https://fred.stlouisfed.org
- Federal Reserve Bank of San Francisco (2026). USMPD.xlsx, README updated 17 Sep 2026. https://www.frbsf.org/wp-content/uploads/USMPD.xlsx (underlying data: LSEG Tick History).
- GDELT Project (2026). Television API 2.0. Internet Archive (2026). TV News Archive item pages. [[PENDING: terms/licence statements]]
- gtfintechlab (2023). fomc_communication dataset, revision 6b0283f5 (CC BY-NC 4.0), hosted on Hugging Face; fomc-hawkish-dovish repository, commit 98646987, GitHub.
- manelalab (2025). chrono-bert-v1-<YYYY>1231 checkpoints (MIT), hosted on Hugging Face.
- Yahoo Finance via yfinance (2026). TLT, UUP daily prices, adjusted.

**Software**
- NLTK 3.10.3; PyTorch 2.11.0; Hugging Face Transformers 5.18.0; pandas; statsmodels; xpdf pdftotext 4.06; ffmpeg. [[PENDING: final versions from the requirements lock file]]

---

## Appendix (outside the page limit; judges need not read it)

**A1. Pre-registration and deviation log.** Times from PREREG_LOG.md, which also records the SHA-256 of each file at each time. The v2 claim and Amendment 1 precede the commit of strategy 01's out-of-sample verdict (20:26 UTC); Amendments 2 and 3 follow it, so the team knew how a lexicon signal had done in 2024-26 before those amendments. v2 did not adopt the obvious post-hoc fix of normalising by document count. The public commit followed the v2 in-sample run; PREREG_LOG.md discloses this.

| Time (UTC, 2026-10-03) | Document | Change | Before any return? |
|---|---|---|---|
| 19:52 | HYPOTHESIS_v2.md | v2 claim, signals T1-T4, expressions E1/E2, windows, gates, falsifiers | yes |
| 19:53 | Amendment 1 | 2016+ window (2015 warm-up), by-chair reporting | yes |
| 20:26 | team repo bf880da | strategy 01 replication and OOS verdict committed | n/a |
| 21:12 (logged; the file text says about 21:20) | Amendment 2 / Deviation D1 | gated FOMC-RoBERTa (401 at 16:47 ET) replaced by walk-forward chrono-BERT | yes |
| 21:35 | v2 clarification | 2015 warm-up documents scored with the 2015 model | yes |
| 21:45 | press-conference ADDENDUM | H1-primary, BENCH-R and G3 made operational | yes for H1 stance; BENCH-R non-blind |
| 21:50 | Amendment 3 / D1a | labels re-dated from source documents (sha256 464f8a5b...) | yes |
| 22:37 | team repo 0fd707f | Amendment 3 code committed | yes |
| 22:40 | DEVIATIONS.md D-1, D-2 | unscheduled de-risk dates kept as registered; T3 scaling | yes |
| about 23:10 | v2 in-sample run | decision rule failed; oos_not_evaluated.json written | n/a |
| 23:11 | team repo 537c483 | public commit of the pre-registration records, ADDENDUM, D1 and team plan | after the v2 IS run; before H1 results |
| [[PENDING: time]] | PREREG-R | ratified H1 G3 spec and sidedness; track-OOS decision for v2; attestations | must precede viewing any H1 result |

**A2. Failed ideas (full).** [[PENDING: source file path in the repo for each row; recheck the rows not yet traced: GTAA 9.7% of 72, carry 0.03/0.25, value COMBO 0.23/-0.60, EWMAC -0.135/-0.54/8.6%, turn-of-month t 0.06 and ZN -1.07, intraday momentum 49% in 50 days, pre-FOMC 70%]]

| Idea | Key numbers (net) | Why it failed |
|---|---|---|
| v2 T4xE1 (lexicon + walk-forward stance model, TLT/UUP; pre-registered) | selection 0.154, validation 0.687, full IS 0.441 (2x 0.387 < 0.5); OOS not evaluated | decision rule failed; 74% of IS P&L from 2022; stance-model-only signals negative in selection |
| Strategy 01 (Board-speech lexicon tone, TLT/UUP) | IS 0.210 (0.060 ex-2022), OOS -0.456; bootstrap IS 90% [-0.20, 0.60] | speech volume drove the decayed sum; 75% of IS P&L from 2022; alpha over rate momentum t 0.84 |
| Strategy 01, futures version | IS 0.36, OOS 0.10 (ZN leg 0.005) | half the gain was a slower fill; the cap bound on 54% of days |
| Overnight drift, ES | gross 0.75, 1x 0.25, 2x -0.24 | costs |
| Intraday momentum, ES | gross 0.52, 1x -0.31 | gross 1.26 bp/trade vs 1 bp cost; 49% of P&L in 50 days of 2020 |
| Pre-FOMC drift, ES | 1x 11.9 bp/event IS; -4.3 bp in 2024-26 | 70% of gross from 2020+2022; negative before 2015 and after 2024 |
| Hourly vs daily trend | hourly 1x -0.65 | costs, no edge |
| Month-end ZN intraday timing | no variant beat the daily hold (0.866) | no improvement |
| Treasury auction cycle (futures, pre-registered) | selection 0.77, validation -0.38 | failed all three adoption rules |
| GTAA timing | later window: timing beat untimed in 9.7% of 72 configs | no robust value |
| Futures carry (XS / TS) | 0.03 / 0.25 IS; post-publication ~0 | decay |
| Value / value+momentum | COMBO 0.23 IS, -0.60 later | decay |
| EWMAC trend (trade-ngin style) | -0.135 IS, -0.54 OOS | cost drag 8.6%/yr |
| Turn-of-month ES, ZN and gold premia | alpha t 0.06; ZN later -1.07 | no edge |
| Press conference: lexicon H1 (control) | -$32.03 per contract per meeting gross (-4.1 ticks), NO-GO | expected null |
| Press conference: BENCH-R after 2020 | -$35.31 per contract per meeting | regime reversal (Narain and Sangani, 2026) |

Prior evidence from a team member's separate entry (a different strategy, cited only for cost realism): at the hacker guide's example costs, that book's Sharpe falls to 0.28 IS / -1.05 OOS.

**A3. Stance-model settings and diagnostics.** 15% stratified validation split (seed 0); learning rate 2e-5; batch 16; max length 256; at most 8 epochs with patience 2 on macro-F1; weight decay 0.01; 10% warmup; seeds 42/43/44; bf16 training, fp32 scoring. NLTK Punkt sentence splitting per paragraph. Training rows per model year: 1,606 (2015) to 2,480 (2023-2026). Validation macro-F1 by model year, mean of 3 seeds: 2015 0.577, 2016 0.618, 2017 0.611, 2018 0.584, 2019 0.579, 2020 0.624, 2021 0.650, 2022 0.613, 2023 0.652, 2024 0.664, 2025 0.661, 2026 0.660 (range over the 36 models 0.545-0.684; models/<Y>/seed_<S>/metrics.json). Label re-dating: the dataset's year column disagrees with the source document's year for 2,336 of 2,480 rows (median gap 7 years); every row was re-dated from the authors' per-document files. Under the literal dataset years, 491 training rows for model 2015 reappear verbatim in documents dated 2015 or later; under the corrected dates, 21 do, all sentences first published earlier and repeated later. 36 fine-tunes on a local RTX 5090 (the scores used); [[PENDING: HiPerGator replication (UF Research Computing), if run]].

**A4. Verification.** Statement release times from the JSON feeds match each page's "For release at" line in every case. Two independent v2 implementations agree to about 1e-15 on placebo scores and catch the same injected-leak canaries. Rebuilding with data cut at 2019-06-28 leaves every earlier signal and weight unchanged. An independent re-implementation of the press-conference backtest reproduces decision times, trade counts (285 of 285 BENCH-R trades across ZT, ZF, ZN and ES for one exit: 70 + 72 + 72 + 71) and P&L exactly.

**A5. Additional figures.** [[PENDING: (a) median ZT/ZN/ES half-spread by minute relative to conference start (-60 to +90 min), from spreads_by_presser_phase.csv; (b) timing-offset histogram (caption video zero minus scheduled start, n = 63); (c) strategy 01 OOS drawdown with Q4 2024 highlighted; (d) selection Sharpes of the 8 combinations against the placebo best-of-8 distribution]].

---

## Open items before submission (delete before the PDF)

Deadline: PDF and repo link on Devpost by **Sun 2026-10-04 10:00 ET**; code pushes until 11:00 ET. Owners are roles until the team assigns names.

**Results to drop in**

| # | Item | Where in the note | What produces it | Who |
|---|---|---|---|---|
| 1 | Ratified H1 G3 spec and sidedness (ADDENDUM vs MERGED_FINAL_PLAN.md s3.11), attestations, and who may still ratify | Section 4, A1, checklist | PREREG-R entry, dated and committed | team (ratifiers who have not read Section 5) |
| 2 | Track-OOS decision for v2: (a) report "not evaluated, per the pre-registered gate" and use strategy 01's OOS as the tone family's only OOS evidence; or (b) a dated deviation that evaluates T4xE1 once on 2024-10-03..2026-10-02 for track compliance, labelled outside the decision rule and unable to rescue it, reported whatever it shows | Section 5, Table 1, Fig. 1 | team decision in PREREG-R first; for (b) only, one run of the v2 runner in OOS mode | team; runner operator |
| 3 | Code behind every result committed to the team repo (v2 backtest run_v2.py, v2lib.py, wire/, corpus builders; press-conference backtest, events, text, verify and ADDENDUM code), with no licensed Databento data and no scratch paths | header, every caption | git commit and push to review/strategy-01 | holder of the local outputs |
| 4 | H1-primary G3 result and robustness rows; OOS-slice and 2016-2022 rows | Summary headline, Section 5, Table 2 | ratified G3 code, run once after item 1 | runner operator |
| 5 | H2/H3 voice/face results | Section 5 | only if G3 = GO; otherwise write "not run (G3 NO-GO)" | HiPerGator pipeline operator |
| 6 | BENCH-R max drawdown per era and the 3 Warsh rows | Section 5, Table 2 | short script on benchr_trades.csv | runner operator |
| 7 | Measured TLT/UUP spreads; 6E quote check; ZN and 6E CME margins with date; press-conference fee check ($2.00/side) | Sections 4 and 7 | quote-sample script; CME margin and fee pages | any teammate |
| 8 | ETF and futures daily dollar volumes; ZT contracts per minute; one-tick share (record-weighted) | Section 7 | committed script plus output over the cached bars | any teammate |
| 9 | Final branch/tag and commit hash; software versions from the lock file; CME ZT contract-spec URL; GDELT and Internet Archive terms; Curti and Kazinnik check; A2 source paths and rechecks | header, References, A2 | git; requirements lock; source pages | any teammate |

**Figures to generate**
- Fig. 1: T4xE1 cumulative net excess return at 1x and 2x, IS only, windows shaded, Variant A dashed (daily_T4xE1_is.parquet, windows_all.csv). If option (b) runs, add the OOS segment after a vertical line.
- Fig. 2: BENCH-R cumulative P&L per contract by era, gross and net of measured cost (benchr_trades.csv); or the event-time ZT response if H1 passes.
- A5 (a)-(d) as listed; (a) first, since it may return to the body.

**Order of work tonight (Sat 2026-10-03, ET; times are a plan)**
1. **Now to 21:00.** Items 1 and 2: record PREREG-R before anyone opens an H1 result; ratifiers do not read Section 5 or Tables 1-2 until then. Start item 3 (code commit) in parallel.
2. **21:00-22:30.** Item 4 (run H1 once on the ratified code) and, if (b) was chosen, the single OOS run. Items 6-8 alongside (small scripts; no new decisions).
3. **22:30-00:00.** Figures 1 and 2; fill Tables 1-2 and the Summary headline. Item 5 is feasible tonight only if G3 = GO and the pipeline is ready; otherwise write "not run".
4. **00:00-01:30.** Render to PDF at 11pt with standard margins; cut the body to five pages including tables and figures (about 350 words over at v1: Methodology first, then Results prose, then Data); check that no scratch path and no placeholder remains.
5. **Sun 08:00-09:00.** Team walkthrough: every member explains the strategy, the failed decision rule and the H1 result.
6. **Sun 09:00-09:45.** Item 9; delete the status box and this list; final commit and push; put the final hash in the header; upload the PDF and repo link to Devpost before 10:00 ET. Code pushes close at 11:00 ET.
