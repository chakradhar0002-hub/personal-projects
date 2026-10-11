#!/usr/bin/env python3
"""Verifier: compare the re-downloaded raw sample with the study's stored delivery table, its mapped panel and the
candidate-trade feature days. usage: python3 -P v02_check_data.py SCRATCH OUTDIR"""
import sys

import numpy as np
import pandas as pd

SP, OUT = sys.argv[1], sys.argv[2]
D = f'{SP}/more_signals/delivery'
raw = pd.read_csv(f'{OUT}/downloads/raw_sample_rows.csv', dtype={'symbol': str})
lg = pd.read_csv(f'{OUT}/downloads/raw_sample_log.csv')
eq = pd.read_csv(f'{D}/downloads/delivery_eq.csv', dtype={'symbol': str})
dp = pd.read_csv(f'{D}/delivery_panel.csv.gz', dtype={'symbol': str})
fr = pd.read_csv(f'{D}/feat_results.csv')
ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv')
days = ses.day.tolist()
out = open(f'{OUT}/v02_check_data.log', 'w')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    out.write(s + '\n')


sd = set(lg.day)
rq = raw[raw.series == 'EQ'].copy()
P(f'raw sample: {len(lg)} days, {len(raw)} universe rows (all series), EQ rows {len(rq)}')
# DATE1 check
bad = lg[(lg.full_rows > 0) & (pd.to_datetime(lg.date1, format='%d-%b-%Y').dt.strftime('%Y-%m-%d') != lg.day)]
P('days whose DATE1 differs from the requested day:', len(bad))

# 1. stored (unmapped) table vs raw
e = eq[eq.day.isin(sd)]
m = rq.merge(e, on=['day', 'symbol'], how='outer', suffixes=('_raw', '_st'), indicator=True)
P('\n1. raw EQ rows vs stored delivery_eq.csv on the sample days:', m._merge.value_counts().to_dict())
both = m[m._merge == 'both']
for c in ['ttl_trd_qnty', 'deliv_qty', 'deliv_per', 'close', 'prev_close']:
    a, b = both[c + '_raw'], both[c + '_st']
    ok = (np.isclose(a, b, rtol=0, atol=1e-6) | (a.isna() & b.isna()))
    P(f'   {c}: equal on {ok.sum()} / {len(both)}')
    if (~ok).any():
        P(both.loc[~ok, ['day', 'symbol', c + '_raw', c + '_st']].head(10).to_string())
if (m._merge != 'both').any():
    P(m.loc[m._merge != 'both', ['day', 'symbol', 'series_raw' if 'series_raw' in m else 'series', '_merge']].head(20).to_string())

# 2. non-EQ series of universe symbols on the sample days
ne = raw[(raw.series != 'EQ') & (raw.src == 'full')]
P(f'\n2. universe rows in non-EQ series on sample days: {len(ne)}; series counts {ne.series.value_counts().to_dict()}')
cur = set(pd.read_csv(f'{SP}/sector_lab/data/returns.csv', nrows=0).columns[1:])
neq = ne[ne.symbol.isin(cur) & ~ne.symbol.isin(set(rq.symbol))]
P('   current symbols present ONLY in a non-EQ series that day (would be a gap):')
P(neq[['day', 'symbol', 'series', 'ttl_trd_qnty', 'deliv_per']].to_string() if len(neq) else '   none')

# 3. ticker changes: raw old/new symbol on the change days, and the mapped panel row for the current symbol
P('\n3. ticker changes (raw file symbol -> mapped panel row of the current symbol)')
for d0, d1, old, new, curs in [('2020-12-17', '2020-12-18', 'INFRATEL', 'INDUSTOWER', 'INDUSTOWER'),
                               ('2022-12-02', '2022-12-05', 'LTI', 'LTIM', 'LTM'),
                               ('2025-04-08', '2025-04-09', 'ZOMATO', 'ETERNAL', 'ETERNAL'),
                               ('2025-10-23', '2025-10-24', 'TATAMOTORS', 'TMPV', 'TMPV'),
                               ('2026-02-26', '2026-02-27', 'LTIM', 'LTM', 'LTM')]:
    for d in (d0, d1):
        r = rq[(rq.day == d) & rq.symbol.isin([old, new])]
        p = dp[(dp.day == d) & (dp.symbol == curs)]
        rs = '; '.join(f'{a} {b:.0f}/{c:.0f}/{x:.2f}' for a, b, c, x in zip(r.symbol, r.ttl_trd_qnty, r.deliv_qty, r.deliv_per))
        ps = '; '.join(f'{a} {b:.0f}/{c:.0f}/{x:.2f}' for a, b, c, x in zip(p.symbol, p.ttl_trd_qnty, p.deliv_qty, p.deliv_per))
        P(f'   {d}: raw [{rs}]  panel [{ps}]')

# 4. MTO day
mt = raw[(raw.src == 'mto') & (raw.series == 'EQ')]
st = eq[eq.day == '2022-08-08']
mm = mt.merge(st, on=['day', 'symbol'], suffixes=('_raw', '_st'))
P(f'\n4. MTO day 2022-08-08: raw MTO EQ rows {len(mt)}, stored {len(st)}, matched {len(mm)}; '
  f'deliv_per equal {np.isclose(mm.deliv_per_raw, mm.deliv_per_st).sum()}, deliv_qty equal '
  f'{np.isclose(mm.deliv_qty_raw, mm.deliv_qty_st).sum()}, ttl equal {np.isclose(mm.ttl_trd_qnty_raw, mm.ttl_trd_qnty_st).sum()}')

# 5. candidate (symbol, decision-day) points on the sampled days
fr['day_e'] = [days[int(i)] for i in fr.e_A]
fr['day_k'] = [days[int(i)] for i in fr.i_react]
pts = []
for lab, df, dcol in [('A10', fr[fr.rank_DP60 > 80], 'day_e'),
                      ('RA1', fr[(fr.in_fo_events == True) & (fr.lag21 < -10) & (fr.DQR >= 1.0)], 'day_e'),
                      ('W_DQK_HI', fr[(fr.W == True) & (fr.DQK >= 3)], 'day_k'),
                      ('A06', fr[fr.rank_DPL > 80], 'day_e')]:
    for s, q, d in zip(df.symbol, df.qn, df[dcol]):
        if d in sd:
            pts.append((lab, s, q, d))
pt = pd.DataFrame(pts, columns=['cand', 'symbol', 'qn', 'day'])
# raw values: map the current symbol back to the raw ticker used that day
# reverse ticker map (own implementation): walk back through dated changes new <- old while the change date > day
scx = pd.read_csv(f'{SP}/symbolchange.csv', header=None, names=['co', 'old', 'new', 'date'], dtype=str)
for c in scx:
    scx[c] = scx[c].str.strip()
scx['d'] = pd.to_datetime(scx.date, format='%d-%b-%Y', errors='coerce').dt.strftime('%Y-%m-%d')
BACK = {}
for o, n, d in zip(scx.old, scx.new, scx.d):
    BACK.setdefault(n, []).append((d, o))
def raw_sym(s, d):
    for _ in range(10):
        c = [(dd, o) for dd, o in BACK.get(s, []) if isinstance(dd, str) and dd > d]
        if not c:
            return s
        s = min(c)[1]
    return s
pt['raw_symbol'] = [raw_sym(s, d) for s, d in zip(pt.symbol, pt.day)]
pt = pt.merge(rq[['day', 'symbol', 'deliv_per', 'deliv_qty', 'ttl_trd_qnty']].rename(columns={'symbol': 'raw_symbol'}),
              on=['day', 'raw_symbol'], how='left')
pt = pt.merge(dp[['day', 'symbol', 'deliv_per', 'deliv_qty', 'ttl_trd_qnty']], on=['day', 'symbol'], how='left',
              suffixes=('_raw', '_panel'))
for c in ['deliv_per', 'deliv_qty', 'ttl_trd_qnty']:
    pt[c + '_ok'] = np.isclose(pt[c + '_raw'], pt[c + '_panel'], rtol=1e-5, atol=1e-6)
pt['all_ok'] = pt[[c + '_ok' for c in ['deliv_per', 'deliv_qty', 'ttl_trd_qnty']]].all(axis=1)
pt.to_csv(f'{OUT}/v02_candidate_points.csv', index=False)
P(f'\n5. candidate (symbol, decision day) points on the sample days: {len(pt)}; by candidate {pt.cand.value_counts().to_dict()}')
P(f'   raw = mapped panel on deliv_per, deliv_qty and traded qty: {pt.all_ok.sum()} / {len(pt)}')
if (~pt.all_ok).any():
    P(pt[~pt.all_ok].to_string())
out.close()
