import os  # LAB_ROOT: scratch folder with ta/, fa/, report/, sector_lab/data; REPO_ROOT: this repo
import numpy as np, pandas as pd
SCR=os.environ.get('LAB_ROOT', 'lab') + ""
X=pd.read_csv("rebuilt_events.csv")
ref=pd.read_csv(os.environ.get('REPO_ROOT', '.') + "/results/lag10_volume/trades.csv")
m=(X.lag< -10)&(X.vol>=1.0)
mine=X[m]
a=set(zip(mine.symbol,mine.quarter)); b=set(zip(ref.symbol,ref.quarter))
print("S85 rebuilt",len(mine),"repo",len(ref),"same",a==b,"only mine",a-b,"only repo",b-a)
j=mine.merge(ref,on=["symbol","quarter"])
print("max |3d diff|",np.abs(j.three_day_x-100*j.three_day_y).max(),"max|tp|",np.abs(j.tp3-100*j.take_profit).max(),
      "max|lag|",np.abs(j.lag-100*j.vs_nifty_1m).max(),"max|vol|",np.abs(j.vol-j.volume_ratio).max())
# near-threshold events
print("near lag/vol threshold:"); print(X[((X.lag.between(-10.3,-9.7))&(X.vol>=0.97))|((X.lag< -10)&X.vol.between(0.97,1.03))][["symbol","quarter","lag","vol"]])
T=pd.read_csv(f"{SCR}/tafa/B_lag_rule_and_model/part1_trades_S85_flags.csv")
E=pd.read_csv(f"{SCR}/ta/build/events_ta.csv",usecols=["symbol","quarter","rsi14","rsi2","stoch_k14","bb_pctb","cci20","mfi14"]).rename(columns={"rsi14":"p_rsi14","rsi2":"p_rsi2"})
F=pd.read_csv(f"{SCR}/fa/build/fa_panel.csv",usecols=["symbol","quarter","loss_any_4q","l1_sales_yoy_pct","l1_pat_yoy_pct"])
J=mine.merge(E,on=["symbol","quarter"]).merge(F,on=["symbol","quarter"]).merge(T[["symbol","quarter","X8_goodfund&oversold3"]],on=["symbol","quarter"])
for a_,b_ in [("rsi14","p_rsi14"),("rsi2","p_rsi2"),("stochk","stoch_k14"),("pctb","bb_pctb"),("cci","cci20"),("mfi","mfi14"),("sales_yoy","l1_sales_yoy_pct"),("pat_yoy","l1_pat_yoy_pct"),("loss4","loss_any_4q")]:
    d=np.abs(J[a_]-J[b_]); print(f"{a_:10s} max diff {d.max():.4g}  n>0.01 {(d>0.01).sum()}  nan mine {J[a_].isna().sum()} theirs {J[b_].isna().sum()}")
def os3(d,c):
    return ((d[c[0]]<30).astype(int)+(d[c[1]]<10)+(d[c[2]]<20)+(d[c[3]]<0)+(d[c[4]]< -100)+(d[c[5]]<20))
J["os_mine"]=os3(J,["rsi14","rsi2","stochk","pctb","cci","mfi"]); J["os_their"]=os3(J,["p_rsi14","p_rsi2","stoch_k14","bb_pctb","cci20","mfi14"])

J["gf_mine"]=np.where((J.loss4==0)&(J.sales_yoy>0)&(J.pat_yoy>0),1,np.where((J.loss4==1)|(J.sales_yoy<=0)|(J.pat_yoy<=0),0,-1))
J["x8_mine"]=np.where(J.gf_mine==-1,-1,((J.gf_mine==1)&(J.os_mine>=3)).astype(int))
print("os mine vs theirs disagreements", (J.os_mine>=3).ne(J.os_their>=3).sum(), " os3 count", (J.os_mine>=3).sum())
print(pd.crosstab(J.x8_mine,J["X8_goodfund&oversold3"]))
bad=J[J.x8_mine.ne(J["X8_goodfund&oversold3"])|(J.os_mine!=J.os_their)]
print(bad[["symbol","quarter","os_mine","os_their","loss4","loss_any_4q","sales_yoy","l1_sales_yoy_pct","pat_yoy","l1_pat_yoy_pct","x8_mine","X8_goodfund&oversold3"]].round(2).to_string())
sel=J[J.x8_mine==1]
print("X8 mine n",len(sel),"mean",sel.three_day.mean().round(3),"tp",sel.tp3.mean().round(3))
J.to_csv("s85_joined.csv",index=False)
