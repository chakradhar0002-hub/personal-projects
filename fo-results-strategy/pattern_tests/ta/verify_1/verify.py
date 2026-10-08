"""Independent verification of 'lag10 + volume 1.3x' (in_fo, lag_pct < -10, vol_ratio_5_60 >= 1.3).
Indicators rebuilt from RAW px + ca (not from the TA panel, not from returns.csv for the lag):
  lag  = 100*(adjusted close ratio k/k-21 using raw closes x bonus/split factors - Nifty 50 ratio k/k-21)
  vol  = mean last 5 sessions / mean last 60 sessions of raw volume x factors of ex-dates after that day (traded days only)
Outcomes recomputed from returns.csv (sum of daily returns on i_m1, i_rd, i_p1), percent.
"""
import os  # LAB_ROOT: scratch folder with sector_lab/data, report/nse_prices.db, ta/; REPO_ROOT: this repo
import sqlite3, numpy as np, pandas as pd, sys
SC = os.environ.get('LAB_ROOT', 'lab') + ""
DATA, DB = f"{SC}/sector_lab/data", f"{SC}/report/nse_prices.db"
OUT = f"{SC}/ta/verify_1"
REPO = os.environ.get('REPO_ROOT', '.') + "/results/lag10_volume"
COST = 0.17
rng = np.random.default_rng(7)

ses = pd.read_csv(f"{DATA}/sessions.csv").day.tolist()
T = len(ses); days = np.array(ses)
R = pd.read_csv(f"{DATA}/returns.csv", index_col=0)
assert R.index.tolist() == ses
syms = R.columns.tolist(); N = len(syms); col = {s: j for j, s in enumerate(syms)}
Rv = R.to_numpy(float) * 100
nifty = pd.read_csv(f"{DATA}/index_close.csv", index_col=0, usecols=["day", "Nifty 50"])["Nifty 50"].reindex(ses).to_numpy()
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
px = pd.read_sql("SELECT day, symbol, close, volume FROM px", con)
ca = pd.read_sql("SELECT symbol, ex_date, kind, factor FROM ca", con)
con.close()
px = px[px.day.isin(set(ses)) & px.symbol.isin(set(syms))]
C = px.pivot(index="day", columns="symbol", values="close").reindex(index=ses, columns=syms).to_numpy(float).copy()
V = px.pivot(index="day", columns="symbol", values="volume").reindex(index=ses, columns=syms).to_numpy(float).copy()
V[V <= 0] = np.nan
V[~np.isfinite(C)] = np.nan

# share-multiplier factor: CF[t] = product of factors of bonus/split ex-dates <= day t (cumulative), so
# adjusted price = raw close * CF[t] / CF[last]; adjusted volume = raw volume * (CF[last]/CF[t])
CF = np.ones((T, N))
nca = 0
for r in ca.itertuples():
    j = col.get(r.symbol)
    if j is None or r.kind not in ("bonus", "split") or not (r.factor == r.factor):
        continue
    CF[days >= r.ex_date, j] *= r.factor; nca += 1
print("bonus/split actions used:", nca)
adjC = C * CF
adjV = V / CF * CF[-1][None, :]

def ffill(a):
    return pd.DataFrame(a).ffill().to_numpy()
aC = ffill(adjC)  # if no trade at k or k-21, use last traded close (rare)
s21 = np.full((T, N), np.nan); s21[21:] = aC[21:] / aC[:-21] - 1
n21 = np.full(T, np.nan); n21[21:] = nifty[21:] / nifty[:-21] - 1
LAG = 100 * (s21 - n21[:, None])
Vd = pd.DataFrame(adjV)
VR = (Vd.rolling(5, min_periods=1).mean() / Vd.rolling(60, min_periods=1).mean()).to_numpy()

# demerger check (lag via raw closes would be wrong around a demerger)
dm = ca[ca.kind == "demerger"]

E = pd.read_csv(f"{DATA}/events.csv")
E["j"] = E.symbol.map(col)
E = E[E.j.notna()].copy(); E["j"] = E.j.astype(int)
k = E.i_cut.to_numpy(); j = E.j.to_numpy()
E["lag_me"] = LAG[k, j]; E["vr_me"] = VR[k, j]
d1, d2, d3 = Rv[E.i_m1, j], Rv[E.i_rd, j], Rv[E.i_p1, j]
E["y"] = d1 + d2 + d3
E["tp"] = np.where(d1 > 3, d1, np.where(d1 + d2 > 3, d1 + d2, d1 + d2 + d3))
# lag via returns.csv as a second check
G = np.cumprod(1 + np.nan_to_num(Rv / 100), axis=0)
E["lag_ret"] = 100 * (G[k, j] / G[k - 21, j] - 1 - n21[k])
# demerger within 21 sessions -> flag
E["dm21"] = False
for r in dm.itertuples():
    m = (E.symbol == r.symbol) & (E.cutoff >= r.ex_date) & (pd.to_datetime(E.cutoff) - pd.to_datetime(r.ex_date) < pd.Timedelta(days=35))
    E.loc[m, "dm21"] = True
print("events max |three_day*100 - y|:", np.nanmax(np.abs(E.three_day * 100 - E.y)))
print("lag raw vs returns-chain, |diff| > 0.5pp:", (np.abs(E.lag_me - E.lag_ret) > 0.5).sum(), "of", E.lag_me.notna().sum())
F = E[(E.in_fo == True) & E.y.notna()].copy()
print("in_fo events:", len(F), "mean", round(F.y.mean(), 3))

def rule(df, lag=-10, vol=1.3, lagcol="lag_me", vcol="vr_me"):
    return df[(df[lagcol] < lag) & (df[vcol] >= vol)]

S = rule(F)
ref = pd.read_csv(f"{REPO}/trades_vol13.csv")
k1, k2 = set(zip(S.symbol, S.quarter)), set(zip(ref.symbol, ref.quarter))
print(f"\nMY REBUILD: {len(S)} trades; repo 44; common {len(k1 & k2)}; only mine {sorted(k1 - k2)}; only repo {sorted(k2 - k1)}")
S2 = rule(F, lagcol="lag_ret")
print("rebuild with returns-chain lag:", len(S2), "common with repo", len(set(zip(S2.symbol, S2.quarter)) & k2))
# boundary cases
bd = F[((F.lag_me < -10) & (F.vr_me.between(1.2, 1.4))) | ((F.vr_me >= 1.3) & F.lag_me.between(-11, -9))]
print("near-boundary in_fo events (lag -11..-9 w/ vol>=1.3, or vol 1.2..1.4 w/ lag<-10):", len(bd))
mm = S.merge(ref, on=["symbol", "quarter"])
print("max |lag me - repo|:", np.abs(mm.lag_me - 100 * mm.vs_nifty_1m).max().round(4), " max |vr me - repo|:", np.abs(mm.vr_me - mm.volume_ratio).max().round(4))
print("trades with demerger in prior ~21 sessions:", S.dm21.sum(), "; split_in_window in repo:", ref.split_in_window.sum())

ALLQ = F.groupby("qn")
pools = {q: g.y.to_numpy() for q, g in ALLQ}

def luck(sub, nrep=20000):
    cnt = sub.qn.value_counts()
    tot = np.zeros(nrep)
    for q, n in cnt.items():
        p = pools[q]
        idx = rng.integers(0, len(p), size=(nrep, n))   # with replacement approx; small n vs pool
        tot += p[idx].sum(1)
    rm = tot / len(sub)
    return (np.sum(rm >= sub.y.mean()) + 1) / (nrep + 1), rm.mean(), np.percentile(rm, 99)

def report(sub, name):
    y = sub.y.to_numpy(); n = len(y)
    if n == 0:
        return {"rule": name, "n": 0}
    qm = sub.groupby("qn").y.mean()
    ys = np.sort(y)
    bq = qm.idxmax()
    # quarter-cluster t: t on quarter means
    tq = qm.mean() / (qm.std(ddof=1) / np.sqrt(len(qm))) if len(qm) > 2 else np.nan
    loqo = [sub[sub.qn != q].y.mean() for q in qm.index]
    return {"rule": name, "n": n, "mean": y.mean(), "net": y.mean() - COST, "tp": sub.tp.mean(), "tp_net": sub.tp.mean() - COST,
            "up%": 100 * (y > 0).mean(), "median": np.median(y), "q": f"{(qm > 0).sum()}/{len(qm)}",
            "f14": sub[sub.qn <= 13].y.mean(), "n14": (sub.qn <= 13).sum(), "l8": sub[sub.qn >= 14].y.mean(), "n8": (sub.qn >= 14).sum(),
            "xb5": ys[:-5].mean() if n > 5 else np.nan, "x_bestq": sub[sub.qn != bq].y.mean(), "loqo_min": min(loqo),
            "qmean_t": tq, "worst": ys[0], "best": ys[-1]}

pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_rows", 200)
rows = [report(S, "CAND lag<-10 vol>=1.3")]
for lag in (-8, -9, -10, -11, -12, -15):
    for vol in (1.0, 1.2, 1.3, 1.4, 1.5):
        if lag == -10 and vol == 1.3:
            continue
        rows.append(report(rule(F, lag, vol), f"lag<{lag} vol>={vol}"))
rows.append(report(F[(F.lag_me < -10) & (F.vr_me >= 1.0) & (F.vr_me < 1.3)], "lag<-10 vol 1.0-1.3"))
rows.append(report(F[(F.lag_me < -10) & (F.vr_me < 1.0)], "lag<-10 vol<1.0"))
rows.append(report(F[(F.lag_me >= -10) & (F.vr_me >= 1.3)], "lag>=-10 vol>=1.3"))
rows.append(report(F[(F.lag_me.between(-10, -5)) & (F.vr_me >= 1.3)], "lag -10..-5 vol>=1.3"))
rows.append(report(rule(F[F.in_fo == True]), "dummy"))
tab = pd.DataFrame(rows[:-1])
print("\n=== CANDIDATE + NEIGHBOURS (percent, gross; net = -0.17) ===")
print(tab.round(3).to_string(index=False))
tab.to_csv(f"{OUT}/neighbours.csv", index=False)

# also non-F&O events, same rule (out-of-universe check)
NF = E[(E.in_fo == False) & E.y.notna()]
print("\nnon-F&O events same rule:", report(rule(NF), "nonFO"))

print("\n=== per quarter (candidate) ===")
pq = S.groupby(["qn", "quarter"]).agg(n=("y", "size"), mean=("y", "mean"), tp=("tp", "mean"), allfo_mean=("qn", lambda s: F[F.qn == s.iloc[0]].y.mean()))
print(pq.round(2).to_string())
pq.to_csv(f"{OUT}/per_quarter.csv")
S[["symbol", "quarter", "qn", "cutoff", "lag_me", "vr_me", "y", "tp"]].sort_values("cutoff").to_csv(f"{OUT}/trades_rebuilt.csv", index=False)
print("\ntop 8 trades:"); print(S.nlargest(8, "y")[["symbol", "quarter", "cutoff", "lag_me", "vr_me", "y"]].round(2).to_string(index=False))
print("distinct cutoff dates:", S.cutoff.nunique(), "; max trades on one cutoff:", S.cutoff.value_counts().max())
# calendar-week clustering
wk = pd.to_datetime(S.cutoff).dt.to_period("W")
print("distinct cutoff weeks:", wk.nunique(), "; largest week cluster:", wk.value_counts().head(3).to_dict())

# market-adjusted: subtract same-quarter in_fo mean, and subtract Nifty 3-day
S = S.copy()
S["y_ex_q"] = S.y - S.qn.map(F.groupby("qn").y.mean())
nret = np.r_[np.nan, np.diff(nifty) / nifty[:-1] * 100]
S["nifty3"] = nret[S.i_m1] + nret[S.i_rd] + nret[S.i_p1]
print(f"mean minus same-quarter F&O mean: {S.y_ex_q.mean():.3f}; mean minus Nifty 3-day: {(S.y - S.nifty3).mean():.3f}; Nifty 3-day avg in these windows {S.nifty3.mean():.3f}")

# luck
p, rm, p99 = luck(S)
print(f"\nLUCK: random same-size per-quarter picks: mean {rm:.3f}, 99th pct {p99:.3f}, p(>= {S.y.mean():.3f}) = {p:.5f}")
# block bootstrap CI over quarters
qs = S.qn.unique()
bm = []
for _ in range(5000):
    pick = rng.choice(qs, len(qs))
    bm.append(np.concatenate([S[S.qn == q].y.to_numpy() for q in pick]).mean())
print("quarter-cluster bootstrap 95% CI of mean:", np.percentile(bm, [2.5, 97.5]).round(3))

# ---------------- placebo
fo_sym_q = F[["symbol", "i_cut"]]
# in_fo per stock-day: in_fo status of nearest event of that stock (by i_cut)
Eall = E[E.in_fo.notna()].sort_values("i_cut")
FOday = np.zeros((T, N), bool)
blocked = np.zeros((T, N), bool)
for s, g in Eall.groupby("symbol"):
    jj = col[s]
    ic = g.i_cut.to_numpy(); fo = g.in_fo.to_numpy(bool); rd = g.i_rd.to_numpy()
    t = np.arange(T)
    near = np.abs(t[:, None] - ic[None, :]).argmin(1)
    FOday[:, jj] = fo[near]
    # window k+1..k+3 ; block if any result session within 10 sessions of it: rd in [k+1-10, k+3+10]
    for r in rd:
        lo, hi = r - 13, r + 9
        blocked[max(lo, 0):max(hi + 1, 0), jj] = True
first_ev, last_ev = E.i_cut.min(), E.i_cut.max()
ok = np.zeros((T, N), bool); ok[first_ev:last_ev + 1] = True
fwd = np.full((T, N), np.nan)
fwd[:-3] = Rv[1:-2] + Rv[2:-1] + Rv[3:]
PL = ok & FOday & ~blocked & np.isfinite(fwd) & np.isfinite(LAG) & np.isfinite(VR)
sig = PL & (LAG < -10) & (VR >= 1.3)
pt, pk = np.nonzero(sig)
py = fwd[pt, pk]
print(f"\nPLACEBO (non-results F&O stock-days, same window span): all rows {PL.sum()} mean {np.nanmean(fwd[PL]):.3f}; "
      f"signal rows {sig.sum()} mean {py.mean():.3f}")
mon = pd.Series(days[pt]).str[:7].to_numpy()
dfp = pd.DataFrame({"y": py, "m": mon})
mm_ = dfp.groupby("m").y.agg(["sum", "size"])
bs = []
for _ in range(3000):
    pick = mm_.sample(len(mm_), replace=True, random_state=int(rng.integers(1e9)))
    bs.append(pick["sum"].sum() / pick["size"].sum())
print("placebo month-cluster 95% CI:", np.percentile(bs, [2.5, 97.5]).round(3))
# placebo halves by date of 2021-.. split at first qn14 cutoff
split_day = F[F.qn == 14].cutoff.min()
print("placebo first/last split at", split_day, ":", dfp[days[pt] < split_day].y.mean().round(3), dfp[days[pt] >= split_day].y.mean().round(3))
# placebo, de-overlapped: one signal per stock per 5 sessions
o = np.lexsort((pt, pk)); last = {}; keep = []
for i in o:
    if pk[i] in last and pt[i] - last[pk[i]] < 5:
        continue
    last[pk[i]] = pt[i]; keep.append(i)
print(f"placebo de-overlapped (>=5 sessions apart per stock): {len(keep)} rows mean {py[keep].mean():.3f}")
# placebo neighbours
for lag, vol in ((-10, 1.0), (-8, 1.3), (-12, 1.3), (-10, 1.5)):
    s_ = PL & (LAG < lag) & (VR >= vol)
    print(f"  placebo lag<{lag} vol>={vol}: {s_.sum()} rows mean {np.nanmean(fwd[s_]):.3f}")
# events-minus-placebo with bootstrap
diff = S.y.mean() - py.mean()
se_e = np.std(bm); se_p = np.std(bs)
print(f"event mean - placebo mean = {diff:.3f}, z ~ {diff / np.sqrt(se_e**2 + se_p**2):.2f}")
