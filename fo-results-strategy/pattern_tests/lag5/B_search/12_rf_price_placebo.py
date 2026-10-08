"""
12_rf_price_placebo.py -- placebo for the walk-forward random forest "P(three_day > +3%)" top-10% picks.
The full model uses results-specific inputs (option IV, peers reported, past reactions...) that do not exist on
ordinary days, so it cannot be applied off-results.  Instead:
  1. Re-run the identical walk-forward RF (same settings, target three_day > +3%, top-10% threshold from out-of-bag
     training scores) using ONLY features that can be computed exactly on ANY date: stock / Nifty / sector price
     features and the stock's own past results reactions (as of the date).  Checked against features_all.csv.
  2. Check this price-only model still finds the edge on results (the real trades).
  3. Apply each quarter's model to the same F&O stocks on dates with no result session within 10 sessions (lag > 5%
     rows only, dates between this season's first cutoff and the next season's first cutoff) and buy rows scoring
     above the same threshold: next-3-session return.
  4. Null: the identical results pipeline on 30 within-quarter shuffles of three_day.
Output: rf_price_placebo.csv, rf_price_trades.csv
"""
import os, sys
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestClassifier
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gsearch as G

D = os.environ.get('LAB_ROOT', 'lab') + '/sector_lab/data/'
R = pd.read_csv(D + 'returns.csv'); I = pd.read_csv(D + 'intraday.csv'); IX = pd.read_csv(D + 'index_close.csv')
E = pd.read_csv(D + 'events.csv')
F = pd.read_csv(f'{G.RL.HERE}/features_all.csv')
days = R.day.values; syms = list(R.columns[1:]); col = {s: j for j, s in enumerate(syms)}
RA = R[syms].values.astype(float); IA = I[syms].values.astype(float)
T, NS = RA.shape
valid = np.isfinite(RA)
started = np.maximum.accumulate(valid, axis=0)
lv = np.cumprod(1 + np.nan_to_num(RA), axis=0); lv[~started] = np.nan


def sh(a, k):
    out = np.full_like(a, np.nan, dtype=float)
    if a.ndim == 1:
        out[k:] = a[:-k]
    else:
        out[k:] = a[:-k]
    return out


def roll(a, n, fn, minp):
    return getattr(pd.DataFrame(a).rolling(n, min_periods=minp), fn)().values


P = {}
for lab, n in (('r1w', 5), ('r1m', 21), ('r3m', 63), ('r6m', 126), ('r1y', 250)):
    P[lab] = lv / sh(lv, n) - 1
cnt250 = roll(np.where(np.isfinite(lv), 1.0, 0.0), 250, 'sum', 1)
hi250 = roll(lv, 250, 'max', 1); lo250 = roll(lv, 250, 'min', 1)
P['from_52w_high'] = np.where(cnt250 > 200, lv / hi250 - 1, np.nan)
P['from_52w_low'] = np.where(cnt250 > 200, lv / lo250 - 1, np.nan)
P['vs_ma50'] = np.where(cnt250 > 200, lv / roll(lv, 50, 'mean', 1) - 1, np.nan)
P['vs_ma200'] = np.where(cnt250 > 200, lv / roll(lv, 200, 'mean', 1) - 1, np.nan)
cnt60 = roll(valid.astype(float), 60, 'sum', 1)
P['vol60'] = np.where(cnt60 > 40, roll(RA, 60, 'std', 2) * np.sqrt(252), np.nan)
nifty = IX['Nifty 50'].values.astype(float)
for lab, n in (('1w', 5), ('1m', 21), ('3m', 63)):
    nr = nifty / sh(nifty, n) - 1
    P[f'nifty_{lab}'] = np.repeat(nr[:, None], NS, 1)
    P[f'vs_nifty_{lab}'] = P[f'r{lab}'] - nr[:, None]
P['india_vix'] = np.repeat(IX['India VIX'].values.astype(float)[:, None], NS, 1)
# sector index per stock (most common in events)
sec_of = E.groupby('symbol').sector_index.agg(lambda s: s.mode().iloc[0] if s.notna().any() else np.nan)
SC = np.full((T, NS), np.nan)
for s, si in sec_of.items():
    if s in col and isinstance(si, str) and si in IX.columns:
        SC[:, col[s]] = IX[si].values.astype(float)
for lab, n in (('1w', 5), ('1m', 21), ('3m', 63)):
    sr = SC / sh(SC, n) - 1
    P[f'sector_{lab}'] = sr
    P[f'vs_sector_{lab}'] = P[f'r{lab}'] - sr
P['d0'] = RA; P['d1'] = sh(RA, 1); P['d2'] = sh(RA, 2)
P['r2d'] = lv / sh(lv, 2) - 1; P['r3d'] = lv / sh(lv, 3) - 1; P['r10d'] = lv / sh(lv, 10) - 1
P['r20d'] = lv / sh(lv, 20) - 1; P['pre5'] = lv / sh(lv, 5) - 1
gap = (1 + RA) / (1 + IA) - 1
P['gap0'] = gap; P['intra0'] = IA
g5 = roll(np.isfinite(gap).astype(float), 5, 'sum', 1); i5 = roll(np.isfinite(IA).astype(float), 5, 'sum', 1)
P['gap5'] = np.where(g5 >= 3, roll(np.nan_to_num(gap), 5, 'sum', 1), np.nan)
P['intra5'] = np.where(i5 >= 3, roll(np.nan_to_num(IA), 5, 'sum', 1), np.nan)
nr1 = np.r_[np.nan, nifty[1:] / nifty[:-1] - 1]
P['nifty_d0'] = np.repeat(nr1[:, None], NS, 1)
n3 = nifty / sh(nifty, 3) - 1; n10 = nifty / sh(nifty, 10) - 1
P['nifty_3d'] = np.repeat(n3[:, None], NS, 1)
P['exn_d0'] = RA - nr1[:, None]; P['exn_3d'] = P['r3d'] - n3[:, None]; P['exn_10d'] = P['r10d'] - n10[:, None]
P['sec_d0'] = SC / sh(SC, 1) - 1; P['sec_3d'] = SC / sh(SC, 3) - 1
P['exs_3d'] = P['r3d'] - P['sec_3d']
pp = np.cumprod(1 + np.nan_to_num(RA), axis=0)
ok45 = cnt60 >= 45
P['dist_20h'] = np.where(ok45, pp / roll(pp, 20, 'max', 1) - 1, np.nan)
P['dist_20l'] = np.where(ok45, pp / roll(pp, 20, 'min', 1) - 1, np.nan)
P['dist_60h'] = np.where(ok45, pp / roll(pp, 60, 'max', 1) - 1, np.nan)
sd60 = roll(RA, 60, 'std', 2) * np.sqrt(np.maximum(cnt60 - 1, 0) / np.maximum(cnt60, 1))
c5 = roll(valid.astype(float), 5, 'sum', 1); c20 = roll(valid.astype(float), 20, 'sum', 1)
sd5 = roll(RA, 5, 'std', 2) * np.sqrt(np.maximum(c5 - 1, 0) / np.maximum(c5, 1))
sd20 = roll(RA, 20, 'std', 2) * np.sqrt(np.maximum(c20 - 1, 0) / np.maximum(c20, 1))
P['vol5_60'] = np.where(ok45 & (sd60 > 0), sd5 / sd60, np.nan)
P['vol20_60'] = np.where(ok45 & (sd60 > 0), sd20 / sd60, np.nan)
P['maxabs5'] = np.where(ok45, roll(np.abs(RA), 5, 'max', 1), np.nan)
P['z5'] = np.where(ok45 & (sd60 > 0), P['pre5'] / (sd60 * np.sqrt(5)), np.nan)
P['z20'] = np.where(ok45 & (sd60 > 0), P['r20d'] / (sd60 * np.sqrt(20)), np.nan)
P['up10'] = np.where(ok45, roll((np.nan_to_num(RA, nan=0.0) > 0).astype(float), 10, 'sum', 10) / 10, np.nan)
sgn = np.where(np.isfinite(RA), np.sign(RA), 0)
st = np.zeros((T, NS))
for i in range(T):
    prev = st[i - 1] if i else np.zeros(NS)
    s = sgn[i]
    st[i] = np.where(s == 0, 0, np.where(np.sign(prev) == s, prev + s, s))
P['streak'] = st
FEATS = list(P.keys())

# ---- check against features_all at the real cutoffs
Fi = F[F.symbol.isin(col)].reset_index(drop=True)
jj = np.array([col[s] for s in Fi.symbol]); ii = Fi.i_cut.values
chk = []
for f in FEATS:
    if f == 'pre5' or f not in Fi.columns:
        continue
    a = P[f][ii, jj]; b = Fi[f].values.astype(float)
    okb = np.isfinite(a) & np.isfinite(b)
    chk.append({'feature': f, 'n_both': int(okb.sum()), 'n_feat': int(np.isfinite(b).sum()), 'n_mine': int(np.isfinite(a).sum()),
                'share_close': float((np.abs(a[okb] - b[okb]) < 1e-4).mean()) if okb.any() else np.nan})
C = pd.DataFrame(chk)
print(C.to_string())
bad = C[(C.share_close < 0.99) | (C.n_both < 0.97 * C.n_feat)]
print('features not reproduced well (dropped):', list(bad.feature))
FEATS = [f for f in FEATS if f not in set(bad.feature) and f != 'pre5']

# ---- own-history as-of features (completed results only)
E2 = E.sort_values(['symbol', 'i_cut'])
own_rows = []
for s, g in E2.groupby('symbol'):
    for k in range(len(g)):
        dm1, rd, dp1, a3 = (g.ret_dm1.values[:k + 1], g.ret_rd.values[:k + 1], g.ret_dp1.values[:k + 1],
                            np.abs(g.three_day.values[:k + 1]))
        own_rows.append({'symbol': s, 'i_from': int(g.i_p1.values[k]) + 1,
                         'own_dm1': np.nanmean(dm1) if k + 1 >= 2 else np.nan, 'own_rd': np.nanmean(rd) if k + 1 >= 2 else np.nan,
                         'own_dp1': np.nanmean(dp1) if k + 1 >= 2 else np.nan, 'own_abs3d': np.nanmean(a3) if k + 1 >= 2 else np.nan})
O = pd.DataFrame(own_rows).sort_values('i_from')
OWN = ['own_dm1', 'own_rd', 'own_dp1', 'own_abs3d']

# results rows (the group) with the price-only features at the cutoff (own_* from features_all, identical definition)
df = G.load_group('fo')
dj = np.array([col[s] for s in df.symbol]); di = df.i_cut.values
Xr = np.column_stack([P[f][di, dj] for f in FEATS] + [df[o].values for o in OWN])
y = df.three_day.values; qn = df.qn.values
FE_ALL = FEATS + OWN
print('price-only features used:', len(FE_ALL))

# placebo rows: lag > 5%, F&O span, no result session within 10 sessions
near = np.zeros((T, NS), bool)
for s, ird in zip(E.symbol, E.i_rd):
    if s in col:
        near[max(0, ird - 10):ird + 11, col[s]] = True
fo_span = np.zeros((T, NS), bool)
for s, g in E[E.in_fo == True].groupby('symbol'):
    if s in col:
        fo_span[g.i_cut.min():g.i_cut.max() + 1, col[s]] = True
fwd = np.full_like(RA, np.nan); z = np.nan_to_num(RA)
fwd[:-3] = z[1:-2] + z[2:-1] + z[3:]; fwd[~started] = np.nan
season_start = df.groupby('qn').i_cut.min()
season_start = F[F.in_fo].groupby('qn').i_cut.min()
mask = fo_span & ~near & np.isfinite(fwd) & (P['vs_nifty_1m'] < -0.05)
pi, pj = np.nonzero(mask)
PL = pd.DataFrame({'i': pi, 'symbol': np.array(syms)[pj], 'fwd3': fwd[pi, pj]})
PL['pq'] = np.searchsorted(season_start.values, pi, side='right') - 1
PL = PL[(PL.pq >= 8)].reset_index(drop=True)
PL = PL.sort_values('i').reset_index(drop=True)
PL = pd.merge_asof(PL, O, left_on='i', right_on='i_from', by='symbol', direction='backward')
Xp = np.column_stack([P[f][PL.i.values, [col[s] for s in PL.symbol]] for f in FEATS] + [PL[o].values for o in OWN])
print('placebo rows (lag>5%, q8+):', len(PL))


def impute(Xtr, X):
    med = np.nanmedian(Xtr, axis=0); med = np.where(np.isfinite(med), med, 0)
    return np.where(np.isfinite(X), X, med)


def run(ys, with_placebo):
    tr_rows, pl_rows = [], []
    for q in range(8, 22):
        tr = qn < q; te = qn == q
        lab = (ys[tr] > 0.03).astype(int)
        m = RandomForestClassifier(n_estimators=300, min_samples_leaf=10, max_features=0.3, oob_score=True,
                                   n_jobs=2, random_state=q)
        m.fit(impute(Xr[tr], Xr[tr]), lab)
        oof = m.oob_decision_function_[:, 1]
        c10, c25 = np.nanpercentile(oof, 90), np.nanpercentile(oof, 75)
        pte = m.predict_proba(impute(Xr[tr], Xr[te]))[:, 1]
        for ii_, p in zip(np.where(te)[0], pte):
            tr_rows.append({'qn': q, 'symbol': df.symbol[ii_], 'score': p, 'top10': p >= c10, 'top25': p >= c25,
                            'pnl': ys[ii_]})
        if with_placebo:
            pm = PL.pq.values == q
            if pm.any():
                pp_ = m.predict_proba(impute(Xr[tr], Xp[pm]))[:, 1]
                sub = PL[pm].assign(score=pp_, top10=pp_ >= c10, top25=pp_ >= c25)
                pl_rows.append(sub[['i', 'symbol', 'pq', 'fwd3', 'score', 'top10', 'top25']])
    return pd.DataFrame(tr_rows), (pd.concat(pl_rows) if pl_rows else None)


TR, PLs = run(y, True)
TR.to_csv(f'{G.HERE}/rf_price_trades.csv', index=False)
out = []
for v in ('top10', 'top25'):
    t = TR[TR[v]]
    qa = t.groupby('qn').pnl.mean()
    p = PLs[PLs[v]]
    out.append({'variant': v, 'trades': len(t), 'avg_pct': 100 * t.pnl.mean(), 'q_pos': f'{int((qa > 0).sum())}/{len(qa)}',
                'last8_trades': int((t.qn >= 14).sum()), 'last8_avg_pct': 100 * t[t.qn >= 14].pnl.mean(),
                'placebo_n': len(p), 'placebo_avg_pct': 100 * p.fwd3.mean(),
                'placebo_date_avg_pct': 100 * p.groupby('i').fwd3.mean().mean(),
                'placebo_all_lag5_rows_avg_pct': 100 * PLs.fwd3.mean()})
print(pd.DataFrame(out).round(3).to_string())
rng = np.random.default_rng(8)
nulls = []
for s in range(30):
    ys = G.shuffle_within(y, qn, rng)
    tn, _ = run(ys, False)
    nulls.append({v: 100 * tn[tn[v]].pnl.mean() for v in ('top10', 'top25')})
N = pd.DataFrame(nulls)
for o in out:
    v = o['variant']
    o['null_mean'] = N[v].mean(); o['null_p95'] = N[v].quantile(.95); o['null_p'] = float((N[v] >= o['avg_pct']).mean())
R_ = pd.DataFrame(out)
R_.to_csv(f'{G.HERE}/rf_price_placebo.csv', index=False)
print(R_.round(3).to_string())
