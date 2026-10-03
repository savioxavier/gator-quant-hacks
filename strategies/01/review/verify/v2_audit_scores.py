"""V2: audit of the extended speech corpus: own scorer on raw HTML, duplicates, speakers, dates vs the
site's own feed (date and time of day), completeness. Writes out/v2_*.csv and out/v2_audit.json."""
import json
import re
from collections import Counter

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup

import vlib as V

OUT = V.HERE / "out"
OUT.mkdir(exist_ok=True)
res = {}

# ------------------------------------------------------------ own scorer (from the published spec)
HAWK = set(w.strip().lower() for w in (V.THEIR / "lexicon" / "hawk.txt").read_text(encoding="utf-8").split() if w.strip())
DOVE = set(w.strip().lower() for w in (V.THEIR / "lexicon" / "dove.txt").read_text(encoding="utf-8").split() if w.strip())
NEG = {"not", "no", "never", "neither", "nor", "without", "cannot", "dont", "doesnt", "didnt", "wont", "isnt", "wasnt"}
HEDGE = {"unlikely", "less", "little"}
STOP = {",", ";", ".", "but", "however", "although"}
TOK = re.compile(r"[a-z]+|[,.;]", re.I)


def toks(text):
    t = text.lower().replace("'", "")
    for ch in ("—", "–", "-"):
        t = t.replace(ch, " ")
    t = t.replace("n't", "nt")
    return [m.group(0).lower() for m in TOK.finditer(t)]


def score(tokens):
    h = d = 0
    left = 0
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in STOP:
            left = 0
        elif t == "no" and i + 1 < len(tokens) and tokens[i + 1] == "longer":
            left = 5
            i += 2
            continue
        elif t in NEG or t in HEDGE:
            left = 5
        else:
            hawk, dove = t in HAWK, t in DOVE
            neg = left > 0
            if hawk:
                d, h = (d + 1, h) if neg else (d, h + 1)
            if dove:
                h, d = (h + 1, d) if neg else (h, d + 1)
            if left > 0:
                left -= 1
        i += 1
    return h, d


def body(html):
    soup = BeautifulSoup(html, "lxml")
    for tg in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tg.decompose()
    m = (soup.find("div", id="content") or soup.find("div", class_="col-xs-12 col-sm-8 col-md-8")
         or soup.find("article") or soup.find("div", id="article") or soup.body)
    if m is None:
        return ""
    for c in ("share", "breadcrumb", "related", "social"):
        for n in m.find_all(class_=re.compile(c, re.I)):
            n.decompose()
    return m.get_text(" ", strip=True)


comb = pd.read_csv(V.EXT / "speech_scores_2011_2026.csv", parse_dates=["speech_date"])
theirs = pd.read_csv(V.TP / "speech_scores.csv", parse_dates=["speech_date"])
res["combined_rows"] = len(comb)
res["combined_by_source"] = comb["source"].value_counts().to_dict()

# 1. in-sample part equals their file
ins = comb[comb["source"] == "their_speech_scores_csv"].set_index("slug")
th = theirs.set_index("slug")
th_is = th[th["speech_date"] <= V.IS_END]
res["insample_rows_equal_their_rows_le_cut"] = {
    "n_comb": len(ins), "n_theirs_le_cut": len(th_is), "same_slugs": set(ins.index) == set(th_is.index),
    "max_abs_s_diff": float((ins["s"] - th_is["s"].reindex(ins.index)).abs().max()),
    "kept_equal": bool((ins["kept"].astype(str) == th_is["kept"].reindex(ins.index).astype(str)).all()),
    "date_equal": bool((ins["speech_date"] == th_is["speech_date"].reindex(ins.index)).all())}
res["their_rows_after_cut_not_in_comb_as_theirs"] = int((th["speech_date"] > V.IS_END).sum())

# 2. rescore every post-cut row (and their 2024 overlap rows) from raw HTML with my scorer
raw = V.EXT / "raw" / "speeches"
rows = []
for slug in sorted(p.stem for p in raw.glob("*.html")):
    txt = (raw / f"{slug}.html").read_text(encoding="utf-8", errors="replace")
    b = body(txt)
    h, d = score(toks(b))
    rows.append({"slug": slug, "H_v": h, "D_v": d, "chars_v": len(b), "kept_v": h + d >= 5,
                 "s_v": (h - d) / (h + d + 1) if h + d >= 5 else np.nan})
rv = pd.DataFrame(rows).set_index("slug")
post = comb[comb["source"] != "their_speech_scores_csv"].set_index("slug")
j = post.join(rv, how="left")
res["rescore_post_cut"] = {"n_rows": len(j), "n_with_raw": int(j["H_v"].notna().sum()),
                           "H_exact": int((j["H"] == j["H_v"]).sum()), "D_exact": int((j["D"] == j["D_v"]).sum()),
                           "chars_exact": int((j["chars"] == j["chars_v"]).sum()),
                           "kept_agree": int((j["kept"].astype(str).str.lower() == j["kept_v"].astype(str).str.lower()).sum()),
                           "max_abs_s_diff": float((j["s"] - j["s_v"]).abs().max())}
j[["H", "H_v", "D", "D_v", "chars", "chars_v", "kept", "kept_v"]].to_csv(OUT / "v2_rescore_post_cut.csv")
jt = th.join(rv, how="inner")
res["rescore_their_rows_with_raw"] = {"n": len(jt), "H_exact": int((jt["H"] == jt["H_v"]).sum()),
                                      "D_exact": int((jt["D"] == jt["D_v"]).sum()), "chars_exact": int((jt["chars"] == jt["chars_v"]).sum())}

# 3. duplicates
comb["speaker"] = comb["slug"].str.extract(r"^([a-z]+)\d{8}")[0]
comb["slugdate"] = pd.to_datetime(comb["slug"].str.extract(r"(\d{8})")[0], format="%Y%m%d")
res["dup_slug"] = int(comb["slug"].duplicated().sum())
res["dup_url"] = int(comb["url"].duplicated().sum())
d2 = comb[comb.duplicated(["speaker", "speech_date", "title"], keep=False)]
res["dup_speaker_date_title"] = d2[["slug", "title"]].values.tolist()
kc = comb[comb["kept"].astype(str).str.lower() == "true"]
d3 = kc[kc.duplicated(["H", "D", "chars"], keep=False)]
res["dup_kept_same_H_D_chars"] = d3[["slug", "H", "D", "chars"]].values.tolist()
d4 = comb[comb.duplicated(["speaker", "title"], keep=False) & comb["title"].notna()].sort_values(["speaker", "title"])
res["same_speaker_same_title_pairs"] = d4[["slug", "title", "kept", "s"]].values.tolist()

# 4. speakers after the cut
pc = comb[comb["speech_date"] > V.IS_END]
res["post_cut_speakers"] = {str(y): dict(Counter(g["speaker"])) for y, g in pc.groupby(pc["speech_date"].dt.year)}
det = pd.read_csv(V.EXT / "our_scores_2024_2026_detail.csv")
res["post_cut_speaker_titles"] = sorted(set(det.loc[det["slug"].isin(pc["slug"]), "speaker_listed"].astype(str)))
res["date_ne_slugdate"] = comb.loc[comb["speech_date"] != comb["slugdate"], ["slug", "speech_date", "kept"]].astype(str).values.tolist()

# 5. feed: dates and times
feed = pd.DataFrame(json.loads((V.EXT / "raw" / "ne-speeches.json").read_text(encoding="utf-8-sig")))
feed = feed[feed["d"].astype(str).str.len() > 0].copy()
feed["dt"] = pd.to_datetime(feed["d"], format="mixed")
feed["has_time"] = feed["d"].astype(str).str.contains(":")
feed["slug"] = feed["l"].astype(str).str.extract(r"/([a-z]+\d{8}[a-z]?)\.htm")[0]
fz = feed.dropna(subset=["slug"]).drop_duplicates("slug").set_index("slug")
m = comb.set_index("slug").join(fz[["dt", "s", "t"]].rename(columns={"s": "feed_speaker", "t": "feed_title"}), how="left")
m["feed_date"] = m["dt"].dt.normalize()
m["lag_days"] = (m["feed_date"] - m["speech_date"]).dt.days
kept = m["kept"].astype(str).str.lower() == "true"
res["feed_match"] = {"rows": len(m), "matched": int(m["dt"].notna().sum()), "kept_matched": int((kept & m["dt"].notna()).sum()),
                     "kept_unmatched": m.index[kept & m["dt"].isna()].tolist()}
res["feed_lag_days_counts_all"] = {str(k): int(v) for k, v in m["lag_days"].value_counts().sort_index().items()}
res["feed_lag_days_counts_kept"] = {str(k): int(v) for k, v in m.loc[kept, "lag_days"].value_counts().sort_index().items()}
late = m[(m["lag_days"] > 0)]
res["speech_date_before_feed_date"] = late[["speech_date", "dt", "kept", "s"]].astype(str).reset_index().values.tolist()
early = m[(m["lag_days"] < 0)]
res["speech_date_after_feed_date"] = early[["speech_date", "dt", "kept"]].astype(str).reset_index().values.tolist()
# time-of-day of kept speeches and usable lag in hours (usable = next session open 09:30)
cal = V.our_opens()[0].index
u = V.usable_index(cal, m["speech_date"])
ok = u < len(cal)
m["usable"] = pd.NaT
m.loc[ok, "usable"] = cal[u[ok]]
m["hours_to_use"] = ((m["usable"] + pd.Timedelta(hours=9, minutes=30)) - m["dt"]).dt.total_seconds() / 3600
res["kept_hours_from_feed_time_to_use_open"] = {"min": float(m.loc[kept, "hours_to_use"].min()),
                                                "n_lt_12h": int((m.loc[kept, "hours_to_use"] < 12).sum()),
                                                "n_le_0": int((m.loc[kept, "hours_to_use"] <= 0).sum())}
m["has_time"] = m.index.map(fz["has_time"])
res["kept_without_feed_time"] = int((kept & (m["has_time"] != True)).sum())
res["kept_feed_hour_hist"] = {str(k): int(v) for k, v in m.loc[kept, "dt"].dt.hour.value_counts().sort_index().items()}
res["kept_weekend_or_holiday_speech_date"] = int((kept & ~m["speech_date"].isin(cal)).sum())
m.reset_index()[["slug", "speech_date", "dt", "lag_days", "usable", "hours_to_use", "kept", "s", "feed_speaker"]].to_csv(OUT / "v2_feed_join.csv", index=False)

# 6. completeness vs feed per year (feed entries with a page link that are not in the corpus)
fz2 = fz[(fz["dt"] >= "2011-01-01") & (fz["dt"] <= "2026-10-02 23:59")]
missing = fz2[~fz2.index.isin(comb["slug"])]
res["feed_entries_missing_from_corpus"] = missing[["dt", "s", "t"]].astype(str).reset_index().values.tolist()
extra = comb[~comb["slug"].isin(fz.index)]
res["corpus_rows_not_in_feed"] = extra[["slug", "speech_date", "kept"]].astype(str).values.tolist()
res["feed_speaker_titles_post_cut"] = dict(Counter(fz2.loc[fz2["dt"] > V.IS_END, "s"]))
# feed speakers in full corpus period that are not Board members (presidents would say 'President')
res["feed_nonboard_like"] = sorted({s for s in fz2["s"] if not re.search(r"Governor|Chair", str(s))})

print(json.dumps(res, indent=1, default=str))
(OUT / "v2_audit.json").write_text(json.dumps(res, indent=1, default=str))
