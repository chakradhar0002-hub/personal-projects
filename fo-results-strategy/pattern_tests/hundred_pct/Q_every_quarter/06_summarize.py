"""
06_summarize.py -- real vs null comparison tables from out/*.json (02_search.py and 05_walkforward.py).
Writes out/summary_hindsight.csv, out/summary_split.csv, out/summary_wf.csv, out/summary.json
"""
import os, sys, json, glob
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 60); pd.set_option('display.max_rows', 500)


def flat(r):
    d = {k: v for k, v in r.items() if not isinstance(v, dict)}
    for k in ('top1', 'top10', 'top1_is', 'n_by_level'):
        if isinstance(r.get(k), dict):
            for kk, vv in r[k].items():
                if not isinstance(vv, dict):
                    d[f'{k}_{kk}'] = vv
    return d


def load(mode, uni='fo'):
    rows = []
    for f in sorted(glob.glob(f'{OUT}/{mode}_{uni}_*.json')):
        for r in json.load(open(f)):
            rows.append(flat(r))
    D = pd.DataFrame(rows)
    if len(D) == 0:
        return D
    D = D.drop_duplicates(subset=['run', 'fam', 'cov', 'net'])
    D['kind'] = D.run.str.split('_').str[0]
    return D


def compare(D, metrics, higher_is_luckier=True):
    out = []
    for (fam, cov, net), g in D.groupby(['fam', 'cov', 'net'], sort=False):
        real = g[g.kind == 'real']
        for kind in ('shuffle', 'signflip', 'weekflip'):
            n = g[g.kind == kind]
            if len(n) == 0:
                continue
            d = {'fam': fam, 'cov': cov, 'net': net, 'null': kind, 'null_runs': len(n)}
            for m in metrics:
                if m not in g:
                    continue
                rv = real[m].iloc[0] if len(real) else np.nan
                x = n[m].astype(float)
                d[f'{m}__real'] = rv
                d[f'{m}__null_median'] = x.median()
                d[f'{m}__null_p95'] = x.quantile(0.95)
                d[f'{m}__null_mean'] = x.mean()
                if pd.notna(rv):
                    d[f'{m}__share_null_ge_real'] = float((x.fillna(-np.inf) >= rv - 1e-12).mean())
            if 'n_rules' in n:
                d['share_null_runs_with_any_rule'] = float((n.n_rules.fillna(0) > 0).mean())
            out.append(d)
    return pd.DataFrame(out)


res = {}
H = load('full')
if len(H):
    H = H.fillna({'n_rules': 0})
    met = ['n_rules', 'n_distinct_picksets', 'n_K_ge100', 'n_K_ge200', 'n_K_ge400', 'is_trades_max', 'top1_is_trades',
           'top1_is_avg_pct']
    CH = compare(H, met)
    CH.to_csv(f'{OUT}/summary_hindsight.csv', index=False)
    show = ['fam', 'cov', 'net', 'null', 'null_runs', 'n_rules__real', 'n_rules__null_median', 'n_rules__null_p95',
            'n_rules__share_null_ge_real', 'n_distinct_picksets__real', 'n_distinct_picksets__null_median',
            'n_K_ge200__real', 'n_K_ge200__null_median', 'n_K_ge200__share_null_ge_real', 'share_null_runs_with_any_rule']
    print('==== HINDSIGHT (all 22 quarters searched)')
    print(CH[[c for c in show if c in CH]].round(3).to_string(index=False))
    res['hindsight'] = CH.to_dict('records')

Sp = load('split')
if len(Sp):
    Sp = Sp.fillna({'n_rules': 0})
    met = ['n_rules', 'n_distinct_picksets', 'oos_mean_frac_quarters_pos', 'oos_mean_pos_of_all', 'oos_frac_rules_all_pos',
           'oos_frac_rules_all8_pos', 'oos_pooled_avg_pct', 'top1_oos_mean_frac_quarters_pos', 'top1_oos_mean_pos_of_all',
           'top1_oos_pooled_avg_pct', 'top10_oos_mean_frac_quarters_pos', 'top10_oos_mean_pos_of_all',
           'top10_oos_pooled_avg_pct']
    CS = compare(Sp, met)
    CS.to_csv(f'{OUT}/summary_split.csv', index=False)
    print('==== FIXED SPLIT (chosen on qn 0..13, tested on qn 14..21)')
    for blk in (['n_rules', 'n_distinct_picksets'], ['oos_mean_frac_quarters_pos', 'oos_mean_pos_of_all', 'oos_pooled_avg_pct'],
                ['top1_oos_mean_pos_of_all', 'top1_oos_pooled_avg_pct', 'top10_oos_mean_frac_quarters_pos', 'top10_oos_pooled_avg_pct']):
        cols = ['fam', 'cov', 'net', 'null', 'null_runs']
        for m in blk:
            cols += [f'{m}__real', f'{m}__null_median', f'{m}__share_null_ge_real']
        print(CS[[c for c in cols if c in CS]].round(3).to_string(index=False))
    res['split'] = CS.to_dict('records')

W = []
for f in sorted(glob.glob(f'{OUT}/wf_fo_*.json')):
    W += json.load(open(f))
W = pd.DataFrame(W)
if len(W):
    W = W.drop_duplicates(subset=['run', 'q', 'fam', 'cov', 'net'])
    W['kind'] = W.run.str.split('_').str[0]
    agg = []
    for (run, fam, cov, net), g in W.groupby(['run', 'fam', 'cov', 'net'], sort=False):
        thr = 0.0017 if net else 0.0
        d = {'run': run, 'kind': g.kind.iloc[0], 'fam': fam, 'cov': cov, 'net': net,
             'wf_quarters': len(g), 'quarters_with_qualifying_rule': int((g.n_qual > 0).sum())}
        if 'top1_te_avg' in g:
            t = g[g.top1_te_avg.notna()]
            d['top1_quarters_traded'] = len(t)
            d['top1_quarters_pos'] = int((t.top1_te_avg > thr).sum())
            d['top1_frac_pos'] = d['top1_quarters_pos'] / len(t) if len(t) else np.nan
            d['top1_trades'] = int(t.top1_te_trades.sum())
            d['top1_pooled_avg_pct'] = 100 * (t.top1_te_avg * t.top1_te_trades).sum() / t.top1_te_trades.sum() if len(t) else np.nan
            d['top1_q14plus_pos'] = f"{int((t[t.q >= 14].top1_te_avg > thr).sum())}/{int((t.q >= 14).sum())}"
        if 'top10_te_avg' in g:
            t = g[g.top10_te_avg.notna()]
            d['top10_quarters_traded'] = len(t)
            d['top10_quarters_pos'] = int((t.top10_te_avg > thr).sum())
            d['top10_frac_pos'] = d['top10_quarters_pos'] / len(t) if len(t) else np.nan
            d['top10_pooled_avg_pct'] = 100 * (t.top10_te_avg * t.top10_te_trades).sum() / t.top10_te_trades.sum() if len(t) else np.nan
        if 'all_frac_pos' in g:
            t = g[g.all_frac_pos.notna()]
            d['all_mean_frac_rules_pos'] = t.all_frac_pos.mean()
            d['all_quarters_majority_pos'] = int((t.all_frac_pos > 0.5).sum())
            d['all_mean_pooled_avg_pct'] = 100 * t.all_pooled_avg.mean()
        agg.append(d)
    WA = pd.DataFrame(agg)
    WA.to_csv(f'{OUT}/summary_wf_runs.csv', index=False)
    out = []
    for (fam, cov, net), g in WA.groupby(['fam', 'cov', 'net'], sort=False):
        real = g[g.kind == 'real']
        for kind in ('shuffle', 'signflip', 'weekflip'):
            n = g[g.kind == kind]
            d = {'fam': fam, 'cov': cov, 'net': net, 'null': kind, 'null_runs': len(n)}
            for m in ('top1_quarters_traded', 'top1_quarters_pos', 'top1_frac_pos', 'top1_pooled_avg_pct', 'top10_frac_pos',
                      'top10_pooled_avg_pct', 'all_mean_frac_rules_pos', 'all_mean_pooled_avg_pct'):
                if m in g:
                    rv = real[m].iloc[0] if len(real) else np.nan
                    d[f'{m}__real'] = rv
                    if len(n):
                        d[f'{m}__null_mean'] = n[m].mean()
                        d[f'{m}__share_null_ge_real'] = float((n[m].fillna(-np.inf) >= rv - 1e-12).mean()) if pd.notna(rv) else np.nan
            if len(real):
                d['top1_q14plus_pos__real'] = real.top1_q14plus_pos.iloc[0] if 'top1_q14plus_pos' in real else None
            out.append(d)
            if len(n) == 0:
                break
    CW = pd.DataFrame(out)
    CW.to_csv(f'{OUT}/summary_wf.csv', index=False)
    print('==== WALK-FORWARD (q = 8..21)')
    print(CW.round(3).to_string(index=False))
    res['wf'] = CW.to_dict('records')
json.dump(res, open(f'{OUT}/summary.json', 'w'), indent=1, default=lambda x: None if x is None else (float(x) if np.isscalar(x) else str(x)))

# ---------------- secondary universe: all 4,460 results (includes results from before a stock joined F&O)
for mode, mets in (('full', ['n_rules', 'n_distinct_picksets', 'n_K_ge200', 'is_trades_max']),
                   ('split', ['n_rules', 'oos_mean_frac_quarters_pos', 'oos_mean_pos_of_all', 'oos_pooled_avg_pct',
                              'top1_oos_mean_pos_of_all', 'top1_oos_pooled_avg_pct', 'top10_oos_pooled_avg_pct'])):
    D = load(mode, 'all')
    if len(D):
        D = D.fillna({'n_rules': 0})
        CA = compare(D, mets)
        CA.to_csv(f'{OUT}/summary_{"hindsight" if mode == "full" else "split"}_allstocks.csv', index=False)
        print(f'==== ALL STOCKS {mode}')
        cols = ['fam', 'cov', 'net', 'null', 'null_runs'] + [f'{m}__{s}' for m in mets for s in ('real', 'null_median', 'share_null_ge_real')]
        print(CA[[c for c in cols if c in CA]].round(3).to_string(index=False))
