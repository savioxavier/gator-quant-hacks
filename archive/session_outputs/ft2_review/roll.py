import pandas as pd, numpy as np
raw = pd.read_parquet(r"<home>/.cache/gqh/databento_raw/glbx_ohlcv1d_v01.parquet")
raw["root"] = raw.symbol.str.split(".").str[0]; raw["rank"] = raw.symbol.str.split(".").str[2].astype(int)
raw["date"] = pd.to_datetime(raw.ts_event).dt.tz_convert("UTC").dt.tz_localize(None).dt.normalize()
print(raw.columns.tolist(), raw.date.max())
w = raw.pivot_table(index=["root", "date"], columns="rank", values="volume", aggfunc="last").dropna()
iv = raw.pivot_table(index=["root", "date"], columns="rank", values="instrument_id", aggfunc="last").dropna()
frac = (w[0] < w[1]).groupby(level=0).mean()
print("share of days where v.0 same-day volume < v.1 volume (would be 0 if rank used same-day volume):")
print(frac.round(4).to_string())
# on roll days: did the new front have higher volume than the old front on the PREVIOUS day?
out = {}
for r, g in iv.groupby(level=0):
    g = g.droplevel(0); vv = w.loc[r]
    f = g[0]; roll = f != f.shift(1); roll.iloc[0] = False
    ok_prev = ok_same = n = 0
    for d in g.index[roll]:
        i = g.index.get_loc(d)
        if i == 0: continue
        pd_ = g.index[i - 1]; old = f.iloc[i - 1]; new = f.loc[d]
        sub_prev = raw[(raw.root == r) & (raw.date == pd_)].set_index("instrument_id").volume
        sub_same = raw[(raw.root == r) & (raw.date == d)].set_index("instrument_id").volume
        if new in sub_prev.index and old in sub_prev.index:
            n += 1; ok_prev += sub_prev[new] > sub_prev[old]
            if new in sub_same.index and old in sub_same.index: ok_same += sub_same[new] > sub_same[old]
    out[r] = (n, ok_prev, ok_same)
print("roll days: n, new>old volume on previous day, new>old on same day:", out)
