#!/bin/bash
# Resubmit the chain from the earliest step that still has failed, blocked or unrun meetings.
# Every stage is idempotent: meetings already done are skipped in milliseconds, so only the failed ones (and
# everything downstream of them) run again.
#   bash slurm/rerun_failed.sh               # show failures, then submit_all.sh --from <earliest open step>
#   bash slurm/rerun_failed.sh --dry-run     # show what would be submitted
#   bash slurm/rerun_failed.sh --step face   # resubmit from this step instead
# A meeting that fails the same way twice needs a fix (config, input file), not a third try: read its log
# (path printed below) first. To redo meetings that finished but are wrong, run the stage with --force.
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
export FP_PKG=${FP_PKG:-$(cd "$HERE/.." && pwd)}
source "$HERE/common.sh"
STEP="" PASS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --step) STEP=$2; shift 2 ;;
    *) PASS+=("$1"); shift ;;
  esac
done
fp_activate >/dev/null || exit 2
mapfile -t SETS < <(fp_sets)
python "$FP_PKG/slurm/status.py" --failed "${SETS[@]}"
[ -n "$STEP" ] || STEP=$(python "$FP_PKG/slurm/status.py" --next "${SETS[@]}")
if [ "$STEP" = none ]; then
  echo "nothing to rerun: every stage is done (or not applicable) for every meeting"; exit 0
fi
echo "resubmitting from step: $STEP"
exec bash "$HERE/submit_all.sh" --from "$STEP" "${PASS[@]}"
