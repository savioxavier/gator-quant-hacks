"""Diagnosis only (not the run): execute the frozen h234_s1_features.py source in memory with ONE change, the WAV
duration read from audio.json["output"]["duration_s"] (where fedpress 436a351 writes it), into a scratch output
folder. s1 reads no market data. No frozen file is modified."""
import os, sys
CODE = os.environ["H234_CODE"]
sys.path.insert(0, CODE)
os.chdir(CODE)
src = open(os.path.join(CODE, "h234_s1_features.py"), encoding="utf-8").read()
old = 'json.loads(am.read_text(encoding="utf-8")).get("duration_s")'
new = 'json.loads(am.read_text(encoding="utf-8")).get("output", {}).get("duration_s")'
assert src.count(old) == 1
src = src.replace(old, new)
g = {"__name__": "diag", "__file__": os.path.join(CODE, "h234_s1_features.py")}
exec(compile(src, "h234_s1_features.py[diag-wavkey]", "exec"), g)
