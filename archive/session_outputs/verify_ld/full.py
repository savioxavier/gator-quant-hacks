exec(open('spot.py', encoding='utf-8').read().split("dated = d[d.source_date.notna()]")[0])
import collections
bydoc = collections.defaultdict(list)
for f in txt:
    bydoc[(ftype(f), key(f))].append(f)
bad, earlier, sp_master_diff = [], [], []
for r in d.itertuples():
    t, stem = r.source_doc_id.split(':')
    k = cnorm(r.sentence)
    if not any(k in txt[f] for f in bydoc[(t, stem)]):
        bad.append((r.row, r.match_method, r.source_doc_id, r.sentence[:120]))
    if len(k) >= 30:
        hits = [f for f in txt if k in txt[f]]
        e = min(fd[f] for f in hits) if hits else None
        if e is not None and str(e.date()) < r.source_date:
            earlier.append((r.row, r.source_date, str(e.date()), [Path(f).name for f in hits if fd[f] == e][:2]))
print('rows whose sentence (char-normalised) is not in the named doc files:', len(bad))
print(pd.Series([b[1] for b in bad]).value_counts().to_dict())
for b in bad[:25]: print(b)
print('rows with an earlier occurrence than source_date:', len(earlier)); print(earlier[:10])
