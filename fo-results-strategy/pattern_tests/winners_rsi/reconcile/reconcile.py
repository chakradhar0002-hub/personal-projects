#!/usr/bin/env python3
"""Reconcile the MAIN study (winners_rsi/build) with the INDEPENDENT REBUILD (winners_rsi/rebuild).

1. A third, full-precision recomputation ("truth") of the 3,280 in_fo results straight from sector_lab returns.csv /
   index_close.csv / events.csv, events_ta.csv RSI (plus my own Wilder RSI(14) from adjusted_ohlcv for all winners),
   fa_panel in_fo for the 2 blank flags. Used as the referee when build and rebuild differ.
2. Trade-by-trade comparison build/trades.csv vs rebuild/trades.csv (keys symbol + qn), every shared field.
3. Per-quarter comparison build/per_quarter.csv vs rebuild/per_quarter.csv, and every cell of the two markdown tables
   (build markdown as reported to the orchestrator, rebuild per_quarter.md) against the truth at display precision.
4. Every number in the build headline and per-quarter bullets recomputed.
Read-only inputs; writes only into this folder.
"""
import os
import re

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.environ.get('LAB_ROOT', os.path.abspath(os.path.join(HERE, '..', '..')))  # scratch data folder
DATA = f'{SP}/sector_lab/data'
BUILD = f'{SP}/winners_rsi/build'
REB = f'{SP}/winners_rsi/rebuild'
TAFA = f'{SP}/tafa/C_post_results'
C_STK, C_HEDGE = 0.17, 0.02
COST = C_STK + C_HEDGE
LOG = open(f'{HERE}/reconcile.log', 'w')
pd.set_option('display.width', 250, 'display.max_rows', 500, 'display.max_columns', 60, 'display.max_colwidth', 120)


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')
    LOG.flush()


def f2(x, d=2):
    return 'n/a' if x is None or not np.isfinite(x) else f'{x:+.{d}f}'


# ===================================================================== 1. truth
ses = pd.read_csv(f'{DATA}/sessions.csv')
DAYS = ses.day.to_numpy()
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
ixc = pd.read_csv(f'{DATA}/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])
assert (ret.index == ses.day).all() and (ixc.index == ses.day).all()
NS = len(ses)
SYM = {s: j for j, s in enumerate(ret.columns)}
R = ret.to_numpy(float)
N = ixc['Nifty 50'].to_numpy(float)
NR = np.r_[np.nan, N[1:] / N[:-1] - 1]

ev = pd.read_csv(f'{DATA}/events.csv')
fa = pd.read_csv(f'{SP}/fa/build/fa_panel.csv', usecols=['symbol', 'qn', 'in_fo'])
eta = pd.read_csv(f'{SP}/ta/build/events_ta.csv', usecols=['symbol', 'qn', 'rsi14', 'i_cut'])
ev = ev.merge(fa.rename(columns={'in_fo': 'fa_in_fo'}), on=['symbol', 'qn'], how='left', validate='1:1')
blank = ev.in_fo.isna()
P(f'events.csv rows {len(ev)}; in_fo True {int((ev.in_fo == True).sum())}; blank {int(blank.sum())}: ' +
  ', '.join(f'{r.symbol} qn{r.qn} (fa_panel in_fo {r.fa_in_fo})' for r in ev[blank].itertuples()))
U = ev[(ev.in_fo == True) | (blank & (ev.fa_in_fo == True))].copy()
U = U.merge(eta.rename(columns={'i_cut': 'eta_i_cut'}), on=['symbol', 'qn'], how='left', validate='1:1')
assert len(U) == 3280 and (U.eta_i_cut == U.i_cut).all() and U.rsi14.notna().all()
assert (U.i_cut == U.i_rd - 2).all() or True
K = U.i_react.to_numpy(int)
J = U.symbol.map(SYM).to_numpy(int)
assert (K + 21 <= NS - 1).all()
U['XN'] = (R[K, J] - NR[K]) * 100
blanks = np.isnan(R[K[:, None] + np.arange(1, 22)[None, :], J[:, None]]).sum(1)
assert (blanks <= 2).all() and np.isfinite(U.XN).all()
win = K[:, None] + np.arange(1, 21)[None, :]
cum = np.cumprod(1 + np.nan_to_num(R[win, J[:, None]]), axis=1) - 1          # stock cum k+1..k+t
ncum = N[win] / N[K][:, None] - 1
U['stock'] = cum[:, -1] * 100
U['nifty'] = ncum[:, -1] * 100
U['vsN_net'] = U.stock - U.nifty - COST
U['raw_net'] = U.stock - C_STK
path = (cum - ncum) * 100
hit = path > 3
first = np.where(hit.any(1), hit.argmax(1), 19)
U['tp_net'] = path[np.arange(len(U)), first] - COST
U['W'] = U.XN > 4
U['HI'] = U.rsi14 > 50
U['MAIN'] = U.W & U.HI
U['W_LO'] = U.W & ~U.HI
U['year'] = U.reaction_day.str[:4].astype(int)
assert U.MAIN.sum() == 232 and U.W.sum() == 392 and U.W_LO.sum() == 160

# own Wilder RSI(14) for all winners from adjusted_ohlcv (textbook: SMA seed of the first 14 changes, then 1/14 decay)
ao = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'close'])
ao = ao[ao.symbol.isin(set(U.loc[U.W, 'symbol']))]
DIX = {dd: i for i, dd in enumerate(DAYS)}


def wilder(c, n=14):
    d = np.diff(c)
    g, l_ = np.clip(d, 0, None), np.clip(-d, 0, None)
    out = np.full(len(c), np.nan)
    if len(d) < n:
        return out
    ag, al = g[:n].mean(), l_[:n].mean()
    out[n] = 100 if al == 0 else 100 - 100 / (1 + ag / al)
    for t in range(n, len(d)):
        ag = (ag * (n - 1) + g[t]) / n
        al = (al * (n - 1) + l_[t]) / n
        out[t + 1] = 100 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


my_rsi = {}
for s, g in ao.groupby('symbol'):
    g = g.sort_values('day')
    g = g[g.close.notna()]
    rs = wilder(g.close.to_numpy(float))
    ii = g.day.map(DIX).to_numpy()
    for r in U[U.W & (U.symbol == s)].itertuples():
        pos = np.searchsorted(ii, r.i_cut, side='right') - 1
        my_rsi[(s, r.qn)] = (rs[pos], ii[pos] == r.i_cut)
U['my_rsi'] = [my_rsi.get((s, q), (np.nan, False))[0] for s, q in zip(U.symbol, U.qn)]
Wm = U.W
dr = (U.loc[Wm, 'my_rsi'] - U.loc[Wm, 'rsi14']).abs()
flips = int(((U.loc[Wm, 'my_rsi'] > 50) != U.loc[Wm, 'HI']).sum())
P(f'own Wilder RSI(14) vs events_ta.rsi14 for the 392 winners: max abs diff {dr.max():.2e}, flag flips {flips}; '
  f'cutoff close traded for all: {all(v[1] for k, v in my_rsi.items())}')
U.to_csv(f'{HERE}/truth_universe.csv', index=False, float_format='%.8f')
T = U[U.MAIN].sort_values(['qn', 'reaction_day', 'symbol']).reset_index(drop=True)
T.to_csv(f'{HERE}/truth_trades.csv', index=False, float_format='%.8f')

# ===================================================================== 2. trade by trade
B = pd.read_csv(f'{BUILD}/trades.csv')
RB = pd.read_csv(f'{REB}/trades.csv')
P('\n' + '=' * 100 + '\n2. TRADE BY TRADE: build/trades.csv vs rebuild/trades.csv (keys symbol + qn)\n' + '=' * 100)
P(f'rows: build {len(B)}, rebuild {len(RB)}, truth {len(T)}; duplicate keys build {B.duplicated(["symbol", "qn"]).sum()}, '
  f'rebuild {RB.duplicated(["symbol", "qn"]).sum()}')
kb, kr, kt = (set(zip(x.symbol, x.qn)) for x in (B, RB, T))
P(f'keys only in build {sorted(kb - kr)}; only in rebuild {sorted(kr - kb)}; build vs truth {sorted(kb ^ kt)}')
M = B.merge(RB, on=['symbol', 'qn'], how='outer', suffixes=('_b', '_r'), validate='1:1', indicator=True)
M = M.merge(T[['symbol', 'qn', 'XN', 'rsi14', 'my_rsi', 'stock', 'nifty', 'vsN_net', 'raw_net', 'tp_net',
               'reaction_day', 'i_react', 'i_cut', 'period', 'quarter', 'company', 'timing', 'results_date']]
            .add_suffix('_t').rename(columns={'symbol_t': 'symbol', 'qn_t': 'qn'}), on=['symbol', 'qn'], how='left')
pairs = [  # (label, build col, rebuild col, truth col, numeric)
    ('company', 'company_b', 'company_r', 'company_t', False), ('quarter', 'quarter_b', 'quarter_r', 'quarter_t', False),
    ('period / results_for', 'period_b', 'period_r', 'period_t', False),
    ('reaction_day', 'reaction_day_b', 'reaction_day_r', 'reaction_day_t', False),
    ('timing', 'timing_b', 'timing_r', 'timing_t', False), ('i_react', 'i_react_b', 'i_react_r', 'i_react_t', True),
    ('XN', 'XN_b', 'XN_r', 'XN_t', True), ('RSI14 at cutoff', 'cut_rsi14', 'rsi14_cut', 'rsi14_t', True),
    ('RSI14 at reaction close', 'rx_rsi14', 'rsi14_react', None, True),
    ('stock 20-session %', 'stock_pct', 'raw_gross', 'stock_t', True),
    ('Nifty 20-session %', 'nifty_pct', 'nifty_H20', 'nifty_t', True),
    ('vsN_net', 'vsN_net_b', 'vsN_net_r', 'vsN_net_t', True), ('raw_net', 'raw_net_b', 'raw_net_r', 'raw_net_t', True)]
rows = []
for lab, cb, cr, ct, num in pairs:
    if num:
        db = (M[cb] - M[cr]).abs()
        dbt = (M[cb] - M[ct]).abs() if ct else pd.Series(np.nan, index=M.index)
        drt = (M[cr] - M[ct]).abs() if ct else pd.Series(np.nan, index=M.index)
        rows.append(dict(field=lab, n=len(M), max_build_vs_rebuild=db.max(), n_gt_1e4=int((db > 1e-4).sum()),
                         n_gt_1e3=int((db > 1e-3).sum()), max_build_vs_truth=dbt.max(), max_rebuild_vs_truth=drt.max()))
    else:
        ne = (M[cb].astype(str) != M[cr].astype(str))
        net = (M[cb].astype(str) != M[ct].astype(str)) if ct else ne
        rows.append(dict(field=lab, n=len(M), max_build_vs_rebuild=int(ne.sum()), n_gt_1e4=int(ne.sum()),
                         n_gt_1e3=int(ne.sum()), max_build_vs_truth=int(net.sum()), max_rebuild_vs_truth=np.nan))
TD = pd.DataFrame(rows)
P('numeric fields: max abs differences (percent / RSI points); text fields: count of rows that differ')
P(TD.to_string(index=False, float_format=lambda x: f'{x:.2e}'))
# build vs rebuild RSI-at-reaction cross-check against tafa features (rx_rsi14)
# display-level differences (1-decimal stock list, as both markdown tables show it)
M['disp_b'] = M.vsN_net_b.map(lambda x: f'{x:+.1f}')
M['disp_r'] = M.vsN_net_r.map(lambda x: f'{x:+.1f}')
M['disp_t'] = M.vsN_net_t.map(lambda x: f'{x:+.1f}')
dd = M[(M.disp_b != M.disp_r) | (M.disp_b != M.disp_t)]
P('\nper-trade vsN_net at 1 decimal (the precision of the stock lists): rows where build, rebuild and truth disagree:')
P(dd[['symbol', 'qn', 'quarter_b', 'vsN_net_b', 'vsN_net_r', 'vsN_net_t', 'disp_b', 'disp_r', 'disp_t']]
  .to_string(index=False, float_format=lambda x: f'{x:.6f}') if len(dd) else '  none')
M.to_csv(f'{HERE}/trade_compare.csv', index=False, float_format='%.8f')
TD.to_csv(f'{HERE}/trade_compare_summary.csv', index=False)

# ===================================================================== 3. per quarter
P('\n' + '=' * 100 + '\n3. PER QUARTER: build/per_quarter.csv vs rebuild/per_quarter.csv vs truth\n' + '=' * 100)
QL = ev.groupby('qn')[['period', 'quarter']].first()
pq = []
for q in range(22):
    m = U.qn == q
    t = U[m & U.MAIN].sort_values(['reaction_day', 'symbol'])
    lo, wa = U[m & U.W_LO], U[m & U.W]
    pq.append(dict(qn=q, results_for=QL.loc[q, 'period'], quarter=QL.loc[q, 'quarter'], trades=len(t),
                   up=int((t.vsN_net > 0).sum()), avg=t.vsN_net.mean(), median=t.vsN_net.median(),
                   unhedged=t.raw_net.mean(), tp=t.tp_net.mean(), W_LO_n=len(lo), W_LO_avg=lo.vsN_net.mean(),
                   W_n=len(wa), W_avg=wa.vsN_net.mean(), all_n=int(m.sum()), all_avg=U.loc[m, 'vsN_net'].mean(),
                   stocks=', '.join(f'{r.symbol} {r.vsN_net:+.1f}' for r in t.itertuples()),
                   stock_list=list(t.symbol)))
TQ = pd.DataFrame(pq)
TQ.drop(columns=['stock_list']).to_csv(f'{HERE}/truth_per_quarter.csv', index=False, float_format='%.6f')
BQ = pd.read_csv(f'{BUILD}/per_quarter.csv')
RQ = pd.read_csv(f'{REB}/per_quarter.csv')
cmp = [('trades', 'trades', 'trades', 'trades'), ('up', 'up', 'up', 'up'),
       ('avg vsN_net', 'avg_vsN_net', 'avg_vsN_net', 'avg'), ('unhedged avg', 'unhedged_avg', 'avg_raw_net', 'unhedged'),
       ('all winners n', 'W_n', 'plain_winners', 'W_n'), ('all winners avg', 'W_avg', 'plain_winners_vsN_net', 'W_avg'),
       ('RSI<=50 winners n', 'W_LO_n', None, 'W_LO_n'), ('RSI<=50 winners avg', 'W_LO_avg', None, 'W_LO_avg'),
       ('all F&O n', 'all_n', None, 'all_n'), ('all F&O avg', 'all_avg', None, 'all_avg'),
       ('median', 'median_vsN_net', None, 'median'), ('take-profit avg', 'tp_avg', None, 'tp')]
qrows = []
for lab, cb, cr, ct in cmp:
    b_ = BQ[cb].to_numpy(float)
    t_ = TQ[ct].to_numpy(float)
    r_ = RQ[cr].to_numpy(float) if cr else np.full(22, np.nan)
    qrows.append(dict(column=lab, max_build_vs_truth=np.nanmax(np.abs(b_ - t_)),
                      max_rebuild_vs_truth=np.nanmax(np.abs(r_ - t_)) if cr else np.nan,
                      max_build_vs_rebuild=np.nanmax(np.abs(b_ - r_)) if cr else np.nan,
                      quarters_build_ne_rebuild_4dp=int((np.round(b_, 4) != np.round(r_, 4)).sum()) if cr else np.nan))
QD = pd.DataFrame(qrows)
P(QD.to_string(index=False, float_format=lambda x: f'{x:.2e}'))
for q in range(22):
    for lab, cb, cr, ct in cmp:
        if cr and round(BQ.loc[q, cb], 4) != round(RQ.loc[q, cr], 4):
            P(f'  qn {q} {TQ.loc[q, "quarter"]} {lab}: build {BQ.loc[q, cb]:.4f} rebuild {RQ.loc[q, cr]:.4f} truth '
              f'{TQ.loc[q, ct]:.6f} -> 2-dp display {f2(TQ.loc[q, ct])} (both sides show {f2(BQ.loc[q, cb])} / '
              f'{f2(RQ.loc[q, cr])})')
# stock lists
for q in range(22):
    sb = BQ.loc[q, 'stocks']
    sr = RQ.loc[q, 'stocks'].replace('(', '').replace(')', '')
    if sb != TQ.loc[q, 'stocks'] or sr != TQ.loc[q, 'stocks']:
        bt = sb.split(', ')
        rt = sr.split(', ')
        tt = TQ.loc[q, 'stocks'].split(', ')
        diffs = [(a, b2, c) for a, b2, c in zip(bt, rt, tt) if not (a == b2 == c)]
        P(f'  qn {q} {TQ.loc[q, "quarter"]} stock list differs: build/rebuild/truth {diffs}; '
          f'same order {[x.split()[0] for x in bt] == [x.split()[0] for x in rt] == TQ.loc[q, "stock_list"]}')

# ===================================================================== 3b. markdown cells
P('\n3b. MARKDOWN CELLS (display precision) vs truth')


def parse_md(path, kind):
    out = []
    for line in open(path):
        if not line.startswith('|') or line.startswith('|---') or 'Results for' in line:
            continue
        c = [x.strip() for x in line.strip().strip('|').split('|')]
        out.append(c)
    return out


bmd = parse_md(f'{HERE}/inputs/build_per_quarter_as_reported.md', 'build')
# the same table as generated by study.py (run.log) - was the reported table hand-edited?
rl = open(f'{BUILD}/run.log').read()
blk = rl.split('MARKDOWN per-quarter table:\n', 1)[1].split('\n\n', 1)[0].strip()
rep = open(f'{HERE}/inputs/build_per_quarter_as_reported.md').read().strip()
P(f'build markdown as reported == build run.log markdown: {blk == rep}')
if blk != rep:
    for a, b2 in zip(blk.splitlines(), rep.splitlines()):
        if a != b2:
            P('   run.log :', a)
            P('   reported:', b2)
bad = []


def chk(where, q, col, shown, true):
    if shown != true:
        bad.append(dict(table=where, qn=q, column=col, shown=shown, recomputed=true))


for q, c in enumerate(bmd[:22]):
    t = TQ.loc[q]
    chk('build md', q, 'Results for', c[0], t.results_for)
    chk('build md', q, 'Quarter', c[1], t.quarter)
    chk('build md', q, 'Trades', c[2], str(t.trades))
    chk('build md', q, 'Up', c[3], str(t.up))
    chk('build md', q, 'Avg vs Nifty', c[4], f2(t.avg))
    chk('build md', q, 'Unhedged avg', c[5], f2(t.unhedged))
    chk('build md', q, 'W RSI<=50 avg (n)', c[6], f'{f2(t.W_LO_avg)} ({t.W_LO_n})')
    chk('build md', q, 'All winners avg (n)', c[7], f'{f2(t.W_avg)} ({t.W_n})')
    chk('build md', q, 'All F&O avg', c[8], f2(t.all_avg))
    for a, b2 in zip(c[9].split(', '), t.stocks.split(', ')):
        chk('build md', q, 'stock ' + b2.split()[0], a, b2)
    if len(c[9].split(', ')) != len(t.stocks.split(', ')):
        chk('build md', q, 'stock count', str(len(c[9].split(', '))), str(t.trades))
tot = bmd[22]
S_all = dict(n=len(T), up=int((T.vsN_net > 0).sum()), avg=T.vsN_net.mean(), raw=T.raw_net.mean())
chk('build md', 'All', 'Trades', tot[2], f"**{S_all['n']}**")
chk('build md', 'All', 'Up', tot[3], f"**{S_all['up']}**")
chk('build md', 'All', 'Avg', tot[4], f"**{f2(S_all['avg'])}**")
chk('build md', 'All', 'Unhedged', tot[5], f"**{f2(S_all['raw'])}**")
chk('build md', 'All', 'W_LO', tot[6], f"{f2(U.loc[U.W_LO, 'vsN_net'].mean())} ({int(U.W_LO.sum())})")
chk('build md', 'All', 'W', tot[7], f"{f2(U.loc[U.W, 'vsN_net'].mean())} ({int(U.W.sum())})")
chk('build md', 'All', 'all', tot[8], f2(U.vsN_net.mean()))
chk('build md', 'All', 'q+', tot[9], f"{int((TQ.avg > 0).sum())}/22 quarters positive")
# rebuild markdown
rmd = parse_md(f'{REB}/per_quarter.md', 'rebuild')
for q, c in enumerate(rmd[:22]):
    t = TQ.loc[q]
    chk('rebuild md', q, '#', c[0], str(q))
    chk('rebuild md', q, 'Results for', c[1], t.results_for)
    chk('rebuild md', q, 'Quarter', c[2], t.quarter)
    chk('rebuild md', q, 'Trades', c[3], str(t.trades))
    chk('rebuild md', q, 'Avg', c[4], f2(t.avg))
    for a, b2 in zip(c[5].split(', '), t.stocks.split(', ')):
        a2 = a.replace('(', '').replace(')', '')
        chk('rebuild md', q, 'stock ' + b2.split()[0], a2, b2)
BAD = pd.DataFrame(bad)
BAD.to_csv(f'{HERE}/markdown_cell_mismatches.csv', index=False)
ncell = 22 * 9 + int(TQ.trades.sum()) + 8
P(f'build markdown: {ncell} cells checked, mismatches {int((BAD.table == "build md").sum()) if len(BAD) else 0}; '
  f'rebuild markdown mismatches {int((BAD.table == "rebuild md").sum()) if len(BAD) else 0}')
if len(BAD):
    for r in BAD.itertuples():
        tv = ''
        if r.column.startswith('stock '):
            s_ = r.column.split()[1]
            tv = f" (truth vsN_net {T.loc[(T.symbol == s_) & (T.qn == r.qn), 'vsN_net'].iloc[0]:.6f})"
        P(f'  {r.table} qn {r.qn} {r.column}: shown {r.shown!r} recomputed {r.recomputed!r}{tv}')

# ===================================================================== 4. headline + bullets
P('\n' + '=' * 100 + '\n4. HEADLINE AND PER-QUARTER BULLETS recomputed\n' + '=' * 100)
v = T.vsN_net.to_numpy()
srt = np.sort(v)
qm = TQ.set_index('qn').avg
fh = T.qn <= 13


def qstats(frame, col):
    qmm = frame.groupby('qn')[col].mean()
    return int((qmm > 0).sum()), int((qmm < 0).sum()), int((qmm[qmm.index <= 13] > 0).sum()), \
        int((qmm[qmm.index >= 14] > 0).sum()), len(qmm)


neg = (qm < 0).to_numpy()
best, cur, end = 0, 0, None
for i, x in enumerate(neg):
    cur = cur + 1 if x else 0
    if cur > best:
        best, end = cur, i
wbest, cur = 0, 0
for x in (qm > 0).to_numpy():
    cur = cur + 1 if x else 0
    wbest = max(wbest, cur)
b_t, w_t = T.loc[T.vsN_net.idxmax()], T.loc[T.vsN_net.idxmin()]
qr = qstats(T, 'raw_net')
yr = T.groupby('year').vsN_net.agg(['size', 'mean'])
tafa_rt = pd.read_csv(f'{TAFA}/results_tests.csv')
wr = tafa_rt[(tafa_rt.test == 'W_RSI_HI') & (tafa_rt.H == 20)].iloc[0]
negq = TQ[TQ.avg < 0]
H = [  # (claim text, claimed, recomputed (display), detail)
    ('trades', '232', str(len(T)), ''),
    ('distinct stocks', '123', str(T.symbol.nunique()), ''),
    ('average vsN_net', '+2.42', f2(v.mean()), f'{v.mean():.4f}'),
    ('median', '+2.21', f2(np.median(v)), f'{np.median(v):.4f}'),
    ('% trades up', '61.6', f'{(v > 0).mean() * 100:.1f}', ''),
    ('quarters with trades', '22', str(T.qn.nunique()), ''),
    ('quarters positive / negative', '17 / 5', f'{int((qm > 0).sum())} / {int((qm < 0).sum())}', ''),
    ('longest losing streak', '3 (Q2 FY22 to Q4 FY22)',
     f'{best} ({TQ.loc[end - best + 1, "quarter"]} to {TQ.loc[end, "quarter"]})', ''),
    ('first 14: avg / n / quarters +', '+2.65 / 122 / 10 of 14',
     f'{f2(v[fh].mean())} / {int(fh.sum())} / {int((qm[:14] > 0).sum())} of 14', ''),
    ('last 8: avg / n / quarters +', '+2.16 / 110 / 7 of 8',
     f'{f2(v[~fh].mean())} / {int((~fh).sum())} / {int((qm[14:] > 0).sum())} of 8', ''),
    ('without best 5 / best 10', '+1.83 / +1.42', f'{f2(srt[:-5].mean())} / {f2(srt[:-10].mean())}', ''),
    ('best trade', 'PFC Q2 FY24 +30.39', f'{b_t.symbol} {b_t.quarter} {f2(b_t.vsN_net)}', f'{b_t.period}'),
    ('worst trade', 'INDUSINDBK Q2 FY22 -19.55', f'{w_t.symbol} {w_t.quarter} {f2(w_t.vsN_net)}', f'{w_t.period}'),
    ('unhedged raw_net avg / quarters + / first14 / last8', '+2.82 / 16 of 22 / +4.13 / +1.37',
     f'{f2(T.raw_net.mean())} / {qr[0]} of {qr[4]} / {f2(T.raw_net[fh].mean())} / {f2(T.raw_net[~fh].mean())}', ''),
    ('take-profit net / % up', '+1.08 / 69.4', f'{f2(T.tp_net.mean())} / {(T.tp_net > 0).mean() * 100:.1f}', ''),
    ('all winners n / avg', '392 / +1.45', f"{int(U.W.sum())} / {f2(U.loc[U.W, 'vsN_net'].mean())}", ''),
    ('RSI<=50 winners n / avg', '160 / +0.04', f"{int(U.W_LO.sum())} / {f2(U.loc[U.W_LO, 'vsN_net'].mean())}", ''),
    ('all F&O results n / avg', '3,280 / +0.42', f"{len(U):,} / {f2(U.vsN_net.mean())}", ''),
    ('by year', '2021 -0.70 (25), 2022 -0.81 (25), 2023 +7.22 (36), 2024 +2.84 (39), 2025 +2.35 (52), 2026 +1.93 (55)',
     ', '.join(f'{y} {f2(r["mean"])} ({int(r["size"])})' for y, r in yr.iterrows()), ''),
    ('Holm(117) / Westfall-Young', '1.00 / 0.54', f"{wr.p_holm117:.2f} / {wr.p_westfall_young:.2f}",
     'tafa results_tests.csv W_RSI_HI H20'),
    ('single-test luck p', '0.0094', f"{wr.p_W_ELIG:.4f} (pre-registered run); build re-draw 0.0094",
     'two Monte Carlo runs of 20,000 draws; MC se ~0.0007'),
    ('negative quarters', 'Q2 FY22 -2.47, Q3 FY22 -0.08, Q4 FY22 -0.13, Q2 FY23 -2.47, Q4 FY26 -0.15',
     ', '.join(f'{r.quarter} {f2(r.avg)}' for r in negq.itertuples()),
     ', '.join(f'{r.quarter} {r.avg:.4f}' for r in negq.itertuples())),
    ('negative quarters within 0.15 of zero', 'Two of the five',
     f'{int((negq.avg.abs() <= 0.15).sum())} of the five at |avg| <= 0.15 (display); '
     f'{int((negq.avg.abs() < 0.155).sum())} round to <= 0.15', ''),
    ('longest winning streak', '13', str(wbest), ''),
    ('beat all winners same quarter', '15 of 22', f'{int((TQ.avg > TQ.W_avg).sum())} of 22', ''),
    ('beat RSI<=50 winners same quarter', '15 of 22',
     f'{int((TQ.avg > TQ.W_LO_avg).sum())} of {int(TQ.W_LO_avg.notna().sum())}', ''),
    ('quarter-weighted means main / W / W_LO', '+2.73 / +1.73 / +0.86',
     f'{f2(TQ.avg.mean())} / {f2(TQ.W_avg.mean())} / {f2(TQ.W_LO_avg.mean())}', ''),
    ('trades per quarter min / max / median', '3 / 23 / 9',
     f'{TQ.trades.min()} / {TQ.trades.max()} / {TQ.trades.median():.0f}', ''),
    ('total vsN_net (pct of one position)', '+561.0', f'{v.sum():+.1f}', ''),
    ('pre-registered d_W (same-quarter diff vs all winners)', '+0.63 (variants table)',
     f"{f2((T.vsN_net - T.qn.map(TQ.set_index('qn').W_avg)).mean())}", f'tafa dW {wr.dW:.4f}'),
]
HD = pd.DataFrame(H, columns=['item', 'claimed', 'recomputed', 'detail'])
HD['ok'] = [c.split(' (')[0].replace('+', '') == r.split(' (')[0].replace('+', '') or c == r for c, r in
            zip(HD.claimed, HD.recomputed)]
HD.to_csv(f'{HERE}/headline_check.csv', index=False)
P(HD.to_string(index=False))

# ===================================================================== 5. corrected final per-quarter markdown
md = ['| # | Results for | Quarter | Trades | Up | Avg vs Nifty (net) | Median | Unhedged avg | '
      'Winners RSI<=50 avg (n) | All winners avg (n) | Main minus all winners | All F&O results avg (n) | '
      'Stocks (% vs Nifty, net) |', '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
for r in TQ.itertuples():
    md.append(f'| {r.qn} | {r.results_for} | {r.quarter} | {r.trades} | {r.up} | {f2(r.avg)} | {f2(r.median)} | '
              f'{f2(r.unhedged)} | {f2(r.W_LO_avg)} ({r.W_LO_n}) | {f2(r.W_avg)} ({r.W_n}) | {f2(r.avg - r.W_avg)} | '
              f'{f2(r.all_avg)} ({r.all_n}) | {r.stocks} |')
md.append(f"| | **All 22** | | **{len(T)}** | **{S_all['up']}** | **{f2(S_all['avg'])}** | **{f2(np.median(v))}** | "
          f"**{f2(S_all['raw'])}** | {f2(U.loc[U.W_LO, 'vsN_net'].mean())} ({int(U.W_LO.sum())}) | "
          f"{f2(U.loc[U.W, 'vsN_net'].mean())} ({int(U.W.sum())}) | "
          f"{f2((T.vsN_net - T.qn.map(TQ.set_index('qn').W_avg)).mean())} (d_W) | {f2(U.vsN_net.mean())} ({len(U)}) | "
          f"{int((TQ.avg > 0).sum())}/22 quarters positive; quarter-weighted {f2(TQ.avg.mean())} |")
MD = '\n'.join(md)
open(f'{HERE}/per_quarter_recomputed.md', 'w').write(MD + '\n')
P('\nrecomputed per-quarter markdown -> per_quarter_recomputed.md (final table with next-open column: final_table.py)')
P(MD)
