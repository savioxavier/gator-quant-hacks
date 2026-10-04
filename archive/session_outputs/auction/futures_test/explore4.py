import sys, os, re
sys.path.insert(0, "<solo-repo>")
import pandas as pd, numpy as np
from src import engine as E
from src.strategies import ifc_treasury as TC
a = TC.load_nominal_auctions("FWD")
def yrs(s):
    y = re.search(r"(\d+)-Year", s); m = re.search(r"(\d+)-Month", s)
    return (int(y.group(1)) if y else 0) + (int(m.group(1)) / 12 if m else 0)
STD = [2, 3, 5, 7, 10, 20, 30]
a["term2"] = a.security_term.map(yrs).map(lambda y: min(STD, key=lambda t: abs(t - y)))
a = a[a.auction_date >= "2010-01-01"].copy()
cal = E.trading_calendar("FWD")
pos = pd.Series(np.arange(len(cal)), index=cal)
ai = cal.searchsorted(a.auction_date.values)
a["ai"] = ai
# month-end offset (trading days to last trading day of month), and day-of-month position from month start
me = pd.Series(cal, index=cal).groupby(cal.to_period("M")).transform("max")
ms = pd.Series(cal, index=cal).groupby(cal.to_period("M")).transform("min")
a["off_me"] = [pos[me[d]] - pos[d] for d in a.auction_date]
a["off_ms"] = [pos[d] - pos[ms[d]] for d in a.auction_date]
for t in STD:
    s = a[a.term2 == t].sort_values("auction_date")
    s = s[~s.auction_date.duplicated()]
    print(t, "same me-offset as prev:", round((s.off_me.diff() == 0).mean(), 2), " same ms-offset:", round((s.off_ms.diff() == 0).mean(), 2),
          "me-off dist", s.off_me.value_counts().head(5).to_dict(), "ms-off", s.off_ms.value_counts().head(5).to_dict())
# Distance between consecutive auctions of same maturity (trading days)
for t in STD:
    s = a[a.term2 == t].sort_values("ai")
    print(t, "gap td", s.ai.diff().describe()[["min","25%","50%","max"]].to_dict())
