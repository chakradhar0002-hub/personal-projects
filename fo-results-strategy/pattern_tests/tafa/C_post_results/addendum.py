#!/usr/bin/env python3
"""ADDED AFTER the main run had been looked at (disclosed; counted; cannot rescue any verdict).

X1  Diagnostics of the only WATCH (W_RSI_HI, H20): per-quarter difference vs the plain winners, RSI(14) bands among
    the plain winners (is it monotonic?), overlap with UP200, without-best-5 comparison against the plain winners
    trimmed the same way, and the result without qn 18-21 (most recent, most winners).
X2  Post-hoc lead seen in the references: BREAKOUT_VOL alone (any numbers) after results earned about what the plain
    winners earn, on more trades, while the same signal on quiet days earned little. 3 extra tests (H5/10/20, luck vs
    all results of the quarter, 20,000 draws) + its overlap with the plain winners and the part outside them.
    Holm over 117 + 3 = 120.
Reads trades.csv / results_tests.csv / placebo.csv / features.csv from this folder only.
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = open(f'{HERE}/addendum.log', 'w')
rng = np.random.default_rng(20261010)


def P_(s=''):
    print(s)
    LOG.write(str(s) + '\n')
    LOG.flush()


t = pd.read_csv(f'{HERE}/trades.csv')
fe = pd.read_csv(f'{HERE}/features.csv')[['symbol', 'qn', 'cut_rsi14', 'cut_close_vs_sma200_pct']]
t = t.merge(fe, on=['symbol', 'qn'], validate='1:1')
res = pd.read_csv(f'{HERE}/results_tests.csv')
for H in (5, 10, 20):
    t[f'v{H}'] = t[f'raw_H{H}'] - t[f'nifty_H{H}'] - 0.19
W = t.W.astype(bool)
w = t[W].copy()
pd.set_option('display.width', 220)

# ---------------- X1
P_('X1  W_RSI_HI diagnostics (H20, vsN net, percent)')
wq = w.groupby('qn').v20.mean()
hi = w[w.cut_rsi14 > 50]
lo = w[w.cut_rsi14 < 50]
pq = pd.DataFrame({'n_W': w.groupby('qn').size(), 'W_mean': wq, 'n_hi': hi.groupby('qn').size(),
                   'hi_mean': hi.groupby('qn').v20.mean(), 'n_lo': lo.groupby('qn').size(),
                   'lo_mean': lo.groupby('qn').v20.mean()})
pq['hi_minus_W'] = pq.hi_mean - pq.W_mean
P_(pq.round(2).to_string())
P_(f"quarters hi > W: {(pq.hi_minus_W > 0).sum()}/{pq.hi_minus_W.notna().sum()}; hi > lo: "
   f"{(pq.hi_mean > pq.lo_mean).sum()}/{(pq.hi_mean.notna() & pq.lo_mean.notna()).sum()}")
bands = pd.cut(w.cut_rsi14, [0, 30, 40, 50, 60, 70, 100])
P_('\nplain winners by cutoff RSI(14) band, H5/H10/H20 vsN net:')
P_(w.groupby(bands, observed=True)[['v5', 'v10', 'v20']].agg(['count', 'mean']).round(2).to_string())
P_(f"\noverlap: RSI_HI winners {len(hi)}, of which UP200 {int((hi.cut_close_vs_sma200_pct > 0).sum())}; "
   f"UP200 & RSI_HI {int(((w.cut_close_vs_sma200_pct > 0) & (w.cut_rsi14 > 50)).sum())}, "
   f"UP200 & RSI_LO {int(((w.cut_close_vs_sma200_pct > 0) & (w.cut_rsi14 < 50)).sum())}")
for nm, d in [('UP200 & RSI_HI', w[(w.cut_close_vs_sma200_pct > 0) & (w.cut_rsi14 > 50)]),
              ('UP200 & RSI_LO', w[(w.cut_close_vs_sma200_pct > 0) & (w.cut_rsi14 < 50)]),
              ('DN200 & RSI_HI', w[(w.cut_close_vs_sma200_pct < 0) & (w.cut_rsi14 > 50)]),
              ('DN200 & RSI_LO', w[(w.cut_close_vs_sma200_pct < 0) & (w.cut_rsi14 < 50)])]:
    P_(f'  winners {nm}: n {len(d)}, H20 vsN net {d.v20.mean():+.2f}')
P_(f"\nwithout best 5: RSI_HI {np.sort(hi.v20)[:-5].mean():+.2f} vs all plain winners without their best 5 "
   f"{np.sort(w.v20)[:-5].mean():+.2f}; median RSI_HI {hi.v20.median():+.2f} vs winners {w.v20.median():+.2f}")
old = w.qn <= 17
P_(f"qn 0-17 only: RSI_HI {hi[hi.qn <= 17].v20.mean():+.2f} (n {int((hi.qn <= 17).sum())}) vs winners "
   f"{w[old].v20.mean():+.2f} (n {int(old.sum())});  qn 18-21: RSI_HI {hi[hi.qn >= 18].v20.mean():+.2f} vs winners "
   f"{w[~old].v20.mean():+.2f}")
r = res[(res.test == 'W_RSI_HI') & (res.H == 20)].iloc[0]
P_(f"main run: n {r.n}, vsN net {r.vsN_net:+.2f}, dW {r.dW:+.2f} (first14 {r.dW_first14:+.2f}, last8 {r.dW_last8:+.2f}), "
   f"t {r.t_dW_q:.2f}, luck p {r.p_W_ELIG:.4f}, Holm(117) {r.p_holm117:.2f}, Westfall-Young {r.p_westfall_young:.2f}")
pl = pd.read_csv(f'{HERE}/placebo.csv')
x = pl[(pl.test == 'W_RSI_HI') & (pl.H == 20)].iloc[0]
P_(f"quiet-day winners with RSI_HI: d vs all quiet-day winners {x.placebo_d_vs_all_quiet_winners:+.2f} "
   f"(se {x.se_d:.2f}) - the split goes the other way on ordinary days")

# ---------------- X2
P_('\nX2  BREAKOUT_VOL alone after results (post hoc), long, vs all results of the quarter')
B = t.BREAKOUT_VOL.astype(bool)
QN = t.qn.to_numpy()
rows = []
for H in (5, 10, 20):
    v = t[f'v{H}'].to_numpy()
    si = np.where(B)[0]
    tot = np.zeros(20000)
    for q in np.unique(QN[si]):
        k = int((QN[si] == q).sum())
        pool = np.where(QN == q)[0]
        pick = np.argpartition(rng.random((20000, len(pool))), k - 1, axis=1)[:, :k]
        tot += v[pool][pick].sum(1)
    tot /= len(si)
    x = v[si]
    qm = pd.Series(x).groupby(QN[si]).mean()
    fh = QN[si] <= 13
    nb = B & ~W
    rows.append(dict(test='X2_BREAKOUT_VOL', H=H, n=len(si), vsN_net=x.mean(), q_pos=f'{(qm > 0).sum()}/{len(qm)}',
                     t_q=qm.mean() / (qm.std() / np.sqrt(len(qm))), first14=x[fh].mean(), last8=x[~fh].mean(),
                     wo_best5=np.sort(x)[:-5].mean(), in_W=int((B & W).sum()), not_W_n=int(nb.sum()),
                     not_W_mean=t.loc[nb, f'v{H}'].mean(), W_not_breakout_n=int((W & ~B).sum()),
                     W_not_breakout_mean=t.loc[W & ~B, f'v{H}'].mean(),
                     p_luck=(1 + (tot >= x.mean()).sum()) / 20001))
x2 = pd.DataFrame(rows)
allp = np.r_[res.p_primary.to_numpy(), x2.p_luck.to_numpy()]
o = np.argsort(allp)
adj = np.empty(len(allp))
run = 0
for i, j in enumerate(o):
    run = max(run, (len(allp) - i) * allp[j])
    adj[j] = min(1, run)
x2['p_holm120'] = adj[-3:]
P_(x2.round(3).to_string(index=False))
P_(f'Holm over 120: min adjusted among the 117 main tests {adj[:-3].min():.3f}')
pq2 = pl[(pl.test == 'P1_GOOD_BREAKOUT_VOL') & (pl.placebo == 'TA_only')][['H', 'n', 'placebo_vsN_net', 'se_month']]
P_('same BREAKOUT_VOL signal on quiet days (from placebo.csv):')
P_(pq2.round(3).to_string(index=False))
x2.to_csv(f'{HERE}/addendum_x2.csv', index=False, float_format='%.4f')
