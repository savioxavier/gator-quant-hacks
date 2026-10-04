"""Model registry helpers: which models the enabled config needs, local paths, and the prefetch step.

Downloads happen only in ``python -m fedpress.cli prefetch-models`` (CPU job or dev session). GPU stages run
with HF_HUB_OFFLINE=1 and call :func:`local_path`, which never touches the network in offline mode.
The Hugging Face token is read by huggingface_hub from $HF_TOKEN or $HF_TOKEN_PATH; it is never handled here.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .config import Config
from .io import atomic_write_json, read_json, sha256_file, utc_now

STAGE_SECTIONS = ("asr", "turns", "diarize", "voice", "face", "text")


def _enabled_parts(node: Any) -> Any:
    """Drop every mapping that says enabled: false (and everything below it)."""
    if isinstance(node, Mapping):
        if node.get("enabled", True) is False:
            return None
        return {k: _enabled_parts(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_enabled_parts(v) for v in node]
    return node


def _unselected_alternatives(cfg: Config) -> set[str]:
    """Sub-sections that exist only for a non-default choice (e.g. turns.align.whisperx_align_model)."""
    drop: set[str] = set()
    if cfg.get("turns.align.method", "text_match") != "whisperx":
        drop.add(str(cfg.get("turns.align.whisperx_align_model", "")))
    if cfg.get("turns.align.method", "text_match") != "qwen_forced_aligner":
        drop.add(str(cfg.get("turns.align.qwen_aligner_model", "")))
    if cfg.get("diarize.method", "ecapa_verify") != "ecapa_verify":
        drop.add(str(cfg.get("diarize.ecapa.model", "")))
    return drop


def enabled_keys(cfg: Config) -> list[str]:
    """Model keys referenced by enabled stages and enabled sub-options."""
    tree = {s: _enabled_parts(cfg.section(s)) for s in STAGE_SECTIONS}
    drop = _unselected_alternatives(cfg)
    return [k for k in cfg.models_in(tree) if k not in drop]


def lock_path(cfg: Config) -> Path:
    return cfg.root_path("cache") / "models_lock.json"


def _lock(cfg: Config) -> dict[str, Any]:
    p = lock_path(cfg)
    return read_json(p) if p.exists() else {}


def local_path(cfg: Config, key: str, year: int | None = None) -> Path:
    """Local directory (hf) or file (url/manual) of a model; offline-safe once prefetched."""
    spec = cfg.model(key)
    src = spec["source"]
    if src == "hf":
        from huggingface_hub import snapshot_download

        repo = spec["id"] if "id" in spec else spec["id_template"].format(year=year)
        rev = spec.get("revision") or (spec.get("revisions") or {}).get(str(year))
        offline = os.environ.get("HF_HUB_OFFLINE") == "1"
        # ignore_patterns: duplicate weight formats / trainer state the loaders never read (saves GBs on /blue)
        return Path(snapshot_download(repo_id=repo, revision=rev, local_files_only=offline,
                                      ignore_patterns=spec.get("ignore_patterns") or None))
    if src == "url":
        return cfg.root_path("cache") / "models" / key / Path(spec["url"]).name
    if src == "manual":
        return Path(str(cfg.get(spec["path_key"], "") or ""))
    raise ValueError(f"model {key}: source 'lib' is downloaded by its library; no local path")


def _download(url: str, dest: Path, timeout: float = 120.0) -> None:
    import requests

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with tmp.open("wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
    os.replace(tmp, dest)


def prefetch(cfg: Config, keys: list[str] | None = None, years: list[int] | None = None) -> dict[str, Any]:
    """Download the given (default: enabled) models into <root>/cache and record what was fetched."""
    os.environ.pop("HF_HUB_OFFLINE", None)
    os.environ.pop("TRANSFORMERS_OFFLINE", None)
    lock = _lock(cfg)
    report: dict[str, Any] = {}
    for key in keys or enabled_keys(cfg):
        spec = cfg.model(key)
        try:
            if spec["source"] == "hf":
                todo = [None] if "id" in spec else list(years or [int(y) for y in spec.get("revisions", {})])
                for y in todo:
                    path = local_path(cfg, key, y)
                    name = key if y is None else f"{key}:{y}"
                    lock[name] = {"source": "hf", "repo": spec.get("id") or spec["id_template"].format(year=y),
                                  "requested": spec.get("revision") or (spec.get("revisions") or {}).get(str(y)),
                                  "resolved": path.name, "path": str(path), "license": spec.get("license"),
                                  "fetched_utc": utc_now()}
                    report[name] = "ok"
            elif spec["source"] == "url":
                dest = local_path(cfg, key)
                if not dest.exists():
                    _download(spec["url"], dest)
                digest = sha256_file(dest)
                if spec.get("sha256") and spec["sha256"] != digest:
                    raise ValueError(f"sha256 mismatch for {key}: {digest} != {spec['sha256']}")
                lock[key] = {"source": "url", "url": spec["url"], "sha256": digest, "path": str(dest),
                             "license": spec.get("license"), "fetched_utc": utc_now()}
                report[key] = "ok"
            elif spec["source"] == "manual":
                p = local_path(cfg, key)
                report[key] = "ok" if p.is_file() else f"missing: set {spec['path_key']} (see {spec.get('url')})"
            else:
                report[key] = f"library download ({spec.get('package')}); run the stage once in a dev session"
        except Exception as e:  # report and continue: one gated model must not stop the others
            report[key] = f"error: {e!r}"
    atomic_write_json(lock_path(cfg), lock)
    return report
