"""Scratch: compact table of check/summary.json."""
import json, os, sys
S = os.path.dirname(os.path.abspath(__file__))
a = json.load(open(os.path.join(S, sys.argv[1] if len(sys.argv) > 1 else "check", "summary.json")))
print("meta", a["meta"]["reference_checks"], "desync", a["meta"].get("desync_bars"))
for k, v in a["references"].items():
    print(f"REF {k:11s}", {w: (round(x['our_sharpe_excess'], 4), round(x['kit_sharpe_rf0'], 4)) for w, x in v["sharpe"].items()},
          {w: (round(v[w]['ann_return'] * 100, 3), round(v[w]['max_drawdown'] * 100, 2)) for w in ("in_sample", "out_of_sample")})
for r in a.get("internals_vs_engine", []):
    if r["max_abs_diff"] > 1e-12 or "paper" in r["quantity"] or r["quantity"] == "k":
        print("   INT", r)
for n, r in a["runs"].items():
    print(f"\n{n}  costs={r['costs']} extra={r['extra_costs']} orders={r['orders']['total']} refused={r['orders']['refused']}")
    for w in ("in_sample", "out_of_sample"):
        x = r["windows"][w]
        m, mal = r["vs_matched_reference"]["raw"][w], r["vs_matched_reference"]["aligned"][w]
        o, oal = r["vs_official"]["raw"][w], r["vs_official"]["aligned"][w]
        print(f"  {w:13s} kit {x['kit_sharpe_rf0']:.4f} ours {x['our_sharpe_excess']:.4f} ann {x['ann_return']*100:.3f}% dd {x['max_drawdown']*100:.2f}% gross {x['mean_gross_weight']:.2f}"
              f" | {r['vs_matched_reference']['reference']}: corr {m['corr']:.5f} mad {m['mean_abs_diff_bp']:.3f} | aligned corr {mal['corr']:.5f} mad {mal['mean_abs_diff_bp']:.3f} td {mal['tracking_diff_ann']*100:.3f}%"
              f" | official: corr {o['corr']:.5f} mad {o['mean_abs_diff_bp']:.3f} al {oal['corr']:.5f}/{oal['mean_abs_diff_bp']:.3f}")
    for rp, ag in (r.get("vs_weight_replays") or {}).items():
        print("    replay", rp, {w: (round(ag[w]['corr'], 5), round(ag[w]['mean_abs_diff_bp'], 3)) for w in ag})
    print("    largest", r["largest_aligned_daily_diffs_bp"])
for k, v in a["attribution"].items():
    print("ATTR", k, v["a"], "vs", v["b"], {w: (round(x["corr"], 6), round(x["mean_abs_diff_bp"], 3), round(x["tracking_diff_ann"] * 100, 3)) for w, x in v["agreement"].items()})
