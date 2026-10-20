#!/usr/bin/env python3
"""Per-result history table for the "each previous quarter" study (see PLAN.txt next to this file).

One row per in_fo result (3,278): outcome y (three-day sum, %), x (y minus the in_fo mean of the quarter), and the same
stock's history: h at lags 1..8 (three-day sum of the event exactly k quarters back, any F&O status, minus the mean of
all events of that quarter), the lag-1 day components, up/down sequences of the last 2/3/4, signed streak, counts of
ups, averages, best/worst of the last 4, |three_day| at lags 1..8 and the 60-session volatility at the cutoff.
Also runs the two validations of PLAN.txt (QUARTER_CORRELATION.md lag-1 r, PAST_PERFORMANCE.md last-4 top tenth) and
flags the lag 10% + volume rule trades and the last-4 top-tenth signal for the overlap in item H.

Reads LAB_ROOT/sector_lab/data/{events,returns}.csv and REPO_ROOT/results/lag10_volume/trades.csv; writes
OUT/history.csv and OUT/build.log (run_tests.py copies build.log into run.log).
"""
import os
import numpy as np
import pandas as pd

REPO = os.environ.get('REPO_ROOT', '.')
LAB = os.environ.get('LAB_ROOT', 'lab')
OUT = os.environ.get('OUT', os.path.join(REPO, 'results', 'prev_quarter_patterns'))
D = os.path.join(LAB, 'sector_lab', 'data')
os.makedirs(OUT, exist_ok=True)
LAGS = range(1, 9)
NQ = 22

log = []
def P(*a):
    s = ' '.join(str(v) for v in a)
    log.append(s)
    print(s)

def fp(v):
    return '-' if v is None or pd.isna(v) else f'{v:+.2f}'

P('== build_history.py ==')
ev = pd.read_csv(os.path.join(D, 'events.csv'))
assert len(ev) == 4462 and not ev.duplicated(['symbol', 'qn']).any()
assert sorted(ev.qn.unique()) == list(range(NQ))
for c in ('i_cut', 'i_m1', 'i_rd', 'i_p1', 'i_react'):
    assert ev[c].notna().all()
    ev[c] = ev[c].astype(int)
assert ((ev.i_m1 == ev.i_cut + 1) & (ev.i_rd == ev.i_m1 + 1) & (ev.i_p1 == ev.i_rd + 1)).all()
ev['fo'] = ev.in_fo.map(lambda v: v is True or v == 'True')
ok = ev.three_day.notna()
assert np.allclose(ev.three_day[ok], (ev.ret_dm1 + ev.ret_rd + ev.ret_dp1)[ok], rtol=0, atol=1e-12)
P(f'events {len(ev)}, with three_day {int(ok.sum())}, in_fo {int(ev.fo.sum())}, stocks {ev.symbol.nunique()}')

# ---------------------------------------------------------------- history events (any F&O status, three_day present)
H = ev[ok].copy()
assert len(H) == 4460
H['td'] = H.three_day * 100
qm_all = H.groupby('qn').td.mean()
H['h'] = H.td - H.qn.map(qm_all)
for c, n in (('ret_dm1', 'c_dm1'), ('ret_rd', 'c_rd'), ('ret_dp1', 'c_dp1')):
    H[n] = H[c] * 100 - H.groupby('qn')[c].transform('mean') * 100
P('all-event quarter means of three_day (%), used to centre h: ' + ', '.join(f'q{q} {fp(v)}' for q, v in qm_all.items()))
HK = H.set_index(['symbol', 'qn'])

# ---------------------------------------------------------------- outcomes (in_fo results)
F = ev[ev.fo].copy().sort_values(['qn', 'symbol']).reset_index(drop=True)
assert len(F) == 3278 and F.three_day.notna().all()
F['y'] = F.three_day * 100
F['x'] = F.y - F.groupby('qn').y.transform('mean')
P(f'in_fo results {len(F)} from {F.symbol.nunique()} stocks; per quarter ' +
  ', '.join(f'q{q} {n}' for q, n in F.groupby('qn').size().items()))

for k in LAGS:
    key = pd.MultiIndex.from_arrays([F.symbol, F.qn - k])
    got = key.isin(HK.index)
    sub = HK.reindex(key)
    F[f'h{k}'] = sub.h.to_numpy()
    F[f'abs{k}'] = sub.td.abs().to_numpy()
    # no look-ahead: the lag event's Day+1 and reaction day closed before this result's cutoff session
    bad = got & ~((sub.i_p1.to_numpy() < F.i_cut.to_numpy()) & (sub.i_react.to_numpy() < F.i_cut.to_numpy()))
    assert not bad.any(), (k, int(bad.sum()))
    if k == 1:
        for c in ('c_dm1', 'c_rd', 'c_dp1'):
            F[f'l1_{c[2:]}'] = sub[c].to_numpy()
        F['l1_qn_close_after_cut'] = np.nan
    P(f'lag {k}: {int(got.sum())} results have the event exactly {k} quarter(s) back '
      f'(look-ahead check passed: its Day+1 and reaction day are before the cutoff)')
assert np.allclose(F.l1_dm1 + F.l1_rd + F.l1_dp1, F.h1, equal_nan=True, atol=1e-9)
F = F.drop(columns='l1_qn_close_after_cut')

# late reporters of quarter t-1 whose window closes after an early cutoff of quarter t (affects only the centring)
last_p1 = H.groupby('qn').i_p1.max()
late = int(sum(((F.qn == q) & (F.i_cut <= last_p1[q - 1])).sum() for q in range(1, NQ)))
P(f'centring note: {late} in_fo results have a cutoff on or before the last Day+1 of quarter t-1 '
  '(the quarter-(t-1) mean is then not fully known at their cutoff; this shifts h of a whole quarter by one constant)')

# ---------------------------------------------------------------- sequences, streaks, counts, averages
Hm = F[[f'h{k}' for k in LAGS]].to_numpy()
UP = np.where(np.isnan(Hm), np.nan, (Hm > 0).astype(float))
for L in (2, 3, 4):
    have = ~np.isnan(UP[:, :L]).any(axis=1)
    lab = [''.join('U' if UP[i, j] == 1 else 'D' for j in range(L - 1, -1, -1)) if have[i] else ''
           for i in range(len(F))]          # oldest first: the last letter is last quarter's result
    F[f'seq{L}'] = pd.Series(lab).replace('', np.nan)
streak = np.full(len(F), np.nan)
for i in range(len(F)):
    if np.isnan(UP[i, 0]):
        continue
    d = UP[i, 0]
    j = 1
    while j < 4 and not np.isnan(UP[i, j]) and UP[i, j] == d:
        j += 1
    if j < 4 and np.isnan(UP[i, j]):
        continue                            # the streak's end is not observed
    streak[i] = j if d == 1 else -j
F['streak'] = streak
F['up_streak'] = np.where(np.isnan(streak), np.nan, np.where(streak > 0, streak, 0))
F['down_streak'] = np.where(np.isnan(streak), np.nan, np.where(streak < 0, -streak, 0))
all4 = ~np.isnan(Hm[:, :4]).any(axis=1)
all8 = ~np.isnan(Hm).any(axis=1)
all2 = ~np.isnan(Hm[:, :2]).any(axis=1)
F['n_up4'] = np.where(all4, np.nansum(UP[:, :4], axis=1), np.nan)
F['n_up8'] = np.where(all8, np.nansum(UP, axis=1), np.nan)
F['mean_h2'] = np.where(all2, Hm[:, :2].mean(axis=1), np.nan)
F['mean_h4'] = np.where(all4, Hm[:, :4].mean(axis=1), np.nan)
F['mean_h8'] = np.where(all8, Hm.mean(axis=1), np.nan)
F['best4'] = np.where(all4, np.nanmax(np.where(all4[:, None], Hm[:, :4], 0), axis=1), np.nan)
F['worst4'] = np.where(all4, np.nanmin(np.where(all4[:, None], Hm[:, :4], 0), axis=1), np.nan)
for c in ('seq2', 'seq3', 'seq4', 'streak', 'n_up4', 'n_up8', 'mean_h2', 'mean_h4', 'mean_h8', 'best4', 'worst4'):
    P(f'{c}: {int(F[c].notna().sum())} results')

# ---------------------------------------------------------------- 60-session volatility at the cutoff
R = pd.read_csv(os.path.join(D, 'returns.csv'))
assert 'day' in R.columns
Rm = R.drop(columns='day')
assert set(F.symbol) <= set(Rm.columns)
ses_res = {s: set(np.r_[g.i_m1, g.i_rd, g.i_p1].tolist()) for s, g in ev.groupby('symbol')}
v60, v60x, nv = [], [], []
for s, ic in zip(F.symbol, F.i_cut):
    w = np.arange(ic - 59, ic + 1)
    r = Rm[s].to_numpy()[w]
    m = ~np.isnan(r)
    v60.append(np.std(r[m], ddof=1) * 100 if m.sum() >= 40 else np.nan)
    keep = m & ~np.isin(w, list(ses_res[s]))
    v60x.append(np.std(r[keep], ddof=1) * 100 if keep.sum() >= 40 else np.nan)
    nv.append(int(m.sum()))
F['vol60'] = v60
F['vol60_ex'] = v60x
P(f'vol60 (sd of daily returns over sessions i_cut-59..i_cut, %): {int(F.vol60.notna().sum())} results '
  f'(median {F.vol60.median():.2f}); vol60_ex (own results sessions removed): {int(F.vol60_ex.notna().sum())}; '
  f'Spearman vol60 vs vol60_ex {F[["vol60", "vol60_ex"]].corr(method="spearman").iloc[0, 1]:.3f}')

# ---------------------------------------------------------------- validation 1: QUARTER_CORRELATION.md lag-1 r
st = F[['symbol', 'qn', 'x']].copy()          # x_qc = three_day% minus the in_fo quarter mean: same as our x
k1 = st.set_index(['symbol', 'qn']).x
nxt = st.assign(qn=st.qn + 1).set_index(['symbol', 'qn']).x
pair = pd.concat([nxt.rename('a'), k1.rename('b')], axis=1, join='inner')
r_qc = np.corrcoef(pair.a, pair.b)[0, 1]
P(f'VALIDATION 1 (QUARTER_CORRELATION.md definition: both results in_fo, x centred on the in_fo quarter mean, '
  f'pooled Pearson): {len(pair)} pairs, r {r_qc:+.4f} = {r_qc:+.2f} at 2 decimals (doc: 3,050 pairs, -0.01)')
assert len(pair) == 3050 and abs(r_qc - (-0.01)) < 0.005
m1 = F.h1.notna()
r_ours = np.corrcoef(F.x[m1], F.h1[m1])[0, 1]
P(f'  ours (history of any F&O status, centred on the all-event quarter mean): {int(m1.sum())} results with lag 1, '
  f'pooled Pearson x vs h1 {r_ours:+.3f}; the main test (A1) is a within-quarter Spearman averaged over quarters')

# ---------------------------------------------------------------- validation 2: PAST_PERFORMANCE.md last-4 top tenth
ev['h_td'] = ev.three_day * 100
G = {s: g.sort_values('qn', ascending=False) for s, g in ev.groupby('symbol')}
td4 = []
for s, q, dec in zip(F.symbol, F.qn, F.i_cut):
    g = G[s]
    h = g[(g.qn < q) & (g.i_p1 < dec) & (g.i_react < dec)]
    td4.append(h.h_td.iloc[:4].mean() if len(h) >= 4 else np.nan)
F['pp_last4'] = td4
f4 = F[F.pp_last4.notna()]
pct = f4.groupby('qn').pp_last4.rank(pct=True)
F['pp_top10'] = False
F.loc[f4.index[pct > 0.9], 'pp_top10'] = True
F['pp_top5'] = False
F.loc[f4.index[pct > 0.8], 'pp_top5'] = True
t10 = F[F.pp_top10]
P(f'VALIDATION 2 (PAST_PERFORMANCE.md last-4 average, top tenth within the quarter): {len(f4)} results with 4 earlier '
  f'results; top tenth {len(t10)} trades, average three-day {fp(t10.y.mean())}% (doc: 292 trades, +1.07%); top fifth '
  f'{int(F.pp_top5.sum())} trades {fp(F[F.pp_top5].y.mean())}% (doc: 569, +0.53%)')
assert len(t10) == 292 and abs(t10.y.mean() - 1.07) < 0.005 and int(F.pp_top5.sum()) == 569
m4 = F.mean_h4.notna()
P(f'  ours: mean_h4 needs lags 1-4 all present and is centred: {int(m4.sum())} results (vs {len(f4)}); '
  f'Spearman mean_h4 vs pp_last4 on common results {F.loc[m4, ["mean_h4", "pp_last4"]].corr(method="spearman").iloc[0, 1]:.3f}')

# ---------------------------------------------------------------- lag 10% + volume rule trades
lv = pd.read_csv(os.path.join(REPO, 'results', 'lag10_volume', 'trades.csv'))
kk = pd.MultiIndex.from_arrays([lv.symbol, lv.qn])
fk = pd.MultiIndex.from_arrays([F.symbol, F.qn])
F['lag10vol'] = fk.isin(kk)
P(f'lag 10% + volume rule: {len(lv)} trades in trades.csv, {int(F.lag10vol.sum())} matched to in_fo results')
assert int(F.lag10vol.sum()) == len(lv)
mt = F.set_index(['symbol', 'qn']).y.reindex(kk).to_numpy()
assert np.allclose(mt / 100, lv.three_day.to_numpy(), atol=1e-6)      # same three-day sums as the rule's trades

cols = (['symbol', 'qn', 'period', 'quarter', 'results_date', 'timing', 'i_cut', 'y', 'x'] +
        [f'h{k}' for k in LAGS] + ['l1_dm1', 'l1_rd', 'l1_dp1', 'seq2', 'seq3', 'seq4', 'streak', 'up_streak',
                                   'down_streak', 'n_up4', 'n_up8', 'mean_h2', 'mean_h4', 'mean_h8', 'best4', 'worst4'] +
        [f'abs{k}' for k in LAGS] + ['vol60', 'vol60_ex', 'pp_last4', 'pp_top5', 'pp_top10', 'lag10vol'])
# 10 significant digits: '%.6g' merged two distinct values (HINDPETRO / LT, qn 4) into a tie and moved quarter ICs
F[cols].to_csv(os.path.join(OUT, 'history.csv'), index=False, float_format='%.10g')
P(f'wrote history.csv: {len(F)} rows, {len(cols)} columns')
with open(os.path.join(OUT, 'build.log'), 'w') as fh:
    fh.write('\n'.join(log) + '\n')
