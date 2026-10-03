"""The stage contract and the runner that applies it (skip if done, requirements, claim, done-marker).

A stage is a module ``fedpress/stages/<name>.py`` that defines

    SPEC = StageSpec(name="voice", requires=("audio", "turns", "diarize"), resource="gpu",
                     outputs=("voice_chunks",))
    def applies(ctx: StageContext) -> str | None: ...   # optional: a reason to skip this meeting
    def run(ctx: StageContext) -> StageResult: ...
    def finalize(cfg, meetings, log) -> list[Path]: ...  # optional: once after a full --all run

and writes every table through ``ctx.write_table`` (which adds the id columns, checks the known_at columns and
embeds provenance). Heavy imports (torch, transformers, ...) go inside ``run``.
"""

from __future__ import annotations

import hashlib
import importlib
import socket
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, Callable

from . import __version__, io
from .clock import TIMING_COLUMNS, Anchor, load_anchor, stamp, stamp_at
from .config import Config
from .log import Log
from .manifest import Meeting

if TYPE_CHECKING:
    import pandas as pd

ID_COLUMNS = ("presser_id", "meeting_date", "chair", "sample_role")
MEDIA_COLUMNS = ("t_start_s", "t_end_s")
OK_STATUSES = ("ok", "not_applicable")
_REGISTRY: dict[str, ModuleType] = {}


@dataclass(frozen=True)
class StageSpec:
    name: str
    requires: tuple[str, ...] = ()   # upstream stages that must be done (disabled or n/a upstream counts as done)
    resource: str = "cpu"            # cpu | gpu | net  (net: needs outbound HTTPS; run in a CPU job or dev session)
    outputs: tuple[str, ...] = ()    # io.FILES keys this stage normally writes (documentation and status)
    config_keys: tuple[str, ...] = ("timing",)  # extra config sections in the stage fingerprint
    stamped: bool = True             # tables carry known_at (False only for raw media stages)


@dataclass
class StageResult:
    outputs: list[str] = field(default_factory=list)   # relative paths written (ctx.write_table fills this)
    rows: dict[str, int] = field(default_factory=dict)
    models: dict[str, str] = field(default_factory=dict)   # model key -> revision actually used
    notes: dict[str, Any] = field(default_factory=dict)    # quality flags, counts, thresholds chosen


def code_version() -> str:
    """Package version + hash of every fedpress/*.py file (the code-hash freeze of the plan)."""
    h = hashlib.sha256()
    for p in sorted(Path(__file__).resolve().parent.rglob("*.py")):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return f"{__version__}+src.{h.hexdigest()[:12]}"


@dataclass
class StageContext:
    cfg: Config
    meeting: Meeting
    paths: io.MeetingPaths
    log: Log
    spec: StageSpec
    run_id: str
    result: StageResult = field(default_factory=StageResult)
    _anchor: Anchor | None = None

    @property
    def stage(self) -> str:
        return self.spec.name

    @property
    def scfg(self) -> dict[str, Any]:
        """This stage's config section."""
        return self.cfg.section(self.spec.name)

    @property
    def latency_s(self) -> float:
        return float(self.cfg.get("timing.latency_s"))

    def out(self, key: str, **fmt: Any) -> Path:
        return self.paths.file(key, **fmt)

    def rel(self, path: Path) -> str:
        return path.resolve().relative_to(self.paths.dir.resolve()).as_posix()

    def scratch(self) -> Path:
        return io.scratch_dir(self.cfg, self.meeting.presser_id, self.stage)

    def anchor(self) -> Anchor:
        if self._anchor is None:
            self._anchor = load_anchor(self.paths.dir)
        return self._anchor

    def stamp(self, df: "pd.DataFrame", t_end_col: str = "t_end_s") -> "pd.DataFrame":
        """known_at from media time (segment/chunk/frame/window end)."""
        return stamp(df, self.anchor(), self.latency_s, t_end_col)

    def stamp_statement(self, df: "pd.DataFrame") -> "pd.DataFrame":
        """known_at for statement rows: scheduled statement release + latency."""
        return stamp_at(df, self.meeting.statement_utc, self.latency_s, "statement_release")

    def with_ids(self, df: "pd.DataFrame") -> "pd.DataFrame":
        out = df.copy()
        m = self.meeting
        for col, val in zip(ID_COLUMNS, (m.presser_id, m.meeting_date.isoformat(), m.chair, m.sample_role)):
            if col not in out.columns:
                out.insert(len(out.columns), col, val)
        return out

    def write_table(self, df: "pd.DataFrame", key: str, models: tuple[str, ...] = (), **fmt: Any) -> Path:
        """Validate and write one output table (io.FILES key) with provenance in the parquet metadata."""
        df = self.with_ids(df)
        required = ID_COLUMNS + (MEDIA_COLUMNS + TIMING_COLUMNS if self.spec.stamped else ())
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"{self.stage}/{key}: missing required columns {missing}")
        if self.spec.stamped and len(df) and df["known_at"].isna().any():
            raise ValueError(f"{self.stage}/{key}: known_at has nulls")
        revs = {k: str(self.cfg.model(k).get("revision") or self.cfg.model(k).get("package")
                       or self.cfg.model(k).get("sha256") or "") for k in models}
        self.result.models.update(revs)
        path = self.out(key, **fmt)
        io.write_parquet(df, path, {
            "stage": self.stage, "presser_id": self.meeting.presser_id, "run_id": self.run_id,
            "config_hash": self.cfg.hash, "stage_fingerprint": fingerprint(self.cfg, self.spec),
            "code_version": code_version(), "models": revs, "created_utc": io.utc_now(),
            "latency_s": self.latency_s,
        })
        rel = self.rel(path)
        if rel not in self.result.outputs:
            self.result.outputs.append(rel)
        self.result.rows[key] = len(df)
        return path

    def add_output(self, path: Path) -> None:
        """Register a non-table output (media file, JSON) so the done-marker lists it."""
        rel = self.rel(path)
        if rel not in self.result.outputs:
            self.result.outputs.append(rel)


def fingerprint(cfg: Config, spec: StageSpec) -> str:
    return cfg.fingerprint((spec.name, *spec.config_keys))


def register(name: str, module: ModuleType) -> None:
    """Register a stage module under ``name`` (tests and extensions); normal stages are imported by name."""
    _REGISTRY[name] = module


def load_stage(name: str) -> ModuleType:
    if name in _REGISTRY:
        return _REGISTRY[name]
    try:
        mod = importlib.import_module(f"fedpress.stages.{name}")
    except ModuleNotFoundError as e:
        if e.name == f"fedpress.stages.{name}":
            raise NotImplementedError(f"stage {name!r} is not implemented (no fedpress/stages/{name}.py)") from e
        raise
    if not isinstance(getattr(mod, "SPEC", None), StageSpec) or not callable(getattr(mod, "run", None)):
        raise TypeError(f"fedpress.stages.{name} must define SPEC: StageSpec and run(ctx) -> StageResult")
    return mod


def max_seconds(cfg: Config) -> float | None:
    """Smoke-test cut (CLI --max-seconds): stages that honour it record notes.max_seconds in their marker."""
    v = cfg.get("runtime.max_seconds", None)
    return float(v) if v else None


def _cut_of(paths: io.MeetingPaths, stage: str) -> float | None:
    v = ((io.read_done(paths, stage) or {}).get("notes") or {}).get("max_seconds")
    return float(v) if v else None


def _requirement_ok(cfg: Config, paths: io.MeetingPaths, req: str) -> bool:
    if cfg.section(req).get("enabled", True) is False:
        return True
    info = io.read_done(paths, req)
    ok = info is not None and info.get("status", "ok") in OK_STATUSES and io.is_done(paths, req)
    up, cut = _cut_of(paths, req), max_seconds(cfg)
    return ok and (up is None or (cut is not None and cut <= up))  # a truncated upstream feeds only smoke runs


def meeting_log(cfg: Config, stage: str, meeting: Meeting, run_id: str) -> Log:
    file = cfg.root_path("logs") / stage / f"{meeting.presser_id}.jsonl"
    return Log(stage, file, stage=stage, presser_id=meeting.presser_id, run_id=run_id)


def run_one(cfg: Config, name: str, meeting: Meeting, *, run_id: str, force: bool = False,
            claim: bool = False, dry_run: bool = False) -> str:
    """Run one stage for one meeting. Returns done | skipped | na | blocked | claimed | disabled | failed | dry."""
    mod = load_stage(name)
    spec: StageSpec = mod.SPEC
    log = meeting_log(cfg, name, meeting, run_id)
    if cfg.section(name).get("enabled", True) is False:
        return "disabled"
    paths = io.MeetingPaths.of(cfg, meeting.presser_id)
    if not dry_run:
        paths.ensure()
    fp = fingerprint(cfg, spec)
    prev_cut = _cut_of(paths, name) if not dry_run else None
    if prev_cut is not None and prev_cut != max_seconds(cfg):  # truncated smoke output never satisfies a full run
        log.info("stage.truncated_redo", previous_max_seconds=prev_cut, current=max_seconds(cfg))
        force = True
    if not force and io.is_done(paths, name):
        prev = (io.read_done(paths, name) or {}).get("stage_fingerprint")
        if prev and prev != fp:
            log.warning("stage.stale", previous=prev, current=fp, hint="config changed since this output; --force to redo")
        return "skipped"
    blocked = [r for r in spec.requires if not _requirement_ok(cfg, paths, r)]
    if blocked:
        log.info("stage.blocked", missing=blocked)
        return "blocked"
    if dry_run:
        return "dry"
    ctx = StageContext(cfg, meeting, paths, log, spec, run_id)
    applies: Callable[[StageContext], str | None] | None = getattr(mod, "applies", None)
    reason = applies(ctx) if applies else None
    if reason:
        io.mark_done(paths, name, {"status": "not_applicable", "reason": reason, "outputs": [],
                                   "stage_fingerprint": fp, "run_id": run_id, "finished_utc": io.utc_now()})
        log.info("stage.not_applicable", reason=reason)
        return "na"
    held = io.try_claim(paths, name, float(cfg.get("runtime.claim_ttl_s", 21600))) if claim else None
    if claim and held is None:
        return "claimed"
    try:
        if not force and io.is_done(paths, name):  # finished by another worker while we were claiming
            return "skipped"
        if force:
            io.clear_done(paths, name)
        started, t0 = io.utc_now(), time.perf_counter()
        log.info("stage.start", resource=spec.resource)
        result = mod.run(ctx) or ctx.result
        missing = [o for o in result.outputs if not (paths.dir / o).exists()]
        if missing or not result.outputs:
            raise RuntimeError(f"stage {name} finished without outputs {missing or '(none declared)'}")
        elapsed = time.perf_counter() - t0
        info: dict[str, Any] = {
            "status": "ok", "outputs": result.outputs, "outputs_detail": io.describe_outputs(paths, result.outputs),
            "rows": result.rows, "models": result.models, "notes": result.notes,
            "stage_fingerprint": fp, "config_hash": cfg.hash, "overrides": list(cfg.overrides),
            "code_version": code_version(), "run_id": run_id, "started_utc": started,
            "finished_utc": io.utc_now(), "elapsed_s": round(elapsed, 3), "host": socket.gethostname(),
        }
        if spec.resource == "gpu":
            from .gpu import info as gpu_info

            info["device"] = gpu_info()
        io.mark_done(paths, name, info)
        log.info("stage.done", elapsed_s=round(elapsed, 3), rows=result.rows)
        return "done"
    except Exception as e:  # a blocker affects only this meeting
        log.error("stage.failed", exc=True, error=repr(e))
        io.mark_failed(paths, name, {"error": repr(e), "traceback": traceback.format_exc(), "run_id": run_id,
                                     "failed_utc": io.utc_now()})
        if cfg.get("runtime.fail_fast", False):
            raise
        return "failed"
    finally:
        if held is not None:
            held.release()


def new_run_id() -> str:
    return datetime.now().strftime("%Y%m%dT%H%M%S") + f"-{socket.gethostname().split('.')[0]}"

