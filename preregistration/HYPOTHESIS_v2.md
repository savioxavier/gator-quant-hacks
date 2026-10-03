# Fed communication tone, version 2: pre-registration

Written Sat 2026-10-03, before anyone on the team has seen strategy 01's 2024-10..2026-10 result and before any v2 backtest. Strategy 01 (Variant A, team repo savioxavier/gator-quant-hacks, commit 5ff6084) stays frozen; v2 is a separate, new strategy.

## Claim
Fed communication carries information about the policy path that rates and the dollar absorb over days, not seconds. Two refinements of Variant A should make that signal cleaner:
1. A domain-trained hawkish/dovish model reads policy stance better than a 40-word lexicon.
2. All official Board/FOMC communication says more than Board speeches alone.

After removing what the tone shares with recent rate momentum, a hawkish consensus should predict falling Treasury futures and a rising dollar.

## Data (built before any return is computed)
- **Documents, with release date and, where available, release time:**
  - Board of Governors speeches, 2011-2026 (Variant A's corpus plus 2024-2026).
  - FOMC statements, released 14:00 ET.
  - FOMC minutes, released 14:00 ET three weeks after the meeting.
  - FOMC press-conference transcripts: video available the same day, PDF published later. Use the transcript's own date; trading starts the next session.
- **Scores per document:**
  - (a) Variant A's frozen lexicon score.
  - (b) FOMC-RoBERTa (gtfintechlab, from Trillion Dollar Words): sentence-level hawkish/dovish/neutral, document score = (share hawkish - share dovish).
  - A general LLM score is not used for selection, because of look-ahead risk from training data that postdates the documents. It may be reported as a cross-check only.
- **Market data:** our cached futures F_ZN, F_ZF, F_ZT, F_6E, F_ES; ETFs TLT, UUP; FRED DGS2.

## Signal and execution (fixed)
Consensus construction follows Variant A exactly: exponential decay with a half-life of 20 sessions, expanding z-score (minimum 252 observations), date-only documents traded at the next session, FOMC de-risk as in Variant A. Sizing follows Variant A: 10% vol target, vol floor 4%, gross cap 1.5, clip 2, no-trade band 0.10. These parameters are not tuned.

### Signal variants (4)
- **T1:** FOMC-RoBERTa score on Board speeches only.
- **T2:** FOMC-RoBERTa score on speeches + statements + minutes + press-conference transcripts, equal weight per document.
- **T3:** T2 orthogonalised to rate momentum. Each day, the residual of the consensus on the 20-session-half-life change in DGS2, lagged two days, from an expanding regression (point in time).
- **T4:** the average of z(lexicon consensus) and z(FOMC-RoBERTa consensus), on T2's document set.

### Expression variants (2)
- **E1:** Variant A's 75% TLT / 25% UUP, next-open fills, costs 1.5 / 5 bp.
- **E2:** 75% F_ZN / 25% short F_6E, next-close fills, realistic costs (ZN 1 bp, 6E 1 bp, roll as one extra round trip).

That gives 8 combinations in total. Variant A (T0 x E1) is reported as the reference.

## Windows and decision rule
- **Selection window, 2012-01 .. 2020-12:** choose the ONE combination with the highest net Sharpe (excess over T-bill, realistic costs).
- **Validation window, 2021-01 .. 2024-10-02:** the chosen combination must have a net Sharpe above 0, and also above 0.5 at 2x costs over the full in-sample period, to proceed. The team's target is a Sharpe of 0.7 or more. The validation Sharpe is reported against that target without changing the choice.
- **Out-of-sample, 2024-10-03 .. 2026-10-02:** evaluated ONCE, only for the chosen combination, and only if validation passed. It is reported whatever it shows. No variant is re-chosen afterwards.
- **Multiple testing:** report the Deflated Sharpe using all 8 combinations plus Variant A's logged trials.
- **Portfolio test (pre-declared):** add the chosen sleeve to core_ER_6 (vol-managed ES, month-end ZN, broad trend) as a fourth sleeve at equal risk, with the same 6% overlay and trailing covariance. Evaluate it in the same windows; out-of-sample once.

## Falsifiers
- Selection-window Sharpe of the chosen combination at or below 0.2, or validation at or below 0.
- More than half of the in-sample P&L comes from 2022.
- After T3's orthogonalisation the signal is about 0 (meaning it was only rate momentum), while T1/T2 look good: in that case, report the strategy as rate momentum, not as a communication edge.
- Net Sharpe at or below 0 at 2x costs.

## Not in this test (later, separately pre-registered)
Voice and facial-expression features from press-conference video, and regional Fed presidents' speeches. Each will get its own pre-registration before its data is processed, following the press-conference plan.

## Amendment 1 (Sat 2026-10-03, about 20:00 UTC, before any v2 return was computed)
At the team's request, the evaluation period starts at the beginning of 2016, so that it covers three Fed chairs: Yellen (to February 2018), Powell (February 2018 to May 2026) and his successor (from May 2026). Nothing else changes: the signals, expressions, parameters, decision rule and falsifiers are as above.
- **Corpus:** documents dated 2015-01-01 .. 2026-10-02. Documents from 2015 are used only to warm up the decay and the expanding z-score, so that trading starts at the beginning of 2016. The expanding z-score's minimum of 252 observations still applies; if it is not met by 2016-01-04, trading starts when it is met, and that date is reported.
- **Selection window:** 2016-01-04 .. 2020-12-31 (replaces 2012-01 .. 2020-12).
- **Validation window:** 2021-01-01 .. 2024-10-02 (unchanged).
- **Out-of-sample:** 2024-10-03 .. 2026-10-02 (unchanged), evaluated once, only for the chosen combination, only if validation passes.
- **Added reporting, not used for selection:** Sharpe and return by chair. Chair tenure dates are taken from federalreserve.gov. The successor's period is only about five months long, so it is descriptive only.
- **Variant A reference:** reported on the same 2016+ windows.

## Amendment 2 (Sat 2026-10-03, about 21:20 UTC, before any v2 return was computed): stance model substitution
gtfintechlab/FOMC-RoBERTa turned out to be gated, with manual approval by its authors, and this machine has no approved access. Unofficial re-uploads of the gated weights are not used. Replacement, chosen by the team before any v2 return exists:
- **Model:** a walk-forward chronological stance model. For each test year Y (2016 .. 2026), the base model is manelalab/chrono-bert-v1-<min(Y-1, 2024)>1231 (MIT; pretrained only on text up to the end of that year). It is fine-tuned on the authors' public hand-labelled hawkish/dovish/neutral sentences (gtfintechlab/fomc_communication, CC BY-NC 4.0, ungated, both splits), using only rows with year <= Y-1. The labels end in 2022, so test years 2023+ use all labels.
- **Fixed training settings:** 15% stratified validation split of the training rows (seed 0) for early stopping on macro-F1; lr 2e-5, batch 16, max length 256, at most 8 epochs, patience 2, weight decay 0.01, 10% warmup; 3 seeds (42, 43, 44), with class probabilities averaged.
- **Scoring:** every document (and press-conference answer) dated in year Y is scored only by model Y. The sentence label is the argmax of the averaged probabilities. The document score = (share hawkish - share dovish), exactly as registered for FOMC-RoBERTa. The sentence splitter is fixed in code before scoring.
- **Unchanged:** everything else (signals T1-T4, expressions, parameters, windows, decision rule, falsifiers). T1-T4 use these scores in place of FOMC-RoBERTa's.
- **Later check:** if official FOMC-RoBERTa access is granted later, a rerun with it is reported as a robustness check only. It cannot replace the primary result.

Clarification to Amendment 2 (2026-10-03, about 21:35 UTC, before any v2 return was computed): the 2015 warm-up documents are scored by the same rule with Y = 2015 (base manelalab/chrono-bert-v1-20141231, labels with year <= 2014). Without this they would have no score and the warm-up would be empty. Note: the chrono-bert-v1 checkpoints are ModernBERT-base (about 150M parameters), not classic BERT-base.

Amendment 3 (2026-10-03, about 21:50 UTC, before any v2 return or any full stance-model training): corrected label dates. An audit found that the `year` column of gtfintechlab/fomc_communication often differs from the year of the sentence's source document (for example, a Feb 2022 speech sentence is labelled 2004). Each labelled sentence is therefore re-dated to the date of its source document, using the authors' own per-document files in github.com/gtfintechlab/fomc-hawkish-dovish (data/filtered_data/*_labeled, data/annotated_data/manual-*.xlsx, data/master_files). Where a sentence occurs in several documents, the earliest date is used. Model Y trains only on rows whose corrected source date is before Y-01-01. Rows that cannot be dated from those files are excluded from the 2015-2022 models and kept for 2023+ (all labels predate 2023). Everything else in Amendment 2 is unchanged.
