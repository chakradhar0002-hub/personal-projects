"""Precise permutation p (200,000 within-quarter shuffles) for the custom Cap goods / IT pair and halves p for the
last-4 top tenth."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from sk_common import *
HERE = SKOUT
ev, allev, qq = load()
QN = ev.qn.to_numpy(); X = ev.x.to_numpy()
rng = np.random.default_rng(20261104)
sk3 = pd.read_csv(f'{HERE}/sk3_stock.csv')
print(sk3[['rule', 'p', 'p_tq']].to_string())
for lab, a, b in (('custom_sector', 'Capital goods & defence', 'IT'), ('custom_sector', 'Banks', 'Metals & mining'),
                  ('nifty_sector', 'Financial Services', 'Metals & Mining')):
    ma, mb = (ev[lab] == a).to_numpy(), (ev[lab] == b).to_numpy()
    ca = np.array([np.sum(ma & (QN == t)) for t in range(22)]); cb = np.array([np.sum(mb & (QN == t)) for t in range(22)])
    q = (ca >= 4) & (cb >= 4)
    Ma = np.zeros((len(X), 22)); Ma[np.where(ma)[0], QN[ma]] = 1
    Mb = np.zeros((len(X), 22)); Mb[np.where(mb)[0], QN[mb]] = 1
    def r_of(xs):
        ea = (xs @ Ma)[:, q] / ca[q]; eb = (xs @ Mb)[:, q] / cb[q]
        ea = ea - ea.mean(1, keepdims=True); eb = eb - eb.mean(1, keepdims=True)
        return (ea * eb).sum(1) / np.sqrt((ea ** 2).sum(1) * (eb ** 2).sum(1))
    r0 = r_of(X[None])[0]
    B, CH = 200000, 5000
    sims = np.concatenate([r_of(X[np.argsort(QN[None] + rng.random((CH, len(X))), axis=1)]) for _ in range(B // CH)])
    print(f'{lab} {a} / {b}: r {r0:+.4f}, null mean {sims.mean():+.4f}, sd {sims.std():.4f}, two-sided centred p '
          f'{p2c(r0, sims):.6f} (B {B:,}); x 244 tests = {min(1, 244 * p2c(r0, sims)):.3f}')
