"""Count press-conference speaker turns per transcript (public-domain Fed PDFs converted with pdftotext).
Speaker labels are all-caps names of 2-4 tokens followed by '.' or ':' (e.g. 'CHAIR POWELL.', 'MICHELLE SMITH.'),
which can appear mid-line in some years, so the whole text is split on that pattern."""
import re, glob, os, csv, collections
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
hdr = re.compile(r"Page \d+ of \d+|[A-Z][a-z]+ \d{1,2}, \d{4}\s+(?:Chair(?:man)?|Vice Chair) \w+'s Press Conference\s+FINAL")
lab = re.compile(r"(?<![A-Za-z'])((?:[A-Z][A-Z'\-]+ ){1,3}[A-Z][A-Z'\-]+)[\.:](?=\s)")
rows = []
for path in sorted(glob.glob(os.path.join(base, "pdf", "FOMCpresconf*.txt"))):
    d = re.search(r"(\d{8})", path).group(1)
    txt = open(path, encoding="utf-8", errors="replace").read()
    txt = hdr.sub(" ", txt)
    txt = re.sub(r"\s+", " ", txt)
    # cut the title line
    i = txt.find("Press Conference", txt.find("Transcript of") if "Transcript of" in txt else 0)
    parts = lab.split(txt)
    turns = []
    for k in range(1, len(parts) - 1, 2):
        turns.append((re.sub(r"^(FINAL )+", "", parts[k]), parts[k + 1]))
    chair_name = next((s for s, _ in turns if s.startswith(("CHAIRMAN ", "CHAIR "))), "")
    chair_turns = [t for t in turns if t[0] == chair_name]
    w = lambda s: len(s.split())
    opening = chair_turns[0][1] if chair_turns else ""
    answers = [t[1] for t in chair_turns[1:]]
    others = collections.Counter(s for s, _ in turns if s != chair_name)
    rows.append(dict(date=d, chair=chair_name.replace("CHAIRMAN", "CHAIR"), n_turns=len(turns), opening_words=w(opening),
                     answers=len(answers), answers_ge40w=sum(w(a) >= 40 for a in answers),
                     answer_words=sum(w(a) for a in answers), other_speakers=len(others),
                     moderator_turns=others.most_common(1)[0][1] if others else 0))
out = os.path.join(base, "presser_segments.csv")
with open(out, "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=list(rows[0].keys())); wr.writeheader(); wr.writerows(rows)
by = collections.defaultdict(list)
for r in rows: by[r["chair"]].append(r)
T = collections.Counter()
for c, rs in by.items():
    n = len(rs); a = sum(r["answers"] for r in rs); a40 = sum(r["answers_ge40w"] for r in rs); aw = sum(r["answer_words"] for r in rs)
    print(f"{c:14s} pressers={n:3d} {rs[0]['date']}..{rs[-1]['date']} answer_turns={a:5d} (>=40 words {a40:5d}) "
          f"opening_words_mean={sum(r['opening_words'] for r in rs)/n:5.0f} answer_turns_per_presser={a/n:4.1f} words_per_answer={aw/a:4.0f}")
    T["pressers"] += n; T["answer_turns"] += a; T["answers_ge40w"] += a40; T["opening_words"] += sum(r['opening_words'] for r in rs); T["answer_words"] += aw
print("TOTAL", dict(T))
for r in rows:
    if r["answers"] < 10 or r["opening_words"] < 500:
        print("check", r)
