s=open('v05_family_split.py').read()
i=s.index("qn=fo.qn.values"); j=s.index("for minn in [10,19]:")
new='''qn=fo.qn.values; y0=fo.three_day.values
OH=np.zeros((len(qn),22),np.float32); OH[np.arange(len(qn)),qn]=1
Nq=M@OH  # rules x quarters counts
def run(y,minn_in=10):
    Sq=M@(OH*y[:,None].astype(np.float32))
    def pick(qs,minn):
        n=Nq[:,qs].sum(1); s=Sq[:,qs].sum(1); m=np.where(n>=minn,s/np.maximum(n,1),-9); return m.argmax(), m.max()
    k,best=pick(slice(0,14),minn_in)
    on=Nq[k,14:].sum(); oos=Sq[k,14:].sum()/on if on else np.nan
    ws=0;wn=0
    for q in range(6,22):
        k2,_=pick(slice(0,q),max(5,int(minn_in*q/14))); ws+=Sq[k2,q]; wn+=Nq[k2,q]
    kall,ball=pick(slice(0,22),30)
    return best*100,oos*100,on,(ws/wn*100 if wn else np.nan),wn,ball*100,k
'''
open('v05_family_split.py','w').write(s[:i]+new+s[j:])
