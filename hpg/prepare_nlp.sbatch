#!/bin/bash
#SBATCH --job-name=chrono_prepare
#SBATCH --account=ai-workshop
#SBATCH --qos=ai-workshop
#SBATCH --partition=hpg-default
#SBATCH --cpus-per-task=4
#SBATCH --mem=16gb
#SBATCH --time=01:30:00
#SBATCH --output=nlp/logs/%x_%j.log
# CPU only: builds the env if it is missing, downloads the labels, verifies the label ids and caches the 11 base
# models (2014-2024, about 6.5 GB) and the Punkt data, so that no GPU job waits on the network.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
source hpg/nlp_env.sh
[ -x "$CHRONO_ENV/bin/python" ] || bash hpg/setup_nlp.sh
python nlp/chrono_stance.py prepare
