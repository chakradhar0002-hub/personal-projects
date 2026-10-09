#!/usr/bin/env python3
"""Entry/exit design search for 'winners with cutoff RSI > 50' - DISCOVERY ONLY (qn 0..13).

Definitions are in candidates.txt (written before any outcome was computed).
Holdout qn >= 14 is sealed: rows are filtered to qn <= 13 BEFORE any price path is read.
For the holdout only an index-based count of data-end drops is computed (no returns touched).
Writes only into this folder.
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.environ.get('LAB_ROOT', os.path.abspath(os.path.join(HERE, '..', '..')))  # scratch data folder
DATA = f'{SP}/sector_lab/data'
COST_H, COST_R = 0.19, 0.17
LOG = open(f'{HERE}/run.log', 'w')
pd.set_option('display.width', 250, 'display.max_rows', 200, 'display.max_columns', 40)


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')
    LOG.flush()


# ------------------------------------------------------------------ signal set (features only)
fe = pd.read_csv(f'{SP}/tafa/C_post_results/features.csv')
S_all = fe[(fe.XN > 4) & (fe.cut_rsi14 > 50)].copy()
ses = pd.read_csv(f'{DATA}/sessions.csv')
NS = len(ses)
LAST = NS - 1
DAYS = ses.day.to_numpy()

# ---- holdout: index-only data-end drop counts (no returns read for these rows)
H_ = S_all[S_all.qn >= 14]
CAND_CAP = {}

# ---- discovery rows only from here on
S = S_all[S_all.qn <= 13].reset_index(drop=True)
assert len(S) == 122, len(S)
del S_all

# ------------------------------------------------------------------ prices
ret = pd.read_csv(f'{DATA}/returns.csv', index_col=0)
ixc = pd.read_csv(f'{DATA}/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])
intra = pd.read_csv(f'{DATA}/intraday.csv', index_col=0)
assert (ret.index == ses.day).all() and (ixc.index == ses.day).all() and (intra.index == ses.day).all()
assert list(intra.columns) == list(ret.columns)
SYM = {s: j for j, s in enumerate(ret.columns)}
R = ret.to_numpy(float)
PX = np.cumprod(1.0 + np.nan_to_num(R), axis=0)
BLANK = np.isnan(R)
NIF = ixc['Nifty 50'].to_numpy(float)
INTRA = intra.to_numpy(float)
o = pd.read_csv(f'{SP}/ta/build/adjusted_ohlcv.csv.gz', usecols=['day', 'symbol', 'low', 'close'])
lowr = (o.assign(r=o.low / o.close).pivot(index='day', columns='symbol', values='r')
        .reindex(index=ret.index, columns=ret.columns)).to_numpy(float)
LOWP = PX * lowr          # adjusted low on the PX scale (NaN where no OHLCV row)

# ------------------------------------------------------------------ candidates
# (id, entry, hcap, rule, min_hold)  rule: list of (kind, param)
CANDS = [
    ('R0', 'close', 20, [], 0),
    ('C01', 'close', 30, [], 0),
    ('C02', 'close', 40, [], 0),
    ('C03', 'close', 60, [], 0),
    ('C04', 'close', 60, [('DON', 10)], 0),
    ('C05', 'close', 60, [('SMA', 20)], 0),
    ('C06', 'close', 60, [('PEAK', 0.10)], 0),
    ('C07', 'close', 60, [('DON', 10)], 20),
    ('C08', 'close', 60, [('SMA', 20)], 20),
    ('C09', 'close', 60, [('PEAK', 0.10)], 20),
    ('C10', 'close', 20, [('SL', 0.08)], 0),
    ('C11', 'close', 20, [('SL', 0.10)], 0),
    ('C12', 'close', 60, [('SL', 0.08)], 0),
    ('C13', 'close', 60, [('SL', 0.10)], 0),
    ('C14', 'close', 40, [('SL', 0.10)], 0),
    ('C15', 'close', 20, [('TP', 0.10)], 0),
    ('C16', 'close', 20, [('TP', 0.15)], 0),
    ('C17', 'close', 60, [('TP', 0.10)], 0),
    ('C18', 'close', 60, [('TP', 0.15)], 0),
    ('C19', 'close', 60, [('SL', 0.08), ('TP', 0.15)], 0),
    ('C20', 'open', 20, [], 0),
    ('C21', 'open', 40, [], 0),
    ('C22', 'open', 60, [], 0),
    ('C23', 'pull', 20, [], 0),
    ('C24', 'pull', 40, [], 0),
    ('C25', 'pull', 60, [], 0),
    ('C26', 'pull', 60, [('SMA', 20)], 0),
    ('C27', 'pull', 60, [('SMA', 20)], 20),
]
DESC = {
    'R0': 'baseline: close k, hold 20', 'C01': 'close k, hold 30', 'C02': 'close k, hold 40',
    'C03': 'close k, hold 60', 'C04': 'close k, trail 10-day low, cap 60', 'C05': 'close k, trail SMA20, cap 60',
    'C06': 'close k, trail 10% off peak, cap 60', 'C07': 'close k, min 20 then 10-day-low trail, cap 60',
    'C08': 'close k, min 20 then SMA20 trail, cap 60', 'C09': 'close k, min 20 then 10%-off-peak trail, cap 60',
    'C10': 'close k, SL -8%, cap 20', 'C11': 'close k, SL -10%, cap 20', 'C12': 'close k, SL -8%, cap 60',
    'C13': 'close k, SL -10%, cap 60', 'C14': 'close k, SL -10%, cap 40', 'C15': 'close k, TP +10%, cap 20',
    'C16': 'close k, TP +15%, cap 20', 'C17': 'close k, TP +10%, cap 60', 'C18': 'close k, TP +15%, cap 60',
    'C19': 'close k, SL -8% + TP +15%, cap 60', 'C20': 'next open, exit close k+20',
    'C21': 'next open, exit close k+40', 'C22': 'next open, exit close k+60',
    'C23': 'pullback entry, hold 20', 'C24': 'pullback entry, hold 40', 'C25': 'pullback entry, hold 60',
    'C26': 'pullback entry, SMA20 trail, cap 60', 'C27': 'pullback entry, min 20 then SMA20 trail, cap 60',
}


def trigger(rule, j, t, e, entry):
    for kind, p in rule:
        if kind == 'DON':
            lo = LOWP[t - p:t, j]
            lo = lo[~np.isnan(lo)]
            if len(lo) and PX[t, j] < lo.min():
                return True
        elif kind == 'SMA':
            if PX[t, j] < PX[t - p + 1:t + 1, j].mean():
                return True
        elif kind == 'PEAK':
            if PX[t, j] <= (1 - p) * PX[e:t + 1, j].max():
                return True
        elif kind == 'SL':
            if PX[t, j] / entry - 1 <= -p:
                return True
        elif kind == 'TP':
            if PX[t, j] / entry - 1 >= p:
                return True
    return False


def run(cid, entry_kind, hcap, rule, minh, delay=0):
    """delay=1 -> condition exits executed at close t+1 (robustness (a))."""
    rows = []
    W = max(21, hcap + 1)
    for r in S.itertuples():
        j = SYM[r.symbol]
        k = int(r.i_react)
        assert r.qn <= 13
        if entry_kind == 'close':
            e, entry, nref = k, PX[k, j], NIF[k]
        elif entry_kind == 'open':
            e, entry, nref = k, PX[k + 1, j] / (1 + INTRA[k + 1, j]), NIF[k]
            if not np.isfinite(entry):
                rows.append(dict(symbol=r.symbol, qn=r.qn, ok=False, why='no_open'))
                continue
        else:
            e = None
            for t in range(k + 1, k + 6):
                if np.isfinite(R[t, j]) and R[t, j] < 0:
                    e = t
                    break
            if e is None:
                rows.append(dict(symbol=r.symbol, qn=r.qn, ok=False, why='no_pullback'))
                continue
            entry, nref = PX[e, j], NIF[e]
        if e + W > LAST:
            rows.append(dict(symbol=r.symbol, qn=r.qn, ok=False, why='data_end'))
            continue
        if BLANK[e + 1:e + W + 1, j].sum() > 2:
            rows.append(dict(symbol=r.symbol, qn=r.qn, ok=False, why='blanks'))
            continue
        x, why = e + hcap, 'cap'
        for t in range(e + 1, e + hcap + 1):
            if t - e < minh:
                continue
            if rule and trigger(rule, j, t, e, entry):
                x, why = min(t + delay, e + hcap), 'rule'
                break
        stock = PX[x, j] / entry - 1
        nif = NIF[x] / nref - 1
        rows.append(dict(symbol=r.symbol, qn=r.qn, reaction_day=r.reaction_day, ok=True, why=why,
                         entry_day=DAYS[e], exit_day=DAYS[x], held=x - e if entry_kind != 'open' else x - k,
                         stock_pct=stock * 100, nifty_pct=nif * 100,
                         vsN_net=(stock - nif) * 100 - COST_H, raw_net=stock * 100 - COST_R))
    return pd.DataFrame(rows)


def summ(cid, T):
    t = T[T.ok].copy()
    v = t.vsN_net.sort_values(ascending=False)
    q = t.groupby('qn').vsN_net.mean()
    yr = t.reaction_day.str[:4]
    return dict(id=cid, desc=DESC.get(cid, cid), n=len(t), skipped=int((~T.ok).sum()),
                avg=t.vsN_net.mean(), wo_best5=v.iloc[5:].mean(), median=t.vsN_net.median(),
                win=(t.vsN_net > 0).mean() * 100, raw_avg=t.raw_net.mean(),
                q_pos=int((q > 0).sum()), q_with=int(len(q)), held=t.held.mean(),
                per20=t.vsN_net.sum() / t.held.sum() * 20, rule_exits=int((t.why == 'rule').sum()),
                avg_ex2023=t.loc[yr != '2023', 'vsN_net'].mean(), n_ex2023=int((yr != '2023').sum()),
                share2023=t.loc[yr == '2023', 'vsN_net'].sum() / t.vsN_net.sum() * 100)


ALL, TR = [], []
for cid, ek, hc, rule, mh in CANDS:
    T = run(cid, ek, hc, rule, mh)
    T.insert(0, 'cand', cid)
    TR.append(T)
    ALL.append(summ(cid, T))
res = pd.DataFrame(ALL)
pd.concat(TR).to_csv(f'{HERE}/discovery_trades.csv', index=False)
P('DISCOVERY qn 0..13 only. vsN_net percent per trade.')
P(res.round(2).to_string(index=False))
res.to_csv(f'{HERE}/discovery_results.csv', index=False)

base = res.set_index('id').loc['R0']
bar = base.wo_best5 + 0.5
P(f"\nR0 check: n={base.n} avg={base.avg:.2f} (expected 122, +2.65); R0 w/o best 5 = {base.wo_best5:.3f}; "
  f"finalist bar = {bar:.3f}")

el = res[(res.id != 'R0') & (res.n >= 35) & (res.q_with >= 7)].sort_values('wo_best5', ascending=False)
P('\nRANKED by discovery avg w/o best 5 (eligible: n>=35, >=7 quarters with trades):')
P(el[['id', 'desc', 'n', 'avg', 'wo_best5', 'q_pos', 'q_with', 'held', 'per20']].round(2).to_string(index=False))
fin = el[el.wo_best5 >= bar].head(2)
P('\nFINALISTS:', list(fin.id) if len(fin) else 'NONE')

# per quarter table (discovery)
pq = (pd.concat(TR).query('ok').groupby(['cand', 'qn']).vsN_net.agg(['size', 'mean']).round(2)
      .unstack('cand'))
pq.to_csv(f'{HERE}/discovery_per_quarter.csv')

# ------------------------------------------------------------------ holdout index-only data-end counts
hc_rows = []
for cid, ek, hc, rule, mh in CANDS:
    W = max(21, hc + 1)
    if ek in ('close', 'open'):
        lo = hi = int((H_.i_react + W > LAST).sum())
    else:
        lo = int((H_.i_react + 1 + W > LAST).sum())
        hi = int((H_.i_react + 5 + W > LAST).sum())
    hc_rows.append(dict(id=cid, holdout_signals=len(H_), dropped_data_end_min=lo, dropped_data_end_max=hi))
hcd = pd.DataFrame(hc_rows)
hcd.to_csv(f'{HERE}/holdout_dataend_drops.csv', index=False)
P('\nHOLDOUT (indices only, no outcomes): trades dropped because the window runs past 2026-09-30')
P(hcd.to_string(index=False))

# ------------------------------------------------------------------ robustness for finalists (discovery)
for cid in fin.id:
    ek, hc, rule, mh = [c[1:] for c in CANDS if c[0] == cid][0]
    T = run(cid, ek, hc, rule, mh, delay=1)
    s = summ(cid + '_exit_t+1', T)
    P(f"\nROBUSTNESS {cid} (a) exits at close t+1: n={s['n']} avg={s['avg']:.2f} wo5={s['wo_best5']:.2f} "
      f"q+={s['q_pos']}/{s['q_with']}")
    r_ = res.set_index('id').loc[cid]
    P(f"  (c) ex-2023 avg {r_.avg_ex2023:.2f} (n={r_.n_ex2023}) vs R0 ex-2023 {base.avg_ex2023:.2f}; "
      f"2023 share of profit {r_.share2023:.0f}% (R0 {base.share2023:.0f}%)")
    P(f"  (d) median {r_['median']:.2f} win {r_.win:.0f}%  (R0 median {base['median']:.2f} win {base.win:.0f}%)")
    P(f"  (e) per 20 sessions {r_.per20:.2f} vs R0 {base.per20:.2f}; held {r_.held:.1f}")
    P('  (b) per quarter (size, mean):')
    P(pq.loc[:, (slice(None), [cid, 'R0'])].to_string())
