import re, os, pandas as pd, numpy as np
fv = r'<scratch>/fedtalk'
d = pd.read_excel(fv + '/verify_literature/fomc_all.xlsx', sheet_name='QA_identifier').drop(columns=['answer'])
d['s'] = (pd.to_datetime(d.datetime_start) - pd.to_datetime(d.press_conf_time)).dt.total_seconds()
def ts(s):
    p=[float(x) for x in s.split(':')]; return p[0]*3600+p[1]*60+p[2] if len(p)==3 else p[0]*60+p[1]
rows=[]
for date, g in d.groupby('date'):
    ds = pd.Timestamp(date).strftime('%Y%m%d')
    f = fv + f'/data_markets/vtt/{ds}.vtt'
    if not os.path.exists(f): rows.append(dict(date=ds, n_gpt=len(g), note='no vtt')); continue
    txt = open(f, encoding='utf-8').read()
    C = [(ts(a), ' '.join(t.split())) for a, b, t in re.findall(r'([\d:.]+) --> ([\d:.]+)[^\n]*\n(.*?)(?:\n\n|\Z)', txt, flags=re.S)]
    # chair answer starts in Q&A: chair-label cues after the first non-chair label
    lab = [(a, t) for a, t in C if re.search(r"[A-Z]{3,}[A-Z .'\-]*\.$", t)]
    first_other = next((a for a, t in lab if 'CHAIR' not in t and a > 60), None)
    cs = np.array([a for a, t in lab if 'CHAIR' in t and first_other is not None and a >= first_other])
    gs = np.sort(g.s.values)
    # nearest chair-label cue to each GPT answer start
    diffs = np.array([x - cs[np.argmin(np.abs(cs - x))] for x in gs]) if len(cs) else np.array([np.nan])
    # robust: best constant offset by grid search maximising matches within 3 s
    grid = np.arange(-400, 400.5, 0.5)
    score = [np.sum(np.min(np.abs((gs[:, None] - o) - cs[None, :]), axis=1) < 3) for o in grid] if len(cs) else [0]
    o = grid[int(np.argmax(score))]
    res = np.array([ (x - o) - cs[np.argmin(np.abs(cs - (x - o)))] for x in gs]) if len(cs) else np.array([np.nan])
    early = res[:len(res)//3]; late = res[-len(res)//3:]
    rows.append(dict(date=ds, n_gpt=len(g), n_chair_cues=len(cs), best_offset=o, matched_3s=int(max(score)),
                     med_abs_resid=round(np.median(np.abs(res)),1), resid_first_third=round(np.median(early),1), resid_last_third=round(np.median(late),1)))
R = pd.DataFrame(rows)
pd.set_option('display.width', 200)
print(R.to_string()); R.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "gpt_vs_vtt.csv"), index=False)
