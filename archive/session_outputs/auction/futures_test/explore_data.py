import sys, os
sys.path.insert(0, "<solo-repo>")
assert os.environ.get("GQH_OOS_UNLOCK") != "1"
import pandas as pd, numpy as np
from src import engine as E
from src.strategies import ifc_treasury as TC
a = TC.load_nominal_auctions("FWD")
print(a.tail(3).T)
print(a.groupby("std_term").size())
a = a[a.auction_date >= "2010-01-01"]
cal = E.trading_calendar("FWD")
ai = cal.searchsorted(a.auction_date.values); ni = cal.searchsorted(a.announcemt_date.values)
a = a.assign(lag=ai-ni, dom=a.auction_date.dt.day, oncal=cal[np.clip(ai,0,len(cal)-1)]==a.auction_date.values)
print("not on cal", (~a.oncal).sum())
print(a.groupby("std_term").lag.describe())
a["tom"] = (a.dom >= 25) | (a.dom <= 5)
print(a.groupby("std_term").tom.mean())
print(a.groupby(["std_term", a.auction_date.dt.year]).size().unstack(0).fillna(0).astype(int))
print(a.groupby("std_term").reopening.value_counts().unstack().fillna(0))
fd = pd.read_parquet(os.environ["GQH_DATA_DIR"] + "/futures_daily.parquet")
print(fd.columns.tolist()); print(fd.groupby("ticker").date.agg(["min","max","count"]))
f16 = pd.read_parquet(os.environ["GQH_DATA_DIR"] + "/futures_1600.parquet")
print(f16.groupby("ticker").date.agg(["min","max","count"]))
