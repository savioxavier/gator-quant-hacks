#!/usr/bin/env python3
"""Reuse the recordings downloaded by hpg/fetch_audio.sh inside the feature package's layout.

<root>/video/<id>.mp4  ->  <root>/meetings/<id>/raw/video.mp4   (hard link, falls back to a symlink)

The package's fetch step then finds each video at the expected size and skips the download; it still fetches the
small files (transcript, captions, statement) itself. Stdlib only; safe to re-run.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.environ.get("FEDPRESS_ROOT", f"/blue/ai-workshop/{os.environ.get('USER', '')}/fedpress"))
    root = Path(ap.parse_args().root)
    videos = sorted((root / "video").glob("*.mp4"))
    linked = skipped = 0
    for v in videos:
        dest = root / "meetings" / v.stem / "raw" / "video.mp4"
        if dest.exists() and dest.stat().st_size == v.stat().st_size:
            skipped += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() or dest.is_symlink():
            dest.unlink()
        try:
            os.link(v, dest)
        except OSError:
            os.symlink(v, dest)
        linked += 1
    print(f"videos found {len(videos)}, linked {linked}, already in place {skipped}, root {root}")


if __name__ == "__main__":
    main()
