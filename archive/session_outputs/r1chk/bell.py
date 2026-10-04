import re,html,os,urllib.request,sys
CACHE='tvcache'
def get(ident):
    p=os.path.join(CACHE,ident+'.html')
    if os.path.exists(p): return open(p,encoding='utf-8').read()
    t=urllib.request.urlopen(urllib.request.Request(f"https://archive.org/details/{ident}",headers={'User-Agent':'Mozilla/5.0'}),timeout=90).read().decode('utf-8','ignore')
    open(p,'w',encoding='utf-8').write(t); return t
for ident in sys.argv[1:]:
    S=[(int(k),' '.join(html.unescape(re.sub(r'<[^>]+>',' ',s)).split())) for k,s in re.findall(r'_(\d{6})\.jpg"/>(.*?)(?=_\d{6}\.jpg"/>|\Z)', get(ident), flags=re.S)]
    for k,t in S:
        if 3480<=k<=3720:
            hits=[m.start() for m in re.finditer(r'bell|BELL|>>|ring',t)]
            print(ident.split('_')[1],k,'|',t[:260].replace('\n',' '))
    print()
