"""Claim 1: Auto stands out. Holm, drop top 3, halves / years, vs Nifty 50 / Nifty Auto / peers, classification."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

pd.set_option('display.width', 250)
pd.set_option('display.max_columns', 40)
AUTO = 'Automobile and Auto Components'
nse = ev[ev.nifty_sector == AUTO]
nfa = ev[ev.symbol.isin(MEM['Nifty Auto'])]
cus = ev[ev.custom_sector == 'Auto & auto parts']
inc = set(ev[ev.qn == 0].symbol)


def row(name, g, perm=False):
    o, p, sd = luck(g)
    t, tp, nq = qt(g)
    ct, cp, cse = cl2(g)
    d = dict(group=name, stocks=g.symbol.nunique(), n=len(g), avg=g.td.mean(), med=g.td.median(),
             up=(g.td > 0).mean() * 100, ex=o, luck_p=p, luck_sd=sd, q_t=t, q_p=tp, nq=nq, cl2_t=ct, cl2_p=cp,
             cl2_se=cse, deff=(cse / sd) ** 2)
    if perm:
        d['stock_perm_p'] = stock_perm(g.symbol.nunique(), o)
    return d


def top3(g, c='ex'):
    return list(g.groupby('symbol')[c].sum().sort_values(ascending=False).index[:3])

print('== (a) significance, three Auto definitions and variants (luck 20,000 draws seed 777; q = quarter t-test; '
      'cl2 = two-way stock x quarter clustered t; deff = (cl2 se / luck sd)^2)')
rows = [row('NSE Auto (Automobile and Auto Components)', nse, True), row('Nifty Auto members', nfa, True),
        row('custom Auto & auto parts', cus, True)]
t3n, t3f = top3(nse), top3(nfa)
t3n_td = top3(nse, 'td')
rows += [row(f'NSE Auto minus top 3 by excess ({",".join(t3n)})', nse[~nse.symbol.isin(t3n)]),
         row(f'Nifty Auto minus top 3 by excess ({",".join(t3f)})', nfa[~nfa.symbol.isin(t3f)]),
         row('Nifty Auto minus M&M, ASHOKLEY, TVSMOTOR', nfa[~nfa.symbol.isin(['M&M', 'ASHOKLEY', 'TVSMOTOR'])]),
         row(f'NSE Auto minus top 5 by excess', nse[~nse.symbol.isin(top3(nse) + list(
             nse.groupby('symbol').ex.sum().sort_values(ascending=False).index[3:5]))]),
         row('NSE Auto, only stocks in F&O since qn 0', nse[nse.symbol.isin(inc)]),
         row('NSE Auto, late F&O joiners', nse[~nse.symbol.isin(inc)]),
         row('NSE Auto ex HYUNDAI', nse[nse.symbol != 'HYUNDAI'])]
A = pd.DataFrame(rows)
print(A.round(4).to_string())
print('top 3 NSE Auto by total td:', t3n_td, ' by total excess:', t3n, '; Nifty Auto by excess:', t3f)

print('\nper-stock excess (NSE Auto + ASHOKLEY):')
ps = ev[ev.symbol.isin(set(nse.symbol) | {'ASHOKLEY'})].groupby('symbol').agg(
    n=('ex', 'size'), avg=('td', 'mean'), ex=('ex', 'mean'), ex_sum=('ex', 'sum'), med=('ex', 'median'))
print(ps.sort_values('ex_sum', ascending=False).round(3).to_string())
st = ps.loc[ps.index != 'ASHOKLEY']
tt = stats.ttest_1samp(st.ex, 0)
print(f'NSE Auto stock-level: {len(st)} stocks, mean of stock mean excess {st.ex.mean():+.3f}, t {tt.statistic:+.2f}, '
      f'p {tt.pvalue:.4f}; stocks with ex>0: {(st.ex > 0).sum()}; median stock excess {st.ex.median():+.3f}')
st2 = st[st.n >= 10]
tt = stats.ttest_1samp(st2.ex, 0)
print(f'  stocks with >=10 results: {len(st2)}, mean {st2.ex.mean():+.3f}, t {tt.statistic:+.2f}, p {tt.pvalue:.4f}')

# Holm of the quarter t-test p across the 17 NSE sectors with >= 30 results
qp = {}
for s, g in ev.groupby('nifty_sector'):
    if len(g) >= 30:
        qp[s] = qt(g)[1]
hq = holm(qp)
print(f'\nquarter t-test p for NSE Auto {qp[AUTO]:.4f}; Holm across {len(qp)} sectors: {hq[AUTO]:.4f}; '
      f'smallest 4: ' + ', '.join(f'{k} {v:.4f}' for k, v in sorted(qp.items(), key=lambda x: x[1])[:4]))
cp = {}
for s, g in ev.groupby('nifty_sector'):
    if len(g) >= 30:
        cp[s] = cl2(g)[1]
hc = holm(cp)
print(f'two-way clustered p for NSE Auto {cp[AUTO]:.4f}; Holm across 17: {hc[AUTO]:.4f}')
# bigger family: 17 NSE sectors + 13 sectoral + 8 thematic + 15 custom sectors (earlier study) = 53
print(f'Bonferroni over a 53-test study family (17 NSE + 13 sectoral + 8 thematic + 15 custom): NSE Auto luck p '
      f'{A.luck_p[0]:.4f} -> {min(1, 53 * A.luck_p[0]):.3f}; Nifty Auto {A.luck_p[1]:.4f} -> {min(1, 53 * A.luck_p[1]):.3f}; '
      f'NSE Auto quarter-t {qp[AUTO]:.4f} -> {min(1, 53 * qp[AUTO]):.3f}')

print('\n== (c) halves and results years (results_date calendar year)')
rows = []
for name, g in [('NSE Auto', nse), ('Nifty Auto', nfa), ('custom Auto', cus)]:
    for lab, h in [('first 14 q (qn 0-13)', g[g.qn <= 13]), ('last 8 q (qn 14-21)', g[g.qn >= 14])] + \
                  [(f'year {y}', g[g.year == y]) for y in sorted(g.year.unique())]:
        o, p, _ = luck(h)
        t, tp, nq = qt(h)
        rows.append(dict(group=name, part=lab, n=len(h), stocks=h.symbol.nunique(), avg=h.td.mean(), ex=o, luck_p=p,
                         q_t=t, q_p=tp, nq=nq, q_above=int((h.groupby('qn').ex.mean() > 0).sum())))
H = pd.DataFrame(rows)
print(H.round(4).to_string())
# last 8 quarters: is NSE Auto's last-8 excess different from its first-14 excess?
a, b = nse[nse.qn <= 13].groupby('qn').ex.mean(), nse[nse.qn >= 14].groupby('qn').ex.mean()
tt = stats.ttest_ind(a, b, equal_var=False)
print(f'NSE Auto first-14 vs last-8 quarterly excess: {a.mean():+.3f} vs {b.mean():+.3f}, Welch t {tt.statistic:+.2f} '
      f'p {tt.pvalue:.3f}')
print('NSE Auto quarterly excess:', ' '.join(f'{q}:{v:+.2f}' for q, v in nse.groupby('qn').ex.mean().items()))
print('NSE Auto quarterly counts:', ' '.join(f'{q}:{v}' for q, v in nse.groupby('qn').size().items()))

print('\n== day decomposition (excess of each day over the same-quarter all-results mean of that day, pp)')
for name, g in [('NSE Auto', nse), ('Nifty Auto', nfa)]:
    out = []
    for c in ['ret_dm1', 'ret_rd', 'ret_dp1']:
        m = ev.groupby('qn')[c].mean()
        out.append(f'{c} {((g[c] - g.qn.map(m)) * 100).mean():+.3f}')
    print(f'  {name}: ' + ', '.join(out))
    for tm, h in g.groupby('timing'):
        print(f'    timing {tm}: n {len(h)}, ex {h.ex.mean():+.3f}')

print('\n== (d) other benchmarks over the same 3 sessions, results vs ordinary placebo windows of the same stocks')
for name, g, peers in [('NSE Auto', nse, sorted(set(nse.symbol))), ('Nifty Auto', nfa, MEM['Nifty Auto'])]:
    gr = bench(g, 'Nifty Auto', peers)
    gp = bench(placebo(sorted(set(g.symbol))), 'Nifty Auto', peers)
    print(f'-- {name}: {len(gr)} results, {len(gp)} placebo windows ({gp.symbol.nunique()} stocks)')
    out = []
    for c, lab in [('td', 'raw 3-day sum'), ('ab_n50', 'minus Nifty 50'), ('ab_beta', 'minus beta x Nifty 50'),
                   ('ab_mm', 'market model (alpha+beta)'), ('ab_ewu', 'minus EW F&O universe'),
                   ('ab_idx', 'minus Nifty Auto index'), ('ab_peer', 'minus EW other members (clean)'),
                   ('idx', 'Nifty Auto index itself'), ('n50', 'Nifty 50 itself')]:
        x = gr[c].dropna()
        t, tp, _ = qt(gr, c)
        ct, cpp, _ = cl2(gr.dropna(subset=[c]), c)
        dm, dt, dp, nq = diff_q(gr, gp, c)
        out.append(dict(measure=lab, res_mean=x.mean(), q_t=t, q_p=tp, cl2_t=ct, cl2_p=cpp, placebo_mean=gp[c].mean(),
                        res_minus_placebo_q=dm, diff_t=dt, diff_p=dp))
    print(pd.DataFrame(out).round(4).to_string())
    print(f'   placebo time-matched excess over all-F&O placebo windows: {placebo_excess(gr, gp):+.3f} '
          f'(results excess {g.ex.mean():+.3f})')
    # beat-the-index share and stock breadth
    b = gr.groupby('symbol').ab_idx.mean()
    print(f'   stocks beating Nifty Auto on average: {(b > 0).sum()} of {len(b)}; median stock {b.median():+.3f}')

print('\n== (e) classification: what differs between the three Auto groups')
sn, sf, sc = set(nse.symbol), set(nfa.symbol), set(cus.symbol)
print('custom - NSE:', sorted(sc - sn), ' NSE - custom:', sorted(sn - sc))
print('Nifty Auto - NSE:', sorted(sf - sn), ' NSE - Nifty Auto:', sorted(sn - sf))
shared = len(nse.merge(cus, on=['symbol', 'qn'])), len(nse.merge(nfa, on=['symbol', 'qn']))
print(f'shared results: NSE&custom {shared[0]} of {len(nse)}/{len(cus)}; NSE&NiftyAuto {shared[1]} of {len(nse)}/{len(nfa)}')
al = ev[ev.symbol == 'ASHOKLEY']
print(f'ASHOKLEY: {len(al)} results, avg {al.td.mean():+.2f}, ex {al.ex.mean():+.2f}')
cg = ev[ev.nifty_sector == 'Capital Goods']
for lab, g in [('Capital Goods', cg), ('Capital Goods ex ASHOKLEY', cg[cg.symbol != 'ASHOKLEY'])]:
    o, p, _ = luck(g)
    print(f'  {lab}: n {len(g)}, avg {g.td.mean():+.2f}, ex {o:+.2f}, luck p {p:.4f}, q-t p {qt(g)[1]:.4f}')
ind = ev.groupby('symbol').agg(industry=('industry', 'first'), sector=('nifty_sector', 'first'), n=('ex', 'size'),
                               ex=('ex', 'mean'))
autoish = ind[ind.industry.str.contains('Auto|Tyre|Tire|Batter|Tractor|Commercial Veh|wheel', case=False, na=False)]
print('stocks with an auto-like old NSE industry:')
print(autoish.round(3).to_string())
print('auto-like industry stocks outside NSE Auto:', autoish[autoish.sector != AUTO].index.tolist())
n500a = n500[n500.Industry == AUTO].Symbol.tolist()
print(f'Nifty 500 NSE Auto sector: {len(n500a)} stocks, {len(set(n500a) & set(ev.symbol))} in the F&O study; '
      f'not in the study: {sorted(set(n500a) - set(ev.symbol))}')
miss_ret = [s for s in n500a if s not in col]
print(f'  of those, without any returns in returns.csv: {len(miss_ret)}')
A.to_csv(os.path.join(SKOUT, 't1_groups.csv'), index=False)
H.to_csv(os.path.join(SKOUT, 't1_halves_years.csv'), index=False)
