# Reproduction commands

There are two separate paths, and they make different claims:

1. **Public saved-result replay.** Recomputes the headline tables and figures from the committed derived files: daily
   return series, held weights and trade rows. It needs no licensed data. It shows that the published tables follow
   from the published series. It does **not** validate signal construction or execution.
2. **Full backtest reproduction.** Rebuilds the series themselves from the frozen document scores and the market
   data. It needs private, licensed inputs.

## Pinned revisions

| What | Revision |
|---|---|
| This repository, submission release | the commit that contains this file on `main` (tag it at release; see `submission_status.md`) |
| Original v2 run and its one D-3 out-of-sample evaluation | results committed in `88ce3ab`; code hashes listed in `backtests/results/v2_oos/RUN_LOG.md` (code as committed at `6a61ef9`) |
| D-4 corrections (main strategy) | `ba16940` (code and results); `6629abf` (runner also recomputes D-4) |
| Full HiPerGator rerun of every stage | `cdb2be6` (logs in `backtests/results/v2_oos/hpg_reproduction/` and `backtests/results/v2_d4/hpg_reproduction/`) |
| Backtest engine (full path only) | github.com/minh-stakc/gqh-flow-clock at commit `1587f25` |
| Python environment | Python 3.12 with `hpg/backtest_requirements.txt` (numpy 2.5.3, pandas 3.0.6, pyarrow 25.0.1, scipy 1.18.1, statsmodels 0.15.0, matplotlib 3.11.2) |

## Setup (both paths)

```bash
git clone -c core.autocrlf=false https://github.com/savioxavier/gator-quant-hacks.git
```

```bash
cd gator-quant-hacks && python -m venv .venv && source .venv/bin/activate && pip install -r hpg/backtest_requirements.txt
```

On Windows Git Bash, activate with `source .venv/Scripts/activate`. Keep `core.autocrlf=false`: the pre-registration
hash checks fail if git rewrites line endings.

## Path 1: public saved-result replay

```bash
python results_2/replay/replay.py
```

**Inputs.** Committed files only: the frozen D-3 run files, `backtests/results/v2_d4/`,
`backtests/results/presser_strategy/`, `backtests/results/presser_h1/`, the H2/H3/H4 reference results and
`results_2/metrics/v2_metrics.csv`. It uses no network and reads no price levels.

**Expected output.** Seven `PASS` lines, then `replay PASSED (exit 0)`:

| Item | Comparisons |
|---|---|
| D-3 metrics | 601 |
| In-sample selection | 309 |
| D-4 metrics | 1,781 |
| Press-conference strategy | 5,100 |
| G3 headline | 7 |
| H2/H3/H4 Holm family | 42 |
| results_2 table | 582 |

Numbers that cannot be recomputed from committed files are printed as `SKIP`, with the reason. A SKIP is not a pass
of that number.

**Failure behaviour.** Exit 1 on a mismatch; exit 2 when an input is missing (each missing file is named). Output goes
to `results_2/replay/replay_out/` (git-ignored). The script refuses to write into frozen folders.

**The reviewer-gap analyses.** Each reads committed files only, exits non-zero on a missing input, and re-running gives
byte-identical outputs:

```bash
python results_2/metrics/compute_metrics.py && python results_2/metrics/test_drawdown.py
```

```bash
python results_2/attribution/attribution.py && python results_2/turnover_capacity/capacity.py
```

```bash
python results_2/provenance/provenance_check.py && python results_2/ledger/build_ledger.py
```

## Path 2: full backtest reproduction

**Private inputs.** Obtain these yourself; the exact requests and the SHA-256 of our copies are in
`docs/guides/data.md`.

| File | Source | SHA-256 (first 8) |
|---|---|---|
| `etf_daily.parquet` | Yahoo Finance via yfinance (no redistribution) | `7086babd` |
| `futures_daily.parquet` | Databento GLBX.MDP3 ohlcv-1d | `71db580d` |
| `futures_1600.parquet` | Databento GLBX.MDP3 ohlcv-1h | `aef98c99` |
| `ohlcv-1m__all_2016_2026.parquet` | Databento, press-conference windows | `268aa049` |
| `ohlcv-1s__all_2016_2026.parquet` | Databento, press-conference windows | `4081e89b` |
| `bbo-1s__all_2016_2026.parquet` | Databento, press-conference windows | `8b3c1804` |

Yahoo's adjusted prices are revised over time, so a fresh `etf_daily.parquet` may not match its checksum. Small v2
differences can come from that alone.

**Public inputs (in the repository):**
- `backtests/v2/inputs/work/`, to point `V2_WORK_ROOT` at;
- `backtests/v2/inputs/data/fred_daily.parquet` and `rf_daily.parquet`, to copy into `GQH_DATA_DIR`;
- the frozen document scores, under `backtests/v2/score/` and `backtests/presser/text_chrono/`;
- the feature tables, under `data/fedpress_features_local/`.

**Command:**

```bash
GQH_REPO=<gqh-flow-clock clone at 1587f25> GQH_DATA_DIR=<folder with the five daily files> V2_WORK_ROOT=$PWD/backtests/v2/inputs/work GQH_MARKET_DIR=<folder with the three Databento intraday files> FEDPRESS_ROOT=$PWD/data/fedpress_features_local H234_OUT_DIR=$PWD/backtests/presser/backtest_h234_local bash backtests/run_all_backtests.sh
```

**What reproduces:**
- **v2** prints `PASS`. It recomputes the in-sample run and the D-3 evaluation into `backtests/rerun/v2_reproduce/` and
  compares them with the committed files to 1e-9 relative. It then recomputes D-4 into `backtests/rerun/v2_d4/`.
- **presser** reproduces `backtests/results/presser_h1/`.
- **h234** completes. With the local feature tables it gives the local replication. `H234_OUT_DIR` keeps it out of the
  committed reference folder `backtests/presser/backtest_h234/`, whose numbers came from the HiPerGator tables.

**Failure behaviour.**
- The exit status is non-zero when a stage fails, is refused or does not reproduce.
- A stage whose inputs are absent is reported as skipped. Count a run as a reproduction only when every stage you need
  reports that it reproduces.
- Re-run outputs go to `backtests/rerun/`. That folder is git-ignored and holds price levels, so never commit it.

**On HiPerGator:**

```bash
sbatch hpg/backtest_all.sbatch
```

```bash
sbatch hpg/v2_oos.sbatch
```

The first runs every stage. Copy the three Databento files to your home directory first. The second runs v2 only and
needs the v2 input bundle `~/gqh_v2_bundle.tgz`. See `docs/guides/hipergator.md`.

## What neither path claims

- **That the stance scores can be regenerated.** That needs the 36 fine-tunes (`bash hpg/submit_nlp.sh`, GPU). The
  frozen scores are committed and hash-checked.
- **That the multimedia features can be regenerated.** That needs the recordings and the feature package
  (`sbatch hpg/run_everything.sbatch`). These features are exploratory and the v2 submission does not need them.
- **That an unseen event can be processed live.** No live wall-clock timing was measured.
