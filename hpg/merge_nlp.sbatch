#!/bin/bash
#SBATCH --job-name=chrono_merge
#SBATCH --account=ai-workshop
#SBATCH --qos=ai-workshop
#SBATCH --partition=hpg-default
#SBATCH --cpus-per-task=2
#SBATCH --mem=8gb
#SBATCH --time=00:20:00
#SBATCH --output=nlp/logs/%x_%j.log
# CPU only: concatenate the per-year scores and build the press-conference H1 tables. Also copies the merged
# tables into data/text_corpus/chrono_scores/ of this clone. MERGE_YEARS=2015-2026 adds the optional 2015 year.
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
source hpg/nlp_env.sh
python nlp/chrono_stance.py merge ${MERGE_YEARS:+--years "$MERGE_YEARS"}
