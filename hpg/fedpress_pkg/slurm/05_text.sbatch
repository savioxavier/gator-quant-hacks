#!/bin/bash
# Step 5 (GPU): walk-forward stance models (deviation D1: chrono-bert-v1-<min(Y-1,2024)>1231 fine-tuned on labels
# with year <= Y-1, 3 seeds; 30 fine-tunes for 2016-2026, shared O_EXCL queue, idempotent), then the text stage
# (statement, chair answers, reporter questions; FOMC-RoBERTa cross-check when its gated weights are cached).
#SBATCH --job-name=fp-05-text
#SBATCH --account=jie.xu
#SBATCH --qos=jie.xu
#SBATCH --partition=hpg-b200
#SBATCH --gres=gpu:b200:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=14
#SBATCH --mem=96gb
#SBATCH --time=01:30:00
#SBATCH --output=fp-05-text_%A_%a.out
set -uo pipefail
_c="${FP_PKG:-$SLURM_SUBMIT_DIR}/slurm/common.sh"
[ -f "$_c" ] || { echo "cannot find $_c: run sbatch from the package folder (cd /blue/jie.xu/$USER/fed_presser_hpg)" >&2; exit 2; }
source "$_c"
PARTITION=${PARTITION:-${SLURM_JOB_PARTITION:-}} fp_gpu_profile || exit 2
export FP_GPU_TYPE_SET=$GPU_TYPE
fp_banner
fp_activate || exit 2
fp_step_text || exit $?
