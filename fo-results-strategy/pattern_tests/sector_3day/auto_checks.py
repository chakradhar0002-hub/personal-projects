#!/usr/bin/env python3
"""Checks on the auto-sector result: by stock and sub-industry, by year, against Nifty and Nifty Auto over the same
3 days, and a placebo on ordinary 3-day windows of the same stocks (no result session within 10 sessions)."""
import os
import numpy as np
import pandas as pd

LAB = os.environ.get('LAB_ROOT', 'lab')
OUT = os.environ.get('OUT', os.path.join(os.environ.get('REPO_ROOT', '.'), 'results', 'sector_3day'))
D = f'{LAB}/sector_lab/data'
ev = pd.read_csv(f'{OUT}/results_3day.csv')
evall = pd.read_csv(f'{D}/events.csv')
ev = ev.merge(evall[['symbol', 'qn', 'i_cut', 'i_m1', 'i_rd', 'i_p1']], on=['symbol', 'qn'])
ev['td'] = ev.three_day * 100
ret = pd.read_csv(f'{D}/returns.csv', index_col=0)
R = ret.to_numpy(float); col = {s: j for j, s in enumerate(ret.columns)}
ix = pd.read_csv(f'{D}/index_close.csv', index_col=0)
def idx_ret(name):
    c = ix[name].to_numpy(float); r = np.r_[np.nan, c[1:] / c[:-1] - 1]; return r
nif, aut = idx_ret('Nifty 50'), idx_ret('Nifty Auto')
w = lambda r, a, b, c: (np.nansum([r[a], r[b], r[c]])) * 100
ev['nifty3'] = [w(nif, a, b, c) for a, b, c in zip(ev.i_m1, ev.i_rd, ev.i_p1)]
ev['auto3'] = [w(aut, a, b, c) for a, b, c in zip(ev.i_m1, ev.i_rd, ev.i_p1)]
A = ev[ev.sector == 'Auto & auto parts'].copy()
qmean = ev.groupby('qn').td.mean()
A['ex'] = A.td - A.qn.map(qmean)
log = []
P = lambda *a: log.append(' '.join(str(x) for x in a))
P(f'auto results {len(A)}, avg 3-day {A.td.mean():+.2f}, vs Nifty {(A.td - A.nifty3).mean():+.2f}, vs Nifty Auto {(A.td - A.auto3).mean():+.2f}, excess over all results same quarter {A.ex.mean():+.2f}')
P('all F&O results: vs Nifty', f'{(ev.td - ev.nifty3).mean():+.2f}')
P('\nby sub-industry:'); P(A.groupby('industry').td.agg(['size', 'mean']).round(2).to_string())
P('\nby stock (sorted by mean):'); bs = A.groupby('symbol').td.agg(['size', 'mean', 'sum']).sort_values('mean'); P(bs.round(2).to_string())
P(f'\nstocks with positive average: {(bs["mean"] > 0).sum()} of {len(bs)}')
tot = A.td.sum(); top = bs['sum'].sort_values(ascending=False)
P(f'total {tot:.1f}; top 3 stocks give {top.iloc[:3].sum():.1f}; without top 3 stocks avg {A[~A.symbol.isin(top.index[:3])].td.mean():+.2f}')
A['year'] = pd.to_datetime(A.results_date).dt.year
P('\nby results year:'); P(A.groupby('year').agg(n=('td', 'size'), avg=('td', 'mean'), ex=('ex', 'mean')).round(2).to_string())
P('\nby day (Day-1 / Result day / Day+1), %:', f"{A.ret_dm1.mean()*100:+.2f} / {A.ret_rd.mean()*100:+.2f} / {A.ret_dp1.mean()*100:+.2f}",
  '| all results:', f"{ev.ret_dm1.mean()*100:+.2f} / {ev.ret_rd.mean()*100:+.2f} / {ev.ret_dp1.mean()*100:+.2f}")
# placebo: ordinary 3-day windows (from a close c to c+3) for the auto stocks, no result session within 10 sessions
res_sessions = {}
for s, g in evall.groupby('symbol'):
    res_sessions[s] = np.sort(g.i_rd.dropna().astype(int).to_numpy())
pl = []
T = R.shape[0]
for s in A.symbol.unique():
    j = col[s]; rs = res_sessions.get(s, np.array([]))
    first = int(A[A.symbol == s].i_cut.min()); last = int(A[A.symbol == s].i_p1.max())
    for c in range(first, min(last, T - 4), 3):
        if rs.size and np.min(np.abs(rs - (c + 2))) <= 10:
            continue
        x = R[c + 1:c + 4, j]
        if np.isnan(x).all():
            continue
        pl.append((s, c, np.nansum(x) * 100, np.nansum(nif[c + 1:c + 4]) * 100))
pl = pd.DataFrame(pl, columns=['symbol', 'c', 'r3', 'n3'])
P(f'\nplacebo (ordinary 3-day windows of the same auto stocks): {len(pl)} windows, avg {pl.r3.mean():+.2f}, vs Nifty {(pl.r3 - pl.n3).mean():+.2f}')
P(f'results windows vs Nifty {(A.td - A.nifty3).mean():+.2f}  -> results-specific part about {(A.td - A.nifty3).mean() - (pl.r3 - pl.n3).mean():+.2f}')
open(f'{OUT}/auto_checks.log', 'w').write('\n'.join(log) + '\n')
print('\n'.join(log))
