# Gator Quant Hacks 2026: trading on what the Fed says

A systematic trading study for the Gator Quant Hacks 2026 Systematic Trading track. It asks whether Federal Reserve
communication (speeches, statements, minutes and press conferences) predicts next-day moves in long Treasuries and
the US dollar. A walk-forward language model scores every Fed document for hawkish or dovish stance. The main
strategy, **v2 T4xE1**, turns those scores into a daily, volatility-targeted position in TLT and UUP. Every test was
pre-registered, with a hashed and timestamped plan, before its results were computed.

**Bottom line.** The strategy failed its own pre-registered decision rule. Its in-sample Sharpe at twice the
modelled costs was 0.387, against a required 0.5, and that verdict stands. The two-year out-of-sample window was
opened once, for reporting only. There it earned a modest, statistically insignificant result. Adding it to an
existing three-sleeve portfolio raised that portfolio's Sharpe, but a paired bootstrap cannot tell the gain from
zero. The press-conference voice and face studies found nothing. The full write-up is
[docs/report/REPORT.md](docs/report/REPORT.md).

## Results at a glance

Main strategy: v2 T4xE1 with both D-4 implementation fixes. Returns are daily excess returns over the T-bill, net
of modelled costs. In-sample is 2016-01-04..2024-10-02 and out-of-sample is 2024-10-03..2026-10-02.

| | In-sample | Out-of-sample |
|---|---|---|
| Sharpe, net 1x / 2x costs | 0.446 / 0.392 | 0.621 / 0.554 |
| Annual excess return (geometric) / volatility | 4.52% / 11.35% | 3.77% / 6.28% |
| Maximum drawdown (excess, starting NAV included) | -18.5% | -7.19% |
| One-way turnover per year | 27.2x | 18.5x |
| Newey-West t of the mean | 1.42 | 0.86 |
| Pre-registered decision rule (in-sample Sharpe at 2x > 0.5) | **FAILED** (0.387 as committed) | not a test: opened once under deviation D-3 |

| Supporting portfolio test (out-of-sample) | Sharpe net / 2x |
|---|---|
| core_ER_6 alone (three existing sleeves) | 0.601 / 0.456 |
| core_ER_6 + v2 T4xE1 as a fourth sleeve | 0.871 / 0.703 |
| Gain from adding v2, paired block bootstrap | +0.27; 90% interval [-0.12, +0.71], includes zero |

Every number above was reproduced on HiPerGator. Sources:
- metrics: [docs/results/sharpe-summary.md](docs/results/sharpe-summary.md) and `results_2/metrics/v2_metrics.csv`;
- bootstrap: `results_2/attribution/bootstrap.csv`;
- the original, unfixed results: `backtests/results/v2_oos/`.

## Repository structure

```
.
├── README.md                 this page: overview, structure, setup, how to run, data
├── docs/                     ALL documentation (index: docs/README.md)
│   ├── report/               the full team report (REPORT.md) and its earlier draft
│   ├── submission/           competition texts: Devpost description, submission status, reproduction commands
│   ├── guides/               how-tos: data, running the backtests, reproduction, HiPerGator, stance model, v2, replay
│   ├── results/              results write-ups: strategy results, Sharpe summary, H2-H4 local run, reviewer-gap coverage
│   └── research/             planning notes, reviews, literature and data-feasibility notes
├── preregistration/          hypotheses, amendments, deviations D-1..D-4 and PREREG_LOG.md (frozen; code checks their hashes)
├── backtests/                the maintained backtest code and every committed result
│   ├── run_all_backtests.sh  one command for every stage: chrono, v2, presser, h234
│   ├── v2/                   the v2 strategy (run_v2*.py, v2lib.py, sim_fixed.py, run_v2_d4.py), its scores, public inputs/
│   ├── presser/              press-conference study: events, Q&A text, ADDENDUM.md, backtest code, H2-H4 reference run
│   ├── wire/                 stance-score wiring and the combined summary
│   ├── tools/                compare_results.py, the reproduction check
│   └── results/              v2/ (in-sample), v2_oos/ (D-3), v2_d4/ (D-4), presser_h1/, presser_strategy/, capacity/, summary.md
├── results_2/                reviewer-gap analyses built from committed outputs only (no new backtest)
│                             metrics/, attribution/, turnover_capacity/, provenance/, replay/
├── nlp/                      walk-forward chrono-BERT stance model: label dating, training, scoring
├── hpg/                      HiPerGator Slurm jobs; fedpress_pkg/ is the voice, face and speech feature package
├── data/                     public data: Fed text corpus, press-conference transcripts and captions, local feature tables
├── strategies/01/            the original strategy 01 hypothesis and its independent review (historical)
├── massive-8k/               the separate Massive 8-K options challenge (notebook and write-up); not part of the Fed study
├── backtest_snapshot/        frozen code, inputs and outputs behind the 2026-10-03 results (provenance record)
└── archive/                  collected session outputs and earlier work (historical, not maintained)
```

Code and documentation are kept apart. Every guide and write-up is in `docs/`. Markdown files outside `docs/` are
one of four kinds:
- records the code reads or hash-checks: `preregistration/`, `backtests/presser/ADDENDUM.md`;
- files written by the scripts next to their results: the READMEs, `metrics.md` and `tables.md` under
  `backtests/results/` and `results_2/`;
- frozen history: `backtest_snapshot/`, `archive/`, `strategies/01/`;
- the feature package's own manual in `hpg/fedpress_pkg/`;
- the separate Massive 8-K challenge in `massive-8k/`, whose README and write-up sit beside its notebook.

`backtests/README.md`, `backtests/v2/README.md` and `nlp/README.md` are one-line pointers, kept because the scripts'
messages mention those paths.

## Setup

Python 3.12 and bash (Git Bash on Windows works):

```bash
git clone -c core.autocrlf=false https://github.com/savioxavier/gator-quant-hacks.git
```

```bash
cd gator-quant-hacks && python -m venv .venv && source .venv/bin/activate
```

On Windows Git Bash, activate with `source .venv/Scripts/activate` instead.

```bash
pip install -r hpg/backtest_requirements.txt
```

`hpg/backtest_requirements.txt` pins the package versions that produced the committed results: numpy, pandas,
pyarrow, scipy, statsmodels and matplotlib. Clone with `core.autocrlf=false`. The pre-registration hash checks fail
if git rewrites line endings.

## How to run

There are three levels. Each one needs more inputs than the one before.

### 1. Replay the published results (public, no licensed data, about a minute)

```bash
python results_2/replay/replay.py
```

This recomputes the headline tables and figures from the committed daily return series and trade rows, then
compares them with the committed tables. It covers:
- the D-3 and D-4 v2 metrics;
- the in-sample selection;
- the press-conference strategy tables;
- the G3 headline;
- the H2-H4 Holm family;
- the results_2 metrics table.

It prints PASS or FAIL per item. The exit code is 0 when everything passes, 1 on a mismatch and 2 on a missing
input. Output goes to `results_2/replay/replay_out/`, which is git-ignored. This checks the arithmetic from the
published series to the published tables. It does not re-run signal construction or execution. Details:
[docs/guides/saved-result-replay.md](docs/guides/saved-result-replay.md).

The reviewer-gap analyses rebuild from committed files the same way. Each refuses to run on a missing input:

```bash
python results_2/metrics/compute_metrics.py && python results_2/metrics/test_drawdown.py
```

```bash
python results_2/attribution/attribution.py && python results_2/turnover_capacity/capacity.py && python results_2/provenance/provenance_check.py
```

### 2. Full backtest reproduction (needs licensed market data)

```bash
bash backtests/run_all_backtests.sh
```

The runner has four stages. `bash backtests/run_all_backtests.sh v2` (or `presser`, `h234`) runs one alone:

| Stage | What it does | Inputs it needs (environment variables) |
|---|---|---|
| chrono (optional) | rebuilds the stance-score inputs from a finished stance-model run and checks them against the frozen ones | `CHRONO_ROOT` |
| v2 | `backtests/v2/run_v2_chrono.py --reproduce`: recomputes the in-sample run and the one D-3 out-of-sample evaluation; then `run_v2_d4.py` recomputes D-4. Compared with the committed results to 1e-9. It never selects or evaluates anything new | `GQH_REPO`, `GQH_DATA_DIR`, `V2_WORK_ROOT` |
| presser | the press-conference suite (BENCH-R, H1, H1-Q, H1-answer, lexicon control, spreads), compared with `backtests/results/presser_h1/` | `GQH_MARKET_DIR` |
| h234 | exploratory H2 (voice), H3 (face) and H4 (combined) on the feature tables | `FEDPRESS_ROOT` (e.g. `$PWD/data/fedpress_features_local`), `GQH_MARKET_DIR`; with the local tables also set `H234_OUT_DIR=$PWD/backtests/presser/backtest_h234_local`, so the committed HiPerGator reference run is not overwritten |

What each variable points at:
- `V2_WORK_ROOT`: `$PWD/backtests/v2/inputs/work` in this repository.
- `GQH_DATA_DIR`:
  - the public FRED and T-bill files from `backtests/v2/inputs/data/`;
  - the private ETF and futures daily files (see Data below).
- `GQH_REPO`: the backtest engine (gqh-flow-clock at commit 1587f25).
- `GQH_MARKET_DIR`: the three Databento intraday files.

Re-run outputs go to `backtests/rerun/`, which is git-ignored and holds price levels, so never commit it. The exit
status is non-zero when a stage fails, is refused or does not reproduce. A skipped stage is reported as skipped.
Count a run as a reproduction only when every stage you need reports that it reproduces. Full guide:
[docs/guides/running-backtests.md](docs/guides/running-backtests.md). What is reproducible from what:
[docs/guides/reproduction.md](docs/guides/reproduction.md).

### 3. On HiPerGator (UF)

Log in yourself (GatorLink and Duo), clone the repository on `/blue`, and submit from the repo root:

| Job | Command | Notes |
|---|---|---|
| Every backtest stage | `sbatch hpg/backtest_all.sbatch` | CPU. First copy the three Databento files to your home directory (`scp *__all_2016_2026.parquet <gatorlink>@hpg.rc.ufl.edu:`); the job moves them to `$GQH_DATA/market` and packs the results into `~/gqh_backtest_results.tgz` without price levels |
| v2 only (in-sample, D-3, D-4) | `sbatch hpg/v2_oos.sbatch` | needs the v2 input bundle `~/gqh_v2_bundle.tgz`, no market files |
| Download the press-conference recordings | `sbatch hpg/fetch_audio.sbatch` | CPU, 95 videos (about 65 GB) and 16 kHz audio, to `/blue/.../fedpress` |
| Voice, face and speech features | `sbatch hpg/run_everything.sbatch` | 2 + 2 B200 GPUs; fetches the pinned models first; then `sbatch hpg/pack_features.sbatch` packs the tables |
| Stance model (36 fine-tunes and scoring) | `bash hpg/submit_nlp.sh` | four chained GPU jobs |

Guides:
- jobs and the feature package: [docs/guides/hipergator.md](docs/guides/hipergator.md) and
  `hpg/fedpress_pkg/README.md`;
- the stance model: [docs/guides/stance-model.md](docs/guides/stance-model.md).

## Data

| Data | Source | Licence | In this repository? |
|---|---|---|---|
| Fed speeches, statements, minutes, press-conference transcripts | federalreserve.gov | public domain (US government) | yes: `data/text_corpus/`, `data/fomc_pressers/` |
| Press-conference video and captions | federalreserve.gov | public domain | captions yes; video no (65 GB): `sbatch hpg/fetch_audio.sbatch` downloads it |
| Voice, face and speech feature tables (64 Powell conferences) | our feature package run on the recordings | ours; model licences apply (one voice model is CC BY-NC-SA) | yes: `data/fedpress_features_local/` |
| Stance-model training labels | gtfintechlab/fomc_communication (Hugging Face) | CC BY-NC 4.0 | downloaded at run time; the re-dated label index is committed |
| Stance base models | manelalab/chrono-bert-v1 (Hugging Face) | MIT | downloaded at run time |
| Treasury yields and T-bill | FRED | public | yes: `backtests/v2/inputs/data/` |
| v2 work inputs (edge return series, FOMC dates, speech scores) | our earlier research | ours | yes: `backtests/v2/inputs/work/` |
| ETF daily prices (TLT, UUP, ...) | Yahoo Finance via yfinance | no redistribution | **no**: download yourself |
| Futures daily and intraday bars and quotes (ZT, ZF, ZN, ES) | Databento, CME Globex GLBX.MDP3 | licensed | **no**: needs your own Databento account (the intraday set cost about $8.53) |

The repository is public. Licensed prices and quotes are never committed, and that includes results that would
reveal price levels. What is published is returns, tick moves, spreads in ticks, P&L and statistics.
[docs/guides/data.md](docs/guides/data.md) covers:
- the exact Databento and Yahoo requests;
- the SHA-256 of every private file used, so a rebuilt copy can be checked;
- how the public data were collected;
- what each committed data folder holds.

## Documentation

| Document | What it is |
|---|---|
| [docs/README.md](docs/README.md) | index of all documentation |
| [docs/report/REPORT.md](docs/report/REPORT.md) | the full report: hypothesis, data, method, results, robustness, limitations |
| [docs/submission/](docs/submission/) | the competition submission texts |
| [docs/guides/results-guide.md](docs/guides/results-guide.md) | how to read the metrics and verdicts |
| [docs/results/strategy-results.md](docs/results/strategy-results.md) | every strategy result with its source file |
| [docs/results/reviewer-gap-coverage.md](docs/results/reviewer-gap-coverage.md) | how each external-review point was resolved |
| [preregistration/PREREG_LOG.md](preregistration/PREREG_LOG.md) | timeline of every pre-registration, amendment and deviation |
| [massive-8k/README.md](massive-8k/README.md) | the separate Massive 8-K options challenge (notebook and write-up). Not part of the Fed study |

## Ground rules this repository keeps

- **Pre-registration first.** Plans are hashed and committed before results. Deviations are written down before
  what they authorise is computed. A failed decision rule stays failed.
- **The out-of-sample window was opened once** (deviation D-3), for reporting. Nothing has been tuned on it.
- **Frozen records are not edited.** This covers `preregistration/`, `backtests/results/v2*/` and
  `backtest_snapshot/`. Re-runs write to `backtests/rerun/` and are compared file by file.
- **No licensed data in git.** This covers Databento and Yahoo prices, and any file derived from them that carries
  price levels.
