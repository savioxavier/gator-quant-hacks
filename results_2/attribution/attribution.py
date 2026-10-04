"""Factor attribution of v2 (T4xE1) and a paired block bootstrap of the portfolio Sharpe increment.

Exploratory, post-result. The specification is results_2/attribution/SPEC.md, fixed before this script computed
anything; the script refuses to run unless that file's sha256 (line endings normalised to LF) equals SPEC_SHA256.

Run from the repository root:

    python results_2/attribution/attribution.py

Reads only committed derived return series (no backtest is run or rerun, no price levels, no raw asset returns).
Writes only results_2/attribution/: factor_attribution.csv, correlations.csv, bootstrap.csv, ATTRIBUTION.md.
Exits non-zero, writing nothing, if an input is missing or a cross-check fails.
"""
from __future__ import annotations

import hashlib
import math
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------- fixed by SPEC.md
OUT = Path("results_2/attribution")
SPEC = OUT / "SPEC.md"
SPEC_SHA256 = "b4ca64d849c0c193632f5d0ce1ff8772645e41174176fcf4be6937df67eb9a46"

D4_DAILY = Path("backtests/results/v2_d4/daily_returns.parquet")
D4_METRICS = Path("backtests/results/v2_d4/metrics.csv")
D3_DAILY = Path("backtests/results/v2_oos/daily_returns.parquet")
INPUTS = (D4_DAILY, D4_METRICS, D3_DAILY)

ANN = 252
SEED = 20261004
N_BOOT = 10_000
BLOCKS = (20, 10, 40)            # 20 primary; 10 and 40 sensitivity
PRIMARY_BLOCK = 20
BASES = ("net_1x", "net_2x")     # net 1x primary; net 2x sensitivity
PRIMARY_BASIS = "net_1x"
STATUS = "exploratory, post-result"

WINDOWS = {  # name: (labels in the parquet's `window` column, start, end, expected rows)
    "full_is": (("selection", "validation"), "2016-01-04", "2024-10-02", 2202),
    "oos": (("oos",), "2024-10-03", "2026-10-02", 501),
}

DEP = {"original": "T4xE1|original|net_1x", "both": "T4xE1|both|net_1x"}
FACTOR_SETS = {
    "primary": {"DUR_USD": "BH7525hold|hold|net_1x", "MOM": "MxE1|both|net_1x", "LEX": "LEXALLxE1|both|net_1x"},
    "S1_matched": {"DUR_USD": "BH7525hold|hold|net_1x", "MOM": "MxE1|original|net_1x",
                   "LEX": "LEXALLxE1|original|net_1x"},
}
FACTOR_SET_FOR = {"original": ("primary", "S1_matched"), "both": ("primary",)}
MODELS = {"M0": (), "M1": ("DUR_USD",), "M2": ("MOM",), "M3": ("LEX",), "M4": ("DUR_USD", "MOM", "LEX")}
FACTORS = ("DUR_USD", "MOM", "LEX")

CORR_SERIES = {
    "v2_original": "T4xE1|original|net_1x",
    "v2_both": "T4xE1|both|net_1x",
    "DUR_USD": "BH7525hold|hold|net_1x",
    "MOM_both": "MxE1|both|net_1x",
    "LEX_both": "LEXALLxE1|both|net_1x",
    "MOM_original": "MxE1|original|net_1x",
    "LEX_original": "LEXALLxE1|original|net_1x",
}

P0 = "core_ER_6|as_committed|{basis}"
P1 = "core_ER_6+T4xE1|{variant}|{basis}"
BOOT_VARIANTS = ("original", "both")

# frozen D-3 column -> v2_d4 column that must equal it
D3_EQUAL = {
    "T4xE1|net_1x": "T4xE1|original|net_1x",
    "T4xE1|net_2x": "T4xE1|original|net_2x",
    "core_ER_6|net_1x": "core_ER_6|as_committed|net_1x",
    "core_ER_6|net_2x": "core_ER_6|as_committed|net_2x",
    "core_ER_6+T4xE1|net_1x": "core_ER_6+T4xE1|original|net_1x",
    "core_ER_6+T4xE1|net_2x": "core_ER_6+T4xE1|original|net_2x",
}
# (series, variant) whose published Sharpe and NW t are recomputed and compared
PUBLISHED = (("T4xE1", "original"), ("T4xE1", "both"), ("MxE1", "both"), ("MxE1", "original"),
             ("LEXALLxE1", "both"), ("LEXALLxE1", "original"), ("BH7525hold", "hold"),
             ("core_ER_6", "as_committed"), ("core_ER_6+T4xE1", "original"), ("core_ER_6+T4xE1", "both"))
TOL_EQUAL = 1e-12
TOL_PUBLISHED = 1e-9


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def sha256(path: Path, text: bool) -> str:
    b = path.read_bytes()
    if text:
        b = b.replace(b"\r\n", b"\n")
    return hashlib.sha256(b).hexdigest()


# ----------------------------------------------------------------------------- statistics
def nw_lag(n: int) -> int:
    return int(math.floor(4 * (n / 100) ** (2 / 9)))


def sharpe(x: np.ndarray) -> float:
    return float(x.mean() / x.std(ddof=1) * math.sqrt(ANN))


def ols_hac(y: np.ndarray, f: np.ndarray | None) -> dict:
    """OLS with intercept; Newey-West HAC (Bartlett, L = floor(4 (n/100)^(2/9))), no small-sample correction."""
    n = len(y)
    X = np.ones((n, 1)) if f is None or f.shape[1] == 0 else np.column_stack([np.ones(n), f])
    k = X.shape[1]
    xtx_inv = np.linalg.inv(X.T @ X)
    b = xtx_inv @ (X.T @ y)
    u = y - X @ b
    L = nw_lag(n)
    g = X * u[:, None]
    S = g.T @ g
    for lag in range(1, L + 1):
        G = g[lag:].T @ g[:-lag]
        S += (1 - lag / (L + 1)) * (G + G.T)
    V = xtx_inv @ S @ xtx_inv
    se = np.sqrt(np.diag(V))
    sst = float((y - y.mean()) @ (y - y.mean()))
    ssr = float(u @ u)
    r2 = 1 - ssr / sst if k > 1 else 0.0
    return {"b": b, "t": b / se, "L": L, "n": n, "k": k, "r2": r2,
            "adj_r2": 1 - (1 - r2) * (n - 1) / (n - k) if k > 1 else 0.0,
            "resid_vol_ann": math.sqrt(ssr / (n - k)) * math.sqrt(ANN)}


def nw_t_mean(x: np.ndarray) -> float:
    """Independent restatement of v2lib.nw_t (used to check ols_hac's intercept-only t)."""
    n = len(x)
    L = nw_lag(n)
    e = x - x.mean()
    s = e @ e / n
    for k in range(1, L + 1):
        s += 2 * (1 - k / (L + 1)) * (e[k:] @ e[:-k]) / n
    return float(x.mean() / math.sqrt(s / n))


def cbb_starts(n: int, b: int) -> np.ndarray:
    rng = np.random.Generator(np.random.PCG64(SEED))
    return rng.integers(0, n, size=(N_BOOT, -(-n // b)))


def cbb_sharpe_diff(p1: np.ndarray, p0: np.ndarray, starts: np.ndarray, b: int, chunk: int = 1000) -> np.ndarray:
    n = len(p1)
    off = np.arange(b)
    out = np.empty(starts.shape[0])
    for i in range(0, starts.shape[0], chunk):
        st = starts[i:i + chunk]
        idx = ((st[:, :, None] + off[None, None, :]) % n).reshape(st.shape[0], -1)[:, :n]
        a, z = p1[idx], p0[idx]
        s1 = a.mean(axis=1) / a.std(axis=1, ddof=1)
        s0 = z.mean(axis=1) / z.std(axis=1, ddof=1)
        out[i:i + chunk] = (s1 - s0) * math.sqrt(ANN)
    return out


# ----------------------------------------------------------------------------- formatting helpers
def pct(x: float, d: int = 2) -> str:
    return f"{100 * x:.{d}f}%"


def num(x: float, d: int = 3) -> str:
    return "" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{d}f}"


def r2_reading(r2: float) -> str:
    if r2 >= 0.50:
        return "mostly explained by these three series"
    if r2 >= 0.10:
        return "partly explained"
    return "mostly not explained"


def md_table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


# ----------------------------------------------------------------------------- main
def main() -> None:
    for p in INPUTS:
        if not p.is_file():
            fail(f"missing input {p.as_posix()} (run from the repository root)")
    if not SPEC.is_file():
        fail(f"missing {SPEC.as_posix()}: the specification must exist before computing")
    spec_hash = sha256(SPEC, text=True)
    if spec_hash != SPEC_SHA256:
        fail(f"{SPEC.as_posix()} sha256 {spec_hash} != fixed {SPEC_SHA256}; the specification changed")

    d = pd.read_parquet(D4_DAILY)
    d3 = pd.read_parquet(D3_DAILY)
    met = pd.read_csv(D4_METRICS)
    checks: list[tuple[str, str]] = []

    needed = set(DEP.values()) | set(CORR_SERIES.values())
    for fs in FACTOR_SETS.values():
        needed |= set(fs.values())
    for basis in BASES:
        needed.add(P0.format(basis=basis))
        needed |= {P1.format(variant=v, basis=basis) for v in BOOT_VARIANTS}
    missing = sorted(c for c in needed | set(D3_EQUAL.values()) | {"window"} if c not in d.columns)
    if missing:
        fail(f"columns missing from {D4_DAILY.as_posix()}: {missing}")
    missing3 = sorted(c for c in D3_EQUAL if c not in d3.columns)
    if missing3:
        fail(f"columns missing from {D3_DAILY.as_posix()}: {missing3}")

    # --- check 1: windows
    win = {}
    for w, (labels, a, b, n_exp) in WINDOWS.items():
        sub = d[d["window"].isin(labels)]
        if len(sub) != n_exp or str(sub.index[0].date()) != a or str(sub.index[-1].date()) != b:
            fail(f"window {w}: {len(sub)} rows {sub.index[0].date()}..{sub.index[-1].date()}, expected {n_exp} {a}..{b}")
        if sub[sorted(needed)].isna().any().any():
            fail(f"window {w}: missing values in a series used here")
        mrow = met[(met.series == "T4xE1") & (met.variant == "original") & (met.window == w)]
        if len(mrow) != 1 or int(mrow.n_days.iloc[0]) != n_exp or mrow.start.iloc[0] != a or mrow.end.iloc[0] != b:
            fail(f"window {w} disagrees with {D4_METRICS.as_posix()}")
        win[w] = sub
    checks.append(("window rows and dates (full IS 2202, OOS 501) agree with metrics.csv", "pass"))

    # --- check 2: originals equal the frozen D-3 file
    if not d.index.equals(d3.index):
        fail("v2_d4 and v2_oos daily files have different dates")
    worst = 0.0
    for c3, c4 in D3_EQUAL.items():
        a4, a3 = d[c4].to_numpy(dtype=float), d3[c3].to_numpy(dtype=float)
        if not np.array_equal(np.isnan(a4), np.isnan(a3)):
            fail(f"{c4} and frozen D-3 {c3} have missing values on different dates")
        diff = float(np.nanmax(np.abs(a4 - a3)))
        worst = max(worst, diff)
        if not diff <= TOL_EQUAL:
            fail(f"{c4} differs from frozen D-3 {c3} by {diff}")
    checks.append((f"original T4xE1, core_ER_6 and core_ER_6+T4xE1 (net 1x, net 2x) vs frozen v2_oos file, "
                   f"all {len(d)} dates: max abs diff {worst:.1e}", "pass"))

    # --- check 3: recomputed published Sharpe and NW t
    worst_s = worst_t = 0.0
    for s, v in PUBLISHED:
        for w in WINDOWS:
            row = met[(met.series == s) & (met.variant == v) & (met.window == w)]
            if len(row) != 1:
                fail(f"metrics.csv has no unique row for {s}|{v}|{w}")
            x1 = win[w][f"{s}|{v}|net_1x"].to_numpy()
            x2 = win[w][f"{s}|{v}|net_2x"].to_numpy()
            ds = max(abs(sharpe(x1) - row.sharpe_net1x.iloc[0]), abs(sharpe(x2) - row.sharpe_net2x.iloc[0]))
            t_hac = float(ols_hac(x1, None)["t"][0])
            dt = max(abs(t_hac - row.nw_t.iloc[0]), abs(nw_t_mean(x1) - row.nw_t.iloc[0]))
            worst_s, worst_t = max(worst_s, ds), max(worst_t, dt)
            if not (ds <= TOL_PUBLISHED and dt <= TOL_PUBLISHED):
                fail(f"recomputed Sharpe/NW t of {s}|{v}|{w} differ from metrics.csv ({ds}, {dt})")
    checks.append((f"Sharpe net 1x / net 2x and NW t of the mean recomputed for {len(PUBLISHED)} series x 2 windows "
                   f"vs metrics.csv: max abs diff {worst_s:.1e} (Sharpe), {worst_t:.1e} (NW t)", "pass"))

    # ------------------------------------------------------------------------- Part A
    arows = []
    for dv, dcol in DEP.items():
        for fs_name in FACTOR_SET_FOR[dv]:
            fs = FACTOR_SETS[fs_name]
            for w, sub in win.items():
                y = sub[dcol].to_numpy()
                mean_ann = float(y.mean() * ANN)
                for m, regs in MODELS.items():
                    f = sub[[fs[r] for r in regs]].to_numpy() if regs else None
                    res = ols_hac(y, f)
                    row = {
                        "status": STATUS, "dependent": "T4xE1", "dependent_variant": dv, "dependent_column": dcol,
                        "factor_set": fs_name, "window": w, "start": str(sub.index[0].date()),
                        "end": str(sub.index[-1].date()), "n": res["n"], "nw_lag": res["L"], "model": m,
                        "regressors": "+".join(regs) if regs else "intercept only",
                        "mean_ann": mean_ann, "alpha_daily": float(res["b"][0]),
                        "alpha_ann": float(res["b"][0] * ANN), "alpha_t": float(res["t"][0]),
                    }
                    for fac in FACTORS:
                        if fac in regs:
                            j = regs.index(fac) + 1
                            row[f"beta_{fac}"], row[f"t_{fac}"] = float(res["b"][j]), float(res["t"][j])
                        else:
                            row[f"beta_{fac}"], row[f"t_{fac}"] = np.nan, np.nan
                    row.update({
                        "r2": res["r2"] if regs else np.nan, "adj_r2": res["adj_r2"] if regs else np.nan,
                        "resid_vol_ann": res["resid_vol_ann"],
                        "alpha_share_of_mean": float(res["b"][0] * ANN / mean_ann) if mean_ann != 0 else np.nan,
                        "col_DUR_USD": fs["DUR_USD"] if "DUR_USD" in regs else "",
                        "col_MOM": fs["MOM"] if "MOM" in regs else "",
                        "col_LEX": fs["LEX"] if "LEX" in regs else "",
                        "reading_rule": r2_reading(res["r2"]) if m == "M4" else "",
                        "spec_sha256": SPEC_SHA256,
                    })
                    arows.append(row)
    fa = pd.DataFrame(arows)

    # --- check 4 (optional, informational): the HAC regressions against an independent implementation
    try:
        import statsmodels.api as sm
    except ImportError:
        checks.append(("HAC regressions vs statsmodels OLS HAC (use_correction=False)", "skipped: not installed"))
    else:
        worst_b = worst_tt = 0.0
        for r in fa[fa.model != "M0"].itertuples():
            fs = FACTOR_SETS[r.factor_set]
            regs = MODELS[r.model]
            sub = win[r.window]
            fit = sm.OLS(sub[DEP[r.dependent_variant]].to_numpy(), sm.add_constant(sub[[fs[x] for x in regs]].to_numpy()),
                         ).fit(cov_type="HAC", cov_kwds={"maxlags": nw_lag(len(sub)), "use_correction": False})
            mine_b = [r.alpha_daily] + [getattr(r, f"beta_{x}") for x in regs]
            mine_t = [r.alpha_t] + [getattr(r, f"t_{x}") for x in regs]
            worst_b = max(worst_b, float(np.max(np.abs(fit.params - mine_b))))
            worst_tt = max(worst_tt, float(np.max(np.abs(fit.tvalues - mine_t))))
        if not (worst_b <= TOL_PUBLISHED and worst_tt <= 1e-6):
            fail(f"HAC regressions disagree with statsmodels ({worst_b}, {worst_tt})")
        checks.append((f"HAC regressions (M1..M4, all rows) vs statsmodels OLS HAC with use_correction=False: max abs "
                       f"diff {worst_b:.1e} (coefficients), {worst_tt:.1e} (t)", "pass"))

    crow = []
    for w, sub in win.items():
        c = sub[list(CORR_SERIES.values())].corr()
        names = list(CORR_SERIES)
        for i, a in enumerate(names):
            for j, b in enumerate(names):
                crow.append({"status": STATUS, "window": w, "start": str(sub.index[0].date()),
                             "end": str(sub.index[-1].date()), "n": len(sub), "series_a": a, "series_b": b,
                             "column_a": CORR_SERIES[a], "column_b": CORR_SERIES[b],
                             "corr": float(c.iloc[i, j]), "spec_sha256": SPEC_SHA256})
    corr = pd.DataFrame(crow)

    # ------------------------------------------------------------------------- Part B
    brows = []
    for w, sub in win.items():
        n = len(sub)
        for b in BLOCKS:
            starts = cbb_starts(n, b)
            for v in BOOT_VARIANTS:
                for basis in BASES:
                    p1 = sub[P1.format(variant=v, basis=basis)].to_numpy()
                    p0 = sub[P0.format(basis=basis)].to_numpy()
                    dist = cbb_sharpe_diff(p1, p0, starts, b)
                    q05, q95, q025, q975 = np.quantile(dist, [0.05, 0.95, 0.025, 0.975])
                    dd = p1 - p0
                    brows.append({
                        "status": STATUS, "window": w, "start": str(sub.index[0].date()),
                        "end": str(sub.index[-1].date()), "n": n, "variant": v, "basis": basis,
                        "block_len": b, "n_resamples": N_BOOT, "seed": SEED,
                        "primary": bool(b == PRIMARY_BLOCK and basis == PRIMARY_BASIS),
                        "p1": P1.format(variant=v, basis=basis), "p0": P0.format(basis=basis),
                        "sharpe_p1": sharpe(p1), "sharpe_p0": sharpe(p0), "diff_obs": sharpe(p1) - sharpe(p0),
                        "vol_p1": float(p1.std(ddof=1) * math.sqrt(ANN)),
                        "vol_p0": float(p0.std(ddof=1) * math.sqrt(ANN)),
                        "boot_mean": float(dist.mean()), "boot_sd": float(dist.std(ddof=1)),
                        "ci90_lo": float(q05), "ci90_hi": float(q95), "ci95_lo": float(q025), "ci95_hi": float(q975),
                        "share_le0": float((dist <= 0).mean()),
                        "nw_lag": nw_lag(n), "nw_t_mean_p1": nw_t_mean(p1), "nw_t_mean_p0": nw_t_mean(p0),
                        "nw_t_mean_diff": nw_t_mean(dd), "mean_diff_ann": float(dd.mean() * ANN),
                        "corr_p1_p0": float(np.corrcoef(p1, p0)[0, 1]),
                        "spec_sha256": SPEC_SHA256,
                    })
    bs = pd.DataFrame(brows)

    # ------------------------------------------------------------------------- write
    report = render(fa, corr, bs, checks, spec_hash)   # rendered before anything is written
    OUT.mkdir(parents=True, exist_ok=True)
    fa.to_csv(OUT / "factor_attribution.csv", index=False, lineterminator="\n", float_format="%.10g")
    corr.to_csv(OUT / "correlations.csv", index=False, lineterminator="\n", float_format="%.10g")
    bs.to_csv(OUT / "bootstrap.csv", index=False, lineterminator="\n", float_format="%.10g")
    (OUT / "ATTRIBUTION.md").write_text(report, encoding="utf-8", newline="\n")
    print(f"wrote {len(fa)} attribution rows, {len(corr)} correlation rows, {len(bs)} bootstrap rows to {OUT.as_posix()}")


# ----------------------------------------------------------------------------- report
def render(fa: pd.DataFrame, corr: pd.DataFrame, bs: pd.DataFrame, checks, spec_hash: str) -> str:
    spec_text = SPEC.read_text(encoding="utf-8").replace("\r\n", "\n")
    spec_lines = [("#" + ln) if ln.startswith("#") else ln for ln in spec_text.rstrip("\n").split("\n")]
    wl = {"full_is": "full IS 2016-01-04..2024-10-02 (2202 sessions)", "oos": "OOS 2024-10-03..2026-10-02 (501 sessions)"}
    vl = {"original": "original (frozen D-3)", "both": "D-4 both fixes"}
    out = []
    out.append("# v2 factor attribution and portfolio-increment bootstrap\n")
    out.append(f"**Status: {STATUS}.** Every number below was computed after v2's in-sample, D-3 out-of-sample and "
               "D-4 results were published and read. The method was fixed in `SPEC.md` before this computation "
               "(reproduced next, headings moved down one level). These results carry no inferential weight for the "
               "registered hypothesis. The registered verdict stands: v2 FAILED its decision rule.\n")
    out.append(f"Generated by `results_2/attribution/attribution.py` (run from the repository root). SPEC.md sha256 "
               f"(LF) `{spec_hash}`, checked by the script before computing.\n")
    out.append("\n".join(spec_lines) + "\n")

    out.append("## Inputs and checks\n")
    rows = [[f"`{p.as_posix()}`", f"`{sha256(p, text=p.suffix != '.parquet')}`"] for p in INPUTS]
    out.append(md_table(["input (read only)", "sha256 (LF-normalised for text files)"], rows) + "\n")
    out.append(md_table(["check", "result"], [[a, b] for a, b in checks]) + "\n")
    out.append(f"Software: Python {platform.python_version()}, numpy {np.__version__}, pandas {pd.__version__}.\n")

    # --- Part A
    out.append("## Part A results: factor attribution (exploratory, post-result)\n")
    lag_is = int(fa[fa.window == "full_is"].nw_lag.iloc[0])
    lag_oos = int(fa[fa.window == "oos"].nw_lag.iloc[0])
    out.append("Daily net-1x excess returns. alpha_ann = 252 x the daily intercept (arithmetic, excess-return units). "
               f"t-statistics are Newey-West HAC, Bartlett kernel, L = floor(4 (n/100)^(2/9)): L = {lag_is} on full "
               f"IS (n = 2202), L = {lag_oos} on OOS (n = 501), with no small-sample correction. Primary factor set: "
               "DUR_USD = BH7525hold, MOM = MxE1 (both fixes), LEX = LEXALLxE1 (both fixes).\n")
    prim = fa[fa.factor_set == "primary"]
    for w in WINDOWS:
        out.append(f"### {wl[w]}\n")
        rows = []
        for dv in DEP:
            for m in MODELS:
                r = prim[(prim.dependent_variant == dv) & (prim.window == w) & (prim.model == m)].iloc[0]
                betas = []
                for fac in FACTORS:
                    betas.append("" if math.isnan(r[f"beta_{fac}"]) else f"{r[f'beta_{fac}']:.3f} ({r[f't_{fac}']:.2f})")
                rows.append([vl[dv], f"{m}: {r.regressors}", pct(r.alpha_ann), num(r.alpha_t, 2), *betas,
                             num(r.r2, 3), num(r.adj_r2, 3), num(r.alpha_share_of_mean, 2)])
        out.append(md_table(["v2 series", "model", "alpha ann.", "alpha t", "beta DUR_USD (t)", "beta MOM (t)",
                             "beta LEX (t)", "R^2", "adj. R^2", "alpha / mean"], rows) + "\n")
        out.append("M0's alpha is the series' own annualised mean, and its t is the published NW t of the mean.\n")

    out.append("### Readings under the SPEC's rules\n")
    rl = []
    for w in WINDOWS:
        for dv in DEP:
            g = prim[(prim.dependent_variant == dv) & (prim.window == w)].set_index("model")
            r4 = g.loc["M4"]
            singles = {"M1": "duration/dollar (DUR_USD)", "M2": "momentum (MOM)", "M3": "its lexicon leg (LEX)"}
            met = [singles[k] for k in singles if g.loc[k, "r2"] >= 0.50]
            sig = [f for f in FACTORS if abs(r4[f"t_{f}"]) >= 1.96]
            rl.append(
                f"- **{wl[w]}, {vl[dv]}.** Joint R^2 {r4.r2:.3f}, so the joint model's reading is "
                f"\"{r2_reading(r4.r2)}\". Single-factor R^2: DUR_USD {g.loc['M1', 'r2']:.3f}, MOM "
                f"{g.loc['M2', 'r2']:.3f}, LEX {g.loc['M3', 'r2']:.3f}. "
                + (f"The \"mostly ...\" rule is met for {', '.join(met)}. " if met else
                   "No single factor reaches R^2 0.50, so v2 is not called mostly duration/dollar, mostly momentum or "
                   "mostly its lexicon leg. ")
                + f"Joint alpha {pct(r4.alpha_ann)} a year (t {r4.alpha_t:.2f}"
                + ("; not distinguishable from zero" if abs(r4.alpha_t) < 1.96 else "; |t| >= 1.96")
                + f"), against a raw mean of {pct(r4.mean_ann)}. "
                + (f"Joint betas with |t| >= 1.96: {', '.join(sig)}." if sig else
                   "No joint beta has |t| >= 1.96.")
            )
    out.append("\n".join(rl) + "\n")

    out.append("### Sensitivity S1: original v2 against matching-variant factors (MxE1 and LEXALLxE1 original)\n")
    s1 = fa[fa.factor_set == "S1_matched"]
    rows = []
    for w in WINDOWS:
        for m in ("M2", "M3", "M4"):
            r = s1[(s1.window == w) & (s1.model == m)].iloc[0]
            p = prim[(prim.dependent_variant == "original") & (prim.window == w) & (prim.model == m)].iloc[0]
            betas = ["" if math.isnan(r[f"beta_{f}"]) else f"{r[f'beta_{f}']:.3f} ({r[f't_{f}']:.2f})" for f in FACTORS]
            rows.append([w, f"{m}: {r.regressors}", pct(r.alpha_ann), num(r.alpha_t, 2), *betas, num(r.r2, 3),
                         num(p.r2, 3)])
    out.append(md_table(["window", "model", "alpha ann.", "alpha t", "beta DUR_USD (t)", "beta MOM (t)",
                         "beta LEX (t)", "R^2 (S1)", "R^2 (primary)"], rows) + "\n")

    out.append("### Correlations of daily net-1x excess returns\n")
    names = list(CORR_SERIES)
    for w in WINDOWS:
        sub = corr[corr.window == w]
        rows = []
        for a in names:
            rows.append([a] + [f"{sub[(sub.series_a == a) & (sub.series_b == b)]['corr'].iloc[0]:.3f}" for b in names])
        out.append(f"**{wl[w]}**\n")
        out.append(md_table(["", *names], rows) + "\n")

    # --- post-result commentary on the reviewer's question (templated from the numbers above)
    def g(dv, w, m, col):
        return float(prim[(prim.dependent_variant == dv) & (prim.window == w) & (prim.model == m)][col].iloc[0])

    def cc(w, a, b):
        sub = corr[(corr.window == w) & (corr.series_a == a) & (corr.series_b == b)]
        return float(sub["corr"].iloc[0])

    def both_vals(w, m, col, fmt):
        return f"{fmt(g('original', w, m, col))} / {fmt(g('both', w, m, col))}"

    f3 = lambda x: f"{x:.3f}"   # noqa: E731
    f2 = lambda x: f"{x:.2f}"   # noqa: E731
    out.append("### Is v2 mostly duration, dollar or momentum exposure? (post-result commentary)\n")
    out.append("Pairs of numbers are original / D-4 both fixes.\n")
    out.append(
        "- **Not under the fixed rules, in either window or variant.** DUR_USD alone has R^2 "
        f"{both_vals('full_is', 'M1', 'r2', f3)} on full IS and {both_vals('oos', 'M1', 'r2', f3)} OOS. MOM alone "
        f"has {both_vals('full_is', 'M2', 'r2', f3)} and {both_vals('oos', 'M2', 'r2', f3)}. Neither comes near "
        "0.50.\n"
        "- **What explains v2 is its own lexicon leg.** LEX alone has R^2 "
        f"{both_vals('full_is', 'M3', 'r2', f3)} on full IS and {both_vals('oos', 'M3', 'r2', f3)} OOS. On full IS the "
        f"joint alpha is {pct(g('original', 'full_is', 'M4', 'alpha_ann'))} / "
        f"{pct(g('both', 'full_is', 'M4', 'alpha_ann'))} a year (t {both_vals('full_is', 'M4', 'alpha_t', f2)}), "
        f"against raw means of {pct(g('original', 'full_is', 'M0', 'alpha_ann'))} / "
        f"{pct(g('both', 'full_is', 'M0', 'alpha_ann'))}. v2's in-sample mean is accounted for by its co-movement "
        f"with the lexicon-only series (joint LEX beta {both_vals('full_is', 'M4', 'beta_LEX', f3)}). So the "
        "stance-model half of T4 added no in-sample return beyond what the lexicon-only series explains. Some "
        "overlap is built in, because LEX is half of T4's signal.\n"
        "- **Momentum adds nothing once LEX is in the model.** Alone, MOM's full-IS beta is "
        f"{both_vals('full_is', 'M2', 'beta_MOM', f3)} (t {both_vals('full_is', 'M2', 't_MOM', f2)}). Jointly it is "
        f"{both_vals('full_is', 'M4', 'beta_MOM', f3)} (t {both_vals('full_is', 'M4', 't_MOM', f2)}). Its link with "
        f"v2 runs through the lexicon leg: corr(MOM, LEX) is {cc('full_is', 'MOM_both', 'LEX_both'):.3f} on full "
        "IS.\n"
        f"- **The OOS joint fit is a collinearity effect.** The OOS joint R^2 of "
        f"{both_vals('oos', 'M4', 'r2', f3)} exceeds the single-factor R^2s added together. The reason is that "
        f"DUR_USD and LEX are strongly correlated OOS ({cc('oos', 'DUR_USD', 'LEX_both'):.3f}, against "
        f"{cc('full_is', 'DUR_USD', 'LEX_both'):.3f} on full IS). With both in the model, LEX's beta is "
        f"{both_vals('oos', 'M4', 'beta_LEX', f3)} and DUR_USD's is {both_vals('oos', 'M4', 'beta_DUR_USD', f3)} "
        f"(t {both_vals('oos', 'M4', 't_DUR_USD', f2)}). Read literally, v2 moved like the lexicon strategy minus the "
        "part of that strategy's returns that tracked the long 75/25 mix in this window. This is a fit on 501 "
        f"sessions, not a stable duration short: DUR_USD alone has R^2 {both_vals('oos', 'M1', 'r2', f3)} OOS, and "
        f"the full-IS joint DUR_USD beta is only {both_vals('full_is', 'M4', 'beta_DUR_USD', f3)} "
        f"(t {both_vals('full_is', 'M4', 't_DUR_USD', f2)}).\n"
        "- **Neither the raw mean nor the alpha is distinguishable from zero OOS.** The raw-mean NW t is "
        f"{both_vals('oos', 'M0', 'alpha_t', f2)} and the joint-alpha t is {both_vals('oos', 'M4', 'alpha_t', f2)}. "
        "The regressions therefore describe co-movement only. They cannot say whether v2 earns a return beyond "
        "these series.\n")

    # --- Part B
    out.append("## Part B results: paired block bootstrap of the Sharpe increment (exploratory, post-result)\n")
    out.append(f"D = Sharpe(core_ER_6+T4xE1) - Sharpe(core_ER_6). Circular block bootstrap of the paired daily rows, "
               f"{N_BOOT:,} resamples, seed {SEED}; the same indices serve both variants and both bases. Percentile "
               "intervals. \"share <= 0\" is a descriptive one-sided bootstrap proportion, not a p-value.\n")
    prim_b = bs[bs.primary]
    rows = []
    for w in ("oos", "full_is"):
        for v in BOOT_VARIANTS:
            r = prim_b[(prim_b.window == w) & (prim_b.variant == v)].iloc[0]
            rows.append([w, vl[v], f"{r.sharpe_p1:.4f}", f"{r.sharpe_p0:.4f}", f"{r.diff_obs:+.4f}",
                         f"{r.boot_mean:+.4f}", f"{r.boot_sd:.4f}", f"[{r.ci90_lo:+.4f}, {r.ci90_hi:+.4f}]",
                         f"[{r.ci95_lo:+.4f}, {r.ci95_hi:+.4f}]", pct(r.share_le0, 1)])
    out.append("### Primary: block length 20, net 1x\n")
    out.append(md_table(["window", "variant", "Sharpe core+v2", "Sharpe core", "D observed", "bootstrap mean of D",
                         "bootstrap sd of D", "90% interval", "95% interval", "share D <= 0"], rows) + "\n")

    out.append("### Sensitivity: block lengths 10 and 40, and net 2x\n")
    rows = []
    for w in ("oos", "full_is"):
        for v in BOOT_VARIANTS:
            for basis in BASES:
                for b in BLOCKS:
                    r = bs[(bs.window == w) & (bs.variant == v) & (bs.basis == basis) & (bs.block_len == b)].iloc[0]
                    rows.append([w, v, basis.replace("_", " "), str(b), f"{r.diff_obs:+.4f}",
                                 f"[{r.ci90_lo:+.4f}, {r.ci90_hi:+.4f}]", f"[{r.ci95_lo:+.4f}, {r.ci95_hi:+.4f}]",
                                 pct(r.share_le0, 1), "yes" if r.primary else ""])
    out.append(md_table(["window", "variant", "basis", "block", "D observed", "90% interval", "95% interval",
                         "share D <= 0", "primary"], rows) + "\n")

    out.append("### Contrast with mean-return Newey-West t statistics (net 1x)\n")
    rows = []
    for w in ("oos", "full_is"):
        for v in BOOT_VARIANTS:
            r = prim_b[(prim_b.window == w) & (prim_b.variant == v)].iloc[0]
            rows.append([w, vl[v], str(int(r.nw_lag)), f"{r.nw_t_mean_p1:.4f}", f"{r.nw_t_mean_p0:.4f}",
                         pct(r.mean_diff_ann), f"{r.nw_t_mean_diff:.4f}", f"{r.corr_p1_p0:.3f}"])
    out.append(md_table(["window", "variant", "NW lag", "NW t, mean of core+v2", "NW t, mean of core",
                         "mean of daily difference, ann.", "NW t, mean of daily difference", "corr(core+v2, core)"],
                        rows) + "\n")

    out.append("### Readings under the SPEC's rules\n")
    rl = []
    for w in ("oos", "full_is"):
        for v in BOOT_VARIANTS:
            r = prim_b[(prim_b.window == w) & (prim_b.variant == v)].iloc[0]
            at10 = not (r.ci90_lo <= 0 <= r.ci90_hi)
            at5 = not (r.ci95_lo <= 0 <= r.ci95_hi)
            verdict = ("distinguishable from zero at the 5% two-sided level" if at5 else
                       "distinguishable from zero at the 10% but not the 5% two-sided level" if at10 else
                       "not distinguishable from zero at the 10% two-sided level")
            sens = bs[(bs.window == w) & (bs.variant == v)]
            n_ex90 = int(((sens.ci90_lo > 0) | (sens.ci90_hi < 0)).sum())
            rl.append(
                f"- **{wl[w]}, {vl[v]}.** D = {r.diff_obs:+.4f} (core+v2 {r.sharpe_p1:.4f} vs core "
                f"{r.sharpe_p0:.4f}); 90% interval [{r.ci90_lo:+.4f}, {r.ci90_hi:+.4f}], 95% interval "
                f"[{r.ci95_lo:+.4f}, {r.ci95_hi:+.4f}]; {pct(r.share_le0, 1)} of resamples have D <= 0. The "
                f"increment is {verdict}. Across all {len(sens)} configurations for this window and variant "
                f"(3 block lengths x 2 bases), {n_ex90} have a 90% interval that excludes 0.")
            rl.append(
                f"  The portfolio's own NW t of its mean is {r.nw_t_mean_p1:.4f} (core alone {r.nw_t_mean_p0:.4f}). "
                f"That t asks whether the portfolio's mean excess return is above zero, not whether adding v2 "
                f"helped. The mean-return analogue of the increment, the NW t of the mean daily difference "
                f"(core+v2 minus core), is {r.nw_t_mean_diff:.4f}, with an annualised mean difference of "
                f"{pct(r.mean_diff_ann)}. Both portfolios are scaled to the same 6% volatility target (realised "
                f"vol {pct(r.vol_p1)} vs {pct(r.vol_p0)}), so D mostly reflects the difference in means. The two "
                f"statistics differ in how they measure its noise.")
    out.append("\n".join(rl) + "\n")

    po = {v: prim_b[(prim_b.window == "oos") & (prim_b.variant == v)].iloc[0] for v in BOOT_VARIANTS}
    pi = {v: prim_b[(prim_b.window == "full_is") & (prim_b.variant == v)].iloc[0] for v in BOOT_VARIANTS}
    so = bs[bs.window == "oos"]
    out.append("### Summary of Part B (post-result commentary)\n")
    out.append(
        f"Adding v2 to core_ER_6 raised the OOS Sharpe by {po['original'].diff_obs:+.4f} (original) and "
        f"{po['both'].diff_obs:+.4f} (both fixes). The primary 90% intervals are "
        f"[{po['original'].ci90_lo:+.4f}, {po['original'].ci90_hi:+.4f}] and "
        f"[{po['both'].ci90_lo:+.4f}, {po['both'].ci90_hi:+.4f}], and {pct(po['original'].share_le0, 1)} / "
        f"{pct(po['both'].share_le0, 1)} of resamples show no gain. Under the fixed rule, the increment is not "
        f"distinguishable from zero. Across the OOS sensitivities, the share with D <= 0 ranges from "
        f"{pct(so.share_le0.min(), 1)} ({int(so.loc[so.share_le0.idxmin(), 'block_len'])}-session blocks) to "
        f"{pct(so.share_le0.max(), 1)} ({int(so.loc[so.share_le0.idxmax(), 'block_len'])}-session blocks), and "
        + ("no 90% interval excludes 0. " if not ((so.ci90_lo > 0) | (so.ci90_hi < 0)).any() else
           f"{int(((so.ci90_lo > 0) | (so.ci90_hi < 0)).sum())} of {len(so)} 90% intervals exclude 0. ")
        + f"On full IS the increment is {pi['original'].diff_obs:+.4f} / {pi['both'].diff_obs:+.4f}, with "
        f"{pct(pi['original'].share_le0, 1)} / {pct(pi['both'].share_le0, 1)} of resamples <= 0.\n\n"
        f"The headline OOS NW t of the portfolio's mean ({po['original'].nw_t_mean_p1:.2f} / "
        f"{po['both'].nw_t_mean_p1:.2f}) answers a different question: whether the combined book's mean excess "
        "return is above zero. It should not be quoted as evidence that v2 improved the portfolio. The matching "
        f"mean-return test of the increment has NW t {po['original'].nw_t_mean_diff:.2f} / "
        f"{po['both'].nw_t_mean_diff:.2f} OOS and {pi['original'].nw_t_mean_diff:.2f} / "
        f"{pi['both'].nw_t_mean_diff:.2f} on full IS.\n")

    out.append("## Caveats (some stated in the SPEC before computing, the rest context from committed results)\n")
    out.append(
        "1. DUR_USD is one fixed long 75% TLT / 25% UUP mix and cannot separate duration from dollar. v2's own "
        "positions trade TLT and UUP with opposite signs (hawkish: short TLT, long UUP), so a long-long mix is only a "
        "partial proxy for its exposures. Separate duration and dollar factors would need raw asset return series, "
        "which these outputs do not use.\n"
        "2. T4 averages the lexicon z and the stance z, so LEX shares half of v2's signal by construction. A high "
        "LEX beta or R^2 means v2 behaves like its own lexicon leg; it does not reveal a hidden risk premium.\n"
        "3. MOM and LEX are E1-sized strategies, not passive factor returns, so the betas describe co-movement with "
        "those strategies.\n"
        "4. The OOS window has 501 sessions and the full IS window 2202. Per `backtests/results/v2_oos/README.md`, "
        "the positive OOS Sharpe of T4xE1 comes from the last months of the window (Warsh period, 92 sessions). The "
        "portfolio gain from adding v2 is also a late-window effect, and 74% of full-IS P&L came from 2022. Neither the regressions nor the bootstrap condition on regime. The "
        "circular block bootstrap assumes the paired daily rows are stationary within the window, and that "
        "concentration contradicts the assumption. The intervals also say nothing about how the increment would "
        "behave in another regime.\n"
        "5. The portfolio's three core_ER_6 sleeves are the committed series from other pipelines and were not "
        "re-simulated with the D-4 fixes (limitation stated in `backtests/results/v2_d4/README.md`). The `both` "
        "portfolio differs from `original` only in its v2 sleeve.\n"
        "6. Everything here is post-result and exploratory. Several configurations are reported. The primary one "
        "(block 20, net 1x, OOS) was fixed in the SPEC, and the others are sensitivities. None of them can change "
        "the registered verdict.\n")

    out.append("## Files\n")
    out.append(md_table(["file", "content"], [
        ["`SPEC.md`", "the specification, fixed before computing (hash-checked by the script)"],
        ["`attribution.py`", "the computation (reads committed derived series only; writes only this folder)"],
        ["`factor_attribution.csv`", f"{len(fa)} rows: dependent variant x factor set x window x model (M0..M4)"],
        ["`correlations.csv`", f"{len(corr)} rows: the two 7 x 7 correlation matrices, long format"],
        ["`bootstrap.csv`", f"{len(bs)} rows: window x variant x basis x block length, with the NW t contrasts"],
        ["`ATTRIBUTION.md`", "this file"],
    ]) + "\n")
    out.append("Reproduce from the repository root: `python results_2/attribution/attribution.py`. It needs only the "
               "three committed input files above, and runs in well under a minute.\n")
    return "\n".join(out)


if __name__ == "__main__":
    main()
