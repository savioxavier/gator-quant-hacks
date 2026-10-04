import sys, pypdf
for p in sys.argv[1:]:
    r = pypdf.PdfReader(p)
    out = p.replace('pdf/', 'txt/').replace('.pdf', '.txt')
    with open(out, 'w', encoding='utf-8') as f:
        for i, pg in enumerate(r.pages):
            f.write(f"\n=== page {i+1} ===\n")
            f.write(pg.extract_text() or '')
    print(out, len(r.pages))
