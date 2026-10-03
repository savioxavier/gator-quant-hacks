#!/usr/bin/env bash
# Download every FOMC press-conference video and extract 16 kHz mono audio, on HiPerGator CPU nodes.
#   sbatch hpg/fetch_audio.sbatch          (or: bash hpg/fetch_audio.sh inside an srundev session)
# Re-runnable: finished downloads and audio files are skipped; partial downloads resume.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${FEDPRESS_ROOT:-/blue/jie.xu/$USER/fedpress}"
NPAR="${NPAR:-8}"                   # parallel downloads and ffmpeg processes
ONLY_STUDY="${ONLY_STUDY:-0}"       # 1 = only the 2016+ study sample; 0 = all 95 (2011-2015 kept for calibration)
mkdir -p "$ROOT"/{manifest,video,audio,captions,transcripts,logs}

# 1. Environment: python, ffmpeg and aria2 from conda-forge, kept on /blue (created once).
ENV="$ROOT/env_fetch"
if [ ! -x "$ENV/bin/ffmpeg" ]; then
  type module >/dev/null 2>&1 || source /etc/profile.d/modules.sh
  module load conda
  mamba create -y -p "$ENV" -c conda-forge python=3.11 ffmpeg aria2
fi
PY="$ENV/bin/python"; FFMPEG="$ENV/bin/ffmpeg"; FFPROBE="$ENV/bin/ffprobe"; ARIA="$ENV/bin/aria2c"

# 2. Fresh manifest: the Brightcove MP4 and caption URLs are signed and expire after a few hours.
"$PY" "$HERE/build_manifest.py" --out-dir "$ROOT/manifest" --cache "$ROOT/manifest/cache" --refresh

# 3. Download list for aria2 (video, captions, transcript PDF per meeting).
"$PY" - "$ROOT" "$ONLY_STUDY" <<'EOF'
import csv, sys
root, only = sys.argv[1], sys.argv[2] == "1"
rows = list(csv.DictReader(open(f"{root}/manifest/pressers.csv", encoding="utf-8")))
if only:
    rows = [r for r in rows if r["in_default_sample"] == "true"]
with open(f"{root}/manifest/aria2_input.txt", "w", encoding="utf-8") as f:
    for r in rows:
        d = r["presser_id"]
        for url, sub, name in ((r["mp4_url"], "video", f"{d}.mp4"), (r["vtt_url"], "captions", f"{d}.vtt"),
                               (r["transcript_pdf_url"], "transcripts", f"FOMCpresconf{d}.pdf")):
            if url:
                f.write(f"{url}\n  dir={root}/{sub}\n  out={name}\n")
print(f"{len(rows)} meetings queued")
EOF
"$ARIA" -i "$ROOT/manifest/aria2_input.txt" -j "$NPAR" -x 4 -c --auto-file-renaming=false \
  --retry-wait=10 --max-tries=8 --console-log-level=warn --summary-interval=60   || echo "WARNING: some downloads failed; re-run the job to resume them"

# 4. Check video sizes against the manifest.
"$PY" - "$ROOT" <<'EOF'
import csv, os, sys
root = sys.argv[1]
bad = []
for r in csv.DictReader(open(f"{root}/manifest/pressers.csv", encoding="utf-8")):
    p = f"{root}/video/{r['presser_id']}.mp4"
    if os.path.exists(p) and r["mp4_bytes"] and os.path.getsize(p) != int(r["mp4_bytes"]):
        bad.append((r["presser_id"], os.path.getsize(p), r["mp4_bytes"]))
print("size mismatches:", bad or "none")
EOF

# 5. Audio: 16 kHz mono FLAC (lossless, about half the size of WAV), one ffmpeg per video in parallel.
export FFMPEG ROOT
ls "$ROOT"/video/*.mp4 | xargs -P "$NPAR" -I{} bash -c '
  f="{}"; d=$(basename "$f" .mp4); out="$ROOT/audio/$d.flac"
  if [ ! -s "$out" ]; then "$FFMPEG" -nostdin -loglevel error -y -i "$f" -vn -ac 1 -ar 16000 -c:a flac "$out.tmp.flac" && mv "$out.tmp.flac" "$out" || echo "ffmpeg failed: $d"; fi'

# 6. Report.
"$PY" - "$ROOT" "$FFPROBE" <<'EOF'
import csv, glob, json, os, subprocess, sys
root, ffprobe = sys.argv[1], sys.argv[2]
rows = []
for p in sorted(glob.glob(f"{root}/audio/*.flac")):
    dur = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                         capture_output=True, text=True).stdout.strip()
    rows.append({"presser_id": os.path.basename(p)[:8], "audio_s": float(dur or 0), "audio_mb": round(os.path.getsize(p) / 1e6, 1)})
n_video = len(glob.glob(f"{root}/video/*.mp4"))
with open(f"{root}/manifest/fetch_report.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["presser_id", "audio_s", "audio_mb"]); w.writeheader(); w.writerows(rows)
print(json.dumps({"videos": n_video, "audio_files": len(rows), "audio_hours": round(sum(r["audio_s"] for r in rows) / 3600, 1),
                  "video_gb": round(sum(os.path.getsize(p) for p in glob.glob(f"{root}/video/*.mp4")) / 1e9, 1)}, indent=1))
EOF
echo "done: $ROOT"
