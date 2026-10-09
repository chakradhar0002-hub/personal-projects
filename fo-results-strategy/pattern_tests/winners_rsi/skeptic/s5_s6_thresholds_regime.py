#!/usr/bin/env python3
"""S5 threshold sensitivity (RSI 40/45/50/55/60 x XN 3/4/5/6) and S6 market regime / benchmark / beta confounds.
All post hoc diagnostics; the main rule is not changed."""
import numpy as np
import pandas as pd

from common import HERE, Log, ols, sg

L = Log('s5_s6_thresholds_regime.log')
P = pd.read_csv(f'{HERE}/panel.csv.gz')

# ---------------------------------------------------------------- S5
L('S5. THRESHOLD GRID (20-session hedged net). dW = per-trade gap to all winners (same XN cut) of the same quarter; '
  'gapQ = within-quarter RSI>cut minus RSI<=cut among those winners (quarter FE, quarter clusters)')
rows = []
for xn in (3, 4, 5, 6):
    Wd = P[P.XN_mine > xn].copy()
    qm = Wd.groupby('qn').vsN_net.mean()
    for rc in (40, 45, 50, 55, 60):
        Wd['HIf'] = (Wd.cut_rsi14 > rc).astype(float)
        hi = Wd[Wd.HIf == 1]
        lo = Wd[Wd.HIf == 0]
        b, se, t, G = ols(Wd.vsN_net, Wd[['HIf']], cl=Wd.qn, fe=Wd.qn)
        rows.append(dict(XN_gt=xn, RSI_gt=rc, n=len(hi), mean=hi.vsN_net.mean(), median=hi.vsN_net.median(),
                         n_lo=len(lo), mean_lo=lo.vsN_net.mean(), mean_W=Wd.vsN_net.mean(),
                         dW=(hi.vsN_net - hi.qn.map(qm)).mean(), gapQ=b[0], t_gapQ=t[0],
                         wins10=np.clip(hi.vsN_net, -10, 10).mean()))
G5 = pd.DataFrame(rows)
G5.to_csv(f'{HERE}/s5_grid.csv', index=False, float_format='%.4f')
L(G5.round(2).to_string(index=False))
for c in ('mean', 'dW', 'gapQ'):
    L(f'\n{c} grid (rows XN>, cols RSI>):')
    L(G5.pivot(index='XN_gt', columns='RSI_gt', values=c).round(2).to_string())
L('\ncontinuous RSI among winners (quarter FE): slope per 10 RSI points, and among non-winners for comparison')
for xn in (3, 4, 5, 6):
    Wd = P[P.XN_mine > xn].copy()
    Wd['r10'] = (Wd.cut_rsi14 - 50) / 10
    b, se, t, G = ols(Wd.vsN_net, Wd[['r10']], cl=Wd.qn, fe=Wd.qn)
    b2, se2, t2, _ = ols(np.clip(Wd.vsN_net, -10, 10), Wd[['r10']], cl=Wd.qn, fe=Wd.qn)
    L(f'   XN>{xn}: n {len(Wd)}, slope {b[0]:+.2f} per 10 pts (t {t[0]:.2f}); winsorised +/-10 {b2[0]:+.2f} (t {t2[0]:.2f})')
Nw = P[P.XN_mine <= 4].copy()
Nw['r10'] = (Nw.cut_rsi14 - 50) / 10
b, se, t, G = ols(Nw.vsN_net, Nw[['r10']], cl=Nw.qn, fe=Nw.qn)
L(f'   non-winners XN<=4: n {len(Nw)}, slope {b[0]:+.2f} per 10 pts (t {t[0]:.2f})')
# RSI bands within quarter among winners (deviation from the quarter's winner mean)
W = P[P.W].copy()
W['dev'] = W.vsN_net - W.groupby('qn').vsN_net.transform('mean')
W['band'] = pd.cut(W.cut_rsi14, [0, 30, 40, 50, 60, 70, 100])
B = W.groupby('band', observed=True).agg(n=('dev', 'size'), mean=('vsN_net', 'mean'), dev_vs_quarter=('dev', 'mean'),
                                         wins10=('vsN_net', lambda s: np.clip(s, -10, 10).mean()))
L('\nwinners by cutoff-RSI band: mean, and mean deviation from the same quarter\'s winners:')
L(B.round(2).to_string())

# ---------------------------------------------------------------- S6
L('\n' + '=' * 100)
L('S6. MARKET REGIME, BENCHMARK AND BETA CONFOUNDS')
W['HIf'] = (W.cut_rsi14 > 50).astype(float)
L(f"Nifty 20-session return to the cutoff: main-rule trades mean {W.loc[W.HIf == 1, 'nifty_pre20'].mean():+.2f}%, "
  f"RSI<=50 winners {W.loc[W.HIf == 0, 'nifty_pre20'].mean():+.2f}%, all results {P.nifty_pre20.mean():+.2f}%")
L(f"Nifty 20-session return DURING the hold: main {W.loc[W.HIf == 1, 'nifty_H20'].mean():+.2f}%, RSI<=50 winners "
  f"{W.loc[W.HIf == 0, 'nifty_H20'].mean():+.2f}%, all results {P.nifty_H20.mean():+.2f}%")
cuts = np.nanpercentile(P.nifty_pre20, [33.33, 66.67])
W['reg'] = np.digitize(W.nifty_pre20, cuts)
P['reg'] = np.digitize(P.nifty_pre20, cuts)
labs = {0: 'Nifty pre-20 weak', 1: 'Nifty pre-20 middle', 2: 'Nifty pre-20 strong'}
rows = []
for r in (0, 1, 2):
    g = W[W.reg == r]
    hi, lo = g[g.HIf == 1], g[g.HIf == 0]
    rows.append(dict(regime=labs[r], share_HI=g.HIf.mean() * 100, n_hi=len(hi), mean_hi=hi.vsN_net.mean(),
                     n_lo=len(lo), mean_lo=lo.vsN_net.mean(), gap=hi.vsN_net.mean() - lo.vsN_net.mean(),
                     all_results_mean=P.loc[P.reg == r, 'vsN_net'].mean()))
RG = pd.DataFrame(rows)
L(f'\nwithin regime (terciles of the Nifty 20-session return to the cutoff over all results: {cuts.round(2)}):')
L(RG.round(2).to_string(index=False))
RG.to_csv(f'{HERE}/s6_regime.csv', index=False, float_format='%.4f')
# forward-regime split (Nifty during the hold) - descriptive only (not knowable at entry)
fc = np.nanpercentile(P.nifty_H20, [33.33, 66.67])
W['freg'] = np.digitize(W.nifty_H20, fc)
rows = []
for r in (0, 1, 2):
    g = W[W.freg == r]
    hi, lo = g[g.HIf == 1], g[g.HIf == 0]
    rows.append(dict(nifty_during_hold=['down', 'flat', 'up'][r], n_hi=len(hi), mean_hi=hi.vsN_net.mean(),
                     n_lo=len(lo), mean_lo=lo.vsN_net.mean(), gap=hi.vsN_net.mean() - lo.vsN_net.mean()))
L('\nby Nifty move DURING the hold (terciles; descriptive, not tradable):')
L(pd.DataFrame(rows).round(2).to_string(index=False))
# regressions among winners: HI with regime controls, quarter FE
W['npre10'] = W.nifty_pre20 / 10
W['nfwd10'] = W.nifty_H20 / 10
W['regS'] = (W.reg == 2).astype(float)
W['regW'] = (W.reg == 0).astype(float)
L('\nwinners, quarter FE, quarter clusters:')
for X in (['HIf'], ['HIf', 'npre10'], ['HIf', 'regS', 'regW'], ['HIf', 'nfwd10']):
    b, se, t, G = ols(W.vsN_net, W[X], cl=W.qn, fe=W.qn)
    L('   ' + ' + '.join(f'{x} {bb:+.2f} (t {tt:.2f})' for x, bb, tt in zip(X, b, t)))
W['HIxN'] = W.HIf * W.npre10
b, se, t, G = ols(W.vsN_net, W[['HIf', 'npre10', 'HIxN']], cl=W.qn, fe=W.qn)
L(f'   HI x Nifty-pre20 interaction {b[2]:+.2f} per 10 pts (t {t[2]:.2f})')

L('\nbenchmarks and beta (20-session net; all minus 0.19 costs). Pre-cutoff 250-session beta to Nifty:')
L(f"   beta: main {W.loc[W.HIf == 1, 'beta250'].mean():.2f}, RSI<=50 winners {W.loc[W.HIf == 0, 'beta250'].mean():.2f}, "
  f"all results {P.beta250.mean():.2f}")
rows = []
for col, lab in [('vsN_net', 'vs Nifty 50 (main measure)'), ('abn_beta_net', 'beta-adjusted vs Nifty 50'),
                 ('vsN500_net', 'vs Nifty 500'), ('vsMID150_net', 'vs Nifty Midcap 150'),
                 ('vsN100EW_net', 'vs Nifty100 Equal Weight'), ('vsSEC_net', 'vs own sector index'),
                 ('raw_net', 'unhedged')]:
    Wd = W[W[col].notna()].copy()
    hi, lo = Wd[Wd.HIf == 1], Wd[Wd.HIf == 0]
    qm = Wd.groupby('qn')[col].mean()
    b, se, t, G = ols(Wd[col], Wd[['HIf']], cl=Wd.qn, fe=Wd.qn)
    rows.append(dict(measure=lab, main=hi[col].mean(), all_W=Wd[col].mean(), W_lo=lo[col].mean(),
                     all_results=P[col].mean(), main_minus_all_results=hi[col].mean() - P[col].mean(),
                     dW=(hi[col] - hi.qn.map(qm)).mean(), gapQ=b[0], t_gapQ=t[0],
                     main_q_pos=int((hi.groupby('qn')[col].mean() > 0).sum())))
BM = pd.DataFrame(rows)
L(BM.round(2).to_string(index=False))
BM.to_csv(f'{HERE}/s6_benchmarks.csv', index=False, float_format='%.4f')
# F&O universe drift vs Nifty on quiet days (what any long F&O stock earned vs Nifty, same period)
Q = pd.read_csv(f'{HERE}/quiet_panel.csv.gz', usecols=['vsN_net', 'vsN500_net', 'vsMID150_net', 'year'])
L(f"\nquiet-day F&O stock-days (no results): mean vs Nifty {Q.vsN_net.mean():+.2f}, vs N500 {Q.vsN500_net.mean():+.2f}, "
  f"vs Midcap150 {Q.vsMID150_net.mean():+.2f}  <- the universe drift the Nifty hedge leaves in")
L('   by year vs Nifty: ' + ', '.join(f'{y} {v:+.2f}' for y, v in Q.groupby('year').vsN_net.mean().items()))
