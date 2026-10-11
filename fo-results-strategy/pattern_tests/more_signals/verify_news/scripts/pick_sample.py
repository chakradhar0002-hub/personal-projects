#!/usr/bin/env python3
"""Pick a random sample of (symbol, cutoff day) points behind the candidates for a raw re-download check.
usage: python3 -P pick_sample.py SP WORK
Writes WORK/sample.csv: tag, symbol, qn, cut_day, from_date, to_date (dd-mm-yyyy; window = cutoff-32d .. cutoff+1d)."""
import sys

import numpy as np
import pandas as pd

SP, WK = sys.argv[1], sys.argv[2]
f = pd.read_csv(f'{WK}/my_feat.csv')
out = pd.read_csv(f'{SP}/perf/features/outcomes.csv', usecols=['symbol', 'qn', 'three_day', 'tradable_B'])
f = f.merge(out, on=['symbol', 'qn'])
ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv')
day = pd.to_datetime(ses.day)
rng = np.random.default_rng(424242)
A = f[f.three_day.notna()]
pick = []
pick.append(A[A.pr30 >= 1].sample(30, random_state=1).assign(tag='A08_in'))
pick.append(A[A.pr30 == 0].sample(12, random_state=2).assign(tag='A08_out'))
pick.append(A[A.biz_rx45 > 0].sample(8, random_state=3).assign(tag='A12_in'))
early = f[(f.rdchg < -7) & f.rdchg_ok & (f.W == True) & (f.tradable_B == True)]
pick.append(early.sample(6, random_state=4).assign(tag='W_EARLY'))
# renamed tickers (old periods) - deliberate
ren = A[A.symbol.isin(['TMPV', 'ZYDUSLIFE', 'ETERNAL', 'LTIM']) & (A.qn <= 12)]
pick.append(ren.sample(min(6, len(ren)), random_state=5).assign(tag='renamed_old'))
s = pd.concat(pick).drop_duplicates(['symbol', 'qn'])
s['cut_day'] = day.iloc[s.i_cut.to_numpy(int)].to_numpy()
s['from_date'] = (s.cut_day - pd.Timedelta(days=32)).dt.strftime('%d-%m-%Y')
s['to_date'] = (s.cut_day + pd.Timedelta(days=1)).dt.strftime('%d-%m-%Y')
s[['tag', 'symbol', 'qn', 'cut_day', 'from_date', 'to_date']].to_csv(f'{WK}/sample.csv', index=False)
print(s.tag.value_counts().to_dict(), len(s))
