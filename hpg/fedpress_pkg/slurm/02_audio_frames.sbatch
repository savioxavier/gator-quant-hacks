#!/bin/bash
# Step 2 (CPU): 16 kHz mono WAV for every meeting, 1 fps JPEG frames for the chairs in face.chairs (Powell).
# Same array size and grouping as step 1, so task i starts as soon as fetch task i is done (aftercorr).
#SBATCH --job-name=fp-02-av
#SBATCH --account=jie.xu
#SBATCH --qos=jie.xu
#SBATCH --partition=hpg-default
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=48gb
#SBATCH --time=03:00:00
#SBATCH --output=fp-02-av_%A_%a.out
set -uo pipefail
_c="${FP_PKG:-$SLURM_SUBMIT_DIR}/slurm/common.sh"
[ -f "$_c" ] || { echo "cannot find $_c: run sbatch from the package folder (cd /blue/jie.xu/$USER/fed_presser_hpg)" >&2; exit 2; }
source "$_c"
fp_banner
fp_activate || exit 2
mapfile -t SEL < <(fp_selection)
mapfile -t SETS < <(fp_sets; fp_face_sets)
python -m fedpress.cli launch audio,frames "${SEL[@]}" --set compute.gpu_type=cpu --workers-per-gpu "$CPU_WORKERS" $(fp_force av) \
  ${MAX_SECONDS:+--max-seconds "$MAX_SECONDS"} "${SETS[@]}"
fp_status $? "audio + frames" || exit $?
fp_check audio || exit $?
