#!/bin/bash
# One-time: build the conda env for the stance model on /blue (re-running it is harmless).
# Run it inside a job, not on a login node. From the repo root:
#   srun --account=ai-workshop --qos=ai-workshop --partition=hpg-default --cpus-per-task=4 --mem=16gb \
#        --time=01:00:00 bash hpg/setup_nlp.sh
# hpg/submit_nlp.sh also runs it from the CPU prepare job when the env does not exist yet.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/nlp_env.sh"
# A batch job's bash child may not have the Lmod `module` function; load it from Lmod's own init if so.
if ! type module >/dev/null 2>&1 && [ -n "${LMOD_PKG:-}" ] && [ -f "$LMOD_PKG/init/bash" ]; then
    source "$LMOD_PKG/init/bash"
fi
set +u  # module scripts may read unset variables
module load conda
set -u
if [ ! -x "$CHRONO_ENV/bin/python" ]; then
    conda create -y -p "$CHRONO_ENV" -c conda-forge --override-channels python=3.12 pip
fi
PY="$CHRONO_ENV/bin/python"
"$PY" -m pip install --upgrade pip
# CUDA 12.8 build: runs on the Blackwell RTX PRO 6000 (sm_120) and B200 (sm_100) nodes. Same versions as the
# local RTX 5090 venv the smoke test ran on.
"$PY" -m pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128
"$PY" -m pip install transformers==5.18.0 tokenizers==0.23.2 huggingface_hub==1.33.0 safetensors==0.8.0 \
    pandas==3.0.6 pyarrow==25.0.1 numpy==2.5.3 nltk==3.10.3
# datasets is optional (chrono_stance.py reads the label CSVs through huggingface_hub). It is installed under the
# pins above so it cannot change them, and a failure here does not stop the setup.
"$PY" -m pip freeze | grep -i -E '^(torch|transformers|tokenizers|huggingface.hub|safetensors|pandas|pyarrow|numpy|nltk)==' \
    > "$CHRONO_ENV/chrono_pins.txt"
"$PY" -m pip install datasets -c "$CHRONO_ENV/chrono_pins.txt" || echo "note: datasets not installed (optional)"
"$PY" -c "import torch, transformers, nltk; print('torch', torch.__version__, 'cuda build', torch.version.cuda, '| transformers', transformers.__version__, '| nltk', nltk.__version__)"
mkdir -p "$CHRONO_NLTK_DATA"
"$PY" -c "import nltk, os; nltk.download('punkt_tab', download_dir=os.environ['CHRONO_NLTK_DATA'], quiet=True)"
echo "env ready: $CHRONO_ENV (punkt_tab in $CHRONO_NLTK_DATA)"
