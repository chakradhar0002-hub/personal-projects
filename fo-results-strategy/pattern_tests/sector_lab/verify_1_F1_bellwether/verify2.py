"""Verification part 2 (written before running; all variants counted here).
A. Re-implement candidate with THEIR size rule (prev-quarter mcap, ties -> mean signal), compare trade-by-trade.
B. Decomposition: bellwether's own next-session excess vs sector-index-ex-bellwether proxy
   (ex-bw proxy = equal-weight average of the other F&O group members' returns, minus Nifty).
C. Robustness: thr {2,2.5,3,3.5,4,5}% x H {1,2,3,5}; drop top5 trades; drop best quarter; leave-one-sector-out;
   leave-one-quarter-out; costs 0.04/0.08/0.19/0.38; entry delayed 1 session (enter close d+1, hold 1).
D. Placebos (2000 draws each): (1) signs shuffled within quarter across triggers (theirs);
   (2) random-date placebo: same sector, same thresholds, but the "bellwether" is the same stock on a random
       session without any result of that stock within +-5 sessions, signal = its excess vs Nifty that day;
       compare: does ANY large-stock >3% excess day predict next-day sector-index excess? (i.e. is it about results?)
   (3) random big-stock placebo on the actual trigger dates: pick a random other top-3 member of a random sector.
Total new variant cells evaluated: 1 (A) + 24 (grid) + LOO/LOSO (diagnostics on the same rule) + 3 placebos.
"""
import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
import sys; sys.path.append('/root/.local/lib/python3.11/site-packages')
import numpy as np, pandas as pd
D=os.environ.get('SECTOR_LAB', 'sector_lab') + '/data/'
OUT=os.environ.get('SECTOR_LAB', 'sector_lab') + '/verify_1_F1_bellwether/'
rng=np.random.default_rng(2024)
e=pd.read_csv(D+'events.csv'); ses=pd.read_csv(D+'sessions.csv')
ic=pd.read_csv(D+'index_close.csv',index_col=0); ret=pd.read_csv(D+'returns.csv',index_col=0)
R=ret.values; rc={c:k for k,c in enumerate(ret.columns)}
nifc=ic['Nifty 50'].values; nr=np.r_[np.nan,nifc[1:]/nifc[:-1]-1]
IX={c:ic[c].values for c in ic.columns}
def ir(name,a,b):
    c=IX[name]; return c[b]/c[a]-1
def tq(pq):
    pq=pq.dropna(); return pq.mean()/(pq.std(ddof=1)/np.sqrt(len(pq)))
def summ(qn,v,day=None):
    s=pd.Series(v).groupby(np.asarray(qn)).mean()*100
    out=dict(n=len(v),q=len(s),avg=round(np.nanmean(v)*100,3),qavg=round(s.mean(),3),t=round(tq(s),2),
             f14=round(s[s.index<=13].mean(),3),l8=round(s[s.index>=14].mean(),3),qpos=int((s>0).sum()))
    if day is not None:
        d=pd.Series(v).groupby(np.asarray(day)).mean(); out['t_date']=round(tq(d),2)
    return out
e['xr']=e.move-nr[e.i_react.values]
prev=e[['symbol','qn','mcap']].copy(); prev['qn']+=1
e=e.merge(prev.rename(columns={'mcap':'mprev'}),on=['symbol','qn'],how='left')
e['size']=np.where(e.qn==0,e.mcap,e.mprev)
g=e[e.sector_index!='Nifty 500']
rows=[]
for (q,s),m in g.groupby(['qn','sector_index']):
    k=m[m['size'].notna()]
    if len(m)<2 or len(k)<3: continue
    top=k.nlargest(3,'size'); d=top.i_react.min(); x=top[top.i_react==d]
    others=m[~m.symbol.isin(x.symbol)]
    rows.append(dict(qn=q,sector=s,d=int(d),sig=x.xr.mean(),bws='|'.join(x.symbol),nbw=len(x),
                     others='|'.join(others.symbol)))
T=pd.DataFrame(rows); T['day']=ses.day.values[T.d]
def trade_vals(T,thr,H,lag=0):
    x=T[T.sig.abs()>thr].copy()
    a=x.d.values+lag; b=a+H
    sec=np.array([ir(s,i,j) for s,i,j in zip(x.sector,a,b)])
    nn=nifc[b]/nifc[a]-1
    x['sg']=np.sign(x.sig); x['vsn']=x.sg*(sec-nn); x['raw']=x.sg*sec
    return x[~np.isnan(sec)]
def stk(sym,a,b):
    v=R[a+1:b+1,rc[sym]]
    if np.isnan(v).any(): return np.nan
    return np.prod(1+v)-1
if __name__=='__main__':
    base=trade_vals(T,0.03,1); base.to_csv(OUT+'base_trades_theirdef.csv',index=False)
    print('A. their-definition replication, 0.04 cost:',summ(base.qn,base.vsn-0.0004,base.day))
    print('   raw (signed sector) net 0.02:',summ(base.qn,base.raw-0.0002))
    print('   basket hedge 0.19:',summ(base.qn,base.vsn-0.0019,base.day))
    print('   nbw>1 (ties) trades:',(base.nbw>1).sum())
    # compare with their index_trades
    it=pd.read_csv(os.environ.get('SECTOR_LAB', 'sector_lab') + '/F1_bellwether/index_trades.csv')
    it=it[(it.BW=='BIG')&(it.h==1)&(it.signal.abs()>0.03)]
    mg=base.merge(it,left_on=['qn','sector','d'],right_on=['qn','group','d'],how='outer',indicator=True)
    print('   match vs their trades:',mg._merge.value_counts().to_dict(),' max |vsn diff|',np.nanmax(np.abs(mg.vsn_x-np.sign(mg.signal)*mg.vsn_y)))
    # B decomposition
    bwn=[];exn=[]
    for r in base.itertuples():
        bwn.append(np.nanmean([stk(s,r.d,r.d+1) for s in r.bws.split('|')])-(nifc[r.d+1]/nifc[r.d]-1))
        oth=[stk(s,r.d,r.d+1) for s in r.others.split('|') if s in rc] if r.others else []
        exn.append(np.nanmean(oth)-(nifc[r.d+1]/nifc[r.d]-1) if len(oth) else np.nan)
    base['bw_next']=base.sg*np.array(bwn); base['oth_next']=base.sg*np.array(exn)
    print('B. bellwether own next-session signed excess:',summ(base.qn,base.bw_next))
    print('   other group members (EW, all incl. already reported) signed excess:',summ(base.dropna(subset=['oth_next']).qn,base.dropna(subset=['oth_next']).oth_next))
    # C robustness
    print('C. grid thr x H (vsn net 0.04):')
    for thr in [0.02,0.025,0.03,0.035,0.04,0.05]:
        for H in [1,2,3,5]:
            x=trade_vals(T,thr,H); s=summ(x.qn,x.vsn-0.0004)
            print(f'   thr {thr:.3f} H{H}: n {s["n"]} qavg {s["qavg"]} t {s["t"]} f14 {s["f14"]} l8 {s["l8"]} qpos {s["qpos"]}/{s["q"]}')
    x=trade_vals(T,0.03,1,lag=1); print('   delayed entry (close d+1, hold 1):',summ(x.qn,x.vsn-0.0004))
    v=base.vsn-0.0004
    b2=base.loc[v.sort_values().index[:-5]]; print('   drop top5 trades:',summ(b2.qn,b2.vsn-0.0004))
    pq=(base.assign(v=v).groupby('qn').v.mean()); bq=pq.idxmax()
    b3=base[base.qn!=bq]; print('   drop best quarter',bq,':',summ(b3.qn,b3.vsn-0.0004))
    b4=base.loc[v.sort_values().index[5:]]; print('   drop worst5 (symmetry):',summ(b4.qn,b4.vsn-0.0004))
    print('   per-quarter %:',(pq*100).round(2).to_dict())
    print('   LOSO:')
    for s in sorted(base.sector.unique()):
        b=base[base.sector!=s]; r=summ(b.qn,b.vsn-0.0004); print(f'     -{s:28s} qavg {r["qavg"]} t {r["t"]}')
    lq=[]
    for q in sorted(base.qn.unique()):
        b=base[base.qn!=q]; lq.append(summ(b.qn,b.vsn-0.0004)['t'])
    print('   LOQO t range',min(lq),max(lq))
    print('   costs:',{c:summ(base.qn,base.vsn-c)['qavg'] for c in [0.0004,0.0008,0.0019,0.0038]})
    print('   long vs short:',{k:summ(b.qn,b.vsn-0.0004) for k,b in base.groupby('sg')})
    # D placebos
    act=summ(base.qn,base.vsn-0.0004); a_m,a_t=act['qavg'],act['t']
    # D1 shuffle within quarter among all triggers with index data
    allx=trade_vals(T,-1,1)  # all triggers
    sig=allx.sig.values; qn=allx.qn.values; sv=allx.vsn.values*allx.sg.values  # unsigned sector excess
    grp=[np.where(qn==k)[0] for k in np.unique(qn)]
    M=[];TT=[]
    for _ in range(2000):
        ps=sig.copy()
        for idx in grp: ps[idx]=sig[rng.permutation(idx)]
        mk=np.abs(ps)>0.03; s=summ(qn[mk],np.sign(ps[mk])*sv[mk]-0.0004); M.append(s['qavg']); TT.append(s['t'])
    M=np.array(M);TT=np.array(TT)
    print(f'D1 shuffle-within-quarter: mean placebo {M.mean():.3f}, P(mean>=act) {np.mean(M>=a_m):.4f}, P(t>=act) {np.mean(TT>=a_t):.4f}')
    # D2 random non-result dates for big stocks: does a >3% excess day of a top-3 sector stock (no results within +-5)
    # predict next-day sector-minus-Nifty? Use all top-3 members, sessions in study window.
    lo=int(e.i_cut.min()); hi=int(e.i_p1.max())
    resd={}
    for r in e.itertuples(): resd.setdefault(r.symbol,set()).update(range(r.i_react-5,r.i_react+6))
    pr=[]
    tops=[]
    for (q,s),m in g.groupby(['qn','sector_index']):
        k=m[m['size'].notna()]
        if len(m)<2 or len(k)<3: continue
        for sym in k.nlargest(3,'size').symbol: tops.append((q,s,sym))
    tops=pd.DataFrame(tops,columns=['qn','sector','sym'])
    qwin=e.groupby('qn').agg(a=('i_cut','min'),b=('i_p1','max'))
    # quarter windows: use calendar of results season [min cutoff, max p1] of each qn
    for r in tops.itertuples():
        a,b=qwin.loc[r.qn]
        if r.sym not in rc: continue
        col=R[:,rc[r.sym]]; c=IX[r.sector]
        for i in range(int(a),int(b)):
            if i in resd[r.sym] or np.isnan(col[i]) or np.isnan(c[i]) or np.isnan(c[i+1]): continue
            x=col[i]-nr[i]
            if abs(x)>0.03:
                pr.append((r.qn,r.sector,i,np.sign(x)*((c[i+1]/c[i]-1)-(nifc[i+1]/nifc[i]-1)),np.sign(x)*(R[i+1,rc[r.sym]]-nr[i+1]) if not np.isnan(R[i+1,rc[r.sym]]) else np.nan))
    pr=pd.DataFrame(pr,columns=['qn','sector','i','vsn','own'])
    print('D2 non-result big-stock >3% days -> next-day signed sector excess (all such days):',summ(pr.qn,pr.vsn-0.0004,pr.i),
          ' own next-day signed:',round(pr.own.mean()*100,3))
    # resample: same number of trades per quarter as actual, 2000 draws
    cnt=base.groupby('qn').size()
    M2=[];T2=[]
    pg={q:pr[pr.qn==q] for q in cnt.index}
    for _ in range(2000):
        vv=[];qq=[]
        for q,n in cnt.items():
            p=pg[q]
            if len(p)==0: continue
            ch=p.vsn.values[rng.integers(0,len(p),n)]; vv+=list(ch); qq+=[q]*n
        s=summ(qq,np.array(vv)-0.0004); M2.append(s['qavg']); T2.append(s['t'])
    M2=np.array(M2);T2=np.array(T2)
    print(f'   resampled to actual per-quarter counts: mean placebo {M2.mean():.3f}, P(mean>=act) {np.mean(M2>=a_m):.4f}, P(t>=act) {np.mean(T2>=a_t):.4f}')
    # D3 random-sector placebo: on actual trigger dates/signs, measure a random OTHER sector index
    secs=[s for s in g.sector_index.unique()]
    M3=[];T3=[]
    for _ in range(2000):
        vv=[]
        for r in base.itertuples():
            while True:
                s=secs[rng.integers(len(secs))]
                if s!=r.sector and not np.isnan(IX[s][r.d]) and not np.isnan(IX[s][r.d+1]): break
            vv.append(r.sg*(ir(s,r.d,r.d+1)-(nifc[r.d+1]/nifc[r.d]-1)))
        s=summ(base.qn,np.array(vv)-0.0004); M3.append(s['qavg']); T3.append(s['t'])
    M3=np.array(M3);T3=np.array(T3)
    print(f'D3 random other sector same date/sign: mean placebo {M3.mean():.3f}, P(mean>=act) {np.mean(M3>=a_m):.4f}, P(t>=act) {np.mean(T3>=a_t):.4f}')
