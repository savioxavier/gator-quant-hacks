import pandas as pd
S = r'<scratch>'
a = pd.read_parquet(S + '/team_push/data/text_corpus/label_dates.parquet')
b = pd.read_parquet(S + '/verify_ld/new/label_dates.parquet')
for c in a.columns:
    ne = ~((a[c] == b[c]) | (a[c].isna() & b[c].isna()))
    if ne.any():
        print(c, int(ne.sum()))
ch = a.source_date != b.source_date
print(pd.DataFrame({'row': a.row[ch], 'old': a.source_date[ch], 'new': b.source_date[ch], 'olddoc': a.source_doc_id[ch], 'newdoc': b.source_doc_id[ch]}).to_string())
