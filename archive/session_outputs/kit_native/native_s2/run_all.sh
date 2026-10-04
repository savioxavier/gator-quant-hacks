#!/usr/bin/env bash
# Scratch: native S1/S2 in the starter kit, every cost setting and fill, against the engine references.
set -u
S="$(cd "$(dirname "$0")" && pwd)"
cd /d/AUTOMATION/gqh-systematic
export GQH_DATA_DIR=<home>/.cache/gqh PYTHONIOENCODING=utf-8
export GQH_STARTER_KIT=<scratch>/webull_kit/gqh-webull-backtrader-starter
P=<home>/.venvs/gqh-systematic/Scripts/python.exe
H=validation/starter_kit/run_in_starter.py
run() { name=$1; shift; $P $H --strategy gqh_equity_trend "$@" --json "$S/$name.json" --series "$S/$name.csv" > "$S/$name.log" 2>&1; echo "exit $?" >> "$S/$name.log"; }
for b in s2 s1; do
  B=$(echo $b | tr a-z A-Z)
  run ${b}_close_project --params "book=$B,decisions=$S/native_${b}_dec_close.csv" --costs project --reference "$S/${b}_official.csv" --report "$S/${b}_close_project.html" &
  run ${b}_close_guide --params "book=$B" --costs guide --reference "$S/${b}_engine_guide.csv" &
  run ${b}_close_guide_literal --params "book=$B" --costs guide --no-extra-costs --reference "$S/${b}_engine_guide.csv" &
  wait
  run ${b}_close_none --params "book=$B" --costs none --reference "$S/${b}_engine_nocost.csv" &
  run ${b}_coc_project --params "book=$B,fill=coc,decisions=$S/native_${b}_dec_coc.csv" --costs project --reference "$S/${b}_official.csv" &
  run ${b}_coc_guide --params "book=$B,fill=coc" --costs guide --reference "$S/${b}_engine_guide.csv" &
  wait
done
grep -l Traceback "$S"/*.log || echo "no tracebacks"
tail -qn1 "$S"/*.log | sort | uniq -c
