import sys; sys.path.insert(0, r"<scratch>/auction/verify")
sys.path.insert(0, "<solo-repo>")
import numpy as np, pandas as pd
import vdata as V
from src.strategies import ifc_treasury as TC
cal, rex, roll, rf = V.returns()
print("cal", cal[0], cal[-1], len(cal))
a = V.auctions()
a, calx = V.index_events(a, cal)
b = TC.load_nominal_auctions("FWD")
b["yrs"] = b.security_term.map(V.term_years); b["term"] = b.yrs.map(lambda y: min(V.STD, key=lambda t: abs(t-y)))
b = b.drop_duplicates(["term","auction_date"])
ka = set(zip(a.term, a.auction_date)); kb = set(zip(b.term, b.auction_date))
print("mine", len(ka), "analyst loader", len(kb), "only mine", sorted(ka-kb)[:20], "only theirs", sorted(kb-ka)[:20])
s = a[a.auction_date >= "2010-06-01"]
print(s.groupby("term").size().to_dict())
print("off-calendar since 2009:", s[~s.on][["auction_date","term"]].to_string())
s = s.assign(lag=s.A - s.N)
print(s.groupby("term").lag.describe()[["min","25%","50%","75%","max"]])
print("tom share by term:", s.groupby("term").tom.mean().round(2).to_dict())
print("2y with security_term != original:", s[(s.term==2)&(s.oterm!=2)][["auction_date","security_term","original_security_term"]].head(25).to_string())
