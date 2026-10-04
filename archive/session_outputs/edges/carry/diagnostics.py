"""Data-quality diagnostics of the carry signals (no returns): coverage, contract gaps, seasonality, sign agreement."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import carry as K  # noqa: E402

pd.set_option("display.width", 250)


def main() -> None:
    daily = pd.read_parquet(HERE / "carry_daily.parquet")
    c1 = pd.read_parquet(HERE / "signal_C1.parquet")
    c12 = pd.read_parquet(HERE / "signal_C12.parquet")
    obs = K.carry_observations()
    rows = []
    me = daily.index.to_series().groupby(daily.index.to_period("M")).max().values
    for r in K.ROOTS:
        d = daily[r]
        first = d.first_valid_index()
        span = d.loc[first:]
        o = obs[obs.root == r]
        m = c1[r].reindex(me).dropna()
        # seasonality: share of month-end C1 variance explained by calendar-month means
        if len(m) > 36:
            mm = m.groupby(m.index.month).transform("mean")
            r2 = 1 - ((m - mm) ** 2).sum() / ((m - m.mean()) ** 2).sum()
        else:
            r2 = np.nan
        both = pd.concat([c1[r].reindex(me), c12[r].reindex(me)], axis=1).dropna()
        rows.append(dict(
            root=r, cls=[k for k, v in K.CLASSES.items() if r in v][0], first=str(first.date()),
            valid_share=float(span.notna().mean()), dt_med_m=float(o.dt_m.median()), dt_max_m=float(o.dt_m.max()),
            carry_mean=float(m.mean()), carry_sd=float(m.std()), c1_p05=float(m.quantile(0.05)),
            c1_p95=float(m.quantile(0.95)), season_r2=float(r2),
            sign_disagree_c1_c12=float((np.sign(both.iloc[:, 0]) != np.sign(both.iloc[:, 1])).mean()),
            corr_c1_c12=float(both.iloc[:, 0].corr(both.iloc[:, 1])),
            pos_share_c12=float((c12[r].reindex(me).dropna() > 0).mean()),
        ))
    t = pd.DataFrame(rows)
    t.to_csv(HERE / "signal_diagnostics.csv", index=False)
    print(t.round(3).to_string(index=False))
    # year-end C12 carry by root (annualised, %), a plain sanity check of signs
    ye = c12.groupby(c12.index.year).last() * 100
    print((ye.round(1)).to_string())
    ye.round(3).to_csv(HERE / "carry_c12_year_end_pct.csv")
    # book diagnostics: scale cap binding and gross notional
    bd = pd.read_csv(HERE / "book_diagnostics.csv")
    s = bd.groupby(["signal", "freq", "cons", "book"]).agg(
        n_med=("n", "median"), scale_med=("scale", "median"), cap_bind=("scale", lambda x: float((x >= 3.999).mean())),
        gross_med=("gross", "median"), gross_max=("gross", "max"))
    print(s.round(2).to_string())
    s.round(4).to_csv(HERE / "book_diagnostics_summary.csv")


if __name__ == "__main__":
    main()
