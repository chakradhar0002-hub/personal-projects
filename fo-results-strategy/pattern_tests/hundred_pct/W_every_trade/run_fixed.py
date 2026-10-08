"""
run_fixed.py -- hindsight (all 22 quarters) or fixed split (choose on qn 0..13, test on qn 14..21) search for
rules whose trades are ALL winners, on real data and on null data (within-quarter shuffle, sign-flip).

usage: python3 run_fixed.py UNIVERSE MODE SETTING THR NSHUF NFLIP [--B 1000] [--seed 1]
   UNIVERSE fo|all   MODE split|full22   SETTING 3day|tp   THR gross|net (net: win = P&L > +0.17%)
Outputs (this folder, tag = UNIVERSE_MODE_SETTING_THR):
   res_<tag>.json            real summary + null distributions + real-vs-null comparison
   list100_<tag>.csv.gz      every 100%-winner rule found on real data (>= 10 trades, >= 4 quarters)
   largest_<tag>.csv         the 25 largest 100% rules per side with full in-sample / out-of-sample records
   top_<tag>.csv             top-100 rules per side and m by shrunk win rate and by Wilson lower bound
   nulls_<tag>.csv           one row per null run
"""
import sys, os, json, time, argparse
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wlib as W

ap = argparse.ArgumentParser()
ap.add_argument('universe'); ap.add_argument('mode'); ap.add_argument('setting'); ap.add_argument('thr')
ap.add_argument('nshuf', type=int); ap.add_argument('nflip', type=int)
ap.add_argument('--B', type=int, default=1000); ap.add_argument('--seed', type=int, default=1)
A = ap.parse_args()
tag = f'{A.universe}_{A.mode}_{A.setting}_{A.thr}'
thr = 0.0 if A.thr == 'gross' else W.COST
H = W.HERE
t0 = time.time()
df = W.load(A.universe)
qn = df.qn.values
info = df.in_fo.values.astype(bool)
pc = W.pieces(df)
if A.mode == 'split':
    tr, te = qn <= 13, qn >= 14
else:
    tr, te = np.ones(len(df), bool), None
E = W.Engine(df, tr, te, B=A.B, ntop=100)
O = W.outcomes(pc)
pl, ps = O[A.setting]
real = E.run(pl, ps, thr, keep_list=True)
print(tag, 'real done', round(time.time() - t0, 1), real['counts'], flush=True)
SIDES = {1: 'long', -1: 'short'}


def full_record(conds, sgn):
    mk = W.rule_mask(E.M, conds)
    pnl = pl if sgn > 0 else ps
    rec = {'rule': W.rule_str(E.names, conds, sgn), 'side': SIDES[sgn], 'level': len(conds)}
    for lab, sel in (('is', tr), ('oos', te), ('all22', np.ones(len(df), bool))):
        if sel is None:
            continue
        r = W.trade_record(pnl[mk & sel], qn[mk & sel], thr)
        rec.update({f'{lab}_{k}': v for k, v in r.items()})
    if A.universe == 'all':
        rec['pre_fo_trades'] = int((mk & ~info).sum())
        rec['pre_fo_wins'] = int(((pnl > thr) & mk & ~info).sum())
    return rec


# ---------------- real: list of all 100% rules
rows = []
for sgn in (1, -1):
    L = real['sides'][sgn]['list100']
    for i in range(len(L['n'])):
        conds = [int(c) for c in L['conds'][i] if c >= 0]
        r = {'side': SIDES[sgn], 'level': int(L['level'][i]), 'rule': W.rule_str(E.names, conds, sgn),
             'is_trades': int(L['n'][i]), 'is_quarters': int(L['q'][i])}
        if te is not None:
            nt = int(L['nte'][i])
            r.update(oos_trades=nt, oos_wins=int(L['wte'][i]),
                     oos_win_rate=100 * L['wte'][i] / nt if nt else np.nan,
                     oos_avg=100 * L['ste'][i] / nt if nt else np.nan)
        rows.append(r)
LIST = pd.DataFrame(rows)
LIST.to_csv(f'{H}/list100_{tag}.csv.gz', index=False)

# ---------------- real: largest 100% rules with full records
lrows = []
for sgn in (1, -1):
    L = real['sides'][sgn]['list100']
    if not len(L['n']):
        continue
    order = np.lexsort((L['level'], -L['n']))
    seen = set()
    for i in order:
        conds = [int(c) for c in L['conds'][i] if c >= 0]
        key = np.packbits(W.rule_mask(E.M, conds)).tobytes()
        if key in seen:
            continue
        seen.add(key)
        rec = full_record(conds, sgn); rec['rank_by_size'] = len(seen)
        lrows.append(rec)
        if len(seen) >= 25:
            break
pd.DataFrame(lrows).to_csv(f'{H}/largest_{tag}.csv', index=False)

# ---------------- real: top lists
trows = []
for sgn in (1, -1):
    for m in E.ms:
        for crit in ('shrunk', 'wilson'):
            for rank, x in enumerate(real['sides'][sgn][m][crit]['rules']):
                rec = full_record(x['conds'], sgn)
                rec.update(min_trades=m, criterion=crit, rank=rank + 1, score=x['score'])
                trows.append(rec)
TOP = pd.DataFrame(trows)
TOP.to_csv(f'{H}/top_{tag}.csv', index=False)


def summ(r, keep_rules=False):
    """compact per-side / per-m summary of an Engine.run result"""
    out = {}
    for sgn in (1, -1):
        for m in E.ms:
            x = r['sides'][sgn][m]
            k = f'{SIDES[sgn]}_m{m}'
            out[f'{k}_count100'] = x['count100']['all']
            for L in (1, 2, 3):
                out[f'{k}_count100_L{L}'] = x['count100'][L]
            out[f'{k}_largest100'] = x['largest100_n']
            if te is not None:
                o = x['oos_of_100']
                out[f'{k}_oos100_pooled_wr'] = o['pooled_winrate']
                out[f'{k}_oos100_mean_wr'] = o['mean_rule_winrate']
                out[f'{k}_oos100_frac_allwin'] = o['frac_rules_oos_all_win']
                out[f'{k}_oos100_frac_allwin_ge5'] = o['frac_rules_oos_all_win_ge5']
                out[f'{k}_oos100_mean_avg'] = o['mean_rule_avg']
                lo = x.get('largest1_oos')
                out[f'{k}_largest1_oos_wr'] = (100 * lo['oos_wins'] / lo['oos_trades']) if lo and lo['oos_trades'] else None
                l10 = x.get('largest10_oos')
                out[f'{k}_largest10_oos_wr'] = l10['pooled_winrate'] if l10 else None
                for crit in ('shrunk', 'wilson'):
                    for kk in (1, 10, 100):
                        t = x[crit].get(f'top{kk}')
                        out[f'{k}_{crit}_top{kk}_oos_wr'] = t['pooled_winrate'] if t else None
                        out[f'{k}_{crit}_top{kk}_oos_avg'] = t['mean_rule_avg'] if t else None
                        out[f'{k}_{crit}_top{kk}_oos_allwin'] = t['frac_rules_oos_all_win'] if t else None
        # in-sample top-1 score
            for crit in ('shrunk', 'wilson'):
                rr = x[crit]['rules']
                out[f'{k}_{crit}_top1_is_wr'] = rr[0]['is_win_rate'] if rr else None
                out[f'{k}_{crit}_top1_is_n'] = rr[0]['is_trades'] if rr else None
    for m in E.ms:
        out[f'both_m{m}_count100'] = out[f'long_m{m}_count100'] + out[f'short_m{m}_count100']
        out[f'both_m{m}_largest100'] = max(out[f'long_m{m}_largest100'], out[f'short_m{m}_largest100'])
    return out


REAL = summ(real)
print({k: v for k, v in REAL.items() if 'count100' in k and '_L' not in k or 'largest100' in k}, flush=True)

# ---------------- nulls
E.ntop = 10
rng = np.random.default_rng(A.seed)
nrows = []
for kind, n in (('shuffle', A.nshuf), ('signflip', A.nflip)):
    for i in range(n):
        pcn = W.null_pieces(pc, qn, kind, rng)
        On = W.outcomes(pcn)
        rn = E.run(*On[A.setting], thr)
        row = summ(rn); row.update(kind=kind, run=i)
        nrows.append(row)
        if i % 10 == 9:
            print(tag, kind, i + 1, round(time.time() - t0, 1), flush=True)
NUL = pd.DataFrame(nrows)
NUL.to_csv(f'{H}/nulls_{tag}.csv', index=False)

# ---------------- comparison
cmp = {}
for kind in ('shuffle', 'signflip'):
    g = NUL[NUL.kind == kind]
    if not len(g):
        continue
    c = {}
    for k, rv in REAL.items():
        if rv is None or k not in g:
            continue
        v = pd.to_numeric(g[k], errors='coerce').dropna()
        if not len(v):
            continue
        c[k] = {'real': rv, 'null_mean': float(v.mean()), 'null_median': float(v.median()),
                'null_p95': float(v.quantile(0.95)), 'null_max': float(v.max()),
                'p_null_ge_real': float((v >= rv - 1e-12).mean()), 'n_runs': int(len(v))}
    cmp[kind] = c
res = {'tag': tag, 'universe': A.universe, 'mode': A.mode, 'setting': A.setting, 'thr': thr, 'B': A.B,
       'n_rows': int(len(df)), 'train_rows': int(tr.sum()), 'test_rows': int(te.sum()) if te is not None else 0,
       'counts_per_run': real['counts'], 'n_null_runs': {'shuffle': A.nshuf, 'signflip': A.nflip},
       'base_win_rate_long_train': float(100 * (pl[tr] > thr).mean()),
       'base_win_rate_short_train': float(100 * (ps[tr] > thr).mean()),
       'base_win_rate_long_test': float(100 * (pl[te] > thr).mean()) if te is not None else None,
       'base_win_rate_short_test': float(100 * (ps[te] > thr).mean()) if te is not None else None,
       'real': REAL, 'comparison': cmp, 'seconds': time.time() - t0}
json.dump(res, open(f'{H}/res_{tag}.json', 'w'), indent=1, default=float)
print(tag, 'done', round(time.time() - t0, 1))
