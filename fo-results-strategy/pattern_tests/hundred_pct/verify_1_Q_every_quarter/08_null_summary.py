import os  # LAB_ROOT: folder holding search22/, sector/, sector_lab/data/ and five_pct/
import json, pandas as pd, numpy as np, glob
for grid,pref,real in [('11-cut grid (my own)','my_','my_real_0.json'),('13-cut grid (theirs)','my13_','my13_real_0.json')]:
    r=json.load(open(real))[0]
    print(f'\n=== {grid}: REAL n_rules14/14={r["n"]} top1 IS worstQ={r["top_mn"]:.2f}% K={r["top_K"]} OOS {r["top_tepos"]}/8 avg {r["top_teavg"]:.2f}% | all qualifying mean OOS {r["all_tepos"]:.2f}/8 avg {r["all_teavg"]:.2f}%  share all-8 {r["frac_all8"]:.4f}')
    for kind in ('signflip','shuffle'):
        fs=glob.glob(f'{pref}{kind}_*.json')
        if not fs: continue
        N=pd.DataFrame(json.load(open(fs[0])))
        N=N[N.n>0]
        print(f' {kind}: runs={len(N)}  n_rules median {N.n.median():.0f} p95 {N.n.quantile(.95):.0f} share>=real {(N.n>=r["n"]).mean():.2f}')
        print(f'   top1 IS worstQ median {N.top_mn.median():.2f}% (share >= real {(N.top_mn>=r["top_mn"]).mean():.2f}); top1 trades median {N.top_K.median():.0f}')
        print(f'   top1 OOS quarters pos: dist {N.top_tepos.value_counts().sort_index().to_dict()}  share>=5: {(N.top_tepos>=5).mean():.2f}  share>=8: {(N.top_tepos>=8).mean():.2f}')
        print(f'   top1 OOS avg median {N.top_teavg.median():.2f}%  share>=+1.04%: {(N.top_teavg>=1.036).mean():.2f}  share (>=5/8 & >=1.04%): {((N.top_tepos>=5)&(N.top_teavg>=1.036)).mean():.2f}')
        print(f'   all-qualifying mean OOS pos median {N.all_tepos.median():.2f}/8, avg {N.all_teavg.median():.2f}%; frac all-8 median {N.frac_all8.median():.4f}')
