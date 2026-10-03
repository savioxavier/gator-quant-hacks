# Reading the Fed: Tone, Q&A Surprise and the Rates/USD Complex

**Gator Quant Hacks 2026, Systematic Trading track. Team quant note, DRAFT v0 (2026-10-03).**
Code: https://github.com/savioxavier/gator-quant-hacks [[PENDING: final branch/tag and commit hash]]

---

> ## Status and page budget (delete before the PDF)
>
> **Target:** 5 pages at 11pt with standard margins, including 2 figures and 2 tables. That leaves about **2,300-2,600 words of body text**. References and the appendix do not count, and judges need not read the appendix, so every required item must appear in the body.
>
> | Section | Target words | Page | Rubric criterion served |
> |---|---|---|---|
> | Summary | 170 | 1 | all; mainly (2) Innovation |
> | Economic Hypothesis | 300 | 1 | (1) Economic foundation, (2) Innovation |
> | Data & Universe | 330 | 1-2 | (5) Evidence; data-hygiene rules |
> | Methodology | 520 | 2 | (2) Innovation, (5) Evidence |
> | Results (+ Table 1, Table 2, Fig. 1, Fig. 2) | 320 | 3 | (5) Evidence |
> | Risk Management | 300 | 4 | (3) Risk management |
> | Liquidity & Capacity | 220 | 4 | (4) Liquidity & capital |
> | Limitations & Next Steps (incl. failed ideas) | 330 | 5 | (5) Evidence, (1) honesty about the claim |
> | **Total body** | **~2,490** | | |
>
> **Guideline checklist**
>
> | Item | Status |
> |---|---|
> | Hypothesis written before any backtest (v2: HYPOTHESIS_v2.md; press conference: team plan + ADDENDUM + D1/D1a) | done (timestamps are recorded inside the files only) |
> | Pre-registration committed to git so its timestamp can be checked | **PENDING, blocker.** HYPOTHESIS_v2.md is gitignored in gqh-systematic and absent from the team repo; the Amendment 3 code is uncommitted. Commit both before any chrono score is joined to returns |
> | Backtest runner pinned to the current pre-registration hash and repointed to chrono scores | **PENDING.** run_v2.py asserts the Amendment-1 hash 6083d3ef... and reads the RoBERTa score file; the current hash is 464f8a5b... |
> | Out-of-sample = last 2 years (2024-10-03..2026-10-02), not looked at, evaluated once | defined; evaluation PENDING |
> | Every signal lagged (trade next bar) | done (spec and code checks) |
> | Net of commissions, spread and slippage; bps per trade stated and justified | done for the spec; the press-conference fee ($2.00/side) is an unverified estimate, PENDING |
> | Results at 2x costs | spec done; numbers PENDING |
> | IS and OOS separately: annual return, vol, Sharpe, max DD, turnover, equity curve | PENDING (Table 1, Fig. 1) |
> | Failed-ideas list kept and reported | done (Section 8, Appendix A2) |
> | Survivorship, corporate actions, missing data addressed | done (Section 3) |
> | Every data source cited | done; licence statements for USMPD, GDELT and Internet Archive PENDING |
> | Open-source libraries and published research cited | done |
> | AI-tools disclosure | done (Section 4) |
> | Every team member can explain the strategy | PENDING (team walkthrough) |
> | Team ratifies which H1 execution spec governs (ADDENDUM vs merged plan v2 R2-04) | PENDING; must happen before stance scores are joined to returns |
> | Team decides whether people who opened the press-conference results/ folder can sign the attestation (merged plan R2-03) | PENDING |
> | Devpost: PDF + repo link by Sun 2026-10-04 10:00 ET; code pushes until 11:00 ET | PENDING |
>
> **Team notes on inconsistencies (resolve, then delete):**
> - Clock bias: use **+28.8 s** median (events table, n=63, TV-anchored) or GAP_REPORT A-02's +24 s (n=61, archive check), and name which. This draft uses +28.8 s.
> - Model count: the code defaults to 2015-2026 x 3 seeds = **36** fine-tunes; nlp/README.md and hpg/README.md still say 33.
> - Audio size: measured 9.7 GB, not the 2-3 GB in hpg/README.md.
> - Databento cost: the re-priced pull cost **$8.53**. Do not cite the earlier GAP_REPORT quotes.
> - GPU allocation: stance jobs ran under ai-workshop (4 RTX PRO 6000 at a time); the jie.xu group cap is 2 GPUs. Say which allocation ran each job.
> - Stale text: strategies/01/review/README.md ("Next on this branch" still says FOMC-RoBERTa) and the fedspeak_v2 backtest/score READMEs (RoBERTa-blocked state, Amendment-1 hash).
> - Merged plan v2 A-35 says the hackathon entry is a different strategy and that this project starts 2026-10-05. That text predates the team's decision and should be marked superseded.
> - The ohlcv-1s / bbo-1s Databento purchase still needs the user's confirmation (merged plan v2 R2-03(1)). Check whether the Databento licence allows sharing raw bars between teammates; if not, share derived tables only.
> - No local path that contains the session scratch folder name may appear in the PDF. Use team-repo paths only.

---

## 1. Summary

*Rubric: all five criteria; foregrounds (2) Innovation. Target ~170 words.*

We test whether the Federal Reserve's own words predict US rates and the dollar after they become public. The strategy has two parts. The **daily sleeve (v2)** scores every Board speech, FOMC statement, set of minutes and press-conference transcript from 2015 to 2026 (1,098 documents; 5,225 including individual Q&A turns) for hawkish or dovish stance. It decays the scores into a consensus and trades 10-year Treasury futures against the euro (or TLT/UUP) at the next bar. The **press-conference study** asks a narrower question: does the Chair's Q&A, measured against the statement released 30 minutes earlier, move 2-year Treasury futures after the answers end? It is benchmarked against a costed replication of Gomez-Cram and Grotteria (2022).

Three extensions of published work are new here. Each year's language model is pretrained and fine-tuned only on text available before that year, using labels we re-dated from source documents. Press-conference answers are timed against live TV captions instead of the 14:30 convention. Costs come from measured quotes, not assumptions. Both parts were pre-registered. Our predecessor strategy failed out of sample, and we report that failure in full.

Headline: [[PENDING: chosen v2 combination; IS and OOS net Sharpe at 1x/2x; H1 G3 GO/NO-GO; one-sentence verdict]].

## 2. Economic Hypothesis

*Rubric: (1) Economic foundation, (2) Innovation. Target ~300 words.*

**Claim (v2, pre-registered).** Fed communication carries information about the future policy path. Rates and the dollar absorb that information over days, not seconds. A hawkish consensus should therefore predict falling Treasury futures and a rising dollar after we remove what the tone shares with recent rate momentum.

**Why prices could adjust slowly.** Prepared remarks are dated, often only by day, and are not fully priced at the next open. Hundreds of speeches a year make the Committee's centre of gravity a slow-moving state variable that no single release reveals. The evidence fits this view. Voice and text tone in press conferences move the S&P 500 about 75 bp per standard deviation over about five days, but only about 1 bp at the minute level (Gorodnichenko, Pham and Talavera, 2023). Press-conference content predicts the future policy rate better than statements or speeches do (Byun et al., 2026).

**Why we expect a better signal than our predecessor's.** Strategy 01 used a 40-word lexicon on Board speeches and failed out of sample (Section 8). v2 makes two refinements. First, a domain-trained stance model reads policy stance better than a lexicon that finds a median of 3 hits per document. Second, all official Board and FOMC communication says more than speeches alone.

**Press-conference claim (H1).** Q&A answers reveal policy information the statement did not contain. If markets absorb it over minutes rather than seconds, a Q&A hawkishness surprise should predict the 2-year futures move after the conference ends. The literature gives a low prior. Gomez-Cram and Grotteria (2022) find that the statement-window move predicts the press-conference move (correlation 0.58 for Eurodollars) across 41 conferences to January 2020. Narain and Sangani (2026) show this continuation reversed under Powell after COVID. None of the papers we read shows predictability net of latency and costs. We therefore treat H1 as a measurement with a single GO/NO-GO, not as a promised P&L.

**Falsifiers (registered).** For v2 the claim fails if any of these holds: selection Sharpe ≤ 0.2 or validation Sharpe ≤ 0; more than half of in-sample P&L comes from 2022; the momentum-orthogonalised signal (T3) is about zero while the raw signals (T1/T2) look good, which means rate momentum, not communication; net Sharpe ≤ 0 at 2x costs.

## 3. Data & Universe

*Rubric: (5) Evidence; survivorship, corporate actions and missing data. Target ~330 words.*

**Text.** We collected 828 Board speeches from 2015-01-01 to 2026-10-02 (828 of 828 index targets; 44 in 2016 rising to 117 in 2025). The FOMC documents are 97 statements, 94 sets of minutes and 79 press-conference transcripts, all from federalreserve.gov with release dates and times from the site's JSON feeds. Statement times match each page's "For release at" line in all cases. Q&A text comes from the 75 transcripts of 2016-2026 (2,026 Chair answers). Answer timing comes from the Board's official WebVTT captions, which exist for 68 of the 75. The Board's video and audio recordings of all 95 conferences since 2011 (82.4 h) were archived for the voice/face extension.

**Labels and models.** Stance labels come from gtfintechlab/fomc_communication (Shah, Paturi and Chava, 2023; 2,480 sentences, CC BY-NC 4.0). Base models are manelalab/chrono-bert-v1 yearly checkpoints (He et al., 2025; MIT licence).

**Markets.** Daily data: CME futures from Databento GLBX.MDP3 (ZN, 6E, ZT, ES; volume-ranked front contract); TLT and UUP from Yahoo Finance; DTB3 and DGS2 from FRED. Intraday data: Databento 1-minute and 1-second bars and 1-second best bid/offer for ZT, ZF, ZN and ES on the 75 press-conference days, 13:30-16:30 ET ($8.53). We used USMPD (Acosta et al., 2025) as an external check; our ZT moves correlate -0.996 with its 2-year yield changes.

**Survivorship.** The instrument set is fixed in advance, and every instrument trades throughout 2015-2026. The document side is a census of all speeches, statements, minutes and conferences, not a survivor-selected sample.

**Corporate actions.** Futures returns are computed within one contract, so rolls create no price jump; each roll day is charged an extra round trip. ETFs are total-return adjusted (yfinance auto_adjust=True). Intraday, the instrument ID is constant inside every press-conference window. The locked ZT.c.0 series was replaced because it is the illiquid delivery-month contract on 42 of 73 meeting days.

**Missing data.** Nothing is filled with later data. TLT, UUP, ZN and 6E have no missing closes from 2015. DGS2 is forward-filled from past values only and lagged two sessions. Missing minutes are skipped, not interpolated. Meetings without captions (7) or with start uncertainty above 30 s are dropped from timing tests (13 of 75 in all). Two days that Databento flags as degraded are kept, with a pre-registered sensitivity that drops them.

## 4. Methodology

*Rubric: (2) Innovation, (5) Evidence. Target ~520 words.*

**Stance model (walk-forward, no look-ahead).** A document dated in year *Y* is scored only by "model *Y*". That model starts from the chrono-BERT checkpoint pretrained on text up to 31 December of *Y*-1 (capped at 2024). It is fine-tuned only on labelled sentences whose *source document* predates *Y*. This required a correction we found ourselves. The dataset's year column disagrees with the source document's year for 2,336 of 2,480 rows (median gap 7 years). We re-dated every row from the authors' per-document files. Under the literal dataset years, 491 training rows for model 2015 reappear verbatim in documents dated 2015 or later; under the corrected dates, 21 do, all boilerplate. Each model is trained with three seeds, and their probabilities are averaged. Every hyperparameter is fixed in advance (Appendix A3). Each document scores share-hawkish minus share-dovish over its sentences. [[PENDING: validation macro-F1 by model year, from models/<Y>/seed_<S>/metrics.json]].

**Signals (v2).** The consensus follows strategy 01 exactly: C_t = λC_{t-1} + Σ(scores first usable at t), with λ = 2^(-1/20) (a half-life of 20 sessions). It is standardised with an expanding z-score (minimum 252 observations). A document dated *d* enters at the first session strictly after *d*, whatever its release time. The four registered signals are:
- **T1:** speeches only.
- **T2:** all document types.
- **T3:** T2 orthogonalised each day against the decayed change in DGS2 (lagged two days) by expanding point-in-time OLS.
- **T4:** the average of the lexicon and model z-scores.

There are two expressions:
- **E1:** 75% TLT / 25% UUP, filled at the next open.
- **E2:** 75% ZN / 25% short 6E, filled at the next close.

That makes eight combinations. Positions target 10% annualised volatility on the unit hawkish mix, as in Section 6.

**Costs and why.** E1 is charged 1.5 bp (TLT) and 5 bp (UUP) per unit traded, plus 30 bp/yr borrow on short ETF weights. E2 is charged 1 bp per leg plus one round trip per roll. At about 111 points a ZN contract, 1 bp is roughly 1.4 times the measured half-spread (0.5 tick, Section 5). [[PENDING: measured TLT/UUP quoted spreads to justify 1.5/5 bp]]. The 2x row doubles trading and roll costs.

**Protocol and windows.** We pick the one combination with the highest net Sharpe in the selection window (2016-01-04..2020-12-31). We proceed only if two conditions hold: validation Sharpe (2021-01-01..2024-10-02) is above 0, and full in-sample Sharpe at 2x costs is above 0.5. **The out-of-sample window is the last two years, 2024-10-03..2026-10-02.** The span 2016-01..2026-10 is about 10.75 years, so 20% would be about 2.15 years, and the track rule takes the shorter of the two. The out-of-sample window is evaluated once, for the chosen combination only, and reported whatever it shows. The runner writes oos_chosen.json before anything else, or oos_not_evaluated.json if the gates fail.

**Multiple testing.** We compute a Deflated Sharpe over 11 trials (Bailey and López de Prado, 2014). A placebo calibrates the selection gate. With 40 random-score seeds, the best of eight combinations averages a selection Sharpe of 0.198 (90th percentile 0.833). The 0.2 falsifier therefore only screens out noise, and the validation and 2x-cost gates do the real work.

**Pre-registration record.** v2 was written on 2026-10-03 (UTC) and amended three times before any v2 return existed:
1. About 20:00 UTC: the window starts in 2016, so all three chairs are covered.
2. About 21:20: the gated FOMC-RoBERTa was replaced by the walk-forward model.
3. About 21:50: labels were re-dated.

The file's sha256 is 464f8a5b..., and it was committed at [[PENDING: commit hash/time]]. The v2 claim and Amendment 1 precede the commit of strategy 01's out-of-sample verdict (20:26 UTC); Amendments 2 and 3 follow it. The team therefore knew how a lexicon signal had done in 2024-26 before v2's windows were fixed. v2 did not adopt the obvious post-hoc fix of normalising by document count.

**Press-conference clock and H1.** We anchor each conference to live TV captions: GDELT TV API blocks for CNBC and FOX Business, plus Internet Archive item pages. The Board's caption video starts a median 28.8 s after the scheduled time (n=63), so the 14:30:00 convention dates speech too early. Under the convention, the "next bar after the answer" would come before our upper-bound bar on 40 of 62 meetings. That is a look-ahead our clock removes. Each decision time is an upper bound: answer end plus start uncertainty (median 9.3 s).

H1 works at the meeting level:
- The surprise is the mean Q&A score minus the statement score, residualised on the 13:50-14:20 ZT move with chair intercepts.
- The position is short ZT on a hawkish residual. It enters at the next 1-minute open after the conference ends and exits at 16:00.
- It is GO only if, on the confirmation sample (n ≥ 15), mean gross P&L is above 0 and a one-sided wild bootstrap gives p ≤ 0.05.

BENCH-R holds the sign of the 13:50-14:20 move from 14:20 until the conference ends, split at 2020. [[PENDING: team ratification of ADDENDUM vs merged-plan R2-04 spec]].

*AI coding assistants were used; the team reviewed and is responsible for all code and claims.*

## 5. Results

*Rubric: (5) Performance & analytical evidence. Target ~320 words plus Tables 1-2 and Figures 1-2.*

**v2 daily sleeve.** [[PENDING: selection-window net Sharpe of all 8 combinations and the chosen one, from selection.csv]]. [[PENDING: validation Sharpe vs the >0 gate and the 0.7 team target; full-IS 2x Sharpe vs 0.5]]. [[PENDING: falsifiers: 2022 share of IS P&L; T3 vs T1/T2; DSR (n=11, n=10)]]. [[PENDING: OOS result, or "not evaluated" if the gates failed]]. [[PENDING: by-chair rows (descriptive) and the core_ER_6 portfolio test]].

**Table 1. v2 chosen combination, net of costs, excess over T-bill.** Strategy 01 rows use the review engine.

| Window | Costs | Ann. return | Volatility | Sharpe | Max DD | Turnover (x/yr) |
|---|---|---|---|---|---|---|
| IS selection 2016-01-04..2020-12-31 | 1x | [[PENDING]] | [[PENDING]] | [[PENDING]] | [[PENDING]] | [[PENDING]] |
| IS validation 2021-01-01..2024-10-02 | 1x | [[PENDING]] | [[PENDING]] | [[PENDING]] | [[PENDING]] | [[PENDING]] |
| IS full 2016-01-04..2024-10-02 | 1x | [[PENDING]] | [[PENDING]] | [[PENDING]] | [[PENDING]] | [[PENDING]] |
| IS full 2016-01-04..2024-10-02 | 2x | [[PENDING]] | [[PENDING]] | [[PENDING]] | [[PENDING]] | [[PENDING]] |
| **OOS 2024-10-03..2026-10-02 (once)** | 1x | [[PENDING]] | [[PENDING]] | [[PENDING]] | [[PENDING]] | [[PENDING]] |
| **OOS 2024-10-03..2026-10-02 (once)** | 2x | [[PENDING]] | [[PENDING]] | [[PENDING]] | [[PENDING]] | [[PENDING]] |
| *Strategy 01, IS 2011-12-30..2024-10-02* | 1x | 2.34% | 11.2% | 0.210 | -33.5% | 24.5 |
| *Strategy 01, IS* | 2x | n/r | n/r | 0.162 | n/r | 24.5 |
| *Strategy 01, OOS 2024-10-03..2026-10-02* | 1x | -4.97% | 10.9% | -0.456 | -15.6% | 23.3 |
| *Strategy 01, OOS* | 2x | n/r | n/r | -0.502 | n/r | 23.3 |
| *Variant A reference on 2016+ windows* | 1x | [[PENDING]] | [[PENDING]] | [[PENDING]] | [[PENDING]] | [[PENDING]] |

**Press-conference study.** BENCH-R reproduces the pre-2020 continuation in sign but not in significance: +$27.73 per contract per meeting gross (t 0.94, n=20). After 2020 it turns negative: -$35.31 (t -1.15, n=50), and 2022 alone loses $267.58 per meeting. The regime difference has the sign Narain and Sangani (2026) report but is not significant (p 0.146). Pre-2020 break-even cost is 1.0-1.4 ticks per side, against a measured half-spread of 0.5 tick. The frozen lexicon, our negative control, is null as expected (NO-GO; 90% CI upper bound 0.60 ticks). [[PENDING: H1-primary G3 result and robustness rows]]. [[PENDING: H2/H3, run only if G3 = GO]].

**Table 2. Press-conference tests, ZT, USD per contract per meeting (exit at conference end).** Per-event statistics, because eight events a year make annualised Sharpe uninformative. H1 is associational (1-minute prints), so no Sharpe is reported for it.

| Test (sample) | n | Gross | Measured cost | 2 ticks/side | 4 ticks/side | t (gross) | Status |
|---|---|---|---|---|---|---|---|
| H1-primary, stance (Powell confirmation 2023-02..2026-04) | 20 | [[PENDING]] | [[PENDING]] | [[PENDING]] | [[PENDING]] | [[PENDING]] | G3 decision, blind |
| H1-primary, stance, track-OOS slice (2024-11..2026-04) | 12 | [[PENDING]] | [[PENDING]] | [[PENDING]] | [[PENDING]] | [[PENDING]] | descriptive |
| H1-primary, stance, 2016-2022 clean sample | [[PENDING: ≤39]] | [[PENDING]] | [[PENDING]] | [[PENDING]] | [[PENDING]] | [[PENDING]] | descriptive |
| Lexicon control (confirmation) | 20 | -$32.03 | -$39.84 | -8.1 ticks | -12.1 ticks | -1.47 | NO-GO, as expected |
| BENCH-R 2016-2019 | 20 | +$27.73 | +$15.23 | -$22.27 | -$72.27 | 0.94 | non-blind replication |
| BENCH-R 2020-2026 | 50 | -$35.31 | -$43.13 | -$66.56 | -$97.81 | -1.15 | non-blind replication |
| BENCH-R 2024-10..2026-09 | 15 | +$22.40 | +$14.58 | [[PENDING]] | -$40.10 | 0.52 | non-blind; not OOS |

**Figure 1.** [[PENDING: v2 chosen combination, cumulative net excess return at 1x and 2x costs. IS 2016-2024 (selection and validation shaded) and OOS 2024-10-03..2026-10-02 after a vertical line; strategy 01 OOS dashed for reference. Source: daily_<combo>_is.parquet and the OOS output.]]

**Figure 2.** [[PENDING: (a) BENCH-R cumulative P&L per contract by era, gross and net of measured cost, 2016-19 vs 2020-26; (b) median ZT/ZN/ES half-spread by minute relative to conference start (-60 to +90 min), from spreads_by_presser_phase.csv. If H1 passes, replace (a) with the event-time ZT response after answers.]]

## 6. Risk Management

*Rubric: (3) Risk management plan. Target ~300 words.*

**Position limits (v2, fixed before testing).** The z-score is clipped at ±2. Position size targets 10% annualised volatility, using the average of 20- and 60-day realised volatility of the traded mix with a 4% floor. Gross exposure is capped at 1.5x capital. A no-trade band skips rebalances smaller than 10% of current gross; trades are forced on FOMC days, the day after, and from flat.

**Event risk.** The rates leg is halved for the position held over each FOMC announcement session. Eight unscheduled actions and releases (2019-10-11, six dates in 2020, 2025-08-22) are de-risked the same way, which is what moved strategy 01's in-sample Sharpe from 0.210 to 0.203 when applied as known in advance.

**Model risk.** T3 checks whether the signal is just rate momentum: strategy 01's consensus correlated 0.53 with the 2-year yield, and its alpha over that control was 2.3%/yr with t 0.84. If T3 is about zero while T1/T2 work, the registered falsifier calls the result rate momentum. Averaging three seeds limits fine-tuning noise. The 2x-cost gate and Deflated Sharpe guard against cost and selection optimism. A concentration falsifier rejects any result with more than half its in-sample P&L in 2022; 75% of strategy 01's came from that year.

**Portfolio context.** The chosen sleeve is tested as a fourth equal-risk sleeve inside a benchmark book, core_ER_6 (vol-managed ES, month-end ZN and broad trend), with a 6% overlay and a leverage cap of 4. It is adopted only if it adds risk-adjusted return in IS, validation and OOS.

**Press-conference trades.** Each trade is one contract, opened after the upper-bound decision time and flat by 16:00, with no overnight risk. No trade is taken when the statement-window sign is zero. Live use is gated (G5): paper trading only after a G3 GO, only if the measured live p90 delay is 60 s or less, at half size under the new Chair.

**Not pre-registered.** There is no drawdown stop. [[PENDING: team decision on a monitoring rule for live use, labelled as untested]].

## 7. Liquidity & Capacity

*Rubric: (4) Liquidity & capital deployment. Target ~220 words.*

**v2 futures expression (E2).** Over the OOS window, median daily front-contract dollar volume was about $184bn in ZN and $22bn in 6E (our calculation from Databento daily bars). At the gross cap, $100m of capital holds at most $112.5m of ZN (about 1,000 contracts at ~111 points) and $37.5m of 6E. That is 0.06% and 0.17% of a median day's volume for the whole position. Daily trades are much smaller: strategy 01 turned over about 23x a year, or roughly 9% of capital per day. Capacity is not binding below several hundred million dollars. [[PENDING: v2 turnover]].

**v2 ETF expression (E1).** TLT trades about $2.75bn a day, but UUP only about $33m. At $10m of capital, a full UUP position is about 11% of daily volume; at $100m it exceeds a full day. E1 does not scale, so E2 is the deployable version if the two perform alike.

**Capital use.** E2 needs only futures margin [[PENDING: initial margin for ZN and 6E, source CME]]. The rest sits in T-bills, which is why returns are reported as excess over the T-bill rate.

**Press-conference trades.** In 2023-2026, ZT traded a median 2,108 contracts per minute between 14:30 and 16:00 on conference days (10th percentile 529). The quoted market was one tick wide 96% of the time. One contract is negligible. At 5% of a 10th-percentile minute, about 26 contracts (~$5m notional) could trade without exceeding a one-tick market. [[PENDING: depth check; no MBP-1 data were bought]].

## 8. Limitations & Next Steps

*Rubric: (5) Evidence, (1) honesty about the claim; failed-ideas rule. Target ~330 words.*

**Known risks to the claim.**
- **Volume drift.** v2 keeps the decayed-sum consensus that sank strategy 01. Speech counts doubled from 44 (2016) to 117 (2025), and T1/T2 inject every document, so volume can again drive the signal. Expanding z-scores do not remove this.
- **Power.** For H1, power is low: with 20 meetings, P(GO) is 0.29 even at a true correlation of 0.3. A NO-GO is weak evidence of no effect.
- **Labels.** The labels were annotated in 2022-23 with hindsight. They and the fine-tuned models are non-commercial (CC BY-NC 4.0).
- **Timing.** No true wall clock exists: the TV delay is assumed to be 11 s (plausible range 3-20 s). H1 fills use 1-minute trade prints, not executable quotes.
- **Exposure.** BENCH-R is non-blind, and a script has already read the lexicon control's 2023-26 outcome windows.

**How the press-conference samples relate to the OOS rule.** H1's registered confirmation sample (Powell, 2023-02-01..2026-04-29, 20 eligible meetings) was chosen because the registered scorer's labels end in 2022. It is longer than two years, excludes the three Warsh conferences, and overlaps v2's validation window (8 meetings) and OOS window (12). It is a single blind confirmation test, not the track's out-of-sample window. We therefore report the 12 meetings inside 2024-10-03..2026-10-02 as a separate descriptive row [[PENDING: team ratification before stance scores join returns]]. BENCH-R's matching slice is non-blind and cannot count as out-of-sample.

**Failed ideas (all net of costs; details in Appendix A2).**
- **Strategy 01 (lexicon tone):** OOS -0.456. The volume drift above caused it; Q4 2024 alone lost 11.8%.
- **Overnight drift (ES):** 1x Sharpe 0.25, 2x -0.24.
- **Intraday momentum (ES):** -0.31.
- **Pre-FOMC drift (ES):** 70% of gross P&L came from 2020 and 2022; -4.3 bp per event in 2024-26.
- **Hourly trend:** -0.65.
- **Treasury auction cycle:** validation -0.38, dropped under its own rule.
- **GTAA timing:** beat untimed holding in only 9.7% of configurations in 2024-26.
- **Futures carry, value and EWMAC trend:** each negative after publication or costs.

**Next steps.**
- NTP-logged live recordings of the 2026-10-28 and 2026-12-09 conferences, to measure the clock and live delay.
- H2/H3 voice and face proxies, only if G3 = GO.
- Normalising the consensus by document count, testable only on data after 2026-10.
- FOMC-RoBERTa as a robustness check if access is granted.

---

## References (outside the page limit)

**Papers**
- Acosta, M., et al. (2025). U.S. Monetary Policy Event-Study Database (USMPD). Federal Reserve Bank of San Francisco Working Paper 2025-30. https://www.frbsf.org/wp-content/uploads/wp2025-30.pdf
- Asness, C., Moskowitz, T., Pedersen, L. H. (2013). Value and momentum everywhere. *Journal of Finance* 68(3).
- Bailey, D. H., López de Prado, M. (2014). The deflated Sharpe ratio. *Journal of Portfolio Management* 40(5).
- Baltussen, G., Da, Z., Lammers, S., Martens, M. (2021). Hedging demand and market intraday momentum. *Journal of Financial Economics* 142(1).
- Boyarchenko, N., Larsen, L., Whelan, P. (2020). The overnight drift. Federal Reserve Bank of New York Staff Report 917.
- Byun, Fees, Jacobson, Walker (2026). [[PENDING: exact title]]. Working paper. https://margaretjacobson.github.io/CV/BFJW-Fed-Fine-Tune.pdf
- Curti, F., Kazinnik, S. (2023). Let's face it: Quantifying the impact of nonverbal communication in FOMC press conferences. *Journal of Monetary Economics* 139: 110-126. [[PENDING: numbers verified on the 2021 working paper only]]
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
- Board of Governors of the Federal Reserve System (2026). Speeches, FOMC statements, minutes, press-conference transcripts, videos and WebVTT captions; FOMC calendars; JSON feeds ne-speeches.json and ne-press.json; Board membership page. https://www.federalreserve.gov (retrieved 2026-10-03; US government works, public domain).
- CME Group (2019). Notice SER-8171: ZT minimum tick change. https://www.cmegroup.com/notices/ser/2019/01/SER-8171.html
- Databento (2026). CME Globex MDP 3.0 (GLBX.MDP3): ohlcv-1d, ohlcv-1m, ohlcv-1s, bbo-1s. https://databento.com/docs/schemas-and-data-formats/ohlcv (licensed; not redistributed).
- Federal Reserve Bank of St. Louis (2026). FRED series DTB3, DGS2. https://fred.stlouisfed.org
- Federal Reserve Bank of San Francisco (2026). USMPD.xlsx, README updated 17 Sep 2026. https://www.frbsf.org/wp-content/uploads/USMPD.xlsx (underlying data: LSEG Tick History).
- GDELT Project (2026). Television API 2.0. Internet Archive (2026). TV News Archive item pages. [[PENDING: terms/licence statements]]
- gtfintechlab (2023). fomc_communication dataset, revision 6b0283f5 (CC BY-NC 4.0); fomc-hawkish-dovish repository, commit 98646987. Hugging Face / GitHub.
- manelalab (2025). chrono-bert-v1-<YYYY>1231 checkpoints (MIT). Hugging Face.
- Yahoo Finance via yfinance (2026). TLT, UUP daily prices, adjusted.

**Software**
- NLTK 3.10.3; PyTorch 2.11.0; Hugging Face Transformers 5.18.0; pandas; statsmodels; xpdf pdftotext 4.06; ffmpeg. [[PENDING: final versions from requirements lock]]

---

## Appendix (outside the page limit; judges need not read it)

**A1. Pre-registration and deviation log.**

| Time (UTC, 2026-10-03) | Document | Change | Before any return? |
|---|---|---|---|
| before ~20:00 | HYPOTHESIS_v2.md | v2 claim, signals T1-T4, expressions E1/E2, windows, gates, falsifiers | yes |
| ~20:00 | Amendment 1 | 2016+ window (2015 warm-up), by-chair reporting | yes |
| 20:26 | team repo bf880da | strategy 01 replication and OOS verdict committed | n/a |
| ~21:20 | Amendment 2 / Deviation D1 | gated FOMC-RoBERTa (401 at 16:47 ET) replaced by walk-forward chrono-BERT | yes |
| ~21:45 | press-conference ADDENDUM | H1-primary, BENCH-R and G3 made operational | yes for H1 stance; BENCH-R non-blind |
| ~21:50 | Amendment 3 / D1a | labels re-dated from source documents | yes |
| [[PENDING]] | git commit | pre-registration and Amendment 3 code committed; sha256 464f8a5b... | must precede scoring |

**A2. Failed ideas (full).**

| Idea | Key numbers (net) | Why it failed |
|---|---|---|
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
| Press conference: lexicon H1 (control) | -4.1 ticks, NO-GO | expected null |
| Press conference: BENCH-R after 2020 | -$35.31 per contract per meeting | regime reversal (Narain and Sangani, 2026) |

Prior evidence from a team member's separate entry (a different strategy, cited only for cost realism): at the hacker guide's example costs, that book's Sharpe falls to 0.28 IS / -1.05 OOS.

**A3. Stance-model settings.** 15% stratified validation split (seed 0); learning rate 2e-5; batch 16; max length 256; at most 8 epochs with patience 2 on macro-F1; weight decay 0.01; 10% warmup; seeds 42/43/44; bf16 training, fp32 scoring. NLTK Punkt sentence splitting per paragraph. Training rows per model year: 1,606 (2015) to 2,480 (2023-2026). 36 fine-tunes, on an RTX 5090 locally and RTX PRO 6000 GPUs on HiPerGator (UF Research Computing).

**A4. Verification.** Two independent v2 implementations agree to about 1e-15 on placebo scores and catch the same injected-leak canaries. Rebuilding with data cut at 2019-06-28 leaves every earlier signal and weight unchanged. An independent re-implementation of the press-conference backtest reproduces decision times, trade counts (285/285) and P&L exactly.

**A5. Additional figures.** [[PENDING: timing-offset histogram (caption video zero minus scheduled start, n=63); strategy 01 OOS drawdown with Q4 2024 highlighted; selection Sharpes of the 8 combinations against the placebo best-of-8 distribution]].
