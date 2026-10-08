"""
vsearch.py -- independent re-implementation of the "largest 100%-winner LONG rule" search (verifier).
Conditions: rulelib grid (feature >=/<= training-row percentile cut, category ==), AND of 1-3.
Level 1, 2 exhaustive; level 3 beam: pairs ranked (a) by shrunk win rate (w+1)/(n+2), n>=10,
(b) by winners among pairs with <= 2 losers (the natural route to a large zero-loser triple);
top B of each, extended by every compatible third condition.  Identical search on null outcomes.
Rule eligible: >= m trades in training, >= 4 training quarters, zero losers (P&L > thr).
"""
import os, sys, json, time
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rulelib_copy as RL

HERE = os.path.dirname(os.path.abspath(__file__))


def prep(universe, train_q_lt, test_q=None):
    df = RL.load(universe)
    tr = (df.qn < train_q_lt).values
    M, names, compat = RL.build_conditions(df, tr)
    return df, tr, M, names, compat


def search(M, compat, y, tr, qn, thr=0.0, B=2000, mins=(10, 15, 20), minq=4, keep_all_min=10):
    """Return list of all zero-loser rules (n>=keep_all_min, >=minq quarters) as (conds, n_train)."""
    X = M[:, tr].astype(np.float32)
    win = (y[tr] > thr)
    Xw, Xl = X[:, win], X[:, ~win]
    qt = qn[tr]
    uq = np.unique(qt)
    Qoh = (qt[:, None] == uq[None, :]).astype(np.float32)   # N x Q
    C = X.shape[0]
    found = {}
    # level 1
    W1, L1 = Xw.sum(1), Xl.sum(1)
    Q1 = ((X @ Qoh) > 0).sum(1)
    for c in np.where((L1 == 0) & (W1 >= keep_all_min) & (Q1 >= minq))[0]:
        found[(int(c),)] = int(W1[c])
    # level 2
    W2 = Xw @ Xw.T
    L2 = Xl @ Xl.T
    up = np.triu(compat, 1)
    N2 = W2 + L2
    cand = np.argwhere(up & (L2 < 0.5) & (W2 >= keep_all_min))
    for a, b in cand:
        m = X[a] * X[b]
        if ((m @ Qoh) > 0).sum() >= minq:
            found[(int(a), int(b))] = int(W2[a, b])
    # beam pairs
    ok = up & (N2 >= 10)
    sh = np.where(ok, (W2 + 1) / (N2 + 2), -1)
    flat = sh.ravel()
    ia = np.argpartition(-flat, B)[:B]
    sel = set(map(int, ia[flat[ia] > 0]))
    wv = np.where(up & (L2 <= 2.5) & (W2 >= 10), W2, -1).ravel()
    ib = np.argpartition(-wv, B)[:B]
    sel |= set(map(int, ib[wv[ib] > 0]))
    pairs = [divmod(k, C) for k in sel]
    n_tri = 0
    seen = set()
    for a, b in pairs:
        mw = Xw[a] * Xw[b]
        ml = Xl[a] * Xl[b]
        w3 = Xw @ mw
        l3 = Xl @ ml
        okc = compat[a] & compat[b]
        okc[[a, b]] = False
        n_tri += int(okc.sum())
        cs = np.where(okc & (l3 < 0.5) & (w3 >= keep_all_min))[0]
        if len(cs) == 0:
            continue
        m2 = X[a] * X[b]
        qc = (((X[cs] * m2) @ Qoh) > 0).sum(1)
        for c, q in zip(cs, qc):
            if q >= minq:
                key = tuple(sorted((int(a), int(b), int(c))))
                if key not in seen:
                    seen.add(key)
                    found[key] = int(w3[c])
    n_rules = C + int(up.sum()) + n_tri
    return found, n_rules


def rule_trades(M, conds):
    m = M[conds[0]].copy()
    for c in conds[1:]:
        m &= M[c]
    return m


def summarize(found, M, y, tr, qn, thr=0.0, mins=(10, 15, 20)):
    te = ~tr
    out = {}
    for m in mins:
        ks = [k for k, n in found.items() if n >= m]
        out[f'count100_m{m}'] = len(ks)
    if not found:
        out['largest'] = 0
        return out, None
    nmax = max(found.values())
    best = [k for k, n in found.items() if n == nmax]
    # tie-break: shortest rule then first
    best.sort(key=lambda k: (len(k), k))
    k = best[0]
    mask = rule_trades(M, list(k))
    yt = y[mask & te]
    out['largest'] = nmax
    out['n_tied_largest'] = len(best)
    out['largest_oos_n'] = int(len(yt))
    out['largest_oos_wr'] = float((yt > thr).mean() * 100) if len(yt) else np.nan
    out['largest_oos_avg'] = float(yt.mean() * 100) if len(yt) else np.nan
    # pooled OOS of all 100% rules with n>=20
    for m in (10, 20):
        ks = [kk for kk, n in found.items() if n >= m]
        wrs = []
        for kk in ks[:20000]:
            mm = rule_trades(M, list(kk)) & te
            if mm.sum():
                wrs.append(((y[mm] > thr).mean(), mm.sum(), y[mm].mean()))
        if wrs:
            a = np.array(wrs)
            out[f'all100_m{m}_oos_mean_wr'] = float(a[:, 0].mean() * 100)
            out[f'all100_m{m}_oos_pooled_wr'] = float((a[:, 0] * a[:, 1]).sum() / a[:, 1].sum() * 100)
            out[f'all100_m{m}_oos_mean_avg'] = float(a[:, 2].mean() * 100)
            out[f'all100_m{m}_oos_frac_wr_ge_69.7'] = float((a[:, 0] >= 0.697).mean() * 100)
    return out, k


def null_y(y, qn, kind, rng):
    y2 = y.copy()
    if kind == 'shuffle':
        for q in np.unique(qn):
            ix = np.where(qn == q)[0]
            y2[ix] = y[rng.permutation(ix)]
    else:
        for q in np.unique(qn):
            ix = np.where(qn == q)[0]
            mu = y[ix].mean()
            s = rng.choice([-1.0, 1.0], len(ix))
            y2[ix] = mu + s * (y[ix] - mu)
    return y2


if __name__ == '__main__':
    universe = sys.argv[1] if len(sys.argv) > 1 else 'fo'
    nnull = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    thr = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 7
    tag = f'{universe}_thr{thr}'
    t0 = time.time()
    df, tr, M, names, compat = prep(universe, 14)
    y = df.three_day.values.astype(float)
    qn = df.qn.values
    print('conditions', M.shape, flush=True)
    found, nr = search(M, compat, y, tr, qn, thr=thr)
    s, k = summarize(found, M, y, tr, qn, thr=thr)
    s['rules_evaluated'] = nr
    s['largest_rule'] = RL.rule_str(names, list(k), 1) if k else None
    print('REAL', json.dumps(s), round(time.time() - t0, 1), flush=True)
    # top 15 largest real
    top = sorted(found.items(), key=lambda kv: -kv[1])[:15]
    rows = []
    for kk, n in top:
        mm = rule_trades(M, list(kk)) & ~tr
        rows.append(dict(rule=RL.rule_str(names, list(kk), 1), n_is=n, n_oos=int(mm.sum()),
                         oos_wr=(y[mm] > thr).mean() * 100, oos_avg=y[mm].mean() * 100))
    pd.DataFrame(rows).to_csv(f'{HERE}/real_top_largest_{tag}.csv', index=False)
    rng = np.random.default_rng(seed)
    res = [dict(kind='real', run=0, **{kk: v for kk, v in s.items()})]
    for i in range(nnull):
        for kind in ('shuffle', 'signflip'):
            y2 = null_y(y, qn, kind, rng)
            f2, _ = search(M, compat, y2, tr, qn, thr=thr)
            s2, k2 = summarize(f2, M, y2, tr, qn, thr=thr)
            s2['largest_rule'] = RL.rule_str(names, list(k2), 1) if k2 else None
            res.append(dict(kind=kind, run=i, **s2))
        print('null', i, res[-2]['largest'], res[-1]['largest'], round(time.time() - t0, 1), flush=True)
        pd.DataFrame(res).to_csv(f'{HERE}/nulls_{tag}.csv', index=False)
    pd.DataFrame(res).to_csv(f'{HERE}/nulls_{tag}.csv', index=False)
    print('done', round(time.time() - t0, 1))
