import re,html,sys,json,urllib.request
def segs(ident):
    t=urllib.request.urlopen(f"https://archive.org/details/{ident}",timeout=90).read().decode('utf-8','ignore')
    return [(int(k),' '.join(html.unescape(re.sub(r'<[^>]+>',' ',s)).split())) for k,s in re.findall(r'_(\d{6})\.jpg"/>(.*?)(?=_\d{6}\.jpg"/>|\Z)', t, flags=re.S)]
ident=sys.argv[1]; lo,hi=int(sys.argv[2]),int(sys.argv[3])
for k,txt in segs(ident):
    if lo<=k<=hi: print(k,'|',txt); print()
