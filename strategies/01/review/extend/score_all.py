"""Score cached pages, validate against the third-party scores, build the 2011-2026 file."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup

from fedscore import page_date, score_html, slug_date

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
THEIRS = HERE.parents[1] / "data" / "processed"
CUT = pd.Timestamp("2024-10-02")  # their in-sample end (inclusive)
END = pd.Timestamp("2026-10-02")  # last date of our data
COLS = ["slug", "url", "speech_date", "title", "H", "D", "HD", "s", "kept", "chars"]


def score_one(slug: str, fallback_date: str | None) -> dict | None:
    path = RAW / "speeches" / f"{slug}.html"
    if not path.exists():
        return None
    html = path.read_text(encoding="utf-8", errors="replace")
    out = score_html(html)
    out["speech_date"], out["date_rule"] = page_date(html, fallback_date)
    out["slug_date"] = slug_date(slug)
    out["html_chars"] = len(html)
    soup = BeautifulSoup(html, "lxml")
    at = soup.find("p", class_="article__time")
    out["article_time"] = at.get_text(" ", strip=True) if at else ""
    out["has_div_article"] = soup.find("div", id="article") is not None
    out["has_div_content"] = soup.find("div", id="content") is not None
    out["has_pdf_link"] = bool(soup.find("a", href=lambda h: h and h.lower().endswith(".pdf") and "/speech/files/" in h))
    out["n_footnote_links"] = len(soup.find_all("a", href=lambda h: h and h.startswith("#f")))
    return out


def compare(theirs: pd.DataFrame, ours: pd.DataFrame, label: str) -> tuple[dict, pd.DataFrame]:
    m = theirs.merge(ours, on="slug", suffixes=("_their", "_our"))
    s_t, s_o = m["s_their"], m["s_our"]
    both = s_t.notna() & s_o.notna()
    res = {
        "set": label,
        "n_compared": int(len(m)),
        "H_and_D_exact": int(((m.H_their == m.H_our) & (m.D_their == m.D_our)).sum()),
        "kept_agree": int((m.kept_their.astype(bool) == m.kept_our.astype(bool)).sum()),
        "s_nan_pattern_agree": int((s_t.isna() == s_o.isna()).sum()),
        "s_max_abs_diff": float((s_t[both] - s_o[both]).abs().max()) if both.any() else None,
        "s_corr": float(np.corrcoef(s_t[both], s_o[both])[0, 1]) if both.sum() > 2 else None,
        "chars_exact": int((m.chars_their == m.chars_our).sum()),
        "date_agree": int((pd.to_datetime(m.speech_date_their) == pd.to_datetime(m.speech_date_our)).sum()),
        "title_agree": int((m.title_their.fillna("") == m.title_our.fillna("")).sum()) if "title_our" in m else None,
    }
    return res, m


def main() -> None:
    their = pd.read_csv(THEIRS / "speech_scores.csv")
    their["speech_date"] = pd.to_datetime(their["speech_date"])
    their_idx = pd.read_csv(THEIRS / "speech_index.csv")
    idx = pd.read_csv(HERE / "index_2024_2026_raw.csv")
    status = pd.read_csv(HERE / "fetch_status.csv")

    # ---- 1. validation: random 40 of their 2011-2024 speeches
    samp = pd.read_csv(HERE / "validation_sample_slugs.csv")
    vrows = []
    for slug in samp.slug:
        fb = their_idx.loc[their_idx.slug == slug, "html_date"].iloc[0]
        r = score_one(slug, fb)
        if r is None:
            continue
        vrows.append({"slug": slug, **r})
    vo = pd.DataFrame(vrows)
    vo["kept"] = (vo.HD >= 5) & vo.speech_date.notna()
    v_res, v_m = compare(their[COLS], vo, "random40_2011_2024")
    keep_cols = ["slug", "speech_date_their", "speech_date_our", "H_their", "H_our", "D_their", "D_our",
                 "s_their", "s_our", "kept_their", "kept_our", "chars_their", "chars_our", "date_rule"]
    v_m[keep_cols].sort_values("speech_date_their").to_csv(HERE / "validation_random40.csv", index=False)

    # ---- 2. score every 2024-2026 page
    rows = []
    for rec in idx.itertuples(index=False):
        r = score_one(rec.slug, rec.html_date)
        base = {"slug": rec.slug, "url": rec.url, "title": rec.title, "index_year": rec.year,
                "speaker_listed": rec.speaker_listed}
        if r is None:
            rows.append({**base, "fetched": False})
        else:
            rows.append({**base, "fetched": True, **r})
    ours = pd.DataFrame(rows)
    ours["speech_date"] = pd.to_datetime(ours["speech_date"])
    ours["kept"] = (ours.HD >= 5) & ours.speech_date.notna()
    ours.to_csv(HERE / "our_scores_2024_2026_detail.csv", index=False)

    # overlap with their full 2024 set
    o24_res, o24_m = compare(their[their.speech_date.dt.year == 2024][COLS], ours[COLS], "all_their_2024_rows")
    o24_m[["slug", "speech_date_their", "speech_date_our", "H_their", "H_our", "D_their", "D_our", "s_their",
           "s_our", "kept_their", "kept_our", "chars_their", "chars_our"]].to_csv(HERE / "validation_2024_overlap.csv", index=False)

    # ---- 3. combined file: theirs through the cut, ours after it (to END)
    t_part = their[their.speech_date.le(CUT) | their.speech_date.isna()][COLS].copy()
    t_part["source"] = "their_speech_scores_csv"
    o_part = ours[ours.fetched & ours.speech_date.gt(CUT) & ours.speech_date.le(END)][COLS].copy()
    o_part["source"] = "rescored_federalreserve_gov_20261003"
    dup = set(t_part.slug) & set(o_part.slug)
    comb = pd.concat([t_part, o_part[~o_part.slug.isin(dup)]], ignore_index=True)
    comb = comb.sort_values(["speech_date", "slug"]).reset_index(drop=True)
    comb["speech_date"] = comb.speech_date.dt.strftime("%Y-%m-%d")
    comb.to_csv(HERE / "speech_scores_2011_2026.csv", index=False)

    # ---- 4. counts per year
    c = comb.copy()
    c["year"] = pd.to_datetime(c.speech_date).dt.year
    per_year = c.groupby(["year", "source"]).agg(n_docs=("slug", "size"), n_kept=("kept", "sum"),
                                                 mean_s_kept=("s", "mean"), median_HD=("HD", "median"),
                                                 median_chars=("chars", "median")).reset_index()
    per_year.to_csv(HERE / "counts_per_year.csv", index=False)

    # ---- 5. completeness vs the site's own feed, for the post-cut window
    feed = json.loads((RAW / "ne-speeches.json").read_text(encoding="utf-8-sig"))
    fd = pd.DataFrame([x for x in feed if isinstance(x, dict) and "l" in x])
    fd["date"] = pd.to_datetime(fd["d"], format="mixed", errors="coerce")
    n_feed_bad_date = int(fd["date"].isna().sum())
    fd["slug"] = fd["l"].str.split("/").str[-1].str.replace(".htm", "", regex=False)
    win = fd[(fd.date.dt.normalize() > CUT) & (fd.date.dt.normalize() <= END)]
    feed_only = win[~win.slug.isin(o_part.slug)]
    ours_win = o_part.slug
    ours_only = sorted(set(ours_win) - set(win.slug))
    feed_is = fd[(fd.date.dt.year >= 2011) & (fd.date.dt.normalize() <= CUT)]
    feed_only_is = feed_is[~feed_is.slug.isin(their.slug)]
    their_only_is = sorted(set(t_part.slug) - set(feed_is.slug))

    # ---- 6. format diagnostics per year
    ours["year"] = ours.speech_date.dt.year
    fmt = ours[ours.fetched].groupby("year").agg(
        n=("slug", "size"), container_div_content=("container", lambda x: int((x == "div#content").sum())),
        has_div_article=("has_div_article", "sum"), date_rule_text=("date_rule", lambda x: int((x == "text_month_date").sum())),
        date_rule_slug=("date_rule", lambda x: int((x == "slug").sum())),
        date_ne_slug=("speech_date", lambda x: 0), median_html_chars=("html_chars", "median"),
        median_body_chars=("chars", "median"), n_body_lt_3000=("chars", lambda x: int((x < 3000).sum())),
    )
    ne = ours[ours.fetched & (ours.speech_date.dt.strftime("%Y-%m-%d") != ours.slug_date)]
    vrows_rules = vo.date_rule.value_counts().to_dict()

    summary = {
        "validation_random40": v_res,
        "validation_random40_date_rules": vrows_rules,
        "validation_all_2024": o24_res,
        "index_counts": idx.groupby("year").size().to_dict(),
        "fetch_failed": status[~status.ok].to_dict("records"),
        "combined_rows": int(len(comb)),
        "combined_by_source": comb.source.value_counts().to_dict(),
        "post_cut_window": [str(CUT.date() + pd.Timedelta(days=1)), str(END.date())],
        "feed_unparsed_dates": n_feed_bad_date,
        "feed_entries_without_link": fd[fd.l.fillna("") == ""][["d", "t", "s"]].to_dict("records"),
        "feed_post_cut_n": int(len(win)),
        "feed_post_cut_missing_from_ours": feed_only[["d", "t", "s", "l"]].to_dict("records"),
        "ours_post_cut_missing_from_feed": ours_only,
        "feed_2011_to_cut_n": int(len(feed_is)),
        "feed_2011_to_cut_missing_from_theirs": feed_only_is[["d", "t", "s", "l"]].to_dict("records"),
        "theirs_2011_to_cut_missing_from_feed": their_only_is,
        "page_date_ne_slug_date": ne[["slug", "speech_date", "slug_date", "date_rule", "article_time"]].astype(str).to_dict("records"),
        "format_by_year": fmt.reset_index().to_dict("records"),
        "short_bodies": ours[ours.fetched & (ours.chars < 3000)][["slug", "title", "chars", "HD"]].to_dict("records"),
    }
    (HERE / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("validation_random40", "validation_all_2024", "index_counts",
                                              "combined_by_source", "feed_post_cut_n")}, indent=1, default=str))
    print(per_year.to_string())


if __name__ == "__main__":
    main()
