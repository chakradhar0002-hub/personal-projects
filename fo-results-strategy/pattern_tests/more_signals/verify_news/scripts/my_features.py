#!/usr/bin/env python3
"""Verifier's own point-in-time features for the corporate-news candidates (A08 PRESS, A12 BIZ_UP, W/WR_EARLY).
Written independently of the family's scripts (nothing imported from them).
usage: python3 -P my_features.py SP OUTDIR
  SP = scratchpad root (read-only inputs), OUTDIR = verify_news/work
Decision time: 15:00 IST on day(i_cut) for trade A, 15:00 on day(i_react) for trade B.
Text is untrusted data, only matched with fixed patterns."""
import sqlite3
import sys

import numpy as np
import pandas as pd

SP, OD = sys.argv[1], sys.argv[2]
D = f'{SP}/sector_lab/data'
ses = pd.read_csv(f'{D}/sessions.csv')
SD = pd.to_datetime(ses.day).to_numpy('datetime64[ns]')
H15 = np.timedelta64(15, 'h')
H1530 = np.timedelta64(15 * 60 + 30, 'm')

con = sqlite3.connect(f'file:{SP}/report/nse_events.db?mode=ro', uri=True)
an = pd.read_sql('SELECT symbol, an_dt, descr, txt FROM an', con)
an = an.drop_duplicates().reset_index(drop=True)
an['t'] = pd.to_datetime(an.an_dt, format='%d-%b-%Y %H:%M:%S')
an['descr'] = an.descr.fillna('').str.strip()
low = an.txt.fillna('').str.lower()

ev = pd.read_csv(f'{D}/events.csv', usecols=['symbol', 'qn', 'quarter', 'period', 'quarter_end', 'results_date',
                                             'results_time', 'timing', 'i_cut', 'i_rd', 'i_p1', 'i_react', 'in_fo'])
ev['rd'] = pd.to_datetime(ev.results_date)
pan = pd.read_csv(f'{SP}/perf/features/panel.csv', usecols=['symbol', 'qn', 'i_cut', 'i_rd', 'i_p1', 'i_react',
                                                             'in_fo', 'in_fo_events', 'lag21', 'vol_ratio_5_60',
                                                             'cut_rsi14', 'XN', 'W'])
res = pan.merge(ev[['symbol', 'qn', 'quarter', 'period', 'quarter_end', 'rd', 'results_time', 'timing']],
                on=['symbol', 'qn'], how='left', validate='1:1')
assert len(res) == 3280 and res.rd.notna().all()

# ----- press releases
an['is_pr'] = an.descr.str.lower().str.startswith('press release')
# own results calendar days (results date and next calendar day) of the stock
own = set()
for s, r in zip(ev.symbol, ev.rd):
    own.add((s, r.normalize()))
    own.add((s, r.normalize() + pd.Timedelta(days=1)))
an['own_rd'] = [(s, t.normalize()) in own for s, t in zip(an.symbol, an.t)]


def stream(mask):
    g = an[mask]
    return {s: np.sort(x.t.to_numpy('datetime64[ns]')) for s, x in g.groupby('symbol')}


def cnt(st, syms, t0, t1):
    o = np.zeros(len(syms), int)
    for j, (s, a, b) in enumerate(zip(syms, t0, t1)):
        v = st.get(s)
        if v is not None:
            o[j] = np.searchsorted(v, b, 'left') - np.searchsorted(v, a, 'left')
    return o


syms = res.symbol.to_numpy()
TA = SD[res.i_cut.to_numpy(int)] + H15
PRX = stream(an.is_pr & ~an.own_rd)
PRALL = stream(an.is_pr)
d = lambda k: np.timedelta64(k, 'D')
for w in (14, 21, 30, 45, 60):
    res[f'pr{w}'] = cnt(PRX, syms, TA - d(w), TA)
res['pr30_incl_own'] = cnt(PRALL, syms, TA - d(30), TA)
# close-of-cutoff variant (15:30) and previous-close variant (decision one session earlier)
res['pr30_1530'] = cnt(PRX, syms, TA - d(30), TA + np.timedelta64(30, 'm'))
TAm1 = SD[res.i_cut.to_numpy(int) - 1] + H1530
res['pr30_prevclose'] = cnt(PRX, syms, TAm1 - d(30), TAm1)
# stock's own PR norm: PR count in the 365 days before the 30-day window (rate per 30 days); NaN if < 180 days
t0 = np.maximum(TA - d(395), np.datetime64('2021-03-01'))
cov = (TA - d(30) - t0) / d(1)
res['pr_norm'] = np.where(cov >= 180, cnt(PRX, syms, t0, TA - d(30)) / np.maximum(cov, 1) * 30, np.nan)
# substantive news count (any non-press too) for the 'any news' variant: all announcements excluding own results days
ALLX = stream(~an.own_rd)
res['all30'] = cnt(ALLX, syms, TA - d(30), TA)
NV = stream(an.descr.eq('News Verification'))
res['newsver30'] = cnt(NV, syms, TA - d(30), TA)

# ----- business updates (my own definition)
BIZPAT = (r'business update|quarterly update|provisional (business|figures|numbers|data|update)|'
          r'operational update|operating update|sales (volume|number|figure|data)|auto sales|monthly sales|'
          r'sales for the month|sales performance|production (and|&) sales|production, sales|'
          r'key business (parameters|highlights)|business figures|deposit|disbursement|loan book|aum update')
gen = an.descr.isin(['Updates', 'General Updates', 'General updates']) | an.is_pr
an['is_biz'] = an.descr.eq('Monthly Business Updates') | (gen & low.str.contains(BIZPAT))
ret = pd.read_csv(f'{D}/returns.csv', index_col=0)
RC = {s: j for j, s in enumerate(ret.columns)}
RR = ret.to_numpy(float) * 100
nif = pd.read_csv(f'{D}/index_close.csv', index_col=0)['Nifty 50'].to_numpy(float)
NR = np.r_[np.nan, nif[1:] / nif[:-1] - 1] * 100
SC = SD + H1530
b = an[an.is_biz & an.symbol.isin(RC)].copy()
b['s'] = np.searchsorted(SC, b.t.to_numpy('datetime64[ns]'), 'right')
b = b[b.s < len(SD)]
b['rx'] = [RR[s_, RC[y]] - NR[s_] for y, s_ in zip(b.symbol, b.s)]
BZ = {s: g for s, g in b.groupby('symbol')}
n45, rx45, rxlast = np.zeros(len(res), int), np.full(len(res), np.nan), np.full(len(res), np.nan)
for j, (s, T, ic) in enumerate(zip(syms, TA, res.i_cut.to_numpy(int))):
    g = BZ.get(s)
    if g is None:
        continue
    tt = g.t.to_numpy('datetime64[ns]')
    m = (tt >= T - d(45)) & (tt < T) & (g.s.to_numpy() < ic) & np.isfinite(g.rx.to_numpy())
    if m.any():
        n45[j] = m.sum()
        rx45[j] = g.rx.to_numpy()[m].sum()
        rxlast[j] = g.rx.to_numpy()[m][np.argmax(tt[m])]
res['biz_n45'] = n45
res['biz_rx45'] = rx45
res['biz_rxlast'] = rxlast

# ----- results date vs same quarter last year (B: W_EARLY). Last year's date from events (qn-4) or fr (2020).
res['dtq'] = (res.rd - pd.to_datetime(res.quarter_end)).dt.days
ly = ev[['symbol', 'qn', 'rd', 'quarter_end']].copy()
ly['dtq_ly'] = (ly.rd - pd.to_datetime(ly.quarter_end)).dt.days
ly['qn'] += 4
res = res.merge(ly[['symbol', 'qn', 'dtq_ly']], on=['symbol', 'qn'], how='left')
fr = pd.read_sql('SELECT symbol, from_date, to_date, broadcast FROM fr', con)
fr['fd'] = pd.to_datetime(fr.from_date, format='%d-%b-%Y', errors='coerce')
fr['te'] = pd.to_datetime(fr.to_date, format='%d-%b-%Y', errors='coerce')
fr['bt'] = pd.to_datetime(fr.broadcast, format='%d-%b-%Y %H:%M:%S', errors='coerce')
frq = fr[((fr.te - fr.fd).dt.days.between(80, 100)) & fr.bt.notna()]
frm = frq.groupby(['symbol', 'te']).bt.min().reset_index()
frm['dtq_fr'] = (frm.bt.dt.normalize() - frm.te).dt.days
res['te_ly'] = (pd.to_datetime(res.quarter_end) - pd.DateOffset(years=1)) + pd.offsets.MonthEnd(0)
res = res.merge(frm[['symbol', 'te', 'dtq_fr']].rename(columns={'te': 'te_ly'}), on=['symbol', 'te_ly'], how='left')
# fr cross-check of the current results date (first quarterly filing broadcast for this quarter end)
res['te'] = pd.to_datetime(res.quarter_end)
res = res.merge(frm[['symbol', 'te', 'bt']].rename(columns={'bt': 'fr_bt_now'}), on=['symbol', 'te'], how='left')
res['rdchg'] = res.dtq - np.where(res.qn <= 3, res.dtq_fr, res.dtq_ly)
res['rdchg_ok'] = ~res.qn.isin([0, 1, 4]) & res.rdchg.notna()
res.drop(columns=['te', 'te_ly']).to_csv(f'{OD}/my_feat.csv', index=False)
an[an.is_pr | an.is_biz][['symbol', 'an_dt', 'descr', 'is_pr', 'is_biz', 'own_rd']].to_csv(f'{OD}/my_pr_biz_rows.csv',
                                                                                           index=False)
print('rows', len(res), 'PR rows', int(an.is_pr.sum()), 'BIZ rows', int(an.is_biz.sum()))
print('pr30>=1:', int((res.pr30 >= 1).sum()), ' biz_rx45>0:', int((res.biz_rx45 > 0).sum()),
      ' rdchg<-7 (ok):', int(((res.rdchg < -7) & res.rdchg_ok).sum()))
