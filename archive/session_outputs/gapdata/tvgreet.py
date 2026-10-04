import re,html,sys,subprocess,json,urllib.request
def items(prefix):
    u=f"https://archive.org/advancedsearch.php?q=identifier%3A{prefix}*&fl%5B%5D=identifier&fl%5B%5D=title&rows=50&output=json"
    return json.load(urllib.request.urlopen(u,timeout=60))['response']['docs']
def segs(ident):
    t=urllib.request.urlopen(f"https://archive.org/details/{ident}",timeout=90).read().decode('utf-8','ignore')
    return [(int(k),' '.join(html.unescape(re.sub(r'<[^>]+>',' ',s)).split())) for k,s in re.findall(r'_(\d{6})\.jpg"/>(.*?)(?=_\d{6}\.jpg"/>|\Z)', t, flags=re.S)]
for d in sys.argv[1:]:
    for ch in ['CNBC','BLOOMBERG','FBC']:
        try: docs=items(f"{ch}_{d}")
        except Exception as e: print(d,ch,'search err',e); continue
        for doc in docs:
            ident=doc['identifier']; hhmmss=ident.split('_')[2]
            h,m=int(hhmmss[:2]),int(hhmmss[2:4])
            # programs starting between 17:00 and 19:30 UTC (or 18-20 for EST)
            if not (16<=h<=19): continue
            try: S=segs(ident)
            except Exception as e: print(ident,'err',e); continue
            hits=[(k,txt[:160]) for k,txt in S if re.search(r'good afternoon',txt,re.I)]
            for k,txt in hits[:2]:
                print(d,ident,doc.get('title'),'offset_s',k,'|',txt)
