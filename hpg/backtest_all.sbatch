#!/bin/bash
#SBATCH --job-name=gqh-backtest
#SBATCH --account=ai-workshop
#SBATCH --qos=ai-workshop
#SBATCH --partition=hpg-default
#SBATCH --cpus-per-task=8
#SBATCH --mem=32gb
#SBATCH --time=02:00:00
#SBATCH --output=gqh-backtest_%j.log
# Every backtest of the strategy on HiPerGator (CPU only). Submit from the repo root:
#   sbatch hpg/backtest_all.sbatch
# Before the first run, copy the three licensed market files to your home directory (the job moves them to
# $GQH_DATA/market):  scp <market dir>/*__all_2016_2026.parquet $USER@hpg.rc.ufl.edu:
# What it does:
#  1. builds the Python 3.12 environment once (hpg/backtest_requirements.txt, pinned to the committed results)
#  2. runs backtests/run_all_backtests.sh all: v2 (decision record, or its out-of-sample run once the repo has it),
#     the press-conference suite (BENCH-R, H1, compared with the committed results) and H2/H3/H4 on this account's
#     feature tables (the HiPerGator reference run of note 1)
#  3. packs the results into ~/gqh_backtest_results.tgz, without the trade logs that hold price levels
# Options: STAGE=presser|h234|v2 runs one stage; V2 runs also need GQH_REPO, GQH_DATA_DIR and V2_WORK_ROOT.
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
export USER="${USER:-$(id -un)}"
GQH_DATA="${GQH_DATA:-/blue/ai-workshop/$USER/gqh_data}"
ENV_DIR="${ENV_DIR:-/blue/ai-workshop/$USER/envs/gqh-backtests}"
export FEDPRESS_ROOT="${FEDPRESS_ROOT:-/blue/ai-workshop/$USER/fedpress}"
echo "[$(date)] repo=$PWD data=$GQH_DATA env=$ENV_DIR features=$FEDPRESS_ROOT"

# 1. market files: move any just copied to the home directory into place. Files that arrived split (e-mail
#    attachments <name>.part01, .part02, ...) are joined first; SHA256SUMS_market, if present, is checked.
mkdir -p "$GQH_DATA/market"
for f in ohlcv-1m__all_2016_2026.parquet ohlcv-1s__all_2016_2026.parquet bbo-1s__all_2016_2026.parquet; do
  if compgen -G "$HOME/$f.part*" > /dev/null; then
    cat $(ls "$HOME/$f".part* | sort) > "$HOME/$f.joined" && mv -f "$HOME/$f.joined" "$HOME/$f" && rm -f "$HOME/$f".part*
  fi
done
if [ -f "$HOME/SHA256SUMS_market" ]; then
  (cd "$HOME" && sha256sum -c --ignore-missing SHA256SUMS_market) || { echo "market files damaged (checksum)" >&2; exit 2; }
fi
for f in ohlcv-1m__all_2016_2026.parquet ohlcv-1s__all_2016_2026.parquet bbo-1s__all_2016_2026.parquet; do
  [ -f "$HOME/$f" ] && mv -f "$HOME/$f" "$GQH_DATA/market/$f"
  [ -f "$GQH_DATA/market/$f" ] || { echo "missing $GQH_DATA/market/$f: copy it first (see the header)" >&2; exit 2; }
done
export GQH_MARKET_DIR="$GQH_DATA/market"

# 2. Python environment (built once; delete $ENV_DIR to rebuild)
if [ ! -x "$ENV_DIR/bin/python" ]; then
  set +eu                                     # the module and conda shell code trips over -e/-u
  type module >/dev/null 2>&1 || source /etc/profile >/dev/null 2>&1
  module load conda
  if command -v mamba >/dev/null; then tool=mamba; else tool=conda; fi
  set -eu
  "$tool" create -y -p "$ENV_DIR" python=3.12 pip
  "$ENV_DIR/bin/python" -m pip install --no-cache-dir -r hpg/backtest_requirements.txt
fi
export PY="$ENV_DIR/bin/python"
"$PY" -c 'import numpy, pandas, scipy, pyarrow; print("python", __import__("sys").version.split()[0], "pandas", pandas.__version__, "numpy", numpy.__version__)'

# 3. every backtest (the full output is also kept in backtests/rerun/run_all_backtests.log)
mkdir -p backtests/rerun
set +e
bash backtests/run_all_backtests.sh "${STAGE:-all}" 2>&1 | tee backtests/rerun/run_all_backtests.log
rc=${PIPESTATUS[0]}
set -e

# 4. results to copy back. Left out: the H2/H3/H4 trade logs with entry/exit prices and the re-run folders, whose
#    comparison with the committed results is in the log.
out="$HOME/gqh_backtest_results.tgz"
paths=(backtests/rerun/run_all_backtests.log)
for p in backtests/results backtests/presser/backtest_h234; do [ -e "$p" ] && paths+=("$p"); done
tar czf "$out" --exclude='answer_trades.csv' --exclude='meeting_trades.csv' --exclude='*.pyc' "${paths[@]}"
sha256sum "$out"; ls -lh "$out"
echo "copy back to the PC (Git Bash there):  scp $USER@hpg.rc.ufl.edu:gqh_backtest_results.tgz ."
echo "[$(date)] run_all_backtests.sh exit code $rc"
exit "$rc"
