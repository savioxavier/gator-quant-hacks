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
turtle|turtle+trading+backtest
lean_lib|strategy+library+quantconnect
intraday_mom|intraday+momentum+spy
overnight|overnight+returns+anomaly
paa|protective+asset+allocation
vaa|vigilant+asset+allocation
daa|defensive+asset+allocation
connors|connors+rsi+backtest
ibs|internal+bar+strength
carver|robert+carver+trading
mf_rep|managed+futures+replication
fomc|fomc+drift
yc|yield+curve+trading+strategy
etf_trend|trend+following+etf+backtest
comm_mom|commodity+momentum+backtest
adaptive|adaptive+asset+allocation
gem|global+equities+momentum
vix_timing|vix+timing+strategy
mom_crash|momentum+futures+backtest
qc_tut|QuantConnect+Tutorials
Q
