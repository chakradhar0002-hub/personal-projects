"""Extra point-in-time fields needed by the pre-registered screens (no outcome is read here).

Execs the record-loading part of ../build/build_panel.py (read-only; its log / dropped-filings outputs are redirected
to this folder), then for every results event computes raw quarterly PAT of L1, L2, L5, L6 (Lk = Q-k) with the
builder's own rule: one basis per pair, every quarter published strictly before the cutoff.
  pat_l1, pat_l5 : same basis (pair L1/L5)   -> turnaround (L5 < 0 < L1), profit-to-loss, PAT down YoY in L1
  pat_l2, pat_l6 : same basis (pair L2/L6)   -> PAT down YoY in L2
Also the Nifty-adjusted market cap: mcap_adj_cr = mcap_cr x 21,700 / Nifty 50 close on the cutoff day
(21,700 = Nifty at the start of Jan 2024, when AMFI's large-cap cut-off was ~Rs 67,000 cr and small-cap ~Rs 22,000 cr).
Output: extra_features.csv (symbol, quarter, ...).
"""
import os  # LAB_ROOT: scratch folder with report/, search22/, sector_lab/data, fa/; REPO_ROOT: this repo
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
BUILD = HERE.parent / "build"
DATA = os.environ.get('LAB_ROOT', 'lab') + ""

src = open(BUILD / "build_panel.py").read()
head = src.split("rows, audit = [], Counter()")[0]
head = head.replace('OUT = Path(__file__).resolve().parent', f'OUT = Path("{HERE / "out" / "builder_scratch"}")')
(HERE / "out" / "builder_scratch").mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(BUILD))
G = {"__file__": str(BUILD / "build_panel.py"), "__name__": "bp_head"}
exec(head, G)
consistent, qshift = G["consistent"], G["qshift"]

panel = pd.read_csv(BUILD / "fa_panel.csv")
idx = pd.read_csv(f"{DATA}/sector_lab/data/index_close.csv", usecols=["day", "Nifty 50"]).set_index("day")["Nifty 50"]

out = []
for r in panel.itertuples(index=False):
    sym, Q, cut = r.symbol, r.quarter_end, r.cutoff
    L = {k: qshift(Q, k) for k in (1, 2, 5, 6)}
    p15 = consistent(sym, [L[1], L[5]], cut)
    p26 = consistent(sym, [L[2], L[6]], cut)
    nif = idx.get(cut, np.nan)
    out.append({"symbol": sym, "quarter": r.quarter,
                "pat_l1": p15[0]["pat"] if p15 else None, "pat_l5": p15[1]["pat"] if p15 else None,
                "pat_l2": p26[0]["pat"] if p26 else None, "pat_l6": p26[1]["pat"] if p26 else None,
                "nifty_cutoff": nif,
                "mcap_adj_cr": r.mcap_cr * 21700.0 / nif if pd.notna(r.mcap_cr) and pd.notna(nif) else None})
ex = pd.DataFrame(out)
ex.to_csv(HERE / "out" / "extra_features.csv", index=False)

# consistency check with the panel (feature-only, no outcomes)
m = panel.merge(ex, on=["symbol", "quarter"])
ok = m["pat_l5"] > 0
g = 100 * (m.loc[ok, "pat_l1"] / m.loc[ok, "pat_l5"] - 1)
diff = (g - m.loc[ok, "l1_pat_yoy_pct"]).abs()
print("rows", len(ex), "pat_l1/l5 pairs", ex.pat_l5.notna().sum(), "pairs l2/l6", ex.pat_l6.notna().sum())
print("L1 YoY recomputed vs panel: compared", diff.notna().sum(), "max abs diff", diff.max(),
      "panel non-null but ours null", (m.l1_pat_yoy_pct.notna() & ~ok).sum())
f = m[m.in_fo == True]
print("in_fo: pat pair coverage", f.pat_l5.notna().mean().round(3), f.pat_l6.notna().mean().round(3),
      "mcap_adj", f.mcap_adj_cr.notna().mean().round(3))
print("in_fo turnaround (L5<0<L1):", ((f.pat_l5 < 0) & (f.pat_l1 > 0)).sum(), " profit->loss:", ((f.pat_l5 > 0) & (f.pat_l1 < 0)).sum())
print("mcap_adj quantiles", f.mcap_adj_cr.quantile([.1, .25, .5, .75, .9]).round(0).to_dict())
