import re, pandas as pd, numpy as np
S = r'<scratch>'
ld = pd.read_parquet(S + '/team_push/data/text_corpus/label_dates.parquet')
docs = pd.read_parquet(S + '/team_push/data/text_corpus/docs_to_score.parquet')
print(docs.columns.tolist(), len(docs), docs.date.min(), docs.date.max())
sd = pd.to_datetime(ld.source_date)
print('undated', sd.isna().sum())
# own normalisation for leakage: tokens of [a-z0-9]+, sequence containment via token-joined strings with delimiters
def toks(s): return re.findall(r'[a-z0-9]+', str(s).lower())
dtxt = ['|' + '|'.join(toks(t)) + '|' for t in docs.text]
ddate = pd.to_datetime(docs.date).to_numpy()
last, first = [], []
for s in ld.sentence:
    tk = toks(s)
    if len(tk) < 4:
        last.append(pd.NaT); first.append(pd.NaT); continue
    n = '|' + '|'.join(tk) + '|'
    hit = [ddate[i] for i, t in enumerate(dtxt) if n in t]
    last.append(max(hit) if hit else pd.NaT); first.append(min(hit) if hit else pd.NaT)
last = pd.to_datetime(pd.Series(last)); first = pd.to_datetime(pd.Series(first))
rows = {}
for Y in range(2015, 2027):
    cut = pd.Timestamp(f'{Y}-01-01')
    use = (sd < cut) | (sd.isna() & (Y >= 2023))
    use_ds = ld.dataset_year <= Y - 1
    rows[Y] = dict(rows_true=int(use.sum()), leak_true=int((use & (last >= cut)).sum()),
                   first_true=int((use & (first >= cut)).sum()),
                   rows_dataset=int(use_ds.sum()), leak_dataset=int((use_ds & (last >= cut)).sum()),
                   only_true=int((use & ~use_ds).sum()), only_dataset=int((use_ds & ~use).sum()))
print(pd.DataFrame(rows).T.to_string())
# rows whose source_date < Y but earliest docs_to_score hit >= Y (Y >= 2016)
x = ld.assign(sd=sd, first=first, last=last)
w = x[(x.first.dt.year > x.sd.dt.year) & (x.first.dt.year >= 2016)]
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 110)
print(w[['row', 'source_doc_id', 'source_date', 'first', 'sentence']].to_string())
# distinct leaked sentences under true across years
lk = set()
for Y in range(2015, 2027):
    cut = pd.Timestamp(f'{Y}-01-01'); use = (sd < cut)
    lk |= set(ld.sentence[use & (last >= cut)].map(lambda s: ' '.join(toks(s))))
print('distinct leaked sentences', len(lk))
