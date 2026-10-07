"""Independent re-implementation of F1 candidate:
 bellwether = first of 3 largest (mcap) members of a Nifty sector-index group (per qn) to react.
 signal = sign of bellwether reaction-day return minus Nifty 50 return that day, if |excess|>3%.
 trade  = at reaction-day close, long(short) sector index, short(long) Nifty, hold H sessions.
Pre-registered verification grid (my own, counted):
 thresholds {2,3,4,5}% x horizons {1,2,3,5} sessions = 16 neighbours (base = 3%,1)
 variants of bellwether definition: top3 (base), top1, top5 ; bellwether-in-FO-only ; drop bellwether from index (ex-bellwether proxy not possible -> use sector index minus w*bellwether is impossible w/o weights; instead report bellwether own next-day move)
 costs: index-futures pair 0.04% (0.02 per leg), basket hedge 0.19%, doubled.
"""
import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
import sys; sys.path.append('/root/.local/lib/python3.11/site-packages')
import numpy as np, pandas as pd
D=os.environ.get('SECTOR_LAB', 'sector_lab') + '/data/'
OUT=os.environ.get('SECTOR_LAB', 'sector_lab') + '/verify_1_F1_bellwether/'
e=pd.read_csv(D+'events.csv')
ses=pd.read_csv(D+'sessions.csv')
ic=pd.read_csv(D+'index_close.csv',index_col=0)
ret=pd.read_csv(D+'returns.csv',index_col=0)
assert list(ic.index)==list(ses.day)
assert list(ret.index)==list(ses.day)
IC=ic.values; cols={c:k for k,c in enumerate(ic.columns)}
nif=IC[:,cols['Nifty 50']]
def idxret(name,i0,i1):
    c=IC[:,cols[name]]
    a,b=c[i0],c[i1]
    if np.isnan(a) or np.isnan(b): return np.nan
    return b/a-1
R=ret.values; rcols={c:k for k,c in enumerate(ret.columns)}
def stockret(sym,i0,i1):
    x=R[i0+1:i1+1,rcols[sym]]
    if np.isnan(x).any(): return np.nan  # flag missing explicitly
    return np.prod(1+x)-1

def build(topk=3, fo_only=False, tie='mcap'):
    g=e[e.sector_index!='Nifty 500'].copy()
    if fo_only: g=g[g.in_fo]
    rows=[]
    for (q,s),d in g.groupby(['qn','sector_index']):
        top=d.sort_values('mcap',ascending=False).head(topk)
        top=top.sort_values(['i_react','mcap'],ascending=[True,False])
        b=top.iloc[0]
        i=int(b.i_react)
        rb=R[i,rcols[b.symbol]] if b.symbol in rcols else np.nan
        nr=nif[i]/nif[i-1]-1
        rows.append(dict(qn=q,sector=s,sym=b.symbol,i=i,day=ses.day[i],in_fo=b.in_fo,move=b.move,rb=rb,nr=nr,exc=b.move-nr,
                         ntie=(top.i_react==i).sum(), mcap=b.mcap))
    return pd.DataFrame(rows)

def trades(bw,thr,H,cost=0.0004):
    t=bw[bw.exc.abs()>thr].copy()
    sg=np.sign(t.exc)
    t['sig']=sg
    t['sec']=[idxret(s,i,i+H) for s,i in zip(t.sector,t.i)]
    t['nif']=[nif[i+H]/nif[i]-1 for i in t.i]
    t['bw_next']=[stockret(s,i,i+H) for s,i in zip(t.sym,t.i)]
    t['raw']=sg*t.sec
    t['ls']=sg*(t.sec-t.nif)
    t['ls_net']=t.ls-cost
    t['raw_net']=t.raw-0.0002*0+(-cost/2)
    return t

def qstats(t,col):
    t=t.dropna(subset=[col])
    pq=t.groupby('qn')[col].mean()*100
    n=len(pq)
    tt=pq.mean()/(pq.std(ddof=1)/np.sqrt(n)) if n>1 else np.nan
    f=pq[pq.index<=13]; l=pq[pq.index>=14]
    # date clustering
    pd_=t.groupby('day')[col].mean()*100
    td=pd_.mean()/(pd_.std(ddof=1)/np.sqrt(len(pd_)))
    return dict(n=len(t),trade_avg=round(t[col].mean()*100,3),q_avg=round(pq.mean(),3),t_q=round(tt,2),
                first14=round(f.mean(),3),last8=round(l.mean(),3),qpos=f"{(pq>0).sum()}/{n}",t_date=round(td,2),win=round((t[col]>0).mean()*100,1))

if __name__=='__main__':
    bw=build()
    bw.to_csv(OUT+'bellwethers.csv',index=False)
    print('groups x quarters',len(bw),'ties',(bw.ntie>1).sum())
    t=trades(bw,0.03,1)
    t.to_csv(OUT+'base_trades.csv',index=False)
    print('BASE thr3 H1 (index pair cost 0.04%)')
    for c in ['raw','ls','ls_net']: print(c,qstats(t,c))
    t['ls_basket']=t.ls-0.0019
    print('basket hedge 0.19%',qstats(t,'ls_basket'))
    t['ls_2x']=t.ls-0.0008; print('cost x2 (0.08)',qstats(t,'ls_2x'))
    t['ls_basket2x']=t.ls-0.0038; print('basket cost x2',qstats(t,'ls_basket2x'))
    print('by sector'); print(t.groupby('sector').agg(n=('ls','size'),ls=('ls',lambda x:x.mean()*100)).round(3))
    print('long/short side'); print(t.groupby('sig').agg(n=('ls','size'),ls=('ls',lambda x:x.mean()*100)).round(3))
    print('bellwether own next-session signed excess vs nifty:', round(((t.sig*(t.bw_next-t.nif)).mean())*100,3), 'n', t.bw_next.notna().sum())
    print('bellwether in F&O at time:', t.in_fo.sum())
    tf=t[t.sector.isin(['Nifty Bank','Nifty Financial Services'])]
    print('Bank/FinServ only',qstats(tf,'ls_net') if len(tf)>1 else len(tf))
