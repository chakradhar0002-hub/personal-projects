"""
Independent re-implementation + adversarial checks of candidate
"BC5 early-season winner: fewer than 2 same-group peers reported yet" (family F3_sector_drift).

Written WITHOUT reading the F3 scripts.

Rule (as stated): at the reaction-day close, stock is F&O and (stock return - Nifty 50 return) on the
reaction day > +4%. Group = peer_group if present, else sector_index unless 'Nifty 500' (then no group).
Count F&O stocks in the same group, same qn, whose reaction day <= this reaction day (self excluded).
If count < 2 (or no group) -> buy at reaction-day close, sell at close 20 sessions later; Nifty hedge.

Pre-registered checks (verifier; counted, not used to pick a new rule):
  V1  base winners B (all), candidate C (self excluded), C' (self included ambiguity)    -> 3
  V2  complement (winners with >=2 peers reported)                                       -> 1
  V3  neighbouring peer thresholds K in {1,2,3,4}  (K=2 is the candidate)                -> 3 extra
  V4  horizons {5,10,20,40} for C                                                        -> 3 extra
  V5  winner threshold {3%,4%,5%} for C                                                  -> 2 extra
  V6  'early season' without any sector: fraction of ALL F&O results already reacted
      < q30 (absolute threshold 30% fixed in advance) for winners                       -> 1
  Robustness on C: drop top 5 trades, drop best quarter, leave-one-group-out,
  leave-one-quarter-out, cost x2, first14 vs last8, date clustering.
  Placebo: (a) random same-size subsets of B per quarter (5000), (b) random peer groups
  (shuffle group labels among F&O events within quarter, 2000), (c) the same 20-day hold
  on random non-results dates for the same stocks (2000).
Costs: 0.17% stock round trip, +0.02% Nifty futures hedge.
Missing returns: compounded over available days only (NaN = no trade; next return spans 2 sessions).
"""
import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
import sys; sys.path.append('/root/.local/lib/python3.11/site-packages')
import numpy as np, pandas as pd
D = os.environ.get('SECTOR_LAB', 'sector_lab') + '/data/'
OUT = os.environ.get('SECTOR_LAB', 'sector_lab') + '/verify_0_F3_sector_drift/'
rng = np.random.default_rng(12345)
C_STOCK, C_HEDGE = 0.0017, 0.0002

e = pd.read_csv(D + 'events.csv')
R = pd.read_csv(D + 'returns.csv', index_col=0)
IC = pd.read_csv(D + 'index_close.csv', index_col=0)
assert (pd.read_csv(D + 'sessions.csv').day.values == R.index.values).all()
assert (IC.index.values == R.index.values).all()
Rv = R.values; sym_ix = {s: k for k, s in enumerate(R.columns)}
nifty = IC['Nifty 50'].values

def cum(sym, i0, h):
    x = Rv[i0 + 1:i0 + 1 + h, sym_ix[sym]]
    x = x[~np.isnan(x)]
    return np.prod(1 + x) - 1 if len(x) else np.nan

def idx_ret(col, i0, h):
    a, b = IC[col].values[i0], IC[col].values[i0 + h]
    return b / a - 1 if (a > 0 and b > 0) else np.nan

e['fo'] = e.in_fo.fillna(False).astype(bool)
e['grp'] = e.peer_group.where(e.peer_group.notna(),
                              e.sector_index.where(e.sector_index != 'Nifty 500'))
e['r_react'] = [Rv[i, sym_ix[s]] for s, i in zip(e.symbol, e.i_react)]
e['n_react'] = nifty[e.i_react.values] / nifty[e.i_react.values - 1] - 1
e['ex_react'] = e.r_react - e.n_react

def peers_before(df, grpcol='grp'):
    out = np.full(len(df), -1)
    fo = df[df.fo]
    for (q, g), sub in fo.groupby(['qn', grpcol]):
        pass
    cnt = []
    key = {}
    for (q, g), sub in fo.groupby(['qn', grpcol]):
        key[(q, g)] = np.sort(sub.i_react.values)
    for k, (q, g, i) in enumerate(zip(df.qn, df[grpcol], df.i_react)):
        if pd.isna(g):
            out[k] = -1; continue
        arr = key.get((q, g), np.array([]))
        out[k] = np.searchsorted(arr, i, side='right')   # includes self if self is F&O
    return out

e['n_inc'] = peers_before(e)                     # includes self
e['n_exc'] = np.where(e.n_inc >= 0, e.n_inc - e.fo.astype(int), -1)

def fwd(df, h):
    df = df.copy()
    df['raw'] = [cum(s, i, h) for s, i in zip(df.symbol, df.i_react)]
    df['nif'] = [idx_ret('Nifty 50', i, h) for i in df.i_react]
    df['sec'] = [idx_ret(c if c in IC.columns else 'Nifty 500', i, h) for c, i in zip(df.sector_index, df.i_react)]
    df['net'] = df.raw - C_STOCK
    df['vsn'] = df.raw - df.nif - C_STOCK - C_HEDGE
    df['vss'] = df.raw - df.sec - C_STOCK
    return df

def summ(df, col='vsn', label=''):
    df = df.dropna(subset=[col])
    if len(df) == 0: return dict(label=label, n=0)
    q = df.groupby('qn')[col].mean() * 100
    t = q.mean() / (q.std(ddof=1) / np.sqrt(len(q))) if len(q) > 1 else np.nan
    dd = df.groupby('reaction_day')[col].mean() * 100   # date cluster
    td = dd.mean() / (dd.std(ddof=1) / np.sqrt(len(dd)))
    f14 = q[q.index <= 13]; l8 = q[q.index >= 14]
    return dict(label=label, n=len(df), avg=round(df[col].mean() * 100, 2), qavg=round(q.mean(), 2),
                t_q=round(t, 2), t_date=round(td, 2), nq=len(q), qpos=int((q > 0).sum()),
                f14=round(f14.mean(), 2), l8=round(l8.mean(), 2), win=round((df[col] > 0).mean() * 100, 1),
                med_q=round(q.median(), 2))

lines = []
def P(*a):
    s = ' '.join(str(x) for x in a); print(s); lines.append(s)

H = 20
base = e[e.fo & (e.ex_react > 0.04)].copy()
base = fwd(base, H)
C = base[base.n_exc < 2]
Cinc = base[base.n_inc < 2]
P('=== V1 reproduction (h=20) ===')
for lab, df in [('B all winners', base), ('C cand (self excl)', C), ("C' self incl", Cinc), ('V2 complement', base[base.n_exc >= 2])]:
    P(lab, summ(df, 'vsn', 'vsNifty'))
    P('   raw net avg %.2f  vsSector avg %.2f' % (df.net.mean() * 100, df.vss.mean() * 100))
P('C composition: no group', (C.n_exc == -1).sum(), ' group<2', (C.n_exc >= 0).sum())
P('C by qn trades:', C.groupby('qn').size().to_dict())
qC = C.groupby('qn').vsn.mean() * 100
P('C per-quarter vsn:', qC.round(2).to_dict())

# diff vs base, per quarter (paired)
qB = base.groupby('qn').vsn.mean() * 100
d = (qC - qB).dropna()
P('C - B per quarter: mean %.2f t %.2f ; first14 %.2f last8 %.2f' % (
    d.mean(), d.mean() / (d.std() / np.sqrt(len(d))), d[d.index <= 13].mean(), d[d.index >= 14].mean()))
# C vs complement
qN = base[base.n_exc >= 2].groupby('qn').vsn.mean() * 100
d2 = (qC - qN).dropna()
P('C - complement per quarter: mean %.2f t %.2f n=%d' % (d2.mean(), d2.mean() / (d2.std() / np.sqrt(len(d2))), len(d2)))

P('=== V3 neighbouring peer thresholds ===')
for K in [1, 2, 3, 4]:
    P('K<', K, summ(base[base.n_exc < K], 'vsn'))
P('group-only (exclude no-group) K<2', summ(base[(base.n_exc >= 0) & (base.n_exc < 2)], 'vsn'))
P('no-group only', summ(base[base.n_exc == -1], 'vsn'))

P('=== V4 horizons for C ===')
for h in [5, 10, 20, 40]:
    b = fwd(e[e.fo & (e.ex_react > 0.04) & (e.i_react + h < len(R))], h)
    P('h', h, 'C', summ(b[b.n_exc < 2], 'vsn'), '| B', summ(b, 'vsn'))

P('=== V5 winner thresholds for C ===')
for th in [0.03, 0.04, 0.05]:
    b = fwd(e[e.fo & (e.ex_react > th)], 20)
    P('th', th, 'C', summ(b[b.n_exc < 2], 'vsn'), '| B', summ(b, 'vsn'))

P('=== V6 early season (all F&O), no sector ===')
fo_all = e[e.fo]
frac = []
for k, r in base.iterrows():
    s = fo_all[fo_all.qn == r.qn]
    frac.append(((s.i_react <= r.i_react).sum() - 1) / len(s))
base['frac'] = frac
C['frac'] = base.loc[C.index, 'frac']
P('median frac in C %.2f, in B %.2f' % (C.frac.median(), base.frac.median()))
for cut in [0.2, 0.3]:
    P('frac<', cut, summ(base[base.frac < cut], 'vsn'), ' | frac>=', summ(base[base.frac >= cut], 'vsn'))
P('C restricted frac>=0.3 (late-season C):', summ(C[C.frac >= 0.3], 'vsn'))

P('=== Robustness on C ===')
s0 = summ(C, 'vsn')
Cs = C.sort_values('vsn', ascending=False)
P('drop top5:', summ(Cs.iloc[5:], 'vsn'))
bestq = qC.idxmax(); P('drop best quarter', bestq, summ(C[C.qn != bestq], 'vsn'))
P('drop top5 + best quarter:', summ(Cs.iloc[5:][Cs.iloc[5:].qn != bestq], 'vsn'))
Cc = C.copy(); Cc['vsn2'] = Cc.vsn - C_STOCK - C_HEDGE
P('cost x2:', summ(Cc, 'vsn2'))
Cc['vsn3'] = Cc.vsn - 3 * (C_STOCK + C_HEDGE)
P('cost x4:', summ(Cc, 'vsn3'))
P('raw net (no hedge):', summ(C, 'net'))
P('vs sector:', summ(C, 'vss'))
Cg = C.copy(); Cg['g2'] = Cg.grp.fillna('NONE')
P('leave one group out:')
for g in Cg.g2.unique():
    s = summ(Cg[Cg.g2 != g], 'vsn'); P('  -%-28s n=%3d(%2d out) qavg %.2f t %.2f f14 %.2f l8 %.2f' % (g, s['n'], (Cg.g2 == g).sum(), s['qavg'], s['t_q'], s['f14'], s['l8']))
Cg['sec2'] = Cg.sector_index
P('leave one sector_index out:')
for g in Cg.sec2.unique():
    s = summ(Cg[Cg.sec2 != g], 'vsn'); P('  -%-28s n=%3d(%2d out) qavg %.2f t %.2f' % (g, s['n'], (Cg.sec2 == g).sum(), s['qavg'], s['t_q']))
lo = []
for q in sorted(C.qn.unique()):
    lo.append(summ(C[C.qn != q], 'vsn')['t_q'])
P('leave-one-quarter-out t: min %.2f max %.2f' % (min(lo), max(lo)))
# overlap: how many trades per quarter share date windows
P('trades per quarter: mean %.1f min %d max %d' % (C.groupby('qn').size().mean(), C.groupby('qn').size().min(), C.groupby('qn').size().max()))
# max concurrent positions
occ = np.zeros(len(R))
for i in C.i_react: occ[i + 1:i + 21] += 1
P('max concurrent positions', int(occ.max()), ' mean when >0 %.1f' % occ[occ > 0].mean())
# same-day duplication
P('distinct reaction dates', C.reaction_day.nunique(), 'for', len(C), 'trades')
# survivorship: count trades in stocks that entered F&O late / were not in F&O
P('in_fo NaN rows', e.in_fo.isna().sum())

P('=== Placebos ===')
# (a) random same-count subsets of base per quarter
cnt = C.groupby('qn').size()
bq = {q: base[base.qn == q].vsn.values for q in cnt.index}
obs_q, obs_t = s0['qavg'], s0['t_q']
ma = mt = mp = 0; NR = 5000
for _ in range(NR):
    qs = []
    for q, n in cnt.items():
        qs.append(rng.choice(bq[q], n, replace=False).mean() * 100)
    qs = pd.Series(qs, index=cnt.index); t = qs.mean() / (qs.std(ddof=1) / np.sqrt(len(qs)))
    ma += qs.mean() >= obs_q; mt += t >= obs_t
    mp += (t >= 2.5) and qs[qs.index <= 13].mean() > 0 and qs[qs.index >= 14].mean() > 0
P('(a) random subsets of winners: avg>=obs %.3f  t>=obs %.3f  promising %.3f' % (ma / NR, mt / NR, mp / NR))

# (b) random peer groups: shuffle grp labels among F&O events within quarter, recompute peer count
NR = 1000; mb = mbt = 0; vals = []
ev = e.copy()
for _ in range(NR):
    g = ev.grp.values.copy()
    for q in ev.qn.unique():
        m = (ev.qn.values == q)
        g[m] = rng.permutation(g[m])
    ev['grp_r'] = g
    nn = peers_before(ev, 'grp_r')
    nn = np.where(nn >= 0, nn - ev.fo.astype(int).values, -1)
    sel = base[pd.Series(nn, index=ev.index).loc[base.index].values < 2]
    s = summ(sel, 'vsn'); vals.append(s['qavg'])
    mb += s['qavg'] >= obs_q; mbt += s['t_q'] >= obs_t
P('(b) random peer groups: avg>=obs %.3f t>=obs %.3f ; mean placebo qavg %.2f' % (mb / NR, mbt / NR, np.mean(vals)))

# (c) random non-results dates: same stocks, random date in the same quarter-window,
# at least 30 sessions away from any of the stock's reaction days; 20-day vs Nifty, no winner filter
react_by_sym = e.groupby('symbol').i_react.apply(np.array).to_dict()
def rand_trade(sym, i0):
    for _ in range(50):
        i = int(i0 + rng.integers(-60, 61))
        if i < 260 or i + 20 >= len(R): continue
        if np.min(np.abs(react_by_sym[sym] - i)) < 25: continue
        return i
    return None
mc = 0; NR = 300; vals = []
for _ in range(NR):
    rows = []
    for k, r in C.iterrows():
        i = rand_trade(r.symbol, r.i_react)
        if i is None: continue
        x = cum(r.symbol, i, 20) - (nifty[i + 20] / nifty[i] - 1) - C_STOCK - C_HEDGE
        rows.append((r.qn, x))
    df = pd.DataFrame(rows, columns=['qn', 'vsn'])
    q = df.groupby('qn').vsn.mean() * 100
    vals.append(q.mean()); mc += q.mean() >= obs_q
P('(c) same stocks random non-results dates: avg>=obs %.3f ; mean %.2f sd %.2f' % (mc / NR, np.mean(vals), np.std(vals)))

base.to_csv(OUT + 'base_winners_h20.csv', index=False)
C.to_csv(OUT + 'candidate_trades_h20.csv', index=False)
open(OUT + 'verify_output.txt', 'w').write('\n'.join(lines))
