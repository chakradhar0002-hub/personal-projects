"""Extra checks: hospitals vs pharma, thematic own-index excess without the Auto / Power names, cl2 diagnostics."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

ap = all_placebo()
hc = ev[ev.nifty_sector == 'Healthcare']
H = ['APOLLOHOSP', 'MAXHEALTH', 'FORTIS']
for lab, g in [('hospitals', hc[hc.symbol.isin(H)]), ('pharma (NSE Healthcare ex hospitals)', hc[~hc.symbol.isin(H)])]:
    o, p, _ = luck(g, 10000)
    print(f'{lab}: n {len(g)}, stocks {g.symbol.nunique()}, avg {g.td.mean():+.3f}, ex {o:+.3f}, luck p {p:.3f}, '
          f'q-t p {qt(g)[1]:.3f}')
a, b = hc[hc.symbol.isin(H)], hc[~hc.symbol.isin(H)]
d = (a.groupby('qn').ex.mean() - b.groupby('qn').ex.mean()).dropna()
print(f'  hospitals minus pharma quarterly: {d.mean():+.3f}, t {d.mean() / d.std(ddof=1) * np.sqrt(len(d)):+.2f}, '
      f'{len(d)} q; per stock:', a.groupby('symbol').ex.agg(['size', 'mean']).round(2).to_dict('index'))

autos = set(ev[ev.nifty_sector == 'Automobile and Auto Components'].symbol) | {'ASHOKLEY'}
power = set(ev[ev.nifty_sector == 'Power'].symbol)
print('\nthematic own-index excess (results vs placebo) after removing a block of names')
for name, drop, lab in [('Nifty India Consumption', autos, 'autos'), ('Nifty MNC', autos, 'autos'),
                        ('Nifty Infrastructure', autos, 'autos'), ('Nifty Commodities', power, 'Power-sector stocks'),
                        ('Nifty Energy', power, 'Power-sector stocks'), ('Nifty Commodities', set(), 'nothing')]:
    mem = MEM[name]
    keep = [s for s in mem if s not in drop]
    gr = bench(ev[ev.symbol.isin(keep)], name, mem)
    gp = bench(ap[ap.symbol.isin(keep)], name, mem)
    t, tp, _ = qt(gr, 'ab_idx')
    dm, dt, dp, _ = diff_q(gr, gp, 'ab_idx')
    print(f'  {name} without {lab} ({sorted(set(mem) & drop)}): n {len(gr)}, vs index {gr.ab_idx.mean():+.3f} (q-t p '
          f'{tp:.3f}); placebo {gp.ab_idx.mean():+.3f}; results-minus-placebo {dm:+.3f} p {dp:.3f}')
cm = ev[ev.symbol.isin(MEM['Nifty Commodities'])]
print('  Commodities members by NSE sector (n, ex vs all):',
      cm.groupby('nifty_sector').ex.agg(['size', 'mean']).round(2).to_dict('index'))

print('\ncl2 diagnostics (variance pieces of the mean): stock, quarter, cell')
for s in ['Automobile and Auto Components', 'Consumer Durables', 'Power', 'Telecommunication']:
    g = ev[ev.nifty_sector == s]
    x = g.ex.to_numpy(); n = len(x); e = x - x.mean()
    vs = (pd.Series(e).groupby(g.symbol.to_numpy()).sum() ** 2).sum() / n ** 2
    vq = (pd.Series(e).groupby(g.qn.to_numpy()).sum() ** 2).sum() / n ** 2
    vc = (e ** 2).sum() / n ** 2
    print(f'  {s}: se_stock {np.sqrt(vs):.3f}, se_quarter {np.sqrt(vq):.3f}, se_iid {np.sqrt(vc):.3f}, '
          f'luck sd {luck(g, 5000)[2]:.3f}; t with quarter-cluster only {x.mean() / np.sqrt(vq):+.2f}, '
          f'stock-cluster only {x.mean() / np.sqrt(vs):+.2f}')
