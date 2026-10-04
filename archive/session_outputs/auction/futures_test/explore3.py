import sys, os, re
sys.path.insert(0, "<solo-repo>")
import pandas as pd, numpy as np
from src.strategies import ifc_treasury as TC
a = TC.load_nominal_auctions("FWD")
def yrs(s):
    y = re.search(r"(\d+)-Year", s); m = re.search(r"(\d+)-Month", s)
    return (int(y.group(1)) if y else 0) + (int(m.group(1)) / 12 if m else 0)
STD = [2, 3, 5, 7, 10, 20, 30]
a["rem"] = a.security_term.map(yrs)
a["term2"] = a.rem.map(lambda y: min(STD, key=lambda t: abs(t - y)))
a = a[a.auction_date >= "2010-01-01"]
print(pd.crosstab(a.std_term, a.term2))
print(a[a.std_term != a.term2][["auction_date","security_term","original_security_term","reopening","offering_amt"]].to_string())
a["ym"] = a.auction_date.dt.to_period("M")
months = pd.period_range("2010-01", "2026-09", freq="M")
for t in STD:
    s = a[a.term2 == t].groupby("ym").size().reindex(months).fillna(0)
    print(t, "months with 0:", [str(m) for m in s[s == 0].index][:40], "months with >1:", [str(m) for m in s[s > 1].index][:20])
raw = pd.read_parquet(os.environ["GQH_DATA_DIR"] + "/treasury_auctions.parquet")
r = raw[(raw.auction_date >= "2017-04-01") & (raw.auction_date <= "2017-05-01")]
print(r[["auction_date","security_type","security_term","original_security_term","high_yield","cusip"]].to_string())
