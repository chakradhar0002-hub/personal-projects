"""Independent re-computation of a few pre-registered combos + POST-HOC diagnostics (NOT pre-registered, not counted
in the family, never used for the pass / fail decision).

    python3 verify_and_posthoc.py   -> out/verify_posthoc_log.txt

Part 1 (verification): rebuilds 1D, 1F, 3B, 7P, 9C with plain pandas directly from the panels (no combos.py), compares
  trade counts and averages with out/summary.csv, and re-does the 1D luck test with direct random same-size per-quarter
  draws (independent RNG) instead of the permutation matrix.
Part 2 (post-hoc, about the only family with nominal hits, "quality on a dip" with QB):
  (a) inside RSI14 < 30 results: QB vs not-QB, within-quarter label permutation p (does the fundamental part add?);
  (b) 1D split by the lag-10% + volume rule and by lag < -10% at any volume;
  (c) 1D per quarter;  (d) 1D without the lag-rule trades: luck vs random picks from non-lag results;
  (e) decomposition of QB: RSI14 < 30 & no loss in 4q only; RSI14 < 30 & PAT up YoY only;
  (f) lag rule (85) split by QB.
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(HERE, "out")
REPO = os.environ.get('REPO_ROOT', '.') + ""
LOG = open(f"{OUT}/verify_posthoc_log.txt", "w")
rng = np.random.default_rng(777)


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.write(s + "\n")


ta = pd.read_csv(f"{SP}/ta/build/events_ta.csv")
ta = ta[(ta.in_fo == True) & ta.three_day.notna()]
fa = pd.read_csv(f"{SP}/fa/build/fa_panel.csv")[["symbol", "quarter", "roe_pct", "debt_equity", "loss_any_4q", "pe",
                                                 "pe_vs_peers_pct", "l1_sales_yoy_pct", "l1_ebitda_margin_chg_yoy_pp"]]
ex = pd.read_csv(f"{SP}/fa/A_pre_results/out/extra_features.csv")[["symbol", "quarter", "pat_l1", "pat_l5"]]
x = ta.merge(fa, on=["symbol", "quarter"]).merge(ex, on=["symbol", "quarter"])
lag = pd.read_csv(f"{REPO}/results/lag10_volume/trades.csv")
x["lagrule"] = x.set_index(["symbol", "cutoff"]).index.isin(list(zip(lag.symbol, lag.cutoff)))
S = pd.read_csv(f"{OUT}/summary.csv").set_index("id")

QB = (x.loss_any_4q == 0) & (x.pat_l1 > x.pat_l5)
osc = ((x.rsi14 < 30).astype(int) + (x.stoch_k14 < 20) + (x.bb_pctb < 0) + (x.cci20 < -100) + (x.mfi14 < 20)
       + (x.willr14 < -80))
G = (x.pat_l5 > 0) & (x.pat_l1 / x.pat_l5 > 1.2) & (x.l1_sales_yoy_pct > 10)
mom = (x.close_vs_sma50_pct > 0) & (x.close_vs_sma200_pct > 0) & (x.dist_52w_high_pct >= -10) & (x.vol_ratio_5_60 >= 1)
fg = ((x.loss_any_4q == 0).astype(int) + (x.pat_l1 > x.pat_l5) + (x.l1_sales_yoy_pct > 10)
      + (x.l1_ebitda_margin_chg_yoy_pp > 0) + (x.pe_vs_peers_pct < 0))
tg = ((x.close_vs_sma200_pct > 0).astype(int) + (x.close_vs_sma50_pct > 0) + (x.macd_pct > x.macd_signal_pct)
      + (x.rsi14 > 50) + (x.obv_slope20 > 0))
chk = {"1D": (QB & (x.rsi14 < 30), +1), "1F": (QB & (osc >= 3), +1), "3B": (G & mom, +1),
       "7P": (((x.pe > 50) | (x.pe_vs_peers_pct > 25)) & (x.rsi14 > 70), -1), "9C": ((fg >= 4) & (tg >= 4), +1)}
log("PART 1 - independent recomputation vs out/summary.csv")
for k, (m, sg) in chk.items():
    a = sg * x.three_day[m].mean()
    log(f"  {k}: n {m.sum()} vs {int(S.loc[k, 'trades'])}; avg {a:+.4f} vs {S.loc[k, 'avg_pct']:+.4f}")


def luck(m, y, pool_mask, R=20000):
    """two-sided p of mean(y[m]) vs random same-size per-quarter picks from pool_mask rows of the same quarter."""
    sim = np.zeros(R)
    K = m.sum()
    exp = 0.0
    for q in np.unique(x.qn[m]):
        k = int((m & (x.qn == q)).sum())
        pool = y[(pool_mask & (x.qn == q)).to_numpy()]
        exp += k * pool.mean()
        keys = rng.random((R, len(pool)))
        idx = np.argpartition(keys, k - 1, axis=1)[:, :k]
        sim += pool[idx].sum(1)
    sim /= K
    exp /= K
    obs = y[m.to_numpy()].mean()
    return obs, exp, (1 + (np.abs(sim - exp) >= abs(obs - exp) - 1e-12).sum()) / (R + 1)


y = x.three_day.to_numpy()
allm = pd.Series(True, index=x.index)
o, e, p = luck(chk["1D"][0], y, allm)
log(f"  1D direct random-draw luck: avg {o:+.3f}, random expectation {e:+.3f}, p_two {p:.4f} "
    f"(permutation run: {S.loc['1D', 'p_two']:.4f})")

log("\nPART 2 - POST-HOC diagnostics (not pre-registered; not counted; descriptive only)")
r30 = x.rsi14 < 30
sub = x[r30].copy()
lab = QB[r30].to_numpy()
yy = sub.three_day.to_numpy()
qq = sub.qn.to_numpy()
d_obs = yy[lab].mean() - yy[~lab].mean()
R = 20000
dist = np.empty(R)
for i in range(R):
    L = lab.copy()
    for q in np.unique(qq):
        g = np.flatnonzero(qq == q)
        L[g] = L[rng.permutation(g)]
    dist[i] = yy[L].mean() - yy[~L].mean()
pp = (1 + (np.abs(dist) >= abs(d_obs) - 1e-12).sum()) / (R + 1)
log(f"(a) inside RSI14<30 results (n {r30.sum()}): QB {lab.sum()} trades {yy[lab].mean():+.3f} vs not-QB {(~lab).sum()} "
    f"{yy[~lab].mean():+.3f}; diff {d_obs:+.3f}, within-quarter label permutation p_two {pp:.4f}")
for h, mm in (("first 14", qq <= 13), ("last 8", qq >= 14)):
    log(f"     {h}: QB {yy[lab & mm].mean():+.3f} (n {(lab & mm).sum()}) vs not-QB {yy[~lab & mm].mean():+.3f} "
        f"(n {(~lab & mm).sum()})")
m1 = chk["1D"][0]
d = x[m1]
log(f"(b) 1D in the lag-10%+volume rule: {d.lagrule.sum()} trades avg {d.three_day[d.lagrule].mean():+.3f}; "
    f"not in it: {(~d.lagrule).sum()} avg {d.three_day[~d.lagrule].mean():+.3f}")
lg = d.lag_pct < -10
log(f"    1D with lag < -10% (any volume): {lg.sum()} avg {d.three_day[lg].mean():+.3f}; lag >= -10%: {(~lg).sum()} "
    f"avg {d.three_day[~lg].mean():+.3f}")
pq = d.groupby("qn").three_day.agg(["size", "mean"]).round(2)
log("(c) 1D per quarter (qn: trades, avg):", "; ".join(f"{q}: {int(r['size'])}, {r['mean']:+.2f}" for q, r in pq.iterrows()))
nl = ~x.lagrule
o, e, p = luck(m1 & nl, y, nl)
log(f"(d) 1D without lag-rule trades: n {(m1 & nl).sum()}, avg {o:+.3f}, random (non-lag results, same quarters) "
    f"{e:+.3f}, p_two {p:.4f}; without best 5: {np.sort(y[(m1 & nl).to_numpy()])[:-5].mean():+.3f}")
for nm, mm in (("RSI14<30 & no loss 4q", r30 & (x.loss_any_4q == 0)), ("RSI14<30 & PAT up YoY", r30 & (x.pat_l1 > x.pat_l5)),
               ("RSI14<30 & QA (ROE>15,D/E<0.5)", r30 & (x.roe_pct > 15) & (x.debt_equity < 0.5)),
               ("RSI14<30 alone", r30)):
    log(f"(e) {nm}: n {mm.sum()}, avg {x.three_day[mm].mean():+.3f}")
L = x[x.lagrule]
qbl = QB[x.lagrule]
log(f"(f) lag rule (85) with QB: {qbl.sum()} trades avg {L.three_day[qbl].mean():+.3f}; without QB: {(~qbl).sum()} avg "
    f"{L.three_day[~qbl].mean():+.3f}")
LOG.close()
