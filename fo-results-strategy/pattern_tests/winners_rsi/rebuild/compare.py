"""Final comparison step: rebuild (universe.csv from rebuild.py) vs tafa/C_post_results features.csv / trades.csv /
per_quarter.csv and ta/build/events_ta.csv. Writes compare.log and mismatches.csv."""
import os

import numpy as np
import pandas as pd

SP = os.environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = SP + '/winners_rsi/rebuild'
U = pd.read_csv(OUT + '/universe.csv')
F = pd.read_csv(SP + '/tafa/C_post_results/features.csv')
T = pd.read_csv(SP + '/tafa/C_post_results/trades.csv')
PQ0 = pd.read_csv(SP + '/tafa/C_post_results/per_quarter.csv')
ETA = pd.read_csv(SP + '/ta/build/events_ta.csv', usecols=['symbol', 'qn', 'rsi14', 'traded_at_cut', 'n_hist'])
log = []
P = lambda *a: (print(*a), log.append(' '.join(str(x) for x in a)))

key = ['symbol', 'qn']
m = U.merge(F[key + ['i_cut', 'i_react', 'XN', 'W', 'cut_rsi14', 'rx_rsi14', 'RSI_HI']],
            on=key, how='outer', suffixes=('', '_f'), indicator=True)
m = m.merge(T[key + ['XN', 'W', 'RSI_HI', 'W_RSI_HI', 'raw_H20', 'nifty_H20']].rename(
    columns={'XN': 'XN_t', 'W': 'W_t', 'RSI_HI': 'RSI_HI_t', 'W_RSI_HI': 'W_RSI_HI_t', 'raw_H20': 'raw_H20_t',
             'nifty_H20': 'nifty_H20_t'}), on=key, how='left')
m = m.merge(ETA.rename(columns={'rsi14': 'rsi14_eta'}), on=key, how='left')
P('rows: rebuild', len(U), '| features', len(F), '| trades', len(T), '| join', m['_merge'].value_counts().to_dict())
P('session indices equal (i_cut, i_react):', int((m.i_cut != m.i_cut_f).sum()), int((m.i_react != m.i_react_f).sum()),
  'mismatches')

b = lambda s: s.astype(str).str.lower().isin(['true', '1', '1.0'])
mm = []


def rep(name, mask, cols):
    n = int(mask.sum())
    P(f'{name}: {n} mismatches')
    if n:
        P(m.loc[mask, key + cols].to_string(index=False))
        for r in m.loc[mask, key].itertuples(index=False):
            mm.append(dict(symbol=r.symbol, qn=r.qn, check=name))


# XN
dXN = (m.XN - m.XN_f).abs()
P(f'XN vs features: max abs diff {dXN.max():.2e}; >1e-6: {int((dXN > 1e-6).sum())}; '
  f'vs trades (4 dp): max {(m.XN - m.XN_t).abs().max():.2e}')
rep('XN > 0.01 vs features', dXN > 0.01, ['XN', 'XN_f'])
rep('winner flag W vs features', b(m.W) != b(m.W_f), ['XN', 'XN_f'])
rep('winner flag W vs trades', b(m.W) != b(m.W_t), ['XN', 'XN_t'])
P('closest XN to the 4.0 threshold (rebuild):')
P(m.assign(dist=(m.XN - 4).abs()).nsmallest(6, 'dist')[key + ['XN', 'XN_f', 'W', 'W_f']].to_string(index=False))

# RSI at cutoff
dR = (m.rsi14_cut - m.cut_rsi14).abs()
P(f'RSI14 at cutoff vs features.cut_rsi14: both present {int((m.rsi14_cut.notna() & m.cut_rsi14.notna()).sum())}, '
  f'rebuild-only {int((m.rsi14_cut.notna() & m.cut_rsi14.isna()).sum())}, features-only '
  f'{int((m.rsi14_cut.isna() & m.cut_rsi14.notna()).sum())}; max abs diff {dR.max():.2e}; median {dR.median():.2e}; '
  f'>1e-3: {int((dR > 1e-3).sum())}; >0.01: {int((dR > 0.01).sum())}; >0.1: {int((dR > 0.1).sum())}')
dE = (m.rsi14_cut - m.rsi14_eta).abs()
P(f'RSI14 at cutoff vs events_ta.rsi14: max abs diff {dE.max():.2e}; >1e-3: {int((dE > 1e-3).sum())}; '
  f'features.cut_rsi14 vs events_ta.rsi14 max diff {(m.cut_rsi14 - m.rsi14_eta).abs().max():.2e}')
P('largest RSI diffs:')
P(m.assign(d=dR).nlargest(8, 'd')[key + ['rsi14_cut', 'cut_rsi14', 'rsi14_eta', 'rsi_rows', 'n_hist', 'd']]
  .to_string(index=False))
rep('RSI_HI flag vs features', b(m.RSI_HI) != b(m.RSI_HI_f), ['rsi14_cut', 'cut_rsi14', 'W'])
rep('RSI_HI flag vs trades', b(m.RSI_HI) != b(m.RSI_HI_t), ['rsi14_cut', 'cut_rsi14', 'W'])
near = m[(m.rsi14_cut - 50).abs() <= 1].copy()
P(f'results with RSI14 within 50 +/- 1: {len(near)} (winners among them: {int(b(near.W).sum())}); all flags agree: '
  f'{bool((b(near.RSI_HI) == b(near.RSI_HI_f)).all())}')
P('winners with RSI14 within 50 +/- 2 (rebuild vs features):')
P(m[b(m.W) & ((m.rsi14_cut - 50).abs() <= 2)].sort_values('rsi14_cut')[
    key + ['XN', 'rsi14_cut', 'cut_rsi14', 'RSI_HI', 'RSI_HI_f', 'vsN_net']].to_string(index=False))
dRX = (m.rsi14_react - m.rx_rsi14).abs()
P(f'RSI14 at reaction close vs features.rx_rsi14 (diagnostic): max abs diff {dRX.max():.2e}; >1e-3: '
  f'{int((dRX > 1e-3).sum())}')

# signal membership
rep('signal W & RSI>50 vs trades.W_RSI_HI', b(m.W_RSI_HI) != b(m.W_RSI_HI_t), ['XN', 'rsi14_cut', 'cut_rsi14'])

# outcomes
dr = (m.raw_gross - m.raw_H20_t).abs()
dn = (m.nifty_H20 - m.nifty_H20_t).abs()
vs_t = m.raw_H20_t - m.nifty_H20_t - 0.19
dv = (m.vsN_net - vs_t).abs()
P(f'raw_H20 (stock 20-session return): max abs diff {dr.max():.2e}; >0.01 pts: {int((dr > 0.01).sum())} '
  f'(trades.csv is rounded to 4 dp)')
P(f'nifty_H20: max abs diff {dn.max():.2e}; >0.01 pts: {int((dn > 0.01).sum())}')
P(f'vsN_net: max abs diff {dv.max():.2e}; >0.01 pts: {int((dv > 0.01).sum())}')
rep('outcome raw_H20 > 0.01 pts', dr > 0.01, ['raw_gross', 'raw_H20_t'])
rep('outcome nifty_H20 > 0.01 pts', dn > 0.01, ['nifty_H20', 'nifty_H20_t'])

# per-quarter vs per_quarter.csv (W_RSI_HI, H=20)
mine = pd.read_csv(OUT + '/per_quarter.csv')
ref = PQ0[(PQ0.test == 'W_RSI_HI') & (PQ0.H == 20)][['qn', 'n', 'vsN_net', 'raw_net', 'plain_winners_vsN_net']]
c = mine.merge(ref.rename(columns={'plain_winners_vsN_net': 'pw_ref'}), on='qn', how='outer')
P('per-quarter vs tafa per_quarter.csv (W_RSI_HI H20): n mismatches', int((c.trades != c.n).sum()),
  '| max |vsN_net diff|', f'{(c.avg_vsN_net - c.vsN_net).abs().max():.2e}',
  '| max |raw_net diff|', f'{(c.avg_raw_net - c.raw_net).abs().max():.2e}',
  '| max |plain winners diff|', f'{(c.plain_winners_vsN_net - c.pw_ref).abs().max():.2e}')
sig_t = T[T.W_RSI_HI == 1]
P(f'tafa trades.csv W_RSI_HI==1: n={len(sig_t)}, mean vsN_net = {(sig_t.raw_H20 - sig_t.nifty_H20 - 0.19).mean():+.4f}'
  f' ; rebuild n={int(b(U.W_RSI_HI).sum())}, mean {U.loc[b(U.W_RSI_HI), "vsN_net"].mean():+.4f}')

pd.DataFrame(mm, columns=['symbol', 'qn', 'check']).to_csv(OUT + '/mismatches.csv', index=False)
open(OUT + '/compare.log', 'w').write('\n'.join(log) + '\n')
