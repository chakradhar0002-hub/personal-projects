import os  # LAB_ROOT: folder holding search22/, sector/, sector_lab/data/ and five_pct/
import numpy as np, pandas as pd
SP=os.environ.get('LAB_ROOT', 'lab') + ''
D=f'{SP}/sector_lab/data'
F=pd.read_csv(f'{SP}/five_pct/A_rule_search/features_all.csv')
E=pd.read_csv(f'{D}/events.csv')[['symbol','qn','i_p1']]
R=pd.read_csv(f'{D}/returns.csv'); I=pd.read_csv(f'{D}/intraday.csv')
days=pd.to_datetime(R.day).values
RA=R.drop(columns='day'); cols={c:k for k,c in enumerate(RA.columns)}; RA=RA.values.astype(float)
IA=I.drop(columns='day')[R.drop(columns='day').columns].values.astype(float)
F=F.merge(E,on=['symbol','qn']).sort_values(['symbol','qn']).reset_index(drop=True)
F['prev_p1']=F.groupby('symbol').i_p1.shift(1)
F['prev_cut']=F.groupby('symbol').cutoff.shift(1); F['prev_dsd']=F.groupby('symbol').days_since_dividend.shift(1)
rows=[]
for _,ev in F.iterrows():
    j=cols[ev.symbol]
    for k in (8,12,16,20,24,28,32,36,40):
        i=ev.i_cut-k
        if not np.isnan(ev.prev_p1) and i-5<=ev.prev_p1: continue   # placebo window must start after previous results window
        if np.isnan(ev.prev_p1) and k>20: continue
        r=RA[:i+1,j]; intr=IA[:i+1,j]
        gap=(1+r[-5:])/(1+intr[-5:])-1
        if np.isfinite(gap).sum()<3: continue
        g5=np.nansum(gap)
        fwd=RA[i+1:i+4,j]
        if not np.isfinite(fwd).all(): continue
        delta=(pd.Timestamp(ev.cutoff)-pd.Timestamp(days[i])).days
        dsd=ev.days_since_dividend
        if dsd>=9999: dsd_p=9999
        elif dsd-delta>=0: dsd_p=dsd-delta
        elif not pd.isna(ev.prev_cut): dsd_p=ev.prev_dsd+(pd.Timestamp(days[i])-pd.Timestamp(ev.prev_cut)).days
        else: dsd_p=np.nan
        rows.append(dict(symbol=ev.symbol,qn=ev.qn,k=k,in_fo=ev.in_fo,gap5=g5,own_dm1=ev.own_dm1,dsd=dsd_p,fwd3=fwd.sum()*100))
P=pd.DataFrame(rows); P.to_csv('placebo_rows.csv',index=False)
fo=P[P.in_fo]
print('placebo F&O rows',len(fo),'base win',round((fo.fwd3>0).mean()*100,1),'avg',round(fo.fwd3.mean(),2))
for nm,m in [('full rule',(fo.dsd>=154)&(fo.gap5<=-0.01678)&(fo.own_dm1<=0.003908)),('gap5&dsd',(fo.dsd>=154)&(fo.gap5<=-0.01678)),('gap5 only',fo.gap5<=-0.01678)]:
    for s,g in [('qn<14',fo[m&(fo.qn<14)]),('qn>=14',fo[m&(fo.qn>=14)]),('all',fo[m])]:
        print(f'{nm:10s} {s:7s} n={len(g):4d} win={(g.fwd3>0).mean()*100:5.1f}% avg={g.fwd3.mean():+.2f}')
