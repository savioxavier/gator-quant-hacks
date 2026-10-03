#!/bin/bash
# Smoke test: ONE meeting through every stage on ONE GPU (default 2025-09-17, Powell, 52 min).
#   sbatch slurm/smoke.sbatch                                  # MAX_SECONDS=120 (frames/face cut at 120 s)
#   SMOKE_ID=20200303 MAX_SECONDS= sbatch slurm/smoke.sbatch   # a whole (14-min) meeting, for timings
#   GPU_TYPE=rtx6000 sbatch --partition=hpg-rtx6000 --gres=gpu:rtx-pro-6000:1 slurm/smoke.sbatch   # other GPU type
# MAX_SECONDS limits only frames and face (the opening alone runs 3-8 min, so 120 s checks face enrolment but
# yields no answer frames; MAX_SECONDS=900 or empty gives answer-level face rows). Speech, text and aggregate
# always process the whole meeting. Outputs are the real ones: the full run reuses them, redoes the cut
# frames/face outputs, and re-aggregates (06 runs with --force). The year's 3 stance models trained here are
# the real fine-tunes, reused by step 5. Downloads (fetch) happen here when missing: needs outbound HTTPS.
#SBATCH --job-name=fp-smoke
#SBATCH --account=jie.xu
#SBATCH --qos=jie.xu
#SBATCH --partition=hpg-b200
#SBATCH --gres=gpu:b200:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64gb
#SBATCH --time=01:30:00
#SBATCH --output=fp-smoke_%j.out
set -uo pipefail
export SMOKE_ID=${SMOKE_ID:-20250917}
export MAX_SECONDS=${MAX_SECONDS-120}
_c="${FP_PKG:-$SLURM_SUBMIT_DIR}/slurm/common.sh"
[ -f "$_c" ] || { echo "cannot find $_c: run sbatch from the package folder (cd /blue/jie.xu/$USER/fed_presser_hpg)" >&2; exit 2; }
source "$_c"
PARTITION=${PARTITION:-${SLURM_JOB_PARTITION:-}} fp_gpu_profile || exit 2
export FP_GPU_TYPE_SET=$GPU_TYPE WORKERS_PER_GPU=1 TRAIN_WORKERS_PER_GPU=3
export TRAIN_YEARS=${TRAIN_YEARS:-${SMOKE_ID:0:4}}
fp_banner
fp_activate || exit 2
mapfile -t SETS < <(fp_sets)
t0=$(date +%s)
python -m fedpress.cli fetch --id "$SMOKE_ID" "${SETS[@]}" || exit 4
python -m fedpress.cli audio --id "$SMOKE_ID" "${SETS[@]}" || exit 1
python -m fedpress.cli frames --id "$SMOKE_ID" ${MAX_SECONDS:+--max-seconds "$MAX_SECONDS"} "${SETS[@]}" || exit 1
fp_step_speech || exit $?
fp_step_face || exit $?
fp_step_text || exit $?
python -m fedpress.cli aggregate --id "$SMOKE_ID" --force "${SETS[@]}"
fp_log "smoke finished in $(( $(date +%s) - t0 )) s"
python "$FP_PKG/slurm/status.py" --id "$SMOKE_ID" "${SETS[@]}"
python - "$SMOKE_ID" <<'PY'
import json, os, sys
from pathlib import Path
d = Path(os.environ["FEDPRESS_ROOT"]) / "meetings" / sys.argv[1] / "_done"
print(f"{'stage':<10} {'status':<15} {'elapsed_s':>9}  notes")
for s in ("fetch", "audio", "frames", "asr", "turns", "diarize", "voice", "face", "text", "aggregate"):
    p = d / f"{s}.json"
    if not p.exists():
        print(f"{s:<10} {'FAILED' if (d / f'{s}.failed.json').exists() else 'missing':<15}"); continue
    j = json.loads(p.read_text())
    n = {k: v for k, v in (j.get("notes") or {}).items() if k in ("rtf", "wer_proxy", "match_frac", "timing_ok",
         "answer_verified_frac", "n_chunks", "frames_feature", "frames_per_s", "n_sentences", "hawk_statement", "h1_gap")}
    print(f"{s:<10} {j.get('status'):<15} {j.get('elapsed_s') or 0:>9.1f}  {json.dumps(n)}  {(j.get('device') or {}).get('gpu') or ''}")
PY
