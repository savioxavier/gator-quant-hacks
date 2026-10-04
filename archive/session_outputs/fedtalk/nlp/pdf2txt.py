import sys, pypdf
r = pypdf.PdfReader(sys.argv[1])
out = []
for i, p in enumerate(r.pages):
    out.append(f"\n=== PAGE {i+1}\n" + (p.extract_text() or ""))
open(sys.argv[2], "w", encoding="utf-8").write("".join(out))
print(len(r.pages), "pages")
