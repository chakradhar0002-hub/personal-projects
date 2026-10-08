import pandas as pd, numpy as np
for tag in ['fo_thr0.0','fo_thr0.0017']:
    N=pd.read_csv(f'nulls_{tag}.csv'); r=N[N.kind=='real'].iloc[0]; n=N[N.kind!='real']
    print('==',tag,'null runs',n.groupby('kind').size().to_dict())
    print(' real largest',r.largest,'count m10/m15/m20',r.count100_m10,r.count100_m15,r.count100_m20,'largest OOS wr',round(r.largest_oos_wr,1))
    for k,g in n.groupby('kind'):
        print(f' {k}: largest median {g.largest.median()} range {g.largest.min()}-{g.largest.max()}; share >= real {(g.largest>=r.largest).mean()*100:.0f}%; '
              f'count m20 median {g.count100_m20.median()} (real {r.count100_m20}) share>=real {(g.count100_m20>=r.count100_m20).mean()*100:.0f}%; count m10 median {g.count100_m10.median()}')
        print(f'    largest-rule OOS wr: mean {g.largest_oos_wr.mean():.1f}%  share >= real {(g.largest_oos_wr>=r.largest_oos_wr).mean()*100:.0f}%; OOS n median {g.largest_oos_n.median()}; all100_m20 pooled OOS wr mean {g.all100_m20_oos_pooled_wr.mean():.1f}')
    print(' real all100_m20 OOS pooled wr', round(r.all100_m20_oos_pooled_wr,1), 'm10', round(r.all100_m10_oos_pooled_wr,1))
