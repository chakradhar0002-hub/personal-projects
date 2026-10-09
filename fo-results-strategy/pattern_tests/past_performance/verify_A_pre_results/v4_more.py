#!/usr/bin/env python3
"""Verifier extras: dose-response by decile, stock concentration, h2 without qn 14, overlap TR05/TR12/TR03,
selection-adjusted view of the post-hoc strict variants. Writes v4_more.log."""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = open(f'{HERE}/v4_more.log', 'w')
COST = 0.17
rng = np.random.default_rng(99)


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')


F = pd.read_csv(f'{HERE}/my_features.csv.gz')
F = F[F.td.notna()].reset_index(drop=True)
y = F.td.to_numpy()
qn = F.qn.to_numpy()
QM = pd.Series(y).groupby(qn).mean()
exc = y - QM.reindex(qn).to_numpy()
fo = (F.fo == 1).to_numpy()
LAG = fo & (F.vsN21 < -10).to_numpy() & (F.vr >= 1.0).to_numpy()
h1, h2 = qn <= 13, qn >= 14

P('=== dose-response: decile of within-quarter rank (avg gross three_day; excess vs quarter) ===')
for c in ['pq_mean_td4', 'pq_mean_xn4']:
    d = np.ceil(F[c] * 10).clip(1, 10)
    tab = []
    for k in range(1, 11):
        m = (d == k).to_numpy()
        tab.append(f'D{k}: {y[m].mean():+.2f} [{y[m & h1].mean():+.2f} / {y[m & h2].mean():+.2f}]')
    P(f'{c} (all [first14 / last8]):')
    P('   ' + ' | '.join(tab))
P('n_pos_td4 (count of positive windows in last 4):')
for k in range(5):
    m = (F.n_pos_td4 == k).to_numpy()
    P(f'   {k}: n={m.sum():4d} avg {y[m].mean():+.2f} excess {exc[m].mean():+.2f} | first14 {y[m & h1].mean():+.2f} '
      f'({(m & h1).sum()}) | last8 {y[m & h2].mean():+.2f} ({(m & h2).sum()})')

# rank correlation (Spearman) per quarter between the feature and three_day; mean IC and t
for c in ['mean_td4', 'mean_xn4', 'n_pos_td4']:
    ics = []
    for q in np.unique(qn):
        m = (qn == q) & F[c].notna().to_numpy()
        if m.sum() > 20:
            ics.append((q, pd.Series(F[c][m].to_numpy()).corr(pd.Series(y[m]), method='spearman')))
    a = np.array([v for _, v in ics])
    a1 = np.array([v for q, v in ics if q <= 13])
    a2 = np.array([v for q, v in ics if q >= 14])
    P(f'Spearman IC {c}: mean {a.mean():+.3f} t {a.mean() / a.std(ddof=1) * np.sqrt(len(a)):.2f} ({len(a)} q) | '
      f'first14 {a1.mean():+.3f} | last8 {a2.mean():+.3f} (positive {int((a2 > 0).sum())}/{len(a2)})')

P('\n=== last 8 without Results for Jul-Sep 2024 (qn 14, the Oct-Nov 2024 sell-off) ===')
for name, m in [('TR05', F.pq_mean_td4 > 0.8), ('TR12', F.pq_mean_xn4 > 0.8), ('TR03', F.n_pos_td4 >= 3)]:
    m = m.to_numpy()
    for lab, hm in [('qn 14-21', h2), ('qn 15-21', qn >= 15)]:
        mm = m & hm
        P(f'{name} {lab}: n={mm.sum()} avg {y[mm].mean():+.2f} net {y[mm].mean() - COST:+.2f} excess {exc[mm].mean():+.2f} '
          f'(all F&O {y[hm].mean():+.2f})')

P('\n=== overlap ===')
A5, A12, A3 = (F.pq_mean_td4 > 0.8).to_numpy(), (F.pq_mean_xn4 > 0.8).to_numpy(), (F.n_pos_td4 >= 3).to_numpy()
P(f'TR05 & TR12: {(A5 & A12).sum()} of {A5.sum()}; TR05 & TR03: {(A5 & A3).sum()}; TR12 & TR03: {(A12 & A3).sum()}')
P(f'corr(mean_td4, mean_xn4) = {F[["mean_td4", "mean_xn4"]].corr().iloc[0, 1]:.2f}')
for name, m in [('TR05 only (not TR12)', A5 & ~A12), ('TR12 only (not TR05)', A12 & ~A5), ('TR05 & TR12', A5 & A12)]:
    P(f'{name}: n={m.sum()} avg {y[m].mean():+.2f} | first14 {y[m & h1].mean():+.2f} | last8 {y[m & h2].mean():+.2f}')

P('\n=== stock concentration ===')
for name, m in [('TR05', A5), ('TR12', A12), ('TR03', A3), ('TR05 top decile', (F.pq_mean_td4 > 0.9).to_numpy()),
                ('TR03 4 of 4', (F.n_pos_td4 == 4).to_numpy())]:
    d = pd.DataFrame({'s': F.symbol[m], 'e': exc[m], 'y': y[m]})
    agg = d.groupby('s').agg(n=('y', 'size'), sum_exc=('e', 'sum')).sort_values('sum_exc', ascending=False)
    tot = d.e.sum()
    top3 = agg.head(3)
    wo = d[~d.s.isin(top3.index)]
    # equal-weight by stock
    ew = d.groupby('s').e.mean()
    P(f'{name}: {len(agg)} stocks; top 3 by summed excess {list(zip(top3.index, top3.n, top3.sum_exc.round(1)))} = '
      f'{top3.sum_exc.sum() / tot * 100:.0f}% of total excess; without them avg {wo.y.mean():+.2f} (n={len(wo)}); '
      f'stock-equal-weight mean excess {ew.mean():+.2f}, share of stocks with positive mean excess {(ew > 0).mean():.2f}')

P('\n=== selection-adjusted view of post-hoc strict variants (my search) ===')
# I tried these nearby variants for TR05/TR12/TR03; compute the best one's luck p vs the max over all of them
QIDX = {q: np.flatnonzero(qn == q) for q in np.unique(qn)}
VAR = {
    'td4>0.9': F.pq_mean_td4 > 0.9, 'td4>0.85': F.pq_mean_td4 > 0.85, 'td4>0.75': F.pq_mean_td4 > 0.75,
    'td4>0.7': F.pq_mean_td4 > 0.7, 'td4>0.667': F.pq_mean_td4 > 0.6667, 'td4>0.5': F.pq_mean_td4 > 0.5,
    'td3>0.8': F.pq_mean_td3 > 0.8, 'td5>0.8': F.pq_mean_td5 > 0.8, 'tdall>0.8': F.pq_mean_td_all > 0.8,
    'td4>0.8': F.pq_mean_td4 > 0.8, 'xn4>0.8': F.pq_mean_xn4 > 0.8,
    'xn4>0.9': F.pq_mean_xn4 > 0.9, 'xn4>0.85': F.pq_mean_xn4 > 0.85, 'xn4>0.75': F.pq_mean_xn4 > 0.75,
    'xn4>0.7': F.pq_mean_xn4 > 0.7, 'xn4>0.5': F.pq_mean_xn4 > 0.5, 'xn3>0.8': F.pq_mean_xn3 > 0.8,
    'xn5>0.8': F.pq_mean_xn5 > 0.8, 'xnall>0.8': F.pq_mean_xn_all > 0.8,
    'npos4>=3': F.n_pos_td4 >= 3, 'npos4==4': F.n_pos_td4 == 4, 'npos4>=2': F.n_pos_td4 >= 2,
    'npos3>=2': F.n_pos_td3 >= 2, 'npos3==3': F.n_pos_td3 == 3, 'npos5>=4': F.n_pos_td5 >= 4,
    'npos5>=3': F.n_pos_td5 >= 3, 'npos6>=4': F.n_pos_td6 >= 4, 'npos6>=5': F.n_pos_td6 >= 5,
    'shareall>=0.75': F.share_pos_td_all >= 0.75, 'shareall>=0.6': F.share_pos_td_all >= 0.6,
}
names = list(VAR)
MM = np.column_stack([VAR[k].fillna(False).to_numpy(bool) for k in names]).astype(float)
NN = MM.sum(0)
obs = (y @ MM) / NN
B = 20000
perm = np.empty((B, len(names)))
for c0 in range(0, B, 2000):
    Yp = np.empty((2000, len(y)))
    for q, ix in QIDX.items():
        Yp[:, ix] = y[ix][np.argsort(rng.random((2000, len(ix))), axis=1)]
    perm[c0:c0 + 2000] = (Yp @ MM) / NN
mu, sd = perm.mean(0), perm.std(0, ddof=1)
z = (obs - mu) / sd
Zp = (perm - mu) / sd
mx = Zp.max(1)
for k in np.argsort(-z)[:8]:
    raw = (1 + (perm[:, k] >= obs[k]).sum()) / (1 + B)
    adj = (1 + (mx >= z[k]).sum()) / (1 + B)
    P(f'{names[k]:15s} n={int(NN[k]):4d} avg {obs[k]:+.2f} z {z[k]:.2f} raw p {raw:.4f} maxT-adjusted over the '
      f'{len(names)} track-record variants {adj:.4f}')
# would the top decile survive the authors' 33-test Holm if it had been pre-registered? (raw p x 33 bound)
k = names.index('td4>0.9')
raw = (1 + (perm[:, k] >= obs[k]).sum()) / (1 + B)
P(f'td4>0.9 raw p {raw:.5f}; Bonferroni x33 = {min(1, raw * 33):.3f} (hypothetical, it was NOT pre-registered)')

P('\n=== strict variants: halves, per quarter, without best 10, lag overlap ===')
for name, m in [('TR05 top decile (td4>0.9)', (F.pq_mean_td4 > 0.9).to_numpy()),
                ('TR03 4 of 4', (F.n_pos_td4 == 4).to_numpy()),
                ('TR03 3 of 3', (F.n_pos_td3 == 3).to_numpy())]:
    v = y[m]
    s = np.sort(v)[::-1]
    pq = pd.Series(y[m]).groupby(qn[m]).mean()
    pqe = pd.Series(exc[m]).groupby(qn[m]).mean()
    P(f'{name}: n={m.sum()} avg {v.mean():+.2f} net {v.mean() - COST:+.2f} | first14 {y[m & h1].mean():+.2f} '
      f'({(m & h1).sum()}) last8 {y[m & h2].mean():+.2f} ({(m & h2).sum()}) net last8 {y[m & h2].mean() - COST:+.2f} | '
      f'w/o best 5 net {s[5:].mean() - COST:+.2f} w/o best 10 net {s[10:].mean() - COST:+.2f} | q+ (net) '
      f'{int((pq - COST > 0).sum())}/{len(pq)} | q excess>0 {int((pqe > 0).sum())}/{len(pqe)} | lag overlap '
      f'{(m & LAG).sum()} | without lag trades {y[m & ~LAG].mean():+.2f}')
    P('   per qn: ' + ' '.join(f'{q}:{pq[q]:+.1f}({int((m & (qn == q)).sum())})' for q in pq.index))
    yr = pd.to_datetime(F.results_date).dt.year.to_numpy()
    P('   by year: ' + ' | '.join(f'{t}: {y[m & (yr == t)].mean():+.2f} ({(m & (yr == t)).sum()})'
                                  for t in sorted(np.unique(yr[m]))))
