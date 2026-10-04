import re,html,urllib.request,sys
for ident in sys.argv[1:]:
    try:
        t=urllib.request.urlopen(urllib.request.Request(f"https://archive.org/details/{ident}",headers={'User-Agent':'Mozilla/5.0'}),timeout=90).read().decode('utf-8','ignore')
    except Exception as e:
        print(ident,'ERR',e); continue
    S=[(int(k),' '.join(html.unescape(re.sub(r'<[^>]+>',' ',s)).split())) for k,s in re.findall(r'_(\d{6})\.jpg"/>(.*?)(?=_\d{6}\.jpg"/>|\Z)', t, flags=re.S)]
    ks=[k for k,_ in S]
    rt=re.findall(r'runtime[^0-9]{0,40}([0-9:]+)',t)[:3]
    print(ident,'nseg',len(S),'min_k',min(ks) if ks else None,'max_k',max(ks) if ks else None,'runtime',rt)
