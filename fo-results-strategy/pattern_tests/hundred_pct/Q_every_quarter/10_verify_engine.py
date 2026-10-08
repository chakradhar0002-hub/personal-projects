# engine check: recompute rule stats directly from masks for a sample of the real split rules
import json, numpy as np, pandas as pd
import qengine as E
df = E.load('fo'); S = E.Search(df, range(14), range(14, 22))
R = pd.read_csv('out/split_fo_real_rules.csv')
R = pd.concat([R.groupby(['fam', 'cov', 'net']).head(3), R.sample(60, random_state=1)])
qn = df.qn.values; bad = 0
for _, r in R.iterrows():
    m = S.rule_mask(json.loads(r.conds))
    u = r.u
    p = {'L3': df.three_day.values, 'S3': -df.three_day.values, 'LT': df.tp3.values, 'ST': df.tp3s.values}[u][m]; q = qn[m]
    qa = pd.Series(p).groupby(q).mean()
    tr, te = qa[qa.index < 14], qa[qa.index >= 14]
    thr = E.COST if r.net else 0.0
    ok = (len(tr) == r.is_nq and m[qn < 14].sum() == r.is_trades and abs(100 * p[q < 14].mean() - r.is_avg_pct) < 1e-3
          and abs(100 * tr.min() - r.is_worst_q_pct) < 1e-3 and (tr > thr).all() and len(te) == r.oos_nq
          and int((te > thr).sum()) == r.oos_pos and m[qn >= 14].sum() == r.oos_trades
          and (r.oos_trades == 0 or abs(100 * p[q >= 14].mean() - r.oos_avg_pct) < 1e-3))
    bad += not ok
    if not ok:
        print('MISMATCH', r.rule, u, r.net, len(tr), r.is_nq, 100 * p[q < 14].mean(), r.is_avg_pct, int((te > thr).sum()), r.oos_pos)
print('checked', len(R), 'mismatches', bad)
