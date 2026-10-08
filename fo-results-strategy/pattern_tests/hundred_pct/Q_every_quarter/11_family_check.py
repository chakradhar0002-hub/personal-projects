"""11_family_check.py -- honest check of the two hindsight 22/22 families using only first-14 information:
take every rule of the same shape with the cuts available on the first 14 quarters
(A: r1w <= c1 AND days_after_quarter_end >= c2 ;  B: sector_3m <= c1 AND pe <= c2 AND vol5_60 >= c3),
keep those positive in all 14 first quarters (gross), report their last-8 record."""
import numpy as np, pandas as pd, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qengine as E
df = E.load('fo'); qn = df.qn.values; y = df.three_day.values
S = E.Search(df, range(14), range(14, 22))
def cuts(f, op):
    return [i for i, n in enumerate(S.names) if n[0] == f and n[1] == op]
fams = {'A r1w<= & days_after_qe>=': [cuts('r1w', '<='), cuts('days_after_quarter_end', '>=')],
        'B sector_3m<= & pe<= & vol5_60>=': [cuts('sector_3m', '<='), cuts('pe', '<='), cuts('vol5_60', '>=')]}
rows = []
for fam, lists in fams.items():
    import itertools
    tot = 0
    for combo in itertools.product(*lists):
        tot += 1
        m = S.rule_mask(list(combo))
        q = qn[m]; p = y[m]
        qa = pd.Series(p).groupby(q).mean()
        tr = qa[qa.index < 14]; te = qa[qa.index >= 14]
        if len(tr) == 14 and (tr > 0).all():
            rows.append({'family': fam, 'rule': S.rule_str(combo, 'L3'), 'is_trades': int((q < 14).sum()),
                         'is_avg_pct': 100 * p[q < 14].mean(), 'oos_trades': int((q >= 14).sum()),
                         'oos_pos_of_8': int((te > 0).sum()), 'oos_avg_pct': 100 * p[q >= 14].mean() if (q >= 14).any() else np.nan})
    print(fam, 'combos tried', tot)
R = pd.DataFrame(rows)
R.to_csv(os.path.join(E.HERE, 'out', 'family_check_first14.csv'), index=False)
pd.set_option('display.width', 220); pd.set_option('display.max_colwidth', 100)
for fam, g in R.groupby('family'):
    print(fam, 'qualifying on first 14:', len(g), ' last-8 positive quarters distribution:', g.oos_pos_of_8.value_counts().sort_index().to_dict(),
          ' mean last-8 avg %.2f%%' % g.oos_avg_pct.mean())
    print(g.sort_values('is_trades', ascending=False).head(8).round(2).to_string(index=False))
