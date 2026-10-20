#!/usr/bin/env python3
"""Tests A-H of PLAN.txt (pre-registered; sha256 in PLAN.sha256) on OUT/history.csv from build_history.py.

Does a stock's three-day results move in each earlier quarter (lags 1..8), or a combination of them, predict its next
three-day results move? Writes run.log, lags.csv + table_lags.md, table_components.md, table_sequences.md,
table_counts.md, table_magnitude.md, table_by_quarter.md (+ by_quarter.csv), table_tradable.md (+ csv files).
"""
import hashlib
import os
import numpy as np
import pandas as pd
from scipy.stats import rankdata

REPO = os.environ.get('REPO_ROOT', '.')
LAB = os.environ.get('LAB_ROOT', 'lab')
OUT = os.environ.get('OUT', os.path.join(REPO, 'results', 'prev_quarter_patterns'))
HERE = os.path.dirname(os.path.abspath(__file__))
B = 5000            # shuffles for IC families and group tests
B2 = 20000          # random splits for A2
MIN_Q = 20          # a quarter enters a feature's IC with at least this many results having the feature
COST = 0.17
NQ = 22
LAGS = list(range(1, 9))
HALF = {'all': list(range(NQ)), 'first': list(range(14)), 'last': list(range(14, NQ))}
SEED = dict(A1=20261101, A2=20261102, B=20261103, C=20261104, streak=20261108, D=20261109, E=20261110,
            Epart=20261111, H=20261120)

log = []
def P(*a):
    s = ' '.join(str(v) for v in a)
    log.append(s)
    print(s)

def fpc(v):                 # percent, signed 2 decimals (no "-0.00")
    return '-' if v is None or pd.isna(v) else f'{(0.0 if abs(v) < 0.005 else v):+.2f}'

def fc(v):                  # correlation, signed 3 decimals (no "-0.000")
    return '-' if v is None or pd.isna(v) else f'{(0.0 if abs(v) < 0.0005 else v):+.3f}'

def fpv(p):
    return '-' if p is None or pd.isna(p) else ('<0.001' if p < 0.001 else f'{p:.3f}')

def fsh(v):                 # share in %, no sign
    return '-' if v is None or pd.isna(v) else f'{v:.0f}%'

def holm(ps):
    ps = np.asarray(ps, float)
    adj = np.full(len(ps), np.nan)
    ok = ~np.isnan(ps)
    idx = np.where(ok)[0]
    run = 0.0
    for k, i in enumerate(idx[np.argsort(ps[idx], kind='stable')]):
        run = max(run, (len(idx) - k) * ps[i])
        adj[i] = min(1.0, run)
    return adj

def p2(obs, null):
    null = np.asarray(null, float)
    c = null.mean()
    return (1 + np.sum(np.abs(null - c) >= abs(obs - c) - 1e-12)) / (len(null) + 1)

def pup(obs, null):
    null = np.asarray(null, float)
    return (1 + np.sum(null >= obs - 1e-12)) / (len(null) + 1)

def maxT(obs, nulls):
    """single-step maxT familywise p over a family: obs (k,), nulls (B, k)"""
    mu, sd = nulls.mean(axis=0), nulls.std(axis=0)
    d_obs = np.abs(obs - mu) / sd
    mx = (np.abs(nulls - mu) / sd).max(axis=1)
    return np.array([(1 + np.sum(mx >= d - 1e-12)) / (len(mx) + 1) for d in d_obs])

# ---------------------------------------------------------------- data
P('== run_tests.py ==')
with open(os.path.join(HERE, 'PLAN.txt'), 'rb') as fh:
    sha = hashlib.sha256(fh.read()).hexdigest()
with open(os.path.join(HERE, 'PLAN.sha256')) as fh:
    sha_rec = fh.read().split()[0]
P(f'PLAN.txt sha256 {sha} (recorded {sha_rec}): {"MATCH" if sha == sha_rec else "MISMATCH"}')
assert sha == sha_rec
P(f'B = {B} shuffles (A2: {B2} random splits); seeds {SEED} (C uses seed C + L: L = 4 shares 20261108 with the streak '
  'test as pre-registered; harmless, different subsets)')
F = pd.read_csv(os.path.join(OUT, 'history.csv'))
assert len(F) == 3278
F = F.sort_values(['qn', 'symbol']).reset_index(drop=True)
QN = F.qn.to_numpy()
QIDX = [np.where(QN == t)[0] for t in range(NQ)]
X = F.x.to_numpy()
Y = F.y.to_numpy()
UPY = (Y > 0).astype(float)
qlab = F.groupby('qn').agg(period=('period', 'first'), quarter=('quarter', 'first'))
P(f'{len(F)} in_fo results, {F.symbol.nunique()} stocks, {NQ} quarters; all F&O average three-day {fpc(Y.mean())}%, '
  f'share up {UPY.mean() * 100:.1f}%')

def nq_str(t_list):
    return f'{len(t_list)} q' if t_list else '0 q'

# ---------------------------------------------------------------- engine 1: within-quarter rank ICs (shared shuffles)
def zr(v):
    r = rankdata(v)
    s = r.std()
    return (r - r.mean()) / s if s > 0 else None

def pq_ic(feats, out, seed):
    """per-quarter Spearman IC of each feature with out, and its null over B within-quarter permutations of out over
    all of the quarter's results (the same permutation for every feature)."""
    rng = np.random.default_rng(seed)
    res = {f: {} for f in feats}
    for t in range(NQ):
        idx = QIDX[t]
        n = len(idx)
        perm = rng.permuted(np.tile(np.arange(n), (B, 1)), axis=1)
        o = out[idx]
        Op = o[perm]
        for f, v in feats.items():
            fv = v[idx]
            m = ~np.isnan(fv)
            k = int(m.sum())
            if k < MIN_Q:
                continue
            zf = zr(fv[m])
            if zf is None:
                continue
            zo = zr(o[m])
            sub = Op[:, m]
            rr = np.argsort(np.argsort(sub, axis=1, kind='stable'), axis=1, kind='stable').astype(float)
            zn = (rr - (k - 1) / 2) / np.sqrt((k * k - 1) / 12)
            res[f][t] = dict(ic=float(np.mean(zf * zo)), n=k, null=(zn * zf).mean(axis=1))
    return res

def ic_summary(res, quarters, fam_name):
    """mean IC over the quarters in `quarters` that have the feature; p, maxT over the family"""
    rows, obs, nulls = [], [], []
    for f, d in res.items():
        ts = [t for t in quarters if t in d]
        if not ts:
            rows.append(dict(feature=f, quarters=0, n=0, ic=np.nan, t=np.nan, pos=0, p=np.nan, null_mean=np.nan))
            obs.append(np.nan); nulls.append(np.full(B, np.nan))
            continue
        ics = np.array([d[t]['ic'] for t in ts])
        nl = np.mean([d[t]['null'] for t in ts], axis=0)
        tt = ics.mean() / (ics.std(ddof=1) / np.sqrt(len(ics))) if len(ics) > 1 else np.nan
        rows.append(dict(feature=f, quarters=len(ts), q_from=min(ts), q_to=max(ts), n=int(sum(d[t]['n'] for t in ts)),
                         ic=ics.mean(), t=tt, pos=int((ics > 0).sum()), p=p2(ics.mean(), nl), null_mean=nl.mean()))
        obs.append(ics.mean()); nulls.append(nl)
    df = pd.DataFrame(rows)
    ok = ~np.isnan(np.array(obs))
    fw = np.full(len(df), np.nan)
    if ok.any():
        fw[ok] = maxT(np.array(obs)[ok], np.array(nulls).T[:, ok])
    df['maxT'] = fw
    df['holm'] = holm(df.p.to_numpy())
    return df

# ---------------------------------------------------------------- engine 2: group means (within-quarter shuffles)
def pq_groups(codes, vals, G, seed, nb=B):
    """codes: int per F row (-1 = outside the analysis subset); vals: dict name -> array. Per quarter: counts, observed
    group sums and null group sums under nb within-quarter permutations of the values inside the subset."""
    rng = np.random.default_rng(seed)
    res = {}
    for t in range(NQ):
        idx = QIDX[t]
        c = codes[idx]
        m = c >= 0
        ii, cc = idx[m], c[m]
        n = len(ii)
        if n == 0:
            continue
        perm = rng.permuted(np.tile(np.arange(n), (nb, 1)), axis=1)
        oh = np.zeros((n, G))
        oh[np.arange(n), cc] = 1
        d = dict(cnt=oh.sum(axis=0))
        for k, v in vals.items():
            vv = v[ii]
            d[k] = (vv @ oh, vv[perm] @ oh)
        res[t] = d
    return res

def grp_agg(res, quarters, key):
    ts = [t for t in quarters if t in res]
    if not ts:
        return None
    cnt = sum(res[t]['cnt'] for t in ts)
    so = sum(res[t][key][0] for t in ts)
    sn = sum(res[t][key][1] for t in ts)
    with np.errstate(invalid='ignore', divide='ignore'):
        return dict(ts=ts, cnt=cnt, mean=so / cnt, null=sn / cnt, tot=so.sum() / cnt.sum())

def grp_p(a, g):
    if a is None or a['cnt'][g] == 0:
        return np.nan, np.nan
    return a['mean'][g], p2(a['mean'][g], a['null'][:, g])

def grp_ss(a):
    ok = a['cnt'] > 0
    ss_o = np.sum(a['cnt'][ok] * (a['mean'][ok] - a['tot']) ** 2)
    ss_n = np.sum(a['cnt'][ok] * (a['null'][:, ok] - a['tot']) ** 2, axis=1)
    return ss_o, pup(ss_o, ss_n), ss_n.mean()

TESTS = []          # one row per test for the confirmation / tradable step
def add(fam, tid, name, obs, p_all, fw_all, p_first, fw_first, obs_first, p_last, obs_last, sign_ref=0.0,
        signed=True, trade=None, n='', quarters=''):
    if signed:
        conf = (fw_first < 0.05) and (np.sign(obs_first - sign_ref) == np.sign(obs_last - sign_ref)) and (p_last < 0.05)
    else:
        conf = (fw_first < 0.05) and (p_last < 0.05)
    TESTS.append(dict(family=fam, id=tid, test=name, obs=obs, p=p_all, fw=fw_all, p_first=p_first, fw_first=fw_first,
                      obs_first=obs_first, p_last=p_last, obs_last=obs_last, confirmed=bool(conf), trade=trade, n=n,
                      quarters=quarters))
    return bool(conf)

# ================================================================ A1: rank IC per lag
P('\n== A1. Each previous quarter individually: within-quarter Spearman of h(t-k) and x(t)')
featA = {f'h{k}': F[f'h{k}'].to_numpy() for k in LAGS}
resA1 = pq_ic(featA, X, SEED['A1'])
A1 = {h: ic_summary(resA1, HALF[h], 'A1') for h in HALF}
for k in LAGS:
    r = {h: A1[h].iloc[k - 1] for h in HALF}
    a = r['all']
    P(f'lag {k}: {a.n} results in {a.quarters} quarters (qn {a.q_from}-{a.q_to}); mean IC {fc(a.ic)} (null mean '
      f'{fc(a.null_mean)}), t {a.t:+.2f}, quarters positive {a.pos} of {a.quarters}, p {fpv(a.p)}, maxT p {fpv(a.maxT)} | '
      f'first 14 q: IC {fc(r["first"].ic)} ({r["first"].quarters} q, {r["first"].n} results) p {fpv(r["first"].p)} maxT '
      f'{fpv(r["first"].maxT)} | last 8 q: IC {fc(r["last"].ic)} ({r["last"].quarters} q, {r["last"].n} results) '
      f'p {fpv(r["last"].p)}')
    add('A1', f'A1-lag{k}', f'Rank IC of h(t-{k}) with x(t)', a.ic, a.p, a.maxT, r['first'].p, r['first'].maxT,
        r['first'].ic, r['last'].p, r['last'].ic, trade=('fifth', f'h{k}', np.sign(a.ic)), n=a.n, quarters=a.quarters)

# ================================================================ A2: direction after an up / a down
P('\n== A2. Direction: results after a lag-k up (h > 0) vs after a lag-k down')
A2rows = []
for k in LAGS:
    h = F[f'h{k}'].to_numpy()
    codes = np.where(np.isnan(h), -1, (h > 0).astype(int))         # 1 = after an up, 0 = after a down
    res = pq_groups(codes, dict(y=Y, x=X, up=UPY), 2, SEED['A2'] + k, nb=B2)
    row = dict(lag=k)
    for hh in HALF:
        ag = {v: grp_agg(res, HALF[hh], v) for v in ('y', 'x', 'up')}
        if ag['y'] is None:
            continue
        for v in ('y', 'x', 'up'):
            a = ag[v]
            dif = a['mean'][1] - a['mean'][0]
            dn = a['null'][:, 1] - a['null'][:, 0]
            row[f'{hh}_{v}_up'] = a['mean'][1] * (100 if v == 'up' else 1)
            row[f'{hh}_{v}_down'] = a['mean'][0] * (100 if v == 'up' else 1)
            row[f'{hh}_{v}_diff'] = dif * (100 if v == 'up' else 1)
            row[f'{hh}_{v}_p'] = p2(dif, dn)
        row[f'{hh}_n_up'] = int(ag['y']['cnt'][1]); row[f'{hh}_n_down'] = int(ag['y']['cnt'][0])
        row[f'{hh}_quarters'] = len(ag['y']['ts'])
    A2rows.append(row)
A2 = pd.DataFrame(A2rows)
for c in A2.columns:
    if c.endswith(('_n_up', '_n_down', '_quarters')):
        A2[c] = A2[c].astype(int)
for hh in HALF:
    A2[f'{hh}_y_holm'] = holm(A2[f'{hh}_y_p'].to_numpy())
for r in A2.itertuples():
    k = int(r.lag)
    P(f'lag {k}: {r.all_n_up + r.all_n_down} results in {r.all_quarters} quarters; after an up {r.all_n_up}: share up '
      f'{r.all_up_up:.1f}%, avg y {fpc(r.all_y_up)}%, avg x {fpc(r.all_x_up)} | after a down {r.all_n_down}: share up '
      f'{r.all_up_down:.1f}%, avg y {fpc(r.all_y_down)}%, avg x {fpc(r.all_x_down)} | difference y {fpc(r.all_y_diff)} '
      f'luck p {fpv(r.all_y_p)} Holm {fpv(r.all_y_holm)}; x {fpc(r.all_x_diff)} p {fpv(r.all_x_p)}; share up '
      f'{r.all_up_diff:+.1f} pts p {fpv(r.all_up_p)} | first 14 q diff y {fpc(r.first_y_diff)} p {fpv(r.first_y_p)} Holm '
      f'{fpv(r.first_y_holm)} ({r.first_quarters} q, {r.first_n_up + r.first_n_down} results) | last 8 q '
      f'{fpc(r.last_y_diff)} p {fpv(r.last_y_p)} ({r.last_quarters} q, {r.last_n_up + r.last_n_down} results)')
    add('A2', f'A2-lag{k}', f'Avg y after a lag-{k} up minus after a down', r.all_y_diff, r.all_y_p, r.all_y_holm,
        r.first_y_p, r.first_y_holm, r.first_y_diff, r.last_y_p, r.last_y_diff,
        trade=('side', f'h{k}', np.sign(r.all_y_diff)), n=int(r.all_n_up + r.all_n_down), quarters=int(r.all_quarters))

# table_lags
lag_rows = []
for k in LAGS:
    a1 = {h: A1[h].iloc[k - 1] for h in HALF}
    a2 = A2.iloc[k - 1]
    c1 = [t for t in TESTS if t['id'] == f'A1-lag{k}'][0]['confirmed']
    c2 = [t for t in TESTS if t['id'] == f'A2-lag{k}'][0]['confirmed']
    lag_rows.append(dict(lag=k, results=a1['all'].n, quarters=a1['all'].quarters, qn_from=a1['all'].q_from,
                         mean_ic=a1['all'].ic, t=a1['all'].t, quarters_pos=a1['all'].pos, p=a1['all'].p,
                         maxT_p=a1['all'].maxT, n_after_up=a2.all_n_up, n_after_down=a2.all_n_down,
                         share_up_after_up=a2.all_up_up, share_up_after_down=a2.all_up_down, avg_y_after_up=a2.all_y_up,
                         avg_y_after_down=a2.all_y_down, diff_y=a2.all_y_diff, luck_p=a2.all_y_p, holm_p=a2.all_y_holm,
                         diff_x=a2.all_x_diff, diff_x_p=a2.all_x_p, diff_share_up=a2.all_up_diff, diff_share_p=a2.all_up_p,
                         ic_first14=a1['first'].ic, q_first14=a1['first'].quarters, n_first14=a1['first'].n,
                         p_first14=a1['first'].p, maxT_first14=a1['first'].maxT, ic_last8=a1['last'].ic,
                         q_last8=a1['last'].quarters, n_last8=a1['last'].n, p_last8=a1['last'].p,
                         diff_y_first14=a2.first_y_diff, p_diff_first14=a2.first_y_p, holm_diff_first14=a2.first_y_holm,
                         diff_y_last8=a2.last_y_diff, p_diff_last8=a2.last_y_p, A1_confirmed=c1, A2_confirmed=c2))
LG = pd.DataFrame(lag_rows)
LG = LG.astype({c: int for c in ('results', 'quarters', 'quarters_pos', 'n_after_up', 'n_after_down', 'q_first14',
                                 'n_first14', 'q_last8', 'n_last8')})
LG.round(5).to_csv(os.path.join(OUT, 'lags.csv'), index=False)
yn = lambda b: 'yes' if b else 'no'
LAGNAME = {1: '1 (last quarter)', 2: '2', 3: '3', 4: '4 (same period, 1 year ago)', 5: '5', 6: '6', 7: '7',
           8: '8 (same period, 2 years ago)'}
md = ['# Each previous quarter, one at a time', '',
      'For every result of a stock in F&O (3,278 results, 22 quarters), the same stock\'s three-day results move k '
      'quarters earlier (any F&O status), measured against that quarter\'s average (h). Outcome: this result\'s three-day '
      'move y and its excess x over the quarter\'s F&O average. Pre-registered in '
      '`pattern_tests/prev_quarter_patterns/PLAN.txt`.', '',
      '## Rank correlation (A1) and direction (A2), all quarters', '',
      '| Lag (quarters back) | Results | Quarters | Mean IC | t | Quarters positive | p | maxT p | Up after up | Up after down | Avg y after up | Avg y after down | Difference | Luck p | Holm p | IC first 14 q | IC last 8 q | Confirmed |',
      '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
for r in LG.itertuples():
    md.append(f'| {LAGNAME[r.lag]} | {r.results:,} | {r.quarters} | {fc(r.mean_ic)} | {r.t:+.2f} | {r.quarters_pos} of '
              f'{r.quarters} | {fpv(r.p)} | {fpv(r.maxT_p)} | {fsh(r.share_up_after_up)} ({r.n_after_up:,}) | '
              f'{fsh(r.share_up_after_down)} ({r.n_after_down:,}) | {fpc(r.avg_y_after_up)}% | {fpc(r.avg_y_after_down)}% | '
              f'{fpc(r.diff_y)} | {fpv(r.luck_p)} | {fpv(r.holm_p)} | {fc(r.ic_first14)} ({r.q_first14} q) | '
              f'{fc(r.ic_last8)} ({r.q_last8} q) | {"IC " + yn(r.A1_confirmed) + ", direction " + yn(r.A2_confirmed)} |')
md += ['', '## The two halves', '',
       '| Lag | First 14 q: results | IC | p | maxT p | Diff y | p | Holm p | Last 8 q: results | IC | p | Diff y | p |',
       '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for r in LG.itertuples():
    md.append(f'| {r.lag} | {r.n_first14:,} ({r.q_first14} q) | {fc(r.ic_first14)} | {fpv(r.p_first14)} | '
              f'{fpv(r.maxT_first14)} | {fpc(r.diff_y_first14)} | {fpv(r.p_diff_first14)} | {fpv(r.holm_diff_first14)} | '
              f'{r.n_last8:,} ({r.q_last8} q) | {fc(r.ic_last8)} | {fpv(r.p_last8)} | {fpc(r.diff_y_last8)} | '
              f'{fpv(r.p_diff_last8)} |')
md += ['', 'Mean IC: Spearman rank correlation between h(t-k) and x(t) inside each quarter (quarters with 20+ results '
       'having lag k), averaged over the quarters. t: mean / standard error over quarters. p: 5,000 within-quarter '
       'shuffles (two-sided). maxT p: corrected for the 8 lags. Up after up / down: share of results with y > 0 when '
       'the lag-k result beat its quarter (h > 0) or not, with counts. Difference: avg y after up minus after down '
       '(points); luck p: 20,000 within-quarter random splits of the same sizes; Holm over the 8 lags. Confirmed: '
       'familywise p < 0.05 in the first 14 quarters (qn 0-13) and the same sign with p < 0.05 in the last 8 (qn 14-21). '
       'Lag k exists only from quarter k on (no data before Jan-Mar 2021 results), so lag 8 has 6 quarters in the first '
       'part.', '']
open(os.path.join(OUT, 'table_lags.md'), 'w').write('\n'.join(md))

# ================================================================ B: lag-1 day components
P('\n== B. Last quarter\'s three days separately (each minus the quarter mean of the same day)')
featB = {'l1_dm1': F.l1_dm1.to_numpy(), 'l1_rd': F.l1_rd.to_numpy(), 'l1_dp1': F.l1_dp1.to_numpy()}
resB = pq_ic(featB, X, SEED['B'])
BB = {h: ic_summary(resB, HALF[h], 'B') for h in HALF}
CNAME = {'l1_dm1': 'Day-1', 'l1_rd': 'Result day', 'l1_dp1': 'Day+1'}
comp_rows = []
for i, f in enumerate(featB):
    a, fi, la = BB['all'].iloc[i], BB['first'].iloc[i], BB['last'].iloc[i]
    P(f'{CNAME[f]}: {a.n} results in {a.quarters} quarters; mean IC {fc(a.ic)}, t {a.t:+.2f}, positive {a.pos} of '
      f'{a.quarters}, p {fpv(a.p)}, Holm {fpv(a.holm)} | first 14 q IC {fc(fi.ic)} p {fpv(fi.p)} Holm {fpv(fi.holm)} | '
      f'last 8 q IC {fc(la.ic)} p {fpv(la.p)}')
    c = add('B', f'B-{f}', f'Rank IC of last quarter\'s {CNAME[f]} with x(t)', a.ic, a.p, a.holm, fi.p, fi.holm, fi.ic,
            la.p, la.ic, trade=('fifth', f, np.sign(a.ic)), n=a.n, quarters=a.quarters)
    comp_rows.append(dict(component=CNAME[f], results=a.n, quarters=a.quarters, mean_ic=a.ic, t=a.t, pos=a.pos, p=a.p,
                          holm=a.holm, ic_first14=fi.ic, p_first14=fi.p, holm_first14=fi.holm, q_first14=fi.quarters,
                          ic_last8=la.ic, p_last8=la.p, q_last8=la.quarters, confirmed=c))
CB = pd.DataFrame(comp_rows)
CB.round(5).to_csv(os.path.join(OUT, 'components.csv'), index=False)

def fifth_table(col, quarters=None, label=None):
    d = F[F[col].notna()].copy()
    d['fifth'] = np.ceil(d.groupby('qn')[col].rank(pct=True) * 5).astype(int)
    rows = []
    for q5 in range(1, 6):
        s = d[d.fifth == q5]
        rows.append(dict(level=q5, n=len(s), feat=s[col].mean(), y=s.y.mean(), x=s.x.mean(), up=(s.y > 0).mean() * 100,
                         x_first=s[s.qn <= 13].x.mean(), x_last=s[s.qn >= 14].x.mean(),
                         n_first=int((s.qn <= 13).sum()), n_last=int((s.qn >= 14).sum())))
    return pd.DataFrame(rows)

FIFTH = {1: 'Bottom', 2: '2', 3: '3', 4: '4', 5: 'Top'}
md = ['# Last quarter\'s three days, separately', '',
      'Does it matter which of last quarter\'s three results days moved? Each day\'s return (Day-1, Result day, Day+1 of '
      'the result one quarter back) minus that quarter\'s average for the same day, against this result\'s excess x.', '',
      '| Last quarter\'s day | Results | Quarters | Mean IC | t | Quarters positive | p | Holm p | IC first 14 q | p | Holm p | IC last 8 q | p | Confirmed |',
      '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
for r in CB.itertuples():
    md.append(f'| {r.component} | {r.results:,} | {r.quarters} | {fc(r.mean_ic)} | {r.t:+.2f} | {r.pos} of {r.quarters} | '
              f'{fpv(r.p)} | {fpv(r.holm)} | {fc(r.ic_first14)} ({r.q_first14} q) | {fpv(r.p_first14)} | '
              f'{fpv(r.holm_first14)} | {fc(r.ic_last8)} ({r.q_last8} q) | {fpv(r.p_last8)} | {yn(r.confirmed)} |')
md += ['', 'Mean IC, p as in table_lags.md (5,000 within-quarter shuffles); Holm over the 3 days.', '',
       '## Average result by fifth of each day (fifths within each quarter)', '',
       '| Fifth | Day-1: avg y | x | Result day: avg y | x | Day+1: avg y | x |', '|---|---:|---:|---:|---:|---:|---:|']
ft = {f: fifth_table(f) for f in featB}
for q5 in range(1, 6):
    md.append(f'| {FIFTH[q5]} ({ft["l1_dm1"].n[q5 - 1]}) | ' + ' | '.join(
        f'{fpc(ft[f].y[q5 - 1])}% | {fpc(ft[f].x[q5 - 1])}' for f in featB) + ' |')
md.append('')
open(os.path.join(OUT, 'table_components.md'), 'w').write('\n'.join(md))

# ================================================================ C: sequences, streaks, alternation
P('\n== C. Up/down sequences of the last 2, 3 and 4 results (oldest first; last letter = last quarter)')
SEQ = {}
glob_rows = []
for L in (2, 3, 4):
    pats = [''.join(p) for p in __import__('itertools').product('UD', repeat=L)]
    pats = sorted(pats, key=lambda s: (-s.count('U'), s[::-1]))
    code = F[f'seq{L}'].map({p: i for i, p in enumerate(pats)}).fillna(-1).astype(int).to_numpy()
    res = pq_groups(code, dict(x=X), len(pats), SEED['C'] + L)
    SEQ[L] = dict(pats=pats, code=code, res=res)
    rows = []
    ag = {h: grp_agg(res, HALF[h], 'x') for h in HALF}
    for g, p in enumerate(pats):
        m = code == g
        row = dict(length=L, pattern=p, n=int(m.sum()), y=Y[m].mean(), x=X[m].mean(), up=UPY[m].mean() * 100)
        for h in HALF:
            mu, pv = grp_p(ag[h], g)
            row[f'x_{h}'], row[f'p_{h}'], row[f'n_{h}'] = mu, pv, int(ag[h]['cnt'][g])
        rows.append(row)
    df = pd.DataFrame(rows)
    for h in HALF:
        df[f'holm_{h}'] = holm(df[f'p_{h}'].to_numpy())
    SEQ[L]['df'] = df
    gl = {h: grp_ss(ag[h]) for h in HALF}
    glob_rows.append(dict(length=L, n=int(ag['all']['cnt'].sum()), quarters=len(ag['all']['ts']), ss=gl['all'][0],
                          ss_null=gl['all'][2], p=gl['all'][1], p_first=gl['first'][1], p_last=gl['last'][1],
                          n_first=int(ag['first']['cnt'].sum()), q_first=len(ag['first']['ts']),
                          n_last=int(ag['last']['cnt'].sum()), q_last=len(ag['last']['ts'])))
    for r in df.itertuples():
        P(f'  {r.pattern}: {r.n} results, avg y {fpc(r.y)}%, share up {r.up:.1f}%, avg x {fpc(r.x)}, p {fpv(r.p_all)}, '
          f'Holm {fpv(r.holm_all)} | first 14 q x {fpc(r.x_first)} ({r.n_first}) p {fpv(r.p_first)} Holm '
          f'{fpv(r.holm_first)} | last 8 q x {fpc(r.x_last)} ({r.n_last}) p {fpv(r.p_last)}')
        add('C', f'C{L}-{r.pattern}', f'Pattern {r.pattern} (last {L}): mean x', r.x_all, r.p_all, r.holm_all, r.p_first,
            r.holm_first, r.x_first, r.p_last, r.x_last, sign_ref=0.0, trade=('pattern', f'seq{L}', r.pattern),
            n=r.n, quarters=len(ag['all']['ts']))
GL = pd.DataFrame(glob_rows).astype({'length': int, 'n': int, 'quarters': int, 'n_first': int, 'q_first': int,
                                     'n_last': int, 'q_last': int}).astype(object)
for h in ('', '_first', '_last'):
    GL[f'holm{h}'] = holm(GL[f'p{h}'].to_numpy())
for r in GL.itertuples():
    P(f'length {r.length}: global "pattern explains x": {r.n} results in {r.quarters} quarters, between-pattern SS '
      f'{r.ss:.1f} (null mean {r.ss_null:.1f}), p {fpv(r.p)}, Holm over 3 lengths {fpv(r.holm)} | first 14 q p '
      f'{fpv(r.p_first)} Holm {fpv(r.holm_first)} ({r.n_first} results, {r.q_first} q) | last 8 q p {fpv(r.p_last)} '
      f'({r.n_last} results, {r.q_last} q)')
    add('C-global', f'Cglob{r.length}', f'Global: last-{r.length} pattern explains x', r.ss, r.p, r.holm, r.p_first,
        r.holm_first, np.nan, r.p_last, np.nan, signed=False, trade=('global', r.length, None), n=r.n,
        quarters=r.quarters)

# streaks
P('\n-- streaks: signed number of consecutive ups (+) or downs (-) ending last quarter (4 = 4 or more)')
SLEV = [4, 3, 2, 1, -1, -2, -3, -4]
SNAME = {4: '4+ ups', 3: '3 ups', 2: '2 ups', 1: '1 up', -1: '1 down', -2: '2 downs', -3: '3 downs', -4: '4+ downs'}
st = F.streak.to_numpy()
scode = np.full(len(F), -1)
for g, lv in enumerate(SLEV):
    scode[st == lv] = g
resS = pq_groups(scode, dict(x=X), len(SLEV), SEED['streak'])
agS = {h: grp_agg(resS, HALF[h], 'x') for h in HALF}
srows = []
for g, lv in enumerate(SLEV):
    m = scode == g
    row = dict(level=lv, name=SNAME[lv], n=int(m.sum()), y=Y[m].mean(), x=X[m].mean(), up=UPY[m].mean() * 100)
    for h in HALF:
        mu, pv = grp_p(agS[h], g)
        row[f'x_{h}'], row[f'p_{h}'], row[f'n_{h}'] = mu, pv, int(agS[h]['cnt'][g])
    srows.append(row)
SD = pd.DataFrame(srows)
for h in HALF:
    SD[f'holm_{h}'] = holm(SD[f'p_{h}'].to_numpy())
glS = {h: grp_ss(agS[h]) for h in HALF}
for r in SD.itertuples():
    P(f'  {r.name}: {r.n} results, avg y {fpc(r.y)}%, share up {r.up:.1f}%, avg x {fpc(r.x)}, p {fpv(r.p_all)}, Holm '
      f'{fpv(r.holm_all)} | first 14 q x {fpc(r.x_first)} ({r.n_first}) Holm {fpv(r.holm_first)} | last 8 q x '
      f'{fpc(r.x_last)} ({r.n_last}) p {fpv(r.p_last)}')
    add('C-streak', f'S{r.level:+d}', f'Streak {r.name}: mean x', r.x_all, r.p_all, r.holm_all, r.p_first, r.holm_first,
        r.x_first, r.p_last, r.x_last, trade=('streak', 'streak', r.level), n=r.n, quarters=len(agS['all']['ts']))
P(f'streak global test: {int(agS["all"]["cnt"].sum())} results in {len(agS["all"]["ts"])} quarters, SS {glS["all"][0]:.1f} '
  f'(null {glS["all"][2]:.1f}) p {fpv(glS["all"][1])} | first 14 q p {fpv(glS["first"][1])} | last 8 q p {fpv(glS["last"][1])}')
add('C-streak-global', 'Sglob', 'Global: streak level explains x', glS['all'][0], glS['all'][1], glS['all'][1],
    glS['first'][1], glS['first'][1], np.nan, glS['last'][1], np.nan, signed=False, trade=('global', 'streak', None),
    n=int(agS['all']['cnt'].sum()), quarters=len(agS['all']['ts']))
# streak as a trend: Spearman of the signed streak with x (descriptive, not in a family)
resST = pq_ic({'streak': st}, X, SEED['streak'] + 100)
stt = ic_summary(resST, HALF['all'], 'streak').iloc[0]
P(f'streak trend (descriptive, not pre-registered as a test): mean within-quarter Spearman of the signed streak with x '
  f'{fc(stt.ic)} over {stt.quarters} quarters, p {fpv(stt.p)}')

# alternation (from the length-3 shuffles)
P('\n-- alternation: UDU and DUD (last 3)')
d3 = SEQ[3]['df'].set_index('pattern')
alt = d3.loc[['UDU', 'DUD']].copy()
for h in HALF:
    alt[f'holm2_{h}'] = holm(alt[f'p_{h}'].to_numpy())
for p, r in alt.iterrows():
    P(f'  {p}: {int(r.n)} results, avg y {fpc(r.y)}%, share up {r.up:.1f}%, avg x {fpc(r.x)}, p {fpv(r.p_all)}, Holm over 2 '
      f'{fpv(r.holm2_all)} | first 14 q x {fpc(r.x_first)} Holm {fpv(r.holm2_first)} | last 8 q x {fpc(r.x_last)} p '
      f'{fpv(r.p_last)}')
    add('C-alt', f'ALT-{p}', f'Alternating {p}: mean x', r.x_all, r.p_all, r.holm2_all, r.p_first, r.holm2_first,
        r.x_first, r.p_last, r.x_last, trade=('pattern', 'seq3', p), n=int(r.n), quarters=len(grp_agg(SEQ[3]['res'],
                                                                                                    HALF['all'], 'x')['ts']))
# write sequences table
seq_out = pd.concat([SEQ[L]['df'] for L in (2, 3, 4)], ignore_index=True)
seq_out.round(5).to_csv(os.path.join(OUT, 'sequences.csv'), index=False)
SD.round(5).to_csv(os.path.join(OUT, 'streaks.csv'), index=False)
conf_of = {t['id']: t['confirmed'] for t in TESTS}
md = ['# Up/down sequences of the last 2, 3 and 4 results', '',
      'Up = the stock\'s three-day results move beat that quarter\'s average (h > 0). Patterns read oldest first: the '
      'last letter is last quarter (e.g. "DDU" = down 3 back, down 2 back, up last quarter). Only results with all the '
      'needed earlier quarters present. Avg y = this result\'s three-day move, x = its excess over the quarter\'s F&O '
      'average.', '']
for L in (2, 3, 4):
    g = GL[GL.length == L].iloc[0]
    md += [f'## Last {L} results ({2 ** L} patterns)', '',
           f'Global test "the pattern explains x": {g.n:,} results in {g.quarters} quarters, p {fpv(g.p)} (Holm over the '
           f'3 lengths {fpv(g.holm)}); first 14 q p {fpv(g.p_first)} ({g.n_first:,} results, {g.q_first} q), last 8 q p '
           f'{fpv(g.p_last)} ({g.n_last:,} results, {g.q_last} q).', '',
           '| Pattern | Count | Avg y | Share up | Avg x | p | Holm p | x first 14 q | x last 8 q | p last 8 q | Confirmed |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in SEQ[L]['df'].itertuples():
        md.append(f'| {r.pattern} | {r.n:,} | {fpc(r.y)}% | {fsh(r.up)} | {fpc(r.x)} | {fpv(r.p_all)} | {fpv(r.holm_all)} | '
                  f'{fpc(r.x_first)} ({r.n_first}) | {fpc(r.x_last)} ({r.n_last}) | {fpv(r.p_last)} | '
                  f'{yn(conf_of[f"C{L}-{r.pattern}"])} |')
    md.append('')
md += ['## Streaks', '',
       f'Consecutive ups (or downs) ending last quarter; "4+" = the last 4 all the same. {int(agS["all"]["cnt"].sum()):,} '
       f'results in {len(agS["all"]["ts"])} quarters (a streak whose start is not observed is left out). Global test p '
       f'{fpv(glS["all"][1])} (first 14 q {fpv(glS["first"][1])}, last 8 q {fpv(glS["last"][1])}). Trend (Spearman of the '
       f'signed streak with x, descriptive): {fc(stt.ic)}, p {fpv(stt.p)}.', '',
       '| Streak | Count | Avg y | Share up | Avg x | p | Holm p | x first 14 q | x last 8 q | p last 8 q | Confirmed |',
       '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
for r in SD.itertuples():
    md.append(f'| {r.name} | {r.n:,} | {fpc(r.y)}% | {fsh(r.up)} | {fpc(r.x)} | {fpv(r.p_all)} | {fpv(r.holm_all)} | '
              f'{fpc(r.x_first)} ({r.n_first}) | {fpc(r.x_last)} ({r.n_last}) | {fpv(r.p_last)} | '
              f'{yn(conf_of[f"S{r.level:+d}"])} |')
md += ['', 'Up-streak 0 = any down streak; down-streak 0 = any up streak.', '', '## Alternating patterns', '',
       '| Pattern | Count | Avg y | Share up | Avg x | p | Holm p (2) | x first 14 q | x last 8 q | p last 8 q | Confirmed |',
       '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
for p, r in alt.iterrows():
    md.append(f'| {p} | {int(r.n):,} | {fpc(r.y)}% | {fsh(r.up)} | {fpc(r.x)} | {fpv(r.p_all)} | {fpv(r.holm2_all)} | '
              f'{fpc(r.x_first)} ({int(r.n_first)}) | {fpc(r.x_last)} ({int(r.n_last)}) | {fpv(r.p_last)} | '
              f'{yn(conf_of[f"ALT-{p}"])} |')
md += ['', 'Four-quarter alternations (UDUD, DUDU) are in the last-4 table.', '',
       'p: mean x of the pattern against 5,000 within-quarter shuffles of the pattern labels (two-sided). Holm p: within '
       'the length (or over the 8 streak levels, or the 2 alternations). Global test: between-pattern sum of squares of '
       'x, upper tail. Confirmed: Holm p < 0.05 in the first 14 quarters and the same sign with p < 0.05 in the last 8.', '']
open(os.path.join(OUT, 'table_sequences.md'), 'w').write('\n'.join(md))

# ================================================================ D: counts and averages
P('\n== D. Counts and averages of earlier results (all needed lags present)')
DF_ = ['n_up4', 'n_up8', 'mean_h2', 'mean_h4', 'mean_h8', 'best4', 'worst4']
DNAME = {'n_up4': 'Ups in the last 4', 'n_up8': 'Ups in the last 8', 'mean_h2': 'Average h of the last 2',
         'mean_h4': 'Average h of the last 4', 'mean_h8': 'Average h of the last 8', 'best4': 'Best of the last 4',
         'worst4': 'Worst of the last 4'}
resD = pq_ic({f: F[f].to_numpy() for f in DF_}, X, SEED['D'])
DD = {h: ic_summary(resD, HALF[h], 'D') for h in HALF}
drows = []
for i, f in enumerate(DF_):
    a, fi, la = DD['all'].iloc[i], DD['first'].iloc[i], DD['last'].iloc[i]
    P(f'{DNAME[f]}: {a.n} results in {a.quarters} quarters (qn {a.q_from}-{a.q_to}); mean IC {fc(a.ic)}, t {a.t:+.2f}, '
      f'positive {a.pos} of {a.quarters}, p {fpv(a.p)}, maxT {fpv(a.maxT)} | first 14 q IC {fc(fi.ic)} ({fi.quarters} q) p '
      f'{fpv(fi.p)} maxT {fpv(fi.maxT)} | last 8 q IC {fc(la.ic)} p {fpv(la.p)}')
    c = add('D', f'D-{f}', f'Rank IC of {DNAME[f]} with x(t)', a.ic, a.p, a.maxT, fi.p, fi.maxT, fi.ic, la.p, la.ic,
            trade=('fifth', f, np.sign(a.ic)), n=a.n, quarters=a.quarters)
    drows.append(dict(feature=DNAME[f], col=f, results=a.n, quarters=a.quarters, mean_ic=a.ic, t=a.t, pos=a.pos, p=a.p,
                      maxT=a.maxT, ic_first14=fi.ic, q_first14=fi.quarters, p_first14=fi.p, maxT_first14=fi.maxT,
                      ic_last8=la.ic, q_last8=la.quarters, p_last8=la.p, confirmed=c))
DT = pd.DataFrame(drows)
DT.round(5).to_csv(os.path.join(OUT, 'counts.csv'), index=False)
md = ['# Counts and averages of earlier results', '',
      'How many of the stock\'s earlier results beat their quarter, and how much on average, against this result\'s '
      'excess x. Every feature needs all its earlier quarters present (e.g. "last 8" only from the 9th quarter on).', '',
      '| Feature | Results | Quarters | Mean IC | t | Quarters positive | p | maxT p | IC first 14 q | p | maxT p | IC last 8 q | p | Confirmed |',
      '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
for r in DT.itertuples():
    md.append(f'| {r.feature} | {r.results:,} | {r.quarters} | {fc(r.mean_ic)} | {r.t:+.2f} | {r.pos} of {r.quarters} | '
              f'{fpv(r.p)} | {fpv(r.maxT)} | {fc(r.ic_first14)} ({r.q_first14} q) | {fpv(r.p_first14)} | '
              f'{fpv(r.maxT_first14)} | {fc(r.ic_last8)} ({r.q_last8} q) | {fpv(r.p_last8)} | {yn(r.confirmed)} |')
md += ['', 'maxT p: corrected over the 7 features (5,000 within-quarter shuffles shared by all 7).', '']
for f, top in (('n_up4', 4), ('n_up8', 8)):
    md += [f'## {DNAME[f]}: by number of ups', '', '| Ups | Results | Avg y | Share up | Avg x | x first 14 q | x last 8 q |',
           '|---:|---:|---:|---:|---:|---:|---:|']
    for lv in range(top + 1):
        s = F[F[f] == lv]
        if len(s) == 0:
            continue
        md.append(f'| {lv} | {len(s):,} | {fpc(s.y.mean())}% | {fsh((s.y > 0).mean() * 100)} | {fpc(s.x.mean())} | '
                  f'{fpc(s[s.qn <= 13].x.mean())} ({int((s.qn <= 13).sum())}) | {fpc(s[s.qn >= 14].x.mean())} '
                  f'({int((s.qn >= 14).sum())}) |')
        P(f'  {f} = {lv}: {len(s)} results, avg y {fpc(s.y.mean())}%, share up {(s.y > 0).mean() * 100:.1f}%, x {fpc(s.x.mean())}')
    md.append('')
for f in ('mean_h2', 'mean_h4', 'mean_h8', 'best4', 'worst4'):
    t5 = fifth_table(f)
    md += [f'## {DNAME[f]}: by fifth (within each quarter)', '',
           '| Fifth | Results | Avg feature | Avg y | Share up | Avg x | x first 14 q | x last 8 q |',
           '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in t5.itertuples():
        md.append(f'| {FIFTH[r.level]} | {r.n:,} | {fpc(r.feat)} | {fpc(r.y)}% | {fsh(r.up)} | {fpc(r.x)} | '
                  f'{fpc(r.x_first)} ({r.n_first}) | {fpc(r.x_last)} ({r.n_last}) |')
        P(f'  {f} fifth {r.level}: {r.n} results, avg {fpc(r.feat)}, y {fpc(r.y)}%, x {fpc(r.x)} (first {fpc(r.x_first)}, '
          f'last {fpc(r.x_last)})')
    md.append('')
open(os.path.join(OUT, 'table_counts.md'), 'w').write('\n'.join(md))

# ================================================================ E: magnitude
P('\n== E. Magnitude: does a big mover stay a big mover? |y(t)| vs |three_day(t-k)|')
AY = np.abs(Y)
featE = {f'abs{k}': F[f'abs{k}'].to_numpy() for k in LAGS}
resE = pq_ic(featE, AY, SEED['E'])
EE = {h: ic_summary(resE, HALF[h], 'E') for h in HALF}
resV = pq_ic({'vol60': F.vol60.to_numpy(), 'vol60_ex': F.vol60_ex.to_numpy()}, AY, SEED['E'] + 50)
EV = ic_summary(resV, HALF['all'], 'vol')
for r in EV.itertuples():
    P(f'context: {r.feature} vs |y|: mean IC {fc(r.ic)} over {r.quarters} quarters ({r.n} results), p {fpv(r.p)}')

def partial_pq(k, volcol, seed):
    rng = np.random.default_rng(seed)
    res = {}
    lag = F[f'abs{k}'].to_numpy()
    vol = F[volcol].to_numpy()
    for t in range(NQ):
        idx = QIDX[t]
        m = ~np.isnan(lag[idx]) & ~np.isnan(vol[idx])
        ii = idx[m]
        n = len(ii)
        if n < MIN_Q:
            continue
        ry, rl, rv = rankdata(AY[ii]), rankdata(lag[ii]), rankdata(vol[ii])
        def resid(a):
            bta = np.polyfit(rv, a, 1)
            return a - np.polyval(bta, rv)
        ey, el = resid(ry), resid(rl)
        den = np.sqrt((ey ** 2).sum() * (el ** 2).sum())
        perm = rng.permuted(np.tile(np.arange(n), (B, 1)), axis=1)
        res[t] = dict(ic=float((ey * el).sum() / den), n=n, null=(ey[perm] * el).sum(axis=1) / den)
    return res

EP, EPX = {}, {}
for k in LAGS:
    EP[k] = partial_pq(k, 'vol60', SEED['Epart'] + k)
    EPX[k] = partial_pq(k, 'vol60_ex', SEED['Epart'] + 100 + k)
def part_summary(resd, quarters):
    rows = []
    for k in LAGS:
        d = resd[k]
        ts = [t for t in quarters if t in d]
        ics = np.array([d[t]['ic'] for t in ts])
        nl = np.mean([d[t]['null'] for t in ts], axis=0)
        rows.append(dict(lag=k, quarters=len(ts), n=int(sum(d[t]['n'] for t in ts)), ic=ics.mean(),
                         t=ics.mean() / (ics.std(ddof=1) / np.sqrt(len(ics))), pos=int((ics > 0).sum()),
                         p=p2(ics.mean(), nl)))
    df = pd.DataFrame(rows)
    df['holm'] = holm(df.p.to_numpy())
    return df.astype({'lag': int, 'quarters': int, 'n': int, 'pos': int}).astype(object)
EPS = {h: part_summary(EP, HALF[h]) for h in HALF}
EPXS = part_summary(EPX, HALF['all'])
mrows = []
for k in LAGS:
    a, fi, la = EE['all'].iloc[k - 1], EE['first'].iloc[k - 1], EE['last'].iloc[k - 1]
    pa, pfi, pla, px = EPS['all'].iloc[k - 1], EPS['first'].iloc[k - 1], EPS['last'].iloc[k - 1], EPXS.iloc[k - 1]
    P(f'lag {k}: raw: {a.n} results in {a.quarters} q, mean IC {fc(a.ic)}, t {a.t:+.2f}, positive {a.pos} of '
      f'{a.quarters}, p {fpv(a.p)}, Holm {fpv(a.holm)} (first 14 q {fc(fi.ic)} Holm {fpv(fi.holm)}, last 8 q {fc(la.ic)} '
      f'p {fpv(la.p)}) | partial (vol60): {pa.n} results, IC {fc(pa.ic)}, t {pa.t:+.2f}, positive {pa.pos} of '
      f'{pa.quarters}, p {fpv(pa.p)}, Holm {fpv(pa.holm)} (first 14 q {fc(pfi.ic)} Holm {fpv(pfi.holm)}, last 8 q '
      f'{fc(pla.ic)} p {fpv(pla.p)}) | partial (vol60_ex) {fc(px.ic)} p {fpv(px.p)}')
    c1 = add('E-raw', f'E-raw-lag{k}', f'|y| vs |three_day(t-{k})| rank IC', a.ic, a.p, a.holm, fi.p, fi.holm, fi.ic,
             la.p, la.ic, trade=('size', k, None), n=a.n, quarters=a.quarters)
    c2 = add('E-partial', f'E-part-lag{k}', f'|y| vs |three_day(t-{k})| partial rank IC given vol60', pa.ic, pa.p,
             pa.holm, pfi.p, pfi.holm, pfi.ic, pla.p, pla.ic, trade=('size', k, None), n=pa.n, quarters=pa.quarters)
    mrows.append(dict(lag=k, results=a.n, quarters=a.quarters, raw_ic=a.ic, raw_t=a.t, raw_pos=a.pos, raw_p=a.p,
                      raw_holm=a.holm, raw_ic_first14=fi.ic, raw_holm_first14=fi.holm, raw_ic_last8=la.ic,
                      raw_p_last8=la.p, part_results=pa.n, part_ic=pa.ic, part_t=pa.t, part_pos=pa.pos, part_p=pa.p,
                      part_holm=pa.holm, part_ic_first14=pfi.ic, part_holm_first14=pfi.holm, part_ic_last8=pla.ic,
                      part_p_last8=pla.p, partex_ic=px.ic, partex_p=px.p, partex_holm=px.holm, raw_confirmed=c1,
                      part_confirmed=c2))
MG = pd.DataFrame(mrows)
MG.round(5).to_csv(os.path.join(OUT, 'magnitude.csv'), index=False)
md = ['# Size of the move: do big movers stay big movers?', '',
      'Direction left aside: the size of this result\'s three-day move |y| against the size of the same stock\'s move k '
      'quarters back (raw |three-day|, %). "Partial" removes the stock\'s ordinary volatility (sd of daily returns over '
      'the 60 sessions to the cutoff, vol60): rank correlation of what is left of each after the volatility rank. This '
      'is the straddle question; no cash trade can use it and no option prices are used here.', '',
      '| Lag | Results | Quarters | Raw IC | t | Quarters positive | p | Holm p | First 14 q | Last 8 q | Partial IC | t | Quarters positive | p | Holm p | First 14 q | Last 8 q | Partial, vol w/o results days | Confirmed (raw / partial) |',
      '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
for r in MG.itertuples():
    md.append(f'| {LAGNAME[r.lag]} | {r.results:,} | {r.quarters} | {fc(r.raw_ic)} | {r.raw_t:+.2f} | {r.raw_pos} of '
              f'{r.quarters} | {fpv(r.raw_p)} | {fpv(r.raw_holm)} | {fc(r.raw_ic_first14)} | {fc(r.raw_ic_last8)} | '
              f'{fc(r.part_ic)} | {r.part_t:+.2f} | {r.part_pos} of {r.quarters} | {fpv(r.part_p)} | {fpv(r.part_holm)} | '
              f'{fc(r.part_ic_first14)} | {fc(r.part_ic_last8)} | {fc(r.partex_ic)} | {yn(r.raw_confirmed)} / '
              f'{yn(r.part_confirmed)} |')
vrow = EV.set_index('feature')
md += ['', f'For comparison, vol60 alone against |y|: mean IC {fc(vrow.loc["vol60"].ic)} (p {fpv(vrow.loc["vol60"].p)}); '
       f'with the stock\'s own results days removed from the window {fc(vrow.loc["vol60_ex"].ic)}.', '',
       'p: 5,000 within-quarter shuffles (raw: of |y|; partial: of |y|\'s volatility residual), two-sided; Holm over the '
       '8 lags. Confirmed: Holm p < 0.05 in the first 14 quarters and same sign with p < 0.05 in the last 8.', '']
for col, nm in (('abs1', 'size of last quarter\'s move |three-day(t-1)|'), ('vol60', 'ordinary volatility vol60')):
    d = F[F[col].notna()].copy()
    d['fifth'] = np.ceil(d.groupby('qn')[col].rank(pct=True) * 5).astype(int)
    md += [f'## Average size |y| by fifth of the {nm} (fifths within each quarter)', '',
           '| Fifth | Results | Avg feature | Avg abs y | Median abs y | Share abs y > 5% | First 14 q | Last 8 q |',
           '|---|---:|---:|---:|---:|---:|---:|---:|']
    for q5 in range(1, 6):
        s = d[d.fifth == q5]
        ay = s.y.abs()
        md.append(f'| {FIFTH[q5]} | {len(s):,} | {fpc(s[col].mean())}% | {fpc(ay.mean())}% | {fpc(ay.median())}% | '
                  f'{fsh((ay > 5).mean() * 100)} | {fpc(s[s.qn <= 13].y.abs().mean())}% | {fpc(s[s.qn >= 14].y.abs().mean())}% |')
        P(f'  |y| by fifth of {col}: fifth {q5}: {len(s)} results, avg {col} {s[col].mean():.2f}, avg |y| {ay.mean():.2f}%, '
          f'median {ay.median():.2f}%, share > 5% {(ay > 5).mean() * 100:.1f}%')
    md.append('')
# within each vol60 fifth: |y| by half of |lag1| (does size persistence survive inside volatility bands?)
d = F[F.abs1.notna()].copy()
d['vf'] = np.ceil(d.groupby('qn').vol60.rank(pct=True) * 5).astype(int)
d['big1'] = d.groupby(['qn', 'vf']).abs1.transform(lambda s: s > s.median())
md += ['## Inside each volatility fifth: last quarter\'s bigger half vs smaller half of moves', '',
       '| vol60 fifth | Results | Avg abs y, last quarter big | Avg abs y, last quarter small | Difference |',
       '|---|---:|---:|---:|---:|']
for q5 in range(1, 6):
    s = d[d.vf == q5]
    b_, s_ = s[s.big1].y.abs().mean(), s[~s.big1].y.abs().mean()
    md.append(f'| {FIFTH[q5]} | {len(s):,} | {fpc(b_)}% | {fpc(s_)}% | {fpc(b_ - s_)} |')
    P(f'  vol60 fifth {q5}: |y| after a big last-quarter move {b_:.2f}% vs small {s_:.2f}% ({len(s)} results)')
md.append('')
open(os.path.join(OUT, 'table_magnitude.md'), 'w').write('\n'.join(md))

# ================================================================ F: quarter by quarter
P('\n== F. Quarter by quarter')
bq = []
for t in range(1, NQ):
    idx = QIDX[t]
    row = dict(qn=t, period=qlab.period[t], quarter=qlab.quarter[t], results=len(idx), q_avg=Y[idx].mean())
    for k in LAGS:
        d = resA1[f'h{k}'].get(t)
        row[f'ic_lag{k}'] = d['ic'] if d else np.nan
        row[f'n_lag{k}'] = d['n'] if d else int(np.sum(~np.isnan(F[f'h{k}'].to_numpy()[idx])))
    h1 = F.h1.to_numpy()[idx]
    yy = Y[idx]
    u, dn = h1 > 0, (h1 <= 0) & ~np.isnan(h1)
    row.update(n_after_up=int(u.sum()), up_after_up=(yy[u] > 0).mean() * 100 if u.any() else np.nan,
               y_after_up=yy[u].mean() if u.any() else np.nan, n_after_down=int(dn.sum()),
               up_after_down=(yy[dn] > 0).mean() * 100 if dn.any() else np.nan,
               y_after_down=yy[dn].mean() if dn.any() else np.nan)
    bq.append(row)
BQ = pd.DataFrame(bq)
BQ.round(5).to_csv(os.path.join(OUT, 'by_quarter.csv'), index=False)
for r in BQ.itertuples():
    P(f'{r.period} (q{r.qn}): {r.results} results, avg {fpc(r.q_avg)}%; lag-1 IC {fc(r.ic_lag1)} ({r.n_lag1}); lag-4 IC '
      f'{fc(r.ic_lag4)} ({r.n_lag4}); up after up {r.up_after_up:.1f}% ({r.n_after_up}), up after down '
      f'{r.up_after_down:.1f}% ({r.n_after_down}); avg y after up {fpc(r.y_after_up)}%, after down {fpc(r.y_after_down)}%')
md = ['# Quarter by quarter', '',
      'Each results season on its own. Lag-1 IC: within-quarter Spearman rank correlation between the stock\'s move last '
      'quarter (vs its quarter average) and this quarter\'s move; lag-4: the same results period a year earlier. Up '
      'after up / down: share of results that rose (three-day > 0) when the stock beat / did not beat its quarter '
      'last time. Descriptive (one quarter of about 100-200 results gives an IC standard error of about 0.07-0.10).', '',
      '| Results for | Quarter | Results | Avg y | Lag-1 IC (n) | Lag-4 IC (n) | Up after up (n) | Up after down (n) | Avg y after up | Avg y after down |',
      '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
for r in BQ.itertuples():
    md.append(f'| {r.period} | {r.quarter} | {r.results} | {fpc(r.q_avg)}% | {fc(r.ic_lag1)} ({r.n_lag1}) | '
              f'{fc(r.ic_lag4) + " (" + str(r.n_lag4) + ")" if not pd.isna(r.ic_lag4) else "-"} | '
              f'{fsh(r.up_after_up)} ({r.n_after_up}) | {fsh(r.up_after_down)} ({r.n_after_down}) | '
              f'{fpc(r.y_after_up)}% | {fpc(r.y_after_down)}% |')
pos1 = int((BQ.ic_lag1 > 0).sum()); n1 = int(BQ.ic_lag1.notna().sum())
pos4 = int((BQ.ic_lag4 > 0).sum()); n4 = int(BQ.ic_lag4.notna().sum())
uu = int((BQ.up_after_up > BQ.up_after_down).sum())
md += ['', f'Lag-1 IC positive in {pos1} of {n1} quarters, lag-4 IC in {pos4} of {n4}. Share up after an up exceeded '
       f'the share up after a down in {uu} of {len(BQ)} quarters.', '',
       '## Rank correlation by quarter and lag (every earlier quarter individually)', '',
       '| Results for | ' + ' | '.join(f'Lag {k}' for k in LAGS) + ' |', '|---|' + '---:|' * len(LAGS)]
for r in BQ.itertuples():
    md.append(f'| {r.period} | ' + ' | '.join(fc(getattr(r, f'ic_lag{k}')) for k in LAGS) + ' |')
md.append('| Mean | ' + ' | '.join(fc(BQ[f'ic_lag{k}'].mean()) for k in LAGS) + ' |')
md.append('| Quarters positive | ' + ' | '.join(f'{int((BQ[f"ic_lag{k}"] > 0).sum())} of {int(BQ[f"ic_lag{k}"].notna().sum())}'
                                             for k in LAGS) + ' |')
md.append('')
P(f'lag-1 IC positive in {pos1} of {n1} quarters; lag-4 in {pos4} of {n4}; up-after-up share > up-after-down share in '
  f'{uu} of {len(BQ)} quarters')
# after the fact (seen in this table, not a pre-registered split): the lag-1 sign by period
md += ['## After the fact: last quarter\'s result by period (not a pre-registered test)', '',
       '| Results for | Quarters | Mean lag-1 IC | Quarters with IC < 0 | After an up: results, avg y | After a down: results, avg y | After a down, net of 0.17% | Quarters where after-a-down beat after-an-up |',
       '|---|---:|---:|---:|---:|---:|---:|---:|']
for lo, hi in ((1, 7), (8, 21), (14, 21)):
    bw = BQ[(BQ.qn >= lo) & (BQ.qn <= hi)]
    w = F[(F.qn >= lo) & (F.qn <= hi) & F.h1.notna()]
    u = w.h1 > 0
    nneg, nbeat = int((bw.ic_lag1 < 0).sum()), int((bw.y_after_down > bw.y_after_up).sum())
    md.append(f'| {qlab.period[lo]} to {qlab.period[hi]} | {len(bw)} | {fc(bw.ic_lag1.mean())} | {nneg} of {len(bw)} | '
              f'{int(u.sum()):,}, {fpc(w.y[u].mean())}% | {int((~u).sum()):,}, {fpc(w.y[~u].mean())}% | '
              f'{fpc(w.y[~u].mean() - COST)}% | {nbeat} of {len(bw)} |')
    P(f'after the fact, qn {lo}-{hi} ({qlab.period[lo]} to {qlab.period[hi]}): mean lag-1 IC {fc(bw.ic_lag1.mean())}, '
      f'negative in {nneg} of {len(bw)} quarters; after a lag-1 up {int(u.sum())} results avg y {fpc(w.y[u].mean())}%, '
      f'after a down {int((~u).sum())} avg y {fpc(w.y[~u].mean())}% (net {fpc(w.y[~u].mean() - COST)}%); after-a-down '
      f'beat after-an-up in {nbeat} of {len(bw)} quarters')
md += ['', 'Early quarters leaned to momentum, later quarters to a mild reversal; over all 21 quarters the two cancel '
       '(mean IC in table_lags.md). The split was chosen after looking at the table, so it is not evidence on its own, '
       'and buying after a down made about nothing after costs even in the reversal period.', '']
open(os.path.join(OUT, 'table_by_quarter.md'), 'w').write('\n'.join(md))

# ================================================================ G: confirmation summary
P('\n== G. Confirmation (familywise significant in qn 0-13 AND same sign, p < 0.05 in qn 14-21) and familywise p < 0.05 '
  'on all quarters')
TT = pd.DataFrame(TESTS)
TT.drop(columns='trade').round(6).to_csv(os.path.join(OUT, 'all_tests.csv'), index=False)
P(f'{len(TT)} tests in total: ' + ', '.join(f'{k} {v}' for k, v in TT.family.value_counts(sort=False).items()))
for r in TT[(TT.confirmed) | (TT.fw < 0.05)].itertuples():
    P(f'  {r.id} [{r.family}] {r.test}: obs {r.obs:+.4f}, p {fpv(r.p)}, familywise {fpv(r.fw)} | first 14 q familywise '
      f'{fpv(r.fw_first)} (obs {r.obs_first:+.4f}) | last 8 q p {fpv(r.p_last)} (obs {r.obs_last:+.4f}) | '
      f'confirmed {yn(r.confirmed)}')
P(f'confirmed: {int(TT.confirmed.sum())}; familywise p < 0.05 on all quarters: {int((TT.fw < 0.05).sum())}; raw p < 0.05: '
  f'{int((TT.p < 0.05).sum())} of {len(TT)} (expected by chance about {0.05 * len(TT):.0f})')
for fam in TT.family.unique():
    s = TT[TT.family == fam]
    P(f'  {fam}: {len(s)} tests, smallest p {fpv(s.p.min())} ({s.loc[s.p.idxmin(), "id"]}), smallest familywise p '
      f'{fpv(s.fw.min())}, confirmed {int(s.confirmed.sum())}')

# ================================================================ H: tradable versions
P('\n== H. Tradable versions of anything confirmed or familywise p < 0.05 on all quarters')
qual = TT[(TT.confirmed) | (TT.fw < 0.05)]
tr_rows, tr_q = [], []
md = ['# Tradable versions', '',
      'Item H of the plan: anything CONFIRMED (familywise significant in the first 14 quarters and same sign, p < 0.05 in '
      'the last 8) or with a familywise p below 0.05 on all quarters, traded as buy (or short) at the cutoff close, sell '
      'at the Day+1 close, after 0.17% round-trip costs.', '']
size_q = qual[qual.family.str.startswith('E-')]
dir_q = qual[~qual.family.str.startswith('E-')]

TNAME = {**{f'h{k}': f'lag-{k} result' for k in LAGS}, 'l1_dm1': "last quarter's Day-1", 'l1_rd': "last quarter's "
         'Result day', 'l1_dp1': "last quarter's Day+1", **{f: DNAME[f].replace('Average h', 'average').lower() for f in DF_}}

def trade_mask(trade):
    kind, col, arg = trade
    if kind == 'fifth':
        v = F[col]
        pct = v.groupby(F.qn).rank(pct=True)
        m = (pct > 0.8) if arg > 0 else (pct <= 0.2)
        return m.fillna(False).to_numpy(), 1
    if kind == 'side':
        h = F[col].to_numpy()
        return ((h > 0) if arg > 0 else (h <= 0)) & ~np.isnan(h), 1
    if kind == 'pattern':
        m = (F[col] == arg).to_numpy()
        return m, None
    if kind == 'streak':
        return (F.streak == arg).to_numpy(), None
    return None, None

if len(dir_q) == 0:
    md += ['**Nothing on direction qualified.** No direction test (A1, A2, B, C, streaks, alternation, D) was confirmed '
           'or reached a familywise p below 0.05 on all quarters, so there is no buy/sell rule to build from the earlier '
           'quarters\' three-day moves.', '']
    P('direction: nothing qualified -> no tradable version')
else:
    seen = set()
    for r in dir_q.itertuples():
        m, side = trade_mask(r.trade)
        if m is None:
            md.append(f'- {r.test}: a global test; no single trade defined from it (see table_sequences.md).')
            continue
        if side is None:
            side = 1 if r.obs > 0 else -1
        key = (r.trade[0], r.trade[1], str(r.trade[2]))
        if key in seen:
            continue
        seen.add(key)
        s = F[m].copy()
        s['gross'] = side * s.y
        s['net'] = s.gross - COST
        codes = m.astype(int)
        res = pq_groups(codes, dict(g=side * Y), 2, SEED['H'] + len(tr_rows))
        a = grp_agg(res, HALF['all'], 'g')
        luck = p2(a['mean'][1], a['null'][:, 1])
        pq = s.groupby('qn').agg(n=('net', 'size'), gross=('gross', 'mean'), net=('net', 'mean'))
        no5 = s.net.sort_values().iloc[:-5].mean() if len(s) > 5 else np.nan
        ov_l = s.lag10vol.sum(); ov_p = s.pp_top10.sum()
        rest = s[~s.lag10vol & ~s.pp_top10]
        kind, col, arg = r.trade
        nm = TNAME.get(col, col)
        lab = {'fifth': f'{"Top" if arg > 0 else "Bottom"} fifth of {nm}', 'side': f'After a {nm} {"up" if arg > 0 else "down"}',
               'pattern': f'Pattern {arg}', 'streak': SNAME.get(arg, str(arg))}[kind]
        row = dict(id=r.id, test=r.test, signal=lab, confirmed=r.confirmed, fw_p=r.fw, side='long' if side > 0 else 'short',
                   trades=len(s), avg_gross=s.gross.mean(),
                   avg_net=s.net.mean(), win=(s.net > 0).mean() * 100, q_pos=int((pq.net > 0).sum()), q_n=len(pq),
                   net_no5=no5, net_first14=s[s.qn <= 13].net.mean(), n_first14=int((s.qn <= 13).sum()),
                   net_last8=s[s.qn >= 14].net.mean(), n_last8=int((s.qn >= 14).sum()), luck_p=luck,
                   overlap_lag10=int(ov_l), overlap_top10=int(ov_p), n_rest=len(rest), net_rest=rest.net.mean())
        tr_rows.append(row)
        for q, rr in pq.iterrows():
            tr_q.append(dict(id=r.id, qn=q, period=qlab.period[q], n=int(rr.n), gross=rr.gross, net=rr.net))
        P(f'{r.id} ({row["side"]}): {len(s)} trades, avg gross {fpc(row["avg_gross"])}%, net {fpc(row["avg_net"])}%, win '
          f'{row["win"]:.1f}%, quarters positive {row["q_pos"]} of {row["q_n"]}, without 5 best {fpc(no5)}%, first 14 q '
          f'{fpc(row["net_first14"])}% ({row["n_first14"]}), last 8 q {fpc(row["net_last8"])}% ({row["n_last8"]}), luck '
          f'p {fpv(luck)}; overlap lag10+volume {ov_l}, last-4 top tenth {ov_p}; the other {len(rest)} trades net '
          f'{fpc(rest.net.mean())}%')
    if tr_rows:
        TR = pd.DataFrame(tr_rows)
        TR.round(5).to_csv(os.path.join(OUT, 'tradable.csv'), index=False)
        pd.DataFrame(tr_q).round(5).to_csv(os.path.join(OUT, 'tradable_per_quarter.csv'), index=False)
        md += ['| Signal (test) | Confirmed | Familywise p | Side | Trades | Avg gross | Avg net | Win rate | Quarters positive | Without 5 best | First 14 q | Last 8 q | Luck p | Overlap lag 10% + volume | Overlap last-4 top tenth | Other trades: net |',
               '|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for r in TR.itertuples():
            md.append(f'| {r.signal} ({r.id}) | {yn(r.confirmed)} | {fpv(r.fw_p)} | {r.side} | {r.trades:,} | '
                      f'{fpc(r.avg_gross)}% | {fpc(r.avg_net)}% | {r.win:.0f}% | '
                      f'{r.q_pos} of {r.q_n} | {fpc(r.net_no5)}% | {fpc(r.net_first14)}% ({r.n_first14}) | '
                      f'{fpc(r.net_last8)}% ({r.n_last8}) | {fpv(r.luck_p)} | {r.overlap_lag10} | {r.overlap_top10} | '
                      f'{fpc(r.net_rest)}% ({r.n_rest}) |')
        md += ['', f'{int(TR.confirmed.sum())} of {len(TR)} confirmed. Avg gross / net: per trade, % (net = gross - 0.17). '
               'Without 5 best: net average after dropping the 5 best trades. First 14 q / last 8 q: net, with trade '
               'counts. Luck p: against random picks of the same size in each quarter (5,000). Overlap: trades that are '
               'also lag 10% + volume rule trades (results/lag10_volume/trades.csv) or in the last-4 top tenth of '
               'PAST_PERFORMANCE.md; other trades: the net average of the trades in neither.', '',
               '### Per quarter (net of 0.17%, trades in brackets; q0 = Jan-Mar 2021 results ... q21 = Apr-Jun 2026)', '',
               '| Signal | ' + ' | '.join(
            f'q{q}' for q in range(NQ)) + ' |', '|---|' + '---:|' * NQ]
        tq = pd.DataFrame(tr_q)
        for i_ in TR.id:
            s = tq[tq.id == i_].set_index('qn')
            md.append(f'| {i_} | ' + ' | '.join(f'{fpc(s.net[q])} ({s.n[q]})' if q in s.index else '-' for q in range(NQ))
                      + ' |')
        md.append('')
if len(size_q):
    md += ['## Size of the move (item E)', '',
           f'{len(size_q)} magnitude tests passed (' + ', '.join(size_q.id) + '). They say how BIG the next results move '
           'tends to be, not which way, so there is no buy/sell version in cash. Using it needs option prices (a straddle '
           'on stocks whose results moves have been big), which this study does not have; see table_magnitude.md for '
           'the sizes by fifth.', '']
    P(f'size: {len(size_q)} magnitude tests qualify ({", ".join(size_q.id)}); no cash trade (needs option prices)')
if len(qual) == 0:
    md += ['Nothing qualified: no test was confirmed or reached a familywise p below 0.05 on all quarters.', '']
open(os.path.join(OUT, 'table_tradable.md'), 'w').write('\n'.join(md))

# ================================================================ log
dev = ['', '== DEVIATIONS from PLAN.txt',
       '- Global "pattern explains x" tests (C lengths, streaks) use the upper tail of the between-pattern sum of '
       'squares (a variance statistic: only large values mean the pattern explains x), not "two-sided around the null '
       'mean" as the plan\'s general wording for group-mean tests says. Per-pattern tests are two-sided as planned.',
       '- Added (descriptive, not in any family): the share-up and x differences in A2 with their own p, the signed-streak '
       'trend IC, vol60 vs |y| context ICs, |y| by fifth tables, in H a luck p against random picks of the same size '
       'in each quarter (5,000 shuffles), and in F an after-the-fact split of the lag-1 result by period (qn 1-7, 8-21, '
       '14-21), chosen after seeing the quarter table: descriptive only, no p value.',
       '- Seeds: C length 4 uses 20261104 + 4 = 20261108, the same seed as the streak test, exactly as pre-registered.']
with open(os.path.join(OUT, 'build.log')) as fh:
    blog = fh.read().rstrip('\n').split('\n')
with open(os.path.join(OUT, 'run.log'), 'w') as fh:
    fh.write('\n'.join(blog + [''] + log + dev) + '\n')
print('\n'.join(dev))
