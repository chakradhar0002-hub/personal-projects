#!/usr/bin/env python3
"""One row per stock and day-3 session: the two earlier daily returns, day 3 and what follows, and the exclusion flags
of PLAN.txt (results within 5 sessions, split/bonus/demerger, NSE corporate-action ex-dates, F&O status).

Reads LAB_ROOT (sector_lab data pack), TA_BUILD (adjusted_ohlcv.csv.gz), CA_DIR (NSE corporate-action JSON files,
untrusted downloads parsed with json only) and REPO_ROOT; writes OUT/days.csv.gz.
"""
import glob
import json
import os
import numpy as np
import pandas as pd

LAB = os.environ.get('LAB_ROOT', 'lab')
TA = os.environ.get('TA_BUILD', os.path.join(LAB, 'ta', 'build'))
CA_DIR = os.environ.get('CA_DIR', os.path.join(LAB, 'dl_ca_history'))
REPO = os.environ.get('REPO_ROOT', '.')
OUT = os.environ.get('OUT', os.path.join(REPO, 'results', 'two_down_days'))
PACK = os.path.join(LAB, 'sector_lab', 'data')
WIN = 5                                   # result sessions within 5 sessions of day1..day3 exclude the triple
os.makedirs(OUT, exist_ok=True)
log = []
P = lambda *a: (log.append(' '.join(str(x) for x in a)), print(*a))

ses = pd.read_csv(f'{PACK}/sessions.csv')
days = ses.day.to_numpy()
T = len(days)
pos = {d: i for i, d in zip(ses.i, ses.day)}

a = pd.read_csv(f'{TA}/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'open', 'close', 'price_factor'])
assert a.day.isin(pos).all()
syms = sorted(a.symbol.unique())
S = len(syms)
a['i'] = a.day.map(pos)
grid = lambda c: a.pivot(index='i', columns='symbol', values=c).reindex(index=range(T), columns=syms).to_numpy(float)
C, O, F = grid('close'), grid('open'), grid('price_factor')
P(f'adjusted OHLCV: {S} stocks, {T} sessions {days[0]} .. {days[-1]}')

# daily return in %, only between two traded sessions (so the first traded day of a stock never gets a return)
R = np.full((T, S), np.nan)
R[1:] = (C[1:] / C[:-1] - 1) * 100
# the session list misses a trading day before these two sessions, so their 'daily' return spans two sessions
GAPDAYS = [k for k, d in enumerate(days) if d in ('2015-12-02', '2016-06-21')]
R[GAPDAYS] = np.nan
GAP = np.full((T, S), np.nan)
GAP[1:] = (O[1:] / C[:-1] - 1) * 100
INTRA = (C / O - 1) * 100
PF = np.zeros((T, S), bool)                # price_factor stepped on session t (split / bonus / demerger)
PF[1:] = np.abs(F[1:] / F[:-1] - 1) > 1e-9
PF &= ~np.isnan(F)

ix = pd.read_csv(f'{PACK}/index_close.csv', index_col=0)
assert (ix.index == days).all()
def iret(name):
    c = ix[name].to_numpy(float)
    r = np.full(T, np.nan)
    r[1:] = (c[1:] / c[:-1] - 1) * 100
    return r
NIF, BNK = iret('Nifty 50'), iret('Nifty Bank')
VIX = ix['India VIX'].to_numpy(float)

# results: result session and reaction session of every result
ev = pd.read_csv(f'{PACK}/events.csv')
RES = np.zeros((T, S), bool)
col = {s: j for j, s in enumerate(syms)}
for s, g in ev.groupby('symbol'):
    if s not in col:
        continue
    for c_ in ('i_rd', 'i_react'):
        v = g[c_].dropna().astype(int).to_numpy()
        RES[v[v < T], col[s]] = True
cres = np.vstack([np.zeros((1, S), int), np.cumsum(RES, axis=0)])   # cres[b] - cres[a] = results in [a, b)
P(f'results: {len(ev)} events, {int(RES.sum())} result/reaction session marks, symbols with events {ev.symbol.isin(col).sum() and ev.symbol.nunique()}')

# NSE corporate actions (ex-dates), untrusted JSON parsed as data only
CA = np.zeros((T, S), bool)
rows, n_out = [], 0
for f in sorted(glob.glob(os.path.join(CA_DIR, 'ca_*.json'))):
    d = json.load(open(f))
    rows += d if isinstance(d, list) else []
ca = pd.DataFrame(rows)
ca = ca[ca.symbol.isin(col)].copy()
ca['ex'] = pd.to_datetime(ca.exDate, format='%d-%b-%Y', errors='coerce')
ca = ca.dropna(subset=['ex']).drop_duplicates(['symbol', 'ex', 'subject'])
k = np.searchsorted(pd.to_datetime(days).to_numpy(), ca.ex.to_numpy())   # ex-date on a holiday -> next session
ok = k < T
CA[k[ok], ca.symbol[ok].map(col).to_numpy()] = True
kind = np.where(ca.subject.str.contains('ividend', case=False), 'dividend', 'other')
P(f'corporate actions for the 213 stocks: {len(ca)} ex-dates ({(kind == "dividend").sum()} dividends) '
  f'{ca.ex.min().date()} .. {ca.ex.max().date()}')
CA_FROM = int(np.searchsorted(pd.to_datetime(days).to_numpy(), ca.ex.min().to_numpy()))

# F&O status on a session, from the previous and next result (as placebo_ta: previous AND next result in F&O)
FO = np.full((T, S), np.nan)
for s, g in ev.sort_values('i_rd').groupby('symbol'):
    if s not in col:
        continue
    rd, fo = g.i_rd.to_numpy(int), g.in_fo.to_numpy(bool)
    t = np.arange(T)
    nxt = np.searchsorted(rd, t, side='right')
    prv = nxt - 1
    has_prev, has_next = prv >= 0, nxt < len(rd)
    v = np.where(has_prev, fo[np.clip(prv, 0, None)] & np.where(has_next, fo[np.minimum(nxt, len(rd) - 1)], True), np.nan)
    v = np.where(has_prev, v, np.nan)
    FO[:, col[s]] = v

# streaks of consecutive down / up days ending at session t (on consecutive traded sessions)
DS, US = np.zeros((T, S), int), np.zeros((T, S), int)
for t in range(1, T):
    r = R[t]
    DS[t] = np.where(r < 0, DS[t - 1] + 1, 0)
    US[t] = np.where(r > 0, US[t - 1] + 1, 0)

# triples: day3 = t, day2 = t-1, day1 = t-2, day0 = t-3 all traded (R non-NaN on t-2, t-1, t)
t3, j = np.nonzero(~np.isnan(R) & ~np.isnan(np.roll(R, 1, 0)) & ~np.isnan(np.roll(R, 2, 0)))
keep = t3 >= 3
t3, j = t3[keep], j[keep]
fwd = lambda k: np.where(t3 + k < T, R[np.minimum(t3 + k, T - 1), j], np.nan)
r4 = fwd(1)
r5d = np.nansum(np.stack([fwd(k) for k in range(5)]), axis=0)
r5ok = np.all(~np.isnan(np.stack([fwd(k) for k in range(5)])), axis=0)
lo, hi = np.clip(t3 - 2 - WIN, 0, None), np.minimum(t3 + WIN + 1, T)
near = (cres[hi, j] - cres[lo, j]) > 0
pfx = PF[t3 - 2, j] | PF[t3 - 1, j] | PF[t3, j]
cax = CA[t3 - 2, j] | CA[t3 - 1, j] | CA[t3, j]
D = pd.DataFrame({
    'symbol': np.array(syms)[j], 'i3': t3, 'day3': days[t3],
    'r1': R[t3 - 2, j], 'r2': R[t3 - 1, j], 'r3': R[t3, j], 'r4': r4, 'r3to7': np.where(r5ok, r5d, np.nan),
    'gap3': GAP[t3, j], 'intra3': INTRA[t3, j],
    'n1': NIF[t3 - 2], 'n2': NIF[t3 - 1], 'n3': NIF[t3], 'vix2': VIX[t3 - 1],
    'dstreak2': DS[t3 - 1, j], 'ustreak2': US[t3 - 1, j],
    'near_result': near, 'split_bonus': pfx, 'corp_action': cax, 'ca_known': t3 - 2 >= CA_FROM,
    'in_fo2': FO[t3 - 1, j],
})
sec = pd.read_csv(os.path.join(REPO, 'results', 'nifty_sector_3day', 'results_3day.csv'), usecols=['symbol', 'nifty_sector'])
D = D.merge(sec.drop_duplicates('symbol'), on='symbol', how='left')
D['has_results'] = ~np.isnan(D.in_fo2)
D['main'] = (D.in_fo2 == 1) & ~D.near_result & ~D.split_bonus & ~D.corp_action
D['all21'] = D.has_results & ~D.near_result & ~D.split_bonus & ~D.corp_action
D['long'] = ~D.split_bonus
assert D.loc[D.has_results, 'ca_known'].all()
P(f'triples (day0..day3 traded): {len(D):,}; with a known result before day2: {int(D.has_results.sum()):,}')
h = D[D.has_results]
P(f'  of those near a result (+-{WIN} sessions): {int(h.near_result.sum()):,}; split/bonus/demerger: {int(h.split_bonus.sum()):,}; '
  f'NSE ex-date on day1..day3: {int(h.corp_action.sum()):,}; not in F&O on day2: {int((h.in_fo2 == 0).sum()):,}')
P(f'MAIN {int(D.main.sum()):,} triples, {D[D.main].symbol.nunique()} stocks, day3 {D[D.main].day3.min()} .. {D[D.main].day3.max()}; '
  f'ALL21 {int(D.all21.sum()):,}; LONG {int(D.long.sum()):,}')
# checks: returns equal the project's returns.csv on traded pairs; the first traded return of each stock is absent
ret = pd.read_csv(f'{PACK}/returns.csv', index_col=0)
assert (ret.index == days).all()
rr = ret.reindex(columns=syms).to_numpy(float) * 100
m = ~np.isnan(R) & ~np.isnan(rr)
P(f'check: |R - returns.csv| max {np.nanmax(np.abs(R[m] - rr[m])):.2e} pct over {int(m.sum()):,} stock-days '
  f'(2015-12-02 and 2016-06-21 dropped: they follow a trading day missing from the session list)')
assert np.nanmax(np.abs(R[m] - rr[m])) < 1e-3
first = np.argmax(~np.isnan(C), axis=0)
assert np.isnan(R[first, np.arange(S)]).all()
P('check: no stock has a return on its first traded session')
D.to_csv(f'{OUT}/days.csv.gz', index=False, float_format='%.8g', compression='gzip')
open(f'{OUT}/build.log', 'w').write('\n'.join(log) + '\n')
