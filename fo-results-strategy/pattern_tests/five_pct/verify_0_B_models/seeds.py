from rf_wf import *
import itertools
rows=[]
for seed in range(3,11):
    sc=run(d.three_day.values,train_fo_only=True,seed=seed,ntree=200)
    s=stats(picks(sc,2)); s['seed']=seed; rows.append(s); print(seed,round(s['avg'],2),round(s['oos_14_21'],2),flush=True)
for leaf in [5,50]:
    sc=run(d.three_day.values,seed=0,leaf=leaf,ntree=200); s=stats(picks(sc,2)); print('leaf',leaf,round(s['avg'],2))
sc=run(d.three_day.values,seed=0,ntree=1500); s=stats(picks(sc,2)); print('1500 trees',{a:round(b,2) for a,b in s.items()})
np.save('sc_1500.npy',sc)
r=pd.DataFrame(rows); print(r.avg.describe()); r.to_csv('seed_runs.csv',index=False)
