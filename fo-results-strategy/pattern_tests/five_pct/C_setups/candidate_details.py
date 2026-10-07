"""Full statistics for the final candidates + results-vs-placebo difference with standard errors."""
import numpy as np, pandas as pd, os
HERE = os.path.dirname(os.path.abspath(__file__))
F = pd.read_csv(os.path.join(HERE, 'events_feat.csv')); O = pd.read_csv(os.path.join(HERE, 'events_outcomes.csv'))
PL = pd.read_csv(os.path.join(HERE, 'placebo.csv.gz')); PL = PL[PL.in_fo == True].reset_index(drop=True)
COLS = ['vs_nifty_1w', 'vs_nifty_1m', 'r3d', 'vs_ma50']; ref = F[(F.in_fo == True) & (F.qn < 14)]
mu, sd = ref[COLS].mean(), ref[COLS].std()
sc = lambda d: (-(d[COLS] - mu) / sd).mean(axis=1, skipna=False).values
F['score'] = sc(F); PL['score'] = sc(PL)
fo = O.in_fo.values == True
cands = {
 'L14_drop3d (3-day drop <= -8%)': (F.r3d.values <= -0.08, PL.r3d.values <= -0.08, 'three_day'),
 'L02_lag1m_15 tp3 (1m vs Nifty < -15%)': (F.vs_nifty_1m.values < -0.15, PL.vs_nifty_1m.values < -0.15, 'tp3'),
 'L02_lag1m_15 3day': (F.vs_nifty_1m.values < -0.15, PL.vs_nifty_1m.values < -0.15, 'three_day'),
 'L01_lag1w_10 (1w vs Nifty < -10%)': (F.vs_nifty_1w.values < -0.10, PL.vs_nifty_1w.values < -0.10, 'three_day'),
 'composite score >= 2.0 (post-hoc)': (np.nan_to_num(F.score.values, nan=-9) >= 2.0, PL.score.values >= 2.0, 'three_day'),
 'composite score >= 1.5 (post-hoc)': (np.nan_to_num(F.score.values, nan=-9) >= 1.5, PL.score.values >= 1.5, 'three_day'),
 'L22_big_washout': (F.big_washout.values == 1, PL.big_washout.values == 1, 'three_day'),
}
base_e = O.three_day.values[fo].mean(); base_p = PL.three_day.mean()
print('base: results windows %.3f%%, placebo windows %.3f%%' % (100 * base_e, 100 * base_p))
for k, (me, mp, oc) in cands.items():
    m = me & fo; p = O[oc].values[m]; q = O.qn.values[m]
    pp = PL[oc].values[mp]
    # placebo se clustered by stock-day overlap is ignored; event se simple
    se_e = p.std(ddof=1) / np.sqrt(len(p))
    diff = p.mean() - pp.mean()
    qm = pd.Series(p).groupby(q).mean()
    dec = O.loc[m, ['ret_dm1', 'ret_rd', 'ret_dp1']].mean().mul(100).round(2).to_dict()
    print(f"{k:42s} n={len(p):3d} nq={qm.size:2d} avg={100*p.mean():5.2f} net={100*(p.mean()-0.0017):5.2f} avg_q={100*qm.mean():5.2f} "
          f"q6+={100*p[q>=6].mean():5.2f}(n={int((q>=6).sum())}) placebo={100*pp.mean():5.2f}(n={len(pp)}) results-extra={100*diff:5.2f} +/- {100*se_e:4.2f} "
          f"extra_vs_base={100*((p.mean()-base_e)-(pp.mean()-base_p)):5.2f}  days(D-1,RD,D+1)={dec}")
