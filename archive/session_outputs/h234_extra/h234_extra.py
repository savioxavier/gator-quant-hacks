"""Extra rows for the local H2/H3/H4 replication (read-only on the stage outputs; no price level is written).

A. note-1 descriptive rows: every primary test without 20190501 and without 20230614 (prereg note 1, sections 1 and 3),
   with a check that both meetings are outside the features, baselines, H4 training fit and test rows (note 2).
B. strategy-level metrics of the H2 and H4 test trades, sized like the press-conference strategy series
   (backtests/results/presser_strategy/build_presser_strategy.py: constant contracts per trade, N chosen so the
   one-contract daily gross P&L has 10% annualised vol on $10m in the training window; daily P&L on the NYSE calendar,
   zero on days without a trade; Sharpe = mean/sd x sqrt(252); additive drawdown on 1 + cumsum(r)).
   Costs: gross; net 1x = measured half-spread at each fill + $2/side fee; net 2x = twice the net 1x cost.

Usage: python h234_extra.py <stage output folder> <out folder>
Env:   GQH_MARKET_DIR (licensed market files, read in memory only), GQH_DATA_DIR (index_daily.parquet calendar)
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

STAGE = Path(sys.argv[1])
OUTD = Path(sys.argv[2])
OUTD.mkdir(parents=True, exist_ok=True)
CODE = STAGE.parent / "backtest" / "code"
sys.path.insert(0, str(CODE))
import lib  # noqa: E402  (the stage's own ADDENDUM code: Bars, Quotes, trade, answer_summary, cluster_t)
from lib import B, SEED, WEBB, TZ, answer_summary, cluster_t  # noqa: E402
from scipy import stats as sps  # noqa: E402

R, P, Q, F, W = (STAGE / x for x in ("results", "positions", "qa", "features", "h4_fit"))
PRIMARY, TRAIN = "primary_2023_2026", "additional_2018_2022"
DROPS = ["20190501", "20230614"]
out: dict = {"stage_folder_name": STAGE.name}


def jdump(p, o):
    def conv(x):
        if isinstance(x, (np.integer,)):
            return int(x)
        if isinstance(x, (np.floating,)):
            return None if not np.isfinite(x) else float(x)
        if isinstance(x, (np.bool_,)):
            return bool(x)
        return str(x)
    Path(p).write_text(json.dumps(o, indent=1, default=conv), encoding="utf-8")


# ============================================================================ A. note-1 descriptive rows
qa = pd.read_csv(Q / "meeting_qa.csv", dtype={"presser_id": str})
bs = pd.read_csv(Q / "baseline_stats.csv", dtype={"presser_id": str})
feat = pd.read_parquet(F / "answers_h234.parquet")
chunks = pd.read_parquet(F / "voice_chunks_assigned.parquet")
AT = pd.read_csv(R / "answer_trades.csv", dtype={"date": str, "answer_id": str})
H4R = pd.read_csv(R / "h4_answer_rows.csv", dtype={"date": str, "answer_id": str})
fit = json.loads((W / "fit.json").read_text())
AS = pd.read_csv(R / "answer_summary.csv")
fam = json.loads((R / "family_holm.json").read_text())
h4res = json.loads((R / "h4_results.json").read_text())

presence = {}
for pid in DROPS:
    d = f"{pid[:4]}-{pid[4:6]}-{pid[6:]}"
    qrow = qa[qa.presser_id == pid].iloc[0]
    fa = feat[feat.presser_id.astype(str) == pid]
    presence[pid] = dict(
        drop_timing=int(qrow.drop_timing), vtt_median_offset_s=qrow.vtt_median_offset_s, qa_ok=bool(qrow.qa_ok),
        h2_ok=bool(qrow.h2_ok), h3_ok=bool(qrow.h3_ok), h2_exclusion=qrow.h2_exclusion, h3_exclusion=qrow.h3_exclusion,
        n_caption_answers=int(qrow.n_caption_answers),
        in_any_baseline=bool((bs.presser_id == pid).any()),
        answers_with_zA=int(fa.zA.notna().sum()), answers_with_U=int(fa.U.notna().sum()),
        valid_chunks_in_record_table=int((chunks.presser_id.astype(str) == pid)[chunks.valid & chunks.answer_id.notna()].sum()),
        answer_trades_rows=int((AT.meeting.astype(str) == pid).sum()),
        h4_rows=int((H4R.meeting.astype(str) == pid).sum()),
        in_h4_training_fit={k: d in v["meetings"] for k, v in fit["fits"].items()},
    )
    # voice_chunks_assigned.parquet records every assigned chunk before the meeting gate; a gated-out meeting's chunks
    # never reach A_raw / z (set to NaN), the baselines, the valence pool (h2_ok only), positions or fits
    presence[pid]["note"] = "chunks in the record table are not used: meeting gated out (h2_ok/h3_ok false)"
    presence[pid]["outside_features_baselines_fits_trades"] = (not presence[pid]["h2_ok"] and not presence[pid]["h3_ok"]
                                           and not presence[pid]["in_any_baseline"]
                                           and presence[pid]["answers_with_zA"] == 0
                                           and presence[pid]["answers_with_U"] == 0
                                           and presence[pid]["answer_trades_rows"] == 0
                                           and presence[pid]["h4_rows"] == 0
                                           and not any(presence[pid]["in_h4_training_fit"].values()))
out["note1_presence"] = presence


def cw(y, yT, yC, g):
    """Copy of h234_s4_pnl.cw (CR1 branch): Clark-West, one-sided p from t(G-1), wild cluster bootstrap of mean(f)."""
    f = (y - yT) ** 2 - ((y - yC) ** 2 - (yT - yC) ** 2)
    o = dict(n=len(f), mean_f=float(np.mean(f)))
    G = len(np.unique(g))
    m, s, t, _ = cluster_t(f, g)
    o.update(se=s, t=t, n_clusters=G, df=G - 1, p_one=float(1 - sps.t.cdf(t, G - 1)),
             p_two=float(2 * (1 - sps.t.cdf(abs(t), G - 1))))
    codes, gi = np.unique(g, return_inverse=True)
    rng = np.random.default_rng(SEED)
    w = rng.choice(WEBB, size=(B, G))
    fc = f - m
    n = len(f)
    ys = w[:, gi] * fc[None, :]
    ms = ys.mean(1)
    S = np.zeros((B, G))
    for j in range(G):
        S[:, j] = (ys[:, gi == j] - ms[:, None]).sum(1)
    ses = np.sqrt((G / (G - 1)) * (S ** 2).sum(1) / n ** 2)
    ts = ms / ses
    o.update(wcb_p_one=float((1 + np.sum(ts >= t)) / (B + 1)), wcb_p_two=float((1 + np.sum(np.abs(ts) >= abs(t))) / (B + 1)))
    o["oos_r2_C_vs_T"] = float(1 - np.sum((y - yC) ** 2) / np.sum((y - yT) ** 2))
    o["oos_r2_C_vs_zero"] = float(1 - np.sum((y - yC) ** 2) / np.sum(y ** 2))
    o["oos_r2_T_vs_zero"] = float(1 - np.sum((y - yT) ** 2) / np.sum(y ** 2))
    nz = y != 0
    o["sign_hit_C"] = float(np.mean(np.sign(yC[nz]) == np.sign(y[nz])))
    o["sign_hit_T"] = float(np.mean(np.sign(yT[nz]) == np.sign(y[nz])))
    return o


def refit(train, feats):
    """Copy of the h234_s3 fit: standardise on the training rows, OLS."""
    mu = {c: float(train[c].mean()) for c in feats}
    sd = {c: float(train[c].std(ddof=1)) for c in feats}
    X = np.column_stack([np.ones(len(train))] + [(train[c].to_numpy(float) - mu[c]) / sd[c] for c in feats])
    b = np.linalg.lstsq(X, train.y.to_numpy(float), rcond=None)[0]
    return mu, sd, dict(zip(["const"] + feats, map(float, b)))


def pred(df, mu, sd, coef, feats):
    X = np.column_stack([np.ones(len(df))] + [(df[c].to_numpy(float) - mu[c]) / sd[c] for c in feats])
    return X @ np.array([coef[c] for c in ["const"] + feats])


FA = ["s_tilde", "zA", "U"]
rows = []
z4 = H4R[H4R.sym == "ZT"].copy()
for drop in [None] + DROPS:
    lab = "main (nothing dropped)" if drop is None else f"without {drop}"
    # H2 and H3 primary: answer-level ZT +1 min gross, 2023-2026, wild cluster bootstrap by meeting
    for k in ["H2", "H3"]:
        d = AT[(AT.key == k) & (AT.h == 1) & (AT.sym == "ZT") & (AT.variant == "base") & (AT["sample"] == PRIMARY)]
        if drop is not None:
            d = d[d.meeting.astype(str) != drop]
        s = answer_summary(d.C0_ticks.to_numpy(float), d.meeting.to_numpy(), d.date.to_numpy())
        status = "killed (G4)" if k == "H3" else "run"
        rows.append(dict(row=lab, test=k, status=status, n=s["n_answers"], n_meetings=s["n_meetings"],
                         mean_ticks=s["mean"], t_cr1=s["t_cr1"], p_wcb_two=s["wcb_p_two"],
                         p_used=(1.0 if k == "H3" else s["wcb_p_two"]), ci90_lo=s["bb_ci90_lo"], ci90_hi=s["bb_ci90_hi"]))
    # H4: refit on the training rows (without the dropped meeting), Clark-West on the test rows
    tr = z4[(z4["sample"] == TRAIN)]
    te = z4[(z4["sample"] == PRIMARY)]
    if drop is not None:
        tr, te = tr[tr.meeting.astype(str) != drop], te[te.meeting.astype(str) != drop]
    muT, sdT, cT = refit(tr, ["s_tilde"])
    muC, sdC, cC = refit(tr, FA)
    yT, yC = pred(te, muT, sdT, cT, ["s_tilde"]), pred(te, muC, sdC, cC, FA)
    c = cw(te.y.to_numpy(float), yT, yC, te.meeting.to_numpy())
    rows.append(dict(row=lab, test="H4", status="run", n=c["n"], n_meetings=c["n_clusters"], train_n=len(tr),
                     train_meetings=int(tr.meeting.nunique()), cw_t=c["t"], p_one=c["p_one"], p_two=c["p_two"],
                     wcb_p_one=c["wcb_p_one"], p_used=c["p_one"], oos_r2_C_vs_T=c["oos_r2_C_vs_T"],
                     oos_r2_C_vs_zero=c["oos_r2_C_vs_zero"], oos_r2_T_vs_zero=c["oos_r2_T_vs_zero"],
                     sign_hit_C=c["sign_hit_C"], sign_hit_T=c["sign_hit_T"],
                     coef_C=cC, coef_T=cT))
N1 = pd.DataFrame(rows)
for lab, g in N1.groupby("row"):
    pv = dict(zip(g.test, g.p_used))
    keys = sorted(pv, key=lambda k: pv[k])
    run, adj = 0.0, {}
    for i, k in enumerate(keys):
        run = max(run, min(1.0, (len(keys) - i) * pv[k]))
        adj[k] = run
    N1.loc[g.index, "p_holm"] = g.test.map(adj).to_numpy()
# reproduction checks against the stage's own numbers
main = N1[N1.row == "main (nothing dropped)"].set_index("test")
st_h2 = AS[AS.designated_primary & (AS.key == "H2")].iloc[0]
ff = h4res["answer_ZT"]["frozen_fit"]
checks = dict(
    H2_mean_matches=abs(main.loc["H2", "mean_ticks"] - st_h2["mean"]) < 1e-12,
    H2_p_matches=abs(main.loc["H2", "p_wcb_two"] - st_h2.wcb_p_two) < 1e-12,
    H4_refit_equals_frozen_fit_C=all(abs(main.loc["H4", "coef_C"][k] - fit["fits"]["answer_ZT"]["coef_C"][k]) < 1e-9
                                     for k in fit["fits"]["answer_ZT"]["coef_C"]),
    H4_t_matches=abs(main.loc["H4", "cw_t"] - ff["t"]) < 1e-9,
    H4_p_one_matches=abs(main.loc["H4", "p_one"] - ff["p_one"]) < 1e-9,
    H4_wcb_matches=abs(main.loc["H4", "wcb_p_one"] - ff["wcb_p_one"]) < 1e-12,
    holm_matches={k: abs(main.loc[k, "p_holm"] - fam[k]["p_holm"]) < 1e-12 for k in ["H2", "H3", "H4"]},
)
cols_cmp = ["n", "n_meetings", "mean_ticks", "t_cr1", "p_wcb_two", "cw_t", "p_one", "oos_r2_C_vs_T", "sign_hit_C", "p_holm"]
eq = {}
for drop in DROPS:
    x = N1[N1.row == f"without {drop}"].set_index("test")
    eq[drop] = all(np.allclose(pd.to_numeric(x.loc[t, cols_cmp], errors="coerce").to_numpy(float),
                               pd.to_numeric(main.loc[t, cols_cmp], errors="coerce").to_numpy(float),
                               equal_nan=True, rtol=0, atol=1e-12) for t in ["H2", "H3", "H4"])
checks["rows_equal_main"] = eq
out["note1_checks"] = checks
N1.drop(columns=["coef_C", "coef_T"]).to_csv(OUTD / "note1_descriptive_rows.csv", index=False)

# ============================================================================ B. strategy-level metrics
CAPITAL, TARGET_VOL, ANN, FEE_SIDE = 10_000_000.0, 0.10, 252, 2.00
TRAIN_END = pd.Timestamp("2022-12-31")
TEST_W = (pd.Timestamp("2023-02-01"), pd.Timestamp("2026-04-29"))      # = the strategy series' G3 sub-window
IS_END, OOS_START, OOS_END = pd.Timestamp("2024-10-02"), pd.Timestamp("2024-10-03"), pd.Timestamp("2026-10-02")
data_dir = Path(os.environ.get("GQH_DATA_DIR", str(Path.home() / ".cache/gqh")))
idx = pd.read_parquet(data_dir / "index_daily.parquet")
CAL = pd.DatetimeIndex(sorted(pd.to_datetime(idx[idx.ticker == "^GSPC"].date).dt.normalize().unique()))

# --- H2 trades: the stage's own rows (answer_trades.csv, ZT, +1 min, base entry)
h2 = AT[(AT.key == "H2") & (AT.h == 1) & (AT.sym == "ZT") & (AT.variant == "base") &
        AT["sample"].isin([PRIMARY, TRAIN])].copy()
h2["strategy"] = "H2 sign(z_A), ZT +1 min"

# --- H4 trades: sign(yC) (and sign(yT) as reference) at +1 min, through the stage's own one_trade logic
bars, quotes = lib.Bars(), lib.Quotes()


def one_trade(date, t0, sym, pos, hh=1):
    """Copy of h234_s4_pnl.one_trade (prices stay in memory; only ticks/usd/half-spreads are kept)."""
    e_ts, e_px = bars.next_open(date, sym, t0, tag="extra_entry")
    if e_ts is None:
        return None
    x_ts, x_px = bars.close_at(date, sym, e_ts + pd.Timedelta(minutes=hh), lo=e_ts, tag="extra_exit")
    if x_ts is None:
        return None
    tr = lib.trade(date, sym, pos, e_ts, e_px, x_ts, x_px, e_ts, x_ts + pd.Timedelta(minutes=1), quotes)
    tr["logret_bp"] = 1e4 * math.log(x_px / e_px)
    return {k: v for k, v in tr.items() if k not in ("entry_px", "exit_px", "ret")}


z4["t0"] = pd.to_datetime(z4.t0, utc=True, format="ISO8601").dt.tz_convert(TZ)
z4 = z4[z4["sample"].isin([PRIMARY, TRAIN])]
h4rows = []
for mdl in ["C", "T"]:
    for r in z4.itertuples():
        pos = float(np.sign(getattr(r, f"y{mdl}")))
        if pos == 0:
            continue
        t_ = one_trade(r.date, r.t0, "ZT", pos)
        if t_ is None:
            continue
        t_.update(strategy=f"H4 sign(y{mdl}){' (combined)' if mdl == 'C' else ' (text-only reference)'}, ZT +1 min",
                  meeting=r.meeting, sample=r.sample, answer_id=r.answer_id, y_check=r.y)
        h4rows.append(t_)
h4 = pd.DataFrame(h4rows)
# reconciliation with the stage: logret equals the stage's y; test-sample sign(yC)/sign(yT) P&L equals h4_results
rec = dict(h4_logret_equals_stage_y=bool(np.allclose(h4.logret_bp, h4.y_check, atol=1e-9)))
for mdl in ["C", "T"]:
    te = h4[(h4.strategy.str.contains(f"sign\\(y{mdl}\\)")) & (h4["sample"] == PRIMARY)]
    for c in ["C0", "C2", "C4"]:
        ref = h4res["answer_ZT"][f"pnl_sign_{mdl}"][c]
        rec[f"sign_{mdl}_{c}_n_and_mean_match"] = bool(len(te) == ref["n_answers"] and
                                                       abs(te[f"{c}_ticks"].mean() - ref["mean"]) < 1e-12)
# H2 replication through the same code path, as a check that the copy of one_trade equals the stage
h2x = []
sel2 = pd.read_csv(P / "answer_sel_H2_h1.csv", dtype={"date": str, "answer_id": str})
sel2["t0"] = pd.to_datetime(sel2.t0, utc=True, format="ISO8601").dt.tz_convert(TZ)
for r in sel2.itertuples():
    pos = r.H2__pos_ZT
    if not np.isfinite(pos) or pos == 0:
        continue
    t_ = one_trade(r.date, r.t0, "ZT", pos)
    if t_:
        h2x.append(dict(answer_id=r.answer_id, C0_ticks=t_["C0_ticks"], hs_entry_ticks=t_["hs_entry_ticks"]))
h2x = pd.DataFrame(h2x).merge(AT[(AT.key == "H2") & (AT.h == 1) & (AT.sym == "ZT") & (AT.variant == "base")]
                              [["answer_id", "C0_ticks", "hs_entry_ticks"]], on="answer_id", suffixes=("_x", "_stage"))
rec["h2_copy_of_one_trade_equals_stage"] = bool(len(h2x) and np.allclose(h2x.C0_ticks_x, h2x.C0_ticks_stage) and
                                                np.allclose(h2x.hs_entry_ticks_x, h2x.hs_entry_ticks_stage, equal_nan=True))
out["strategy_reconciliation"] = rec

T = pd.concat([h2, h4], ignore_index=True)
T["date_ts"] = pd.to_datetime(T.date)
missing_days = sorted(set(T.date_ts) - set(CAL))
if missing_days:
    raise SystemExit(f"trade dates not in the calendar: {missing_days}")
measured = T.hs_entry_ticks.notna() & T.hs_exit_ticks.notna()
T["cost_basis"] = np.where(measured, "measured half-spread + fee", "2 ticks/side + fee (quote missing)")
T["spread_cost_ticks"] = np.where(measured, T.hs_entry_ticks + T.hs_exit_ticks, 4.0)
T["gross_usd"] = T.C0_ticks * T.usd_per_tick
cost1 = T.spread_cost_ticks * T.usd_per_tick + 2 * FEE_SIDE
T["net1x_usd"] = T.gross_usd - cost1
T["net2x_usd"] = T.gross_usd - 2 * cost1
rec["net1x_equals_stage_CMF_where_measured"] = bool(np.allclose(T.net1x_usd[measured], T.CMF_usd[measured], atol=1e-9))
rec["trades_without_measured_half_spread"] = T[~measured].groupby("strategy").size().to_dict()


def drawdown(r):
    eq_ = 1.0 + np.cumsum(r)
    peak = np.maximum.accumulate(np.r_[1.0, eq_])[1:]
    return float((eq_ / peak - 1.0).min()), float((peak - eq_).max() * CAPITAL)


met, size_rows, daily = [], [], []
for st, g in T.groupby("strategy"):
    first_train = g[g["sample"] == TRAIN].date_ts.min()
    days_tr = CAL[(CAL >= first_train) & (CAL <= TRAIN_END)]
    pnl1 = g[g["sample"] == TRAIN].groupby("date_ts").gross_usd.sum().reindex(days_tr, fill_value=0.0)
    vol1 = (pnl1 / CAPITAL).std(ddof=1) * np.sqrt(ANN)
    N = max(1, int(round(TARGET_VOL / vol1)))
    size_rows.append(dict(strategy=st, sizing_window=f"{days_tr.min().date()}..{days_tr.max().date()}",
                          sizing_days=len(days_tr), sizing_trades=int((g["sample"] == TRAIN).sum()),
                          ann_vol_one_contract=vol1, N_exact=TARGET_VOL / vol1, N=N, ann_vol_with_N=vol1 * N))
    wins = [("training window (sizing; H4 in-sample fit)", first_train, TRAIN_END, TRAIN),
            ("TEST window 2023-02-01..2026-04-29 (headline)", TEST_W[0], TEST_W[1], PRIMARY),
            ("competition IS: first trade..2024-10-02 (includes training trades)", first_train, IS_END, None),
            ("competition OOS: 2024-10-03..2026-10-02 (test trades only)", OOS_START, OOS_END, None)]
    for wname, w0, w1, smp in wins:
        days = CAL[(CAL >= w0) & (CAL <= w1)]
        gw = g[(g.date_ts >= w0) & (g.date_ts <= w1)]
        if smp is not None:
            gw = gw[gw["sample"] == smp]
        for c in ["gross", "net1x", "net2x"]:
            pnl = (gw.groupby("date_ts")[f"{c}_usd"].sum() * N).reindex(days, fill_value=0.0)
            r = (pnl / CAPITAL).to_numpy()
            mu, sd = r.mean(), r.std(ddof=1)
            mdd, mdd_usd = drawdown(r)
            pt = gw[f"{c}_usd"].to_numpy()
            met.append(dict(strategy=st, window=wname, cost=c, start=str(days.min().date()), end=str(days.max().date()),
                            trading_days=len(days), N_contracts=N, n_trades=len(pt), n_trade_days=int(gw.date_ts.nunique()),
                            n_meetings=int(gw.meeting.nunique()), ann_return=mu * ANN, ann_vol=sd * np.sqrt(ANN),
                            sharpe=mu / sd * np.sqrt(ANN) if sd > 0 else np.nan, max_drawdown=mdd,
                            max_drawdown_usd=mdd_usd, total_return=r.sum(), total_pnl_usd=pnl.sum(),
                            mean_usd_per_contract_trade=pt.mean() if len(pt) else np.nan,
                            mean_ticks_per_trade=(pt / gw.usd_per_tick.to_numpy()).mean() if len(pt) else np.nan,
                            hit_rate=(pt > 0).mean() if len(pt) else np.nan))
    days = CAL[(CAL >= first_train) & (CAL <= OOS_END)]
    d = pd.DataFrame({"date": days.strftime("%Y-%m-%d")})
    for c in ["gross", "net1x", "net2x"]:
        d[f"ret_{c}"] = ((g.groupby("date_ts")[f"{c}_usd"].sum() * N).reindex(days, fill_value=0.0) / CAPITAL).to_numpy()
    d.insert(0, "strategy", st)
    daily.append(d)
M = pd.DataFrame(met)
M.to_csv(OUTD / "strategy_metrics.csv", index=False, float_format="%.6g")
pd.DataFrame(size_rows).to_csv(OUTD / "strategy_sizing.csv", index=False, float_format="%.6g")
pd.concat(daily).to_csv(OUTD / "strategy_daily_returns.csv", index=False, float_format="%.8g")
keep = ["strategy", "date", "meeting", "sample", "answer_id", "pos", "tick_era", "usd_per_tick", "C0_ticks",
        "hs_entry_ticks", "hs_exit_ticks", "cost_basis", "gross_usd", "net1x_usd", "net2x_usd"]
T[keep].sort_values(["strategy", "date"]).to_csv(OUTD / "strategy_per_trade_no_prices.csv", index=False, float_format="%.6g")
out["strategy_sizing"] = size_rows
out["capital_usd"], out["target_vol"], out["fee_usd_per_side"] = CAPITAL, TARGET_VOL, FEE_SIDE
out["calendar"] = f"{data_dir.name}/index_daily.parquet ^GSPC trading days"
jdump(OUTD / "extra_summary.json", out)

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 200)
print(json.dumps(out, indent=1, default=str))
print(N1.drop(columns=["coef_C", "coef_T"]).to_string())
print(M[["strategy", "window", "cost", "N_contracts", "n_trades", "n_meetings", "ann_return", "ann_vol", "sharpe",
         "max_drawdown", "mean_ticks_per_trade", "hit_rate"]].to_string())
