"""Detailed metrics for candidate settings of the real in_fo run + simple volatility baselines."""
import os, numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
import pipeline as P
HERE = os.path.dirname(os.path.abspath(__file__))
pd.set_option('display.width', 250)

T, feats, X = P.load('fo')
y = T.three_day.values
pk = pd.read_csv(os.path.join(HERE, 'picks_real_fo.csv'))
pk = pk.merge(T[['symbol', 'qn', 'excess_nifty', 'vol60', 'past_abs3d', 'log_mcap', 'r1m', 'r3m']], on=['symbol', 'qn'])


def full(proto, fam, rule, parts=(('6-13', 6, 13), ('14-21', 14, 21), ('6-21', 6, 21))):
    g = pk[(pk.protocol == proto) & (pk.family == fam) & (pk.rule == rule)]
    d = P.DIRECTION[fam]
    rows = []
    for name, a, b in parts:
        h = g[(g.qn >= a) & (g.qn <= b)]
        m = P.metrics(d * h.three_day.values, h.qn.values)
        m.update(setting=f'{proto}|{fam}|{rule}', part=name, avg_excess_nifty=100 * d * h.excess_nifty.mean(),
                 pick_vol60=h.vol60.mean())
        rows.append(m)
    return rows


rows = []
for fam, rule in [('RFc+', 'top1'), ('RFc+', 'top2'), ('RFc+', 'top3'), ('RFc+', 'top5'), ('RFc+', 'top10'),
                  ('RFc+', 'T2'), ('RFc+', 'T5'), ('RIDGE', 'top1'), ('ENS+', 'top1'), ('ENS+', 'top5'),
                  ('ENS-', 'top5'), ('HGBc+', 'top2')]:
    rows += full('WF', fam, rule)
    rows += full('SPLIT', fam, rule, parts=(('14-21', 14, 21),))
D = pd.DataFrame(rows)
cols = ['setting', 'part', 'n', 'quarters', 'avg_gross', 'avg_net', 'avg_qavg_net', 'pct_win', 'median', 'top5_share',
        'avg_wo_top5', 'avg_excess_nifty', 'pick_vol60']
print(D[cols].round(2).to_string())
D[cols].to_csv(os.path.join(HERE, 'candidates_detail_fo.csv'), index=False)

# simple baselines: top-k per quarter by a single volatility-type feature, quarters 6..21
print('\nSimple one-feature baselines (top-k per quarter, long, quarters 6-21, gross %):')
qn = T.qn.values
res = []
for f in ['vol60', 'past_abs3d', 'iv_t5', 'vol20', 'beta250', 'idio60', 'past_frac_gt5', 'nbig20', 'maxr20']:
    v = T[f].values
    lab = y > .05
    m6 = qn >= 6
    ok = m6 & np.isfinite(v)
    auc_gt = roc_auc_score(lab[ok], v[ok]); auc_lt = roc_auc_score((y < -.05)[ok], v[ok])
    row = dict(feature=f, auc_gt5=auc_gt, auc_lt5=auc_lt)
    for k in (2, 5, 10):
        s = []
        for q in range(6, 22):
            mm = np.where((qn == q) & np.isfinite(v))[0]
            o = mm[np.argsort(-v[mm])[:k]]
            s.extend(y[o])
        row[f'top{k}_gross'] = 100 * np.mean(s)
        row[f'top{k}_sd'] = 100 * np.std(s)
    res.append(row)
print(pd.DataFrame(res).round(3).to_string())

# which stocks / quarters does RFc+ top5 pick?
g = pk[(pk.protocol == 'WF') & (pk.family == 'RFc+') & (pk.rule == 'top5')]
print('\nRFc+ top5 (WF) per-quarter average gross %:')
print((100 * g.groupby('qn').three_day.mean()).round(2).to_dict())
print('most frequent symbols:', g.symbol.value_counts().head(12).to_dict())
print('5 best trades:', g.nlargest(5, 'three_day')[['symbol', 'qn', 'three_day']].to_dict('records'))
