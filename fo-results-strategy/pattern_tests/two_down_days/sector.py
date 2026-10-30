#!/usr/bin/env python3
"""PLAN_SECTOR.txt: two and three down days by sector (stocks by NSE index sector; sector indices themselves).

Reads OUT/days.csv.gz (build_days.py), OUT/windows4.csv.gz (three_down.py), LAB_ROOT sessions and index closes, and
REPO_ROOT/results/nifty_sector_3day/results_3day.csv; writes OUT/table_sector.md, sector_*.csv and sector.log.
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
PACK = os.path.join(LAB, 'sector_lab', 'data')
B, SEED, MIN_N = 5000, 20261102, 100
log = []
def P(*a):
    log.append(' '.join(str(x) for x in a))
    print(*a)
h = hashlib.sha256(open(os.path.join(HERE, 'PLAN_SECTOR.txt'), 'rb').read()).hexdigest()
P(f'PLAN_SECTOR.txt sha256 {h} ({"MATCH" if h == open(os.path.join(HERE, "PLAN_SECTOR.sha256")).read().strip() else "MISMATCH"})')
rng = np.random.default_rng(SEED)
pct = lambda v: '-' if pd.isna(v) else f'{v:.1f}%'
sgn = lambda v: '-' if pd.isna(v) else f'{v:+.2f}'
fpv = lambda p: '-' if pd.isna(p) else ('<0.001' if p < 0.001 else f'{p:.3f}')
def md(rows, cols):
    out = ['| ' + ' | '.join(cols) + ' |', '|' + '|'.join('---' if i == 0 else '---:' for i in range(len(cols))) + '|']
    return '\n'.join(out + ['| ' + ' | '.join(str(x) for x in r) + ' |' for r in rows])
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
def test(d):
    """mean of per-date differences, t-test over dates, month bootstrap"""
    d = d.dropna()
    if len(d) < 3:
        return np.nan, np.nan, np.nan, len(d)
    ms = d.groupby(d.index.str[:7]).agg(['sum', 'size'])
    idx = rng.integers(0, len(ms), size=(B, len(ms)))
    bs = ms['sum'].to_numpy()[idx].sum(1) / ms['size'].to_numpy()[idx].sum(1)
    return d.mean(), stats.ttest_1samp(d, 0).pvalue, min(1.0, 2 * min((bs <= 0).mean(), (bs >= 0).mean())), len(d)

sec = pd.read_csv(os.path.join(REPO, 'results', 'nifty_sector_3day', 'results_3day.csv'), usecols=['symbol', 'nifty_sector']).drop_duplicates('symbol')
dts = pd.to_datetime(pd.read_csv(f'{PACK}/sessions.csv').day)
T = len(dts)

# 2D sample (outcome day 3) with the not-near flag of PLAN_NO_WEEKEND.txt
D = pd.read_csv(f'{OUT}/days.csv.gz')
D = D[D.main].copy()
i3 = D.i3.to_numpy()
d0, d3 = dts.to_numpy()[i3 - 3], dts.to_numpy()[i3]
nx = dts.to_numpy()[np.minimum(i3 + 1, T - 1)]
wd = np.stack([pd.DatetimeIndex(dts.to_numpy()[i3 - k]).weekday for k in range(4)])
nobreak = ((d3 - d0).astype('timedelta64[D]').astype(int) == 3) & (wd < 5).all(axis=0)
D['away'] = nobreak & (i3 + 1 < T) & ((nx - d3).astype('timedelta64[D]').astype(int) == 1) & (pd.DatetimeIndex(nx).weekday < 5)
D2 = pd.DataFrame({'symbol': D.symbol, 'date': D.day3, 'sector': D.nifty_sector, 'sig': (D.r1 < 0) & (D.r2 < 0),
                   'y': D.r3, 'away': D.away})
# 3D sample (outcome day 4) with the holiday-free flag of PLAN_THREE_DOWN.txt
W = pd.read_csv(f'{OUT}/windows4.csv.gz').merge(sec, on='symbol', how='left')
D3 = pd.DataFrame({'symbol': W.symbol, 'date': W.day4, 'sector': W.nifty_sector, 'sig': (W.r1 < 0) & (W.r2 < 0) & (W.r3 < 0),
                   'y': W.r4, 'away': W.holfree.astype(bool)})
for X in (D2, D3):
    X['down'] = (X.y < 0).astype(float)
P(f'2D sample {len(D2):,} (away {int(D2.away.sum()):,}); 3D sample {len(D3):,} (away {int(D3.away.sum()):,}); stocks without a sector: '
  f'{int(D2.sector.isna().sum() + D3.sector.isna().sum())}')

# ---------------------------------------------------------------- part A: stocks by sector
def sector_rows(X):
    allp = X[~X.sig].groupby('date').down.mean()                      # all other stocks that date
    secp = X[~X.sig].groupby(['sector', 'date']).down.mean()          # same-sector stocks without the signal that date
    cut = X.date.sort_values().iloc[len(X) // 2]
    out = []
    for s, G in X[X.sig].groupby('sector'):
        g = G.groupby('date').down.mean()
        da = (g - allp.reindex(g.index))
        ds = (g - secp.loc[s].reindex(g.index)) if s in secp.index.get_level_values(0) else g * np.nan
        r = dict(sector=s, n=len(G), stocks=G.symbol.nunique(), share_down=G.down.mean(), mean_y=G.y.mean(),
                 others_down=X[(X.sector == s) & ~X.sig].down.mean())
        r['all_diff'], r['all_pt'], r['all_pb'], _ = test(da)
        r['sec_diff'], r['sec_pt'], r['sec_pb'], r['sec_dates'] = test(ds)
        for half, m in (('h1', ds.index < cut), ('h2', ds.index >= cut)):
            r[f'{half}_diff'], _, r[f'{half}_pb'], _ = test(ds[m])
        out.append(r)
    R = pd.DataFrame(out)
    t = R.n >= MIN_N
    for c_ in ('all_pb', 'sec_pb'):
        R[c_.replace('pb', 'holm')] = np.nan; R[c_.replace('pb', 'bh')] = np.nan
        R.loc[t, c_.replace('pb', 'holm')] = holm(R.loc[t, c_]); R.loc[t, c_.replace('pb', 'bh')] = bh(R.loc[t, c_])
    R['h1_holm'] = np.nan
    R.loc[t, 'h1_holm'] = holm(R.loc[t, 'h1_pb'])
    R['confirmed'] = t & (R.h1_holm < 0.05) & (np.sign(R.h2_diff) == np.sign(R.h1_diff)) & (R.h2_pb < 0.05)
    return R.sort_values('sec_diff')

COLS = ['Sector', 'Windows', 'Stocks', 'Next day down', 'Same sector, no signal', 'Mean next day', 'vs all stocks (pts)', 'Holm',
        'vs own sector (pts)', 'p', 'Holm', 'First half / second half (pts)', 'Confirmed']
def rows_md(R):
    rows = []
    for r in R.itertuples():
        tested = r.n >= MIN_N
        rows.append([r.sector, f'{r.n:,}', r.stocks, pct(r.share_down * 100), pct(r.others_down * 100), sgn(r.mean_y) + '%',
                     sgn(r.all_diff * 100), fpv(r.all_holm) if tested else 'not tested', sgn(r.sec_diff * 100), fpv(r.sec_pb),
                     fpv(r.sec_holm) if tested else 'not tested', f'{sgn(r.h1_diff * 100)} / {sgn(r.h2_diff * 100)}',
                     'yes' if r.confirmed else 'no'])
    return md(rows, COLS)
partA, allA = [], []
for sig, X, ver_all, ver_away in (('Two down days, then day 3', D2, 'All ordinary days', 'Away from weekends and holidays (Mon..Thu, Friday open)'),
                                  ('Three down days, then day 4', D3, 'All ordinary days', 'No holiday nearby (weekends allowed)')):
    for ver, Y in ((ver_all, X), (ver_away, X[X.away])):
        R = sector_rows(Y)
        R.insert(0, 'version', ver); R.insert(0, 'signal', sig)
        allA.append(R)
        n_conf, n_holm = int(R.confirmed.sum()), int((R.sec_holm < 0.05).sum())
        lean_down = int(((R.sec_diff > 0) & (R.n >= MIN_N)).sum()); tested = int((R.n >= MIN_N).sum())
        txt = (f'### {sig}: {ver}\n\n{rows_md(R)}\n\nTested sectors (at least {MIN_N} windows): {tested}. Falling more often than '
               f'their own sector the next day: {lean_down} of {tested}. Significant after Holm across sectors (own-sector '
               f'comparison): {n_holm}. Confirmed in both halves: {n_conf}.\n')
        partA.append(txt); P(txt)
pd.concat(allA).to_csv(f'{OUT}/sector_stocks.csv', index=False, float_format='%.6g')

# ---------------------------------------------------------------- part B: sector indices themselves
ix = pd.read_csv(f'{PACK}/index_close.csv', index_col=0)
assert (pd.to_datetime(ix.index) == dts).all()
NAMES = ['Nifty Auto', 'Nifty Bank', 'Nifty Financial Services', 'Nifty FMCG', 'Nifty IT', 'Nifty Media', 'Nifty Metal',
         'Nifty Pharma', 'Nifty PSU Bank', 'Nifty Private Bank', 'Nifty Realty', 'Nifty Healthcare Index',
         'Nifty Consumer Durables', 'Nifty Oil & Gas']
def iret(name):
    c = ix[name].to_numpy(float)
    r = np.full(T, np.nan)
    r[1:] = (c[1:] / c[:-1] - 1) * 100            # NaN when either close is missing: only consecutive sessions
    r[[k for k, d in enumerate(ix.index) if d in ('2015-12-02', '2016-06-21')]] = np.nan
    return r
NIFTY = iret('Nifty 50')
cal = {}
for k in (3, 4):                                   # window day0..day_k on k+1 consecutive calendar weekdays
    ok = np.zeros(T, bool)
    for t in range(k, T):
        span = pd.date_range(dts[t - k], dts[t])
        ok[t] = len(span) == k + 1 and (span.weekday < 5).all()
    cal[k] = ok
start = int(np.searchsorted(dts.to_numpy(), np.datetime64('2016-01-01')))
def index_test(r, ndown, version):
    """after ndown down days: next day down vs every other session with the same history available"""
    k = ndown + 1
    ok = np.ones(T, bool)
    for q in range(k):
        ok &= ~np.isnan(np.roll(r, q))
    ok[:start] = False
    if version == 'away':
        ok &= cal[k]
    sig = ok.copy()
    for q in range(1, k):
        sig &= np.roll(r, q) < 0
    oth = ok & ~sig
    a_, b_ = r[sig] < 0, r[oth] < 0
    p = stats.fisher_exact([[a_.sum(), (~a_).sum()], [b_.sum(), (~b_).sum()]])[1] if sig.sum() else np.nan
    return dict(n=int(sig.sum()), share_down=a_.mean(), others_down=b_.mean(), mean=np.nanmean(r[sig]), p=p)
partB, allB = [], []
for ndown in (2, 3):
    for version, vlab in (('all', 'all sessions'), ('away', 'no weekend or holiday inside')):
        for measure, mlab in (('raw', 'the index'), ('rel', 'the index minus Nifty 50')):
            out = []
            for name in NAMES:
                r = iret(name)
                if measure == 'rel':
                    r = r - NIFTY
                out.append(dict(index=name, **index_test(r, ndown, version)))
            R = pd.DataFrame(out)
            R['holm'] = holm(R.p.fillna(1)); R['bh'] = bh(R.p.fillna(1))
            ref = index_test(NIFTY, ndown, version) if measure == 'raw' else None
            R.insert(0, 'measure', mlab); R.insert(0, 'version', vlab); R.insert(0, 'signal', f'{ndown} down days')
            allB.append(R)
            rows = [[x.index, f'{x.n:,}', pct(x.share_down * 100), pct(x.others_down * 100), sgn(x.mean) + '%', fpv(x.p), fpv(x.holm), fpv(x.bh)]
                    for x in R.itertuples()]
            if ref:
                rows.append(['Nifty 50 (reference)', f'{ref["n"]:,}', pct(ref['share_down'] * 100), pct(ref['others_down'] * 100), sgn(ref['mean']) + '%', fpv(ref['p']), '-', '-'])
            txt = (f'### After {ndown} down days, {mlab}, {vlab}\n\n' +
                   md(rows, ['Index', 'Runs', 'Next day down', 'Other sessions down', 'Mean next day', 'p (Fisher)', 'Holm', 'BH q']) +
                   f'\n\nHigher than on other sessions: {int((R.share_down > R.others_down).sum())} of {len(R)}; Holm p < 0.05: {int((R.holm < 0.05).sum())}.\n')
            partB.append(txt); P(txt)
pd.concat(allB).to_csv(f'{OUT}/sector_indices.csv', index=False, float_format='%.6g')
open(f'{OUT}/table_sector.md', 'w').write(
    '# Two and three down days, by sector\n\nPLAN_SECTOR.txt. Part A: F&O stocks on ordinary days (as in table_main.md and '
    'table_three_down.md), split by NSE index sector. "vs all stocks": the share of next days down minus that of every '
    'other eligible stock on the same date. "vs own sector": minus that of the other stocks of the same sector on the same '
    'date that did not have the signal, so a whole sector moving together does not count. Differences in percentage '
    'points (negative = a bounce), averaged over dates; p from a 5,000-draw month bootstrap; Holm across the tested '
    'sectors. Confirmed: own-sector difference significant after Holm in the first half and the same sign with p < 0.05 in '
    'the second.\n\n## Part A: stocks, by sector\n\n' + '\n'.join(partA) +
    '\n## Part B: the sector indices themselves (2016 .. Sep 2026)\n\nA run counts only consecutive sessions that both '
    'have a close (Healthcare, Consumer Durables and Oil & Gas have long gaps in this data). p: Fisher exact test of the '
    'share down against all other sessions of the same index; Holm and BH across the 14 indices.\n\n' + '\n'.join(partB))
open(f'{OUT}/sector.log', 'w').write('\n'.join(log) + '\n')
