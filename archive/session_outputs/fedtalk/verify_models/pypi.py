import json, urllib.request
pk={'whisperx':'3.8.6','faster-whisper':'1.2.1','pyannote.audio':'4.0.7','opensmile':'2.6.0','praat-parselmouth':'0.4.7','py-feat':'2.1.3','openface-test':'0.1.26','libreface':'0.2.0','mediapipe':'1.0.1','insightface':'2.1','emotiefflib':'1.1.1','hsemotion':'0.3.0','sixdrepnet':'0.1.6','retina-face':'0.0.18','funasr':'1.4.16','nemo-toolkit':'3.0.0','ctranslate2':'4.5.0'}
for p,claim in pk.items():
    try:
        d=json.load(urllib.request.urlopen(f'https://pypi.org/pypi/{p}/json',timeout=30))
        i=d['info']; v=i['version']; rel=d['releases'].get(v,[])
        t=rel[0]['upload_time'][:10] if rel else '?'
        win=any('win' in f['filename'] for f in rel)
        hasclaim = claim in d['releases']
        ct = d['releases'].get(claim,[{}])[0].get('upload_time','')[:10] if hasclaim else ''
        print(f"{p}: latest={v} ({t}) lic={i.get('license') and i['license'][:40]!r} req_py={i.get('requires_python')} winwheel={win} | claim {claim} exists={hasclaim} {ct}")
        if p=='whisperx': print('  requires:', i.get('requires_dist'))
    except Exception as e: print(p,'FAIL',e)
