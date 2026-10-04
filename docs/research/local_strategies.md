# Local trading and quant-research artifacts on this PC

Survey date: 2026-10-03 (Sat, about 06:30 ET). Prepared for Gator Quant Hacks 2026, Systematic Trading track.
Companion report on the GitHub repos: `research/github_repos.md`.

## 0. Bottom line

- **There is very little trading code on this PC.** The quant work that has a real backtest stack
  (`physics-quant-research`, `algogator-tail-risk`, `algogator-apply`, `cb-policy-tracker`, `mev-simulator`)
  exists only on GitHub (minh-stakc). None of it is cloned anywhere on C: or D:. See `github_repos.md`.
- There are three local quant projects, all under `<automation>\projects\`:
  - **Factor Forensics.** Multiple-testing haircut on 15 Ken French factor proxies. The most reusable local code.
  - **Surface Audit.** Static no-arbitrage checks on SPY options, with a robust Black-Scholes and implied-vol solver.
  - **lobster-sim.** Order-book rebuild, queue-position cost and OFI code. Synthetic data only. It is an AI
    reconstruction, not the user's original project (see 1.3).
- There is also a $100 Alpaca paper-trading **scaffold**: config and state files only, with no engine and no backtest.
  There is one detailed **design doc**, the Kraken research system, which holds a strong cost and validation checklist.
- **No durable cached price data exists anywhere** on D: or in `<home>`:
  - no parquet, feather, h5 or Databento `.dbn` files;
  - no OHLC CSVs.
  The only market data on disk falls into three groups:
  - the Ken French monthly decile files in Factor Forensics;
  - one saved SPY option-chain snapshot (2026-08-26);
  - files that sibling agents downloaded today into this session's temp scratchpad (FRED, CBOE, KF daily). Those
    should be copied into `gqh-systematic/data/cache/` if they will be used (see section 3).
- **No Databento, Massive/Polygon, Alpaca, Webull or FRED keys exist** in any env file or in the user or process
  environment. A Gemini key exists (for the MLH Gemini prize). See section 4.

## 1. Search method and coverage

- Content search used ripgrep with `--no-ignore --hidden`, over `*.py, *.ipynb, *.R, *.md, *.cpp, *.js, *.ts`.
  Patterns: `backtest, sharpe, max drawdown, yfinance, ccxt, databento, vectorbt, backtrader, zipline,
  cointegrat, kalman, risk parity, ohlcv, mean reversion, pairs trading, quantconnect, alpaca, polygon.io`.
  A second pass looked for `hmmlearn, GaussianHMM, qaoa, IMC Prosperity datamodel/TradingState, arch_model,
  statsmodels.tsa, pykalman, implied_vol`.
- Locations searched:
  - all of D: (`AUTOMATION`, `LOCAL`, `OUTBOUND`, `james`, `james-browser-bench`);
  - `<home>`: Desktop, Documents, Downloads, OneDrive, `.<assistant>`, `.codex`, `.config`, `.ipython`, `.jupyter`;
  - `C:\Projects`.
- Excluded: `node_modules`, venvs, `site-packages`, `.git`, Playwright and auth profiles, and generated resume output.
  The machine has only two drives, C: and D:.
- Filename search covered: `*backtest*`, `*quant*`, `*physics-quant*`, `*algogator*`, `*prosperity*`, `*kalman*`,
  `*.parquet`, `*.feather`, `*.h5`, `*.dbn*`, and CSVs with an OHLC header.
- The D: content search returned 78 files. All were triaged. About 70 are false positives: resume, outreach or
  application text that mentions "Sharpe" or "backtest", "sharper" in prose, a careers address at alpaca.markets,
  or "deflated" in zlib code. The real artifacts are listed below.

## 2. Artifacts

### 2.1 Factor Forensics: `<automation>\projects\factor-forensics\`

| | |
|---|---|
| Idea | Asks how many of 15 published equity-factor proxies survive multiple-testing corrections. The proxies are long-short decile spreads (top minus bottom, or the reverse) from Ken French univariate sorts. The sign of each comes from its source paper, which is recorded in `src/zoo.py`. |
| Data | Ken French Data Library, monthly value-weighted decile returns. Cached raw CSVs are in `data/` (15 files). The panel is `results/factor_returns.csv`: 756 months (1963-07 to 2026-06) by 15 factors, in % per month. |
| Results (verified frozen 2026-09-05, `VERIFICATION_2026-09-05.md`) | 5 of 15 pass t>1.96. Survivors under each correction: Bonferroni 2, Holm 2, Benjamini-Yekutieli 1 (momentum only), row-bootstrap max-\|t\| 2. The bootstrap hurdle is \|t\| = 2.844. The effective number of independent tests is M_eff = 5.27, against M = 15. Momentum (12-2): 14.6 %/yr, t = 4.59. Net share issuance: t = 3.03. Size: t = 1.07. Raw low-minus-high beta: mean is negative. |
| Code | `src/data.py` is the KF downloader and parser, with a byte-safe cache. `src/zoo.py` builds the 15 signed spreads. `src/haircut.py` implements t-stats, Bonferroni, Holm, BY, the row bootstrap max-\|t\| hurdle and the eigenvalue M_eff. `run.py` is the CLI. Requires numpy, pandas and scipy. |
| Red flags | (a) Decile spreads are not the published factor constructions; HML here is a raw B/M decile spread. (b) The t-tests have no Newey-West correction, and the IID row bootstrap ignores serial dependence. (c) This is retrospective significance, not a tradable strategy: there are no costs and no out-of-sample split. (d) The README says the bootstrap "independently reproduces" Harvey-Liu-Zhu; the 09-05 verification note correctly walks that back to a numerical comparison. |
| Reuse for GQH | **High.** (1) `haircut.py` gives the "number of variants tried" machinery directly: Holm/BY across all strategy variants, plus an empirical max-statistic hurdle across correlated variants. That pairs naturally with a Deflated Sharpe Ratio (DSR) computed from the variant count. Switch the IID row bootstrap to a stationary or block bootstrap for daily data. (2) `data.py` is a working KF loader that will fetch `F-F_Research_Data_Factors`, `F-F_Research_Data_5_Factors_2x3` and `F-F_Momentum_Factor` for the required factor regression. **Caveat:** its parser keys on 6-digit `YYYYMM` dates (`_MONTHLY = r"^\s*(\d{6})\s*,"`), so the `*_daily` files (8-digit dates) need a one-line regex change. (3) `BUILDLOG.md` documents two traps worth citing as robustness hygiene: the Windows `\r\r\n` cache-corruption bug (read and write caches as bytes) and long-leg sign conventions. |

### 2.2 Surface Audit: `<automation>\projects\surface-audit\`

| | |
|---|---|
| Idea | Model-free static no-arbitrage checks (put-call parity, vertical, butterfly, calendar) on live SPY option chains. The central question is whether a violation survives paying the bid-ask spread. The forward and discount factor are implied per expiry by weighted least squares of (C-P) on K, instead of being assumed. |
| Data | Live yfinance option chains (no key needed). The saved snapshot is `results/SPY_surface.csv` from 2026-08-26 (evening run): 1,383 cleaned quotes from 2,012 raw, 7 expiries from 2026-08-27 to 2026-09-04, spot 766.08. It includes the solver's own `iv`, `delta` and `vega`. There are also per-check violation CSVs and `summary.json`. |
| Results | Morning run: 242 violations at mid, of which 27 survive execution (88.8% are artifacts of quoting at mid). Evening run, the one saved: 896 at mid, 169 survive (81.1%). The implied forward removed a one-sided bias that had manufactured about 110 fake parity violations. IV solver round-trip: 246 of 350 cases converge to 4.3e-07 in 5.8 Newton iterations on average. The remaining 104 return NaN by design because vega falls below a floor. |
| Code | `src/bs.py`: `price`, `vega`, `greeks`, no-arbitrage `bounds`, and `implied_vol(target, S, K, T, r, q, kind)`, a damped Newton with bisection fallback that returns NaN when IV is unidentifiable. `src/chains.py`: yfinance chain fetch plus quote cleaning (two-sided markets only, relative spread at most 50% of mid, own IV). `src/arb.py`: `implied_forward`, `parity`, `vertical`, `butterfly`, `calendar`. |
| Red flags | SPY options are American, so parity is an inequality and the counts are upper bounds. Quotes are not simultaneous. The README numbers (morning run) differ from the saved `results/` (evening run); `BUILDLOG.md` acknowledges this. It is not a strategy and has no P&L. |
| Reuse for GQH | **Medium-high for the Massive "Trade the 8-K" options bonus.** The IV solver, Greeks and quote-cleaning filters are what is needed to price straddles or variance exposure around 8-K events from Massive option bars, and to compute event IV crush. `implied_forward` gives a dividend- and rate-free forward per expiry. Not needed for a pure equities or futures entry. |

### 2.3 lobster-sim: `<automation>\projects\lobster-sim\` (Downloads also has `lobster-sim.zip`)

| | |
|---|---|
| Idea | Rebuilds Nasdaq limit order books order by order from LOBSTER message files. Measures (1) the cost of resting passively at the back of the queue against crossing the spread, bucketed by volume ahead, and (2) Cont-Kukanov-Stoikov order-flow-imbalance (OFI) price-impact regressions with a depth fit (published CKS values: R² 0.65, λ 0.98, c 0.45). |
| Data | **Synthetic only**: 3 ticker-days, 180k messages, in `results/synthetic_smoke/`. It has never been run on real LOBSTER data. |
| Results | Rebuild matches 99.994% of snapshot rows before correction, on synthetic data. Queue-cost numbers such as passive drag of -6.7 bps are synthetic artifacts with no market meaning. The codex memory reports 14 tests passing. |
| Red flags | **Integrity.** `<home>\Downloads\CITADEL_HANDOFF_20260924.md` and the codex memory both record that this is a 2026-09-24 AI reconstruction of a lost original project, made "to refresh memory". It is pure Python, while the resume says C++. It must not be presented as original work or as evidence for resume metrics. If any of it is used, label it as a reconstruction. |
| Reuse for GQH | **Low-medium.** It is only relevant for a Databento angle (Best Use of Databento): Databento MBO or MBP-10 data could feed the OFI code through an adapter that writes the LOBSTER message/orderbook layout, as `lobster_io.py` documents. That would support an empirical impact or capacity estimate to set beside the square-root model. Not on the critical path for a daily-frequency strategy. |

### 2.4 Alpaca paper-trading scaffold: `<automation>\trader\`

| | |
|---|---|
| Idea | `momentum_trend_weekly`: hold the top 3 of `[SPY, QQQ, AAPL, MSFT, NVDA, GOOGL, AMZN, META]` by 63-day momentum, only while above their 200-day MA, rebalanced weekly on Monday at 09:35 ET, equal weight, $100 paper. |
| Data / results | None. Only `README.md`, `config.json` and `state.json` exist; `engine.py` and `digest.py` were never written, and no Alpaca keys exist. |
| Red flags | The universe is chosen with hindsight (2026 mega-cap winners), which is survivorship and look-ahead in universe selection. There was never a backtest. |
| Reuse for GQH | **Low.** The risk-guard parameter set is a reasonable template for the Risk Management Plan's hard limits: 6% per-position stop, 4% daily loss auto-halt, 95% maximum exposure, 3 maximum positions, a kill switch in a state file. The strategy itself should not be reused. |

### 2.5 Kraken research system design: `<automation>\docs\kraken-research-system-design.md` (212 lines, 2026-09-06)

| | |
|---|---|
| Idea | Advisory and paper-trading architecture for Kraken instruments: a deterministic engine, an AI analyst that may only interpret or abstain, calibrated probabilities, and an explicit fee and slippage ledger. Design only; nothing was implemented. |
| Reuse for GQH | **High as a text and methodology source** for the Risk Management and Liquidity sections: (a) a **self-financing ledger** that computes rebalancing trades from *drifted* holdings rather than from target-weight deltas; (b) a **no-double-counting** rule, where fill prices that already sweep the book get no extra flat slippage haircut; (c) acceptance tests, e.g. a flat-price round trip must lose exactly the costs, and partial fills accrue only their own fees; (d) a validation protocol (section 6): chronological windows, purge plus embargo at split boundaries, preserve every trial, freeze acceptance criteria before touching the test set, cite Bailey et al. on the Probability of Backtest Overfitting; (e) a clean split between facts, model estimates and interpretation. Maps directly onto the GQH rules: OOS once, 2x costs, variants reported. |

### 2.6 Codex session memories: `<home>\.codex\memories\`

- `rollout_summaries\2026-09-06T23-47-48-QWo5-kraken_quant_research_system_design_and_cost_model.md` contains an
  inventory of the GitHub quant repos with audit findings:
  - `physics-quant-research` is the strongest baseline, with `GhostDim` features `swept_area_z`, `arc_length_z`,
    `regime_z` and `regime_ok`. `regime_ok` is a smooth gate, not a probability.
  - The crypto runner annualizes with 252 days, which is wrong for 24/7 crypto.
  - `algogator-tail-risk` fits its HMM and GARCH on the full sample, which is leakage.
  - `algogator-apply` and `mev-simulator` have look-ahead, same-sample parameter selection and missing costs.
- `rollout_summaries\2026-09-14T02-18-28-*alpaca_paper_trading_scaffold.md` explains why `<automation>\trader`
  stops at a scaffold.
- `MEMORY.md` lines 551-591 hold the lobster-sim provenance: synthetic-only, local commit `c82733b`, push to GitHub
  unverified.

### 2.7 Independent audit of the quant repos: `<automation>\outputs\verified_facts.md`

A byte-identical copy is at `SIG_reconsideration_session_2026-08-30\outputs\SIG_PC_transfer_2026-08-30\evidence\verified_facts_audit_2026-08-26.md`.

This is the most useful local record of what the GitHub quant code actually shows. Use it to avoid re-claiming
weak numbers in the quant note.

**physics-quant-research**
- The strategy is flat 1/N with portfolio vol targeting. It is not risk parity, despite the label.
- A permutation test of the gate's timing (3,000 reshuffles) gives **p = 0.3823**, a null result.
- Ablation: **Sharpe 1.009 ungated vs 1.059 gated.**
- Walk-forward OOS Sharpe is **0.759 vs 0.699** for buy-and-hold.
- The ensemble ceiling was predicted at about 1.61 and measured at 1.16. The 3x-ETF sleeve is 0.866 correlated with
  the mixed sleeve.
- It has block-bootstrap Sharpe CIs, Bailey-López de Prado DSR and a 14-fold walk-forward.
- The repo is a single commit with no tests, and its IBKR loader is unused.

**algogator-tail-risk**
- An honest negative result. Over SPY plus 9 sector SPDRs, 2005-2024 with 2018-2024 OOS, GARCH(1,1) beat regime
  CVaR: MAE 0.0205 vs 0.0282, Diebold-Mariano 5.71.
- The regime model was worst in the COVID 2020 shock (28.85% violations) and best in the 2022 hiking cycle.
- All models failed Kupiec and Christoffersen. GARCH was also fit on the full sample.

**Resume quant projects with no code anywhere** (confirmed by this search: no repo and nothing on C: or D:)
- HMM Volatility Regime Detector
- Kalman Filter Pairs Cointegration Engine
- Newton-Raphson IV Pricing Engine. The nearest real code is `surface-audit/src/bs.py`.
- Cross-Sectional Momentum Factor Pipeline
- QAOA Quantum Portfolio Strategy
- Options Greeks Pricing Engine
- Poker EV Decision Simulator
- IMC Prosperity code

Do not cite any of these as prior work in the competition note.

### 2.8 Idea documents (no code)

- `<automation>\outputs\impressive_buildable_projects.md`:
  - **P4 "Mirage-check"**: LOB alpha with purged and embargoed k-fold CV, Deflated Sharpe and a cost-aware
    backtest. This is the right validation template.
  - **P5**: Factor Forensics, now built.
- `<automation>\outputs\impressive_buildable_projects_apex.md`: an LOB simulator idea, stylized-fact tests
  against LOBSTER.

### 2.9 Downloads: `CITADEL_HANDOFF_20260924.md` and `CITADEL_HANDOFF_20260924_1.md`

The two files are identical, 12,564 bytes each. They are Citadel SWE interview preparation, not quant research.
Their only relevant content is the lobster-sim integrity note (2.3) and a list of resume items (CPZ Lab "backtest
orchestration", Algogator, IMC Prosperity top-100). Nothing reusable for a strategy.

### 2.10 Checked and not trading-related

- `D:\LOCAL\references\resume-projects-20260928\cuesearch`: C++ billiards physics engine.
- `D:\LOCAL\references\resume-projects-20260928\miniml`: OCaml language.
- `<automation>\islands\`: stats-course mini-projects.
- `<automation>\outputs\research\strategy-g-*.md`: federated LLM safety, not trading.
- `Downloads\HW1_KMeans.ipynb` and `hw2_problem*.py`: ML homework on random matrices.
- `D:\james*`: AI-employee product; prose matches only.
- `<automation>\SIG_reconsideration_session_2026-08-30\`: outreach campaign only.
- OneDrive `Coding stuff`: hello-world C and Python.

## 3. Market data on disk that can be reused

| Location | Content | Range | Format | Durable? |
|---|---|---|---|---|
| `<automation>\projects\factor-forensics\data\*.csv` | 15 KF monthly decile-sort files: ME, BE-ME, OP, INV, E-P, CF-P, D-P, AC, BETA, NI, VAR, RESVAR, Prior_12_2, Prior_1_0, Prior_60_13 | 1926 to 1963 start (varies) through 2026-06 | Raw KF CSV, multi-table, CRLF. Parse with `src/data.py`. | Yes |
| `...\factor-forensics\results\factor_returns.csv` | 15 signed long-short spreads | 1963-07 to 2026-06, 756 rows | Tidy CSV, % per month | Yes |
| `<automation>\projects\surface-audit\results\SPY_surface.csv` | SPY option snapshot: bid, ask, mid, own IV, delta, vega | One snapshot 2026-08-26; expiries 2026-08-27 to 09-04 | CSV | Yes, but a single snapshot is not useful for a backtest |
| `...\lobster-sim\results\synthetic_smoke\synthetic_data\` | Synthetic LOBSTER files | n/a | LOBSTER CSV | Synthetic, do not use |
| `<scratch>\data_tests\` (downloaded today by sibling agents) | **CBOE**: VIX (1990-01-02 to 2026-10-02, OHLC), VIX9D, VIX1D, VIX3M, VIX6M, VVIX, VXN, VXTLT, GVZ, OVX, SKEW, PUT and BXM indexes, plus VX futures contracts for 2025-11 and 2026-10. **FRED**: DGS10 (1962 to 2026-10-01), DGS2, DTB3, DFF, SOFR, T10Y2Y, T10YIE, BAMLH0A0HYM2, BAMLC0A0CM, NFCI, STLFSI4, WALCL, RRPONTSYD, ICSA, UNRATE, DTWEXBGS, VIXCLS. **Ken French daily**: FF3, FF5 2x3, Momentum, ST-Reversal, 49 Industry portfolios (1926 to 2026-08-31). `yf_daily_summary.csv` holds coverage stats only; no yfinance prices were saved. It covers 33 ETFs (SPY from 1993, sector SPDRs from 1998, TLT/IEF/LQD from 2002, HYG from 2007, and so on) and the futures continuations ES, NQ, YM, RTY, ZN and ZB. | as noted | CBOE/FRED CSV; KF raw CSV with no extension | **No.** Temp scratchpad, lost when the session is cleaned. Copy to `gqh-systematic/data/cache/` (gitignored) or re-download through `data/download.py`. |

There are no Databento, Massive/Polygon or Alpaca downloads anywhere on the machine.

## 4. Keys and credentials (names and locations only; values not read into this report)

| File | Relevant variables present |
|---|---|
| `<automation>\.env` | `GITHUB_TOKEN`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` |
| `<home>\Downloads\env` | `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `ANTHROPIC_ADMIN_KEY`, `OPENAI_API_KEY`, `OPENAI_ADMIN_KEY` |
| `D:\james\.env` | Same set as `Downloads\env`, including `GEMINI_API_KEY` |
| User and process environment | No DATABENTO, POLYGON, MASSIVE, ALPACA, FRED, WEBULL, KRAKEN, TIGER or SNOWFLAKE variables |

- `gqh-systematic/.gitignore` already ignores `.env`, `data/cache/` and `.massive_cache/`.
- A Databento key must come from the Discord, as the brief says, and go into `gqh-systematic/.env`.
- FRED CSV download (`fredgraph.csv`) and Ken French need no key.
- Separately, `github_repos.md` notes a hardcoded Copernicus CDS key in the public git history of `algogator-apply`.
  Rotate it.

## 5. Red flags to avoid repeating, in competition-rule terms

1. **Hindsight universes.** The `trader/` mega-cap list. Use a rules-based ETF or futures universe chosen ex ante.
2. **Full-sample fits** (algogator-tail-risk GARCH/HMM). Every model must be fit on past data only, walk-forward,
   with signals lagged.
3. **Calendar errors.** 252-day annualization for 24/7 crypto in physics-quant-research. Use 365 for crypto.
4. **Mislabeling.** "Risk parity" that is really 1/N. Describe the weighting exactly.
5. **Live-feed numbers quoted as fixed.** Surface Audit counts changed between runs. Freeze data snapshots with
   hashes so the code reproduces the note's numbers; otherwise Performance is capped at 4.
6. **Gates that add nothing.** The GhostDim gate's p = 0.38. Report ablations and permutation tests honestly;
   judges reward that.
7. **Selection bias.** CueSearch shows the right habit: a sweep winner re-run on fresh seeds fell from 4.0% to 1.7%.
   Count every variant for DSR.

## 6. Top 5 most reusable pieces, ranked

1. **`<automation>\projects\factor-forensics\src\haircut.py` + `src\data.py`.** Multiple-testing and max-statistic
   bootstrap code, plus a working Ken French loader and cache. Directly supports two rules: "report number of
   variants tried (Deflated Sharpe)" and "factor regression vs market/value/momentum". Changes needed: an 8-digit
   date regex for daily files; a block or stationary bootstrap instead of the IID row bootstrap; the DSR formula
   added.
2. **`<automation>\docs\kraken-research-system-design.md` (sections 6, 8, 9).** A ready-made, rule-aligned cost and
   validation spec: self-financing ledger with drift-based rebalancing, no double-counted slippage, cost acceptance
   tests, purge and embargo, frozen criteria before a single OOS evaluation. Adapt the text and checks for the Risk
   Management Plan and Liquidity sections of the quant note.
3. **`physics-quant-research` (GitHub only; clone it).** The only real backtester and metrics stack the user owns:
   walk-forward, block-bootstrap Sharpe CIs, DSR, and a permutation test of signal timing. Its honest numbers are
   in `outputs\verified_facts.md`. It is the natural base engine, or at least the source of the metrics module.
   Details in `github_repos.md`.
4. **`<automation>\projects\surface-audit\src\bs.py` + `chains.py` + `arb.py`.** A robust IV solver that returns
   NaN below a vega floor, Greeks, no-arbitrage bounds, an implied forward and quote-cleaning filters. Needed only
   if the team also enters the Massive "Trade the 8-K" options bonus, e.g. event straddles and IV crush.
5. **Today's scratchpad data pull** (`...\scratchpad\data_tests\`). CBOE VIX term-structure indexes and VX
   futures, FRED rates, credit and stress series, and Ken French daily factors, all current to 2026-10-01/02 (KF to
   2026-08-31). This is the input set for a macro, vol-regime or factor-regression study. Persist it into
   `gqh-systematic/data/cache/` now, because the temp folder is not durable.
   - Honorable mention, `<automation>\projects\lobster-sim\src\ofi.py` + `queue_sim.py`: a Databento MBO/MBP
     impact or capacity angle. It is synthetic-only and an AI reconstruction, so it must be labeled as such if
     used at all.
