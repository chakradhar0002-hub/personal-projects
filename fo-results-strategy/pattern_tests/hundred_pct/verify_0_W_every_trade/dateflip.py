"""Null that keeps same-day clustering: one random sign per CUTOFF DATE (all stocks with that cutoff flipped together)
around the quarter mean.  Same search as vsearch.py."""
import sys, time, numpy as np, pandas as pd
sys.path.insert(0,'.')
import vsearch as V, rulelib_copy as RL
df, tr, M, names, compat = V.prep('fo', 14)
y = df.three_day.values.astype(float); qn = df.qn.values
codes = pd.factorize(df.cutoff)[0]
qm = pd.Series(y).groupby(qn).transform('mean').values
rng = np.random.default_rng(int(sys.argv[2]) if len(sys.argv)>2 else 5)
res=[]; t0=time.time()
for i in range(int(sys.argv[1])):
    s = rng.choice([-1.0,1.0], codes.max()+1)[codes]
    y2 = qm + s*(y-qm)
    f2,_ = V.search(M, compat, y2, tr, qn)
    s2,k2 = V.summarize(f2, M, y2, tr, qn)
    s2['largest_rule'] = RL.rule_str(names, list(k2), 1) if k2 else None
    res.append(dict(kind='dateflip', run=i, **s2))
    pd.DataFrame(res).to_csv('nulls_dateflip.csv', index=False)
    print(i, s2['largest'], s2['count100_m20'], round(time.time()-t0,1), flush=True)
