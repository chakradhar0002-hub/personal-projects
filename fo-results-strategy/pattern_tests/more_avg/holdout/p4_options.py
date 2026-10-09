#!/usr/bin/env python3
"""Holdout evaluator - step 4: option finalists F7 (ATM call) and F8 (5% OTM call) on WR50 signals, all quarters.
Rules re-implemented from the finalist definitions (see eval_plan.txt). Reads my own bhav.db (p3_fetch_bhav.py).
usage: p4_options.py plan   -> writes exit_days_needed.csv (expiry sessions not yet fetched)
       p4_options.py run    -> writes opt_trades.csv
"""
import csv
import sqlite3
import sys
from datetime import datetime
import numpy as np
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f'{SP}/more_avg/holdout'
ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv')
DAYS = ses.day.to_numpy()
LAST = len(ses) - 1
P = pd.read_csv(f'{OUT}/panel.csv')
S = P[(P.XN > 4) & (P.rsi_cut > 50)].reset_index(drop=True)
assert len(S) == 232
db = sqlite3.connect(f'{OUT}/bhav.db')
odb = sqlite3.connect(f'{SP}/report/options.db')
done = dict(db.execute('SELECT day, fmt FROM done WHERE ok=1').fetchall())

# ticker valid on a day
chg = {}
for r in csv.reader(open(f'{SP}/symbolchange.csv', encoding='latin-1')):
    if len(r) >= 4:
        chg.setdefault(r[2].strip(), []).append((r[1].strip(), datetime.strptime(r[3].strip(), '%d-%b-%Y').date().isoformat()))


def tick(s, d):
    for old, dt in chg.get(s, []):
        if dt > d:
            return tick(old, d)
    return s


# raw (unadjusted) close as a spot fallback for old-format days
oh = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'raw_close'])
RAWC = {(s, d): c for s, d, c in zip(oh.symbol, oh.day, oh.raw_close)}


def exp_session(e):
    """last session index with day <= expiry date e"""
    return int(np.searchsorted(DAYS, e, side='right') - 1)


def rows(sym, d):
    t = pd.read_sql_query('SELECT * FROM row WHERE symbol=? AND day=?', db, params=(sym, d))
    return t


def nearest(c, target):
    c = c.assign(dist=(c.strike - target).abs()).sort_values(['dist', 'strike'])
    return c.iloc[0]


def entry(s, k, mult):
    d = DAYS[k]
    if d not in done:
        return None, 'entry_day_not_fetched'
    tk = tick(s, d)
    t = rows(tk, d)
    if len(t) == 0:
        return None, 'no_rows_on_k'
    fmt = done[d]
    if fmt == 'udiff':
        und = t.und[t.und > 0]
        spot = float(und.iloc[0]) if len(und) else np.nan
        src = 'udiff'
    else:
        r = odb.execute('SELECT spot FROM spot WHERE day=? AND symbol IN (?,?)', (d, s, tk)).fetchone()
        if r:
            spot, src = float(r[0]), 'options.db'
        else:
            spot, src = float(RAWC.get((s, d), np.nan)), 'raw_close'
    if not np.isfinite(spot):
        return None, 'no_spot'
    ce = t[(t.tp == 'STO') & (t.kind == 'CE')].copy()
    ce['es'] = ce.expiry.map(exp_session)
    ok_exp = sorted(e for e in ce.expiry.unique() if exp_session(e) >= k + 15)
    if not ok_exp:
        return None, 'no_expiry'
    E = ok_exp[0]
    c = ce[ce.expiry == E]
    target = mult * spot
    pick = nearest(c, target)
    fallback = False
    if not (pick.volume > 0 and pick.close > 0):
        cc = c[(c.volume > 0) & (c.close > 0) & ((c.strike / target - 1).abs() <= 0.025)]
        if len(cc) == 0:
            return None, 'no_liquid_strike'
        pick = nearest(cc, target)
        fallback = True
    return dict(tick=tk, spot=spot, spot_src=src, expiry=E, es=exp_session(E), K=float(pick.strike),
                P=float(pick.close), fallback=fallback, raw_spot=float(RAWC.get((s, d), np.nan))), 'ok'


def contract_on(s, i, E, K):
    d = DAYS[i]
    if d not in done:
        return None, None
    tk = tick(s, d)
    t = rows(tk, d)
    eday = DAYS[exp_session(E)]
    m = (t.tp == 'STO') & (t.kind == 'CE') & (np.isclose(t.strike, K)) & (t.expiry.isin([E, eday]) | t.act_expiry.isin([E, eday]))
    f = (t.tp == 'STF') & (t.expiry.isin([E, eday]) | t.act_expiry.isin([E, eday]))
    return (t[m].iloc[0] if m.any() else None), (t[f].iloc[0] if f.any() else None)


def trade(s, k, mult):
    en, why = entry(s, k, mult)
    if en is None:
        return dict(status=why)
    x = min(k + 20, en['es'])
    o = dict(status='ok', **en, x=x, x_day=DAYS[x], x_is_expiry=(x == en['es']))
    if DAYS[x] not in done:
        o['status'] = 'exit_day_not_fetched'
        return o
    opt, fut = contract_on(s, x, en['expiry'], en['K'])
    if x == en['es']:
        if fut is not None and fut.settle > 0:
            U, usrc = float(fut.settle), 'fut_settle'
        elif opt is not None and opt.settle > 0:
            U, usrc = float(opt.settle), 'opt_settle'
        else:
            o['status'] = 'exit_missing'
            return o
        o.update(X=max(U - en['K'], 0.0), x_src=usrc, U=U)
        if opt is not None and fut is not None and opt.settle > 0:
            o['settle_eq_U'] = bool(abs(opt.settle - fut.settle) < 0.011)
    else:
        if opt is None:
            o['status'] = 'exit_missing'
            return o
        if opt.volume > 0 and opt.close > 0:
            o.update(X=float(opt.close), x_src='close')
        else:
            o.update(X=float(opt.settle), x_src='settle')
    o['net'] = (o['X'] / en['P'] - 1) * 100 - 1.0 - 0.05 * en['spot'] / en['P']
    # realistic: buy the same contract at the OPEN of k+1, doubled costs
    o['real_status'] = 'ok'
    if k + 1 > LAST or DAYS[k + 1] not in done:
        o['real_status'] = 'k1_not_fetched'
    else:
        op1, f1 = contract_on(s, k + 1, en['expiry'], en['K'])
        if op1 is None or not (op1.volume > 0 and op1.open > 0):
            o['real_status'] = 'no_open_k1'
        else:
            o['P_open1'] = float(op1.open)
            o['net_real'] = (o['X'] / o['P_open1'] - 1) * 100 - 2.0 - 0.10 * en['spot'] / o['P_open1']
    return o


if __name__ == '__main__':
    mode = sys.argv[1]
    res = []
    for _, r in S.iterrows():
        for name, mult in (('ATM', 1.0), ('OTM5', 1.05)):
            o = trade(r.symbol, int(r.i_react), mult)
            o.update(symbol=r.symbol, qn=int(r.qn), quarter=r.quarter, k=int(r.i_react), reaction_day=r.reaction_day,
                     variant=name)
            res.append(o)
    T = pd.DataFrame(res)
    if mode == 'plan':
        need = sorted(set(T.loc[T.status == 'exit_day_not_fetched', 'x'].astype(int)))
        pd.DataFrame({'i': need, 'day': [DAYS[i] for i in need]}).to_csv(f'{OUT}/exit_days_needed.csv', index=False)
        print('exit days to fetch', len(need))
        print(T.status.value_counts().to_dict())
    else:
        T.to_csv(f'{OUT}/opt_trades.csv', index=False, float_format='%.6f')
        print(T.groupby('variant').status.value_counts())
        print(T.groupby('variant').real_status.value_counts())
        print('fallback strikes', T.groupby('variant').fallback.sum().to_dict())
        print('exit source', T.groupby(['variant', 'x_src']).size().to_dict())
        print('settle==U on expiry exits', T.settle_eq_U.value_counts().to_dict() if 'settle_eq_U' in T else None)
        print('spot sources', T.groupby('spot_src').size().to_dict())
        sp = T.dropna(subset=['raw_spot'])
        print('spot vs raw close: max abs rel diff %', float((sp.spot / sp.raw_spot - 1).abs().max() * 100),
              ' n>0.5%:', int(((sp.spot / sp.raw_spot - 1).abs() > 0.005).sum()))
