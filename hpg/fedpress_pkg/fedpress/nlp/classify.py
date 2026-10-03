"""Sentence classification with Hugging Face sequence classifiers (one model, or an ensemble of seeds whose
class probabilities are averaged, as the walk-forward stance models require).

Label names come from each model's ``config.id2label`` (lower-cased). Generic names (``LABEL_0`` ...) are
mapped with the registry's ``label_map_fallback``. All ensemble members must agree on the label order.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class Predictions:
    labels: list[str]                  # class names, column order of ``probs``
    probs: np.ndarray                  # (n, k) float64, rows sum to 1
    n_tokens: np.ndarray               # (n,) tokens before truncation (special tokens included)
    truncated: np.ndarray              # (n,) bool: longer than max_length
    info: dict[str, Any] = field(default_factory=dict)

    def column(self, name: str) -> np.ndarray:
        return self.probs[:, self.labels.index(name)] if name in self.labels else np.full(len(self.probs), np.nan)

    def argmax_labels(self) -> list[str]:
        return [self.labels[i] for i in self.probs.argmax(axis=1)] if len(self.probs) else []


def resolve_labels(id2label: Mapping[Any, str], fallback: Mapping[Any, str] | None) -> list[str]:
    """Class names in index order; generic LABEL_i names are replaced by ``fallback[i]``."""
    k = len(id2label)
    names = [str(id2label.get(i, id2label.get(str(i), f"LABEL_{i}"))).strip().lower() for i in range(k)]
    if all(n.startswith("label_") for n in names):
        if not fallback:
            raise ValueError(f"model has generic labels {names} and no label_map_fallback in the registry")
        names = [str(fallback.get(i, fallback.get(str(i)))).strip().lower() for i in range(k)]
    return names


def predict(model_dirs: Sequence[Path], texts: Sequence[str], *, device: str, batch_size: int, max_length: int,
            dtype: str = "float32", label_map_fallback: Mapping[Any, str] | None = None) -> Predictions:
    """Class probabilities for ``texts``; with several ``model_dirs`` the probabilities are averaged."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    if not model_dirs:
        raise ValueError("no model directories given")
    tok = AutoTokenizer.from_pretrained(str(model_dirs[0]))
    lengths = np.array([len(x) for x in tok(list(texts), add_special_tokens=True, truncation=False)["input_ids"]],
                       dtype=np.int64) if texts else np.zeros(0, dtype=np.int64)
    order = np.argsort(-lengths, kind="stable")   # long first: fewer pad tokens per batch
    total: np.ndarray | None = None
    labels: list[str] | None = None
    autocast = dtype in ("bfloat16", "float16") and device == "cuda"
    for d in model_dirs:
        model = AutoModelForSequenceClassification.from_pretrained(str(d)).to(device).eval()
        names = resolve_labels(model.config.id2label, label_map_fallback)
        if labels is None:
            labels = names
        elif names != labels:
            raise ValueError(f"ensemble label order differs: {d} has {names}, expected {labels}")
        probs = np.zeros((len(texts), len(names)), dtype=np.float64)
        with torch.inference_mode():
            for i in range(0, len(order), batch_size):
                idx = order[i : i + batch_size]
                enc = tok([texts[j] for j in idx], padding=True, truncation=True, max_length=max_length,
                          return_tensors="pt").to(device)
                with torch.autocast(device_type="cuda", dtype=getattr(torch, dtype), enabled=autocast):
                    logits = model(**enc).logits
                probs[idx] = torch.softmax(logits.float(), dim=-1).cpu().numpy()
        total = probs if total is None else total + probs
        del model
        if device == "cuda":
            torch.cuda.empty_cache()
    assert total is not None and labels is not None
    info = {"n_models": len(model_dirs), "device": device, "dtype": dtype, "max_length": max_length,
            "tokenizer": type(tok).__name__}
    return Predictions(labels, total / len(model_dirs), lengths, lengths > max_length, info)
