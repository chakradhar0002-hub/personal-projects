"""Verify candidate: lag10+volume AND Nifty-adjusted mcap >= 67,000 cr (3-day results window)."""
import os  # LAB_ROOT: scratch folder with report/, search22/, sector_lab/data, fa/; REPO_ROOT: this repo
import numpy as np
import pandas as pd

DATA = os.environ.get('LAB_ROOT', 'lab') + ""
HERE = DATA + "/fa/verify_0"
REPO = os.environ.get('REPO_ROOT', '.') + ""
COST = 0.17
rng = np.random.default_rng(12345)
R = 20000

mc = pd.read_csv(f"{HERE}/mcap_pit.csv")
mc["adj_a"] = mc.mcap_a * 21700 / mc.nifty
mc["adj_b"] = mc.mcap_b * 21700 / mc.nifty
ex = pd.read_csv(f"{DATA}/fa/A_pre_results/out/extra_features.csv")
pan = pd.read_csv(f"{DATA}/fa/build/fa_panel.csv", usecols=["symbol", "quarter", "mcap_cr", "in_fo", "three_day", "tp3"])

# rank of mcap among all in_fo results-events within the same quarter (size rank in F&O universe)
sl = pd.read_csv(f"{DATA}/sector_lab/data/events.csv", usecols=["symbol", "quarter", "in_fo"])
mc = mc.merge(sl, on=["symbol", "quarter"], how="left")


def stats(df, label, col="ret"):
    y = df[col].to_numpy()
    if len(y) == 0:
        print(label, "no trades"); return
    pq = df.groupby("qn")[col].mean()
    s = np.sort(y)
    wob5 = s[:-5].mean() if len(y) > 5 else np.nan
    bestq = pq.idxmax()
    wobq = df[df.qn != bestq][col].mean()
    f14 = df[df.qn <= 13][col].mean(); l8 = df[df.qn >= 14][col].mean()
    print(f"{label:46s} n={len(y):3d} avg={y.mean():+.2f} net={y.mean()-COST:+.2f} up%={100*(y>0).mean():.0f} "
          f"q+={int((pq>0).sum())}/{len(pq)} f14={f14:+.2f}({(df.qn<=13).sum()}) l8={l8:+.2f}({(df.qn>=14).sum()}) "
          f"woBest5={wob5:+.2f} woBestQ={wobq:+.2f} tp={df.tp.mean():+.2f}")


for fname in ("trades.csv", "trades_vol13.csv"):
    tr = pd.read_csv(f"{REPO}/results/lag10_volume/{fname}")
    tr["ret"] = 100 * tr.three_day
    tr["tp"] = 100 * tr.take_profit
    t = tr.merge(mc[["symbol", "quarter", "mcap_a", "mcap_b", "adj_a", "adj_b", "nifty", "lag", "filing_q", "filing_pub", "shares_fixed"]],
                 on=["symbol", "quarter"], how="left")
    t = t.merge(ex[["symbol", "quarter", "mcap_adj_cr"]], on=["symbol", "quarter"], how="left")
    t = t.merge(pan[["symbol", "quarter", "mcap_cr"]], on=["symbol", "quarter"], how="left")
    print("=" * 30, fname, len(t))
    rel = (t.adj_a / t.mcap_adj_cr - 1).abs()
    print("mine(a) vs panel mcap_adj: max rel diff", rel.max(), "n>1%:", (rel > 0.01).sum(), " missing mine:", t.adj_a.isna().sum(),
          "missing panel:", t.mcap_adj_cr.isna().sum())
    relb = (t.adj_b / t.adj_a - 1).abs()
    print("variant b (raw filing shares) vs a: n>5% diff", (relb > 0.05).sum())
    print(t.loc[relb > 0.05, ["symbol", "quarter", "adj_a", "adj_b", "shares_fixed"]].to_string())
    print("filing published before cutoff in all:", (t.filing_pub < t.cutoff).all(), " lag dist", t.lag.value_counts().to_dict())
    flagA = t.adj_a >= 67000; flagP = t.mcap_adj_cr >= 67000
    print("flag disagreements mine vs panel:", (flagA != flagP).sum())
    print(t.loc[(t.adj_a > 50000) & (t.adj_a < 90000), ["symbol", "quarter", "adj_a", "mcap_adj_cr", "ret"]].sort_values("adj_a").to_string())
    stats(t, "ALL lag10 trades")
    stats(t[flagA], "large adj>=67k (mine)")
    stats(t[~flagA], "not large")
    # neighbouring cut-offs
    for thr in (40000, 50000, 60000, 67000, 75000, 85000, 100000, 150000):
        stats(t[t.adj_a >= thr], f"adj mcap >= {thr}")
    for thr in (50000, 67000, 100000):
        stats(t[t.mcap_a >= thr], f"UNADJUSTED mcap >= {thr}")
    # within-quarter rank among all in_fo results that quarter (top 100 of F&O ~ 'large')
    u = mc[mc.in_fo == True].copy()
    u["rk"] = u.groupby("qn").mcap_a.rank(ascending=False)
    u["nq"] = u.groupby("qn").mcap_a.transform("count")
    u["pct"] = u.rk / u.nq
    t2 = t.merge(u[["symbol", "quarter", "rk", "pct"]], on=["symbol", "quarter"], how="left")
    for p in (0.33, 0.5, 0.67):
        stats(t2[t2.pct <= p], f"top {int(p*100)}% mcap of in_fo that quarter")
    med = t.adj_a.median()
    stats(t[t.adj_a >= med], f"above median of trades ({med:,.0f})")
    from scipy.stats import spearmanr
    print("spearman log mcap vs ret:", spearmanr(t.adj_a, t.ret, nan_policy="omit"))
    if fname != "trades.csv":
        continue
    L = t[flagA]
    # per-quarter
    pq = t.assign(large=flagA).groupby(["qn", "large"]).ret.agg(["count", "mean"]).unstack()
    print(pq.round(2).to_string())
    # leave one quarter out
    lo = [(q, L[L.qn != q].ret.mean(), t[(~flagA) & (t.qn != q)].ret.mean()) for q in sorted(t.qn.unique())]
    print("LOQO large avg range", min(x[1] for x in lo), max(x[1] for x in lo), " diff range",
          min(x[1] - x[2] for x in lo), max(x[1] - x[2] for x in lo))
    # luck 1: random same-size per-quarter picks from the lag10 trades (within-quarter shuffle)
    y = t.ret.to_numpy(); q = t.qn.to_numpy(); f = flagA.to_numpy()
    obs = y[f].mean() - y[~f].mean()
    sims = np.empty(R); simm = np.empty(R)
    groups = [np.where(q == k)[0] for k in np.unique(q)]
    for r in range(R):
        ff = np.zeros(len(y), bool)
        for g in groups:
            ff[rng.choice(g, f[g].sum(), replace=False)] = True
        sims[r] = y[ff].mean() - y[~ff].mean(); simm[r] = y[ff].mean()
    print(f"within-quarter shuffle: obs diff {obs:+.2f} p2={np.mean(np.abs(sims) >= abs(obs)):.3f} ; obs large mean {y[f].mean():+.2f} "
          f"p(mean>=)={np.mean(simm >= y[f].mean()):.3f}")
    # luck 2: random same-size per-quarter picks from ALL in_fo results (is large-lag10 better than random in_fo picks?)
    allr = pd.read_csv(f"{DATA}/sector_lab/data/events.csv", usecols=["symbol", "quarter", "qn", "in_fo", "three_day"])
    allr = allr[(allr.in_fo == True) & allr.three_day.notna()]
    allr["ret"] = 100 * allr.three_day
    pools = {k: g.ret.to_numpy() for k, g in allr.groupby("qn")}
    cnt = L.groupby("qn").size()
    sm = np.empty(R)
    for r in range(R):
        sm[r] = np.concatenate([rng.choice(pools[k], n, replace=False) for k, n in cnt.items()]).mean()
    print(f"large-lag10 {L.ret.mean():+.2f} vs random in_fo picks mean {sm.mean():+.2f}; p(>=)={np.mean(sm >= L.ret.mean()):.4f}")
    # large in_fo baseline in the same quarters
    allr = allr.merge(mc[["symbol", "quarter", "adj_a"]], on=["symbol", "quarter"], how="left")
    lg = allr[allr.adj_a >= 67000]
    base = sum(lg[lg.qn == k].ret.mean() * n for k, n in cnt.items()) / cnt.sum()
    print(f"all large in_fo results, same-quarter weighted baseline {base:+.2f}; all large overall {lg.ret.mean():+.2f}, "
          f"not large overall {allr[allr.adj_a < 67000].ret.mean():+.2f}")
    # placebo: same large-lag10 picks... use price-type placebo: lag10+vol is price; large filter on random non-results day not
    # needed for fundamentals; instead 'large' vs 'not large' among ALL in_fo results per quarter:
    d = allr.assign(large=allr.adj_a >= 67000).groupby(["qn", "large"]).ret.mean().unstack()
    print("all in_fo: per-quarter large minus not-large: mean", (d[True] - d[False]).mean().round(3), "pos q", int(((d[True] - d[False]) > 0).sum()), "/", len(d))
    # bootstrap of the large-lag10 mean by quarter clusters
    qs = L.qn.unique(); bm = []
    for r in range(5000):
        pick = rng.choice(qs, len(qs), replace=True)
        bm.append(pd.concat([L[L.qn == k] for k in pick]).ret.mean())
    print("quarter-cluster bootstrap 90% CI of large-lag10 mean:", np.percentile(bm, [5, 50, 95]).round(2))
    L.to_csv(f"{HERE}/large_trades_mine.csv", index=False)
