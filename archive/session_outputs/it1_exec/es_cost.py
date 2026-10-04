import pandas as pd, numpy as np
d=pd.read_parquet(r"<home>/.cache/gqh/databento_raw/glbx_ohlcv1d_v01.parquet")
print(d.columns.tolist()); print(d.symbol.unique()[:10])
es=d[d.symbol=="ES.v.0"].copy()
tcol=[c for c in es.columns if "ts" in c or "date" in c.lower()][0]
es["date"]=pd.to_datetime(es[tcol]).dt.tz_localize(None).dt.normalize() if pd.api.types.is_datetime64_any_dtype(es[tcol]) else pd.to_datetime(es[tcol])
es=es.set_index("date").sort_index()
pc=pd.read_excel(r"<scratch>/fedtalk/data_markets/usmpd/USMPD.xlsx", sheet_name="Press Conferences")
pc["date"]=pd.to_datetime(pc["Date"]).dt.normalize()
pc=pc[~pc.date.isin(pd.to_datetime(["2020-03-03","2020-03-15"]))]
px=es["close"].reindex(pc.date, method="ffill")
pc["es"]=px.values
pc["tick_bp"]=0.25/pc.es*1e4
pc["rt_bp"]=17.5/(50*pc.es)*1e4   # 1 tick + $5 fees round trip
pc["yr"]=pc.date.dt.year
pc["SPFUT_bp"]=pc["SPFUT"]*100
g=pc.groupby("yr").agg(n=("es","size"),es=("es","mean"),tick_bp=("tick_bp","mean"),rt_bp=("rt_bp","mean"),sd_presser_bp=("SPFUT_bp","std"),maxabs_bp=("SPFUT_bp",lambda x: x.abs().max()))
g["rt_x23_over_sd"]=g.rt_bp*23/g.sd_presser_bp
print(g.round(2).to_string())
for lo,hi in [(2011,2015),(2016,2023),(2024,2026),(2016,2026)]:
    s=pc[(pc.yr>=lo)&(pc.yr<=hi)]
    print(lo,hi,"n",len(s),"mean RT bp %.2f"%s.rt_bp.mean(),"tick bp %.2f"%s.tick_bp.mean(),"vs plan 0.35-0.5 bp; ratio %.1fx"%(s.rt_bp.mean()/0.45), "presser sd bp %.1f"%s.SPFUT_bp.std())
# largest presser-window moves in $ per ES contract at event-day price and today's
pc["usd_evt"]=pc.SPFUT/100*pc.es*50
top=pc.reindex(pc.SPFUT.abs().sort_values(ascending=False).index)[["date","SPFUT","es","usd_evt"]].head(8)
top["usd_today"]=top.SPFUT/100*7776.5*50
print(top.round(3).to_string())
