"""text (gpu): sentence-level stance, sentiment and dictionary features for the statement, the chair's answers
and the reporters' questions; one row per sentence and one per unit. Opening remarks are not scored by
default (team plan); add ``opening`` to ``text.units`` for descriptive use.

Scorers (``text.stance_models`` + ``text.sentiment_models``, registry ``models:``):

* ``chrono_wf`` (primary, deviation D1): walk-forward ChronoBERT fine-tunes for the presser's year, seed
  probabilities averaged; trained by ``python -m fedpress.train.stance_walkforward``.
* ``fomc_roberta``: gtfintechlab/FOMC-RoBERTa (gated, manual approval). Scored when its weights are in the
  cache; otherwise recorded as unavailable (a cross-check never fails the meeting).
* ``centralbank_roberta``: agent sentiment (positive/negative for households, firms, ...), not stance (A-30).

Unit score (A-10, D1): sentences with >= ``text.sentences.min_words`` words, equal weights.
``<p>_hawk_share`` = share hawkish - share dovish (argmax), ``<p>_hawk_prob`` = mean P(hawkish) - P(dovish);
``hawk`` = the primary scorer under ``text.score``. ``<p>_hawk_share_tdw`` uses only sentences passing the TDW
keyword filter (robustness). Loughran-McDonald counts and hedge phrases are per 100 words of the unit.
``nov_stmt_lex`` (and ``nov_stmt_emb`` when embeddings are on) = 1 - cosine with the same day's statement.

Tables (common id/timing columns added by ``ctx.write_table``):

* ``text_sentences``: unit, turn_idx, qa_idx, sent_idx, text, n_words, included, tdw_filter, t_start_s,
  t_end_s, time_method, splitter, <p>_p_<label>, <p>_label, <p>_truncated, lm_<cat>, hedge_count,
  in_tdw_labels. known_at = sentence end + latency (statement: release + latency).
* ``text_units``: unit, turn_idx, qa_idx, speaker, role, segment_kind, n_sentences, n_included, n_words,
  <p>_hawk_share / _hawk_prob / _hawk_share_tdw / _n_hawkish / _n_dovish / _n_neutral, <p>_in_train,
  cbr_sentiment, lm_<cat>_per100, hedge_count, hedge_per100, nov_stmt_lex, [nov_stmt_emb], hawk, hawk_model,
  hawk_method, stance_model_id, in_classifier_train. known_at = unit end + latency.
* ``text_vectors``: unit, turn_idx, tf_idx / tf_val (hashed term counts), [emb] (for cross-meeting novelty in
  the dataset build).
"""

from __future__ import annotations

import math
from datetime import date
from typing import Any

from .. import io
from ..stage import StageContext, StageResult, StageSpec

SPEC = StageSpec(name="text", requires=("fetch", "turns"), resource="gpu",
                 outputs=("text_sentences", "text_units", "text_vectors"), config_keys=("timing", "train"))

UNIT_ROLES = {"answer": "chair", "opening": "chair", "closing": "chair", "question": "reporter"}
STANCE_LABELS = ("hawkish", "dovish", "neutral")


def _prefix(ctx: StageContext, key: str) -> str:
    return str(ctx.cfg.model(key).get("prefix") or key)


def _units(ctx: StageContext, turns: Any) -> list[dict[str, Any]]:
    """Chair/reporter turns selected by text.units (statement handled separately), in turn order."""
    out = []
    for unit in ctx.scfg.get("units", ["statement", "answer", "question"]):
        if unit == "statement":
            continue
        if unit not in UNIT_ROLES:
            raise ValueError(f"text.units: unknown unit {unit!r} (statement, answer, question, opening, closing)")
        sel = turns[turns["segment_kind"] == unit]
        sel = sel[sel["is_chair"]] if UNIT_ROLES[unit] == "chair" else sel[~sel["is_chair"]]
        for r in sel.itertuples(index=False):
            out.append({"unit": unit, "turn_idx": int(r.turn_idx), "qa_idx": int(r.qa_idx), "speaker": str(r.speaker),
                        "role": str(r.role), "segment_kind": unit, "text": str(r.text),
                        "t_start_s": float(r.t_start_s), "t_end_s": float(r.t_end_s)})
    return sorted(out, key=lambda u: u["turn_idx"])


def _statement(ctx: StageContext) -> dict[str, Any] | None:
    from ..nlp.statement import statement_paragraphs

    st = ctx.scfg.get("statement", {}) or {}
    path = ctx.out("statement_html")
    if not path.exists():
        if st.get("required", True) and "statement" in ctx.scfg.get("units", []):
            raise FileNotFoundError(f"{path} missing (fetch.statement_html); the H1 gap needs the statement")
        return None
    paras = statement_paragraphs(path.read_text(encoding="utf-8", errors="replace"), str(st.get("stop_regex")))
    if not paras:
        raise ValueError(f"{path}: no statement paragraphs found")
    return {"unit": "statement", "turn_idx": -1, "qa_idx": -1, "speaker": "FOMC", "role": "committee",
            "segment_kind": "statement", "text": " ".join(paras), "t_start_s": math.nan, "t_end_s": math.nan,
            "n_paragraphs": len(paras)}


def _word_times(words: Any, turn_idx: int) -> tuple[list[float], list[float]] | None:
    """Start/end times of a turn's transcript words; an unknown end takes the next known time (only later,
    never earlier, so known_at stays conservative); an unknown start takes the previous known end."""
    if words is None:
        return None
    w = words[words["turn_idx"] == turn_idx].sort_values("word_idx")
    if not len(w):
        return None
    starts, ends = w["t_start_s"].astype(float).tolist(), w["t_end_s"].astype(float).tolist()
    nxt = math.nan
    for i in range(len(ends) - 1, -1, -1):
        if math.isnan(ends[i]):
            ends[i] = nxt
        nxt = starts[i] if not math.isnan(starts[i]) else (ends[i] if not math.isnan(ends[i]) else nxt)
    prev = math.nan
    for i in range(len(starts)):
        if math.isnan(starts[i]):
            starts[i] = prev
        prev = ends[i] if not math.isnan(ends[i]) else prev
    return starts, ends


def _sentence_times(text: str, spans: list[Any], times: tuple[list[float], list[float]] | None,
                    t0: float, t1: float) -> list[tuple[float, float, str]]:
    from ..nlp.split import spoken_tokens

    toks = spoken_tokens(text)
    out = []
    for sp in spans:
        idx = [i for i, (a, _) in enumerate(toks) if sp.start <= a < sp.end] or [0]
        i0, i1 = idx[0], idx[-1]
        if times is not None and len(times[0]) == len(toks):
            s, e, how = times[0][i0], times[1][i1], "words"
        elif times is not None and toks:  # counts differ: proportional map; the end rounds up (later, never earlier)
            n = len(times[0])
            j0, j1 = min(n - 1, i0 * n // len(toks)), min(n - 1, math.ceil((i1 + 1) * n / len(toks)) - 1)
            s, e, how = times[0][j0], times[1][j1], "words_prop"
        else:
            frac0, frac1 = sp.start / max(1, len(text)), sp.end / max(1, len(text))
            s, e, how = t0 + (t1 - t0) * frac0, t0 + (t1 - t0) * frac1, "interp"
        s = t0 if math.isnan(s) else min(max(s, t0), t1)
        e = t1 if math.isnan(e) else min(max(e, s), t1)
        out.append((s, e, how))
    return out


def _resolve(ctx: StageContext, key: str) -> tuple[list[Any], str, dict[str, Any]]:
    """(model dirs, model id for the rows, info) or raise when the model is not usable here."""
    from ..models import local_path

    spec = ctx.cfg.model(key)
    if key == "chrono_wf":
        from ..train.stance_walkforward import year_models

        mkey, dirs, metas = year_models(ctx.cfg, ctx.meeting.presser_date.year)
        if any(m.get("smoke") for m in metas) and not ctx.scfg.get("chrono_wf", {}).get("allow_smoke", False):
            raise RuntimeError(f"walk-forward model {mkey} is a smoke-test model (--max-rows/--max-epochs)")
        info = {"key": mkey, "seeds": [m["seed"] for m in metas], "val_macro_f1": [m["val_macro_f1"] for m in metas],
                "base_revision": metas[0]["base_revision"], "labels_sha256": metas[0]["labels_sha256"],
                "heldout": {str(m["seed"]): m.get("heldout") for m in metas}}
        return dirs, f"chrono_wf:{mkey}", info
    if spec.get("source") != "hf":
        raise ValueError(f"model {key}: only hf classifiers can score sentences")
    path = local_path(ctx.cfg, key)
    if not (path / "config.json").exists():
        raise FileNotFoundError(f"{path}: no config.json")
    return [path], f"{key}@{str(spec.get('revision', ''))[:12]}", {"revision": spec.get("revision")}


def _in_train(ctx: StageContext, key: str) -> bool | None:
    """Model-cutoff registry (A-29): True when the meeting is on or before the model's training-data end."""
    if key == "chrono_wf":
        return False  # labels <= Y-1 and base pretrained to Y-1 by construction
    end = ctx.cfg.model(key).get("data_end")
    return None if not end else ctx.meeting.meeting_date <= date.fromisoformat(str(end))


def run(ctx: StageContext) -> StageResult:
    import numpy as np
    import pandas as pd

    from ..gpu import device as pick_device
    from ..gpu import preload_cuda_libs
    from ..nlp import classify, lexicon, split, vectors
    from ..train import labels as lab

    s = ctx.scfg
    sent_cfg = s.get("sentences", {}) or {}
    min_words = int(sent_cfg.get("min_words", 4))
    splitter = split.make_splitter(str(sent_cfg.get("splitter", "fedpress_regex")))
    sp_id = split.splitter_info(str(sent_cfg.get("splitter", "fedpress_regex")))["splitter"]
    turns = io.read_parquet(ctx.out("turns"))
    words = io.read_parquet(ctx.out("words")) if ctx.out("words").exists() else None
    units = _units(ctx, turns)
    stmt = _statement(ctx) if "statement" in s.get("units", []) else None
    if stmt is not None:
        units = [stmt] + units
    if not any(u["unit"] == "answer" for u in units) and "answer" in s.get("units", []):
        raise ValueError("no chair answers in turns")

    # ---- sentences, times, dictionaries
    lm_cfg = s.get("loughran_mcdonald", {}) or {}
    lm_cats = [lexicon.category_key(c) for c in lm_cfg.get("categories", [])]
    lm = None
    if lm_cfg.get("enabled", True) and str(lm_cfg.get("csv_path") or "").strip():
        lm = lexicon.LMDictionary.load(str(lm_cfg["csv_path"]), list(lm_cfg.get("categories", [])))
    elif lm_cfg.get("enabled", True) and lm_cfg.get("required", False):
        raise FileNotFoundError("text.loughran_mcdonald.csv_path is empty (set FEDPRESS_LM_CSV)")
    hedges = lexicon.HedgeMatcher((s.get("hedges", {}) or {}).get("phrases", []))
    tdw_keys: set[str] | None = None
    if lab.labels_path(ctx.cfg).exists():
        tdw_keys = set(pd.read_parquet(lab.labels_path(ctx.cfg), columns=["key"])["key"])
    rows: list[dict[str, Any]] = []
    for u in units:
        text = split.normalise(u["text"])
        u["text_norm"] = text
        spans = splitter(text)
        times = None if u["unit"] == "statement" else _word_times(words, u["turn_idx"])
        tt = ([(math.nan, math.nan, "statement")] * len(spans) if u["unit"] == "statement"
              else _sentence_times(text, spans, times, u["t_start_s"], u["t_end_s"]))
        for k, (sp, (t0, t1, how)) in enumerate(zip(spans, tt)):
            toks = lexicon.words(sp.text)
            nw = split.n_words(sp.text)
            row = {"unit": u["unit"], "turn_idx": u["turn_idx"], "qa_idx": u["qa_idx"], "sent_idx": k,
                   "text": sp.text, "n_words": nw, "included": nw >= min_words, "tdw_filter": lexicon.tdw_filter(sp.text),
                   "t_start_s": t0, "t_end_s": t1, "time_method": how, "splitter": sp_id,
                   "hedge_count": hedges.count(toks),
                   "in_tdw_labels": (lab.sentence_key(sp.text) in tdw_keys) if tdw_keys is not None else None}
            counts = lm.counts(toks) if lm else {}
            for c in lm_cats:
                row[f"lm_{c}"] = counts.get(c, math.nan) if lm else math.nan
            rows.append(row)
    sents = pd.DataFrame(rows)
    if not len(sents):
        raise ValueError("no sentences to score")

    # ---- classifiers
    preload_cuda_libs()
    dev = pick_device(str(s.get("device", "cuda")))
    texts = sents["text"].tolist()
    uniq = list(dict.fromkeys(texts))   # each distinct sentence is scored once
    lut = {t: i for i, t in enumerate(uniq)}
    pos = np.array([lut[t] for t in texts])
    primary = str(s.get("primary", "chrono_wf"))
    stance = list(dict.fromkeys([primary, *s.get("stance_models", [])]))
    sentiment = list(s.get("sentiment_models", []))
    avail: dict[str, Any] = {}
    model_ids: dict[str, str] = {}
    for key in stance + sentiment:
        p = _prefix(ctx, key)
        try:
            dirs, mid, info = _resolve(ctx, key)
            pred = classify.predict(dirs, uniq, device=dev, batch_size=int(s.get("batch_size", 64)),
                                    max_length=int(s.get("max_length", 256)), dtype=str(s.get("dtype", "float32")),
                                    label_map_fallback=ctx.cfg.model(key).get("label_map_fallback"))
        except Exception as e:
            if key == primary and s.get("require_primary", True):
                raise RuntimeError(f"primary stance model {key} unavailable: {e!r}") from e
            avail[key] = {"available": False, "reason": repr(e)[:400]}
            ctx.log.warning("text.model_unavailable", model=key, reason=repr(e)[:400])
            continue
        want = STANCE_LABELS if key in stance else ("positive", "negative")
        if not set(want) <= set(pred.labels):
            raise ValueError(f"{key}: labels {pred.labels} do not contain {want}")
        for lbl in pred.labels:
            sents[f"{p}_p_{lbl}"] = pred.column(lbl)[pos]
        sents[f"{p}_label"] = np.array(pred.argmax_labels(), dtype=object)[pos]
        sents[f"{p}_truncated"] = pred.truncated[pos]
        avail[key] = {"available": True, "model_id": mid, "labels": pred.labels, **pred.info, **info,
                      "n_truncated": int(pred.truncated[pos].sum())}
        model_ids[key] = mid
    if primary not in model_ids:
        raise RuntimeError(f"primary stance model {primary} produced no scores")

    # ---- units
    method = str(s.get("score", "share"))
    if method not in ("share", "prob"):
        raise ValueError("text.score must be share or prob")
    pp = _prefix(ctx, primary)
    stmt_tf = vectors.hashed_tf(stmt["text_norm"]) if stmt is not None else {}
    urows, vrows = [], []
    for u in units:
        g = sents[(sents["unit"] == u["unit"]) & (sents["turn_idx"] == u["turn_idx"])]
        inc = g[g["included"]]
        r: dict[str, Any] = {k: u[k] for k in ("unit", "turn_idx", "qa_idx", "speaker", "role", "segment_kind",
                                               "t_start_s", "t_end_s")}
        nw_total = int(g["n_words"].sum())
        r.update(n_sentences=len(g), n_included=len(inc), n_words=nw_total)
        for key in stance:
            if not avail.get(key, {}).get("available"):
                continue
            p = _prefix(ctx, key)
            lab_col, ph, pd_ = inc[f"{p}_label"], inc[f"{p}_p_hawkish"], inc[f"{p}_p_dovish"]
            n = len(inc)
            r[f"{p}_hawk_share"] = ((lab_col == "hawkish").sum() - (lab_col == "dovish").sum()) / n if n else math.nan
            r[f"{p}_hawk_prob"] = float((ph - pd_).mean()) if n else math.nan
            tdw = inc[inc["tdw_filter"]]
            r[f"{p}_hawk_share_tdw"] = (((tdw[f"{p}_label"] == "hawkish").sum() - (tdw[f"{p}_label"] == "dovish").sum())
                                        / len(tdw)) if len(tdw) else math.nan
            for lbl in STANCE_LABELS:
                r[f"{p}_n_{lbl}"] = int((lab_col == lbl).sum())
            r[f"{p}_in_train"] = _in_train(ctx, key)
        for key in sentiment:
            if avail.get(key, {}).get("available"):
                p = _prefix(ctx, key)
                r[f"{p}_sentiment"] = float((inc[f"{p}_p_positive"] - inc[f"{p}_p_negative"]).mean()) if len(inc) else math.nan
        for c in lm_cats:
            r[f"lm_{c}_per100"] = 100.0 * g[f"lm_{c}"].sum() / nw_total if (lm and nw_total) else math.nan
        r["hedge_count"] = int(g["hedge_count"].sum())
        r["hedge_per100"] = 100.0 * r["hedge_count"] / nw_total if nw_total else math.nan
        tf = vectors.hashed_tf(u["text_norm"])
        r["nov_stmt_lex"] = vectors.novelty(tf, stmt_tf) if u["unit"] != "statement" and stmt_tf else math.nan
        r["hawk"] = r.get(f"{pp}_hawk_{method}", math.nan)
        r["hawk_model"], r["hawk_method"], r["stance_model_id"] = primary, method, model_ids[primary]
        r["in_classifier_train"] = _in_train(ctx, primary)
        if u["unit"] == "statement":
            r["n_paragraphs"] = u.get("n_paragraphs")
        urows.append(r)
        idx, val = vectors.to_lists(tf)
        vrows.append({"unit": u["unit"], "turn_idx": u["turn_idx"], "qa_idx": u["qa_idx"],
                      "t_start_s": u["t_start_s"], "t_end_s": u["t_end_s"], "tf_idx": idx, "tf_val": val})
    unit_df = pd.DataFrame(urows)
    vec_df = pd.DataFrame(vrows)

    emb_cfg = (s.get("novelty", {}) or {}).get("embeddings", {}) or {}
    if emb_cfg.get("enabled", False):
        from ..models import local_path

        ekey = str(emb_cfg["model"])
        emb, einfo = vectors.encode(local_path(ctx.cfg, ekey), [u["text_norm"] for u in units], device=dev,
                                    batch_size=int(emb_cfg.get("batch_size", 16)),
                                    max_seq_length=emb_cfg.get("max_seq_length"), dtype=str(emb_cfg.get("dtype", "float32")))
        vec_df["emb"] = emb
        se = emb[0] if stmt is not None else None
        unit_df["nov_stmt_emb"] = [1.0 - vectors.dense_cosine(e, se) if (se is not None and u["unit"] != "statement")
                                   else math.nan for e, u in zip(emb, units)]
        unit_df["emb_in_train"] = _in_train(ctx, ekey)
        avail[ekey] = {"available": True, **einfo}
        model_ids[ekey] = f"{ekey}@{str(ctx.cfg.model(ekey).get('revision', ''))[:12]}"

    # ---- stamp and write
    def stamped(df: Any) -> Any:
        st = df[df["unit"] == "statement"]
        rest = df[df["unit"] != "statement"]
        parts = [ctx.stamp_statement(st)] if len(st) else []
        if len(rest):
            parts.append(ctx.stamp(rest))
        return pd.concat(parts, ignore_index=True)

    for col in ("in_tdw_labels",):
        sents[col] = pd.array(sents[col].tolist(), dtype="boolean")
    for col in [c for c in unit_df.columns if c.endswith("_in_train") or c == "in_classifier_train"]:
        unit_df[col] = pd.array(unit_df[col].tolist(), dtype="boolean")
    used = tuple(k for k in model_ids if k != "chrono_wf")
    ctx.write_table(stamped(sents), "text_sentences", models=used)
    ctx.write_table(stamped(unit_df), "text_units", models=used)
    ctx.write_table(stamped(vec_df), "text_vectors", models=used)
    ctx.result.models.update(model_ids)
    n_ans = unit_df[unit_df["unit"] == "answer"]
    ctx.result.notes.update({
        "models": avail, "primary": primary, "score": method, "splitter": sp_id, "min_words": min_words,
        "n_units": {k: int(v) for k, v in unit_df["unit"].value_counts().items()},
        "n_sentences": int(len(sents)), "n_included": int(sents["included"].sum()),
        "time_methods": {k: int(v) for k, v in sents["time_method"].value_counts().items()},
        "statement_words": int(unit_df.loc[unit_df["unit"] == "statement", "n_words"].sum()) if stmt else None,
        "hawk_statement": float(unit_df.loc[unit_df["unit"] == "statement", "hawk"].iloc[0]) if stmt else None,
        "hawk_answers_mean": float(n_ans["hawk"].mean()) if len(n_ans) else None,
        "loughran_mcdonald": str(lm.path) if lm else None, "tdw_label_overlap": int(sents["in_tdw_labels"].sum())
        if tdw_keys is not None else None,
    })
    ctx.log.info("text.scored", sentences=len(sents), units=len(unit_df), primary=model_ids[primary])
    return ctx.result
