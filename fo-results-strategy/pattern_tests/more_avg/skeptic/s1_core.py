#!/usr/bin/env python3
"""Skeptic review, part 1: rebuild baseline / F3 (hold 60) / F4 (pullback + hold 60) trades from raw data with my own
code, then concentration, survivorship, calendar-time portfolio (Newey-West) and next-results-in-window checks.
Holdout has already been opened by the holdout evaluator; this is a post-holdout review."""
import numpy as np
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f'{SP}/more_avg/skeptic'
D = f'{SP}/sector_lab/data'

ses = pd.read_csv(f'{D}/sessions.csv')
days = ses.day.tolist()
T = len(days)
LAST = T - 1
ret = pd.read_csv(f'{D}/returns.csv', index_col=0)
assert ret.index.tolist() == days
SYM = {s: j for j, s in enumerate(ret.columns)}
R = ret.to_numpy(float)
NIF = pd.read_csv(f'{D}/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])['Nifty 50']
assert NIF.index.tolist() == days
N = NIF.to_numpy(float)
NR = np.r_[np.nan, N[1:] / N[:-1] - 1]

f = pd.read_csv(f'{SP}/tafa/C_post_results/features.csv',
                usecols=['symbol', 'quarter', 'qn', 'reaction_day', 'i_cut', 'i_rd', 'i_react', 'XN', 'cut_rsi14'])
ev = pd.read_csv(f'{D}/events.csv', usecols=['symbol', 'qn', 'in_fo', 'i_rd', 'i_react'])

COST, COST_RAW = 0.19, 0.17


def fwd(sym, k, H):
    """(stock %, nifty %, ok) for buy close k, sell close k+H; baseline tradability rule."""
    j = SYM[sym]
    if k + H + 1 > LAST:
        return np.nan, np.nan, False
    r = R[k + 1:k + H + 2, j]
    if np.isnan(r).sum() > 2:
        return np.nan, np.nan, False
    rr = np.nan_to_num(R[k + 1:k + H + 1, j])
    return (np.prod(1 + rr) - 1) * 100, (N[k + H] / N[k] - 1) * 100, True


rows = []
for x in f.itertuples(index=False):
    k = int(x.i_react)
    d = dict(symbol=x.symbol, qn=x.qn, k=k, XN=x.XN, rsi=x.cut_rsi14)
    for H in (20, 30, 40, 60):
        s, n, ok = fwd(x.symbol, k, H)
        d[f's{H}'], d[f'n{H}'], d[f'ok{H}'] = s, n, ok
        d[f'v{H}'] = s - n - COST if ok else np.nan
    # pullback entry
    j = SYM[x.symbol]
    e = None
    for t in range(k + 1, min(k + 6, T)):
        if np.isfinite(R[t, j]) and R[t, j] < 0:
            e = t
            break
    d['e'] = e
    if e is not None:
        s, n, ok = fwd(x.symbol, e, 60)
        d['vPB'] = s - n - COST if ok else np.nan
    else:
        d['vPB'] = np.nan
    rows.append(d)
P = pd.DataFrame(rows)
P['W'] = P.XN > 4
P['BASE'] = P.W & (P.rsi > 50)
P['HOLD'] = P.qn >= 14
P.to_csv(f'{OUT}/panel_skeptic.csv', index=False, float_format='%.6g')

L = []


def pr(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    L.append(s)


def stats(v):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    s = np.sort(v)[::-1]
    lo, hi = np.percentile(v, [5, 95])
    lo1, hi1 = np.percentile(v, [1, 99])
    return dict(n=len(v), avg=v.mean(), med=np.median(v), wo5=s[5:].mean(), wo10=s[10:].mean(),
                win5=np.clip(v, lo, hi).mean(), win1=np.clip(v, lo1, hi1).mean(), up=(v > 0).mean() * 100)


def fmt(d):
    return (f"n {d['n']:3d} avg {d['avg']:+.2f} med {d['med']:+.2f} wo5 {d['wo5']:+.2f} wo10 {d['wo10']:+.2f} "
            f"wins5-95 {d['win5']:+.2f} wins1-99 {d['win1']:+.2f} up {d['up']:.0f}%")


B = P[P.BASE]
pr('=== 0. Rebuild check (own code from returns.csv / index_close.csv; features.csv XN & cut_rsi14) ===')
for nm, m in [('disc', ~B.HOLD), ('hold', B.HOLD), ('full', B.qn >= 0)]:
    b = B[m]
    pr(f'{nm}: BASE H20 {fmt(stats(b.v20))} | F3 H60 {fmt(stats(b.v60))} | F4 PB60 n {b.vPB.notna().sum()} avg {b.vPB.mean():+.2f}')
pr('(holdout evaluator: BASE hold 110 +2.16; F3 hold 93 +5.10 wo5 +3.11; F4 hold 92 +4.43; disc F3 122 +4.64)')

H3 = B[B.HOLD & B.v60.notna()].copy()
H3['d'] = H3.v60 - H3.v20
H4 = B[B.HOLD & B.vPB.notna()].copy()
H4['d'] = H4.vPB - H4.v20

pr('\n=== 1. Concentration in the HOLDOUT ===')
for nm, h, col in [('F3 H60', H3, 'v60'), ('F4 PB60', H4, 'vPB')]:
    pr(f'{nm}: {fmt(stats(h[col]))}')
    pr(f'   baseline H20 same signals: {fmt(stats(h.v20))}')
    pr(f'   paired diff (finalist - base): {fmt(stats(h.d))}')
    top = h.sort_values(col, ascending=False).head(10)
    pr('   top 10: ' + ', '.join(f'{r.symbol} q{r.qn} {getattr(r, col):+.1f}' for r in top.itertuples()))
    tot = h[col].sum()
    pr(f'   share of total from best 5: {top[col].head(5).sum() / tot * 100:.0f}%, best 10: {top[col].sum() / tot * 100:.0f}%')
    pr('   leave-one-quarter-out (avg | paired diff):')
    for q in sorted(h.qn.unique()):
        g = h[h.qn != q]
        pr(f'     drop qn {q}: n {len(g):3d} avg {g[col].mean():+.2f} | diff {g.d.mean():+.2f}  (quarter n {int((h.qn == q).sum())})')
    qm = h.groupby('qn')[col].mean()
    qd = h.groupby('qn').d.mean()
    pr(f'   quarter means: ' + ', '.join(f'{q}:{v:+.2f}' for q, v in qm.items()))
    pr(f'   equal-weight quarters avg {qm.mean():+.2f}; quarter-mean of paired diff {qd.mean():+.2f}, '
       f't {qd.mean() / (qd.std(ddof=1) / np.sqrt(len(qd))):.2f}, quarters with diff>0 {int((qd > 0).sum())}/{len(qd)}')
    # without best 5 / 10 on BOTH: remove finalist's best trades and same signals' baseline
    for kx in (5, 10):
        ids = h.sort_values(col, ascending=False).index[kx:]
        pr(f'   drop finalist best {kx} signals: finalist {h.loc[ids, col].mean():+.2f} vs base same {h.loc[ids, "v20"].mean():+.2f}'
           f'  diff {h.loc[ids, "d"].mean():+.2f}')
    # drop best 10 paired diffs
    sd = np.sort(h.d.to_numpy())[::-1]
    pr(f'   paired diff without its own best 5 / 10: {sd[5:].mean():+.2f} / {sd[10:].mean():+.2f}; median {np.median(sd):+.2f}')

pr('\n=== 1b. Same checks in DISCOVERY (for comparison) ===')
D3 = B[~B.HOLD & B.v60.notna()].copy()
D3['d'] = D3.v60 - D3.v20
pr(f'F3 disc: {fmt(stats(D3.v60))}; base same: {fmt(stats(D3.v20))}; diff {fmt(stats(D3.d))}')
ex23 = ~D3.k.map(lambda k: days[k][:4] == '2023')
pr(f'F3 disc ex-2023 reaction days: n {ex23.sum()} avg {D3.v60[ex23].mean():+.2f} base {D3.v20[ex23].mean():+.2f}')

# ---------------------------------------------------------------- survivorship
pr('\n=== 2. Survivorship: early F&O members vs later joiners ===')
fo = ev[ev.in_fo == True]
early1 = set(fo[fo.qn <= 1].symbol)
early13 = set(fo[fo.qn <= 13].symbol)
for nm, S in [('in F&O by qn 1', early1), ('in F&O by qn 13 (pre-holdout)', early13)]:
    for smp, h in [('HOLDOUT', H3), ('DISC', D3), ('FULL', pd.concat([D3, H3]))]:
        m = h.symbol.isin(S)
        a, b = h[m], h[~m]
        pr(f'{nm:30s} {smp:7s} early n {len(a):3d} F3 {a.v60.mean():+.2f} base {a.v20.mean():+.2f} diff {a.d.mean():+.2f} '
           f'| joiners n {len(b):3d} F3 {b.v60.mean():+.2f} base {b.v20.mean():+.2f} diff {b.d.mean():+.2f}')
# generic drift of all results by group, holdout, H60 vs H20
A = P[P.HOLD & P.v60.notna()]
for nm, S in [('by qn 1', early1), ('by qn 13', early13)]:
    m = A.symbol.isin(S)
    pr(f'all F&O results holdout, {nm}: early n {m.sum()} H20 {A.v20[m].mean():+.2f} H60 {A.v60[m].mean():+.2f} | '
       f'joiners n {(~m).sum()} H20 {A.v20[~m].mean():+.2f} H60 {A.v60[~m].mean():+.2f}')

# ---------------------------------------------------------------- drift-adjusted: vs results with same RSI>50 but not winners
pr('\n=== 3. Is the 21-60 extension specific to winners? (holdout, same-quarter means) ===')
grp = {'BASE (W & RSI>50)': P.BASE, 'winners RSI<=50': P.W & (P.rsi <= 50), 'non-winners RSI>50': ~P.W & (P.rsi > 50),
       'non-winners RSI<=50': ~P.W & (P.rsi <= 50), 'all F&O results': P.qn >= 0}
for smp, mm in [('DISC', ~P.HOLD), ('HOLD', P.HOLD)]:
    for nm, g in grp.items():
        x = P[g & mm & P.v60.notna()]
        pr(f'{smp} {nm:22s} n {len(x):4d} H20 {x.v20.mean():+.2f} H60 {x.v60.mean():+.2f} ext(H60-H20) {(x.v60 - x.v20).mean():+.2f}')

# ---------------------------------------------------------------- next results inside the window
pr('\n=== 4. Does the 60-session window include the NEXT results reaction? ===')
evs = ev.sort_values('i_react')
nxt = {}
for s, g in evs.groupby('symbol'):
    nxt[s] = g.i_react.to_numpy()
for nm, h in [('HOLD', H3), ('DISC', D3)]:
    inc = []
    for r in h.itertuples():
        a = nxt[r.symbol]
        inc.append(bool(((a > r.k) & (a <= r.k + 60)).any()))
    inc = np.array(inc)
    pr(f'{nm}: {inc.sum()}/{len(h)} windows contain the next reaction day; F3 avg with {h.v60[inc].mean():+.2f}, without '
       f'{h.v60[~inc].mean():+.2f}; base H20 with {h.v20[inc].mean():+.2f}, without {h.v20[~inc].mean():+.2f}')

# ---------------------------------------------------------------- calendar-time portfolio, Newey-West
pr('\n=== 5. Calendar-time portfolios (equal weight across open positions, daily stock - Nifty, cash = 0) ===')


def port(trs, a, b):
    """trs: list of (sym, k). Active on days k+a..k+b inclusive. returns daily mean excess and count."""
    S = np.zeros(T)
    C = np.zeros(T)
    for s, k in trs:
        j = SYM[s]
        lo, hi = k + a, min(k + b, LAST)
        x = np.nan_to_num(R[lo:hi + 1, j]) - NR[lo:hi + 1]
        S[lo:hi + 1] += x
        C[lo:hi + 1] += 1
    m = np.where(C > 0, S / np.maximum(C, 1), 0.0)
    return m * 100, C


def nw(x, lag):
    x = np.asarray(x, float)
    n = len(x)
    mu = x.mean()
    e = x - mu
    v = e @ e / n
    for l in range(1, lag + 1):
        w = 1 - l / (lag + 1)
        v += 2 * w * (e[l:] @ e[:-l]) / n
    return mu, mu / np.sqrt(v / n)


# universe drift: stocks in F&O at day t (in_fo of latest result with i_rd <= t)
U = np.zeros(T)
UC = np.zeros(T)
for s, g in ev.sort_values('i_rd').groupby('symbol'):
    if s not in SYM:
        continue
    j = SYM[s]
    g = g.reset_index(drop=True)
    ird = g.i_rd.to_numpy(int)
    flag = g.in_fo.fillna(False).to_numpy(bool)
    for i in range(len(g)):
        lo = ird[i] + 1
        hi = ird[i + 1] if i + 1 < len(g) else LAST
        if not flag[i]:
            continue
        r = R[lo:hi + 1, j]
        ok = np.isfinite(r)
        idx = np.arange(lo, hi + 1)[ok]
        U[idx] += r[ok] - NR[idx]
        UC[idx] += 1
UNIV = np.where(UC > 0, U / np.maximum(UC, 1), 0.0) * 100

for smp, h in [('HOLDOUT', H3), ('DISC', D3)]:
    tr = list(zip(h.symbol, h.k))
    f3, c3 = port(tr, 1, 60)
    b0, c0 = port(tr, 1, 20)
    ex, ce = port(tr, 21, 60)
    span = np.where((c3 > 0) | (c0 > 0))[0]
    lo, hi = span.min(), span.max()
    sl = slice(lo, hi + 1)
    nd = hi - lo + 1
    for nm, ser in [('F3 (days 1-60)', f3), ('BASE same signals (days 1-20)', b0), ('F3 - BASE', f3 - b0),
                    ('extension days 21-60 only', ex)]:
        mu, t20 = nw(ser[sl], 20)
        _, t60 = nw(ser[sl], 60)
        pr(f'{smp} {nm:32s} days {nd} mean/day {mu:+.4f}  per 20d {mu * 20:+.2f}  NW t(lag20) {t20:+.2f} t(lag60) {t60:+.2f}')
    # extension vs universe drift on days extension is active
    act = (ce > 0)
    act[:lo] = False
    act[hi + 1:] = False
    xs = ex[act] - UNIV[act]
    mu, t20 = nw(xs, 20)
    _, t60 = nw(xs, 60)
    pr(f'{smp} extension minus EW F&O-universe excess, active days only ({act.sum()}): per 20d {mu * 20:+.2f} '
       f'NW t20 {t20:+.2f} t60 {t60:+.2f}; universe excess itself per 20d {UNIV[act].mean() * 20:+.2f}')
    act0 = (c0 > 0)
    act0[:lo] = False
    act0[hi + 1:] = False
    xs = b0[act0] - UNIV[act0]
    mu, t20 = nw(xs, 20)
    pr(f'{smp} base days 1-20 minus universe, active days ({act0.sum()}): per 20d {mu * 20:+.2f} NW t20 {t20:+.2f}')
    pr(f'{smp} mean open positions: F3 {c3[sl][c3[sl] > 0].mean():.1f}, base {c0[sl][c0[sl] > 0].mean():.1f}; '
       f'days with F3 open {int((c3[sl] > 0).sum())}, base open {int((c0[sl] > 0).sum())}')

open(f'{OUT}/s1_core.log', 'w').write('\n'.join(L) + '\n')
