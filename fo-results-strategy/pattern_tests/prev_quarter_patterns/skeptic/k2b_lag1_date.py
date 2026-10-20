"""k2b: is the lag-1 momentum-then-reversal (and lag 3 / track record) stock-specific? Demean BOTH sides by cutoff date,
and by sector within quarter; per-quarter view; max-over-breakpoints check of the after-the-fact split."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from common import *
F = load(); F['qn'] = F.qn.astype(int)
ev = pd.read_csv(os.path.join(D, 'events.csv'))
E = ev[ev.three_day.notna()].copy(); E['td'] = E.three_day * 100
g = E.groupby('i_cut').td
E['n'] = g.transform('size'); E['hdd'] = np.where(E.n >= 2, (E.td - g.transform('sum') / E.n) * E.n / (E.n - 1), np.nan)  # minus mean of OTHER events same cutoff
E['hsec'] = E.td - E.groupby(['qn', 'sector_index']).td.transform('mean')
k = E.set_index(['symbol', 'qn'])
for kk in range(1, 9):
    key = pd.MultiIndex.from_arrays([F.symbol, F.qn - kk])
    F[f'hdd{kk}'] = k.hdd.reindex(key).to_numpy(); F[f'hsec{kk}'] = k.hsec.reindex(key).to_numpy()
F['ysec'] = F.y - F.groupby(['qn', 'sector_index']).y.transform('mean')
print('sector groups per quarter (median)', F.groupby('qn').sector_index.nunique().median())
for nm, f, y in [('x vs h1 (build)', 'h1', 'x'), ('y_dd_all vs h1', 'h1', 'y_dd_all'), ('y_dd_all vs hdd1 (both date-demeaned)', 'hdd1', 'y_dd_all'),
                 ('ysec vs hsec1 (both sector-demeaned)', 'hsec1', 'ysec')]:
    ics = ic_q(F, f, y)
    o, nl, _ = perm_ic_multi(F, [f], y, B=2000, seed=5)
    v = {q: c for q, c, _ in ics}
    seg = lambda lo, hi: np.array([v[q] for q in v if lo <= q <= hi])
    s = ' | '.join(f'qn {lo}-{hi} {seg(lo, hi).mean():+.3f} neg {int((seg(lo, hi) < 0).sum())}/{len(seg(lo, hi))}' for lo, hi in ((1, 7), (8, 21), (14, 21)))
    print(f'{nm:42s}: all {summ(ics)[0]:+.3f} p {fpv(two_sided(nl[:, 0], o[0]))} | {s}')
    print('    per quarter: ' + ' '.join(f'{q}:{c:+.2f}' for q, c in v.items()))
# lags 1..8 both sides date-demeaned
print('\nall lags, both sides date-demeaned (IC, p, first 14 q / last 8 q):')
o, nl, _ = perm_ic_multi(F, [f'hdd{kk}' for kk in range(1, 9)], 'y_dd_all', B=2000, seed=6)
mt = maxT(nl, o)
for kk in range(1, 9):
    ics = ic_q(F, f'hdd{kk}', 'y_dd_all')
    a = summ([c for c in ics if c[0] <= 13]); b = summ([c for c in ics if c[0] >= 14])
    print(f'  lag {kk}: {o[kk - 1]:+.3f} p {fpv(two_sided(nl[:, kk - 1], o[kk - 1]))} maxT {mt[kk - 1]:.3f} | {a[0]:+.3f} / {b[0]:+.3f}')
# track record with date-demeaned history
H = np.column_stack([F[f'hdd{kk}'] for kk in range(1, 5)])
F['mean_hdd4'] = np.where(~np.isnan(H).any(1), H.mean(1), np.nan); F['best_hdd4'] = np.where(~np.isnan(H).any(1), np.nanmax(H, 1), np.nan)
for f in ('mean_hdd4', 'best_hdd4'):
    o, nl, _ = perm_ic_multi(F, [f], 'y_dd_all', B=2000, seed=8)
    ics = ic_q(F, f, 'y_dd_all')
    print(f'{f} vs y_dd_all: IC {o[0]:+.3f} p {fpv(two_sided(nl[:, 0], o[0]))} n {summ(ics)[4]} | first {summ([c for c in ics if c[0] <= 13])[0]:+.3f} last {summ([c for c in ics if c[0] >= 14])[0]:+.3f}')

# breakpoint search: how unusual is "a run of >= 13 of 14 same-sign quarters at the end after choosing the break"?
print('\nafter-the-fact split: null distribution of max over breakpoints b (3..18) of |mean IC after b| / se, within-quarter shuffles')
rng = np.random.default_rng(3)
qs = sorted(F.qn.unique())[1:]
obs_ics = np.array([c for _, c, _ in ic_q(F, 'h1', 'x')])
def stat(v):
    best = 0
    for b in range(3, 19):
        seg = v[b - 1:]
        best = max(best, abs(seg.mean()) / (seg.std(ddof=1) / np.sqrt(len(seg))))
    return best
o_stat = stat(obs_ics)
_, nl, _ = perm_ic_multi(F, ['h1'], 'x', B=1, seed=1)
# per-quarter permutation ICs
null_stats = []
sub = F[F.h1.notna()]
groups = {q: s for q, s in sub.groupby('qn')}
for b in range(1000):
    v = []
    for q in qs:
        s = groups[q]; a = rank(s.h1.to_numpy()); yy = rank(rng.permutation(s.x.to_numpy()))
        v.append(np.corrcoef(a, yy)[0, 1])
    null_stats.append(stat(np.array(v)))
null_stats = np.array(null_stats)
print(f'  observed max |t| of a tail segment {o_stat:.2f}; null 95th pct {np.quantile(null_stats, 0.95):.2f}; p {(1 + (null_stats >= o_stat).sum()) / 1001:.3f}')
# sign-run: longest run of negative ICs ending at the last quarter, allowing one exception
