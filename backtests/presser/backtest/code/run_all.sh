#!/usr/bin/env bash
# Reproduce the backtest label end to end (positions are re-frozen by s02; s03 refuses changed positions).
#
# Stages:
#   run_all.sh            the ADDENDUM label (BENCH-R, H1-primary, H1-answer): s01..s05, unchanged
#   run_all.sh h234       exploratory H2/H3/H4 (preregistration/presser_H2H3H4_EXPLORATORY.md) only:
#                         needs FEDPRESS_ROOT (the fedpress output tree); optional H234_SI_ROOT (64 kbps re-runs)
#                         and H234_OUT_DIR (output folder). Reads the frozen H1 positions read-only.
#   run_all.sh all        both, in that order
PY="${PY:-python}"   # interpreter with pandas, numpy, scipy, statsmodels, pyarrow
cd "$(dirname "$0")"
STAGE=${1:-addendum}

run_addendum() {
  "$PY" -W ignore s01_qa.py && "$PY" -W ignore s02_positions.py && "$PY" -W ignore s03_pnl.py && "$PY" -W ignore s04_spreads.py && "$PY" -W ignore s05_tables.py
}

run_h234() {
  : "${FEDPRESS_ROOT:?set FEDPRESS_ROOT to the fedpress output tree}"
  "$PY" -W ignore h234_s1_features.py && "$PY" -W ignore h234_s2_positions.py && "$PY" -W ignore h234_s3_h4train.py && "$PY" -W ignore h234_s4_pnl.py
}

case "$STAGE" in
  addendum) run_addendum ;;
  h234) run_h234 ;;
  all) run_addendum && run_h234 ;;
  *) echo "unknown stage: $STAGE (addendum | h234 | all)" >&2; exit 2 ;;
esac
