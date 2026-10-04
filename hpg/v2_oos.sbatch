#!/bin/bash
#SBATCH --job-name=gqh-v2-oos
#SBATCH --account=ai-workshop
#SBATCH --qos=ai-workshop
#SBATCH --partition=hpg-default
#SBATCH --cpus-per-task=4
#SBATCH --mem=16gb
#SBATCH --time=01:00:00
#SBATCH --output=v2-oos_%j.log
# v2's out-of-sample test on HiPerGator (CPU only). Submit from the repo root:
#   sbatch hpg/v2_oos.sbatch
# What it does: recomputes, from scratch, the v2 in-sample run and the one out-of-sample evaluation of T4xE1
# (2024-10-03..2026-10-02) made under deviation D-3 (preregistration/v2_DEVIATION_D3_OOS.md), and compares every number
# with the committed results (backtests/results/v2, backtests/results/v2_oos) to 1e-9 relative: PASS or FAIL, with the
# headline numbers (in-sample and out-of-sample Sharpe at 1x and 2x costs, return, vol, drawdown, portfolio test),
# reproduced next to committed. The decision rule failed (full in-sample Sharpe at 2x costs 0.387 <= 0.5) and that
# verdict stands; this job chooses nothing, changes no parameter and writes no decision record. The out-of-sample stage
# runs only after the in-sample files agree with backtests/results/v2.
# Needs the v2 input bundle and no market files. Before the first run, copy gqh_v2_bundle.tgz (or its parts
# gqh_v2_bundle.tgz.part01, .part02, ...) and gqh_v2_bundle.tgz.sha256 to your home directory:
#   scp gqh_v2_bundle.tgz* $USER@hpg.rc.ufl.edu:
# The job unpacks it into $GQH_DATA/v2 (default /blue/ai-workshop/$USER/gqh_data/v2) and reuses that folder later.
# Output: this job's log v2-oos_<job id>.log, the report backtests/rerun/v2_reproduce/reproduce_report.json, and
# ~/gqh_backtest_results.tgz to copy back. It runs hpg/backtest_all.sbatch with STAGE=v2, which holds the bundle
# handling, the Python environment and the packing.
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
export STAGE=v2
exec bash hpg/backtest_all.sbatch
