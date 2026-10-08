import os  # LAB_ROOT: scratch folder with search22/, sector/, sector_lab/data/, five_pct/; REPO_ROOT: this repo
import pandas as pd, numpy as np
D=os.environ.get('LAB_ROOT', 'lab') + '/lag5/verify_1_B_search/'
real=pd.read_csv(D+'null_real.csv'); real_val=2.37  # 10-seed average of the candidate in my re-implementation
for m in ['shuffle','signflip']:
    N=pd.read_csv(D+f'null_{m}.csv')
    c=N[(N.lab==3.0)&(N['var']=='top10')].avg
    long_best=N[N['var']!='bot25'].groupby('run').avg.max(); all_best=N.groupby('run').avg.max()
    print(f'{m}: runs={N.run.nunique()} | same variant: mean {c.mean():.2f} p95 {c.quantile(.95):.2f} max {c.max():.2f} p(>=2.37) {(c>=real_val).mean():.3f} p(>=1.88 worst seed) {(c>=1.88).mean():.3f}')
    print(f'   best of 10 RF variants per run: mean {all_best.mean():.2f} p95 {all_best.quantile(.95):.2f} max {all_best.max():.2f} p(>=2.37) {(all_best>=real_val).mean():.3f} p(>=2.67) {(all_best>=2.67).mean():.3f}')
    print('   null last-8 of top10 up3: mean %.2f p95 %.2f'%(N[(N.lab==3.0)&(N['var']=='top10')].l8.mean(),N[(N.lab==3.0)&(N['var']=='top10')].l8.quantile(.95)))
print(real.round(2).to_string())
