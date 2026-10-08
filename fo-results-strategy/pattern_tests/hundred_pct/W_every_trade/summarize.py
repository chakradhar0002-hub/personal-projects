"""summarize.py -- collect res_*.json, top_/largest_ csv, wf_*.csv, candidates_W.csv into summary_W.json + printed tables."""
import os, json, glob
import numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__))
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40); pd.set_option('display.max_colwidth', 110)
pd.set_option('display.max_rows', 400)
OUT = {}


def g(c, kind, k, f='p_null_ge_real'):
    x = c.get(kind, {}).get(k)
    return None if x is None else x.get(f)


rows_h, rows_s = [], []
for fn in sorted(glob.glob(f'{H}/res_*.json')):
    r = json.load(open(fn))
    tag = r['tag']; R = r['real']; C = r['comparison']
    for side in ('long', 'short', 'both'):
        for m in (10, 15, 20, 30):
            k = f'{side}_m{m}'
            row = {'tag': tag, 'side': side, 'm': m, 'count100': R[f'{k}_count100'], 'largest100': R[f'{k}_largest100']}
            for kind in ('shuffle', 'signflip'):
                row[f'{kind}_count_med'] = g(C, kind, f'{k}_count100', 'null_median')
                row[f'{kind}_count_p95'] = g(C, kind, f'{k}_count100', 'null_p95')
                row[f'{kind}_count_p'] = g(C, kind, f'{k}_count100')
                row[f'{kind}_largest_med'] = g(C, kind, f'{k}_largest100', 'null_median')
                row[f'{kind}_largest_max'] = g(C, kind, f'{k}_largest100', 'null_max')
                row[f'{kind}_largest_p'] = g(C, kind, f'{k}_largest100')
            if r['mode'] == 'split' and side != 'both':
                for kk in ('oos100_pooled_wr', 'oos100_frac_allwin', 'oos100_frac_allwin_ge5', 'oos100_mean_avg',
                           'largest1_oos_wr', 'largest10_oos_wr',
                           'shrunk_top1_oos_wr', 'shrunk_top10_oos_wr', 'shrunk_top100_oos_wr',
                           'wilson_top1_oos_wr', 'wilson_top10_oos_wr', 'wilson_top100_oos_wr',
                           'shrunk_top1_oos_avg', 'wilson_top1_oos_avg', 'shrunk_top10_oos_avg', 'wilson_top10_oos_avg'):
                    row[kk] = R.get(f'{k}_{kk}')
                    for kind in ('shuffle', 'signflip'):
                        row[f'{kind}_{kk}_mean'] = g(C, kind, f'{k}_{kk}', 'null_mean')
                        row[f'{kind}_{kk}_p95'] = g(C, kind, f'{k}_{kk}', 'null_p95')
                        row[f'{kind}_{kk}_p'] = g(C, kind, f'{k}_{kk}')
            (rows_s if r['mode'] == 'split' else rows_h).append(row)
    OUT[tag] = {'counts_per_run': r['counts_per_run'], 'n_null_runs': r['n_null_runs'],
                'base_win_rates': {k: r[k] for k in r if k.startswith('base_win_rate')}}
HS = pd.DataFrame(rows_h); SP = pd.DataFrame(rows_s)
HS.to_csv(f'{H}/summary_hindsight.csv', index=False); SP.to_csv(f'{H}/summary_split.csv', index=False)
print('=== HINDSIGHT (all 22 quarters): number of 100%-winner rules and largest, real vs null')
if len(HS):
    print(HS[['tag', 'side', 'm', 'count100', 'shuffle_count_med', 'shuffle_count_p95', 'shuffle_count_p', 'signflip_count_med',
              'signflip_count_p95', 'signflip_count_p', 'largest100', 'shuffle_largest_med', 'shuffle_largest_max',
              'shuffle_largest_p', 'signflip_largest_med', 'signflip_largest_max', 'signflip_largest_p']].to_string())
print('\n=== SPLIT (choose q0-13, test q14-21): in-sample 100% rules and OOS')
if len(SP):
    print(SP[['tag', 'side', 'm', 'count100', 'shuffle_count_med', 'signflip_count_med', 'signflip_count_p', 'largest100',
              'signflip_largest_med', 'signflip_largest_p', 'oos100_pooled_wr', 'shuffle_oos100_pooled_wr_mean',
              'signflip_oos100_pooled_wr_mean', 'oos100_frac_allwin_ge5', 'signflip_oos100_frac_allwin_ge5_mean',
              'largest1_oos_wr', 'largest10_oos_wr', 'signflip_largest10_oos_wr_mean']].round(3).to_string())
    print('\n=== SPLIT: chosen by shrunk / Wilson -- OOS pooled win rate (real vs null mean, p95, p)')
    cols = ['tag', 'side', 'm']
    for crit in ('shrunk', 'wilson'):
        for kk in ('top1', 'top10', 'top100'):
            cols += [f'{crit}_{kk}_oos_wr', f'signflip_{crit}_{kk}_oos_wr_mean', f'signflip_{crit}_{kk}_oos_wr_p95',
                     f'signflip_{crit}_{kk}_oos_wr_p', f'shuffle_{crit}_{kk}_oos_wr_p']
    print(SP[cols].round(3).to_string())

# ---- top-chosen rules detail (real)
det = []
for fn in sorted(glob.glob(f'{H}/top_*split*.csv')):
    tag = os.path.basename(fn)[4:-4]
    T = pd.read_csv(fn)
    T = T[T['rank'] == 1]
    T.insert(0, 'tag', tag)
    det.append(T)
if det:
    D = pd.concat(det)
    D.to_csv(f'{H}/summary_split_top1_rules.csv', index=False)
    print('\n=== SPLIT top-1 chosen rules (real)')
    print(D[['tag', 'side', 'min_trades', 'criterion', 'rule', 'is_trades', 'is_win_rate', 'oos_trades', 'oos_wins',
             'oos_win_rate', 'oos_avg', 'oos_worst', 'oos_quarters', 'oos_quarters_pos']].round(2).to_string())

# ---- walk-forward
wf = []
for fn in sorted(glob.glob(f'{H}/wf_*.csv')):
    b = os.path.basename(fn)
    if b.startswith(('wf_trades_', 'wf_rules_', 'wf_all_runs_')):
        continue
    W = pd.read_csv(fn); W.insert(0, 'tag', b[3:-4]); wf.append(W)
if wf:
    WF = pd.concat(wf, ignore_index=True)
    WF.to_csv(f'{H}/summary_wf.csv', index=False)
    cols = [c for c in ['tag', 'criterion', 'min_trades', 'side', 'trades', 'wins', 'win_rate', 'avg', 'worst', 'quarters',
                        'quarters_pos', 'quarters_all_trades_won', 'last8_trades', 'last8_win_rate', 'last8_avg',
                        'shuffle_win_rate_mean', 'shuffle_win_rate_p95', 'shuffle_win_rate_p', 'signflip_win_rate_mean',
                        'signflip_win_rate_p95', 'signflip_win_rate_p', 'signflip_avg_mean', 'signflip_avg_p'] if c in WF]
    print('\n=== WALK-FORWARD')
    print(WF[cols].round(2).to_string())
json.dump(OUT, open(f'{H}/summary_W.json', 'w'), indent=1, default=float)
