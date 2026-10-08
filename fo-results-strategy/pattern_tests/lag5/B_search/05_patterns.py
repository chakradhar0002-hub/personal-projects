"""
05_patterns.py -- what separates bouncers from fallers inside the lag > 5% group (in_fo True).
For every numeric cutoff-time feature:
  * Spearman rank correlation with three_day: all 22 quarters, first 14, last 8
  * tercile split with cuts from the first-14 rows: average three_day in the bottom and top third, first 14 / last 8
  * bouncers (three_day > +3%) vs fallers (three_day < -3%): median feature value of each
  * does the first-14 direction hold in the last 8?  (count vs 50% expected by chance)
Model-based importance: RF / GBM fitted on qn 0..13 (target three_day > +3% and > 0), permutation importance
measured on qn 14..21 (AUC drop, 20 repeats), plus RF impurity importance.
Outputs: patterns_features.csv, patterns_importance.csv
"""
import sys, os
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsearch as G

df = G.load_group('fo')
y = df.three_day.values
qn = df.qn.values
tr, te = qn <= 13, qn >= 14
rows = []
for f in G.NUM_FEATS + ['fq']:
    x = df[f].values.astype(float)
    ok = np.isfinite(x)
    if ok.sum() < 100:
        continue
    r = {'feature': f, 'n': int(ok.sum())}
    for lab, mk in (('all', ok), ('f14', ok & tr), ('l8', ok & te)):
        r[f'rho_{lab}'] = spearmanr(x[mk], y[mk])[0] if mk.sum() > 20 else np.nan
    lo, hi = np.nanpercentile(x[tr], [100 / 3, 200 / 3])
    for lab, mk in (('f14', tr), ('l8', te), ('all', np.ones(len(y), bool))):
        b = mk & ok & (x <= lo); t = mk & ok & (x >= hi)
        r[f'bot3_{lab}_pct'] = 100 * y[b].mean() if b.any() else np.nan
        r[f'top3_{lab}_pct'] = 100 * y[t].mean() if t.any() else np.nan
        r[f'top_minus_bot_{lab}_pct'] = r[f'top3_{lab}_pct'] - r[f'bot3_{lab}_pct']
    r['n_bot3_all'] = int((ok & (x <= lo)).sum()); r['n_top3_all'] = int((ok & (x >= hi)).sum())
    bnc, fal = ok & (y > 0.03), ok & (y < -0.03)
    r['median_bouncers'] = np.median(x[bnc]); r['median_fallers'] = np.median(x[fal]); r['median_all'] = np.median(x[ok])
    sd = np.nanstd(x)
    r['std_diff_bouncers_minus_fallers'] = (np.mean(x[bnc]) - np.mean(x[fal])) / sd if sd > 0 else np.nan
    r['same_sign_f14_l8'] = bool(np.sign(r['top_minus_bot_f14_pct']) == np.sign(r['top_minus_bot_l8_pct']))
    rows.append(r)
P = pd.DataFrame(rows).sort_values('rho_all')
P.to_csv(f'{G.HERE}/patterns_features.csv', index=False)
pd.set_option('display.width', 250)
cols = ['feature', 'rho_all', 'rho_f14', 'rho_l8', 'bot3_all_pct', 'top3_all_pct', 'top_minus_bot_f14_pct',
        'top_minus_bot_l8_pct', 'median_bouncers', 'median_fallers']
print('n bouncers (>+3%)', int((y > 0.03).sum()), 'n fallers (<-3%)', int((y < -0.03).sum()), 'of', len(y))
print(P[cols].round(3).to_string())
print('features whose first-14 tercile direction holds in last 8: %d of %d' % (P.same_sign_f14_l8.sum(), len(P)))
big = P[P.top_minus_bot_f14_pct.abs() >= 1.5]
print('of features with |top-bot| >= 1.5%% in first 14 (%d), direction holds in last 8: %d' % (len(big), big.same_sign_f14_l8.sum()))
print('corr of rho_f14 with rho_l8 across features: %.3f' % P[['rho_f14', 'rho_l8']].corr().iloc[0, 1])

# --- model-based importance (fit on first 14, permutation on last 8)
FE = list(P.feature)
X = df[FE].values.astype(float)
med = np.nanmedian(X[tr], axis=0); med = np.where(np.isfinite(med), med, 0)
Xi = np.where(np.isfinite(X), X, med)
imp_rows = []
for target, thr in (('up3', 0.03), ('up0', 0.0)):
    lab = (y > thr).astype(int)
    rf = RandomForestClassifier(n_estimators=500, min_samples_leaf=10, max_features=0.3, n_jobs=2, random_state=0)
    rf.fit(Xi[tr], lab[tr])
    auc_rf = roc_auc_score(lab[te], rf.predict_proba(Xi[te])[:, 1])
    pi = permutation_importance(rf, Xi[te], lab[te], scoring='roc_auc', n_repeats=20, random_state=0, n_jobs=2)
    gb = HistGradientBoostingClassifier(learning_rate=0.05, max_iter=150, max_depth=3, min_samples_leaf=20,
                                        l2_regularization=1.0, random_state=0).fit(Xi[tr], lab[tr])
    auc_gb = roc_auc_score(lab[te], gb.predict_proba(Xi[te])[:, 1])
    pg = permutation_importance(gb, Xi[te], lab[te], scoring='roc_auc', n_repeats=20, random_state=0, n_jobs=2)
    print(target, 'held-out (last 8) AUC: RF %.3f  GBM %.3f' % (auc_rf, auc_gb))
    for k, f in enumerate(FE):
        imp_rows.append({'target': target, 'feature': f, 'rf_impurity': rf.feature_importances_[k],
                         'rf_perm_auc_drop_last8': pi.importances_mean[k], 'gbm_perm_auc_drop_last8': pg.importances_mean[k],
                         'rf_auc_last8': auc_rf, 'gbm_auc_last8': auc_gb})
I = pd.DataFrame(imp_rows)
I.to_csv(f'{G.HERE}/patterns_importance.csv', index=False)
for t in ('up3', 'up0'):
    d = I[I.target == t].merge(P[['feature', 'rho_all', 'rho_f14', 'rho_l8']], on='feature')
    print(t, 'top 15 by RF impurity (fit on first 14):')
    print(d.sort_values('rf_impurity', ascending=False).head(15).round(4).to_string())
    print(t, 'top 10 by RF permutation AUC drop on last 8:')
    print(d.sort_values('rf_perm_auc_drop_last8', ascending=False).head(10).round(4).to_string())
