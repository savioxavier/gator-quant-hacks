#!/usr/bin/env bash
# Scratch: refused orders on the kit's cash broker by reserve (S3 / BH5, project / guide, 1e9 / 100k).
set -u
S="$(cd "$(dirname "$0")" && pwd)/reserve"
cd /d/AUTOMATION/gqh-systematic
export GQH_DATA_DIR=<home>/.cache/gqh PYTHONIOENCODING=utf-8
export GQH_STARTER_KIT=<scratch>/webull_kit/gqh-webull-backtrader-starter
P=<home>/.venvs/gqh-systematic/Scripts/python.exe
n=0
for bh in false true; do for costs in project guide; do for cash in 1e9 100000; do for r in 0 0.0025 0.005 0.01; do
  name="bh${bh}_${costs}_${cash}_r${r}"
  $P validation/starter_kit/run_in_starter.py --strategy gqh_gtaa --costs $costs --cash $cash --params "buy_and_hold=$bh,reserve=$r" --json "$S/$name.json" --series "$S/$name.csv" > "$S/$name.log" 2>&1 &
  n=$((n+1)); if [ $((n % 8)) -eq 0 ]; then wait; fi
done; done; done; done
wait
grep -l Traceback "$S"/*.log || echo "no tracebacks"
