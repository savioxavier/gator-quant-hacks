import json,urllib.request,sys
for d in sys.argv[1:]:
    for ch in ['CNBC','FBC','BLOOMBERG']:
        u=f"https://archive.org/advancedsearch.php?q=identifier%3A{ch}_{d}*&fl%5B%5D=identifier&rows=60&output=json"
        try:
            t=json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=60).read())
            ids=sorted(x['identifier'] for x in t['response']['docs'])
            print(d,ch,[i for i in ids if any(h in i for h in ['_17','_18','_19','_20'])])
        except Exception as e: print(d,ch,'ERR',e)
