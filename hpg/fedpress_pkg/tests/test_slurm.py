"""Slurm layer: script syntax, the submit chain (dry run: 2-GPU cap, %2 throttle, dependencies) and status.py.
No Slurm, GPU or network needed; the shell tests are skipped where bash is missing."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from fedpress import io
from fedpress.config import load

PKG = Path(__file__).resolve().parents[1]
SLURM = PKG / "slurm"
sys.path.insert(0, str(SLURM))
import status

BASH = shutil.which("bash")
needs_bash = pytest.mark.skipif(BASH is None, reason="bash not available")


@pytest.fixture()
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("FEDPRESS_ROOT", str(tmp_path / "root"))
    monkeypatch.delenv("FEDPRESS_CONFIG", raising=False)
    monkeypatch.delenv("FP_SET", raising=False)
    return load()


@needs_bash
@pytest.mark.parametrize("script", sorted(p.name for p in SLURM.iterdir() if p.suffix in (".sh", ".sbatch")))
def test_shell_syntax(script):
    assert subprocess.run([BASH, "-n", str(SLURM / script)], capture_output=True, check=False).returncode == 0


def test_scripts_have_unix_line_endings():
    """sbatch refuses DOS line breaks and Linux bash breaks on a sourced CRLF file; Git Bash on Windows ignores CR,
    so the syntax test above cannot catch it."""
    files = [p for d in (SLURM, PKG / "env") for p in d.iterdir() if p.suffix in (".sh", ".sbatch", ".yml", ".def")]
    assert files and not [p.name for p in files if b"\r" in p.read_bytes()]


def test_gpu_scripts_request_at_most_two_gpus():
    for p in SLURM.glob("*.sbatch"):
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith("#SBATCH") and "gpu:" in line:
                assert int(line.rsplit(":", 1)[1]) <= 2, (p.name, line)


def _dry_run(tmp_path: Path, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
    fake = tmp_path / "env" / "bin"
    fake.mkdir(parents=True, exist_ok=True)
    py = Path(sys.executable).as_posix()
    (fake / "python").write_text(f'#!/bin/bash\nexec "{py}" "$@"\n', encoding="utf-8")
    (fake / "python").chmod(0o755)
    e = os.environ | {"FP_ENV": (tmp_path / "env").as_posix(), "FEDPRESS_ROOT": (tmp_path / "root").as_posix(),
                      "USER": "student", "PYTHONIOENCODING": "utf-8"} | env
    for k in ("FP_SET", "GPU_LAYOUT", "GPUS", "GROUP_SIZE", "GPU_TYPE", "QOS_GPU", "FP_PKG"):
        if k not in env:
            e.pop(k, None)
    return subprocess.run([BASH, str(SLURM / "submit_all.sh"), "--dry-run", *args], capture_output=True, text=True,
                          env=e, cwd=PKG, check=False)


@needs_bash
def test_submit_chain_dry_run(tmp_path):
    r = _dry_run(tmp_path)
    assert r.returncode == 0, r.stderr
    cmds = [line for line in r.stdout.splitlines() if line.startswith("[dry-run]")]
    assert len(cmds) == 6
    gpu = [c for c in cmds if "--gres=gpu:" in c]
    assert len(gpu) == 3 and all("--gres=gpu:b200:1" in c and "--array=0-1%2" in c for c in gpu)
    assert "aftercorr:" in cmds[1] and all("afterok:" in c for c in cmds[2:])
    assert "75 meetings" in r.stdout


@needs_bash
def test_submit_refuses_more_than_two_gpus_and_gpu_burst(tmp_path):
    assert _dry_run(tmp_path, GPU_LAYOUT="job", GPUS="3").returncode == 2
    assert _dry_run(tmp_path, QOS_GPU="jie.xu-b").returncode == 2
    ok = _dry_run(tmp_path, "--only", "speech", GPU_LAYOUT="job", GPUS="2")
    assert ok.returncode == 0 and "--gres=gpu:b200:2" in ok.stdout and "--array" not in ok.stdout


@needs_bash
def test_group_size_sets_array_length(tmp_path):
    r = _dry_run(tmp_path, "--only", "speech", GROUP_SIZE="6")
    assert r.returncode == 0 and "--array=0-12%2" in r.stdout and "FP_NSHARDS=13" in r.stdout


def test_status_next_failed_and_check(cfg, monkeypatch):
    import importlib

    from fedpress import STAGES
    from fedpress import manifest as mf

    # the real stage specs (other tests register stub stages under the same names)
    real = {s: tuple(importlib.import_module(f"fedpress.stages.{s}").SPEC.requires) for s in STAGES}
    monkeypatch.setattr(status, "_requires", lambda: real)

    meetings = mf.sample(cfg)
    m0, m1 = meetings[0], meetings[1]
    for m in (m0, m1):
        p = io.MeetingPaths.of(cfg, m.presser_id).ensure()
        for s in ("fetch", "audio", "frames"):
            io.mark_done(p, s, {"status": "ok", "outputs": [], "elapsed_s": 1.0})
    p0 = io.MeetingPaths.of(cfg, m0.presser_id)
    io.mark_failed(p0, "asr", {"error": "RuntimeError('boom')\nmore", "failed_utc": "x"})
    s = status.summarise(cfg, meetings)
    assert s["next_step"] == "fetch"  # the other 73 meetings were never fetched
    assert [f["presser_id"] for f in s["failures"]] == [m0.presser_id]
    row0 = next(r for r in s["rows"] if r["presser_id"] == m0.presser_id)
    assert row0["asr"] == "F" and row0["turns"] == "b" and row0["audio"] == "D"
    s2 = status.summarise(cfg, [m0, m1])
    assert s2["next_step"] == "speech"
    assert status.main(["--check", "asr", "--id", m0.presser_id]) == 3   # every selected meeting failed asr
    assert status.main(["--check", "audio", "--id", m0.presser_id]) == 0
