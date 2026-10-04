"""Independent re-implementation of futures carry (KMPV 2018) for verification.
Own contract mapping (from the raw symbology API output), own carry, own simulator (no engine.simulate)."""
import sys, json, math, os
import numpy as np, pandas as pd
sys.path.insert(0, "<solo-repo>")
from src import engine as E

V = "<scratch>/edges/"
OUT = V + "verify_carry/"
RAW = "<home>/.cache/gqh/databento_raw/glbx_ohlcv1d_v01.parquet"
CLS = {"fx": ["6E", "6J", "6B", "6A", "6C", "6S"], "rates": ["ZT", "ZF", "ZN", "ZB", "UB"],
       "comm": ["CL", "HO", "RB", "NG", "GC", "SI", "PL", "HG", "ZC", "ZS", "ZW", "ZL", "ZM", "LE", "HE"],
       "eq": ["ES", "NQ", "YM", "RTY"]}
ROOTS = sum(CLS.values(), [])
COST = {"ES": 0.5, "NQ": 0.75, "YM": 0.75, "RTY": 1.0, "ZT": 0.3, "ZF": 0.5, "ZN": 1.0, "ZB": 1.25, "UB": 1.5,
        "6E": 0.5, "6J": 0.75, "6B": 0.75, "6A": 0.75, "6C": 0.75, "6S": 1.0, "CL": 1.5, "GC": 1.5, "SI": 1.5,
        "HG": 1.5, "NG": 2.5, "HO": 2.5, "RB": 2.5, "PL": 2.5,
        "ZC": 4, "ZS": 4, "ZW": 4, "ZL": 4, "ZM": 4, "LE": 4, "HE": 4}
MC = "FGHJKMNQUVXZ"


def contracts():
    r = pd.read_parquet(RAW, columns=["ts_event", "instrument_id", "close", "volume", "symbol"])
    r["date"] = r.ts_event.dt.tz_convert(None).dt.normalize()
    r["root"] = r.symbol.str.split(".").str[0]
    r["rank"] = r.symbol.str[-1].astype(int)
    st = json.load(open(V + "carry/symbology_cache.json"))
    iv = [(int(i), x["d0"], x["d1"], x["s"]) for res in st.values() for i, l in res.items() for x in l]
    iv = pd.DataFrame(iv, columns=["instrument_id", "d0", "d1", "raw"]).drop_duplicates()
    iv["d0"] = pd.to_datetime(iv.d0)
    iv["d1"] = pd.to_datetime(iv.d1)
    m = r.merge(iv, on="instrument_id")
    m = m[(m.date >= m.d0) & (m.date < m.d1)]
    ex = m.raw.str.extract(r"^([0-9A-Z]+?)([FGHJKMNQUVXZ])(\d{1,2})$")
    keep = ex[0] == m.root
    m = m[keep].copy()
    ex = ex[keep]
    mon = ex[1].map(MC.index) + 1
    yy = ex[2].astype(int)
    one = ex[2].str.len() == 1
    ty = m.date.dt.year
    y1 = ty - 1 + ((yy - (ty - 1)) % 10)      # smallest year >= trade_year-1 ending in that digit
    m["dy"] = np.where(one, y1, 2000 + yy)
    m["dm"] = mon
    m["mi"] = m.dy * 12 + m.dm - 1
    n0 = len(m)
    m = m.drop_duplicates(["date", "root", "rank"])
    print("raw rows", len(r), "mapped", len(m), "dups dropped", n0 - len(m), flush=True)
    return m


def carry_daily(m, cal):
    a = m[m["rank"] == 0].set_index(["root", "date"])[["close", "mi", "instrument_id"]]
    b = m[m["rank"] == 1].set_index(["root", "date"])[["close", "mi"]]
    j = a.join(b, lsuffix="0", rsuffix="1", how="inner")
    j = j[(j.close0 > 0) & (j.close1 > 0)]
    gap = j.mi1 - j.mi0
    j = j[(gap != 0) & (gap.abs() <= 12)].copy()
    gap = gap.loc[j.index]
    near = np.where(gap > 0, j.close0, j.close1)
    far = np.where(gap > 0, j.close1, j.close0)
    j["c"] = (near / far) ** (12.0 / gap.abs()) - 1
    j = j.reset_index()
    # a UTC-day bar for D closes about 19:00 ET on D (after the NYSE close of D): usable from the first
    # NYSE session strictly after D
    pos = cal.searchsorted(j.date.values, side="right")
    ok = pos < len(cal)
    j = j[ok].copy()
    j["avail"] = cal[pos[ok]]
    j = j.sort_values("date").groupby(["root", "avail"]).last().reset_index()
    return j.pivot(index="avail", columns="root", values="c").reindex(cal)[ROOTS]


def rolls(m, cal):
    a = m[m["rank"] == 0].sort_values(["root", "date"]).copy()
    a["chg"] = a.groupby("root").instrument_id.diff().fillna(0) != 0
    a = a[a.chg]
    pos = cal.searchsorted(a.date.values, side="left")
    ok = pos < len(cal)
    a = a[ok].copy()
    a["nyse"] = cal[pos[ok]]
    out = pd.DataFrame(0.0, index=cal, columns=ROOTS)
    for r, g in a.groupby("root"):
        out.loc[g.nyse.unique(), r] = 1.0
    return out


def rank_w(s):
    d = s.rank() - (len(s) + 1) / 2
    return d / d[d > 0].sum()


def scale(w, cov, cap=4.0, tv=0.10):
    nz = w[w != 0].index
    if len(nz) == 0:
        return w * 0
    v = float(w[nz] @ cov.loc[nz, nz].fillna(0).values @ w[nz]) * 252
    return w * min(tv / math.sqrt(v), cap) if v > 0 else w * 0


def build(sig, ex, vol, elig, dates, cons, cap=4.0, classes=CLS):
    out = {k: {} for k in list(classes) + ["global"]}
    for t in dates:
        cov = ex.loc[:t].iloc[-252:].cov(min_periods=60)
        books = {}
        for c, rs in classes.items():
            el = [r for r in rs if elig.at[t, r] and np.isfinite(sig.at[t, r])]
            w = pd.Series(0.0, index=ROOTS)
            if cons == "XS" and len(el) >= 3:
                w[el] = rank_w(sig.loc[t, el]) * 0.10 / vol.loc[t, el]
            elif cons == "TS" and len(el) >= 1:
                w[el] = np.sign(sig.loc[t, el]) * 0.10 / vol.loc[t, el] / len(el)
            w = scale(w, cov, cap)
            out[c][t] = w
            if w.abs().sum() > 0:
                books[c] = w
        g = sum(books.values()) / len(books) if books else pd.Series(0.0, index=ROOTS)
        out["global"][t] = scale(g, cov, cap)
    return {k: pd.DataFrame(v).T for k, v in out.items()}


def sim(wdec, ex, roll, cal, lag=2):
    """Held on day t = latest decision at or before session t-lag (next_close: decided close d, traded close d+1,
    earns d+2). Constant target weights between decisions; costs on weight changes and 2x|w| on roll days."""
    w = wdec.reindex(cal).ffill().fillna(0.0).shift(lag).fillna(0.0)
    cost = pd.Series(COST)[w.columns] / 1e4
    trade = w.diff().abs()
    trade.iloc[0] = w.iloc[0].abs()
    tc = (trade * cost).sum(1)
    rc = (2 * w.abs() * roll[w.columns] * cost).sum(1)
    g = (w * ex[w.columns].fillna(0)).sum(1)
    df = pd.DataFrame({"gross": g, "net_1x": g - tc - rc, "net_2x": g - 2 * (tc + rc)})
    return df, trade.sum(1) + (2 * w.abs() * roll[w.columns]).sum(1), w.abs().sum(1)


def setup():
    ohlc = E.load_ohlc([f"F_{r}" for r in ROOTS], "FWD")
    cal = ohlc["close"].index
    rf = E.load_rf("FWD").reindex(cal).ffill().fillna(0.0)
    px = ohlc["close"].rename(columns=lambda c: c[2:])[ROOTS]
    ex = px.pct_change(fill_method=None).sub(rf, axis=0)
    vol = np.sqrt((ex ** 2).ewm(com=60, min_periods=60).mean() * 252)
    vlm = ohlc["volume"].rename(columns=lambda c: c[2:])[ROOTS].fillna(0)
    elig = (ex.notna().cumsum() >= 300) & (vol > 0) & ((vlm > 0).rolling(10, min_periods=1).max() > 0)
    ir = ohlc["roll"].rename(columns=lambda c: c[2:])[ROOTS].fillna(0)
    return ohlc, cal, rf, ex, vol, elig, ir


def decision_dates(cal, fq):
    s = pd.Series(cal, index=cal)
    return pd.DatetimeIndex(s.groupby(cal.to_period("M" if fq == "M" else "W-FRI")).max().values)


def main():
    ohlc, cal, rf, ex, vol, elig, ir = setup()
    m = contracts()
    cd = carry_daily(m, cal)
    cd.to_parquet(OUT + "v_carry_daily.parquet")
    rl = rolls(m, cal)
    print("roll flag agreement", float((rl == ir).values.mean()), "my rolls", int(rl.values.sum()),
          "index rolls", int(ir.values.sum()), flush=True)
    res = {}
    for lagx in (0, 1, 2):   # 0 = availability rule above (equivalent to the analyst's); 1, 2 = extra lags
        for sn, (win, mn) in {"C1": (21, 10), "C12": (252, 126)}.items():
            sig = cd.rolling(win, min_periods=mn).mean().shift(lagx)
            for fq in ("M", "W"):
                if lagx != 0 and fq == "W":
                    continue
                dates = decision_dates(cal, fq)
                for cons in ("XS", "TS"):
                    bk = build(sig, ex, vol, elig, dates, cons)
                    for b, wd in bk.items():
                        res[(lagx, sn, fq, cons, b)] = sim(wd[ROOTS], ex, rl, cal)
                    print("done", lagx, sn, fq, cons, flush=True)
    pd.to_pickle(res, OUT + "v_results.pkl")


if __name__ == "__main__":
    main()
