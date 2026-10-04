# Data feasibility and environment (GQH 2026, Systematic Trading)

Tested Sat 2026-10-03, about 05:50 to 06:40 ET. Every claim below comes from an actual pull made in this session unless it is marked *(docs)* or *(unverified)*. Small test outputs are in
`<scratch>/data_tests/`.

## TL;DR

* We can get **everything needed for a daily cross-asset strategy, 2006/2007 to 2026-10-02, with no keys**: yfinance (ETFs, indices, vol indices, FX, crypto, unadjusted front-month futures), FRED (rates, spreads, macro), Ken French (FF5 + MOM daily, up to **2026-08-31** only), Cboe CDN (VIX-family indices plus **per-contract VX futures settles back to 2004**), CFTC COT, AQR factor library, SEC EDGAR submissions JSON (8-K item codes).
* **Stooq is dead for automation.** It now serves a JavaScript bot-check page instead of the CSV, and pandas-datareader 0.11.1 removed the `stooq` reader. Do not try to get around the check. Our backup and cross-check is Ken French Mkt vs SPY (daily correlation 0.991), plus FRED/Cboe for indices.
* **No Databento key on this machine** (checked env vars and `.env*` files under `<automation>`). Databento's own `ohlcv-1d` continuous futures (GLBX.MDP3, from June 2010) would cost pennies against the $125 signup credit or a sponsor key. They are worth adding for the "Best Use of Databento" prize and for clean futures rolls, but we do not depend on them.
* **OOS window: 2024-10-03 to 2026-10-02 (501 NYSE trading days)**. The 2-year cap binds for any history longer than about 10 years. In-sample is 2007-07-02 to 2024-10-02 for the cross-asset ETF universe.
* **Environment caveat:** `D:` is a **FAT32 USB stick** that is very slow to write: 20 x 4 KB files took 13 s, and one 20 MB file took 153 s (about 130 KB/s). A venv cannot live there, so the real venv is on `C:` and `D:/…/.venv` is a shim to it (details below). **Keep data caches off D:** (or keep them tiny).

## 1. Python environment

| Item | Value |
|---|---|
| Real venv | `<home>/.venvs/gqh-systematic` (Python 3.12.10, system install `<python>`). This follows the user's existing `<home>\.venvs\*` convention. |
| Project path shim | `<solo-repo>/.venv` is a real venv whose `Lib/site-packages/zz_gqh_cvenv.pth` runs `site.addsitedir(r"<home>\.venvs\gqh-systematic\Lib\site-packages")`. Result: `<solo-repo>/.venv/Scripts/python.exe` imports every package from the C: venv (verified: pandas, numpy, scipy.linalg, statsmodels, yfinance, databento, sklearn, arch, reportlab, matplotlib). |
| Installing more packages | Use `<home>/.venvs/gqh-systematic/Scripts/python.exe -m pip install …`. The pip inside the D: shim works, but it writes to D:, which is extremely slow. A first attempt to install everything into D: ran 30 minutes and finished only the pip self-upgrade. |
| Pins | `<solo-repo>/requirements.txt` (full `pip freeze`, 68 packages). Key versions: pandas 3.0.6, numpy 2.5.3, scipy 1.18.1, statsmodels 0.15.0, scikit-learn 1.9.1, matplotlib 3.11.2, yfinance 1.7.0, pandas-datareader 0.11.1, pyarrow 25.0.1, databento 0.87.0 (dbn 0.70.0), arch 8.0.0, reportlab 5.0.1, numba 0.68.0, seaborn 0.13.2, openpyxl 3.1.5, requests 2.34.2. |
| Windows Application Control | The **first** import of scipy (`_linalg_pythran` DLL) failed with "An Application Control policy has blocked this file". Every import after that succeeded (individually and together, several runs). This looks like a one-time reputation check on new DLLs. If it recurs, retry once. No security setting was touched. |
| Git | `git status` in the repo fails with "dubious ownership" (FAT32 does not record owners). Use `git -c safe.directory=<solo-repo> <cmd>` per command. Global git config was not changed. Nothing was committed. |

## 2. Source-by-source results

### 2.1 yfinance 1.7.0: primary price source

Pulled `period="max"`, daily, in 5 batches (about 80 tickers). Each batch took 0.3 to 2.8 s. **No rate limiting was seen.** Cache to parquet anyway, on C:, so backtests never re-hit Yahoo.

**Adjustment.** `auto_adjust=True` Close equals `Adj Close` to within 1e-6 relative (SPY). Both are split and dividend adjusted: SPY total return over 2005 to now was 9.50x, against 6.40x for price only. With `auto_adjust=False`, the `Close` column is **already split-adjusted but not dividend-adjusted**. Example: USO's 1:8 reverse split on 2020-04-29 shows no jump in Close. **Use total-return (adjusted) prices for P&L.** GLD, SLV and USO pay no distributions, so for them adjusted equals raw.

**First dates (all series run to 2026-10-02):**

| Group | Tickers (first date) |
|---|---|
| US equity / sector ETFs | SPY 1993-01-29, QQQ 1999-03-10, IWM 2000-05-26, XLK/XLF/XLE/XLV/XLY/XLP/XLI/XLB/XLU 1998-12-22, XLRE 2015-10-08, XLC 2018-06-19, VNQ 2004-09-29 |
| Intl equity | EFA 2001-08-27, EEM 2003-04-14, VWO 2005-03-10, VEA 2007-07-26 |
| Bonds | TLT/IEF/SHY/LQD 2002-07-30, AGG 2003-09-29, TIP 2003-12-05, HYG 2007-04-11, BIL 2007-05-30, EMB 2007-12-19 |
| Real assets / FX ETF | GLD 2004-11-18, SLV 2006-04-28, USO 2006-04-10, DBC 2006-02-06, GSG 2006-07-21, UUP 2007-03-01, PDBC 2014-11-07 |
| Factor-proxy ETFs | IWD/IWF 2000-05-26, IWN/IWO 2000-07-28, VTV/VUG 2004-01-30, MTUM/VLUE/SIZE 2013-04-18, QUAL 2013-07-18, USMV 2011-10-20, SPLV/SPHB 2011-05-05, SPMO 2015-10-12 |
| Managed-futures benchmarks | DBMF 2019-05-08, KMLM 2020-12-02, CTA 2022-03-08 |
| Indices | ^GSPC 1927, ^NDX 1985, ^RUT 1987, ^TNX 1962, ^IRX 1960 (has 7 zero values), ^MOVE 2002-11-12 (only free MOVE source; Cboe's MOVE CSV returns 403) |
| Vol indices | ^VIX 1990-01-02, ^SKEW 1990, ^VIX3M 2006-07-17 (Yahoo includes back-calculated data; Cboe's own CSV starts 2009-09-18), ^VVIX 2007-01-03, ^VIX6M 2008-01-02, ^VIX9D 2011-01-03 |
| Continuous futures (`=F`) | ES/NQ 2000-09-18, YM 2002-04-05, RTY 2017-07-10, ZN/ZB/ZF ~2000-09-21, ZT 2000-06-02, CL 2000-08-23, NG/GC/SI/HG 2000-08-30, ZC/ZW 2000-07-17, ZS 2000-09-15, 6E 2000-09-12, 6J/6B/6A/6C/6S 2000. **`DX=F` and `VX=F` do not exist on Yahoo** (404). |
| FX | JPY=X 1996-10-30, EURUSD/GBPUSD/NZDUSD 2003-12-01, USDCAD/USDCHF 2003-09-17, AUDUSD 2006-05-16 |
| Crypto | BTC-USD 2014-09-17, ETH-USD 2017-11-09, SOL-USD 2020-04-10 (7-day calendar) |

**Data-quality findings:**
* ETFs are clean. Missing business days match holidays only, and the max gap is 4 to 7 days (holiday weekends). There are repeated-close days, i.e. stale prints: UUP 219, ZN=F 113, DBC 85, HYG 74 since 2005. Treat these as low-liquidity flags.
* **Yahoo `=F` futures are unadjusted front-month splices.** Roll days produce fake returns. ES=F minus SPY daily return reached +2.75% on 2024-12-23 (roll) and ±2.2% on 2020-06-19 and 06-22. Closes are also not synchronous with ETF closes (±6% on 2020-03-20 and 03-23). **Bad prints:** CL=F at -37.63 on 2020-04-20 (real, but it breaks log returns); 6J=F jumps +904% on 2001-12-18 after a 0.0008 print. Gaps of up to 27 days (6B), 14 days (6J, 6S, ZC) and 12 days (ZN). **Do not use `=F` returns for P&L without rolling the contracts yourself.** Use ETFs, Databento continuous contracts with our own back-adjustment, or Cboe per-contract VX.
* FX `=X` data has gaps of up to 18 days, and some series carry a 2026-10-03 (Saturday) bar because of timezone stamping. It is usable for signals; prefer futures or ETFs for P&L.
* `^VIX` and other indices report Volume = 0. They are not tradable; trade VX futures, or SPY/TLT as instruments.

**Intraday limits (SPY):** `1m` is available only for the last 30 days, at most about 8 days per request. A request for 2026-08-01 fails with "must be within the last 30 days". `2m/5m/15m/30m/90m` cover the last 60 days. `60m/1h` cover the last 730 days (`period="730d"` returned 2023-11-03 onward). **No usable long intraday history, so daily frequency is the right choice.**

### 2.2 FRED: direct CSV works, pandas-datareader works

`https://fred.stlouisfed.org/graph/fredgraph.csv?id=<ID>` takes about 0.5 s and needs no key. Columns are `observation_date,<ID>`, and missing days show as empty or "." values. `pandas_datareader.data.DataReader([...], "fred")` also works.

| Series | First obs | Last obs | Note |
|---|---|---|---|
| DGS10 | 1962-01-02 | 2026-10-01 | |
| DGS2 | 1976-06-01 | 2026-10-01 | |
| T10Y2Y | 1976-06-01 | 2026-10-02 | |
| DTB3 | 1954-01-04 | 2026-10-01 | cash rate |
| DFF | 1954-07-01 | 2026-10-01 | |
| SOFR | 2018-04-03 | 2026-10-01 | |
| T10YIE | 2003-01-02 | 2026-10-02 | breakeven |
| VIXCLS | 1990-01-02 | 2026-10-01 | |
| NFCI (weekly) | 1971-01-08 | 2026-09-25 | revised; released Wednesdays |
| STLFSI4 (weekly) | 1993-12-31 | 2026-09-25 | |
| ICSA (weekly) | 1967-01-07 | 2026-09-26 | released Thursdays, revised |
| UNRATE (monthly) | 1948 | 2026-09-01 | revised |
| DTWEXBGS | 2006-01-02 | 2026-09-25 | broad USD, weekly lag |
| WALCL / RRPONTSYD | 2002 / 2003 | 2026-09-30 / 10-02 | liquidity |
| **BAMLH0A0HYM2, BAMLC0A0CM** | **2023-10-03** | 2026-10-01 | **ICE BofA OAS series are cut to 3 years on FRED since April 2026** (FRED's series note says so; `cosd=` does not extend them). Not usable for a 2007+ backtest. |
| BAA10Y / DBAA / DAAA / AAA10Y | 1986 / 1986 / 1983 / 1983 | 2026-10-01 | **Use Moody's BAA-10Y (or HYG/IEF, LQD/IEF price ratios) as the long-history credit-spread proxy.** |

### 2.3 Ken French data library: works, ends 2026-08-31

Direct zips (`https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/<name>_CSV.zip`) and `DataReader(name, "famafrench")` both parse. Tested: `F-F_Research_Data_5_Factors_2x3_daily` (1963-07-01 to 2026-08-31), `F-F_Momentum_Factor_daily` (1926-11-03 to 2026-08-31), `F-F_Research_Data_Factors_daily`, `F-F_ST_Reversal_Factor_daily`, `49_Industry_Portfolios_daily` (missing values are coded -99.99/-999). Built from the "202608 CRSP database".
* **pandas 3 pitfall:** the pandas-datareader famafrench reader returns a `PeriodIndex`. Call `df.index = df.index.to_timestamp()` before joining, or it raises `TypeError: Passing PeriodDtype data is invalid`. Values are in percent, so divide by 100.
* Sanity check: correlation of (Mkt-RF + RF) with SPY daily returns over 2007 to 2026-08 is **0.9913**. Annualized vol is 19.9% vs 19.6%.
* Daily RF is rounded to 0.01% steps (alternating 0.01 and 0.02). It averages correctly (4.0% annualized over the last year, against DTB3 3.71%), but use FRED DTB3 or BIL for cash accrual.
* **The OOS factor regression can only run through 2026-08-31** (about 23 of the 501 OOS days are lost). Options: (a) report the regression through Aug 31 and say so; (b) add a parallel regression on ETF proxies (SPY for market, IWD-IWF or VLUE for value, MTUM for momentum, full sample from 2013-04) covering the whole OOS window.
* Extra: the **AQR data library** downloads fine (e.g. `Time-Series-Momentum-Factors-Monthly.xlsx`, ends 2026-05; `Quality-Minus-Junk-Factors-Daily.xlsx`, 32 MB, which is large). Useful for regressing on a TSMOM/BAB/QMJ benchmark.

### 2.4 Stooq: not usable

* `pandas_datareader` 0.11.1: `NotImplementedError: data_source='stooq' is not implemented` (removed).
* `https://stooq.com/q/d/l/?s=spy.us&i=d` and stooq.pl return HTTP 200 with a JavaScript challenge page, not CSV, for every symbol tried (spy.us, tlt.us, ^spx, es.f, cl.f). This is a bot check, so per policy it is **not bypassed**. A second price source for cross-checks: Ken French market return, Cboe/FRED indices, or Databento if a key arrives.

### 2.5 Cboe CDN: works, and gives a real VX futures history

* Index histories: `https://cdn.cboe.com/api/global/us_indices/daily_prices/<SYM>_History.csv`. All of these work: VIX (1990-01-02, OHLC), VIX9D (2011), VIX3M (2009-09-18), VIX6M (2008), VIX1D (2022-05), VVIX (2006-03-06), SKEW (1990), VXN (2009), OVX/GVZ (2009), VXTLT (2004), PUT (1991, PutWrite index), BXM (2002, BuyWrite). Dates are `MM/DD/YYYY` and run to 2026-10-02. MOVE returns 403.
* **VX futures per-contract daily OHLC/Settle/Volume/OI:**
  * 2013 to 2027 expiries: `https://cdn.cboe.com/data/us/futures/market_statistics/historical_data/VX/VX_<YYYY-MM-DD expiry>.csv`. The full list (628 monthly and weekly contracts, with `duration_type` M/W) is in JSON at `https://www.cboe.com/us/futures/market_statistics/historical_data/product/list/VX/`.
  * 2004 to 2012: `https://cdn.cboe.com/resources/futures/archive/volume-and-price/CFE_<MonthCode><YY>_VX.csv`, e.g. `CFE_F08_VX.csv`, `CFE_G10_VX.csv`. Dates are `MM/DD/YYYY`.
  * Quirks: early rows show Open/Close of 0 with only Settle filled, so **use Settle**. The final-day row on the new-path file can show Settle = 0 (VX_2013-01-16), so drop zero settles and use the VRO special opening quotation for expiry.
  * Result: we can build a correctly rolled VX continuous series, with roll yield, from 2004 for free.
* `cdn.cboe.com/api/global/delayed_quotes/term_structure/VIX.json` and the CFE settlement JSON return 403.

### 2.6 Other free sources checked

* **CFTC COT:** yearly zips (`https://www.cftc.gov/files/dea/history/fut_fin_txt_2025.zip`, TFF report) and the Socrata API (`https://publicreporting.cftc.gov/resource/gpe5-46if.json`, latest report 2026-09-29) both work. Positions are as of Tuesday and released Friday, so lag by at least 3 business days.
* **SEC EDGAR:** `https://data.sec.gov/submissions/CIK##########.json` works and includes **8-K item codes per filing** (e.g. AAPL 2026-07-30 items "2.02,9.01"). This is the signal side of the Massive "Trade the 8-K" bonus. `www.sec.gov/Archives/.../full-index` returned 403 with a generic User-Agent; SEC requires a declared contact UA, which the user should set to their own contact details. Options data for that bonus needs the Massive (ex-Polygon) key. Neither a Massive nor a Polygon env var exists on this machine.
* **Webull OpenAPI:** not tested (1 to 2 day approval).

## 3. Databento

**Key status:** no `DATABENTO_API_KEY` (or any Databento/Polygon/Massive/Webull/Tiingo variable) exists in the process, user or machine environment. No `.env*` file under `<automation>` mentions Databento. A wider search of `.env` files across C: and D: was refused by the session's permission classifier and was not pursued. Keys reportedly come via the event Discord, and the user has to obtain them. Signup also gives **$125 of free historical credit, valid 6 months** (pricing page). Account creation must be done by the user.

**Client:** `databento` 0.87.0 is installed and lists datasets including GLBX.MDP3, XNAS.ITCH, DBEQ.BASIC, EQUS.SUMMARY/MINI/ALL, OPRA.PILLAR, XCBF.PITCH (Cboe Futures Exchange, i.e. VX), IFUS/IFEU.IMPACT (ICE), XEUR.EOBI (Eurex). Schemas include `ohlcv-1d`, `ohlcv-eod`, `statistics`, `definition`. Symbology types include `continuous` and `parent`. There is also a `db.Reference` client (adjustment factors, corporate actions).

**Most useful pulls, in priority order:**
1. **GLBX.MDP3 `ohlcv-1d`, `stype_in="continuous"`**. Data starts June 2010 *(docs)*. Symbols follow `ROOT.RULE.RANK`: `c` = calendar, `n` = open interest, `v` = volume, e.g. `ES.v.0`, `ES.v.1`. Roots: ES NQ RTY YM ZN ZB ZF ZT GE/SR3 CL NG RB HO GC SI HG ZC ZS ZW 6E 6J 6B 6A 6C 6S, etc. **Continuous contracts are unadjusted** *(docs: "original, unadjusted prices")*. Use the `instrument_id` change in the output as the roll marker and back-adjust (ratio or difference) yourself; that roll handling is itself a strong judging point.
2. **GLBX.MDP3 `statistics`** for **official settlement prices and open interest**. `ohlcv-1d` is cut by **UTC day** from electronic trades and can differ from settlement *(docs)*. Pull it for the parent symbols only.
3. **GLBX.MDP3 `definition`** for multipliers, tick sizes and expirations, which feed the capacity and cost model. Filter by `stype_in="parent"` (e.g. `ES.FUT`), because the full daily definition set is large.
4. Optional: **XCBF.PITCH** (VX futures, as a cross-check against Cboe CSVs; check the start date with `get_dataset_range`). **OPRA.PILLAR `ohlcv-1d`/`cbbo-1m`** for an options leg. OPRA history begins around 2023 *(unverified; check with `get_dataset_range`)*, so it is too short to be the main backtest. Equities via XNAS.ITCH start 2018-05-01 *(docs example)*, also too short for a 2007 start.

**Cost:** an OHLCV record is 56 bytes. 30 roots x 2 ranks x about 4,100 days is about 14 MB, well under $1 at any listed $/GB rate and trivial against $125. `statistics` and OPRA are the only pulls that can cost real money. **Always call `client.metadata.get_cost(...)` (and `get_billable_size`, `list_unit_prices`) first**, and use `get_dataset_range` for exact coverage. The Standard plan ($199/mo) includes 16+ years of L0 history, OHLCV included *(pricing page)*. That is not needed if we stay on usage credits.

```python
import databento as db, os
client = db.Historical(os.environ["DATABENTO_API_KEY"])           # never hard-code the key
syms = [f"{r}.v.0" for r in ["ES","NQ","ZN","ZB","CL","GC","6E","6J"]]
q = dict(dataset="GLBX.MDP3", schema="ohlcv-1d", stype_in="continuous",
         symbols=syms, start="2010-06-07", end="2026-10-03")
print(client.metadata.get_cost(**q))                               # check cost before pulling
df = client.timeseries.get_range(**q).to_df()                      # roll = instrument_id change per symbol
```

## 4. Recommended free-data universes (daily)

**A. Cross-asset ETF universe (recommended core). Common start 2007-07-02** (VEA starts 2007-07-26; use 2008-01-02 if EMB, which starts 2007-12-19, is included):
SPY, QQQ, IWM, EFA, EEM (or VWO), TLT, IEF, SHY, LQD, HYG, TIP, GLD, SLV, DBC, UUP, VNQ. Add the 9 original SPDR sectors (from 1998) for a sector sleeve and BIL for cash.
* Pros: total-return prices with splits and dividends handled; every fund still trades with large ADV, so capacity and square-root impact can be computed from Yahoo Volume x Close; costs are easy to state (1 to 3 bps half-spread for SPY/TLT/GLD-class funds; HYG/DBC/UUP/SLV are wider).
* It runs through the GFC (2008), 2011, 2015 to 16, 2018 Q4, 2020 and 2022, so regime robustness is testable.
* Signals: FRED (curve slope, real yields, BAA10Y credit spread, NFCI/STLFSI with lags), Cboe vol term structure (VIX/VIX3M, VIX9D from 2011, VVIX, SKEW), COT positioning.

**B. VIX futures carry/term-structure sleeve (2004 to now)** from the Cboe per-contract CSVs. A novel and rigorous angle, with a real instrument and real roll yield.

**C. Futures via Databento (if a key arrives), 2010-06 to now**: back-adjusted continuous ES/NQ/ZN/ZB/CL/GC/6E/… This is the cleanest path for the Databento prize. **Yahoo `=F` series are not suitable for P&L** (see 2.1).

**OOS split (rule: most recent 20% or 2 years, whichever is shorter):**

| History start | Years to 2026-10-02 | 20% would start | Binding | OOS |
|---|---|---|---|---|
| 2006-01-03 | 20.7 | 2022-08-05 | 2 years | **2024-10-03 to 2026-10-02** |
| 2007-07-02 | 19.25 | 2022-11-21 | 2 years | **2024-10-03 to 2026-10-02** |
| 2008-01-02 | 18.75 | 2022-12-28 | 2 years | **2024-10-03 to 2026-10-02** |
| 2010-06-07 (Databento GLBX) | 16.3 | 2023-06-27 | 2 years | **2024-10-03 to 2026-10-02** |
| ETH-USD 2017-11-09 (crypto, 7-day) | 8.9 | 2024-12-22 | **20%** | 2024-12-22 to 2026-10-02 |

The OOS window holds 501 NYSE trading days, first 2024-10-03 (Thu), last 2026-10-02 (Fri). In-sample for universe A is 2007-07-02 to 2024-10-02. **Freeze code and parameters and commit the hypothesis before touching any data after 2024-10-02**, then run the OOS once. Also keep the 2 to 3 day buffer that signal lags imply.

## 5. Data pitfalls to handle in code and in the note

1. **Look-ahead and lags.** Trade at t+1 close (or t+1 open) on signals computed at the t close. FRED daily rates (H.15) for date t are published the next business day, so lag by at least 1 business day. Weekly NFCI (Wednesday release, data to the prior Friday), ICSA (Thursday release), STLFSI, DTWEXBGS and COT (Friday release, Tuesday data) need lags of 3 to 5 business days or more. Monthly macro (UNRATE etc.) is revised; use ALFRED vintages or avoid it.
2. **FRED ICE BofA OAS series hold only 3 years** (BAMLH0A0HYM2, BAMLC0A0CM start 2023-10-03). Use BAA10Y or ETF ratios instead.
3. **Ken French ends 2026-08-31**, so the factor regression misses the last month of OOS. Disclose this and add an ETF-proxy regression. Under pandas 3 the reader returns a PeriodIndex.
4. **Yahoo `=F` futures:** unadjusted roll gaps, a negative CL print, bad 6J prints, asynchronous closes. Do not use them for returns.
5. **Survivorship in ETF choice:** the funds are survivors chosen today. Fix the universe from fund launch dates before the IS start, document the rule, and note that the very large, liquid funds used carry minimal delisting risk. Structural changes: USO changed its roll methodology in April 2020 and did a 1:8 reverse split; DBC uses an optimized roll; HYG/EMB/BIL/VEA start in 2007.
6. **Stale prints and holidays:** repeated closes (UUP, HYG, DBC, ZN=F). Calendars must be aligned: crypto trades 7 days, FX has weekend-dated bars, Cboe CSVs use MM/DD/YYYY, FRED uses blank/"." for NA.
7. **Adjusted prices change retroactively** whenever a dividend is added. Snapshot pulls to parquet with a pull timestamp and hash for reproducibility, and do not re-download during the final OOS run.
8. **The latest daily bar can be partial** if pulled during market hours. Our end date is 2026-10-02 and the pull happened on Saturday, so this does not apply now, but pin `end="2026-10-03"`.
9. **Costs:** state the bps per instrument and show 1x and 2x. Get ADV for square-root impact from Yahoo Volume (ETFs) or Databento volume/OI (futures). Index levels (^VIX, ^GSPC) have zero volume and are not tradable.
10. **Storage:** D: is a FAT32 USB stick at about 130 KB/s sustained (FAT32 also caps files at 4 GB). Put caches on C: (e.g. `<home>/.cache/gqh/`) or keep `data/cache/` small. It is already git-ignored.

## 6. Files produced

* `<solo-repo>/requirements.txt`: pinned freeze.
* `<solo-repo>/.venv/Lib/site-packages/zz_gqh_cvenv.pth`: shim to the C: venv.
* Scratch test outputs (`.../scratchpad/data_tests/`): `yf_daily_summary.csv` (per-ticker coverage table), `yf_test.py`, `yf_test2.py`, `pdr_test.py`, `fred_*.csv` (17 series), the Ken French CSVs (5 files), `cboe_*_History.csv` and two sample VX contract files.
