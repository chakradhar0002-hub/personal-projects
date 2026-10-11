#!/usr/bin/env python3
"""Verifier (v2) - own point-in-time news features for the 3,280 F&O results and for ordinary placebo days.
Independent of the study's scripts. Reads only local CSV / sqlite (read-only).
usage: python3 v2_features.py SCRATCH OUTDIR
  SCRATCH = scratchpad root (report/nse_events.db, perf/features, sector_lab/data)
Writes OUTDIR/feat_results.csv, OUTDIR/feat_placebo.csv.gz, OUTDIR/biz_items.csv
Announcement text is untrusted data: only matched against fixed regexes here."""
import re
import sqlite3
import sys

import numpy as np
import pandas as pd

SC, OUT = sys.argv[1], sys.argv[2]
DB = f'{SC}/report/nse_events.db'
D = f'{SC}/sector_lab/data'
F = f'{SC}/perf/features'

ses = pd.read_csv(f'{D}/sessions.csv')
sday = pd.to_datetime(ses.day).values  # index i -> day
day2i = {pd.Timestamp(d): i for i, d in zip(ses.i, ses.day)}
NS = len(ses)

panel = pd.read_csv(f'{F}/panel.csv', usecols=['symbol', 'qn', 'industry', 'i_cut', 'i_rd', 'i_p1', 'i_react',
                                                'in_fo_events', 'lag21', 'vol_ratio_5_60', 'cut_rsi14', 'XN', 'W',
                                                'mean_drift_4_B', 'n_prev_B'])
out = pd.read_csv(f'{F}/outcomes.csv', usecols=['symbol', 'qn', 'three_day', 'three_day_net', 'tradable_B',
                                                 'vsN_H20', 'vsN_net_H20'])
ev = pd.read_csv(f'{D}/events.csv', usecols=['symbol', 'qn', 'quarter_end', 'results_date', 'results_time',
                                             'i_rd', 'i_cut', 'in_fo'])
ev['results_date'] = pd.to_datetime(ev.results_date)
ev['quarter_end'] = pd.to_datetime(ev.quarter_end)

# ---------------- announcements
con = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
an = pd.read_sql('select symbol, an_dt, descr, txt from an', con)
n0 = len(an)
an = an.drop_duplicates()
an['t'] = pd.to_datetime(an.an_dt, format='%d-%b-%Y %H:%M:%S')
an['descr'] = an.descr.fillna('').str.strip()
an['txt'] = an.txt.fillna('')
print('announcements', n0, 'after exact-dup drop', len(an))

# own results dates (all quarters in events.csv, F&O or not) and the calendar day after -> excluded from counts
rd = ev[['symbol', 'results_date']].dropna()
excl = set()
for s, d in zip(rd.symbol, rd.results_date):
    excl.add((s, d.normalize()))
    excl.add((s, (d + pd.Timedelta(days=1)).normalize()))
an['own_rd'] = [(s, t.normalize()) in excl for s, t in zip(an.symbol, an.t)]
print('items on own results day / day after', int(an.own_rd.sum()))

PR_SET = {'Press Release', 'Press Release (Revised)'}
an['PR'] = an.descr.isin(PR_SET)
biz_re = re.compile(r'business update|quarterly update|provisional (business|figures|numbers|data)|'
                    r'monthly (sales|business|update)|(auto|vehicle|tractor) sales|sales (update|performance|volume|'
                    r'numbers|figures|data)|production (and|&) sales|sales for the month|operational update|'
                    r'key business (update|highlights)|business performance update', re.I)
upd = an.descr.isin({'Updates', 'General Updates', 'General updates'} | PR_SET)
an['BIZ'] = (an.descr == 'Monthly Business Updates') | (upd & an.txt.str.contains(biz_re))
print('PR items', int(an.PR.sum()), ' BIZ items', int(an.BIZ.sum()),
      ' (Monthly Business Updates', int((an.descr == 'Monthly Business Updates').sum()), ')')

# nifty and stock returns
ret = pd.read_csv(f'{D}/returns.csv')
ret['day'] = pd.to_datetime(ret.day)
ic = pd.read_csv(f'{D}/index_close.csv', usecols=['day', 'Nifty 50'])
ic['day'] = pd.to_datetime(ic.day)
nif = ic.set_index('day')['Nifty 50'].pct_change()
sessdays = pd.to_datetime(ses.day)
ret = ret.set_index('day').reindex(sessdays.values)
nifr = nif.reindex(sessdays.values).values
R = {c: ret[c].values for c in ret.columns}


def react_session(t):
    """first session whose close (15:30) is at/after t"""
    d = t.normalize()
    i = np.searchsorted(sday, np.datetime64(d))
    if i < NS and pd.Timestamp(sday[i]) == d and t.hour * 60 + t.minute < 15 * 60 + 30:
        return i
    if i < NS and pd.Timestamp(sday[i]) == d:
        return i + 1
    return i  # next session after a non-session day


# BIZ reaction per item
biz = an[an.BIZ].copy()
biz['s'] = [react_session(t) for t in biz.t]
biz['rx'] = [((R[s][i] - nifr[i]) * 100 if (s in R and i < NS and not np.isnan(R[s][i]) and not np.isnan(nifr[i]))
              else np.nan) for s, i in zip(biz.symbol, biz.s)]
biz[['symbol', 'an_dt', 'descr', 's', 'rx', 'own_rd']].to_csv(f'{OUT}/biz_items.csv', index=False)

# per-symbol sorted arrays
grp = {}
for s, g in an.groupby('symbol'):
    g = g.sort_values('t')
    grp[s] = {
        'pr_t': g.t[g.PR & ~g.own_rd].values,
        'pr_t_all': g.t[g.PR].values,
        'all_t': g.t[~g.own_rd].values,
    }
bizg = {s: g.sort_values('t') for s, g in biz[~biz.own_rd].groupby('symbol')}


def cnt(arr, lo, hi):
    return int(np.searchsorted(arr, np.datetime64(hi), 'left') - np.searchsorted(arr, np.datetime64(lo), 'left'))


def feats(sym, i_dec, hh=15, mm=0):
    T = pd.Timestamp(sday[i_dec]) + pd.Timedelta(hours=hh, minutes=mm)
    g = grp.get(sym)
    o = {}
    if g is None:
        return o
    for w in (7, 14, 21, 30, 45, 60, 90):
        o[f'PR{w}'] = cnt(g['pr_t'], T - pd.Timedelta(days=w), T)
    o['PR30_incl'] = cnt(g['pr_t_all'], T - pd.Timedelta(days=30), T)
    o['N30'] = cnt(g['all_t'], T - pd.Timedelta(days=30), T)
    # stock's own PR norm: PR per 30 days over [T-395d, T-30d) clipped at 2021-03-01
    lo = max(T - pd.Timedelta(days=395), pd.Timestamp('2021-03-01'))
    span = (T - pd.Timedelta(days=30) - lo).days
    o['PRnorm'] = cnt(g['pr_t'], lo, T - pd.Timedelta(days=30)) * 30 / span if span >= 90 else np.nan
    bg = bizg.get(sym)
    if bg is not None:
        m = (bg.t >= T - pd.Timedelta(days=45)) & (bg.t < T)
        o['BIZ45'] = int(m.sum())
        mm_ = m & (bg.s < i_dec)
        ss = bg.loc[mm_].drop_duplicates('s')
        o['BIZ45_done'] = int(mm_.sum())
        o['BIZ_RX'] = float(ss.rx.sum()) if len(ss) else np.nan
    else:
        o['BIZ45'] = 0
        o['BIZ45_done'] = 0
        o['BIZ_RX'] = np.nan
    return o


rows = []
for r in panel.itertuples():
    o = {'symbol': r.symbol, 'qn': r.qn}
    o.update(feats(r.symbol, r.i_cut))
    f1530 = feats(r.symbol, r.i_cut, 15, 30)
    o['PR30_1530'] = f1530.get('PR30')
    fprev = feats(r.symbol, r.i_cut - 1, 15, 30)  # as of the previous close
    o['PR30_prev'] = fprev.get('PR30')
    rows.append(o)
fr_ = pd.DataFrame(rows)

# ------------- RDCHG (results date vs same quarter last year)
ev['rdays'] = (ev.results_date - ev.quarter_end).dt.days
evk = ev.set_index(['symbol', 'qn'])
fr = pd.read_sql('select symbol, to_date, broadcast from fr', con)
fr['b'] = pd.to_datetime(fr.broadcast, format='%d-%b-%Y %H:%M:%S', errors='coerce')
fr['to'] = pd.to_datetime(fr.to_date, format='%d-%b-%Y', errors='coerce')
fr = fr.dropna(subset=['b', 'to'])
fr_first = fr.groupby(['symbol', 'to']).b.min()


def rd_last_year(sym, qn):
    if qn - 4 >= 0:
        if (sym, qn - 4) in evk.index:
            v = evk.loc[(sym, qn - 4), 'rdays']
            return float(v)
        return np.nan
    qe = evk.loc[(sym, qn), 'quarter_end'] - pd.DateOffset(years=1)
    qe = qe + pd.offsets.MonthEnd(0)
    if (sym, qe) in fr_first.index:
        return float((fr_first.loc[(sym, qe)].normalize() - qe).days)
    return np.nan


rdl = []
for r in panel.itertuples():
    cur = evk.loc[(r.symbol, r.qn), 'rdays']
    ly = rd_last_year(r.symbol, r.qn)
    rdl.append((cur, ly))
fr_['rdays'] = [a for a, b in rdl]
fr_['rdays_ly'] = [b for a, b in rdl]
fr_['RDCHG_raw'] = fr_.rdays - fr_.rdays_ly
fr_['RDCHG'] = np.where(fr_.qn.isin([0, 1, 4]), np.nan, fr_.RDCHG_raw)

res = panel.merge(out, on=['symbol', 'qn']).merge(fr_, on=['symbol', 'qn'])
res.to_csv(f'{OUT}/feat_results.csv', index=False)
print('results rows', len(res))

# ---------------- placebo days: ordinary F&O stock-days, no result session of the stock within 10 sessions
# F&O proxy: the stock's next result (first event with i_rd > d) is a panel (F&O) result
ev_all = ev.dropna(subset=['i_rd']).copy()
ev_all['i_rd'] = ev_all.i_rd.astype(int)
pset = set(zip(panel.symbol, panel.qn))
pl = []
i_lo = day2i.get(pd.Timestamp('2021-04-01'), None) or int(np.searchsorted(sday, np.datetime64('2021-04-01')))
i_hi = NS - 4
for s, g in ev_all.groupby('symbol'):
    if s not in R:
        continue
    rds = np.sort(g.i_rd.values)
    nxt_q = g.sort_values('i_rd')
    for i in range(i_lo, i_hi, 1):
        k = np.searchsorted(rds, i)
        near = False
        if k < len(rds) and rds[k] - i <= 10:
            near = True
        if k > 0 and i - rds[k - 1] <= 10:
            near = True
        if near or k >= len(rds):
            continue
        qn_next = int(nxt_q.qn.values[k])
        if (s, qn_next) not in pset:
            continue
        rr = R[s][i + 1:i + 4]
        if np.isnan(rr).any():
            continue
        pl.append((s, i, qn_next, float(rr.sum() * 100)))
pl = pd.DataFrame(pl, columns=['symbol', 'i', 'qn_next', 'fwd3'])
# every 1 day is heavy; features only for all rows (vectorised count)
prc = []
for s, g in pl.groupby('symbol'):
    gg = grp.get(s)
    T = sday[g.i.values] + np.timedelta64(15, 'h')
    if gg is None:
        prc.append(pd.Series(0, index=g.index)); continue
    a = gg['pr_t']
    c30 = np.searchsorted(a, T, 'left') - np.searchsorted(a, T - np.timedelta64(30, 'D'), 'left')
    prc.append(pd.Series(c30, index=g.index))
pl['PR30'] = pd.concat(prc)
pl['day'] = sday[pl.i.values]
pl.to_csv(f'{OUT}/feat_placebo.csv.gz', index=False)
print('placebo days', len(pl), 'mean fwd3', round(pl.fwd3.mean(), 3), 'PR30>=1 share', round((pl.PR30 >= 1).mean(), 3))
