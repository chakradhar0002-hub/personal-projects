#!/usr/bin/env python3
"""PLAN_NO_WEEKEND.txt: the two-down-days tests on stretches away from weekends and holidays.

Reads OUT/days.csv.gz (build_days.py) and LAB_ROOT/sector_lab/data/sessions.csv; writes OUT/table_no_weekend.md,
no_weekend_*.csv and no_weekend.log.
"""
import hashlib
import os
import numpy as np
import pandas as pd
from scipy import stats

REPO = os.environ.get('REPO_ROOT', '.')
LAB = os.environ.get('LAB_ROOT', 'lab')
OUT = os.environ.get('OUT', os.path.join(REPO, 'results', 'two_down_days'))
HERE = os.path.dirname(os.path.abspath(__file__))
B, SEED, COST = 5000, 20261031, 0.17
log = []
def P(*a):
    log.append(' '.join(str(x) for x in a))
    print(*a)
h = hashlib.sha256(open(os.path.join(HERE, 'PLAN_NO_WEEKEND.txt'), 'rb').read()).hexdigest()
P(f'PLAN_NO_WEEKEND.txt sha256 {h} ({"MATCH" if h == open(os.path.join(HERE, "PLAN_NO_WEEKEND.sha256")).read().strip() else "MISMATCH"})')

ses = pd.to_datetime(pd.read_csv(os.path.join(LAB, 'sector_lab', 'data', 'sessions.csv')).day).to_numpy()
T = len(ses)
D = pd.read_csv(f'{OUT}/days.csv.gz')
M = D[D.main].copy()
i3 = M.i3.to_numpy()
d0, d3 = pd.to_datetime(ses[i3 - 3]), pd.to_datetime(ses[i3])
nxt = pd.to_datetime(ses[np.minimum(i3 + 1, T - 1)])
has_next = i3 + 1 < T
wd = np.stack([pd.to_datetime(ses[i3 - k]).weekday for k in range(4)])
M['nobreak'] = ((d3 - d0).days == 3) & (wd < 5).all(axis=0)
M['notnear'] = M.nobreak & has_next & ((nxt - d3).days == 1) & (nxt.weekday < 5)
M['weekday3'] = d3.day_name().str[:3]
# what the window day0..day3 contains: a weekend (or weekend session), a weekday holiday, or nothing
def window_kind(a, b):
    r = pd.date_range(a, b)
    if (r.weekday >= 5).any():
        return 'weekend inside'
    return 'holiday inside' if len(r) > 4 else 'no break'
kinds = {}
for a, b in set(zip(d0, d3)):
    kinds[(a, b)] = window_kind(a, b)
M['window'] = [kinds[(a, b)] for a, b in zip(d0, d3)]
assert (M.nobreak == (M.window == 'no break')).all()
M['down3'] = (M.r3 < 0).astype(float)
M['up3'] = (M.r3 > 0).astype(float)
M['x3'] = M.r3 - M.n3
M['two_down'] = (M.r1 < 0) & (M.r2 < 0)
M['two_up'] = (M.r1 > 0) & (M.r2 > 0)
M['one_down'] = M.r2 < 0
M['quarter'] = M.day3.str[:4] + ' Q' + ((M.day3.str[5:7].astype(int) - 1) // 3 + 1).astype(str)
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
    g = X.assign(s=np.asarray(sig)).dropna(subset=[ycol]).groupby(['day3', 's'])[ycol].agg(['mean', 'size']).unstack('s').dropna()
    if len(g) < 3:
        return dict(diff=np.nan, wdiff=np.nan, dates=len(g), p_t=np.nan, p_boot=np.nan, n_sig=0)
    d = g[('mean', True)] - g[('mean', False)]
    w = g[('size', True)]
    ms = d.groupby(d.index.str[:7]).agg(['sum', 'size'])
    idx = rng.integers(0, len(ms), size=(B, len(ms)))
    bs = ms['sum'].to_numpy()[idx].sum(1) / ms['size'].to_numpy()[idx].sum(1)
    return dict(diff=d.mean(), wdiff=(d * w).sum() / w.sum(), dates=len(d), p_t=stats.ttest_1samp(d, 0).pvalue,
                p_boot=min(1.0, 2 * min((bs <= 0).mean(), (bs >= 0).mean())), n_sig=int(w.sum()))

SAMPLES = {'Not near a weekend or holiday (Mon..Thu, Friday open)': M[M.notnear],
           'No weekend or holiday inside (day 3 Thu or Fri)': M[M.nobreak],
           'All ordinary days (earlier result)': M}
P(f'MAIN {len(M):,} triples; no break {int(M.nobreak.sum()):,}; not near {int(M.notnear.sum()):,}')
sections, csv = [], []
for name, X in SAMPLES.items():
    rows = []
    for lab, m in (('All days', np.ones(len(X), bool)), ('After two up days', X.two_up.to_numpy()),
                   ('After one down day', X.one_down.to_numpy()), ('After two down days', X.two_down.to_numpy())):
        x = X[m]
        rows.append([lab, f'{len(x):,}', pct(x.down3.mean() * 100), f'±{clustered_se(x.down3, x.day3) * 100:.1f}',
                     pct(x.up3.mean() * 100), sgn(x.r3.mean()) + '%', sgn(x.x3.mean())])
    t1 = md(rows, ['Group', 'Triples', 'Day 3 down', '± (date-clustered SE)', 'Day 3 up', 'Mean day 3', 'Day 3 vs Nifty (pts)'])
    rows = []
    for ycol, lab in (('down3', 'Share down'), ('r3', 'Mean day 3')):
        r = peers(X, X.two_down, ycol)
        k = 100 if ycol == 'down3' else 1
        rows.append([lab, f'{r["n_sig"]:,}', f'{r["dates"]:,}', sgn(r['diff'] * k), sgn(r['wdiff'] * k), fpv(r['p_t']), fpv(r['p_boot'])])
        csv.append(dict(sample=name, outcome=ycol, **r))
    t2 = md(rows, ['Two-down minus same-day peers', 'Two-down triples', 'Dates', 'Each date equal (pts)', 'Weighted by count (pts)', 'p (t)', 'p (month bootstrap)'])
    cut = X.day3.sort_values().iloc[len(X) // 2]
    H, rows = {}, []
    for lab, Y in (('First half', X[X.day3 < cut]), ('Second half', X[X.day3 >= cut])):
        r = peers(Y, Y.two_down, 'down3'); H[lab] = r
        y = Y[Y.two_down]
        rows.append([lab, f'{Y.day3.min()} .. {Y.day3.max()}', f'{len(y):,}', pct(y.down3.mean() * 100), sgn(r['diff'] * 100), fpv(r['p_t']), fpv(r['p_boot'])])
    f1, f2 = H['First half'], H['Second half']
    conf = bool(f1['p_t'] < 0.05 and f1['p_boot'] < 0.05 and np.sign(f2['diff']) == np.sign(f1['diff']) and f2['p_t'] < 0.05 and f2['p_boot'] < 0.05)
    t3 = md(rows, ['Half', 'Day 3 dates', 'Two-down triples', 'Day 3 down', 'vs same-day peers (pts)', 'p (t)', 'p (bootstrap)'])
    rows = []
    for lab, sig in (('Both days below -1%', (X.r1 < -1) & (X.r2 < -1)), ('Both days below -2%', (X.r1 < -2) & (X.r2 < -2))):
        x = X[sig]; r = peers(X, sig, 'down3')
        rows.append([lab, f'{len(x):,}', pct(x.down3.mean() * 100), sgn(x.r3.mean()) + '%', sgn(r['diff'] * 100), fpv(r['p_boot']), sgn(r['wdiff'] * 100)])
    t4 = md(rows, ['Bigger falls', 'Triples', 'Day 3 down', 'Mean day 3', 'vs peers, dates equal (pts)', 'p', 'vs peers, weighted (pts)'])
    rows = []
    for col_, lab in (('gap3', 'Opening gap'), ('intra3', 'Open to close'), ('r3', 'Whole day 3')):
        r = peers(X, X.two_down, col_)
        rows.append([lab, sgn(X[X.two_down][col_].mean()) + '%', sgn(X[~X.two_down][col_].mean()) + '%', sgn(r['diff']), fpv(r['p_boot'])])
    t5 = md(rows, ['Part of day 3', 'After two down days', 'Other stocks', 'Difference, same day (pts)', 'p'])
    TD = X[X.two_down]
    rows = []
    for lab, v in (('Buy at the day-2 close, sell at the day-3 close', TD.r3 - COST), ('Short at the day-2 close, cover at the day-3 close', -TD.r3 - COST)):
        rows.append([lab, f'{len(v):,}', sgn(v.mean()) + '%', pct((v > 0).mean() * 100), sgn(v.sort_values().iloc[:-5].mean()) + '%',
                     sgn(v[TD.day3 < cut].mean()) + '%', sgn(v[TD.day3 >= cut].mean()) + '%'])
    t6 = md(rows, ['Trade, after 0.17% costs', 'Trades', 'Avg net', 'Winning', 'Without the 5 best', 'First half', 'Second half'])
    sections.append(f'## {name}\n\n{t1}\n\n{t2}\n\n{t3}\n\nCONFIRMED by the plan\'s rule (significant in the first half and '
                    f'again in the second): **{"yes" if conf else "no"}**.\n\n{t4}\n\n{t5}\n\n{t6}\n')
    P(f'== {name}'); P(t1); P(t2); P(t3); P(f'CONFIRMED: {conf}'); P(t4); P(t5); P(t6)

# every quarter, not-near sample
X = SAMPLES['Not near a weekend or holiday (Mon..Thu, Friday open)']
rows, qc = [], []
for q, Y in X.groupby('quarter'):
    y = Y[Y.two_down]
    if len(y) < 20:
        continue
    r = peers(Y, Y.two_down, 'down3')
    rows.append([q, f'{len(y):,}', pct(y.down3.mean() * 100), pct(Y[~Y.two_down].down3.mean() * 100), sgn(r['diff'] * 100), sgn(y.r3.mean()) + '%'])
    qc.append(dict(quarter=q, n=len(y), share_down=y.down3.mean(), others_down=Y[~Y.two_down].down3.mean(), peer_diff=r['diff'], mean_r3=y.r3.mean()))
qc = pd.DataFrame(qc); qc.to_csv(f'{OUT}/no_weekend_by_quarter.csv', index=False)
tq = md(rows, ['Quarter', 'Two-down triples', 'Day 3 down', 'Other stocks down', 'vs same-day peers (pts)', 'Mean day 3'])
tq += f'\n\nBelow its same-day peers (a bounce) in {int((qc.peer_diff < 0).sum())} of {len(qc)} quarters.'
P(tq)

# descriptive: full MAIN by weekday of day 3 and by window kind
rows = []
for lab, key, vals in (('Day 3 weekday', 'weekday3', ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']),
                       ('Day 0 .. day 3 window', 'window', ['no break', 'weekend inside', 'holiday inside'])):
    for v in vals:
        Y = M[M[key] == v]
        y = Y[Y.two_down]
        r = peers(Y, Y.two_down, 'down3')
        rows.append([lab, v, f'{len(y):,}', pct(y.down3.mean() * 100), pct(Y[~Y.two_down].down3.mean() * 100), sgn(r['diff'] * 100), fpv(r['p_boot']), sgn(y.r3.mean()) + '%'])
tw = md(rows, ['Split', 'Value', 'Two-down triples', 'Day 3 down', 'Other stocks down', 'vs same-day peers (pts)', 'p', 'Mean day 3'])
P(tw)
pd.DataFrame(csv).to_csv(f'{OUT}/no_weekend_peers.csv', index=False)
open(f'{OUT}/table_no_weekend.md', 'w').write(
    '# Two down days, away from weekends and holidays\n\nPLAN_NO_WEEKEND.txt: the MAIN sample of PLAN.txt (ordinary days, F&O '
    'stocks while in F&O, May 2021 .. Sep 2026), restricted to stretches with no weekend or holiday. "Not near": day 0 '
    '(Monday) to day 3 (Thursday) on four calendar days in a row, and the Friday a normal session. "No break inside": four '
    'calendar weekdays in a row (day 3 a Thursday or Friday). A weekend session (Muhurat, special Saturday) counts as a '
    'break.\n\n' + '\n'.join(sections) + '\n## Every quarter (not near a weekend or holiday)\n\n' + tq +
    '\n\n## What weekends and holidays do (all ordinary days)\n\n' + tw + '\n')
open(f'{OUT}/no_weekend.log', 'w').write('\n'.join(log) + '\n')
