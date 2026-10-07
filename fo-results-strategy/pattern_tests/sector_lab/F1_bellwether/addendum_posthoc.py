"""
F1 addendum -- EXPLICITLY POST-HOC (written after seeing familywise.py output). Counted as extra variants.

Variant #337 (post-hoc, suggested by the bucket diagnostic in familywise.py): SEC / BIG bellwether,
    |bellwether excess reaction| > 3% in EITHER direction -> BUY the not-yet-reported F&O sector peers at the
    bellwether's reaction-day close, hold 3 sessions (exit no later than the peer's own cutoff), hedge with Nifty.
    Because it was picked after looking, it cannot be called "promising" whatever the numbers say; it is
    reported only so the trader knows what the data show. Placebos PL1 (within-quarter signal permutation)
    and PL2 (random non-peers) as before.
Index check (pre-registered test idx: SEC BIG h=1 U_all T=3%, t 3.14 in bellwether.py): PL1 placebo, and the
    net result if the sector exposure has to be bought as a basket of stock futures (0.17% + 0.02% cost)
    instead of an index future (only Bank / FinServ have one).
TOTAL VARIANT COUNT after this addendum: 336 pre-registered two-sided tests + 1 post-hoc = 337.
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
rng = np.random.default_rng(11)
NDRAW = 1000
COST = bw.COST_HEDGE


def qmt(qn, v):
    q = pd.Series(v).groupby(np.asarray(qn)).mean()
    return q


def main():
    ses, R, IX, INTRA, ev = bw.load()
    px = bw.Px(R, IX)
    trig = pd.read_csv(OUT + 'triggers.csv')
    trades = pd.read_csv(OUT + 'peer_trades.csv')
    tg = trig[(trig.G == 'SEC') & (trig.BW == 'BIG')].reset_index(drop=True)
    df = trades[(trades.G == 'SEC') & (trades.BW == 'BIG') & (trades.H == 'H3')].reset_index(drop=True)
    kid = {k: i for i, k in enumerate(zip(tg.qn, tg.group, tg.d))}
    df['tid'] = [kid[k] for k in zip(df.qn, df.group, df.d)]
    m = df.signal.abs() > 0.03
    x = df[m]
    v = x.vsn.values - COST
    q = qmt(x.qn.values, v)
    tl = pd.Series(v).groupby([x.qn.values, x.group.values, x.d.values]).mean()
    raw_q = qmt(x.qn.values, x.raw.values - bw.COST_RAW)
    vss_q = qmt(x.qn.values, x.vss.values - COST)
    print(f'#337 POST-HOC SEC BIG H3 |s|>3% long peers: trades {len(x)}, triggers {len(tl)}, quarters {len(q)}')
    print(f'   avg/trade: raw net {(x.raw.values - bw.COST_RAW).mean()*100:.2f}%, hedged net {v.mean()*100:.2f}%, '
          f'vs sector net {(x.vss.values - COST).mean()*100:.2f}%  | win {np.mean(v > 0)*100:.0f}%')
    print(f'   quarter-avg hedged {q.mean()*100:.2f}%  t {bw.tstat(q):.2f}  first14 {q[q.index <= 13].mean()*100:.2f}  '
          f'last8 {q[q.index >= 14].mean()*100:.2f}  positive {int((q > 0).sum())}/{len(q)}  | raw q-avg {raw_q.mean()*100:.2f}% '
          f'| vs-sector q-avg {vss_q.mean()*100:.2f}% t {bw.tstat(vss_q):.2f} | trigger-level t {bw.tstat(tl):.2f}')
    act = q.mean(); act_t = bw.tstat(q)
    # PL1
    sig = tg.signal.values; tq = tg.qn.values
    gq = [np.where(tq == k)[0] for k in np.unique(tq)]
    pm, pt = [], []
    for _ in range(NDRAW):
        ps = sig.copy()
        for idx in gq:
            ps[idx] = sig[rng.permutation(idx)]
        mm = np.abs(ps[df.tid.values]) > 0.03
        qq = qmt(df.qn.values[mm], df.vsn.values[mm] - COST)
        pm.append(qq.mean()); pt.append(bw.tstat(qq))
    pm, pt = np.array(pm), np.array(pt)
    print(f'   PL1 permutation: placebo mean {pm.mean()*100:.2f}%, share >= actual mean {np.mean(pm >= act):.3f}, share >= actual t {np.mean(pt >= act_t):.3f}')
    # PL2 random non-peers
    evq = {k: g for k, g in ev.groupby('qn')}
    trg = x.groupby('tid').agg(n=('peer', 'size'), qn=('qn', 'first'), d=('d', 'first'), group=('group', 'first')).reset_index()
    pools = []
    for r in trg.itertuples(index=False):
        e = evq[r.qn]
        e = e[e.in_fo & (e.sector_index != r.group) & (e.i_react > r.d) & (e.i_cut >= r.d + 3)]
        a = np.full(len(e), r.d)
        pools.append(np.array([px.stock(s, r.d, r.d + 3)[0] for s in e.symbol]) - px.index('Nifty 50', a, a + 3))
    pm2, pt2 = [], []
    for _ in range(NDRAW):
        vals, qs = [], []
        for k, r in enumerate(trg.itertuples(index=False)):
            nn = min(r.n, len(pools[k]))
            vals.append(pools[k][rng.choice(len(pools[k]), nn, replace=False)] - COST); qs.append(np.full(nn, r.qn))
        qq = qmt(np.concatenate(qs), np.concatenate(vals))
        pm2.append(qq.mean()); pt2.append(bw.tstat(qq))
    pm2, pt2 = np.array(pm2), np.array(pt2)
    print(f'   PL2 random non-peers: placebo mean {pm2.mean()*100:.2f}%, share >= actual mean {np.mean(pm2 >= act):.3f}, share >= actual t {np.mean(pt2 >= act_t):.3f}')
    print('   per quarter %:', (q * 100).round(2).to_dict())

    # ---------------- index check
    it = pd.read_csv(OUT + 'index_trades.csv')
    it = it[(it.BW == 'BIG') & (it.h == 1)].reset_index(drop=True)
    mm = it.signal.abs() > 0.03
    y = it[mm]
    for nm, c in [('index future cost 0.04%', bw.COST_INDEX), ('stock-basket cost 0.19%', COST)]:
        qq = qmt(y.qn.values, np.sign(y.signal.values) * y.vsn.values - c)
        print(f'\nINDEX SEC BIG h1 |s|>3% (all sectors) with {nm}: trades {len(y)}, q-avg {qq.mean()*100:.2f}%, t {bw.tstat(qq):.2f}, '
              f'first14 {qq[qq.index <= 13].mean()*100:.2f}, last8 {qq[qq.index >= 14].mean()*100:.2f}')
    fut = y[y.group.isin(['Nifty Bank', 'Nifty Financial Services'])]
    print(f'   futures-tradeable part (Bank/FinServ): {len(fut)} trades')
    qa = qmt(y.qn.values, np.sign(y.signal.values) * y.vsn.values - bw.COST_INDEX)
    a0, t0 = qa.mean(), bw.tstat(qa)
    # PL1 on index: permute signals within quarter among SEC BIG triggers that have index data
    s = it.signal.values; qn = it.qn.values
    gq = [np.where(qn == k)[0] for k in np.unique(qn)]
    pm3, pt3 = [], []
    for _ in range(NDRAW):
        ps = s.copy()
        for idx in gq:
            ps[idx] = s[rng.permutation(idx)]
        mk = np.abs(ps) > 0.03
        qq = qmt(qn[mk], np.sign(ps[mk]) * it.vsn.values[mk] - bw.COST_INDEX)
        pm3.append(qq.mean()); pt3.append(bw.tstat(qq))
    pm3, pt3 = np.array(pm3), np.array(pt3)
    print(f'   PL1 permutation (index): placebo mean {np.nanmean(pm3)*100:.2f}%, share >= actual mean {np.nanmean(pm3 >= a0):.3f}, share >= actual t {np.nanmean(pt3 >= t0):.3f}')


if __name__ == '__main__':
    main()
