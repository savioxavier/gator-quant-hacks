"""ES vs 2-year yield co-movement in USMPD press-conference windows, by period."""
import pandas as pd, numpy as np
f=r"<scratch>/fedtalk/data_markets/usmpd/USMPD.xlsx"
pc=pd.read_excel(f, sheet_name="Press Conferences"); pc["date"]=pd.to_datetime(pc.Date)
pc=pc[~pc.date.dt.strftime("%Y-%m-%d").isin(["2020-03-03","2020-03-15"])]; pc["yr"]=pc.date.dt.year
for lo,hi in [(2011,2015),(2016,2018),(2019,2021),(2022,2023),(2024,2026),(2016,2023)]:
    s=pc[(pc.yr>=lo)&(pc.yr<=hi)]
    print(lo,hi,"n",len(s),"corr(SPFUT,UST2Y) %.2f"%s[["SPFUT","UST2Y"]].corr().iloc[0,1],"corr(SPFUT,ED4) %.2f"%s[["SPFUT","ED4"]].corr().iloc[0,1])
pc=pc.sort_values("date"); r=pc.SPFUT.rolling(8).corr(pc.UST2Y)
print("share of trailing 8-event windows with corr>0 since 2016: %.2f (min %.2f, max %.2f)"%((r[pc.yr>=2016]>0).mean(), r[pc.yr>=2016].min(), r[pc.yr>=2016].max()))
