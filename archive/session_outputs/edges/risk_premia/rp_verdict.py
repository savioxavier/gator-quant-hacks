"""Apply the pre-registered verdict rule (SPEC.md section 7) mechanically and merge all 36 variants into one table."""
from __future__ import annotations

import pandas as pd

import rp_core as R

PROXY = {"STATIC": "STATIC", "CV": "CV", "CVB": "CV", "MM": "MM", "FB": "FB", "FBB": "FB"}
PROXY_SLEEVE = {"ES": "EQ", "ZN": "BOND", "SB": "SB", "GC": None}


def main() -> None:
    ft = pd.read_csv(R.OUT / "futures_table.csv")
    lh = pd.read_csv(R.OUT / "longhist_table.csv")
    rows = []
    for name in ft["name"].unique():
        f = ft[ft.name == name].set_index("window")
        _, s, ov = name.split("_", 2)
        IS, A, B, L = f.loc["IS"], f.loc["A"], f.loc["B"], f.loc["LATER"]
        ps = PROXY_SLEEVE[s]
        proxy_name = f"LH_{ps}_{PROXY[ov]}" if ps else None
        proxy_sr = float(lh[(lh.name == proxy_name) & (lh.window == "IS_full")]["sharpe_net1"].iloc[0]) if ps else float("nan")
        real = (IS.nw_t >= 2.0 and IS.sharpe_net2 > 0 and A.sharpe_net1 > 0 and B.sharpe_net1 > 0
                and IS.pct_positive_years >= 0.6 and (proxy_sr > 0.2 if ps else True))
        fails = IS.sharpe_net1 <= 0.1 or IS.nw_t < 1.0
        verdict = "real_edge" if real else ("fails" if fails else "weak_or_uncertain")
        rows.append({"name": name, "verdict": verdict, "is_sharpe_net1": IS.sharpe_net1, "is_sharpe_net2": IS.sharpe_net2,
                     "is_sharpe_gross": IS.sharpe_gross, "is_nw_t": IS.nw_t, "A_sharpe": A.sharpe_net1, "B_sharpe": B.sharpe_net1,
                     "is_pct_pos_years": IS.pct_positive_years, "is_max_dd": IS.max_dd, "is_worst_year": IS.worst_year,
                     "is_2022": IS.ret_2022, "is_roll2y_p10": IS.roll2y_p10, "is_roll2y_p50": IS.roll2y_p50,
                     "is_roll2y_p90": IS.roll2y_p90, "proxy": proxy_name, "proxy_is_sharpe": proxy_sr,
                     "later_sharpe_net1": L.sharpe_net1, "later_max_dd": L.max_dd})
    v = pd.DataFrame(rows)
    v.to_csv(R.OUT / "verdicts.csv", index=False)

    # overlay value test (SPEC 7, last bullet), futures IS and long-history full IS
    bs = pd.read_csv(R.OUT / "bootstrap_is.csv")
    lb = pd.read_csv(R.OUT / "longhist_bootstrap.csv")
    ov_rows = []
    for src, df in (("futures_IS", bs[bs.sleeve != "cross"]), ("longhist_IS_full", lb[(lb.sleeve != "cross") & (lb.window == "IS_full")]),
                    ("longhist_post_2016", lb[(lb.sleeve != "cross") & (lb.window == "post_2016")])):
        for _, r in df.iterrows():
            dd_cut = 1 - r.mdd_a / r.mdd_b if r.mdd_b < 0 else float("nan")
            adds = (r.p_two_sided < 0.05 and r.d_sharpe > 0) or (dd_cut >= 0.25 and r.d_sharpe >= -0.1)
            ov_rows.append({"source": src, "sleeve": r.sleeve, "overlay": r.a, "vs": r.b, "d_sharpe": r.d_sharpe,
                            "ci_lo": r.ci_lo, "ci_hi": r.ci_hi, "p": r.p_two_sided, "mdd_overlay": r.mdd_a,
                            "mdd_base": r.mdd_b, "dd_cut": dd_cut, "adds_value": adds})
    pd.DataFrame(ov_rows).to_csv(R.OUT / "overlay_value.csv", index=False)

    ft2 = ft.assign(source="futures")
    lh2 = lh.assign(source="longhist_proxy")
    allv = pd.concat([ft2, lh2], ignore_index=True, sort=False)
    allv = allv[["source", "name", "window"] + [c for c in allv.columns if c not in ("source", "name", "window")]]
    allv.to_csv(R.OUT / "all_variants.csv", index=False)
    print("variants:", ft.name.nunique(), "futures +", lh.name.nunique(), "proxy")
    with pd.option_context("display.width", 250, "display.max_rows", 200):
        print(v.round(3).to_string(index=False))
        print(pd.DataFrame(ov_rows).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
