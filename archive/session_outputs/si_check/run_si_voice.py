"""Run only the package voice stage on the source-invariance tree (FEDPRESS_ROOT must point at <fedpress-root>_si),
one meeting at a time, with the local workers' overrides and the same board-power guard as the local workers:
wait until power <= 450 W before a stage; suspend the stage's process tree if power > 490 W on 2 consecutive
0.5 s samples and resume once it stays <= 420 W for 2 s.

Usage (Git Bash):  source localfeat/fp_env.sh; export FEDPRESS_ROOT='<fedpress-root>_si'; python run_si_voice.py
"""
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil

HERE = Path(__file__).resolve().parent
LF = HERE.parent / "localfeat"
PY = str(LF / "venv" / "Scripts" / "python.exe")
OVR = json.loads((LF / "worker_0_overrides.json").read_text(encoding="utf-8"))
MEETINGS = ["20190130", "20190320", "20190619"]
WAIT_W, HIGH_W, RESUME_W = 450.0, 490.0, 420.0
LOG = HERE / "run_si_voice.log"


def log(msg):
    line = f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} {msg}"
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line, flush=True)


def power():
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=power.draw", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        return float(out.splitlines()[0])
    except Exception:
        return None


def tree(pid):
    try:
        p = psutil.Process(pid)
        return [p, *p.children(recursive=True)]
    except psutil.Error:
        return []


def run_voice(mid):
    w = power()
    while w is None or w > WAIT_W:
        log(f"wait_power {mid}: {w} W")
        time.sleep(5)
        w = power()
    cmd = [PY, "-m", "fedpress.cli", "voice", "--id", mid, "--log-format", "text"]
    for o in OVR:
        cmd += ["--set", o]
    lg_path = HERE / f"voice_{mid}.log"
    lg = lg_path.open("w", encoding="utf-8")
    t0 = time.time()
    proc = subprocess.Popen(cmd, stdout=lg, stderr=subprocess.STDOUT, cwd=str(HERE))
    samples, stop, st = [], threading.Event(), {"susp": False, "n": 0}

    def watch():
        hi = lo = 0
        while not stop.is_set():
            w = power()
            if w is not None:
                samples.append(w)
                hi = hi + 1 if w > HIGH_W else 0
                lo = lo + 1 if w <= RESUME_W else 0
                if not st["susp"] and hi >= 2:
                    for p in tree(proc.pid):
                        try:
                            p.suspend()
                        except psutil.Error:
                            pass
                    st["susp"], st["n"] = True, st["n"] + 1
                    log(f"  {mid}: power {w} W > {HIGH_W} W twice, suspended")
                elif st["susp"] and lo >= 4:
                    for p in tree(proc.pid):
                        try:
                            p.resume()
                        except psutil.Error:
                            pass
                    st["susp"] = False
                    log(f"  {mid}: power {w} W, resumed")
            stop.wait(0.5)

    th = threading.Thread(target=watch, daemon=True)
    th.start()
    rc = proc.wait(timeout=3600)
    stop.set()
    th.join()
    lg.close()
    res = {"meeting": mid, "rc": rc, "wall_s": round(time.time() - t0, 1),
           "power_max_w": max(samples) if samples else None,
           "power_mean_w": round(sum(samples) / len(samples), 1) if samples else None, "suspensions": st["n"],
           "summary": [l for l in lg_path.read_text(encoding="utf-8", errors="replace").splitlines()
                       if "run.summary" in l or "stage." in l][-3:]}
    log(json.dumps(res))
    return res


if __name__ == "__main__":
    root = os.environ.get("FEDPRESS_ROOT", "")
    if Path(root).resolve() != Path(r"<fedpress-root>_si").resolve():
        sys.exit(f"FEDPRESS_ROOT={root!r}: must be <fedpress-root>_si (the original tree is read-only)")
    log(f"start: overrides {OVR}, FEDPRESS_ROOT={root}")
    out = [run_voice(m) for m in (sys.argv[1:] or MEETINGS)]
    sys.exit(1 if any(r["rc"] for r in out) else 0)
