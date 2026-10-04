"""diarize (GPU): is the chair-labelled speech really the chair? Chunk-level voice check after the opening.

Default ``diarize.method: ecapa_verify`` (Apache-2.0, ungated): SpeechBrain ECAPA embeddings; the chair's
voiceprint is the mean embedding of the opening remarks. The opening precedes every Q&A turn, so the check is
causal. With ``ecapa.threshold: null`` the threshold is also set from the opening only:
max(min_threshold, quantile(leave-one-out opening scores, calib_quantile) - calib_margin). Reporter scores are
reported as diagnostics and never used to choose the threshold (they lie in the future of most chunks).

Optional pyannote (``diarize.pyannote.enabled``; gated models, Hub terms + HF token needed for prefetch):
speaker-diarization-3.1 or community-1. The chair's pyannote speaker is the one that talks most during the
opening. Clustering uses the whole recording, so pyannote is not causal: by default it is recorded as a
cross-check; ``pyannote.gate: true`` also requires agreement before a chunk counts as verified.

Output ``chair_check`` diarize/chair_check.parquet (stamped at chunk end; only chunks that start after the
opening): chunk_idx, turn_idx, qa_idx, role, segment_kind, t_start_s, t_end_s, dur_s, label_is_chair, method,
score, threshold, ecapa_ok, pyannote_speaker, pyannote_chair_frac, pyannote_ok, chair_verified, agree.
chair_verified = label says chair AND every enabled voice check says chair; agree = labels and voice agree.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np

from .. import gpu, models
from ..stage import StageContext, StageResult, StageSpec
from . import _chunks, _media

SPEC = StageSpec(name="diarize", requires=("audio", "turns"), resource="gpu", outputs=("chair_check",))


def run(ctx: StageContext) -> StageResult:
    from .. import io

    s = ctx.scfg
    method = str(s.get("method", "ecapa_verify"))
    pya: dict[str, Any] = dict(s.get("pyannote") or {})
    use_pya = method == "pyannote" or bool(pya.get("enabled", False))
    if method == "pyannote" and not pya.get("enabled", False):
        raise ValueError("diarize.method=pyannote needs diarize.pyannote.enabled=true (so prefetch-models fetches it)")
    ecfg: dict[str, Any] = dict(s.get("ecapa") or {})
    turns = io.read_parquet(ctx.out("turns"))
    audio, sr = _media.read_wav(ctx.out("audio_wav"))
    opening = turns[turns["segment_kind"] == "opening"]
    enroll_end = float(opening["t_end_s"].max())
    chunk_s, min_s = float(ecfg.get("chunk_s", 3.0)), float(ecfg.get("min_chunk_s", 1.5))
    df = _chunks.turn_chunks(turns, chunk_s, chunk_s, min_s, not_before=enroll_end, merge_tail=True)
    df["label_is_chair"] = df["role"] == "chair"
    df["method"] = method
    for col, val in (("score", np.nan), ("threshold", np.nan), ("ecapa_ok", True), ("pyannote_speaker", ""),
                     ("pyannote_chair_frac", np.nan), ("pyannote_ok", True)):
        df[col] = val
    notes: dict[str, Any] = {"method": method, "enroll_end_s": round(enroll_end, 3), "n_chunks": len(df)}
    used: list[str] = []

    if method == "ecapa_verify":
        key = str(ecfg.get("model", "ecapa_voxceleb"))
        enc = Ecapa(ctx.cfg, key, gpu.device(str(s.get("device", "cuda"))), ctx.scratch())
        spans = [(a, b) for t in opening.itertuples(index=False)
                 for a, b in _chunks.windows(t.t_start_s, t.t_end_s, chunk_s, chunk_s, chunk_s)]
        enroll_s = len(spans) * chunk_s
        if enroll_s < float(ecfg.get("min_enroll_s", 60)):
            raise ValueError(f"opening gives {enroll_s:.0f} s of chair speech, below diarize.ecapa.min_enroll_s")
        bs = int(ecfg.get("batch_size", 64))
        emb_open = enc.embed([_media.slice_audio(audio, sr, a, b) for a, b in spans], bs)
        centroid, loo = enroll(emb_open, float(ecfg.get("outlier_mad", 4.0)))
        thr = ecfg.get("threshold")
        thr = float(thr) if thr is not None else calibrate(loo, float(ecfg.get("calib_quantile", 0.02)),
                                                           float(ecfg.get("calib_margin", 0.10)),
                                                           float(ecfg.get("min_threshold", 0.30)))
        clips = [_media.slice_audio(audio, sr, a, b) for a, b in zip(df["t_start_s"], df["t_end_s"])]
        valid = np.array([len(c) >= int(0.9 * min_s * sr) for c in clips], dtype=bool)
        if valid.any():  # chunks past the end of the audio (extrapolated word times) keep score NaN
            df.loc[valid, "score"] = enc.embed([c for c, v in zip(clips, valid) if v], bs) @ centroid
        df["threshold"] = thr
        df["ecapa_ok"] = df["score"] >= thr
        used.append(key)
        notes |= {"threshold": round(thr, 4), "threshold_source": "config" if ecfg.get("threshold") is not None
                  else "opening_loo", "enroll_s": enroll_s, "n_enroll": len(spans),
                  "enroll_loo_q": {q: round(float(np.quantile(loo, q)), 4) for q in (0.02, 0.1, 0.5)}}

    if use_pya:
        key = str(pya.get("model", "pyannote_31"))
        segs = run_pyannote(ctx.cfg, key, audio, sr, gpu.device(str(s.get("device", "cuda"))), pya, ctx.scratch())
        spk, frac, chair_spk = assign_speakers(segs, df[["t_start_s", "t_end_s"]].to_numpy(),
                                               opening[["t_start_s", "t_end_s"]].to_numpy())
        df["pyannote_speaker"], df["pyannote_chair_frac"] = spk, frac
        df["pyannote_ok"] = df["pyannote_chair_frac"] >= float(pya.get("min_chair_frac", 0.5))
        used.extend([key, *ctx.cfg.model(key).get("needs", [])])
        notes |= {"pyannote_model": key, "pyannote_chair_speaker": chair_spk, "pyannote_gate": bool(pya.get("gate")),
                  "pyannote_speakers": int(len({x[2] for x in segs})), "pyannote_causal": False}

    checks = [df["ecapa_ok"].astype(bool)] if method == "ecapa_verify" else []
    if use_pya and (method == "pyannote" or pya.get("gate", False)):
        checks.append(df["pyannote_ok"].astype(bool))
    voice_ok = df["label_is_chair"].copy() if not checks else checks[0]  # method none: labels only
    for c in checks[1:]:
        voice_ok &= c
    df["chair_verified"] = df["label_is_chair"] & voice_ok
    df["agree"] = df["label_is_chair"] == voice_ok
    ctx.write_table(ctx.stamp(df), "chair_check", models=tuple(used))
    ctx.result.notes.update(notes | diagnostics(df))
    ctx.log.info("diarize.done", chunks=len(df), **diagnostics(df))
    return ctx.result


def enroll(emb: np.ndarray, outlier_mad: float) -> tuple[np.ndarray, np.ndarray]:
    """Chair voiceprint from unit-norm opening embeddings: drop windows far below the median similarity
    (applause, crosstalk), re-average. Returns (unit centroid, leave-one-out cosine of each kept window)."""
    c = _unit(emb.mean(axis=0))
    sim = emb @ c
    med, mad = np.median(sim), np.median(np.abs(sim - np.median(sim))) + 1e-9
    keep = emb[sim >= med - outlier_mad * 1.4826 * mad]
    total = keep.sum(axis=0)
    loo = np.array([float(_unit(total - e) @ e) for e in keep]) if len(keep) > 1 else np.array([1.0])
    return _unit(total), loo


def calibrate(loo: np.ndarray, quantile: float, margin: float, floor: float) -> float:
    return max(floor, float(np.quantile(loo, quantile)) - margin)


def diagnostics(df: Any) -> dict[str, Any]:
    """Score separation and agreement (reported only; nothing here feeds back into the decision)."""
    out: dict[str, Any] = {}
    chair = df[df["segment_kind"] == "answer"]
    if len(chair):
        out["answer_verified_frac"] = round(float((chair["chair_verified"] * chair["dur_s"]).sum()
                                                  / max(chair["dur_s"].sum(), 1e-9)), 4)
    scored = df[df["score"].notna()] if df["score"].notna().any() else df[df["method"] != "ecapa_verify"]
    out["n_unscored"] = int(len(df) - len(scored))
    s_chair, s_rep = scored[scored["segment_kind"] == "answer"], scored[scored["role"] == "reporter"]
    if df["score"].notna().any():
        if len(s_chair):
            out["answer_score_median"] = round(float(s_chair["score"].median()), 4)
        if len(s_rep):
            out["reporter_score_median"] = round(float(s_rep["score"].median()), 4)
            out["reporter_accept_frac"] = round(float(s_rep["ecapa_ok"].mean()), 4)
    out["label_disagree_frac"] = round(float((~scored["agree"]).mean()), 4) if len(scored) else None
    return out


def _unit(v: np.ndarray) -> np.ndarray:
    return v / (np.linalg.norm(v, axis=-1, keepdims=True) + 1e-12)


class Ecapa:
    """speechbrain/spkrec-ecapa-voxceleb loaded from the pinned local snapshot; unit-norm 192-d embeddings."""

    def __init__(self, cfg: Any, key: str, device: str, scratch: Path) -> None:
        gpu.preload_cuda_libs()
        import torch

        try:
            from speechbrain.inference.speaker import EncoderClassifier
        except ImportError:  # speechbrain < 1.0
            from speechbrain.pretrained import EncoderClassifier
        work = _stage_snapshot(models.local_path(cfg, key), scratch / "ecapa")
        kwargs: dict[str, Any] = {"source": str(work), "savedir": str(work), "run_opts": {"device": device}}
        if "pretrained_path:" in (work / "hyperparams.yaml").read_text(encoding="utf-8"):
            kwargs["overrides"] = {"pretrained_path": str(work)}  # resolve checkpoints locally, never via the Hub
        try:  # speechbrain links checkpoint names; Windows without symlink rights needs copies
            from speechbrain.utils.fetching import LocalStrategy

            kwargs["local_strategy"] = LocalStrategy.COPY if os.name == "nt" else LocalStrategy.SYMLINK
        except ImportError:
            pass
        self.model = EncoderClassifier.from_hparams(**kwargs)
        self.model.eval()
        self.device = device
        self.torch = torch

    def embed(self, clips: list[np.ndarray], batch_size: int = 64) -> np.ndarray:
        torch = self.torch
        out = []
        for k in range(0, len(clips), batch_size):
            part = clips[k:k + batch_size]
            n = max(len(c) for c in part)
            wav = np.zeros((len(part), n), dtype=np.float32)
            for i, c in enumerate(part):
                wav[i, :len(c)] = c
            lens = torch.tensor([len(c) / n for c in part], dtype=torch.float32)
            with torch.inference_mode():
                e = self.model.encode_batch(torch.from_numpy(wav).to(self.device), lens.to(self.device))
            out.append(e.squeeze(1).float().cpu().numpy())
        return _unit(np.concatenate(out)) if out else np.zeros((0, 192), dtype=np.float32)


def _stage_snapshot(src: Path, work: Path) -> Path:
    """The model snapshot as a speechbrain source folder in scratch (symlinks; copies on Windows) plus the
    optional custom.py speechbrain probes for, so loading never reaches the Hub."""
    import shutil

    work.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        dst = work / f.name
        if f.is_file() and not dst.exists():
            if os.name == "nt":
                shutil.copyfile(f, dst)
            else:
                dst.symlink_to(f.resolve())
    (work / "custom.py").touch()
    return work


def run_pyannote(cfg: Any, key: str, audio: np.ndarray, sr: int, device: str, pya: dict[str, Any],
                 scratch: Path) -> list[tuple[float, float, str]]:
    """(start, end, speaker) turns from a pyannote pipeline loaded offline from the pinned snapshots. Exclusive
    (non-overlapping) output is used when the pipeline provides it (community-1)."""
    gpu.preload_cuda_libs()
    import torch
    from pyannote.audio import Pipeline

    src = models.local_path(cfg, key)
    conf = src / "config.yaml"
    text = conf.read_text(encoding="utf-8")
    for need in cfg.model(key).get("needs", []):  # 3.1 names its sub-models by repo id: point them at local files
        sub = models.local_path(cfg, need)
        target = next((p for p in (sub / "pytorch_model.bin", sub / "model.safetensors") if p.exists()), sub)
        text = text.replace(str(cfg.model(need)["id"]), str(target))
    patched = scratch / f"{key}_config.yaml"
    patched.write_text(text, encoding="utf-8")
    pipe = Pipeline.from_pretrained(str(patched if cfg.model(key).get("needs") else src))
    pipe.to(torch.device(device))
    kwargs = {"num_speakers": int(pya["num_speakers"])} if pya.get("num_speakers") else {}
    out = pipe({"waveform": torch.from_numpy(audio)[None, :], "sample_rate": sr}, **kwargs)
    ann = getattr(out, "exclusive_speaker_diarization", None) or getattr(out, "speaker_diarization", None) or out
    return [(float(seg.start), float(seg.end), str(spk)) for seg, _, spk in ann.itertracks(yield_label=True)]


def assign_speakers(segs: list[tuple[float, float, str]], spans: np.ndarray,
                    opening: np.ndarray) -> tuple[list[str], np.ndarray, str]:
    """Dominant pyannote speaker per chunk, the fraction of each chunk spoken by the chair's speaker, and the
    chair's speaker (most talk time inside the opening)."""
    if not segs:
        return [""] * len(spans), np.zeros(len(spans)), ""
    speakers = sorted({s for _, _, s in segs})
    per = {sp: np.array([[a, b] for a, b, s in segs if s == sp]) for sp in speakers}
    open_cov = {sp: float((_chunks.coverage(opening, per[sp]) * (opening[:, 1] - opening[:, 0])).sum())
                for sp in speakers}
    chair_spk = max(open_cov, key=open_cov.get)
    cov = np.stack([_chunks.coverage(spans, per[sp]) for sp in speakers], axis=1) if len(spans) else np.zeros((0, 1))
    dominant = [speakers[i] if cov[k, i] > 0 else "" for k, i in enumerate(cov.argmax(axis=1))] if len(spans) else []
    return dominant, cov[:, speakers.index(chair_spk)] if len(spans) else np.zeros(0), chair_spk
