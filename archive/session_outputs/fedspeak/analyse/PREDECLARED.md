# Fed speech tone, Variant A: analysis plan (label "analyse")

Written 2026-10-03 before any post-cut (2024-10-03 onwards) result of the strategy, the control, the
orthogonalised variant, the futures version or the portfolio test was computed. Known at writing: the
in-sample replication (replicate/SPEC_OURS.md) and the extended speech scores (extend/), whose
validation was checked but whose trading result was not.

## Rule under test (frozen, as replicated)

replicate/fedsignal.py unchanged: consensus half-life 20 sessions, expanding z (clock 2011-01-03,
min 252), clip 2, 75/25 TLT/UUP, 10 % vol target on the 20/60 blended open-to-open mix vol (floor 4 %),
gross cap 1.5, FOMC halves TLT, no-trade band 0.10, costs TLT 1.5 bp / UUP 5 bp, engine next_open.

Inputs for the full run: kept rows of extend/speech_scores_2011_2026.csv (their CSV up to the cut, our
re-score after it). FOMC sessions: their fomc_dates.csv up to 2024-10-02, then the scheduled
announcement days from edges/calendar/fomc_scheduled.csv (federalreserve.gov calendar). The in-sample
weights must equal the replication's weights (checked).

Windows: IS 2011-12-30 .. 2024-10-02; holdout 2021-01-01 .. 2024-10-02 (descriptive, in-sample);
OOS 2024-10-03 .. 2026-10-02; FULL 2011-12-30 .. 2026-10-02. Sharpe in two definitions: rf = 0
(engine run with zero rf, Sharpe of net) and ours (engine run with T-bill, Sharpe of net minus T-bill).

## 1. Control: rate momentum with the same machinery

inj_t = DGS2(t-2) - DGS2(t-3) for entry session t (DGS2 forward-filled on the NYSE calendar, so a bond
holiday contributes 0). C_ctl_t = lam C_ctl_{t-1} + inj_t with lam = 2^(-1/20). Positive C_ctl (yields
rising) is "hawkish": short TLT, long UUP. Then the identical z, sizing, FOMC, band, costs and engine.

Tests: (a) OLS of the strategy's daily excess return on the control's daily excess return, alpha and
NW t (5 lags), beta, R2, per window; (b) correlation and partial correlation of z_tone_t with future TLT
open-to-open returns from open t over h = 1, 5, 20 sessions, controlling for z_ctl_t (spec A) and for
z_ctl_t plus the 5- and 60-session DGS2 changes ending at t-2 (spec B); OLS with NW t (lags h + 4);
h = 20 also on non-overlapping 20-session samples.

## 2. Tone orthogonalised to the DGS2 change

For each session t from the clock start: OLS (with intercept) of C_tone on C_ctl over all sessions from
2011-01-03 to t (expanding, min 252 obs); e_t = C_tone_t - a_t - b_t C_ctl_t; z_orth_t = e_t / s_t with
s_t the residual std of that fit (ddof 2). z_orth replaces z in the frozen sizing.

## 3. 2022 dependence

Sharpe excluding calendar 2022 (IS, holdout, FULL); circular block bootstrap of the IS 1x Sharpe,
63-day blocks, 10,000 draws, seed 7, 90 % interval (21 and 126-day blocks as sensitivity); share of the
summed IS daily net return from the 10 best days, and the Sharpe without them.

## 4. Futures version (no tuning)

Same z. Bond leg F_ZN (primary) and F_ZB (secondary) in place of TLT; short F_6E in place of long UUP
(w_6E = -w_UUP). Vol = 20/60 blend of the close-to-close excess-return mix -0.75 r_bond - 0.25 r_6E
ending at the decision close, floor 4 %; same target, clip, cap 1.5, FOMC haircut on the bond leg,
band. Strict timing: the decision at close d uses z of session d (information by the open of d); the
engine next_close fills at close d+1 and earns from d+2; FOMC flags refer to the holding day. Costs ZN
1 bp, ZB 1.5 bp, 6E 1 bp, roll days one extra round trip (engine). Futures returns are excess returns, so
one Sharpe (excess) is reported.

## 5. Portfolio fit

Correlation of the strategy's daily excess (net 1x, ETF version) with PORT_core_ER_6 net_1x and with its
sleeves rpm_ES_MM, CAL_TSY_ME_ZN, S1 (daily and monthly sums). Test: core_ER_6 rebuilt with
edges/combine/combine.py build() (ER, 6 %, trailing 252-day covariance, month-end, applied d+2, cap 4,
overlay costs) with the strategy as a fourth sleeve (live after 126 returns; sleeve gross = held
|w_TLT| + |w_UUP|; overlay cost = gross-weighted TLT/UUP cost). Primary fourth sleeve: the ETF version;
secondary: the ZN futures version. The rebuilt 3-sleeve portfolio must equal PORT_core_ER_6.
Reported per window (IS from the combine common start 2012-05-02, holdout, OOS, FULL): Sharpe 1x/2x/gross,
excess return, vol, max DD, NW t, and the Sharpe change with a paired 63-day block bootstrap (5,000
draws). The addition counts as helpful only if the 1x Sharpe change is positive in IS, holdout and OOS.
