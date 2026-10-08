"""Independent rebuild (verifier 0): adjusted OHLCV from raw px + returns.csv, textbook indicators, lag & volume,
for every symbol-day. Does NOT read the other agent's panel. Output: panel_mine.parquet-ish csv.gz (symbol, i, ...).
"""
import os  # LAB_ROOT: scratch folder with sector_lab/data, report/nse_prices.db, ta/; REPO_ROOT: this repo
import sqlite3, numpy as np, pandas as pd
B = os.environ.get('LAB_ROOT', 'lab') + ""
DD = f"{B}/sector_lab/data"
OUT = f"{B}/ta/verify_0"

ses = pd.read_csv(f"{DD}/sessions.csv")
R = pd.read_csv(f"{DD}/returns.csv", index_col=0)
assert list(R.index) == list(ses.day)
IX = pd.read_csv(f"{DD}/index_close.csv", index_col=0)
nifty = IX["Nifty 50"].reindex(ses.day).to_numpy()
con = sqlite3.connect(f"{B}/report/nse_prices.db")
px = pd.read_sql("select day,symbol,open,high,low,close,volume from px", con)
ca = pd.read_sql("select * from ca where factor is not null", con)
px = px[px.symbol.isin(R.columns)]
pos = {d: i for i, d in enumerate(ses.day)}
px["i"] = px.day.map(pos)
px = px[px.i.notna()]
px["i"] = px.i.astype(int)
N = len(ses)


def rma(x, n):
    """Wilder smoothing seeded by SMA of first n valid values."""
    out = np.full(len(x), np.nan)
    v = np.flatnonzero(~np.isnan(x))
    if len(v) < n:
        return out
    s = v[0]
    out[s + n - 1] = np.nanmean(x[s:s + n])
    a = 1.0 / n
    for t in range(s + n, len(x)):
        out[t] = out[t - 1] + a * (x[t] - out[t - 1]) if not np.isnan(x[t]) else out[t - 1]
    return out


def rsi(c, n):
    d = np.diff(c, prepend=np.nan)
    g, l = np.where(d > 0, d, 0.0), np.where(d < 0, -d, 0.0)
    g[np.isnan(d)] = np.nan; l[np.isnan(d)] = np.nan
    ag, al = rma(g, n), rma(l, n)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = 100 - 100 / (1 + ag / al)
    r[(al == 0) & (ag > 0)] = 100
    r[(al == 0) & (ag == 0)] = 50
    return r


rows = []
mism = []
for sym in R.columns:
    r = R[sym].to_numpy()
    p = px[px.symbol == sym].set_index("i").sort_index()
    if p.empty:
        continue
    # adjusted close by compounding returns (scale irrelevant for every indicator used)
    rr = np.where(np.isnan(r), 0.0, r)
    ac = np.cumprod(1 + rr)
    raw = p.reindex(range(N))
    rc = raw.close.to_numpy()
    k = rc / ac                      # raw/adjusted ratio; jumps at splits/bonuses (and drifts with dividends)
    ao, ah, al_ = raw.open.to_numpy() / k, raw.high.to_numpy() / k, raw.low.to_numpy() / k
    acl = np.where(np.isnan(rc), np.nan, ac)
    # volume: (a) price-ratio method v * k / k_last ; (b) ca factor method
    vr = raw.volume.to_numpy()
    # correct derivation: after a 1:2 split raw price halves -> k halves -> post-split volume doubles;
    # back-adjust pre-split volume by multiplying with the factor = k_pre / k_post, i.e. v_adj = v * k / k_last.
    kl = k[np.flatnonzero(np.isfinite(k))[-1]]
    v_a = vr * k / kl
    cs = ca[ca.symbol == sym].drop_duplicates(["ex_date", "kind", "factor"])
    fac = np.ones(N)
    for _, c in cs.iterrows():
        if c.ex_date in pos:
            fac[:pos[c.ex_date]] *= c.factor
        else:
            j = np.searchsorted(ses.day.to_numpy(), c.ex_date)
            fac[:j] *= c.factor
    v_b = vr * fac
    d = pd.DataFrame({"i": np.arange(N), "o": ao, "h": ah, "l": al_, "c": acl, "v": v_a, "v_ca": v_b, "r": r})
    d = d[d.c.notna() & d.h.notna()].reset_index(drop=True)
    if len(d) < 80:
        continue
    c, h, l, v = d.c.to_numpy(), d.h.to_numpy(), d.l.to_numpy(), d.v.to_numpy()
    h = np.maximum(h, c); l = np.minimum(l, c)
    o = pd.DataFrame(index=d.index)
    o["symbol"], o["i"] = sym, d.i
    o["c"] = c
    o["rsi14"], o["rsi2"] = rsi(c, 14), rsi(c, 2)
    HH = pd.Series(h).rolling(14).max().to_numpy(); LL = pd.Series(l).rolling(14).min().to_numpy()
    o["stoch"] = np.where(HH > LL, 100 * (c - LL) / (HH - LL), 50)
    m20 = pd.Series(c).rolling(20).mean().to_numpy()
    sdp = pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    sds = pd.Series(c).rolling(20).std(ddof=1).to_numpy()
    o["pctb"] = (c - (m20 - 2 * sdp)) / (4 * sdp)
    o["pctb_s"] = (c - (m20 - 2 * sds)) / (4 * sds)
    tp = (h + l + c) / 3
    tps = pd.Series(tp)
    sma = tps.rolling(20).mean()
    md = tps.rolling(20).apply(lambda w: np.mean(np.abs(w - w.mean())), raw=True)
    o["cci"] = ((tps - sma) / (0.015 * md)).to_numpy()
    mf = tp * v
    dtp = np.diff(tp, prepend=np.nan)
    pos_ = pd.Series(np.where(dtp > 0, mf, 0.0)).rolling(14).sum().to_numpy()
    neg_ = pd.Series(np.where(dtp < 0, mf, 0.0)).rolling(14).sum().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        o["mfi"] = np.where(neg_ > 0, 100 - 100 / (1 + pos_ / neg_), 100.0)
    o.loc[np.arange(len(o)) < 14, "mfi"] = np.nan
    # lag vs Nifty (21 sessions, on session index, compounding returns)
    ii = d.i.to_numpy()
    cfull = np.full(N, np.nan); cfull[ii] = c
    rr_full = np.cumprod(1 + rr)
    s21 = rr_full[ii] / rr_full[np.maximum(ii - 21, 0)] - 1
    n21 = nifty[ii] / nifty[np.maximum(ii - 21, 0)] - 1
    o["lag_pct"] = 100 * (s21 - n21)
    vf = np.full(N, np.nan); vf[ii] = v
    vcf = np.full(N, np.nan); vcf[ii] = d.v_ca.to_numpy()
    V = pd.Series(vf); Vc = pd.Series(vcf)
    o["vol"] = (V.rolling(5, min_periods=1).mean() / V.rolling(60, min_periods=1).mean()).to_numpy()[ii]
    o["vol_ca"] = (Vc.rolling(5, min_periods=1).mean() / Vc.rolling(60, min_periods=1).mean()).to_numpy()[ii]
    # forward 3-day sum of returns (placebo outcome)
    rf = np.where(np.isnan(r), np.nan, r)
    f3 = pd.Series(rf).rolling(3).sum().shift(-3).to_numpy()
    o["fwd3"] = 100 * f3[ii]
    rows.append(o)

P = pd.concat(rows, ignore_index=True)
P.to_csv(f"{OUT}/panel_mine.csv.gz", index=False, float_format="%.6g")
print(P.shape)
print(P.describe().T[["count", "mean", "min", "max"]])
