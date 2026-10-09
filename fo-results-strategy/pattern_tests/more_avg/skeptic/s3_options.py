#!/usr/bin/env python3
"""Skeptic review, part 3: option finalists F7 (ATM call) / F8 (5% OTM call). Is the higher average just leverage?
Spot-checks 30 trades' entry/exit prices against the raw bhavcopy rows, then compares risk with the stock trade on the
same signals (worst trade, share losing > 50%, mean/sd, leverage-matched stock)."""
import sqlite3

import numpy as np
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f'{SP}/more_avg/skeptic'
o = pd.read_csv(f'{SP}/more_avg/holdout/opt_trades.csv')
P = pd.read_csv(f'{OUT}/panel_skeptic.csv')
L = []


def pr(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    L.append(s)


# ---- spot check against bhav rows
c = sqlite3.connect(f'file:{SP}/more_avg/holdout/bhav.db?mode=ro', uri=True)
ok = o[o.status == 'ok']
smp = ok.sample(30, random_state=7)
bad = 0
for r in smp.itertuples():
    q = c.execute("select close, settle, volume, expiry, act_expiry from row where day=? and symbol=? and kind='CE' "
                  "and abs(strike-?)<1e-6", (r.reaction_day, r.tick, r.K)).fetchall()
    q = [x for x in q if r.expiry in (x[3], x[4])]
    Pc = q[0][0] if q else np.nan
    if r.x_src == 'intrinsic' or r.x_is_expiry:
        Xc = max(r.U - r.K, 0) if np.isfinite(r.U) else np.nan
    else:
        xx = c.execute("select close, settle, volume, expiry, act_expiry from row where day=? and symbol=? and kind='CE' "
                       "and abs(strike-?)<1e-6", (r.x_day, r.tick, r.K)).fetchall()
        xx = [x for x in xx if r.expiry in (x[3], x[4])]
        Xc = (xx[0][0] if xx and xx[0][2] > 0 and xx[0][0] > 0 else (xx[0][1] if xx else np.nan))
    net = (Xc / Pc - 1) * 100 - 1.0 - 0.05 * r.spot / Pc
    flag = abs(net - r.net) > 0.05
    bad += flag
    if flag:
        pr(f'  MISMATCH {r.variant} {r.symbol} {r.reaction_day} K {r.K} P {r.P}/{Pc} X {r.X}/{Xc} net {r.net:.2f}/{net:.2f} {r.x_src}')
pr(f'spot check: 30 random option trades re-read from bhav rows, mismatches > 0.05 pts: {bad}')

# ---- leverage comparison on the same signals
P['key'] = P.symbol + '|' + P.k.astype(str)
ok = ok.copy()
ok['key'] = ok.symbol + '|' + ok.k.astype(str)
P['raw20'] = P.s20 - 0.17
m = ok.merge(P[['key', 'v20', 'raw20', 's20', 'n20']], on='key', how='left')
assert m.v20.notna().all()


def risk(x):
    x = np.asarray(x, float)
    return dict(n=len(x), avg=x.mean(), med=np.median(x), sd=x.std(ddof=1), mpsd=x.mean() / x.std(ddof=1),
                worst=x.min(), p50=(x < -50).mean() * 100, p90=(x <= -90).mean() * 100, p10=(x < -10).mean() * 100,
                up=(x > 0).mean() * 100)


def fm(d):
    return (f"n {d['n']:3d} avg {d['avg']:+7.2f} med {d['med']:+7.2f} sd {d['sd']:6.2f} mean/sd {d['mpsd']:+.3f} "
            f"worst {d['worst']:+7.1f} lose>10% {d['p10']:3.0f}% lose>50% {d['p50']:3.0f}% lose>=90% {d['p90']:3.0f}% up {d['up']:.0f}%")


rows = []
for v in ('ATM', 'OTM5'):
    for smp, mm in [('DISC', m.qn <= 13), ('HOLD', m.qn >= 14), ('FULL', m.qn >= 0)]:
        x = m[(m.variant == v) & mm]
        a, b, cc = risk(x.net), risk(x.raw20), risk(x.v20)
        pr(f'{v:4s} {smp}: option  {fm(a)}')
        pr(f'          stock unhedged same signals {fm(b)}')
        pr(f'          stock vs Nifty same signals {fm(cc)}')
        lev = a['sd'] / b['sd']
        pr(f'          sd ratio option/stock {lev:.1f}x -> stock levered to the same sd: avg {lev * b["avg"]:+.2f} '
           f'(option {a["avg"]:+.2f}); option beta to stock move {np.polyfit(x.raw20, x.net, 1)[0]:.1f}')
        rows.append(dict(variant=v, sample=smp, **{f'opt_{k}': w for k, w in a.items()},
                         **{f'stk_{k}': w for k, w in b.items()}, lev=lev))
pd.DataFrame(rows).to_csv(f'{OUT}/options_risk.csv', index=False, float_format='%.4f')
open(f'{OUT}/s3_options.log', 'w').write('\n'.join(L) + '\n')
