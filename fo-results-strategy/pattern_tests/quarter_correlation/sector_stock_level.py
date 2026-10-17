#!/usr/bin/env python3
"""Do good and bad results seasons, and best and worst sectors, carry over? Sector- and stock-level checks.

Universe: the 3,278 results of stocks in F&O at the time (events.csv in_fo == True), 22 seasons (qn 0 = results for
Jan-Mar 2021 ... qn 21 = Apr-Jun 2026). three_day = ret_dm1 + ret_rd + ret_dp1 (sum, not compounded), in %.
Q_t = mean three-day sum of all F&O results in quarter t. Sector excess e(s,t) = sector s's average in quarter t minus
Q_t. Best / worst sector of a quarter: highest / lowest sector average among sectors with at least 4 results that
quarter (as in results/nifty_sector_3day/table_quarter_leaders.md).

1. Sector persistence: Spearman rank correlation of e(s,t) and e(s,t+L) over sectors with >= 4 results in both
   quarters, averaged over the quarter pairs (L = 1: 21 pairs; L = 4, same results period a year later: 18 pairs),
   and the pooled weighted regression slope of e(s,t+L) on e(s,t) (weight n1*n2/(n1+n2), the inverse of the
   sampling variance of a difference of two cell means up to a constant). Null: B within-quarter shuffles of the
   results across the sector labels (every cell keeps its size), two-sided permutation p.
2. Transitions of the best and the worst sector into the next quarter (rank percentile, excess, best/worst counts)
   against the same shuffle null.
3. Cross-sector correlation of e(s,t) over quarters for sectors with >= 4 results in at least 18 of 22 quarters;
   pair p = share of shuffles whose r is at least as far from the pair's null mean as the observed r (two-sided, as
   p2); familywise p = share of shuffles whose largest such distance over all pairs reaches the observed one
   (single-step maxT).
4. Item 1 for the members of the 13 Nifty sectoral indices with F&O members, outcome = member excess vs its own index
   (index_member_results.csv). Memberships overlap (a bank can be in Nifty Bank, Private Bank and Financial Services).
   Null: within each quarter the distinct member results are permuted over the member "slots": result r' takes over
   every index membership of result r, and its excess vs each of those indices is recomputed from index_close.csv on
   r''s own three sessions. This keeps every index's member count and the overlap pattern between indices.
5. Stock level: x = three_day - Q_t. Pooled correlation of a stock's x in quarter t and t+1 (and t+4). Null A: B
   shuffles of each stock's quarter order (within stock; keeps each stock's own average, so it tests carry-over
   beyond a permanent stock effect). Null B: within-quarter shuffle of x across stocks (no persistence at all).
   Quintiles of x in quarter t -> average x at the next result (quarter t+1), random-pick null (within-quarter
   shuffle of next-quarter x among stocks with results in both quarters). Plus the last-4 track record of
   docs/PAST_PERFORMANCE.md rebuilt for comparison.

Holm within each item's family (listed in s_table_tests.md). Sector checks are done for the NSE index sectors
(nifty_sector, 18 sectors) and the headline statistics are repeated for the custom 15 sectors (custom_sector).
Reads LAB_ROOT/sector_lab/data and REPO_ROOT/results/nifty_sector_3day; writes s_* files in OUT (default
REPO_ROOT/results/quarter_correlation).
"""
import os
import numpy as np
import pandas as pd

REPO = os.environ.get('REPO_ROOT', '.')
LAB = os.environ.get('LAB_ROOT', 'lab')
OUT = os.environ.get('OUT', os.path.join(REPO, 'results', 'quarter_correlation'))
D = f'{LAB}/sector_lab/data'
NS = os.path.join(REPO, 'results', 'nifty_sector_3day')
OLDQL = os.path.join(REPO, 'results', 'sector_3day', 'quarter_leaders.csv')
os.makedirs(OUT, exist_ok=True)
B = 2000            # shuffles per null
MIN_N = 4           # sector / index counted in a quarter only with at least this many results
MIN_Q = 18          # item 3: sectors with >= MIN_N results in at least this many quarters
NQ = 22
SEEDS = dict(sector=20261017, index=20261018, stock_within=20261019, stock_across=20261020, quint=20261021,
             last4=20261022)

SHORT = {'Financial Services': 'Fin services', 'Capital Goods': 'Cap goods', 'Automobile and Auto Components': 'Auto',
         'Healthcare': 'Healthcare', 'Information Technology': 'IT', 'Fast Moving Consumer Goods': 'FMCG',
         'Metals & Mining': 'Metals', 'Consumer Durables': 'Cons dur', 'Consumer Services': 'Cons services',
         'Oil Gas & Consumable Fuels': 'Oil & gas', 'Power': 'Power', 'Realty': 'Realty', 'Services': 'Services',
         'Chemicals': 'Chemicals', 'Construction Materials': 'Constr mat', 'Telecommunication': 'Telecom',
         'Construction': 'Construction', 'Textiles': 'Textiles'}
OLD_SHORT = {'Banks': 'Banks', 'NBFC & financials': 'NBFC/Fin', 'IT': 'IT', 'Pharma & healthcare': 'Pharma',
             'Auto & auto parts': 'Auto', 'Capital goods & defence': 'Cap goods', 'Real estate & construction': 'Realty',
             'Cement & building materials': 'Cement', 'Metals & mining': 'Metals', 'Oil & gas': 'Oil & gas',
             'Power': 'Power', 'FMCG': 'FMCG', 'Consumer durables & retail': 'Cons dur', 'Chemicals & agro': 'Chem/agro',
             'Services, telecom & internet': 'Services'}
IDX_SHORT = {'Nifty Auto': 'Auto', 'Nifty Bank': 'Bank', 'Nifty Financial Services': 'Fin Serv', 'Nifty FMCG': 'FMCG',
             'Nifty Healthcare Index': 'Healthcare', 'Nifty IT': 'IT', 'Nifty Metal': 'Metal', 'Nifty Pharma': 'Pharma',
             'Nifty PSU Bank': 'PSU Bank', 'Nifty Private Bank': 'Pvt Bank', 'Nifty Realty': 'Realty',
             'Nifty Consumer Durables': 'Cons Dur', 'Nifty Oil & Gas': 'Oil & Gas'}

log = []
def P(*a):
    s = ' '.join(str(x) for x in a)
    log.append(s)
    print(s)

def fp(v):      # percent values and correlations: signed, 2 decimals
    return '-' if v is None or pd.isna(v) else f'{v:+.2f}'

def fpv(p):
    return '-' if p is None or pd.isna(p) else ('<0.001' if p < 0.001 else f'{p:.3f}')

def holm(ps):
    ps = np.asarray(ps, float)
    adj, run = np.empty(len(ps)), 0.0
    for k, i in enumerate(np.argsort(ps, kind='stable')):
        run = max(run, (len(ps) - k) * ps[i])
        adj[i] = min(1.0, run)
    return adj

def p2(obs, null):
    """two-sided permutation p: share of shuffles at least as far from the null mean as the observed value"""
    null = np.asarray(null, float)
    null = null[~np.isnan(null)]
    c = null.mean()
    return (1 + np.sum(np.abs(null - c) >= abs(obs - c) - 1e-12)) / (len(null) + 1)

def rk(v):
    return np.argsort(np.argsort(v, kind='stable'), kind='stable').astype(float)

def spear(a, b):
    return np.corrcoef(rk(a), rk(b))[0, 1]

TESTS = []
def add_test(item, fam, tid, name, obs, null, n, meaning_q, p=None, fmt=fp, unit=''):
    TESTS.append(dict(item=item, family=fam, id=tid, test=name, observed=obs, null_mean=np.nanmean(null),
                      n=n, p=p2(obs, null) if p is None else p, question=meaning_q, fmt=fmt, unit=unit))

P('== sector_stock_level.py ==')
P(f'B = {B} shuffles per null; seeds {SEEDS}')

# ---------------------------------------------------------------- data
ev = pd.read_csv(f'{D}/events.csv')
ev = ev[ev.in_fo == True].copy()
assert len(ev) == 3278 and ev.symbol.nunique() == 206, (len(ev), ev.symbol.nunique())
assert ev.three_day.notna().all()
assert np.allclose(ev.three_day, ev.ret_dm1 + ev.ret_rd + ev.ret_dp1)
assert ((ev.i_m1 == ev.i_cut + 1) & (ev.i_rd == ev.i_m1 + 1) & (ev.i_p1 == ev.i_rd + 1)).all()
lab = pd.read_csv(f'{NS}/results_3day.csv')
ev = ev.merge(lab[['symbol', 'qn', 'nifty_sector', 'custom_sector', 'three_day']].rename(columns={'three_day': 'td_lab'}),
              on=['symbol', 'qn'], how='left', validate='1:1')
assert ev.nifty_sector.notna().all() and ev.custom_sector.notna().all()
assert np.allclose(ev.three_day, ev.td_lab, rtol=0, atol=1e-9)
assert set(ev.nifty_sector) <= set(SHORT) and set(ev.custom_sector) <= set(OLD_SHORT)
ev = ev.sort_values(['qn', 'symbol']).reset_index(drop=True)
ev['td'] = ev.three_day * 100
Q = ev.groupby('qn').td.mean()
assert list(Q.index) == list(range(NQ))
Qv = Q.to_numpy()
ev['x'] = ev.td - ev.qn.map(Q)
qlab = ev.groupby('qn').agg(period=('period', 'first'), quarter=('quarter', 'first'))
P(f'F&O results {len(ev)}, stocks {ev.symbol.nunique()}, quarters {NQ}; three_day matches '
  f'nifty_sector_3day/results_3day.csv; {ev.nifty_sector.nunique()} NSE sectors, {ev.custom_sector.nunique()} custom sectors')
P('Q_t (all F&O average, %): ' + ', '.join(f'{qlab.quarter[q]} {fp(Q[q])}' for q in range(NQ)))

def setup(col, short):
    size = ev[col].value_counts()
    names = sorted(size.index, key=lambda s: (-size[s], s))
    code = ev[col].map({s: i for i, s in enumerate(names)}).to_numpy()
    S = len(names)
    cell = ev.qn.to_numpy() * S + code
    cnt = np.bincount(cell, minlength=NQ * S).reshape(NQ, S)
    return dict(col=col, names=names, short=[short[s] for s in names], S=S, cell=cell, cnt=cnt, valid=cnt >= MIN_N)

def excess(L, td):
    s = np.bincount(L['cell'], weights=td, minlength=NQ * L['S']).reshape(NQ, L['S'])
    with np.errstate(invalid='ignore', divide='ignore'):
        m = s / L['cnt']
    return m - Qv[:, None]          # Q_t is unchanged by a within-quarter shuffle

NIF = setup('nifty_sector', SHORT)
CUS = setup('custom_sector', OLD_SHORT)
TD = ev.td.to_numpy()
QN = ev.qn.to_numpy()

# reproduce the earlier best / worst sector tables
def leaders(L, e):
    bw = []
    for t in range(NQ):
        v = np.where(L['valid'][t])[0]
        bw.append((v[np.argmax(e[t, v])], v[np.argmin(e[t, v])]))
    return bw

e_nif, e_cus = excess(NIF, TD), excess(CUS, TD)
qln = pd.read_csv(f'{NS}/quarter_leaders.csv')
qlc = pd.read_csv(OLDQL)
for L, e, ref, nm in [(NIF, e_nif, qln, 'NSE'), (CUS, e_cus, qlc, 'custom')]:
    bw = leaders(L, e)
    assert [L['names'][b] for b, _ in bw] == list(ref.best), nm
    assert [L['names'][w] for _, w in bw] == list(ref.worst), nm
    assert np.allclose([e[t, b] + Qv[t] for t, (b, _) in enumerate(bw)], ref.best_avg, atol=6e-4)
    assert np.allclose(Qv, ref.avg, atol=6e-4)
    P(f'{nm} sectors: best / worst sector of all 22 quarters reproduce the earlier quarter-leaders table')

# ---------------------------------------------------------------- items 1-3 statistics
def persist(e, cnt, valid, lag):
    rhos, ks, X, Y, W = [], [], [], [], []
    for t in range(NQ - lag):
        m = valid[t] & valid[t + lag]
        a, b = e[t, m], e[t + lag, m]
        rhos.append(spear(a, b))
        ks.append(int(m.sum()))
        n1, n2 = cnt[t, m], cnt[t + lag, m]
        X.append(a); Y.append(b); W.append(n1 * n2 / (n1 + n2))
    X, Y, W = map(np.concatenate, (X, Y, W))
    xm, ym = np.average(X, weights=W), np.average(Y, weights=W)
    slope = np.sum(W * (X - xm) * (Y - ym)) / np.sum(W * (X - xm) ** 2)
    return np.array(rhos), np.array(ks), slope, len(X)

def transitions(e, valid):
    out = []
    for t in range(NQ - 1):
        v0 = np.where(valid[t])[0]
        b, w = v0[np.argmax(e[t, v0])], v0[np.argmin(e[t, v0])]
        v1 = np.where(valid[t + 1])[0]
        K = len(v1)
        rank = {s: i + 1 for i, s in enumerate(v1[np.argsort(-e[t + 1, v1], kind='stable')])}
        out.append((b, w, rank.get(b), rank.get(w), K, e[t + 1, b], e[t + 1, w]))
    return out

def trans_summary(tr):
    rb = [(r, K, ex) for _, _, r, _, K, ex, _ in tr if r is not None]
    rw = [(r, K, ex) for _, _, _, r, K, _, ex in tr if r is not None]
    pct = lambda r, K: 100 * (K - r) / (K - 1)          # 100 = best, 0 = worst
    return dict(pct_b=np.mean([pct(r, K) for r, K, _ in rb]), pct_w=np.mean([pct(r, K) for r, K, _ in rw]),
                ex_b=np.mean([ex for *_, ex in rb]), ex_w=np.mean([ex for *_, ex in rw]),
                bb=sum(r == 1 for r, K, _ in rb), bw=sum(r == K for r, K, _ in rb),
                ww=sum(r == K for r, K, _ in rw), wb=sum(r == 1 for r, K, _ in rw), n_b=len(rb), n_w=len(rw))

def pair_corr(E):
    """pairwise Pearson r of the columns of E (T x k, NaN = missing) over rows where both are present"""
    M = (~np.isnan(E)).astype(float)
    X = np.nan_to_num(E)
    n = M.T @ M
    Sx, Sxx, Sxy = X.T @ M, (X ** 2).T @ M, X.T @ X
    with np.errstate(invalid='ignore', divide='ignore'):
        r = (Sxy - Sx * Sx.T / n) / np.sqrt((Sxx - Sx ** 2 / n) * (Sxx.T - Sx.T ** 2 / n))
    return r, n

def corr_input(L, e):
    keep = np.where(L['valid'].sum(axis=0) >= MIN_Q)[0]
    E = np.where(L['valid'][:, keep], e[:, keep], np.nan)
    return keep, E

def all_stats(L, e):
    r1, k1, s1, n1 = persist(e, L['cnt'], L['valid'], 1)
    r4, k4, s4, n4 = persist(e, L['cnt'], L['valid'], 4)
    tr = transitions(e, L['valid'])
    keep, E = corr_input(L, e)
    R, _ = pair_corr(E)
    iu = np.triu_indices(len(keep), 1)
    small = sum(int(L['cnt'][t, b] <= 5) + int(L['cnt'][t, w] <= 5) for t, (b, w) in enumerate(leaders(L, e)))
    return dict(rho1=r1, rho4=r4, slope1=s1, slope4=s4, k1=k1, k4=k4, n1=n1, n4=n4, tr=tr, ts=trans_summary(tr),
                R=R, ru=R[iu], keep=keep, small=small)

obs = {'NSE': all_stats(NIF, e_nif), 'custom': all_stats(CUS, e_cus)}
LABS = {'NSE': NIF, 'custom': CUS}

# null: within-quarter shuffles of the results across sector labels (same permutation applied to both label sets)
rng = np.random.default_rng(SEEDS['sector'])
NULL = {k: dict(rho1=[], rho4=[], slope1=[], slope4=[], ts=[], ru=[], maxabs=[], r2=[], small=[]) for k in obs}
for b in range(B):
    perm = np.lexsort((rng.random(len(TD)), QN))        # ev is sorted by qn, so this permutes within quarter
    tds = TD[perm]
    for k, L in LABS.items():
        st = all_stats(L, excess(L, tds))
        d = NULL[k]
        d['rho1'].append(st['rho1'].mean()); d['rho4'].append(st['rho4'].mean())
        d['slope1'].append(st['slope1']); d['slope4'].append(st['slope4'])
        d['ts'].append(st['ts']); d['ru'].append(st['ru'])
        d['maxabs'].append(np.nanmax(np.abs(st['ru']))); d['r2'].append(np.nanmean(st['ru'] ** 2))
        d['small'].append(st['small'])
for d in NULL.values():
    for k in ('rho1', 'rho4', 'slope1', 'slope4', 'maxabs', 'r2', 'small'):
        d[k] = np.array(d[k])
    d['ru'] = np.array(d['ru'])
    d['ts'] = pd.DataFrame(d['ts'])

# ---------------------------------------------------------------- item 1 output
P('\n== 1. Sector persistence (sector excess e(s,t) = sector average - all-F&O average Q_t)')
for k in ('NSE', 'custom'):
    o, d = obs[k], NULL[k]
    P(f'{k} sectors: lag 1: mean Spearman over {len(o["rho1"])} quarter pairs {fp(o["rho1"].mean())} '
      f'(null mean {fp(d["rho1"].mean())}, p {fpv(p2(o["rho1"].mean(), d["rho1"]))}); pairs positive '
      f'{(o["rho1"] > 0).sum()} of {len(o["rho1"])}; sectors per pair {o["k1"].min()}-{o["k1"].max()}')
    P(f'{k} sectors: lag 4: mean Spearman over {len(o["rho4"])} quarter pairs {fp(o["rho4"].mean())} '
      f'(null mean {fp(d["rho4"].mean())}, p {fpv(p2(o["rho4"].mean(), d["rho4"]))}); pairs positive '
      f'{(o["rho4"] > 0).sum()} of {len(o["rho4"])}; sectors per pair {o["k4"].min()}-{o["k4"].max()}')
    P(f'{k} sectors: weighted slope of e(s,t+1) on e(s,t): {o["slope1"]:+.3f} over {o["n1"]} sector-pairs '
      f'(null mean {d["slope1"].mean():+.3f}, p {fpv(p2(o["slope1"], d["slope1"]))}); lag 4: {o["slope4"]:+.3f} over '
      f'{o["n4"]} (null mean {d["slope4"].mean():+.3f}, p {fpv(p2(o["slope4"], d["slope4"]))})')
o, d = obs['NSE'], NULL['NSE']
Q1 = 'Do sectors that beat (lag) the quarter average beat (lag) it again next quarter? (rank order of sectors)'
Q4 = 'Do sectors that beat the quarter average beat it again in the same results period a year later?'
QS1 = 'Pooled: how much of a sector\'s excess this quarter carries into next quarter (pp per pp)'
QS4 = 'Pooled: how much of a sector\'s excess carries into the same period a year later (pp per pp)'
add_test(1, '1', '1a', 'NSE sectors: mean Spearman e(s,t) vs e(s,t+1)', o['rho1'].mean(), d['rho1'],
         f'{len(o["rho1"])} pairs, {o["k1"].min()}-{o["k1"].max()} sectors', Q1)
add_test(1, '1', '1b', 'NSE sectors: mean Spearman e(s,t) vs e(s,t+4)', o['rho4'].mean(), d['rho4'],
         f'{len(o["rho4"])} pairs, {o["k4"].min()}-{o["k4"].max()} sectors', Q4)
add_test(1, '1', '1c', 'NSE sectors: weighted slope e(s,t+1) on e(s,t)', o['slope1'], d['slope1'],
         f'{o["n1"]} sector-pairs', QS1)
add_test(1, '1', '1d', 'NSE sectors: weighted slope e(s,t+4) on e(s,t)', o['slope4'], d['slope4'],
         f'{o["n4"]} sector-pairs', QS4)
o, d = obs['custom'], NULL['custom']
add_test(1, '1', '1e', 'Custom sectors: mean Spearman e(s,t) vs e(s,t+1)', o['rho1'].mean(), d['rho1'],
         f'{len(o["rho1"])} pairs, {o["k1"].min()}-{o["k1"].max()} sectors', Q1.replace('sectors', 'custom sectors', 1))
add_test(1, '1', '1f', 'Custom sectors: mean Spearman e(s,t) vs e(s,t+4)', o['rho4'].mean(), d['rho4'],
         f'{len(o["rho4"])} pairs, {o["k4"].min()}-{o["k4"].max()} sectors', Q4.replace('sectors', 'custom sectors', 1))
add_test(1, '1', '1g', 'Custom sectors: weighted slope e(s,t+1) on e(s,t)', o['slope1'], d['slope1'], f'{o["n1"]} sector-pairs',
         QS1.replace('sector', 'custom sector', 1))
add_test(1, '1', '1h', 'Custom sectors: weighted slope e(s,t+4) on e(s,t)', o['slope4'], d['slope4'], f'{o["n4"]} sector-pairs',
         QS4.replace('sector', 'custom sector', 1))

# ---------------------------------------------------------------- item 2 output
P('\n== 2. Best and worst sector of a quarter, next quarter')
for k in ('NSE', 'custom'):
    ts, nd = obs[k]['ts'], NULL[k]['ts']
    P(f'{k}: best sector next quarter: {ts["n_b"]} transitions, rank percentile {ts["pct_b"]:.1f} (100 = best; null '
      f'{nd.pct_b.mean():.1f}, p {fpv(p2(ts["pct_b"], nd.pct_b))}), excess {fp(ts["ex_b"])} (null {fp(nd.ex_b.mean())}, '
      f'p {fpv(p2(ts["ex_b"], nd.ex_b))})')
    P(f'{k}: worst sector next quarter: {ts["n_w"]} transitions, rank percentile {ts["pct_w"]:.1f} (null '
      f'{nd.pct_w.mean():.1f}, p {fpv(p2(ts["pct_w"], nd.pct_w))}), excess {fp(ts["ex_w"])} (null {fp(nd.ex_w.mean())}, '
      f'p {fpv(p2(ts["ex_w"], nd.ex_w))})')
    P(f'{k}: counts best->best {ts["bb"]} (expected {nd.bb.mean():.2f}), best->worst {ts["bw"]} ({nd.bw.mean():.2f}), '
      f'worst->worst {ts["ww"]} ({nd.ww.mean():.2f}), worst->best {ts["wb"]} ({nd.wb.mean():.2f})')
    P(f'{k} (descriptive): best or worst slots (of 44) taken by a sector with only 4-5 results that quarter: '
      f'{obs[k]["small"]} (shuffle null mean {NULL[k]["small"].mean():.1f}; small sectors have noisier averages)')
ts, nd = obs['NSE']['ts'], NULL['NSE']['ts']
pf = lambda v: f'{v:.1f}'
nb, nw = f'{ts["n_b"]} quarters', f'{ts["n_w"]} quarters'
add_test(2, '2', '2a', 'NSE: best sector, mean rank percentile next quarter (100 = best)', ts['pct_b'], nd.pct_b, nb,
         'Does the best sector stay near the top next quarter?', fmt=pf)
add_test(2, '2', '2b', 'NSE: worst sector, mean rank percentile next quarter (100 = best)', ts['pct_w'], nd.pct_w, nw,
         'Does the worst sector stay near the bottom next quarter?', fmt=pf)
add_test(2, '2', '2c', 'NSE: best sector, mean excess next quarter', ts['ex_b'], nd.ex_b, nb,
         'Does the best sector still beat the quarter average next quarter?', unit='%')
add_test(2, '2', '2d', 'NSE: worst sector, mean excess next quarter', ts['ex_w'], nd.ex_w, nw,
         'Does the worst sector still lag the quarter average next quarter?', unit='%')
pc = lambda v: f'{v:.0f}' if float(v).is_integer() else f'{v:.2f}'
add_test(2, '2', '2e', 'NSE: count best -> best next quarter', ts['bb'], nd.bb, nb, 'Is the best sector best again?', fmt=pc)
add_test(2, '2', '2f', 'NSE: count best -> worst next quarter', ts['bw'], nd.bw, nb, 'Does the best sector flip to worst?', fmt=pc)
add_test(2, '2', '2g', 'NSE: count worst -> worst next quarter', ts['ww'], nd.ww, nw, 'Is the worst sector worst again?', fmt=pc)
add_test(2, '2', '2h', 'NSE: count worst -> best next quarter', ts['wb'], nd.wb, nw, 'Does the worst sector flip to best?', fmt=pc)
ts, nd = obs['custom']['ts'], NULL['custom']['ts']
add_test(2, '2', '2i', 'Custom: best sector, mean rank percentile next quarter', ts['pct_b'], nd.pct_b, f'{ts["n_b"]} quarters',
         'Custom sectors: does the best sector stay near the top?', fmt=pf)
add_test(2, '2', '2j', 'Custom: worst sector, mean rank percentile next quarter', ts['pct_w'], nd.pct_w, f'{ts["n_w"]} quarters',
         'Custom sectors: does the worst sector stay near the bottom?', fmt=pf)

# transitions table (NSE) and csv (both)
def trans_rows(L, e, tr):
    rows = []
    for t in range(NQ):
        v = np.where(L['valid'][t])[0]
        b, w = v[np.argmax(e[t, v])], v[np.argmin(e[t, v])]
        r = dict(qn=t, period=qlab.period[t], quarter=qlab.quarter[t], Q=Qv[t], ranked=len(v),
                 best=L['names'][b], best_avg=e[t, b] + Qv[t], best_n=int(L['cnt'][t, b]),
                 worst=L['names'][w], worst_avg=e[t, w] + Qv[t], worst_n=int(L['cnt'][t, w]))
        if t < NQ - 1:
            bb, ww, rb, rw, K, *_ = tr[t]
            assert bb == b and ww == w
            r.update(next_ranked=K, best_next_rank=rb, best_next_avg=e[t + 1, b] + Qv[t + 1],
                     best_next_n=int(L['cnt'][t + 1, b]), worst_next_rank=rw, worst_next_avg=e[t + 1, w] + Qv[t + 1],
                     worst_next_n=int(L['cnt'][t + 1, w]), Q_next=Qv[t + 1])
        rows.append(r)
    return pd.DataFrame(rows)

TR = {k: trans_rows(LABS[k], e, obs[k]['tr']) for k, e in (('NSE', e_nif), ('custom', e_cus))}
for k, df in TR.items():
    df.round(3).to_csv(f'{OUT}/s_transitions{"" if k == "NSE" else "_custom"}.csv', index=False)

def trans_md(k, sh):
    df = TR[k]
    out = ['| Results for | Quarter | All F&O avg | Best sector (avg, n) | Its rank next quarter | Its avg next quarter | '
           'Worst sector (avg, n) | Its rank next quarter | Its avg next quarter | All F&O avg next quarter |',
           '|---|---|---:|---|---:|---:|---|---:|---:|---:|']
    for _, r in df.iterrows():
        if r.qn < NQ - 1:
            rk_b = f'{int(r.best_next_rank)} of {int(r.next_ranked)}' if pd.notna(r.best_next_rank) else f'- (n={r.best_next_n})'
            rk_w = f'{int(r.worst_next_rank)} of {int(r.next_ranked)}' if pd.notna(r.worst_next_rank) else f'- (n={r.worst_next_n})'
            nx = [rk_b, f'{fp(r.best_next_avg)}%', rk_w, f'{fp(r.worst_next_avg)}%', f'{fp(r.Q_next)}%']
        else:
            nx = ['-', '-', '-', '-', '-']
        out.append(f'| {r.period} | {r.quarter} | {fp(r.Q)}% | {sh[r.best]} {fp(r.best_avg)}% ({r.best_n}) | {nx[0]} | {nx[1]} | '
                   f'{sh[r.worst]} {fp(r.worst_avg)}% ({r.worst_n}) | {nx[2]} | {nx[3]} | {nx[4]} |')
    ts, nd = obs[k]['ts'], NULL[k]['ts']
    out += ['', f'Best and worst sector: highest and lowest average three-day sum among sectors with at least {MIN_N} '
            'results that quarter (n = number of results). Rank next quarter: among the sectors with at least '
            f'{MIN_N} results next quarter (1 = best); "-" when the sector has fewer than {MIN_N} results next quarter.', '',
            f'Summary over {ts["n_b"]} best and {ts["n_w"]} worst transitions (expected under {B:,} within-quarter shuffles '
            'of the results across sector labels in brackets):', '',
            '| | Best sector of quarter t | Worst sector of quarter t |', '|---|---:|---:|',
            f'| Mean rank percentile next quarter (100 = best, 0 = worst) | {ts["pct_b"]:.1f} ({nd.pct_b.mean():.1f}) | '
            f'{ts["pct_w"]:.1f} ({nd.pct_w.mean():.1f}) |',
            f'| Mean excess over all F&O next quarter | {fp(ts["ex_b"])}% ({fp(nd.ex_b.mean())}%) | {fp(ts["ex_w"])}% '
            f'({fp(nd.ex_w.mean())}%) |',
            f'| Best again next quarter | {ts["bb"]} ({nd.bb.mean():.2f}) | {ts["wb"]} ({nd.wb.mean():.2f}) |',
            f'| Worst next quarter | {ts["bw"]} ({nd.bw.mean():.2f}) | {ts["ww"]} ({nd.ww.mean():.2f}) |', '',
            f'Of the 44 best and worst slots, {obs[k]["small"]} go to a sector with only 4-5 results that quarter (shuffle '
            f'null {NULL[k]["small"].mean():.1f}). Averages of few results swing more, which is why small sectors'
            + (' such as Cons services (4-9 results)' if k == 'NSE' else '') +
            ' top and tail the table so often; the counts above are therefore compared with '
            'the shuffle null, not with 1 in K.']
    return out

md = ['# Best and worst sector of each quarter, and where they ranked the next quarter', '',
      '## NSE index sectors', ''] + trans_md('NSE', SHORT)
md += ['', 'Short names: ' + '; '.join(f'{SHORT[s]} = {s}' for s in NIF['names']) + '.', '',
       '## Custom 15 sectors (summary only; per-quarter rows in s_transitions_custom.csv)', '']
md += trans_md('custom', OLD_SHORT)[-10:]
open(f'{OUT}/s_table_transitions.md', 'w').write('\n'.join(md) + '\n')
P('\n--- s_table_transitions.md ---\n' + '\n'.join(md))

# ---------------------------------------------------------------- item 3 output
P('\n== 3. Which sectors are best and worst together (correlation of sector excess across quarters)')
PAIRS = []
for k in ('NSE', 'custom'):
    L, o, d = LABS[k], obs[k], NULL[k]
    keep = o['keep']
    nq = L['valid'][:, keep].sum(axis=0)
    P(f'{k}: {len(keep)} sectors with >= {MIN_N} results in >= {MIN_Q} of 22 quarters: '
      + ', '.join(f'{L["short"][i]} ({nq[j]})' for j, i in enumerate(keep)))
    E = np.where(L['valid'][:, keep], (e_nif if k == 'NSE' else e_cus)[:, keep], np.nan)
    R, N = pair_corr(E)
    names = [L['short'][i] for i in keep]
    pd.DataFrame(np.round(R, 3), index=names, columns=names).to_csv(f'{OUT}/s_sector_corr{"" if k == "NSE" else "_custom"}.csv')
    iu = np.triu_indices(len(keep), 1)
    assert np.allclose(R[iu], o['ru'], equal_nan=True)
    # two-sided as in p2: distance from each pair's own null mean (the null r is below 0, about -0.03 to -0.19,
    # because the sector excesses add up to zero each quarter); maxT over the pairs on that distance
    assert not np.isnan(d['ru']).any()
    mu = d['ru'].mean(axis=0)
    dev = np.abs(d['ru'] - mu)
    d['maxdev'] = dev.max(axis=1)
    for j, (a, bb) in enumerate(zip(*iu)):       # column j of the null pair matrix = this pair
        r = R[a, bb]
        PAIRS.append(dict(labels=k, sector_a=names[a], sector_b=names[bb], r=r, null_mean_r=mu[j], n_quarters=int(N[a, bb]),
                          p_pair=(1 + np.sum(dev[:, j] >= abs(r - mu[j]) - 1e-12)) / (B + 1),
                          p_familywise=(1 + np.sum(d['maxdev'] >= abs(r - mu[j]) - 1e-12)) / (B + 1)))
    P(f'{k}: {len(iu[0])} pairs; mean r {np.nanmean(o["ru"]):+.3f} (null {np.nanmean(d["ru"]):+.3f}; pair null means '
      f'{mu.min():+.2f} to {mu.max():+.2f}); mean r^2 '
      f'{np.nanmean(o["ru"] ** 2):.3f} (null {d["r2"].mean():.3f}, p {fpv(p2(np.nanmean(o["ru"] ** 2), d["r2"]))}); '
      f'null max |r - pair null mean|: median {np.median(d["maxdev"]):.2f}, 95th pct {np.quantile(d["maxdev"], 0.95):.2f}')
PAIRS = pd.DataFrame(PAIRS)
assert PAIRS.r.notna().all()
PAIRS.round(4).to_csv(f'{OUT}/s_sector_corr_pairs.csv', index=False)
for k in ('NSE', 'custom'):
    sub = PAIRS[PAIRS.labels == k].sort_values('r')
    P(f'{k} most negative pairs: ' + '; '.join(f'{r.sector_a} / {r.sector_b} {r.r:+.2f} (n {r.n_quarters}, pair p '
                                              f'{fpv(r.p_pair)}, familywise p {fpv(r.p_familywise)})' for r in sub.head(5).itertuples()))
    P(f'{k} most positive pairs: ' + '; '.join(f'{r.sector_a} / {r.sector_b} {r.r:+.2f} (n {r.n_quarters}, pair p '
                                              f'{fpv(r.p_pair)}, familywise p {fpv(r.p_familywise)})' for r in sub.tail(5)[::-1].itertuples()))
for k, tid in (('NSE', '3a'), ('custom', '3b')):
    o, d = obs[k], NULL[k]
    add_test(3, '3-global', tid, f'{"NSE" if k == "NSE" else "Custom"} sectors: mean r^2 over the {len(o["ru"])} sector pairs', np.nanmean(o['ru'] ** 2),
             d['r2'], f'{len(o["keep"])} sectors, {PAIRS[PAIRS.labels == k].n_quarters.min()}-'
             f'{PAIRS[PAIRS.labels == k].n_quarters.max()} quarters per pair',
             f'{"Custom sectors" if k == "custom" else "Sectors"}: more co-movement (or opposite movement) of sector excess '
             'across quarters than chance?', fmt=lambda v: f'{v:.3f}')
sel = []
for k, nn in (('NSE', 5), ('custom', 3)):
    sub = PAIRS[PAIRS.labels == k].sort_values('r')
    sel += [('neg', r) for r in sub.head(nn).itertuples()] + [('pos', r) for r in sub.tail(nn)[::-1].itertuples()]
for i, (sign, r) in enumerate(sel):
    TESTS.append(dict(item=3, family='3-pairs (maxT)', id=f'3p{i + 1:02d}',
                      test=f'{r.labels}: r({r.sector_a}, {r.sector_b})', observed=r.r, null_mean=r.null_mean_r,
                      n=f'{r.n_quarters} quarters', p=r.p_pair, holm=r.p_familywise,
                      question=f'Are {r.sector_a} and {r.sector_b} {"best and worst together (opposite)" if sign == "neg" else "good and bad together (same way)"}?',
                      fmt=fp, unit=''))

def corr_md(k):
    L, o = LABS[k], obs[k]
    keep = o['keep']
    names = [L['short'][i] for i in keep]
    R = o['R']
    out = ['| | ' + ' | '.join(names) + ' |', '|---|' + '---:|' * len(names)]
    for a in range(len(names)):
        out.append(f'| {names[a]} | ' + ' | '.join('-' if a == b else fp(R[a, b]) for b in range(len(names))) + ' |')
    return out

def pairs_md(k, nn):
    sub = PAIRS[PAIRS.labels == k].sort_values('r')
    out = ['| | Pair | r | Null mean r | Quarters | Pair p | Familywise p |', '|---|---|---:|---:|---:|---:|---:|']
    for lab_, part in (('Most negative', sub.head(nn)), ('Most positive', sub.tail(nn)[::-1])):
        for r in part.itertuples():
            out.append(f'| {lab_} | {r.sector_a} / {r.sector_b} | {fp(r.r)} | {fp(r.null_mean_r)} | {r.n_quarters} | '
                       f'{fpv(r.p_pair)} | {fpv(r.p_familywise)} |')
    return out

o, d = obs['NSE'], NULL['NSE']
oc, dc = obs['custom'], NULL['custom']
md = ['# Which sectors are best and worst together', '',
      f'Pearson correlation, across quarters, of sector excess e(s,t) (sector average three-day sum minus the all-F&O '
      f'average of that quarter), for sectors with at least {MIN_N} results in at least {MIN_Q} of the 22 quarters. Each '
      f'pair uses the quarters where both sectors have at least {MIN_N} results.', '',
      '## NSE index sectors', ''] + corr_md('NSE') + [
      '', f'Mean r over the {len(o["ru"])} pairs {fp(np.nanmean(o["ru"]))} (shuffle null {fp(np.nanmean(d["ru"]))}: the '
      'excesses of all sectors add up to zero each quarter, so chance alone gives slightly negative r); mean r^2 '
      f'{np.nanmean(o["ru"] ** 2):.3f} (null {d["r2"].mean():.3f}, p {fpv(p2(np.nanmean(o["ru"] ** 2), d["r2"]))}).', '',
      ] + pairs_md('NSE', 5) + [
      '', f'Null mean r: average r of that pair over {B:,} within-quarter shuffles of the results across sector labels '
      '(below 0 because the sector excesses add up to zero each quarter). Pair p (two-sided): share of shuffles in '
      'which the pair\'s r is at least as far from its null mean as the observed r. Familywise p: share of shuffles '
      f'in which the largest such distance over all {len(o["ru"])} pairs reaches the observed distance (single-step '
      'maxT; corrects for having looked at every pair). Under the null the largest distance has median '
      f'{np.median(d["maxdev"]):.2f} and 95th percentile {np.quantile(d["maxdev"], 0.95):.2f}.', '',
      'Short names: ' + '; '.join(f'{SHORT[NIF["names"][i]]} = {NIF["names"][i]}' for i in o['keep']) + '.', '',
      '## Custom 15 sectors', ''] + corr_md('custom') + [
      '', f'Mean r {fp(np.nanmean(oc["ru"]))} (null {fp(np.nanmean(dc["ru"]))}); mean r^2 {np.nanmean(oc["ru"] ** 2):.3f} '
      f'(null {dc["r2"].mean():.3f}, p {fpv(p2(np.nanmean(oc["ru"] ** 2), dc["r2"]))}). Null max |r - null mean r|: median '
      f'{np.median(dc["maxdev"]):.2f}, 95th percentile {np.quantile(dc["maxdev"], 0.95):.2f}.', ''] + pairs_md('custom', 3) + [
      '', 'Short names: ' + '; '.join(f'{OLD_SHORT[CUS["names"][i]]} = {CUS["names"][i]}' for i in oc['keep']) + '.']
open(f'{OUT}/s_table_sector_corr.md', 'w').write('\n'.join(md) + '\n')
P('\n--- s_table_sector_corr.md ---\n' + '\n'.join(md))

# ---------------------------------------------------------------- item 4: Nifty sectoral index members
P('\n== 4. Members of the 13 Nifty sectoral indices with F&O members: excess vs own index')
im = pd.read_csv(f'{NS}/index_member_results.csv')
im = im[im.group == 'sectoral'].copy()
ref = pd.read_csv(f'{NS}/index_excess_by_quarter.csv')
IDX = [c for c in ref.columns if c in IDX_SHORT]
assert len(IDX) == 13 and set(im['index']) == set(IDX), set(im['index']) ^ set(IDX)
ix = pd.read_csv(f'{D}/index_close.csv', index_col=0)
ses = pd.read_csv(f'{D}/sessions.csv')
assert (ix.index == ses.day).all()
Wd = ev[['i_m1', 'i_rd', 'i_p1']].to_numpy(int)
EM = np.empty((len(ev), len(IDX)))
for j, name in enumerate(IDX):
    c = ix[name].to_numpy(float)
    r = np.r_[np.nan, c[1:] / c[:-1] - 1]
    EM[:, j] = TD - r[Wd].sum(axis=1) * 100          # stock minus index three-day sum, on the result's own sessions
pos = pd.Series(range(len(ev)), index=pd.MultiIndex.from_arrays([ev.symbol, ev.qn]))
ri = pos.loc[list(zip(im.symbol, im.qn))].to_numpy()
cj = im['index'].map({n: j for j, n in enumerate(IDX)}).to_numpy()
A = np.zeros((len(ev), len(IDX)), bool)
A[ri, cj] = True
assert A.sum() == len(im) == 2822
chk = EM[ri, cj]
both = ~np.isnan(chk) & im.excess_vs_index.notna().to_numpy()
assert (np.isnan(chk) == im.excess_vs_index.isna().to_numpy()).all()
assert np.allclose(chk[both], im.excess_vs_index.to_numpy()[both] * 100, atol=1e-5)
assert np.allclose(TD[ri], im.three_day * 100, atol=1e-5)
# membership is today's list: the same for every quarter of a stock
assert (pd.DataFrame(A).groupby(ev.symbol.to_numpy()).nunique() <= 1).all().all()
P(f'{len(im)} member results (sectoral group), {int(A.any(axis=1).sum())} distinct results in at least one sectoral index; '
  f'excess recomputed from index_close.csv matches index_member_results.csv (max abs diff '
  f'{np.nanmax(np.abs(chk[both] - im.excess_vs_index.to_numpy()[both] * 100)):.1e} pp); '
  f'{int(np.isnan(chk).sum())} member results without an index move (missing closes) left out')
mult = A[A.any(axis=1)].sum(axis=1)
P('memberships per member result: ' + ', '.join(f'{m} index(es): {(mult == m).sum()}' for m in sorted(set(mult))))
ROWS = [np.where((QN == t) & A.any(axis=1))[0] for t in range(NQ)]

def index_excess(EMx):
    e, cnt = np.full((NQ, len(IDX)), np.nan), np.zeros((NQ, len(IDX)), int)
    for t, rows in enumerate(ROWS):
        a = A[rows]
        v = EMx[t]
        ok = a & ~np.isnan(v)
        cnt[t] = ok.sum(axis=0)
        with np.errstate(invalid='ignore', divide='ignore'):
            e[t] = np.where(ok, v, 0).sum(axis=0) / cnt[t]
    return e, cnt

e_ix, c_ix = index_excess([EM[rows] for rows in ROWS])
refv = ref.set_index('qn')[IDX].to_numpy()
assert np.allclose(np.where(c_ix > 0, e_ix, np.nan), refv, atol=6e-4, equal_nan=True)
P('per-quarter index excesses reproduce results/nifty_sector_3day/index_excess_by_quarter.csv')
cnt_ref = pd.read_csv(f'{NS}/index_count_by_quarter.csv').set_index('qn')[IDX].to_numpy()
assert (A[:, :].sum() == cnt_ref.sum())
oi = dict(zip(('rho1', 'k1', 'slope1', 'n1'), persist(e_ix, c_ix, c_ix >= MIN_N, 1)))
oi.update(dict(zip(('rho4', 'k4', 'slope4', 'n4'), persist(e_ix, c_ix, c_ix >= MIN_N, 4))))
rng = np.random.default_rng(SEEDS['index'])
NI = dict(rho1=[], rho4=[], slope1=[], slope4=[])
for b in range(B):
    EMx = [EM[rows][rng.permutation(len(rows))] for rows in ROWS]   # result r' takes over all memberships of slot r
    e, c = index_excess(EMx)
    v = c >= MIN_N
    r1, _, s1, _ = persist(e, c, v, 1)
    r4, _, s4, _ = persist(e, c, v, 4)
    NI['rho1'].append(r1.mean()); NI['rho4'].append(r4.mean()); NI['slope1'].append(s1); NI['slope4'].append(s4)
NI = {k: np.array(v) for k, v in NI.items()}
P(f'indices with >= {MIN_N} member results per quarter: {int((c_ix >= MIN_N).sum(axis=1).min())}-'
  f'{int((c_ix >= MIN_N).sum(axis=1).max())}')
for L_ in (1, 4):
    P(f'lag {L_}: mean Spearman over {len(oi[f"rho{L_}"])} pairs {fp(oi[f"rho{L_}"].mean())} (null '
      f'{fp(NI[f"rho{L_}"].mean())}, p {fpv(p2(oi[f"rho{L_}"].mean(), NI[f"rho{L_}"]))}), pairs positive '
      f'{(oi[f"rho{L_}"] > 0).sum()}; slope {oi[f"slope{L_}"]:+.3f} over {oi[f"n{L_}"]} index-pairs (null '
      f'{NI[f"slope{L_}"].mean():+.3f}, p {fpv(p2(oi[f"slope{L_}"], NI[f"slope{L_}"]))})')
QI = 'Do index members that beat (lag) their own index as a group do so again'
add_test(4, '4', '4a', 'Index members: mean Spearman of excess vs own index, t vs t+1', oi['rho1'].mean(), NI['rho1'],
         f'{len(oi["rho1"])} pairs, {oi["k1"].min()}-{oi["k1"].max()} indices', QI + ' next quarter? (rank order of indices)')
add_test(4, '4', '4b', 'Index members: mean Spearman of excess vs own index, t vs t+4', oi['rho4'].mean(), NI['rho4'],
         f'{len(oi["rho4"])} pairs, {oi["k4"].min()}-{oi["k4"].max()} indices', QI + ' a year later?')
add_test(4, '4', '4c', 'Index members: weighted slope, t+1 on t', oi['slope1'], NI['slope1'], f'{oi["n1"]} index-pairs',
         'Pooled: how much of the members\' excess vs their index carries into next quarter (pp per pp)')
add_test(4, '4', '4d', 'Index members: weighted slope, t+4 on t', oi['slope4'], NI['slope4'], f'{oi["n4"]} index-pairs',
         'Pooled: how much carries into the same period a year later (pp per pp)')

# persistence table (items 1 and 4, per quarter pair)
def pers_md(lag):
    rows = []
    for t in range(NQ - lag):
        rows.append(f'| {qlab.period[t]} -> {qlab.period[t + lag]} | {obs["NSE"][f"k{lag}"][t]} | '
                    f'{fp(obs["NSE"][f"rho{lag}"][t])} | {obs["custom"][f"k{lag}"][t]} | {fp(obs["custom"][f"rho{lag}"][t])} | '
                    f'{oi[f"k{lag}"][t]} | {fp(oi[f"rho{lag}"][t])} |')
    return (['| Results for t -> t+%d | NSE sectors | Spearman | Custom sectors | Spearman | Sectoral indices | Spearman |' % lag,
             '|---|---:|---:|---:|---:|---:|---:|'] + rows)

def summ_line(lab_, o_, n_, lag):
    return (f'| {lab_} | {fp(o_[f"rho{lag}"].mean())} | {fp(np.mean(n_[f"rho{lag}"]))} | {fpv(p2(o_[f"rho{lag}"].mean(), n_[f"rho{lag}"]))} | '
            f'{int((o_[f"rho{lag}"] > 0).sum())} of {len(o_[f"rho{lag}"])} | {o_[f"slope{lag}"]:+.2f} | {np.mean(n_[f"slope{lag}"]):+.2f} | '
            f'{fpv(p2(o_[f"slope{lag}"], n_[f"slope{lag}"]))} |')

md = ['# Do sector excesses carry over to the next quarter?', '',
      'Sector excess = sector average three-day sum minus the all-F&O average of the quarter. Index members: the members\' '
      'average excess over their own sectoral index. Spearman = rank correlation, over the sectors (indices) with at least '
      f'{MIN_N} results in both quarters, of the excess in quarter t and in quarter t+1 (t+4 = the same results period a '
      'year later). Slope = pooled weighted regression of the later excess on the earlier one (weight n1*n2/(n1+n2)).', '',
      '## Summary', '']
for lag in (1, 4):
    md += [f'Lag {lag}:', '', '| | Mean Spearman | Null mean | p | Pairs positive | Slope | Null mean | p |',
           '|---|---:|---:|---:|---:|---:|---:|---:|',
           summ_line('NSE sectors', obs['NSE'], NULL['NSE'], lag), summ_line('Custom sectors', obs['custom'], NULL['custom'], lag),
           summ_line('Sectoral index members (vs own index)', oi, NI, lag), '']
md += [f'Null: {B:,} within-quarter shuffles of the results across sector labels (every cell keeps its size); for the '
       'index members, within-quarter shuffles of the member results over the member slots (a result takes over all '
       'index memberships of the slot it lands in, so overlapping indices stay overlapping; its excess is recomputed '
       'against each of those indices on its own sessions). p two-sided, before Holm (Holm p in s_table_tests.md).', '', '## Lag 1, per quarter pair', ''] + pers_md(1) + ['', '## Lag 4, per quarter pair', ''] + pers_md(4)
open(f'{OUT}/s_table_persistence.md', 'w').write('\n'.join(md) + '\n')
P('\n--- s_table_persistence.md ---\n' + '\n'.join(md))
pd.DataFrame([dict(labels=lab_, lag=lag, t=t, period_t=qlab.period[t], period_next=qlab.period[t + lag], k=o_[f'k{lag}'][t],
                   spearman=o_[f'rho{lag}'][t])
              for lab_, o_ in (('NSE', obs['NSE']), ('custom', obs['custom']), ('sectoral_index', oi))
              for lag in (1, 4) for t in range(NQ - lag)]).round(4).to_csv(f'{OUT}/s_persistence_pairs.csv', index=False)

# ---------------------------------------------------------------- item 5: stock level
P('\n== 5. Stock level: x = three-day sum minus the all-F&O average of the quarter')
st = ev[['symbol', 'qn', 'period', 'quarter', 'td', 'x']].sort_values(['symbol', 'qn']).reset_index(drop=True)
X = st.x.to_numpy()
SQ = st.qn.to_numpy()
sym = st.symbol.astype('category').cat.codes.to_numpy()
key = pd.Series(range(len(st)), index=pd.MultiIndex.from_arrays([st.symbol, st.qn]))
def pairs(lag):
    k2 = pd.MultiIndex.from_arrays([st.symbol, st.qn + lag])
    ok = k2.isin(key.index)
    return np.where(ok)[0], key.loc[k2[ok]].to_numpy()
a1, b1 = pairs(1)
a4, b4 = pairs(4)
assert (st.symbol.to_numpy()[a1] == st.symbol.to_numpy()[b1]).all() and (SQ[b1] == SQ[a1] + 1).all()
nxt = st.groupby('symbol').qn.shift(-1)
gaps = int(((nxt - st.qn) > 1).sum())
P(f'{len(a1)} consecutive-quarter pairs (t, t+1) from {len(np.unique(sym[a1]))} stocks; {len(a4)} pairs (t, t+4); '
  f'{gaps} results whose next result is more than one quarter later (left out); {int(nxt.isna().sum())} last results')
pear = lambda u, v: np.corrcoef(u, v)[0, 1]
o5 = dict(r1=pear(X[a1], X[b1]), r4=pear(X[a4], X[b4]), s1=spear(X[a1], X[b1]), s4=spear(X[a4], X[b4]))
# null A: within-stock shuffle of the quarter order
rng = np.random.default_rng(SEEDS['stock_within'])
NA = dict(r1=[], r4=[], s1=[], s4=[])
for b in range(B):
    xs = X[np.lexsort((rng.random(len(X)), sym))]     # st is sorted by symbol: permutes within stock
    NA['r1'].append(pear(xs[a1], xs[b1])); NA['r4'].append(pear(xs[a4], xs[b4]))
    NA['s1'].append(spear(xs[a1], xs[b1])); NA['s4'].append(spear(xs[a4], xs[b4]))
NA = {k: np.array(v) for k, v in NA.items()}
# null B: within-quarter shuffle across stocks
rng = np.random.default_rng(SEEDS['stock_across'])
byq = np.argsort(SQ, kind='stable')
NB = dict(r1=[], r4=[], s1=[], s4=[])
for b in range(B):
    xs = np.empty(len(X))
    xs[byq] = X[np.lexsort((rng.random(len(X)), SQ))]
    NB['r1'].append(pear(xs[a1], xs[b1])); NB['r4'].append(pear(xs[a4], xs[b4]))
    NB['s1'].append(spear(xs[a1], xs[b1])); NB['s4'].append(spear(xs[a4], xs[b4]))
NB = {k: np.array(v) for k, v in NB.items()}
for k, nm in (('r1', 'Pearson lag 1'), ('r4', 'Pearson lag 4'), ('s1', 'Spearman lag 1'), ('s4', 'Spearman lag 4')):
    P(f'{nm}: {fp(o5[k])}; within-stock null mean {fp(NA[k].mean())} p {fpv(p2(o5[k], NA[k]))}; across-stock null mean '
      f'{fp(NB[k].mean())} p {fpv(p2(o5[k], NB[k]))}')
add_test(5, '5', '5a', 'Stocks: Pearson r of x(t) and x(t+1), within-stock shuffle null', o5['r1'], NA['r1'], f'{len(a1):,} pairs',
         'Is a stock\'s results move next quarter tied to this quarter\'s more than to a random other quarter of the same stock?')
add_test(5, '5', '5b', 'Stocks: Pearson r of x(t) and x(t+4), within-stock shuffle null', o5['r4'], NA['r4'], f'{len(a4):,} pairs',
         'Same, for the same results period a year later')
add_test(5, '5', '5c', 'Stocks: Spearman of x(t) and x(t+1), within-stock shuffle null', o5['s1'], NA['s1'], f'{len(a1):,} pairs',
         'As 5a, on ranks (less sensitive to a few huge moves)')
add_test(5, '5', '5d', 'Stocks: Spearman of x(t) and x(t+4), within-stock shuffle null', o5['s4'], NA['s4'], f'{len(a4):,} pairs',
         'As 5b, on ranks')
add_test(5, '5', '5e', 'Stocks: Pearson r of x(t) and x(t+1), across-stock shuffle null', o5['r1'], NB['r1'], f'{len(a1):,} pairs',
         'Any carry-over at all (stock trait or momentum) from one quarter to the next?')
add_test(5, '5', '5f', 'Stocks: Pearson r of x(t) and x(t+4), across-stock shuffle null', o5['r4'], NB['r4'], f'{len(a4):,} pairs',
         'Any carry-over at all to the same period a year later?')

# quintiles of x(t) -> x at the next result (t+1)
st['pct'] = st.groupby('qn').x.rank(pct=True)
st['quint'] = np.ceil(st.pct * 5).astype(int)
QA = st.quint.to_numpy()[a1]
XB = X[b1]
QB = SQ[b1]
top, bot = QA == 5, QA == 1
o_top, o_bot = XB[top].mean(), XB[bot].mean()
rng = np.random.default_rng(SEEDS['quint'])
byqb = np.argsort(QB, kind='stable')
NQT = dict(top=[], bot=[], spr=[])
for b in range(B):
    xs = np.empty(len(XB))
    xs[byqb] = XB[np.lexsort((rng.random(len(XB)), QB))]   # random picks of next-quarter results, same quarter mix
    NQT['top'].append(xs[top].mean()); NQT['bot'].append(xs[bot].mean()); NQT['spr'].append(xs[top].mean() - xs[bot].mean())
NQT = {k: np.array(v) for k, v in NQT.items()}
qrows = []
for qq in range(1, 6):
    m = QA == qq
    h1, h2 = m & (SQ[a1] <= 12), m & (SQ[a1] >= 13)     # next result in the first 14 / last 8 quarters
    qrows.append(dict(quintile=qq, pairs=int(m.sum()), x_t=X[a1][m].mean(), x_next=XB[m].mean(),
                      up_next=(XB[m] > 0).mean() * 100, x_next_first14=XB[h1].mean(), x_next_last8=XB[h2].mean(),
                      n_first14=int(h1.sum()), n_last8=int(h2.sum())))
qdf = pd.DataFrame(qrows)
P('quintiles of x(t) (1 = bottom fifth) -> x at the next result (t+1):')
P(qdf.round(2).to_string(index=False))
P(f'top fifth next {fp(o_top)} (random-pick null {fp(NQT["top"].mean())}, p {fpv(p2(o_top, NQT["top"]))}); bottom fifth next '
  f'{fp(o_bot)} (null {fp(NQT["bot"].mean())}, p {fpv(p2(o_bot, NQT["bot"]))}); spread {fp(o_top - o_bot)} (null '
  f'{fp(NQT["spr"].mean())}, p {fpv(p2(o_top - o_bot, NQT["spr"]))})')
add_test(5, '5', '5g', 'Stocks in the top fifth of x(t): mean x at their next result', o_top, NQT['top'], f'{int(top.sum())} results',
         'Do this quarter\'s best results movers beat the next quarter\'s average?', unit='%')
add_test(5, '5', '5h', 'Stocks in the bottom fifth of x(t): mean x at their next result', o_bot, NQT['bot'], f'{int(bot.sum())} results',
         'Do this quarter\'s worst results movers lag the next quarter\'s average?', unit='%')
add_test(5, '5', '5i', 'Top fifth minus bottom fifth, x at the next result', o_top - o_bot, NQT['spr'],
         f'{int(top.sum())} + {int(bot.sum())} results', 'Long last quarter\'s best movers, short the worst: any spread?', unit='%')

# last-4 track record (docs/PAST_PERFORMANCE.md, trade A: average three-day sum of the last 4 earlier results), built as
# in pattern_tests/past_performance/features/build_panel.py: history = all events of the stock (any F&O status) of an
# earlier quarter whose 3-day window and reaction day closed before this result's cutoff session; mean over the
# non-missing of the last 4; NaN with fewer than 4 earlier results
allev = pd.read_csv(f'{D}/events.csv')
allev['h_td'] = allev.three_day * 100
H = {s: g.sort_values('qn', ascending=False) for s, g in allev.groupby('symbol')}
cut = ev.set_index(['symbol', 'qn']).i_cut
td4 = []
for s, q in zip(st.symbol, st.qn):
    g = H[s]
    dec = cut[(s, q)]
    h = g[(g.qn < q) & (g.i_p1 < dec) & (g.i_react < dec)]
    td4.append(h.h_td.iloc[:4].mean() if len(h) >= 4 else np.nan)   # pandas mean skips missing, like nmean
st['td4'] = td4
P(f'last-4 history: {len(allev)} events of the 206 stocks (any F&O status); {int(st.td4.notna().sum())} F&O results '
  'with 4 earlier results')
f4 = st[st.td4.notna()].copy()
f4['pct4'] = f4.groupby('qn').td4.rank(pct=True)
o4 = {}
rng = np.random.default_rng(SEEDS['last4'])
X4, Q4 = f4.x.to_numpy(), f4.qn.to_numpy()
by4 = np.argsort(Q4, kind='stable')
N4 = dict(t5=[], t10=[])
m5, m10 = f4.pct4.to_numpy() > 0.8, f4.pct4.to_numpy() > 0.9
for b in range(B):
    xs = np.empty(len(X4))
    xs[by4] = X4[np.lexsort((rng.random(len(X4)), Q4))]
    N4['t5'].append(xs[m5].mean()); N4['t10'].append(xs[m10].mean())
N4 = {k: np.array(v) for k, v in N4.items()}
for k, m, nm in (('t5', m5, 'top fifth'), ('t10', m10, 'top tenth')):
    s = f4[m]
    o4[k] = s.x.mean()
    P(f'last-4 average three-day sum, {nm}: {len(s)} results, avg three-day {fp(s.td.mean())}%, x {fp(s.x.mean())} '
      f'(first 14 q {fp(s[s.qn <= 13].x.mean())} ({(s.qn <= 13).sum()}), last 8 q {fp(s[s.qn >= 14].x.mean())} '
      f'({(s.qn >= 14).sum()})); random-pick null {fp(N4[k].mean())}, p {fpv(p2(o4[k], N4[k]))}')
s5, s10 = f4[m5], f4[m10]
P(f'vs docs/PAST_PERFORMANCE.md (3,280-result panel incl. RELIANCE Q1 FY24 and VEDL Q4 FY26, whose events.csv in_fo is '
  f'blank): top fifth 569 trades +0.53%, here {len(s5)} {fp(s5.td.mean())}%; top tenth 292 trades +1.07% (excess over '
  f'all results +0.99), here {len(s10)} {fp(s10.td.mean())}% (x {fp(s10.x.mean())})')
assert abs(len(s5) - 569) <= 3 and abs(len(s10) - 292) <= 3 and abs(s10.td.mean() - 1.07) < 0.1, (len(s5), len(s10))
add_test(5, '5', '5j', 'Last-4 average in the top fifth: mean x this result', o4['t5'], N4['t5'], f'{int(m5.sum())} results',
         'Rebuild of PAST_PERFORMANCE.md (pre-registered TR05): habitual risers into results', unit='%')
add_test(5, '5', '5k', 'Last-4 average in the top tenth: mean x this result', o4['t10'], N4['t10'], f'{int(m10.sum())} results',
         'Rebuild of PAST_PERFORMANCE.md\'s post-hoc top tenth (292 trades; same data, so not an independent confirmation): habitual risers into results', unit='%')
qdf.round(3).to_csv(f'{OUT}/s_stock_quintiles.csv', index=False)

l4 = []
for k, m, nm in (('t5', m5, 'Last-4 average, top fifth (TR05)'), ('t10', m10, 'Last-4 average, top tenth')):
    s = f4[m]
    l4.append(f'| {nm} | {len(s)} | {fp(s.td.mean())}% | {fp(s.x.mean())} | {fp(s[s.qn <= 13].x.mean())} | '
              f'{fp(s[s.qn >= 14].x.mean())} | {fpv(p2(o4[k], N4[k]))} |')
md = ['# Stock level: does a stock\'s results move carry over?', '',
      'x = a result\'s three-day sum minus the average of all F&O results that quarter (pp). Pairs: the same stock in '
      'quarter t and t+1 (consecutive results) or t+4 (same results period a year later).', '',
      '| Statistic | Observed | Within-stock null mean | p | Across-stock null mean | p | Pairs |',
      '|---|---:|---:|---:|---:|---:|---:|']
for k, nm, n_ in (('r1', 'Pearson r, t vs t+1', len(a1)), ('r4', 'Pearson r, t vs t+4', len(a4)),
                  ('s1', 'Spearman, t vs t+1', len(a1)), ('s4', 'Spearman, t vs t+4', len(a4))):
    md.append(f'| {nm} | {fp(o5[k])} | {fp(NA[k].mean())} | {fpv(p2(o5[k], NA[k]))} | {fp(NB[k].mean())} | '
              f'{fpv(p2(o5[k], NB[k]))} | {n_:,} |')
md += ['', f'Within-stock null: {B:,} shuffles of each stock\'s own quarters (keeps each stock\'s average, so it asks whether '
       'neighbouring quarters are more alike than any two quarters of the same stock). Across-stock null: shuffles of x '
       'across stocks within each quarter (no carry-over of any kind). p two-sided, before Holm.', '',
       '## Quintiles of x in quarter t and x at the next result (quarter t+1)', '',
       '| Fifth of x(t) | Pairs | Avg x(t) | Avg x next | Next up | First 14 q | Last 8 q |', '|---|---:|---:|---:|---:|---:|---:|']
for r in qdf.itertuples():
    nm = {1: 'Bottom', 5: 'Top'}.get(r.quintile, str(r.quintile))
    md.append(f'| {nm} | {r.pairs} | {fp(r.x_t)} | {fp(r.x_next)} | {r.up_next:.0f}% | {fp(r.x_next_first14)} ({r.n_first14}) | '
              f'{fp(r.x_next_last8)} ({r.n_last8}) |')
md += ['', f'Top fifth next: p {fpv(p2(o_top, NQT["top"]))}; bottom fifth next: p {fpv(p2(o_bot, NQT["bot"]))}; top minus '
       f'bottom {fp(o_top - o_bot)}: p {fpv(p2(o_top - o_bot, NQT["spr"]))} (random-pick null: next-quarter x shuffled across '
       'the stocks with results in both quarters, within quarter). Next up = share of next results with x > 0. First 14 q / '
       'last 8 q: next result in Apr-Jun 2021 .. Apr-Jun 2024 results / Jul-Sep 2024 .. Apr-Jun 2026 results.', '',
       '## Comparison: the last-4 track record of docs/PAST_PERFORMANCE.md (rebuilt here)', '',
       '| Signal | Results | Avg three-day | Avg x | x first 14 q | x last 8 q | p |', '|---|---:|---:|---:|---:|---:|---:|'] + l4
md += ['', 'Last-4 average = mean three-day sum of the stock\'s 4 previous results (any F&O status, as in '
       'pattern_tests/past_performance/features/build_panel.py), ranked within the quarter among results with 4 earlier results. The top tenth reproduces the 292 trades at +1.07% of PAST_PERFORMANCE.md.']
open(f'{OUT}/s_table_stock.md', 'w').write('\n'.join(md) + '\n')
P('\n--- s_table_stock.md ---\n' + '\n'.join(md))

# ---------------------------------------------------------------- tests table with Holm per family
T = pd.DataFrame(TESTS)
T['holm'] = T.get('holm', pd.Series(np.nan, index=T.index))
for fam, idx in T.groupby('family').groups.items():
    if not fam.startswith('3-pairs'):
        T.loc[idx, 'holm'] = holm(T.loc[idx, 'p'].to_numpy())

def verdict(r):
    if r.holm < 0.05:
        return 'yes, beyond chance after Holm'
    if r.p < 0.05:
        return 'only before multiple-testing correction (p < 0.05, Holm p >= 0.05)'
    return 'no, within chance'

def direction(r):
    if pd.isna(r.null_mean):
        return ''
    return f' (observed {"above" if r.observed > r.null_mean else "below"} chance)'

T['meaning'] = [f'{r.question} -> {verdict(r)}{direction(r) if r.p < 0.05 else ""}' for r in T.itertuples()]
P('\n== tests (Holm within each family; 3-pairs: familywise maxT p over all pairs instead of Holm)')
for r in T.itertuples():
    P(f'{r.id} [{r.family}] {r.test}: {r.fmt(r.observed)}{r.unit} (null {"-" if pd.isna(r.null_mean) else r.fmt(r.null_mean)}'
      f'{r.unit if not pd.isna(r.null_mean) else ""}), n {r.n}, p {fpv(r.p)}, Holm {fpv(r.holm)} | {r.meaning}')
T.assign(observed=T.observed.round(4), null_mean=T.null_mean.round(4), p=T.p.round(4), holm=T.holm.round(4)).drop(
    columns=['fmt', 'question', 'unit']).to_csv(f'{OUT}/s_tests.csv', index=False)
md = ['# Sector- and stock-level tests: every test of this script', '',
      '| Item | Id | Test | Statistic | Null mean | n | p | Holm p | Meaning |', '|---|---|---|---:|---:|---|---:|---:|---|']
for r in T.itertuples():
    nm = '-' if pd.isna(r.null_mean) else r.fmt(r.null_mean) + r.unit
    md.append(f'| {r.item} | {r.id} | {r.test} | {r.fmt(r.observed)}{r.unit} | {nm} | {r.n} | {fpv(r.p)} | {fpv(r.holm)} | {r.meaning} |')
md += ['', 'Families for Holm: item 1 (1a-1h: Spearman and slopes at lag 1 and 4, NSE and custom sectors); item 2 (2a-2j); item 3 global (3a-3b); item 4 (4a-4d); item 5 (5a-5k). Item 3 pairs (3p..): p = pair '
       f'permutation p (distance of r from the pair\'s null mean, given in the Null mean column); the Holm column holds '
       f'the familywise maxT p over all sector pairs of that label set (78 NSE, 78 '
       f'custom), which already corrects for looking at every pair. All p are two-sided permutation p from {B:,} shuffles '
       '(fixed seeds): within-quarter shuffles of results across sector labels (items 1-3), of member results over index '
       'member slots (item 4), within-stock and across-stock shuffles (item 5a-5f), random picks within quarter '
       '(5g-5k). Statistic units: Spearman / r / slope unitless; rank percentile 0-100; excess and x in percentage points '
       '(three-day sum minus the all-F&O average of the quarter).']
open(f'{OUT}/s_table_tests.md', 'w').write('\n'.join(md) + '\n')
open(f'{OUT}/s_run.log', 'w').write('\n'.join(log) + '\n')
