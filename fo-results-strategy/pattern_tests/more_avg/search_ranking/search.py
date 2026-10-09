#!/usr/bin/env python3
"""Walk-forward ranking-model search on DISCOVERY quarters only (see candidates.txt, written before this ran).

Outcomes: tafa/C_post_results/trades.csv, rows with qn >= 14 are DROPPED immediately after loading (sealed holdout).
Training for scored quarter q uses winners with qn < q only; scored quarters q = 4..13.
"""
import os
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, Ridge

warnings.filterwarnings('ignore')
HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.environ.get('LAB_ROOT', os.path.abspath(os.path.join(HERE, '..', '..')))  # scratch data folder
COST = 0.19
DISC_MAX = 13
Q_SCORED = list(range(4, DISC_MAX + 1))
LOG = open(f'{HERE}/run.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')
    LOG.flush()


FEATS = ['cut_rsi14', 'rx_rsi14', 'XN', 'lvol', 'rx_gap_pct', 'rx_don20_break_up', 'BREAKOUT_VOL', 'pre21_rel',
         'rx_close_vs_sma50_pct', 'rx_close_vs_sma200_pct', 'sec21_rel', 'rq_pat_yoy_pct', 'rq_sales_yoy_pct',
         'log_mcap']

# ------------------------------------------------------------------ data (holdout outcomes sealed)
tr = pd.read_csv(f'{SP}/tafa/C_post_results/trades.csv', usecols=['symbol', 'qn', 'i_react', 'raw_H20', 'nifty_H20'])
tr = tr[tr.qn <= DISC_MAX].copy()                       # <-- holdout rows dropped before anything else
assert tr.qn.max() <= DISC_MAX
tr['vsN_net'] = tr.raw_H20 - tr.nifty_H20 - COST
fr = pd.read_csv(f'{HERE}/features_rank.csv')
fr = fr[fr.qn <= DISC_MAX].copy()
d = fr.merge(tr[['symbol', 'qn', 'i_react', 'vsN_net']], on=['symbol', 'qn', 'i_react'], how='left', validate='1:1')
assert d.vsN_net.notna().all() and d.qn.max() <= DISC_MAX
fe = pd.read_csv(f'{SP}/tafa/C_post_results/features.csv', usecols=['symbol', 'qn', 'cut_rsi14', 'XN'])
fe = fe[fe.qn <= DISC_MAX]
W = d[d.W].reset_index(drop=True)                        # winners XN > 4, qn 0..13
P(f'winners qn 0..13: {len(W)}; scored quarters {Q_SCORED[0]}..{Q_SCORED[-1]}: {int(W.qn.isin(Q_SCORED).sum())}')


# ------------------------------------------------------------------ preprocessing / models
def prep_fit(Xtr):
    lo = np.nanpercentile(Xtr, 1, axis=0)
    hi = np.nanpercentile(Xtr, 99, axis=0)
    Xc = np.clip(Xtr, lo, hi)
    med = np.nanmedian(Xc, axis=0)
    Xi = np.where(np.isnan(Xc), med, Xc)
    mu, sd = Xi.mean(0), Xi.std(0)
    sd[sd == 0] = 1.0
    return dict(lo=lo, hi=hi, med=med, mu=mu, sd=sd)


def prep_apply(X, p, impute=True):
    Xc = np.clip(X, p['lo'], p['hi'])
    Xc = np.where(np.isnan(X), np.nan, Xc)
    if not impute:
        return Xc
    Xi = np.where(np.isnan(Xc), p['med'], Xc)
    return (Xi - p['mu']) / p['sd']


def ecdf(pool, x):
    s = np.sort(pool)
    return np.searchsorted(s, x, side='right') / len(s)


def fit_score(model, trn, tst):
    """Returns (scores on training rows, scores on test rows, info)."""
    if model == 'HAND':
        st = ecdf(trn.cut_rsi14.to_numpy(), trn.cut_rsi14.to_numpy()) + ecdf(trn.XN.to_numpy(), trn.XN.to_numpy())
        ss = ecdf(trn.cut_rsi14.to_numpy(), tst.cut_rsi14.to_numpy()) + ecdf(trn.XN.to_numpy(), tst.XN.to_numpy())
        return st, ss, None
    Xtr, Xte = trn[FEATS].to_numpy(float), tst[FEATS].to_numpy(float)
    y = trn.vsN_net.to_numpy(float)
    yc = np.clip(y, np.percentile(y, 5), np.percentile(y, 95))
    p = prep_fit(Xtr)
    if model == 'RIDGE':
        m = Ridge(alpha=50.0, fit_intercept=True).fit(prep_apply(Xtr, p), yc)
        return m.predict(prep_apply(Xtr, p)), m.predict(prep_apply(Xte, p)), m.coef_
    if model == 'LOGIT':
        m = LogisticRegression(penalty='l2', C=0.05, solver='lbfgs', max_iter=2000).fit(prep_apply(Xtr, p),
                                                                                        (y > 0).astype(int))
        return m.predict_proba(prep_apply(Xtr, p))[:, 1], m.predict_proba(prep_apply(Xte, p))[:, 1], m.coef_[0]
    if model == 'GBM':
        m = HistGradientBoostingRegressor(loss='squared_error', learning_rate=0.03, max_iter=150, max_depth=2,
                                          min_samples_leaf=15, l2_regularization=1.0, early_stopping=False,
                                          random_state=0)
        m.fit(prep_apply(Xtr, p, impute=False), yc)
        return m.predict(prep_apply(Xtr, p, impute=False)), m.predict(prep_apply(Xte, p, impute=False)), None
    raise ValueError(model)


# ------------------------------------------------------------------ walk-forward
MODELS = ['RIDGE', 'LOGIT', 'GBM', 'HAND']
SEL = {'T25': None, 'T5': 5, 'T3': 3}
picks = {}          # name -> list of row indices of W
coef_rows = []
thr_rows = []
for model in MODELS:
    for s in SEL:
        picks[f'{model}_{s}'] = []
    if model in ('RIDGE', 'HAND'):
        picks[f'{model}_RANKQ25'] = []
for q in Q_SCORED:
    trn = W[W.qn < q]
    tst = W[W.qn == q]
    assert (trn.i_react + 20 < tst.i_react.min()).all(), q        # all training outcomes known before entry
    nq_tr = trn.qn.nunique()
    for model in MODELS:
        st, ss, info = fit_score(model, trn, tst)
        if info is not None and model == 'RIDGE':
            coef_rows.append(dict(q=q, model=model, **dict(zip(FEATS, np.round(info, 3)))))
        for s, k in SEL.items():
            f = 0.25 if k is None else min(1.0, k * nq_tr / len(trn))
            thr = np.quantile(st, 1 - f)
            sel = tst.index[ss >= thr].tolist()
            picks[f'{model}_{s}'] += sel
            thr_rows.append(dict(q=q, cand=f'{model}_{s}', n_train=len(trn), frac=round(f, 3), thr=thr,
                                 n_winners_q=len(tst), n_sel=len(sel)))
        if model in ('RIDGE', 'HAND'):
            ntop = int(np.ceil(0.25 * len(tst)))
            order = np.argsort(-ss, kind='stable')[:ntop]
            picks[f'{model}_RANKQ25'] += tst.index[order].tolist()

ID = {'RIDGE_T25': 'C01', 'RIDGE_T5': 'C02', 'RIDGE_T3': 'C03', 'LOGIT_T25': 'C04', 'LOGIT_T5': 'C05',
      'LOGIT_T3': 'C06', 'GBM_T25': 'C07', 'GBM_T5': 'C08', 'GBM_T3': 'C09', 'HAND_T25': 'C10', 'HAND_T5': 'C11',
      'HAND_T3': 'C12', 'RIDGE_RANKQ25': 'D13', 'HAND_RANKQ25': 'D14'}


def stats(v, q):
    v = np.asarray(v, float)
    q = np.asarray(q)
    if len(v) == 0:
        return dict(n=0)
    qm = pd.Series(v).groupby(q).mean()
    s = np.sort(v)
    t = qm.mean() / (qm.std(ddof=1) / np.sqrt(len(qm))) if len(qm) > 2 and qm.std(ddof=1) > 0 else np.nan
    return dict(n=len(v), avg=v.mean(), median=float(np.median(v)), up_pct=(v > 0).mean() * 100,
                wo5=s[:-5].mean() if len(s) > 5 else np.nan, wo10=s[:-10].mean() if len(s) > 10 else np.nan,
                nq=len(qm), q_pos=int((qm > 0).sum()), t_q=t, best=s[-1], worst=s[0])


# references
base = d[(d.XN > 4) & (d.cut_rsi14 > 50)]
refs = {'R_BASE_0_13': base, 'R_BASE_4_13': base[base.qn >= 4], 'R_WIN_4_13': W[W.qn >= 4]}
rows = []
for name, x in refs.items():
    rows.append(dict(id=name, cand=name, eligible=False, **stats(x.vsN_net, x.qn)))
assert rows[0]['n'] == 122 and abs(rows[0]['avg'] - 2.65) < 0.01, rows[0]
BAR = max(rows[0]['wo5'], rows[1]['wo5']) + 0.5
P(f"baseline wo5: qn0-13 {rows[0]['wo5']:+.3f}, qn4-13 {rows[1]['wo5']:+.3f} -> BAR = {BAR:+.3f}")

trades = []
for name, idx in picks.items():
    x = W.loc[sorted(set(idx))]
    assert len(x) == len(idx)
    rows.append(dict(id=ID[name], cand=name, eligible=ID[name].startswith('C'), **stats(x.vsN_net, x.qn)))
    t = x[['symbol', 'quarter', 'qn', 'reaction_day', 'XN', 'cut_rsi14', 'rx_rsi14', 'vsN_net']].copy()
    t.insert(0, 'cand', name)
    trades.append(t)
res = pd.DataFrame(rows)
res['qualifies'] = res.eligible & (res.n >= 35) & (res.nq >= 7) & (res.wo5 >= BAR)
res.to_csv(f'{HERE}/discovery_results.csv', index=False, float_format='%.4f')
pd.concat(trades).to_csv(f'{HERE}/discovery_trades.csv', index=False, float_format='%.4f')
pd.DataFrame(thr_rows).to_csv(f'{HERE}/thresholds.csv', index=False, float_format='%.4f')
pd.DataFrame(coef_rows).to_csv(f'{HERE}/ridge_coefs.csv', index=False)

pd.set_option('display.width', 250)
P(res[['id', 'cand', 'n', 'avg', 'median', 'wo5', 'wo10', 'up_pct', 'q_pos', 'nq', 't_q', 'best', 'worst',
       'qualifies']].round(2).to_string(index=False))

# per-quarter table for all
pq = []
for t in trades:
    g = t.groupby('qn').vsN_net.agg(['size', 'mean'])
    for qq, r in g.iterrows():
        pq.append(dict(cand=t.cand.iloc[0], qn=qq, n=int(r['size']), avg=r['mean']))
pq = pd.DataFrame(pq)
pq.to_csv(f'{HERE}/discovery_per_quarter.csv', index=False, float_format='%.3f')
P('\nper quarter n / avg (qn 4..13):')
P(pq.pivot(index='cand', columns='qn', values='avg').round(1).to_string())
P(pq.pivot(index='cand', columns='qn', values='n').fillna(0).astype(int).to_string())

# markdown table
md = ['| id | candidate | n | avg | w/o best 5 | median | quarters + / with trades | qualifies |',
      '|---|---|---|---|---|---|---|---|']
for _, r in res.iterrows():
    md.append(f"| {r.id} | {r.cand} | {r.n} | {r.avg:+.2f} | {r.wo5:+.2f} | {r['median']:+.2f} | "
              f"{r.q_pos}/{r.nq} | {'yes' if r.qualifies else 'no'} |")
md.append(f'\nBar for finalist = max(baseline wo5 qn0-13, qn4-13) + 0.5 = {BAR:+.2f}')
open(f'{HERE}/discovery_table.md', 'w').write('\n'.join(md) + '\n')
P('\n'.join(md))
