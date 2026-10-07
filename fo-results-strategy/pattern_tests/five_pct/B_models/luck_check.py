"""Compare the real run with the shuffled-outcome runs (three_day shuffled within quarter, identical pipeline)."""
import os, sys, glob, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
pd.set_option('display.width', 250)
tag = sys.argv[1] if len(sys.argv) > 1 else 'fo'
K = pd.concat([pd.read_csv(f) for f in glob.glob(os.path.join(HERE, f'keystats_shuffled_{tag}_*.csv'))])
S = pd.concat([pd.read_csv(f) for f in glob.glob(os.path.join(HERE, f'settings_shuffled_{tag}_*.csv'))])
real = json.load(open(os.path.join(HERE, f'keystats_real_{tag}.json')))
R = pd.read_csv(os.path.join(HERE, f'settings_real_{tag}.csv'))
nrun = K.seed.nunique()
print(f'shuffled runs: {nrun}')
out = {'n_shuffled_runs': int(nrun)}
for k in ['best_is_avg_net', 'best_is_oos_wf', 'best_is_oos_split', 'max_all_wf', 'max_all_wf_n20', 'max_all_wf_n30',
          'max_oos_wf', 'max_oos_split', 'ENS+_top5_all_wf', 'ENS+_top5_oos_split', 'ENS-_top5_all_wf',
          'ENS-_top5_oos_split', 'meta_avg_net_8_21_min10', 'meta_avg_net_14_21_min10', 'meta_avg_net_8_21_min20',
          'meta_avg_net_14_21_min20', 'meta_avg_net_8_21_min30', 'meta_avg_net_14_21_min30']:
    v = K[k].astype(float)
    row = dict(real=real[k], shuf_mean=v.mean(), shuf_median=v.median(), shuf_p90=v.quantile(.9), shuf_max=v.max(),
               frac_shuf_ge_real=(v >= real[k]).mean())
    out[k] = row
    print(f'{k:28s} real {real[k]:6.2f} | shuffled mean {v.mean():6.2f} median {v.median():6.2f} '
          f'90th {v.quantile(.9):6.2f} max {v.max():6.2f} | share of shuffles >= real {(v >= real[k]).mean():.2f}')

# per-setting comparison: real walk-forward 6..21 vs the same setting in shuffled runs, and vs max over settings
W = S[(S.protocol == 'WF') & (S.part == 'all')]
Wr = R[(R.protocol == 'WF') & (R.part == 'all')].set_index(['family', 'rule'])
rows = []
for (f, r), g in W.groupby(['family', 'rule']):
    rv = Wr.loc[(f, r)]
    if rv.n < 10: continue
    # max over settings with at least as many trades, in each shuffled run
    mx = W[W.n >= rv.n].groupby('seed').avg_net.max()
    rows.append(dict(family=f, rule=r, n=rv.n, real_avg_net=rv.avg_net, shuf_same_mean=g.avg_net.mean(),
                     shuf_same_sd=g.avg_net.std(), frac_same_ge=(g.avg_net >= rv.avg_net).mean(),
                     frac_maxany_ge=(mx >= rv.avg_net).mean()))
P = pd.DataFrame(rows).sort_values('real_avg_net', ascending=False)
P.to_csv(os.path.join(HERE, f'luck_per_setting_{tag}.csv'), index=False)
print('\nper-setting (walk-forward quarters 6..21, net %): real vs same setting in shuffles; '
      'frac_maxany_ge = share of shuffles where ANY setting with >= as many trades did as well')
print(P.head(20).round(3).to_string())
# how many settings exceed thresholds, real vs shuffled
for thr in (2, 3, 5):
    rc = int(((Wr.n >= 10) & (Wr.avg_net > thr)).sum())
    sc = W[(W.n >= 10) & (W.avg_net > thr)].groupby('seed').size().reindex(K.seed.unique(), fill_value=0)
    print(f'settings (>=10 trades) with 6..21 net avg > {thr}%: real {rc}, shuffled mean {sc.mean():.1f}, '
          f'share of shuffles >= real {(sc >= rc).mean():.2f}')
    out[f'n_settings_gt{thr}'] = dict(real=rc, shuf_mean=float(sc.mean()), frac_ge=float((sc >= rc).mean()))
json.dump(out, open(os.path.join(HERE, f'luck_summary_{tag}.json'), 'w'), indent=1, default=float)
