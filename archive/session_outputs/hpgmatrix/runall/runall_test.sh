#!/bin/bash
#SBATCH --job-name=fedmaster
#SBATCH --account=ai-workshop
#SBATCH --qos=ai-workshop
#SBATCH --partition=hpg-default
#SBATCH --cpus-per-task=8
#SBATCH --mem=32gb
#SBATCH --time=04:00:00
#SBATCH --output=fedmaster_%j.log
# One job that starts everything on HiPerGator (submit from the repo root):   sbatch hpg/run_everything.sbatch
#  1. links the recordings from hpg/fetch_audio.sbatch into the feature package (no second 67 GB download)
#  2. builds the feature-package environment on /blue if it is missing (the text chain builds its own)
#  3. submits two chains, 2 GPUs each (4 at once, group limit 5):
#     - features: fetch (small files only) -> audio+frames -> speech (Whisper timing, chair voice) -> face
#     - text: 36 walk-forward chrono-BERT trainings -> 12 scoring tasks -> merge (corrected label dates)
# Options: GPU_TYPE=rtx6000 sbatch hpg/run_everything.sbatch  (default b200; rtx6000 was rejected on 2026-10-03 with
#          "Requested node configuration is not available"). SKIP_NLP=1 skips the text chain (already scored locally).
#          STEPS=speech,face resubmits only those feature steps (default fetch,av,speech,face; finished meetings are
#          skipped either way). FACE_ON_CPU=1 runs face on hpg-default instead of a GPU.
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
export USER="${USER:-$(id -un)}"
export FP_GROUP=ai-workshop
export FEDPRESS_ROOT=<scratch>/hpgmatrix/runall/root FP_ENV=<scratch>/hpgmatrix/runall/env
export GPU_TYPE="${GPU_TYPE:-b200}"
export GPU_PROFILE="$GPU_TYPE"          # the text chain (hpg/submit_nlp.sh) reads GPU_PROFILE
export MAX_GPUS=2
echo "[$(date)] root=$FEDPRESS_ROOT gpu=$GPU_TYPE"

# 1. reuse the downloaded recordings
: link_fetched

# 2. feature-package environment (idempotent)
: setup env

# 2b. models: the GPU steps run offline (config.yaml runtime.offline_gpu), so every model they load must already be
#     in $FEDPRESS_ROOT/cache. These are the models of the asr, turns, diarize, voice and face sections; all are
#     ungated (no Hugging Face token). Already cached models are not downloaded again. A failed download stops here.
SPEECH_FACE_MODELS=whisper_turbo_ct2,ecapa_voxceleb,audeering_msp_dim,mediapipe_face_landmarker,emotiefflib_enet_b0_8_va_mtl,sface_opencv
( export FP_PKG="$PWD/hpg/fedpress_pkg"
  source hpg/fedpress_pkg/slurm/common.sh
  fp_activate
  python -m fedpress.cli prefetch-models --keys "$SPEECH_FACE_MODELS" )

# 3. submit both chains
: submit_all
if [ "${SKIP_NLP:-0}" != 1 ]; then : nlp; else echo "text chain skipped (SKIP_NLP=1)"; fi

echo "[$(date)] all chains submitted; watch with: squeue -u $USER"
echo "feature status: $FEDPRESS_ROOT  (python hpg/fedpress_pkg/slurm/status.py)"
