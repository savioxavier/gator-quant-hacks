"""voice (GPU): the Powell-only vocal_proxy on chair answer chunks. A proxy, not "the emotion of the chair".

Chunks (``voice.chunking``): ``fixed`` windows of chunk_s every hop_s inside each answer turn (default 8 s,
non-overlapping, a tail shorter than min_chunk_s dropped) or ``words`` (cut at word boundaries/pauses, between
min_chunk_s and max_chunk_s). Each chunk is processed on its own audio only: no whole-video normalisation.

Features per chunk:

* audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim: arousal, dominance, valence (about 0..1). The model's
  feature extractor normalises each chunk by its own mean/variance (causal). Valence partly re-reads the words.
* praat-parselmouth: F0 in semitones re ``f0.semitone_ref_hz`` (median, IQR, p10, p90), voiced fraction,
  intensity (dB, energy mean), HNR (dB).
* word timing (turns/words): speech rate (words/s), articulation rate (words per voiced-speech second), pause
  fraction and count (gaps >= ``pause_min_s`` between exactly matched words).
* options, off by default: emotion2vec_plus_large class probabilities (``e2v_*``), openSMILE eGeMAPSv02
  functionals (``egemaps_*``), 3loi WavLM A/D/V cross-check (``ser3_*``).

identity_frac = share of the chunk covered by diarize chunks with chair_verified; identity_ok =
identity_frac >= ``identity_min_frac`` (labels only when diarize is disabled). Rows are kept and flagged.
Output ``voice_chunks`` voice/voice_chunks.parquet, stamped at chunk end.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from .. import gpu, io, models
from ..stage import StageContext, StageResult, StageSpec
from . import _chunks, _media

SPEC = StageSpec(name="voice", requires=("audio", "turns", "diarize"), resource="gpu", outputs=("voice_chunks",))
ADV_DEFAULT = ("arousal", "dominance", "valence")


def applies(ctx: StageContext) -> str | None:
    chairs = ctx.scfg.get("chairs") or []
    if chairs and ctx.meeting.chair not in chairs:
        return f"chair {ctx.meeting.chair} not in voice.chairs {list(chairs)}"
    return None


def run(ctx: StageContext) -> StageResult:
    s = ctx.scfg
    turns = io.read_parquet(ctx.out("turns"))
    words = io.read_parquet(ctx.out("words"))
    audio, sr = _media.read_wav(ctx.out("audio_wav"))
    df = _chunks.turn_chunks(turns[turns["is_chair"]], float(s.get("chunk_s", 8.0)), float(s.get("hop_s", 8.0)),
                             float(s.get("min_chunk_s", 3.0)), kinds=s.get("segments") or ["answer"], words=words,
                             mode=str(s.get("chunking", "fixed")), max_len=float(s.get("max_chunk_s", 15.0)),
                             pause_s=float(s.get("chunk_pause_s", 0.6)))
    df = df.drop(columns=["role", "segment_kind"])
    clips = [_media.slice_audio(audio, sr, a, b) for a, b in zip(df["t_start_s"], df["t_end_s"])]
    df = df.join(identity(ctx, df, float(s.get("identity_min_frac", 1.0)), bool(s.get("identity_gate", True))))
    used: list[str] = []
    if len(df):
        dev = gpu.device(str(s.get("device", "cuda")))
        key = str(s.get("model", "audeering_msp_dim"))
        adv, emb = audeering_adv(ctx.cfg, key, clips, sr, dev, int(s.get("batch_size", 32)),
                                 str(s.get("dtype", "float32")))
        df = df.join(adv)
        used.append(key)
        if s.get("save_embeddings", False):
            path = ctx.paths.stage_dir("voice") / "voice_embeddings.npz"
            np.savez_compressed(path, chunk_idx=df["chunk_idx"].to_numpy(), embedding=emb.astype(np.float16))
            ctx.add_output(path)
        f0 = dict(s.get("f0") or {})
        ranges = dict(f0.get("pitch_range_hz") or {})
        rng = ranges.get(ctx.meeting.chair) or ranges.get("default", [75, 300])
        df = df.join(_frame([prosody(c, sr, float(rng[0]), float(rng[1]), float(f0.get("time_step_s", 0.01)),
                                     float(f0.get("semitone_ref_hz", 100.0))) for c in clips], df.index))
        df = df.join(_frame([word_timing(words, a, b, float(s.get("pause_min_s", 0.25)))
                             for a, b in zip(df["t_start_s"], df["t_end_s"])], df.index))
        for opt, fn in (("emotion2vec", emotion2vec), ("ser_crosscheck", ser_3loi), ("opensmile", opensmile_feats)):
            ocfg = dict(s.get(opt) or {})
            if ocfg.get("enabled", False):
                df = df.join(fn(ctx.cfg, ocfg, clips, sr, dev).set_index(df.index))
                if ocfg.get("model"):
                    used.append(str(ocfg["model"]))
    else:
        for col in (*ADV_DEFAULT, "f0_median_st", "speech_rate_wps"):
            df[col] = np.nan
    ctx.write_table(ctx.stamp(df), "voice_chunks", models=tuple(used))
    ok = df[df["identity_ok"]] if len(df) else df
    ctx.result.notes.update({"n_chunks": len(df), "n_identity_ok": int(len(ok)),
                             "chunk_s_median": round(float(df["dur_s"].median()), 2) if len(df) else None,
                             **{f"{c}_median": round(float(ok[c].median()), 4) for c in ADV_DEFAULT if len(ok)}})
    ctx.log.info("voice.done", chunks=len(df), identity_ok=int(len(ok)))
    return ctx.result


def identity(ctx: StageContext, df: Any, min_frac: float, gate: bool) -> Any:
    import pandas as pd

    path = ctx.out("chair_check")
    if not gate or not path.exists() or ctx.cfg.section("diarize").get("enabled", True) is False:
        return pd.DataFrame({"identity_frac": np.nan, "identity_ok": True, "identity_source": "labels"}, index=df.index)
    cc = io.read_parquet(path, columns=["t_start_s", "t_end_s", "chair_verified"])
    ver = cc.loc[cc["chair_verified"].astype(bool), ["t_start_s", "t_end_s"]].to_numpy()
    frac = _chunks.coverage(df[["t_start_s", "t_end_s"]].to_numpy(), ver)
    return pd.DataFrame({"identity_frac": frac, "identity_ok": frac >= min_frac - 1e-9,
                         "identity_source": "diarize"}, index=df.index)


def _frame(rows: list[dict[str, float]], index: Any) -> Any:
    import pandas as pd

    return pd.DataFrame(rows, index=index)


# ------------------------------------------------------------------ audeering A/D/V
def audeering_adv(cfg: Any, key: str, clips: list[np.ndarray], sr: int, dev: str, batch: int,
                  dtype: str = "float32") -> tuple[Any, np.ndarray]:
    """Arousal/dominance/valence per clip with the model card's EmotionModel; equal-length clips are batched."""
    import pandas as pd

    gpu.preload_cuda_libs()
    import torch
    import torch.nn as nn
    from transformers import Wav2Vec2FeatureExtractor
    from transformers.models.wav2vec2.modeling_wav2vec2 import Wav2Vec2Model, Wav2Vec2PreTrainedModel

    class RegressionHead(nn.Module):
        def __init__(self, config: Any) -> None:
            super().__init__()
            self.dense = nn.Linear(config.hidden_size, config.hidden_size)
            self.dropout = nn.Dropout(config.final_dropout)
            self.out_proj = nn.Linear(config.hidden_size, config.num_labels)

        def forward(self, x: Any) -> Any:
            return self.out_proj(self.dropout(torch.tanh(self.dense(self.dropout(x)))))

    class EmotionModel(Wav2Vec2PreTrainedModel):
        def __init__(self, config: Any) -> None:
            super().__init__(config)
            self.config = config
            self.wav2vec2 = Wav2Vec2Model(config)
            self.classifier = RegressionHead(config)
            self.init_weights()

        def forward(self, input_values: Any) -> Any:
            hidden = self.wav2vec2(input_values)[0].mean(dim=1)
            return hidden, self.classifier(hidden)

    path = models.local_path(cfg, key)
    proc = Wav2Vec2FeatureExtractor.from_pretrained(str(path))  # per-chunk zero-mean/unit-variance
    torch_dtype = torch.float16 if (dtype == "float16" and dev == "cuda") else torch.float32
    model = EmotionModel.from_pretrained(str(path)).to(dev, dtype=torch_dtype).eval()
    labels = _labels(model.config)
    preds = np.full((len(clips), len(labels)), np.nan, dtype=np.float32)
    embs = np.zeros((len(clips), model.config.hidden_size), dtype=np.float32)
    by_len: dict[int, list[int]] = {}
    for i, c in enumerate(clips):
        by_len.setdefault(len(c), []).append(i)
    for n, idx in by_len.items():
        if n < sr // 10:
            continue
        for k in range(0, len(idx), batch):
            part = idx[k:k + batch]
            x = proc([clips[i] for i in part], sampling_rate=sr, return_tensors="np")["input_values"]
            with torch.inference_mode():
                h, y = model(torch.from_numpy(np.asarray(x, dtype=np.float32)).to(dev, dtype=torch_dtype))
            preds[part] = y.float().cpu().numpy()
            embs[part] = h.float().cpu().numpy()
    return pd.DataFrame(preds, columns=labels), embs


def _labels(config: Any) -> list[str]:
    id2 = getattr(config, "id2label", None) or {}
    names = [str(id2.get(i, id2.get(str(i), ""))).lower() for i in range(int(config.num_labels))]
    return names if set(names) == set(ADV_DEFAULT) else list(ADV_DEFAULT)


# ------------------------------------------------------------------ prosody (parselmouth) and word timing
def prosody(clip: np.ndarray, sr: int, f0_min: float, f0_max: float, step: float, ref_hz: float) -> dict[str, float]:
    import parselmouth

    nan = float("nan")
    out = {"f0_median_st": nan, "f0_iqr_st": nan, "f0_p10_st": nan, "f0_p90_st": nan, "voiced_frac": nan,
           "intensity_db": nan, "hnr_db": nan}
    if len(clip) < int(0.5 * sr):
        return out
    snd = parselmouth.Sound(clip.astype(np.float64), sampling_frequency=sr)
    f0 = snd.to_pitch(time_step=step, pitch_floor=f0_min, pitch_ceiling=f0_max).selected_array["frequency"]
    voiced = f0[f0 > 0]
    out["voiced_frac"] = float(len(voiced) / max(1, len(f0)))
    if len(voiced) >= 5:
        st = 12.0 * np.log2(voiced / ref_hz)
        q10, q25, q50, q75, q90 = np.quantile(st, [0.1, 0.25, 0.5, 0.75, 0.9])
        out |= {"f0_median_st": float(q50), "f0_iqr_st": float(q75 - q25), "f0_p10_st": float(q10),
                "f0_p90_st": float(q90)}
    inten = snd.to_intensity(minimum_pitch=f0_min).values.ravel()
    if inten.size:
        out["intensity_db"] = float(10 * np.log10(np.mean(10 ** (inten / 10))))
    hnr = snd.to_harmonicity_cc(time_step=step, minimum_pitch=f0_min).values.ravel()
    hnr = hnr[hnr > -199]
    if hnr.size:
        out["hnr_db"] = float(np.mean(hnr))
    return out


def word_timing(words: Any, t0: float, t1: float, pause_min: float) -> dict[str, float]:
    """Rates and pauses inside [t0, t1] from aligned transcript words (a word counts where its midpoint falls)."""
    dur = t1 - t0
    mid = (words["t_start_s"] + words["t_end_s"]) / 2
    w = words[(mid >= t0) & (mid < t1)].sort_values("t_start_s")
    n = len(w)
    out = {"n_words": float(n), "speech_rate_wps": n / dur if dur > 0 else math.nan, "articulation_rate_wps": math.nan,
           "pause_frac": math.nan, "n_pauses": math.nan}
    m = w[w["matched"].astype(bool)]
    if len(m) >= 2:
        gaps = m["t_start_s"].to_numpy()[1:] - m["t_end_s"].to_numpy()[:-1]
        pauses = gaps[gaps >= pause_min]
        pause_t = float(pauses.sum())
        out |= {"pause_frac": pause_t / dur, "n_pauses": float(len(pauses)),
                "articulation_rate_wps": n / (dur - pause_t) if dur - pause_t > 0 else math.nan}
    return out


# ------------------------------------------------------------------ plan_v0 options (off by default)
def emotion2vec(cfg: Any, ocfg: dict[str, Any], clips: list[np.ndarray], sr: int, dev: str) -> Any:
    """emotion2vec_plus_large (FunASR) utterance-level class probabilities, columns e2v_<label>."""
    import pandas as pd
    from funasr import AutoModel

    path = models.local_path(cfg, str(ocfg.get("model", "emotion2vec_plus_large")))
    model = AutoModel(model=str(path), device=dev, disable_update=True, disable_pbar=True, log_level="ERROR")
    rows = []
    for c in clips:
        res = model.generate(c.astype(np.float32), fs=sr, granularity="utterance", extract_embedding=False)[0]
        rows.append({f"e2v_{str(lab).split('/')[-1].strip().lower() or 'unk'}": float(p)
                     for lab, p in zip(res["labels"], res["scores"])})
    return pd.DataFrame(rows)


def ser_3loi(cfg: Any, ocfg: dict[str, Any], clips: list[np.ndarray], sr: int, dev: str) -> Any:
    """3loi/SER-Odyssey-Baseline-WavLM-Multi-Attributes (MIT) arousal/dominance/valence, columns ser3_*."""
    import pandas as pd
    import torch
    from transformers import AutoModelForAudioClassification

    path = models.local_path(cfg, str(ocfg.get("model", "ser_3loi_wavlm")))
    model = AutoModelForAudioClassification.from_pretrained(str(path), trust_remote_code=True).to(dev).eval()
    mean, std = float(model.config.mean), float(model.config.std)
    names = [str(model.config.id2label[i]).lower() for i in range(len(model.config.id2label))]
    rows = []
    for c in clips:
        x = torch.from_numpy(((c - mean) / (std + 1e-6)).astype(np.float32))[None].to(dev)
        with torch.inference_mode():
            out = model(x, torch.ones_like(x))
        y = getattr(out, "logits", out).float().cpu().numpy().ravel()
        rows.append({f"ser3_{n}": float(v) for n, v in zip(names, y)})
    return pd.DataFrame(rows)


def opensmile_feats(cfg: Any, ocfg: dict[str, Any], clips: list[np.ndarray], sr: int, dev: str) -> Any:
    """openSMILE functionals (default eGeMAPSv02, 88 features), columns egemaps_<name>. CPU."""
    import opensmile
    import pandas as pd

    smile = opensmile.Smile(feature_set=getattr(opensmile.FeatureSet, str(ocfg.get("feature_set", "eGeMAPSv02"))),
                            feature_level=opensmile.FeatureLevel.Functionals)
    rows = [smile.process_signal(c, sr).iloc[0].add_prefix("egemaps_").to_dict() for c in clips]
    return pd.DataFrame(rows)
