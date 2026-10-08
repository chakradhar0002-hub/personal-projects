"""
oos_detail.py -- for EVERY rule with 100% winners on qn 0..13 (F&O, fixed split, beam 1000), its full record on qn 14..21:
trades, win rate, average, worst trade, quarters positive -- bucketed by in-sample size and side.
Also: the same for the identical search on ONE sign-flip and ONE shuffle draw (seeded) for comparison.
usage: python3 oos_detail.py SETTING THR       Output: oos_detail_<setting>_<thr>.csv (+ printed buckets)
"""
import sys, os
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wlib as W

setting, thrlab = sys.argv[1], sys.argv[2]
thr = 0.0 if thrlab == 'gross' else W.COST
df = W.load('fo'); qn = df.qn.values
tr, te = qn <= 13, qn >= 14
E = W.Engine(df, tr, te, B=1000, ntop=1)
pc = W.pieces(df)
rng = np.random.default_rng(99)
draws = [('real', pc), ('signflip', W.null_pieces(pc, qn, 'signflip', rng)), ('shuffle', W.null_pieces(pc, qn, 'shuffle', rng))]
Mte = E.M[:, te]
qte = qn[te]
uq, qi = np.unique(qte, return_inverse=True)
Qmat = np.zeros((len(qte), len(uq)), np.float32); Qmat[np.arange(len(qte)), qi] = 1
rows = []
for kind, p in draws:
    pl, ps = W.outcomes(p)[setting]
    r = E.run(pl, ps, thr, keep_list=True)
    for sgn in (1, -1):
        L = r['sides'][sgn]['list100']
        n = len(L['n'])
        if not n:
            continue
        y = (pl if sgn > 0 else ps)[te]
        # boolean OOS masks for all rules (n x Nte)
        mk = np.ones((n, te.sum()), bool)
        for j in range(3):
            c = L['conds'][:, j]
            ok = c >= 0
            mk[ok] &= Mte[c[ok]]
        nt = mk.sum(1)
        wins = (mk & (y > thr)).sum(1)
        s = mk @ y
        worst = np.where(mk, y, np.inf).min(1)
        qs = mk.astype(np.float32) @ (Qmat * y[:, None])
        qc = mk.astype(np.float32) @ Qmat
        qpos = ((qc > 0) & (qs / np.maximum(qc, 1) > thr)).sum(1)
        qwith = (qc > 0).sum(1)
        for i in range(n):
            rows.append((kind, 'long' if sgn > 0 else 'short', int(L['level'][i]), int(L['n'][i]), int(nt[i]), int(wins[i]),
                         float(s[i]), float(worst[i]) if nt[i] else np.nan, int(qwith[i]), int(qpos[i])))
D = pd.DataFrame(rows, columns=['kind', 'side', 'level', 'is_n', 'oos_n', 'oos_wins', 'oos_sum', 'oos_worst', 'oos_q', 'oos_qpos'])
D.to_csv(f'{W.HERE}/oos_detail_{setting}_{thrlab}.csv.gz', index=False)
D['bucket'] = pd.cut(D.is_n, [9, 14, 19, 24, 100], labels=['10-14', '15-19', '20-24', '25+'])
D = D[D.oos_n > 0]
agg = D.groupby(['kind', 'side', 'bucket'], observed=True).apply(lambda g: pd.Series({
    'rules': len(g), 'median_oos_trades': g.oos_n.median(), 'pooled_oos_winrate': 100 * g.oos_wins.sum() / g.oos_n.sum(),
    'mean_oos_avg': 100 * (g.oos_sum / g.oos_n).mean(), 'median_oos_worst': 100 * g.oos_worst.median(),
    'frac_oos_all_win': (g.oos_wins == g.oos_n).mean(), 'frac_oos_all_win_5plus': ((g.oos_wins == g.oos_n) & (g.oos_n >= 5)).mean(),
    'frac_all_oos_quarters_pos': (g.oos_qpos == g.oos_q).mean()}))
pd.set_option('display.width', 250)
print(agg.round(3).to_string())
agg.to_csv(f'{W.HERE}/oos_detail_buckets_{setting}_{thrlab}.csv')
