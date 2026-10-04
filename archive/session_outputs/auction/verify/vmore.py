import sys, math; sys.path.insert(0, r"<scratch>/auction/verify")
import numpy as np, pandas as pd, vstrat as S
cal, rex, A = S.cal, S.rex, S.A
# 1. alignment print: one 2y auction, V1_2y_t10 held weights around it
h = pd.read_parquet(S.V.OUT / "held_V1_2y_t10.parquet")["F_ZT"]
e = A[(A.term == 2) & (A.auction_date == "2019-06-25")].iloc[0]
print("2y 2019-06-25 announced", e.announcemt_date.date(), "N->A sessions", e.A - e.N)
print(h.iloc[e.A - 11:e.A + 12].round(2).to_string())
# 2. sleeve-days long/short at t=10 across maturity sleeves (gated, all auctions)
L = Sh = 0
for m in S.TRADED:
    w = S.sleeve(S.evsel([m]), S.INST[m], None, 10, 10, True, 30 / S.DUR[S.INST[m]])[S.INST[m]][:"2024-10-02"]
    L += int((w > 0).sum()); Sh += int((w < 0).sum())
print("V1_all_t10 sleeve-days long/short to 2024-10-02:", L, Sh)
# 3. V2_2y_t10 with a trailing hedge ratio (252-day OLS beta of ZT on ZN, known at decision date) instead of fixed durations
beta = (rex.F_ZT.rolling(252, min_periods=126).cov(rex.F_ZN) / rex.F_ZN.rolling(252, min_periods=126).var()).shift(0)
held_fixed = pd.read_parquet(S.V.OUT / "held_V2_2y_t10.parquet")
zt = held_fixed.F_ZT
# hedge decided at close t-2 for return day t
hz = -zt * beta.shift(2)
hv = held_fixed.copy(); hv["F_ZN"] = hz.fillna(0.0)
print("fixed hedge ratio 1.9/6.3 =", round(1.9/6.3,3), "; trailing beta median", round(beta.median(),3), "range", round(beta.quantile(.05),3), round(beta.quantile(.95),3))
st, _ = S.stats_of(hv)
print("V2_2y_t10 trailing-beta hedge:", {k: round(v, 3) for k, v in st.items() if k.endswith(("n1", "n2")) or k.startswith("nw")})
