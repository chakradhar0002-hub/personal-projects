"""
05_walkforward.py -- walk-forward for reading Q (every quarter positive).

For each test quarter q = 8..21: rules are judged on quarters 0..q-1 only; a rule qualifies if every one of
those quarters that has picks is positive and it has picks in >= req quarters, req = all q (strict),
ceil(16/22*q) (hi) or ceil(10/22*q) (lo).  Chosen (pre-registered, as in 02_search):
  top1  = most quarters with picks, then best worst-quarter average, then most trades
  top10 = the 10 best by that order; portfolio = every stock picked by any of them (each once)
  all   = every qualifying rule (share of them positive in q, pooled average)
and traded in quarter q.  Families 3-day / TP (long+short), gross / after costs.
Condition cuts: percentiles of quarters 0..7 only (all before the first test quarter), so the condition set
is fixed and 1/2-condition statistics can be accumulated quarter by quarter.  3-condition rules: beam of
`beam` pairs per P&L variant re-selected every quarter from the history, then scanned over quarters 0..q.
usage: python3 05_walkforward.py NULL NRUNS SEED [--real] [--beam B]
"""
import sys, os, json, time, argparse
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qengine as E

ap = argparse.ArgumentParser()
ap.add_argument('null'); ap.add_argument('nruns', type=int); ap.add_argument('seed', type=int)
ap.add_argument('--real', action='store_true'); ap.add_argument('--beam', type=int, default=400)
ap.add_argument('--universe', default='fo')
A = ap.parse_args()
OUT = os.path.join(E.HERE, 'out'); os.makedirs(OUT, exist_ok=True)
df = E.load(A.universe)
S = E.Search(df, range(8), range(8, 22), beam=A.beam)
C = S.C
SETTINGS = [(fam, cov, net) for fam in ('3day', 'tp') for cov in ('strict', 'hi', 'lo') for net in (False, True)]
print(A, 'conditions', C, flush=True)
t0 = time.time()


def ranks(nq, mn, K, k):
    o = np.lexsort((-K, -mn, -nq.astype(int)))
    return o[:k]


def wf_one(Y, tag, keep=False):
    Yb = S.Yb(Y)
    acc2 = E.Acc((C, C))
    for q in range(8):
        Xq = S.Xb[q]
        Kq = Xq @ Xq.T
        acc2.update(Kq, {v: (Xq * Yb[q][v][None, :].astype(np.float32)) @ Xq.T for v in ('L3', 'LT', 'ST')})
    out, chosen = [], []
    for q in range(8, 22):
        req = {'strict': q, 'hi': int(np.ceil(16 / 22 * q - 1e-9)), 'lo': int(np.ceil(10 / 22 * q - 1e-9))}
        # --- beam from the history, triple scan over quarters 0..q
        elig = S.upper & (acc2.nq >= req['lo'])
        inbeam = np.zeros((C, C), bool)
        for u in E.UVARS:
            key = acc2.nf[u].astype(np.float64) * 1e4 - acc2.nq.astype(np.float64) * 100 - np.clip(acc2.mn[u], -5, 5)
            key = np.where(elig, key, np.inf).ravel()
            kk = min(S.beam, int(np.isfinite(key).sum()))
            if kk > 0:
                inbeam.ravel()[np.argpartition(key, kk - 1)[:kk]] = True
        a, b = np.nonzero(inbeam)
        A3 = {qq: S.Xb[qq][a] * S.Xb[qq][b] for qq in range(q + 1)}
        tr3, te3 = E.scan(A3, S.Xb, Yb, list(range(q + 1)), set(range(q)), {q})
        A_ = a[:, None]; B_ = b[:, None]; c_ = np.arange(C)[None, :]
        lo1 = np.minimum(A_, c_); hi1 = np.maximum(A_, c_); lo2 = np.minimum(B_, c_); hi2 = np.maximum(B_, c_)
        sm1 = (lo1 < A_) | ((lo1 == A_) & (hi1 < B_)); sm2 = (lo2 < A_) | ((lo2 == A_) & (hi2 < B_))
        valid3 = ~(inbeam[lo1, hi1] & sm1) & ~(inbeam[lo2, hi2] & sm2) & S.compat[a] & S.compat[b]
        del lo1, hi1, lo2, hi2, sm1, sm2
        # --- pair stats for quarter q
        Xq = S.Xb[q]
        Kq = Xq @ Xq.T
        Sq = {v: (Xq * Yb[q][v][None, :].astype(np.float32)) @ Xq.T for v in ('L3', 'LT', 'ST')}
        te2 = E.Acc((C, C)); te2.update(Kq, Sq)
        rows_q = S.ix[q]
        for fam, cov, net in SETTINGS:
            parts = []   # (level, r, c, u, nq, mn, K, teK, teS, tepos)
            for L, tr, te, valid in ((1, acc2, te2, S.valid1), (2, acc2, te2, S.upper), (3, tr3, te3, valid3)):
                for u in E.FAMS[fam]:
                    ok = valid & (tr.nq >= req[cov]) & ((tr.nfn[u] if net else tr.nf[u]) == 0)
                    r, c = np.nonzero(ok)
                    if len(r):
                        parts.append((np.full(len(r), L), r, c, np.full(len(r), u), tr.nq[r, c], tr.mn[u][r, c],
                                      tr.K[r, c], te.K[r, c], te.sum_for(u)[r, c]))
            d = {'run': tag, 'q': q, 'fam': fam, 'cov': cov, 'net': net, 'req': req[cov], 'n_qual': 0}
            if parts:
                Lv, rv, cv, uv, nq, mn, K, teK, teS = [np.concatenate([p[i] for p in parts]) for i in range(9)]
                thr = E.COST if net else 0.0
                d['n_qual'] = int(len(Lv))
                has = teK > 0
                d['all_n_with_picks'] = int(has.sum())
                if has.any():
                    d['all_frac_pos'] = float((teS[has] / teK[has] > thr).mean())
                    d['all_pooled_avg'] = float(teS[has].sum() / teK[has].sum())
                o = ranks(nq, mn, K, 10)
                masks = []
                for rank, i in enumerate(o):
                    if Lv[i] == 1:
                        conds = (int(rv[i]),)
                    elif Lv[i] == 2:
                        conds = (int(rv[i]), int(cv[i]))
                    else:
                        conds = tuple(sorted((int(a[rv[i]]), int(b[rv[i]]), int(cv[i]))))
                    mk = S.rule_mask(conds)[rows_q]
                    masks.append((mk, E.SIGN[uv[i]], uv[i]))
                    if rank == 0:
                        d.update(top1_is_nq=int(nq[i]), top1_is_trades=int(K[i]), top1_is_worst_q=float(mn[i]),
                                 top1_te_trades=int(teK[i]), top1_te_avg=float(teS[i] / teK[i]) if teK[i] else None)
                        if keep:
                            col = 'tp3' if fam == 'tp' else 'three_day'
                            colS = 'tp3s' if fam == 'tp' else 'three_day'
                            chosen.append({'q': q, 'fam': fam, 'cov': cov, 'net': net, 'rule': S.rule_str(conds, uv[i]),
                                           'is_quarters_with_picks': int(nq[i]), 'is_trades': int(K[i]),
                                           'is_worst_quarter_pct': 100 * float(mn[i]), 'oos_trades': int(teK[i]),
                                           'oos_avg_pct': 100 * float(teS[i] / teK[i]) if teK[i] else None,
                                           'n_qualifying': int(len(Lv))})
                # top10 portfolio: each (stock, direction) once
                yv = {'L3': Yb[q]['L3'], 'S3': -Yb[q]['L3'], 'LT': Yb[q]['LT'], 'ST': Yb[q]['ST']}
                pn = []
                for u in E.FAMS[fam]:
                    mm = np.zeros(len(rows_q), bool)
                    for mk, sg, uu in masks:
                        if uu == u:
                            mm |= mk
                    pn.append(yv[u][mm])
                pn = np.concatenate(pn)
                d['top10_te_trades'] = int(len(pn))
                d['top10_te_avg'] = float(pn.mean()) if len(pn) else None
            out.append(d)
        acc2.update(Kq, Sq)
    return out, chosen


rows = []
if A.real:
    r, ch = wf_one(E.real_Y(df), 'real', keep=True)
    rows += r
    pd.DataFrame(ch).to_csv(f'{OUT}/wf_{A.universe}_real_chosen.csv', index=False)
    print('real done', round(time.time() - t0, 1), flush=True)
    json.dump(rows, open(f'{OUT}/wf_{A.universe}_{A.null}_{A.seed}.json', 'w'), default=float)
if A.null != 'none':
    rng = np.random.default_rng(A.seed)
    for s in range(A.nruns):
        r, _ = wf_one(E.null_Y(df, A.null, rng), f'{A.null}_{A.seed}_{s}')
        rows += r
        print('run', s, round(time.time() - t0, 1), flush=True)
        json.dump(rows, open(f'{OUT}/wf_{A.universe}_{A.null}_{A.seed}.json', 'w'), default=float)
json.dump(rows, open(f'{OUT}/wf_{A.universe}_{A.null}_{A.seed}.json', 'w'), default=float)
print('done', round(time.time() - t0, 1))
