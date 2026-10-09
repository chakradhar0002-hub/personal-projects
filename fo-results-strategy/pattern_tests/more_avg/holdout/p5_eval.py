#!/usr/bin/env python3
"""Holdout evaluator - step 5: evaluate the 8 finalists (plan: eval_plan.txt). Reads panel.csv, nifty_open.csv,
opt_trades.csv (all written by my own scripts p1..p4). Writes eval.log, finalist_table.csv/.md, per_quarter_all.csv,
per_quarter.md, trades_<finalist>.csv."""
import numpy as np
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f'{SP}/more_avg/holdout'
D = f'{SP}/sector_lab/data'
ND = 20000
rng = np.random.default_rng(20261009)
LOG = open(f'{OUT}/eval.log', 'w')


def say(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    LOG.write(s + '\n')


def f2(x, d=2):
    return 'n/a' if x is None or not np.isfinite(x) else f'{x:+.{d}f}'


ses = pd.read_csv(f'{D}/sessions.csv')
LAST = len(ses) - 1
ret = pd.read_csv(f'{D}/returns.csv', index_col=0)
R = ret.to_numpy(float)
SYM = {s: j for j, s in enumerate(ret.columns)}
PX = np.cumprod(1 + np.nan_to_num(R), axis=0)
N = pd.read_csv(f'{D}/index_close.csv', index_col=0, usecols=['day', 'Nifty 50'])['Nifty 50'].to_numpy(float)
NO = np.full(len(ses), np.nan)
no = pd.read_csv(f'{OUT}/nifty_open.csv')
NO[no.i.to_numpy(int)] = no.open.to_numpy(float)

P = pd.read_csv(f'{OUT}/panel.csv')
k = P.i_react.to_numpy(int)
jx = P.symbol.map(SYM).to_numpy(int)

# ------------------------------------------------------------------ outcomes (percent)
P['vsN20'] = P.stk_H20 - P.nif_H20 - 0.19
P['raw20'] = P.stk_H20 - 0.17
P['vsN60'] = P.stk_H60 - P.nif_H60 - 0.19
P['raw60'] = P.stk_H60 - 0.17
P['vsNPB'] = P.stk_PB60 - P.nif_PB60 - 0.19
P['rawPB'] = P.stk_PB60 - 0.17


def open_entry(j, i_open, i_exit, oc):
    """buy at the open of session i_open, exit close i_exit; stock = (C/O on i_open) * PX[i_exit]/PX[i_open]"""
    s = oc * PX[i_exit, j] / PX[i_open, j] - 1
    n = N[i_exit] / NO[i_open] - 1
    return s * 100, n * 100


def realistic(H, ok_col, start, oc_col):
    vs, rw = np.full(len(P), np.nan), np.full(len(P), np.nan)
    for r, (j, st, ok, oc) in enumerate(zip(jx, start, P[ok_col], P[oc_col])):
        if ok != 'ok' or not np.isfinite(st):
            continue
        st = int(st)
        if st + 1 + (H - 1) > LAST or not np.isfinite(NO[st + 1]):
            continue
        s, n = open_entry(j, st + 1, st + H, oc)
        vs[r] = s - n - 0.42
        rw[r] = s - 0.40
    return vs, rw


P['real20'], P['rawreal20'] = realistic(20, 'ok_H20', k, 'oc_k1')
P['real60'], P['rawreal60'] = realistic(60, 'ok_H60', k, 'oc_k1')
P['realPB'], P['rawrealPB'] = realistic(60, 'ok_PB60', P.pb_e.to_numpy(float), 'oc_e1')

# ------------------------------------------------------------------ selections
P['W'] = P.XN > 4
P['BASE'] = P.W & (P.rsi_cut > 50)
assert P.BASE.sum() == 232 and P.W.sum() == 392
disc_base = P[P.BASE & (P.qn <= 13)]
vix_cut = float(np.quantile(disc_base.vix_k, 1 / 3))
say(f'VIX cut recomputed as np.quantile(VIX(k) of the 122 discovery baseline signals, 1/3) = {vix_cut:.6f} '
    f'(finalist states 13.346667)')
P['F1'] = (P.XN > 5) & (P.rsi_cut > 50)
P['F2'] = P.BASE & (P.brk20 == 1) & (P.volr50 >= 1.5)
P['F5'] = P.BASE & (P.vix_k <= 13.346667)

# F6: walk-forward hand rank-sum
P['F6'] = False
P['F6_score'] = np.nan
P['F6_thr'] = np.nan
for q in range(4, 22):
    pool = P[P.W & (P.qn < q)]
    a, b = np.sort(pool.rsi_cut.to_numpy()), np.sort(pool.XN.to_numpy())
    n = len(pool)

    def score(x_rsi, x_xn):
        return np.searchsorted(a, x_rsi, side='right') / n + np.searchsorted(b, x_xn, side='right') / n
    ps = score(pool.rsi_cut.to_numpy(), pool.XN.to_numpy())
    f = min(1.0, 5 * pool.qn.nunique() / n)
    assert pool.qn.nunique() == q
    thr = np.quantile(ps, 1 - f)
    cur = P.W & (P.qn == q)
    sc = score(P.loc[cur, 'rsi_cut'].to_numpy(), P.loc[cur, 'XN'].to_numpy())
    P.loc[cur, 'F6_score'] = sc
    P.loc[cur, 'F6_thr'] = thr
    P.loc[cur, 'F6'] = sc >= thr
P['F6'] = P.F6.astype(bool)
P['F3'] = P.BASE
P['F4'] = P.BASE

# options
OT = pd.read_csv(f'{OUT}/opt_trades.csv')
for v, F in (('ATM', 'F7'), ('OTM5', 'F8')):
    t = OT[(OT.variant == v)][['symbol', 'qn', 'status', 'net', 'net_real', 'real_status', 'fallback', 'x_src']]
    t = t.rename(columns={c: f'{F}_{c}' for c in t.columns if c not in ('symbol', 'qn')})
    P = P.merge(t, on=['symbol', 'qn'], how='left', validate='1:1')
    P[F] = P.BASE & (P[f'{F}_status'] == 'ok')

FIN = {
    'F1': dict(name='C05_XN5 (XN > 5, RSI > 50, H20)', col='vsN20', raw='raw20', real='real20', rawreal='rawreal20',
               test='rand', disc=(89, 4.125, 2.761)),
    'F2': dict(name='C27_BRK20_VOL1.5 (20-day high breakout on volume, H20)', col='vsN20', raw='raw20', real='real20',
               rawreal='rawreal20', test='rand', disc=(100, 3.86, 2.54)),
    'F3': dict(name='C03 hold 60 sessions (exit design)', col='vsN60', raw='raw60', real='real60', rawreal='rawreal60',
               test='paired', disc=(122, 4.64, 2.70)),
    'F4': dict(name='C25 pullback entry + hold 60 (exit design)', col='vsNPB', raw='rawPB', real='realPB',
               rawreal='rawrealPB', test='paired', disc=(119, 4.25, 2.32)),
    'F5': dict(name='C10 low India VIX <= 13.35 (context)', col='vsN20', raw='raw20', real='real20', rawreal='rawreal20',
               test='rand', disc=(41, 6.91, 4.11)),
    'F6': dict(name='C11 HAND_T5 walk-forward rank-sum (ranking)', col='vsN20', raw='raw20', real='real20',
               rawreal='rawreal20', test='rand', disc=(53, 5.56, 3.61)),
    'F7': dict(name='C10 OPT ATM call (return on premium, unhedged)', col='F7_net', raw='F7_net', real='F7_net_real',
               rawreal=None, test='paired', disc=(118, 49.54, 21.6)),
    'F8': dict(name='C11 OPT 5% OTM call (return on premium, unhedged)', col='F8_net', raw='F8_net', real='F8_net_real',
               rawreal=None, test='paired', disc=(115, 70.45, 15.94)),
}
HQ = list(range(14, 22))


def sel(F, sample):
    m = P[F] & P[FIN[F]['col']].notna()
    if sample == 'disc':
        m &= P.qn <= 13
    elif sample == 'hold':
        m &= P.qn >= 14
    return P[m]


def st(v, q=None):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    o = dict(n=len(v), avg=v.mean() if len(v) else np.nan, med=np.median(v) if len(v) else np.nan,
             wo5=np.sort(v)[:-5].mean() if len(v) > 5 else np.nan, win=(v > 0).mean() * 100 if len(v) else np.nan)
    return o


def qstats(df, col):
    g = df.groupby('qn')[col].mean()
    return int((g > 0).sum()), int(len(g))


def randpick_p(fin, col, pool_mask):
    obs = fin[col].mean()
    tot = np.zeros(ND)
    m_all = 0
    capped = 0
    for q in HQ:
        nq = int((fin.qn == q).sum())
        if nq == 0:
            continue
        v = P.loc[pool_mask & (P.qn == q) & P[col].notna(), col].to_numpy(float)
        m = min(nq, len(v))
        capped += nq - m
        idx = rng.random((ND, len(v))).argsort(axis=1)[:, :m]
        tot += v[idx].sum(axis=1)
        m_all += m
    means = tot / m_all
    return (1 + (means >= obs - 1e-12).sum()) / (ND + 1), means.mean(), capped


def signflip_p(d, q):
    d = np.asarray(d, float)
    obs = d.mean()
    fl = rng.choice([-1.0, 1.0], size=(ND, len(d)))
    p_trade = (1 + ((fl * d).mean(axis=1) >= obs - 1e-12).sum()) / (ND + 1)
    s = pd.Series(d).groupby(np.asarray(q)).sum().to_numpy()
    flq = rng.choice([-1.0, 1.0], size=(ND, len(s)))
    p_q = (1 + ((flq * s).sum(axis=1) / len(d) >= obs - 1e-12).sum()) / (ND + 1)
    return p_trade, p_q


# ------------------------------------------------------------------ baseline / plain winners references
say('\n=== REFERENCES (vsN_net, H20, close-of-k entry) ===')
for nm, m in (('BASELINE', P.BASE), ('PLAIN WINNERS', P.W)):
    for smp, mm in (('disc 0-13', P.qn <= 13), ('hold 14-21', P.qn >= 14), ('full 0-21', P.qn >= 0)):
        x = P[m & mm]
        s = st(x.vsN20)
        qp, qt = qstats(x, 'vsN20')
        sr = st(x.real20)
        say(f'{nm:14s} {smp:10s} n {s["n"]:4d} avg {f2(s["avg"])} med {f2(s["med"])} wo5 {f2(s["wo5"])} q+ {qp}/{qt} '
            f'raw {f2(x.raw20.mean())} | next-open 0.40: n {sr["n"]} avg {f2(sr["avg"])}')
BH = P[P.BASE & (P.qn >= 14)]
WH = P[P.W & (P.qn >= 14)]
bh_s = st(BH.vsN20)

# ------------------------------------------------------------------ finalists
rows = []
say('\n=== FINALISTS ===')
for F, c in FIN.items():
    col = c['col']
    di, ho, fu = sel(F, 'disc'), sel(F, 'hold'), sel(F, 'full')
    sd, sh, sf = st(di[col]), st(ho[col]), st(fu[col])
    qp, qt = qstats(ho, col)
    dn, da, dw = c['disc']
    mism = []
    if abs(sd['n'] - dn) > 1:
        mism.append(f'n {sd["n"]} vs {dn}')
    if abs(sd['avg'] - da) > 0.05:
        mism.append(f'avg {sd["avg"]:.3f} vs {da}')
    if abs(sd['wo5'] - dw) > 0.05:
        mism.append(f'wo5 {sd["wo5"]:.3f} vs {dw} (info)')
    # comparator (a)
    if c['test'] == 'rand':
        cmpa = P[P.BASE & P.qn.isin(sorted(ho.qn.unique()))]
        p, rmean, capped = randpick_p(ho, col, P.BASE)
        p_q = np.nan
        ptxt = f'random same-size-per-quarter from baseline pool: p {p:.4f} (mean of draws {rmean:+.2f}, capped {capped})'
        if F == 'F6':
            p_w, rmean_w, cap_w = randpick_p(ho, col, P.W)
            ptxt += f'; plain-winners pool p {p_w:.4f} (draw mean {rmean_w:+.2f})'
    else:
        cmpa = P[P.index.isin(ho.index)]          # same signals, baseline outcome
        d = ho[col].to_numpy() - ho['vsN20'].to_numpy()
        p, p_q = signflip_p(d, ho.qn)
        ptxt = f'paired sign-flip vs baseline on same {len(d)} signals: mean diff {d.mean():+.2f}, p {p:.4f}; quarter-clustered p {p_q:.4f}'
    sa = st(cmpa.vsN20)
    sre = st(ho[c['real']]) if c['real'] in ho else dict(n=0, avg=np.nan)
    ho_real = P[P[F] & (P.qn >= 14) & P[c['real']].notna()]
    sre = st(ho_real[c['real']])
    base_real_same = st(P.loc[P.BASE & P.qn.isin(sorted(ho.qn.unique())), 'real20'])
    raw_h = ho[c['raw']].mean()
    rows.append(dict(F=F, name=c['name'], disc_n=sd['n'], disc_avg=sd['avg'], disc_wo5=sd['wo5'],
                     search_disc_n=dn, search_disc_avg=da, mismatch='; '.join(mism) or 'none',
                     hold_n=sh['n'], hold_avg=sh['avg'], hold_med=sh['med'], hold_wo5=sh['wo5'], hold_win=sh['win'],
                     hold_qpos=qp, hold_qtr=qt, hold_raw=raw_h,
                     cmpA_n=sa['n'], cmpA_avg=sa['avg'], cmpA_wo5=sa['wo5'],
                     base_hold_avg=bh_s['avg'], base_hold_wo5=bh_s['wo5'], winners_hold_avg=st(WH.vsN20)['avg'],
                     p_raw=p, p_q=p_q, real_n=sre['n'], real_avg=sre['avg'], base_real_sameq=base_real_same['avg'],
                     full_n=sf['n'], full_avg=sf['avg'], full_wo5=sf['wo5'], test=ptxt))
    say(f'\n{F} {c["name"]}')
    say(f'  discovery: n {sd["n"]} avg {f2(sd["avg"])} wo5 {f2(sd["wo5"])}   [search: {dn} / {da} / {dw}]  mismatch: {"; ".join(mism) or "none"}')
    say(f'  holdout:   n {sh["n"]} avg {f2(sh["avg"])} med {f2(sh["med"])} wo5 {f2(sh["wo5"])} win {sh["win"]:.0f}% '
        f'q+ {qp}/{qt} unhedged/raw {f2(raw_h)}')
    say(f'  comparator (a) baseline: n {sa["n"]} avg {f2(sa["avg"])} wo5 {f2(sa["wo5"])};  baseline all holdout '
        f'n {bh_s["n"]} avg {f2(bh_s["avg"])} wo5 {f2(bh_s["wo5"])}; plain winners holdout {f2(st(WH.vsN20)["avg"])}')
    say(f'  test: {ptxt}')
    say(f'  realistic (next open, 0.40+0.02): n {sre["n"]} avg {f2(sre["avg"])} (baseline realistic same quarters '
        f'{f2(base_real_same["avg"])})')
    say(f'  full sample (in-sample): n {sf["n"]} avg {f2(sf["avg"])} wo5 {f2(sf["wo5"])}')
    ho.to_csv(f'{OUT}/trades_{F}_holdout.csv', index=False, float_format='%.4f')
    fu.to_csv(f'{OUT}/trades_{F}_all.csv', index=False, float_format='%.4f')

T = pd.DataFrame(rows)
# Holm
order = np.argsort(T.p_raw.to_numpy())
m = len(T)
adj = np.empty(m)
run = 0
for rank, i in enumerate(order):
    run = max(run, min(1.0, (m - rank) * T.p_raw.iloc[i]))
    adj[i] = run
T['p_holm'] = adj
T['margin_A'] = T.hold_avg - T.cmpA_avg
T['margin_base_all'] = T.hold_avg - T.base_hold_avg
T['survivor'] = (T.margin_A >= 0.5) & (T.p_holm < 0.10) & (T.hold_n >= 20) & (T.hold_wo5 > T.cmpA_wo5)
T.to_csv(f'{OUT}/finalist_table.csv', index=False, float_format='%.4f')
say('\n=== SUMMARY ===')
say(T[['F', 'hold_n', 'hold_avg', 'hold_wo5', 'cmpA_avg', 'cmpA_wo5', 'margin_A', 'p_raw', 'p_holm', 'survivor']]
    .to_string(float_format=lambda x: f'{x:.3f}'))

# ------------------------------------------------------------------ per quarter (all 22)
pq = pd.DataFrame({'qn': range(22)})
pq['quarter'] = pq.qn.map(P.groupby('qn').quarter.first())
for nm, mask, col in [('BASE', P.BASE, 'vsN20'), ('WIN', P.W, 'vsN20')] + [(F, P[F], FIN[F]['col']) for F in FIN]:
    g = P[mask & P[col].notna()].groupby('qn')[col].agg(['size', 'mean'])
    pq[f'{nm}_n'] = pq.qn.map(g['size']).fillna(0).astype(int)
    pq[f'{nm}_avg'] = pq.qn.map(g['mean'])
pq.to_csv(f'{OUT}/per_quarter_all.csv', index=False, float_format='%.3f')
P.to_csv(f'{OUT}/panel_eval.csv', index=False, float_format='%.5f')
