import sys; sys.path.insert(0, r"<scratch>/auction/verify")
import numpy as np, pandas as pd, vstrat as S
cal, rex, A = S.cal, S.rex, S.A
r = rex["F_ES"].to_numpy()*1e4; z = rex["F_ZT"].to_numpy()*1e4
rows=[]
for e in A[(A.term==2)&(A.auction_date<="2013-12-31")].itertuples():
    lo,hi=e.A-10,e.A+10
    if lo<1: print("skip",e.auction_date.date(),lo); continue
    v=r[lo:hi+1]; rows.append((e.auction_date.date(), v[11:16].sum()-v[6:11].sum(), cal[lo].date(), np.isnan(v).sum(), np.isnan(z[lo:hi+1]).sum()))
d=pd.DataFrame(rows,columns=["A","D5","lo","nanES","nanZT"]); print(len(d)); print(d.head(5).to_string())
for i in range(len(d)):
    m=d.D5.drop(i).mean()
    if abs(m-89.65)<0.5: print("dropping",d.loc[i].to_dict(), m)
print("first ES, ZT valid:", rex["F_ES"].first_valid_index(), rex["F_ZT"].first_valid_index())
