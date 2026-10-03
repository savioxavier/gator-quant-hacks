"""Novelty vectors: hashed term frequencies (no fitted vocabulary, so nothing is learned from later meetings)
and optional sentence embeddings (Qwen3-Embedding or any sentence-transformers model in the registry).

Novelty = 1 - cosine similarity. Within a meeting the text stage compares each unit with the same day's
statement; the dataset build compares a meeting with the previous presser (both earlier in time).
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from .lexicon import words

HASH_DIM = 1 << 20
# Function words carry no topical content; this short list is fixed so vectors stay comparable across runs.
STOPWORDS = frozenset("""
a about above after again against all am an and any are as at be because been before being below between both but
by can could did do does doing down during each few for from further had has have having he her here hers herself
him himself his how i if in into is it its itself just me more most my myself no nor not now of off on once only or
other our ours ourselves out over own same she should so some such than that the their theirs them themselves then
there these they this those through to too under until up very was we were what when where which while who whom why
will with would you your yours yourself yourselves i'm i've i'd i'll we're we've we'd we'll you're it's that's
there's don't doesn't didn't won't wouldn't can't couldn't isn't aren't wasn't weren't haven't hasn't let's also
well so yes okay ok mean really just thing things think know going get got say said
""".split())


def _bucket(token: str) -> int:
    return int.from_bytes(hashlib.blake2b(token.encode(), digest_size=8).digest(), "little") % HASH_DIM


def hashed_tf(text: str) -> dict[int, float]:
    """Term counts of content words (stopwords removed), hashed into HASH_DIM buckets."""
    return dict(Counter(_bucket(t) for t in words(text) if t not in STOPWORDS and len(t) > 1))


def pool(vectors: Iterable[Mapping[int, float]]) -> dict[int, float]:
    out: Counter[int] = Counter()
    for v in vectors:
        out.update(v)
    return dict(out)


def cosine(a: Mapping[int, float], b: Mapping[int, float]) -> float:
    if not a or not b:
        return float("nan")
    small, big = (a, b) if len(a) <= len(b) else (b, a)
    dot = sum(v * big.get(k, 0.0) for k, v in small.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else float("nan")


def novelty(a: Mapping[int, float], b: Mapping[int, float]) -> float:
    c = cosine(a, b)
    return float("nan") if math.isnan(c) else 1.0 - c


def to_lists(v: Mapping[int, float]) -> tuple[list[int], list[float]]:
    keys = sorted(v)
    return keys, [float(v[k]) for k in keys]


def from_lists(idx: Sequence[int] | None, val: Sequence[float] | None) -> dict[int, float]:
    if idx is None or val is None:
        return {}
    return {int(i): float(x) for i, x in zip(idx, val)}


# ------------------------------------------------------------------ dense embeddings (option)
def dense_cosine(a: Sequence[float] | None, b: Sequence[float] | None) -> float:
    if a is None or b is None or len(a) == 0 or len(b) == 0:
        return float("nan")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else float("nan")


def dense_mean(rows: Iterable[Sequence[float] | None]) -> list[float] | None:
    rows = [r for r in rows if r is not None and len(r)]
    if not rows:
        return None
    n = len(rows)
    return [sum(col) / n for col in zip(*rows)]


def encode(model_dir: Path, texts: Sequence[str], *, device: str, batch_size: int, max_seq_length: int | None,
           dtype: str = "float32") -> tuple[list[list[float]], dict[str, Any]]:
    """L2-normalised document embeddings with sentence-transformers (no query prompt: documents vs documents)."""
    import torch
    from sentence_transformers import SentenceTransformer

    kwargs: dict[str, Any] = {}
    if dtype != "float32":
        kwargs["model_kwargs"] = {"torch_dtype": getattr(torch, dtype)}
    model = SentenceTransformer(str(model_dir), device=device, **kwargs)
    if max_seq_length:
        model.max_seq_length = int(max_seq_length)
    emb = model.encode(list(texts), batch_size=batch_size, normalize_embeddings=True, convert_to_numpy=True,
                       show_progress_bar=False)
    info = {"dim": int(emb.shape[1]) if len(emb) else None, "max_seq_length": model.max_seq_length, "dtype": dtype}
    del model
    if device == "cuda":
        torch.cuda.empty_cache()
    return [list(map(float, r)) for r in emb], info
