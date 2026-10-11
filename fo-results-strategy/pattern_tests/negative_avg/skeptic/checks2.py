#!/usr/bin/env python3
"""Skeptic step 5: IT-sector shock, C22 40-session (post-hoc) stress, calendar-time without q14, MA4 concentration,
40-session placebo."""
import numpy as np, pandas as pd
SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f'{SP}/negative_avg/skeptic'
days = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv').day.tolist(); T = len(days)
ret = pd.read_csv(f'{SP}/sector_lab/data/returns.csv', index_col=0); R = ret.to_numpy(float)
SYMS = list(ret.columns); SYM = {s: j for j, s in enumerate(SYMS)}; S = len(SYMS)
N = pd.read_csv(f'{SP}/sector_lab/data/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])['Nifty 50'].to_numpy(float)
NR = np.r_[np.nan, N[1:] / N[:-1] - 1]
P = pd.read_csv(f'{OUT}/skeptic_panel.csv')
ev = pd.read_csv(f'{SP}/sector_lab/data/events.csv', usecols=['symbol', 'qn', 'industry', 'i_rd', 'i_react'])
P = P.merge(ev[['symbol', 'qn', 'industry']], on=['symbol', 'qn'], how='left')
P['sh'] = -(P.st20 - P.nf20) - 0.19
P['sh40'] = -(P.st40 - P.nf40) - 0.19
lines = []
def say(s=''):
    lines.append(s); print(s)
def wo(x, n):
    x = np.sort(np.asarray(x))[::-1]; return x[n:].mean()
def nw_tstat(y, L=20):
    y = np.asarray(y, float); n = len(y); x = y - y.mean(); g = x @ x / n
    s = g + 2 * sum((1 - l / (L + 1)) * (x[l:] @ x[:-l] / n) for l in range(1, L + 1)); return y.mean() / np.sqrt(s / n)

H12 = P[P.st20.notna() & (P['sample'] == 'holdout') & P.C12.astype(bool)]
it = H12.industry == 'Computers - Software'
say(f'C12 holdout IT software: n {it.sum()} mean {H12.sh[it].mean():+.2f} (q19 IT n {(it & (H12.qn == 19)).sum()} '
    f'mean {H12.sh[it & (H12.qn == 19)].mean():+.2f}); without IT n {(~it).sum()} mean {H12.sh[~it].mean():+.2f} wo5 {wo(H12.sh[~it], 5):+.2f}')
say(f'  without IT and without q14: n {(~it & (H12.qn != 14)).sum()} mean {H12.sh[~it & (H12.qn != 14)].mean():+.2f}')
B = P[P.st20.notna() & (P['sample'] == 'holdout')]
say(f'  holdout base IT software q19: n {((B.industry == "Computers - Software") & (B.qn == 19)).sum()} mean '
    f'{B.sh[(B.industry == "Computers - Software") & (B.qn == 19)].mean():+.2f} (all IT results fell after Jan-Feb 2026 results)')

# calendar-time without q14
def calendar(d, H=20, cost=0.19):
    rows = {}
    for r in d.itertuples():
        e = int(r.i_react); jj = SYM[r.symbol]
        w = np.nan_to_num(R[e + 1:e + H + 1, jj])
        path = np.r_[1, np.cumprod(1 + w)]; npath = np.r_[1, N[e + 1:e + H + 1] / N[e]]
        pnl = (-(np.diff(path)) + np.diff(npath)) * 100 - cost / H
        for t, v in zip(range(e + 1, e + H + 1), pnl):
            rows.setdefault(t, []).append(v)
    ts = pd.Series({t: np.mean(v) for t, v in rows.items()}).sort_index()
    return ts, nw_tstat(ts.values, H)
ts, t = calendar(H12[H12.qn != 14])
say(f'C12 holdout calendar-time without q14: mean daily {ts.mean():+.4f}% (x20 {ts.mean() * 20:+.2f}), NW t {t:.2f}')
ts, t = calendar(H12[~it])
say(f'C12 holdout calendar-time without IT software: x20 {ts.mean() * 20:+.2f}, NW t {t:.2f}')

# C22 at 40 sessions (post-hoc lead)
for smp in ['discovery', 'holdout']:
    d = P[(P['sample'] == smp) & P.C22.astype(bool) & P.st40.notna()]
    base = P[(P['sample'] == smp) & P.st40.notna()]
    q = d.groupby('qn').sh40.agg(['size', 'mean', 'sum'])
    loo = [(d.sh40.sum() - r['sum']) / (len(d) - r['size']) for _, r in q.iterrows()]
    say(f'\nC22 H40 {smp}: n {len(d)} vsN {-(d.sh40 + 0.19).mean():+.2f} short {d.sh40.mean():+.2f} median {d.sh40.median():+.2f} '
        f'wo5 {wo(d.sh40, 5):+.2f} wo10 {wo(d.sh40, 10):+.2f}; base {base.sh40.mean():+.2f}; LOQO min {min(loo):+.2f}; '
        f'per qn ' + ', '.join(f'{i}:{int(r["size"])}/{r["mean"]:+.2f}' for i, r in q.iterrows()))
    if smp == 'holdout':
        it2 = d.industry == 'Computers - Software'
        say(f'  without IT software: n {(~it2).sum()} {d.sh40[~it2].mean():+.2f}; without q14: {d.sh40[d.qn != 14].mean():+.2f};'
            f' unhedged {(-d.st40 - 0.17).mean():+.2f}; beta-hedged {(-(d.st40 - d.beta250 * d.nf40) - 0.19).mean():+.2f};'
            f' worst {d.sh40.min():+.1f}; share losing >10% {100 * (d.sh40 < -10).mean():.1f}%')
        ts, t = calendar(d, H=40)
        say(f'  calendar-time H40: x40 {ts.mean() * 40:+.2f}, NW(40) t {t:.2f}')

# 40-session placebo of C22 signal on ordinary days (same construction as placebo.py)
Z = np.load(f'{OUT}/stock_day.npz'); CL, S200 = Z['CL'], Z['SMA200']
inuni = np.zeros((T, S), bool)
for s, g in P.groupby('symbol'):
    inuni[max(0, int(g.i_cut.min()) - 5):min(T, int(g.i_react.max()) + 66), SYM[s]] = True
near = np.zeros((T, S), bool)
for r in ev.dropna(subset=['i_rd', 'i_react']).itertuples():
    if r.symbol in SYM:
        for x in {int(r.i_rd), int(r.i_react)}:
            near[max(0, x - 41):min(T, x + 11), SYM[r.symbol]] = True
cum = np.vstack([np.ones((1, S)), np.cumprod(1 + np.nan_to_num(R[1:]), axis=0)])
blank = np.vstack([np.zeros((1, S)), np.cumsum(np.isnan(R[1:]), axis=0)])
Hh = 40
st = np.full((T, S), np.nan); st[:T - Hh] = (cum[Hh:] / cum[:T - Hh] - 1) * 100
nbl = np.full((T, S), 99.0); nbl[:T - Hh] = blank[Hh:] - blank[:T - Hh]
nf = np.full(T, np.nan); nf[:T - Hh] = (N[Hh:] / N[:T - Hh] - 1) * 100
sh = -(st - nf[:, None]) - 0.19
okm = inuni & ~near & np.isfinite(R) & (nbl <= 2) & np.isfinite(st)
sig = ((R - NR[:, None]) * 100 < -4) & (CL < S200)
first_h = int(P.loc[P.qn >= 14, 'i_cut'].min())
for lab, rng_ in [('discovery dates', (int(P.i_cut.min()), int(P.loc[P.qn <= 13, 'i_react'].max()))), ('holdout dates', (first_h, T - 1))]:
    tm = np.zeros(T, bool); tm[rng_[0]:rng_[1] + 1] = True
    m = okm & sig & tm[:, None]
    say(f'placebo C22 H40 ({lab}, no results within [t-10, t+41]): n {m.sum()} hedged short {sh[m].mean():+.2f}; '
        f'ordinary base {sh[okm & tm[:, None]].mean():+.2f}')

# MA4 concentration (trade A, unhedged) from the evaluator's trade list, re-derived from outcomes
tr = pd.read_csv(f'{SP}/negative_avg/holdout/trades_all.csv')
m4 = tr[(tr.finalist == 'MA4') & (tr['sample'] == 'holdout')]
say(f'\nMA4 holdout: n {len(m4)} short {m4.short_primary.mean():+.2f} median {m4.short_primary.median():+.2f} '
    f'wo5 {wo(m4.short_primary, 5):+.2f}; per qn ' +
    ', '.join(f'{i}:{len(g)}/{g.short_primary.mean():+.2f}' for i, g in m4.groupby('qn')) +
    f'; worst {m4.short_primary.min():+.1f}; share losing >10% {100 * (m4.short_primary < -10).mean():.1f}%')
with open(f'{OUT}/checks2.log', 'w') as fh:
    fh.write('\n'.join(lines) + '\n')
