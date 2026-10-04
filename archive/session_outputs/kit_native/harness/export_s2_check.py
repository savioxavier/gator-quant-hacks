"""Scratch: S2 engine held weights and net returns, to check the harness's futures roll debit and financing."""
import sys
from pathlib import Path

ROOT = Path("<solo-repo>")
sys.path.insert(0, str(ROOT))
from src import engine as E      # noqa: E402
from src import forward2 as F2   # noqa: E402

out = Path(__file__).resolve().parent
w = F2.s2_decisions("FWD")
ohlc = E.load_ohlc(F2.S1_TICKERS, "FWD")
rf = E.load_rf("FWD")
net, gross, to, held, cost = E.simulate(w, ohlc, rf, exec="next_close", cost_bps=F2.S1_COST_BPS)
held.rename_axis("date").to_csv(out / "s2_held.csv")
net.rename("ret").rename_axis("date").to_csv(out / "s2_engine_net.csv")
net0, *_ = E.simulate(w, ohlc, rf * 0.0, exec="next_close", cost_bps={t: 0.0 for t in F2.S1_TICKERS})
net0.rename("ret").rename_axis("date").to_csv(out / "s2_engine_nocost_rf0.csv")
print(held.shape, float(held.abs().sum(axis=1).max()), float(ohlc["roll"].fillna(0).values.sum()))

# S3 (next_open ETFs): engine held weights (from the open of t) and net returns, project ETF costs
w3 = F2.s3_decisions("FWD")
ohlc3 = E.load_ohlc(F2.S3_TICKERS, "FWD")
net3, _, to3, held3, _ = E.simulate(w3, ohlc3, rf, exec="next_open")
held3.rename_axis("date").to_csv(out / "s3_held.csv")
net3.rename("ret").rename_axis("date").to_csv(out / "s3_engine_net.csv")
print("S3", held3.shape, float(held3.sum(axis=1).max()), float(to3.mean() * 252))
