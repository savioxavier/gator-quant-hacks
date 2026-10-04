"""Collect official video metadata (Brightcove playback API, the same call the federalreserve.gov player makes) for
every press-conference page. Metadata only: no media files are downloaded."""
import json, re, time, urllib.request, csv, os
H = {'User-Agent': 'Mozilla/5.0'}
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pk = json.load(open(os.path.join(base, 'html', 'bc_config.json')))['video_cloud']['policy_key']
dates = [l.strip() for l in open(os.path.join(base, 'presser_dates.txt')) if l.strip()]
rows = []
for d in dates:
    url = f'https://www.federalreserve.gov/monetarypolicy/fomcpresconf{d}.htm'
    if d == '20260128': url = 'https://www.federalreserve.gov/monetarypolicy/fomcpressconf20260128.htm'
    try:
        page = urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=30).read().decode('utf-8', 'replace')
    except Exception as e:
        rows.append(dict(date=d, page=url, video_id='', note=f'page error {e}')); continue
    vids = re.findall(r'data-video-id="(\d+)"', page)
    yt = re.findall(r'youtube\.com/(?:embed/|watch\?v=)([\w-]{11})', page)
    r = dict(date=d, page=url, video_id=';'.join(vids), youtube_ids=';'.join(sorted(set(yt))))
    if vids:
        try:
            req = urllib.request.Request(f'https://edge.api.brightcove.com/playback/v1/accounts/66043936001/videos/{vids[0]}',
                                         headers={**H, 'Accept': f'application/json;pk={pk}'})
            v = json.loads(urllib.request.urlopen(req, timeout=30).read())
            mp4 = [s for s in v.get('sources', []) if s.get('container') == 'MP4']
            best = max(mp4, key=lambda s: s.get('width') or 0) if mp4 else {}
            r.update(name=v.get('name'), duration_s=round((v.get('duration') or 0) / 1000, 1), created_at=v.get('created_at'),
                     published_at=v.get('published_at'), max_w=best.get('width'), max_h=best.get('height'),
                     max_bitrate=best.get('avg_bitrate'), max_size_mb=round((best.get('size') or 0) / 1e6),
                     captions=any(t.get('kind') == 'captions' for t in v.get('text_tracks', [])),
                     tags='|'.join(v.get('tags') or []))
        except Exception as e:
            r['note'] = f'api error {e}'
    rows.append(r); time.sleep(0.6)
keys = sorted({k for r in rows for k in r}, key=lambda k: ['date','name','duration_s','created_at','published_at','max_w','max_h','max_bitrate','max_size_mb','captions','video_id','youtube_ids','page','tags','note'].index(k) if k in ['date','name','duration_s','created_at','published_at','max_w','max_h','max_bitrate','max_size_mb','captions','video_id','youtube_ids','page','tags','note'] else 99)
with open(os.path.join(base, 'video_meta.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
print('done', len(rows))
