"""Fetch (cached, polite) the validation sample and every 2024-2026 Board speech page."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

import polite_fetch as pf
from fedindex import parse_year

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
THEIRS = HERE.parents[1] / "data" / "processed"
SEED = 20261003
N_SAMPLE = 40


def main() -> None:
    sc = pd.read_csv(THEIRS / "speech_scores.csv")
    sample = sc.sample(N_SAMPLE, random_state=SEED)[["slug", "url"]]
    sample.to_csv(HERE / "validation_sample_slugs.csv", index=False)

    rows = []
    for y in (2024, 2025, 2026):
        html, st, _ = pf.get(f"https://www.federalreserve.gov/newsevents/speech/{y}-speeches.htm", RAW / "index" / f"{y}.html")
        if html is None:
            raise SystemExit(f"index {y} failed status={st}")
        rows += parse_year(html, y)
    idx = pd.DataFrame(rows).drop_duplicates("slug", keep="last")
    idx.to_csv(HERE / "index_2024_2026_raw.csv", index=False)

    # completeness cross-check against the site's own speech feed (one request)
    feed, st, _ = pf.get("https://www.federalreserve.gov/json/ne-speeches.json", RAW / "ne-speeches.json")
    print("feed status", st, None if feed is None else len(feed))

    todo = list(dict.fromkeys(list(sample["url"]) + list(idx["url"])))
    print(f"pages to fetch: {len(todo)}", flush=True)
    status = []
    for k, url in enumerate(todo, 1):
        slug = url.rstrip("/").split("/")[-1].replace(".htm", "")
        html, st, cached = pf.get(url, RAW / "speeches" / f"{slug}.html")
        status.append({"slug": slug, "url": url, "status": st, "cached": cached, "ok": html is not None})
        if k % 25 == 0:
            print(f"{k}/{len(todo)}", flush=True)
    pd.DataFrame(status).to_csv(HERE / "fetch_status.csv", index=False)
    (HERE / "fetch_log.json").write_text(json.dumps(pf.LOG, indent=1), encoding="utf-8")
    bad = [s for s in status if not s["ok"]]
    print(f"done ok={len(status) - len(bad)} failed={len(bad)} {bad[:10]}")


if __name__ == "__main__":
    main()
