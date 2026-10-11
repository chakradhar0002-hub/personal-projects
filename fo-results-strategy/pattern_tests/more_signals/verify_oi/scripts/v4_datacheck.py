#!/usr/bin/env python3
"""Verifier - data checks: my independent raw re-download (my_fo.db) vs the family's stored compact tables
(fo_compact.db) and their features (results_features.csv) vs my features (my_results_features.csv).

usage: python3 -P v4_datacheck.py <scratchpad> <my_fo.db> <their fo_compact.db> <their results_features.csv>
                                  <my_results_features.csv> <out_dir>
"""
import sqlite3
import sys

import numpy as np
import pandas as pd

SP, MYDB, THDB, THF, MYF, OUT = sys.argv[1:7]
LOGF = open(f'{OUT}/v4_datacheck.log', 'w')
rng = np.random.default_rng(2026)


def log(*a):
    s = ' '.join(map(str, a))
    print(s, flush=True)
    LOGF.write(s + '\n')


my = sqlite3.connect(MYDB)
th = sqlite3.connect(THDB)
# ---------------- 1. whole-table comparison at the raw-ticker level
mf = pd.read_sql('select day, sym, expiry, oi, settle from vfut where expiry >= day', my)
mft = mf.groupby(['day', 'sym']).oi.sum().rename('my_oi')
tf = pd.read_sql('select day, sym, oi_tot, und, e1, e1_settle from fut', th).set_index(['day', 'sym'])
j = tf.join(mft, how='outer')
log('fut rows: theirs', len(tf), 'mine', len(mft), 'only theirs', int(j.my_oi.isna().sum()), 'only mine', int(j.oi_tot.isna().sum()))
jj = j.dropna(subset=['my_oi', 'oi_tot'])
rel = (jj.oi_tot / jj.my_oi - 1).abs()
log(f'futures OI (all expiries) theirs vs my raw: exact {float((rel < 1e-9).mean()):.4%}, >0.1% off {int((rel > 1e-3).sum())}')
if (rel > 1e-3).any():
    log(jj[rel > 1e-3].head(10).to_string())
mu = pd.read_sql('select day, sym, und from vund', my).set_index(['day', 'sym']).und.rename('my_und')
ju = tf[['und']].join(mu, how='inner').dropna()
ru = (ju.und / ju.my_und - 1).abs()
log(f'underlying close theirs vs mine: n {len(ju)}, exact {float((ru < 1e-9).mean()):.4%}, >0.1% off {int((ru > 1e-3).sum())}')
mo = pd.read_sql('select day, sym, ce_oi, pe_oi from vopt', my).set_index(['day', 'sym'])
to = pd.read_sql('select day, sym, ce_oi, pe_oi from opt', th).set_index(['day', 'sym'])
jo = to.join(mo, how='outer', lsuffix='_th', rsuffix='_my')
log('opt rows: theirs', len(to), 'mine', len(mo), 'only theirs', int(jo.ce_oi_my.isna().sum()), 'only mine', int(jo.ce_oi_th.isna().sum()))
jo = jo.dropna()
pc_th = jo.pe_oi_th / jo.ce_oi_th
pc_my = jo.pe_oi_my / jo.ce_oi_my
dpc = (pc_th - pc_my).abs()
log(f'PCR (all strikes/expiries) theirs vs mine: n {len(jo)}, exact {float((dpc < 1e-12).mean()):.4%}, |diff| > 0.001: {int((dpc > 1e-3).sum())}')
# front-futures settle (nearest expiry) comparison
m1 = mf.sort_values('expiry').drop_duplicates(['day', 'sym']).set_index(['day', 'sym'])
jt = tf[['e1', 'e1_settle']].join(m1[['expiry', 'settle']], how='inner')
log(f'nearest futures expiry equal: {float((jt.e1 == jt.expiry).mean()):.4%}; settle equal: '
    f'{float(((jt.e1_settle - jt.settle).abs() < 1e-6).mean()):.4%}')

# ---------------- 2. features: theirs vs mine on all results rows
TH = pd.read_csv(THF)
MY = pd.read_csv(MYF)
key = ['symbol', 'qn']
cmpcols = ['A_dOI5', 'A_dOI10', 'A_dP5', 'A_OI20', 'A_BASIS', 'A_BASISDEV', 'A_PCR', 'A_dPCR5', 'A_IV', 'A_IVREL', 'A_IVSPREAD',
           'A_dCIV20', 'A_dPIV20', 'B_dOI1', 'B_dOI5', 'B_OI20', 'B_BASISDEV', 'B_dBASIS1', 'B_PCR', 'B_dPCR1', 'B_IV', 'B_IVREL',
           'B_IVSPREAD', 'B_dCIV20', 'B_dPIV20']
M = TH[key + [c for c in cmpcols if c in TH.columns]].merge(MY[key + cmpcols], on=key, suffixes=('_th', '_my'))
rows = []
for c in cmpcols:
    if c + '_th' not in M.columns:
        continue
    a, b = M[c + '_th'], M[c + '_my']
    both = a.notna() & b.notna()
    d = (a - b).abs()[both]
    scale = np.maximum(np.abs(b[both]), 1e-9)
    rows.append({'feature': c, 'n_th': int(a.notna().sum()), 'n_my': int(b.notna().sum()), 'both': int(both.sum()),
                 'only_th': int((a.notna() & b.isna()).sum()), 'only_my': int((a.isna() & b.notna()).sum()),
                 'share_abs_diff<1e-4': float((d < 1e-4).mean()), 'share_rel_diff<1%': float((d / scale < 0.01).mean()),
                 'max_abs_diff': float(d.max()), 'corr': float(np.corrcoef(a[both], b[both])[0, 1])})
FC = pd.DataFrame(rows)
log('\nfeature agreement on 3,280 results rows (their features vs mine):')
log(FC.round(4).to_string(index=False))
FC.to_csv(f'{OUT}/feature_agreement.csv', index=False)

# ---------------- 3. sampled points behind the candidates: raw values side by side
ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv').day.to_numpy()
tr09 = pd.read_csv(f'{SP}/more_signals/oi/results/trades_B09.csv')
tr13 = pd.read_csv(f'{SP}/more_signals/oi/results/trades_B13.csv')
tr12 = pd.read_csv(f'{SP}/more_signals/oi/results/trades_A12.csv')
tr22 = pd.read_csv(f'{SP}/more_signals/oi/results/trades_A22.csv')
samp = pd.concat([tr09.sample(20, random_state=1).assign(c='B09', i=lambda x: x.i_react),
                  tr13.sample(10, random_state=2).assign(c='B13', i=lambda x: x.i_react),
                  tr12.sample(10, random_state=3).assign(c='A12', i=lambda x: x.i_cut),
                  tr22.sample(10, random_state=4).assign(c='A22', i=lambda x: x.i_cut)])[['c', 'symbol', 'qn', 'i']]
samp['day'] = ses[samp.i.to_numpy()]
log(f'\nsampled (candidate, symbol, day) points: {len(samp)}')
# map panel symbol -> raw ticker used on that day (my db): try the symbol itself, else known older tickers
REN = {}
import csv
from datetime import datetime
with open(f'{SP}/symbolchange.csv', encoding='latin-1') as fh:
    for row in csv.reader(fh):
        if len(row) >= 4:
            try:
                dd = datetime.strptime(row[3].strip().upper(), '%d-%b-%Y').date().isoformat()
            except ValueError:
                continue
            REN.setdefault(row[2].strip(), []).append((dd, row[1].strip()))


def raw_candidates(sym, d):
    out = [sym]
    cur = sym
    for _ in range(5):
        prev = [o for dd, o in REN.get(cur, []) if dd > d]
        if not prev:
            break
        cur = prev[0]
        out.insert(0, cur)
    return out


recs = []
for _, r in samp.iterrows():
    for rs in raw_candidates(r.symbol, r.day)[::-1][::-1]:
        x = pd.read_sql('select * from vopt where day=? and sym=?', my, params=(r.day, rs))
        if len(x):
            break
    f_ = pd.read_sql('select * from vfut where day=? and sym=? and expiry>=day', my, params=(r.day, rs))
    t_o = pd.read_sql('select * from opt where day=? and sym=?', th, params=(r.day, rs))
    t_f = pd.read_sql('select * from fut where day=? and sym=?', th, params=(r.day, rs))
    recs.append({'cand': r.c, 'symbol': r.symbol, 'raw': rs, 'day': r.day,
                 'my_fut_oi': f_.oi.sum() if len(f_) else np.nan, 'th_fut_oi': t_f.oi_tot.iloc[0] if len(t_f) else np.nan,
                 'my_pcr': (x.pe_oi / x.ce_oi).iloc[0] if len(x) else np.nan,
                 'th_pcr': (t_o.pe_oi / t_o.ce_oi).iloc[0] if len(t_o) else np.nan})
SM = pd.DataFrame(recs)
SM['oi_match'] = (SM.my_fut_oi - SM.th_fut_oi).abs() < 0.5
SM['pcr_match'] = (SM.my_pcr - SM.th_pcr).abs() < 1e-9
log(SM.round(4).to_string(index=False))
log(f'sample: fut OI match {int(SM.oi_match.sum())}/{len(SM)}, PCR match {int(SM.pcr_match.sum())}/{len(SM)}')
SM.to_csv(f'{OUT}/sample_raw_check.csv', index=False)
log('done')
