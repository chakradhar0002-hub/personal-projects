"""Evaluate the pre-registered setups (setups.py) exactly once, plus selection / walk-forward / shuffles / placebo.
Run: python3 build_features.py && python3 evaluate.py
Outputs (this folder): setup_results.csv, selection_results.json, shuffle_selection.csv, l01_stability.csv,
per_quarter_top.csv, setup_trades_top.csv"""
import numpy as np, pandas as pd, json, os
from setups import SETUPS, OUTCOMES, MIN_TRADES_LIST, N_SHUFFLE, N_SHUFFLE_SETUP, COST, SEED
HERE = os.path.dirname(os.path.abspath(__file__))
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40); pd.set_option('display.max_rows', 200)

F = pd.read_csv(os.path.join(HERE, 'events_feat.csv'))
O = pd.read_csv(os.path.join(HERE, 'events_outcomes.csv'))
assert (F.symbol.values == O.symbol.values).all() and (F.quarter.values == O.quarter.values).all()
PL = pd.read_csv(os.path.join(HERE, 'placebo.csv.gz'))
PL = PL[PL.in_fo == True].reset_index(drop=True)
NQ = 22; IS = np.arange(NQ) < 14

OPS = {'<': np.less, '<=': np.less_equal, '>': np.greater, '>=': np.greater_equal, '==': np.equal}
def mask(df, conds, allow_missing_cols=False):
    m = np.ones(len(df), bool); dropped = []
    for c, op, th in conds:
        if c not in df.columns:
            if allow_missing_cols: dropped.append(c); continue
            raise KeyError(c)
        v = df[c].values.astype(float)
        m &= ~np.isnan(v) & OPS[op](np.nan_to_num(v, nan=0.0), th)
    return m, dropped

def pnl_of(df, direction, outcome):
    if outcome == '3day': return direction * df.three_day.values
    return df.tp3.values if direction > 0 else df.tp3s.values

def stats(p, qn):
    p = np.asarray(p, float); qn = np.asarray(qn)
    n = len(p)
    if n == 0: return dict(n=0)
    qm = pd.Series(p).groupby(qn).mean()
    s = np.sort(p)[::-1]; tot = p.sum()
    isel = qn < 14
    return dict(n=n, nq=int(qm.size), avg=100 * p.mean(), avg_net=100 * (p.mean() - COST), avg_q=100 * qm.mean(),
                win=100 * (p > 0).mean(), med=100 * np.median(p), top5_share=(s[:5].sum() / tot) if tot > 0 else np.nan,
                avg_wo_top5=100 * s[5:].mean() if n > 5 else np.nan,
                is_n=int(isel.sum()), is_avg=100 * p[isel].mean() if isel.any() else np.nan,
                oos_n=int((~isel).sum()), oos_nq=int(len(np.unique(qn[~isel]))), oos_avg=100 * p[~isel].mean() if (~isel).any() else np.nan,
                pct_q_pos=100 * (qm > 0).mean())

# ---------------- universes ----------------
FO = F[F.in_fo == True].reset_index(drop=True)
FO_O = O[O.in_fo == True].reset_index(drop=True)
print('F&O universe', len(FO), ' base mean three_day %.3f%%' % (100 * FO_O.three_day.mean()))
print('Placebo F&O windows', len(PL), ' base mean %.3f%%' % (100 * PL.three_day.mean()))

variants = [(s, o) for s in SETUPS for o in OUTCOMES]
rows = []
masks_fo = {}
for (sid, d, conds, note), o in variants:
    mf, _ = mask(FO, conds); masks_fo[(sid, o)] = mf
    st = stats(pnl_of(FO_O, d, o)[mf], FO_O.qn.values[mf])
    ma, _ = mask(F, conds)
    sa = stats(pnl_of(O, d, o)[ma], O.qn.values[ma])
    pre = ma & (O.in_fo.values == False)
    sp = stats(pnl_of(O, d, o)[pre], O.qn.values[pre])
    mp, dropped = mask(PL, conds, allow_missing_cols=True)
    ppl = pnl_of(PL, d, o)[mp]
    rows.append(dict(setup=sid, dir='long' if d > 0 else 'short', outcome=o, note=note,
                     **{k: st.get(k) for k in ['n', 'nq', 'avg', 'avg_net', 'avg_q', 'win', 'med', 'top5_share', 'avg_wo_top5', 'pct_q_pos', 'is_n', 'is_avg', 'oos_n', 'oos_nq', 'oos_avg']},
                     all_n=sa.get('n'), all_avg=sa.get('avg'), preFO_n=sp.get('n'), preFO_avg=sp.get('avg'),
                     placebo_n=int(mp.sum()), placebo_avg=100 * ppl.mean() if mp.any() else np.nan,
                     placebo_is=100 * ppl[PL.qn.values[mp] < 14].mean() if mp.any() else np.nan,
                     placebo_oos=100 * ppl[PL.qn.values[mp] >= 14].mean() if mp.any() else np.nan,
                     placebo_dropped='|'.join(dropped)))
res = pd.DataFrame(rows)

# ---------------- per-setup shuffle p-values (F&O, 22 quarters) ----------------
rng = np.random.default_rng(SEED)
qn = FO_O.qn.values; N = len(FO_O)
groups = [np.where(qn == q)[0] for q in range(NQ)]
def perm_index(rng):
    pi = np.empty(N, int)
    for g in groups: pi[g] = rng.permutation(g)
    return pi
M = np.array([masks_fo[v] for v in [(s[0], o) for s, o in variants]], dtype=float)   # V x N
dirs = np.array([s[1] for s, o in variants]); outs = np.array([o for s, o in variants])
Y3, YT, YS = FO_O.three_day.values, FO_O.tp3.values, FO_O.tp3s.values
def variant_pnl_matrix(pi):
    """N x V matrix of P&L for each variant given row permutation pi of outcomes."""
    y3, yt, ys = Y3[pi], YT[pi], YS[pi]
    cols = []
    for d, o in zip(dirs, outs):
        cols.append(d * y3 if o == '3day' else (yt if d > 0 else ys))
    return np.array(cols)  # V x N
real_tot = (M * variant_pnl_matrix(np.arange(N))).sum(1)
cnt = M.sum(1)
B = N_SHUFFLE_SETUP; ge = np.zeros(len(variants))
for b in range(B):
    tot = (M * variant_pnl_matrix(perm_index(rng))).sum(1)
    ge += tot >= real_tot - 1e-12
res['shuffle_p'] = ge / B
res['shuffle_p'] = np.where(cnt > 0, res['shuffle_p'], np.nan)

# ---------------- selection protocol: in-sample best, walk-forward, shuffles ----------------
Q1 = np.zeros((N, NQ)); Q1[np.arange(N), qn] = 1
CQ = M @ Q1                                    # V x Q counts (fixed)
def qsums(pi):
    Pm = variant_pnl_matrix(pi)                # V x N
    return (M * Pm) @ Q1                       # V x Q sums
def select(SQ, minT):
    out = {}
    cis, sis = CQ[:, IS].sum(1), SQ[:, IS].sum(1)
    nqis = (CQ[:, IS] > 0).sum(1)
    elig = (cis >= minT) & (nqis >= 5)
    avg = np.where(elig, sis / np.maximum(cis, 1), -np.inf)
    v = int(np.argmax(avg))
    out['is_best'] = v; out['is_avg'] = 100 * avg[v]; out['is_n'] = int(cis[v])
    co, so = CQ[v, ~IS].sum(), SQ[v, ~IS].sum()
    out['oos_n'] = int(co); out['oos_avg'] = 100 * so / co if co > 0 else np.nan
    out['oos_nq'] = int((CQ[v, ~IS] > 0).sum())
    # walk-forward
    ws, wc, chosen = 0.0, 0.0, []
    for q in range(6, NQ):
        c, s = CQ[:, :q].sum(1), SQ[:, :q].sum(1)
        el = (c >= minT) & ((CQ[:, :q] > 0).sum(1) >= 3)
        if not el.any(): chosen.append(None); continue
        a = np.where(el, s / np.maximum(c, 1), -np.inf); vq = int(np.argmax(a))
        chosen.append(vq); ws += SQ[vq, q]; wc += CQ[vq, q]
    out['wf_n'] = int(wc); out['wf_avg'] = 100 * ws / wc if wc > 0 else np.nan; out['wf_chosen'] = chosen
    return out
vname = ['%s/%s' % (s[0], o) for s, o in variants]
real_sel = {}
for minT in MIN_TRADES_LIST:
    r = select(qsums(np.arange(N)), minT)
    r['is_best_name'] = vname[r['is_best']]
    r['wf_chosen_names'] = [vname[c] if c is not None else None for c in r['wf_chosen']]
    real_sel[minT] = r
shuf_rows = []
rng2 = np.random.default_rng(SEED + 1)
for b in range(N_SHUFFLE):
    SQ = qsums(perm_index(rng2))
    for minT in MIN_TRADES_LIST:
        r = select(SQ, minT)
        shuf_rows.append(dict(run=b, minT=minT, is_avg=r['is_avg'], is_n=r['is_n'], oos_avg=r['oos_avg'], oos_n=r['oos_n'], wf_avg=r['wf_avg'], wf_n=r['wf_n'], best=vname[r['is_best']]))
sh = pd.DataFrame(shuf_rows); sh.to_csv(os.path.join(HERE, 'shuffle_selection.csv'), index=False)
sel_summary = {}
for minT in MIN_TRADES_LIST:
    r = real_sel[minT]; s = sh[sh.minT == minT]
    sel_summary[minT] = dict(real_is_best=r['is_best_name'], real_is_avg=r['is_avg'], real_is_n=r['is_n'],
                             real_oos_avg=r['oos_avg'], real_oos_n=r['oos_n'], real_oos_nq=r['oos_nq'],
                             real_wf_avg=r['wf_avg'], real_wf_n=r['wf_n'], wf_chosen=r['wf_chosen_names'],
                             shuf_is_avg_median=s.is_avg.median(), shuf_is_avg_p95=s.is_avg.quantile(0.95),
                             frac_shuf_is_ge_real=float((s.is_avg >= r['is_avg']).mean()),
                             shuf_oos_avg_mean=s.oos_avg.mean(), shuf_oos_avg_p95=s.oos_avg.quantile(0.95),
                             frac_shuf_oos_ge_real=float((s.oos_avg >= r['oos_avg']).mean()),
                             shuf_wf_avg_mean=s.wf_avg.mean(), shuf_wf_avg_p95=s.wf_avg.quantile(0.95),
                             frac_shuf_wf_ge_real=float((s.wf_avg >= r['wf_avg']).mean()),
                             frac_shuf_is_best_over_5=float((s.is_avg > 5).mean()))
json.dump(sel_summary, open(os.path.join(HERE, 'selection_results.json'), 'w'), indent=1, default=float)

# ---------------- L01 stability (lag vs Nifty in the week) ----------------
stab = []
for th in [-0.06, -0.08, -0.10, -0.12, -0.15]:
    for uni, df, oo in [('F&O', FO, FO_O), ('all', F, O), ('preF&O', F[F.in_fo == False], O[O.in_fo == False])]:
        mm = (df.vs_nifty_1w.values < th)
        p = oo.three_day.values[mm]; st = stats(p, oo.qn.values[mm])
        stab.append(dict(threshold=th, universe=uni, **st))
    mp = PL.vs_nifty_1w.values < th
    stab.append(dict(threshold=th, universe='placebo F&O non-results', n=int(mp.sum()), avg=100 * PL.three_day.values[mp].mean(),
                     is_avg=100 * PL.three_day.values[mp & (PL.qn.values < 14)].mean(), oos_avg=100 * PL.three_day.values[mp & (PL.qn.values >= 14)].mean()))
stab = pd.DataFrame(stab); stab.to_csv(os.path.join(HERE, 'l01_stability.csv'), index=False)

res.to_csv(os.path.join(HERE, 'setup_results.csv'), index=False)

# ---------------- per-quarter detail for setups with avg >= 2% and n >= 10 ----------------
top = res[(res.n >= 10)].sort_values('avg', ascending=False).head(8)
pq, trades = [], []
for _, t in top.iterrows():
    s = [x for x in SETUPS if x[0] == t.setup][0]
    mf = masks_fo[(t.setup, t.outcome)]
    p = pnl_of(FO_O, s[1], t.outcome)[mf]
    g = pd.Series(p).groupby(FO_O.qn.values[mf]).agg(['size', 'mean'])
    for q in range(NQ):
        pq.append(dict(variant=t.setup + '/' + t.outcome, qn=q, n=int(g['size'].get(q, 0)), avg=100 * g['mean'].get(q, np.nan)))
    tt = FO_O[mf][['symbol', 'quarter', 'qn']].copy(); tt['pnl_pct'] = 100 * p; tt['variant'] = t.setup + '/' + t.outcome
    trades.append(tt)
pd.DataFrame(pq).to_csv(os.path.join(HERE, 'per_quarter_top.csv'), index=False)
pd.concat(trades).to_csv(os.path.join(HERE, 'setup_trades_top.csv'), index=False)

# ---------------- print ----------------
show = ['setup', 'outcome', 'n', 'nq', 'avg', 'avg_net', 'avg_q', 'win', 'med', 'top5_share', 'avg_wo_top5', 'is_n', 'is_avg', 'oos_n', 'oos_avg', 'shuffle_p', 'all_n', 'all_avg', 'preFO_n', 'preFO_avg', 'placebo_n', 'placebo_avg', 'placebo_dropped']
print(res[show].round(2).to_string())
print('\nL01 stability'); print(stab[['threshold', 'universe', 'n', 'nq', 'avg', 'avg_q', 'win', 'med', 'top5_share', 'avg_wo_top5', 'is_n', 'is_avg', 'oos_n', 'oos_avg']].round(2).to_string())
print('\nSelection protocol'); print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != 'wf_chosen'} for k, v in sel_summary.items()}, indent=1, default=float))
print('\nWF chosen (minT=10):', sel_summary[10]['wf_chosen'])
print('\nVariants with 22q avg > 5% and n>=10:', res[(res.avg > 5) & (res.n >= 10) & (res.nq >= 5)][['setup', 'outcome', 'n', 'avg']].to_string())
print('Variants tried:', len(variants))
