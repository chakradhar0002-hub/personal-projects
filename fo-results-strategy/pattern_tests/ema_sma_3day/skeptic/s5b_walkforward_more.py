"""Skeptic 5b: walk-forward details - picks by |t|, OOS excess, without lag trades, date-demeaned."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from common import *

df = load_events()
df['ex'] = df.three_day - df.groupby('qn').three_day.transform('mean')
df['y_dd'] = df.three_day - df.groupby('i_cut').three_day.transform('mean')
qs = sorted(df.qn.unique())
FI = pd.DataFrame({f: fifth(df, f) for f in CONT})
for ycol in ['three_day', 'y_dd']:
    IC = pd.DataFrame({f: ic_by_q(df, f, ycol) for f in CONT})
    for t0 in [2, 4, 8]:
        for crit in ['absIC', 'abs_t']:
            rows = []; picks = []
            for q in qs:
                if q < t0: continue
                past = IC.loc[[x for x in qs if x < q]]
                score = past.mean().abs() if crit == 'absIC' else (past.mean() / past.std(ddof=1) * np.sqrt(len(past))).abs()
                f = score.idxmax(); sgn = np.sign(past[f].mean()); fav = 5 if sgn > 0 else 1
                g = df[df.qn == q]; sel = g[FI.loc[g.index, f] == fav]
                rows.append(sel.assign(pick=f)); picks.append(f'{q}:{f}{"+" if sgn > 0 else "-"}')
            o = pd.concat(rows)
            o['net'] = o.three_day - COST
            nl = o[~o.lag_trade]
            pq = o.groupby('qn').ex.mean()
            print(f'select on {ycol:9s} start {t0} {crit:5s}: trades {len(o)}, net {o.net.mean():+.2f}%, hit {(o.net > 0).mean():.1%}, '
                  f'excess vs quarter mean {o.ex.mean():+.2f}% (quarters >0 {(pq > 0).sum()}/{len(pq)}), vs same-cutoff mean {o.y_dd.mean():+.2f}%, '
                  f'without lag trades net {nl.net.mean():+.2f}% excess {nl.ex.mean():+.2f}% (n {len(nl)})')
            if crit == 'abs_t' and t0 == 4 and ycol == 'three_day':
                print('     picks:', ' '.join(picks))
