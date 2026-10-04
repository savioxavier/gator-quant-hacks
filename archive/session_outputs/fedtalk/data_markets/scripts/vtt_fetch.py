"""Fetch the official WebVTT caption tracks (text) that the federalreserve.gov player loads, and summarise them:
time of the chair's greeting inside the video, number of speaker-label cues, caption span. No media files."""
import json, urllib.request, re, csv, os, time
H = {'User-Agent': 'Mozilla/5.0'}
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pk = json.load(open(os.path.join(base, 'html', 'bc_config.json')))['video_cloud']['policy_key']
meta = list(csv.DictReader(open(os.path.join(base, 'video_meta.csv'), encoding='utf-8')))
os.makedirs(os.path.join(base, 'vtt'), exist_ok=True)
def ts(s):
    p = s.split(':'); return sum(float(x) * 60 ** i for i, x in enumerate(reversed(p)))
lab = re.compile(r"^((?:CHAIR(?:MAN)?|MR\.|MS\.)?\s*(?:[A-Z][A-Z'\-]+ ){1,3}[A-Z][A-Z'\-]+)\.\s*$")
out = []
for r in meta:
    d = r['date']; path = os.path.join(base, 'vtt', f'{d}.vtt')
    if r['captions'] != 'True':
        out.append(dict(date=d, captions=False)); continue
    if not os.path.exists(path):
        vid = r['video_id'].split(';')[0]
        v = json.loads(urllib.request.urlopen(urllib.request.Request(
            f'https://edge.api.brightcove.com/playback/v1/accounts/66043936001/videos/{vid}',
            headers={**H, 'Accept': f'application/json;pk={pk}'}), timeout=30).read())
        t = [t for t in v['text_tracks'] if t['kind'] == 'captions'][0]
        srcs = [s['src'] for s in t.get('sources', []) if s.get('src', '').startswith('https')] or [t['src']]
        data = urllib.request.urlopen(urllib.request.Request(srcs[0], headers=H), timeout=30).read().decode('utf-8', 'replace')
        open(path, 'w', encoding='utf-8').write(data); time.sleep(0.5)
    data = open(path, encoding='utf-8').read()
    cues = re.findall(r'(\d{1,2}:\d{2}(?::\d{2})?\.\d{3}) --> (\d{1,2}:\d{2}(?::\d{2})?\.\d{3})[^\n]*\n(.*?)(?:\n\n|\Z)', data, re.S)
    greet = next((ts(c[0]) for c in cues[:40] if re.search(r'Good (afternoon|day|morning|evening)|Thank you|welcome', c[2])), None)
    labels = []
    for c in cues:
        for ln in c[2].split('\n'):
            m = lab.match(ln.strip())
            if m: labels.append((ts(c[0]), m.group(1)))
    out.append(dict(date=d, captions=True, n_cues=len(cues), first_cue_s=ts(cues[0][0]) if cues else None,
                    greeting_s=greet, last_cue_end_s=ts(cues[-1][1]) if cues else None,
                    speaker_label_cues=len(labels), chair_label_cues=sum(l[1].startswith('CHAIR') for l in labels),
                    duration_s=float(r['duration_s'])))
keys = ['date', 'captions', 'n_cues', 'first_cue_s', 'greeting_s', 'last_cue_end_s', 'speaker_label_cues', 'chair_label_cues', 'duration_s']
with open(os.path.join(base, 'vtt_summary.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(out)
print('done', len(out))
