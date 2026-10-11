#!/usr/bin/env python3
"""Discovery-only evaluation of the 35 candidates in candidates.txt (fade the over-reaction family).

HOLDOUT SEALED: every table is filtered to qn <= 13 BEFORE any return / forward price is read or computed.
Outputs: discovery_table.csv / .md, trades_discovery.csv, per_quarter_discovery.csv, finalists.txt, evaluate.log.
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.environ.get('LAB_ROOT', os.path.abspath(os.path.join(HERE, '..', '..')))  # scratch data folder
DATA = f'{SP}/sector_lab/data'
QMAX = 13
COST_A_RAW, COST_HEDGED = 0.17, 0.19

log = open(f'{HERE}/evaluate.log', 'w')


def out(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    log.write(s + '\n')


# ---------------------------------------------------------------- discovery rows only
f = pd.read_csv(f'{HERE}/features_fade.csv')
f = f[f.qn <= QMAX].reset_index(drop=True)
assert f.qn.max() <= QMAX and len(f) == 1808

oc = pd.read_csv(f'{SP}/perf/features/outcomes.csv')
oc = oc[oc.qn <= QMAX][['symbol', 'qn', 'three_day', 'tradable_B', 'raw_H5', 'nifty_H5', 'raw_H10', 'nifty_H10',
                        'raw_H20', 'nifty_H20']]
assert oc.qn.max() <= QMAX
f = f.merge(oc, on=['symbol', 'qn'], how='left', validate='1:1')
assert f.qn.max() <= QMAX

ses = pd.read_csv(f'{DATA}/sessions.csv')
days = ses.day.tolist()
T = len(days)
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
assert ret.index.tolist() == days
SYM = {s: j for j, s in enumerate(ret.columns)}
R = ret.to_numpy(float)
nifty = pd.read_csv(f'{DATA}/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])['Nifty 50'].to_numpy(float)
nret = np.r_[np.nan, nifty[1:] / nifty[:-1] - 1]

j = f.symbol.map(SYM).to_numpy(int)
k = f.i_react.to_numpy(int)
# the latest session any discovery outcome may touch: k+1+20 of the last discovery result
last_used = int((k + 21).max())
out(f'discovery rows {len(f)}; latest session touched {days[last_used]}; first holdout cutoff (features only) '
    f"{days[int(pd.read_csv(HERE + '/features_fade.csv').query('qn >= 14').i_cut.min())]}")


def fwd(entry, H):
    """stock and Nifty return (%) from close entry to close entry+H, discovery rows only."""
    st = np.full(len(f), np.nan)
    nf = np.full(len(f), np.nan)
    for n_, (jj, e) in enumerate(zip(j, entry)):
        w = R[e + 1:e + H + 1, jj]
        st[n_] = (np.prod(1 + np.nan_to_num(w)) - 1) * 100
        nf[n_] = (nifty[e + H] / nifty[e] - 1) * 100
    return st, nf


# ---------------------------------------------------------------- check vs outcomes.csv (entry k, H 5/10/20)
for H in (5, 10, 20):
    st, nf = fwd(k, H)
    m = f.tradable_B.fillna(False).astype(bool).to_numpy()
    d1 = np.nanmax(np.abs(st[m] - f[f'raw_H{H}'].to_numpy()[m]))
    d2 = np.nanmax(np.abs(nf[m] - f[f'nifty_H{H}'].to_numpy()[m]))
    out(f'check entry k H{H}: max |stock - raw_H| {d1:.2e}, max |nifty - nifty_H| {d2:.2e} over {m.sum()} tradable')
    assert d1 < 1e-3 and d2 < 1e-3

# ---------------------------------------------------------------- trade A
ic = f.i_cut.to_numpy(int)
ip1 = f.i_p1.to_numpy(int)
three_chk = np.array([np.nansum(R[a + 1:b + 1, jj]) * 100 for a, b, jj in zip(ic, ip1, j)])
mA = f.three_day.notna().to_numpy()
out(f'check three_day = sum of 3 daily returns: max diff {np.max(np.abs(three_chk[mA] - f.three_day[mA])):.2e}')
assert ((ip1 - ic) == 3).all()
f['nifty3d'] = [np.sum(nret[a + 1:b + 1]) * 100 for a, b in zip(ic, ip1)]

# ---------------------------------------------------------------- outcomes per window (B)
WIN = {}
trB = f.tradable_B.fillna(False).astype(bool).to_numpy()
trk1 = trB & f.traded_k1.astype(bool).to_numpy()
for ent in ('k', 'k1'):
    entry = k if ent == 'k' else k + 1
    for H in (1, 5, 20):
        st, nf = fwd(entry, H)
        elig = trB if ent == 'k' else trk1
        WIN[(ent, H)] = dict(stock=st, nifty=nf, short=-(st - nf) - COST_HEDGED, elig=elig)

# ---------------------------------------------------------------- candidates
XN, W = f.XN, f.XN > 4
S = {
    'FAILGAP3': (f.rx_gap_pct > 3) & (f.close_lt_open_k == 1),
    'W_WEAKCLOSE': W & (f.clv_k < 2 / 3),
    'W_RSI75': W & (f.rx_rsi14 > 75),
    'W_RUNUP': W & (f.lag21 > 5),
    'W_STRETCH': W & (f.rx_close_vs_sma50_pct > 15),
    'UP_BAD': (XN > 2) & (f.BAD == True),
    'UP_PATDOWN': (XN > 2) & (f.rq_pat_yoy_pct < 0),
    'BIGJUMP': XN > 8,
    'W_LOWDELP': W & (f.DPK < -20),
    'W_LOWDELQ': W & (f.DQK < 2),
    'RUN5_8': f.r5vsN_cut > 8,
    'RUN5_5': f.r5vsN_cut > 5,
}
S = {a: b.fillna(False).astype(bool).to_numpy() for a, b in S.items()}
CANDS = [
    ('B01', 'FAILGAP3', 'k', 1), ('B02', 'FAILGAP3', 'k', 5), ('B03', 'FAILGAP3', 'k', 20), ('B04', 'FAILGAP3', 'k1', 5),
    ('B05', 'W_WEAKCLOSE', 'k', 1), ('B06', 'W_WEAKCLOSE', 'k', 5), ('B07', 'W_WEAKCLOSE', 'k', 20),
    ('B08', 'W_WEAKCLOSE', 'k1', 5),
    ('B09', 'W_RSI75', 'k', 1), ('B10', 'W_RSI75', 'k', 5), ('B11', 'W_RSI75', 'k', 20),
    ('B12', 'W_RUNUP', 'k', 1), ('B13', 'W_RUNUP', 'k', 5), ('B14', 'W_RUNUP', 'k', 20),
    ('B15', 'W_STRETCH', 'k', 1), ('B16', 'W_STRETCH', 'k', 5), ('B17', 'W_STRETCH', 'k', 20),
    ('B18', 'UP_BAD', 'k', 1), ('B19', 'UP_BAD', 'k', 5), ('B20', 'UP_BAD', 'k', 20),
    ('B21', 'UP_PATDOWN', 'k', 1), ('B22', 'UP_PATDOWN', 'k', 5), ('B23', 'UP_PATDOWN', 'k', 20),
    ('B24', 'BIGJUMP', 'k', 1), ('B25', 'BIGJUMP', 'k', 5), ('B26', 'BIGJUMP', 'k', 20),
    ('B27', 'W_LOWDELP', 'k1', 1), ('B28', 'W_LOWDELP', 'k1', 5), ('B29', 'W_LOWDELP', 'k1', 20),
    ('B30', 'W_LOWDELQ', 'k1', 1), ('B31', 'W_LOWDELQ', 'k1', 5), ('B32', 'W_LOWDELQ', 'k1', 20),
    ('A01', 'RUN5_8', 'A', 'raw'), ('A02', 'RUN5_8', 'A', 'hedged'), ('A03', 'RUN5_5', 'A', 'hedged'),
]
assert len(CANDS) == 35

qn = f.qn.to_numpy()
rows, trades, perq = [], [], []
for cid, sig, ent, H in CANDS:
    if ent == 'A':
        elig = mA
        st = f.three_day.to_numpy()
        nf = f.nifty3d.to_numpy()
        short = -st - COST_A_RAW if H == 'raw' else -(st - nf) - COST_HEDGED
        win = f'A {H}'
    else:
        w_ = WIN[(ent, H)]
        elig, st, nf, short = w_['elig'], w_['stock'], w_['nifty'], w_['short']
        win = f"B entry {'k' if ent == 'k' else 'k+1'} H{H}"
    base = short[elig].mean()
    m = elig & S[sig]
    s = short[m]
    n = int(m.sum())
    q = qn[m]
    pq = pd.Series(s).groupby(q).mean()
    wo5 = np.sort(s)[:-5].mean() if n > 5 else np.nan
    h1 = s[q <= 6].mean() if (q <= 6).any() else np.nan
    h2 = s[q >= 7].mean() if (q >= 7).any() else np.nan
    tq = pq.mean() / (pq.std(ddof=1) / np.sqrt(len(pq))) if len(pq) > 2 else np.nan
    rows.append(dict(id=cid, signal=sig, window=win, n=n, quarters=int(pd.Series(q).nunique()),
                     avg_ret_raw=st[m].mean(), avg_ret_vsN=(st - nf)[m].mean(), short_net=s.mean(),
                     short_wo_best5=wo5, median_short=np.median(s) if n else np.nan,
                     hit=(s > 0).mean() if n else np.nan,
                     q_pos=int((pq > 0).sum()), half1=h1, n_h1=int((q <= 6).sum()), half2=h2,
                     n_h2=int((q >= 7).sum()), t_quarters=tq, base_short=base, vs_base=s.mean() - base))
    for qq, v in pq.items():
        perq.append(dict(id=cid, qn=qq, n=int((q == qq).sum()), short_net=v))
    tt = f.loc[m, ['symbol', 'qn', 'quarter', 'XN']].copy()
    tt['id'] = cid
    tt['stock_ret'] = st[m]
    tt['nifty_ret'] = nf[m]
    tt['short_net'] = s
    trades.append(tt)

tab = pd.DataFrame(rows)
assert int(np.max([t.qn.max() for t in trades if len(t)])) <= QMAX
tab['c1_n_q'] = (tab.n >= 40) & (tab.quarters >= 7)
tab['c2_halves'] = (tab.half1 > 0) & (tab.half2 > 0)
tab['c3_base'] = tab.vs_base >= 0.5
tab['qualifies'] = tab.c1_n_q & tab.c2_halves & tab.c3_base
tab.to_csv(f'{HERE}/discovery_table.csv', index=False)
pd.concat(trades).to_csv(f'{HERE}/trades_discovery.csv', index=False)
pd.DataFrame(perq).to_csv(f'{HERE}/per_quarter_discovery.csv', index=False)

# base shorts
out('\nBASE SHORT per window (all eligible discovery results):')
for (ent, H), w_ in WIN.items():
    e = w_['elig']
    out(f"  B entry {'k' if ent == 'k' else 'k+1'} H{H:2d}: n {e.sum()}, stock vs Nifty {(w_['stock'] - w_['nifty'])[e].mean():+.2f}%,"
        f" short net {w_['short'][e].mean():+.2f}%")
out(f"  A raw:    n {mA.sum()}, three_day {f.three_day[mA].mean():+.2f}%, short net {(-f.three_day[mA] - 0.17).mean():+.2f}%")
out(f"  A hedged: n {mA.sum()}, three_day - nifty3d {(f.three_day - f.nifty3d)[mA].mean():+.2f}%, short net "
    f"{(-(f.three_day - f.nifty3d)[mA] - 0.19).mean():+.2f}%")


def fmt(x, d=2):
    return '' if pd.isna(x) else f'{x:+.{d}f}'


md = ['| id | signal | window | n | qtrs | avg ret raw | avg ret vs Nifty | short net | w/o best 5 | qtrs short+ / with trades | half 0-6 (n) | half 7-13 (n) | base short | vs base | qualifies |',
      '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
for r in tab.itertuples():
    md.append(f'| {r.id} | {r.signal} | {r.window} | {r.n} | {r.quarters} | {fmt(r.avg_ret_raw)} | {fmt(r.avg_ret_vsN)} | '
              f'{fmt(r.short_net)} | {fmt(r.short_wo_best5)} | {r.q_pos} / {r.quarters} | {fmt(r.half1)} ({r.n_h1}) | '
              f'{fmt(r.half2)} ({r.n_h2}) | {fmt(r.base_short)} | {fmt(r.vs_base)} | '
              f"{'YES' if r.qualifies else 'no'} |")
open(f'{HERE}/discovery_table.md', 'w').write('\n'.join(md) + '\n')
out('\n' + '\n'.join(md))

# ---------------------------------------------------------------- finalists (rule fixed in candidates.txt)
qual = tab[tab.qualifies].sort_values('short_wo_best5', ascending=False)
fin = []
for r in qual.itertuples():
    if len(fin) == 2:
        break
    if fin and r.signal == fin[0].signal:
        continue
    fin.append(r)
out('\nQUALIFIERS:', qual[['id', 'signal', 'window', 'n', 'short_net', 'short_wo_best5', 'vs_base']].to_string()
    if len(qual) else 'none')
txt = ['FINALISTS (rule in candidates.txt): ' + (', '.join(f'{r.id} {r.signal} {r.window}' for r in fin) if fin else 'NONE')]
for c in ('c1_n_q', 'c2_halves', 'c3_base'):
    txt.append(f'  candidates passing {c}: {int(tab[c].sum())} of 35')
open(f'{HERE}/finalists.txt', 'w').write('\n'.join(txt) + '\n')
out('\n'.join(txt))
log.close()
