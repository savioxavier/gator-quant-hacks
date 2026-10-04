import json, urllib.request, time, sys
out={}
for mid in open('ids.txt').read().split():
    url=f"https://huggingface.co/api/models/{mid}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            d=json.load(r)
        cd=d.get('cardData') or {}
        st=(d.get('safetensors') or {}).get('total')
        tags=[t for t in d.get('tags',[]) if t.startswith('license:')]
        out[mid]=dict(ok=True, id=d.get('id'), license=cd.get('license'), license_name=cd.get('license_name'), lictags=tags, gated=d.get('gated'), lastModified=d.get('lastModified'), createdAt=d.get('createdAt'), params=st, downloads=d.get('downloads'), base=cd.get('base_model'))
    except Exception as e:
        out[mid]=dict(ok=False, err=str(e))
    time.sleep(0.3)
json.dump(out, open('hf_meta.json','w'), indent=1)
for k,v in out.items():
    if v['ok']:
        print(f"{k} | id={v['id']} | lic={v['license']} {v['license_name'] or ''} | gated={v['gated']} | mod={str(v['lastModified'])[:10]} | params={v['params']} | dl={v['downloads']}")
    else: print(k,'| FAIL', v['err'])
