import sys, runpy
pkg = sys.argv.pop(1)
sys.path.insert(0, pkg)
src = open(sys.argv[1], encoding="utf-8").read().replace("PKG = Path(__file__).resolve().parents[1]", f"PKG = Path(r'{pkg}')")
sys.argv = sys.argv[1:]
code = compile(src, "status_fixed.py", "exec")
g = {"__name__": "__main__", "__file__": "status_fixed.py"}
try:
    exec(code, g)
except SystemExit as e:
    raise
