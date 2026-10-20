"""Shared loaders for the prev-quarter-patterns skeptic (read-only on repo and lab data)."""
import os
import numpy as np
import pandas as pd

LAB = os.environ.get('LAB_ROOT', 'lab')
REPO = os.environ.get('REPO_ROOT', '.')
D = os.path.join(LAB, 'sector_lab', 'data')
RES = os.path.join(REPO, 'results', 'prev_quarter_patterns')
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.environ.get('SK_CACHE', os.path.join(LAB, 'prev_quarter_skeptic_cache'))  # regenerated, not committed
os.makedirs(CACHE, exist_ok=True)
COST = 0.17
LAGS = range(1, 9)


def fpv(p):
    return '<0.001' if p < 0.001 else f'{p:.3f}'


def rank(a):
    return pd.Series(a).rank().to_numpy()


def load():
    """history.csv (repo build) + extra controls computed here."""
    cp = os.path.join(CACHE, 'panel.pkl')
    if os.path.exists(cp):
        return pd.read_pickle(cp)
    F = pd.read_csv(os.path.join(RES, 'history.csv'))
    ev = pd.read_csv(os.path.join(D, 'events.csv'))
    ev['fo'] = ev.in_fo.map(lambda v: v is True or v == 'True')
    e = ev[['symbol', 'qn', 'i_cut', 'i_m1', 'i_rd', 'i_p1', 'nifty_3d', 'mcap', 'sector_index', 'industry',
            'three_day', 'fo']]
    F = F.merge(e.drop(columns=['three_day', 'fo', 'i_cut']), on=['symbol', 'qn'], how='left', validate='1:1')
    assert len(F) == 3278
    # date-demeaned outcomes
    g = F.groupby('i_cut').y
    F['n_cut'] = g.transform('size')
    F['y_dd'] = np.where(F.n_cut >= 2, F.y - g.transform('mean'), np.nan)
    ea = ev[ev.three_day.notna()].copy()
    ea['td'] = ea.three_day * 100
    ga = ea.groupby('i_cut').td.agg(['sum', 'size'])
    s = F.i_cut.map(ga['sum']); n = F.i_cut.map(ga['size'])
    # mean of the OTHER events (any F&O status) with the same cutoff
    F['n_cut_all'] = n
    F['y_dd_all'] = np.where(n >= 2, F.y - (s - F.y) / (n - 1), np.nan)
    # market model controls from returns / index
    R = pd.read_csv(os.path.join(D, 'returns.csv'))
    ic = pd.read_csv(os.path.join(D, 'index_close.csv'), index_col=0)
    nif = ic['Nifty 50'].to_numpy(float)
    nret = np.r_[np.nan, nif[1:] / nif[:-1] - 1]
    vix = ic['India VIX'].to_numpy(float)
    Rm = R.drop(columns='day')
    beta, vol250, ret250, ret60 = [], [], [], []
    for sym, i in zip(F.symbol, F.i_cut):
        r = Rm[sym].to_numpy()
        w = np.arange(i - 249, i + 1)
        a, b = r[w], nret[w]
        m = ~np.isnan(a) & ~np.isnan(b)
        if m.sum() >= 120:
            cv = np.cov(a[m], b[m])
            beta.append(cv[0, 1] / cv[1, 1])
            vol250.append(np.std(a[m], ddof=1) * 100)
        else:
            beta.append(np.nan); vol250.append(np.nan)
        lr = np.log1p(a[~np.isnan(a)])
        ret250.append(np.expm1(lr.sum()) * 100 if m.sum() >= 200 else np.nan)
        w6 = r[i - 59:i + 1]
        ret60.append(np.expm1(np.log1p(w6[~np.isnan(w6)]).sum()) * 100)
    F['beta'] = beta
    F['vol250'] = vol250
    F['ret250'] = ret250
    F['ret60'] = ret60
    F['vix'] = vix[F.i_cut.to_numpy()]
    F['nifty_vol20'] = [np.nanstd(nret[i - 19:i + 1], ddof=1) * 100 for i in F.i_cut]
    F['y_mm'] = F.y - F.beta * F.nifty_3d * 100           # market-model residual (beta known at the cutoff)
    F['x_mm'] = F.y_mm - F.groupby('qn').y_mm.transform('mean')
    F['x_nif'] = (F.y - F.nifty_3d * 100) - (F.y - F.nifty_3d * 100).groupby(F.qn).transform('mean')
    F['absy'] = F.y.abs()
    F.to_pickle(cp)
    return F


def ic_q(df, f, y, minn=20):
    """per-quarter Spearman list (qn, ic, n)."""
    out = []
    for q, s in df[['qn', f, y]].dropna().groupby('qn'):
        if len(s) < minn:
            continue
        a, b = rank(s[f].to_numpy()), rank(s[y].to_numpy())
        out.append((q, np.corrcoef(a, b)[0, 1], len(s)))
    return out


def summ(ics):
    v = np.array([c for _, c, _ in ics])
    if len(v) == 0:
        return np.nan, np.nan, 0, 0, 0
    t = v.mean() / (v.std(ddof=1) / np.sqrt(len(v))) if len(v) > 1 else np.nan
    return v.mean(), t, int((v > 0).sum()), len(v), int(sum(n for _, _, n in ics))


def perm_ic_multi(df, feats, y, B=2000, seed=1, minn=20):
    """within-quarter permutation of y (same perm for all feats). Returns obs mean IC, null matrix (B x F)."""
    rng = np.random.default_rng(seed)
    obs = np.zeros(len(feats)); null = np.zeros((B, len(feats))); nq = np.zeros(len(feats))
    for q, s in df.groupby('qn'):
        yv = s[y].to_numpy()
        ok_y = ~np.isnan(yv)
        valid = np.flatnonzero(ok_y)
        P = np.tile(np.arange(len(yv)), (B, 1))
        for b in range(B):
            P[b, valid] = valid[rng.permutation(len(valid))]   # shuffle y among rows with valid y only
        for j, f in enumerate(feats):
            fv = s[f].to_numpy()
            m = ok_y & ~np.isnan(fv)
            if m.sum() < minn:
                continue
            # null: assign y of permuted valid rows to the rows having f
            idx_f = np.flatnonzero(m)
            a = rank(fv[idx_f]); a = a - a.mean()
            yo = rank(yv[idx_f]); yo = yo - yo.mean()
            den = np.sqrt((a ** 2).sum() * (yo ** 2).sum())
            obs[j] += (a * yo).sum() / den
            # map: the permuted y for row r = yv[P[:, r]]; restrict to idx_f rows and re-rank
            Yp = yv[P[:, idx_f]]
            Rp = np.argsort(np.argsort(Yp, axis=1), axis=1).astype(float) + 1   # outcome continuous: no ties
            Rp = Rp - Rp.mean(axis=1, keepdims=True)
            null[:, j] += (Rp @ a) / np.sqrt((a ** 2).sum() * (Rp ** 2).sum(axis=1))
            nq[j] += 1
    obs = obs / np.maximum(nq, 1); null = null / np.maximum(nq, 1)
    return obs, null, nq


def two_sided(null, obs):
    c = null.mean()
    return (1 + np.sum(np.abs(null - c) >= abs(obs - c) - 1e-12)) / (len(null) + 1)


def maxT(null, obs):
    mu, sd = null.mean(0), null.std(0)
    z = np.abs((null - mu) / sd); zo = np.abs((obs - mu) / sd)
    mx = z.max(1)
    return np.array([(1 + np.sum(mx >= zo[j] - 1e-12)) / (len(mx) + 1) for j in range(len(obs))])


def holm(p):
    p = np.asarray(p, float); o = np.argsort(p); m = len(p)
    adj = np.empty(m); run = 0
    for r, i in enumerate(o):
        run = max(run, (m - r) * p[i]); adj[i] = min(1, run)
    return adj
