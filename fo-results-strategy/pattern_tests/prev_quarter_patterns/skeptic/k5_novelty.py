"""k5: is anything new vs PAST_PERFORMANCE.md (last-4 average, top tenth) and QUARTER_CORRELATION.md (lag-1 r)?"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from common import *
F = load(); F['qn'] = F.qn.astype(int)
rng = np.random.default_rng(9)


def partial(df, f, ctrl, y='x', B=2000):
    d = df.dropna(subset=[f, y] + ctrl).copy()
    ics, null = [], np.zeros(B)
    for q, s in d.groupby('qn'):
        if len(s) < 20:
            continue
        X = np.column_stack([np.ones(len(s))] + [rank(s[c].to_numpy()) for c in ctrl])
        def res(v):
            b, *_ = np.linalg.lstsq(X, v, rcond=None); return v - X @ b
        a = res(rank(s[f].to_numpy())); b = res(rank(s[y].to_numpy()))
        den = np.sqrt((a ** 2).sum() * (b ** 2).sum())
        ics.append((q, (a * b).sum() / den, len(s)))
        P = np.array([rng.permutation(len(b)) for _ in range(B)]); null += (b[P] @ a) / den
    v = np.array([c for _, c, _ in ics]); null /= len(v)
    return v.mean(), two_sided(null, v.mean()), sum(n for *_, n in ics), len(v)


print('== Spearman (pooled) between the D features and the PAST_PERFORMANCE last-4 average (pp_last4)')
for f in ('best4', 'mean_h4', 'mean_h8', 'n_up4', 'n_up8', 'h3', 'h4'):
    d = F[[f, 'pp_last4']].dropna()
    print(f'   {f:8s} rho {d.corr(method="spearman").iloc[0, 1]:+.3f} (n {len(d)})')
print('\n== does the feature add anything beyond pp_last4? partial rank IC with x (and with y_dd_all), control = pp_last4')
for f in ('best4', 'mean_h8', 'n_up4', 'n_up8', 'h3', 'worst4'):
    a = partial(F, f, ['pp_last4']); b = partial(F, f, ['pp_last4'], 'y_dd_all')
    r = partial(F, f, [])
    print(f'   {f:8s}: raw IC {r[0]:+.3f} (p {fpv(r[1])}); beyond pp_last4 {a[0]:+.3f} (p {fpv(a[1])}, n {a[2]}, {a[3]} q); '
          f'same-cutoff outcome beyond pp_last4 {b[0]:+.3f} (p {fpv(b[1])})')
a = partial(F, 'pp_last4', ['best4']); print(f'   reverse: pp_last4 beyond best4 {a[0]:+.3f} (p {fpv(a[1])})')
# tradable sets vs pp_top10
print('\n== top-fifth trades vs the PAST_PERFORMANCE top tenth')
for f in ('best4', 'mean_h8', 'mean_h4'):
    have = F[f].notna(); pr = F[have].groupby('qn')[f].rank(pct=True).reindex(F.index)
    top = F[pr > 0.8]
    ins, out = top[top.pp_top10], top[~top.pp_top10]
    out2 = top[~top.pp_top10 & ~top.lag10vol]
    print(f'   {f}: {len(top)} trades; inside pp top tenth {len(ins)} net {ins.y.mean() - COST:+.2f}% (x {ins.x.mean():+.2f}); outside '
          f'{len(out)} net {out.y.mean() - COST:+.2f}% (x {out.x.mean():+.2f}, y_dd_all {out.y_dd_all.mean():+.2f}); outside both pp and lag10vol {len(out2)} '
          f'net {out2.y.mean() - COST:+.2f}%; outside, last 8 q {out[out.qn >= 14].y.mean() - COST:+.2f}% ({int((out.qn >= 14).sum())})')
t10 = F[F.pp_top10]
print(f'   pp top tenth itself: {len(t10)} trades, net {t10.y.mean() - COST:+.2f}%, first 14 q {t10[t10.qn <= 13].y.mean() - COST:+.2f}% '
      f'({int((t10.qn <= 13).sum())}), last 8 q {t10[t10.qn >= 14].y.mean() - COST:+.2f}% ({int((t10.qn >= 14).sum())}); x {t10.x.mean():+.2f}, '
      f'y_dd_all {t10.y_dd_all.mean():+.2f}; stocks {t10.symbol.nunique()}')
st = t10.groupby('symbol').x.agg(['sum', 'size']).sort_values('sum', ascending=False)
tops = ", ".join(str(sym) + " " + str(int(r["size"])) + "x" for sym, r in st.head(5).iterrows())
print(f'   pp top tenth: top-5 stocks {tops} give {st["sum"].head(5).sum() / st["sum"].sum():.0%} of summed x')
# UUU / UUUU vs track record
print('\n== UUU / 4+ ups vs the track record')
for p, L in (('UUU', 3), ('UUUU', 4)):
    m = F[f'seq{L}'] == p
    print(f'   {p}: {int(m.sum())} results; share in pp top tenth {F[m].pp_top10.mean():.0%}, in mean_h4 top fifth '
          f'{(F[m].groupby("qn").size().sum() and (F.loc[m, "mean_h4"] > F.groupby("qn").mean_h4.transform(lambda s: s.quantile(0.8))[m]).mean()):.0%}; '
          f'x inside pp top tenth {F[m & F.pp_top10].x.mean():+.2f} ({int((m & F.pp_top10).sum())}), outside {F[m & ~F.pp_top10].x.mean():+.2f} ({int((m & ~F.pp_top10).sum())})')
d = F.copy(); d['is_uuu'] = (d.seq3 == 'UUU').astype(float)
a = partial(d[d.seq3.notna()], 'is_uuu', ['mean_h4']); print(f'   UUU indicator beyond mean_h4: partial IC {a[0]:+.3f} (p {fpv(a[1])})')
# QUARTER_CORRELATION: lag-1 fifths
print('\n== QUARTER_CORRELATION.md: last quarter top / bottom fifth of movers (doc: -0.02 / +0.07 over the quarter)')
have = F.h1.notna(); pr = F[have].groupby('qn').h1.rank(pct=True).reindex(F.index)
print(f'   ours (h1 fifths, x): top {F[pr > 0.8].x.mean():+.2f} ({int((pr > 0.8).sum())}), bottom {F[pr <= 0.2].x.mean():+.2f} ({int((pr <= 0.2).sum())})')
print('   PAST_PERFORMANCE "rose in the last results window": 1,548 trades, +0.03%, +0.32% first / -0.31% last '
      f'| ours after lag-1 up (h>0): {int((F.h1 > 0).sum())}, {F[F.h1 > 0].y.mean():+.2f}%, first 14 q {F[(F.h1 > 0) & (F.qn <= 13)].y.mean():+.2f}% / last 8 q {F[(F.h1 > 0) & (F.qn >= 14)].y.mean():+.2f}%')
m = F.n_up4 >= 3
print(f'   PAST_PERFORMANCE "rose in 3 or 4 of the last 4": 816, +0.39%, +0.95/-0.10 | ours n_up4>=3: {int(m.sum())}, {F[m].y.mean():+.2f}%, '
      f'first {F[m & (F.qn <= 13)].y.mean():+.2f}% / last {F[m & (F.qn >= 14)].y.mean():+.2f}%')
