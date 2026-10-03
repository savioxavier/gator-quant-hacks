"""Per-meeting directory layout, atomic parquet/JSON writes, done-markers and claims (shared work queue).

<root>/meetings/<presser_id>/
    raw/  audio/  frames/  asr/  turns/  diarize/  voice/  face/  text/  features/
    _done/<stage>.json        written last, only after every declared output exists
    _done/<stage>.failed.json last failure (removed on success)
    _claims/<stage>.claim     held while one worker runs the stage for this meeting
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import socket
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

if TYPE_CHECKING:
    import pandas as pd

    from .config import Config

STAGE_DIRS = ("raw", "audio", "frames", "asr", "turns", "diarize", "voice", "face", "text", "features")

#: Canonical file names (relative to the meeting directory). Stages use these keys, never ad-hoc names.
FILES: dict[str, str] = {
    "video": "raw/video.mp4",
    "transcript_pdf": "raw/transcript.pdf",
    "captions_vtt": "raw/captions.vtt",
    "statement_html": "raw/statement.html",
    "fetch_meta": "raw/fetch.json",
    "audio_wav": "audio/audio_16k.wav",
    "audio_meta": "audio/audio.json",
    "frames_zip": "frames/frames_{fps}fps.zip",
    "frames_index": "frames/frames_{fps}fps.parquet",
    "frames_meta": "frames/frames_meta.json",
    "asr_words": "asr/words.parquet",
    "asr_segments": "asr/segments.parquet",
    "asr_meta": "asr/asr.json",
    "turns": "turns/turns.parquet",
    "words": "turns/words.parquet",
    "anchor": "turns/anchor.json",
    "chair_check": "diarize/chair_check.parquet",
    "voice_chunks": "voice/voice_chunks.parquet",
    "face_frames": "face/face_frames.parquet",
    "face_turns": "face/face_turns.parquet",
    "face_enroll": "face/enroll.json",
    "text_sentences": "text/text_sentences.parquet",
    "text_units": "text/text_units.parquet",
    "text_vectors": "text/text_vectors.parquet",
    "answers": "features/answers.parquet",
    "meeting": "features/meeting.parquet",
    "windows": "features/windows.parquet",
}


def fps_tag(fps: float) -> str:
    return f"{fps:g}".replace(".", "p")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class MeetingPaths:
    dir: Path

    @classmethod
    def of(cls, cfg: "Config", presser_id: str) -> "MeetingPaths":
        return cls(cfg.root_path("meetings") / presser_id)

    @property
    def presser_id(self) -> str:
        return self.dir.name

    def stage_dir(self, stage: str) -> Path:
        return self.dir / ("features" if stage == "aggregate" else stage)

    def file(self, key: str, **fmt: Any) -> Path:
        if "fps" in fmt:
            fmt["fps"] = fps_tag(float(fmt["fps"]))
        return self.dir / FILES[key].format(**fmt)

    def ensure(self) -> "MeetingPaths":
        for d in (*STAGE_DIRS, "_done", "_claims"):
            (self.dir / d).mkdir(parents=True, exist_ok=True)
        return self


# ------------------------------------------------------------------ atomic writes and hashes
def _tmp_for(path: Path) -> Path:
    return path.with_name(f".{path.name}.{os.getpid()}.tmp")


def atomic_write_bytes(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tmp_for(path)
    tmp.write_bytes(data)
    os.replace(tmp, path)
    return path


def atomic_write_json(path: Path, obj: Any) -> Path:
    return atomic_write_bytes(path, (json.dumps(obj, indent=2, default=str) + "\n").encode())


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path, chunk: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


# ------------------------------------------------------------------ parquet
def write_parquet(df: "pd.DataFrame", path: Path, meta: dict[str, Any] | None = None) -> Path:
    """Atomic parquet write; ``meta`` goes into the schema metadata under the key ``fedpress``."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, preserve_index=False)
    md = dict(table.schema.metadata or {})
    md[b"fedpress"] = json.dumps(meta or {}, default=str).encode()
    table = table.replace_schema_metadata(md)
    tmp = _tmp_for(path)
    pq.write_table(table, tmp, compression="zstd")
    os.replace(tmp, path)
    return path


def read_parquet(path: Path, columns: list[str] | None = None) -> "pd.DataFrame":
    import pandas as pd

    return pd.read_parquet(path, columns=columns)


def read_meta(path: Path) -> dict[str, Any]:
    import pyarrow.parquet as pq

    md = pq.read_schema(path).metadata or {}
    return json.loads(md.get(b"fedpress", b"{}"))


# ------------------------------------------------------------------ done markers
def done_path(paths: MeetingPaths, stage: str) -> Path:
    return paths.dir / "_done" / f"{stage}.json"


def failed_path(paths: MeetingPaths, stage: str) -> Path:
    return paths.dir / "_done" / f"{stage}.failed.json"


def read_done(paths: MeetingPaths, stage: str) -> dict[str, Any] | None:
    p = done_path(paths, stage)
    return read_json(p) if p.exists() else None


def is_done(paths: MeetingPaths, stage: str) -> bool:
    """Done = marker present and every output it lists still exists."""
    info = read_done(paths, stage)
    return info is not None and all((paths.dir / o).exists() for o in info.get("outputs", []))


def mark_done(paths: MeetingPaths, stage: str, info: dict[str, Any]) -> Path:
    failed_path(paths, stage).unlink(missing_ok=True)
    return atomic_write_json(done_path(paths, stage), {"stage": stage, "presser_id": paths.presser_id, **info})


def mark_failed(paths: MeetingPaths, stage: str, info: dict[str, Any]) -> Path:
    return atomic_write_json(failed_path(paths, stage), {"stage": stage, "presser_id": paths.presser_id, **info})


def clear_done(paths: MeetingPaths, stage: str) -> None:
    done_path(paths, stage).unlink(missing_ok=True)


def describe_outputs(paths: MeetingPaths, rel: list[str], hash_limit: int = 256 << 20) -> list[dict[str, Any]]:
    """Size, mtime and (for files up to ``hash_limit`` bytes) sha256 of each output, for the done-marker."""
    out = []
    for r in rel:
        p = paths.dir / r
        st = p.stat()
        out.append({"path": r, "bytes": st.st_size, "mtime": st.st_mtime,
                    "sha256": sha256_file(p) if st.st_size <= hash_limit else None})
    return out


# ------------------------------------------------------------------ claims (work stealing across workers/GPUs)
def _pid_alive(pid: int) -> bool:
    if os.name == "nt" or pid <= 0:  # on Windows os.kill(pid, 0) terminates the process: never probe there
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


_JOB_GONE: dict[str, bool] = {}


def slurm_job_gone(job: str | None) -> bool:
    """True only when ``job`` is another Slurm job that Slurm no longer lists as pending or running (a job
    killed by a time limit, out of memory or scancel leaves its claims behind on a different host, where the
    pid check cannot see it). Any doubt (no squeue, a transient error) answers False and leaves the TTL rule."""
    import shutil
    import subprocess

    job = str(job or "").strip()
    if not job or job == os.environ.get("SLURM_JOB_ID") or shutil.which("squeue") is None:
        return False
    if job not in _JOB_GONE:
        try:
            r = subprocess.run(["squeue", "-h", "-j", job, "-o", "%T"], capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return False
        gone = (r.returncode == 0 and not r.stdout.strip()) or "invalid job id" in (r.stderr or "").lower()
        _JOB_GONE[job] = gone
    return _JOB_GONE[job]


def claim_is_stale(held: dict[str, Any], age_s: float, ttl_s: float) -> bool:
    """A claim can be taken over when it is older than ``ttl_s``, its process died on this host, or its Slurm
    job has ended (so a resubmitted chain does not wait out the TTL behind a killed job's claims)."""
    if age_s > ttl_s:
        return True
    if held.get("host") == socket.gethostname() and not _pid_alive(int(held.get("pid", 0) or 0)):
        return True
    return slurm_job_gone(held.get("job"))


@dataclass
class Claim:
    path: Path

    def release(self) -> None:
        self.path.unlink(missing_ok=True)


def try_claim(paths: MeetingPaths, stage: str, ttl_s: float) -> Claim | None:
    """Atomically create _claims/<stage>.claim (O_EXCL is atomic on Lustre and local disks). A stale claim
    (older than ``ttl_s``, left by a dead process on this host, or by a Slurm job that has ended) is taken
    over. None = someone else has it."""
    p = paths.dir / "_claims" / f"{stage}.claim"
    p.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps({"host": socket.gethostname(), "pid": os.getpid(), "since": utc_now(),
                       "job": os.environ.get("SLURM_JOB_ID"), "gpu": os.environ.get("CUDA_VISIBLE_DEVICES")})
    for _ in range(2):
        try:
            fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
            try:
                held = json.loads(p.read_text(encoding="utf-8") or "{}")
                age = time.time() - p.stat().st_mtime
            except (OSError, ValueError):
                continue  # vanished or half-written: retry once
            if claim_is_stale(held, age, ttl_s):
                p.unlink(missing_ok=True)
                continue
            return None
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(body)
        return Claim(p)
    return None


def claim_holder(paths: MeetingPaths, stage: str) -> dict[str, Any] | None:
    p = paths.dir / "_claims" / f"{stage}.claim"
    try:
        return json.loads(p.read_text(encoding="utf-8") or "{}")
    except (OSError, ValueError):
        return None


# ------------------------------------------------------------------ frames container
class FrameStore:
    """Read access to frames/frames_<fps>fps.zip (JPEG members) with its index parquet
    (columns: frame_idx, t_s, member, width, height)."""

    def __init__(self, paths: MeetingPaths, fps: float) -> None:
        self.zip_path = paths.file("frames_zip", fps=fps)
        self.index = read_parquet(paths.file("frames_index", fps=fps))
        self._zf: zipfile.ZipFile | None = None

    def read(self, member: str) -> bytes:
        if self._zf is None:
            self._zf = zipfile.ZipFile(self.zip_path)
        return self._zf.read(member)

    def __iter__(self) -> Iterator[tuple[int, float, bytes]]:
        for row in self.index.itertuples(index=False):
            yield int(row.frame_idx), float(row.t_s), self.read(str(row.member))

    def close(self) -> None:
        if self._zf is not None:
            self._zf.close()
            self._zf = None


def scratch_dir(cfg: "Config", presser_id: str, stage: str) -> Path:
    """Node-local scratch ($TMPDIR in Slurm, deleted at job end); never a place for outputs."""
    d = cfg.scratch / presser_id / stage
    d.mkdir(parents=True, exist_ok=True)
    return d
