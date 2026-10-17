"""Stock-level lag-1 carry-over by half: Pearson / Spearman, Fisher z for the difference, and a within-quarter
across-stock shuffle null for each half."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from scipy import stats
from sk_common import *
ev, allev, qq = load()
p = ev[['symbol', 'qn', 'x']].copy(); n_ = p.copy(); n_['qn'] -= 1
pr = p.merge(n_, on=['symbol', 'qn'], suffixes=('', '_n'))
rng = np.random.default_rng(20261106)
res = {}
for nm, m in (('t<=9', pr.qn <= 9), ('t>=11', pr.qn >= 11), ('t=10..20 (second half incl. 10)', pr.qn >= 10)):
    d = pr[m].reset_index(drop=True)
    r, rs = pear(d.x, d.x_n), spear(d.x, d.x_n)
    # across-stock null: shuffle next-quarter x among the pairs of the same quarter t
    o = np.argsort(d.qn.to_numpy(), kind='stable'); a = d.x.to_numpy()[o]; b = d.x_n.to_numpy()[o]; q = d.qn.to_numpy()[o].astype(float)
    az = (a - a.mean()) / a.std()
    sims = []
    for _ in range(4):
        P_ = np.argsort(q[None] + rng.random((5000, len(b))), axis=1)
        bb = b[P_]; bb = (bb - bb.mean(1, keepdims=True)) / bb.std(1, keepdims=True)
        sims.append((bb * az).mean(1))
    sims = np.concatenate(sims)
    res[nm] = (r, len(d))
    print(f'{nm}: {len(d)} pairs, Pearson {r:+.3f}, Spearman {rs:+.3f}, across-stock null p {fpv(p2c(r, sims))}')
(r1, n1), (r2, n2) = res['t<=9'], res['t>=11']
z = (np.arctanh(r1) - np.arctanh(r2)) / np.sqrt(1 / (n1 - 3) + 1 / (n2 - 3))
print(f'difference of halves: z {z:.2f}, two-sided normal p {2 * stats.norm.sf(abs(z)):.4f}')
