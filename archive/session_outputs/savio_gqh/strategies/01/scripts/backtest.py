"""Lagged, costed, lookahead-aware IS backtest. rf=0, 252-day ann. Cut 2024-10-02."""

from __future__ import annotations

import json
import sys
from pathlib import Path as _P

sys.path.insert(0, str(_P(__file__).resolve().parent))

import numpy as np
import pandas as pd

from config import (
    ANN,
    COST_BPS,
    DATA_PROC,
    GROSS_CAP,
    HALF_LIFE,
    IS_END,
    NO_TRADE_BAND,
    OUTPUTS,
    POS_CLIP,
    TRIALS,
    VOL_FLOOR,
    VOL_TARGET,
    VOL_W_LONG,
    VOL_W_SHORT,
    W_TLT,
    W_UUP,
    Z_CLOCK_START,
    Z_MIN_OBS,
)

LAM = 2.0 ** (-1.0 / HALF_LIFE)


def next_session(dates: pd.DatetimeIndex, d: pd.Timestamp) -> pd.Timestamp | pd.NaT:
    i = dates.searchsorted(pd.Timestamp(d), side="right")
    if i >= len(dates):
        return pd.NaT
    return dates[i]


def max_dd(r: pd.Series) -> float:
    eq = (1.0 + r.fillna(0)).cumprod()
    return float((eq / eq.cummax() - 1.0).min())


def ann_stats(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 2:
        return {"n": len(r), "ann_ret": np.nan, "vol": np.nan, "sharpe": np.nan, "maxdd": np.nan}
    mu = float(r.mean())
    sd = float(r.std(ddof=1))
    return {
        "n": int(len(r)),
        "ann_ret": mu * ANN,
        "vol": sd * np.sqrt(ANN),
        "sharpe": (mu / sd) * np.sqrt(ANN) if sd > 0 else np.nan,
        "maxdd": max_dd(r),
    }


def main() -> dict:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    TRIALS.mkdir(parents=True, exist_ok=True)
    is_end = pd.Timestamp(IS_END)

    px = pd.read_csv(DATA_PROC / "markets.csv", index_col=0, parse_dates=True)
    px = px.loc[px.index <= is_end].copy()
    if px.index.max() > is_end:
        raise RuntimeError("OOS prices leaked into markets.csv")

    sc = pd.read_csv(DATA_PROC / "speech_scores.csv", parse_dates=["speech_date"])
    sc = sc[sc["kept"].astype(bool) & sc["speech_date"].notna() & sc["speech_date"].le(is_end)].copy()

    fomc = pd.read_csv(DATA_PROC / "fomc_dates.csv", parse_dates=["fomc_date"])
    fomc = fomc[fomc["fomc_date"] <= is_end]

    dgs2 = pd.read_csv(DATA_PROC / "fred_DGS2.csv", parse_dates=["date"])
    dgs2 = dgs2[dgs2["date"] <= is_end].set_index("date")["value"].sort_index()

    tdays = px.index.sort_values()
    tday_set = set(tdays.normalize())

    sc["usable"] = sc["speech_date"].map(lambda d: next_session(tdays, d))
    sc = sc[sc["usable"].notna()].copy()
    inj = sc.groupby("usable", as_index=True)["s"].sum()

    C = pd.Series(0.0, index=tdays, dtype=float)
    running = 0.0
    inj_map = inj.to_dict()
    for t in tdays:
        running = LAM * running + float(inj_map.get(t, 0.0))
        C.loc[t] = running

    clock = pd.Timestamp(Z_CLOCK_START)
    C_clock = C.loc[C.index >= clock]
    mu = C_clock.expanding(min_periods=Z_MIN_OBS).mean()
    sd = C_clock.expanding(min_periods=Z_MIN_OBS).std(ddof=1)
    z = ((C_clock - mu) / sd).reindex(tdays)
    z = z.replace([np.inf, -np.inf], np.nan)
    pos = z.clip(-POS_CLIP, POS_CLIP)

    r_tlt = px["TLT_ret"]
    r_uup = px["UUP_ret"]
    # last IS row has no next-open inside the cut
    valid_ret = r_tlt.notna() & r_uup.notna()

    mix = -W_TLT * r_tlt + W_UUP * r_uup
    past = mix.shift(1)
    v20 = past.rolling(VOL_W_SHORT, min_periods=VOL_W_SHORT).std(ddof=1) * np.sqrt(ANN)
    v60 = past.rolling(VOL_W_LONG, min_periods=VOL_W_LONG).std(ddof=1) * np.sqrt(ANN)
    vol = (0.5 * v20 + 0.5 * v60).clip(lower=VOL_FLOOR)

    fomc_days = set()
    for d in pd.to_datetime(fomc["fomc_date"]):
        d = pd.Timestamp(d).normalize()
        if d in tday_set:
            fomc_days.add(d)
        else:
            nxt = next_session(tdays, d - pd.Timedelta(days=1))
            if pd.notna(nxt):
                fomc_days.add(pd.Timestamp(nxt).normalize())
    fomc_next = set()
    for d in fomc_days:
        nxt = next_session(tdays, d)
        if pd.notna(nxt):
            fomc_next.add(pd.Timestamp(nxt).normalize())

    n = len(tdays)
    w_tlt = np.zeros(n)
    w_uup = np.zeros(n)
    traded = np.zeros(n, dtype=bool)
    pos_v = pos.reindex(tdays).to_numpy()
    vol_v = vol.reindex(tdays).to_numpy()
    z_ok = np.isfinite(pos_v) & np.isfinite(vol_v)

    prev_tlt = 0.0
    prev_uup = 0.0
    for i, t in enumerate(tdays):
        tn = pd.Timestamp(t).normalize()
        if not z_ok[i]:
            w_tlt[i] = prev_tlt
            w_uup[i] = prev_uup
            continue
        scale = VOL_TARGET / vol_v[i]
        wt = -W_TLT * pos_v[i] * scale
        wu = W_UUP * pos_v[i] * scale
        gross = abs(wt) + abs(wu)
        if gross > GROSS_CAP and gross > 0:
            cap = GROSS_CAP / gross
            wt *= cap
            wu *= cap
        if tn in fomc_days:
            wt *= 0.5
        proposed_l1 = abs(wt - prev_tlt) + abs(wu - prev_uup)
        cur_g = abs(prev_tlt) + abs(prev_uup)
        force = (tn in fomc_days) or (tn in fomc_next) or (cur_g == 0.0 and (abs(wt) + abs(wu)) > 0)
        if (not force) and cur_g > 0 and proposed_l1 < NO_TRADE_BAND * cur_g:
            w_tlt[i] = prev_tlt
            w_uup[i] = prev_uup
            continue
        w_tlt[i] = wt
        w_uup[i] = wu
        traded[i] = True
        prev_tlt, prev_uup = wt, wu

    w_tlt_s = pd.Series(w_tlt, index=tdays)
    w_uup_s = pd.Series(w_uup, index=tdays)
    dw_tlt = w_tlt_s.diff().fillna(w_tlt_s)
    dw_uup = w_uup_s.diff().fillna(w_uup_s)
    cost1 = (dw_tlt.abs() * (COST_BPS["TLT"] / 1e4)) + (dw_uup.abs() * (COST_BPS["UUP"] / 1e4))

    r_g = w_tlt_s * r_tlt + w_uup_s * r_uup
    r1 = r_g - cost1
    r2 = r_g - 2.0 * cost1
    r_tlt_leg = w_tlt_s * r_tlt - dw_tlt.abs() * (COST_BPS["TLT"] / 1e4)
    r_uup_leg = w_uup_s * r_uup - dw_uup.abs() * (COST_BPS["UUP"] / 1e4)

    first_z = z.first_valid_index()
    if first_z is None:
        raise RuntimeError("no valid expanding z — check speech corpus / dates")
    # IS: first valid z through last return that does not need a post-cut open
    mask = valid_ret & (tdays >= pd.Timestamp(first_z)) & (tdays < is_end)
    # last return date is the session whose next open is still <= IS_END
    last_ok = tdays[valid_ret].max()
    mask = valid_ret & (z.notna()) & (tdays >= pd.Timestamp(first_z))
    # drop the final IS row if its return is NaN (no next open)
    r_g_is = r_g.where(mask).dropna()
    # belt: no index beyond last_ok
    r_g_is = r_g_is.loc[:last_ok]
    if r_g_is.index.max() > is_end:
        raise RuntimeError("OOS return leaked")
    r1_is = r1.reindex(r_g_is.index)
    r2_is = r2.reindex(r_g_is.index)
    r_tlt_is = r_tlt_leg.reindex(r_g_is.index)
    r_uup_is = r_uup_leg.reindex(r_g_is.index)
    pos_is = pos.reindex(r_g_is.index)
    c_is = C.reindex(r_g_is.index)
    r_tlt_raw = r_tlt.reindex(r_g_is.index)

    to_l1 = (dw_tlt.abs() + dw_uup.abs()).reindex(r_g_is.index)
    turnover_ann = float(to_l1.mean() * ANN)

    rows = []
    for label, series in [("gross", r_g_is), ("1x", r1_is), ("2x", r2_is)]:
        st = ann_stats(series)
        st.update({"sleeve": "combined", "cost": label, "turnover_ann": turnover_ann})
        rows.append(st)
    for sleeve, series in [("TLT", r_tlt_is), ("UUP", r_uup_is)]:
        st = ann_stats(series)
        st.update({"sleeve": sleeve, "cost": "1x", "turnover_ann": np.nan})
        rows.append(st)

    y2022 = (r1_is.index >= "2022-01-01") & (r1_is.index <= "2022-12-31")
    st_22 = ann_stats(r1_is.loc[y2022])
    st_22.update({"sleeve": "combined_2022", "cost": "1x", "turnover_ann": np.nan})
    rows.append(st_22)
    st_rest = ann_stats(r1_is.loc[~y2022])
    st_rest.update({"sleeve": "combined_rest", "cost": "1x", "turnover_ann": np.nan})
    rows.append(st_rest)

    # DGS2 dated t-2 trading days (H.15 available at open t)
    dgs2_td = dgs2.reindex(tdays).ffill()
    dgs2_lag2 = dgs2_td.shift(2)
    corr_df = pd.concat([c_is, dgs2_lag2.reindex(r_g_is.index)], axis=1).dropna()
    corr_df.columns = ["C", "dgs2_tminus2"]
    corr_c_dgs2 = float(corr_df["C"].corr(corr_df["dgs2_tminus2"])) if len(corr_df) > 5 else np.nan

    # tilt vs timing on clipped z vs r_TLT (and on traded TLT weight)
    p = pos_is.dropna()
    rt = r_tlt_raw.reindex(p.index).dropna()
    p, rt = p.align(rt, join="inner")
    tilt_z = float(p.mean() * rt.mean())
    timing_z = float(p.cov(rt, ddof=1)) if len(p) > 2 else np.nan
    wt = w_tlt_s.reindex(r_g_is.index)
    tilt_w = float(wt.mean() * r_tlt_raw.mean())
    timing_w = float(wt.cov(r_tlt_raw, ddof=1)) if len(wt) > 2 else np.nan

    # cheap event study: s terciles vs TLT h=1 (next-open already in usable) and h=5
    ev = None
    try:
        sc2 = sc.dropna(subset=["s", "usable"]).copy()
        sc2["tercile"] = pd.qcut(sc2["s"], 3, labels=["dove", "mid", "hawk"], duplicates="drop")
        ao = px["TLT_adjopen"]
        recs = []
        for rec in sc2.itertuples(index=False):
            t0 = rec.usable
            if t0 not in ao.index:
                continue
            i0 = ao.index.get_loc(t0)
            if i0 + 5 >= len(ao.index):
                continue
            r1e = float(ao.iloc[i0 + 1] / ao.iloc[i0] - 1.0) if i0 + 1 < len(ao) else np.nan
            r5e = float(ao.iloc[i0 + 5] / ao.iloc[i0] - 1.0)
            recs.append({"tercile": rec.tercile, "r1": r1e, "r5": r5e})
        evdf = pd.DataFrame(recs)
        ev = evdf.groupby("tercile")[["r1", "r5"]].mean().to_dict() if len(evdf) else None
    except Exception as e:
        ev = {"error": str(e)}

    metrics = pd.DataFrame(rows)
    extra = pd.DataFrame(
        [
            {"sleeve": "diag", "cost": "corr_C_DGS2_tminus2", "sharpe": corr_c_dgs2},
            {"sleeve": "diag", "cost": "tilt_z_meanpos_meanrTLT", "sharpe": tilt_z},
            {"sleeve": "diag", "cost": "timing_cov_z_rTLT", "sharpe": timing_z},
            {"sleeve": "diag", "cost": "tilt_wTLT_meanw_meanr", "sharpe": tilt_w},
            {"sleeve": "diag", "cost": "timing_cov_wTLT_rTLT", "sharpe": timing_w},
            {"sleeve": "diag", "cost": "n_docs_kept", "sharpe": float(len(sc))},
            {"sleeve": "diag", "cost": "n_fomc", "sharpe": float(len(fomc_days))},
            {"sleeve": "diag", "cost": "first_z", "sharpe": np.nan, "note": str(pd.Timestamp(first_z).date())},
            {"sleeve": "diag", "cost": "last_ret", "sharpe": np.nan, "note": str(r_g_is.index.max().date())},
            {"sleeve": "diag", "cost": "rf", "sharpe": 0.0},
            {"sleeve": "diag", "cost": "ann_days", "sharpe": float(ANN)},
        ]
    )
    metrics = pd.concat([metrics, extra], ignore_index=True)
    metrics.to_csv(OUTPUTS / "is_metrics.csv", index=False)

    eq = pd.DataFrame(
        {
            "C": C,
            "z": z,
            "pos": pos,
            "vol_mix": vol,
            "w_tlt": w_tlt_s,
            "w_uup": w_uup_s,
            "r_gross": r_g,
            "r_1x": r1,
            "r_2x": r2,
            "equity_gross": (1.0 + r_g.where(mask).fillna(0)).cumprod(),
            "equity_1x": (1.0 + r1.where(mask).fillna(0)).cumprod(),
            "equity_2x": (1.0 + r2.where(mask).fillna(0)).cumprod(),
            "dgs2_tminus2": dgs2_lag2,
            "fomc_derisk": [pd.Timestamp(t).normalize() in fomc_days for t in tdays],
        },
        index=tdays,
    )
    eq = eq.loc[r_g_is.index]
    eq["equity_gross"] = (1.0 + r_g_is).cumprod()
    eq["equity_1x"] = (1.0 + r1_is).cumprod()
    eq["equity_2x"] = (1.0 + r2_is).cumprod()
    eq.to_csv(OUTPUTS / "equity_is.csv")

    sharpe_1x = float(ann_stats(r1_is)["sharpe"])
    summary = {
        "first_z": str(pd.Timestamp(first_z).date()),
        "last_ret": str(r_g_is.index.max().date()),
        "n_is_days": int(len(r_g_is)),
        "n_docs_kept": int(len(sc)),
        "n_fomc": int(len(fomc_days)),
        "sharpe_gross": float(ann_stats(r_g_is)["sharpe"]),
        "sharpe_1x": sharpe_1x,
        "sharpe_2x": float(ann_stats(r2_is)["sharpe"]),
        "sharpe_tlt_1x": float(ann_stats(r_tlt_is)["sharpe"]),
        "sharpe_uup_1x": float(ann_stats(r_uup_is)["sharpe"]),
        "sharpe_2022_1x": float(st_22["sharpe"]),
        "sharpe_rest_1x": float(st_rest["sharpe"]),
        "corr_C_DGS2_tminus2": corr_c_dgs2,
        "tilt_z": tilt_z,
        "timing_z": timing_z,
        "tilt_w": tilt_w,
        "timing_w": timing_w,
        "turnover_ann": turnover_ann,
        "event_study": ev,
        "rf": 0.0,
        "ann": ANN,
        "max_px_date": str(px.index.max().date()),
        "max_eq_date": str(eq.index.max().date()),
    }
    (OUTPUTS / "is_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "event_study"}, indent=2))
    print("event_study", ev)
    return summary


if __name__ == "__main__":
    main()
