#!/usr/bin/env python3
"""Verifier, own code: extra checks for B09 (and B13): tail dependence with a fair trimmed-mean luck test, rank tests,
winsorised means, return decomposition around the entry (gap / day k+1 / later), and the role of PCR level vs change.
usage: python3 w8_extra.py <scratchpad> <verify_dir>
"""
import sys

import numpy as np
import pandas as pd

SP, VD = sys.argv[1], sys.argv[2]
W = f'{VD}/work'
LOG = open(f'{W}/w8_extra.log', 'w')
pd.set_option('display.width', 250)
rng = np.random.default_rng(123)


def log(*a):
    s = ' '.join(map(str, a))
    print(s, flush=True)
    LOG.write(s + '\n')


ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv')
DAYS = ses.day.to_numpy()
T = len(DAYS)
ret = pd.read_csv(f'{SP}/sector_lab/data/returns.csv', index_col=0)
SY = ret.columns.tolist()
SJ = {s: j for j, s in enumerate(SY)}
RET = ret.to_numpy(float)
PX = np.cumprod(1 + np.nan_to_num(RET), axis=0)
NIF = pd.read_csv(f'{SP}/sector_lab/data/index_close.csv', index_col=0)['Nifty 50'].to_numpy(float)
ohl = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'open', 'close'])
ohl = ohl[ohl.symbol.isin(SJ) & ohl.day.isin(set(DAYS))]
DI = {d: i for i, d in enumerate(DAYS)}
OPEN = np.full((T, len(SY)), np.nan)
CLO = np.full((T, len(SY)), np.nan)
OPEN[ohl.day.map(DI).to_numpy(), ohl.symbol.map(SJ).to_numpy()] = ohl.open.to_numpy(float)
CLO[ohl.day.map(DI).to_numpy(), ohl.symbol.map(SJ).to_numpy()] = ohl.close.to_numpy(float)

pan = pd.read_csv(f'{SP}/perf/features/panel.csv', usecols=['symbol', 'qn', 'i_react', 'W', 'XN', 'cut_rsi14'])
oc = pd.read_csv(f'{SP}/perf/features/outcomes.csv', usecols=['symbol', 'qn', 'vsN_net_H20', 'tradable_B'])
fl = pd.read_csv(f'{W}/w4_flags.csv')
fe = pd.read_csv(f'{W}/w_results_features.csv', usecols=['symbol', 'qn', 'A_PCR', 'B_PCR', 'Bm1_PCR', 'B_dPCR1'])
D = pan.merge(oc, on=['symbol', 'qn']).merge(fl, on=['symbol', 'qn']).merge(fe, on=['symbol', 'qn'])
PB = ((D.W == True) & (D.tradable_B == True)).to_numpy()
D = D[PB].reset_index(drop=True)
y = D.vsN_net_H20.to_numpy(float)
q = D.qn.to_numpy()
J = D.symbol.map(SJ).to_numpy()
k = D.i_react.to_numpy()


def trimmed_luck(m, drop, nd=20000):
    """statistic: mean of the signal set without its `drop` best trades; null: random same-size within-quarter picks
    from the 392 winners with their own `drop` best removed."""
    obs = np.sort(y[m])[:-drop].mean() if drop else y[m].mean()
    cnt = pd.Series(q[m]).value_counts()
    sims = np.empty((nd, int(m.sum())))
    c0 = 0
    for g, c in cnt.items():
        pool = y[q == g]
        pick = np.argsort(rng.random((nd, len(pool))), axis=1)[:, :c]
        sims[:, c0:c0 + c] = pool[pick]
        c0 += c
    sims.sort(axis=1)
    st = sims[:, :sims.shape[1] - drop].mean(1) if drop else sims.mean(1)
    return obs, st.mean(), (1 + (st >= obs - 1e-12).sum()) / (nd + 1)


def within_q_rank_test(m, nd=20000):
    """share of signal trades above their quarter's winner median; null by within-quarter permutation."""
    med = pd.Series(y).groupby(q).transform('median').to_numpy()
    above = (y > med).astype(float)
    obs = above[m].mean()
    cnt = pd.Series(q[m]).value_counts()
    tot = np.zeros(nd)
    for g, c in cnt.items():
        pool = above[q == g]
        pick = np.argsort(rng.random((nd, len(pool))), axis=1)[:, :c]
        tot += pool[pick].sum(1)
    st = tot / m.sum()
    return obs, (1 + (st >= obs - 1e-12).sum()) / (nd + 1)


for t in ('B09', 'B13'):
    m = D[t].to_numpy(bool)
    el = D['el_' + t].to_numpy(bool)
    log(f'\n========== {t}: n {m.sum()} of {len(D)} winners')
    for drop in (0, 5, 10, 20):
        o, nm, p = trimmed_luck(m, drop)
        log(f'  mean without own best {drop:2d}: signal {o:+.3f}  random same-size subsets (same trimming) {nm:+.3f}  '
            f'diff {o - nm:+.3f}  luck p {p:.4f}')
    o, p = within_q_rank_test(m)
    log(f'  share of signal trades above their quarter winner median: {o:.3f} (null 0.5ish), luck p {p:.4f}')
    for lo, hi in ((1, 99), (5, 95)):
        a, b = np.percentile(y, [lo, hi])
        yw = np.clip(y, a, b)
        qm = pd.Series(yw).groupby(q).mean()
        ex = (yw[m] - qm.reindex(q[m]).to_numpy()).mean()
        log(f'  winsorised {lo}/{hi}: signal mean {yw[m].mean():+.3f} OUT {yw[el & ~m].mean():+.3f} excess {ex:+.3f}')
    log(f'  median net: signal {np.median(y[m]):+.3f}  OUT {np.median(y[el & ~m]):+.3f}  all winners {np.median(y):+.3f}')
    # decomposition of the stock leg (unhedged, %): gap close k -> open k+1, day k+1 open -> close, k+1 close -> k+20 close
    gap = (OPEN[k + 1, J] / CLO[k, J] - 1) * 100
    d1 = (CLO[k + 1, J] / OPEN[k + 1, J] - 1) * 100
    rest = (PX[k + 20, J] / PX[k + 1, J] - 1) * 100
    k21 = (PX[k + 21, J] / PX[k + 20, J] - 1) * 100
    nf = lambda a, b: (NIF[b] / NIF[a] - 1) * 100
    rows = []
    for nm_, v, nv in (('gap close k->open k+1 (stock)', gap, np.zeros(len(k))),
                       ('day k+1 open->close (stock)', d1, np.zeros(len(k))),
                       ('close k -> close k+1 hedged', (PX[k + 1, J] / PX[k, J] - 1) * 100, nf(k, k + 1)),
                       ('close k+1 -> close k+20 hedged', rest, nf(k + 1, k + 20)),
                       ('close k+20 -> close k+21 hedged', k21, nf(k + 20, k + 21))):
        h = v - nv
        qm = pd.Series(h).groupby(q).mean()
        exc = h - qm.reindex(q).to_numpy()
        rows.append({'piece': nm_, 'signal_mean': np.nanmean(h[m]), 'OUT_mean': np.nanmean(h[el & ~m]),
                     'signal_excess_vs_winners': np.nanmean(exc[m])})
    log(pd.DataFrame(rows).round(3).to_string(index=False))

# PCR level vs change: 2x2 among winners (cutoff PCR top quintile within quarter over all results is in w6; here use
# the winners' own medians for a descriptive split)
m9 = D.B09.to_numpy(bool)
hi_pre = (D.A_PCR > D.A_PCR.groupby(D.qn).transform('median')).to_numpy()
hi_chg = (D.B_dPCR1 > D.B_dPCR1.groupby(D.qn).transform('median')).to_numpy()
log('\nB09 decomposition among winners: PCR at cutoff above winners-median (pre level) x PCR change on k above median')
for a_ in (True, False):
    for b_ in (True, False):
        s = (hi_pre == a_) & (hi_chg == b_)
        log(f'  pre-level high={a_!s:5s} change high={b_!s:5s}: n {s.sum():3d} net {y[s].mean():+.3f}  (B09 share {m9[s].mean():.2f})')
log('done')
