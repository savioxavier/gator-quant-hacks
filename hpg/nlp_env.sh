#!/bin/bash
# Shared settings for the stance-model (nlp/chrono_stance.py) jobs. Source it, do not run it.
# Override any of these by exporting them before `bash hpg/submit_nlp.sh` (sbatch passes the environment on).
export USER="${USER:-$(id -un)}"
export NLP_GROUP="${NLP_GROUP:-ai-workshop}"
export NLP_BASE="${NLP_BASE:-/blue/$NLP_GROUP/$USER}"
export CHRONO_ENV="${CHRONO_ENV:-$NLP_BASE/envs/chrono}"          # conda env (python 3.12, torch cu128)
export CHRONO_ROOT="${CHRONO_ROOT:-$NLP_BASE/chrono}"             # labels, models, scores
export CHRONO_NLTK_DATA="${CHRONO_NLTK_DATA:-$CHRONO_ROOT/nltk_data}"
export HF_HOME="${HF_HOME:-$NLP_BASE/hf}"                          # Hugging Face cache on /blue, not /home
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$NLP_BASE/.cache/pip}"
export CONDA_PKGS_DIRS="${CONDA_PKGS_DIRS:-$NLP_BASE/.conda/pkgs}"  # conda package cache on /blue, not /home
export PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 TOKENIZERS_PARALLELISM=false
export PATH="$CHRONO_ENV/bin:$PATH"
mkdir -p "$CHRONO_ROOT" "$HF_HOME"
