# Feature-only probe (no outcome columns read): prevalence of the planned signals.
import pandas as pd, numpy as np
P='../build/fa_panel.csv'
cols=['symbol','qn','in_fo','fin_type','timing','results_date','reaction_day','rq_sales_yoy_pct','rq_pat_yoy_pct',
      'rq_ebitda_margin_chg_yoy_pp','rq_net_margin_chg_yoy_pp','rq_pat_surprise_vs_trend_pp',
      'rq_loss_to_profit_yoy','rq_profit_to_loss_yoy','rq_xbrl_lag_days']
d=pd.read_csv(P,usecols=cols)
print(d.in_fo.value_counts(dropna=False))
f=d[d.in_fo==True].copy()
print(len(f), f.fin_type.value_counts().to_dict(), f.timing.value_counts().to_dict())
f['mchg']=np.where(f.fin_type=='Company',f.rq_ebitda_margin_chg_yoy_pp,f.rq_net_margin_chg_yoy_pp)
sig={'strong':(f.rq_pat_yoy_pct>25)&(f.rq_sales_yoy_pct>15),'weak':f.rq_pat_yoy_pct<-25,
     'mup':f.mchg>2,'mdown':f.mchg<-2,'l2p':f.rq_loss_to_profit_yoy==1,'p2l':f.rq_profit_to_loss_yoy==1,
     'surp_nonnull':f.rq_pat_surprise_vs_trend_pp.notna(),'mchg_nonnull':f.mchg.notna()}
print(pd.DataFrame({k:v.groupby(f.qn).sum() for k,v in sig.items()}).astype(int).to_string())
print({k:int(v.sum()) for k,v in sig.items()})
print('company mchg via ebitda nonnull', f[f.fin_type=='Company'].rq_ebitda_margin_chg_yoy_pp.notna().sum(), 'of', (f.fin_type=='Company').sum())
print('fin mchg via net nonnull', f[f.fin_type!='Company'].rq_net_margin_chg_yoy_pp.notna().sum(), 'of', (f.fin_type!='Company').sum())
