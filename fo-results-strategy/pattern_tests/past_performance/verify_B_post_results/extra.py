"""Extra checks on S1: cross-sectional rank IC per quarter, first-time vs repeat picks, industry-neutral record,
single-stock removals, year x momentum control, and the realistic per-trade number. Own code."""
import numpy as np, pandas as pd
from scipy.stats import spearmanr

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = SP + '/perf/verify_B_post_results'
t = pd.read_csv(f'{OUT}/vb_tradable.csv')
p = pd.read_csv(f'{OUT}/vb_panel.csv')
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a); print(s); LOG.append(s)


el = t.mean_drift_4.notna()
t['year'] = t.reaction_day_s.str[:4].astype(int)


def summ(sel, par, df=t):
    pm = df[par].groupby('qn').vsN_net.mean()
    x = df[sel]; d = x.vsN_net - x.qn.map(pm); f = x.qn <= 13
    qm = d.groupby(x.qn).mean()
    return (f'n {len(x):4d} avg {x.vsN_net.mean():+.2f} gain {d.mean():+.2f} f14 {d[f].mean():+.2f} l8 {d[~f].mean():+.2f} '
            f'q+ {(qm > 0).sum()}/{len(qm)} t_q {qm.mean() / qm.std() * np.sqrt(len(qm)):.2f}')


# 1. rank IC per quarter over all eligible results (whole cross-section, not just the top quintile)
ics = []
for q, g in t[el].groupby('qn'):
    ics.append((q, spearmanr(g.mean_drift_4, g.vsN_net).statistic, len(g)))
ic = pd.DataFrame(ics, columns=['qn', 'ic', 'n'])
P('rank IC(mean_drift_4, 20-session vsN) per quarter:', ic.ic.round(3).tolist())
for lab, m in (('all', ic.qn >= 0), ('first14', ic.qn <= 13), ('last8', ic.qn > 13)):
    v = ic.ic[m]
    P(f'  {lab}: mean IC {v.mean():+.3f}, t {v.mean() / v.std() * np.sqrt(len(v)):.2f}, positive {(v > 0).sum()}/{len(v)}')

# 2. first-time vs repeat S1 picks (repeat = the stock was S1 at its previous result)
t = t.sort_values(['symbol', 'qn'])
t['S1_prev'] = t.groupby('symbol').S1.shift(1).fillna(False).astype(bool)
t['qn_prev'] = t.groupby('symbol').qn.shift(1)
t.loc[t.qn_prev != t.qn - 1, 'S1_prev'] = False
t = t.sort_index()
P('\nS1 repeat picks (S1 also last quarter):  ', summ(t.S1 & t.S1_prev, el))
P('S1 first-time picks:                     ', summ(t.S1 & ~t.S1_prev, el))

# 3. industry-neutral record: mean_drift_4 minus the quarter x industry mean of mean_drift_4, top quintile
p['md4_ind'] = p.mean_drift_4 - p.groupby(['qn', 'industry']).mean_drift_4.transform('mean')
p['md4_sec'] = p.mean_drift_4 - p.groupby(['qn', 'sector_index']).mean_drift_4.transform('mean')
t = t.merge(p[['symbol', 'qn', 'md4_ind', 'md4_sec']], on=['symbol', 'qn'], how='left')
for c in ('md4_ind', 'md4_sec'):
    th = p.groupby('qn')[c].quantile(0.8)
    P(f'top 20% of {c} (stock record relative to its {"industry" if c == "md4_ind" else "sector index"} peers):',
      summ(t[c] >= t.qn.map(th), el & t[c].notna()))
# industry-level record alone: quarter x industry mean of mean_drift_4, top quintile of rows
p['ind_md4'] = p.groupby(['qn', 'industry']).mean_drift_4.transform('mean')
t = t.merge(p[['symbol', 'qn', 'ind_md4']], on=['symbol', 'qn'], how='left')
th = p.groupby('qn').ind_md4.quantile(0.8)
P('top 20% of the INDUSTRY average record (peer trait):', summ(t.ind_md4 >= t.qn.map(th), el))

# 4. single-stock removals (leave-one-stock-out from trades and parent)
x = t[t.S1]
res = []
for s in x.symbol.unique():
    m = t.symbol != s
    pm = t[el & m].groupby('qn').vsN_net.mean()
    xx = t[t.S1 & m]
    res.append((s, (xx.vsN_net - xx.qn.map(pm)).mean()))
lo = pd.DataFrame(res, columns=['s', 'g']).sort_values('g')
P('\nleave-one-stock-out gain: min', lo.head(3).round(2).values.tolist(), 'max', lo.tail(2).round(2).values.tolist())
for drop in (['IDEA'], ['HAL'], ['HAL', 'BHEL', 'BEL', 'BDL', 'MAZDOCK', 'PFC', 'RECLTD', 'IRFC', 'NHPC', 'SJVN', 'NTPC', 'COALINDIA',
                                'ONGC', 'IOC', 'BPCL', 'GAIL', 'SAIL', 'NMDC', 'NBCC', 'IRCTC', 'CONCOR', 'HUDCO', 'IREDA',
                                'NLCINDIA', 'RVNL', 'BANKBARODA', 'PNB', 'CANBK', 'UNIONBANK', 'SBIN', 'INDIANB', 'BANKINDIA', 'POWERGRID', 'OIL', 'HINDCOPPER', 'LICI', 'GICRE', 'SOLARINDS', 'COCHINSHIP', 'BEML']):
    m = ~t.symbol.isin(drop)
    P(f'w/o {drop if len(drop) < 3 else "PSU / defence list (%d names)" % len(drop)}:', summ(t.S1 & m, el & m))
P('  PSU/defence names among S1 trades:', int(t.S1[t.symbol.isin(drop)].sum()))

# 5. year x momentum control
el2 = el & t.vsN_252.notna()
t['_b'] = t[el2].groupby('qn').vsN_252.transform(lambda s: pd.qcut(s.rank(method='first'), 5, labels=False))
pm = t[el2].groupby(['qn', '_b']).vsN_net.mean()
xx = t[t.S1 & el2].copy()
xx['dm'] = xx.vsN_net.to_numpy() - pm.reindex(pd.MultiIndex.from_arrays([xx.qn, xx._b])).to_numpy()
pq = t[el].groupby('qn').vsN_net.mean()
xx['d'] = xx.vsN_net - xx.qn.map(pq)
P('\nS1 by year: gain (quarter) and gain (quarter x 12m-momentum quintile)')
P(xx.groupby('year').agg(n=('d', 'size'), avg=('vsN_net', 'mean'), gain=('d', 'mean'), gain_mom=('dm', 'mean')).round(2).to_string())
P('2023 excluded:', summ(t.S1 & (t.year != 2023), el & (t.year != 2023)))
P('2024-2026 only (reaction day >= 2024-01-01):', summ(t.S1 & (t.year >= 2024), el & (t.year >= 2024)))
P('2025-2026 only:', summ(t.S1 & (t.year >= 2025), el & (t.year >= 2025)))
P('qn 15-21 (expanded F&O list):', summ(t.S1 & (t.qn >= 15), el & (t.qn >= 15)))

# 6. last-8 and recent luck p (random same-quarter picks of eligible results)
rng = np.random.default_rng(7)


def luck(sel, par, nd=20000):
    x = t[sel]; obs = x.vsN_net.mean(); tot = np.zeros(nd)
    for q, nq in x.groupby('qn').size().items():
        pool = t[par & (t.qn == q)].vsN_net.to_numpy()
        tot += pool[np.argsort(rng.random((nd, len(pool))), axis=1)[:, :nq]].sum(1)
    return (1 + (tot / len(x) >= obs).sum()) / (1 + nd)


for lab, m in (('last8', t.qn > 13), ('qn 17-21', t.qn >= 17), ('2025-2026', t.year >= 2025)):
    P(f'luck p {lab}: {luck(t.S1 & m, el & m):.4f}')

# 7. trades.csv for S1 with results-for labels
x = t[t.S1].copy()
x['d_par'] = x.vsN_net - x.qn.map(pq)
x[['symbol', 'qn', 'results_for', 'reaction_day_s', 'industry', 'XN', 'mean_drift_4', 'vsN_net', 'd_par', 'first_fo_qn']] \
    .sort_values(['qn', 'symbol']).to_csv(f'{OUT}/S1_trades.csv', index=False, float_format='%.3f')
open(f'{OUT}/extra.log', 'w').write('\n'.join(LOG) + '\n')
