"""v11 - independent recomputation (own code, no study script imported) of the delivery features behind the top
candidates, from the compact delivery table (raw-verified in v02 / v10), with OWN ticker mapping and OWN split
adjustment (derived from raw close / next-day prev_close), then stress tests and placebos.
usage: python3 -P v11_independent.py <scratchpad> <out_dir>
"""
import sys
import numpy as np, pandas as pd

SP, OUT = sys.argv[1], sys.argv[2]
ST = f'{SP}/more_signals/delivery'
DATA = f'{SP}/sector_lab/data'
log = open(f'{OUT}/v11_independent.log', 'w')
def P(*a):
    s = ' '.join(str(x) for x in a); print(s); log.write(s + '\n'); log.flush()

ses = pd.read_csv(f'{DATA}/sessions.csv')
DAYS = ses.day.tolist(); NI = len(DAYS); IDX = {d: i for i, d in enumerate(DAYS)}
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
assert ret.index.tolist() == DAYS
SY = ret.columns.tolist(); SJ = {s: j for j, s in enumerate(SY)}; NS = len(SY)
R = ret.to_numpy(float)
NC = pd.read_csv(f'{DATA}/index_close.csv', usecols=['day', 'Nifty 50']).set_index('day')['Nifty 50'].reindex(DAYS).to_numpy(float)
NR = np.r_[np.nan, NC[1:] / NC[:-1] - 1]

# ---------------------------------------------------------------- own ticker mapping
_l = [ln.rstrip('\n').rsplit(',', 3) for ln in open(f'{SP}/symbolchange.csv', encoding='utf-8', errors='replace')]
sc = pd.DataFrame([x for x in _l if len(x) == 4], columns=['name', 'old', 'new', 'date'])
sc['old'] = sc.old.str.strip(); sc['new'] = sc.new.str.strip()
sc['date'] = pd.to_datetime(sc.date.str.strip(), format='%d-%b-%Y', errors='coerce')
sc = sc.dropna(subset=['date'])
eq = pd.read_csv(f'{ST}/downloads/delivery_eq.csv')
eq['dt'] = pd.to_datetime(eq.day)
eq['cur'] = eq.symbol
# rows dated before a change carry the old ticker -> forward-map (repeat for chains LTI->LTIM->LTM)
for _ in range(5):
    changed = 0
    for r in sc.itertuples():
        m = (eq.cur == r.old) & (eq.dt < r.date)
        if m.any():
            eq.loc[m, 'cur'] = r.new; changed += int(m.sum())
    if changed == 0:
        break
eq = eq[eq.cur.isin(SJ)].copy()
dup = eq.duplicated(['day', 'cur']).sum()
P(f'own mapping: rows in universe {len(eq)}, renamed {int((eq.cur != eq.symbol).sum())}, duplicate day-symbol {dup}')
P('   renamed tickers:', eq[eq.cur != eq.symbol].groupby(['symbol', 'cur']).size().to_dict())
# old tickers still present AFTER their change date (would mean the mapping is wrong / ticker reused)
bad = []
for r in sc.itertuples():
    if r.new in SJ:
        n = int(((eq.symbol == r.old) & (eq.dt >= r.date)).sum())
        if n: bad.append((r.old, r.new, str(r.date.date()), n))
P('   old ticker rows on/after the change date:', bad)

# ---------------------------------------------------------------- matrices
I = eq.day.map(IDX).to_numpy(int); J = eq.cur.map(SJ).to_numpy(int)
DP = np.full((NI, NS), np.nan); DQ = DP.copy(); TQ = DP.copy(); CL = DP.copy(); PC = DP.copy()
DP[I, J] = eq.deliv_per; DQ[I, J] = eq.deliv_qty; TQ[I, J] = eq.ttl_trd_qnty; CL[I, J] = eq.close; PC[I, J] = eq.prev_close
I0, I1 = int(I.min()), int(I.max())
P(f'delivery sessions i {I0}..{I1}: sessions in that range {I1 - I0 + 1}, sessions with any row {len(set(I))}')
missing_days = [DAYS[i] for i in range(I0, I1 + 1) if not np.isfinite(DP[i]).any()]
P('   sessions with no delivery rows at all:', missing_days)
cnt = np.isfinite(DP[I0:I1 + 1]).sum(1)
P(f'   rows per session: min {cnt.min()} (on {DAYS[I0 + int(cnt.argmin())]}), median {int(np.median(cnt))}, max {cnt.max()}')

# own share-count adjustment: a_t = prev_close_t / close_{t-1 traded}; a nice ratio far from 1 = split / bonus
SF = np.ones((NI, NS))   # multiply quantities by SF to put them on today's (latest) share basis
events = []
for j in range(NS):
    # NSE PREV_CLOSE is the unadjusted previous close: raw close/prev_close vs the adjusted return gives the
    # price-adjustment factor of the ex-date
    rows = np.where(np.isfinite(CL[:, j]) & np.isfinite(PC[:, j]) & np.isfinite(R[:, j]))[0]
    if len(rows) < 2: continue
    a = (CL[rows, j] / PC[rows, j]) / (1 + R[rows, j])
    for t, aa in zip(rows, a):
        if not np.isfinite(aa) or abs(aa - 1) < 0.15: continue
        inv = 1 / aa
        nice = False
        for q in range(1, 12):
            p = round(inv * q)
            if p > 0 and abs(inv - p / q) / inv < 0.01:
                nice = True; break
        events.append((SY[j], DAYS[t], round(aa, 4), nice))
        if nice:
            SF[:t, j] *= inv
P(f'own adjustment events (raw close/prev_close vs adjusted return, |a-1| >= 15%): {len(events)}; treated as share-count change (nice ratio): {sum(e[3] for e in events)}')
P('   not treated (demerger-like):', [e for e in events if not e[3]])
DQA = DQ * SF
# compare with the project's adjusted OHLCV volume_factor (relative factor inside windows)
adj = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'volume', 'volume_factor'])
adj = adj[adj.symbol.isin(SJ) & adj.day.isin(IDX)]
VF = np.full((NI, NS), np.nan); VF[adj.day.map(IDX), adj.symbol.map(SJ)] = adj.volume_factor
VOL = np.full((NI, NS), np.nan); VOL[adj.day.map(IDX), adj.symbol.map(SJ)] = adj.volume
ok = np.isfinite(TQ) & np.isfinite(VOL) & (VOL > 0)
rel = TQ[ok] * SF[ok] / VOL[ok]
# ratio should be constant per symbol (normalisation of the latest basis); check per symbol dispersion
rr = pd.DataFrame({'j': np.where(ok)[1], 'rel': rel})
disp = rr.groupby('j').rel.agg(lambda x: np.mean(np.abs(x / np.median(x) - 1) < 0.01))
P(f'own-adjusted traded qty / project adjusted volume constant within 1%: median share per symbol {disp.median():.4f}, '
  f'symbols below 99%: {[(SY[j], round(v, 3)) for j, v in disp.items() if v < 0.99]}')

def rmean(X, w, minp):
    return pd.DataFrame(X).rolling(w, min_periods=minp).mean().to_numpy()
DP60 = rmean(DP, 60, 40)              # mean over e-59..e
DQ5 = rmean(DQA, 5, 4); DQ60 = rmean(DQA, 60, 40)
DQR = DQ5 / DQ60
DPprev60 = np.vstack([np.full((1, NS), np.nan), rmean(DP, 60, 40)[:-1]])   # mean over e-60..e-1
DPL = DP - DPprev60
DQprev60 = np.vstack([np.full((1, NS), np.nan), rmean(DQA, 60, 40)[:-1]])
DQK_M = DQA / DQprev60                 # day-k qty / mean of k-60..k-1
TRADED = np.isfinite(R)

# ---------------------------------------------------------------- results panel
pan = pd.read_csv(f'{SP}/perf/features/panel.csv')
out = pd.read_csv(f'{SP}/perf/features/outcomes.csv')
f = pan.merge(out[['symbol', 'qn', 'three_day', 'three_day_net', 'tradable_B', 'vsN_H20', 'vsN_net_H20']], on=['symbol', 'qn'])
f['j'] = f.symbol.map(SJ)
assert f.j.notna().all()
f['e'] = f.i_cut - 1
j = f.j.to_numpy(int); e = f.e.to_numpy(int); k = f.i_react.to_numpy(int)
f['DP60'] = DP60[e, j]; f['DQR'] = DQR[e, j]; f['DPL'] = DPL[e, j]; f['DQK'] = DQK_M[k, j]
# coverage check: delivery values vs traded days inside the 60-session A window and the B window
nA = np.array([np.isfinite(DP[ee - 59:ee + 1, jj]).sum() for ee, jj in zip(e, j)])
tA = np.array([TRADED[ee - 59:ee + 1, jj].sum() for ee, jj in zip(e, j)])
nB = np.array([np.isfinite(DP[kk - 60:kk + 1, jj]).sum() for kk, jj in zip(k, j)])
tB = np.array([TRADED[kk - 60:kk + 1, jj].sum() for kk, jj in zip(k, j)])
P(f'window coverage: A rows with fewer delivery values than traded days {int((nA < tA).sum())}; B rows {int((nB < tB).sum())}; '
  f'A min values {nA.min()}, B min {nB.min()}; rows with day-k delivery missing {int(np.isnan(DP[k, j]).sum())}')
# point-in-time rank among the same quarter's F&O results stocks, all at the row's session e
def qrank(col_mat, name):
    rk = np.full(len(f), np.nan)
    for q, g in f.groupby('qn'):
        jj = g.j.to_numpy(int)
        for ee in g.e.unique():
            v = col_mat[ee, jj]
            s = pd.Series(v).rank(method='average')
            n = np.isfinite(v).sum()
            pct = (100 * s / n).to_numpy()
            rows = g.index[g.e.to_numpy() == ee]
            pos = [list(jj).index(x) for x in f.loc[rows, 'j']]
            rk[rows] = pct[pos]
    f[name] = rk
qrank(DP60, 'rank_DP60'); qrank(DPL, 'rank_DPL')

# compare with the study's features
st = pd.read_csv(f'{ST}/feat_results.csv')
c = f.merge(st[['symbol', 'qn', 'DP60', 'DQR', 'DPL', 'DQK', 'rank_DP60', 'rank_DPL']], on=['symbol', 'qn'], suffixes=('', '_st'))
for col in ['DP60', 'DQR', 'DPL', 'DQK', 'rank_DP60', 'rank_DPL']:
    a, b = c[col], c[col + '_st']
    d = np.abs(a - b) / np.maximum(1, np.abs(b))
    P(f'  {col:10s} n {len(c)} both-finite {int((a.notna() & b.notna()).sum())} differ>1e-3 rel: {int((d > 1e-3).sum())}  max {np.nanmax(d):.2e}')
    if (d > 1e-3).any():
        P(c.loc[d > 1e-3, ['symbol', 'qn', col, col + '_st']].head(12).to_string())

# ---------------------------------------------------------------- outcomes (own)
ic = f.i_cut.to_numpy(int); ip = f.i_p1.to_numpy(int)
own3 = np.array([np.nansum(R[a + 1:b + 1, jj]) * 100 for a, b, jj in zip(ic, ip, j)])
P(f'own three_day (sum of daily returns cutoff+1..Day+1) vs outcomes three_day: max abs diff {np.nanmax(np.abs(own3 - f.three_day)):.2e}; '
  f'window length always 3: {bool(np.all(ip - ic == 3))}')
def hedged(entry, H=20):
    y = np.full(len(f), np.nan); trad = np.zeros(len(f), bool)
    for n_, (en, jj) in enumerate(zip(entry, j)):
        if en + H + 1 > NI - 1: continue
        seg = R[en + 1:en + H + 1, jj]
        nt = np.isnan(R[en + 1:en + H + 2, jj]).sum()
        trad[n_] = nt <= 2
        y[n_] = (np.nanprod(1 + seg) - np.prod(1 + NR[en + 1:en + H + 1])) * 100 - 0.19
    return y, trad
y0, t0 = hedged(k); y1, t1 = hedged(k + 1); y2, t2 = hedged(k + 2)
m = f.tradable_B.to_numpy(bool)
P(f'own entry-k hedged net vs outcomes vsN_net_H20 (tradable_B): max abs diff {np.nanmax(np.abs(y0[m] - f.vsN_net_H20[m])):.2e}; '
  f'own tradable agrees {np.mean(t0 == m) * 100:.2f}%')
f['y_k0'], f['y_k1'], f['t_k1'] = y0, y1, t1
f.to_csv(f'{OUT}/v11_feat.csv', index=False)
np.savez_compressed(f'{OUT}/v11_mats.npz', DP60=DP60, DQR=DQR, DPL=DPL, DQK=DQK_M, DP=DP)
P('saved v11_feat.csv / v11_mats.npz')
