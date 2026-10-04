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

Reproduction of that run (it recomputes, it never evaluates):

    GQH_REPO=... GQH_DATA_DIR=... V2_WORK_ROOT=... run_v2_chrono.py --reproduce [--doc-scores <doc_scores.parquet>]

--reproduce recomputes the committed in-sample run and its one D-3 out-of-sample evaluation with the same code path,
inputs, combination and windows, and compares every number with the committed files. It refuses unless the committed
D-3 record backtests/results/v2_oos/run/oos_chosen.json and the failed-rule record
backtests/results/v2/oos_not_evaluated.json (oos_evaluated false) exist, and refuses V2_OOS_DEVIATION. It clears and
writes only <BACKTEST_RERUN_DIR>/v2_reproduce (default backtests/rerun/v2_reproduce, git-ignored; an explicit
BACKTEST_RERUN_DIR must lie outside this repository and not above it) and writes no decision record (the out-of-sample
record is oos_reproduced.json, the failed-rule record oos_not_evaluated_reproduced.json). It chooses nothing: the
in-sample selection must give the committed combination, the decision rule must fail as committed, and the in-sample
files must agree with backtests/results/v2 before the out-of-sample stage runs. Compared, at rtol 1e-9 / atol 1e-12
(backtests/tools/compare_results.py), with the fixed file sets of the committed tree (commit 6a61ef9, RUN_LOG.md; a
missing file is a difference): backtests/results/v2 (7 in-sample files and the failed-rule record),
backtests/results/v2_oos/run (18 files: out-of-sample, portfolio, Variant A) and backtests/results/v2_oos/metrics.csv
and daily_returns.parquet (report_v2_oos.py functions). Prints PASS or FAIL and the headline numbers (reproduced vs
committed), writes v2_reproduce/reproduce_report.json, and exits 1 on any difference.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import sys
import os
from pathlib import Path

import numpy as np

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
D3_RECORD = D3_OUT / "oos_chosen.json"                  # the committed record of the one out-of-sample evaluation
TEAM = HERE.parents[1]
RULE_RECORD = LOCK_DIR / "oos_not_evaluated.json"       # the committed failed-rule record (the verdict stands)
RULE_FAILED = {"oos_evaluated": False, "reason": "decision rule failed (validation net Sharpe <= 0 or full-IS 2x "
               "Sharpe <= 0.5)"}                        # what main() writes there when the rule fails
# --reproduce compares these committed files (tree of commit 6a61ef9, RUN_LOG.md); a missing one is a difference
IS_FILES = ("by_chair_is.csv", "portfolio.csv", "portfolio_info.json", "selection.csv", "sens_scheduled_only_is.csv",
            "summary_is.json", "windows_all.csv")                         # backtests/results/v2
OOS_RUN_FILES = ("by_chair_is.csv", "by_chair_oos.csv", "daily_T4xE1_full.parquet", "daily_T4xE1_is.parquet",
                 "daily_VariantA_frozen_T0fxE1_full.parquet", "daily_excess_all_combos_is.parquet",
                 "daily_portfolio_full.parquet", "oos_chosen.json", "portfolio.csv", "portfolio_info.json",
                 "portfolio_info_oos.json", "portfolio_oos.csv", "selection.csv", "sens_scheduled_only_is.csv",
                 "sens_scheduled_only_oos.csv", "signals_entry_session.parquet", "summary_is.json",
                 "windows_all.csv")                                         # backtests/results/v2_oos/run
REPORT_FILES = ("metrics.csv", "daily_returns.parquet")                     # backtests/results/v2_oos
RUN_LOG_COMMIT = "6a61ef9"                              # the commit holding the code whose sha256 RUN_LOG.md lists


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


# ------------------------------------------------------------------------ --reproduce (recomputes, never evaluates)
def rel(p) -> str:
    try:
        return Path(p).resolve().relative_to(TEAM.resolve()).as_posix()
    except ValueError:
        return str(p)


def max_abs_diff(ref: Path, new: Path) -> float:
    """Largest absolute difference between the numbers of two files (NaN = NaN; NaN vs a number counts as inf)."""
    def num(x, y) -> float:
        fx, fy = float(x), float(y)
        if math.isnan(fx) or math.isnan(fy):
            return 0.0 if math.isnan(fx) and math.isnan(fy) else math.inf
        return abs(fx - fy)

    def walk(a, b) -> float:
        if isinstance(a, dict) and isinstance(b, dict):
            return max([walk(a[k], b[k]) for k in a if k in b] or [0.0])
        if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
            return max([walk(x, y) for x, y in zip(a, b)] or [0.0])
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) \
                and not isinstance(a, bool) and not isinstance(b, bool):
            return num(a, b)
        return 0.0
    if ref.suffix == ".json":
        return walk(json.loads(ref.read_text(encoding="utf-8")), json.loads(new.read_text(encoding="utf-8")))
    rd = pd.read_parquet if ref.suffix == ".parquet" else pd.read_csv
    a, b = rd(ref), rd(new)
    if len(a) != len(b):
        return math.inf
    m = 0.0
    for c in a.columns:
        if c in b.columns and pd.api.types.is_numeric_dtype(a[c]) and pd.api.types.is_numeric_dtype(b[c]):
            x, y = a[c].to_numpy(float), b[c].to_numpy(float)
            d = np.abs(x - y)
            d[np.isnan(x) & np.isnan(y)] = 0.0
            d[np.isnan(d)] = math.inf
            m = max(m, float(d.max()) if len(d) else 0.0)
    return m


def compare_files(label: str, ref_dir: Path, pairs: list) -> dict:
    """pairs: (committed file, reproduced file, committed JSON keys left out). Tolerance and rules of
    backtests/tools/compare_results.py; parquet indexes must be equal as well."""
    sys.path.insert(0, str(HERE.parent / "tools"))
    import compare_results as CR  # noqa: E402
    files = []
    for ref, new, drop in pairs:
        diffs: list = []
        mad = None
        if not ref.is_file():
            diffs.append("missing in the committed results")
        elif not new.is_file():
            diffs.append("missing in the reproduction")
        else:
            try:
                if ref.suffix == ".json":
                    a = json.loads(ref.read_text(encoding="utf-8"))
                    for k in drop:
                        a.pop(k, None)
                    CR.cmp_json(a, json.loads(new.read_text(encoding="utf-8")), ref.name, diffs)
                else:
                    CR.cmp_csv(ref, new, diffs)
                    if ref.suffix == ".parquet" and not pd.read_parquet(ref).index.equals(pd.read_parquet(new).index):
                        diffs.append("index (dates) differs")
                mad = max_abs_diff(ref, new)
            except Exception as e:  # an unreadable file counts as a difference
                diffs.append(f"error: {e!r}")
        files.append({"committed": rel(ref), "reproduced": new.name, "agree": not diffs, "max_abs_diff": mad,
                      "diffs": diffs[:10]})
    n_ok = sum(f["agree"] for f in files)
    mads = [f["max_abs_diff"] for f in files if f["max_abs_diff"] is not None]
    return {"label": label, "committed": rel(ref_dir), "n_files": len(files), "n_agree": n_ok,
            "max_abs_diff": max(mads) if mads else None, "files": files}


def run_log_hashes() -> dict:
    """sha256 of the code and inputs listed in backtests/results/v2_oos/RUN_LOG.md against the files used now."""
    txt = (D3_OUT.parent / "RUN_LOG.md").read_text(encoding="utf-8")
    rows = {}
    for m in re.finditer(r"^- (data cache )?`([^`]+)` sha256 ([0-9a-f]{64})", txt, re.M):
        cache, name, want = m.groups()
        if cache:
            p = Path(R.E.C.DATA_DIR) / name
        elif name.startswith("<v2 work root>/"):
            p = R.WORK / name.split("/", 1)[1]
        else:
            p = TEAM / name
        rows[name] = (p, want)
    m = re.search(r"src/engine\.py sha256 ([0-9a-f]{64})", txt)
    if m:
        rows["gqh-flow-clock src/engine.py"] = (Path(R.E.__file__), m.group(1))
    out = {}
    for name, (p, want) in rows.items():
        got = sha256(p) if p.is_file() else None
        out[name] = {"run_log": want, "now": got, "same": got == want}
    return out


def reproduce_dir() -> Path:
    """<BACKTEST_RERUN_DIR>/v2_reproduce, the one folder --reproduce clears and writes. It must be named v2_reproduce
    and lie inside the repo's git-ignored rerun area (backtests/rerun) or under an explicit BACKTEST_RERUN_DIR outside
    this repository and not above it; never backtests/results, the backtests folder, the repo root, a folder above any
    of them, or one below backtests/results."""
    area = (HERE.parent / "rerun").resolve()
    env = os.environ.get("BACKTEST_RERUN_DIR")
    rerun = Path(env).resolve() if env else area
    out = (rerun / "v2_reproduce").resolve()            # resolved: a link cannot send the clearing elsewhere
    results, bts, repo = (HERE.parent / "results").resolve(), HERE.parent.resolve(), TEAM.resolve()
    why = ""
    if out.name != "v2_reproduce":
        why = "its name is not v2_reproduce"
    elif any(out == p or out in p.parents for p in (results, bts, repo)):
        why = "it is backtests/results, the backtests folder or the repo root, or a folder above them"
    elif results in out.parents:
        why = "it lies below backtests/results"
    elif area not in out.parents and (rerun == repo or repo in rerun.parents or rerun in repo.parents):
        why = f"it lies neither inside {area} (git-ignored) nor under a BACKTEST_RERUN_DIR outside this repository"
    if why:
        raise SystemExit(f"refusing: --reproduce clears and writes {out}, but {why} (BACKTEST_RERUN_DIR "
                         f"{env or 'unset'})")
    return out


def headline(out: Path, chosen: str) -> dict:
    """The quoted v2 numbers, reproduced next to committed (None where the reproduction did not get that far)."""
    def g(d, *keys):
        for k in keys:
            d = d.get(k) if isinstance(d, dict) else None
        return None if d is None else float(d)

    def windows(d: Path) -> dict:                        # the chosen combination's in-sample rows
        p = d / "windows_all.csv"
        if not p.is_file():
            return {}
        w = pd.read_csv(p)
        return {r["window"]: r for r in w[w["combo"] == chosen].to_dict("records")}

    def jread(p: Path) -> dict:
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}

    def portfolios(d: Path) -> dict:
        p = d / "portfolio_oos.csv"
        return {r["portfolio"]: r for r in pd.read_csv(p).to_dict("records")} if p.is_file() else {}

    src = {"reproduced": (windows(out), jread(out / "oos_reproduced.json"), portfolios(out)),
           "committed": (windows(LOCK_DIR), jread(D3_RECORD), portfolios(D3_OUT))}

    def pair(i: int, *keys) -> dict:
        return {k: g(v[i], *keys) for k, v in src.items()}

    return {"combo": chosen,
            "in_sample_sharpe": {w: {b: pair(0, w, f"sharpe_{b}") for b in ("net1x", "net2x")}
                                 for w in ("selection", "validation", "full_is")},
            "oos_window": jread(D3_RECORD).get("window"),
            "oos": {k: pair(1, k) for k in ("sharpe_net1x", "sharpe_net2x", "sharpe_gross", "ann_excess_arith", "vol",
                                           "max_dd_excess")},
            "portfolio_oos_sharpe": {p: {b: pair(2, p, f"sharpe_{b}") for b in ("net1x", "net2x")}
                                     for p in ("core_ER_6", f"core_ER_6+{chosen}")}}


def show_headline(h: dict | None) -> None:
    if not h:
        print("  headline: not available (the reproduction stopped before it)")
        return

    def f(p: dict, pct: bool = False) -> str:
        def one(x):
            return "n/a" if x is None else (f"{100 * x:.2f}%" if pct else f"{x:.4f}")
        return f"{one(p['reproduced'])} | {one(p['committed'])}"
    s, o, w = h["in_sample_sharpe"], h["oos"], h["oos_window"] or ["?", "?"]
    print(f"  headline, {h['combo']} (reproduced | committed):")
    for b, name in (("net1x", "net 1x"), ("net2x", "net 2x")):
        print(f"    in-sample Sharpe {name}: selection {f(s['selection'][b])}, validation {f(s['validation'][b])}, "
              f"full IS {f(s['full_is'][b])}" + (" (decision rule: full IS net 2x > 0.5)" if b == "net2x" else ""))
    print(f"    out-of-sample {w[0]}..{w[1]} Sharpe: net 1x {f(o['sharpe_net1x'])}, net 2x {f(o['sharpe_net2x'])}, "
          f"gross {f(o['sharpe_gross'])}")
    print(f"    out-of-sample ann. return (arith, net 1x) {f(o['ann_excess_arith'], True)}, vol {f(o['vol'], True)}, "
          f"max drawdown {f(o['max_dd_excess'], True)}")
    print("    portfolio out-of-sample Sharpe net 1x / net 2x: " + "; ".join(
        f"{p} {f(v['net1x'])} / {f(v['net2x'])}" for p, v in h["portfolio_oos_sharpe"].items()))


def reproduce(doc_scores: Path) -> None:
    """Recompute the committed in-sample run and its one D-3 out-of-sample evaluation; compare with the committed files.
    The in-sample files are compared first: the out-of-sample window is recomputed only if they agree."""
    if not D3_RECORD.is_file():
        raise SystemExit(f"refusing to reproduce: the committed D-3 record {D3_RECORD} does not exist. A reproduction "
                         "recomputes the one out-of-sample evaluation that was made; it never makes a first one.")
    rule = json.loads(RULE_RECORD.read_text(encoding="utf-8")) if RULE_RECORD.is_file() else {}
    if rule.get("oos_evaluated") is not False:
        raise SystemExit(f"refusing to reproduce: the committed failed-rule record {RULE_RECORD} is missing or does "
                         "not say oos_evaluated false. The D-3 evaluation is reproduced only beside that verdict.")
    if os.environ.get("V2_OOS_DEVIATION"):
        raise SystemExit("refusing: --reproduce never uses the D-3 unlock; unset V2_OOS_DEVIATION")
    out = reproduce_dir()
    d3rec = json.loads(D3_RECORD.read_text(encoding="utf-8"))
    is_ref = json.loads((LOCK_DIR / "summary_is.json").read_text(encoding="utf-8"))
    used = {json.loads((d / "summary_is.json").read_text(encoding="utf-8")).get("doc_scores_sha256")
            for d in (LOCK_DIR, D3_OUT)}
    if used != {sha256(doc_scores)}:
        raise SystemExit(f"refusing: {doc_scores} (sha256 {sha256(doc_scores)}) is not the file the committed runs "
                         f"used ({sorted(used)})")
    global R
    sys.path.insert(0, str(HERE))
    import run_v2 as R  # noqa: E402  (imports gqh-flow-clock's src.engine)
    got = sha256(R.PREREG)
    if got != PREREG_SHA_NOW:
        raise SystemExit(f"pre-registration hash {got} != {PREREG_SHA_NOW}")
    if list(R.OOS) != list(d3rec["window"]):
        raise SystemExit(f"refusing: out-of-sample window {list(R.OOS)} is not the committed one {d3rec['window']}")
    R.PREREG_SHA = PREREG_SHA_NOW
    R.DOC_SCORES = doc_scores
    if out.exists():
        shutil.rmtree(out)                              # stale files must not stand in for missing ones (reproduce_dir)
    out.mkdir(parents=True)
    chosen = d3rec["chosen"]                            # the committed combination; nothing is chosen here
    rep = {"verdict": None, "what": "reproduction of the committed v2 in-sample run and its one out-of-sample "
           "evaluation under deviation D-3; recomputed, not evaluated; no decision record written; nothing chosen",
           "headline": None,
           "reproduced_utc": pd.Timestamp.now("UTC").isoformat(),
           "committed_d3_record": {"path": rel(D3_RECORD), "sha256": sha256(D3_RECORD), "chosen": chosen,
                                   "window": d3rec["window"], "evaluated_once_utc": d3rec["evaluated_once_utc"]},
           "committed_rule_record": {"path": rel(RULE_RECORD), "sha256": sha256(RULE_RECORD), **rule},
           "doc_scores_sha256": sha256(doc_scores), "prereg_sha256": got,
           "windows": {"selection": R.SEL, "validation": R.VAL, "full_is": R.FULL_IS, "oos": R.OOS},
           "tolerance": {"rtol": 1e-9, "atol": 1e-12, "rule": "backtests/tools/compare_results.py"},
           "output_dir": str(out), "oos_recomputed": False, "comparisons": [], "failures": []}

    def disagree(cs: list) -> list:
        return [f"{f['committed']}: " + "; ".join(f["diffs"][:3]) for c in cs for f in c["files"] if not f["agree"]]
    try:
        rep["code_and_inputs_vs_run_log"] = run_log_hashes()
        rep["run_log_note"] = (f"the code sha256 in RUN_LOG.md are those of the files committed at {RUN_LOG_COMMIT} "
                               "(the D-3 run: 1c8c9e1 plus its unlock); run_v2.py and run_v2_chrono.py differ from "
                               "them because --reproduce was added afterwards")
        res = R.pipeline_is("run", out)
        summ = res["summary"]
        summ["mode"] = "run (chrono walk-forward stance scores)"
        summ["prereg_sha256_checked"] = PREREG_SHA_NOW
        summ["doc_scores"] = str(R.DOC_SCORES)
        summ["doc_scores_sha256"] = sha256(R.DOC_SCORES)
        summ["reproduction_of"] = rel(D3_RECORD)
        jdump(summ, out / "summary_is.json")
        rep["chosen"] = {"committed": chosen, "reproduced_selection": res["chosen"]}
        rep["decision_rule_passed"] = {"committed": is_ref["decision_rule_passed"], "reproduced": res["passed"]}
        if res["chosen"] != chosen:
            rep["failures"].append(f"in-sample selection gives {res['chosen']}, the committed choice is {chosen}; "
                                   "out-of-sample not recomputed")
        if res["passed"] != is_ref["decision_rule_passed"]:
            rep["failures"].append(f"decision rule passed {res['passed']}, committed {is_ref['decision_rule_passed']}; "
                                   "out-of-sample not recomputed")
        if not res["passed"]:                           # the record main() writes, under a name no lock reads
            jdump(RULE_FAILED, out / "oos_not_evaluated_reproduced.json")
        if not rep["failures"]:
            is_w = [("selection", R.SEL), ("validation", R.VAL), ("full_is", R.FULL_IS)]
            pd.DataFrame(scheduled_only(chosen, "IS", is_w, R.IS_END)).to_csv(out / "sens_scheduled_only_is.csv",
                                                                             index=False)
        # in-sample first: nothing is computed on the out-of-sample window unless these agree
        rep["comparisons"].append(compare_files("in-sample", LOCK_DIR, [(LOCK_DIR / f, out / f, ()) for f in IS_FILES]))
        rep["comparisons"].append(compare_files("failed-rule record", LOCK_DIR, [
            (RULE_RECORD, out / "oos_not_evaluated_reproduced.json", ())]))
        bad = disagree(rep["comparisons"])
        if bad:
            rep["failures"] += bad + ["the in-sample results do not reproduce backtests/results/v2; out-of-sample not "
                                      "recomputed"]
        if not rep["failures"]:
            R.stage_oos(res, out, reproduce_of=D3_RECORD)
            rep["oos_recomputed"] = True
            pd.DataFrame(scheduled_only(chosen, "FWD", [("oos", R.OOS)], R.OOS[1])).to_csv(
                out / "sens_scheduled_only_oos.csv", index=False)
            import report_v2_oos as RP  # noqa: E402  (the D-3 report's own metric code)
            series = RP.load(out)
            RP.table(series).to_csv(out / "metrics.csv", index=False)
            RP.daily(series).to_parquet(out / "daily_returns.parquet")
            rec_keys = ("evaluated_once_utc", "authorised_by")  # when and under what the committed record was made
            oos_cmp = [compare_files("out-of-sample run (D-3)", D3_OUT, [
                (D3_OUT / f, out / "oos_reproduced.json", rec_keys) if f == "oos_chosen.json"
                else (D3_OUT / f, out / f, ()) for f in OOS_RUN_FILES]),
                compare_files("out-of-sample report (D-3)", D3_OUT.parent, [
                    (D3_OUT.parent / f, out / f, ()) for f in REPORT_FILES])]
            rep["comparisons"] += oos_cmp
            rep["failures"] += disagree(oos_cmp)
        rep["headline"] = headline(out, chosen)
    except BaseException as e:                          # a refusal or crash mid-run is a FAIL, never a PASS
        rep["failures"].append(f"error: {e!r}")
        raise
    finally:
        rep["verdict"] = "FAIL" if rep["failures"] else "PASS"
        jdump(rep, out / "reproduce_report.json")
    print(f"v2 reproduce: {rep['verdict']}")
    print(f"  committed D-3 record {rel(D3_RECORD)}: {chosen} {d3rec['window'][0]}..{d3rec['window'][1]}, evaluated "
          f"once {d3rec['evaluated_once_utc']}")
    print(f"  in-sample selection: {res['chosen']} (committed {chosen}); decision rule passed {res['passed']} "
          f"(committed {is_ref['decision_rule_passed']})"
          + ("; the failed verdict stands" if not res["passed"] else ""))
    for c in rep["comparisons"]:
        print(f"  {c['label']} vs {c['committed']}: {c['n_agree']}/{c['n_files']} files agree, "
              f"max abs diff {c['max_abs_diff']}")
    if not rep["oos_recomputed"]:
        print("  out-of-sample: NOT recomputed (the in-sample checks above failed)")
    show_headline(rep["headline"])
    ci = rep["code_and_inputs_vs_run_log"]
    print(f"  code and inputs vs RUN_LOG.md (code as committed at {RUN_LOG_COMMIT}): "
          f"{sum(v['same'] for v in ci.values())}/{len(ci)} sha256 equal; differ: "
          + (", ".join(k for k, v in ci.items() if not v["same"]) or "none"))
    print(f"  report: {out / 'reproduce_report.json'} (no decision record written; nothing evaluated or chosen)")
    if rep["failures"]:
        print("v2 reproduce: FAIL: the re-run does NOT reproduce the committed results:")
        for f in rep["failures"]:
            print(f"  - {f}")
        raise SystemExit(1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc-scores")
    ap.add_argument("--out")
    ap.add_argument("--placebo", action="store_true")
    ap.add_argument("--skip-if-complete", action="store_true")
    ap.add_argument("--reproduce", action="store_true",
                    help="recompute the committed D-3 run into <BACKTEST_RERUN_DIR>/v2_reproduce and compare it")
    a = ap.parse_args()
    if a.reproduce:
        if a.out or a.placebo or a.skip_if_complete:
            ap.error("--reproduce writes only to <BACKTEST_RERUN_DIR>/v2_reproduce; it takes no --out, --placebo or "
                     "--skip-if-complete")
        return reproduce(Path(a.doc_scores or HERE / "score" / "doc_scores.parquet").resolve())
    if not a.doc_scores or not a.out:
        ap.error("the following arguments are required: --doc-scores, --out")
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
