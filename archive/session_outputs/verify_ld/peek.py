import pandas as pd
S=r'<scratch>'
T=S+'/tdw_repo/data/'
d=pd.read_parquet(S+'/team_push/data/text_corpus/label_dates.parquet')
print(d.dtypes); print(d.head(2).T)
st=d.source_doc_id.str.split(':').str[1]
print(st.str.match(r'^\d').value_counts())
print(d[~st.str.match(r'^\d')].source_doc_id.unique()[:20])
print(pd.crosstab(d.source_type,d.source_doc_type))
m=pd.read_excel(T+'master_files/master_mm_final_Oct_2024.xlsx'); print(m.columns.tolist()); print(m.head(3).T); print(m.tail(2).T)
print(pd.read_excel(T+'master_files/master_pc_final.xlsx').head(2).T)
