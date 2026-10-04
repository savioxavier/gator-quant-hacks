import urllib.parse
import json,urllib.request,csv,re,sys
B='<scratch>/fedtalk/data_markets'
pk=json.load(open(B+'/html/bc_config.json'))['video_cloud']['policy_key']
meta={r['date']:r for r in csv.DictReader(open(B+'/video_meta.csv',encoding='utf-8'))}
H={'User-Agent':'Mozilla/5.0'}
for d in sys.argv[1:]:
    vid=meta[d]['video_id'].split(';')[0]
    v=json.loads(urllib.request.urlopen(urllib.request.Request(f'https://edge.api.brightcove.com/playback/v1/accounts/66043936001/videos/{vid}',headers={**H,'Accept':f'application/json;pk={pk}'}),timeout=30).read())
    hls=[s['src'] for s in v['sources'] if 'hls' in s.get('src','') and s['src'].startswith('https')][0]
    master=urllib.request.urlopen(urllib.request.Request(hls,headers=H),timeout=30).read().decode()
    lines=[l for l in master.splitlines() if l and not l.startswith('#')]
    sub=urllib.parse.urljoin(hls,lines[0]) if lines else None
    pl=urllib.request.urlopen(urllib.request.Request(sub,headers=H),timeout=30).read().decode()
    ext=[float(x) for x in re.findall(r'#EXTINF:([\d.]+)',pl)]
    mp4=[s for s in v['sources'] if s.get('container')=='MP4']
    print(d,'api_duration_s',v['duration']/1000,'mp4_durations',sorted({s.get('duration') for s in mp4}),'hls_sum_s',round(sum(ext),1),'nseg',len(ext),'PDT' ,'#EXT-X-PROGRAM-DATE-TIME' in pl,'updated_at',v.get('updated_at'),'created_at',v.get('created_at'))
