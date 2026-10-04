# Hypothesis — Variant A (trial 1)

**Claim.** The exponentially-decayed consensus of Board of Governors speech tone, scored with a frozen hawk/dove lexicon, is a lagged predictor of next-open TLT and UUP returns. Hawkish consensus → short duration / long USD; dovish consensus → the reverse.

**Mechanism.** Prepared Fedspeak is dated (often date-only) and is not fully in the open print of the same session. Markets update policy-path beliefs after the text is public. Cumulative tone (half-life 20 sessions) is a slow state variable for the rates/USD complex, not a same-day event trade.

**Falsifiers (in-sample only).**
- Daily IS Sharpe net of 1x costs near 0 or negative after open-to-open lag, costs, FOMC de-risk, and expanding-z (min 252).
- `corr(C_t, DGS2_{t-2})` ≈ 0 and the TLT timing term `cov(pos, r_TLT)` ≈ 0 (tone is not tracking the 2y path and is not timing duration).
- All 1x Sharpe concentrated in 2022 (one-regime artifact).
- Gross Sharpe ≫ net Sharpe with extreme turnover (not tradable after 1.5/5.0 bps).

**What would make this a bug, not a result.** Daily IS Sharpe net 1x costs > 1.5 (stop and hunt). > 3 is a construction error (lookahead, unadjusted close, or scoring the FOMC statement).

**Deliberately not claimed.** Regional-Fed corpus, FinBERT/LLM scores, testimony Q&A, OOS, CSCV/PBO, capacity. Board speeches + date-only → next-session-open lag is the simulation.

**Decision rule for tomorrow.** GO if 1x IS Sharpe is credibly positive after the falsifiers above; NO-GO if ~0/negative or 2022-only; BORDERLINE if modestly positive but fragile (tiny n, 2022-heavy, or cost-sensitive).
