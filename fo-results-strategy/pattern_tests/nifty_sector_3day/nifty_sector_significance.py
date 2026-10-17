#!/usr/bin/env python3
"""Is any NSE index sector's average three-day results move different from chance?

For each NSE Nifty index sector: excess = average over its results of (three-day sum - average three-day sum of all
3,278 F&O results of the same quarter). Luck p: 20,000 random draws; each draw picks, in every quarter, as many results
as the sector has that quarter, without replacement, from all F&O results of that quarter; p = (1 + number of draws
whose excess is at least as far from 0 as the sector's) / 20,001 (two-sided). Holm adjustment across the sectors with
at least MIN_HOLM results; smaller sectors are reported but left out of Holm. Also: quarters above the same-quarter
average, both halves (first 14 / last 8 quarters), without the best / worst 5 results, after costs (0.17) as a long
or a short. As a reference, the custom 'Auto & auto parts' group of the earlier study (NSE Auto + Ashok Leyland) is run
through the same test (not part of Holm).
Reads OUT/results_3day.csv written by nifty_sector_table.py; writes sector_significance.csv, table_significance.md
and appends its checks to run.log.
"""
import os
import numpy as np
import pandas as pd

OUT = os.environ.get('OUT', os.path.join(os.environ.get('REPO_ROOT', '.'), 'results', 'nifty_sector_3day'))
N_SIM = 20000
MIN_HOLM = 30
COST = 0.17
ev = pd.read_csv(f'{OUT}/results_3day.csv')
assert len(ev) == 3278
ev['td'] = ev.three_day * 100
rng = np.random.default_rng(20261017)
qmean = ev.groupby('qn').td.mean()
ev['ex'] = ev.td - ev.qn.map(qmean)
pools = {q: g.ex.to_numpy() for q, g in ev.groupby('qn')}     # same-quarter deviations of all results

log = []
def P(*a):
    s = ' '.join(str(x) for x in a)
    log.append(s)
    print(s)

def luck(g):
    """Two-sided luck p of the group's average excess: random same-size picks per quarter without replacement."""
    obs = g.ex.mean()
    sims = np.zeros(N_SIM)
    for q, k in g.groupby('qn').size().items():
        pool = pools[q]
        if k == len(pool):          # the whole quarter: excess sum is 0 in every draw
            continue
        keys = rng.random((N_SIM, len(pool)))
        idx = np.argpartition(keys, k - 1, axis=1)[:, :k]     # k distinct results per draw
        sims += pool[idx].sum(axis=1)
    sims /= len(g)
    return obs, (1 + (np.abs(sims) >= abs(obs) - 1e-12).sum()) / (N_SIM + 1), sims

def stats(name, g):
    obs, p, sims = luck(g)
    qa = g.groupby('qn').ex.mean()
    srt = np.sort(g.td.to_numpy())
    return dict(sector=name, stocks=g.symbol.nunique(), results=len(g), avg=g.td.mean(), excess=obs,
                q_above=int((qa > 0).sum()), q=len(qa),
                t_quarters=qa.mean() / (qa.std(ddof=1) / np.sqrt(len(qa))) if len(qa) > 1 else np.nan,
                ex_first14=g[g.qn <= 13].ex.mean(), ex_last8=g[g.qn >= 14].ex.mean(),
                avg_wo_best5=srt[:-5].mean(), avg_wo_worst5=srt[5:].mean(),
                long_net=g.td.mean() - COST, short_net=-g.td.mean() - COST, sim_sd=sims.std(), p=p)

P('\n== nifty_sector_significance.py ==')
P(f'luck test: {N_SIM:,} draws, same number of results per quarter, without replacement, two-sided; seed 20261017')
order = ev.nifty_sector.value_counts()
rows = [stats(s, ev[ev.nifty_sector == s]) for s in sorted(order.index, key=lambda s: (-order[s], s))]
r = pd.DataFrame(rows)
r['in_holm'] = r.results >= MIN_HOLM
t = r[r.in_holm].sort_values('p')
m = len(t)
r['holm'] = np.nan
r.loc[t.index, 'holm'] = np.maximum.accumulate([min(1, (m - i) * p) for i, p in enumerate(t.p)])
r = pd.concat([r[r.in_holm].sort_values(['p', 'results'], ascending=[True, False]),
               r[~r.in_holm]]).reset_index(drop=True)
assert np.isclose((ev.groupby('qn').ex.sum()).abs().max(), 0, atol=1e-9)
P(f'Holm across {m} sectors with at least {MIN_HOLM} results; not in Holm: '
  + (', '.join(f'{s.sector} ({s.results} results)' for _, s in r[~r.in_holm].iterrows()) or 'none'))
r.round(4).to_csv(f'{OUT}/sector_significance.csv', index=False)

# reference: the custom Auto group (NSE Auto + ASHOKLEY), same test, not in Holm
ca = stats('Auto & auto parts (custom, earlier study)', ev[ev.custom_sector == 'Auto & auto parts'])
na = ev[(ev.nifty_sector == 'Automobile and Auto Components')]
P(f"reference, custom Auto & auto parts: {ca['results']} results, avg {ca['avg']:+.2f}%, excess {ca['excess']:+.2f}, "
  f"quarters above {ca['q_above']} of {ca['q']}, luck p {ca['p']:.4f}")
al = ev[ev.symbol == 'ASHOKLEY']
P(f"Ashok Leyland (custom Auto, NSE Capital Goods): {len(al)} results, avg {al.td.mean():+.2f}%, excess {al.ex.mean():+.2f}")
P(f"NSE Auto without its best stock by total: "
  + (lambda b: f"{b}: avg {na[na.symbol != b].td.mean():+.2f}%, excess {na[na.symbol != b].ex.mean():+.2f}")(
      na.groupby('symbol').td.sum().idxmax()))

fp = lambda v: f'{v:.4f}' if v < 0.001 else f'{v:.3f}'
out = ['| Sector | Stocks | Results | Avg 3-day sum | Excess over same-quarter avg | Quarters above | '
       'Excess first 14 q / last 8 q | Luck p | Holm p |',
       '|---|---:|---:|---:|---:|---:|---|---:|---:|']
for _, s in r.iterrows():
    h = fp(s.holm) if s.in_holm else 'not tested (fewer than 30 results)'
    out.append(f'| {s.sector} | {s.stocks} | {s.results:,} | {s.avg:+.2f}% | {s.excess:+.2f} | {s.q_above} of {s.q} | '
               f'{s.ex_first14:+.2f} / {s.ex_last8:+.2f} | {fp(s.p)} | {h} |')
out += ['', f'Excess: average over the sector\'s results of (its three-day sum minus the average three-day sum of all 3,278 '
        'F&O results of the same quarter), in percentage points. Quarters above: quarters in which the sector\'s average '
        'beat the all-results average, of quarters with results. Luck p: share of 20,000 random draws (in every quarter '
        'the same number of results as the sector has, picked without replacement from all results of that quarter) whose '
        'excess is at least as far from 0 as the sector\'s, two-sided, (1 + count) / 20,001. Holm across the '
        f'{m} sectors with at least {MIN_HOLM} results; Textiles (one stock, Page Industries, 18 results) is reported '
        'but left out of Holm.',
        '', f"Reference, same test (not in Holm): the custom 'Auto & auto parts' group of the earlier study (NSE Auto + "
        f"Ashok Leyland), {ca['results']} results, avg {ca['avg']:+.2f}%, excess {ca['excess']:+.2f}, quarters above "
        f"{ca['q_above']} of {ca['q']}, luck p {fp(ca['p'])}."]
assert list(r[~r.in_holm].sector) == ['Textiles'], r[~r.in_holm].sector.tolist()
open(f'{OUT}/table_significance.md', 'w').write('\n'.join(out) + '\n')
P('\n' + r.drop(columns=['sim_sd']).round(3).to_string())
P('\nsignificant after Holm (< 0.05):', ', '.join(r[r.holm < 0.05].sector) or 'none')
P('luck p < 0.05 before Holm:', ', '.join(r[r.p < 0.05].sector) or 'none')

# append to run.log (replacing an earlier section of this script, so reruns do not duplicate it)
path = f'{OUT}/run.log'
prev = open(path).read() if os.path.exists(path) else ''
prev = prev.split('\n== nifty_sector_significance.py ==')[0].rstrip('\n')
open(path, 'w').write(prev + '\n' + '\n'.join(log) + '\n')
