"""Independent measured half-spreads (bbo-1s, last clean quote at or before each second)."""
import json
import numpy as np
import pandas as pd
from vlib import *

ev = pd.read_csv(BT / "events/events.csv", dtype={"date": str})
ev = ev[(ev.scheduled == 1) & (ev.market_window_covers_event == 1)]
qc, nbad = clean_bbo(load_bbo())
grid = []
for r in ev.itertuples():
    secs = pd.date_range(ts(r.date, "13:30:00"), ts(r.date, "16:30:00"), freq="s", inclusive="left")
    st = ts(r.date, r.presser_start_est_et)
    for s in ["ZT", "ZN", "ES"]:
        grid.append(pd.DataFrame(dict(sym=s, t=secs, date=r.date, pm=np.floor((secs - st).total_seconds() / 60).astype(int),
                                      hm=secs.strftime("%H:%M"))))
G = pd.concat(grid, ignore_index=True)
q = quote_asof(qc, G)
G["hs"] = ((q.ask - q.bid) / 2).values
G["stale"] = q.stale_s.values
G["tk"] = [tick(s, d) for s, d in zip(G.sym, G.date)] if False else np.where(
    G.sym == "ZT", np.where(G.date < "2019-01-14", 1 / 128, 1 / 256), np.where(G.sym == "ZN", 1 / 64, 0.25))
G["hs_t"] = G.hs / G.tk
G["era"] = np.where(G.date < "2020-01-01", "2016-2019", "2020-2026")
out = {"bad_records": nbad}
pmw = G[(G.pm >= -40) & (G.pm <= 90)]
agg = pmw.groupby(["sym", "era", "pm"]).hs_t.agg(med="median", p90=lambda x: x.quantile(0.9), mean="mean")
out["minutes_where_median_ne_0.5"] = agg[agg.med != 0.5].reset_index().to_dict("records")
out["minutes_where_p90_gt_0.5"] = agg[agg.p90 > 0.5].reset_index().to_dict("records")
cm = G.groupby(["sym", "era", "hm"]).hs_t.agg(med="median", p90=lambda x: x.quantile(0.9), mean="mean")
out["clock_minutes_p90_gt_0.5"] = cm[cm.p90 > 0.5].reset_index().to_dict("records")
out["share_seconds_one_tick_market"] = G.groupby("sym").apply(lambda g: float((g.hs_t == 0.5).mean())).to_dict()
out["share_seconds_stale_gt60"] = G.groupby("sym").apply(lambda g: float((g.stale > 60).mean())).to_dict()
# fill points
tr = pd.read_csv(V / "v02_benchr_trades.csv", dtype={"date": str})
fp = {}
for nm, sub in [("bench_entry_1420", tr[tr["var"] == "tau"][["sym", "e_bid", "e_ask", "tk", "e_stale"]].rename(
        columns={"e_bid": "b", "e_ask": "a", "e_stale": "st"})),
                ("bench_exit_tau", tr[tr["var"] == "tau"][["sym", "x_bid", "x_ask", "tk", "x_stale"]].rename(
                    columns={"x_bid": "b", "x_ask": "a", "x_stale": "st"}))]:
    sub = sub.dropna()
    sub["hs_t"] = (sub.a - sub.b) / 2 / sub.tk
    fp[nm] = sub.groupby("sym").agg(n=("hs_t", "size"), med=("hs_t", "median"), p90=("hs_t", lambda x: x.quantile(0.9)),
                                     mean=("hs_t", "mean"), stale_max=("st", "max")).round(3).to_dict("index")
h1 = pd.read_csv(V / "v03_lex_h1primary_trades_ZT.csv", dtype={"date": str})
h1 = h1[h1.clock == "upper"]
fp["h1_exit_1600_ZT"] = dict(med=float((h1.x_hs / h1.tk).median()), p90=float((h1.x_hs / h1.tk).quantile(0.9)),
                             stale_max=float(h1.x_stale.max()))
fp["h1_entry_tau_ZT"] = dict(med=float((h1.e_hs / h1.tk).median()), p90=float((h1.e_hs / h1.tk).quantile(0.9)),
                             stale_max=float(h1.e_stale.max()))
out["fill_points"] = fp
# dollar conversion of a 0.5-tick half-spread
out["usd_per_side_at_0.5_tick"] = {"ZT_2016-2018": 0.5 * 15.625, "ZT_2019+": 0.5 * 7.8125, "ZN": 0.5 * 15.625, "ES": 0.5 * 12.5}
json.dump(out, open(V / "v05_spreads.json", "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in out.items() if k not in ("minutes_where_median_ne_0.5",)}, indent=1, default=str)[:6000])
print("minutes median != 0.5:", out["minutes_where_median_ne_0.5"])
