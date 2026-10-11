#!/usr/bin/env python3
"""Independent holdout evaluator - step 3: statistics for the 3 finalists (C12, C42, MA4) and 4 reference groups.

Inputs (my own, this folder): eval_panel.csv (build.py), ma4_scores_seed0.csv (ma4.py). Percent units.
Writes: summary.csv, summary.md, per_quarter.csv, per_quarter.md, references.csv, references.md, trades_all.csv,
        evaluate.log
"""
import numpy as np
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = f'{SP}/negative_avg/holdout'
NDRAW = 20000
N_CANDIDATES = 40 + 42 + 35 + 14
DISC, HOLD, FULL = range(0, 14), range(14, 22), range(0, 22)
LOG = open(f'{OUT}/evaluate.log', 'w')


def P(*x):
    s = ' '.join(str(v) for v in x)
    print(s)
    LOG.write(s + '\n')


E = pd.read_csv(f'{OUT}/eval_panel.csv')
S = pd.read_csv(f'{OUT}/ma4_scores_seed0.csv')
E = E.merge(S[['symbol', 'qn', 'score', 'thr', 'pick']], on=['symbol', 'qn'], how='left', validate='1:1')
E['pick'] = E.pick.fillna(False).astype(bool)
for c in ['C12', 'C42', 'L4', 'W', 'GOOD', 'BELOW50', 'SB_cut', 'B0_ok', 'B1_ok']:
    E[c] = E[c].astype(bool)

# ------------------------------------------------------------------ trade definitions
# each "window" = (eligible mask, raw return, vs-Nifty return, primary short net, hedged short net, unhedged short net)
W = {
    'B0': dict(ok=E.B0_ok, raw=E.B0_stock, vsn=E.B0_vsN, prim=-E.B0_vsN - 0.19, hedged=-E.B0_vsN - 0.19,
               unhedged=-E.B0_stock - 0.17, label='post-results, close k -> close k+20, hedged, cost 0.19'),
    'B1r': dict(ok=E.B1_ok, raw=E.B1_stock, vsn=E.B1_vsN, prim=-E.B1_vsN - 0.27, hedged=-E.B1_vsN - 0.27,
                unhedged=-E.B1_stock - 0.25, label='REALISTIC: close k+1 -> close k+21, hedged, cost 0.25+0.02'),
    'A': dict(ok=E.three_day.notna(), raw=E.three_day, vsn=E.three_day - E.nifty3, prim=-E.three_day - 0.17,
              hedged=-(E.three_day - E.nifty3) - 0.19, unhedged=-E.three_day - 0.17,
              label='pre-results, close i_cut -> close i_p1, unhedged primary, cost 0.17 (hedged 0.19)'),
    'Ar': dict(ok=E.two_day.notna(), raw=E.two_day, vsn=E.two_day - E.nifty2, prim=-E.two_day - 0.25,
               hedged=-(E.two_day - E.nifty2) - 0.27, unhedged=-E.two_day - 0.25,
               label='REALISTIC: close i_cut+1 -> close i_p1, unhedged primary, cost 0.25 (hedged 0.27)'),
}
FIN = {
    'C12': dict(sig=E.C12, win='B0', real='B1r', primary='hedged'),
    'C42': dict(sig=E.C42, win='B0', real='B1r', primary='hedged'),
    'MA4': dict(sig=E.pick, win='A', real='Ar', primary='unhedged'),
}
REF = {
    'R1 lag21 < -10 & vol 5/60 < 1 (quiet-volume laggards), 3-day pre-results short':
        dict(sig=(E.lag21 < -10) & (E.vol_ratio_5_60 < 1.0), win='A'),
    'R2 GOOD numbers & close_k < SMA50 (good numbers below 50-day avg), short 20 sessions hedged':
        dict(sig=E.GOOD & E.BELOW50, win='B0'),
    'R3 winners XN > 4 & pre-results futures short build-up (A_dP5 < 0, A_dOI5 > 10), short 20 sessions hedged':
        dict(sig=E.W & E.SB_cut, win='B0'),
    'R4 losers XN < -4, short 20 sessions hedged':
        dict(sig=E.L4, win='B0'),
}
rng = np.random.default_rng(20261011)


def luck_p(qn, prof, pool_qn, pool_prof):
    """one-sided p: share of random same-size picks per quarter (from the base pool) with mean short net >= actual."""
    actual = prof.mean()
    tot = np.zeros(NDRAW)
    n = 0
    for q, nq in pd.Series(qn).value_counts().items():
        v = pool_prof[pool_qn == q]
        idx = rng.random((NDRAW, len(v))).argsort(axis=1)[:, :nq]
        tot += v[idx].sum(axis=1)
        n += nq
    return (1 + np.sum(tot / n >= actual - 1e-12)) / (1 + NDRAW)


def stats(sig, win, quarters, primary='hedged', halves=None, do_p=True):
    w = W[win]
    qmask = E.qn.isin(list(quarters))
    base = w['ok'] & qmask
    m = sig & base
    t = E[m]
    prof = w[primary][m].to_numpy()
    r = dict(n=int(m.sum()), stocks=int(t.symbol.nunique()), max_per_stock=int(t.symbol.value_counts().max()) if len(t) else 0,
             raw=w['raw'][m].mean(), vsN=w['vsn'][m].mean(), short=prof.mean() if len(prof) else np.nan,
             med=np.median(prof) if len(prof) else np.nan,
             hedged=w['hedged'][m].mean(), unhedged=w['unhedged'][m].mean())
    sp = np.sort(prof)
    r['wo5'] = sp[:-5].mean() if len(sp) > 5 else np.nan
    r['wo10'] = sp[:-10].mean() if len(sp) > 10 else np.nan
    hs = np.sort(w['hedged'][m].to_numpy())
    r['hedged_wo5'] = hs[:-5].mean() if len(hs) > 5 else np.nan
    pq = pd.Series(prof, index=t.qn.to_numpy()).groupby(level=0).mean()
    r['q_trades'] = len(pq)
    r['q_pos'] = int((pq > 0).sum())
    r['t_q'] = pq.mean() / (pq.std(ddof=1) / np.sqrt(len(pq))) if len(pq) > 2 else np.nan
    r['base_n'] = int(base.sum())
    r['base_short'] = w[primary][base].mean()
    r['base_raw'] = w['raw'][base].mean()
    r['base_vsN'] = w['vsn'][base].mean()
    r['margin'] = r['short'] - r['base_short']
    if halves:
        for i, h in enumerate(halves, 1):
            mh = m & E.qn.isin(list(h))
            r[f'h{i}_n'] = int(mh.sum())
            r[f'h{i}_short'] = w[primary][mh].mean()
    if do_p and r['n'] > 0:
        r['p'] = luck_p(t.qn.to_numpy(), prof, E.qn[base].to_numpy(), w[primary][base].to_numpy())
        r['p_hedged'] = luck_p(t.qn.to_numpy(), w['hedged'][m].to_numpy(), E.qn[base].to_numpy(),
                               w['hedged'][base].to_numpy()) if primary != 'hedged' else r['p']
    r['hit_fall'] = float((w['raw'][m] < 0).mean() * 100) if r['n'] else np.nan
    return r


# ------------------------------------------------------------------ 1. discovery reproduction
CLAIM = {
    'C12': dict(n=88, vsN=-1.43, raw=-1.01, short=1.24, wo5=0.54, h1_n=58, h1_short=1.66, h2_n=30, h2_short=0.45,
                base_short=-0.98, unhedged=0.84),
    'C42': dict(n=74, vsN=-0.84, raw=-0.75, short=0.65, wo5=-0.31, h1_n=41, h1_short=1.10, h2_n=33, h2_short=0.09,
                base_short=-0.98, unhedged=0.58),
    'MA4': dict(n=132, raw=-0.59, vsN=-0.89, short=0.42, wo5=-0.07, h1_n=41, h1_short=0.34, h2_n=91, h2_short=0.46,
                base_short=-0.41, hedged=0.70, hedged_wo5=0.21),
}
P('=' * 100)
P('1. DISCOVERY REPRODUCTION (my code vs the search report; flag > 0.05 points or > 1 trade)')
mism = []
disc = {}
for f, d in FIN.items():
    qd = range(4, 14) if f == 'MA4' else DISC
    hv = [range(4, 7), range(7, 14)] if f == 'MA4' else [range(0, 7), range(7, 14)]
    r = stats(d['sig'], d['win'], qd, d['primary'], hv, do_p=False)
    disc[f] = r
    line = []
    for key, cv in CLAIM[f].items():
        mv = r[key]
        bad = abs(mv - cv) > (1 if key.endswith('n') else 0.05)
        line.append(f'{key} {mv:.2f} (claimed {cv}){" MISMATCH" if bad else ""}')
        if bad:
            mism.append(f'{f} discovery {key}: mine {mv:.3f} vs claimed {cv}')
    P(f'  {f}: ' + '; '.join(line))
P('  mismatches: ' + ('; '.join(mism) if mism else 'none'))

# ------------------------------------------------------------------ 2-4. holdout, realistic, full sample
P('=' * 100)
rows = []
HH = [range(14, 18), range(18, 22)]
for f, d in FIN.items():
    for tag, win, qs in [('discovery', d['win'], range(4, 14) if f == 'MA4' else DISC),
                         ('HOLDOUT', d['win'], HOLD), ('HOLDOUT realistic', d['real'], HOLD),
                         ('discovery realistic', d['real'], range(4, 14) if f == 'MA4' else DISC),
                         ('full 22q (in-sample)', d['win'], range(4, 22) if f == 'MA4' else FULL)]:
        r = stats(d['sig'], win, qs, d['primary'], HH if tag.startswith('HOLDOUT') else None,
                  do_p=tag.startswith('HOLDOUT'))
        r.update(finalist=f, sample=tag, window=W[win]['label'], primary=d['primary'])
        rows.append(r)
R = pd.DataFrame(rows)
hold = R[R['sample'] == 'HOLDOUT'].copy()
# Holm across the 3 finalists (primary holdout luck p)
order = hold.sort_values('p').index.tolist()
m_ = len(order)
adj, run = {}, 0.0
for i, ix in enumerate(order):
    run = max(run, min(1.0, (m_ - i) * hold.loc[ix, 'p']))
    adj[ix] = run
R['p_holm'] = pd.Series(adj)
hold = R[R['sample'] == 'HOLDOUT']
P('2-3. HOLDOUT qn 14-21 (primary measure: C12/C42 hedged short net, MA4 unhedged short net)')
surv = []
for _, r in hold.iterrows():
    crit = {'short>0': r['short'] > 0, 'margin>=0.5': r['margin'] >= 0.5, 'Holm p<0.10': r['p_holm'] < 0.10,
            'n>=20': r['n'] >= 20, 'wo5>0': r['wo5'] > 0}
    ok = all(crit.values())
    R.loc[(R.finalist == r.finalist) & (R['sample'] == 'HOLDOUT'), 'survivor'] = ok
    R.loc[(R.finalist == r.finalist) & (R['sample'] == 'HOLDOUT'), 'failed'] = ', '.join(k for k, v in crit.items() if not v)
    if ok:
        surv.append(r.finalist)
    P(f"  {r.finalist}: n {r.n} ({r.stocks} stocks, max {r.max_per_stock}/stock), raw {r.raw:+.2f}, vsN {r.vsN:+.2f}, "
      f"short net {r.short:+.2f} (median {r.med:+.2f}, w/o 5 biggest falls {r.wo5:+.2f}, w/o 10 {r.wo10:+.2f}), "
      f"hedged {r.hedged:+.2f} / unhedged {r.unhedged:+.2f}, quarters {r.q_pos}/{r.q_trades} short-profitable, "
      f"halves qn14-17 {r.h1_n} {r.h1_short:+.2f} / qn18-21 {r.h2_n} {r.h2_short:+.2f}, t_q {r.t_q:+.2f}; "
      f"base short {r.base_short:+.2f} (n {r.base_n}, base raw {r.base_raw:+.2f}, vsN {r.base_vsN:+.2f}), "
      f"margin {r.margin:+.2f}; luck p {r.p:.4f} (hedged p {r.p_hedged:.4f}), Holm {r.p_holm:.4f}; "
      f"SURVIVOR {'YES' if all(crit.values()) else 'NO - fails ' + ', '.join(k for k, v in crit.items() if not v)}")
P(f'  survivors: {surv if surv else "NONE"}; total candidates tried across the 4 families: {N_CANDIDATES}; '
  f'Holm over the 3 finalists')
P('4. REALISTIC (entry one session later, costs 0.25 + 0.02 hedge)')
for _, r in R[R['sample'].str.contains('realistic')].iterrows():
    P(f"  {r.finalist} {r['sample']}: n {r.n}, raw {r.raw:+.2f}, vsN {r.vsN:+.2f}, short net {r.short:+.2f} "
      f"(w/o 5 {r.wo5:+.2f}), base {r.base_short:+.2f}, margin {r.margin:+.2f}"
      + (f", luck p {r.p:.4f}" if 'HOLDOUT' in r['sample'] else ''))
P('5. FULL SAMPLE (in-sample)')
for _, r in R[R['sample'].str.startswith('full')].iterrows():
    P(f"  {r.finalist}: n {r.n}, raw {r.raw:+.2f}, vsN {r.vsN:+.2f}, short net {r.short:+.2f} (w/o 5 {r.wo5:+.2f}), "
      f"hedged {r.hedged:+.2f}, unhedged {r.unhedged:+.2f}, quarters {r.q_pos}/{r.q_trades}, base {r.base_short:+.2f}, "
      f"margin {r.margin:+.2f}")
R.to_csv(f'{OUT}/summary.csv', index=False, float_format='%.4f')

# ------------------------------------------------------------------ per-quarter (22 quarters) next to the base
pq_rows = []
for f, d in FIN.items():
    w = W[d['win']]
    for q in FULL:
        base = w['ok'] & (E.qn == q)
        m = d['sig'] & base
        pq_rows.append(dict(finalist=f, qn=q, quarter=E.quarter[E.qn == q].iloc[0], n=int(m.sum()),
                            avg_raw=w['raw'][m].mean(), avg_vsN=w['vsn'][m].mean(),
                            short=w[d['primary']][m].mean(), base_n=int(base.sum()), base_raw=w['raw'][base].mean(),
                            base_vsN=w['vsn'][base].mean(), base_short=w[d['primary']][base].mean(),
                            sample='holdout' if q >= 14 else 'discovery'))
PQ = pd.DataFrame(pq_rows)
PQ.to_csv(f'{OUT}/per_quarter.csv', index=False, float_format='%.3f')


def fmt(x, nd=2, sign=True):
    return '' if pd.isna(x) else (f'{x:+.{nd}f}' if sign else f'{x:.{nd}f}')


md = ['| qn | quarter | set | C12 n | C12 avg vsN | C12 short | C42 n | C42 avg vsN | C42 short | B base n | B base vsN | '
      'B base short | MA4 n | MA4 avg 3d | MA4 short | A base n | A base 3d | A base short |',
      '|' + '---|' * 18]
for q in FULL:
    a = PQ[(PQ.qn == q) & (PQ.finalist == 'C12')].iloc[0]
    b = PQ[(PQ.qn == q) & (PQ.finalist == 'C42')].iloc[0]
    c = PQ[(PQ.qn == q) & (PQ.finalist == 'MA4')].iloc[0]
    md.append(f"| {q} | {a.quarter} | {'HOLD' if q >= 14 else 'disc'} | {a.n} | {fmt(a.avg_vsN)} | {fmt(a.short)} | "
              f"{b.n} | {fmt(b.avg_vsN)} | {fmt(b.short)} | {a.base_n} | {fmt(a.base_vsN)} | {fmt(a.base_short)} | "
              f"{c.n if q >= 4 else '-'} | {fmt(c.avg_raw)} | {fmt(c.short)} | {c.base_n} | {fmt(c.base_raw)} | "
              f"{fmt(c.base_short)} |")
open(f'{OUT}/per_quarter.md', 'w').write('\n'.join(md) + '\n')

# ------------------------------------------------------------------ references (contaminated, full sample seen)
P('=' * 100)
P('REFERENCES - known negative groups (ALREADY SEEN on the full sample; contaminated, not finalists)')
ref_rows = []
for name, d in REF.items():
    for tag, qs in [('discovery', DISC), ('HOLDOUT', HOLD), ('full', FULL)]:
        prim = 'unhedged' if d['win'] == 'A' else 'hedged'
        r = stats(d['sig'], d['win'], qs, prim, HH if tag == 'HOLDOUT' else None, do_p=(tag == 'HOLDOUT'))
        r.update(reference=name, sample=tag, primary=prim)
        ref_rows.append(r)
        P(f"  {name[:2]} {tag:9s}: n {r['n']}, raw {r['raw']:+.2f}, vsN {r['vsN']:+.2f}, short net ({prim}) {r['short']:+.2f} "
          f"(w/o 5 {r['wo5']:+.2f}), hedged {r['hedged']:+.2f}, quarters {r['q_pos']}/{r['q_trades']}, "
          f"base {r['base_short']:+.2f}, margin {r['margin']:+.2f}" + (f", luck p {r['p']:.4f}" if 'p' in r else ''))
RF = pd.DataFrame(ref_rows)
RF.to_csv(f'{OUT}/references.csv', index=False, float_format='%.4f')

# ------------------------------------------------------------------ trades
tr = []
for f, d in FIN.items():
    w = W[d['win']]
    m = d['sig'] & w['ok']
    t = E.loc[m, ['symbol', 'qn', 'quarter', 'i_cut', 'i_react', 'XN', 'c_vs_sma50', 'c_vs_sma200', 'BAD',
                  'volr50']].copy()
    t['finalist'] = f
    t['raw'], t['vsN'], t['short_primary'] = w['raw'][m], w['vsn'][m], w[d['primary']][m]
    t['sample'] = np.where(t.qn >= 14, 'holdout', 'discovery')
    tr.append(t)
pd.concat(tr).to_csv(f'{OUT}/trades_all.csv', index=False, float_format='%.4f')

# 5 biggest holdout falls per finalist
for f in FIN:
    t = pd.concat(tr)
    t = t[(t.finalist == f) & (t['sample'] == 'holdout')].sort_values('short_primary', ascending=False).head(5)
    P(f'  {f} 5 biggest holdout short profits: ' + ', '.join(f'{a} q{b} {c:+.1f}' for a, b, c in
                                                             zip(t.symbol, t.qn, t.short_primary)))

# ------------------------------------------------------------------ secondary (info only; not survivor criteria)
P('=' * 100)
P('SECONDARY (information only - NOT survivor criteria, not counted as tests)')
W['B40'] = dict(ok=E.B40_ok.astype(bool), raw=E.B40_stock, vsn=E.B40_vsN, prim=-E.B40_vsN - 0.19,
                hedged=-E.B40_vsN - 0.19, unhedged=-E.B40_stock - 0.17, label='close k -> close k+40, hedged')
sec = []
for name, sig, win, prim in [('C12 unhedged (short stock only)', E.C12, 'B0', 'unhedged'),
                             ('C42 unhedged (short stock only)', E.C42, 'B0', 'unhedged'),
                             ('MA4 Nifty-hedged', E.pick, 'A', 'hedged'),
                             ('C22 = L4 & B200, 40 sessions hedged (bumped by the overlap clause; not a finalist)',
                              E.L4 & (E.c_vs_sma200 < 0), 'B40', 'hedged')]:
    for tag, qs in [('discovery', range(4, 14) if name.startswith('MA4') else DISC), ('HOLDOUT', HOLD)]:
        r = stats(sig, win, qs, prim, HH if tag == 'HOLDOUT' else None, do_p=(tag == 'HOLDOUT'))
        r.update(name=name, sample=tag)
        sec.append(r)
        P(f"  {name} {tag}: n {r['n']}, raw {r['raw']:+.2f}, vsN {r['vsN']:+.2f}, short net {r['short']:+.2f} "
          f"(w/o 5 {r['wo5']:+.2f}), quarters {r['q_pos']}/{r['q_trades']}, base {r['base_short']:+.2f}, "
          f"margin {r['margin']:+.2f}" + (f", halves {r['h1_short']:+.2f} / {r['h2_short']:+.2f}, luck p {r['p']:.4f}"
                                          if tag == 'HOLDOUT' else ''))
pd.DataFrame(sec).to_csv(f'{OUT}/secondary.csv', index=False, float_format='%.4f')

# ------------------------------------------------------------------ summary.md
H = R[R['sample'] == 'HOLDOUT'].set_index('finalist')
Dd = R[R['sample'] == 'discovery'].set_index('finalist')
Rr = R[R['sample'] == 'HOLDOUT realistic'].set_index('finalist')
Fu = R[R['sample'].str.startswith('full')].set_index('finalist')
L = ['| | C12 losers below SMA50 & SMA200 (B, 20d, hedged) | C42 BAD + breakdown on volume (B, 20d, hedged) | '
     'MA4 GBM bottom decile (A, 3-day, unhedged) |', '|---|---|---|---|']
def row(label, fn):
    L.append(f'| {label} | ' + ' | '.join(fn(f) for f in ['C12', 'C42', 'MA4']) + ' |')
row('Discovery n / short net (mine = claimed)', lambda f: f"{Dd.loc[f,'n']} / {Dd.loc[f,'short']:+.2f}")
row('HOLDOUT n (stocks)', lambda f: f"{H.loc[f,'n']} ({H.loc[f,'stocks']})")
row('Holdout avg stock return raw / vs Nifty', lambda f: f"{H.loc[f,'raw']:+.2f} / {H.loc[f,'vsN']:+.2f}")
row('Holdout short net after costs (primary)', lambda f: f"**{H.loc[f,'short']:+.2f}**")
row('Holdout median short net', lambda f: f"{H.loc[f,'med']:+.2f}")
row('Holdout short net w/o 5 biggest falls', lambda f: f"{H.loc[f,'wo5']:+.2f}")
row('Holdout hedged / unhedged short net', lambda f: f"{H.loc[f,'hedged']:+.2f} / {H.loc[f,'unhedged']:+.2f}")
row('Holdout quarters short-profitable / with trades', lambda f: f"{H.loc[f,'q_pos']} / {H.loc[f,'q_trades']}")
row('Holdout halves qn14-17 / qn18-21 (n, short)', lambda f: f"{H.loc[f,'h1_n']} {H.loc[f,'h1_short']:+.2f} / "
    f"{H.loc[f,'h2_n']} {H.loc[f,'h2_short']:+.2f}")
row('Base short, same window and quarters', lambda f: f"{H.loc[f,'base_short']:+.2f} (n {H.loc[f,'base_n']})")
row('Margin vs base (needs >= +0.50)', lambda f: f"{H.loc[f,'margin']:+.2f}")
row('Luck p (one-sided, 20,000 random picks) / Holm (3)', lambda f: f"{H.loc[f,'p']:.3f} / {H.loc[f,'p_holm']:.3f}")
row('Realistic: entry 1 session later, cost 0.25(+0.02)', lambda f: f"{Rr.loc[f,'short']:+.2f} (w/o 5 "
    f"{Rr.loc[f,'wo5']:+.2f}; base {Rr.loc[f,'base_short']:+.2f})")
row('Full sample (in-sample) n / short net / w/o 5', lambda f: f"{Fu.loc[f,'n']} / {Fu.loc[f,'short']:+.2f} / "
    f"{Fu.loc[f,'wo5']:+.2f}")
row('SURVIVOR', lambda f: 'NO (fails ' + str(H.loc[f, 'failed']) + ')' if not H.loc[f, 'survivor'] else 'YES')
open(f'{OUT}/summary.md', 'w').write('\n'.join(L) + '\n')
RFh = RF[RF['sample'] == 'HOLDOUT']
L2 = ['| Reference (contaminated: seen on the full sample) | holdout n | raw | vs Nifty | short net | w/o 5 | '
      'quarters + | base | margin | luck p | full-sample n / short net |', '|' + '---|' * 11]
for _, r in RFh.iterrows():
    fu = RF[(RF.reference == r.reference) & (RF['sample'] == 'full')].iloc[0]
    L2.append(f"| {r.reference} | {r.n} | {r.raw:+.2f} | {r.vsN:+.2f} | {r.short:+.2f} | {r.wo5:+.2f} | "
              f"{r.q_pos}/{r.q_trades} | {r.base_short:+.2f} | {r.margin:+.2f} | {r.p:.3f} | {fu.n} / {fu.short:+.2f} |")
open(f'{OUT}/references.md', 'w').write('\n'.join(L2) + '\n')
LOG.close()
