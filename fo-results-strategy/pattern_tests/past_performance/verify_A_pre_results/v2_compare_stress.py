#!/usr/bin/env python3
"""Verifier: recompute the candidate tests from my own features (my_features.csv.gz), list mismatches against the
authors' signals/trades, and stress the candidates. Writes v2_compare_stress.log and stress.csv in this folder."""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
AUTH = f'{SP}/perf/A_pre_results'
LOG = open(f'{HERE}/v2_compare_stress.log', 'w')
COST = 0.17
rng = np.random.default_rng(424242)


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')
    LOG.flush()


F = pd.read_csv(f'{HERE}/my_features.csv.gz')
F = F[F.td.notna()].reset_index(drop=True)
y = F.td.to_numpy(float)
qn = F.qn.to_numpy(int)
N = len(F)
QS = np.unique(qn)
QIDX = {q: np.flatnonzero(qn == q) for q in QS}
QMEAN = pd.Series(y).groupby(qn).mean()
year = pd.to_datetime(F.results_date).dt.year.to_numpy()
P(f'all F&O results n={N} avg {y.mean():+.3f} first14 {y[qn <= 13].mean():+.3f} last8 {y[qn >= 14].mean():+.3f}')
per = F.groupby('qn').agg(quarter=('quarter', 'first'), period=('period', 'first'))
RF = {q: f'Results for {per.period[q]} ({per.quarter[q]})' for q in QS}

fo = (F.fo == 1).to_numpy()
LAG = fo & (F.vsN21 < -10).to_numpy() & (F.vr >= 1.0).to_numpy()
LAG_ALONE = fo & (F.vsN21 < -10).to_numpy()
VOL_ALONE = fo & (F.vr >= 1.0).to_numpy()
rep = pd.read_csv(__import__('os').environ.get('REPO_ROOT', '.') + '/results/lag10_volume/trades.csv')
s_mine = set(zip(F.symbol[LAG], F.qn[LAG]))
s_rep = set(zip(rep.symbol, rep.qn))
P(f'lag rule: mine n={LAG.sum()} avg {y[LAG].mean():+.3f}; repo n={len(rep)} avg {rep.three_day.mean() * 100:+.3f}; '
  f'same set {s_mine == s_rep}')

MASK = {
    'TR03': (F.n_pos_td4 >= 3).to_numpy(),
    'TR05': (F.pq_mean_td4 > 0.8).to_numpy(),
    'TR12': (F.pq_mean_xn4 > 0.8).to_numpy(),
    'TR11': (F.n_win4 >= 2).to_numpy(),
    'TR15': (F.pq_mean_dr4 > 0.8).to_numpy(),
    'RP1': VOL_ALONE & (F.rk63 <= 20).to_numpy(),
    'LAGRULE': LAG,
    'LAG_ALONE': LAG_ALONE,
    'VOL_ALONE': VOL_ALONE,
}

# ---------------------------------------------------------------- mismatches vs the authors
sig = pd.read_csv(f'{AUTH}/signals_results.csv.gz')
out = pd.read_csv(f'{SP}/perf/features/outcomes.csv', usecols=['symbol', 'qn', 'three_day'])
A = sig.merge(out, on=['symbol', 'qn'])
A = A[A.three_day.notna()]
A = F[['symbol', 'qn']].merge(A, on=['symbol', 'qn'], how='left', validate='1:1')
mism = []
P('\n=== recomputation vs authors (signals_results + outcomes) ===')
for t in ['TR03', 'TR05', 'TR12', 'TR11', 'TR15', 'RP1', 'LAGRULE', 'LAG_ALONE', 'VOL_ALONE']:
    am = A[t].fillna(False).to_numpy(bool)
    mm = MASK[t]
    only_me = F.loc[mm & ~am, ['symbol', 'quarter']].values.tolist()
    only_au = F.loc[am & ~mm, ['symbol', 'quarter']].values.tolist()
    P(f'{t:9s} mine n={mm.sum():4d} avg {y[mm].mean():+.4f} | authors n={am.sum():4d} avg {y[am].mean():+.4f} | '
      f'only mine {len(only_me)} {only_me[:6]} | only authors {len(only_au)} {only_au[:6]}')
    if only_me or only_au or abs(y[mm].mean() - y[am].mean()) > 0.005:
        mism.append(f'{t}: mine n={mm.sum()} avg {y[mm].mean():+.3f} vs authors n={am.sum()} avg {y[am].mean():+.3f}; '
                    f'only mine {only_me[:6]}, only authors {only_au[:6]}')
# outcome check
d = (A.three_day - F.td).abs().max()
P(f'three_day authors outcomes.csv vs events.csv x100: max abs diff {d:.2e}')
# feature value checks
pan = pd.read_csv(f'{SP}/perf/features/panel.csv')
G = F.merge(pan, on=['symbol', 'qn'], how='left', validate='1:1')
for mine, theirs in [('mean_td4', 'mean_three_day_4_A'), ('mean_xn4', 'mean_xn_4_A'), ('n_pos_td4', 'n_pos_three_day_4_A'),
                     ('mean_dr4', 'mean_drift_4_A'), ('n_win4', 'n_winner_4_A'), ('rk63', 'rank_vsN_63_A'),
                     ('rk252', 'rank_vsN_252_A'), ('d52', 'dist_52wh_A'), ('prev1_td', 'prev1_three_day_A')]:
    dd = (G[mine] - G[theirs]).abs()
    nn = (G[mine].isna() != G[theirs].isna()).sum()
    P(f'feature {mine:10s} vs {theirs:22s}: max abs diff {dd.max():.2e}, NaN-pattern differences {nn}')
    if dd.max() > 1e-2 or nn:
        bad = G.loc[(dd > 1e-2) | (G[mine].isna() != G[theirs].isna()), ['symbol', 'quarter', mine, theirs]]
        P(bad.head(8).to_string(index=False))
        mism.append(f'feature {mine} vs {theirs}: max abs diff {dd.max():.3g}, NaN-pattern differences {nn}')


# ---------------------------------------------------------------- statistics helpers
def luck_p(m, B=20000, sign=1):
    obs = sign * y[m].mean()
    nq = pd.Series(qn[m]).value_counts()
    tot = np.zeros(B)
    for q, k in nq.items():
        ix = QIDX[q]
        keys = rng.random((B, len(ix)))
        tot += y[ix][np.argpartition(keys, k - 1, axis=1)[:, :k]].sum(1) if k < len(ix) else y[ix].sum()
    return (1 + (sign * tot / m.sum() >= obs - 1e-12).sum()) / (1 + B)


def excess(m):
    return (y[m] - QMEAN.reindex(qn[m]).to_numpy()).mean()


def summ(name, m, sign=1, lp=True):
    v = sign * y[m]
    h1, h2 = m & (qn <= 13), m & (qn >= 14)
    pq = pd.Series(v - COST).groupby(qn[m]).mean()
    srt = np.sort(v)[::-1]
    r = dict(test=name, n=int(m.sum()), avg=v.mean(), net=v.mean() - COST, excess=sign * excess(m),
             n_h1=int(h1.sum()), avg_h1=sign * y[h1].mean() if h1.any() else np.nan,
             n_h2=int(h2.sum()), avg_h2=sign * y[h2].mean() if h2.any() else np.nan,
             q_pos=int((pq > 0).sum()), q_with=len(pq),
             net_wo5=srt[5:].mean() - COST if len(v) > 5 else np.nan,
             net_wo10=srt[10:].mean() - COST if len(v) > 10 else np.nan,
             median=np.median(v), hit=(v > 0).mean() * 100)
    r['luck_p'] = luck_p(m, sign=sign) if lp else np.nan
    return r


def fmt(r):
    return (f"{r['test']:48s} n={r['n']:4d} avg {r['avg']:+.2f} net {r['net']:+.2f} exc {r['excess']:+.2f} | "
            f"h1 {r['avg_h1']:+.2f} ({r['n_h1']}) h2 {r['avg_h2']:+.2f} ({r['n_h2']}) | q+ {r['q_pos']}/{r['q_with']} | "
            f"w/o5 {r['net_wo5']:+.2f} w/o10 {r['net_wo10']:+.2f} | med {r['median']:+.2f} | luck p {r['luck_p']:.3f}")


ROWS = []


def show(name, m, sign=1, group='', lp=True):
    r = summ(name, m, sign, lp)
    r['group'] = group
    ROWS.append(r)
    P(fmt(r))
    return r


def loqo(name, m):
    vals = []
    for q in np.unique(qn[m]):
        mm = m & (qn != q)
        vals.append((y[mm].mean(), q))
    lo = min(vals)
    hi = max(vals)
    P(f'   LOQO {name}: avg range {lo[0]:+.2f} (drop {RF[lo[1]]}) .. {hi[0]:+.2f} (drop {RF[hi[1]]}); '
      f'net min {lo[0] - COST:+.2f}')
    return lo[0]


def by_year(name, m):
    s = []
    for yr in sorted(np.unique(year)):
        mm = m & (year == yr)
        allm = year == yr
        s.append(f'{yr}: {y[mm].mean():+.2f} ({mm.sum()}; all {y[allm].mean():+.2f})' if mm.any() else f'{yr}: -')
    P(f'   by year {name}: ' + ' | '.join(s))


def per_q(name, m):
    s = []
    for q in QS:
        mm = m & (qn == q)
        if mm.any():
            s.append(f'{q}:{y[mm].mean():+.1f}/{QMEAN[q]:+.1f}({mm.sum()})')
    P(f'   per qn (avg / all F&O) {name}: ' + ' '.join(s))


def drop_q_set(name, m, qset):
    mm = m & ~np.isin(qn, qset)
    P(f'   {name} without qn {qset}: n={mm.sum()} avg {y[mm].mean():+.2f}')


def reg_fe(name, m, controls):
    """OLS of three_day on the signal dummy + controls + quarter fixed effects; HC1 SE (clustered by quarter not
    possible with few clusters, so also report a quarter-cluster SE)."""
    X = [m.astype(float)]
    ok = np.ones(N, bool)
    for c in controls:
        v = F[c].to_numpy(float)
        ok &= np.isfinite(v)
        X.append(v)
    D = pd.get_dummies(pd.Series(qn), prefix='q', drop_first=False).to_numpy(float)
    Xm = np.column_stack(X + [D])[ok]
    yy = y[ok]
    beta, *_ = np.linalg.lstsq(Xm, yy, rcond=None)
    res = yy - Xm @ beta
    XtX = np.linalg.pinv(Xm.T @ Xm)
    # cluster by quarter
    meat = np.zeros((Xm.shape[1], Xm.shape[1]))
    for q in np.unique(qn[ok]):
        s = (Xm[qn[ok] == q] * res[qn[ok] == q, None]).sum(0)
        meat += np.outer(s, s)
    V = XtX @ meat @ XtX
    # also by stock
    sy = F.symbol.to_numpy()[ok]
    meat2 = np.zeros_like(meat)
    for s_ in np.unique(sy):
        s = (Xm[sy == s_] * res[sy == s_, None]).sum(0)
        meat2 += np.outer(s, s)
    V2 = XtX @ meat2 @ XtX
    P(f'   OLS {name} + {controls} + quarter FE: coef {beta[0]:+.3f}, t(cluster quarter) {beta[0] / np.sqrt(V[0, 0]):.2f}, '
      f't(cluster stock) {beta[0] / np.sqrt(V2[0, 0]):.2f}, n={ok.sum()}')


# ---------------------------------------------------------------- candidates
early = F.early.to_numpy(bool)
P('\nsurvivorship: results of symbols in the universe by qn 1:', int(early.sum()), '; later joiners:', int((~early).sum()))

for t in ['TR05', 'TR12', 'TR03']:
    m = MASK[t]
    P(f'\n=== {t} ===')
    show(t, m, group=t)
    loqo(t, m)
    by_year(t, m)
    per_q(t, m)
    srt = np.argsort(-y[m])
    top = F.loc[m].iloc[srt[:5]][['symbol', 'quarter', 'td']]
    P('   best 5 trades:', top.round(2).values.tolist())
    show(f'{t} early symbols (in F&O by qn 1)', m & early, group=t)
    show(f'{t} later joiners', m & ~early, group=t)
    show(f'{t} first 14 (qn<=13)', m & (qn <= 13), group=t, lp=False)
    show(f'{t} last 8 (qn>=14)', m & (qn >= 14), group=t)
    show(f'{t} last 4 quarters (qn 18-21)', m & (qn >= 18), group=t)
    show(f'{t} overlap with lag rule', m & LAG, group=t, lp=False)
    show(f'{t} without lag-rule trades', m & ~LAG, group=t)
    show(f'{t} without any lag21 < -10', m & ~(F.vsN21 < -10).to_numpy(), group=t)
    show(f'{t} without 2023 results', m & (year != 2023), group=t)
    drop_q_set(t, m, [5, 11, 12])
    reg_fe(t, m, [])
    reg_fe(t, m, ['vsN21', 'vsN63', 'vsN252'])

P('\n=== nearby cut-offs: TR05 family (mean 3-day window, long) ===')
for c, thr in [('pq_mean_td4', 0.9), ('pq_mean_td4', 0.85), ('pq_mean_td4', 0.75), ('pq_mean_td4', 0.70),
               ('pq_mean_td4', 0.6667), ('pq_mean_td4', 0.5), ('pq_mean_td3', 0.8), ('pq_mean_td5', 0.8),
               ('pq_mean_td_all', 0.8)]:
    show(f'{c} > {thr}', (F[c] > thr).to_numpy(), group='TR05 nearby')
show('ex-ante: mean_td4 > previous quarter 80th pct', (F.exante_top_mean_td4 == 1).to_numpy(), group='TR05 nearby')
show('mean_td4 > 0 (raw, no rank)', (F.mean_td4 > 0).to_numpy(), group='TR05 nearby')
show('mean_td4 > 2 (raw)', (F.mean_td4 > 2).to_numpy(), group='TR05 nearby')

P('\n=== nearby cut-offs: TR12 family (mean reaction vs Nifty, long) ===')
for c, thr in [('pq_mean_xn4', 0.9), ('pq_mean_xn4', 0.85), ('pq_mean_xn4', 0.75), ('pq_mean_xn4', 0.70),
               ('pq_mean_xn4', 0.5), ('pq_mean_xn3', 0.8), ('pq_mean_xn5', 0.8), ('pq_mean_xn_all', 0.8)]:
    show(f'{c} > {thr}', (F[c] > thr).to_numpy(), group='TR12 nearby')
show('ex-ante: mean_xn4 > previous quarter 80th pct', (F.exante_top_mean_xn4 == 1).to_numpy(), group='TR12 nearby')
show('mean_xn4 > 0 (raw)', (F.mean_xn4 > 0).to_numpy(), group='TR12 nearby')

P('\n=== nearby cut-offs: TR03 family (count of positive windows, long) ===')
for name, m in [('n_pos_td4 == 4', F.n_pos_td4 == 4), ('n_pos_td4 >= 2', F.n_pos_td4 >= 2),
                ('n_pos_td3 >= 2', F.n_pos_td3 >= 2), ('n_pos_td3 == 3', F.n_pos_td3 == 3),
                ('n_pos_td5 >= 4', F.n_pos_td5 >= 4), ('n_pos_td5 >= 3', F.n_pos_td5 >= 3),
                ('n_pos_td6 >= 4', F.n_pos_td6 >= 4), ('n_pos_td6 >= 5', F.n_pos_td6 >= 5),
                ('share_pos_td_all >= 0.75', F.share_pos_td_all >= 0.75),
                ('share_pos_td_all >= 0.6', F.share_pos_td_all >= 0.6)]:
    show(name, m.to_numpy(), group='TR03 nearby')

P('\n=== RP1 (volume >= 1.0 AND 3-month vs Nifty bottom quintile) ===')
m = MASK['RP1']
show('RP1', m, group='RP1')
loqo('RP1', m)
by_year('RP1', m)
per_q('RP1', m)
show('RP1 overlap with lag rule', m & LAG, group='RP1', lp=False)
show('RP1 without lag-rule trades', m & ~LAG, group='RP1')
show('RP1 with lag21 in [-10, -5)', m & (F.vsN21 >= -10).to_numpy() & (F.vsN21 < -5).to_numpy(), group='RP1')
show('RP1 with lag21 >= -5', m & (F.vsN21 >= -5).to_numpy(), group='RP1')
show('RP1 early symbols', m & early, group='RP1')
show('RP1 later joiners', m & ~early, group='RP1')
show('lag rule NOT in RP1', LAG & ~m, group='RP1', lp=False)
for thr in (10, 15, 25, 30):
    show(f'vol>=1.0 & rk63 <= {thr}', VOL_ALONE & (F.rk63 <= thr).to_numpy(), group='RP1 nearby')
    show(f'   same, without lag-rule trades', VOL_ALONE & (F.rk63 <= thr).to_numpy() & ~LAG, group='RP1 nearby')
for v in (0.9, 1.1, 1.2):
    show(f'vol>={v} & rk63 <= 20', fo & (F.vr >= v).to_numpy() & (F.rk63 <= 20).to_numpy(), group='RP1 nearby')
show('vol>=1.0 & rk126 <= 20', VOL_ALONE & (F.rk126 <= 20).to_numpy(), group='RP1 nearby')
show('vol>=1.0 & rk21 <= 20 (1-month instead of 3)', VOL_ALONE & (F.rk21 <= 20).to_numpy(), group='RP1 nearby')
show('vol>=1.0 & vsN63 < -10', VOL_ALONE & (F.vsN63 < -10).to_numpy(), group='RP1 nearby')
show('vol>=1.0 & vsN63 < -10 & lag21 >= -10', VOL_ALONE & (F.vsN63 < -10).to_numpy() & (F.vsN21 >= -10).to_numpy(),
     group='RP1 nearby')
reg_fe('RP1', m, [])
reg_fe('RP1 controlling lag', m, ['vsN21'])
# lag in disguise: does rk63 add anything inside the lag-alone set?
la = LAG_ALONE & F.rk63.notna().to_numpy()
show('lag-alone & rk63 <= 20', la & (F.rk63 <= 20).to_numpy(), group='RP1 lag?', lp=False)
show('lag-alone & rk63 > 20', la & (F.rk63 > 20).to_numpy(), group='RP1 lag?', lp=False)
show('vol-alone & lag21 < -10 & rk63 > 20', VOL_ALONE & LAG_ALONE & (F.rk63 > 20).to_numpy(), group='RP1 lag?', lp=False)
show('vol-alone & lag21 >= -10 & rk63 <= 20', VOL_ALONE & ~LAG_ALONE & (F.rk63 <= 20).to_numpy(), group='RP1 lag?', lp=False)
show('vol-alone & lag21 >= -10 & rk63 > 20', VOL_ALONE & ~LAG_ALONE & (F.rk63 > 20).to_numpy(), group='RP1 lag?', lp=False)
P(f'   corr(rk63, lag21) among volume>=1 results: {np.corrcoef(F.rk63[VOL_ALONE].fillna(50), F.vsN21[VOL_ALONE])[0, 1]:.2f}; '
  f'share of RP1 with lag21 < -10: {LAG_ALONE[m].mean():.2f}; share of lag rule in RP1: {m[LAG].mean():.2f}')

# ---------------------------------------------------------------- within-rule splits (PP12, TR15)
P('\n=== within the lag 10% + volume rule ===')
show('lag rule', LAG, group='rule')
loqo('lag rule', LAG)
by_year('lag rule', LAG)
show('lag rule early symbols', LAG & early, group='rule')
show('lag rule later joiners', LAG & ~early, group='rule')


def split(name, inm, avail, B=20000, nearby=False):
    a = LAG & avail
    yin, yout = y[a & inm], y[a & ~inm]
    diff = yin.mean() - yout.mean()
    ya = y[a]
    k = len(yin)
    keys = rng.random((B, len(ya)))
    sel = np.argsort(keys, axis=1)[:, :k]
    s_in = ya[sel].sum(1)
    dp = s_in / k - (ya.sum() - s_in) / (len(ya) - k)
    p2 = (1 + (np.abs(dp) >= abs(diff) - 1e-12).sum()) / (1 + B)
    h = []
    for hm in (qn <= 13, qn >= 14):
        h.append(f'{y[a & inm & hm].mean():+.2f}({(a & inm & hm).sum()})/{y[a & ~inm & hm].mean():+.2f}({(a & ~inm & hm).sum()})')
    srt = np.sort(yin)[::-1]
    P(f'{name:42s} IN {k:3d} {yin.mean():+.2f} | OUT {len(yout):3d} {yout.mean():+.2f} | diff {diff:+.2f} | '
      f'h1 IN/OUT {h[0]} | h2 IN/OUT {h[1]} | perm p2 {p2:.3f} | IN w/o best 3 {srt[3:].mean():+.2f}')
    return diff, p2


av = np.ones(N, bool)
split('PP12: dist_52wh <= -30', (F.d52 <= -30).to_numpy(), F.d52.notna().to_numpy())
for thr in (-20, -25, -35, -40):
    split(f'   nearby dist_52wh <= {thr}', (F.d52 <= thr).to_numpy(), F.d52.notna().to_numpy())
split('   vsN252 bottom quintile (rk252<=20)', (F.rk252 <= 20).to_numpy(), F.rk252.notna().to_numpy())
split('   vsN63 < -15', (F.vsN63 < -15).to_numpy(), F.vsN63.notna().to_numpy())
split('   lag21 < -15 (deeper 1-month lag)', (F.vsN21 < -15).to_numpy(), av)
split('TR15: mean_dr4 top quintile', (F.pq_mean_dr4 > 0.8).to_numpy(), F.pq_mean_dr4.notna().to_numpy())
for thr in (0.7, 0.75, 0.85, 0.9):
    split(f'   nearby pq_mean_dr4 > {thr}', (F.pq_mean_dr4 > thr).to_numpy(), F.pq_mean_dr4.notna().to_numpy())
split('   mean_dr4 > 0 (raw)', (F.mean_dr4 > 0).to_numpy(), F.mean_dr4.notna().to_numpy())
m15 = LAG & (F.pq_mean_dr4 > 0.8).to_numpy()
P('   TR15-in-rule trades:', F.loc[m15, ['symbol', 'quarter']].assign(td=y[m15].round(2)).values.tolist())
m12 = LAG & (F.d52 <= -30).to_numpy()
P('   PP12-in-rule per qn:', pd.Series(y[m12]).groupby(qn[m12]).agg(['size', 'mean']).round(2).T.to_dict())
show('lag rule & PP12 (d52 <= -30)', m12, group='rule')
loqo('lag rule & PP12', m12)
by_year('lag rule & PP12', m12)
show('lag rule & PP12 early symbols', m12 & early, group='rule', lp=False)
show('lag rule & PP12 later joiners', m12 & ~early, group='rule', lp=False)
show('lag rule & TR15', m15, group='rule')
loqo('lag rule & TR15', m15)
by_year('lag rule & TR15', m15)

pd.DataFrame(ROWS).to_csv(f'{HERE}/stress.csv', index=False, float_format='%.4f')
P('\nMISMATCHES:')
for s in mism:
    P(' -', s)
if not mism:
    P(' none')
