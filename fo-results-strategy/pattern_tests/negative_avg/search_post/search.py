#!/usr/bin/env python3
"""DISCOVERY-ONLY outcomes for the 42 candidates in candidates.txt (family "losers keep falling", trade B, short).

Holdout (qn >= 14) rows are dropped right after reading the features and BEFORE any price lookup; an assert guards
every outcome array. Writes discovery_table.csv / .md, trades_discovery.csv, per_quarter_discovery.csv, base.csv,
finalists.txt, search.log into this folder.
"""
import hashlib
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
DATA = f'{SP}/sector_lab/data'
DISC_MAX = 13
HALF1_MAX = 6
COST_H, COST_RAW = 0.19, 0.17
NDRAW = 10000
SEED = 20261011
LOG = open(f'{HERE}/search.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')
    LOG.flush()


# pre-registration check
want = {l.split()[1]: l.split()[0] for l in open(f'{HERE}/prereg.sha256') if len(l.split()) == 2}
for fn, h in want.items():
    got = hashlib.sha256(open(f'{HERE}/{fn}', 'rb').read()).hexdigest()
    assert got == h, f'{fn} changed after pre-registration'
P('prereg hashes OK:', want)

# ---------------------------------------------------------------- features, DISCOVERY ONLY
fa = pd.read_csv(f'{HERE}/features_all.csv')
f = fa[fa.qn <= DISC_MAX].copy().reset_index(drop=True)
del fa
assert f.qn.max() <= DISC_MAX
P('discovery results:', len(f), 'quarters', f.qn.nunique())

# ---------------------------------------------------------------- prices
ses = pd.read_csv(f'{DATA}/sessions.csv')
days = ses.day.tolist()
DIX = {d: i for i, d in enumerate(days)}
NS = len(days)
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
assert ret.index.tolist() == days
SYM = {s: j for j, s in enumerate(ret.columns)}
R = ret.to_numpy(float)
PX = np.cumprod(1.0 + np.nan_to_num(R), axis=0)
CVALID = np.cumsum(~np.isnan(R), axis=0)
NIFTY = pd.read_csv(f'{DATA}/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])['Nifty 50'].to_numpy(float)
px = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'open', 'close'])
px = px[px.symbol.isin(SYM)]
px['i'] = px.day.map(DIX)
px = px.dropna(subset=['i'])
px['i'] = px.i.astype(int)
PKO = px.set_index(['symbol', 'i'])

J = f.symbol.map(SYM).to_numpy(int)
K = f.i_react.astype(int).to_numpy()
XN_OK = f.XN.notna().to_numpy()


def outcome(entry, H):
    """stock %, nifty % and tradable flag for every discovery row."""
    n = len(f)
    stock, nif = np.full(n, np.nan), np.full(n, np.nan)
    ok = XN_OK.copy()
    if entry == 'E0':
        e, x = K, K + H
    elif entry == 'E1':
        e, x = K + 1, K + 1 + H
    elif entry == 'E1o':
        e, x = K + 1, K + H
    ok &= x <= NS - 1
    e_, x_ = np.where(ok, e, 0), np.where(ok, x, 0)
    if entry in ('E1', 'E1o'):
        ok &= np.isfinite(R[e_, J])                         # traded on k+1
    blanks = (x_ - e_) - (CVALID[x_, J] - CVALID[e_, J])     # blank returns in e+1..x
    ok &= blanks <= 2
    if entry == 'E1o':
        oc = PKO.reindex(list(zip(f.symbol, e_)))
        o_, c_ = oc.open.to_numpy(float), oc.close.to_numpy(float)
        ok &= np.isfinite(o_) & np.isfinite(c_) & (o_ > 0)
        with np.errstate(invalid='ignore', divide='ignore'):
            stock = (c_ / o_ * PX[x_, J] / PX[e_, J] - 1) * 100
        nif = (NIFTY[x_] / NIFTY[K] - 1) * 100              # hedge leg from close k (no Nifty open in data)
    else:
        stock = (PX[x_, J] / PX[e_, J] - 1) * 100
        nif = (NIFTY[x_] / NIFTY[e_] - 1) * 100
    stock[~ok] = np.nan
    nif[~ok] = np.nan
    return stock, nif, ok


WINDOWS = [('E0', 5), ('E0', 10), ('E0', 20), ('E0', 40), ('E1', 20), ('E1', 40), ('E1o', 20)]
OUT = {w: outcome(*w) for w in WINDOWS}

# cross-check E0 H5/10/20 against outcomes.csv (discovery rows only; holdout rows dropped on read)
oc = pd.read_csv(f'{SP}/perf/features/outcomes.csv')
oc = oc[oc.qn <= DISC_MAX]
chk = f[['symbol', 'qn']].merge(oc, on=['symbol', 'qn'], how='left', validate='1:1')
for H in (5, 10, 20):
    s, n_, ok = OUT[('E0', H)]
    a = s - n_
    b = (chk[f'raw_H{H}'] - chk[f'nifty_H{H}']).to_numpy(float)
    both = np.isfinite(a) & np.isfinite(b)
    P(f'check E0 H{H} vs outcomes.csv: n both {both.sum()}, mine only {(np.isfinite(a) & ~np.isfinite(b)).sum()}, '
      f'theirs only {(~np.isfinite(a) & np.isfinite(b)).sum()}, max abs diff {np.nanmax(np.abs(a[both] - b[both])):.2e}')
del oc, chk

# ---------------------------------------------------------------- signals (exactly candidates.txt)
XN = f.XN
L2, L4, L6 = XN < -2, XN < -4, XN < -6
W = XN > 4
nonW = XN <= 4
B50 = f.rx_close_vs_sma50_pct < 0
B200 = f.rx_close_vs_sma200_pct < 0
RSIc = f.cut_rsi14
BRK = f.BRKDN_VOL.astype(bool)
BAD = f.BAD.astype(bool)
GOOD_B50 = f.GOOD.astype(bool) & f.BELOW50.astype(bool)
CLV = f.CLV_k <= 0.25
SECD = f.SEC21_k < 0
DRIFT1 = (f.n_drift_4_B >= 3) & (f.mean_drift_4_B < 0)
DRIFT2 = (f.n_drift_4_B == 4) & (f.mean_drift_4_B < 0) & (f.n_pos_drift_4_B <= 1)
VS252 = f.vsN_252_B < 0
SBK = (f.B_dP5 < 0) & (f.B_dOI5 > 10)
OIUP = f.B_dOI1 > 5
DQK3 = f.DQK >= 3
FT1 = f.FT1 < 0
SBC = (f.A_dP5 < 0) & (f.A_dOI5 > 10)

C = [
    ('C01', 'L4', L4, 'E0', 5), ('C02', 'L4', L4, 'E0', 10), ('C03', 'L4 [C]', L4, 'E0', 20),
    ('C04', 'L4', L4, 'E0', 40), ('C05', 'L2', L2, 'E0', 20), ('C06', 'L6', L6, 'E0', 20),
    ('C07', 'L4', L4, 'E1', 20), ('C08', 'L4', L4, 'E1o', 20),
    ('C09', 'L4 & RSIcut<50', L4 & (RSIc < 50), 'E0', 20), ('C10', 'L4 & B50', L4 & B50, 'E0', 20),
    ('C11', 'L4 & B200', L4 & B200, 'E0', 20), ('C12', 'L4 & B50 & B200', L4 & B50 & B200, 'E0', 20),
    ('C13', 'L4 & BRKDN_VOL', L4 & BRK, 'E0', 20), ('C14', 'L4 & BAD', L4 & BAD, 'E0', 20),
    ('C15', 'L4 & CLV<=0.25', L4 & CLV, 'E0', 20), ('C16', 'L4 & SEC21<0', L4 & SECD, 'E0', 20),
    ('C17', 'L4 & DRIFT-', L4 & DRIFT1, 'E0', 20), ('C18', 'L4 & VSN252-', L4 & VS252, 'E0', 20),
    ('C19', 'L4 & BAD & B50', L4 & BAD & B50, 'E0', 20), ('C20', 'L6 & B200', L6 & B200, 'E0', 20),
    ('C21', 'L2 & B200 & VSN252-', L2 & B200 & VS252, 'E0', 20),
    ('C22', 'L4 & B200', L4 & B200, 'E0', 40), ('C23', 'L4 & B50', L4 & B50, 'E0', 40),
    ('C24', 'L4 & BRKDN_VOL', L4 & BRK, 'E0', 40), ('C25', 'L4 & B50 & B200', L4 & B50 & B200, 'E0', 10),
    ('C26', 'L4 & SB_k', L4 & SBK, 'E1', 20), ('C27', 'L4 & SB_k', L4 & SBK, 'E1o', 20),
    ('C28', 'L4 & OIUP_k', L4 & OIUP, 'E1', 20), ('C29', 'L4 & DQK3', L4 & DQK3, 'E1', 20),
    ('C30', 'L4 & FT1', L4 & FT1, 'E1', 20), ('C31', 'L4 & SB_k', L4 & SBK, 'E1', 40),
    ('C32', 'GOOD & BELOW50 [C]', GOOD_B50, 'E0', 20), ('C33', 'GOOD & BELOW50', GOOD_B50, 'E0', 40),
    ('C34', 'GOOD & BELOW50 & XN<0', GOOD_B50 & (XN < 0), 'E0', 20),
    ('C35', 'W & SB_cut [C]', W & SBC, 'E0', 20), ('C36', 'W & RSIcut<=50 [C]', W & (RSIc <= 50), 'E0', 20),
    ('C37', 'nonW & RSIcut<50 [C]', nonW & (RSIc < 50), 'E0', 20),
    ('C38', 'nonW & RSIcut<50 & B50 & B200', nonW & (RSIc < 50) & B50 & B200, 'E0', 20),
    ('C39', 'XN<0 & B200 & VSN252-', (XN < 0) & B200 & VS252, 'E0', 20),
    ('C40', 'XN<0 & B200 & VSN252-', (XN < 0) & B200 & VS252, 'E0', 40),
    ('C41', 'DRIFT-- (any reaction)', DRIFT2, 'E0', 20), ('C42', 'BAD & BRKDN_VOL [C]', BAD & BRK, 'E0', 20),
]
assert len(C) == 42 and len({c[0] for c in C}) == 42
P('candidates:', len(C))

QN = f.qn.to_numpy()
rng = np.random.default_rng(SEED)


def short_net(w):
    s, n_, ok = OUT[w]
    return -(s - n_) - COST_H, ok


# ---------------------------------------------------------------- base short per window
base_rows = []
BASE = {}
for w in WINDOWS:
    sn, ok = short_net(w)
    BASE[w] = sn[ok].mean()
    s, n_, _ = OUT[w]
    base_rows.append(dict(entry=w[0], H=w[1], n=int(ok.sum()), avg_stock=np.nanmean(s[ok]),
                          avg_vsN=np.nanmean((s - n_)[ok]), short_net=sn[ok].mean(),
                          short_net_h1=sn[ok & (QN <= HALF1_MAX)].mean(), short_net_h2=sn[ok & (QN > HALF1_MAX)].mean()))
base = pd.DataFrame(base_rows)
base.to_csv(f'{HERE}/base.csv', index=False, float_format='%.4f')
P('\nBASE SHORT (all tradable discovery results):\n' + base.round(3).to_string(index=False))


def luck_p(sel, sn, ok, actual):
    """one-sided: share of random same-size per-quarter picks (from the window's tradable pool) with mean >= actual."""
    tot = np.zeros(NDRAW)
    ntot = 0
    for q in np.unique(QN[sel]):
        pool = sn[ok & (QN == q)]
        m = int((sel & (QN == q)).sum())
        r = rng.random((NDRAW, len(pool)))
        idx = np.argpartition(r, m - 1, axis=1)[:, :m] if m < len(pool) else np.tile(np.arange(len(pool)), (NDRAW, 1))
        tot += pool[idx].sum(1)
        ntot += m
    return (1 + (tot / ntot >= actual - 1e-12).sum()) / (1 + NDRAW)


rows, trades, perq = [], [], []
for cid, name, sig, entry, H in C:
    w = (entry, H)
    s, n_, ok = OUT[w]
    sn, _ = short_net(w)
    sel = sig.fillna(False).to_numpy(bool) & ok
    assert QN[sel].max() <= DISC_MAX
    x = sn[sel]
    n = len(x)
    srt = np.sort(x)[::-1]
    wo5 = srt[5:].mean() if n > 5 else np.nan
    qs = pd.Series(x).groupby(QN[sel]).mean()
    h1 = x[QN[sel] <= HALF1_MAX]
    h2 = x[QN[sel] > HALF1_MAX]
    tq = qs.mean() / (qs.std(ddof=1) / np.sqrt(len(qs))) if len(qs) > 1 else np.nan
    lp = luck_p(sel, sn, ok, x.mean()) if n else np.nan
    raw_short = (-s[sel] - COST_RAW)
    elig_n = (n >= 40) and (len(qs) >= 7)
    elig_h = (len(h1) > 0 and h1.mean() > 0) and (len(h2) > 0 and h2.mean() > 0)
    elig_b = (x.mean() - BASE[w]) >= 0.5
    reason = ','.join(r for r, okk in (('n/quarters', elig_n), ('halves', elig_h), ('vs base<0.5', elig_b)) if not okk)
    rows.append(dict(id=cid, signal=name, entry=entry, H=H, n=n, quarters=len(qs),
                     avg_stock=s[sel].mean(), avg_vsN=(s - n_)[sel].mean(), short_net=x.mean(), short_wo5=wo5,
                     base_short=BASE[w], vs_base=x.mean() - BASE[w], q_pos=int((qs > 0).sum()),
                     n_h1=len(h1), short_h1=h1.mean() if len(h1) else np.nan, n_h2=len(h2),
                     short_h2=h2.mean() if len(h2) else np.nan, raw_short_net=raw_short.mean(),
                     hit=(x > 0).mean() * 100, t_q=tq, luck_p=lp, eligible=elig_n and elig_h and elig_b,
                     fail=reason))
    tr = f.loc[sel, ['symbol', 'qn', 'quarter', 'XN']].copy()
    tr['id'], tr['stock'], tr['nifty'], tr['short_net'] = cid, s[sel], n_[sel], x
    trades.append(tr)
    for q, v in qs.items():
        perq.append(dict(id=cid, qn=q, n=int((QN[sel] == q).sum()), short_net=v))

T = pd.DataFrame(rows)
TR = pd.concat(trades, ignore_index=True)
assert TR.qn.max() <= DISC_MAX
T.to_csv(f'{HERE}/discovery_table.csv', index=False, float_format='%.4f')
TR.to_csv(f'{HERE}/trades_discovery.csv', index=False, float_format='%.4f')
pd.DataFrame(perq).to_csv(f'{HERE}/per_quarter_discovery.csv', index=False, float_format='%.4f')

pd.set_option('display.width', 250)
P('\nDISCOVERY TABLE (qn 0-13; short_net = -(stock - Nifty) - 0.19, %):')
P(T[['id', 'signal', 'entry', 'H', 'n', 'quarters', 'avg_stock', 'avg_vsN', 'short_net', 'short_wo5', 'base_short',
     'vs_base', 'q_pos', 'short_h1', 'short_h2', 'raw_short_net', 't_q', 'luck_p', 'eligible', 'fail']]
  .round(3).to_string(index=False))

# ---------------------------------------------------------------- finalist rule (fixed in candidates.txt)
E = T[T.eligible].sort_values('short_wo5', ascending=False)
P('\nELIGIBLE, ranked by short net without the 5 best short trades:')
P(E[['id', 'signal', 'entry', 'H', 'n', 'short_net', 'short_wo5', 'vs_base', 'short_h1', 'short_h2']].round(3)
  .to_string(index=False) if len(E) else '  none')
fin = []
keyset = {cid: set(zip(g.symbol, g.qn)) for cid, g in TR.groupby('id')}
for cid in E.id:
    if not fin:
        fin.append(cid)
    elif len(fin) == 1:
        a, b = keyset[fin[0]], keyset[cid]
        ov = len(a & b) / min(len(a), len(b))
        P(f'  overlap {fin[0]} vs {cid}: {ov:.2f}')
        if ov < 0.5:
            fin.append(cid)
            break
P('\nFINALISTS:', fin if fin else 'none')
with open(f'{HERE}/finalists.txt', 'w') as fh:
    fh.write('\n'.join(fin) + '\n' if fin else 'none\n')

# markdown table
md = ['| id | signal | entry | H | n | avg stock | avg vs Nifty | short net | w/o best 5 | base short | vs base | '
      'q short+ / q | half 1 (qn0-6) | half 2 (qn7-13) | luck p | eligible |',
      '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---|']
for r in T.itertuples():
    md.append(f'| {r.id} | {r.signal} | {r.entry} | {r.H} | {r.n} | {r.avg_stock:+.2f} | {r.avg_vsN:+.2f} | '
              f'{r.short_net:+.2f} | {r.short_wo5:+.2f} | {r.base_short:+.2f} | {r.vs_base:+.2f} | '
              f'{r.q_pos}/{r.quarters} | {r.short_h1:+.2f} ({r.n_h1}) | {r.short_h2:+.2f} ({r.n_h2}) | {r.luck_p:.3f} | '
              f'{"YES" if r.eligible else "no: " + r.fail} |')
open(f'{HERE}/discovery_table.md', 'w').write('\n'.join(md) + '\n')
P('wrote discovery_table.csv/.md, trades_discovery.csv, per_quarter_discovery.csv, base.csv, finalists.txt')
