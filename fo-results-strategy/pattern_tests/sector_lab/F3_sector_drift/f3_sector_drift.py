#!/usr/bin/env python3
"""
F3  Sector-aware version of the results-winner drift
=====================================================

PRE-REGISTRATION (written before any outcome was computed. Anything added after
seeing results is marked "ADDED AFTER" and counted.)

Known edge to build on
----------------------
Buy an F&O stock that beat Nifty 50 by more than 4% on its reaction day, at the
reaction-day close, hold 20 sessions.

Conventions (fixed in advance)
------------------------------
* Universe for trades: events.in_fo True in that quarter (F&O at the time).
  The two blank in_fo values (RELIANCE qn9, VEDL qn20) are set True: both stocks
  are F&O in the neighbouring quarters.
* Reaction day = events.i_react (result day for before/during-market or
  non-trading-day results; next session for after-close results). The stock's
  reaction is public only at that close.
* Reaction excess vs Nifty   XN = stock return on i_react - Nifty 50 return on i_react.
  Reaction excess vs sector  XS = stock return on i_react - own sector index return.
* Sector index of a stock = events.sector_index. If it is "Nifty 500" (no
  matching sector) OR the index has no close on a date needed, the fallback is
  Nifty 500 (said in the output). India Manufacturing (<2021-08), India Digital
  (<2021-12) and India Defence (<2022-01) therefore fall back in early quarters.
* Peer group GRP = events.peer_group if not blank, else events.sector_index if
  it is not "Nifty 500", else no group.
* Entry at the close of the decision session (reaction-day close for the
  winner; the TRIGGER's reaction-day close for laggard trades). Exit at the
  close H sessions later. Stock holding return = compounded daily returns
  (blank return = no trade -> factor 1, the next return already spans it).
  Trades whose window has more than 2 blank stock returns are dropped (reported).
  Index holding return = close(exit)/close(entry) - 1.
* Costs: 0.17% per stock round trip; hedged (minus Nifty) also pays 0.02% for
  the Nifty futures leg -> net_raw = raw - 0.17%, net_vsN = raw - Nifty - 0.19%,
  net_vsS = raw - sector - 0.19% (research number: only Nifty Bank and Nifty
  Financial Services among our sector indices have index futures; any other
  sector short needs a basket of stock futures; E2 below prices that).
* Unit of evidence = quarter (qn of the event / trigger). Per-quarter mean of
  trades, then mean and t across quarters with trades. First 14 (qn 0..13) vs
  last 8 (qn 14..21). Trade count, % trades with net_vsN > 0.
* "Promising" (from the brief): net_vsN > 0 in BOTH halves, |t| >= 2.5, >= 30
  trades, placebo clearly worse. For a REFINEMENT (subset of base winners) the
  placebo is a random subset of base winners of the same size in each quarter;
  the refinement only counts as an improvement if it beats >= 95% of random
  subsets AND its quarter-by-quarter difference vs the base is > 0 in both halves.

Pre-registered variants (35)
----------------------------
B  base (reproduction / context)                                       6
   B1 XN>4%  H=5          B2 XN>4% H=10        B3 XN>4% H=20 (primary)
   B4 XN>3%  H=20         B5 XN>6% H=20
   B6 XN>4%  H=20, entry at NEXT session open (intraday.csv), exit same close.
A  winner defined against the SECTOR index                             6
   A1 XS>4% (all)                              H in {5,20}
   A2 XS>4% and XN<=4%  ("sector-only" winner) H in {5,20}
   A3 XN>4% and XS<=4%  ("Nifty-only" winner, sector also rallied) H in {5,20}
BC confirmation by already-reported peers (among base winners XN>4%)   9
   peer score PS = mean XN of F&O stocks in the same GRP, same quarter, whose
   reaction day <= the winner's reaction day (public at that close), excluding
   the winner; defined if n>=2.
   BC1 PS>0      H in {5,20}      BC2 PS<=0    H in {5,20}
   BC3 PS>+2%    H in {5,20}      BC4 PS<-2%   H in {5,20}
   BC5 fewer than 2 reported peers (incl. no group)  H=20
C  sector trend at the reaction-day close (among base winners)        8
   C1 sector close > its 200-session average   C2 below     H in {5,20}
   C3 sector 63-session (3M) return > 0        C4 <= 0      H in {5,20}
D  laggard catch-up (trigger = base winner XN>4%; trade = PEERS)       4
   D1 same-GRP F&O peers that already reported this quarter (reaction day <=
      trigger's) with XN < 0                                   H in {5,20}
   D2 same-GRP F&O peers that have NOT reported yet (reaction day > trigger's)
                                                               H in {5,20}
   Entry at the trigger's reaction-day close. One trade per (peer, quarter):
   the first trigger only.
E  sector-neutral (long winner, short sector)                          2
   E1 B3 trades measured minus own sector index (cost 0.19%) - research number
   E2 B3 trades whose sector is Nifty Bank or Nifty Financial Services (real
      index futures exist): minus that index, cost 0.19%.  For the other
      sectors also reported with basket cost 0.34% (0.17 stock + 0.17 basket).

ADDED AFTER (counted): variant #36 = K5 in f3_addendum.py, the prior-work
   definition of the same base trade (entry at the Day+1 close = events.next20).
   TOTAL VARIANTS = 36. f3_addendum.py also holds extra placebo checks (no variants).

Run order: f3_sector_drift.py -> f3_placebo.py -> f3_addendum.py

Placebos / controls (not counted as variants; they are checks)
   PL0 unconditional: every F&O result, buy at reaction close, H=20 (survivorship
       and market baseline).
   PL1 non-results big up days: F&O stock beats Nifty by > 4% on a session that
       is not within [i_cut, i_react+5] of any of its results; buy at close,
       hold 20; per stock no overlapping trades. Grouped by calendar quarter.
   PL2 random subsets of base winners (same count per quarter), 2000 reps, for
       every A2/A3/BC/C subset at its horizon.
   PL3 random peers for D: same trigger, same status (reported-weak / not yet
       reported), stocks drawn from OTHER groups, same count; 500 reps.
   PL4 random sector map for A1: each stock gets a sector index drawn by
       permuting the stock->sector map; 500 reps.
"""
import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
import sys
sys.path.append('/root/.local/lib/python3.11/site-packages')
import numpy as np
import pandas as pd

DATA = os.environ.get('SECTOR_LAB', 'sector_lab') + '/data'
OUT = os.environ.get('SECTOR_LAB', 'sector_lab') + '/F3_sector_drift'
COST = 0.0017
HEDGE = 0.0002
T4 = 0.04
FIRST14 = 14
RNG = np.random.default_rng(20261007)

# ---------------------------------------------------------------- load
ses = pd.read_csv(f'{DATA}/sessions.csv')
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
intra = pd.read_csv(f'{DATA}/intraday.csv', index_col=0)
ixc = pd.read_csv(f'{DATA}/index_close.csv', index_col=0)
ev = pd.read_csv(f'{DATA}/events.csv')
assert len(ses) == len(ret) == len(ixc) == len(intra)
assert (ret.index == ses.day).all() and (ixc.index == ses.day).all()
ev.loc[ev.in_fo.isna(), 'in_fo'] = True
ev['in_fo'] = ev.in_fo.astype(bool)

NS = len(ses)
SYM = {s: k for k, s in enumerate(ret.columns)}
R = ret.values  # NaN = no trade
R0 = np.nan_to_num(R, nan=0.0)
P = np.cumprod(1.0 + R0, axis=0)  # price index (adjusted)
VALID = ~np.isnan(R)
CVALID = np.cumsum(VALID, axis=0)
INTRA = intra.values

NIFTY = ixc['Nifty 50'].values
N500 = ixc['Nifty 500'].values
nret = np.r_[np.nan, NIFTY[1:] / NIFTY[:-1] - 1]

SECTORS = sorted(ev.sector_index.unique())


def idx_arr(name):
    return ixc[name].values


IDX = {s: idx_arr(s) for s in SECTORS}
IDX['Nifty 50'] = NIFTY


def stock_hold(sym, i0, H, entry='close'):
    """compounded return from close i0 (or open i0+1) to close i0+H; blanks count"""
    k = SYM[sym]
    i1 = i0 + H
    if i1 >= NS:
        return np.nan, 99
    nblank = H - (CVALID[i1, k] - CVALID[i0, k])
    if entry == 'close':
        r = P[i1, k] / P[i0, k] - 1
    else:  # next open: intraday of i0+1 then closes i0+2..i1
        ir = INTRA[i0 + 1, k]
        if np.isnan(ir):
            return np.nan, 99
        r = (1 + ir) * (P[i1, k] / P[i0 + 1, k]) - 1
    return r, nblank


def index_hold(name, i0, H):
    a = IDX[name] if name in IDX else ixc[name].values
    i1 = i0 + H
    if i1 >= NS:
        return np.nan, name
    v0, v1 = a[i0], a[i1]
    if np.isnan(v0) or np.isnan(v1):
        name = 'Nifty 500'
        v0, v1 = N500[i0], N500[i1]
    return v1 / v0 - 1, name


def index_dret(name, i):
    a = IDX[name]
    if np.isnan(a[i]) or np.isnan(a[i - 1]):
        return N500[i] / N500[i - 1] - 1, 'Nifty 500'
    return a[i] / a[i - 1] - 1, name


# ---------------------------------------------------------------- event features
ev['grp'] = np.where(ev.peer_group.notna(), ev.peer_group,
                     np.where(ev.sector_index != 'Nifty 500', ev.sector_index, None))
ev['r_react'] = [R[i, SYM[s]] for s, i in zip(ev.symbol, ev.i_react)]
ev['n_react'] = nret[ev.i_react.values]
ev['XN'] = ev.r_react - ev.n_react
sd, sn = [], []
for s, i in zip(ev.sector_index, ev.i_react):
    d, nm = index_dret(s, i)
    sd.append(d); sn.append(nm)
ev['s_react'] = sd
ev['sec_used_react'] = sn
ev['XS'] = ev.r_react - ev.s_react


# sector trend at reaction-day close (fallback Nifty 500 if not enough history)
def trend(name, i):
    a = IDX[name]
    w = a[i - 199:i + 1]
    if np.isnan(w).any() or np.isnan(a[i - 63]):
        a = N500
        w = a[i - 199:i + 1]
        name = 'Nifty 500'
    return a[i] > w.mean(), a[i] / a[i - 63] - 1, name


tr = [trend(s, i) for s, i in zip(ev.sector_index, ev.i_react)]
ev['above200'] = [t[0] for t in tr]
ev['sec3m'] = [t[1] for t in tr]
ev['sec_used_trend'] = [t[2] for t in tr]

fo = ev[ev.in_fo & ev.r_react.notna()].copy()


# peer score among already-reported F&O peers (reaction day <= own, same qn, same grp)
def peer_score(row, pool):
    if row.grp is None or pd.isna(row.grp):
        return np.nan, 0
    p = pool[(pool.qn == row.qn) & (pool.grp == row.grp) & (pool.symbol != row.symbol)
             & (pool.i_react <= row.i_react)]
    if len(p) < 2:
        return np.nan, len(p)
    return p.XN.mean(), len(p)


ps = [peer_score(r, fo) for r in fo.itertuples()]
fo['PS'] = [p[0] for p in ps]
fo['PSn'] = [p[1] for p in ps]


# ---------------------------------------------------------------- trade builder
def build(df, H, entry_col='i_react', entry='close', label=''):
    rows = []
    for r in df.itertuples():
        i0 = getattr(r, entry_col)
        raw, nb = stock_hold(r.symbol, i0, H, entry)
        if np.isnan(raw) or nb > 2:
            rows.append(None)
            continue
        nf, _ = index_hold('Nifty 50', i0, H)
        sc, sname = index_hold(r.sector_index, i0, H)
        rows.append((r.symbol, int(r.qn), i0, r.sector_index, sname, raw, nf, sc))
    dropped = sum(x is None for x in rows)
    t = pd.DataFrame([x for x in rows if x is not None],
                     columns=['symbol', 'qn', 'i_entry', 'sector_index', 'sector_used', 'raw', 'nifty', 'sector'])
    t['net_raw'] = t.raw - COST
    t['net_vsN'] = t.raw - t.nifty - COST - HEDGE
    t['net_vsS'] = t.raw - t.sector - COST - HEDGE
    t['label'] = label
    t['H'] = H
    t.attrs['dropped'] = dropped
    return t


def qstats(t, col='net_vsN', allq=None):
    """per-quarter means -> mean, t, halves, quarters positive"""
    if len(t) == 0:
        return dict(n=0)
    q = t.groupby('qn')[col].mean()
    nq = len(q)
    m = q.mean()
    s = q.std(ddof=1) if nq > 1 else np.nan
    tt = m / (s / np.sqrt(nq)) if nq > 1 and s > 0 else np.nan
    f = q[q.index < FIRST14]
    l = q[q.index >= FIRST14]
    return dict(n=len(t), nq=nq, q_mean=m, t=tt, first14=f.mean() if len(f) else np.nan,
                last8=l.mean() if len(l) else np.nan, qpos=int((q > 0).sum()),
                trade_mean=t[col].mean())


def summarize(t, name, H, extra=None):
    d = dict(variant=name, H=H, trades=len(t), dropped=t.attrs.get('dropped', 0))
    for col, tag in [('net_raw', 'raw'), ('net_vsN', 'vsN'), ('net_vsS', 'vsS')]:
        s = qstats(t, col)
        d[f'{tag}_trade_avg'] = s.get('trade_mean', np.nan) * 100
        d[f'{tag}_q_avg'] = s.get('q_mean', np.nan) * 100
        d[f'{tag}_t'] = s.get('t', np.nan)
        d[f'{tag}_first14'] = s.get('first14', np.nan) * 100
        d[f'{tag}_last8'] = s.get('last8', np.nan) * 100
        d[f'{tag}_qpos'] = f"{s.get('qpos', 0)}/{s.get('nq', 0)}"
    d['nq'] = qstats(t).get('nq', 0)
    d['pct_win_vsN'] = (t.net_vsN > 0).mean() * 100 if len(t) else np.nan
    if extra:
        d.update(extra)
    return d


def per_quarter_table(t, name):
    g = t.groupby('qn').agg(n=('raw', 'size'), net_raw=('net_raw', 'mean'),
                            net_vsN=('net_vsN', 'mean'), net_vsS=('net_vsS', 'mean'))
    g[['net_raw', 'net_vsN', 'net_vsS']] *= 100
    g['variant'] = name
    return g.reset_index()


def diff_vs_base(t, base, col='net_vsN'):
    """quarter-by-quarter difference subset - base (quarters with both)"""
    a = t.groupby('qn')[col].mean()
    b = base.groupby('qn')[col].mean()
    d = (a - b).dropna()
    if len(d) < 2:
        return dict(diff_avg=np.nan, diff_t=np.nan, diff_first14=np.nan, diff_last8=np.nan)
    return dict(diff_avg=d.mean() * 100, diff_t=d.mean() / (d.std(ddof=1) / np.sqrt(len(d))),
                diff_first14=d[d.index < FIRST14].mean() * 100, diff_last8=d[d.index >= FIRST14].mean() * 100)


# ---------------------------------------------------------------- run
if __name__ == '__main__':
    log = open(f'{OUT}/run_main.txt', 'w')

    def P_(*a):
        s = ' '.join(str(x) for x in a)
        print(s)
        log.write(s + '\n')

    P_('DATA CHECKS')
    P_(f'sessions {len(ses)} ({ses.day.iloc[0]} .. {ses.day.iloc[-1]}), symbols {R.shape[1]}, indices {ixc.shape[1]}')
    P_(f'events {len(ev)}, F&O-at-time events {int(ev.in_fo.sum())}, quarters {ev.qn.nunique()}')
    P_('F&O events per quarter:', fo.groupby('qn').size().to_dict())
    P_('blank reaction-day returns among F&O events:', int(ev[ev.in_fo].r_react.isna().sum()))
    P_('sector used for reaction-day return (fallback count):',
       (fo.sec_used_react != fo.sector_index).sum(), 'of', len(fo))
    P_('sector used for trend (fallback to Nifty 500 where sector!=N500):',
       ((fo.sec_used_trend == 'Nifty 500') & (fo.sector_index != 'Nifty 500')).sum())
    P_('GRP counts (F&O):', fo.grp.value_counts(dropna=False).to_dict())
    for s in SECTORS:
        a = IDX[s][1300:]
        P_(f'  index {s:28s} first valid {ixc[s].first_valid_index()}  NaN sessions after i=1300: {int(np.isnan(a).sum())}')

    summ, pq, trades_all = [], [], []

    W = fo[fo.XN > T4]
    P_(f'\nBase winners XN>4%: {len(W)} trades')

    def run(name, df, H, entry='close', extra=None, keep=True):
        t = build(df, H, entry=entry, label=name)
        d = summarize(t, name, H, extra)
        summ.append(d)
        pq.append(per_quarter_table(t, name))
        if keep:
            trades_all.append(t)
        return t

    # B
    base = {}
    base[5] = run('B1 XN>4 H5', W, 5)
    base[10] = run('B2 XN>4 H10', W, 10)
    base[20] = run('B3 XN>4 H20', W, 20)
    run('B4 XN>3 H20', fo[fo.XN > 0.03], 20)
    run('B5 XN>6 H20', fo[fo.XN > 0.06], 20)
    run('B6 XN>4 H20 next-open', W, 20, entry='open')

    # A
    for H in (5, 20):
        run(f'A1 XS>4 H{H}', fo[fo.XS > T4], H)
        a2 = run(f'A2 XS>4&XN<=4 H{H}', fo[(fo.XS > T4) & (fo.XN <= T4)], H)
        a3 = run(f'A3 XN>4&XS<=4 H{H}', fo[(fo.XN > T4) & (fo.XS <= T4)], H)

    # BC
    for H in (5, 20):
        run(f'BC1 PS>0 H{H}', W[W.PS > 0], H)
        run(f'BC2 PS<=0 H{H}', W[W.PS <= 0], H)
        run(f'BC3 PS>2 H{H}', W[W.PS > 0.02], H)
        run(f'BC4 PS<-2 H{H}', W[W.PS < -0.02], H)
    run('BC5 n<2 H20', W[W.PS.isna()], 20)

    # C
    for H in (5, 20):
        run(f'C1 above200 H{H}', W[W.above200], H)
        run(f'C2 below200 H{H}', W[~W.above200], H)
        run(f'C3 sec3m>0 H{H}', W[W.sec3m > 0], H)
        run(f'C4 sec3m<=0 H{H}', W[W.sec3m <= 0], H)

    # D  laggard catch-up
    def laggards(W, fo, kind):
        rows = []
        for w in W.sort_values('i_react').itertuples():
            if w.grp is None or pd.isna(w.grp):
                continue
            p = fo[(fo.qn == w.qn) & (fo.grp == w.grp) & (fo.symbol != w.symbol)]
            if kind == 'weak':
                p = p[(p.i_react <= w.i_react) & (p.XN < 0)]
            else:
                p = p[p.i_react > w.i_react]
            for x in p.itertuples():
                rows.append(dict(symbol=x.symbol, qn=x.qn, sector_index=x.sector_index, grp=x.grp,
                                 i_trig=w.i_react, trigger=w.symbol, peer_i_react=x.i_react))
        d = pd.DataFrame(rows)
        d = d.sort_values('i_trig').drop_duplicates(['symbol', 'qn'], keep='first')
        return d

    LAG = {'weak': laggards(W, fo, 'weak'), 'notyet': laggards(W, fo, 'notyet')}
    for H in (5, 20):
        for kind, nm in (('weak', 'D1 reported-weak peers'), ('notyet', 'D2 not-yet-reported peers')):
            d = LAG[kind]
            t = build(d, H, entry_col='i_trig', label=f'{nm} H{H}')
            summ.append(summarize(t, f'{nm} H{H}', H))
            pq.append(per_quarter_table(t, f'{nm} H{H}'))
            trades_all.append(t)

    # E  sector-neutral
    b = base[20].copy()
    e1 = summarize(b, 'E1 B3 minus sector (all)', 20)
    summ.append(e1)
    feas = b[b.sector_used.isin(['Nifty Bank', 'Nifty Financial Services'])].copy()
    summ.append(summarize(feas, 'E2 B3 Bank/FinServ sector, short index fut', 20))
    pq.append(per_quarter_table(feas, 'E2 B3 Bank/FinServ sector, short index fut'))
    other = b[~b.sector_used.isin(['Nifty Bank', 'Nifty Financial Services'])].copy()
    other['net_vsS'] = other.raw - other.sector - COST - COST  # basket of stock futures
    d = summarize(other, 'E2b (info) other sectors, short basket cost 0.34%', 20)
    summ.append(d)

    S = pd.DataFrame(summ)
    # differences vs base at same horizon for subset variants
    for k, row in S.iterrows():
        nm = row.variant
        if nm.startswith(('A2', 'A3', 'BC', 'C', 'A1', 'B4', 'B5', 'B6')):
            t = [x for x in trades_all if len(x) and x.label.iloc[0] == nm][0]
            dd = diff_vs_base(t, base[int(row.H)])
            for kk, vv in dd.items():
                S.loc[k, kk] = vv
    S.to_csv(f'{OUT}/summary.csv', index=False)
    pd.concat(pq).to_csv(f'{OUT}/per_quarter.csv', index=False)
    pd.concat(trades_all).to_csv(f'{OUT}/trades.csv', index=False)
    fo.to_csv(f'{OUT}/fo_events_features.csv', index=False)
    for kind in LAG:
        LAG[kind].to_csv(f'{OUT}/laggards_{kind}.csv', index=False)

    pd.set_option('display.width', 250)
    pd.set_option('display.max_columns', 40)
    pd.set_option('display.max_rows', 200)
    cols = ['variant', 'trades', 'nq', 'raw_q_avg', 'vsN_trade_avg', 'vsN_q_avg', 'vsN_t', 'vsN_first14', 'vsN_last8',
            'vsN_qpos', 'vsS_q_avg', 'vsS_t', 'pct_win_vsN', 'diff_avg', 'diff_t', 'diff_first14', 'diff_last8']
    P_('\nSUMMARY (percent; q_avg = mean of per-quarter means; t across quarters)')
    P_(S[cols].round(2).to_string(index=False))
    P_('\nBase B3 per quarter (percent):')
    P_(per_quarter_table(base[20], 'B3').round(2).to_string(index=False))
    log.close()
