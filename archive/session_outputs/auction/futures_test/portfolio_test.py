"""Pre-declared portfolio test (SPEC.md s.7): core_ER_6 + auction sleeve at equal risk, using the combine
study's own load()/build(). The chosen variant decides; every other eligible variant is descriptive."""
from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

assert os.environ.get("GQH_OOS_UNLOCK") != "1"
SP = Path("<scratch>")
OUT = SP / "auction" / "futures_test"
SER = SP / "auction" / "series"
spec = importlib.util.spec_from_file_location("combine_mod", SP / "edges" / "combine" / "combine.py")
CB = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CB)

SEL = (pd.Timestamp("2010-06-07"), pd.Timestamp("2020-12-31"))
VAL = (pd.Timestamp("2021-01-01"), pd.Timestamp("2024-10-02"))
FULL = (pd.Timestamp("2010-06-07"), pd.Timestamp("2024-10-02"))
LATER = (pd.Timestamp("2024-10-03"), pd.Timestamp("2026-10-02"))
PRE14 = (pd.Timestamp("2010-06-07"), pd.Timestamp("2013-12-31"))
POST14 = (pd.Timestamp("2014-01-01"), pd.Timestamp("2024-10-02"))
WINDOWS = {"sel": SEL, "val": VAL, "full": FULL, "later": LATER, "pre14": PRE14, "post14": POST14}
CORE = ["rpm_ES_MM", "CAL_TSY_ME_ZN", "S1"]


def sharpe(x):
    x = x.dropna()
    return float(x.mean() / x.std() * math.sqrt(252)) if len(x) > 20 and x.std() > 0 else float("nan")


def mdd(x):
    eq = (1 + x.dropna()).cumprod()
    return float((eq / eq.cummax() - 1).min()) if len(eq) else float("nan")


def stats(ret: pd.DataFrame, start: pd.Timestamp) -> dict:
    d = {}
    for wn, (a, b) in WINDOWS.items():
        a = max(a, start)
        r = ret.loc[a:b]
        if len(r.dropna()) < 40:
            continue
        d[f"{wn}_net1x"] = sharpe(r["net_1x"])
        d[f"{wn}_net2x"] = sharpe(r["net_2x"])
        d[f"{wn}_gross"] = sharpe(r["gross"])
        d[f"{wn}_vol"] = float(r["net_1x"].std() * math.sqrt(252))
        d[f"{wn}_maxdd"] = mdd(r["net_1x"])
        d[f"{wn}_start"] = str(r.index[0].date())
    return d


def main():
    cal, rf, sl, gr, cost, nat, es_ex, s1, f2, extra = CB.load()
    summ = json.loads((OUT / "variants_summary.json").read_text())
    chosen = summ["chosen"]
    core = CB.build(CORE, "ER", 0.06, cal, sl, gr, cost)
    saved = pd.read_parquet(SP / "edges" / "series" / "PORT_core_ER_6.parquet")
    saved.index = pd.to_datetime(saved.index)
    j = pd.concat([core["ret"]["net_1x"], saved["net_1x"]], axis=1, join="inner").dropna()
    check = {"max_abs_diff_vs_saved": float((j.iloc[:, 0] - j.iloc[:, 1]).abs().max()), "n_overlap": int(len(j)),
             "core_build_first": str(core["first"].date()), "saved_first": str(saved.index[0].date())}
    print("core rebuild check:", check)

    rows, ports = [], {}
    for vid, res in summ["variants"].items():
        if res["diagnostic"]:
            continue
        s = pd.read_parquet(SER / f"{vid}.parquet")
        s.index = pd.to_datetime(s.index)
        meta = json.loads((SER / f"{vid}.json").read_text())
        hg = pd.read_parquet(OUT / f"held_gross_{vid}.parquet")["held_gross"]
        hg.index = pd.to_datetime(hg.index)
        sl2, gr2, cost2 = dict(sl), dict(gr), dict(cost)
        sl2["AUC"] = s[["net_1x", "net_2x", "gross"]].reindex(cal)
        gr2["AUC"] = hg.reindex(cal).fillna(0.0)
        cost2["AUC"] = meta["avg_cost_bp"]
        p = CB.build(CORE + ["AUC"], "ER", 0.06, cal, sl2, gr2, cost2)
        # common start: first return day with all four sleeves live (multiplier > 0 for AUC), and not before saved core start
        m_auc = p["m"]["AUC"]
        start = max(m_auc[m_auc.abs() > 0].index[0], saved.index[0])
        ports[vid] = p["ret"]
        st_p = stats(p["ret"], start)
        st_c = stats(core["ret"], start)
        row = {"variant": vid, "chosen": vid == chosen, "start": str(start.date())}
        for k, v in st_p.items():
            row[f"port_{k}"] = v
        for k, v in st_c.items():
            row[f"core_{k}"] = v
        row["mean_auc_weight"] = float(p["m"]["AUC"].loc[start:"2024-10-02"].mean())
        row["cap_bind_share"] = float(p["capbind"].loc[start:"2024-10-02"].mean())
        rows.append(row)
        print(f"{vid:16s} start {start.date()}  port sel {st_p.get('sel_net1x', np.nan):+.2f} val {st_p.get('val_net1x', np.nan):+.2f} "
              f"later {st_p.get('later_net1x', np.nan):+.2f} full {st_p.get('full_net1x', np.nan):+.2f} | core sel {st_c.get('sel_net1x', np.nan):+.2f} "
              f"val {st_c.get('val_net1x', np.nan):+.2f} later {st_c.get('later_net1x', np.nan):+.2f} full {st_c.get('full_net1x', np.nan):+.2f}")
    tab = pd.DataFrame(rows)
    tab.to_csv(OUT / "portfolio_test.csv", index=False)
    pc = pd.concat({k: v for k, v in ports.items()}, axis=1)
    pc.to_parquet(OUT / "portfolio_series.parquet")
    core["ret"].to_parquet(OUT / "core_ER_6_rebuilt.parquet")
    ch = tab[tab["chosen"]].iloc[0].to_dict()
    vres = summ["variants"][chosen]
    adoption = {"a_val_net1x_gt0": vres["val_net1x"] > 0, "b_val_net2x_gt0": vres["val_net2x"] > 0,
                "c_port_val_beats_core": ch["port_val_net1x"] > ch["core_val_net1x"], "sel_nw_t_ge2": vres["nw_t_sel"] >= 2}
    adoption["adopt"] = bool(adoption["a_val_net1x_gt0"] and adoption["b_val_net2x_gt0"] and adoption["c_port_val_beats_core"])
    out = {"chosen": chosen, "core_rebuild_check": check, "chosen_portfolio": ch, "adoption": adoption}
    (OUT / "portfolio_summary.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
