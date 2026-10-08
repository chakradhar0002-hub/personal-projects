"""
01b_volume_placebo.py -- add volume_5d_vs_60d to the placebo panel (added after 02 ran: prereg had marked S20 as
"no placebo" because the data pack has no volume; the project's price DB does).  Same definition as features22.py:
mean volume of the last 5 sessions (days the stock traded with volume > 0) / mean of the last 60 sessions.
Checked against features_all at the real cutoffs.  Reads the DB read-only.  Writes placebo_vol.csv.
"""
import os, sqlite3
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.abspath(os.path.join(HERE, '..', '..'))
S = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv')
R = pd.read_csv(f'{SP}/sector_lab/data/returns.csv', nrows=1)
syms = [c for c in R.columns if c != 'day']
con = sqlite3.connect(f'file:{SP}/report/nse_prices.db?mode=ro', uri=True)
V = pd.read_sql('SELECT day, symbol, volume FROM px', con)
V = V[V.symbol.isin(syms)]
W = V.pivot(index='day', columns='symbol', values='volume').reindex(S.day.values)
W = W.where(W > 0)
print('symbols with volume', W.notna().any().sum(), 'of', len(syms))
v5 = W.rolling(5, min_periods=1).mean()
v60 = W.rolling(60, min_periods=1).mean()
ratio = (v5 / v60).reset_index(drop=True)

FA = pd.read_csv(f'{SP}/five_pct/A_rule_search/features_all.csv')
rec = np.array([ratio.at[c, s] if s in ratio.columns else np.nan for s, c in zip(FA.symbol, FA.i_cut)])
a = FA.volume_5d_vs_60d.values
ok = np.isfinite(a) & np.isfinite(rec)
print('check vs features_all: n', ok.sum(), 'of', np.isfinite(a).sum(), 'corr %.5f' % np.corrcoef(a[ok], rec[ok])[0, 1],
      'median |diff| %.2e' % np.median(np.abs(a[ok] - rec[ok])), 'share |diff|<1e-6 %.3f' % (np.abs(a[ok] - rec[ok]) < 1e-6).mean())
PL = pd.read_csv(f'{HERE}/placebo.csv')
PL['volume_5d_vs_60d'] = [ratio.at[c, s] if s in ratio.columns else np.nan for s, c in zip(PL.symbol, PL.c)]
print('placebo rows with volume ratio', PL.volume_5d_vs_60d.notna().sum(), 'of', len(PL))
PL.to_csv(f'{HERE}/placebo_vol.csv', index=False)
