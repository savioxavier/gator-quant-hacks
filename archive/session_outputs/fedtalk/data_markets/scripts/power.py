"""Power / minimum-detectable-effect calculations for presser-level and answer-level tests, plus cost-to-volatility
ratios from the free USMPD press-conference windows."""
import numpy as np, pandas as pd
from scipy import stats
z = stats.norm.ppf
def mde_r(n, alpha=0.05, power=0.8, two_sided=True):
    za = z(1 - alpha / 2) if two_sided else z(1 - alpha)
    return np.tanh((za + z(power)) / np.sqrt(n - 3))
print("== Minimum detectable correlation (Fisher z), 80% power")
for label, n in [("all scheduled pressers 2011-2026", 93), ("every-meeting era 2019-2026", 61), ("Powell only", 64),
                 ("Warsh so far", 3), ("by end-2027 (93+10)", 103)]:
    print(f"  {label:34s} n={n:4d}  alpha=.05: r={mde_r(n):.3f}   alpha=.01: r={mde_r(n, 0.01):.3f}   alpha=.001 (t~3.3): r={mde_r(n, 0.001):.3f}" if n > 3 else f"  {label}: n={n} (no inference possible)")
print("== Answer-level with clustering by meeting: n=2226 answers in 93-95 pressers (m~23.4 per presser)")
m = 2226 / 95
for icc in [0.0, 0.02, 0.05, 0.1, 0.2, 0.4]:
    deff = 1 + (m - 1) * icc; neff = 2226 / deff
    print(f"  ICC={icc:4.2f} design effect={deff:5.2f} n_eff={neff:7.0f} MDE r(.05)={mde_r(neff):.3f} MDE r(.001)={mde_r(neff, 0.001):.3f}")
print("== Per-event Sharpe needed for t-stat thresholds (t = SR_event * sqrt(N))")
for N in [61, 93, 103]:
    for t in [2.0, 3.0]:
        sr = t / np.sqrt(N); print(f"  N={N:3d} t={t}: SR/event={sr:.3f}  annualised at 8 events/yr={sr*np.sqrt(8):.2f}")
print("== Years of live out-of-sample needed to confirm a given per-event Sharpe at t=2 (8 pressers/yr)")
for sr in [0.1, 0.2, 0.3, 0.5]:
    N = (2.0 / sr) ** 2; print(f"  SR/event={sr}: N={N:5.0f} events = {N/8:5.1f} years")
print("== Same for answer-level trades, ~22 answers/presser, assuming design effect 3 (ICC~0.1)")
for sr in [0.02, 0.05, 0.1]:
    N = (2.0 / sr) ** 2 * 3; print(f"  SR/trade={sr}: trades={N:7.0f} = {N/22:6.0f} pressers = {N/22/8:5.1f} years")

# cost vs volatility using USMPD presser-window moves (2019-2026) and contract specs
pc = pd.read_excel("usmpd/USMPD.xlsx", sheet_name="Press Conferences")
pc = pc[(pc["Date"] >= "2019-01-01") & ~pc["Date"].astype(str).str.startswith(("2020-03-03", "2020-03-15"))]
# approximate contract dollar value per unit move (assumptions; DV01s are approximate and vary with yield/CTD)
spec = {
    "ES (SPFUT %)": dict(col="SPFUT", per_unit=lambda: 0.01 * 7776.5 * 50, tick=12.50, fee=2*2.5),   # $ per 1% at ES 7776.5 on 2026-10-02 (cached daily), 1 tick spread, ~$2.5/side
    "ZN (UST10Y pp)": dict(col="UST10Y", per_unit=lambda: 100 * 70.0, tick=15.625, fee=2*2.0),    # DV01 ~ $70/bp (approx.)
    "ZF (UST5Y pp)": dict(col="UST5Y", per_unit=lambda: 100 * 45.0, tick=7.8125, fee=2*2.0),      # DV01 ~ $45/bp (approx.)
    "ZT (UST2Y pp)": dict(col="UST2Y", per_unit=lambda: 100 * 39.0, tick=7.8125, fee=2*2.0),      # DV01 ~ $39/bp (approx.)
    "SR3 (ED4 pp, 4th qtr strip)": dict(col="ED4", per_unit=lambda: 100 * 25.0, tick=12.50, fee=2*2.0),  # $25/bp exact; tick 0.005
    "6E (EURUSD %)": dict(col="EURUSD", per_unit=lambda: 0.01 * 1.129 * 125000, tick=6.25, fee=2*2.0),
}
print("== Cost of one round trip (1 tick spread + fees) vs volatility, 2019-2026 scheduled pressers")
for k, s in spec.items():
    x = pc[s["col"]].dropna(); sd = x.std() * s["per_unit"](); rt = s["tick"] + s["fee"]
    seg = sd / np.sqrt(35)   # ~2-minute answer if variance were spread evenly over 70 minutes
    print(f"  {k:28s} n={len(x):3d} presser-window sd=${sd:7.0f}/contract  per-2-min sd~${seg:6.0f}  round trip=${rt:5.1f}  cost/sd presser={rt/sd:5.1%}  cost/sd 2-min={rt/seg:5.1%}  min |IC| for sign trade at 2-min={rt/(seg*np.sqrt(2/np.pi)):.3f}")
