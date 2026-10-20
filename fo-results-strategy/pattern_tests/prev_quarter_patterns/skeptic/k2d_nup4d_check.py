"""k2d: robustness of the post-hoc n_up4d 'confirmation' (more shuffles, other date-demeaned outcome, stock concentration)."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from common import *
F = load(); F['qn'] = F.qn.astype(int)
ev = pd.read_csv(os.path.join(D, 'events.csv'))
E = ev[ev.three_day.notna()].copy(); E['td'] = E.three_day * 100
g = E.groupby('i_cut').td; E['n'] = g.transform('size')
E['hdd'] = np.where(E.n >= 2, (E.td - g.transform('sum') / E.n) * E.n / (E.n - 1), np.nan)
k = E.set_index(['symbol', 'qn'])
H = np.column_stack([k.hdd.reindex(pd.MultiIndex.from_arrays([F.symbol, F.qn - kk])).to_numpy() for kk in range(1, 5)])
a4 = ~np.isnan(H).any(1)
F['n_up4d'] = np.where(a4, (H > 0).sum(1), np.nan)
for y in ('y_dd_all', 'y_dd', 'x'):
    for hn, m in (('first', F.qn <= 13), ('last', F.qn >= 14)):
        o, nl, nq = perm_ic_multi(F[m], ['n_up4d'], y, B=10000, seed=31)
        print(f'n_up4d vs {y:8s} {hn}: IC {o[0]:+.3f} p {fpv(two_sided(nl[:, 0], o[0]))} ({int(nq[0])} q)')
print('levels (y_dd_all / x / y, count):')
for v in range(5):
    s = F[F.n_up4d == v]
    print(f'   {v} ups: {len(s)} results, y_dd_all {s.y_dd_all.mean():+.2f}, x {s.x.mean():+.2f}, y {s.y.mean():+.2f}%, '
          f'last 8 q y {s[s.qn >= 14].y.mean():+.2f}% ({int((s.qn >= 14).sum())})')
# leave out the 5 track-record stocks of PAST_PERFORMANCE / this study
drop = ['RECLTD', 'CUMMINSIND', 'ADANIPORTS', 'TRENT', 'POWERINDIA', 'BEL']
o, nl, _ = perm_ic_multi(F[~F.symbol.isin(drop)], ['n_up4d'], 'y_dd_all', B=3000, seed=32)
print(f'without {drop}: IC {o[0]:+.3f} p {fpv(two_sided(nl[:, 0], o[0]))}')
s = F[F.n_up4d == 4].copy(); s['net'] = s.y - COST
pq = s.groupby('qn').net.mean()
st = s.groupby('symbol').x.agg(['sum', 'size']).sort_values('sum', ascending=False)
tops = ', '.join(f'{a} {int(r["size"])}x' for a, r in st.head(5).iterrows())
w5 = s.net.sort_values().iloc[:-5].mean()
print(f'\n4 date-relative ups (post hoc): {len(s)} trades, {s.symbol.nunique()} stocks, net {s.net.mean():+.2f}%, win {(s.net > 0).mean():.0%}, '
      f'quarters net>0 {int((pq > 0).sum())}/{len(pq)}, without 5 best {w5:+.2f}%; first 14 q {s[s.qn <= 13].net.mean():+.2f}% '
      f'({int((s.qn <= 13).sum())}), last 8 q {s[s.qn >= 14].net.mean():+.2f}% ({int((s.qn >= 14).sum())}); top-5 stocks {tops} give '
      f'{st["sum"].head(5).sum() / st["sum"].sum():.0%} of summed x; without them x {s[~s.symbol.isin(st.index[:5])].x.mean():+.2f}; '
      f'in pp top tenth {int(s.pp_top10.sum())}, outside net {s[~s.pp_top10].net.mean():+.2f}% ({int((~s.pp_top10).sum())}); overlap with UUUU '
      f'{int((s.seq4 == "UUUU").sum())}')
