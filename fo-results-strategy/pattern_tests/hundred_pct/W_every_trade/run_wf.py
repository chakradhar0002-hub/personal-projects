"""
run_wf.py -- walk-forward: for each quarter q = 6..21 build conditions and search on quarters < q only, pick a rule,
trade it in quarter q.  Picks (per minimum trade count m and side long / short / either):
   shrunk  : top-1 by (wins+1)/(n+2)                         (n >= m, picks in >= 4 earlier quarters)
   wilson  : top-1 by Wilson 95% lower bound of the win rate  (same eligibility)
   largest : the largest rule with 100% winners so far        (ties: fewer conditions)
   all100  : EVERY rule with 100% winners so far, all traded  (pooled; shows what "100% so far" is worth)
"either" = the side whose top rule has the higher score (largest: more trades).
Real data and NSHUF within-quarter shuffles + NFLIP sign-flips (same null draw used across all quarters of a run).
usage: python3 run_wf.py UNIVERSE SETTING THR NSHUF NFLIP [--B 500] [--q0 6] [--seed 7]
Outputs: wf_<tag>.json (summary real + null distribution), wf_trades_<tag>.csv (real trades), wf_rules_<tag>.csv
"""
import sys, os, json, time, argparse
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wlib as W

ap = argparse.ArgumentParser()
ap.add_argument('universe'); ap.add_argument('setting'); ap.add_argument('thr')
ap.add_argument('nshuf', type=int); ap.add_argument('nflip', type=int)
ap.add_argument('--B', type=int, default=500); ap.add_argument('--q0', type=int, default=6)
ap.add_argument('--seed', type=int, default=7)
A = ap.parse_args()
tag = f'{A.universe}_{A.setting}_{A.thr}'
thr = 0.0 if A.thr == 'gross' else W.COST
H = W.HERE
MS = (10, 15, 20, 30)
t0 = time.time()
df = W.load(A.universe)
qn = df.qn.values
pc = W.pieces(df)
rng = np.random.default_rng(A.seed)
draws = [('real', 0, pc)]
for kind, n in (('shuffle', A.nshuf), ('signflip', A.nflip)):
    for i in range(n):
        draws.append((kind, i, W.null_pieces(pc, qn, kind, rng)))
outs = [W.outcomes(p)[A.setting] for _, _, p in draws]
# trades[d][(crit, m, side)] = list of (qn, pnl, row)
trades = [dict() for _ in draws]
all100 = [dict() for _ in draws]          # (m, side) -> [wins, trades, quarters list]
rules_rows = []


def add(d, key, q, pnl, rows):
    trades[d].setdefault(key, []).extend(zip([q] * len(pnl), pnl, rows))


for q in range(A.q0, 22):
    tr, te = qn < q, qn == q
    E = W.Engine(df, tr, te, B=A.B, ntop=1, ms=MS)
    for d, (kind, i, _) in enumerate(draws):
        pl, ps = outs[d]
        r = E.run(pl, ps, thr, keep_list=True)
        for m in MS:
            for crit in ('shrunk', 'wilson', 'largest'):
                best = {}
                for sgn in (1, -1):
                    so = r['sides'][sgn]
                    if crit == 'largest':
                        L = so['list100']
                        ok = L['n'] >= m
                        if not ok.any():
                            continue
                        ix = np.nonzero(ok)[0][np.lexsort((L['level'][ok], -L['n'][ok]))[0]]
                        conds = [int(c) for c in L['conds'][ix] if c >= 0]
                        best[sgn] = (float(L['n'][ix]), conds)
                    else:
                        rr = so[m][crit]['rules']
                        if not rr:
                            continue
                        best[sgn] = (rr[0]['score'], rr[0]['conds'])
                if not best:
                    continue
                either = max(best, key=lambda s: (best[s][0], s))   # tie -> long
                for side, sgn in (('long', 1), ('short', -1), ('either', either)):
                    if sgn not in best:
                        continue
                    conds = best[sgn][1]
                    mk = W.rule_mask(E.M, conds) & te
                    pnl = (pl if sgn > 0 else ps)[mk]
                    add(d, (crit, m, side), q, pnl, np.nonzero(mk)[0])
                    if d == 0:
                        rules_rows.append({'q': q, 'criterion': crit, 'min_trades': m, 'side': side,
                                           'rule': W.rule_str(E.names, conds, sgn), 'score': best[sgn][0],
                                           'q_trades': int(len(pnl)), 'q_wins': int((pnl > thr).sum()),
                                           'q_avg': 100 * pnl.mean() if len(pnl) else np.nan})
            for sgn, side in ((1, 'long'), (-1, 'short')):
                L = r['sides'][sgn]['list100']
                ok = (L['n'] >= m) & (L['nte'] > 0)
                a = all100[d].setdefault((m, side), [0, 0, 0, 0])
                a[0] += int(L['wte'][ok].sum()); a[1] += int(L['nte'][ok].sum())
                a[2] += int(ok.sum()); a[3] += int((L['n'] >= m).sum())
    print(tag, 'quarter', q, 'done', round(time.time() - t0, 1), flush=True)


def wf_stats(lst):
    if not lst:
        return {'trades': 0}
    qq = np.array([x[0] for x in lst]); p = np.array([x[1] for x in lst])
    if len(p) == 0:
        return {'trades': 0}
    qa = pd.Series(p).groupby(qq).mean()
    allwin_q = pd.Series(p > thr).groupby(qq).all()
    return {'trades': int(len(p)), 'wins': int((p > thr).sum()), 'win_rate': 100 * float((p > thr).mean()),
            'avg': 100 * float(p.mean()), 'worst': 100 * float(p.min()), 'quarters': int(len(qa)),
            'quarters_pos': int((qa > thr).sum()), 'quarters_all_trades_won': int(allwin_q.sum()),
            'last8_trades': int((qq >= 14).sum()),
            'last8_win_rate': 100 * float((p[qq >= 14] > thr).mean()) if (qq >= 14).any() else None,
            'last8_avg': 100 * float(p[qq >= 14].mean()) if (qq >= 14).any() else None}


summ = []
for d, (kind, i, _) in enumerate(draws):
    for key, lst in trades[d].items():
        s = wf_stats(lst); s.update(kind=kind, run=i, criterion=key[0], min_trades=key[1], side=key[2])
        summ.append(s)
    for (m, side), a in all100[d].items():
        summ.append({'kind': kind, 'run': i, 'criterion': 'all100', 'min_trades': m, 'side': side,
                     'trades': a[1], 'wins': a[0], 'win_rate': 100 * a[0] / a[1] if a[1] else None,
                     'n_rule_quarters': a[3], 'n_rule_quarters_with_trades': a[2]})
S = pd.DataFrame(summ)
S.to_csv(f'{H}/wf_all_runs_{tag}.csv', index=False)
R0 = S[S.kind == 'real']
comp = []
for _, r in R0.iterrows():
    row = r.to_dict()
    for kind in ('shuffle', 'signflip'):
        g = S[(S.kind == kind) & (S.criterion == r.criterion) & (S.min_trades == r.min_trades) & (S.side == r.side)]
        for col in ('win_rate', 'avg'):
            if col in g and g[col].notna().any() and pd.notna(r.get(col)):
                v = g[col].dropna()
                row[f'{kind}_{col}_mean'] = float(v.mean()); row[f'{kind}_{col}_p95'] = float(v.quantile(0.95))
                row[f'{kind}_{col}_p'] = float((v >= r[col] - 1e-12).mean()); row[f'{kind}_n'] = int(len(v))
    comp.append(row)
C = pd.DataFrame(comp)
C.to_csv(f'{H}/wf_{tag}.csv', index=False)
tr_rows = []
for key, lst in trades[0].items():
    for qq, p, rw in lst:
        tr_rows.append({'criterion': key[0], 'min_trades': key[1], 'side': key[2], 'qn': qq,
                        'symbol': df.symbol.values[rw], 'pnl_pct': 100 * p})
pd.DataFrame(tr_rows).to_csv(f'{H}/wf_trades_{tag}.csv', index=False)
pd.DataFrame(rules_rows).to_csv(f'{H}/wf_rules_{tag}.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
print(C[['criterion', 'min_trades', 'side', 'trades', 'win_rate', 'avg', 'worst', 'quarters', 'quarters_pos',
         'quarters_all_trades_won'] + [c for c in C.columns if c.endswith('win_rate_mean') or c.endswith('win_rate_p')]].to_string())
print('done', round(time.time() - t0, 1))
