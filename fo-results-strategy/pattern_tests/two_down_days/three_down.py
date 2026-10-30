#!/usr/bin/env python3
"""PLAN_THREE_DOWN.txt: after three down days on ordinary days, is the fourth day down?

Builds the four-day windows from the same inputs as build_days.py (LAB_ROOT, TA_BUILD, CA_DIR, REPO_ROOT) and writes
OUT/table_three_down.md, three_down_*.csv and three_down.log (OUT default REPO_ROOT/results/two_down_days).
"""
import glob
import hashlib
import json
import os
import numpy as np
import pandas as pd
from scipy import stats

LAB = os.environ.get('LAB_ROOT', 'lab')
TA = os.environ.get('TA_BUILD', os.path.join(LAB, 'ta', 'build'))
CA_DIR = os.environ.get('CA_DIR', os.path.join(LAB, 'dl_ca_history'))
REPO = os.environ.get('REPO_ROOT', '.')
OUT = os.environ.get('OUT', os.path.join(REPO, 'results', 'two_down_days'))
PACK = os.path.join(LAB, 'sector_lab', 'data')
HERE = os.path.dirname(os.path.abspath(__file__))
WIN, B, SEED, COST = 5, 5000, 20261101, 0.17
log = []
def P(*a):
    log.append(' '.join(str(x) for x in a))
    print(*a)
h = hashlib.sha256(open(os.path.join(HERE, 'PLAN_THREE_DOWN.txt'), 'rb').read()).hexdigest()
P(f'PLAN_THREE_DOWN.txt sha256 {h} ({"MATCH" if h == open(os.path.join(HERE, "PLAN_THREE_DOWN.sha256")).read().strip() else "MISMATCH"})')

# ---------------------------------------------------------------- inputs (as build_days.py)
ses = pd.read_csv(f'{PACK}/sessions.csv')
days = ses.day.to_numpy()
dts = pd.to_datetime(days)
T = len(days)
pos = {d: i for i, d in zip(ses.i, ses.day)}
a = pd.read_csv(f'{TA}/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'open', 'close', 'price_factor'])
syms = sorted(a.symbol.unique())
S = len(syms)
col = {s: j for j, s in enumerate(syms)}
a['i'] = a.day.map(pos)
grid = lambda c: a.pivot(index='i', columns='symbol', values=c).reindex(index=range(T), columns=syms).to_numpy(float)
C, O, F = grid('close'), grid('open'), grid('price_factor')
R = np.full((T, S), np.nan)
R[1:] = (C[1:] / C[:-1] - 1) * 100
R[[k for k, d in enumerate(days) if d in ('2015-12-02', '2016-06-21')]] = np.nan   # a trading day is missing before these
GAP = np.full((T, S), np.nan)
GAP[1:] = (O[1:] / C[:-1] - 1) * 100
INTRA = (C / O - 1) * 100
PF = np.zeros((T, S), bool)
PF[1:] = np.abs(F[1:] / F[:-1] - 1) > 1e-9
ix = pd.read_csv(f'{PACK}/index_close.csv', index_col=0)
def iret(name):
    c = ix[name].to_numpy(float)
    r = np.full(T, np.nan)
    r[1:] = (c[1:] / c[:-1] - 1) * 100
    r[[k for k, d in enumerate(days) if d in ('2015-12-02', '2016-06-21')]] = np.nan
    return r
NIF = iret('Nifty 50')
ev = pd.read_csv(f'{PACK}/events.csv')
RES = np.zeros((T, S), bool)
FO = np.full((T, S), np.nan)
for s, g in ev.sort_values('i_rd').groupby('symbol'):
    if s not in col:
        continue
    for c_ in ('i_rd', 'i_react'):
        v = g[c_].dropna().astype(int).to_numpy()
        RES[v[v < T], col[s]] = True
    rd, fo = g.i_rd.to_numpy(int), g.in_fo.to_numpy(bool)          # a missing in_fo counts as in F&O
    t = np.arange(T)
    nxt = np.searchsorted(rd, t, side='right')
    prv = nxt - 1
    v = np.where(prv >= 0, fo[np.clip(prv, 0, None)] & np.where(nxt < len(rd), fo[np.minimum(nxt, len(rd) - 1)], True), np.nan)
    FO[:, col[s]] = np.where(prv >= 0, v, np.nan)
cres = np.vstack([np.zeros((1, S), int), np.cumsum(RES, axis=0)])
rows = []
for f in sorted(glob.glob(os.path.join(CA_DIR, 'ca_*.json'))):
    d = json.load(open(f))
    rows += d if isinstance(d, list) else []
ca = pd.DataFrame(rows)
ca = ca[ca.symbol.isin(col)].copy()
ca['ex'] = pd.to_datetime(ca.exDate, format='%d-%b-%Y', errors='coerce')
ca = ca.dropna(subset=['ex'])
k = np.searchsorted(dts.to_numpy(), ca.ex.to_numpy())
ok = k < T
CA = np.zeros((T, S), bool)
CA[k[ok], ca.symbol[ok].map(col).to_numpy()] = True
DS = np.zeros((T, S), int)
for t in range(1, T):
    DS[t] = np.where(R[t] < 0, DS[t - 1] + 1, 0)

# calendar flags per day-4 session t (the same for every stock)
weekend_sessions = set(dts[dts.weekday >= 5])
holidays = set(pd.bdate_range(dts.min(), dts.max() + pd.Timedelta(days=7)).difference(dts))
NOBREAK, HOLFREE = np.zeros(T, bool), np.zeros(T, bool)
for t in range(4, T):
    d0, d4 = dts[t - 4], dts[t]
    span = pd.date_range(d0, d4)
    NOBREAK[t] = (d4 - d0).days == 4 and (span.weekday < 5).all()
    nxt_wd = d4 + pd.offsets.BDay(1)
    span2 = pd.date_range(d0, nxt_wd)
    HOLFREE[t] = not any(x in holidays for x in span2[span2.weekday < 5]) and not any(x in weekend_sessions for x in span2)

# ---------------------------------------------------------------- four-day windows
ok = ~np.isnan(R)
t4, j = np.nonzero(ok & np.roll(ok, 1, 0) & np.roll(ok, 2, 0) & np.roll(ok, 3, 0))
keep = t4 >= 4
t4, j = t4[keep], j[keep]
lo, hi = np.clip(t4 - 3 - WIN, 0, None), np.minimum(t4 + WIN + 1, T)
W = pd.DataFrame({
    'symbol': np.array(syms)[j], 'i4': t4, 'day4': days[t4],
    'r1': R[t4 - 3, j], 'r2': R[t4 - 2, j], 'r3': R[t4 - 1, j], 'r4': R[t4, j], 'gap4': GAP[t4, j], 'intra4': INTRA[t4, j],
    'n4': NIF[t4], 'ds0': DS[t4 - 4, j],
    'near': (cres[hi, j] - cres[lo, j]) > 0,
    'corp': PF[t4 - 3, j] | PF[t4 - 2, j] | PF[t4 - 1, j] | PF[t4, j] | CA[t4 - 3, j] | CA[t4 - 2, j] | CA[t4 - 1, j] | CA[t4, j],
    'fo3': FO[t4 - 1, j], 'nobreak': NOBREAK[t4], 'holfree': HOLFREE[t4], 'weekday4': dts[t4].day_name().str[:3],
})
M = W[(W.fo3 == 1) & ~W.near & ~W.corp].copy()
P(f'four-day windows (day0..day4 traded): {len(W):,}; with a known result before day3: {int((~W.fo3.isna()).sum()):,}; '
  f'MAIN (in F&O, ordinary): {len(M):,} windows, {M.symbol.nunique()} stocks, day4 {M.day4.min()} .. {M.day4.max()}')
P(f'  NO-BREAK (Mon..Fri, no holiday): {int(M.nobreak.sum()):,}; HOLIDAY-FREE: {int(M.holfree.sum()):,}')
assert set(M[M.nobreak].weekday4) == {'Fri'}
M['down4'] = (M.r4 < 0).astype(float)
M['up4'] = (M.r4 > 0).astype(float)
M['x4'] = M.r4 - M.n4
M['three_down'] = (M.r1 < 0) & (M.r2 < 0) & (M.r3 < 0)
M['exact3'] = M.three_down & (M.ds0 == 0)
M['three_up'] = (M.r1 > 0) & (M.r2 > 0) & (M.r3 > 0)
M['two_down'] = (M.r2 < 0) & (M.r3 < 0)
M['big3'] = (M.r1 < -1) & (M.r2 < -1) & (M.r3 < -1)
M['quarter'] = M.day4.str[:4] + ' Q' + ((M.day4.str[5:7].astype(int) - 1) // 3 + 1).astype(str)
M.to_csv(f'{OUT}/windows4.csv.gz', index=False, float_format='%.8g', compression='gzip')   # for sector.py; not committed

# ---------------------------------------------------------------- helpers
rng = np.random.default_rng(SEED)
pct = lambda v: '-' if pd.isna(v) else f'{v:.1f}%'
sgn = lambda v: '-' if pd.isna(v) else f'{v:+.2f}'
fpv = lambda p: '-' if pd.isna(p) else ('<0.001' if p < 0.001 else f'{p:.3f}')
def md(rows, cols):
    out = ['| ' + ' | '.join(cols) + ' |', '|' + '|'.join('---' if i == 0 else '---:' for i in range(len(cols))) + '|']
    return '\n'.join(out + ['| ' + ' | '.join(str(x) for x in r) + ' |' for r in rows])
def clustered_se(y, dates):
    y = np.asarray(y, float)
    g = pd.Series(y - y.mean()).groupby(np.asarray(dates)).sum()
    return np.sqrt((g ** 2).sum()) / len(y)
def peers(X, sig, ycol):
    g = X.assign(s=np.asarray(sig)).dropna(subset=[ycol]).groupby(['day4', 's'])[ycol].agg(['mean', 'size']).unstack('s').dropna()
    if len(g) < 3:
        return dict(diff=np.nan, wdiff=np.nan, dates=len(g), p_t=np.nan, p_boot=np.nan, n_sig=0)
    d = g[('mean', True)] - g[('mean', False)]
    w = g[('size', True)]
    ms = d.groupby(d.index.str[:7]).agg(['sum', 'size'])
    idx = rng.integers(0, len(ms), size=(B, len(ms)))
    bs = ms['sum'].to_numpy()[idx].sum(1) / ms['size'].to_numpy()[idx].sum(1)
    return dict(diff=d.mean(), wdiff=(d * w).sum() / w.sum(), dates=len(d), p_t=stats.ttest_1samp(d, 0).pvalue,
                p_boot=min(1.0, 2 * min((bs <= 0).mean(), (bs >= 0).mean())), n_sig=int(w.sum()))

# ---------------------------------------------------------------- per calendar version
VERS = {'All ordinary days': M, 'No weekend or holiday inside (Monday to Friday, day 4 a Friday)': M[M.nobreak],
        'No holiday nearby (weekends allowed)': M[M.holfree]}
sections, csv, headline = [], [], {}
for name, X in VERS.items():
    rows = []
    for lab, m in (('All windows', np.ones(len(X), bool)), ('After three up days', X.three_up.to_numpy()),
                   ('After two down days', X.two_down.to_numpy()), ('After three down days', X.three_down.to_numpy())):
        x = X[m]
        rows.append([lab, f'{len(x):,}', pct(x.down4.mean() * 100), f'±{clustered_se(x.down4, x.day4) * 100:.1f}',
                     pct(x.up4.mean() * 100), sgn(x.r4.mean()) + '%', sgn(x.x4.mean())])
    t1 = md(rows, ['Group', 'Windows', 'Day 4 down', '± (date-clustered SE)', 'Day 4 up', 'Mean day 4', 'Day 4 vs Nifty (pts)'])
    rows = []
    for ycol, lab in (('down4', 'Share down'), ('r4', 'Mean day 4')):
        r = peers(X, X.three_down, ycol)
        kk = 100 if ycol == 'down4' else 1
        rows.append([lab, f'{r["n_sig"]:,}', f'{r["dates"]:,}', sgn(r['diff'] * kk), sgn(r['wdiff'] * kk), fpv(r['p_t']), fpv(r['p_boot'])])
        csv.append(dict(version=name, outcome=ycol, **r))
        if ycol == 'down4':
            headline[name] = (X[X.three_down].down4.mean(), X.down4.mean(), r)
    t2 = md(rows, ['Three-down minus same-day peers', 'Three-down windows', 'Dates', 'Each date equal (pts)', 'Weighted by count (pts)', 'p (t)', 'p (month bootstrap)'])
    cut = X.day4.sort_values().iloc[len(X) // 2]
    H, rows = {}, []
    for lab, Y in (('First half', X[X.day4 < cut]), ('Second half', X[X.day4 >= cut])):
        r = peers(Y, Y.three_down, 'down4'); H[lab] = r
        y = Y[Y.three_down]
        rows.append([lab, f'{Y.day4.min()} .. {Y.day4.max()}', f'{len(y):,}', pct(y.down4.mean() * 100), sgn(r['diff'] * 100), fpv(r['p_t']), fpv(r['p_boot'])])
    f1, f2 = H['First half'], H['Second half']
    conf = bool(f1['p_t'] < 0.05 and f1['p_boot'] < 0.05 and np.sign(f2['diff']) == np.sign(f1['diff']) and f2['p_t'] < 0.05 and f2['p_boot'] < 0.05)
    t3 = md(rows, ['Half', 'Day 4 dates', 'Three-down windows', 'Day 4 down', 'vs same-day peers (pts)', 'p (t)', 'p (bootstrap)'])
    TD = X[X.three_down]
    rows = []
    for lab, v in (('Buy at the day-3 close, sell at the day-4 close', TD.r4 - COST), ('Short at the day-3 close, cover at the day-4 close', -TD.r4 - COST)):
        rows.append([lab, f'{len(v):,}', sgn(v.mean()) + '%', pct((v > 0).mean() * 100), sgn(v.sort_values().iloc[:-5].mean()) + '%',
                     sgn(v[TD.day4 < cut].mean()) + '%', sgn(v[TD.day4 >= cut].mean()) + '%'])
    t4_ = md(rows, ['Trade, after 0.17% costs', 'Trades', 'Avg net', 'Winning', 'Without the 5 best', 'First half', 'Second half'])
    sections.append(f'## {name}\n\n{t1}\n\n{t2}\n\n{t3}\n\nCONFIRMED by the plan\'s rule: **{"yes" if conf else "no"}**.\n\n{t4_}\n')
    P(f'== {name}'); P(t1); P(t2); P(t3); P(f'CONFIRMED: {conf}'); P(t4_)

# ---------------------------------------------------------------- extras on all ordinary days
X = M
rows = []
for lab, sig in (('Three down days (any)', X.three_down), ('Exactly three (the day before was not down)', X.exact3),
                 ('All three days below -1%', X.big3)):
    x = X[sig]; r = peers(X, sig, 'down4')
    rows.append([lab, f'{len(x):,}', pct(x.down4.mean() * 100), sgn(x.r4.mean()) + '%', sgn(r['diff'] * 100), fpv(r['p_boot']), sgn(r['wdiff'] * 100)])
tv = md(rows, ['Signal', 'Windows', 'Day 4 down', 'Mean day 4', 'vs peers, dates equal (pts)', 'p', 'vs peers, weighted (pts)'])
rows = []
for c_, lab in (('gap4', 'Opening gap'), ('intra4', 'Open to close'), ('r4', 'Whole day 4')):
    r = peers(X, X.three_down, c_)
    rows.append([lab, sgn(X[X.three_down][c_].mean()) + '%', sgn(X[~X.three_down][c_].mean()) + '%', sgn(r['diff']), fpv(r['p_boot'])])
ts = md(rows, ['Part of day 4', 'After three down days', 'Other stocks', 'Difference, same day (pts)', 'p'])
rows = []
for v in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']:
    Y = X[X.weekday4 == v]; y = Y[Y.three_down]; r = peers(Y, Y.three_down, 'down4')
    rows.append([v, f'{len(y):,}', pct(y.down4.mean() * 100), pct(Y[~Y.three_down].down4.mean() * 100), sgn(r['diff'] * 100), fpv(r['p_boot'])])
tw = md(rows, ['Day 4 weekday', 'Three-down windows', 'Day 4 down', 'Other stocks down', 'vs same-day peers (pts)', 'p'])
rows, qc = [], []
for q, Y in X.groupby('quarter'):
    y = Y[Y.three_down]
    if len(y) < 20:
        continue
    r = peers(Y, Y.three_down, 'down4')
    rows.append([q, f'{len(y):,}', pct(y.down4.mean() * 100), pct(Y[~Y.three_down].down4.mean() * 100), sgn(r['diff'] * 100), sgn(y.r4.mean()) + '%'])
    qc.append(dict(quarter=q, n=len(y), share_down=y.down4.mean(), others_down=Y[~Y.three_down].down4.mean(), peer_diff=r['diff'], mean_r4=y.r4.mean()))
qc = pd.DataFrame(qc); qc.to_csv(f'{OUT}/three_down_by_quarter.csv', index=False)
tq = md(rows, ['Quarter', 'Three-down windows', 'Day 4 down', 'Other stocks down', 'vs same-day peers (pts)', 'Mean day 4'])
tq += f'\n\nBelow its same-day peers (a bounce) in {int((qc.peer_diff < 0).sum())} of {len(qc)} quarters.'
rows = []
for name in ('Nifty 50', 'Nifty Bank'):
    r = pd.Series(iret(name), index=days)
    df = pd.DataFrame({'r1': r.shift(3), 'r2': r.shift(2), 'r3': r.shift(1), 'r4': r}).dropna()
    df = df[df.index >= '2016-01-01']
    dd = (df.r1 < 0) & (df.r2 < 0) & (df.r3 < 0)
    a_, b_ = (df[dd].r4 < 0), (df[~dd].r4 < 0)
    p = stats.fisher_exact([[a_.sum(), (~a_).sum()], [b_.sum(), (~b_).sum()]])[1]
    rows.append([name, f'{int(dd.sum()):,}', pct(a_.mean() * 100), pct(b_.mean() * 100), sgn(df[dd].r4.mean()) + '%', fpv(p)])
ti = md(rows, ['Index (2016 .. Sep 2026)', 'Three-down runs', 'Next day down', 'Other days down', 'Mean next day', 'p (Fisher)'])
P(tv); P(ts); P(tw); P(tq); P(ti)
pd.DataFrame(csv).to_csv(f'{OUT}/three_down_peers.csv', index=False)
open(f'{OUT}/table_three_down.md', 'w').write(
    '# Three down days, then the fourth day\n\nPLAN_THREE_DOWN.txt: F&O stocks while in F&O, May 2021 .. Sep 2026, ordinary '
    'days only (no result or reaction session within 5 sessions of the four days, no split/bonus/demerger or NSE ex-date on '
    'them). "No weekend or holiday inside": the session before day 1 to day 4 on five calendar weekdays in a row, which can '
    'only be Monday to Friday, so day 4 is always a Friday. "No holiday nearby": no weekday holiday and no special weekend '
    'session from the session before day 1 to the weekday after day 4.\n\n' + '\n'.join(sections) +
    '\n## More on all ordinary days\n\n' + tv + '\n\n' + ts + '\n\n### By weekday of day 4\n\n' + tw +
    '\n\n### Every quarter\n\n' + tq + '\n\n### The index itself\n\n' + ti + '\n')
open(f'{OUT}/three_down.log', 'w').write('\n'.join(log) + '\n')
