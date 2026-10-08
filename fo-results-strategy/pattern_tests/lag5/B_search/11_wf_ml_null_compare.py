"""
11_wf_ml_null_compare.py -- real walk-forward (rule search and ML) vs the identical pipelines on fake outcomes.
Outputs: wf_null_comparison.csv, ml_null_comparison.csv
"""
import os, glob
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))


def summarize(a, keys):
    g = a.groupby(keys + ['run'])
    out = g.apply(lambda d: pd.Series({
        'trades': d.n.sum(), 'avg_pct': 100 * d['sum'].sum() / d.n.sum() if d.n.sum() else np.nan,
        'q_with': int((d.n > 0).sum()), 'q_pos': int(((d['sum'] > 0) & (d.n > 0)).sum()),
        'trades14': d[d.qn >= 14].n.sum(),
        'avg14_pct': 100 * d[d.qn >= 14]['sum'].sum() / d[d.qn >= 14].n.sum() if d[d.qn >= 14].n.sum() else np.nan}),
        include_groups=False).reset_index()
    return out


def compare(real, nulls, keys):
    rows = []
    for k, r in real.groupby(keys):
        r = r.iloc[0]
        row = dict(zip(keys, k if isinstance(k, tuple) else (k,)))
        row.update({c: r[c] for c in ('trades', 'avg_pct', 'q_with', 'q_pos', 'trades14', 'avg14_pct')})
        for mode, N in nulls.items():
            n = N
            for kk, vv in zip(keys, k if isinstance(k, tuple) else (k,)):
                n = n[n[kk] == vv]
            v = n.avg_pct.values
            row[f'{mode}_runs'] = len(v)
            row[f'{mode}_mean'] = np.nanmean(v); row[f'{mode}_p95'] = np.nanpercentile(v, 95)
            row[f'{mode}_p'] = float(np.nanmean(v >= r.avg_pct))
            v14 = n.avg14_pct.values
            row[f'{mode}_p_q14'] = float(np.nanmean(v14 >= r.avg14_pct))
        rows.append(row)
    return pd.DataFrame(rows)


pd.set_option('display.width', 250)
# rule-search walk-forward
keys = ['objective', 'min_trades', 'variant']
real = summarize(pd.read_csv(f'{HERE}/wf_fo_real_beam150_agg.csv'), keys)
nulls = {}
for mode in ('shuffle', 'signflip'):
    f = f'{HERE}/wf_fo_{mode}_beam150_agg.csv'
    if os.path.exists(f):
        a = pd.read_csv(f)
        full = a.groupby('run').qn.max()
        a = a[a.run.isin(full[full == 21].index)]
        nulls[mode] = summarize(a, keys)
C = compare(real, nulls, keys)
C.to_csv(f'{HERE}/wf_null_comparison.csv', index=False)
print(C.round(2).to_string())
for mode in nulls:
    print(mode, 'mean over 36 variants: real %.2f%% vs null %.2f%%; variants with p<=0.05: %d; p<=0.10: %d' % (
        C.avg_pct.mean(), C[f'{mode}_mean'].mean(), (C[f'{mode}_p'] <= 0.05).sum(), (C[f'{mode}_p'] <= 0.10).sum()))
    for v in ('best_long', 'best_short', 'best_either', 'top5_either'):
        c = C[C.variant == v]
        print('  ', mode, v, 'real mean %.2f vs null %.2f' % (c.avg_pct.mean(), c[f'{mode}_mean'].mean()))

# ML
keys = ['model', 'target', 'variant']
real = summarize(pd.read_csv(f'{HERE}/ml_fo_real_11_agg.csv'), keys)
files = glob.glob(f'{HERE}/ml_fo_shuffle_*_agg.csv')
if files:
    a = pd.concat([pd.read_csv(f).assign(run=lambda d, i=i: d.run + 1000 * i) for i, f in enumerate(files)])
    full = a.groupby('run').qn.max(); a = a[a.run.isin(full[full == 21].index)]
    C2 = compare(real, {'shuffle': summarize(a, keys)}, keys)
    C2.to_csv(f'{HERE}/ml_null_comparison.csv', index=False)
    print(C2.round(2).to_string())


# ---- family-wise check: the best variant of the real run vs the best variant of each null run
def familywise(real_s, null_s, keys, label, only_long=None):
    r = real_s.copy(); n = null_s.copy()
    if only_long is not None:
        r = r[only_long(r)]; n = n[only_long(n)]
    rb = r.avg_pct.max()
    nb = n.groupby('run').avg_pct.max()
    print(f'{label}: best real variant {rb:.2f}% ({len(r)} variants) vs null best-variant mean {nb.mean():.2f}%, '
          f'p95 {nb.quantile(.95):.2f}%, family-wise p = {(nb >= rb).mean():.3f} ({len(nb)} null runs)')


keys = ['objective', 'min_trades', 'variant']
real = summarize(pd.read_csv(f'{HERE}/wf_fo_real_beam150_agg.csv'), keys)
for mode in ('shuffle', 'signflip'):
    f = f'{HERE}/wf_fo_{mode}_beam150_agg.csv'
    if os.path.exists(f):
        a = pd.read_csv(f); full = a.groupby('run').qn.max(); a = a[a.run.isin(full[full == 21].index)]
        if len(a):
            ns = summarize(a, keys)
            familywise(real, ns, keys, f'WF rule search, all 36 variants, {mode}')
            familywise(real, ns, keys, f'WF rule search, 9 best_long variants, {mode}', lambda d: d.variant == 'best_long')
keys = ['model', 'target', 'variant']
real = summarize(pd.read_csv(f'{HERE}/ml_fo_real_11_agg.csv'), keys)
if files:
    a = pd.concat([pd.read_csv(f).assign(run=lambda d, i=i: d.run + 1000 * i) for i, f in enumerate(files)])
    full = a.groupby('run').qn.max(); a = a[a.run.isin(full[full == 21].index)]
    ns = summarize(a, keys)
    familywise(real, ns, keys, 'ML, all 12 variants, shuffle')
    familywise(real, ns, keys, 'ML, 8 long variants, shuffle', lambda d: d.variant != 'bot25')
