"""Shared loading and test helpers for the skeptic checks. Reads LAB_ROOT, LISTS_DIR and REPO_ROOT; csv outputs go to
SKOUT (default REPO_ROOT/results/nifty_sector_3day/skeptic), the placebo cache to LAB_ROOT/nifty_sector_skeptic_cache."""
import os
import numpy as np
import pandas as pd
from scipy import stats

LAB = os.environ.get('LAB_ROOT', 'lab')
LISTS = os.environ.get('LISTS_DIR', 'lists')
REPO = os.environ.get('REPO_ROOT', '.')
RES = os.path.join(REPO, 'results', 'nifty_sector_3day')
D = f'{LAB}/sector_lab/data'
SKOUT = os.environ.get('SKOUT', os.path.join(RES, 'skeptic'))
CACHE = os.path.join(LAB, 'nifty_sector_skeptic_cache')

SECTORAL = {'niftyauto': 'Nifty Auto', 'niftybank': 'Nifty Bank', 'niftyfinance': 'Nifty Financial Services',
            'niftyfmcg': 'Nifty FMCG', 'niftyhealthcare': 'Nifty Healthcare Index', 'niftyit': 'Nifty IT',
            'niftymedia': 'Nifty Media', 'niftymetal': 'Nifty Metal', 'niftypharma': 'Nifty Pharma',
            'niftypsubank': 'Nifty PSU Bank', 'nifty_privatebank': 'Nifty Private Bank', 'niftyrealty': 'Nifty Realty',
            'niftyconsumerdurables': 'Nifty Consumer Durables', 'niftyoilgas': 'Nifty Oil & Gas'}
THEMATIC = {'niftyenergy': 'Nifty Energy', 'niftyinfra': 'Nifty Infrastructure', 'niftycommodities': 'Nifty Commodities',
            'niftyconsumption': 'Nifty India Consumption', 'niftymnc': 'Nifty MNC', 'niftypse': 'Nifty PSE',
            'niftycpse': 'Nifty CPSE', 'niftyservice': 'Nifty Services Sector'}

# ---------------------------------------------------------------- data
evall = pd.read_csv(f'{D}/events.csv')
ev = evall[evall.in_fo == True].copy().reset_index(drop=True)
assert len(ev) == 3278 and ev.symbol.nunique() == 206
ev['td'] = ev.three_day * 100
rs = pd.read_csv(f'{RES}/results_3day.csv')
ev = ev.merge(rs[['symbol', 'qn', 'nifty_sector', 'custom_sector', 'three_day']].rename(columns={'three_day': 'td_repo'}),
              on=['symbol', 'qn'], how='left', validate='1:1')
assert np.allclose(ev.td_repo * 100, ev.td)
qmean = ev.groupby('qn').td.mean()
ev['ex'] = ev.td - ev.qn.map(qmean)
ev['year'] = ev.results_date.str[:4].astype(int)
QS = sorted(ev.qn.unique())

ret = pd.read_csv(f'{D}/returns.csv', index_col=0)
ix = pd.read_csv(f'{D}/index_close.csv', index_col=0)
ses = pd.read_csv(f'{D}/sessions.csv')
assert (ret.index == ses.day).all() and (ix.index == ses.day).all()
R = ret.to_numpy(float) * 100            # percent daily returns
col = {s: j for j, s in enumerate(ret.columns)}
NS = len(ret)
W = ev[['i_m1', 'i_rd', 'i_p1']].to_numpy(int)
chk = np.array([R[w, col[s]].sum() for s, w in zip(ev.symbol, W)])
assert np.abs(chk - ev.td).max() < 1e-4


def idx_ret(name):
    c = ix[name].to_numpy(float)
    return np.r_[np.nan, c[1:] / c[:-1] - 1] * 100


IR = {c: idx_ret(c) for c in list(SECTORAL.values()) + list(THEMATIC.values()) + ['Nifty 50']}
ev['n50'] = IR['Nifty 50'][W].sum(axis=1)

# ---------------------------------------------------------------- lists
n500 = pd.read_csv(os.path.join(LISTS, 'ind_nifty500list.csv'))
n500['Symbol'] = n500.Symbol.astype(str).str.strip()
assert (ev.symbol.map(n500.set_index('Symbol').Industry) == ev.nifty_sector).all()
MEM = {}
for f, name in (SECTORAL | THEMATIC).items():
    d = pd.read_csv(os.path.join(LISTS, f'ind_{f}list.csv'))
    MEM[name] = sorted(set(d.Symbol.astype(str).str.strip()) & set(ev.symbol))

# result-window mask: sessions i_m1..i_p1 of every event of the stock (any in_fo status)
RW = np.zeros(R.shape, bool)
RD = {}
for s, g in evall[evall.i_rd.notna()].groupby('symbol'):
    if s not in col:
        continue
    rd = g.i_rd.to_numpy(int)
    RD[s] = rd
    for o in (-1, 0, 1):
        RW[np.clip(rd + o, 0, NS - 1), col[s]] = True

# in-F&O stock x quarter coverage (for time-matched placebo windows)
FOQ = set(zip(ev.symbol, ev.qn))
LO, HI = int(ev.i_m1.min()), int(ev.i_p1.max())


def bucket(k):
    """Results quarter bucket of a session: Apr-Jun 2021 -> qn 0 (Jan-Mar 2021 results), etc."""
    d = ses.day.iloc[k]
    y, m = int(d[:4]), int(d[5:7])
    return (y - 2021) * 4 + (m - 1) // 3 - 1


BUCKET = np.array([bucket(k) for k in range(NS)])


def placebo(syms, gap=12):
    """Non-overlapping ordinary 3-day windows (m-1, m, m+1) of each stock, |m - any result day| >= gap (i.e. no result
    session within 10 sessions of the window), only in quarters in which the stock has an in-F&O result."""
    rows = []
    for s in syms:
        j = col[s]
        rd = RD.get(s, np.array([], int))
        for m in range(LO + 1, HI, 3):
            q = BUCKET[m]
            if (s, q) not in FOQ:
                continue
            if len(rd) and np.abs(rd - m).min() < gap:
                continue
            x = R[m - 1:m + 2, j]
            if np.isnan(x).any():
                continue
            rows.append((s, q, m, x.sum()))
    return pd.DataFrame(rows, columns=['symbol', 'qn', 'm', 'td'])


# ---------------------------------------------------------------- tests
POOLS = {q: g.ex.to_numpy() for q, g in ev.groupby('qn')}


def luck(g, n_sim=20000, seed=777, col_='ex'):
    obs = g[col_].mean()
    rng = np.random.default_rng(seed)
    sims = np.zeros(n_sim)
    for q, k in g.groupby('qn').size().items():
        pool = POOLS[q]
        if k == len(pool):
            continue
        keys = rng.random((n_sim, len(pool)))
        idx = np.argpartition(keys, k - 1, axis=1)[:, :k]
        sims += pool[idx].sum(axis=1)
    sims /= len(g)
    return obs, (1 + (np.abs(sims) >= abs(obs) - 1e-12).sum()) / (n_sim + 1), sims.std()


def qt(g, c='ex'):
    """Quarter t-test: mean of quarterly group means / se, two-sided p (df = quarters - 1)."""
    m = g.groupby('qn')[c].mean()
    if len(m) < 3:
        return np.nan, np.nan, len(m)
    t = m.mean() / (m.std(ddof=1) / np.sqrt(len(m)))
    return t, 2 * stats.t.sf(abs(t), len(m) - 1), len(m)


def cl2(g, c='ex'):
    """Two-way (stock, quarter) cluster-robust t of the mean, df = min(clusters) - 1."""
    x = g[c].to_numpy()
    n = len(x)
    e = x - x.mean()
    gs, gq = g.symbol.to_numpy(), g.qn.to_numpy()
    def v(keys):
        s = pd.Series(e).groupby(keys).sum().to_numpy()
        G = len(s)
        return (s ** 2).sum() / n ** 2 * (G / (G - 1) if G > 1 else 1)
    vs, vq, vc = v(gs), v(gq), (e ** 2).sum() / n ** 2
    V = vs + vq - vc
    if V <= 0:
        V = max(vs, vq)
    df = min(len(set(gs)), len(set(gq))) - 1
    t = x.mean() / np.sqrt(V)
    return t, 2 * stats.t.sf(abs(t), max(df, 1)), np.sqrt(V)


SYM_EX = ev.groupby('symbol').ex.agg(['sum', 'size'])


def stock_perm(k, obs, n_sim=20000, seed=11):
    """Random groups of k stocks (of 206): result-weighted mean excess; two-sided p."""
    rng = np.random.default_rng(seed)
    s, n = SYM_EX['sum'].to_numpy(), SYM_EX['size'].to_numpy()
    keys = rng.random((n_sim, len(s)))
    idx = np.argpartition(keys, k - 1, axis=1)[:, :k]
    sims = s[idx].sum(1) / n[idx].sum(1)
    return (1 + (np.abs(sims) >= abs(obs)).sum()) / (n_sim + 1)


def holm(p):
    p = pd.Series(p).dropna()
    o = p.sort_values()
    m = len(o)
    adj = np.maximum.accumulate([min(1, (m - i) * v) for i, v in enumerate(o)])
    return pd.Series(adj, index=o.index).reindex(pd.Series(p).index)


# ---------------------------------------------------------------- same-day benchmarks
CLEAN = ~RW & ~np.isnan(R)
FOSYM = sorted(set(ev.symbol))
FOMASK = np.zeros(R.shape, bool)
for s, q in FOQ:
    FOMASK[BUCKET == q, col[s]] = True
_u = CLEAN & FOMASK
_U = np.where(_u, R, 0.0)
EWU = _U.sum(1) / np.maximum(_u.sum(1), 1)          # equal-weight in-F&O universe, own-result-window days removed
EWU[_u.sum(1) == 0] = np.nan


def peer_arrays(syms):
    js = [col[s] for s in syms]
    m = CLEAN[:, js]
    return np.where(m, R[:, js], 0.0).sum(1), m.sum(1)


def loo_peer3(sym, w, psum, pcnt, members):
    """Equal-weight average of the other (clean) members over sessions w, summed; NaN if a day has no peer."""
    j = col[sym]
    tot = 0.0
    for k in w:
        own = CLEAN[k, j] and sym in members
        c = pcnt[k] - own
        if c <= 0:
            return np.nan
        tot += (psum[k] - (R[k, j] if own else 0.0)) / c
    return tot


N50 = IR['Nifty 50']
BETA = {}
for s in FOSYM:
    j = col[s]
    k = np.arange(LO, HI + 1)
    ok = CLEAN[k, j] & ~np.isnan(N50[k])
    x, y = N50[k][ok], R[k, j][ok]
    b = np.cov(x, y)[0, 1] / x.var(ddof=1)
    BETA[s] = (b, y.mean() - b * x.mean())


def windows(df):
    if 'i_rd' in df:
        return df[['i_m1', 'i_rd', 'i_p1']].to_numpy(int)
    m = df.m.to_numpy(int)
    return np.c_[m - 1, m, m + 1]


def bench(df, index=None, peers=None):
    """Add same-session benchmark moves (percent, 3-day sums) to a frame of results or placebo windows."""
    df = df.copy()
    w = windows(df)
    df['n50'] = N50[w].sum(1)
    df['ewu'] = EWU[w].sum(1)
    b = np.array([BETA[s][0] for s in df.symbol])
    a = np.array([BETA[s][1] for s in df.symbol])
    df['ab_beta'] = df.td - b * df.n50
    df['ab_mm'] = df.td - 3 * a - b * df.n50
    df['ab_n50'] = df.td - df.n50
    df['ab_ewu'] = df.td - df.ewu
    if index is not None:
        df['idx'] = IR[index][w].sum(1)
        df['ab_idx'] = df.td - df.idx
    if peers is not None:
        ps, pc = peer_arrays(peers)
        mem = set(peers)
        df['peer'] = [loo_peer3(s, ww, ps, pc, mem) for s, ww in zip(df.symbol, w)]
        df['ab_peer'] = df.td - df.peer
    return df


_ALLP = None


def all_placebo():
    global _ALLP
    if _ALLP is None:
        os.makedirs(CACHE, exist_ok=True)
        path = os.path.join(CACHE, 'placebo_all.pkl')
        if os.path.exists(path):
            _ALLP = pd.read_pickle(path)
        else:
            _ALLP = placebo(FOSYM)
            _ALLP.to_pickle(path)
    return _ALLP


def diff_q(gr, gp, c):
    """Results minus placebo, per quarter (same stocks): mean of quarterly differences, t over quarters, p."""
    a = gr.groupby('qn')[c].mean()
    b = gp.groupby('qn')[c].mean()
    d = (a - b).dropna()
    t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))
    return d.mean(), t, 2 * stats.t.sf(abs(t), len(d) - 1), len(d)


def placebo_excess(gr, gp):
    """Placebo-window 'excess over same-quarter average of all F&O placebo windows', weighted to the group's result
    counts per quarter (so it is time-matched to the results)."""
    ap = all_placebo()
    qm = ap.groupby('qn').td.mean()
    pq = (gp.td - gp.qn.map(qm)).groupby(gp.qn).mean()
    wq = gr.groupby('qn').size()
    pq = pq.reindex(wq.index)
    ok = pq.notna()
    return (pq[ok] * wq[ok]).sum() / wq[ok].sum()
