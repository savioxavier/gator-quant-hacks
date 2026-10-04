#!/bin/bash
# Step 4 (GPU, or CPU with FACE_ON_CPU=1): face (Powell expression_proxy). Default = team plan: MediaPipe
# landmarks/blendshapes + SFace identity gate + EmotiEffLib at 1 fps from the frames zip. FACE_PRESET=pyfeat2
# or pyfeat5 runs the plan_v0 py-feat option from its own env ($FP_ENV_PYFEAT), decoding the video itself.
#SBATCH --job-name=fp-04-face
#SBATCH --account=jie.xu
#SBATCH --qos=jie.xu
#SBATCH --partition=hpg-b200
# No #SBATCH --gres line: submit_all.sh passes --gres for the GPU step and none for FACE_ON_CPU=1 (a header
# --gres would survive the CPU partition override and make the CPU job ask hpg-default for a B200).
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=14
#SBATCH --mem=96gb
#SBATCH --time=01:30:00
#SBATCH --output=fp-04-face_%A_%a.out
set -uo pipefail
_c="${FP_PKG:-$SLURM_SUBMIT_DIR}/slurm/common.sh"
[ -f "$_c" ] || { echo "cannot find $_c: run sbatch from the package folder (cd /blue/jie.xu/$USER/fed_presser_hpg)" >&2; exit 2; }
source "$_c"
if [ "$FACE_ON_CPU" != 1 ]; then
  PARTITION=${PARTITION:-${SLURM_JOB_PARTITION:-}} fp_gpu_profile || exit 2
  export FP_GPU_TYPE_SET=$GPU_TYPE
fi
fp_banner
case "$FACE_PRESET" in pyfeat*) fp_activate "$FP_ENV_PYFEAT" || exit 2 ;; *) fp_activate || exit 2 ;; esac
fp_step_face || exit $?
fp_check face || exit $?
