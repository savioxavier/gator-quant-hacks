"""Per-meeting completion and failures of a fedpress run. Reads only done-markers, failure markers and claims,
so it is safe on a login node (activate the env first: `source env/activate.sh`).

    python slurm/status.py                        # meeting x stage matrix, per-stage totals, failures
    python slurm/status.py --failed               # failures only: stage, meeting, error line, log file
    python slurm/status.py --failed-ids voice     # presser_ids whose voice stage failed (one per line)
    python slurm/status.py --next                 # earliest submit_all.sh step with unfinished work
    python slurm/status.py --check asr,turns [--shard I/N | --id ID]   # exit 3 if no meeting finished them
    python slurm/status.py --json                 # the same summary as JSON
    python slurm/status.py --jobs                 # also list your queued/running fp-* Slurm jobs

Cell codes: D done, n not applicable, F failed, C claimed (running now), b blocked (an upstream stage is not
done), . not run yet, x stage disabled.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))

from fedpress import STAGES, io
from fedpress import manifest as mf
from fedpress.config import Config, load
from fedpress.stage import load_stage

# submit_all.sh steps in order, and the stages each one runs
STEPS: dict[str, tuple[str, ...]] = {
    "fetch": ("fetch",), "av": ("audio", "frames"), "speech": ("asr", "turns", "diarize", "voice"),
    "face": ("face",), "text": ("text",), "agg": ("aggregate",),
}
OPEN = {"F", ".", "b"}


def _requires() -> dict[str, tuple[str, ...]]:
    out: dict[str, tuple[str, ...]] = {}
    for s in STAGES:
        try:
            out[s] = tuple(load_stage(s).SPEC.requires)
        except Exception:  # a stage module that cannot be imported here: no requirement check
            out[s] = ()
    return out


def cell(cfg: Config, paths: io.MeetingPaths, stage: str, req: dict[str, tuple[str, ...]],
         memo: dict[str, str]) -> str:
    if stage in memo:
        return memo[stage]
    info = io.read_done(paths, stage)
    if cfg.section(stage).get("enabled", True) is False:
        c = "x"
    elif info and io.is_done(paths, stage):
        c = "n" if info.get("status") == "not_applicable" else "D"
    elif io.failed_path(paths, stage).exists():
        c = "F"
    elif io.claim_holder(paths, stage):
        c = "C"
    elif any(cell(cfg, paths, r, req, memo) not in ("D", "n", "x") for r in req.get(stage, ())):
        c = "b"
    else:
        c = "."
    memo[stage] = c
    return c


def summarise(cfg: Config, meetings: list[mf.Meeting]) -> dict[str, Any]:
    req = _requires()
    rows, failures = [], []
    totals: dict[str, Counter[str]] = {s: Counter() for s in STAGES}
    secs: dict[str, list[float]] = {s: [] for s in STAGES}
    video_h: dict[str, float] = {s: 0.0 for s in STAGES}
    for m in meetings:
        paths = io.MeetingPaths.of(cfg, m.presser_id)
        memo: dict[str, str] = {}
        cells = {s: cell(cfg, paths, s, req, memo) for s in STAGES}
        for s, c in cells.items():
            totals[s][c] += 1
            if c == "D":
                e = float((io.read_done(paths, s) or {}).get("elapsed_s") or 0)
                secs[s].append(e)
                video_h[s] += (m.duration_s or 0) / 3600
            elif c == "F":
                f = io.read_json(io.failed_path(paths, s))
                err = str(f.get("error", "")).splitlines()[0][:220] if f.get("error") else "?"
                failures.append({"stage": s, "presser_id": m.presser_id, "chair": m.chair, "error": err,
                                 "failed_utc": f.get("failed_utc"), "run_id": f.get("run_id"),
                                 "log": str(cfg.root_path("logs") / s / f"{m.presser_id}.jsonl")})
        rows.append({"presser_id": m.presser_id, "date": m.presser_date.isoformat(), "chair": m.chair, **cells})
    timing = {s: {"n": len(v), "sum_min": round(sum(v) / 60, 2), "mean_s": round(sum(v) / len(v), 1) if v else None,
                  "s_per_video_h": round(sum(v) / video_h[s], 1) if video_h[s] else None} for s, v in secs.items()}
    return {"root": str(cfg.root), "meetings": len(meetings), "rows": rows, "failures": failures,
            "totals": {s: dict(c) for s, c in totals.items()}, "timing": timing, "next_step": next_step(rows)}


def next_step(rows: list[dict[str, Any]]) -> str | None:
    for step, stages in STEPS.items():
        if any(r[s] in OPEN for r in rows for s in stages):
            return step
    return None


def training(cfg: Config) -> str:
    try:
        from fedpress.train import labels as lab
        from fedpress.train import stance_walkforward as sw

        _, meta = lab.load(cfg)
        jobs = sw.plan(cfg, sw.sample_years(cfg), int(meta["max_year"]))
        done = sum(sw.job_done(cfg, j, meta["sha256"]) for j in jobs)
        return f"{done}/{len(jobs)} fine-tunes done ({len({j.key for j in jobs})} models x seeds)"
    except Exception as e:  # labels not prepared yet, or no pandas on this python
        return f"unavailable ({type(e).__name__}: {str(e)[:120]})"


def slurm_jobs() -> str:
    if shutil.which("squeue") is None:
        return "(squeue not found)"
    out = subprocess.run(["squeue", "--me", "--format=%.18i %.14j %.9T %.10M %.12l %.6D %R"], capture_output=True,
                         text=True, check=False).stdout.splitlines()
    return "\n".join(line for k, line in enumerate(out) if k == 0 or " fp-" in line)


def print_matrix(s: dict[str, Any], failed_only: bool) -> None:
    if not failed_only:
        print(f"{'presser_id':<10} {'chair':<7} " + " ".join(f"{st[:5]:>5}" for st in STAGES))
        for r in s["rows"]:
            print(f"{r['presser_id']:<10} {r['chair']:<7} " + " ".join(f"{r[st]:>5}" for st in STAGES))
        print("# D done, n n/a, F failed, C running, b blocked upstream, . to do, x disabled")
        print(f"# {'stage':<9} {'counts':<34} {'done':>4} {'sum min':>8} {'mean s':>7} {'s/video-h':>9}")
        for st in STAGES:
            t = s["timing"][st]
            counts = " ".join(f"{k}={v}" for k, v in sorted(s["totals"][st].items()))
            print(f"# {st:<9} {counts:<34} {t['n']:>4} {t['sum_min']:>8} {t['mean_s'] or '':>7} {t['s_per_video_h'] or '':>9}")
    print(f"# failures: {len(s['failures'])}")
    for f in s["failures"]:
        print(f"F {f['stage']:<9} {f['presser_id']} {f['chair']:<7} {f['error']}\n    log: {f['log']}")
    print(f"# next step with unfinished work: {s['next_step'] or 'none (all done)'}   root: {s['root']}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--config")
    p.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    p.add_argument("--shard", help="I/N: only this array task's group (same rule as the CLI)")
    p.add_argument("--id", dest="presser_id", help="one meeting")
    p.add_argument("--failed", action="store_true", help="failures only")
    p.add_argument("--failed-ids", metavar="STAGE", help="print presser_ids whose STAGE failed")
    p.add_argument("--check", metavar="STAGES", help="exit 3 when no selected meeting finished one of STAGES")
    p.add_argument("--next", action="store_true", help="print the earliest step with unfinished work")
    p.add_argument("--json", action="store_true")
    p.add_argument("--jobs", action="store_true", help="also show your fp-* Slurm jobs")
    a = p.parse_args(argv)
    sets = list(a.set) + [kv for kv in os.environ.get("FP_SET", "").split() if kv]
    cfg = load(a.config, sets)
    shard = tuple(int(x) for x in a.shard.split("/")) if a.shard else None
    meetings = mf.select(cfg, presser_id=a.presser_id, all_=not a.presser_id, shard=shard)  # type: ignore[arg-type]
    s = summarise(cfg, meetings)
    if a.check:
        bad = []
        for st in a.check.split(","):
            t = s["totals"][st]
            if (t.get("D", 0) + t.get("x", 0)) == 0 and t.get("F", 0) > 0:
                bad.append(st)
        if bad:
            print(f"systemic failure: no meeting finished {bad}; first errors:", file=sys.stderr)
            for f in [f for f in s["failures"] if f["stage"] in bad][:3]:
                print(f"  {f['stage']} {f['presser_id']}: {f['error']}", file=sys.stderr)
            return 3
        return 0
    if a.failed_ids:
        print("\n".join(f["presser_id"] for f in s["failures"] if f["stage"] == a.failed_ids))
        return 0
    if a.next:
        print(s["next_step"] or "none")
        return 0
    if a.json:
        print(json.dumps(s | {"training": training(cfg)}, indent=1, default=str))
        return 0
    print_matrix(s, a.failed)
    if not a.failed:
        print(f"# stance training: {training(cfg)}")
    if a.jobs:
        print(slurm_jobs())
    return 0


if __name__ == "__main__":
    sys.exit(main())
