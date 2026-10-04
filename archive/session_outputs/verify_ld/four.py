import pandas as pd, re, glob
S = r'<scratch>'
d = pd.read_parquet(S + '/team_push/data/text_corpus/label_dates.parquet').set_index('row')
for row, pat in [(805, 'raw_data/meeting_minutes/19980331.txt'), (1963, 'raw_data/meeting_minutes/19970819.txt'),
                 (1990, 'raw_data/speech/text/all/20000522.txt'), (2057, 'raw_data/speech/text/all/kroszner20061116a.txt')]:
    r = d.loc[row]
    print('ROW', row, r.source_type, r.source_doc_id, r.source_date, r.match_method, 'n_docs', r.n_source_docs, 'ds', r.dataset_year)
    print('  S:', r.sentence)
    t = open(S + '/tdw_repo/data/' + pat, encoding='utf-8', errors='replace').read()
    w = r.sentence.split()
    i = t.find(' '.join(w[:5]))
    if i < 0: i = t.find(' '.join(w[-5:]))
    print('  RAW', pat, i, repr(t[max(0, i - 50): i + len(r.sentence) + 80]))
