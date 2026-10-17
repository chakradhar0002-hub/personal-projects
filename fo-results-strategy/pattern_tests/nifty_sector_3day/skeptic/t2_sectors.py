"""Claim 2: other sectors / indices that look strong or weak. Holm under several tests, one stock / one quarter,
thin cells, general drift (placebo), and the quarter-leaders table under a null."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

pd.set_option('display.width', 300)
pd.set_option('display.max_columns', 40)
pd.set_option('display.max_colwidth', 40)
ap = all_placebo()
print(f'all-F&O placebo windows: {len(ap)} ({ap.symbol.nunique()} stocks)')

groups = []
for s in sorted(ev.nifty_sector.unique()):
    groups.append(('NSE', s, ev[ev.nifty_sector == s]))
for s in SECTORAL.values():
    if MEM[s]:
        groups.append(('sectoral', s, ev[ev.symbol.isin(MEM[s])]))
for s in THEMATIC.values():
    groups.append(('thematic', s, ev[ev.symbol.isin(MEM[s])]))

PL = {}
rows = []
for fam, name, g in groups:
    o, p, sd = luck(g)
    t, tp, nq = qt(g)
    ct, cp, _ = cl2(g)
    sp = stock_perm(g.symbol.nunique(), o) if g.symbol.nunique() < 206 else np.nan
    cnt = g.groupby('qn').size()
    thin = cnt[cnt <= 3]
    # most influential stock / quarter (largest contribution in the direction of the excess)
    sgn = np.sign(o)
    cs = g.groupby('symbol').ex.sum() * sgn
    top_s = cs.idxmax()
    g1 = g[g.symbol != top_s]
    o1, p1, _ = luck(g1, n_sim=10000)
    cq = g.groupby('qn').ex.sum() * sgn
    top_q = cq.idxmax()
    g2 = g[g.qn != top_q]
    o2, p2, _ = luck(g2, n_sim=10000)
    # placebo (general drift of the same stocks in ordinary windows, time-matched)
    syms = sorted(set(g.symbol))
    gp = ap[ap.symbol.isin(syms) & ap.set_index(['symbol', 'qn']).index.isin(list(zip(g.symbol, g.qn)))]
    PL[(fam, name)] = gp
    pex = placebo_excess(g, gp)
    qm = ap.groupby('qn').td.mean()
    gp2 = gp.assign(ex=gp.td - gp.qn.map(qm))
    dm, dt, dp, _ = diff_q(g, gp2, 'ex')
    rows.append(dict(fam=fam, group=name, stocks=g.symbol.nunique(), n=len(g), avg=g.td.mean(), ex=o, luck_p=p,
                     q_t=t, q_p=tp, nq=nq, cl2_p=cp, stock_perm_p=sp, q_above=int((g.groupby('qn').ex.mean() > 0).sum()),
                     thin_q=len(thin), thin_res=int(thin.sum()),
                     top_stock=top_s, top_stock_n=int((g.symbol == top_s).sum()), ex_wo_top_stock=o1, p_wo_top_stock=p1,
                     top_q=int(top_q), top_q_n=int(cnt[top_q]), ex_wo_top_q=o2, p_wo_top_q=p2,
                     placebo_ex=pex, res_minus_plac=dm, rmp_p=dp))
T = pd.DataFrame(rows)
for fam, m in [('NSE', 30), ('sectoral', 30), ('thematic', 30)]:
    k = (T.fam == fam) & (T.n >= m)
    for c in ['luck_p', 'q_p', 'cl2_p', 'stock_perm_p']:
        T.loc[k, f'holm_{c}'] = holm(T.loc[k, c]).values
T.to_csv(os.path.join(SKOUT, 't2_groups.csv'), index=False)
show = ['fam', 'group', 'stocks', 'n', 'avg', 'ex', 'luck_p', 'holm_luck_p', 'q_p', 'holm_q_p', 'cl2_p', 'holm_cl2_p',
        'stock_perm_p', 'holm_stock_perm_p', 'q_above', 'nq', 'thin_q', 'thin_res']
print(T.sort_values(['fam', 'luck_p'])[show].round(4).to_string())
print()
show2 = ['fam', 'group', 'ex', 'top_stock', 'top_stock_n', 'ex_wo_top_stock', 'p_wo_top_stock', 'top_q', 'top_q_n',
         'ex_wo_top_q', 'p_wo_top_q', 'placebo_ex', 'res_minus_plac', 'rmp_p']
print(T.sort_values(['fam', 'luck_p'])[show2].round(4).to_string())

print('\n== per-stock detail for the flagged groups')
for name in ['Power', 'Telecommunication', 'Consumer Durables', 'Consumer Services', 'Capital Goods', 'Realty',
             'Financial Services', 'Services']:
    g = ev[ev.nifty_sector == name]
    d = g.groupby('symbol').agg(n=('ex', 'size'), avg=('td', 'mean'), ex=('ex', 'mean'), ex_sum=('ex', 'sum'))
    tot = g.ex.sum()
    d['share'] = d.ex_sum / tot
    print(f'-- {name}: ex {g.ex.mean():+.3f}, total ex-sum {tot:+.1f}')
    print(d.sort_values('ex_sum').round(3).to_string())
    print('   by quarter n:', ' '.join(f'{q}:{v}' for q, v in g.groupby('qn').size().items()))
    print('   by quarter ex:', ' '.join(f'{q}:{v:+.1f}' for q, v in g.groupby('qn').ex.mean().items()))
    h1, h2 = g[g.qn <= 13], g[g.qn >= 14]
    print(f'   halves: first14 n {len(h1)} ex {h1.ex.mean():+.2f} p {luck(h1, 10000)[1]:.3f}; '
          f'last8 n {len(h2)} ex {h2.ex.mean():+.2f} p {luck(h2, 10000)[1]:.3f}')

print('\n== pairwise: PSU Bank vs Private Bank, Healthcare vs Pharma, hospitals vs pharma')
def pair(a, b, la, lb):
    qa, qb = a.groupby('qn').ex.mean(), b.groupby('qn').ex.mean()
    d = (qa - qb).dropna()
    t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))
    pt = 2 * stats.t.sf(abs(t), len(d) - 1)
    # label permutation within quarter among the union (overlap removed)
    u = pd.concat([a.assign(L=1), b.assign(L=0)])
    obs = a.ex.mean() - b.ex.mean()
    rng = np.random.default_rng(5)
    sims = []
    for _ in range(5000):
        lab = u.groupby('qn').L.transform(lambda x: rng.permutation(x.to_numpy()))
        sims.append(u.ex[lab == 1].mean() - u.ex[lab == 0].mean())
    pp = (1 + (np.abs(sims) >= abs(obs)).sum()) / 5001
    print(f'  {la} (n {len(a)}, ex {a.ex.mean():+.3f}) vs {lb} (n {len(b)}, ex {b.ex.mean():+.3f}): diff {obs:+.3f}; '
          f'quarter-paired t {t:+.2f} p {pt:.3f} ({len(d)} q); within-quarter label permutation p {pp:.3f}')
psu, pvt = ev[ev.symbol.isin(MEM['Nifty PSU Bank'])], ev[ev.symbol.isin(MEM['Nifty Private Bank'])]
pair(psu, pvt, 'PSU Bank', 'Private Bank')
print('   PSU Bank by quarter ex:', ' '.join(f'{q}:{v:+.1f}' for q, v in psu.groupby('qn').ex.mean().items()))
print('   PSU Bank best/worst quarter contributions:', psu.groupby('qn').ex.sum().sort_values().iloc[[0, 1, -2, -1]].round(1).to_dict())
for lab, g in [('PSU Bank', psu), ('Private Bank', pvt)]:
    d = g.groupby('symbol').agg(n=('ex', 'size'), ex=('ex', 'mean'))
    print(f'   {lab} stocks:', ', '.join(f'{s} {r.ex:+.2f} ({r.n})' for s, r in d.iterrows()))
hc = ev[ev.nifty_sector == 'Healthcare']
print('   Healthcare industries:', hc.groupby('industry').symbol.unique().apply(list).to_dict())
hosp = hc[hc.industry.str.contains('Hospital|Healthcare Serv|Health Care Serv', case=False, na=False)]
ph = hc[~hc.index.isin(hosp.index)]
pair(hosp, ph, 'Healthcare: hospitals/services', 'Healthcare: pharma etc.')
nph = ev[ev.symbol.isin(MEM['Nifty Pharma'])]
nhc = ev[ev.symbol.isin(MEM['Nifty Healthcare Index'])]
print(f'   Nifty Pharma members {len(nph)} res ex {nph.ex.mean():+.3f}; Nifty Healthcare members {len(nhc)} ex '
      f'{nhc.ex.mean():+.3f}; overlap {len(set(MEM["Nifty Pharma"]) & set(MEM["Nifty Healthcare Index"]))} stocks; '
      f'Healthcare-only members: {sorted(set(MEM["Nifty Healthcare Index"]) - set(MEM["Nifty Pharma"]))}')

print('\n== thematic indices without the Auto names')
autos = set(ev[ev.nifty_sector == 'Automobile and Auto Components'].symbol) | {'ASHOKLEY'}
for s in THEMATIC.values():
    g = ev[ev.symbol.isin(MEM[s])]
    a = sorted(set(MEM[s]) & autos)
    if a:
        g2 = g[~g.symbol.isin(autos)]
        o, p, _ = luck(g2, 10000)
        print(f'  {s}: autos {a}; with autos n {len(g)} ex {g.ex.mean():+.3f}; without n {len(g2)} ex {o:+.3f} luck p {p:.3f} '
              f'q-t p {qt(g2)[1]:.3f}')

print('\n== quarter leaders under the null (results shuffled across sectors within each quarter, cell sizes kept)')
rng = np.random.default_rng(9)
sec = ev.nifty_sector.to_numpy()
best_cnt, worst_cnt = {}, {}
def leaders(lab):
    b, w = {}, {}
    for q, g in ev.assign(L=lab).groupby('qn'):
        m = g.groupby('L').td.agg(['mean', 'size'])
        m = m[m['size'] >= 4]
        b[m['mean'].idxmax()] = b.get(m['mean'].idxmax(), 0) + 1
        w[m['mean'].idxmin()] = w.get(m['mean'].idxmin(), 0) + 1
    return b, w
ob, ow = leaders(sec)
NS_ = 1000
sb = {s: [] for s in set(sec)}
sw = {s: [] for s in set(sec)}
qidx = [np.where(ev.qn.to_numpy() == q)[0] for q in QS]
for _ in range(NS_):
    lab = sec.copy()
    for ii in qidx:
        lab[ii] = sec[rng.permutation(ii)]
    b, w = leaders(lab)
    for s in sb:
        sb[s].append(b.get(s, 0))
        sw[s].append(w.get(s, 0))
L = pd.DataFrame({'best_obs': pd.Series(ob), 'best_null_mean': {s: np.mean(v) for s, v in sb.items()},
                  'p_best_ge_obs': {s: np.mean(np.array(v) >= ob.get(s, 0)) for s, v in sb.items()},
                  'worst_obs': pd.Series(ow), 'worst_null_mean': {s: np.mean(v) for s, v in sw.items()},
                  'p_worst_ge_obs': {s: np.mean(np.array(v) >= ow.get(s, 0)) for s, v in sw.items()}}).fillna(0)
L['median_cell'] = ev.groupby('nifty_sector').qn.value_counts().groupby(level=0).median()
print(L.sort_values('best_null_mean', ascending=False).round(3).to_string())
