"""beam_check.py -- how sensitive are the 100%-rule counts to the beam size? (real data, F&O, 3day gross)"""
import os  # LAB_ROOT: folder holding search22/, sector/, sector_lab/data/ and five_pct/
import time, sys, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wlib as W
df = W.load('fo'); qn = df.qn.values
O = W.outcomes(W.pieces(df))
out = {}
for mode in ('split', 'full22'):
    tr = qn <= 13 if mode == 'split' else np.ones(len(df), bool)
    te = qn >= 14 if mode == 'split' else None
    for B in (250, 500, 1000, 2000, 4000):
        t0 = time.time()
        E = W.Engine(df, tr, te, B=B, ntop=10)
        r = E.run(*O['3day'], 0.0)
        row = {'secs': round(time.time() - t0, 1), 'counts': r['counts']}
        for s in (1, -1):
            for m in E.ms:
                x = r['sides'][s][m]
                row[f'{s}_{m}'] = [x['count100']['all'], x['largest100_n']] + ([round(x['oos_of_100']['pooled_winrate'] or -1, 1)] if te is not None else [])
        out[f'{mode}_B{B}'] = row
        print(mode, B, row, flush=True)
json.dump(out, open('beam_check.json', 'w'), indent=1)
