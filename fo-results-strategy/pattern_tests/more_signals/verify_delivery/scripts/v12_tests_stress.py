"""v12 - own tests, stress and placebos for the top candidates, from v11 features (own code).
usage: python3 -P v12_tests_stress.py <scratchpad> <out_dir>
"""
import sys
import numpy as np, pandas as pd

SP, OUT = sys.argv[1], sys.argv[2]
ST = f'{SP}/more_signals/delivery'
DATA = f'{SP}/sector_lab/data'
log = open(f'{OUT}/v12_tests_stress.log', 'w')
def P(*a):
    s = ' '.join(str(x) for x in a); print(s); log.write(s + '\n'); log.flush()

f = pd.read_csv(f'{OUT}/v11_feat.csv')
M = np.load(f'{OUT}/v11_mats.npz'); DP60M, DQKM, DPM = M['DP60'], M['DQK'], M['DP']
ses = pd.read_csv(f'{DATA}/sessions.csv'); DAYS = ses.day.tolist(); NI = len(DAYS)
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0); SY = ret.columns.tolist(); SJ = {s: j for j, s in enumerate(SY)}
R = ret.to_numpy(float)
NC = pd.read_csv(f'{DATA}/index_close.csv', usecols=['day', 'Nifty 50']).set_index('day')['Nifty 50'].reindex(DAYS).to_numpy(float)
NR = np.r_[np.nan, NC[1:] / NC[:-1] - 1]
QL = {q: f'Results for {g.period.iloc[0]} ({g.quarter.iloc[0]})' for q, g in f.groupby('qn')}
rng = np.random.default_rng(20261012)

QN = f.qn.to_numpy(int); H1 = QN <= 13
YEAR = pd.to_datetime(f.cutoff).dt.year.to_numpy()
first_q = f.groupby('symbol').qn.min(); EARLY = (f.symbol.map(first_q) <= 1).to_numpy()
LAG = (f.in_fo_events == True).to_numpy() & (f.lag21 < -10).to_numpy() & (f.vol_ratio_5_60 >= 1.0).to_numpy()
Y3 = f.three_day.to_numpy(float)
qmean3 = f.groupby('qn').three_day.transform('mean').to_numpy()

def statA(m, sign=1, label=''):
    y = sign * Y3[m]; ex = y - sign * qmean3[m]
    o = np.argsort(-y)
    def wo(nb):
        keep = np.ones(len(y), bool); keep[o[:nb]] = False
        return y[keep].mean() - 0.17, ex[keep].mean()
    qq = pd.Series(y - 0.17).groupby(QN[m]).mean()
    s = (f'n {m.sum():4d} gross {y.mean():+.3f} net {y.mean() - .17:+.3f} ex {ex.mean():+.3f} q+ {int((qq > 0).sum())}/{len(qq)} '
         f'| h1 n {int((m & H1).sum())} net {(sign * Y3[m & H1]).mean() - .17:+.3f} ex {ex[H1[m]].mean():+.3f} '
         f'| h2 n {int((m & ~H1).sum())} net {(sign * Y3[m & ~H1]).mean() - .17:+.3f} ex {ex[~H1[m]].mean():+.3f} '
         f'| wo5 net {wo(5)[0]:+.3f} ex {wo(5)[1]:+.3f} | wo10 net {wo(10)[0]:+.3f} ex {wo(10)[1]:+.3f}')
    P(f'   {label:34s} {s}')
    return y, ex

def luckA(m, sign=1, B=20000):
    obs = (sign * Y3[m]).mean(); tot = np.zeros(B); n = m.sum()
    for q in np.unique(QN[m]):
        pool = sign * Y3[(QN == q) & np.isfinite(Y3)]; nq = int((m & (QN == q)).sum())   # NaN outcomes excluded
        idx = np.argsort(rng.random((B, len(pool))), axis=1)[:, :nq]
        tot += pool[idx].sum(1)
    return (1 + np.sum(tot / n >= obs - 1e-12)) / (1 + B)

def loqo(m, val):
    out = []
    for q in np.unique(QN[m]):
        keep = m & (QN != q); out.append((q, val[keep].mean()))
    out = sorted(out, key=lambda x: x[1]); return out[0], out[-1]

# ================================================================ TRADE A
P('=' * 100); P('TRADE A - own membership vs study trades_A.csv, own luck p, stress'); P('=' * 100)
ta = pd.read_csv(f'{ST}/trades_A.csv')
def member_check(name, m):
    mine = set(zip(f.symbol[m], f.qn[m])); th = set(zip(ta[ta.test == name].symbol, ta[ta.test == name].qn))
    P(f'{name}: mine {len(mine)} study {len(th)} both {len(mine & th)} only mine {sorted(mine - th)[:5]} only study {sorted(th - mine)[:5]}')
A10 = (f.rank_DP60 > 80).to_numpy() & np.isfinite(Y3)
A06 = (f.rank_DPL > 80).to_numpy() & np.isfinite(Y3)
RA1 = (f.in_fo_events == True).to_numpy() & (f.lag21 < -10).to_numpy() & (f.DQR >= 1.0).to_numpy() & np.isfinite(Y3)
member_check('A10', A10); member_check('A06', A06); member_check('RA1', RA1); member_check('LAGRULE', LAG)
rep = pd.read_csv(__import__('os').environ.get('REPO_ROOT', '.') + '/results/lag10_volume/trades.csv')
P(f'lag rule vs repo trades.csv: repo {len(rep)}, same set {set(zip(rep.symbol, rep.qn)) == set(zip(f.symbol[LAG], f.qn[LAG]))}, '
  f'repo three_day x100 mean {rep.three_day.mean() * 100:+.3f}')
P(f'all F&O results: n {np.isfinite(Y3).sum()} gross {np.nanmean(Y3):+.3f} net {np.nanmean(Y3) - .17:+.3f}')

for name, m in [('A10', A10), ('A06', A06), ('RA1', RA1), ('LAGRULE', LAG)]:
    P('-' * 100); P(name)
    y, ex = statA(m, label='base')
    lp = luckA(m); P(f'   own luck p (within-quarter random picks, 20,000): {lp:.4f}; x26 Holm-equivalent if smallest: {min(1, lp * 26):.3f}')
    exfull = Y3 - qmean3
    (qa, va), (qb, vb) = loqo(m, exfull)
    P(f'   LOQO excess: min {va:+.3f} (drop {QL[qa]}), max {vb:+.3f} (drop {QL[qb]})')
    (qa, va), (qb, vb) = loqo(m, Y3 - 0.17)
    P(f'   LOQO net:    min {va:+.3f} (drop {QL[qa]}), max {vb:+.3f} (drop {QL[qb]})')
    yr = pd.DataFrame({'y': YEAR[m], 'net': Y3[m] - .17, 'ex': exfull[m]}).groupby('y').agg(n=('net', 'size'), net=('net', 'mean'), ex=('ex', 'mean'))
    P('   by year: ' + ', '.join(f'{yy}: n {int(r.n)} net {r.net:+.2f} ex {r.ex:+.2f}' for yy, r in yr.iterrows()))
    statA(m & EARLY, label='survivorship: in F&O by qn 1')
    statA(m & ~EARLY, label='later joiners')
    statA(m & ~LAG, label='without lag-rule trades')
    P(f'   overlap with lag rule: {int((m & LAG).sum())}')
    o = np.argsort(-Y3[m]); top = f[m].iloc[o[:5]]
    P('   best 5: ' + '; '.join(f'{r.symbol} {QL[r.qn]} {r.three_day:+.1f}' for r in top.itertuples()))

P('-' * 100); P('A10 nearby cut-offs (rank_DP60 > c) and A06 (rank_DPL > c)')
for c in [60, 70, 75, 80, 85, 90]:
    statA((f.rank_DP60 > c).to_numpy() & np.isfinite(Y3), label=f'A10 rank_DP60 > {c}')
for c in [70, 75, 80, 85, 90]:
    statA((f.rank_DPL > c).to_numpy() & np.isfinite(Y3), label=f'A06 rank_DPL > {c}')
P('RA1 nearby cut-offs')
for lg in [-8, -10, -12]:
    for dq in [0.9, 1.0, 1.1, 1.2]:
        mm = (f.in_fo_events == True).to_numpy() & (f.lag21 < lg).to_numpy() & (f.DQR >= dq).to_numpy() & np.isfinite(Y3)
        statA(mm, label=f'lag<{lg} & DQR>={dq}')
P('RA1 decomposition vs the lag rule')
statA(RA1 & LAG, label='RA1 and lag rule (shared)')
statA(RA1 & ~LAG, label='RA1 only (new trades)')
statA(LAG & ~RA1, label='lag rule only (dropped)')
statA(RA1 | LAG, label='union')

# ---------------------------------------------------------------- own placebo A
P('-' * 100); P('OWN PLACEBO A (ordinary F&O stock-days)')
ev = pd.read_csv(f'{DATA}/events.csv', usecols=['symbol', 'i_rd', 'i_react'])
ev = ev[ev.symbol.isin(SJ)]
RES = np.zeros((NI + 30, len(SY)), bool)
for r in ev.itertuples():
    for x in (r.i_rd, r.i_react):
        if np.isfinite(x): RES[int(x), SJ[r.symbol]] = True
med_cut = f.groupby('qn').i_cut.median()
UQ = {q: np.array(sorted(g.symbol.map(SJ))) for q, g in f.groupby('qn')}
CUM3 = np.full((NI, len(SY)), np.nan)
for d in range(NI - 3):
    CUM3[d] = R[d + 1:d + 4].sum(0) * 100
    bad = np.isnan(R[d + 1:d + 4]).any(0); CUM3[d, bad] = np.nan
resc = np.cumsum(np.vstack([np.zeros((1, RES.shape[1])), RES]), 0)   # resc[t] = # result sessions < t
rows = []
start = int(f.i_cut.min()) - 70
for d in range(start, int(f.i_cut.max()) + 1):
    later = med_cut[med_cut >= d]
    if len(later) == 0: continue
    q = int(later.index[0]); jj = UQ[q]
    near = resc[d + 14, jj] - resc[d - 10, jj]
    v = DP60M[d - 1, jj]
    rk = pd.Series(v).rank().to_numpy() / np.isfinite(v).sum() * 100
    y = CUM3[d, jj]
    ok = (near == 0) & np.isfinite(y) & np.isfinite(v)
    for a, b, c_ in zip(jj[ok], rk[ok], y[ok]):
        rows.append((d, q, a, b, c_))
pl = pd.DataFrame(rows, columns=['d', 'q', 'j', 'rank', 'y'])
pl['ex_d'] = pl.y - pl.groupby('d').y.transform('mean')
pl['ex_q'] = pl.y - pl.groupby('q').y.transform('mean')
sig = pl[pl['rank'] > 80]
# results: date-matched to the equal-weight quarter universe over the same 3 days
EW = np.array([np.nanmean(CUM3[ic, UQ[q]]) for ic, q in zip(f.i_cut, f.qn)])
dm = Y3 - EW
allres_dm = np.nanmean(dm)
qw = pd.Series(QN[A10]).value_counts(normalize=True)
pl_q = sig.groupby('q').ex_q.mean(); pl_d = sig.groupby('q').ex_d.mean()
pl_ex_q = float((pl_q.reindex(qw.index) * qw).sum()); pl_ex_d = float((pl_d.reindex(qw.index) * qw).sum())
res_ex_q = (Y3[A10] - qmean3[A10]).mean(); res_ex_d = dm[A10].mean() - allres_dm
P(f'placebo stock-days {len(pl)}, signal days {len(sig)}; placebo signal excess quarter-matched {pl_ex_q:+.3f}, date-matched {pl_ex_d:+.3f}')
P(f'results A10 excess quarter-matched {res_ex_q:+.3f}, date-matched (vs EW universe, minus all results) {res_ex_d:+.3f}')
P(f'DiD quarter-matched {res_ex_q - pl_ex_q:+.3f}; DiD date-matched {res_ex_d - pl_ex_d:+.3f}')
# placebo p: draws of placebo signal days with the trades' per-quarter counts (date-matched excess)
B = 10000; tot = np.zeros(B); nq = pd.Series(QN[A10]).value_counts()
for q, c_ in nq.items():
    pool = sig.ex_d[sig.q == q].to_numpy()
    tot += pool[rng.integers(0, len(pool), (B, c_))].sum(1)
P(f'placebo p (date-matched; P(draw >= results A10 excess {res_ex_d:+.3f})): {(1 + np.sum(tot / nq.sum() >= res_ex_d)) / (1 + B):.4f}')
for h, lab in [(True, 'first 14'), (False, 'last 8')]:
    mm = A10 & (H1 == h); s2 = sig[(sig.q <= 13) == h]
    P(f'   {lab}: results A10 date-matched {dm[mm].mean() - np.nanmean(dm[H1 == h]):+.3f}; placebo signal date-matched {s2.ex_d.mean():+.3f}')
# same placebo for A06 (DPL rank) quickly
DPLM = np.load(f'{OUT}/v11_mats.npz')['DPL']

# ================================================================ TRADE B
P('=' * 100); P('TRADE B - W_DQK_HI / WR_DQK_HI (buy close k+1, 20 sessions, short Nifty, net 0.19)'); P('=' * 100)
tb = pd.read_csv(f'{ST}/trades_B.csv')
XN = f.XN.to_numpy(float); W = XN > 4; WR = W & (f.cut_rsi14 > 50).to_numpy()
T1 = f.t_k1.to_numpy(bool); Y1 = f.y_k1.to_numpy(float); Y0 = f.vsN_net_H20.to_numpy(float); T0 = f.tradable_B.to_numpy(bool)
DQK = f.DQK.to_numpy(float)
btr = pd.read_csv(f'{SP}/perf/B_post_results/trades.csv')
hab = set(zip(btr[btr.test == 'S1_DRIFT4_Q5'].symbol, btr[btr.test == 'S1_DRIFT4_Q5'].qn))
HAB = np.array([(s, q) in hab for s, q in zip(f.symbol, f.qn)])

def statB(m, parent, Y, label=''):
    pm = pd.Series(Y[parent]).groupby(QN[parent]).mean()
    g = Y[m] - pd.Series(QN[m]).map(pm).to_numpy()
    y = Y[m]; o = np.argsort(-y)
    def wo(nb):
        keep = np.ones(len(y), bool); keep[o[:nb]] = False
        return y[keep].mean(), g[keep].mean()
    qq = pd.Series(y).groupby(QN[m]).mean()
    P(f'   {label:40s} n {m.sum():3d} net {y.mean():+.3f} parent {Y[parent].mean():+.3f} gain {g.mean():+.3f} q+ {int((qq > 0).sum())}/{len(qq)} '
      f'| h1 n {int((m & H1).sum())} net {Y[m & H1].mean():+.3f} gain {g[H1[m]].mean():+.3f} | h2 n {int((m & ~H1).sum())} '
      f'net {Y[m & ~H1].mean():+.3f} gain {g[~H1[m]].mean():+.3f} | wo5 net {wo(5)[0]:+.3f} gain {wo(5)[1]:+.3f} '
      f'| wo10 net {wo(10)[0]:+.3f} gain {wo(10)[1]:+.3f}')
    return g

def luckB(m, parent, Y, B=20000):
    obs = Y[m].mean(); tot = np.zeros(B); n = m.sum()
    for q in np.unique(QN[m]):
        pool = Y[parent & (QN == q)]; nq = int((m & (QN == q)).sum())
        idx = np.argsort(rng.random((B, len(pool))), axis=1)[:, :nq]
        tot += pool[idx].sum(1)
    return (1 + np.sum(tot / n >= obs - 1e-12)) / (1 + B)

for pname, POOL in [('W', W), ('WR', WR)]:
    name = f'{pname}_DQK_HI'
    par = POOL & T1 & np.isfinite(DQK); m = par & (DQK >= 3)
    mine = set(zip(f.symbol[m], f.qn[m])); th = set(zip(tb[tb.test == name].symbol, tb[tb.test == name].qn))
    P('-' * 100)
    P(f'{name}: mine {len(mine)} study {len(th)} both {len(mine & th)}')
    g = statB(m, par, Y1, 'base (k+1)')
    P(f'   own luck p {luckB(m, par, Y1):.4f}')
    gfull = Y1 - pd.Series(QN).map(pd.Series(Y1[par]).groupby(QN[par]).mean()).to_numpy()
    (qa, va), (qb, vb) = loqo(m, gfull)
    P(f'   LOQO gain: min {va:+.3f} (drop {QL[qa]}), max {vb:+.3f} (drop {QL[qb]})')
    yr = pd.DataFrame({'y': YEAR[m], 'net': Y1[m], 'g': gfull[m]}).groupby('y').agg(n=('net', 'size'), net=('net', 'mean'), g=('g', 'mean'))
    P('   by year: ' + ', '.join(f'{yy}: n {int(r.n)} net {r.net:+.2f} gain {r.g:+.2f}' for yy, r in yr.iterrows()))
    for c_ in [2, 2.5, 3, 3.5, 4, 5]:
        statB(par & (DQK >= c_), par, Y1, f'DQK >= {c_}')
    statB(m & EARLY, par & EARLY, Y1, 'survivorship: in F&O by qn 1 (parent too)')
    statB(m & ~EARLY, par & ~EARLY, Y1, 'later joiners (parent too)')
    statB(m & ~HAB, par & ~HAB, Y1, 'not habitual drifters')
    P(f'   overlap: RSI>50 winners {int((m & WR).sum())}/{m.sum()}, habitual drifters {int((m & HAB).sum())}')
    # vs existing rule bought at close k
    par0 = POOL & T0
    P(f'   existing rule bought at k: n {par0.sum()} net {Y0[par0].mean():+.3f}; signal at k+1 net {Y1[m].mean():+.3f}; '
      f'the rest of the pool at k+1 net {Y1[par & ~m].mean():+.3f}')
    # XN control
    terc = pd.Series(XN).where(par).groupby(QN).transform(lambda x: pd.qcut(x.rank(method='first'), 3, labels=False))
    cell = pd.Series(QN * 10 + terc.fillna(-1).to_numpy())
    cm = pd.Series(Y1).where(par).groupby(cell).transform('mean').to_numpy()
    P(f'   gain within quarter x XN tercile: {np.nanmean(Y1[m] - cm[m]):+.3f}; Spearman(DQK, XN) in pool '
      f'{pd.Series(DQK[par]).corr(pd.Series(XN[par]), method="spearman"):+.3f}')
    o = np.argsort(-Y1[m]); top = f[m].iloc[o[:5]]
    P('   best 5: ' + '; '.join(f'{r.symbol} {QL[r.qn]} {r.y_k1:+.1f}' for r in top.itertuples()))

# ---------------------------------------------------------------- own placebo B (quiet winners)
P('-' * 100); P('OWN PLACEBO B: quiet winners (XN_k > 4, no result session of the stock in [k-10, k+22]), DQK on day k, buy k+1')
CP = np.nancumprod(np.nan_to_num(1 + R, nan=1.0), 0)
NCP = np.nancumprod(np.nan_to_num(1 + NR, nan=1.0))
rows = []
for kk in range(int(f.i_react.min()) - 40, NI - 23):
    later = med_cut[med_cut >= kk - 60]
    if len(later) == 0: continue
    q = int(later.index[0]); jj = UQ[q]
    xn = (R[kk, jj] - NR[kk]) * 100
    near = resc[kk + 23, jj] - resc[kk - 10, jj]
    ok = (xn > 4) & (near == 0) & np.isfinite(DQKM[kk, jj])
    for a in jj[ok]:
        nt = np.isnan(R[kk + 2:kk + 23, a]).sum()
        if nt > 2: continue
        y = (CP[kk + 21, a] / CP[kk + 1, a] - NCP[kk + 21] / NCP[kk + 1]) * 100 - 0.19
        rows.append((kk, DAYS[kk][:7], a, DQKM[kk, a], y))
qb = pd.DataFrame(rows, columns=['k', 'month', 'j', 'DQK', 'y'])
qb['gain'] = qb.y - qb.groupby('month').y.transform('mean')
P(f'quiet winners {len(qb)}, mean net {qb.y.mean():+.3f}; DQK >= 3: {int((qb.DQK >= 3).sum())}, net {qb.y[qb.DQK >= 3].mean():+.3f}, '
  f'gain vs same-month quiet winners {qb.gain[qb.DQK >= 3].mean():+.3f}')
for c_ in [2, 3, 4]:
    P(f'   quiet DQK >= {c_}: n {int((qb.DQK >= c_).sum())} gain {qb.gain[qb.DQK >= c_].mean():+.3f}')
par = W & T1 & np.isfinite(DQK); m = par & (DQK >= 3)
res_g = (Y1 - pd.Series(QN).map(pd.Series(Y1[par]).groupby(QN[par]).mean()).to_numpy())[m].mean()
pool = qb.gain[qb.DQK >= 3].to_numpy()
draws = pool[rng.integers(0, len(pool), (10000, m.sum()))].mean(1)
P(f'results W_DQK_HI gain {res_g:+.3f}; DiD {res_g - pool.mean():+.3f}; placebo p {(1 + np.sum(draws >= res_g)) / 10001:.4f}')
