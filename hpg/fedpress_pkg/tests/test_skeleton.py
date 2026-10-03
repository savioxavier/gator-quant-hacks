"""Skeleton tests: config, manifest selection, known_at rule, done-markers, claims, the stage runner, the CLI.
They need only pyyaml, pandas and pyarrow (no GPU, no network)."""

from __future__ import annotations

import math
import types
from datetime import date, datetime, timezone

import pandas as pd
import pytest

from fedpress import cli, io
from fedpress import manifest as mf
from fedpress.clock import Anchor, et_to_utc, make_anchor, save_anchor, stamp
from fedpress.config import ConfigError, expand, load
from fedpress.stage import StageSpec, register, run_one


@pytest.fixture()
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("FEDPRESS_ROOT", str(tmp_path / "root"))
    monkeypatch.delenv("FEDPRESS_CONFIG", raising=False)
    return load()


def test_expand_nested_default(monkeypatch):
    monkeypatch.delenv("FP_X", raising=False)
    monkeypatch.setenv("FP_Y", "y")
    assert expand("${FP_X:-/a/${FP_Y}/b}") == "/a/y/b"
    monkeypatch.setenv("FP_X", "/x")
    assert expand("${FP_X:-/a/${FP_Y}/b}") == "/x"


def test_gpu_cap_enforced(tmp_path, monkeypatch):
    monkeypatch.setenv("FEDPRESS_ROOT", str(tmp_path))
    with pytest.raises(ConfigError, match="max_gpus"):
        load(overrides=["compute.max_gpus=3"])


def test_default_sample(cfg):
    smp = mf.sample(cfg)
    assert len(mf.load(cfg)) == 95
    assert len(smp) == 75  # held pressers 2016-03-16 .. 2026-09-16 (2016-2018 were quarterly)
    assert smp[0].presser_id == "20160316" and smp[-1].chair == "Warsh"
    assert {m.chair for m in smp} == {"Yellen", "Powell", "Warsh"}
    with_cal = mf.sample(load(overrides=["sample.include_calibration=true"]))
    assert len(with_cal) == 95


def test_select_modes(cfg):
    assert mf.select(cfg, index=0)[0].presser_id == "20160316"
    assert mf.select(cfg, on_date="2020-03-02")[0].presser_id == "20200303"  # meeting date != presser date
    assert mf.select(cfg, presser_id="20120125")[0].sample_role == "calibration"
    shards = [mf.select(cfg, all_=True, shard=(i, 4)) for i in range(4)]
    assert sum(len(s) for s in shards) == 75
    with pytest.raises(ConfigError):
        mf.select(cfg, index=0, all_=True)


def test_et_to_utc_dst():
    assert et_to_utc(date(2022, 6, 15), "14:30") == datetime(2022, 6, 15, 18, 30, tzinfo=timezone.utc)
    assert et_to_utc(date(2016, 1, 27), "14:30") == datetime(2016, 1, 27, 19, 30, tzinfo=timezone.utc)
    assert et_to_utc(date(2020, 3, 15), "18:30") == datetime(2020, 3, 15, 22, 30, tzinfo=timezone.utc)


def test_known_at_rule(cfg):
    m = mf.select(cfg, presser_id="20220615")[0]
    a = make_anchor(cfg, m, greeting_media_s=11.1)
    assert a.source == "scheduled_start" and math.isnan(a.uncertainty_s)
    df = stamp(pd.DataFrame({"t_start_s": [100.0], "t_end_s": [131.1]}), a, latency_s=30.0)
    # greeting at 11.1 s = 18:30:00Z, so t_end 131.1 s = 18:32:00Z, known 30 s later
    assert df["t_end_utc"].iloc[0] == pd.Timestamp("2022-06-15T18:32:00Z")
    assert df["known_at"].iloc[0] == pd.Timestamp("2022-06-15T18:32:30Z")
    v0 = make_anchor(load(overrides=["timing.anchor.rule=video_zero_at_scheduled"]), m, None)
    assert v0.media_s == 0.0
    assert Anchor.from_json(a.to_json()).to_json() == a.to_json()


def test_claims_and_done(cfg):
    paths = io.MeetingPaths.of(cfg, "20220615").ensure()
    c1 = io.try_claim(paths, "voice", ttl_s=3600)
    assert c1 is not None and io.try_claim(paths, "voice", ttl_s=3600) is None
    c1.release()
    assert io.try_claim(paths, "voice", ttl_s=3600) is not None
    assert not io.is_done(paths, "voice")
    (paths.dir / "voice" / "x.txt").write_text("x")
    io.mark_done(paths, "voice", {"status": "ok", "outputs": ["voice/x.txt"]})
    assert io.is_done(paths, "voice")
    (paths.dir / "voice" / "x.txt").unlink()
    assert not io.is_done(paths, "voice")  # an output vanished -> not done


def test_claim_of_ended_slurm_job_is_taken_over(cfg, monkeypatch):
    """A claim left by a killed job on another node is taken over once squeue no longer lists that job."""
    import json
    import shutil
    import subprocess

    paths = io.MeetingPaths.of(cfg, "20220615").ensure()
    claim = paths.dir / "_claims" / "asr.claim"
    claim.write_text(json.dumps({"host": "c0000a-s1.ufhpc", "pid": 1, "job": "999001"}))
    monkeypatch.setenv("SLURM_JOB_ID", "999002")
    monkeypatch.setattr(shutil, "which", lambda name: None)  # no squeue: only the TTL can free it
    io._JOB_GONE.clear()
    assert io.try_claim(paths, "asr", ttl_s=3600) is None
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/squeue")
    running = types.SimpleNamespace(returncode=0, stdout="RUNNING\n", stderr="")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: running)
    assert io.try_claim(paths, "asr", ttl_s=3600) is None  # the other job still runs
    io._JOB_GONE.clear()
    ended = types.SimpleNamespace(returncode=1, stdout="", stderr="slurm_load_jobs error: Invalid job id specified")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: ended)
    held = io.try_claim(paths, "asr", ttl_s=3600)
    assert held is not None and json.loads(claim.read_text())["job"] == "999002"
    io._JOB_GONE.clear()


def _fake_stage(name: str, requires: tuple[str, ...] = ()) -> types.ModuleType:
    mod = types.ModuleType(f"fake_{name}")
    mod.SPEC = StageSpec(name=name, requires=requires, resource="cpu", outputs=("turns",))
    calls: list[str] = []

    def run(ctx):
        calls.append(ctx.meeting.presser_id)
        if name == "turns":
            save_anchor(ctx.paths.dir, make_anchor(ctx.cfg, ctx.meeting, greeting_media_s=10.0))
            df = ctx.stamp(pd.DataFrame({"turn_idx": [0], "t_start_s": [10.0], "t_end_s": [70.0]}))
            ctx.write_table(df, "turns")
        else:
            ctx.write_table(ctx.stamp(pd.DataFrame({"t_start_s": [10.0], "t_end_s": [20.0]})), "voice_chunks")
        return ctx.result

    mod.run = run
    mod.calls = calls
    return mod


def test_runner_idempotent_and_blocked(cfg):
    turns, voice = _fake_stage("turns"), _fake_stage("voice", requires=("turns",))
    register("turns", turns)
    register("voice", voice)
    m = mf.select(cfg, presser_id="20220615")[0]
    assert run_one(cfg, "voice", m, run_id="t") == "blocked"
    assert run_one(cfg, "turns", m, run_id="t") == "done"
    assert run_one(cfg, "turns", m, run_id="t") == "skipped"
    assert run_one(cfg, "turns", m, run_id="t", force=True) == "done"
    assert run_one(cfg, "voice", m, run_id="t", claim=True) == "done"
    out = io.read_parquet(io.MeetingPaths.of(cfg, m.presser_id).file("voice_chunks"))
    assert {"presser_id", "chair", "known_at", "anchor_source"} <= set(out.columns)
    meta = io.read_meta(io.MeetingPaths.of(cfg, m.presser_id).file("voice_chunks"))
    assert meta["stage"] == "voice" and meta["latency_s"] == 30.0
    assert turns.calls == ["20220615", "20220615"]


def test_write_table_rejects_unstamped(cfg):
    bad = types.ModuleType("bad")
    bad.SPEC = StageSpec(name="text")
    bad.run = lambda ctx: (ctx.write_table(pd.DataFrame({"t_start_s": [1.0], "t_end_s": [2.0]}), "text_units"),
                           ctx.result)[1]
    register("text", bad)
    m = mf.select(cfg, presser_id="20220615")[0]
    assert run_one(cfg, "text", m, run_id="t") == "failed"
    assert io.failed_path(io.MeetingPaths.of(cfg, m.presser_id), "text").exists()


def test_cli_list_and_status(cfg, capsys):
    assert cli.main(["list"]) == 0
    assert "sample = 75 pressers" in capsys.readouterr().out
    assert cli.main(["status"]) == 0
    assert cli.main(["asr"]) == 2  # no selection
