"""Execution timing, commission rates, slippage and the financing adjustment, from the independent order/book log."""
import json
import sys

import numpy as np
import pandas as pd

V = "<scratch>/kit_native/verify_native_flow_clock/runs/"
name = sys.argv[1]
guide = "guide" in name
o = pd.read_csv(V + f"{name}_orders.csv", parse_dates=["created", "exec_dt"])
book = pd.read_csv(V + f"{name}_book.csv", parse_dates=["date"]).set_index("date")
meta = json.load(open(V + f"{name}_meta.json"))
days = book.index
nxt = pd.Series(days[1:], index=days[:-1])
print(name, "orders logged", len(o), o["status"].value_counts().to_dict())
c = o[o.status == "Completed"].copy()
c["next_bar"] = c["created"].map(nxt)
CLOSE, MARKET = 4, 0   # backtrader Order.Close=4? verify below
print("exectypes", c["exectype"].value_counts().to_dict())
for et, g in c.groupby("exectype"):
    same_day = (g["exec_dt"] == g["created"]).mean()
    next_day = (g["exec_dt"] == g["next_bar"]).mean()
    px_close = np.isclose(g["ex_price"], g["bar_close"], rtol=0, atol=1e-9).mean()
    px_open = np.isclose(g["ex_price"], g["bar_open"], rtol=0, atol=1e-9).mean()
    print(f"exectype {et}: n={len(g)} filled same bar {same_day:.4f} next bar {next_day:.4f} "
          f"at bar close {px_close:.4f} at bar open {px_open:.4f}")
    late = g[g["exec_dt"] != g["next_bar"]]
    if len(late):
        print("   not next bar:", late[["created", "exec_dt", "sym"]].head(5).to_string())
    notional = (g["ex_size"].abs() * g["ex_price"])
    rate = g["comm"] / notional
    exp = g["sym"].map(meta["side_bps"]) / 1e4 if not guide else 0.0005
    print(f"   commission/notional vs expected: max abs dev {np.abs(rate - exp).max():.3e}; "
          f"total comm {g['comm'].sum():.6g}, notional {notional.sum():.6g}")
    if guide:
        ref = g["bar_open"] if et == 0 else g["bar_close"]
        slip = np.sign(g["ex_size"]) * (g["ex_price"] / ref - 1) * 1e4
        print(f"   slippage bp: mean {slip.mean():.3f}, share < 4.999 bp {(slip < 4.999).mean():.4f}, "
              f"notional-weighted {np.average(slip, weights=notional):.3f}")
        short = (0.0005 - slip.clip(upper=5) / 1e4) * notional
        print(f"   slippage short of 5 bp: {short.sum():.6g} money; the harness extra totals {meta['extra_totals']}")

# financing: independent net weight held over day t from positions (A/C close fills at t excluded)
syms = meta["symbols"]
pos = book[[f"pos_{s}" for s in syms]].set_axis(syms, axis=1)
px = book[[f"c_{s}" for s in syms]].set_axis(syms, axis=1)
cf = c[c.exectype != 0].groupby(["exec_dt", "sym"])["ex_size"].sum().unstack().reindex(index=days, columns=syms).fillna(0.0)
held = pos - cf
nw = (held * px.shift(1)).sum(axis=1) / book["value"].shift(1)
daily = pd.read_csv(V + f"{name}_daily.csv", index_col=0, parse_dates=True)
d = (nw.reindex(daily.index).fillna(0.0) - daily["net_weight"]).abs()
print("independent net weight vs harness: max abs diff", d.max())
# return decomposition: bt return = overnight on pre-open shares + intraday on post-open shares - costs, cash earns 0
op = book[[f"o_{s}" for s in syms]].set_axis(syms, axis=1)
mk = c[c.exectype == 0].groupby(["exec_dt", "sym"])["ex_size"].sum().unstack().reindex(index=days, columns=syms).fillna(0.0)
pre = held - mk
pnl = (pre * (op - px.shift(1))).sum(axis=1) + (held * (px - op)).sum(axis=1)
# fill-price deviation from the open/close reference (slippage) and commissions
c["ref"] = np.where(c.exectype == 0, c["bar_open"], c["bar_close"])
dev = (c["ex_size"] * (c["ex_price"] - c["ref"])).groupby(c["exec_dt"]).sum().reindex(days).fillna(0.0)
comm = c.groupby("exec_dt")["comm"].sum().reindex(days).fillna(0.0)
extra = daily["extra_cost"].reindex(days).fillna(0.0) * book["value"] if "extra_cost" in daily else 0.0
r_dec = (pnl - dev - comm - extra) / book["value"].shift(1)
d2 = (r_dec.reindex(daily.index) - daily["ret"]).iloc[2:]
print("bt return vs (risky P&L - fill deviation - commission - extra) / NAV: max abs diff bp", float(d2.abs().max() * 1e4),
      "mean abs bp", float(d2.abs().mean() * 1e4))
