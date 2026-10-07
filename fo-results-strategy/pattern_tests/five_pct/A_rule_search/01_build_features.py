"""
01_build_features.py  --  build one feature table for the +5% rule search.

PLAN (written before running anything):
  * Start from search22/features.csv (4,460 results, 49 cutoff-time features).
  * Add the 9 sector features from sector/sector_features.csv that are not already
    in features.csv (sec_vs_nifty_1w/1m/3m, sec_rank_1m/3m, sec_vs_50dma/200dma,
    sec_from_52w_high, sec_reported_3d).  The other sector columns are exact copies.
  * Build NEW features from the daily price files, using only sessions up to and
    including the cutoff session (i_cut):
      d0, d1, d2           stock return on the cutoff day, 1 and 2 sessions earlier
      r2d, r3d, r10d, r20d compounded return over the last 2/3/10/20 sessions
      gap0, intra0         cutoff-day open gap and open-to-close move
      gap5, intra5         sum of gaps / open-to-close moves over the last 5 sessions
      nifty_d0, nifty_3d   Nifty 50 return on cutoff day / last 3 sessions
      exn_d0, exn_3d, exn_10d   stock minus Nifty 50 over the same windows
      sec_d0, sec_3d, exs_3d    sector index return and stock-minus-sector (3 sessions)
      dist_20h, dist_20l, dist_60h  distance of the cutoff close from the 20/60-session high/low
      streak               signed run of consecutive up (+) / down (-) days ending at cutoff
      vol5_60, vol20_60    recent realised volatility relative to 60-session volatility
      maxabs5              largest absolute daily move in the last 5 sessions
      z5, z20              5/20-session return divided by 60-session vol (scaled)
      up10                 share of up days in the last 10 sessions
      pre5_vs_own          5-session pre-cutoff return minus this stock's average
                           pre-cutoff 5-session return in its earlier result seasons
      own_dm1, own_rd, own_dp1, own_abs3d   stock's average Day-1 / Result-day / Day+1 return
                           and average |3-day| in its earlier seasons (in this data set)
      n_prior              number of earlier seasons in the data
      cal_days             calendar days from cutoff to results date
      fq                   fiscal quarter (1..4; 4 = annual results)
  * Categorical columns kept for equality conditions: fin_type, sector_index, industry.
  * results timing / after_close are NOT used (usually unknown in advance).
Output: features_all.csv in this folder.
"""
import numpy as np, pandas as pd, os

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.abspath(os.path.join(HERE, '..', '..'))
F = pd.read_csv(f'{SP}/search22/features.csv')
S = pd.read_csv(f'{SP}/sector/sector_features.csv')
E = pd.read_csv(f'{SP}/sector_lab/data/events.csv')
R = pd.read_csv(f'{SP}/sector_lab/data/returns.csv')
I = pd.read_csv(f'{SP}/sector_lab/data/intraday.csv')
IX = pd.read_csv(f'{SP}/sector_lab/data/index_close.csv')

sec_extra = ['sec_vs_nifty_1w', 'sec_vs_nifty_1m', 'sec_vs_nifty_3m', 'sec_rank_1m', 'sec_rank_3m',
             'sec_vs_50dma', 'sec_vs_200dma', 'sec_from_52w_high', 'sec_reported_3d']
df = F.merge(S[['symbol', 'qn'] + sec_extra], on=['symbol', 'qn'], how='left')
df = df.merge(E[['symbol', 'qn', 'i_cut', 'i_m1', 'i_rd', 'i_p1', 'sector_index', 'ret_dm1', 'ret_rd', 'ret_dp1']],
              on=['symbol', 'qn'], how='left')
assert df.i_cut.notna().all()
df['i_cut'] = df.i_cut.astype(int)

Rv = R.drop(columns='day')
Iv = I.drop(columns='day')
assert (R.day.values == I.day.values).all() and (R.day.values == IX.day.values).all()
sym_idx = {s: k for k, s in enumerate(Rv.columns)}
RA = Rv.values.astype(float)        # sessions x symbols
IA = Iv[Rv.columns].values.astype(float)
nifty = IX['Nifty 50'].values.astype(float)
nifty_r = np.r_[np.nan, nifty[1:] / nifty[:-1] - 1]


def comp(x):
    x = x[~np.isnan(x)]
    return np.prod(1 + x) - 1 if len(x) else np.nan


rows = []
for k, ev in df.iterrows():
    j = sym_idx[ev.symbol]
    i = ev.i_cut
    r = RA[:i + 1, j]
    w60 = r[-60:]
    o = {}
    o['d0'], o['d1'], o['d2'] = r[-1], r[-2], r[-3]
    o['r2d'] = comp(r[-2:]); o['r3d'] = comp(r[-3:]); o['r10d'] = comp(r[-10:]); o['r20d'] = comp(r[-20:])
    intr = IA[:i + 1, j]
    gap = (1 + r) / (1 + intr) - 1
    o['gap0'], o['intra0'] = gap[-1], intr[-1]
    o['gap5'] = np.nansum(gap[-5:]) if np.isfinite(gap[-5:]).sum() >= 3 else np.nan
    o['intra5'] = np.nansum(intr[-5:]) if np.isfinite(intr[-5:]).sum() >= 3 else np.nan
    nr = nifty_r[:i + 1]
    o['nifty_d0'] = nr[-1]; o['nifty_3d'] = comp(nr[-3:])
    o['exn_d0'] = o['d0'] - o['nifty_d0']; o['exn_3d'] = o['r3d'] - o['nifty_3d']
    o['exn_10d'] = o['r10d'] - comp(nr[-10:])
    si = ev.sector_index
    if isinstance(si, str) and si in IX.columns:
        sc = IX[si].values[:i + 1].astype(float)
        if np.isfinite(sc[-4:]).all():
            o['sec_d0'] = sc[-1] / sc[-2] - 1; o['sec_3d'] = sc[-1] / sc[-4] - 1
            o['exs_3d'] = o['r3d'] - o['sec_3d']
    # price path (missing return days treated as flat) for highs/lows
    valid60 = np.isfinite(w60).sum()
    p = np.cumprod(1 + np.nan_to_num(r[-61:]))
    if valid60 >= 45:
        o['dist_20h'] = p[-1] / p[-20:].max() - 1
        o['dist_20l'] = p[-1] / p[-20:].min() - 1
        o['dist_60h'] = p[-1] / p[-60:].max() - 1
        sd60 = np.nanstd(w60)
        o['vol5_60'] = np.nanstd(r[-5:]) / sd60 if sd60 > 0 else np.nan
        o['vol20_60'] = np.nanstd(r[-20:]) / sd60 if sd60 > 0 else np.nan
        o['maxabs5'] = np.nanmax(np.abs(r[-5:]))
        o['z5'] = comp(r[-5:]) / (sd60 * np.sqrt(5)) if sd60 > 0 else np.nan
        o['z20'] = comp(r[-20:]) / (sd60 * np.sqrt(20)) if sd60 > 0 else np.nan
        o['up10'] = np.nanmean(r[-10:] > 0)
    # streak
    st = 0
    for x in r[::-1]:
        if not np.isfinite(x) or x == 0:
            break
        if st == 0:
            st = 1 if x > 0 else -1
        elif (x > 0) == (st > 0):
            st += 1 if st > 0 else -1
        else:
            break
    o['streak'] = st
    o['pre5'] = comp(r[-5:])
    rows.append(o)
new = pd.DataFrame(rows, index=df.index)
df = pd.concat([df, new], axis=1)

# own-history features (only earlier seasons of the same stock, all completed before this cutoff)
df = df.sort_values(['symbol', 'qn']).reset_index(drop=True)
g = df.groupby('symbol')
for col, src in [('own_dm1', 'ret_dm1'), ('own_rd', 'ret_rd'), ('own_dp1', 'ret_dp1'), ('own_pre5', 'pre5')]:
    df[col] = g[src].transform(lambda s: s.shift(1).expanding().mean())
df['abs3'] = df.three_day.abs()
df['own_abs3d'] = g['abs3'].transform(lambda s: s.shift(1).expanding().mean())
df['n_prior'] = g.cumcount()
# require at least 2 earlier seasons for own-history averages
for col in ['own_dm1', 'own_rd', 'own_dp1', 'own_pre5', 'own_abs3d']:
    df.loc[df.n_prior < 2, col] = np.nan
df['pre5_vs_own'] = df.pre5 - df.own_pre5
# sanity: the previous season's window must have finished before this cutoff
prev_p1 = g['i_p1'].shift(1)
assert ((prev_p1.isna()) | (prev_p1 < df.i_cut)).all()
df['cal_days'] = (pd.to_datetime(df.results_date) - pd.to_datetime(df.cutoff)).dt.days
df['fq'] = df.quarter.str.slice(1, 2).astype(int)
df = df.drop(columns=['abs3', 'ret_dm1', 'ret_rd', 'ret_dp1', 'own_pre5', 'i_m1', 'i_rd', 'i_p1'])
df = df.sort_values(['qn', 'results_date', 'symbol']).reset_index(drop=True)
df.to_csv(f'{HERE}/features_all.csv', index=False)
print(df.shape)
newcols = list(new.columns) + ['own_dm1', 'own_rd', 'own_dp1', 'own_abs3d', 'pre5_vs_own', 'n_prior', 'cal_days', 'fq']
print(df[newcols].describe().T[['count', 'mean', 'std', 'min', 'max']].round(4).to_string())
print('corr with three_day (in_fo):')
fo = df[df.in_fo]
print(fo[newcols + sec_extra].corrwith(fo.three_day).round(3).sort_values().to_string())
