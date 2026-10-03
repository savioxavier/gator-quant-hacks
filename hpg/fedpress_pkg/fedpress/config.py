"""Load config.yaml: expand ${VAR:-default}, apply --set overrides, validate, fingerprint, set cache env vars."""

from __future__ import annotations

import copy
import getpass
import hashlib
import json
import math
import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

PKG_DIR = Path(__file__).resolve().parent.parent  # folder holding config.yaml, manifest/, env/
HARD_MAX_GPUS = 2  # group rule for jie.xu: never more than 2 GPUs per job or session
ANCHOR_RULES = ("greeting_at_scheduled", "video_zero_at_scheduled", "file")
CLOCK_SOURCES = ("asr", "vtt", "vtt_then_asr")
_MISSING = object()


class ConfigError(ValueError):
    pass


def _env(name: str) -> str | None:
    val = os.environ.get(name)
    if val is None and name == "USER":  # Windows smoke tests have USERNAME instead
        val = getpass.getuser()
    return val


def expand(text: str) -> str:
    """Expand ``${VAR}`` and ``${VAR:-default}`` (defaults may nest); unset ``${VAR}`` becomes ''."""
    out, i = [], 0
    while (start := text.find("${", i)) >= 0:
        out.append(text[i:start])
        depth, j = 1, start + 2
        while j < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            j += 1
        if depth:
            raise ConfigError(f"unbalanced ${{...}} in {text!r}")
        body = text[start + 2 : j - 1]
        name, sep, default = body.partition(":-")
        val = _env(name)
        out.append(val if val not in (None, "") else (expand(default) if sep else ""))
        i = j
    out.append(text[i:])
    return "".join(out)


def _expand_tree(node: Any) -> Any:
    if isinstance(node, str):
        return expand(node)
    if isinstance(node, dict):
        return {k: _expand_tree(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_expand_tree(v) for v in node]
    return node


def _set_dotted(data: dict[str, Any], dotted: str, value: Any) -> None:
    keys = dotted.split(".")
    node = data
    for k in keys[:-1]:
        node = node.setdefault(k, {})
        if not isinstance(node, dict):
            raise ConfigError(f"--set {dotted}: {k} is not a section")
    node[keys[-1]] = value


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))


def _hash(obj: Any) -> str:
    return hashlib.sha256(_canonical(obj).encode()).hexdigest()[:12]


@dataclass(frozen=True)
class Config:
    data: Mapping[str, Any]
    source: Path
    overrides: tuple[str, ...] = field(default=())

    # ---- access
    def get(self, dotted: str, default: Any = _MISSING) -> Any:
        node: Any = self.data
        for k in dotted.split("."):
            if isinstance(node, Mapping) and k in node:
                node = node[k]
            elif default is _MISSING:
                raise ConfigError(f"missing config key: {dotted}")
            else:
                return default
        return node

    def section(self, name: str) -> dict[str, Any]:
        sec = self.get(name, {})
        return dict(sec) if isinstance(sec, Mapping) else {}

    def model(self, key: str) -> dict[str, Any]:
        models = self.section("models")
        if key not in models:
            raise ConfigError(f"unknown model key {key!r}; add it under models:")
        return {"key": key, **models[key]}

    # ---- paths
    @property
    def root(self) -> Path:
        root = str(self.get("paths.root"))
        if not root:
            raise ConfigError("paths.root is empty; set FEDPRESS_ROOT")
        return Path(root).expanduser()

    def root_path(self, key: str) -> Path:
        """A ``paths.<key>`` entry resolved against the data root."""
        p = Path(str(self.get(f"paths.{key}")))
        return p if p.is_absolute() else self.root / p

    def pkg_path(self, value: str | os.PathLike[str]) -> Path:
        """A package-relative path (manifest files): next to the loaded config if present, else in the package."""
        p = Path(value).expanduser()
        if p.is_absolute():
            return p
        near = self.source.parent / p
        return near if near.exists() else PKG_DIR / p

    @property
    def scratch(self) -> Path:
        s = str(self.get("paths.scratch", "") or "")
        return Path(s) / "fedpress" if s else self.root / "tmp"

    # ---- fingerprints
    @property
    def hash(self) -> str:
        return _hash(self.data)

    def models_in(self, node: Any) -> list[str]:
        """Model keys referenced anywhere inside ``node`` (strings equal to a key of ``models``)."""
        keys = set(self.section("models"))
        found: list[str] = []

        def walk(n: Any) -> None:
            if isinstance(n, str) and n in keys and n not in found:
                found.append(n)
                walk(self.section("models")[n].get("needs", []))
            elif isinstance(n, Mapping):
                for v in n.values():
                    walk(v)
            elif isinstance(n, list):
                for v in n:
                    walk(v)

        walk(node)
        return found

    def fingerprint(self, sections: Iterable[str]) -> str:
        """Hash of the named sections plus the specs of every model they reference."""
        secs = {s: self.get(s, None) for s in sections}
        models = {k: self.section("models")[k] for k in self.models_in(secs)}
        return _hash({"sections": secs, "models": models})


def load(path: str | os.PathLike[str] | None = None, overrides: Iterable[str] = ()) -> Config:
    """Read the config (``path``, else $FEDPRESS_CONFIG, else <package>/config.yaml) and validate it."""
    src = Path(path or os.environ.get("FEDPRESS_CONFIG") or PKG_DIR / "config.yaml").expanduser().resolve()
    with src.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    data = copy.deepcopy(raw)
    ovr = tuple(overrides)
    for item in ovr:
        key, sep, val = item.partition("=")
        if not sep:
            raise ConfigError(f"--set expects key=value, got {item!r}")
        _set_dotted(data, key.strip(), yaml.safe_load(val))
    cfg = Config(_expand_tree(data), src, ovr)
    validate(cfg)
    return cfg


def _iso(value: Any, key: str) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as e:
        raise ConfigError(f"{key}: not an ISO date: {value!r}") from e


def validate(cfg: Config) -> None:
    errs: list[str] = []
    max_gpus = cfg.get("compute.max_gpus", HARD_MAX_GPUS)
    if not isinstance(max_gpus, int) or not 1 <= max_gpus <= HARD_MAX_GPUS:
        errs.append(f"compute.max_gpus must be 1..{HARD_MAX_GPUS} (group limit), got {max_gpus!r}")
    gpu_type = cfg.get("compute.gpu_type", None)
    if gpu_type not in cfg.section("compute").get("profiles", {}):
        errs.append(f"compute.gpu_type {gpu_type!r} has no entry under compute.profiles")
    lat = cfg.get("timing.latency_s", None)
    if not isinstance(lat, (int, float)) or math.isnan(lat) or lat < 0:
        errs.append(f"timing.latency_s must be a number >= 0, got {lat!r}")
    if cfg.get("timing.anchor.rule", None) not in ANCHOR_RULES:
        errs.append(f"timing.anchor.rule must be one of {ANCHOR_RULES}")
    if cfg.get("turns.clock_source", "asr") not in CLOCK_SOURCES:
        errs.append(f"turns.clock_source must be one of {CLOCK_SOURCES}")
    for w in ("study_window", "calibration_window"):
        try:
            a, b = _iso(cfg.get(f"sample.{w}.start"), w), _iso(cfg.get(f"sample.{w}.end"), w)
            if a > b:
                errs.append(f"sample.{w}: start after end")
        except ConfigError as e:
            errs.append(str(e))
    if float(cfg.get("face.fps", 1.0)) > float(cfg.get("frames.fps", 1.0)):
        errs.append("face.fps must not exceed frames.fps")
    models = cfg.section("models")
    for key in models:
        if models[key].get("source") not in ("hf", "url", "lib", "manual"):
            errs.append(f"models.{key}.source must be hf|url|lib|manual")
    for stage in ("asr", "turns", "diarize", "voice", "face", "text"):
        sec = cfg.section(stage)
        for k in ("model", "primary"):
            if isinstance(sec.get(k), str) and sec[k] not in models:
                errs.append(f"{stage}.{k} = {sec[k]!r} is not a key under models:")
    if errs:
        raise ConfigError("invalid config:\n  " + "\n  ".join(errs))


def apply_env(cfg: Config, offline: bool = False) -> dict[str, str]:
    """Point every library cache at <root>/cache and keep the HF token outside /blue. Returns what was set.

    The token itself is never read here: huggingface_hub reads $HF_TOKEN or the file at $HF_TOKEN_PATH.
    """
    cache = cfg.root_path("cache")
    wanted = {
        "HF_HOME": cache / "huggingface",
        "TORCH_HOME": cache / "torch",
        "CUDA_CACHE_PATH": cache / "nv",
        "MPLCONFIGDIR": cache / "matplotlib",
        "MODELSCOPE_CACHE": cache / "modelscope",
        "INSIGHTFACE_HOME": cache / "insightface",
    }
    set_now: dict[str, str] = {}
    for k, v in wanted.items():
        if not os.environ.get(k):
            os.environ[k] = set_now[k] = str(v)
    if not os.environ.get("HF_TOKEN_PATH"):  # HF_HOME moved, so pin the token path back to $HOME
        os.environ["HF_TOKEN_PATH"] = set_now["HF_TOKEN_PATH"] = str(Path.home() / ".cache" / "huggingface" / "token")
    os.environ.setdefault("CUDA_CACHE_MAXSIZE", str(4 * 1024**3))  # ORT/CT2 PTX JIT on sm_100 is cached here
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    if offline:
        for k in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE"):
            os.environ[k] = set_now[k] = "1"
    return set_now
