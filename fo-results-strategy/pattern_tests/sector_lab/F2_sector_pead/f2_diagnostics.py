#!/usr/bin/env python3
"""
F2 diagnostics -- ADDED AFTER seeing the main results (counted: 4 extra variants,
total 116 + 4 = 120). None of these can create a new "promising" claim on its own;
they explain the main results.

D1 (2 variants): A1 REP long, T=3%, H=20, groupings SEC and PEER, with every stock
    whose OWN reaction excess vs Nifty > +4% removed from the basket. Question: is the
    best-looking sector basket just the already-known single-stock edge (buy F&O stock
    that beat Nifty by >4% on reaction day, hold 20)?
D2 (2 variants): mirror of the strongest negative t in A1 (SEC, short sector INDEX after
    the score falls to <= -T, H=5): instead BUY the sector index at that close, hold 5
    sessions, T in {2%, 3%}. Short-term reversal check, with costs.
Placebos: P1 random peers (400 reps) and P2 random dates (400 reps), same as main script.
"""
import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
import sys
sys.path.append('/root/.local/lib/python3.11/site-packages')
import importlib.util
import numpy as np
import pandas as pd

OUT = os.environ.get('SECTOR_LAB', 'sector_lab') + '/F2_sector_pead'
spec = importlib.util.spec_from_file_location('f2main', OUT + '/f2_sector_pead.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
NREP = 400


def d1_frame(lab, grouping, drop):
    a1, _ = m.engine_A(lab, grouping, drop_big=drop)
    d = pd.DataFrame(a1, columns=m.A_COLS)
    return d[(d['T'] == 0.03) & (d.side == 1) & (d.inst == 'REP') & (d.H == 20)]


def d2_frame(lab):
    a1, _ = m.engine_A(lab, 'SEC')
    d = pd.DataFrame(a1, columns=m.A_COLS)
    d = d[(d.side == -1) & (d.inst == 'IDX') & (d.H == 5)].copy()
    c = np.array([m.ix_cost(g) for g in d.g])
    d['side'] = 1
    d['raw_net'] = d.gross - c
    d['vsn_net'] = d.gross - d.nifty - c - m.C_NF
    d['vss_net'] = np.nan
    return d


def perq(d):
    return d.groupby('q').vsn_net.mean().mean() if len(d) else np.nan


def shuffled(lab0, rng):
    lab = lab0.copy()
    for q in range(22):
        idx = np.where(m.ev_fo & (m.ev_q == q))[0]
        lab[idx] = lab0[idx][rng.permutation(len(idx))]
    return lab


def main():
    rng = np.random.default_rng(m.SEED + 7)
    rows = []
    # D1
    for grouping, lab0 in (('SEC', m.lab_SEC), ('PEER', m.lab_PEER)):
        full = d1_frame(lab0, grouping, False)
        drop = d1_frame(lab0, grouping, True)
        s = m.summarize(drop, m.VKEY)
        s['variant'] = f'D1 {grouping} REP long T3 H20 minus >4% stocks'
        s['full_basket_perq'] = full.groupby('q').vsn_net.mean().mean() * 100
        s['legs_removed'] = int(full.nleg.sum() - drop.nleg.sum())
        p1 = np.array([perq(d1_frame(shuffled(lab0, rng), grouping, True)) for _ in range(NREP)])
        p1 = p1[np.isfinite(p1)]
        s['P1_mean'] = p1.mean() * 100
        s['P1_p'] = (p1 >= s.perq_avg.iloc[0] / 100).mean()
        rows.append(s)
    # D2
    d = d2_frame(m.lab_SEC)
    s = m.summarize(d, m.VKEY)
    p1 = [d2_frame(shuffled(m.lab_SEC, rng)) for _ in range(NREP)]
    p1s = {}
    for dd in p1:
        for kv, x in dd.groupby(m.VKEY):
            p1s.setdefault(kv, []).append(x.groupby('q').vsn_net.mean().mean())
    p2 = m.placebo_P2(d, m.lab_SEC, 'SEC', rng, NREP)
    s['variant'] = ['D2 SEC long INDEX after score <= -%d%% H5' % round(t * 100) for t in s['T']]
    s['P1_mean'] = [np.mean(p1s[tuple(r[k] for k in m.VKEY)]) * 100 for _, r in s.iterrows()]
    s['P1_p'] = [np.mean(np.array(p1s[tuple(r[k] for k in m.VKEY)]) >= r.perq_avg / 100) for _, r in s.iterrows()]
    s['P2_mean'] = [np.nanmean(p2[tuple(r[k] for k in m.VKEY)]) * 100 for _, r in s.iterrows()]
    s['P2_p'] = [np.mean(p2[tuple(r[k] for k in m.VKEY)] >= r.perq_avg / 100) for _, r in s.iterrows()]
    rows.append(s)
    out = pd.concat(rows, ignore_index=True)
    out.to_csv(OUT + '/diagnostics_summary.csv', index=False)
    pd.set_option('display.width', 250)
    pd.set_option('display.max_columns', 40)
    cols = ['variant', 'trades', 'legs', 'avg_raw_net', 'avg_vsn_net', 'pct_win', 'nq', 'perq_avg', 't_q', 'first14', 'last8',
            'q_pos', 'full_basket_perq', 'legs_removed', 'P1_mean', 'P1_p', 'P2_mean', 'P2_p']
    print(out.reindex(columns=cols).round(3).to_string())


if __name__ == '__main__':
    main()
