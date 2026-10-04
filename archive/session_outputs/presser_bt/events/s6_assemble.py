"""Step 6: assemble events.csv (one row per press-conference meeting, 75 rows) plus a long market file.

Timing model. Caption cue times are seconds from caption-video zero (V0). Wall clock = V0 + cue time.
  * convention (literature, Gomez-Cram and Grotteria Table 1): V0 = scheduled start (14:30:00 ET; 11:00 / 18:30 for
    the two unscheduled 2020 meetings).
  * TV evidence (s2_tv_gdelt_*.csv): live TV caption blocks give off = V0 + lag - scheduled start, lag = live TV +
    live-caption delay, assumed LAG_S = 11 s with band [3, 20] s (not measured here; the upper end covers the -14 s
    systematic difference between Internet Archive page timing and GDELT timing).  V0_tv = sched + off - LAG_S.
  * archive pages (s2b): secondary, used only where GDELT has no coverage (Dec 2024 on); their segment timing differs
    from GDELT by a station/item-specific amount, so they carry a wider uncertainty.
Start = V0 + greeting cue (first audible open matching the transcript's first words). End = V0 + end of last speech cue.
Drop rule (plan section 4): drop from timing-sensitive tests if start uncertainty > 30 s; also drop when there are no
captions (no answer times without ASR), when the caption timeline is distorted (overrun > 20 s or stretched cues
> 30 s in total), or when the downloaded market window does not contain the event.
"""
import os, re, glob
import numpy as np, pandas as pd
from mkt import load_1m, load_bbo, Bars, SYMS, ET, tick, MULT

HERE = os.path.dirname(os.path.abspath(__file__))
LAG_S, LAG_LO, LAG_HI = 11.0, 3.0, 20.0
B = pd.read_csv(os.path.join(HERE, 's1_calendar_vtt.csv'), dtype={'date_key': str})

# ---------------- TV evidence ----------------
def read(f):
    p = os.path.join(HERE, f)
    return pd.read_csv(p, dtype={'date_key': str}) if os.path.exists(p) else pd.DataFrame(columns=['date_key'])
def read_gdelt(st):
    df = read(f's2_tv_gdelt_{st}.csv')
    if len(df):
        return df
    rows = []  # fall back to the progress log while the run is still going
    p = os.path.join(HERE, f's2_gdelt_{st.lower()}.log')
    if os.path.exists(p):
        for line in open(p, encoding='utf-8', errors='ignore'):
            m = re.match(r'(\d{8}) (\[.*\])', line.strip())
            if m:
                for s_, n, off, mad, opn, note in eval(m.group(2).replace('nan', 'None')):
                    rows.append(dict(date_key=m.group(1), station=s_, n_used=n, off_median_s=off, off_mad_s=mad, tv_open_minus_sched_s=opn))
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=['date_key'])
g_c, g_f = read_gdelt('CNBC'), read_gdelt('FBC')
def parse_log(f):
    rows = []
    p = os.path.join(HERE, f)
    if not os.path.exists(p):
        return pd.DataFrame(columns=['date_key'])
    for line in open(p, encoding='utf-8', errors='ignore'):
        m = re.match(r'(\d{8}) (\[.*\])', line.strip())
        if not m:
            continue
        for st, n, off, mad, opn in eval(m.group(2).replace('nan', 'None')):
            rows.append(dict(date_key=m.group(1), station=st, n=n, off=off, mad=mad, open_fit=opn))
    return pd.DataFrame(rows)
arch = pd.concat([parse_log('s2b_archive_part1.log'), parse_log('s2b_archive_part2.log'), parse_log('s2b_archive_part3.log')]).drop_duplicates(['date_key', 'station'], keep='last')

def gd(df, d, col):
    x = df[df.date_key == d] if len(df) else df
    return float(x[col].iloc[0]) if len(x) and col in x and pd.notna(x[col].iloc[0]) else np.nan

# calibration of archive-page offsets against GDELT on overlapping meetings (per station, median difference)
cal = {}
for st, gdf in [('CNBC', g_c), ('FBC', g_f)]:
    diffs = []
    for d in set(arch.date_key):
        a = arch[(arch.date_key == d) & (arch.station == st)]
        if len(a) and pd.notna(a.off.iloc[0]) and not np.isnan(gd(gdf, d, 'off_median_s')):
            diffs.append(float(a.off.iloc[0]) - gd(gdf, d, 'off_median_s'))
    cal[st] = (float(np.median(diffs)), float(np.median(np.abs(np.array(diffs) - np.median(diffs)))), len(diffs)) if diffs else (np.nan, np.nan, 0)
print('archive-minus-GDELT offset by station (median, MAD, n):', cal)


import json, html as _html
DM = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'fedtalk', 'data_markets')
def _norm(t):
    return re.findall(r"[a-z]+", t.lower().replace('%', ' percent '))
def _transcript_words(d):
    txt = open(os.path.join(DM, 'pdf', f'FOMCpresconf{d}.txt'), encoding='utf-8', errors='replace').read()
    m = re.search(r'CHAIR(?:MAN)? [A-Z]+[.:]\s*', txt)
    return _norm(txt[m.end():]) if m else []
def tv_open_gdelt(d, st, sched, rate=3.0, kmax=150):
    """TV time (s after sched, includes lag) of the chair's first transcript word from cached GDELT blocks.
    Uses 5-word sequences unique in the whole transcript, located in its first 300 words; each matched block gives
    t0 = block start + j/3 - k/rate (k = transcript word index, j = position in the block); returns the median."""
    f = os.path.join(HERE, 'src', 'tv_raw', f'{d}_{st}.json')
    if not os.path.exists(f):
        return np.nan
    js = json.load(open(f, encoding='utf-8'))
    PW = _transcript_words(d)
    cnt, pos = {}, {}
    for i in range(len(PW) - 4):
        g5 = ' '.join(PW[i:i + 5]); cnt[g5] = cnt.get(g5, 0) + 1; pos.setdefault(g5, i)
    est = []
    for c in js.get('clips', []):
        b = (pd.Timestamp(c['date']).tz_convert(ET) - sched).total_seconds()
        if not (-120 <= b <= 400):
            continue
        sn = _norm(c.get('snippet', ''))
        for j in range(len(sn) - 4):
            g5 = ' '.join(sn[j:j + 5])
            if cnt.get(g5) == 1 and pos[g5] <= kmax:
                est.append(b + j / 3.0 - pos[g5] / rate)
                break
    return float(np.median(est)) if est else np.nan
def tv_open_archive(d, st, sched):
    """Archive-page time (s after sched) of the segment text 'good afternoon/good evening' (char-fraction interpolation)."""
    best = np.nan
    for f in glob.glob(os.path.join(HERE, 'src', 'tv_archive', f'{st}_{d}_*.html')):
        mm = re.search(rf'{st}_(\d{{8}})_(\d{{6}})_', os.path.basename(f))
        t0 = pd.Timestamp(mm.group(1) + mm.group(2), tz='UTC').tz_convert(ET)
        t = open(f, encoding='utf-8', errors='ignore').read()
        for k, seg in re.findall(r'_(\d{6})\.jpg"/>(.*?)(?=_\d{6}\.jpg"/>|\Z)', t, flags=re.S):
            seg = ' '.join(_html.unescape(re.sub(r'<[^>]+>', ' ', seg)).split()).lower()
            tabs = (t0 + pd.Timedelta(seconds=int(k)) - sched).total_seconds()
            if -300 < tabs < 900:
                p = seg.find('good afternoon')
                if p < 0:
                    p = seg.find('good evening')
                if p >= 0:
                    v = tabs + 60.0 * p / max(len(seg), 1)
                    best = v if np.isnan(best) else min(best, v)
    return best

# drift of the caption timeline against live TV through the presser (archive segments, offsets late - early)
_seg = pd.concat([pd.read_csv(os.path.join(HERE, f), dtype={'date_key': str}) for f in
                  ('s2b_tv_archive_segments_main.csv', 's2b_tv_archive_segments_part3.csv', 's2b_tv_archive_segments_part4.csv')
                  if os.path.exists(os.path.join(HERE, f))]).dropna(subset=['off_s']).drop_duplicates(['date_key', 'station', 'item', 'seg_s'])
DRIFT = {}
for (d_, st_), g_ in _seg.groupby(['date_key', 'station']):
    g_ = g_.sort_values('vtt_t'); m_ = g_.off_s.median(); g_ = g_[(g_.off_s - m_).abs() < 15]
    if len(g_) >= 8 and g_.vtt_t.max() - g_.vtt_t.min() > 600:
        DRIFT[(d_, st_)] = float(g_[g_.vtt_t > g_.vtt_t.max() - 600].off_s.median() - g_[g_.vtt_t < g_.vtt_t.min() + 600].off_s.median())
med_greet = float(B.loc[B.has_captions == 1, 'greeting_s'].median())
RATE = {'Yellen': 2.35, 'Powell': 3.2, 'Warsh': 3.0}  # opening-statement words/s, median caption words/s by chair
# transcript-based opening estimator, calibrated against the caption-based TV start on meetings with clean captions
OPEN = {}
for _, r in B.iterrows():
    sched = pd.Timestamp(f'{r.date} {r.presser_sched_et}', tz=ET)
    OPEN[r.date_key] = {st: tv_open_gdelt(r.date_key, st, sched, rate=RATE[r.chair]) for st in ['CNBC', 'FBC']}
OPEN_CAL = {}
for st, gdf in [('CNBC', g_c), ('FBC', g_f)]:
    ch = []
    for _, r in B.iterrows():
        clean = r.has_captions == 1 and abs(r.caption_overrun_s) <= 20 and r.stretched_all_s <= 30
        off = gd(gdf, r.date_key, 'off_median_s')
        if clean and not np.isnan(off) and not np.isnan(OPEN[r.date_key][st]):
            ch.append(OPEN[r.date_key][st] - (off + r.greeting_s))
    ch = np.array(ch)
    OPEN_CAL[st] = (float(np.median(ch)), float(1.4826 * np.median(np.abs(ch - np.median(ch)))), len(ch)) if len(ch) else (0.0, 10.0, 0)
print('transcript-opening estimator minus caption-based TV start (median, robust sd, n):', OPEN_CAL)

rows = []
for _, r in B.iterrows():
    d = r.date_key
    sched = pd.Timestamp(f'{r.date} {r.presser_sched_et}', tz=ET)
    o = dict(date_key=d)
    oc, of_ = gd(g_c, d, 'off_median_s'), gd(g_f, d, 'off_median_s')
    o.update(tv_gdelt_cnbc_off_s=oc, tv_gdelt_cnbc_mad_s=gd(g_c, d, 'off_mad_s'), tv_gdelt_cnbc_n=gd(g_c, d, 'n_used'),
             tv_gdelt_fbc_off_s=of_, tv_gdelt_fbc_mad_s=gd(g_f, d, 'off_mad_s'), tv_gdelt_fbc_n=gd(g_f, d, 'n_used'),
             tv_gdelt_cnbc_open_s=gd(g_c, d, 'tv_open_minus_sched_s'), tv_gdelt_fbc_open_s=gd(g_f, d, 'tv_open_minus_sched_s'))
    for st in ['CNBC', 'FBC', 'BLOOMBERG']:
        a = arch[(arch.date_key == d) & (arch.station == st)]
        o[f'tv_archive_{st.lower()}_off_s'] = float(a.off.iloc[0]) if len(a) and pd.notna(a.off.iloc[0]) else np.nan
        o[f'tv_archive_{st.lower()}_mad_s'] = float(a.mad.iloc[0]) if len(a) and pd.notna(a.mad.iloc[0]) else np.nan
    has_vtt = r.has_captions == 1
    gre = r.greeting_s if has_vtt else med_greet
    # ---- convention
    start_conv = sched + pd.Timedelta(seconds=gre)
    end_conv = sched + pd.Timedelta(seconds=(r.last_speech_end_s if has_vtt else r.video_duration_s))
    # ---- TV-implied V0 (or open time for no-caption / distorted-caption meetings)
    src, v0_off, unc = None, np.nan, np.nan
    start_tv = end_tv = pd.NaT
    # stretched cues = local forced-alignment failure (distorted timeline). A caption overrun alone (captions running
    # past the trimmed video) is kept when live TV shows no drift of the caption timeline through the presser.
    distorted = has_vtt and (r.n_stretched_open > 0 or r.stretched_all_s > 30)
    o['tv_drift_s'] = DRIFT.get((d, 'CNBC'), DRIFT.get((d, 'FBC'), np.nan))
    # FOX Business captions ran ~30 s later than CNBC from 2023 to mid-2025 (CNBC and FBC agree within 9 s in
    # 2016-2022 and again from mid-2025 on archive pages); when the two disagree by > 12 s use CNBC only.
    fbc_shift = (not np.isnan(oc)) and (not np.isnan(of_)) and abs(oc - of_) > 12
    offs = [x for x in ((oc,) if fbc_shift else (oc, of_)) if not np.isnan(x)]
    mads = [x for x in ((gd(g_c, d, 'off_mad_s'),) if fbc_shift else (gd(g_c, d, 'off_mad_s'), gd(g_f, d, 'off_mad_s'))) if not np.isnan(x)]
    o['tv_fbc_excluded'] = int(fbc_shift)
    lag_half = (LAG_HI - LAG_LO) / 2
    opens_g = {st: OPEN[d][st] - OPEN_CAL[st][0] for st in ['CNBC', 'FBC']}
    opens_g = {k: v for k, v in opens_g.items() if not np.isnan(v)}
    o['tv_open_cnbc_s'], o['tv_open_fbc_s'] = opens_g.get('CNBC', np.nan), opens_g.get('FBC', np.nan)
    if len(opens_g) == 2 and abs(opens_g['CNBC'] - opens_g['FBC']) > 12:
        opens_g = {'CNBC': opens_g['CNBC']}  # same FBC caption-delay rule as for the offsets
    if has_vtt and offs and not distorted:
        v0_off = float(np.median(offs)) - LAG_S
        disagree = (max(offs) - min(offs)) / 2 if len(offs) == 2 else (6.0 if fbc_shift else 10.0)  # single station penalty
        unc = float(np.sqrt(lag_half ** 2 + disagree ** 2 + (max(mads) if mads else 5) ** 2))
        src = 'TV live captions, GDELT (' + ('CNBC+FBC' if len(offs) == 2 else ('CNBC; FBC excluded, shifted' if fbc_shift else ('CNBC' if not np.isnan(oc) else 'FBC'))) + f') minus assumed {LAG_S:.0f} s lag'
        start_tv = sched + pd.Timedelta(seconds=v0_off + gre)
        end_tv = sched + pd.Timedelta(seconds=v0_off + r.last_speech_end_s)
    elif opens_g and (not has_vtt or distorted):
        ov = list(opens_g.values())
        t_open = float(np.median(ov)) - LAG_S
        disagree = (max(ov) - min(ov)) / 2 if len(ov) == 2 else 10.0
        unc = float(np.sqrt(lag_half ** 2 + disagree ** 2 + max(OPEN_CAL[k][1] for k in opens_g) ** 2))
        src = ('TV live captions, GDELT blocks matched to the transcript opening (' + '+'.join(opens_g) + f'; calibrated on clean-caption meetings) minus assumed {LAG_S:.0f} s lag; '
               + ('no captions' if not has_vtt else 'caption timeline distorted, not used'))
        start_tv = sched + pd.Timedelta(seconds=t_open)
        dur = (r.video_duration_s - med_greet) if not has_vtt else (min(r.last_speech_end_s, r.video_duration_s) - min(r.greeting_s, 30))
        end_tv = start_tv + pd.Timedelta(seconds=dur)
        unc_end = np.nan
        v0_off = t_open - (med_greet if not has_vtt else r.greeting_s)
    else:
        a_offs = []
        ac, af = o['tv_archive_cnbc_off_s'], o['tv_archive_fbc_off_s']
        a_fbc_shift = (not np.isnan(ac)) and (not np.isnan(af)) and abs(ac - af) > 12
        o['tv_fbc_excluded'] = int(a_fbc_shift) if not o['tv_fbc_excluded'] else 1
        for st in (['CNBC'] if a_fbc_shift else ['CNBC', 'FBC']):
            x = o[f'tv_archive_{st.lower()}_off_s']
            if has_vtt and not distorted and not np.isnan(x) and not np.isnan(cal.get(st, (np.nan,))[0]):
                a_offs.append(x - cal[st][0])
        a_open = {st: tv_open_archive(d, st, sched) for st in ['CNBC', 'FBC']}
        a_open = {k: v - cal[k][0] for k, v in a_open.items() if not np.isnan(v) and not np.isnan(cal[k][0])}
        cal_mad = max(cal[st][1] for st in ['CNBC', 'FBC'] if not np.isnan(cal[st][1]))
        if a_offs:
            v0_off = float(np.median(a_offs)) - LAG_S
            rng = (max(a_offs) - min(a_offs)) if len(a_offs) == 2 else 15.0  # full range; single station (FBC shifted): 15 s
            unc = float(np.sqrt(lag_half ** 2 + rng ** 2 + (1.4826 * cal_mad) ** 2))
            src = f'TV caption segments, Internet Archive item pages (calibrated -14 s to GDELT), minus assumed {LAG_S:.0f} s lag'
            start_tv = sched + pd.Timedelta(seconds=v0_off + gre)
            end_tv = sched + pd.Timedelta(seconds=v0_off + r.last_speech_end_s)
        elif a_open:
            ov = list(a_open.values())
            t_open = float(np.median(ov)) - LAG_S
            rng = (max(ov) - min(ov)) if len(ov) == 2 else 15.0
            unc = float(np.sqrt(lag_half ** 2 + rng ** 2 + (1.4826 * cal_mad) ** 2 + 10 ** 2))
            src = f'TV caption segment containing the greeting, Internet Archive item pages (calibrated), minus {LAG_S:.0f} s lag; ' + ('no captions' if not has_vtt else 'caption timeline distorted')
            start_tv = sched + pd.Timedelta(seconds=t_open)
            dur = (r.video_duration_s - med_greet) if not has_vtt else (min(r.last_speech_end_s, r.video_duration_s) - min(r.greeting_s, 30))
            end_tv = start_tv + pd.Timedelta(seconds=dur)
            v0_off = t_open - (med_greet if not has_vtt else r.greeting_s)
    o['v0_minus_sched_tv_s'] = round(v0_off, 1) if (not np.isnan(v0_off) and has_vtt and not distorted) else np.nan
    o['presser_start_conv_et'] = start_conv.strftime('%H:%M:%S')
    o['presser_end_conv_et'] = end_conv.strftime('%H:%M:%S')
    o['presser_start_tv_et'] = start_tv.strftime('%H:%M:%S') if pd.notna(start_tv) else None
    o['presser_end_tv_et'] = end_tv.strftime('%H:%M:%S') if pd.notna(end_tv) else None
    o['start_unc_tv_s'] = round(unc, 1) if not np.isnan(unc) else np.nan
    # convention uncertainty: evidence-based lower bound |V0_tv - sched| (+ lag band); without TV evidence use the
    # 90th percentile of |V0_tv - sched| over TV-checked meetings (filled below)
    o['start_unc_conv_s'] = round(abs(o['v0_minus_sched_tv_s']) + lag_half, 1) if not np.isnan(o['v0_minus_sched_tv_s']) else (
        round(abs((start_tv - start_conv).total_seconds()) + lag_half, 1) if pd.notna(start_tv) else np.nan)
    o['_start_tv'], o['_end_tv'], o['_start_conv'], o['_end_conv'], o['tv_source'] = start_tv, end_tv, start_conv, end_conv, src
    rows.append(o)
T = pd.DataFrame(rows)
pop = T.v0_minus_sched_tv_s.abs().dropna()
p90 = float(np.percentile(pop, 90)) + (LAG_HI - LAG_LO) / 2 if len(pop) else np.nan
T['start_unc_conv_s'] = T.start_unc_conv_s.fillna(round(p90, 1))
print(f'|V0_tv - sched| over {len(pop)} TV-checked meetings: median {pop.median():.1f} s, p90 {np.percentile(pop, 90) if len(pop) else np.nan:.1f} s')

E = B.merge(T, on='date_key', how='left')
# ---------------- primary estimate, drop flags ----------------
def primary(x):
    if pd.notna(x._start_tv):
        return x._start_tv, x._end_tv, x.start_unc_tv_s, x.tv_source
    return x._start_conv, x._end_conv, x.start_unc_conv_s, ('caption greeting cue + scheduled-start convention (V0 = scheduled start, no TV evidence)' if x.has_captions == 1
                                                         else 'no captions: convention + median greeting offset; video duration')
P = E.apply(lambda x: pd.Series(primary(x), index=['_start', '_end', 'start_unc_s', 'start_source']), axis=1)
E = pd.concat([E, P], axis=1)
E['presser_start_est_et'] = E._start.dt.strftime('%H:%M:%S')
E['presser_end_est_et'] = E._end.dt.strftime('%H:%M:%S')
E['presser_duration_min'] = ((E._end - E._start).dt.total_seconds() / 60).round(1)
E['qa_start_est_et'] = [(s - pd.Timedelta(seconds=g) + pd.Timedelta(seconds=q)).strftime('%H:%M:%S') if pd.notna(q) else None
                        for s, g, q in zip(E._start, E.greeting_s.fillna(med_greet), E.first_qa_label_s)]

def reasons(x):
    rs = []
    if x.has_captions != 1:
        rs.append('no_captions(ASR needed for answer times)')
    else:
        if abs(x.caption_overrun_s) > 20 and not (pd.notna(x.tv_drift_s) and abs(x.tv_drift_s) <= 5):
            rs.append(f'caption_overrun_{x.caption_overrun_s:+.0f}s_without_TV_drift_check')
        if x.stretched_all_s > 30 or x.n_stretched_open > 0:
            rs.append(f'stretched_cues_{x.stretched_all_s:.0f}s(caption timeline distorted)')
    if x.start_unc_s > 30:
        rs.append(f'start_unc_{x.start_unc_s:.0f}s>30')
    if x.date_key in ('20200303', '20200315'):
        rs.append('event_outside_downloaded_13:30-16:30_window')
    return ';'.join(rs)
E['drop_reasons'] = E.apply(reasons, axis=1)
E['drop_timing'] = (E.drop_reasons != '').astype(int)
E['drop_timing_if_convention'] = ((E.start_unc_conv_s > 30) | (E.has_captions != 1) | (E.caption_overrun_s.abs() > 20)
                                  | (E.stretched_all_s > 30) | E.date_key.isin(['20200303', '20200315'])).astype(int)

# ---------------- market: coverage, BENCH-R signal, 14:20 -> end ----------------
C = pd.read_csv(os.path.join(HERE, 's3_coverage_long.csv'), dtype={'date_key': str})
m1 = load_1m()
long = []
for _, x in E.iterrows():
    d = x.date_key
    t1350 = pd.Timestamp(f'{x.date} 13:50', tz=ET); t1420 = pd.Timestamp(f'{x.date} 14:20', tz=ET)
    bbo = load_bbo(d)
    for sym in SYMS:
        k = sym.split('.')[0]
        g = m1[(m1.d == d) & (m1.symbol == sym)]
        rec = dict(date_key=d, sym=k, tick=tick(k, x.date), usd_per_tick=tick(k, x.date) * MULT[k])
        if len(g):
            bars = Bars(g)
            p0, s0 = bars.asof(t1350); p1, s1_ = bars.asof(t1420)
            eo, ed = bars.next_open(t1420)
            rec.update(p_1350=p0, stale_1350_s=s0, p_1420=p1, stale_1420_s=s1_,
                       r_1350_1420=p1 / p0 - 1 if p0 else np.nan, ticks_1350_1420=(p1 - p0) / rec['tick'],
                       entry_open_1420=eo, entry_delay_s=ed)
            for lab, tend in [('est', x._end), ('conv', x._end_conv)]:
                if pd.isna(tend):
                    continue
                xo, xd = bars.next_open(tend)
                pe, se = bars.asof(tend)
                ok = xd <= 300 if not np.isnan(xd) else False
                rec.update({f'exit_open_after_end_{lab}': xo if ok else np.nan, f'exit_delay_{lab}_s': xd,
                            f'r_1420_end_{lab}': (xo / eo - 1) if ok and eo else np.nan,
                            f'ticks_1420_end_{lab}': (xo - eo) / rec['tick'] if ok else np.nan,
                            f'p_end_asof_{lab}': pe, f'stale_end_{lab}_s': se,
                            f'r_1420_end_close_{lab}': pe / p1 - 1 if p1 else np.nan})
        b = bbo[(bbo.symbol == sym)].set_index('t').sort_index() if bbo is not None else None
        if b is not None and ((b.index >= t1350 - pd.Timedelta('20min')) & (b.index < t1350 + pd.Timedelta('160min'))).sum() >= 100:
            grid = pd.date_range(pd.Timestamp(f'{x.date} 13:30', tz=ET), pd.Timestamp(f'{x.date} 16:30', tz=ET), freq='1s')
            q = b[['bid_px_00', 'ask_px_00']].reindex(grid, method='ffill')
            spr = (q.ask_px_00 - q.bid_px_00) / rec['tick']
            for lab, a0, a1 in [('1350_1420', t1350, t1420), ('1420_end', t1420, x._end)]:
                if pd.isna(a1):
                    continue
                s = spr[(spr.index >= a0) & (spr.index < a1)].dropna()
                s = s[s > 0]
                if len(s):
                    rec[f'spread_ticks_med_{lab}'] = float(s.median()); rec[f'spread_ticks_mean_{lab}'] = float(s.mean())
                    rec[f'spread_1tick_share_{lab}'] = float((s <= 1.0001).mean())
                    rec[f'half_spread_usd_mean_{lab}'] = float(s.mean() / 2 * rec['usd_per_tick'])
        long.append(rec)
L = pd.DataFrame(long).merge(C, on=['date_key', 'sym'], how='left')
L.to_csv(os.path.join(HERE, 'events_market_long.csv'), index=False)

# wide market columns
W = E[['date_key']].copy()
for k in ['ZT', 'ZF', 'ZN', 'ES']:
    l = L[L.sym == k].set_index('date_key')
    for c_src, c_dst in [('n_1m_bars', 'n_1m_bars_1330_1630'), ('n_missing_minutes', 'n_missing_min'), ('n_instrument_ids', 'n_instrument_ids'),
                         ('instrument_ids', 'instrument_id'), ('r_1350_1420', 'r_1350_1420'), ('ticks_1350_1420', 'ticks_1350_1420'),
                         ('r_1420_end_est', 'r_1420_end'), ('ticks_1420_end_est', 'ticks_1420_end'), ('r_1420_end_conv', 'r_1420_end_conv'),
                         ('spread_ticks_med_1420_end', 'spread_ticks_med_1420_end'), ('half_spread_usd_mean_1420_end', 'half_spread_usd_mean_1420_end')]:
        if c_src in l:
            W[f'{k.lower()}_{c_dst}'] = W.date_key.map(l[c_src])
for k in ['zt', 'zf', 'zn', 'es']:
    W[f'{k}_instrument_id'] = W[f'{k}_instrument_id'].map(lambda v: '' if pd.isna(v) else str(v).replace('.0', ''))
W['zt_tick_pts'] = W.date_key.map(L[L.sym == 'ZT'].set_index('date_key').tick)
W['zt_usd_per_tick'] = W.date_key.map(L[L.sym == 'ZT'].set_index('date_key').usd_per_tick)
W['market_window_covers_event'] = (~E.date_key.isin(['20200303', '20200315'])).astype(int).values
# the 13:30-16:30 window does not contain the 2020-03-03 (10:00 statement, 11:00 presser) or 2020-03-15 events
for c in [c for c in W.columns if re.search(r'_(r|ticks)_1350_1420$|_(r|ticks)_1420_end(_conv)?$|_spread_|_half_spread_', c)]:
    W.loc[W.market_window_covers_event == 0, c] = np.nan
W['databento_degraded_day'] = E.date_key.isin(['20240918', '20250917']).astype(int).values

# ---------------- USMPD ----------------
U = pd.read_csv(os.path.join(HERE, 'usmpd_presser_days.csv'), dtype={'date_key': str})
keep = ['MP1', 'MP2', 'FF4', 'ED4', 'OIS1Y', 'OIS2Y', 'UST2Y', 'UST5Y', 'UST10Y', 'SPFUT']
Uk = U[['date_key', 'stmt_date_time', 'pc_date_time'] + [f'stmt_{c}' for c in keep] + [f'pc_{c}' for c in keep]]
Uk = Uk.rename(columns={'stmt_date_time': 'usmpd_stmt_time', 'pc_date_time': 'usmpd_pc_time',
                        **{f'stmt_{c}': f'usmpd_stmt_{c}' for c in keep}, **{f'pc_{c}': f'usmpd_pc_{c}' for c in keep}})

OUT = E.merge(W, on='date_key').merge(Uk, on='date_key')
OUT['era'] = np.where(OUT.date < '2020-01-01', 'pre2020', '2020_26')
OUT['sample_role'] = np.where(OUT.chair == 'Warsh', 'warsh_text_only',
                              np.where(OUT.date >= '2023-01-01', 'confirmation_2023_2026_powell', 'contaminated_2016_2022'))
cols = ['date', 'chair', 'scheduled', 'sep_meeting', 'era', 'sample_role', 'statement_release_et', 'presser_sched_et',
        'presser_start_est_et', 'start_unc_s', 'start_source', 'presser_end_est_et', 'presser_duration_min', 'qa_start_est_et',
        'drop_timing', 'drop_reasons',
        'presser_start_conv_et', 'presser_end_conv_et', 'start_unc_conv_s', 'drop_timing_if_convention',
        'presser_start_tv_et', 'presser_end_tv_et', 'start_unc_tv_s', 'v0_minus_sched_tv_s',
        'tv_gdelt_cnbc_off_s', 'tv_gdelt_cnbc_mad_s', 'tv_gdelt_cnbc_n', 'tv_gdelt_fbc_off_s', 'tv_gdelt_fbc_mad_s', 'tv_gdelt_fbc_n',
        'tv_open_cnbc_s', 'tv_open_fbc_s', 'tv_drift_s', 'tv_fbc_excluded', 'tv_archive_cnbc_off_s', 'tv_archive_fbc_off_s', 'tv_archive_bloomberg_off_s',
        'has_captions', 'first_cue_s', 'greeting_s', 'greeting_src', 'first_qa_label_s', 'last_speech_end_s', 'video_duration_s',
        'caption_overrun_s', 'cues_after_video_end', 'n_stretched_open', 'stretched_all_s', 'opening_text_match',
        'calendar_heading', 'calendar_source', 'statement_release_source', 'video_page'] + \
       [c for c in W.columns if c != 'date_key'] + [c for c in Uk.columns if c != 'date_key']
OUT = OUT[cols]
OUT.to_csv(os.path.join(HERE, 'events.csv'), index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 100)
print(OUT[['date', 'chair', 'presser_start_est_et', 'start_unc_s', 'presser_end_est_et', 'v0_minus_sched_tv_s', 'drop_timing',
           'drop_timing_if_convention', 'drop_reasons', 'zt_ticks_1350_1420', 'zt_ticks_1420_end']].to_string())
print('drop_timing', OUT.drop_timing.sum(), '| drop_if_convention', OUT.drop_timing_if_convention.sum())
