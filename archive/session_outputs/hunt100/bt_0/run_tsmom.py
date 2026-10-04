"""Runs trend_momentum_mop_tsmom12 and trend_momentum_hop_1_3_12 exactly as their SPEC.md files declare."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as K  # noqa: E402
import tsmom_lib as T  # noqa: E402

BT = K.BT


def aqr_check(res: dict) -> dict:
    a = K.aqr_tsmom_monthly()
    if a is None:
        return {}
    x = res["df"]["gross"]
    start = res["start"]
    m = (1 + x).resample("ME").prod() - 1
    m.index = m.index.to_period("M")
    # full months only: first full month after the start, through 2024-09 for IS
    first_full = (start + pd.offsets.MonthBegin(1)).to_period("M")
    is_m = m.loc[first_full:pd.Period("2024-09", "M")]
    lat_m = m.loc[pd.Period("2024-10", "M"):]
    j_is = pd.concat([is_m.rename("ours"), a.rename("aqr")], axis=1, join="inner").dropna()
    j_lat = pd.concat([lat_m.rename("ours"), a.rename("aqr")], axis=1, join="inner").dropna()
    sr = lambda s: float(s.mean() / s.std() * np.sqrt(12))  # noqa: E731
    return {
        "aqr_window_is": f"{j_is.index[0]}..{j_is.index[-1]}",
        "aqr_tsmom_gross_sharpe_is": sr(j_is["aqr"]),
        "ours_gross_monthly_sharpe_is": sr(j_is["ours"]),
        "corr_monthly_is": float(j_is["ours"].corr(j_is["aqr"])),
        "aqr_window_later": f"{j_lat.index[0]}..{j_lat.index[-1]}" if len(j_lat) else "",
        "aqr_tsmom_gross_sharpe_later": sr(j_lat["aqr"]) if len(j_lat) > 2 else float("nan"),
        "ours_gross_monthly_sharpe_later": sr(j_lat["ours"]) if len(j_lat) > 2 else float("nan"),
        "corr_monthly_later": float(j_lat["ours"].corr(j_lat["aqr"])) if len(j_lat) > 2 else float("nan"),
    }


def run(sid: str, variants: dict, sources: list, rule_text: dict, source_reported: str) -> dict:
    folder = BT / sid
    out = {}
    for name, w in variants.items():
        res = K.simulate_all(w)
        m = K.metrics(res)
        m.update(aqr_check(res))
        K.save_variant(folder, name, res)
        out[name] = (res, m)
        print(sid, name, K.fmt(m))
        if "aqr_tsmom_gross_sharpe_is" in m:
            print("   AQR TSMOM same months: IS", m["aqr_window_is"], f"AQR {m['aqr_tsmom_gross_sharpe_is']:.2f} ours(gross, monthly) "
                  f"{m['ours_gross_monthly_sharpe_is']:.2f} corr {m['corr_monthly_is']:.2f} | later AQR "
                  f"{m['aqr_tsmom_gross_sharpe_later']:.2f} ours {m['ours_gross_monthly_sharpe_later']:.2f} corr {m['corr_monthly_later']:.2f}")
    head = max(out, key=lambda k: out[k][1]["is_net_sharpe_1x"])
    res, m = out[head]
    sidecar = {
        "id": sid, "headline_variant": head, "rule": rule_text[head], "all_variants": rule_text,
        "selection": "headline = highest in-sample net Sharpe (1x) of 3 pre-declared variants",
        "sources": sources, "source_reported": source_reported,
        "window": {"is_start": str(res["start"].date()), "is_end": "2024-10-02",
                   "later": "2024-10-03..2026-10-02 (descriptive)"},
        "columns": {"net_1x": "daily excess return over T-bill, realistic cost map",
                    "net_2x": "same at 2x costs", "gross": "before costs"},
        "cost_bps_one_way": K.COST, "exec": "next_close", "vol": "book scaled to 10% ex-ante (trailing 252d cov)",
        "spec": str(folder / "SPEC.md"), "script": str(Path(__file__).resolve()),
    }
    K.save_headline(sid, res, sidecar)
    summary = {k: v[1] for k, v in out.items()}
    summary["_headline"] = head
    (folder / "results.json").write_text(json.dumps(summary, indent=2, default=str))
    return summary


def main():
    P = K.panel()
    cal = P["ex"].index
    me = K.month_ends(cal)
    we = K.week_ends(cal)

    # ---------------------------------------------------------------- MOP
    mop = {
        "V1": T.decisions(me, T.sig_sign(252)),
        "V2": T.decisions(me, T.sig_sign(252, skip=21)),
        "V3": T.decisions(me, T.sig_sign(252), vol_scaled=False),
    }
    mop_rules = {
        "V1": "Month-end s_i = sign(12-month (252-session) cumulative excess return); w_i = s_i*0.40/sigma_i/N "
              "(sigma EWMA com 60); book to 10% ex-ante (252d cov), gross<=3; next_close",
        "V2": "As V1 with skip-month 12-1 signal (sessions t-252..t-21)",
        "V3": "As V1 without vol scaling: w_i = s_i/N equal notional, then book to 10%",
    }
    run("trend_momentum_mop_tsmom12", mop,
        ["https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf",
         "https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Time-Series-Momentum-Factors-Monthly.xlsx",
         "https://www.aqr.com/Insights/Research/Journal-Article/Demystifying-Managed-Futures"],
        mop_rules,
        "MOP 2012 58 futures 1985-2009 strongly significant; AQR TSMOM factor gross Sharpe 1.41 1985-2009, 0.39 "
        "2012-05..2026-05, 0.03 2016-01..2024-09, 0.97 2024-10..2026-05; AQMIX ~0.26 net since 2010; SG Trend 0.30 net")

    # ---------------------------------------------------------------- HOP
    s1 = F2M_s1()
    mine = T.decisions(me, T.sig_blend_sign())
    diff = float((s1 - mine.reindex_like(s1)).abs().max().max())
    print("HOP V1 cross-check: max |forward2.s1_decisions - re-implementation| =", diff)
    hop = {
        "V1": s1,
        "V2": T.decisions(we, T.sig_blend_sign()),
        "V3": T.decisions(me, T.sig_blend_cont()),
    }
    hop_rules = {
        "V1": "Month-end s_i = mean(sign R_21, sign R_63, sign R_252); w_i = s_i*0.40/sigma_i/N; book to 10%, "
              "gross<=3, next_close (= forward2.s1_decisions) with the realistic cost map",
        "V2": "As V1 with weekly decisions (last NYSE session of each week)",
        "V3": "As V1 with continuous horizon signals clip(R_h/(sigma_daily*sqrt(h)), -1, 1)",
    }
    run("trend_momentum_hop_1_3_12", hop,
        ["https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/AQR-JPM-Fall-2017.pdf",
         "https://www.aqr.com/Insights/Research/Journal-Article/Demystifying-Managed-Futures",
         "https://www.aqr.com/Insights/Research/Journal-Article/You-Cant-Always-Trend-When-You-Want",
         "https://invesco.com/content/dam/invesco/emea/en/pdf/RRE_2024_Q2_NavigatingMomentum.pdf"],
        hop_rules,
        "HOP 2017 67 markets 1880-2016 ~0.76-0.77 net of costs and 2/20 fees, positive every decade, ~0.41 2010-16; "
        "Babu et al. 2020 ~0.32 2010-18; SG Trend 0.30 net 1999-2024; BTOP50 0.50 net 1987-2012")


def F2M_s1():
    from src import forward2 as F2M
    return F2M.s1_decisions("FWD").reindex(columns=K.TICK)


if __name__ == "__main__":
    main()
