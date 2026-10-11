#!/usr/bin/env python3
"""Skeptic step 2: stress tests of the C12 / C42 short (20 sessions from close k, Nifty-hedged, cost 0.19)."""
import numpy as np
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f'{SP}/negative_avg/skeptic'
C_H, C_U = 0.19, 0.17
days = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv').day.tolist()
T = len(days)
ret = pd.read_csv(f'{SP}/sector_lab/data/returns.csv', index_col=0)
R = ret.to_numpy(float)
N = pd.read_csv(f'{SP}/sector_lab/data/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])['Nifty 50'].to_numpy(float)
NR = np.r_[np.nan, N[1:] / N[:-1] - 1]

P = pd.read_csv(f'{OUT}/skeptic_panel.csv')
P['entry_day'] = pd.to_datetime(P.entry_day)
P['vsN20'] = P.st20 - P.nf20
P['sh'] = -P.vsN20 - C_H                       # hedged short net
P['su'] = -P.st20 - C_U                        # unhedged short net
P['sb'] = -(P.st20 - P.beta250 * P.nf20) - C_H  # beta-hedged short net
P['sh_k1'] = -(P.st20_k1 - P.nf20_k1) - 0.27     # realistic: close k+1, 0.25 + 0.02
P['sh40'] = -(P.st40 - P.nf40) - C_H
P['sh10'] = -(P.st10 - P.nf10) - C_H
ok = P.st20.notna()
lines = []


def say(s=''):
    lines.append(s)
    print(s)


def wo(x, n):
    x = np.sort(np.asarray(x))[::-1]
    return x[n:].mean() if len(x) > n else np.nan


def nw_t(x, L):
    x = np.asarray(x, float); x = x - x.mean(); n = len(x)
    g0 = x @ x / n
    s = g0 + 2 * sum((1 - l / (L + 1)) * (x[l:] @ x[:-l] / n) for l in range(1, L + 1))
    return np.nan if s <= 0 else None if False else s


def nw_tstat(y, L=20):
    y = np.asarray(y, float); n = len(y)
    s = nw_t(y, L)
    return y.mean() / np.sqrt(s / n)


def block(name, sig, sample):
    d = P[sig & ok & (P['sample'] == sample if sample != 'all' else True)].copy()
    base = P[ok & (P['sample'] == sample if sample != 'all' else True)]
    say(f'\n=== {name} [{sample}] n {len(d)} stocks {d.symbol.nunique()}')
    if len(d) == 0:
        return d
    say(f'  raw {d.st20.mean():+.2f}  vsN {d.vsN20.mean():+.2f}  hedged short {d.sh.mean():+.2f}  median {d.sh.median():+.2f}'
        f'  wo5 {wo(d.sh, 5):+.2f}  wo10 {wo(d.sh, 10):+.2f}  trim10% {d.sh.clip(d.sh.quantile(.1), d.sh.quantile(.9)).mean():+.2f}'
        f'  win% {100 * (d.sh > 0).mean():.0f}')
    say(f'  unhedged short {d.su.mean():+.2f} (wo5 {wo(d.su, 5):+.2f})  beta-hedged {d.sb.mean():+.2f} (wo5 {wo(d.sb.dropna(), 5):+.2f})'
        f'  mean beta {d.beta250.mean():.2f} vs base {base.beta250.mean():.2f}')
    say(f'  base: hedged {base.sh.mean():+.2f} unhedged {base.su.mean():+.2f} beta-hedged {base.sb.mean():+.2f}  (n {len(base)})')
    # OLS stock = a + b * nifty over the trade window (per-trade, pooled)
    b, a = np.polyfit(d.nf20, d.st20, 1)
    bb, ab = np.polyfit(base.nf20, base.st20, 1)
    say(f'  pooled regression stock20 = a + b*nifty20: a {a:+.2f} b {b:.2f}  (base a {ab:+.2f} b {bb:.2f});'
        f' short alpha after cost {-a - C_U:+.2f}')
    # quarters
    q = d.groupby('qn').sh.agg(['size', 'mean', 'sum'])
    tot = d.sh.sum()
    say('  per qn (n, mean): ' + ', '.join(f'{i}:{r["size"]}/{r["mean"]:+.2f}' for i, r in q.iterrows()))
    loo = {i: (tot - r['sum']) / (len(d) - r['size']) for i, r in q.iterrows()}
    say('  leave-one-quarter-out mean: ' + ', '.join(f'-{i}:{v:+.2f}' for i, v in loo.items()) +
        f'  -> min {min(loo.values()):+.2f}, max {max(loo.values()):+.2f}')
    top2 = q['mean'].mul(q['size']).sort_values(ascending=False).index[:2].tolist()
    rest = d[~d.qn.isin(top2)]
    say(f'  without the 2 best quarters {top2}: n {len(rest)} mean {rest.sh.mean():+.2f}')
    y = d.groupby(d.entry_day.dt.year).sh.agg(['size', 'mean'])
    say('  by entry year: ' + ', '.join(f'{i}:{r["size"]}/{r["mean"]:+.2f}' for i, r in y.iterrows()))
    # Nifty regimes
    for lab, m in [('Nifty up over the hold', d.nf20 > 0), ('Nifty down over the hold', d.nf20 <= 0),
                   ('Nifty above 200d at entry', d.nifty_above200), ('Nifty below 200d at entry', ~d.nifty_above200),
                   ('Nifty 20d before entry > 0', d.nifty_pre20 > 0), ('Nifty 20d before entry <= 0', d.nifty_pre20 <= 0)]:
        x = d[m]
        bm = base[(base.nf20 > 0) if 'up over' in lab else (base.nf20 <= 0) if 'down over' in lab else
                  base.nifty_above200 if 'above 200d' in lab else ~base.nifty_above200 if 'below 200d' in lab else
                  (base.nifty_pre20 > 0) if '> 0' in lab else (base.nifty_pre20 <= 0)]
        if len(x):
            say(f'  {lab:28s} n {len(x):3d} hedged {x.sh.mean():+.2f} (base {bm.sh.mean():+.2f})  unhedged {x.su.mean():+.2f}'
                f' (base {bm.su.mean():+.2f})  wo5 hedged {wo(x.sh, 5):+.2f}')
    # survivorship split
    for lab, m in [('in F&O since qn<=1', d.first_qn <= 1), ('later joiners (first qn>=2)', d.first_qn >= 2)]:
        x = d[m]; bm = base[(base.first_qn <= 1) if 'since' in lab else (base.first_qn >= 2)]
        if len(x):
            say(f'  {lab:28s} n {len(x):3d} hedged {x.sh.mean():+.2f} wo5 {wo(x.sh, 5):+.2f} (base {bm.sh.mean():+.2f}, n {len(bm)})')
    # squeeze
    say(f'  worst trade {d.sh.min():+.2f} ({d.loc[d.sh.idxmin(), "symbol"]} q{d.loc[d.sh.idxmin(), "qn"]}); '
        f'share losing >10% {100 * (d.sh < -10).mean():.1f}% (base {100 * (base.sh < -10).mean():.1f}%); '
        f'share losing >5% {100 * (d.sh < -5).mean():.1f}%')
    say(f'  biggest one-day rise against the short: raw {d.max_up_day.max():+.2f}% '
        f'({d.loc[d.max_up_day.idxmax(), "symbol"]} q{d.loc[d.max_up_day.idxmax(), "qn"]}), vs Nifty {d.max_rel_day.max():+.2f}%;'
        f' trades with a +10% day {int((d.max_up_day > 10).sum())}; median worst intra-hold drawdown (hedged) {d.mae_hedged.median():.2f}%,'
        f' 90th pct {d.mae_hedged.quantile(.9):.2f}%, max {d.mae_hedged.max():.2f}%')
    # top contributors
    t5 = d.nlargest(5, 'sh')[['symbol', 'qn', 'entry_day', 'sh']]
    say('  5 biggest falls: ' + '; '.join(f'{r.symbol} q{r.qn} {r.entry_day.date()} {r.sh:+.1f}' for r in t5.itertuples()))
    st = d.groupby('symbol').sh.sum().sort_values(ascending=False)
    say(f'  top-3 stocks share of total profit: {st.head(3).sum() / tot * 100 if tot > 0 else np.nan:.0f}% '
        f'({", ".join(f"{s} {v:+.1f}" for s, v in st.head(3).items())}); sum {tot:+.1f}')
    # realistic / horizon neighbours
    say(f'  realistic close k+1, cost 0.27: {d.sh_k1.mean():+.2f} (wo5 {wo(d.sh_k1.dropna(), 5):+.2f}; base {base.sh_k1.mean():+.2f})'
        f';  H10 {d.sh10.mean():+.2f}; H40 {d.sh40.mean():+.2f} (n {d.sh40.notna().sum()})')
    return d


def calendar(name, d, cost=C_H):
    """Daily equal-weight portfolio of open hedged shorts; cost charged evenly over the 20 days."""
    if len(d) == 0:
        return
    rows = {}
    for r in d.itertuples():
        e = int(r.i_react); jj = int(r.j)
        w = np.nan_to_num(R[e + 1:e + 21, jj]); nr = NR[e + 1:e + 21]
        # static position: daily P&L on entry notional
        path = np.r_[1, np.cumprod(1 + w)]; npath = np.r_[1, N[e + 1:e + 21] / N[e]]
        pnl = -(np.diff(path)) + np.diff(npath)
        for t, v in zip(range(e + 1, e + 21), pnl * 100 - cost / 20):
            rows.setdefault(t, []).append(v)
    ts = pd.Series({t: np.mean(v) for t, v in rows.items()}).sort_index()
    cnt = pd.Series({t: len(v) for t, v in rows.items()}).sort_index()
    t_nw = nw_tstat(ts.values, 20)
    full = pd.Series(0.0, index=range(ts.index.min(), ts.index.max() + 1)); full.loc[ts.index] = ts
    t_full = nw_tstat(full.values, 20)
    say(f'  calendar-time {name}: active days {len(ts)} (of {len(full)}), mean open positions {cnt.mean():.1f} (max {cnt.max()}),'
        f' mean daily {ts.mean():+.4f}% -> x20 {ts.mean() * 20:+.2f}%, NW(20) t {t_nw:.2f};'
        f' incl. idle days t {t_full:.2f}; annualised on active days {ts.mean() * 250:+.1f}%, vol {ts.std() * np.sqrt(250):.1f}%,'
        f' worst day {ts.min():+.2f}%, max drawdown {(full.cumsum() - full.cumsum().cummax()).min():.1f} pts')
    # by month contribution
    mon = full.groupby([days[i][:7] for i in full.index]).sum().sort_values()
    say('   best months for the short: ' + ', '.join(f'{m} {v:+.1f}' for m, v in mon.tail(4)[::-1].items()) +
        ' | worst: ' + ', '.join(f'{m} {v:+.1f}' for m, v in mon.head(3).items()) + f' | total {mon.sum():+.1f}')
    return ts


for name, col in [('C12', 'C12'), ('C42', 'C42'), ('C22 (post-hoc, H20 shown; H40 in last line)', 'C22')]:
    for smp in ['discovery', 'holdout']:
        d = block(name, P[col].fillna(False).astype(bool), smp)
        if smp == 'holdout' or col != 'C22':
            calendar(f'{col} {smp}', d)

# neighbours on the holdout (information only, not a reselection)
say('\n=== holdout neighbours of C12 (hedged short, H20, mean / wo5 / n)')
H = P[ok & (P['sample'] == 'holdout')]
for lab, m in [('XN<-3 & <SMA50 & <SMA200', (H.XN < -3) & (H.c50 < 0) & (H.c200 < 0)),
               ('XN<-4 & <SMA50 & <SMA200 (C12)', (H.XN < -4) & (H.c50 < 0) & (H.c200 < 0)),
               ('XN<-5 & <SMA50 & <SMA200', (H.XN < -5) & (H.c50 < 0) & (H.c200 < 0)),
               ('XN<-6 & <SMA50 & <SMA200', (H.XN < -6) & (H.c50 < 0) & (H.c200 < 0)),
               ('XN<-4 & <SMA200 (C22 at H20)', (H.XN < -4) & (H.c200 < 0)),
               ('XN<-4 & >=SMA200', (H.XN < -4) & (H.c200 >= 0)),
               ('any XN & <SMA50 & <SMA200', (H.c50 < 0) & (H.c200 < 0)),
               ('-4<=XN<0 & <SMA50 & <SMA200', (H.XN >= -4) & (H.XN < 0) & (H.c50 < 0) & (H.c200 < 0)),
               ('XN>=0 & <SMA50 & <SMA200', (H.XN >= 0) & (H.c50 < 0) & (H.c200 < 0)),
               ('all results (base)', H.XN.notna() | True)]:
    x = H[m]
    say(f'  {lab:34s} {x.sh.mean():+.2f} / {wo(x.sh, 5):+.2f} / {len(x)}   unhedged {x.su.mean():+.2f}')

with open(f'{OUT}/analyze.log', 'w') as fh:
    fh.write('\n'.join(lines) + '\n')
