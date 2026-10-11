#!/usr/bin/env python3
"""Verifier, own code: data checks.
 1. my two raw sources agree (my_fo.db vs w_fo.db on the 15 cross-validation days);
 2. the study's compact DB (oi/downloads/fo_compact.db) vs my raw re-download, every (day, raw ticker);
 3. >= 40 (symbol, day) points behind the candidates (B09, B13, A12; plus B09-OUT winners): raw values and the
    study's stored features vs mine;
 4. all 3,280 results rows: the study's features vs mine (agreement rates), and the candidate flags.
usage: python3 w2_datacheck.py <scratchpad> <verify_dir>
"""
import sqlite3
import sys

import numpy as np
import pandas as pd

SP, VD = sys.argv[1], sys.argv[2]
OI = f'{SP}/more_signals/oi'
LOG = open(f'{VD}/work/w2_datacheck.log', 'w')
pd.set_option('display.width', 250)
pd.set_option('display.max_columns', 40)


def log(*a):
    s = ' '.join(map(str, a))
    print(s, flush=True)
    LOG.write(s + '\n')
    LOG.flush()


A = sqlite3.connect(f'{VD}/downloads/my_fo.db')
B = sqlite3.connect(f'{VD}/downloads/w_fo.db')
TH = sqlite3.connect(f'file:{OI}/downloads/fo_compact.db?mode=ro', uri=True)

# ------------------------------------------------------------ 1. my_fo vs w_fo on overlap days
xd = [r[0] for r in B.execute('SELECT day FROM wdone WHERE ok=1 AND day <= "2023-04-10"')]
log('1. cross-validation days in both of my sources:', len(xd), xd)
tot = {}
for tv, tw, keys in (('vfut', 'wfut', ['day', 'sym', 'expiry']), ('vopt', 'wopt', ['day', 'sym']),
                     ('vund', 'wund', ['day', 'sym']), ('vatm', 'watm', ['day', 'sym', 'expiry', 'strike', 'otype'])):
    q = ','.join(f'"{d}"' for d in xd)
    a = pd.read_sql(f'SELECT * FROM {tv} WHERE day IN ({q})', A)
    b = pd.read_sql(f'SELECT * FROM {tw} WHERE day IN ({q})', B)
    m = a.merge(b, on=keys, how='outer', suffixes=('_v', '_w'), indicator=True)
    num = [c[:-2] for c in m.columns if c.endswith('_v') and pd.api.types.is_numeric_dtype(m[c])]
    bad = {c: int((~np.isclose(m[c + '_v'], m[c + '_w'], rtol=1e-9, equal_nan=True))[m._merge == 'both'].sum())
           for c in num}
    log(f'   {tv}: rows v {len(a)} w {len(b)} matched {int((m._merge == "both").sum())} '
        f'only-v {int((m._merge == "left_only").sum())} only-w {int((m._merge == "right_only").sum())} mismatches {bad}')

# ------------------------------------------------------------ 2. study DB vs my raw, all days
done = {r[0]: r[1] for r in B.execute('SELECT day, ok FROM wdone')}


def mine(tv, tw):
    a = pd.read_sql(f'SELECT * FROM {tv}', A)
    b = pd.read_sql(f'SELECT * FROM {tw}', B)
    a = a[~a.day.isin([d for d, o in done.items() if o == 1])]
    return pd.concat([a, b], ignore_index=True)


mf = mine('vfut', 'wfut')
mo = mine('vopt', 'wopt')
mu = mine('vund', 'wund')
log('\n2. study compact DB vs my raw download (raw tickers, all fetched days)')
tf = pd.read_sql('SELECT day, sym, oi_tot, chg_oi_tot, e1, e1_settle, e1_oi, e2, e2_settle, und FROM fut', TH)
to = pd.read_sql('SELECT day, sym, ce_oi, pe_oi, ce_ctr, pe_ctr FROM opt', TH)
log(f'   study days fut {tf.day.nunique()} / my days {mf.day.nunique()}')
g = mf.groupby(['day', 'sym']).agg(oi=('oi', 'sum'), chg=('chg', 'sum')).reset_index()
mf = mf.sort_values(['day', 'sym', 'expiry'])
mf['rk'] = mf.groupby(['day', 'sym']).cumcount()
n1 = mf[mf.rk == 0][['day', 'sym', 'expiry', 'settle', 'oi']].rename(columns={'expiry': 'x1', 'settle': 's1', 'oi': 'o1'})
n2 = mf[mf.rk == 1][['day', 'sym', 'expiry', 'settle']].rename(columns={'expiry': 'x2', 'settle': 's2'})
g = g.merge(n1, on=['day', 'sym'], how='left').merge(n2, on=['day', 'sym'], how='left').merge(
    mu[['day', 'sym', 'und']].rename(columns={'und': 'und_m'}), on=['day', 'sym'], how='left')
c = tf.merge(g, on=['day', 'sym'], how='outer', indicator=True)
log('   fut (day, ticker) rows:', c._merge.value_counts().to_dict())
cb = c[c._merge == 'both']
for x, y in (('oi_tot', 'oi'), ('chg_oi_tot', 'chg'), ('e1_settle', 's1'), ('e1_oi', 'o1'), ('e2_settle', 's2'),
             ('und', 'und_m')):
    ok = np.isclose(cb[x], cb[y], rtol=1e-9, atol=1e-9, equal_nan=True)
    log(f'   {x:10s} vs mine: rows {len(cb)}, mismatches {int((~ok).sum())}')
    if (~ok).sum():
        log(cb.loc[~ok, ['day', 'sym', x, y]].head(8).to_string(index=False))
log('   expiry e1 equal', float((cb.e1 == cb.x1).mean()), '; e2 equal', float((cb.e2.fillna('') == cb.x2.fillna('')).mean()))
c = to.merge(mo, on=['day', 'sym'], how='outer', suffixes=('_t', '_m'), indicator=True)
log('   opt (day, ticker) rows:', c._merge.value_counts().to_dict())
cb = c[c._merge == 'both']
for x in ('ce_oi', 'pe_oi', 'ce_ctr', 'pe_ctr'):
    ok = np.isclose(cb[x + '_t'], cb[x + '_m'], rtol=1e-9, equal_nan=True)
    log(f'   {x:6s}: mismatches {int((~ok).sum())} of {len(cb)}')
miss = sorted(set(tf.day) ^ set(g.day))
log('   days in one source only:', miss[:10])
log('   2021-03-30 in sessions:', '2021-03-30' in set(pd.read_csv(f'{SP}/sector_lab/data/sessions.csv').day),
    '| my fetch status:', done.get('2021-03-30'))

# ------------------------------------------------------------ 3. sample points behind the candidates
ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv').day.to_numpy()
th = pd.read_csv(f'{OI}/work/results_features.csv')
mi = pd.read_csv(f'{VD}/work/w_results_features.csv')
D = th.merge(mi, on=['symbol', 'qn'], suffixes=('_t', ''))
rng = np.random.default_rng(99)
pts = []
for t, n_, dcol, feats in (('B09', 20, 'i_react', ['B_PCR']), ('B13', 10, 'i_react', ['B_dCIV20']),
                           ('A12', 10, 'i_cut', ['A_BASISDEV', 'A_BASIS'])):
    sel = D[D[t] & (D.W if t[0] == 'B' else True)] if t[0] == 'B' else D[D[t]]
    sel = sel.iloc[rng.choice(len(sel), n_, replace=False)]
    for _, r in sel.iterrows():
        pts.append((t, r.symbol, r.qn, int(r[dcol]), feats))
outW = D[D.W & D.el_B09 & ~D.B09]
for _, r in outW.iloc[rng.choice(len(outW), 6, replace=False)].iterrows():
    pts.append(('B09-OUT', r.symbol, r.qn, int(r.i_react), ['B_PCR']))
dd = np.load(f'{VD}/work/w_daily.npz')
SY = list(dd['syms'])
rows = []
for t, s, q, i, feats in pts:
    j = SY.index(s)
    r = D[(D.symbol == s) & (D.qn == q)].iloc[0]
    row = {'cand': t, 'symbol': s, 'qn': q, 'day': ses[i], 'my_CE_OI': dd['CE'][i, j], 'my_PE_OI': dd['PE'][i, j],
           'my_futOI': dd['OIA'][i, j], 'my_und': dd['UND'][i, j]}
    for f in feats:
        row[f + '_study'] = r[f + '_t']
        row[f + '_mine'] = r[f]
    if t == 'B13':
        row['my_CIV_k'] = dd['CIV'][i, j]
        row['my_CIV_k-20'] = dd['CIV'][i - 20, j]
        row['day_k-20'] = ses[i - 20]
    rows.append(row)
P = pd.DataFrame(rows)
log('\n3. sample points (raw values from my download; study feature vs mine):')
log(P.round(4).to_string(index=False))
fcols = [c for c in P.columns if c.endswith('_study')]
agree = []
for f in fcols:
    b = f[:-6]
    x = P[[f, b + '_mine']].dropna()
    agree.append(f'{b}: {int(np.isclose(x[f], x[b + "_mine"], rtol=1e-3, atol=1e-3).sum())}/{len(x)}')
log('   agreement (rel 1e-3):', agree, '| points', len(P), 'distinct days', P.day.nunique())
P.to_csv(f'{VD}/work/w2_sample_points.csv', index=False)

# ------------------------------------------------------------ 4. all results rows: features
log('\n4. all 3,280 results rows: study feature vs mine')
for f in ['A_dOI5', 'A_dP5', 'A_dOI10', 'A_OI20', 'A_BASIS', 'A_BASISDEV', 'A_PCR', 'A_dPCR5', 'A_IV', 'A_IVREL',
          'A_IVSPREAD', 'A_dCIV20', 'A_dPIV20', 'B_dOI1', 'B_dOI5', 'B_OI20', 'B_BASISDEV', 'B_dBASIS1', 'B_PCR',
          'B_dPCR1', 'B_IVREL', 'B_IVSPREAD', 'B_dCIV20', 'B_dPIV20']:
    x, y = D[f + '_t'], D[f]
    both = x.notna() & y.notna()
    close = np.isclose(x[both], y[both], rtol=1e-3, atol=1e-3)
    log(f'   {f:12s} study n {int(x.notna().sum()):5d} mine n {int(y.notna().sum()):5d} both {int(both.sum()):5d} '
        f'equal {close.mean():.4f}  corr {np.corrcoef(x[both], y[both])[0, 1]:.5f}')
    if (~close).sum():
        bad = D.loc[both].loc[~close, ['symbol', 'qn', f + '_t', f]]
        log('      e.g.', bad.head(4).round(4).to_dict('records'))
