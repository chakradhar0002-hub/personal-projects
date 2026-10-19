"""T1-T5 of PLAN.txt: do EMA / SMA features at the cutoff close correlate with the three-day results move?

    LAB_ROOT=... TA_BUILD=... REPO_ROOT=... python3 -P run_tests.py       (after build_features.py)

Reads OUT/features_events.csv, OUT/features_placebo.csv.gz, OUT/build.log, results/lag10_volume/trades.csv.
Writes into OUT: t1_continuous.csv, table_continuous.md, quintiles.csv, table_quintiles.md, t2_binary.csv,
table_binary.md, table_by_quarter.md, t5_tradable.md (only if something has familywise p < 0.05), run.log.
Every definition is in PLAN.txt (sha256 checked against PLAN.sha256 at start).
"""
import hashlib
import importlib.util
import os

import numpy as np
import pandas as pd
from scipy import stats

REPO = os.environ.get('REPO_ROOT', '.')
LAB = os.environ.get('LAB_ROOT', 'lab')
TA = os.environ.get('TA_BUILD', os.path.join(LAB, 'ta', 'build'))
OUT = os.environ.get('OUT', os.path.join(REPO, 'results', 'ema_sma_3day'))
HERE = os.path.dirname(os.path.abspath(__file__))
LAG10 = os.path.join(REPO, 'results', 'lag10_volume', 'trades.csv')

_spec = importlib.util.spec_from_file_location('ema_sma_build_features', os.path.join(HERE, 'build_features.py'))
_bf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_bf)
CONT, BINARY = _bf.CONT, _bf.BINARY

SEED_PERM, SEED_LUCK = 20261019, 20261020
B_PERM, B_LUCK = 5000, 20000
COST = 0.17
FIRST = list(range(0, 14))
LAST = list(range(14, 22))
QS = list(range(22))

LOG = []
DEVIATIONS = []


def log(msg=''):
    print(msg)
    LOG.append(msg)


# ----------------------------------------------------------------------------------------------- formatting
def fp(x):
    """percent, signed, 2 decimals"""
    return '' if x is None or not np.isfinite(x) else f'{x:+.2f}'


def fc(x):
    """correlation, signed, 3 decimals"""
    return '' if x is None or not np.isfinite(x) else f'{x:+.3f}'


def fpv(p):
    """p value, 3 decimals, '<0.001' below 0.0005"""
    if p is None or not np.isfinite(p):
        return ''
    return '<0.001' if p < 0.0005 else f'{p:.3f}'


def ft(x):
    return '' if x is None or not np.isfinite(x) else f'{x:+.2f}'


def label(f):
    """Plain-language name of a feature."""
    def ma(tok):                                  # 'ema9' -> 'EMA 9'
        return tok[:3].upper() + ' ' + tok[3:]
    p = f.split('_')
    if f.startswith('dist_'):
        return f'Close vs {p[1].upper()} {p[2]}'
    if f.startswith('slope_'):
        return f'{p[1].upper()} {p[2]} slope over 5 days'
    if f.startswith('ema_vs_sma_'):
        return f'EMA {p[3]} vs SMA {p[3]}'
    if f.startswith('spread_'):
        kind, a, b = p[1][:3], p[1][3:], p[2]
        return f'{kind.upper()} {a} vs {kind.upper()} {b}'
    if f.startswith('above_'):
        return f'Close above {p[1].upper()} {p[2]}'
    if f.startswith(('state_', 'xup_', 'xdn_')):
        kind, a, b = p[1][:3], p[1][3:], p[2]
        pair = f'{kind.upper()} {a} {{}} {kind.upper()} {b}'
        if p[0] == 'state':
            return pair.format('above')
        return pair.format('crossed above' if p[0] == 'xup' else 'crossed below') + ' (last 5 days)'
    if f.startswith(('pxup_', 'pxdn_')):
        return f'Close crossed {"above" if p[0] == "pxup" else "below"} {ma(p[1][:-2] + p[1][-2:])} (last 3 days)'
    if f.startswith(('bull_stack_', 'bear_stack_')):
        k = p[2].upper()
        return (f'Close > {k}20 > {k}50 > {k}200' if p[0] == 'bull' else f'Close < {k}20 < {k}50 < {k}200')
    return f


def md_table(df, align=None):
    cols = list(df.columns)
    align = align or ['l'] + ['r'] * (len(cols) - 1)
    out = ['| ' + ' | '.join(cols) + ' |',
           '|' + '|'.join(':---' if a == 'l' else '---:' for a in align) + '|']
    for r in df.itertuples(index=False):
        out.append('| ' + ' | '.join(str(v) for v in r) + ' |')
    return '\n'.join(out)


# ----------------------------------------------------------------------------------------------- statistics
def zrank(v):
    """Standardised average ranks along the last axis (population sd): Spearman = mean(zrank(x) * zrank(y))."""
    r = stats.rankdata(v, axis=-1)
    r = r - r.mean(axis=-1, keepdims=True)
    sd = np.sqrt((r ** 2).mean(axis=-1, keepdims=True))
    with np.errstate(invalid='ignore', divide='ignore'):
        return r / np.where(sd > 0, sd, np.nan)


def holm(p):
    p = np.asarray(p, float)
    out = np.full(len(p), np.nan)
    ok = np.isfinite(p)
    idx = np.flatnonzero(ok)
    if not len(idx):
        return out
    order = idx[np.argsort(p[idx], kind='mergesort')]
    m = len(order)
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (m - rank) * p[i]))
        out[i] = run
    return out


def two_sided(sim, obs, center):
    """(1 + #{|sim - center| >= |obs - center|}) / (1 + B), with a 1e-12 float tolerance."""
    return (1 + np.sum(np.abs(sim - center) >= np.abs(obs - center) - 1e-12)) / (1 + len(sim))


def luck_sums(rng, pool, k, B):
    """Sums of k values picked without replacement from pool, B times (uniform random k-subsets)."""
    N = len(pool)
    if k == 0:
        return np.zeros(B)
    if k == N:
        return np.full(B, pool.sum())
    m = min(k, N - k)
    keys = rng.random((B, N))
    idx = np.argpartition(keys, m - 1, axis=1)[:, :m]
    s = pool[idx].sum(axis=1)
    return s if m == k else pool.sum() - s


def fifths(df, f):
    """Fifth (1 = bottom .. 5 = top) of feature f inside each quarter: floor((average rank - 1) x 5 / n) + 1."""
    lab = np.full(len(df), np.nan)
    qn = df.qn.to_numpy()
    x_all = df[f].to_numpy(float)
    for q in np.unique(qn):
        m = (qn == q) & np.isfinite(x_all)
        if m.any():
            r = stats.rankdata(x_all[m])
            lab[m] = np.floor((r - 1) * 5 / m.sum()) + 1
    return lab


# ----------------------------------------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    plan = os.path.join(HERE, 'PLAN.txt')
    h = hashlib.sha256(open(plan, 'rb').read()).hexdigest()
    rec = open(os.path.join(HERE, 'PLAN.sha256')).read().split()[0]
    log('=== EMA / SMA vs the three-day results move: run log')
    log(f'PLAN.txt sha256 {h}  recorded {rec}  {"MATCH" if h == rec else "MISMATCH"}')
    assert h == rec, 'PLAN.txt changed after registration'
    build_log = open(os.path.join(OUT, 'build.log')).read().rstrip('\n').split('\n')
    for line in build_log:
        if line.startswith('DEVIATION: '):
            DEVIATIONS.append(line[len('DEVIATION: '):])
        else:
            log(line)
    log()
    log('=== run_tests.py')

    fe = pd.read_csv(os.path.join(OUT, 'features_events.csv'))
    pl = pd.read_csv(os.path.join(OUT, 'features_placebo.csv.gz'))
    assert len(fe) == 3278 and sorted(fe.qn.unique()) == QS
    period = fe.groupby('qn').period.first()
    nq = fe.groupby('qn').size()
    qmean = fe.groupby('qn').three_day.mean()
    pl['excess'] = pl.three_day - pl.groupby('qn').three_day.transform('mean')
    plq = pl.groupby('qn').three_day.mean()
    log(f'results: {len(fe)} (qn 0..21), mean three_day {fp(fe.three_day.mean())}%, median {fp(fe.three_day.median())}%, '
        f'sd {fe.three_day.std():.2f}; first 14 q mean {fp(fe[fe.qn < 14].three_day.mean())}%, '
        f'last 8 q {fp(fe[fe.qn >= 14].three_day.mean())}%')
    log(f'placebo: {len(pl)} ordinary F&O stock-days, mean three_day {fp(pl.three_day.mean())}%, seasons with days: '
        f'{pl.qn.nunique()} (min {pl.groupby("qn").size().min()}, max {pl.groupby("qn").size().max()} per season)')
    log('per quarter: qn, period, results, mean three_day (%), placebo days, placebo mean three_day (%)')
    for q in QS:
        log(f'  {q:2d} {period[q]:13s} {nq[q]:4d} {fp(qmean[q]):>6s}   {int((pl.qn == q).sum()):5d} {fp(plq.get(q, np.nan)):>6s}')

    # ======================================================================== T1 continuous
    log()
    log(f'=== T1 continuous: per-quarter Spearman IC, {B_PERM} within-quarter shuffles (seed {SEED_PERM})')
    F = len(CONT)
    rng = np.random.default_rng(SEED_PERM)
    ic_obs = np.full((22, F), np.nan)
    ic_perm = np.full((22, B_PERM, F), np.nan)
    ic_comp = {c: np.full((22, F), np.nan) for c in ('d1', 'd2', 'd3')}
    ic_pl = np.full((22, F), np.nan)
    for q in QS:
        g = fe[fe.qn == q]
        n = len(g)
        y = g.three_day.to_numpy(float)
        X = g[CONT].to_numpy(float)
        perms = rng.permuted(np.tile(np.arange(n), (B_PERM, 1)), axis=1)
        valid = np.isfinite(X)
        full = valid.all(axis=0)
        zy = zrank(y)
        if full.any():
            ZX = zrank(X[:, full].T).T
            ic_obs[q, full] = zy @ ZX / n
            ic_perm[q][:, full] = zy[perms] @ ZX / n
            for c in ic_comp:
                ic_comp[c][q, full] = zrank(g[c].to_numpy(float)) @ ZX / n
        for f in np.flatnonzero(~full):                       # generic path (not used: no NaN features here)
            v = valid[:, f]
            if v.sum() < 3:
                continue
            zx = zrank(X[v, f])
            ic_obs[q, f] = zrank(y[v]) @ zx / v.sum()
            ic_perm[q][:, f] = zrank(y[perms][:, v]) @ zx / v.sum()
            for c in ic_comp:
                ic_comp[c][q, f] = zrank(g[c].to_numpy(float)[v]) @ zx / v.sum()
        # placebo IC over the season's ordinary stock-days
        gp = pl[pl.qn == q]
        if len(gp) >= 3:
            Xp = gp[CONT].to_numpy(float)
            yp = gp.three_day.to_numpy(float)
            for f in range(F):
                v = np.isfinite(Xp[:, f])
                if v.sum() >= 3:
                    ic_pl[q, f] = np.mean(zrank(Xp[v, f]) * zrank(yp[v]))
    # cross-check one value against scipy
    g0 = fe[fe.qn == 0]
    chk = abs(stats.spearmanr(g0[CONT[0]], g0.three_day).statistic - ic_obs[0, 0])
    log(f'IC cross-check vs scipy.spearmanr (qn 0, {CONT[0]}): diff {chk:.1e}')
    assert chk < 1e-10

    def summarise(qs):
        o = np.nanmean(ic_obs[qs], axis=0)
        pm = np.nanmean(ic_perm[qs], axis=0)                 # B x F
        p = np.array([two_sided(pm[:, f], o[f], 0.0) for f in range(F)])
        mx = np.nanmax(np.abs(pm), axis=1)
        pmax = np.array([(1 + np.sum(mx >= abs(o[f]) - 1e-12)) / (1 + B_PERM) for f in range(F)])
        nqv = np.sum(np.isfinite(ic_obs[qs]), axis=0)
        sd = np.nanstd(ic_obs[qs], axis=0, ddof=1)
        t = o / sd * np.sqrt(nqv)
        pos = np.sum(ic_obs[qs] > 0, axis=0)
        z = np.abs(o - pm.mean(axis=0)) / pm.std(axis=0)
        return dict(mean=o, p=p, pmax=pmax, t=t, pos=pos, nq=nqv, z=z)

    A, E1, E2 = summarise(QS), summarise(FIRST), summarise(LAST)
    rows = []
    for j, f in enumerate(CONT):
        x = fe[f].to_numpy(float)
        v = np.isfinite(x)
        rho = stats.spearmanr(x[v], fe.excess.to_numpy(float)[v])
        d = ic_obs[:, j] - ic_pl[:, j]
        dv = d[np.isfinite(d)]
        tt = stats.ttest_1samp(dv, 0.0)
        conf = (E1['pmax'][j] < 0.05) and (np.sign(E2['mean'][j]) == np.sign(E1['mean'][j])) and (E2['p'][j] < 0.05)
        rows.append(dict(
            feature=f, label=label(f), n=int(v.sum()), nan=int((~v).sum()), mean_ic=A['mean'][j], t=A['t'][j],
            q_pos=int(A['pos'][j]), q_n=int(A['nq'][j]), perm_p=A['p'][j], maxt_p=A['pmax'][j], z=A['z'][j],
            pooled_rho_excess=rho.statistic, pooled_rho_p=rho.pvalue,
            ic_first14=E1['mean'][j], p_first14=E1['p'][j], maxt_p_first14=E1['pmax'][j], q_pos_first14=int(E1['pos'][j]),
            ic_last8=E2['mean'][j], p_last8=E2['p'][j], maxt_p_last8=E2['pmax'][j], q_pos_last8=int(E2['pos'][j]),
            placebo_ic=np.nanmean(ic_pl[:, j]), placebo_q_pos=int(np.sum(ic_pl[:, j] > 0)),
            res_minus_placebo=float(np.mean(dv)), res_minus_placebo_p=tt.pvalue,
            ic_d1=np.nanmean(ic_comp['d1'][:, j]), ic_d2=np.nanmean(ic_comp['d2'][:, j]),
            ic_d3=np.nanmean(ic_comp['d3'][:, j]), confirmed='yes' if conf else 'no'))
    t1 = pd.DataFrame(rows)
    t1['_abs'] = t1.mean_ic.abs()
    t1 = t1.sort_values('_abs', ascending=False).drop(columns='_abs').reset_index(drop=True)
    ic_cols = ['mean_ic', 'pooled_rho_excess', 'ic_first14', 'ic_last8', 'placebo_ic', 'res_minus_placebo', 'ic_d1',
               'ic_d2', 'ic_d3']
    p_cols = ['perm_p', 'maxt_p', 'pooled_rho_p', 'p_first14', 'maxt_p_first14', 'p_last8', 'maxt_p_last8',
              'res_minus_placebo_p']
    csv = t1.copy()
    csv[ic_cols] = csv[ic_cols].round(3)
    csv[p_cols] = csv[p_cols].round(4)
    csv[['t', 'z']] = csv[['t', 'z']].round(2)
    csv.to_csv(os.path.join(OUT, 't1_continuous.csv'), index=False)

    log('feature (sorted by |mean IC|): n, mean IC, t, quarters IC>0, perm p, maxT p | pooled rho vs excess (p) | '
        'first 14 q IC (perm p, maxT p) | last 8 q IC (perm p) | placebo IC | results-placebo (p) | IC d1/d2/d3 | conf')
    for r in t1.itertuples():
        log(f'  {r.feature:17s} n={r.n} IC {fc(r.mean_ic)} t {ft(r.t)} pos {r.q_pos}/{r.q_n} p {fpv(r.perm_p)} '
            f'maxT {fpv(r.maxt_p)} | rho {fc(r.pooled_rho_excess)} ({fpv(r.pooled_rho_p)}) | '
            f'{fc(r.ic_first14)} ({fpv(r.p_first14)}, {fpv(r.maxt_p_first14)}) | {fc(r.ic_last8)} ({fpv(r.p_last8)}) | '
            f'{fc(r.placebo_ic)} | {fc(r.res_minus_placebo)} ({fpv(r.res_minus_placebo_p)}) | '
            f'{fc(r.ic_d1)}/{fc(r.ic_d2)}/{fc(r.ic_d3)} | {r.confirmed}')

    tab = pd.DataFrame({
        'Feature': [f'{r.label} (`{r.feature}`)' for r in t1.itertuples()],
        'Results': t1.n.map(lambda v: f'{v:,}'),
        'Mean IC': t1.mean_ic.map(fc), 't': t1.t.map(ft),
        'Quarters IC > 0': [f'{a} of {b}' for a, b in zip(t1.q_pos, t1.q_n)],
        'Perm p': t1.perm_p.map(fpv), 'maxT p (27)': t1.maxt_p.map(fpv),
        'Pooled rho vs excess (p)': [f'{fc(a)} ({fpv(b)})' for a, b in zip(t1.pooled_rho_excess, t1.pooled_rho_p)],
        'IC q0-13 (p)': [f'{fc(a)} ({fpv(b)})' for a, b in zip(t1.ic_first14, t1.p_first14)],
        'maxT p q0-13': t1.maxt_p_first14.map(fpv),
        'IC q14-21 (p)': [f'{fc(a)} ({fpv(b)})' for a, b in zip(t1.ic_last8, t1.p_last8)],
        'Placebo IC': t1.placebo_ic.map(fc),
        'Results - placebo (p)': [f'{fc(a)} ({fpv(b)})' for a, b in zip(t1.res_minus_placebo, t1.res_minus_placebo_p)],
        'Confirmed': t1.confirmed})
    with open(os.path.join(OUT, 'table_continuous.md'), 'w') as fh:
        fh.write('# EMA / SMA continuous features vs the three-day results move\n\n'
                 f'3,278 F&O results, 22 quarters (qn 0 = Jan-Mar 2021 results .. 21 = Apr-Jun 2026). Feature at the '
                 'cutoff close; three_day = Day-1 + Result day + Day+1 returns (gross). IC = Spearman correlation '
                 'inside one quarter; Mean IC = average over the quarters. t = mean / sd x sqrt(quarters). Perm p: '
                 f'{B_PERM:,} within-quarter shuffles, two-sided. maxT p: familywise over all 27 features. Pooled rho: '
                 'Spearman of the feature vs excess (three_day minus the quarter mean) over all results. q0-13 = first '
                 '14 quarters, q14-21 = last 8. Placebo IC: same IC on ordinary F&O stock-days (no results within 10 '
                 'sessions), by results season. Results - placebo: mean of the 22 quarterly differences, one-sample '
                 't-test. Confirmed = maxT p < 0.05 in q0-13 AND same sign with perm p < 0.05 in q14-21. '
                 'Sorted by |Mean IC|. No feature has missing values (every result has >= 205 traded days).\n\n')
        fh.write(md_table(tab) + '\n')

    # ------------------------------------------------------------------ quintiles
    qrows = []
    fifth = {}
    for f in CONT:
        lab = fifths(fe, f)
        fifth[f] = lab
        avg = [fe.three_day[lab == k].mean() for k in range(1, 6)]
        cnt = [int((lab == k).sum()) for k in range(1, 6)]
        qtop = fe.three_day[lab == 5].groupby(fe.qn[lab == 5]).mean()
        qbot = fe.three_day[lab == 1].groupby(fe.qn[lab == 1]).mean()
        both = qtop.index.intersection(qbot.index)
        qrows.append(dict(feature=f, label=label(f), **{f'q{k}': a for k, a in zip(range(1, 6), avg)},
                          **{f'n{k}': c for k, c in zip(range(1, 6), cnt)}, top_minus_bottom=avg[4] - avg[0],
                          q_top_beats_bottom=int((qtop[both] > qbot[both]).sum()), q_n=len(both)))
    quin = pd.DataFrame(qrows).set_index('feature').loc[t1.feature].reset_index()
    c5 = ['q1', 'q2', 'q3', 'q4', 'q5', 'top_minus_bottom']
    qcsv = quin.copy()
    qcsv[c5] = qcsv[c5].round(2)
    qcsv.to_csv(os.path.join(OUT, 'quintiles.csv'), index=False)
    log()
    log('Quintiles (average three_day % by fifth within quarter, bottom .. top; top - bottom; quarters top > bottom):')
    for r in quin.itertuples():
        log(f'  {r.feature:17s} {fp(r.q1)} {fp(r.q2)} {fp(r.q3)} {fp(r.q4)} {fp(r.q5)} | {fp(r.top_minus_bottom)} | '
            f'{r.q_top_beats_bottom}/{r.q_n}  (n {r.n1}/{r.n2}/{r.n3}/{r.n4}/{r.n5})')
    qt = pd.DataFrame({'Feature': [f'{r.label} (`{r.feature}`)' for r in quin.itertuples()],
                       'Bottom fifth': quin.q1.map(fp), '2nd': quin.q2.map(fp), '3rd': quin.q3.map(fp),
                       '4th': quin.q4.map(fp), 'Top fifth': quin.q5.map(fp),
                       'Top - bottom': quin.top_minus_bottom.map(fp),
                       'Quarters top > bottom': [f'{a} of {b}' for a, b in zip(quin.q_top_beats_bottom, quin.q_n)]})
    with open(os.path.join(OUT, 'table_quintiles.md'), 'w') as fh:
        fh.write('# Three-day results move by fifth of each EMA / SMA feature\n\n'
                 'Inside each quarter the feature is cut into fifths (bottom = lowest values); the cells are the '
                 'average three_day (%, gross) of every result in that fifth over all 22 quarters (about 655 results '
                 f'per fifth). All results average {fp(fe.three_day.mean())}%. Sorted like table_continuous.md '
                 '(by |Mean IC|).\n\n')
        fh.write(md_table(qt) + '\n')

    # ======================================================================== T2 binary
    log()
    log(f'=== T2 binary: {B_LUCK} random same-size within-quarter picks (seed {SEED_LUCK})')
    rng = np.random.default_rng(SEED_LUCK)
    brow = []
    bq = {}
    for f in BINARY:
        x = fe[f].to_numpy(float)
        valid = np.isfinite(x)
        sig = valid & (x == 1)
        n_sig = int(sig.sum())
        sums = np.zeros((B_LUCK, 22))
        kq = np.zeros(22, int)
        null_q = np.zeros(22)
        obs_q = np.zeros(22)
        for q in QS:
            mq = (fe.qn == q).to_numpy()
            pool = fe.three_day.to_numpy(float)[mq & valid]
            k = int((mq & sig).sum())
            kq[q] = k
            obs_q[q] = fe.three_day.to_numpy(float)[mq & sig].sum()
            null_q[q] = k * pool.mean() if len(pool) else 0.0
            if k:
                sums[:, q] = luck_sums(rng, pool, k, B_LUCK)

        def luck(qs):
            k = kq[qs].sum()
            if k == 0:
                return np.nan, np.nan, np.nan
            sim = sums[:, qs].sum(axis=1) / k
            obs = obs_q[qs].sum() / k
            nm = null_q[qs].sum() / k
            return two_sided(sim, obs, nm), nm, abs(obs - nm) / sim.std()

        p_all, null_all, z_all = luck(QS)
        p_1, _, _ = luck(FIRST)
        p_2, _, _ = luck(LAST)
        ex = fe.excess.to_numpy(float)
        first = (fe.qn < 14).to_numpy()
        # per quarter signal excess (results and placebo)
        res_q = pd.Series(fe.three_day[sig].groupby(fe.qn[sig]).mean() - qmean).dropna()
        xs = pl[f].to_numpy(float)
        psig = np.isfinite(xs) & (xs == 1)
        pl_q = pd.Series(pl.three_day[psig].groupby(pl.qn[psig]).mean() - plq).dropna()
        both = res_q.index.intersection(pl_q.index)
        dq = (res_q[both] - pl_q[both]).to_numpy()
        tt = stats.ttest_1samp(dq, 0.0) if len(dq) >= 2 else None
        bq[f] = res_q
        dex = {c: (fe[c] - fe.groupby('qn')[c].transform('mean'))[sig].mean() for c in ('d1', 'd2', 'd3')}
        brow.append(dict(
            feature=f, label=label(f), n_sig=n_sig, n_without=int((valid & ~sig).sum()), nan=int((~valid).sum()),
            avg_with=fe.three_day[sig].mean(), avg_without=fe.three_day[valid & ~sig].mean(),
            excess=ex[sig].mean() if n_sig else np.nan,
            q_beat=int((res_q > 0).sum()), q_with=int(len(res_q)), luck_p=p_all, null_mean=null_all, z=z_all,
            n_first14=int((sig & first).sum()), excess_first14=ex[sig & first].mean() if (sig & first).any() else np.nan,
            p_first14=p_1, n_last8=int((sig & ~first).sum()),
            excess_last8=ex[sig & ~first].mean() if (sig & ~first).any() else np.nan, p_last8=p_2,
            placebo_n=int(psig.sum()), placebo_diff=pl.excess[psig].mean() if psig.any() else np.nan,
            res_minus_placebo=float(np.mean(dq)) if len(dq) else np.nan,
            res_minus_placebo_p=tt.pvalue if tt is not None else np.nan, res_minus_placebo_q=int(len(dq)),
            excess_d1=dex['d1'], excess_d2=dex['d2'], excess_d3=dex['d3']))
    t2 = pd.DataFrame(brow)
    t2['holm_p'] = holm(t2.luck_p)
    t2['holm_p_first14'] = holm(t2.p_first14)
    t2['confirmed'] = np.where((t2.holm_p_first14 < 0.05) & (np.sign(t2.excess_last8) == np.sign(t2.excess_first14))
                               & (t2.p_last8 < 0.05), 'yes', 'no')
    t2 = t2.sort_values(['luck_p', 'z'], ascending=[True, False]).reset_index(drop=True)
    pc = ['avg_with', 'avg_without', 'excess', 'null_mean', 'excess_first14', 'excess_last8', 'placebo_diff',
          'res_minus_placebo', 'excess_d1', 'excess_d2', 'excess_d3']
    pp = ['luck_p', 'holm_p', 'p_first14', 'holm_p_first14', 'p_last8', 'res_minus_placebo_p']
    csv = t2.copy()
    csv[pc] = csv[pc].round(2)
    csv[pp] = csv[pp].round(4)
    csv['z'] = csv.z.round(2)
    csv.to_csv(os.path.join(OUT, 't2_binary.csv'), index=False)
    log('feature (sorted by luck p): n with, avg with / without, excess, quarters beating all, luck p, Holm p | '
        'first 14 q excess (p, Holm) | last 8 q excess (p) | placebo diff (n) | results-placebo (p, quarters) | '
        'excess d1/d2/d3 | conf')
    for r in t2.itertuples():
        log(f'  {r.feature:17s} n={r.n_sig:4d} {fp(r.avg_with)} / {fp(r.avg_without)} ex {fp(r.excess)} beat '
            f'{r.q_beat}/{r.q_with} p {fpv(r.luck_p)} Holm {fpv(r.holm_p)} | {fp(r.excess_first14)} n={r.n_first14} '
            f'({fpv(r.p_first14)}, {fpv(r.holm_p_first14)}) | {fp(r.excess_last8)} n={r.n_last8} ({fpv(r.p_last8)}) | '
            f'{fp(r.placebo_diff)} (n={r.placebo_n}) | {fp(r.res_minus_placebo)} ({fpv(r.res_minus_placebo_p)}, '
            f'{r.res_minus_placebo_q} q) | {fp(r.excess_d1)}/{fp(r.excess_d2)}/{fp(r.excess_d3)} | {r.confirmed}')
    tb = pd.DataFrame({
        'Signal': [f'{r.label} (`{r.feature}`)' for r in t2.itertuples()],
        'Results with signal': t2.n_sig.map(lambda v: f'{v:,}'),
        'Avg with': t2.avg_with.map(fp), 'Avg without': t2.avg_without.map(fp), 'Excess': t2.excess.map(fp),
        'Quarters beating all results': [f'{a} of {b}' for a, b in zip(t2.q_beat, t2.q_with)],
        'Luck p': t2.luck_p.map(fpv), 'Holm p (32)': t2.holm_p.map(fpv),
        'q0-13 excess (p)': [f'{fp(a)} ({fpv(b)})' for a, b in zip(t2.excess_first14, t2.p_first14)],
        'Holm p q0-13': t2.holm_p_first14.map(fpv),
        'q14-21 excess (p)': [f'{fp(a)} ({fpv(b)})' for a, b in zip(t2.excess_last8, t2.p_last8)],
        'Placebo diff': t2.placebo_diff.map(fp),
        'Results - placebo (p)': [f'{fp(a)} ({fpv(b)})' for a, b in zip(t2.res_minus_placebo, t2.res_minus_placebo_p)],
        'Confirmed': t2.confirmed})
    with open(os.path.join(OUT, 'table_binary.md'), 'w') as fh:
        fh.write('# EMA / SMA yes/no signals vs the three-day results move\n\n'
                 '3,278 F&O results, 22 quarters. Avg with / without = average three_day (%, gross) of results with / '
                 'without the signal at the cutoff close. Excess = signal results minus the same-quarter average of all '
                 'results. Quarters beating all results = quarters where the signal group averaged more than all '
                 f'results (of quarters with the signal). Luck p: {B_LUCK:,} random picks of the same number of results '
                 'inside each quarter, two-sided. Holm p: adjusted over the 32 signals. q0-13 / q14-21: first 14 / '
                 'last 8 quarters. Placebo diff: the signal\'s excess on ordinary F&O stock-days (no results within 10 '
                 'sessions). Results - placebo: per quarter (results excess - placebo excess), averaged, one-sample '
                 't-test. Confirmed = Holm p < 0.05 in q0-13 AND same sign with luck p < 0.05 in q14-21. Sorted by '
                 'luck p. "Crossed" signals look back 5 traded days (MA pairs) or 3 (close vs MA20).\n\n')
        fh.write(md_table(tb) + '\n')

    rc = fe[CONT].rank().corr().abs().to_numpy()
    off = rc[np.triu_indices(len(CONT), 1)]
    log(f'(extra, descriptive) |pooled Spearman| between the 27 continuous features: median {np.median(off):.3f}, '
        f'share above 0.5: {100 * np.mean(off > 0.5):.0f}% (they mostly measure one thing: how far the price has run)')
    DEVIATIONS.append('Addition (descriptive, not in PLAN.txt): run.log prints the pooled rank correlation between the '
                      '27 continuous features, to show they are not 27 independent tests.')

    # ======================================================================== T3 summary
    log()
    log('=== T3 confirmation (first 14 quarters familywise p < 0.05 AND last 8 same sign with p < 0.05)')
    log(f'  continuous: {int((t1.confirmed == "yes").sum())} of {len(t1)} confirmed; maxT p < 0.05 in q0-13: '
        f'{int((t1.maxt_p_first14 < 0.05).sum())}; perm p < 0.05 in q14-21: {int((t1.p_last8 < 0.05).sum())}')
    log(f'  binary    : {int((t2.confirmed == "yes").sum())} of {len(t2)} confirmed; Holm p < 0.05 in q0-13: '
        f'{int((t2.holm_p_first14 < 0.05).sum())}; luck p < 0.05 in q14-21: {int((t2.p_last8 < 0.05).sum())}')
    log(f'  unadjusted p < 0.05 over all 22 quarters: continuous {int((t1.perm_p < 0.05).sum())} of 27 '
        f'(expected by chance ~1.4), binary {int((t2.luck_p < 0.05).sum())} of 32 (~1.6)')
    log(f'  familywise p < 0.05 over all 22 quarters: continuous (maxT) {int((t1.maxt_p < 0.05).sum())}, '
        f'binary (Holm) {int((t2.holm_p < 0.05).sum())}')
    sm = t2[t2.feature == 'state_sma50_200'].iloc[0]
    log(f'  cross-check with docs/TECHNICAL_ANALYSIS.md: golden-cross state (state_sma50_200) {sm.n_sig} results, '
        f'avg {fp(sm.avg_with)}% (doc: 2,070 trades, +0.05%)')

    # ======================================================================== by-quarter table
    cand = pd.concat([pd.DataFrame({'feature': t1.feature, 'p': t1.perm_p, 'z': t1.z, 'kind': 'cont'}),
                      pd.DataFrame({'feature': t2.feature, 'p': t2.luck_p, 'z': t2.z, 'kind': 'bin'})])
    top6 = cand.sort_values(['p', 'z'], ascending=[True, False]).head(6)
    log()
    log('=== 6 strongest features by overall p (ties by |z|): '
        + ', '.join(f'{r.feature} (p {fpv(r.p)}, z {r.z:.2f})' for r in top6.itertuples()))
    cols = {}
    head = []
    for r in top6.itertuples():
        if r.kind == 'cont':
            j = CONT.index(r.feature)
            cols[r.feature] = [fc(ic_obs[q, j]) for q in QS]
            row = t1[t1.feature == r.feature].iloc[0]
            cols[r.feature] += [fc(row.mean_ic), f'{row.q_pos} of {row.q_n}', fpv(row.perm_p)]
            head.append(f'{label(r.feature)} (`{r.feature}`): IC')
        else:
            s = bq[r.feature]
            ns = fe[fe[r.feature] == 1].groupby('qn').size()
            cols[r.feature] = [f'{fp(s[q])} ({int(ns[q])})' if q in s.index else '- (0)' for q in QS]
            row = t2[t2.feature == r.feature].iloc[0]
            cols[r.feature] += [fp(row.excess), f'{row.q_beat} of {row.q_with}', fpv(row.luck_p)]
            head.append(f'{label(r.feature)} (`{r.feature}`): excess % (n)')
    bt = pd.DataFrame({'Quarter': [f'{q} {period[q]}' for q in QS] + ['All 22 quarters', 'Quarters positive', 'p'],
                       'Results': [str(nq[q]) for q in QS] + [f'{len(fe):,}', '', ''],
                       'Avg three_day': [fp(qmean[q]) for q in QS] + [fp(fe.three_day.mean()), '', '']})
    for hname, f in zip(head, top6.feature):
        bt[hname] = cols[f]
    with open(os.path.join(OUT, 'table_by_quarter.md'), 'w') as fh:
        conf6 = [f for f in top6.feature
                 if (t1.loc[t1.feature == f, 'confirmed'].tolist() + t2.loc[t2.feature == f, 'confirmed'].tolist())[0]
                 == 'yes']
        fam6 = [f for f in top6.feature if (t1.loc[t1.feature == f, 'maxt_p'].tolist()
                                             + t2.loc[t2.feature == f, 'holm_p'].tolist())[0] < 0.05]
        fh.write('# The 6 strongest EMA / SMA features, quarter by quarter\n\n'
                 'Chosen by the smallest overall p (permutation p for continuous features, luck p for yes/no signals) '
                 f'out of all 59. Confirmed by the split rule: {", ".join(conf6) if conf6 else "none"}. Familywise '
                 f'p < 0.05 over all 22 quarters: {", ".join(fam6) if fam6 else "none"}. Continuous: '
                 'Spearman IC between the feature and three_day inside the quarter (positive = higher feature, higher '
                 'three-day move). Yes/no: average three_day of results with the signal minus the average of all '
                 'results that quarter (%), with the number of signal results in brackets. The "All 22 quarters" row '
                 'is the mean IC / the trade-weighted excess.\n\n')
        fh.write(md_table(bt) + '\n')
    log('quarterly values of the 6 strongest written to table_by_quarter.md:')
    for line in md_table(bt).split('\n'):
        log('  ' + line)

    # ======================================================================== T5 tradable
    log()
    sig_c = t1[t1.maxt_p < 0.05]
    sig_b = t2[t2.holm_p < 0.05]
    t5_path = os.path.join(OUT, 't5_tradable.md')
    if len(sig_c) + len(sig_b) == 0:
        log('=== T5: nothing has familywise p < 0.05 over all 22 quarters (maxT for continuous, Holm for binary); '
            't5_tradable.md not written.')
        if os.path.exists(t5_path):
            os.remove(t5_path)
    else:
        lag = pd.read_csv(LAG10)
        lagkey = set(zip(lag.symbol, lag.qn))
        parts = ['# Tradable versions of features with familywise p < 0.05\n',
                 f'Cost {COST}% a round trip. Buy (or short) at the cutoff close, exit at the Day+1 close.\n']
        log('=== T5 tradable (familywise p < 0.05 overall)')
        items = [(r.feature, 'cont', r.mean_ic) for r in sig_c.itertuples()] + \
                [(r.feature, 'bin', r.excess) for r in sig_b.itertuples()]
        for f, kind, sgn in items:
            if kind == 'cont':
                lab = fifth[f]
                m = lab == (5 if sgn > 0 else 1)
                desc = f'long the {"top" if sgn > 0 else "bottom"} fifth of {f}'
                side = 1.0
            else:
                m = (fe[f] == 1).to_numpy()
                side = 1.0 if sgn > 0 else -1.0
                desc = f'{"long" if side > 0 else "short"} results with {f}'
            tr = fe[m].copy()
            tr['gross'] = side * tr.three_day
            tr['net'] = side * tr.three_day - COST
            tr['lag10'] = [(s, q) in lagkey for s, q in zip(tr.symbol, tr.qn)]
            per_q = tr.groupby('qn').net.agg(['size', 'mean'])
            no5 = tr.net.sort_values(ascending=False).iloc[5:].mean()
            nolag = tr[~tr.lag10].net
            fq, lq = tr[tr.qn < 14].net.mean(), tr[tr.qn >= 14].net.mean()
            # extra (not in PLAN.txt, descriptive): the same rule on ordinary F&O stock-days (placebo)
            if kind == 'cont':
                pm = fifths(pl, f) == (5 if sgn > 0 else 1)
            else:
                pm = (pl[f] == 1).to_numpy()
            pnet = side * pl.three_day[pm] - COST
            pall = side * pl.three_day - COST
            pmsg = (f'same rule on ordinary days (placebo, extra): {int(pm.sum()):,} stock-days, avg net '
                    f'{fp(pnet.mean())}% (all ordinary days, same side, net {fp(pall.mean())}%); results minus '
                    f'placebo {fp(tr.net.mean() - pnet.mean())}%')
            msg = (f'{desc}: {len(tr)} trades, avg gross {fp(tr.gross.mean())}%, avg net {fp(tr.net.mean())}%, '
                   f'win rate {100 * (tr.net > 0).mean():.1f}%, '
                   f'quarters positive {int((per_q["mean"] > 0).sum())} of {len(per_q)}, first 14 q {fp(fq)}%, '
                   f'last 8 q {fp(lq)}%, without the 5 best trades {fp(no5)}%, without the {int(tr.lag10.sum())} '
                   f'lag 10% + volume trades: {len(nolag)} trades {fp(nolag.mean())}%')
            log('  ' + msg)
            log('    ' + pmsg)
            parts.append(f'\n## {label(f)} (`{f}`)\n\n{msg}\n\n{pmsg[0].upper() + pmsg[1:]}.\n\n')
            pq = pd.DataFrame({'Quarter': [f'{q} {period[q]}' for q in per_q.index],
                               'Trades': per_q['size'].astype(int).astype(str), 'Avg net %': per_q['mean'].map(fp)})
            parts.append(md_table(pq) + '\n')
        with open(t5_path, 'w') as fh:
            fh.write('\n'.join(parts))
        DEVIATIONS.append('Addition (descriptive, not in PLAN.txt): T5 also shows the same tradable rule on the '
                          'ordinary-day placebo (fifths cut within each results season), to show whether the tradable '
                          'version is specific to results.')

    # ======================================================================== deviations
    log()
    log('=== DEVIATIONS from PLAN.txt')
    if not DEVIATIONS:
        log('  none')
    for i, d in enumerate(DEVIATIONS, 1):
        log(f'  {i}. {d}')
    with open(os.path.join(OUT, 'run.log'), 'w') as fh:
        fh.write('\n'.join(LOG) + '\n')


if __name__ == '__main__':
    main()
