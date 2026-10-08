import os  # LAB_ROOT: folder holding search22/, sector/, sector_lab/data/ and five_pct/
import time, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wlib as W
df = W.load('fo'); qn = df.qn.values
pc = W.pieces(df); O = W.outcomes(pc)
for B in (int(sys.argv[1]),):
    t0 = time.time()
    E = W.Engine(df, qn <= 13, qn >= 14, B=B)
    t1 = time.time()
    r = E.run(*O['3day'], 0.0)
    t2 = time.time()
    print('B', B, 'init', round(t1-t0,1), 'run', round(t2-t1,1), r['counts'])
    for s in (1,-1):
        for m in E.ms:
            x = r['sides'][s][m]
            print(s, m, x['count100'], 'largest', x['largest100_n'], 'oos100', {k: (round(v,2) if isinstance(v,float) else v) for k,v in x['oos_of_100'].items()},
                  'shrunk top1', x['shrunk']['top1'], 'wilson top1', x['wilson']['top1'])
