#!/usr/bin/env bash
# Fix-ups that a pip requirements list cannot express, then install fedpress and freeze the environment.
#   bash env/post_install.sh /blue/jie.xu/$USER/envs/fedpress            (main env)
#   bash env/post_install.sh /blue/jie.xu/$USER/envs/fedpress-pyfeat     (py-feat env)
# 1. One onnxruntime: faster-whisper, emotiefflib and insightface depend on the CPU package, whose
#    `onnxruntime` module would shadow the GPU build. Keep only onnxruntime-gpu 1.26.0 (CUDA 12.8 build with
#    compute_90 PTX, which the driver JIT-compiles for sm_100; later CUDA 12.8 builds have no sm_100 code).
# 2. One OpenCV: mediapipe wants opencv-contrib-python, others opencv-python; they overwrite each other's cv2.
set -euo pipefail
PREFIX=${1:?usage: post_install.sh <env-prefix>}
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PY="$PREFIX/bin/python"
ORT_VERSION=${ORT_VERSION:-1.26.0}
CV_VERSION=${CV_VERSION:-4.12.0.88}

"$PY" -m pip uninstall -y onnxruntime onnxruntime-gpu opencv-python opencv-python-headless opencv-contrib-python \
  opencv-contrib-python-headless || true
"$PY" -m pip install --no-deps "onnxruntime-gpu==${ORT_VERSION}" "opencv-contrib-python-headless==${CV_VERSION}"
"$PY" -m pip install --no-deps -e "$HERE/.."
"$PY" -m pip check || echo "pip check reported conflicts (see above); run 'python -m fedpress.cli doctor'"

name=$(basename "$PREFIX")
"$PY" -m pip freeze --exclude-editable > "$HERE/requirements-lock-${name}-linux.txt"
echo "wrote $HERE/requirements-lock-${name}-linux.txt"

"$PY" - <<'EOF'
import cv2, onnxruntime as ort, torch
print("torch", torch.__version__, "cuda", torch.version.cuda, "archs", torch.cuda.get_arch_list())
print("onnxruntime", ort.__version__, ort.get_available_providers())
print("opencv", cv2.__version__)
EOF
