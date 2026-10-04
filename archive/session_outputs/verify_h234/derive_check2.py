"""Would h4_answer_rows.csv (y = 1e4 ln(exit/entry), not git-ignored under backtest_h234*/results) plus a per-trade tick
table (h234_extra strategy_per_trade_no_prices.csv, C0_ticks) give back price levels?"""
import numpy as np
import pandas as pd

b = pd.read_parquet("<home>/.cache/gqh/presser/ohlcv-1m__all_2016_2026.parquet", columns=["open", "close"])
LV = np.array(sorted(set(np.round(b.open, 9)) | set(np.round(b.close, 9))))
h4 = pd.read_csv("../team_push/backtests/presser/backtest_h234_local/results/h4_answer_rows.csv", dtype={"answer_id": str})
h4 = h4[h4.sym == "ZT"]
st = pd.read_csv("../h234_extra/out/strategy_per_trade_no_prices.csv", dtype={"answer_id": str})
print(st.strategy.value_counts().to_dict())
m = st.merge(h4[["answer_id", "y"]], on="answer_id")
m = m[(m.C0_ticks != 0) & (m.y != 0)]
tick = 1 / 256
move = m.C0_ticks / m.pos
e = move * tick / np.expm1(m.y / 1e4)
sn = np.round(e / tick) * tick
print(dict(rows=len(m), on_tick_grid=int((np.abs(e - sn) < 1e-6 * e).sum()),
           equal_to_a_1m_bar_level=int(np.isin(np.round(sn, 9), LV).sum())))
