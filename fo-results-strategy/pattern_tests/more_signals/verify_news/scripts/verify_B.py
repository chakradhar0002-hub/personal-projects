#!/usr/bin/env python3
"""Verifier: recompute and stress W_EARLY / WR_EARLY (trade B) from the verifier's own features.
usage: python3 -P verify_B.py SP VDIR NEWSDIR"""
import sys

import numpy as np
import pandas as pd

SP, V, NW = sys.argv[1:4]
D = f'{SP}/sector_lab/data'
LOG = open(f'{V}/verify_B.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + '\n')


CB = 0.19
f = pd.read_csv(f'{V}/work/my_feat.csv')
out = pd.read_csv(f'{SP}/perf/features/outcomes.csv', usecols=['symbol', 'qn', 'vsN_net_H20', 'tradable_B'])
pan = pd.read_csv(f'{SP}/perf/features/panel.csv', usecols=['symbol', 'qn', 'industry', 'mean_drift_4_B', 'n_drift_4_B'])
f = f.merge(out, on=['symbol', 'qn']).merge(pan, on=['symbol', 'qn'])
ses = pd.read_csv(f'{D}/sessions.csv')
SD = pd.to_datetime(ses.day)
f['y'] = f.vsN_net_H20
# habitual drifters: mean_drift_4_B >= quarter's 80th pct over all F&O results (n_drift_4_B >= 4)
el = f.n_drift_4_B >= 4
q80 = f[el].groupby('qn').mean_drift_4_B.quantile(0.8)
f['hab'] = el & (f.mean_drift_4_B >= f.qn.map(q80))
hb = f[f.hab & (f.tradable_B == True) & f.y.notna()]
P(f'habitual drifters reproduced: {len(hb)} trades, mean vsN_net {hb.y.mean() + CB:+.3f} gross-of-cost '
  f'/ {hb.y.mean():+.3f} net  [documented 569, +1.80 (gross vsN?)]')
B = f[(f.tradable_B == True) & f.y.notna()].reset_index(drop=True)
W = B[B.W == True].reset_index(drop=True)
P(f'W {len(W)} mean {W.y.mean():+.3f}; WR {int((W.cut_rsi14 > 50).sum())} mean {W.y[W.cut_rsi14 > 50].mean():+.3f}')
W['year'] = SD.iloc[W.i_react.to_numpy(int)].dt.year.to_numpy()
fr = pd.read_csv(f'{NW}/work/feat_results.csv', usecols=['symbol', 'qn', 'RDCHG'])
W = W.merge(fr, on=['symbol', 'qn'], how='left')
P(f'W rows with RDCHG equal to theirs: {np.mean((W.rdchg == W.RDCHG) | (W.RDCHG.isna() & ~W.rdchg_ok)) * 100:.1f}%')
tB = pd.read_csv(f'{NW}/trades_B.csv')


def bstats(pool, mask, name, B_=20000, seed=3):
    """pool: DataFrame (parent, feature known); mask on pool."""
    s = pool[mask]
    pm = pool.groupby('qn').y.mean()
    gain = s.y - s.qn.map(pm)
    r = {'name': name, 'n': len(s), 'net': s.y.mean(), 'gain': gain.mean(), 'parent': pool.y.mean()}
    pq = s.groupby('qn').y.mean()
    r['q+'] = f'{int((pq > 0).sum())}/{len(pq)}'
    for h, hm in (('h1', s.qn <= 13), ('h2', s.qn >= 14)):
        r[h] = f'{int(hm.sum())}, {s.y[hm].mean():+.2f}, {gain[hm].mean():+.2f}'
    o = np.argsort(-s.y.to_numpy())
    r['net-5'] = np.delete(s.y.to_numpy(), o[:5]).mean()
    r['gain-5'] = np.delete(gain.to_numpy(), o[:5]).mean()
    r['net-10'] = np.delete(s.y.to_numpy(), o[:10]).mean() if len(s) > 10 else np.nan
    r['gain-10'] = np.delete(gain.to_numpy(), o[:10]).mean() if len(s) > 10 else np.nan
    r['median'] = s.y.median()
    rng = np.random.default_rng(seed)
    cnt = s.qn.value_counts()
    sims = np.zeros(B_)
    for q, c in cnt.items():
        pv = pool.y[pool.qn == q].to_numpy()
        sims += pv[np.argsort(rng.random((B_, len(pv))), axis=1)[:, :c]].sum(1)
    sims /= cnt.sum()
    r['luck_p'] = (1 + (sims >= s.y.mean() - 1e-12).sum()) / (B_ + 1)
    return r


def tab(rows):
    return pd.DataFrame(rows).to_string(index=False, float_format=lambda v: f'{v:+.3f}')


Wk = W[W.rdchg_ok].reset_index(drop=True)
WRk = Wk[Wk.cut_rsi14 > 50].reset_index(drop=True)
e1 = (Wk.rdchg < -7).to_numpy()
e2 = (WRk.rdchg < -7).to_numpy()
P(f'\nparent W with RDCHG known: {len(Wk)} (theirs 355); WR known: {len(WRk)}')
mine = set(zip(Wk.symbol[e1], Wk.qn[e1]))
th = tB[tB.test == 'W_EARLY']
P(f'W_EARLY trades mine {len(mine)}, theirs {len(th)}, common {len(mine & set(zip(th.symbol, th.qn)))}')
P('\n=== W_EARLY / WR_EARLY recomputed')
rows = [bstats(Wk, e1, 'W_EARLY rdchg<-7'), bstats(WRk, e2, 'WR_EARLY rdchg<-7')]
for c in (-3, -5, -10, -14, -21):
    rows.append(bstats(Wk, (Wk.rdchg < c).to_numpy(), f'W rdchg<{c}'))
    rows.append(bstats(WRk, (WRk.rdchg < c).to_numpy(), f'WR rdchg<{c}'))
rows.append(bstats(Wk, (Wk.rdchg > 7).to_numpy(), 'W LATE rdchg>7'))
rows.append(bstats(Wk, (Wk.rdchg.abs() <= 7).to_numpy(), 'W on-time |rdchg|<=7'))
rows.append(bstats(Wk, (Wk.rdchg < 0).to_numpy(), 'W any earlier rdchg<0'))
P(tab(rows))
P('\n--- W_EARLY trades by quarter / year')
P(Wk[e1].groupby('qn').agg(n=('y', 'size'), net=('y', 'mean')).T.round(2).to_string())
P(Wk[e1].groupby('year').agg(n=('y', 'size'), net=('y', 'mean')).round(2).to_string())
P('WR_EARLY trades:')
P(WRk[e2][['symbol', 'qn', 'rdchg', 'XN', 'cut_rsi14', 'y']].sort_values('y').round(2).to_string(index=False))
P('\n--- LOQO (WR_EARLY gain)')
pm = WRk.groupby('qn').y.mean()
g = WRk.y - WRk.qn.map(pm)
lo = [g[e2 & (WRk.qn != q).to_numpy()].mean() for q in sorted(WRk.qn.unique())]
P(f'WR_EARLY LOQO gain range {min(lo):+.3f} .. {max(lo):+.3f}')
pmW = Wk.groupby('qn').y.mean()
gW = Wk.y - Wk.qn.map(pmW)
lo = [gW[e1 & (Wk.qn != q).to_numpy()].mean() for q in sorted(Wk.qn.unique())]
P(f'W_EARLY LOQO gain range {min(lo):+.3f} .. {max(lo):+.3f}')
P('\n--- overlap')
P(tab([bstats(Wk, e1 & Wk.hab.to_numpy(), 'W_EARLY & habitual'), bstats(Wk, e1 & ~Wk.hab.to_numpy(), 'W_EARLY not habitual'),
       bstats(Wk, e1 & (Wk.cut_rsi14 > 50).to_numpy(), 'W_EARLY & RSI>50'),
       bstats(Wk, e1 & ~(Wk.cut_rsi14 > 50).to_numpy(), 'W_EARLY & RSI<=50')]))
first = B.groupby('symbol').qn.min()
P(tab([bstats(Wk, e1 & (Wk.symbol.map(first) <= 1).to_numpy(), 'W_EARLY members by qn1'),
       bstats(Wk, e1 & (Wk.symbol.map(first) > 1).to_numpy(), 'W_EARLY later joiners'),
       bstats(WRk, e2 & (WRk.symbol.map(first) <= 1).to_numpy(), 'WR_EARLY members by qn1'),
       bstats(WRk, e2 & (WRk.symbol.map(first) > 1).to_numpy(), 'WR_EARLY later joiners')]))
# placebo 1: early reporting among NON-winners (all tradable results, any reaction) - does EARLY predict drift anyway?
Bk = B[B.rdchg_ok].reset_index(drop=True)
nw = Bk[Bk.W != True].reset_index(drop=True)
P('\n--- placebo: same EARLY flag on results that were NOT winners / all results')
P(tab([bstats(nw, (nw.rdchg < -7).to_numpy(), 'non-winners EARLY'), bstats(Bk, (Bk.rdchg < -7).to_numpy(), 'all results EARLY')]))
# placebo 2: quiet-day winners (no result within [k-10, k+22]) of stocks whose most recent result was EARLY
ret = pd.read_csv(f'{D}/returns.csv', index_col=0)
RC = {s: j for j, s in enumerate(ret.columns)}
R = ret.to_numpy(float)
nif = pd.read_csv(f'{D}/index_close.csv', index_col=0)['Nifty 50'].to_numpy(float)
NR = np.r_[np.nan, nif[1:] / nif[:-1] - 1]
px = np.nancumprod(1 + np.nan_to_num(R), axis=0)


def rsi(x, n=14):
    d = np.diff(x, prepend=np.nan)
    au = pd.Series(np.where(d > 0, d, 0.)).ewm(alpha=1 / n, adjust=False).mean()
    ad = pd.Series(np.where(d < 0, -d, 0.)).ewm(alpha=1 / n, adjust=False).mean()
    return (100 - 100 / (1 + au / ad)).to_numpy()


ev = pd.read_csv(f'{D}/events.csv', usecols=['symbol', 'qn', 'i_rd', 'i_react', 'in_fo'])
rk = f.set_index(['symbol', 'qn'])
rows = []
T = len(nif)
for s, g in ev.groupby('symbol'):
    if s not in RC:
        continue
    j = RC[s]
    rr = R[:, j]
    rs = rsi(px[:, j])
    rses = np.unique(np.r_[g.i_rd.to_numpy(int), g.i_react.to_numpy(int)])
    g = g.sort_values('i_react')
    for _, e in g.iterrows():
        if (s, e.qn) not in rk.index:
            continue
        nxt = g.i_rd[g.i_rd > e.i_react]
        hi = int(nxt.min()) - 23 if len(nxt) else T - 22
        for k in range(int(e.i_react) + 11, min(hi, T - 21)):
            xn = (rr[k] - NR[k]) * 100
            if not np.isfinite(xn) or xn <= 4:
                continue
            if np.any((rses >= k - 10) & (rses <= k + 22)):
                continue
            y = ((np.prod(1 + rr[k + 1:k + 21]) - 1) - (nif[k + 20] / nif[k] - 1)) * 100 - CB
            rows.append((s, e.qn, k, xn, rs[k - 2], y, rk.loc[(s, e.qn), 'rdchg'], rk.loc[(s, e.qn), 'rdchg_ok']))
qw = pd.DataFrame(rows, columns=['symbol', 'qn_prev', 'k', 'xn', 'rsi_m2', 'y', 'rdchg_prev', 'ok'])
qw = qw[qw.y.notna()]
qw['month'] = SD.iloc[qw.k.to_numpy(int)].dt.to_period('M').to_numpy()
P(f'\nquiet winners {len(qw)}; RSI>50 {int((qw.rsi_m2 > 50).sum())}; mean y {qw.y.mean():+.3f}')
for nm, pool in (('quiet W', qw[qw.ok]), ('quiet WR', qw[qw.ok & (qw.rsi_m2 > 50)])):
    pool = pool.assign(g=pool.y - pool.groupby('month').y.transform('mean'))
    m = pool.rdchg_prev < -7
    P(f'{nm}: n {len(pool)}, last result EARLY n {int(m.sum())}, gain {pool.g[m].mean():+.3f}, '
      f'net {pool.y[m].mean():+.3f} vs others net {pool.y[~m].mean():+.3f}')
qw.to_csv(f'{V}/work/my_quiet_winners.csv.gz', index=False, compression='gzip')
LOG.close()
