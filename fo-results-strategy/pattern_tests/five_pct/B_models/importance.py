"""Permutation importance (AUC drop) of the fixed-split classifiers trained on quarters 0..13 (in_fo),
measured on the training quarters and on the 14..21 holdout. Plus RF impurity importance."""
import os
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
import pipeline as P
HERE = os.path.dirname(os.path.abspath(__file__))

T, feats, X = P.load('fo')
y = T.three_day.values; qn = T.qn.values
tr, te = qn < 14, qn >= 14
lab = (y > .05).astype(int)
A = np.where(np.isnan(X), -999., X)
rf = RandomForestClassifier(random_state=0, n_jobs=1, **P.CONFIGS['rf_gt'][0]).fit(A[tr], lab[tr])
hgb = HistGradientBoostingClassifier(random_state=0, **P.CONFIGS['hgb_gt'][2]).fit(X[tr], lab[tr])
out = pd.DataFrame({'feature': feats, 'rf_impurity': rf.feature_importances_})
for name, m, M in (('rf', rf, A), ('hgb', hgb, X)):
    for part, msk in (('train', tr), ('holdout', te)):
        pi = permutation_importance(m, M[msk], lab[msk], scoring='roc_auc', n_repeats=5, random_state=0, n_jobs=1)
        out[f'{name}_perm_auc_{part}'] = pi.importances_mean
out = out.sort_values('rf_perm_auc_holdout', ascending=False)
out.to_csv(os.path.join(HERE, 'feature_importance_fo.csv'), index=False)
pd.set_option('display.width', 200)
print(out.head(25).round(4).to_string())
print('\nby train-set RF impurity:')
print(out.sort_values('rf_impurity', ascending=False).head(15)[['feature', 'rf_impurity']].round(4).to_string())
