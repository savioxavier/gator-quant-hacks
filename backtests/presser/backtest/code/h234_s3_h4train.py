"""H2/H3/H4 step 3 (prereg 6.4, 9.4): the H4 training fit on Powell 2018-2022, written and hashed before any
2023-2026 join. Prices are read only for training rows (dates before 2023-01-01).

Recorded with the fit: the H1 code hash (presser_bt/backtest/code) and the sha256 of text_chrono/answers.parquet."""
from __future__ import annotations

import hashlib
import json
import math

import numpy as np
import pandas as pd

from lib import TZ, Bars, check_addendum, sha256
from h234_lib import h1_code_files, LABEL, OUT, TEXT_CHRONO, check_manifest, check_prereg, dump, load_provenance

check_addendum()
check_prereg()
PROV = load_provenance()
P, W = OUT / "positions", OUT / "h4_fit"
check_manifest(P, "positions")
W.mkdir(parents=True, exist_ok=True)
TRAIN_END = "2022-12-31"
T = lambda d, s: pd.Timestamp(f"{d} {s}", tz=TZ)

sel = pd.read_csv(P / "answer_sel_H4_h1.csv", dtype={"date": str, "answer_id": str})
sel["t0"] = pd.to_datetime(sel.t0, utc=True, format="ISO8601").dt.tz_convert(TZ)
tr = sel[sel["sample"] == "additional_2018_2022"].copy()
assert (tr.date <= TRAIN_END).all()
mp = pd.read_csv(P / "meetings_h234_positions.csv", dtype={"date": str})
mp["tau_end_upper"] = pd.to_datetime(mp.tau_end_upper, utc=True, format="ISO8601").dt.tz_convert(TZ)
mtr = mp[mp["H4__meligible"].astype(bool) & (mp["sample"] == "additional_2018_2022")].copy()
assert (mtr.date <= TRAIN_END).all()
bars = Bars()


def answer_y(df, sym):
    y = []
    for r in df.itertuples():
        e_ts, e_px = bars.next_open(r.date, sym, r.t0, tag="h4_train_entry")
        if e_ts is None:
            y.append(np.nan)
            continue
        # exit one minute after this symbol's own entry bar, exactly as the test target in h234_s4 (one_trade)
        x_ts, x_px = bars.close_at(r.date, sym, e_ts + pd.Timedelta(minutes=1), lo=e_ts, tag="h4_train_exit")
        y.append(1e4 * math.log(x_px / e_px) if x_ts is not None else np.nan)
    return np.array(y)


def meeting_y(df, sym):
    y = []
    for r in df.itertuples():
        e_ts, e_px = bars.next_open(r.date, sym, r.tau_end_upper, tag="h4m_train_entry")
        if e_ts is None or e_ts >= T(r.date, "15:59:00"):
            y.append(np.nan)
            continue
        x_ts, x_px = bars.close_at(r.date, sym, T(r.date, "16:00:00"), lo=e_ts, tag="h4m_train_exit")
        y.append(1e4 * math.log(x_px / e_px) if x_ts is not None else np.nan)
    return np.array(y)


def fit(df, y, feats_T, feats_C, group):
    ok = np.isfinite(y) & np.all(np.isfinite(df[feats_C].to_numpy(float)), axis=1)
    d, yy = df[ok], y[ok]
    mu = {c: float(d[c].mean()) for c in feats_C}
    sd = {c: float(d[c].std(ddof=1)) for c in feats_C}
    out = dict(n=int(ok.sum()), n_meetings=int(d[group].nunique()), meetings=sorted(d.date.unique().tolist()),
               standardise_mean=mu, standardise_sd=sd)
    for name, fs in [("T", feats_T), ("C", feats_C)]:
        X = np.column_stack([np.ones(len(d))] + [(d[c].to_numpy(float) - mu[c]) / sd[c] for c in fs])
        b = np.linalg.lstsq(X, yy, rcond=None)[0]
        e = yy - X @ b
        out[f"coef_{name}"] = dict(zip(["const"] + fs, map(float, b)))
        out[f"r2_in_sample_{name}"] = float(1 - (e ** 2).sum() / ((yy - yy.mean()) ** 2).sum())
    return out


fits = {}
for sym in ["ZT", "ES"]:
    fits[f"answer_{sym}"] = fit(tr, answer_y(tr, sym), ["s_tilde"], ["s_tilde", "zA", "U"], "meeting")
    fits[f"meeting_{sym}"] = fit(mtr, meeting_y(mtr, sym), ["s_tilde_m"], ["s_tilde_m", "zA_m", "U_m"], "meeting")
code_files = h1_code_files()
h = hashlib.sha256()
for p in code_files:
    h.update(p.name.encode())
    h.update(p.read_bytes())
doc = dict(label=LABEL, spec="prereg 6.4: OLS fitted once on Powell 2018-2022 (timing-eligible, after burn-in); frozen",
           target="10,000 x ln(close at t0 + 1 min / open at t0) (answer); next 1m open after tau_end_upper to the "
                  "16:00 close (meeting)",
           fits=fits, h1_code_sha256={p.name: sha256(p) for p in code_files}, h1_code_combined_sha256=h.hexdigest(),
           text_chrono_answers_sha256=sha256(TEXT_CHRONO / "answers.parquet"),
           positions_manifest_sha256=sha256(P / "manifest_sha256.txt"),
           features_manifest_sha256=sha256(OUT / "features" / "manifest_sha256.txt"),
           qa_manifest_sha256=sha256(OUT / "qa" / "manifest_sha256.txt"),
           placebo_features=bool(PROV["placebo"]), train_end=TRAIN_END,
           written_before_test_join=True)
dump(W / "fit.json", doc)
(W / "fit.sha256").write_text(f"{sha256(W / 'fit.json')}  fit.json\n")
print(json.dumps({k: {kk: v[kk] for kk in ("n", "n_meetings", "coef_T", "coef_C")} for k, v in fits.items()},
                 indent=1))
print("fit sha256", sha256(W / "fit.json"))
