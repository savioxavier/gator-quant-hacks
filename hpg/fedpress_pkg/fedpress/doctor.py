"""`python -m fedpress.cli doctor`: environment checks before a run (prints OK/WARN/FAIL lines, never secrets)."""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

from . import manifest as mf
from .config import HARD_MAX_GPUS, Config
from .gpu import profile, visible_gpus

PACKAGES = ("torch", "torchaudio", "ctranslate2", "faster_whisper", "transformers", "huggingface_hub", "onnxruntime",
            "mediapipe", "emotiefflib", "parselmouth", "speechbrain", "pyannote.audio", "cv2", "pandas", "pyarrow",
            "pdfplumber", "webvtt")


class Report:
    def __init__(self) -> None:
        self.fails = 0

    def line(self, level: str, what: str, detail: str = "") -> None:
        self.fails += level == "FAIL"
        print(f"{level:<4} {what:<34} {detail}")

    def check(self, what: str, fn: Callable[[], str], level_on_error: str = "FAIL") -> None:
        try:
            self.line("OK", what, fn())
        except Exception as e:  # each check is independent
            self.line(level_on_error, what, f"{type(e).__name__}: {e}")


def _version(name: str) -> str:
    mod = importlib.import_module(name)
    return str(getattr(mod, "__version__", "") or getattr(mod, "VERSION", "") or "imported")


def _torch_cuda() -> str:
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError(f"torch {torch.__version__} sees no CUDA device")
    p = torch.cuda.get_device_properties(0)
    arch = f"sm_{p.major}{p.minor}"
    if arch not in torch.cuda.get_arch_list() and f"compute_{p.major}{p.minor}" not in torch.cuda.get_arch_list():
        raise RuntimeError(f"{p.name} is {arch}, torch built for {torch.cuda.get_arch_list()}")
    x = torch.randn(1024, 1024, device="cuda", dtype=torch.float16)
    float((x @ x).sum())
    return f"{p.name} {arch} {p.total_memory / 1e9:.0f} GB, torch {torch.__version__} cuda {torch.version.cuda}"


def _ort_cuda() -> str:
    import numpy as np
    import onnxruntime as ort
    from onnx import TensorProto, helper

    if hasattr(ort, "preload_dlls"):
        ort.preload_dlls()
    if "CUDAExecutionProvider" not in ort.get_available_providers():
        raise RuntimeError(f"onnxruntime {ort.__version__} providers {ort.get_available_providers()} (CPU package installed?)")
    g = helper.make_graph([helper.make_node("MatMul", ["a", "b"], ["c"])], "t",
                          [helper.make_tensor_value_info(n, TensorProto.FLOAT, [64, 64]) for n in "ab"],
                          [helper.make_tensor_value_info("c", TensorProto.FLOAT, [64, 64])])
    model = helper.make_model(g, opset_imports=[helper.make_opsetid("", 13)])
    model.ir_version = 8
    s = ort.InferenceSession(model.SerializeToString(), providers=["CUDAExecutionProvider"])
    a = np.ones((64, 64), np.float32)
    s.run(None, {"a": a, "b": a})
    return f"onnxruntime {ort.__version__} CUDA EP ran a MatMul (first run JIT-compiles PTX on sm_100)"


def _ct2_cuda() -> str:
    import ctranslate2

    n = ctranslate2.get_cuda_device_count()
    if n < 1:
        raise RuntimeError("CTranslate2 sees no CUDA device")
    types = ctranslate2.get_supported_compute_types("cuda")
    return f"ctranslate2 {ctranslate2.__version__}: {n} GPU(s), compute types {sorted(types)}"


def _ct2_whisper(cfg: Config) -> str:
    """Run real CTranslate2 kernels on this GPU: 2 s of noise through the cached Whisper model (the device-count
    check above passes even when the wheel has no kernels for this architecture)."""
    import numpy as np
    from faster_whisper import WhisperModel

    from .models import local_path

    path = local_path(cfg, str(cfg.get("asr.model")))
    model = WhisperModel(str(path), device="cuda", compute_type=str(cfg.get("asr.compute_type", "float16")))
    audio = (np.random.default_rng(0).standard_normal(32000) * 0.01).astype(np.float32)
    segs, info = model.transcribe(audio, language="en", beam_size=1, vad_filter=False)
    list(segs)
    return f"Whisper ({cfg.get('asr.compute_type', 'float16')}) decoded 2 s on the GPU"


def _torchcodec() -> str:
    import torchcodec
    from torchcodec.decoders import AudioDecoder  # noqa: F401  (loads the native core: needs FFmpeg 4-7 and NPP)

    return f"torchcodec {torchcodec.__version__} core loaded"


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg not on PATH (conda env provides it; or `module load ffmpeg`)")
    out = subprocess.run([exe, "-version"], capture_output=True, text=True, timeout=30).stdout.splitlines()[0]
    return out


def _token() -> str:
    if os.environ.get("HF_TOKEN"):
        return "HF_TOKEN set in the environment (value not shown)"
    p = Path(os.environ.get("HF_TOKEN_PATH", Path.home() / ".cache/huggingface/token"))
    if not p.exists():
        raise RuntimeError(f"no token at {p}: gated models (FOMC-RoBERTa, pyannote) will fail; run `hf auth login`")
    mode = p.stat().st_mode & 0o777
    if os.name == "posix" and mode & 0o077:
        raise RuntimeError(f"{p} is readable by others (mode {oct(mode)}); chmod 600 it")
    return f"token file present at {p} (value not shown)"


def _models_cached(cfg: Config) -> str:
    from .models import enabled_keys, local_path

    missing = []
    for k in enabled_keys(cfg):
        spec = cfg.model(k)
        if spec["source"] in ("hf", "url", "manual"):
            years = [int(y) for y in spec.get("revisions", {})] if "id_template" in spec else [None]
            for y in years:  # chrono_bert: one pinned snapshot per pretraining year
                name = k if y is None else f"{k}:{y}"
                try:
                    p = local_path(cfg, k, y)
                    if not p.exists() or (spec["source"] == "manual" and not p.is_file()):
                        missing.append(name)
                except Exception:
                    missing.append(name)
    if missing:
        raise RuntimeError(f"not cached: {missing}; run `prefetch-models` in a dev session")
    return "all enabled models cached"


def run_checks(cfg: Config) -> int:
    r = Report()
    r.line("OK" if sys.version_info >= (3, 11) else "FAIL", "python", sys.version.split()[0])
    r.line("OK", "config", f"{cfg.source} hash {cfg.hash}")
    r.check("data root writable", lambda: (cfg.root.mkdir(parents=True, exist_ok=True), str(cfg.root))[1])
    r.check("manifest", lambda: f"{len(mf.load(cfg))} pressers, sample {len(mf.sample(cfg))}")
    prof = profile(cfg)
    r.line("OK", "gpu profile", f"{prof['name']} ({prof.get('partition')}, {prof['workers_per_gpu']} workers/GPU)")
    gpus = visible_gpus()
    cap = min(int(cfg.get("compute.max_gpus")), HARD_MAX_GPUS)
    r.line("OK" if len(gpus) <= HARD_MAX_GPUS else "WARN", "visible GPUs",
           f"{len(gpus)} visible, at most {cap} used (group limit {HARD_MAX_GPUS})")
    for name in PACKAGES:
        r.check(f"import {name}", lambda n=name: _version(n), "WARN")
    if prof["name"] != "cpu":
        r.check("torch CUDA matmul", _torch_cuda)
        r.check("ctranslate2 CUDA", _ct2_cuda)
        r.check("ctranslate2 Whisper on GPU", lambda: _ct2_whisper(cfg))
        r.check("onnxruntime CUDA EP", _ort_cuda, "WARN")
        r.check("nvidia-smi compute mode", lambda: subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,compute_mode", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=30, check=True).stdout.strip().replace("\n", " | "), "WARN")
    r.check("ffmpeg", _ffmpeg)
    r.check("torchcodec (pyannote, py-feat)", _torchcodec, "WARN")
    r.check("Hugging Face token", _token, "WARN")
    r.line("OK", "HF_HUB_OFFLINE", os.environ.get("HF_HUB_OFFLINE", "0"))
    r.check("model cache", lambda: _models_cached(cfg), "WARN")
    print(f"# {r.fails} failure(s)")
    return 1 if r.fails else 0
