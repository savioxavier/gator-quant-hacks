#!/bin/bash
# One-time setup on HiPerGator. Run the heavy parts in a dev session, never on a login node:
#   module load ufrc && srundev --time=04:00:00 --cpus-per-task=8 --mem=32gb
#   cd /blue/jie.xu/$USER/fed_presser_hpg
#   bash slurm/00_setup.sh all          # = env, models, check
#
# Subcommands (run in this order the first time; each is safe to repeat):
#   info       accounts, QOS limits, quota, internet (prints only; fine on a login node)
#   env        conda env on /blue from env/environment.yml + env/post_install.sh   (~20-40 min)
#   env-pyfeat the optional py-feat env (FACE_PRESET=pyfeat2|pyfeat5 only)
#   token      check the Hugging Face token file (location and mode; the value is never printed)
#   models     pre-download every enabled model at its pinned revision + the stance training labels (~15 GB)
#   check      CPU doctor in this session; then `sbatch slurm/gpu_check.sbatch` for the GPU side
#   fetch      download the meeting files from this session (only if compute nodes have no internet)
set -uo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
export FP_PKG=${FP_PKG:-$(cd "$HERE/.." && pwd)}
source "$HERE/common.sh"
cd "$FP_PKG" || exit 2

on_login() { [[ "$(hostname -s)" == login* ]] && [ -z "${SLURM_JOB_ID:-}" ]; }
need_compute() {
  if on_login && [ "${FP_ALLOW_LOGIN:-0}" != 1 ]; then
    echo "'$1' is heavy: start a dev session first (login nodes allow 4 cores / 32 GB / short tests):" >&2
    echo "  module load ufrc && srundev --time=04:00:00 --cpus-per-task=8 --mem=32gb" >&2
    exit 2
  fi
}
load_conda() {  # sets CONDA_TOOL; must run in this shell (not in $(...)), or the module's PATH change is lost
  type module >/dev/null 2>&1 || source /etc/profile >/dev/null 2>&1 || true
  module load conda >/dev/null 2>&1 || { echo "module load conda failed" >&2; exit 2; }
  if command -v mamba >/dev/null; then CONDA_TOOL=mamba; else CONDA_TOOL=conda; fi
  command -v "$CONDA_TOOL" >/dev/null || { echo "$CONDA_TOOL not on PATH after module load conda" >&2; exit 2; }
}

cmd_info() {
  echo "== identity and group (jie.xu must be listed; if it is a secondary group, jobs need --account/--qos=jie.xu)"
  id
  command -v showAssoc >/dev/null && showAssoc "$USER" || echo "(module load ufrc for showAssoc/showQos/slurmInfo)"
  echo "== QOS limits: GPU jobs count against $QOS_GPU (gres/gpu, cpu, mem shared by the whole group)"
  command -v showQos >/dev/null && { showQos "$QOS_GPU"; showQos "${FP_GROUP}-b"; } || true
  command -v slurmInfo >/dev/null && slurmInfo "$FP_GROUP" || true
  echo "== storage"
  command -v blue_quota >/dev/null && blue_quota || true
  echo "need about 60 GB for the 75 default videos (82 GB for all 95) + 25 GB frames + 20 GB models/env"
  echo "== outbound HTTPS from $(hostname -s)"
  for url in https://www.federalreserve.gov https://edge.api.brightcove.com https://huggingface.co; do
    printf '  %-36s %s\n' "$url" "$(curl -s -o /dev/null --max-time 15 -w '%{http_code}' "$url" || echo none)"
  done
  echo "== GPU partition defaults"; scontrol show partition "$( (fp_gpu_profile && echo "$GPU_PARTITION") 2>/dev/null || echo hpg-b200)" 2>/dev/null \
    | tr ' ' '\n' | grep -E 'DefMemPer|DefCpuPer|MaxTime|MaxMemPer' || true
}

make_env() {  # make_env <prefix> <yml>
  need_compute "env"
  local prefix=$1 yml=$2 tool
  load_conda
  tool=$CONDA_TOOL
  if [ -x "$prefix/bin/python" ] && [ "${FORCE:-0}" != 1 ]; then
    echo "env exists at $prefix (FORCE=1 rebuilds it)"
  else
    [ "${FORCE:-0}" = 1 ] && rm -rf "$prefix"
    mkdir -p "$(dirname "$prefix")" "$FEDPRESS_ROOT/cache/pip"
    export PIP_CACHE_DIR="$FEDPRESS_ROOT/cache/pip" TMPDIR=${TMPDIR:-/tmp}
    local yes=(); [ "$tool" = mamba ] && yes=(-y)   # older `conda env create` rejects -y (it never prompts)
    "$tool" env create "${yes[@]}" -p "$prefix" -f "$yml" || { echo "env create failed" >&2; exit 2; }
  fi
  bash "$FP_PKG/env/post_install.sh" "$prefix" || exit 2
}

cmd_token() {
  local p=${HF_TOKEN_PATH:-$HOME/.cache/huggingface/token}
  if [ -n "${HF_TOKEN:-}" ]; then echo "HF_TOKEN is set in the environment (it overrides the file)"; fi
  if [ -f "$p" ]; then
    chmod 700 "$(dirname "$p")"; chmod 600 "$p"
    [ -f "$(dirname "$p")/stored_tokens" ] && chmod 600 "$(dirname "$p")/stored_tokens"
    echo "token file: $p ($(stat -c '%A' "$p"), $(wc -c < "$p") bytes). Needed only for gated models:"
  else
    echo "no token file at $p. Needed only for gated models:"
  fi
  for f in "$FEDPRESS_ROOT/cache/huggingface/token" "$FEDPRESS_ROOT/cache/huggingface/stored_tokens"; do
    [ -f "$f" ] && echo "WARNING: $f is on /blue, which group members can read: delete it (rm $f)"
  done
  echo "  gtfintechlab/FOMC-RoBERTa (text cross-check, manual approval) and pyannote (diarize.pyannote, off by default)."
  echo "  Create one: huggingface.co -> Settings -> Access Tokens -> 'Read'. Then, in this session:"
  echo "    source env/activate.sh && hf auth login        # paste the token; it is written to $p"
  echo "    bash slurm/00_setup.sh token                   # fixes the file mode to 600"
}

cmd_models() {
  need_compute "models"
  fp_activate || exit 2
  mapfile -t SETS < <(fp_sets)
  python -m fedpress.cli prefetch-models "${SETS[@]}"
  local rc=$?
  [ "$rc" -ne 0 ] && echo "some models failed (gated FOMC-RoBERTa without approved access is expected; the text stage records it as unavailable)"
  python -m fedpress.train.stance_walkforward prepare "${SETS[@]}" | tail -n 5 || { echo "label download failed" >&2; exit 2; }
  if [ "$FACE_PRESET" != default ] && [ -x "$FP_ENV_PYFEAT/bin/python" ]; then
    mapfile -t FSETS < <(fp_face_sets)
    "$FP_ENV_PYFEAT/bin/python" -m fedpress.cli prefetch-models "${SETS[@]}" "${FSETS[@]}" || true
  fi
  du -sh "$FEDPRESS_ROOT/cache" 2>/dev/null || true
}

cmd_check() {
  fp_activate || exit 2
  mapfile -t SETS < <(fp_sets)
  # the dev session has no GPU: the cpu profile skips the CUDA checks (gpu_check.sbatch runs them on a B200)
  python -m fedpress.cli doctor --set compute.gpu_type=cpu "${SETS[@]}"
  python -m fedpress.cli list "${SETS[@]}" | tail -n 3
  echo "next: sbatch slurm/gpu_check.sbatch   (5 min on one B200: CUDA, CTranslate2, onnxruntime on sm_100)"
}

cmd_fetch() {
  need_compute "fetch"
  fp_activate || exit 2
  mapfile -t SETS < <(fp_sets)
  local sel=(--all); [ -n "${SMOKE_ID:-}" ] && sel=(--id "$SMOKE_ID")
  python -m fedpress.cli launch fetch "${sel[@]}" --set compute.gpu_type=cpu --workers-per-gpu "${FETCH_WORKERS:-4}" "${SETS[@]}"
}

case "${1:-}" in
  info) cmd_info ;;
  env) make_env "$FP_ENV" "$FP_PKG/env/environment.yml" ;;
  env-pyfeat) make_env "$FP_ENV_PYFEAT" "$FP_PKG/env/environment-pyfeat.yml" ;;
  token) cmd_token ;;
  models) cmd_models ;;
  check) cmd_check ;;
  fetch) cmd_fetch ;;
  all) make_env "$FP_ENV" "$FP_PKG/env/environment.yml" && cmd_token && cmd_models && cmd_check ;;
  *) sed -n '2,15p' "$0"; exit 2 ;;
esac
