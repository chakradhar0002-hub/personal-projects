#!/usr/bin/env python3
"""PLAN_STOCKS.txt: two and three down days, stock by stock.

Reads OUT/days.csv.gz (build_days.py), OUT/windows4.csv.gz (three_down.py), LAB_ROOT sessions and
REPO_ROOT/results/nifty_sector_3day/results_3day.csv; writes OUT/table_each_stock.md, each_stock.csv and stocks.log.
"""
import hashlib
import os
import numpy as np
import pandas as pd
from scipy import stats

REPO = os.environ.get('REPO_ROOT', '.')
LAB = os.environ.get('LAB_ROOT', 'lab')
OUT = os.environ.get('OUT', os.path.join(REPO, 'results', 'two_down_days'))
HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.join(LAB, 'sector_lab', 'data')
MIN_N, MIN_HALF, NPERM, NPERS, SEED = 30, 15, 1000, 10000, 20261103
log = []
def P(*a):
    log.append(' '.join(str(x) for x in a))
    print(*a)
h = hashlib.sha256(open(os.path.join(HERE, 'PLAN_STOCKS.txt'), 'rb').read()).hexdigest()
P(f'PLAN_STOCKS.txt sha256 {h} ({"MATCH" if h == open(os.path.join(HERE, "PLAN_STOCKS.sha256")).read().strip() else "MISMATCH"})')
rng = np.random.default_rng(SEED)
def holm(p):
    p = np.asarray(p, float); o = np.argsort(p); adj = np.empty(len(p)); run = 0.0
    for k, i in enumerate(o):
        run = max(run, (len(p) - k) * p[i]); adj[i] = min(1.0, run)
    return adj
def bh(p):
    p = np.asarray(p, float); n = len(p); o = np.argsort(p)[::-1]; adj = np.empty(n); run = 1.0
    for k, i in enumerate(o):
        run = min(run, p[i] * n / (n - k)); adj[i] = run
    return adj
pct = lambda v: '-' if pd.isna(v) else f'{v * 100:.1f}%'
sgn = lambda v: '-' if pd.isna(v) else f'{v * 100:+.1f}'
fpv = lambda p: '-' if pd.isna(p) else ('<0.001' if p < 0.001 else f'{p:.3f}')
def md(rows, cols):
    out = ['| ' + ' | '.join(cols) + ' |', '|' + '|'.join('---' if i == 0 else '---:' for i in range(len(cols))) + '|']
    return '\n'.join(out + ['| ' + ' | '.join(str(x) for x in r) + ' |' for r in rows])

# ---------------------------------------------------------------- the two samples (as sector.py)
sec = pd.read_csv(os.path.join(REPO, 'results', 'nifty_sector_3day', 'results_3day.csv'), usecols=['symbol', 'nifty_sector']).drop_duplicates('symbol')
dts = pd.to_datetime(pd.read_csv(f'{PACK}/sessions.csv').day)
T = len(dts)
D = pd.read_csv(f'{OUT}/days.csv.gz')
D = D[D.main].copy()
i3 = D.i3.to_numpy()
d0, d3 = dts.to_numpy()[i3 - 3], dts.to_numpy()[i3]
nx = dts.to_numpy()[np.minimum(i3 + 1, T - 1)]
wd = np.stack([pd.DatetimeIndex(dts.to_numpy()[i3 - k]).weekday for k in range(4)])
nobreak = ((d3 - d0).astype('timedelta64[D]').astype(int) == 3) & (wd < 5).all(axis=0)
D['away'] = nobreak & (i3 + 1 < T) & ((nx - d3).astype('timedelta64[D]').astype(int) == 1) & (pd.DatetimeIndex(nx).weekday < 5)
D2 = pd.DataFrame({'symbol': D.symbol.to_numpy(), 'date': D.day3.to_numpy(), 'sig': ((D.r1 < 0) & (D.r2 < 0)).to_numpy(),
                   'y': D.r3.to_numpy(), 'away': D.away.to_numpy()})
W = pd.read_csv(f'{OUT}/windows4.csv.gz')
D3 = pd.DataFrame({'symbol': W.symbol, 'date': W.day4, 'sig': (W.r1 < 0) & (W.r2 < 0) & (W.r3 < 0), 'y': W.r4,
                   'away': W.holfree.astype(bool)})
for X in (D2, D3):
    X['down'] = (X.y < 0).astype(float)

def peer_diff(X):
    """for signal rows: next day down minus the share down of the other stocks without the signal that date"""
    g = X[~X.sig].groupby('date').down.mean()
    S_ = X[X.sig].copy()
    S_['d'] = S_.down - S_.date.map(g)
    return S_.dropna(subset=['d'])

def per_stock(X):
    S_ = peer_diff(X)
    own = X.groupby('symbol').down.mean()
    cut = X.date.sort_values().iloc[len(X) // 2]
    rows = []
    for s, g in S_.groupby('symbol'):
        k, n = int(g.down.sum()), len(g)
        r = dict(symbol=s, n=n, share_down=g.down.mean(), own_down=own[s], mean_y=g.y.mean(),
                 p_own=stats.binomtest(k, n, own[s]).pvalue if n >= MIN_N else np.nan,
                 peer=g.d.mean(), p_peer=stats.ttest_1samp(g.d, 0).pvalue if n >= MIN_N and g.d.std() > 0 else np.nan)
        for half, m in (('h1', g.date < cut), ('h2', g.date >= cut)):
            x = g.d[m]
            r[f'{half}_n'] = len(x)
            r[f'{half}_peer'] = x.mean() if len(x) else np.nan
            r[f'{half}_p'] = stats.ttest_1samp(x, 0).pvalue if len(x) >= 3 and x.std() > 0 else np.nan
        rows.append(r)
    R = pd.DataFrame(rows)
    t = R.n >= MIN_N
    for c_ in ('p_own', 'p_peer', 'h1_p'):
        R[c_ + '_holm'] = np.nan; R[c_ + '_bh'] = np.nan
        ok = t & R[c_].notna()
        R.loc[ok, c_ + '_holm'] = holm(R.loc[ok, c_]); R.loc[ok, c_ + '_bh'] = bh(R.loc[ok, c_])
    R['confirmed'] = t & (R.h1_p_holm < 0.05) & (np.sign(R.h2_peer) == np.sign(R.h1_peer)) & (R.h2_p < 0.05)
    return R, cut

def heterogeneity(X):
    """spread of per-stock z-scores of the peer difference vs within-date shuffles of the signal labels"""
    X = X.dropna(subset=['down']).reset_index(drop=True)
    dc = pd.factorize(X.date)[0]; sc = pd.factorize(X.symbol)[0]
    y = X.down.to_numpy(); sig = X.sig.to_numpy()
    nd, ns = dc.max() + 1, sc.max() + 1
    order = np.argsort(dc, kind='stable')
    dcs = dc[order]
    start = np.searchsorted(dcs, np.arange(nd))
    pos = np.arange(len(dcs)) - start[dcs]
    nsig = np.bincount(dc[sig], minlength=nd)
    N = np.bincount(dc, minlength=nd); Sy = np.bincount(dc, weights=y, minlength=nd)
    def zvar(sg):
        Ss = np.bincount(dc[sg], weights=y[sg], minlength=nd)
        with np.errstate(invalid='ignore', divide='ignore'):
            peer = (Sy - Ss) / (N - nsig)
        d = y[sg] - peer[dc[sg]]
        ok = ~np.isnan(d)
        s_ = sc[sg][ok]; d = d[ok]
        n = np.bincount(s_, minlength=ns); m1 = np.bincount(s_, weights=d, minlength=ns); m2 = np.bincount(s_, weights=d * d, minlength=ns)
        keep = n >= MIN_N
        mean = m1[keep] / n[keep]; var = (m2[keep] - n[keep] * mean ** 2) / (n[keep] - 1)
        z = mean / np.sqrt(var / n[keep])
        return np.var(z), keep.sum()
    obs, nst = zvar(sig)
    null = []
    for _ in range(NPERM):
        key = rng.random(len(y))
        o2 = np.lexsort((key, dc))
        sg = np.zeros(len(y), bool)
        sg[o2] = (np.arange(len(y)) - start[dc[o2]]) < nsig[dc[o2]]
        null.append(zvar(sg)[0])
    null = np.array(null)
    return obs, nst, null.mean(), (1 + (null >= obs).sum()) / (NPERM + 1)

def persistence(R):
    x = R[(R.h1_n >= MIN_HALF) & (R.h2_n >= MIN_HALF)]
    rho = stats.spearmanr(x.h1_peer, x.h2_peer).statistic
    a, b = x.h1_peer.rank().to_numpy(), x.h2_peer.rank().to_numpy()
    null = np.array([stats.spearmanr(a, rng.permutation(b)).statistic for _ in range(NPERS)])
    return rho, len(x), (1 + (np.abs(null) >= abs(rho)).sum()) / (NPERS + 1)

RUNS = [('Two down days, then day 3', 'All ordinary days', D2), ('Two down days, then day 3', 'Away from weekends and holidays (Mon..Thu, Friday open)', D2[D2.away]),
        ('Three down days, then day 4', 'All ordinary days', D3), ('Three down days, then day 4', 'No holiday nearby (weekends allowed)', D3[D3.away])]
allR, summ, notable = [], [], []
for sig, ver, X in RUNS:
    R, cut = per_stock(X)
    hv, nst, hnull, hp = heterogeneity(X)
    rho, npers, pp = persistence(R)
    R.insert(0, 'version', ver); R.insert(0, 'signal', sig)
    allR.append(R)
    t = R[R.n >= MIN_N]
    summ.append([sig, ver, f'{len(t)}', f'{int((t.peer > 0).sum())} / {int((t.peer < 0).sum())}', f'{int((t.p_peer_bh < 0.05).sum())}',
                 f'{int((t.p_own_bh < 0.05).sum())}', f'{int(t.confirmed.sum())}', f'{hv:.2f} vs {hnull:.2f} (p {fpv(hp)})',
                 f'{rho:+.2f} ({npers} stocks, p {fpv(pp)})'])
    P(f'{sig} | {ver}: tested {len(t)}; lean down/bounce {int((t.peer > 0).sum())}/{int((t.peer < 0).sum())}; BH peers {int((t.p_peer_bh < 0.05).sum())}; '
      f'BH own {int((t.p_own_bh < 0.05).sum())}; confirmed {int(t.confirmed.sum())}; spread of z {hv:.3f} vs null {hnull:.3f} p {hp:.3f}; '
      f'halves rho {rho:+.3f} n {npers} p {pp:.4f}')
    for r in t[(t.p_peer_bh < 0.05) | (t.p_own_bh < 0.05) | t.confirmed].itertuples():
        notable.append([sig, ver, r.symbol, r.n, pct(r.share_down), pct(r.own_down), sgn(r.peer), fpv(r.p_peer_bh), fpv(r.p_own_bh),
                        f'{sgn(r.h1_peer)} / {sgn(r.h2_peer)}', 'yes' if r.confirmed else 'no'])
A = pd.concat(allR).merge(sec, on='symbol', how='left')
A.to_csv(f'{OUT}/each_stock.csv', index=False, float_format='%.6g')

# one row per stock: all ordinary days, 2D and 3D side by side, plus the away versions' share down
k2a, k2w = (A.signal.str.startswith('Two')) & (A.version == 'All ordinary days'), (A.signal.str.startswith('Two')) & (A.version != 'All ordinary days')
k3a, k3w = (A.signal.str.startswith('Three')) & (A.version == 'All ordinary days'), (A.signal.str.startswith('Three')) & (A.version != 'All ordinary days')
B = A[k2a].set_index('symbol')
B3 = A[k3a].set_index('symbol'); B2w = A[k2w].set_index('symbol'); B3w = A[k3w].set_index('symbol')
rows = []
for s in sorted(set(B.index) | set(B3.index)):
    def cells(T_, s):
        if s not in T_.index:
            return ['-', '-', '-', '-']
        r = T_.loc[s]
        flag = ' *' if (r.n >= MIN_N and (r.p_peer_bh < 0.05 or r.p_own_bh < 0.05)) else ''
        return [f'{int(r.n)}', pct(r.share_down), pct(r.own_down), sgn(r.peer) + flag]
    def away(T_, s):
        return f'{pct(T_.loc[s].share_down)} ({int(T_.loc[s].n)})' if s in T_.index else '-'
    sector = sec.set_index('symbol').nifty_sector.get(s, '-')
    rows.append([s, sector] + cells(B, s) + [away(B2w, s)] + cells(B3, s) + [away(B3w, s)])
full = md(rows, ['Stock', 'Sector', '2D: times', 'Day 3 down', 'Normal', 'vs peers (pts)', 'Day 3 down, away from weekends (times)',
                 '3D: times', 'Day 4 down', 'Normal', 'vs peers (pts)', 'Day 4 down, no holiday nearby (times)'])
st = md(summ, ['Signal', 'Version', 'Stocks tested', 'Lean to keep falling / to bounce', 'Pass BH vs peers', 'Pass BH vs own normal',
               'Confirmed in both halves', 'Spread of stock results vs chance', 'First half vs second half (rank corr.)'])
nt = md(notable, ['Signal', 'Version', 'Stock', 'Times', 'Next day down', 'Normal', 'vs peers (pts)', 'BH q vs peers', 'BH q vs own',
                  'First half / second half', 'Confirmed']) if notable else 'None.'
P(st); P(nt)
open(f'{OUT}/table_each_stock.md', 'w').write(
    '# Two and three down days, stock by stock\n\nPLAN_STOCKS.txt. F&O stocks while in F&O, ordinary days (no result within 5 '
    'sessions, no split/bonus/ex-date), May 2021 .. Sep 2026. "Normal": the stock\'s own share of down days over all its '
    'windows in that sample. "vs peers": the stock\'s next-day share down minus that of the other stocks (without the '
    'signal) on the same dates, in percentage points; negative = a bounce. Stocks with fewer than 30 signal windows are '
    'listed but not tested. BH / Holm: corrected for the number of stocks tested.\n\n## Summary\n\n' + st +
    '\n\nSpread of stock results vs chance: the variance of the per-stock z-scores against 1,000 shuffles of the signal '
    'among stocks on each date (if stocks had their own patterns, the spread would be wider than chance). First half vs '
    'second half: whether the stocks that bounced most in the first half also did in the second (Spearman, permutation p).'
    '\n\n## Stocks that pass a correction in any version\n\n' + nt +
    '\n\n## Every stock (all ordinary days; * = passes BH vs peers or vs its own normal)\n\n' + full + '\n')
open(f'{OUT}/stocks.log', 'w').write('\n'.join(log) + '\n')
