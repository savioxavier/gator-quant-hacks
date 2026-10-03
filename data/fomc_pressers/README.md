# FOMC press conferences: transcripts and captions

All 95 FOMC press conferences from 2011-04-27 to 2026-09-16 (Bernanke 12, Yellen 16, Powell 64, Warsh 3).

| Folder | Contents |
|---|---|
| `transcripts/` | `FOMCpresconfYYYYMMDD.pdf`: the official transcript PDFs, with speaker labels for the chair and reporters. `.txt` holds the extracted text of each PDF. |
| `captions/` | `YYYYMMDD.vtt`: the official WebVTT caption files from the Board's video player. There are 83 of them, and cue times are relative to the start of the video. `missing_captions.txt` lists the 12 meetings without a caption file. |

**Source:** federalreserve.gov, from the press-conference pages linked from the FOMC calendars. These are works of the US federal government and are in the public domain. Retrieved 2026-10-03.

**Timing convention:** published work treats video time zero as 14:30:00 ET. The real start varies, because the greeting falls 0.6-144 s into the video. Estimate a per-meeting offset before any timing-sensitive test, and drop meetings whose start is uncertain by more than 30 s (see the team plan).

## Not in this repository

- **Video and audio recordings** (95 MP4s, about 65 GB). They are too large for GitHub, whose limit is 100 MB per file. The HiPerGator pipeline downloads them from federalreserve.gov using a manifest of the video URLs. Derived chair-only voice and face features (small parquet files) can be added here after that run.
- **Futures market data** (Databento). It is licensed and must not be redistributed, so it stays in each user's local cache.
