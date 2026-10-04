"""Runs trend_momentum_carver_ewmac_breakout and trend_momentum_carver_staunch_trend_carry as their SPEC.md declare."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import carver_lib as CL  # noqa: E402
import common as K  # noqa: E402
from run_tsmom import aqr_check  # noqa: E402

BT = K.BT
CARVER_LIVE = {  # UK tax year (Apr-Apr) -> account return, net, from qoppac.blogspot.com 2025-04
    "2014/15": 0.595, "2015/16": 0.281, "2016/17": 0.024, "2017/18": 0.020, "2018/19": 0.045, "2019/20": 0.338,
    "2020/21": -0.017, "2021/22": 0.258, "2022/23": -0.076, "2023/24": 0.206, "2024/25": -0.147}


def tax_year_table(res: dict) -> dict:
    x = res["df"]["net_1x"]
    rows = {}
    for lab in CARVER_LIVE:
        y0 = int(lab[:4])
        s = x.loc[pd.Timestamp(f"{y0}-04-06"):pd.Timestamp(f"{y0 + 1}-04-05")]
        rows[lab] = float((1 + s).prod() - 1) if len(s) > 200 else float("nan")
    ours = pd.Series(rows)
    live = pd.Series(CARVER_LIVE)
    j = pd.concat([ours.rename("ours"), live.rename("carver")], axis=1).dropna()
    return {"tax_years_ours_excess": {k: round(v, 4) for k, v in rows.items()},
            "tax_years_corr_with_carver_live": float(j["ours"].corr(j["carver"])),
            "tax_years_rank_corr": float(j["ours"].rank().corr(j["carver"].rank())),
            "tax_years_ours_sharpe_like": float(j["ours"].mean() / j["ours"].std()),
            "tax_years_carver_sharpe_like": float(j["carver"].mean() / j["carver"].std())}


def run_variants(sid: str, variants: dict, rule_text: dict, sources: list, source_reported: str, extra: dict) -> dict:
    folder = BT / sid
    out = {}
    for name, (w_dec, info) in variants.items():
        res = K.simulate_all(w_dec)
        m = K.metrics(res)
        m.update(aqr_check(res))
        m.update(tax_year_table(res))
        m.update(info)
        K.save_variant(folder, name, res)
        out[name] = (res, m)
        print(sid, name, K.fmt(m))
        print("   FDM mean IS", round(info.get("fdm_mean_is", float("nan")), 3), "| AQR same months IS",
              f"{m.get('aqr_tsmom_gross_sharpe_is', float('nan')):.2f} ours {m.get('ours_gross_monthly_sharpe_is', float('nan')):.2f} "
              f"corr {m.get('corr_monthly_is', float('nan')):.2f} | tax-year corr with Carver live "
              f"{m['tax_years_corr_with_carver_live']:.2f} (rank {m['tax_years_rank_corr']:.2f})")
        print("   tax years ours:", m["tax_years_ours_excess"])
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
        "cost_bps_one_way": K.COST, "exec": "next_close, daily decisions with 10% buffer",
        "vol": "book scaled to 10% ex-ante daily (trailing 252d cov), gross<=3",
        "spec": str(folder / "SPEC.md"), "script": str(Path(__file__).resolve()),
    }
    sidecar.update(extra)
    K.save_headline(sid, res, sidecar)
    summary = {k: v[1] for k, v in out.items()}
    summary["_headline"] = head
    (folder / "results.json").write_text(json.dumps(summary, indent=2, default=str))
    return summary


def build(forecasts: dict, weights: dict, fdm) -> tuple[pd.DataFrame, dict]:
    fdm_s = CL.fdm_trailing(forecasts, weights) if fdm == "trailing" else fdm
    comb = CL.combine(forecasts, weights, fdm_s)
    w, k = CL.positions(comb)
    isl = slice("2011-08-01", "2024-10-02")
    info = {"fdm_mean_is": float(fdm_s.loc[isl].mean()) if isinstance(fdm_s, pd.Series) else float(fdm_s),
            "fdm_last": float(fdm_s.dropna().iloc[-1]) if isinstance(fdm_s, pd.Series) else float(fdm_s),
            "mean_abs_comb_forecast_is": float(comb.loc[isl].abs().stack().mean()),
            "book_scale_median_is": float(k.loc[isl].median())}
    return w, info


def main():
    ew = {f"ewmac{f}_{s}": CL.ewmac(f, s) for (f, s) in CL.EWMAC_SCALARS}
    bo = {f"breakout{n}": CL.breakout(n) for n in CL.BREAKOUT_SCALARS}
    car = CL.carry()

    # ---------------------------------------------------------------- EWMAC + breakout
    v1 = build(ew, {k: 1.0 for k in ew}, "trailing")
    v2 = build(bo, {k: 1.0 for k in bo}, "trailing")
    allr = {**ew, **bo}
    v3 = build(allr, {k: 1.0 for k in allr}, "trailing")
    rules = {
        "V1": "EWMAC 8/32,16/64,32/128,64/256 (scalars 5.3/3.75/2.65/1.87), equal weights, trailing pooled FDM; "
              "w=(F/10)*0.10/sigma/N, book to 10% daily, 10% buffer, next_close",
        "V2": "Breakout 20/40/80/160/320 (scalars 0.67/0.70/0.73/0.74/0.74), equal weights, trailing FDM; as V1",
        "V3": "All nine rules equal weights, trailing FDM; as V1",
    }
    run_variants("trend_momentum_carver_ewmac_breakout", {"V1": v1, "V2": v2, "V3": v3}, rules,
                 ["https://raw.githubusercontent.com/robcarver17/pysystemtrade/master/systems/provided/futures_chapter15/futuresconfig.yaml",
                  "https://github.com/robcarver17/pysystemtrade",
                  "https://qoppac.blogspot.com/2025/04/annual-performance-update-returneth.html"],
                 "Carver live futures account net 2014/15-2024/25: mean 12.9%, sd 16.8%, Sharpe 0.76 (rf=0), CAGR 12.0% "
                 "vs SG CTA 6.4%; live system also has carry/relative-value rules on 100+ instruments",
                 {"carver_live_tax_years": CARVER_LIVE})

    # ---------------------------------------------------------------- staunch: EWMAC + carry
    st = {"ewmac16_64": ew["ewmac16_64"], "ewmac32_128": ew["ewmac32_128"], "ewmac64_256": ew["ewmac64_256"],
          "carry": car}
    w_cfg = {"ewmac16_64": 0.21, "ewmac32_128": 0.08, "ewmac64_256": 0.21, "carry": 0.50}
    s1 = build(st, w_cfg, 1.31)
    s2 = build(st, {k: 0.25 for k in st}, "trailing")
    tr = {k: st[k] for k in ("ewmac16_64", "ewmac32_128", "ewmac64_256")}
    s3 = build(tr, {"ewmac16_64": 0.42, "ewmac32_128": 0.16, "ewmac64_256": 0.42}, "trailing")
    rules_s = {
        "V1": "pysystemtrade chapter-15 config: EWMAC16/64 0.21, 32/128 0.08, 64/256 0.21, carry (ewm com 90, scalar 30) "
              "0.50, FDM 1.31, cap 20; w=(F/10)*0.10/sigma/N, book to 10% daily, 10% buffer, next_close",
        "V2": "Equal 0.25 weights on the four rules, trailing pooled FDM; as V1",
        "V3": "Trend-only part of V1 (EWMAC weights 0.42/0.16/0.42), trailing FDM; as V1",
    }
    summ = run_variants("trend_momentum_carver_staunch_trend_carry", {"V1": s1, "V2": s2, "V3": s3}, rules_s,
                        ["https://raw.githubusercontent.com/robcarver17/pysystemtrade/master/systems/provided/futures_chapter15/futuresconfig.yaml",
                         "https://qoppac.blogspot.com/2025/04/annual-performance-update-returneth.html",
                         "https://github.com/robcarver17/pysystemtrade"],
                        "Carver live account (net, 2014/15-2024/25, Sharpe 0.76 rf=0, CAGR 12.0%); config is his "
                        "published 6-instrument example system",
                        {"carver_live_tax_years": CARVER_LIVE,
                         "carry_source": "edges/carry/contracts.parquet (Databento .v.0/.v.1 closes + free symbology)"})
    # carry contribution: V1 vs V3
    a = pd.read_parquet(BT / "trend_momentum_carver_staunch_trend_carry" / "variants" / "V1.parquet")["net_1x"]
    b = pd.read_parquet(BT / "trend_momentum_carver_staunch_trend_carry" / "variants" / "V3.parquet")["net_1x"]
    j = pd.concat([a.rename("v1"), b.rename("v3")], axis=1).dropna().loc[:"2024-10-02"]
    print("staunch V1 vs V3 (IS): corr", round(float(j.corr().iloc[0, 1]), 3), "Sharpe V1",
          round(K.sharpe(j["v1"]), 3), "V3", round(K.sharpe(j["v3"]), 3))


if __name__ == "__main__":
    main()
