cd /d/AUTOMATION/gqh-systematic
export GQH_DATA_DIR=<home>/.cache/gqh PYTHONIOENCODING=utf-8 GQH_STARTER_KIT=<scratch>/webull_kit/gqh-webull-backtrader-starter
V=<scratch>/kit_native/verify_native_flow_clock
PY=<home>/.venvs/gqh-systematic/Scripts/python.exe
job() { $PY -B $V/vrun.py "$@" > $V/runs/log_$(echo "$@" | tr -c 'A-Za-z0-9' _ | tail -c 60).txt 2>&1; }
i=0
for c in 2009-02-19 2014-05-23 2020-03-31 2017-11-22 2025-07-28 2011-08-30 2007-08-15 2013-04-10 2022-09-13 2026-02-05; do
  i=$((i+1)); job --out $V/runs/cut_$c --cut $c --seed $i --perturb-side &
  if (( i % 5 == 0 )); then wait; fi
done
job --out $V/runs/base_guide --costs guide &
job --out $V/runs/cutg_2016-06-27 --costs guide --cut 2016-06-27 --seed 99 --perturb-side &
job --out $V/runs/base_none --costs none &
wait
echo done
