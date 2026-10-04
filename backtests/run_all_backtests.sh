#!/usr/bin/env bash
# One command for every backtest in this folder (see README.md).
#
#   bash backtests/run_all_backtests.sh [all | chrono | v2 | presser | h234]      (default: all)
#
# Steps
#   chrono   only if CHRONO_ROOT is set: check the chrono run, rebuild the v2 document scores and the
#            press-conference text label from it into $BACKTEST_RERUN_DIR/chrono_inputs, and compare them with the
#            committed frozen inputs (v2/score/doc_scores.parquet, presser/text_chrono/). The committed inputs are
#            the ones used below.
#   v2       Fed communication v2. One-shot out-of-sample lock: once results/v2/oos_chosen.json or
#            results/v2/oos_not_evaluated.json exists the run is refused (and the script says so). The record exists:
#            the decision rule FAILED and the out-of-sample window was not evaluated.
#   presser  press-conference ADDENDUM suite (BENCH-R, H1-primary, H1-Q, H1-answer and its 1 s sweep, lexicon
#            control, spreads) on presser/text_chrono, written to $BACKTEST_RERUN_DIR/presser_h1, then compared with
#            the committed results (results/presser_h1, presser/backtest/positions). Needs the licensed market data.
#   h234     exploratory H2/H3/H4 stage, only when FEDPRESS_ROOT holds the fedpress feature tree; skipped with a
#            message otherwise. Real mode only: a placebo tree, re-run tree or output folder is refused.
#
# Environment (no machine-specific defaults)
#   PY                  Python with pandas, numpy, scipy, statsmodels, pyarrow (default: python)
#   GQH_MARKET_DIR      folder with the licensed Databento files ohlcv-1m__all_2016_2026.parquet,
#                       ohlcv-1s__all_2016_2026.parquet, bbo-1s__all_2016_2026.parquet (default: $GQH_DATA_DIR/presser)
#   GQH_DATA_DIR        the gqh data cache (v2 engine data; fallback location of the market files)
#   CHRONO_ROOT         chrono walk-forward work root (nlp/run_local.py); optional
#   CHRONO_PY           Python for nlp/chrono_stance.py merge, if the merge is missing (default: $PY)
#   FEDPRESS_ROOT       fedpress output tree <root>/meetings/<presser_id>/ (HiPerGator run); optional
#   H234_SI_ROOT        64 kbps source-invariance re-run tree; optional
#   H234_OUT_DIR        H2/H3/H4 output folder (default: backtests/presser/backtest_h234)
#   FEDPRESS_PKG        fedpress package (default: hpg/fedpress_pkg in this repo)
#   GQH_REPO, V2_WORK_ROOT  only needed if the v2 run were not locked (see v2/run_v2.py)
#   BACKTEST_RERUN_DIR  re-run outputs (default: backtests/rerun, ignored by git)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$HERE")"
PY="${PY:-python}"
CHRONO_PY="${CHRONO_PY:-$PY}"
RERUN="${BACKTEST_RERUN_DIR:-$HERE/rerun}"
STAGE="${1:-all}"
export PYTHONIOENCODING=utf-8
export PYTHONDONTWRITEBYTECODE=1
unset GQH_OOS_UNLOCK PRESSER_OUT_DIR PRESSER_TEXT_DIR PRESSER_BT_DIR || true

case "$STAGE" in
  all | chrono | v2 | presser | h234) ;;
  *) echo "usage: $0 [all | chrono | v2 | presser | h234]" >&2; exit 2 ;;
esac

FAIL=0
STATUS=()
record() { STATUS+=("$1"); echo "-> $1"; }
want() { [ "$STAGE" = all ] || [ "$STAGE" = "$1" ]; }

lower() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]'; }
is_placebo_path() {   # a path that names or holds placebo data
  [ -n "$1" ] || return 1
  case "$(lower "$1")" in *placebo*) return 0 ;; esac
  [ -e "$1/PLACEBO.json" ] || [ -e "$1/PLACEBO_README.txt" ]
}

MARKET_FILES="ohlcv-1m__all_2016_2026.parquet ohlcv-1s__all_2016_2026.parquet bbo-1s__all_2016_2026.parquet"
MKT="${GQH_MARKET_DIR:-}"
if [ -z "$MKT" ] && [ -n "${GQH_DATA_DIR:-}" ]; then MKT="$GQH_DATA_DIR/presser"; fi
market_ok() {
  [ -n "$MKT" ] || return 1
  local f
  for f in $MARKET_FILES; do [ -f "$MKT/$f" ] || return 1; done
}

mkdir -p "$RERUN"
echo "backtests: $HERE"
echo "re-run outputs: $RERUN"

# ------------------------------------------------------------------ chrono inputs (optional)
if want chrono; then
  echo
  echo "== chrono inputs"
  if [ -z "${CHRONO_ROOT:-}" ]; then
    record "chrono: skipped (CHRONO_ROOT not set; the committed frozen inputs are used)"
  elif is_placebo_path "$CHRONO_ROOT"; then
    record "chrono: REFUSED ($CHRONO_ROOT is a placebo root; this script runs real data only)"; FAIL=1
  else
    CI="$RERUN/chrono_inputs"
    rm -rf "$CI"; mkdir -p "$CI"
    built=1
    if ! (cd "$HERE/wire" && "$PY" check_chrono.py --root "$CHRONO_ROOT") > "$CI/check_chrono.log" 2>&1; then
      tail -n 20 "$CI/check_chrono.log"; built=0; why="check_chrono failed (see $CI/check_chrono.log)"
    elif [ ! -f "$CHRONO_ROOT/scores/merge_meta.json" ] && ! "$CHRONO_PY" "$REPO_ROOT/nlp/chrono_stance.py" \
        --root "$CHRONO_ROOT" merge --years 2015-2026 --no-publish > "$CI/merge_stdout.log" 2>&1; then
      built=0; why="chrono merge failed (see $CI/merge_stdout.log)"
    elif ! "$PY" "$HERE/v2/adapt_v2.py" --chrono-root "$CHRONO_ROOT" --out "$CI/v2/doc_scores.parquet" \
        > "$CI/adapt_v2.log" 2>&1; then
      built=0; why="v2 adapter failed (see $CI/adapt_v2.log)"
    elif ! "$PY" "$HERE/presser/adapt_presser.py" --chrono-root "$CHRONO_ROOT" --text-out "$CI/text_chrono" \
        > "$CI/adapt_presser.log" 2>&1; then
      built=0; why="press-conference adapter failed (see $CI/adapt_presser.log)"
    fi
    if [ "$built" = 1 ]; then
      ok=1
      "$PY" "$HERE/tools/compare_results.py" --label "v2 doc scores" --ref "$HERE/v2/score" --new "$CI/v2" \
        --skip doc_scores_lexonly.parquet || ok=0
      "$PY" "$HERE/tools/compare_results.py" --label "presser text_chrono" --ref "$HERE/presser/text_chrono" \
        --new "$CI/text_chrono" || ok=0
      if [ "$ok" = 1 ]; then
        record "chrono: rebuilt inputs match the committed frozen inputs"
      else
        record "chrono: rebuilt inputs DIFFER from the committed frozen inputs (see above; committed inputs used)"; FAIL=1
      fi
    else
      record "chrono: $why"; FAIL=1
    fi
  fi
fi

# ------------------------------------------------------------------ v2 (one-shot OOS lock)
if want v2; then
  echo
  echo "== Fed communication v2"
  REC=""
  for f in oos_chosen.json oos_not_evaluated.json; do
    if [ -f "$HERE/results/v2/$f" ]; then REC="$HERE/results/v2/$f"; break; fi
  done
  if [ -n "$REC" ]; then
    echo "v2: REFUSED to re-run: one-shot out-of-sample lock."
    echo "    Decision record: $REC"
    sed 's/^/    /' "$REC"
    echo
    echo "    The pre-registered rule failed (full in-sample Sharpe at 2x costs 0.387 <= 0.5), so the out-of-sample"
    echo "    window was never evaluated and never will be. Committed results: results/v2/, results/summary.md."
    # the runner applies the same lock itself (checked before gqh-flow-clock is imported)
    if "$PY" "$HERE/v2/run_v2_chrono.py" --doc-scores "$HERE/v2/score/doc_scores.parquet" --out "$HERE/results/v2" \
        --skip-if-complete > "$RERUN/v2_lock_check.log" 2>&1; then
      sed 's/^/    runner: /' "$RERUN/v2_lock_check.log"
      record "v2: refused (one-shot OOS lock; decision record $(basename "$REC") exists: rule FAILED, OOS not evaluated)"
    else
      sed 's/^/    runner: /' "$RERUN/v2_lock_check.log"
      record "v2: refused by the lock, but the runner's own lock check failed (see $RERUN/v2_lock_check.log)"; FAIL=1
    fi
  else
    # only reachable if the committed decision record were removed
    : "${GQH_REPO:?set GQH_REPO (gqh-flow-clock clone) for a v2 run}"
    : "${GQH_DATA_DIR:?set GQH_DATA_DIR for a v2 run}"
    : "${V2_WORK_ROOT:?set V2_WORK_ROOT (v2 inputs not in git) for a v2 run}"
    if (cd "$GQH_REPO" && "$PY" "$HERE/v2/run_v2_chrono.py" --doc-scores "$HERE/v2/score/doc_scores.parquet" \
        --out "$HERE/results/v2"); then
      record "v2: run completed (results/v2; its decision record now locks the out-of-sample window)"
    else
      record "v2: FAILED"; FAIL=1
    fi
  fi
fi

# ------------------------------------------------------------------ press-conference ADDENDUM suite
P_OUT="$RERUN/presser_h1"
if want presser; then
  echo
  echo "== press-conference suite (BENCH-R, H1-primary, H1-Q, H1-answer, lexicon control)"
  if ! market_ok; then
    record "presser: NOT RUN (licensed market data not found; set GQH_MARKET_DIR to the folder with $MARKET_FILES)"
    FAIL=1
  else
    export GQH_MARKET_DIR="$MKT"
    rm -rf "$P_OUT"; mkdir -p "$P_OUT"
    if PRESSER_TEXT_DIR="$HERE/presser/text_chrono" PRESSER_OUT_DIR="$P_OUT" PY="$PY" \
        bash "$HERE/presser/backtest/code/run_all.sh" addendum > "$P_OUT/run_all_stdout.log" 2>&1; then
      tail -n 3 "$P_OUT/run_all_stdout.log"
      ok=1
      "$PY" "$HERE/tools/compare_results.py" --label "H1 results" --ref "$HERE/results/presser_h1" \
        --new "$P_OUT/results" --skip $(cd "$HERE/results/presser_h1" && ls tables/*.csv) || ok=0
      "$PY" "$HERE/tools/compare_results.py" --label "per-meeting tables" --ref "$HERE/results/presser_h1/tables" \
        --new "$P_OUT/tables" || ok=0
      "$PY" "$HERE/tools/compare_results.py" --label "frozen H1 positions" --ref "$HERE/presser/backtest/positions" \
        --new "$P_OUT/positions" || ok=0
      if [ "$ok" = 1 ]; then
        record "presser: re-run reproduces the committed results (G3 NO-GO unchanged); outputs in $P_OUT"
      else
        record "presser: re-run DIFFERS from the committed results (see above); outputs in $P_OUT"; FAIL=1
      fi
      if [ -n "${CHRONO_ROOT:-}" ] && ! is_placebo_path "$CHRONO_ROOT" && [ -f "$CHRONO_ROOT/scores/merge_meta.json" ]; then
        if "$PY" "$HERE/wire/summarize.py" --chrono-root "$CHRONO_ROOT" --v2-scores "$HERE/v2/score/doc_scores.parquet" \
            --v2-out "$HERE/results/v2" --presser-text "$HERE/presser/text_chrono" --presser-out "$P_OUT" \
            --out-dir "$RERUN/summary" > "$RERUN/summarize.log" 2>&1; then
          echo "combined summary: $RERUN/summary/summary.md"
        else
          echo "combined summary failed (see $RERUN/summarize.log)"
        fi
      fi
    else
      tail -n 30 "$P_OUT/run_all_stdout.log"
      record "presser: FAILED (see $P_OUT/run_all_stdout.log)"; FAIL=1
    fi
  fi
fi

# ------------------------------------------------------------------ exploratory H2/H3/H4
if want h234; then
  echo
  echo "== exploratory H2/H3/H4 (voice, face, combined)"
  have_features=0
  if [ -n "${FEDPRESS_ROOT:-}" ] && [ -d "$FEDPRESS_ROOT/meetings" ]; then
    if compgen -G "$FEDPRESS_ROOT/meetings/*/voice/voice_chunks.parquet" > /dev/null \
        || compgen -G "$FEDPRESS_ROOT/meetings/*/face/face_frames.parquet" > /dev/null; then have_features=1; fi
  fi
  if [ "$have_features" = 0 ]; then
    record "h234: skipped (no fedpress voice/face features: FEDPRESS_ROOT unset or without meetings/*/voice|face tables; pending the HiPerGator run)"
  elif is_placebo_path "$FEDPRESS_ROOT" || is_placebo_path "${H234_SI_ROOT:-}" || is_placebo_path "${H234_OUT_DIR:-}"; then
    record "h234: REFUSED (placebo tree or output path given; this script runs real features only)"; FAIL=1
  elif ! market_ok; then
    record "h234: NOT RUN (licensed market data not found; set GQH_MARKET_DIR)"; FAIL=1
  else
    export GQH_MARKET_DIR="$MKT"
    H_LOG="$RERUN/h234_run_all_stdout.log"
    if PY="$PY" bash "$HERE/presser/backtest/code/run_all.sh" h234 > "$H_LOG" 2>&1; then
      tail -n 5 "$H_LOG"
      record "h234: completed (exploratory, post-NO-GO; cannot rescue G3; no trading claim); outputs in ${H234_OUT_DIR:-$HERE/presser/backtest_h234}"
    else
      tail -n 30 "$H_LOG"
      record "h234: FAILED or refused (see $H_LOG)"; FAIL=1
    fi
  fi
fi

echo
echo "== summary"
for s in ${STATUS[@]+"${STATUS[@]}"}; do echo "  $s"; done
exit "$FAIL"
