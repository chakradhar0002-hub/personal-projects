#!/usr/bin/env python3
"""Tests of PLAN.txt on OUT/days.csv.gz: after two down days on ordinary days, is day 3 down?

Writes the table_*.md files, their CSVs and run.log in OUT (default REPO_ROOT/results/two_down_days).
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
B, SEED, COST = 5000, 20261030, 0.17
log = []
def P(*a):
    log.append(' '.join(str(x) for x in a))
    print(*a)

plan = open(os.path.join(HERE, 'PLAN.txt'), 'rb').read()
want = open(os.path.join(HERE, 'PLAN.sha256')).read().strip()
P(f'PLAN.txt sha256 {hashlib.sha256(plan).hexdigest()} ({"MATCH" if hashlib.sha256(plan).hexdigest() == want else "MISMATCH"})')

D = pd.read_csv(f'{OUT}/days.csv.gz')
D['down3'] = (D.r3 < 0).astype(float)
D['up3'] = (D.r3 > 0).astype(float)
D['x3'] = D.r3 - D.n3
D['two_down'] = (D.r1 < 0) & (D.r2 < 0)
D['two_up'] = (D.r1 > 0) & (D.r2 > 0)
D['one_down'] = D.r2 < 0
D['month'] = D.day3.str[:7]
D['year'] = D.day3.str[:4]
D['quarter'] = D.year + ' Q' + ((D.day3.str[5:7].astype(int) - 1) // 3 + 1).astype(str)
SAMPLES = {'MAIN': D[D.main], 'ALL21': D[D.all21], 'LONG': D[D.long]}
M = SAMPLES['MAIN']
half_cut = M.day3.sort_values().iloc[len(M) // 2]
P(f'MAIN halves split at day3 {half_cut}')
rng = np.random.default_rng(SEED)
pct = lambda v: '-' if pd.isna(v) else f'{v:.1f}%'
sgn = lambda v: '-' if pd.isna(v) else f'{v:+.2f}'
fpv = lambda p: '-' if pd.isna(p) else ('<0.001' if p < 0.001 else f'{p:.3f}')
def md(df, cols):
    out = ['| ' + ' | '.join(cols) + ' |', '|' + '|'.join('---' if i == 0 else '---:' for i in range(len(cols))) + '|']
    for r in df:
        out.append('| ' + ' | '.join(str(x) for x in r) + ' |')
    return '\n'.join(out)

def clustered_se(y, dates):
    """standard error of a share with observations clustered by date"""
    y = np.asarray(y, float)
    p = y.mean()
    g = pd.Series(y - p).groupby(np.asarray(dates)).sum()
    return np.sqrt((g ** 2).sum()) / len(y)

def peers(X, sig, ycol):
    """same-day peer difference: per day3 date, mean y of signal rows minus mean y of the other rows"""
    g = X.assign(s=sig.to_numpy()).groupby(['day3', 's'])[ycol].agg(['mean', 'size']).unstack('s')
    g = g.dropna()
    if len(g) < 3:
        return dict(diff=np.nan, wdiff=np.nan, dates=len(g), p_t=np.nan, p_boot=np.nan, n_sig=0)
    d = g[('mean', True)] - g[('mean', False)]
    w = g[('size', True)]
    t_p = stats.ttest_1samp(d, 0).pvalue
    mon = pd.Series(d.index.str[:7], index=d.index)
    ms = d.groupby(mon).agg(['sum', 'size'])
    idx = rng.integers(0, len(ms), size=(B, len(ms)))
    bs = ms['sum'].to_numpy()[idx].sum(1) / ms['size'].to_numpy()[idx].sum(1)
    p_b = min(1.0, 2 * min((bs <= 0).mean(), (bs >= 0).mean()))
    return dict(diff=d.mean(), wdiff=(d * w).sum() / w.sum(), dates=len(d), p_t=t_p, p_boot=p_b, n_sig=int(w.sum()))

# ---------------------------------------------------------------- main table
rows, csv = [], []
for name, X in SAMPLES.items():
    for lab, m in (('All days', np.ones(len(X), bool)), ('After two up days', X.two_up.to_numpy()),
                   ('After one down day', X.one_down.to_numpy()), ('After two down days', X.two_down.to_numpy())):
        x = X[m]
        se = clustered_se(x.down3, x.day3) * 100
        rows.append([name, lab, f'{len(x):,}', pct(x.down3.mean() * 100), f'±{se:.1f}', pct(x.up3.mean() * 100),
                     sgn(x.r3.mean()) + '%', sgn(x.r3.median()) + '%', sgn(x.x3.mean())])
        csv.append(dict(sample=name, group=lab, n=len(x), share_down=x.down3.mean(), se_down=se / 100,
                        share_up=x.up3.mean(), mean_r3=x.r3.mean(), median_r3=x.r3.median(), mean_r3_vs_nifty=x.x3.mean()))
main_tab = md(rows, ['Sample', 'Group', 'Triples', 'Day 3 down', '± (date-clustered SE)', 'Day 3 up', 'Mean day 3',
                     'Median day 3', 'Day 3 vs Nifty (pts)'])
prow, pcsv = [], []
for name, X in SAMPLES.items():
    for ycol, lab in (('down3', 'share down'), ('r3', 'mean day-3 return')):
        r = peers(X, X.two_down, ycol)
        k = 100 if ycol == 'down3' else 1
        prow.append([name, lab, f'{r["n_sig"]:,}', f'{r["dates"]:,}', sgn(r['diff'] * k), sgn(r['wdiff'] * k), fpv(r['p_t']), fpv(r['p_boot'])])
        pcsv.append(dict(sample=name, outcome=ycol, **r))
peer_tab = md(prow, ['Sample', 'Outcome', 'Two-down triples', 'Dates', 'Two-down minus same-day peers (each date equal)',
                     'Weighted by two-down count', 'p (t over dates)', 'p (month bootstrap)'])
pd.DataFrame(csv).to_csv(f'{OUT}/main.csv', index=False)
pd.DataFrame(pcsv).to_csv(f'{OUT}/peers.csv', index=False)
open(f'{OUT}/table_main.md', 'w').write(
    '# After two down days: is day 3 down?\n\nOrdinary days only (see PLAN.txt): MAIN = F&O stocks while in F&O, May 2021 '
    '.. Sep 2026, no result within 5 sessions, no split/bonus/demerger or NSE ex-date on the three days; ALL21 = the same, '
    'any F&O status; LONG = 2016 .. 2026, only split/bonus/demerger days removed (results and dividends before 2021 not '
    'known).\n\n' + main_tab + '\n\nShares in %; returns in %, gross. Day 3 vs Nifty: day-3 return minus Nifty 50\'s, '
    'percentage points.\n\n## Against other stocks on the same day\n\n' + peer_tab +
    '\n\nShare down in percentage points, return in percentage points. Each day-3 date gives one difference (two-down '
    'stocks minus every other eligible stock that day); the mean is over dates. p: t-test over dates, and a 5,000-draw '
    'bootstrap of calendar months (two-sided).\n')
P(main_tab); P(peer_tab)

# ---------------------------------------------------------------- streaks
rows, csv = [], []
for kind, colk in (('down', 'dstreak2'), ('up', 'ustreak2')):
    for k in range(1, 7):
        sig = (M[colk] >= 6) if k == 6 else (M[colk] == k)
        x = M[sig]
        r = peers(M, sig, 'down3')
        lab = f'{k}+ {kind}' if k == 6 else f'{k} {kind}'
        rows.append([lab, f'{len(x):,}', pct(x.down3.mean() * 100), sgn(x.r3.mean()) + '%', sgn(r['diff'] * 100), fpv(r['p_t']), fpv(r['p_boot'])])
        csv.append(dict(streak=lab, n=len(x), share_down=x.down3.mean(), mean_r3=x.r3.mean(), peer_diff=r['diff'], p_t=r['p_t'], p_boot=r['p_boot']))
pd.DataFrame(csv).to_csv(f'{OUT}/streaks.csv', index=False)
st_tab = md(rows, ['Days in a row before (ending day 2)', 'Triples', 'Next day down', 'Mean next day', 'vs same-day peers (pts)', 'p (t)', 'p (bootstrap)'])
open(f'{OUT}/table_streaks.md', 'w').write('# Streaks: after k down (or up) days in a row, the next day (MAIN)\n\n' + st_tab +
    '\n\n"vs same-day peers": share of next days down, minus that of all other eligible stocks on the same date, '
    'percentage points.\n')
P(st_tab)

# ---------------------------------------------------------------- size
X = M.copy()
X['fall2'] = X.r1 + X.r2
X['fifth'] = X.groupby('day3').fall2.transform(lambda s: pd.qcut(s.rank(method='first'), 5, labels=False) if len(s) >= 5 else np.nan)
rows = []
for f, lab in zip(range(5), ['Bottom (fell most)', '2', '3', '4', 'Top (rose most)']):
    x = X[X.fifth == f]
    rows.append([lab, f'{len(x):,}', sgn(x.fall2.mean()) + '%', pct(x.down3.mean() * 100), sgn(x.r3.mean()) + '%', sgn(x.x3.mean())])
size1 = md(rows, ['Fifth of day 1 + day 2 (within each date)', 'Triples', 'Avg two-day move', 'Day 3 down', 'Mean day 3', 'Day 3 vs Nifty'])
rows, csv = [], []
for lab, sig in (('Two down days', M.two_down), ('Both days below -1%', (M.r1 < -1) & (M.r2 < -1)),
                 ('Both days below -2%', (M.r1 < -2) & (M.r2 < -2)),
                 ('Two down days vs Nifty (stock minus Nifty < 0 both days)', ((M.r1 - M.n1) < 0) & ((M.r2 - M.n2) < 0))):
    x = M[sig]
    r = peers(M, sig, 'down3'); rr = peers(M, sig, 'r3')
    rows.append([lab, f'{len(x):,}', pct(x.down3.mean() * 100), sgn(x.r3.mean()) + '%', sgn(r['diff'] * 100), fpv(r['p_boot']), sgn(rr['diff']), fpv(rr['p_boot'])])
    csv.append(dict(signal=lab, n=len(x), share_down=x.down3.mean(), mean_r3=x.r3.mean(), peer_down=r['diff'], p_down=r['p_boot'], peer_r3=rr['diff'], p_r3=rr['p_boot']))
pd.DataFrame(csv).to_csv(f'{OUT}/size.csv', index=False)
size2 = md(rows, ['Signal', 'Triples', 'Day 3 down', 'Mean day 3', 'Share down vs peers (pts)', 'p', 'Mean day 3 vs peers (pts)', 'p'])
open(f'{OUT}/table_size.md', 'w').write('# Does the size of the two-day fall matter? (MAIN)\n\n' + size1 + '\n\n' + size2 +
    '\n\np: month bootstrap of the same-day peer difference.\n')
P(size1); P(size2)

# ---------------------------------------------------------------- day 3 split
rows = []
for col_, lab in (('gap3', 'Overnight gap (open day 3 / close day 2)'), ('intra3', 'During day 3 (close / open)'), ('r3', 'Whole day 3')):
    r = peers(M, M.two_down, col_)
    rows.append([lab, sgn(M[M.two_down][col_].mean()) + '%', sgn(M[~M.two_down][col_].mean()) + '%', sgn(r['diff']), fpv(r['p_t']), fpv(r['p_boot'])])
split_tab = md(rows, ['Part of day 3', 'After two down days', 'Other stocks', 'Difference, same day (pts)', 'p (t)', 'p (bootstrap)'])
open(f'{OUT}/table_split.md', 'w').write('# Where day 3 moves: the opening gap or the session (MAIN)\n\n' + split_tab + '\n')
P(split_tab)

# ---------------------------------------------------------------- market state and the index itself
rows = []
ndown = (M.n1 < 0) & (M.n2 < 0)
vmed = M.vix2.median()
for lab, cond in (('Nifty 50 also down both days', ndown), ('Nifty 50 not down both days', ~ndown),
                  (f'India VIX at the day-2 close above {vmed:.1f}', M.vix2 > vmed), (f'India VIX at or below {vmed:.1f}', M.vix2 <= vmed)):
    X = M[cond]
    x = X[X.two_down]
    r = peers(X, X.two_down, 'down3')
    rows.append([lab, f'{len(x):,}', pct(x.down3.mean() * 100), pct(X[~X.two_down].down3.mean() * 100), sgn(x.r3.mean()) + '%', sgn(r['diff'] * 100), fpv(r['p_boot'])])
mk1 = md(rows, ['Market state', 'Two-down triples', 'Day 3 down', 'Other stocks down', 'Mean day 3', 'vs same-day peers (pts)', 'p'])
ix = pd.read_csv(os.path.join(LAB, 'sector_lab', 'data', 'index_close.csv'), index_col=0)
rows = []
for name in ('Nifty 50', 'Nifty Bank'):
    c = ix[name]
    r = c.pct_change() * 100
    r[r.index.isin(['2015-12-02', '2016-06-21'])] = np.nan
    df = pd.DataFrame({'r1': r.shift(2), 'r2': r.shift(1), 'r3': r}).dropna()
    df = df[df.index >= '2016-01-01']
    for lab, m in (('all sessions', np.ones(len(df), bool)), ('after two down days', (df.r1 < 0) & (df.r2 < 0)), ('after two up days', (df.r1 > 0) & (df.r2 > 0))):
        x = df[m]
        bt = stats.binomtest(int((x.r3 < 0).sum()), len(x), (df.r3 < 0).mean()).pvalue if lab != 'all sessions' else np.nan
        rows.append([name, lab, f'{len(x):,}', pct((x.r3 < 0).mean() * 100), sgn(x.r3.mean()) + '%', fpv(bt)])
mk2 = md(rows, ['Index', 'Sessions', 'Count', 'Next day down', 'Mean next day', 'p (vs all sessions)'])
open(f'{OUT}/table_market.md', 'w').write('# Market state, and the index itself\n\n## Two down days by market state (MAIN)\n\n' + mk1 +
    '\n\n## Nifty 50 and Nifty Bank themselves, 2016 .. Sep 2026\n\n' + mk2 + '\n\np for the index: binomial test of the share down against all sessions.\n')
P(mk1); P(mk2)

# ---------------------------------------------------------------- stability
def by(colname, X=M):
    rows, csv = [], []
    for k, X_ in X.groupby(colname):
        x = X_[X_.two_down]
        if len(x) < 20:
            continue
        r = peers(X_, X_.two_down, 'down3')
        rows.append([k, f'{len(x):,}', pct(x.down3.mean() * 100), pct(X_[~X_.two_down].down3.mean() * 100),
                     sgn(r['diff'] * 100), sgn(x.r3.mean()) + '%', sgn(X_[~X_.two_down].r3.mean()) + '%'])
        csv.append(dict(key=k, n=len(x), share_down=x.down3.mean(), others_down=X_[~X_.two_down].down3.mean(), peer_diff=r['diff'],
                        mean_r3=x.r3.mean(), others_r3=X_[~X_.two_down].r3.mean(), p_boot=r['p_boot']))
    return rows, pd.DataFrame(csv)
cols = ['Two-down triples', 'Day 3 down', 'Other stocks down', 'Difference, same day (pts)', 'Mean day 3', 'Others mean day 3']
qr, qc = by('quarter'); yr, yc = by('year')
qc.to_csv(f'{OUT}/by_quarter.csv', index=False); yc.to_csv(f'{OUT}/by_year.csv', index=False)
q_pos = int((qc.peer_diff > 0).sum())
open(f'{OUT}/table_by_quarter.md', 'w').write('# Every calendar quarter (MAIN)\n\n' + md(qr, ['Quarter'] + cols) +
    f'\n\nThe two-down group fell more often than its same-day peers in {q_pos} of {len(qc)} quarters.\n')
open(f'{OUT}/table_by_year.md', 'w').write('# By year (MAIN)\n\n' + md(yr, ['Year'] + cols) + '\n')
P(md(qr, ['Quarter'] + cols)); P(md(yr, ['Year'] + cols))
sr, sc = by('nifty_sector')
sc.to_csv(f'{OUT}/by_sector.csv', index=False)
open(f'{OUT}/table_sectors.md', 'w').write('# By NSE index sector (MAIN)\n\n' + md(sr, ['Sector'] + cols) + '\n')

# halves and the confirmation rule
H = {}
for lab, X in (('First half', M[M.day3 < half_cut]), ('Second half', M[M.day3 >= half_cut])):
    r = peers(X, X.two_down, 'down3'); rr = peers(X, X.two_down, 'r3')
    H[lab] = (X, r, rr)
f1, f2 = H['First half'][1], H['Second half'][1]
confirmed = (f1['p_t'] < 0.05 and f1['p_boot'] < 0.05 and np.sign(f2['diff']) == np.sign(f1['diff']) and f2['p_t'] < 0.05 and f2['p_boot'] < 0.05)
rows = []
for lab, (X, r, rr) in H.items():
    x = X[X.two_down]
    rows.append([lab, f'{X.day3.min()} .. {X.day3.max()}', f'{len(x):,}', pct(x.down3.mean() * 100), sgn(r['diff'] * 100),
                 fpv(r['p_t']), fpv(r['p_boot']), sgn(rr['diff']), fpv(rr['p_boot'])])
half_tab = md(rows, ['Half', 'Day 3 dates', 'Two-down triples', 'Day 3 down', 'Share down vs peers (pts)', 'p (t)', 'p (bootstrap)', 'Mean day 3 vs peers (pts)', 'p'])
P(half_tab); P(f'CONFIRMED (plan rule): {"yes" if confirmed else "no"}')

# per stock
rows = []
for s, X in M.groupby('symbol'):
    x = X[X.two_down]
    if len(x) < 30:
        continue
    base = X.down3.mean()
    k = int(x.down3.sum())
    rows.append(dict(symbol=s, n=len(x), down=k, share_down=k / len(x), own_share_down=base,
                     diff=k / len(x) - base, p=stats.binomtest(k, len(x), base).pvalue, mean_r3=x.r3.mean()))
ST = pd.DataFrame(rows).sort_values('diff')
def holm(p):
    p = np.asarray(p, float); o = np.argsort(p); adj = np.empty(len(p)); run = 0.0
    for k, i in enumerate(o):
        run = max(run, (len(p) - k) * p[i]); adj[i] = min(1.0, run)
    return adj
def bh(p):
    p = np.asarray(p, float); n = len(p); o = np.argsort(p)[::-1]; adj = np.empty(n); run = 1.0
    for k, i in enumerate(o):
        run = min(run, p[i] * n / (n - k)); adj[i] = run
    return adj
ST['holm'] = holm(ST.p)
ST['bh'] = bh(ST.p)
ST.to_csv(f'{OUT}/by_stock.csv', index=False, float_format='%.6g')
srow = lambda r: [r.symbol, r.n, pct(r.share_down * 100), pct(r.own_share_down * 100), sgn(r.diff * 100), sgn(r.mean_r3) + '%', fpv(r.p), fpv(r.holm), fpv(r.bh)]
scols = ['Stock', 'Two-down triples', 'Day 3 down', 'Stock\'s own normal share down', 'Difference (pts)', 'Mean day 3', 'p', 'Holm p', 'BH q']
passed = ST[ST.bh < 0.05]
stock_md = ('# By stock (MAIN, stocks with at least 30 two-down triples)\n\n'
            f'{len(ST)} stocks tested. Passing the correction for {len(ST)} stocks (BH q < 0.05): {len(passed)}'
            + (' (' + ', '.join(passed.symbol) + ')' if len(passed) else '') + f'; Holm p < 0.05: {int((ST.holm < 0.05).sum())}. '
            f'Stocks whose two-down share down is above their own normal share: {int((ST["diff"] > 0).sum())} of {len(ST)}.\n\n'
            '## Ten that fell most often on day 3 (relative to their own normal)\n\n' + md([srow(r) for r in ST.tail(10)[::-1].itertuples()], scols) +
            '\n\n## Ten that bounced most often\n\n' + md([srow(r) for r in ST.head(10).itertuples()], scols) +
            '\n\np: binomial test against the stock\'s own share of down days over all its MAIN triples. Full list: by_stock.csv.\n')
open(f'{OUT}/table_stocks.md', 'w').write(stock_md)
P(stock_md)

# ---------------------------------------------------------------- tradable
rows, csv = [], []
TD = M[M.two_down]
for lab, v in (('Buy at the day-2 close, sell at the day-3 close', TD.r3 - COST),
               ('Short at the day-2 close, cover at the day-3 close', -TD.r3 - COST),
               ('Buy, hold 2 sessions (day 3 + day 4)', (TD.r3 + TD.r4) - COST),
               ('Buy, hold 5 sessions (day 3 .. day 7)', TD.r3to7 - COST)):
    v = v.dropna()
    top5 = v.sort_values().iloc[:-5]
    first = v[TD.loc[v.index, 'day3'] < half_cut]; second = v[TD.loc[v.index, 'day3'] >= half_cut]
    rows.append([lab, f'{len(v):,}', sgn(v.mean()) + '%', pct((v > 0).mean() * 100), sgn(top5.mean()) + '%', sgn(first.mean()) + '%', sgn(second.mean()) + '%'])
    csv.append(dict(trade=lab, n=len(v), net=v.mean(), win=(v > 0).mean(), without_best5=top5.mean(), first_half=first.mean(), second_half=second.mean()))
allb = (M.r3 - COST)
rows.append(['Reference: buy every eligible stock-day, sell next close', f'{len(allb):,}', sgn(allb.mean()) + '%', pct((allb > 0).mean() * 100), '-', '-', '-'])
pd.DataFrame(csv).to_csv(f'{OUT}/tradable.csv', index=False)
yrows = []
for y, g in TD.groupby('year'):
    yrows.append([y, f'{len(g):,}', sgn((g.r3 - COST).mean()) + '%', sgn((-g.r3 - COST).mean()) + '%'])
tr_tab = md(rows, ['Trade (MAIN, after 0.17% a round trip)', 'Trades', 'Avg net', 'Winning trades', 'Without the 5 best', 'First half', 'Second half'])
open(f'{OUT}/table_tradable.md', 'w').write('# As a trade (MAIN, two down days)\n\n' + tr_tab + '\n\n## By year\n\n' +
    md(yrows, ['Year', 'Trades', 'Buy, 1 day, net', 'Short, 1 day, net']) + '\n\n## Halves and the plan\'s confirmation rule\n\n' + half_tab +
    f'\n\nCONFIRMED by the plan\'s rule (same-day peer difference in share down significant in the first half and again '
    f'in the second): **{"yes" if confirmed else "no"}**.\n')
P(tr_tab)
open(f'{OUT}/run.log', 'w').write('\n'.join(log) + '\n\nDEVIATIONS\n- 2015-12-02 and 2016-06-21 dropped (LONG only): a trading '
    'day is missing from the session list before each, so their return spans two sessions.\n')
