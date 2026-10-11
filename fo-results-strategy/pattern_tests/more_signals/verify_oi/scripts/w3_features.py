#!/usr/bin/env python3
"""Verifier, own code: daily F&O positioning matrices + point-in-time features from MY raw downloads
(downloads/my_fo.db v-tables for days up to 2023-04-10, downloads/w_fo.db w-tables for the later days).
No outcome is read here.

usage: python3 w3_features.py <scratchpad> <verify_dir>
outputs (verify_dir/work): w_daily.npz, w_results_features.csv, w3_features.log
"""
import csv
import sqlite3
import sys
from datetime import date, datetime

import numpy as np
import pandas as pd
from scipy.special import ndtr

SP, VD = sys.argv[1], sys.argv[2]
W = f'{VD}/work'
LOG = open(f'{W}/w3_features.log', 'w')
RATE = 0.065


def log(*a):
    s = ' '.join(map(str, a))
    print(s, flush=True)
    LOG.write(s + '\n')
    LOG.flush()


ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv')
DAYS = ses.day.tolist()
T = len(DAYS)
DI = {d: i for i, d in enumerate(DAYS)}
ret = pd.read_csv(f'{SP}/sector_lab/data/returns.csv', index_col=0)
assert ret.index.tolist() == DAYS
SY = ret.columns.tolist()
NS = len(SY)
SJ = {s: j for j, s in enumerate(SY)}
RET = ret.to_numpy(float)
PX = np.cumprod(1 + np.nan_to_num(RET), axis=0)

# ---------------------------------------------------------------- my ticker resolver
chg = {}
with open(f'{SP}/symbolchange.csv', encoding='latin-1') as fh:
    for row in csv.reader(fh):
        if len(row) < 4:
            continue
        try:
            dt = datetime.strptime(row[3].strip().title(), '%d-%b-%Y').date().isoformat()
        except ValueError:
            continue
        chg.setdefault(row[1].strip(), []).append((dt, row[2].strip()))


def to_panel(raw, d):
    s, hops = raw, 0
    while s in chg and hops < 10:
        later = sorted(x for x in chg[s] if x[0] > d)
        if not later:
            break
        s = later[0][1]
        hops += 1
    return s


# ---------------------------------------------------------------- load raw tables (two sources)
A = sqlite3.connect(f'{VD}/downloads/my_fo.db')
B = sqlite3.connect(f'{VD}/downloads/w_fo.db')
wdays = {r[0] for r in B.execute('SELECT day FROM wdone WHERE ok=1')}
vdays = {r[0] for r in A.execute('SELECT day FROM vdone WHERE ok=1')}
want = [d for d in DAYS[1262:2697]]
src = {d: ('w' if d in wdays else ('v' if d in vdays else None)) for d in want}
log('sessions 1262..2696:', len(want), 'from w_fo', sum(v == 'w' for v in src.values()), 'from my_fo',
    sum(v == 'v' for v in src.values()), 'missing', [d for d, v in src.items() if v is None])


def load(tv, tw):
    a = pd.read_sql(f'SELECT * FROM {tv}', A)
    b = pd.read_sql(f'SELECT * FROM {tw}', B)
    a = a[a.day.map(src) == 'v']
    b = b[b.day.map(src) == 'w']
    return pd.concat([a, b], ignore_index=True)


fut = load('vfut', 'wfut')
opt = load('vopt', 'wopt')
und = load('vund', 'wund')
atm = load('vatm', 'watm')
log('raw rows fut', len(fut), 'opt', len(opt), 'und', len(und), 'atm', len(atm))


def mapsym(df):
    k = df[['day', 'sym']].drop_duplicates().copy()
    k['symbol'] = [to_panel(s, d) for s, d in zip(k.sym, k.day)]
    df = df.merge(k, on=['day', 'sym'])
    df = df[df.symbol.isin(SJ)].copy()
    # if two raw tickers land on one panel symbol on a day keep the one equal to the panel symbol
    dup = df[['day', 'symbol', 'sym']].drop_duplicates()
    dup = dup.assign(pref=(dup.sym == dup.symbol).astype(int)).sort_values('pref', ascending=False)
    keep = dup.drop_duplicates(['day', 'symbol'])
    nd = len(dup) - len(keep)
    df = df.merge(keep[['day', 'symbol', 'sym']], on=['day', 'symbol', 'sym'])
    df['i'] = df.day.map(DI).astype(int)
    df['j'] = df.symbol.map(SJ).astype(int)
    return df, nd


fut, n1 = mapsym(fut)
opt, n2 = mapsym(opt)
und, n3 = mapsym(und)
atm, n4 = mapsym(atm)
log('mapped: fut symbols', fut.symbol.nunique(), '| duplicate raw tickers dropped', n1, n2, n3, n4)
renamed = fut[fut.sym != fut.symbol][['sym', 'symbol']].drop_duplicates()
log('raw->panel renames used:', sorted(map(tuple, renamed.to_numpy().tolist())))


def M(df, col):
    X = np.full((T, NS), np.nan)
    X[df.i.to_numpy(), df.j.to_numpy()] = df[col].to_numpy(float)
    return X


UND = M(und, 'und')
UND[UND <= 0] = np.nan
fo = fut.groupby(['i', 'j']).oi.sum().reset_index()
OI = M(fo, 'oi')
OI[OI <= 0] = np.nan
CE = M(opt, 'ce_oi')
PE = M(opt, 'pe_oi')

# corporate-action steps (> 2%) in raw underlying vs adjusted price -> OI in constant share units
LG = np.log(UND) - np.log(PX)
STEP = np.zeros((T, NS))
steps = []
for j in range(NS):
    ix = np.flatnonzero(np.isfinite(LG[:, j]) & np.isfinite(OI[:, j]))
    if len(ix) < 2:
        continue
    d = np.diff(LG[ix, j])
    big = np.abs(d) > np.log(1.02)
    c = np.zeros(T)
    for k in np.flatnonzero(big):
        c[ix[k + 1]:] += d[k]
        steps.append((SY[j], DAYS[ix[k + 1]], round(float(np.exp(d[k])), 4)))
    STEP[:, j] = c
log('corporate-action steps:', len(steps))
for s in steps:
    log('   ', s)
OIA = OI * np.exp(STEP)


def lagdiff(X, L, pct):
    Y = np.full_like(X, np.nan)
    Y[L:] = (X[L:] / X[:-L] - 1) * 100 if pct else X[L:] - X[:-L]
    return Y


def trailing(X, w, minp, how):
    df = pd.DataFrame(X).shift(1).rolling(w, min_periods=minp)
    return (df.mean() if how == 'mean' else df.median()).to_numpy()


F = {}
for L in (1, 5, 10):
    F[f'dOI{L}'] = lagdiff(OIA, L, True)
    p = lagdiff(PX, L, True)
    p[np.isnan(OIA)] = np.nan
    F[f'dP{L}'] = p
F['OI20'] = OIA / trailing(OIA, 20, 15, 'mean')

# front futures (>= 7 calendar days), basis annualised %
fut['dte'] = (pd.to_datetime(fut.expiry) - pd.to_datetime(fut.day)).dt.days
fut = fut.sort_values(['i', 'j', 'expiry'])
fut['rk'] = fut.groupby(['i', 'j']).cumcount()
f1 = fut[fut.rk == 0].set_index(['i', 'j'])
f2 = fut[fut.rk == 1].set_index(['i', 'j'])
fr = f1[['settle', 'dte']].join(f2[['settle', 'dte']], rsuffix='2')
fr['fs'] = np.where(fr.dte >= 7, fr.settle, fr.settle2)
fr['fd'] = np.where(fr.dte >= 7, fr.dte, fr.dte2)
fr = fr.reset_index()
FS, FD = M(fr, 'fs'), M(fr, 'fd')
ok = (FS > 0) & (UND > 0) & (FD >= 7)
F['BASIS'] = np.where(ok, (FS / UND - 1) * 365 / FD * 100, np.nan)
F['BASISDEV'] = F['BASIS'] - trailing(F['BASIS'], 60, 40, 'median')
F['dBASIS1'] = lagdiff(F['BASIS'], 1, False)
F['PCR'] = np.where(CE > 0, PE / CE, np.nan)
F['dPCR5'] = lagdiff(F['PCR'], 5, False)
F['dPCR1'] = lagdiff(F['PCR'], 1, False)


# ATM implied vol, own Black-Scholes and bisection
def bs_price(S, K, t, v, is_call):
    sd = v * np.sqrt(t)
    d1 = (np.log(S / K) + (RATE + v * v / 2) * t) / sd
    d2 = d1 - sd
    pv = K * np.exp(-RATE * t)
    c = S * ndtr(d1) - pv * ndtr(d2)
    return np.where(is_call, c, c - S + pv)          # put by parity


def solve_iv(px, S, K, t, is_call):
    lo = np.full(px.shape, 0.01)
    hi = np.full(px.shape, 5.0)
    good = np.isfinite(px) & (px > 0) & (t > 0) & (bs_price(S, K, t, lo, is_call) <= px) & \
        (bs_price(S, K, t, hi, is_call) >= px)
    for _ in range(70):
        m = (lo + hi) / 2
        above = bs_price(S, K, t, m, is_call) > px
        hi = np.where(above, m, hi)
        lo = np.where(above, lo, m)
    return np.where(good, (lo + hi) / 2 * 100, np.nan)


chk = bs_price(np.array([100.]), np.array([105.]), np.array([0.1]), np.array([0.25]), np.array([False]))
assert abs(solve_iv(chk, np.array([100.]), np.array([105.]), np.array([0.1]), np.array([False]))[0] - 25) < 1e-5
a = atm.merge(und[['i', 'j', 'und']], on=['i', 'j'])
a['dte'] = (pd.to_datetime(a.expiry) - pd.to_datetime(a.day)).dt.days
ex = a[['i', 'j', 'expiry', 'dte']].drop_duplicates().sort_values(['i', 'j', 'expiry'])
ex['rk'] = ex.groupby(['i', 'j']).cumcount()
e = ex[ex.rk == 0].set_index(['i', 'j'])[['expiry', 'dte']].join(
    ex[ex.rk == 1].set_index(['i', 'j'])[['expiry', 'dte']], rsuffix='2')
e['front'] = np.where(e.dte >= 7, e.expiry, np.where(e.dte2 >= 7, e.expiry2, None))
a = a.merge(e[['front']].reset_index(), on=['i', 'j'])
a = a[a.expiry == a.front]
a['dist'] = (a.strike - a.und).abs()
kk = a[['i', 'j', 'strike', 'dist']].drop_duplicates().sort_values(['i', 'j', 'dist', 'strike']).drop_duplicates(['i', 'j'])
a = a.merge(kk[['i', 'j', 'strike']], on=['i', 'j', 'strike'])
legs = {}
for ot in ('CE', 'PE'):
    x = a[a.otype == ot].drop_duplicates(['i', 'j']).copy()
    use = (x.ctr > 0) & (x.settle > 0)
    x['iv'] = np.where(use, solve_iv(x.settle.to_numpy(float), x.und.to_numpy(float), x.strike.to_numpy(float),
                                     x.dte.to_numpy(float) / 365, np.full(len(x), ot == 'CE')), np.nan)
    legs[ot] = M(x, 'iv')
CIV, PIV = legs['CE'], legs['PE']
IV = np.nanmean(np.stack([CIV, PIV]), axis=0)
log(f'ATM: call IV present {np.isfinite(CIV).sum()}, put IV {np.isfinite(PIV).sum()}, IV {np.isfinite(IV).sum()} '
    f'of {np.isfinite(UND).sum()} stock-days with underlying; median IV {np.nanmedian(IV):.1f}')
F['IV'] = IV
F['IVREL'] = IV / trailing(IV, 60, 40, 'median')
F['IVSPREAD'] = CIV - PIV
F['dCIV20'] = lagdiff(CIV, 20, False)
F['dPIV20'] = lagdiff(PIV, 20, False)
# extra (verification only): PCR vs the stock's own trailing 60-session median; same-day cross-sectional rank
F['PCRREL'] = F['PCR'] / trailing(F['PCR'], 60, 40, 'median')
F['PCR_XS'] = pd.DataFrame(F['PCR']).rank(axis=1, pct=True).to_numpy()
F['NOTIONAL'] = OI * UND / 1e7     # futures OI notional, Rs crore (size proxy)

np.savez_compressed(f'{W}/w_daily.npz', **F, OIA=OIA, UND=UND, CE=CE, PE=PE, CIV=CIV, PIV=PIV, syms=np.array(SY),
                    days=np.array(DAYS))

pan = pd.read_csv(f'{SP}/perf/features/panel.csv', usecols=['symbol', 'qn', 'quarter', 'period', 'i_cut', 'i_react'])
jj = pan.symbol.map(SJ).to_numpy(int)
out = pan.copy()
for tag, ii in (('A_', pan.i_cut.to_numpy()), ('A1_', pan.i_cut.to_numpy() - 1), ('B_', pan.i_react.to_numpy()),
                ('Bm1_', pan.i_react.to_numpy() - 1)):
    for k, X in F.items():
        out[tag + k] = X[ii, jj]
out.to_csv(f'{W}/w_results_features.csv', index=False, float_format='%.6g')
cov = out.groupby('qn').agg(n=('symbol', 'size'), oi_cut=('A_dOI5', 'count'), pcr_k=('B_PCR', 'count'),
                            civ20_k=('B_dCIV20', 'count'), basisdev_cut=('A_BASISDEV', 'count'))
log(cov.to_string())
log('done')
