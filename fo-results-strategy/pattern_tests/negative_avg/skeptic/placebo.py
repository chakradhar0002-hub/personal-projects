#!/usr/bin/env python3
"""Skeptic step 3: placebo - the same C12 / C42-style chart signals on ordinary days without results.

Ordinary day t for stock j: the stock is in the F&O results panel's span (from its first panel cutoff - 5 to its
last panel reaction + 65 sessions) and NO results event of that stock (events.csv, F&O or not) has its result
session or reaction session in [t-10, t+21]: no results news shortly before t or during the 20-session hold.
Signals at close t (same definitions as at k):
  P12: day-t return vs Nifty < -4% & close < SMA50 & close < SMA200
  P42: close < prior 20-session low & volume >= 1.5 x prior-50 mean (BRKDN_VOL; no 'BAD numbers' exists off-results)
Outcome: short stock / long Nifty from close t to close t+20, cost 0.19, same tradability rule.
"""
import numpy as np
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f'{SP}/negative_avg/skeptic'
days = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv').day.tolist()
T = len(days)
ret = pd.read_csv(f'{SP}/sector_lab/data/returns.csv', index_col=0)
SYMS = list(ret.columns); SYM = {s: j for j, s in enumerate(SYMS)}
R = ret.to_numpy(float)
N = pd.read_csv(f'{SP}/sector_lab/data/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])['Nifty 50'].to_numpy(float)
NR = np.r_[np.nan, N[1:] / N[:-1] - 1]
Z = np.load(f'{OUT}/stock_day.npz')
CL, S50, S200, LOW20, VOLR, NH = (Z[x] for x in ['CL', 'SMA50', 'SMA200', 'LOW20', 'VOLR', 'NH'])
P = pd.read_csv(f'{OUT}/skeptic_panel.csv')
ev = pd.read_csv(f'{SP}/sector_lab/data/events.csv', usecols=['symbol', 'i_rd', 'i_react'])

S = len(SYMS)
inuni = np.zeros((T, S), bool)
for s, g in P.groupby('symbol'):
    j = SYM[s]
    inuni[max(0, int(g.i_cut.min()) - 5):min(T, int(g.i_react.max()) + 66), j] = True
near = np.zeros((T, S), bool)
for r in ev.dropna().itertuples():
    if r.symbol not in SYM:
        continue
    j = SYM[r.symbol]
    for x in {int(r.i_rd), int(r.i_react)}:
        near[max(0, x - 21):min(T, x + 11), j] = True     # t in [x-21, x+10]  <=>  x in [t-10, t+21]
ordinary = inuni & ~near

# 20-session hedged outcome from every close t (vectorised over stocks)
H = 20
cum = np.vstack([np.ones(S), np.cumprod(1 + np.nan_to_num(R[1:]), axis=0)])   # cum[t] = value at close t (blank=0)
cum = np.vstack([np.ones((1, S)), np.cumprod(1 + np.nan_to_num(R[1:]), axis=0)])
blank = np.vstack([np.zeros((1, S)), np.cumsum(np.isnan(R[1:]), axis=0)])
st = np.full((T, S), np.nan); nf = np.full(T, np.nan)
st[:T - H] = (cum[H:] / cum[:T - H] - 1) * 100
nbl = np.full((T, S), 99.0); nbl[:T - H] = blank[H:] - blank[:T - H]
nf[:T - H] = (N[H:] / N[:T - H] - 1) * 100
tradable = np.isfinite(R) & (nbl <= 2) & np.isfinite(st)
sh = -(st - nf[:, None]) - 0.19

XN = (R - NR[:, None]) * 100
P12 = (XN < -4) & (CL < S50) & (CL < S200)
P42 = (CL < LOW20) & (VOLR >= 1.5) & (NH >= 51)

first_h = int(P.loc[P.qn >= 14, 'i_cut'].min())
last_d = int(P.loc[P.qn <= 13, 'i_react'].max())
start = int(P.i_cut.min())
periods = {'discovery-period dates': (start, last_d), 'holdout-period dates': (first_h, T - 1)}
lines = []


def say(s=''):
    lines.append(s); print(s)


def wo(x, n):
    x = np.sort(np.asarray(x))[::-1]
    return x[n:].mean() if len(x) > n else np.nan


def nonoverlap(tt, jj):
    """keep a signal only if the same stock had no kept signal in the previous 20 sessions"""
    keep = []
    last = {}
    for t, j in sorted(zip(tt, jj)):
        if t - last.get(j, -999) > 20:
            keep.append((t, j)); last[j] = t
    return np.array(keep)


rows = []
for pname, (a, b) in periods.items():
    tmask = np.zeros(T, bool); tmask[a:b + 1] = True
    base = ordinary & tradable & tmask[:, None]
    say(f'\n=== {pname} ({days[a]} .. {days[b]}): ordinary stock-days {base.sum()}, base hedged short {np.nanmean(sh[base]):+.2f}')
    for name, sig in [('P12 placebo of C12', P12), ('P42 placebo of C42 (BRKDN_VOL)', P42),
                      ('P12 but XN<-5', (XN < -5) & (CL < S50) & (CL < S200)),
                      ('below SMA50 & SMA200, any day move', (CL < S50) & (CL < S200))]:
        m = base & sig
        tt, jj = np.nonzero(m)
        v = sh[tt, jj]
        # day-clustered: mean per signal day, then mean of days
        dfm = pd.DataFrame({'t': tt, 'v': v})
        day_mean = dfm.groupby('t').v.mean()
        ko = nonoverlap(tt, jj) if len(tt) else np.zeros((0, 2), int)
        vk = sh[ko[:, 0], ko[:, 1]] if len(ko) else np.array([])
        su = -st[tt, jj] - 0.17
        say(f'  {name:36s} n {len(v):6d} hedged {v.mean():+.2f} median {np.median(v):+.2f} wo5 {wo(v, 5):+.2f}'
            f'  unhedged {su.mean():+.2f} | day-clustered {day_mean.mean():+.2f} over {len(day_mean)} days'
            f' | non-overlapping n {len(vk)} {vk.mean() if len(vk) else np.nan:+.2f}')
        rows.append(dict(period=pname, signal=name, n=len(v), hedged=v.mean(), median=np.median(v), wo5=wo(v, 5),
                         unhedged=su.mean(), day_clustered=day_mean.mean(), n_days=len(day_mean),
                         n_nonoverlap=len(vk), nonoverlap=vk.mean() if len(vk) else np.nan,
                         base=np.nanmean(sh[base])))
        if name.startswith('P12 placebo'):
            # by year
            yy = pd.Series(v).groupby([days[t][:4] for t in tt]).agg(['size', 'mean'])
            say('     by year: ' + ', '.join(f'{i}:{r["size"]}/{r["mean"]:+.2f}' for i, r in yy.iterrows()))
            top_days = dfm.groupby('t').v.agg(['size', 'mean']).sort_values('size', ascending=False).head(3)
            say('     busiest signal days: ' + ', '.join(f'{days[t]} n{r["size"]} {r["mean"]:+.2f}' for t, r in top_days.iterrows()))

# results-day comparison in the same table form
say('\n=== same signals AT RESULTS (from skeptic_panel; hedged short H20)')
P['sh'] = -(P.st20 - P.nf20) - 0.19
for smp in ['discovery', 'holdout']:
    d = P[(P['sample'] == smp) & P.st20.notna()]
    for name, m in [('C12', d.C12.astype(bool)), ('BRKDN_VOL (any numbers)', d.BRKDN_VOL.astype(bool)),
                    ('BRKDN_VOL & not BAD', d.BRKDN_VOL.astype(bool) & ~d.BAD.astype(bool)),
                    ('C42', d.C42.astype(bool))]:
        x = d[m]
        say(f'  {smp:9s} {name:26s} n {len(x):4d} hedged {x.sh.mean():+.2f} wo5 {wo(x.sh, 5):+.2f}')
pd.DataFrame(rows).to_csv(f'{OUT}/placebo.csv', index=False, float_format='%.4f')
with open(f'{OUT}/placebo.log', 'w') as fh:
    fh.write('\n'.join(lines) + '\n')
