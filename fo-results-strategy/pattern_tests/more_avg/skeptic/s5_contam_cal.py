#!/usr/bin/env python3
"""Skeptic review, part 5: (a) contamination - were the finalists' holdout numbers already computable from earlier
full-sample work? (b) full-sample calendar-time F3 - BASE with Newey-West."""
import numpy as np
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f'{SP}/more_avg/skeptic'
D = f'{SP}/sector_lab/data'
L = []


def pr(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    L.append(s)


h = pd.read_csv(f'{SP}/winners_rsi/build/holds.csv')
v = pd.read_csv(f'{SP}/winners_rsi/build/variants.csv')
pr('=== (a) Contamination: earlier full-sample files vs this round\'s holdout numbers ===')
r = h[(h.H == 60) & (h.group == 'MAIN W&RSI>50')].iloc[0]
pr(f'holds.csv H60 MAIN: n {r.n} avg {r.avg:.4f}, first14 {r.first14:.4f}, last8 {r.last8:.4f} '
   f'(holdout evaluator F3: 93 trades +5.104)')
pr(f'  derivable from the published doc alone: (4.84*215 - 4.64*122)/93 = {(4.84 * 215 - 4.64 * 122) / 93:.2f}')
for H in (30, 40, 60):
    rr = h[(h.H == H) & (h.group == 'MAIN W&RSI>50')].iloc[0]
    pr(f'  H{H}: first14 {rr.first14:+.2f} last8 {rr.last8:+.2f}')
for nm in ['XN>5 & cut RSI>50', 'XN>6 & cut RSI>50', 'XN>4 & cut RSI>60', 'XN>4 & cut RSI>70']:
    rr = v[v.variant == nm].iloc[0]
    pr(f'variants.csv {nm}: n {rr.n} avg {rr.avg:+.2f} first14 {rr.first14:+.2f} last8 {rr.last8:+.2f}')
pr('  (holdout evaluator F1 XN>5: 75 trades +2.26)')

# ---- (b) full-sample calendar-time
days = pd.read_csv(f'{D}/sessions.csv').day.tolist()
T = len(days)
LAST = T - 1
ret = pd.read_csv(f'{D}/returns.csv', index_col=0)
SYM = {s: j for j, s in enumerate(ret.columns)}
R = ret.to_numpy(float)
N = pd.read_csv(f'{D}/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])['Nifty 50'].to_numpy(float)
NR = np.r_[np.nan, N[1:] / N[:-1] - 1]
P = pd.read_csv(f'{OUT}/panel_skeptic.csv')
B = P[(P.XN > 4) & (P.rsi > 50) & P.v60.notna()]


def port(trs, a, b):
    S = np.zeros(T)
    C = np.zeros(T)
    for s, k in trs:
        j = SYM[s]
        lo, hi = k + a, min(k + b, LAST)
        S[lo:hi + 1] += np.nan_to_num(R[lo:hi + 1, j]) - NR[lo:hi + 1]
        C[lo:hi + 1] += 1
    return np.where(C > 0, S / np.maximum(C, 1), 0.0) * 100, C


def nw(x, lag):
    x = np.asarray(x, float)
    n = len(x)
    mu = x.mean()
    e = x - mu
    var = e @ e / n
    for l in range(1, lag + 1):
        var += 2 * (1 - l / (lag + 1)) * (e[l:] @ e[:-l]) / n
    return mu, mu / np.sqrt(var / n)


pr('\n=== (b) Calendar-time, FULL sample (215 signals with a 60-session window) ===')
tr = list(zip(B.symbol, B.k))
f3, c3 = port(tr, 1, 60)
b0, c0 = port(tr, 1, 20)
span = np.where(c3 > 0)[0]
sl = slice(span.min(), span.max() + 1)
for nm, s in [('F3', f3), ('BASE', b0), ('F3 - BASE', f3 - b0)]:
    mu, t20 = nw(s[sl], 20)
    _, t60 = nw(s[sl], 60)
    pr(f'{nm:10s} per 20 sessions {mu * 20:+.2f}  NW t lag20 {t20:+.2f} lag60 {t60:+.2f}')
# capital-matched: baseline with 3x the capital per trade is not possible; compare per-position-day returns
pr(f'per position-day: F3 {np.nansum(f3[sl] * c3[sl]) / c3[sl].sum() * 20:+.2f} per 20d, '
   f'BASE {np.nansum(b0[sl] * c0[sl]) / c0[sl].sum() * 20:+.2f} per 20d')
open(f'{OUT}/s5_contam_cal.log', 'w').write('\n'.join(L) + '\n')
