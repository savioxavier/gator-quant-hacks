# Shared settings and helpers for the fedpress Slurm scripts. Sourced by submit_all.sh, rerun_failed.sh,
# 00_setup.sh and every *.sbatch; never run directly.
#
# Every setting is an environment variable with a default, so one command changes it for a whole run:
#   GPU_TYPE=rtx6000 bash slurm/submit_all.sh
# Group rule for jie.xu: never more than 2 GPUs at once. GPU arrays are throttled with %2 (MAX_GPUS), a
# single GPU job asks for at most 2, and fedpress itself refuses compute.max_gpus > 2.

# ---------------------------------------------------------------- locations
: "${FP_PKG:=${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}}"
[ -f "$FP_PKG/config.yaml" ] || FP_PKG=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
: "${FP_GROUP:=jie.xu}"
: "${FP_BLUE:=/blue/$FP_GROUP/$USER}"
: "${FP_ENV:=$FP_BLUE/envs/fedpress}"                 # conda env prefix (00_setup.sh env)
: "${FP_ENV_PYFEAT:=$FP_BLUE/envs/fedpress-pyfeat}"   # only for FACE_PRESET=pyfeat2|pyfeat5
: "${FEDPRESS_ROOT:=$FP_BLUE/fedpress}"               # data root: meetings/, panel/, logs/, cache/, models/
: "${FP_LOGDIR:=$FEDPRESS_ROOT/logs/slurm}"           # Slurm stdout/stderr, one file per job (array task)
export FP_PKG FP_ENV FP_ENV_PYFEAT FEDPRESS_ROOT FP_LOGDIR

# ---------------------------------------------------------------- accounts and queues
: "${ACCOUNT:=$FP_GROUP}"
: "${QOS_GPU:=$FP_GROUP}"             # there is no burst QOS for GPUs on HiPerGator
: "${QOS_CPU:=$FP_GROUP}"             # $FP_GROUP-b (burst: more cores, low priority, <= 4 days) is allowed here
: "${CPU_PARTITION:=hpg-default}"
: "${MAX_GPUS:=2}"                    # group rule; values above 2 are refused
: "${MAIL_USER:=}"                    # e.g. gatorlink@ufl.edu -> --mail-type=END,FAIL on every job

# ---------------------------------------------------------------- GPU type (the one fallback variable)
# b200 (default) | rtx6000 | l4 | a100. HiPerGator returned its A100s in June 2025: a100 needs PARTITION set to
# a partition that has them (e.g. on another cluster). Keep the per-GPU numbers in step with config.yaml
# compute.profiles; the job passes --set compute.gpu_type=$GPU_TYPE so fedpress uses the same profile.
: "${GPU_TYPE:=b200}"
fp_gpu_profile() {
  case "$GPU_TYPE" in
    b200)    _part=hpg-b200;    _gres=b200;         _cpg=14; _wpg=6; _speed=1.0 ;;
    rtx6000) _part=hpg-rtx6000; _gres=rtx-pro-6000; _cpg=16; _wpg=4; _speed=1.3 ;;
    l4)      _part=hpg-turin;   _gres=l4;           _cpg=4;  _wpg=2; _speed=3.0 ;;
    a100)    _part=;            _gres=a100;         _cpg=8;  _wpg=1; _speed=1.6 ;;
    *) echo "GPU_TYPE=$GPU_TYPE: use b200, rtx6000, l4 or a100" >&2; return 2 ;;
  esac
  GPU_PARTITION=${PARTITION:-$_part}
  GPU_GRES=${GRES_TYPE:-$_gres}
  WORKERS_PER_GPU=${WORKERS_PER_GPU:-$_wpg}
  CPUS_PER_GPU=${CPUS_PER_GPU:-$_cpg}
  MEM_PER_GPU_GB=${MEM_PER_GPU_GB:-$((16 + 12 * WORKERS_PER_GPU))}   # ~12 GB host RAM per worker process
  GPU_SPEED=${GPU_SPEED:-$_speed}       # wall-time multiplier relative to one B200 (time requests only)
  if [ -z "$GPU_PARTITION" ]; then
    echo "GPU_TYPE=$GPU_TYPE has no partition on HiPerGator (no A100s since 2025-06); set PARTITION=..." >&2
    return 2
  fi
  export GPU_TYPE GPU_PARTITION GPU_GRES WORKERS_PER_GPU CPUS_PER_GPU MEM_PER_GPU_GB GPU_SPEED
}

# ---------------------------------------------------------------- run layout
: "${GPU_LAYOUT:=array}"     # array: GPU_TASKS one-GPU array tasks, at most MAX_GPUS running (%N)
                             # job:   one job per GPU step holding GPUS (<= 2) GPUs, one shared claim queue
: "${GPU_TASKS:=2}"          # array tasks per GPU step; each takes a group of meetings (--shard i/N)
: "${GROUP_SIZE:=}"          # meetings per GPU array task; overrides GPU_TASKS (e.g. GROUP_SIZE=$WORKERS_PER_GPU)
: "${GPUS:=1}"               # GPU_LAYOUT=job only
: "${CPU_TASKS:=4}"          # array tasks for fetch and audio+frames (same N, so they chain with aftercorr)
: "${CPU_CPUS:=16}"          # cores per CPU task (must fit `showQos $QOS_CPU`)
: "${CPU_MEM_GB:=48}"
: "${CPU_WORKERS:=8}"        # fedpress worker processes per CPU task (shared claim queue inside the task)
: "${FACE_ON_CPU:=0}"        # 1: run the face step as a CPU job (face.device=cpu); frees the B200 queue
: "${FACE_PRESET:=default}"  # default (team plan: MediaPipe + EmotiEffLib, 1 fps) | pyfeat2 | pyfeat5 (plan_v0)
: "${TRAIN_WORKERS_PER_GPU:=6}"   # concurrent stance fine-tunes per GPU in the text step
: "${FP_SET:=}"              # extra config overrides for every stage: "face.fps=2 text.score=prob"
: "${FP_STRICT:=0}"          # 1: a meeting-level failure fails the job (and stops the afterok chain)
: "${FP_FORCE:=}"            # steps to redo even where done, e.g. "av face" after switching FACE_PRESET
export GPU_LAYOUT GPU_TASKS GROUP_SIZE GPUS CPU_TASKS CPU_WORKERS FACE_ON_CPU FACE_PRESET FP_SET FP_STRICT FP_FORCE \
  TRAIN_WORKERS_PER_GPU

# ---------------------------------------------------------------- helpers used inside jobs
fp_log() { printf '%s [%s] %s\n' "$(date -u +%FT%TZ)" "${SLURM_JOB_ID:-local}${SLURM_ARRAY_TASK_ID:+_$SLURM_ARRAY_TASK_ID}" "$*"; }

fp_activate() {  # fp_activate [env-prefix]
  local env=${1:-$FP_ENV}
  if [ ! -x "$env/bin/python" ]; then
    echo "conda env not found at $env; run: bash slurm/00_setup.sh env" >&2
    return 2
  fi
  # shellcheck source=/dev/null
  source "$FP_PKG/env/activate.sh" "$env"
  cd "$FP_PKG" || return 2
}

fp_sets() {  # the --set arguments shared by every fedpress call in this job
  local out=() kv
  [ -n "${FP_GPU_TYPE_SET:-}" ] && out+=(--set "compute.gpu_type=$FP_GPU_TYPE_SET")
  for kv in $FP_SET; do out+=(--set "$kv"); done
  printf '%s\n' "${out[@]}"
}

fp_face_sets() {  # face/frames overrides for FACE_PRESET (docs/FACE.md); one per line
  case "$FACE_PRESET" in
    default) ;;
    pyfeat2|pyfeat5)
      local f=${FACE_PRESET#pyfeat}
      printf '%s\n' --set "frames.fps=$f" --set frames.store=index --set "face.fps=$f" --set face.source=stream \
        --set face.pyfeat.enabled=true --set face.detector=pyfeat --set "face.expression=[pyfeat]" \
        --set face.emotiefflib.enabled=false ;;
    *) echo "FACE_PRESET=$FACE_PRESET: use default, pyfeat2 or pyfeat5" >&2; return 2 ;;
  esac
}

fp_selection() {  # meetings for this job: the whole sample, or this array task's group
  if [ -n "${SMOKE_ID:-}" ]; then
    printf '%s\n' --id "$SMOKE_ID"
  elif [ -n "${SLURM_ARRAY_TASK_ID:-}" ] && [ -n "${FP_NSHARDS:-}" ]; then
    printf '%s\n' --all --shard "${SLURM_ARRAY_TASK_ID}/${FP_NSHARDS}"
  else
    printf '%s\n' --all
  fi
}

fp_banner() {  # what this job is and where it runs
  fp_log "job=${SLURM_JOB_NAME:-local} host=$(hostname) partition=${SLURM_JOB_PARTITION:-} cpus=${SLURM_CPUS_PER_TASK:-} \
gpus=${CUDA_VISIBLE_DEVICES:-none} array=${SLURM_ARRAY_TASK_ID:-}/${FP_NSHARDS:-} root=$FEDPRESS_ROOT"
  if [ -n "${CUDA_VISIBLE_DEVICES:-}" ]; then
    local n
    n=$(echo "$CUDA_VISIBLE_DEVICES" | tr ',' '\n' | grep -c .)
    if [ "$n" -gt 2 ]; then
      fp_log "refusing to run: $n GPUs visible, the group limit is 2"; exit 2
    fi
    nvidia-smi --query-gpu=index,name,driver_version,compute_mode,memory.total,memory.used --format=csv 2>/dev/null || true
  fi
}

fp_status() {  # map a fedpress exit code to the job's exit code
  # 0 ok; 1 some meetings failed (recorded per meeting; the chain continues unless FP_STRICT=1); >= 2 fatal
  local rc=$1 what=$2
  if [ "$rc" -eq 0 ]; then
    fp_log "$what: ok"; return 0
  elif [ "$rc" -eq 1 ] && [ "$FP_STRICT" != 1 ]; then
    fp_log "$what: finished with meeting-level failures (see: python slurm/status.py --failed)"; return 0
  fi
  fp_log "$what: fatal (exit $rc)"; return "$rc"
}

fp_check() {  # fp_check <stage,...>: fail the job when every meeting of this task failed (a systemic error)
  python "$FP_PKG/slurm/status.py" --check "$1" $(fp_selection | grep -v -- '^--all$') $(fp_sets) \
    || { fp_log "systemic failure in $1: no meeting of this task finished it"; return 3; }
}

fp_force() {  # fp_force <step>: --force when the step is listed in FP_FORCE (the launcher clears markers once)
  [[ " $FP_FORCE " == *" $1 "* ]] && echo --force
  return 0
}

# ---------------------------------------------------------------- the GPU steps (shared by 03/04/05 and smoke)
fp_step_speech() {
  local sel; mapfile -t sel < <(fp_selection)
  local sets; mapfile -t sets < <(fp_sets)
  python -m fedpress.cli launch asr,turns,diarize,voice "${sel[@]}" --workers-per-gpu "$WORKERS_PER_GPU" $(fp_force speech) \
    ${MAX_SECONDS:+--max-seconds "$MAX_SECONDS"} "${sets[@]}"
  fp_status $? "speech (asr, turns, diarize, voice)" || return $?
  fp_check asr,turns
}

fp_step_face() {
  local sel; mapfile -t sel < <(fp_selection)
  local sets; mapfile -t sets < <(fp_sets; fp_face_sets)
  local wpg=$WORKERS_PER_GPU
  if [ "$FACE_ON_CPU" = 1 ]; then
    sets+=(--set compute.gpu_type=cpu --set face.device=cpu); wpg=$CPU_WORKERS
  fi
  python -m fedpress.cli launch face "${sel[@]}" --workers-per-gpu "$wpg" $(fp_force face) \
    ${MAX_SECONDS:+--max-seconds "$MAX_SECONDS"} "${sets[@]}"
  fp_status $? "face ($FACE_PRESET)" || return $?
}

fp_step_train() {  # walk-forward stance models (deviation D1); idempotent, shared O_EXCL claim queue
  local sets; mapfile -t sets < <(fp_sets)
  local years=(--all) wait_s=0 rc
  [ -n "${TRAIN_YEARS:-}" ] && years=(--years "$TRAIN_YEARS")
  while :; do
    python -m fedpress.train.stance_walkforward train "${years[@]}" --gpus "${SLURM_GPUS_ON_NODE:-1}" \
      --workers-per-gpu "$TRAIN_WORKERS_PER_GPU" "${sets[@]}"
    rc=$?
    if [ "$rc" -ne 0 ]; then  # a failed fine-tune would fail every meeting of its years: stop here
      fp_log "stance training failed (exit $rc): see $FEDPRESS_ROOT/logs/train/"; return 3
    fi
    # Another array task may still be training a model this task skipped as claimed: wait for it, so no
    # meeting is scored before its year's model exists (text.require_primary would fail it).
    local st; st=$(python -m fedpress.train.stance_walkforward status "${years[@]}" "${sets[@]}")
    if grep -q ' stale$' <<< "$st"; then  # finished models from other labels/settings are never overwritten silently
      fp_log "stance models trained with other labels or settings (the text stage would refuse them):"
      grep ' stale$' <<< "$st" | while read -r key _ seed _; do
        fp_log "  rm -rf $FEDPRESS_ROOT/models/stance_walkforward/$key/seed$seed"
      done
      fp_log "run those commands on a login node, then: bash slurm/submit_all.sh --from text"
      return 3
    fi
    if ! grep -q ' todo$' <<< "$st"; then
      fp_log "stance training: all models done"; return 0
    fi
    if [ "$wait_s" -ge "${TRAIN_WAIT_MAX_S:-1200}" ]; then  # keep well under the 1 h idle-GPU limit
      fp_log "stance training: models still missing after ${wait_s}s"; return 3
    fi
    sleep 30; wait_s=$((wait_s + 30))
  done
}

fp_step_text() {
  local sel; mapfile -t sel < <(fp_selection)
  local sets; mapfile -t sets < <(fp_sets)
  fp_step_train || return $?
  python -m fedpress.cli launch text "${sel[@]}" --workers-per-gpu "$WORKERS_PER_GPU" $(fp_force text) "${sets[@]}"
  fp_status $? "text" || return $?
  fp_check text
}
