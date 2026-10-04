"""Post-hoc data-construction check for basis-momentum (SPEC.md addendum). Not a variant; never the headline."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import common as K  # noqa: E402
import run_bt3 as R  # noqa: E402


def r2_fixed(px: pd.DataFrame, mi: pd.DataFrame) -> tuple[pd.Series, pd.Series, dict]:
    """px rows (date, rank, instrument_id, close); mi: (date, rank) -> month_index. Returns r1, r2fix on CME dates."""
    px = px.merge(mi, on=["date", "rank"], how="left")
    by_day_id = px.set_index(["date", "instrument_id"])["close"]
    by_day_id = by_day_id[~by_day_id.index.duplicated(keep="last")]
    p0 = px[px["rank"] == 0].set_index("date").sort_index()
    p1 = px[px["rank"] == 1].set_index("date").sort_index()
    dates = p0.index
    prev_dates = pd.Series(dates).shift(1).values
    r1, r2 = [], []
    valid = 0
    for d, pdte in zip(dates, prev_dates):
        c0, id0, m0 = p0.at[d, "close"], p0.at[d, "instrument_id"], p0.at[d, "month_index"]
        if pd.isna(pdte):
            r1.append(0.0)
            r2.append(0.0)
            continue
        pv0 = by_day_id.get((pdte, id0), np.nan)
        a = c0 / pv0 - 1.0 if (np.isfinite(pv0) and pv0 > 0 and c0 > 0) else 0.0
        b = a
        if d in p1.index:
            c1, id1, m1 = p1.at[d, "close"], p1.at[d, "instrument_id"], p1.at[d, "month_index"]
            pv1 = by_day_id.get((pdte, id1), np.nan)
            if (np.isfinite(m0) and np.isfinite(m1) and m1 > m0 and np.isfinite(pv1) and pv1 > 0 and c1 > 0):
                b = c1 / pv1 - 1.0
                valid += 1
        r1.append(a)
        r2.append(b)
    return pd.Series(r1, index=dates), pd.Series(r2, index=dates), {"days": len(dates), "valid_far_days": valid}


def main() -> None:
    refs = K.references()
    tk = [f"F_{r}" for r in K.COMM]
    P = K.futures_panel(tk)
    ex, sigma, elig, cal = P["ex"], P["sigma"], P["elig"], P["cal"]
    raw = pd.read_parquet(R.RAW)
    raw["date"] = pd.to_datetime(raw["ts_event"]).dt.tz_convert("UTC").dt.tz_localize(None).dt.normalize()
    raw = raw[raw["date"].dt.dayofweek < 5]
    raw["root"] = raw["symbol"].str.split(".").str[0]
    raw["rank"] = raw["symbol"].str.split(".").str[2].astype(int)
    con = pd.read_parquet(R.CONTRACTS)
    r1, r2, diag = {}, {}, {}
    for root in K.COMM:
        px = raw[raw["root"] == root][["date", "rank", "instrument_id", "close"]].drop_duplicates(["date", "rank"], keep="last")
        mi = con[con["root"] == root][["date", "rank", "month_index"]].drop_duplicates(["date", "rank"])
        a, b, dg = r2_fixed(px, mi)
        r1[f"F_{root}"] = R._to_nyse(a, cal)
        r2[f"F_{root}"] = R._to_nyse(b, cal)
        diag[root] = dg
    r1, r2 = pd.DataFrame(r1), pd.DataFrame(r2)
    dates = K.month_ends(cal)
    bm_fix = pd.DataFrame(np.nan, index=dates, columns=tk)
    mom = pd.DataFrame(np.nan, index=dates, columns=tk)
    for t in dates:
        n_obs = r1.loc[:t].notna().sum()
        v = (1 + r1.loc[:t].tail(252)).prod() - (1 + r2.loc[:t].tail(252)).prod()
        v[n_obs < 252] = np.nan
        bm_fix.loc[t] = v.values
        mom.loc[t] = ((1 + ex.loc[:t].tail(252).fillna(0.0)).prod() - 1).values
    bm_pre = pd.read_parquet(HERE / "bm_signal.parquet")

    def avg_rank_corr(a, b):
        cs = []
        for t in a.index:
            x, y = a.loc[t], b.loc[t]
            ok = x.notna() & y.notna()
            if ok.sum() >= 8:
                cs.append(x[ok].rank().corr(y[ok].rank()))
        return float(np.nanmean(cs))

    W = pd.DataFrame(0.0, index=dates, columns=tk)
    for t in dates:
        el = [c for c in tk if bool(elig.loc[t, c]) and np.isfinite(bm_fix.loc[t, c])]
        if len(el) < 8:
            continue
        top, bot = K.rank_pick(bm_fix.loc[t, el], 4)
        w = pd.Series(0.0, index=tk)
        w[top] = 0.25
        w[bot] = -0.25
        W.loc[t] = K.book(w, ex.loc[:t], gross_cap=3.0).values
    df, turn, held = K.run_sim(W, P["ohlc"], P["rf"], "next_close", K.COST_BPS)
    start = pd.Timestamp(json.loads((HERE / "metrics.json").read_text())["start"])
    d = df.loc[start:]
    out = {"is": K.window_stats(d.loc[:K.IS_END], turn, refs), "later": K.window_stats(d.loc[K.LATER_START:], turn, refs),
           "rank_corr_bm_pre_vs_mom12": avg_rank_corr(bm_pre, mom), "rank_corr_bm_fix_vs_mom12": avg_rank_corr(bm_fix, mom),
           "rank_corr_bm_pre_vs_fix": avg_rank_corr(bm_pre, bm_fix), "valid_far_days": diag}
    d.to_parquet(HERE / "posthoc_V1_r2fix.parquet")
    (HERE / "posthoc_check.json").write_text(json.dumps(out, indent=2, default=float))
    print(json.dumps({k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if kk != "yearly"})
                      for k, v in out.items()}, indent=1, default=float))


if __name__ == "__main__":
    main()
