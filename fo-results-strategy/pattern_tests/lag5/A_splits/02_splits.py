"""
02_splits.py -- test every pre-registered split in prereg.py ONCE (no new splits are added here).

For each split, on the in_fo group (main) and on the all-results group (secondary):
  both sides' n, average 3-day and take-profit return, up-rate, quarters positive, first 14 vs last 8,
  average without the best 5, average lag; the A-B difference pooled and per quarter (t across quarters,
  all 22 / first 14 / last 8); depth-adjusted difference; random-subset p-values (same per-quarter counts);
  placebo on non-results dates (in_fo, lag > 5%).
Also: C01 depth curve (results vs placebo, per-quarter slope), D01 sector table, and the battery luck test
(1,000 within-quarter shuffled + sign-flipped outcome sets).
"""
import os, sys, json
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from prereg import SPLITS, LAG_BANDS, DEPTH_ADJ_BANDS, FIRST14, COST

pd.set_option('display.width', 250, 'display.max_columns', 60, 'display.max_rows', 300)
rng = np.random.default_rng(20261008)

GF = pd.read_csv(f'{HERE}/group_fo.csv')
GA = pd.read_csv(f'{HERE}/group_all.csv')
PL = pd.read_csv(f'{HERE}/placebo.csv')
PL.loc[PL.sector_index == 'Nifty 500', 'sec_vs_nifty_1m'] = np.nan     # same coverage as features_all
PLF = PL[PL.in_fo == True].reset_index(drop=True)
QS = np.arange(22)


def band_of(lag, bands):
    out = np.full(len(lag), -1)
    for k, (a, b) in enumerate(bands):
        out[(lag >= a) & (lag < b)] = k
    return out


def qmeans(y, q, m):
    """per-quarter mean of y over mask m -> array of 22 (nan where no trade)"""
    s = np.bincount(q[m], weights=y[m], minlength=22)
    n = np.bincount(q[m], minlength=22)
    with np.errstate(invalid='ignore', divide='ignore'):
        return s / n, n


def tstat(d):
    d = d[np.isfinite(d)]
    if len(d) < 3 or d.std(ddof=1) == 0:
        return np.nan, len(d)
    return d.mean() / (d.std(ddof=1) / np.sqrt(len(d))), len(d)


def side(df, m, ycol='three_day_pct'):
    x = df[m]
    y = x[ycol].values
    if len(y) == 0:
        return dict(n=0)
    qa, qn_ = qmeans(df[ycol].values, df.qn.values, m.values if hasattr(m, 'values') else m)
    has = qn_ > 0
    srt = np.sort(y)
    return dict(n=len(y), avg=y.mean(), tp=x.tp_pct.mean(), up=100 * (y > 0).mean(),
                q_with=int(has.sum()), q_pos=int((qa[has] > 0).sum()), q_neg=int((qa[has] < 0).sum()),
                f14=x[x.qn < FIRST14][ycol].mean(), l8=x[x.qn >= FIRST14][ycol].mean(),
                n14=int((x.qn < FIRST14).sum()), n8=int((x.qn >= FIRST14).sum()),
                tp14=x[x.qn < FIRST14].tp_pct.mean(), tp8=x[x.qn >= FIRST14].tp_pct.mean(),
                wo5=srt[:-5].mean() if len(y) > 5 else np.nan, worst5_removed_short=srt[5:].mean() if len(y) > 5 else np.nan,
                lag=100 * x.lag.mean())


def qdiff(df, mA, mB, ycol='three_day_pct'):
    y, q = df[ycol].values, df.qn.values
    a, _ = qmeans(y, q, mA); b, _ = qmeans(y, q, mB)
    d = a - b
    t22, n22 = tstat(d)
    t14, n14 = tstat(d[:FIRST14])
    t8, n8 = tstat(d[FIRST14:])
    return dict(qd=np.nanmean(d), t22=t22, nq22=n22, qd14=np.nanmean(d[:FIRST14]), t14=t14,
                qd8=np.nanmean(d[FIRST14:]), t8=t8, nq8=n8), d


def evalmask(df, expr):
    with np.errstate(invalid='ignore'):
        m = df.eval(expr)
    return m.fillna(False).astype(bool).values


def run_universe(G, tag, do_placebo=True, nperm=2000):
    G = G.reset_index(drop=True)
    y = G.three_day_pct.values
    q = G.qn.values.astype(int)
    # depth-adjusted outcome: minus the average of the trade's lag band (all 22 quarters)
    b = band_of(G.lag.values, DEPTH_ADJ_BANDS)
    bm = pd.Series(y).groupby(b).mean()
    G['adj'] = y - bm.reindex(b).values
    # within-quarter permutations (random same-size-per-quarter subsets)
    qidx = [np.where(q == k)[0] for k in QS]
    perms = np.empty((nperm, len(y)))
    for p in range(nperm):
        yy = y.copy()
        for ix in qidx:
            yy[ix] = y[rng.permutation(ix)]
        perms[p] = yy
    rows, qtabs = [], []
    for sid, fam, name, ea, eb, shortB, plok, note in SPLITS:
        mA, mB = evalmask(G, ea), evalmask(G, eb)
        A, B = side(G, mA), side(G, mB)
        D, d = qdiff(G, mA, mB)
        Dadj, _ = qdiff(G, mA, mB, 'adj')
        row = dict(id=sid, family=fam, name=name, A=ea, B=eb, short_B=shortB, note=note)
        for k, v in A.items():
            row['A_' + k] = v
        for k, v in B.items():
            row['B_' + k] = v
        row['A_net'] = A.get('avg', np.nan) - COST
        row['B_short_net'] = -B.get('avg', np.nan) - COST if B['n'] else np.nan
        row['pooled_diff'] = A.get('avg', np.nan) - B.get('avg', np.nan)
        row.update({'qdiff': D['qd'], 't22': D['t22'], 'nq': D['nq22'], 'qdiff14': D['qd14'], 't14': D['t14'],
                    'qdiff8': D['qd8'], 't8': D['t8']})
        row['adj_qdiff'] = Dadj['qd']; row['adj_t22'] = Dadj['t22']
        # random-subset p-values: chance a same-size-per-quarter random pick averages >= A (<= B)
        if A['n']:
            row['A_p_rand'] = float((perms[:, mA].mean(1) >= y[mA].mean()).mean())
        if B['n']:
            row['B_p_rand_short'] = float((perms[:, mB].mean(1) <= y[mB].mean()).mean())
        if do_placebo and plok:
            pA, pB = evalmask(PLF, ea), evalmask(PLF, eb)
            PA, PB = side(PLF, pA), side(PLF, pB)
            PD, _ = qdiff(PLF, pA, pB)
            row.update({'pl_A_n': PA['n'], 'pl_A_avg': PA.get('avg'), 'pl_A_tp': PA.get('tp'),
                        'pl_A_f14': PA.get('f14'), 'pl_A_l8': PA.get('l8'),
                        'pl_B_n': PB['n'], 'pl_B_avg': PB.get('avg'), 'pl_diff': PD['qd'], 'pl_t22': PD['t22']})
            row['results_minus_placebo_A'] = A.get('avg', np.nan) - PA.get('avg', np.nan)
            row['results_minus_placebo_diff'] = D['qd'] - PD['qd']
        rows.append(row)
        qa, na = qmeans(y, q, mA); qb, nb = qmeans(y, q, mB)
        qtabs.append(pd.DataFrame({'id': sid, 'qn': QS, 'A_n': na, 'A_avg': qa, 'B_n': nb, 'B_avg': qb, 'diff': qa - qb}))
    T = pd.DataFrame(rows)
    T.to_csv(f'{HERE}/splits_{tag}.csv', index=False)
    pd.concat(qtabs).to_csv(f'{HERE}/splits_{tag}_per_quarter.csv', index=False)
    return T, G


def battery_null(G, nsim=1000):
    """identical battery on outcomes shuffled within quarter and sign-flipped around the quarter mean"""
    y = G.three_day_pct.values
    q = G.qn.values.astype(int)
    qm = pd.Series(y).groupby(q).mean().reindex(QS).values
    qidx = [np.where(q == k)[0] for k in QS]
    MA = np.array([evalmask(G, s[3]) for s in SPLITS]); MB = np.array([evalmask(G, s[4]) for s in SPLITS])
    Q = np.zeros((22, len(y))); Q[q, np.arange(len(y))] = 1
    nA = MA.astype(float) @ Q.T; nB = MB.astype(float) @ Q.T

    def tvals(yy):
        with np.errstate(invalid='ignore', divide='ignore'):
            a = (MA * yy) @ Q.T / nA; b = (MB * yy) @ Q.T / nB
            d = a - b
            ok = np.isfinite(d)
            n = ok.sum(1)
            dm = np.where(ok, d, 0).sum(1) / n
            ss = np.where(ok, (d - dm[:, None]) ** 2, 0).sum(1) / (n - 1)
            t = dm / np.sqrt(ss / n)
            a14 = np.nansum(np.where(ok[:, :FIRST14], d[:, :FIRST14], 0), 1)
            Aavg = (MA * yy).sum(1) / MA.sum(1)
            Bavg = (MB * yy).sum(1) / MB.sum(1)
        return t, Aavg, Bavg
    t_real, A_real, B_real = tvals(y)
    out = []
    for s in range(nsim):
        yy = y.copy()
        for ix in qidx:
            yy[ix] = y[rng.permutation(ix)]
        sg = rng.choice([-1.0, 1.0], len(y))
        yy = qm[q] + sg * (yy - qm[q])
        t, Aa, Ba = tvals(yy)
        out.append(dict(max_abs_t=np.nanmax(np.abs(t)), n_abs_t_ge2=int((np.abs(t) >= 2).sum()),
                        n_t_ge2=int((t >= 2).sum()), best_A_avg=np.nanmax(Aa), worst_B_avg=np.nanmin(Ba)))
    N = pd.DataFrame(out)
    real = dict(max_abs_t=float(np.nanmax(np.abs(t_real))), n_abs_t_ge2=int((np.abs(t_real) >= 2).sum()),
                n_t_ge2=int((t_real >= 2).sum()), best_A_avg=float(np.nanmax(A_real)), worst_B_avg=float(np.nanmin(B_real)))
    summ = {'real': real, 'null_mean': N.mean().to_dict(), 'null_p95': N.quantile(0.95).to_dict(),
            'p_value': {k: float((N[k] >= real[k]).mean()) if k != 'worst_B_avg' else float((N[k] <= real[k]).mean())
                        for k in real}}
    return summ, N


def curve(G, Pdf, tag):
    rows = []
    for k, (a, b) in enumerate(LAG_BANDS):
        m = (G.lag >= a) & (G.lag < b)
        pm = (Pdf.lag >= a) & (Pdf.lag < b)
        s = side(G, m.values); ps = side(Pdf, pm.values)
        rows.append(dict(band=f'{-100*b:.1f}-{-100*a:.1f}%' if a > -1 else f'>{-100*b:.0f}%', n=s['n'], avg=s.get('avg'),
                         tp=s.get('tp'), up=s.get('up'), q_pos=f"{s.get('q_pos')}/{s.get('q_with')}", f14=s.get('f14'),
                         l8=s.get('l8'), placebo_n=ps['n'], placebo_avg=ps.get('avg'), placebo_tp=ps.get('tp'),
                         results_minus_placebo=s.get('avg', np.nan) - ps.get('avg', np.nan)))
    C = pd.DataFrame(rows)
    # per-quarter OLS slope of three_day (pct) on lag (pct points), inside the group
    sl, psl = [], []
    for k in QS:
        x = G[G.qn == k]
        if len(x) >= 5:
            sl.append(np.polyfit(100 * x.lag, x.three_day_pct, 1)[0])
        xp = Pdf[Pdf.qn == k]
        if len(xp) >= 5:
            psl.append(np.polyfit(100 * xp.lag, xp.three_day_pct, 1)[0])
    sl, psl = np.array(sl), np.array(psl)
    slope = dict(mean_slope_per_1pt_lag=sl.mean(), t=tstat(sl)[0], quarters=len(sl), share_negative=(sl < 0).mean(),
                 first14=sl[:FIRST14].mean(), last8=sl[FIRST14:].mean(),
                 placebo_mean_slope=psl.mean(), placebo_t=tstat(psl)[0])
    C.to_csv(f'{HERE}/depth_curve_{tag}.csv', index=False)
    return C, slope


if __name__ == '__main__':
    res = {}
    print('BASELINES (pct):  group fo 3-day %.3f tp %.3f n %d | placebo fo lag>5%% 3-day %.3f tp %.3f n %d' % (
        GF.three_day_pct.mean(), GF.tp_pct.mean(), len(GF), PLF.three_day_pct.mean(), PLF.tp_pct.mean(), len(PLF)))
    TF, GFa = run_universe(GF, 'fo')
    TA, _ = run_universe(GA, 'all', do_placebo=False, nperm=500)
    C, slope = curve(GF, PLF, 'fo')
    print('\nC01 depth curve (in_fo):'); print(C.round(2).to_string()); print('slope', {k: round(v, 3) for k, v in slope.items()})
    CA, slopeA = curve(GA, PL, 'all')
    print('\nC01 depth curve (all results; placebo = all stocks):'); print(CA.round(2).to_string())
    # D01 sector table (descriptive)
    D = GF.groupby('sector_index').agg(n=('three_day_pct', 'size'), avg=('three_day_pct', 'mean'), tp=('tp_pct', 'mean'),
                                       up=('three_day_pct', lambda s: 100 * (s > 0).mean()))
    D['f14'] = GF[GF.qn < FIRST14].groupby('sector_index').three_day_pct.mean()
    D['l8'] = GF[GF.qn >= FIRST14].groupby('sector_index').three_day_pct.mean()
    D.sort_values('avg').to_csv(f'{HERE}/sector_table_fo.csv')
    print('\nD01 sector table (descriptive only):'); print(D.sort_values('avg').round(2).to_string())
    cols = ['id', 'name', 'A_n', 'A_avg', 'A_tp', 'A_up', 'A_q_pos', 'A_q_with', 'A_f14', 'A_l8', 'A_lag', 'B_n', 'B_avg',
            'B_tp', 'B_q_neg', 'B_q_with', 'B_f14', 'B_l8', 'B_lag', 'qdiff', 't22', 't14', 't8', 'adj_qdiff', 'adj_t22',
            'A_p_rand', 'B_p_rand_short', 'pl_A_n', 'pl_A_avg', 'pl_B_avg', 'pl_diff', 'pl_t22']
    print('\nSPLITS, in_fo (percent):'); print(TF[cols].round(2).to_string())
    colsA = ['id', 'name', 'A_n', 'A_avg', 'A_tp', 'A_f14', 'A_l8', 'B_n', 'B_avg', 'B_f14', 'B_l8', 'qdiff', 't22', 't14', 't8']
    print('\nSPLITS, all results (secondary):'); print(TA[colsA].round(2).to_string())
    summ, N = battery_null(GFa)
    N.to_csv(f'{HERE}/battery_null_fo.csv', index=False)
    print('\nBATTERY LUCK (1,000 shuffled + sign-flipped outcome sets):'); print(json.dumps(summ, indent=1, default=float))
    json.dump({'slope_fo': slope, 'slope_all': slopeA, 'battery_null_fo': summ}, open(f'{HERE}/splits_summary.json', 'w'),
              indent=1, default=float)
