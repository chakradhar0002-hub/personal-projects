#!/usr/bin/env python3
"""Check every 'build error' claimed by the SKEPTIC and TRADABILITY agents, with my own code.
Uses truth_universe.csv from reconcile.py (full-precision recomputation). Everything here is a diagnostic; the main
rule is not changed. Writes claims.log / claims_*.csv into this folder only."""
import os
import sqlite3
from math import comb

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.environ.get('LAB_ROOT', os.path.abspath(os.path.join(HERE, '..', '..')))  # scratch data folder
DATA = f'{SP}/sector_lab/data'
TAFA = f'{SP}/tafa/C_post_results'
COST, C_STK = 0.19, 0.17
LOG = open(f'{HERE}/claims.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')
    LOG.flush()


def sg(x, d=2):
    return 'n/a' if x is None or not np.isfinite(x) else f'{x:+.{d}f}'


def ols(y, X, cl, fe):
    """OLS, fixed effects absorbed by within-demeaning, CR1 cluster-robust SE (G/(G-1) * (n-1)/(n-k))."""
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    X = X[:, None] if X.ndim == 1 else X
    fe = np.asarray(fe)
    y = y - pd.Series(y).groupby(fe).transform('mean').to_numpy()
    X = X - pd.DataFrame(X).groupby(fe).transform('mean').to_numpy()
    XtX = np.linalg.pinv(X.T @ X)
    b = XtX @ X.T @ y
    e = y - X @ b
    codes, u = pd.factorize(np.asarray(cl))
    G = len(u)
    S = np.zeros((G, X.shape[1]))
    np.add.at(S, codes, X * e[:, None])
    n, k = X.shape
    V = XtX @ (S.T @ S) @ XtX * G / (G - 1) * (n - 1) / (n - k)
    se = np.sqrt(np.diag(V))
    return b, b / se


ses = pd.read_csv(f'{DATA}/sessions.csv')
DAYS = ses.day.to_numpy()
NS = len(ses)
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
R = ret.to_numpy(float)
SYM = {s: j for j, s in enumerate(ret.columns)}
IX = pd.read_csv(f'{DATA}/index_close.csv', index_col=0)
NC = IX['Nifty 50'].to_numpy(float)
NR = np.r_[np.nan, NC[1:] / NC[:-1] - 1]
PX = np.cumprod(1 + np.nan_to_num(R), axis=0)
U = pd.read_csv(f'{HERE}/truth_universe.csv')
K = U.i_react.to_numpy(int)
J = U.symbol.map(SYM).to_numpy(int)
U['month'] = U.reaction_day.str[:7]
W = U[U.W].copy()
qW = W.groupby('qn').vsN_net.mean()
MAIN = U[U.MAIN]
rows = []


def claim(agent, claim_txt, theirs, mine, verdict):
    rows.append(dict(agent=agent, claim=claim_txt, their_number=theirs, my_number=mine, verdict=verdict))
    P(f'[{agent}] {claim_txt}\n    theirs: {theirs}\n    mine:   {mine}\n    verdict: {verdict}')


# ------------------------------------------------------------------ S-a pooled vs within-quarter
pooled_dw = MAIN.vsN_net.mean() - W.vsN_net.mean()
dW = (MAIN.vsN_net - MAIN.qn.map(qW)).mean()
b, t = ols(W.vsN_net, W.HI.astype(float), W.qn, W.qn)
pooled_gap = MAIN.vsN_net.mean() - U.loc[U.W_LO, 'vsN_net'].mean()
pqg = MAIN.groupby('qn').vsN_net.mean() - qW
beat = int((pqg > 0).sum())
sign_p = sum(comb(22, i) for i in range(beat, 23)) / 2 ** 22
nif20 = (NC[W.i_cut.to_numpy(int)] / NC[W.i_cut.to_numpy(int) - 20] - 1) * 100
W['nif_pre20'] = nif20
terc = pd.qcut(W.nif_pre20, 3, labels=['weak', 'mid', 'strong'])
share = W.groupby(terc, observed=True).HI.mean() * 100
claim('skeptic', 'Pooled gaps overstate the edge: pre-registered same-quarter d_W is +0.63 not pooled +0.97; '
      'within-quarter RSI gap +1.95 (t 2.08) not pooled +2.38; RSI>50 share 36% weak vs 79% strong Nifty tercile; '
      'beat all winners 15/22 (sign p 0.067); median quarter gap +0.58',
      '+0.63 / +0.97; +1.95 (t 2.08) / +2.38; 36% / 79%; 15/22 p 0.067; +0.58',
      f'{sg(dW)} / {sg(pooled_dw)}; {sg(b[0])} (t {t[0]:.2f}) / {sg(pooled_gap)}; '
      f"{share['weak']:.0f}% / {share['strong']:.0f}% (mid {share['mid']:.0f}%); {beat}/22 p {sign_p:.3f}; "
      f'{sg(pqg.median())}',
      'REAL (presentation, not arithmetic). Numbers reproduce. The build headline and robustness text lead with '
      'pooled gaps (+0.97 vs all winners, +2.38 vs RSI<=50 winners) that include between-quarter composition; the '
      'pre-registered statistic is d_W +0.63 and the within-quarter RSI split is +1.95. The build did print +0.63 '
      '(variants table) and +1.95 (momentum table) but not as the headline comparison.')

# ------------------------------------------------------------------ S-b momentum comparison
mm = pd.read_csv(f'{SP}/winners_rsi/build/momentum_models.csv')
m6 = mm[mm.term == 'MOM_HI'].iloc[0]
med = W.groupby('qn').stock_21d_pct.transform('median') if 'stock_21d_pct' in W else None
eta = pd.read_csv(f'{SP}/ta/build/events_ta.csv', usecols=['symbol', 'qn', 'stock_21d_pct', 'close_vs_sma200_pct',
                                                           'lag_pct'])
W = W.merge(eta, on=['symbol', 'qn'], how='left', validate='1:1')
W['MOM_HI'] = (W.stock_21d_pct > W.groupby('qn').stock_21d_pct.transform('median')).astype(float)
bm, tm = ols(W.vsN_net, W.MOM_HI, W.qn, W.qn)
pooled_mom = W.loc[W.MOM_HI == 1, 'vsN_net'].mean() - W.loc[W.MOM_HI == 0, 'vsN_net'].mean()
claim('skeptic', "Build compares a pooled momentum split (+0.90) with a pooled fixed-threshold RSI split (+2.38); "
      'like for like within quarter it is +0.97 vs +1.95',
      '+0.90 vs +2.38 -> +0.97 vs +1.95',
      f'pooled momentum split {sg(pooled_mom)}; within-quarter momentum dummy {sg(bm[0])} (t {tm[0]:.2f}; build M6 '
      f'{sg(m6.coef)}); within-quarter RSI {sg(b[0])} (t {t[0]:.2f})',
      'REAL but minor. RSI still beats a plain momentum split within quarter (about 2x rather than 2.6x), and with '
      'both in the model neither is cleanly identified (build M3: RSI t 1.43).')

# ------------------------------------------------------------------ S-c not winner specific
U['HIf'] = U.HI.astype(float)
U['Wf'] = U.W.astype(float)
U['HIxW'] = U.HIf * U.Wf
NW_ = U[~U.W]
bn, tn = ols(NW_.vsN_net, NW_.HIf, NW_.qn, NW_.qn)
LS = U[U.XN < -4]
bl, tl = ols(LS.vsN_net, LS.HIf, LS.qn, LS.qn)
bi, ti = ols(U.vsN_net, U[['HIf', 'Wf', 'HIxW']], U.qn, U.qn)
claim('skeptic', "Build's placebo line '(b) the split appears only around results, it is not generic momentum' "
      'implies a winner-specific effect; within quarter RSI>50 also lifts non-winners (+0.68) and losers XN<-4 '
      '(+1.39); HI x W only +1.06 (t 1.10)',
      'non-winners +0.68 (t 1.70); losers +1.39 (t 1.70); HI x W +1.06 (t 1.10)',
      f'non-winners {sg(bn[0])} (t {tn[0]:.2f}); losers XN<-4 n {len(LS)} {sg(bl[0])} (t {tl[0]:.2f}); '
      f'HI x W {sg(bi[2])} (t {ti[2]:.2f}), HI {sg(bi[0])} (t {ti[0]:.2f})',
      'PARTLY REAL. Numbers reproduce. But the build did not claim winner specificity: its own placebo text and '
      'caveat say RSI>50 also helps non-winners on results days (+0.82 vs -0.39) and that the effect is "a '
      'results-period effect and not specific to winners". The quiet-day line is the pre-registered interpretation '
      'rule and is correct as stated. The fair correction is emphasis: the rule = plain winner drift + a general '
      'pre-results-strength effect around results; the winner-specific increment is not significant.')

# ------------------------------------------------------------------ S-d sector adjustment
ev = pd.read_csv(f'{DATA}/events.csv', usecols=['symbol', 'qn', 'sector_index'])
U = U.merge(ev, on=['symbol', 'qn'], how='left', validate='1:1', suffixes=('', '_ev'))
sec_col = 'sector_index' if 'sector_index' in U else 'sector_index_ev'
sec_ret, sec_pre = np.full(len(U), np.nan), np.full(len(U), np.nan)
for s_, g in U.groupby(sec_col):
    Bx = IX[s_].to_numpy(float)
    ix_ = U.index.get_indexer(g.index)
    k_, c_ = g.i_react.to_numpy(int), g.i_cut.to_numpy(int)
    sec_ret[ix_] = (Bx[k_ + 20] / Bx[k_] - 1) * 100
    sec_pre[ix_] = (Bx[c_] / Bx[c_ - 20] - 1) * 100
U['vsSEC_net'] = U.stock - sec_ret - COST
U['sec_pre20'] = sec_pre
W2 = U[U.W]
qWs = W2.groupby('qn').vsSEC_net.mean()
M2 = U[U.MAIN]
dWs = (M2.vsSEC_net - M2.qn.map(qWs)).mean()
bs, ts = ols(W2.vsSEC_net, W2.HIf, W2.qn, W2.qn)
claim('skeptic', 'Missing sector adjustment: vs own sector index d_W falls to +0.35 and the within-quarter RSI gap to '
      '+1.06 (t 1.32); RSI>50 winners sector index +3.74% vs -1.96% in the 20 sessions to the cutoff',
      '+0.35; +1.06 (t 1.32); +3.74 vs -1.96; main vs own sector +1.90',
      f'd_W vs sector {sg(dWs)}; within-quarter gap vs sector {sg(bs[0])} (t {ts[0]:.2f}); sector pre-cutoff '
      f"{sg(W2.loc[W2.HI, 'sec_pre20'].mean())} vs {sg(W2.loc[~W2.HI, 'sec_pre20'].mean())}; main vs own sector "
      f'{sg(M2.vsSEC_net.mean())}; missing sector values {int(np.isnan(sec_ret).sum())}',
      'REAL omission (diagnostic, not an arithmetic error). About half of the RSI increment is sector momentum.')


# ------------------------------------------------------------------ S-e calendar time
def ct(df):
    s, c = np.zeros(NS), np.zeros(NS)
    for k_, j_ in zip(df.i_react.to_numpy(int), df.symbol.map(SYM).to_numpy(int)):
        d_ = np.arange(k_ + 1, k_ + 21)
        s[d_] += np.nan_to_num(R[d_, j_]) - NR[d_]
        c[d_] += 1
    with np.errstate(invalid='ignore'):
        return pd.Series(np.where(c > 0, s / c, np.nan))


def nw(x, lag=20):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    e = x - x.mean()
    n = len(x)
    v = e @ e / n
    for l_ in range(1, lag + 1):
        v += 2 * (1 - l_ / (lag + 1)) * (e[l_:] @ e[:-l_]) / n
    return x.mean(), x.mean() / np.sqrt(v / n), n


hiS, loS, wS = ct(U[U.MAIN]), ct(U[U.W_LO]), ct(U[U.W])
m_, t_, n_ = nw(hiS)
dl = (hiS - loS).dropna()
m2_, t2_, n2_ = nw(dl)
dw_ = (hiS - wS).dropna()
m3_, t3_, n3_ = nw(dw_)
yrs = dl.groupby(pd.Series(DAYS[dl.index]).str[:4].to_numpy()).mean() * 2000
claim('skeptic', 'Missing cross-correlation check: calendar-time (daily equal-weight, gross, NW lag 20) main +2.85 per '
      '20 sessions (t 3.32); main minus RSI<=50 winners +1.70 (t 1.39); main minus all winners +1.07 (t 2.70)',
      '+2.85 (3.32); +1.70 (1.39); +1.07 (2.70); long-short negative 2021, 2024, 2026',
      f'{m_ * 2000:+.2f} (t {t_:.2f}, {n_} days); {m2_ * 2000:+.2f} (t {t2_:.2f}, {n2_} overlap days); '
      f'{m3_ * 2000:+.2f} (t {t3_:.2f}); long-short by year ' + ', '.join(f'{y} {v:+.2f}' for y, v in yrs.items()),
      'REAL omission. Once overlapping, co-moving trades are treated as one daily portfolio, the RSI>50 minus '
      'RSI<=50 long-short is not significant; main minus all winners still is.')

# ------------------------------------------------------------------ S-f benchmarks + quiet drift
bench = {}
for nm in ['Nifty 500', 'Nifty100 Equal Weight', 'Nifty Midcap 150']:
    Bx = IX[nm].to_numpy(float)
    k_ = M2.i_react.to_numpy(int)
    bench[nm] = (M2.stock - (Bx[k_ + 20] / Bx[k_] - 1) * 100 - COST).mean()
qd = pd.read_csv(f'{TAFA}/quiet_days.csv.gz', usecols=['symbol', 'i'])
qk, qj = qd.i.to_numpy(int), qd.symbol.map(SYM).to_numpy(int)
okq = qk + 21 <= NS - 1
qk, qj = qk[okq], qj[okq]
qv = ((PX[qk + 20, qj] / PX[qk, qj] - 1) - (NC[qk + 20] / NC[qk] - 1)) * 100 - COST
claim('skeptic', 'Level depends on the hedge: +2.05 vs Nifty 500, +1.81 vs Nifty100 EW, +1.22 vs Midcap 150; quiet '
      'F&O stock-days beat Nifty by +0.56 per 20 sessions after costs',
      '+2.05 / +1.81 / +1.22; +0.56',
      ' / '.join(f'{k} {sg(v)}' for k, v in bench.items()) + f'; quiet days n {len(qv):,} mean {sg(qv.mean())}',
      'REAL (context, not a build error). About 0.5 of the Nifty-hedged level is F&O-universe drift in this period.')

# ------------------------------------------------------------------ execution: next-open entry
con = sqlite3.connect(f'file:{SP}/report/nse_prices.db?mode=ro', uri=True)
ixo = pd.read_sql("SELECT day, open, close FROM idx WHERE name='Nifty 50'", con).set_index('day').reindex(DAYS)
con.close()
assert np.allclose(ixo.close.to_numpy(float), NC)
NO = ixo.open.to_numpy(float)
ao = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'open', 'close'])
ao = ao[ao.symbol.isin(SYM)]
DIX = {d: i for i, d in enumerate(DAYS)}
ao = ao[ao.day.isin(DIX)]
OC = np.full((NS, len(SYM)), np.nan)
OC[ao.day.map(DIX).to_numpy(int), ao.symbol.map(SYM).to_numpy(int)] = (ao.close / ao.open).to_numpy(float)
K = U.i_react.to_numpy(int)
J = U.symbol.map(SYM).to_numpy(int)
oc1 = OC[K + 1, J]
U['E1a_g'] = ((oc1 * PX[K + 21, J] / PX[K + 1, J] - 1) - (NC[K + 21] / NO[K + 1] - 1)) * 100
U['E1b_g'] = ((PX[K + 21, J] / PX[K + 1, J] - 1) - (NC[K + 21] / NC[K + 1] - 1)) * 100
U['SK_g'] = ((oc1 * PX[K + 20, J] / PX[K + 1, J] - 1) - (NC[K + 20] / NC[K] - 1)) * 100   # skeptic version
U['E0_g'] = U.vsN_net + COST
nmiss = int(np.isnan(oc1[U.MAIN.to_numpy()]).sum())
tab = {}
for g, m in [('MAIN', U.MAIN), ('W', U.W), ('W_LO', U.W_LO)]:
    x = U[m]
    tab[g] = {e: (x[f'{e}_g'] - COST).mean() for e in ('E0', 'E1a', 'E1b', 'SK')}
qWa = U[U.W].groupby('qn').E1a_g.mean()
dW_e1a = (U.loc[U.MAIN, 'E1a_g'] - U.loc[U.MAIN, 'qn'].map(qWa)).mean()
qpos_e1a = int((U[U.MAIN].groupby('qn').E1a_g.mean() - COST > 0).sum())
qpos_e1a_40 = int((U[U.MAIN].groupby('qn').E1a_g.mean() - 0.40 > 0).sum())
fh = U.qn <= 13
claim('tradability + skeptic', 'Same-bar entry not tested: next-open entry (open k+1 -> close k+21, Nifty open k+1) '
      'gives main +2.25, all winners +1.24, RSI<=50 -0.22; next close +2.15 / +1.19 / -0.19; skeptic variant (open '
      'k+1 -> close k+20, Nifty close k) +2.07; d_W unchanged',
      'E1a +2.25 / +1.24 / -0.22; E1b +2.15 / +1.19 / -0.19; skeptic +2.07; dW +0.64',
      f"E1a {sg(tab['MAIN']['E1a'])} / {sg(tab['W']['E1a'])} / {sg(tab['W_LO']['E1a'])}; E1b {sg(tab['MAIN']['E1b'])} / "
      f"{sg(tab['W']['E1b'])} / {sg(tab['W_LO']['E1b'])}; skeptic variant {sg(tab['MAIN']['SK'])}; d_W at E1a "
      f"{sg(dW_e1a)}; E1a quarters positive {qpos_e1a}/22 (at 0.40 cost {qpos_e1a_40}/22); E1a first14 "
      f"{sg((U.loc[U.MAIN & fh, 'E1a_g'] - COST).mean())} last8 {sg((U.loc[U.MAIN & ~fh, 'E1a_g'] - COST).mean())}; "
      f'main trades without an open on k+1: {nmiss}',
      'REAL omission (the build listed it only as a caveat). Cost is modest: about -0.17 at the next open.')
claim('tradability', 'Cost assumption too low: 0.17 stock round trip; cash-delivery STT alone is 0.1% + 0.1%; '
      'realistic all-in about 0.35-0.40; main at next open and 0.40 nets +2.04, all winners +1.03',
      'E1a/0.40 main +2.04, all winners +1.03',
      f"E0/0.40 main {sg(tab['MAIN']['E0'] + COST - 0.40)}; E1a/0.40 main {sg(tab['MAIN']['E1a'] + COST - 0.40)}, all "
      f"winners {sg(tab['W']['E1a'] + COST - 0.40)}, RSI<=50 {sg(tab['W_LO']['E1a'] + COST - 0.40)}",
      'REAL as an assumption issue (not an arithmetic error): 0.17 is a futures-like cost, the pre-registered value. '
      'STT on delivery equity is 0.1% on each side, so a cash-delivery round trip is >= 0.2% before stamp duty, fees '
      'and spread. Level falls about 0.2; the RSI increment is unaffected (same cost on both sides).')

# ------------------------------------------------------------------ late filings
evf = pd.read_csv(f'{DATA}/events.csv', usecols=['symbol', 'qn', 'results_time', 'timing', 'i_rd', 'i_react'])
assert {'results_time', 'i_rd', 'timing'} <= set(U.columns)
mins = pd.to_datetime(U.results_time, format='%H:%M', errors='coerce')
mins = mins.dt.hour * 60 + mins.dt.minute
late = (U.timing == 'During market') & (mins >= 900)
L_ = U[late]
k_, j_ = L_.i_react.to_numpy(int), L_.symbol.map(SYM).to_numpy(int)
mk = np.nanmedian(np.abs(R[k_, j_] - NR[k_]) * 100)
mk1 = np.nanmedian(np.abs(R[k_ + 1, j_] - NR[k_ + 1]) * 100)
claim('tradability', 'Results filed 15:00-15:29 are tagged During market with k = results day; reaction is really on '
      'k+1 (median |move vs Nifty| 2.50 on k+1 vs 1.30 on k); 135 F&O results, 0 main-rule trades, 1 RSI<=50 winner',
      '135; 0 main; 1 W_LO; 2.50 vs 1.30',
      f'{int(late.sum())} results; k == results session for all: {bool((L_.i_react == L_.i_rd).all())}; main '
      f'{int((late & U.MAIN).sum())}; W_LO {int((late & U.W_LO).sum())}; median |move| k {mk:.2f} vs k+1 {mk1:.2f}',
      'REAL, but upstream (events.csv reaction-day definition), not a build error; it does not touch the 232 trades.')

# ------------------------------------------------------------------ in_fo gaps / blanks / survivorship
ev_all = pd.read_csv(f'{DATA}/events.csv', usecols=['symbol', 'qn', 'in_fo'])
fa = pd.read_csv(f'{SP}/fa/build/fa_panel.csv', usecols=['symbol', 'qn', 'in_fo'])
q0 = fa[fa.qn == 0]
seq = fa.sort_values('qn').groupby('symbol')
oldnames = sorted(s for s, g in seq if len(g) > 2 and (not g.in_fo.iloc[0]) and g.in_fo.iloc[1] and g.in_fo.iloc[2]
                  and g.qn.iloc[0] == 0)
claim('tradability', 'in_fo flag gaps: qn 0 flags only 98 of 189 results; 21 long-standing F&O names False at qn 0 '
      'and True from qn 1',
      '98 of 189; 21 names',
      f'fa_panel qn 0: in_fo True {int(q0.in_fo.sum())} of {len(q0)}; events.csv qn 0 True '
      f"{int((ev_all[ev_all.qn == 0].in_fo == True).sum())}; names False at qn0 then True at qn1-2: {len(oldnames)} "
      f"({', '.join(oldnames[:12])}...)",
      'REAL upstream universe noise (not look-ahead, not a build error). It thins the first quarter.')
v_ = U[(U.symbol == 'VEDL') & (U.qn == 20)]
vk = int(v_.i_react.iloc[0]) if len(v_) else None
claim('tradability / rebuild', 'events.csv in_fo blank for RELIANCE qn 9 and VEDL qn 20 (demergers); fa_panel True; '
      'neither is a main-rule trade',
      'both blank, neither main',
      f"both in the 3,280: {bool(((U.symbol == 'RELIANCE') & (U.qn == 9)).any() and len(v_))}; main? "
      f"{bool(U.loc[((U.symbol == 'RELIANCE') & (U.qn == 9)) | ((U.symbol == 'VEDL') & (U.qn == 20)), 'MAIN'].any())}; "
      f"XN RELIANCE {U.loc[(U.symbol == 'RELIANCE') & (U.qn == 9), 'XN'].iloc[0]:+.2f}, VEDL "
      f"{v_.XN.iloc[0]:+.2f}; VEDL return blank on k+1: {bool(np.isnan(R[vk + 1, SYM['VEDL']]))}",
      'REAL, harmless (baseline only).')
absent = [s for s in ['HDFC', 'MINDTREE', 'ZEEL', 'PVR', 'IBULHSGFIN', 'ACC', 'BATAINDIA'] if s not in SYM]
lastp = {s: DAYS[np.flatnonzero(np.isfinite(R[:, j]))[-1]] for s, j in SYM.items() if np.isfinite(R[:, j]).any()}
early_end = sum(v < DAYS[-1] for v in lastp.values())
first_fo = fa[fa.in_fo == True].groupby('symbol').qn.min()
U['old'] = U.symbol.map(first_fo) <= 1
co = {c: U[U.MAIN & (U.old == c)].vsN_net for c in (True, False)}
coW = {c: U[U.W & (U.old == c)].vsN_net for c in (True, False)}
x23 = U.year != 2023
oldx = U.MAIN & U.old & x23
claim('tradability', 'Survivorship: universe is today\'s list (212 symbols); >= 47 F&O names of 2021 absent (HDFC, '
      'MINDTREE, ...); no price history ends early; main +1.79 (n 172) on names in F&O by qn 1 vs +4.22 (n 60) on '
      'later joiners; old names ex-2023 at E1a/0.40 +0.62 vs all winners +0.01. Build "mentions but does not quantify"',
      '+1.79 (172) vs +4.22 (60)',
      f'symbols in returns.csv {len(SYM)}; absent from the sample list: {absent}; symbols whose prices end before '
      f'{DAYS[-1]}: {early_end}; main old {sg(co[True].mean())} (n {len(co[True])}) vs later {sg(co[False].mean())} '
      f'(n {len(co[False])}); all winners old {sg(coW[True].mean())} vs later {sg(coW[False].mean())}; old ex-2023 '
      f"E1a/0.40 main {sg((U.loc[oldx, 'E1a_g'] - 0.40).mean())} (n {int(oldx.sum())}) vs all winners "
      f"{sg((U.loc[U.W & U.old & x23, 'E1a_g'] - 0.40).mean())}",
      'REAL and the most important level issue. Correction to the tradability note: the build does NOT mention '
      'survivorship at all (no mention in study.py, run.log or its caveats).')

# ------------------------------------------------------------------ brief labels / luck p
nwhi = U[~U.W & U.HI].vsN_net.mean()
claim('skeptic', "Task brief says non-winners with RSI>50 earn +0.79; should be +0.815 (build's +0.82 is right)",
      '+0.815', f'{nwhi:+.3f} (n {int((~U.W & U.HI).sum())}); RSI<=50 {U[~U.W & ~U.HI].vsN_net.mean():+.3f}',
      'REAL (brief typo, not a build error).')
rt = pd.read_csv(f'{TAFA}/results_tests.csv')
wr = rt[(rt.test == 'W_RSI_HI') & (rt.H == 20)].iloc[0]
claim('reconcile', 'Build headline cites luck p 0.0094 (its own redraw); the pre-registered run gave 0.0105',
      '0.0094', f'pre-registered p_W_ELIG {wr.p_W_ELIG:.4f}, p_W_ALL {wr.p_W_ALL:.4f}; Holm117 {wr.p_holm117:.2f}; WY '
      f'{wr.p_westfall_young:.4f}; z_perm {wr.z_perm:.2f}',
      'Both are valid Monte Carlo draws (se ~0.0007); quote the pre-registered 0.0105 as the official number.')
# multiple testing family
nA = len(pd.read_csv(f'{SP}/ta/A_standalone/signals_summary.csv'))
sigs = pd.read_csv(f'{SP}/ta/A_standalone/signals_summary.csv', usecols=['signal'])
claim('skeptic', 'Testing family understated even at 117: ta/A_standalone (44 signals incl. RSI thresholds), ta/B, '
      'tafa A/B also looked at RSI-type splits',
      '44 signals', f"ta/A_standalone signals {nA}; RSI-type: {', '.join(s for s in sigs.signal if 'RSI' in s.upper())}",
      'REAL (qualitative). The 117-test Holm / Westfall-Young numbers are a lower bound on the search; it does not '
      'change any number, it makes the WATCH weaker.')

pd.DataFrame(rows).to_csv(f'{HERE}/claims_check.csv', index=False)
# per-quarter next-open (diagnostic) for the verdict
pqe = U[U.MAIN].groupby('qn').agg(n=('E1a_g', 'size'), E0=('vsN_net', 'mean'), E1a_019=('E1a_g', lambda s: (s - COST).mean()),
                                  E1a_040=('E1a_g', lambda s: (s - 0.40).mean()))
pqe.to_csv(f'{HERE}/claims_per_quarter_next_open.csv', float_format='%.4f')
P('\nper-quarter MAIN at next-open entry (diagnostic):')
P(pqe.round(2).to_string())
U[['symbol', 'qn', 'XN', 'rsi14', 'W', 'HI', 'MAIN', 'vsN_net', 'E1a_g', 'E1b_g', 'SK_g', 'vsSEC_net', 'old']].to_csv(
    f'{HERE}/claims_panel.csv', index=False, float_format='%.6f')
