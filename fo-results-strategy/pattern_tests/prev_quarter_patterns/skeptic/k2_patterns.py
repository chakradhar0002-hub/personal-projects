"""k2: for every good-looking pattern / feature: results, stocks, concentration by stock and quarter, leave-one-quarter-
out, stock-clustered SE, and the date-demeaned (same-cutoff) and market-model outcomes."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from common import *

F = load()
F['qn'] = F.qn.astype(int)
rng = np.random.default_rng(20261021)
B = 3000
OUTS = [('x', 'x (quarter excess)'), ('y_dd', 'same-cutoff demeaned (in_fo)'), ('y_dd_all', 'same-cutoff demeaned (all events)'),
        ('x_nif', 'minus Nifty, quarter-demeaned'), ('x_mm', 'minus beta*Nifty, quarter-demeaned')]


def perm_mean(mask, y, have, B=B):
    """pooled mean of y over mask; null: within-quarter shuffles of y among rows in `have` (subset with the needed lags
    and non-missing y). Returns obs, p (two-sided around null mean)."""
    ok = have & F[y].notna().to_numpy()
    obs = F[y].to_numpy()[mask & ok].mean()
    null = np.zeros(B); tot = (mask & ok).sum()
    for q, idx in F[ok].groupby('qn').indices.items():
        rows = F.index[ok][idx].to_numpy()
        yv = F[y].to_numpy()[rows]; mk = mask[rows]
        if mk.sum() == 0:
            continue
        P = np.array([rng.permutation(len(rows)) for _ in range(B)])
        null += (yv[P] * mk).sum(1)
    null /= tot
    return obs, two_sided(null, obs)


def cluster_se(v, g):
    """SE of a mean with clustering by g."""
    d = pd.DataFrame({'v': v - v.mean(), 'g': g})
    s = d.groupby('g').v.sum()
    G = len(s); n = len(v)
    return np.sqrt((s ** 2).sum()) / n * np.sqrt(G / (G - 1))


def pattern_report(name, mask, have, sign):
    sub = F[mask]
    print(f'\n-- {name}: {mask.sum()} results, {sub.symbol.nunique()} stocks, {sub.qn.nunique()} quarters; avg y {sub.y.mean():+.2f}%, '
          f'x {sub.x.mean():+.2f}; share up {(sub.y > 0).mean():.1%}')
    # by stock
    st = sub.groupby('symbol').x.agg(['sum', 'size', 'mean'])
    o = st.sort_values('sum', ascending=(sign < 0))
    top5 = o.head(5)
    tops = ", ".join(f"{s} {int(r['size'])}x {r['mean']:+.1f}" for s, r in top5.iterrows())
    print(f'   results per stock: max {st["size"].max()}, stocks with >= 4 {int((st["size"] >= 4).sum())}; top-5 stocks '
          f'({tops}) give {top5["sum"].sum() / st["sum"].sum():.0%} of the summed x')
    rest = sub[~sub.symbol.isin(top5.index)]
    print(f'   without those 5 stocks: {len(rest)} results, x {rest.x.mean():+.2f}; stocks with mean x of the favoured sign '
          f'{int((np.sign(st["mean"]) == sign).sum())} of {len(st)}')
    # by quarter
    qq = sub.groupby('qn').x.agg(['sum', 'size', 'mean'])
    loqo = [(sub.x.sum() - qq.loc[q, 'sum']) / (len(sub) - qq.loc[q, 'size']) for q in qq.index]
    best = qq.sort_values('sum', ascending=(sign < 0)).head(2)
    print(f'   quarters with mean x of the favoured sign {int((np.sign(qq["mean"]) == sign).sum())} of {len(qq)}; best 2 quarters '
          f'(q{best.index[0]} {best["mean"].iloc[0]:+.2f} n{int(best["size"].iloc[0])}, q{best.index[1]} {best["mean"].iloc[1]:+.2f} '
          f'n{int(best["size"].iloc[1])}) give {best["sum"].sum() / qq["sum"].sum():.0%} of the sum; leave-one-quarter-out mean x '
          f'{min(loqo):+.2f} .. {max(loqo):+.2f}')
    se_s = cluster_se(sub.x.to_numpy(), sub.symbol.to_numpy()); se_q = cluster_se(sub.x.to_numpy(), sub.qn.to_numpy())
    print(f'   SE of mean x: iid {sub.x.std() / np.sqrt(len(sub)):.2f}, clustered by stock {se_s:.2f} (t {sub.x.mean() / se_s:+.2f}), '
          f'by quarter {se_q:.2f} (t {sub.x.mean() / se_q:+.2f})')
    for y, lab in OUTS:
        o_, p_ = perm_mean(mask, y, have)
        m1 = mask & (F.qn <= 13).to_numpy(); m2 = mask & (F.qn >= 14).to_numpy()
        print(f'   {lab:38s}: {o_:+.2f} (n {int((mask & F[y].notna().to_numpy()).sum())}) p {fpv(p_)} | first 14 q '
              f'{F.loc[m1, y].mean():+.2f} | last 8 q {F.loc[m2, y].mean():+.2f}')


def ic_report(name, f, sign_note=''):
    have = F[f].notna()
    print(f'\n-- feature {name} ({f}): {int(have.sum())} results, {F[have].symbol.nunique()} stocks')
    for y, lab in OUTS:
        ics = ic_q(F, f, y)
        m, t, pos, nq, n = summ(ics)
        obs, null, _ = perm_ic_multi(F, [f], y, B=2000, seed=11)
        p = two_sided(null[:, 0], obs[0])
        f1 = summ([c for c in ics if c[0] <= 13]); f2 = summ([c for c in ics if c[0] >= 14])
        print(f'   {lab:38s}: IC {m:+.3f} t {t:+.2f} pos {pos}/{nq} n {n} p {fpv(p)} | first {f1[0]:+.3f} ({f1[3]} q) | last {f2[0]:+.3f}')
    ics = ic_q(F, f, 'x'); v = np.array([c for _, c, _ in ics]); qq = [q for q, _, _ in ics]
    loqo = [(v.sum() - v[i]) / (len(v) - 1) for i in range(len(v))]
    o = np.argsort(-v)
    print(f'   per-quarter IC: max q{qq[o[0]]} {v[o[0]]:+.3f}, q{qq[o[1]]} {v[o[1]]:+.3f}; leave-one-quarter-out {min(loqo):+.3f} .. {max(loqo):+.3f}; '
          f'without the best 2 quarters {np.delete(v, o[:2]).mean():+.3f}')
    # stock jackknife (drop one stock at a time) on the mean IC
    syms = F[have].symbol.unique(); infl = []
    base = v.mean()
    for s in syms:
        d = F[F.symbol != s]
        infl.append((s, summ(ic_q(d, f, 'x'))[0] - base))
    infl.sort(key=lambda z: z[1])
    drop5 = [s for s, _ in infl[:5]]
    print(f'   most influential stocks (IC change when dropped): {", ".join(f"{s} {d:+.4f}" for s, d in infl[:5])}; dropping these 5: '
          f'IC {summ(ic_q(F[~F.symbol.isin(drop5)], f, "x"))[0]:+.3f}')
    # favoured fifth trades
    fifth = F[have].groupby('qn')[f].rank(pct=True)
    top = F[have][fifth > 0.8]
    st = top.groupby('symbol').x.agg(['sum', 'size']).sort_values('sum', ascending=False)
    tops = ", ".join(f"{s} {int(r['size'])}x" for s, r in st.head(5).iterrows())
    print(f'   top fifth: {len(top)} results, {top.symbol.nunique()} stocks, x {top.x.mean():+.2f}, y_dd {top.y_dd.mean():+.2f}, '
          f'x_mm {top.x_mm.mean():+.2f}; top-5 stocks give {st["sum"].head(5).sum() / st["sum"].sum():.0%} of summed x '
          f'({tops}); without them x '
          f'{top[~top.symbol.isin(st.index[:5])].x.mean():+.2f}')


ALLQ = np.ones(len(F), bool)
print('== patterns (have = results with the needed lags; null shuffles within quarter inside that subset)')
for L, pats in ((3, [('UUU', 1), ('DDD', -1)]), (4, [('UUUU', 1), ('DDUU', -1), ('DDDU', -1), ('DDDD', -1)]), (2, [('DD', -1)])):
    have = F[f'seq{L}'].notna().to_numpy()
    for p, sgn in pats:
        pattern_report(f'pattern {p}', (F[f'seq{L}'] == p).to_numpy(), have, sgn)
have = F.streak.notna().to_numpy()
pattern_report('streak 3 ups (= DUUU)', (F.streak == 3).to_numpy(), have, 1)
h3 = F.h3.notna().to_numpy()
pattern_report('lag 3 up (A2)', (F.h3 > 0).to_numpy(), h3, 1)
pattern_report('lag 3 down (A2)', (F.h3 <= 0).to_numpy(), h3, -1)
print('\n== continuous features (IC with each outcome; p from 2,000 within-quarter shuffles)')
for nm, f in (('best of last 4', 'best4'), ('average of last 8', 'mean_h8'), ('average of last 4', 'mean_h4'),
              ('ups in last 4', 'n_up4'), ('lag 3', 'h3'), ('lag 4', 'h4'), ('lag 1', 'h1')):
    ic_report(nm, f)

print('\n== lag-1 after-the-fact split, by outcome definition (mean quarterly IC; quarters negative)')
for y, lab in OUTS:
    ics = ic_q(F, 'h1', y)
    for lo, hi in ((1, 7), (8, 21), (14, 21)):
        v = np.array([c for q, c, _ in ics if lo <= q <= hi])
        print(f'   {lab:38s} qn {lo}-{hi}: IC {v.mean():+.3f}, negative {int((v < 0).sum())}/{len(v)}')
