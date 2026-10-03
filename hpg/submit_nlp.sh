#!/bin/bash
# Train and score everything in one go: prepare (CPU) -> 36 fine-tunes (GPU array, 4 at a time)
# -> 12 scoring tasks (GPU array) -> merge (CPU), chained with --dependency=afterok.
# Years 2015-2026 by default (2015 scores the v2 warm-up documents, per the clarification to Amendment 2 of
# research/fedspeak_v2/HYPOTHESIS_v2.md); YEAR0=2016 runs only the test years 2016-2026.
# Run it from anywhere inside the clone:   bash hpg/submit_nlp.sh
# Options (environment variables):
#   GPU_PROFILE=rtx6000   default: --partition=hpg-rtx6000 --gres=gpu:rtx-pro-6000:1
#   GPU_PROFILE=b200      --partition=hpg-b200 --gres=gpu:b200:1 (long queue)
#   CONC=4                GPUs at once in each array
#   CHRONO_LABEL_YEAR=true|dataset|redated   which date decides the labelled rows of model Y (default true: the
#                         source document's date from data/text_corpus/label_dates.parquet, per fedspeak v2
#                         Amendment 3 / D1a; see nlp/README.md "Label years"). Passed to every job.
#   CHRONO_ROOT, HF_HOME, CHRONO_ENV, NLP_GROUP   see hpg/nlp_env.sh
set -euo pipefail
export USER="${USER:-$(id -un)}"
cd "$(dirname "${BASH_SOURCE[0]}")/.."
case "${GPU_PROFILE:-rtx6000}" in
    rtx6000) GPU_ARGS=(--partition=hpg-rtx6000 --gres=gpu:rtx-pro-6000:1) ;;
    b200)    GPU_ARGS=(--partition=hpg-b200 --gres=gpu:b200:1) ;;
    *) echo "GPU_PROFILE must be rtx6000 or b200" >&2; exit 1 ;;
esac
CONC="${CONC:-4}"
export YEAR0="${YEAR0:-2015}"              # first scored year; the last is 2026
case "$YEAR0" in
    2015|2016|2017|2018|2019|2020|2021|2022|2023|2024|2025|2026) ;;
    *) echo "YEAR0 must be a year from 2015 to 2026" >&2; exit 1 ;;
esac
NY=$(( 2026 - YEAR0 + 1 ))
export MERGE_YEARS="${YEAR0}-2026"
export CHRONO_LABEL_YEAR="${CHRONO_LABEL_YEAR:-true}"
case "$CHRONO_LABEL_YEAR" in
    true|dataset|redated) ;;
    *) echo "CHRONO_LABEL_YEAR must be true, dataset or redated" >&2; exit 1 ;;
esac
mkdir -p nlp/logs
for f in data/text_corpus/docs_to_score.parquet data/text_corpus/label_dates.parquet; do
    if [ ! -f "$f" ]; then
        echo "$f is missing (pull the branch first)" >&2
        exit 1
    fi
done
# Submit one job and print its id; fail (non-zero) if sbatch fails or returns no job id. A command substitution does
# not inherit `set -e`, so the checks are explicit and every call site stops the chain on failure.
jid() {
    local out
    out=$(sbatch --parsable --kill-on-invalid-dep=yes "$@") || { echo "sbatch failed: sbatch $*" >&2; return 1; }
    out="${out%%;*}"
    [[ "$out" =~ ^[0-9]+$ ]] || { echo "sbatch returned no job id for: sbatch $*" >&2; return 1; }
    echo "$out"
}
stop() { echo "stopped; cancel the jobs already queued with: scancel $*" >&2; exit 1; }
P=$(jid hpg/prepare_nlp.sbatch) || exit 1
T=$(jid --dependency=afterok:"$P" "${GPU_ARGS[@]}" --array=0-$(( 3 * NY - 1 ))%"$CONC" hpg/train_nlp.sbatch) || stop "$P"
S=$(jid --dependency=afterok:"$T" "${GPU_ARGS[@]}" --array=0-$(( NY - 1 ))%"$CONC" hpg/score_nlp.sbatch) || stop "$P" "$T"
M=$(jid --dependency=afterok:"$S" hpg/merge_nlp.sbatch) || stop "$P" "$T" "$S"
echo "label-year rule: $CHRONO_LABEL_YEAR"
echo "years $MERGE_YEARS: prepare $P -> train $T ($(( 3 * NY )) tasks, $CONC at a time) -> score $S ($NY tasks) -> merge $M"
echo "watch:   squeue -u $USER        logs: nlp/logs/"
echo "results: ${CHRONO_ROOT:-/blue/${NLP_GROUP:-ai-workshop}/$USER/chrono}/scores and data/text_corpus/chrono_scores/"
