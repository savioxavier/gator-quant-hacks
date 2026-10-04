import re, glob, os, json
pat = re.compile(r'\{"label":"([^"]{1,20})","value":(-?[0-9.eE+-]{1,25})\}')
def groups(html):
    out = []; cur = []; last = -10; st = 0
    for m in pat.finditer(html):
        if m.start() - last <= 1 and cur: cur.append((m.group(1), float(m.group(2))))
        else:
            if cur: out.append((st, cur))
            cur = [(m.group(1), float(m.group(2)))]; st = m.start()
        last = m.end()
    if cur: out.append((st, cur))
    return out
res = {}
for f in sorted(glob.glob('pdb/*.html')):
    slug = os.path.basename(f)[:-5]
    html = open(f, encoding='utf-8').read().replace('\\"', '"')
    gs = groups(html)
    yearly = [g for st, g in gs if all(re.fullmatch(r'\d{4}', l) for l, _ in g) and len(g) > 15]
    strat = yearly[0]
    bench = yearly[1] if len(yearly) > 1 else None
    def ann(g):
        d = dict(g); ys = sorted(int(y) for y in d)
        r = {}
        for y in ys:
            prev = d.get(str(y-1))
            if prev: r[y] = d[str(y)]/prev - 1
        first = ys[0]
        r[first] = d[str(first)]/10000 - 1
        return r
    a = ann(strat)
    b = ann(bench) if bench else {}
    m = re.search(r'<meta name="description" content="([^"]+)"', html)
    desc = m.group(1) if m else ''
    res[slug] = {'ann': a, 'bench': b, 'desc': desc, 'start': min(a)}
json.dump(res, open('pdb_annual.json', 'w'), indent=0)
def cagr(a, y0, y1):
    p = 1.0; n = 0
    for y in range(y0, y1+1):
        if y in a: p *= 1 + a[y]; n += 1
    return p**(1/n) - 1 if n else float('nan'), n
for slug, d in res.items():
    a = d['ann']
    c_is, _ = cagr(a, 2008, 2023); c_post = cagr(a, 2024, 2025)[0]
    worst = min((a[y], y) for y in range(2008, 2026) if y in a)
    print(f"{slug[:45]:45s} start {d['start']} CAGR08-23 {c_is:6.1%} 24-25 {c_post:6.1%} 2022 {a.get(2022, float('nan')):6.1%} worst08-25 {worst[0]:.1%}({worst[1]}) bench08-23 {cagr(d['bench'],2008,2023)[0]:6.1%}")
