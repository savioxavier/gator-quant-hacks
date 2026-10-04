import pandas as pd
from vlib import *
m1 = load_1m(); q = load_bbo()
s1 = pd.read_parquet(C / "ohlcv-1s__all_2016_2026.parquet", columns=["ts_event","instrument_id","symbol"]); s1["sym"]=s1.symbol.str[:2]; s1["day"]=s1.ts_event.dt.tz_convert(NY).dt.date.astype(str)
I = pd.DataFrame({nm: d.groupby(["day","sym"]).instrument_id.agg(lambda s: tuple(sorted(set(s)))) for nm,d in [("1m",m1),("1s",s1),("bbo",q)]})
print(I[(I["1m"]!=I["1s"]) | ((I["bbo"]!=I["1m"]) & I["bbo"].notna())])
print(I[I["1m"].isna()])
