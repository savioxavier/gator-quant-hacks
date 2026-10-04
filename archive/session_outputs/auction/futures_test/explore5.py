import pandas as pd
p = pd.read_parquet("<scratch>/intraday_study/data/hourly_panel.parquet")
print(p.dtypes)
z = p[(p.root == "ZN") & (p.trade_date == "2017-04-11")]
print(z[["bar_start_et","hour_et","trade_date","ret_simple","gap_type","cme_non_nyse_session","volume"]].to_string())
