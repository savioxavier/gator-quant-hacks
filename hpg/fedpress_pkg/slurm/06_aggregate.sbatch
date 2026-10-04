#!/bin/bash
# Step 6 (CPU): per-answer, per-meeting and trailing-window feature tables, then the panel files
# (<root>/panel/*.parquet: answers, meetings = 88-meeting calendar, windows, text_units, causal z-scores).
# Runs with --force by default (AGG_FORCE=1): it takes seconds and picks up any rerun of voice, face or text.
#SBATCH --job-name=fp-06-aggregate
#SBATCH --account=jie.xu
#SBATCH --qos=jie.xu
#SBATCH --partition=hpg-default
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16gb
#SBATCH --time=01:00:00
#SBATCH --output=fp-06-aggregate_%j.out
set -uo pipefail
_c="${FP_PKG:-$SLURM_SUBMIT_DIR}/slurm/common.sh"
[ -f "$_c" ] || { echo "cannot find $_c: run sbatch from the package folder (cd /blue/jie.xu/$USER/fed_presser_hpg)" >&2; exit 2; }
source "$_c"
fp_banner
fp_activate || exit 2
mapfile -t SETS < <(fp_sets)
SEL=(--all); [ -n "${SMOKE_ID:-}" ] && SEL=(--id "$SMOKE_ID")
FORCE=(); [ "${AGG_FORCE:-1}" = 1 ] && FORCE=(--force)
python -m fedpress.cli aggregate "${SEL[@]}" "${FORCE[@]}" --set compute.gpu_type=cpu "${SETS[@]}"
rc=$?
mkdir -p "$FEDPRESS_ROOT/panel"
python -m fedpress.cli status "${SEL[@]}" --set compute.gpu_type=cpu "${SETS[@]}" > "$FEDPRESS_ROOT/panel/status.txt" 2>&1 || true
python "$FP_PKG/slurm/status.py" ${SMOKE_ID:+--id "$SMOKE_ID"} "${SETS[@]}" > "$FEDPRESS_ROOT/panel/status_report.txt" 2>&1 || true
tail -n 25 "$FEDPRESS_ROOT/panel/status_report.txt"
fp_status $rc aggregate || exit $?
