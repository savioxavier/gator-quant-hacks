"""Decomposition, volume, bootstrap and concentration checks built on v01's independent ledger (store.pkl)."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
IS_END = pd.Timestamp("2024-10-02")
LATER0 = pd.Timestamp("2024-10-03")
PUB = pd.Timestamp("2019-12-01")
S = pd.read_pickle(HERE / "store.pkl")
store, days, mo, hb = S["store"], S["days"], S["mo"], S["hb"]
OUT = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    OUT.append(s)


def nw_t(x, lags=3):
    x = np.asarray(x, float)
    n = len(x)
    e = x - x.mean()
    s = e @ e / n
    for L in range(1, lags + 1):
        s += 2 * (1 - L / (lags + 1)) * (e[L:] @ e[:-L]) / n
    return x.mean() / math.sqrt(s / n)


def per_window(bars, mask, label):
    b = bars[mask]
    allT = bars["T_w"].unique()
    return b.groupby("T_w")["x"].sum().reindex(allT).fillna(0.0).sort_index() * 1e4


# window T for each held bar: the month T of its return day if offset<=0 else (exit_1700 bars) previous T
for key, (P, C, Cn, bars) in store.items():
    bars = bars.copy()
    bars["T_w"] = np.where(bars["off"] <= 0, bars["T"], pd.NaT)
    # bars on T+1 (exit_1700 extension): map to previous T
    nxt = bars["T_w"].isna()
    if nxt.any():
        i = days.get_indexer(bars.loc[nxt, "rd"])
        bars.loc[nxt, "T_w"] = days.values[i - 1]
    bars["T_w"] = pd.to_datetime(bars["T_w"])
    store[key] = (P, C, Cn, bars)

# ---------------- sleeve C base: block decomposition, pre/post
P, C, Cn, b = store[("C", "base")]
b["is"] = b["rd"] <= IS_END
b["same_day"] = b["date_et"] == b["rd"]
for smp, m in {"IS": b["is"], "IS_pre": b["rd"] < PUB, "IS_post": (b["rd"] >= PUB) & b["is"], "later": b["rd"] >= LATER0}.items():
    bs = b[m]
    tot = per_window(bs, slice(None), "tot")
    out = [f"C {smp}: n_win {len(tot)} total {tot.mean():.2f}bp (t {nw_t(tot.values):.2f})"]
    for name, hrs in {"14-15": [14], "15-16": [15], "10-12": [10, 11], "asia18-02": [18, 19, 20, 21, 22, 23, 0, 1],
                      "post16-18": [16, 17]}.items():
        y = per_window(bs, bs["hour"].isin(hrs), name)
        out.append(f"{name} {y.mean():.2f} (t {nw_t(y.values):.2f})")
    day = per_window(bs, bs["same_day"] & bs["hour"].between(9, 15), "day")
    out.append(f"day {day.mean():.2f} (t {nw_t(day.values):.2f}) night {(tot-day).mean():.2f} (t {nw_t((tot-day).values):.2f})")
    for k in (-2, -1, 0):
        y = per_window(bs, bs["off"] == k, f"k{k}")
        out.append(f"T{k:+d} {y.mean():.2f} (t {nw_t(y.values):.2f})")
    for k in (0,):
        for hh in (13, 14, 15):
            y = per_window(bs, (bs["off"] == k) & (bs["hour"] == hh) & bs["same_day"], "x")
            out.append(f"T bar{hh} {y.mean():.2f} (t {nw_t(y.values):.2f})")
    log(" | ".join(out))

# unit ZN return in 15:00 bar on T and 14:00 bar on T (all months, in-sample, excluding gap bars via hb)
z = hb[(hb.root == "ZN") & (hb.rd <= IS_END) & (hb.off == 0) & (hb.date_et == hb.rd)]
for hh in (13, 14, 15):
    y = z[z.hour == hh].groupby("rd")["r"].sum() * 1e4
    log(f"ZN unit bar {hh}:00 on T, IS: mean {y.mean():.2f}bp t {nw_t(y.values, 2):.2f} n {len(y)}")

# ---------------- volume: ZN/ES on T by hour vs same-month T-15..T-6 same hour (median ratio)
for root in ("ZN", "ES"):
    v = hb[(hb.root == root) & (hb.rd <= IS_END)].copy()
    v["month"] = v["T"]
    base = v[v["off"].between(-15, -6)].groupby(["month", "hour"])["vol_tot"].mean().rename("base")
    t = v[(v["off"] == 0)].join(base, on=["month", "hour"])
    t["ratio"] = t["vol_tot"] / t["base"]
    r = t.groupby("hour")["ratio"].median()
    log(f"{root} median abnormal volume on T by start hour:", r.round(2).loc[[9, 10, 11, 12, 13, 14, 15, 16]].to_dict())

# ---------------- sleeve A: leg split, Feb-2020 concentration
P, C, Cn, b = store[("A", "base")]
bi = b[b["rd"] <= IS_END]
tot = per_window(bi, slice(None), "tot")
es = per_window(bi, bi["root"] == "ES", "es")
log(f"A IS window mean {tot.mean():.2f} (t {nw_t(tot.values):.2f}); ES leg {es.mean():.2f} ({es.mean()/tot.mean():.0%}); ZN leg {(tot-es).mean():.2f}")
dd = bi["date_et"] == bi["rd"]
day = per_window(bi, dd & bi["hour"].between(9, 15), "d")
log(f"A IS day {day.mean():.2f} ({day.mean()/tot.mean():.0%}, t {nw_t(day.values):.2f}); T 15:00 bar {per_window(bi, (bi.off==0)&(bi.hour==15)&dd,'x').mean():.2f}")
net = (P - C)
first = days[days.get_loc(b["rd"].min()) - 1]
m = (days >= first) & (days <= IS_END)
x = net[m]
wT = pd.Series(pd.NaT, index=days, dtype="datetime64[ns]")
for T in tot.index:
    i = days.get_loc(T)
    wT.iloc[i - 5:i + 1] = T
wp = x.groupby(wT[m]).sum().sort_values(ascending=False)
log(f"A IS net1x total {wp.sum()*1e4:.1f}bp; top window {wp.index[0].date()} share {wp.iloc[0]/wp.sum():.0%}; top5 {wp.iloc[:5].sum()/wp.sum():.0%}")
xe = x[~((x.index >= wp.index[0] - pd.Timedelta(days=12)) & (x.index <= wp.index[0]))]
log(f"A IS net1x Sharpe {x.mean()/x.std()*math.sqrt(252):.3f}; without best window {xe.mean()/xe.std()*math.sqrt(252):.3f}")

# C concentration and later-window three last months
P, C, Cn, b = store[("C", "base")]
x = (P - C)
wT = pd.Series(pd.NaT, index=days, dtype="datetime64[ns]")
for T in b["T_w"].unique():
    i = days.get_loc(T)
    wT.iloc[i - 3:i + 1] = T
lw = x[days >= LATER0].groupby(wT[days >= LATER0]).sum() * 1e4
log("C later net1x per window (last 6):", lw.tail(6).round(1).to_dict())
lg = P[days >= LATER0].groupby(wT[days >= LATER0]).sum() * 1e4
log(f"C later gross sum {lg.sum():.0f}bp over {len(lg)} windows; ex last 3 mean {lg.iloc[:-3].mean():.1f}bp")

# ---------------- paired block bootstrap of Sharpe differences (3-month blocks), in-sample, own RNG
rng = np.random.default_rng(7)


def boot(sleeve, cost_mult, B=4000):
    first = days[days.get_loc(store[(sleeve, "base")][3]["rd"].min()) - 1]
    m = (days >= first) & (days <= IS_END)
    ser = {v: (store[(sleeve, v)][0] - cost_mult * store[(sleeve, v)][1])[m] for v in
           ("base", "exit_1500", "exit_1700", "day_only", "night_only")}
    per = days[m].to_period("M")
    months = per.unique()
    M = len(months)
    agg = {v: np.stack([s.groupby(per).sum().reindex(months).values, (s ** 2).groupby(per).sum().reindex(months).values,
                        s.groupby(per).size().reindex(months).values], 1) for v, s in ser.items()}
    nb = math.ceil(M / 3)
    st = rng.integers(0, M - 2, size=(B, nb))
    idx = (st[:, :, None] + np.arange(3)).reshape(B, -1)[:, :M]

    def sr(a):
        s, s2, c = a[..., 0].sum(-1), a[..., 1].sum(-1), a[..., 2].sum(-1)
        mu = s / c
        return mu / np.sqrt(s2 / c - mu ** 2) * math.sqrt(252)
    base = sr(agg["base"][idx])
    for v in ("exit_1500", "exit_1700", "day_only", "night_only"):
        d = sr(agg[v][idx]) - base
        log(f"boot {sleeve} {cost_mult}x {v}: dSR CI [{np.percentile(d,2.5):.3f}, {np.percentile(d,97.5):.3f}] P(d<=0) {np.mean(d<=0):.3f}")


for sl in ("C", "A"):
    boot(sl, 1)
boot("C", 0)
(HERE / "v02_log.txt").write_text("\n".join(OUT), encoding="utf-8")
