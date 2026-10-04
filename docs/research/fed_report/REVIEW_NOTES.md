# Review notes on REPORT_DRAFT.md (draft v0)

Reviewed Sat 2026-10-03, 19:10-19:50 ET, against the draft as written at 19:10 ET (35,824 bytes; identical to
`report/REPORT_DRAFT.md` in team commit `537c483`). Line numbers refer to that file. The draft was not edited.

Path shorthand: `<s>/` = the session scratch folder (never cite it in the PDF); `team/` = the team repo checkout
`<s>/team_push` (branch `review/strategy-01`); `plan/` = `research/fed_presser_plan/`.

> **Exposure warning (read before circulating this file).** `plan/MERGED_FINAL_PLAN.md` s3.11 seals the `presser_bt`
> outputs (BENCH-R, lexicon control, spreads) and says no presser ratifier may open a v2 validation-window number
> before PREREG-R (R2-35). The draft already quotes the sealed BENCH-R and lexicon numbers. Section S at the end of
> this file contains v2 in-sample numbers. A teammate who still has to ratify the H1 spec should not read the draft's
> Results section or Section S of this file until the ratification is recorded. No H1 stance result was opened for this
> review. The `presser_bt/backtest/results/` files that changed after 19:08 ET (an H1 run appears to be in progress)
> were not read.

Severity: **B** = blocker before submission; **E** = factual error; **C** = consistency; **G** = guideline or rubric
gap; **P** = page budget; **M** = minor or wording.

---

## 1. Results that are no longer pending (the draft is stale)

1. **B. The v2 in-sample run has happened, and its decision rule failed** (lines 31, 34-35, 67, 145, 150-156, 177).
   `<s>/fedspeak_v2/backtest/summary_is.json` (written 19:08 ET, pre-registration sha256 `464f8a5b...` checked),
   `selection.csv`, `windows_all.csv` and `oos_not_evaluated.json` exist. `team/preregistration/PREREG_LOG.md` records
   the run at about 23:10 UTC. The out-of-sample window was **not evaluated** (validation passed, full-IS 2x Sharpe
   failed the 0.5 gate).
   **Fix:** replace every v2 `[[PENDING]]` in Summary, Results, Table 1 and Fig. 1 with the numbers in Section S1.
   Replace the two OOS rows of Table 1 with one row: "OOS 2024-10-03..2026-10-02: not evaluated; the pre-registered
   decision rule failed (full-IS Sharpe at 2x costs 0.387 < 0.5)". Keep the strategy 01 OOS rows. Fig. 1 becomes
   IS only (selection and validation shaded) with no OOS segment; say so in its caption.
2. **B. Two registered falsifiers fired** (line 81 lists them; line 145 leaves them pending).
   `summary_is.json` `falsifiers`: selection Sharpe 0.154 <= 0.2 (true); 2022 share of full-IS P&L 0.739 > 0.5
   (true); validation 0.687 > 0 (not fired); net 2x Sharpe 0.387 > 0 (not fired); T3 is not about zero (corr(z_T2,
   z_T3) = 0.975, so the rate-momentum falsifier does not fire).
   **Fix:** state in Results: "Two of four registered falsifiers fire: selection Sharpe 0.154 (<= 0.2) and 74% of
   in-sample P&L from 2022. The signal is not rate momentum (T3 tracks T2, correlation 0.975)."
3. **B. The stance scores exist; they are not "being trained"** (lines 103, 221-236 context, and the computed task
   framing). All 36 fine-tunes finished on the local RTX 5090 (18:37-18:53 ET) and scoring finished 18:56 ET
   (`<s>/chrono/full/`, `merge_stdout.log`; `doc_scores_meta.json`: 12 years x seeds 42/43/44, 5,225 documents,
   chrono doc-score sha256 `a9d7d206...`).
   **Fix:** fill line 103's placeholder with "Validation macro-F1 across the 36 models: 0.545-0.684 (by year, mean of
   3 seeds: 2015 0.577, 2016 0.618, 2017 0.611, 2018 0.584, 2019 0.579, 2020 0.624, 2021 0.650, 2022 0.613, 2023
   0.652, 2024 0.664, 2025 0.661, 2026 0.660), from `models/<Y>/seed_<S>/metrics.json`." Add for context that Shah et
   al. report about 0.71 combined F1 for FOMC-RoBERTa (team plan s1), so the walk-forward model is weaker than the
   gated one.
4. **B. The pre-registration is committed; the checklist rows on lines 29-30 are wrong now, and the commit came
   after the v2 run.** `team/` commit `537c483` (2026-10-03 23:11:18 UTC, pushed to `origin/review/strategy-01`) adds
   `preregistration/HYPOTHESIS_v2.md` (sha256 `464f8a5b...`, identical to the local file), `DEVIATIONS.md`,
   `PREREG_LOG.md`, the ADDENDUM, D1 and the team plan. The Amendment 3 code is in `0fd707f` (22:37 UTC). The v2 run
   checked the current hash through `wire/run_v2_chrono.py` (`summary_is.json` `prereg_sha256_checked`), so the
   "runner pinned to 6083d3ef" item is resolved. `PREREG_LOG.md` itself discloses that the public commit followed
   the v2 in-sample run.
   **Fix:** line 128: "committed publicly at 23:11 UTC (`537c483`), after the v2 in-sample run (about 23:10 UTC) and
   before any press-conference H1 result was viewed; the earlier times are recorded in the files and their hashes in
   PREREG_LOG.md". Appendix A1 last row (line 295): time "23:11", change "public commit 537c483", last column "after the
   v2 IS run; before H1 results" (delete "must precede scoring", which did not happen). Mark lines 29-30 done.
5. **E. A1 omits the v2 deviations file and uses approximate times that disagree with the log** (lines 289-295).
   `PREREG_LOG.md`: v2 written 19:52 UTC, Amendment 1 19:53, Amendment 2 and D1 21:12 (the files themselves say
   "about 21:20"), clarification 21:35, ADDENDUM 21:45, Amendment 3 and D1a 21:50, `DEVIATIONS.md` (D-1 unscheduled
   de-risk dates, D-2 T3 scaling) 22:40.
   **Fix:** use the logged times and add a row "22:40 | DEVIATIONS.md D-1, D-2 | yes". Change line 124's "About
   20:00" to "19:53" and line 125's "About 21:20" to "21:12 (logged; the file text says about 21:20)".
6. **B. The v2 portfolio, per-chair and Deflated Sharpe numbers exist** (line 145).
   **Fix:** use Section S2-S4. Note that strategy 01's PREDECLARED adoption rule ("adds risk-adjusted return in IS,
   validation and OOS", line 191) is not in HYPOTHESIS_v2, which says only "evaluate it in the same windows". Either
   delete the adoption sentence or label it as strategy 01's rule. In-sample the sleeve lowers core_ER_6's selection
   Sharpe (0.928 vs 1.062) and raises validation (1.185 vs 0.912) and full IS (1.038 vs 0.998).
7. **G. Choose how to meet the track's OOS rule, and record the choice before acting.** The track asks for IS and OOS
   statistics and an equity curve for each; the v2 pre-registration evaluates OOS only if validation and the 2x gate
   pass. The draft does not address this conflict. **Fix (team decision, written down before anything runs):** either
   (a) report "OOS not evaluated, per the pre-registered gate" and show strategy 01's OOS as the only OOS evidence for
   the tone family, or (b) log a dated deviation that evaluates the chosen T4xE1 once on 2024-10-03..2026-10-02 for
   track compliance, labelled as outside the decision rule and unable to rescue it, and report it whatever it shows.
   Do not run (b) without that deviation entry.

## 2. Factual errors against the sources

8. **E. bbo-1s does not cover ZF** (line 91, "1-second best bid/offer for ZT, ZF, ZN and ES"). `<s>/presser_pull.log`:
   bbo-1s rows exist for ES, ZN, ZT only; ADDENDUM s1.3 "ZF has no bbo-1s". **Fix:** "1-minute and 1-second bars for
   ZT, ZF, ZN and ES, and 1-second best bid/offer for ZT, ZN and ES".
9. **E. Market data cover 74 trading days, not 75** (lines 91, 207 context). 75 dates were requested, 2020-03-15 is a
   Sunday (no data), `verify/v01_data_qa.json` `n_days` = 74, and 73 scheduled meetings enter BENCH-R (ADDENDUM s2).
   **Fix:** "75 press-conference dates (74 trading days with data; 73 scheduled meetings used)".
10. **E. USMPD correlation is -0.995, not -0.996** (line 91). From `events.csv`: ZT 13:50-14:20 return vs USMPD
    statement-window UST2Y change, corr -0.9954 (n = 73); ZT 14:20-to-end vs USMPD press-conference UST2Y, -0.983.
    **Fix:** "correlate -0.995 (statement window) and -0.983 (press-conference window) with its 2-year yield changes".
11. **E. The timing drop count is mis-described** (line 97). `events.csv` `drop_reasons`: 7 without captions, 4 with
    distorted caption timelines, 2 outside the downloaded window (one of them also has start uncertainty 58 s). Only
    one meeting is dropped for uncertainty above 30 s. **Fix:** "Meetings without captions (7), with distorted caption
    timelines (4) or outside the 13:30-16:30 data window (2, the unscheduled March 2020 meetings) are dropped from
    timing tests: 13 of 75, leaving 62."
12. **E. The risk section inverts strategy 01's de-risk finding and omits D-1** (line 187). In
    `strategies/01/review/replicate/SPEC_OURS.md` (sensitivities and audit notes) the six unscheduled 2019-20 de-risk
    dates are a small use of hindsight; removing them moves the Sharpe from 0.205 to 0.203; the 0.210 -> 0.203 move in
    VERDICT combines that with three corrected speech release dates. v2 keeps the unscheduled dates as registered
    (DEVIATIONS.md D-1) and reports a scheduled-only sensitivity (`sens_scheduled_only_is.csv`: full-IS 0.442 vs 0.441,
    i.e. immaterial). **Fix:** "Eight unscheduled actions and releases (2019-10-11, six dates in 2020, 2025-08-22) are
    also de-risked, as registered. They were not announced in advance, so this is a small use of hindsight (deviation
    D-1); a scheduled-only list changes the full in-sample Sharpe from 0.441 to 0.442."
13. **E. "Consensus follows strategy 01 exactly"** (line 105) is not exact. v2 T1/T2 have no hit-count keep rule
    (every document injects; `fedspeak_v2/backtest/README.md` item 4), whereas strategy 01 kept only documents with
    H+D >= 5. **Fix:** add "except that every document injects (no keep rule); the lexicon leg of T4 keeps strategy
    01's rule".
14. **E. Sample size for the 2016-2022 clean sample** (line 171, "<=39"). 39 meetings are timing-eligible, but the
    8-meeting burn-in means no position before 2018-03-21 (ADDENDUM s3.3); 31 eligible meetings fall after it.
    **Fix:** `[[PENDING: <=31]]`.
15. **E. Table 2's caption says "exit at conference end"** (line 165). H1-primary and the lexicon control exit at
    16:00 ET (ADDENDUM s3.5); only BENCH-R exits at the conference end. **Fix:** "Entry/exit: H1 and lexicon rows
    enter at the next 1-minute open after the conference ends and exit at 16:00 ET; BENCH-R holds from 14:20 to the
    conference end."
16. **E. Units are mixed in Table 2's lexicon row** (line 172). The columns are USD per contract; "-8.1 ticks" and
    "-12.1 ticks" are ticks. At $7.8125 per tick (all 2023+): -$63.28 and -$94.53 (`verify/v03_h1_lex.json`
    `ZT_primary_C2_ticks` / `C4_ticks`). **Fix:** use the dollar values.
17. **E. Table 2 BENCH-R OOS-slice 2-tick cell is computable, not pending** (line 175). Recomputed from
    `benchr_trades.csv` (ZT, `exit_tau_upper`, 2024-10-03..2026-10-02): n 15, gross +$22.40, measured +$14.58,
    2 ticks -$8.85, 4 ticks -$40.10, t 0.52. **Fix:** fill "-$8.85". Add that the 15 include the three Warsh
    conferences and exclude 2026-01-28 (zero statement-window sign).
18. **E. Model training location** (line 319, "RTX 5090 locally and RTX PRO 6000 GPUs on HiPerGator"). Every
    `metrics.json` in `<s>/chrono/full/models/` records `NVIDIA GeForce RTX 5090`; the scores used come from that run.
    **Fix:** "36 fine-tunes on a local RTX 5090 (the scores used); [[PENDING: HiPerGator replication, if run]]".
    Delete the status-box note on line 51 or restate it the same way.
19. **E. "Costs come from measured quotes, not assumptions"** (line 65) is true only for the press-conference study.
    v2 costs are assumed bp (lines 117). **Fix:** "Press-conference costs come from measured quotes."
20. **M. Gorodnichenko et al. effect** (line 75). The ~75 bp per 1 SD after ~5 days is for voice tone, significant at
    10% on 36 conferences (`<s>/fedtalk/literature/NOTES.md` s2). **Fix:** "Positive voice tone moves the S&P 500 about
    75 bp per standard deviation over about five days (36 conferences, 10% significance), but only about 1 bp at the
    minute level".
21. **M. Byun et al. wording and title** (lines 75, 248). Title: "The Fed's Fine-Tune: Coarse Statements and
    Predictive Pressers", July 2026 (`<s>/fedtalk/literature/finetune.txt`). Their claim is a stronger correlation with
    the future policy rate. **Fix:** "Press-conference content correlates more strongly with the future policy rate than
    statements or speeches do" and fill the reference title.
22. **M. Speech counts "doubled"** (line 214). 44 (2016) to 117 (2025) is 2.7x (`docs_to_score.parquet`).
    **Fix:** "rose from 44 (2016) to 117 (2025)".
23. **M. "all boilerplate"** (line 103). The audit's 60 repeated sentences include Clarida repeating his 2020
    framework sentences in 2021 (`team/nlp/README.md`, leakage audit). For model 2015 the 21 rows are repeats of
    earlier documents. **Fix:** "21 do, all sentences first published earlier and repeated later".
24. **M. 5,225 documents "including individual Q&A turns"** (line 63) also counts 2,026 reporter questions and 75
    duplicate statements. **Fix:** "1,098 documents; 5,225 scored units including 2,026 Chair answers and the questions
    before them".
25. **M. A4 "trade counts (285/285)"** (line 321) is the BENCH-R trade total across ZT, ZF, ZN and ES (70+72+72+71) for
    one exit, from `verify/v02_bench.json`. **Fix:** say so.
26. **M. One-tick share** (line 207, "96%"). Record-weighted from bbo-1s (ZT, 2023+, 14:30-16:00) it is 97.0%; no saved
    output backs either figure. **Fix:** commit the calculation and quote its output with the weighting stated.
27. **M. Liquidity figures have no source file** (lines 201, 203): $184bn ZN, $22bn 6E, TLT $2.75bn, UUP $33m. ZT
    2,108 / 529 contracts per minute were reproduced from the 1m cache (30 conference days 2023-2026). **Fix:** commit a
    script and its output for the daily-volume figures and cite it; until then mark them `[[PENDING: source]]`.

## 3. Consistency

28. **B. Two execution specs disagree on G3, and the draft follows the superseded one** (lines 135, 137, 42).
    `plan/MERGED_FINAL_PLAN.md` (written from 18:55 ET) says `bt/ADDENDUM.md` is "a superseded record" (s3.11, R2-04)
    and sets G3 as an HC3 t with a restricted wild bootstrap, two-sided by default (lines 131, 319), Holm m = 3 for
    BENCH-R, and different BENCH-R exit and era rules. The draft states the ADDENDUM's G3 (one-sided sign-flip on mean
    P&L). **Fix:** record the team's ratification (which spec, which sidedness) before any H1 result is viewed, cite it
    in line 135, and replace line 42's "merged plan v2 R2-04" with "MERGED_FINAL_PLAN.md s3.11". If both readings are
    computed, report both, with the ratified one named as the decision. Note in Limitations that H1 code from `bt/` is
    usable only after the final plan's changes are made and hashed.
29. **C. Tick size change is never stated in the body.** BENCH-R 2016-2019 mixes 1/128 (to the 2018-12-19 meeting)
    and 1/256 ticks (CME SER-8171), so "2 ticks/side" is $62.50 round trip before 2019 and $31.25 after; the break-even
    "1.0-1.4 ticks per side" (line 163) is 1.0 tick = $15.63 in the 1/128 era and 1.44 ticks = $11.23 in the 1/256 era
    (`benchr_cost_hurdle.csv`, `exit_tau_upper`). **Fix:** add one sentence to Data or Methodology: "ZT's tick fell from
    1/128 to 1/256 of a point ($15.625 to $7.8125 per contract) in January 2019 (CME SER-8171); cost rows use the tick
    of the day." Rewrite line 163: "break-even cost is $15.63 per side (1.0 tick, 2016-18) and $11.23 (1.4 ticks, 2019),
    against a measured half-spread of half a tick".
30. **C. BENCH-R n = 50, not 53, after 2020** (Table 2 line 174 vs ADDENDUM s2's 53). Three meetings have a zero
    statement-window sign (2020-09-16, 2023-07-26, 2026-01-28; `v02_bench.json`). **Fix:** footnote "50 of 53 meetings;
    3 with a zero sign take no trade".
31. **C. The OOS slices of H1 and BENCH-R use different rules.** H1's track-OOS slice (line 170, n 12) excludes the
    three Warsh meetings inside 2024-10-03..2026-10-02; BENCH-R's (line 175, n 15) includes them. The track rule says
    the OOS window is the most recent stretch. **Fix:** define the slice once ("all eligible meetings dated
    2024-10-03..2026-10-02"), state that H1 has no Warsh rows because Warsh is text-only/descriptive in the registered
    family, and list the Warsh rows separately as descriptive.
32. **C. Chair dates are used but never stated.** The by-chair rows need them. `corpus/build_meta.json` (Board
    membership page): Yellen 2014-02-03..2018-02-03, Powell 2018-02-05..2026-05-22, Warsh from 2026-05-22 (that day
    assigned to Warsh). These agree with HYPOTHESIS_v2 Amendment 1 and the team plan. **Fix:** add them to Data with the
    source.
33. **C. "Ann. return" is undefined in Table 1.** The strategy 01 rows use the arithmetic annualised mean excess
    return (2.34% IS; CAGR is 1.73%). **Fix:** label the column "Ann. excess return (arithmetic)" and use
    `ann_excess_arith` for the v2 rows.
34. **C. Summary leads with the futures expression** (line 63, "trades 10-year Treasury futures against the euro (or
    TLT/UUP)"). The chosen combination is T4xE1 (TLT/UUP). **Fix:** "trades TLT against UUP (or 10-year Treasury
    futures against the euro)".
35. **C. Status-box note on model counts is stale** (line 48). `team/nlp/README.md` and `team/hpg/README.md` both say
    36 now. **Fix:** delete the note. The other notes (audio 9.7 GB vs "2-3 GB" in `hpg/README.md`; stale "Next on this
    branch" in `strategies/01/review/README.md`) are still correct.
36. **C. Clock bias figure.** +28.8 s (n = 63) is the median of `events.csv` `v0_minus_sched_tv_s` and matches line
    130; GAP_REPORT A-02's +24 s (n = 61) is an earlier archive check. **Fix:** keep +28.8 s, name the source once,
    delete the line-47 note.
37. **C. ZN cost justification compares unlike windows** (line 117). The 0.5-tick half-spread is measured 13:30-16:30
    on FOMC days; E2 fills at the daily close. **Fix:** "1 bp is about 1.4 times the half-spread we measured around
    FOMC announcements", and add a 6E line (at about 1.10, one tick of 0.00005 is about 0.45 bp, so 1 bp is about
    four half-spreads; verify against a quote sample).
38. **C. Video size.** `team/data/fomc_pressers/README.md` says about 65 GB; `fetch_report.json` says 67.4 GB
    (62.8 GiB in `fed_presser_hpg/manifest/README.md`). The draft cites hours (82.4 h, verified) only. **Fix:** none in
    the note; align the READMEs.

## 4. Guideline and rubric coverage

39. **B. The code repo does not contain the code behind the results.** `git ls-files` in `team/` has no v2 backtest
    (`fedspeak_v2/backtest/run_v2.py`, `v2lib.py`, `wire/`), no corpus builders, and no press-conference backtest
    (`presser_bt/backtest`, `events`, `text`, `verify`, ADDENDUM code). The track requires the repo link and judges
    score reasoning backed by code. **Fix:** commit these (without licensed Databento data or scratch paths) before
    Sun 2026-10-04 11:00 ET, and point every table caption at a repo path.
40. **G. IS/OOS statistics for the press-conference study.** The track asks for annualised return, volatility,
    Sharpe, max drawdown, turnover and an equity curve for IS and OOS; the ADDENDUM rules out an annualised Sharpe for
    BENCH-R and a net Sharpe for H1. Line 165 justifies omitting Sharpe but not the other items. **Fix:** report for
    BENCH-R per era: max drawdown of cumulative P&L per contract, turnover (about 8 round trips a year), and the equity
    curve (Fig. 2a), and add one sentence: "Annualised Sharpe is withheld by pre-registration (ADDENDUM s5) because
    eight events a year give a meaningless estimate."
41. **G. Capacity of the chosen expression.** Line 203 concludes E1 does not scale and E2 is "the deployable version
    if the two perform alike". The chosen combination is E1 (T4xE1), and T4xE2's full-IS 2x Sharpe is 0.377. **Fix:**
    state that the chosen sleeve's capacity is bound by UUP (about $3.75m at 11% of daily volume at $10m capital) and
    give E2 as the scalable alternative with its own IS numbers.
42. **G. Risk management (rubric 3) lacks a stop rule, margin and stress.** Line 195 says there is no drawdown stop;
    margin is pending (line 205). **Fix:** add (a) the in-sample worst drawdown of the chosen sleeve (-18.8%) and
    strategy 01's OOS worst quarter (Q4 2024, -11.8%) as the stress case; (b) correlation with core_ER_6 (0.025 full IS,
    `summary_is.json`); (c) a monitoring rule, labelled untested, or say plainly that none is proposed because the
    strategy is not deployed; (d) ZN/6E initial margin from CME with date.
43. **G. Failed-ideas list.** It is present (lines 222-230, A2). Numbers checked against source: overnight drift
    (gross 0.75, 1x 0.25, 2x -0.24), intraday momentum (gross 0.52, 1x -0.31, 1.26 bp/trade), pre-FOMC drift (11.9
    bp/event IS 1x, -4.3 bp 2024-26), hourly trend (-0.65), month-end ZN (0.866), auction (selection 0.77, validation
    -0.38), strategy 01 rows. Not traced in this review: GTAA "9.7% of 72", carry 0.03/0.25, value COMBO 0.23/-0.60,
    EWMAC -0.135/-0.54/8.6%, turn-of-month t 0.06 and ZN -1.07, intraday momentum "49% in 50 days", pre-FOMC "70%".
    **Fix:** attach the source file path to each A2 row in the repo version and recheck those not traced. Add v2's own
    failure (Section S1) as the first row.
44. **G. Survivorship, corporate actions, missing data** (lines 93-97): covered. ETF adjustment checked
    (`data/download.py` uses `auto_adjust=True`); DGS2 forward-fill from the past only checked (`v2lib.py`). No fix
    beyond item 11.
45. **G. Data-source citations.** Missing: CME ZT contract specification (the $200k face value behind $15.625 /
    $7.8125), the Board membership page as the chair-date source (it is listed among Board pages; name it), Hugging Face
    as the host of the models and dataset. GDELT and Internet Archive terms are already marked pending. **Fix:** add
    them to Data sources.
46. **G. Innovation statement versus the result.** The chosen T4 averages the failed lexicon with the new model, and
    its validation Sharpe (0.687) equals frozen Variant A's on the same window (0.691); Variant A with the 2015 warm-up
    has the same selection Sharpe (0.153 vs 0.154). The stance model alone (T1, T2) has negative selection Sharpes.
    **Fix:** say this in Results; keep the three methodological extensions in the Summary as the contribution, and do
    not imply the model improved returns.
47. **G. Licensing.** The labels (CC BY-NC 4.0) make the fine-tuned models non-commercial; line 216 says so. Keep it
    in the body, since the event has sponsors.
48. **G. Every team member can explain the strategy** (line 41): still pending; schedule the walkthrough before
    10:00 ET.

## 5. Placeholders and invented content

49. **No invented H1, H2/H3 or v2 OOS number was found.** H1 rows in Table 2 are placeholders; the confirmation n of 20
    and the slice n of 12 are counts of eligible meetings (`events.csv`, ADDENDUM s2), not results. Keep them labelled
    "eligible meetings".
50. **M. Placeholder format.** Several placeholders lack a source (`[[PENDING]]` in Tables 1-2, line 4, lines 295,
    323). **Fix:** use `[[PENDING: what, source file]]` throughout, for example
    `[[PENDING: H1-primary gross USD, G3 output of the ratified code]]`.

## 6. Page budget

51. **P. The body is already over budget before Results are written.** Word count of sections 1-8, excluding tables,
    rubric lines and placeholders: 2,864 (Summary 185, Hypothesis 374, Data 379, Methodology 828, Results 158, Risk
    324, Liquidity 231, Limitations 385), against the box's own target of 2,490. At 11 pt with 1-inch margins (about
    560-600 words of prose per page), Table 1 (about 0.35 page), Table 2 (0.3) and two figures (about 0.6) leave room
    for about 2,100-2,200 words. Results still need about 250 words. **Fix:** cut about 900 words:
    - Methodology 828 -> 500: move the label re-dating detail, leakage counts and the pre-registration timeline to
      Appendix A1/A3; keep one sentence each.
    - Hypothesis 374 -> 280; Data 379 -> 300; Limitations 385 -> 300 (failed ideas as one compact line with the
      numbers, details in A2).
    - Table 1: drop the strategy 01 2x rows (put 2x Sharpe in a column) and replace the two OOS rows with one
      "not evaluated" row: 11 rows -> 7.
    - Fig. 2: one panel only if space is short (BENCH-R cumulative P&L by era); move the spread panel to A5.

## 7. AI attribution

52. **OK.** No occurrence of the assistant's name, the vendor name, or a scratch path in the body. The one-line
    disclosure (line 139) matches the requested wording. Line 55 (status box) mentions the scratch folder name rule;
    the box is deleted before the PDF. **Fix:** move the disclosure line to the end of Section 8 or the References
    header so it does not sit inside Methodology's word count; wording unchanged.

## 8. Verified as written (no change needed)

Text and data counts: 828 of 828 speeches; 97 statements, 94 minutes, 79 transcripts; 2,026 answers; 68 of 75 with
captions; 82.4 video-hours; 2,480 labels; 2,336 re-dated rows, median gap 7 years; leak counts 491 vs 21 for model
2015; training rows 1,606-2,480; statement times 0 mismatches (`corpus/build_meta.json`). Clock: median +28.8 s
(n 63); start uncertainty median 9.3 s (eligible); 40 of 62 earlier entry bars under the convention. ZT.c.0 delivery
month on 42 of 73 days (GAP_REPORT A-01). Databento $8.53. Placebo best-of-8 mean 0.198, p90 0.833 (40 seeds,
`verify/placebo_seeds.csv`). DSR trial count 11. OOS window 2024-10-03..2026-10-02 and the 10.75-year / 2.15-year
arithmetic. BENCH-R: +$27.73 (t 0.94, n 20), -$35.31 (t -1.15, n 50), 2022 -$267.58 per meeting, break p 0.146,
measured and 2/4-tick rows. Lexicon control: -$32.03, measured -$39.84, t -1.47, CI upper 0.60 ticks. Power 0.29 at
n 20, rho 0.3. Strategy 01 Table 1 rows (2.34%, 11.2%, 0.210, -33.5%, 24.5; 2x 0.162; OOS -4.97%, 10.9%, -0.456,
-15.6%, 23.3; 2x -0.502), 0.53 correlation, alpha 2.3%/yr t 0.84, 75% from 2022, Q4 2024 -11.8%, futures version
0.36/0.10. Sizing rules (clip 2, 10% target, 20/60-day vol, 4% floor, 1.5 cap, 10% band). Solo-entry cross-check
0.28 / -1.05.

---

## S. Numbers now available for the v2 placeholders (exposure warning applies)

All from `<s>/fedspeak_v2/backtest/` (written 19:08 ET). Excess over T-bill, net of costs unless stated. Chosen
combination: **T4xE1** (average of lexicon and stance-model z, 75% TLT / 25% UUP).

**S1. Table 1 rows (T4xE1)**

| Window | Ann. excess (arith.) | Vol | Sharpe 1x | Sharpe 2x | Max DD | Turnover (x/yr) |
|---|---|---|---|---|---|---|
| Selection 2016-01-04..2020-12-31 | 1.25% | 8.1% | 0.154 | 0.053 | -16.1% | 35.0 |
| Validation 2021-01-04..2024-10-02 | 10.00% | 14.6% | 0.687 | 0.664 | -17.8% | 15.9 |
| Full IS 2016-01-04..2024-10-02 | 5.00% | 11.3% | 0.441 | 0.387 | -18.8% | 26.8 |
| OOS 2024-10-03..2026-10-02 | not evaluated (decision rule failed) | | | | | |

Decision rule: validation 0.687 > 0 (pass); full-IS 2x 0.387 <= 0.5 (fail). Validation against the 0.7 target:
-0.013. Gross full-IS Sharpe 0.507. Other 2x columns are not in the saved outputs (mark n/r or recompute from
`daily_T4xE1_is.parquet`).

Selection-window net Sharpe of all eight combinations (`selection.csv`): T1xE1 -0.582, T1xE2 -0.358, T2xE1 -0.346,
T2xE2 -0.177, T3xE1 -0.205, T3xE2 -0.065, T4xE1 0.154, T4xE2 0.151.

Variant A reference on the 2016+ windows (`windows_all.csv`, frozen T0fxE1): selection -0.013, validation 0.691,
full IS 0.355 (2x 0.312), ann. excess 4.18%, vol 11.8%, max DD -20.7%, turnover 23.2. With the 2015 warm-up
(T0v2xE1): 0.153 / 0.638 / 0.400.

**S2. Deflated Sharpe** (`summary_is.json` `dsr`; 11 trials, row 3 of Variant A's log repeats row 2): selection
window 0.223, full IS 0.436; n = 10 sensitivity 0.232.

**S3. By chair, in-sample** (`by_chair_is.csv`): Yellen 2016-01-04..2018-02-02, Sharpe 0.031 (2x -0.073); Powell
2018-02-05..2024-10-02, 0.537 (2x 0.494). No Warsh days in-sample.

**S4. Portfolio test** (`portfolio.csv`): core_ER_6 alone vs with T4xE1 as a fourth equal-risk sleeve: selection
1.062 vs 0.928; validation 0.912 vs 1.185; full IS 0.998 vs 1.038. Correlation of the sleeve with core_ER_6, full IS:
0.025.

**S5. Falsifiers:** listed in item 2. Scheduled-only de-risk sensitivity: item 12.
