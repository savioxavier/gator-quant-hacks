"""Combined summary of the two stance-score backtests -> summary.json and summary.md.

    python summarize.py --chrono-root R --v2-scores F --v2-out D --presser-text T --presser-out P --out-dir O [--placebo]

Reads only files the two backtests wrote; computes nothing new.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd

from wirelib import YEARS, jdump, jload


def rj(p: Path):
    return jload(p) if p.exists() else None


def rc(p: Path):
    return pd.read_csv(p) if p.exists() and p.stat().st_size > 1 else None


def recs(p: Path):
    d = rc(p)
    return d.to_dict("records") if d is not None else None


def fmt(x, nd=3):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "n/a"
    if isinstance(x, (int,)) and not isinstance(x, bool):
        return str(x)
    if isinstance(x, float):
        if x.is_integer() and abs(x) >= 1:
            return str(int(x))
        return f"{x:.{nd}f}"
    return str(x)


def md_table(df: pd.DataFrame, cols: list[str]) -> str:
    cols = [c for c in cols if c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(fmt(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("chrono-root", "v2-scores", "v2-out", "presser-text", "presser-out", "out-dir"):
        ap.add_argument(f"--{k}", required=True)
    ap.add_argument("--placebo", action="store_true")
    a = ap.parse_args()
    root, v2o, pto, pout, od = (Path(a.chrono_root), Path(a.v2_out), Path(a.presser_text), Path(a.presser_out),
                                Path(a.out_dir))
    od.mkdir(parents=True, exist_ok=True)
    label = "PLACEBO CHAIN TEST (random scores; these numbers are not results)" if a.placebo else "results"

    # ---------------------------------------------------------------- stance model
    sd = root / "scores"
    years = {}
    for y in YEARS:
        m = rj(sd / f"{y}_meta.json") or {}
        years[str(y)] = {"n_docs": m.get("n_docs"), "n_sentences": m.get("n_sentences"),
                         "seed_val_macro_f1": m.get("seed_val_macro_f1"),
                         "seed_label_agreement": m.get("seed_label_agreement")}
    # D1a: label coverage and leakage counts per model year (team code's prepare audit), reported as required
    aud = rj(root / "data" / "label_year_audit.json") or {}
    rule = aud.get("rule_in_use")
    d1a = ({y: {"train_rows": v.get(f"rows_{rule}"), "verbatim_in_corpus_doc_dated_ge_Y": v.get(f"leak_{rule}"),
                "first_seen_in_corpus_ge_Y": v.get(f"first_{rule}")}
            for y, v in (aud.get("per_test_year") or {}).items()} if rule else None)
    stance = {"chrono_root": str(root), "merge_meta": rj(sd / "merge_meta.json"), "years": years,
              "label_audit_D1a": {"rule_in_use": rule, "label_dates": aud.get("label_dates"),
                                  "per_model_year": d1a} if rule else None,
              "v2_adapter": rj(Path(a.v2_scores).with_name(Path(a.v2_scores).stem + "_meta.json")),
              "presser_adapter": rj(pto / "scorer.json")}

    # ---------------------------------------------------------------- v2
    s = rj(v2o / "summary_is.json") or {}
    sel = rc(v2o / "selection.csv")
    win = rc(v2o / "windows_all.csv")
    port = rc(v2o / "portfolio.csv")
    chair = rc(v2o / "by_chair_is.csv")
    oos = rj(v2o / "oos_chosen.json")
    oos_no = rj(v2o / "oos_not_evaluated.json") or rj(v2o / "oos_not_evaluated_placebo.json")
    sens_is = rc(v2o / "sens_scheduled_only_is.csv")
    v2 = {"out_dir": str(v2o), "mode": s.get("mode"), "chosen": s.get("chosen"),
          "selection_sharpe_net1x": s.get("selection_sharpe_net1x"),
          "validation_sharpe_net1x": s.get("validation_sharpe_net1x"),
          "full_is_sharpe_net2x": s.get("full_is_sharpe_net2x"), "decision_rule_passed": s.get("decision_rule_passed"),
          "validation_vs_target_0.7": s.get("validation_vs_target_0.7"), "falsifiers": s.get("falsifiers"),
          "dsr": s.get("dsr"), "corr_chosen_vs_core_ER_6_full_is": s.get("corr_chosen_vs_core_ER_6_full_is"),
          "first_valid_z": s.get("first_valid_z"),
          "selection_table": sel.to_dict("records") if sel is not None else None,
          "portfolio_is": port.to_dict("records") if port is not None else None,
          "by_chair_is": chair.to_dict("records") if chair is not None else None,
          "sens_scheduled_only_is": sens_is.to_dict("records") if sens_is is not None else None,
          "oos": oos, "oos_not_evaluated": oos_no,
          "portfolio_oos": recs(v2o / "portfolio_oos.csv") if oos else None,
          "by_chair_oos": recs(v2o / "by_chair_oos.csv") if oos else None,
          "sens_scheduled_only_oos": recs(v2o / "sens_scheduled_only_oos.csv") if oos else None}

    # ---------------------------------------------------------------- presser H1
    R = pout / "results"
    g3 = rj(R / "g3_and_h1primary_extras.json") or {}
    meta = rj(R / "run_meta.json") or {}
    S = rc(R / "summary_long.csv")
    h1rows = None
    if S is not None and "test" in S.columns:
        q = S[(S.test.isin(["H1-primary[H1]", "H1-Q[H1Q]"])) & (S.sym == "ZT") & (S.cost.isin(["C0", "C2", "C4"])) &
              (S.unit == "usd") & (S.variant.isin(["primary|exit_1600", "exec30|exit_1600", "primary|exit_1630"]))]
        h1rows = q[["test", "variant", "sample", "cost", "n", "mean", "sd", "hit", "t", "wb_p_one", "wb_p_two",
                    "bb_ci90_lo", "bb_ci90_hi"]].copy()
    ans = rc(R / "h1answer_summary.csv")
    ans_h1 = None
    if ans is not None and "signal" in ans.columns and "cost" in ans.columns:
        ans_h1 = ans[(ans.signal == "H1") & (ans.split == "all") & (ans.cost == "C0")]
    presser = {"out_dir": str(pout), "stance_scorer": meta.get("stance_scorer"), "text_dir": meta.get("text_dir"),
               "G3_H1_primary_confirmation_2023_2026": g3.get("H1"), "H1Q": g3.get("H1Q"),
               "H1_primary_ZT_rows_usd": h1rows.to_dict("records") if h1rows is not None else None,
               "H1_answer_ZT_C0": ans_h1.to_dict("records") if ans_h1 is not None else None,
               "lexicon_control": {"lexH1": g3.get("lexH1"), "lexH1raw": g3.get("lexH1raw")},
               "key_results": rj(R / "key_results.json")}

    summary = {"label": label, "placebo": a.placebo, "stance_model": stance, "fedspeak_v2": v2,
               "presser_H1": presser}
    jdump(summary, od / "summary.json")

    # ---------------------------------------------------------------- markdown
    L = [f"# Stance-model backtests: {label}", ""]
    if a.placebo:
        L += ["**PLACEBO.** Every stance score here is random. This file only shows that the chain runs end to end.",
              "No number below says anything about the strategies.", ""]
    mm = stance["merge_meta"] or {}
    L += ["## Stance model (chrono walk-forward)", "",
          f"- Work root: `{root}`",
          f"- Years merged: {mm.get('years_merged')}; label-year rule: {mm.get('label_year_rule')}; "
          f"documents: {mm.get('n_docs')}",
          f"- Non-full-spec years: {mm.get('nonspec_years') or 'none'}", ""]
    yt = pd.DataFrame([{"year": y, **{k: v for k, v in d.items() if k != "seed_val_macro_f1"},
                        "val_macro_f1_by_seed": (", ".join(f"{float(x):.3f}" for x in d["seed_val_macro_f1"].values())
                                                 if d.get("seed_val_macro_f1") else "n/a")}
                       for y, d in years.items()])
    L += [md_table(yt, ["year", "n_docs", "n_sentences", "val_macro_f1_by_seed", "seed_label_agreement"]), ""]
    if d1a:
        L += [f"Label coverage and leakage per model year (D1a / Amendment 3; rule `{rule}`; every training row's "
              "source document is dated before Y by construction). `verbatim >= Y` = training rows whose sentence "
              "also appears verbatim in a scored document dated Y or later; `first >= Y` = rows whose first "
              "verbatim corpus occurrence is dated Y or later:", "",
              md_table(pd.DataFrame([{"model_year": y, "train_rows": v["train_rows"],
                                      "verbatim >= Y": v["verbatim_in_corpus_doc_dated_ge_Y"],
                                      "first >= Y": v["first_seen_in_corpus_ge_Y"]} for y, v in d1a.items()]),
                       ["model_year", "train_rows", "verbatim >= Y", "first >= Y"]), ""]
    else:
        L += ["Label coverage and leakage audit (D1a): `data/label_year_audit.json` not found under the work root.", ""]

    L += ["## Fed communication v2 (HYPOTHESIS_v2, Amendments 1-3)", "",
          f"- Chosen combination (max net 1x Sharpe, selection 2016-01-04..2020-12-31): **{v2['chosen']}**",
          f"- Selection Sharpe (net 1x): {fmt(v2['selection_sharpe_net1x'])}",
          f"- Validation Sharpe (net 1x, 2021-01-01..2024-10-02): {fmt(v2['validation_sharpe_net1x'])} "
          f"(target 0.7; difference {fmt(v2['validation_vs_target_0.7'])})",
          f"- Full in-sample Sharpe at 2x costs: {fmt(v2['full_is_sharpe_net2x'])}",
          f"- Decision rule (validation > 0 and full-IS 2x > 0.5): "
          f"**{'PASSED' if v2['decision_rule_passed'] else 'FAILED'}**", ""]
    if sel is not None:
        L += ["Selection window, all 8 combinations:", "",
              md_table(sel, ["combo", "first_position_date", "sharpe_net1x", "sharpe_net2x", "sharpe_gross",
                             "ann_excess_arith", "vol", "max_dd_excess", "turnover_per_year"]), ""]
    if v2["dsr"]:
        d = v2["dsr"]
        L += [f"- Deflated Sharpe ({d.get('n_trials')} trials): selection window "
              f"{fmt((d.get('selection_window') or {}).get('dsr'))}, full in-sample "
              f"{fmt((d.get('full_is') or {}).get('dsr'))}; n = 10 sensitivity "
              f"{fmt((d.get('sens_n10_dedup') or {}).get('dsr'))}; PSR vs 0 (selection) "
              f"{fmt((d.get('psr_vs_0_selection') or {}).get('dsr'))}", ""]
    if v2["falsifiers"]:
        f = v2["falsifiers"]
        L += ["Falsifiers:", "",
              f"- selection Sharpe <= 0.2: {f.get('selection_sharpe_le_0.2')}; validation <= 0: "
              f"{f.get('validation_le_0')}; net 2x <= 0: {f.get('net2x_le_0')}",
              f"- share of full-IS P&L from 2022: {fmt(f.get('share_full_is_pnl_from_2022'))} "
              f"(> half: {f.get('share_2022_gt_half')})",
              f"- corr(z_T2, z_T3) full IS: {fmt(f.get('corr_zT2_zT3_full_is'))}; corr(C_T2, M) full IS: "
              f"{fmt(f.get('corr_CT2_M_full_is'))}", ""]
    if port is not None:
        L += ["Portfolio test (core_ER_6 + chosen sleeve), in-sample:", "",
              md_table(port, ["portfolio", "window", "sharpe_net1x", "sharpe_net2x", "ann_excess_geo", "vol",
                              "max_dd_excess"]), ""]
    if chair is not None:
        L += ["By chair, in-sample:", "", md_table(chair, list(chair.columns)[:8]), ""]
    if sens_is is not None:
        L += ["Sensitivity (DEVIATIONS.md D-1, not used for selection): FOMC de-risk list registered vs "
              "scheduled-only:", "",
              md_table(sens_is, ["derisk_list", "window", "n_days", "sharpe_net1x", "sharpe_net2x", "ann_excess_arith"]), ""]
    if oos:
        w = oos.get("window") or [None, None]
        L += [f"### Out-of-sample {w[0]}..{w[1]} (evaluated once)", "",
              f"`{ {k: v for k, v in oos.items() if not isinstance(v, (dict, list))} }`", ""]
        for nm in ("portfolio_oos", "by_chair_oos", "sens_scheduled_only_oos"):
            if v2[nm]:
                L += [f"{nm}:", "", md_table(pd.DataFrame(v2[nm]), list(pd.DataFrame(v2[nm]).columns)[:8]), ""]
    else:
        L += [f"Out-of-sample: not evaluated ({(oos_no or {}).get('reason')}).", ""]

    L += ["## Press-conference H1 (ADDENDUM, D1/D1a stance scores)", "",
          f"- Stance scorer recorded by the run: {presser['stance_scorer']}", ""]
    g = presser["G3_H1_primary_confirmation_2023_2026"] or {}
    L += [f"- **G3 (confirmation sample, Powell 2023-2026, ZT, primary clock, 16:00 exit, gross): "
          f"{g.get('decision', g.get('status'))}**",
          f"- n = {g.get('n')}, mean = {fmt(g.get('mean'))} ticks ({fmt(g.get('mean_usd'), 2)} USD), "
          f"sign-flip wild bootstrap p (one-sided) = {fmt(g.get('wb_p_one'), 4)}, block-bootstrap 90% CI "
          f"[{fmt(g.get('bb_ci90_lo'))}, {fmt(g.get('bb_ci90_hi'))}], permutation p = {fmt(g.get('perm_p_one'), 4)}",
          f"- exec30 mean = {fmt(g.get('exec30_mean'))}; leave-one-out range [{fmt(g.get('loo_min'))}, "
          f"{fmt(g.get('loo_max'))}]; companion slope {fmt(g.get('slope_coef'), 5)} (HC3 t {fmt(g.get('slope_t_hc3'))})",
          ""]
    if h1rows is not None and len(h1rows):
        L += ["H1-primary and H1-Q, ZT, per meeting in USD (2016-2022 is the additional sample reported beside "
              "the confirmation sample; never part of G3):", "",
              md_table(h1rows, ["test", "variant", "sample", "cost", "n", "mean", "hit", "t", "wb_p_one",
                                "bb_ci90_lo", "bb_ci90_hi"]), ""]
    if ans_h1 is not None and len(ans_h1):
        L += ["H1-answer (diagnostic), ZT, gross:", "",
              md_table(ans_h1, ["sample", "h", "unit", "n_answers", "n_meetings", "mean", "t_cr1", "wcb_p_two",
                                "mtg_mean", "mtg_wb_p_two"]), ""]
    L += ["Inputs:", "", f"- v2 outputs: `{v2o}`", f"- press-conference outputs: `{pout}`",
          f"- press-conference text with stance columns: `{pto}`", ""]
    (od / "summary.md").write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {od / 'summary.json'} and {od / 'summary.md'}")


if __name__ == "__main__":
    main()
