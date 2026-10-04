"""V1: independent implementation on their own CSVs vs their equity_is.csv / is_summary.json."""
import json

import numpy as np
import pandas as pd

import vlib as V

out = {}
o = V.their_opens()
sc = V.kept_scores(V.TP / "speech_scores.csv", end=V.IS_END)
fomc = V.their_fomc()
fomc = fomc[fomc <= V.IS_END]
b = V.build(o, sc, fomc)
sa = V.standalone(b)
eq = pd.read_csv(V.THEIR / "outputs" / "equity_is.csv", index_col=0, parse_dates=True)
summ = json.loads((V.THEIR / "outputs" / "is_summary.json").read_text())

idx = eq.index
mine = pd.DataFrame({"C": b["C"], "z": b["z"], "vol_mix": b["vol"], "w_tlt": b["w"]["TLT"], "w_uup": b["w"]["UUP"],
                     "r_gross": sa["gross"], "r_1x": sa["net1"], "r_2x": sa["net2"]}).reindex(idx)
out["daily_maxabsdiff_vs_equity_is"] = {c: float((mine[c] - eq[c]).abs().max()) for c in mine}
r1 = sa["net1"].reindex(idx)
y22 = (idx.year == 2022)
mine_stats = {
    "n_days": len(idx), "first": str(idx[0].date()), "last": str(idx[-1].date()),
    "sharpe_gross": V.sharpe(sa["gross"].reindex(idx)), "sharpe_1x": V.sharpe(r1), "sharpe_2x": V.sharpe(sa["net2"].reindex(idx)),
    "sharpe_tlt_1x": V.sharpe(sa["tlt"].reindex(idx)), "sharpe_uup_1x": V.sharpe(sa["uup"].reindex(idx)),
    "sharpe_2022_1x": V.sharpe(r1[y22]), "sharpe_rest_1x": V.sharpe(r1[~y22]),
    "turnover_ann": float(sa["l1"].reindex(idx).mean() * 252), "n_docs_kept": int(len(sc)),
    "maxdd_1x": V.maxdd(r1),
}
dg = pd.read_csv(V.TP / "fred_DGS2.csv", parse_dates=["date"]).set_index("date")["value"]
dg = dg.reindex(dg.index.union(o.index)).ffill().reindex(o.index).shift(2)
mine_stats["corr_C_DGS2_t2"] = float(pd.concat([b["C"].reindex(idx), dg.reindex(idx)], axis=1).dropna().corr().iloc[0, 1])
out["mine"] = mine_stats
out["theirs"] = {k: summ[k] for k in ("n_is_days", "first_z", "last_ret", "sharpe_gross", "sharpe_1x", "sharpe_2x", "sharpe_tlt_1x",
                                      "sharpe_uup_1x", "sharpe_2022_1x", "sharpe_rest_1x", "turnover_ann", "n_docs_kept", "corr_C_DGS2_tminus2")}
# holdout in their accounting
out["holdout_1x_their_accounting"] = V.sharpe(r1.loc["2021-01-01":])
print(json.dumps(out, indent=1))
(V.HERE / "out").mkdir(exist_ok=True)
(V.HERE / "out" / "v1_reproduce.json").write_text(json.dumps(out, indent=1))
