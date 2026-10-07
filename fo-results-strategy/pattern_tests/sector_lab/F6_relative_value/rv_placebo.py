#!/usr/bin/env python3
"""
F6 placebo checks (pre-registered in rv_main.py header): run for every near-candidate
(none qualified) plus the best-t variant of each part:
  a_continue_D8_any_h20, b_long_good_sales_yoy_20_h20, c4_highSD_signMU_signMU_h20, d_long_S3
200 runs each.  Output: placebo_results.csv, run_placebo.txt (stdout).
Run: python3 -I rv_placebo.py
"""
import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
import sys
sys.path.append('/root/.local/lib/python3.11/site-packages')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import rv_main as M

ev = M.ev
rng = np.random.default_rng(777)
NP = M.NPLACEBO
OUT = M.OUT


def summ(df):
    q = df.groupby('qn')['main'].mean()
    return q.mean(), M.tstat(q.values), len(df)


def shuffle_within(E, col, keys, mask):
    E = E.copy()
    sub = E[mask]
    vals = E[col].values.copy()
    for _, idx in sub.groupby(keys).groups.items():
        idx = np.asarray(idx)
        vals[idx] = rng.permutation(vals[idx])
    E[col] = vals
    return E


rows = []


def report(name, kind, actual, draws):
    am, at, an = actual
    dm = np.array([d[0] for d in draws]); dt = np.array([d[1] for d in draws]); dn = np.array([d[2] for d in draws])
    r = dict(variant=name, placebo=kind, actual_season_avg=am, actual_t=at, actual_trades=an,
             placebo_mean_season_avg=np.nanmean(dm), placebo_p95_season_avg=np.nanpercentile(dm, 95),
             placebo_mean_t=np.nanmean(dt), placebo_mean_trades=dn.mean(),
             share_placebo_avg_ge_actual=np.mean(dm >= am), share_placebo_t_ge_actual=np.mean(dt >= at), runs=len(draws))
    rows.append(r)
    print(f'{name:32s} {kind:28s} actual avg {am:6.2f} t {at:5.2f} n {an:5d} | placebo avg {r["placebo_mean_season_avg"]:6.2f} '
          f'(p95 {r["placebo_p95_season_avg"]:5.2f}) t {r["placebo_mean_t"]:5.2f} n {r["placebo_mean_trades"]:7.1f} | '
          f'P(avg>=act) {r["share_placebo_avg_ge_actual"]:.3f}  P(t>=act) {r["share_placebo_t_ge_actual"]:.3f}', flush=True)


# ------------------------------------------------------------------ (a)
P = M.build_pairs(ev)
act = summ(M.eval_a(P, 0.08, 'any', 20, 'continue', full=False))
mask = ev.fo & ev.exc.notna() & ev.grp.notna()
draws = []
for k in range(NP):
    E2 = shuffle_within(ev, 'exc', ['grp', 'qn'], mask)
    draws.append(summ(M.eval_a(M.build_pairs(E2), 0.08, 'any', 20, 'continue', full=False)))
report('a_continue_D8_any_h20', 'P1 shuffle reaction in grp-season', act, draws)

# P2 fake reaction days: random non-results session inside the same season window
season_lo = ev.groupby('qn').i_react.min(); season_hi = ev.groupby('qn').i_react.max()
lo = ev.qn.map(season_lo).values; hi = ev.qn.map(season_hi).values
cut = ev.i_cut.values; rea = ev.i_react.values; s = ev.s.values
draws = []
for k in range(NP):
    fake = np.empty(len(ev), int)
    for j in range(len(ev)):
        while True:
            d = rng.integers(lo[j], hi[j] + 1)
            if not (cut[j] <= d <= rea[j] + 1):
                break
        fake[j] = d
    E2 = ev.copy()
    E2['i_react'] = fake
    E2['exc'] = M.R[fake, s] - M.NRET[fake]
    draws.append(summ(M.eval_a(M.build_pairs(E2), 0.08, 'any', 20, 'continue', full=False)))
report('a_continue_D8_any_h20', 'P2 random non-results days', act, draws)

# ------------------------------------------------------------------ (b)
B = M.build_b(ev, 'sales_yoy')
act = summ(M.eval_b(B, 0.20, 'long_good', 20, full=False))
maskb = ev.grp.notna() & ev.exc.notna()
draws = []
for k in range(NP):
    E2 = shuffle_within(ev, 'sales_yoy', ['grp', 'qn'], maskb)
    draws.append(summ(M.eval_b(M.build_b(E2, 'sales_yoy'), 0.20, 'long_good', 20, full=False)))
report('b_long_good_sales_yoy_20_h20', 'P1 shuffle sales_yoy grp-season', act, draws)

# ------------------------------------------------------------------ (c)
C = M.build_c(ev)
act = summ(M.eval_c(C, 'c4_highSD_signMU', 'signMU', 20, full=False))
maskc = ev.exc.notna() & ~ev.sector_index.isin(M.PART_C_EXCLUDE)
draws = []
for k in range(NP):
    E2 = shuffle_within(ev, 'exc', ['qn'], maskc)
    draws.append(summ(M.eval_c(M.build_c(E2), 'c4_highSD_signMU', 'signMU', 20, full=False)))
report('c4_highSD_signMU_signMU_h20', 'P1 shuffle reaction across sectors in season', act, draws)

# ------------------------------------------------------------------ (d)
Dd = M.build_d(ev)
act = summ(M.eval_d(Dd, 0.03, 'long', full=False))
maskd = ev.grp.notna() & ev.exc.notna()
draws = []
for k in range(NP):
    E2 = shuffle_within(ev, 'exc', ['grp', 'qn'], maskd)
    draws.append(summ(M.eval_d(M.build_d(E2), 0.03, 'long', full=False)))
report('d_long_S3', 'P1 shuffle reaction in grp-season', act, draws)

pd.DataFrame(rows).to_csv(OUT + 'placebo_results.csv', index=False)
print('written', OUT + 'placebo_results.csv')
