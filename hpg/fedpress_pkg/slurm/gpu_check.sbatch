#!/bin/bash
# One-off check on a real GPU node (about 5 minutes): driver, compute mode, torch on sm_100, CTranslate2 CUDA
# (faster-whisper), onnxruntime CUDA, ffmpeg, HF token presence/mode (never its value) and the model cache.
#   sbatch slurm/gpu_check.sbatch                    # B200
#   GPU_TYPE=rtx6000 sbatch --partition=hpg-rtx6000 --gres=gpu:rtx-pro-6000:1 slurm/gpu_check.sbatch
#SBATCH --job-name=fp-gpucheck
#SBATCH --account=jie.xu
#SBATCH --qos=jie.xu
#SBATCH --partition=hpg-b200
#SBATCH --gres=gpu:b200:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32gb
#SBATCH --time=00:20:00
#SBATCH --output=fp-gpucheck_%j.out
set -uo pipefail
_c="${FP_PKG:-$SLURM_SUBMIT_DIR}/slurm/common.sh"
[ -f "$_c" ] || { echo "cannot find $_c: run sbatch from the package folder (cd /blue/jie.xu/$USER/fed_presser_hpg)" >&2; exit 2; }
source "$_c"
fp_banner
fp_activate || exit 2
nvidia-smi
echo "CUDA MPS control daemon: $(command -v nvidia-cuda-mps-control || echo 'not found')"
python -m fedpress.cli doctor --set "compute.gpu_type=${GPU_TYPE:-b200}"
