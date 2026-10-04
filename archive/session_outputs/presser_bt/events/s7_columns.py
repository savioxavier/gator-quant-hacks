"""Write events_columns.csv: one line per events.csv column with its definition and source."""
import os, re
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
E = pd.read_csv(os.path.join(HERE, 'events.csv'), nrows=1)
D = {
 'date': 'Press-conference date (ET).',
 'chair': 'Chair on that date from the federalreserve.gov board-membership Chairs table: Yellen 2014-02-03..2018-02-03, Powell 2018-02-05..2026-05-22, Warsh 2026-05-22..',
 'scheduled': '1 = regularly scheduled FOMC meeting; 0 = unscheduled (2020-03-03, 2020-03-15). Source: federalreserve.gov calendars.',
 'sep_meeting': '1 = meeting with a Summary of Economic Projections (calendar asterisk 2021+; SEP compilation/projection tables 2016-2020). March 15 2020 had none.',
 'era': 'pre2020 vs 2020_26 split for BENCH-R (plan).',
 'sample_role': 'contaminated_2016_2022 (FOMC-RoBERTa labelled data through 2022) / confirmation_2023_2026_powell / warsh_text_only.',
 'statement_release_et': 'FOMC statement release time ET (press-release feed; also USMPD statement timestamp). 14:00 except 2020-03-03 10:00 and 2020-03-15 17:00.',
 'presser_sched_et': 'Scheduled press-conference start (Fed press releases; USMPD presser timestamp).',
 'presser_start_est_et': 'Best estimate of the wall-clock time of the chair\'s first audible words (greeting). TV-anchored where TV evidence exists, else convention. See start_source.',
 'start_unc_s': 'Uncertainty (s) of presser_start_est_et: sqrt(lag band half-width^2 + station disagreement^2 + within-station spread^2) for TV; for convention, |TV-implied offset| + lag half-width, or the p90 of that over TV-checked meetings when no TV evidence exists.',
 'start_source': 'Source of presser_start_est_et.',
 'presser_end_est_et': 'Estimated end: same anchor as the start + end of the last caption speech cue (no captions: + video duration).',
 'presser_duration_min': 'presser_end_est_et - presser_start_est_et, minutes.',
 'qa_start_est_et': 'Estimated wall-clock time of the first non-chair speaker label (start of Q&A) on the same anchor.',
 'drop_timing': '1 = drop from timing-sensitive tests (H1-primary/H1-answer next-open fills): reasons in drop_reasons (plan rule start uncertainty > 30 s, plus no captions, distorted caption timeline, event outside downloaded market window).',
 'drop_reasons': 'Semicolon list of reasons for drop_timing.',
 'presser_start_conv_et': 'Convention: scheduled start (14:30:00) + caption greeting cue (no captions: + median greeting cue of captioned meetings).',
 'presser_end_conv_et': 'Convention: scheduled start + end of last caption speech cue (no captions: + video duration).',
 'start_unc_conv_s': 'Evidence-based uncertainty of the convention start (see start_unc_s).',
 'drop_timing_if_convention': 'Drop flag if the convention timing were used instead of the TV anchor.',
 'presser_start_tv_et': 'TV-anchored start (V0_tv + greeting cue), blank when no TV evidence.',
 'presser_end_tv_et': 'TV-anchored end.',
 'start_unc_tv_s': 'Uncertainty of the TV-anchored start.',
 'v0_minus_sched_tv_s': 'TV-implied wall-clock of caption-video zero minus scheduled start, after subtracting the assumed TV/caption lag (convention assumes 0).',
 'tv_gdelt_cnbc_off_s': 'GDELT TV API, CNBC: median over caption blocks of (block start - scheduled start) - caption time of the block\'s first words = V0 + lag - sched.',
 'tv_gdelt_cnbc_mad_s': 'Median absolute deviation of the CNBC block offsets.',
 'tv_gdelt_cnbc_n': 'Number of CNBC blocks matched to caption words.',
 'tv_gdelt_fbc_off_s': 'As tv_gdelt_cnbc_off_s for FOX Business.', 'tv_gdelt_fbc_mad_s': 'MAD, FOX Business.', 'tv_gdelt_fbc_n': 'Blocks matched, FOX Business.',
 'tv_gdelt_cnbc_open_s': 'No-caption meetings: CNBC block time of the chair\'s first transcript words minus scheduled start (includes lag).',
 'tv_gdelt_fbc_open_s': 'As above for FOX Business.',
 'tv_open_cnbc_s': 'CNBC (GDELT) TV time of the first transcript word of the chair minus scheduled start, includes lag, from blocks matched to unique 5-word transcript sequences in the first 150 words (word index / chair speech rate), calibrated (-3.9 s) against the caption-based TV start on clean-caption meetings; used for no-caption and distorted-caption meetings.',
 'tv_open_fbc_s': 'As tv_open_cnbc_s for FOX Business (calibration -3.4 s).',
 'tv_drift_s': 'Change of the TV-vs-caption offset from the first to the last 10 minutes of the presser (Internet Archive segments; CNBC, else FBC). Near 0 = caption timeline linear and uncut against live TV.',
 'tv_fbc_excluded': '1 = FOX Business offsets disagree with CNBC by > 12 s and were excluded (FBC captions ran about 30 s later than CNBC from late 2022 to early 2025).',
 'tv_archive_cnbc_off_s': 'Internet Archive TV item pages (60 s caption segments), CNBC: V0 + delay - sched; differs from GDELT by about -14 s (calibrated on overlapping meetings).',
 'tv_archive_fbc_off_s': 'As above, FOX Business.', 'tv_archive_bloomberg_off_s': 'As above, Bloomberg TV.',
 'has_captions': '1 = official WebVTT caption track exists for the federalreserve.gov video.',
 'first_cue_s': 'First caption cue time (s from video zero).',
 'greeting_s': 'Caption time of the chair\'s first words (greeting cue, matched to transcript opening).',
 'greeting_src': 'greeting cue / first chair speech cue when there is no greeting.',
 'first_qa_label_s': 'Caption time of the first non-chair speaker label after the opening.',
 'last_speech_end_s': 'End time of the last caption speech cue.',
 'video_duration_s': 'Brightcove video duration.',
 'caption_overrun_s': 'last_speech_end_s - video_duration_s (captions extending past the video = distorted caption timeline).',
 'cues_after_video_end': 'Caption cues starting after the video ends.',
 'n_stretched_open': 'Stretched cues (>8 s, <0.6 words/s) inside the opening statement.',
 'stretched_all_s': 'Total seconds of stretched cues in the whole caption track.',
 'opening_text_match': 'Share of the first 12 caption words after the greeting found in the first 20 transcript words.',
 'calendar_heading': 'Meeting heading/date label on the federalreserve.gov calendar.', 'calendar_source': 'Calendar page URL.',
 'statement_release_source': 'Source of the statement time.', 'video_page': 'federalreserve.gov press-conference page.',
 'zt_tick_pts': 'ZT minimum tick in points: 1/128 through 2018, 1/256 from 2019 (checked in the data: no odd 1/256 prices on presser days through 2018-12-19, present from 2019-01-30).',
 'zt_usd_per_tick': 'ZT $ per tick per contract ($200,000 face, 1 point = $2,000): $15.625 through 2018, $7.8125 from 2019.',
 'market_window_covers_event': '0 for 2020-03-03 (statement 10:00, presser 11:00) and 2020-03-15 (Sunday) whose events fall outside the downloaded 13:30-16:30 ET window.',
 'databento_degraded_day': 'Databento reported reduced quality for GLBX.MDP3 on this day (2024-09-18, 2025-09-17).',
 'usmpd_stmt_time': 'USMPD statement timestamp (ET).', 'usmpd_pc_time': 'USMPD press-conference timestamp (scheduled minute).',
}
pat = [
 (r'^(zt|zf|zn|es)_n_1m_bars_1330_1630$', '1m bars present 13:30-16:30 ET (max 180; a minute without trades has no bar; ES halted 16:15-16:30 before mid-2021).'),
 (r'^(zt|zf|zn|es)_n_missing_min$', 'Minutes without a 1m bar in 13:30-16:30 ET.'),
 (r'^(zt|zf|zn|es)_n_instrument_ids$', 'Distinct instrument_ids of the .v.0 series inside the window (1 = no roll inside the window).'),
 (r'^(zt|zf|zn|es)_instrument_id$', 'Databento instrument_id of the volume-ranked front (.v.0) that day (matches symbology.resolve).'),
 (r'^(zt|zf|zn|es)_r_1350_1420$', 'BENCH-R signal: close of last 1m bar completed by 14:20:00 / close of last bar completed by 13:50:00 - 1 (simple return).'),
 (r'^(zt|zf|zn|es)_ticks_1350_1420$', 'Same move in ticks.'),
 (r'^(zt|zf|zn|es)_r_1420_end$', '14:20 -> presser end: open of first 1m bar starting >= 14:20:00 to open of first bar starting >= presser_end_est_et (next 1m open after the end) - 1.'),
 (r'^(zt|zf|zn|es)_ticks_1420_end$', 'Same move in ticks.'),
 (r'^(zt|zf|zn|es)_r_1420_end_conv$', 'As r_1420_end but exit at the next 1m open after presser_end_conv_et.'),
 (r'^(zt|zf|zn|es)_spread_ticks_med_1420_end$', 'Median quoted bid-ask spread in ticks, bbo-1s forward-filled per second, 14:20 -> presser end.'),
 (r'^(zt|zf|zn|es)_half_spread_usd_mean_1420_end$', 'Mean half-spread in $ per contract over 14:20 -> presser end (bbo-1s).'),
 (r'^usmpd_stmt_(.*)$', 'USMPD statement window (-10/+20 min) change: rates in percentage points, SPFUT in percent.'),
 (r'^usmpd_pc_(.*)$', 'USMPD press-conference window (-10/+60 min from scheduled start) change: rates in percentage points, SPFUT in percent.'),
]
rows = []
for c in E.columns:
    desc = D.get(c)
    if desc is None:
        for p, dsc in pat:
            if re.match(p, c):
                desc = dsc; break
    rows.append(dict(column=c, definition=desc or ''))
pd.DataFrame(rows).to_csv(os.path.join(HERE, 'events_columns.csv'), index=False)
print('undocumented:', [r['column'] for r in rows if not r['definition']])
