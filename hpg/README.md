# HiPerGator quick start: recordings and audio

This job downloads every FOMC press-conference recording (95 videos, 2011-2026, about 65 GB) and extracts 16 kHz mono audio (FLAC, about 2-3 GB). It also fetches the caption files and transcript PDFs. Everything runs on CPU nodes, so it never waits in the B200 queue.

## Run it (about 30-60 minutes)

Log in yourself (Duo), then run:

```bash
ssh <gatorlink>@hpg.rc.ufl.edu
```

```bash
mkdir -p /blue/jie.xu/$USER && cd /blue/jie.xu/$USER
```

```bash
git clone -b review/strategy-01 https://github.com/savioxavier/gator-quant-hacks.git && cd gator-quant-hacks
```

```bash
sbatch hpg/fetch_audio.sbatch
```

Watch it:

```bash
squeue -u $USER
```

```bash
tail -f fedpress_fetch_*.log
```

## Output, under /blue/jie.xu/$USER/fedpress

| Folder | Contents |
|---|---|
| `video/` | `YYYYMMDD.mp4`, the Board's recording (largest rendition up to 960x540) |
| `audio/` | `YYYYMMDD.flac`, 16 kHz mono, the input for the voice models |
| `captions/` | Official WebVTT files (83 meetings have them) |
| `transcripts/` | Official transcript PDFs |
| `manifest/` | `pressers.csv` (one row per press conference: chair, times, URLs, sizes), `fetch_report.csv` (audio duration per meeting) |

## Settings

- `ONLY_STUDY=1` downloads only the 2016+ study sample (75 press conferences).
- `NPAR` sets the number of parallel downloads and ffmpeg processes.
- `FEDPRESS_ROOT` changes the output root.

For example:

```bash
sbatch --export=ALL,ONLY_STUDY=1 hpg/fetch_audio.sbatch
```

## Notes

- The first run builds a small conda environment on /blue (python, ffmpeg, aria2). Later runs reuse it.
- The job is re-runnable. Finished files are skipped and partial downloads resume.
- The video and caption links are signed and expire after a few hours, so the job rebuilds the manifest every time it starts (`build_manifest.py`, standard-library Python only).
- If `jie.xu` is a secondary group for you, keep `--account=jie.xu` (already set).
- If the burst QOS `jie.xu-b` is busy, edit the sbatch file to use `--qos=jie.xu`.
- The recordings are public-domain works of the US government (federalreserve.gov). They stay on /blue and are not committed to git.
- The voice, face and text feature stages, which use the B200s with at most 2 GPUs, follow in this folder next. They read `audio/`, `video/`, `captions/` and `transcripts/` from the same root.
