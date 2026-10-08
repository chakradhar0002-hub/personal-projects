"""05_posthoc_rule.py -- POST-HOC (chosen after seeing 04): evaluate 'lag > 10% AND volume_5d_vs_60d >= 1.0' and its
complement inside lag > 10%, with the same evaluation as 03 (per quarter, halves, luck, placebo).  Not out-of-sample."""
import os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(f'{HERE}/03_combos.py').read()
# reuse 03's loaders and evaluate() without re-running its analyses
exec(src.split('# ------------------------------------------------------------------ S20 placebo (volume)')[0])
exec('def tstat(d):' + src.split('def tstat(d):')[1].split('# ------------------------------------------------------------------ S20 placebo')[0])
exec('def evaluate(' + src.split('def evaluate(')[1].split('# ------------------------------------------------------------------ COMBO-H selection')[0])
y = G.three_day_pct.values; q = G.qn.values.astype(int); QS = np.arange(22); qidx = [np.where(q == k)[0] for k in QS]
R = []
for lab, ex, sg in [('POST-HOC lag>10% & volume >= 1.0x', ['lag < -0.10', 'volume_5d_vs_60d >= 1.0'], 1),
                    ('POST-HOC lag>10% & volume < 1.0x', ['lag < -0.10', 'volume_5d_vs_60d < 1.0'], 1),
                    ('POST-HOC lag>10% & volume < 1.0x (short)', ['lag < -0.10', 'volume_5d_vs_60d < 1.0'], -1),
                    ('POST-HOC lag 5-10% & volume >= 1.0x', ['lag >= -0.10', 'volume_5d_vs_60d >= 1.0'], 1)]:
    o, pq = evaluate(lab, ex, sg, False)
    R.append(o)
    print(lab, ' | '.join(f"{int(r.qn)}:{int(r.trades)}/{r.avg:+.1f}" for r in pq.itertuples() if r.trades > 0))
R = pd.DataFrame(R); R.to_csv(f'{HERE}/posthoc_rule.csv', index=False)
show = ['name', 'trades', 'avg_pct', 'avg_net_pct', 'tp_pct', 'up_pct', 'quarters_positive', 'first14_trades', 'first14_avg_pct', 'last8_trades',
        'last8_avg_pct', 'last8_quarters_positive', 'without_best5_avg_pct', 'avg_lag', 'luck_p', 'luck_p_last8', 'placebo_n', 'placebo_avg_pct',
        'placebo_quarters_positive', 'results_minus_placebo']
print(R[show].round(2).to_string())
o, _ = evaluate('ALL-RESULTS post-hoc', ['lag < -0.10', 'volume_5d_vs_60d >= 1.0'], 1, False, universe=GA, pl=None)
print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in o.items() if k in show})
