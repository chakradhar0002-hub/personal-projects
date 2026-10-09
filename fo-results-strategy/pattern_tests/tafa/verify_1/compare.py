import os  # LAB_ROOT: scratch folder with ta/, fa/, report/, sector_lab/data; REPO_ROOT: this repo
import pandas as pd, numpy as np
SP=os.environ.get('LAB_ROOT', 'lab') + ""
m=pd.read_csv('raw_events.csv')
f=pd.read_csv(f'{SP}/tafa/C_post_results/features.csv')
t=pd.read_csv(f'{SP}/tafa/C_post_results/trades.csv')
print('cand features', len(f), 'cand trades rows', len(t))
x=m.merge(f[['symbol','qn','XN','cut_rsi14','rq_pat_yoy_pct','rq_sales_yoy_pct','MCHG','GOOD','RSI_HI','W','fin_type']],on=['symbol','qn'],how='outer',indicator=True,suffixes=('','_c'))
print(x._merge.value_counts())
print(x[x._merge!='both'][['symbol','qn','_merge']])
b=x[x._merge=='both'].copy()
for a,c in [('XN','XN_c'),('rsi_cut','cut_rsi14'),('pat_yoy','rq_pat_yoy_pct'),('sales_yoy','rq_sales_yoy_pct'),('mchg_pp','MCHG')]:
    both=b[a].notna()&b[c].notna(); d=(b[a]-b[c]).abs()
    print(f'{a:10s} both {both.sum()} only-mine {(b[a].notna()&b[c].isna()).sum()} only-cand {(b[a].isna()&b[c].notna()).sum()} '
          f'|d|>0.01: {(d[both]>0.01).sum()} |d|>1: {(d[both]>1).sum()} median|d| {d[both].median():.2e}')
# my flags
b['W_m']=b.XN>4
pat,sal,mc=b.pat_yoy,b.sales_yoy,b.mchg_pp
b['GOOD_m']=((pat>25)&(sal>15))|(mc>2)
b['RSI_m']=b.rsi_cut>50
b['CAND_m']=b.W_m&b.GOOD_m&b.RSI_m&b.tradable
b['CAND_c']=b.W&b.GOOD&b.RSI_HI
for a,c in [('W_m','W'),('GOOD_m','GOOD'),('RSI_m','RSI_HI'),('CAND_m','CAND_c')]:
    print(f'{a}: mine {b[a].sum()} cand {b[c].sum()} both {(b[a]&b[c]).sum()} mine-only {(b[a]&~b[c]).sum()} cand-only {(~b[a]&b[c]).sum()}')
d=b[b.CAND_m!=b.CAND_c][['symbol','qn','XN','XN_c','rsi_cut','cut_rsi14','pat_yoy','rq_pat_yoy_pct','sales_yoy','rq_sales_yoy_pct','mchg_pp','MCHG','fin_type','fin_type_c','basis0','basis4','CAND_m','CAND_c']]
pd.set_option('display.width',250); print(d.round(2).to_string())
# RSI threshold flips
bb=b[b.W_m&b.GOOD_m]; print('winner&GOOD rsi diff >1:', ((bb.rsi_cut-bb.cut_rsi14).abs()>1).sum())
b.to_csv('compare_merged.csv',index=False)
