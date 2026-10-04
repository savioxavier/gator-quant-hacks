"""Run the fedspeak_v2 backtest (run_v2.py, unchanged) on the chrono stance scores, exactly per HYPOTHESIS_v2.

    GQH_DATA_DIR=<data cache> PYTHONIOENCODING=utf-8 <gqh python> run_v2_chrono.py \
        --doc-scores <doc_scores.parquet> --out <dir> [--placebo]

Uses run_v2's own functions (pipeline_is, stage_oos) with two settings changed from outside the frozen runner:
  * the pre-registration hash: run_v2 pins the Amendment-1 version; the file now carries Amendments 2-3 and the
    clarification, so the current hash (PREREG_SHA_NOW) is checked instead;
  * the input path (DOC_SCORES) and the output folder.
Order (pre-registered): selection 2016-01-04..2020-12-31 -> validation and full-IS 2x decision rule -> DSR,
portfolio test, per-chair (IS) -> only if the rule passes, ONE out-of-sample evaluation of the chosen combination
(oos_chosen.json written first) with its portfolio and per-chair tables. Otherwise oos_not_evaluated.json.
Added afterwards, never used for selection (DEVIATIONS.md D-1): the chosen combination with a scheduled-only FOMC
de-risk list, in-sample, and out-of-sample only after oos_chosen.json exists.
--placebo never evaluates out-of-sample and refuses output paths without 'placebo'. A real run refuses to start if
backtests/results/v2 (the committed decision record) or the output folder holds an out-of-sample record
(oos_chosen.json or oos_not_evaluated.json; the OOS is evaluated once); with --skip-if-complete it instead exits 0
without computing anything, after checking that --doc-scores is the file that run used (sha256). The lock is checked
before run_v2 (and gqh-flow-clock) is imported.
Deviation D-3 (preregistration/v2_DEVIATION_D3_OOS.md): with V2_OOS_DEVIATION naming that file at its pinned sha256
and --out backtests/results/v2_oos/run, the committed failed-rule record does not refuse, and the frozen pipeline runs
stage_oos ONCE although the rule failed (the verdict stands). Any other record, a D-3 one included, still refuses.
"""
from __future__ import annotations

import argparse
import json
import sys
import os
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent                  # backtests/v2
sys.path.insert(0, str(HERE.parent / "wire"))
from wirelib import jdump, sha256  # noqa: E402

LOCK_DIR = HERE.parent / "results" / "v2"               # the committed decision record (one-shot OOS)
LOCK_FILES = ("oos_chosen.json", "oos_not_evaluated.json")
PREREG_SHA_NOW = "464f8a5bad37e6466ccde42e8941fa1836323600324792d4d53dcc0c50eb8a2e"  # Amendments 1-3 + clarification
R = None                                                # run_v2, imported after the lock check (needs gqh-flow-clock)
D3_DEVIATION = HERE.parents[1] / "preregistration" / "v2_DEVIATION_D3_OOS.md"
D3_SHA = "97585d3ca3e7f5764d16e24787486c51ca298dd95ca57ad82d27e1ba30af1c69"  # D-3: OOS once for reporting, rule failed
D3_OUT = HERE.parent / "results" / "v2_oos" / "run"     # the only output folder of the D-3 evaluation


def d3_unlocked() -> bool:
    p = os.environ.get("V2_OOS_DEVIATION")
    return bool(p) and Path(p).resolve() == D3_DEVIATION.resolve() and D3_DEVIATION.is_file() \
        and sha256(D3_DEVIATION) == D3_SHA


def lock_records(out: Path) -> list:
    seen, found = set(), []
    for d in (LOCK_DIR, out):
        for f in LOCK_FILES:
            p = (Path(d) / f).resolve()
            if p.exists() and p not in seen:
                seen.add(p)
                found.append(p)
    return found


def fomc_sched_path() -> Path:
    return R.WORK / "fedspeak_v2" / "corpus" / "fomc_dates.csv"  # the 93 scheduled meetings 2015-2026


def load_fomc_scheduled() -> pd.Series:
    a = pd.read_csv(R.FOMC_S01, parse_dates=["fomc_date"])["fomc_date"]
    b = pd.read_csv(fomc_sched_path(), parse_dates=["fomc_date"])["fomc_date"]
    return pd.Series(sorted(set(a[a < "2015-01-01"]) | set(b)))


def scheduled_only(chosen: str, period: str, windows: list[tuple[str, tuple[str, str]]], end: str) -> list[dict]:
    t, e = chosen[:2], chosen[3:]
    docs = R.load_docs("run")
    ext = R.load_ext_speeches("run")
    ohlc, rf, dgs2, cal = R.market(period)
    docs = docs[docs["date"] <= end]
    ext = ext[ext["speech_date"] <= end]
    sig = R.build_signals(docs, ext, cal, dgs2)
    fs = load_fomc_scheduled()
    rows = []
    for label, fomc in (("registered_101_dates", R.load_fomc()), ("scheduled_only_93_dates", fs)):
        w, _ = R.combo_weights(sig["Z"][t], e, ohlc, fomc)
        sim = R.simulate(w, e, ohlc, rf)
        for wn, win in windows:
            rows.append({"combo": chosen, "derisk_list": label, "window": wn, **R.stats_row(sim, win)})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc-scores", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--placebo", action="store_true")
    ap.add_argument("--skip-if-complete", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    if a.placebo and "placebo" not in str(out).lower():
        raise SystemExit("refusing: placebo output folder must contain 'placebo'")
    if not a.placebo and "placebo" in str(a.doc_scores).lower():
        raise SystemExit("refusing: real mode pointed at placebo scores")
    if a.placebo and out.resolve() == LOCK_DIR.resolve():
        raise SystemExit("refusing: a placebo run may not write to the committed v2 results folder")
    rec = [] if a.placebo else lock_records(out)
    d3 = bool(rec) and not a.placebo and not a.skip_if_complete and d3_unlocked()
    if d3:
        # deviation D-3: one out-of-sample evaluation beside the committed failed-rule record, never a second one
        if out.resolve() != D3_OUT.resolve():
            raise SystemExit(f"refusing: the D-3 out-of-sample evaluation writes only to {D3_OUT}")
        rec = [r for r in rec if r != (LOCK_DIR / "oos_not_evaluated.json").resolve()]
    if rec:
        # one-shot out-of-sample lock: the committed decision record (or one in --out) ends the v2 run for good
        summ_dir = rec[0].parent
        if a.skip_if_complete:
            prev = json.loads((summ_dir / "summary_is.json").read_text(encoding="utf-8")).get("doc_scores_sha256")
            if prev != sha256(a.doc_scores):
                raise SystemExit(f"refusing: {a.doc_scores} (sha256 {sha256(a.doc_scores)}) is not the file the "
                                 f"completed v2 run used ({prev})")
            print(f"v2 one-shot OOS lock: decision record {rec[0]} exists (same doc_scores sha256); "
                  "the v2 run is complete and was not re-run. Nothing recomputed.")
            return
        raise SystemExit(f"v2 one-shot OOS lock: decision record {rec[0]} exists; the out-of-sample window is "
                         "evaluated once. Nothing recomputed.")
    global R
    sys.path.insert(0, str(HERE))
    import run_v2 as R  # noqa: E402  (imports gqh-flow-clock's src.engine)
    got = sha256(R.PREREG)
    if got != PREREG_SHA_NOW:
        raise SystemExit(f"pre-registration hash {got} != {PREREG_SHA_NOW}")
    R.PREREG_SHA = PREREG_SHA_NOW
    R.DOC_SCORES = Path(a.doc_scores)
    out.mkdir(parents=True, exist_ok=True)
    if a.placebo:
        (out / "PLACEBO_README.txt").write_text("PLACEBO chain test on random scores. Not results.\n", encoding="utf-8")

    res = R.pipeline_is("run", out)
    summ = res["summary"]
    summ["mode"] = "PLACEBO chain test" if a.placebo else "run (chrono walk-forward stance scores)"
    summ["prereg_sha256_checked"] = PREREG_SHA_NOW
    summ["doc_scores"] = str(R.DOC_SCORES)
    summ["doc_scores_sha256"] = sha256(R.DOC_SCORES)
    jdump(summ, out / "summary_is.json")
    print(json.dumps({k: summ[k] for k in ("chosen", "selection_sharpe_net1x", "validation_sharpe_net1x",
                                           "full_is_sharpe_net2x", "decision_rule_passed")}, indent=1, default=str))
    chosen = res["chosen"]
    is_w = [("selection", R.SEL), ("validation", R.VAL), ("full_is", R.FULL_IS)]
    pd.DataFrame(scheduled_only(chosen, "IS", is_w, R.IS_END)).to_csv(out / "sens_scheduled_only_is.csv", index=False)

    if not res["passed"] and not d3:
        jdump({"oos_evaluated": False, "reason": "decision rule failed (validation net Sharpe <= 0 or full-IS 2x "
               "Sharpe <= 0.5)"}, out / "oos_not_evaluated.json")
        print("Decision rule failed: out-of-sample NOT evaluated.")
        return
    if not res["passed"]:
        print("Decision rule failed (verdict stands); deviation D-3: out-of-sample evaluated once for reporting.")
    if a.placebo:
        jdump({"oos_evaluated": False, "reason": "PLACEBO chain test: the out-of-sample stage is never run on "
               "placebo scores (rule passed on random scores)"}, out / "oos_not_evaluated_placebo.json")
        print("PLACEBO: decision rule passed on random scores; out-of-sample deliberately NOT evaluated.")
        return
    rec = R.stage_oos(res, out)  # writes oos_chosen.json before anything else on OOS
    print("OOS (evaluated once):", json.dumps(rec, indent=1, default=str))
    pd.DataFrame(scheduled_only(chosen, "FWD", [("oos", R.OOS)], R.OOS[1])).to_csv(
        out / "sens_scheduled_only_oos.csv", index=False)


if __name__ == "__main__":
    main()
