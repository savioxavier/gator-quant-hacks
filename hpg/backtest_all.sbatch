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
#  2. runs backtests/run_all_backtests.sh all: v2 (with the v2 input bundle, reproduces the committed in-sample run
#     and its one D-3 out-of-sample evaluation; otherwise prints the records), the press-conference suite (BENCH-R,
#     H1, compared with the committed results) and H2/H3/H4 on this account's feature tables (note 1's reference run)
#  3. packs the results into ~/gqh_backtest_results.tgz, without the trade logs that hold price levels (with the v2
#     reproduction's report, out-of-sample record, in-sample summary and portfolio table)
# Options: STAGE=presser|h234|v2 runs one stage (STAGE=v2 needs no market files).
# v2 input bundle: ~/gqh_v2_bundle.tgz or its e-mail parts ~/gqh_v2_bundle.tgz.part01, .part02, ... (joined in order).
# v2 bundle check: ~/gqh_v2_bundle.tgz.sha256, if present, is checked; then v2/MANIFEST.sha256 after unpacking.
# v2 bundle place: unpacked into $GQH_DATA/v2 (archive, parts and .sha256 deleted afterwards); while $GQH_DATA/v2
#   exists the job sets GQH_REPO, GQH_DATA_DIR and V2_WORK_ROOT to it.
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
export USER="${USER:-$(id -un)}"
unset BACKTEST_RERUN_DIR   # re-run outputs stay in backtests/rerun, where step 3 clears and step 4 packs them
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
if [ -f "$HOME/SHA256SUMS_market" ] && compgen -G "$HOME/*__all_2016_2026.parquet" > /dev/null; then
  # only when market files are waiting in the home directory (sha256sum fails when it verifies none of them)
  (cd "$HOME" && sha256sum -c --ignore-missing SHA256SUMS_market) || { echo "market files damaged (checksum)" >&2; exit 2; }
fi
need_market=1; [ "${STAGE:-all}" = v2 ] && need_market=0
for f in ohlcv-1m__all_2016_2026.parquet ohlcv-1s__all_2016_2026.parquet bbo-1s__all_2016_2026.parquet; do
  [ -f "$HOME/$f" ] && mv -f "$HOME/$f" "$GQH_DATA/market/$f"
  [ -f "$GQH_DATA/market/$f" ] || [ "$need_market" = 0 ] \
    || { echo "missing $GQH_DATA/market/$f: copy it first (see the header)" >&2; exit 2; }
done
compgen -G "$HOME/*__all_2016_2026.parquet*" > /dev/null || rm -f "$HOME/SHA256SUMS_market"   # all moved: done with it
export GQH_MARKET_DIR="$GQH_DATA/market"

# 1b. v2 inputs not in git (gqh_v2_bundle.tgz, see the header): join the parts, check the archive and the manifest in
#     a staging folder, then replace $GQH_DATA/v2. The archive and parts are deleted only after both checks pass.
V2B="$HOME/gqh_v2_bundle.tgz"
if [ -f "$V2B" ] || compgen -G "$V2B.part*" > /dev/null; then
  if compgen -G "$V2B.part*" > /dev/null; then cat $(ls "$V2B".part* | sort) > "$V2B"; fi
  if [ -f "$V2B.sha256" ]; then
    want=$(awk '{print $1; exit}' "$V2B.sha256"); got=$(sha256sum "$V2B" | awk '{print $1}')
    [ "$want" = "$got" ] || { echo "gqh_v2_bundle.tgz damaged or incomplete (sha256 $got, expected $want)" >&2; exit 2; }
    echo "gqh_v2_bundle.tgz: sha256 $got OK"
  fi
  unpack="$GQH_DATA/.v2_unpack"
  rm -rf "$unpack"; mkdir -p "$unpack"
  tar xzf "$V2B" -C "$unpack" || { echo "v2 bundle: cannot unpack $V2B" >&2; exit 2; }
  (cd "$unpack/v2" && sha256sum -c --quiet MANIFEST.sha256) || { echo "v2 bundle: MANIFEST.sha256 check failed" >&2; exit 2; }
  echo "gqh_v2_bundle.tgz: MANIFEST.sha256 OK ($(wc -l < "$unpack/v2/MANIFEST.sha256") files)"
  rm -rf "$GQH_DATA/v2"; mv "$unpack/v2" "$GQH_DATA/v2"; rmdir "$unpack"
  rm -f "$V2B" "$V2B".part* "$V2B.sha256"
fi
if [ -d "$GQH_DATA/v2" ]; then
  export GQH_REPO="$GQH_DATA/v2/gqh-flow-clock" GQH_DATA_DIR="$GQH_DATA/v2/data" V2_WORK_ROOT="$GQH_DATA/v2/work"
  echo "v2 inputs: $GQH_DATA/v2 (GQH_REPO, GQH_DATA_DIR, V2_WORK_ROOT set)"
else
  echo "v2 inputs: none (no ~/gqh_v2_bundle.tgz and no $GQH_DATA/v2); the v2 stage prints the records only"
fi

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
V2R=backtests/rerun/v2_reproduce
V2R_PACK=("$V2R/reproduce_report.json" "$V2R/oos_reproduced.json" "$V2R/summary_is.json" "$V2R/portfolio_oos.csv")
rm -f "${V2R_PACK[@]}"   # packed below only when this job's v2 stage writes them
set +e
bash backtests/run_all_backtests.sh "${STAGE:-all}" 2>&1 | tee backtests/rerun/run_all_backtests.log
rc=${PIPESTATUS[0]}
set -e

# 4. results to copy back. Left out: the H2/H3/H4 trade logs with entry/exit prices and the re-run folders, whose
#    comparison with the committed results is in the log (the v2 reproduction's report and headline files are kept).
out="$HOME/gqh_backtest_results.tgz"
paths=(backtests/rerun/run_all_backtests.log)
for p in backtests/results backtests/presser/backtest_h234 "${V2R_PACK[@]}"; do
  [ -e "$p" ] && paths+=("$p")
done
tar czf "$out" --exclude='answer_trades.csv' --exclude='meeting_trades.csv' --exclude='*.pyc' "${paths[@]}"
sha256sum "$out"; ls -lh "$out"
echo "copy back to the PC (Git Bash there):  scp $USER@hpg.rc.ufl.edu:gqh_backtest_results.tgz ."
echo "[$(date)] run_all_backtests.sh exit code $rc"
exit "$rc"
