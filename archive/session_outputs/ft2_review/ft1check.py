import sys
sys.path.insert(0, r"<solo-repo>")
import pandas as pd, numpy as np
from src import forward as F, engine as E
p = F.positions_for_next_session("F3", "FWD", [])
f = pd.read_csv(r"<solo-repo>/forward/positions_for_2026-10-06.csv")
f = f[f.strategy == "F3"].set_index("instrument")["weight_of_nav"]
j = pd.concat([p.round(6).rename("now"), f.rename("file")], axis=1)
print("FT1 F3 positions vs file: max|diff|", float((j.now - j.file).abs().max()), "symdiff", sorted(set(p.index) ^ set(f.index)))
# zero-volume runs for LE/HE/ES
o = E.load_ohlc(["F_LE", "F_HE", "F_ES", "F_CL"], "FWD")
for t in ["F_LE", "F_ES", "F_CL"]:
    v = o["volume"][t].dropna(); z = v[v == 0]
    print(t, "zero-volume dates:", [str(d.date()) for d in z.index])
