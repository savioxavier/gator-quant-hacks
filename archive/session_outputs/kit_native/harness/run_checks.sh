#!/usr/bin/env bash
# Scratch: every harness check (smoke test, F1 and S2 weight replays) into this folder.
set -u
S="$(cd "$(dirname "$0")" && pwd)"
cd /d/AUTOMATION/gqh-systematic
export GQH_DATA_DIR=<home>/.cache/gqh PYTHONIOENCODING=utf-8
export GQH_STARTER_KIT=<scratch>/webull_kit/gqh-webull-backtrader-starter
P=<home>/.venvs/gqh-systematic/Scripts/python.exe
H=validation/starter_kit/run_in_starter.py
F1="--strategy replay_weights --start 2005-01-03 --is-start 2006-05-08"
W="path=$S/f1_weights.csv"
ALL10=$(head -1 "$S/f1_weights.csv" | tr ',' '\n' | tail -n +2 | sed 's/$/=10/' | paste -sd,)

$P validation/starter_kit/export_f1.py --out "$S" > "$S/export_f1.log" 2>&1
$P "$S/export_s2_check.py" > "$S/export_s2.log" 2>&1

run() { name=$1; shift; $P $H "$@" --json "$S/$name.json" --series "$S/$name.csv" > "$S/$name.log" 2>&1; }
run smoke_dual_ma --strategy dual_ma --symbols SPY --start 2005-01-03 --end 2024-10-02 --report "$S/smoke_dual_ma.html" &
run replay_f1_project_noextra $F1 --params "$W" --costs project --no-extra-costs --reference "$S/f1_engine_simple.csv" --reference-rf zero &
run replay_f1_project $F1 --params "$W" --costs project --reference "$S/f1_official.csv" &
run replay_f1_guide_noextra $F1 --params "$W" --costs guide --no-extra-costs --reference "$S/f1_official.csv" &
run replay_f1_guide $F1 --params "$W" --costs guide --reference "$S/f1_official.csv" --report "$S/replay_f1_guide.html" &
wait
run replay_f1_comm10 $F1 --params "$W" --costs project --cost-bps "$ALL10" --reference "$S/f1_official.csv" &
run replay_f1_close_project_noextra $F1 --params "$W,fill=close" --costs project --no-extra-costs --reference "$S/f1_engine_simple.csv" --reference-rf zero &
run replay_f1_close_project $F1 --params "$W,fill=close" --costs project --reference "$S/f1_official.csv" &
run replay_f1_close_guide $F1 --params "$W,fill=close" --costs guide --reference "$S/f1_official.csv" &
run replay_s2_project --strategy replay_weights --params "path=$S/s2_held.csv" --costs project --is-start 2011-09-02 --reference "$S/s2_engine_net.csv" --reference-rf tbill &
wait
grep -l Traceback "$S"/*.log || echo "no tracebacks"
ALL5=$(echo "$ALL10" | sed 's/=10/=5/g')
run replay_f1_comm5_noextra $F1 --params "$W" --costs project --cost-bps "$ALL5" --no-extra-costs --reference "$S/f1_official.csv" &
run replay_s3_open_project --strategy replay_weights --params "path=$S/s3_held.csv,fill=open" --costs project --start 2005-01-03 --is-start 2005-11-01 --reference "$S/s3_engine_net.csv" --reference-rf tbill &
run replay_s3_open_guide --strategy replay_weights --params "path=$S/s3_held.csv,fill=open" --costs guide --start 2005-01-03 --is-start 2005-11-01 --reference "$S/s3_engine_net.csv" --reference-rf tbill &
wait
grep -l Traceback "$S"/*.log || echo "no tracebacks"
