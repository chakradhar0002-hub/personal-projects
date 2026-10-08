import os  # LAB_ROOT: scratch folder with sector_lab/data, report/nse_prices.db, ta/; REPO_ROOT: this repo
import numpy as np, pandas as pd, sys
B = os.environ.get('LAB_ROOT', 'lab') + ""
OUT = f"{B}/ta/verify_0"
REPO = os.environ.get('REPO_ROOT', '.') + "/results/lag10_volume"
COST = 0.17
rng = np.random.default_rng(12345)
pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_rows", 300)

P = pd.read_csv(f"{OUT}/panel_mine.csv.gz")
E = pd.read_csv(f"{B}/sector_lab/data/events.csv")
E = E[(E.in_fo == True) & E.three_day.notna()].copy()
E["td"] = 100 * E.three_day
a, b = E.ret_dm1, E.ret_dm1 + E.ret_rd
E["tp"] = 100 * np.where(a > 0.03, a, np.where(b > 0.03, b, E.three_day))
E = E.merge(P, left_on=["symbol", "i_cut"], right_on=["symbol", "i"], how="left")
print("events", len(E), "missing indicators:", E.rsi14.isna().sum(), E.mfi.isna().sum(), E.cci.isna().sum())


def flags(d, rsi=30, rsi2=10, st=20, pb=0.0, cci=-100, mfi=20, pbcol="pctb"):
    return np.column_stack([d.rsi14 < rsi, d.rsi2 < rsi2, d.stoch < st, d[pbcol] < pb, d.cci < cci, d.mfi < mfi])


# ---------------------------------------------------------------- 1. reproduce base sets and the candidate
for nm, th, f in (("S85", 1.0, "trades.csv"), ("S44", 1.3, "trades_vol13.csv")):
    m = (E.lag_pct < -10) & (E.vol >= th)
    mc = (E.lag_pct < -10) & (E.vol_ca >= th)
    ref = pd.read_csv(f"{REPO}/{f}")
    k1, k2, k3 = set(zip(E[m].symbol, E[m].quarter)), set(zip(ref.symbol, ref.quarter)), set(zip(E[mc].symbol, E[mc].quarter))
    print(f"{nm}: mine {m.sum()} (ca-factor vol {mc.sum()}), repo {len(ref)}, same {k1 == k2}, ca-version same {k3 == k2}, "
          f"only mine {sorted(k1 - k2)}, only repo {sorted(k2 - k1)}")
    j = E[m].merge(ref, on=["symbol", "quarter"])
    print("   max |lag diff| pp", np.abs(j.lag_pct - 100 * j.vs_nifty_1m).max().round(4),
          " max |vol diff|", np.abs(j.vol - j.volume_ratio).max().round(4),
          " max |tp diff|", np.abs(j.tp - 100 * j.take_profit).max().round(4))

S44 = ((E.lag_pct < -10) & (E.vol >= 1.3)).to_numpy()
S85 = ((E.lag_pct < -10) & (E.vol >= 1.0)).to_numpy()
F = flags(E)
cnt = F.sum(1)
cand = S44 & (cnt >= 3)

# compare with the other agent's panel flags on the 85 trades
T = pd.read_csv(f"{B}/ta/B_on_lag_rule/trades_S85_with_ta.csv")
print("their S85 file cols:", [c for c in T.columns][:60])
x = E[S85].merge(T, on=["symbol", "quarter"], suffixes=("", "_t"))
for mine, th in (("rsi14", "rsi14"), ("rsi2", "rsi2"), ("stoch", "stoch_k14"), ("pctb", "bb_pctb"), ("cci", "cci20"), ("mfi", "mfi14")):
    if th in x:
        print(f"   {mine:6s} vs theirs: max abs diff {np.abs(x[mine] - x[th]).max():.3f}, median {np.abs(x[mine] - x[th]).median():.4f}")


def stats(mask, label, y=None):
    d = E[mask]
    y = d.td.to_numpy()
    q = d.qn.to_numpy()
    qm = pd.Series(y).groupby(q).mean()
    ys = np.sort(y)
    bq = qm.idxmax() if len(qm) else None
    r = dict(rule=label, n=len(y), mean=y.mean(), net=y.mean() - COST, tp=d.tp.mean(), tp_net=d.tp.mean() - COST,
             up=100 * (y > 0).mean(), qpos=f"{(qm > 0).sum()}/{len(qm)}",
             n14=(q <= 13).sum(), f14=y[q <= 13].mean() if (q <= 13).any() else np.nan,
             n8=(q >= 14).sum(), l8=y[q >= 14].mean() if (q >= 14).any() else np.nan,
             xb5=ys[:-5].mean() if len(y) > 5 else np.nan,
             x_bestq=y[q != bq].mean() if len(qm) > 1 else np.nan,
             median=np.median(y))
    return r


print("\n=== candidate rebuilt (my indicators) ===")
r = stats(cand, "S44 & oversold>=3 (mine)")
print(pd.DataFrame([r]).round(3).to_string(index=False))
d = E[cand]
print(d.groupby("qn").td.agg(["size", "mean"]).round(2).T.to_string())
theirs = set(zip(T.symbol, T.quarter)) if "symbol" in T else set()
print("candidate trades:")
print(d[["symbol", "quarter", "qn", "lag_pct", "vol", "rsi14", "rsi2", "stoch", "pctb", "cci", "mfi", "td", "tp"]].round(2).to_string(index=False))

# leave-one-quarter-out
loq = []
for q in sorted(d.qn.unique()):
    loq.append(d[d.qn != q].td.mean())
print(f"leave-one-quarter-out mean: min {min(loq):.2f} max {max(loq):.2f}")
# drop best 5 & best quarter
print(f"without best 5: {r['xb5']:.2f}; without best quarter: {r['x_bestq']:.2f}; median {r['median']:.2f}")

# ---------------------------------------------------------------- 2. neighbours
print("\n=== neighbouring thresholds (all on in_fo results events) ===")
res = []
base_specs = {"S85 (vol>=1.0)": S85, "S44 (vol>=1.3)": S44, "vol 1.0-1.3": S85 & ~S44,
              "lag<-10 vol>=1.2": ((E.lag_pct < -10) & (E.vol >= 1.2)).to_numpy(),
              "lag<-10 vol>=1.5": ((E.lag_pct < -10) & (E.vol >= 1.5)).to_numpy(),
              "lag<-8 vol>=1.3": ((E.lag_pct < -8) & (E.vol >= 1.3)).to_numpy(),
              "lag<-12 vol>=1.3": ((E.lag_pct < -12) & (E.vol >= 1.3)).to_numpy(),
              "lag<-10 any vol": (E.lag_pct < -10).to_numpy(),
              "lag<-10 vol<1.0": ((E.lag_pct < -10) & (E.vol < 1.0)).to_numpy(),
              "ALL in_fo": np.ones(len(E), bool)}
th_specs = {"textbook": {}, "loose (RSI35,RSI2 15,St25,%B.05,CCI-80,MFI25)": dict(rsi=35, rsi2=15, st=25, pb=0.05, cci=-80, mfi=25),
            "strict (RSI25,RSI2 5,St15,%B-.05,CCI-120,MFI15)": dict(rsi=25, rsi2=5, st=15, pb=-0.05, cci=-120, mfi=15),
            "sample-sd Bollinger": dict(pbcol="pctb_s")}
for bn, bm in base_specs.items():
    for tn, kw in th_specs.items():
        c = flags(E, **kw).sum(1)
        for k in (2, 3, 4):
            if tn != "textbook" and k != 3:
                continue
            m1, m0 = bm & (c >= k), bm & (c < k)
            if m1.sum() == 0:
                continue
            res.append(dict(base=bn, thr=tn, k=k, nT=m1.sum(), meanT=E.td[m1].mean(), nF=m0.sum(),
                            meanF=E.td[m0].mean() if m0.any() else np.nan))
NB = pd.DataFrame(res)
NB["D"] = NB.meanT - NB.meanF
print(NB.round(2).to_string(index=False))

# single indicators, neighbours, on S44 and S85
print("\n=== single indicators on S44 / S85 / vol 1.0-1.3 (T mean / F mean) ===")
single = [("RSI14<25", E.rsi14 < 25), ("RSI14<30", E.rsi14 < 30), ("RSI14<35", E.rsi14 < 35),
          ("RSI2<5", E.rsi2 < 5), ("RSI2<10", E.rsi2 < 10), ("RSI2<15", E.rsi2 < 15),
          ("St<15", E.stoch < 15), ("St<20", E.stoch < 20), ("St<25", E.stoch < 25),
          ("%B<0", E.pctb < 0), ("%B<0.05", E.pctb < .05), ("CCI<-80", E.cci < -80), ("CCI<-100", E.cci < -100),
          ("CCI<-150", E.cci < -150), ("MFI<15", E.mfi < 15), ("MFI<20", E.mfi < 20), ("MFI<25", E.mfi < 25), ("MFI<30", E.mfi < 30)]
o = []
for nm, f in single:
    f = f.to_numpy()
    row = {"cond": nm}
    for bn in ("S44 (vol>=1.3)", "S85 (vol>=1.0)", "vol 1.0-1.3"):
        bm = base_specs[bn]
        row[bn[:3] + "_nT"] = (bm & f).sum()
        row[bn[:3] + "_T"] = E.td[bm & f].mean()
        row[bn[:3] + "_F"] = E.td[bm & ~f].mean()
    o.append(row)
print(pd.DataFrame(o).round(2).to_string(index=False))

# ---------------------------------------------------------------- 3. within-S44 permutation, luck vs random picks
y44, q44, l44 = E.td[S44].to_numpy(), E.qn[S44].to_numpy(), cand[S44]
NP = 20000


def within_perm(y, q, lab):
    D = y[lab].mean() - y[~lab].mean()
    o = np.argsort(q, kind="stable"); y, q, lab = y[o], q[o], lab[o]
    idx = np.argsort(q[None, :] + rng.random((NP, len(y))), axis=1)
    L = lab[idx]; nT = L.sum(1); sT = (L * y).sum(1)
    Dp = sT / nT - (y.sum() - sT) / (len(y) - nT)
    return D, (np.sum(Dp >= D - 1e-12) + 1) / (NP + 1), (np.sum(np.abs(Dp) >= abs(D) - 1e-12) + 1) / (NP + 1)


D, p1, p2 = within_perm(y44, q44, l44)
print(f"\nwithin-S44 within-quarter permutation: D={D:.2f}, one-sided p={p1:.4f}, two-sided p={p2:.4f}")
D, p1, p2 = within_perm(E.td[S85].to_numpy(), E.qn[S85].to_numpy(), (cnt >= 3)[S85])
print(f"within-S85: D={D:.2f}, one-sided p={p1:.4f}, two-sided p={p2:.4f}")
mid = S85 & ~S44
D, p1, p2 = within_perm(E.td[mid].to_numpy(), E.qn[mid].to_numpy(), (cnt >= 3)[mid])
print(f"within vol 1.0-1.3 slice: D={D:.2f}, one-sided p={p1:.4f}, two-sided p={p2:.4f}")

# random same-size per-quarter picks from (a) all in_fo events (b) the S44 set
Y, QA = E.td.to_numpy(), E.qn.to_numpy()


def luck(mask, pool):
    obs = Y[mask].mean(); tot = np.zeros(NP); n = 0
    for q in np.unique(QA[mask]):
        idx = np.flatnonzero(pool & (QA == q)); k = int((mask & (QA == q)).sum())
        if len(idx) < k:
            return np.nan
        tot += Y[idx][np.argsort(rng.random((NP, len(idx))), axis=1)[:, :k]].sum(1); n += k
    return (np.sum(tot / n >= obs - 1e-12) + 1) / (NP + 1)


print(f"luck vs random same-size per-quarter picks from ALL in_fo events: p={luck(cand, np.ones(len(E), bool)):.5f}")
print(f"luck vs random same-size per-quarter picks from S44 itself: p={luck(cand, S44):.4f}")
print(f"luck vs random picks from S85: p={luck(cand, S85):.4f}")

# ---------------------------------------------------------------- 4. placebo on non-results days
ev_all = pd.read_csv(f"{B}/sector_lab/data/events.csv")
fo = ev_all.groupby("symbol").in_fo.agg(lambda s: s.mean())
# in_fo of a stock-day: in_fo flag of the symbol's nearest event (by session index)
Pp = P.copy()
ev_s = ev_all[["symbol", "i_rd", "in_fo"]].dropna().sort_values("i_rd")
Pp = Pp.sort_values("i")
Pp["i_rd_f"] = Pp.i.astype(float)
near = pd.merge_asof(Pp.sort_values("i_rd_f"), ev_s.assign(i_rd=ev_s.i_rd.astype(float)).sort_values("i_rd"),
                     left_on="i_rd_f", right_on="i_rd", by="symbol", direction="nearest")
Pp = near
# exclude any day whose window k+1..k+3 has a result session within 10 sessions
excl = np.zeros(len(Pp), bool)
rd = ev_all.groupby("symbol").i_rd.apply(lambda s: np.sort(s.dropna().to_numpy()))
for sym, g in Pp.groupby("symbol"):
    arr = rd.get(sym, np.array([]))
    if len(arr) == 0:
        continue
    k = g.i.to_numpy()
    lo = np.searchsorted(arr, k + 1 - 10, "left"); hi = np.searchsorted(arr, k + 3 + 10, "right")
    excl[g.index.to_numpy()] = hi > lo
Pp = Pp[~excl & (Pp.in_fo == True) & Pp.fwd3.notna() & Pp.rsi14.notna() & Pp.mfi.notna() & Pp.cci.notna()]
Pp = Pp[Pp.i >= E.i_cut.min() - 5]
print(f"\nplacebo rows: {len(Pp)}, mean fwd3 {Pp.fwd3.mean():.3f}")
FP = flags(Pp).sum(1)
pb44 = ((Pp.lag_pct < -10) & (Pp.vol >= 1.3)).to_numpy()
pb85 = ((Pp.lag_pct < -10) & (Pp.vol >= 1.0)).to_numpy()
month = pd.read_csv(f"{B}/sector_lab/data/sessions.csv").day.str[:7].to_numpy()[Pp.i.to_numpy()]


def boot(mask):
    y = Pp.fwd3.to_numpy()[mask]; cl = month[mask]
    codes, u = pd.factorize(cl); K = len(u)
    s = np.bincount(codes, weights=y, minlength=K); n = np.bincount(codes, minlength=K).astype(float)
    W = rng.multinomial(K, np.full(K, 1 / K), size=2000)
    bb = (W @ s) / (W @ n)
    return mask.sum(), y.mean(), np.percentile(bb, 2.5), np.percentile(bb, 97.5)


for nm, m in (("placebo S44 & oversold>=3", pb44 & (FP >= 3)), ("placebo S44 & oversold<3", pb44 & (FP < 3)),
              ("placebo S44", pb44), ("placebo S85 & os>=3", pb85 & (FP >= 3)), ("placebo S85 & os<3", pb85 & (FP < 3)),
              ("placebo all os>=3 (no lag)", FP >= 3)):
    n, mu, lo, hi = boot(m)
    print(f"{nm:30s} n={n:6d} mean={mu:+.3f} [{lo:+.2f}, {hi:+.2f}]")
