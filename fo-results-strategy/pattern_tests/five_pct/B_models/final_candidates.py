"""Full metrics for the final candidates (in_fo universe, real run), incl. the nested meta-selection picks."""
import os, json, numpy as np, pandas as pd
import pipeline as P
HERE = os.path.dirname(os.path.abspath(__file__))
pd.set_option('display.width', 250)
pk = pd.read_csv(os.path.join(HERE, 'picks_real_fo.csv'))


def trades(proto, fam, rule):
    g = pk[(pk.protocol == proto) & (pk.family == fam) & (pk.rule == rule)].copy()
    g['s'] = P.DIRECTION[fam] * g.three_day
    return g[['symbol', 'qn', 's']]


def meta_trades(min_n):
    M = pd.read_csv(os.path.join(HERE, f'meta_select_real_fo_min{min_n}.csv'))
    out = []
    for r in M.itertuples():
        f, ru = r.setting.split('|')
        t = trades('WF', f, ru); out.append(t[t.qn == r.qn])
    return pd.concat(out)


cands = {
    'A_RFc+_T2_WF (chosen on q6-13)': trades('WF', 'RFc+', 'T2'),
    'A_RFc+_T2_SPLIT (fit q0-13)': trades('SPLIT', 'RFc+', 'T2'),
    'B_RFc+_top5_WF': trades('WF', 'RFc+', 'top5'),
    'B_RFc+_top5_SPLIT': trades('SPLIT', 'RFc+', 'top5'),
    'C_RFc+_top2_WF': trades('WF', 'RFc+', 'top2'),
    'C_RFc+_top2_SPLIT': trades('SPLIT', 'RFc+', 'top2'),
    'D_META_min30 (nested WF)': meta_trades(30),
    'D_META_min10 (nested WF)': meta_trades(10),
    'D_META_min20 (nested WF)': meta_trades(20),
    'E_ENS+_top5_WF (a priori)': trades('WF', 'ENS+', 'top5'),
    'E_ENS-_top5_WF (a priori short)': trades('WF', 'ENS-', 'top5'),
}
rows = []
for name, t in cands.items():
    for part, a, b in (('6-13', 6, 13), ('14-21', 14, 21), ('all', 0, 21)):
        h = t[(t.qn >= a) & (t.qn <= b)]
        if len(h) == 0: continue
        m = P.metrics(h.s.values, h.qn.values)
        m['avg_qavg_gross'] = 100 * h.groupby('qn').s.mean().mean()
        m.update(candidate=name, part=part)
        rows.append(m)
D = pd.DataFrame(rows)
cols = ['candidate', 'part', 'n', 'quarters', 'avg_gross', 'avg_net', 'avg_qavg_gross', 'avg_qavg_net', 'pct_win',
        'median', 'top5_share', 'avg_wo_top5']
print(D[cols].round(2).to_string())
D[cols].to_csv(os.path.join(HERE, 'final_candidates_fo.csv'), index=False)
for name in ('B_RFc+_top5_WF', 'D_META_min30 (nested WF)'):
    t = cands[name]
    print(name, 'per-quarter gross %:', (100 * t.groupby('qn').s.mean()).round(1).to_dict())
