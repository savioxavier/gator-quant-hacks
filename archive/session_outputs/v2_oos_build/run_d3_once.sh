#!/usr/bin/env bash
# The ONE out-of-sample evaluation of v2 under deviation D-3. Writes RUN_LOG.md before the run starts; prints only
# the exit status (no number) to the terminal; the run's own stdout goes to a log file.
set -u
S="<scratch>"
T="$S/team_push"
PY="<home>/.venvs/gqh-systematic/Scripts/python.exe"
OUTROOT="$T/backtests/results/v2_oos"
LOG="$OUTROOT/RUN_LOG.md"
RAW="$S/v2_oos_build/run_stdout_raw.log"
if [ -e "$OUTROOT/run" ] || [ -e "$LOG" ]; then echo "refusing: $OUTROOT/run or RUN_LOG.md already exists"; exit 1; fi
mkdir -p "$OUTROOT"
cd "$T" || exit 1
h() { sha256sum "$1" | cut -d' ' -f1; }
D="<home>/.cache/gqh"
{
  echo "# v2 out-of-sample evaluation: run log (deviation D-3)"
  echo
  echo "Deviation: \`preregistration/v2_DEVIATION_D3_OOS.md\`, sha256 $(h preregistration/v2_DEVIATION_D3_OOS.md)"
  echo "(pinned: 97585d3ca3e7f5764d16e24787486c51ca298dd95ca57ad82d27e1ba30af1c69)."
  echo "Pre-registration: \`preregistration/HYPOTHESIS_v2.md\`, sha256 $(h preregistration/HYPOTHESIS_v2.md)."
  echo
  echo "This file was written before the run started; the end time and exit status were appended when the process"
  echo "exited, before any output number was read. The evaluation is run once."
  echo
  echo "## Command"
  echo
  echo '```'
  echo 'cd <team repo>'
  echo 'GQH_REPO=<solo-repo> GQH_DATA_DIR=<home>/.cache/gqh V2_WORK_ROOT=<v2 work root> \'
  echo '  V2_OOS_DEVIATION=preregistration/v2_DEVIATION_D3_OOS.md PYTHONIOENCODING=utf-8 \'
  echo '  <home>/.venvs/gqh-systematic/Scripts/python.exe backtests/v2/run_v2_chrono.py \'
  echo '  --doc-scores backtests/v2/score/doc_scores.parquet --out backtests/results/v2_oos/run'
  echo '```'
  echo
  echo "GQH_OOS_UNLOCK unset. \`<team repo>\` is this repository; \`<v2 work root>\` is the original local v2 work root"
  echo "(inputs not in git, see \`backtests/v2/README.md\`). stdout and stderr: \`run/run_stdout.log\` (local paths replaced"
  echo "by these placeholders)."
  echo
  echo "## Code and inputs"
  echo
  echo "- git HEAD $(git rev-parse --short HEAD) (branch $(git rev-parse --abbrev-ref HEAD)); uncommitted D-3 unlock in"
  echo "  \`backtests/v2/run_v2.py\` and \`backtests/v2/run_v2_chrono.py\` (git diff sha256 $(git diff -- backtests/v2/run_v2.py backtests/v2/run_v2_chrono.py | sha256sum | cut -d' ' -f1))"
  for f in backtests/v2/run_v2.py backtests/v2/run_v2_chrono.py backtests/v2/v2lib.py backtests/wire/wirelib.py \
           backtests/v2/report_v2_oos.py backtests/v2/score/doc_scores.parquet; do
    echo "- \`$f\` sha256 $(h "$f")"
  done
  echo "- report script \`backtests/v2/report_v2_oos.py\` (metric definitions) was written and tested on synthetic"
  echo "  series before this run; its hash above is the version used for the report"
  for f in fedspeak_v2/corpus/fomc_dates.csv fedspeak_v2/corpus/fomc_dates_variantA_style.csv \
           savio_gqh/strategies/01/data/processed/fomc_dates.csv savio_gqh/strategies/01/trials/log.csv \
           fedspeak/extend/speech_scores_2011_2026.csv edges/combine/combine.py edges/series/PORT_core_ER_6.parquet; do
    echo "- \`<v2 work root>/$f\` sha256 $(h "$S/$f")"
  done
  for f in etf_daily.parquet futures_daily.parquet futures_1600.parquet fred_daily.parquet rf_daily.parquet; do
    echo "- data cache \`$f\` sha256 $(h "$D/$f")"
  done
  echo "- gqh-flow-clock HEAD $(git -C <solo-repo> rev-parse --short HEAD); src/engine.py sha256 $(h <solo-repo>/src/engine.py)"
  echo
  echo "## Run"
  echo
  echo "- start (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$LOG"

env -u GQH_OOS_UNLOCK GQH_REPO=<solo-repo> GQH_DATA_DIR="$D" V2_WORK_ROOT="$S" \
  V2_OOS_DEVIATION=preregistration/v2_DEVIATION_D3_OOS.md PYTHONIOENCODING=utf-8 \
  "$PY" backtests/v2/run_v2_chrono.py --doc-scores backtests/v2/score/doc_scores.parquet \
  --out backtests/results/v2_oos/run > "$RAW" 2>&1
rc=$?
{
  echo "- end (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "- exit status: $rc"
  echo
  echo "## Outputs (sha256)"
  echo
  if [ -d backtests/results/v2_oos/run ]; then
    for f in $(cd backtests/results/v2_oos/run && ls); do echo "- \`run/$f\` $(h "backtests/results/v2_oos/run/$f")"; done
  fi
} >> "$LOG"
echo "exit $rc"
