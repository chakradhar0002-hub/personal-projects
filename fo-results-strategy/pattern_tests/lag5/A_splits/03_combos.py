"""
03_combos.py -- the pre-registered combination step (prereg.py docstring), applied mechanically to splits_fo.csv,
plus full evaluation of the combos and of the best single splits.

  * S20 (volume) placebo now available via placebo_vol.csv (01b).
  * Battery luck refined: max |t| / count |t|>=2 only over splits whose two sides share >= 10 quarters
    (with 3-5 shared quarters a per-quarter t explodes under the null and the statistic is meaningless).
  * COMBO-H (chosen on qn 0-13 only), its null (identical selection on 500 shuffled + sign-flipped outcome sets).
  * COMBO-T (task wording, chosen after seeing the last 8 -> in-sample only).
  * Every rule: all-22, first 14 / last 8, per quarter, quarters positive, gross/net, tp3, without best 5,
    placebo (non-results dates), luck (5,000 random same-size-per-quarter subsets of the group).
"""
import os, sys, json
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from prereg import SPLITS, FIRST14, COST

pd.set_option('display.width', 250, 'display.max_columns', 60, 'display.max_rows', 300)
rng = np.random.default_rng(7)
G = pd.read_csv(f'{HERE}/group_fo.csv').reset_index(drop=True)
GA = pd.read_csv(f'{HERE}/group_all.csv').reset_index(drop=True)
PL = pd.read_csv(f'{HERE}/placebo_vol.csv')
PL.loc[PL.sector_index == 'Nifty 500', 'sec_vs_nifty_1m'] = np.nan
PLF = PL[PL.in_fo == True].reset_index(drop=True)
T = pd.read_csv(f'{HERE}/splits_fo.csv')
SP = {s[0]: s for s in SPLITS}
NOPL = {'iv_vs_realised', 'days_after_quarter_end', 'peers_reported_3d', 'season_so_far_3d'}
y = G.three_day_pct.values
q = G.qn.values.astype(int)
QS = np.arange(22)
qidx = [np.where(q == k)[0] for k in QS]


def emask(df, expr):
    with np.errstate(invalid='ignore'):
        return df.eval(expr).fillna(False).astype(bool).values


def tstat(d):
    d = d[np.isfinite(d)]
    if len(d) < 3 or d.std(ddof=1) == 0:
        return np.nan
    return d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))


def qmeans(yy, qq, m):
    s = np.bincount(qq[m], weights=yy[m], minlength=22); n = np.bincount(qq[m], minlength=22)
    with np.errstate(invalid='ignore', divide='ignore'):
        return s / n, n


# ------------------------------------------------------------------ S20 placebo (volume)
s20 = SP['S20']
pA, pB = emask(PLF, s20[3]), emask(PLF, s20[4])
a, _ = qmeans(PLF.three_day_pct.values, PLF.qn.values, pA); b, _ = qmeans(PLF.three_day_pct.values, PLF.qn.values, pB)
s20pl = dict(pl_A_n=int(pA.sum()), pl_A_avg=PLF.three_day_pct[pA].mean(), pl_A_tp=PLF.tp_pct[pA].mean(),
             pl_A_f14=PLF.three_day_pct[pA & (PLF.qn < FIRST14)].mean(), pl_A_l8=PLF.three_day_pct[pA & (PLF.qn >= FIRST14)].mean(),
             pl_B_n=int(pB.sum()), pl_B_avg=PLF.three_day_pct[pB].mean(), pl_diff=np.nanmean(a - b), pl_t22=tstat(a - b))
print('S20 volume placebo:', {k: round(float(v), 3) for k, v in s20pl.items()})
# all placebo rows (not only lag > 5%) with high volume, as context
print('   placebo, lag>5%, volume>=1.5 & lag>10%:', round(PLF.three_day_pct[pA & (PLF.lag < -0.10)].mean(), 3),
      int((pA & (PLF.lag < -0.10)).sum()), '| results same:', round(G.three_day_pct[emask(G, s20[3]) & (G.lag < -0.10).values].mean(), 3),
      int((emask(G, s20[3]) & (G.lag < -0.10).values).sum()))

# ------------------------------------------------------------------ refined battery luck
MA = np.array([emask(G, s[3]) for s in SPLITS]); MB = np.array([emask(G, s[4]) for s in SPLITS])
Q = np.zeros((22, len(y))); Q[q, np.arange(len(y))] = 1
nA = MA.astype(float) @ Q.T; nB = MB.astype(float) @ Q.T
shared = ((nA > 0) & (nB > 0)).sum(1)
keep = shared >= 10
qm = pd.Series(y).groupby(q).mean().reindex(QS).values


def tv(yy):
    with np.errstate(invalid='ignore', divide='ignore'):
        d = (MA * yy) @ Q.T / nA - (MB * yy) @ Q.T / nB
    ok = np.isfinite(d); n = ok.sum(1)
    dm = np.where(ok, d, 0).sum(1) / n
    ss = np.where(ok, (d - dm[:, None]) ** 2, 0).sum(1) / (n - 1)
    return dm / np.sqrt(ss / n)


def shuffled_signflip():
    yy = y.copy()
    for ix in qidx:
        yy[ix] = y[rng.permutation(ix)]
    return qm[q] + rng.choice([-1.0, 1.0], len(y)) * (yy - qm[q])


treal = tv(y)[keep]
nulls = []
for _ in range(2000):
    t = tv(shuffled_signflip())[keep]
    nulls.append((np.nanmax(np.abs(t)), (np.abs(t) >= 2).sum(), (t >= 2).sum()))
nulls = np.array(nulls)
battery = dict(n_splits_used=int(keep.sum()), real_max_abs_t=float(np.nanmax(np.abs(treal))),
               real_n_abs_t_ge2=int((np.abs(treal) >= 2).sum()), real_n_t_ge2=int((treal >= 2).sum()),
               null_mean_max_abs_t=float(nulls[:, 0].mean()), null_p95_max_abs_t=float(np.percentile(nulls[:, 0], 95)),
               p_max_abs_t=float((nulls[:, 0] >= np.nanmax(np.abs(treal))).mean()),
               null_mean_n_abs_t_ge2=float(nulls[:, 1].mean()), p_n_abs_t_ge2=float((nulls[:, 1] >= (np.abs(treal) >= 2).sum()).mean()),
               null_mean_n_t_ge2=float(nulls[:, 2].mean()), p_n_t_ge2=float((nulls[:, 2] >= (treal >= 2).sum()).mean()))
print('\nBATTERY LUCK (splits sharing >= 10 quarters):', json.dumps(battery, indent=1))


# ------------------------------------------------------------------ rule evaluation
def evaluate(label, exprs, sign, chosen_before_last8, nluck=5000, universe=G, pl=PLF):
    m = np.ones(len(universe), bool)
    for e in exprs:
        m &= emask(universe, e)
    yy = universe.three_day_pct.values; qq = universe.qn.values.astype(int)
    pnl = sign * yy[m]; tp = sign * universe.tp_pct.values[m]
    qa, qn_ = qmeans(sign * yy, qq, m)
    has = qn_ > 0
    f14 = m & (qq < FIRST14); l8 = m & (qq >= FIRST14)
    srt = np.sort(pnl)
    out = dict(name=label, rule=('LONG' if sign > 0 else 'SHORT') + ': lag > 5% AND ' + ' AND '.join(exprs),
               trades=int(m.sum()), avg_pct=pnl.mean() if m.any() else np.nan, avg_net_pct=pnl.mean() - COST if m.any() else np.nan,
               tp_pct=tp.mean() if m.any() else np.nan, up_pct=100 * (pnl > 0).mean() if m.any() else np.nan,
               quarters_positive=f'{int((qa[has] > 0).sum())}/{int(has.sum())}', quarters_with_trades=int(has.sum()),
               first14_trades=int(f14.sum()), first14_avg_pct=sign * yy[f14].mean() if f14.any() else np.nan,
               last8_trades=int(l8.sum()), last8_avg_pct=sign * yy[l8].mean() if l8.any() else np.nan,
               last8_tp_pct=sign * universe.tp_pct.values[l8].mean() if l8.any() else np.nan,
               last8_quarters_positive=f'{int((qa[14:][has[14:]] > 0).sum())}/{int(has[14:].sum())}',
               without_best5_avg_pct=srt[:-5].mean() if len(srt) > 5 else np.nan,
               avg_lag=100 * universe.lag.values[m].mean() if m.any() else np.nan,
               chosen_before_seeing_last8=chosen_before_last8)
    # luck: random same-size-per-quarter subsets of the group
    if universe is G and m.any():
        cnt = np.bincount(qq[m], minlength=22)
        draws = np.zeros(nluck)
        for k in QS:
            if cnt[k] == 0:
                continue
            ix = qidx[k]
            draws += y[ix][rng.random((nluck, len(ix))).argsort(1)[:, :cnt[k]]].sum(1)
        draws = sign * draws / m.sum()
        out['luck_p'] = float((draws >= pnl.mean()).mean())
        out['luck_random_mean'] = float(draws.mean()); out['luck_random_p95'] = float(np.percentile(draws, 95))
        if l8.any():
            cnt8 = cnt.copy(); cnt8[:14] = 0
            d8 = np.zeros(nluck)
            for k in range(14, 22):
                if cnt8[k]:
                    d8 += y[qidx[k]][rng.random((nluck, len(qidx[k]))).argsort(1)[:, :cnt8[k]]].sum(1)
            d8 = sign * d8 / l8.sum()
            out['luck_p_last8'] = float((d8 >= out['last8_avg_pct']).mean())
    # placebo
    if pl is not None:
        pe = [e for e in exprs if not any(f in e for f in NOPL)]
        out['placebo_dropped'] = ', '.join(e for e in exprs if e not in pe)
        pm = np.ones(len(pl), bool)
        for e in pe:
            pm &= emask(pl, e)
        pp = sign * pl.three_day_pct.values[pm]
        out['placebo_n'] = int(pm.sum()); out['placebo_avg_pct'] = pp.mean() if pm.any() else np.nan
        out['placebo_tp_pct'] = sign * pl.tp_pct.values[pm].mean() if pm.any() else np.nan
        out['placebo_f14'] = sign * pl.three_day_pct.values[pm & (pl.qn.values < FIRST14)].mean() if pm.any() else np.nan
        out['placebo_l8'] = sign * pl.three_day_pct.values[pm & (pl.qn.values >= FIRST14)].mean() if pm.any() else np.nan
        pq, pn = qmeans(sign * pl.three_day_pct.values, pl.qn.values.astype(int), pm)
        out['placebo_quarters_positive'] = f'{int((pq[pn > 0] > 0).sum())}/{int((pn > 0).sum())}'
        out['results_minus_placebo'] = out['avg_pct'] - out['placebo_avg_pct']
    perq = pd.DataFrame({'qn': QS, 'trades': qn_, 'avg': qa})
    return out, perq


# ------------------------------------------------------------------ COMBO-H selection (first 14 only)
def select_H(Tab, side='A'):
    if side == 'A':
        el = Tab[(Tab.A_n14 >= 25) & (Tab.t14 >= 1.5) & (Tab.A_f14 > 0)]
    else:
        el = Tab[(Tab.B_n14 >= 25) & (Tab.t14 >= 1.5) & (Tab.B_f14 < 0)]
    el = el.sort_values('t14', ascending=False)
    picks, fams = [], set()
    for _, r in el.iterrows():
        if r.family in fams:
            continue
        picks.append(r.id); fams.add(r.family)
        if len(picks) == 3:
            break
    return picks


picksA = select_H(T, 'A'); picksB = select_H(T, 'B')
print('\nCOMBO-H long picks (first-14 t ranked):', picksA, ' short picks:', picksB)
print(T[T.id.isin(picksA + picksB)][['id', 'name', 'A_n14', 'A_f14', 'B_n14', 'B_f14', 't14']].round(2).to_string())


def select_T(Tab):
    el = Tab[(Tab.A_f14 > 0) & (Tab.A_l8 > 0) & (Tab.qdiff14 > 0) & (Tab.qdiff8 > 0)].sort_values('t22', ascending=False)
    picks, fams = [], set()
    for _, r in el.iterrows():
        if r.family in fams or not np.isfinite(r.t22):
            continue
        picks.append(r.id); fams.add(r.family)
        if len(picks) == 3:
            break
    return picks, el


picksT, elT = select_T(T)
print('COMBO-T eligible (ranked by all-22 t):'); print(elT[['id', 'name', 'family', 'A_f14', 'A_l8', 'qdiff14', 'qdiff8', 't22']].round(2).to_string())
print('COMBO-T picks:', picksT)

R, PQ = [], {}


def add(label, ids_or_exprs, sign, before, side='A'):
    exprs = [SP[i][3 if side == 'A' else 4] if i in SP else i for i in ids_or_exprs]
    o, pq = evaluate(label, exprs, sign, before)
    R.append(o); PQ[label] = pq
    return o


add('COMBO-H long 2-way', picksA[:2], +1, True)
if len(picksA) >= 3:
    m3 = np.ones(len(G), bool)
    for i in picksA:
        m3 &= emask(G, SP[i][3])
    if (m3 & (q < FIRST14)).sum() >= 15:
        add('COMBO-H long 3-way', picksA, +1, True)
    else:
        print('COMBO-H 3-way skipped: first-14 trades', int((m3 & (q < FIRST14)).sum()))
add('COMBO-H short 2-way', picksB[:2], -1, True, side='B')
add('COMBO-T long 2-way (in-sample)', picksT[:2], +1, False)
if len(picksT) >= 3:
    add('COMBO-T long 3-way (in-sample)', picksT, +1, False)
# best single splits, as reported (selected after seeing all 22 quarters, except S02 which earlier work had found)
add('S02 lag > 15%', ['S02'], +1, False)
add('S20 capitulation volume >= 1.5x', ['S20'], +1, False)
add('S14 news-shock day <= -6%', ['S14'], +1, False)
add('S40 India VIX >= 18', ['S40'], +1, False)
add('S19-B 3M return < -15% (opposite of prereg direction)', ['S19'], +1, False, side='B')
add('S03-B stock up on month but lagged >5% (short)', ['S03'], -1, False, side='B')
add('S01-B lag 5-10% (short)', ['S01'], -1, False, side='B')
add('S21-B vol60 < 25% (short)', ['S21'], -1, False, side='B')
add('whole group (reference)', ['lag < -0.05'], +1, False)
Rd = pd.DataFrame(R)
Rd.to_csv(f'{HERE}/combos_and_candidates.csv', index=False)
pd.concat([v.assign(rule=k) for k, v in PQ.items()]).to_csv(f'{HERE}/combos_per_quarter.csv', index=False)
show = ['name', 'trades', 'avg_pct', 'avg_net_pct', 'tp_pct', 'up_pct', 'quarters_positive', 'first14_trades', 'first14_avg_pct',
        'last8_trades', 'last8_avg_pct', 'last8_tp_pct', 'last8_quarters_positive', 'without_best5_avg_pct', 'avg_lag', 'luck_p',
        'luck_p_last8', 'placebo_n', 'placebo_avg_pct', 'placebo_f14', 'placebo_l8', 'placebo_quarters_positive', 'results_minus_placebo', 'placebo_dropped']
print('\nRULES (percent):'); print(Rd[show].round(2).to_string())
for k, v in PQ.items():
    print(k, ' | '.join(f"{int(r.qn)}:{int(r.trades)}/{r.avg:+.1f}" for r in v.itertuples() if r.trades > 0))

# ------------------------------------------------------------------ COMBO-H null: identical selection on shuffled outcomes
n14A = MA[:, q < FIRST14].sum(1); n14B = MB[:, q < FIRST14].sum(1)
fam = np.array([s[1] for s in SPLITS]); ids = np.array([s[0] for s in SPLITS])


def table_from(yy):
    with np.errstate(invalid='ignore', divide='ignore'):
        a = (MA * yy) @ Q.T / nA; b = (MB * yy) @ Q.T / nB
    d = a - b
    t14 = np.array([tstat(r[:FIRST14]) for r in d])
    f14m = (q < FIRST14)
    A14 = (MA[:, f14m] * yy[f14m]).sum(1) / np.maximum(n14A, 1)
    B14 = (MB[:, f14m] * yy[f14m]).sum(1) / np.maximum(n14B, 1)
    return pd.DataFrame({'id': ids, 'family': fam, 'A_n14': n14A, 'B_n14': n14B, 'A_f14': A14, 'B_f14': B14, 't14': t14})


null = []
for it in range(500):
    yy = shuffled_signflip()
    Tn = table_from(yy)
    pk = select_H(Tn, 'A')
    if len(pk) < 2:
        null.append((np.nan, np.nan, np.nan, 0)); continue
    m = MA[list(ids).index(pk[0])] & MA[list(ids).index(pk[1])]
    null.append((yy[m & (q < FIRST14)].mean(), yy[m & (q >= FIRST14)].mean() if (m & (q >= FIRST14)).any() else np.nan,
                 yy[m].mean(), int(m.sum())))
null = pd.DataFrame(null, columns=['f14', 'l8', 'all', 'n'])
null.to_csv(f'{HERE}/comboH_null.csv', index=False)
ch = Rd[Rd.name == 'COMBO-H long 2-way'].iloc[0]
nullsum = dict(runs=len(null), runs_with_combo=int(null.f14.notna().sum()), null_f14_mean=null.f14.mean(),
               null_f14_p95=null.f14.quantile(.95), real_f14=ch.first14_avg_pct, p_f14=float((null.f14 >= ch.first14_avg_pct).mean()),
               null_l8_mean=null.l8.mean(), null_l8_sd=null.l8.std(), real_l8=ch.last8_avg_pct,
               p_l8=float((null.l8 >= ch.last8_avg_pct).mean()), null_trades_median=float(null.n.median()))
print('\nCOMBO-H selection null (500 shuffled + sign-flipped outcome sets):', {k: (round(v, 3) if isinstance(v, float) else v) for k, v in nullsum.items()})

# ------------------------------------------------------------------ all-results secondary for the main rules
R2 = []
for lab, ex, sg in [('COMBO-H long 2-way', [SP[i][3] for i in picksA[:2]], 1), ('S02 lag > 15%', [SP['S02'][3]], 1),
                    ('S20 capitulation volume', [SP['S20'][3]], 1), ('S14 news shock', [SP['S14'][3]], 1),
                    ('S03-B short', [SP['S03'][4]], -1)]:
    o, _ = evaluate(lab, ex, sg, False, universe=GA, pl=None)
    R2.append(o)
R2 = pd.DataFrame(R2)
R2.to_csv(f'{HERE}/candidates_all_results.csv', index=False)
print('\nALL RESULTS (secondary):'); print(R2[['name', 'trades', 'avg_pct', 'tp_pct', 'up_pct', 'quarters_positive', 'first14_avg_pct', 'last8_avg_pct', 'without_best5_avg_pct']].round(2).to_string())
json.dump({'battery_refined': battery, 's20_placebo': s20pl, 'comboH_null': nullsum, 'picksA': picksA, 'picksB': picksB,
           'picksT': picksT}, open(f'{HERE}/combos_summary.json', 'w'), indent=1, default=float)
