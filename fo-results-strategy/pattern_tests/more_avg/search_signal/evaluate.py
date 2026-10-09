#!/usr/bin/env python3
"""Discovery evaluation (qn 0..13 ONLY) of the candidates in candidates.py / candidates.txt.

Outcomes: tafa/C_post_results/trades.csv - rows with qn >= 14 are dropped right after reading, before any arithmetic.
Writes discovery_table.csv / discovery_table.md / discovery_trades.csv / finalists.txt / run.log in this folder.
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.environ.get('LAB_ROOT', os.path.abspath(os.path.join(HERE, '..', '..')))  # scratch data folder
sys.path.insert(0, HERE)
from candidates import CANDS, W  # noqa: E402

DISC_MAX_QN = 13
COST, C_STK = 0.19, 0.17
LOG = open(f'{HERE}/run.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')


# ------------------------------------------------------------------ outcomes: discovery rows only
tr = pd.read_csv(f'{SP}/tafa/C_post_results/trades.csv', usecols=['symbol', 'qn', 'i_react', 'raw_H20', 'nifty_H20'])
tr = tr[tr.qn <= DISC_MAX_QN].copy()          # SEAL: holdout rows gone before anything is computed
assert tr.qn.max() <= DISC_MAX_QN
tr['vsN_net'] = tr.raw_H20 - tr.nifty_H20 - COST
tr['raw_net'] = tr.raw_H20 - C_STK

fe = pd.read_csv(f'{HERE}/features_signal.csv')
fe = fe[fe.qn <= DISC_MAX_QN]
d = fe.merge(tr, on=['symbol', 'qn'], how='inner', validate='1:1')
assert (d.i_react_x == d.i_react_y).all() and len(d) == len(fe)
d['year'] = d.reaction_day.str[:4].astype(int)


def stats(m):
    x = d.loc[m]
    v = x.vsN_net.sort_values()
    n = len(v)
    qs = x.groupby('qn').vsN_net.mean()
    tot = v.sum()
    y23 = x.loc[x.year == 2023, 'vsN_net'].sum()
    return dict(n=n, avg=v.mean() if n else np.nan, median=v.median() if n else np.nan,
                wo_best5=v.iloc[:-5].mean() if n > 5 else np.nan,
                win=(v > 0).mean() * 100 if n else np.nan,
                raw_net=x.raw_net.mean() if n else np.nan,
                q_with=int(len(qs)), q_pos=int((qs > 0).sum()),
                share2023=(y23 / tot * 100) if n and tot > 0 else np.nan,
                avg_ex2023=x.loc[x.year != 2023, 'vsN_net'].mean() if n else np.nan,
                n_ex2023=int((x.year != 2023).sum()))


base_m = W(d)
B = stats(base_m)
P(f"BASE (XN>4 & cut RSI14>50) discovery: n {B['n']} avg {B['avg']:+.3f} median {B['median']:+.3f} "
  f"w/o best5 {B['wo_best5']:+.3f} quarters +{B['q_pos']}/{B['q_with']} raw_net {B['raw_net']:+.3f} "
  f"2023 share {B['share2023']:.0f}% avg ex-2023 {B['avg_ex2023']:+.3f} (n {B['n_ex2023']})")
assert B['n'] == 122, B['n']
assert abs(B['avg'] - 2.65) < 0.006, B['avg']
BAR = B['wo_best5'] + 0.5
P(f"FINALIST BAR: discovery avg w/o best 5 >= {BAR:+.3f} (base {B['wo_best5']:+.3f} + 0.5), n >= 35, quarters >= 7")

rows = [dict(name='BASE', definition='XN>4 & cut RSI14>50', **B)]
for name, defin, f in CANDS:
    m = f(d).fillna(False).astype(bool)
    assert not (m & ~base_m).any(), name   # every candidate is a subset of the baseline signals
    rows.append(dict(name=name, definition=defin, **stats(m)))
T = pd.DataFrame(rows)
T['eligible'] = (T.n >= 35) & (T.q_with >= 7) & (T.name != 'BASE')
T['clears_bar'] = T.eligible & (T.wo_best5 >= BAR)
T.to_csv(f'{HERE}/discovery_table.csv', index=False, float_format='%.4f')

pd.set_option('display.width', 250, 'display.max_rows', 100)
P(T[['name', 'n', 'avg', 'median', 'wo_best5', 'win', 'raw_net', 'q_pos', 'q_with', 'share2023', 'avg_ex2023',
     'eligible', 'clears_bar']].round(2).to_string(index=False))

# markdown table
md = ['| # | candidate | definition | n | avg | w/o best 5 | median | quarters +/with | 2023 share | eligible | clears bar |',
      '|---|---|---|---|---|---|---|---|---|---|---|']
for i, r in T.iterrows():
    md.append(f"| {i} | {r['name']} | {r.definition} | {r.n} | {r.avg:+.2f} | {r.wo_best5:+.2f} | {r['median']:+.2f} | "
              f"{r.q_pos}/{r.q_with} | {r.share2023:.0f}% | {'yes' if r.eligible else 'no'} | "
              f"{'YES' if r.clears_bar else 'no'} |")
open(f'{HERE}/discovery_table.md', 'w').write('\n'.join(md) + '\n')

# finalists
F = T[T.clears_bar].sort_values('wo_best5', ascending=False).head(2)
P('\nELIGIBLE ranked by w/o best 5:')
P(T[T.eligible].sort_values('wo_best5', ascending=False)[['name', 'n', 'avg', 'wo_best5', 'q_pos', 'q_with']]
  .round(3).to_string(index=False))
P('\nFINALISTS:', ', '.join(F.name) if len(F) else 'NONE')

# per-quarter (discovery) for base and finalists, and the trades of the finalists
out = []
for name in ['BASE'] + F.name.tolist():
    f = (lambda dd: W(dd)) if name == 'BASE' else [c for c in CANDS if c[0] == name][0][2]
    m = f(d).fillna(False).astype(bool)
    x = d.loc[m].copy()
    x['candidate'] = name
    out.append(x)
    pq = x.groupby('qn').vsN_net.agg(['count', 'mean']).round(2)
    P(f'\n{name}: per discovery quarter (n, avg vsN_net)')
    P(pq.T.to_string())
    py = x.groupby('year').vsN_net.agg(['count', 'mean', 'sum']).round(2)
    P(py.T.to_string())
    P('top 5 trades:', x.nlargest(5, 'vsN_net')[['symbol', 'qn', 'vsN_net']].round(2).values.tolist())
if out:
    pd.concat(out)[['candidate', 'symbol', 'quarter', 'qn', 'reaction_day', 'XN', 'cut_rsi14', 'rx_vol_ratio_50',
                    'rx_clv', 'rx_brk52', 'lag_pct', 'secrel21', 'GOOD', 'mcap', 'raw_H20', 'nifty_H20', 'vsN_net',
                    'raw_net']].to_csv(f'{HERE}/discovery_trades.csv', index=False, float_format='%.4f')
LOG.close()
