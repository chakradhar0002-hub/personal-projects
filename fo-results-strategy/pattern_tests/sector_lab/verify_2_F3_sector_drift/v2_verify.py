"""
Independent verification of candidate "B5": at the reaction-day close, buy an F&O-at-the-time stock whose
reaction-day return minus Nifty 50 return that day is > +6%, sell at the close 20 sessions later.
Hedge = short Nifty futures. Costs 0.17% stock round trip, +0.02% for Nifty futures hedge.

Written WITHOUT reading the candidate's scripts.

PRE-REGISTERED CHECKS (written before looking at outcomes):
  A. Base reproduction: threshold 6%, hold 20, entry reaction-day close.                         (1)
  B. Neighbouring thresholds {3,4,5,6,7,8}% x horizons {5,10,20,30} sessions                       (24, incl. A)
  C. Execution realism: entry next-session open (intraday.csv) and next-session close, hold to
     the same exit (close of reaction day + 20) and also 20 sessions from entry.                    (3)
  D. Robustness on base: drop 5 best trades; drop best quarter; leave-one-quarter-out (min t);
     leave-one-sector_index-out; costs doubled; first 14 vs last 8 quarters; date-clustered stats;
     calendar-month clustering; beta-adjusted hedge (beta from 250 trailing sessions before entry).  (descriptive)
  E. Placebos: (i) random F&O results events with the same per-quarter counts (2000 draws);
     (ii) same rule (>6% beat over Nifty) on F&O stocks on days with NO result within +-10 sessions;
     (iii) date-matched placebo: for each trade, a random other F&O stock (not reporting within +-10 sessions)
     on the same date, same hold;  (iv) random 6%-sized subsets of the >4% winners.
  F. Survivorship note only (universe = today's F&O list; cannot be fixed from this pack).
Total distinct rule variants evaluated here: 24 (B) + 3 (C) = 27; only A is the candidate under test.
Missing returns: a blank daily return means no trade; compounding skips it (the next return spans 2 sessions,
so the product is still the close-to-close return). Trades whose reaction-day return is blank are dropped.
"""
import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
import sys
sys.path.append('/root/.local/lib/python3.11/site-packages')
import numpy as np, pandas as pd

D = os.environ.get('SECTOR_LAB', 'sector_lab') + '/data/'
OUT = os.environ.get('SECTOR_LAB', 'sector_lab') + '/verify_2_F3_sector_drift/'
rng = np.random.default_rng(12345)
C_STK, C_HEDGE = 0.0017, 0.0019

ev = pd.read_csv(D + 'events.csv')
R = pd.read_csv(D + 'returns.csv', index_col=0)
ID = pd.read_csv(D + 'intraday.csv', index_col=0)
IX = pd.read_csv(D + 'index_close.csv', index_col=0)
assert (R.index == IX.index).all() and (ID.index == R.index).all()
N = len(R)
syms = list(R.columns); sidx = {s: k for k, s in enumerate(syms)}
Rv = R.values  # NaN = no trade
G = np.nan_to_num(Rv) + 1.0
CG = np.vstack([np.ones((1, G.shape[1])), np.cumprod(G, axis=0)])  # CG[t+1] = growth up to and incl day t
IDv = ID.reindex(columns=syms).values
nifty = IX['Nifty 50'].values
nret = np.r_[np.nan, nifty[1:] / nifty[:-1] - 1]
lines = []
def P(*a):
    s = ' '.join(str(x) for x in a); print(s); lines.append(s)

def stock_hold(k, a, b):
    """compounded return from close of session a to close of session b"""
    return CG[b + 1, k] / CG[a + 1, k] - 1

def idx_hold(name, a, b):
    s = IX[name].values
    if np.isnan(s[a]) or np.isnan(s[b]):
        s = IX['Nifty 500'].values
    return s[b] / s[a] - 1

ev = ev[ev.symbol.isin(syms)].copy()
ev['k'] = ev.symbol.map(sidx)
ev['react_ret'] = [Rv[i, k] for i, k in zip(ev.i_react, ev.k)]
ev['nifty_react'] = nret[ev.i_react.values]
ev['beat'] = ev.react_ret - ev.nifty_react
fo = ev[ev.in_fo == True].copy()
P('F&O events', len(fo), 'blank reaction-day return', fo.react_ret.isna().sum())
P('check vs events.move (reaction-day return) max abs diff:', np.nanmax(np.abs(fo.react_ret - fo.move)))

def build(df, thr, H, entry='close0'):
    d = df[df.beat > thr].copy()
    out = []
    for _, r in d.iterrows():
        i0, k = int(r.i_react), int(r.k)
        if entry == 'close0':
            a, b = i0, i0 + H
            if b >= N: continue
            raw = stock_hold(k, a, b)
        elif entry == 'open1':  # buy next-session open, sell close i0+H
            a, b = i0, i0 + H
            if b >= N or np.isnan(IDv[i0 + 1, k]): continue
            raw = (1 + IDv[i0 + 1, k]) * (CG[b + 1, k] / CG[i0 + 2, k]) - 1
        elif entry == 'close1':
            a, b = i0 + 1, i0 + 1 + H
            if b >= N: continue
            raw = stock_hold(k, a, b)
        nf = nifty[b] / nifty[a] - 1
        sc = idx_hold(r.sector_index, a, b)
        out.append(dict(symbol=r.symbol, qn=int(r.qn), i0=i0, a=a, b=b, sector=r.sector_index, beat=r.beat,
                        raw=raw, nifty=nf, sect=sc, net=raw - C_STK, hedged=raw - nf - C_HEDGE,
                        vs_sector=raw - sc - C_STK, day=R.index[i0]))
    return pd.DataFrame(out)

def qstats(t, col='hedged', qcol='qn'):
    g = t.groupby(qcol)[col].mean()
    n = len(g); m = g.mean(); sd = g.std(ddof=1)
    tv = m / (sd / np.sqrt(n)) if n > 1 else np.nan
    return g, m, tv

def summary(t, label):
    if len(t) == 0:
        P(label, 'no trades'); return
    g, m, tv = qstats(t)
    f14 = t[t.qn <= 13]; l8 = t[t.qn >= 14]
    gf = f14.groupby('qn').hedged.mean(); gl = l8.groupby('qn').hedged.mean()
    P(f"{label}: n={len(t)} raw_net={100*t.net.mean():.2f} hedged={100*t.hedged.mean():.2f} vs_sector={100*t.vs_sector.mean():.2f} "
      f"perQ={100*m:.2f} t={tv:.2f} Qpos={int((g>0).sum())}/{len(g)} first14(trade)={100*f14.hedged.mean():.2f} "
      f"last8(trade)={100*l8.hedged.mean():.2f} first14(perQ)={100*gf.mean():.2f} last8(perQ)={100*gl.mean():.2f} "
      f"last8_raw={100*l8.net.mean():.2f} win={100*(t.hedged>0).mean():.1f}%")
    return g

# ---------------- A. base
P('\n=== A. base reproduction (6%, 20, close entry)')
base = build(fo, 0.06, 20)
g = summary(base, 'BASE')
P('per-quarter hedged avg (%):', ' '.join(f"{q}:{100*v:.2f}({(base.qn==q).sum()})" for q, v in g.items()))
base.to_csv(OUT + 'base_trades.csv', index=False)
# by date clustering
gd = base.groupby('day').hedged.mean()
P(f"date-clustered: dates={len(gd)} mean={100*gd.mean():.2f} t={gd.mean()/(gd.std()/np.sqrt(len(gd))):.2f}")
base['month'] = base.day.str[:7]
gm = base.groupby('month').hedged.mean()
P(f"calendar-month clustered: months={len(gm)} mean={100*gm.mean():.2f} t={gm.mean()/(gm.std()/np.sqrt(len(gm))):.2f}")
P('Overlap: trades per quarter', base.groupby('qn').size().describe().round(1).to_dict())
# max concurrent positions
conc = np.zeros(N)
for _, r in base.iterrows(): conc[r.a + 1:r.b + 1] += 1
P('max concurrent positions', int(conc.max()), 'mean while any open', round(conc[conc > 0].mean(), 1))

# ---------------- B. grid
P('\n=== B. neighbouring thresholds x horizons (hedged net, % ; perQ mean / t / first14 perQ / last8 perQ / n)')
grid = {}
for thr in [0.03, 0.04, 0.05, 0.06, 0.07, 0.08]:
    for H in [5, 10, 20, 30]:
        t = build(fo, thr, H)
        gq, m, tv = qstats(t)
        f = t[t.qn <= 13].groupby('qn').hedged.mean().mean(); l = t[t.qn >= 14].groupby('qn').hedged.mean().mean()
        grid[(thr, H)] = t
        P(f"thr={thr:.2f} H={H:2d}: n={len(t):4d} trade={100*t.hedged.mean():5.2f} perQ={100*m:5.2f} t={tv:5.2f} "
          f"f14={100*f:5.2f} l8={100*l:5.2f} raw_net={100*t.net.mean():5.2f} vsSect={100*t.vs_sector.mean():5.2f}")

# ---------------- C. execution realism
P('\n=== C. execution')
for ent in ['open1', 'close1']:
    t = build(fo, 0.06, 20, ent); summary(t, f'entry={ent}')
    if ent == 'close1': c1 = t

# ---------------- D. robustness
P('\n=== D. robustness on base')
b = base.sort_values('hedged', ascending=False)
summary(b.iloc[5:], 'drop 5 best trades')
bestq = g.idxmax(); summary(base[base.qn != bestq], f'drop best quarter (qn {bestq})')
lo = []
for q in sorted(base.qn.unique()):
    _, m, tv = qstats(base[base.qn != q]); lo.append((tv, q, m))
P('leave-one-quarter-out min t', min(lo)[0].round(2), 'qn', min(lo)[1], 'max t', max(lo)[0].round(2))
for s in base.sector.value_counts().index:
    t = base[base.sector != s]; _, m, tv = qstats(t)
    P(f"  drop sector {s:28s} ({(base.sector==s).sum():3d} trades): perQ={100*m:.2f} t={tv:.2f} trade={100*t.hedged.mean():.2f}")
P('by sector (hedged trade mean, n):', base.groupby('sector').hedged.agg(['mean', 'size']).assign(mean=lambda x: (100*x['mean']).round(2)).to_dict('index'))
t2 = base.copy(); t2['hedged'] = t2.hedged - C_HEDGE; summary(t2, 'costs doubled')
# top symbols concentration
P('trades by symbol top 10:', base.symbol.value_counts().head(10).to_dict())
P('repeat-symbol share', round(1 - base.symbol.nunique() / len(base), 2))
# beta-adjusted hedge
betas = []
for _, r in base.iterrows():
    k = sidx[r.symbol]; lo_ = max(1, r.a - 250)
    x = nret[lo_:r.a]; y = Rv[lo_:r.a, k]; mk = ~np.isnan(x) & ~np.isnan(y)
    betas.append(np.cov(x[mk], y[mk])[0, 1] / np.var(x[mk], ddof=1) if mk.sum() > 60 else 1.0)
base['beta'] = betas
tb = base.copy(); tb['hedged'] = tb.raw - tb.beta * tb.nifty - C_HEDGE
P(f"median beta {np.median(betas):.2f}"); summary(tb, 'beta-hedged')
# extremes: beats > 15%
P('trades with beat>15%:', (base.beat > 0.15).sum(), 'their hedged mean', round(100*base[base.beat > 0.15].hedged.mean(), 2))
# market regime: hedged result vs Nifty move over the hold
P('corr(hedged, nifty over hold)', round(np.corrcoef(base.hedged, base.nifty)[0, 1], 2))
# year breakdown
base['year'] = base.day.str[:4]
P('by year hedged mean %:', (100*base.groupby('year').hedged.mean()).round(2).to_dict(), base.groupby('year').size().to_dict())

# ---------------- E. placebos
P('\n=== E. placebos')
# (i) random F&O results with same per-quarter counts
allfo = fo.dropna(subset=['react_ret']).copy()
allfo = allfo[allfo.i_react + 20 < N]
allfo['raw'] = [stock_hold(int(k), int(i), int(i) + 20) for k, i in zip(allfo.k, allfo.i_react)]
allfo['hedged'] = allfo.raw - (nifty[allfo.i_react.values + 20] / nifty[allfo.i_react.values] - 1) - C_HEDGE
cnt = base.groupby('qn').size()
obs_m = qstats(base)[1]; obs_trade = base.hedged.mean()
sims = []
grp = {q: allfo[allfo.qn == q].hedged.values for q in cnt.index}
for _ in range(2000):
    parts = [rng.choice(grp[q], cnt[q], replace=False) for q in cnt.index]
    sims.append(np.mean([p.mean() for p in parts]))
sims = np.array(sims)
P(f"(i) random results same counts: perQ mean {100*sims.mean():.2f}, 95th pct {100*np.percentile(sims,95):.2f}, share >= obs {100*obs_m:.2f}: {(sims>=obs_m).mean():.4f}")
P(f"    all F&O results unconditional 20d hedged: {100*allfo.hedged.mean():.2f}")
# (ii) non-results days: F&O stocks with >6% beat on days with no result within +-10 sessions
# F&O status per stock-date: approximate with in_fo of the nearest event of that stock (same qn season); restrict to
# stock-days between the stock's first and last in_fo==True events.
fo_span = ev[ev.in_fo == True].groupby('k').agg(lo=('i_react', 'min'), hi=('i_react', 'max'))
near = np.zeros_like(Rv, dtype=bool)
for k, i in zip(ev.k, ev.i_react):
    near[max(0, i - 10):min(N, i + 11), k] = True
beat_all = Rv - nret[:, None]
rows = []
for k, (lo_, hi_) in fo_span.iterrows():
    for i in range(lo_, min(hi_ + 1, N - 21)):
        if not near[i, k] and beat_all[i, k] > 0.06:
            raw = stock_hold(k, i, i + 20); nf = nifty[i + 20] / nifty[i] - 1
            rows.append(dict(k=k, i=i, raw=raw, hedged=raw - nf - C_HEDGE, day=R.index[i]))
nr = pd.DataFrame(rows)
# assign to qn by nearest season: use calendar quarter
nr['cq'] = pd.to_datetime(nr.day).dt.to_period('Q').astype(str)
gq_ = nr.groupby('cq').hedged.mean()
P(f"(ii) non-results >6% beat days: n={len(nr)} hedged trade mean {100*nr.hedged.mean():.2f}, per-cal-quarter mean {100*gq_.mean():.2f} t={gq_.mean()/(gq_.std()/np.sqrt(len(gq_))):.2f}")
# (iii) date-matched random non-reporting F&O stock, same entry date & hold
infoq = ev[ev.in_fo == True].groupby('qn').k.apply(set).to_dict()
pm = []
for it in range(200):
    vals = []
    for _, r in base.iterrows():
        cands = [k for k in infoq[r.qn] if not near[r.a, k] and not np.isnan(Rv[r.a, k])]
        k = rng.choice(cands)
        raw = stock_hold(k, r.a, r.b); vals.append((r.qn, raw - r.nifty - C_HEDGE))
    d = pd.DataFrame(vals, columns=['qn', 'h']); pm.append(d.groupby('qn').h.mean().mean())
pm = np.array(pm)
P(f"(iii) same-date random non-reporting F&O stock: perQ mean {100*pm.mean():.2f}, share >= obs: {(pm>=obs_m).mean():.3f}")
# (iii-b) same-date: all F&O stocks that did NOT beat (beat<=6%) among those reporting same reaction day
# (iv) random subsets of 4% winners
w4 = grid[(0.04, 20)]
sub = []
for _ in range(2000):
    s = w4.sample(len(base), random_state=int(rng.integers(1e9)))
    sub.append(qstats(s)[1])
sub = np.array(sub)
P(f"(iv) random subsets of 4% winners (n={len(base)} of {len(w4)}): mean {100*sub.mean():.2f}; share >= obs: {(sub>=obs_m).mean():.3f}")
# (v) sign test-like: within-quarter shuffle of 'beat' label across F&O reporters (same quarter): equivalent to (i).

# ---------------- multiple testing
P('\n=== multiple testing')
# approx two-sided p from t with df=21 via simulation of student t
df_ = len(g) - 1; tobs = qstats(base)[2]
tdraw = rng.standard_normal((400000,)) / np.sqrt(rng.chisquare(df_, 400000) / df_)
p = (np.abs(tdraw) >= tobs).mean()
P(f"t={tobs:.2f} df={df_} two-sided p~{p:.4f}; Bonferroni x36 -> {min(1,36*p):.3f}; x(36+prior 4% search) remains > 0.05 if p>0.0014")

open(OUT + 'v2_output.txt', 'w').write('\n'.join(lines))
