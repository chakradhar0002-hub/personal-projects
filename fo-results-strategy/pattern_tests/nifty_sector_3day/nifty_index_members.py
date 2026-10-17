#!/usr/bin/env python3
"""Three-day results sum (Day-1 + Result day + Day+1 daily returns) by Nifty sectoral and thematic index membership,
and against the index's own move over the same three sessions, 22 seasons.

Universe: results of stocks that were in F&O at the time (events.csv in_fo == True), as in sector_3day.
Membership: today's NSE constituent lists (ind_<name>list.csv in LISTS_DIR); a stock can be in several indices.
These are today's constituents, so the grouping has the same look-ahead / survivorship caveat as the stock universe.
three_day = ret_dm1 + ret_rd + ret_dp1 (sum, not compounded). Index three-day sum = sum of the index's daily
close-to-close returns on sessions i_m1, i_rd, i_p1; missing if any of the three is missing (no filling).
Excess vs own index = stock three-day sum - its index's three-day sum on the same sessions.
Luck test as sector_3day/sector_significance.py (excess over the same-quarter average of all results, 20,000
same-size random picks per quarter) but drawn WITHOUT replacement; Holm across the sectoral indices that have
F&O members. Reads LAB_ROOT/sector_lab/data and LISTS_DIR; writes index_* files in OUT
(default REPO_ROOT/results/nifty_sector_3day).
"""
import difflib
import os
import re
import numpy as np
import pandas as pd
from scipy import stats

LAB = os.environ.get('LAB_ROOT', 'lab')
LISTS = os.environ.get('LISTS_DIR', 'lists')
REPO = os.environ.get('REPO_ROOT', '.')
OUT = os.environ.get('OUT', os.path.join(REPO, 'results', 'nifty_sector_3day'))
os.makedirs(OUT, exist_ok=True)
D = f'{LAB}/sector_lab/data'
N_SIM = 20000
rng = np.random.default_rng(20261017)

# list file -> (index_close.csv column, short label for the markdown tables); NSE's own sectoral / thematic grouping
SECTORAL = {
    'niftyauto': ('Nifty Auto', 'Auto'),
    'niftybank': ('Nifty Bank', 'Bank'),
    'niftyfinance': ('Nifty Financial Services', 'Fin Serv'),
    'niftyfmcg': ('Nifty FMCG', 'FMCG'),
    'niftyhealthcare': ('Nifty Healthcare Index', 'Healthcare'),
    'niftyit': ('Nifty IT', 'IT'),
    'niftymedia': ('Nifty Media', 'Media'),
    'niftymetal': ('Nifty Metal', 'Metal'),
    'niftypharma': ('Nifty Pharma', 'Pharma'),
    'niftypsubank': ('Nifty PSU Bank', 'PSU Bank'),
    'nifty_privatebank': ('Nifty Private Bank', 'Pvt Bank'),
    'niftyrealty': ('Nifty Realty', 'Realty'),
    'niftyconsumerdurables': ('Nifty Consumer Durables', 'Cons Dur'),
    'niftyoilgas': ('Nifty Oil & Gas', 'Oil & Gas'),
}
THEMATIC = {
    'niftyenergy': ('Nifty Energy', 'Energy'),
    'niftyinfra': ('Nifty Infrastructure', 'Infra'),
    'niftycommodities': ('Nifty Commodities', 'Commodities'),
    'niftyconsumption': ('Nifty India Consumption', 'Consumption'),
    'niftymnc': ('Nifty MNC', 'MNC'),
    'niftypse': ('Nifty PSE', 'PSE'),
    'niftycpse': ('Nifty CPSE', 'CPSE'),
    'niftyservice': ('Nifty Services Sector', 'Services'),
}
GROUP = {v[0]: 'sectoral' for v in SECTORAL.values()} | {v[0]: 'thematic' for v in THEMATIC.values()}
SHORT = {v[0]: v[1] for v in (SECTORAL | THEMATIC).values()}
SEC = [v[0] for v in SECTORAL.values()]
THE = [v[0] for v in THEMATIC.values()]
ALL_IDX = SEC + THE
LIST_COLS = ['Company Name', 'Industry', 'Symbol', 'Series', 'ISIN Code']

log = []
P = lambda *a: log.append(' '.join(str(x) for x in a))

# ---------------------------------------------------------------- results and their windows
ev = pd.read_csv(f'{D}/events.csv')
ev = ev[ev.in_fo == True].copy().reset_index(drop=True)
assert np.allclose(ev.three_day, ev.ret_dm1 + ev.ret_rd + ev.ret_dp1, equal_nan=True)
assert ((ev.i_m1 == ev.i_cut + 1) & (ev.i_rd == ev.i_m1 + 1) & (ev.i_p1 == ev.i_rd + 1)).all()
ok = ev.three_day.notna()
P(f'F&O results: {len(ev)} rows, {ev.symbol.nunique()} symbols, {(~ok).sum()} without a three-day sum (dropped)')
ev = ev[ok].reset_index(drop=True)
ev['td'] = ev.three_day * 100
qlab = ev.groupby('qn').agg(period=('period', 'first'), quarter=('quarter', 'first'))
QS = list(qlab.index)
qmean = ev.groupby('qn').td.mean()
ev['ex_all'] = ev.td - ev.qn.map(qmean)
FO = set(ev.symbol)

ret = pd.read_csv(f'{D}/returns.csv', index_col=0)
ix = pd.read_csv(f'{D}/index_close.csv', index_col=0)
ses = pd.read_csv(f'{D}/sessions.csv')
assert (ret.index == ses.day).all() and (ix.index == ses.day).all(), 'returns / index_close / sessions rows differ'
R = ret.to_numpy(float)
col = {s: j for j, s in enumerate(ret.columns)}
W = ev[['i_m1', 'i_rd', 'i_p1']].to_numpy(int)
rs = np.array([np.nansum(R[w, col[s]]) for s, w in zip(ev.symbol, W)])
P(f'check three_day vs returns.csv: max abs diff {np.abs(rs - ev.three_day.to_numpy()).max():.2e}')
prev = os.path.join(REPO, 'results', 'sector_3day', 'results_3day.csv')
if os.path.exists(prev):
    pv = pd.read_csv(prev).merge(ev[['symbol', 'qn', 'three_day']], on=['symbol', 'qn'], how='outer', indicator=True)
    P(f'check vs $REPO_ROOT/results/sector_3day/results_3day.csv: {(pv._merge == "both").sum()} matched, '
      f'{(pv._merge != "both").sum()} unmatched, max abs diff {(pv.three_day_x - pv.three_day_y).abs().max():.2e}')


def idx_ret(name):
    c = ix[name].to_numpy(float)
    return np.r_[np.nan, c[1:] / c[:-1] - 1]


def three(name):  # index three-day sum (%) on every result's sessions i_m1, i_rd, i_p1; NaN if any day is missing
    return idx_ret(name)[W].sum(axis=1) * 100


lo, hi = int(ev.i_m1.min()) - 1, int(ev.i_p1.max())
P(f'result windows span sessions {lo}..{hi} ({ix.index[lo]} .. {ix.index[hi]})')
for name in ALL_IDX + ['Nifty 50']:
    miss = ix[name].iloc[lo:hi + 1]
    miss = miss[miss.isna()]
    if len(miss):
        P(f'  {name}: {len(miss)} missing closes inside the windows span: {", ".join(miss.index)}')
ev['nifty3'] = three('Nifty 50')

# ---------------------------------------------------------------- index lists
n500 = pd.read_csv(os.path.join(LISTS, 'ind_nifty500list.csv'))
assert list(n500.columns) == LIST_COLS, n500.columns
n500['Symbol'] = n500.Symbol.astype(str).str.strip()
nse_sector = n500.set_index('Symbol').Industry
isin = n500.set_index('Symbol')['ISIN Code']
missing500 = sorted(FO - set(n500.Symbol))
assert not missing500, f'F&O symbols not in the Nifty 500 list: {missing500}'
ev['nse_sector'] = ev.symbol.map(nse_sector)
comp = ev.groupby('symbol').company.first()
res_n = ev.groupby('symbol').size()

mem_rows, members = [], {}
for f, (name, _) in (SECTORAL | THEMATIC).items():
    d = pd.read_csv(os.path.join(LISTS, f'ind_{f}list.csv'))
    assert list(d.columns) == LIST_COLS, (f, d.columns)
    d['Symbol'] = d.Symbol.astype(str).str.strip()
    assert d.Symbol.is_unique, f
    members[name] = sorted(set(d.Symbol) & FO)
    for _, x in d.iterrows():
        mem_rows.append(dict(index=name, group=GROUP[name], symbol=x.Symbol, in_fo_results=x.Symbol in FO,
                             company=x['Company Name'], nse_sector=x.Industry, results=int(res_n.get(x.Symbol, 0)),
                             list_file=f'ind_{f}list.csv', isin=x['ISIN Code']))
mem = pd.DataFrame(mem_rows)
mem.to_csv(f'{OUT}/index_members.csv', index=False)

P('\n== index lists vs the F&O universe (returns.csv columns)')
P(f'{len(ALL_IDX)} index lists, {len(mem)} memberships, {mem.symbol.nunique()} distinct symbols; '
  f'{mem.in_fo_results.sum()} memberships are F&O symbols')
for name in ALL_IDX:
    m = mem[mem['index'] == name]
    out = m[~m.in_fo_results]
    in_ret = [s for s in out.symbol if s in col]
    P(f'  {name:26s} {GROUP[name]:8s} list {len(m):3d}  F&O {len(members[name]):3d}  not F&O {len(out):3d}'
      + (f'  [{", ".join(out.symbol)}]' if len(out) else '')
      + (f'  (in returns.csv but not in F&O results: {", ".join(in_ret)})' if in_ret else ''))


def norm(s):
    s = re.sub(r'\b(limited|ltd|the|india|of|and|co|company|corporation|corp)\b', ' ', str(s).lower().replace('&', ' and '))
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


fo_isin = {isin[s]: s for s in FO}
fo_name = {s: norm(n500.set_index('Symbol').loc[s, 'Company Name']) for s in FO} | {s + ' (events)': norm(comp[s]) for s in FO}
P('\n== possible symbol renames (non-F&O list member with an F&O ISIN or a near-identical company name)')
nf = mem[~mem.in_fo_results].drop_duplicates('symbol')
flag = 0
for _, x in nf.iterrows():
    hit_isin = fo_isin.get(x['isin'])
    nn = norm(x.company)
    best = max(fo_name.items(), key=lambda kv: difflib.SequenceMatcher(None, nn, kv[1]).ratio())
    r = difflib.SequenceMatcher(None, nn, best[1]).ratio()
    same_first = nn.split()[:1] == best[1].split()[:1]
    if hit_isin or (r >= 0.8 and same_first):
        flag += 1
        P(f'  FLAG {x.symbol} ({x.company}): same ISIN as {hit_isin}' if hit_isin else
          f'  FLAG {x.symbol} ({x.company}): name close to {best[0]} ({best[1]}), ratio {r:.2f}')
    elif r >= 0.8:
        P(f'  lookalike only (different first word, different company): {x.symbol} ({nn}) ~ {best[0]} ({best[1]}), ratio {r:.2f}')
P(f'  {flag} flagged of {len(nf)} non-F&O list members (rule: same ISIN, or name ratio >= 0.8 with the same first word)'
  + (' -> no rename mismatch' if flag == 0 else ''))
bad = [s for s in FO if difflib.SequenceMatcher(None, norm(comp[s]),
                                               norm(n500.set_index('Symbol').loc[s, 'Company Name'])).ratio() < 0.6]
P('F&O symbols whose events.csv company name differs from the Nifty 500 list name (ratio < 0.6): '
  + (', '.join(f'{s} ({comp[s]} / {n500.set_index("Symbol").loc[s, "Company Name"]})' for s in sorted(bad)) or 'none'))

# membership matrix for the 206 F&O symbols
mat = pd.DataFrame(0, index=sorted(FO), columns=ALL_IDX)
for name in ALL_IDX:
    mat.loc[members[name], name] = 1
mat.insert(0, 'nse_sector', mat.index.map(nse_sector))
mat.insert(1, 'company', mat.index.map(comp))
mat['n_sectoral'] = mat[SEC].sum(axis=1)
mat['n_thematic'] = mat[THE].sum(axis=1)
mat.index.name = 'symbol'
mat.to_csv(f'{OUT}/index_membership_matrix.csv')
none = mat[mat.n_sectoral == 0]
none_out = none[['company', 'nse_sector', 'n_thematic']].assign(
    thematic=[', '.join(SHORT[c] for c in THE if none.loc[s, c]) for s in none.index],
    results=none.index.map(res_n))
none_out.to_csv(f'{OUT}/index_no_sectoral.csv')
P(f'\n== F&O stocks in no sectoral index: {len(none)} of {len(mat)} '
  f'({int(res_n.reindex(none.index).sum())} of {len(ev)} results); in none of the 22 indices: {((mat.n_sectoral + mat.n_thematic) == 0).sum()}')
P('by NSE sector: ' + ', '.join(f'{k} {v}' for k, v in none.nse_sector.value_counts().items()))
for s, r in none_out.iterrows():
    P(f'  {s:12s} {r.nse_sector:34s} thematic: {r.thematic or "-"}')
P('F&O stocks by number of sectoral indices: ' + ', '.join(f'{k}: {v}' for k, v in mat.n_sectoral.value_counts().sort_index().items()))

# ---------------------------------------------------------------- member results with the index's own move
I3 = {name: three(name) for name in ALL_IDX}
parts = []
for name in ALL_IDX:
    msk = ev.symbol.isin(members[name]).to_numpy()
    g = ev.loc[msk, ['symbol', 'qn', 'period', 'quarter', 'td', 'ex_all', 'nse_sector', 'sector_index', 'sector_3d']].copy()
    g.insert(0, 'index', name)
    g['idx3'] = I3[name][msk]
    g['exc'] = g.td - g.idx3
    parts.append(g)
mr = pd.concat(parts, ignore_index=True)
(mr.assign(group=mr['index'].map(GROUP), three_day=mr.td / 100, index_three_day=mr.idx3 / 100,
           excess_vs_index=mr.exc / 100)
 [['index', 'group', 'symbol', 'qn', 'period', 'quarter', 'nse_sector', 'three_day', 'index_three_day', 'excess_vs_index']]
 .round(8).to_csv(f'{OUT}/index_member_results.csv', index=False))

# ---------------------------------------------------------------- quarter tables (sectoral indices)
allq = ev.groupby('qn').td.agg(['mean', 'size'])
piv = lambda v, f: mr.pivot_table(index='qn', columns='index', values=v, aggfunc=f).reindex(index=QS, columns=SEC)
avg, own, exc = piv('td', 'mean'), piv('idx3', 'mean'), piv('exc', 'mean')
cnt = piv('td', 'size').fillna(0).astype(int)
cnt_i = mr.dropna(subset=['idx3']).pivot_table(index='qn', columns='index', values='idx3', aggfunc='size') \
    .reindex(index=QS, columns=SEC).fillna(0).astype(int)
nif_q = ev.groupby('qn').nifty3.mean()
exn_q = (ev.td - ev.nifty3).groupby(ev.qn).mean()


def with_labels(df):
    d = df.copy()
    d.insert(0, 'quarter', qlab.quarter)
    d.insert(0, 'period', qlab.period)
    return d


with_labels(avg.assign(all_results=allq['mean'])).round(3).to_csv(f'{OUT}/index_avg_by_quarter.csv')
with_labels(cnt.assign(all_results=allq['size'])).to_csv(f'{OUT}/index_count_by_quarter.csv')
with_labels(own.assign(nifty50_all_results=nif_q)).round(3).to_csv(f'{OUT}/index_own_by_quarter.csv')
with_labels(exc.assign(all_results_vs_nifty50=exn_q)).round(3).to_csv(f'{OUT}/index_excess_by_quarter.csv')


def md(df, n, fmt, allcol, alln, alllab):
    hdr = ['Results for', 'Quarter'] + [SHORT[s] for s in SEC] + [alllab]
    out = ['| ' + ' | '.join(hdr) + ' |', '|---|---|' + '---:|' * (len(SEC) + 1)]
    for q in QS:
        cells = [qlab.period[q], qlab.quarter[q]] + [fmt(df.loc[q, s], n.loc[q, s]) for s in SEC] + [fmt(allcol[q], alln[q])]
        out.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(out) + '\n'


f_avg = lambda v, n: '-' if n == 0 or pd.isna(v) else f'{v:+.2f}'
f_cnt = lambda v, n: f'{int(n)}'
open(f'{OUT}/index_table_avg.md', 'w').write(md(avg, cnt, f_avg, allq['mean'], allq['size'], 'All'))
open(f'{OUT}/index_table_count.md', 'w').write(md(cnt, cnt, f_cnt, allq['size'], allq['size'], 'All'))
open(f'{OUT}/index_table_own.md', 'w').write(md(own, cnt_i, f_avg, nif_q, allq['size'], 'Nifty 50 (all)'))
open(f'{OUT}/index_table_excess.md', 'w').write(md(exc, cnt_i, f_avg, exn_q, allq['size'], 'All vs Nifty 50'))

# ---------------------------------------------------------------- summary, luck test, quarter t-test
by_q = {q: g.ex_all.to_numpy() for q, g in ev.groupby('qn')}


def luck(g):
    """Two-sided luck p of the group's average excess over the same-quarter all-results average; draws without replacement."""
    sims = np.zeros(N_SIM)
    for q, k in g.groupby('qn').size().items():
        pool = by_q[q]
        pick = rng.random((N_SIM, len(pool))).argpartition(k - 1, axis=1)[:, :k]
        sims += pool[pick].sum(axis=1)
    sims /= len(g)
    obs = g.ex_all.mean()
    return obs, (1 + (np.abs(sims) >= abs(obs) - 1e-12).sum()) / (N_SIM + 1)


def qt(x):
    x = x.dropna()
    if len(x) < 3:
        return np.nan, np.nan
    t = x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))
    return t, 2 * stats.t.sf(abs(t), len(x) - 1)


per = lambda qa, q: f'{qlab.period[q]} ({qa[q]:+.2f}%)'
rows = []
for name in ALL_IDX:
    g = mr[mr['index'] == name]
    r = dict(index=name, group=GROUP[name], fo_members=len(members[name]), results=len(g))
    if len(g):
        qa, qe = g.groupby('qn').td.mean(), g.groupby('qn').exc.mean().dropna()
        gi = g.dropna(subset=['idx3'])
        ex_all, p = luck(g)
        t, tp = qt(qe)
        ta, tap = qt(g.groupby('qn').ex_all.mean())
        r |= dict(stocks_with_results=g.symbol.nunique(), avg_stock=g.td.mean(), median_stock=g.td.median(),
                  avg_index=gi.idx3.mean(), avg_excess=gi.exc.mean(), index_missing=int(g.idx3.isna().sum()),
                  up_pct=(g.td > 0).mean() * 100, beat_index_pct=(gi.exc > 0).mean() * 100,
                  q_with=len(qa), q_pos=int((qa > 0).sum()), q_with_ex=len(qe), q_pos_ex=int((qe > 0).sum()),
                  first14=g[g.qn <= 13].td.mean(), last8=g[g.qn >= 14].td.mean(),
                  ex_first14=gi[gi.qn <= 13].exc.mean(), ex_last8=gi[gi.qn >= 14].exc.mean(),
                  best_q=per(qa, qa.idxmax()), worst_q=per(qa, qa.idxmin()),
                  excess_vs_all=ex_all, luck_p=p, t_excess_index=t, p_t_excess_index=tp,
                  t_excess_all=ta, p_t_excess_all=tap)
    rows.append(r)
summ = pd.DataFrame(rows)
tested = summ[(summ.group == 'sectoral') & summ.luck_p.notna()].sort_values('luck_p')
m = len(tested)
holm = lambda ps: np.minimum(1, np.maximum.accumulate([(len(ps) - i) * p for i, p in enumerate(ps)]))
summ.loc[tested.index, 'holm_p'] = holm(tested.luck_p)
for grp in ['sectoral', 'thematic']:  # extra: Holm of the quarter t-test p, within each group
    tt = summ[(summ.group == grp) & summ.p_t_excess_index.notna()].sort_values('p_t_excess_index')
    summ.loc[tt.index, 'holm_p_t_excess_index'] = holm(tt.p_t_excess_index)
g = ev
qa, qe = g.groupby('qn').td.mean(), (g.td - g.nifty3).groupby(g.qn).mean()
t, tp = qt(qe)
summ.loc[len(summ)] = dict(index='All F&O results (vs Nifty 50)', group='all', fo_members=g.symbol.nunique(), results=len(g),
                           stocks_with_results=g.symbol.nunique(), avg_stock=g.td.mean(), median_stock=g.td.median(),
                           avg_index=g.nifty3.mean(), avg_excess=(g.td - g.nifty3).mean(), index_missing=int(g.nifty3.isna().sum()),
                           up_pct=(g.td > 0).mean() * 100, beat_index_pct=(g.td > g.nifty3).mean() * 100,
                           q_with=len(qa), q_pos=int((qa > 0).sum()), q_with_ex=len(qe), q_pos_ex=int((qe > 0).sum()),
                           first14=g[g.qn <= 13].td.mean(), last8=g[g.qn >= 14].td.mean(),
                           ex_first14=(g.td - g.nifty3)[g.qn <= 13].mean(), ex_last8=(g.td - g.nifty3)[g.qn >= 14].mean(),
                           best_q=per(qa, qa.idxmax()), worst_q=per(qa, qa.idxmin()), excess_vs_all=0.0,
                           t_excess_index=t, p_t_excess_index=tp)
INTS = ['stocks_with_results', 'index_missing', 'q_with', 'q_pos', 'q_with_ex', 'q_pos_ex']
summ[INTS] = summ[INTS].astype('Int64')
summ.round(4).to_csv(f'{OUT}/index_summary.csv', index=False)

pf = lambda p: '-' if pd.isna(p) else ('<0.001' if p < 0.001 else f'{p:.3f}')
s_md = ['| Index | Group | F&O members | Results | Avg stock 3-day | Avg index 3-day | Excess vs own index | t (quarters) | p (t) '
        '| Quarters stock > 0 | Quarters excess > 0 | First 14 q / last 8 q stock | First 14 q / last 8 q excess '
        '| Best quarter | Worst quarter | Excess vs all results | Luck p | Holm p |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---:|---:|---:|']
for _, r in summ.iterrows():
    if r.results == 0:
        s_md.append(f'| {r["index"]} | {r.group} | 0 | 0 |' + ' - |' * 14)
        continue
    star = '*' if r.index_missing else ''
    s_md.append(f'| {r["index"]} | {r.group} | {r.fo_members} | {r.results:,} | {r.avg_stock:+.2f}% | {r.avg_index:+.2f}%{star} | '
                f'{r.avg_excess:+.2f}%{star} | {r.t_excess_index:+.2f} | {pf(r.p_t_excess_index)} | {r.q_pos} of {r.q_with} | '
                f'{r.q_pos_ex} of {r.q_with_ex} | {r.first14:+.2f}% / {r.last8:+.2f}% | {r.ex_first14:+.2f}% / {r.ex_last8:+.2f}% | '
                f'{r.best_q} | {r.worst_q} | ' + ('-' if r.group == 'all' else f'{r.excess_vs_all:+.2f}%') +
                f' | {pf(r.luck_p)} | {pf(r.holm_p)} |')
hc = summ.set_index('index').index_missing.fillna(0).astype(int)
s_md.append('')
s_md.append('Stock and index three-day sums are Day-1 + Result day + Day+1 daily returns (summed). Excess vs own index = stock '
            'minus its index over the same three sessions; t (quarters) = mean of the quarterly average excesses / its '
            'standard error, two-sided p. Luck p: members\' average excess over the same-quarter average of all F&O results, '
            f'vs {N_SIM:,} same-size random picks per quarter (without replacement); Holm across the {m} sectoral indices '
            'with F&O members (Nifty Media has none); thematic luck p are unadjusted. '
            + ('* index move missing for ' + ', '.join(f'{int(v)} result(s) of {k}' for k, v in hc.items() if v > 0)
               + ' (missing index closes); those results are left out of the index and excess columns. ' if hc.sum() else '')
            + 'Members are today\'s index constituents (look-ahead / survivorship caveat, as for the F&O universe).')
open(f'{OUT}/index_table_summary.md', 'w').write('\n'.join(s_md) + '\n')

# ---------------------------------------------------------------- validation
P('\n== (1) index three-day sums vs events.csv sector_3d (older mapping), results whose sector_index is the same index')
for name in ALL_IDX:
    g = mr[(mr['index'] == name) & (mr.sector_index == name)].dropna(subset=['idx3'])
    if len(g) == 0:
        continue
    rows_i = ev.set_index(['symbol', 'qn']).loc[g.set_index(['symbol', 'qn']).index]
    c = ix[name].to_numpy(float)
    comp3 = (c[rows_i.i_p1.to_numpy(int)] / c[rows_i.i_cut.to_numpy(int)] - 1) * 100
    P(f'  {name:26s} {len(g):4d} results  max |sum - sector_3d| {np.abs(g.idx3 - g.sector_3d * 100).max() / 100:.2e}  '
      f'(compounded vs sector_3d {np.abs(comp3 - g.sector_3d.to_numpy() * 100).max() / 100:.2e})')
sx = ev[ev.sector_index.isin(ix.columns)]
allchk = np.array([idx_ret(n)[w].sum() for n, w in zip(sx.sector_index, sx[['i_m1', 'i_rd', 'i_p1']].to_numpy(int))])
P(f'  all {len(sx)} results, own sector_index recomputed as a sum: max abs diff {np.nanmax(np.abs(allchk - sx.sector_3d)):.2e} '
  f'({np.isnan(allchk).sum()} NaN) -> sector_3d is the summed three-day move, same definition as here')
P('  overlap of the old sector_index with the new membership (member results whose sector_index is that index): '
  + ', '.join(f'{SHORT[n]} {int(((mr["index"] == n) & (mr.sector_index == n)).sum())}/{int((mr["index"] == n).sum())}'
              for n in ALL_IDX if (mr['index'] == n).any()))
P('\n== (2) Nifty 50 three-day sum vs events.csv nifty_3d')
d2 = np.abs(ev.nifty3 / 100 - ev.nifty_3d)
P(f'  {ev.nifty3.notna().sum()} results, max abs diff {d2.max():.2e}, NaN {ev.nifty3.isna().sum()}')
P('\n== (3) missing index moves (any of the three index returns NaN)')
for name in ALL_IDX:
    g = mr[mr['index'] == name]
    if g.idx3.isna().any():
        P(f'  {name}: {int(g.idx3.isna().sum())} of {len(g)} member results: '
          + ', '.join(f'{s} {qlab.period[q]}' for s, q in zip(g[g.idx3.isna()].symbol, g[g.idx3.isna()].qn)))
P(f'  all other indices and Nifty 50: 0 missing; total missing memberships {int(mr.idx3.isna().sum())} of {len(mr)}')
P(f'\nluck test: {N_SIM:,} draws per index, numpy seed 20261017, without replacement; Holm across {m} sectoral indices '
  '(holm_p); thematic luck p unadjusted. index_summary.csv also has holm_p_t_excess_index = Holm of the quarter t-test p '
  'within each group (13 sectoral, 8 thematic).')
open(f'{OUT}/index_validation.log', 'w').write('\n'.join(log) + '\n')
print('\n'.join(log))
print()
print(summ.drop(columns=['best_q', 'worst_q']).round(2).to_string())
