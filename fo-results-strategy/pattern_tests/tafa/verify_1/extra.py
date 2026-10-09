import pandas as pd, numpy as np
a=pd.read_csv('analysis_rows.csv')
a['GOOD']=((a.pat_yoy>25)&(a.sales_yoy>15))|(a.mchg_pp>2)
EG=(a.pat_yoy.notna()&a.sales_yoy.notna())|a.mchg_pp.notna()
W=a.XN>4; hi=a.rsi_cut>50
def qt(m1,m0,col='v20'):
    d=(a[m1].groupby('qn')[col].mean()-a[m0].groupby('qn')[col].mean()).dropna()
    return d.mean(), d.mean()/(d.std(ddof=1)/np.sqrt(len(d))), (d>0).sum(), len(d)
print('within-quarter RSI>50 minus <=50, H20: all results %.2f t %.2f %d/%d'%qt(hi,~hi))
print('                                  non-winners %.2f t %.2f %d/%d'%qt(hi&~W,~hi&~W))
print('                                  winners     %.2f t %.2f %d/%d'%qt(hi&W,~hi&W))
print('                                  winners&GOOD %.2f t %.2f %d/%d'%qt(hi&W&a.GOOD,~hi&W&a.GOOD))
print('GOOD minus notGOOD within winners&RSI>50: %.2f t %.2f %d/%d'%qt(hi&W&a.GOOD,hi&W&~a.GOOD&EG))
c=W&a.GOOD&hi
print('n',c.sum())
b=pd.cut(a.rsi_cut,[50,60,70,100])
print('\ncandidate by RSI band (H20 net):'); print(a[c].groupby(b[c]).v20.agg(['size','mean','median']).round(2))
print('winners (any FA) by RSI band:'); print(a[W&hi].groupby(b[W&hi]).v20.agg(['size','mean','median']).round(2))
x=a.loc[c,'v20'].sort_values()
print('candidate median %.2f, trimmed 5%% each side %.2f'%(x.median(), x.iloc[int(.05*len(x)):int(.95*len(x))].mean()))
print('without best 10 %.2f, without best quarter(qn10) and best 5 %.2f'%(x.iloc[:-10].mean(), a.loc[c&(a.qn!=10),'v20'].sort_values().iloc[:-5].mean()))
a['yr']=a.results_date.str[:4]
print('candidate by year'); print(a[c].groupby('yr').v20.agg(['size','mean']).round(2).T)
print('plain winners by year'); print(a[W].groupby('yr').v20.agg(['size','mean']).round(2).T)
print('unhedged raw net candidate %.2f; nifty over hold %.2f'%((a.loc[c,'raw_H20']-0.17).mean(), a.loc[c,'nif_H20'].mean()))
print('best 5 trades:'); print(a[c].nlargest(5,'v20')[['symbol','qn','rsi_cut','XN','v20']].round(2))
