"""
08_composite.py -- a simple linear alternative to the rule search and the tree models (walk-forward).
For q = 8..21: on the group's rows with qn < q compute each numeric feature's Spearman correlation with three_day;
keep features with |rho| >= 0.08; score = average over kept features of sign(rho) x (percentile rank of the feature
among the training rows; missing -> 0.5).  Buy test stocks whose score >= the 75th percentile of the training rows'
scores (top25) / 90th (top10); short those <= 25th (bot25).
Fixed-split version: weights from qn 0..13, tested on qn 14..21.
Null: identical pipeline on 200 within-quarter shuffles of three_day.
Output: composite_summary.csv
"""
import os, sys
import numpy as np, pandas as pd
from scipy.stats import spearmanr, rankdata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsearch as G

df = G.load_group('fo')
FE = list(G.NUM_FEATS)
X = df[FE].values.astype(float)
y = df.three_day.values.astype(float)
qn = df.qn.values


def pct_rank(xtr, x):
    """percentile of x within the finite training values xtr (missing -> 0.5)."""
    s = np.sort(xtr[np.isfinite(xtr)])
    out = np.searchsorted(s, x, side='right') / max(len(s), 1)
    return np.where(np.isfinite(x), out, 0.5)


def score_fit(tr, ys):
    w = []
    for k in range(X.shape[1]):
        x = X[tr, k]; ok = np.isfinite(x)
        if ok.sum() < 60 or len(np.unique(x[ok])) < 5:
            w.append(0.0); continue
        r = spearmanr(x[ok], ys[tr][ok])[0]
        w.append(np.sign(r) if abs(r) >= 0.08 else 0.0)
    w = np.array(w)
    return w


def score_apply(w, tr, rows):
    keep = np.where(w != 0)[0]
    if not len(keep):
        return np.zeros(rows.sum())
    s = np.zeros(rows.sum())
    for k in keep:
        p = pct_rank(X[tr, k], X[rows, k])
        s += w[k] * (p - 0.5)
    return s / len(keep)


# speed: precompute nothing fancy; 200 shuffles x 14 quarters is fine
def run(ys):
    out = {}
    for q in range(8, 22):
        tr = qn < q; te = qn == q
        w = score_fit(tr, ys)
        s_tr = score_apply(w, tr, tr); s_te = score_apply(w, tr, te)
        for v, c in (('top25', np.percentile(s_tr, 75)), ('top10', np.percentile(s_tr, 90)), ('bot25', np.percentile(s_tr, 25))):
            pick = s_te >= c if v.startswith('top') else s_te <= c
            sg = 1 if v.startswith('top') else -1
            pn = sg * ys[te][pick]
            a = out.setdefault(('wf', v), [0.0, 0, 0.0, 0, 0, 0])
            a[0] += pn.sum(); a[1] += len(pn)
            if q >= 14:
                a[2] += pn.sum(); a[3] += len(pn)
            if len(pn):
                a[4] += 1; a[5] += pn.mean() > 0
    tr = qn <= 13; te = ~tr
    w = score_fit(tr, ys)
    s_tr = score_apply(w, tr, tr); s_te = score_apply(w, tr, te)
    for v, c in (('top25', np.percentile(s_tr, 75)), ('top10', np.percentile(s_tr, 90)), ('bot25', np.percentile(s_tr, 25))):
        pick = s_te >= c if v.startswith('top') else s_te <= c
        sg = 1 if v.startswith('top') else -1
        pn = sg * ys[te][pick]
        qq = qn[te][pick]
        qa = pd.Series(pn).groupby(qq).mean()
        out[('fixed', v)] = [0.0, 0, pn.sum(), len(pn), len(qa), int((qa > 0).sum())]
    return out, w


real, w_fixed = run(y)
print('fixed-split features kept (first 14):', [(FE[k], int(w_fixed[k])) for k in np.where(w_fixed != 0)[0]])
rng = np.random.default_rng(3)
nulls = [run(G.shuffle_within(y, qn, rng))[0] for _ in range(200)]
rows = []
for key, a in real.items():
    r = {'split': key[0], 'variant': key[1]}
    if key[0] == 'wf':
        r.update(trades_q8_21=a[1], avg_q8_21_pct=100 * a[0] / a[1] if a[1] else np.nan, q_with=a[4], q_pos=a[5])
        nv = np.array([100 * n[key][0] / n[key][1] if n[key][1] else np.nan for n in nulls])
        r.update(null_mean=np.nanmean(nv), null_p95=np.nanpercentile(nv, 95), p=float(np.nanmean(nv >= r['avg_q8_21_pct'])))
    r.update(trades_last8=a[3], avg_last8_pct=100 * a[2] / a[3] if a[3] else np.nan)
    nv8 = np.array([100 * n[key][2] / n[key][3] if n[key][3] else np.nan for n in nulls])
    r.update(null_last8_mean=np.nanmean(nv8), null_last8_p95=np.nanpercentile(nv8, 95),
             p_last8=float(np.nanmean(nv8 >= r['avg_last8_pct'])))
    if key[0] == 'fixed':
        r.update(q_with=a[4], q_pos=a[5])
    rows.append(r)
C = pd.DataFrame(rows)
C.to_csv(f'{G.HERE}/composite_summary.csv', index=False)
pd.set_option('display.width', 250)
print(C.round(3).to_string())
