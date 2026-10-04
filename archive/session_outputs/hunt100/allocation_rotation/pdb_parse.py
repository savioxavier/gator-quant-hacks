import re, sys
html = open(sys.argv[1], encoding='utf-8').read().replace('\\"', '"')
pat = re.compile(r'\{"label":"([^"]{1,20})","value":(-?[0-9.eE+-]{1,25})\}')
groups = []; cur = []; last_end = -10
for m in pat.finditer(html):
    if m.start() - last_end <= 1 and cur:
        cur.append((m.group(1), float(m.group(2))))
    else:
        if cur: groups.append((cur_start, cur))
        cur = [(m.group(1), float(m.group(2)))]; cur_start = m.start()
    last_end = m.end()
if cur: groups.append((cur_start, cur))
for st, g in groups:
    ctx = html[max(0, st-300):st]
    keys = re.findall(r'"([A-Za-z_]{2,40})":', ctx)[-5:]
    print(len(g), keys, g[:2], g[-2:])
