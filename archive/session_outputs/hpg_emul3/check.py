import csv, json, re, sys
from pathlib import Path

PRICE = re.compile(r"(^|_)(px|price|prices)(_\d+)?$", re.I)
EXACT = {"open", "high", "low", "close", "bid", "ask", "mid", "vwap", "settle", "last", "price", "px"}
PIXEL = re.compile(r"(^|_)[hw]_px$", re.I)            # image sizes in pixels (fedpress face gates), not prices


def names(p: Path):
    try:
        return _names(p)
    except Exception as e:                          # an unreadable table is withheld, not guessed
        return [f"<unreadable: {type(e).__name__}>"]


def _names(p: Path):
    if p.suffix == ".csv":
        with open(p, newline="", encoding="utf-8", errors="replace") as f:
            return next(csv.reader(f), [])
    if p.suffix == ".parquet":
        import pyarrow.parquet as pq
        return pq.read_schema(p).names
    if p.suffix == ".json":
        out = []
        def walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    out.append(str(k)); walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(json.loads(p.read_text(encoding="utf-8")))
        return out
    return []


bad = []
for rel in Path(sys.argv[1]).read_text().split():
    hit = sorted({n for n in names(Path(rel))
                  if (PRICE.search(n) and not PIXEL.search(n)) or n.lower() in EXACT or n.startswith("<unreadable")})
    if hit:
        bad.append(f"{rel}\t{','.join(hit[:6])}")
Path(sys.argv[2]).write_text("".join(b + "\n" for b in bad))
