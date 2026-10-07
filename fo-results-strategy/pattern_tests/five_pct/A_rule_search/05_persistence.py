"""
05_persistence.py -- do rules that looked good in the first 14 quarters stay good in the last 8?
For every 1- and 2-condition rule (long side; the short side is the mirror image) with >= 20 trades in
quarters 0..13 and >= 10 trades in quarters 14..21: bucket rules by their in-sample average and report the
average out-of-sample result of each bucket, plus the correlation between in-sample and out-of-sample
averages.  The same on 20 within-quarter shuffles (where by construction nothing persists).
Output: persistence.csv, persistence.json
"""
import sys, os, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rulelib as R

df = R.load('fo')
y = df.three_day.values.astype(float); qn = df.qn.values
tr = qn <= 13; te = ~tr
M, names, compat = R.build_conditions(df, tr)
X = M[:, tr].astype(np.float32); Xt = M[:, te].astype(np.float32)
K = X @ X.T; Kt = Xt @ Xt.T
up = np.triu(compat, 1) | np.eye(len(names), dtype=bool)     # diagonal = 1-condition rules
sel = up & (K >= 20) & (Kt >= 10)
print('rules used', int(sel.sum()))
BINS = [-np.inf, -0.05, -0.03, -0.02, -0.01, 0, 0.01, 0.02, 0.03, 0.05, np.inf]


def one(yv):
    S = (X * yv[tr].astype(np.float32)) @ X.T
    St = (Xt * yv[te].astype(np.float32)) @ Xt.T
    a = (S / K)[sel]; b = (St / Kt)[sel]
    cat = pd.cut(a, BINS)
    tab = pd.DataFrame({'is': a, 'oos': b, 'bin': cat}).groupby('bin', observed=False).agg(
        n_rules=('is', 'size'), is_avg=('is', 'mean'), oos_avg=('oos', 'mean'))
    return float(np.corrcoef(a, b)[0, 1]), tab


r0, tab0 = one(y)
rng = np.random.default_rng(99)
cors, tabs = [], []
for s in range(20):
    c, t = one(R.shuffle_within(y, qn, rng))
    cors.append(c); tabs.append(t.oos_avg.values)
tab0['shuffled_oos_avg_mean'] = np.nanmean(np.array(tabs), 0)
tab0[['is_avg', 'oos_avg', 'shuffled_oos_avg_mean']] *= 100
tab0.to_csv(f'{R.HERE}/persistence.csv')
out = {'n_rules': int(sel.sum()), 'corr_is_oos_real': r0, 'corr_is_oos_shuffled_mean': float(np.mean(cors)),
       'corr_is_oos_shuffled_p95': float(np.quantile(cors, 0.95)), 'corr_shuffled_all': cors}
json.dump(out, open(f'{R.HERE}/persistence.json', 'w'), indent=1)
print(tab0.round(3).to_string())
print({k: v for k, v in out.items() if k != 'corr_shuffled_all'})
