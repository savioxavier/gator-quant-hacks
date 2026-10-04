#!/bin/bash
# Step 1 (CPU, network): MP4, transcript PDF, statement HTML and captions for each meeting.
# One array task per group of meetings (--shard i/N); 4 meetings download at once inside a task.
# Compute nodes appear to have outbound HTTPS (docs/HIPERGATOR_NOTES.md section 11). The job checks that
# first and stops with a clear message if not; then run `bash slurm/00_setup.sh fetch` in an srundev session.
#SBATCH --job-name=fp-01-fetch
#SBATCH --account=jie.xu
#SBATCH --qos=jie.xu
#SBATCH --partition=hpg-default
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8gb
#SBATCH --time=04:00:00
#SBATCH --output=fp-01-fetch_%A_%a.out
set -uo pipefail
_c="${FP_PKG:-$SLURM_SUBMIT_DIR}/slurm/common.sh"
[ -f "$_c" ] || { echo "cannot find $_c: run sbatch from the package folder (cd /blue/jie.xu/$USER/fed_presser_hpg)" >&2; exit 2; }
source "$_c"
fp_banner
fp_activate || exit 2
for url in https://www.federalreserve.gov https://edge.api.brightcove.com https://huggingface.co; do
  code=$(curl -s -o /dev/null --max-time 20 -w '%{http_code}' "$url" || true)
  if [ "${code:-000}" = 000 ]; then
    fp_log "no outbound HTTPS from $(hostname) to $url: run 'bash slurm/00_setup.sh fetch' in an srundev session"
    exit 4
  fi
done
mapfile -t SEL < <(fp_selection)
mapfile -t SETS < <(fp_sets)
python -m fedpress.cli launch fetch "${SEL[@]}" --set compute.gpu_type=cpu --workers-per-gpu "${FETCH_WORKERS:-4}" "${SETS[@]}"
fp_status $? fetch || exit $?
fp_check fetch || exit $?
