"""turns (CPU, runs inside the GPU wave): transcript speaker turns with media times, the meeting anchor.

Words come from the official transcript PDF; times come from the configured clock (``turns.clock_source``):

* ``asr`` (default, team plan): faster-whisper words from the ``asr`` stage
* ``vtt``: the official WebVTT captions (a vendor forced alignment of the same transcript; 7 of the default
  75 meetings have none)
* ``vtt_then_asr``: captions when the meeting has them, otherwise ASR

Each transcript word takes the time of the clock word it aligns with (``fedpress.stages._align``); unmatched
words are interpolated. ``turns.align.method`` whisperx / qwen_forced_aligner refine the times afterwards.
The chair's first transcript word (the greeting) anchors media time to wall time (``timing.anchor``).

Outputs (stamped):

* ``turns`` turns/turns.parquet: turn_idx, speaker, role, is_chair, segment_kind, qa_idx, text, n_words,
  n_matched, t_start_s, t_end_s, clock_source, match_frac, timing_ok
* ``words`` turns/words.parquet: word_idx, turn_idx, word, matched, timed_by (match|sub|interp|forced),
  t_start_s, t_end_s, prob
* ``anchor`` turns/anchor.json

The text is the edited official transcript, published after the event; a live observer would have ASR text.
Quality flags (``timing_ok``, WER proxy) never delete rows.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .. import clock
from ..stage import StageContext, StageResult, StageSpec
from . import _align, _transcript, _vtt

SPEC = StageSpec(name="turns", requires=("fetch", "asr"), resource="cpu", outputs=("turns", "words", "anchor"),
                 config_keys=("timing", "asr"))


def run(ctx: StageContext) -> StageResult:
    import pandas as pd

    s, m = ctx.scfg, ctx.meeting
    align_cfg: dict[str, Any] = dict(s.get("align") or {})
    pdf = ctx.out("transcript_pdf")
    if not pdf.exists():
        raise FileNotFoundError(f"{pdf} missing: the fetch stage needs fetch.transcript_pdf=true")
    turns = _transcript.classify(
        _transcript.split_turns(_transcript.pdf_text(pdf)), m.chair, str(s["chair_label_regex"]),
        str(s["moderator_label_regex"]), int(s.get("closing_max_words", 25)), float(s.get("label_fuzzy", 0.8)))
    _check(turns, m.chair)
    words = [w for t in turns for w in t.words]
    owner = np.array([k for k, t in enumerate(turns) for _ in t.words], dtype=int)

    source = _source(ctx)
    al = _align.align(words, _timed(ctx, source))
    clock_source, forced_notes = source, None
    method = str(align_cfg.get("method", "text_match"))
    if method != "text_match":
        from . import _forced, _media

        audio, sr = _media.read_wav(ctx.out("audio_wav"))
        al, forced_notes = _forced.refine(method, ctx.cfg, align_cfg, audio, sr, words, owner, al)
        clock_source = "forced"

    max_wer, min_match = float(align_cfg.get("max_wer_proxy", 0.35)), float(align_cfg.get("min_matched_frac", 0.80))
    meeting_ok = al.stats["wer_proxy"] <= max_wer and al.stats["match_frac"] >= min_match

    wdf = pd.DataFrame({"word_idx": np.arange(len(words)), "turn_idx": owner, "word": words,
                        "matched": al.matched, "timed_by": al.timed_by.astype(str),
                        "t_start_s": al.start.astype("float64"), "t_end_s": al.end.astype("float64"),
                        "prob": al.prob.astype("float64")})
    tdf = _turn_table(turns, wdf, clock_source, meeting_ok, min_match)

    opening = tdf[tdf["segment_kind"] == "opening"]
    greeting = float(opening["t_start_s"].iloc[0])
    first_word = wdf[wdf["turn_idx"] == int(opening["turn_idx"].iloc[0])].iloc[0]
    search = float(s.get("greeting_search_s", 240))
    if greeting > search:
        raise ValueError(f"chair greeting at {greeting:.1f} s, beyond turns.greeting_search_s={search:g}: "
                         "the clock alignment is probably wrong for this meeting")
    anchor = clock.make_anchor(ctx.cfg, m, greeting)
    ctx.add_output(clock.save_anchor(ctx.paths.dir, anchor))
    ctx._anchor = anchor

    ctx.write_table(ctx.stamp(tdf), "turns", models=_models(ctx, source, method))
    ctx.write_table(ctx.stamp(wdf), "words", models=_models(ctx, source, method))

    notes: dict[str, Any] = {
        "clock_source": clock_source, "base_clock": source, "align_method": method, "text_source": "transcript_pdf",
        **{k: al.stats[k] for k in ("wer_proxy", "match_frac", "timed_frac", "n_ref_words", "n_hyp_tokens")},
        "timing_ok": bool(meeting_ok), "greeting_media_s": round(greeting, 3), "greeting_word": str(first_word["word"]),
        "greeting_timed_by": str(first_word["timed_by"]), "anchor": anchor.to_json(),
        "n_turns": len(tdf), "n_answers": int((tdf["segment_kind"] == "answer").sum()),
        "n_questions": int((tdf["segment_kind"] == "question").sum()),
        "chair_labels": sorted({t.speaker for t in turns if t.is_chair}),
    }
    if forced_notes:
        notes["forced"] = forced_notes
    if source != "vtt" and s.get("vtt_check", True) and ctx.out("captions_vtt").exists():
        notes["vtt_check"] = _align.compare(al, _align.align(words, _timed(ctx, "vtt")))
    ctx.result.notes.update(notes)
    ctx.log.info("turns.aligned", clock=clock_source, wer_proxy=al.stats["wer_proxy"],
                 match_frac=al.stats["match_frac"], greeting_s=round(greeting, 2), turns=len(tdf))
    return ctx.result


def _check(turns: list[_transcript.Turn], chair: str) -> None:
    if not turns:
        raise ValueError("no speaker labels found in the transcript PDF")
    if not any(t.is_chair for t in turns):
        raise ValueError(f"no turn labelled as chair {chair}; labels: {sorted({t.speaker for t in turns})[:10]}")
    if not any(t.segment_kind == "opening" and t.words for t in turns):
        raise ValueError("no opening remarks found (first chair turn has no words)")


def _source(ctx: StageContext) -> str:
    want = str(ctx.scfg.get("clock_source", "asr"))
    has_vtt, has_asr = ctx.out("captions_vtt").exists(), ctx.out("asr_words").exists()
    if want == "vtt_then_asr":
        want = "vtt" if has_vtt else "asr"
    if want == "vtt" and not has_vtt:
        raise FileNotFoundError("turns.clock_source=vtt but raw/captions.vtt is missing (no caption track, or "
                                "fetch.captions_vtt=false); use vtt_then_asr")
    if want == "asr" and not has_asr:
        raise FileNotFoundError("asr/words.parquet missing: run the asr stage (asr.enabled=true)")
    return want


def _timed(ctx: StageContext, source: str) -> list[_align.Timed]:
    if source == "vtt":
        cues, header = _vtt.read(ctx.out("captions_vtt"))
        tsmap = header.get("X-TIMESTAMP-MAP", "")
        if tsmap and "MPEGTS:0" not in tsmap.replace(" ", ""):
            ctx.log.warning("turns.vtt_timestamp_map", value=tsmap, hint="cue times are used as media times")
        return [_align.Timed(w, a, b) for w, a, b in _vtt.timed_words(cues)]
    from .. import io

    df = io.read_parquet(ctx.out("asr_words"), columns=["word", "t_start_s", "t_end_s", "prob"])
    return [_align.Timed(str(r.word), float(r.t_start_s), float(r.t_end_s), float(r.prob))
            for r in df.itertuples(index=False)]


def _turn_table(turns: list[_transcript.Turn], wdf: Any, clock_source: str, meeting_ok: bool,
                min_match: float) -> Any:
    import pandas as pd

    g = wdf.groupby("turn_idx").agg(t_start_s=("t_start_s", "min"), t_end_s=("t_end_s", "max"),
                                    n_matched=("matched", "sum"))
    rows, prev_end = [], 0.0
    for k, t in enumerate(turns):
        if k in g.index:
            a, b, nm = float(g.at[k, "t_start_s"]), float(g.at[k, "t_end_s"]), int(g.at[k, "n_matched"])
        else:  # a label with no spoken words (e.g. only a bracketed note): zero length at the previous end
            a = b = prev_end
            nm = 0
        prev_end = b
        frac = nm / len(t.words) if t.words else float("nan")
        rows.append({"turn_idx": k, "speaker": t.speaker, "role": t.role, "is_chair": t.is_chair,
                     "segment_kind": t.segment_kind, "qa_idx": t.qa_idx, "text": t.text, "n_words": len(t.words),
                     "n_matched": nm, "t_start_s": a, "t_end_s": b, "clock_source": clock_source,
                     "match_frac": frac, "timing_ok": bool(meeting_ok and frac >= min_match)})
    return pd.DataFrame(rows).astype({"t_start_s": "float64", "t_end_s": "float64", "match_frac": "float64"})


def _models(ctx: StageContext, source: str, method: str) -> tuple[str, ...]:
    keys = [str(ctx.cfg.get("asr.model"))] if source == "asr" else []
    if method == "whisperx":
        keys.append(str(ctx.scfg.get("align", {}).get("whisperx_align_model", "wav2vec2_align_en")))
    elif method == "qwen_forced_aligner":
        keys.append(str(ctx.scfg.get("align", {}).get("qwen_aligner_model", "qwen_forced_aligner")))
    return tuple(keys)
