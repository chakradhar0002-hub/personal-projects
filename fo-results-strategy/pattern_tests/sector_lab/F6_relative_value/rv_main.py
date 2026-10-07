#!/usr/bin/env python3
"""
F6  -  Within-sector RELATIVE VALUE after peers report (Indian NSE F&O stocks, 22 results seasons).
Run:  python3 -I rv_main.py      (from any cwd; all paths absolute)

=====================================================================================
PRE-REGISTRATION  (written BEFORE any outcome was computed; nothing below was changed
after seeing results - any later addition is listed in the ADDENDUM block and counted)
=====================================================================================
Definitions (fixed in advance)
  * "Peer group" (parts a, b, d) = events.peer_group when not blank, else the NSE
    industry; industry 'Miscellaneous' is dropped (not a real peer group).
  * Sector (part c) = events.sector_index, only indices with full 2021-2026 history:
    Nifty 'Nifty 500' (= no sector), India Digital, India Manufacturing, India Defence
    are excluded from part c.
  * Reaction excess of an event = stock daily return on reaction_day minus Nifty 50
    daily return on reaction_day (reaction_day = result day for before/during-market,
    next session for after-close). Known at the reaction-day close.
  * Trades only in stocks with in_fo == True for that season (both legs for pairs).
  * Entry at the CLOSE of the decision session; exit at the close h sessions later.
    Holding returns compounded from returns.csv (a blank return = no trade that day;
    the next return spans both sessions, so blanks are skipped in the product; a trade
    is dropped if the stock has a blank on the entry day or >2 blanks inside the window).
  * Costs: 0.17% per stock round trip, +0.02% for a Nifty futures hedge.
      single stock vs Nifty: 0.19 ; pair (long stock fut + short stock fut): 0.34 ;
      sector index vs Nifty (part c): 0.04 if Nifty Bank / Nifty Financial Services
      (index futures exist), else 0.19 (sector needs a basket of stock futures).
  * Every trade measured: raw, minus Nifty 50, minus the stock's own sector index over
    the same window (sector index missing -> Nifty 500, noted).
  * Unit of evidence = season (qn). Per-season mean, t across seasons, first 14 (qn 0-13)
    vs last 8 (qn 14-21), seasons positive; also a date-clustered t (secondary).

PART (a) Reaction divergence of two same-group F&O peers, both reported this season.
  Pair formed at decision t = later of the two reaction days (close of t).
  D = |excess_A - excess_B|. Winner W = higher reaction excess, loser L.
  Grid: threshold D > {4%, 8%}  x  window {any time this season, reaction days <= 5
        sessions apart ("near")}  x  hold h {5, 10, 20}  x  direction {CONTINUE: long W
        short L ; REVERSE: long L short W}                       -> 2*2*3*2 = 24 variants
  Main metric: pair spread net = r_long - r_short - 0.34. Legs reported separately:
  long leg vs Nifty (r_long - r_nifty - 0.19), short leg vs Nifty (r_nifty - r_short - 0.19).

PART (b) Fundamental vs price disagreement, stock X (F&O) vs peers already reported
  (peers = same group & season with reaction_day <= X's reaction day, any F&O status,
  need >= 2 peers with data). Decision = X's reaction-day close.
  F = X metric - median(peer metric); P = X reaction excess - median(peer reaction excess)
  GOOD-NEWS-PUNISHED (long X):  F > thr  and P < 0
  BAD-NEWS-REWARDED  (short X): F < -thr and P > 0
  Grid: metric {pat_yoy thr 0.25 / 0.50 ; sales_yoy thr 0.10 / 0.20} (2 metrics x 2 thr)
        x direction {long-good, short-bad} x hold {10, 20}       -> 2*2*2*2 = 16 variants
  Main metric: X vs Nifty net (sign * (r_X - r_nifty) - 0.19). Also: vs equal-weight
  basket of the F&O peers in the reference set (cost 0.34), raw, vs sector.

PART (c) Sector dispersion. For each (sector, season) with >= 5 reporters: decision t =
  reaction day of the 5th reporter; set = all members with reaction_day <= t (any F&O
  status); SD = std (ddof=1) of their reaction excess, MU = mean.
  Outcome = sector index minus Nifty 50 over h sessions after close t.
  c1 HIGH  SD > 5%    : long sector vs Nifty / short sector vs Nifty  x h{5,10,20} = 6
  c2 LOW   SD < 2.5%  : long / short                                   x h{5,10,20} = 6
  c3 LOW SD < 2.5%  : trade sector in the sign of MU vs Nifty          x h{5,10,20} = 3
  c4 HIGH SD > 5%   : trade sector in the sign of MU vs Nifty          x h{5,10,20} = 3
                                                                           -> 18 variants
PART (d) (user's 3-day window) Catch-up / lag before own results.
  At X's cutoff close: peers = same group & season with reaction_day <= cutoff (>= 2).
  S = mean peer reaction excess. LAG = X return minus Nifty from the close before the first
  such peer reaction through the cutoff close.
  d-long : S > thr and LAG < 0 -> buy X at cutoff close, sell at Day+1 close.
  d-short: S < -thr and LAG > 0 -> short X same window.
  thr {2%, 3%} x direction {long, short}                                  -> 4 variants
  Outcome: user's definition (sum of the 3 daily returns), raw, minus Nifty 3d, minus sector 3d.

TOTAL PRE-REGISTERED VARIANTS = 24 + 16 + 18 + 4 = 62

"Promising" = main hedged metric after costs > 0 in BOTH qn 0-13 and qn 14-21,
  t across seasons >= 2.5, >= 30 trades, AND placebo clearly worse.
PLACEBO (pre-registered, 200 runs each) run for every variant with t >= 2.0 and both halves
  > 0 and >= 30 trades, plus the best-t variant of each part regardless:
  (a) P1 shuffle reaction excess among the F&O events of the same group & season;
      P2 fake "reaction days" = random non-results sessions in the same season.
  (b) P1 shuffle the fundamental metric among events of the same group & season.
  (c) P1 shuffle reaction excess among all events of the same season (across sectors).
  (d) P1 shuffle reaction excess among events of the same group & season.
  Report share of placebo runs whose mean (and t) >= actual.
ADDENDUM (post-hoc, counted separately): none at time of writing.
=====================================================================================
"""
import sys
sys.path.append('/root/.local/lib/python3.11/site-packages')  # pandas deps (python3 -I hides user site)
import os
import numpy as np
import pandas as pd

D = os.environ.get('SECTOR_LAB', 'sector_lab') + '/data/'
OUT = os.environ.get('SECTOR_LAB', 'sector_lab') + '/F6_relative_value/'
NPLACEBO = 200
RNG = np.random.default_rng(20261007)

C_STOCK, C_HEDGE = 0.17, 0.02
C_SINGLE = C_STOCK + C_HEDGE      # 0.19
C_PAIR = 2 * C_STOCK              # 0.34
FUT_INDICES = {'Nifty Bank', 'Nifty Financial Services'}
C_SPLIT = 13                       # qn <= 13 first 14 seasons
PART_C_EXCLUDE = {'Nifty 500', 'Nifty India Digital', 'Nifty India Manufacturing', 'Nifty India Defence'}

pd.set_option('display.width', 250)
pd.set_option('display.max_columns', 40)
pd.set_option('display.max_rows', 200)

# ------------------------------------------------------------------ load + checks
ses = pd.read_csv(D + 'sessions.csv')
ret = pd.read_csv(D + 'returns.csv', index_col=0)
ixc = pd.read_csv(D + 'index_close.csv', index_col=0)
ev = pd.read_csv(D + 'events.csv')
T = len(ses)
assert list(ret.index) == list(ses.day) == list(ixc.index), 'calendar mismatch'
assert (ses.i.values == np.arange(T)).all()
print(f'sessions {T} ({ses.day.iloc[0]}..{ses.day.iloc[-1]}), returns {ret.shape}, indices {ixc.shape}, events {ev.shape}')
assert not ev.duplicated(['symbol', 'qn']).any()
for c in ['i_cut', 'i_m1', 'i_rd', 'i_p1', 'i_react']:
    assert (ses.day.values[ev[c].values] == ev[{'i_cut': 'cutoff', 'i_m1': 'day_m1', 'i_rd': 'result_day',
                                               'i_p1': 'day_p1', 'i_react': 'reaction_day'}[c]].values).all(), c
print('event session positions match sessions.csv: OK')
missing_sym = set(ev.symbol) - set(ret.columns)
assert not missing_sym, missing_sym

R = ret.values.astype(float)                      # T x S
RN = np.nan_to_num(R, nan=0.0)
PC = np.cumprod(1.0 + RN, axis=0)                 # price index (blank -> flat)
CNAN = np.vstack([np.zeros((1, R.shape[1])), np.cumsum(np.isnan(R), axis=0)])  # CNAN[k] = #nan in rows < k
SIDX = {s: k for k, s in enumerate(ret.columns)}
IX = {c: ixc[c].values.astype(float) for c in ixc.columns}
NIF = IX['Nifty 50']
NRET = np.r_[np.nan, NIF[1:] / NIF[:-1] - 1]
N500 = IX['Nifty 500']

used_idx = sorted(set(ev.sector_index)) + ['Nifty 50']
print('\nIndex coverage in study window (2021-01-01..):')
w0 = int(np.searchsorted(ses.day.values, '2021-01-01'))
for c in used_idx:
    x = IX[c][w0:]
    print(f'  {c:28s} nan={int(np.isnan(x).sum()):4d} of {len(x)}')

# -------------------------------------------------------------- event features
ev['s'] = ev.symbol.map(SIDX)
ev['grp'] = ev.peer_group.fillna(ev.industry)
ev.loc[ev.grp == 'Miscellaneous', 'grp'] = np.nan
ev['fo'] = ev.in_fo.fillna(False).astype(bool)
ev['exc'] = R[ev.i_react.values, ev.s.values] - NRET[ev.i_react.values]
chk = np.nanmax(np.abs(R[ev.i_react.values, ev.s.values] - ev.move.values))
print(f'\nreaction-day return from returns.csv vs events.move: max abs diff {chk:.2e}')
print(f'events with reaction excess: {ev.exc.notna().sum()} / {len(ev)}; F&O events: {ev.fo.sum()}; '
      f'F&O & grouped: {(ev.fo & ev.grp.notna()).sum()}')
gq = ev[ev.fo & ev.grp.notna()].groupby(['qn', 'grp']).size()
print('F&O peer groups with >=2 members per season (median count):', int((gq >= 2).groupby(level=0).sum().median()))


def fwd_stock(s, t, h):
    """compounded return of stock col s from close t to close t+h; NaN if invalid."""
    s = np.asarray(s); t = np.asarray(t)
    out = np.full(len(s), np.nan)
    ok = (t + h <= T - 1) & (t >= 0)
    ss, tt = s[ok], t[ok]
    r = PC[tt + h, ss] / PC[tt, ss] - 1.0
    nmiss = CNAN[tt + h + 1, ss] - CNAN[tt + 1, ss]          # blanks in (t, t+h]
    bad = np.isnan(R[tt, ss]) | (nmiss > 2)
    r[bad] = np.nan
    out[ok] = r
    return out


def fwd_index(name, t, h):
    t = np.asarray(t)
    out = np.full(len(t), np.nan)
    ok = t + h <= T - 1
    x = IX[name]
    out[ok] = x[t[ok] + h] / x[t[ok]] - 1.0
    return out


def fwd_sector(names, t, h):
    """sector index fwd return; fallback Nifty 500 when the sector index is missing."""
    names = np.asarray(names); t = np.asarray(t)
    out = np.full(len(t), np.nan)
    for nm in np.unique(names):
        m = names == nm
        v = fwd_index(nm, t[m], h)
        fb = fwd_index('Nifty 500', t[m], h)
        v = np.where(np.isnan(v), fb, v)
        out[m] = v
    return out


def tstat(x):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    if len(x) < 3 or x.std(ddof=1) == 0:
        return np.nan
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))


def season_stats(df, col, three_day=False):
    """df must have qn, t (decision session) and the metric col (percent)."""
    d = df[df[col].notna()]
    if len(d) == 0:
        return dict(trades=0)
    q = d.groupby('qn')[col].mean()
    dd = d.groupby('t')[col].mean()
    res = dict(trades=len(d), seasons=len(q), avg_trade=d[col].mean(), per_season_avg=q.mean(),
               t_season=tstat(q.values), first14=q[q.index <= C_SPLIT].mean(), last8=q[q.index > C_SPLIT].mean(),
               n_first14=int((q.index <= C_SPLIT).sum()), n_last8=int((q.index > C_SPLIT).sum()),
               seasons_pos=int((q > 0).sum()), pct_win=100 * (d[col] > 0).mean(), t_date=tstat(dd.values),
               n_dates=len(dd))
    if three_day:
        res['seasons_ge2'] = int((q >= 2.0).sum())
    return res


# ======================================================================== PART (a)
def build_pairs(E):
    """all unordered same-group, same-season pairs of F&O events with reaction excess."""
    F = E[E.fo & E.exc.notna() & E.grp.notna()]
    out = []
    for (g, q), d in F.groupby(['grp', 'qn'], sort=False):
        n = len(d)
        if n < 2:
            continue
        i, j = np.triu_indices(n, 1)
        s = d.s.values; tr = d.i_react.values; ex = d.exc.values; sec = d.sector_index.values
        win_is_i = ex[i] >= ex[j]
        out.append(pd.DataFrame({
            'grp': g, 'qn': q,
            'sW': np.where(win_is_i, s[i], s[j]), 'sL': np.where(win_is_i, s[j], s[i]),
            'excW': np.where(win_is_i, ex[i], ex[j]), 'excL': np.where(win_is_i, ex[j], ex[i]),
            'tW': np.where(win_is_i, tr[i], tr[j]), 'tL': np.where(win_is_i, tr[j], tr[i]),
            'secW': np.where(win_is_i, sec[i], sec[j]), 'secL': np.where(win_is_i, sec[j], sec[i]),
        }))
    P = pd.concat(out, ignore_index=True)
    P['t'] = np.maximum(P.tW, P.tL)
    P['Dv'] = P.excW - P.excL
    P['gapdays'] = (P.tW - P.tL).abs()
    return P


A_THR = [0.04, 0.08]
A_WIN = ['any', 'near']
HS_A = [5, 10, 20]


def pair_returns(P, h):
    t = P.t.values
    fW = fwd_stock(P.sW.values, t, h); fL = fwd_stock(P.sL.values, t, h)
    fN = fwd_index('Nifty 50', t, h)
    fSW = fwd_sector(P.secW.values, t, h); fSL = fwd_sector(P.secL.values, t, h)
    return fW, fL, fN, fSW, fSL


def eval_a(P, thr, win, h, direction, rets=None, full=True):
    m = (P.Dv.values > thr)
    if win == 'near':
        m &= P.gapdays.values <= 5
    fW, fL, fN, fSW, fSL = rets if rets is not None else pair_returns(P, h)
    if direction == 'continue':
        lo, sh, slo, ssh = fW, fL, fSW, fSL
    else:
        lo, sh, slo, ssh = fL, fW, fSL, fSW
    df = pd.DataFrame({'qn': P.qn.values, 't': P.t.values})
    df['main'] = 100 * (lo - sh) - C_PAIR
    m &= ~np.isnan(df.main.values)
    df = df[m].copy()
    if not full:
        return df
    lo, sh, fNm, slo, ssh = lo[m], sh[m], fN[m], slo[m], ssh[m]
    df['long_raw'] = 100 * lo - C_STOCK
    df['short_raw'] = -100 * sh - C_STOCK
    df['long_vs_nifty'] = 100 * (lo - fNm) - C_SINGLE
    df['short_vs_nifty'] = 100 * (fNm - sh) - C_SINGLE
    df['long_vs_sector'] = 100 * (lo - slo) - C_SINGLE
    df['short_vs_sector'] = 100 * (ssh - sh) - C_SINGLE
    df['pair_vs_sector'] = 100 * ((lo - slo) - (sh - ssh)) - C_PAIR
    df['pair_gross'] = 100 * (lo - sh)
    sub = P[m]
    for c in ['grp', 'sW', 'sL', 'excW', 'excL', 'tW', 'tL', 'Dv', 'gapdays']:
        df[c] = sub[c].values
    return df


# ======================================================================== PART (b)
B_GRID = [('pat_yoy', 0.25), ('pat_yoy', 0.50), ('sales_yoy', 0.10), ('sales_yoy', 0.20)]
HS_B = [10, 20]


def build_b(E, metric):
    """for every F&O event X: compare to peers (same grp & qn) with reaction_day <= X's."""
    rows = []
    G = E[E.grp.notna() & E.exc.notna()]
    for (g, q), d in G.groupby(['grp', 'qn'], sort=False):
        if len(d) < 3:
            continue
        tr = d.i_react.values; ex = d.exc.values; mv = d[metric].values; fo = d.fo.values
        s = d.s.values; sec = d.sector_index.values
        for k in range(len(d)):
            if not fo[k] or np.isnan(mv[k]):
                continue
            pm = (tr <= tr[k]) & (np.arange(len(d)) != k) & ~np.isnan(mv)
            if pm.sum() < 2:
                continue
            fo_peers = s[pm & fo]
            rows.append((g, q, s[k], tr[k], sec[k], mv[k] - np.median(mv[pm]), ex[k] - np.median(ex[pm]),
                         int(pm.sum()), tuple(fo_peers)))
    return pd.DataFrame(rows, columns=['grp', 'qn', 's', 't', 'sec', 'F', 'Pgap', 'npeers', 'fo_peers'])


def basket_fwd(peer_tuples, t, h):
    out = np.full(len(t), np.nan)
    for k, (pt, tt) in enumerate(zip(peer_tuples, t)):
        if len(pt) == 0:
            continue
        v = fwd_stock(np.array(pt), np.full(len(pt), tt), h)
        if np.isfinite(v).any():
            out[k] = np.nanmean(v)
    return out


def eval_b(B, thr, direction, h, rets=None, full=True):
    if direction == 'long_good':
        m = (B.F.values > thr) & (B.Pgap.values < 0); sgn = 1.0
    else:
        m = (B.F.values < -thr) & (B.Pgap.values > 0); sgn = -1.0
    Bm = B[m]
    t = Bm.t.values
    if rets is None:
        fX = fwd_stock(Bm.s.values, t, h)
    else:
        fX = rets[m]
    fN = fwd_index('Nifty 50', t, h)
    df = pd.DataFrame({'qn': Bm.qn.values, 't': t})
    df['main'] = 100 * sgn * (fX - fN) - C_SINGLE
    ok = ~np.isnan(df.main.values)
    if not full:
        return df[ok]
    fS = fwd_sector(Bm.sec.values, t, h)
    fB = basket_fwd(Bm.fo_peers.values, t, h)
    df['raw'] = 100 * sgn * fX - C_STOCK
    df['vs_sector'] = 100 * sgn * (fX - fS) - C_SINGLE
    df['vs_peer_basket'] = 100 * sgn * (fX - fB) - C_PAIR
    for c in ['grp', 's', 'F', 'Pgap', 'npeers']:
        df[c] = Bm[c].values
    return df[ok]


# ======================================================================== PART (c)
HS_C = [5, 10, 20]


def build_c(E):
    rows = []
    G = E[E.exc.notna() & ~E.sector_index.isin(PART_C_EXCLUDE)]
    for (sec, q), d in G.groupby(['sector_index', 'qn'], sort=False):
        if len(d) < 5:
            continue
        tr = np.sort(d.i_react.values)
        t5 = tr[4]
        x = d.exc.values[d.i_react.values <= t5]
        rows.append((sec, q, t5, len(x), x.std(ddof=1), x.mean()))
    return pd.DataFrame(rows, columns=['sector', 'qn', 't', 'nrep', 'SD', 'MU'])


C_VARIANTS = []
for h in HS_C:
    for d_ in ['long', 'short']:
        C_VARIANTS.append(('c1_highSD', d_, h))
        C_VARIANTS.append(('c2_lowSD', d_, h))
    C_VARIANTS.append(('c3_lowSD_signMU', 'signMU', h))
    C_VARIANTS.append(('c4_highSD_signMU', 'signMU', h))


def eval_c(Cdf, kind, d_, h, full=True):
    if kind.startswith('c1') or kind.startswith('c4'):
        m = Cdf.SD.values > 0.05
    else:
        m = Cdf.SD.values < 0.025
    X = Cdf[m]
    if d_ == 'long':
        sg = np.ones(len(X))
    elif d_ == 'short':
        sg = -np.ones(len(X))
    else:
        sg = np.sign(X.MU.values)
    t = X.t.values
    fS = np.array([fwd_index(s, np.array([tt]), h)[0] for s, tt in zip(X.sector.values, t)]) if len(X) else np.array([])
    fN = fwd_index('Nifty 50', t, h)
    cost = np.where(X.sector.isin(FUT_INDICES).values, 2 * C_HEDGE, C_SINGLE)
    df = pd.DataFrame({'qn': X.qn.values, 't': t})
    df['main'] = 100 * sg * (fS - fN) - cost
    if full:
        df['raw_sector'] = 100 * sg * fS - cost + C_HEDGE   # sector leg alone (basket/futures), no Nifty hedge
        df['nifty_leg'] = -100 * sg * fN                   # what the Nifty hedge contributed
        df['sector'] = X.sector.values; df['SD'] = X.SD.values; df['MU'] = X.MU.values
    return df[df.main.notna()]


# ======================================================================== PART (d)
D_THR = [0.02, 0.03]


def build_d(E):
    rows = []
    G = E[E.grp.notna()]
    for (g, q), d in G.groupby(['grp', 'qn'], sort=False):
        if len(d) < 3:
            continue
        tr = d.i_react.values; ex = d.exc.values; fo = d.fo.values; cut = d.i_cut.values
        for k in range(len(d)):
            if not fo[k] or np.isnan(d.three_day.values[k]):
                continue
            pm = (tr <= cut[k]) & (np.arange(len(d)) != k) & ~np.isnan(ex)
            if pm.sum() < 2:
                continue
            first = tr[pm].min()
            s = d.s.values[k]
            a0 = first - 1
            lag = (PC[cut[k], s] / PC[a0, s] - 1) - (NIF[cut[k]] / NIF[a0] - 1)
            rows.append((g, q, d.symbol.values[k], s, cut[k], ex[pm].mean(), int(pm.sum()), lag,
                         d.three_day.values[k], d.excess_nifty.values[k], d.excess_sector.values[k]))
    return pd.DataFrame(rows, columns=['grp', 'qn', 'symbol', 's', 't', 'S', 'npeers', 'LAG', 'three_day',
                                       'ex_nifty3', 'ex_sector3'])


def eval_d(Dd, thr, direction, full=True):
    if direction == 'long':
        m = (Dd.S.values > thr) & (Dd.LAG.values < 0); sg = 1.0
    else:
        m = (Dd.S.values < -thr) & (Dd.LAG.values > 0); sg = -1.0
    X = Dd[m]
    df = pd.DataFrame({'qn': X.qn.values, 't': X.t.values})
    df['main'] = 100 * sg * X.ex_nifty3.values - C_SINGLE
    if full:
        df['raw'] = 100 * sg * X.three_day.values - C_STOCK
        df['vs_sector'] = 100 * sg * X.ex_sector3.values - C_SINGLE
        for c in ['grp', 'symbol', 'S', 'LAG', 'npeers']:
            df[c] = X[c].values
    return df[df.main.notna()]


# ======================================================================== RUN ALL
def row(part, name, rule, horizon, df, extra_cols, three_day=False):
    st = season_stats(df, 'main', three_day=three_day)
    r = dict(part=part, variant=name, rule=rule, horizon=horizon)
    r.update({f'main_{k}': v for k, v in st.items()})
    for c in extra_cols:
        sc = season_stats(df, c, three_day=three_day)
        r[f'{c}_avg'] = sc.get('avg_trade', np.nan)
        r[f'{c}_season_avg'] = sc.get('per_season_avg', np.nan)
        r[f'{c}_t'] = sc.get('t_season', np.nan)
        r[f'{c}_first14'] = sc.get('first14', np.nan)
        r[f'{c}_last8'] = sc.get('last8', np.nan)
        if three_day:
            r[f'{c}_seasons_ge2'] = sc.get('seasons_ge2', np.nan)
            r[f'{c}_seasons_pos'] = sc.get('seasons_pos', np.nan)
    return r


if __name__ == '__main__':
    results = []
    trades_store = {}

    # ---------------- (a)
    P = build_pairs(ev)
    print(f'\n(a) same-group F&O pairs: {len(P)}; share D>4%: {(P.Dv > .04).mean():.2f}, D>8%: {(P.Dv > .08).mean():.2f}; '
          f'near(<=5d): {(P.gapdays <= 5).mean():.2f}')
    RA = {h: pair_returns(P, h) for h in HS_A}
    a_cols = ['long_vs_nifty', 'short_vs_nifty', 'long_raw', 'short_raw', 'long_vs_sector', 'short_vs_sector',
              'pair_vs_sector', 'pair_gross']
    for thr in A_THR:
        for win in A_WIN:
            for h in HS_A:
                for dr in ['continue', 'reverse']:
                    name = f'a_{dr}_D{int(thr*100)}_{win}_h{h}'
                    df = eval_a(P, thr, win, h, dr, rets=RA[h])
                    trades_store[name] = df
                    rule = (f'At the later reaction-day close of two same-group F&O peers (same season'
                            f'{", reactions <=5 sessions apart" if win == "near" else ""}) whose reaction-day excess '
                            f'vs Nifty differs by >{int(thr*100)}%: {"long winner / short loser" if dr == "continue" else "long loser / short winner"}'
                            f' (stock futures), exit after {h} sessions.')
                    results.append(row('a', name, rule, f'{h}d', df, a_cols))

    # ---------------- (b)
    BB = {m_: build_b(ev, m_) for m_ in ['pat_yoy', 'sales_yoy']}
    for m_, B in BB.items():
        print(f'(b) {m_}: F&O events with >=2 reported peers: {len(B)}')
    b_cols = ['raw', 'vs_sector', 'vs_peer_basket']
    for metric, thr in B_GRID:
        B = BB[metric]
        for dr in ['long_good', 'short_bad']:
            for h in HS_B:
                name = f'b_{dr}_{metric}_{int(thr*100)}_h{h}'
                df = eval_b(B, thr, dr, h)
                trades_store[name] = df
                if dr == 'long_good':
                    rule = (f'At F&O stock X reaction-day close: X {metric} beats median of already-reported same-group peers '
                            f'(>=2) by >{int(thr*100)} pts but X reaction excess < peers median: buy X, hedge Nifty, exit after {h} sessions.')
                else:
                    rule = (f'At F&O stock X reaction-day close: X {metric} trails median of already-reported same-group peers '
                            f'(>=2) by >{int(thr*100)} pts but X reaction excess > peers median: short X, hedge Nifty, exit after {h} sessions.')
                results.append(row('b', name, rule, f'{h}d', df, b_cols))

    # ---------------- (c)
    Cdf = build_c(ev)
    print(f'(c) sector-season observations: {len(Cdf)}; SD quantiles: '
          f'{np.round(np.quantile(Cdf.SD, [.1, .25, .5, .75, .9]) * 100, 2).tolist()} %; '
          f'SD>5%: {(Cdf.SD > .05).sum()}, SD<2.5%: {(Cdf.SD < .025).sum()}')
    c_cols = ['raw_sector', 'nifty_leg']
    for kind, d_, h in C_VARIANTS:
        name = f'{kind}_{d_}_h{h}'
        df = eval_c(Cdf, kind, d_, h)
        trades_store[name] = df
        cond = 'SD>5%' if ('c1' in kind or 'c4' in kind) else 'SD<2.5%'
        act = {'long': 'long sector index vs short Nifty', 'short': 'short sector index vs long Nifty',
               'signMU': 'trade sector vs Nifty in the sign of the mean reaction of the first >=5 reporters'}[d_]
        rule = (f'At reaction-day close of the 5th reporter of a sector this season, if the cross-sectional SD of '
                f'reporters\' reaction excess {cond}: {act}; exit after {h} sessions.')
        results.append(row('c', name, rule, f'{h}d', df, c_cols))

    # ---------------- (d)
    Dd = build_d(ev)
    print(f'(d) F&O events with >=2 peers reported by cutoff: {len(Dd)}')
    d_cols = ['raw', 'vs_sector']
    for thr in D_THR:
        for dr in ['long', 'short']:
            name = f'd_{dr}_S{int(thr*100)}'
            df = eval_d(Dd, thr, dr)
            trades_store[name] = df
            if dr == 'long':
                rule = (f'At X cutoff close (2 sessions before result session): >=2 same-group peers already reacted, '
                        f'their mean reaction excess >+{int(thr*100)}% and X lagged Nifty since first peer reaction: '
                        f'buy X, sell Day+1 close (3-day window).')
            else:
                rule = (f'At X cutoff close: >=2 same-group peers already reacted, mean reaction excess <-{int(thr*100)}% '
                        f'and X beat Nifty since first peer reaction: short X, cover Day+1 close.')
            results.append(row('d', name, rule, '3-day window', df, d_cols, three_day=True))

    RES = pd.DataFrame(results)
    print(f'\nTOTAL VARIANTS TESTED: {len(RES)}')
    assert len(RES) == 62
    RES['near_candidate'] = ((RES.main_t_season >= 2.0) & (RES.main_first14 > 0) & (RES.main_last8 > 0)
                             & (RES.main_trades >= 30))
    RES['meets_stats_bar'] = ((RES.main_t_season >= 2.5) & (RES.main_first14 > 0) & (RES.main_last8 > 0)
                              & (RES.main_trades >= 30))
    RES.to_csv(OUT + 'variants_all.csv', index=False)
    for k, v in trades_store.items():
        pass
    # store trades of all variants (compact) in one file per part
    for part in 'abcd':
        frames = [v.assign(variant=k) for k, v in trades_store.items() if k.startswith(part)]
        pd.concat(frames, ignore_index=True).to_csv(OUT + f'trades_part_{part}.csv', index=False)

    show = ['variant', 'main_trades', 'main_seasons', 'main_avg_trade', 'main_per_season_avg', 'main_t_season',
            'main_first14', 'main_last8', 'main_seasons_pos', 'main_t_date']
    for part in 'abcd':
        print(f'\n===== PART ({part}) main hedged metric, % per trade after costs =====')
        print(RES[RES.part == part][show].round(2).to_string(index=False))
    print('\n----- (a) legs (per-season averages, % net) -----')
    print(RES[RES.part == 'a'][['variant', 'long_vs_nifty_season_avg', 'long_vs_nifty_t', 'short_vs_nifty_season_avg',
                                'short_vs_nifty_t', 'pair_vs_sector_season_avg', 'pair_gross_season_avg']].round(2).to_string(index=False))
    print('\n----- (b) alternative measures (per-season averages, % net) -----')
    print(RES[RES.part == 'b'][['variant', 'raw_season_avg', 'vs_sector_season_avg', 'vs_sector_t',
                                'vs_peer_basket_season_avg', 'vs_peer_basket_t']].round(2).to_string(index=False))
    print('\n----- (c) decomposition -----')
    print(RES[RES.part == 'c'][['variant', 'raw_sector_season_avg', 'nifty_leg_season_avg']].round(2).to_string(index=False))
    print('\n----- (d) 3-day window raw / vs sector -----')
    print(RES[RES.part == 'd'][['variant', 'raw_season_avg', 'raw_t', 'raw_first14', 'raw_last8', 'raw_seasons_pos',
                                'raw_seasons_ge2', 'vs_sector_season_avg', 'vs_sector_t']].round(2).to_string(index=False))
    print('\nnear-candidates (t>=2, both halves>0, >=30 trades):')
    print(RES[RES.near_candidate][show].round(2).to_string(index=False))
    print('\nmeets statistical bar (before placebo):')
    print(RES[RES.meets_stats_bar][show].round(2).to_string(index=False))
    print('\nbest-t variant per part:')
    print(RES.loc[RES.groupby('part').main_t_season.idxmax()][show].round(2).to_string(index=False))
