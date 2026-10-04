#!/usr/bin/env bash
# Scratch: gqh_gtaa sized at the fill's own open (cheat-on-open diagnostic), then exact_next_open.py.
set -u
D="$(cd "$(dirname "$0")" && pwd)"
C="$D/../check"
cd /d/AUTOMATION/gqh-systematic
export GQH_DATA_DIR=<home>/.cache/gqh PYTHONIOENCODING=utf-8 PYTHONPATH="$D"
export GQH_STARTER_KIT=<scratch>/webull_kit/gqh-webull-backtrader-starter
P=<home>/.venvs/gqh-systematic/Scripts/python.exe
for bh in false true; do n=$([ $bh = true ] && echo BH5 || echo S3); for costs in project none; do
  $P validation/starter_kit/run_in_starter.py --strategy gtaa_open_sizing --margin --cash 1e9 --costs $costs \
    --params "buy_and_hold=$bh" --is-start 2005-11-01 --reference "$C/engine_${n}_${costs}.csv" \
    --json "$D/${n}_${costs}_open_sized.json" --series "$D/${n}_${costs}_open_sized.csv" > "$D/${n}_${costs}.log" 2>&1 &
done; done; wait
$P "$D/exact_next_open.py"
