#!/bin/bash
cd "$(dirname "$0")/gh"
i=0
while IFS='|' read -r name q; do
  [ -z "$name" ] && continue
  curl -s -H "Accept: application/vnd.github+json" "https://api.github.com/search/repositories?q=${q}&sort=stars&order=desc&per_page=30" -o "${name}.json"
  echo "$name $(python -c "import json;d=json.load(open('${name}.json',encoding='utf-8'));print(d.get('total_count'),d.get('message',''))" 2>&1)"
  i=$((i+1))
  python -c "import time; time.sleep(7)"
done <<'Q'
rsi2|rsi2+strategy
ibs2|ibs+mean+reversion
mr_spy|mean+reversion+spy+backtest
pairs_etf|pairs+trading+etf+backtest
skew_comm|skewness+commodity+futures
fedmodel|fed+model+yield+gap
jan_bar|january+barometer
dual_thrust|dual+thrust
gold_timing|gold+timing+strategy
paired_sw|paired+switching
Q
