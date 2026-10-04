"""Collect headline metrics for the four bt_3 strategies into results.json and add source numbers to sidecars."""
import json
from pathlib import Path

B = Path(__file__).resolve().parent
S = B.parent / "series"
SRC = {
    "trend_momentum_commodity_xsmom": "Miffre-Rallis 2007 (31 commodities, 1979-2004, gross): 12m/1m long-short 14.6%/yr, vol 25.6% (Sharpe ~0.57); Hollstein et al. 2021: 1-yr momentum 7.44%/yr full sample, much attenuated post-2004; AQR VME commodity momentum Sharpe 0.52 (1972-2011) vs -0.20 post-publication; AQR Century commodities momentum -0.02 (2012-2026).",
    "trend_momentum_basis_momentum": "Boons & Porras Prado 2019 (21 commodities, 1960-08..2014-02, gross): High4-Low4 nearby return 18.38%/yr (t 6.73), Sharpe about 0.9, robust pre/post 1986; no post-2014 replication found.",
    "trend_momentum_fx_xsmom": "Menkhoff-Sarno-Schmeling-Schrimpf 2012 (up to 48 currencies, 1976-2010): winner-loser up to ~10%/yr gross, best ~4%/yr after costs, weakest in developed currencies; AQR VME FX momentum Sharpe 0.33 (1972-2011) vs -0.04 post-publication; Century currencies momentum -0.14 (2012-2026).",
    "trend_momentum_sector_rs": "Faber 2010 (French 10 industries 1928-2009): rotation beats buy-and-hold in ~70% of years; hunt calc (French 10 VW, gross): top3 minus EW10 Sharpe 0.43 (1928-2009), 0.30 (2010-01..2026-08), 0.47 (2016-01..2024-09); top3 excess Sharpe 0.82 vs EW10 0.70 over 2003-2024-09.",
}
out = {}
for sid, src in SRC.items():
    m = json.loads((B / sid / "metrics.json").read_text())
    head = m["headline"]
    side_p = S / f"{sid}.json"
    side = json.loads(side_p.read_text())
    side["source_reported"] = src
    side_p.write_text(json.dumps(side, indent=2))
    st = m["stats"]
    out[sid] = {"headline": head, "start": m["start"], "source_reported": src,
                "headline_IS": {k: v for k, v in st[head]["IS"].items()},
                "headline_LATER": {k: v for k, v in st[head]["LATER"].items() if k != "yearly"},
                "variants": {v: {"IS_net1x": st[v]["IS"]["sharpe_net_1x"], "IS_net2x": st[v]["IS"]["sharpe_net_2x"],
                                 "IS_gross": st[v]["IS"]["sharpe_gross"], "LATER_net1x": st[v]["LATER"]["sharpe_net_1x"],
                                 "IS_maxdd": st[v]["IS"]["max_dd"]} for v in st}}
(B / "results.json").write_text(json.dumps(out, indent=2, default=float))
for sid, o in out.items():
    h = o["headline_IS"]
    print(sid, o["headline"], o["start"])
    print("  IS", {k: round(h[k], 3) for k in ("sharpe_net_1x", "sharpe_net_2x", "sharpe_gross", "ann_return", "ann_vol", "max_dd", "worst_year", "pct_pos_years", "roll2y_p10", "turnover_per_year", "nw_t", "corr_ES", "corr_S1", "corr_F2")}, h["worst_year_label"])
    l = o["headline_LATER"]
    print("  LATER", round(l["sharpe_net_1x"], 3), round(l["max_dd"], 3))
    print("  variants", {k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in o["variants"].items()})
    print("  yearly IS", h["yearly"])
