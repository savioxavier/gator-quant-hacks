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
trend_futures|trend+following+futures+backtest
carry_futures|carry+futures+backtest
taa|tactical+asset+allocation
dual_momentum|dual+momentum
risk_parity|risk+parity+backtest
pysystemtrade|pysystemtrade
qc_futures|quantconnect+strategy+futures
quantpedia|quantpedia
tom|turn+of+the+month
sector_rotation|sector+rotation+backtest
voltarget|volatility+targeting
vix_term|vix+term+structure
bond_mom|bond+momentum
orb|opening+range+breakout
seasonality|seasonality+futures
cot|commitments+of+traders
awesome_quant|awesome+quant
tsmom|time+series+momentum
cta|cta+replication
gtaa|faber+asset+allocation
Q
