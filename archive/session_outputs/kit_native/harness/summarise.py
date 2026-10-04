"""Scratch: one table of every check's windows and reference agreement."""
import glob
import json
import os
import sys

S = os.path.dirname(os.path.abspath(__file__))
for f in sorted(glob.glob(os.path.join(S, "*.json"))):
    a = json.load(open(f))
    if "windows" not in a:
        continue
    m = a["meta"]
    print(f"{os.path.basename(f)}  costs={m['costs']} extra={m['extra_costs']} fill={m['params'].get('fill', '-')} "
          f"orders={a['orders']['total']} refused={a['orders']['refused']} kit_sharpe_full={a['kit_metrics']['sharpe_ratio']}"
          f" xc={ {k: round(v / 1e6, 1) for k, v in (a.get('extra_costs_money') or {}).items()} }")
    for w in ("in_sample", "out_of_sample", "full"):
        x = a["windows"][w]
        if not x:
            continue
        r = (a.get("reference") or {}).get("windows", {}).get(w) or {}
        ag = r.get("agreement_bt_minus_reference", {})
        print(f"   {w:13s} {x['start']}..{x['end']} kit {x['kit_sharpe_rf0']:.4f} ours {x['our_sharpe_excess']:.4f} "
              f"tot_sample {x['sharpe_total_sample_std']:.4f} ann {x['ann_return']:.5f} dd {x['max_drawdown']:.5f} "
              f"orders {x['orders']} ref[corr {ag.get('corr', float('nan')):.6f} mad {ag.get('mean_abs_diff_bp', float('nan')):.4f}bp "
              f"ours {r.get('reference_our_sharpe_excess')} kit {r.get('reference_kit_sharpe_rf0')}]")
