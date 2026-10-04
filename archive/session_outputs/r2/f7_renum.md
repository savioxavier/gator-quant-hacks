### F.7 Round-2 amendments (dated 2026-10-03, label `r2_patch`)

Written 2026-10-03 between 18:00 and 19:00 EDT. Every item is typed as a correction, an implementation detail (does
not alter a locked hypothesis), a clarifying amendment the team ratifies in writing with a date, or a separately
pre-registered extension. Unlike r1, these amendments are written **after** Databento-based BENCH-R, lexicon-control
and lexicon H1-answer numbers existed on disk (R2-00); none of them was opened by the authors of this round. No
stance-model H1 score exists. Round-2 evidence: `plan/checks_r2_stats/`, `plan/checks_r2_execution/`,
`plan/checks_r2_data_eng/`, `plan/checks_r2_validity/`, `plan/checks_r2_econ/`, `plan/checks_r2_merge/`.
`bt/` = `<scratch>/presser_bt/`; `cache/` = `<home>/.cache/gqh/presser/`.

#### Governance: scorer of record, exposure, one spec

**R2-00 Status and exposure record (correction to the header and to A-08).** Facts at 18:07 EDT
(`plan/checks_r2_merge/exposure_inventory_20261003.txt`, names, sizes, times and SHA-256 only):

- `cache/` holds ohlcv-1m (written 16:42-16:49 ET), ohlcv-1s (16:49-16:56) and bbo-1s (16:56-17:06) for 75 presser
  days 2016-03-16..2026-09-16, 13:30-16:30 ET, plus one combined file per schema. bt/ADDENDUM.md s0 says ZT/ZF/ZN/ES
  for 1m and 1s and ZT/ZN/ES for bbo-1s, and that "the task states it is approved"; no recorded user approval of the
  1s or bbo-1s purchase is known to this plan (A-13, A-18 still list them as pending).
- A parallel pipeline (`bt/`, governed by bt/ADDENDUM.md, written 17:42 ET on merged_plan_v0 and team deviation D1)
  wrote at 17:48-17:57 ET: a QA set; positions; `results/` with BENCH-R trades, break statistics, cost hurdle and the
  USMPD UST2Y comparison; `h1primary_trades.csv`, `g3_and_h1primary_extras.json` and a 2016-2022 robustness file
  computed on the lexicon signal (`positions_status.json`: stance H1 n_signal 0; lexicon `lexH1raw` 65 positions, 20
  of them confirmation-eligible); lexicon H1-answer trades; a 1 s latency sweep; spreads at fill points;
  `key_results.json`; per-meeting BENCH-R tables for ZT/ZF/ZN/ES and per-meeting lexicon H1-primary tables for
  ZT/ZF/ZN/ES. So the τ→16:00 outcome windows of the 2023-2026 confirmation meetings have already been read by a
  script, and BENCH-R 2016-26 has been computed under the ADDENDUM's exit and era rules.
- bt/events/events_market_long.csv (17:28 ET) holds per-event BENCH-R legs; ADDENDUM s12 reports Databento
  BENCH-R correlations computed from it before v1 was saved (17:40 ET). One round-2 reviewer read s12; no reviewer
  and no author of this v2 opened any `results/` or `tables/` file.
- Consequences are in R2-03 (seal, attest, label) and R2-04 (which spec governs).

**R2-01 Reconciliation with team deviation D1 (clarifying amendment; the team ratifies one option in writing,
dated, before any chrono-bert score on presser text exists).** `plan/DEVIATION_D1_stance_model.md` (file time 17:13
EDT) is a dated team decision that replaces frozen FOMC-RoBERTa with the walk-forward chrono-bert model of fedspeak_v2
Amendment 2 for H1-primary, H1-answer and H1-Q, scores by "share hawkish − share dovish" and adds 2016-2022 as a
sample "reported alongside". merged_plan_v1 (17:40 EDT) did not cite it and says the opposite in A-40(a) ("postponed,
not replaced"), A-14 ("v2 uses an argmax share, which H1 does not"), A-10 and section G. The code already follows D1
(`hpg/fedpress/train/stance_walkforward.py` header; `logits.argmax`). v1 cannot override a dated team decision
silently, and two pre-result scorer records let the governing one be chosen after text-only outputs are seen: with
either scorer allowed to count, the false-GO rate at n = 20 is 0.079-0.097 against 0.048-0.055 for one pre-named
scorer (`plan/checks_r2_stats/r2_two_scorers.out`). Until the team ratifies, no H1 input is frozen.

*Option D1 (default, because it is the team's dated text):*

1. The scorer of record for H1-primary, H1-answer, H1-Q, H1-run, H1-A, H1-PX, H1-P, the 2026-10-28 shadow decisions
   and every counted paper trade is D1's walk-forward model: for meetings in year Y, `manelalab/chrono-bert-v1-
   <min(Y−1, 2024)>1231` fine-tuned with the A-14 settings (= v2 Amendment 2) on `fomc_communication` rows with year
   ≤ Y−1, three seeds, probabilities averaged; checkpoints and fine-tunes trained and hashed under R2-05.
2. *Score function.* D1 fixes the score type: sentence label = argmax of the averaged probabilities; term score =
   share hawkish − share dovish. D1 is silent on the sentence filter, clause split and pooling, so A-10's
   training-domain rule fills them (the fine-tunes are trained on the same filtered, clause-split rows, so A-10's
   argument holds): shares are computed over the qualifying (TDW-filtered, clause-split, no "?") chair Q&A sentences
   pooled over the meeting, and over qualifying statement sentences; s = difference. The team ratifies this in
   writing; if it has not by the freeze, this default holds. Tier 3 rows: D1 literal (all chair Q&A sentences of ≥ 4
   words, unfiltered; the r1 warning that about 80% of the Q&A term is then out of domain is recorded), A-10's
   P(h) − P(d), and the answer-weighted mean. The R2-11 construct note is part of the ratification.
3. A-40(a), (c), (d) and (e) and the 2026-10-14 weight deadline (A-35) are withdrawn as gates. The Tier 2 slot of
   H1-replica becomes **H1-RoBERTa**: official FOMC-RoBERTa on the confirmation sample with the R2-01(2) score
   function, run only if weights pass R2-06 before the PREREG timestamp, else p = 1. After the freeze, FOMC-RoBERTa
   is Tier 3 robustness only (v2 Amendment 2, "later check"). H1-replica moves to Tier 3. Holm m stays 9 (the
   Tier 2 BENCH-R-ES numbers already exist on disk, R2-00, so m is not reopened).
4. The A-14 accuracy gate (pooled rolling-origin macro-F1 over 2016-2022 label years ≥ 0.55) becomes a pre-G3
   validity gate, computed and hashed before any market join. A fail postpones H1-primary (G3 not run, live events
   measurement-only, R2-02 abandonment date); no other scorer is swapped in. R2-10 adds a presser-domain label.
5. D1's "additional clean sample, reported alongside" is exactly the Tier 2 row **H1-pooled**: the 70 scheduled
   pressers 2016-2026 with the R2-21 specification (replaces the A-14 decision row). The 2016-2022 and 2023-2026
   sub-samples are Tier 3. Never a GO path; no P&L language outside 2023-2026 Powell.
6. A-09/A-42: a, b and σ come from D1 scores of prior meetings from 2020-01-01 (after the BENCH-R break), a = b = 0
   until 8 such meetings exist. Walk-forward-scored meetings count as uncontaminated under A-29.
7. D-VAL is out of sample for this scorer once the 2011-2015 models exist (R2-08); a pass is labelled
   "out-of-sample".
8. A-43 counts are recorded under this scorer and labelled non-commercial (the labels are CC BY-NC 4.0).
9. Wording: D1's "clean" is recorded as "chronologically consistent pretraining and label years; labels annotated in
   2022-23 with hindsight; tokenizer later than the weights (R2-15)".

*Option v1:* the team withdraws D1 in a dated, hashed note citing A-40, filed before any chrono presser score
exists; then A-40 and A-14 stand as written in v1, with R2-02 and R2-06, and the D1 trainer writes no H1 input.

*Either option:* PREREG_H1.md names one Tier 0 scorer with its weight hashes; no other scorer's G3-type result is ever
reported as a GO; D1's hash goes into the A-12 manifest. If fedspeak_v2 produces chrono scores on presser text before
ratification, that is declared (R2-35).

**R2-02 Script order while G3 waits (implementation detail added to A-12 and A-40).** While H1-primary is
unratified or postponed, no script reads 2023-2026 records of any schema after 14:20 ET: that covers the 2023-2026
rows of H1-pooled and H1-chrono, BENCH-R 2020-26 for 2023+, H1-answer, the A-07 presser-window diagnostic and
spread reports. They wait until G3 runs or until **2027-01-31**, when a still-postponed G3 is formally cancelled and
logged; only then do those rows run. 2016-2022 rows may run earlier. R2-00 shows the windows were already read once
by a parallel script; this rule governs every later read and does not repair that one (R2-03).

**R2-03 Data on disk, sealed outputs and outcome access (correction plus implementation detail).**

1. *Purchase.* The user is asked directly to confirm or deny the purchase (schemas, dollar amount, date). Until the
   user confirms, the ohlcv-1s and bbo-1s files are not read by any plan script; their hashes are kept.
2. *Moratorium.* No script reads `cache/` records after 14:20 ET for any 2020-2026 day until PREREG_H1.md is
   timestamped. PREREG carries an access log from 16:42 ET (scripts run, files read, hashes), starting from the
   R2-00 inventory.
3. *Sealed outputs.* Everything under `bt/backtest/results/`, `bt/backtest/tables/` and `bt/backtest/positions/`
   stays unopened by every person who ratifies A-03, A-10 or R2-01 or writes PREREG; the hashes in the inventory are
   the record. Moving or deleting them is the team's decision, not this plan's.
4. *Attestation and labels.* Each team member states in PREREG whether they opened any sealed file or the ADDENDUM
   s12 numbers, and which. No viewing of 2023-2026 outcome rows attested: G3 carries the label "outcome windows read
   by a parallel script before the freeze; contents unseen by the authors of the frozen choices (attested)". Any
   attested viewing of per-meeting 2023-2026 rows or key results: G3 is labelled "non-blind (outcome vector viewed)"
   and H1-P is the only blind confirmation. The locked G3 rule is still computed and reported, never re-decided.
5. *A-12 reworded.* "Frozen before the 1m download" becomes "freezes the SHA-256 of the data already on disk". Any
   future Databento request for 2023-2026 is split into pre-14:20 and 14:20-16:30 ET files at no extra cost, and the
   outcome file is fetched only after the PREREG and QA-addendum timestamps. A-12's "bar" means any record of any
   schema.
6. *Small fixes.* The A-21 multiplicity and monotonicity check runs on a non-FOMC day or a pre-2016 presser day; the
   A-13 spread report for 2023-2026 runs after the H1-primary script; A-01 record counts for 2023-2026 end at 14:20
   before the freeze and the full-window check runs in the post-freeze QA.
7. *Provenance (A-08).* The prior-exposure list adds the download times, the events-label BENCH-R correlations
   (ADDENDUM s12), the `bt/events/s4_market_align.py` 1 s volatility diagnostic around answer onsets (2023-2026
   included) and the R2-00 outputs. In the provenance table the r1 BENCH-R choices (A-06 exit, entry, sidedness) are
   marked "chosen after exposure to USMPD results on the identical windows" unless their authors attest otherwise.

**R2-04 One execution spec and one code path (clarifying; ratified with R2-01).** bt/ADDENDUM.md (built on
merged_plan_v0) and this plan differ on the H1 and BENCH-R execution choices. Superseded item by item; the ADDENDUM's
hash is listed in PREREG as a superseded record:

| Item | ADDENDUM | Governing rule |
|---|---|---|
| G3 statistic | mean sign-trade P&L, sign-flip bootstrap, n ≥ 15 (s8.2) | HC3 t of s, restricted wild bootstrap (A-03, A-23) |
| Sidedness | as ADDENDUM | A-03 (default two-sided) |
| Residualiser | expanding from 2016 with chair fixed effects (s3.3) | A-09 with R2-01(6) |
| Aggregation | equal-weight mean of answer scores (s3.1) | R2-01(2) |
| Exec30 | veto kept (s3.6) | A-20: no veto, Tier 3 label only |
| BENCH-R exit, era | video end, 15:30 robustness; 2016-19 vs 2020-26 | R2-19; locked 2011-19 era (R2-24) |
| Latency | sweep of L ∈ {0, 5, 15, 30} s on 1 s data (s4.4) | A-18: only τ_used + 30 s; the sweep is a Tier 3 descriptive |
| Clock | GDELT point offset minus an assumed 11 s TV lag (s1.1) | A-02 with R2-16/R2-17 (below) |

*Clock fork.* The ADDENDUM's τ is not an upper bound: on 11 of 23 meetings it lies below the IA LAG-free upper bound,
by up to 17.1 s (20240612) and 12.6 s (20230322), and v1's τ_used is a median 30.0 s later, a different entry bar in
about half the meetings (`plan/checks_r2_data_eng/r2_extra_checks_output.txt` s2). The A-02 clock is the only clock
for H1 entries; the GDELT point clock is a Tier 3 diagnostic. GDELT may serve only as a second upper bound:
τ_used = τ_media + sched + max(hi_IA, hi_GDELT) + M with hi_GDELT = block start + block length − media time, no lag
subtracted.

*Code path.* `hpg/fedpress` produces every H1 text and clock input. `bt/` market-join code may be reused only after it
is changed to these rules, hashed and re-run under PREREG; its existing outputs stay sealed (R2-03).

#### Scorer, training and measurement validity

**R2-05 Training platform and determinism of every walk-forward checkpoint (implementation detail).** Under D1 the
fine-tunes feed H1, H1-P sizing, the A-43 counts and fedspeak_v2 (a trading sleeve), while A-27 and the package put
training on HiPerGator (`registry` on `/blue`, `--gpus 2 --workers-per-gpu 3`), against A-48(4) and A-49(1). The
trainer fixes seeds and turns TF32 off but sets neither `torch.use_deterministic_algorithms`, `CUBLAS_WORKSPACE_CONFIG`
nor `attn_implementation`; the chrono config has `deterministic_flash_attn: false`
(`plan/checks_r2_validity/chrono_tokenizer.out`), and argmax shares flip on boundary changes. Rule: every checkpoint
used by H1, H1-P or v2 is trained exactly once on the local 5090 with `torch.use_deterministic_algorithms(True)`,
`CUBLAS_WORKSPACE_CONFIG=:4096:8`, `attn_implementation="sdpa"` (recorded in each done-marker and in the A-49(8)
twice-run check), float32, pinned torch/transformers. Keys: test years 2011-2022 one key each (`b2010_l2010` ..
`b2021_l2021`; 2011-2014 serve D-VAL only, 2015 also v2's warm-up), plus `b2022_l2022`, `b2023_l2022`, `b2024_l2022`
for 2023-2027: 15 keys × seeds 42-44 = 45 fine-tunes, minutes each. The checkpoints and the full sentence-score table
are hashed into PREREG before any market join; a retrain gets a new id. HiPerGator may replicate them for an agreement
report (argmax flips, meeting-score deltas) after the A-48 sponsor confirmation, inside the R2-36 lanes. The package
registry default moves to a local path. The training runs move into the pre-freeze block under the R2-36 runbook.

**R2-06 FOMC-RoBERTa identity vs reproduction (implementation detail; numbers fixed before access).** The published
presser labels were committed 2022-12-23; the HF repo was created 2023-05-03 and last modified 2023-09-12; TDW trained
3 seeds (`plan/checks_r2_validity/tdw_label_vintage.out`). Authentic weights can fail v1's ≥ 0.98 / |Δ| ≤ 0.01 gate,
and A-40(d) has no earlier commit to fall back on. Identity = pinned commit + LFS oid + SHA-256 of the weight file
obtained through the gated route. Label-map check = argmax agreement ≥ 0.90 on the 63 pressers with the confusion
matrix published; max and p99 |Δscore| reported, not gated. Agreement in [0.90, 0.98): the model runs with the label
"published labels not reproduced exactly". Below 0.90 or an inverted label map: not run (p = 1 in its slot). Replaces
the thresholds of A-10(a) and A-40(e); under option v1 the same rule decides whether G3 runs.

**R2-07 D-VAL additions (diagnostic extension to A-15, filed before D-VAL runs).** (1) Human answer ratings vary 25.8%
between and 74.2% within meetings, and year means explain 18.0% (`plan/checks_r2_stats/r2_dval_within.out`), so a
scorer that only reproduces meeting means reaches answer-level ρ ≈ 0.51 and one that reproduces year means ≈ 0.42.
Add ρ_within (Spearman between score and −avr_score after demeaning both by meeting, meeting-cluster bootstrap); label
"Q&A term not validated" if its one-sided 95% lower bound is below 0.1; print the 0.51 / 0.42 benchmarks next to the
answer-level ρ. (2) Statements are not a TDW training document type (minutes, presser transcripts, speeches;
`<scratch>/fedtalk/literature/tdw.txt` l.121-128): add statement-level ρ (n = 68, bootstrap clustered by year) to the
"measurement weak" rule with the same 0.1 lower-bound test. Applies to every scorer entering Tier 0-2.

**R2-08 Walk-forward D-VAL on the full 2011-2019 deciding sample (implementation detail).** A-14 pinned only 2015-2024
checkpoints, leaving walk-forward D-VAL with 16 pressers. Pin `chrono-bert-v1` 2010-2014 by sha (26 checkpoints exist,
`plan/checks_gap_models/gap_models_hf.out`; 1,296-1,608 label rows precede 2011-2015, `gap_models_ds3.out`), train the
2011-2015 keys under R2-05, and run D-VAL on 2011-2019 with the A-15 rule plus R2-07. A pass is "out-of-sample" for
chrono and "in-sample, not falsified" for FOMC-RoBERTa.

**R2-09 D-VAL-W redesign (clarifying amendment to A-47, filed before any labelling).** As written the rule depends on
class prevalence (identical confusion matrices make Warsh "measurement weak" 40-88% of the time when Warsh has fewer
non-neutral units, `plan/checks_r2_stats/r2_dvalw.out`), 200 qualifying Warsh sentences do not exist (about 105), and
at n = 42-105 the rule fires 8-23% under equal quality (`plan/checks_r2_validity/dvalw_noise.out`).

1. Unit: qualifying clause units (the R2-01(2)/A-10 pipeline input). Warsh: all units of the held Warsh pressers;
   Powell: all units of 3 2025 pressers drawn with the PREREG seed. Statements scored separately. Pre-registered
   addenda add 2026-10-28 and 2026-12-09.
2. Gold label: units where both blind annotators agree; disagreements go to a third blind annotator, else "neutral".
   Cohen's kappa ≥ 0.6 between the first two, else D-VAL-W is "uninformative".
3. Labelling guide: balance-sheet and reserves sentences are labelled by implied policy direction (deviation from TDW
   Table 10, which labels reserve reductions dovish; `tdw.txt` l.692-760), recorded.
4. Metric: balanced accuracy and per-class recall (prevalence-free); macro-F1 and kappa reported.
5. Rule: "measurement weak" if the Warsh − Powell balanced-accuracy difference is ≤ −0.10 with a one-sided 95%
   bootstrap upper bound below 0, or the upper bound of Warsh balanced accuracy is below 0.45.
6. Before labelling, publish the simulated false-fail rate at equal quality and the power against a 0.15 drop at the
   realised unit counts. Report strata: productivity/AI (2.1% of Warsh Q&A sentences vs 0.9% Powell) and balance
   sheet, with the share the filter drops.

**R2-10 Presser-domain accuracy (diagnostic).** Only 219 of 808 label rows 2016-2022 are presser rows
(`plan/checks_r2_validity/chrono_gate_mix.out`), so the pooled 0.55 gate mostly measures minutes and speeches. Add the
rolling-origin macro-F1 on those 219 rows (year-Y rows scored by model Y) with a bootstrap CI; point estimate < 0.45
attaches "measurement weak (presser domain)" to the scorer of record.

**R2-11 What hawk(statement) measures under the filter (clarifying; part of the A-10 / R2-01(2) ratification).** The
authors' keyword match is a substring test and "fund rate" does not match "federal funds rate". On the 27 Powell
confirmation statements, rate-decision sentences pass 1 of 27, forward-guidance "adjustments" sentences 0 of 14 and
balance-sheet sentences 0 of 24; 185 of the 268 passing sentences (0.69) repeat a passing sentence of the previous
statement verbatim (`plan/checks_r2_validity/stmt_filter_content.out`); all 2,480 training rows pass the filter
(`tdw_funds_rate.out`). PREREG states the construct: "hawk(statement) = tone of filtered assessment sentences;
decision, guidance and balance-sheet sentences are excluded by the TDW rule". D-DOM splits S into S_repeat and S_new
and reports variance shares and corr(s, −S_repeat). Tier 3 rows: S_new only; S_all (all statement sentences of ≥ 4
words, decision included, labelled out of training domain). Label "statement term is repeated boilerplate" if
var(S_repeat) > 50% of var(S). The locked statistic is unchanged.

**R2-12 H1-Q question score (clarifying).** A-10 drops every "?" sentence; applied to reporter turns 2023-2026 it keeps
13% of sentences and 70% of turns contribute nothing (`plan/checks_r2_validity/hq_question_sentences.out`). Question
score: all sentences of each reporter turn including "?" sentences, the filter as ratified, the R2-01(2) score type,
meeting mean over turns; turns without a qualifying sentence logged; the term labelled out of domain. H1-Q's locked
role is unchanged.

**R2-13 Scorer vintage inside the confirmation sample (clarifying plus diagnostic).** D1's rule switches base model
on 2024-01-01 and 2025-01-01 (confirmation meetings per base 8 / 8 / 11; anchored 3 / 7 / 10;
`plan/checks_r2_econ/r2_econ_checks.out` s3) although all three fine-tunes use the same labels and the 2022 base is
already uncontaminated for 2023-2026; calendar-year dummies explain 30% of the lexicon s (s3). Default: D1 as written.
(i) **H1-1base** (Tier 3): every 2023-2026 meeting scored by the `b2022_l2022` fine-tunes. (ii) **D-VINTAGE**
(diagnostic, before the market join): all 27 meetings scored by all three bases; per-meeting Spearman between bases,
mean shift of A, S and s at each boundary, share of var(s) explained by base identity. (iii) Each base's sentence
scores are centred and scaled on the fixed causal reference set (pre-2016 statement sentences), extending A-14's
scaling. (iv) Label "not robust to scorer vintage" if H1-1base and the primary differ in sign, or one is significant at
0.05 and the other not. Recommendation: the team may ratify the single 2022 base for 2023-2026 before any market join;
then H1-1base is the primary and D1-as-written Tier 3.

**R2-14 H4 training scores (dated amendment to A-26).** FOMC-RoBERTa's labels include 179 presser rows from 2018-2022
(`chrono_gate_mix.out`), so H4 weights trained on its 2018-2022 scores over-weight text. H4's training-period text
features are the walk-forward chrono scores (same scorer family as Tier 0 under R2-01). Under option v1, H4 is
recorded as an A-29 exception "trained on in-sample text scores".

**R2-15 Licences, tokenizer and caches (records).** (1) The chrono-bert tokenizer is identical across 2015-2024
checkpoints (git oid 2f4d8583e5; " COVID" is one token in the 2015 checkpoint, `chrono_tokenizer.out`): the A-29
registry says the weights are chronological and the tokenizer is not; the share of tokens first used after the
checkpoint year is logged per meeting; Tier 3 row without such sentences. (2) The TDW repository code is CC BY-NC 4.0
(`tdw_label_vintage.out`): the A-43 permissive scorer uses team-drawn federalreserve.gov sentences, a filter and
clause split reimplemented from the paper text with a provenance note, and labels made without viewing
`fomc_communication`; A-30 lists the TDW code as NC. (3) Raw TV-archive pages and GDELT caption text cached under
`bt/events/src/tv_archive`, `bt/events/src/tv_raw` and `<scratch>/gapdata/tvcache` stay private, outside any shared,
pushed or HiPerGator path, listed in a do-not-share manifest, and are sealed or deleted once the text-free per-cue
tables are hashed (A-02(9)).

#### Clocks

**R2-16 Anchor windows and the drop rule (implementation detail; replaces A-02(3) and A-02(5), returning to the locked
criterion).** Replaying the r1 rules on the VTT timeline keeps 16 of the 20 v0-anchored confirmation meetings
(`plan/checks_r2_data_eng/r1_anchor_rules_replay_output.txt`): 20240131 fails because its τ bin is the last partial
media bin (4 cues), and 20230322 and 20240612 fail the drift gate although their τ-bin bound is *later* (a Power Lunch
→ Closing Bell time-base step of +11.5 / +17.4 s), so dropping them protects nothing; none has a half-width > 30 s, the
only locked criterion. (a) τ window = trailing [τ − 600 s, τ] inside the single item airing at τ, with ≥ 20 live cues;
the same for each answer (H1-answer, H1-run). (b) Estimator frozen as the evidence code computes it: lo = P80 and
hi = P20 of per-cue bounds over live matches only (|implied offset| ≤ 300 s, one station, replays excluded); the
`tv_anchor.py` comment is corrected. (c) Drop only if the half-width is > 30 s; fewer than 20 cues counts as > 30 s.
(d) The drift gate is replaced by τ_used = τ_media + sched + max(hi_τ-window, hi of the first window of the same
station) + M; a meeting goes to (C) only if the two differ by > 60 s (broken timeline). (e) The realised n, its
composition and the A-11 operating characteristics are recomputed and frozen in PREREG.

**R2-17 Archive time-base error ε (implementation detail; amends A-02(1),(7)).** Consecutive CNBC items differ by
+11.5, +17.4 and −7.0 s; IA-page and GDELT derivations differ by a median −14.6 s with a sign flip between 2016 and
2017+; FBC runs +17..+34 s behind CNBC in 2023-01..2025-03 (`r2_extra_checks_output.txt` s1, s3); since 2019 Power
Lunch starts at 14:00, so the 2016-2018 one-sided check does not cover the confirmation era. (1) One station per
meeting: CNBC, FBC only if CNBC is absent, never mixed. Record the Power → Closing step; for τ in the later item add
max(0, −step) to M. (2) Before the freeze, validate the IA segment convention against GDELT block starts on 2016-2024
and use the later upper bound. (3) For 2026-10-28 and 2026-12-09, a recorder that captures CEA-608 captions of a
channel the archive records gives a valid one-sided bound ε_early ≤ min over cues of (t_rec_caption − seg0); it needs
a tuner or IPTV feed the user has (user decision). (4) If no calibration exists when G3 runs, the M + 15 s and M + 30 s
reruns run anyway; "not robust to clock" attaches if either disagrees; PREREG labels the clock "margin
uncalibrated".

**R2-18 MP4 completeness and the clock-source rule (implementation detail; replaces the tests in A-05).** A CTC
aligner places every token, so "coverage ≥ 90%" cannot fail; rule (a)'s 1 s criterion fails on 13 of 27 confirmation
meetings, so rule (b) is the main path; and rule (b)'s cross-check compares two quantities built from the same cues.
(1) Completeness, independent of the aligner: pinned Whisper on the final 180 s of each MP4; complete iff the last 20
words of the PDF's last chair answer are found (token fuzzy ratio ≥ 0.8), end ≥ 1 s before the MP4 end, and the
answer's words per second lie within the meeting's own p1-p99. (2) The aligner is seeded from Whisper ASR, never from
the VTT; pad ≥ 2 s; segments cut at VAD silences. (3) Rule (b) is valid only if the pre- and post-MP4-end TV intervals
of the same item overlap with |Δhi| ≤ 5 s (20240131: [−40.4, 0.4] vs [−48.3, −1.3],
`plan/checks_r1_data_eng/tv_after_video_end_output.txt`); remove the VTT-to-MP4 offset before calling a 1-6 s overrun
a truncation. (4) The aligner model stays the explicit `jonatasgrosman/wav2vec2-large-xlsr-53-english` pin; it is not
the WhisperX English default (torchaudio `WAV2VEC2_ASR_BASE_960H`). (5) Optional: completeness cross-check on C-SPAN's
copy, derived timings only.

#### BENCH-R and price definitions

**R2-19 BENCH-R exit, Tier 1 status and BENCH-R-P (clarifying amendment the team ratifies; default = the locked
words).** A-06 (r1) replaced the locked "presser-end" with scheduled start + 60 min and called it an implementation
detail. That hold runs a median 5.0 minutes past the video end in 2011-19 (25% of holds end inside the presser) and
10.2 minutes in 2020-26 (6%), 10.7 in Powell 2023-26 and 17.4 for Warsh
(`plan/checks_r2_execution/benchr_horizon_by_era_output.txt`), so the locked 2020 break compares different horizons
and BENCH-R 2020-26 holds into H1's first post-τ minutes; it also equals the USMPD presser window whose correlations
were seen (A-08). (1) Exit = open of the first 1m bar at or after scheduled start + MP4 duration + 60 s: metadata only,
no ASR or anchor, defined for all 93 scheduled pressers; the two truncated MP4s move it by at most 2 bars. Live and in
BENCH-R-P: the A-42(2) stream end, else the same rule on the live recording's duration. (2) Start + 60 min is a
Tier 3 USMPD-comparable row; the A-19 hurdle table is computed on both exits; label "break confounded with hold
horizon" if the two exits disagree in sign or in Holm significance for the break. Tier 3: in-presser leg (14:20 to
presser end) and post-presser leg (presser end to start + 60) per regime; overlap minutes with the H1 window per
meeting. (3) A-06's list of unidentified break causes adds presser length / post-presser minutes, SEP composition
(R2-30) and the CME feed change (R2-22). (4) Tier 1 is renamed "reproduction on a second instrument (ZT vs USMPD
UST2Y), non-blind"; Holm m = 3 is kept for bookkeeping; the write-up does not call it a test or a confirmation.
(5) **BENCH-R-P** (Tier P, registered now): the video-free BENCH-R decision computed by next-day deterministic replay
(R2-20) for every presser after the PREREG timestamp; sign-trade mean with the R2-29 intercept companion, two-sided,
studentised O'Brien-Fleming looks at 8/16/24 events with the R2-25 two-sided boundaries. It is the only blind BENCH-R
evidence. If the team keeps start + 60 min, the write-up states the 5.0 vs 10.2 minute and 25% vs 6% asymmetry.

**R2-20 One R_stmt, no shared prints (implementation detail).** A-38 ends R_stmt at the 14:20 open and A-06 enters
BENCH-R at that same print, so sign(R_stmt) partly records bid or ask and builds about half a tick of reversal into the
hold (a t-shift of about 0.4 in 2011-19 and 0.13 in 2020-26 toward a "break"; sub-tick signs 12.5% / 18.9%, 34.8% in
2020-22). Live, A-17(5) used as-of quotes, a different measurement from the trade-price R_stmt that a, b were fitted
on. Rule: R_stmt = log close of the 14:19 bar − log close of the 13:49 bar (`ZT.v.0`; era windows shifted per A-06),
the last trades inside the window, offline, live (computed next day) and in BENCH-R; the BENCH-R entry stays the 14:20
open. R_pc runs from the 14:19 close to the close of the bar before the H1 entry bar. A-09/A-42 a, b, σ use this
definition. The as-of-mid version is Tier 3 after the bbo question is settled. A-17(9)'s live BENCH-R logging is a
next-day deterministic replay (feeds BENCH-R-P). Registered now as Tier 3: **BENCH-R-d10** (entry 14:30), the object a
10-minute-delayed live quote could trade.

**R2-21 Samples across the 2020 break (clarifying, before results).** R_stmt's relation to later returns changes at
2020 (USMPD statement-to-presser 2y corr +0.27 in 2011-19, `r2_econ_checks.out` s5; −0.06 in 2020-26, A-08), and a
single coefficient in a pooled test inflates false GO to 0.057 / 0.072 / 0.102 against 0.045-0.051 with an interaction
(`plan/checks_r2_stats/r2_chrono_break.out`). Every test that uses 2016-2022 meetings (H1-pooled, H1-chrono, the
2016-2022 FOMC-RoBERTa descriptive run, D1's 2016-2022 sample) uses y ~ 1 + post2020 + s + R_stmt + R_stmt×post2020 +
chair + SEP. The decision statistic is the pooled s coefficient; the s×post2020 Wald test is reported; label
"regime-heterogeneous" if the sub-period slopes have opposite signs. Tier 3 variant with the break at 2022-03-16
(Narain-Sangani). The confirmation sample lies after 2020 and is unaffected.

**R2-22 The legacy CME feed before 2017-05-21 (implementation detail).** Databento's 2010-2017 GLBX.MDP3 history comes
from CME's legacy FIX/FAST feed via DataMine; ts_recv and ts_event come from SendingTime and `F_BAD_TS_RECV` is set on
all messages up to 2017-05-21 (https://databento.com/blog/CME-history-extended-to-2010). That covers 25 of the 40
2011-19 BENCH-R pressers and 5 H1-pooled meetings. (1) 2017-05-21 is an era boundary wherever eras are used (A-01
floors, A-13 spread tables, A-21 density and staleness, A-04): legacy feed to 2017-05-20; 2017-05-21..2019-01-11; from
2019-01-14. (2) The join keeps `F_BAD_TS_RECV` records and logs reorder counts per meeting; unit test that 2016-03-16
returns bars. (3) The A-21 check covers one legacy day and one MDP3 day. (4) Tier 3: the 2011-19 mean split at
2017-05-21 and the break without legacy-feed events; the feed change is an unidentified break cause. (5) 1 s uses on
legacy events are flagged "SendingTime clock". (6) Unit test that mids and quote fills use the bid/ask levels only,
never the BBO record's price field (the last trade, `databento_dbn` `_lib.pyi`).

**R2-23 Degraded vendor days (implementation detail).** The free `get_dataset_condition` lists 2024-09-18 and
2025-09-17 as degraded (last modified 2026-08-29 and 2026-08-28; `r2_extra_checks_output.txt` s4); 2024-09-18 is also
MP4-truncated. Record condition and last-modified date per event day in the A-49 manifest; QA record counts on those
days against neighbouring presser days before outcomes; Tier 3 row without degraded days; a re-download after the
freeze is hash-compared and a mismatch logged, never silently replaced.

**R2-24 Rows that need data outside the cached window (implementation detail; needs a printed quote and the user's
approval).** The cache covers 2016-2026, 13:30-16:30 ET. P1 needs a window ending 13:50 of outcome length (median
38.6 min, so from about 13:11); P3 needs the previous trading day; the A-03 robustness exit needs next-day 15:00; A-06
needs 2011-2015. Before PREREG these extras get a free `get_cost` printout for the user's decision, or are marked "not
computable" in PREREG. BENCH-R keeps the locked 2011-19 era; running 2016-19 instead would be a dated deviation.

#### Statistics and interpretation

**R2-25 H1-P: statistic, sidedness and wording (clarifying amendment to A-41/A-43, filed before 2026-10-28).** A-43's
levels (z 2.95 / 2.09 / 1.71) are one-sided boundaries; applied to |t| under the two-sided default they give size
about 0.10 (0.074 for HC3 at looks 8/16/24); the reference t_{k−1} does not fit a 3-parameter regression; and a
Rademacher bootstrap at n = 8 cannot reach the look-1 level (`plan/checks_r2_stats/r2_sequential.out`). (1) Statistic:
HC3 t of s in y ~ 1 + s + R_stmt, referred to t_{k−3}; never a wild bootstrap at look 1. (2) After a G3 GO: one-sided
in the sign_G3 direction with nominal one-sided p 0.00153 / 0.0181 / 0.0437. After a NO-GO or while G3 is postponed:
two-sided with nominal two-sided p 0.00052 / 0.0141 / 0.0451. (3) Before 2026-10-28, publish the simulated size and
the look-1 power (about zero). (4) A-11 prints two-sided reference values beside the one-sided ones (n = 20: 0.13 /
0.25, MDE 0.59). (5) Wording: H1-P is "prospective replication (Warsh era, live clock)" in every case, a joint test of
a new chair and a new cycle phase (R2-30); it becomes "confirmation" only by a dated amendment filed before
2026-10-28.

**R2-26 Execution after a G3 NO-GO (clarifying; frozen in PREREG).** After a GO all tiers run. After a NO-GO: Tier 1
runs (it does not depend on H1); H2, H3 and H4 do not run (p = 1, the locked "do not mine H2"); H1-pooled, H1-A,
H1-PX, H1-run, H1-RoBERTa and the 2016-2022 rows run only as "post-NO-GO descriptive", Holm p printed, with the fixed
sentence "cannot rescue G3"; diagnostics run; H1-P and BENCH-R-P continue in Tier P. The write-up reports the G3
verdict first.

**R2-27 What a GO means (implementation detail in PREREG).** With two-sided power 0.13-0.33 at n = 20-27 and a
data-chosen trading sign, the positive predictive value of a GO is 0.22-0.42 at a prior of 0.10
(`r2_econ_checks.out` s4). PREREG states a prior π = 0.1 with its provenance (A-24's three event studies that died
after costs) and the PPV of a GO at the realised n by simulating the exact A-23 procedure. GO wording: "association
detected (PPV ≈ x at π = 0.1), not an edge". Edge or real-money language only after H1-P's first passing look in the
sign_G3 direction and a licence path (A-30, A-43). G3 itself is unchanged.

**R2-28 Fixed-design operating characteristics (implementation detail in A-11).** s is persistent (AR(1) 0.94 human,
0.55 lexicon); at the realised 3/7/7/3 composition with AR 0.94 and a year component in y, false GO is 0.060 / 0.075 /
0.090 at year ICC 0.05 / 0.10 / 0.20 against 0.046-0.053 i.i.d. (`plan/checks_r2_stats/r2_yearblock.out`); the
outcome-free year ICC of ZN 15:00-16:00 returns on non-FOMC days 2016-2026 is 0.006 (`r2_icc_nonevent.out`). A-11's
simulation runs fixed-design on the frozen realised s and R_stmt with null y at year ICC 0, 0.05 and 0.10, each
published. Tier 3 row with year fixed effects; D-DOM prints the share of var(s) explained by year.

**R2-29 Mean statistics and drift (implementation detail).** For the BENCH-R sign-trade mean, H1-run and the counted
P&L, E[position × return] mixes drift with predictability. Beside every mean statistic report the split into
covariance and E[position]·E[return] and a regression companion with an intercept; label "drift times exposure, not
timing" when the covariance term and the mean disagree in sign or significance. H1-run's s̃ uses the A-09 expanding
coefficients.

**R2-30 Additional registered rows (Tier 3 unless stated; filed now, no tuning).** (1) *SEP composition:* all 32
pressers 2011-2018 were SEP meetings, 36 of 40 in 2011-19 against 26 of 53 in 2020-26
(`hpg/manifest/pressers.csv`); Powell discusses projections 2.3 times as often at SEP meetings (`r2_econ_checks.out`
s2). BENCH-R break on SEP meetings only and the non-SEP 2019-2026 descriptive; SEP dummy in every 2016-2022 test
(R2-21). (2) **D-STMT-PATH** (run after the H1-primary script, non-blind for 2023-26): R_pc and R(14:20 → exit) on
S_m with R_stmt as control; label "statement-text drift; Q&A not required" if S's coefficient on R_pc has the
D-DECOMP sign with p ≤ 0.10. (3) *Cycle phase:* an outcome-free event-table field (decision and direction of the last
move, from the statement), frozen per meeting; H1 by phase descriptive. The confirmation sample has 4 hikes, 17 holds
and 6 cuts; Warsh has 2 holds and a hike (`r2_econ_checks.out` s6). (4) **H1-ZF, H1-ZN, H1-ES:** same exit, R_stmt on
the same instrument (ES also with the ZT R_stmt), ES also at 15:49. (5) *Morning supply news:* a second flag class
"same-day pre-13:50 Treasury supply or rates news" (quarterly refunding statements fell on 2023-05-03, 2023-11-01,
2024-05-01 and 2025-07-30, FRASER press releases; month-ends), frozen before outcomes, with a row without flagged
meetings.

#### Live path and paper trades

**R2-31 Live delay, fill time and the Warsh settlement rule (implementation detail, registered before 2026-10-28;
amends A-17(4),(6), A-42(4), A-43).** v1 checks G5 on per-answer latency (i) but trades on (ii), whose end event has a
90 s timeout, so the locked kill switch never binds the traded entry; A-17(6) says the delay is never added while A-43
freezes one; (ii) is measured on the recording's own clock, which omits stream lag; and A-42(4)'s 15:01 rule enters
before the decision when τ_used ∈ (15:01:00, 15:02:00].

1. G5 as locked: per-answer p90 of delay_upper (i) ≤ 60 s. D_frozen = max(p90 of (i) on 2026-10-28, 30 s).
2. Counted fill time t_fill = max(t_decision + 1 s, τ_wall_hi + D_frozen, t_rule), where τ_wall_hi is the upper bound
   of the last answer end on the reference clock and t_rule is item 5. The frozen delay is a floor, never an addition.
3. (ii) = t_decision − (t_ref(last answer) − L_ref), on the reference clock; reported beside a pre-stated cap
   E_cap + 60 s = 150 s. If (ii) on 2026-10-28 exceeds the cap, counted trades do not start.
4. 2026-10-28 shadow decisions use the same rule with D_frozen := 60 s. A G5 fail stops counting until a dated
   pipeline change plus one fresh measurement presser; never a retroactive re-measurement. H1-exec-live stays the
   offline bracket.
5. Warsh settlement: the 15:01 rule is deleted. Entry time = 15:00:00 only when τ_used ∈ [14:59:30, 15:00:00) (the
   ZT settlement VWAP window, https://cmegroupclientsite.atlassian.net/wiki/x/CgAtH), otherwise τ_used; the locked
   next-open rule applies to that time, identically for offline Warsh rows, H1-P and counted trades. Unit test: entry
   ≥ τ_used for every τ_used on a 1 s grid 14:55-15:05. The plain locked bar is logged beside it.

**R2-32 Live clock references and the segment-level recorder clock (implementation detail, by 2026-10-21).** None of
the A-17(3) references is confirmed, the Fed calendar lists no Board-hosted stream before 2026-10-28
(https://www.federalreserve.gov/newsevents/2026-october.htm, fetched 2026-10-03), and the Fed HLS segments are about
10 s (`plan/checks_r1_data_eng/hls_output.txt`). (1) By 2026-10-21 register the 2026-10-28 reference set with L_ref
values: a UF library Bloomberg session (headline times readable after the event; second resolution UNVERIFIED) and a
tuner only if the user has one. Fallback stated now: no reference → processing-lag-only and no counted trade on
2026-12-09. (2) Every event is stamped with a monotonic counter (`perf_counter_ns`) mapped to UTC by query-only NTP
every 5 min; each HLS segment is dated by its own NTP-corrected arrival time with its sequence number; check
EXT-X-MEDIA-SEQUENCE continuity; never extrapolate start + offset across a gap; flag stalls (arrival gap > 2 ×
segment length); cross-correlate loopback audio against HLS. τ_wall_upper = arrival of the segment containing τ +
processing; H1-P uses it, and its entry-lag distribution is reported beside the historical one (TV hi + M). (3) PDT is
accepted only if PDT(segment) ≤ arrival(segment) − target duration for every segment. (4) Schedules use
America/New_York; the scheduler is dry-run in EST before 2026-12-09 (first presser after the 2026-11-01 change).
(5) Optional, user decision, manual only: post IDs of wire-headline accounts encode creation time
((id >> 22) + 1288834974657 ms; epoch from memory, UNVERIFIED) and could give extra upper bounds for A-02; derived
offsets only, no scraping.

**R2-33 One paper cost model and the A-43 statistic (implementation detail).** A-17(6) fills at the as-of ask/bid and
then charges A-04's {2, 4}-tick all-in stress, charging the spread twice; A-13 uses half-spread + 1 tick. Counted
paper P&L = quote fill at the as-of ask/bid + fees + 1 tick slippage (the A-13 measured-cost column); the {2, 4}-tick
stress applies only to mid-to-mid or trade-price P&L. A-43 statistic = studentised mean of per-event net P&L in ZT
DV01 units (quote-fill version), gross and stress versions reported; H1-P keeps the R2-25 slope. Checked and
rejected: t_{k−1} vs t_{k−3} quantiles change size only from 0.052 to 0.055 (`plan/checks_r2_execution/
h1p_obf_df_output.txt`).

**R2-34 Quote-fill timing (implementation detail in A-13).** A-13 priced the quote-fill and measured-cost columns at
τ_used, up to 60 s before the locked entry. They now use the as-of quote at the locked entry instant (the entry bar's
minute boundary, or with 1 s data the second of that bar's first trade); exit quotes at 16:00:00 for H1 and at the
BENCH-R exit bar boundary for BENCH-R. The τ_used-instant quote fill is a Tier 3 timing variant beside H1-exec30.
Spread tables name the exit they use.

**R2-35 Sequencing with fedspeak_v2 (implementation detail).** v2's validation window (2021-01-01..2024-10-02) holds
14 of the 27 confirmation pressers and its variant T2 scores presser transcripts with the same checkpoints. No v2
validation-window or out-of-sample number, and no attribution by document type, is opened until PREREG_H1 is
timestamped. If v2 validation is opened first, the 2023-02-01..2024-09-18 confirmation meetings carry "exposed via
fedspeak_v2 validation" and the write-up names H1-P the only blind confirmation.

#### Compute

**R2-36 GPU lanes and the batch runbook (implementation detail; replaces the A-48(1) guard).** The current squeue
documentation (https://slurm.schedmd.com/squeue.html, fetched 2026-10-03) shows GPU requests under `-O tres-per-job /
tres-per-node / tres-alloc`, not `%b`; pending array elements collapse into one line without `-r`; counting pending
GRES blocks A-27's own `%2` arrays; and check-then-submit races. (1) The user's rule (at most 2 GPUs per session) is
enforced by the scheduler: every GPU job uses one of two job names (lane A, lane B), each with exactly 1 GPU, or a
single 2-GPU lane, submitted with `--dependency=singleton`, so at most 2 GPUs are allocated however many jobs are
pending; arrays run inside a lane. Audit, not gate: `squeue -u $USER -h -r -t R -O JobID,Name,tres-alloc`, summing
running gres/gpu into each done-marker. No interactive or Open OnDemand GPU session while a lane job runs.
(2) Local batch runbook for the freeze-critical work on the shared 5090 (alignment, anchors, 45 fine-tunes, scoring,
A-49(8) double runs): pull media once and freeze its SHA-256 before any GPU job (Brightcove URLs expire after about
6 h); unload the LLM stack and pause the autonomous worker for the batch; atomic per-meeting outputs whose done-markers
carry device, driver and a 12VHPWR-guard log excerpt; a guard, OOM or power event voids only the in-flight unit,
which is rerun from hashed inputs; resume, never restart from partial files.
