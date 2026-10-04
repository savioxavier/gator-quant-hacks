"""Independent data loaders for the verification (own parsing; KF files re-downloaded into ./raw)."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
THEIR_RAW = HERE.parent / "long_history" / "raw"   # read-only use of public files they downloaded
CACHE = Path("<home>/.cache/gqh")


def _kf_table(path: Path, datelen: int) -> pd.DataFrame:
    rows, cols = [], None
    for line in path.read_text(encoding="latin-1").splitlines():
        p = [x.strip() for x in line.split(",")]
        if cols is None and len(p) > 2 and p[0] == "" and p[1] == "Mkt-RF":
            cols = p[1:]
            continue
        if cols is not None:
            if re.fullmatch(r"\d{%d}" % datelen, p[0] or "x"):
                rows.append([p[0]] + [float(v) for v in p[1:len(cols) + 1]])
            elif rows:
                break
    df = pd.DataFrame(rows, columns=["d"] + cols)
    fmt = "%Y%m%d" if datelen == 8 else "%Y%m"
    df.index = pd.to_datetime(df.pop("d"), format=fmt)
    if datelen == 6:
        df.index = df.index + pd.offsets.MonthEnd(0)
    return df.replace(-99.99, np.nan) / 100.0


def kf_daily() -> pd.DataFrame:
    d = _kf_table(RAW / "F-F_Research_Data_Factors_daily.csv", 8)
    return pd.DataFrame({"R": d["Mkt-RF"] + d["RF"], "rf": d["RF"]})


def kf_monthly() -> pd.DataFrame:
    d = _kf_table(RAW / "F-F_Research_Data_Factors.csv", 6)
    return pd.DataFrame({"US_EQ": d["Mkt-RF"] + d["RF"], "rf": d["RF"]})


def dev_ex_us() -> pd.Series:
    d = _kf_table(RAW / "Developed_ex_US_3_Factors.csv", 6)
    return (d["Mkt-RF"] + d["RF"]).dropna()


def ind_all() -> pd.Series:
    out = {}
    for line in (THEIR_RAW / "kf" / "Ind_all.Dat").read_text(encoding="latin-1").splitlines():
        m = re.match(r"^\s*(\d{6})\s+(-?\d+\.\d+)", line)
        if m:
            out[m.group(1)] = float(m.group(2))
        elif out:
            break
    s = pd.Series(out)
    s.index = pd.to_datetime(s.index, format="%Y%m") + pd.offsets.MonthEnd(0)
    return s.replace(-99.99, np.nan) / 100.0


def nareit_all_equity() -> pd.Series:
    raw = pd.read_csv(THEIR_RAW / "nareit_monthly__2_Index_Data.csv", header=None, dtype=str, encoding="latin-1")
    hdr = raw.iloc[5].fillna("")
    c = [i for i, v in enumerate(hdr) if v.strip() == "All Equity REITs"][0]
    # column c = total return (%), c+1 = total return index
    sub = raw.iloc[9:, [0, c + 1]].dropna()
    idx = pd.to_numeric(sub.iloc[:, 1].str.replace(",", ""), errors="coerce")
    dt = pd.to_datetime(sub.iloc[:, 0], format="%b-%y") + pd.offsets.MonthEnd(0)
    s = pd.Series(idx.values, index=dt).dropna()
    return s.pct_change().dropna()


def aqr_commod_er() -> pd.Series:
    d = pd.read_excel(THEIR_RAW / "aqr_commod.xlsx", sheet_name=0, header=None)
    b = d.iloc[11:, :2].dropna()
    s = pd.Series(pd.to_numeric(b.iloc[:, 1]).values, index=pd.to_datetime(b.iloc[:, 0]) + pd.offsets.MonthEnd(0))
    return s


def dgs10_daily() -> pd.Series:
    f = pd.read_parquet(CACHE / "fred_daily.parquet").set_index("date")
    f.index = pd.to_datetime(f.index)
    return f["DGS10"].dropna() / 100.0


def rf_daily() -> pd.Series:
    r = pd.read_parquet(CACHE / "rf_daily.parquet").set_index("date")["rf"]
    r.index = pd.to_datetime(r.index)
    return r


def bond_daily_duration() -> pd.DataFrame:
    """Own 10y constant-maturity TR: carry y_{t-1}*dt - ModDur*dy + 0.5*Conv*dy^2 (par bond, semiannual)."""
    y = dgs10_daily()
    dt = y.index.to_series().diff().dt.days / 365.0
    y0 = y.shift(1)
    dy = y - y0
    h = y0 / 2
    n = 20
    # modified duration and convexity of a 10y par bond with semiannual coupons
    moddur = (1 - (1 + h) ** (-n)) / y0

    def price(c, yy):
        k = np.arange(1, n + 1)[None, :]
        cf = np.full((len(c), n), 0.0) + (c[:, None] / 2)
        cf[:, -1] += 1
        return (cf / (1 + yy[:, None] / 2) ** k).sum(axis=1)

    c0 = y0.to_numpy()
    eps = 1e-4
    ok = ~np.isnan(c0)
    conv = np.full(len(c0), np.nan)
    p0 = price(c0[ok], c0[ok])
    conv[ok] = (price(c0[ok], c0[ok] + eps) + price(c0[ok], c0[ok] - eps) - 2 * p0) / (eps ** 2 * p0)
    conv = pd.Series(conv, index=y.index)
    r = y0 * dt - moddur * dy + 0.5 * conv * dy ** 2
    out = pd.DataFrame({"R": r}).iloc[1:]
    out["rf"] = rf_daily().reindex(out.index).ffill()
    return out.dropna()
