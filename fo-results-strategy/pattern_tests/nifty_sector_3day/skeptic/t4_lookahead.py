"""Claim 4: look-ahead. What the data can say about today's membership / classification applied to 2021-2026."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

pd.set_option('display.width', 250)
first_q = ev.groupby('symbol').qn.min()
first_ret = {s: ret[s].first_valid_index() for s in FOSYM}
start = ses.day.iloc[LO]
late_list = {s for s in FOSYM if first_ret[s] > '2021-03-01'}
late_fo = set(first_q[first_q > 0].index)
print(f'206 stocks: {len(late_fo)} have their first in-F&O result after qn 0 ({(ev.symbol.isin(late_fo)).sum()} results); '
      f'{len(late_list)} have no returns before 2021-03 (listed later): {sorted(late_list)}')
print('first in-F&O qn distribution:', first_q.value_counts().sort_index().to_dict())

rows = []
for fam, name, g in [('NSE', s, ev[ev.nifty_sector == s]) for s in sorted(ev.nifty_sector.unique())] + \
        [('index', s, ev[ev.symbol.isin(MEM[s])]) for s in list(SECTORAL.values()) + list(THEMATIC.values()) if MEM[s]]:
    syms = set(g.symbol)
    rows.append(dict(fam=fam, group=name, stocks=len(syms), late_fo=len(syms & late_fo), listed_later=len(syms & late_list),
                     res=len(g), res_late_fo=int(g.symbol.isin(late_fo).sum()),
                     ex_all=g.ex.mean(), ex_incumbents=g[~g.symbol.isin(late_fo)].ex.mean(),
                     n_inc=int((~g.symbol.isin(late_fo)).sum()), ex_late=g[g.symbol.isin(late_fo)].ex.mean()))
T = pd.DataFrame(rows)
print(T.round(3).to_string())

# selection on outcomes: results of today's F&O stocks from BEFORE they were in F&O (events.csv in_fo False)
pre = evall[(evall.in_fo != True) & evall.symbol.isin(FOSYM) & evall.three_day.notna() & evall.qn.isin(QS)].copy()
pre['td'] = pre.three_day * 100
pre['ex'] = pre.td - pre.qn.map(qmean)
pre['nifty_sector'] = pre.symbol.map(ev.groupby('symbol').nifty_sector.first())
print(f'\npre-F&O results of today\'s F&O stocks: {len(pre)} results, {pre.symbol.nunique()} stocks; avg {pre.td.mean():+.3f}, '
      f'excess over same-quarter in-F&O avg {pre.ex.mean():+.3f}, median {pre.ex.median():+.3f}')
qq = pre.groupby('qn').ex.mean()
print(f'  quarterly mean excess: t {qq.mean() / qq.std(ddof=1) * np.sqrt(len(qq)):+.2f} over {len(qq)} quarters; '
      f'stocks with positive mean: {(pre.groupby("symbol").ex.mean() > 0).sum()} of {pre.symbol.nunique()}')
# the last 4 pre-entry results before joining F&O
pre['k'] = pre.groupby('symbol').qn.rank(ascending=False)
p4 = pre[pre.k <= 4]
print(f'  last 4 results before F&O entry: n {len(p4)}, excess {p4.ex.mean():+.3f}')
late = ev[ev.symbol.isin(late_fo)]
inc = ev[~ev.symbol.isin(late_fo)]
print(f'in-F&O results: late joiners n {len(late)} ex {late.ex.mean():+.3f}; incumbents n {len(inc)} ex {inc.ex.mean():+.3f}')
print('pre-F&O results by NSE sector (n, ex):', pre.groupby('nifty_sector').ex.agg(['size', 'mean']).round(2).to_dict('index'))
au = pre[pre.nifty_sector == 'Automobile and Auto Components']
print('  Auto pre-F&O:', au.groupby('symbol').ex.agg(['size', 'mean']).round(2).to_dict('index'))
