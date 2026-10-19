"""EMA / SMA features at every F&O result cutoff and every ordinary-day placebo signal day.

    LAB_ROOT=... TA_BUILD=... REPO_ROOT=... python3 -P build_features.py

Pre-registered in PLAN.txt (same folder; sha256 in PLAN.sha256). Reads (read-only):
    LAB/sector_lab/data/events.csv, sessions.csv
    TA/adjusted_ohlcv.csv.gz, TA/events_ta.csv, TA/placebo_ta.csv.gz
Writes into OUT (results/ema_sma_3day):
    features_events.csv       one row per F&O result (3,278): outcome + 59 features
    features_placebo.csv.gz   one row per in_fo placebo stock-day: symbol, i, qn, three_day + 59 features
    build.log                 validation numbers (appended to run.log by run_tests.py)

Conventions (= TA/build_panel.py): every MA runs on the stock's own traded days; SMA(n) = mean of the last n closes
incl. day k; EMA(n) = seeded with the mean of the first n closes, then alpha = 2/(n+1) (pandas ewm, adjust=False, on
the seed followed by the remaining closes, exactly as build_panel.seeded()). Close = raw_close x price_factor.
"""
import importlib.util
import os
import sys

import numpy as np
import pandas as pd

LAB = os.environ.get('LAB_ROOT', 'lab')
TA = os.environ.get('TA_BUILD', os.path.join(LAB, 'ta', 'build'))
OUT = os.environ.get('OUT', os.path.join(os.environ.get('REPO_ROOT', '.'), 'results', 'ema_sma_3day'))
PACK = os.path.join(LAB, 'sector_lab', 'data')

EMA_N = [5, 9, 10, 12, 20, 21, 26, 50, 100, 200]
SMA_N = [5, 10, 20, 50, 100, 200]
P = [5, 10, 20, 50, 100, 200]
PAIRS = [('ema9_21', 'E', 9, 21), ('ema12_26', 'E', 12, 26), ('ema20_50', 'E', 20, 50), ('ema50_200', 'E', 50, 200),
         ('sma20_50', 'S', 20, 50), ('sma50_200', 'S', 50, 200)]

CONT = ([f'dist_ema_{n}' for n in P] + [f'dist_sma_{n}' for n in P]
        + [f'slope_ema_{n}' for n in (20, 50, 200)] + [f'slope_sma_{n}' for n in (20, 50, 200)]
        + [f'ema_vs_sma_{n}' for n in (20, 50, 200)] + [f'spread_{p[0]}' for p in PAIRS])
BINARY = ([f'above_ema_{n}' for n in (20, 50, 200)] + [f'above_sma_{n}' for n in (20, 50, 200)]
          + [f'state_{p[0]}' for p in PAIRS] + [f'xup_{p[0]}' for p in PAIRS] + [f'xdn_{p[0]}' for p in PAIRS]
          + ['pxup_ema20', 'pxup_sma20', 'pxdn_ema20', 'pxdn_sma20']
          + ['bull_stack_ema', 'bear_stack_ema', 'bull_stack_sma', 'bear_stack_sma'])
FEATURES = CONT + BINARY
assert len(CONT) == 27 and len(BINARY) == 32

LOG = []


def log(msg=''):
    print(msg)
    LOG.append(msg)


# ----------------------------------------------------------------------------------------- moving averages
def ema(c, n):
    """build_panel.seeded(c, n, 2/(n+1), 0): seed = mean of the first n closes, then pandas ewm(adjust=False)."""
    out = np.full(len(c), np.nan)
    if len(c) < n:
        return out
    y = c[n - 1:].astype(float).copy()
    y[0] = c[:n].mean()
    out[n - 1:] = np.array(pd.Series(y).ewm(alpha=2 / (n + 1), adjust=False).mean(), dtype=float)
    return out


def sma(c, n):
    """build_panel.roll(c, n, 'mean')."""
    return np.array(pd.Series(c).rolling(n, min_periods=n).mean(), dtype=float)


def shift(x, k):
    out = np.full(len(x), np.nan)
    if k < len(x):
        out[k:] = x[:-k]
    return out


def flag(cond, defined):
    """1/0 where `defined`, NaN elsewhere."""
    return np.where(defined, cond.astype(float), np.nan)


def cross_within(fast, slow, window, up):
    """1 if, for some j in k-window+1..k, fast <= slow on j-1 and fast > slow on j (mirror when not up).
    NaN unless the pair is defined on k-window (so every j-1 in the window is defined)."""
    fp, sp = shift(fast, 1), shift(slow, 1)
    with np.errstate(invalid='ignore'):
        ev = ((fp <= sp) & (fast > slow)) if up else ((fp >= sp) & (fast < slow))
    ev = ev.astype(float)
    anyev = np.array(pd.Series(ev).rolling(window, min_periods=window).max(), dtype=float)
    defined = np.isfinite(shift(fast, window)) & np.isfinite(shift(slow, window))
    return np.where(defined & np.isfinite(anyev), anyev, np.nan)


def crossed_build(diff_, window, up):
    """build_panel.crossed(): used only to validate against golden_x10 / death_x10."""
    prev = shift(diff_, 1)
    with np.errstate(invalid='ignore'):
        ev = (diff_ > 0) & (prev <= 0) if up else (diff_ < 0) & (prev >= 0)
    out = np.array(pd.Series(ev.astype(float)).rolling(window, min_periods=1).max(), dtype=float)
    out[np.isnan(diff_)] = np.nan
    return out


def features(c):
    """All 59 features on one stock's traded closes (array without gaps) + validation series."""
    E = {n: ema(c, n) for n in EMA_N}
    S = {n: sma(c, n) for n in SMA_N}
    F = {}
    with np.errstate(invalid='ignore', divide='ignore'):
        for n in P:
            F[f'dist_ema_{n}'] = (c / E[n] - 1) * 100
            F[f'dist_sma_{n}'] = (c / S[n] - 1) * 100
        for n in (20, 50, 200):
            F[f'slope_ema_{n}'] = (E[n] / shift(E[n], 5) - 1) * 100
            F[f'slope_sma_{n}'] = (S[n] / shift(S[n], 5) - 1) * 100
        for n in (20, 50, 200):
            F[f'ema_vs_sma_{n}'] = (E[n] / S[n] - 1) * 100
        for name, kind, a, b in PAIRS:
            M = E if kind == 'E' else S
            F[f'spread_{name}'] = (M[a] / M[b] - 1) * 100
        for n in (20, 50, 200):
            F[f'above_ema_{n}'] = flag(c > E[n], np.isfinite(E[n]))
            F[f'above_sma_{n}'] = flag(c > S[n], np.isfinite(S[n]))
        for name, kind, a, b in PAIRS:
            M = E if kind == 'E' else S
            F[f'state_{name}'] = flag(M[a] > M[b], np.isfinite(M[a]) & np.isfinite(M[b]))
            F[f'xup_{name}'] = cross_within(M[a], M[b], 5, True)
            F[f'xdn_{name}'] = cross_within(M[a], M[b], 5, False)
        F['pxup_ema20'] = cross_within(c, E[20], 3, True)
        F['pxup_sma20'] = cross_within(c, S[20], 3, True)
        F['pxdn_ema20'] = cross_within(c, E[20], 3, False)
        F['pxdn_sma20'] = cross_within(c, S[20], 3, False)
        for kind, M in (('ema', E), ('sma', S)):
            ok = np.isfinite(M[200])
            F[f'bull_stack_{kind}'] = flag((c > M[20]) & (M[20] > M[50]) & (M[50] > M[200]), ok)
            F[f'bear_stack_{kind}'] = flag((c < M[20]) & (M[20] < M[50]) & (M[50] < M[200]), ok)
        V = {'macd_pct': (E[12] - E[26]) / c * 100,
             'golden_state': flag(S[50] > S[200], np.isfinite(S[200])),
             'golden_x10': crossed_build(S[50] - S[200], 10, True),
             'death_x10': crossed_build(S[50] - S[200], 10, False)}
    return F, V


def compute(px, want):
    """want: DataFrame(symbol, i) -> DataFrame of features (+ validation cols) aligned with want's index."""
    out = pd.DataFrame(np.nan, index=want.index, columns=FEATURES + ['_macd_pct', '_golden_state', '_golden_x10',
                                                                     '_death_x10', '_traded'])
    groups = want.groupby('symbol').groups
    for sym, g in px.groupby('symbol', sort=False):
        if sym not in groups:
            continue
        idx = groups[sym]
        ii = want.loc[idx, 'i'].to_numpy(int)
        rows = g.i.to_numpy(int)
        pos = np.searchsorted(rows, ii)
        hit = (pos < len(rows)) & (rows[np.minimum(pos, len(rows) - 1)] == ii)
        F, V = features(g.c.to_numpy(float))
        p = pos[hit]
        sel = np.asarray(idx)[hit]
        for k in FEATURES:
            out.loc[sel, k] = F[k][p]
        for k, v in V.items():
            out.loc[sel, '_' + k] = v[p]
        out.loc[sel, '_traded'] = 1.0
    out['_traded'] = out['_traded'].fillna(0.0)
    return out


# PLAN.txt said "+1e-9"; the stored inputs only allow ~1e-8 relative precision in C / MA (price_factor is stored with 8
# significant digits, so a split/bonus step inside the MA window carries up to ~5e-8 relative error). Slack is
# therefore 5e-6 percentage points (= 5e-8 in the ratio). Written in run.log DEVIATIONS.
SLACK = 5e-6
DEVIATIONS = []


def check_6g(mine, file_vals, name, where):
    """Pass rule: rel diff <= 1e-6 OR within half a unit of the file's 6th significant digit + SLACK (pct points)."""
    m = np.isfinite(mine) & np.isfinite(file_vals)
    a, b = mine[m], file_vals[m]
    d = np.abs(a - b)
    with np.errstate(divide='ignore', invalid='ignore'):
        rel = np.where(b != 0, d / np.abs(b), np.where(d == 0, 0.0, np.inf))
        half_unit = 0.5 * 10.0 ** (np.floor(np.log10(np.abs(np.where(b == 0, 1.0, b)))) - 5)
    ok = (rel <= 1e-6) | (d <= half_unit + SLACK)
    strict = int(((rel <= 1e-6) | (d <= half_unit + 1e-9)).sum())
    nan_mismatch = int((np.isfinite(mine) != np.isfinite(file_vals)).sum())
    log(f'  {where:7s} {name:26s} n={m.sum():6d}  max abs diff {d.max():.2e}  max rel diff {rel.max():.2e}  '
        f'max (diff - 6-digit half-unit) {np.max(d - half_unit):.2e} pct pts  rel<=1e-6 {int((rel <= 1e-6).sum())}  '
        f'within rounding+1e-9 {strict}  within rounding+{SLACK:.0e} {int(ok.sum())}/{len(ok)}  '
        f'NaN mismatches {nan_mismatch}')
    return bool(ok.all()) and nan_mismatch == 0


def identity_check(px):
    """My sma()/ema() vs the builder's own roll()/seeded() on the same closes (convention identity)."""
    path = os.path.join(TA, 'build_panel.py')
    if not os.path.exists(path):
        log('identity check vs build_panel.py skipped (file not found)')
        return True
    spec = importlib.util.spec_from_file_location('ta_build_panel', path)
    bp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bp)
    worst, nan_bad = 0.0, 0
    for _, g in px.groupby('symbol', sort=False):
        c = g.c.to_numpy(float)
        pairs = [(sma(c, n), bp.roll(c, n, 'mean')) for n in SMA_N]
        pairs += [(ema(c, n), bp.seeded(c, n, 2 / (n + 1), 0)) for n in EMA_N]
        for a, b in pairs:
            m = np.isfinite(b)
            nan_bad += int((np.isfinite(a) != m).sum())
            if m.any():
                worst = max(worst, float(np.max(np.abs(a[m] / b[m] - 1))))
    log(f'identity check: my SMA/EMA vs build_panel.roll()/seeded() on every stock-day: max rel diff {worst:.1e}, '
        f'NaN pattern mismatches {nan_bad}')
    return worst <= 1e-12 and nan_bad == 0


def main():
    os.makedirs(OUT, exist_ok=True)
    log('=== build_features.py')
    sessions = pd.read_csv(os.path.join(PACK, 'sessions.csv'))
    day_to_i = dict(zip(sessions.day, sessions.i))
    px = pd.read_csv(os.path.join(TA, 'adjusted_ohlcv.csv.gz'), usecols=['day', 'symbol', 'close', 'raw_close',
                                                                         'price_factor'])
    px['i'] = px.day.map(day_to_i)
    assert px.i.notna().all()
    px['c'] = px.raw_close * px.price_factor
    rel = np.abs(px.c / px.close - 1)
    log(f'prices: {len(px)} stock-days, {px.symbol.nunique()} symbols; close = raw_close x price_factor '
        f'(vs stored close: max rel diff {rel.max():.1e})')
    assert px.c.notna().all() and (px.c > 0).all()
    px = px.sort_values(['symbol', 'i']).reset_index(drop=True)
    ok = identity_check(px)

    # ------------------------------------------------------------------ results
    ev = pd.read_csv(os.path.join(PACK, 'events.csv'))
    ev = ev[ev.in_fo == True].reset_index(drop=True)
    assert len(ev) == 3278 and ev.symbol.nunique() == 206 and not ev.duplicated(['symbol', 'qn']).any()
    assert ((ev.i_m1 - ev.i_cut) == 1).all() and ((ev.i_rd - ev.i_cut) == 2).all() and ((ev.i_p1 - ev.i_cut) == 3).all()
    d = {f'd{j}': 100 * ev[c].fillna(0.0) for j, c in ((1, 'ret_dm1'), (2, 'ret_rd'), (3, 'ret_dp1'))}
    three = d['d1'] + d['d2'] + d['d3']
    chk = np.nanmax(np.abs(three - 100 * ev.three_day))
    log(f'results: {len(ev)} F&O results, {ev.symbol.nunique()} symbols, qn {ev.qn.min()}..{ev.qn.max()}; '
        f'three_day = d1 + d2 + d3 vs 100 x events.three_day max diff {chk:.1e}')
    assert chk < 1e-9
    want = pd.DataFrame({'symbol': ev.symbol, 'i': ev.i_cut.astype(int)})
    Fe = compute(px, want)
    fe = pd.DataFrame({'symbol': ev.symbol, 'qn': ev.qn, 'period': ev.period, 'cutoff': ev.cutoff,
                       'three_day': three, 'd1': d['d1'], 'd2': d['d2'], 'd3': d['d3']})
    fe['excess'] = fe.three_day - fe.groupby('qn').three_day.transform('mean')
    fe = pd.concat([fe, Fe[FEATURES]], axis=1)
    log(f'  traded at the cutoff: {int(Fe._traded.sum())} of {len(Fe)}')

    # validation against events_ta.csv
    et = pd.read_csv(os.path.join(TA, 'events_ta.csv'))
    et = et[et.in_fo == True].set_index(['symbol', 'qn'])
    et = et.loc[list(zip(ev.symbol, ev.qn))].reset_index()
    assert (et.i_cut.to_numpy() == ev.i_cut.to_numpy()).all()
    log('validation vs events_ta.csv (stored with 6 significant digits):')
    for n in (20, 50, 200):
        ok &= check_6g(Fe[f'dist_sma_{n}'].to_numpy(), et[f'close_vs_sma{n}_pct'].to_numpy(),
                       f'close_vs_sma{n}_pct', 'results')
    ok &= check_6g(Fe['_macd_pct'].to_numpy(), et['macd_pct'].to_numpy(), 'macd_pct (EMA12-EMA26)/C', 'results')
    for a, b in (('state_sma50_200', 'golden_state'), ('_golden_state', 'golden_state'),
                 ('_golden_x10', 'golden_x10'), ('_death_x10', 'death_x10')):
        mism = int((Fe[a].to_numpy() != et[b].to_numpy()).sum())
        log(f'  results {a:22s} vs {b:13s} mismatches {mism} of {len(et)}')
        ok &= mism == 0
    sanity = float(np.nanmax(np.abs(Fe['spread_sma50_200'] - et['sma50_vs_sma200_pct'])))
    log(f'  results spread_sma50_200 vs sma50_vs_sma200_pct max abs diff {sanity:.2e}')

    # ------------------------------------------------------------------ placebo
    pl = pd.read_csv(os.path.join(TA, 'placebo_ta.csv.gz'),
                     usecols=['symbol', 'day', 'i', 'in_fo', 'd1', 'd2', 'd3', 'three_day', 'close_vs_sma20_pct',
                              'close_vs_sma50_pct', 'close_vs_sma200_pct', 'macd_pct', 'golden_state'])
    n_all = len(pl)
    pl = pl[pl.in_fo == True].reset_index(drop=True)
    # season of a placebo day: the quarter whose results season most recently began (season q starts at the
    # earliest cutoff session of quarter q's F&O results)
    starts = ev.groupby('qn').i_cut.min().sort_index()
    ends = ev.groupby('qn').i_cut.max().sort_index()
    assert (starts.to_numpy()[1:] > ends.to_numpy()[:-1]).all(), 'seasons overlap'
    q_idx = np.searchsorted(starts.to_numpy(), pl.i.to_numpy(), side='right') - 1
    before = int((q_idx < 0).sum())
    pl['qn'] = np.where(q_idx >= 0, starts.index.to_numpy()[np.maximum(q_idx, 0)], -1)
    pl = pl[pl.qn >= 0].reset_index(drop=True)
    log(f'placebo: {n_all} stock-days in placebo_ta, {len(pl)} with in_fo True kept '
        f'({before} before the first season dropped); seasons start at sessions '
        + ', '.join(f'{q}:{s}' for q, s in starts.items()))
    Fp = compute(px, pl[['symbol', 'i']])
    log(f'  traded on the placebo day: {int(Fp._traded.sum())} of {len(Fp)}')
    log('validation vs placebo_ta.csv.gz (6 significant digits):')
    for n in (20, 50, 200):
        ok &= check_6g(Fp[f'dist_sma_{n}'].to_numpy(), pl[f'close_vs_sma{n}_pct'].to_numpy(),
                       f'close_vs_sma{n}_pct', 'placebo')
    ok &= check_6g(Fp['_macd_pct'].to_numpy(), pl['macd_pct'].to_numpy(), 'macd_pct (EMA12-EMA26)/C', 'placebo')
    mism = int((Fp['state_sma50_200'].to_numpy() != pl['golden_state'].to_numpy()).sum())
    log(f'  placebo state_sma50_200 vs golden_state mismatches {mism} of {len(pl)}')
    ok &= mism == 0
    log(f'VALIDATION {"PASSED" if ok else "FAILED"}')
    DEVIATIONS.append(f'Validation slack: PLAN.txt allowed |diff| <= 6-digit half-unit + 1e-9; used + {SLACK:.0e} '
                      'percentage points because adjusted_ohlcv.csv.gz stores price_factor with 8 significant digits '
                      '(a split/bonus step inside an MA window carries up to ~5e-8 relative error). The MA code itself '
                      'is identical to build_panel.roll()/seeded() (identity check above). The 1e-6-relative and '
                      '+1e-9 counts are printed next to each check.')

    fp = pd.concat([pl[['symbol', 'i', 'qn', 'three_day']], Fp[FEATURES]], axis=1)

    # ------------------------------------------------------------------ NaN counts
    log('NaN count per feature (results / placebo):')
    for k in FEATURES:
        log(f'  {k:18s} {int(fe[k].isna().sum()):5d} / {int(fp[k].isna().sum()):6d}')
    log('binary signal counts (results / placebo):')
    for k in BINARY:
        log(f'  {k:18s} {int((fe[k] == 1).sum()):5d} / {int((fp[k] == 1).sum()):6d}')

    for k in BINARY:
        fe[k] = fe[k].astype('Int64')
        fp[k] = fp[k].astype('Int64')
    # 8 significant digits (= the precision of the price inputs): run_tests.py ranks these stored values, and fewer
    # digits (%.6g / %.5g) created ties that do not exist in the computed features (fifth boundaries, placebo ranks).
    fe.to_csv(os.path.join(OUT, 'features_events.csv'), index=False, float_format='%.8g')
    fp.to_csv(os.path.join(OUT, 'features_placebo.csv.gz'), index=False, float_format='%.8g', compression='gzip')
    log(f'wrote features_events.csv ({len(fe)} rows x {fe.shape[1]} cols), '
        f'features_placebo.csv.gz ({len(fp)} rows x {fp.shape[1]} cols)')
    with open(os.path.join(OUT, 'build.log'), 'w') as fh:
        fh.write('\n'.join(LOG) + '\n')
        for x in DEVIATIONS:
            fh.write('DEVIATION: ' + x + '\n')
    if not ok:
        sys.exit('validation failed')


if __name__ == '__main__':
    main()
