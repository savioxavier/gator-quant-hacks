import re, pathlib
P = pathlib.Path("<solo-repo>/research/fed_presser_plan")
B = pathlib.Path(__file__).parent
t = (P / "merged_plan_v2.md").read_text(encoding="utf-8")
f8 = (B / "f8.md").read_text(encoding="utf-8")
jj = (B / "j.md").read_text(encoding="utf-8")


def rep(old, new, count=1):
    global t
    n = t.count(old)
    assert n == count, (n, old[:90])
    t = t.replace(old, new)


def after(old, add):
    rep(old, old + add)


# ---- header
rep("(hardened), merged v2", "(hardened), merged v3")
rep("and review round 2 (label `r2_patch`). Sections A-E",
    "review round 2 (label `r2_patch`) and review round 3 (label `r3_patch`). Sections A-E")
after("appended the round-2 change list (section I); in-place markers **[R2-nn]** point to F.7.",
      " Round 3 added section F.8 (R3-01..R3-42), revised the register (section G) and appended the round-3 change list"
      " (section J); in-place markers **[R3-nn]** point to F.8.")
after("inside the 2-GPU rule enforced by the scheduler (R2-05, R2-36).",
      "\n\n**Round-3 headline for the reader.** (1) The plan's trainer dates labels by the shuffled `year` field of"
      " `fomc_communication`; the team's own Update D1a re-dates them, and R3-01 adopts it (Tier 0 unaffected; the"
      " accuracy gate, D-VAL and the 2016-2022 rows were contaminated). (2) Non-spec chrono scores and checkpoints on"
      " presser text, and a third pushed D1 code base, exist outside the record; they are inventoried and sealed, one"
      " code base is named, and the team ratifies all rules in **PREREG-R** before any 2023-2026 presser text is scored,"
      " then hashes data in **PREREG-D** before outcomes (R3-02..R3-04). (3) The lexicon control is not estimable as"
      " frozen; its locked \"negative control\" reading is restored (R3-06). (4) G5 is again terminal as locked"
      " (R3-35); counted decisions are committed at the fill (R3-36); next-day data pulls wait 25 h (R3-38). (5) One"
      " τ_used formula (R3-13), answer windows across 15:00 ET (R3-14), estimate-difference labels with published"
      " operating characteristics (R3-19), a size-controlled G3 critical value (R3-20), and the disjoint 2016-2022"
      " sample (H1-clean) in Tier 2 (R3-21). (6) HiPerGator GPU work runs as one `fp-gpu` singleton job with at most"
      " 2 GPUs (R3-41), the user's rule restated this round.")

# ---- A.2 table and extension list
rep("R2-16..R2-18 (clock), R2-20, R2-25..R2-28 |",
    "R2-16..R2-18 (clock), R2-20, R2-25..R2-28; **r3:** R3-01, R3-04, R3-08, R3-10, R3-13..R3-16, R3-19, R3-20, R3-35..R3-40 |")
rep("**r2:** R2-01, R2-34 |", "**r2:** R2-01, R2-34; **r3:** R3-14 |")
rep("R2-22 (legacy feed), R2-24 (2011-19 era kept) |",
    "R2-22 (legacy feed), R2-24 (2011-19 era kept); **r3:** R3-31 (decisive statistic in bp), R3-32, R3-33, R3-38 |")
rep("A-33 (A/V skew), A-16 (ECAPA threshold; r1) |", "A-33 (A/V skew), A-16 (ECAPA threshold; r1); **r3:** R3-42 |")
rep("A-31 (valence excluded); **r2:** R2-14 |", "A-31 (valence excluded); **r2:** R2-14; **r3:** R3-01 |")
rep("| A-39 (r1: same statistic; fixed interpretation; read as a weak-measure comparison, not a null) |",
    "| A-39 (r1: same statistic; fixed interpretation; ~~read as a weak-measure comparison, not a null~~); **r3:** R3-06"
    " (not estimable as frozen, MIN_HD; LEX-RAW Tier 3; the locked \"Negative control\" reading governs) |")
rep("**D-STMT-PATH** and the R2-30 rows. Every test has one tier",
    "**D-STMT-PATH** and the R2-30 rows. Added in round 3: **H1-clean** (Tier 2; H1-pooled moves to Tier 3) (R3-21),"
    " **LEX-RAW** (R3-06), **D-VAL-C** (R3-08), **D-OPEN**, **H1-O** and **H1-A-O** (R3-25), **H1-SEP** (R3-26),"
    " **H1-RUNUP** (R3-28), **H1-L** (R3-30) and the R3-13, R3-22, R3-27, R3-39 and R3-40 rows. Every test has one tier")

# ---- A.5, A.7, A.8, A.9
rep("measurement-only. Warsh live",
    "measurement-only. **[R3-35: terminal; one measurement presser; R2-31(4)'s retry withdrawn]** Warsh live")
rep("R2-03 exposure labels]** |",
    "R2-03 exposure labels; (r3) R3-04 PREREG-R before scores and PREREG-D before outcomes; R3-20 critical value]** |")
rep("(r2) R2-31 fill rule and D_frozen, R2-32 references]** |",
    "(r2) R2-31 fill rule and D_frozen, R2-32 references; (r3) R3-35 locked kill restored, R3-36 commit at t_fill,"
    " R3-37 fill instant, R3-38 25 h data rule, R3-34 gross statistic]** |")
after("\"paper trading unaffected\" (A-30) is an UNVERIFIED legal reading.",
      " **[R3-07]** NC-derived files get a NOTICE or ship without label text, and every downstream use of NC-derived"
      " scores (fedspeak_v2 sleeve, sponsor, prize or demo uses) carries the per-scorer flag.")
after("extras outside the cached window get a printed quote first.",
      " **[R3-33]** ZF.v.0 bbo-1s for the 75 cached days: $0.96 (free get_cost), for the user's decision.")

# ---- C, D
after("| Gap review 2026-10-03 | 3 | 16 | 19 | roll symbol, wall-clock anchor, H1 exit (critical); see GAP_REPORT.md |",
      "\n| Review round 1 (`r1_patch`) | 2 | 20 | 22 | MP4 truncation, statement dominance; section H |"
      "\n| Review round 2 (`r2_patch`) | 3 | 12 | 15 | two scorer records, second spec, data on disk; section I |"
      "\n| Review round 3 (`r3_patch`) | 1 | 11 | 12 | label dates (D1a), G5 retry, non-spec chrono outputs, GPU cap; section J |")
after("H1-P and BENCH-R-P are the only fully blind evidence (R2-00, R2-03, R2-19, R2-25).",
      "\n\nAdded in round 3:\n\n"
      "12. **Unregistered code and outputs.** Three D1 implementations and non-spec chrono outputs on presser text existed\n"
      "    before any ratification, and the plan's own trainer dated labels by a shuffled field (R3-01..R3-03). Blindness\n"
      "    of the choices now rests on the PREREG-R timestamp and attestations (R3-04).\n"
      "13. **The live path can be retried or edited after the outcome.** Fixed by restoring the terminal G5 (R3-35),\n"
      "    committing at the fill (R3-36) and one fill instant (R3-37); its power remains low (A-43).")

# ---- E checklist
rep("- Smoke Powell presser + 2026-09-16 Warsh: PDF + video,",
    "- Smoke Powell presser **[R3-03(5): 20200303]** + 2026-09-16 Warsh **[text scores sealed until its D-VAL-W labels"
    " are hashed]**: PDF + video,")
rep("replace the squeue guard by two singleton GPU lanes (R2-36)",
    "replace the squeue guard by ~~two singleton GPU lanes (R2-36)~~ one `fp-gpu` singleton job name (R3-41)\n"
    "- **Added (r3), in this order (R3-03(5), R3-04):** the team ratifies and timestamps PREREG-R (R2-01 option and score\n"
    "  function, A-03 with sidedness, R2-13 base rule, R2-19 exit, R3-31 BENCH-R statistic, R3-03 code base, R3-06\n"
    "  lexicon reading, R3-01 date rule and threshold confirmation, R3-19/R3-20 rules) before any 2023-2026 presser text\n"
    "  is scored; then G0 on 20200303 with smoke-only models; every member attests about the R3-02 non-spec outputs; the\n"
    "  user decides on pushing the team-runner and NOTICE fixes and on the `ai-workshop` allocation (R3-07, R3-41);\n"
    "  check IA items for the 7 uncaptioned dates (R3-18)")
rep("- Write PREREG_H1.md:", "- Write PREREG_H1.md **[R3-04: this is PREREG-D, after PREREG-R]**:")
after("quotes for the R2-24 extras; ADDENDUM supersession table (R2-04)",
      "\n- **Added (r3), outcome-free:** source-date training and its audit (R3-01); D-VAL-C labels (R3-08); cutoff probe\n"
      "  (R3-12); τ_used per R3-13 with the GDELT re-pull and answer windows per R3-14; MP4-clock completeness (R3-15);\n"
      "  frozen decoding options (R3-17); D-DOM with covariance shares, D-OPEN, Δdot, run-up, political share and L (R3-23,\n"
      "  R3-25..R3-30), on 2016-2022 only until PREREG-R; R3-19 and R3-20 simulations; then PREREG-D")
after("**(r2: with R2-09, R2-25, R2-31 and the R2-32 reference set by 2026-10-21)**",
      " **(r3: with R3-05, R3-09, R3-16, R3-35..R3-40 and the R3-38 pull helper)**")

# ---- F.1-F.6 markers
after("**A-02 Wall-clock anchor protocol (revised r1).**",
      " **(r3) τ_used formula R3-13; answer windows R3-14; label criterion R3-19.**")
after("**A-03 H1-primary horizon, sign and test (revised r1).**",
      " **(r3) Ratified in PREREG-R (R3-04); critical value R3-20.**")
after("**A-05 Captions, re-timing and clock source per meeting (revised r1).**",
      " **(r3) MP4-clock completeness and last chair answer R3-15.**")
after("**A-06 Event clocks, windows and BENCH-R scope (revised r1).**", " **(r3) Decisive statistic in bp (R3-31).**")
after("**A-09 Residualisation (revised r1).**",
      " **(r3) Trading residualiser from 2022-03-16 (R3-22); Warsh a and σ (R3-40).**")
after("**A-11 Confirmation sample size and G3 operating characteristics (revised r1).**",
      " **(r3) Size rule R3-20; label operating characteristics R3-19.**")
after("**A-12 Pre-registration record (revised r1: sequencing).**",
      " **(r3) Two timestamps, PREREG-R and PREREG-D (R3-04).**")
after("**A-17 Live delay and paper-trade protocol (revised r1).**", " **(r3) R3-35..R3-38.**")
after("**A-42 Live decision object, end detection and position map (new r1; implementation detail).**",
      " **(r3) Position scale and Warsh rule R3-40; end-detector replay R3-39.**")
after("not a delay sample and not a p90 kill.",
      " **[R3-36: only a watchdog-stamped failure before t_fill voids a counted event]**")
after("| (r2) D-VAL-W kappa < 0.6 (R2-09) | D-VAL-W \"uninformative\" |",
      "\n\n**(r3)** The rows from R2-13(iv), R2-17(4), R2-19(2), R2-29 and A-02(7) fire by the R3-19 estimate-difference"
      " rule; the lexicon row reads as in R3-06; the variance-ratio rows read as in R3-23; new rows are listed in"
      " R3-19(4); a label with LR < 1.5 is demoted to a note (R3-19(3)).")
rep("scheduler-enforced lanes, R2-36).*", "scheduler-enforced lanes, R2-36; r3: one `fp-gpu` singleton job name, R3-41).*")
rep("| GPU guard (r2) | `squeue ... -o %b` pre-submit count | two singleton job lanes; `tres-alloc` audit | R2-36 |",
    "| GPU guard (r2, r3) | `squeue ... -o %b` pre-submit count | ~~two singleton job lanes~~ one `fp-gpu` job name with"
    " `--dependency=singleton`, ≤ 2 GPUs per job, no GPU arrays, `GPU_LAYOUT=job`, no `--allow-concurrent`;"
    " `tres-alloc` audit | R2-36, R3-41 |\n"
    "| Label-date rule (r3) | dataset `year` (`labels.py` l.132) | `source_date` from the pinned `label_dates.parquet` |"
    " R3-01 |\n"
    "| Clock anchor (r3) | single affine anchor per meeting (`clock.py`) | per-τ_k bound table by source and station |"
    " R3-13 |\n"
    "| Smoke and fingerprint (r3) | `SMOKE_ID=20250917`, production keys, `h1_gap` printed; fingerprint without host,"
    " versions, flags, code hash | 20200303, smoke-only models, no score printouts; full fingerprint | R3-03 |\n"
    "| ASR decoding (r3) | default temperature fallback, unseeded, VAD by mode | temperature [0.0], explicit VAD,"
    " seeded, frozen batch sizes | R3-17 |")
after("**A-49 Reproducibility of frozen tables (new r1; implementation detail, all in the A-12 manifest).**",
      " **(r3) H2/H3 reference platform R3-42; decoding R3-17; fingerprint R3-03(3).**")
rep("- *Outgoing chair.*", "- *Outgoing chair (r3: second cut from 2025-06-25, R3-27).*")
rep("- *Concurrent news (r2: second flag class in R2-30(5)).*",
    "- *Concurrent news (r2: second flag class in R2-30(5); r3: pre-treatment flags only, R3-29).*")
after("**A-14 H1-chrono (revised r1; role changed by R2-01).**", " **(r3) Counts on source dates (R3-01).**")
rep("(r1)** H1-exec-live: entry at τ_used + 120 s (A-42(5)).",
    "(r1)** H1-exec-live: entry at τ_used + 120 s (A-42(5)). **[R3-39: end-detector replay row added; this row stays"
    " as a second bracket]**")
rep("If var(S) exceeds 50% of var(s), PREREG says",
    "~~If var(S) exceeds 50% of var(s)~~ **[R3-23]** If share_S = −cov(s, S)/var(s) exceeds 0.5, PREREG says")
after("**A-39 Placebos and the lexicon row (new r1; clarifying for the locked lexicon row).**",
      " **(r3) Item (1) is replaced by R3-06: the frozen row is not estimable (MIN_HD); LEX-RAW is Tier 3; the"
      " weak-measure reading and its label are withdrawn.**")
after("**A-41 H1-P: prospective ~~confirmation~~ replication (new r1; renamed and specified by R2-25).**",
      " **(r3) Eligibility R3-05(2); clock R3-16.**")
after("**A-43 Counted paper trades and the sequential rule (new r1; replaces A-25 and the last sentence of A-35).**",
      " **(r3) Statistic gross (R3-34); commit at t_fill (R3-36); G5 terminal (R3-35); D-VAL-W verdicts act forward"
      " (R3-09); licence flag extended (R3-07).**")
rep("r2: unit, sample, gold label, metric and rule replaced by R2-09).**",
    "r2: unit, sample, gold label, metric and rule replaced by R2-09; r3: blindness and forward-only verdicts, R3-09).**")
after("The locked {2, 4}-tick stress and the H1 statistic are unchanged; no net Sharpe on H1.",
      " **[R3-33: spreads are outright-book upper bounds; ZF quote pending]**")
after("- **(r2)** WhisperX 3.8.6 English align default name, re-checked in the pinned source (R2-18(4)).",
      "\n- **(r3)** `ai-workshop` allocation terms vs A-48(4) (R3-41); whether singleton serialises array tasks (CPU"
      " dummy, R3-41(2)).\n- **(r3)** FOMC-RoBERTa weight history for the H1-RoBERTa row (R3-11).\n"
      "- **(r3)** Whether a sponsor-judged use of NC-derived scores is commercial under CC BY-NC 4.0 (R3-07).")

# ---- F.7 markers
after("dated, before any chrono-bert score on presser text exists).**",
      " **(r3) Precondition reworded by R3-02(2); ratification belongs to PREREG-R (R3-04); label dates R3-01; one code"
      " base R3-03.**")
rep("5. D1's \"additional clean sample, reported alongside\" is exactly",
    "5. **[R3-21: the Tier 2 slot is H1-clean (2016-2022); H1-pooled moves to Tier 3]** D1's \"additional clean"
    " sample, reported alongside\" is exactly")
rep("6. A-09/A-42: a, b and σ come from D1 scores of prior meetings from 2020-01-01",
    "6. **[R3-22: from 2022-03-16; Warsh rule R3-40]** A-09/A-42: a, b and σ come from D1 scores of prior meetings from"
    " ~~2020-01-01~~")
after("**R2-02 Script order while G3 waits (implementation detail added to A-12 and A-40).**",
      " **(r3) Scope: the named event list of R3-05(1).**")
after("**R2-03 Data on disk, sealed outputs and outcome access (correction plus implementation detail).**",
      " **(r3) R3-02 adds the non-spec chrono outputs; R3-05 scopes items 2 and 5; R3-24 extends item 7.**")
rep("τ_used = τ_media + sched + max(hi_IA, hi_GDELT) + M with",
    "**[formula replaced by R3-13]** τ_used = τ_media + sched + max(hi_IA, hi_GDELT) + M with")
after("**R2-05 Training platform and determinism of every walk-forward checkpoint (implementation detail).**",
      " **(r3) Label dates R3-01; fingerprint R3-03(3); `reference_compile=False` R3-12; quarantined integration"
      " checkpoints R3-02.**")
after("**R2-09 D-VAL-W redesign (clarifying amendment to A-47, filed before any labelling).**",
      " **(r3) Blindness and forward-only verdicts R3-09; Tier 0 checkpoints R3-08.**")
after("var(S_repeat) > 50% of var(S). The locked statistic is unchanged.", " **[R3-23: covariance-share rule]**")
rep("(iii) Each base's sentence", "(iii) **[replaced by R3-10]** Each base's sentence")
rep("(iv) Label \"not robust to scorer vintage\"", "(iv) **[criterion replaced by R3-19]** Label \"not robust to scorer vintage\"")
rep("ratify the single 2022 base for 2023-2026 before any market join;",
    "ratify the single 2022 base for 2023-2026 ~~before any market join~~ **[R3-04: in PREREG-R only]**;")
rep("sealed or deleted once the text-free per-cue",
    "sealed ~~or deleted~~ **[R3-18: never deleted before PREREG-D]** once the text-free per-cue")
rep("(d) The drift gate is replaced by τ_used",
    "(d) **[formula replaced by R3-13; answer-level windows R3-14]** The drift gate is replaced by τ_used")
rep("(1) One station per", "(1) **[\"CNBC first\" and the step term withdrawn by R3-13]** One station per")
rep("(2) Before the freeze, validate the IA segment convention",
    "(2) **[superseded by R3-13(1),(4)]** Before the freeze, validate the IA segment convention")
rep("\"not robust to clock\" attaches if either disagrees", "\"not robust to clock\" attaches if either disagrees **[criterion R3-19]**")
rep("(1) Completeness, independent of the aligner:",
    "(1) **[1 s rule and last-answer definition amended by R3-15]** Completeness, independent of the aligner:")
rep("(2) Start + 60 min is a", "(2) **[label criterion R3-19]** Start + 60 min is a")
rep("(5) **BENCH-R-P** (Tier P, registered now):",
    "(5) **BENCH-R-P** (Tier P, registered now; **r3:** exit R3-32, statistic R3-31, eligibility R3-05, data R3-38):")
after("**R2-21 Samples across the 2020 break (clarifying, before results).**",
      " **(r3) H1-clean in Tier 2 and H1-pooled in Tier 3 (R3-21); ZLB rows (R3-22); decision p R3-20(2).**")
after("**R2-25 H1-P: statistic, sidedness and wording (clarifying amendment to A-41/A-43, filed before 2026-10-28).**",
      " **(r3) Eligibility R3-05(2); clock R3-16.**")
rep("H1-pooled, H1-A,", "~~H1-pooled~~ H1-clean (R3-21), H1-A,")
after("**R2-28 Fixed-design operating characteristics (implementation detail in A-11).**",
      " **(r3) Acted on by R3-20; label operating characteristics R3-19(2).**")
rep("when the covariance term and the mean disagree in sign or significance",
    "when the covariance term and the mean disagree in sign or significance **[criterion R3-19(1)]**")
rep("1. G5 as locked: per-answer p90 of delay_upper (i) ≤ 60 s. D_frozen = max(p90 of (i) on 2026-10-28, 30 s).",
    "1. G5 as locked: per-answer p90 of delay_upper (i) ≤ 60 s. D_frozen = max(p90 of (i) on 2026-10-28, 30 s)."
    " **[R3-35]**")
rep("2. Counted fill time t_fill", "2. **[fill instant and settlement test R3-37]** Counted fill time t_fill")
rep("A G5 fail stops counting until a dated\n   pipeline change plus one fresh measurement presser; never a retroactive"
    " re-measurement.",
    "~~A G5 fail stops counting until a dated\n   pipeline change plus one fresh measurement presser; never a retroactive"
    " re-measurement.~~ **(r3, R3-35)** A G5 fail kills\n   live for the project, as locked.")
rep("5. Warsh settlement: the 15:01 rule is deleted.",
    "5. Warsh settlement: the 15:01 rule is deleted. **[R3-37(2): the window test applies to t_fill]**")
rep("processing; H1-P uses it", "processing; ~~H1-P uses it~~ **[R3-16: H1-P uses arrival + NTP uncertainty, no processing term]**")
rep("A-43 statistic = studentised mean of per-event net P&L in ZT",
    "**[R3-34 replaces the next sentence: the A-43 statistic is gross mid to mid; net P&L is a hurdle line]** A-43"
    " statistic = studentised mean of per-event net P&L in ZT")
after("**R2-36 GPU lanes and the batch runbook (implementation detail; replaces the A-48(1) guard).**",
      " **(r3) Item (1) is replaced by R3-41 (one `fp-gpu` singleton job name, ≤ 2 GPUs per job, no GPU arrays).**")

# ---- F.8 before section G
rep("\n---\n\n## G. Test register", "\n" + f8.rstrip() + "\n\n---\n\n## G. Test register")

# ---- section G table
g0 = t.index("## G. Test register")
gs = t[g0:]
after_note = ("any pooled test, and every other r2 change below still applies.")
assert gs.count(after_note) == 1
rows = {
    "| 0 |": "| 0 | alpha 0.05, sidedness as ratified in PREREG-R (A-03, R3-04); the only GO/NO-GO; one pre-named scorer with weight hashes (R2-01, R3-03); critical value = max(WRE, fixed-design ICC 0.05 quantile) (R3-20(1)) | H1-primary on the scorer of record (default: D1 walk-forward chrono-bert, R2-01(1)-(2), source-date labels R3-01) |",
    "| 1 |": "| 1 | Holm, m = 3; \"reproduction on a second instrument (ZT vs USMPD UST2Y), non-blind\"; no \"test\" or \"confirm\" wording (R2-19); decisive statistic gross, in bp (R3-31) | BENCH-R ZT with the R2-19 exit: 2011-19 regime mean (one-sided continuation); 2020-26 regime mean (two-sided); break (two-sided) |",
    "| 2 |": "| 2 | Holm, m = 9 (unchanged); confirmation-sample tests use the R3-20(1) critical value, multi-year tests the year-cluster bootstrap (R3-20(2)) | **H1-clean** (2016-2022, R2-21 specification; R3-21; replaces H1-pooled); H1-A (A-37); H1-PX (A-38); H1-run (A-03, legs per R3-14); H1-RoBERTa (official weights passing R2-06 and R3-11 before PREREG-D, else p = 1); BENCH-R-ES break (A-19); H2 arousal (A-31); H3 upper-face composite (A-32); H4 Clark-West (A-26, R2-14) |",
    "| P |": "| P | own alpha 0.05 each, studentised O'Brien-Fleming looks at 8/16/24 events with the R2-25 statistic and boundaries; eligibility R3-05(2) | H1-P (prospective replication, R2-25; clock R3-16); BENCH-R-P (R2-19; exit R3-32; statistic R3-31); the counted paper-trade sequence (A-43, gross statistic R3-34, committed at t_fill R3-36) is reported on the same looks and supports no claim beyond A-43 |",
    "| D |": "| D | diagnostics; fixed labels only (A-46, R3-19) | D-VAL with ρ_within and statement-level ρ (R2-07, R2-08), D-VAL-W (R2-09, R3-09), D-VAL-C (R3-08), presser-domain F1 (R2-10), D-ASR, D-DOM with the S_repeat/S_new split and covariance shares (R2-11, R3-23) plus Δdot, run-up, political share and L (R3-26..R3-30), D-VINTAGE (R2-13, R3-10), D-OPEN (R3-25), chrono cutoff probe (R3-12) |",
}
lines = gs.split("\n")
for i, ln in enumerate(lines):
    for k, v in rows.items():
        if ln.startswith(k):
            lines[i] = v
    if ln.startswith("| 3 |"):
        assert ln.endswith("(R2-17) |")
        lines[i] = ln[:-2] + ("; plus (r3): H1-pooled 2016-2026 (R3-21(2)); H1 2016-2022 locked spec (R3-21(3)); ZLB-regime"
                               " and volatility-scaled rows (R3-22); LEX-RAW (R3-06); D1 literal answer-weighted if not ratified"
                               " (R3-03(1)); CNBC-only τ_used and the 2024-10-09 / 2025-04-01 splits (R3-13); H1-answer without"
                               " fallback windows (R3-14); matched-delay H1-P (R3-16); H1-O and H1-A-O (R3-25); H1-SEP (R3-26);"
                               " outgoing-chair cut from 2025-06-25 and s × political share (R3-27); H1-RUNUP (R3-28); H1-L and"
                               " y/√L (R3-30); BENCH-R-P with the live end-event exit (R3-32); H1-exec-live by end-detector replay"
                               " beside the fixed +120 s bracket (R3-39); sign-only and A-only H1-P companions (R3-40) |")
gs = "\n".join(lines)
gs = gs.replace(after_note, after_note +
                "\n\n**(r3)** H1-clean replaces H1-pooled in Tier 2 (R3-21); Tier 0 and the confirmation-sample Tier 2 tests"
                " use the R3-20(1) critical value and multi-year Tier 2 tests the year-cluster bootstrap (R3-20(2)); Tier P"
                " eligibility follows R3-05(2); every label follows R3-19. If option v1 is taken, these r3 rules still apply.",
                1)
t = t[:g0] + gs

# ---- J at end
t = t.rstrip() + "\n" + jj.rstrip() + "\n"

for bad in ["<assistant>", "<assistant>.ai"]:
    assert bad not in t, bad
(P / "merged_plan_v3.md").write_text(t, encoding="utf-8")
print(len(t), t.count("\n"))
