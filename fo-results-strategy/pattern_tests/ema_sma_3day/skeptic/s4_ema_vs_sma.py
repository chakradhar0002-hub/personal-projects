"""Skeptic 4: EMA vs SMA of the same period - same information? Any EMA clearly better?
Also: after-close follow-up (post hoc) and the death-cross binary signals."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from scipy import stats
from common import *

df = load_events()
pairs = [(f'dist_ema_{n}', f'dist_sma_{n}') for n in P] + [(f'slope_ema_{n}', f'slope_sma_{n}') for n in (20, 50, 200)] \
    + [('spread_ema20_50', 'spread_sma20_50'), ('spread_ema50_200', 'spread_sma50_200')]
print('== EMA vs SMA pairs: within-quarter Spearman between them; IC difference (EMA - SMA), paired over 22 quarters, '
      'joint within-quarter shuffle p (B=5000)')
B = 5000
rng = np.random.default_rng(5)
qs = sorted(df.qn.unique())
dsim = np.zeros((B, len(pairs))); dobs = np.zeros(len(pairs))
diffs = {k: [] for k in range(len(pairs))}
for q in qs:
    g = df[df.qn == q]
    ry = zr(g.three_day.values)
    Re = np.column_stack([zr(g[a].values) for a, b in pairs]); Rs = np.column_stack([zr(g[b].values) for a, b in pairs])
    D = Re - Rs
    dobs += ry @ D
    for k in range(len(pairs)):
        diffs[k].append(ry @ D[:, k])
    idx = np.argsort(rng.random((B, len(ry))), axis=1)
    dsim += ry[idx] @ D
dobs /= len(qs); dsim /= len(qs)
mx = np.abs(dsim).max(1)
for k, (a, b) in enumerate(pairs):
    rho = np.mean([stats.spearmanr(g[a], g[b])[0] for _, g in df.groupby('qn')])
    ica = ic_by_q(df, a).mean(); icb = ic_by_q(df, b).mean()
    d = np.array(diffs[k])
    p = (1 + (np.abs(dsim[:, k]) >= abs(dobs[k]) - 1e-12).sum()) / (1 + B)
    pm = (1 + (mx >= abs(dobs[k]) - 1e-12).sum()) / (1 + B)
    print(f'  {a:17s} vs {b:17s} rank corr {rho:.3f} | IC {ica:+.3f} vs {icb:+.3f}, diff {dobs[k]:+.3f} '
          f'(EMA "better" = more extreme in the IC direction in {int((np.sign(ica) * d > 0).sum())}/22 q) p {fpv(p)} maxT({len(pairs)}) {fpv(pm)}')

bp = [(f'above_ema_{n}', f'above_sma_{n}') for n in (20, 50, 200)] + [('state_ema20_50', 'state_sma20_50'), ('state_ema50_200', 'state_sma50_200'),
      ('xup_ema20_50', 'xup_sma20_50'), ('xdn_ema20_50', 'xdn_sma20_50'), ('xup_ema50_200', 'xup_sma50_200'), ('xdn_ema50_200', 'xdn_sma50_200'),
      ('pxup_ema20', 'pxup_sma20'), ('pxdn_ema20', 'pxdn_sma20'), ('bull_stack_ema', 'bull_stack_sma'), ('bear_stack_ema', 'bear_stack_sma')]
print('\n== binary EMA vs SMA: agreement and excess difference')
df['ex'] = df.three_day - df.groupby('qn').three_day.transform('mean')
for a, b in bp:
    agree = (df[a] == df[b]).mean()
    both = ((df[a] == 1) & (df[b] == 1)).sum()
    jacc = both / ((df[a] == 1) | (df[b] == 1)).sum()
    ea = df.loc[df[a] == 1, 'ex'].mean(); eb = df.loc[df[b] == 1, 'ex'].mean()
    oa = df.loc[(df[a] == 1) & (df[b] == 0), 'ex']; ob = df.loc[(df[a] == 0) & (df[b] == 1), 'ex']
    print(f'  {a:15s} vs {b:15s} same value {agree:.1%}, overlap (Jaccard) {jacc:.2f} | excess {ea:+.2f} vs {eb:+.2f}; '
          f'EMA-only n {len(oa)} {oa.mean():+.2f} vs SMA-only n {len(ob)} {ob.mean():+.2f} (Welch p {stats.ttest_ind(oa, ob, equal_var=False).pvalue if len(oa) > 2 and len(ob) > 2 else np.nan:.3f})')

print('\n== post-hoc: after-close subgroup (not pre-registered)')
df['y_dd'] = df.three_day - df.groupby('i_cut').three_day.transform('mean')
ac = df[df.timing == 'After close']
for f in ['slope_sma_50', 'dist_sma_100', 'slope_ema_50', 'dist_ema_50', 'dist_sma_20']:
    parts = []
    for name, d, y in [('raw', ac, 'three_day'), ('xs_nifty', ac, 'xs_nifty'), ('date_dm(all results)', ac, 'y_dd'),
                       ('q0-13', ac[ac.qn <= 13], 'three_day'), ('q14-21', ac[ac.qn >= 14], 'three_day'),
                       ('q0-13 dm', ac[ac.qn <= 13], 'y_dd'), ('q14-21 dm', ac[ac.qn >= 14], 'y_dd')]:
        m, p, _ = perm_ic(d, f, y, B=2000)
        parts.append(f'{name} {m:+.3f} (p {fpv(p)})')
    print(f'  {f:14s} ' + ' | '.join(parts))
# how many timing x feature cells were effectively looked at, and the max |t|
ts = []
for tname in ['After close', 'During market', 'Non-trading day']:
    d = df[df.timing == tname]
    for f in CONT:
        ics = ic_by_q(d, f)
        ts.append((tname, f, summ(ics)[1], ics.mean()))
ts = pd.DataFrame(ts, columns=['timing', 'f', 't', 'ic'])
print('  27 features x 3 timing groups: |t| >= 2.0 in', (ts.t.abs() >= 2).sum(), 'of', len(ts), '; largest:')
print(ts.reindex(ts.t.abs().sort_values(ascending=False).index).head(6).to_string(index=False))
# joint shuffle maxT over 27 features within the after-close subgroup
B = 5000
rng = np.random.default_rng(11)
s = np.zeros((B, 27)); o = np.zeros(27); nq = 0
for q, g in ac.groupby('qn'):
    R = np.column_stack([zr(g[f].values) for f in CONT]); ry = zr(g.three_day.values)
    o += ry @ R
    idx = np.argsort(rng.random((B, len(ry))), axis=1); s += ry[idx] @ R; nq += 1
o /= nq; s /= nq
mx = np.abs(s).max(1)
j = CONT.index('slope_sma_50')
print(f'  after-close slope_sma_50 maxT27 p {(1 + (mx >= abs(o[j])).sum()) / (1 + B):.4f}; x3 timing groups (Bonferroni) '
      f'{min(1, 3 * (1 + (mx >= abs(o[j])).sum()) / (1 + B)):.3f}')

print('\n== death-cross signals (small n)')
for f in ['xdn_sma50_200', 'xdn_ema50_200']:
    d = df[df[f] == 1].sort_values('ex', ascending=False)
    print(f'  {f}: n {len(d)}, excess {d.ex.mean():+.2f}, median {d.ex.median():+.2f}, drop best 1 {d.ex.iloc[1:].mean():+.2f}, '
          f'drop best 3 {d.ex.iloc[3:].mean():+.2f}; lag trades among them {int(d.lag_trade.sum())}; '
          f'distinct symbols {d.symbol.nunique()}; excess vs Nifty {d.xs_nifty.mean() - df.xs_nifty.mean():+.2f}')
    print('    top 3:', ', '.join(f'{r.symbol} q{r.qn} {r.three_day:+.1f}' for r in d.head(3).itertuples()))
