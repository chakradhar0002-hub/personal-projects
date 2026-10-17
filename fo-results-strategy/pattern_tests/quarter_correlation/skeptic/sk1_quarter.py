"""Skeptic checks of the quarter-level build: halves, leave-one-quarter-out, drop 2021, precise p, power, mechanics,
walk-forward forecasts from pre-season variables."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from scipy import stats
from sk_common import *

ev, allev, qq = load()
n = len(qq)
Q, N, S = qq.Q.to_numpy(), qq.N.to_numpy(), qq.S.to_numpy()
V = {c: qq[c].to_numpy() for c in ['nifty_pre20', 'nifty_pre60', 'vix', 'vix_chg20', 'nifty_season', 'sd', 'results',
                                   'best_avg', 'worst_avg', 'spread', 'best_excess', 'worst_excess']}
# timing: is quarter t-1 finished before quarter t's first cutoff?
fc, ld = pd.to_datetime(qq.first_cutoff), pd.to_datetime(qq.last_day_p1)
ok = [(ld[t - 1] < fc[t]) for t in range(1, n)]
print('last Day+1 of t-1 before first cutoff of t:', sum(ok), 'of', n - 1)

def lagpairs(x, k, idx=None):
    idx = range(n) if idx is None else idx
    s = set(idx)
    a = [(x[t], x[t + k]) for t in range(n - k) if t in s and t + k in s]
    a = np.array(a)
    return a[:, 0], a[:, 1]

def fisher_ci(r, m):
    z, se = np.arctanh(r), 1 / np.sqrt(m - 3)
    return np.tanh(z - 1.96 * se), np.tanh(z + 1.96 * se)

rng = np.random.default_rng(777)
def perm_p_pair(a, b, B=200000, sp=False):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if sp: a, b = rk(a), rk(b)
    r = np.corrcoef(a, b)[0, 1]
    sims = np.empty(B)
    bz = (b - b.mean()) / b.std()
    az = (a - a.mean()) / a.std()
    for i in range(0, B, 20000):
        P_ = np.argsort(rng.random((min(20000, B - i), len(a))), axis=1)
        sims[i:i + P_.shape[0]] = (bz[P_] * az).mean(axis=1)
    return r, p2t(r, sims)

def perm_p_lag(x, k, B=200000, sp=False):
    # null: shuffle order of the whole series, recompute lag-k pairs correlation
    x = np.asarray(x, float)
    a, b = x[:-k], x[k:]
    r = np.corrcoef(rk(a), rk(b))[0, 1] if sp else np.corrcoef(a, b)[0, 1]
    sims = np.empty(B)
    for i in range(0, B, 20000):
        m = min(20000, B - i)
        X = x[np.argsort(rng.random((m, len(x))), axis=1)]
        A, Bb = X[:, :-k], X[:, k:]
        if sp:
            A = np.argsort(np.argsort(A, 1), 1).astype(float); Bb = np.argsort(np.argsort(Bb, 1), 1).astype(float)
        A = A - A.mean(1, keepdims=True); Bb = Bb - Bb.mean(1, keepdims=True)
        sims[i:i + m] = (A * Bb).sum(1) / np.sqrt((A * A).sum(1) * (Bb * Bb).sum(1))
    return r, p2t(r, sims), sims.mean()

H1, H2 = list(range(0, 11)), list(range(11, 22))
LATE = list(range(5, 22))
rows = []
def corr_on(a, b, idx):
    idx = list(idx)
    return pear(a[idx], b[idx])

claims = [
    ('Q lag 1', 'lag', Q, 1), ('Q lag 2', 'lag', Q, 2), ('Q lag 4', 'lag', Q, 4), ('S lag 1', 'lag', S, 1),
    ('Q vs N (same-day Nifty)', 'xy', Q, N), ('Q vs Nifty season', 'xy', Q, V['nifty_season']),
    ('Q vs Nifty pre20', 'xy', Q, V['nifty_pre20']), ('Q vs Nifty pre60', 'xy', Q, V['nifty_pre60']),
    ('Q vs VIX', 'xy', Q, V['vix']), ('S vs VIX', 'xy', S, V['vix']), ('S vs pre20', 'xy', S, V['nifty_pre20']),
    ('Q vs sd', 'xy', Q, V['sd']), ('S vs N', 'xy', S, N),
    ('best avg vs worst avg', 'xy', V['best_avg'], V['worst_avg']), ('Q vs worst avg', 'xy', Q, V['worst_avg']),
    ('Q vs best avg', 'xy', Q, V['best_avg']), ('Q vs spread', 'xy', Q, V['spread']),
]
print('\n== headline quarter-level correlations: full, halves, drop 2021 seasons (q0-4), LOO range, Fisher CI, precise p ==')
for name, kind, x, y in claims:
    if kind == 'lag':
        k = y
        a, b = lagpairs(x, k); r = pear(a, b); m = len(a)
        ra = pear(*lagpairs(x, k, H1)); rb = pear(*lagpairs(x, k, H2)); rl = pear(*lagpairs(x, k, LATE))
        loo = []
        for j in range(n):
            idx = [i for i in range(n) if i != j]
            aa, bb = lagpairs(x, k, idx); loo.append((pear(aa, bb), j))
        _, pp, nm = perm_p_lag(x, k, B=200000)
        # null-centred halves
    else:
        r = pear(x, y); m = n
        ra = corr_on(x, y, H1); rb = corr_on(x, y, H2); rl = corr_on(x, y, LATE)
        loo = [(corr_on(x, y, [i for i in range(n) if i != j]), j) for j in range(n)]
        _, pp = perm_p_pair(x, y, B=200000)
    lo, hi = fisher_ci(r, m)
    rmin, rmax = min(loo), max(loo)
    rows.append(dict(claim=name, r=r, n=m, p_precise=pp, ci_lo=lo, ci_hi=hi, half1=ra, half2=rb, drop2021=rl,
                     loo_min=rmin[0], loo_min_drop=qq.period[rmin[1]], loo_max=rmax[0], loo_max_drop=qq.period[rmax[1]]))
R = pd.DataFrame(rows)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
print(R.round(3).to_string(index=False))
R.to_csv(os.path.join(SKOUT, 'sk1_claims.csv'), index=False)

# ---- mechanics of Q vs N
print('\n== mechanics ==')
sdN, sdS = N.std(ddof=1), S.std(ddof=1)
print(f'sd N {sdN:.3f}, sd S {sdS:.3f}, corr(N,S) {pear(N,S):+.2f}')
print(f'corr(Q,N) if S independent of N: {sdN/np.sqrt(sdN**2+sdS**2):+.2f} (observed {pear(Q,N):+.2f})')
print(f'slope of Q on N: {np.polyfit(N,Q,1)[0]:.2f}; mean beta-1 implied by S on N slope {np.polyfit(N,S,1)[0]:+.2f}')
d = V['nifty_season']
print(f'corr(N, season) {pear(N,d):+.2f}; corr(S, season) {pear(S,d):+.2f}')
# partial corr Q vs season given N
rq = Q - np.polyval(np.polyfit(N, Q, 1), N); rd = d - np.polyval(np.polyfit(N, d, 1), N)
r_, p_ = perm_p_pair(rq, rd, B=200000)
print(f'partial corr(Q, season | N) {r_:+.2f}, perm p {fpv(p_)} (approx; residuals shuffled)')
# what share of results-days are within the season window: trivially all
# Results stock beta to Nifty within window, pooled across results
b_res = np.polyfit(ev.n3, ev.td, 1)[0]
print(f'pooled beta of result three-day sums on same-session Nifty three-day sums: {b_res:.2f}')

# ---- power
print('\n== power (n = 22 quarters) ==')
def rho_for_power(m, alpha, power=0.8):
    z = (stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)) / np.sqrt(m - 3)
    return np.tanh(z)
for m, lab in ((22, 'cross corr n=22'), (21, 'lag-1 n=21'), (18, 'lag-4 n=18')):
    print(f'{lab}: |rho| for 80% power at alpha 0.05: {rho_for_power(m,0.05):.2f}; at 0.05/13: {rho_for_power(m,0.05/13):.2f}; '
          f'at 0.05/32: {rho_for_power(m,0.05/32):.2f}; at 0.05/244: {rho_for_power(m,0.05/244):.2f}')
# simulated AR(1) power with permutation test (lag-1 Pearson, twice smaller tail)
rs = np.random.default_rng(99)
print('AR(1) simulation: power of the lag-1 permutation test (400 shuffles per series, 2,000 series)')
for phi in [0.2, 0.3, 0.4, 0.5, 0.6]:
    hits, hitsH = 0, 0
    for s in range(2000):
        e = rs.standard_normal(22 + 50); x = np.zeros_like(e)
        for t in range(1, len(e)): x[t] = phi * x[t - 1] + e[t]
        x = x[50:]
        r = np.corrcoef(x[:-1], x[1:])[0, 1]
        X = x[np.argsort(rs.random((400, 22)), axis=1)]
        A, Bb = X[:, :-1] - X[:, :-1].mean(1, keepdims=True), X[:, 1:] - X[:, 1:].mean(1, keepdims=True)
        sims = (A * Bb).sum(1) / np.sqrt((A * A).sum(1) * (Bb * Bb).sum(1))
        p = p2t(r, sims)
        hits += p < 0.05
        hitsH += r > np.quantile(sims, 1 - 0.05 / 13 / 2)
    print(f'  phi {phi:.1f}: power at p<0.05 {hits/2000:.2f}; at Bonferroni 0.05/13 (approx) {hitsH/2000:.2f}')

# ---- seasonality halves
print('\n== Q by results period, halves ==')
for h, idx in (('q0-10', H1), ('q11-21', H2)):
    sub = qq.iloc[idx]
    print(h, sub.groupby(sub.period.str[:7]).Q.agg(['mean', 'count']).round(2).to_dict())

# ---- walk-forward forecasts
print('\n== walk-forward: fit on quarters before t, predict Q_t (and S_t) ==')
F = pd.DataFrame({'pre20': V['nifty_pre20'], 'pre60': V['nifty_pre60'], 'vix': V['vix'], 'vixchg': V['vix_chg20'],
                  'prevQ': np.r_[np.nan, Q[:-1]], 'prevS': np.r_[np.nan, S[:-1]], 'nres': V['results'],
                  'prevSd': np.r_[np.nan, V['sd'][:-1]]})
per = qq.period.str[:7].to_numpy()
wf = []
for target_name, Y in (('Q', Q), ('S', S)):
    for start in (6, 8):
        tt = list(range(start, n))
        act = Y[tt]
        bench = np.array([Y[:t].mean() for t in tt])
        def summ(name, pred):
            pred = np.asarray(pred)
            hit = np.mean(np.sign(pred) == np.sign(act))
            hit_m = np.mean((pred > bench) == (act > bench))
            sse, sse0 = np.sum((act - pred) ** 2), np.sum((act - bench) ** 2)
            wf.append(dict(target=target_name, start=start, model=name, n=len(tt), hit_sign=hit,
                           hit_vs_mean=hit_m, corr=pear(pred, act), oos_r2=1 - sse / sse0))
        summ('expanding mean', bench)
        summ('always +', np.full(len(tt), 1e-9))
        for f in F.columns:
            pr = []
            for t in tt:
                tr = [i for i in range(t) if not np.isnan(F[f][i])]
                c = np.polyfit(F[f].to_numpy()[tr], Y[tr], 1)
                pr.append(np.polyval(c, F[f][t]))
            summ(f, pr)
        # seasonal: mean of same period earlier (fallback expanding mean)
        pr = []
        for t in tt:
            prev = [Y[i] for i in range(t) if per[i] == per[t]]
            pr.append(np.mean(prev) if prev else Y[:t].mean())
        summ('same-period mean', pr)
        # all pre-season vars together (OLS)
        cols = ['pre20', 'pre60', 'vix', 'vixchg', 'prevQ', 'prevS']
        pr = []
        for t in tt:
            tr = [i for i in range(1, t)]
            Xtr = np.c_[np.ones(len(tr)), F[cols].to_numpy()[tr]]
            beta = np.linalg.lstsq(Xtr, Y[tr], rcond=None)[0]
            pr.append(np.r_[1, F[cols].to_numpy()[t]] @ beta)
        summ('all 6 pre-season vars OLS', pr)
W = pd.DataFrame(wf)
print(W.round(2).to_string(index=False))
W.to_csv(os.path.join(SKOUT, 'sk1_walkforward.csv'), index=False)
print('actual sign of Q, q6-21:', ''.join('+' if v > 0 else '-' for v in Q[6:]), ' positive', int((Q[6:] > 0).sum()), 'of 16')
print('actual sign of Q, q8-21:', ''.join('+' if v > 0 else '-' for v in Q[8:]), ' positive', int((Q[8:] > 0).sum()), 'of 14')
