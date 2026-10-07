"""
F1  BELLWETHER SPILLOVER TO PEERS THAT HAVE NOT REPORTED YET  (intra-industry information transfer)
=====================================================================================================
PRE-REGISTRATION (written before looking at any outcome; nothing below was added after seeing results)

Signal ("bellwether reaction"):
    excess reaction of a reporter = its reaction-day close-to-close return (events.move)
                                    minus the Nifty 50 return of the same session.
    reaction_day = result session for before/during-market results, next session for after-close
    (and the next session for weekend/holiday results). It is known at the reaction-day CLOSE = decision time d.
    If several group members of the bellwether set react on the same session, the signal is their simple mean.

Peer groups (G) -- 3 definitions:
    PG  = events.peer_group (9 groups, blank excluded)
    IND = events.industry   (NSE industry, 49 groups)
    SEC = events.sector_index (17 Nifty sector indices; "Nifty 500" = no sector -> excluded)

Bellwether definitions (BW) -- 3:
    FIRST = the group member(s) with the earliest reaction session of the season (quarter qn).
    BIG   = the earliest-reacting member among the group's 3 largest members, size = the member's mcap in the
            PREVIOUS quarter's events row (known before the season; qn 0 uses its own row = small look-ahead in
            the ordering only). Group-quarters where fewer than 3 members have a known size are skipped.
            (For groups with <= 3 members BIG == FIRST.)
    ALL   = every reaction session of every group member is a trigger (generalised information transfer;
            several triggers per group and season, trades may overlap). Only spillover horizons (no TW/OWN3,
            because "average reaction of already-reported peers -> own 3-day window" was already tested).

Peers traded: members of the same group, same quarter, with in_fo == True in that quarter, whose results
are NOT public at d (their own i_react > d). The bellwether itself and members reacting on d are never peers.

Horizons (H):
    H1, H3, H5 = hold 1/3/5 sessions from the close of d; only peers whose own cutoff i_cut >= d + h,
                 i.e. the trade ends at or before the peer's own cutoff close (never overlaps own result window).
    PC   = from the close of d to the close of the peer's own cutoff (requires i_cut > d).  (spillover only)
    TW   = from the close of d THROUGH the peer's own 3-day window to its Day+1 close (requires i_cut >= d).
           (FIRST and BIG only)
    OWN3 = the peer's own 3-day results window (user's definition: sum of Day-1, Result day, Day+1 daily
           returns; entry at the peer's cutoff close, exit at Day+1 close), traded only if the bellwether
           reaction was known by the peer's cutoff close (d <= i_cut). (FIRST and BIG only)

Thresholds (T): |signal| > 3% and > 5% (absolute, fixed in advance; no ranking of any kind).

Legs:
    L  = buy peers after a strong bellwether (signal > +T)
    S  = short peers (stock futures) after a weak bellwether (signal < -T)
    LS = both, pooled (continuation). Each leg is read TWO-SIDED: a significantly negative continuation
         number means "reversal". Reversal returns are computed explicitly (gross sign flipped, costs re-applied).

Index test (the "reverse" question: does the sector index itself continue?):
    SEC groups, BW in {FIRST, BIG, ALL}, T in {3%, 5%}, h in {1,3,5}: return of the group's own Nifty sector
    index minus Nifty 50 over h sessions after the close of d, signed by the bellwether sign (LS only).
    Universe U_all = every sector index with data (diagnostic; not tradeable with index futures except Bank/FinServ)
    Universe U_fut = Nifty Bank and Nifty Financial Services only (tradeable with index futures).
    Cost 0.02% index future + 0.02% Nifty future.

Continuous slope test (same-date-safe, no ranking): per quarter OLS slope of the peer's hedged return (minus Nifty)
    on the bellwether signal (all triggers, no threshold), averaged across quarters, t across quarters.
    G x BW{FIRST,BIG} x H{PC, OWN3}.

COUNT OF PRE-REGISTERED TWO-SIDED TESTS:
    peer trades : 3 G x [FIRST 6 H + BIG 6 H + ALL 4 H] x 2 T x 3 legs = 3 x 16 x 2 x 3 = 288
    index       : 3 BW x 2 T x 3 h x 2 universes (LS)                  = 36
    slopes      : 3 G x 2 BW x 2 H                                     = 12
    TOTAL = 336 two-sided tests (= 672 one-directional rules if continuation and reversal are counted apart).
    Expected by luck alone at |t| >= 2.5 (about p = 0.02 two-sided with ~20 quarters): about 6-7 tests.

Measurement (every trade): raw stock return; minus Nifty 50 over the same window; minus the stock's own sector
    index (events.sector_index; Nifty 500 when no sector, or when the sector index has no data yet, e.g. India
    Digital before Dec-2021 / India Manufacturing before Aug-2021) over the same window.
    Holding returns are compounded from adjusted daily returns; a blank (no trade) day is skipped, so the next
    return spans 2 sessions (counted and reported). OWN3 keeps the user's sum-of-3-daily-returns definition.
    Costs: 0.17% per stock round trip (raw); 0.19% for hedged (stock + Nifty future). The minus-sector number uses
    the same 0.19%, but only Bank / FinServ / Midcap Select have index futures; other sector hedges need a
    basket of stock futures (more cost) -- treat minus-sector as a diagnostic.
Statistics: unit = quarter (equal weight per trade inside a quarter, then mean across quarters, t across
    quarters); also t clustered by entry date. First 14 quarters (qn 0..13) vs last 8 (qn 14..21);
    quarters positive; for OWN3 also quarters with raw average >= +2%.
Promising = hedged (minus Nifty) average after costs > 0 in BOTH halves (same sign as the claim),
    |t across quarters| >= 2.5, >= 30 trades, and the placebos (placebo.py) clearly worse.
Placebos (pre-registered, run in placebo.py on the screened candidates and on the top-|t| cells):
    PL1 signal permutation: within each quarter, permute the bellwether signals across the variant's triggers
        (keeps timing and peers, breaks which group got the news); 1000 draws.
    PL2 random non-peers: replace each trigger's true peers with the same number of random in_fo stocks from
        OTHER groups that satisfy the same not-yet-reported / horizon eligibility at the same date; 1000 draws.
"""
import sys
sys.path.append('/root/.local/lib/python3.11/site-packages')  # pandas deps live in user site (python3 -I hides it)
import os
import numpy as np
import pandas as pd

D = os.environ.get('SECTOR_LAB', 'sector_lab') + '/data/'
OUT = os.environ.get('SECTOR_LAB', 'sector_lab') + '/F1_bellwether/'

COST_RAW = 0.0017
COST_HEDGE = 0.0019
COST_INDEX = 0.0004
THRESHOLDS = [0.03, 0.05]
FIXED_H = [1, 3, 5]
GROUPINGS = {'PG': 'peer_group', 'IND': 'industry', 'SEC': 'sector_index'}
BW_DEFS = ['FIRST', 'BIG', 'ALL']
HORIZONS = {'FIRST': ['H1', 'H3', 'H5', 'PC', 'TW', 'OWN3'],
            'BIG': ['H1', 'H3', 'H5', 'PC', 'TW', 'OWN3'],
            'ALL': ['H1', 'H3', 'H5', 'PC']}
LEGS = ['L', 'S', 'LS']


# ----------------------------------------------------------------------------------------------- data
def load():
    ses = pd.read_csv(D + 'sessions.csv')
    R = pd.read_csv(D + 'returns.csv', index_col=0)
    IX = pd.read_csv(D + 'index_close.csv', index_col=0)
    INTRA = pd.read_csv(D + 'intraday.csv', index_col=0)
    ev = pd.read_csv(D + 'events.csv')
    assert (R.index.values == ses.day.values).all() and (IX.index.values == ses.day.values).all()
    assert not ev.duplicated(['symbol', 'qn']).any()
    ev['in_fo'] = ev['in_fo'].fillna(False).astype(bool)
    return ses, R, IX, INTRA, ev


class Px:
    """compounded holding returns from close of a to close of b"""

    def __init__(self, R, IX):
        self.syms = {s: j for j, s in enumerate(R.columns)}
        r = R.values.astype(float)
        self.nan = np.isnan(r)
        self.L = np.vstack([np.zeros((1, r.shape[1])), np.cumsum(np.log1p(np.where(self.nan, 0.0, r)), axis=0)])
        self.NC = np.vstack([np.zeros((1, r.shape[1])), np.cumsum(self.nan, axis=0)])
        # L[k] = sum of log returns of sessions 0..k-1 ; return from close a to close b = L[b+1]-L[a+1]
        self.ix = {c: IX[c].values.astype(float) for c in IX.columns}

    def stock(self, sym, a, b):
        j = self.syms[sym]
        a = np.asarray(a); b = np.asarray(b)
        ret = np.exp(self.L[b + 1, j] - self.L[a + 1, j]) - 1
        nblank = self.NC[b + 1, j] - self.NC[a + 1, j]
        return ret, nblank

    def index(self, name, a, b):
        c = self.ix[name]
        return c[np.asarray(b)] / c[np.asarray(a)] - 1

    def sector(self, name, a, b):
        """sector index return; falls back to Nifty 500 where the sector index has no data"""
        r = self.index(name, a, b) if name in self.ix else np.full(np.shape(a), np.nan)
        fb = self.index('Nifty 500', a, b)
        return np.where(np.isnan(r), fb, r)


# ----------------------------------------------------------------------------------------------- triggers
def build_triggers(ev, nifty_ret):
    """one row per (grouping, bw, qn, group, d) with the bellwether signal."""
    ev = ev.copy()
    ev['xreact'] = ev['move'] - nifty_ret[ev['i_react'].values]
    # previous-quarter size (known before the season)
    prev = ev[['symbol', 'qn', 'mcap']].copy(); prev['qn'] = prev['qn'] + 1
    ev = ev.merge(prev.rename(columns={'mcap': 'mcap_prev'}), on=['symbol', 'qn'], how='left')
    ev['size'] = np.where(ev['qn'] == 0, ev['mcap'], ev['mcap_prev'])
    rows = []
    for gname, col in GROUPINGS.items():
        sub = ev[ev[col].notna()]
        if gname == 'SEC':
            sub = sub[sub[col] != 'Nifty 500']
        for (qn, grp), m in sub.groupby(['qn', col]):
            if len(m) < 2:
                continue
            byd = m.groupby('i_react')
            # ALL
            for d, x in byd:
                rows.append(dict(G=gname, BW='ALL', qn=qn, group=grp, d=int(d), signal=x['xreact'].mean(),
                                 bw_syms='|'.join(x.symbol), n_members=len(m)))
            # FIRST
            d0 = m['i_react'].min(); x = m[m.i_react == d0]
            rows.append(dict(G=gname, BW='FIRST', qn=qn, group=grp, d=int(d0), signal=x['xreact'].mean(),
                             bw_syms='|'.join(x.symbol), n_members=len(m)))
            # BIG
            known = m[m['size'].notna()]
            if len(known) >= 3:
                top = known.nlargest(3, 'size')
                dB = top['i_react'].min(); x = top[top.i_react == dB]
                rows.append(dict(G=gname, BW='BIG', qn=qn, group=grp, d=int(dB), signal=x['xreact'].mean(),
                                 bw_syms='|'.join(x.symbol), n_members=len(m)))
    return pd.DataFrame(rows), ev


# ----------------------------------------------------------------------------------------------- peer trades
def build_trades(trig, ev, px):
    nifty = 'Nifty 50'
    out = []
    evg = {}
    for gname, col in GROUPINGS.items():
        evg[gname] = {k: v for k, v in ev[ev[col].notna()].groupby(['qn', col])}
    for t in trig.itertuples(index=False):
        m = evg[t.G][(t.qn, t.group)]
        peers = m[(m.in_fo) & (m.i_react > t.d) & (m.i_cut >= t.d)]
        if len(peers) == 0:
            continue
        for H in HORIZONS[t.BW]:
            if H.startswith('H'):
                h = int(H[1:])
                p = peers[peers.i_cut >= t.d + h]
                a = np.full(len(p), t.d); b = a + h
            elif H == 'PC':
                p = peers[peers.i_cut > t.d]
                a = np.full(len(p), t.d); b = p.i_cut.values
            elif H == 'TW':
                p = peers
                a = np.full(len(p), t.d); b = p.i_p1.values
            else:  # OWN3
                p = peers[peers.three_day.notna()]
                a = p.i_cut.values; b = p.i_p1.values
            if len(p) == 0:
                continue
            if H == 'OWN3':
                raw = p.three_day.values
                vsn = p.excess_nifty.values
                vss = p.excess_sector.values
                nbl = np.zeros(len(p))
            else:
                raw = np.empty(len(p)); nbl = np.empty(len(p)); sec = np.empty(len(p))
                for k, (sym, secname) in enumerate(zip(p.symbol.values, p.sector_index.values)):
                    raw[k], nbl[k] = px.stock(sym, a[k], b[k])
                    sec[k] = px.sector(secname, a[k], b[k])
                nr = px.index(nifty, a, b)
                vsn = raw - nr
                vss = raw - sec
            for k in range(len(p)):
                out.append((t.G, t.BW, t.qn, t.group, t.d, t.signal, H, p.symbol.values[k], int(a[k]), int(b[k]),
                            raw[k], vsn[k], vss[k], nbl[k]))
    cols = ['G', 'BW', 'qn', 'group', 'd', 'signal', 'H', 'peer', 'entry_i', 'exit_i', 'raw', 'vsn', 'vss', 'nblank']
    return pd.DataFrame(out, columns=cols)


# ----------------------------------------------------------------------------------------------- stats
def tstat(x):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    if len(x) < 2 or x.std(ddof=1) == 0:
        return np.nan
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))


def leg_returns(df, leg, T, direction=+1):
    """returns DataFrame with net signed returns for a leg; direction +1 continuation, -1 reversal"""
    if leg == 'L':
        x = df[df.signal > T].copy(); sgn = np.ones(len(x))
    elif leg == 'S':
        x = df[df.signal < -T].copy(); sgn = -np.ones(len(x))
    else:
        x = df[df.signal.abs() > T].copy(); sgn = np.sign(x.signal.values)
    sgn = sgn * direction
    x['sgn'] = sgn
    x['raw_net'] = sgn * x.raw - COST_RAW
    x['vsn_net'] = sgn * x.vsn - COST_HEDGE
    x['vss_net'] = sgn * x.vss - COST_HEDGE
    return x


def summarize(x, own3=False):
    res = dict(trades=len(x))
    if len(x) == 0:
        return res
    q = x.groupby('qn')[['raw_net', 'vsn_net', 'vss_net']].mean()
    qv = q['vsn_net']
    dclu = x.groupby('entry_i')['vsn_net'].mean()
    res.update(
        avg_raw_net=x.raw_net.mean() * 100, avg_vsn_net=x.vsn_net.mean() * 100, avg_vss_net=x.vss_net.mean() * 100,
        pct_win_vsn=(x.vsn_net > 0).mean() * 100,
        quarters=len(q), q_avg_raw=q.raw_net.mean() * 100, q_avg_vsn=qv.mean() * 100, q_avg_vss=q.vss_net.mean() * 100,
        t_q_vsn=tstat(qv), t_q_raw=tstat(q.raw_net), t_q_vss=tstat(q.vss_net),
        first14_vsn=qv[qv.index <= 13].mean() * 100, last8_vsn=qv[qv.index >= 14].mean() * 100,
        n_q_first14=int((qv.index <= 13).sum()), n_q_last8=int((qv.index >= 14).sum()),
        q_pos_vsn=int((qv > 0).sum()),
        dates=len(dclu), t_date_vsn=tstat(dclu),
        n_triggers=x[['qn', 'group', 'd']].drop_duplicates().shape[0],
        blanks=int((x.nblank > 0).sum()),
    )
    if own3:
        res['q_ge2_raw'] = int((q.raw_net >= 0.02).sum())
        res['q_pos_raw'] = int((q.raw_net > 0).sum())
    return res


def main():
    ses, R, IX, INTRA, ev = load()
    print('events', ev.shape, 'returns', R.shape, 'indices', IX.shape)
    nifty_close = IX['Nifty 50'].values
    nifty_ret = np.r_[np.nan, nifty_close[1:] / nifty_close[:-1] - 1]
    px = Px(R, IX)
    # coverage check of the indices used, over the study period (first cutoff .. last exit)
    lo, hi = int(ev.i_cut.min()) - 10, int(ev.i_p1.max()) + 25
    print('index coverage (missing sessions in study period):')
    for c in sorted(ev.sector_index.unique()) + ['Nifty 50']:
        v = IX[c].values[lo:hi]
        miss = np.isnan(v)
        first_ok = ses.day.values[lo + np.argmax(~miss)] if (~miss).any() else None
        print(f'   {c:28s} missing {miss.sum():4d}  first valid in period {first_ok}')

    trig, ev2 = build_triggers(ev, nifty_ret)
    trig.to_csv(OUT + 'triggers.csv', index=False)
    print('triggers:', trig.groupby(['G', 'BW']).size().to_dict())
    trades = build_trades(trig, ev2, px)
    trades.to_csv(OUT + 'peer_trades.csv', index=False)
    print('peer trade rows:', len(trades), ' with blank days inside window:', int((trades.nblank > 0).sum()))

    # ---------------- peer tests
    rows = []
    for (G, BW, H), df in trades.groupby(['G', 'BW', 'H']):
        base = leg_returns(df.assign(signal=1.0), 'L', 0)   # unconditional baseline: buy every eligible peer
        bs = summarize(base, own3=(H == 'OWN3'))
        rows.append(dict(G=G, BW=BW, H=H, T=0, leg='ALLPEERS', direction='long', **bs))
        for T in THRESHOLDS:
            for leg in LEGS:
                for direction, dn in [(+1, 'cont'), (-1, 'rev')]:
                    x = leg_returns(df, leg, T, direction)
                    s = summarize(x, own3=(H == 'OWN3'))
                    rows.append(dict(G=G, BW=BW, H=H, T=T, leg=leg, direction=dn, **s))
    res = pd.DataFrame(rows)
    res.to_csv(OUT + 'peer_tests.csv', index=False)

    # ---------------- index tests
    irows = []
    itr = []
    sec = trig[trig.G == 'SEC']
    for t in sec.itertuples(index=False):
        if t.group not in px.ix:
            continue
        for h in FIXED_H:
            a, b = t.d, t.d + h
            r = px.index(t.group, a, b); n = px.index('Nifty 50', a, b)
            if np.isnan(r):
                continue
            itr.append((t.BW, t.qn, t.group, t.d, t.signal, h, r, r - n))
    itr = pd.DataFrame(itr, columns=['BW', 'qn', 'group', 'd', 'signal', 'h', 'raw', 'vsn'])
    itr.to_csv(OUT + 'index_trades.csv', index=False)
    for (BW, h), df in itr.groupby(['BW', 'h']):
        for uni in ['U_all', 'U_fut']:
            u = df if uni == 'U_all' else df[df.group.isin(['Nifty Bank', 'Nifty Financial Services'])]
            for T in THRESHOLDS:
                x = u[u.signal.abs() > T].copy()
                x['vsn_net'] = np.sign(x.signal) * x.vsn - COST_INDEX
                x['raw_net'] = np.sign(x.signal) * x.raw - COST_INDEX / 2
                if len(x) == 0:
                    continue
                q = x.groupby('qn').vsn_net.mean()
                irows.append(dict(BW=BW, h=h, universe=uni, T=T, trades=len(x),
                                  avg_vsn_net=x.vsn_net.mean() * 100, avg_raw_net=x.raw_net.mean() * 100,
                                  quarters=len(q), q_avg_vsn=q.mean() * 100, t_q_vsn=tstat(q),
                                  first14_vsn=q[q.index <= 13].mean() * 100, last8_vsn=q[q.index >= 14].mean() * 100,
                                  q_pos=int((q > 0).sum()), t_date=tstat(x.groupby('d').vsn_net.mean())))
    ires = pd.DataFrame(irows)
    ires.to_csv(OUT + 'index_tests.csv', index=False)

    # ---------------- slope tests
    srows = []
    for (G, BW, H), df in trades[trades.BW.isin(['FIRST', 'BIG']) & trades.H.isin(['PC', 'OWN3'])].groupby(['G', 'BW', 'H']):
        sl = {}
        for qn, x in df.groupby('qn'):
            if x.signal.nunique() < 3:
                continue
            s = x.signal.values; y = x.vsn.values
            sl[qn] = np.cov(s, y, ddof=1)[0, 1] / np.var(s, ddof=1)
        sl = pd.Series(sl)
        srows.append(dict(G=G, BW=BW, H=H, quarters=len(sl), trades=len(df),
                          slope_mean=sl.mean(), t_q=tstat(sl),
                          first14=sl[sl.index <= 13].mean(), last8=sl[sl.index >= 14].mean(), q_pos=int((sl > 0).sum())))
    sres = pd.DataFrame(srows)
    sres.to_csv(OUT + 'slope_tests.csv', index=False)

    # ---------------- report
    pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40); pd.set_option('display.max_rows', 400)
    cols = ['G', 'BW', 'H', 'T', 'leg', 'direction', 'trades', 'n_triggers', 'quarters', 'avg_raw_net', 'avg_vsn_net',
            'avg_vss_net', 'q_avg_vsn', 't_q_vsn', 't_date_vsn', 'first14_vsn', 'last8_vsn', 'q_pos_vsn']
    print('\nUNCONDITIONAL baseline (buy every eligible peer):')
    print(res[res.leg == 'ALLPEERS'][cols].round(2).to_string(index=False))
    cont = res[(res.direction == 'cont')]
    print('\nALL continuation tests (reversal = mirror image; |t| is the same up to cost):')
    print(cont[cols].round(2).to_string(index=False))
    tested = res[(res.leg != 'ALLPEERS')]
    screen = tested[(tested.trades >= 30) & (tested.t_q_vsn.abs() >= 2.5) & (tested.first14_vsn > 0) & (tested.last8_vsn > 0) & (tested.t_q_vsn > 0)]
    print('\nSCREEN (>=30 trades, t>=2.5, both halves > 0 after costs, hedged):')
    print(screen[cols].round(2).to_string(index=False))
    print('\n|t_q| >= 2.5 among two-sided continuation tests:', int((cont.trades >= 30).sum()), 'tests with >=30 trades;',
          int(((cont.trades >= 30) & (cont.t_q_vsn.abs() >= 2.5)).sum()), 'hit |t|>=2.5')
    print('\nOWN3 rows (user target = raw 3-day >= +2% each quarter):')
    o = res[(res.H == 'OWN3') & (res.direction != 'rev')]
    print(o[cols + ['q_pos_raw', 'q_ge2_raw', 'q_avg_raw']].round(2).to_string(index=False))
    print('\nINDEX tests:')
    print(ires.round(2).to_string(index=False))
    print('\nSLOPE tests (hedged peer return per unit bellwether excess):')
    print(sres.round(3).to_string(index=False))


if __name__ == '__main__':
    main()
