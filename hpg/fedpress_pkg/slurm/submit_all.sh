#!/bin/bash
# Submit the whole build as a chain of Slurm jobs (run on a login node from the package directory):
#
#   bash slurm/submit_all.sh                 # fetch -> audio+frames -> speech -> face -> text -> aggregate
#   bash slurm/submit_all.sh --dry-run       # print the sbatch commands, submit nothing
#   bash slurm/submit_all.sh --from speech   # resume at a step (earlier outputs are reused)
#   bash slurm/submit_all.sh --only face,agg # just these steps, chained in order
#   GPU_TYPE=rtx6000 bash slurm/submit_all.sh      # fallback GPU type (b200 | rtx6000 | l4 | a100 + PARTITION)
#   FACE_PRESET=pyfeat5 bash slurm/submit_all.sh --only face,agg   # plan_v0 face option (own env)
#
# Steps: fetch av speech face text agg. Dependencies: av task i waits for fetch task i (aftercorr, same grouping);
# every other step waits for the whole previous step (afterok). GPU steps run one after another, each as an
# array of one-GPU tasks throttled to %2 (or one job with GPUS <= 2 when GPU_LAYOUT=job): never more than 2 GPUs.
# A job exits 0 when only some meetings failed (they are recorded per meeting; see slurm/status.py), so one bad
# meeting does not stop the chain; a fatal error (environment, config, no network, every meeting failing) does.
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
export FP_PKG=${FP_PKG:-$(cd "$HERE/.." && pwd)}
# shellcheck source=common.sh
source "$HERE/common.sh"

ALL_STEPS=(fetch av speech face text agg)
FROM="" ONLY="" DRY=0 CONCURRENT=0
while [ $# -gt 0 ]; do
  case "$1" in
    --from) FROM=$2; shift 2 ;;
    --only) ONLY=$2; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    --allow-concurrent) CONCURRENT=1; shift ;;
    -h|--help) sed -n '2,17p' "$0"; exit 0 ;;
    *) echo "unknown option $1 (see --help)" >&2; exit 2 ;;
  esac
done

# ---------------------------------------------------------------- checks
fp_gpu_profile
case "$QOS_GPU" in *-b) echo "QOS_GPU=$QOS_GPU: there is no burst QOS for GPUs on HiPerGator; use $FP_GROUP" >&2; exit 2 ;; esac
if [ "$MAX_GPUS" -gt 2 ] || [ "$GPUS" -gt 2 ] || [ "$GPUS" -gt "$MAX_GPUS" ]; then
  echo "group rule: at most 2 GPUs at once (MAX_GPUS=$MAX_GPUS GPUS=$GPUS)" >&2; exit 2
fi
if [ "$DRY" = 0 ] && [ "$CONCURRENT" = 0 ] && command -v squeue >/dev/null; then
  running=$(squeue --me -h -o '%j' | grep -c '^fp-' || true)
  if [ "$running" -gt 0 ]; then
    echo "$running fp-* jobs are already queued or running (squeue --me). A second chain could push the group past" >&2
    echo "2 GPUs and would race on the same meetings. Wait, scancel them, or pass --allow-concurrent." >&2
    exit 2
  fi
fi
if command -v showQos >/dev/null; then  # best effort: a request above the group pool pends forever (QOSGrp*Limit)
  qos=$(showQos "$QOS_GPU" 2>/dev/null | grep -o 'cpu=[0-9]*\|gres/gpu=[0-9]*' | sort -u | tr '\n' ' ' || true)
  qcpu=$(grep -o 'cpu=[0-9]*' <<< "$qos" | head -1 | cut -d= -f2 || true)
  qgpu=$(grep -o 'gres/gpu=[0-9]*' <<< "$qos" | head -1 | cut -d= -f2 || true)
  want=$(( CPUS_PER_GPU * ($([ "$GPU_LAYOUT" = job ] && echo "$GPUS" || echo 1)) ))
  if [ -n "$qcpu" ] && [ "$qcpu" -gt 0 ] && [ "$want" -gt "$qcpu" ]; then
    echo "warning: a GPU task asks for $want cores but showQos $QOS_GPU allows cpu=$qcpu: lower CPUS_PER_GPU" >&2
  fi
  if [ -n "$qgpu" ] && [ "$qgpu" -eq 0 ]; then
    echo "warning: showQos $QOS_GPU lists gres/gpu=0: the group has no GPU allocation under this QOS" >&2
  fi
fi
STEPS=()
started=$([ -z "$FROM" ] && echo 1 || echo 0)
for s in "${ALL_STEPS[@]}"; do
  [ "$s" = "$FROM" ] && started=1
  if [ -n "$ONLY" ]; then [[ ",$ONLY," == *",$s,"* ]] && STEPS+=("$s"); elif [ "$started" = 1 ]; then STEPS+=("$s"); fi
done
[ ${#STEPS[@]} -gt 0 ] || { echo "no steps selected (--from $FROM --only $ONLY; steps: ${ALL_STEPS[*]})" >&2; exit 2; }

# sample size (honours FP_SET, e.g. sample.include_calibration=true for all 95 pressers)
if [ -x "$FP_ENV/bin/python" ]; then PY="$FP_ENV/bin/python"; else PY=python3; fi
mapfile -t SETS < <(fp_sets)
N=$(cd "$FP_PKG" && "$PY" -m fedpress.cli list "${SETS[@]}" 2>/dev/null | sed -n 's/.*sample = \([0-9]*\) pressers.*/\1/p' | tail -1)
[ -n "$N" ] || { echo "could not read the sample size: is the env built? (bash slurm/00_setup.sh env)" >&2; exit 2; }
if [ -n "$GROUP_SIZE" ]; then GPU_TASKS=$(( (N + GROUP_SIZE - 1) / GROUP_SIZE )); fi
[ "$GPU_TASKS" -ge 1 ] || GPU_TASKS=1
THROTTLE=$(( MAX_GPUS < 2 ? MAX_GPUS : 2 ))

# ---------------------------------------------------------------- wall-time requests
# Minutes = startup + per-meeting minutes x meetings per task x GPU_SPEED; the per-meeting figures are about
# 3x the local RTX 5090 measurements scaled to a B200 task with WORKERS_PER_GPU workers (README section 9).
hhmm() { local m=$1; [ "$m" -lt 30 ] && m=30; printf '%02d:%02d:00' $((m / 60)) $((m % 60)); }
per_task() { echo $(( ($1 + $2 - 1) / $2 )); }          # meetings per task
gpu_minutes() {  # gpu_minutes <startup> <centi-minutes per meeting> <tasks>
  awk -v s="$1" -v c="$2" -v n="$(per_task "$N" "$3")" -v f="$GPU_SPEED" 'BEGIN { printf "%d", s + c / 100 * n * f + 0.5 }'
}
GT=$([ "$GPU_LAYOUT" = job ] && echo 1 || echo "$GPU_TASKS")
GSCALE=$([ "$GPU_LAYOUT" = job ] && echo "$GPUS" || echo 1)
case "$FACE_PRESET" in pyfeat2) FACE_C=150 ;; pyfeat5) FACE_C=320 ;; *) FACE_C=40 ;; esac
[ "$FACE_ON_CPU" = 1 ] && FACE_C=$((FACE_C * 2))
T_FETCH=${TIME_FETCH:-$(hhmm $(( 20 + 3 * $(per_task "$N" "$CPU_TASKS") )))}
T_AV=${TIME_AV:-$(hhmm $(( 15 + 2 * $(per_task "$N" "$CPU_TASKS") )))}
T_SPEECH=${TIME_SPEECH:-$(hhmm $(( $(gpu_minutes 20 40 "$GT") / GSCALE + 10 )))}
T_FACE=${TIME_FACE:-$(hhmm $(( $(gpu_minutes 20 "$FACE_C" "$GT") / GSCALE + 10 )))}
T_TEXT=${TIME_TEXT:-$(hhmm $(( 45 + $(gpu_minutes 10 15 "$GT") / GSCALE )))}
T_AGG=${TIME_AGG:-01:00:00}

# ---------------------------------------------------------------- submission
mkdir -p "$FP_LOGDIR"
STAMP=$(date +%Y%m%dT%H%M%S)
RECORD="$FP_LOGDIR/submit_$STAMP.tsv"
[ "$DRY" = 1 ] && RECORD=/dev/null
printf 'step\tjob_id\tarray\tdependency\tpartition\ttime\n' > "$RECORD"
MAIL=(); [ -n "$MAIL_USER" ] && MAIL=(--mail-type=END,FAIL --mail-user="$MAIL_USER")
fake=1000
PREV="" PREV_STEP=""

submit() {  # submit <step> <script> <array-spec|-> <shards|-> <dependency|-> <sbatch options...>
  local step=$1 script=$2 arr=$3 shards=$4 dep=$5; shift 5
  local out="$FP_LOGDIR/%x_%j.out" opts=()
  [ "$arr" != - ] && { out="$FP_LOGDIR/%x_%A_%a.out"; opts+=(--array="$arr"); }
  [ "$dep" != - ] && opts+=(--dependency="$dep" --kill-on-invalid-dep=yes)
  opts+=(--account="$ACCOUNT" --output="$out" --export=ALL "${MAIL[@]}" "$@")
  local cmd=(sbatch --parsable "${opts[@]}" "$FP_PKG/slurm/$script")
  local jid
  if [ "$DRY" = 1 ]; then
    fake=$((fake + 1)); jid=$fake
    echo "[dry-run] FP_NSHARDS=${shards/-/} ${cmd[*]}"
  else
    jid=$(cd "$FP_PKG" && FP_NSHARDS=${shards/-/} "${cmd[@]}" | cut -d';' -f1)
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$step" "$jid" "$arr" "$dep" "$(printf '%s ' "$@" | grep -o 'partition=[^ ]*' || true)" \
    "$(printf '%s ' "$@" | grep -o 'time=[^ ]*' || true)" | tee -a "$RECORD" >/dev/null
  printf '  %-7s job %-10s array=%-8s dep=%s\n' "$step" "$jid" "$arr" "$dep"
  PREV=$jid PREV_STEP=$step
}

gpu_opts() {  # partition, GPUs, cores and memory for one GPU-step job or array task
  local g=$([ "$GPU_LAYOUT" = job ] && echo "$GPUS" || echo 1)
  echo "--partition=$GPU_PARTITION --qos=$QOS_GPU --gres=gpu:$GPU_GRES:$g --nodes=1 --ntasks=1" \
       "--cpus-per-task=$((CPUS_PER_GPU * g)) --mem=$((MEM_PER_GPU_GB * g))gb"
}
cpu_opts() { echo "--partition=$CPU_PARTITION --qos=$QOS_CPU --nodes=1 --ntasks=1 --cpus-per-task=$1 --mem=$2gb"; }
gpu_array() { [ "$GPU_LAYOUT" = job ] && echo - || echo "0-$((GPU_TASKS - 1))%$THROTTLE"; }
gpu_shards() { [ "$GPU_LAYOUT" = job ] && echo - || echo "$GPU_TASKS"; }
dep_after() {  # dependency on the previous submitted step
  [ -z "$PREV" ] && { echo -; return; }
  if [ "$1" = av ] && [ "$PREV_STEP" = fetch ]; then echo "aftercorr:$PREV"; else echo "afterok:$PREV"; fi
}

echo "fedpress chain: $N meetings, GPU_TYPE=$GPU_TYPE ($GPU_PARTITION, gres gpu:$GPU_GRES), layout=$GPU_LAYOUT," \
     "GPU tasks=$GT x $([ "$GPU_LAYOUT" = job ] && echo "$GPUS" || echo 1) GPU (max $THROTTLE at once)," \
     "workers/GPU=$WORKERS_PER_GPU, face=$FACE_PRESET$([ "$FACE_ON_CPU" = 1 ] && echo ' on CPU'), root=$FEDPRESS_ROOT"
for s in "${STEPS[@]}"; do
  case "$s" in
    fetch)  # shellcheck disable=SC2046
            submit fetch 01_fetch.sbatch "0-$((CPU_TASKS - 1))" "$CPU_TASKS" "$(dep_after fetch)" \
              $(cpu_opts 4 8) --time="$T_FETCH" ;;
    av)     # shellcheck disable=SC2046
            submit av 02_audio_frames.sbatch "0-$((CPU_TASKS - 1))" "$CPU_TASKS" "$(dep_after av)" \
              $(cpu_opts "$CPU_CPUS" "$CPU_MEM_GB") --time="$T_AV" ;;
    speech) # shellcheck disable=SC2046
            submit speech 03_speech.sbatch "$(gpu_array)" "$(gpu_shards)" "$(dep_after speech)" \
              $(gpu_opts) --time="$T_SPEECH" ;;
    face)   if [ "$FACE_ON_CPU" = 1 ]; then  # shellcheck disable=SC2046
              submit face 04_face.sbatch "0-$((CPU_TASKS - 1))" "$CPU_TASKS" "$(dep_after face)" \
                $(cpu_opts "$CPU_CPUS" "$CPU_MEM_GB") --time="$T_FACE"
            else  # shellcheck disable=SC2046
              submit face 04_face.sbatch "$(gpu_array)" "$(gpu_shards)" "$(dep_after face)" $(gpu_opts) --time="$T_FACE"
            fi ;;
    text)   # shellcheck disable=SC2046
            submit text 05_text.sbatch "$(gpu_array)" "$(gpu_shards)" "$(dep_after text)" $(gpu_opts) --time="$T_TEXT" ;;
    agg)    # shellcheck disable=SC2046
            submit agg 06_aggregate.sbatch - - "$(dep_after agg)" $(cpu_opts 2 16) --time="$T_AGG" ;;
  esac
done
[ "$DRY" = 1 ] || echo "recorded in $RECORD; monitor: squeue --me; python slurm/status.py; logs: $FP_LOGDIR"
