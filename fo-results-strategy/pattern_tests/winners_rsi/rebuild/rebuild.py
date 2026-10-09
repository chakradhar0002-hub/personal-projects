"""Independent rebuild of the pre-registered rule "results winners with RSI(14) above 50" (W_RSI_HI, H20, long, Nifty hedged).

Inputs ONLY (no tafa/C_post_results output and no ta/build/events_ta.csv are read here):
  sector_lab/data/events.csv, sessions.csv, returns.csv, index_close.csv ; ta/build/adjusted_ohlcv.csv.gz (closes only)
  fa/build/fa_panel.csv is read ONLY for its in_fo flag to fill the 2 events whose events.csv in_fo is blank.

Rule (fixed, not tuned):
  k = events.i_react ; XN = (stock adj. return on k - Nifty 50 return on k) * 100 ; winner W = XN > 4
  RSI14 = Wilder RSI(14) on the stock's own traded-day adjusted closes (seed = simple mean of the first 14 gains / losses,
          then avg = (13*avg + x)/14), value at the cutoff close (session i_cut; as-of last traded close <= i_cut)
  RSI_HI = RSI14 > 50 ; signal = W & RSI_HI
  Trade: buy close k, sell close k+20, short Nifty for the same value.
  vsN_net = ((prod(1+r_{k+1..k+20}) - 1) - (N_{k+20}/N_k - 1)) * 100 - 0.19 (blank r = 0) ; raw_net = stock*100 - 0.17
  Tradable: return on k exists, session k+21 exists, <= 2 blank daily returns in k+1..k+21.
Outputs (this folder): universe.csv (every in_fo result with XN / RSI / outcome), trades.csv (the signal trades),
  per_quarter.csv, per_quarter.md, summary.txt
"""
import os

import numpy as np
import pandas as pd

SP = os.environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = SP + '/winners_rsi/rebuild'
H = 20
COST_HEDGED, COST_RAW = 0.19, 0.17

# ---------------------------------------------------------------- inputs
ev = pd.read_csv(SP + '/sector_lab/data/events.csv')
ses = pd.read_csv(SP + '/sector_lab/data/sessions.csv')
ret = pd.read_csv(SP + '/sector_lab/data/returns.csv', index_col=0)
idx = pd.read_csv(SP + '/sector_lab/data/index_close.csv', index_col=0)
ohl = pd.read_csv(SP + '/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'close'])
fa = pd.read_csv(SP + '/fa/build/fa_panel.csv', usecols=['symbol', 'qn', 'in_fo'])

assert (ses.i.values == np.arange(len(ses))).all()
assert list(ret.index) == list(ses.day) and list(idx.index) == list(ses.day), 'calendar mismatch'
NS = len(ses)                       # sessions 0..NS-1
day2i = dict(zip(ses.day, ses.i))
R = ret.values                      # [session, symbol] fraction, NaN = blank
col = {s: j for j, s in enumerate(ret.columns)}
N = idx['Nifty 50'].values
assert not np.isnan(N).any()

# ---------------------------------------------------------------- universe
ev = ev.merge(fa.rename(columns={'in_fo': 'in_fo_fa'}), on=['symbol', 'qn'], how='left')
in_fo_ev = ev['in_fo'].map({True: True, False: False, 'True': True, 'False': False})
ev['in_fo_filled'] = in_fo_ev.isna()
ev['in_fo_u'] = in_fo_ev.fillna(ev['in_fo_fa'].map({True: True, False: False, 'True': True, 'False': False}))
u = ev[ev['in_fo_u'] == True].copy().reset_index(drop=True)
print('in_fo universe', len(u), '(events.csv blank in_fo filled from fa_panel:',
      u.loc[u.in_fo_filled, ['symbol', 'qn']].values.tolist(), ')')

# ---------------------------------------------------------------- own Wilder RSI(14)
def wilder_rsi(close, n=14):
    c = np.asarray(close, float)
    out = np.full(len(c), np.nan)
    if len(c) <= n:
        return out
    d = np.diff(c)
    g = np.where(d > 0, d, 0.0)
    l = np.where(d < 0, -d, 0.0)
    ag, al = g[:n].mean(), l[:n].mean()          # seed on changes 1..14 -> RSI defined at row 14

    def rsi(a, b):
        if b == 0:
            return 100.0 if a > 0 else 50.0
        return 100.0 - 100.0 / (1.0 + a / b)
    out[n] = rsi(ag, al)
    for t in range(n, len(d)):                   # change d[t] is close[t+1]-close[t]
        ag = (ag * (n - 1) + g[t]) / n
        al = (al * (n - 1) + l[t]) / n
        out[t + 1] = rsi(ag, al)
    return out

ohl = ohl.sort_values(['symbol', 'day']).reset_index(drop=True)
ohl['i'] = ohl['day'].map(day2i)
assert ohl['i'].notna().all()
rsi_tab = {}   # symbol -> (traded session indices array, rsi array)
for s, g in ohl.groupby('symbol', sort=False):
    rsi_tab[s] = (g['i'].values.astype(int), wilder_rsi(g['close'].values))


def rsi_asof(sym, i):
    """RSI at the last traded close <= session i; also returns the session used and #traded rows up to it."""
    if sym not in rsi_tab:
        return np.nan, -1, 0
    ii, rr = rsi_tab[sym]
    p = np.searchsorted(ii, i, side='right') - 1
    if p < 0:
        return np.nan, -1, 0
    return rr[p], int(ii[p]), p + 1


# ---------------------------------------------------------------- per-result features + outcome
rows = []
for r in u.itertuples(index=False):
    k, sym = int(r.i_react), r.symbol
    j = col.get(sym)
    rec = dict(symbol=sym, company=r.company, qn=int(r.qn), quarter=r.quarter, period=r.period,
               results_date=r.results_date, timing=r.timing, i_cut=int(r.i_cut), i_react=k,
               reaction_day=ses.day[k], in_fo_filled=bool(r.in_fo_filled))
    rsi_c, i_used, nrows = rsi_asof(sym, int(r.i_cut))
    rec.update(rsi14_cut=rsi_c, rsi_session_used=i_used, rsi_traded_on_cut=(i_used == int(r.i_cut)), rsi_rows=nrows)
    rsi_k, ik_used, _ = rsi_asof(sym, k)
    rec.update(rsi14_react=rsi_k if ik_used == k else np.nan)
    rk = R[k, j] if j is not None else np.nan
    nret = N[k] / N[k - 1] - 1
    rec.update(stock_ret_k=rk * 100 if pd.notna(rk) else np.nan, nifty_ret_k=nret * 100)
    rec['XN'] = (rk - nret) * 100 if pd.notna(rk) else np.nan
    has_k21 = k + H + 1 <= NS - 1
    if j is not None and has_k21:
        w = R[k + 1:k + H + 2, j]                    # k+1..k+21
        nblank = int(np.isnan(w).sum())
        hold = np.nan_to_num(R[k + 1:k + H + 1, j], nan=0.0)   # k+1..k+20
        stock = np.prod(1 + hold) - 1
        nif = N[k + H] / N[k] - 1
    else:
        nblank, stock, nif = (np.nan, np.nan, np.nan)
    rec.update(has_k21=has_k21, blanks_k1_k21=nblank,
               tradable=bool(pd.notna(rk) and has_k21 and nblank <= 2))
    rec['raw_gross'] = stock * 100 if pd.notna(stock) else np.nan
    rec['nifty_H20'] = nif * 100 if pd.notna(nif) else np.nan
    rec['vsN_gross'] = (stock - nif) * 100 if pd.notna(stock) else np.nan
    rec['raw_net'] = rec['raw_gross'] - COST_RAW
    rec['vsN_net'] = rec['vsN_gross'] - COST_HEDGED
    rows.append(rec)

U = pd.DataFrame(rows)
U['W'] = U['XN'] > 4
U['RSI_HI'] = U['rsi14_cut'] > 50
U['W_RSI_HI'] = U['W'] & U['RSI_HI']
U['W_RSI_LE50'] = U['W'] & (U['rsi14_cut'] <= 50)
U.to_csv(OUT + '/universe.csv', index=False)

T = U[U.tradable & U.W_RSI_HI].sort_values(['qn', 'reaction_day', 'symbol']).reset_index(drop=True)
T['exit_day'] = [ses.day[k + H] for k in T.i_react]
cols = ['qn', 'period', 'quarter', 'symbol', 'company', 'results_date', 'timing', 'reaction_day', 'exit_day',
        'i_cut', 'i_react', 'stock_ret_k', 'nifty_ret_k', 'XN', 'rsi14_cut', 'rsi_traded_on_cut', 'rsi14_react',
        'blanks_k1_k21', 'raw_gross', 'nifty_H20', 'vsN_gross', 'raw_net', 'vsN_net']
T[cols].to_csv(OUT + '/trades.csv', index=False, float_format='%.6f')

# ---------------------------------------------------------------- per-quarter table (all 22 quarters)
qmeta = u.groupby('qn').agg(period=('period', 'first'), quarter=('quarter', 'first')).reset_index()
pq = []
for q in qmeta.itertuples(index=False):
    t = T[T.qn == q.qn]
    pw = U[(U.qn == q.qn) & U.tradable & U.W]
    pq.append(dict(qn=q.qn, results_for=q.period, quarter=q.quarter, trades=len(t),
                   avg_vsN_net=t.vsN_net.mean() if len(t) else np.nan,
                   avg_raw_net=t.raw_net.mean() if len(t) else np.nan,
                   up=int((t.vsN_net > 0).sum()),
                   plain_winners=len(pw), plain_winners_vsN_net=pw.vsN_net.mean() if len(pw) else np.nan,
                   stocks=', '.join(f'{s} ({v:+.1f})' for s, v in zip(t.symbol, t.vsN_net))))
PQ = pd.DataFrame(pq)
PQ.to_csv(OUT + '/per_quarter.csv', index=False, float_format='%.4f')

md = ['| # | Results for | Quarter | Trades | Avg vs Nifty net | Stocks (vs Nifty net, %) |',
      '|---|---|---|---:|---:|---|']
for p in PQ.itertuples(index=False):
    a = f'{p.avg_vsN_net:+.2f}' if pd.notna(p.avg_vsN_net) else '-'
    md.append(f'| {p.qn} | {p.results_for} | {p.quarter} | {p.trades} | {a} | {p.stocks} |')
md.append(f'| | **All** | **22 quarters** | **{len(T)}** | **{T.vsN_net.mean():+.2f}** | |')
open(OUT + '/per_quarter.md', 'w').write('\n'.join(md) + '\n')

# ---------------------------------------------------------------- summary
def summ(df, name):
    if not len(df):
        return f'{name}: n=0'
    qm = df.groupby('qn').vsN_net.mean()
    f14, l8 = df[df.qn <= 13], df[df.qn >= 14]
    wo5 = df.vsN_net.sort_values().iloc[:-5].mean() if len(df) > 5 else np.nan
    t_q = qm.mean() / (qm.std(ddof=1) / np.sqrt(len(qm))) if len(qm) > 1 else np.nan
    return (f'{name}: n={len(df)}  vsN_net={df.vsN_net.mean():+.3f}  raw_net={df.raw_net.mean():+.3f}  '
            f'vsN_gross={df.vsN_gross.mean():+.3f}  up%={100*(df.vsN_net>0).mean():.1f}  '
            f'quarters +/with trades={int((qm>0).sum())}/{len(qm)}  t_q={t_q:.2f}  '
            f'first14={f14.vsN_net.mean():+.3f} (n={len(f14)}, q+ {int((f14.groupby("qn").vsN_net.mean()>0).sum())}/'
            f'{f14.qn.nunique()})  last8={l8.vsN_net.mean():+.3f} (n={len(l8)}, q+ '
            f'{int((l8.groupby("qn").vsN_net.mean()>0).sum())}/{l8.qn.nunique()})  without best 5={wo5:+.3f}  '
            f'median={df.vsN_net.median():+.3f}')

tr = U[U.tradable]
lines = [
    f'in_fo results: {len(U)}  (events.csv in_fo True {int((~U.in_fo_filled).sum())} + {int(U.in_fo_filled.sum())} '
    f'blank filled from fa_panel)',
    f'reaction-day return blank: {int(U.XN.isna().sum())}; no session k+21: {int((~U.has_k21).sum())}; '
    f'>2 blanks k+1..k+21: {int(((U.blanks_k1_k21 > 2) & U.has_k21).sum())}; tradable: {len(tr)}',
    f'RSI at cutoff missing: {int(U.rsi14_cut.isna().sum())}; RSI taken from an earlier traded close (no trade on '
    f'cutoff): {int((U.rsi14_cut.notna() & ~U.rsi_traded_on_cut).sum())}',
    summ(tr[tr.W_RSI_HI], 'MAIN  winners & RSI>50'),
    summ(tr[tr.W], 'ref   plain winners XN>4'),
    summ(tr[tr.W_RSI_LE50], 'ref   winners & RSI<=50'),
    summ(tr[tr.W & tr.rsi14_cut.isna()], 'ref   winners, RSI missing'),
    summ(tr[~tr.W & (tr.rsi14_cut > 50)], 'diag  non-winners & RSI>50'),
    summ(tr[~tr.W & (tr.rsi14_cut <= 50)], 'diag  non-winners & RSI<=50'),
    summ(tr, 'diag  all tradable results'),
]
qpos = int((PQ.avg_vsN_net > 0).sum())
lines.append(f'quarters positive (main): {qpos}/22 (quarters with no trade: {int((PQ.trades == 0).sum())})')
open(OUT + '/summary.txt', 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
print(PQ[['qn', 'results_for', 'quarter', 'trades', 'avg_vsN_net', 'avg_raw_net', 'up', 'plain_winners',
          'plain_winners_vsN_net']].to_string(index=False, float_format=lambda x: f'{x:+.2f}'))
