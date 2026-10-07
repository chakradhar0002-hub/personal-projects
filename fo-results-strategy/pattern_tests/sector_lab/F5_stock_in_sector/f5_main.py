"""
F5  STOCK-VS-SECTOR PERSISTENCE AND SECTOR SEASONALITY FOR THE USER'S 3-DAY RESULTS WINDOW
==========================================================================================
PRE-REGISTRATION (written before computing any rule outcome; only descriptive data checks were run before).

TRADE / OUTCOME (one horizon only: the user's 3-day window)
  Decision time  = close of the CUTOFF session (2 sessions before the result session), i_cut.
  Entry          = cutoff close.  Exit = Day+1 close (i_p1).   Results dates are public by the cutoff.
  Outcome O3     = events.three_day  (SUM of the 3 daily returns Day-1, Result day, Day+1 = user's definition)
  Three measures per trade:
     raw   = three_day                      - 0.17%   (stock round trip)
     nifty = three_day - nifty_3d           - 0.19%   (+0.02% Nifty futures hedge)
     sect  = three_day - sector_3d          - 0.19% if sector is Nifty Bank / Nifty Financial Services
                                              (index futures exist), else - 0.34% (hedge must be a BASKET of
                                              stock futures: another 0.17% round trip)
  Short-side rules flip the sign of the gross number and pay the same costs.
  Trades: only events with in_fo == True at that time (NaN in_fo treated as not tradable) and three_day known.
  Stock-in-sector rules use only events whose sector_index is a real sector (not the "Nifty 500" fallback).

INFORMATION SET (strictly causal)
  Stock features use only the stock's OWN previous results with qn' < qn and window end i_p1' < i_cut.
  Sector features use only sector x quarter cells of EARLIER quarters (qn' < qn); no current-season information
  at all, so the "later reporters' trailing windows contain earlier reporters' outcomes" bias cannot arise.
  No within-quarter ranking.  Thresholds are fixed numbers, or percentiles of the feature's values pooled over
  EARLIER quarters only (expanding window).
  A sector x quarter "cell" = all reporters (F&O or not) with that sector_index in that quarter; cells with < 3
  reporters are ignored.  FQ (fiscal quarter of year) = qn mod 4 (0 = Q4/Jan-Mar results, 1 = Q1, 2 = Q2, 3 = Q3).

FEATURES
  PX  = mean of own past excess_sector (3-day window minus sector index), >= 4 past results
  PH  = share of own past windows with excess_sector > 0, >= 4 past results
  PN  = mean of own past raw three_day, >= 4 past results          (control: stock-level, not sector-relative)
  ID  = mean of own past |excess_sector| (size of the stock-specific window move), >= 4 past results
  BW  = OLS slope of own past three_day on own past sector_3d (window co-movement with sector), >= 6 past results
  SS  = sector x FQ seasonality: mean over EARLIER YEARS (qn-4, qn-8, ...) of the cell mean three_day; >= 1 earlier year
  EQ  = sector earnings seasonality (Chang-Hartzmark-Solomon-Soltes 2017 idea, sector version):
        mean over earlier same-FQ cells of the cell MEDIAN sales_qoq (clipped to [-1,1])
        minus mean over ALL earlier cells of the cell median sales_qoq; needs >= 1 same-FQ and >= 4 earlier cells
  EQs = same idea at stock level: own mean sales_qoq (clipped [-0.5,0.5]) in earlier same-FQ results minus own mean
        over all earlier results; needs >= 1 same-FQ and >= 4 earlier values
  GX  = sector's habitual results-window excess: mean over ALL earlier cells (>= 4) of the cell mean excess_sector

PRE-REGISTERED RULES (20 in total; each reported raw / minus Nifty / minus sector)
  (a) persistence
   A1  PX > +1%                                   -> BUY
   A2  PX > +2%                                   -> BUY
   A3  PX >= 80th pct of PX pooled over earlier quarters' eligible F&O events (expanding) -> BUY
   A4  PH >= 0.70                                 -> BUY
   A5  PX < -1%                                   -> SHORT (mirror check of persistence)
   A6  diagnostic: per-quarter cross-sectional OLS slope of excess_sector on PX (eligible F&O events),
       t across quarters (not a trade; tests persistence directly)
   A7  control: PN > +1%                          -> BUY
  (b) sector seasonality
   B1  SS > +1%   -> BUY all F&O stocks of that sector reporting in that quarter
   B2  SS > +0.5% -> BUY all F&O stocks of that sector
   B3  EQ > +3 percentage points -> BUY all F&O stocks of that sector
   B4  EQs > +5 percentage points -> BUY that stock  (stock-level counterpart of B3)
   B5  diagnostic, NOT real time: leave-one-year-out stability of sector x FQ means (correlation of a year's cell
       mean with the other years' mean) and the LOYO version of B1 (uses future years -> not tradable)
  (c) co-movement / sector-hedged window
   C1  ID >= expanding 67th pct (earlier quarters) -> BUY ("idiosyncratic reactors": announcement-risk premium)
   C2  ID <= expanding 33rd pct                    -> BUY ("sector-driven" stocks)
   C3  BW >= expanding 67th pct                    -> BUY (high window co-movement; Savor-Wilson systematic-news idea)
   C4  BW <= expanding 33rd pct                    -> BUY
   G1  GX > +0.5% -> LONG stock / SHORT sector for all F&O stocks of that sector (judged also on the sect measure)
   G2  GX < -0.5% -> SHORT stock / LONG sector
  (d) combination (gated): run only if BOTH parts have minus-Nifty net average > 0 over qn 0..13
   D1  A1 and B1
   D2  A1 and B3

STATISTICS
  Unit = quarter: per-quarter equal-weight mean of trades, t = mean/(sd/sqrt(nq)) across quarters with trades.
  Also a trade-level t clustered by entry date.  Splits: qn 0..13 ("first 14") vs qn 14..21 ("last 8").
  Quarters positive; quarters with raw net >= +2% (the user's target).
  Promising = minus-Nifty net > 0 in both halves, |t| >= 2.5, >= 30 trades, and placebo clearly worse.

PLACEBOS (run for every trade rule)
  P1  stock-level rules: in each quarter draw the same number of trades at random from the rule's eligible pool
      (F&O, sector stock, feature defined); 2000 draws.  Sector-level rules (B1-B3, G1-G2): in each quarter draw the
      same number of SECTORS at random among sectors with the feature defined and take all their F&O reporters.
      Report share of draws with t >= actual t (one-sided in the rule's direction).
  P2  persistence rules A1-A4, A5, A7: rebuild the feature from PSEUDO windows (the same 3 sessions shifted 20 sessions
      earlier, skipping any overlap with a results window) and apply the same rule.  If the pseudo feature works as
      well, the effect is generic stock drift, not results-specific.
"""
import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
import sys
sys.path.append('/root/.local/lib/python3.11/site-packages')
import numpy as np
import pandas as pd

pd.set_option('display.width', 250); pd.set_option('display.max_columns', 60); pd.set_option('display.max_rows', 400)
D = os.environ.get('SECTOR_LAB', 'sector_lab') + '/data/'
OUT = os.environ.get('SECTOR_LAB', 'sector_lab') + '/F5_stock_in_sector/'
RNG = np.random.default_rng(20261007)
NDRAW = 2000
C_RAW, C_NIF, C_SEC_FUT, C_SEC_BASKET = 0.0017, 0.0019, 0.0019, 0.0034
FUT_SECTORS = {'Nifty Bank', 'Nifty Financial Services'}
N_RULES = 20

# ------------------------------------------------------------------ load + checks
ev = pd.read_csv(D + 'events.csv')
ret = pd.read_csv(D + 'returns.csv', index_col=0)
icl = pd.read_csv(D + 'index_close.csv', index_col=0)
ses = pd.read_csv(D + 'sessions.csv')
irt = icl.pct_change(fill_method=None)
print('events', ev.shape, 'returns', ret.shape, 'index', icl.shape, 'sessions', len(ses))
assert len(ret) == len(ses) == len(icl)
ev['in_fo'] = ev.in_fo.map({True: True, False: False, 'True': True, 'False': False}).fillna(False).astype(bool)
ev['ok'] = ev.three_day.notna()
ev['fq'] = ev.qn % 4
ev['has_sec'] = ev.sector_index != 'Nifty 500'
ev['sec_cost'] = np.where(ev.sector_index.isin(FUT_SECTORS), C_SEC_FUT, C_SEC_BASKET)
ev = ev.sort_values(['symbol', 'qn']).reset_index(drop=True)
print('in_fo NaN->False; tradable events (F&O, ok):', int((ev.in_fo & ev.ok).sum()),
      ' of which real sector:', int((ev.in_fo & ev.ok & ev.has_sec).sum()))
# coverage of sector indices actually used inside the 3-day windows
used = ev[ev.ok]
for s in sorted(used.sector_index.unique()):
    u = used[used.sector_index == s]
    idx = np.r_[u.i_m1.values, u.i_rd.values, u.i_p1.values]
    print(f'  {s:28s} events {len(u):4d}  NaN index returns inside windows: {int(np.isnan(irt[s].values[idx]).sum())}')

R = ret.values; SYMCOL = {s: k for k, s in enumerate(ret.columns)}
IR = {c: irt[c].values for c in irt.columns}

# results-window sessions per stock (for pseudo-window overlap checks)
win_sessions = {}
for sym, g in ev.groupby('symbol'):
    ss = set()
    for a, b in zip(g.i_cut.values, g.i_p1.values):
        ss.update(range(int(a), int(b) + 1))
    win_sessions[sym] = ss


def pseudo_excess(sym, sec, im1, ird, ip1, shift=20):
    days = [im1 - shift, ird - shift, ip1 - shift]
    if any(d in win_sessions[sym] or d < 1 for d in days):
        return np.nan
    if sym not in SYMCOL:
        return np.nan
    rs = R[days, SYMCOL[sym]]
    xs = IR[sec][days]
    if np.isnan(rs).any() or np.isnan(xs).any():
        return np.nan
    return float(rs.sum() - xs.sum())


ev['pseudo_x'] = [pseudo_excess(s, c, a, b, d) for s, c, a, b, d in
                  zip(ev.symbol, ev.sector_index, ev.i_m1, ev.i_rd, ev.i_p1)]

# ------------------------------------------------------------------ stock-level features (own past results only)
cols = {k: np.full(len(ev), np.nan) for k in ['n_past', 'PX', 'PH', 'PN', 'ID', 'BW', 'EQs', 'PXpseudo']}
sq_clip_s = ev.sales_qoq.clip(-0.5, 0.5)
for sym, g in ev.groupby('symbol'):
    gi = g.index.values
    for k in gi:
        qn, icut, fq = ev.at[k, 'qn'], ev.at[k, 'i_cut'], ev.at[k, 'fq']
        pm = (g.qn.values < qn) & (g.i_p1.values < icut)
        past = g[pm & g.ok.values]
        n = len(past)
        cols['n_past'][k] = n
        if n >= 4:
            x = past.excess_sector.values
            cols['PX'][k] = x.mean()
            cols['PH'][k] = (x > 0).mean()
            cols['PN'][k] = past.three_day.mean()
            cols['ID'][k] = np.abs(x).mean()
            ps = past.pseudo_x.dropna()
            if len(ps) >= 4:
                cols['PXpseudo'][k] = ps.mean()
        if n >= 6:
            sx = past.sector_3d.values; sy = past.three_day.values
            v = np.var(sx, ddof=1)
            if v > 0:
                cols['BW'][k] = np.cov(sx, sy, ddof=1)[0, 1] / v
        pall = sq_clip_s.loc[g.index[pm]].dropna()
        psame = sq_clip_s.loc[g.index[pm & (g.fq.values == fq)]].dropna()
        if len(pall) >= 4 and len(psame) >= 1:
            cols['EQs'][k] = psame.mean() - pall.mean()
for k, v in cols.items():
    ev[k] = v

# ------------------------------------------------------------------ sector x quarter cells (earlier quarters only)
evs = ev[ev.ok & ev.has_sec].copy()
evs['sq_clip'] = evs.sales_qoq.clip(-1, 1)
cell = evs.groupby(['sector_index', 'qn']).agg(n=('symbol', 'size'), m3=('three_day', 'mean'),
                                              mx=('excess_sector', 'mean'), msq=('sq_clip', 'median')).reset_index()
cell = cell[cell.n >= 3]
cdict = {(s, q): r for s, q, r in zip(cell.sector_index, cell.qn, cell.itertuples())}
sec_feat = []
for s in sorted(evs.sector_index.unique()):
    for q in range(22):
        same = [cdict[(s, qq)] for qq in range(q - 4, -1, -4) if (s, qq) in cdict]
        allp = [cdict[(s, qq)] for qq in range(q) if (s, qq) in cdict]
        SS = np.mean([c.m3 for c in same]) if len(same) >= 1 else np.nan
        GX = np.mean([c.mx for c in allp]) if len(allp) >= 4 else np.nan
        sq_same = [c.msq for c in same if not np.isnan(c.msq)]
        sq_all = [c.msq for c in allp if not np.isnan(c.msq)]
        EQ = (np.mean(sq_same) - np.mean(sq_all)) if (len(sq_same) >= 1 and len(sq_all) >= 4) else np.nan
        sec_feat.append(dict(sector_index=s, qn=q, SS=SS, GX=GX, EQ=EQ, n_same=len(same), n_all=len(allp)))
sec_feat = pd.DataFrame(sec_feat)
ev = ev.merge(sec_feat[['sector_index', 'qn', 'SS', 'GX', 'EQ']], on=['sector_index', 'qn'], how='left')
ev.loc[~ev.has_sec, ['SS', 'GX', 'EQ']] = np.nan
sec_feat.to_csv(OUT + 'f5_sector_features.csv', index=False)

# tradable pool for all rules
T = ev[ev.in_fo & ev.ok & ev.has_sec].copy()
print('tradable sector-stock events:', len(T), ' quarters:', T.qn.nunique())


def expanding_pct(df, feat, p):
    """threshold for quarter q = p-th percentile of feature values of tradable events in quarters < q"""
    th = {}
    for q in range(22):
        v = df.loc[(df.qn < q) & df[feat].notna(), feat].values
        th[q] = np.percentile(v, p) if len(v) >= 50 else np.nan
    return df.qn.map(th)


for f in ['PX', 'ID', 'BW']:
    for p in [33, 67, 80]:
        T[f'{f}_p{p}'] = expanding_pct(T, f, p)

# ------------------------------------------------------------------ evaluation helpers


def trade_values(tr, side):
    raw = side * tr.three_day.values - C_RAW
    nif = side * tr.excess_nifty.values - C_NIF
    sec = side * tr.excess_sector.values - tr.sec_cost.values
    return raw, nif, sec


def qstats(qn, x):
    s = pd.Series(x).groupby(np.asarray(qn)).mean()
    n = len(s)
    t = s.mean() / (s.std(ddof=1) / np.sqrt(n)) if n > 2 and s.std(ddof=1) > 0 else np.nan
    return s, t


def cluster_t(x, cl):
    x = np.asarray(x); m = x.mean(); N = len(x)
    g = pd.Series(x - m).groupby(np.asarray(cl)).sum().values
    se = np.sqrt((g ** 2).sum()) / N
    return m / se if se > 0 else np.nan


def evaluate(tr, name, side=+1):
    if len(tr) == 0:
        return dict(rule=name, trades=0)
    raw, nif, sec = trade_values(tr, side)
    qr, t_raw = qstats(tr.qn, raw)
    qn_, t_nif = qstats(tr.qn, nif)
    qs, t_sec = qstats(tr.qn, sec)
    first = qn_[qn_.index <= 13]; last = qn_[qn_.index >= 14]
    return dict(rule=name, side='long' if side > 0 else 'short', trades=len(tr), quarters=len(qn_),
                q_first=len(first), q_last=len(last),
                avg_raw_net=raw.mean() * 100, avg_nifty_net=nif.mean() * 100, avg_sector_net=sec.mean() * 100,
                perq_raw=qr.mean() * 100, perq_nifty=qn_.mean() * 100, perq_sector=qs.mean() * 100,
                t_q_raw=t_raw, t_q_nifty=t_nif, t_q_sector=t_sec,
                t_date_nifty=cluster_t(nif, tr.i_cut.values),
                first14_nifty=first.mean() * 100 if len(first) else np.nan,
                last8_nifty=last.mean() * 100 if len(last) else np.nan,
                first14_raw=qr[qr.index <= 13].mean() * 100, last8_raw=qr[qr.index >= 14].mean() * 100,
                qpos_nifty=f'{int((qn_ > 0).sum())} of {len(qn_)}', qpos_raw=f'{int((qr > 0).sum())} of {len(qr)}',
                q_ge2_raw=f'{int((qr >= 0.02).sum())} of {len(qr)}',
                win_nifty=(nif > 0).mean() * 100, win_raw=(raw > 0).mean() * 100,
                max_q_raw=qr.max() * 100, min_q_raw=qr.min() * 100)


RULES = {}   # name -> (mask over T, side, kind ['stock'|'sector'], pool mask, feature)


def add(name, mask, side, kind, pool, feat):
    RULES[name] = (mask.fillna(False).values if hasattr(mask, 'fillna') else mask, side, kind,
                   pool.fillna(False).values if hasattr(pool, 'fillna') else pool, feat)


poolPX = T.PX.notna()
add('A1 PX>+1%', T.PX > 0.01, +1, 'stock', poolPX, 'PX')
add('A2 PX>+2%', T.PX > 0.02, +1, 'stock', poolPX, 'PX')
add('A3 PX>=exp80pct', T.PX >= T.PX_p80, +1, 'stock', poolPX & T.PX_p80.notna(), 'PX')
add('A4 PH>=0.70', T.PH >= 0.70, +1, 'stock', T.PH.notna(), 'PH')
add('A5 PX<-1% SHORT', T.PX < -0.01, -1, 'stock', poolPX, 'PX')
add('A7 ctrl PN>+1%', T.PN > 0.01, +1, 'stock', T.PN.notna(), 'PN')
add('B1 SS>+1%', T.SS > 0.01, +1, 'sector', T.SS.notna(), 'SS')
add('B2 SS>+0.5%', T.SS > 0.005, +1, 'sector', T.SS.notna(), 'SS')
add('B3 EQ>+3pp', T.EQ > 0.03, +1, 'sector', T.EQ.notna(), 'EQ')
add('B4 EQs>+5pp', T.EQs > 0.05, +1, 'stock', T.EQs.notna(), 'EQs')
add('C1 ID>=exp67pct', T.ID >= T.ID_p67, +1, 'stock', T.ID.notna() & T.ID_p67.notna(), 'ID')
add('C2 ID<=exp33pct', T.ID <= T.ID_p33, +1, 'stock', T.ID.notna() & T.ID_p33.notna(), 'ID')
add('C3 BW>=exp67pct', T.BW >= T.BW_p67, +1, 'stock', T.BW.notna() & T.BW_p67.notna(), 'BW')
add('C4 BW<=exp33pct', T.BW <= T.BW_p33, +1, 'stock', T.BW.notna() & T.BW_p33.notna(), 'BW')
add('G1 GX>+0.5% long-vs-sector', T.GX > 0.005, +1, 'sector', T.GX.notna(), 'GX')
add('G2 GX<-0.5% short-vs-sector', T.GX < -0.005, -1, 'sector', T.GX.notna(), 'GX')

results = []; trades_out = []; qrows = []
base = evaluate(T, 'BASELINE all F&O sector stocks (not a rule)')
base_px = evaluate(T[poolPX.values], 'BASELINE eligible PX pool (not a rule)')
results += [base, base_px]


def run_rule(name):
    mask, side, kind, pool, feat = RULES[name]
    tr = T[mask]
    r = evaluate(tr, name, side); r['kind'] = kind
    raw, nif, sec = trade_values(tr, side)
    tt = tr[['symbol', 'qn', 'quarter', 'results_date', 'sector_index', 'cutoff', 'day_p1', 'three_day', 'excess_nifty',
             'excess_sector', feat]].copy()
    tt.insert(0, 'rule', name); tt['side'] = side
    tt['raw_net'] = raw; tt['nifty_net'] = nif; tt['sector_net'] = sec
    trades_out.append(tt.rename(columns={feat: 'feature_value'}).assign(feature=feat))
    for q, g in tt.groupby('qn'):
        qrows.append(dict(rule=name, qn=q, n=len(g), raw_net=g.raw_net.mean() * 100, nifty_net=g.nifty_net.mean() * 100,
                          sector_net=g.sector_net.mean() * 100, picks=' '.join(g.symbol.tolist())))
    return r


for name in list(RULES):
    results.append(run_rule(name))

# ---- A6 diagnostic: per-quarter cross-sectional slope of excess_sector on PX
sl = []
for q, g in T[poolPX.values].groupby('qn'):
    if len(g) >= 10:
        x = g.PX.values; y = g.excess_sector.values
        b = np.cov(x, y, ddof=1)[0, 1] / np.var(x, ddof=1)
        y3 = g.three_day.values
        b3 = np.cov(x, y3, ddof=1)[0, 1] / np.var(x, ddof=1)
        sl.append(dict(qn=q, n=len(g), slope_exsec=b, slope_3d=b3, corr_exsec=np.corrcoef(x, y)[0, 1]))
sl = pd.DataFrame(sl)
sl.to_csv(OUT + 'f5_A6_slopes.csv', index=False)
def tq(v):
    v = np.asarray(v); return v.mean() / (v.std(ddof=1) / np.sqrt(len(v)))
print('\nA6 persistence slope of current excess_sector on past PX (per quarter):')
print(f'  quarters {len(sl)}  mean slope {sl.slope_exsec.mean():.3f}  t {tq(sl.slope_exsec):.2f}  '
      f'first14 {sl[sl.qn<=13].slope_exsec.mean():.3f}  last8 {sl[sl.qn>=14].slope_exsec.mean():.3f}  '
      f'mean corr {sl.corr_exsec.mean():.3f}   | slope of raw 3-day on PX: {sl.slope_3d.mean():.3f} t {tq(sl.slope_3d):.2f}')
results.append(dict(rule='A6 diag slope exsec~PX', trades=int(sl.n.sum()), quarters=len(sl),
                    t_q_nifty=tq(sl.slope_exsec), perq_nifty=sl.slope_exsec.mean(),
                    first14_nifty=sl[sl.qn <= 13].slope_exsec.mean(), last8_nifty=sl[sl.qn >= 14].slope_exsec.mean(),
                    kind='diagnostic (slope, not %)'))

# ---- B5 diagnostic (NOT real time): leave-one-year-out seasonality stability
cc = cell.copy(); cc['fq'] = cc.qn % 4
rows = []
for (s, fq), g in cc.groupby(['sector_index', 'fq']):
    if len(g) < 3:
        continue
    for _, r in g.iterrows():
        other = g[g.qn != r.qn].m3.mean()
        rows.append(dict(sector_index=s, fq=fq, qn=r.qn, m3=r.m3, loyo=other))
loyo = pd.DataFrame(rows)
print('\nB5 (not real time) LOYO: corr(cell mean, other-years mean) = %.3f over %d cells' %
      (np.corrcoef(loyo.m3, loyo.loyo)[0, 1], len(loyo)))
# also the same correlation after removing the common quarter effect (market move of the season)
loyo['m3_dm'] = loyo.m3 - loyo.groupby('qn').m3.transform('mean')
cc['m3_dm'] = cc.m3 - cc.groupby('qn').m3.transform('mean')
rows = []
for (s, fq), g in cc.groupby(['sector_index', 'fq']):
    if len(g) < 3:
        continue
    for _, r in g.iterrows():
        rows.append(dict(m=r.m3_dm, o=g[g.qn != r.qn].m3_dm.mean()))
rr = pd.DataFrame(rows)
print('    after removing each quarter\'s all-sector mean: corr = %.3f' % np.corrcoef(rr.m, rr.o)[0, 1])
# placebo for that correlation: shuffle FQ labels within sector
pc = []
for d in range(500):
    c2 = cc.copy()
    c2['fq'] = c2.groupby('sector_index').fq.transform(lambda v: RNG.permutation(v.values))
    rows = []
    for (s, fq), g in c2.groupby(['sector_index', 'fq']):
        if len(g) < 3:
            continue
        for _, r in g.iterrows():
            rows.append((r.m3_dm, g[g.qn != r.qn].m3_dm.mean()))
    a = np.array(rows); pc.append(np.corrcoef(a[:, 0], a[:, 1])[0, 1])
pc = np.array(pc)
print('    placebo (FQ labels shuffled within sector, 500 draws): mean corr %.3f, share >= actual %.3f' %
      (pc.mean(), (pc >= np.corrcoef(rr.m, rr.o)[0, 1]).mean()))
lmap = {(s, q): v for s, q, v in zip(loyo.sector_index, loyo.qn, loyo.loyo)}
T['SS_loyo'] = [lmap.get((s, q), np.nan) for s, q in zip(T.sector_index, T.qn)]
r = evaluate(T[(T.SS_loyo > 0.01).values], 'B5 LOYO SS>+1% (NOT REAL TIME)'); r['kind'] = 'diagnostic'
results.append(r)

# ---- D gated combos
res_df = pd.DataFrame(results).set_index('rule')
def gate(nm):
    return res_df.loc[nm, 'first14_nifty'] > 0
for dname, a, b in [('D1 A1&B1', 'A1 PX>+1%', 'B1 SS>+1%'), ('D2 A1&B3', 'A1 PX>+1%', 'B3 EQ>+3pp')]:
    ok = gate(a) and gate(b)
    print(f'\n{dname}: gate {a} first14 {res_df.loc[a,"first14_nifty"]:.3f}, {b} first14 {res_df.loc[b,"first14_nifty"]:.3f} -> {"RUN" if ok else "NOT RUN (gate failed)"}')
    if ok:
        m1 = RULES[a][0] & RULES[b][0]
        add(dname, m1, +1, 'stock', RULES[a][3] & RULES[b][3], 'PX')
        results.append(run_rule(dname))
    else:
        results.append(dict(rule=dname, trades=0, kind='gated out'))

res = pd.DataFrame(results)

# ------------------------------------------------------------------ placebos P1 (all trade rules) and P2 (persistence)
def placebo_stock(name, ndraw=NDRAW):
    mask, side, kind, pool, feat = RULES[name]
    tr = T[mask]
    if len(tr) < 5:
        return None
    _, nif_act, _ = trade_values(tr, side)
    _, t_act = qstats(tr.qn, nif_act)
    k_q = tr.groupby('qn').size()
    P = T[pool]
    _, nifP, _ = trade_values(P, side)
    rawP = side * P.three_day.values - C_RAW
    byq = {q: np.flatnonzero(P.qn.values == q) for q in k_q.index}
    ts = np.empty(ndraw); ms = np.empty(ndraw); mr = np.empty(ndraw)
    for d in range(ndraw):
        qm = []; qr = []
        for q, k in k_q.items():
            ix = byq[q]
            pick = RNG.choice(ix, size=min(k, len(ix)), replace=False)
            qm.append(nifP[pick].mean()); qr.append(rawP[pick].mean())
        qm = np.array(qm)
        ms[d] = qm.mean(); mr[d] = np.mean(qr)
        ts[d] = qm.mean() / (qm.std(ddof=1) / np.sqrt(len(qm))) if len(qm) > 2 else np.nan
    return dict(rule=name, placebo='P1 random picks from pool, same count per quarter', draws=ndraw,
                actual_t=t_act, actual_perq_nifty=pd.Series(nif_act).groupby(tr.qn.values).mean().mean() * 100,
                placebo_mean_perq_nifty=ms.mean() * 100, placebo_mean_perq_raw=mr.mean() * 100,
                placebo_mean_t=np.nanmean(ts), share_t_ge_actual=np.nanmean(ts >= t_act))


def placebo_sector(name, ndraw=NDRAW):
    mask, side, kind, pool, feat = RULES[name]
    tr = T[mask]
    if len(tr) < 5:
        return None
    _, nif_act, _ = trade_values(tr, side)
    _, t_act = qstats(tr.qn, nif_act)
    P = T[pool].copy()
    _, P['nif'], _ = trade_values(P, side)
    P['rawn'] = side * P.three_day.values - C_RAW
    m_q = tr.groupby('qn').sector_index.nunique()
    secq = {q: P[P.qn == q].groupby('sector_index') for q in m_q.index}
    secsum = {q: (g.nif.sum(), g.nif.size(), g.rawn.sum()) for q, g in secq.items()}
    ts = np.empty(ndraw); ms = np.empty(ndraw); mr = np.empty(ndraw)
    for d in range(ndraw):
        qm = []; qr = []
        for q, m in m_q.items():
            s_sum, s_n, r_sum = secsum[q]
            pick = RNG.choice(len(s_sum), size=min(m, len(s_sum)), replace=False)
            qm.append(s_sum.values[pick].sum() / s_n.values[pick].sum())
            qr.append(r_sum.values[pick].sum() / s_n.values[pick].sum())
        qm = np.array(qm)
        ms[d] = qm.mean(); mr[d] = np.mean(qr)
        ts[d] = qm.mean() / (qm.std(ddof=1) / np.sqrt(len(qm))) if len(qm) > 2 else np.nan
    return dict(rule=name, placebo='P1 random sectors, same number per quarter', draws=ndraw, actual_t=t_act,
                actual_perq_nifty=pd.Series(nif_act).groupby(tr.qn.values).mean().mean() * 100,
                placebo_mean_perq_nifty=ms.mean() * 100, placebo_mean_perq_raw=mr.mean() * 100,
                placebo_mean_t=np.nanmean(ts), share_t_ge_actual=np.nanmean(ts >= t_act))


pl = []
for name, (mask, side, kind, pool, feat) in RULES.items():
    p = placebo_stock(name) if kind == 'stock' else placebo_sector(name)
    if p:
        pl.append(p)
# P2 pseudo-window feature for persistence rules
P2 = {'A1 PX>+1%': ('PXpseudo', lambda v: v > 0.01, +1), 'A2 PX>+2%': ('PXpseudo', lambda v: v > 0.02, +1),
      'A5 PX<-1% SHORT': ('PXpseudo', lambda v: v < -0.01, -1)}
for name, (f, fn, side) in P2.items():
    tr = T[fn(T[f]).fillna(False).values]
    r = evaluate(tr, name + ' [P2 pseudo-window feature]', side)
    pl.append(dict(rule=name, placebo='P2 same rule on pseudo (non-results) window history', draws=1,
                   actual_t=res.set_index('rule').loc[name, 't_q_nifty'], placebo_trades=r['trades'],
                   placebo_mean_perq_nifty=r.get('perq_nifty'), placebo_mean_perq_raw=r.get('perq_raw'),
                   placebo_mean_t=r.get('t_q_nifty')))
pl = pd.DataFrame(pl)

# ------------------------------------------------------------------ output
res['promising'] = False
for i, r in res.iterrows():
    if r.get('kind') in ('stock', 'sector') and r.get('trades', 0) >= 30:
        p = pl[(pl.rule == r.rule) & pl.placebo.str.startswith('P1')]
        ok = (r.first14_nifty > 0 and r.last8_nifty > 0 and abs(r.t_q_nifty) >= 2.5 and len(p) and
              p.share_t_ge_actual.iloc[0] < 0.05)
        res.at[i, 'promising'] = bool(ok)
res.to_csv(OUT + 'f5_summary.csv', index=False)
pd.DataFrame(qrows).to_csv(OUT + 'f5_quarterly.csv', index=False)
pd.concat(trades_out).to_csv(OUT + 'f5_trades.csv', index=False)
pl.to_csv(OUT + 'f5_placebo.csv', index=False)
ev.to_csv(OUT + 'f5_event_features.csv', index=False)

show = ['rule', 'trades', 'quarters', 'perq_raw', 'perq_nifty', 'perq_sector', 't_q_nifty', 't_date_nifty',
        'first14_nifty', 'last8_nifty', 'qpos_nifty', 'q_ge2_raw', 'max_q_raw', 'win_nifty', 'promising']
print('\n=== SUMMARY (percent; per-quarter averages after costs) ===')
print(res[show].round(3).to_string(index=False))
print('\n=== PLACEBOS ===')
print(pl.round(3).to_string(index=False))
print(f'\nPre-registered rules: {N_RULES} (A1-A7, B1-B5, C1-C4, G1-G2, D1-D2), one horizon (3-day window), '
      f'3 measures each. Promising: {res[res.promising].rule.tolist()}')
