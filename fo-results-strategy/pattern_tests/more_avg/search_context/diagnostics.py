"""ADDED AFTER diagnostics for C10 (VIX Low). Discovery only (qn 0..13)."""
import numpy as np
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = SP + '/more_avg/search_context'
H, DISC_MAX = 20, 13
F = pd.read_csv(OUT + '/features.csv')
T1 = pd.read_csv(OUT + '/cutpoints.csv').set_index('feature').loc['vix', 't1']
ret = pd.read_csv(SP + '/sector_lab/data/returns.csv', index_col=0)
idx = pd.read_csv(SP + '/sector_lab/data/index_close.csv', index_col=0)
R, N = ret.values, idx['Nifty 50'].values
col = {s: j for j, s in enumerate(ret.columns)}
b = lambda s: s.astype(str).str.lower() == 'true'


def outcome(sym, k, qn):
    assert qn <= DISC_MAX
    hold = np.nan_to_num(R[k + 1:k + H + 1, col[sym]], nan=0.0)
    return ((np.prod(1 + hold) - 1) - (N[k + H] / N[k] - 1)) * 100 - 0.19


Dw = F[(F.qn <= DISC_MAX) & b(F.tradable) & (F.XN > 4)].copy()   # plain winners, discovery
Dw['vsN_net'] = [outcome(s, int(k), int(q)) for s, k, q in zip(Dw.symbol, Dw.i_react, Dw.qn)]
Dw['year'] = Dw.reaction_day.str[:4]
Dw['base'] = Dw.rsi14_cut > 50
D = Dw[Dw.base]


def st(t, name):
    if len(t) == 0:
        return f'{name:48s} n=0'
    qm = t.groupby('qn').vsN_net.mean()
    wo5 = t.vsN_net.sort_values().iloc[:-5].mean() if len(t) > 5 else np.nan
    return (f'{name:48s} n={len(t):3d} avg={t.vsN_net.mean():+6.2f} wo5={wo5:+6.2f} med={t.vsN_net.median():+6.2f} '
            f'q+={int((qm > 0).sum())}/{len(qm)}')


lines = []
C10 = D[D.vix <= T1]
lines.append(st(D, 'baseline'))
lines.append(st(C10, 'C10 VIX<=%.2f' % T1))
for th in [12, 13, 14, 15, 16]:
    lines.append(st(D[D.vix <= th], f'A VIX<={th}'))
lines.append(st(Dw[Dw.vix <= T1], 'A34 plain winners & VIX Low'))
lines.append(st(Dw[Dw.vix > T1], '    plain winners & VIX not Low'))
lines.append(st(C10[C10.year != '2023'], 'C10 excluding 2023 reaction days'))
lines.append(st(D[(D.vix > T1) & (D.year != '2023')], 'baseline VIX>t1 excluding 2023'))
lines.append(st(D[(D.vix > T1) & (D.year == '2023')], 'baseline VIX>t1 in 2023'))
lines.append(st(C10[C10.year == '2023'], 'C10 in 2023'))
lines.append('\nC10 per quarter:')
for q, g in C10.groupby('qn'):
    lines.append(f'  qn {q:2d} {g.quarter.iloc[0]:9s} n={len(g):2d} avg={g.vsN_net.mean():+6.2f} vix {g.vix.min():.1f}-{g.vix.max():.1f} '
                 f'| baseline same qn n={int((D.qn == q).sum())} avg={D[D.qn == q].vsN_net.mean():+6.2f}')
lines.append('\nC10 by year:')
for y, g in C10.groupby('year'):
    lines.append(f'  {y} n={len(g):2d} avg={g.vsN_net.mean():+6.2f} sum={g.vsN_net.sum():+7.1f}')
lines.append('\nbaseline by year (VIX low / not low):')
for y, g in D.groupby('year'):
    lo, hi = g[g.vix <= T1], g[g.vix > T1]
    lines.append(f'  {y} low n={len(lo):2d} avg={lo.vsN_net.mean() if len(lo) else np.nan:+6.2f} | '
                 f'not-low n={len(hi):2d} avg={hi.vsN_net.mean() if len(hi) else np.nan:+6.2f}')
lines.append('\nC10 top 5 trades:')
for r in C10.sort_values('vsN_net', ascending=False).head(5).itertuples():
    lines.append(f'  {r.symbol} {r.reaction_day} vix={r.vix:.1f} vsN_net={r.vsN_net:+.2f}')
# holdout feature-only: how many baseline signals fall under VIX <= t1 per holdout quarter (counts only)
Hs = F[(F.qn > DISC_MAX) & (F.XN > 4) & (F.rsi14_cut > 50)]
lines.append('\nHoldout baseline signals by qn (counts only, no outcomes): VIX<=t1 / all')
for q, g in Hs.groupby('qn'):
    lines.append(f'  qn {q}: {int((g.vix <= T1).sum())} / {len(g)}  (vix range {g.vix.min():.1f}-{g.vix.max():.1f})')
txt = '\n'.join(lines)
print(txt)
open(OUT + '/diagnostics.txt', 'w').write(txt + '\n')
