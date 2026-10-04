"""Fed communication v2 backtest runner (pre-registration HYPOTHESIS_v2.md + Amendment 1).

Modes
  check  no strategy returns: data status, T0 vs replicate cross-check, causality (prefix) test, T3 regression
         check, core_ER_6 rebuild check, chair dates.
  smoke  the whole in-sample pipeline on PLACEBO scores (every score column replaced by random numbers);
         outputs to smoke_placebo/; never evaluates out-of-sample.
  run    the pre-registered run. Refuses to start unless score/doc_scores.parquet exists with a FOMC-RoBERTa
         score for every document. Out-of-sample (FWD) only for the chosen combination and only if the
         decision rule passes.

Run from the repo root:
  GQH_DATA_DIR=<data cache> PYTHONIOENCODING=utf-8 <gqh venv python> <this file> <mode>
Never sets GQH_OOS_UNLOCK, never calls engine.run_backtest/log_trial, never writes to the repo.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(os.environ.get("GQH_REPO") or "../gqh-flow-clock")  # github.com/minh-stakc/gqh-flow-clock
HERE = Path(__file__).resolve().parent
SCR = HERE.parents[1]                                   # scratchpad
V2 = HERE.parent                                        # scratchpad/fedspeak_v2
PREREG = REPO / "research" / "fedspeak_v2" / "HYPOTHESIS_v2.md"
PREREG_SHA = "6083d3ef742ad67623b34337c8299ce4c7172fc1e1a786003eae4b4fb7ced910"
DOC_SCORES = V2 / "score" / "doc_scores.parquet"
DOC_SCORES_LEXONLY = V2 / "score" / "doc_scores_lexonly.parquet"
FOMC_VA = V2 / "corpus" / "fomc_dates_variantA_style.csv"
FOMC_S01 = SCR / "savio_gqh" / "strategies" / "01" / "data" / "processed" / "fomc_dates.csv"
EXT_SPEECH = SCR / "fedspeak" / "extend" / "speech_scores_2011_2026.csv"
REPL_SIGNAL = SCR / "fedspeak" / "replicate" / "signal.parquet"
TRIAL_LOG = SCR / "savio_gqh" / "strategies" / "01" / "trials" / "log.csv"
COMBINE_PY = SCR / "edges" / "combine" / "combine.py"
CORE6 = SCR / "edges" / "series" / "PORT_core_ER_6.parquet"

assert os.environ.get("GQH_OOS_UNLOCK") != "1", "OOS unlock must stay off"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))
from src import engine as E  # noqa: E402
import v2lib as L  # noqa: E402

IS_END = "2024-10-02"
CORPUS = ("2015-01-01", "2026-10-02")
SEL = ("2016-01-04", "2020-12-31")
VAL = ("2021-01-01", "2024-10-02")
FULL_IS = ("2016-01-04", "2024-10-02")
OOS = ("2024-10-03", "2026-10-02")
V2_CLOCK = "2015-01-01"           # expanding-z clock: sessions from the start of the corpus (first session 2015-01-02)
T0F_CLOCK = "2011-01-03"          # Variant A as frozen
CHAIRS = [  # federalreserve.gov Board membership page (cached corpus/raw, checked 2026-10-03)
    ("Yellen", "2014-02-03", "2018-02-03"),
    ("Powell", "2018-02-05", "2026-05-21"),      # chair term ended 2026-05-22; that day is assigned to the successor
    ("Warsh", "2026-05-22", "2099-12-31"),
]
SIGNALS = ["T1", "T2", "T3", "T4"]
COMBOS = [f"{t}x{e}" for t in SIGNALS for e in ("E1", "E2")]
TICKERS = ["TLT", "UUP", "F_ZN", "F_6E"]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def jdump(obj, path: Path):
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


# ----------------------------------------------------------------------------- inputs
def load_docs(mode: str, seed: int = 0) -> pd.DataFrame:
    if mode == "run":
        if not DOC_SCORES.exists():
            raise SystemExit(f"BLOCKED: {DOC_SCORES} does not exist (FOMC-RoBERTa scores not produced). Nothing computed.")
        d = pd.read_parquet(DOC_SCORES)
        miss = int(d["rob_score"].isna().sum())
        if miss:
            raise SystemExit(f"BLOCKED: {miss} documents have no rob_score. Nothing computed.")
    else:
        d = pd.read_parquet(DOC_SCORES_LEXONLY)
        if mode == "smoke":
            rng = np.random.default_rng(seed)
            for c in ("lex_score", "lex_score_varA_html", "rob_score"):
                d[c] = rng.uniform(-1, 1, len(d))
    d["date"] = pd.to_datetime(d["date"])
    d = d[(d["date"] >= CORPUS[0]) & (d["date"] <= CORPUS[1])].copy()
    return d


def load_ext_speeches(mode: str, seed: int = 0) -> pd.DataFrame:
    e = pd.read_csv(EXT_SPEECH, parse_dates=["speech_date"])
    e = e[e["kept"].astype(bool) & e["speech_date"].notna() & e["s"].notna()].copy()
    if mode == "smoke":
        e["s"] = np.random.default_rng(seed + 1).uniform(-1, 1, len(e))
    return e[e["speech_date"] <= CORPUS[1]]


def load_fomc() -> pd.Series:
    a = pd.read_csv(FOMC_S01, parse_dates=["fomc_date"])["fomc_date"]
    b = pd.read_csv(FOMC_VA, parse_dates=["fomc_date"])["fomc_date"]
    return pd.Series(sorted(set(a[a < "2015-01-01"]) | set(b)))


def market(period: str):
    ohlc = E.load_ohlc(TICKERS, period)
    rf = E.load_rf(period)
    dgs2 = E.load_series("fred_daily.parquet", period)["DGS2"].dropna()
    cal = ohlc["close"].index
    return ohlc, rf.reindex(cal).ffill().fillna(0.0), dgs2, cal


# ----------------------------------------------------------------------------- signals
def build_signals(docs: pd.DataFrame, ext: pd.DataFrame, cal: pd.DatetimeIndex, dgs2: pd.Series) -> dict:
    sp = docs[docs["doc_type"] == "speech"]
    va = sp[sp["lex_kept_varA_html"].astype("boolean").fillna(False).astype(bool)]
    lex_all = docs[docs["lex_kept"].astype(bool)]
    C = {
        "T0f": L.consensus_s(cal, ext["speech_date"], ext["s"]),
        "T0v2": L.consensus_s(cal, va["date"], va["lex_score_varA_html"]),
        "T1": L.consensus_s(cal, sp["date"], sp["rob_score"]),
        "T2": L.consensus_s(cal, docs["date"], docs["rob_score"]),
        "LEXALL": L.consensus_s(cal, lex_all["date"], lex_all["lex_score"]),
    }
    Z = {
        "T0f": L.expanding_z(C["T0f"], T0F_CLOCK),
        "T0v2": L.expanding_z(C["T0v2"], V2_CLOCK),
        "T1": L.expanding_z(C["T1"], V2_CLOCK),
        "T2": L.expanding_z(C["T2"], V2_CLOCK),
    }
    M = L.rate_momentum_s(cal, dgs2)
    t3 = L.expanding_residual_z(C["T2"], M, V2_CLOCK)
    Z["T3"] = t3["z"]
    z_lex = L.expanding_z(C["LEXALL"], V2_CLOCK)
    Z["T4"] = 0.5 * (z_lex + Z["T2"])
    return {"C": C, "Z": Z, "M": M, "T3": t3, "z_lexall": z_lex}


def combo_weights(z_s: pd.Series, e: str, ohlc: dict, fomc: pd.Series):
    ex = L.EXPRS[e]
    fs = L.fomc_day_s(z_s.index, fomc)
    if e == "E1":
        return L.weights_E1(z_s, ohlc["open"][[ex.rate, ex.fx]], fs, ex)
    return L.weights_E2(z_s, ohlc["close"][[ex.rate, ex.fx]], fs, ex)


def simulate(w_dec: pd.DataFrame, e: str, ohlc: dict, rf: pd.Series) -> pd.DataFrame:
    ex = L.EXPRS[e]
    n1, g, t1, held, c1 = E.simulate(w_dec, ohlc, rf, exec=ex.exec, cost_bps=ex.cost_bps)
    n2, _, _, _, _ = E.simulate(w_dec, ohlc, rf, exec=ex.exec, cost_bps=ex.cost_bps, cost_mult=2.0)
    r = rf.reindex(n1.index).fillna(0.0)
    out = pd.DataFrame({"net": n1, "gross": g, "rf": r, "ex1": n1 - r, "ex2": n2 - r, "exg": g - r,
                        "turnover": t1, "cost": c1,
                        "w_rate": held[ex.rate], "w_fx": held[ex.fx]})
    out["gross_exposure"] = held.abs().sum(axis=1)
    return out


def first_trade(sim: pd.DataFrame) -> str | None:
    nz = sim.index[sim["gross_exposure"] > 0]
    return str(nz[0].date()) if len(nz) else None


def stats_row(sim: pd.DataFrame, win) -> dict:
    """Window statistics; a window never includes days before the first held position (no zero padding)."""
    ft = first_trade(sim)
    a = max(pd.Timestamp(win[0]), pd.Timestamp(ft)) if ft else pd.Timestamp(win[0])
    return L.window_stats(sim["ex1"], sim["ex2"], sim["exg"], sim["turnover"], a, win[1])


# ----------------------------------------------------------------------------- portfolio test
def load_combine():
    spec = importlib.util.spec_from_file_location("combine_v1", COMBINE_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def portfolio(sleeve: pd.DataFrame | None, cost_bp: float | None, end: str, label: str):
    """core_ER_6 rebuilt with the original code path (combine.build), optionally with a fourth sleeve.
    Returns (baseline returns, augmented returns or None, info)."""
    CB = load_combine()
    cal, rf, sl, gr, cost, *_ = CB.load()
    cal = cal[cal <= pd.Timestamp(end)]
    core = list(CB.CORE)
    base = CB.build(core, "ER", 0.06, cal, sl, gr, cost)
    info = {"core_first": str(base["first"].date())}
    ref = pd.read_parquet(CORE6)["net_1x"]
    ref.index = pd.to_datetime(ref.index)
    j = pd.concat([base["ret"]["net_1x"], ref], axis=1, join="inner").dropna()
    j = j.loc[: pd.Timestamp(end)]
    info["rebuild_max_abs_diff_vs_PORT_core_ER_6"] = float((j.iloc[:, 0] - j.iloc[:, 1]).abs().max())
    info["rebuild_n_compared"] = int(len(j))
    if sleeve is None:
        return base, None, info
    name = f"FED_{label}"
    s = sleeve.copy()
    first = s.index[s["gross_exposure"] > 0][0]
    df = pd.DataFrame({"net_1x": s["ex1"], "net_2x": s["ex2"], "gross": s["exg"]})
    df.loc[df.index < first] = np.nan
    df = df.loc[: pd.Timestamp(end)].reindex(cal)
    sl[name] = df
    gr[name] = s["gross_exposure"].reindex(cal).fillna(0.0)
    cost[name] = cost_bp
    aug = CB.build(core + [name], "ER", 0.06, cal, sl, gr, cost)
    m = aug["m"][name]
    info["fed_sleeve_first_live_multiplier"] = str(m.index[m > 0][0].date()) if (m > 0).any() else None
    return base, aug, info


def port_stats(R: pd.DataFrame, win) -> dict:
    s = slice(pd.Timestamp(win[0]), pd.Timestamp(win[1]))
    x1, x2 = R["net_1x"].loc[s].dropna(), R["net_2x"].loc[s].dropna()
    if len(x1) < 21:
        return {}
    yrs = len(x1) / 252
    return {"start": str(x1.index[0].date()), "end": str(x1.index[-1].date()), "n_days": len(x1),
            "sharpe_net1x": L.sharpe(x1), "sharpe_net2x": L.sharpe(x2),
            "ann_excess_geo": float((1 + x1).prod() ** (1 / yrs) - 1), "vol": float(x1.std() * math.sqrt(252)),
            "max_dd_excess": L.max_dd(x1)}


# ----------------------------------------------------------------------------- per-chair
def chair_rows(series: dict, windows: list[tuple[str, str, str]]) -> list[dict]:
    rows = []
    for name, sim in series.items():
        for chair, a, b in windows:
            st = stats_row(sim, (a, b))
            if st.get("n_days", 0) >= 2:
                rows.append({"series": name, "chair": chair, **st})
    return rows


def chair_windows(lo: str, hi: str):
    out = []
    for c, a, b in CHAIRS:
        a2, b2 = max(a, lo), min(b, hi)
        if a2 <= b2:
            out.append((c, a2, b2))
    return out


# ----------------------------------------------------------------------------- DSR
def dsr_block(ex_sel: pd.Series, ex_full: pd.Series, sel_sharpes: list[float]) -> dict:
    log = pd.read_csv(TRIAL_LOG)
    logged = [float(v) for v in log["sharpe_1x"]]
    srs = list(sel_sharpes) + logged
    var = float(np.var(srs, ddof=1))
    out = {"trial_sharpes_used": srs, "n_trials": len(srs), "var_sr_ann": var,
           "note": "8 combos (selection-window net Sharpe) + Variant A's 3 logged trials (sharpe_1x column; row 3 repeats row 2)",
           "selection_window": E.deflated_sharpe(ex_sel, len(srs), var),
           "full_is": E.deflated_sharpe(ex_full, len(srs), var)}
    var8 = float(np.var(sel_sharpes, ddof=1))
    out["sens_n10_dedup"] = E.deflated_sharpe(ex_sel, 10, var)
    out["sens_var_from_8_combos_only"] = E.deflated_sharpe(ex_sel, len(srs), var8)
    out["psr_vs_0_selection"] = E.deflated_sharpe(ex_sel, 1, var)
    return out


# ----------------------------------------------------------------------------- pipeline (IS)
def pipeline_is(mode: str, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    docs = load_docs(mode)
    ext = load_ext_speeches(mode)
    fomc = load_fomc()
    ohlc, rf, dgs2, cal = market("IS")
    docs = docs[docs["date"] <= IS_END]
    ext = ext[ext["speech_date"] <= IS_END]
    sig = build_signals(docs, ext, cal, dgs2)
    first_z = {k: (str(v.first_valid_index().date()) if v.first_valid_index() is not None else None) for k, v in sig["Z"].items()}

    sims, weights = {}, {}
    for t in SIGNALS:
        for e in ("E1", "E2"):
            w, aux = combo_weights(sig["Z"][t], e, ohlc, fomc)
            weights[f"{t}x{e}"] = (w, aux)
            sims[f"{t}x{e}"] = simulate(w, e, ohlc, rf)
    for ref in ("T0f", "T0v2"):
        w, aux = combo_weights(sig["Z"][ref], "E1", ohlc, fomc)
        sims[f"{ref}xE1"] = simulate(w, "E1", ohlc, rf)

    # step 2: selection
    rows = []
    for k in COMBOS:
        st = stats_row(sims[k], SEL)
        rows.append({"combo": k, "signal": k[:2], "expression": k[3:], "first_position_date": first_trade(sims[k]),
                     "first_valid_z": first_z[k[:2]], **st})
    sel = pd.DataFrame(rows)
    sel.to_csv(out / "selection.csv", index=False)
    chosen = sel.loc[sel["sharpe_net1x"].idxmax(), "combo"]

    # validation, full IS, references
    tab = []
    for k in COMBOS + ["T0fxE1", "T0v2xE1"]:
        for wn, win in (("selection", SEL), ("validation", VAL), ("full_is", FULL_IS)):
            tab.append({"combo": k, "window": wn, "chosen": k == chosen, **stats_row(sims[k], win)})
    tab = pd.DataFrame(tab)
    tab.to_csv(out / "windows_all.csv", index=False)
    g = tab.set_index(["combo", "window"])
    val_sr = float(g.loc[(chosen, "validation"), "sharpe_net1x"])
    full2x = float(g.loc[(chosen, "full_is"), "sharpe_net2x"])
    sel_sr = float(g.loc[(chosen, "selection"), "sharpe_net1x"])
    passed = bool(val_sr > 0 and full2x > 0.5)

    # falsifiers
    x = sims[chosen]["ex1"].loc[FULL_IS[0]:FULL_IS[1]]
    pnl22 = float(x.loc["2022"].sum())
    tot = float(x.sum())
    fals = {
        "selection_sharpe_le_0.2": sel_sr <= 0.2,
        "validation_le_0": val_sr <= 0,
        "share_full_is_pnl_from_2022": pnl22 / tot if tot != 0 else None,
        "full_is_pnl_sum": tot, "pnl_2022_sum": pnl22,
        "share_2022_gt_half": (pnl22 / tot > 0.5) if tot > 0 else "undefined: full-IS P&L <= 0",
        "full_is_net2x_sharpe": full2x, "net2x_le_0": full2x <= 0,
        "T3_vs_T1_T2": {k: {wn: float(g.loc[(k, wn), "sharpe_net1x"]) for wn in ("selection", "validation", "full_is")}
                        for k in COMBOS if k[:2] in ("T1", "T2", "T3")},
        "corr_zT2_zT3_full_is": float(pd.concat([sig["Z"]["T2"], sig["Z"]["T3"]], axis=1).loc[FULL_IS[0]:FULL_IS[1]].corr().iloc[0, 1]),
        "corr_CT2_M_full_is": float(pd.concat([sig["C"]["T2"], sig["M"]], axis=1).loc[FULL_IS[0]:FULL_IS[1]].corr().iloc[0, 1]),
        "T3_beta_last": float(sig["T3"]["beta"].dropna().iloc[-1]),
    }
    # DSR
    sel_sharpes = [float(v) for v in sel["sharpe_net1x"]]
    dsr = dsr_block(sims[chosen]["ex1"].loc[SEL[0]:SEL[1]], sims[chosen]["ex1"].loc[FULL_IS[0]:FULL_IS[1]], sel_sharpes)

    # portfolio test (IS windows)
    e = chosen[3:]
    cbp = 0.75 * 1.5 + 0.25 * 5.0 if e == "E1" else 1.0
    base, aug, pinfo = portfolio(sims[chosen], cbp, IS_END, chosen)
    prow = []
    for wn, win in (("selection", SEL), ("validation", VAL), ("full_is", FULL_IS)):
        prow.append({"portfolio": "core_ER_6", "window": wn, **port_stats(base["ret"], win)})
        prow.append({"portfolio": f"core_ER_6+{chosen}", "window": wn, **port_stats(aug["ret"], win)})
    pd.DataFrame(prow).to_csv(out / "portfolio.csv", index=False)
    jdump(pinfo, out / "portfolio_info.json")
    corr = pd.concat([sims[chosen]["ex1"], base["ret"]["net_1x"]], axis=1).loc[FULL_IS[0]:FULL_IS[1]].dropna().corr().iloc[0, 1]

    # per-chair (IS part)
    pd.DataFrame(chair_rows({chosen: sims[chosen], "VariantA_frozen(T0fxE1)": sims["T0fxE1"],
                             "VariantA_2015warmup(T0v2xE1)": sims["T0v2xE1"]},
                            chair_windows(FULL_IS[0], FULL_IS[1]))).to_csv(out / "by_chair_is.csv", index=False)

    # daily series
    sims[chosen].to_parquet(out / f"daily_{chosen}_is.parquet")
    pd.DataFrame({k: v["ex1"] for k, v in sims.items()}).loc["2015-12-01":].to_parquet(out / "daily_excess_all_combos_is.parquet")
    pd.DataFrame({**{f"z_{k}": v for k, v in sig["Z"].items()}, **{f"C_{k}": v for k, v in sig["C"].items()},
                  "M_dgs2": sig["M"], "T3_beta": sig["T3"]["beta"], "z_lexall": sig["z_lexall"]}).loc["2014-12-01":].to_parquet(out / "signals_entry_session.parquet")

    summary = {"mode": mode, "prereg_sha256": sha256(PREREG), "first_valid_z": first_z,
               "first_position_dates": {k: first_trade(sims[k]) for k in sims},
               "chosen": chosen, "selection_sharpe_net1x": sel_sr, "validation_sharpe_net1x": val_sr,
               "full_is_sharpe_net2x": full2x, "decision_rule_passed": passed,
               "validation_vs_target_0.7": val_sr - 0.7, "falsifiers": fals, "dsr": dsr,
               "corr_chosen_vs_core_ER_6_full_is": float(corr), "portfolio_info": pinfo}
    jdump(summary, out / "summary_is.json")
    return {"summary": summary, "sims": sims, "chosen": chosen, "passed": passed, "fomc": fomc}


def stage_oos(res: dict, out: Path):
    """Evaluate the chosen combination ONCE on 2024-10-03..2026-10-02 (engine period FWD)."""
    chosen = res["chosen"]
    t, e = chosen[:2], chosen[3:]
    docs = load_docs("run")
    ext = load_ext_speeches("run")
    ohlc, rf, dgs2, cal = market("FWD")
    sig = build_signals(docs, ext, cal, dgs2)
    w, _ = combo_weights(sig["Z"][t], e, ohlc, res["fomc"])
    sim = simulate(w, e, ohlc, rf)
    is_sim = res["sims"][chosen]
    diff = float((sim["ex1"].loc[FULL_IS[0]:FULL_IS[1]] - is_sim["ex1"].loc[FULL_IS[0]:FULL_IS[1]]).abs().max())
    st = stats_row(sim, OOS)
    rec = {"chosen": chosen, "window": OOS, "evaluated_once_utc": pd.Timestamp.now("UTC").isoformat(),
           "is_consistency_max_abs_diff": diff, **st}
    jdump(rec, out / "oos_chosen.json")                  # written before anything else is computed on OOS
    sim.to_parquet(out / f"daily_{chosen}_full.parquet")
    # portfolio OOS
    cbp = 0.75 * 1.5 + 0.25 * 5.0 if e == "E1" else 1.0
    base, aug, pinfo = portfolio(sim, cbp, OOS[1], chosen)
    pd.DataFrame([{"portfolio": "core_ER_6", "window": "oos", **port_stats(base["ret"], OOS)},
                  {"portfolio": f"core_ER_6+{chosen}", "window": "oos", **port_stats(aug["ret"], OOS)}]).to_csv(out / "portfolio_oos.csv", index=False)
    # per-chair OOS (Variant A computed only after the chosen combination's OOS record is on disk)
    wa, _ = combo_weights(sig["Z"]["T0f"], "E1", ohlc, res["fomc"])
    sim_va = simulate(wa, "E1", ohlc, rf)
    pd.DataFrame(chair_rows({chosen: sim, "VariantA_frozen(T0fxE1)": sim_va}, chair_windows(OOS[0], OOS[1]))).to_csv(out / "by_chair_oos.csv", index=False)
    return rec


# ----------------------------------------------------------------------------- check mode (no returns)
def check(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    rep = {"prereg_sha256": sha256(PREREG), "prereg_sha_ok": sha256(PREREG) == PREREG_SHA}
    rep["doc_scores_exists"] = DOC_SCORES.exists()
    lx = pd.read_parquet(DOC_SCORES_LEXONLY)
    rep["lexonly_rob_score_nonnull"] = int(lx["rob_score"].notna().sum())
    rep["lexonly_rob_status_sample"] = str(lx["rob_status"].iloc[0])[:160]
    ohlc, rf, dgs2, cal = market("IS")
    fomc = load_fomc()
    a = pd.read_csv(FOMC_S01, parse_dates=["fomc_date"])["fomc_date"]
    b = pd.read_csv(FOMC_VA, parse_dates=["fomc_date"])["fomc_date"]
    rep["fomc_strat01_vs_corpus_2015_2024_symdiff"] = sorted(str(d.date()) for d in set(a[a >= "2015-01-01"]) ^ set(b[b <= IS_END]))

    # 1. T0 (frozen Variant A) vs replicate signal.parquet: decision-date weights
    docs = load_docs("check")
    ext = load_ext_speeches("check")
    sig = build_signals(docs[docs["date"] <= IS_END], ext[ext["speech_date"] <= IS_END], cal, dgs2)
    w, aux = combo_weights(sig["Z"]["T0f"], "E1", ohlc, fomc)
    rp = pd.read_parquet(REPL_SIGNAL)
    rp.index = pd.to_datetime(rp.index)
    k = rp.index[(rp.index >= "2010-01-04") & (rp.index < IS_END)]
    mine = pd.DataFrame({"consensus": sig["C"]["T0f"].shift(-1), "z": sig["Z"]["T0f"].shift(-1),
                         "w_TLT": w["TLT"], "w_UUP": w["UUP"]}).reindex(k)
    d = (mine - rp.reindex(k)[mine.columns]).abs()
    rep["T0f_vs_replicate_max_abs_diff"] = {c: float(d[c].max()) for c in d}
    rep["T0f_vs_replicate_n_dates"] = int(len(k))
    rep["T0f_vs_replicate_z_nan_mismatch"] = int((mine["z"].isna() != rp.reindex(k)["z"].isna()).sum())
    # T0v2 (2015 warm-up, v2 corpus scoring) vs T0f
    cc = pd.concat([sig["C"]["T0v2"], sig["C"]["T0f"]], axis=1).loc["2016-01-04":IS_END]
    rep["T0v2_vs_T0f_consensus_max_abs_diff_2016_IS"] = float((cc.iloc[:, 0] - cc.iloc[:, 1]).abs().max())
    zz = pd.concat([sig["Z"]["T0v2"], sig["Z"]["T0f"]], axis=1).loc["2016-01-04":IS_END]
    rep["T0v2_vs_T0f_z_corr_2016_IS"] = float(zz.corr().iloc[0, 1])
    rep["first_valid_z_T0v2"] = str(sig["Z"]["T0v2"].first_valid_index().date())

    # 2. causality: prefix invariance of every signal and weight series (placebo scores)
    pdocs = load_docs("smoke", seed=7)
    pext = load_ext_speeches("smoke", seed=7)
    cut = pd.Timestamp("2019-06-28")
    calc = cal[cal <= cut]
    full = build_signals(pdocs[pdocs["date"] <= IS_END], pext[pext["speech_date"] <= IS_END], cal, dgs2)
    part = build_signals(pdocs[pdocs["date"] <= cut], pext[pext["speech_date"] <= cut], calc, dgs2[dgs2.index <= cut])
    ohlc_c = {kk: v.loc[:cut] for kk, v in ohlc.items()}
    pref = {}
    for t in SIGNALS + ["T0f", "T0v2"]:
        zf, zp = full["Z"][t].loc[:cut], part["Z"][t]
        pref[f"z_{t}"] = float((zf - zp).abs().max())
        for e in ("E1", "E2"):
            wf, _ = combo_weights(full["Z"][t], e, ohlc, fomc)
            wp, _ = combo_weights(part["Z"][t], e, ohlc_c, fomc)
            # the last decision of the truncated run is a placeholder (filled after the cut), so it is excluded
            pref[f"w_{t}x{e}"] = float((wf.loc[:cut].iloc[:-1] - wp.iloc[:-1]).abs().max().max())
    rep["prefix_invariance_max_abs_diff"] = pref

    # 3. T3 expanding regression vs statsmodels at three dates
    import statsmodels.api as sm
    t3 = full["T3"]
    chk = {}
    for dte in ("2016-06-30", "2019-12-31", "2024-09-30"):
        dd = pd.Timestamp(dte)
        y = full["C"]["T2"].loc["2015-01-01":dd]
        xx = full["M"].loc["2015-01-01":dd]
        fit = sm.OLS(y.to_numpy(), sm.add_constant(xx.to_numpy())).fit()
        e_last = fit.resid[-1]
        z_last = e_last / np.std(fit.resid, ddof=1)
        chk[dte] = {"beta_diff": float(abs(fit.params[1] - t3.loc[dd, "beta"])), "z_diff": float(abs(z_last - t3.loc[dd, "z"]))}
    rep["T3_vs_statsmodels"] = chk

    # 4. timing spot-check: a document dated d must first move C on the session after d
    rep["timing_examples"] = []
    for dte in ("2016-03-16", "2019-10-11", "2020-03-15"):
        dd = pd.Timestamp(dte)
        one = L.consensus_s(cal, [dd], [1.0])
        rep["timing_examples"].append({"doc_date": dte, "first_session_with_C": str(one.index[one > 0][0].date())})

    # 5. core_ER_6 rebuild through the IS end
    _, _, pinfo = portfolio(None, None, IS_END, "none")
    rep["core_ER_6_rebuild"] = pinfo
    rep["chairs"] = CHAIRS
    jdump(rep, out / "check.json")
    print(json.dumps(rep, indent=1, default=str))


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    assert sha256(PREREG) == PREREG_SHA, "pre-registration hash mismatch"
    if mode == "check":
        check(HERE / "check")
    elif mode == "smoke":
        res = pipeline_is("smoke", HERE / "smoke_placebo")
        print(json.dumps({k: v for k, v in res["summary"].items() if k != "dsr"}, indent=1, default=str))
        print("SMOKE: placebo scores; out-of-sample is never evaluated in this mode.")
    elif mode == "run":
        res = pipeline_is("run", HERE)
        print(json.dumps(res["summary"], indent=1, default=str))
        if res["passed"]:
            rec = stage_oos(res, HERE)
            print("OOS (evaluated once):", json.dumps(rec, indent=1, default=str))
        else:
            jdump({"oos_evaluated": False, "reason": "decision rule failed (validation net Sharpe <= 0 or full-IS 2x Sharpe <= 0.5)"},
                  HERE / "oos_not_evaluated.json")
            print("Decision rule failed: out-of-sample NOT evaluated.")
    else:
        raise SystemExit(f"unknown mode {mode}")


if __name__ == "__main__":
    main()
