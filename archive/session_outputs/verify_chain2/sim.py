import sys, os
sys.path.insert(0, sys.argv[1])
from fedpress.config import load
from fedpress import manifest as mf, io
cfg = load(None, [])
# simulate: everything upstream done for every meeting; face/voice n/a for non-Powell, failed for every Powell;
# diarize failed for every meeting in variant B
variant = sys.argv[2]
for m in mf.select(cfg, all_=True):
    p = io.MeetingPaths.of(cfg, m.presser_id); p.ensure()
    for st in ("fetch", "audio", "asr", "turns"):
        io.mark_done(p, st, {"status": "ok", "outputs": []})
    io.mark_done(p, "frames", {"status": "ok" if m.chair == "Powell" else "not_applicable", "outputs": []})
    if variant == "A":
        io.mark_done(p, "diarize", {"status": "ok", "outputs": []})
        for st in ("face", "voice"):
            if m.chair == "Powell":
                io.mark_failed(p, st, {"error": "RuntimeError('simulated systemic failure')"})
            else:
                io.mark_done(p, st, {"status": "not_applicable", "outputs": []})
    else:
        io.mark_failed(p, "diarize", {"error": "RuntimeError('simulated diarize failure')"})
