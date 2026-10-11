#!/usr/bin/env python3
"""Pick a fresh random sample (seed 4242) of (symbol, window) points behind A08 / A12 / W_EARLY.
usage: python3 v2_pick.py FEAT_RESULTS SESSIONS OUTDIR"""
import sys
import numpy as np, pandas as pd
f = pd.read_csv(sys.argv[1]); ses = pd.read_csv(sys.argv[2]); OUT = sys.argv[3]
day = pd.to_datetime(ses.day).values
rng = np.random.default_rng(4242)
f['T'] = pd.to_datetime(day[f.i_cut.values]) + pd.Timedelta(hours=15)
A = f[f.three_day.notna()]
pts = []
def add(df, k, tag, back):
    idx = rng.choice(len(df), size=min(k, len(df)), replace=False)
    for r in df.iloc[idx].itertuples():
        pts.append(dict(tag=tag, symbol=r.symbol, qn=r.qn, T=r.T,
                        from_date=(r.T - pd.Timedelta(days=back)).strftime('%d-%m-%Y'),
                        to_date=(r.T + pd.Timedelta(days=1)).strftime('%d-%m-%Y')))
add(A[A.PR30 >= 1], 25, 'A08_in', 31)
add(A[A.PR30 == 0], 8, 'A08_out', 31)
add(A[A.BIZ_RX > 0], 7, 'A12_in', 46)
p = pd.DataFrame(pts)
p.insert(0, 'pid', range(len(p)))
# ticker-change probes: old symbol and new symbol for the same window
tc = [('ZOMATO', '01-06-2023', '30-06-2023'), ('ETERNAL', '01-06-2023', '30-06-2023'),
      ('GMRINFRA', '01-06-2023', '30-06-2023'), ('GMRAIRPORT', '01-06-2023', '30-06-2023'),
      ('LTIM', '01-01-2024', '31-01-2024'), ('LTM', '01-01-2024', '31-01-2024'),
      ('TATAMOTORS', '01-01-2024', '31-01-2024'), ('TMPV', '01-01-2024', '31-01-2024')]
for j, (s, a, b) in enumerate(tc):
    p.loc[len(p)] = dict(pid=1000 + j, tag='ticker', symbol=s, qn=-1, T=pd.NaT, from_date=a, to_date=b)
p.to_csv(f'{OUT}/sample_an.csv', index=False)
W = f[(f.W == True) & (f.tradable_B == True)]
we = W[W.RDCHG < -7]; wn = W[(W.RDCHG >= -7)]
ie = rng.choice(len(we), 15, replace=False); inn = rng.choice(len(wn), 5, replace=False)
w = pd.concat([we.iloc[ie].assign(tag='W_EARLY'), wn.iloc[inn].assign(tag='W_other')])
w[['tag', 'symbol', 'qn', 'RDCHG', 'rdays', 'rdays_ly']].to_csv(f'{OUT}/sample_w.csv', index=False)
print(p.tag.value_counts().to_dict(), w.tag.value_counts().to_dict(), 'unique W symbols', w.symbol.nunique())
