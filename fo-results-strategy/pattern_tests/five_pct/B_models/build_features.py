"""Build the model table: features.csv + sector extras + new cutoff-time features from the data pack.
Output: model_table.csv (one row per result, 4,460 rows). Everything uses data up to the cutoff close (i_cut)."""
import numpy as np, pandas as pd, os
HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.path.abspath(os.path.join(HERE, '..', '..'))
DATA = os.path.join(SP, 'sector_lab', 'data')

f = pd.read_csv(os.path.join(SP, 'search22', 'features.csv'))
sf = pd.read_csv(os.path.join(SP, 'sector', 'sector_features.csv'))
ev = pd.read_csv(os.path.join(DATA, 'events.csv'))
R = pd.read_csv(os.path.join(DATA, 'returns.csv')).set_index('day')
I = pd.read_csv(os.path.join(DATA, 'intraday.csv')).set_index('day')
IX = pd.read_csv(os.path.join(DATA, 'index_close.csv')).set_index('day')

syms = list(R.columns)
col = {s: j for j, s in enumerate(syms)}
r = R.values.astype(float)
rc = np.clip(r, -0.4, 0.6)                 # guard against a few bad prints for feature purposes
intr = I[syms].values.astype(float)
nifty = IX['Nifty 50'].ffill().values
nret = np.r_[np.nan, nifty[1:] / nifty[:-1] - 1]

# log price paths (NaN where no trade) for MA / highs
lr = np.log1p(rc)
lp = np.where(np.isnan(lr), np.nan, np.nancumsum(np.nan_to_num(lr), axis=0))
lpf = pd.DataFrame(lp).ffill().values
ma50 = pd.DataFrame(lpf).rolling(50, min_periods=40).mean().values
above50 = np.where(np.isnan(ma50) | np.isnan(lp), np.nan, (lpf > ma50).astype(float))
breadth50 = np.nanmean(above50, axis=1)
r5 = pd.DataFrame(rc).rolling(5, min_periods=4).sum().values
xs_disp5 = np.nanstd(r5, axis=1)
ew5 = np.nanmean(r5, axis=1)
nifty_vol20 = pd.Series(nret).rolling(20).std().values

ev = ev.sort_values(['symbol', 'i_cut']).reset_index(drop=True)
rows = []
for e in ev.itertuples():
    out = {'symbol': e.symbol, 'qn': e.qn}
    t = e.i_cut
    j = col.get(e.symbol)
    if j is not None:
        x = rc[:t + 1, j]
        def last(n):
            return x[max(0, t + 1 - n):]
        d = last(3)
        out['d0'], out['d1'], out['d2'] = (d[-1], d[-2], d[-3]) if len(d) == 3 else (np.nan,) * 3
        out['r3d'] = np.nansum(last(3)) if np.isfinite(last(3)).sum() == 3 else np.nan
        w10 = last(10); out['r10d'] = np.nansum(w10) if np.isfinite(w10).sum() >= 8 else np.nan
        ia = intr[t, j]
        out['intra0'] = ia
        out['gap0'] = (1 + r[t, j]) / (1 + ia) - 1 if np.isfinite(ia) and np.isfinite(r[t, j]) else np.nan
        w5, w20, w60, w250 = last(5), last(20), last(60), last(250)
        v5, v20, v60, v250 = (np.nanstd(w) if np.isfinite(w).sum() >= len(w) * .8 else np.nan for w in (w5, w20, w60, w250))
        out['vol5'], out['vol20'], out['vol250'] = v5, v20, v250
        out['vol5_60'] = v5 / v60 if v60 and np.isfinite(v60) else np.nan
        out['vol20_250'] = v20 / v250 if v250 and np.isfinite(v250) else np.nan
        out['maxr20'], out['minr20'] = np.nanmax(w20), np.nanmin(w20)
        out['nbig20'] = np.nansum(np.abs(w20) > 0.04)
        s = 0
        for v in x[::-1]:
            if np.isfinite(v) and v > 0: s += 1
            else: break
        out['up_streak'] = s
        s = 0
        for v in x[::-1]:
            if np.isfinite(v) and v < 0: s += 1
            else: break
        out['down_streak'] = s
        out['z5'] = np.nansum(w5) / (v60 * np.sqrt(5)) if v60 else np.nan
        out['z20'] = np.nansum(w20) / (v60 * np.sqrt(20)) if v60 else np.nan
        # own-history z-score of the 10-day return (vs rolling 10-day returns of the last 250 days)
        if np.isfinite(w250).sum() > 200:
            c = np.nancumsum(np.nan_to_num(w250)); r10s = c[10:] - c[:-10]
            out['z10_own'] = (out['r10d'] - r10s.mean()) / (r10s.std() + 1e-9)
        else:
            out['z10_own'] = np.nan
        # beta / idio vol vs Nifty over 250d / 60d
        nr = nret[max(0, t - 249):t + 1]
        ok = np.isfinite(w250) & np.isfinite(nr)
        if ok.sum() > 150:
            b = np.cov(w250[ok], nr[ok])[0, 1] / np.var(nr[ok]); out['beta250'] = b
            ok6 = ok[-60:]
            res = w250[-60:][ok6] - b * nr[-60:][ok6]
            out['idio60'] = res.std()
        else:
            out['beta250'] = out['idio60'] = np.nan
        out['skew60'] = pd.Series(w60).skew()
        lpw = lpf[max(0, t - 19):t + 1, j]
        out['from_20d_high'] = lpf[t, j] - np.nanmax(lpw) if np.isfinite(lpf[t, j]) else np.nan
    out['nifty_d0'] = nret[t]
    out['nifty_3d'] = np.nansum(nret[t - 2:t + 1])
    out['nifty_vol20'] = nifty_vol20[t]
    out['breadth50'] = breadth50[t]
    out['xs_disp5'] = xs_disp5[t]
    out['ew_mkt5'] = ew5[t]
    rows.append(out)
nf = pd.DataFrame(rows)

# past results-window history of the same stock (only windows whose Day+1 <= cutoff)
ev['absw'] = ev.three_day.abs(); ev['absmove'] = ev.move.abs()
hist = []
for sym, g in ev.groupby('symbol'):
    g = g.sort_values('i_cut')
    for e in g.itertuples():
        p = g[g.i_p1 <= e.i_cut]
        o = {'symbol': sym, 'qn': e.qn, 'past_n': len(p)}
        if len(p):
            o['past_abs3d'] = p.absw.mean(); o['past_absmove'] = p.absmove.mean()
            o['past_frac_gt5'] = (p.three_day > .05).mean(); o['past_frac_lt5'] = (p.three_day < -.05).mean()
            o['past_dm1'] = p.ret_dm1.mean()
            # mean 10-day pre-cutoff run-up in past results seasons
            j = col.get(sym)
            if j is not None:
                ru = [np.nansum(rc[max(0, ic - 9):ic + 1, j]) for ic in p.i_cut]
                o['past_runup10'] = np.mean(ru)
        hist.append(o)
hf = pd.DataFrame(hist)

# season context: number of companies reported (Day-of-reaction completed) by the cutoff
ev_q = ev[['qn', 'i_react']].copy()
cnt = []
for e in ev.itertuples():
    q = ev_q[ev_q.qn == e.qn]
    cnt.append({'symbol': e.symbol, 'qn': e.qn, 'n_reported': int((q.i_react <= e.i_cut).sum()),
                'fiscal_q': e.qn % 4, 'rd_weekday': pd.Timestamp(e.results_date).weekday()})
cf = pd.DataFrame(cnt)

drop_sf = ['quarter', 'qn', 'results_date', 'cutoff', 'industry', 'fin_type', 'timing', 'three_day', 'excess_nifty',
           'in_fo', 'tp3', 'peers_reported_3d', 'nifty_1m', 'nifty_3m', 'india_vix', 'season_so_far_3d']
sfx = sf.drop(columns=[c for c in drop_sf if c != 'qn'])
T = f.merge(sfx, on=['symbol', 'qn'], how='left').merge(nf, on=['symbol', 'qn'], how='left') \
     .merge(hf, on=['symbol', 'qn'], how='left').merge(cf, on=['symbol', 'qn'], how='left')
T['fin_type_code'] = T.fin_type.astype('category').cat.codes
assert len(T) == len(f)
T.to_csv(os.path.join(HERE, 'model_table.csv'), index=False)
print(T.shape)
newc = list(sfx.columns[1:]) + list(nf.columns[2:]) + list(hf.columns[2:]) + list(cf.columns[2:])
print(T[newc].describe().T[['count', 'mean', 'min', 'max']].to_string())
