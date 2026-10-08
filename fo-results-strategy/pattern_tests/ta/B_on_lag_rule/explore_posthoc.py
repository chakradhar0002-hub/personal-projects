"""POST-HOC (not pre-registered) follow-ups to ta_on_lag.py, labelled as such and counted.

 1. Family-wise (max-|z|) within-quarter permutation p for the 19 splits on S85 and S44 (accounts for the correlation
    between the oversold indicators; a fairer multiplicity correction than Holm). Not a new test, an adjustment.
 2. The three splits with raw p < 0.05 (C6 MFI<20 on S85; C5 CCI<-100 and C7 oversold>=3 on S44) as rules, with luck,
    placebo, halves, per-quarter, plus the same split on the 41 trades with volume 1.0-1.3x (S85 minus S44).
 3. Reference levels: unconditional in_fo placebo mean, and the not-in-lag-rule part of each replacement rule.

    python3 explore_posthoc.py  -> posthoc.log
"""
import os
import sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = [sys.argv[0]]
# reuse the pre-registered definitions without re-running the main script's printing
src = open(f"{HERE}/ta_on_lag.py").read()
src = src.split("# ------------------------------------------------------------------------------------------------ splits")[0]
src = src.replace('sys.stdout = Tee(f"{HERE}/run.log")', 'sys.stdout = Tee(f"{HERE}/posthoc.log")')
exec(compile(src, "ta_on_lag_defs", "exec"))
rng = np.random.default_rng(777)

# ---------------------------------------------------------------------------- 1. family-wise max-|z| permutation
print("\n=== 1. family-wise within-quarter permutation (max |z| over the 19 conditions) ===")
for base in ("S85", "S44"):
    m = S[base]
    d = E[m].reset_index(drop=True)
    o = np.argsort(d.qn.to_numpy(), kind="stable")
    y, q = d.three_day.to_numpy()[o], d.qn.to_numpy()[o]
    L = np.column_stack([CE[c][m][o] for c in CE]).astype(float)        # n x 19
    keys = q[None, :] + rng.random((NPERM, len(y)))
    Yp = y[np.argsort(keys, axis=1)]                                      # outcome shuffled within quarter
    nT = L.sum(0)
    ok = (nT > 0) & (nT < len(y))
    sT = Yp @ L                                                           # NPERM x 19
    Dp = sT / nT - (Yp.sum(1, keepdims=True) - sT) / (len(y) - nT)
    Dobs = (y @ L) / nT - (y.sum() - y @ L) / (len(y) - nT)
    sd = Dp.std(0)
    z = np.abs(Dp[:, ok] / sd[ok]).max(1)
    zo = np.abs(Dobs / sd)
    fw = [(np.sum(z >= zo[i] - 1e-12) + 1) / (NPERM + 1) if ok[i] else np.nan for i in range(len(zo))]
    t = pd.DataFrame({"cond": list(CE), "nT": nT.astype(int), "D": Dobs, "z": Dobs / sd, "p_familywise": fw})
    print(f"-- {base}")
    print(t.round(3).to_string(index=False))

# ---------------------------------------------------------------------------- 2. post-hoc rules
Y = E.three_day.to_numpy()
QALL = E.qn.to_numpy()
QIDX = {qq: np.flatnonzero(QALL == qq) for qq in np.unique(QALL)}


def luck(mask):
    obs = Y[mask].mean()
    tot, n = np.zeros(NLUCK), 0
    for qq, idx in QIDX.items():
        k = int(mask[idx].sum())
        if k:
            tot += Y[idx][np.argsort(rng.random((NLUCK, len(idx))), axis=1)[:, :k]].sum(1)
            n += k
    return (np.sum(tot / n >= obs - 1e-12) + 1) / (NLUCK + 1)


def boot_mean(y, cl):
    codes, uniq = pd.factorize(cl)
    K = len(uniq)
    s, n = np.bincount(codes, weights=y, minlength=K), np.bincount(codes, minlength=K).astype(float)
    W = rng.multinomial(K, np.full(K, 1 / K), size=NBOOT)
    b = (W @ s) / (W @ n)
    return y.mean(), np.percentile(b, 2.5), np.percentile(b, 97.5)


def report(name, mask, pmask, within=None):
    d = E[mask]
    y = d.three_day.to_numpy()
    q = d.qn.to_numpy()
    qm = d.groupby("qn").three_day.mean()
    ys = np.sort(y)
    pm, lo, hi = boot_mean(P.three_day.to_numpy()[pmask], P.month.to_numpy()[pmask])
    r = {"rule": name, "n": len(y), "mean": y.mean(), "net": y.mean() - COST, "tp": d.take_profit.mean(),
         "tp_net": d.take_profit.mean() - COST, "up%": 100 * (y > 0).mean(), "q+": f"{(qm > 0).sum()}/{len(qm)}",
         "n14": (q <= 13).sum(), "f14": y[q <= 13].mean(), "n8": (q >= 14).sum(), "l8": y[q >= 14].mean(),
         "xb5": ys[:-5].mean(), "luck_p_vs_all_events": luck(mask), "plac_n": int(pmask.sum()), "plac_mean": pm,
         "plac_lo": lo, "plac_hi": hi}
    print(pd.DataFrame([r]).round(3).to_string(index=False))
    print("   per quarter:", " ".join(f"q{k}:{v:+.1f}({c})" for (k, v), c in
                                     zip(qm.items(), d.groupby("qn").size())))
    return r


print("\n=== 2. POST-HOC rules (not pre-registered; promoted by nothing; shown because raw p < 0.05) ===")
volE, volP = E.vol_ratio_5_60.to_numpy(), P.vol_ratio_5_60.to_numpy()
mid = S["S85"] & ~S["S44"]
pmid = PB["S85"] & ~PB["S44"]
rows = []
for c, base, pb in (("C6_mfi_lt20", "S85", "S85"), ("C5_cci_lt_m100", "S44", "S44"), ("C7_oversold_ge3", "S44", "S44")):
    print(f"\n-- {base} + {c}")
    rows.append(report(f"{base}+{c}", S[base] & CE[c], PB[pb] & CP[c]))
    rows.append(report(f"{base}+NOT {c}", S[base] & ~CE[c], PB[pb] & ~CP[c]))
    for lab, mk, pk in (("vol 1.0-1.3 slice", mid, pmid),):
        a, b = mk & CE[c], mk & ~CE[c]
        print(f"   same split on the {lab} ({mk.sum()} trades): T n={a.sum()} mean={Y[a].mean():+.3f}  "
              f"F n={b.sum()} mean={Y[b].mean():+.3f}  D={Y[a].mean() - Y[b].mean():+.3f}")
pd.DataFrame(rows).to_csv(f"{HERE}/posthoc_rules.csv", index=False, float_format="%.4f")

# ---------------------------------------------------------------------------- 3. reference levels
print("\n=== 3. reference levels (three_day %, gross) ===")
print(f"all in_fo placebo rows: n={len(P)} mean={P.three_day.mean():.3f}; all in_fo events: mean={E.three_day.mean():.3f}")
for th in (1.0, 1.3):
    m = lagE & (volE >= th)
    pm = lagP & (volP >= th)
    print(f"lag<-10 & vol>={th}: events n={m.sum()} mean={Y[m].mean():.3f} | placebo n={pm.sum()} "
          f"mean={P.three_day.to_numpy()[pm].mean():.3f}")
q = lagE & (volE < 1.0)
print(f"lag<-10 & vol<1.0 (quiet): events n={q.sum()} mean={Y[q].mean():.3f}")
for c in ("C1_rsi14_lt30", "C7_oversold_ge3", "C5_cci_lt_m100"):
    for nm, mk in (("lag<-10 & vol<1.0", lagE & (volE < 1.0)), ("NOT lag<-10, vol>=1.0", ~lagE & (volE >= 1.0)),
                   ("NOT lag<-10, any vol", ~lagE)):
        a = mk & CE[c]
        print(f"{c:18s} within {nm:22s}: n={a.sum():4d} mean={Y[a].mean():+.3f}")
