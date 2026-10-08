import os  # LAB_ROOT: folder holding search22/, sector/, sector_lab/data/ and five_pct/
import pandas as pd, numpy as np
S=os.environ.get('LAB_ROOT', 'lab') + '/'
idx=pd.read_csv(S+'sector_lab/data/index_close.csv',index_col=0); ses=pd.read_csv(S+'sector_lab/data/sessions.csv')
print('index dates aligned',(idx.index.values==ses.day.values).all())
m=pd.read_csv('rebuilt.csv')
fa=pd.read_csv(S+'five_pct/A_rule_search/features_all.csv')
m=m.merge(fa[['symbol','qn','tp3','timing']],on=['symbol','qn'])
def pick(d,a=-0.02782,b=-0.00891,c=-0.01338):
    return d[(d.r3d_cmp<=a)&(d.intra0<=b)&(d.sec_3d>=c)]
def rep(p,col='pnl',lab=''):
    q=p.groupby('qn')[col].mean()
    print(f"{lab:28s} n={len(p):4d} win={100*(p[col]>0).mean():5.1f}% winAC={100*(p[col]>0.0017).mean():5.1f}% avg={100*p[col].mean():6.2f}% qpos={(q>0).sum()}/{len(q)} qposAC={(q>0.0017).sum()}/{len(q)} worstQ={100*q.min():6.2f} worstT={100*p[col].min():6.2f}")
    return q
fo=m[m.in_fo]
p=pick(fo).copy(); p['pnl']=-p.td; p['pnl_tp']=-p.tp3
q=rep(p,'pnl','all22')
rep(p[p.qn<14],'pnl','first14'); rep(p[p.qn>=14],'pnl','last8')
rep(p,'pnl_tp','TP col (short of tp3)')
print('per quarter n / avg%:'); g=p.groupby('qn').pnl.agg(['size','mean']); g['mean']*=100; print(g.round(2).T.to_string())
# all stocks
pa=pick(m).copy(); pa['pnl']=-pa.td; rep(pa,'pnl','all stocks'); print('pre-FO survivors in all-stocks picks',(~pa.in_fo).sum())
# baseline: shorting every in_fo stock
fo2=fo.copy(); fo2['pnl']=-fo2.td; rep(fo2,'pnl','short all in_fo'); rep(fo2[fo2.qn>=14],'pnl','short all in_fo last8')
p.to_csv('cand_trades.csv',index=False)
