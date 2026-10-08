"""
07_candidates.py -- detail for the few rules worth showing (no new search):
  A  hindsight 2-condition rule positive in all 22 quarters: LONG r1w <= -1.642% AND days_after_quarter_end >= 26
     (+ neighbouring thresholds grid)
  B  hindsight rule positive in all 22 quarters after costs: LONG sector_3m <= 17.16% AND pe <= 89.59 AND vol5_60 >= 1.196
  C  rule chosen on the first 14 quarters (pre-registered top 1, 3-day): SHORT r3d <= -2.782% AND intra0 <= -0.8914%
     AND sec_3d >= -1.338%
  D  lagged Nifty (vs_nifty_1m < -15%), TP exit  (full detail in 04_lagged_nifty.py)
For each: trades, win rate, average, quarters with picks / positive (all, first 14, last 8), after costs, TP version,
worst trade, without best 5 trades, random-pick and own-sign-flip baselines (3,000 draws).
Output: out/candidates.csv, out/candidate_A_grid.csv
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qengine as E

df = E.load('fo')
qn = df.qn.values
rng = np.random.default_rng(7)
COLS = {('long', '3day'): ('three_day', 1), ('long', 'tp'): ('tp3', 1), ('short', '3day'): ('three_day', -1),
        ('short', 'tp'): ('tp3s', 1)}


def f(c):
    return df[c].values.astype(float)


with np.errstate(invalid='ignore'):
    CANDS = {
        'A hindsight: r1w <= -1.642% AND days_after_quarter_end >= 26': ('long', (f('r1w') <= -0.01642) & (f('days_after_quarter_end') >= 26)),
        'B hindsight after costs: sector_3m <= 17.16% AND pe <= 89.59 AND vol5_60 >= 1.196': ('long', (f('sector_3m') <= 0.1716) & (f('pe') <= 89.59) & (f('vol5_60') >= 1.196)),
        'C chosen on first 14: r3d <= -2.782% AND intra0 <= -0.8914% AND sec_3d >= -1.338%': ('short', (f('r3d') <= -0.02782) & (f('intra0') <= -0.008914) & (f('sec_3d') >= -0.01338)),
        'D lagged Nifty: vs_nifty_1m < -15%': ('long', f('vs_nifty_1m') < -0.15),
    }


def detail(name, side, m, ex, draws=3000):
    col, sg = COLS[(side, ex)]
    p = sg * df[col].values[m]; q = qn[m]
    qa = pd.Series(p).groupby(q).mean()
    d = {'candidate': name, 'side': side, 'exit': ex, 'trades': len(p), 'win_rate_pct': 100 * (p > 0).mean(),
         'win_rate_net_pct': 100 * (p > E.COST).mean(), 'avg_pct': 100 * p.mean(), 'worst_trade_pct': 100 * p.min(),
         'quarters_with_picks': len(qa), 'quarters_pos': int((qa > 0).sum()), 'quarters_pos_net': int((qa > E.COST).sum()),
         'first14': f"{int((qa[qa.index < 14] > 0).sum())}/{int((qa.index < 14).sum())}",
         'last8': f"{int((qa[qa.index >= 14] > 0).sum())}/{int((qa.index >= 14).sum())}",
         'first14_avg_pct': 100 * p[q < 14].mean(), 'last8_avg_pct': 100 * p[q >= 14].mean() if (q >= 14).any() else np.nan,
         'worst_quarter_pct': 100 * qa.min(), 'trades_per_quarter_median': float(pd.Series(q).value_counts().median())}
    o = np.argsort(-p)[5:]
    qa5 = pd.Series(p[o]).groupby(q[o]).mean()
    d.update(avg_wo_best5_pct=100 * p[o].mean(), quarters_pos_wo_best5=f"{int((qa5 > 0).sum())}/{len(qa5)}")
    cnt = pd.Series(q).value_counts()
    allp = {qq: sg * df[col].values[qn == qq] for qq in cnt.index}
    qm = pd.Series(sg * df[col].values).groupby(qn).mean()
    dev = p - qm.loc[q].values
    codes = pd.factorize(q, sort=True)[0]; ns = np.bincount(codes)
    rp, sf = np.zeros(draws, int), np.zeros(draws, int)
    for k in range(draws):
        rp[k] = sum(rng.choice(allp[qq], c, replace=False).mean() > 0 for qq, c in cnt.items())
        pf = qm.loc[q].values + rng.choice([-1.0, 1.0], len(p)) * dev
        sf[k] = int(((np.bincount(codes, weights=pf) / ns) > 0).sum())
    d.update(randompick_mean_quarters_pos=rp.mean(), randompick_p_ge=float((rp >= d['quarters_pos']).mean()),
             signflip_mean_quarters_pos=sf.mean(), signflip_p_ge=float((sf >= d['quarters_pos']).mean()))
    return d


rows = []
for name, (side, m) in CANDS.items():
    for ex in ('3day', 'tp'):
        rows.append(detail(name, side, m, ex))
Cd = pd.DataFrame(rows)
Cd.to_csv(os.path.join(E.HERE, 'out', 'candidates.csv'), index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 60)
print(Cd.round(3).to_string(index=False))

# neighbourhood of candidate A
g = []
for th in (-0.005, -0.01, -0.01642, -0.02, -0.03, -0.05):
    for dq in (0, 15, 20, 23, 26, 30, 35, 40):
        with np.errstate(invalid='ignore'):
            m = (f('r1w') <= th) & (f('days_after_quarter_end') >= dq)
        for ex in ('3day', 'tp'):
            col, sg = COLS[('long', ex)]
            p = df[col].values[m]; q = qn[m]
            qa = pd.Series(p).groupby(q).mean()
            g.append({'r1w_le_pct': 100 * th, 'days_after_qe_ge': dq, 'exit': ex, 'trades': len(p), 'avg_pct': 100 * p.mean(),
                      'win_rate_pct': 100 * (p > 0).mean(), 'quarters_with_picks': len(qa), 'quarters_pos': int((qa > 0).sum()),
                      'quarters_pos_net': int((qa > E.COST).sum()),
                      'first14': f"{int((qa[qa.index < 14] > 0).sum())}/{int((qa.index < 14).sum())}",
                      'last8': f"{int((qa[qa.index >= 14] > 0).sum())}/{int((qa.index >= 14).sum())}"})
G = pd.DataFrame(g)
G.to_csv(os.path.join(E.HERE, 'out', 'candidate_A_grid.csv'), index=False)
print(G[G.exit == '3day'].pivot(index='r1w_le_pct', columns='days_after_qe_ge', values='quarters_pos').to_string())
print(G[G.exit == '3day'].pivot(index='r1w_le_pct', columns='days_after_qe_ge', values='avg_pct').round(2).to_string())
print(G[G.exit == '3day'].pivot(index='r1w_le_pct', columns='days_after_qe_ge', values='trades').to_string())
# the same rule with each of its two conditions alone
for nm, m in (('r1w <= -1.642% alone', f('r1w') <= -0.01642), ('days_after_quarter_end >= 26 alone', f('days_after_quarter_end') >= 26),
              ('days_after_quarter_end < 26 AND r1w <= -1.642%', (f('r1w') <= -0.01642) & (f('days_after_quarter_end') < 26))):
    p = df.three_day.values[m]; q = qn[m]; qa = pd.Series(p).groupby(q).mean()
    print(f"{nm:50s} trades {len(p):4d} avg {100 * p.mean():5.2f}% quarters pos {int((qa > 0).sum())}/{len(qa)}")
