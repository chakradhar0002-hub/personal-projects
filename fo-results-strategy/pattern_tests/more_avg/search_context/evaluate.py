"""Discovery-only outcomes (qn 0..13) for the 28 context candidates. Holdout outcomes are never computed."""
import numpy as np
import pandas as pd

SP = __import__('os').environ.get('LAB_ROOT', 'lab')  # scratch data folder
OUT = SP + '/more_avg/search_context'
H = 20
DISC_MAX = 13

F = pd.read_csv(OUT + '/features.csv')
CP = pd.read_csv(OUT + '/cutpoints.csv').set_index('feature')
ses = pd.read_csv(SP + '/sector_lab/data/sessions.csv')
ret = pd.read_csv(SP + '/sector_lab/data/returns.csv', index_col=0)
idx = pd.read_csv(SP + '/sector_lab/data/index_close.csv', index_col=0)
R = ret.values
col = {s: j for j, s in enumerate(ret.columns)}
N = idx['Nifty 50'].values


def outcome(sym, k, qn):
    assert qn <= DISC_MAX, 'holdout outcome requested'
    j = col[sym]
    hold = np.nan_to_num(R[k + 1:k + H + 1, j], nan=0.0)
    stock = np.prod(1 + hold) - 1
    nif = N[k + H] / N[k] - 1
    return (stock - nif) * 100 - 0.19, stock * 100 - 0.17


def terc(c, x):
    t1, t2 = CP.loc[c, 't1'], CP.loc[c, 't2']
    return np.where(x.isna(), 'NA', np.where(x <= t1, 'L', np.where(x <= t2, 'M', 'H')))


for c in ['nifty_r20', 'vix', 'sec_r20', 'breadth_w', 'season_pos']:
    F[c + '_T'] = terc(c, F[c])
b = lambda s: s.astype(str).str.lower() == 'true'
for c in ['nifty_sma50_up', 'nifty_sma200_up', 'sec_sma50_up', 'fin', 'BASE']:
    F[c] = b(F[c])

CANDS = {
    'C01 nifty>SMA50': F.nifty_sma50_up,
    'C02 nifty<=SMA50': ~F.nifty_sma50_up,
    'C03 nifty>SMA200': F.nifty_sma200_up,
    'C04 nifty<=SMA200': ~F.nifty_sma200_up,
    'C05 nifty>SMA50&SMA200': F.nifty_sma50_up & F.nifty_sma200_up,
    'C06 nifty_r20 Low': F.nifty_r20_T == 'L',
    'C07 nifty_r20 Mid': F.nifty_r20_T == 'M',
    'C08 nifty_r20 High': F.nifty_r20_T == 'H',
    'C09 nifty_r20 not High': F.nifty_r20_T.isin(['L', 'M']),
    'C10 VIX Low': F.vix_T == 'L',
    'C11 VIX Mid': F.vix_T == 'M',
    'C12 VIX High': F.vix_T == 'H',
    'C13 sector>SMA50': F.sec_sma50_up,
    'C14 sector<=SMA50': ~F.sec_sma50_up,
    'C15 sec_r20>0': F.sec_r20 > 0,
    'C16 sec_r20<=0': F.sec_r20 <= 0,
    'C17 sec_r20 High': F.sec_r20_T == 'H',
    'C18 sec_r20 Low': F.sec_r20_T == 'L',
    'C19 sec_rel20>0': F.sec_rel20 > 0,
    'C20 breadth High': F.breadth_w_T == 'H',
    'C21 breadth Low': F.breadth_w_T == 'L',
    'C22 breadth not Low': F.breadth_w_T.isin(['M', 'H']),
    'C23 season early': F.season_pos_T == 'L',
    'C24 season mid': F.season_pos_T == 'M',
    'C25 season late': F.season_pos_T == 'H',
    'C26 financials': F.fin,
    'C27 companies': ~F.fin,
    'C28 nifty>SMA200&sector>SMA50': F.nifty_sma200_up & F.sec_sma50_up,
}
assert len(CANDS) == 28

# discovery outcomes for tradable baseline signals only
D = F[(F.qn <= DISC_MAX) & b(F.tradable) & F.BASE].copy()
o = [outcome(s, int(k), int(q)) for s, k, q in zip(D.symbol, D.i_react, D.qn)]
D['vsN_net'] = [x[0] for x in o]
D['raw_net'] = [x[1] for x in o]
D['year'] = D.reaction_day.str[:4]
D.to_csv(OUT + '/discovery_trades.csv', index=False, float_format='%.6f')


def stats(t):
    n = len(t)
    if n == 0:
        return dict(n=0)
    qm = t.groupby('qn').vsN_net.mean()
    wo5 = t.vsN_net.sort_values().iloc[:-5].mean() if n > 5 else np.nan
    s23 = t[t.year == '2023'].vsN_net.sum() / t.vsN_net.sum() * 100 if t.vsN_net.sum() > 0 else np.nan
    return dict(n=n, avg=t.vsN_net.mean(), wo5=wo5, median=t.vsN_net.median(), up_pct=100 * (t.vsN_net > 0).mean(),
                raw=t.raw_net.mean(), q_pos=int((qm > 0).sum()), q_with=len(qm), share2023=s23,
                t_q=qm.mean() / (qm.std(ddof=1) / np.sqrt(len(qm))) if len(qm) > 2 else np.nan)


base = stats(D)
rows = [dict(cand='B00 baseline', **base)]
for name, m in CANDS.items():
    t = D[m.loc[D.index].values]
    rows.append(dict(cand=name, **stats(t)))
T = pd.DataFrame(rows)
T['eligible'] = (T.n >= 35) & (T.q_with >= 7)
T['beats_base_wo5_by_0.5'] = T.wo5 >= base['wo5'] + 0.5
T.to_csv(OUT + '/discovery_table.csv', index=False, float_format='%.4f')
pd.set_option('display.width', 250)
print(T.to_string(index=False, float_format=lambda x: f'{x:+.2f}'))
print(f"\nbaseline discovery: n={base['n']} avg={base['avg']:+.3f} wo5={base['wo5']:+.3f}; threshold wo5 >= {base['wo5'] + 0.5:+.3f}")
E = T[(T.cand != 'B00 baseline') & T.eligible].sort_values('wo5', ascending=False)
print('\nEligible ranked by wo5:')
print(E[['cand', 'n', 'avg', 'wo5', 'q_pos', 'q_with', 'beats_base_wo5_by_0.5']].to_string(index=False))
fin = E[E['beats_base_wo5_by_0.5']].head(2)
print('\nFINALISTS:', list(fin.cand))
open(OUT + '/finalists.txt', 'w').write('\n'.join(fin.cand) + '\n')

# holdout signal COUNTS only (features, no outcomes, no tradability) for finalists
for name in fin.cand:
    m = CANDS[name]
    hs = F[(F.qn > DISC_MAX) & F.BASE & m]
    print(f'{name}: holdout signals (count only, untested) = {len(hs)} over {hs.qn.nunique()} quarters')

# markdown table
md = ['| cand | n | avg | w/o best 5 | median | up% | quarters +/with | 2023 share% | eligible |', '|---|---:|---:|---:|---:|---:|---:|---:|---|']
for r in T.itertuples(index=False):
    if r.n == 0:
        md.append(f'| {r.cand} | 0 | - | - | - | - | - | - | no |')
        continue
    md.append(f'| {r.cand} | {r.n} | {r.avg:+.2f} | {r.wo5:+.2f} | {r.median:+.2f} | {r.up_pct:.0f} | {r.q_pos}/{r.q_with} | '
              f'{r.share2023:.0f} | {"yes" if r.eligible else "no"} |')
open(OUT + '/discovery_table.md', 'w').write('\n'.join(md) + '\n')
