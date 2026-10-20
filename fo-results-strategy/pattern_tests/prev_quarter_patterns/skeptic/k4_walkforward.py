"""k4: walk-forward. Using only quarters before t, pick the best lag / pattern / feature and its direction, apply it in
quarter t (buy or short at the cutoff close, exit at the Day+1 close), 0.17% round-trip cost."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from common import *

F = load(); F['qn'] = F.qn.astype(int)
ICF = [f'h{k}' for k in LAGS] + ['l1_dm1', 'l1_rd', 'l1_dp1', 'n_up4', 'n_up8', 'mean_h2', 'mean_h4', 'mean_h8', 'best4', 'worst4']

# candidate trades: name -> (family, boolean mask over F, side +1 long / -1 short)
C = {}
for f in ICF:
    have = F[f].notna()
    pr = F[have].groupby('qn')[f].rank(pct=True).reindex(F.index)
    lag = f'h{f[1]}' if f.startswith('h') else None
    fam = 'lag' if f.startswith('h') else ('B' if f.startswith('l1') else 'D')
    C[f'{f} top fifth, long'] = (fam, (pr > 0.8).to_numpy(), 1)
    C[f'{f} bottom fifth, long'] = (fam, (pr <= 0.2).to_numpy(), 1)
for k in LAGS:
    h = F[f'h{k}']
    for side in (1, -1):
        C[f'after lag-{k} up, {"long" if side > 0 else "short"}'] = ('lag', (h > 0).to_numpy(), side)
        C[f'after lag-{k} down, {"long" if side > 0 else "short"}'] = ('lag', (h <= 0).to_numpy(), side)
for L in (2, 3, 4):
    for p in sorted(F[f'seq{L}'].dropna().unique()):
        for side in (1, -1):
            C[f'pattern {p}, {"long" if side > 0 else "short"}'] = ('pattern', (F[f'seq{L}'] == p).to_numpy(), side)
for s in (-4, -3, -2, -1, 1, 2, 3, 4):
    for side in (1, -1):
        C[f'streak {s:+d}, {"long" if side > 0 else "short"}'] = ('pattern', (F.streak == s).to_numpy(), side)
names = list(C)
print(f'{len(names)} candidate trades (each feature / pattern in both directions)')
qs = list(range(22))
y = F.y.to_numpy(); x = F.x.to_numpy(); q = F.qn.to_numpy()
# per-quarter mean signed excess and count for every candidate
PQ = np.full((len(names), 22), np.nan); NQ = np.zeros((len(names), 22))
for i, n in enumerate(names):
    fam, m, side = C[n]
    for t in qs:
        mm = m & (q == t)
        NQ[i, t] = mm.sum()
        if mm.sum() >= 5:
            PQ[i, t] = side * x[mm].mean()


def run(fams, lag_train=1, crit='t', min_q=4, label=''):
    idx = [i for i, n in enumerate(names) if C[n][0] in fams]
    trades = []; picks = []
    for t in range(1, 22):
        tr = [s for s in range(0, t - lag_train + 1)]
        best, bv = None, -np.inf
        for i in idx:
            v = PQ[i, tr]; v = v[~np.isnan(v)]
            if len(v) < min_q:
                continue
            sc = v.mean() / (v.std(ddof=1) / np.sqrt(len(v))) if crit == 't' else v.mean()
            if sc > bv:
                best, bv = i, sc
        if best is None:
            continue
        fam, m, side = C[names[best]]
        mm = m & (q == t)
        if mm.sum() == 0:
            continue
        net = side * y[mm] - COST; ex = side * x[mm]
        picks.append((t, names[best], int(mm.sum()), net.mean(), ex.mean()))
        trades += [(t, a, b) for a, b in zip(net, ex)]
    T = pd.DataFrame(trades, columns=['qn', 'net', 'ex'])
    pq = T.groupby('qn').net.mean(); pe = T.groupby('qn').ex.mean()
    tq = pq.mean() / (pq.std(ddof=1) / np.sqrt(len(pq)))
    print(f'\n== {label}: families {fams}, training through t-{lag_train}, pick by {crit}')
    print(f'   {len(pq)} OOS quarters (q{pq.index.min()}-{pq.index.max()}), {len(T)} trades: avg net {T.net.mean():+.2f}%, hit rate (net > 0) '
          f'{(T.net > 0).mean():.0%}, excess over the quarter {T.ex.mean():+.2f}; quarters net > 0: {int((pq > 0).sum())} of {len(pq)}; '
          f'per-quarter mean net {pq.mean():+.2f} (t {tq:+.2f}); per-quarter mean excess {pe.mean():+.2f}')
    for lo, hi in ((0, 13), (14, 21)):
        s = T[(T.qn >= lo) & (T.qn <= hi)]
        print(f'   qn {lo}-{hi}: {len(s)} trades, net {s.net.mean():+.2f}%, excess {s.ex.mean():+.2f}, hit {(s.net > 0).mean():.0%}')
    print('   picks: ' + '; '.join(f'q{t} {n} (n{k}, net {a:+.2f})' for t, n, k, a, e in picks))
    return T


ALL = ('lag', 'B', 'D', 'pattern')
run(('lag',), 1, 't', label='each previous quarter individually (lags 1-8: fifths and up/down sides)')
run(ALL, 1, 't', label='every candidate')
run(ALL, 2, 't', label='every candidate, skip the last quarter in training (no overlap with late reporters)')
run(ALL, 1, 'mean', label='every candidate, pick by training mean (not t)')
run(('D',), 1, 't', label='counts / averages only (track record)')
run(('pattern',), 1, 't', label='sequences and streaks only')
base = F[F.qn >= 5]
print(f'\nbaseline: buy every in_fo result in qn 5-21: {len(base)} trades, net {base.y.mean() - COST:+.2f}%, hit {(base.y - COST > 0).mean():.0%}')
# null: the same 'every candidate' walk-forward on within-quarter shuffled x (and y = x + quarter mean)
rng = np.random.default_rng(4)
qmy = F.groupby('qn').y.mean().reindex(F.qn).to_numpy()
res = []
for b in range(200):
    xs = x.copy()
    for t in qs:
        ii = np.flatnonzero(q == t); xs[ii] = x[rng.permutation(ii)]
    PQs = np.full_like(PQ, np.nan)
    for i, n in enumerate(names):
        fam, m, side = C[n]
        for t in qs:
            mm = m & (q == t)
            if mm.sum() >= 5:
                PQs[i, t] = side * xs[mm].mean()
    tot = []
    for t in range(1, 22):
        best, bv = None, -np.inf
        for i in range(len(names)):
            v = PQs[i, :t]; v = v[~np.isnan(v)]
            if len(v) < 4:
                continue
            sc = v.mean() / (v.std(ddof=1) / np.sqrt(len(v)))
            if sc > bv:
                best, bv = i, sc
        if best is None:
            continue
        fam, m, side = C[names[best]]; mm = m & (q == t)
        tot += list(side * xs[mm])
    res.append(np.mean(tot))
res = np.array(res)
print(f'null (200 within-quarter shuffles), every candidate, pick by t: OOS excess mean {res.mean():+.3f}, sd {res.std():.3f}, 95% range '
      f'{np.quantile(res, 0.025):+.2f} .. {np.quantile(res, 0.975):+.2f}')
