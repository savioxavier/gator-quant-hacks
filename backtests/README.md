# Backtests

Every backtest of the Fed-communication study, with one command to run them:

```
bash backtests/run_all_backtests.sh
```

`../backtest_snapshot/` keeps the frozen provenance record (exact code, inputs and every output) behind the results
reported on 2026-10-03. This folder is the maintained version: portable paths, one runner, a reproduction check,
and the new H2/H3/H4 stage.

## Tests and verdicts

| Test | Pre-registration | Verdict | Code | Results |
|---|---|---|---|---|
| Fed communication v2: daily stance strategy, 8 combinations (T1-T4 x E1/E2) | `../preregistration/HYPOTHESIS_v2.md` (Amendments 1-3), `../preregistration/DEVIATIONS.md` | **Decision rule FAILED** (full in-sample Sharpe at 2x costs 0.387 <= 0.5; validation 0.687), and the verdict stands. **Out-of-sample evaluated once, for reporting only**, under deviation D-3 (`../preregistration/v2_DEVIATION_D3_OOS.md`): T4xE1 Sharpe 0.607 net 1x, 0.544 net 2x; it cannot reverse the verdict and is never evaluated again | `v2/` | `results/v2/`, `results/v2_oos/`, `results/summary.md` |
| Press conference BENCH-R: 13:50-14:20 ZT move, continuation into the press conference | `../preregistration/presser_ADDENDUM.md` section 5 (non-blind descriptive replication) | Continuation before 2020, reversal after; neither significant | `presser/backtest/code/` | `results/presser_h1/` |
| Press conference H1-primary: Q&A tone minus statement tone (point-in-time residual), ZT from the end of the press conference to 16:00 | `presser_ADDENDUM.md` section 3, gate G3 in 8.2; `../preregistration/presser_team_FINAL_PLAN.md`; `../preregistration/presser_DEVIATION_D1.md` (stance model) | **G3 NO-GO**: Powell 2023-2026, n = 20, mean +0.50 ticks gross (USD 3.91), one-sided p = 0.45, 90% block-bootstrap CI [-4.06, 5.30] ticks | `presser/backtest/code/` | `results/presser_h1/key_results.json`, `results/summary.md` |
| H1-Q: H1 with question tone added to the residual regression | ADDENDUM section 6 (robustness only, not gated) | Not detected (confirmation sample mean USD 4.69, p = 0.44) | same | `results/presser_h1/summary_long.csv` |
| H1-answer: answer-level version at +1/+5/+15 min, plus the 1 s latency sweep | ADDENDUM section 4 (diagnostic only) | Nothing detected (confirmation +1 min: -0.135 ticks, wild-cluster p = 0.23) | same | `results/presser_h1/h1answer_summary.csv`, `h1answer_1s_sweep_summary.csv` |
| Lexicon negative control (frozen lexicon scores through the same pipelines) | ADDENDUM section 6 | No effect, as expected (`lex_H1` not estimable: 4 of 75 meetings; `lex_H1_raw` G3 replica: n = 20, mean -4.1 ticks, NO-GO) | same | `results/presser_h1/key_results.json` |
| H2 (voice arousal), H3 (upper-face composite), H4 (combined vs text-only, Clark-West) | `../preregistration/presser_H2H3H4_EXPLORATORY.md` (EXPLORATORY, POST-G3) | HiPerGator reference results are committed: H2 and H4 were not detected; H3 was stopped by its variance gate. These exploratory tests do not overturn G3 or support a trading claim. H2 source invariance was not checked. | `presser/backtest/code/h234_*.py` | `presser/backtest_h234/`; local replication summary: `presser/backtest_h234/H234_LOCAL_SUMMARY.md` |

The H2/H3/H4 stage was built and checked on placebo features (null, calibrated p-values) and on a planted positive
control (detected). Those runs are not results and are not in this repository.

## Layout

```
backtests/
  run_all_backtests.sh        the one command (stages: chrono, v2, presser, h234)
  README.md
  v2/                         run_v2.py, v2lib.py, run_v2_chrono.py, adapt_v2.py, score/ (the document scores used)
  presser/
    ADDENDUM.md               frozen execution rules (sha256 1921b2ca...de2dc4, checked by every step)
    events/                   the 75 press conferences: calendar, timing, caption QA, and market-derived returns,
                              tick moves and spread statistics (no price levels); events_columns.csv defines them
    text/                     Q&A segmentation and timing (no stance columns) and the code that built it
    text_chrono/              the stance-scored text label used by H1 (prereg-pinned hashes)
    adapt_presser.py          chrono sentence labels -> text_chrono/
    backtest/code/            s01..s05 (QA, positions, P&L, spreads, tables) and h234_s1..s4 (H2/H3/H4)
    backtest/positions/       the frozen H1 positions read by the H2/H3/H4 stage (read-only)
  wire/                       check_chrono.py, summarize.py, wirelib.py (shared wiring for the chrono scores)
  tools/compare_results.py    reproduction check: a re-run against the committed results
  results/
    summary.md, summary.json  the combined results of v2 and H1 (chrono stance scores)
    v2/                       selection, windows, portfolio, by-chair, sensitivity, decision record
    v2_oos/                   the one out-of-sample evaluation under D-3: metrics, daily returns, run/ (its record)
    presser_h1/               key results, summary tables, G3 trades and per-meeting tables (no price levels)
  rerun/                      re-run outputs (git-ignored)
```

## Running

### Environment variables

| variable | needed for | meaning |
|---|---|---|
| `PY` | all | Python with pandas, numpy, scipy, pyarrow (statsmodels for v2). Default `python` |
| `GQH_MARKET_DIR` | presser, h234 | folder holding the licensed Databento files `ohlcv-1m__all_2016_2026.parquet`, `ohlcv-1s__all_2016_2026.parquet`, `bbo-1s__all_2016_2026.parquet` (ZT/ZF/ZN/ES `.v.0`, 13:30-16:30 ET on the 75 press-conference days). Default `$GQH_DATA_DIR/presser` |
| `GQH_DATA_DIR` | v2 reproduction | the gqh data cache (`v2/data` of the v2 input bundle) |
| `CHRONO_ROOT` | chrono (optional) | chrono walk-forward work root (`../nlp/run_local.py`); rebuilds and checks the frozen stance inputs |
| `CHRONO_PY` | chrono (optional) | Python for `nlp/chrono_stance.py merge`, used only if the merge is missing |
| `FEDPRESS_ROOT` | h234 | fedpress output tree `<root>/meetings/<presser_id>/` (`../hpg/fedpress_pkg`) |
| `H234_SI_ROOT` | h234 (optional) | the 64 kbps source-invariance re-runs of 2019-01-30, 2019-03-20, 2019-06-19 (`voice/voice_chunks.parquet` and `_done/voice.json`); without it H2 carries the label "source invariance not checked" |
| `H234_OUT_DIR` | h234 (optional) | output folder; default `presser/backtest_h234` |
| `FEDPRESS_PKG` | h234 (optional) | the fedpress package; default `../hpg/fedpress_pkg` |
| `BACKTEST_RERUN_DIR` | all (optional) | re-run outputs; default `backtests/rerun` |
| `GQH_REPO`, `V2_WORK_ROOT` | v2 reproduction | gqh-flow-clock and the v2 work-root inputs (`v2/gqh-flow-clock`, `v2/work` of the v2 input bundle); see `v2/README.md` |

### What the command does

1. **chrono** (only with `CHRONO_ROOT`): checks that the chrono run finished, rebuilds the v2 document scores and
   `text_chrono/` into `rerun/chrono_inputs/`, and compares them with the committed frozen inputs.
2. **v2**: never evaluates the out-of-sample window again. The decision rule failed
   (`results/v2/oos_not_evaluated.json`) and that verdict stands; under deviation D-3 the window was evaluated once,
   for reporting (`results/v2_oos/`, record `results/v2_oos/run/oos_chosen.json`).
   - With `GQH_REPO`, `GQH_DATA_DIR` and `V2_WORK_ROOT` set (the v2 input bundle), it runs
     `v2/run_v2_chrono.py --reproduce`. That recomputes the committed in-sample run and the D-3 evaluation into
     `rerun/v2_reproduce/` and compares them with `results/v2/` and `results/v2_oos/` (numbers to 1e-9 relative). It
     writes no decision record and chooses nothing; it prints PASS or FAIL and writes
     `rerun/v2_reproduce/reproduce_report.json`.
   - Without them it says so, prints both records and skips. `run_v2_chrono.py` and `run_v2.py run` refuse a new run
     on their own too.
3. **presser**: runs the ADDENDUM suite (BENCH-R, H1-primary, H1-Q, H1-answer with the 1 s sweep, lexicon control,
   spreads) on `presser/text_chrono/` into `rerun/presser_h1/`. It then compares the re-run with
   `results/presser_h1/` and the frozen positions (numbers to 1e-9 relative). With `CHRONO_ROOT` it also writes a
   fresh combined summary to `rerun/summary/`.
4. **h234**: runs only when `FEDPRESS_ROOT` holds voice or face tables; otherwise it prints a skip message. It runs
   real features only:
   - this script refuses a placebo tree (a `PLACEBO.json` marker or "placebo" in the path), a placebo re-run tree
     and a placebo output folder;
   - the stage itself also refuses tables or done markers stamped as placebo.

   The order is fixed by section 9 of the pre-registration:
   - s1: features and QA, no market data;
   - s2: positions, no prices;
   - s3: the H4 fit on 2018-2022, hashed before any 2023-2026 price is read;
   - s4: tests and Holm across the three primary tests.

   Every table carries the label "exploratory, post-NO-GO; cannot rescue G3; no trading claim".

The exit status is non-zero if a stage failed, was refused, or did not reproduce the committed results. A skipped
h234 stage (no features yet) and a skipped v2 stage (v2 inputs not set) are not failures. One stage can be run alone:
`bash backtests/run_all_backtests.sh presser`.

### Locally (Git Bash on Windows, or any bash)

```
cd <repo>
PY=<python with pandas/numpy/scipy/pyarrow/statsmodels> \
GQH_MARKET_DIR=<folder with the three licensed parquet files> \
CHRONO_ROOT=<chrono work root, optional> \
bash backtests/run_all_backtests.sh
```

For the v2 reproduction, unpack the v2 input bundle (`tar -xzf gqh_v2_bundle.tgz -C <root>`) and add
`GQH_REPO=<root>/v2/gqh-flow-clock GQH_DATA_DIR=<root>/v2/data V2_WORK_ROOT=<root>/v2/work`. On Windows, clone this
repository with `git clone -c core.autocrlf=false`, or the pre-registration hash check fails.

Once the fedpress tables are copied back from HiPerGator, add `FEDPRESS_ROOT=<copied fedpress root>` and, if
available, `H234_SI_ROOT=<64 kbps re-run tree>`.

### On HiPerGator

First copy the licensed market data **privately**. /blue is readable by the whole group, so the files go in a
mode-700 folder in your home directory, never under /blue and never into the repository:

```
# on your own machine
ssh <gatorlink>@hpg.rc.ufl.edu 'mkdir -p ~/private/gqh_market && chmod 700 ~/private ~/private/gqh_market'
scp <local market dir>/ohlcv-1m__all_2016_2026.parquet <local market dir>/ohlcv-1s__all_2016_2026.parquet \
    <local market dir>/bbo-1s__all_2016_2026.parquet <gatorlink>@hpg.rc.ufl.edu:~/private/gqh_market/
```

Then, on HiPerGator, after the fedpress feature run (`../hpg/fedpress_pkg/README.md`):

```
srundev --time=02:00:00 --cpus-per-task=4 --mem=16gb
cd /blue/jie.xu/$USER/<repo clone>            # git clone -b review/strategy-01 <repo url>, or git pull
source hpg/fedpress_pkg/env/activate.sh       # fedpress env (pandas, numpy, scipy, pyarrow); sets FEDPRESS_ROOT
PY=python GQH_MARKET_DIR=$HOME/private/gqh_market FEDPRESS_ROOT=/blue/jie.xu/$USER/fedpress \
  bash backtests/run_all_backtests.sh
```

Notes for the HiPerGator run:
- Keep `turns.clock_source = asr` (the config default) in the fedpress run. With `vtt` or `vtt_then_asr` the
  package skips `vtt_check`, the stage's "check missing means out" rule drops every meeting, and H2 and H3 cannot
  run.
- The stage stops if the model revisions stamped in the parquet metadata differ from the pre-registration (audeering
  6eba34a2, ECAPA 0f99f2d0, MediaPipe 64184e22, SFace 0ba9fbfa, emotiefflib==1.1.1). A difference needs a dated
  deviation note first.
- The fedpress env has no statsmodels, which the v2 reproduction needs. Run that stage with
  `../hpg/backtest_all.sbatch` (its environment, `../hpg/backtest_requirements.txt`, has it). The job unpacks the v2
  input bundle when `~/gqh_v2_bundle.tgz` (or its parts) is in your home directory; see its header.
- The fedpress env's pandas (2.3) is older than the one used for the committed results. The reproduction check
  reports any numeric difference above 1e-9 relative.
- Write nothing derived from the market files into a group-readable folder. `rerun/` (git-ignored) holds trade logs
  with price levels.

## Data and licensing

- **Market data (licensed, Databento): never in git.** These are the ohlcv-1m, ohlcv-1s and bbo-1s files for
  ZT/ZF/ZN/ES. The committed results keep tick moves, returns, spreads in ticks, and P&L, but no price levels: the
  trade logs and per-meeting tables have `entry_px`/`exit_px` removed. A re-run's own outputs in `rerun/` contain
  price levels and are git-ignored; do not commit them. `events/events_market_long.csv`, which holds price levels,
  is not part of this folder.
- **Fed text, video and captions** are public-domain US government works. The events, text tables, transcripts and
  stance scores here are derived from them.
- **Stance model labels** come from gtfintechlab/fomc_communication (CC BY-NC 4.0). The stance scores are derived
  from a model trained on them.
- **Frozen text files and line ends.** The frozen H1 files were written on Windows with CRLF line ends. The
  repository stores them with LF (`.gitattributes`). The original hashes are still checked:
  - the H2/H3/H4 stage restores CRLF before it compares the H1 positions with the manifest hash pinned when the
    stage was written (8707dbd2...440f);
  - `events/events.csv` restored to CRLF has the hash pinned in the pre-registrations (13ace998...bcae);
  - the parquet files are byte-identical (for example, `text_chrono` answers 146f281a...afd6 and meetings
    c9196464...b028).

## Changes from the frozen code (`../backtest_snapshot/`)

- **Paths.** Every location comes from an environment variable or from the repository layout; there is no
  machine-specific default (`presser/backtest/code/lib.py`, `h234_lib.py`, `v2/run_v2.py`, `wire/wirelib.py`).
- **Presser defaults.** The default text label is `text_chrono/` (the reported H1 run). The default output folder is
  `rerun/presser_h1/`. s01-s05 refuse to write into `presser/backtest/`, the frozen folder. s01 records the plan
  documents under their names in `../preregistration/` and lists absent ones as missing.
- **H2/H3/H4.**
  - The H1 code hash used by H4 covers the seven H1 files only, not the stage's own files.
  - The frozen positions are checked with the line-end rule above.
  - The real run's default output folder is `presser/backtest_h234/`.
- **v2.**
  - The one-shot lock is checked against the committed decision record whatever output folder is given, before
    gqh-flow-clock is imported, and again inside `stage_oos`.
  - `run_v2_chrono.py --reproduce` (added after the D-3 run) recomputes that run through the same `pipeline_is` and
    `stage_oos`. It refuses unless the committed D-3 record exists, writes only to `rerun/v2_reproduce/`, writes no
    decision record (`oos_reproduced.json` instead) and stops before the out-of-sample stage unless the in-sample
    selection gives the committed combination.
  - `run_v2.py` accepts the current pre-registration hash as well as the Amendment-1 hash it pinned.
  - check and smoke outputs go to `rerun/`.
- **Statistics.** No rule, parameter or test was changed. The re-run is compared with the committed results file by
  file.
