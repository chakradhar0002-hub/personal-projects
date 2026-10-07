"""
04_candidates.py -- full trade statistics for the rules each search picked as its #1
(per run, per minimum trade count, per list: any size / up to 2 conditions / 1 condition).
For every rule: all 22 quarters (pooled and average of quarter averages), first 14 quarters (where it was
chosen), last 8 quarters (hold-out), gross and net of 0.17% cost, % winners, median trade, share of the
total from the 5 best trades, result without the 5 best trades, and the same rule on ALL stocks
(including results from before a stock joined F&O) with the pre-F&O share.
Output: candidates.csv
"""
import sys, os, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rulelib as R

RUNS = [('fo_n00_beam1000', 'fo', False), ('fo_n020_beam1000', 'fo', False),
        ('all_n00_beam1000', 'all', False), ('fo_n00_beam1000_full22', 'fo', True)]
ALL = R.load('all')
FO = R.load('fo')


def mask_of(df, conds):
    m = np.ones(len(df), bool)
    for f, op, v in conds:
        x = df[f].values if op != '==' else df[f].astype(str).values
        with np.errstate(invalid='ignore'):
            m &= (x >= v) if op == '>=' else (x <= v) if op == '<=' else (x == v)
    return m


def stats_block(df, m, sign, prefix):
    out = {}
    y = sign * df.three_day.values
    q = df.qn.values
    st = R.trade_stats(y[m], q[m])
    for k, v in st.items():
        out[f'{prefix}{k}'] = v
    for lab, sel in (('is14', q <= 13), ('oos8', q >= 14)):
        mm = m & sel
        out[f'{prefix}{lab}_trades'] = int(mm.sum())
        out[f'{prefix}{lab}_avg'] = 100 * y[mm].mean() if mm.any() else np.nan
        out[f'{prefix}{lab}_quarters'] = int(len(np.unique(q[mm])))
    return out


rows = []
for tag, uni, full in RUNS:
    fn = f'{R.HERE}/fixed_{tag}_top.csv'
    if not os.path.exists(fn):
        print('missing', fn); continue
    df = R.load(uni)
    tr = np.ones(len(df), bool) if full else (df.qn.values <= 13)
    M, names, compat = R.build_conditions(df, tr)
    T = pd.read_csv(fn)
    for (m, lst), g in T[T['rank'] == 1].groupby(['min_trades', 'list']):
        r = g.iloc[0]
        conds = [names[c] for c in json.loads(r.conds)]
        sign = int(r.sign)
        d = {'run': tag, 'min_trades': m, 'list': lst, 'rule': r.rule, 'sign': sign, 'conds': json.dumps(conds),
             'chosen_before_holdout': not full, 'sel_is_avg': r.is_avg_pct, 'sel_is_trades': r.is_trades}
        d.update(stats_block(FO, mask_of(FO, conds), sign, 'fo_'))
        ma = mask_of(ALL, conds)
        d.update(stats_block(ALL, ma, sign, 'all_'))
        pre = ma & ~ALL.in_fo.values
        d['all_pre_fo_trades'] = int(pre.sum())
        d['all_pre_fo_avg'] = 100 * sign * ALL.three_day.values[pre].mean() if pre.any() else np.nan
        rows.append(d)
C = pd.DataFrame(rows)
C.to_csv(f'{R.HERE}/candidates.csv', index=False)
pd.set_option('display.width', 250)
cols = ['run', 'min_trades', 'list', 'rule', 'fo_trades', 'fo_quarters_with_picks', 'fo_avg_gross', 'fo_avg_net',
        'fo_avg_of_quarter_avgs', 'fo_is14_avg', 'fo_is14_trades', 'fo_oos8_avg', 'fo_oos8_trades', 'fo_pct_win',
        'fo_median', 'fo_top5_share_of_total', 'fo_avg_without_top5', 'all_trades', 'all_avg_gross', 'all_pre_fo_trades',
        'all_pre_fo_avg']
print(C[cols].round(2).to_string())
