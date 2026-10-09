#!/usr/bin/env python3
"""S3 (time dependence) and S4 (outliers), own code.

Edge measures, all on the 20-session Nifty-hedged net (percent):
  mean      main-rule per-trade mean (pooled)
  dW        per-trade mean of (main trade - mean of ALL winners of the same quarter)   [pre-registered d_W]
  gapQ      within-quarter RSI>50 minus RSI<=50 among winners (OLS with quarter FE)
"""
import numpy as np
import pandas as pd

from common import HERE, Log, ols, sg, winsor

L = Log('s3_time_outliers.log')
rng = np.random.default_rng(7)
P = pd.read_csv(f'{HERE}/panel.csv.gz')
W = P[P.W].copy()
W['HIf'] = (W.cut_rsi14 > 50).astype(float)
QL = P.groupby('qn')[['period', 'quarter']].first()


def measures(Wd, col='vsN_net'):
    hi = Wd[Wd.HIf == 1]
    lo = Wd[Wd.HIf == 0]
    qm = Wd.groupby('qn')[col].mean()
    dW = (hi[col] - hi.qn.map(qm)).mean() if len(hi) else np.nan
    if hi.qn.nunique() >= 2 and len(lo):
        b, se, t, G = ols(Wd[col], Wd[['HIf']], cl=Wd.qn, fe=Wd.qn)
        gq, tq = b[0], t[0]
    else:
        gq, tq = np.nan, np.nan
    return dict(n_main=len(hi), mean_main=hi[col].mean(), n_W=len(Wd), mean_W=Wd[col].mean(),
                mean_lo=lo[col].mean(), dW=dW, gapQ=gq, t_gapQ=tq)


L('S3. TIME DEPENDENCE')
full = measures(W)
L('full sample: ' + ', '.join(f'{k} {v:+.3f}' if isinstance(v, float) else f'{k} {v}' for k, v in full.items()))
# by year
rows = []
for y, g in W.groupby('year'):
    rows.append(dict(year=y, **measures(g)))
Y = pd.DataFrame(rows)
L('\nby calendar year of the reaction day:')
L(Y.round(3).to_string(index=False))
Y.to_csv(f'{HERE}/s3_by_year.csv', index=False, float_format='%.4f')
L(f"years with dW > 0: {(Y.dW > 0).sum()}/{len(Y)}; years with main mean > 0: {(Y.mean_main > 0).sum()}/{len(Y)}; "
  f"years with main > all winners (pooled): {(Y.mean_main > Y.mean_W).sum()}/{len(Y)}")
# halves
rows = []
for lab, m in [('2021-22 (calendar)', W.year <= 2022), ('2023+ (calendar)', W.year >= 2023),
               ('first 14 quarters qn 0-13', W.qn <= 13), ('last 8 quarters qn 14-21', W.qn >= 14),
               ('qn 0-10', W.qn <= 10), ('qn 11-21', W.qn >= 11),
               ('without 2023', W.year != 2023), ('without qn 10 (Jul-Sep 2023)', W.qn != 10),
               ('without qn 8-10 (best 3 quarters)', ~W.qn.isin([8, 9, 10])),
               ('only 2024-2026', W.year >= 2024)]:
    rows.append(dict(sample=lab, **measures(W[m])))
H = pd.DataFrame(rows)
L('\nsplits:')
L(H.round(3).to_string(index=False))
H.to_csv(f'{HERE}/s3_splits.csv', index=False, float_format='%.4f')
# per quarter
rows = []
for q, g in W.groupby('qn'):
    m = measures(g)
    rows.append(dict(qn=q, results_for=QL.loc[q, 'period'], quarter=QL.loc[q, 'quarter'], n_main=m['n_main'],
                     mean_main=m['mean_main'], n_W=m['n_W'], mean_W=m['mean_W'], mean_lo=m['mean_lo'],
                     main_minus_W=m['mean_main'] - m['mean_W']))
PQ = pd.DataFrame(rows)
PQ.to_csv(f'{HERE}/s3_per_quarter.csv', index=False, float_format='%.4f')
L(f"\nquarters main > all winners {int((PQ.main_minus_W > 0).sum())}/22; median per-quarter gap "
  f"{PQ.main_minus_W.median():+.2f}; mean {PQ.main_minus_W.mean():+.2f}; sign-test p (one-sided) "
  f"{sum(__import__('math').comb(22, k) for k in range(int((PQ.main_minus_W > 0).sum()), 23)) / 2 ** 22:.3f}")
# leave one quarter out
rows = []
for q in sorted(W.qn.unique()):
    m = measures(W[W.qn != q])
    rows.append(dict(drop_qn=q, quarter=QL.loc[q, 'quarter'], **m))
LQ = pd.DataFrame(rows)
LQ.to_csv(f'{HERE}/s3_loqo.csv', index=False, float_format='%.4f')
L('\nleave-one-quarter-out: range of mean_main [%.2f, %.2f], dW [%.2f, %.2f], gapQ [%.2f, %.2f], t_gapQ [%.2f, %.2f]'
  % (LQ.mean_main.min(), LQ.mean_main.max(), LQ.dW.min(), LQ.dW.max(), LQ.gapQ.min(), LQ.gapQ.max(),
     LQ.t_gapQ.min(), LQ.t_gapQ.max()))
L(LQ.sort_values('dW').head(4)[['drop_qn', 'quarter', 'mean_main', 'dW', 'gapQ', 't_gapQ']].round(3).to_string(index=False))
rows = []
for y in sorted(W.year.unique()):
    rows.append(dict(drop_year=y, **measures(W[W.year != y])))
LY = pd.DataFrame(rows)
LY.to_csv(f'{HERE}/s3_loyo.csv', index=False, float_format='%.4f')
L('\nleave-one-year-out:')
L(LY.round(3).to_string(index=False))

# quarter-cluster bootstrap
NB = 5000
qs_all = np.array(sorted(W.qn.unique()))
G = {q: W[W.qn == q] for q in qs_all}
bm, bd, bg = [], [], []
for b in range(NB):
    pick = rng.choice(qs_all, len(qs_all), replace=True)
    parts = []
    for r_, q in enumerate(pick):
        g = G[q].copy()
        g['qn'] = r_                         # each draw is its own quarter
        parts.append(g)
    Wd = pd.concat(parts)
    hi = Wd[Wd.HIf == 1]
    qm = Wd.groupby('qn').vsN_net.mean()
    bm.append(hi.vsN_net.mean())
    bd.append((hi.vsN_net - hi.qn.map(qm)).mean())
    y = Wd.vsN_net - Wd.groupby('qn').vsN_net.transform('mean')
    x = Wd.HIf - Wd.groupby('qn').HIf.transform('mean')
    bg.append((x * y).sum() / (x * x).sum())
for lab, a in [('main mean', bm), ('dW', bd), ('gapQ', bg)]:
    a = np.array(a)
    L(f"quarter bootstrap {lab}: 90% [{np.percentile(a, 5):+.2f}, {np.percentile(a, 95):+.2f}], 95% "
      f"[{np.percentile(a, 2.5):+.2f}, {np.percentile(a, 97.5):+.2f}], P(<=0) {(a <= 0).mean():.3f}")

# ---------------------------------------------------------------- S4 outliers
L('\nS4. OUTLIERS (20-session hedged net, percent)')
groups = {'MAIN W&RSI>50': W[W.HIf == 1].vsN_net.to_numpy(), 'all winners': W.vsN_net.to_numpy(),
          'W&RSI<=50': W[W.HIf == 0].vsN_net.to_numpy(), 'all F&O results': P.vsN_net.to_numpy()}


def robust(v):
    s = np.sort(v)
    n = len(s)
    k2 = int(round(0.02 * n))
    k5 = int(round(0.05 * n))
    return dict(n=n, mean=v.mean(), median=np.median(v), wo_best5=s[:-5].mean(), wo_best10=s[:-10].mean(),
                wo_top2pct=s[:n - k2].mean(), trim5_both=s[k5:n - k5].mean(), wins10=winsor(v, -10, 10).mean(),
                wins5=winsor(v, -5, 5).mean(), up_pct=(v > 0).mean() * 100)


R4 = pd.DataFrame({k: robust(v) for k, v in groups.items()}).T
L(R4.round(3).to_string())
R4.to_csv(f'{HERE}/s4_outliers.csv', float_format='%.4f')
L('\nmain minus all winners under each measure: ' + ', '.join(
    f"{c} {R4.loc['MAIN W&RSI>50', c] - R4.loc['all winners', c]:+.2f}" for c in R4.columns if c not in ('n',)))
# within-quarter measures on winsorised / ranked outcomes
for lab, col in [('winsor +/-10', 'w10'), ('winsor +/-5', 'w5'), ('within-quarter rank (0-1)', 'rk')]:
    W['w10'] = winsor(W.vsN_net, -10, 10)
    W['w5'] = winsor(W.vsN_net, -5, 5)
    W['rk'] = W.groupby('qn').vsN_net.rank(pct=True)
    m = measures(W, col)
    L(f"{lab:26s}: main {m['mean_main']:+.3f}, all W {m['mean_W']:+.3f}, dW {m['dW']:+.3f}, gapQ {m['gapQ']:+.3f} "
      f"(t {m['t_gapQ']:.2f})")
# permutation p for the rank statistic (within quarter shuffle of the RSI label)
W['rk'] = W.groupby('qn').vsN_net.rank(pct=True)
act = W.loc[W.HIf == 1, 'rk'].mean()
lab = W.HIf.to_numpy()
qn = W.qn.to_numpy()
rk = W.rk.to_numpy()
idx = [np.flatnonzero(qn == q) for q in np.unique(qn)]
cnt = 0
for b in range(20000):
    lp = lab.copy()
    for ix in idx:
        lp[ix] = lab[ix][rng.permutation(len(ix))]
    cnt += rk[lp == 1].mean() >= act - 1e-12
L(f"mean within-quarter percentile rank of main-rule trades among the quarter's winners: {act:.3f} "
  f"(0.5 + tie-adjusted = no edge); permutation p {(1 + cnt) / 20001:.4f}")
# drop best-k trades from main, recompute dW (same-quarter gap) with the trades also removed from the winners pool
for k in (5, 10, 20):
    top = W[W.HIf == 1].vsN_net.nlargest(k).index
    Wd = W.drop(top)
    m = measures(Wd)
    L(f"drop main-rule best {k:2d} trades (also from the winners pool): main {m['mean_main']:+.3f}, all W "
      f"{m['mean_W']:+.3f}, dW {m['dW']:+.3f}, gapQ {m['gapQ']:+.3f} (t {m['t_gapQ']:.2f})")
for k in (5, 10, 20):
    top = W.vsN_net.nlargest(k).index
    Wd = W.drop(top)
    m = measures(Wd)
    L(f"drop the best {k:2d} trades of ALL winners (fair, any RSI): main {m['mean_main']:+.3f}, all W "
      f"{m['mean_W']:+.3f}, dW {m['dW']:+.3f}, gapQ {m['gapQ']:+.3f} (t {m['t_gapQ']:.2f}); "
      f"{int((W.loc[top, 'HIf'] == 1).sum())} of them RSI>50")
