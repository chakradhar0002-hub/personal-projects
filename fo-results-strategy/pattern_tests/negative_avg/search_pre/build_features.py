"""Build the cutoff-time FEATURE table for the 3,280 F&O results (no outcomes read here).

Point in time (short entered at the close of the cutoff session i_cut):
  - price / volume features: up to and including the close of i_cut (as in all earlier trade-A studies)
  - F&O bhavcopy features (OI, PCR, IV, basis): the A1_ columns = session i_cut-1 (bhavcopy of t is published after t)
  - delivery features: feat_results.csv e_A = i_cut-1 (already lagged)
  - news features: announcements broadcast before 15:00 of the cutoff day (news feature file)
  - fundamentals: fa_panel 'pre' block (latest 4 quarters published before the cutoff)
  - sector index: close of i_cut vs i_cut-L
Every outcome-like column (three_day, d1..d3, XN, W, *_B, next*, rq_*, move ...) is dropped on load.
"""
import pandas as pd, numpy as np
SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = SP + '/negative_avg/search_pre'
K = ['symbol', 'qn']

panel = pd.read_csv(SP + '/perf/features/panel.csv')
drop = [c for c in panel.columns if c.endswith('_B') or c in ('XN', 'W')]
panel = panel.drop(columns=drop)

ta = pd.read_csv(SP + '/ta/build/events_ta.csv')
ta = ta[['symbol', 'qn', 'rsi14', 'close_vs_sma20_pct', 'close_vs_sma50_pct', 'close_vs_sma200_pct',
         'ret_5d_pct', 'bb_pctb', 'dist_52w_high_pct', 'obv_div20', 'mfi14', 'traded_at_cut']]

oi = pd.read_csv(SP + '/more_signals/oi/work/results_features.csv')
oi = oi[K + [c for c in oi.columns if c.startswith('A1_')]]

dl = pd.read_csv(SP + '/more_signals/delivery/feat_results.csv')
dl = dl[K + ['e_A', 'ACC', 'DQR', 'DPL', 'DP60', 'PR5', 'rank_ACC', 'rank_DQR']]

nw = pd.read_csv(SP + '/more_signals/news/work/feat_results.csv')
nw = nw[K + ['NEWS30', 'NORM30', 'NEWSR', 'PR30', 'CALLPRE', 'RDCHG', 'LEAD', 'LEADCHG', 'PROMSELL90', 'HOLDSELL90', 'BIZ_RX']]

fa = pd.read_csv(SP + '/fa/build/fa_panel.csv')
fa = fa[K + ['l1_pub_before_cutoff', 'l1_pat_yoy_pct', 'l2_pat_yoy_pct', 'l1_sales_yoy_pct', 'pat_up_yoy_4q',
             'loss_any_4q', 'ttm_pat_yoy_pct', 'debt_equity', 'pe', 'pe_vs_own3y_pct']]

df = panel.merge(ta, on=K, how='left').merge(oi, on=K, how='left').merge(dl, on=K, how='left') \
          .merge(nw, on=K, how='left').merge(fa, on=K, how='left')
assert len(df) == 3280 and not df.duplicated(K).any()

# sector index / Nifty returns over L sessions ending at the cutoff close
ic = pd.read_csv(SP + '/sector_lab/data/index_close.csv')
ses = pd.read_csv(SP + '/sector_lab/data/sessions.csv')
assert (ic.day.values == ses.day.values).all()
def idx_ret(col, i_end, L):
    v = ic[col].values
    a, b = v[i_end - L], v[i_end]
    return (b / a - 1) * 100
for L in (5, 21):
    df[f'sec{L}'] = [idx_ret(s, i, L) for s, i in zip(df.sector_index, df.i_cut)]
    df[f'nif{L}'] = idx_ret('Nifty 50', df.i_cut.values, L)
    df[f'sec{L}_vsN'] = df[f'sec{L}'] - df[f'nif{L}']
# stock 5-session return minus Nifty (ret_5d_pct is compounded 5-session stock return)
df['ret5_vsN'] = df['ret_5d_pct'] - df['nif5']
df['disc'] = df.qn <= 13
df.to_csv(OUT + '/features_cutoff.csv', index=False)
print('rows', len(df), 'discovery', int(df.disc.sum()))
print('missing share:'); print(df.isna().mean().round(3)[df.isna().mean() > 0].to_string())
