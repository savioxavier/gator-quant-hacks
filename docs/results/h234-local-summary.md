# H2/H3/H4 local replication: results summary

> **Exploratory, post-G3 (post-NO-GO); cannot rescue G3; no trading claim.** G3 stays NO-GO. In the locked
> register H2, H3 and H4 stay at p = 1 (R2-26). This is the **local replication** of note 1, section 2. The
> **HiPerGator reference run** (`backtests/presser/backtest_h234/`, which governs) agrees: H2 p 0.439 (local 0.438), H3 killed by G4
> in both, H4 p 0.243 (local 0.244); the reference run has 269 answers where this run has 268.

Written 2026-10-04 (UTC). Pre-registration: `preregistration/presser_H2H3H4_EXPLORATORY.md` (sha256
`e030af98...dca6d0`), with notes 1-3 (`presser_H2H3H4_NOTE1.md`, `NOTE2.md`, `NOTE3.md`). This file holds no
price levels. It reports only ticks, log returns in bp and statistics.

## Headline

**None of the three primary tests is detected.**

| Test | Raw p | Holm p (m = 3) |
|---|---|---|
| H2 (voice arousal) | 0.438 (two-sided) | 0.876 |
| H3 (upper-face composite) | killed by G4, enters at p = 1 | 1.0 |
| H4 (combined vs text-only, Clark-West) | 0.244 (one-sided) | 0.733 |

The 2023-2026 answer-level trades lose money gross, at a mean of -0.09 ticks (H2) and -0.03 ticks (H4) per trade.
Costs dominate: each trade is held for one minute, and there are about 27 trades per meeting.

## 1. What ran

- **Command.** `bash backtests/run_all_backtests.sh h234` was run once with these settings:
  - `FEDPRESS_ROOT`: the local feature tree. All 64 Powell meetings were computed on one local GPU, as note 1,
    section 2 describes.
  - `H234_SI_ROOT`: the local 64 kbps re-encode tree.
  - `H234_OUT_DIR=backtests/presser/backtest_h234_local`.
  - The licensed market files, read from a local folder.
- **Run.** 2026-10-04, 01:18:57 to 01:19:35 UTC, exit 0. The output folder did not exist beforehand, and no code
  or environment fix was made. Under section 9 this is the first and only local result.
- **Code and environment.**
  - Stage code as of commit 1c8c9e1 (the note-3 fix). The stage files are unchanged at the current branch head.
  - Python 3.12.10, pandas 3.0.6, numpy 2.5.3, scipy 1.18.1, pyarrow 25.0.1.
  - Seed 20261003; 9,999 bootstrap draws.
- **Hash chain (section 9 order).** The pre-registration hash was checked. The manifests were then written in this
  order:
  - qa `d7f4f5a4...`;
  - features `16fd2ac3...`;
  - positions `22d7eab9...`;
  - the H4 fit `8a864d77...`, hashed before any 2023-2026 price was read.

  These hashes include the absolute output path (`qa/provenance.json`), so any other run location gets different
  hashes. Compare runs numerically.
- **Outputs.** All outputs are in `backtests/presser/backtest_h234_local/` (`qa/`, `features/`, `positions/`,
  `h4_fit/`, `results/`). The whole folder is git-ignored and is not committed. Its trade logs carry price levels,
  and its provenance records local paths.

## 2. Gates and kill switches (before any market join)

| Check | Outcome |
|---|---|
| Model revisions (ECAPA 0f99f2d0, audeering 6eba34a2, MediaPipe 64184e22, SFace 0ba9fbfa, emotiefflib 1.1.1) | all 5 match |
| EmotiEffLib labels | the 8 expected labels |
| Face gates vs frozen values, SFace 0.363 threshold, jaw flag | 0 mismatches |
| `causal_z` cross-check against the package | passes |
| WAV length check (section 3.7) | 62 of 62 pass |
| Caption check, \|ASR vs caption offset\| <= 2 s (section 3.7) | 26 of 62 baseline meetings pass (h2_ok = h3_ok = 26). All 36 exclusions fail this check; 7 of them have no caption-timed answers |
| Burn-in (first 4 valid meetings) | 2018-03-21, 2019-01-30, 2019-03-20, 2019-07-31 |
| Post-burn-in meetings | 22: 12 training (2019-10-30 .. 2022-05-04) and 10 test (2023-09-20, 2024-06-12, 2024-11-07, 2024-12-18, 2025-01-29, 2025-03-19, 2025-06-18, 2025-07-30, 2025-09-17, 2026-01-28) |
| **H3, G4 variance gate** | **KILLED.** The browInnerUp floor (0.005) binds in 22 of 22 post-burn-in meetings, at a raw scale of 0.0024-0.0046. BD and ES bind in 0 of 22 |
| H2, G4 variance gate | not killed: the arousal floor binds in 0 of 22 (dominance 0 of 22) |
| H2, source invariance (A-31) | **not checked.** 2019-06-19, one of the three re-encode meetings, fails the caption check (offset -2.79 s), so the ICC is not computed (note 3). The stage's label reads "source invariance not checked (missing re-runs: ['20190619'])". The re-run exists; the meeting is simply outside h2_ok |
| known_at QA | every voice chunk ends at or before E_k. The package known_at is recorded for comparison only. τ falls a median 20.0 s (voice) and 18.2 s (face) after it |

## 3. Primary results (2023-2026, Holm m = 3)

| Test | Status | n (answers / meetings) | Statistic | Raw p | Holm p | Wording |
|---|---|---|---|---|---|---|
| **H2**: arousal z, long ZT on +sign(z), +1 min, gross | run; "source invariance not checked" | 268 / 10 | mean -0.086 ticks, CR1 t -0.81; 90% block-bootstrap CI [-0.262, +0.068] | 0.4382 (wild-cluster, two-sided) | 0.8764 | not detected |
| **H3**: upper-face composite U | **killed by G4** (browInnerUp) | 272 / 10 | computed but not used: mean +0.011 ticks, wild-cluster p 0.951 | enters at 1 | 1.0 | not detected (killed) |
| **H4**: combined C vs text-only T, ZT, frozen 2018-2022 fit | run (see the component status below) | test 268 / 10; training 247 / 12 | Clark-West mean f 0.00830, CR1 SE 0.01149, **t 0.722** (df 9). **OOS R²**: C vs T -0.0043; C vs zero -0.0292; T vs zero -0.0248 | **0.2442** (one-sided); two-sided 0.4885; wild bootstrap 0.2576 one-sided, 0.5001 two-sided | 0.7327 | not detected |

**H4 component status (note 1, section 4).** H4 uses two components from the other tests:
- U, the H3 composite, which G4 killed (the browInnerUp floor binds in 22 of 22 post-burn-in meetings);
- z_A from H2, which carries "source invariance not checked".

The Holm family is unchanged: m = 3, and the killed test enters at p = 1. The stage's `family_holm.json` shows H4
with only the generic label; this paragraph is the required statement.

**H2 primary, further detail.**
- Leave-one-meeting-out range [-0.146, -0.028]; the most influential meeting is 2025-09-17.
- Meeting-averaged mean -0.116 ticks (sign-flip p 0.352).

**H4 frozen fit** (OLS on 2018-2022, in bp of the +1 min ZT log return per training-sample SD of each feature):

| Model | const | s~ | z_A | U |
|---|---|---|---|---|
| T (text only) | 0.0733 | -0.0155 | | |
| C (combined) | 0.0733 | +0.0126 | -0.0218 | -0.0836 |

Sign hits over the 211 test answers with a non-zero return: C 0.498, T 0.488.

## 4. Secondary rows (reported, outside Holm)

### H2: costs on the same 268 trades (ZT, +1 min)

| Cost | C0 | C2 | C4 | CM | CQ | C2F | C4F | CMF |
|---|---|---|---|---|---|---|---|---|
| Mean ticks | -0.086 | -4.086 | -8.086 | -1.108 | -1.112 | -4.598 | -8.598 | -1.620 |
| Wild-cluster p (two-sided) | 0.438 | 0.0001 | 0.0001 | 0.0004 | 0.0003 | 0.0001 | 0.0001 | 0.0001 |

C2 and C4 charge 2 and 4 ticks per side. Measured spreads (CM) cost about 1.02 ticks per round trip. The F rows add
the unverified $2.00 per side fee.

### H2: other answer-level rows (gross)

| Row | n (answers / meetings) | Mean ticks | Wild-cluster p (two-sided) | 90% CI |
|---|---|---|---|---|
| ZT +5 min | 81 / 10 | -0.790 | 0.0115 | [-1.127, -0.506] |
| ZT +15 min | 31 / 10 | -2.065 | 0.125 | [-3.567, -0.531] |
| ZT +1 min, +30 s entry | 268 / 10 | -0.146 | 0.0508 | [-0.253, -0.036] |
| ES +1 min (short ES on +sign(z)) | 268 / 10 | +0.444 | 0.608 | [-0.637, +1.583] |
| ZF +1 min | 268 / 10 | -0.052 | 0.680 | [-0.245, +0.121] |
| ZN +1 min | 268 / 10 | -0.078 | 0.373 | [-0.206, +0.037] |
| 2018-2022, ZT +1 min | 247 / 12 | +0.032 | 0.831 (year-clustered 0.690) | [-0.138, +0.211] |
| Pooled 2018-2026 | 515 / 22 | -0.029 | 0.733 | [-0.137, +0.092] |
| Pooled, excluding 2020-2021 | 358 / 14 | -0.045 | 0.700 | [-0.199, +0.110] |
| Sensitivity 1 (drop text flags) | 268 / 10 | -0.086 | 0.438 (same as primary) | [-0.262, +0.068] |
| Sensitivity 2 (drop degraded) | 239 / 9 | -0.146 | 0.176 | [-0.309, -0.012] |
| Sensitivity 3 (start uncertainty <= 10 s) | 77 / 3 | -0.182 | 0.0996 | [-0.289, -0.077] |

The pre-registered position is long ZT on higher arousal, so a negative mean is the opposite sign to the hypothesis.
The +5 min row (p 0.012) is one of many unadjusted secondary rows. In 2018-2022 the same row has the other sign
(+1.53 ticks, p 0.118).

### H2: meeting level (ZT, signal z_A,m, gross, n = 10)

| Exit | Mean ticks | Sign-flip p (two-sided) | 90% CI |
|---|---|---|---|
| 16:00 | +0.70 | 0.746 | [-2.2, +3.3] |
| 16:30 | +4.0 | 0.142 | [+0.6, +7.4] |
| 16:00, +30 s execution clock | +0.80 | 0.706 | [-1.8, +3.4] |

### Companion slopes

Each row is an OLS of the +1 min ZT log return (bp) on [feature, s~, R], plus M for the face rows.

| Feature | Sample | Coefficient | CR1 t | Wild-bootstrap p |
|---|---|---|---|---|
| H2 arousal z | 2023-2026 | -0.0112 | -0.41 | 0.653 |
| H2 arousal z | 2018-2022 | -0.0469 | -1.34 | 0.182 (year-clustered 0.412) |
| H2 arousal z | pooled 2018-2026 | -0.0097 | -0.40 | 0.702 |
| Dominance z (descriptive) | 2023-2026 | +0.0144 | +0.63 | 0.534 |
| H3 U (killed; not used) | 2023-2026 | -0.064 | -0.82 | 0.478 |

### Descriptive rows

- **Dominance** (answer level, ZT +1 min, 2023-2026): +0.034 ticks, n = 268, p 0.789. At the meeting level (16:00
  exit) it is -0.9 ticks, sign-flip p 0.673.
- **Residualised valence** (section 3.6): **n = 0.** The local feature tree has no text-stage outputs, so every
  chunk's text score is missing. This is an input limitation of the local tree, not a code fault. Whether the
  HiPerGator tree has the text stage is open.
- **H3, computed for the record (killed; p = 1 enters Holm):**
  - answer level: +0.011 ticks, n = 272 in 10 meetings, 90% CI [-0.176, +0.217];
  - meeting level, 16:00 exit: -3.1 ticks, sign-flip p 0.165.
- **Tier-3 face features** (descriptive, no kill rule applies to them):
  - cheekSquint and eyeWide hit their variance floor in every meeting. Their z-scores are about 0, so their slopes
    are meaningless; the cheekSquint slope of about -1,550 is an example.
  - browInnerUp without reading frames hits its floor in 36% of meetings.

### H4: further rows (not decisive)

| Row | Clark-West t | p (one-sided) | OOS R², C vs T | Sign hits C / T |
|---|---|---|---|---|
| ZT, frozen fit (primary) | 0.722 | 0.244 | -0.0043 | 0.498 / 0.488 |
| ES, frozen fit | -0.930 | 0.812 | -0.0101 | 0.465 / 0.465 |
| ZT, expanding window | 0.544 | 0.300 | -0.0077 | 0.488 / 0.474 |
| ZT, leave-one-meeting-out 2023-2026 (not point-in-time) | -0.948 | 0.816 | -0.0162 | 0.507 / 0.502 |
| ZT, leave-one-meeting-out 2018-2022 (not point-in-time; n 247, 12 meetings, df 11) | 1.595 | 0.0695 | +0.0006 | 0.520 / 0.559 |
| Meeting level ZT (HC3, n = 10) | 2.389 | 0.0203 (two-sided 0.0407) | +0.407 | 0.7 / 0.5 |
| Meeting level ES (HC3, n = 10) | 2.046 | 0.0356 | +0.121 | 0.4 / 0.4 |

**The meeting-level rows rest on 10 observations and sit outside Holm.** Both meeting-level ZT models forecast worse
than zero: OOS R² is -0.489 for C and -1.513 for T. The C-vs-T gain is therefore relative to a poor text-only model.

**H4 trade P&L at +1 min (ZT, 268 test answers, mean ticks):**

| Positions | C0 | C2 | C4 |
|---|---|---|---|
| sign(ŷC) | -0.026 (wild-cluster p 0.838; CI [-0.270, +0.193]; hit rate 0.392) | -4.026 | -8.026 |
| sign(ŷT) | -0.153 (p 0.336) | -4.153 | -8.153 |

On ES, sign(ŷC) and sign(ŷT) are identical: always long, because the intercept dominates. Their mean is -0.511
ticks gross (C2 -4.511, C4 -8.511).

## 5. Note-1 descriptive rows

Note 1 asks for every primary test to be reported without 20190501 and without 20230614. Both rows are
**identical** to the main rows for H2, H3, H4 and Holm:

| Row | H2 mean (p) | H3 | H4 Clark-West t (one-sided p) | Holm H2 / H3 / H4 |
|---|---|---|---|---|
| Main | -0.0858 (0.4382) | killed | 0.722 (0.2442) | 0.8764 / 1.0 / 0.7327 |
| Without 20190501 | identical | identical | identical | identical |
| Without 20230614 | identical | identical | identical | identical |

Neither meeting enters any feature, baseline, fit, position or trade:

- **20190501** fails the frozen gates: caption offset -172.8 s, `drop_timing` = 1, QA failed. It is in no baseline,
  its z_A and U are empty, and it is not among the 12 H4 training meetings. Its chunk records (97 valid chunks inside
  answers) sit only in the record table `features/voice_chunks_assigned.parquet` and are never used.
- **20230614**: `drop_timing` = 1, no caption-timed answers and 0 chunks. Note 2 found its video to be the
  2023-07-26 press conference; none of its voice or face rows is used.

**Correction to note 1, section 1.** Note 1 says 20190501 "stays in the 2018-2022 training sample". Under the
frozen gates it does not. The H4 training sample is 12 meetings without it, so the "without 20190501" row equals the
main row.

## 6. Strategy-level metrics of the H2 and H4 test trades

This section presents trades that are already fixed. It follows deviation D-3's last section and uses the same
conventions as `backtests/results/presser_strategy/` (see its README). No position, sample or rule changes. G3 stays NO-GO.

**Method:**
- **Trades.** The stage's own trades: ZT, +1 min, positions sign(z_A) for H2 and sign(ŷC) for H4, with sign(ŷT) as
  the text-only reference.
- **Daily series.** The S&P 500 trading calendar, with zero P&L on days without a trade. Sharpe is annualised with
  sqrt(252), and the drawdown is additive.
- **Sizing.** One contract's gross daily volatility over the training window (2019-10-30 .. 2022-12-30, 799 trading
  days, 247 trades) is scaled to 10% a year on $10m. That gives N = 7,036 contracts for H2, 8,245 for H4 sign(ŷC)
  and 6,941 for sign(ŷT).
- **Costs.** net 1x = the measured half-spread at the entry and exit seconds plus $2 per side. Every trade had a
  measured quote, so this equals the stage's CMF row. net 2x doubles that cost.
- **Reconciliation.** The H4 log returns equal the stage's y. The C0, C2 and C4 test-sample means equal
  `h4_results.json`.

**Test window 2023-02-01 .. 2026-04-29** (10 meetings, 268 trades). Each cell shows annualised return / annualised
volatility / Sharpe / maximum drawdown:

| Strategy | Gross | Net 1x | Net 2x |
|---|---|---|---|
| H2 sign(z_A) | -3.92% / 8.32% / -0.47 / -20.8% | -74.0% / 42.1% / -1.76 / -238.7% | -144.0% / 81.6% / -1.77 / -464.7% |
| H4 sign(ŷC) | -1.40% / 11.23% / -0.12 / -22.5% | -83.5% / 48.6% / -1.72 / -269.4% | -165.6% / 94.6% / -1.75 / -534.3% |
| H4 sign(ŷT) (reference) | -6.89% / 12.30% / -0.56 / -24.4% | -76.0% / 44.7% / -1.70 / -245.2% | -145.1% / 83.3% / -1.74 / -468.2% |

**Other windows** (Sharpe gross / net 1x / net 2x):

| Strategy | Training window (in-sample for the H4 fit) | Competition IS: first trade .. 2024-10-02 (303 trades, includes training) | Competition OOS: 2024-10-03 .. 2026-10-02 (212 trades, 8 meetings) |
|---|---|---|---|
| H2 sign(z_A) | 0.14 / -1.86 / -1.92 | 0.19 / -1.62 / -1.66 | -0.77 / -2.00 / -2.01 |
| H4 sign(ŷC) | 0.53 / -1.89 / -1.93 | 0.65 / -1.64 / -1.67 | -0.71 / -1.97 / -2.00 |
| H4 sign(ŷT) | 0.86 / -1.88 / -1.93 | 0.47 / -1.59 / -1.65 | -0.54 / -1.93 / -1.99 |

**How to read these tables:**
- Gross returns are about zero at best. Net of costs, every window loses: 1.4 to 1.7 ticks per trade at net 1x.
- The training-window rows for H4 are in-sample by construction.
- The competition OOS window is a calendar split, not an unseen holdout.
- The sizing convention puts roughly 140-165 times the capital into each one-minute trade, because the gross
  volatility is so small. With an additive drawdown, the net rows show drawdowns beyond -100%. These rows describe costs, not a
  strategy.

## 7. Verification

**Independent recomputation.** A separate script recomputed the results without importing the stage code. It used
only the run's feature, position and fit tables and the 1-minute bar file (sha256 `268aa049...`, as pinned in the
ADDENDUM).
- **110 checks, 0 mismatches.** The largest relative difference is 7.5e-15.
- **Features.** z_A, z_D, z_BD, z_BI, z_ES and U, recomputed from the raw answer values, equal the feature table.
  The G4 outcomes are reproduced: 0 of 22 for arousal, dominance, BD and ES; 22 of 22 for browInnerUp. The 20190619
  caption offset is -2.788 s.
- **H2.** The positions (+sign(z_A)) and the selections match.
  - Every trade's position and gross ticks equal the run's.
  - Mean -0.0858209 ticks; CR1 SE 0.105365, so t -0.81451; p 0.4382 with the same seed.
  - With another seed and 99,999 draws, p is 0.4343.
- **H3.** Mean +0.011029, t 0.0671, p 0.9507.
- **H4.**
  - Refitting the 2018-2022 model from market data reproduces every coefficient and standardisation constant to
    within 2.6e-15.
  - Clark-West t 0.72230, one-sided p 0.244227.
  - Wild bootstrap 0.2576 / 0.5001. With another seed: 0.2494 / 0.4961.
  - The OOS R² values, sign hits and the per-answer y, ŷT and ŷC match.
- **Holm.** H2 0.8764, H3 1.0, H4 0.73268.
- **Order of operations (section 9).** File write times and the code confirm the order:
  1. qa manifest 01:19:01.854;
  2. features manifest 01:19:01.877;
  3. positions manifest 01:19:03.372;
  4. fit.json 01:19:04.257;
  5. first results file 01:19:14.916.

  Nothing in `qa/`, `features/`, `positions/` or `h4_fit/` changed afterwards. Steps 1 and 2 never load market data.
  Step 3 joins prices for training rows only, and asserts that their dates fall on or before 2022-12-31.
- **Caveats.**
  - Step 3 loads the whole bar file into memory, although it joins no 2023-2026 price before the fit is hashed.
  - The training-tag check in `bar_log` is vacuous (0 events).
  - The ordering evidence rests on write times plus the code.
- **Excluded meetings.**
  - 20200303, 20200315 and the three Warsh meetings: no package table was read.
  - 20230614: only its turns and chair-check tables were read.
  - 20190501: as in section 5.
- **Price levels.** Among the outputs, only `results/answer_trades.csv` and `results/meeting_trades.csv` carry price
  levels (`entry_px`, `exit_px`). Both are in the git-ignored folder.

**Emulation of the HiPerGator job.** `hpg/run_backtests.sbatch` was run end to end on the PC on the local features,
and the h234 stage reproduced every table and verdict of this run. Only these differ:
- the hashes driven by the output path (`qa/provenance.json`, then the qa manifest, then `fit.json`'s
  `qa_manifest_sha256`, then `h4_results.json`'s `fit_sha256`);
- without the re-encode tree, the source-invariance label text.

## 8. For the comparison with the HiPerGator reference run

- **Features.** The reference run uses the HiPerGator tables (speech on B200, face on CPU; note 1, section 2), so
  small value differences are possible. Compare with `backtests/tools/compare_results.py` (numbers), not by bytes or
  hashes. Line ends (LF vs CRLF) and the path-driven hash chain above differ in any case.
- **compare_results false difference.** `compare_results.py` reports the empty `qa/valence_resid_fits.csv` as a
  difference ("No columns to parse from file"). Ignore it.
- **Re-encode tree.** Without it on HiPerGator, the H2 label reads "source invariance not checked" without the
  "(missing re-runs: ...)" suffix. The ICC is not computed either way.
- **Residualised valence.** It can only be non-empty if the HiPerGator tree has the text stage.
- **Commit risk.** Before committing any reference-run output, note that `results/h4_answer_rows.csv` holds y = 1e4
  x ln(exit/entry) per answer at full precision. Together with a per-trade tick table for the same answers, it lets
  the entry prices be recovered. Keep it git-ignored, or round or drop y.
- **Bar and quote data notes (this run).** `bar_log` records 24 next-open skips and 33 stale closes. 1,593 bad quote
  records were skipped.

## 9. Standing labels

- Exploratory, post-G3 (post-NO-GO); cannot rescue G3; no trading claim.
- G3 stays NO-GO. In the locked register H2, H3 and H4 stay at p = 1 (R2-26).
- Local replication (note 1, section 2). The HiPerGator reference is pending, governs where the runs disagree, and
  its agreement will be reported.
- H3 killed by G4 (browInnerUp floor, 22 of 22). H2: source invariance not checked. H4 carries both statuses.
- Any significant result could only motivate a new pre-registered test on another chair. No forward Powell data
  will ever exist.
