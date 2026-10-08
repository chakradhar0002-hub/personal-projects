"""Standalone technical-analysis signals in the 3-day results window (F&O results only).

    python3 standalone_ta.py        (reads ../build read-only, writes into this folder)

PRE-REGISTRATION (written before any signal outcome was computed; nothing below is tuned)
==========================================================================================
Universe   : events_ta.csv rows with in_fo True and three_day present (3,278 results, qn 0..21).
Trade      : buy at the cutoff close (2 sessions before the result session), sell at the Day+1 close.
             three_day = d1 + d2 + d3 (sum of the Day-1, Result-day and Day+1 daily returns, percent, gross).
             take_profit (long) = d1 if d1 > 3, else d1 + d2 if d1 + d2 > 3, else three_day.
             Cost 0.17 (percent) per round trip.
Short side : a short signal is scored in its own direction: edge = -three_day; short take-profit is the mirror
             (-d1 if -d1 > 3, else -(d1 + d2) if > 3, else -three_day). Shorting F&O stocks is possible via futures;
             a short signal is equally an "avoid this long" filter.
Signal day : the cutoff close only (all indicators in the panel use data up to and including that close).

SIGNALS (44; fixed textbook thresholds; L = long, S = short mirror, N = non-directional tested as long)
  L01 RSI(14) < 30                          S01 RSI(14) > 70
  L02 RSI(2) < 10                           S02 RSI(2) > 90
  L03 Stochastic %K(14) < 20                S03 Stochastic %K(14) > 80
  L04 Williams %R(14) < -80                 S04 Williams %R(14) > -20
      (NOTE: %R = %K - 100 by definition, so L04 == L03 and S04 == S03 exactly; kept because it was asked for and
       still counted in the multiple-testing number.)
  L05 CCI(20) < -100                        S05 CCI(20) > 100
  L06 MFI(14) < 20                          S06 MFI(14) > 80
  L07 close below lower Bollinger(20,2) (%B < 0)          S07 close above upper band (%B > 1)
  L08 MACD bullish crossover on k-2..k (macd_bull_x3)     S08 MACD bearish crossover on k-2..k (macd_bear_x3)
  L09 MACD line < 0 and histogram rising (hist_k > hist_k-1)
                                            S09 MACD line > 0 and histogram falling (hist_k < hist_k-1)
      (hist_k-1 is not in the panel: recomputed here from adjusted_ohlcv.csv.gz with the builder's exact EMA
       definition and checked against the panel's macd_hist_pct / macd_pct.)
  L10 pullback in an uptrend: close > SMA200 and close < SMA50
                                            S10 rally in a downtrend: close < SMA200 and close > SMA50
  L11 golden-cross state (SMA50 > SMA200)   S11 death-cross state (SMA50 <= SMA200)
  L12 fresh golden cross (k-9..k)           S12 fresh death cross (k-9..k)
  L13 ADX(14) > 25 and +DI > -DI            S13 ADX(14) > 25 and -DI > +DI
  L14 hammer                                S14 shooting star
  L15 bullish engulfing                     S15 bearish engulfing
  L16 gap down > 2% on day k (gap_pct < -2), long = gap fill
                                            S16 gap up > 2% (gap_pct > 2), short = gap fill
  L17 within 5% of the 52-week low (dist_52w_low_pct <= 5), long = support
                                            S17 within 5% of the 52-week high (dist_52w_high_pct >= -5), short = resistance
      (the direction of L16/S16/L17/S17 is the task's long/short ordering; momentum reads them the other way.
       The two-sided p-value below covers both readings.)
  L18 Donchian-20 breakout up (close > prior 20-session high)
                                            S18 Donchian-20 breakdown (close < prior 20-session low)
  L19 OBV bullish divergence (20-session price slope < 0, OBV slope > 0)
                                            S19 OBV bearish divergence (price slope > 0, OBV slope < 0)
  L20 oversold count >= 3                   S20 overbought count >= 3
  L21 oversold count >= 4                   S21 overbought count >= 4
      oversold count  = #(RSI14 < 30, %K < 20, %B < 0, CCI < -100, MFI < 20, %R < -80)   (%K and %R are the same
                        condition, so the count effectively double-counts the stochastic)
      overbought count = #(RSI14 > 70, %K > 80, %B > 1, CCI > 100, MFI > 80, %R > -20)
  N01 NR7 (narrowest range of 7)            N02 doji
      (non-directional textbook signals; tested as long, judged on the two-sided p-value)

REPORTED FOR EACH SIGNAL (direction-adjusted, percent)
  trades, average three_day, after cost (-0.17), take-profit average (and after cost), up % (edge > 0), median,
  quarters with trades / quarters positive, first 14 quarters (qn 0..13) vs last 8 (qn 14..21) averages,
  average without the best 5 trades, placebo on non-results days, results minus placebo, luck test.
  Placebo  : the same signal on placebo_ta.csv.gz rows with in_fo True (F&O stock-days with no result session within
             10 sessions of the 3-day window); outcome = sum of the next 3 daily returns. Rows overlap in time, so the
             placebo standard error is clustered by calendar month (and the results one by cutoff month);
             results-minus-placebo z = diff / sqrt(se_res^2 + se_pla^2).
  Luck     : 20,000 random draws of the same number of trades per quarter from all F&O results of that quarter
             (without replacement); p_one = share of draws whose direction-adjusted average >= the signal's
             (+1 smoothing), p_two = 2 x min(upper, lower tail), capped at 1.
  Multiple testing over the 44 signals (primary = three_day): Holm and Benjamini-Hochberg on p_two.

PASS CRITERIA (all must hold to call a signal a candidate; set before running)
  (1) Holm-adjusted p_two < 0.05 on three_day (44 tests), effect in the pre-registered direction (N: either).
  (2) average after cost > 0.
  (3) first-14 and last-8 averages both > 0 (gross, direction-adjusted).
  (4) average without the best 5 trades > 0 (gross).
  (5) at least 60% of quarters with trades positive.
  (6) results minus placebo > 0 (the edge is not just the same signal's ordinary 3-day drift).
  Nominal p_two < 0.05 that fails Holm = "unconfirmed hint", not a finding.

SECONDARY (informational only, never used for pass/fail)
  - average excess over Nifty 50 (three_day minus the Nifty's sum of the same 3 daily returns), because oversold
    signals cluster in market-wide sell-off weeks;
  - overlap with the known lag10_volume rule (85 trades) and the average without those trades.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(os.path.dirname(HERE), "build")
SP = os.path.dirname(os.path.dirname(HERE))
PACK = f"{SP}/sector_lab/data"
LAG10 = os.environ.get('REPO_ROOT', '.') + "/results/lag10_volume/trades.csv"
COST = 0.17
NSIM = 20000
RNG = np.random.default_rng(20261008)


# ------------------------------------------------------------------------------------------------ MACD hist k-1
def seeded(x, n, alpha, start):
    """Copy of build_panel.seeded: RMA/EMA of x[start:] seeded with the mean of its first n values."""
    out = np.full(len(x), np.nan)
    if len(x) - start < n:
        return out
    y = x[start + n - 1:].astype(float).copy()
    y[0] = x[start:start + n].mean()
    out[start + n - 1:] = np.array(pd.Series(y).ewm(alpha=alpha, adjust=False).mean(), dtype=float)
    return out


def macd_hist_grid(sessions):
    """(sessions x symbols) matrices of MACD hist at k and at the previous traded day, and MACD line, all / close."""
    a = pd.read_csv(f"{BUILD}/adjusted_ohlcv.csv.gz", usecols=["day", "symbol", "close"])
    C = a.pivot(index="day", columns="symbol", values="close").reindex(index=sessions)
    syms = C.columns.tolist()
    Cm = C.to_numpy(float)
    T, N = Cm.shape
    H, Hp, M = (np.full((T, N), np.nan) for _ in range(3))
    for j in range(N):
        rows = np.flatnonzero(np.isfinite(Cm[:, j]))
        c = Cm[rows, j]
        macd = seeded(c, 12, 2 / 13, 0) - seeded(c, 26, 2 / 27, 0)
        hist = macd - seeded(macd, 9, 0.2, 25)
        H[rows, j] = hist / c * 100
        hp = np.full(len(c), np.nan)
        hp[1:] = hist[:-1] / c[1:] * 100          # previous day's hist scaled by TODAY's close: same price units
        Hp[rows, j] = hp
        M[rows, j] = macd / c * 100
    return syms, H, Hp, M


# ------------------------------------------------------------------------------------------------ signals
def signal_defs():
    D = []
    add = lambda code, name, d, f: D.append((code, name, d, f))
    add("L01", "RSI14 < 30", "long", lambda x: x.rsi14 < 30)
    add("S01", "RSI14 > 70", "short", lambda x: x.rsi14 > 70)
    add("L02", "RSI2 < 10", "long", lambda x: x.rsi2 < 10)
    add("S02", "RSI2 > 90", "short", lambda x: x.rsi2 > 90)
    add("L03", "Stoch %K < 20", "long", lambda x: x.stoch_k14 < 20)
    add("S03", "Stoch %K > 80", "short", lambda x: x.stoch_k14 > 80)
    add("L04", "Williams %R < -80", "long", lambda x: x.willr14 < -80)
    add("S04", "Williams %R > -20", "short", lambda x: x.willr14 > -20)
    add("L05", "CCI20 < -100", "long", lambda x: x.cci20 < -100)
    add("S05", "CCI20 > 100", "short", lambda x: x.cci20 > 100)
    add("L06", "MFI14 < 20", "long", lambda x: x.mfi14 < 20)
    add("S06", "MFI14 > 80", "short", lambda x: x.mfi14 > 80)
    add("L07", "close < lower BB", "long", lambda x: x.bb_pctb < 0)
    add("S07", "close > upper BB", "short", lambda x: x.bb_pctb > 1)
    add("L08", "MACD bull cross (3d)", "long", lambda x: x.macd_bull_x3 == 1)
    add("S08", "MACD bear cross (3d)", "short", lambda x: x.macd_bear_x3 == 1)
    add("L09", "MACD<0, hist rising", "long", lambda x: (x.macd_pct < 0) & (x.hist_k > x.hist_k1))
    add("S09", "MACD>0, hist falling", "short", lambda x: (x.macd_pct > 0) & (x.hist_k < x.hist_k1))
    add("L10", "C>SMA200 & C<SMA50", "long", lambda x: (x.close_vs_sma200_pct > 0) & (x.close_vs_sma50_pct < 0))
    add("S10", "C<SMA200 & C>SMA50", "short", lambda x: (x.close_vs_sma200_pct < 0) & (x.close_vs_sma50_pct > 0))
    add("L11", "golden state", "long", lambda x: x.golden_state == 1)
    add("S11", "death state", "short", lambda x: x.golden_state == 0)
    add("L12", "fresh golden cross", "long", lambda x: x.golden_x10 == 1)
    add("S12", "fresh death cross", "short", lambda x: x.death_x10 == 1)
    add("L13", "ADX>25 & +DI>-DI", "long", lambda x: (x.adx14 > 25) & (x.plus_di14 > x.minus_di14))
    add("S13", "ADX>25 & -DI>+DI", "short", lambda x: (x.adx14 > 25) & (x.minus_di14 > x.plus_di14))
    add("L14", "hammer", "long", lambda x: x.cdl_hammer == 1)
    add("S14", "shooting star", "short", lambda x: x.cdl_shooting_star == 1)
    add("L15", "bullish engulfing", "long", lambda x: x.cdl_bull_engulf == 1)
    add("S15", "bearish engulfing", "short", lambda x: x.cdl_bear_engulf == 1)
    add("L16", "gap down > 2%", "long", lambda x: x.gap_pct < -2)
    add("S16", "gap up > 2%", "short", lambda x: x.gap_pct > 2)
    add("L17", "within 5% of 52w low", "long", lambda x: x.dist_52w_low_pct <= 5)
    add("S17", "within 5% of 52w high", "short", lambda x: x.dist_52w_high_pct >= -5)
    add("L18", "Donchian20 break up", "long", lambda x: x.don20_break_up == 1)
    add("S18", "Donchian20 break down", "short", lambda x: x.don20_break_dn == 1)
    add("L19", "OBV bull divergence", "long", lambda x: x.obv_div20 == 1)
    add("S19", "OBV bear divergence", "short", lambda x: x.obv_div20 == -1)
    add("L20", "oversold count >= 3", "long", lambda x: x.os_count >= 3)
    add("S20", "overbought count >= 3", "short", lambda x: x.ob_count >= 3)
    add("L21", "oversold count >= 4", "long", lambda x: x.os_count >= 4)
    add("S21", "overbought count >= 4", "short", lambda x: x.ob_count >= 4)
    add("N01", "NR7", "nondir", lambda x: x.nr7 == 1)
    add("N02", "doji", "nondir", lambda x: x.cdl_doji == 1)
    return D


def prepare(df, nifty_ret, i_cols):
    df = df.copy()
    df["os_count"] = ((df.rsi14 < 30).astype(int) + (df.stoch_k14 < 20) + (df.bb_pctb < 0) + (df.cci20 < -100)
                      + (df.mfi14 < 20) + (df.willr14 < -80))
    df["ob_count"] = ((df.rsi14 > 70).astype(int) + (df.stoch_k14 > 80) + (df.bb_pctb > 1) + (df.cci20 > 100)
                      + (df.mfi14 > 80) + (df.willr14 > -20))
    df["nifty3"] = sum(100 * nifty_ret[df[c].to_numpy()] for c in i_cols)
    df["excess"] = df.three_day - df.nifty3
    s1, s12 = -df.d1, -(df.d1 + df.d2)
    df["tp_short"] = np.where(s1 > 3, s1, np.where(s12 > 3, s12, -df.three_day))
    return df


def cl_se(v, g):
    """Standard error of the mean of v clustered by g (CR0 with small-sample factor)."""
    v = np.asarray(v, float)
    n = len(v)
    if n < 2:
        return np.nan
    u = pd.Series(v - v.mean()).groupby(np.asarray(g)).sum().to_numpy()
    G = len(u)
    if G < 2:
        return np.nan
    return np.sqrt(G / (G - 1) * (u ** 2).sum()) / n


def holm(p):
    p = np.asarray(p)
    o = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    run = 0
    for r, i in enumerate(o):
        run = max(run, (m - r) * p[i])
        adj[i] = min(1, run)
    return adj


def bh(p):
    p = np.asarray(p)
    m = len(p)
    o = np.argsort(p)
    q = np.empty(m)
    prev = 1
    for r in range(m - 1, -1, -1):
        i = o[r]
        prev = min(prev, p[i] * m / (r + 1))
        q[i] = prev
    return q


def main():
    out = []
    log = lambda *a: (print(*a), out.append(" ".join(str(x) for x in a)))
    sessions = pd.read_csv(f"{PACK}/sessions.csv").day.tolist()
    nifty = pd.read_csv(f"{PACK}/index_close.csv", index_col=0, usecols=["day", "Nifty 50"])["Nifty 50"]
    assert nifty.index.tolist() == sessions
    nv = nifty.to_numpy(float)
    nifty_ret = np.r_[np.nan, nv[1:] / nv[:-1] - 1]

    ev = pd.read_csv(f"{BUILD}/events_ta.csv")
    ev = ev[(ev.in_fo == True) & ev.three_day.notna()].reset_index(drop=True)
    pl = pd.read_csv(f"{BUILD}/placebo_ta.csv.gz", low_memory=False)
    pl = pl[pl.in_fo == True].reset_index(drop=True)
    assert len(ev) == 3278 and len(pl) == 120238
    assert (pl.i + 3 < len(sessions)).all()

    # MACD histogram at k and at the previous traded day
    syms, H, Hp, M = macd_hist_grid(sessions)
    col = {s: j for j, s in enumerate(syms)}
    for df, icol in ((ev, "i_cut"), (pl, "i")):
        ii, jj = df[icol].to_numpy(), df.symbol.map(col).to_numpy()
        df["hist_k"], df["hist_k1"], df["macd_chk"] = H[ii, jj], Hp[ii, jj], M[ii, jj]
    for nm, df in (("events", ev), ("placebo", pl)):
        dh = (df.hist_k - df.macd_hist_pct).abs()
        dm = (df.macd_chk - df.macd_pct).abs()
        log(f"MACD recompute check ({nm}): rows {len(df)}, NaN hist_k1 {df.hist_k1.isna().sum()}, "
            f"max |hist - panel| {dh.max():.2e} (% of close), max |line - panel| {dm.max():.2e}, "
            f"sign(hist) disagreements {int((np.sign(df.hist_k) != np.sign(df.macd_hist_pct)).sum())}")

    ev = prepare(ev, nifty_ret, ["i_m1", "i_rd", "i_p1"])
    pl["i1"], pl["i2"], pl["i3"] = pl.i + 1, pl.i + 2, pl.i + 3
    pl = prepare(pl, nifty_ret, ["i1", "i2", "i3"])
    # sanity: placebo three_day = sum of next 3 daily returns, already checked by the builder
    ev["month"] = ev.cutoff.str[:7]
    pl["month"] = pl.day.str[:7]

    lag10 = pd.read_csv(LAG10)
    lagkey = set(zip(lag10.symbol, lag10.cutoff))
    ev["in_lag10"] = [(s, c) in lagkey for s, c in zip(ev.symbol, ev.cutoff)]
    assert ev.in_lag10.sum() == 85

    defs = signal_defs()
    # signal flags (NaN comparisons are False; the panel has no NaN in F&O rows except hist_k1 on day 1 of history)
    for code, name, d, f in defs:
        ev[code] = f(ev).fillna(False).astype(bool)
        pl[code] = f(pl).fillna(False).astype(bool)

    # ---------------------------------------------------------------- luck: common random permutations per quarter
    qs = sorted(ev.qn.unique())
    pools = {q: ev.index[ev.qn == q].to_numpy() for q in qs}
    need = {q: sorted({int(ev.loc[pools[q], code].sum()) for code, *_ in defs} - {0}) for q in qs}
    rand = {m: np.zeros((NSIM, len(defs))) for m in ("three_day", "take_profit", "tp_short", "excess")}
    cnt = {code: ev.groupby("qn")[code].sum() for code, *_ in defs}
    for q in qs:
        P = len(pools[q])
        perm = np.argsort(RNG.random((NSIM, P)), axis=1)
        for m in rand:
            vals = ev.loc[pools[q], m].to_numpy()
            cs = np.cumsum(vals[perm], axis=1)
            for s, (code, *_ ) in enumerate(defs):
                n = int(cnt[code].get(q, 0))
                if n:
                    rand[m][:, s] += cs[:, n - 1]
    base_res = ev.three_day.mean()
    base_pla = pl.three_day.mean()
    log(f"\nBaselines: all F&O results three_day {base_res:+.3f} (n {len(ev)}), take_profit {ev.take_profit.mean():+.3f}; "
        f"all F&O placebo days {base_pla:+.3f} (n {len(pl)})")

    rows, perq = [], []
    for s, (code, name, d, f) in enumerate(defs):
        sg = -1.0 if d == "short" else 1.0
        x = ev[ev[code]]
        n = len(x)
        e3 = sg * x.three_day
        etp = x.take_profit if d != "short" else x.tp_short
        exc = sg * x.excess
        by_q = e3.groupby(x.qn).agg(["size", "mean"])
        for q, r in by_q.iterrows():
            perq.append({"code": code, "signal": name, "direction": d, "qn": q, "trades": int(r["size"]),
                         "avg_pct": r["mean"], "tp_avg_pct": etp[x.qn == q].mean()})
        y = pl[pl[code]]
        p3 = sg * y.three_day
        ptp = y.take_profit if d != "short" else y.tp_short
        # luck
        rm = rand["three_day"][:, s] / n * sg
        obs = e3.mean()
        up_t = (1 + (rm >= obs - 1e-12).sum()) / (NSIM + 1)
        lo_t = (1 + (rm <= obs + 1e-12).sum()) / (NSIM + 1)
        rtp = (rand["tp_short" if d == "short" else "take_profit"][:, s]) / n
        tp_up = (1 + (rtp >= etp.mean() - 1e-12).sum()) / (NSIM + 1)
        rex = rand["excess"][:, s] / n * sg
        ex_up = (1 + (rex >= exc.mean() - 1e-12).sum()) / (NSIM + 1)
        ex_lo = (1 + (rex <= exc.mean() + 1e-12).sum()) / (NSIM + 1)
        se_r, se_p = cl_se(e3, x.month), cl_se(p3, y.month)
        diff = obs - p3.mean()
        nl = x.in_lag10.sum()
        rows.append({
            "code": code, "signal": name, "direction": d, "trades": n,
            "trades_per_quarter": n / 22, "avg_pct": obs, "avg_net_pct": obs - COST,
            "median_pct": e3.median(), "up_pct": 100 * (e3 > 0).mean(),
            "tp_avg_pct": etp.mean(), "tp_net_pct": etp.mean() - COST,
            "quarters_with_trades": int(by_q.shape[0]), "quarters_positive": int((by_q["mean"] > 0).sum()),
            "first14_pct": e3[x.qn <= 13].mean(), "last8_pct": e3[x.qn >= 14].mean(),
            "n_first14": int((x.qn <= 13).sum()), "n_last8": int((x.qn >= 14).sum()),
            "without_best5_pct": e3.sort_values().iloc[:-5].mean() if n > 5 else np.nan,
            "random_avg_pct": rm.mean(), "random_p95_pct": np.percentile(rm, 95),
            "luck_p_one": up_t, "luck_p_two": min(1.0, 2 * min(up_t, lo_t)), "tp_luck_p_one": tp_up,
            "placebo_trades": len(y), "placebo_avg_pct": p3.mean(), "placebo_tp_pct": ptp.mean(),
            "placebo_all_pct": sg * base_pla,
            "res_minus_placebo_pct": diff, "res_minus_placebo_z": diff / np.sqrt(se_r ** 2 + se_p ** 2),
            "se_res_cluster_month": se_r, "se_placebo_cluster_month": se_p,
            "excess_vs_nifty_pct": exc.mean(), "excess_luck_p_two": min(1.0, 2 * min(ex_up, ex_lo)),
            "lag10_overlap": int(nl), "avg_without_lag10_pct": sg * x.three_day[~x.in_lag10].mean(),
        })
    S = pd.DataFrame(rows)
    S["holm_p"] = holm(S.luck_p_two.to_numpy())
    S["bh_q"] = bh(S.luck_p_two.to_numpy())
    S["holm_p_excess"] = holm(S.excess_luck_p_two.to_numpy())
    good_dir = (S.avg_pct > S.random_avg_pct) | (S.direction == "nondir")
    crit = pd.DataFrame({
        "c1_holm": (S.holm_p < 0.05) & good_dir,
        "c2_net": S.avg_net_pct > 0,
        "c3_halves": (S.first14_pct > 0) & (S.last8_pct > 0),
        "c4_wo_best5": S.without_best5_pct > 0,
        "c5_quarters": S.quarters_positive >= 0.6 * S.quarters_with_trades,
        "c6_placebo": S.res_minus_placebo_pct > 0,
    })
    S = pd.concat([S, crit], axis=1)
    S["criteria_met"] = crit.sum(axis=1)
    S["verdict"] = np.where(crit.all(axis=1), "CANDIDATE",
                   np.where((S.luck_p_two < 0.05) & good_dir, "unconfirmed hint (nominal p<0.05, fails Holm or other)",
                   np.where((S.luck_p_two < 0.05) & ~good_dir, "REVERSE direction (nominal p<0.05)", "nothing")))
    S.to_csv(f"{HERE}/signals_summary.csv", index=False, float_format="%.5g")
    pd.DataFrame(perq).to_csv(f"{HERE}/per_quarter.csv", index=False, float_format="%.5g")
    keep = ["symbol", "quarter", "qn", "cutoff", "i_cut", "d1", "d2", "d3", "three_day", "take_profit", "tp_short",
            "nifty3", "excess", "in_lag10", "os_count", "ob_count", "hist_k", "hist_k1"] + [c for c, *_ in defs]
    ev[keep].to_csv(f"{HERE}/event_signals.csv", index=False, float_format="%.6g")

    # ---------------------------------------------------------------- printout
    pd.set_option("display.width", 250, "display.max_columns", 60, "display.max_rows", 200)
    T = S[["code", "signal", "trades", "avg_pct", "avg_net_pct", "tp_avg_pct", "up_pct", "quarters_with_trades",
           "quarters_positive", "first14_pct", "last8_pct", "without_best5_pct", "placebo_avg_pct",
           "res_minus_placebo_pct", "res_minus_placebo_z", "random_avg_pct", "luck_p_two", "holm_p", "bh_q",
           "excess_vs_nifty_pct", "lag10_overlap", "avg_without_lag10_pct", "criteria_met"]].copy()
    T.columns = ["code", "signal", "n", "avg", "net", "tp", "up%", "qT", "q+", "f14", "l8", "-b5", "plac", "r-p",
                 "z", "rand", "p2", "holm", "bh", "xNif", "lag10", "noLag", "crit"]
    log("\nAll returns direction-adjusted (short signals: profit of the short), percent, gross unless 'net'.")
    log(T.round(3).to_string(index=False))
    log("\nVerdicts:")
    for r in S.itertuples():
        log(f"  {r.code} {r.signal:24s} {r.verdict}")
    log(f"\nSignals tested: {len(S)}; Holm < 0.05: {int((S.holm_p < 0.05).sum())}; BH q < 0.10: "
        f"{int((S.bh_q < 0.10).sum())}; nominal p_two < 0.05: {int((S.luck_p_two < 0.05).sum())} "
        f"(expected by chance about {0.05 * len(S):.1f})")
    with open(f"{HERE}/run.log", "w") as fh:
        fh.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
