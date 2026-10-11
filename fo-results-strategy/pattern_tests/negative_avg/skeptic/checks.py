#!/usr/bin/env python3
"""Skeptic step 4: data sanity of the extreme trades, sector concentration, symmetric trimming, quarter-level t,
conditional luck test (random picks among downtrend results of the same quarter), pre-F&O results check."""
import numpy as np, pandas as pd
SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f'{SP}/negative_avg/skeptic'
days = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv').day.tolist()
P = pd.read_csv(f'{OUT}/skeptic_panel.csv')
P['sh'] = -(P.st20 - P.nf20) - 0.19
ok = P.st20.notna()
ev = pd.read_csv(f'{SP}/sector_lab/data/events.csv', usecols=['symbol', 'qn', 'industry', 'sector_index', 'in_fo',
                                                              'i_react', 'i_rd', 'timing'])
P = P.merge(ev[['symbol', 'qn', 'industry', 'sector_index']], on=['symbol', 'qn'], how='left')
lines = []
def say(s=''):
    lines.append(s); print(s)
def wo(x, n):
    x = np.sort(np.asarray(x))[::-1]; return x[n:].mean()
rng = np.random.default_rng(7)

# 1. data sanity: corporate actions / raw price jumps inside the windows of the 6 most extreme holdout trades
px = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'close', 'raw_close', 'price_factor'])
px['i'] = px.day.map({d: i for i, d in enumerate(days)})
H = P[ok & (P['sample'] == 'holdout') & P.C12.astype(bool)]
ext = pd.concat([H.nlargest(5, 'sh'), H.nsmallest(3, 'sh')])
say('=== extreme C12 holdout trades: raw close at entry/exit, price-factor changes in the window')
for r in ext.itertuples():
    g = px[(px.symbol == r.symbol) & (px.i >= r.i_react) & (px.i <= r.i_react + 20)].sort_values('i')
    pf = g.price_factor.nunique()
    say(f'  {r.symbol:10s} q{r.qn} entry {days[r.i_react]} XN {r.XN:+.1f} short {r.sh:+.1f}: raw {g.raw_close.iloc[0]:.1f} -> '
        f'{g.raw_close.iloc[-1]:.1f} ({(g.raw_close.iloc[-1] / g.raw_close.iloc[0] - 1) * 100:+.1f}%), adj '
        f'{(g.close.iloc[-1] / g.close.iloc[0] - 1) * 100:+.1f}%, my stock {r.st20:+.1f}%, price factors {pf}, '
        f'{r.industry}')

# 2. sector concentration of the holdout profit
say('\n=== C12 holdout by industry (n, mean hedged short, sum)')
s = H.groupby('industry').sh.agg(['size', 'mean', 'sum']).sort_values('sum', ascending=False)
for i, r in s.iterrows():
    if r['size'] >= 3 or abs(r['sum']) > 8:
        say(f'  {i:40s} {int(r["size"]):3d} {r["mean"]:+6.2f} {r["sum"]:+7.1f}')
it = H.industry == 'Computers - Software'
say(f'  IT/software trades {it.sum()}, sum {H.sh[it].sum():+.1f}; without IT: n {(~it).sum()} mean {H.sh[~it].mean():+.2f}')
D = P[ok & (P['sample'] == 'discovery') & P.C12.astype(bool)]

# 3. symmetric trimming, quarter-level t of (C12 - base), q14 / sell-off exclusions
for nm, d, smp in [('C12 discovery', D, 'discovery'), ('C12 holdout', H, 'holdout')]:
    x = np.sort(d.sh.values)
    base = P[ok & (P['sample'] == smp)]
    bq = base.groupby('qn').sh.mean()
    qd = d.groupby('qn').sh.mean() - bq.reindex(d.groupby('qn').sh.mean().index)
    qa = d.groupby('qn').sh.mean()
    say(f'\n=== {nm}: drop 5 best AND 5 worst {x[5:-5].mean():+.2f}; drop 10/10 {x[10:-10].mean():+.2f}; '
        f'quarter-level mean short {qa.mean():+.2f} t {qa.mean() / qa.std(ddof=1) * np.sqrt(len(qa)):.2f} ({len(qa)} q); '
        f'margin vs base per quarter {qd.mean():+.2f} t {qd.mean() / qd.std(ddof=1) * np.sqrt(len(qd)):.2f}')
say(f'  holdout without q14: {H[H.qn != 14].sh.mean():+.2f}; without q14 & q15 (Oct 2024 - Mar 2025 sell-off): '
    f'{H[~H.qn.isin([14, 15])].sh.mean():+.2f} (n {(~H.qn.isin([14, 15])).sum()}); q14+q15 only {H[H.qn.isin([14, 15])].sh.mean():+.2f}')

# 4. conditional luck test: is XN < -4 worth anything beyond 'below SMA50 & SMA200 at results'?
for smp, d in [('discovery', D), ('holdout', H)]:
    pool = P[ok & (P['sample'] == smp) & (P.c50 < 0) & (P.c200 < 0)]
    act = d.sh.mean(); cnt = 0; B = 20000
    groups = {q: g.sh.values for q, g in pool.groupby('qn')}
    need = d.groupby('qn').size()
    sims = np.zeros(B)
    for q, nq in need.items():
        sims += np.array([rng.choice(groups[q], nq, replace=False).sum() for _ in range(B)])
    sims /= len(d)
    say(f'  conditional luck p ({smp}): C12 {act:+.2f} vs random same-quarter picks among results below SMA50 & SMA200 '
        f'(pool mean {pool.sh.mean():+.2f}, n {len(pool)}): p {(1 + (sims >= act).sum()) / (B + 1):.3f}')

# 5. pre-F&O results of today's F&O stocks (not tradable with futures then; survivor-heavy) - same signal
say('\n=== results of these stocks while NOT in F&O (events.csv in_fo False): same C12 signal, hedged 20 sessions')
ret = pd.read_csv(f'{SP}/sector_lab/data/returns.csv', index_col=0); R = ret.to_numpy(float); SYM = {s: j for j, s in enumerate(ret.columns)}
N = pd.read_csv(f'{SP}/sector_lab/data/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])['Nifty 50'].to_numpy(float)
NR = np.r_[np.nan, N[1:] / N[:-1] - 1]
Z = np.load(f'{OUT}/stock_day.npz'); CL, S50, S200 = Z['CL'], Z['SMA50'], Z['SMA200']
E = ev[(~ev.in_fo.astype(bool)) & ev.i_react.notna() & ev.symbol.isin(SYM)].copy()
out = []
for r in E.itertuples():
    k = int(r.i_react); j = SYM[r.symbol]
    if k + 20 >= len(days) or not np.isfinite(R[k, j]):
        continue
    w = R[k + 1:k + 21, j]
    if np.isnan(w).sum() > 2: continue
    xn = (R[k, j] - NR[k]) * 100
    sig = xn < -4 and CL[k, j] < S50[k, j] and CL[k, j] < S200[k, j]
    st = (np.prod(1 + np.nan_to_num(w)) - 1) * 100; nf = (N[k + 20] / N[k] - 1) * 100
    out.append((r.symbol, r.qn, sig, -(st - nf) - 0.19))
O = pd.DataFrame(out, columns=['symbol', 'qn', 'sig', 'sh'])
for lab, m in [('all non-F&O results', O.sig | True), ('C12 signal', O.sig)]:
    x = O[m]
    say(f'  {lab:22s} n {len(x):4d} hedged short {x.sh.mean():+.2f}' + (f' wo5 {wo(x.sh, 5):+.2f}' if len(x) > 10 else ''))
with open(f'{OUT}/checks.log', 'w') as fh:
    fh.write('\n'.join(lines) + '\n')
