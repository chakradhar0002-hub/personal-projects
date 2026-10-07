"""
F1 family-wise (selection-adjusted) placebo + diagnostics for the screened candidates.

ADDED AFTER seeing the screen results (declared honestly): this is NOT a new trading rule, it is a stricter
version of the pre-registered PL1 placebo. PL1 in placebo.py tests the single chosen cell; but the cell was
chosen as the best of 576 directional rules. Here every draw permutes the bellwether signals within each
quarter (separately for each grouping/bellwether definition, the same permutation used for all horizons,
thresholds and legs of that definition), recomputes ALL 576 directional rules (288 cells x continuation /
reversal, after costs, hedged vs Nifty), and records
    (a) the best t among rules with >= 30 trades,
    (b) the number of rules passing the full screen (>= 30 trades, t >= 2.5, both halves > 0).
The p-value = share of draws where chance does as well as the real data (best t 2.85; 4 rules passing).

Diagnostics for C1 (SEC BIG H3 S-leg reversal): trigger-level (one number per bellwether event) t;
the peers' own move on the bellwether's reaction day (known at entry); path day+1/day+2/day+3 of the H3 sample.
"""
import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
import sys
sys.path.append('/root/.local/lib/python3.11/site-packages')
import importlib.util
import numpy as np
import pandas as pd

OUT = os.environ.get('SECTOR_LAB', 'sector_lab') + '/F1_bellwether/'
spec = importlib.util.spec_from_file_location('bw', OUT + 'bellwether.py')
bw = importlib.util.module_from_spec(spec); spec.loader.exec_module(bw)
NDRAW = 1000
rng = np.random.default_rng(7)
COST = bw.COST_HEDGE
NQ = 22


def cell_stats(qn, val, mask):
    """quarter-averaged mean, t, first14, last8, n for all trades in mask"""
    n = mask.sum()
    if n < 30:
        return None
    cnt = np.bincount(qn[mask], minlength=NQ); s = np.bincount(qn[mask], weights=val[mask], minlength=NQ)
    have = cnt > 0
    qm = s[have] / cnt[have]; qi = np.arange(NQ)[have]
    if len(qm) < 3:
        return None
    t = qm.mean() / (qm.std(ddof=1) / np.sqrt(len(qm)))
    f = qm[qi <= 13]; l = qm[qi >= 14]
    return t, (f.mean() if len(f) else np.nan), (l.mean() if len(l) else np.nan)


def all_rules(blocks, sigs):
    """blocks: list of (qn, vsn, tid) arrays per (G,BW,H); sigs: per (G,BW) signal arrays"""
    best = -np.inf; npass = 0
    for (gb, qn, vsn, tid) in blocks:
        s = sigs[gb][tid]
        for T in bw.THRESHOLDS:
            up = s > T; dn = s < -T
            for leg in ('L', 'S', 'LS'):
                sg = np.zeros(len(s))
                if leg in ('L', 'LS'):
                    sg[up] = 1
                if leg in ('S', 'LS'):
                    sg[dn] = -1
                m = sg != 0
                for d in (+1, -1):
                    r = cell_stats(qn, d * sg * vsn - COST, m)
                    if r is None:
                        continue
                    t, f, l = r
                    best = max(best, t)
                    if t >= 2.5 and f > 0 and l > 0:
                        npass += 1
    return best, npass


def main():
    trig = pd.read_csv(OUT + 'triggers.csv')
    trades = pd.read_csv(OUT + 'peer_trades.csv')
    trig['tid'] = trig.groupby(['G', 'BW']).cumcount()
    trades = trades.merge(trig[['G', 'BW', 'qn', 'group', 'd', 'tid']], on=['G', 'BW', 'qn', 'group', 'd'], how='left')
    assert trades.tid.notna().all()
    blocks = []
    for (G, BWd, H), df in trades.groupby(['G', 'BW', 'H']):
        blocks.append(((G, BWd), df.qn.values.astype(int), df.vsn.values, df.tid.values.astype(int)))
    sig0 = {k: g.sort_values('tid').signal.values for k, g in trig.groupby(['G', 'BW'])}
    qn_t = {k: g.sort_values('tid').qn.values for k, g in trig.groupby(['G', 'BW'])}
    best0, pass0 = all_rules(blocks, sig0)
    print(f'REAL DATA: best t over all directional rules {best0:.2f}; rules passing full screen {pass0}')
    bests, passes = [], []
    qidx = {k: [np.where(v == q)[0] for q in np.unique(v)] for k, v in qn_t.items()}
    for _ in range(NDRAW):
        sig = {}
        for k, v in sig0.items():
            p = v.copy()
            for idx in qidx[k]:
                p[idx] = v[rng.permutation(idx)]
            sig[k] = p
        b, n = all_rules(blocks, sig)
        bests.append(b); passes.append(n)
    bests = np.array(bests); passes = np.array(passes)
    print(f'PLACEBO (within-quarter signal permutation, {NDRAW} draws): median best t {np.median(bests):.2f}, '
          f'95th pct {np.percentile(bests, 95):.2f}; share of draws with best t >= {best0:.2f}: {np.mean(bests >= best0):.3f}')
    print(f'   rules passing the full screen per draw: mean {passes.mean():.2f}, median {np.median(passes):.0f}, '
          f'share of draws with >= {pass0}: {np.mean(passes >= pass0):.3f}')
    pd.DataFrame({'best_t': bests, 'n_pass': passes}).to_csv(OUT + 'familywise_draws.csv', index=False)

    # ---------------- diagnostics for C1
    ses, R, IX, INTRA, ev = bw.load()
    px = bw.Px(R, IX)
    c1 = trades[(trades.G == 'SEC') & (trades.BW == 'BIG') & (trades.H == 'H3') & (trades.signal < -0.03)].copy()
    c1['v'] = c1.vsn - COST   # reversal = long the peer
    tl = c1.groupby(['qn', 'group', 'd']).v.mean()
    print(f'\nC1 trigger-level (one number per bellwether event): n {len(tl)}, mean {tl.mean()*100:.2f}%, t {bw.tstat(tl):.2f}, '
          f'positive {int((tl > 0).sum())}/{len(tl)}')
    for k in (1, 2, 3):
        a = c1.d.values + k - 1; b = c1.d.values + k
        r = np.array([px.stock(s, a[j], b[j])[0] for j, s in enumerate(c1.peer.values)]) - px.index('Nifty 50', a, b)
        q = pd.Series(r).groupby(c1.qn.values).mean()
        print(f'   path: session d+{k} gross excess (long peer) q-avg {q.mean()*100:.2f}%  t {bw.tstat(q):.2f}')
    a = c1.d.values - 1; b = c1.d.values
    r0 = np.array([px.stock(s, a[j], b[j])[0] for j, s in enumerate(c1.peer.values)]) - px.index('Nifty 50', a, b)
    c1['peer_day_d'] = r0
    q = pd.Series(r0).groupby(c1.qn.values).mean()
    print(f'   peers own excess on the bellwether reaction day d (known at entry): q-avg {q.mean()*100:.2f}%  t {bw.tstat(q):.2f}')
    fell = c1.peer_day_d < 0
    for nm, mm in [('peers that fell on d', fell), ('peers that did not fall on d', ~fell)]:
        q = c1[mm].groupby('qn').v.mean()
        print(f'   {nm:30s}: trades {mm.sum()}, q-avg net hedged {q.mean()*100:.2f}%, t {bw.tstat(q):.2f}')
    c1.to_csv(OUT + 'C1_trades.csv', index=False)
    # same-length check: H3 sample of all-peer baseline (unconditional) -- is the rebound specific to weak-bellwether dates?
    allp = trades[(trades.G == 'SEC') & (trades.BW == 'BIG') & (trades.H == 'H3')]
    for nm, mm in [('signal < -3%', allp.signal < -0.03), ('-3%..+3%', allp.signal.abs() <= 0.03), ('signal > +3%', allp.signal > 0.03)]:
        q = allp[mm].groupby('qn').vsn.mean()
        print(f'   SEC BIG H3 long-peer GROSS hedged by bellwether bucket {nm:14s}: trades {mm.sum():4d}, q-avg {q.mean()*100:.2f}%, t {bw.tstat(q):.2f}')


if __name__ == '__main__':
    main()
