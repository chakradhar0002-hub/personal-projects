"""
07_candidates.py -- detailed honest checks of the candidates.
Selection (mechanical, first-14 information only; declared before this script was run, but after the rank-1 rules'
last-8 averages had been printed by 02_fixed_split.py):
  C1  rank-1 rule (either side) of the fixed-split search, objective mean,  min trades 30
  C2  rank-1 rule (either side), objective fpos (share of quarters positive), min trades 30
  C3  rank-1 rule (either side), objective worst quarter, min trades 30
  C4  best rule with at most 2 conditions (long, objective mean, min trades 30, >= 6 quarters) -- the simple version
  C5  best 1-condition rule (either side, objective mean, min trades 30, >= 6 quarters) -- added after C1-C4 were
      run, chosen on the first 14 quarters only (rank 1 of 4,192 one-condition rules)
All four turn out to be LONG rules.  For each: all-22 / first-14 / last-8 numbers (gross, net of 0.17%), take-profit
exit, per-quarter table, without the best 5 trades, luck test (10,000 random same-size-per-quarter subsets of the
group), placebo (lag > 5% AND the rule on the same F&O stocks at dates with no result session within 10 sessions,
next-3-session return), and the all-results universe (secondary).
Outputs: candidates.csv, candidates_per_quarter.csv, candidates_trades.csv
"""
import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsearch as G

df = G.load_group('fo')
y = df.three_day.values.astype(float); tp = df.tp3.values.astype(float); qn = df.qn.values
tr = qn <= 13; te = ~tr
M, names, compat = G.build_conditions(df, tr)
T = pd.read_csv(f'{G.HERE}/fixed_fo_real_top.csv')


def top_either(o, m):
    d = T[(T.objective == o) & (T.min_trades == m)].sort_values(['is_obj', 'is_avg_pct'], ascending=False)
    r = d.iloc[0]
    return json.loads(r.conds), int(r.sign)


# C4: best <= 2-condition long rule, mean objective, m = 30, picks in >= 6 quarters (exhaustive)
S = G.GSearcher(M[:, tr], qn[tr], compat, ms=(15, 30, 60), minq=6)
X = S.X; yt = y[tr].astype(np.float32)
S1 = X @ yt; m1 = S1 / np.maximum(S.K1, 1); v1 = (S.K1 >= 30) & (S.Q1 >= 6)
S2 = ((X * yt) @ X.T).ravel()[S.idx2]; m2 = S2 / S.K2; v2 = (S.K2 >= 30) & (S.Q2 >= 6)
b1 = np.argmax(np.where(v1, m1, -np.inf)); b2 = np.argmax(np.where(v2, m2, -np.inf))
if m2[b2] > m1[b1]:
    c4 = list(divmod(int(S.idx2[b2]), S.C))
else:
    c4 = [int(b1)]
o1l = np.where(v1, m1, -np.inf); o1s = np.where(v1, -m1, -np.inf)
c5 = ([int(np.argmax(o1l))], 1) if o1l.max() >= o1s.max() else ([int(np.argmax(o1s))], -1)
CANDS = {'C1': top_either('mean', 30), 'C2': top_either('fpos', 30), 'C3': top_either('worst', 30), 'C4': (c4, 1), 'C5': c5}
for k, (c, s) in CANDS.items():
    print(k, G.rule_str(names, c, s))

# ---------------- placebo panel
L = pd.read_pickle(f'{G.HERE}/placebo_panel.pkl')
PLACEBO_MAP = {'own_rd': 'own_rd_asof'}
Lg = L[L.vs_nifty_1m < -0.05]


def placebo(conds):
    mk = np.ones(len(Lg), bool); used, skipped = [], []
    for c in conds:
        f, op, v = names[c]
        col = PLACEBO_MAP.get(f, f)
        if col not in Lg.columns:
            skipped.append(f); continue
        x = Lg[col].values
        with np.errstate(invalid='ignore'):
            mk &= (x >= v) if op == '>=' else (x <= v)
        used.append(f)
    x = Lg[mk]
    d = x.groupby('day').fwd3.mean()
    return {'placebo_n': int(mk.sum()), 'placebo_avg_pct': 100 * x.fwd3.mean(), 'placebo_up_pct': 100 * (x.fwd3 > 0).mean(),
            'placebo_dates': int(len(d)), 'placebo_avg_of_date_avgs_pct': 100 * d.mean(),
            'placebo_used': '+'.join(used), 'placebo_skipped': '+'.join(skipped)}


base_placebo = {'n': len(Lg), 'avg': 100 * Lg.fwd3.mean()}
print('placebo baseline lag>5%% non-results days: n=%d avg %.3f%%' % (base_placebo['n'], base_placebo['avg']))

# ---------------- all-results universe
dfa = G.load_group('all')


def mask_on(frame, conds):
    mk = np.ones(len(frame), bool)
    for c in conds:
        f, op, v = names[c]
        x = frame[f].values
        if op == '==':
            mk &= frame[f].astype(str).values == v
        else:
            with np.errstate(invalid='ignore'):
                mk &= (x >= v) if op == '>=' else (x <= v)
    return mk


rng = np.random.default_rng(5)
rows, pq_rows, tr_rows = [], [], []
for k, (c, s) in CANDS.items():
    mk = G.rule_mask(M, c)
    pn = s * y[mk]; q = qn[mk]
    r = {'candidate': k, 'rule': G.rule_str(names, c, s)}
    r.update(G.stats(pn, q, 'all22_'))
    r.update(G.stats(pn[q <= 13], q[q <= 13], 'first14_'))
    r.update(G.stats(pn[q >= 14], q[q >= 14], 'last8_'))
    if s > 0:
        r['all22_tp_avg_pct'] = 100 * tp[mk].mean(); r['last8_tp_avg_pct'] = 100 * tp[mk & te].mean()
        r['first14_tp_avg_pct'] = 100 * tp[mk & tr].mean()
    # luck: random subsets of the group with the same number of picks per quarter
    cnt = pd.Series(q).value_counts()
    idx_by_q = {qq: np.where(qn == qq)[0] for qq in cnt.index}
    sims, sims8 = [], []
    for _ in range(10000):
        tot, n, tot8, n8 = 0.0, 0, 0.0, 0
        for qq, nn in cnt.items():
            pick = rng.choice(idx_by_q[qq], nn, replace=False)
            v = s * y[pick].sum()
            tot += v; n += nn
            if qq >= 14:
                tot8 += v; n8 += nn
        sims.append(tot / n); sims8.append(tot8 / n8 if n8 else np.nan)
    sims, sims8 = np.array(sims), np.array(sims8)
    r['luck_p_all22'] = float((sims >= pn.mean()).mean())
    r['luck_p_last8'] = float((sims8 >= pn[q >= 14].mean()).mean()) if (q >= 14).any() else np.nan
    r['luck_random_avg_pct'] = 100 * sims.mean(); r['luck_random_p95_pct'] = 100 * np.percentile(sims, 95)
    r.update(placebo(c))
    r['distinct_cutoff_dates'] = int(df.cutoff[mk].nunique())
    r['max_share_one_quarter'] = float(pd.Series(q).value_counts().max() / len(q))
    ma = mask_on(dfa, c)
    pa = s * dfa.three_day.values[ma]
    r.update(G.stats(pa, dfa.qn.values[ma], 'allres_'))
    r['allres_last8_avg_pct'] = 100 * pa[dfa.qn.values[ma] >= 14].mean()
    rows.append(r)
    g = pd.DataFrame({'qn': q, 'pnl': pn, 'tp': tp[mk]}).groupby('qn')
    for qq, gg in g:
        pq_rows.append({'candidate': k, 'qn': qq, 'trades': len(gg), 'avg_pct': 100 * gg.pnl.mean(),
                        'tp_avg_pct': 100 * gg.tp.mean(), 'up': int((gg.pnl > 0).sum()),
                        'group_avg_pct': 100 * y[qn == qq].mean()})
    for ii in np.where(mk)[0]:
        tr_rows.append({'candidate': k, 'symbol': df.symbol[ii], 'quarter': df.quarter[ii], 'qn': qn[ii],
                        'cutoff': df.cutoff[ii], 'results_date': df.results_date[ii], 'three_day_pct': 100 * y[ii],
                        'tp_pct': 100 * tp[ii]})
R = pd.DataFrame(rows)
R.to_csv(f'{G.HERE}/candidates.csv', index=False)
pd.DataFrame(pq_rows).to_csv(f'{G.HERE}/candidates_per_quarter.csv', index=False)
pd.DataFrame(tr_rows).to_csv(f'{G.HERE}/candidates_trades.csv', index=False)
pd.set_option('display.width', 250, 'display.max_colwidth', 120)
print(R.T.to_string())
PQ = pd.DataFrame(pq_rows)
print(PQ.pivot(index='qn', columns='candidate', values='avg_pct').round(1).join(
    PQ.pivot(index='qn', columns='candidate', values='trades'), rsuffix='_n').to_string())
