"""
04_ml.py -- walk-forward random forest and gradient boosting inside the lag > 5% group.
For q = 8..21 train on the group's rows with qn < q, score quarter q.
  models : RF  = RandomForestClassifier(300 trees, min_samples_leaf 10, max_features 0.3), median-imputed features;
                 out-of-fold training scores = out-of-bag scores
           GBM = HistGradientBoostingClassifier(lr 0.05, 150 iter, depth 3, leaf 20, l2 1.0), NaN native;
                 out-of-fold training scores = 4-fold CV grouped by quarter
  targets: up0 = three_day > 0,  up3 = three_day > +3%
  trades : LONG top25 / top10 -> buy test stocks whose score >= the 75th / 90th percentile of the out-of-fold training
           scores;  SHORT bot25 -> short test stocks whose score <= the 25th percentile.
Features: rulelib.NUM_FEATS (numeric, cutoff-time) + fq.  No results-time feature.
Null: identical pipeline with three_day shuffled within quarter (whole y), N runs.

usage: python3 04_ml.py UNIVERSE real | shuffle N [--seed S]
"""
import sys, os, json, time, argparse
os.environ.setdefault('OMP_NUM_THREADS', '2')
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsearch as G

ap = argparse.ArgumentParser()
ap.add_argument('universe'); ap.add_argument('mode'); ap.add_argument('n', type=int, nargs='?', default=0)
ap.add_argument('--seed', type=int, default=11)
A = ap.parse_args()
df = G.load_group(A.universe)
FEATS = list(G.NUM_FEATS) + ['fq']
X = df[FEATS].values.astype(float)
y = df.three_day.values.astype(float)
tp = df.tp3.values.astype(float)
qn = df.qn.values
rng = np.random.default_rng(A.seed)
Ys = [y] if A.mode == 'real' else [G.shuffle_within(y, qn, rng) for _ in range(A.n)]


def fit_predict(kind, Xtr, ytr, gtr, Xte, seed):
    if kind == 'rf':
        med = np.nanmedian(Xtr, axis=0)
        med = np.where(np.isfinite(med), med, 0)
        Xtr_ = np.where(np.isfinite(Xtr), Xtr, med); Xte_ = np.where(np.isfinite(Xte), Xte, med)
        m = RandomForestClassifier(n_estimators=300, min_samples_leaf=10, max_features=0.3, oob_score=True,
                                   n_jobs=2, random_state=seed)
        m.fit(Xtr_, ytr)
        oof = m.oob_decision_function_[:, 1]
        return m.predict_proba(Xte_)[:, 1], oof, m
    mk = lambda: HistGradientBoostingClassifier(learning_rate=0.05, max_iter=150, max_depth=3, min_samples_leaf=20,
                                                l2_regularization=1.0, random_state=seed)
    ok = np.array([len(np.unique(c[np.isfinite(c)])) >= 3 for c in Xtr.T])
    Xtr, Xte = Xtr[:, ok], Xte[:, ok]
    oof = np.full(len(ytr), np.nan)
    for a, b in GroupKFold(n_splits=4).split(Xtr, ytr, gtr):
        if len(np.unique(ytr[a])) < 2:
            oof[b] = ytr[a].mean(); continue
        okf = np.array([len(np.unique(c[np.isfinite(c)])) >= 3 for c in Xtr[a].T])
        oof[b] = mk().fit(Xtr[a][:, okf], ytr[a]).predict_proba(Xtr[b][:, okf])[:, 1]
    m = mk().fit(Xtr, ytr)
    return m.predict_proba(Xte)[:, 1], oof, m


rows, trades, scores = [], [], []
t0 = time.time()
for s, ys in enumerate(Ys):
    for q in range(8, 22):
        tr = qn < q; te = qn == q
        for target, thr in (('up0', 0.0), ('up3', 0.03)):
            lab = (ys[tr] > thr).astype(int)
            for kind in ('rf', 'gbm'):
                pte, oof, model = fit_predict(kind, X[tr], lab, qn[tr], X[te], seed=q)
                cut = {'top25': np.nanpercentile(oof, 75), 'top10': np.nanpercentile(oof, 90),
                       'bot25': np.nanpercentile(oof, 25)}
                for v, c in cut.items():
                    pick = pte >= c if v.startswith('top') else pte <= c
                    sgn = 1 if v.startswith('top') else -1
                    pn = sgn * ys[te][pick]
                    rows.append({'mode': A.mode, 'run': s, 'model': kind, 'target': target, 'variant': v, 'qn': q,
                                 'sum': pn.sum(), 'n': len(pn)})
                    if A.mode == 'real':
                        for ii, p in zip(np.where(te)[0][pick], pn):
                            trades.append({'model': kind, 'target': target, 'variant': v, 'qn': q,
                                           'symbol': df.symbol.values[ii], 'pnl': p,
                                           'tp_pnl': tp[ii] if sgn > 0 else np.nan})
                if A.mode == 'real':
                    for ii, p in zip(np.where(te)[0], pte):
                        scores.append({'model': kind, 'target': target, 'qn': q, 'symbol': df.symbol.values[ii],
                                       'score': p, 'three_day': y[ii]})
    print(A.mode, 'run', s + 1, round(time.time() - t0, 1), flush=True)
    pd.DataFrame(rows).to_csv(f'{G.HERE}/ml_{A.universe}_{A.mode}_{A.seed}_agg.csv', index=False)
if A.mode == 'real':
    pd.DataFrame(trades).to_csv(f'{G.HERE}/ml_{A.universe}_real_trades.csv', index=False)
    S = pd.DataFrame(scores); S.to_csv(f'{G.HERE}/ml_{A.universe}_real_scores.csv', index=False)
    for (k, t), g in S.groupby(['model', 'target']):
        thr = 0.0 if t == 'up0' else 0.03
        lab = (g.three_day > thr).astype(int)
        a_all = roc_auc_score(lab, g.score)
        a14 = roc_auc_score(lab[g.qn >= 14], g.score[g.qn >= 14])
        rc = g[['score', 'three_day']].corr(method='spearman').iloc[0, 1]
        print(k, t, 'walk-forward AUC q8-21 %.3f  q14-21 %.3f  spearman(score, three_day) %.3f' % (a_all, a14, rc))
print('done', round(time.time() - t0, 1))
