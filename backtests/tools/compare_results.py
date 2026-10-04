"""Compare a re-run's outputs with the committed results (reproduction check; computes nothing new).

    python compare_results.py --ref <committed folder> --new <re-run folder> [--label NAME]

Every CSV, parquet and JSON file under --ref is compared with the file of the same relative path under --new:
  * CSV and parquet: the committed columns only (the committed trade logs had the Databento price levels entry_px/exit_px
    removed, so extra re-run columns are ignored); numbers within rtol 1e-9 / atol 1e-12, NaN equal to NaN;
    everything else as text;
  * JSON: recursively, with the same numeric tolerance; values of keys that hold machine paths are skipped.
Line ends do not matter (files are parsed). Manifest and log files are skipped (their hashes depend on the line-end
convention of the machine that wrote them). Exit status 0 when every compared file agrees, 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RTOL, ATOL = 1e-9, 1e-12
SKIP_FILES = {"manifest_sha256.txt", "input_manifest.json", "run_all_stdout.log",
              "run_meta.json"}  # run_meta holds machine paths and the line-end-dependent manifest
PATH_KEYS = {"text_dir", "out_dir", "doc_scores", "chrono_root", "out", "chrono_doc_scores", "lexonly",
             "fedpress_root", "si_root", "path"}


def num_close(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    fa, fb = float(a), float(b)
    if math.isnan(fa) and math.isnan(fb):
        return True
    return math.isclose(fa, fb, rel_tol=RTOL, abs_tol=ATOL)


def cmp_json(a, b, where: str, out: list) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            if k in PATH_KEYS or (isinstance(k, str) and ("/" in k or "\\" in k)):
                continue
            if k not in b:
                out.append(f"{where}.{k}: missing in re-run")
                continue
            cmp_json(a[k], b[k], f"{where}.{k}", out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{where}: length {len(a)} vs {len(b)}")
            return
        for i, (x, y) in enumerate(zip(a, b)):
            cmp_json(x, y, f"{where}[{i}]", out)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if not num_close(a, b):
            out.append(f"{where}: {a} vs {b}")
    elif a is None and isinstance(b, float) and math.isnan(b) or b is None and isinstance(a, float) and math.isnan(a):
        return
    elif a != b:
        out.append(f"{where}: {str(a)[:80]!r} vs {str(b)[:80]!r}")


def cmp_csv(ref: Path, new: Path, out: list) -> None:
    if ref.suffix == ".parquet":
        a, b = pd.read_parquet(ref).reset_index(drop=True), pd.read_parquet(new).reset_index(drop=True)
    else:
        a, b = pd.read_csv(ref, low_memory=False), pd.read_csv(new, low_memory=False)
    if len(a) != len(b):
        out.append(f"rows {len(a)} vs {len(b)}")
        return
    miss = [c for c in a.columns if c not in b.columns]
    if miss:
        out.append(f"columns missing in re-run: {miss}")
        return
    for c in a.columns:
        x, y = a[c], b[c]
        if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
            xv, yv = x.to_numpy(float), y.to_numpy(float)
            ok = np.isclose(xv, yv, rtol=RTOL, atol=ATOL, equal_nan=True)
            if not ok.all():
                i = int(np.argmax(~ok))
                out.append(f"column {c}: {int((~ok).sum())} rows differ (first row {i}: {xv[i]} vs {yv[i]})")
        else:
            xs, ys = x.astype(str).where(x.notna(), ""), y.astype(str).where(y.notna(), "")
            bad = xs.to_numpy() != ys.to_numpy()
            if bad.any():
                i = int(np.argmax(bad))
                out.append(f"column {c}: {int(bad.sum())} rows differ (first row {i}: {xs.iloc[i]!r} vs {ys.iloc[i]!r})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--skip", nargs="*", default=[], help="relative paths to leave out")
    a = ap.parse_args()
    ref, new = Path(a.ref), Path(a.new)
    n_ok, n_bad, n_missing = 0, 0, 0
    for f in sorted(p for p in ref.rglob("*") if p.is_file()):
        rel = f.relative_to(ref).as_posix()
        if f.name in SKIP_FILES or rel in a.skip or f.suffix not in (".csv", ".json", ".parquet"):
            continue
        g = new / rel
        if not g.exists():
            print(f"  MISSING {rel}")
            n_missing += 1
            continue
        diffs: list = []
        try:
            if f.suffix in (".csv", ".parquet"):
                cmp_csv(f, g, diffs)
            else:
                cmp_json(json.loads(f.read_text(encoding="utf-8")), json.loads(g.read_text(encoding="utf-8")), rel,
                         diffs)
        except Exception as e:  # unreadable file counts as a difference
            diffs.append(f"error: {e}")
        if diffs:
            n_bad += 1
            print(f"  DIFF    {rel}")
            for d in diffs[:5]:
                print(f"            {d}")
        else:
            n_ok += 1
    tag = f"[{a.label}] " if a.label else ""
    print(f"{tag}{n_ok} files agree, {n_bad} differ, {n_missing} missing in the re-run")
    return 0 if n_bad == 0 and n_missing == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
