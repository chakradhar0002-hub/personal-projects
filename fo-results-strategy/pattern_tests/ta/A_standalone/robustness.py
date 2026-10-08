"""Secondary checks on standalone_ta.py output. ADDED AFTER the primary run (disclosed); no new signal, no new threshold.

    python3 robustness.py      (needs event_signals.csv and signals_summary.csv from standalone_ta.py)

1. Westfall-Young family-wise correction. Holm ignores that the 44 signals overlap heavily (e.g. %K < 20 and
   %R < -80 are identical). Here the three_day outcomes are permuted among the F&O results of the same quarter
   (20,000 times), every signal's direction-adjusted average is recomputed on the SAME permutation, and each
   signal's |z| is compared with the permutation distribution of the maximum |z| over all 44 signals.
   This can only make the multiple-testing verdict less conservative than Holm; it does not select anything.
2. Timing-matched luck: the same permutation but within the cutoff's calendar week (ISO year-week) instead of the
   quarter, so a signal that merely fires in weeks when the whole market bounced gets no credit (also with the
   Westfall-Young max-|z| family-wise p).
3. The two signals that went nominally the WRONG way (S13, S18) scored in the long direction (post hoc, so they
   can only be leads), and the overlap between the nominal hints and the known lag10_volume trades.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
NSIM = 20000
RNG = np.random.default_rng(7)
COST = 0.17


def perm_means(y, groups, F, sg, nsim, chunk=1000):
    """(nsim x signals) direction-adjusted signal averages with y permuted within groups."""
    idx_by_g = [np.flatnonzero(groups == g) for g in np.unique(groups)]
    n_sig = F.sum(axis=0)
    out = np.empty((nsim, F.shape[1]))
    for c0 in range(0, nsim, chunk):
        m = min(chunk, nsim - c0)
        Y = np.empty((m, len(y)))
        for ix in idx_by_g:
            if len(ix) == 1:
                Y[:, ix] = y[ix]
                continue
            p = np.argsort(RNG.random((m, len(ix))), axis=1)
            Y[:, ix] = y[ix][p]
        out[c0:c0 + m] = (Y @ F) / n_sig * sg
    return out


def main():
    E = pd.read_csv(f"{HERE}/event_signals.csv")
    S = pd.read_csv(f"{HERE}/signals_summary.csv")
    codes = S.code.tolist()
    F = E[codes].to_numpy(float)
    sg = np.where(S.direction == "short", -1.0, 1.0)
    y = E.three_day.to_numpy(float)
    obs = (y @ F) / F.sum(axis=0) * sg
    assert np.allclose(obs, S.avg_pct, atol=1e-3)

    lines = []
    log = lambda *a: (print(*a), lines.append(" ".join(str(x) for x in a)))

    # 1. Westfall-Young max-|z| within quarter
    P = perm_means(y, E.qn.to_numpy(), F, sg, NSIM)
    mu, sd = P.mean(0), P.std(0)
    z_obs = (obs - mu) / sd
    zmax = np.abs((P - mu) / sd).max(axis=1)
    wy = np.array([(1 + (zmax >= abs(z)).sum()) / (NSIM + 1) for z in z_obs])
    p_marg = np.minimum(1, 2 * np.minimum((1 + (P >= obs).sum(0)) / (NSIM + 1), (1 + (P <= obs).sum(0)) / (NSIM + 1)))

    # 2. within-week permutation
    wk = pd.to_datetime(E.cutoff).dt.isocalendar()
    week = (wk.year * 100 + wk.week).to_numpy()
    W = perm_means(y, week, F, sg, NSIM)
    p_week = np.minimum(1, 2 * np.minimum((1 + (W >= obs).sum(0)) / (NSIM + 1), (1 + (W <= obs).sum(0)) / (NSIM + 1)))
    muw, sdw = W.mean(0), W.std(0)
    zmaxw = np.abs((W - muw) / sdw).max(axis=1)
    wy_week = np.array([(1 + (zmaxw >= abs(z)).sum()) / (NSIM + 1) for z in (obs - muw) / sdw])
    R = pd.DataFrame({"code": codes, "signal": S.signal, "direction": S.direction, "trades": S.trades,
                      "avg_pct": obs, "perm_quarter_mean": mu, "z_quarter": z_obs, "p_two_quarter": p_marg,
                      "westfall_young_p": wy, "perm_week_mean": W.mean(0),
                      "edge_vs_week_pct": obs - W.mean(0), "p_two_week": p_week, "westfall_young_p_week": wy_week,
                      "holm_p": S.holm_p, "luck_p_two_primary": S.luck_p_two})
    R.to_csv(f"{HERE}/robustness_multiple_testing.csv", index=False, float_format="%.5g")
    pd.set_option("display.width", 250, "display.max_rows", 100)
    log("1-2. Family-wise (Westfall-Young, within-quarter permutation) and timing-matched (within-week) p-values")
    log(R.sort_values("p_two_quarter").round(4).to_string(index=False))
    log(f"\nsmallest Westfall-Young p: {wy.min():.4f}; signals with WY p < 0.05: {int((wy < 0.05).sum())}; "
        f"nominal within-week p < 0.05: {int((p_week < 0.05).sum())}; smallest within-week Westfall-Young p: "
        f"{wy_week.min():.4f} ({codes[int(np.argmin(wy_week))]})")

    # 3. reverse-direction signals scored long (post hoc) and overlap with lag10
    log("\n3. Post-hoc long scoring of the two signals that went the wrong way (leads only, NOT pre-registered)")
    for code in ("S18", "S13"):
        x = E[E[code] == 1]
        v = x.three_day
        q = v.groupby(x.qn).mean()
        nl = x[~x.in_lag10].three_day
        log(f"  {code} long: n {len(v)}, avg {v.mean():+.3f}, net {v.mean() - COST:+.3f}, take-profit {x.take_profit.mean():+.3f}, "
            f"up {100 * (v > 0).mean():.1f}%, quarters {len(q)}/{int((q > 0).sum())} positive, "
            f"first14 {v[x.qn <= 13].mean():+.3f} last8 {v[x.qn >= 14].mean():+.3f}, "
            f"without best 5 {v.sort_values().iloc[:-5].mean():+.3f}, lag10 overlap {int(x.in_lag10.sum())}, "
            f"without lag10 n {len(nl)} avg {nl.mean():+.3f} (w/o best5 {nl.sort_values().iloc[:-5].mean():+.3f})")
    hints = ["L05", "L20", "S09", "S19", "S13", "S18"]
    O = pd.DataFrame({a: [int(((E[a] == 1) & (E[b] == 1)).sum()) for b in hints + ["in_lag10"]] for a in hints},
                     index=hints + ["lag10"])
    log("\nOverlap (trades in both) between the nominal hints and the lag10_volume trades:")
    log(O.to_string())
    with open(f"{HERE}/robustness.log", "w") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
