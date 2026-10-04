import pandas as pd, numpy as np
R=pd.read_csv('gap_data/tv_anchor.csv',dtype={'date':str})
q=pd.read_csv('it1_data_eng/vtt_quality.csv',dtype={'date':str})
R=R[(R.n_match>0)&(R.late_hi>R.late_lo)].drop(columns=['overrun_s']).merge(q[['date','overrun_s','stretched_s','video_s']],on='date',how='left')
R['mid']=(R.late_lo+R.late_hi)/2; R['emid']=(R.early_lo+R.early_hi)/2; R['w']=R.late_hi-R.late_lo
R['drift']=R.mid-R.emid
good=R[R.mid>=-90].copy()
print('n good',len(good))
print('corr(offset mid, overrun_s) good:',round(good[['mid','overrun_s']].corr().iloc[0,1],3), ' spearman', round(good[['mid','overrun_s']].corr('spearman').iloc[0,1],3))
print(good.sort_values('overrun_s',ascending=False)[['date','mid','w','overrun_s','stretched_s','emid','drift']].head(10).round(1).to_string(index=False))
print('abs drift late-early quantiles', good.drift.abs().quantile([.5,.75,.9,1]).round(1).to_dict())
c=R[(R.date>='2023')&(R.date<='20260430')]
print('confirmation with TV anchor', len(c), 'width<=60 & not broken:', int(((c.w<=60)&(c.mid>=-90)).sum()))
print(c[['date','mid','w','overrun_s','stretched_s']].round(1).to_string(index=False))
# coverage: presser minutes covered by Power Lunch (program ends 15:00 ET) vs video length
good['cover_frac']= (1800-good['greeting_s'])/good['video_s']
print('share of video after the TV coverage ends (15:00 ET): median', round(1-good.cover_frac.median(),2))
