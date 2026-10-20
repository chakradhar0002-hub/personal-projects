"""k2c: the post-hoc both-sides date-demeaned variant under the pre-registered confirmation rule (A1 lags maxT-8, D
features maxT-7, inside each half), plus top-fifth trade economics and stock concentration."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from common import *
F = load(); F['qn'] = F.qn.astype(int)
ev = pd.read_csv(os.path.join(D, 'events.csv'))
E = ev[ev.three_day.notna()].copy(); E['td'] = E.three_day * 100
g = E.groupby('i_cut').td; E['n'] = g.transform('size')
E['hdd'] = np.where(E.n >= 2, (E.td - g.transform('sum') / E.n) * E.n / (E.n - 1), np.nan)
k = E.set_index(['symbol', 'qn'])
for kk in range(1, 9):
    F[f'hdd{kk}'] = k.hdd.reindex(pd.MultiIndex.from_arrays([F.symbol, F.qn - kk])).to_numpy()
H = np.column_stack([F[f'hdd{kk}'] for kk in range(1, 9)])
a4 = ~np.isnan(H[:, :4]).any(1); a8 = ~np.isnan(H).any(1); a2 = ~np.isnan(H[:, :2]).any(1)
U = np.where(np.isnan(H), np.nan, (H > 0).astype(float))
F['n_up4d'] = np.where(a4, np.nansum(U[:, :4], 1), np.nan); F['n_up8d'] = np.where(a8, np.nansum(U, 1), np.nan)
F['mean2d'] = np.where(a2, np.nanmean(H[:, :2], 1), np.nan)
F['mean4d'] = np.where(a4, np.nanmean(H[:, :4], 1), np.nan); F['mean8d'] = np.where(a8, np.nanmean(H, 1), np.nan)
F['best4d'] = np.where(a4, np.nanmax(np.where(a4[:, None], H[:, :4], 0), 1), np.nan)
F['worst4d'] = np.where(a4, np.nanmin(np.where(a4[:, None], H[:, :4], 0), 1), np.nan)
Y = 'y_dd_all'
fams = {'A1 (lags)': [f'hdd{kk}' for kk in range(1, 9)], 'D (counts/averages)': ['n_up4d', 'n_up8d', 'mean2d', 'mean4d', 'mean8d', 'best4d', 'worst4d']}
for fam, feats in fams.items():
    print(f'== {fam}, both sides same-cutoff demeaned, outcome {Y}')
    res = {}
    for hn, m in (('all', F.qn >= 0), ('first', F.qn <= 13), ('last', F.qn >= 14)):
        o, nl, nq = perm_ic_multi(F[m], feats, Y, B=3000, seed=12)
        res[hn] = (o, np.array([two_sided(nl[:, j], o[j]) for j in range(len(feats))]), maxT(nl, o))
    for j, f in enumerate(feats):
        conf = res['first'][2][j] < 0.05 and np.sign(res['first'][0][j]) == np.sign(res['last'][0][j]) and res['last'][1][j] < 0.05
        print(f'  {f:8s} all {res["all"][0][j]:+.3f} p {fpv(res["all"][1][j])} maxT {res["all"][2][j]:.3f} | first {res["first"][0][j]:+.3f} '
              f'maxT {res["first"][2][j]:.3f} | last {res["last"][0][j]:+.3f} p {fpv(res["last"][1][j])} | confirmed {conf}')
# economics of the top fifth of mean4d (long, cutoff -> Day+1)
for f in ('mean4d', 'best4d', 'hdd3'):
    have = F[f].notna()
    pr = F[have].groupby('qn')[f].rank(pct=True)
    top = F[have][pr > 0.8]
    st = top.groupby('symbol').x.agg(['sum', 'size']).sort_values('sum', ascending=False)
    pq = top.groupby('qn').y.mean() - COST
    print(f'\n{f} top fifth: {len(top)} trades, {top.symbol.nunique()} stocks, gross {top.y.mean():+.2f}%, net {top.y.mean() - COST:+.2f}%, '
          f'x {top.x.mean():+.2f}, y_dd_all {top.y_dd_all.mean():+.2f}; first 14 q net {top[top.qn <= 13].y.mean() - COST:+.2f}% '
          f'({int((top.qn <= 13).sum())}) last 8 q {top[top.qn >= 14].y.mean() - COST:+.2f}% ({int((top.qn >= 14).sum())}); quarters net>0 '
          f'{int((pq > 0).sum())}/{len(pq)}; top-5 stocks share of summed x {st["sum"].head(5).sum() / st["sum"].sum():.0%} '
          f'({", ".join(st.index[:5])}); without them x {top[~top.symbol.isin(st.index[:5])].x.mean():+.2f}; overlap pp_top10 {int(top.pp_top10.sum())}')
