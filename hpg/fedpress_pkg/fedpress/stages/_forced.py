"""Optional word-time refinement by forced alignment (plan_v0 options, off by default).

* whisperx            wav2vec2 CTC alignment (``turns.align.whisperx_align_model``); numbers and symbols that
                      have no alignable characters keep their base time.
* qwen_forced_aligner Qwen3-ForcedAligner-0.6B through the ``qwen-asr`` package (segments up to 5 minutes).

Both align the transcript text segment by segment around the base clock (ASR or captions), then map the
aligner's words back to the transcript words with the same token alignment as the base clock.
"""

from __future__ import annotations

import os
from typing import Any, Sequence

import numpy as np

from .. import gpu, models
from ..config import Config
from . import _align


def segments(owner: np.ndarray, al: _align.Alignment, max_seg_s: float, pad_s: float,
             total_s: float) -> list[tuple[int, int, float, float]]:
    """(word_lo, word_hi, t0, t1): runs of words inside one turn, each spanning at most ``max_seg_s``."""
    out = []
    lo, n = 0, len(owner)
    for i in range(1, n + 1):
        new_turn = i == n or owner[i] != owner[lo]
        too_long = not new_turn and al.end[i] - al.start[lo] > max_seg_s
        if new_turn or too_long:
            out.append((lo, i, max(0.0, float(al.start[lo]) - pad_s), min(total_s, float(al.end[i - 1]) + pad_s)))
            lo = i
    return out


def refine(method: str, cfg: Config, scfg: dict[str, Any], audio: np.ndarray, sr: int, words: Sequence[str],
           owner: np.ndarray, base: _align.Alignment) -> tuple[_align.Alignment, dict[str, Any]]:
    """Replace base word times with forced-alignment times where the aligner's words align to the transcript."""
    if cfg.get("runtime.offline_gpu", True):
        os.environ["HF_HUB_OFFLINE"] = "1"
    gpu.preload_cuda_libs()
    dev = gpu.device(str(scfg.get("device", "cuda")))
    seg_s = scfg.get("whisperx_segment_s", 30.0) if method == "whisperx" else scfg.get("qwen_segment_s", 180.0)
    segs = segments(owner, base, float(seg_s), float(scfg.get("pad_s", 0.5)), len(audio) / sr)
    if method == "whisperx":
        timed = _whisperx(cfg, scfg, audio, sr, words, segs, dev)
    elif method == "qwen_forced_aligner":
        timed = _qwen(cfg, scfg, audio, sr, words, segs, dev)
    else:
        raise ValueError(f"turns.align.method {method!r}: use text_match, whisperx or qwen_forced_aligner")
    fa = _align.align(words, timed)
    use = fa.timed_by != "interp"
    start, end = np.where(use, fa.start, base.start), np.where(use, fa.end, base.end)
    timed_by = np.where(use, "forced", base.timed_by).astype(object)
    start = np.maximum.accumulate(start)
    forced = {**fa.stats, "method": method, "device": dev, "segments": len(segs),
              "refined_frac": round(float(use.mean()), 4)}
    out = _align.Alignment(start, np.maximum(end, start), base.matched, timed_by, base.prob,
                           {**base.stats, "forced": forced})
    shift = np.abs(out.start - base.start)[use]
    return out, {"method": method, "refined_frac": round(float(use.mean()), 4), "segments": len(segs),
                 "median_shift_s": round(float(np.median(shift)), 3) if shift.size else None}


def _whisperx(cfg: Config, scfg: dict[str, Any], audio: np.ndarray, sr: int, words: Sequence[str],
              segs: list[tuple[int, int, float, float]], dev: str) -> list[_align.Timed]:
    import whisperx

    path = models.local_path(cfg, str(scfg.get("whisperx_align_model", "wav2vec2_align_en")))
    model, meta = whisperx.load_align_model(language_code="en", device=dev, model_name=str(path))
    transcript = [{"start": t0, "end": t1, "text": " ".join(words[lo:hi])} for lo, hi, t0, t1 in segs]
    res = whisperx.align(transcript, model, meta, audio, dev, return_char_alignments=False)
    return [_align.Timed(w["word"], float(w["start"]), float(w["end"]), float(w.get("score", np.nan)))
            for w in res.get("word_segments", []) if w.get("start") is not None and w.get("end") is not None]


def _qwen(cfg: Config, scfg: dict[str, Any], audio: np.ndarray, sr: int, words: Sequence[str],
          segs: list[tuple[int, int, float, float]], dev: str) -> list[_align.Timed]:
    import torch
    from qwen_asr import Qwen3ForcedAligner

    path = models.local_path(cfg, str(scfg.get("qwen_aligner_model", "qwen_forced_aligner")))
    dtype = torch.bfloat16 if dev == "cuda" else torch.float32
    model = Qwen3ForcedAligner.from_pretrained(str(path), dtype=dtype, device_map="cuda:0" if dev == "cuda" else "cpu")
    batch = int(scfg.get("qwen_batch_size", 8))
    out: list[_align.Timed] = []
    for k in range(0, len(segs), batch):
        part = segs[k:k + batch]
        clips = [(audio[int(t0 * sr):int(t1 * sr)], sr) for _, _, t0, t1 in part]
        texts = [" ".join(words[lo:hi]) for lo, hi, _, _ in part]
        res = model.align(audio=clips, text=texts, language=["English"] * len(part))
        for (_, _, t0, _), items in zip(part, res):
            out.extend(_align.Timed(str(it.text), t0 + float(it.start_time), t0 + float(it.end_time)) for it in items)
    return out
