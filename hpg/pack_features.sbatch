#!/bin/bash
#SBATCH --job-name=fedpack
#SBATCH --account=ai-workshop
#SBATCH --qos=ai-workshop
#SBATCH --partition=hpg-default
#SBATCH --cpus-per-task=2
#SBATCH --mem=8gb
#SBATCH --time=00:30:00
#SBATCH --output=fedpack_%j.log
# Last HiPerGator step, after the feature chain (run_everything.sbatch) has finished. Submit from the repo root:
#   sbatch hpg/pack_features.sbatch
#  1. prints the feature status and checks that every Powell meeting finished asr, turns, diarize, voice and face
#  2. packs the feature tables (no video, audio or frame images; about 150 MB) into ~/fedpress_features.tgz
# The backtest itself does not run here: it joins the features to licensed Databento prices, which stay on the
# machine that licensed them and are never copied to HiPerGator (pre-registration section 9). Copy the archive
# back and run backtests/run_all_backtests.sh there. Exit 3 = archive written but some Powell meeting is incomplete.
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
export USER="${USER:-$(id -un)}"
export FP_GROUP=ai-workshop
export FEDPRESS_ROOT="/blue/ai-workshop/$USER/fedpress"
export FP_PKG="$PWD/hpg/fedpress_pkg"
OUT="${OUT:-$HOME/fedpress_features.tgz}"
source hpg/fedpress_pkg/slurm/common.sh
fp_activate                                   # also cd's into the package folder

python slurm/status.py | tail -n 30 || true
python slurm/status.py --failed | head -n 60 || true

# every Powell meeting of the sample must have an ok done-marker for each speech and face stage
rc=0
python - <<'EOF' || rc=3
import json, sys
from pathlib import Path
from fedpress.config import load
from fedpress import manifest as mf

cfg = load()
root = Path(cfg.root_path("meetings"))
stages = ("asr", "turns", "diarize", "voice", "face")
powell = [m.presser_id for m in mf.sample(cfg) if m.chair == "Powell"]
missing = []
for pid in powell:
    for st in stages:
        p = root / pid / "_done" / f"{st}.json"
        status = json.loads(p.read_text()).get("status") if p.exists() else "missing"
        if status != "ok":
            missing.append(f"{pid}:{st}={status}")
print(f"Powell meetings in the sample: {len(powell)}; incomplete stage results: {len(missing)}")
for m in missing:
    print("  " + m)
sys.exit(1 if missing else 0)
EOF

cd "$FEDPRESS_ROOT"
extra=(); [ -f cache/models_lock.json ] && extra=(cache/models_lock.json)   # model revisions, checked by the backtest
tar czf "$OUT" --exclude='raw/video.mp4' --exclude='audio/audio_16k.wav' --exclude='frames/frames_1fps.zip' \
  --exclude='_claims' --exclude='*.part' meetings "${extra[@]}"
sha256sum "$OUT"
ls -lh "$OUT"
echo "copy to the PC (Git Bash there):  mkdir -p /c/fedpress_hpg && scp $USER@hpg.rc.ufl.edu:$OUT /c/fedpress_hpg/"
[ "$rc" = 0 ] || echo "WARNING: some Powell meetings are incomplete (listed above); the archive holds what exists"
exit "$rc"
