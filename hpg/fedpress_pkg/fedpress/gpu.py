"""GPU profile, the 2-GPU cap, worker slots, device choice and CUDA library preloading."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

from .config import HARD_MAX_GPUS, Config


@dataclass(frozen=True)
class Slot:
    worker: int        # 0..n-1 across the job
    gpu: str | None    # physical GPU index/UUID exported as CUDA_VISIBLE_DEVICES, None = CPU worker
    threads: int


def profile(cfg: Config) -> dict[str, Any]:
    name = str(cfg.get("compute.gpu_type"))
    return {"name": name, **cfg.section("compute")["profiles"][name]}


def visible_gpus() -> list[str]:
    """GPUs this process may use: $CUDA_VISIBLE_DEVICES (set by Slurm) or nvidia-smi."""
    env = os.environ.get("CUDA_VISIBLE_DEVICES")
    if env is not None:
        return [g for g in env.split(",") if g.strip() and g.strip() != "-1"]
    if shutil.which("nvidia-smi") is None:
        return []
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=index", "--format=csv,noheader"],
                             capture_output=True, text=True, timeout=30, check=True).stdout
    except (subprocess.SubprocessError, OSError):
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def plan_slots(cfg: Config, gpus: int | None = None, workers_per_gpu: int | None = None) -> list[Slot]:
    """Worker slots for one job: at most min(compute.max_gpus, 2, visible) GPUs, workers_per_gpu each."""
    prof = profile(cfg)
    wpg = int(workers_per_gpu or cfg.get("compute.workers_per_gpu", None) or prof["workers_per_gpu"])
    if prof["name"] == "cpu":  # threads per worker from the job's cores (fetch: 4 cores, 4 workers -> 1 each)
        n = max(1, wpg)
        cpus = int(os.environ.get("SLURM_CPUS_PER_TASK") or prof["cpus_per_gpu"])
        return [Slot(k, None, max(1, cpus // n)) for k in range(n)]
    cap = min(int(cfg.get("compute.max_gpus")), HARD_MAX_GPUS)
    avail = visible_gpus()
    use = avail[: min(cap, gpus or cap)]
    if not use:
        raise RuntimeError("no GPU visible (CUDA_VISIBLE_DEVICES / nvidia-smi); use --set compute.gpu_type=cpu")
    cpus = int(os.environ.get("SLURM_CPUS_PER_TASK") or prof["cpus_per_gpu"] * len(use))
    per = int(cfg.get("compute.cpus_per_worker", None) or max(1, cpus // (wpg * len(use))))
    return [Slot(k * len(use) + i, g, per) for k in range(wpg) for i, g in enumerate(use)]


def worker_env(slot: Slot) -> dict[str, str]:
    env = dict(os.environ)
    env["CUDA_VISIBLE_DEVICES"] = slot.gpu if slot.gpu is not None else ""
    for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        env[k] = str(slot.threads)
    env["FEDPRESS_WORKER"] = str(slot.worker)
    env["TOKENIZERS_PARALLELISM"] = "false"
    return env


def preload_cuda_libs() -> None:
    """Import torch first so its pip CUDA/cuDNN libraries are loaded, then let onnxruntime find them.
    CTranslate2 (faster-whisper) and onnxruntime-gpu resolve libcublas/libcudnn from the loaded process."""
    try:
        import torch  # noqa: F401
    except ImportError:
        return
    try:
        import onnxruntime as ort

        if hasattr(ort, "preload_dlls"):
            ort.preload_dlls()
    except ImportError:
        pass


def device(requested: str = "cuda") -> str:
    """'cuda' when requested and usable, else 'cpu'."""
    if requested != "cuda":
        return "cpu"
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


def info() -> dict[str, Any]:
    """Name, compute capability and memory of the current device (for done-markers and doctor)."""
    try:
        import torch

        if torch.cuda.is_available():
            i = torch.cuda.current_device()
            p = torch.cuda.get_device_properties(i)
            return {"gpu": p.name, "cc": f"{p.major}.{p.minor}", "vram_gb": round(p.total_memory / 1e9, 1),
                    "torch": torch.__version__, "cuda": torch.version.cuda,
                    "arch_list": torch.cuda.get_arch_list()}
        return {"gpu": None, "torch": torch.__version__}
    except ImportError:
        return {"gpu": None, "torch": None}
