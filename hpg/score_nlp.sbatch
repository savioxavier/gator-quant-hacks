#!/bin/bash
#SBATCH --job-name=chrono_score
#SBATCH --account=ai-workshop
#SBATCH --qos=ai-workshop
#SBATCH --partition=hpg-rtx6000
#SBATCH --gres=gpu:rtx-pro-6000:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32gb
#SBATCH --time=00:30:00
#SBATCH --array=0-10%4
#SBATCH --output=nlp/logs/%x_%A_%a.log
# Score every document dated in year YEAR0 + i (YEAR0 = 2016) with the 3 seed models of that year
# (about 1 minute per year). B200 instead: sbatch --partition=hpg-b200 --gres=gpu:b200:1 hpg/score_nlp.sbatch
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
source hpg/nlp_env.sh
export HF_HUB_OFFLINE=1
YEAR=$(( ${YEAR0:-2016} + ${SLURM_ARRAY_TASK_ID:-0} ))
echo "score year $YEAR on $(hostname)"
python nlp/chrono_stance.py score --year "$YEAR"
