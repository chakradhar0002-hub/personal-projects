"""Skeptic checks of the stock-level claims: last-quarter top / bottom fifth as a trade, the last-4 track record
(PAST_PERFORMANCE.md rebuild): threshold sweep, halves, leave-one-quarter / one-stock out, stock concentration,
quarter-clustered test, precise permutation p, costs."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from scipy import stats
from sk_common import *
HERE = SKOUT
ev, allev, qq = load()
Qv = qq.Q.to_numpy()
rng = np.random.default_rng(20261102)

def perm_null(df, mask, B=200000, CH=5000):
    """random picks within quarter among df rows: shuffle x within quarter, mean over mask positions"""
    df = df.reset_index(drop=True)
    o = np.argsort(df.qn.to_numpy(), kind='stable')
    xq, qn = df.x.to_numpy()[o], df.qn.to_numpy()[o].astype(float)
    mk = mask[o]
    out = np.empty(B)
    for b0 in range(0, B, CH):
        m = min(CH, B - b0)
        perm = np.argsort(qn[None] + rng.random((m, len(xq))), axis=1)
        out[b0:b0 + m] = xq[perm][:, mk].mean(1)
    return out

def describe(name, sel, base, B=200000):
    s = base[sel]
    null = perm_null(base, sel, B)
    p = p2c(s.x.mean(), null)
    qt = s.groupby('qn').agg(td=('td', 'mean'), x=('x', 'mean'), n=('td', 'size'))
    tq = stats.ttest_1samp(qt.x, 0)
    A, Bh = s[s.qn <= 10], s[s.qn >= 11]
    # one-quarter-out and one-stock-out extremes of the mean x
    lq = [s[s.qn != q].x.mean() for q in qt.index]
    st = s.groupby('symbol').x.agg(['sum', 'size']).sort_values('sum', ascending=False)
    ls = [(s.x.sum() - r['sum']) / (len(s) - r['size']) for _, r in st.iterrows()]
    top5 = st.head(5)
    print(f'{name}: {len(s)} results, {s.symbol.nunique()} stocks, {len(qt)} quarters; avg three-day {fp(s.td.mean())}% '
          f'(net of {COST:.2f}: {fp(s.td.mean() - COST)}%), all F&O same quarters {fp(base[base.qn.isin(qt.index)].td.mean())}%; '
          f'excess x {fp(s.x.mean())}; random-pick null {fp(null.mean())} sd {null.std():.3f}; p {fpv(p)} (B {B:,})')
    print(f'   per quarter: avg three-day {fp(qt.td.mean())}%, x {fp(qt.x.mean())}; quarters with x > 0: {int((qt.x > 0).sum())} of {len(qt)}; '
          f'quarters with net three-day > 0: {int((qt.td - COST > 0).sum())}; quarter-clustered t {tq.statistic:.2f}, p {fpv(tq.pvalue)}')
    print(f'   halves: q0-10 {len(A)} results x {fp(A.x.mean())} td {fp(A.td.mean())}%; q11-21 {len(Bh)} results x {fp(Bh.x.mean())} td {fp(Bh.td.mean())}%')
    print(f'   leave-one-quarter-out x: {fp(min(lq))} to {fp(max(lq))}; leave-one-stock-out x: {fp(min(ls))} to {fp(max(ls))}')
    print(f'   top 5 stocks by summed x: ' + ', '.join(f'{k} ({int(r["size"])} trades, sum {r["sum"]:+.1f})' for k, r in top5.iterrows())
          + f'; they give {100 * top5["sum"].sum() / s.x.sum():.0f}% of the summed excess with {100 * top5["size"].sum() / len(s):.0f}% of trades')
    s_ = s.copy(); s_['rep'] = s_.groupby('symbol').td.transform('size')
    one = s_[s_.rep == 1]
    print(f'   stocks picked 4+ times: {int((st["size"] >= 4).sum())}, their trades {int(st[st["size"] >= 4]["size"].sum())}; '
          f'x of stocks picked once: {fp(one.x.mean())} ({len(one)})')
    return dict(rule=name, results=len(s), stocks=s.symbol.nunique(), quarters=len(qt), avg_td=s.td.mean(),
                net=s.td.mean() - COST, excess=s.x.mean(), p=p, q_x=qt.x.mean(), q_pos=int((qt.x > 0).sum()),
                t_q=tq.statistic, p_tq=tq.pvalue, xA=A.x.mean(), nA=len(A), xB=Bh.x.mean(), nB=len(Bh),
                loo_q_min=min(lq), loo_s_min=min(ls), top5_share=top5['sum'].sum() / s.x.sum())

rows = []
# --- last quarter's move: top / bottom fifth of x(t-1), trade at the next F&O result (t)
p = ev[['symbol', 'qn', 'x', 'td']].copy()
nxt = p.copy(); nxt['qn'] = nxt.qn - 1
pr = p.merge(nxt, on=['symbol', 'qn'], suffixes=('', '_n'))
print('pairs (t, t+1) of the same stock, both F&O:', len(pr))
pr['pct'] = pr.groupby('qn').x.rank(pct=True)
base = pr[['symbol', 'qn']].copy(); base['qn'] = pr.qn + 1; base['x'] = pr.x_n.values; base['td'] = pr.td_n.values
base['pct_prev'] = pr.pct.values
# x here is excess vs the full quarter average (as in the build); the null picks among stocks that have a previous result
for nm, m in (('top fifth of last quarter\'s x, next result', base.pct_prev.to_numpy() > 0.8),
              ('bottom fifth of last quarter\'s x, next result', base.pct_prev.to_numpy() <= 0.2)):
    rows.append(describe(nm, m, base))

# --- last-4 track record (rebuild as in sector_stock_level.py / build_panel.py)
allev['h_td'] = allev.three_day * 100
H = {s: g.sort_values('qn', ascending=False) for s, g in allev.groupby('symbol')}
cut = ev.set_index(['symbol', 'qn']).i_cut
td4, td4fo = [], []
fo_hist = {s: g for s, g in ev.assign(h_td=ev.td).groupby('symbol')}
for s, q in zip(ev.symbol, ev.qn):
    g = H[s]; dec = cut[(s, q)]
    h = g[(g.qn < q) & (g.i_p1 < dec) & (g.i_react < dec)]
    td4.append(h.h_td.iloc[:4].mean() if len(h) >= 4 else np.nan)
    gf = fo_hist[s].sort_values('qn', ascending=False)
    hf = gf[(gf.qn < q) & (gf.i_p1 < dec) & (gf.i_react < dec)]
    td4fo.append(hf.h_td.iloc[:4].mean() if len(hf) >= 4 else np.nan)
ev['td4'] = td4; ev['td4fo'] = td4fo
f4 = ev[ev.td4.notna()].copy().reset_index(drop=True)
f4['pct4'] = f4.groupby('qn').td4.rank(pct=True)
print(f'\nresults with 4 earlier results: {len(f4)}; first quarter {f4.qn.min()}')
for thr, nm in ((0.8, 'last-4 top fifth (TR05, pre-registered)'), (0.9, 'last-4 top tenth (post hoc)')):
    rows.append(describe(nm, f4.pct4.to_numpy() > thr, f4))

print('\nthreshold sweep (last-4 average, share kept from the top), mean x, avg three-day, p (20,000 picks):')
for thr in (0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.93, 0.95, 0.97):
    m = f4.pct4.to_numpy() > thr
    nl = perm_null(f4, m, 20000)
    s = f4[m]
    print(f'  top {100*(1-thr):.0f}%: {m.sum()} results, x {fp(s.x.mean())}, td {fp(s.td.mean())}%, p {fpv(p2c(s.x.mean(), nl))}; '
          f'q0-10 x {fp(s[s.qn<=10].x.mean())} ({(s.qn<=10).sum()}), q11-21 x {fp(s[s.qn>=11].x.mean())} ({(s.qn>=11).sum()})')
# exclusive bands
print('bands of last-4 percentile: x and three-day by band')
f4['band'] = pd.cut(f4.pct4, [0, .2, .4, .6, .8, .9, 1.0])
print(f4.groupby('band', observed=True).agg(n=('x', 'size'), x=('x', 'mean'), td=('td', 'mean')).round(2).to_string())

f4fo = ev[ev.td4fo.notna()].copy().reset_index(drop=True)
f4fo['pct4'] = f4fo.groupby('qn').td4fo.rank(pct=True)
print('\nF&O-only history (instead of all events):')
for thr, nm in ((0.8, 'last-4 F&O-only top fifth'), (0.9, 'last-4 F&O-only top tenth')):
    rows.append(describe(nm, f4fo.pct4.to_numpy() > thr, f4fo, B=50000))

R = pd.DataFrame(rows)
pd.set_option('display.width', 300); pd.set_option('display.max_columns', 30)
print(R.round(3).to_string(index=False))
R.to_csv(f'{HERE}/sk3_stock.csv', index=False)

# stock-level lag-4 correlation halves (5f)
p4 = p.copy(); p4n = p.copy(); p4n['qn'] = p4n.qn - 4
pp4 = p4.merge(p4n, on=['symbol', 'qn'], suffixes=('', '_n'))
print(f'\nstock x(t) vs x(t+4): r {pear(pp4.x, pp4.x_n):+.3f} (n {len(pp4)}); t<=6 r {pear(pp4[pp4.qn<=6].x, pp4[pp4.qn<=6].x_n):+.3f} '
      f'(n {(pp4.qn<=6).sum()}); t>=11 r {pear(pp4[pp4.qn>=11].x, pp4[pp4.qn>=11].x_n):+.3f} (n {(pp4.qn>=11).sum()}); '
      f'Spearman {spear(pp4.x, pp4.x_n):+.3f}')
pp1 = pr
print(f'stock x(t) vs x(t+1): r {pear(pp1.x, pp1.x_n):+.3f} (n {len(pp1)}); t<=9 {pear(pp1[pp1.qn<=9].x, pp1[pp1.qn<=9].x_n):+.3f}; '
      f't>=11 {pear(pp1[pp1.qn>=11].x, pp1[pp1.qn>=11].x_n):+.3f}; 95% CI half-width about {1.96/np.sqrt(len(pp1)):.3f}')
