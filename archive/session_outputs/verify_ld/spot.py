"""Independent spot-check of label_dates.parquet."""
import re, glob, os, json
from pathlib import Path
import pandas as pd
S = r'<scratch>'
T = Path(S + '/tdw_repo/data')
d = pd.read_parquet(S + '/team_push/data/text_corpus/label_dates.parquet')

def cnorm(s):  # char-only normalisation, different from the builder's word normalisation
    s = str(s).lower().replace('\u2019', "'").replace('\u2018', "'")
    return re.sub(r'[^a-z0-9]', '', s)

# every file, text as one string (CSV -> all 'sentence' cells joined)
files = []
for pat in ['filtered_data/**/*.csv', 'raw_data/meeting_minutes/*.txt', 'raw_data/press_conference/csv/all/*.csv',
            'raw_data/speech/text/all/*.txt']:
    files += glob.glob(str(T / pat), recursive=True)
txt = {}
for f in files:
    if f.endswith('.csv'):
        x = pd.read_csv(f, encoding='utf-8', encoding_errors='replace')
        t = ' '.join(x['sentence'].dropna().astype(str))
    else:
        t = Path(f).read_text(encoding='utf-8', errors='replace')
    txt[f] = cnorm(t)
print('files', len(txt))

def key(f):
    s = Path(f).stem.lower()
    s = re.sub(r'^labeled_', '', s); s = s.replace('_select', '').replace('_filtered', '')
    return s

def ftype(f):
    f = f.replace(chr(92), '/')
    return 'mm' if 'meeting_minutes' in f else 'pc' if 'press_conference' in f else 'sp'

# my own date table
mm = pd.read_excel(T / 'master_files/master_mm_final_Oct_2024.xlsx')
mmrel = {re.search(r'(\d{8})', u).group(1): pd.Timestamp(r).normalize() for u, r in zip(mm.Url, mm.ReleaseDate)}
spm = pd.read_csv(T / 'master_files/master_speech_final.csv')
spd = {}
for lp, dt, u in zip(spm.LocalPath, spm.Date, spm.Url):
    spd[os.path.splitext(os.path.basename(str(lp).replace(chr(92), '/')))[0].lower()] = (pd.Timestamp(dt), u)

def fdate(f):
    t, k = ftype(f), key(f)
    m = re.search(r'((?:19|20)\d{6})', k)
    if t == 'mm':
        return mmrel.get(m.group(1)) if m else None
    if t == 'pc':
        return pd.Timestamp(m.group(1))
    if k in spd:
        return spd[k][0]
    return pd.Timestamp(m.group(1)) if m else None

fd = {f: fdate(f) for f in txt}
print('files without a date:', [f for f, v in fd.items() if v is None][:5])

dated = d[d.source_date.notna()]
samp = pd.concat([g.sample(20, random_state=7) for _, g in dated.groupby('source_type')])
res = []
for r in samp.itertuples():
    t, stem = r.source_doc_id.split(':')
    own = [f for f in txt if ftype(f) == t and key(f) == stem]
    k = cnorm(r.sentence)
    in_doc = any(k in txt[f] for f in own)
    # earliest file anywhere containing it (only sentences with >= 30 chars, to avoid trivial hits)
    hits = [f for f in txt if len(k) >= 30 and k in txt[f]]
    earliest = min((fd[f] for f in hits if fd[f] is not None), default=None)
    # recompute the date of the named doc
    m = re.search(r'((?:19|20)\d{6})', stem)
    if t == 'mm':
        mydate = mmrel[m.group(1)]
    elif t == 'pc':
        mydate = pd.Timestamp(m.group(1))
    else:
        mydate = spd.get(stem, (pd.Timestamp(m.group(1)) if m else None,))[0]
        if m and stem in spd and spd[stem][0] != pd.Timestamp(m.group(1)):
            mydate = max(spd[stem][0], pd.Timestamp(m.group(1)))
    res.append(dict(row=r.row, type=r.source_type, doc=r.source_doc_id, date=r.source_date, method=r.match_method,
                    n_files=len(own), in_doc=in_doc, my_date=str(mydate.date()) if mydate is not None else None,
                    date_ok=(mydate is not None and str(mydate.date()) == r.source_date),
                    earliest=str(earliest.date()) if earliest is not None else None,
                    earliest_ok=(earliest is None or str(earliest.date()) >= r.source_date),
                    sp_url=spd.get(stem, (None, None))[1] if t == 'sp' else None, ds_year=r.dataset_year,
                    sent=r.sentence[:90]))
R = pd.DataFrame(res)
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 60); pd.set_option('display.max_rows', 100)
print(R.drop(columns=['sent', 'sp_url']).to_string())
print('\nnot found in named doc:', (~R.in_doc).sum(), ' date mismatch:', (~R.date_ok).sum(),
      ' earlier occurrence elsewhere:', (~R.earliest_ok).sum())
print(R[~R.in_doc | ~R.date_ok | ~R.earliest_ok].to_string())
R.to_csv(S + '/verify_ld/sample60.csv', index=False)
