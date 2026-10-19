import os
import numpy as np
import pandas as pd
from scipy import stats

S = os.path.dirname(os.path.abspath(__file__))
# control features (prep.py output) are regenerated, not committed
CACHE = os.environ.get('SK_CACHE', os.path.join(os.environ.get('LAB_ROOT', 'lab'), 'ema_sma_skeptic_cache'))
os.makedirs(CACHE, exist_ok=True)
LAB = os.environ.get('LAB_ROOT', 'lab')
TA = os.environ.get('TA_BUILD', os.path.join(os.environ.get('LAB_ROOT', 'lab'), 'ta', 'build'))
REPO = os.environ.get('REPO_ROOT', '.')
PACK = os.path.join(LAB, 'sector_lab', 'data')
RES = os.path.join(REPO, 'results', 'ema_sma_3day')

P = [5, 10, 20, 50, 100, 200]
PAIRS = ['ema9_21', 'ema12_26', 'ema20_50', 'ema50_200', 'sma20_50', 'sma50_200']
CONT = ([f'dist_ema_{n}' for n in P] + [f'dist_sma_{n}' for n in P]
        + [f'slope_ema_{n}' for n in (20, 50, 200)] + [f'slope_sma_{n}' for n in (20, 50, 200)]
        + [f'ema_vs_sma_{n}' for n in (20, 50, 200)] + [f'spread_{p}' for p in PAIRS])
BINARY = ([f'above_ema_{n}' for n in (20, 50, 200)] + [f'above_sma_{n}' for n in (20, 50, 200)]
          + [f'state_{p}' for p in PAIRS] + [f'xup_{p}' for p in PAIRS] + [f'xdn_{p}' for p in PAIRS]
          + ['pxup_ema20', 'pxup_sma20', 'pxdn_ema20', 'pxdn_sma20']
          + ['bull_stack_ema', 'bear_stack_ema', 'bull_stack_sma', 'bear_stack_sma'])
COST = 0.17


def load_events():
    fe = pd.read_csv(os.path.join(RES, 'features_events.csv'))
    ev = pd.read_csv(os.path.join(PACK, 'events.csv'))
    ev = ev[ev.in_fo == True][['symbol', 'qn', 'timing', 'mcap', 'nifty_3d', 'excess_nifty', 'i_cut', 'fin_type']]
    ta = pd.read_csv(os.path.join(TA, 'events_ta.csv'))
    ta = ta[ta.in_fo == True][['symbol', 'qn', 'lag_pct', 'stock_21d_pct', 'nifty_21d_pct', 'ret_5d_pct',
                                'vol_ratio_5_60', 'close_vs_sma50_pct']]
    ct = pd.read_csv(os.path.join(CACHE, 'ctrl_events.csv')).drop(columns=['i'])
    df = fe.merge(ev, on=['symbol', 'qn'], how='left').merge(ta, on=['symbol', 'qn'], how='left') \
        .merge(ct, on=['symbol', 'qn'], how='left')
    assert len(df) == 3278 and df.timing.notna().all() and df.lag_pct.notna().all()
    df['xs_nifty'] = df.three_day - 100 * df.nifty_3d
    first = df.groupby('symbol').qn.transform('min')
    df['first_qn'] = first
    lag = pd.read_csv(os.path.join(REPO, 'results', 'lag10_volume', 'trades.csv'))
    key = set(zip(lag.symbol, lag.qn))
    df['lag_trade'] = [(s, q) in key for s, q in zip(df.symbol, df.qn)]
    return df.sort_values(['qn', 'symbol']).reset_index(drop=True)


def zr(v):
    """standardised average ranks (unit norm) so dot product = Spearman."""
    r = stats.rankdata(v)
    r = r - r.mean()
    n = np.sqrt((r ** 2).sum())
    return r / n if n > 0 else r


def ic_by_q(df, f, y='three_day', qcol='qn'):
    out = {}
    for q, g in df.groupby(qcol):
        g = g[[f, y]].dropna()
        if len(g) < 5 or g[f].nunique() < 2:
            continue
        out[q] = float(zr(g[f].values) @ zr(g[y].values))
    return pd.Series(out)


def summ(ics):
    m = ics.mean()
    sd = ics.std(ddof=1)
    t = m / sd * np.sqrt(len(ics)) if sd > 0 else np.nan
    return m, t, int((ics > 0).sum()), len(ics)


def perm_ic(df, f, y='three_day', B=5000, seed=1, qcol='qn'):
    """mean IC and within-quarter shuffle p (two-sided), single feature."""
    rng = np.random.default_rng(seed)
    obs = []
    sims = np.zeros(B)
    nq = 0
    for q, g in df.groupby(qcol):
        g = g[[f, y]].dropna()
        if len(g) < 5 or g[f].nunique() < 2:
            continue
        rx = zr(g[f].values)
        ry = zr(g[y].values)
        obs.append(rx @ ry)
        idx = np.argsort(rng.random((B, len(ry))), axis=1)
        sims += ry[idx] @ rx
        nq += 1
    m = np.mean(obs)
    sims /= nq
    p = (1 + (np.abs(sims) >= abs(m) - 1e-12).sum()) / (1 + B)
    return m, p, np.std(sims)


def partial_ic(df, f, ctrl, y='three_day', B=5000, seed=2):
    """within-quarter partial rank correlation of f with y controlling for ctrl (list): residualise rank(f) on
    rank(ctrl) by OLS, correlate residual with rank(y). Returns mean, t, pos, p (shuffle y)."""
    rng = np.random.default_rng(seed)
    obs = []
    sims = np.zeros(B)
    for q, g in df.groupby('qn'):
        g = g[[f, y] + ctrl].dropna()
        rx = zr(g[f].values)
        X = np.column_stack([np.ones(len(g))] + [zr(g[c].values) for c in ctrl])
        beta, *_ = np.linalg.lstsq(X, rx, rcond=None)
        res = rx - X @ beta
        res = res / np.sqrt((res ** 2).sum())
        ry = zr(g[y].values)
        obs.append(res @ ry)
        idx = np.argsort(rng.random((B, len(ry))), axis=1)
        sims += ry[idx] @ res
    obs = pd.Series(obs)
    sims /= len(obs)
    m, t, pos, n = summ(obs)
    p = (1 + (np.abs(sims) >= abs(m) - 1e-12).sum()) / (1 + B)
    return m, t, pos, p


def fifth(df, f, qcol='qn'):
    r = df.groupby(qcol)[f].rank(method='average')
    n = df.groupby(qcol)[f].transform('count')
    return (np.floor((r - 1) * 5 / n) + 1).astype(int)


def f3(x):
    return f'{x:+.3f}'


def f2(x):
    return f'{x:+.2f}'


def fpv(p):
    return '<0.001' if p < 0.0005 else f'{p:.3f}'
