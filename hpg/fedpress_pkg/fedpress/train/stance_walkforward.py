"""Walk-forward stance models (team-plan deviation D1, identical to fedspeak_v2 Amendment 2).

For press conferences in year Y the scorer is ``manelalab/chrono-bert-v1-<min(Y-1, newest)>1231`` (MIT;
pretrained only on text up to that year end), fine-tuned on labelled sentences with year <= Y-1, where year is
the source document's year (deviation D1a re-dating, ``fedpress.train.labels``). Several test
years can share one model: years whose (base checkpoint year, last label year) coincide (e.g. 2025 and 2026:
base 2024, labels end 2022) use the same fine-tunes, named ``b<base>_l<label_end>``.

Fixed settings (``train.stance_walkforward``): 15 % stratified validation split (seed 0) for early stopping on
macro-F1; lr 2e-5, batch 16, max length 256, at most 8 epochs, patience 2, weight decay 0.01 (not on bias and
norm weights), 10 % linear warmup; seeds 42, 43, 44, whose class probabilities the text stage averages.

    python -m fedpress.train.stance_walkforward prepare            # labels (network; CPU job or dev session)
    python -m fedpress.train.stance_walkforward train --all        # every year of the sample (GPU job, offline)
    python -m fedpress.train.stance_walkforward train --years 2016-2018 --gpus 2 --workers-per-gpu 3
    python -m fedpress.train.stance_walkforward status

Outputs: <root>/<out_dir>/<key>/seed<s>/ (model, tokenizer, meta.json) and <root>/<out_dir>/registry.json.
Each job is idempotent (skipped when its meta.json carries the same fingerprint) and claimed with an O_EXCL
file, so any number of workers on at most 2 GPUs can share the queue.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import socket
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .. import manifest as mf
from ..config import Config, ConfigError, apply_env, load
from ..io import atomic_write_json, claim_is_stale, read_json, utc_now
from ..log import Log, setup
from . import labels as lab

ID2LABEL = {0: "dovish", 1: "hawkish", 2: "neutral"}


@dataclass(frozen=True)
class Job:
    key: str                 # b<base_year>_l<label_end>
    base_year: int           # ChronoBERT checkpoint year
    label_end: int           # last label year used (labels with year <= label_end)
    test_years: tuple[int, ...]
    seed: int


# ------------------------------------------------------------------ configuration helpers
def scfg(cfg: Config) -> dict[str, Any]:
    return lab.scfg(cfg)


def out_dir(cfg: Config) -> Path:
    p = Path(str(scfg(cfg).get("out_dir", "models/stance_walkforward")))
    return p if p.is_absolute() else cfg.root / p


def registry_path(cfg: Config) -> Path:
    return out_dir(cfg) / "registry.json"


def base_years(cfg: Config) -> list[int]:
    spec = cfg.model(str(scfg(cfg).get("base", "chrono_bert")))
    return sorted(int(y) for y in (spec.get("revisions") or {}))


def key_for_year(cfg: Config, year: int, label_max_year: int) -> tuple[str, int, int]:
    """(key, base_year, label_end) of the model that scores pressers held in ``year``."""
    years = base_years(cfg)
    if not years:
        raise ConfigError("models.chrono_bert.revisions is empty")
    base = min(year - 1, years[-1])
    if base < years[0]:
        raise ConfigError(f"no ChronoBERT checkpoint for {year} (needs {year - 1}; pinned {years[0]}..{years[-1]})")
    if base not in years:
        raise ConfigError(f"ChronoBERT {base} is not pinned under models.chrono_bert.revisions")
    end = min(year - 1, label_max_year)
    return f"b{base}_l{end}", base, end


def plan(cfg: Config, years: list[int], label_max_year: int) -> list[Job]:
    by_key: dict[str, tuple[int, int, list[int]]] = {}
    for y in sorted(set(years)):
        key, base, end = key_for_year(cfg, y, label_max_year)
        by_key.setdefault(key, (base, end, []))[2].append(y)
    seeds = [int(s) for s in scfg(cfg).get("seeds", [42, 43, 44])]
    return [Job(k, b, e, tuple(ys), s) for k, (b, e, ys) in sorted(by_key.items()) for s in seeds]


def sample_years(cfg: Config) -> list[int]:
    return sorted({m.presser_date.year for m in mf.sample(cfg)})


def _fingerprint(cfg: Config, job: Job, labels_sha: str) -> str:
    s = scfg(cfg)
    spec = cfg.model(str(s.get("base", "chrono_bert")))
    body = {"key": job.key, "seed": job.seed, "base_rev": (spec.get("revisions") or {}).get(str(job.base_year)),
            "labels_sha256": labels_sha, "split": s.get("split"), "hyper": s.get("hyper"),
            "doc_types": s.get("data", {}).get("doc_types"), "dtype": s.get("dtype"), "allow_tf32": s.get("allow_tf32")}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:16]


def seed_dir(cfg: Config, key: str, seed: int) -> Path:
    return out_dir(cfg) / key / f"seed{seed}"


def year_models(cfg: Config, year: int) -> tuple[str, list[Path], list[dict[str, Any]]]:
    """(key, seed model dirs, their meta) for pressers in ``year``; raises FileNotFoundError when incomplete."""
    meta = read_json(lab.meta_path(cfg)) if lab.meta_path(cfg).exists() else None
    if meta is None:
        raise FileNotFoundError(f"{lab.meta_path(cfg)} missing: run `python -m fedpress.train.stance_walkforward "
                                "prepare` and `train` before the text stage")
    key, base, end = key_for_year(cfg, year, int(meta["max_year"]))
    seeds = [int(s) for s in scfg(cfg).get("seeds", [42, 43, 44])]
    dirs, metas = [], []
    for s in seeds:
        d = seed_dir(cfg, key, s)
        m = d / "meta.json"
        if not m.exists() or not (d / "config.json").exists():
            raise FileNotFoundError(f"walk-forward model {key} seed {s} missing ({d}); run "
                                    f"`python -m fedpress.train.stance_walkforward train --years {year}`")
        info = read_json(m)
        want = _fingerprint(cfg, Job(key, base, end, (year,), s), str(meta.get("sha256")))
        if info.get("fingerprint") != want:
            raise RuntimeError(f"{d} was trained with other labels or settings (fingerprint {info.get('fingerprint')} "
                               f"!= {want}); retrain with `train --years {year} --force`")
        dirs.append(d)
        metas.append(info)
    return key, dirs, metas


# ------------------------------------------------------------------ training
def _macro_f1(y: list[int], p: list[int], k: int = 3) -> float:
    f1s = []
    for c in range(k):
        tp = sum(1 for a, b in zip(y, p) if a == c and b == c)
        fp = sum(1 for a, b in zip(y, p) if a != c and b == c)
        fn = sum(1 for a, b in zip(y, p) if a == c and b != c)
        f1s.append(0.0 if tp == 0 else 2 * tp / (2 * tp + fp + fn))
    return sum(f1s) / k


def stratified_split(labels: list[int], frac: float, seed: int) -> tuple[list[int], list[int]]:
    """(train indices, validation indices); ``round(frac * n_c)`` of each class goes to validation."""
    import numpy as np

    rng = np.random.RandomState(seed)
    tr, va = [], []
    arr = np.asarray(labels)
    for c in sorted(set(labels)):
        idx = np.flatnonzero(arr == c)
        idx = idx[rng.permutation(len(idx))]
        n_val = int(round(frac * len(idx)))
        va += idx[:n_val].tolist()
        tr += idx[n_val:].tolist()
    return sorted(tr), sorted(va)


def _evaluate(model: Any, tok: Any, texts: list[str], device: str, max_length: int, batch: int = 64) -> list[int]:
    import torch

    preds: list[int] = []
    model.eval()
    with torch.inference_mode():
        for i in range(0, len(texts), batch):
            enc = tok(texts[i : i + batch], padding=True, truncation=True, max_length=max_length,
                      return_tensors="pt").to(device)
            preds += model(**enc).logits.argmax(-1).cpu().tolist()
    return preds


def train_job(cfg: Config, job: Job, df: Any, labels_meta: dict[str, Any], log: Log, *, max_rows: int | None = None,
              max_epochs: int | None = None) -> dict[str, Any]:
    """Fine-tune one (key, seed); writes model + meta.json into seed_dir. ``max_rows``/``max_epochs`` are for
    smoke tests only (recorded in meta, and such a model is marked ``smoke: true``)."""
    import numpy as np
    import torch
    import transformers
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

    from ..gpu import device as pick_device
    from ..gpu import preload_cuda_libs
    from ..models import local_path

    s = scfg(cfg)
    hp = {"lr": 2e-5, "batch_size": 16, "max_length": 256, "max_epochs": 8, "patience": 2, "weight_decay": 0.01,
          "warmup_frac": 0.10, **(s.get("hyper") or {})}
    if max_epochs:
        hp["max_epochs"] = int(max_epochs)
    split = {"val_frac": 0.15, "seed": 0, **(s.get("split") or {})}
    doc_types = s.get("data", {}).get("doc_types")
    preload_cuda_libs()
    dev = pick_device(str(s.get("device", "cuda")))
    torch.backends.cuda.matmul.allow_tf32 = bool(s.get("allow_tf32", False))
    torch.backends.cudnn.allow_tf32 = bool(s.get("allow_tf32", False))
    dtype = str(s.get("dtype", "float32"))
    random.seed(job.seed)
    np.random.seed(job.seed)
    torch.manual_seed(job.seed)

    rows = df[df["year"] <= job.label_end]
    if doc_types:
        rows = rows[rows["doc_type"].isin(list(doc_types))]
    rows = rows.reset_index(drop=True)
    if max_rows:
        rows = rows.sample(n=min(max_rows, len(rows)), random_state=0).reset_index(drop=True)
    if len(rows) < 30 or rows["label"].nunique() < 3:
        raise ValueError(f"{job.key}: only {len(rows)} labelled rows / {rows['label'].nunique()} classes")
    tr_idx, va_idx = stratified_split(rows["label"].tolist(), float(split["val_frac"]), int(split["seed"]))
    tr, va = rows.iloc[tr_idx], rows.iloc[va_idx]

    base_key = str(s.get("base", "chrono_bert"))
    base_path = local_path(cfg, base_key, job.base_year)
    tok = AutoTokenizer.from_pretrained(str(base_path))
    model = AutoModelForSequenceClassification.from_pretrained(
        str(base_path), num_labels=3, id2label=ID2LABEL, label2id={v: k for k, v in ID2LABEL.items()}).to(dev)
    decay = [p for n, p in model.named_parameters() if not any(x in n.lower() for x in ("bias", "norm"))]
    no_decay = [p for n, p in model.named_parameters() if any(x in n.lower() for x in ("bias", "norm"))]
    opt = torch.optim.AdamW([{"params": decay, "weight_decay": float(hp["weight_decay"])},
                             {"params": no_decay, "weight_decay": 0.0}], lr=float(hp["lr"]))
    bs = int(hp["batch_size"])
    steps_per_epoch = math.ceil(len(tr) / bs)
    total = steps_per_epoch * int(hp["max_epochs"])
    sched = get_linear_schedule_with_warmup(opt, int(round(float(hp["warmup_frac"]) * total)), total)
    gen = torch.Generator().manual_seed(job.seed)
    texts, labels = tr["sentence"].tolist(), tr["label"].tolist()
    autocast = dtype in ("bfloat16", "float16") and dev == "cuda"

    best_f1, best_epoch, best_state, history, bad = -1.0, -1, None, [], 0
    t0 = time.perf_counter()
    for epoch in range(int(hp["max_epochs"])):
        model.train()
        perm = torch.randperm(len(texts), generator=gen).tolist()
        loss_sum = 0.0
        for i in range(0, len(perm), bs):
            idx = perm[i : i + bs]
            enc = tok([texts[j] for j in idx], padding=True, truncation=True, max_length=int(hp["max_length"]),
                      return_tensors="pt").to(dev)
            y = torch.tensor([labels[j] for j in idx], device=dev)
            with torch.autocast(device_type="cuda", dtype=getattr(torch, dtype), enabled=autocast):
                out = model(**enc, labels=y)
            out.loss.backward()
            opt.step()
            sched.step()
            opt.zero_grad(set_to_none=True)
            loss_sum += out.loss.detach().item() * len(idx)
        f1 = _macro_f1(va["label"].tolist(), _evaluate(model, tok, va["sentence"].tolist(), dev, int(hp["max_length"])))
        history.append({"epoch": epoch + 1, "train_loss": loss_sum / len(texts), "val_macro_f1": f1})
        log.info("train.epoch", key=job.key, seed=job.seed, epoch=epoch + 1, val_macro_f1=round(f1, 4))
        if f1 > best_f1:
            best_f1, best_epoch, bad = f1, epoch + 1, 0
            best_state = {k: v.detach().to("cpu", copy=True) for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= int(hp["patience"]):
                break
    assert best_state is not None
    model.load_state_dict(best_state)

    # held-out check on labels of the test years themselves (never used by this model); the accuracy gate
    heldout: dict[str, Any] = {}
    for y in job.test_years:
        h = df[df["year"] == y]
        if len(h):
            pred = _evaluate(model, tok, h["sentence"].tolist(), dev, int(hp["max_length"]))
            pc = h["doc_type"].eq("pc").to_numpy()
            heldout[str(y)] = {"n": int(len(h)), "macro_f1": _macro_f1(h["label"].tolist(), pred),
                               "n_pc": int(pc.sum()),
                               "pc_macro_f1": (_macro_f1(h["label"][pc].tolist(), [p for p, k in zip(pred, pc) if k])
                                               if pc.sum() >= 10 else None)}
    dest = seed_dir(cfg, job.key, job.seed)
    tmp = dest.with_name(dest.name + f".tmp{os.getpid()}")
    model.save_pretrained(str(tmp), safe_serialization=True)
    tok.save_pretrained(str(tmp))
    base_spec = cfg.model(base_key)
    meta = {
        **asdict(job), "complete": True, "smoke": bool(max_rows or max_epochs),
        "fingerprint": _fingerprint(cfg, job, labels_meta["sha256"]), "labels_sha256": labels_meta["sha256"],
        "base_repo": base_spec["id_template"].format(year=job.base_year),
        "base_revision": (base_spec.get("revisions") or {}).get(str(job.base_year)),
        "n_train": len(tr), "n_val": len(va), "train_label_counts": tr["label_name"].value_counts().to_dict(),
        "train_doc_types": tr["doc_type"].value_counts().to_dict(), "train_max_year": int(rows["year"].max()),
        "train_max_source_date": (str(rows["source_date"].dropna().max()) if "source_date" in rows
                                  and rows["source_date"].notna().any() else None),  # D1a: must be < Y-01-01
        "year_basis": labels_meta.get("year_basis", "dataset_year"),
        "hyper": hp, "split": split, "history": history, "best_epoch": best_epoch, "val_macro_f1": best_f1,
        "heldout": heldout, "device": dev, "dtype": dtype, "allow_tf32": bool(s.get("allow_tf32", False)),
        "torch": torch.__version__, "transformers": transformers.__version__, "seconds": time.perf_counter() - t0,
        "host": socket.gethostname(), "created_utc": utc_now(), "id2label": ID2LABEL,
        "license": "base MIT (ChronoBERT); fine-tuned on CC BY-NC 4.0 labels (gtfintechlab) -> non-commercial",
    }
    atomic_write_json(tmp / "meta.json", meta)
    if dest.exists():
        import shutil

        shutil.rmtree(dest)
    tmp.replace(dest)
    del model
    if dev == "cuda":
        torch.cuda.empty_cache()
    return meta


# ------------------------------------------------------------------ queue, workers, registry
def _claim(path: Path, ttl_s: float) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            try:
                held = json.loads(path.read_text(encoding="utf-8") or "{}")
                if claim_is_stale(held, time.time() - path.stat().st_mtime, ttl_s):  # TTL, dead pid, ended job
                    path.unlink(missing_ok=True)
                    continue
            except (OSError, ValueError):
                continue
            return False
        with os.fdopen(fd, "w") as fh:
            fh.write(json.dumps({"host": socket.gethostname(), "pid": os.getpid(), "since": utc_now(),
                                 "job": os.environ.get("SLURM_JOB_ID")}))
        return True
    return False


def job_done(cfg: Config, job: Job, labels_sha: str, smoke: bool = False) -> bool:
    m = seed_dir(cfg, job.key, job.seed) / "meta.json"
    if not m.exists():
        return False
    info = read_json(m)
    return info.get("fingerprint") == _fingerprint(cfg, job, labels_sha) and bool(info.get("smoke")) == smoke


def run_jobs(cfg: Config, jobs: list[Job], log: Log, *, force: bool = False, **smoke: Any) -> int:
    df, meta = lab.load(cfg)
    ttl = float(cfg.get("runtime.claim_ttl_s", 21600))
    is_smoke = any(bool(v) for v in smoke.values())
    failed = 0
    for job in jobs:
        d = seed_dir(cfg, job.key, job.seed)
        if not force and job_done(cfg, job, meta["sha256"], is_smoke):
            continue
        prev = read_json(d / "meta.json") if (d / "meta.json").exists() else None
        if not force and prev is not None and not prev.get("smoke"):
            log.warning("train.stale", key=job.key, seed=job.seed, hint="settings or labels changed; --force to redo")
            continue
        claim = out_dir(cfg) / job.key / f"seed{job.seed}.claim"
        if not _claim(claim, ttl):
            continue
        try:
            info = train_job(cfg, job, df, meta, log, **smoke)
            log.info("train.done", key=job.key, seed=job.seed, val_macro_f1=round(info["val_macro_f1"], 4),
                     seconds=round(info["seconds"], 1))
        except Exception as e:  # one failed fine-tune must not stop the others
            failed += 1
            log.error("train.failed", exc=True, key=job.key, seed=job.seed, error=repr(e))
        finally:
            claim.unlink(missing_ok=True)
    write_registry(cfg)
    return failed


def write_registry(cfg: Config) -> Path:
    """Summary of every finished fine-tune (rebuilt by scanning; the text stage reads seed dirs directly)."""
    root = out_dir(cfg)
    keys: dict[str, Any] = {}
    years: dict[str, str] = {}
    for m in sorted(root.glob("b*_l*/seed*/meta.json")):
        info = read_json(m)
        k = keys.setdefault(info["key"], {"base_year": info["base_year"], "label_end": info["label_end"],
                                          "test_years": info["test_years"], "seeds": {}})
        k["seeds"][str(info["seed"])] = {"val_macro_f1": info["val_macro_f1"], "heldout": info["heldout"],
                                         "fingerprint": info["fingerprint"], "smoke": info.get("smoke", False),
                                         "path": str(m.parent)}
        for y in info["test_years"]:
            years[str(y)] = info["key"]
    if lab.meta_path(cfg).exists():  # every sample year whose model exists (several years can share one key)
        top = int(read_json(lab.meta_path(cfg))["max_year"])
        for y in sample_years(cfg):
            try:
                k = key_for_year(cfg, y, top)[0]
            except ConfigError:
                continue
            if k in keys:
                years[str(y)] = k
    gate = scfg(cfg).get("gate", {}) or {}
    return atomic_write_json(registry_path(cfg), {"updated_utc": utc_now(), "years": dict(sorted(years.items())),
                                                  "keys": keys, "gate": gate})


def _parse_years(text: str) -> list[int]:
    out: list[int] = []
    for part in text.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


def _spawn(cfg: Config, a: argparse.Namespace, log: Log) -> int:
    """Workers on at most min(compute.max_gpus, 2) GPUs share the claim queue (same rule as `cli launch`)."""
    from ..gpu import plan_slots, worker_env

    slots = plan_slots(cfg, gpus=a.gpus, workers_per_gpu=a.workers_per_gpu)
    base = [sys.executable, "-m", "fedpress.train.stance_walkforward", "train", "--worker"]
    base += ["--years", a.years] if a.years else ["--all"]
    base += (["--config", a.config] if a.config else []) + [x for s in a.set for x in ("--set", s)]
    logdir = cfg.root_path("logs") / "train"
    logdir.mkdir(parents=True, exist_ok=True)
    procs = []
    for slot in slots:
        fh = (logdir / f"stance_w{slot.worker:02d}.log").open("w", encoding="utf-8")
        procs.append((subprocess.Popen(base, env=worker_env(slot), stdout=fh, stderr=subprocess.STDOUT), fh))
        time.sleep(0.5)
    codes = [p.wait() for p, _ in procs]
    for _, fh in procs:
        fh.close()
    write_registry(cfg)
    log.info("train.workers_done", exit_codes=codes, workers=len(slots))
    return int(any(codes))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m fedpress.train.stance_walkforward", description=__doc__.split("\n")[0])
    p.add_argument("command", choices=("prepare", "train", "status"))
    p.add_argument("--years", help="test years, e.g. 2016-2026 or 2016,2019 (default with --all: the sample's years)")
    p.add_argument("--all", action="store_true", help="every presser year of the configured sample")
    p.add_argument("--force", action="store_true")
    p.add_argument("--gpus", type=int, help="spawn workers on up to this many GPUs (<= 2)")
    p.add_argument("--workers-per-gpu", type=int)
    p.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--max-rows", type=int, help="smoke test only: subsample the training rows")
    p.add_argument("--max-epochs", type=int, help="smoke test only: fewer epochs")
    p.add_argument("--config")
    p.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    a = p.parse_args(argv)
    try:
        cfg = load(a.config, a.set)
        setup(str(cfg.get("runtime.log_level", "INFO")), str(cfg.get("runtime.log_format", "json")))
        log = Log("train", cfg.root_path("logs") / "train" / "stance_walkforward.jsonl")
        if a.command == "prepare":
            apply_env(cfg, offline=False)
            path = lab.build(cfg, log, force=a.force)
            print(json.dumps(read_json(lab.meta_path(cfg)), indent=2, default=str))
            print(f"# wrote {path}")
            return 0
        apply_env(cfg, offline=a.command == "train" and bool(cfg.get("runtime.offline_gpu", True)))
        _, meta = lab.load(cfg)
        years = _parse_years(a.years) if a.years else sample_years(cfg)
        jobs = plan(cfg, years, int(meta["max_year"]))
        if a.command == "status":
            for j in jobs:
                m = seed_dir(cfg, j.key, j.seed) / "meta.json"
                # stale = a finished non-smoke model trained with other labels/settings: `train` skips it (it never
                # overwrites a finished model without --force) and the text stage refuses it
                state = ("done" if job_done(cfg, j, meta["sha256"]) else
                         "stale" if m.exists() and not read_json(m).get("smoke") else "todo")
                print(f"{j.key:<12} seed {j.seed:<4} years {','.join(map(str, j.test_years)):<16} {state}")
            print(f"# registry {registry_path(cfg)}")
            return 0
        if not (a.years or a.all):
            raise ConfigError("train needs --years or --all")
        if (a.gpus or a.workers_per_gpu) and not a.worker:
            if a.force:  # clear once here; workers never --force or they would redo each other's jobs
                for j in jobs:
                    (seed_dir(cfg, j.key, j.seed) / "meta.json").unlink(missing_ok=True)
            return _spawn(cfg, a, log)
        return int(run_jobs(cfg, jobs, log, force=a.force, max_rows=a.max_rows, max_epochs=a.max_epochs) > 0)
    except (ConfigError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
