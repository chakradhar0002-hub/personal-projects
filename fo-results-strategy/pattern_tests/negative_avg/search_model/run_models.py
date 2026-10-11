#!/usr/bin/env python3
"""Walk-forward 'ranking model for falls' (pre-registered in candidates.txt; this script implements it exactly).

Usage:
  python3 run_models.py --quarters 4-13 --tag discovery          (what this study ran)
  UNSEAL_HOLDOUT=1 python3 run_models.py --quarters 14-21 --tag holdout   (the sealed holdout re-run; NOT run here)

Outcomes are loaded only for qn <= max(scored quarters); with the holdout sealed that is qn <= 13.
"""
import argparse
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, Ridge

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
HERE = os.path.dirname(os.path.abspath(__file__))
SEAL = 14

ap = argparse.ArgumentParser()
ap.add_argument('--quarters', default='4-13')
ap.add_argument('--tag', default='discovery')
ap.add_argument('--ndraw', type=int, default=10000)
a = ap.parse_args()
q0, q1 = (int(x) for x in a.quarters.split('-'))
QS = list(range(q0, q1 + 1))
if q1 >= SEAL and os.environ.get('UNSEAL_HOLDOUT') != '1':
    sys.exit('HOLDOUT SEALED: refusing to score qn >= 14 (set UNSEAL_HOLDOUT=1 only for the holdout re-run)')
MAXQ = q1
LOG = open(f'{HERE}/{a.tag}_run.log', 'w')


def P(*x):
    s = ' '.join(str(v) for v in x)
    print(s, flush=True)
    LOG.write(s + '\n')
    LOG.flush()


# ------------------------------------------------------------------ data
FL = {}
for line in open(f'{HERE}/feature_lists.txt'):
    if line.strip():
        w, rest = line.split(':', 1)
        FL[w.split()[0]] = [c.strip() for c in rest.split(',')]
FA = pd.read_csv(f'{HERE}/features_A.csv')
FB = pd.read_csv(f'{HERE}/features_B.csv')
assert list(FA.columns[7:]) == FL['A'] and list(FB.columns[7:]) == FL['B']

out = pd.read_csv(f'{SP}/perf/features/outcomes.csv')
out = out[out.qn <= MAXQ][['symbol', 'qn', 'three_day', 'vsN_H20', 'raw_H20', 'nifty_H20', 'tradable_B']].copy()
assert out.qn.max() <= MAXQ
if os.environ.get('UNSEAL_HOLDOUT') != '1':
    assert out.qn.max() < SEAL

ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv')
ixc = pd.read_csv(f'{SP}/sector_lab/data/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])
assert ixc.index.tolist() == ses.day.tolist()
NIF = ixc['Nifty 50'].to_numpy(float)
NRET = np.r_[np.nan, NIF[1:] / NIF[:-1] - 1] * 100

A = FA.merge(out, on=['symbol', 'qn'], how='left')
A['y'] = A.three_day
A['elig'] = (A.qn <= MAXQ) & A.y.notna()
ic, ip = A.i_cut.to_numpy(int), A.i_p1.to_numpy(int)
A['nifty3'] = np.where(A.qn <= MAXQ, [NRET[c + 1:p + 1].sum() if p - c == 3 else np.nan for c, p in zip(ic, ip)],
                       np.nan)
A['short'] = -A.y - 0.17
A['short_hedged'] = -(A.y - A.nifty3) - 0.19
A['done'] = A.i_p1            # outcome complete at the close of this session
A['dec'] = A.i_cut            # decision session

B = FB.merge(out, on=['symbol', 'qn'], how='left')
B['y'] = B.vsN_H20
B['elig'] = (B.qn <= MAXQ) & (B.tradable_B == True) & B.y.notna()  # noqa: E712
B['short'] = -B.y - 0.19
B['short_raw'] = -B.raw_H20 - 0.17
B['done'] = B.i_react + 20
B['dec'] = B.i_react
P(f'loaded: A rows {len(A)} eligible (qn<={MAXQ}) {int(A.elig.sum())}; B eligible {int(B.elig.sum())}')


# ------------------------------------------------------------------ models
def keep_feats(tr, feats):
    k = []
    for f in feats:
        v = tr[f]
        if v.notna().mean() < 0.5:
            continue
        lo, hi = v.quantile(0.01), v.quantile(0.99)
        if not np.isfinite(lo) or not (hi > lo):
            continue
        k.append(f)
    return k


def wins(tr, te, k):
    lo, hi = tr[k].quantile(0.01), tr[k].quantile(0.99)
    return tr[k].clip(lo, hi, axis=1), te[k].clip(lo, hi, axis=1)


def zs(tr, te, k):
    a_, b_ = wins(tr, te, k)
    mu, sd = a_.mean(), a_.std().replace(0, 1)
    return ((a_ - mu) / sd).fillna(0).to_numpy(), ((b_ - mu) / sd).fillna(0).to_numpy()


def target(tr):
    yd = tr.y - tr.groupby('qn').y.transform('mean')
    lo, hi = yd.quantile(0.01), yd.quantile(0.99)
    return yd.clip(lo, hi).to_numpy()


HAND_LOG = []


def fit_score(model, tr, te, feats, log_key=None):
    k = keep_feats(tr, feats)
    if model == 'RIDGE':
        Ztr, Zte = zs(tr, te, k)
        return Ridge(alpha=1000).fit(Ztr, target(tr)).predict(Zte)
    if model == 'LOGIT':
        Ztr, Zte = zs(tr, te, k)
        lab = (tr.y < tr.groupby('qn').y.transform('median')).astype(int).to_numpy()
        m = LogisticRegression(C=0.01, max_iter=5000).fit(Ztr, lab)
        return -m.predict_proba(Zte)[:, 1]
    if model == 'GBM':
        Xtr, Xte = wins(tr, te, k)
        m = HistGradientBoostingRegressor(loss='squared_error', learning_rate=0.03, max_iter=200, max_depth=3,
                                          min_samples_leaf=40, l2_regularization=1.0, max_features=0.5,
                                          early_stopping=False, random_state=0)
        return m.fit(Xtr.to_numpy(), target(tr)).predict(Xte.to_numpy())
    if model == 'HAND':
        rows = []
        for f in k:
            ics = []
            for _, g in tr[[f, 'y', 'qn']].dropna().groupby('qn'):
                if len(g) >= 20 and g[f].nunique() > 1:
                    ics.append(spearmanr(g[f], g.y).statistic)
            ics = np.array([x for x in ics if np.isfinite(x)])
            if len(ics) >= 3 and ics.std(ddof=1) > 0:
                rows.append((f, ics.mean(), ics.mean() / (ics.std(ddof=1) / np.sqrt(len(ics)))))
        R = pd.DataFrame(rows, columns=['f', 'ic', 't'])
        R = R.assign(at=R.t.abs(), aic=R.ic.abs()).sort_values(['at', 'aic'], ascending=False).head(5)
        if log_key is not None:
            HAND_LOG.append(dict(key=log_key, feats='; '.join(f'{f} ({"+" if i > 0 else "-"}, IC {i:.3f}, t {t:.1f})'
                                                              for f, i, t in zip(R.f, R.ic, R.t))))
        s = np.zeros(len(te))
        for f, i in zip(R.f, R.ic):
            ref = np.sort(tr[f].dropna().to_numpy())
            x = te[f].to_numpy()
            u = (np.searchsorted(ref, x, 'left') + np.searchsorted(ref, x, 'right')) / (2 * len(ref))
            u = np.where(np.isnan(x), 0.5, u)
            s += np.sign(i) * (u - 0.5)
        return s / len(R)
    raise ValueError(model)


MODELS = ['RIDGE', 'LOGIT', 'GBM', 'HAND']
CANDS = [('MA1', 'A', 'RIDGE', 'DECILE'), ('MA2', 'A', 'RIDGE', 'BOTTOM5'), ('MA3', 'A', 'LOGIT', 'DECILE'),
         ('MA4', 'A', 'GBM', 'DECILE'), ('MA5', 'A', 'GBM', 'BOTTOM5'), ('MA6', 'A', 'HAND', 'DECILE'),
         ('MA7', 'A', 'HAND', 'BOTTOM5'),
         ('MB1', 'B', 'RIDGE', 'DECILE'), ('MB2', 'B', 'RIDGE', 'BOTTOM5'), ('MB3', 'B', 'LOGIT', 'DECILE'),
         ('MB4', 'B', 'GBM', 'DECILE'), ('MB5', 'B', 'GBM', 'BOTTOM5'), ('MB6', 'B', 'HAND', 'DECILE'),
         ('MB7', 'B', 'HAND', 'BOTTOM5')]
NQ_ALL = FA.groupby('qn').size()      # number of F&O results per quarter (features only)

SCORES = []                           # every quarter-q row: window, model, symbol, qn, s, t_dec, t_b5
for W, D, feats in (('A', A, FL['A']), ('B', B, FL['B'])):
    for model in MODELS:
        t0 = time.time()
        for q in QS:
            Dq = D.loc[D.qn == q, 'dec'].min()
            pool = D[D.elig & (D.qn < q) & (D.done < Dq)].reset_index(drop=True)
            tq = sorted(pool.qn.unique())
            ref = []
            for j in tq[-4:]:
                tr_j, te_j = pool[pool.qn != j], pool[pool.qn == j]
                ref.append(fit_score(model, tr_j, te_j, feats))
            ref = np.concatenate(ref)
            p5 = 5.0 / NQ_ALL[q - 1]
            t_dec, t_b5 = np.quantile(ref, 0.10), np.quantile(ref, p5)
            te = D[D.qn == q]
            s = fit_score(model, pool, te, feats, log_key=f'{W} q{q}')
            SCORES.append(pd.DataFrame(dict(window=W, model=model, symbol=te.symbol.to_numpy(), qn=q, s=s,
                                            t_dec=t_dec, t_b5=t_b5, n_pool=len(pool), n_ref=len(ref), p5=p5)))
        P(f'{W} {model}: done in {time.time() - t0:.0f}s')
SC = pd.concat(SCORES, ignore_index=True)
SC.to_csv(f'{HERE}/{a.tag}_scores.csv', index=False, float_format='%.6g')
pd.DataFrame(HAND_LOG).to_csv(f'{HERE}/{a.tag}_hand_features.csv', index=False)

# ------------------------------------------------------------------ evaluation
rng = np.random.default_rng(12345)


def luck_p(D, tr, nd):
    """share of random same-size-per-quarter picks (from the eligible pool) whose mean short >= the candidate's."""
    tot = np.zeros(nd)
    n = 0
    for q, g in tr.groupby('qn'):
        v = D.loc[D.elig & (D.qn == q), 'short'].to_numpy()
        m = len(g)
        idx = np.argsort(rng.random((nd, len(v))), axis=1)[:, :m]
        tot += v[idx].sum(axis=1)
        n += m
    return float((tot / n >= tr.short.mean() - 1e-12).mean())


rows, perq, trades = [], [], []
H1, H2 = [q for q in QS if q <= 6], [q for q in QS if q >= 7]
if q0 >= SEAL:
    H1, H2 = QS[:len(QS) // 2], QS[len(QS) // 2:]
for cid, W, model, thr in CANDS:
    D = A if W == 'A' else B
    sc = SC[(SC.window == W) & (SC.model == model)]
    E = D[D.elig & D.qn.isin(QS)].merge(sc[['symbol', 'qn', 's', 't_dec', 't_b5']], on=['symbol', 'qn'])
    thr_col = 't_dec' if thr == 'DECILE' else 't_b5'
    tr = E[E.s <= E[thr_col]].copy()
    base = E.short.mean()
    sh = tr.short.sort_values().to_numpy()
    wo5 = sh[:-5].mean() if len(sh) > 5 else np.nan
    qm = tr.groupby('qn').short.mean()
    ics = [spearmanr(g.s, g.y).statistic for _, g in E.groupby('qn')]
    h1, h2 = tr[tr.qn.isin(H1)].short.mean(), tr[tr.qn.isin(H2)].short.mean()
    r = dict(id=cid, window=W, model=model, threshold=thr, n=len(tr), q_with=int(tr.qn.nunique()), q_scored=len(QS),
             avg_ret=tr.y.mean(), avg_ret_vsN=(tr.y - tr.nifty3).mean() if W == 'A' else tr.y.mean(),
             short_net=tr.short.mean(), short_wo5=wo5, base_short=base, vs_base=tr.short.mean() - base,
             q_short_pos=int((qm > 0).sum()), half1=h1, half2=h2, n_half1=int(tr.qn.isin(H1).sum()),
             n_half2=int(tr.qn.isin(H2).sum()),
             t_quarters=qm.mean() / (qm.std(ddof=1) / np.sqrt(len(qm))) if len(qm) > 2 else np.nan,
             luck_p=luck_p(D, tr, a.ndraw) if len(tr) else np.nan, mean_IC=float(np.nanmean(ics)),
             hedged_short=tr.short_hedged.mean() if W == 'A' else np.nan,
             hedged_wo5=(np.sort(tr.short_hedged.to_numpy())[:-5].mean() if W == 'A' and len(tr) > 5 else np.nan),
             base_hedged=E.short_hedged.mean() if W == 'A' else np.nan,
             raw_short=tr.short_raw.mean() if W == 'B' else np.nan)
    r['eligible'] = bool(r['n'] >= 40 and r['q_with'] >= 7 and h1 > 0 and h2 > 0 and r['vs_base'] >= 0.5)
    rows.append(r)
    for q in QS:
        g = tr[tr.qn == q]
        perq.append(dict(id=cid, qn=q, n=len(g), short_net=g.short.mean() if len(g) else np.nan,
                         avg_ret=g.y.mean() if len(g) else np.nan, n_elig=int((E.qn == q).sum()),
                         base_q=E.loc[E.qn == q, 'short'].mean()))
    t_ = tr[['symbol', 'qn', 's', thr_col, 'y', 'short']].rename(columns={thr_col: 'threshold'})
    t_.insert(0, 'id', cid)
    trades.append(t_)

T = pd.DataFrame(rows)
T.to_csv(f'{HERE}/{a.tag}_table.csv', index=False, float_format='%.4g')
pd.DataFrame(perq).to_csv(f'{HERE}/{a.tag}_per_quarter.csv', index=False, float_format='%.4g')
TR = pd.concat(trades, ignore_index=True)
TR.to_csv(f'{HERE}/{a.tag}_trades.csv', index=False, float_format='%.5g')

# finalist rule (mechanical)
el = T[T.eligible].sort_values('short_wo5', ascending=False)
fin = []
for _, r in el.iterrows():
    if not fin:
        fin.append(r.id)
        continue
    if len(fin) == 2:
        break
    s1 = set(map(tuple, TR.loc[TR.id == fin[0], ['symbol', 'qn']].to_numpy()))
    s2 = set(map(tuple, TR.loc[TR.id == r.id, ['symbol', 'qn']].to_numpy()))
    if len(s1 & s2) < 0.5 * min(len(s1), len(s2)):
        fin.append(r.id)
with open(f'{HERE}/{a.tag}_finalists.txt', 'w') as fh:
    fh.write(('\n'.join(fin) if fin else 'NONE') + '\n')


def f2(x, sign=True):
    return '' if pd.isna(x) else (f'{x:+.2f}' if sign else f'{x:.2f}')


md = ['| id | window | model | thr | n | avg ret | avg ret vs Nifty | short net | short w/o 5 biggest falls | base short | '
      'vs base | quarters short+ / with trades | half 4-6 (n) | half 7-13 (n) | hedged short (A) | luck p | '
      'mean IC | eligible |', '|' + '---|' * 18]
for r in T.itertuples():
    md.append(f'| {r.id} | {r.window} | {r.model} | {r.threshold} | {r.n} | {f2(r.avg_ret)} | {f2(r.avg_ret_vsN)} | '
              f'{f2(r.short_net)} | {f2(r.short_wo5)} | {f2(r.base_short)} | {f2(r.vs_base)} | '
              f'{r.q_short_pos} / {r.q_with} | {f2(r.half1)} ({r.n_half1}) | {f2(r.half2)} ({r.n_half2}) | '
              f'{f2(r.hedged_short)} | {r.luck_p:.3f} | {r.mean_IC:+.3f} | {"YES" if r.eligible else "no"} |')
open(f'{HERE}/{a.tag}_table.md', 'w').write('\n'.join(md) + '\n')
P('\n'.join(md))
P('finalists:', fin if fin else 'NONE')
