"""09_allstocks_survivors.py -- how much of the all-stocks 'every quarter positive' comes from results reported
before the stock joined F&O (survivors).  For the real hindsight (all-stocks) qualifying rules (top 300 per setting):
share of their trades that are pre-F&O, and their record when only the F&O-at-the-time trades are kept."""
import json, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qengine as E
df = E.load('all'); S = E.Search(df, range(22), ())
R = pd.read_csv(os.path.join(E.HERE, 'out', 'full_all_real_rules.csv'))
qn = df.qn.values; fo = df.in_fo.values
Y = {'L3': df.three_day.values, 'S3': -df.three_day.values, 'LT': df.tp3.values, 'ST': df.tp3s.values}
print('pre-F&O share of all 4,460 results: %.1f%%; by quarter first 14: %.1f%%, last 8: %.1f%%' % (
    100 * (~fo).mean(), 100 * (~fo[qn < 14]).mean(), 100 * (~fo[qn >= 14]).mean()))
print('buy-all average: F&O %.2f%%, pre-F&O %.2f%%' % (100 * df.three_day[fo].mean(), 100 * df.three_day[~fo].mean()))
out = []
for (fam, cov, net), g in R.groupby(['fam', 'cov', 'net'], sort=False):
    sh, fq, fpos, favg = [], [], [], []
    for _, r in g.iterrows():
        m = S.rule_mask(json.loads(r.conds))
        sh.append((~fo[m]).mean())
        mf = m & fo
        p = Y[r.u][mf]; qa = pd.Series(p).groupby(qn[mf]).mean()
        fq.append(len(qa)); fpos.append(int((qa > (E.COST if net else 0)).sum())); favg.append(p.mean() if len(p) else np.nan)
    fq, fpos = np.array(fq), np.array(fpos)
    out.append({'fam': fam, 'cov': cov, 'net': net, 'rules': len(g), 'mean_share_trades_pre_FO_pct': 100 * np.mean(sh),
                'FO_only_share_rules_still_all_pos': float(np.mean(fpos == fq)), 'FO_only_mean_frac_quarters_pos': float(np.mean(fpos / np.maximum(fq, 1))),
                'FO_only_mean_avg_pct': 100 * np.nanmean(favg)})
O = pd.DataFrame(out)
O.to_csv(os.path.join(E.HERE, 'out', 'allstocks_survivor_share.csv'), index=False)
pd.set_option('display.width', 200)
print(O.round(3).to_string(index=False))
