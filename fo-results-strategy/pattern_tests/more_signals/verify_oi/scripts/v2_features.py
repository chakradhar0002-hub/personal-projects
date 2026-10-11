#!/usr/bin/env python3
"""Verifier - own point-in-time F&O features from my own re-download (my_fo.db). Reads no outcome.

usage: python3 -P v2_features.py <my_fo.db> <scratchpad> <out_dir>
Writes out_dir/my_daily.npz and out_dir/my_results_features.csv (+ placebo feature files) and my_features.log.
Definitions follow the family's prereg.txt text (re-implemented, not copied):
  OI = futures OI summed over all live expiries, split-adjusted by step changes (>2%) of raw close / adjusted close;
  front contract = nearest expiry with >= 7 calendar days (else next); basis annualised; PCR = put OI / call OI all
  strikes+expiries; ATM IV from settle prices of traded legs at the strike nearest the underlying (tie -> lower), BS r=6.5%.
"""
import csv
import sqlite3
import sys
from datetime import date, datetime

import numpy as np
import pandas as pd
from scipy.stats import norm

DB, SP, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
LOG = open(f'{OUT}/my_features.log', 'w')


def log(*a):
    s = ' '.join(map(str, a))
    print(s, flush=True)
    LOG.write(s + '\n')


ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv')
DAYS = ses.day.tolist()
IX = {d: i for i, d in enumerate(DAYS)}
T = len(DAYS)
ret = pd.read_csv(f'{SP}/sector_lab/data/returns.csv', index_col=0)
SYMS = list(ret.columns)
JX = {s: j for j, s in enumerate(SYMS)}
S = len(SYMS)
ADJPX = np.cumprod(1 + np.nan_to_num(ret.to_numpy(float)), axis=0)
ADJPX[np.isnan(ret.to_numpy(float))] = np.nan

# ---- renames: old -> [(date, new)]
REN = {}
with open(f'{SP}/symbolchange.csv', encoding='latin-1') as fh:
    for row in csv.reader(fh):
        if len(row) < 4:
            continue
        try:
            dd = datetime.strptime(row[3].strip().upper(), '%d-%b-%Y').date().isoformat()
        except ValueError:
            continue
        REN.setdefault(row[1].strip(), []).append((dd, row[2].strip()))


def to_panel(sym, d):
    for _ in range(10):
        later = sorted(x for x in REN.get(sym, []) if x[0] > d)
        if not later:
            return sym
        sym = later[0][1]
    return sym


db = sqlite3.connect(DB)
vd = pd.read_sql('select * from vdone', db)
log('days ok', int(vd.ok.sum()), 'missing', vd.day[vd.ok == 0].tolist())
fut = pd.read_sql('select * from vfut', db)
opt = pd.read_sql('select * from vopt', db)
und = pd.read_sql('select * from vund', db)
atm = pd.read_sql('select * from vatm', db)
log('raw rows fut', len(fut), 'opt', len(opt), 'und', len(und), 'atm', len(atm))

keys = pd.concat([fut[['day', 'sym']], opt[['day', 'sym']]]).drop_duplicates()
keys['panel'] = [to_panel(s, d) for s, d in zip(keys.sym, keys.day)]
keys = keys[keys.panel.isin(JX) & keys.day.isin(IX)]
# conflicts: two raw tickers -> same panel symbol on the same day
cnt = keys.groupby(['day', 'panel']).sym.nunique()
conf = cnt[cnt > 1]
log('raw->panel conflicts (day, symbol with >1 raw ticker):', len(conf), conf.reset_index().head(10).values.tolist())
keys['own'] = (keys.sym == keys.panel).astype(int)
keys = keys.sort_values('own', ascending=False).drop_duplicates(['day', 'panel'])
renamed = keys[keys.sym != keys.panel].groupby(['sym', 'panel']).day.agg(['min', 'max', 'count'])
log('renamed raw tickers used:\n' + renamed.to_string())
KM = keys.set_index(['day', 'sym']).panel


def attach(df):
    df = df.join(KM, on=['day', 'sym'], how='inner')
    df['i'] = df.day.map(IX).astype(int)
    df['j'] = df.panel.map(JX).astype(int)
    return df


fut, opt, und, atm = attach(fut), attach(opt), attach(und), attach(atm)


def M(df, col):
    A = np.full((T, S), np.nan)
    A[df.i.to_numpy(), df.j.to_numpy()] = df[col].to_numpy(float)
    return A


# ---- futures aggregates
fut = fut[fut.expiry >= fut.day]
ftot = fut.groupby(['day', 'panel', 'i', 'j'], as_index=False).oi.sum()
OI = M(ftot, 'oi')
OI[OI <= 0] = np.nan
UND = M(und, 'und')
UND[UND <= 0] = np.nan

# split adjustment: steps > 2% in log(raw close / adjusted close) between consecutive observations
LR = np.log(UND / ADJPX)
OIA = np.full((T, S), np.nan)
nstep = []
for j in range(S):
    ii = np.flatnonzero(np.isfinite(LR[:, j]))
    if len(ii) == 0:
        continue
    d = np.diff(LR[ii, j])
    st = np.where(np.abs(d) > np.log(1.02), d, 0.0)
    cc = np.full(T, np.nan)
    cc[ii] = np.r_[0.0, np.cumsum(st)]
    cc = pd.Series(cc).ffill().fillna(0.0).to_numpy()
    OIA[:, j] = OI[:, j] * np.exp(cc)
    for k in np.flatnonzero(st):
        nstep.append((SYMS[j], DAYS[ii[k + 1]], round(float(np.exp(st[k])), 3)))
log('split steps', len(nstep))
for x in nstep:
    log('  ', x)

# front futures (>= 7 calendar days)
fut['dte'] = (pd.to_datetime(fut.expiry) - pd.to_datetime(fut.day)).dt.days
ff = fut[fut.dte >= 7].sort_values(['day', 'panel', 'expiry']).drop_duplicates(['day', 'panel'])
ff = ff.merge(und[['day', 'panel', 'und']], on=['day', 'panel'])
ff = ff[(ff.settle > 0) & (ff.und > 0)]
ff['basis'] = (ff.settle / ff.und - 1) * 365 / ff.dte * 100
BASIS = M(ff, 'basis')

# PCR
opt['pcr'] = np.where(opt.ce_oi > 0, opt.pe_oi / opt.ce_oi.where(opt.ce_oi > 0), np.nan)
PCR = M(opt, 'pcr')

# ATM IV
atm['dte'] = (pd.to_datetime(atm.expiry) - pd.to_datetime(atm.day)).dt.days
ex = atm[['day', 'panel', 'expiry', 'dte']].drop_duplicates().sort_values(['day', 'panel', 'expiry'])
ex['ok7'] = ex.dte >= 7
front = ex[ex.ok7].drop_duplicates(['day', 'panel'])[['day', 'panel', 'expiry']]
a = atm.merge(front, on=['day', 'panel', 'expiry']).merge(und[['day', 'panel', 'und']], on=['day', 'panel'])
a['dist'] = (a.strike - a.und).abs()
best = a.sort_values(['day', 'panel', 'dist', 'strike']).drop_duplicates(['day', 'panel'])[['day', 'panel', 'strike']]
a = a.merge(best, on=['day', 'panel', 'strike'])
r = 0.065


def bs_price(S_, K, t, v, call):
    sd = v * np.sqrt(t)
    d1 = (np.log(S_ / K) + (r + v * v / 2) * t) / sd
    d2 = d1 - sd
    c = S_ * norm.cdf(d1) - K * np.exp(-r * t) * norm.cdf(d2)
    return np.where(call, c, c - S_ + K * np.exp(-r * t))     # put via parity


def iv_solve(p, S_, K, t, call):
    lo = np.full(len(p), 0.01)
    hi = np.full(len(p), 5.0)
    plo, phi = bs_price(S_, K, t, lo, call), bs_price(S_, K, t, hi, call)
    ok = np.isfinite(p) & (p > plo) & (p < phi)
    for _ in range(70):
        mid = (lo + hi) / 2
        pm = bs_price(S_, K, t, mid, call)
        lo = np.where(pm < p, mid, lo)
        hi = np.where(pm < p, hi, mid)
    return np.where(ok, (lo + hi) / 2 * 100, np.nan)


a = a[(a.ctr > 0) & (a.settle > 0)].copy()
a['iv'] = iv_solve(a.settle.to_numpy(float), a.und.to_numpy(float), a.strike.to_numpy(float), a.dte.to_numpy(float) / 365,
                   (a.otype == 'CE').to_numpy())
civ = a[a.otype == 'CE'][['day', 'panel', 'i', 'j', 'iv']]
piv = a[a.otype == 'PE'][['day', 'panel', 'i', 'j', 'iv']]
CIV, PIV = M(civ, 'iv'), M(piv, 'iv')
IV = np.nanmean(np.stack([CIV, PIV]), axis=0)
log('IV coverage on stock-days with OI:', round(float(np.isfinite(IV[np.isfinite(OI)]).mean()), 4),
    'median IV', round(float(np.nanmedian(IV)), 2))


def lagdiff(A, L, pct):
    B = np.full_like(A, np.nan)
    B[L:] = (A[L:] / A[:-L] - 1) * 100 if pct else A[L:] - A[:-L]
    return B


def prev_stat(A, w, minp, how):
    df = pd.DataFrame(A).shift(1).rolling(w, min_periods=minp)
    return (df.mean() if how == 'mean' else df.median()).to_numpy()


F = {}
for L in (1, 5, 10):
    F[f'dOI{L}'] = lagdiff(OIA, L, True)
    dp = lagdiff(ADJPX, L, True)
    dp[np.isnan(OIA)] = np.nan
    F[f'dP{L}'] = dp
F['OI20'] = OIA / prev_stat(OIA, 20, 15, 'mean')
F['BASIS'] = BASIS
F['BASISDEV'] = BASIS - prev_stat(BASIS, 60, 40, 'median')
F['dBASIS1'] = lagdiff(BASIS, 1, False)
F['PCR'] = PCR
F['PCRREL'] = PCR / prev_stat(PCR, 60, 40, 'median')          # extra (not pre-registered): PCR vs own history
F['PCR_MED60'] = prev_stat(PCR, 60, 40, 'median')
F['dPCR1'] = lagdiff(PCR, 1, False)
F['dPCR5'] = lagdiff(PCR, 5, False)
F['IV'] = IV
F['IVREL'] = IV / prev_stat(IV, 60, 40, 'median')
F['CIV'] = CIV
F['PIV'] = PIV
F['IVSPREAD'] = CIV - PIV
F['dCIV20'] = lagdiff(CIV, 20, False)
F['dPIV20'] = lagdiff(PIV, 20, False)
np.savez_compressed(f'{OUT}/my_daily.npz', days=np.array(DAYS), syms=np.array(SYMS), OI=OI, OIA=OIA, UND=UND,
                    **{k: v for k, v in F.items()})


def take(ii, jj):
    ii, jj = np.asarray(ii, int), np.asarray(jj, int)
    ok = (ii >= 0) & (ii < T) & (jj >= 0)
    out = {}
    for k, A in F.items():
        v = np.full(len(ii), np.nan)
        v[ok] = A[ii[ok], jj[ok]]
        out[k] = v
    return pd.DataFrame(out)


pan = pd.read_csv(f'{SP}/perf/features/panel.csv', usecols=['symbol', 'qn', 'quarter', 'period', 'timing', 'i_cut', 'i_rd',
                                                              'i_react', 'in_fo', 'in_fo_events', 'lag21', 'vol_ratio_5_60',
                                                              'cut_rsi14', 'XN', 'W', 'industry'])
J = pan.symbol.map(JX).fillna(-1).astype(int).to_numpy()
out = pan.copy()
for pre, ii in (('A_', pan.i_cut), ('A1_', pan.i_cut - 1), ('B_', pan.i_react), ('Bm1_', pan.i_react - 1),
                ('Bp1_', pan.i_react + 1)):
    X = take(ii, J)
    for c in X.columns:
        out[pre + c] = X[c].to_numpy()
out.to_csv(f'{OUT}/my_results_features.csv', index=False, float_format='%.7g')
log('results rows', len(out), 'B_PCR present', int(out.B_PCR.notna().sum()), 'A_BASISDEV', int(out.A_BASISDEV.notna().sum()),
    'B_dCIV20', int(out.B_dCIV20.notna().sum()), 'A_dPIV20', int(out.A_dPIV20.notna().sum()))

qd = pd.read_csv(f'{SP}/tafa/C_post_results/quiet_days.csv.gz', usecols=['symbol', 'i', 'day', 'XN', 'W', 'm2_rsi14'])
qd = qd[qd.symbol.isin(JX)].reset_index(drop=True)
X = take(qd.i, qd.symbol.map(JX))
X1 = take(qd.i + 1, qd.symbol.map(JX))
for c in X.columns:
    qd['B_' + c] = X[c].to_numpy()
qd['Bp1_PCR'] = X1['PCR'].to_numpy()
qd.to_csv(f'{OUT}/my_quiet_features.csv.gz', index=False, float_format='%.7g', compression='gzip')
pl = pd.read_csv(f'{SP}/ta/build/placebo_ta.csv.gz', usecols=['symbol', 'day', 'i', 'in_fo', 'qn_next'])
pl = pl[(pl.in_fo == True) & pl.qn_next.notna() & pl.symbol.isin(JX)].reset_index(drop=True)
X = take(pl.i, pl.symbol.map(JX))
for c in ['BASISDEV', 'dPIV20', 'PCR', 'dPCR5']:
    pl['A_' + c] = X[c].to_numpy()
pl.to_csv(f'{OUT}/my_placeboA_features.csv.gz', index=False, float_format='%.7g', compression='gzip')
log('quiet days', len(qd), 'placebo A days', len(pl))
log('done')
