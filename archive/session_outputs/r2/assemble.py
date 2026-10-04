import io, re, sys
P = '<solo-repo>/research/fed_presser_plan/'
R = '<scratch>/r2/'
t = open(P + 'merged_plan_v1.md', encoding='utf-8').read()
f7 = open(R + 'f7_renum.md', encoding='utf-8').read()
gtab = open(R + 'g_table.md', encoding='utf-8').read()
seci = open(R + 'sec_i.md', encoding='utf-8').read()

def rep(old, new):
    global t
    n = t.count(old)
    if n != 1:
        sys.exit('count %d for: %r' % (n, old[:90]))
    t = t.replace(old, new)

def after(anchor, add):
    rep(anchor, anchor + add)

rep('(hardened), merged v1', '(hardened), merged v2')
rep('revised the same day after review round 1 (label `r1_patch`).',
    'revised the same day after review round 1 (label `r1_patch`) and review round 2 (label `r2_patch`).')
after('round-1 change list (section H).',
      ' Round 2 added section F.7 (R2-00..R2-36), revised the register (section G) and appended the round-2 change'
      ' list (section I); in-place markers **[R2-nn]** point to F.7.')
rep('No amendment here was written after any H1-primary, H1-answer or BENCH-R number on Databento data existed.',
    '~~No amendment here was written after any H1-primary, H1-answer or BENCH-R number on Databento data existed.~~\n'
    '**[R2-00] Correction:** that sentence holds for v0 and r1 only. Databento ohlcv-1m, ohlcv-1s and bbo-1s for 75\n'
    'presser days were on disk from 16:42-17:06 ET, and a parallel pipeline wrote BENCH-R, lexicon-control and lexicon\n'
    'H1-answer results at 17:48-17:57 ET, after v1 (17:40 ET) and before the round-2 amendments. No stance-model H1\n'
    'score or H1-primary result exists. The authors of round 2 did not open those results (hash inventory:\n'
    '`plan/checks_r2_merge/exposure_inventory_20261003.txt`).')
after('(6) HiPerGator use is limited to the research arm and to at most 2 GPUs per user at any time (A-48).',
      '\n\n**Round-2 headline for the reader.** (1) Two pre-result records name different scorers for H1-primary: the'
      ' team\'s dated deviation D1 (walk-forward chrono-bert, argmax share; 17:13 EDT) and v1\'s A-40 (FOMC-RoBERTa or'
      ' postpone), which overlooked D1. R2-01 makes D1 the default scorer of record, withdraws A-40\'s postponement and'
      ' deadline under that option, and asks the team to ratify one score function before any chrono score on presser'
      ' text exists. (2) Paid 1m, 1s and bbo-1s data for the 2016+ presser days are already on disk, and a parallel'
      ' pipeline (`presser_bt`, under its own ADDENDUM) has already computed BENCH-R, the lexicon control and lexicon'
      ' H1-answer on them, reading the 2023-2026 H1 outcome windows; nothing stance-based exists. R2-00, R2-03 and'
      ' R2-04 record this, seal those outputs, ask the user to confirm the purchase and make one spec and one code'
      ' path govern. (3) BENCH-R\'s exit returns to the locked presser-end; its Tier 1 is renamed a reproduction and a'
      ' blind prospective BENCH-R-P is added (R2-19). (4) The r1 anchor drop criteria and clock-source tests are'
      ' replaced by the locked half-width rule and tests that can fail (R2-16..R2-18); the realised confirmation n is'
      ' recomputed. (5) Live fills, H1-P boundaries, D-VAL and D-VAL-W are made well defined (R2-07, R2-09, R2-25,'
      ' R2-31). (6) Every checkpoint that feeds H1, paper trades or fedspeak_v2 is trained once on the local 5090;'
      ' HiPerGator replicates only, inside the 2-GPU rule enforced by the scheduler (R2-05, R2-36).')

# family table pointers
rep('A-46 (interpretation labels; r1) |',
    'A-46 (interpretation labels; r1); **r2:** R2-01 (scorer of record; ratify), R2-03 (exposure), R2-11, R2-13,'
    ' R2-16..R2-18 (clock), R2-20, R2-25..R2-28 |')
rep('A-18 (1s extension; r1) |', 'A-18 (1s extension; r1); **r2:** R2-01, R2-34 |')
rep('A-19 (hurdle table; BENCH-R-ES extension) |',
    'A-19 (hurdle table; BENCH-R-ES extension); **r2:** R2-19 (exit = presser-end, ratify; Tier 1 renamed;'
    ' BENCH-R-P), R2-20 (R_stmt print), R2-22 (legacy feed), R2-24 (2011-19 era kept) |')
rep('A-10, A-15 (questions are out of the classifier\'s domain) |',
    'A-10, A-15 (questions are out of the classifier\'s domain); **r2:** R2-12 |')
rep('A-26 (training window, Clark-West), A-31 (valence excluded) |',
    'A-26 (training window, Clark-West), A-31 (valence excluded); **r2:** R2-14 |')
rep('**D-VAL-W** (A-47). Every test has one tier in the register (section G).',
    '**D-VAL-W** (A-47). Added in round 2: **H1-pooled** (replaces the H1-chrono decision row) and **H1-RoBERTa**'
    ' (replaces H1-replica in Tier 2) (R2-01), **BENCH-R-P** (R2-19), **H1-1base** and **D-VINTAGE** (R2-13),'
    ' **BENCH-R-d10** (R2-20), **D-STMT-PATH** and the R2-30 rows. Every test has one tier in the register'
    ' (section G).')
rep('**[A-28]** pin revision sha; access is gated (manual) |',
    '**[A-28]** pin revision sha; access is gated (manual). **[R2-01]** Under team deviation D1 (default) the scorer'
    ' of record is walk-forward chrono-bert; FOMC-RoBERTa is the Tier 2 H1-RoBERTa row if verified before the freeze'
    ' (R2-06), else Tier 3 robustness |')
rep('**[A-13]** bbo-1s (top of book) is enough to measure 1-lot spreads.',
    '**[A-13]** bbo-1s (top of book) is enough to measure 1-lot spreads. **[R2-00, R2-03]** ohlcv-1m, ohlcv-1s and\n'
    'bbo-1s for the 75 2016+ presser days (13:30-16:30 ET) are already on disk; the purchase awaits the user\'s direct\n'
    'confirmation, and every read follows R2-03.')
rep('A-40: run once, from the frozen hash, only with verified official weights]**',
    'A-40: run once, from the frozen hash, ~~only with verified official weights~~ **(r2)** with the one ratified'
    ' scorer of record (R2-01); R2-26 table after a NO-GO; R2-27 GO wording; R2-03 exposure labels]**')
rep('counted only after a G3 GO and never on 2026-10-28]**',
    'counted only after a G3 GO and never on 2026-10-28; (r2) R2-31 fill rule and D_frozen, R2-32 references]**')
rep('2011–2015 ohlcv-1m about $0.04.',
    '2011–2015 ohlcv-1m about $0.04. **[R2-03, R2-24]** The 2016+ ohlcv-1m, ohlcv-1s and bbo-1s windows are already on\n'
    'disk (the user confirms or denies that purchase); extras outside the cached window get a printed quote first.')
after('only post-freeze events (A-41) are fully blind, and they are all Warsh events.',
      '\n\nAdded in round 2:\n\n'
      '10. **Two scorer records and a parallel execution spec.** Team deviation D1 and v1\'s A-40 name different\n'
      '    scorers, and bt/ADDENDUM.md fixes different execution choices; whichever runs first could define "the\n'
      '    pre-registered result" (R2-01, R2-04).\n'
      '11. **Outcome windows already read.** A parallel pipeline read the 2023-2026 τ→16:00 windows for the lexicon\n'
      '    control and computed BENCH-R 2016-26 before any freeze. Blindness of G3 now rests on sealed outputs and\n'
      '    attestation; H1-P and BENCH-R-P are the only fully blind evidence (R2-00, R2-03, R2-19, R2-25).')
# section E
rep('- **Added:** user requests FOMC-RoBERTa access (A-28); apply the A-36 config changes',
    '- **Added:** user requests FOMC-RoBERTa access (A-28); apply the A-36 config changes\n'
    '- **Added (r2):** team chooses option D1 or option v1 and ratifies the score function in writing (R2-01) and the\n'
    '  BENCH-R exit (R2-19); every member attests about the sealed `presser_bt` outputs (R2-03); the user confirms or\n'
    '  denies the 1s/bbo-1s purchase (R2-03); moratorium on post-14:20 reads of 2020-2026 data until PREREG (R2-03);\n'
    '  replace the squeue guard by two singleton GPU lanes (R2-36)')
rep('- **Added (r1):** if verified official FOMC-RoBERTa weights are not in hand by 2026-10-14, H1-primary is postponed\n'
    '  (A-40); the freeze and the 1m download then slip together, never a partial freeze',
    '- ~~**Added (r1):** if verified official FOMC-RoBERTa weights are not in hand by 2026-10-14, H1-primary is postponed\n'
    '  (A-40); the freeze and the 1m download then slip together, never a partial freeze~~ **(r2, R2-01)** that rule holds\n'
    '  only under option v1; under option D1 the accuracy gate decides postponement\n'
    '- **Added (r2), outcome-free, local 5090 under the R2-36 runbook:** 45 walk-forward fine-tunes with deterministic\n'
    '  flags and their score table hashed (R2-05); accuracy gate and presser-domain F1 (R2-01(4), R2-10); D-VINTAGE\n'
    '  (R2-13); D-DOM with S_repeat/S_new (R2-11); trailing-window anchors, one station per meeting, IA vs GDELT\n'
    '  validation and recomputed realised n (R2-16, R2-17); aligner-independent MP4 completeness (R2-18); fixed-design\n'
    '  operating characteristics and PPV (R2-27, R2-28); D-VAL with ρ_within, statement ρ and 2011-2015 models (R2-07,\n'
    '  R2-08); degraded-day QA plan (R2-23); quotes for the R2-24 extras; ADDENDUM supersession table (R2-04)')
rep('- Download 1m windows if quote OK',
    '- ~~Download 1m windows if quote OK~~ **(r2, R2-03, R2-24)** the 2016+ windows are already on disk; only the\n'
    '  R2-24 extras are downloaded, after a printed quote and the user\'s approval')
rep('Powell; run H1-chrono as registered **(r1: the H1-primary 2023-2026 script runs first, once, from the frozen hash;\n'
    '  then the Tier 1-3 rows of section G)**',
    'Powell; run H1-chrono as registered **(r1: the H1-primary 2023-2026 script runs first, once, from the frozen hash;\n'
    '  then the Tier 1-3 rows of section G)** **(r2, R2-01)** under option D1, H1-primary runs on the D1 scorer and\n'
    '  H1-pooled replaces H1-chrono; the contaminated FOMC-RoBERTa 2016-2022 run happens only if weights arrive')
rep('2026-10-28 (A-41, A-47)',
    '2026-10-28 (A-41, A-47) **(r2: with R2-09, R2-25, R2-31 and the R2-32 reference set by 2026-10-21)**')

# in-place markers in section F
rep('**A-10 Score function (retyped r1: clarifying amendment, ratified with A-03).**',
    '**A-10 Score function (retyped r1: clarifying amendment, ratified with A-03).** **(r2) Under option D1 of R2-01\n'
    'the score type is D1\'s argmax share over the qualifying sentences defined here, P(h) − P(d) becomes a Tier 3\n'
    'variant, gate (a) below is replaced by R2-06, and the R2-11 construct note is part of the ratification.**')
rep('3. *Bins (r1).*', '3. *Bins (r1; superseded by R2-16).*')
rep('5. *Drop rule (r1: the locked text, read literally).*',
    '5. *Drop rule (r1; superseded by R2-16, which keeps only the locked half-width criterion).*')
rep('7. *ε calibration (r1).*', '7. *ε calibration (r1; amended by R2-17).*')
rep('revision 569a623, the WhisperX English default)',
    'revision 569a623; ~~the WhisperX English default~~ **(r2, R2-18)** an explicit pin, not the WhisperX English\n'
    '  default)')
rep('- *Clock-source rule, frozen per meeting before any market join (r1).*',
    '- *Clock-source rule, frozen per meeting before any market join (r1; its tests are replaced by R2-18).*')
rep('- *Exit (r1).*', '- *Exit (r1; superseded by R2-19, which restores the locked presser-end).*')
rep('after the 2020 break only (FOMC-RoBERTa: 2023+)',
    'after the 2020 break only (FOMC-RoBERTa: 2023+; **r2:** D1 scorer from 2020-01-01, R2-01(6); R_stmt per R2-20)')
rep('**A-11 Confirmation sample size and G3 operating characteristics (revised r1).**',
    '**A-11 Confirmation sample size and G3 operating characteristics (revised r1).** **(r2) The realised n is\n'
    'recomputed under R2-16 (the r1 criteria kept 16 of 20); the simulation is fixed-design (R2-28); two-sided\n'
    'reference values are printed (R2-25(4)); PPV per R2-27.**')
rep('**A-12 Pre-registration record (revised r1: sequencing).**',
    '**A-12 Pre-registration record (revised r1: sequencing).** **(r2) Data were downloaded before any freeze\n'
    '(R2-00); R2-03(5) rewords "frozen before the 1m download" as "freezes the SHA-256 of the data on disk" and reads\n'
    '"bar" as any record of any schema; R2-02 adds the waiting rule.**')
rep('**A-14 H1-chrono (revised r1).**',
    '**A-14 H1-chrono (revised r1; role changed by R2-01).** **(r2) Under option D1 this specification (training\n'
    'settings, checkpoints, standardisation, accuracy gate) becomes the scorer of record for H1-primary; the decision\n'
    'row becomes H1-pooled with the R2-21 specification; the gate becomes a pre-G3 validity gate (R2-01(4)); training\n'
    'follows R2-05; the score type is D1\'s argmax share (R2-01(2)); checkpoints 2010-2014 are added (R2-08).**')
rep('**A-15 D-VAL (diagnostic; revised r1).**',
    '**A-15 D-VAL (diagnostic; revised r1; r2: R2-07 within-meeting and statement ρ, R2-08 walk-forward 2011-2015).**')
rep('4. *Two latencies (r1).*', '4. *Two latencies (r1; amended by R2-31).*')
rep('deterministically the next day from as-of quotes at 13:49:59 and 14:19:59',
    'deterministically the next day from ~~as-of quotes at 13:49:59 and 14:19:59~~ **(r2, R2-20)** the 13:49 and\n'
    '   14:19 1m bar closes')
rep('6. *Fills (r1).*', '6. *Fills (r1; amended by R2-31 and R2-33).*')
rep('an operational check that needs no ASR.',
    'an operational check that needs no ASR **(r2, R2-20: a next-day deterministic replay that feeds BENCH-R-P)**.')
rep('**A-21 H1-answer-mid and bbo semantics (revised r1).**',
    '**A-21 H1-answer-mid and bbo semantics (revised r1; r2: R2-03(6), R2-22).**')
rep('tests on 2023-2026 with the Clark-West nested-model statistic.',
    'tests on 2023-2026 with the Clark-West nested-model statistic. **(r2, R2-14)** Training-period text features are walk-forward chrono scores.')
rep('H1-chrono walk-forward fine-tunes, voice/face features',
    '~~H1-chrono walk-forward fine-tunes~~ **(r2, R2-05)** replication only of the walk-forward fine-tunes (trained\n'
    '  locally), voice/face features')
rep('**A-29 Model cutoff registry (revised r1).**',
    '**A-29 Model cutoff registry (revised r1; r2: walk-forward-scored meetings count as uncontaminated, R2-01(6);\n'
    'tokenizer note, R2-15(1)).**')
rep('Official FOMC-RoBERTa weights verified by\n2026-10-14, else A-40(a).',
    '~~Official FOMC-RoBERTa weights verified by 2026-10-14, else A-40(a).~~ **(r2, R2-01)** That deadline applies only\n'
    'under option v1.')
rep('| A-48 |\n\nUnit tests (r1):',
    '| A-48 |\n'
    '| `train.stance_walkforward` registry, trainer (r2) | `/blue/...` registry; `--gpus 2`; no deterministic flags; attention backend unpinned | local registry; `torch.use_deterministic_algorithms(True)`, `CUBLAS_WORKSPACE_CONFIG`, `attn_implementation="sdpa"`, float32; 2010-2014 keys added | R2-05, R2-08 |\n'
    '| text stage score (r2) | argmax share over all sentences (D1 literal) | as ratified under R2-01(2) | R2-01 |\n'
    '| GPU guard (r2) | `squeue ... -o %b` pre-submit count | two singleton job lanes; `tres-alloc` audit | R2-36 |\n'
    '\nUnit tests (r1):')
rep('4. *Warsh timing.*', '4. *Warsh timing (settlement rule replaced by R2-31(5)).*')
rep('| D-VAL-W fails for Warsh (A-47) | Warsh events "measurement weak" (measurement-only, A-43) |',
    '| D-VAL-W fails for Warsh (A-47) | Warsh events "measurement weak" (measurement-only, A-43) |\n'
    '| (r2) Presser-domain macro-F1 < 0.45 (R2-10) | "measurement weak (presser domain)" |\n'
    '| (r2) ρ_within lower bound < 0.1 (R2-07) | "Q&A term not validated" |\n'
    '| (r2) var(S_repeat) > 50% of var(S) (R2-11) | "statement term is repeated boilerplate" |\n'
    '| (r2) H1-1base and primary disagree (R2-13) | "not robust to scorer vintage" |\n'
    '| (r2) H1-pooled sub-period slopes of opposite sign (R2-21) | "regime-heterogeneous" |\n'
    '| (r2) BENCH-R presser-end and start + 60 exits disagree (R2-19) | "break confounded with hold horizon" |\n'
    '| (r2) Covariance term and mean disagree (R2-29) | "drift times exposure, not timing" |\n'
    '| (r2) Outcome windows read before the freeze, no viewing attested / viewing attested (R2-03) | "outcome windows read by a parallel script before the freeze" / "non-blind (outcome vector viewed)" |\n'
    '| (r2) fedspeak_v2 validation opened before PREREG (R2-35) | "exposed via fedspeak_v2 validation" |\n'
    '| (r2) FOMC-RoBERTa agreement in [0.90, 0.98) (R2-06) | "published labels not reproduced exactly" |\n'
    '| (r2) D-STMT-PATH condition (R2-30(2)) | "statement-text drift; Q&A not required" |\n'
    '| (r2) No ε calibration when G3 runs (R2-17) | clock labelled "margin uncalibrated" |\n'
    '| (r2) D-VAL-W kappa < 0.6 (R2-09) | D-VAL-W "uninformative" |')
rep('1. *2-GPU rule per user (the user\'s instruction: at most 2 GPUs per session).*',
    '1. *2-GPU rule per user (the user\'s instruction: at most 2 GPUs per session; r2: the guard below is replaced by\n'
    '   scheduler-enforced lanes, R2-36).*')
rep('- *Concurrent news.*', '- *Concurrent news (r2: second flag class in R2-30(5)).*')
rep('**A-19 BENCH-R cost hurdle and BENCH-R-ES (r1: aligned with A-06).**',
    '**A-19 BENCH-R cost hurdle and BENCH-R-ES (r1: aligned with A-06; r2: hurdle table on both R2-19 exits).**')
rep('- **D-DOM (diagnostic, text-only):**',
    '- **D-DOM (diagnostic, text-only; r2: plus the R2-11 S_repeat/S_new split and the R2-28 year share):**')
rep('Define R_pc = `ZT.v.0` log return from the 14:20 open to the H1 entry open (no gap with',
    'Define ~~R_pc = `ZT.v.0` log return from the 14:20 open to the H1 entry open~~ **(r2, R2-20)** R_pc = `ZT.v.0` log\n'
    'return from the 14:19 bar close to the close of the bar before the H1 entry bar (no gap with')
rep('**A-40 Model-access contingency and weight verification (new r1; filed before any market join).**',
    '**A-40 Model-access contingency and weight verification (new r1; filed before any market join).** **(r2) Under\n'
    'option D1 of R2-01, items (a), (c), (d) and (e) as gates and the 2026-10-14 deadline are withdrawn; (b), (f), (g)\n'
    'and (h) stay; the identity rule is R2-06; H1-replica moves to Tier 3. Under option v1 this amendment stands with\n'
    'R2-02 and R2-06.**')
rep('**A-41 H1-P: prospective confirmation (new r1).**',
    '**A-41 H1-P: prospective ~~confirmation~~ replication (new r1; renamed and specified by R2-25).**')
rep('after a GO it is the confirmation.', '~~after a GO it is the confirmation~~ **(r2)** after a GO it is the prospective\nreplication (R2-25(5)).')
rep('logged with a frozen 60 s delay.', 'logged with a frozen 60 s delay **(r2: D_frozen := 60 s under the R2-31 rule)**.')
rep('max(p90 of delay_upper, 30 s).', 'max(p90 of delay_upper, 30 s) **(r2: R2-31 fill rule, R2-33 statistic)**.')
rep('**A-47 D-VAL-W: Warsh-era text validity (new r1; separately pre-registered diagnostic, filed before 2026-10-28).**',
    '**A-47 D-VAL-W: Warsh-era text validity (new r1; separately pre-registered diagnostic, filed before 2026-10-28;\n'
    'r2: unit, sample, gold label, metric and rule replaced by R2-09).**')
rep('**A-13 Measured spreads (r1: as-of quote rule).**',
    '**A-13 Measured spreads (r1: as-of quote rule; r2: R2-34 quote timing, R2-33 one cost model, R2-03 order for\n2023-2026).**')
rep('- **(r1)** FOMC-RoBERTa commit history and weight hashes once access is granted (A-40(d)).',
    '- **(r1)** FOMC-RoBERTa commit history and weight hashes once access is granted (A-40(d)).\n'
    '- **(r2)** The user\'s confirmation of the 1s/bbo-1s purchase found on disk (R2-03(1)).\n'
    '- **(r2)** The team\'s option (D1 or v1) and score-function ratification (R2-01); attestations about the sealed\n'
    '  outputs (R2-03(4)).\n'
    '- **(r2)** The 2026-10-28 live reference set and L_ref values, registered by 2026-10-21 (R2-32); whether a\n'
    '  caption-capture tuner or IPTV feed exists (R2-17).\n'
    '- **(r2)** WhisperX 3.8.6 English align default name, re-checked in the pinned source (R2-18(4)).')

# insert F.7 before section G
rep('---\n\n## G. Test register', f7.rstrip() + '\n\n---\n\n## G. Test register')
# section G table: keep v1 table under a struck note, add r2 table
g0 = t.index('| Tier | Rule | Tests |')
g1 = t.index('| D | diagnostics; fixed labels only (A-46) | D-VAL, D-VAL-W, D-ASR, D-DOM |')
g1 = t.index('\n', g1)
t = t[:g0] + gtab.rstrip() + t[g1:]
t = t.rstrip() + '\n' + seci
assert 'laude' not in t, 'attribution word present'
open(P + 'merged_plan_v2.md', 'w', encoding='utf-8', newline='\n').write(t)
print('ok', len(t), t.count('\n'))
