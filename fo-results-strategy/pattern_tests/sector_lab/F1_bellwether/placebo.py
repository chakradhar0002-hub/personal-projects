"""
F1 placebo / robustness checks.  Run AFTER bellwether.py (reads its CSVs, reuses its functions).

Pre-registered in bellwether.py: candidates for placebo = every cell passing the screen
(>= 30 trades, hedged t across quarters >= 2.5, both halves > 0 after costs).  The screen passed 4 cells:
    C1  SEC BIG H3  T=3%  S-leg reversal   (buy unreported sector peers after a big sector bellwether lags Nifty >3%)
    C2  SEC BIG H5  T=3%  S-leg reversal   (same, 5 sessions)
    C3  PG  BIG TW  T=5%  LS continuation  (peer_group; trade peers from bellwether close through their own Day+1)
    C4  PG  BIG TW  T=5%  S-leg continuation
Placebos (as pre-registered):
    PL1 within-quarter permutation of the bellwether signals across the variant's triggers, 1000 draws.
    PL2 random non-peers: same number of random in_fo stocks from other groups, same date, same eligibility, 1000 draws.
Robustness diagnostics (not new rules; reported for honesty, not used to pick anything):
    R1 entry at the next session's OPEN instead of the bellwether's reaction close (spillover horizons only)
    R2 leave-one-group-out (min / max of the quarter-t when one sector/peer group is dropped)
    R3 drop the single best quarter
Also:
    gross (no-cost) two-sided count of |t| >= 2.5 over the 288 peer cells, to compare with the ~6 expected by luck.
    Index diagnostic: the SEC/BIG/h=1 index continuation (U_all, not futures-tradeable) -- is it just the
    bellwether's own post-reaction drift?  Compare the bellwether's own next-session excess return with the
    already-reported and not-yet-reported peers'.
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
rng = np.random.default_rng(20261007)

CANDS = [dict(name='C1', G='SEC', BW='BIG', H='H3', T=0.03, leg='S', direction=-1),
         dict(name='C2', G='SEC', BW='BIG', H='H5', T=0.03, leg='S', direction=-1),
         dict(name='C3', G='PG', BW='BIG', H='TW', T=0.05, leg='LS', direction=+1),
         dict(name='C4', G='PG', BW='BIG', H='TW', T=0.05, leg='S', direction=+1)]


def leg_sign(signal, leg, T, direction):
    """+1/-1 position sign, 0 = no trade"""
    s = np.zeros(len(signal))
    if leg in ('L', 'LS'):
        s[signal > T] = 1
    if leg in ('S', 'LS'):
        s[signal < -T] = -1
    return s * direction


def qstat(qn, val, mask):
    """equal weight per trade within quarter -> mean & t across quarters"""
    if mask.sum() == 0:
        return np.nan, np.nan, 0
    q = pd.Series(val[mask]).groupby(qn[mask]).mean()
    return q.mean(), bw.tstat(q), mask.sum()


def main():
    ses, R, IX, INTRA, ev = bw.load()
    px = bw.Px(R, IX)
    nifty = IX['Nifty 50'].values
    nifty_ret = np.r_[np.nan, nifty[1:] / nifty[:-1] - 1]
    trig = pd.read_csv(OUT + 'triggers.csv')
    trades = pd.read_csv(OUT + 'peer_trades.csv')
    ev = ev.copy()

    # ------------------------------------------------ gross two-sided count
    rows = []
    for (G, BWd, H), df in trades.groupby(['G', 'BW', 'H']):
        for T in bw.THRESHOLDS:
            for leg in bw.LEGS:
                sg = leg_sign(df.signal.values, leg, T, +1)
                m = sg != 0
                mu, t, n = qstat(df.qn.values, sg * df.vsn.values, m)
                rows.append(dict(G=G, BW=BWd, H=H, T=T, leg=leg, trades=n, gross_q_vsn=mu * 100, gross_t=t))
    g = pd.DataFrame(rows)
    g.to_csv(OUT + 'gross_two_sided.csv', index=False)
    ok = g[g.trades >= 30]
    print(f'GROSS (no cost) continuation cells with >=30 trades: {len(ok)}; |t|>=2.5: {(ok.gross_t.abs() >= 2.5).sum()} '
          f'(+: {(ok.gross_t >= 2.5).sum()}, -: {(ok.gross_t <= -2.5).sum()}); |t|>=2: {(ok.gross_t.abs() >= 2).sum()}')
    print('expected by luck at |t|>=2.5 (~2% two-sided, ~20 quarters):', round(0.02 * len(ok), 1),
          ' at |t|>=2 (~6%):', round(0.06 * len(ok), 1))
    print(ok[ok.gross_t.abs() >= 2.5].round(2).to_string(index=False))

    # ------------------------------------------------ candidates
    out = []
    evq = {k: v for k, v in ev.groupby('qn')}
    for c in CANDS:
        df = trades[(trades.G == c['G']) & (trades.BW == c['BW']) & (trades.H == c['H'])].reset_index(drop=True)
        tg = trig[(trig.G == c['G']) & (trig.BW == c['BW'])].reset_index(drop=True)
        key = list(zip(tg.qn, tg.group, tg.d))
        kid = {k: i for i, k in enumerate(key)}
        df['tid'] = [kid[k] for k in zip(df.qn, df.group, df.d)]
        cost = bw.COST_HEDGE
        sg = leg_sign(df.signal.values, c['leg'], c['T'], c['direction'])
        m = sg != 0
        act_mu, act_t, n = qstat(df.qn.values, sg * df.vsn.values - cost, m)
        print(f"\n=== {c['name']} {c['G']} {c['BW']} {c['H']} T={c['T']} leg={c['leg']} dir={c['direction']}: "
              f"trades {n}, triggers {df[m].tid.nunique()}, q-avg hedged {act_mu*100:.2f}%, t {act_t:.2f}")

        # PL1: permute signals within quarter across triggers
        sig = tg.signal.values; tq = tg.qn.values
        groups_q = [np.where(tq == q)[0] for q in np.unique(tq)]
        pm, pt = [], []
        for _ in range(NDRAW):
            ps = sig.copy()
            for idx in groups_q:
                ps[idx] = sig[rng.permutation(idx)]
            s2 = leg_sign(ps[df.tid.values], c['leg'], c['T'], c['direction'])
            mm = s2 != 0
            mu, t, _ = qstat(df.qn.values, s2 * df.vsn.values - cost, mm)
            pm.append(mu); pt.append(t)
        pm = np.array(pm); pt = np.array(pt)
        p1_mu = np.nanmean(pm >= act_mu); p1_t = np.nanmean(pt >= act_t)
        print(f'   PL1 signal permutation: placebo q-avg mean {np.nanmean(pm)*100:.2f}%, '
              f'share of draws >= actual mean {p1_mu:.3f}, >= actual t {p1_t:.3f}')

        # PL2: random non-peers
        col = bw.GROUPINGS[c['G']]
        H = c['H']
        sel = df[m]
        trg = sel.groupby('tid').agg(n=('peer', 'size'), qn=('qn', 'first'), d=('d', 'first'), group=('group', 'first'),
                                     signal=('signal', 'first')).reset_index()
        pools = []
        for r in trg.itertuples(index=False):
            e = evq[r.qn]
            e = e[e.in_fo & (e[col].fillna('__none__') != r.group) & (e.i_react > r.d)]
            if H.startswith('H'):
                h = int(H[1:]); e = e[e.i_cut >= r.d + h]
                a = np.full(len(e), r.d); b = a + h
            elif H == 'PC':
                e = e[e.i_cut > r.d]; a = np.full(len(e), r.d); b = e.i_cut.values
            elif H == 'TW':
                e = e[e.i_cut >= r.d]; a = np.full(len(e), r.d); b = e.i_p1.values
            else:
                e = e[(e.i_cut >= r.d) & e.three_day.notna()]
            if H == 'OWN3':
                v = e.excess_nifty.values
            else:
                v = np.array([px.stock(s, a[k], b[k])[0] for k, s in enumerate(e.symbol.values)]) - px.index('Nifty 50', a, b)
            pools.append(v)
        sgn_t = leg_sign(trg.signal.values, c['leg'], c['T'], c['direction'])
        qn_t = trg.qn.values
        pm2, pt2 = [], []
        for _ in range(NDRAW):
            vals, qs = [], []
            for k in range(len(trg)):
                pool = pools[k]
                nn = min(trg.n.values[k], len(pool))
                if nn == 0:
                    continue
                pick = pool[rng.choice(len(pool), nn, replace=False)]
                vals.append(sgn_t[k] * pick - cost); qs.append(np.full(nn, qn_t[k]))
            vals = np.concatenate(vals); qs = np.concatenate(qs)
            mu, t, _ = qstat(qs, vals, np.ones(len(vals), bool))
            pm2.append(mu); pt2.append(t)
        pm2 = np.array(pm2); pt2 = np.array(pt2)
        p2_mu = np.nanmean(pm2 >= act_mu); p2_t = np.nanmean(pt2 >= act_t)
        print(f'   PL2 random non-peers: placebo q-avg mean {np.nanmean(pm2)*100:.2f}%, '
              f'share of draws >= actual mean {p2_mu:.3f}, >= actual t {p2_t:.3f}')

        # R1 next-open entry
        r1 = None
        if H.startswith('H') or H in ('PC', 'TW'):
            ent = sel.entry_i.values + 1
            ex = sel.exit_i.values
            okk = ex > ent - 1
            intr = INTRA.values
            rr = np.empty(len(sel)); nn_ = np.empty(len(sel))
            for k, (s, a0, b0) in enumerate(zip(sel.peer.values, ent, ex)):
                j = px.syms[s]
                io = intr[a0, j]
                rest = px.stock(s, a0, b0)[0] if b0 > a0 else 0.0
                rr[k] = (1 + io) * (1 + rest) - 1
                # nifty from next open is not available -> hedge from the next-session close-to-close proxy:
                # use Nifty from close of entry_i to exit (same as base) minus Nifty's next-session overnight is unknown;
            nifty_part = px.index('Nifty 50', sel.entry_i.values, ex)
            # stock leg from next open vs Nifty from decision close: slightly conservative/approximate hedge
            v = sg[m] * (rr - nifty_part) - cost
            mu, t, _ = qstat(sel.qn.values, v, np.ones(len(v), bool))
            r1 = (mu, t)
            print(f'   R1 next-open entry (Nifty hedge still from decision close; approx): q-avg {mu*100:.2f}%, t {t:.2f}')

        # R2 leave-one-group-out, R3 drop best quarter
        v = sg[m] * sel.vsn.values - cost
        lo = []
        for gname in sel.group.unique():
            mm = sel.group.values != gname
            mu, t, _ = qstat(sel.qn.values, v, mm)
            lo.append((gname, mu, t))
        lo = pd.DataFrame(lo, columns=['group', 'mu', 't'])
        q = pd.Series(v).groupby(sel.qn.values).mean()
        qd = q.drop(q.idxmax())
        print(f'   R2 leave-one-group-out t range {lo.t.min():.2f} .. {lo.t.max():.2f} '
              f'(dropping {lo.loc[lo.t.idxmin(), "group"]} gives the min)')
        print(f'   R3 drop best quarter (qn {q.idxmax()}, {q.max()*100:.2f}%): q-avg {qd.mean()*100:.2f}%, t {bw.tstat(qd):.2f}')
        print('   per-quarter hedged avg % :', (q * 100).round(2).to_dict())
        print('   trades by group:', sel.group.value_counts().to_dict())
        out.append(dict(name=c['name'], G=c['G'], BW=c['BW'], H=H, T=c['T'], leg=c['leg'], direction=c['direction'],
                        trades=n, triggers=int(df[m].tid.nunique()), q_avg_vsn=act_mu * 100, t=act_t,
                        PL1_mean=np.nanmean(pm) * 100, PL1_p_mean=p1_mu, PL1_p_t=p1_t,
                        PL2_mean=np.nanmean(pm2) * 100, PL2_p_mean=p2_mu, PL2_p_t=p2_t,
                        R1_mu=None if r1 is None else r1[0] * 100, R1_t=None if r1 is None else r1[1],
                        R2_tmin=lo.t.min(), R2_tmax=lo.t.max(), R3_mu=qd.mean() * 100, R3_t=bw.tstat(qd)))
    pd.DataFrame(out).to_csv(OUT + 'placebo_results.csv', index=False)

    # ------------------------------------------------ index diagnostic (SEC BIG, h=1, |signal|>3%)
    ev2 = ev.copy()
    ev2['xreact'] = ev2['move'] - nifty_ret[ev2.i_react.values]
    tg = trig[(trig.G == 'SEC') & (trig.BW == 'BIG') & (trig.signal.abs() > 0.03)]
    rows = []
    for t in tg.itertuples(index=False):
        if t.group not in px.ix:
            continue
        a, b = t.d, t.d + 1
        nr = px.index('Nifty 50', a, b)
        ixr = px.index(t.group, a, b) - nr
        sgn = np.sign(t.signal)
        bws = t.bw_syms.split('|')
        own = np.mean([px.stock(s, a, b)[0] - nr for s in bws])
        m_ = ev2[(ev2.qn == t.qn) & (ev2.sector_index == t.group)]
        rep = m_[(m_.i_react < t.d)]  # already reported earlier
        unr = m_[(m_.i_react > t.d)]
        rep_r = np.mean([px.stock(s, a, b)[0] - nr for s in rep.symbol]) if len(rep) else np.nan
        unr_r = np.mean([px.stock(s, a, b)[0] - nr for s in unr.symbol]) if len(unr) else np.nan
        rows.append(dict(qn=t.qn, group=t.group, d=t.d, sgn=sgn, index_x=sgn * ixr, bellwether_own=sgn * own,
                         reported_peers=sgn * rep_r, unreported_peers=sgn * unr_r))
    dd = pd.DataFrame(rows)
    dd.to_csv(OUT + 'index_diagnostic.csv', index=False)
    print('\nINDEX DIAGNOSTIC (SEC BIG, |signal|>3%, next session, signed by bellwether, gross, % per trigger):')
    for ccol in ['index_x', 'bellwether_own', 'reported_peers', 'unreported_peers']:
        q = dd.groupby('qn')[ccol].mean()
        print(f'   {ccol:18s} mean {dd[ccol].mean()*100:6.2f}  q-avg {q.mean()*100:6.2f}  t_q {bw.tstat(q):5.2f}  n {dd[ccol].notna().sum()}')
    print('   sector index split by group (index_x mean %):', (dd.groupby('group').index_x.mean() * 100).round(2).to_dict())


if __name__ == '__main__':
    main()
