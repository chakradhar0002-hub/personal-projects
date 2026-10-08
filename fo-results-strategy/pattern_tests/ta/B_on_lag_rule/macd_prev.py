"""C9 helper: MACD histogram at k and at the previous traded day, from ../build/adjusted_ohlcv.csv.gz, using
build_panel.py's exact EMA definition (seed = simple mean of the first n values). Verified against the panel's
macd_hist_pct at k. Uses no outcome columns. Writes macd_prev.csv.gz (symbol, day, macd_hist_rising)."""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(os.path.dirname(HERE), "build")


def seeded(x, n, alpha, start):
    out = np.full(len(x), np.nan)
    if len(x) - start < n:
        return out
    y = x[start + n - 1:].astype(float).copy()
    y[0] = x[start:start + n].mean()
    out[start + n - 1:] = np.array(pd.Series(y).ewm(alpha=alpha, adjust=False).mean(), dtype=float)
    return out


a = pd.read_csv(f"{BUILD}/adjusted_ohlcv.csv.gz", usecols=["day", "symbol", "close"])
a = a[np.isfinite(a.close)].sort_values(["symbol", "day"]).reset_index(drop=True)
parts = []
for s, g in a.groupby("symbol", sort=False):
    c = g.close.to_numpy(float)
    macd = seeded(c, 12, 2 / 13, 0) - seeded(c, 26, 2 / 27, 0)
    sig = seeded(macd, 9, 0.2, 25)
    hist = macd - sig
    prev = np.r_[np.nan, hist[:-1]]
    parts.append(pd.DataFrame({"symbol": s, "day": g.day.to_numpy(), "hist_pct_chk": hist / c * 100,
                               "macd_hist_rising": np.where(np.isnan(hist) | np.isnan(prev), np.nan,
                                                            (hist > prev).astype(float))}))
M = pd.concat(parts, ignore_index=True)

e = pd.read_csv(f"{BUILD}/events_ta.csv", usecols=["symbol", "cutoff", "macd_hist_pct", "in_fo"])
e = e.merge(M, left_on=["symbol", "cutoff"], right_on=["symbol", "day"], how="left")
d = (e.hist_pct_chk - e.macd_hist_pct).abs()
print("events: rows", len(e), "matched", e.hist_pct_chk.notna().sum(), "max |diff| vs panel macd_hist_pct", d.max(),
      "max rel diff", (d / e.macd_hist_pct.abs().clip(lower=1e-3)).max(),
      "| in_fo rows unmatched:", (e.in_fo == True).sum() - e.loc[e.in_fo == True, "hist_pct_chk"].notna().sum())
p = pd.read_csv(f"{BUILD}/placebo_ta.csv.gz", usecols=["symbol", "day", "macd_hist_pct"])
p = p.merge(M, on=["symbol", "day"], how="left")
d = (p.hist_pct_chk - p.macd_hist_pct).abs()
print("placebo: rows", len(p), "matched", p.hist_pct_chk.notna().sum(), "max |diff|", d.max())
print("rising share events in_fo:", e.loc[e.in_fo == True, "macd_hist_rising"].mean(), " placebo:", p.macd_hist_rising.mean())
M[["symbol", "day", "macd_hist_rising"]].to_csv(f"{HERE}/macd_prev.csv.gz", index=False)
