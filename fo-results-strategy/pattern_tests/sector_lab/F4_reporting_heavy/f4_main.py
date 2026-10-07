"""
F4  SECTOR EARNINGS-ANNOUNCEMENT PREMIUM ("reporting-heavy" sector windows)
==========================================================================
PRE-REGISTRATION (written before any outcome column was looked at; only signal
distributions were inspected, see signal_explore.py / signal_explore2.py).

Universe ........ events.csv rows with in_fo == True (stock had F&O at that time),
                  three_day not NaN.  Trades are only in these stocks.
Groupings ....... G1 = sector_index (rows with "Nifty 500" = no sector are excluded)
                  G2 = peer_group   (blank excluded)
                  A (qn, group) is used only if it has M >= 4 F&O members that quarter.
Knowledge ....... STRICT (primary): a stock's result session is public at its cutoff
                  (= 2 sessions before the result session).  Announcement dates are NOT
                  in the data pack, so this is the conservative floor.
                  FORESIGHT-5 (secondary, assumption-dependent): result sessions are public
                  at least 5 sessions ahead.  Cannot be verified from this data pack.
Costs ........... stock round trip 0.17%; Nifty futures hedge +0.02%.
                  Sector hedge: Nifty Bank / Nifty Financial Services index futures 0.02%;
                  any other sector index needs a basket of stock futures: 0.17%.
Outcomes ........ O3  = user's 3-day window: buy at cutoff close, sell at Day+1 close,
                        return = SUM of the 3 daily returns (three_day); Nifty and sector
                        versions = nifty_3d / sector_3d from events.csv (same definition).
                  O10 = compounded return from cutoff close to close of cutoff+10 sessions
                        (blank stock return = no trade; treated as 0 which is exact because the
                        next return spans both sessions).  Nifty / sector compounded likewise.
                  net raw    = gross - 0.17
                  net vs Nifty  = gross - Nifty - 0.19
                  net vs sector = gross - sector - 0.17 - sector hedge cost

VARIANTS (32 in total)
---------------------------------------------------------------------------
A  Busy vs quiet sector window (event-level, long the reporting stock, outcome O3)
   t = stock's cutoff session.
   c2 = # OTHER F&O members of the same group & quarter with result session in [t+1, t+2]
        (STRICT: exactly what is public at t).
   c5 = # OTHER F&O members with result session in [t+1, t+5]   (FORESIGHT-5).
   A01 G1 c2>=2   A02 G1 c2>=4   A03 G1 c2==0 (quiet)
   A04 G1 c5>=3   A05 G1 c5>=6   A06 G1 c5==0 (quiet)
   A07..A12 = same six for G2.
   Diagnostic only (not extra trades): busy-minus-quiet per quarter.

B  Sector time series (daily position decided at close d-1 for day d)
   W_S(d) = # F&O members of sector S (that quarter) whose 3-day window covers day d
            (i_rd-1 <= d <= i_rd+1).  Every such member has i_rd <= d+1, so its date is
            public by its cutoff i_rd-2 <= d-1 -> STRICT real time.
   share = W_S(d) / M_S(q).  Heavy day: share >= thr.  Long instrument, short Nifty 50.
   A trade = a run of consecutive heavy days of one sector: enter at close before the first
   heavy day, exit at close of the last heavy day; legs compounded separately.
   B01 G1 sector INDEX, thr 0.25     B02 G1 sector INDEX, thr 0.40
   B03 G1 EW basket of sector F&O stocks, thr 0.25   B04 same thr 0.40
   B05 G2 EW basket, thr 0.25        B06 G2 EW basket, thr 0.40
   B07 Nifty Bank index only, thr 0.25   (index futures tradeable)
   B08 Nifty Financial Services index only, thr 0.25 (index futures tradeable)
   Index instrument uses only sectors with complete index data since Apr-2021
   (excludes India Manufacturing, India Digital, India Defence).
   Costs per run: Bank/FinServ index 0.02+0.02; other indices/baskets 0.17+0.02.

C  Position in the sector's reporting order (event-level, long, outcomes O3 and O10)
   before = # OTHER F&O members (same group, quarter) with result session < own.
   All of them report by t+1, so this is public at the cutoff t under STRICT.
   first: before == 0 (same-day co-reporters both count as first)
   late : before / (M-1) >= 0.5
   C01 G1 first O3  C02 G1 late O3  C03 G2 first O3  C04 G2 late O3
   C05 G1 first O10 C06 G1 late O10 C07 G2 first O10 C08 G2 late O10

D  Season timing within sector (G1 events only, long, outcomes O3 and O10)
   s0(q) = earliest result session of any F&O stock in quarter q (public by any later
   stock's cutoff; for the first reporter itself it is its own date).
   early: i_rd - s0 <= 4 (first 5 sessions of the season); late: i_rd - s0 >= 20.
   D01 early O3  D02 late O3  D03 early O10  D04 late O10

STATISTICS: unit = quarter (qn 0..21). Per-quarter mean of net-vs-Nifty, t across quarters,
first 14 (qn 0..13) vs last 8 (qn 14..21), quarters positive, quarters with raw-net >= 2%
(O3 only), date-clustered t (mean per entry date, t across dates).
PROMISING = net-vs-Nifty > 0 in both halves AND |t_q| >= 2.5 AND >= 30 trades AND the
placebo (f4_placebo.py) does clearly worse.
Expected false positives: with 32 variants, ~1.6 at |t|>=2 and ~0.4 at |t|>=2.5 by chance.
"""
import sys; sys.path.append('/root/.local/lib/python3.11/site-packages')  # pandas deps live in user site (python3 -I hides it)
import os
import numpy as np, pandas as pd

D = os.environ.get('SECTOR_LAB', 'sector_lab') + '/data/'
OUT = os.path.dirname(os.path.abspath(__file__)) + '/'
C_STOCK, C_NIFTY, C_IDXFUT = 0.17, 0.02, 0.02
FUT_SECTORS = {'Nifty Bank', 'Nifty Financial Services'}
INDEX_EXCLUDE = {'Nifty India Manufacturing', 'Nifty India Digital', 'Nifty India Defence', 'Nifty 500'}


def load():
    s = pd.read_csv(D + 'sessions.csv')
    r = pd.read_csv(D + 'returns.csv', index_col=0)
    ic = pd.read_csv(D + 'index_close.csv', index_col=0)
    e = pd.read_csv(D + 'events.csv')
    assert len(s) == len(r) == len(ic) and (r.index.values == s.day.values).all()
    return s, r, ic, e


def sector_cost(sec):
    return C_IDXFUT if sec in FUT_SECTORS else C_STOCK


def prep_events(s, r, ic, e):
    f = e[(e.in_fo == True) & e.three_day.notna()].copy()
    R = r.values
    col = {c: k for k, c in enumerate(r.columns)}
    idxr = ic.pct_change(fill_method=None)
    nifty = idxr['Nifty 50'].values
    # O3 (percent units)
    f['o3_gross'] = 100 * f.three_day
    f['o3_raw'] = f.o3_gross - C_STOCK
    f['o3_nifty'] = 100 * (f.three_day - f.nifty_3d) - C_STOCK - C_NIFTY
    f['o3_sector'] = 100 * (f.three_day - f.sector_3d) - C_STOCK - f.sector_index.map(sector_cost)
    # O10 compounded, cutoff close -> cutoff+10 close
    g10, n10, s10 = [], [], []
    for row in f.itertuples():
        a, b = row.i_cut + 1, row.i_cut + 10
        x = R[a:b + 1, col[row.symbol]]
        g10.append(np.prod(1 + np.nan_to_num(x)) - 1)
        n10.append(np.prod(1 + nifty[a:b + 1]) - 1)
        sr = idxr[row.sector_index].values[a:b + 1]
        s10.append(np.prod(1 + sr) - 1 if np.isfinite(sr).all() else np.nan)
    f['o10_gross'] = 100 * np.array(g10)
    f['o10_raw'] = f.o10_gross - C_STOCK
    f['o10_nifty'] = 100 * (np.array(g10) - np.array(n10)) - C_STOCK - C_NIFTY
    f['o10_sector'] = 100 * (np.array(g10) - np.array(s10)) - C_STOCK - f.sector_index.map(sector_cost)
    f['date'] = f.cutoff
    # signals per grouping
    for gname, gcol in [('G1', 'sector_index'), ('G2', 'peer_group')]:
        ok = f[gcol].notna() & (f[gcol] != 'Nifty 500')
        f[gname + '_M'] = np.nan
        for k in ['c2', 'c5', 'before']:
            f[gname + '_' + k] = np.nan
        for (q, g), gg in f[ok].groupby(['qn', gcol]):
            rd = gg.i_rd.values
            M = len(gg)
            t = gg.i_cut.values
            c2 = ((rd[None, :] >= t[:, None] + 1) & (rd[None, :] <= t[:, None] + 2)).sum(1) - 1  # self has rd=t+2
            c5 = ((rd[None, :] >= t[:, None] + 1) & (rd[None, :] <= t[:, None] + 5)).sum(1) - 1
            before = (rd[None, :] < rd[:, None]).sum(1)
            f.loc[gg.index, gname + '_M'] = M
            f.loc[gg.index, gname + '_c2'] = c2
            f.loc[gg.index, gname + '_c5'] = c5
            f.loc[gg.index, gname + '_before'] = before
        f[gname + '_elig'] = f[gname + '_M'] >= 4
    s0 = f.groupby('qn').i_rd.min()
    f['sinc'] = f.i_rd - f.qn.map(s0)
    return f


def event_variants(f):
    """returns dict name -> (eligible mask, selected mask, outcome prefix, grouping, description)"""
    V = {}
    for gi, (gname, gl) in enumerate([('G1', 'sector_index'), ('G2', 'peer_group')]):
        el = f[gname + '_elig']
        c2, c5 = f[gname + '_c2'], f[gname + '_c5']
        base = 0 if gname == 'G1' else 6
        defs = [('c2>=2', c2 >= 2, 'STRICT'), ('c2>=4', c2 >= 4, 'STRICT'), ('c2==0', c2 == 0, 'STRICT'),
                ('c5>=3', c5 >= 3, 'FORESIGHT-5'), ('c5>=6', c5 >= 6, 'FORESIGHT-5'), ('c5==0', c5 == 0, 'FORESIGHT-5')]
        for j, (lab, m, kn) in enumerate(defs):
            V['A%02d' % (base + j + 1)] = (el, el & m, 'o3', gname,
                                         f'{gname}({gl}) {lab} [{kn}] other F&O peers reporting in window; 3-day window')
    for gname, gl, off in [('G1', 'sector_index', 0), ('G2', 'peer_group', 2)]:
        el = f[gname + '_elig']
        b = f[gname + '_before']
        late = b / (f[gname + '_M'] - 1) >= 0.5
        for h, hoff in [('o3', 0), ('o10', 4)]:
            V['C%02d' % (1 + off + hoff)] = (el, el & (b == 0), h, gname, f'{gname}({gl}) FIRST reporter of sector this season; {h}')
            V['C%02d' % (2 + off + hoff)] = (el, el & late, h, gname, f'{gname}({gl}) LATE reporter (>=50% of peers already reported); {h}')
    el = f['G1_elig']
    for h, k in [('o3', 0), ('o10', 2)]:
        V['D%02d' % (1 + k)] = (el, el & (f.sinc <= 4), h, 'G1', f'G1 early-season (first 5 sessions of season); {h}')
        V['D%02d' % (2 + k)] = (el, el & (f.sinc >= 20), h, 'G1', f'G1 late-season (>=20 sessions after season start); {h}')
    return V


def tstat(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 2 or x.std(ddof=1) == 0:
        return np.nan
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))


def summarize(tr, name, desc, horizon, prefix, is3=False):
    """tr: DataFrame with qn, date, <prefix>_raw/_nifty/_sector/_gross"""
    q = tr.groupby('qn')[prefix + '_nifty'].mean()
    qr = tr.groupby('qn')[prefix + '_raw'].mean()
    qg = tr.groupby('qn')[prefix + '_gross'].mean()
    qs = tr.groupby('qn')[prefix + '_sector'].mean()
    dd = tr.groupby('date')[prefix + '_nifty'].mean()
    cost_n = (tr[prefix + '_gross'] - tr[prefix + '_raw']) + C_NIFTY   # cost of the Nifty-hedged trade
    qgn = (tr[prefix + '_nifty'] + cost_n).groupby(tr.qn).mean()        # gross (before costs) vs Nifty
    out = dict(name=name, desc=desc, horizon=horizon, trades=len(tr), quarters=len(q),
               avg_raw_net=tr[prefix + '_raw'].mean(), avg_nifty_net=tr[prefix + '_nifty'].mean(),
               avg_sector_net=tr[prefix + '_sector'].mean(),
               pct_win=100 * (tr[prefix + '_nifty'] > 0).mean(),
               perq_nifty=q.mean(), t_q=tstat(q), t_date=tstat(dd), n_dates=len(dd),
               first14=q[q.index <= 13].mean(), last8=q[q.index >= 14].mean(),
               q_pos=int((q > 0).sum()), perq_raw=qr.mean(), t_q_raw=tstat(qr), perq_sector=qs.mean(), t_q_sector=tstat(qs),
               q_raw_ge2=int((qr >= 2).sum()) if is3 else np.nan, q_gross_ge2=int((qg >= 2).sum()) if is3 else np.nan,
               max_q_raw=qr.max(), perq_nifty_gross=qgn.mean(), t_q_gross=tstat(qgn),
               first14_gross=qgn[qgn.index <= 13].mean(), last8_gross=qgn[qgn.index >= 14].mean())
    return out, q


def run_event_tests(f):
    V = event_variants(f)
    rows, perq = [], {}
    for name, (el, sel, h, gname, desc) in V.items():
        tr = f[sel]
        o, q = summarize(tr, name, desc, '3-day window' if h == 'o3' else '10 sessions', h, is3=(h == 'o3'))
        # baseline: all eligible events of the same grouping, same outcome
        bq = f[el].groupby('qn')[h + '_nifty'].mean()
        diff = (q - bq.reindex(q.index))
        o['baseline_perq_nifty'] = bq.mean()
        o['minus_baseline_perq'] = diff.mean(); o['t_minus_baseline'] = tstat(diff)
        rows.append(o); perq[name] = q
    # A diagnostics: busy minus quiet per quarter
    diag = []
    for g in ['G1', 'G2']:
        el = f[g + '_elig']
        for k, busy_thr in [('c2', 2), ('c5', 3)]:
            b = f[el & (f[g + '_' + k] >= busy_thr)].groupby('qn').o3_nifty.mean()
            qq = f[el & (f[g + '_' + k] == 0)].groupby('qn').o3_nifty.mean()
            d = (b - qq).dropna()
            diag.append(dict(grouping=g, signal=f'{k}>={busy_thr} minus {k}==0', perq_diff=d.mean(), t=tstat(d), q=len(d),
                             first14=d[d.index <= 13].mean(), last8=d[d.index >= 14].mean()))
    return pd.DataFrame(rows), pd.DataFrame(perq), pd.DataFrame(diag), V


# ------------------------------------------------------------------ B: time series
def build_daily(s, r, ic, f):
    idxr = ic.pct_change(fill_method=None)
    nifty = idxr['Nifty 50'].values
    R = r.values
    col = {c: k for k, c in enumerate(r.columns)}
    s0 = f.groupby('qn').i_rd.min(); send = f.groupby('qn').i_p1.max()
    first_day, last_day = int(s0.min()) - 5, int(send.max()) + 5
    days = np.arange(first_day, last_day + 1)
    # day -> quarter (latest season that has started, starting 5 sessions before s0)
    qstart = (s0 - 5).sort_index()
    dq = np.searchsorted(qstart.values, days, side='right') - 1
    in_season = np.zeros(len(days), bool)
    for q in s0.index:
        in_season |= (days >= s0[q] - 1) & (days <= send[q])
    recs = []
    for gname, gcol in [('G1', 'sector_index'), ('G2', 'peer_group')]:
        ok = f[gcol].notna() & (f[gcol] != 'Nifty 500')
        for sec in sorted(f.loc[ok, gcol].unique()):
            W = np.zeros(len(days)); M = np.zeros(len(days)); ew = np.full(len(days), np.nan)
            for q in s0.index:
                gg = f[ok & (f[gcol] == sec) & (f.qn == q)]
                mq = dq == q
                if len(gg) == 0 or not mq.any():
                    continue
                M[mq] = len(gg)
                dsel = days[mq]
                rd = gg.i_rd.values
                W[mq] = ((rd[None, :] >= dsel[:, None] - 1) & (rd[None, :] <= dsel[:, None] + 1)).sum(1)
                cols_ = [col[x] for x in gg.symbol]
                with np.errstate(all='ignore'):
                    ew[mq] = np.nanmean(R[dsel][:, cols_], axis=1)
            rec = pd.DataFrame(dict(day_i=days, qn=dq, in_season=in_season, W=W, M=M, ew=ew, nifty=nifty[days]))
            rec['grouping'] = gname; rec['sector'] = sec
            rec['idx'] = idxr[sec].values[days] if (gname == 'G1' and sec in idxr.columns) else np.nan
            recs.append(rec)
    dl = pd.concat(recs, ignore_index=True)
    dl['share'] = np.where(dl.M > 0, dl.W / dl.M.replace(0, np.nan), 0)
    return dl


B_DEFS = {
    'B01': ('G1', 'idx', 0.25, None), 'B02': ('G1', 'idx', 0.40, None),
    'B03': ('G1', 'ew', 0.25, None), 'B04': ('G1', 'ew', 0.40, None),
    'B05': ('G2', 'ew', 0.25, None), 'B06': ('G2', 'ew', 0.40, None),
    'B07': ('G1', 'idx', 0.25, 'Nifty Bank'), 'B08': ('G1', 'idx', 0.25, 'Nifty Financial Services'),
}


def b_subset(dl, g, inst, only):
    x = dl[(dl.grouping == g) & (dl.M >= 4)]
    if inst == 'idx':
        x = x[~x.sector.isin(INDEX_EXCLUDE)]
    if only:
        x = x[x.sector == only]
    return x


def runs_from_flags(x, inst, flag):
    """x: one grouping subset (sorted by sector, day_i); flag: bool array aligned. returns trade table."""
    out = []
    for sec, gg in x.assign(flag=flag).groupby('sector', sort=False):
        fl = gg.flag.values; di = gg.day_i.values
        ri = gg[inst].values; rn = gg.nifty.values; re = gg.ew.values; rx = gg.idx.values; qn = gg.qn.values
        start = None
        for k in range(len(fl) + 1):
            on = k < len(fl) and fl[k] and (start is None or di[k] == di[k - 1] + 1)
            if on and start is None:
                start = k
            elif not on and start is not None:
                sl = slice(start, k)
                g_ = np.prod(1 + np.nan_to_num(ri[sl])) - 1
                n_ = np.prod(1 + rn[sl]) - 1
                xs = np.prod(1 + np.nan_to_num(rx[sl])) - 1 if np.isfinite(rx[sl]).all() else np.nan
                out.append((sec, qn[start], di[start], k - start, g_, n_, xs))
                start = None
                if k < len(fl) and fl[k]:
                    start = k
    t = pd.DataFrame(out, columns=['sector', 'qn', 'date', 'ndays', 'g', 'n', 'secidx'])
    return t


def b_trades(dl, name, flag_override=None):
    g, inst, thr, only = B_DEFS[name]
    x = b_subset(dl, g, inst, only).sort_values(['sector', 'day_i'])
    flag = (x.share.values >= thr) if flag_override is None else flag_override
    t = runs_from_flags(x, inst, flag)
    hedge = t.sector.map(lambda sct: C_IDXFUT if (inst == 'idx' and sct in FUT_SECTORS) else C_STOCK)
    t['b_gross'] = 100 * t.g
    t['b_raw'] = t.b_gross - hedge
    t['b_nifty'] = 100 * (t.g - t.n) - hedge - C_NIFTY
    if inst == 'idx':
        t['b_sector'] = np.nan  # long index vs same index: meaningless (zero by construction)
    else:
        t['b_sector'] = 100 * (t.g - t.secidx) - C_STOCK - t.sector.map(sector_cost) if g == 'G1' else np.nan
    return t, x


def b_daily_diag(dl):
    rows = []
    for name, (g, inst, thr, only) in B_DEFS.items():
        x = b_subset(dl, g, inst, only)
        ex = 100 * (x[inst] - x.nifty)
        heavy = x.share >= thr
        seas = x.in_season & ~heavy
        off = ~x.in_season
        qh = ex[heavy].groupby(x.qn[heavy]).mean(); qs = ex[seas].groupby(x.qn[seas]).mean()
        d = (qh - qs).dropna()
        rows.append(dict(name=name, heavy_days=int(heavy.sum()), mean_excess_heavy_day=ex[heavy].mean(),
                         mean_excess_other_season_day=ex[seas].mean(), mean_excess_offseason_day=ex[off].mean(),
                         perq_heavy_minus_season=d.mean(), t_heavy_minus_season=tstat(d)))
    return pd.DataFrame(rows)


def main():
    s, r, ic, e = load()
    print('events', len(e), 'F&O events', (e.in_fo == True).sum())
    f = prep_events(s, r, ic, e)
    f.to_csv(OUT + 'events_with_signals.csv', index=False)
    print('eligible G1', int(f.G1_elig.sum()), 'G2', int(f.G2_elig.sum()))
    summ, perq, diag, V = run_event_tests(f)
    dl = build_daily(s, r, ic, f)
    dl.to_csv(OUT + 'B_daily_panel.csv', index=False)
    brows, bperq, btr = [], {}, []
    for name in B_DEFS:
        t, _ = b_trades(dl, name)
        g, inst, thr, only = B_DEFS[name]
        desc = f"{g} {'sector INDEX' if inst == 'idx' else 'EW basket of sector F&O stocks'} long / Nifty short on days when >= {int(thr*100)}% of sector F&O members are inside their 3-day results window" + (f' ({only} only)' if only else '')
        o, q = summarize(t.assign(date=t.date), name, desc, 'run of heavy days (avg %.1f sessions)' % t.ndays.mean(), 'b')
        o['avg_days'] = t.ndays.mean()
        brows.append(o); bperq[name] = q; btr.append(t.assign(variant=name))
    bsum = pd.DataFrame(brows)
    allsum = pd.concat([summ, bsum], ignore_index=True)
    allsum['promising_stats'] = (allsum.first14 > 0) & (allsum.last8 > 0) & (allsum.t_q.abs() >= 2.5) & (allsum.trades >= 30)
    allsum.to_csv(OUT + 'variant_summary.csv', index=False)
    pd.concat([perq, pd.DataFrame(bperq)], axis=1).to_csv(OUT + 'per_quarter_nifty_net.csv')
    diag.to_csv(OUT + 'A_busy_minus_quiet.csv', index=False)
    bd = b_daily_diag(dl); bd.to_csv(OUT + 'B_daily_diag.csv', index=False)
    pd.concat(btr).to_csv(OUT + 'B_trades.csv', index=False)
    pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40)
    cols = ['name', 'trades', 'quarters', 'avg_raw_net', 'avg_nifty_net', 'avg_sector_net', 'perq_nifty', 't_q', 't_date',
            'first14', 'last8', 'q_pos', 'q_raw_ge2', 'max_q_raw', 'perq_sector', 't_q_sector', 'perq_nifty_gross', 't_q_gross', 'promising_stats']
    print(allsum[cols].round(3).to_string())
    print('\nbaselines / minus baseline (event variants):')
    print(summ[['name', 'baseline_perq_nifty', 'minus_baseline_perq', 't_minus_baseline']].round(3).to_string())
    print('\nA busy minus quiet:'); print(diag.round(3).to_string())
    print('\nB daily diag:'); print(bd.round(4).to_string())
    print('\nDescriptions:')
    for _, rw in allsum.iterrows():
        print(rw['name'], '|', rw.desc)
    print('\nVARIANTS TESTED:', len(allsum))


if __name__ == '__main__':
    main()
