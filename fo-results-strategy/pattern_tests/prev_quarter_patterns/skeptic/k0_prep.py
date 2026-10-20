"""k0: build panel, independent sanity checks of history.csv against events.csv."""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from common import *
F = load()
ev = pd.read_csv(os.path.join(D, 'events.csv'))
ev['fo'] = ev.in_fo.map(lambda v: v is True or v == 'True')
H = ev[ev.three_day.notna()].copy(); H['td'] = H.three_day * 100
H['h'] = H.td - H.groupby('qn').td.transform('mean')
hk = H.set_index(['symbol', 'qn']).h
mx = 0
for k in LAGS:
    v = hk.reindex(pd.MultiIndex.from_arrays([F.symbol, F.qn - k])).to_numpy()
    assert (np.isnan(v) == F[f'h{k}'].isna().to_numpy()).all()
    mx = max(mx, np.nanmax(np.abs(v - F[f'h{k}'].to_numpy())))
print('h1..h8 recomputed from events: max abs diff', f'{mx:.2e}')
fo = ev[ev.fo]; ym = (fo.three_day * 100).groupby(fo.qn).mean()
print('x check', np.abs(F.x - (F.y - F.qn.map(ym))).max())
print(f'results {len(F)}, stocks {F.symbol.nunique()}; share of results sharing a cutoff with another in_fo result '
      f'{(F.n_cut >= 2).mean():.3f} ({int((F.n_cut >= 2).sum())}); with another event of any status {(F.n_cut_all >= 2).mean():.3f}')
print('distinct cutoff sessions per quarter (median)', F.groupby('qn').i_cut.nunique().median())
print('beta median', F.beta.median().round(2), 'missing', F.beta.isna().sum(), '| vol250 missing', F.vol250.isna().sum(),
      '| vix range', F.vix.min(), F.vix.max())
print('corr(y_dd, x) =', F[['y_dd', 'x']].corr().iloc[0, 1].round(3), '; sd x', F.x.std().round(2), 'sd y_dd', F.y_dd.std().round(2),
      'sd x_mm', F.x_mm.std().round(2))
