"""
02_fixed_split.py -- exhaustive 1/2/3-condition search on the first 14 quarters (qn 0..13),
honest test on the last 8 (qn 14..21), and the identical pipeline on within-quarter shuffles of three_day.

usage: python3 02_fixed_split.py UNIVERSE N_SHUFFLES [--n0 X] [--beam B] [--full]
  UNIVERSE  fo  (in F&O at the time, main)  or  all  (all 4,460 results)
  --n0      objective = sum / (n + n0)  (0 = plain pooled average, the main objective)
  --full    search all 22 quarters in sample (min picks in 5 quarters); no hold-out.  This answers the
            literal question "is there a rule averaging > 5% over all 22 quarters" -- and shows how many
            such rules pure noise produces.
Outputs (this folder): fixed_<tag>.json, fixed_<tag>_top.csv, fixed_<tag>_shuffles.csv
"""
import sys, json, time, argparse
import numpy as np, pandas as pd
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import rulelib as R

ap = argparse.ArgumentParser()
ap.add_argument('universe'); ap.add_argument('nshuf', type=int)
ap.add_argument('--n0', type=float, default=0.0); ap.add_argument('--beam', type=int, default=1000)
ap.add_argument('--full', action='store_true')
ap.add_argument('--null', default='quarter', help='quarter: shuffle three_day within each quarter (main); '
                'week: shuffle within (quarter, ISO week of results date) -- keeps same-week market moves; '
                'signflip: keep each result\'s size of move around its quarter average but flip its direction at '
                'random -- keeps "volatile stocks move a lot", removes any ability to predict direction')
A = ap.parse_args()
tag = f"{A.universe}_n0{int(A.n0)}_beam{A.beam}" + ('_full22' if A.full else '') + ('' if A.null == 'quarter' else '_null' + A.null)
MS = (10, 20, 30)
MINQ = 5 if A.full else 4

df = R.load(A.universe)
y = df.three_day.values.astype(float)
qn = df.qn.values
if A.null == 'week':
    wk = pd.to_datetime(df.results_date).dt.isocalendar()
    grp = pd.factorize(df.qn.astype(str) + '_' + wk.year.astype(str) + '_' + wk.week.astype(str))[0]
else:
    grp = qn
tr = np.ones(len(df), bool) if A.full else (qn <= 13)
te = ~tr
M, names, compat = R.build_conditions(df, tr)
S = R.Searcher(M[:, tr], qn[tr], compat, M[:, te] if te.any() else None)
print(tag, 'rows', len(df), 'train', tr.sum(), 'conditions', len(names), 'pairs', S.n_pairs, flush=True)


def oos_of(rule_list, yv):
    """per-rule out-of-sample stats on the hold-out quarters for a list of (obj, mean, n, L, conds, sign)."""
    out = []
    for c in rule_list:
        mk = R.rule_mask(M, list(c[4]))
        mt = mk & te
        pn = c[5] * yv[mt]
        out.append((pn.sum(), len(pn), len(np.unique(qn[mt]))))
    return out


def agg_top(rule_list, yv, ks=(1, 10, 100)):
    o = oos_of(rule_list, yv) if te.any() else []
    res = {}
    for k in ks:
        sub = rule_list[:k]
        d = {'n_rules': len(sub), 'is_mean_of_rule_avgs': 100 * float(np.mean([c[1] for c in sub])) if sub else None}
        if te.any() and sub:
            oo = o[:k]
            has = [x for x in oo if x[1] > 0]
            d['n_with_oos_trades'] = len(has)
            if has:
                avgs = np.array([x[0] / x[1] for x in has])
                d['oos_mean_of_rule_avgs'] = 100 * float(avgs.mean())
                d['oos_pooled'] = 100 * float(sum(x[0] for x in has) / sum(x[1] for x in has))
                d['oos_frac_rules_gt5'] = float((avgs > 0.05).mean())
                d['oos_frac_rules_gt0'] = float((avgs > 0).mean())
                d['oos_median_trades'] = float(np.median([x[1] for x in has]))
        res[k] = d
    return res, o


def summarize(res, yv, keep_rules=False):
    out = {}
    for m in MS:
        r = res[m]
        d = {'count_gt5': r['count_gt5'], 'count_gt5_long': r['count_gt5_long']}
        if 'n_eligible' in r:
            d['n_eligible'] = r['n_eligible']
        d['best_is'] = {str(L): (100 * r['best_by_level'][L][1] if r['best_by_level'][L] else None) for L in (1, 2, 3)}
        d['best_is']['all'] = 100 * r['top'][0][1]
        d['best_is_obj'] = 100 * r['top'][0][0]
        d['top_all'], o_all = agg_top(r['top'], yv)
        d['top_upto2'], o2 = agg_top(r['top_upto2'], yv)
        d['top_upto1'], o1 = agg_top(r['top_upto1'], yv)
        if 'oos_gt5' in r:
            d['oos_gt5'] = {str(L): {k: (100 * v if k in ('mean_of_rule_avgs', 'median_rule_avg', 'pooled') else v)
                                     for k, v in r['oos_gt5'][L].items()} for L in r['oos_gt5']}
        if keep_rules:
            rows = []
            for lst, oo, name in ((r['top'], o_all, 'all'), (r['top_upto2'], o2, 'upto2'), (r['top_upto1'], o1, 'upto1')):
                for rank, (c, x) in enumerate(zip(lst, oo if oo else [(np.nan, 0, 0)] * len(lst))):
                    rows.append({'min_trades': m, 'list': name, 'rank': rank + 1, 'level': c[3],
                                 'rule': R.rule_str(names, c[4], c[5]), 'conds': json.dumps(list(c[4])), 'sign': c[5],
                                 'is_avg_pct': 100 * c[1], 'is_obj_pct': 100 * c[0], 'is_trades': c[2],
                                 'oos_avg_pct': 100 * x[0] / x[1] if x[1] else np.nan, 'oos_trades': x[1],
                                 'oos_quarters': x[2]})
            d['_rows'] = rows
        out[m] = d
    return out


t0 = time.time()
res = S.run(y[tr], ms=MS, minq=MINQ, beam=A.beam, n0=A.n0, yte=y[te] if te.any() else None,
            collect_oos_gt5=te.any(), count_eligible=True)
real = summarize(res, y, keep_rules=True)
counts = {'n_conditions': res['n_conditions'], 'n_pairs': res['n_pairs'], 'n_beam_pairs': res['n_beam_pairs'],
          'n_triples_evaluated': res['n_triples_evaluated'],
          'rules_evaluated_long_and_short': 2 * (res['n_conditions'] + res['n_pairs'] + res['n_triples_evaluated'])}
print('real done', round(time.time() - t0, 1), counts, flush=True)
rows = []
for m in MS:
    rows += real[m].pop('_rows')
pd.DataFrame(rows).to_csv(f'{R.HERE}/fixed_{tag}_top.csv', index=False)
for m in MS:
    print(m, 'count>5%', real[m]['count_gt5'], 'best IS', real[m]['best_is'],
          'top1/10/100 OOS', [real[m]['top_all'][k].get('oos_mean_of_rule_avgs') for k in (1, 10, 100)], flush=True)

# ---------------- shuffles
rng = np.random.default_rng(12345)
sh_rows = []
for s in range(A.nshuf):
    if A.null == 'signflip':
        qm = pd.Series(y).groupby(qn).transform('mean').values
        ys = qm + rng.choice([-1.0, 1.0], len(y)) * (y - qm)
    else:
        ys = R.shuffle_within(y, grp, rng)
    rs = S.run(ys[tr], ms=MS, minq=MINQ, beam=A.beam, n0=A.n0, yte=ys[te] if te.any() else None,
               collect_oos_gt5=te.any())
    sm = summarize(rs, ys)
    for m in MS:
        d = sm[m]
        row = {'shuffle': s, 'min_trades': m, 'best_is_all': d['best_is']['all'], 'best_is_obj': d['best_is_obj']}
        for L in ('1', '2', '3'):
            row[f'best_is_L{L}'] = d['best_is'][L]
            row[f'count_gt5_L{L}'] = d['count_gt5'][int(L)]
        for lst in ('top_all', 'top_upto2', 'top_upto1'):
            for k in (1, 10, 100):
                row[f'{lst}_{k}_oos'] = d[lst][k].get('oos_mean_of_rule_avgs')
                row[f'{lst}_{k}_is'] = d[lst][k].get('is_mean_of_rule_avgs')
        if 'oos_gt5' in d:
            for L in ('1', '2', '3'):
                row[f'gt5_L{L}_oos_mean'] = d['oos_gt5'][L].get('mean_of_rule_avgs')
        sh_rows.append(row)
    if s % 5 == 4:
        print('shuffle', s + 1, round(time.time() - t0, 1), flush=True)
SH = pd.DataFrame(sh_rows)
SH.to_csv(f'{R.HERE}/fixed_{tag}_shuffles.csv', index=False)

# ---------------- comparison real vs shuffled
cmp = {}
if len(SH):
    for m in MS:
        sm = SH[SH.min_trades == m]
        d = {}
        d['p_best_is_all'] = float((sm.best_is_obj >= real[m]['best_is_obj'] - 1e-12).mean())
        d['shuf_best_is_all_median'] = float(sm.best_is_all.median())
        d['shuf_best_is_all_p95'] = float(sm.best_is_all.quantile(0.95))
        for L in ('1', '2', '3'):
            rv = real[m]['count_gt5'][int(L)]
            d[f'count_gt5_L{L}_real'] = rv
            d[f'count_gt5_L{L}_shuf_median'] = float(sm[f'count_gt5_L{L}'].median())
            d[f'count_gt5_L{L}_shuf_p95'] = float(sm[f'count_gt5_L{L}'].quantile(0.95))
            d[f'p_count_gt5_L{L}'] = float((sm[f'count_gt5_L{L}'] >= rv).mean())
            rb = real[m]['best_is'][L]
            if rb is not None:
                d[f'p_best_is_L{L}'] = float((sm[f'best_is_L{L}'] >= rb - 1e-12).mean())
        for lst in ('top_all', 'top_upto2', 'top_upto1'):
            for k in (1, 10, 100):
                col = f'{lst}_{k}_oos'
                if col in sm and sm[col].notna().any():
                    d[f'{col}_shuf_mean'] = float(sm[col].mean())
                    d[f'{col}_shuf_p95'] = float(sm[col].quantile(0.95))
                    rv = real[m][lst][k].get('oos_mean_of_rule_avgs')
                    if rv is not None:
                        d[f'{col}_real'] = rv
                        d[f'{col}_p'] = float((sm[col] >= rv).mean())
        cmp[m] = d
json.dump({'tag': tag, 'null': A.null, 'counts': counts, 'real': real, 'shuffle_comparison': cmp, 'n_shuffles': A.nshuf,
           'seconds': time.time() - t0}, open(f'{R.HERE}/fixed_{tag}.json', 'w'), indent=1, default=float)
print(json.dumps(cmp, indent=1, default=float))
print('done', round(time.time() - t0, 1))
