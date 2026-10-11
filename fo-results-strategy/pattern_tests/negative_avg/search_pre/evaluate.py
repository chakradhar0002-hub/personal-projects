"""Evaluate the 40 pre-registered candidates on DISCOVERY (qn 0..13) only. Holdout outcomes are never loaded."""
import hashlib, re, sys
import numpy as np, pandas as pd
SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = SP + '/negative_avg/search_pre'
EXPECTED = '26fd5881cc5091ae9f007f51410eaae363840c5f6b0e15a1bf3eb83da7d59a51'
raw = open(OUT + '/candidates.txt', 'rb').read()
if hashlib.sha256(raw).hexdigest() != EXPECTED:
    sys.exit('candidates.txt changed after registration - refusing to run')
cands = []
for line in raw.decode().splitlines():
    m = re.match(r'^(S\d\d) \| (.+?) \| (.+)$', line)
    if m:
        cands.append(m.groups())
assert len(cands) == 40

COST, COST_H = 0.17, 0.19
feat = pd.read_csv(OUT + '/features_cutoff.csv')

# ---- outcomes: DISCOVERY ONLY (filtered immediately on load) ----
oc = pd.read_csv(SP + '/perf/features/outcomes.csv', usecols=['symbol', 'qn', 'three_day'])
oc = oc[oc.qn <= 13].copy()
disc = feat[feat.qn <= 13].merge(oc, on=['symbol', 'qn'], how='left')
assert disc.qn.max() <= 13
disc = disc[disc.three_day.notna()].copy()

# Nifty 3-day (same 3 sessions i_cut+1..i_p1), discovery rows only
ic = pd.read_csv(SP + '/sector_lab/data/index_close.csv', usecols=['day', 'Nifty 50'])
nv = ic['Nifty 50'].values
nret = np.r_[np.nan, nv[1:] / nv[:-1] - 1] * 100
disc['nifty3'] = [nret[a + 1:b + 1].sum() for a, b in zip(disc.i_cut, disc.i_p1)]
assert (disc.i_p1 - disc.i_cut == 3).all()
# cross-check against fa_panel excess_nifty_3d (discovery rows only)
fa = pd.read_csv(SP + '/fa/build/fa_panel.csv', usecols=['symbol', 'qn', 'excess_nifty_3d', 'three_day'])
fa = fa[fa.qn <= 13]
chk = disc.merge(fa, on=['symbol', 'qn'], suffixes=('', '_fa'))
d_ex = (chk.three_day - chk.nifty3) - chk.excess_nifty_3d
print(f'check nifty3 vs fa_panel excess_nifty_3d: n {len(chk)}, |diff| > 0.01: {(d_ex.abs() > 0.01).sum()}, '
      f'three_day |diff| > 0.01: {((chk.three_day - chk.three_day_fa).abs() > 0.01).sum()}')

disc['short'] = -disc.three_day - COST
disc['short_h'] = -(disc.three_day - disc.nifty3) - COST_H
disc['half'] = np.where(disc.qn <= 6, 1, 2)
base_s, base_h = disc.short.mean(), disc.short_h.mean()
print(f'DISCOVERY base: n {len(disc)}, three_day {disc.three_day.mean():+.3f}, vs Nifty {(disc.three_day - disc.nifty3).mean():+.3f}, '
      f'base short {base_s:+.3f}, base hedged short {base_h:+.3f}')
for h in (1, 2):
    s = disc[disc.half == h]
    print(f'  half {h}: n {len(s)} base short {s.short.mean():+.3f} hedged {s.short_h.mean():+.3f}')

rng = np.random.default_rng(20261011)
NDRAW = 5000
pools = {q: g.three_day.values for q, g in disc.groupby('qn')}
def luck_p(sel):
    tot = np.zeros(NDRAW); n = 0
    for q, k in sel.groupby('qn').size().items():
        pool = pools[q]
        idx = np.argsort(rng.random((NDRAW, len(pool))), axis=1)[:, :k]
        tot += pool[idx].sum(axis=1); n += k
    obs = sel.three_day.mean()
    return (1 + (tot / n <= obs + 1e-12).sum()) / (1 + NDRAW)

def wo5(x):
    x = np.sort(np.asarray(x))[::-1]  # biggest short profits first
    return x[5:].mean() if len(x) > 5 else np.nan

rows = []
for cid, expr, desc in cands:
    m_all = feat.eval(expr, engine='python').fillna(False).astype(bool)
    n_hold_sig = int((m_all & (feat.qn >= 14)).sum())  # feature-only count
    m = disc.eval(expr, engine='python').fillna(False).astype(bool)
    s = disc[m]
    n = len(s)
    r = dict(id=cid, rule=expr, desc=desc, n=n, n_holdout_signals=n_hold_sig)
    if n == 0:
        rows.append(r); continue
    qs = s.groupby('qn').short.mean()
    qsh = s.groupby('qn').short_h.mean()
    r.update(
        avg_ret=s.three_day.mean(), avg_vsN=(s.three_day - s.nifty3).mean(),
        short=s.short.mean(), short_wo5=wo5(s.short), short_h=s.short_h.mean(), short_h_wo5=wo5(s.short_h),
        hit=(s.short > 0).mean() * 100,
        q_trades=len(qs), q_pos=int((qs > 0).sum()), q_pos_h=int((qsh > 0).sum()),
        n_h1=int((s.half == 1).sum()), short_h1=s[s.half == 1].short.mean(), n_h2=int((s.half == 2).sum()),
        short_h2=s[s.half == 2].short.mean(),
        hedged_h1=s[s.half == 1].short_h.mean(), hedged_h2=s[s.half == 2].short_h.mean(),
        luck_p=luck_p(s))
    rows.append(r)
res = pd.DataFrame(rows)
# Holm over the 40 luck p (candidates with trades)
p = res.luck_p.fillna(1.0).values
order = np.argsort(p); holm = np.empty_like(p); run = 0
for rank, i in enumerate(order):
    run = max(run, min(1.0, (len(p) - rank) * p[i])); holm[i] = run
res['holm_p'] = holm
res['beats_base'] = res.short - base_s
res['c1'] = (res.n >= 40) & (res.q_trades >= 7)
res['c2'] = (res.short_h1 > 0) & (res.short_h2 > 0)
res['c3'] = res.beats_base >= 0.5
res['qualifies'] = res.c1 & res.c2 & res.c3
res.to_csv(OUT + '/discovery_results.csv', index=False)

def f(x, d=2, sign=True):
    return '' if pd.isna(x) else (f'{x:+.{d}f}' if sign else f'{x:.{d}f}')
lines = ['| id | rule | n | avg ret | avg vs Nifty | short net | short net w/o 5 biggest falls | hedged short net | hedged w/o 5 | '
         'quarters short-profitable / with trades | H1 (qn 0-6) n, short | H2 (qn 7-13) n, short | luck p | Holm p | criteria 1/2/3 |',
         '|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---:|---:|---|']
for _, r in res.iterrows():
    if r.n == 0:
        lines.append(f'| {r.id} | {r.desc} | 0 | | | | | | | | | | | | n/n/n |'); continue
    lines.append(f'| {r.id} | {r.desc} | {r.n} | {f(r.avg_ret)} | {f(r.avg_vsN)} | {f(r.short)} | {f(r.short_wo5)} | '
                 f'{f(r.short_h)} | {f(r.short_h_wo5)} | {r.q_pos}/{r.q_trades} | {r.n_h1}, {f(r.short_h1)} | '
                 f'{r.n_h2}, {f(r.short_h2)} | {r.luck_p:.3f} | {r.holm_p:.2f} | '
                 f'{"y" if r.c1 else "n"}/{"y" if r.c2 else "n"}/{"y" if r.c3 else "n"} |')
hdr = (f'Discovery qn 0-13, {len(disc)} results. Base: avg three_day {disc.three_day.mean():+.2f}%, base short net '
       f'{base_s:+.2f}, base hedged short net {base_h:+.2f}. Criterion 3 needs short net >= {base_s + 0.5:+.2f}.\n\n')
open(OUT + '/discovery_table.md', 'w').write(hdr + '\n'.join(lines) + '\n')
print(hdr + '\n'.join(lines))

q = res[res.qualifies].sort_values('short_wo5', ascending=False)
print('\nQUALIFIERS (ranked by short net w/o 5 biggest falls):')
print(q[['id', 'desc', 'n', 'short', 'short_wo5', 'short_h1', 'short_h2', 'q_pos', 'q_trades']].to_string())
fin = q.head(2)
open(OUT + '/finalists.txt', 'w').write(fin[['id', 'rule', 'desc']].to_string(index=False) + '\n' if len(fin) else 'NONE\n')
for _, r in fin.iterrows():
    m = disc.eval(r.rule, engine='python').fillna(False).astype(bool)
    t = disc[m][['symbol', 'qn', 'quarter', 'cutoff', 'three_day', 'nifty3', 'short', 'short_h']].sort_values(['qn', 'symbol'])
    t.to_csv(OUT + f'/trades_{r.id}_discovery.csv', index=False)
    pq = t.groupby(['qn', 'quarter']).agg(n=('short', 'size'), avg_ret=('three_day', 'mean'), short=('short', 'mean'),
                                         short_h=('short_h', 'mean')).reset_index()
    pq.to_csv(OUT + f'/per_quarter_{r.id}_discovery.csv', index=False)
    print(f'\n{r.id} per quarter:\n', pq.round(2).to_string(index=False))
    print(' 5 biggest falls:', t.nsmallest(5, 'three_day')[['symbol', 'quarter', 'three_day']].round(2).values.tolist())
