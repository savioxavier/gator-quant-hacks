"""Step 4 (diagnostic only, not used to align any meeting): does the market say where caption-video zero is?

Speaker turns come from the caption label cues (CHAIR X. = chair answer starts; any other label = reporter or
moderator). Reporters' questions carry little news; chair answers do. With 1-second ES and ZN bars, the volatility
around chair-answer onsets should rise right after the true onset. For a global shift delta applied to the caption
timeline (wall clock = anchor + delta + caption time), we compute the pooled jump in normalised absolute 1 s returns
    J(delta) = mean |r| over [onset, onset+20 s) - mean |r| over [onset-15 s, onset)
across Q&A answer onsets. Anchors compared: (a) convention, anchor = 14:30:00; (b) TV, anchor = scheduled start +
GDELT TV offset (median of CNBC/FBC; this includes the TV/caption delay, so the TV-anchored peak is expected at a
small negative delta). The delta that maximises J estimates the systematic offset of each anchor. Pooled over
meetings, so it cannot and does not set any single meeting's alignment.
Output: s4_market_align.csv (J by delta and anchor), printed summary.
"""
import os, re
import numpy as np, pandas as pd
from mkt import load_1s, ET

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.dirname(os.path.dirname(HERE))
DM = os.path.join(SP, 'fedtalk', 'data_markets')
B = pd.read_csv(os.path.join(HERE, 's1_calendar_vtt.csv'), dtype={'date_key': str})
EV = pd.read_csv(os.path.join(HERE, 'events.csv'), dtype={'date': str})
EV['date_key'] = EV.date.str.replace('-', '')
tvm = EV.set_index('date_key').v0_minus_sched_tv_s.dropna()

def ts(s):
    p = [float(x) for x in s.split(':')]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]

def turns(d):
    raw = open(os.path.join(DM, 'vtt', d + '.vtt'), encoding='utf-8').read()
    L = []
    for a, b, body in re.findall(r'([\d:.]+) --> ([\d:.]+)[^\n]*\n(.*?)(?:\n\n|\Z)', raw, flags=re.S):
        body = ' '.join(body.split())
        m = re.search(r"((?:[A-Z][A-Z'\-]+\.? ){0,3}[A-Z][A-Z'\-]+)[.:]$", body)
        if m and body.upper() == body:
            L.append((ts(a), 'CHAIR' in body))
    return L

s1 = load_1s()
s1 = s1[s1.symbol.isin(['ES.v.0', 'ZN.v.0', 'ZT.v.0'])]
deltas = np.arange(-40, 91, 1)
res = []
good = B[(B.has_captions == 1) & (B.scheduled == 1) & (B.caption_overrun_s.abs() <= 20) & (B.n_stretched_open == 0)]
for sym in ['ES.v.0', 'ZN.v.0', 'ZT.v.0']:
    acc = {('conv', dl): [] for dl in deltas}
    acc.update({('tv', dl): [] for dl in deltas})
    n_meet = {'conv': 0, 'tv': 0}
    for _, r in good.iterrows():
        d = r.date_key
        x = s1[(s1.d == d) & (s1.symbol == sym)].set_index('t').close
        if len(x) < 1000:
            continue
        day0 = pd.Timestamp(f'{r.date} 14:00', tz=ET)
        grid = pd.date_range(day0, day0 + pd.Timedelta('2h30min'), freq='1s')
        p = x.reindex(grid, method='ffill')
        ar = np.abs(np.log(p).diff()).fillna(0).values
        tsec = (grid - pd.Timestamp(f'{r.date} 14:30', tz=ET)).total_seconds().values  # seconds after 14:30:00
        T = turns(d)
        qa0 = r.first_qa_label_s
        onsets = [t for i, (t, ch) in enumerate(T) if ch and t > qa0 and i > 0 and not T[i - 1][1]]
        lo, hi = qa0, r.last_speech_end_s
        base = np.median(ar[(tsec >= lo) & (tsec <= hi)][ar[(tsec >= lo) & (tsec <= hi)] > 0]) if np.any(ar > 0) else np.nan
        if not np.isfinite(base) or base <= 0:
            continue
        nr = ar / base
        cs = np.concatenate([[0], np.cumsum(nr)])
        def mean_between(a, b):  # a, b seconds after 14:30
            i0 = int(np.searchsorted(tsec, a)); i1 = int(np.searchsorted(tsec, b))
            return (cs[i1] - cs[i0]) / max(i1 - i0, 1)
        anchors = {'conv': 0.0}
        if d in tvm.index:
            anchors['tv'] = float(tvm[d])
        for an, a0 in anchors.items():
            n_meet[an] += 1
            for dl in deltas:
                j = [mean_between(a0 + dl + o, a0 + dl + o + 20) - mean_between(a0 + dl + o - 15, a0 + dl + o) for o in onsets]
                acc[(an, dl)].append(np.mean(j))
    for (an, dl), v in acc.items():
        if v:
            res.append(dict(sym=sym, anchor=an, delta=dl, J=np.mean(v), se=np.std(v, ddof=1) / np.sqrt(len(v)), n_meetings=len(v)))
R = pd.DataFrame(res)
R.to_csv(os.path.join(HERE, 's4_market_align.csv'), index=False)
for (sym, an), g in R.groupby(['sym', 'anchor']):
    g = g.sort_values('J', ascending=False)
    top = g.iloc[0]
    # smoothed peak: 5 s moving average
    gg = R[(R.sym == sym) & (R.anchor == an)].sort_values('delta')
    sm = gg.J.rolling(7, center=True).mean()
    print(f'{sym} anchor={an} n={int(top.n_meetings)} argmax delta={int(top.delta)} J={top.J:.3f} (se {top.se:.3f}); '
          f'smoothed argmax delta={int(gg.delta.iloc[int(np.nanargmax(sm.values))])}; J(0)={gg[gg.delta == 0].J.iloc[0]:.3f}')
