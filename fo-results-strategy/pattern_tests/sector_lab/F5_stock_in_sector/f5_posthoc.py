"""
F5 POST-HOC ROBUSTNESS (written AFTER seeing f5_main.py output; every item here is counted as an extra variant and
cannot by itself make anything "promising").

Motivation seen in the main run:  F&O events average +0.04% in the 3-day window but non-F&O events +0.94%.  The
non-F&O events are pre-inclusion windows of stocks that are in TODAY's F&O list, i.e. strongly survivorship-selected.
The persistence feature PX averages ALL past windows, including those pre-inclusion windows, so it may partly be a
"recently promoted into F&O" flag rather than a habit of beating the sector.

  R1  A1 rebuilt with PX from past windows in which the stock was ALREADY in F&O (>= 4 such windows)   [rule]
  R2  A1 restricted to stocks that were already in F&O at qn 0 (no late promotions)                    [rule]
  R3  A1 excluding stocks promoted into F&O within the previous 4 quarters                             [rule]
  R4  A6 slope with PX winsorised to [-5%, +5%] and outcome to [-15%, +15%]                             [diagnostic]
  R5  G2 leave-one-sector-out t-values                                                                  [diagnostic]
  R6  A6 slope recomputed with the F&O-only PX of R1                                                    [diagnostic]
Total after this addendum: 20 pre-registered + 6 post-hoc = 26 variants.
"""
import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
import sys
sys.path.append('/root/.local/lib/python3.11/site-packages')
import numpy as np
import pandas as pd

pd.set_option('display.width', 250); pd.set_option('display.max_columns', 60)
OUT = os.environ.get('SECTOR_LAB', 'sector_lab') + '/F5_stock_in_sector/'
RNG = np.random.default_rng(7)
C_RAW, C_NIF = 0.0017, 0.0019
ev = pd.read_csv(OUT + 'f5_event_features.csv')
ev = ev.sort_values(['symbol', 'qn']).reset_index(drop=True)

# R1 feature: PX from F&O-era past windows only
pxf = np.full(len(ev), np.nan)
first_fo = ev[ev.in_fo].groupby('symbol').qn.min()
for sym, g in ev.groupby('symbol'):
    for k in g.index:
        past = g[(g.qn < ev.at[k, 'qn']) & (g.i_p1 < ev.at[k, 'i_cut']) & g.ok & g.in_fo]
        if len(past) >= 4:
            pxf[k] = past.excess_sector.mean()
ev['PXfo'] = pxf
ev['first_fo_qn'] = ev.symbol.map(first_fo)
T = ev[ev.in_fo & ev.ok & ev.has_sec].copy()
print('share of A1 picks (PX>1%) whose stock was promoted into F&O within the previous 4 quarters:',
      round(((T.PX > 0.01) & (T.qn - T.first_fo_qn < 4)).sum() / (T.PX > 0.01).sum(), 3),
      '  vs share in the PX pool:', round(((T.PX.notna()) & (T.qn - T.first_fo_qn < 4)).sum() / T.PX.notna().sum(), 3))
print('mean PX: promoted within 4q %.3f%%, others %.3f%%' % (
    T[T.qn - T.first_fo_qn < 4].PX.mean() * 100, T[T.qn - T.first_fo_qn >= 4].PX.mean() * 100))


def tq(v):
    v = np.asarray(v, float); v = v[~np.isnan(v)]
    return v.mean() / (v.std(ddof=1) / np.sqrt(len(v))) if len(v) > 2 else np.nan


def ev_rule(tr, name, pool):
    nif = tr.excess_nifty.values - C_NIF; raw = tr.three_day.values - C_RAW
    q = pd.Series(nif).groupby(tr.qn.values).mean(); qr = pd.Series(raw).groupby(tr.qn.values).mean()
    # P1 placebo: same number per quarter from pool
    k_q = tr.groupby('qn').size(); nifP = pool.excess_nifty.values - C_NIF
    byq = {qq: np.flatnonzero(pool.qn.values == qq) for qq in k_q.index}
    ts = []
    for d in range(2000):
        m = np.array([nifP[RNG.choice(byq[qq], size=min(k, len(byq[qq])), replace=False)].mean() for qq, k in k_q.items()])
        ts.append(tq(m))
    ts = np.array(ts)
    return dict(rule=name, trades=len(tr), quarters=len(q), perq_raw=qr.mean() * 100, perq_nifty=q.mean() * 100,
                t_q_nifty=tq(q.values), first14_nifty=q[q.index <= 13].mean() * 100, last8_nifty=q[q.index >= 14].mean() * 100,
                qpos_nifty=f'{int((q > 0).sum())} of {len(q)}', q_ge2_raw=f'{int((qr >= 0.02).sum())} of {len(qr)}',
                pool_perq_nifty=pd.Series(nifP).groupby(pool.qn.values).mean().mean() * 100,
                placebo_share_t_ge=np.mean(ts >= tq(q.values)))


rows = []
P1 = T[T.PXfo.notna()]
rows.append(ev_rule(P1[P1.PXfo > 0.01], 'R1 A1 with F&O-era-only PX>+1%', P1))
P2 = T[T.PX.notna() & (T.first_fo_qn == 0)]
rows.append(ev_rule(P2[P2.PX > 0.01], 'R2 A1 only stocks in F&O since qn0', P2))
P3 = T[T.PX.notna() & (T.qn - T.first_fo_qn >= 4)]
rows.append(ev_rule(P3[P3.PX > 0.01], 'R3 A1 excl. promoted in last 4q', P3))
P0 = T[T.PX.notna()]
rows.append(ev_rule(P0[P0.PX > 0.01], 'A1 (main, re-run for reference)', P0))
R = pd.DataFrame(rows)
print(R.round(3).to_string(index=False))


def slopes(df, f, wins=False):
    out = []
    for q, g in df[df[f].notna()].groupby('qn'):
        if len(g) < 10:
            continue
        x = g[f].values; y = g.excess_sector.values
        if wins:
            x = np.clip(x, -0.05, 0.05); y = np.clip(y, -0.15, 0.15)
        out.append(dict(qn=q, b=np.cov(x, y, ddof=1)[0, 1] / np.var(x, ddof=1)))
    return pd.DataFrame(out)


for nm, f, w in [('R4 A6 winsorised', 'PX', True), ('R6 A6 with F&O-era PX', 'PXfo', False), ('A6 main', 'PX', False)]:
    s = slopes(T, f, w)
    print(f'{nm:24s} quarters {len(s)} mean slope {s.b.mean():.3f} t {tq(s.b):.2f} '
          f'first14 {s[s.qn<=13].b.mean():.3f} last8 {s[s.qn>=14].b.mean():.3f}')

# R5 G2 leave-one-sector-out
tr = pd.read_csv(OUT + 'f5_trades.csv')
g2 = tr[tr.rule == 'G2 GX<-0.5% short-vs-sector']
print('\nR5 G2 leave-one-sector-out (short stock vs Nifty, net):')
for s in sorted(g2.sector_index.unique()):
    g = g2[g2.sector_index != s]
    q = g.groupby('qn').nifty_net.mean()
    print(f'  without {s:28s} trades {len(g):4d} perq {q.mean()*100:6.3f}%  t {tq(q.values):5.2f}  '
          f'first14 {q[q.index<=13].mean()*100:6.3f} last8 {q[q.index>=14].mean()*100:6.3f}')
R.to_csv(OUT + 'f5_posthoc.csv', index=False)
