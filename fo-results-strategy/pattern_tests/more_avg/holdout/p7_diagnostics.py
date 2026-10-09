#!/usr/bin/env python3
"""Holdout evaluator - step 7: POST-HOC diagnostics (written after the holdout result was seen; not used for the
survivor decision). Focus: F3 (hold 60) and F4 (pullback + hold 60), plus option sanity checks."""
import numpy as np
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f'{SP}/more_avg/holdout'
D = f'{SP}/sector_lab/data'
LOG = open(f'{OUT}/diagnostics.log', 'w')
rng = np.random.default_rng(7)


def say(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')


ses = pd.read_csv(f'{D}/sessions.csv')
LAST = len(ses) - 1
ret = pd.read_csv(f'{D}/returns.csv', index_col=0)
R = ret.to_numpy(float)
SYM = {s: j for j, s in enumerate(ret.columns)}
PX = np.cumprod(1 + np.nan_to_num(R), axis=0)
CV = np.vstack([np.zeros((1, R.shape[1])), np.cumsum(~np.isnan(R), axis=0)])
N = pd.read_csv(f'{D}/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])['Nifty 50'].to_numpy(float)
P = pd.read_csv(f'{OUT}/panel_eval.csv')
k = P.i_react.to_numpy(int)
jx = P.symbol.map(SYM).to_numpy(int)


def vsn(H, start=None):
    st = k if start is None else start
    out = np.full(len(P), np.nan)
    for r, (j, e) in enumerate(zip(jx, st)):
        if not np.isfinite(e):
            continue
        e = int(e)
        W = max(21, H + 1)
        if e + W > LAST:
            continue
        if W - (CV[e + W + 1, j] - CV[e + 1, j]) > 2:
            continue
        out[r] = ((PX[e + H, j] / PX[e, j]) - (N[e + H] / N[e])) * 100 - 0.19
    return out


HO = P.qn >= 14
groups = {'BASE (W & RSI>50)': P.BASE, 'plain winners': P.W, 'winners RSI<=50': P.W & ~P.BASE,
          'all F&O results': P.qn >= 0}
say('=== 1. Hold-length curve in the HOLDOUT (vsN_net %, close-of-k entry; H>=40 drops qn 21 at data end) ===')
curves = {}
for H in (20, 30, 40, 50, 55, 60):
    curves[H] = vsn(H)
hdr = 'group'.ljust(22) + ''.join(f'H{H:<8d}' for H in curves)
say(hdr)
for g, m in groups.items():
    s = g.ljust(22)
    for H, v in curves.items():
        x = v[m & HO]
        x = x[np.isfinite(x)]
        s += f'{x.mean():+6.2f}({len(x):3d})'.ljust(9) if len(x) else 'n/a'.ljust(9)
    say(s)
same = P.BASE & HO & np.isfinite(curves[60])
say('BASE same 93 signals: ' + ', '.join(f'H{H} {curves[H][same].mean():+.2f}' for H in curves))
say('per 20 sessions on the same 93 signals: ' + ', '.join(f'H{H} {curves[H][same].mean() * 20 / H:+.2f}' for H in curves))

say('\n=== 2. Excess over the generic drift of all F&O results (same quarter, same hold) - holdout ===')
allm = {}
for H in (20, 60):
    v = curves[H]
    qm = pd.Series(v[np.isfinite(v)]).groupby(P.qn[np.isfinite(v)].to_numpy()).mean()
    allm[H] = P.qn.map(qm).to_numpy()
ex60 = curves[60] - allm[60]
ex20 = curves[20] - allm[20]
say(f'F3 (H60) minus same-quarter all-results H60 mean: {np.nanmean(ex60[same]):+.2f} (n {same.sum()})')
say(f'BASE (H20) minus same-quarter all-results H20 mean, same signals: {np.nanmean(ex20[same]):+.2f}')
d = ex60[same] - ex20[same]
fl = rng.choice([-1.0, 1.0], size=(20000, len(d)))
p = (1 + ((fl * d).mean(1) >= d.mean()).sum()) / 20001
qs = pd.Series(d).groupby(P.qn[same].to_numpy()).sum().to_numpy()
flq = rng.choice([-1.0, 1.0], size=(20000, len(qs)))
pq = (1 + ((flq * qs).sum(1) / len(d) >= d.mean()).sum()) / 20001
say(f'paired excess-over-drift diff {d.mean():+.2f}: sign-flip p {p:.4f}, quarter-clustered p {pq:.4f}')
say(f'all F&O results holdout H20 avg {np.nanmean(curves[20][HO]):+.2f}, H60 avg {np.nanmean(curves[60][HO]):+.2f}')

say('\n=== 3. F3 holdout: per quarter, concentration, risk path ===')
t = P[same].copy()
t['v60'] = curves[60][same]
t['v20'] = curves[20][same]
g = t.groupby('qn').agg(n=('v60', 'size'), H60=('v60', 'mean'), H20_same=('v20', 'mean'))
g['diff'] = g.H60 - g.H20_same
say(g.to_string(float_format=lambda x: f'{x:+.2f}'))
tot = t.v60.sum()
best = t.v60.sort_values(ascending=False)
say(f'best 5 trades: ' + ', '.join(f'{r.symbol} q{r.qn} {r.v60:+.1f}' for _, r in t.loc[best.index[:5]].iterrows()) +
    f'; share of holdout total {best.iloc[:5].sum() / tot * 100:.0f}%')
for q in g.index:
    x = t.loc[t.qn != q, 'v60']
    say(f'  drop qn {q}: n {len(x)} avg {x.mean():+.2f}')
# worst hedged mark during the 60 sessions
worst = []
for _, r in t.iterrows():
    j, e = SYM[r.symbol], int(r.i_react)
    path = [((PX[e + h, j] / PX[e, j]) - (N[e + h] / N[e])) * 100 for h in range(1, 61)]
    worst.append(min(path))
worst = np.array(worst)
say(f'worst hedged mark during hold: median {np.median(worst):+.1f}%, 10th pct {np.percentile(worst, 10):+.1f}%, '
    f'share below -10%: {(worst < -10).mean() * 100:.0f}%')
say(f'worst trade {t.v60.min():+.1f}%, best {t.v60.max():+.1f}%, quarter t-stat '
    f'{g.H60.mean() / (g.H60.std(ddof=1) / np.sqrt(len(g))):.2f}')
# concurrency
open_ = np.zeros(LAST + 1)
for e in t.i_react.astype(int):
    open_[e + 1:e + 61] += 1
o20 = np.zeros(LAST + 1)
for e in P.loc[P.BASE & HO, 'i_react'].astype(int):
    o20[e + 1:e + 21] += 1
a, b = t.i_react.min() + 1, t.i_react.max() + 60
say(f'open positions over the holdout trading span: F3 avg {open_[a:b + 1].mean():.1f} max {open_.max():.0f}; '
    f'baseline H20 avg {o20[a:b + 1].mean():.1f} max {o20.max():.0f}')

say('\n=== 4. F4 (pullback + H60) holdout per quarter ===')
t4 = P[P.BASE & HO & P.vsNPB.notna()]
say(t4.groupby('qn').vsNPB.agg(['size', 'mean']).to_string(float_format=lambda x: f'{x:+.2f}'))

say('\n=== 5. Options sanity (holdout) ===')
OT = pd.read_csv(f'{OUT}/opt_trades.csv')
OT = OT.merge(P[['symbol', 'qn', 'raw20', 'stk_H20']], on=['symbol', 'qn'], how='left')
for v in ('ATM', 'OTM5'):
    x = OT[(OT.variant == v) & (OT.status == 'ok')]
    for lab, m in (('disc', x.qn <= 13), ('hold', x.qn >= 14)):
        y = x[m]
        yr = y.reaction_day.str[:4]
        say(f'{v} {lab}: n {len(y)} avg {y.net.mean():+.1f} median {y.net.median():+.1f} hit {(y.net > 0).mean() * 100:.0f}% '
            f'lose>=50% {(y.net <= -50).mean() * 100:.0f}%  corr(net, stock 20d) {np.corrcoef(y.net, y.stk_H20)[0, 1]:.2f}  '
            f'stock raw avg {y.stk_H20.mean():+.2f}  premium/spot median {np.median(y.P / y.spot) * 100:.2f}%  '
            f'fallback {int(y.fallback.sum())} expiry exits {int(y.x_is_expiry.sum())}')
    y = x[x.qn >= 14]
    say(f'  {v} holdout by year: ' + ', '.join(f'{k_} n {len(g_)} {g_.net.mean():+.1f}' for k_, g_ in y.groupby(y.reaction_day.str[:4])))
cols = ['symbol', 'reaction_day', 'tick', 'spot', 'expiry', 'K', 'P', 'fallback', 'x_day', 'x_src', 'X', 'net', 'stk_H20']
say('sample holdout ATM trades:')
say(OT[(OT.variant == 'ATM') & (OT.qn >= 14) & (OT.status == 'ok')].sample(6, random_state=1)[cols]
    .to_string(float_format=lambda x: f'{x:.2f}'))
