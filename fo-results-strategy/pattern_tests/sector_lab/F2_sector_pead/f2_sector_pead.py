#!/usr/bin/env python3
"""
F2  Sector-level post-results drift and sector rotation by results.
=====================================================================

PRE-REGISTRATION (written before any outcome was computed; nothing below
was added after seeing results unless marked "ADDED AFTER" and counted).

Universe / timing conventions
-----------------------------
* Trades only in F&O stocks (events.in_fo True for that quarter; the two
  blank in_fo values, RELIANCE qn9 and VEDL qn20, are set True because the
  same stock is F&O in the neighbouring quarters).
* "Sector" groupings:
    SEC  = events.sector_index, excluding "Nifty 500" (= no matching sector)
           -> 17 groups; each has a tradable-ish index (the index itself).
    PEER = events.peer_group (9 groups: Banks, NBFCs, Insurers, Metals,
           Real estate, FMCG, IT services, Pharma, Consumer brands).
* Reaction excess of a stock = its close-to-close return on its reaction
  day (i_react) minus the Nifty 50 return that day. It becomes public at
  the reaction-day close.
* Running sector score S(g,q,t) = mean reaction excess of the F&O stocks of
  group g, quarter q, whose reaction day <= t; defined only when n >= 3.
* Holding returns are compounded daily close-to-close returns. A blank
  return (no trade) is set to 0 inside the product because the next
  available return already spans the missing session(s). Index holding
  returns = close(exit)/close(entry) - 1; a trade on an index with no data
  at entry/exit is dropped (India Defence/Digital/Manufacturing start late).
* Costs: 0.17% per stock round trip; an equal-weight stock basket costs
  0.17%. Nifty futures hedge +0.02%. Sector-index trades: Nifty Bank and
  Nifty Financial Services have futures (0.02%); every other sector index
  must be replicated with a basket of stock futures (0.17%). Same rule for
  the hedge cost of the "minus sector" measurement of stock trades.
* Shorts: sign of the gross return flipped, same costs.
* Unit of evidence: the results quarter (A) / the rebalance (B).
  t across quarters = mean of quarter averages / (sd / sqrt(n quarters)).

Family A1  running sector score -> holding-period trade      (60 variants)
------------------------------------------------------------------------
Trigger: for each group g and season q, the FIRST session t (scanned over
reaction sessions in time order) at whose close n >= 3 and
    LONG : S >= +T      SHORT: S <= -T,     T in {2%, 3%}.
At most one long and one short trigger per (g, q). Decision = close of t,
entry at that close, exit at the close of t+H, H in {5, 10, 20} sessions.
Instruments:
    REP    equal-weight basket of g's F&O stocks that already reacted (<= t)
    NOTREP equal-weight basket of g's F&O stocks of quarter q that have NOT
           reacted yet (> t); needs >= 2 stocks
    IDX    the sector index itself (SEC grouping only)
Count: SEC 2 T x 2 sides x 3 instr x 3 H = 36 ; PEER 2 x 2 x 2 x 3 = 24.

Family A2  running sector score -> the user's 3-day window   (8 variants)
------------------------------------------------------------------------
For every F&O event e (stock not yet reported), at its cutoff close
(i_cut): score of e's group from F&O peers with reaction day <= i_cut
(n >= 3). LONG if S >= +T, SHORT if S <= -T, T in {2%, 3%}. Buy at the
cutoff close, sell at the Day+1 close; outcome = three_day (sum of the 3
daily returns, the user's definition), hedged = three_day - nifty_3d.
Count: 2 groupings x 2 T x 2 sides = 8.

Family B  season-end sector rotation (SEC grouping)          (48 variants)
------------------------------------------------------------------------
Rebalance date R80(q): first session at whose close >= 80% of quarter q's
F&O events in the 17 SEC groups have had their reaction day. Common date
for all sectors -> ranking is a same-date ranking (allowed).
Eligible sector: >= 3 reported F&O stocks AND >= 3 non-blank pat_yoy AND
>= 3 non-blank sales_yoy among them.
Scores (higher = better):
    S1 mean reaction excess vs Nifty (reported F&O stocks)
    S2 median pat_yoy   (reported F&O stocks)
    S3 median sales_yoy (reported F&O stocks)
    S4 composite = mean of the same-date ranks of S1, S2, S3
Portfolio: top 3 eligible sectors (long) and bottom 3.
Instruments: IDX sector index ; BSK equal-weight basket of the sector's F&O
stocks of quarter q (each sector weighted equally).
Hold: H20, H40, NEXT (until R80 of the next season).
Legs: TOP3 (long top 3, minus Nifty) ; SPREAD (top 3 minus bottom 3).
Count: 4 scores x 2 instr x 3 holds x 2 legs = 48.

TOTAL PRE-REGISTERED VARIANTS: 60 + 8 + 48 = 116.

Placebos (run for every variant; promising requires clearly worse chance):
    A-P1 random peers : within each quarter permute the group labels among
         F&O events (group sizes kept), rerun the identical rule. 400 reps.
    A-P2 random dates : each actual trade (same group, season, side,
         instrument, H) moved to a uniformly random session of the same
         group-season where the instrument is defined (n reported >= 3;
         NOTREP needs >= 2 unreported). 400 reps. Tests the timing signal.
    B-P  permutation  : shuffle the score across eligible sectors on each
         rebalance date. 2000 reps.
    p = share of placebo runs whose mean-of-quarter hedged net >= actual.

Robustness checks, ONLY for variants that pass the promising screen
(counted separately, they cannot add new candidates):
    R1 one-session delay: enter at close of t+1, exit close t+1+H.
    R2 (A1 REP only) drop stocks whose own reaction excess > +4% (the known
       individual-stock edge) from the basket.
    R3 (B only) rebalance at the first session after the regulatory deadline
       (quarter end + 45 days; +60 days for the March quarter).

"Promising" = hedged (minus Nifty) average after costs > 0 in BOTH qn 0..13
and qn 14..21, |t across quarters| >= 2.5, >= 30 trades, and placebo
p <= 0.05 (both A-P1 and A-P2 for A1; A-P1 for A2; B-P for B).
"""
import sys
sys.path.append('/root/.local/lib/python3.11/site-packages')   # pandas' dateutil lives here
import os, time
import numpy as np
import pandas as pd
from concurrent.futures import ProcessPoolExecutor

BASE = os.environ.get('SECTOR_LAB', 'sector_lab') + ''
DATA = BASE + '/data'
OUT = BASE + '/F2_sector_pead'
NREP_A = 400
NREP_B = 2000
SEED = 20261007

C_STK = 0.0017
C_NF = 0.0002
FUT_INDICES = {'Nifty 50', 'Nifty Bank', 'Nifty Financial Services', 'Nifty Midcap Select'}

TS = (0.02, 0.03)
HS = (5, 10, 20)

# ---------------------------------------------------------------- load
ses = pd.read_csv(DATA + '/sessions.csv')
R = pd.read_csv(DATA + '/returns.csv', index_col=0)
IX = pd.read_csv(DATA + '/index_close.csv', index_col=0)
EV = pd.read_csv(DATA + '/events.csv')
N = len(ses)
assert list(R.index) == list(ses.day) and list(IX.index) == list(ses.day)
assert (ses.i.values == np.arange(N)).all()

EV['in_fo'] = EV['in_fo'].map({True: True, False: False, 'True': True, 'False': False})
miss = EV['in_fo'].isna()
EV.loc[miss, 'in_fo'] = True        # RELIANCE qn9, VEDL qn20 (F&O in neighbour quarters)
EV['in_fo'] = EV['in_fo'].astype(bool)

syms = list(R.columns)
col = {s: j for j, s in enumerate(syms)}
Rv = R.values.astype(float)
Rz = np.nan_to_num(Rv, nan=0.0)
L = np.cumsum(np.log1p(Rz), axis=0)          # hold(i0,i1) = exp(L[i1]-L[i0]) - 1
IXv = IX.values.astype(float)
kix = {c: k for k, c in enumerate(IX.columns)}
K50 = kix['Nifty 50']
n50ret = np.r_[np.nan, IXv[1:, K50] / IXv[:-1, K50] - 1]


def hold_stk(cols, i0, i1):
    return np.exp(L[i1, cols] - L[i0, cols]) - 1.0


def hold_ix(k, i0, i1):
    return IXv[i1, k] / IXv[i0, k] - 1.0


def ix_cost(name):
    return C_NF if name in FUT_INDICES else C_STK


# event arrays
ev_q = EV.qn.values.astype(int)
ev_sc = EV.symbol.map(col).values.astype(int)
ev_react = EV.i_react.values.astype(int)
ev_cut = EV.i_cut.values.astype(int)
ev_fo = EV.in_fo.values
ev_x = Rv[ev_react, ev_sc] - n50ret[ev_react]
ev_ksec = EV.sector_index.map(kix).values.astype(int)
ev_kcost = np.array([ix_cost(s) for s in EV.sector_index])
lab_SEC = np.where(EV.sector_index.values == 'Nifty 500', '', EV.sector_index.values).astype(object)
lab_PEER = EV.peer_group.fillna('').values.astype(object)
td3 = EV.three_day.values
n3 = EV.nifty_3d.values
s3 = EV.sector_3d.values
pat = EV.pat_yoy.values
sal = EV.sales_yoy.values


def data_checks():
    lines = []
    lines.append(f'sessions {N}  {ses.day.iloc[0]} .. {ses.day.iloc[-1]}')
    lines.append(f'returns {R.shape}  index_close {IX.shape}  events {EV.shape}')
    lines.append(f'in_fo blanks filled True: {int(miss.sum())}')
    lines.append(f'F&O events {int(ev_fo.sum())}; reaction excess non-blank {int(np.isfinite(ev_x[ev_fo]).sum())}')
    used = sorted(set(EV.sector_index)) + ['Nifty 50']
    for n in used:
        c = IX[n]
        sub = c[c.index >= '2021-01-01']
        lines.append(f'  index {n:28s} first {c.first_valid_index()}  blanks since 2021 {int(sub.isna().sum())}'
                     f'  first valid since 2021 {sub.first_valid_index()}')
    g = EV[EV.in_fo].groupby('qn')
    lines.append('F&O events per qn: ' + ' '.join(str(v) for v in g.size().values))
    # exit-day blanks would truncate a spanning return; count among stock-days used later is reported per run
    return '\n'.join(lines)


# ---------------------------------------------------------------- family A
def group_members(lab):
    """dict (q, g) -> event indices sorted by reaction session (F&O only, non-blank excess)."""
    out = {}
    ok = ev_fo & (lab != '') & np.isfinite(ev_x)
    for q in range(22):
        idx = np.where(ok & (ev_q == q))[0]
        for g in np.unique(lab[idx]):
            e = idx[lab[idx] == g]
            e = e[np.argsort(ev_react[e], kind='stable')]
            out[(q, g)] = e
    return out


def basket_stats(e_set, t0, t1):
    """gross basket, nifty, minus-sector gross (avg), hedge cost for sector."""
    cols = ev_sc[e_set]
    r = hold_stk(cols, t0, t1)
    secr = IXv[t1, ev_ksec[e_set]] / IXv[t0, ev_ksec[e_set]] - 1
    d = r - secr
    return float(r.mean()), float(np.nanmean(d)) if np.isfinite(d).any() else np.nan, float(ev_kcost[e_set].mean())


def engine_A(lab, grouping, delay=0, drop_big=False):
    """Returns list of A1 trade tuples and A2 trade tuples."""
    mem = group_members(lab)
    insts = ('REP', 'NOTREP', 'IDX') if grouping == 'SEC' else ('REP', 'NOTREP')
    a1, a2 = [], []
    for (q, g), e in mem.items():
        r = ev_react[e]
        x = ev_x[e]
        cum = np.cumsum(x)
        us, first_pos = np.unique(r, return_index=True)
        last_pos = np.r_[first_pos[1:] - 1, len(r) - 1]
        n_at = last_pos + 1
        score = cum[last_pos] / n_at
        for T in TS:
            for side in (1, -1):
                ok = (n_at >= 3) & (side * score >= T)
                if not ok.any():
                    continue
                k = int(np.argmax(ok))
                t = int(us[k])
                for inst in insts:
                    if inst == 'REP':
                        bk = e[r <= t]
                        if drop_big:
                            bk = bk[ev_x[bk] <= 0.04]
                            if len(bk) == 0:
                                continue
                    elif inst == 'NOTREP':
                        bk = e[r > t]
                        if len(bk) < 2:
                            continue
                    for H in HS:
                        t0 = t + delay
                        t1 = t0 + H
                        if t1 > N - 1:
                            continue
                        nf = hold_ix(K50, t0, t1)
                        if inst == 'IDX':
                            gr = hold_ix(kix[g], t0, t1)
                            if not np.isfinite(gr):
                                continue
                            c = ix_cost(g)
                            dsec, csec, nleg = np.nan, np.nan, 0
                        else:
                            gr, dsec, csec = basket_stats(bk, t0, t1)
                            c = C_STK
                            nleg = len(bk)
                        raw = side * gr - c
                        vsn = side * (gr - nf) - c - C_NF
                        vss = side * dsec - c - csec if np.isfinite(dsec) else np.nan
                        a1.append((grouping, T, side, inst, H, q, g, t, nleg, float(gr), float(nf), raw, vsn, vss, float(score[k]), int(n_at[k])))
        # A2: each member event at its cutoff (only peers already reacted by cutoff)
        # all F&O events of the group incl. those with blank excess are candidates
    # A2 loop over all F&O events with a label
    okev = np.where(ev_fo & (lab != '') & np.isfinite(td3))[0]
    for i in okev:
        e = mem.get((ev_q[i], lab[i]))
        if e is None:
            continue
        r = ev_react[e]
        kk = np.searchsorted(r, ev_cut[i], side='right')   # peers reacted by cutoff close
        if kk < 3:
            continue
        sc = ev_x[e[:kk]].mean()
        for T in TS:
            for side in (1, -1):
                if side * sc >= T:
                    raw = side * td3[i] - C_STK
                    vsn = side * (td3[i] - n3[i]) - C_STK - C_NF
                    vss = side * (td3[i] - s3[i]) - C_STK - ev_kcost[i] if np.isfinite(s3[i]) else np.nan
                    a2.append((grouping, T, side, 'STOCK3D', 3, int(ev_q[i]), lab[i], int(ev_cut[i]), 1, float(td3[i]), float(n3[i]), raw, vsn, vss, float(sc), int(kk)))
    return a1, a2


A_COLS = ['grouping', 'T', 'side', 'inst', 'H', 'q', 'g', 't', 'nleg', 'gross', 'nifty', 'raw_net', 'vsn_net', 'vss_net', 'score', 'n_rep']
VKEY = ['grouping', 'T', 'side', 'inst', 'H']


def tstat(v):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if len(v) < 3 or v.std(ddof=1) == 0:
        return np.nan
    return v.mean() / (v.std(ddof=1) / np.sqrt(len(v)))


def summarize(df, key, unit='q', three_day=False):
    rows = []
    for kv, d in df.groupby(key, sort=False):
        qa = d.groupby(unit).vsn_net.mean()
        qr = d.groupby(unit).raw_net.mean()
        da = d.groupby('t').vsn_net.mean()
        f14 = qa[qa.index <= 13]
        l8 = qa[qa.index >= 14]
        row = dict(zip(key, kv if isinstance(kv, tuple) else (kv,)))
        row.update(trades=len(d), legs=int(d.nleg.sum()),
                   avg_raw_net=d.raw_net.mean() * 100, avg_vsn_net=d.vsn_net.mean() * 100,
                   avg_vss_net=d.vss_net.mean() * 100, pct_win=(d.vsn_net > 0).mean() * 100,
                   nq=len(qa), perq_avg=qa.mean() * 100, t_q=tstat(qa.values),
                   t_dates=tstat(da.values), t_trades=tstat(d.vsn_net.values),
                   first14=f14.mean() * 100 if len(f14) else np.nan, nq14=len(f14),
                   last8=l8.mean() * 100 if len(l8) else np.nan, nq8=len(l8),
                   q_pos=f'{int((qa > 0).sum())} of {len(qa)}')
        if three_day:
            row['q_ge2_raw'] = f'{int((qr >= 0.02).sum())} of {len(qr)}'
            row['max_q_raw'] = qr.max() * 100
        rows.append(row)
    return pd.DataFrame(rows)


def stat_by_variant(df):
    """mean of quarter averages of vsn_net per variant -> dict."""
    if len(df) == 0:
        return {}
    s = df.groupby(VKEY + ['q']).vsn_net.mean().groupby(level=list(range(len(VKEY)))).mean()
    return s.to_dict()


def _p1_worker(args):
    seed, nrep = args
    rng = np.random.default_rng(seed)
    res = []
    for _ in range(nrep):
        out = {}
        for grouping, lab0 in (('SEC', lab_SEC), ('PEER', lab_PEER)):
            lab = lab0.copy()
            for q in range(22):
                idx = np.where(ev_fo & (ev_q == q))[0]
                lab[idx] = lab0[idx][rng.permutation(len(idx))]
            a1, a2 = engine_A(lab, grouping)
            d = pd.DataFrame(a1 + a2, columns=A_COLS)
            out.update(stat_by_variant(d))
        res.append(out)
    return res


def placebo_P2(trades, lab, grouping, rng, nrep):
    """random dates within the same group-season for each actual A1 trade."""
    mem = group_members(lab)
    stats = {}
    for kv, d in trades.groupby(VKEY, sort=False):
        grouping_, T, side, inst, H = kv
        # eligible session ranges per trade
        rngs = []
        for _, tr in d.iterrows():
            e = mem[(tr.q, tr.g)]
            r = ev_react[e]
            lo = int(r[2])                       # 3rd reporter's reaction session
            if inst == 'NOTREP':
                hi = int(r[-2]) - 1             # still >= 2 unreported at close
            else:
                hi = int(r[-1])
            hi = min(hi, N - 1 - H)
            if hi < lo:
                hi = lo
            rngs.append((e, r, lo, hi, tr.q, tr.g))
        vals = np.empty(nrep)
        for rep in range(nrep):
            qv = {}
            for (e, r, lo, hi, q, g) in rngs:
                t = int(rng.integers(lo, hi + 1))
                t1 = t + H
                if t1 > N - 1:
                    continue
                nf = hold_ix(K50, t, t1)
                if inst == 'IDX':
                    gr = hold_ix(kix[g], t, t1)
                    if not np.isfinite(gr):
                        continue
                    c = ix_cost(g)
                else:
                    bk = e[r <= t] if inst == 'REP' else e[r > t]
                    if len(bk) == 0:
                        continue
                    gr = hold_stk(ev_sc[bk], t, t1).mean()
                    c = C_STK
                qv.setdefault(q, []).append(side * (gr - nf) - c - C_NF)
            vals[rep] = np.mean([np.mean(v) for v in qv.values()]) if qv else np.nan
        stats[kv] = vals
    return stats


# ---------------------------------------------------------------- family B
def rebalance_dates(mode='R80'):
    okfo = ev_fo & (lab_SEC != '')
    out = {}
    for q in range(22):
        if mode == 'R80':
            r = np.sort(ev_react[okfo & (ev_q == q)])
            k = int(np.ceil(0.8 * len(r))) - 1
            out[q] = int(r[k])
        else:   # deadline: quarter end + 45 days (+60 for March quarter); first session after
            qe = pd.Timestamp(EV.loc[ev_q == q, 'quarter_end'].iloc[0])
            dl = qe + pd.Timedelta(days=60 if qe.month == 3 else 45)
            out[q] = int(np.searchsorted(pd.to_datetime(ses.day).values, np.datetime64(dl), side='right'))
    return out


SC_NAMES = ('S1_react', 'S2_patyoy', 'S3_salesyoy', 'S4_composite')


def rank01(v):
    o = np.argsort(np.argsort(v, kind='stable'), kind='stable')
    return o / (len(v) - 1)


def build_B(mode='R80', delay=0):
    """per rebalance: eligible sectors, score matrix, forward returns per instrument/hold."""
    rb = rebalance_dates(mode)
    okfo = ev_fo & (lab_SEC != '')
    recs = []
    for q in range(22):
        t = rb[q] + delay
        sects, S, members = [], [], []
        for g in sorted(set(lab_SEC[okfo & (ev_q == q)])):
            e_all = np.where(okfo & (ev_q == q) & (lab_SEC == g))[0]
            rep = e_all[(ev_react[e_all] <= rb[q]) & np.isfinite(ev_x[e_all])]
            p = pat[rep][np.isfinite(pat[rep])]
            s = sal[rep][np.isfinite(sal[rep])]
            if len(rep) < 3 or len(p) < 3 or len(s) < 3:
                continue
            sects.append(g)
            S.append([ev_x[rep].mean(), np.median(p), np.median(s)])
            members.append(e_all)
        S = np.array(S)
        comp = (rank01(S[:, 0]) + rank01(S[:, 1]) + rank01(S[:, 2])) / 3
        S = np.c_[S, comp]
        holds = {}
        for hn in ('H20', 'H40', 'NEXT'):
            if hn == 'NEXT':
                if q + 1 not in rb:
                    continue
                t1 = rb[q + 1] + delay
            else:
                t1 = t + int(hn[1:])
            if t1 > N - 1:
                continue
            nf = hold_ix(K50, t, t1)
            idx_r = np.array([hold_ix(kix[g], t, t1) for g in sects])
            idx_c = np.array([ix_cost(g) for g in sects])
            bsk_r = np.array([hold_stk(ev_sc[m], t, t1).mean() for m in members])
            bsk_d = np.array([np.nanmean(hold_stk(ev_sc[m], t, t1) - idx_r[j]) for j, m in enumerate(members)])
            bsk_cs = idx_c.copy()
            holds[hn] = dict(nf=nf, IDX=(idx_r, idx_c), BSK=(bsk_r, np.full(len(sects), C_STK)), BSKd=(bsk_d, bsk_cs))
        recs.append(dict(q=q, t=t, sects=sects, S=S, holds=holds))
    return recs


def legs_from_order(order, hd, inst):
    """order: sector positions sorted by score descending; returns dict of leg values."""
    r, c = hd[inst]
    nf = hd['nf']
    top, bot = order[:3], order[-3:]
    # drop sectors with no index data (IDX) from a leg
    tv, bv = r[top], r[bot]
    tm, bm = np.isfinite(tv), np.isfinite(bv)
    if tm.sum() == 0 or bm.sum() == 0:
        return None
    tg, bg = tv[tm].mean(), bv[bm].mean()
    tc, bc = c[top][tm].mean(), c[bot][bm].mean()
    out = dict(TOP3_raw=tg - tc, TOP3_vsn=tg - nf - tc - C_NF, SPREAD=tg - bg - tc - bc,
               top_gross=tg, bot_gross=bg, nifty=nf)
    if inst == 'BSK':
        dv, dc = hd['BSKd']
        dd = dv[top]
        out['TOP3_vss'] = np.nanmean(dd) - C_STK - dc[top].mean() if np.isfinite(dd).any() else np.nan
    else:
        out['TOP3_vss'] = np.nan
    return out


def run_B(recs, perm_rng=None):
    rows = []
    for rec in recs:
        n = len(rec['sects'])
        if n < 6:
            continue
        for si, sn in enumerate(SC_NAMES):
            sc = rec['S'][:, si]
            if perm_rng is not None:
                sc = sc[perm_rng.permutation(n)]
            order = np.argsort(-sc, kind='stable')
            for hn, hd in rec['holds'].items():
                for inst in ('IDX', 'BSK'):
                    lv = legs_from_order(order, hd, inst)
                    if lv is None:
                        continue
                    base = dict(score=sn, inst=inst, H=hn, q=rec['q'], t=rec['t'], n_sect=n,
                                top=';'.join(rec['sects'][j] for j in order[:3]),
                                bot=';'.join(rec['sects'][j] for j in order[-3:]))
                    rows.append({**base, 'leg': 'TOP3', 'nleg': 3, 'raw_net': lv['TOP3_raw'], 'vsn_net': lv['TOP3_vsn'],
                                 'vss_net': lv['TOP3_vss'], 'gross': lv['top_gross'], 'nifty': lv['nifty']})
                    rows.append({**base, 'leg': 'SPREAD', 'nleg': 6, 'raw_net': lv['SPREAD'], 'vsn_net': lv['SPREAD'],
                                 'vss_net': np.nan, 'gross': lv['top_gross'] - lv['bot_gross'], 'nifty': lv['nifty']})
    return pd.DataFrame(rows)


BKEY = ['score', 'inst', 'H', 'leg']


def _pB_worker(args):
    seed, nrep, recs = args
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(nrep):
        d = run_B(recs, perm_rng=rng)
        out.append(d.groupby(BKEY).vsn_net.mean().to_dict())
    return out


# ---------------------------------------------------------------- main
def main():
    t0 = time.time()
    chk = data_checks()
    print(chk)
    with open(OUT + '/data_checks.txt', 'w') as f:
        f.write(chk + '\n')

    # ---------- A actual
    a1s, a2s = engine_A(lab_SEC, 'SEC')
    b1, b2 = engine_A(lab_PEER, 'PEER')
    A1 = pd.DataFrame(a1s + b1, columns=A_COLS)
    A2 = pd.DataFrame(a2s + b2, columns=A_COLS)
    A1.to_csv(OUT + '/A1_trades.csv', index=False)
    A2.to_csv(OUT + '/A2_trades.csv', index=False)
    sA1 = summarize(A1, VKEY)
    sA2 = summarize(A2, VKEY, three_day=True)
    print(f'A1 variants with trades {len(sA1)} (pre-registered 60); A2 {len(sA2)} (8)   {time.time()-t0:.0f}s')

    # ---------- A placebo P1 (random peers)
    nw = 4
    per = NREP_A // nw
    with ProcessPoolExecutor(nw) as ex:
        parts = list(ex.map(_p1_worker, [(SEED + w, per) for w in range(nw)]))
    p1 = [r for p in parts for r in p]
    print(f'P1 done {time.time()-t0:.0f}s')
    for s in (sA1, sA2):
        pv, pm, p95 = [], [], []
        for _, row in s.iterrows():
            kv = tuple(row[k] for k in VKEY)
            act = row.perq_avg / 100
            vals = np.array([r.get(kv, np.nan) for r in p1], float)
            vals = vals[np.isfinite(vals)]
            pv.append((vals >= act).mean() if len(vals) else np.nan)
            pm.append(vals.mean() * 100 if len(vals) else np.nan)
            p95.append(np.percentile(vals, 95) * 100 if len(vals) else np.nan)
        s['P1_mean'] = pm
        s['P1_95pct'] = p95
        s['P1_p'] = pv

    # ---------- A placebo P2 (random dates), A1 only
    rng = np.random.default_rng(SEED + 99)
    p2 = {}
    p2.update(placebo_P2(A1[A1.grouping == 'SEC'], lab_SEC, 'SEC', rng, NREP_A))
    p2.update(placebo_P2(A1[A1.grouping == 'PEER'], lab_PEER, 'PEER', rng, NREP_A))
    pv, pm = [], []
    for _, row in sA1.iterrows():
        kv = tuple(row[k] for k in VKEY)
        vals = p2[kv]
        vals = vals[np.isfinite(vals)]
        pv.append((vals >= row.perq_avg / 100).mean())
        pm.append(vals.mean() * 100)
    sA1['P2_mean'] = pm
    sA1['P2_p'] = pv
    print(f'P2 done {time.time()-t0:.0f}s')

    # ---------- B
    recs = build_B('R80')
    B = run_B(recs)
    B.to_csv(OUT + '/B_trades.csv', index=False)
    sB = summarize(B, BKEY, unit='q')
    sB['legs'] = sB['legs']  # sector-legs count
    with ProcessPoolExecutor(nw) as ex:
        parts = list(ex.map(_pB_worker, [(SEED + 500 + w, NREP_B // nw, recs) for w in range(nw)]))
    pb = [r for p in parts for r in p]
    pv, pm, p95 = [], [], []
    for _, row in sB.iterrows():
        kv = tuple(row[k] for k in BKEY)
        vals = np.array([r.get(kv, np.nan) for r in pb], float)
        pv.append((vals >= row.perq_avg / 100).mean())
        pm.append(vals.mean() * 100)
        p95.append(np.percentile(vals, 95) * 100)
    sB['P_mean'] = pm
    sB['P_95pct'] = p95
    sB['P_p'] = pv
    print(f'B done {time.time()-t0:.0f}s; rebalances {B.q.nunique()}, eligible sectors per rebalance '
          f'{[len(r["sects"]) for r in recs]}')

    # ---------- promising screen
    def screen(s, pcols):
        ok = (s.first14 > 0) & (s.last8 > 0) & (s.t_q.abs() >= 2.5) & (s.trades >= 30)
        for c in pcols:
            ok &= s[c] <= 0.05
        return ok
    sA1['promising'] = screen(sA1, ['P1_p', 'P2_p'])
    sA2['promising'] = screen(sA2, ['P1_p'])
    # B: a rebalance portfolio is the trade; sector legs = 3 per rebalance, require >= 30 sector legs
    sB['sector_legs'] = sB['trades'] * 3
    okB = (sB.first14 > 0) & (sB.last8 > 0) & (sB.t_q.abs() >= 2.5) & (sB.sector_legs >= 30) & (sB.P_p <= 0.05)
    sB['promising'] = okB

    sA1.to_csv(OUT + '/A1_summary.csv', index=False)
    sA2.to_csv(OUT + '/A2_summary.csv', index=False)
    sB.to_csv(OUT + '/B_summary.csv', index=False)

    pd.set_option('display.width', 250)
    pd.set_option('display.max_columns', 40)
    fmt = lambda s, cols: s[cols].round(3).to_string()
    c1 = VKEY + ['trades', 'legs', 'avg_raw_net', 'avg_vsn_net', 'avg_vss_net', 'pct_win', 'nq', 'perq_avg', 't_q', 't_dates',
                 'first14', 'last8', 'q_pos', 'P1_mean', 'P1_p', 'P2_mean', 'P2_p', 'promising']
    print('\n=== A1 (holding-period) ===')
    print(fmt(sA1, c1))
    c2 = VKEY + ['trades', 'avg_raw_net', 'avg_vsn_net', 'avg_vss_net', 'pct_win', 'nq', 'perq_avg', 't_q', 't_dates',
                 'first14', 'last8', 'q_pos', 'q_ge2_raw', 'max_q_raw', 'P1_mean', 'P1_p', 'promising']
    print('\n=== A2 (3-day window) ===')
    print(fmt(sA2, c2))
    c3 = BKEY + ['trades', 'avg_raw_net', 'avg_vsn_net', 'avg_vss_net', 'pct_win', 'nq', 'perq_avg', 't_q', 'first14', 'last8',
                 'q_pos', 'P_mean', 'P_95pct', 'P_p', 'promising']
    print('\n=== B (rotation) ===')
    print(fmt(sB, c3))
    nvar = len(sA1) + len(sA2) + len(sB)
    print(f'\nvariants evaluated {nvar} (pre-registered 116); promising A1 {int(sA1.promising.sum())} '
          f'A2 {int(sA2.promising.sum())} B {int(sB.promising.sum())}   {time.time()-t0:.0f}s')


if __name__ == '__main__':
    main()
