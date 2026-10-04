
---

## I. Changes in round 2 (`r2_patch`, 2026-10-03)

Round 2 received 63 hole reports from five lenses (statistics 13, execution 10, data engineering 13, validity 14,
economics 13). After deduplication they are 48 distinct holes (3 critical, 12 high, 24 medium, 9 low); all 48 are
addressed by R2-00..R2-36. One further fact found while merging (the parallel pipeline's `results/` and `tables/`,
written 17:48-17:57 ET, after v1) is folded into item 3. Sub-claims checked and rejected or not adopted are noted.

**Critical**

1. Two incompatible scorer records for H1-primary: team deviation D1 (17:13 EDT) vs v1's A-40/A-14/A-10/section G,
   which never cited D1; two-scorer false GO 0.079-0.097 → R2-01 (default D1 with ratified score function; A-40
   gates and the 10-14 deadline withdrawn under that option; H1-pooled and H1-RoBERTa slots; m kept at 9), A-10, A-14,
   A-35, A-40 markers, section G. [stats, execution, data_eng, validity, econ] Not adopted: deleting the Tier 2 slot
   (m 9 → 8; data_eng), because BENCH-R-ES numbers already exist on disk; turning the accuracy gate into a label only
   (validity), because a failed gate should stop G3 rather than let a weak scorer decide it.
2. A second execution spec (bt/ADDENDUM.md) and a second code path disagree with v1 on the G3 statistic, residualiser,
   aggregation, exec30, BENCH-R exit and era, latency and clock → R2-04 (supersession table, one code path). [data_eng]
3. Paid 1m/1s/bbo-1s data on disk before any freeze; outcome windows readable before H1; and (found in the merge)
   BENCH-R, lexicon H1-primary and lexicon H1-answer results already written by the parallel pipeline, including the
   2023-2026 τ→16:00 windows → R2-00 (inventory with hashes), R2-03 (purchase confirmation, moratorium, sealed
   outputs, attestation and labels, A-12 reworded, split requests, provenance), header correction. [data_eng, stats]

**High**

4. A-40 postponement plus "H1-chrono runs as registered" would make a late G3 non-blind → R2-02 (no 2023-2026
   post-14:20 reads while G3 waits; cancellation date 2027-01-31). [stats]
5. D-VAL-W depends on prevalence, its sample does not exist as written, and its gold standard can invert → R2-09.
   [stats, validity]
6. BENCH-R exit changed to start + 60 min as an "implementation detail"; horizon differs by era → R2-19 (presser-end
   from metadata, ratify; start + 60 Tier 3; label). [execution, econ]
7. Live delay has no single meaning; frozen delay has no role; (ii) omits stream lag → R2-31(1)-(4). [execution]
8. ADDENDUM τ is not an upper bound (median 30 s earlier than τ_used) → R2-04 clock fork. [data_eng]
9. r1 anchor rules cut the confirmation n from 20 to 16 by criteria the locked rule lacks → R2-16. [data_eng]
10. ε is item- and station-specific and uncalibrated for the confirmation era → R2-17. [data_eng]
11. A-05 clock-source tests cannot fail → R2-18 (aligner-independent completeness, Whisper-seeded aligner, valid
    rule (b), WhisperX-default correction). [data_eng]
12. Walk-forward checkpoints feeding paper trades and v2 are trained on HiPerGator without determinism → R2-05 (local
    5090, deterministic flags, `sdpa`, 45 fine-tunes hashed; HiPerGator replicates). [data_eng, validity, execution,
    econ; validity low (attention backend) merged]
13. The TDW filter removes decision, guidance and balance-sheet sentences from hawk(statement) → R2-11. [validity]
14. Official weights may never pass the reproduction gate → R2-06. [validity]
15. D1's base switches on 1 January inside the confirmation sample → R2-13 (H1-1base, D-VINTAGE, per-base centring,
    label; single 2022 base recommended, not defaulted, because D1's text names the per-year rule). [econ]

**Medium**

16. D-VAL passes a scorer with no within-meeting content → R2-07(1). [stats]
17. Walk-forward D-VAL lacks 2011-2015 models → R2-08. [stats, validity]
18. H1-P sidedness, degrees of freedom and reference distribution → R2-25(1)-(4). [stats, econ]
19. Pooled 2016-2026 test ignores the 2020 break → R2-21. [stats, econ]
20. BENCH-R Tier 1 recomputes seen USMPD numbers → R2-19(4)-(5) (renamed; BENCH-R-P), R2-03(7). [stats]
21. Warsh 15:01 settlement rule enters before the decision → R2-31(5). [execution]
22. Pre-2017-05-21 legacy feed, synthetic timestamps; BBO price field is the last trade → R2-22. [execution]
23. Quote-fill priced at τ_used, not the locked entry → R2-34. [execution]
24. Live references unconfirmed; dropped segments, clock steps, PDT trust; HLS segment clock → R2-32. [execution,
    data_eng]
25. Two R_stmt definitions; shared 14:20 print builds in bounce → R2-20. [execution]
26. Paper costs counted twice; A-43 statistic undefined → R2-33. Rejected sub-claim (by its own lens): t_{k−1} vs
    t_{k−3} matters little (size 0.052 vs 0.055). [execution]
27. The squeue 2-GPU guard is unreliable and blocks the plan's own arrays → R2-36(1). [data_eng]
28. Two confirmation days are vendor-degraded → R2-23. [data_eng]
29. Rows that need data outside the cached window; ADDENDUM's 2016-19 era → R2-24. [data_eng]
30. No runbook for the freeze-critical GPU batch → R2-36(2). [data_eng]
31. Statements are not a TDW document type; statement-level ρ unused → R2-07(2). [validity]
32. The pooled accuracy gate mostly measures minutes and speeches → R2-10. [validity]
33. H1-Q drops the questions → R2-12. [validity]
34. fedspeak_v2 results would expose the confirmation sample → R2-35. [validity]
35. H4 trains on in-sample text scores → R2-14. [validity, stats]
36. SEP composition confounds the BENCH-R break → R2-30(1), R2-19(3), R2-21. [econ]
37. G3 NO-GO "Stop" not reconciled with the register → R2-26. [econ]
38. No statement of how often a GO is a true edge → R2-27. [econ]
39. No test separates statement-text drift from Q&A diffusion → R2-30(2). [econ]

**Low**

40. A-11 simulation ignores the persistence and realised design of s → R2-28. [stats]
41. Mean statistics without an intercept mix drift and predictability → R2-29. [stats]
42. H1-P called "the confirmation" → R2-25(5), A-41 marker. [stats]
43. Raw archive caption pages cached → R2-15(3). [data_eng]
44. The chrono tokenizer is not chronological → R2-15(1). [validity]
45. TDW code is CC BY-NC → R2-15(2). [validity]
46. Blind events come from a different policy cycle → R2-30(3), R2-25(5). [econ]
47. ZF/ZN/ES robustness rows missing → R2-30(4). [econ]
48. Morning Treasury supply news outside the flag window → R2-30(5). [econ]

**Not changed in round 2.** The locked family table text (section A.2, Spec and Role columns), the locked {2, 4}-tick
stress, "No net Sharpe on H1", "No LLM in the primary path", the 15:59 exit of A-03, the H2/H3/H4 specifications and
Holm m in Tiers 1 and 2. "No 1s bars without a new user-approved quote" stands; whether the 1s data on disk were
approved is the user's answer (R2-03(1)). Items that need people rather than text: the team's dated choice between
option D1 and option v1 and its ratification of the score function (R2-01), the BENCH-R exit (R2-19), A-03 and A-10;
every team member's attestation about the sealed outputs (R2-03(4)); the user's confirmation of the data purchase,
the 2026-10-28 reference set and any caption-capture hardware (R2-03, R2-17, R2-32); written sponsor confirmation for
HiPerGator.
