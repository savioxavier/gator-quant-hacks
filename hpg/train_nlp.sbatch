#!/bin/bash
#SBATCH --job-name=chrono_train
#SBATCH --account=ai-workshop
#SBATCH --qos=ai-workshop
#SBATCH --partition=hpg-rtx6000
#SBATCH --gres=gpu:rtx-pro-6000:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32gb
#SBATCH --time=01:00:00
#SBATCH --array=0-32%4
#SBATCH --output=nlp/logs/%x_%A_%a.log
# One (year, seed) fine-tune per array task: task i -> year YEAR0 + i/3 (YEAR0 = 2016), seed 42/43/44 by i%3.
# 11 years x 3 seeds = 33 tasks, at most 4 GPUs at once. Expected 1.5-3 minutes per task.
# B200 instead (long queue): sbatch --partition=hpg-b200 --gres=gpu:b200:1 hpg/train_nlp.sbatch
# A finished model is skipped, so resubmitting only redoes missing or failed tasks.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
source hpg/nlp_env.sh
export HF_HUB_OFFLINE=1
YEAR0="${YEAR0:-2016}"
SEEDS=(42 43 44)
TASK="${SLURM_ARRAY_TASK_ID:-0}"
YEAR=$((YEAR0 + TASK / 3))
SEED=${SEEDS[$((TASK % 3))]}
echo "task $TASK -> year $YEAR seed $SEED on $(hostname)"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
python -c "import torch; assert torch.cuda.is_available(), 'no CUDA'; print(torch.__version__, torch.cuda.get_device_name(0))"
python nlp/chrono_stance.py train --year "$YEAR" --seed "$SEED"
