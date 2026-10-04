
---

## J. Changes in round 3 (`r3_patch`, 2026-10-03)

Round 3 received 52 hole reports from five lenses (statistics 12, execution 11, data engineering 9, validity 9,
economics 11). After deduplication they are 42 distinct holes (1 critical, 11 high, 18 medium, 12 low); all 42 are
addressed by R3-01..R3-42 (section F.8). Key evidence was spot-checked before patching: the D1a text in
`DEVIATION_D1_stance_model.md`, `checks_r3_validity/r3_label_dates.out` and `r3_code_paths.out`,
`checks_r3_data_eng/r3_checks_output.txt` s5, `checks_r3_econ/r3_econ_checks.out` s1-s6 and the Databento licensing
sentence (re-fetched). Choices that differ from a lens's suggestion are noted.

**Critical**

1. The code path trains on the shuffled `year` column; team Update D1a (re-dated labels) was never adopted, so the
   gate, R2-10, D-VAL, the 2016-2022 rows and H4 features are look-ahead-contaminated → R3-01 (source-date rule,
   reprinted counts, training-row audit, threshold confirmed before any gate number). [validity]

**High**

2. R2-31(4) turned the locked terminal G5 kill into a retry loop on a near-single-draw p90 → R3-35 (locked kill
   restored; one measurement presser; D_frozen as locked; pooled re-evaluation can only kill). Not adopted: the
   stats lens's alternative "at most one retry" amendment, which would change a locked gate. [stats; execution
   medium merged]
3. Robustness labels fire on "one significant, the other not" and barely separate true from false GOs → R3-19
   (estimate-difference rule, published firing rates, LR < 1.5 demoted). [stats]
4. Sidedness and the single base could be ratified after per-meeting 2023-2026 scores exist → R3-04 (PREREG-R before
   any 2023-2026 presser scoring; PREREG-D before outcomes; D-DOM/D-VINTAGE on 2016-2022 until PREREG-R). [stats]
5. Failures declared after the fill could void counted trades → R3-36 (commit at t_fill; watchdog-stamped pre-fill
   failures only; no H1-P drops). [execution]
6. "Next-day" Databento pulls could fall inside the licensed intraday window and on non-final data → R3-38 (25 h
   rule enforced in code, condition check, governing first file, T + 30 refetch). [execution]
7. The 2-GPU rule is not enforced: R2-36 lanes allow 3-4 GPUs, the package's guard is a name grep with an override,
   and the pushed team runner runs 4 GPUs in bf16 on an unconfirmed allocation → R3-41 (one job name `fp-gpu` with
   singleton, ≤ 2 GPUs per job, no GPU arrays, audit, training job without wait loop; team runner converted,
   replication only, allocation checked). [validity; execution and data_eng mediums merged]
8. Non-spec chrono scores and production-key checkpoints on presser text exist outside the record; the smoke script
   trains real fine-tunes and prints a confirmation meeting's H1 gap; the fingerprint is incomplete → R3-02
   (inventory, seal, quarantine, reworded precondition, attestation), R3-03(2)-(3),(5). [data_eng]
9. Three incompatible τ_used definitions; GDELT missing for 11 of 20 anchored meetings; CNBC-first takes the earlier
   bound; a step counted twice → R3-13 (one max over sources × stations × windows, Δ_missing, GDELT re-pull, per-τ_k
   bound table). [data_eng]
10. A third D1 implementation (team_push) with a different score function, precision and keying, already wired into
    `bt` → R3-03(1),(4) (one named code base, guard in `bt`), R3-02 (its scores sealed). [validity]
11. The Tier 0 checkpoints (b2022, b2023, b2024) are never validated → R3-08 D-VAL-C. [validity; stats medium
    merged]
12. The locked lexicon control cannot be computed as frozen (MIN_HD), and two records read it oppositely while
    results sit sealed → R3-06 (locked result "not estimable as frozen"; LEX-RAW Tier 3; locked "Negative control"
    reading governs; A-39(1) withdrawn). [econ]

**Medium**

13. Answers ending just after 15:00 ET fail the 20-cue window and collapse H1-run → R3-14 (leading-window and
    previous-item fallbacks, merged legs, meetings never dropped; Tier 0 τ unchanged with a printed count). The two
    lenses differed on Tier 0; the stats lens's narrower scope was kept. [stats, data_eng]
14. H1-pooled re-uses the Tier 0 sample and demotes D1's disjoint 2016-2022 sample → R3-21 (H1-clean in Tier 2,
    H1-pooled Tier 3, m = 9; Tier 3 row with the locked covariates on 2016-2022, R3-21(3)). [stats; econ low on
    R2-21 vs D1's locked covariates merged]
15. Simulated size inflation is not acted on; pooled tests unsimulated → R3-20 (G3 critical value = max of WRE and the
    ICC 0.05 simulation quantile; cluster-by-year bootstrap for multi-year Tier 2 tests). Not adopted: a year-cluster
    bootstrap for confirmation-sample tests (four clusters); they use the G3 rule instead. [stats]
16. R2-33 made a net-P&L Sharpe the A-43 statistic against the locked "No net Sharpe on H1" → R3-34 (gross mid-to-mid
    statistic; net as hurdle lines). [stats]
17. D-VAL-W blindness and addenda that could retroactively switch counted events → R3-09 (blind to model outputs;
    verdicts act forward only; labeller exposure recorded). The stats lens's restriction to pre-PREREG pressers was
    not needed once verdicts act only on later events. [stats, validity]
18. Read bans swallow the prospective events; H1-P eligibility conflicts with a slipping freeze → R3-05. [stats;
    execution low merged]
19. Counted fill instant defined three ways; settlement rule tests τ_used → R3-37. [execution]
20. BENCH-R Tier 1 statistic not pinned (gross vs costed); tick units change in 2019 → R3-31 (gross bp decisive by
    default; costed versions outside Holm; team may name one costed version in PREREG-R). [execution]
21. H1-exec-live does not reproduce the live end detector → R3-39. [execution]
22. Warsh-era a, σ and statement-term rules inconsistent; 4-6 qualifying statement sentences → R3-40 (shrunk a,
    noise-adjusted σ, empty-S rule, logs, Tier 3 companions, one b2024 set). Chose the analytic binomial adjustment
    over a bootstrap ratio or per-chair shrinkage because it is deterministic at the first Warsh event. [validity, econ;
    execution low merged]
23. Truncation list and the 1 s rule on the VTT clock; undefined last chair answer → R3-15. [data_eng]
24. H1-P clock contradiction (A-41 vs R2-32(2)); gaps squeeze the aligner → R3-16. [data_eng]
25. Licence of NC-derived files in a public repo; fedspeak_v2 sleeve and sponsor uses → R3-07. [validity]
26. D-DOM and R2-11 variance-ratio rules fire on co-movement → R3-23. [econ]
27. Opening remarks preview Q&A tone in 2016-2022 → R3-25 (D-OPEN, H1-O, label). [econ]
28. ZLB years pooled with 2022-26 → R3-22 (Tier 3 ZLB and vol-scaled rows, regime-scaled OCs, residualiser from
    2022-03-16). Not adopted: ZLB terms in the H1-clean decision model (43 observations; ZLB covers 15 of its 23
    post-2020 meetings). [econ]
29. SEP and dot-plot release uncontrolled → R3-26. [econ]
30. Outgoing-chair regime from mid-2025 → R3-27 (sources secondary; original report not opened). [econ]

**Low**

31. R2-13(iii) centring cancels in s; argmax scaling can blow up → R3-10. [stats]
32. Round-2 BENCH-R choices not marked in the provenance table → R3-24. [stats]
33. Measured spreads exclude implied liquidity; ZF quotes missing; 2017 construction change → R3-33. [execution]
34. BENCH-R-P exit differs from historical BENCH-R → R3-32. [execution]
35. Whisper decoding and batch sizes not frozen → R3-17. [data_eng]
36. Raw TV pages deletable before aligner anchors; no IA check for uncaptioned meetings → R3-18. [data_eng]
37. No reference platform for H2/H3 tables → R3-42. [data_eng]
38. H1-RoBERTa runs without the weight-history check → R3-11. [validity]
39. ChronoBERT cutoffs unverified; `reference_compile: null` → R3-12. [validity]
40. Pre-meeting run-up omitted → R3-28. [econ]
41. Concurrent-news exclusion can be post-treatment → R3-29. [econ]
42. Outcome-window length varies with s and by chair → R3-30. [econ]

**Not changed in round 3.** The locked family table text (section A.2, Spec and Role columns), the locked {2, 4}-tick
stress (kept as the costed BENCH-R versions and the hurdle lines), "No net Sharpe on H1" (restored for the A-43
statistic), "No LLM in the primary path", "No 1s bars without a new user-approved quote", the 15:59 exit of A-03, the
H2/H3/H4 specifications and Holm m in Tiers 1 and 2. Items that need people rather than text: the team's PREREG-R
ratifications (R2-01 option and score function, A-03, R2-13 base, R2-19 exit, R3-03 code base, R3-06 reading, R3-31
statistic) and the R3-01(3) threshold confirmation; every member's attestation about the sealed outputs and the
non-spec chrono outputs (R2-03(4), R3-02); the user's decisions on the data purchase, the ZF bbo-1s quote (R3-33),
pushing the team-runner and NOTICE fixes and telling teammates (R3-07, R3-41), and the `ai-workshop` allocation;
written sponsor confirmation for HiPerGator.
