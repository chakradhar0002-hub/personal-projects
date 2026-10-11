#!/usr/bin/env python3
"""POST-SELECTION, DESCRIPTIVE ONLY (discovery qn 0-13): neighbours of the two finalists fixed by search.py.
Not candidates, cannot change the finalists. Reuses search.py's outcome code by import-free copy of its definitions.
Writes robustness.txt.
"""
import os
import runpy

HERE = os.path.dirname(os.path.abspath(__file__))
import numpy as np  # noqa: E402

# run search.py's module body to get f, OUT-building function (it re-writes its own outputs identically; seed fixed)
g = runpy.run_path(f'{HERE}/search.py', run_name='robust')
f, outcome, QN = g['f'], g['outcome'], g['QN']
assert f.qn.max() <= 13
out = []


def row(name, sig, entry, H):
    s, n_, ok = outcome(entry, H)
    sn = -(s - n_) - 0.19
    base = sn[ok].mean()
    sel = sig.fillna(False).to_numpy(bool) & ok
    x = sn[sel]
    srt = np.sort(x)[::-1]
    h1, h2 = x[QN[sel] <= 6], x[QN[sel] > 6]
    qs = {q: x[QN[sel] == q].mean() for q in np.unique(QN[sel])}
    out.append(f'{name:44s} {entry:3s} H{H:<3d} n {len(x):4d}  short {x.mean():+6.2f}  w/o5 {srt[5:].mean():+6.2f}  '
               f'w/o10 {srt[10:].mean():+6.2f}  base {base:+6.2f}  h1 {h1.mean():+6.2f} ({len(h1)})  '
               f'h2 {h2.mean():+6.2f} ({len(h2)})  q+ {sum(v > 0 for v in qs.values())}/{len(qs)}')


XN = f.XN
B50, B200 = f.rx_close_vs_sma50_pct < 0, f.rx_close_vs_sma200_pct < 0
BAD, BRK = f.BAD.astype(bool), f.BRKDN_VOL.astype(bool)
out.append('Finalist 1 C12 = XN < -4 & close_k < SMA50 & close_k < SMA200, E0 H20 - neighbours')
for thr in (-2, -3, -4, -5, -6):
    row(f'XN<{thr} & B50 & B200', (XN < thr) & B50 & B200, 'E0', 20)
for H in (5, 10, 40):
    row('XN<-4 & B50 & B200', (XN < -4) & B50 & B200, 'E0', H)
row('XN<-4 & B50 & B200', (XN < -4) & B50 & B200, 'E1', 20)
row('XN<-4 & B50 & B200', (XN < -4) & B50 & B200, 'E1o', 20)
row('XN<-4 & B50 & B200, qn >= 3 only', (XN < -4) & B50 & B200 & (f.qn >= 3), 'E0', 20)
row('XN<-4 & B50 & NOT B200', (XN < -4) & B50 & ~B200, 'E0', 20)
row('XN<-4 & NOT B50', (XN < -4) & ~B50, 'E0', 20)
row('XN in [-4, 0) & B50 & B200', (XN < 0) & (XN >= -4) & B50 & B200, 'E0', 20)
row('any XN & B50 & B200', B50 & B200, 'E0', 20)
out.append('')
out.append('Finalist 2 C42 = BAD reported numbers & 20-day low breakdown on volume >= 1.5x at k, E0 H20 - neighbours')
for H in (5, 10, 40):
    row('BAD & BRKDN_VOL', BAD & BRK, 'E0', H)
row('BAD & BRKDN_VOL', BAD & BRK, 'E1', 20)
row('BAD & BRKDN_VOL', BAD & BRK, 'E1o', 20)
row('BAD & BRKDN_VOL & XN<0', BAD & BRK & (XN < 0), 'E0', 20)
row('BAD & close<20d low (any volume)', BAD & (f.rx_don20_break_dn == 1), 'E0', 20)
row('NOT BAD & BRKDN_VOL', ~BAD & f.E_BAD.astype(bool) & BRK, 'E0', 20)
row('BRKDN_VOL (any numbers)', BRK, 'E0', 20)
open(f'{HERE}/robustness.txt', 'w').write('POST-SELECTION DESCRIPTIVE ONLY - discovery qn 0-13; short = -(stock-Nifty)-0.19 %\n'
                                          + '\n'.join(out) + '\n')
print('\n'.join(out))
