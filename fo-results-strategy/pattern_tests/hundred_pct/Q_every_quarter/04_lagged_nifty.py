"""
04_lagged_nifty.py -- the earlier candidate "stock lagged Nifty by > 15% over the month" (vs_nifty_1m =
21-session stock return minus 21-session Nifty 50 return, at the cutoff close), long, take-profit exit
(reported 51 trades, 15 of 16 quarters with picks positive).

Checks (all prespecified in 00_plan.txt):
  thresholds -10/-12/-15/-18/-20%;  3-day and TP exit;  gross and after 0.17%;
  quarters positive in first 14 vs last 8;  without the best 5 trades;
  random-pick baseline: same number of random F&O results in each quarter (5,000 draws);
  sign-flip baseline: the rule's own trades flipped around their quarter's all-F&O mean (5,000 draws);
  placebo on non-results dates: cutoff t with no result session within 10 sessions of the window
  (no result session in [t-9, t+13]), same filter, 3-day = sum of returns t+1..t+3 (TP analog);
  (a) one random eligible date per stock per season, 500 draws;  (b) every eligible date.
Output: out/lagged_nifty.csv, out/lagged_nifty_placebo.csv, out/lagged_nifty_trades.csv
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qengine as E

OUT = os.path.join(E.HERE, 'out')
D = os.path.join(E.SP, 'sector_lab', 'data')
df = E.load('fo')
qn = df.qn.values
rng = np.random.default_rng(2024)
THS = [-0.10, -0.12, -0.15, -0.18, -0.20]
EXITS = {'3day': 'three_day', 'tp': 'tp3'}
qmean_all = {ex: df.groupby('qn')[c].mean() for ex, c in EXITS.items()}


def qstats(p, q):
    qa = pd.Series(p).groupby(q).mean()
    return qa


rows, trades = [], []
for th in THS:
    m = df.vs_nifty_1m.values < th
    for ex, col in EXITS.items():
        p = df[col].values[m]; q = qn[m]
        qa = qstats(p, q)
        d = {'threshold_pct': 100 * th, 'exit': ex, 'trades': len(p), 'win_rate_pct': 100 * (p > 0).mean(),
             'win_rate_net_pct': 100 * (p > E.COST).mean(), 'avg_pct': 100 * p.mean(), 'avg_net_pct': 100 * (p.mean() - E.COST),
             'worst_trade_pct': 100 * p.min(), 'quarters_with_picks': len(qa), 'quarters_pos': int((qa > 0).sum()),
             'quarters_pos_net': int((qa > E.COST).sum()),
             'first14': f"{int((qa[qa.index < 14] > 0).sum())}/{int((qa.index < 14).sum())}",
             'last8': f"{int((qa[qa.index >= 14] > 0).sum())}/{int((qa.index >= 14).sum())}",
             'first14_avg_pct': 100 * p[q < 14].mean() if (q < 14).any() else np.nan,
             'last8_avg_pct': 100 * p[q >= 14].mean() if (q >= 14).any() else np.nan,
             'failing_quarters': ';'.join(f"q{k}:{100 * v:.2f}" for k, v in qa[qa <= 0].items()),
             'worst_quarter_pct': 100 * qa.min(), 'trades_per_quarter_median': float(pd.Series(q).value_counts().median())}
        # without the best 5 trades
        o = np.argsort(-p)[5:]
        p5, q5 = p[o], q[o]
        qa5 = qstats(p5, q5)
        d.update(avg_wo_best5_pct=100 * p5.mean(), quarters_with_picks_wo_best5=len(qa5),
                 quarters_pos_wo_best5=int((qa5 > 0).sum()))
        # random-pick baseline and sign-flip baseline (same picks per quarter)
        cnt = pd.Series(q).value_counts()
        allp = {qq: df[col].values[qn == qq] for qq in cnt.index}
        obs = d['quarters_pos']
        rp, sf = np.zeros(5000, int), np.zeros(5000, int)
        rpa, sfa = np.zeros(5000), np.zeros(5000)
        qm = qmean_all[ex]
        dev = p - qm.loc[q].values
        for k in range(5000):
            tot, n, pos = 0.0, 0, 0
            for qq, c in cnt.items():
                x = rng.choice(allp[qq], c, replace=False)
                pos += x.mean() > 0; tot += x.sum(); n += c
            rp[k], rpa[k] = pos, tot / n
            s = rng.choice([-1.0, 1.0], len(p))
            pf = qm.loc[q].values + s * dev
            # vectorised per quarter mean
            sums = np.bincount(pd.factorize(q, sort=True)[0], weights=pf)
            ns = np.bincount(pd.factorize(q, sort=True)[0])
            sf[k] = int(((sums / ns) > 0).sum()); sfa[k] = pf.mean()
        d.update(randompick_mean_quarters_pos=rp.mean(), randompick_p_ge_obs=float((rp >= obs).mean()),
                 randompick_p_all_pos=float((rp == len(qa)).mean()), randompick_avg_pct=100 * rpa.mean(),
                 signflip_mean_quarters_pos=sf.mean(), signflip_p_ge_obs=float((sf >= obs).mean()),
                 signflip_p_avg_ge_obs=float((sfa >= p.mean()).mean()))
        rows.append(d)
        if th == -0.15:
            t = df.loc[m, ['symbol', 'quarter', 'qn', 'cutoff', 'vs_nifty_1m', 'three_day', 'tp3']].copy()
            trades.append(t)
L = pd.DataFrame(rows)
L.to_csv(f'{OUT}/lagged_nifty.csv', index=False)
pd.concat(trades).drop_duplicates().to_csv(f'{OUT}/lagged_nifty_trades.csv', index=False)
pd.set_option('display.width', 250)
print(L.drop(columns=['failing_quarters']).round(3).to_string(index=False))
print(L[['threshold_pct', 'exit', 'failing_quarters']].to_string(index=False))

# ------------------------------------------------------------------ placebo on non-results dates
E_ = pd.read_csv(f'{D}/events.csv', usecols=['symbol', 'qn', 'i_cut', 'i_rd', 'i_react', 'in_fo'])
Rr = pd.read_csv(f'{D}/returns.csv')
IX = pd.read_csv(f'{D}/index_close.csv', usecols=['day', 'Nifty 50'])
assert (Rr.day.values == IX.day.values).all()
syms = list(Rr.columns[1:]); col = {s: j for j, s in enumerate(syms)}
R = Rr[syms].values.astype(float)
T = len(R)
P = np.nancumprod(np.where(np.isnan(R), 0, R) + 1, axis=0)
first = np.array([np.argmax(~np.isnan(R[:, j])) for j in range(len(syms))])
nif = IX['Nifty 50'].values.astype(float)
n21 = np.full(T, np.nan); n21[21:] = nif[21:] / nif[:-21] - 1
r21 = np.full_like(P, np.nan); r21[21:] = P[21:] / P[:-21] - 1
for j in range(len(syms)):
    r21[:first[j] + 21, j] = np.nan
fw = [np.vstack([R[k:], np.full((k, R.shape[1]), np.nan)]) for k in (1, 2, 3)]
# check: our vs_nifty_1m at the event cutoffs equals the feature
chk = df
v = r21[chk.i_cut.values, chk.symbol.map(col).values] - n21[chk.i_cut.values]
print('vs_nifty_1m recomputed vs feature, max abs diff:', np.nanmax(np.abs(v - chk.vs_nifty_1m.values)))
ev = E_.sort_values(['symbol', 'qn'])
t_lo = int(ev.loc[ev.qn == 0, 'i_cut'].min()) - 63
pl = []
for s, g in ev.groupby('symbol'):
    if s not in col:
        continue
    j = col[s]
    res = np.unique(np.r_[g.i_rd.values, g.i_react.values].astype(int))
    ts = np.arange(max(t_lo, first[j] + 22), T - 3)
    bad = np.zeros(len(ts), bool)
    for rs in res:
        bad |= (rs >= ts - 9) & (rs <= ts + 13)
    ts = ts[~bad]
    gi = g.i_cut.values.astype(int)
    nxt = np.searchsorted(gi, ts, side='right')
    keep = nxt < len(g)
    ts, nxt = ts[keep], nxt[keep]
    d = pd.DataFrame({'symbol': s, 't': ts, 'qn': g.qn.values[nxt], 'in_fo': g.in_fo.values[nxt],
                      'vs_nifty_1m': r21[ts, j] - n21[ts], 'd1': fw[0][ts, j], 'd2': fw[1][ts, j], 'd3': fw[2][ts, j]})
    pl.append(d)
pl = pd.concat(pl, ignore_index=True)
pl = pl[pl.in_fo & pl[['d1', 'd2', 'd3', 'vs_nifty_1m']].notna().all(axis=1)].reset_index(drop=True)
y3, tl, _ = E.outcomes(pl.d1.values, pl.d2.values, pl.d3.values)
pl['three_day'] = y3; pl['tp3'] = tl
print('placebo windows (in F&O, no results within 10 sessions):', len(pl), 'stocks', pl.symbol.nunique(),
      'seasons', pl.qn.nunique())
prow = []
# (b) every eligible date
for th in THS:
    m = pl.vs_nifty_1m.values < th
    for ex, c in EXITS.items():
        p = pl[c].values[m]; q = pl.qn.values[m]
        qa = qstats(p, q)
        prow.append({'version': 'all eligible dates', 'threshold_pct': 100 * th, 'exit': ex, 'windows': len(p),
                     'avg_pct': 100 * p.mean(), 'win_rate_pct': 100 * (p > 0).mean(),
                     'quarters_with_picks': len(qa), 'quarters_pos': int((qa > 0).sum())})
# (a) one random eligible date per stock per season, 500 draws
pl['grp'] = pd.factorize(pl.symbol + '_' + pl.qn.astype(str))[0]
gsz = pl.groupby('grp').size().values
starts = np.r_[0, np.cumsum(gsz)[:-1]]
order = np.argsort(pl.grp.values, kind='stable')
pls = pl.iloc[order].reset_index(drop=True)
real_res = {(r['threshold_pct'], r['exit']): r for r in rows}
for th in THS:
    for ex, c in EXITS.items():
        qp, avg, ntr, nqp, allpos = [], [], [], [], []
        for k in range(500):
            pick = starts + (rng.random(len(gsz)) * gsz).astype(int)
            sub = pls.iloc[pick]
            m = sub.vs_nifty_1m.values < th
            p = sub[c].values[m]; q = sub.qn.values[m]
            if len(p) == 0:
                continue
            qa = qstats(p, q)
            qp.append(int((qa > 0).sum())); nqp.append(len(qa)); avg.append(p.mean()); ntr.append(len(p))
            allpos.append(int((qa > 0).sum()) == len(qa))
        qp, nqp, avg = np.array(qp), np.array(nqp), np.array(avg)
        rr = real_res[(100 * th, ex)]
        frac_real = rr['quarters_pos'] / rr['quarters_with_picks']
        prow.append({'version': 'one random date per stock-season (500 draws)', 'threshold_pct': 100 * th, 'exit': ex,
                     'windows': float(np.mean(ntr)), 'avg_pct': 100 * avg.mean(), 'avg_p95_pct': 100 * np.quantile(avg, 0.95),
                     'quarters_with_picks': float(nqp.mean()), 'quarters_pos': float(qp.mean()),
                     'frac_quarters_pos': float((qp / nqp).mean()),
                     'p_frac_quarters_pos_ge_results': float(((qp / nqp) >= frac_real - 1e-12).mean()),
                     'p_avg_ge_results': float((avg >= rr['avg_pct'] / 100).mean()),
                     'p_all_quarters_pos': float(np.mean(allpos))})
PL = pd.DataFrame(prow)
PL.to_csv(f'{OUT}/lagged_nifty_placebo.csv', index=False)
print(PL.round(3).to_string(index=False))
