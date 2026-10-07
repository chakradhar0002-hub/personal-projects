#!/usr/bin/env python3
"""
F6 ADDENDUM - POST-HOC (written AFTER seeing rv_main.py results; every variant here is COUNTED
on top of the 62 pre-registered ones).

Why: in part (b) the pre-registered 'short_bad_pat_yoy' variants were clearly NEGATIVE
(t -2.6 to -2.7), i.e. the mirror ("follow the price, ignore weak PAT") made money. And part (a)
suggested that shorting the beaten peer is a worse hedge than Nifty. Two post-hoc questions:

 A1-A4  "price beats fundamentals" mirror of (b): at F&O stock X's reaction-day close, X pat_yoy
        trails the median of >=2 already-reported same-group peers by > {25, 50} pts BUT X's
        reaction excess is ABOVE the peers' median -> buy X, Nifty hedge, hold {10, 20}.  (4 variants)
        Checks: (i) placebo shuffling pat_yoy inside group-season (does PAT add anything?);
                (ii) price-only baseline (same rule without the PAT condition);
                (iii) overlap with the known edge (X reaction excess > +4%).
 A5-A6  Known edge with SECTOR hedges: buy F&O X whose reaction excess vs Nifty > +4% at the
        reaction close, hold 20 sessions; hedge with (A5) X's sector index (basket of stock
        futures unless Bank/FinServ), (A6) equal-weight basket of same-group F&O peers already
        reported. Reference (not counted, already known): Nifty hedge.          (2 variants)
 Diagnostics (no new trade rule): split of a_continue_D8_any_h20 by winner reaction > 4% or not and
        by whether the winner was the later (fresh) or the earlier reporter.
ADDENDUM VARIANTS = 6  ->  TOTAL TESTED = 62 + 6 = 68
Run: python3 -I rv_addendum.py
"""
import os  # SECTOR_LAB: folder holding data/ from sector_lab_data.py
import sys
sys.path.append('/root/.local/lib/python3.11/site-packages')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import rv_main as M

ev = M.ev
OUT = M.OUT
rng = np.random.default_rng(4242)
pd.set_option('display.width', 250)


def st(df, col='main'):
    s = M.season_stats(df, col)
    return {k: (round(v, 2) if isinstance(v, float) else v) for k, v in s.items()}


def long_mirror(B, thr, h, ex_map=None, pat_cond=True):
    m = (B.Pgap.values > 0)
    if pat_cond:
        m &= (B.F.values < -thr)
    X = B[m]
    t = X.t.values
    fX = M.fwd_stock(X.s.values, t, h); fN = M.fwd_index('Nifty 50', t, h)
    df = pd.DataFrame({'qn': X.qn.values, 't': t, 's': X.s.values})
    df['main'] = 100 * (fX - fN) - M.C_SINGLE
    df['raw'] = 100 * fX - M.C_STOCK
    df['vs_sector'] = 100 * (fX - M.fwd_sector(X.sec.values, t, h)) - M.C_SINGLE
    df['vs_peer_basket'] = 100 * (fX - M.basket_fwd(X.fo_peers.values, t, h)) - M.C_PAIR
    return df[df.main.notna()]


rows = []
B = M.build_b(ev, 'pat_yoy')
B = B.merge(ev[['s', 'qn', 'exc']], on=['s', 'qn'], how='left')
print('=== A1-A4: long X when PAT trails peers but reaction beats peers (post-hoc mirror) ===')
for thr in [0.25, 0.50]:
    for h in [10, 20]:
        df = long_mirror(B, thr, h)
        df = df.merge(B[['s', 'qn', 'exc']], on=['s', 'qn'], how='left')
        s = st(df)
        base = st(long_mirror(B, thr, h, pat_cond=False))
        in_edge = df.exc > 0.04
        s_out = st(df[~in_edge]) if (~in_edge).sum() >= 3 else {}
        r = dict(variant=f'A_long_badPAT{int(thr*100)}_goodReaction_h{h}', **{f'main_{k}': v for k, v in s.items()},
                 raw_season_avg=st(df, 'raw').get('per_season_avg'), vs_sector_season_avg=st(df, 'vs_sector').get('per_season_avg'),
                 vs_peer_basket_season_avg=st(df, 'vs_peer_basket').get('per_season_avg'),
                 baseline_price_only_trades=base['trades'], baseline_price_only_season_avg=base['per_season_avg'],
                 baseline_price_only_t=base['t_season'], share_in_known_edge=round(in_edge.mean(), 2),
                 excl_known_edge_trades=s_out.get('trades'), excl_known_edge_season_avg=s_out.get('per_season_avg'),
                 excl_known_edge_t=s_out.get('t_season'))
        rows.append(r)
        print(pd.Series(r).to_string(), '\n')

# placebo: shuffle pat_yoy within group-season for the h20 variants
print('placebo: shuffle pat_yoy within group-season (200 runs)')
maskb = ev.grp.notna() & ev.exc.notna()
plc = {(0.25, 20): [], (0.50, 20): [], (0.25, 10): [], (0.50, 10): []}
for k in range(M.NPLACEBO):
    E2 = ev.copy()
    vals = E2.pat_yoy.values.copy()
    for _, idx in E2[maskb].groupby(['grp', 'qn']).groups.items():
        idx = np.asarray(idx); vals[idx] = rng.permutation(vals[idx])
    E2['pat_yoy'] = vals
    B2 = M.build_b(E2, 'pat_yoy')
    for key in plc:
        d2 = long_mirror(B2, key[0], key[1])
        q = d2.groupby('qn').main.mean()
        plc[key].append((q.mean(), M.tstat(q.values), len(d2)))
for key, draws in plc.items():
    name = f'A_long_badPAT{int(key[0]*100)}_goodReaction_h{key[1]}'
    r = [x for x in rows if x['variant'] == name][0]
    dm = np.array([d[0] for d in draws]); dt = np.array([d[1] for d in draws])
    r['placebo_season_avg_mean'] = round(dm.mean(), 2); r['placebo_t_mean'] = round(np.nanmean(dt), 2)
    r['placebo_share_avg_ge_actual'] = np.mean(dm >= r['main_per_season_avg'])
    r['placebo_share_t_ge_actual'] = np.mean(dt >= r['main_t_season'])
    print(f'{name}: actual avg {r["main_per_season_avg"]} t {r["main_t_season"]} | placebo avg {dm.mean():.2f} t {np.nanmean(dt):.2f} '
          f'| P(avg>=act) {r["placebo_share_avg_ge_actual"]:.3f} P(t>=act) {r["placebo_share_t_ge_actual"]:.3f}')

# ------------------------------------------------------------------ A5-A6 known edge + sector hedges
print('\n=== A5-A6: known edge (reaction excess > +4%, hold 20) with sector / peer hedges ===')
K = ev[ev.fo & (ev.exc > 0.04)].copy()
t = K.i_react.values; h = 20
fX = M.fwd_stock(K.s.values, t, h)
fN = M.fwd_index('Nifty 50', t, h)
fS = M.fwd_sector(K.sector_index.values, t, h)
sec_fut = K.sector_index.isin(M.FUT_INDICES).values
# peers already reported (reaction <= t), same group, F&O, excluding X
peer_lists = []
for _, x in K.iterrows():
    if pd.isna(x.grp):
        peer_lists.append(()); continue
    pm = (ev.grp == x.grp) & (ev.qn == x.qn) & ev.fo & (ev.i_react <= x.i_react) & (ev.s != x.s)
    peer_lists.append(tuple(ev.s[pm].values))
fP = M.basket_fwd(np.array(peer_lists, dtype=object), t, h)
KD = pd.DataFrame({'qn': K.qn.values, 't': t, 'symbol': K.symbol.values, 'exc': K.exc.values})
KD['ref_vs_nifty'] = 100 * (fX - fN) - M.C_SINGLE
KD['main'] = KD['ref_vs_nifty']
KD['vs_sector'] = 100 * (fX - fS) - np.where(sec_fut, M.C_STOCK + M.C_HEDGE, M.C_PAIR)
KD['vs_peer_basket'] = 100 * (fX - fP) - M.C_PAIR
KD['raw'] = 100 * fX - M.C_STOCK
KD = KD[KD.main.notna()]
KD.to_csv(OUT + 'addendum_known_edge_hedges.csv', index=False)
for col, lab in [('ref_vs_nifty', 'REFERENCE known edge vs Nifty'), ('vs_sector', 'A5 vs own sector index'),
                 ('vs_peer_basket', 'A6 vs basket of already-reported F&O peers'), ('raw', 'raw (unhedged)')]:
    d = KD[KD[col].notna()]
    s = M.season_stats(d, col)
    q = d.groupby('qn')[col].mean()
    sd_season = q.std(ddof=1)
    print(f'{lab:45s} trades {s["trades"]:4d} seasons {s["seasons"]:2d} per-season avg {s["per_season_avg"]:5.2f} '
          f't {s["t_season"]:5.2f} first14 {s["first14"]:5.2f} last8 {s["last8"]:5.2f} pos {s["seasons_pos"]}/{s["seasons"]} '
          f'season-SD {sd_season:4.2f}')
    if col in ('vs_sector', 'vs_peer_basket'):
        rows.append(dict(variant=f'A_known_edge_{col}_h20', **{f'main_{k}': (round(v, 2) if isinstance(v, float) else v)
                                                               for k, v in s.items()}, season_sd=round(sd_season, 2)))
# same-trade comparison (only trades where the peer basket exists)
both = KD.dropna(subset=['vs_peer_basket'])
print(f'  on the {len(both)} trades that have a peer basket: vs Nifty {both.groupby("qn").ref_vs_nifty.mean().mean():.2f}, '
      f'vs peers {both.groupby("qn").vs_peer_basket.mean().mean():.2f}')

# ------------------------------------------------------------------ diagnostics for (a)
print('\n=== diagnostics: a_continue_D8_any_h20 split ===')
P = M.build_pairs(ev)
dfa = M.eval_a(P, 0.08, 'any', 20, 'continue')
dfa['winner_in_known_edge'] = dfa.excW > 0.04
dfa['winner_is_fresh'] = dfa.tW >= dfa.tL
for col in ['winner_in_known_edge', 'winner_is_fresh']:
    for v in [True, False]:
        d = dfa[dfa[col] == v]
        s = M.season_stats(d, 'main'); sl = M.season_stats(d, 'long_vs_nifty'); ss = M.season_stats(d, 'short_vs_nifty')
        print(f'{col}={v!s:5s} trades {s["trades"]:5d} pair net {s["per_season_avg"]:5.2f} (t {s["t_season"]:5.2f}) | '
              f'long leg vs Nifty {sl["per_season_avg"]:5.2f} (t {sl["t_season"]:5.2f}) | short leg vs Nifty {ss["per_season_avg"]:5.2f} (t {ss["t_season"]:5.2f})')
        rows.append(dict(variant=f'diag_a_continue_D8_any_h20_{col}={v}', **{f'main_{k}': (round(x, 2) if isinstance(x, float) else x)
                                                                              for k, x in s.items()},
                         long_vs_nifty=round(sl['per_season_avg'], 2), short_vs_nifty=round(ss['per_season_avg'], 2)))

pd.DataFrame(rows).to_csv(OUT + 'addendum_results.csv', index=False)
print('\nADDENDUM variants counted: 6  -> total variants tested 68')
print('written', OUT + 'addendum_results.csv')
