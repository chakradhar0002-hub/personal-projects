#!/usr/bin/env python3
"""F&O positioning family - step 2: point-in-time OI / basis / PCR / IV features (NO outcome is read here).

usage: python3 -P p2_features.py <fo_compact.db> <scratchpad> <out_dir>

Builds (T sessions x S symbols) daily matrices from the compact bhavcopy tables, then features at:
  results rows (perf/features/panel.csv): A at i_cut (and i_cut-1 for the robustness check), B at k = i_react
    (B05 at i_cut);
  trade-A placebo days (ta/build/placebo_ta.csv.gz: in F&O, next result in the panel) at day i;
  trade-B placebo days (tafa/C_post_results/quiet_days.csv.gz) at day i (B05 at i-2).
Signal flags follow prereg.txt (quintile cut-offs within quarter for results; within qn_next / month for placebo days).
Outputs in out_dir: daily.npz, results_features.csv, placebo_A_features.csv.gz, placebo_B_features.csv.gz,
features.log, coverage.csv.
"""
import csv
import os
import sqlite3
import sys
from datetime import date, datetime

import numpy as np
import pandas as pd

DB, SP, OUTD = sys.argv[1], sys.argv[2], sys.argv[3]
DATA = f'{SP}/sector_lab/data'
os.makedirs(OUTD, exist_ok=True)
LOG = open(f'{OUTD}/features.log', 'w')
R_RATE = 0.065


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + '\n')
    LOG.flush()


ses = pd.read_csv(f'{DATA}/sessions.csv')
days = ses.day.tolist()
T = len(days)
DIX = {d: i for i, d in enumerate(days)}
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
assert ret.index.tolist() == days
SYMS = ret.columns.tolist()
S = len(SYMS)
SYM = {s: j for j, s in enumerate(SYMS)}
R = ret.to_numpy(float)
PX = np.cumprod(1.0 + np.nan_to_num(R), axis=0)

# ------------------------------------------------------------------ ticker changes (raw ticker on day d -> panel symbol)
CH = {}
for r in csv.reader(open(f'{SP}/symbolchange.csv', encoding='latin-1')):
    if len(r) >= 4:
        try:
            dt = datetime.strptime(r[3].strip(), '%d-%b-%Y').date().isoformat()
        except ValueError:
            continue
        CH.setdefault(r[1].strip(), []).append((dt, r[2].strip()))
for k in CH:
    CH[k].sort()


def resolve(sym, d):
    seen = set()
    while sym in CH and sym not in seen:
        seen.add(sym)
        nxt = [n for dt, n in CH[sym] if dt > d]
        if not nxt:
            break
        sym = nxt[0]
    return sym


# ------------------------------------------------------------------ load compact tables
db = sqlite3.connect(DB)
done = pd.read_sql('SELECT * FROM done', db)
P(f'fetched sessions ok {int((done.ok == 1).sum())}, missing {int((done.ok == 0).sum())}: '
  f'{done.day[done.ok == 0].tolist()}')
fut = pd.read_sql('SELECT * FROM fut', db)
opt = pd.read_sql('SELECT * FROM opt', db)
atm = pd.read_sql('SELECT * FROM atm', db)
P(f'rows fut {len(fut)} opt {len(opt)} atm {len(atm)}')


def map_frame(df):
    key = df[['day', 'sym']].drop_duplicates()
    key['symbol'] = [resolve(s, d) for s, d in zip(key.sym, key.day)]
    df = df.merge(key, on=['day', 'sym'])
    df = df[df.symbol.isin(SYM) & df.day.isin(DIX)].copy()
    # one raw ticker per (day, symbol): prefer the one that already is the panel symbol
    df['own'] = (df.sym == df.symbol).astype(int)
    first = df.sort_values('own', ascending=False).drop_duplicates(['day', 'symbol'])[['day', 'symbol', 'sym']]
    df = df.merge(first, on=['day', 'symbol', 'sym'])
    df['i'] = df.day.map(DIX).astype(int)
    df['j'] = df.symbol.map(SYM).astype(int)
    return df


fut, opt, atm = map_frame(fut), map_frame(opt), map_frame(atm)
P(f'mapped to panel symbols: fut {len(fut)} rows / {fut.symbol.nunique()} symbols; opt {len(opt)}; atm {len(atm)}')


def mat(df, col):
    M = np.full((T, S), np.nan)
    M[df.i.to_numpy(), df.j.to_numpy()] = df[col].to_numpy(float)
    return M


OI = mat(fut, 'oi_tot')
UND = mat(fut, 'und')
CE_OI, PE_OI = mat(opt, 'ce_oi'), mat(opt, 'pe_oi')
OI[OI <= 0] = np.nan

# ------------------------------------------------------------------ split / demerger adjustment of OI (shares)
# g = log(raw underlying / adjusted price); a step |dg| > log(1.02) between consecutive observed sessions is a
# corporate action (split, bonus, demerger); OI is put in the units of the first observation.
G = np.log(UND) - np.log(PX)
ADJ = np.zeros((T, S))
n_steps = []
for j in range(S):
    idx = np.flatnonzero(np.isfinite(G[:, j]))
    if len(idx) < 2:
        continue
    dg = np.diff(G[idx, j])
    step = np.where(np.abs(dg) > np.log(1.02), dg, 0.0)     # prereg: step changes > 2%
    cum = np.concatenate([[0.0], np.cumsum(step)])
    col = np.full(T, np.nan)
    col[idx] = cum
    col = pd.Series(col).ffill().fillna(0.0).to_numpy()
    ADJ[:, j] = col
    for k_ in np.flatnonzero(step):
        n_steps.append((SYMS[j], days[idx[k_ + 1]], round(float(np.exp(step[k_])), 4)))
P(f'corporate-action steps applied to OI: {len(n_steps)}')
for x in n_steps:
    P('   ', x)
OIA = OI * np.exp(ADJ)


def chg(M, L, pct=True):
    out = np.full((T, S), np.nan)
    if pct:
        out[L:] = (M[L:] / M[:-L] - 1) * 100
    else:
        out[L:] = M[L:] - M[:-L]
    return out


dOI = {L: chg(OIA, L) for L in (1, 5, 10)}
dP = {L: chg(PX, L) for L in (1, 5, 10)}
dP_valid = {}
for L in (1, 5, 10):          # price change only where the stock has a price at both ends (returns not all NaN)
    dP[L][np.isnan(OIA)] = np.nan


def roll_prev(M, w, minp, fn):
    """statistic over the previous w sessions (i-w .. i-1), per column."""
    df = pd.DataFrame(M)
    r = df.shift(1).rolling(w, min_periods=minp)
    return (r.mean() if fn == 'mean' else r.median()).to_numpy()


OI20 = OIA / roll_prev(OIA, 20, 15, 'mean')

# ------------------------------------------------------------------ basis (front futures, >= 7 calendar days)
DAYD = np.array([date.fromisoformat(d).toordinal() for d in days])


def dte(col_day, col_exp):
    e = pd.to_datetime(col_exp, errors='coerce')
    d = pd.to_datetime(col_day)
    return (e - d).dt.days.to_numpy(float)


fut['dte1'] = dte(fut.day, fut.e1)
fut['dte2'] = dte(fut.day, fut.e2)
use1 = fut.dte1 >= 7
fut['f_settle'] = np.where(use1, fut.e1_settle, fut.e2_settle)
fut['f_dte'] = np.where(use1, fut.dte1, fut.dte2)
ok = (fut.f_settle > 0) & (fut.und > 0) & (fut.f_dte >= 7)
fut['basis'] = np.where(ok, (fut.f_settle / fut.und - 1) * 365 / fut.f_dte * 100, np.nan)
BASIS = mat(fut, 'basis')
BASISDEV = BASIS - roll_prev(BASIS, 60, 40, 'median')
dBASIS1 = chg(BASIS, 1, pct=False)

# ------------------------------------------------------------------ PCR
PCR = np.where(CE_OI > 0, PE_OI / CE_OI, np.nan)
dPCR5 = chg(PCR, 5, pct=False)
dPCR1 = chg(PCR, 1, pct=False)

# ------------------------------------------------------------------ ATM implied vol (Black-Scholes, r = 6.5%)
from math import sqrt  # noqa: E402
from scipy.special import ndtr  # noqa: E402


def bs(S_, K, T_, sig, call):
    v = sig * np.sqrt(T_)
    d1 = (np.log(S_ / K) + (R_RATE + 0.5 * sig * sig) * T_) / v
    d2 = d1 - v
    disc = K * np.exp(-R_RATE * T_)
    return np.where(call, S_ * ndtr(d1) - disc * ndtr(d2), disc * ndtr(-d2) - S_ * ndtr(-d1))


def implied_vol(price, S_, K, T_, call):
    price, S_, K, T_ = map(lambda a: np.asarray(a, float), (price, S_, K, T_))
    call = np.asarray(call, bool)
    disc = K * np.exp(-R_RATE * T_)
    lo_b = np.where(call, np.maximum(S_ - disc, 0), np.maximum(disc - S_, 0))
    hi_b = np.where(call, S_, disc)
    ok_ = np.isfinite(price) & (price > lo_b) & (price < hi_b) & (T_ > 0)
    lo, hi = np.full(price.shape, 0.01), np.full(price.shape, 5.0)
    p_lo, p_hi = bs(S_, K, T_, lo, call), bs(S_, K, T_, hi, call)
    ok_ &= (price >= p_lo) & (price <= p_hi)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        pm = bs(S_, K, T_, mid, call)
        up = pm < price
        lo = np.where(up, mid, lo)
        hi = np.where(up, hi, mid)
    iv = 0.5 * (lo + hi) * 100
    return np.where(ok_, iv, np.nan)


a = atm.merge(fut[['day', 'symbol', 'und']], on=['day', 'symbol'], how='left')
a['dte'] = dte(a.day, a.expiry)
# front option expiry per (day, symbol)
ex = a[['day', 'symbol', 'expiry', 'dte']].drop_duplicates().sort_values(['day', 'symbol', 'expiry'])
ex['rk'] = ex.groupby(['day', 'symbol']).cumcount()
e1 = ex[ex.rk == 0].set_index(['day', 'symbol'])
e2 = ex[ex.rk == 1].set_index(['day', 'symbol'])
fr = e1[['expiry', 'dte']].rename(columns={'expiry': 'x1', 'dte': 'd1'}).join(
    e2[['expiry', 'dte']].rename(columns={'expiry': 'x2', 'dte': 'd2'}))
fr['front'] = np.where(fr.d1 >= 7, fr.x1, np.where(fr.d2 >= 7, fr.x2, None))
a = a.merge(fr[['front']].reset_index(), on=['day', 'symbol'])
a = a[(a.expiry == a.front) & (a.und > 0)].copy()
a['dist'] = (a.strike - a.und).abs()
a = a.sort_values(['day', 'symbol', 'dist', 'strike']).drop_duplicates(['day', 'symbol'])
Tm = a.dte.to_numpy(float) / 365.0
cu = (a.ce_ctr > 0) & (a.ce_settle > 0)
pu = (a.pe_ctr > 0) & (a.pe_settle > 0)
a['civ'] = np.where(cu, implied_vol(a.ce_settle.to_numpy(float), a.und, a.strike, Tm, np.ones(len(a), bool)), np.nan)
a['piv'] = np.where(pu, implied_vol(a.pe_settle.to_numpy(float), a.und, a.strike, Tm, np.zeros(len(a), bool)), np.nan)
a['iv'] = a[['civ', 'piv']].mean(axis=1)
P(f'ATM rows (front expiry, nearest strike): {len(a)}; call IV {a.civ.notna().mean():.1%}, put IV '
  f'{a.piv.notna().mean():.1%}, IV {a.iv.notna().mean():.1%}; median IV {a.iv.median():.1f}%, '
  f'median call-put spread {(a.civ - a.piv).median():+.2f}')
# quick sanity check of the solver
tp = bs(np.array([100.0]), np.array([100.0]), np.array([30 / 365]), np.array([0.3]), np.array([True]))
assert abs(implied_vol(tp, [100.0], [100.0], [30 / 365], [True])[0] - 30) < 1e-6
CIV, PIV, IV = mat(a, 'civ'), mat(a, 'piv'), mat(a, 'iv')
IVREL = IV / roll_prev(IV, 60, 40, 'median')
IVSPREAD = CIV - PIV
dCIV20 = chg(CIV, 20, pct=False)
dPIV20 = chg(PIV, 20, pct=False)

np.savez_compressed(f'{OUTD}/daily.npz', OIA=OIA, UND=UND, BASIS=BASIS, PCR=PCR, IV=IV, CIV=CIV, PIV=PIV,
                    syms=np.array(SYMS), days=np.array(days))

FEATS = {'dOI1': dOI[1], 'dOI5': dOI[5], 'dOI10': dOI[10], 'dP1': dP[1], 'dP5': dP[5], 'dP10': dP[10],
         'OI20': OI20, 'BASIS': BASIS, 'BASISDEV': BASISDEV, 'dBASIS1': dBASIS1, 'PCR': PCR, 'dPCR5': dPCR5,
         'dPCR1': dPCR1, 'IV': IV, 'IVREL': IVREL, 'IVSPREAD': IVSPREAD, 'dCIV20': dCIV20, 'dPIV20': dPIV20}


def at(ii, jj, prefix=''):
    ii, jj = np.asarray(ii, int), np.asarray(jj, int)
    okk = (ii >= 0) & (ii < T)
    out = {}
    for k_, M in FEATS.items():
        v = np.full(len(ii), np.nan)
        v[okk] = M[ii[okk], jj[okk]]
        out[prefix + k_] = v
    return pd.DataFrame(out)


# ------------------------------------------------------------------ signal flags
QF_A = ['OI20', 'BASISDEV', 'PCR', 'dPCR5', 'IVREL', 'IVSPREAD', 'dCIV20', 'dPIV20']
QF_B = ['OI20', 'BASISDEV', 'dBASIS1', 'PCR', 'dPCR1', 'IVREL', 'IVSPREAD', 'dCIV20', 'dPIV20']


def cutoffs(df, cols, grp):
    """80th / 20th percentile per group, as columns <c>_q80 / <c>_q20."""
    out = pd.DataFrame(index=df.index)
    for c in cols:
        g = df.groupby(grp)[c]
        out[c + '_q80'] = g.transform(lambda s: s.quantile(0.8))
        out[c + '_q20'] = g.transform(lambda s: s.quantile(0.2))
    return out


def flags_A(X, C, p=''):
    """X: feature frame with prefix p; C: cut-off frame. returns {test: (signal, eligible)}."""
    f = {}
    for L, base in ((5, 1), (10, 5)):
        dp, do = X[f'{p}dP{L}'], X[f'{p}dOI{L}']
        el = dp.notna() & do.notna()
        f[f'A{base:02d}'] = ((dp > 0) & (do > 10), el)
        f[f'A{base + 1:02d}'] = ((dp < 0) & (do > 10), el)
        f[f'A{base + 2:02d}'] = ((dp > 0) & (do < -10), el)
        f[f'A{base + 3:02d}'] = ((dp < 0) & (do < -10), el)
    spec = [('A09', 'OI20', 'top'), ('A10', 'OI20', 'bot'), ('A11', 'BASISDEV', 'top'), ('A12', 'BASISDEV', 'bot'),
            ('A13', 'PCR', 'top'), ('A14', 'PCR', 'bot'), ('A15', 'dPCR5', 'top'), ('A16', 'dPCR5', 'bot'),
            ('A17', 'IVREL', 'top'), ('A18', 'IVREL', 'bot'), ('A19', 'IVSPREAD', 'top'),
            ('A20', 'IVSPREAD', 'bot'), ('A21', 'dCIV20', 'top'), ('A22', 'dPIV20', 'top')]
    for t, c, side in spec:
        v = X[p + c]
        el = v.notna() & C[c + '_q80'].notna()
        sig = (v > C[c + '_q80']) if side == 'top' else (v <= C[c + '_q20'])
        f[t] = (sig, el)
    return {k: ((s & e).fillna(False).to_numpy(bool), e.fillna(False).to_numpy(bool)) for k, (s, e) in f.items()}


def flags_B(X, C, Xpre):
    f = {}
    el = X.dOI1.notna()
    f['B01'] = (X.dOI1 > 0, el)
    f['B02'] = (X.dOI1 > 10, el)
    el = X.dP5.notna() & X.dOI5.notna()
    f['B03'] = ((X.dP5 > 0) & (X.dOI5 > 10), el)
    el = X.dP10.notna() & X.dOI10.notna()
    f['B04'] = ((X.dP10 > 0) & (X.dOI10 > 10), el)
    el = Xpre.dP5.notna() & Xpre.dOI5.notna()
    f['B05'] = ((Xpre.dP5 < 0) & (Xpre.dOI5 > 10), el)
    spec = [('B06', 'OI20', 'top'), ('B07', 'BASISDEV', 'top'), ('B08', 'dBASIS1', 'top'), ('B09', 'PCR', 'top'),
            ('B10', 'dPCR1', 'top'), ('B11', 'IVREL', 'bot'), ('B12', 'IVSPREAD', 'top'), ('B13', 'dCIV20', 'top'),
            ('B14', 'dPIV20', 'bot')]
    for t, c, side in spec:
        v = X[c]
        e = v.notna() & C[c + '_q80'].notna()
        f[t] = ((v > C[c + '_q80']) if side == 'top' else (v <= C[c + '_q20']), e)
    return {k: ((pd.Series(s).reset_index(drop=True) & pd.Series(e).reset_index(drop=True)).fillna(False).to_numpy(bool),
                pd.Series(e).reset_index(drop=True).fillna(False).to_numpy(bool)) for k, (s, e) in f.items()}


def add_flags(base, fl, suffix=''):
    for k_, (s, e) in fl.items():
        base[k_ + suffix] = s
        base['el_' + k_ + suffix] = e
    return base


# ------------------------------------------------------------------ results rows
pan = pd.read_csv(f'{SP}/perf/features/panel.csv',
                  usecols=['symbol', 'qn', 'quarter', 'period', 'i_cut', 'i_rd', 'i_react', 'in_fo_events',
                           'lag21', 'vol_ratio_5_60', 'cut_rsi14', 'XN', 'W'])
assert len(pan) == 3280
J = pan.symbol.map(SYM).to_numpy(int)
XA = at(pan.i_cut, J)
XA1 = at(pan.i_cut - 1, J)
XB = at(pan.i_react, J)
res = pan.copy()
for X_, pre in ((XA, 'A_'), (XA1, 'A1_'), (XB, 'B_')):
    for c in X_.columns:
        res[pre + c] = X_[c].to_numpy()
# A flags: cut-offs within quarter over all F&O results (at i_cut); robustness variants
CA = cutoffs(XA.assign(qn=pan.qn), QF_A, 'qn')
CA1 = cutoffs(XA1.assign(qn=pan.qn), QF_A, 'qn')
add_flags(res, flags_A(XA, CA))
add_flags(res, flags_A(XA1, CA1), '_lag1')


def prev_q_cutoffs(X, cols, qn):
    """strictly point in time: cut-offs of the previous quarter's results (qn 0 keeps its own)."""
    out = pd.DataFrame(index=X.index)
    for c in cols:
        q80 = X[c].groupby(qn).quantile(0.8)
        q20 = X[c].groupby(qn).quantile(0.2)
        m80 = {q: q80.get(q - 1, q80[q]) for q in q80.index}
        m20 = {q: q20.get(q - 1, q20[q]) for q in q20.index}
        out[c + '_q80'] = qn.map(m80).to_numpy()
        out[c + '_q20'] = qn.map(m20).to_numpy()
    return out


add_flags(res, flags_A(XA, prev_q_cutoffs(XA, QF_A, pan.qn)), '_pq')
# B flags (cut-offs within quarter over all F&O results at their own k)
CB = cutoffs(XB.assign(qn=pan.qn), QF_B, 'qn')
add_flags(res, flags_B(XB, CB, XA))
add_flags(res, flags_B(XB, prev_q_cutoffs(XB, QF_B, pan.qn), XA), '_pq')
res.to_csv(f'{OUTD}/results_features.csv', index=False, float_format='%.6g')

cov = []
for q, g in res.groupby('qn'):
    cov.append({'qn': q, 'results_for': f'Results for {g.period.iloc[0]} ({g.quarter.iloc[0]})', 'n': len(g),
                'oi_at_cut': int(g.A_dOI5.notna().sum()), 'basis_at_cut': int(g.A_BASISDEV.notna().sum()),
                'pcr_at_cut': int(g.A_PCR.notna().sum()), 'ivrel_at_cut': int(g.A_IVREL.notna().sum()),
                'ivspread_at_cut': int(g.A_IVSPREAD.notna().sum()), 'oi_at_k': int(g.B_dOI1.notna().sum()),
                'ivrel_at_k': int(g.B_IVREL.notna().sum())})
cov = pd.DataFrame(cov)
cov.to_csv(f'{OUTD}/coverage.csv', index=False)
P('\ncoverage by quarter (results rows with the feature):')
P(cov.to_string(index=False))

# ------------------------------------------------------------------ trade-A placebo days (features only)
pl = pd.read_csv(f'{SP}/ta/build/placebo_ta.csv.gz', usecols=['symbol', 'day', 'i', 'in_fo', 'qn_prev', 'qn_next'])
pl = pl[(pl.in_fo == True) & pl.qn_next.notna()].copy()
pl['qn_next'] = pl.qn_next.astype(int)
keys = set(zip(pan.symbol, pan.qn))
pl = pl[[(s, q) in keys for s, q in zip(pl.symbol, pl.qn_next)]]
pl = pl[pl.symbol.isin(SYM)].reset_index(drop=True)
P(f'\ntrade-A placebo days: {len(pl)} (expected 115909)')
XP = at(pl.i, pl.symbol.map(SYM))
CP = cutoffs(XP.assign(g=pl.qn_next.to_numpy()), QF_A, 'g')
outA = pl[['symbol', 'day', 'i', 'qn_next']].copy()
for c in XP.columns:
    outA[c] = XP[c].to_numpy()
add_flags(outA, flags_A(XP, CP))
outA.to_csv(f'{OUTD}/placebo_A_features.csv.gz', index=False, float_format='%.6g', compression='gzip')

# ------------------------------------------------------------------ trade-B placebo days (quiet days; features only)
qd = pd.read_csv(f'{SP}/tafa/C_post_results/quiet_days.csv.gz', usecols=['symbol', 'i', 'day', 'qn_prev', 'XN', 'W',
                                                                          'm2_rsi14'])
qd = qd[qd.symbol.isin(SYM)].reset_index(drop=True)
jq = qd.symbol.map(SYM).to_numpy(int)
XQ = at(qd.i, jq)
XQpre = at(qd.i - 2, jq)
month = qd.day.str[:7].to_numpy()
CQ = cutoffs(XQ.assign(g=month), QF_B, 'g')
outB = qd.copy()
for c in XQ.columns:
    outB[c] = XQ[c].to_numpy()
add_flags(outB, flags_B(XQ, CQ, XQpre))
outB.to_csv(f'{OUTD}/placebo_B_features.csv.gz', index=False, float_format='%.6g', compression='gzip')
P(f'trade-B placebo (quiet) days: {len(qd)}, quiet winners {int(qd.W.sum())}')

# ------------------------------------------------------------------ feature-only counts (no outcome)
W = (pan.W == True).to_numpy()
WR = W & (pan.cut_rsi14 > 50).to_numpy()
P('\nsignal counts - results rows (all 3,280) / placebo-A days | B: winners W / RSI winners WR / quiet winners')
for t in [f'A{k:02d}' for k in range(1, 23)]:
    P(f'  {t}: {int(res[t].sum()):5d} (eligible {int(res["el_" + t].sum())}) / {int(outA[t].sum()):6d}')
QW = outB.W.to_numpy(bool)
for t in [f'B{k:02d}' for k in range(1, 15)]:
    P(f'  {t}: W {int((res[t] & W).sum()):4d} (eligible {int((res["el_" + t] & W).sum())}) / WR {int((res[t] & WR).sum()):4d}'
      f' / quiet winners {int((outB[t] & QW).sum()):4d} (eligible {int((outB["el_" + t] & QW).sum())})')
P('\nfeature medians at i_cut (results) vs placebo-A days:')
for c in XA.columns:
    P(f'  {c:9s} {np.nanmedian(XA[c]):+9.3f} {np.nanmedian(XP[c]):+9.3f}')
P('done')
