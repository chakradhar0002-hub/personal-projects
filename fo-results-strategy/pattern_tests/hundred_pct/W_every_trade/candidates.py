"""
candidates.py -- the pre-registered candidates named before this task (no search here): win rates on the last 8
quarters (qn 14..21), the first 14 and all 22; 3-day and take-profit exits; gross and after costs (> +0.17%).
  C1 r3d <= -8%                                   long   (stock fell 8%+ in the 3 sessions before the cutoff)
  C2 vs_nifty_1m < -15%                           long   (lagged Nifty by > 15% over the month)
  C3 vs_ma200 <= -16.85% AND peers_reported_n <= 1 AND dist_20h <= -10.18%   long (hindsight rule, chosen on all 22)
  ML picks from five_pct/B_models/picks_real_fo.csv (walk-forward / split random-forest top picks, META selection)
Output: candidates_W.csv
"""
import sys, os
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wlib as W

H = W.HERE
rows = []
PARTS = (('all22', 0, 21), ('first14', 0, 13), ('last8', 14, 21))


def rec(name, universe, exit_, pnl, q, extra=None):
    for part, a, b in PARTS:
        s = (q >= a) & (q <= b)
        for lab, thr in (('gross', 0.0), ('net', W.COST)):
            r = W.trade_record(pnl[s], q[s], thr)
            d = {'candidate': name, 'universe': universe, 'exit': exit_, 'part': part, 'win_def': lab}
            d.update(r)
            if extra is not None:
                d.update({k: int(v[s].sum()) for k, v in extra.items()})
            rows.append(d)


for uni in ('fo', 'all'):
    df = W.load(uni)
    q = df.qn.values
    O = W.outcomes(W.pieces(df))
    # exact hindsight cut values = the condition ids printed by the earlier full-22 search
    M, names, _ = W.build_conditions(W.load('fo'), np.ones(len(W.load('fo')), bool))
    c200 = [n for n in names if n[0] == 'vs_ma200' and n[1] == '<=' and abs(n[2] + 0.1685) < 5e-4][0][2]
    c20h = [n for n in names if n[0] == 'dist_20h' and n[1] == '<=' and abs(n[2] + 0.1018) < 5e-4][0][2]
    with np.errstate(invalid='ignore'):
        C = {'C1 r3d<=-8% long': df.r3d.values <= -0.08,
             'C2 vs_nifty_1m<-15% long': df.vs_nifty_1m.values < -0.15,
             f'C3 vs_ma200<={c200:.4f} & peers_reported_n<=1 & dist_20h<={c20h:.4f} long (hindsight)':
                 (df.vs_ma200.values <= c200) & (df.peers_reported_n.values <= 1) & (df.dist_20h.values <= c20h)}
    pre = ~df.in_fo.values.astype(bool)
    for name, mk in C.items():
        for ex in ('3day', 'tp'):
            pnl = O[ex][0]
            rec(name, uni, ex, pnl[mk], q[mk], extra={'pre_fo_trades': pre[mk]} if uni == 'all' else None)

# ---------------- ML picks
pk = pd.read_csv(f'{W.SP}/five_pct/B_models/picks_real_fo.csv')
fo = W.load('fo')
O = W.outcomes(W.pieces(fo))
key = fo[['symbol', 'qn']].copy(); key['l3'] = O['3day'][0]; key['ltp'] = O['tp'][0]; key['s3'] = O['3day'][1]; key['stp'] = O['tp'][1]
pk = pk.merge(key, on=['symbol', 'qn'], how='left')
assert np.allclose(pk.three_day, pk.l3)
for (proto, fam, rule), g in pk.groupby(['protocol', 'family', 'rule']):
    if not (fam.startswith('RFc') or fam.startswith('ENS')) or rule not in ('top1', 'top2', 'top5', 'T2'):
        continue
    sgn = -1 if fam.endswith('-') else 1
    for ex in ('3day', 'tp'):
        col = ('l' if sgn > 0 else 's') + ('3' if ex == '3day' else 'tp')
        rec(f'ML {proto} {fam} {rule}', 'fo', ex, g[col].values, g.qn.values)
R = pd.DataFrame(rows)
R.to_csv(f'{H}/candidates_W.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 500); pd.set_option('display.max_colwidth', 80)
show = R[(R.part != 'first14')]
print(show[['candidate', 'universe', 'exit', 'part', 'win_def', 'trades', 'wins', 'win_rate', 'avg', 'worst', 'quarters',
            'quarters_pos', 'all_win'] + (['pre_fo_trades'] if 'pre_fo_trades' in R else [])].round(2).to_string())
