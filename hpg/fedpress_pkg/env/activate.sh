# Source before running fedpress (login shell, dev session or job script):
#   source env/activate.sh [/blue/jie.xu/$USER/envs/fedpress]
# Sets the data root, puts every cache on /blue, keeps the Hugging Face token in $HOME (never on /blue,
# which group members can read), and exposes the CUDA libraries of the pip wheels to CTranslate2/onnxruntime.
FEDPRESS_ENV=${1:-${FEDPRESS_ENV:-/blue/jie.xu/$USER/envs/fedpress}}
export FEDPRESS_ENV
export FEDPRESS_PKG=${FEDPRESS_PKG:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
export FEDPRESS_ROOT=${FEDPRESS_ROOT:-/blue/jie.xu/$USER/fedpress}
export PATH="$FEDPRESS_ENV/bin:$PATH"
export PYTHONNOUSERSITE=1

export HF_HOME=$FEDPRESS_ROOT/cache/huggingface
export HF_TOKEN_PATH=${HF_TOKEN_PATH:-$HOME/.cache/huggingface/token}
export TORCH_HOME=$FEDPRESS_ROOT/cache/torch
export CUDA_CACHE_PATH=$FEDPRESS_ROOT/cache/nv
export CUDA_CACHE_MAXSIZE=4294967296          # PTX JIT cache (onnxruntime / CTranslate2 on sm_100)
export PIP_CACHE_DIR=$FEDPRESS_ROOT/cache/pip
export UV_CACHE_DIR=$FEDPRESS_ROOT/cache/uv
export MPLCONFIGDIR=$FEDPRESS_ROOT/cache/matplotlib
export TOKENIZERS_PARALLELISM=false

if [ -x "$FEDPRESS_ENV/bin/python" ]; then
  _nv=$("$FEDPRESS_ENV/bin/python" -c 'import glob,os,site; print(":".join(sorted({d for sp in site.getsitepackages() for d in glob.glob(os.path.join(sp,"nvidia","*","lib"))})))' 2>/dev/null)
  [ -n "$_nv" ] && export LD_LIBRARY_PATH="$_nv${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  unset _nv
fi
mkdir -p "$FEDPRESS_ROOT/cache" "$FEDPRESS_ROOT/logs"
if [ -f "$HF_TOKEN_PATH" ]; then chmod 600 "$HF_TOKEN_PATH"; chmod 700 "$(dirname "$HF_TOKEN_PATH")"; fi
