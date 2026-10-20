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
for kk in (1, 2, 4):
    ic_k = EK.i_cut.reindex(pd.MultiIndex.from_arrays([F.symbol, F.qn - kk])).to_numpy()
    for off in (10, 15, 20):
        F[f'ord{kk}_{off}'] = [np.nan if np.isnan(i) else abs(win(s, int(i) - off)) for s, i in zip(F.symbol, ic_k)]
# ordinary outcome windows after the result: starting i_p1 + 6, +11, +16, +21
for j, off in enumerate((6, 11, 16, 21)):
    F[f'pl{j}'] = [win(s, int(i) + off) for s, i in zip(F.symbol, F.i_p1)]
    F[f'apl{j}'] = F[f'pl{j}'].abs()
F['mcap_r'] = F.mcap
print(f'ordinary predictor windows present (lag 1): {int(F.ord1_10.notna().sum())}; ordinary outcome windows: '
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
    'none': ([], False),
    'vol60 (build)': (['vol60'], False),
    'vol60 + vol250': (['vol60', 'vol250'], False),
    '+ beta + mcap': (['vol60', 'vol250', 'beta', 'mcap_r'], False),
    '+ VIX at cutoff': (['vol60', 'vol250', 'beta', 'mcap_r', 'vix'], False),
    '+ sector dummies': (['vol60', 'vol250', 'beta', 'mcap_r', 'vix'], True),
}
print('\n== partial rank IC of |three_day(t-k)| with |y(t)|, controls added step by step (p: 2,000 within-quarter shuffles)')
print('lag | ' + ' | '.join(CTRL))
rows = []
for kk in LAGS:
    cells = []
    for nm, (cols, sec) in CTRL.items():
        m, p, pos, nq, n, a, b = partial_ic(F, f'abs{kk}', 'absy', cols, sec)
        cells.append(f'{m:+.3f} ({fpv(p)})'); rows.append((kk, nm, m, p, pos, nq, n, a, b))
    print(f'  {kk} | ' + ' | '.join(cells) + f' | n {n}, {nq} q')
fam = pd.DataFrame(rows, columns=['lag', 'ctrl', 'ic', 'p', 'pos', 'nq', 'n', 'first', 'last'])
for nm in CTRL:
    s = fam[fam.ctrl == nm]
    print(f'   {nm:18s}: Holm over 8 lags min {holm(s.p).min():.3f}; lags with Holm < 0.05: '
          f'{[int(l) for l, h in zip(s.lag, holm(s.p)) if h < 0.05]}; mean of the 8 lag ICs {s.ic.mean():+.3f}')
full = fam[fam.ctrl == '+ sector dummies']
print('   full controls, halves: ' + '; '.join(f'lag {int(r.lag)} {r["first"]:+.3f} / {r["last"]:+.3f}' for _, r in full.iterrows()))

# context: what do the controls themselves explain
print('\n== context ICs with |y| (raw within-quarter Spearman, mean over quarters)')
for c in ('vol60', 'vol250', 'beta', 'mcap_r', 'vix', 'nifty_vol20'):
    s = summ(ic_q(F, c, 'absy'))
    print(f'   {c:10s} IC {s[0]:+.3f} pos {s[2]}/{s[3]}')

# common sample: results with all 8 lags (qn 8-21) so lags are compared on the same results
cs = F[[f'abs{k}' for k in LAGS]].notna().all(1)
print(f'\n== common sample (all 8 lags present): {int(cs.sum())} results, qn {F[cs].qn.min()}-{F[cs].qn.max()}; full controls')
for kk in LAGS:
    m, p, pos, nq, n, a, b = partial_ic(F[cs], f'abs{kk}', 'absy', ['vol60', 'vol250', 'beta', 'mcap_r', 'vix'], True)
    m0 = summ(ic_q(F[cs], f'abs{kk}', 'absy'))[0]
    print(f'   lag {kk}: raw {m0:+.3f}; partial {m:+.3f} p {fpv(p)} pos {pos}/{nq}')
# average of past |results moves| (last 4) as a single predictor
A4 = F[[f'abs{k}' for k in range(1, 5)]]
F['abs_mean4'] = np.where(A4.notna().all(1), A4.mean(1), np.nan)
m, p, pos, nq, n, a, b = partial_ic(F, 'abs_mean4', 'absy', ['vol60', 'vol250', 'beta', 'mcap_r', 'vix'], True)
print(f'   mean |move| of last 4 results: partial IC {m:+.3f} p {fpv(p)} pos {pos}/{nq} n {n} | first {a:+.3f} last {b:+.3f}')

# results-specific? (a) ordinary windows of the lag period as predictors of |y|
print('\n== (a) ordinary 3-day windows of the same stock in the lag-k period as predictors of |y| (same controls)')
for kk in (1, 2, 4):
    for off in (10, 15, 20):
        f = f'ord{kk}_{off}'
        m, p, pos, nq, n, *_ = partial_ic(F, f, 'absy', ['vol60', 'vol250', 'beta', 'mcap_r', 'vix'], True)
        m0 = summ(ic_q(F, f, 'absy'))[0]
        print(f'   lag-{kk} period, window ending {off - 2} sessions before its cutoff: raw {m0:+.3f}, partial {m:+.3f} p {fpv(p)} (n {n})')
    m, p, *_ = partial_ic(F[F[f'ord{kk}_10'].notna()], f'abs{kk}', 'absy', ['vol60', 'vol250', 'beta', 'mcap_r', 'vix'], True)
    print(f'   lag-{kk} RESULTS move on the same results: partial {m:+.3f} p {fpv(p)}')
# (b) |lag-k results move| as predictor of ORDINARY windows after the result
print('\n== (b) |three_day(t-k)| as predictor of |ordinary 3-day windows after this result| (controls vol60, vol250, beta, mcap, VIX, sector)')
for kk in (1, 2, 4, 7, 8):
    vals = []
    for j in range(4):
        m, p, *_ = partial_ic(F, f'abs{kk}', f'apl{j}', ['vol60', 'vol250', 'beta', 'mcap_r', 'vix'], True, B=500)
        vals.append(m)
    mr, pr, *_ = partial_ic(F, f'abs{kk}', 'absy', ['vol60', 'vol250', 'beta', 'mcap_r', 'vix'], True)
    print(f'   lag {kk}: ordinary windows partial ICs {", ".join(f"{v:+.3f}" for v in vals)} (mean {np.mean(vals):+.3f}) vs results window {mr:+.3f}')

# practical size: |y| by quintile of the full-control residual of abs1, and an implied-move style ratio
print('\n== practical: average |y| by within-quarter fifth of |lag-1 move| inside vol60 terciles')
F['v3'] = F.groupby('qn').vol60.transform(lambda s: pd.qcut(s.rank(method='first'), 3, labels=False))
for t in range(3):
    s = F[(F.v3 == t) & F.abs1.notna()]
    fq = s.groupby('qn').abs1.transform(lambda z: pd.qcut(z.rank(method='first'), 5, labels=False))
    print(f'   vol60 tercile {t + 1}: ' + ', '.join(f'fifth {i + 1} {s[fq == i].absy.mean():.2f}%' for i in range(5)) + f' (n {len(s)})')
