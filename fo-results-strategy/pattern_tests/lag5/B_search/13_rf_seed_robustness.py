"""
13_rf_seed_robustness.py -- is the walk-forward RF P(three_day > +3%) top-10% result stable across random seeds and
nearby settings?  Same pipeline as 04_ml.py (all ~96 cutoff-time features), seeds 0..9, thresholds top 5/10/15/20%,
min_samples_leaf 5/10/20.  Output: rf_seed_robustness.csv
"""
import os, sys
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestClassifier
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsearch as G

df = G.load_group('fo')
FEATS = list(G.NUM_FEATS) + ['fq']
X = df[FEATS].values.astype(float); y = df.three_day.values; qn = df.qn.values
rows = []
for leaf in (5, 10, 20):
    for seed in range(10):
        picks = {t: [] for t in (5, 10, 15, 20)}
        for q in range(8, 22):
            tr = qn < q; te = qn == q
            med = np.nanmedian(X[tr], axis=0); med = np.where(np.isfinite(med), med, 0)
            Xtr = np.where(np.isfinite(X[tr]), X[tr], med); Xte = np.where(np.isfinite(X[te]), X[te], med)
            m = RandomForestClassifier(n_estimators=300, min_samples_leaf=leaf, max_features=0.3, oob_score=True,
                                       n_jobs=2, random_state=1000 * seed + q).fit(Xtr, (y[tr] > 0.03).astype(int))
            oof = m.oob_decision_function_[:, 1]; p = m.predict_proba(Xte)[:, 1]
            for t in picks:
                k = p >= np.nanpercentile(oof, 100 - t)
                picks[t] += [(q, v) for v in y[te][k]]
        for t, lst in picks.items():
            a = np.array(lst)
            rows.append({'leaf': leaf, 'seed': seed, 'top_pct': t, 'trades': len(a),
                         'avg_pct': 100 * a[:, 1].mean() if len(a) else np.nan,
                         'last8_avg_pct': 100 * a[a[:, 0] >= 14, 1].mean() if len(a) else np.nan})
        print(leaf, seed, flush=True)
Rr = pd.DataFrame(rows)
Rr.to_csv(f'{G.HERE}/rf_seed_robustness.csv', index=False)
print(Rr.groupby(['leaf', 'top_pct'])[['trades', 'avg_pct', 'last8_avg_pct']].agg(['mean', 'min', 'max']).round(2).to_string())
