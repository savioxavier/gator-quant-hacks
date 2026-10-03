# Strategy 01 (Fed-speech tone, Variant A): independent review

**Verdict: drop.** We reproduced their results exactly. The frozen rule lost money in the clean out-of-sample test, and in-sample it is a 2022 rate trade.

| Window | Their accounting (rf=0) | Our engine, excess over T-bill | Futures ZN + short 6E | core_ER_6 Sharpe change, ETF / ZN sleeve |
|---|---|---|---|---|
| In-sample 2012..2024-10-02 | 0.205 | 0.210 (0.203 corrected) | 0.36 | -0.05 / +0.085 |
| In-sample without 2022 | 0.065 | 0.060 | 0.17 | |
| Holdout 2021..2024-10 (in-sample) | 0.693 | 0.691 | 0.83 | +0.27 / +0.27 |
| **Out of sample 2024-10-03..2026-10-02** | **-0.235** | **-0.456** | 0.10 | **-0.37 / -0.03** |
| Full period | 0.142 | 0.122 | 0.32 | -0.09 / +0.07 |

**Reproduction.** It matches exactly. Two independent implementations agree with their equity_is.csv on every daily column to within 3e-14, and with every published statistic: gross 0.255, 1x 0.205, 2x 0.156, 2022 1.19, other years 0.07, corr with DGS2 0.53, turnover 23x/yr, max DD -33%. Their trial 1 (0.41) also reproduces, and the "spec fix" that lowered it was a genuine correction. Their market data match ours. Our engine shows 0.177 at rf=0 against their 0.205. The difference comes from booking P&L open-to-open (-0.018) and the 30 bp short borrow (-0.014); T-bill accounting then adds +0.032.

**Out of sample (the clean test).** We fetched and scored the 203 Board speeches after their cut with their frozen lexicon. Our scorer matches their scores exactly on 144 of 144 checked documents. The rule returned -5%/yr, Sharpe -0.46, max DD -15.6%. Almost all of the loss is Q4 2024 (-11.8%): the book was about 0.96 long TLT while 2-year yields rose 62 bp. Without that quarter the Sharpe is 0.14. The cause is a design flaw. The consensus is a decayed *sum*, and kept speeches rose from 27 to 47 a year. That pushed z to an average of -1.1, so the book stayed persistently long bonds. Speech volume drove the signal, not tone. Caveats: the window is only 501 days (90% interval [-1.2, 0.3]), and the author's log is dated 2026-10-03, so they could have seen those years.

**More than rate momentum?** Barely, and not significantly. The consensus correlates 0.53 with the 2-year yield level. Regressed on a DGS2-change control, the strategy has beta 0.31 and alpha 2.3%/yr (t 0.84). Tone does not forecast TLT: the correlation with next-20-day returns is -0.055 in-sample and has the wrong sign out of sample. Lagging the signal one more day *raises* the Sharpe to 0.295, so this is not a reaction to speeches.

**2022.** 2022 supplies 75% of in-sample P&L, and the 10 best days supply 99%. The in-sample bootstrap interval is [-0.20, 0.60].

**Futures version.** It looks better but is not credible. About half of the gain comes from a one-day-slower fill: ETFs on the same timing get 0.30 in-sample. The 1.5 gross cap binds on 54% of days, so the book runs at about 6% vol. Out of sample, the 0.10 comes from the short-6E leg (0.23); the ZN leg made 0.005. The verification pass did not independently recheck this version.

**Portfolio.** The ETF sleeve hurts core_ER_6 in-sample, in 2012-17 (-0.43, p 0.03) and out of sample (-0.37). The ZN sleeve gives +0.085 in-sample (p 0.30) and -0.03 out of sample. Both fail the pre-declared rule, which requires a gain in-sample, in the holdout and out of sample.

**0.7 bar.** The rule clears it only in the 2021-24 holdout: 0.69 for the ETFs, 0.83 for futures. That window is in-sample, driven by 2022 (0.42 without it) and, for futures, partly a timing artifact. Nowhere is it credible.

**Disagreements flagged.**
- The analysis pass's gross 0.272 leaves out borrow; with borrow it is 0.258.
- The verification pass corrects in-sample 0.210 to 0.203: three speeches were used before they were given, and some FOMC de-risk dates were not pre-announced.
- No result changes the verdict.

**Ideas, pre-registered on new data only. Low prior.**
1. Mean tone instead of a decayed sum. Normalising by speech count fixes the volume drift, but we found it after seeing the out-of-sample data, so it needs post-2026-10 data.
2. Replace the lexicon with FOMC-RoBERTa (or similar) scoring. The lexicon finds a median 3 hits per document and keeps only 46% of documents. Test first on speech-day TLT/2-year moves before any holding rule.
3. Orthogonalise to the 2-year yield from the start.
