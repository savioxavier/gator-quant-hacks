# Press-conference manifest

Built 2026-10-03 from the Board of Governors' website and the Brightcove playback API used by the
federalreserve.gov video player. Every URL was checked with HEAD (or a 1-byte range request where HEAD gave no
length); no video was downloaded.

| File | What it holds |
|---|---|
| `pressers.csv` | One row per FOMC press conference held: 95 rows, 2011-04-27 to 2026-09-16 |
| `meetings.csv` | One row per entry on the Board's meeting calendars 2011-2027: 148 rows (meetings, conference calls, notation votes, the cancelled March 2020 meeting), with a presser flag |
| `check.json` | Build record: HTTP status, byte count and method of every probe, chair source, page titles, summary |
| `build_manifest.py` | The builder (standard library only, Python 3.11+). Re-run it to refresh or extend the manifest |

## Counts

| Chair | Pressers | Dates | Default sample | Video hours | MP4 bytes (chosen rendition) |
|---|---|---|---|---|---|
| Bernanke | 12 | 2011-04-27 to 2013-12-18 | 0 | 11.42 | 9,397,708,110 |
| Yellen | 16 | 2014-03-19 to 2017-12-13 | 8 | 15.64 | 12,400,759,454 |
| Powell | 64 | 2018-03-21 to 2026-04-29 | 64 | 53.41 | 43,997,785,459 |
| Warsh | 3 | 2026-06-17 to 2026-09-16 | 3 | 1.94 | 1,595,984,519 |
| **All** | **95** | | **75** | **82.40** | **67,392,237,542 (62.8 GiB)** |

Default sample (`in_default_sample`, 2016-01-01 to 2026-10-31, the window in `team_FINAL_PLAN.md`): 75 held
pressers (73 scheduled plus the unscheduled 2020-03-03 and 2020-03-15), 63.1 video hours, 51,980,849,234 bytes
(48.4 GiB). `meetings.csv` gives the plan's 88 policy meetings for the same window: 87 scheduled or equivalent
plus the extra 2-3 March 2020 meeting. Of these, 75 have a held presser, 12 are 2016-2018 meetings that had
no presser, and 2026-10-28 has not happened yet.

All 95 rows have a verified page, transcript PDF and MP4. 83 have an official WebVTT caption track. The 95
transcript PDFs total 16.1 MB and the 83 caption files total 7.2 MB.

## `pressers.csv` columns

| Column | Meaning |
|---|---|
| `presser_id` | `YYYYMMDD` of the presser, as used in the Fed file names (`FOMCpresconfYYYYMMDD.pdf`). Read it as a string |
| `meeting_date` | Last day of the policy meeting as listed by the Board. It equals `presser_date` except for 2020-03-03, whose unscheduled meeting is listed as March 2 |
| `meeting_start_date` | First day of the meeting (two-day meetings start the day before) |
| `presser_date` | Date of the press conference (ISO) |
| `chair` | Bernanke, Yellen, Powell or Warsh, taken from the transcript title ("Transcript of Chair Powell's Press Conference"). The builder falls back to a date rule when no transcript text is available |
| `scheduled` | false only for 2020-03-03 and 2020-03-15, which the Board lists as unscheduled. 2020-03-15 replaced the cancelled March 17-18 meeting |
| `sep` | A Summary of Economic Projections was released at this meeting. Taken from the listing pages: the asterisk on `fomccalendars.htm`, SEP links on the historical pages. Agrees with the USMPD SEP flag on all 95 rows: 62 true, 33 false |
| `statement_time_et` | Scheduled release time of the statement (ET, 24-hour). 2011-2012: 12:30; 2013 onward: 14:00; 2020-03-03: 10:00; 2020-03-15: 17:00 |
| `presser_start_et` | **Nominal** start (ET): 14:15 for 2011-2012, 14:30 from 2013-03-20, 11:00 on 2020-03-03, 18:30 on 2020-03-15. This is the scheduled time, not a measured one |
| `time_source` | `<statement source>\|<presser source>`. `statement_release` is the "For release at" line of the statement press release (2016 onward and both 2020 specials). `era_rule` is the Board schedule announced 2011-03-24 (`monetary20110324a.htm`) and 2013-03-13 (`monetary20130313a.htm`). `board_announcement` is the same two releases for the presser start. `usmpd` is the SF Fed USMPD minute for the two unscheduled pressers. All 95 rows agree with the USMPD statement and presser minutes |
| `in_default_sample` | presser_date within 2016-01-01..2026-10-31. A convenience flag only: the package config decides the sample |
| `fed_page_url` | Press-conference page. 2026-01-28 uses the Board's misspelt URL `fomcpressconf20260128.htm` |
| `statement_url` | Statement press release (HTML) |
| `transcript_pdf_url`, `transcript_pdf_bytes` | Official transcript PDF and its HEAD Content-Length |
| `vtt_url`, `vtt_bytes` | Official WebVTT caption track and its size; empty when Brightcove has no caption track. **Signed URL, expires** (see below) |
| `brightcove_account_id`, `brightcove_video_id` | Stable identifiers of the official video (account 66043936001). Use these to download |
| `mp4_url` | Chosen MP4 rendition. **Signed URL, expires** |
| `mp4_width`, `mp4_height`, `mp4_avg_bitrate` | Chosen rendition (bitrate in bit/s as reported by Brightcove) |
| `mp4_bytes` | HEAD Content-Length of `mp4_url`. It equals the playback API `size` except on 2026-03-18, where HEAD reports 63 more bytes; HEAD is kept |
| `mp4_rule` | `max_within_960x540` (94 rows) or `above_cap_highest` (2015-12-16, whose only rendition is 1280x720) |
| `mp4_renditions` | All MP4 renditions offered, largest first |
| `signed_url_expires_utc` | Expiry decoded from the `fastly_token` of `mp4_url`, about 6 hours after the build |
| `duration_s` | Video duration from the playback API (ms / 1000) |
| `bc_created_at` | Brightcove `created_at`. This is an **upload** time, not a broadcast clock: same-day uploads land a median of about 16 minutes after the scheduled start, and some videos were uploaded days later |
| `local_pdf_path`, `local_txt_path`, `local_vtt_path` | Copies already on the research PC, as paths relative to `--local-root` (here the research session's `fedtalk/` scratch folder, so `data_markets/pdf/...`, `data_markets/vtt/...`). The `.txt` files are text extracted from the PDFs. These files are not on HiPerGator unless they are copied there; the transcript PDFs and captions can also be fetched from the URLs |
| `local_pdf_sha256`, `local_vtt_sha256` | SHA-256 of those copies, for checking fresh downloads. The VTT hash is computed after CRLF->LF normalisation, which gives the bytes as the server sends them, because the local copies were saved with Windows line endings |
| `local_pdf_matches_remote`, `local_vtt_matches_remote` | Local size (VTT normalised as above) equals the remote Content-Length. True for 95/95 PDFs and 83/83 VTTs |
| `checked_at_utc` | When the row's probes ran |
| `notes` | Exceptions; see Gaps |

MP4 rule: among the HTTPS MP4 renditions, take the one with the largest pixel area within 960x540 (width
<= 960 and height <= 540), breaking ties by bitrate. If every rendition is larger than the cap, take the
highest available. The resulting renditions are 81 x 960x540, 9 x 640x360, 3 x 720x404 (2011), 1 x 480x270
(2012-01-25, the only rendition offered) and 1 x 1280x720 (2015-12-16).

## Signed URLs: resolve at download time

`mp4_url` and `vtt_url` carry a `fastly_token` that expires about 6 hours after the playback API call. They
prove that the file existed on the build date; they are not download links. The download stage must re-resolve
each video from `brightcove_account_id` and `brightcove_video_id`:

```
GET https://players.brightcove.net/66043936001/default_default/config.json   -> video_cloud.policy_key (public)
GET https://edge.api.brightcove.com/playback/v1/accounts/66043936001/videos/<brightcove_video_id>
    Accept: application/json;pk=<policy_key>
    -> sources[] (MP4 renditions: width, height, avg_bitrate, size, src), text_tracks[] (kind == "captions")
```

Apply the MP4 rule above to `sources`, then check that the downloaded size equals `mp4_bytes`. The policy key
is the public key that the federalreserve.gov player sends to every visitor. It is not a credential and is
not stored in this package. `build_manifest.py` re-runs the same calls.

## `meetings.csv` columns

`meeting_start_date`, `meeting_date` (last day); `kind` (`scheduled` 135, `unscheduled` 5, `notation_vote` 5,
`conference_call` 2, `cancelled` 1); `sep`; `has_presser`; `presser_date`; `chair` (date rule); `statement_url`
(empty when the Board lists none); `in_default_sample` (meeting_date in 2016-01-01..2026-10-31 and scheduled or
with a presser; 88 rows); `held` (meeting_date on or before the build date and not cancelled; only 2026-10-28 is
in the sample but not yet held); `listing_url`.

## Gaps and caveats

- **No caption track (12):** 2011-04-27, 2011-11-02, 2012-01-25, 2012-06-20, 2013-12-18, 2022-12-14, 2023-06-14,
  2023-07-26, 2023-11-01, 2023-12-13, 2024-03-20, 2025-12-10. Brightcove offers only thumbnail metadata tracks
  for these. Seven are in the default sample. This matters only when the optional WebVTT clock source is on: the
  default clock is Whisper plus the transcript PDF, which covers all 95.
- **No wall-clock anchor.** `presser_start_et` is the scheduled minute. Video time zero is not the scheduled
  start: the chair's greeting falls 0.6-144 s into the video (median 11.8 s, from the 83 caption files). The VOD
  streams carry no program-date-time tags, and `bc_created_at` is an upload time. Per-meeting offsets must come
  from another source, as in the plan's start-time rule.
- **Statement time, 2012.** The presser pages list the statement as released at 12:20 (2012-01-25) and 12:35
  (2012-04-25, 06-20, 09-13). The Board's schedule and USMPD both say 12:30, so the manifest keeps 12:30 and
  records the page value in `notes`. Both are before the 14:15 presser and do not affect Q&A timing.
- **Upcoming pressers.** 2026-10-28 is in the default window but not yet held, and 2026-12-09 is outside it.
  Re-run the builder after each presser: it picks up the new listing entry and appends the row.
- **Warsh start date.** 2026-05-22 comes from news reports; no Board release was found. It is used only as the
  chair date-rule fallback. No presser falls between 2026-04-29 (last Powell) and 2026-06-17 (first Warsh), and
  the transcript titles give the chair on all 95 rows.
- **2015-12-16** offers only a 1280x720 rendition (909 MB). Frame sampling at 1 fps should downscale it to match
  the other meetings.
- **Video size varies:** 14 videos are not 960x540, and in each case the chosen rendition is the largest
  offered. Three are 720x404 (2011). Nine are 640x360: 2012-09-13, 2013-03-20, 06-19 and 09-18, 2014-06-18,
  09-17 and 12-17, 2015-09-17, 2016-09-21. 2012-01-25 is 480x270 and 2015-12-16 is 1280x720. In the default
  sample only 2016-09-21 (Yellen) is not 960x540. Face features should therefore record frame size and
  face-box pixels, and the voice stage should log the audio codec and bitrate.
- **Durations** run from 13.9 min (2020-03-03) to 76.1 min. They agree with transcript lengths: 125-187
  transcript words per video minute, median 169, so none of the videos looks truncated.
- **2026-03-18:** HEAD reports 63 more bytes than the API `size` (noted in the row). Verify downloads against
  the HEAD value.

## Rebuild or extend

```
python manifest/build_manifest.py                      # live: listing pages, Brightcove API, HEAD probes
python manifest/build_manifest.py --offline            # rebuild from the page cache, no network
python manifest/build_manifest.py --local-root DIR     # also fill local_* columns from files under DIR
python manifest/build_manifest.py --usmpd-times CSV    # cross-check times and SEP against USMPD
```

Outputs go to the script's folder unless `--out-dir` is given, and they overwrite the shipped files. An
`--offline` run makes no probes and therefore writes no byte counts, so point it at another folder with
`--out-dir`. The page cache defaults to `~/.cache/fed_presser_manifest` and is safe to delete. A live run makes about 600
small requests at 0.3 s spacing, about 5 minutes. Run it on a login node or in a CPU job: it needs outbound
HTTPS to www.federalreserve.gov, players.brightcove.net, edge.api.brightcove.com and brightcovecdn.com. On
HiPerGator there are no local copies, so the `local_*` columns come out empty.

## Sources and licence

- Board pages and files are public domain unless marked (https://www.federalreserve.gov/disclaimer.htm); the
  Board asks for attribution. Do not use YouTube or C-SPAN copies.
- Listing pages: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm and
  https://www.federalreserve.gov/monetarypolicy/fomchistorical2011.htm ... `fomchistorical2020.htm`.
- Time announcements: https://www.federalreserve.gov/newsevents/pressreleases/monetary20110324a.htm,
  https://www.federalreserve.gov/newsevents/pressreleases/monetary20130313a.htm.
- SF Fed US Monetary Policy Event-Study Database (cross-check only):
  https://www.frbsf.org/research-and-insights/data-and-indicators/us-monetary-policy-event-study-database/

## `label_dates.parquet` (stance training labels, deviation D1a)

One row per row of `gtfintechlab/fomc_communication` (train + test, revision `6b0283f5`, 2,480 rows) with the
date of the earliest source document that contains the sentence (`source_date`, `source_doc_id`,
`match_method`), found in the authors' per-document files at github.com/gtfintechlab/fomc-hawkish-dovish commit
`98646987`. All 2,480 rows are dated; 2,336 differ from the dataset's `year` column. `fedpress/train/labels.py`
uses it when `train.stance_walkforward.data.redate.enabled` (default), checking the sha256 pinned in
`config.yaml` (`16a54100...`; also in `label_dates_meta.json`). Rebuild: `build_label_dates.py` (instructions in
its docstring; pandas + openpyxl, a sparse clone of the repository and network for the dataset CSVs). Licence:
CC BY-NC 4.0, like its sources.
