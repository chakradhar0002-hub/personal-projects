#!/usr/bin/env python3
"""CORPORATE NEWS FLOW family - point-in-time features (NO outcome of any trade is read here).

usage: python3 build_features.py OUT SP
  OUT = .../more_signals/news (writes only into OUT/work), SP = scratchpad root (read-only inputs)
Inputs (read-only):
  report/nse_events.db           an (NSE corporate announcements), fr (2020 results filing dates)
  OUT/downloads/board_meetings.csv   NSE board-meeting intimations (bm_date, bm_timestamp = broadcast)
  OUT/downloads/sast29.csv           NSE SAST Reg 29 disclosures (promoter / large-holder acquisitions and sales)
  sector_lab/data/{sessions,events,returns,index_close}.csv  (returns only for days BEFORE each decision)
  perf/features/panel.csv        keys + i_cut, i_rd, i_react, in_fo_events, lag21, vol_ratio_5_60, XN, W, cut_rsi14
  ta/build/placebo_ta.csv.gz     placebo A stock-day keys (symbol, i, in_fo, qn_next) - outcome columns NOT read
  tafa/C_post_results/quiet_days.csv.gz  quiet days (symbol, i, day, qn_prev, XN, W, m2_rsi14) - no outcomes
POINT IN TIME: a trade at the close of session d (NSE close = average price 15:00-15:30 IST) is decided at 15:00 IST on
day(d); it can use an announcement / intimation / disclosure only if its broadcast time is < day(d) 15:00.
Trade A decides at the cutoff close (i_cut); trade B at the
reaction close k (i_react). Placebo A day k decides at close k; placebo B quiet day k decides at close k.
Text fields are untrusted data: only matched with fixed regular expressions, never executed or followed.
"""
import sqlite3
import warnings
import sys

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore', message='This pattern is interpreted')
OUT, SP = sys.argv[1], sys.argv[2]
DATA = f'{SP}/sector_lab/data'
W_ = f'{OUT}/work'
LOG = open(f'{W_}/build_features.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + '\n')
    LOG.flush()


DAY = pd.Timedelta(days=1)
CLOSE = pd.Timedelta(hours=15, minutes=30)
ses = pd.read_csv(f'{DATA}/sessions.csv')
SDAY = pd.to_datetime(ses.day).to_numpy()            # session i -> date (datetime64)
SCLOSE = SDAY + np.timedelta64(15 * 60 + 30, 'm')     # session close timestamps (used only to date a reaction)
SDEC = SDAY + np.timedelta64(15 * 60, 'm')            # decision time for a trade at the close of the session
T_LAST = len(SDAY) - 1

# =========================================================================== announcements
con = sqlite3.connect(f'file:{SP}/report/nse_events.db?mode=ro', uri=True)
an = pd.read_sql('SELECT symbol, an_dt, descr, txt FROM an', con)
n0 = len(an)
an = an.drop_duplicates(['symbol', 'an_dt', 'descr', 'txt']).reset_index(drop=True)
an['t'] = pd.to_datetime(an.an_dt, format='%d-%b-%Y %H:%M:%S')
an['descr'] = an.descr.fillna('').str.strip()
tx = an.txt.fillna('').str.lower()
AN_START = pd.Timestamp('2021-03-01')
AN_END = pd.Timestamp('2026-09-30 23:59:59')
P(f'announcements {n0} rows, {len(an)} after removing exact duplicates; {an.symbol.nunique()} symbols; '
  f'{an.t.min()} .. {an.t.max()}')

ROUTINE = {
    'Loss of Share Certificates', 'Loss of share certificate', 'Issue of Duplicate Share Certificate',
    'Certificate under SEBI (Depositories and Participants) Regulations, 2018', 'Copy of Newspaper Publication',
    'Newspaper Advertisements', 'Trading Window', 'Closure of trading window', 'Shareholders meeting',
    'Annual General Meeting', 'Postal Ballot', 'Extra Ordinary Meeting', 'ESOP/ESOS/ESPS', 'ESOP/ESPS/SBEB Scheme',
    'Allotment of ESOP/ESPS', 'Record Date', 'Book Closure', 'Revised Record date', 'Revised Book Closure',
    'Date of payment of dividend', 'Annual Secretarial Compliance Report', 'Annual Disclosure',
    'Business Responsibility & Sustainability Report (BRSR)', 'Statement of deviation(s) or variation(s) under Reg. 32',
    'Monitoring Agency Report', 'Registrar & Share Transfer Agent Update', 'Address Change',
    "E-mail ID for Investor's Grievance Redressal", 'Structural Digital Database',
    'Quarterly Compliance Report on Corporate governance - within 21 days from the end of the quarter',
    'Disclosure under SEBI Takeover Regulations', 'Code of Conduct under SEBI(PIT) Reg., 2015',
    'Code of conduct under SEBI (PIT) Regulations', 'Trading Plan under PIT', 'Trading Plan under SEBI (PIT) Regulations',
    'Trading Plan under SEBI (PIT) Reg., 2015', 'Insider Trading - Others', 'Disclosure under SEBI (PIT) Reg 2015',
    'Notice Of Shareholders Meetings-XBRL', 'Notice of Unitholder meetings', 'Confirmation of payment of Interest/Principal',
    'Date of payment of Interest/Principal', 'Interest Rates Updates', 'Redemption', 'Communication to shareholders as per Reg 30',
}
RESULTS_CYCLE = {
    'Outcome of Board Meeting', 'Board Meeting Intimation', 'Board meeting Cancelled', 'Board Meeting Adjourned',
    'Financial Result Updates', 'Financial Results Updates', 'Integrated Filing- Financial', 'Integrated Filing- Governance',
    'Limited Review Report', "Auditor's report", 'Declaration for audit reports with unmodified opinion(s)',
    'Publish Audited Results', 'Clarification - Financial Results', 'Clarification- Financial Results',
    'Reply to Clarification- Financial results', 'Reply to Clarification Sought- Financial Results',
    'Consolidated Result Updates - IFRS', 'Statement on Impact of Audit Qualifications', 'Investor Presentation',
    'Dividend', 'Dividend Updates',
}
ANALYST = {'Analysts/Institutional Investor Meet/Con. Call Updates',
           'Schedule of Analysts/Institutional Investor Meet/Con. Call',
           'Transcript of Analysts/Institutional Investor Meet/Con. Call',
           'Recording of Analysts/Institutional Investor Meet/Con. Call'}
PRESS = {'Press Release', 'Press Release (Revised)'}
GENERAL = {'Updates', 'General Updates', 'General updates'}
ORDER_DESCR = {'Bagging/Receiving of orders/contracts', 'Bagging orders/contract', 'Awarding of order(s)/contract(s)',
               'Awarding orders/contract'}
WIN_RX = (r'(work orders?|letter of award|letter of acceptance|\bloa\b|\bloi\b|letter of intent|\bbag(s|ged)?\b|'
          r'\bsecure[sd]?\b|\bwins?\b|\bwon\b|awarded|receiv\w* (an? |the |new |large |significant |major |'
          r'repeat |export |domestic |\w+ )?(orders?|contracts?)|orders? (worth|valued|amounting|aggregating|of rs)|'
          r'order inflow|lowest bidder|\bl-?1 bidder)')
NEG_RX = (r'(\btax|gst|commissioner|penalt|demand|court|tribunal|nclt|show cause|assessment|authorit|appellate|'
          r'customs|excise|arbitra|regulatory order|\bcbi\b|\bed\b|enforcement|sebi order|income.tax|warning letter|'
          r'\bfda\b|observation|disqualif|blacklist|debar)')
BIZ_RX = (r'(business update|quarterly update|provisional (business|figures|numbers|data)|business performance update|'
          r'operational update|quarterly business|sales (volume|number|figure)s?|auto sales|monthly sales|'
          r'sales for the month|production (and|&) sales|key business parameters|business figures)')
EVENT_DESCR = {
    'Acquisition', 'Amalgamation/Merger', 'Scheme of Arrangement', 'Demerger', 'Sale or disposal',
    'Sale or disposal of unit/ division/subsidiary', 'Diversification/Disinvestment', 'Agreements',
    'Memorandum of Understanding/Agreements', "Agreements/Contracts/Arrangements/ MOU's PARA A",
    "Agreements/Contracts/Arrangements/ MOU's PARA B", 'Agreements,Contracts,Arrangements,MOU-XBRL',
    'Arrangements for strategic, technical, manufacturing, or marketing tie up', 'Capacity addition',
    'Capacity addition/product launch', 'Product launch', 'Commencement of commercial production/operations',
    'Buyback', 'Buyback - others', 'Buyback - Open Market', 'Buyback - Tender offer',
    'Public Announcement - Buyback of Shares', 'Bonus', 'Stock split', 'Split of shares', 'Issue of Securities',
    'Qualified Institutional Placement', 'Qualified Institutional Placements', 'Rights Issue', 'Preferential issue',
    'Preferential Issue', 'Open Offer', 'Public Announcement-Open Offer',
    'Granting/withdrawal/surrender/cancellation/suspension of key licenses/ regulatory approvals',
    'Grant of licenses/regulatory approvals', 'Adoption of new line(s) of business',
    'Credit Rating', 'Credit Rating- Revision', 'Credit Rating- New', 'Credit Rating- Others',
} | ORDER_DESCR
d = an.descr
an['SUBST'] = ~(d.isin(ROUTINE) | d.isin(RESULTS_CYCLE) | d.isin(ANALYST))
an['PR'] = d.isin(PRESS)
an['ORDER'] = d.isin(ORDER_DESCR) | ((d.isin(GENERAL) | d.isin(PRESS)) & tx.str.contains(WIN_RX)
                                     & ~tx.str.contains(NEG_RX))
an['ACQ'] = d.eq('Acquisition')
iscr = d.str.startswith('Credit Rating')
an['CRUP'] = iscr & tx.str.contains('upgrad') & ~tx.str.contains('downgrad')
an['CRDN'] = iscr & tx.str.contains('downgrad') & ~tx.str.contains('upgrad')
an['CALLANN'] = (d.isin(ANALYST) & ~d.str.startswith('Transcript') & ~d.str.startswith('Recording')
                 & ~tx.str.contains(r'(transcript|recording|audio|video|link of)'))
an['BIZ'] = d.eq('Monthly Business Updates') | ((d.isin(GENERAL) | d.isin(PRESS)) & tx.str.contains(BIZ_RX))
an['EVENT'] = d.isin(EVENT_DESCR) | an.ORDER
for c in ['SUBST', 'PR', 'ORDER', 'ACQ', 'CRUP', 'CRDN', 'CALLANN', 'BIZ', 'EVENT']:
    P(f'  class {c:8s} {int(an[c].sum()):7d} announcements')

# own results days (calendar dates results_date and results_date + 1) are excluded from every news count
ev = pd.read_csv(f'{DATA}/events.csv')
ev['rd'] = pd.to_datetime(ev.results_date)
RDAYS = {s: set(g.rd.dt.normalize()) | set(g.rd.dt.normalize() + DAY) for s, g in ev.groupby('symbol')}
an['own_rd'] = [t.normalize() in RDAYS.get(s, ()) for s, t in zip(an.symbol, an.t)]
P(f'  announcements on own results day / day after (excluded from counts): {int(an.own_rd.sum())}')
anx = an[~an.own_rd]
STREAM = {}
for c in ['SUBST', 'PR', 'ORDER', 'ACQ', 'CRUP', 'CRDN', 'CALLANN', 'BIZ', 'EVENT']:
    # EVENT / CALLANN keep results-day items (EVENT_K is about news on the results days besides the results)
    src = an if c in ('EVENT', 'CALLANN') else anx
    g = src[src[c]]
    STREAM[c] = {s: np.sort(gg.t.to_numpy()) for s, gg in g.groupby('symbol')}
BIZ_ROWS = an[an.BIZ][['symbol', 't']].copy()


def count_in(stream, syms, t0, t1):
    """number of items of stream with t0 <= t < t1, per row (t0, t1 datetime64 arrays)."""
    out = np.zeros(len(syms), int)
    for s in np.unique(syms):
        ix = np.flatnonzero(syms == s)
        a = stream.get(s)
        if a is None or len(a) == 0:
            continue
        out[ix] = np.searchsorted(a, t1[ix], 'left') - np.searchsorted(a, t0[ix], 'left')
    return out


def news_block(df, syms, T):
    """news features as of decision time T (datetime64 array)."""
    T = np.asarray(T, 'datetime64[ns]')
    d30, d21, d45, d90 = (np.timedelta64(k, 'D') for k in (30, 21, 45, 90))
    df['NEWS30'] = count_in(STREAM['SUBST'], syms, T - d30, T)
    # norm: substantive announcements in [T-395d, T-30d), scaled to 30 days by the days the database covers
    w0 = np.maximum(T - np.timedelta64(395, 'D'), np.datetime64(AN_START))
    w1 = T - d30
    cov_days = (w1 - w0) / np.timedelta64(1, 'D')
    cnt = count_in(STREAM['SUBST'], syms, w0, w1)
    norm = np.where(cov_days >= 90, cnt / np.maximum(cov_days, 1) * 30, np.nan)
    ok30 = (T - d30) >= np.datetime64(AN_START)
    df['NORM30'] = norm
    df['NEWSR'] = np.where(ok30 & np.isfinite(norm), (df.NEWS30 + 1) / (norm + 1), np.nan)
    df.loc[~ok30, 'NEWS30'] = np.nan
    for c, dd in (('PR', d30), ('ORDER', d30), ('ACQ', d30), ('CRUP', d90), ('CRDN', d90)):
        v = count_in(STREAM[c], syms, T - dd, T).astype(float)
        v[(T - dd) < np.datetime64(AN_START)] = np.nan
        df[f'{c}{int(dd / np.timedelta64(1, "D"))}'] = v
    return df


# business-update reaction: stock minus Nifty return on the session the update reached the market
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
RSYM = {s: j for j, s in enumerate(ret.columns)}
R = ret.to_numpy(float) * 100
NIF = pd.read_csv(f'{DATA}/index_close.csv', index_col=0)['Nifty 50'].to_numpy(float)
NR = np.r_[np.nan, NIF[1:] / NIF[:-1] - 1] * 100
assert len(NIF) == len(SDAY) == len(R)
bt = BIZ_ROWS.t.to_numpy('datetime64[ns]')
BIZ_ROWS['s'] = np.searchsorted(SCLOSE, bt, 'right')   # first session whose close is after the broadcast
BIZ_ROWS['rx'] = [R[s_, RSYM[sym]] - NR[s_] if (s_ <= T_LAST and sym in RSYM) else np.nan
                  for sym, s_ in zip(BIZ_ROWS.symbol, BIZ_ROWS.s)]
BIZS = {s: (g.s.to_numpy(int), g.t.to_numpy('datetime64[ns]'), g.rx.to_numpy(float))
        for s, g in BIZ_ROWS.groupby('symbol')}


def biz_block(df, syms, T, i_dec):
    """business updates broadcast in [T-45d, T) whose reaction session is < the decision session i_dec."""
    T = np.asarray(T, 'datetime64[ns]')
    n_, rx_ = np.zeros(len(syms), int), np.full(len(syms), np.nan)
    for r_, (s, t, i0) in enumerate(zip(syms, T, i_dec)):
        b = BIZS.get(s)
        if b is None:
            continue
        m = (b[1] >= t - np.timedelta64(45, 'D')) & (b[1] < t) & (b[0] < i0) & np.isfinite(b[2])
        if m.any():
            n_[r_] = m.sum()
            rx_[r_] = b[2][m].sum()
    df['BIZ_N45'] = n_
    df['BIZ_RX'] = rx_
    return df


# =========================================================================== board meeting intimations
bm = pd.read_csv(f'{OUT}/downloads/board_meetings.csv')
bm['bd'] = pd.to_datetime(bm.bm_date, format='%d-%b-%Y', errors='coerce')
bm['ts'] = pd.to_datetime(bm.bm_timestamp, format='%d-%b-%Y %H:%M:%S', errors='coerce')
btxt = (bm.bm_purpose.fillna('') + ' ' + bm.bm_desc.fillna('')).str.lower()
bm['res'] = btxt.str.contains(r'(result|financial statement|financials)')
bm = bm[bm.res & bm.bd.notna() & bm.ts.notna()].copy()
P(f'\nboard meeting rows {len(pd.read_csv(f"{OUT}/downloads/board_meetings.csv"))}; results-type {len(bm)}; '
  f'{bm.symbol.nunique()} symbols; meetings {bm.bd.min().date()} .. {bm.bd.max().date()}')
# one record per (symbol, meeting date): first intimation broadcast
BMM = bm.groupby(['symbol', 'bd']).ts.min().reset_index()
BMM['lead'] = (BMM.bd - BMM.ts.dt.normalize()).dt.days
BMM = BMM[BMM.lead >= 0]
BMS = {s: g.sort_values('bd') for s, g in BMM.groupby('symbol')}

# =========================================================================== SAST Reg 29
sa = pd.read_csv(f'{OUT}/downloads/sast29.csv', dtype=str)
sa['t1'] = pd.to_datetime(sa.timestamp, format='%d-%b-%Y %H:%M', errors='coerce')
sa['t2'] = pd.to_datetime(sa.sysTime, format='%d-%b-%Y %H:%M', errors='coerce')
sa['t'] = sa[['t1', 't2']].max(axis=1)          # the later of filing and dissemination time (conservative)
sa = sa[sa.t.notna()].drop_duplicates(['query_symbol', 'application_no', 'acqSaleType'])
P(f'\nSAST Reg 29 rows {len(sa)} ({sa.query_symbol.nunique()} symbols), {sa.t.min()} .. {sa.t.max()}')
P('  promoterType x acqSaleType:', sa.groupby(['promoterType', 'acqSaleType']).size().to_dict())
P('  acquisitionMode (promoters):', sa[sa.promoterType == 'Y'].acquisitionMode.value_counts().head(8).to_dict())
SAS = {}
# transfers that are not a purchase / sale decision (inter-se promoter transfers, gifts, schemes) are left out
real = ~sa.acquisitionMode.fillna('').str.lower().str.contains(r'inter-se|inter se|gift|scheme|transmission')
buy = sa.acqSaleType.eq('Acquisition') & real
sell = sa.acqSaleType.isin(['Sale', 'Disposal']) & real
P(f'  real-decision rows: promoter buys {int((buy & (sa.promoterType == "Y")).sum())}, promoter sells '
  f'{int((sell & (sa.promoterType == "Y")).sum())}, other holders buys {int((buy & (sa.promoterType != "Y")).sum())}, '
  f'sells {int((sell & (sa.promoterType != "Y")).sum())}')
for nm, m in (('PROMBUY', (sa.promoterType == 'Y') & buy), ('PROMSELL', (sa.promoterType == 'Y') & sell),
              ('HOLDBUY', (sa.promoterType != 'Y') & buy), ('HOLDSELL', (sa.promoterType != 'Y') & sell)):
    SAS[nm] = {s: np.sort(g.t.to_numpy('datetime64[ns]')) for s, g in sa[m].groupby('query_symbol')}


def sast_block(df, syms, T):
    T = np.asarray(T, 'datetime64[ns]')
    for nm in SAS:
        for dd in (30, 90):
            df[f'{nm}{dd}'] = count_in(SAS[nm], syms, T - np.timedelta64(dd, 'D'), T)
    return df


# =========================================================================== results rows
pcols = ['symbol', 'qn', 'quarter', 'period', 'i_cut', 'i_rd', 'i_p1', 'i_react', 'in_fo', 'in_fo_events', 'lag21',
         'vol_ratio_5_60', 'XN', 'W', 'cut_rsi14']
pan = pd.read_csv(f'{SP}/perf/features/panel.csv', usecols=pcols)
assert len(pan) == 3280
res = pan.merge(ev[['symbol', 'qn', 'quarter_end', 'results_date', 'results_time', 'timing']], on=['symbol', 'qn'],
                how='left', validate='1:1')
syms = res.symbol.to_numpy()
TA = SDEC[res.i_cut.to_numpy(int)]
res['T_A'] = TA
res = news_block(res, syms, TA)
res = biz_block(res, syms, TA, res.i_cut.to_numpy(int))
res = sast_block(res, syms, TA)
res['CALLPRE'] = count_in(STREAM['CALLANN'], syms, TA - np.timedelta64(21, 'D'), TA)

# results date vs the same quarter last year (days from quarter end); prior year from events (qn-4) or, for qn 0-3,
# the earliest 2020 NSE results filing of that quarter (fr table)
ev['dtq'] = (ev.rd - pd.to_datetime(ev.quarter_end)).dt.days
prev = ev[['symbol', 'qn', 'dtq']].assign(qn=lambda x: x.qn + 4).rename(columns={'dtq': 'dtq_ly'})
res = res.merge(prev, on=['symbol', 'qn'], how='left')
fr = pd.read_sql('SELECT symbol, from_date, to_date, broadcast FROM fr', con)
fr['te'] = pd.to_datetime(fr.to_date, format='%d-%b-%Y', errors='coerce')
fr['fd'] = pd.to_datetime(fr.from_date, format='%d-%b-%Y', errors='coerce')
fr['bd'] = pd.to_datetime(fr.broadcast, format='%d-%b-%Y %H:%M:%S', errors='coerce')
fr = fr[((fr.te - fr.fd).dt.days < 100) & fr.bd.notna()]
f20 = fr.groupby(['symbol', 'te']).bd.min().reset_index()
f20['dtq_fr'] = (f20.bd.dt.normalize() - f20.te).dt.days
res['te_ly'] = pd.to_datetime(res.quarter_end) - pd.DateOffset(years=1)
res['te_ly'] = res.te_ly + pd.offsets.MonthEnd(0)
res = res.merge(f20[['symbol', 'te', 'dtq_fr']].rename(columns={'te': 'te_ly'}), on=['symbol', 'te_ly'], how='left')
res['dtq'] = (pd.to_datetime(res.results_date) - pd.to_datetime(res.quarter_end)).dt.days
res['dtq_prev'] = np.where(res.qn <= 3, res.dtq_fr, res.dtq_ly)
res['RDCHG'] = res.dtq - res.dtq_prev
res.loc[res.qn.isin([0, 1, 4]), 'RDCHG'] = np.nan     # comparison year had SEBI COVID deadline extensions

# board meeting intimation lead time and the stock's own norm (median of its previous <= 4 results meetings)
lead, lnorm, n_prev_bm = np.full(len(res), np.nan), np.full(len(res), np.nan), np.zeros(len(res), int)
rdt = pd.to_datetime(res.results_date).to_numpy('datetime64[ns]')
for r_, (s, rd_, T) in enumerate(zip(syms, rdt, TA)):
    g = BMS.get(s)
    if g is None:
        continue
    bd = g.bd.to_numpy('datetime64[ns]')
    dd = (bd - rd_) / np.timedelta64(1, 'D')
    mt = (dd >= -2) & (dd <= 1)
    if mt.any():
        ts0 = g.ts.to_numpy('datetime64[ns]')[mt].min()
        if ts0 < T:
            lead[r_] = (rd_ - ts0.astype('datetime64[D]')) / np.timedelta64(1, 'D')
    pv = g[(g.bd < pd.Timestamp(rd_) - pd.Timedelta(days=30))].tail(4)
    n_prev_bm[r_] = len(pv)
    if len(pv) >= 2:
        lnorm[r_] = pv.lead.median()
res['LEAD'] = lead
res['LEADNORM'] = lnorm
res['LEADCHG'] = res.LEAD - res.LEADNORM

# trade B: material corporate-event news on k-1 or k (from day(k-1) 00:00 to the close of k) - besides the results
k = res.i_react.to_numpy(int)
res['EVENT_K'] = count_in(STREAM['EVENT'], syms, SDAY[k - 1], SDEC[k])
res['ORDER_K'] = count_in({s: np.sort(g.t.to_numpy()) for s, g in an[an.ORDER].groupby('symbol')}, syms, SDAY[k - 1],
                          SDEC[k])
# busy reaction day: number of results (all 212 stocks, any F&O status) with the same reaction session k
busy = ev.groupby('i_react').size()
res['BUSY_K'] = pd.Series(k).map(busy).fillna(0).to_numpy(int)
res['results_for'] = 'Results for ' + res.period + ' (' + res.quarter + ')'
res.drop(columns=['T_A', 'te_ly']).to_csv(f'{W_}/feat_results.csv', index=False, float_format='%.6g')
P(f'\nresults rows {len(res)} written (work/feat_results.csv)')

# coverage
cov = res.groupby('qn').agg(n=('symbol', 'size'),
                            NEWS30=('NEWS30', lambda s: s.notna().mean() * 100),
                            NEWSR=('NEWSR', lambda s: s.notna().mean() * 100),
                            RDCHG=('RDCHG', lambda s: s.notna().mean() * 100),
                            LEAD=('LEAD', lambda s: s.notna().mean() * 100),
                            LEADCHG=('LEADCHG', lambda s: s.notna().mean() * 100))
cov.insert(0, 'results_for', res.groupby('qn').results_for.first())
P('\ncoverage by quarter (% of F&O results with the feature; announcements cover 2021-03-01 .. 2026-09-30):')
P(cov.round(1).to_string())

# =========================================================================== placebo A days
pl = pd.read_csv(f'{SP}/ta/build/placebo_ta.csv.gz', usecols=['symbol', 'day', 'i', 'in_fo', 'qn_next',
                                                               'since_prev_result', 'to_next_result', 'lag_pct',
                                                               'vol_ratio_5_60'])
pl = pl[(pl.in_fo == True) & pl.qn_next.notna()].copy()
pl['qn_next'] = pl.qn_next.astype(int)
keys = set(zip(res.symbol, res.qn))
pl = pl[np.array([(s, q) in keys for s, q in zip(pl.symbol, pl.qn_next)])].reset_index(drop=True)
assert (pl.since_prev_result >= 10).all() and (pl.to_next_result >= 14).all()
ps = pl.symbol.to_numpy()
TP = SDEC[pl.i.to_numpy(int)]
pl = news_block(pl, ps, TP)
pl = biz_block(pl, ps, TP, pl.i.to_numpy(int))
pl = sast_block(pl, ps, TP)
# stock-quarter placebo for results-specific features: the upcoming result's (qn_next) value
rs = res.set_index(['symbol', 'qn'])
for c in ['RDCHG', 'LEAD', 'LEADCHG', 'CALLPRE']:
    pl[c] = rs[c].reindex(list(zip(pl.symbol, pl.qn_next))).to_numpy()
pl.to_csv(f'{W_}/feat_placeboA.csv.gz', index=False, float_format='%.6g', compression='gzip')
P(f'\nplacebo A stock-days {len(pl)} (F&O, no result session within 9 before / 13 after)')

# =========================================================================== placebo B quiet days
qd = pd.read_csv(f'{SP}/tafa/C_post_results/quiet_days.csv.gz', usecols=['symbol', 'i', 'day', 'qn_prev', 'XN',
                                                                          'm2_rsi14', 'W'])
qd = qd[qd.symbol.isin(set(res.symbol))].reset_index(drop=True)
RS = {}
for s, g in ev.groupby('symbol'):
    RS[s] = np.unique(np.r_[g.i_rd.dropna().to_numpy(int), g.i_react.dropna().to_numpy(int)])
kq = qd.i.to_numpy(int)
far = np.ones(len(qd), bool)
for n, (s, kk) in enumerate(zip(qd.symbol, kq)):
    r_ = RS.get(s)
    if r_ is not None and np.any((r_ >= kk - 10) & (r_ <= kk + 22)):
        far[n] = False
qd['no_result_k22'] = far
qs = qd.symbol.to_numpy()
# pre-event news state as of the close two sessions before (as a results cutoff is ~2 sessions before)
T2 = SDEC[kq - 2]
qd = news_block(qd, qs, T2)
qd = sast_block(qd, qs, T2)
qd['EVENT_K'] = count_in(STREAM['EVENT'], qs, SDAY[kq - 1], SDEC[kq])
qd['BUSY_K'] = pd.Series(kq).map(busy).fillna(0).to_numpy(int)
for c in ['RDCHG', 'CALLPRE', 'LEADCHG']:
    qd[c] = rs[c].reindex(list(zip(qd.symbol, qd.qn_prev.fillna(-1).astype(int)))).to_numpy()
qd.to_csv(f'{W_}/feat_placeboB.csv.gz', index=False, float_format='%.6g', compression='gzip')
P(f'quiet days {len(qd)}; no result session in [k-10, k+22]: {far.sum()}; quiet winners (XN > 4) {(qd.W == True).sum()}')
LOG.close()
