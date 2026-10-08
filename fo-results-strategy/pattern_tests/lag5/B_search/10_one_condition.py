"""
10_one_condition.py -- the simplest search: one extra condition on top of lag > 5%.
(a) fixed split: best 1-condition rule (either side, mean objective, min trades 30 / 15 / 60, picks in >= 6 quarters)
    on qn 0..13, its last-8 result; the same on 1,000 within-quarter shuffles and 1,000 sign-flips (identical cuts).
(b) walk-forward: for q = 8..21 cuts and choice from qn < q, trade the best 1-condition rule in q (either side and
    long-only), same nulls (300 each).
Output: one_condition_summary.csv, one_condition_wf_trades.csv
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsearch as G

df = G.load_group('fo')
y = df.three_day.values.astype(float); qn = df.qn.values
tr = qn <= 13; te = ~tr
rng = np.random.default_rng(99)


def prep(trmask):
    M, names, _ = G.build_conditions(df, trmask)
    X = M.astype(np.float32)
    K = X[:, trmask].sum(1)
    Q = np.array([len(np.unique(qn[trmask & M[i]])) for i in range(len(M))])
    return M, X, K, Q, names


def best1(X, K, Q, ys, trmask, m, side):
    S = X[:, trmask] @ ys[trmask]
    mean = S / np.maximum(K, 1)
    ok = (K >= m) & (Q >= 6)
    cands = []
    if side in ('either', 'long'):
        cands.append((np.where(ok, mean, -np.inf), 1))
    if side in ('either', 'short'):
        cands.append((np.where(ok, -mean, -np.inf), -1))
    best = max(((o.max(), int(o.argmax()), s) for o, s in cands), key=lambda z: z[0])
    return best  # (is_avg, cond index, sign)


M, X, K, Q, names = prep(tr)
rows = []
for m in (15, 30, 60):
    for side in ('either', 'long', 'short'):
        isv, c, s = best1(X, K, Q, y, tr, m, side)
        p8 = s * y[M[c] & te]
        real = {'part': 'fixed', 'min_trades': m, 'side': side, 'rule': G.rule_str(names, [c], s), 'is_avg_pct': 100 * isv,
                'last8_trades': len(p8), 'last8_avg_pct': 100 * p8.mean()}
        for mode in ('shuffle', 'signflip'):
            isn, l8n = [], []
            for _ in range(1000):
                ys = G.shuffle_within(y, qn, rng) if mode == 'shuffle' else G.signflip(y, qn, rng)
                a, cc, ss = best1(X, K, Q, ys, tr, m, side)
                isn.append(100 * a); l8n.append(100 * (ss * ys[M[cc] & te]).mean())
            isn, l8n = np.array(isn), np.nan_to_num(np.array(l8n))
            real[f'{mode}_p_is'] = float((isn >= real['is_avg_pct'] - 1e-9).mean())
            real[f'{mode}_is_median'] = float(np.median(isn))
            real[f'{mode}_l8_mean'] = float(l8n.mean()); real[f'{mode}_l8_p95'] = float(np.percentile(l8n, 95))
            real[f'{mode}_p_l8'] = float((l8n >= real['last8_avg_pct']).mean())
        rows.append(real)
        print(real, flush=True)

# walk-forward
PREP = {q: prep(qn < q) for q in range(8, 22)}
Y = {'real': [y], 'shuffle': [G.shuffle_within(y, qn, rng) for _ in range(300)],
     'signflip': [G.signflip(y, qn, rng) for _ in range(300)]}
wf_trades = []
for m in (15, 30, 60):
    for side in ('either', 'long'):
        res = {}
        for mode, ylist in Y.items():
            out = []
            for ys in ylist:
                tot, n, tot8, n8, qp, qw = 0.0, 0, 0.0, 0, 0, 0
                for q in range(8, 22):
                    Mq, Xq, Kq, Qq, nq = PREP[q]
                    a, c, s = best1(Xq, Kq, Qq, ys, qn < q, m, side)
                    pk = Mq[c] & (qn == q)
                    pn = s * ys[pk]
                    tot += pn.sum(); n += len(pn)
                    if q >= 14:
                        tot8 += pn.sum(); n8 += len(pn)
                    if len(pn):
                        qw += 1; qp += pn.mean() > 0
                    if mode == 'real':
                        for ii, p in zip(np.where(pk)[0], pn):
                            wf_trades.append({'min_trades': m, 'side': side, 'qn': q, 'symbol': df.symbol[ii],
                                              'rule': G.rule_str(nq, [c], s), 'pnl_pct': 100 * p})
                out.append((100 * tot / max(n, 1), n, 100 * tot8 / max(n8, 1), n8, qp, qw))
            res[mode] = np.array(out)
        r = res['real'][0]
        row = {'part': 'walkforward', 'min_trades': m, 'side': side, 'wf_trades': int(r[1]), 'wf_avg_pct': r[0],
               'wf_q_pos': f'{int(r[4])}/{int(r[5])}', 'wf_last8_trades': int(r[3]), 'wf_last8_avg_pct': r[2]}
        for mode in ('shuffle', 'signflip'):
            nv = res[mode][:, 0]
            row[f'{mode}_wf_mean'] = float(nv.mean()); row[f'{mode}_wf_p95'] = float(np.percentile(nv, 95))
            row[f'{mode}_p_wf'] = float((nv >= r[0]).mean())
        rows.append(row)
        print(row, flush=True)
pd.DataFrame(rows).to_csv(f'{G.HERE}/one_condition_summary.csv', index=False)
pd.DataFrame(wf_trades).to_csv(f'{G.HERE}/one_condition_wf_trades.csv', index=False)
