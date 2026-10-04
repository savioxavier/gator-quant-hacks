"""Build long-history monthly and daily return series for the 10-month SMA timing study.

Every series is a TOTAL return (price + income) in decimal, plus the cash rate. Sources (all free, raw files
in ./raw, downloaded over HTTP):
  US_EQ      Ken French market (Mkt-RF + RF), monthly 1926-07.., daily 1926-07-01..
  US_10Y     constant-maturity 10y Treasury total return rebuilt from FRED DGS10 (daily, 1962-01..)
             par bond, coupon = yesterday's yield, repriced at today's yield with maturity 10y - dt, + carry
  GOLD_AVG   World Bank Pink Sheet gold price, MONTHLY AVERAGES (datahub gold-prices), 1968-04..
  GOLD_ME    GLD month-end closes (cache), 2004-11.. (used only to calibrate the averaging bias)
  COMMOD     AQR "Commodities for the Long Run" excess return of the equal-weight commodity futures portfolio
             (1877-02..2025-05) + cash; extended 2025-06.. by an equal-weight of the 15 commodity futures in
             our CME cache (validated on the 2010-07..2025-05 overlap)
  REIT       FTSE Nareit All Equity REITs total return, 1972-01..
  INTL       Ken French international: Ind_all value-weight USD returns 1975-01..1990-06, then
             Developed ex US (Mkt-RF + RF) 1990-07..
  US_EQ_SHA  Shiller S&P composite (monthly AVERAGE prices + dividends), 1871-02..2023-06
  cash       Ken French RF (1-month T-bill) from 1926-07; Shiller annual one-year rate before (approximate);
             rf_daily (3m T-bill) for the 2026-09 month and for the daily bond series.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
OUT = HERE / "data"
OUT.mkdir(exist_ok=True)
CACHE = Path("<home>/.cache/gqh")


def me(p: pd.PeriodIndex) -> pd.DatetimeIndex:
    return p.to_timestamp(how="end").normalize()


# ----------------------------------------------------------------------------- Ken French
def kf_csv(path: Path, daily: bool = False) -> pd.DataFrame:
    """First table of a Ken French CSV (stops at the annual block)."""
    lines = path.read_text(encoding="latin-1").splitlines()
    hdr = next(i for i, l in enumerate(lines) if l.replace(" ", "").startswith(",Mkt-RF"))
    rows = []
    for l in lines[hdr + 1:]:
        parts = [x.strip() for x in l.split(",")]
        if not parts[0] or not parts[0].isdigit():
            break
        if (daily and len(parts[0]) != 8) or (not daily and len(parts[0]) != 6):
            break
        rows.append(parts)
    cols = ["date"] + [c.strip() for c in lines[hdr].split(",")[1:]]
    df = pd.DataFrame(rows, columns=cols[: len(rows[0])])
    for c in df.columns[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.replace(-99.99, np.nan)
    if daily:
        df.index = pd.to_datetime(df["date"], format="%Y%m%d")
    else:
        df.index = me(pd.PeriodIndex(pd.to_datetime(df["date"], format="%Y%m"), freq="M"))
    return df.drop(columns="date") / 100.0


def kf_ind_all() -> pd.Series:
    """Ind_all.Dat first block: value-weight dollar returns, column Mkt."""
    lines = (RAW / "kf" / "Ind_all.Dat").read_text(encoding="latin-1").splitlines()
    out = {}
    started = False
    for l in lines:
        m = re.match(r"^\s*(\d{6})\s+(-?\d+\.\d+)", l)
        if m:
            started = True
            out[m.group(1)] = float(m.group(2))
        elif started:
            break
    s = pd.Series(out)
    s.index = me(pd.PeriodIndex(pd.to_datetime(s.index, format="%Y%m"), freq="M"))
    return (s.replace(-99.99, np.nan) / 100.0).rename("INTL_IND_ALL")


# ----------------------------------------------------------------------------- Shiller
def shiller() -> tuple[pd.Series, pd.Series]:
    """(monthly TR from averaged prices, annual one-year rate as monthly cash)."""
    rows = []
    for l in (RAW / "shiller_ie_data__2_Data.csv").read_text(encoding="latin-1").splitlines():
        m = re.match(r"^(\d{4})\.(\d{2}),([^,]*),([^,]*),", l)
        if m:
            rows.append((int(m.group(1)), int(m.group(2)), m.group(3), m.group(4)))
    df = pd.DataFrame(rows, columns=["y", "m", "P", "D"])
    df["m"] = df["m"].replace({1: 1})
    # Shiller encodes October as .1 -> "10"; the regex reads two digits so 1871.10 -> m=10, fine
    df["P"] = pd.to_numeric(df["P"].str.replace(" ", ""), errors="coerce")
    df["D"] = pd.to_numeric(df["D"].str.replace(" ", ""), errors="coerce")
    df.index = me(pd.PeriodIndex([pd.Period(year=y, month=m, freq="M") for y, m in zip(df.y, df.m)]))
    df = df.dropna(subset=["P", "D"])
    tr = ((df["P"] + df["D"] / 12.0) / df["P"].shift(1) - 1).dropna().rename("US_EQ_SHA")
    x = pd.read_excel(RAW / "shiller_chapt26.xlsx", sheet_name="Data", header=None)
    yr = pd.to_numeric(x.iloc[8:, 0], errors="coerce")
    r1 = pd.to_numeric(x.iloc[8:, 4], errors="coerce")
    ann = pd.Series(r1.values, index=yr.values).dropna()
    ann = ann[~ann.index.isna()]
    ann.index = ann.index.astype(int)
    months = pd.period_range("1871-01", "1926-12", freq="M")
    rf = pd.Series([(1 + ann.get(p.year, np.nan) / 100.0) ** (1 / 12) - 1 for p in months], index=me(months))
    return tr, rf.rename("rf_shiller")


# ----------------------------------------------------------------------------- bond from DGS10
def par_price(c: np.ndarray, y: np.ndarray, m: np.ndarray) -> np.ndarray:
    """Price of a semiannual-coupon bond (coupon c, yield y, maturity m years), per 1 of face."""
    v = (1 + y / 2.0) ** (-2.0 * m)
    return np.where(np.abs(y) > 1e-10, c / y * (1 - v) + v, 1.0 + c * m)


def bond_daily() -> pd.DataFrame:
    f = pd.read_parquet(CACHE / "fred_daily.parquet").set_index("date")
    f.index = pd.to_datetime(f.index)
    y = (f["DGS10"].dropna() / 100.0)
    dt_years = y.index.to_series().diff().dt.days.to_numpy() / 365.25
    c = y.shift(1).to_numpy()
    yt = y.to_numpy()
    r = c * dt_years + par_price(c, yt, 10.0 - dt_years) - 1.0
    out = pd.DataFrame({"US_10Y": r}, index=y.index).iloc[1:]
    rf = pd.read_parquet(CACHE / "rf_daily.parquet").set_index("date")["rf"]
    rf.index = pd.to_datetime(rf.index)
    out["rf"] = rf.reindex(out.index).ffill()
    out["yield"] = y.reindex(out.index)
    return out


# ----------------------------------------------------------------------------- futures commodity EW
COMMOD_ROOTS = ["F_CL", "F_HO", "F_RB", "F_NG", "F_GC", "F_SI", "F_HG", "F_PL", "F_ZC", "F_ZS", "F_ZW",
                "F_ZL", "F_ZM", "F_LE", "F_HE"]


def futures_commod_monthly() -> pd.Series:
    fu = pd.read_parquet(CACHE / "futures_daily.parquet")
    fu = fu[fu.ticker.isin(COMMOD_ROOTS)].pivot(index="date", columns="ticker", values="close").sort_index()
    fu.index = pd.to_datetime(fu.index)
    m = fu.groupby(fu.index.to_period("M")).last()
    r = m.pct_change(fill_method=None).iloc[1:]
    ew = r.mean(axis=1)
    ew.index = me(ew.index)
    # drop the first (partial) month and any incomplete final month
    last = fu.index.max()
    if (last + pd.offsets.BDay(1)).to_period("M") == last.to_period("M"):
        ew = ew.iloc[:-1]
    return ew.iloc[1:].rename("COMMOD_FUT_EW_TR")


def nareit() -> pd.Series:
    raw = pd.read_csv(RAW / "nareit_monthly__2_Index_Data.csv", header=None, dtype=str, encoding="latin-1")
    hdr = raw.iloc[5].fillna("")
    col = [i for i, v in enumerate(hdr) if v.strip() == "All Equity REITs"][0]
    sub = raw.iloc[9:, [0, col + 1]].dropna()
    sub.columns = ["date", "idx"]
    sub["idx"] = pd.to_numeric(sub["idx"].str.replace(",", ""), errors="coerce")
    sub = sub.dropna()
    sub.index = me(pd.PeriodIndex(pd.to_datetime(sub["date"], format="%b-%y"), freq="M"))
    # %y maps 71..99 to 1971..1999 and 00..68 to 2000..2068 -> correct for this 1971-2026 range
    lvl = sub["idx"].astype(float)
    return lvl.pct_change().dropna().rename("REIT")


def aqr_commod() -> pd.Series:
    d = pd.read_excel(RAW / "aqr_commod.xlsx", sheet_name="Commodities for the Long Run", header=None)
    body = d.iloc[11:, :2].dropna()
    body.columns = ["date", "er"]
    body.index = me(pd.PeriodIndex(pd.to_datetime(body["date"]), freq="M"))
    return pd.to_numeric(body["er"]).rename("COMMOD_ER")


def gold_avg() -> pd.Series:
    g = pd.read_csv(RAW / "gold_monthly.csv")
    g.index = me(pd.PeriodIndex(g["Date"], freq="M"))
    p = g["Price"].astype(float)
    p = p.loc["1968-03-31":]          # London price floats from the two-tier market (March 1968)
    return p.pct_change().dropna().rename("GOLD_AVG")


def gld_me() -> pd.Series:
    e = pd.read_parquet(CACHE / "etf_daily.parquet")
    g = e[e.ticker == "GLD"].set_index("date")["close"]
    g.index = pd.to_datetime(g.index)
    m = g.groupby(g.index.to_period("M")).last()
    r = m.pct_change().dropna()
    r.index = me(r.index)
    last = g.index.max()
    if (last + pd.offsets.BDay(1)).to_period("M") == last.to_period("M"):
        r = r.iloc[:-1]
    return r.iloc[1:].rename("GOLD_ME")


def main() -> None:
    ffm = kf_csv(RAW / "kf" / "F-F_Research_Data_Factors.csv")
    ffd = kf_csv(RAW / "kf" / "F-F_Research_Data_Factors_daily.csv", daily=True)
    dxm = kf_csv(RAW / "kf" / "Developed_ex_US_3_Factors.csv")
    sh_tr, sh_rf = shiller()

    # cash: FF RF; before 1926-07 Shiller one-year rate; after FF ends, compounded rf_daily
    rf_d = pd.read_parquet(CACHE / "rf_daily.parquet").set_index("date")["rf"]
    rf_d.index = pd.to_datetime(rf_d.index)
    rf_dm = (1 + rf_d).groupby(rf_d.index.to_period("M")).prod() - 1
    rf_dm.index = me(rf_dm.index)
    rf = ffm["RF"].copy()
    rf = pd.concat([sh_rf[sh_rf.index < rf.index[0]], rf])
    extra = rf_dm[(rf_dm.index > rf.index[-1]) & (rf_dm.index <= pd.Timestamp("2026-09-30"))]
    rf = pd.concat([rf, extra]).rename("rf")

    us_eq = (ffm["Mkt-RF"] + ffm["RF"]).rename("US_EQ")

    bd = bond_daily()
    bm = (1 + bd["US_10Y"]).groupby(bd.index.to_period("M")).prod() - 1
    bm.index = me(bm.index)
    bm = bm.loc["1962-02-28":"2026-09-30"].rename("US_10Y")   # drop partial first (1962-01) and last month

    intl_a = kf_ind_all()
    intl_b = (dxm["Mkt-RF"] + dxm["RF"]).dropna()
    intl = pd.concat([intl_a[intl_a.index < intl_b.index[0]], intl_b]).rename("INTL")

    aqr = aqr_commod()
    fut = futures_commod_monthly()
    # cash for the commodity TR: FF RF where present, rf_daily after, Shiller before 1926-07
    com_tr = (aqr + rf.reindex(aqr.index)).rename("COMMOD")
    fut_er = fut - rf.reindex(fut.index)
    ext = fut[fut.index > aqr.index[-1]]
    com = pd.concat([com_tr, ext]).rename("COMMOD")

    monthly = pd.concat([rf, us_eq, bm, gold_avg(), gld_me(), com, nareit(), intl, sh_tr,
                         aqr.rename("COMMOD_ER_AQR"), fut_er.rename("COMMOD_FUT_EW_ER"),
                         intl_a, intl_b.rename("INTL_DEV_EX_US")], axis=1).sort_index()
    monthly.index.name = "date"
    monthly.to_parquet(OUT / "monthly.parquet")

    ff_daily = pd.DataFrame({"US_EQ": ffd["Mkt-RF"] + ffd["RF"], "rf": ffd["RF"]})
    ff_daily.index.name = "date"
    ff_daily.to_parquet(OUT / "daily_us_eq.parquet")
    bd.index.name = "date"
    bd.to_parquet(OUT / "daily_us_10y.parquet")

    # ---------------------------------------------------------------- validation printout
    print("monthly coverage:")
    for c in monthly.columns:
        s = monthly[c].dropna()
        print(f"  {c:18s} {s.index.min().date()} .. {s.index.max().date()}  n={len(s)}")
    print("daily US_EQ", ff_daily.index.min().date(), ff_daily.index.max().date(), len(ff_daily))
    print("daily US_10Y", bd.index.min().date(), bd.index.max().date(), len(bd))

    # bond construction vs IEF / TLT / F_ZN
    e = pd.read_parquet(CACHE / "etf_daily.parquet")
    px = e[e.ticker.isin(["IEF", "TLT"])].pivot(index="date", columns="ticker", values="close")
    px.index = pd.to_datetime(px.index)
    pm = px.groupby(px.index.to_period("M")).last().pct_change()
    pm.index = me(pm.index)
    j = pd.concat([bm, pm], axis=1).loc["2003-08-31":"2024-09-30"].dropna()
    print("bond monthly corr vs IEF/TLT 2003-2024:", j.corr().iloc[0, 1:].round(3).to_dict(),
          " ann mean:", (j.mean() * 12).round(4).to_dict(), " ann vol:", (j.std() * np.sqrt(12)).round(4).to_dict())
    # COMMOD splice validation
    jj = pd.concat([aqr, fut_er], axis=1).dropna()
    print("AQR EW commodity ER vs our 15-futures EW ER, overlap", jj.index.min().date(), jj.index.max().date(),
          "corr", round(jj.corr().iloc[0, 1], 3), "ann mean", (jj.mean() * 12).round(4).to_dict(),
          "ann vol", (jj.std() * np.sqrt(12)).round(4).to_dict())
    # INTL splice validation
    k = pd.concat([intl_a, intl_b], axis=1).dropna()
    print("Ind_all vs Dev ex US overlap corr", round(k.corr().iloc[0, 1], 3), "ann mean",
          (k.mean() * 12).round(4).to_dict())
    # Shiller vs FF overlap
    s2 = pd.concat([sh_tr, us_eq], axis=1).dropna()
    print("Shiller avg-price TR vs FF month-end TR: corr", round(s2.corr().iloc[0, 1], 3),
          "lag-1 autocorr Shiller", round(s2.iloc[:, 0].autocorr(), 3), "FF", round(s2.iloc[:, 1].autocorr(), 3))
    g2 = pd.concat([gold_avg(), gld_me()], axis=1).dropna()
    print("Gold avg vs GLD month-end: corr", round(g2.corr().iloc[0, 1], 3), "autocorr avg",
          round(g2.iloc[:, 0].autocorr(), 3), "GLD", round(g2.iloc[:, 1].autocorr(), 3))
    # daily FF vs monthly FF consistency
    dm = (1 + ff_daily["US_EQ"]).groupby(ff_daily.index.to_period("M")).prod() - 1
    dm.index = me(dm.index)
    z = pd.concat([dm, us_eq], axis=1).dropna()
    print("FF daily compounded vs FF monthly: max abs diff", float((z.iloc[:, 0] - z.iloc[:, 1]).abs().max()))


if __name__ == "__main__":
    main()
