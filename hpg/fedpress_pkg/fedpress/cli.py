"""Command line.

    python -m fedpress.cli <stage> (--index N | --date YYYY-MM-DD | --id YYYYMMDD | --all) [--force] [--claim]
                                   [--shard I/N | --shard slurm] [--dry-run] [--set key=value ...]
    python -m fedpress.cli launch <stage[,stage...]> --all [--gpus N] [--workers-per-gpu K] [--force]
    python -m fedpress.cli list | status | config | doctor | prefetch-models [--keys a,b]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from . import STAGES, io, log as logmod
from . import manifest as mf
from .config import HARD_MAX_GPUS, Config, ConfigError, apply_env, load

UTILITIES = ("list", "status", "config", "doctor", "launch", "prefetch-models")


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m fedpress.cli", description="FOMC presser feature build.")
    p.add_argument("command", help=f"a stage ({', '.join(STAGES)}) or one of: {', '.join(UTILITIES)}")
    p.add_argument("stages", nargs="?", help="launch only: comma-separated stages run one after another")
    sel = p.add_mutually_exclusive_group()
    sel.add_argument("--index", type=int, help="0-based position in the configured sample (see `list`)")
    sel.add_argument("--date", help="presser or meeting date YYYY-MM-DD")
    sel.add_argument("--id", dest="presser_id", help="presser id YYYYMMDD")
    sel.add_argument("--all", action="store_true", help="the whole configured sample")
    p.add_argument("--force", action="store_true", help="redo even if the done-marker exists")
    p.add_argument("--claim", action="store_true", help="take meetings through the shared claim queue")
    p.add_argument("--shard", help="I/N (every N-th selected meeting from I) or 'slurm' (array task id/count)")
    p.add_argument("--dry-run", action="store_true", help="show what would run")
    p.add_argument("--finalize", action="store_true", help="run only the stage's cross-meeting finalize step")
    p.add_argument("--config", help="config file (default $FEDPRESS_CONFIG or <package>/config.yaml)")
    p.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="override a config key")
    p.add_argument("--max-seconds", type=float, help="smoke tests: stages that support it process only media time "
                   "< N s (sets runtime.max_seconds; a later full run redoes those meetings)")
    p.add_argument("--gpus", type=int, help=f"launch: GPUs to use (<= {HARD_MAX_GPUS})")
    p.add_argument("--workers-per-gpu", type=int, help="launch: worker processes per GPU")
    p.add_argument("--keys", help="prefetch-models: comma-separated model keys (default: all enabled)")
    p.add_argument("--log-format", choices=("json", "text"), help="override runtime.log_format")
    return p


def _shard(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    if value == "slurm":
        tid, tmin = int(os.environ["SLURM_ARRAY_TASK_ID"]), int(os.environ.get("SLURM_ARRAY_TASK_MIN", "0"))
        return tid - tmin, int(os.environ["SLURM_ARRAY_TASK_COUNT"])
    i, n = (int(x) for x in value.split("/"))
    if not 0 <= i < n:
        raise ConfigError(f"--shard {value}: need 0 <= I < N")
    return i, n


def _select(cfg: Config, a: argparse.Namespace) -> list[mf.Meeting]:
    return mf.select(cfg, index=a.index, on_date=a.date, presser_id=a.presser_id, all_=a.all, shard=_shard(a.shard))


# ------------------------------------------------------------------ stage runs
def cmd_stage(cfg: Config, a: argparse.Namespace) -> int:
    from .stage import load_stage, new_run_id, run_one

    mod = load_stage(a.command)
    apply_env(cfg, offline=bool(cfg.get("runtime.offline_gpu", True)) and mod.SPEC.resource == "gpu")
    run_id = os.environ.get("FEDPRESS_RUN_ID") or new_run_id()
    log = logmod.Log("cli", stage=a.command, run_id=run_id)
    meetings = _select(cfg, a)
    counts: Counter[str] = Counter()
    if not a.finalize:
        for m in meetings:
            status = run_one(cfg, a.command, m, run_id=run_id, force=a.force, claim=a.claim, dry_run=a.dry_run)
            counts[status] += 1
            if a.dry_run:
                print(f"{m.presser_id} {m.presser_date} {m.chair:<8} {status}")
    full_run = a.all and not a.claim and not a.shard and not a.dry_run
    if hasattr(mod, "finalize") and (a.finalize or full_run):
        written = mod.finalize(cfg, meetings, log)
        log.info("stage.finalized", outputs=[str(p) for p in written or []])
    log.info("run.summary", meetings=len(meetings), **counts)
    return 1 if counts["failed"] else 0


def cmd_launch(cfg: Config, a: argparse.Namespace) -> int:
    """Run stages on one job's GPUs: workers_per_gpu processes per GPU drain one claim queue, so both GPUs
    finish together (the idle-GPU rule kills a job whose GPU sits at 0 % for an hour)."""
    from .gpu import plan_slots, worker_env
    from .stage import new_run_id

    if not a.stages:
        raise ConfigError("launch needs stages, e.g. `launch asr,turns,diarize,voice,face,text --all`")
    stages = [s.strip() for s in a.stages.split(",") if s.strip()]
    unknown = [s for s in stages if s not in STAGES]
    if unknown:
        raise ConfigError(f"unknown stages {unknown}")
    slots = plan_slots(cfg, gpus=a.gpus, workers_per_gpu=a.workers_per_gpu)
    run_id = os.environ.get("FEDPRESS_RUN_ID") or new_run_id()
    log = logmod.Log("launch", run_id=run_id)
    meetings = _select(cfg, a)
    sel = ["--all"] if a.all else (["--index", str(a.index)] if a.index is not None else
                                   ["--date", a.date] if a.date else ["--id", str(a.presser_id)])
    passthrough = (["--config", a.config] if a.config else []) + [x for s in a.set for x in ("--set", s)]
    if a.shard:  # an array task's group of meetings: every worker of this task drains only that group
        passthrough += ["--shard", a.shard]
    logdir = cfg.root_path("logs") / "launch" / run_id
    logdir.mkdir(parents=True, exist_ok=True)
    mps = _start_mps(cfg, log) if cfg.get("compute.mps", False) else None
    rc = 0
    try:
        for stage in stages:
            if a.force:  # clear once here; workers must not --force or they would redo each other's meetings
                for m in meetings:
                    io.clear_done(io.MeetingPaths.of(cfg, m.presser_id), stage)
            log.info("launch.stage", stage=stage, workers=len(slots), gpus=sorted({s.gpu for s in slots if s.gpu}))
            procs = []
            for slot in slots:
                env = worker_env(slot) | {"FEDPRESS_RUN_ID": run_id}
                out = (logdir / f"{stage}_w{slot.worker:02d}.log").open("w", encoding="utf-8")
                cmd = [sys.executable, "-m", "fedpress.cli", stage, *sel, "--claim", *passthrough]
                procs.append((subprocess.Popen(cmd, env=env, stdout=out, stderr=subprocess.STDOUT), out))
                time.sleep(0.5)  # stagger model loads
            codes = [p.wait() for p, _ in procs]
            for _, fh in procs:
                fh.close()
            log.info("launch.stage_done", stage=stage, exit_codes=codes)
            # 1 = some meetings failed (recorded per meeting); 2 = config error; a worker killed by a signal
            # (negative code, e.g. out of memory) counts as 3, so job scripts can tell crashes from failures
            rc = max([rc, *(c if c >= 0 else 3 for c in codes)])
    finally:
        if mps is not None:
            _stop_mps(mps)
    return rc


def _start_mps(cfg: Config, log: logmod.Log) -> dict[str, str]:
    base = cfg.scratch / "mps"
    env = {"CUDA_MPS_PIPE_DIRECTORY": str(base / "pipe"), "CUDA_MPS_LOG_DIRECTORY": str(base / "log")}
    for d in env.values():
        Path(d).mkdir(parents=True, exist_ok=True)
    os.environ.update(env)
    subprocess.run(["nvidia-cuda-mps-control", "-d"], check=True)
    log.info("mps.started", **env)
    return env


def _stop_mps(env: dict[str, str]) -> None:
    subprocess.run(["nvidia-cuda-mps-control"], input="quit\n", text=True, env=os.environ | env, check=False)


# ------------------------------------------------------------------ utilities
def cmd_list(cfg: Config, a: argparse.Namespace) -> int:
    rows = mf.load(cfg) if a.all else mf.sample(cfg)
    smp = {m.presser_id: i for i, m in enumerate(mf.sample(cfg))}
    print(f"{'idx':>4} {'presser_id':<10} {'date':<10} {'chair':<8} {'role':<11} sep vtt {'mp4_MB':>7} {'min':>5}")
    for m in rows:
        idx = smp.get(m.presser_id)
        print(f"{'' if idx is None else idx:>4} {m.presser_id:<10} {m.presser_date} {m.chair:<8} {m.sample_role:<11} "
              f"{'y' if m.sep else 'n':>3} {'y' if m.has_vtt else 'n':>3} {(m.mp4_bytes or 0) / 1e6:>7.0f} "
              f"{(m.duration_s or 0) / 60:>5.1f}")
    print(f"# {len(rows)} rows; sample = {len(smp)} pressers; config {cfg.hash}")
    return 0


def cmd_status(cfg: Config, a: argparse.Namespace) -> int:
    meetings = _select(cfg, a) if (a.all or a.index is not None or a.date or a.presser_id) else mf.sample(cfg)
    import pandas as pd

    sym = {"ok": "D", "not_applicable": "n"}
    totals: dict[str, Counter[str]] = {s: Counter() for s in STAGES}
    elapsed: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []
    print(f"{'presser_id':<10} {'chair':<8} " + " ".join(f"{s[:5]:>5}" for s in STAGES))
    for m in meetings:
        paths = io.MeetingPaths.of(cfg, m.presser_id)
        cells = []
        for s in STAGES:
            info = io.read_done(paths, s)
            secs = None
            if info and io.is_done(paths, s):
                c = sym.get(info.get("status", "ok"), "?")
                secs = float(info.get("elapsed_s", 0) or 0)
                elapsed[s] += secs
            elif io.failed_path(paths, s).exists():
                c = "F"
            elif io.claim_holder(paths, s):
                c = "C"
            elif cfg.section(s).get("enabled", True) is False:
                c = "x"
            else:
                c = "."
            totals[s][c] += 1
            cells.append(f"{c:>5}")
            rows.append({"presser_id": m.presser_id, "presser_date": m.presser_date.isoformat(), "chair": m.chair,
                         "sample_role": m.sample_role, "stage": s, "state": c, "elapsed_s": secs})
        print(f"{m.presser_id:<10} {m.chair:<8} " + " ".join(cells))
    print("# D done, n not applicable, F failed, C claimed (running), x disabled, . to do")
    for s in STAGES:
        print(f"# {s:<9} " + " ".join(f"{k}={v}" for k, v in sorted(totals[s].items()))
              + f"  elapsed_sum={elapsed[s] / 60:.1f} min")
    out = io.write_parquet(pd.DataFrame(rows), cfg.root_path("panel") / "status.parquet",
                           {"config_hash": cfg.hash, "created_utc": io.utc_now()})
    print(f"# wrote {out}")
    return 0


def cmd_config(cfg: Config, a: argparse.Namespace) -> int:
    from .stage import fingerprint, load_stage

    print(yaml.safe_dump(json.loads(json.dumps(cfg.data, default=str)), sort_keys=False, width=120))
    print(f"# source {cfg.source}  config_hash {cfg.hash}  root {cfg.root}")
    for s in STAGES:
        try:
            print(f"# {s:<9} fingerprint {fingerprint(cfg, load_stage(s).SPEC)}")
        except NotImplementedError:
            print(f"# {s:<9} (not implemented yet)")
    return 0


def cmd_prefetch(cfg: Config, a: argparse.Namespace) -> int:
    from .models import enabled_keys, prefetch

    apply_env(cfg, offline=False)
    keys = [k.strip() for k in a.keys.split(",")] if a.keys else enabled_keys(cfg)
    report = prefetch(cfg, keys)
    for k, v in report.items():
        print(f"{k:<32} {v}")
    return 1 if any(str(v).startswith("error") for v in report.values()) else 0


def cmd_doctor(cfg: Config, a: argparse.Namespace) -> int:
    from .doctor import run_checks

    apply_env(cfg, offline=bool(cfg.get("runtime.offline_gpu", True)))
    return run_checks(cfg)


def main(argv: list[str] | None = None) -> int:
    a = _parser().parse_args(argv)
    if a.max_seconds:
        a.set.append(f"runtime.max_seconds={a.max_seconds:g}")  # also passed on to `launch` workers
    try:
        cfg = load(a.config, a.set)
        logmod.setup(str(cfg.get("runtime.log_level", "INFO")), a.log_format or str(cfg.get("runtime.log_format", "json")))
        handlers: dict[str, Any] = {"list": cmd_list, "status": cmd_status, "config": cmd_config,
                                    "doctor": cmd_doctor, "launch": cmd_launch, "prefetch-models": cmd_prefetch}
        if a.command in handlers:
            return int(handlers[a.command](cfg, a))
        if a.command not in STAGES:
            raise ConfigError(f"unknown command {a.command!r}; stages: {', '.join(STAGES)}; utilities: {', '.join(UTILITIES)}")
        return cmd_stage(cfg, a)
    except (ConfigError, NotImplementedError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
