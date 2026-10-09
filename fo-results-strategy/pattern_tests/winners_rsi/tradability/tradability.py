#!/usr/bin/env python3
"""Practitioner check of the pre-registered rule "results winners with RSI above 50" (W_RSI_HI, H20).

MAIN RULE (unchanged): XN > 4 on reaction day k (stock adjusted return minus Nifty 50 return, percent) AND cutoff
RSI(14) > 50; buy close k, sell close k+20, short Nifty 50 for the same value; vsN_net = (stock - Nifty)*100 - 0.19.
Everything here beyond reproducing that number is a tradability diagnostic: realistic entries, timing, costs, hedge,
capital / book, survivorship, overlap with the plain winner drift, and build checks.

Reads (read-only): sector_lab/data/{sessions,returns,index_close,events}.csv, ta/build/{adjusted_ohlcv.csv.gz,
events_ta.csv}, tafa/C_post_results/{trades,features}.csv, fa/build/fa_panel.csv, report/nse_prices.db (idx table:
Nifty 50 open, Nifty 50 Futures Index; px / ca for spot checks), winners_rsi/build/trades.csv (to compare).
Writes only into this folder.
"""
import os
import sqlite3

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.environ.get('LAB_ROOT', os.path.abspath(os.path.join(HERE, '..', '..')))  # scratch data folder
DATA = f'{SP}/sector_lab/data'
TAFA = f'{SP}/tafa/C_post_results'
DB = f'{SP}/report/nse_prices.db'
SEED = 20261009
NDRAW = 20000
rng = np.random.default_rng(SEED)
LOG = open(f'{HERE}/tradability.log', 'w')
pd.set_option('display.width', 250, 'display.max_rows', 500, 'display.max_columns', 60, 'display.max_colwidth', 200)


def P_(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')
    LOG.flush()


def sg(x, d=2):
    return 'n/a' if x is None or not np.isfinite(x) else f'{x:+.{d}f}'


# ===================================================================================================== prices
ses = pd.read_csv(f'{DATA}/sessions.csv')
DAYS = ses.day.to_numpy()
DIX = {d: i for i, d in enumerate(DAYS)}
NS = len(DAYS)
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
assert (ret.index == DAYS).all()
SYMS = ret.columns.tolist()
SYM = {s: j for j, s in enumerate(SYMS)}
R = ret.to_numpy(float)
PX = np.cumprod(1.0 + np.nan_to_num(R), axis=0)             # blank daily return = 0 (as the build)
CVALID = np.cumsum(~np.isnan(R), axis=0)
NIF = pd.read_csv(f'{DATA}/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])['Nifty 50']
assert (NIF.index == DAYS).all()
NC = NIF.to_numpy(float)
NRET = np.r_[np.nan, NC[1:] / NC[:-1] - 1]

con = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
idx = pd.read_sql("SELECT day, name, open, close FROM idx WHERE name IN ('Nifty 50','Nifty 50 Futures Index')", con)
ix_n = idx[idx.name == 'Nifty 50'].set_index('day').reindex(DAYS)
assert np.allclose(ix_n.close.to_numpy(float), NC), 'DB Nifty close != index_close.csv'
NO = ix_n.open.to_numpy(float)                             # Nifty 50 open
ix_f = idx[idx.name == 'Nifty 50 Futures Index'].set_index('day').reindex(DAYS)
FC = ix_f.close.to_numpy(float)                            # Nifty 50 Futures Index (rolling near-month futures)
ca = pd.read_sql('SELECT symbol, ex_date, kind, factor, subject FROM ca', con)
rawpx = pd.read_sql('SELECT day, symbol, open, close, prevclose FROM px', con)
con.close()

ao = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'open', 'close'])
ao = ao[ao.symbol.isin(SYM) & ao.day.isin(DIX)]
AO = np.full((NS, len(SYMS)), np.nan)
AC = np.full((NS, len(SYMS)), np.nan)
ii_, jj_ = ao.day.map(DIX).to_numpy(int), ao.symbol.map(SYM).to_numpy(int)
AO[ii_, jj_] = ao.open.to_numpy(float)
AC[ii_, jj_] = ao.close.to_numpy(float)
OC = AC / AO                                               # same-day close/open (adjustment factor cancels)
# check vs sector_lab intraday.csv (close/open - 1)
intr = pd.read_csv(f'{DATA}/intraday.csv', index_col=0).reindex(columns=SYMS).to_numpy(float)
both = np.isfinite(intr) & np.isfinite(OC)
P_(f'CHECK adjusted_ohlcv close/open vs intraday.csv: {both.sum():,} cells, '
   f'max abs diff {np.nanmax(np.abs(OC[both] - 1 - intr[both])):.2e}, '
   f'share within 1e-6: {np.mean(np.abs(OC[both] - 1 - intr[both]) < 1e-6):.4f}')

# ===================================================================================================== universe
tr0 = pd.read_csv(f'{TAFA}/trades.csv')
fe = pd.read_csv(f'{TAFA}/features.csv')
ev = pd.read_csv(f'{DATA}/events.csv')
d = tr0[['symbol', 'qn', 'quarter', 'reaction_day', 'i_react', 'XN', 'W', 'RSI_HI', 'W_RSI_HI', 'raw_H20',
         'nifty_H20']].merge(fe[['symbol', 'qn', 'timing', 'cut_rsi14', 'i_cut', 'i_rd']], on=['symbol', 'qn'],
                             how='left', validate='1:1')
d = d.merge(ev[['symbol', 'qn', 'period', 'results_date', 'results_time', 'industry', 'in_fo']].rename(
    columns={'in_fo': 'ev_in_fo'}), on=['symbol', 'qn'], how='left', validate='1:1')
assert len(d) == 3280
K = d.i_react.to_numpy(int)
J = d.symbol.map(SYM).to_numpy(int)
d['W'] = d.XN > 4
d['HI'] = d.cut_rsi14 > 50
d['MAIN'] = d.W & d.HI
d['COMP'] = d.W & ~d.HI
assert d.MAIN.sum() == 232 and d.W.sum() == 392 and d.COMP.sum() == 160 and (d.MAIN == (d.W_RSI_HI == 1)).all()
d['FIRST'] = d.qn <= 13
QLAB = ev.groupby('qn')[['period', 'quarter']].first()
mins = pd.to_datetime(d.results_time, format='%H:%M').dt.hour * 60 + pd.to_datetime(d.results_time,
                                                                                     format='%H:%M').dt.minute
d['tclass'] = np.select([d.timing == 'Before open', (d.timing == 'During market') & (mins < 900),
                         (d.timing == 'During market') & (mins >= 900), d.timing == 'After close',
                         d.timing == 'Non-trading day'],
                        ['1 Before open', '2 During market <15:00', '3 During market 15:00-15:29', '4 After close',
                         '5 Non-trading day'], 'other')
assert (d.tclass != 'other').all()

# ===================================================================================================== trades
assert (K + 21 <= NS - 1).all()


def comp(a, b):
    """compounded adjusted stock return from close a to close b (rows a+1..b), blank = 0."""
    return PX[b, J] / PX[a, J] - 1


C_E0 = 0.19
d['E0_stk'] = comp(K, K + 20)
d['E0_nif'] = NC[K + 20] / NC[K] - 1
assert np.allclose(d.E0_stk * 100, d.raw_H20, atol=6e-5) and np.allclose(d.E0_nif * 100, d.nifty_H20, atol=6e-5)
blank = 21 - (CVALID[K + 21, J] - CVALID[K, J])
assert (blank <= 2).all()
# XN re-derived
assert np.allclose((R[K, J] - NRET[K]) * 100, d.XN, atol=6e-5)
# E1a: buy the open of k+1, sell the close of k+21 ; Nifty short at the open of k+1
oc1 = OC[K + 1, J]
d['traded_k1'] = np.isfinite(oc1) & np.isfinite(R[K + 1, J])
d['E1a_stk'] = oc1 * PX[K + 21, J] / PX[K + 1, J] - 1
d['E1a_nif'] = NC[K + 21] / NO[K + 1] - 1
# E1a20: open k+1 -> close k+20 (20 closes after entry including the entry day)
d['E1a20_stk'] = oc1 * PX[K + 20, J] / PX[K + 1, J] - 1
d['E1a20_nif'] = NC[K + 20] / NO[K + 1] - 1
# E1b: buy the close of k+1, sell close of k+21
d['E1b_stk'] = comp(K + 1, K + 21)
d['E1b_nif'] = NC[K + 21] / NC[K + 1] - 1
# E0p: stock bought at close k in NSE's post-close session (at the closing price), Nifty short only at the open of
# k+1 (F&O does not trade after 15:30); exit close k+20
d['E0p_stk'] = d.E0_stk
d['E0p_nif'] = NC[K + 20] / NO[K + 1] - 1
# decomposition of the lost first day
d['gap_stk'] = 1 / oc1 * (1 + R[K + 1, J]) - 1               # close k -> open k+1 (adjusted)
d['gap_nif'] = NO[K + 1] / NC[K] - 1
d['d1_vsN'] = (np.nan_to_num(R[K + 1, J]) - NRET[K + 1]) * 100   # close k -> close k+1, vs Nifty
d['gap_vsN'] = (d.gap_stk - d.gap_nif) * 100
# cross-check E1a stock with adjusted levels directly
alt = AC[K + 21, J] / AO[K + 1, J] - 1
okalt = np.isfinite(alt) & np.isfinite(d.E1a_stk)
P_(f'CHECK E1a stock return via compounded returns vs adjusted close(k+21)/open(k+1): n {okalt.sum()}, '
   f'median abs diff {np.median(np.abs(alt[okalt] - d.E1a_stk[okalt])) * 100:.4f} pts, '
   f'max {np.max(np.abs(alt[okalt] - d.E1a_stk[okalt])) * 100:.3f} pts')
# Nifty futures-index hedge (same windows)
d['E0_fut'] = FC[K + 20] / FC[K] - 1
d['E1a_fut'] = FC[K + 21] / FC[K + 1] * (NC[K + 1] / NO[K + 1]) - 1   # futures index has no open: spot open->close
                                                                       # for day k+1, futures close-close after

ENTRIES = {'E0': 'close k -> close k+20 (study, pre-registered)',
           'E0p': 'stock at close k (post-close session), Nifty short at open k+1 -> close k+20',
           'E1a': 'open k+1 -> close k+21 (next-session open)',
           'E1a20': 'open k+1 -> close k+20',
           'E1b': 'close k+1 -> close k+21 (next-session close)'}
for e in ENTRIES:
    d[f'{e}_gross'] = (d[f'{e}_stk'] - d[f'{e}_nif']) * 100
    d[f'{e}_raw'] = d[f'{e}_stk'] * 100
nk1 = (~d.traded_k1).sum()
P_(f'trades without a k+1 open (not traded on k+1): {nk1} of 3,280; among MAIN {(~d.traded_k1 & d.MAIN).sum()}')
P_('CHECK: E0 stock/Nifty returns and XN recomputed from returns.csv / index_close.csv equal tafa trades.csv (3,280); '
   'all have k+21 and <= 2 blanks')
bt = pd.read_csv(f'{SP}/winners_rsi/build/trades.csv')
mm = bt.merge(d[['symbol', 'qn', 'E0_gross']], on=['symbol', 'qn'], how='left')
assert len(bt) == 232 and np.allclose(mm.vsN_net, mm.E0_gross - 0.19, atol=1e-3)
P_('CHECK: winners_rsi/build/trades.csv (232) vsN_net equals my E0 recomputation (abs diff < 1e-3)')

GROUPS = {'MAIN W&RSI>50': d.MAIN, 'W&RSI<=50 (complement)': d.COMP, 'all winners XN>4': d.W,
          'all F&O results': pd.Series(True, index=d.index)}


def stats(m, col, cost):
    x = d[m & d[col].notna()]
    v = x[col].to_numpy(float) - cost
    if len(v) == 0:
        return {}
    qm = pd.Series(v, index=x.index).groupby(x.qn).mean()
    srt = np.sort(v)
    f, l = x.FIRST.to_numpy(), ~x.FIRST.to_numpy()
    tq = qm.mean() / (qm.std(ddof=1) / np.sqrt(len(qm))) if len(qm) > 2 else np.nan
    return {'n': len(v), 'mean': v.mean(), 'median': np.median(v), 'up_pct': 100 * np.mean(v > 0),
            'q_pos': int((qm > 0).sum()), 'q_with': len(qm), 'qw_mean': qm.mean(), 't_quarters': tq,
            'first14': v[f].mean() if f.any() else np.nan, 'last8': v[l].mean() if l.any() else np.nan,
            'wo_best5': srt[:-5].mean() if len(v) > 5 else np.nan, 'worst': srt[0], 'best': srt[-1]}


# ===================================================================================================== 1. entries
P_('\n' + '=' * 110 + '\n1. ENTRY TIMING (signal XN > 4 is only known at the close of k)')
for e, lab in ENTRIES.items():
    P_(f'  {e:6s} {lab}')
rows = []
for e in ENTRIES:
    for g, m in GROUPS.items():
        for cost_lab, c in (('gross', 0.0), ('net 0.19', 0.19), ('net 0.30', 0.30), ('net 0.50', 0.50)):
            s = stats(m, f'{e}_gross', c)
            rows.append({'entry': e, 'group': g, 'measure': f'vsN {cost_lab}', **s})
        for cost_lab, c in (('raw net 0.17', 0.17), ('raw net 0.28', 0.28), ('raw net 0.48', 0.48)):
            s = stats(m, f'{e}_raw', c)
            rows.append({'entry': e, 'group': g, 'measure': cost_lab, **s})
ENT = pd.DataFrame(rows)
ENT.to_csv(f'{HERE}/entries_costs.csv', index=False, float_format='%.4f')
show = ENT[ENT.measure == 'vsN net 0.19'][['entry', 'group', 'n', 'mean', 'median', 'up_pct', 'q_pos', 'q_with',
                                           'first14', 'last8', 'wo_best5', 't_quarters']]
P_(show.to_string(index=False, float_format=lambda x: f'{x:+.2f}'))
P_('\nMAIN minus all winners, and MAIN minus complement, per entry (vsN, costs cancel):')
for e in ENTRIES:
    a = d.loc[d.MAIN, f'{e}_gross'].mean()
    b = d.loc[d.W, f'{e}_gross'].mean()
    c = d.loc[d.COMP, f'{e}_gross'].mean()
    P_(f'  {e:6s} MAIN {a:+.2f}  all W {b:+.2f}  COMP {c:+.2f}   MAIN-W {a - b:+.2f}   MAIN-COMP {a - c:+.2f}')
P_('\nWhat the first day costs (MAIN / all winners / complement), means in percent:')
for g, m in list(GROUPS.items())[:3]:
    x = d[m]
    P_(f'  {g:24s} overnight gap close k->open k+1 vs Nifty {x.gap_vsN.mean():+.2f} (median {x.gap_vsN.median():+.2f}),'
       f' day k+1 close-close vs Nifty {x.d1_vsN.mean():+.2f} (median {x.d1_vsN.median():+.2f}); '
       f'E0 gross {x.E0_gross.mean():+.2f} -> E1a gross {x.E1a_gross.mean():+.2f} -> E1b gross {x.E1b_gross.mean():+.2f}')

# luck test under each entry: random same-size picks per quarter from that quarter's winners
P_('\nLuck p (one-sided) per entry: 20,000 draws, per quarter the same number of trades drawn from that quarter\'s'
   ' winners (all 392 have RSI). Single-test p (the 117-test family is not redone here).')
LUCK = []
wq = d[d.W].copy()
for e in ['E0', 'E0p', 'E1a', 'E1a20', 'E1b']:
    col = f'{e}_gross'
    actual = d.loc[d.MAIN, col].mean()
    groups = []
    for q, g in wq.groupby('qn'):
        groups.append((g[col].to_numpy(float), int(g.MAIN.sum())))
    tot = sum(kq for _, kq in groups)
    draws = np.zeros(NDRAW)
    for vals, kq in groups:
        if kq == 0:
            continue
        idxs = np.argsort(rng.random((NDRAW, len(vals))), axis=1)[:, :kq]
        draws += vals[idxs].sum(1)
    draws /= tot
    p = (1 + np.sum(draws >= actual - 1e-12)) / (1 + NDRAW)
    LUCK.append({'entry': e, 'actual_gross': actual, 'draw_mean': draws.mean(), 'draw_p95': np.quantile(draws, .95),
                 'p_one_sided': p})
    P_(f'  {e:6s} actual {actual:+.3f}  random-winner mean {draws.mean():+.3f}  95th {np.quantile(draws, .95):+.3f}'
       f'  p {p:.4f}')
pd.DataFrame(LUCK).to_csv(f'{HERE}/luck_by_entry.csv', index=False, float_format='%.4f')

# per quarter, E0 vs E1a, main / complement / all winners
pq = []
for q in range(22):
    r = {'Results for': QLAB.loc[q, 'period'], 'Quarter': QLAB.loc[q, 'quarter'], 'qn': q}
    for g, m in (('MAIN', d.MAIN), ('COMP', d.COMP), ('W', d.W)):
        x = d[m & (d.qn == q)]
        r[f'{g}_n'] = len(x)
        for e in ('E0', 'E1a', 'E1b'):
            r[f'{g}_{e}_net'] = (x[f'{e}_gross'] - 0.19).mean() if len(x) else np.nan
        r[f'{g}_E1a_net030'] = (x['E1a_gross'] - 0.30).mean() if len(x) else np.nan
    pq.append(r)
PQ = pd.DataFrame(pq)
PQ.to_csv(f'{HERE}/per_quarter_entries.csv', index=False, float_format='%.3f')
P_('\nPer quarter, vsN net 0.19 (MAIN E0 / E1a / E1b; complement E1a; all winners E1a) and MAIN E1a at 0.30:')
P_(PQ[['Results for', 'Quarter', 'MAIN_n', 'MAIN_E0_net', 'MAIN_E1a_net', 'MAIN_E1b_net', 'MAIN_E1a_net030', 'COMP_n',
       'COMP_E1a_net', 'W_n', 'W_E1a_net']].to_string(index=False, float_format=lambda x: f'{x:+.2f}'))
for e in ('E0', 'E1a', 'E1b'):
    c = PQ[f'MAIN_{e}_net']
    P_(f'  MAIN {e}: quarters positive {int((c > 0).sum())}/22; quarter-weighted mean {c.mean():+.2f}; '
       f'MAIN beats all-winners same quarter (same entry) in {int((PQ[f"MAIN_{e}_net"] > PQ[f"W_{e}_net"]).sum())}/22')

# ===================================================================================================== 2. timing
P_('\n' + '=' * 110 + '\n2. TIMING')
P_('i_react rule check over all 4,462 events.csv rows: Before open / During market -> k = results_date session; '
   'After close -> next session; Non-trading day -> first session after results_date.')
evc = ev.copy()
mismatch = 0
for r in evc.itertuples():
    dd = r.results_date
    if r.timing in ('Before open', 'During market'):
        exp = DIX.get(dd, -1)
    elif r.timing == 'After close':
        exp = DIX[dd] + 1 if dd in DIX else -1
    else:
        exp = int(np.searchsorted(DAYS, dd, side='right')) if dd not in DIX else -1
    mismatch += int(exp != r.i_react)
P_(f'  mismatches: {mismatch};  i_rd - i_cut == 2 for all: {bool(((evc.i_rd - evc.i_cut) == 2).all())};  '
   f'i_cut < i_react for all: {bool((evc.i_cut < evc.i_react).all())}')
P_('  timing class boundaries in the data: Before open 00:00-09:13, During market 09:21-15:29, After close 15:30-23:50; '
   'Non-trading day = weekend/holiday dates (no session on results_date)')
ex = []
for t in ['Before open', 'During market', 'After close', 'Non-trading day']:
    x = d[(d.timing == t) & d.MAIN].head(3)
    ex.append(x)
ex.append(d[(d.tclass == '3 During market 15:00-15:29') & d.W].head(3))
EX = pd.concat(ex)
EX['results_weekday'] = pd.to_datetime(EX.results_date).dt.day_name().str[:3]
EX['reaction_weekday'] = pd.to_datetime(EX.reaction_day).dt.day_name().str[:3]
EX['cutoff_day'] = DAYS[EX.i_cut.to_numpy(int)]
P_('  examples (MAIN trades, plus late-session winners):')
P_(EX[['symbol', 'quarter', 'results_date', 'results_weekday', 'results_time', 'timing', 'cutoff_day', 'reaction_day',
       'reaction_weekday', 'XN']].to_string(index=False))
# spot check XN of the examples against raw prices in the DB
rp = rawpx.set_index(['symbol', 'day'])
for r in EX.itertuples():
    try:
        x = rp.loc[(r.symbol, r.reaction_day)]
        rr = (x.close / x.prevclose - 1 - NRET[r.i_react]) * 100
        P_(f'    raw DB check {r.symbol} {r.reaction_day}: close/prevclose - Nifty = {rr:+.2f} vs XN {r.XN:+.2f}')
    except KeyError:
        P_(f'    raw DB check {r.symbol} {r.reaction_day}: no raw row')
# where is the reaction? median |stock - Nifty| on days k-1, k, k+1 by announcement time (all 3,280 in_fo results)
d['ax_m1'] = np.abs(R[K - 1, J] - NRET[K - 1]) * 100
d['ax_0'] = np.abs(R[K, J] - NRET[K]) * 100
d['ax_p1'] = np.abs(R[K + 1, J] - NRET[K + 1]) * 100
d['XN_p1'] = (R[K + 1, J] - NRET[K + 1]) * 100
hb = pd.cut(mins, [0, 555, 690, 780, 840, 870, 900, 930, 1440],
            labels=['<09:15', '09:15-11:30', '11:30-13:00', '13:00-14:00', '14:00-14:30', '14:30-15:00', '15:00-15:30',
                    '>=15:30'], right=False)
d['hbucket'] = np.where(d.timing == 'Non-trading day', 'non-trading day', hb.astype(str))
AX = d.groupby('hbucket').agg(n=('XN', 'size'), med_abs_k_minus1=('ax_m1', 'median'), med_abs_k=('ax_0', 'median'),
                              med_abs_k_plus1=('ax_p1', 'median'), winners=('W', 'sum'), main=('MAIN', 'sum'))
AX.to_csv(f'{HERE}/reaction_by_time.csv', float_format='%.3f')
P_('\n  Where the reaction happens, by filing time (median |stock - Nifty| %, all in_fo results):')
P_(AX.to_string(float_format=lambda v: f'{v:.2f}'))
late = d[d.tclass == '3 During market 15:00-15:29']
lw = late[(late.XN_p1 > 4) & late.HI]
P_(f'  Results filed 15:00-15:29 ({len(late)}): the reaction is on k+1, not k. Winners on k: {int(late.W.sum())}. '
   f'DIAGNOSTIC (not the rule): if k were moved to k+1 for them, {int((late.XN_p1 > 4).sum())} would be winners, '
   f'{len(lw)} with RSI > 50, earning close k+1 -> close k+21 vs Nifty net 0.19: '
   f'{(lw.E1b_gross - .19).mean():+.2f} (these are missed by the rule, not mis-traded)')
TROWS = []
for tc in sorted(d.tclass.unique()):
    for g, m in list(GROUPS.items())[:3]:
        x = d[m & (d.tclass == tc)]
        if len(x) == 0:
            continue
        TROWS.append({'timing': tc, 'group': g, 'n': len(x), 'E0_net': (x.E0_gross - .19).mean(),
                      'E1a_net': (x.E1a_gross - .19).mean(), 'E1b_net': (x.E1b_gross - .19).mean(),
                      'E0_up_pct': 100 * np.mean(x.E0_gross - .19 > 0), 'gap_vsN': x.gap_vsN.mean(),
                      'day1_vsN': x.d1_vsN.mean(), 'XN_mean': x.XN.mean(),
                      'first14_E0': (x[x.FIRST].E0_gross - .19).mean(), 'last8_E0': (x[~x.FIRST].E0_gross - .19).mean()})
TT = pd.DataFrame(TROWS)
TT.to_csv(f'{HERE}/timing.csv', index=False, float_format='%.3f')
P_('\n  by timing class (vsN net 0.19):')
P_(TT.to_string(index=False, float_format=lambda x: f'{x:+.2f}'))

# ===================================================================================================== 3. costs / hedge
P_('\n' + '=' * 110 + '\n3. COSTS AND HEDGE')
for e in ('E0', 'E1a'):
    for g, m in list(GROUPS.items())[:3]:
        x = d[m]
        gv, rv = x[f'{e}_gross'], x[f'{e}_raw']
        P_(f'  {e:4s} {g:24s} hedged gross {gv.mean():+.2f} -> net 0.19 {gv.mean() - .19:+.2f}, 0.30 '
           f'{gv.mean() - .30:+.2f}, 0.50 {gv.mean() - .50:+.2f} (break-even round trip {gv.mean():.2f});  '
           f'unhedged gross {rv.mean():+.2f} -> net 0.17 {rv.mean() - .17:+.2f}, 0.48 {rv.mean() - .48:+.2f};  '
           f'hedged sd {gv.std():.2f} vs unhedged sd {rv.std():.2f}')
# halves at 0.30 / 0.50
P_('\n  MAIN by half at higher costs (vsN):')
for e in ('E0', 'E1a', 'E1b'):
    for c in (0.30, 0.50):
        s = stats(d.MAIN, f'{e}_gross', c)
        P_(f'    {e:4s} cost {c:.2f}: mean {s["mean"]:+.2f}, first14 {s["first14"]:+.2f}, last8 {s["last8"]:+.2f}, '
           f'w/o best 5 {s["wo_best5"]:+.2f}, quarters + {s["q_pos"]}/22, median {s["median"]:+.2f}')
# futures hedge
okf = np.isfinite(d.E0_fut)
diff_all = []
for i in range(NS - 20):
    if np.isfinite(FC[i]) and np.isfinite(FC[i + 20]) and DAYS[i] >= '2021-01-01':
        diff_all.append(((NC[i + 20] / NC[i]) - (FC[i + 20] / FC[i])) * 100)
diff_all = np.array(diff_all)
fr = np.diff(np.log(FC)), np.diff(np.log(NC))
okd = np.isfinite(fr[0]) & (DAYS[1:] >= '2021-01-01')
P_(f'\n  Nifty 50 Futures Index vs Nifty 50 spot since 2021: daily log-return corr {np.corrcoef(fr[0][okd], fr[1][okd])[0, 1]:.4f};'
   f' over every 20-session window, spot minus futures return: mean {diff_all.mean():+.3f}, median '
   f'{np.median(diff_all):+.3f}, 5-95% [{np.quantile(diff_all, .05):+.3f}, {np.quantile(diff_all, .95):+.3f}] '
   f'(this is what a SHORT futures hedge earns over a short spot hedge: the basis converging)')
for g, m in list(GROUPS.items())[:3]:
    x = d[m & okf]
    sp_ = (x.E0_stk - x.E0_nif).mean() * 100
    fu_ = (x.E0_stk - x.E0_fut).mean() * 100
    P_(f'  {g:24s} E0 hedged gross with spot {sp_:+.2f} vs with Nifty futures index {fu_:+.2f} (n {len(x)}); '
       f'carry earned by the short {fu_ - sp_:+.2f}')
P_('  NOTE: the futures carry is roughly the interest rate minus the Nifty dividend yield. It is not a free gain: '
   'the long stock leg ties up cash (the vsN return ignores that funding), so the futures carry roughly pays for '
   'the cash; the study\'s spot hedge without funding is a fair excess-return approximation.')

# ===================================================================================================== 4. book
P_('\n' + '=' * 110 + '\n4. CAPITAL, CONCURRENCY AND THE BOOK (each trade 1 unit of notional, hedged, daily mark to market)')


def book(mask, e, cost):
    """daily P&L of an equal-notional book; cost charged half at entry, half at exit. Returns daily frame, trades."""
    x = d[mask].copy()
    pnl = np.zeros(NS)
    openc = np.zeros(NS, int)      # positions held overnight after this session's close
    newc = np.zeros(NS, int)
    for r in x.itertuples():
        k, j = int(r.i_react), SYM[r.symbol]
        if e == 'E0':
            t0, t1 = k, k + 20
            first_ratio_s, first_ratio_n = None, None
        elif e == 'E1a':
            t0, t1 = k + 1, k + 21
        else:
            raise ValueError
        vs, vn = 1.0, 1.0
        if e == 'E1a':
            # entry at the open of t0, mark at close t0
            vs1 = OC[t0, j]
            vn1 = NC[t0] / NO[t0]
            pnl[t0] += (vs1 - 1) - (vn1 - 1) - cost / 200
            vs, vn = vs1, vn1
            newc[t0] += 1
            openc[t0] += 1
            start = t0 + 1
        else:
            pnl[t0] -= cost / 200
            newc[t0] += 1
            openc[t0] += 1
            start = t0 + 1
        for t in range(start, t1 + 1):
            rs = 0.0 if np.isnan(R[t, j]) else R[t, j]
            rn = NRET[t]
            pnl[t] += vs * rs - vn * rn
            vs *= 1 + rs
            vn *= 1 + rn
            if t < t1:
                openc[t] += 1
        pnl[t1] -= cost / 200
        x.loc[r.Index, 'chk'] = (vs - vn) * 100 - cost
    df = pd.DataFrame({'day': DAYS, 'pnl_units_pct': pnl * 100, 'open_after_close': openc, 'new_entries': newc})
    return df, x


BOOK = {}
for e, cost in (('E0', 0.19), ('E1a', 0.30)):
    for g, m in (('MAIN', d.MAIN), ('W', d.W)):
        df, x = book(m, e, cost)
        assert np.allclose(x.chk, x[f'{e}_gross'] - cost, atol=1e-6)
        BOOK[(e, g)] = (df, x)
        span = df[(df.day >= DAYS[x.i_react.min()]) & (df.day <= DAYS[min(NS - 1, x.i_react.max() + 21)])].copy()
        eq = span.pnl_units_pct.cumsum()
        dd_ = eq - eq.cummax()
        trough = dd_.idxmin()
        peak = eq.loc[:trough].idxmax()
        years = len(span) / 248.0
        peakpos = span.open_after_close.max()
        x['exit_day'] = DAYS[(x.i_react + (20 if e == 'E0' else 21)).to_numpy(int)]
        x['exit_month'] = x.exit_day.str[:7]
        x['net'] = x[f'{e}_gross'] - cost
        mon_exit = x.groupby('exit_month').net.sum()
        allm = pd.Series(0.0, index=sorted(span.day.str[:7].unique()))
        mon_exit = allm.add(mon_exit, fill_value=0)
        mon_mtm = span.groupby(span.day.str[:7]).pnl_units_pct.sum()
        yrs = x.reaction_day.str[:4].value_counts().sort_index()
        res = {'entry': e, 'cost': cost, 'group': g, 'trades': len(x), 'total_pct_units': x.net.sum(),
               'span_sessions': len(span), 'years': years, 'max_open': int(peakpos),
               'max_open_day': span.loc[span.open_after_close.idxmax(), 'day'],
               'mean_open': span.open_after_close.mean(),
               'mean_open_when_any': span.open_after_close[span.open_after_close > 0].mean(),
               'pct_sessions_none': 100 * np.mean(span.open_after_close == 0),
               'p95_open': np.quantile(span.open_after_close, .95), 'max_new_one_day': int(span.new_entries.max()),
               'maxDD_units_pct': dd_.min(), 'dd_peak_day': span.loc[peak, 'day'], 'dd_trough_day': span.loc[trough, 'day'],
               'worst_month_exits': mon_exit.min(), 'worst_month_exits_label': mon_exit.idxmin(),
               'months_negative_exits': int((mon_exit < 0).sum()), 'months_with_exits': int((x.groupby('exit_month').size() > 0).sum()),
               'worst_month_mtm': mon_mtm.min(), 'worst_month_mtm_label': mon_mtm.idxmin(),
               'best_month_mtm': mon_mtm.max(),
               'worst_trade': x.net.min(), 'worst_trade_name': x.loc[x.net.idxmin(), 'symbol'] + ' ' + x.loc[x.net.idxmin(), 'quarter'],
               'trades_per_year': ' '.join(f'{a}:{b}' for a, b in yrs.items()),
               'annual_pct_on_peak_capital': x.net.sum() / years / peakpos,
               'annual_pct_on_peak_capital_incl_margin': x.net.sum() / years / (peakpos * 1.15),
               'maxDD_pct_of_peak_capital': dd_.min() / peakpos}
        BOOK[(e, g, 'res')] = res
        BOOK[(e, g, 'mon')] = pd.DataFrame({'exits_sum': mon_exit, 'mtm': mon_mtm})
BR = pd.DataFrame([BOOK[k] for k in BOOK if len(k) == 3 and k[2] == 'res'])
BR.to_csv(f'{HERE}/book_summary.csv', index=False, float_format='%.3f')
P_(BR.T.to_string())
for (e, g) in (('E0', 'MAIN'), ('E1a', 'MAIN')):
    mon = BOOK[(e, g, 'mon')]
    mon.to_csv(f'{HERE}/book_monthly_{e}_{g}.csv', float_format='%.3f')
    P_(f'\n  {e} {g}: 5 worst calendar months by sum of trades exiting (units = % of one position):')
    P_('   ' + ', '.join(f'{i} {v:+.1f}' for i, v in mon.exits_sum.nsmallest(5).items()))
    P_(f'  {e} {g}: 5 worst calendar months mark-to-market: ' + ', '.join(f'{i} {v:+.1f}' for i, v in mon.mtm.nsmallest(5).items()))
    BOOK[(e, g)][0].to_csv(f'{HERE}/book_daily_{e}_{g}.csv', index=False, float_format='%.4f')

# ===================================================================================================== 5. survivorship
P_('\n' + '=' * 110 + '\n5. SURVIVORSHIP')
fa = pd.read_csv(f'{SP}/fa/build/fa_panel.csv', usecols=['symbol', 'qn', 'in_fo'])
P_(f'  symbols in events.csv / returns.csv: {ev.symbol.nunique()} / {len(SYMS)}; results rows {len(ev)}; '
   f'in_fo True (fa_panel) {int(fa.in_fo.sum())}; events.csv in_fo True {int((ev.in_fo == True).sum())}')
P_('  in_fo True results per quarter: ' + ' '.join(f'{q}:{n}' for q, n in fa.groupby('qn').in_fo.sum().items()))
dis = fa.merge(ev[['symbol', 'qn', 'in_fo']], on=['symbol', 'qn'], suffixes=('_fa', '_ev'))
dis = dis[dis.in_fo_fa.astype(str) != dis.in_fo_ev.astype(str)]
P_('  fa_panel vs events.csv in_fo disagreements:\n' + dis.to_string(index=False))
# in_fo patterns: point-in-time?
pat = fa.sort_values(['symbol', 'qn']).groupby('symbol').in_fo.apply(lambda s: ''.join('1' if v else '0' for v in s))
n_entry = pat.str.contains('01').sum()
n_exit = pat.str.contains('10').sum()
P_(f'  in_fo pattern over each symbol\'s quarters: always 1 {int((pat.str.count("0") == 0).sum())}, never 1 '
   f'{int((pat.str.count("1") == 0).sum())}, symbols with a 0->1 switch (joined F&O in-sample) {n_entry}, with a 1->0 '
   f'switch (left F&O, still in the data) {n_exit}')
P_('  symbols with a 1->0 switch: ' + ', '.join(f'{s}:{p}' for s, p in pat[pat.str.contains("10")].items()))
OLD21 = ('ACC AARTIIND ABFRL AMARAJABAT APOLLOTYRE BALKRISIND BATAINDIA BERGEPAINT CANFINHOME CUB DEEPAKNTR ESCORTS '
         'EXIDEIND GUJGASLTD HDFC IBULHSGFIN IGL IRCTC LALPATHLAB LTTS M&MFIN MGL MINDTREE MRF NAVINFLUOR PEL PFIZER '
         'PVR RAMCOCEM SUNTV TATACHEM TATACOMM TORNTPOWER UBL ZEEL GRANULES IPCALAB METROPOLIS SYNGENE COROMANDEL '
         'DALBHARAT INDIACEM DELTACORP BALRAMCHIN GNFC CHAMBLFERT HINDCOPPER').split()
RENAMED = {'CADILAHC': 'ZYDUSLIFE', 'GMRINFRA': 'GMRAIRPORT', 'L&TFH': 'LTF', 'LTI': 'LTM', 'MCDOWELL-N': 'UNITDSPR',
           'MOTHERSUMI': 'MOTHERSON', 'SRTRANSFIN': 'SHRIRAMFIN', 'TATAMOTORS': 'TMPV'}
absent = [s for s in OLD21 if s not in SYM]
P_(f'  2021-era F&O symbols (from memory, not from the data) with NO rows in the data: {len(absent)}: {" ".join(absent)}')
P_(f'  renamed and present under the new symbol: ' + ', '.join(f'{a}->{b} ({"present" if b in SYM else "absent"})'
                                                            for a, b in RENAMED.items()))
# in_fo results lacking prices
miss = []
for r in d.itertuples():
    j = SYM[r.symbol]
    lastp = np.flatnonzero(np.isfinite(R[:, j]))[-1]
    if not np.isfinite(R[r.i_react, j]) or lastp < r.i_react + 21:
        miss.append((r.symbol, r.qn))
P_(f'  in_fo results whose reaction-day return or k+21 window is missing: {len(miss)} {miss[:10]}')
lastday = {s: DAYS[np.flatnonzero(np.isfinite(R[:, SYM[s]]))[-1]] for s in SYMS}
stale = {s: v for s, v in lastday.items() if v < DAYS[-1]}
P_(f'  symbols whose last price is before {DAYS[-1]}: {stale}')
# main rule by "old guard" (in_fo at qn 0) vs later F&O entrants
first_fo = fa[fa.in_fo == True].groupby('symbol').qn.min()
d['fo_cohort'] = np.where(d.symbol.map(first_fo) <= 1, 'in F&O by qn 1 (2021)', 'joined F&O later')
P_('  NOTE in_fo comes from option-chain prices on the pre-results day (fa build: in_fo = bool(opt_expiry)). qn 0 is '
   'incomplete: in_fo True for ' + str(int(fa[fa.qn == 0].in_fo.sum())) + ' of ' + str(int((fa.qn == 0).sum())) +
   ' qn-0 results; long-standing F&O names flagged False at qn 0 and True from qn 1: ' +
   ' '.join(sorted(fa.sort_values('qn').groupby('symbol').filter(lambda g: (len(g) > 2) and (not g.in_fo.iloc[0]) and g.in_fo.iloc[1] and g.in_fo.iloc[2]).symbol.unique())))
sand = fa.sort_values(['symbol', 'qn']).copy()
sand['prev'] = sand.groupby('symbol').in_fo.shift()
sand['nxt'] = sand.groupby('symbol').in_fo.shift(-1)
sand = sand[(sand.in_fo == False) & (sand.prev == True) & (sand.nxt == True)]
P_(f'  isolated one-quarter in_fo gaps (True before and after): {len(sand)}: ' +
   ' '.join(f'{a}:{b}' for a, b in zip(sand.symbol, sand.qn)))
SV = []
for g, m in list(GROUPS.items()):
    for c in ['in F&O by qn 1 (2021)', 'joined F&O later']:
        x = d[m & (d.fo_cohort == c)]
        SV.append({'group': g, 'cohort': c, 'n': len(x), 'E0_net': (x.E0_gross - .19).mean(),
                   'E1a_net': (x.E1a_gross - .19).mean(), 'first14_E0': (x[x.FIRST].E0_gross - .19).mean(),
                   'last8_E0': (x[~x.FIRST].E0_gross - .19).mean()})
SVD = pd.DataFrame(SV)
SVD.to_csv(f'{HERE}/survivorship_cohorts.csv', index=False, float_format='%.3f')
P_('  by F&O cohort (vsN net 0.19):\n' + SVD.to_string(index=False, float_format=lambda x: f'{x:+.2f}'))
P_(f'  survivor drift of the universe itself: all in_fo results E0 vsN net {(d.E0_gross - .19).mean():+.2f} per 20 '
   f'sessions (first 14 {(d[d.FIRST].E0_gross - .19).mean():+.2f}, last 8 {(d[~d.FIRST].E0_gross - .19).mean():+.2f})')

# ===================================================================================================== 6. overlap
P_('\n' + '=' * 110 + '\n6. OVERLAP WITH THE PLAIN WINNER DRIFT')
OV = []
for e in ('E0', 'E1a', 'E1b'):
    for c in (0.19, 0.30, 0.50):
        r = {'entry': e, 'cost': c}
        for g, m in (('MAIN', d.MAIN), ('COMP', d.COMP), ('W', d.W)):
            x = d[m]
            v = x[f'{e}_gross'] - c
            r[f'{g}_n'] = len(v)
            r[f'{g}_mean'] = v.mean()
            r[f'{g}_first14'] = v[x.FIRST].mean()
            r[f'{g}_last8'] = v[~x.FIRST].mean()
            r[f'{g}_total'] = v.sum()
        OV.append(r)
OVD = pd.DataFrame(OV)
OVD.to_csv(f'{HERE}/overlap.csv', index=False, float_format='%.3f')
P_(OVD.to_string(index=False, float_format=lambda x: f'{x:+.2f}'))
# per-quarter: complement by quarter (E1a, 0.30)
cq = d[d.COMP].groupby('qn').apply(lambda x: pd.Series({'n': len(x), 'E1a_net030': (x.E1a_gross - .30).mean()}))
P_('  complement per quarter E1a net 0.30: ' + ' '.join(f'{QLAB.loc[q, "quarter"]}:{v.E1a_net030:+.1f}({int(v.n)})'
                                                         for q, v in cq.iterrows()))
P_(f'  complement quarters positive (E1a, 0.30): {int((cq.E1a_net030 > 0).sum())}/{len(cq)}')
for e, c in (('E0', 0.19), ('E1a', 0.30)):
    rm, rw = BOOK[(e, 'MAIN', 'res')], BOOK[(e, 'W', 'res')]
    P_(f'  {e} cost {c}: book MAIN total {rm["total_pct_units"]:+.0f} units-% with peak {rm["max_open"]} open, maxDD '
       f'{rm["maxDD_units_pct"]:+.1f}; all winners total {rw["total_pct_units"]:+.0f} with peak {rw["max_open"]} open, '
       f'maxDD {rw["maxDD_units_pct"]:+.1f}; return on peak capital per year MAIN {rm["annual_pct_on_peak_capital"]:.2f}% '
       f'vs all winners {rw["annual_pct_on_peak_capital"]:.2f}%')

# ===================================================================================================== 7. build checks
P_('\n' + '=' * 110 + '\n7. BUILD CHECKS (look-ahead, windows, data)')
# (a) independent RSI recomputation (own Wilder code) on adjusted closes, traded days only, up to the cutoff close
adj = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'close'])


def wilder_rsi(c, n=14):
    dlt = np.diff(c)
    out = np.full(len(c), np.nan)
    if len(dlt) < n:
        return out
    g = np.clip(dlt, 0, None)
    l_ = np.clip(-dlt, 0, None)
    ag, al = g[:n].mean(), l_[:n].mean()
    out[n] = 100 - 100 / (1 + ag / al) if al > 0 else (100.0 if ag > 0 else 50.0)
    for t in range(n, len(dlt)):
        ag = (ag * (n - 1) + g[t]) / n
        al = (al * (n - 1) + l_[t]) / n
        out[t + 1] = 100 - 100 / (1 + ag / al) if al > 0 else (100.0 if ag > 0 else 50.0)
    return out


W_ = d[d.W]
diffs, flips, upto = [], 0, {}
for s, g in W_.groupby('symbol'):
    a = adj[adj.symbol == s].sort_values('day')
    days_s = a.day.to_numpy()
    for r in g.itertuples():
        cutday = DAYS[r.i_cut]
        hist = a[a.day <= cutday].close.to_numpy(float)     # data strictly up to the cutoff close
        rs = wilder_rsi(hist)[-1] if len(hist) else np.nan
        diffs.append(rs - r.cut_rsi14)
        flips += int((rs > 50) != (r.cut_rsi14 > 50))
        upto[r.Index] = days_s[days_s <= cutday][-1] if (days_s <= cutday).any() else None
diffs = np.array(diffs)
P_(f'  (a) RSI(14) recomputed with my own Wilder code from adjusted closes up to the cutoff close for the 392 winners: '
   f'max abs diff {np.nanmax(np.abs(diffs)):.2e}; RSI>50 flag flips {flips}')
lastc = pd.Series(upto).reindex(W_.index)
P_(f'      last close used is on/before the cutoff day for all: {bool((lastc <= DAYS[W_.i_cut.to_numpy(int)]).all())}; '
   f'cutoff is 2 sessions before the result session and {sorted((W_.i_react - W_.i_cut).unique())} sessions before k')
# RSI sensitivity: RSI one session later (k-1 / closer to results) for info
# (b) scale invariance: adjustment anchored on the LAST close (2026-09-30) uses future split factors; RSI is a ratio
#     so a constant factor cancels. Check by recomputing RSI from RAW closes for winners with no split/bonus in the
#     RSI history window (raw = what a trader saw)
cab = ca  # split, bonus and demerger all change the adjustment factor
rawc = rawpx.set_index(['symbol', 'day']).close
nraw, mx = 0, 0.0
for r in W_.itertuples():
    cutday = DAYS[r.i_cut]
    a = rawpx[(rawpx.symbol == r.symbol) & (rawpx.day <= cutday) & rawpx.day.isin(DIX)].sort_values('day')
    a = a.tail(250)
    c_ = cab[(cab.symbol == r.symbol) & (cab.ex_date > a.day.min()) & (cab.ex_date <= cutday)] if len(a) else cab.iloc[:0]
    if len(a) < 100 or len(c_):
        continue
    # compare the last 250 closes: adjusted / raw ratio must be constant
    aa = adj[(adj.symbol == r.symbol) & adj.day.isin(set(a.day))].sort_values('day')
    ratio = aa.close.to_numpy() / a.close.to_numpy()
    mx = max(mx, ratio.max() / ratio.min() - 1)
    nraw += 1
n_ca_win = 0
for r in W_.itertuples():
    lo = DAYS[max(r.i_cut - 250, 0)]
    n_ca_win += int(((ca.symbol == r.symbol) & (ca.ex_date > lo) & (ca.ex_date <= DAYS[r.i_cut])).any())
P_(f'  (b) for {nraw} winners with no split/bonus/demerger in the 250 sessions before the cutoff, adjusted/raw close ratio is '
   f'constant (max relative spread {mx:.1e}) -> RSI on adjusted closes = RSI a trader saw on raw closes (no look-ahead '
   f'from the backward adjustment); {n_ca_win} winners have a split/bonus/demerger in the 250 sessions before the '
   f'cutoff, where the adjusted RSI is the correct (continuous) one')
# (c) corporate actions inside MAIN windows
win = []
for r in d[d.MAIN].itertuples():
    lo, hi = DAYS[max(r.i_cut - 30, 0)], DAYS[r.i_react + 21]
    c_ = ca[(ca.symbol == r.symbol) & (ca.ex_date >= lo) & (ca.ex_date <= hi)]
    for cr in c_.itertuples():
        i_ex = int(np.searchsorted(DAYS, cr.ex_date))
        win.append({'symbol': r.symbol, 'quarter': r.quarter, 'kind': cr.kind, 'ex_date': cr.ex_date,
                    'ex_vs_k': i_ex - r.i_react, 'adj_ret_ex_pct': R[i_ex, SYM[r.symbol]] * 100,
                    'E0_net': r.E0_gross - .19})
P_(f'  (c) corporate actions from cutoff-30 to k+21 for MAIN trades: {len(win)}')
if win:
    P_(pd.DataFrame(win).to_string(index=False, float_format=lambda x: f'{x:+.2f}'))
# (d) extreme daily returns in MAIN holding windows
ext = []
for r in d[d.MAIN].itertuples():
    j = SYM[r.symbol]
    seg = R[r.i_react + 1:r.i_react + 22, j]
    if np.nanmax(np.abs(seg)) > 0.12:
        t = int(np.nanargmax(np.abs(seg)))
        ext.append((r.symbol, r.quarter, DAYS[r.i_react + 1 + t], round(seg[t] * 100, 2)))
P_(f'  (d) MAIN trades with a daily move > 12% inside k+1..k+21: {len(ext)}: {ext}')
for s, q, day, v in ext:
    try:
        x = rp.loc[(s, day)]
        P_(f'      raw {s} {day}: close/prevclose {100 * (x.close / x.prevclose - 1):+.2f}% (adjusted {v:+.2f}%)')
    except KeyError:
        pass
# (e) same-stock overlap and duplicates
dup = d.duplicated(['symbol', 'qn']).sum()
ov = 0
for s, g in d[d.MAIN].groupby('symbol'):
    kk = np.sort(g.i_react.to_numpy())
    ov += int((np.diff(kk) <= 20).sum())
P_(f'  (e) duplicate (symbol, qn): {dup}; MAIN trades of the same stock overlapping in time: {ov}')
# results of the same stock inside an open MAIN window (a second result announced during the hold)
nxt = 0
for r in d[d.MAIN].itertuples():
    e2 = ev[(ev.symbol == r.symbol) & (ev.i_react > r.i_react) & (ev.i_react <= r.i_react + 20)]
    nxt += len(e2)
P_(f'      another result of the same stock within k+1..k+20 of a MAIN trade: {nxt}')
# (f) XN near the threshold vs raw prices (signal precision) and stale returns
near = d[d.W & (d.XN < 5)]
P_(f'  (f) winners with 4 < XN <= 5 (most exposed to a pre-close signal estimate): {len(near)} of 392; '
   f'MAIN {int((near.MAIN).sum())} of 232; their E0 net {(near[near.MAIN].E0_gross - .19).mean():+.2f}, '
   f'MAIN with XN > 5 {(d[d.MAIN & (d.XN > 5)].E0_gross - .19).mean():+.2f}')
# (g) raw check of XN for all MAIN trades
bad = 0
nchk = 0
for r in d[d.MAIN].itertuples():
    try:
        x = rp.loc[(r.symbol, r.reaction_day)]
    except KeyError:
        continue
    nchk += 1
    rr = (x.close / x.prevclose - 1 - NRET[r.i_react]) * 100
    if abs(rr - r.XN) > 0.05:
        bad += 1
        P_(f'      XN raw mismatch {r.symbol} {r.quarter} {r.reaction_day}: raw {rr:+.2f} vs XN {r.XN:+.2f}')
P_(f'  (g) XN of the {nchk} MAIN trades vs raw DB close/prevclose: {bad} differ by > 0.05 pts')
# (h) timing classes of late-session results in MAIN
P_(f'  (h) MAIN trades from results filed 15:00-15:29 ("During market"; the NSE close is the 15:00-15:30 VWAP, so '
   f'the close only partly reflects them): {int((d.MAIN & (d.tclass == "3 During market 15:00-15:29")).sum())}')

# ===================================================================================================== 8. extras
P_('\n' + '=' * 110 + '\n8. EXTRAS: underwater time, liquidity, realistic number')
for (e, g) in (('E0', 'MAIN'), ('E1a', 'MAIN'), ('E1a', 'W')):
    df = BOOK[(e, g)][0]
    x = BOOK[(e, g)][1]
    span = df[(df.day >= DAYS[x.i_react.min()]) & (df.day <= DAYS[min(NS - 1, x.i_react.max() + 21)])].reset_index(drop=True)
    eq = span.pnl_units_pct.cumsum()
    under = eq < eq.cummax() - 1e-9
    runs, cur, start = [], 0, None
    for i, u in enumerate(under):
        if u:
            cur += 1
            start = i if cur == 1 else start
        else:
            if cur:
                runs.append((cur, span.day[start], span.day[i]))
            cur = 0
    if cur:
        runs.append((cur, span.day[start], 'not recovered'))
    lr = max(runs)
    P_(f'  {e} {g}: longest time below a previous equity peak {lr[0]} sessions ({lr[1]} -> {lr[2]}); '
       f'equity at end {eq.iloc[-1]:+.0f} units-%')
# liquidity: traded value on k+1 (raw close x volume, Rs crore)
con = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
vol = pd.read_sql('SELECT day, symbol, close, volume FROM px', con).set_index(['symbol', 'day'])
con.close()
tv = []
for r in d[d.MAIN].itertuples():
    try:
        x = vol.loc[(r.symbol, DAYS[r.i_react + 1])]
        tv.append(x.close * x.volume / 1e7)
    except KeyError:
        pass
tv = np.array(tv)
P_(f'  MAIN: traded value on k+1 (Rs crore): median {np.median(tv):.0f}, 10th pct {np.quantile(tv, .1):.0f}, '
   f'min {tv.min():.1f} -> a Rs 10 lakh position is {0.1 / np.quantile(tv, .1) * 100:.2f}% of a 10th-percentile day')
REAL = []
for lab, m in (('full sample', d.MAIN), ('ex calendar 2023', d.MAIN & (d.reaction_day.str[:4] != '2023')),
               ('in F&O by qn 1 (less survivor-selected)', d.MAIN & (d.fo_cohort == 'in F&O by qn 1 (2021)')),
               ('in F&O by qn 1, ex 2023', d.MAIN & (d.fo_cohort == 'in F&O by qn 1 (2021)') & (d.reaction_day.str[:4] != '2023'))):
    for e in ('E0', 'E1a', 'E1b'):
        x = d[m]
        mw = d.W & (m | ~d.MAIN)  # comparable winners in the same slice
        REAL.append({'slice': lab, 'entry': e, 'n': len(x), 'gross': x[f'{e}_gross'].mean(),
                     'net_0.19': x[f'{e}_gross'].mean() - .19, 'net_0.40': x[f'{e}_gross'].mean() - .40,
                     'net_0.50': x[f'{e}_gross'].mean() - .50})
RL = pd.DataFrame(REAL)
# matching all-winner slices
for lab, m in (('full sample', d.W), ('ex calendar 2023', d.W & (d.reaction_day.str[:4] != '2023')),
               ('in F&O by qn 1 (less survivor-selected)', d.W & (d.fo_cohort == 'in F&O by qn 1 (2021)')),
               ('in F&O by qn 1, ex 2023', d.W & (d.fo_cohort == 'in F&O by qn 1 (2021)') & (d.reaction_day.str[:4] != '2023'))):
    x = d[m]
    RL.loc[(RL.slice == lab) & (RL.entry == 'E1a'), 'all_winners_E1a_net_0.40'] = x.E1a_gross.mean() - .40
    RL.loc[(RL.slice == lab) & (RL.entry == 'E1a'), 'all_winners_n'] = len(x)
RL.to_csv(f'{HERE}/realistic.csv', index=False, float_format='%.3f')
P_(RL.to_string(index=False, float_format=lambda v: f'{v:+.2f}'))

d.to_csv(f'{HERE}/trades_all_entries.csv', index=False, float_format='%.5f',
         columns=['symbol', 'qn', 'quarter', 'period', 'results_date', 'results_time', 'timing', 'tclass', 'reaction_day',
                  'i_cut', 'i_react', 'XN', 'cut_rsi14', 'W', 'MAIN', 'COMP', 'fo_cohort', 'traded_k1', 'gap_vsN',
                  'd1_vsN'] + [f'{e}_{s}' for e in ENTRIES for s in ('gross', 'raw')] + ['E0_fut'])
P_('\nwrote: tradability.log, entries_costs.csv, luck_by_entry.csv, per_quarter_entries.csv, timing.csv, '
   'book_summary.csv, book_monthly_*.csv, book_daily_*.csv, survivorship_cohorts.csv, overlap.csv, trades_all_entries.csv')
