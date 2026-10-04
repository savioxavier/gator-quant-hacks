import json, numpy as np, pandas as pd
from vlib import *
out = {}
m1 = load_1m()
s1 = pd.read_parquet(C / "ohlcv-1s__all_2016_2026.parquet"); s1["sym"] = s1.symbol.str[:2]
s1["et"] = s1.ts_event.dt.tz_convert(NY); s1["day"] = s1.et.dt.date.astype(str)
q = load_bbo()
# 1. window coverage
fl = m1.groupby(["day", "sym"]).et.agg(["min", "max", "count"])
fl["first"] = fl["min"].dt.strftime("%H:%M"); fl["last"] = fl["max"].dt.strftime("%H:%M")
out["first_bar_times"] = fl["first"].value_counts().to_dict()
out["last_bar_times"] = fl["last"].value_counts().head(8).to_dict()
out["n_days"] = int(m1.day.nunique())
# 2. bar convention: 1m open == first 1s open in [M, M+60)?
s1["minute"] = s1.et.dt.floor("min")
f1 = s1.sort_values("et").groupby(["sym", "minute"]).agg(o=("open", "first"), c=("close", "last"), v=("volume", "sum")).reset_index()
j = m1.merge(f1, left_on=["sym", "et"], right_on=["sym", "minute"], how="inner")
out["bar_start_conv_open_match"] = float((j.open == j.o).mean())
out["bar_start_conv_close_match"] = float((j.close == j.c).mean())
out["bar_start_conv_volume_match"] = float((j.volume == j.v).mean())
f1s = f1.copy(); f1s["minute"] = f1s.minute + pd.Timedelta(minutes=1)  # if ts_event were bar END
j2 = m1.merge(f1s, left_on=["sym", "et"], right_on=["sym", "minute"], how="inner")
out["bar_end_conv_open_match"] = float((j2.open == j2.o).mean())
# 3. statement jump minute (ET clock, DST check)
m1["absr"] = (m1.close / m1.open - 1).abs()
w = m1[(m1.sym == "ZT") & (m1.et.dt.strftime("%H:%M") >= "13:55") & (m1.et.dt.strftime("%H:%M") <= "14:10")]
pk = w.loc[w.groupby("day").absr.idxmax()]
pk["hm"] = pk.et.dt.strftime("%H:%M"); pk["dst"] = pk.et.apply(lambda x: bool(x.dst()))
out["ZT_peak_minute_13:55-14:10"] = pk.hm.value_counts().to_dict()
out["ZT_peak_minute_by_dst"] = pk.groupby("dst").hm.agg(lambda s: s.value_counts().to_dict()).to_dict()
# also high-low range per minute averaged
w2 = m1[m1.sym == "ZT"].copy(); w2["hm"] = w2.et.dt.strftime("%H:%M"); w2["rng"] = (w2.high - w2.low)
out["ZT_mean_range_pts_by_minute"] = w2[w2.hm.between("13:57", "14:03")].groupby("hm").rng.mean().round(5).to_dict()
# 4. instrument ids per window per file
ids = {}
for nm, d in [("1m", m1), ("1s", s1), ("bbo", q)]:
    ids[nm] = d.groupby(["day", "sym"]).instrument_id.agg(lambda s: tuple(sorted(set(s))))
I = pd.DataFrame(ids)
out["windows_with_id_change"] = {nm: int((I[nm].dropna().apply(len) > 1).sum()) for nm in ids}
I2 = I.dropna(subset=["bbo"])
out["bbo_vs_1m_id_mismatch"] = int((I2["bbo"] != I2["1m"]).sum())
out["1s_vs_1m_id_mismatch"] = int((I["1s"] != I["1m"]).sum())
# 5. price level and tick grid per sym per year
s1["yr"] = s1.day.str[:4]
grid = {}
for (sym, yr), g in s1.groupby(["sym", "yr"]):
    px = np.unique(np.r_[g.open.values, g.close.values, g.high.values, g.low.values])
    d = np.diff(px); d = d[d > 1e-12]
    grid[f"{sym}_{yr}"] = dict(med_px=round(float(np.median(px)), 3), min_step=float(d.min()) if len(d) else None)
out["tick_grid"] = grid
# ZT pre/post 2019 fine grid check
for lab, sub in [("ZT_le_2018-12-19", s1[(s1.sym == "ZT") & (s1.day <= "2018-12-19")]), ("ZT_ge_2019-01-30", s1[(s1.sym == "ZT") & (s1.day >= "2019-01-30")])]:
    px = np.r_[sub.open.values, sub.close.values]
    out[f"{lab}_share_on_1/256_odd"] = float(np.mean(np.abs((px * 256) % 2 - 1) < 1e-6))
# 6. prints inside quotes: 1s close vs quote at end of that second (ts_recv = second+1)
qc, nbad = clean_bbo(q)
out["bbo_bad_records"] = nbad
smp = s1[s1.sym.isin(["ZT", "ZN", "ES"])].sample(200000, random_state=1)
req = pd.DataFrame({"sym": smp.sym.values, "t": (smp.et + pd.Timedelta(seconds=1)).values, "px": smp.close.values})
req["t"] = pd.to_datetime(req.t).dt.tz_convert(NY) if req.t.dt.tz is not None else pd.to_datetime(req.t).dt.tz_localize("UTC").dt.tz_convert(NY)
r = quote_asof(qc, req)
inside = (r.px >= r.bid - 1e-9) & (r.px <= r.ask + 1e-9)
out["1s_close_inside_quote_at_second_end"] = r.assign(i=inside).groupby("sym").i.mean().round(4).to_dict()
req2 = req.copy(); req2["t"] = req2.t - pd.Timedelta(seconds=1)
r2 = quote_asof(qc, req2)
out["1s_close_inside_quote_at_second_start"] = r2.assign(i=(r2.px >= r2.bid - 1e-9) & (r2.px <= r2.ask + 1e-9)).groupby("sym").i.mean().round(4).to_dict()
# bbo ts_recv whole seconds? ts_event < ts_recv?
out["bbo_ts_recv_whole_second_share"] = float((q.ts_recv.dt.nanosecond == 0).mean() * (q.ts_recv.dt.microsecond == 0).mean())
out["bbo_ts_event_le_ts_recv_share"] = float((q.ts_event <= q.ts_recv).mean())
json.dump(out, open(V / "v01_data_qa.json", "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
