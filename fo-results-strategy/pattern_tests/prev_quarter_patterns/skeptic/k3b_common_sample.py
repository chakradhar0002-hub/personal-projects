"""k3: magnitude persistence. Is |lag-k results move| -> |y| just volatility (vol60, vol250, beta, sector, size, India
VIX)? Is it results-specific (ordinary 3-day windows of the same stock as predictor and as outcome)?"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from common import *

F = load(); F['qn'] = F.qn.astype(int)
rng = np.random.default_rng(20261022)
ev = pd.read_csv(os.path.join(D, 'events.csv'))
R = pd.read_csv(os.path.join(D, 'returns.csv')); Rm = R.drop(columns='day'); NS = len(Rm)
res_days = {s: set(np.r_[g.i_m1, g.i_rd, g.i_p1].astype(int).tolist()) for s, g in ev.groupby('symbol')}
EK = ev.set_index(['symbol', 'qn'])


def win(sym, s):
    """3-day sum (%) of sessions s..s+2, NaN if out of range / missing / touches a results session of the stock."""
    if s < 0 or s + 2 >= NS:
        return np.nan
    if res_days[sym] & {s, s + 1, s + 2}:
        return np.nan
    r = Rm[sym].to_numpy()[s:s + 3]
    return np.nan if np.isnan(r).any() else r.sum() * 100


# ordinary predictor windows in the lag-k period: 3-day windows ending 8, 13, 18 sessions before that lag event's cutoff
for kk in ():
    ic_k = EK.i_cut.reindex(pd.MultiIndex.from_arrays([F.symbol, F.qn - kk])).to_numpy()
    for off in (10, 15, 20):
        F[f'ord{kk}_{off}'] = [np.nan if np.isnan(i) else abs(win(s, int(i) - off)) for s, i in zip(F.symbol, ic_k)]
# ordinary outcome windows after the result: starting i_p1 + 6, +11, +16, +21
for j, off in enumerate(()):
    F[f'pl{j}'] = [win(s, int(i) + off) for s, i in zip(F.symbol, F.i_p1)]
    F[f'apl{j}'] = F[f'pl{j}'].abs()
F['mcap_r'] = F.mcap
if 0: print(f'ordinary predictor windows present (lag 1): {int(F.ord1_10.notna().sum())}; ordinary outcome windows: '
      + ', '.join(str(int(F[f"pl{j}"].notna().sum())) for j in range(4)))


def resid_rank(df, cols, target, sector=False):
    """within quarter: rank target, regress on ranks of cols (+ sector dummies), return residual Series."""
    out = pd.Series(np.nan, index=df.index)
    for q, s in df.groupby('qn'):
        s = s.dropna(subset=cols + [target])
        if len(s) < 20:
            continue
        X = [np.ones(len(s))] + [rank(s[c].to_numpy()) for c in cols]
        if sector:
            d = pd.get_dummies(s.sector_index, drop_first=True).to_numpy(float)
            X += [d[:, i] for i in range(d.shape[1])]
        X = np.column_stack(X); yv = rank(s[target].to_numpy())
        b, *_ = np.linalg.lstsq(X, yv, rcond=None)
        out.loc[s.index] = yv - X @ b
    return out


def partial_ic(df, pred, target, cols, sector=False, B=2000):
    need = cols + [pred, target] + (['sector_index'] if sector else [])
    d = df.dropna(subset=need).copy()
    d['rp'] = resid_rank(d, cols, pred, sector) if cols or sector else d.groupby('qn')[pred].rank()
    d['rt'] = resid_rank(d, cols, target, sector) if cols or sector else d.groupby('qn')[target].rank()
    ics, null = [], np.zeros(B); n = 0
    for q, s in d.dropna(subset=['rp', 'rt']).groupby('qn'):
        if len(s) < 20:
            continue
        a = s.rp.to_numpy() - s.rp.mean(); b = s.rt.to_numpy() - s.rt.mean()
        den = np.sqrt((a ** 2).sum() * (b ** 2).sum())
        ics.append((q, (a * b).sum() / den, len(s))); n += len(s)
        P = np.array([rng.permutation(len(b)) for _ in range(B)])
        null += (b[P] @ a) / den
    v = np.array([c for _, c, _ in ics]); null /= len(v)
    return v.mean(), two_sided(null, v.mean()), int((v > 0).sum()), len(v), n, \
        np.mean([c for q, c, _ in ics if q <= 13]), np.mean([c for q, c, _ in ics if q >= 14])



CTRL = {
    'none': ([], False), 'vol60 (build)': (['vol60'], False), 'sector only': ([], True), 'vol60 + sector': (['vol60'], True),
    'vol60 + vol250': (['vol60', 'vol250'], False), '+ beta + mcap': (['vol60', 'vol250', 'beta', 'mcap_r'], False),
    '+ VIX': (['vol60', 'vol250', 'beta', 'mcap_r', 'vix'], False), '+ sector (all)': (['vol60', 'vol250', 'beta', 'mcap_r', 'vix'], True)}
G = F.dropna(subset=['vol60', 'vol250', 'beta', 'mcap_r', 'vix']).copy()
print(f'common sample: {len(G)} of {len(F)} results (mcap present)')
print('lag | ' + ' | '.join(CTRL))
rows = []
for kk in LAGS:
    cells = []
    for nm, (cols, sec) in CTRL.items():
        m, p, pos, nq, n, a, b = partial_ic(G, f'abs{kk}', 'absy', cols, sec)
        cells.append(f'{m:+.3f} ({fpv(p)})'); rows.append((kk, nm, m, p))
    print(f'  {kk} | ' + ' | '.join(cells) + f' | n {n}, {nq} q')
fam = pd.DataFrame(rows, columns=['lag', 'ctrl', 'ic', 'p'])
for nm in CTRL:
    s = fam[fam.ctrl == nm]; hh = holm(s.p)
    print(f'   {nm:16s}: mean IC over lags {s.ic.mean():+.3f}; Holm<0.05 lags {[int(l) for l, h in zip(s.lag, hh) if h < 0.05]}; min Holm {hh.min():.3f}')
