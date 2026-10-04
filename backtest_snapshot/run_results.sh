#!/usr/bin/env bash
# Chrono stance scores -> fedspeak_v2 backtest + press-conference H1 backtest -> combined summary.
#
#   bash run_results.sh            real run: needs the finished chrono run in chrono/full
#   bash run_results.sh --placebo  the same chain on PLACEBO scores under placebo_chain/ (never touches real outputs,
#                                  never evaluates the v2 out-of-sample period)
#
# Steps: 1 check the chrono run finished (36 models, 12 years scored, run.log ends cleanly)
#        2 chrono_stance.py merge --no-publish
#        3 adapters (v2 doc_scores.parquet; press-conference answers/meetings with stance columns)
#        4 v2 backtest per HYPOTHESIS_v2 (selection, validation, OOS once only if the rule passes, portfolio, chair)
#        5 press-conference backtest (presser_bt/backtest/code/run_all.sh)
#        6 summary.json + summary.md
# Git Bash compatible. Stops at the first failing step.
# Rerun after a completed real v2 run: step 3 keeps doc_scores.parquet only if it is unchanged, step 4 is skipped
# (its out-of-sample record exists; the OOS is never recomputed) and steps 5-6 run again.
set -euo pipefail

SCR="${WORK_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
CHRONO_PY="${CHRONO_PY:-python}"
GQH_PY="${GQH_PY:-python}"
REPO="${GQH_REPO:?set GQH_REPO to a clone of github.com/minh-stakc/gqh-flow-clock}"
WIRE="$SCR/wire"
export PYTHONIOENCODING=utf-8
export GQH_DATA_DIR="${GQH_DATA_DIR:?set GQH_DATA_DIR to the gqh data cache}"
unset GQH_OOS_UNLOCK || true

MODE=real
if [ "${1:-}" = "--placebo" ]; then MODE=placebo; fi

if [ "$MODE" = placebo ]; then
  BASE="$SCR/placebo_chain"
  ROOT="$BASE/chrono"
  V2_SCORES="$BASE/v2_score/doc_scores.parquet"
  V2_OUT="$BASE/v2_out"
  P_TEXT="$BASE/presser_text"
  P_OUT="$BASE/presser_out"
  RES="$BASE/results_final"
  PFLAG="--placebo"
  # remove only this chain's own outputs (keeps e.g. placebo_chain/oos_codepath_test)
  for d in chrono v2_score v2_out presser_text presser_out results_final; do rm -rf "${BASE:?}/$d"; done
  mkdir -p "$BASE"
  echo "PLACEBO chain test: random stance scores, not results." > "$BASE/PLACEBO_README.txt"
  echo "== 0  build placebo chrono outputs"
  ( cd "$WIRE" && "$CHRONO_PY" make_placebo.py --root "$ROOT" )
else
  ROOT="$SCR/chrono/full"
  V2_SCORES="$SCR/fedspeak_v2/score/doc_scores.parquet"
  V2_OUT="$SCR/fedspeak_v2/backtest"
  P_TEXT="$SCR/presser_bt/text_chrono"
  P_OUT="$SCR/presser_bt/backtest"
  RES="$SCR/results_final"
  PFLAG=""
  # DEVIATIONS.md (D-1, D-2) must exist before any return on real scores is computed
  DEV="$SCR/fedspeak_v2/DEVIATIONS.md"
  if [ ! -f "$DEV" ] || ! grep -q "^## D-1" "$DEV" || ! grep -q "^## D-2" "$DEV"; then
    echo "refusing: $DEV with entries D-1 and D-2 must exist before the real run"; exit 1
  fi
fi
V2_DONE=0
if [ "$MODE" = real ] && { [ -f "$V2_OUT/oos_chosen.json" ] || [ -f "$V2_OUT/oos_not_evaluated.json" ]; }; then
  V2_DONE=1
  echo "note: the v2 run in $V2_OUT is already complete; it will not be recomputed"
fi

echo "== 1  chrono run complete?"
( cd "$WIRE" && "$CHRONO_PY" check_chrono.py --root "$ROOT" $PFLAG )

echo "== 2  merge (--no-publish)"
"$CHRONO_PY" "$SCR/../nlp/chrono_stance.py" --root "$ROOT" merge --years 2015-2026 --no-publish > "$ROOT/merge_stdout.log"
tail -n 3 "$ROOT/merge_stdout.log"

echo "== 3  adapters"
KEEP=""; if [ "$V2_DONE" = 1 ]; then KEEP="--keep-if-equal"; fi
( cd "$WIRE" && "$GQH_PY" adapt_v2.py --chrono-root "$ROOT" --out "$V2_SCORES" $PFLAG $KEEP )
( cd "$WIRE" && "$GQH_PY" adapt_presser.py --chrono-root "$ROOT" --text-out "$P_TEXT" $PFLAG )

echo "== 4  fedspeak_v2 backtest"
SKIP=""; if [ "$V2_DONE" = 1 ]; then SKIP="--skip-if-complete"; fi
( cd "$REPO" && "$GQH_PY" "$WIRE/run_v2_chrono.py" --doc-scores "$V2_SCORES" --out "$V2_OUT" $PFLAG $SKIP )

echo "== 5  press-conference H1 backtest"
if [ "$MODE" = real ]; then
  # keep the pre-chrono outputs (BENCH-R and the lexicon control, no stance scores) before run_all.sh rewrites them
  SNAP="$SCR/presser_bt/backtest_prechrono"
  if [ ! -d "$SNAP" ]; then
    mkdir -p "$SNAP"
    for d in positions qa results tables; do cp -r "$P_OUT/$d" "$SNAP/"; done
    cp "$P_OUT/manifest_sha256.txt" "$SNAP/"
  fi
fi
mkdir -p "$P_OUT"
PRESSER_TEXT_DIR="$P_TEXT" PRESSER_OUT_DIR="$P_OUT" sh "$SCR/presser_bt/backtest/code/run_all.sh" > "$P_OUT/run_all_stdout.log" 2>&1 || {
  echo "run_all.sh failed; tail of $P_OUT/run_all_stdout.log:"; tail -n 30 "$P_OUT/run_all_stdout.log"; exit 1; }
tail -n 3 "$P_OUT/run_all_stdout.log"

echo "== 6  combined summary"
( cd "$WIRE" && "$GQH_PY" summarize.py --chrono-root "$ROOT" --v2-scores "$V2_SCORES" --v2-out "$V2_OUT" \
    --presser-text "$P_TEXT" --presser-out "$P_OUT" --out-dir "$RES" $PFLAG )
echo "done ($MODE): $RES/summary.md"
