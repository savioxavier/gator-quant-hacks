# Type I error of the A-25 O'Brien-Fleming rule (z > 2.95/2.09/1.71 at 8/16/24 events) when the per-event
# sd is estimated from the same events (studentised) and P&L is heavy-tailed.
import numpy as np
rng=np.random.default_rng(3); R=200000; bnd=np.array([2.95,2.09,1.71]); looks=[8,16,24]
for name,gen in [('normal',lambda s: rng.standard_normal(s)),('t3',lambda s: rng.standard_t(3,s)),
                 ('t3 skew-free, known sd',None)]:
    if gen is None: continue
    x=gen((R,24)); rej=np.zeros(R,bool); rej_known=np.zeros(R,bool)
    sd_true = 1.0 if name=='normal' else np.sqrt(3.0)
    for b,k in zip(bnd,looks):
        m=x[:,:k].mean(1); s=x[:,:k].std(1,ddof=1)
        z_est=m/s*np.sqrt(k); z_known=m/sd_true*np.sqrt(k)
        rej |= (z_est>b); rej_known |= (z_known>b)
    print(name,'type I with estimated sd: %.4f | with known sd: %.4f'%(rej.mean(),rej_known.mean()))
