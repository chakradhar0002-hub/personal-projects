"""
F4 placebo / luck checks for ALL 32 pre-registered variants (run after f4_main.py).
 Event variants (A, C, D):
   P1 = shuffle the rule's label among eligible F&O events of the SAME quarter (same number picked per quarter).
   P2 = shuffle within the same (quarter, sector group) - holds sector mix fixed, tests only the timing/order part.
 Time-series variants (B):
   P3 = circularly shift every sector's heavy-day flag series by the same random offset (20..T-20 sessions),
        i.e. the same rule applied on random dates (mostly non-results dates).
 Statistic: per-quarter mean of net-vs-Nifty (after costs) and its t across quarters.
 Reported: p_hi = share of placebo draws with t >= actual t; p_lo = share with t <= actual t.
"""
import sys; sys.path.append('/root/.local/lib/python3.11/site-packages')
import os
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f4_main as M

OUT = M.OUT
rng = np.random.default_rng(20261007)
NDRAW_EV, NDRAW_B = 2000, 1000


def tq(qmeans):
    """qmeans: (ndraw, nq) -> t across quarters per draw (ignores NaN quarters)"""
    m = np.nanmean(qmeans, axis=1)
    n = np.sum(np.isfinite(qmeans), axis=1)
    sd = np.nanstd(qmeans, axis=1, ddof=1)
    return m, m / (sd / np.sqrt(n))


def shuffle_draws(y, qn, strata, sel, nd):
    """random picks of the same number of items per stratum; returns per-quarter means (nd, nq)"""
    qs = np.unique(qn)
    sums = np.zeros((nd, len(qs))); cnts = np.zeros(len(qs))
    qpos = {q: k for k, q in enumerate(qs)}
    for st in np.unique(strata):
        idx = np.where(strata == st)[0]
        k = int(sel[idx].sum())
        if k == 0:
            continue
        q = qpos[qn[idx[0]]]
        pick = np.argsort(rng.random((nd, len(idx))), axis=1)[:, :k]
        sums[:, q] += y[idx][pick].sum(1)
        cnts[q] += k
    with np.errstate(invalid='ignore', divide='ignore'):
        return sums / np.where(cnts > 0, cnts, np.nan)


def event_placebos(f):
    V = M.event_variants(f)
    rows = []
    for name, (el, sel, h, gname, desc) in V.items():
        x = f[el]
        s_ = sel[el].values
        y = x[h + '_nifty'].values
        ok = np.isfinite(y); x, s_, y = x[ok], s_[ok], y[ok]
        qn = x.qn.values
        qa = pd.Series(y[s_]).groupby(qn[s_]).mean()
        act_m, act_t = qa.mean(), M.tstat(qa)
        gcol = 'sector_index' if gname == 'G1' else 'peer_group'
        res = dict(name=name, actual_perq=act_m, actual_t=act_t)
        for lab, strata in [('P1_quarter', qn.astype(str)), ('P2_quarter_sector', (x.qn.astype(str) + '|' + x[gcol].astype(str)).values)]:
            qm = shuffle_draws(y, qn, strata, s_, NDRAW_EV)
            m, t = tq(qm)
            res[lab + '_mean_perq'] = np.mean(m)
            res[lab + '_t05'] = np.quantile(t, 0.05); res[lab + '_t95'] = np.quantile(t, 0.95)
            res[lab + '_p_hi'] = np.mean(t >= act_t); res[lab + '_p_lo'] = np.mean(t <= act_t)
        rows.append(res)
    return pd.DataFrame(rows)


def runs_vec(x, inst, flag):
    """vectorised run builder; same logic as M.runs_from_flags (checked below)."""
    out = []
    for sec, gg in x.groupby('sector', sort=False):
        fl = flag[gg.index.values] if isinstance(flag, pd.Series) else None
        fl = fl.values.astype(bool)
        di = gg.day_i.values
        brk = np.r_[True, np.diff(di) != 1]
        start = fl & (brk | ~np.r_[False, fl[:-1]])
        end = fl & (np.r_[brk[1:], True] | ~np.r_[fl[1:], False])
        si = np.where(start)[0]; ei = np.where(end)[0]
        if len(si) == 0:
            continue
        li = np.r_[0, np.cumsum(np.log1p(np.nan_to_num(gg[inst].values)))]
        ln = np.r_[0, np.cumsum(np.log1p(gg.nifty.values))]
        g_ = np.expm1(li[ei + 1] - li[si]); n_ = np.expm1(ln[ei + 1] - ln[si])
        out.append(pd.DataFrame(dict(sector=sec, qn=gg.qn.values[si], g=g_, n=n_)))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=['sector', 'qn', 'g', 'n'])


def b_net(t, inst):
    hedge = t.sector.map(lambda s: M.C_IDXFUT if (inst == 'idx' and s in M.FUT_SECTORS) else M.C_STOCK)
    return 100 * (t.g - t.n) - hedge - M.C_NIFTY


def b_placebos(dl):
    rows = []
    for name, (g, inst, thr, only) in M.B_DEFS.items():
        x = M.b_subset(dl, g, inst, only).sort_values(['sector', 'day_i'])
        flag = pd.Series(x.share.values >= thr, index=x.index)
        t = runs_vec(x, inst, flag)
        net = b_net(t, inst)
        qa = net.groupby(t.qn).mean()
        # consistency check against f4_main implementation
        tm, _ = M.b_trades(dl, name)
        assert len(tm) == len(t) and abs(tm.b_nifty.mean() - net.mean()) < 1e-9, name
        act_m, act_t = qa.mean(), M.tstat(qa)
        ts, ms = [], []
        T = x.groupby('sector').size().min()
        for _ in range(NDRAW_B):
            off = int(rng.integers(20, T - 20))
            sh = flag.groupby(x.sector.values).transform(lambda v: np.roll(v.values, off)).astype(bool)
            tt = runs_vec(x, inst, sh)
            if len(tt) < 3:
                continue
            q = b_net(tt, inst).groupby(tt.qn).mean()
            ms.append(q.mean()); ts.append(M.tstat(q))
        ts = np.array(ts); ms = np.array(ms)
        rows.append(dict(name=name, actual_perq=act_m, actual_t=act_t, P3_mean_perq=np.nanmean(ms),
                         P3_t05=np.nanquantile(ts, 0.05), P3_t95=np.nanquantile(ts, 0.95),
                         P3_p_hi=np.nanmean(ts >= act_t), P3_p_lo=np.nanmean(ts <= act_t), draws=len(ts)))
    return pd.DataFrame(rows)


def main():
    f = pd.read_csv(OUT + 'events_with_signals.csv')
    for g in ['G1', 'G2']:
        f[g + '_elig'] = f[g + '_elig'].astype(bool)
    ev = event_placebos(f)
    ev.to_csv(OUT + 'placebo_events.csv', index=False)
    dl = pd.read_csv(OUT + 'B_daily_panel.csv')
    bp = b_placebos(dl)
    bp.to_csv(OUT + 'placebo_B.csv', index=False)
    pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
    print(ev.round(3).to_string()); print(); print(bp.round(3).to_string())
    # family-wise: how many variants beat their placebo at 5% one-sided, in either direction
    hi = (ev.P1_quarter_p_hi < 0.05).sum() + (bp.P3_p_hi < 0.05).sum()
    lo = (ev.P1_quarter_p_lo < 0.05).sum() + (bp.P3_p_lo < 0.05).sum()
    print(f'\nVariants better than placebo at p<0.05 (one-sided): {hi} of 32; worse than placebo at p<0.05: {lo} of 32 '
          f'(about 1.6 each expected by chance)')


if __name__ == '__main__':
    main()
