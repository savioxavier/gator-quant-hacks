import sys, os
sys.path.insert(0, "<solo-repo>")
import pandas as pd, numpy as np
raw = pd.read_parquet(os.environ["GQH_DATA_DIR"] + "/treasury_auctions.parquet")
print(raw.columns.tolist())
r = raw[(raw.security_type.isin(["Note","Bond"])) & (raw.auction_date.dt.year.isin([2015,2017,2019]))]
pd.set_option("display.width", 250, "display.max_rows", 500)
cols = ["auction_date","announcemt_date","security_type","security_term","original_security_term","high_yield","offering_amt","reopening","cusip"]
x = r[r.original_security_term.str.contains("2-Year|5-Year")][cols].sort_values("auction_date")
print(x.to_string())
