"""Global multiplicity across both builds: count every test, replace the small p values with precise ones, Holm (and
BH for reference) over the whole set. Plus index-member persistence halves."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from sk_common import *
HERE = SKOUT
ev, allev, qq = load()
Q, N = qq.Q.to_numpy(), qq.N.to_numpy()
rng = np.random.default_rng(20261103)

def perm_corr(a, b, B=2_000_000, CH=50000, sp=False):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if sp: a, b = rk(a), rk(b)
    az = (a - a.mean()) / a.std(); bz = (b - b.mean()) / b.std()
    r = (az * bz).mean()
    lo = hi = 0
    for b0 in range(0, B, CH):
        P_ = np.argsort(rng.random((CH, len(a))), axis=1)
        s = (bz[P_] * az).mean(1)
        lo += np.sum(s <= r + 1e-12); hi += np.sum(s >= r - 1e-12)
    return r, min(1, 2 * min((1 + lo) / (B + 1), (1 + hi) / (B + 1)))

prec = {}
for nm, a, b, sp in (('Q vs N P', Q, N, False), ('Q vs N S', Q, N, True),
                     ('Q vs season P', Q, qq.nifty_season, False), ('Q vs season S', Q, qq.nifty_season, True)):
    r, p = perm_corr(a, b, sp=sp)
    prec[nm] = p
    print(f'{nm}: r {r:+.3f}, p (2,000,000 shuffles) {p:.6f}')

qt = pd.read_csv(f'{QC}/q_tests.csv')
st = pd.read_csv(f'{QC}/s_tests.csv')
print('q_tests columns:', list(qt.columns))
print(f'quarter build tests: {len(qt)}; sector build tests: {len(st)} rows, of which {st.id.str.startswith("3p").sum()} listed pairs')
pairs = pd.read_csv(f'{HERE}/sk2_pairs.csv')
print(f'sector pairs searched (78 NSE + 78 custom): {len(pairs)}')
sk3 = pd.read_csv(f'{HERE}/sk3_stock.csv')

rows = []
pcol = 'p' if 'p' in qt.columns else [c for c in qt.columns if c.startswith('p')][0]
for _, r in qt.iterrows():
    nm = str(r.get('test', r.iloc[1]))
    p = r[pcol]
    key = None
    if 'Nifty 50 three-day' in nm and nm.startswith('Q'):
        key = 'Q vs N P' if 'Pearson' in nm else 'Q vs N S'
    if 'over the season' in nm and nm.startswith('Q'):
        key = 'Q vs season P' if 'Pearson' in nm else 'Q vs season S'
    if key: p = prec[key]
    rows.append(dict(build='q', test=nm, p=p))
for _, r in st.iterrows():
    if r.id.startswith('3p'): continue
    p = r.p
    if r.id == '5k': p = float(sk3.loc[sk3.rule == 'last-4 top tenth (post hoc)', 'p'].iloc[0])
    if r.id == '5j': p = float(sk3.loc[sk3.rule.str.startswith('last-4 top fifth'), 'p'].iloc[0])
    rows.append(dict(build='s', test=f'{r.id} {r.test}', p=p))
for _, r in pairs.iterrows():
    rows.append(dict(build='s-pair', test=f'{r.labels} {r.pair}', p=r.p_pair))
G = pd.DataFrame(rows)
G['holm_global'] = holm(G.p.to_numpy())
o = np.argsort(G.p.to_numpy()); m = len(G)
bh = np.empty(m); run = 1.0
for k in range(m - 1, -1, -1):
    i = o[k]; run = min(run, G.p.iloc[i] * m / (k + 1)); bh[i] = run
G['bh_global'] = bh
print(f'\nall tests across both builds: {m} (53 quarter-level + {len(st) - st.id.str.startswith("3p").sum()} sector/stock + {len(pairs)} pairs)')
print(G.sort_values('p').head(15).to_string(index=False))
print('\nwithout the 140 unlisted pairs (104 tests):')
G2 = G[(G.build != 's-pair') | G.test.isin([f'{a} {b}' for a, b in []])].copy()
listed = set()
for _, r in st[st.id.str.startswith('3p')].iterrows():
    t = r.test.replace('NSE: r(', 'NSE ').replace('custom: r(', 'custom ').rstrip(')').replace(', ', ' / ')
    listed.add(t)
G2 = G[(G.build != 's-pair') | G.test.isin(listed)].copy()
G2['holm'] = holm(G2.p.to_numpy())
print(len(G2), 'tests'); print(G2.sort_values('p').head(10).to_string(index=False))
G.to_csv(f'{HERE}/sk4_global.csv', index=False)

# index-member persistence (item 4) halves
im = pd.read_csv(f'{REPO}/results/nifty_sector_3day/index_member_results.csv')
im = im[im['group'] == 'sectoral'] if 'group' in im.columns else im
c = im.groupby(['index', 'qn']).excess_vs_index.agg(['mean', 'size']).reset_index()
c = c[c['size'] >= 4]
P_ = c.pivot(index='qn', columns='index', values='mean') * 100
rh = []
for t in range(21):
    a, b = P_.loc[t], P_.loc[t + 1] if t + 1 in P_.index else None
    m_ = a.notna() & b.notna()
    rh.append(spear(a[m_], b[m_]))
rh = np.array(rh)
print(f'\nindex members, lag-1 Spearman of mean excess vs own index: all {rh.mean():+.3f} (build 4a -0.11); '
      f't=0..9 {rh[:10].mean():+.3f}; t=11..20 {rh[11:].mean():+.3f}; per pair {np.round(rh, 2).tolist()}')
