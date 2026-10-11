#!/usr/bin/env python3
"""Verifier v2 - recompute and stress W_EARLY / WR_EARLY (trade B) from own features.
usage: python3 v2_stats_B.py SCRATCH WORKDIR STUDY_DIR"""
import sys
import numpy as np
import pandas as pd

SC, W, STUDY = sys.argv[1:4]
COST = 0.19
f = pd.read_csv(f'{W}/feat_results.csv')
ses = pd.read_csv(f'{SC}/sector_lab/data/sessions.csv')
sday = pd.to_datetime(ses.day).values
NS = len(ses)
ret = pd.read_csv(f'{SC}/sector_lab/data/returns.csv')
ret['day'] = pd.to_datetime(ret.day)
ret = ret.set_index('day').reindex(pd.to_datetime(ses.day).values)
ic = pd.read_csv(f'{SC}/sector_lab/data/index_close.csv', usecols=['day', 'Nifty 50'])
ic['day'] = pd.to_datetime(ic.day)
nclose = ic.set_index('day')['Nifty 50'].reindex(pd.to_datetime(ses.day).values).values
nret = pd.Series(nclose).pct_change().values
rng = np.random.default_rng(777)


def hedged(sym, k, H=20):
    r = ret[sym].values[k + 1:k + 1 + H]
    if len(r) < H or np.isnan(r).sum() > 2:
        return np.nan
    stock = np.nanprod(1 + r) - 1
    nif = nclose[k + H] / nclose[k] - 1
    return (stock - nif) * 100


# own outcome check
f['my_vsN'] = [hedged(s, int(k)) if t else np.nan for s, k, t in zip(f.symbol, f.i_react, f.tradable_B)]
d = (f.my_vsN - f.vsN_H20).abs()
print(f'own 20-session hedged return vs outcomes vsN_H20: max |diff| {d.max():.2e} over {d.notna().sum()} rows')

B = f[f.tradable_B == True].copy()
B['y'] = B.vsN_net_H20
B['cutday'] = pd.to_datetime(sday[B.i_react.values])
B['year'] = B.cutday.dt.year
first_q = f.groupby('symbol').qn.min()
B['early_member'] = B.symbol.map(first_q) <= 1
# habitual drifters: mean_drift_4_B >= the quarter's 80th pct over ALL F&O results (study S1 definition)
p80 = f.groupby('qn').mean_drift_4_B.quantile(0.8)
B['habit'] = B.mean_drift_4_B >= B.qn.map(p80)
B['W_'] = B.W == True
B['WR'] = B.W_ & (B.cut_rsi14 > 50)
print(f'W {B.W_.sum()} mean {B[B.W_].y.mean():+.3f}; WR {B.WR.sum()} mean {B[B.WR].y.mean():+.3f}; '
      f'habitual drifters {B.habit.sum()} mean {B[B.habit].y.mean():+.3f}')
B['rq_med'] = B.groupby('qn').RDCHG.transform('median')


def stats(name, pool, sig, with_p=True):
    """pool: parent mask (feature known); sig: signal mask within pool."""
    P = B[pool].copy()
    P['pm'] = P.groupby('qn').y.transform('mean')
    P['g'] = P.y - P.pm
    S = P[sig[pool]]
    o = {'name': name, 'n': len(S)}
    if len(S) == 0:
        return o
    o['net'] = S.y.mean(); o['gain'] = S.g.mean(); o['parent'] = P.y.mean()
    pq = S.groupby('qn').y.mean()
    o['q+'] = f'{(pq > 0).sum()}/{len(pq)}'
    h1, h2 = S[S.qn <= 13], S[S.qn >= 14]
    o['h1 n,net,gain'] = f'{len(h1)}, {h1.y.mean():+.2f}, {h1.g.mean():+.2f}'
    o['h2 n,net,gain'] = f'{len(h2)}, {h2.y.mean():+.2f}, {h2.g.mean():+.2f}'
    s = S.sort_values('y', ascending=False)
    o['net-5'] = s.y.iloc[5:].mean(); o['gain-5'] = s.g.iloc[5:].mean()
    o['net-10'] = s.y.iloc[10:].mean() if len(s) > 10 else np.nan
    o['gain-10'] = s.g.iloc[10:].mean() if len(s) > 10 else np.nan
    o['median'] = S.y.median()
    if with_p:
        obs = S.y.mean(); tot = np.zeros(20000)
        for q, k in S.groupby('qn').size().items():
            v = P.loc[P.qn == q, 'y'].values
            keys = rng.random((20000, len(v)))
            idx = np.argpartition(keys, k - 1, axis=1)[:, :k]
            tot += v[idx].sum(1)
        o['luck_p'] = (1 + (tot / len(S) >= obs - 1e-12).sum()) / 20001
    return o


fmt = lambda df: df.to_string(index=False, float_format=lambda x: f'{x:+.3f}')
pd.set_option('display.width', 260)
known = B.RDCHG.notna()
EARLY = B.RDCHG < -7
rows = [stats('W_EARLY  (RDCHG<-7)', B.W_ & known, EARLY), stats('WR_EARLY (RDCHG<-7)', B.WR & known, EARLY)]
print('\n=== RECOMPUTED'); print(fmt(pd.DataFrame(rows)))
print('study: W_EARLY n 53 net +2.43 gain +1.02 q+ 13/17 h1 22,+1.57,-0.44 h2 31,+3.03,+2.06 w/o5 +0.76,-0.47 luck 0.1348')
print('study: WR_EARLY n 29 gain +2.08 h1/h2 gain +2.19/+2.01 luck 0.062 (diagnostic, n<30)')
tb = pd.read_csv(f'{STUDY}/trades_B.csv')
th = set(zip(tb[tb.test == 'W_EARLY'].symbol, tb[tb.test == 'W_EARLY'].qn))
mi = set(zip(B[B.W_ & EARLY].symbol, B[B.W_ & EARLY].qn))
print(f'W_EARLY trade list: study {len(th)}, mine {len(mi)}, common {len(th & mi)}')

print('\n=== STRESS')
var = []
for thr in (-3, -5, -7, -10, -14):
    var.append(stats(f'W  RDCHG<{thr}', B.W_ & known, B.RDCHG < thr))
    var.append(stats(f'WR RDCHG<{thr}', B.WR & known, B.RDCHG < thr))
dm = B.RDCHG - B.rq_med
var.append(stats('W  RDCHG-quarter median < -7', B.W_ & known, dm < -7))
var.append(stats('WR RDCHG-quarter median < -7', B.WR & known, dm < -7))
for nm, ex in [('excl qn 2-3 (fr last-year dates, 2020 comparison)', B.qn.isin([2, 3])), ('excl qn 2', B.qn == 2)]:
    var.append(stats(f'W_EARLY {nm}', B.W_ & known & ~ex, EARLY))
    var.append(stats(f'WR_EARLY {nm}', B.WR & known & ~ex, EARLY))
print(fmt(pd.DataFrame(var)))

ov = [stats('W_EARLY & habitual drifter', B.W_ & known, EARLY & B.habit),
      stats('W_EARLY not habitual', B.W_ & known, EARLY & ~B.habit),
      stats('habitual drifters & EARLY (pool: habitual, RDCHG known)', B.habit & known, EARLY),
      stats('W_EARLY & RSI>50 (=WR_EARLY, vs W pool)', B.W_ & known, EARLY & (B.cut_rsi14 > 50)),
      stats('W_EARLY & RSI<=50 (vs W pool)', B.W_ & known, EARLY & ~(B.cut_rsi14 > 50)),
      stats('W_EARLY member by qn1', B.W_ & known, EARLY & B.early_member),
      stats('W_EARLY later joiner', B.W_ & known, EARLY & ~B.early_member),
      stats('WR_EARLY member by qn1', B.WR & known, EARLY & B.early_member),
      stats('WR_EARLY later joiner', B.WR & known, EARLY & ~B.early_member)]
print('\noverlap / survivorship:'); print(fmt(pd.DataFrame(ov)))

for nm, pool in [('W', B.W_ & known), ('WR', B.WR & known)]:
    S = B[pool & EARLY]
    P = B[pool]; pm = P.groupby('qn').y.mean()
    g = S.y - S.qn.map(pm)
    lo = [(g[S.qn != q].mean()) for q in sorted(S.qn.unique())]
    print(f'{nm}_EARLY leave-one-quarter-out gain range {min(lo):+.3f} .. {max(lo):+.3f}')
    print(f'{nm}_EARLY by year: ' + ', '.join(f'{y}: n {len(x)} net {x.y.mean():+.2f} gain {(x.y - x.qn.map(pm)).mean():+.2f}'
                                          for y, x in S.groupby('year')))
    print(f'{nm}_EARLY per quarter n: {S.groupby("qn").size().to_dict()}')

# PLACEBO 1: EARLY flag among non-winner results and all results (does early reporting predict 20d drift in general?)
pl = [stats('non-winners (XN<=4) EARLY vs non-winners', ~B.W_ & known, EARLY, False),
      stats('all results EARLY vs all results', known, EARLY, False),
      stats('losers (XN<-4) EARLY vs losers', (B.XN < -4) & known, EARLY, False)]
print('\nplacebo 1 (results that are not winners):'); print(fmt(pd.DataFrame(pl)))

# PLACEBO 2: quiet winner days (|no result session within [d-10, d+22]|, XN_d > 4), stock-quarter carries the EARLY flag
#   of the stock's most recent result (known on that day); gain vs all quiet winners of the same calendar month
ev = pd.read_csv(f'{SC}/sector_lab/data/events.csv', usecols=['symbol', 'qn', 'i_rd'])
fl = f[['symbol', 'qn', 'RDCHG', 'i_react']]
qw = []
for s, g in ev.dropna().groupby('symbol'):
    if s not in ret.columns:
        continue
    rds = np.sort(g.i_rd.astype(int).values)
    r = ret[s].values
    xn = (r - nret) * 100
    cand = np.where(xn > 4)[0]
    for i in cand:
        if i < 1300 or i + 21 >= NS:
            continue
        k = np.searchsorted(rds, i)
        if (k < len(rds) and rds[k] - i <= 22) or (k > 0 and i - rds[k - 1] <= 10):
            continue
        prev = fl[(fl.symbol == s) & (fl.i_react < i)]
        if not len(prev):
            continue
        last = prev.sort_values('i_react').iloc[-1]
        h = hedged(s, i)
        if np.isnan(h):
            continue
        qw.append((s, i, last.qn, last.RDCHG, h - COST))
qw = pd.DataFrame(qw, columns=['symbol', 'i', 'qn_prev', 'RDCHG_prev', 'y'])
qw = qw[qw.RDCHG_prev.notna()]
qw['month'] = pd.to_datetime(sday[qw.i.values]).to_period('M')
qw['g'] = qw.y - qw.groupby('month').y.transform('mean')
e = qw[qw.RDCHG_prev < -7]
print(f'\nplacebo 2: quiet winner days with known last-result RDCHG {len(qw)}; of an EARLY stock-quarter {len(e)}: '
      f'gain {e.g.mean():+.3f} (net {e.y.mean():+.3f})')
Wg = stats('x', B.W_ & known, EARLY, False)['gain']; WRg = stats('x', B.WR & known, EARLY, False)['gain']
print(f'  DiD W_EARLY {Wg - e.g.mean():+.3f}; WR_EARLY {WRg - e.g.mean():+.3f}')
bs = np.array([e.g.values[rng.integers(0, len(e), 53)].mean() for _ in range(10000)])
print(f'  placebo p (W_EARLY gain vs quiet draws of 53): {(bs >= Wg).mean():.4f}')
bs = np.array([e.g.values[rng.integers(0, len(e), 29)].mean() for _ in range(10000)])
print(f'  placebo p (WR_EARLY gain vs quiet draws of 29): {(bs >= WRg).mean():.4f}')

# the trades
S = B[B.WR & known & EARLY].sort_values('y')
print('\nWR_EARLY trades:')
print(S[['symbol', 'qn', 'RDCHG', 'rdays', 'rdays_ly', 'XN', 'cut_rsi14', 'habit', 'y']].round(2).to_string(index=False))
