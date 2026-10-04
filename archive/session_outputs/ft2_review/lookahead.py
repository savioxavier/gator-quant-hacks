import sys, pickle
sys.path.insert(0, r"<solo-repo>")
import numpy as np, pandas as pd
from src import engine as E, forward2 as F2, calendar_utils as CU
SP = r"<scratch>/ft2_review/"
ORIG_OHLC, ORIG_RF = E.load_ohlc, E.load_rf
base = pickle.load(open(SP + "dec_base.pkl", "rb"))
FUNCS = {"S1": lambda: F2.s1_decisions("FWD"), "S2": lambda: F2.s2_decisions("FWD"),
         "ES_10VOL": lambda: F2.es_sleeve_decisions("FWD"), "S3": lambda: F2.s3_decisions("FWD"),
         "BH5": lambda: F2.s3_decisions("FWD", buy_and_hold=True)}

def make_perturbed(cut, seed):
    cut = pd.Timestamp(cut)
    def load_ohlc(tickers=None, period="IS"):
        out = ORIG_OHLC(tickers, period)
        rng = np.random.default_rng(seed)
        close = out["close"].copy()
        after = close.index > cut
        n = int(after.sum())
        for t in close.columns:
            last = close.loc[~after, t].dropna()
            anchor = last.iloc[-1] if len(last) else 100.0
            steps = rng.normal(0, 0.015, n)
            rw = anchor * np.exp(np.cumsum(steps))
            col = close[t].to_numpy().copy()
            mask = after & ~np.isnan(col)
            col[after] = np.where(np.isnan(col[after]), np.nan, rw)
            close[t] = col
        new = dict(out)
        new["close"] = close
        for k in ("open", "high", "low"):
            o = out[k].copy(); o.loc[after] = close.loc[after] * (1 + rng.normal(0, 0.003, o.loc[after].shape))
            new[k] = o
        return new
    def load_rf(period="IS"):
        r = ORIG_RF(period).copy()
        a = r.index > cut
        r[a] = np.abs(np.random.default_rng(seed + 1).normal(0.0002, 0.0001, int(a.sum())))
        return r
    return load_ohlc, load_rf

def make_truncated(cut):
    cut = pd.Timestamp(cut)
    def load_ohlc(tickers=None, period="IS"):
        out = ORIG_OHLC(tickers, period)
        return {k: v.loc[:cut] for k, v in out.items()}
    def load_rf(period="IS"):
        return ORIG_RF(period).loc[:cut]
    return load_ohlc, load_rf

def run(mode, cut, seed=0):
    lo, lr = make_perturbed(cut, seed) if mode == "perturb" else make_truncated(cut)
    E.load_ohlc, E.load_rf = lo, lr
    try:
        res = {k: f() for k, f in FUNCS.items()}
    finally:
        E.load_ohlc, E.load_rf = ORIG_OHLC, ORIG_RF
    cutt = pd.Timestamp(cut)
    for k, w in res.items():
        b = base[k]
        pre_b, pre_w = b.loc[:cutt], w.loc[:cutt]
        assert pre_b.index.equals(pre_w.index)
        same = np.array_equal(pre_b.to_numpy(), pre_w.to_numpy())
        maxd_pre = float(np.abs(pre_b.to_numpy() - pre_w.to_numpy()).max())
        line = f"{mode:8s} cut={cut} {k:9s} pre-cut bit-identical={same} max|diff|pre={maxd_pre:.3g}"
        if mode == "perturb":
            post_b, post_w = b.loc[cutt:].iloc[1:], w.loc[cutt:].iloc[1:]
            d = np.abs(post_b.to_numpy() - post_w.to_numpy())
            me = CU.month_offsets(b.index); me = me.index[me.off_own == 0]; me_post = me[me > cutt]
            changed = int(((post_b.loc[me_post] - post_w.loc[me_post]).abs().sum(axis=1) > 1e-12).sum())
            line += f" | post max|diff|={d.max():.3g} month-ends changed {changed}/{len(me_post)}"
        print(line)

for cut in ["2013-05-15", "2019-08-14", "2025-06-16", "2020-03-31", "2015-01-15"]:
    run("perturb", cut, seed=hash(cut) % 1000)
for cut in ["2013-05-15", "2019-08-14", "2025-06-16", "2020-03-31", "2026-09-30", "2026-08-31"]:
    run("truncate", cut)
