#!/bin/bash
# Step 3 (GPU): asr (Whisper large-v3-turbo, faster-whisper) -> turns (transcript words on ASR clocks, anchor,
# known_at) -> diarize (ECAPA chair-voice check) -> voice (Powell vocal_proxy). One GPU per array task; the
# task's group of meetings is drained by WORKERS_PER_GPU processes on that GPU. submit_all.sh throttles the
# array to 2 running tasks (%2), so at most 2 GPUs are in use.
#SBATCH --job-name=fp-03-speech
#SBATCH --account=jie.xu
#SBATCH --qos=jie.xu
#SBATCH --partition=hpg-b200
#SBATCH --gres=gpu:b200:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=14
#SBATCH --mem=96gb
#SBATCH --time=02:00:00
#SBATCH --output=fp-03-speech_%A_%a.out
set -uo pipefail
_c="${FP_PKG:-$SLURM_SUBMIT_DIR}/slurm/common.sh"
[ -f "$_c" ] || { echo "cannot find $_c: run sbatch from the package folder (cd /blue/jie.xu/$USER/fed_presser_hpg)" >&2; exit 2; }
source "$_c"
PARTITION=${PARTITION:-${SLURM_JOB_PARTITION:-}} fp_gpu_profile || exit 2
export FP_GPU_TYPE_SET=$GPU_TYPE
fp_banner
fp_activate || exit 2
fp_step_speech || exit $?
