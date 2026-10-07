"""Sector performance before results -> the stock's three-day results window.

Sector = the Nifty sector index matched to the stock's industry (results mapped to the Nifty 500 fallback are left
out). All measured at the cutoff (2 sessions before the result session). Pre-registered tests; rules are judged on the
first 14 quarters and checked on the last 8. Also writes a sector-only feature file for search22.py.

Caution: bucket_test ranks each stock against stocks reporting later in the same quarter, whose trailing returns already
include its three-day window. For trailing-price measures this is biased negative (random price paths give about -0.5%
to -0.9%); see docs/TARGET_2PCT.md, "Sector performance before results", for the corrected checks.

    python3 sector.py DATA features22.csv OUT_DIR
"""
import csv, json, math, statistics, sys
from pathlib import Path

RB = Path(__file__).resolve().parents[1] / "report_builder"
DATA, FEAT, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
sys.argv = [sys.argv[0], DATA]
__file__ = str(RB / "analyze_events.py")
exec(open(RB / "analyze_events.py").read().split("# ---------------------------------------------------------------- options")[0])
import numpy as np
import pandas as pd

SECTORS = ["Nifty Bank", "Nifty IT", "Nifty Pharma", "Nifty FMCG", "Nifty Auto", "Nifty Metal", "Nifty Realty", "Nifty Energy",
           "Nifty Financial Services", "Nifty Media", "Nifty PSU Bank", "Nifty Private Bank", "Nifty Oil & Gas",
           "Nifty Healthcare Index", "Nifty Consumer Durables", "Nifty Commodities", "Nifty Infrastructure",
           "Nifty India Consumption", "Nifty Services Sector", "Nifty India Manufacturing"]
IDX = {}
for name in set(SECTORS) | {"Nifty 50", "Nifty India Defence", "Nifty India Digital"}:
    rows = sorted((day, v[0]) for day, v in indexes.get(name, {}).items() if v[0])
    IDX[name] = ([r[0] for r in rows], [r[1] for r in rows])


def level(name, day, back=0):
    """Index close `back` index-days before the last close on or before `day`."""
    days, vals = IDX[name]
    j = bisect_right(days, day) - 1 - back
    return vals[j] if j >= 0 else None


def ret(name, day, n):
    a, b = level(name, day, n), level(name, day)
    return b / a - 1 if a and b else None


d = pd.read_csv(FEAT)
ev = {(r["symbol"], r["quarter"]): r for r in json.load(open(f"{DATA}/report/events.json"))}
d["sector_index"] = [ev[(s, q)]["sector_index"] for s, q in zip(d.symbol, d.quarter)]
d["day_p1"] = [ev[(s, q)]["day_p1"] for s, q in zip(d.symbol, d.quarter)]
d = d[d.sector_index != "Nifty 500"].copy()

feats = defaultdict(list)
for sec, cut in zip(d.sector_index, d.cutoff):
    r1m = {s: ret(s, cut, 21) for s in SECTORS}
    r3m = {s: ret(s, cut, 63) for s in SECTORS}
    ok1 = sorted(v for v in r1m.values() if v is not None)
    ok3 = sorted(v for v in r3m.values() if v is not None)
    s1, s3 = ret(sec, cut, 21), ret(sec, cut, 63)
    n1, n3 = ret("Nifty 50", cut, 21), ret("Nifty 50", cut, 63)
    feats["sec_1w"].append(ret(sec, cut, 5))
    feats["sec_1m"].append(s1)
    feats["sec_3m"].append(s3)
    feats["sec_vs_nifty_1w"].append(ret(sec, cut, 5) - ret("Nifty 50", cut, 5) if ret(sec, cut, 5) is not None else None)
    feats["sec_vs_nifty_1m"].append(s1 - n1 if s1 is not None and n1 is not None else None)
    feats["sec_vs_nifty_3m"].append(s3 - n3 if s3 is not None and n3 is not None else None)
    feats["sec_rank_1m"].append(bisect_left(ok1, s1) / (len(ok1) - 1) if s1 is not None and len(ok1) > 5 else None)   # 1 = best sector
    feats["sec_rank_3m"].append(bisect_left(ok3, s3) / (len(ok3) - 1) if s3 is not None and len(ok3) > 5 else None)
    days, vals = IDX[sec]
    j = bisect_right(days, cut) - 1
    w50, w200, w250 = vals[max(0, j - 49):j + 1], vals[max(0, j - 199):j + 1], vals[max(0, j - 249):j + 1]
    feats["sec_vs_50dma"].append(vals[j] / statistics.mean(w50) - 1 if len(w50) == 50 else None)
    feats["sec_vs_200dma"].append(vals[j] / statistics.mean(w200) - 1 if len(w200) == 200 else None)
    feats["sec_from_52w_high"].append(vals[j] / max(w250) - 1 if len(w250) > 200 else None)
for k, v in feats.items():
    d[k] = v
# this season so far: stocks in the same sector index whose Day+1 closed on or before this cutoff
season = defaultdict(list)
for sec, q, dp1, t in zip(d.sector_index, d.quarter, d.day_p1, d.three_day):
    season[(sec, q)].append((dp1, t))
d["sec_reported_3d"] = [np.mean([t for dp1, t in season[(s, q)] if dp1 <= c]) if any(dp1 <= c for dp1, _ in season[(s, q)]) else np.nan
                        for s, q, c in zip(d.sector_index, d.quarter, d.cutoff)]
d["sec_reported_n"] = [sum(dp1 <= c for dp1, _ in season[(s, q)]) for s, q, c in zip(d.sector_index, d.quarter, d.cutoff)]
d.loc[d.sec_reported_n < 3, "sec_reported_3d"] = np.nan
d["stock_vs_sec_1m"], d["stock_vs_sec_1w"] = d["vs_sector_1m"], d["vs_sector_1w"]
d["peers_reported_3d"] = d["peers_reported_3d"]

qavg = d.groupby("qn")["three_day"].mean()
TRAIN = 14


def tstat(s):
    s = pd.Series(s).dropna()
    return s.mean() / s.std(ddof=1) * math.sqrt(len(s)) if len(s) > 2 else float("nan")


def bucket_test(name, col, desc):
    x = d[d[col].notna()]
    out = []
    for q, g in x.groupby("qn"):
        if len(g) < 15:
            continue
        lo, hi = g[col].quantile(1 / 3), g[col].quantile(2 / 3)
        top, bot = g[g[col] >= hi].three_day.mean(), g[g[col] <= lo].three_day.mean()
        out.append((q, top, bot, top - bot, g[col].rank().corr(g.three_day.rank())))
    o = pd.DataFrame(out, columns=["qn", "top", "bot", "spread", "ic"])
    tr, te = o[o.qn < TRAIN], o[o.qn >= TRAIN]
    return {"test": name, "what": desc, "quarters": len(o), "top_third_avg": o.top.mean(), "bottom_third_avg": o.bot.mean(),
            "spread": o.spread.mean(), "spread_t": tstat(o.spread), "ic": o.ic.mean(), "ic_t": tstat(o.ic),
            "spread_first14": tr.spread.mean(), "spread_last8": te.spread.mean(),
            "top_quarters_ge_2pct": int((o.top >= 0.02).sum()), "bottom_quarters_ge_2pct": int((o.bot >= 0.02).sum())}


def rule_test(name, mask, desc):
    x = d[mask]
    pq = x.groupby("qn").three_day.mean().reindex(range(22))
    ex = (pq - qavg).dropna()
    return {"test": name, "what": desc, "picks": len(x), "avg_3day": x.three_day.mean(), "pct_up": (x.three_day > 0).mean(),
            "avg_tp3": x.tp3.mean(), "quarters_ge_2pct": int((pq >= 0.02).sum()), "quarters_pos": int((pq > 0).sum()),
            "no_pick_quarters": int(pq.isna().sum()), "vs_all": ex.mean(), "vs_all_t": tstat(ex),
            "first14": pq.iloc[:TRAIN].mean(), "last8": pq.iloc[TRAIN:].mean()}


B = [bucket_test("S1", "sec_1w", "Sector index 1-week return"),
     bucket_test("S2", "sec_1m", "Sector index 1-month return"),
     bucket_test("S3", "sec_3m", "Sector index 3-month return"),
     bucket_test("S4", "sec_vs_nifty_1m", "Sector vs Nifty, 1 month"),
     bucket_test("S5", "sec_vs_nifty_3m", "Sector vs Nifty, 3 months"),
     bucket_test("S6", "sec_rank_1m", "Sector's rank among 20 sector indices, 1 month"),
     bucket_test("S7", "sec_rank_3m", "Sector's rank among 20 sector indices, 3 months"),
     bucket_test("S8", "sec_vs_200dma", "Sector index vs its 200-day average"),
     bucket_test("S9", "sec_vs_50dma", "Sector index vs its 50-day average"),
     bucket_test("S10", "sec_from_52w_high", "Sector index distance from its 52-week high"),
     bucket_test("S11", "peers_reported_3d", "Same-industry stocks already reported this season: their 3-day average"),
     bucket_test("S12", "sec_reported_3d", "Same-sector-index stocks already reported this season: their 3-day average"),
     bucket_test("S13", "stock_vs_sec_1m", "Stock vs its sector, 1 month"),
     bucket_test("S14", "stock_vs_sec_1w", "Stock vs its sector, 1 week")]
strong = d.sec_rank_1m >= 2 / 3
weak = d.sec_rank_1m <= 1 / 3
R = [rule_test("C1", strong & (d.stock_vs_sec_1m < 0), "Strong sector (top third of sectors, 1M) and stock lagging its sector (catch-up)"),
     rule_test("C2", strong & (d.stock_vs_sec_1m > 0), "Strong sector and stock leading its sector"),
     rule_test("C3", weak & (d.stock_vs_sec_1m > 0), "Weak sector (bottom third) and stock leading its sector"),
     rule_test("C4", weak & (d.stock_vs_sec_1m < 0), "Weak sector and stock lagging its sector"),
     rule_test("C5", (d.sec_vs_200dma > 0) & (d.sec_reported_3d > 0.01), "Sector above its 200-day average and sector stocks reported so far up > 1%"),
     rule_test("C6", (d.sec_reported_3d < -0.01), "Sector stocks reported so far down > 1%"),
     rule_test("C7", (d.sec_rank_1m >= 0.8) & (d.sec_vs_200dma > 0), "Top-4 sector by 1M and above its 200-day average"),
     rule_test("C8", (d.sec_rank_1m <= 0.2) & (d.sec_from_52w_high < -0.1), "Bottom-4 sector by 1M and 10%+ below its 52-week high (sector bounce)"),
     rule_test("ALL", d.three_day.notna(), "All results with a sector index")]
pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_colwidth", 70)
bt, rt = pd.DataFrame(B), pd.DataFrame(R)
bt.to_csv(f"{OUT}/sector_bucket_tests.csv", index=False)
rt.to_csv(f"{OUT}/sector_rule_tests.csv", index=False)
print(bt.drop(columns=["what"]).round(4).to_string())
print(rt.drop(columns=["what"]).round(4).to_string())
keep = ["symbol", "quarter", "qn", "results_date", "cutoff", "industry", "fin_type", "timing", "three_day", "excess_nifty",
        "in_fo", "tp3"] + list(feats) + ["sec_reported_3d", "stock_vs_sec_1m", "stock_vs_sec_1w", "peers_reported_3d", "nifty_1m",
                                          "nifty_3m", "india_vix", "season_so_far_3d"]
d[keep].to_csv(f"{OUT}/sector_features.csv", index=False)
print("sector feature rows:", len(d))
