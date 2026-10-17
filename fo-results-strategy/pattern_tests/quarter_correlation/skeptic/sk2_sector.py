"""Skeptic checks of the sector-level build: halves, LOO, thin cells, between-sector variance, pair correlations with a
156-pair familywise null, and tradable sector rules (buy last quarter's best / avoid its worst) with permutation p."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from sk_common import *

HERE = SKOUT
ev, allev, qq = load()
NQ = 22
QN = ev.qn.to_numpy(); X = ev.x.to_numpy(); TD = ev.td.to_numpy()
Qv = qq.Q.to_numpy()
B = int(os.environ.get('SK_B', 20000)); CH = 1000
MIN_N, MIN_Q = 4, 18
SHORTN = {'Financial Services': 'Fin services', 'Capital Goods': 'Cap goods', 'Automobile and Auto Components': 'Auto',
          'Healthcare': 'Healthcare', 'Information Technology': 'IT', 'Fast Moving Consumer Goods': 'FMCG',
          'Metals & Mining': 'Metals', 'Consumer Durables': 'Cons dur', 'Consumer Services': 'Cons services',
          'Oil Gas & Consumable Fuels': 'Oil & gas', 'Power': 'Power', 'Realty': 'Realty', 'Services': 'Services',
          'Chemicals': 'Chemicals', 'Construction Materials': 'Constr mat', 'Telecommunication': 'Telecom',
          'Construction': 'Construction', 'Textiles': 'Textiles'}
SHORTC = {'Banks': 'Banks', 'NBFC & financials': 'NBFC/Fin', 'IT': 'IT', 'Pharma & healthcare': 'Pharma',
          'Auto & auto parts': 'Auto', 'Capital goods & defence': 'Cap goods', 'Real estate & construction': 'Realty',
          'Cement & building materials': 'Cement', 'Metals & mining': 'Metals', 'Oil & gas': 'Oil & gas',
          'Power': 'Power', 'FMCG': 'FMCG', 'Consumer durables & retail': 'Cons dur', 'Chemicals & agro': 'Chem/agro',
          'Services, telecom & internet': 'Services'}

def setup(col, short):
    size = ev[col].value_counts()
    names = sorted(size.index, key=lambda s: (-size[s], s))
    code = ev[col].map({s: i for i, s in enumerate(names)}).to_numpy()
    K = len(names)
    cell = QN * K + code
    cnt = np.bincount(cell, minlength=NQ * K).reshape(NQ, K)
    M = np.zeros((len(ev), NQ * K)); M[np.arange(len(ev)), cell] = 1
    return dict(names=names, short=[short[s] for s in names], K=K, cell=cell, cnt=cnt, M=M)

L = {'NSE': setup('nifty_sector', SHORTN), 'custom': setup('custom_sector', SHORTC)}

def E_of(Lb, xs):            # xs (b, n) -> excess e (b, NQ, K), NaN where empty
    s = (xs @ Lb['M']).reshape(len(xs), NQ, Lb['K'])
    with np.errstate(invalid='ignore', divide='ignore'):
        return s / Lb['cnt'][None]

def rank_rows(A):
    return np.argsort(np.argsort(A, axis=-1, kind='stable'), axis=-1, kind='stable').astype(float)

def rowcorr(A, Bm):
    A = A - A.mean(-1, keepdims=True); Bm = Bm - Bm.mean(-1, keepdims=True)
    with np.errstate(invalid='ignore', divide='ignore'):
        return (A * Bm).sum(-1) / np.sqrt((A * A).sum(-1) * (Bm * Bm).sum(-1))

def persist(E, Lb, lag, ts, mn=MIN_N):
    valid = Lb['cnt'] >= mn
    rh, Xs, Ys, Ws = [], [], [], []
    for t in ts:
        if t + lag >= NQ: continue
        m = valid[t] & valid[t + lag]
        a, b = E[:, t, m], E[:, t + lag, m]
        rh.append(rowcorr(rank_rows(a), rank_rows(b)))
        n1, n2 = Lb['cnt'][t, m], Lb['cnt'][t + lag, m]
        Xs.append(a); Ys.append(b); Ws.append(n1 * n2 / (n1 + n2))
    Xa, Ya, W = np.concatenate(Xs, 1), np.concatenate(Ys, 1), np.concatenate(Ws)
    xm = (Xa * W).sum(1, keepdims=True) / W.sum(); ym = (Ya * W).sum(1, keepdims=True) / W.sum()
    slope = (W * (Xa - xm) * (Ya - ym)).sum(1) / (W * (Xa - xm) ** 2).sum(1)
    return np.mean(rh, axis=0), slope, len(rh)

def keep_of(Lb):
    return np.where((Lb['cnt'] >= MIN_N).sum(0) >= MIN_Q)[0]

def pairs_r(E, Lb, qmask=None, mn=MIN_N):
    keep = keep_of(Lb); valid = Lb['cnt'] >= mn
    out = {}
    for i in range(len(keep)):
        for j in range(i + 1, len(keep)):
            a, b = keep[i], keep[j]
            m = valid[:, a] & valid[:, b]
            if qmask is not None: m = m & qmask
            out[(Lb['short'][a], Lb['short'][b])] = rowcorr(E[:, m, a], E[:, m, b])
    return out

def between_ss(E, Lb):
    c = Lb['cnt'][None].astype(float)
    return np.nansum(c * E ** 2, axis=(1, 2))

def bw_spread(E, Lb, mn):
    valid = Lb['cnt'] >= mn
    sp = []
    for t in range(NQ):
        v = valid[t]
        sp.append(E[:, t, v].max(1) - E[:, t, v].min(1))
    return np.mean(sp, axis=0)

# ---- observed
OBS = {k: E_of(Lb, X[None])[0] for k, Lb in L.items()}

def leaders(e, Lb, mn=MIN_N, top=1):
    valid = Lb['cnt'] >= mn
    out = []
    for t in range(NQ):
        v = np.where(valid[t])[0]
        o = v[np.argsort(-e[t, v], kind='stable')]
        out.append((list(o[:top]), list(o[::-1][:top])))
    return out

# check against the builds
ldr = leaders(OBS['NSE'], L['NSE'])
tq = pd.read_csv(f'{QC}/q_quarters.csv')
assert [L['NSE']['names'][b[0]] for b, w in ldr] == list(tq.best)
assert [L['NSE']['names'][w[0]] for b, w in ldr] == list(tq.worst)
r1, s1, _ = persist(OBS['NSE'][None], L['NSE'], 1, range(NQ))
print(f'check: NSE lag-1 mean Spearman {r1[0]:+.4f} (build +0.0169), slope {s1[0]:+.4f} (build +0.0122)')
pc = pairs_r(OBS['custom'][None], L['custom'])
pn = pairs_r(OBS['NSE'][None], L['NSE'])
print(f'check: custom Cap goods/IT {pc[("Cap goods","IT")][0]:+.4f} (build +0.6413); NSE Fin services/Metals '
      f'{pn[("Fin services","Metals")][0]:+.4f} (build +0.5206)')

# ---- trade rules (selection from observed earlier quarters, applied to quarter t)
def rule_cells(k, kind, lag=1, mn=MIN_N, top=1):
    Lb = L[k]; ld = leaders(OBS[k], Lb, mn, top)
    cells = []
    for t in range(lag, NQ):
        b, w = ld[t - lag]
        sel = b if kind == 'best' else w
        for s in sel:
            if Lb['cnt'][t, s] > 0: cells.append((t, s))
    return cells

RULES = [('NSE: buy last quarter\'s best sector', 'NSE', 'best', 1, MIN_N, 1),
         ('NSE: buy last quarter\'s worst sector', 'NSE', 'worst', 1, MIN_N, 1),
         ('NSE: buy last quarter\'s top 3 sectors', 'NSE', 'best', 1, MIN_N, 3),
         ('NSE: buy last quarter\'s bottom 3 sectors', 'NSE', 'worst', 1, MIN_N, 3),
         ('NSE: buy best sector of a year ago (t-4)', 'NSE', 'best', 4, MIN_N, 1),
         ('NSE: buy worst sector of a year ago (t-4)', 'NSE', 'worst', 4, MIN_N, 1),
         ('NSE: buy last quarter\'s best, picked among sectors with 8+ results', 'NSE', 'best', 1, 8, 1),
         ('NSE: buy last quarter\'s worst, picked among sectors with 8+ results', 'NSE', 'worst', 1, 8, 1),
         ('custom: buy last quarter\'s best sector', 'custom', 'best', 1, MIN_N, 1),
         ('custom: buy last quarter\'s worst sector', 'custom', 'worst', 1, MIN_N, 1)]
RC = {nm: rule_cells(k, kind, lag, mn, top) for nm, k, kind, lag, mn, top in RULES}

# ---- null loop
rng = np.random.default_rng(20261101)
keys = QN.astype(float)
NULL = {k: dict(p1=[], s1=[], p4=[], s4=[], p1a=[], s1a=[], p1b=[], s1b=[], bss=[], sp4=[], sp8=[], pr={}, prA={}, prB={})
        for k in L}
RN = {nm: dict(res=[], qtr=[], resA=[], resB=[]) for nm in RC}
H1 = np.arange(NQ) <= 10
def rule_stats(Eb, k, cells, xsums):
    Lb = L[k]
    idx = np.array([t * Lb['K'] + s for t, s in cells])
    cn = np.array([Lb['cnt'][t, s] for t, s in cells])
    tt = np.array([t for t, s in cells])
    sums = xsums[k][:, idx]
    res = sums.sum(1) / cn.sum()
    qt = []
    for t in np.unique(tt):
        m = tt == t
        qt.append(sums[:, m].sum(1) / cn[m].sum())
    qtr = np.mean(qt, axis=0)
    mA = tt <= 10
    return res, qtr, sums[:, mA].sum(1) / cn[mA].sum(), sums[:, ~mA].sum(1) / cn[~mA].sum()

def run_stats(xs, store, rstore):
    xsums = {k: xs @ Lb['M'] for k, Lb in L.items()}
    for k, Lb in L.items():
        with np.errstate(invalid='ignore', divide='ignore'):
            E = (xsums[k].reshape(len(xs), NQ, Lb['K'])) / Lb['cnt'][None]
        d = store[k]
        a, b, _ = persist(E, Lb, 1, range(NQ)); d['p1'].append(a); d['s1'].append(b)
        a, b, _ = persist(E, Lb, 4, range(NQ)); d['p4'].append(a); d['s4'].append(b)
        a, b, _ = persist(E, Lb, 1, range(0, 10)); d['p1a'].append(a); d['s1a'].append(b)
        a, b, _ = persist(E, Lb, 1, range(11, 21)); d['p1b'].append(a); d['s1b'].append(b)
        d['bss'].append(between_ss(E, Lb)); d['sp4'].append(bw_spread(E, Lb, 4)); d['sp8'].append(bw_spread(E, Lb, 8))
        for nmq, qm, tgt in (('pr', None, d['pr']), ('prA', H1, d['prA']), ('prB', ~H1, d['prB'])):
            for pk, v in pairs_r(E, Lb, qm).items():
                tgt.setdefault(pk, []).append(v)
    for nm, k, *_ in RULES:
        res, qtr, rA, rB = rule_stats(None, k, RC[nm], xsums)
        rstore[nm]['res'].append(res); rstore[nm]['qtr'].append(qtr)
        rstore[nm]['resA'].append(rA); rstore[nm]['resB'].append(rB)

OBSS = {k: dict(p1=[], s1=[], p4=[], s4=[], p1a=[], s1a=[], p1b=[], s1b=[], bss=[], sp4=[], sp8=[], pr={}, prA={}, prB={}) for k in L}
ROBS = {nm: dict(res=[], qtr=[], resA=[], resB=[]) for nm in RC}
run_stats(X[None], OBSS, ROBS)
for b0 in range(0, B, CH):
    m = min(CH, B - b0)
    perm = np.argsort(keys[None] + rng.random((m, len(X))), axis=1)
    run_stats(X[perm], NULL, RN)

def cat(v): return np.concatenate(v) if isinstance(v, list) else v
for store in (NULL, OBSS):
    for k in store:
        for kk in list(store[k]):
            if isinstance(store[k][kk], dict):
                store[k][kk] = {pk: cat(v) for pk, v in store[k][kk].items()}
            else:
                store[k][kk] = cat(store[k][kk])
for store in (RN, ROBS):
    for nm in store:
        for kk in store[nm]: store[nm][kk] = cat(store[nm][kk])

print(f'\nnull: {B:,} within-quarter shuffles of results across sector labels (both label sets together), seed 20261101')
print('\n== persistence (items 1a/1c, 1e/1g): full and halves; MDE = 2.8 x null sd ==')
TESTS = []
for k in L:
    o, n_ = OBSS[k], NULL[k]
    for key, lab in (('p1', 'mean Spearman lag 1, all 21 pairs'), ('s1', 'weighted slope lag 1, all'),
                     ('p1a', 'mean Spearman lag 1, pairs t=0..9 (first half)'), ('s1a', 'slope lag 1, first half'),
                     ('p1b', 'mean Spearman lag 1, pairs t=11..20 (second half)'), ('s1b', 'slope lag 1, second half'),
                     ('p4', 'mean Spearman lag 4'), ('s4', 'slope lag 4')):
        p = p2c(o[key][0], n_[key])
        print(f'{k:6s} {lab:52s} obs {o[key][0]:+.3f} null {n_[key].mean():+.3f} sd {n_[key].std():.3f} '
              f'p {fpv(p)}  MDE(80%, 5%) {2.8 * n_[key].std():.3f}')
        TESTS.append(dict(test=f'{k} {lab}', obs=o[key][0], null=n_[key].mean(), p=p))

print('\n== do sector labels carry any same-quarter information? between-sector SS within quarters (all cells) ==')
for k in L:
    o, n_ = OBSS[k]['bss'][0], NULL[k]['bss']
    tot = np.sum(X ** 2)
    p = (1 + np.sum(n_ >= o)) / (len(n_) + 1)
    print(f'{k}: between-sector SS {o:.0f} = {100*o/tot:.1f}% of the within-quarter SS; null mean {n_.mean():.0f} '
          f'({100*n_.mean()/tot:.1f}%), 99th pct {np.quantile(n_, 0.99):.0f}; upper-tail p {fpv(p)}; '
          f'observed / null = {o / n_.mean():.2f}')
    TESTS.append(dict(test=f'{k} between-sector SS (upper)', obs=o, null=n_.mean(), p=p))
    for key, lab in (('sp4', 'avg best-worst spread, min 4'), ('sp8', 'avg best-worst spread, min 8')):
        p = p2c(OBSS[k][key][0], NULL[k][key])
        print(f'   {lab}: obs {OBSS[k][key][0]:+.2f} null {NULL[k][key].mean():+.2f} p {fpv(p)}')

print('\n== sector pairs: precise pair p and familywise maxT over all 156 pairs (NSE + custom) ==')
allp = []
for k in L:
    for pk, v in NULL[k]['pr'].items():
        allp.append((k, pk, OBSS[k]['pr'][pk][0], v))
mu = np.array([v.mean() for *_, v in allp])
dev = np.array([np.abs(v - m) for (_, _, _, v), m in zip(allp, mu)])      # (156, B)
maxdev = np.nanmax(dev, axis=0)
mx78 = {k: np.nanmax(np.array([np.abs(v - v.mean()) for kk, _, _, v in allp if kk == k]), axis=0) for k in L}
prow = []
for (k, pk, r, v), m in zip(allp, mu):
    d = abs(r - m)
    prow.append(dict(labels=k, pair=f'{pk[0]} / {pk[1]}', r=r, null_mean=m,
                     p_pair=(1 + np.sum(np.abs(v - m) >= d - 1e-12)) / (len(v) + 1),
                     fw78=(1 + np.sum(mx78[k] >= d - 1e-12)) / (len(v) + 1),
                     fw156=(1 + np.sum(maxdev >= d - 1e-12)) / (len(v) + 1),
                     rA=OBSS[k]['prA'][pk][0], rB=OBSS[k]['prB'][pk][0],
                     pA=p2c(OBSS[k]['prA'][pk][0], NULL[k]['prA'][pk]), pB=p2c(OBSS[k]['prB'][pk][0], NULL[k]['prB'][pk])))
PR = pd.DataFrame(prow).sort_values('p_pair')
print(PR.head(12).round(4).to_string(index=False))
print(f'null max |r - mean| over 156 pairs: median {np.median(maxdev):.2f}, 95th {np.quantile(maxdev, .95):.2f}')
print(f'pairs with pair p < 0.05: {int((PR.p_pair < 0.05).sum())} of 156 (expected about 7.8)')
PR.to_csv(f'{HERE}/sk2_pairs.csv', index=False)

# LOO, drop 2021, thicker cells for the top pairs
print('\n== top pairs: leave-one-quarter-out, drop q0-4, cells with 8+ results, NSE counterpart ==')
def pair_obs(k, a, b, qmask=None, mn=MIN_N):
    Lb = L[k]; ia, ib = Lb['short'].index(a), Lb['short'].index(b)
    e = OBS[k]; valid = Lb['cnt'] >= mn
    m = valid[:, ia] & valid[:, ib]
    if qmask is not None: m = m & qmask
    return pear(e[m, ia], e[m, ib]), int(m.sum())
for k, a, b in (('custom', 'Cap goods', 'IT'), ('NSE', 'Cap goods', 'IT'), ('NSE', 'Fin services', 'Metals'),
                ('custom', 'Banks', 'Metals'), ('custom', 'NBFC/Fin', 'Metals'), ('NSE', 'Auto', 'IT'),
                ('custom', 'Auto', 'IT'), ('NSE', 'Cons services', 'Constr mat')):
    r, m = pair_obs(k, a, b)
    loo = [(pair_obs(k, a, b, np.arange(NQ) != j)[0], qq.period[j]) for j in range(NQ)]
    lo, hi = min(loo), max(loo)
    r8, m8 = pair_obs(k, a, b, mn=8)
    rl, ml = pair_obs(k, a, b, np.arange(NQ) >= 5)
    print(f'{k:6s} {a}/{b}: r {r:+.2f} (n {m}); LOO {lo[0]:+.2f} (drop {lo[1]}) to {hi[0]:+.2f} (drop {hi[1]}); '
          f'drop q0-4 {rl:+.2f} (n {ml}); cells 8+ {r8:+.2f} (n {m8})')
    Lb = L[k]; ia, ib = Lb['short'].index(a), Lb['short'].index(b)
    print('      cells per quarter:', list(zip(Lb['cnt'][:, ia], Lb['cnt'][:, ib])))

print('\n== item 2 transitions: halves and LOO of best/worst next-quarter excess ==')
for k in L:
    ld = leaders(OBS[k], L[k]); valid = L[k]['cnt'] >= MIN_N
    exb = np.array([OBS[k][t + 1, ld[t][0][0]] if valid[t + 1, ld[t][0][0]] else np.nan for t in range(NQ - 1)])
    exw = np.array([OBS[k][t + 1, ld[t][1][0]] if valid[t + 1, ld[t][1][0]] else np.nan for t in range(NQ - 1)])
    for nm, ex in (('best', exb), ('worst', exw)):
        loo = [np.nanmean(np.delete(ex, j)) for j in range(len(ex))]
        print(f'{k} {nm}: next-quarter excess {np.nanmean(ex):+.2f} (n {np.sum(~np.isnan(ex))}); t=0..9 '
              f'{np.nanmean(ex[:10]):+.2f}, t=11..20 {np.nanmean(ex[11:]):+.2f}; LOO {min(loo):+.2f} to {max(loo):+.2f}; '
              f'per-quarter values {np.round(ex, 2).tolist()}')

print('\n== tradable sector rules: average three-day sum per result and per quarter vs all F&O (gross; net = gross - 0.17) ==')
rrows = []
for nm, k, kind, lag, mn, top in RULES:
    cells = RC[nm]; Lb = L[k]
    tt = np.array([t for t, s in cells]); cn = np.array([Lb['cnt'][t, s] for t, s in cells])
    mask = np.isin(QN, np.unique(tt))
    sel = np.zeros(len(X), bool)
    for t, s in cells: sel |= (Lb['cell'] == t * Lb['K'] + s)
    td_sel, x_sel = TD[sel], X[sel]
    allavg = TD[mask].mean()
    qt_td = [TD[sel & (QN == t)].mean() for t in np.unique(tt)]
    qt_all = [Qv[t] for t in np.unique(tt)]
    o = ROBS[nm]; nn = RN[nm]
    row = dict(rule=nm, results=int(sel.sum()), quarters=len(np.unique(tt)), avg_td=td_sel.mean(), net=td_sel.mean() - COST,
               all_avg=allavg, excess=x_sel.mean(), p_res=p2c(o['res'][0], nn['res']),
               q_avg=np.mean(qt_td), q_all=np.mean(qt_all), q_excess=o['qtr'][0], p_q=p2c(o['qtr'][0], nn['qtr']),
               q_pos_net=int(np.sum(np.array(qt_td) - COST > 0)), q_beat_all=int(np.sum(np.array(qt_td) > np.array(qt_all))),
               exA=o['resA'][0], pA=p2c(o['resA'][0], nn['resA']), exB=o['resB'][0], pB=p2c(o['resB'][0], nn['resB']),
               null_sd=nn['res'].std())
    rrows.append(row)
RR = pd.DataFrame(rrows)
pd.set_option('display.width', 300); pd.set_option('display.max_columns', 30)
print(RR.round(3).to_string(index=False))
RR.to_csv(f'{HERE}/sk2_rules.csv', index=False)
pd.DataFrame(TESTS).to_csv(f'{HERE}/sk2_tests.csv', index=False)

print('\n== top pairs: is the co-movement the market on shared result days? split e(s,t) into Nifty part and stock part ==')
N3 = ev.n3.to_numpy(); xN = N3 - ev.qn.map(ev.groupby('qn').n3.mean()).to_numpy(); xS = X - xN
EN = {k: E_of(Lb, xN[None])[0] for k, Lb in L.items()}; ES = {k: E_of(Lb, xS[None])[0] for k, Lb in L.items()}
RD = ev.i_rd.to_numpy().astype(float)
for k, a, b in (('custom', 'Cap goods', 'IT'), ('NSE', 'Fin services', 'Metals'), ('custom', 'Banks', 'Metals'),
                ('NSE', 'Auto', 'IT'), ('custom', 'Auto', 'IT')):
    Lb = L[k]; ia, ib = Lb['short'].index(a), Lb['short'].index(b)
    valid = Lb['cnt'] >= MIN_N; m = valid[:, ia] & valid[:, ib]
    # timing overlap: share of a's result sessions within 2 sessions of some b result session, per quarter
    ov = []
    for t in np.where(m)[0]:
        ra = RD[(QN == t) & (Lb['cell'] == t * Lb['K'] + ia)]; rb = RD[(QN == t) & (Lb['cell'] == t * Lb['K'] + ib)]
        ov.append(np.mean([np.min(np.abs(rb - v)) <= 2 for v in ra]))
    print(f'{k:6s} {a}/{b}: total r {pear(OBS[k][m, ia], OBS[k][m, ib]):+.2f}; Nifty-part r {pear(EN[k][m, ia], EN[k][m, ib]):+.2f}; '
          f'stock-part (vs Nifty) r {pear(ES[k][m, ia], ES[k][m, ib]):+.2f}; mean share of {a} results within 2 sessions of a {b} result {np.mean(ov):.2f}')
