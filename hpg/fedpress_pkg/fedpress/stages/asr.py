"""asr (GPU): word timestamps from Whisper large-v3-turbo via faster-whisper (the team plan's clock).

Outputs (raw, not stamped: the anchor exists only after ``turns``):

* ``asr_words``    asr/words.parquet: word_idx, word, t_start_s, t_end_s, prob, seg_idx
* ``asr_segments`` asr/segments.parquet: seg_idx, t_start_s, t_end_s, text, avg_logprob, no_speech_prob,
  compression_ratio
* ``asr_meta``     asr/asr.json: model, revision, device, decoding parameters, durations, real-time factor

The words are only a clock: ``turns`` keeps the transcript PDF's words and takes their times from here. With
``turns.clock_source: vtt_then_asr`` meetings that have official captions are marked not applicable.
"""

from __future__ import annotations

import os
import time
from typing import Any

from .. import gpu, io, models
from ..stage import StageContext, StageResult, StageSpec
from . import _media

SPEC = StageSpec(name="asr", requires=("audio",), resource="gpu",
                 outputs=("asr_words", "asr_segments", "asr_meta"), config_keys=(), stamped=False)


def applies(ctx: StageContext) -> str | None:
    src = str(ctx.cfg.get("turns.clock_source", "asr"))
    if src == "vtt":
        return "turns.clock_source=vtt: captions are the clock (set asr.enabled=false to skip this stage)"
    if src == "vtt_then_asr" and ctx.out("captions_vtt").exists():
        return "turns.clock_source=vtt_then_asr and this meeting has official captions"
    return None


def run(ctx: StageContext) -> StageResult:
    import pandas as pd

    s = ctx.scfg
    wav = ctx.out("audio_wav")
    if not wav.exists():
        raise FileNotFoundError(f"{wav} missing: run the audio stage")
    gpu.preload_cuda_libs()
    from faster_whisper import BatchedInferencePipeline, WhisperModel

    dev = gpu.device(str(s.get("device", "cuda")))
    ctype = str(s.get("compute_type", "float16")) if dev == "cuda" else str(s.get("compute_type_cpu", "int8"))
    key = str(s.get("model", "whisper_turbo_ct2"))
    path = models.local_path(ctx.cfg, key)
    threads = int(os.environ.get("OMP_NUM_THREADS", "0") or 0)
    t0 = time.perf_counter()
    model = WhisperModel(str(path), device=dev, compute_type=ctype, cpu_threads=threads)
    audio, sr = _media.read_wav(wav)
    if sr != 16000:
        raise ValueError(f"{wav}: {sr} Hz, faster-whisper needs 16 kHz (audio.sample_rate)")
    load_s = time.perf_counter() - t0
    opts: dict[str, Any] = {
        "language": s.get("language", "en"), "beam_size": int(s.get("beam_size", 5)),
        "word_timestamps": bool(s.get("word_timestamps", True)), "vad_filter": bool(s.get("vad_filter", True)),
        "condition_on_previous_text": bool(s.get("condition_on_previous_text", False)),
    }
    if s.get("initial_prompt"):
        opts["initial_prompt"] = str(s["initial_prompt"])
    batch = int(s.get("batch_size", 16) or 0)
    t1 = time.perf_counter()
    if batch > 0:
        opts.pop("condition_on_previous_text")
        segments, info = BatchedInferencePipeline(model=model).transcribe(audio, batch_size=batch, **opts)
    else:
        segments, info = model.transcribe(audio, **opts)
    seg_rows, word_rows = [], []
    for k, seg in enumerate(segments):  # generator: decoding happens here
        seg_rows.append((k, float(seg.start), float(seg.end), seg.text.strip(), float(seg.avg_logprob),
                         float(seg.no_speech_prob), float(seg.compression_ratio)))
        for w in seg.words or []:
            text = w.word.strip()
            if text:
                word_rows.append((text, float(w.start), float(w.end), float(w.probability), k))
    decode_s = time.perf_counter() - t1
    words = pd.DataFrame(word_rows, columns=["word", "t_start_s", "t_end_s", "prob", "seg_idx"])
    words.insert(0, "word_idx", range(len(words)))
    segs = pd.DataFrame(seg_rows, columns=["seg_idx", "t_start_s", "t_end_s", "text", "avg_logprob",
                                           "no_speech_prob", "compression_ratio"])
    if words.empty:
        raise RuntimeError("faster-whisper returned no words (silent or undecodable audio?)")
    ctx.write_table(words, "asr_words", models=(key,))
    ctx.write_table(segs, "asr_segments", models=(key,))
    dur = len(audio) / sr
    meta = {"model_key": key, "repo": ctx.cfg.model(key).get("id"), "revision": ctx.cfg.model(key).get("revision"),
            "path": str(path), "device": dev, "compute_type": ctype, "batch_size": batch, **opts,
            "detected_language": getattr(info, "language", None), "audio_s": round(dur, 3),
            "load_s": round(load_s, 2), "decode_s": round(decode_s, 2), "rtf": round(decode_s / max(dur, 1e-9), 4),
            "n_words": len(words), "n_segments": len(segs), "versions": _versions(), "gpu": gpu.info(),
            "created_utc": io.utc_now()}
    ctx.add_output(io.atomic_write_json(ctx.out("asr_meta"), meta))
    ctx.result.notes.update({"n_words": len(words), "rtf": meta["rtf"], "device": dev, "compute_type": ctype,
                             "mean_word_prob": round(float(words["prob"].mean()), 4)})
    ctx.log.info("asr.decoded", words=len(words), segments=len(segs), rtf=meta["rtf"], device=dev)
    return ctx.result


def _versions() -> dict[str, str]:
    out = {}
    for mod in ("faster_whisper", "ctranslate2"):
        try:
            out[mod] = __import__(mod).__version__
        except (ImportError, AttributeError):
            out[mod] = "?"
    return out
