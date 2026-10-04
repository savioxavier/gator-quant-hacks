"""Scratch: count Close-fill notifications seen by ExtraCosts in the fill=close replay."""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "<solo-repo>/validation/starter_kit")
import run_in_starter as H  # noqa: E402

S = Path(__file__).resolve().parent
seen = Counter()
notional = [0.0, 0.0]
orig = H.ExtraCosts.notify_order


def patched(self, order):
    if order.status == order.Completed and order.exectype == order.Close:
        seen[order.ref] += 1
        notional[0] += abs(order.executed.size) * order.executed.price
    orig(self, order)


H.ExtraCosts.notify_order = patched
out = H.main(["--strategy", "replay_weights", "--start", "2005-01-03", "--is-start", "2006-05-08",
              "--params", f"path={S / 'f1_weights.csv'},fill=close", "--costs", "guide"])
print("close fills", len(seen), "max notifications per order", max(seen.values()), "notional", notional[0])
print(out["extra_costs_money"], out["orders"])
