#!/usr/bin/env python3
"""Are good and bad results quarters related? Quarter-level checks on the three-day results sum, 22 seasons.

Universe: all 3,278 results of stocks in F&O at the time (events.csv in_fo == True), 206 stocks, 22 seasons
(qn 0 = results for Jan-Mar 2021 ... qn 21 = results for Apr-Jun 2026). three_day = ret_dm1 + ret_rd + ret_dp1 (sum
of the three daily returns, not compounded), in %. Sector = NSE index sector (nifty_sector) from
REPO_ROOT/results/nifty_sector_3day/results_3day.csv.

Quarter average Q_t = mean three-day sum of the quarter's results. Nifty part = Nifty 50 three-day sum on the same
three sessions as each result, averaged over the quarter's results (events.csv nifty_3d); stock part = Q_t - Nifty
part. Best / worst sector = highest / lowest sector average among sectors with at least MIN_N results that quarter
(same as nifty_sector_3day/quarter_leaders.csv, checked). Season market variables, with i0 = the season's first
cutoff session (min i_cut) and i1 = its last Day+1 session (max i_p1), rows of index_close.csv: Nifty 50 return over
the 20 and the 60 sessions before i0 (close i0 / close i0-k - 1), India VIX close at i0 and its change in points over
the 20 sessions before, Nifty 50 return from close i0 to close i1 (the whole season).

Tests. Permutation p values, two-sided = twice the smaller tail, each tail (1 + count) / (N + 1), capped at 1; the
seasonality test is upper-tail. Holm within each section's family:
  section 2, persistence: autocorrelation of Q at lags 1-4 (Pearson and Spearman, pairs (Q_t, Q_t+k)), runs above /
    below the median, average next-quarter Q after the 5 best minus after the 5 worst quarters (of the 21 quarters
    that have a next one); lag-1 Pearson, Spearman and next-quarter checks on the stock part.
    Null: 20,000 shuffles of the order of the 22 quarters.
  section 3, seasonality: between-period sum of squares of Q (and of the stock part) by results period
    (Jan-Mar / Apr-Jun / Jul-Sep / Oct-Dec results); null: 20,000 shuffles of the period labels.
  section 4, what good and bad quarters have in common: Pearson and Spearman correlation of Q and of the stock part
    with the market variables, the cross-sectional sd and the number of results; null: 20,000 shuffles of the 22
    values of Q (or of the stock part).
  section 5, best vs worst sector: correlations across the 22 quarters of the best and the worst sector average,
    their excess over Q_t, the best-minus-worst spread and Q_t, and the average spread; null: 2,000 within-quarter
    shuffles of the three-day sums across the sector labels (every sector-quarter cell keeps its size, Q_t is
    unchanged), best and worst recomputed in each shuffle.
Fixed seeds. Reads LAB_ROOT/sector_lab/data and REPO_ROOT/results/nifty_sector_3day; writes q_* files in OUT
(default REPO_ROOT/results/quarter_correlation).
"""
import os
import numpy as np
import pandas as pd
from scipy import stats

REPO = os.environ.get('REPO_ROOT', '.')
LAB = os.environ.get('LAB_ROOT', 'lab')
OUT = os.environ.get('OUT', os.path.join(REPO, 'results', 'quarter_correlation'))
NS = os.path.join(REPO, 'results', 'nifty_sector_3day')
os.makedirs(OUT, exist_ok=True)
D = f'{LAB}/sector_lab/data'
MIN_N = 4          # best / worst only among sectors with at least this many results that quarter
N_PERM = 20000     # shuffles for sections 2-4
N_SHUF = 2000      # within-quarter label shuffles for section 5
TOPK = 5           # best / worst quarters for the next-quarter check
SEED = 20261017
PERIODS = ['Jan-Mar', 'Apr-Jun', 'Jul-Sep', 'Oct-Dec']

SHORT = {'Financial Services': 'Fin services', 'Capital Goods': 'Cap goods', 'Automobile and Auto Components': 'Auto',
         'Healthcare': 'Healthcare', 'Information Technology': 'IT', 'Fast Moving Consumer Goods': 'FMCG',
         'Metals & Mining': 'Metals', 'Consumer Durables': 'Cons dur', 'Consumer Services': 'Cons services',
         'Oil Gas & Consumable Fuels': 'Oil & gas', 'Power': 'Power', 'Realty': 'Realty', 'Services': 'Services',
         'Chemicals': 'Chemicals', 'Construction Materials': 'Constr mat', 'Telecommunication': 'Telecom',
         'Construction': 'Construction', 'Textiles': 'Textiles'}

log = []
def P(*a):
    s = ' '.join(str(x) for x in a)
    log.append(s)
    print(s)

fpc = lambda v: f'{v:+.2f}'                        # percent / percentage points, signed
fr = lambda r: f'{r:+.2f}'                         # correlation
fp = lambda p: '<0.001' if p < 0.001 else f'{p:.3f}'

def holm(p):
    p = np.asarray(p, float)
    m, o = len(p), np.argsort(p, kind='stable')
    adj, run = np.empty(m), 0.0
    for i, j in enumerate(o):
        run = max(run, min(1.0, (m - i) * p[j]))
        adj[j] = run
    return adj

def p_two(obs, sims):
    """Two-sided permutation p: twice the smaller tail, each tail (1 + count) / (N + 1), capped at 1."""
    hi = (1 + (sims >= obs - 1e-12).sum()) / (len(sims) + 1)
    lo = (1 + (sims <= obs + 1e-12).sum()) / (len(sims) + 1)
    return min(1.0, 2 * min(hi, lo))

def p_upper(obs, sims):
    return (1 + (sims >= obs - 1e-12).sum()) / (len(sims) + 1)

def rowcorr(A, B):
    """Pearson correlation of matching rows of A and B (broadcast)."""
    A, B = np.broadcast_arrays(np.asarray(A, float), np.asarray(B, float))
    A = A - A.mean(axis=-1, keepdims=True)
    B = B - B.mean(axis=-1, keepdims=True)
    return (A * B).sum(-1) / np.sqrt((A * A).sum(-1) * (B * B).sum(-1))

def ranks_rows(A):
    """Ranks along each row (data without ties)."""
    return A.argsort(axis=1).argsort(axis=1).astype(float)

def show(df, pct=(), r=(), pv=(), dec2=(), dec0=()):
    """Copy of df formatted for the log: signed 2-decimal percents / correlations, 3-decimal p values."""
    d = df.copy()
    for c in d.columns:
        if c in pct:
            d[c] = d[c].map(fpc)
        elif c in r:
            d[c] = d[c].map(fr)
        elif c in pv:
            d[c] = d[c].map(fp)
        elif c in dec2:
            d[c] = d[c].map(lambda v: f'{v:.2f}')
        elif c in dec0:
            d[c] = d[c].map(lambda v: f'{v:.0f}')
    return d

PCT_Q = ('avg', 'median', 'nifty_part', 'stock_part', 'best_avg', 'worst_avg', 'spread', 'best_excess', 'worst_excess',
         'nifty_pre20', 'nifty_pre60', 'vix_chg20', 'nifty_season', 'mean_Q', 'median_Q', 'min_Q', 'max_Q')

def pearson(x, y):
    return float(np.corrcoef(x, y)[0, 1])

def spearman(x, y):
    return float(stats.spearmanr(x, y)[0])

P('== quarter_level.py ==')
# ---------------------------------------------------------------- data and checks
ev = pd.read_csv(f'{D}/events.csv')
ev = ev[ev.in_fo == True].copy()
assert len(ev) == 3278 and ev.symbol.nunique() == 206, (len(ev), ev.symbol.nunique())
sec = pd.read_csv(f'{NS}/results_3day.csv')
assert len(sec) == 3278 and not sec.duplicated(['symbol', 'qn']).any()
ev = ev.merge(sec[['symbol', 'qn', 'nifty_sector', 'three_day']].rename(columns={'three_day': 'td_ns'}),
              on=['symbol', 'qn'], how='left', validate='1:1')
assert ev.nifty_sector.notna().all() and len(ev) == 3278
assert set(ev.nifty_sector) <= set(SHORT)
assert ev.three_day.notna().all() and ev.nifty_3d.notna().all()
assert np.allclose(ev.three_day, ev.ret_dm1 + ev.ret_rd + ev.ret_dp1, rtol=0, atol=1e-12)
assert np.allclose(ev.three_day, ev.td_ns, rtol=0, atol=1e-9), np.abs(ev.three_day - ev.td_ns).max()
assert ((ev.i_m1 - ev.i_cut == 1) & (ev.i_rd - ev.i_m1 == 1) & (ev.i_p1 - ev.i_rd == 1)).all()

ses = pd.read_csv(f'{D}/sessions.csv')
ic = pd.read_csv(f'{D}/index_close.csv', index_col=0)
assert (ses.i.to_numpy() == np.arange(len(ses))).all() and (ic.index.to_numpy() == ses.day.to_numpy()).all()
C = ic['Nifty 50'].to_numpy(float)
V = ic['India VIX'].to_numpy(float)
nret = np.r_[np.nan, C[1:] / C[:-1] - 1]
chk = nret[ev.i_m1] + nret[ev.i_rd] + nret[ev.i_p1]
d_n = np.abs(chk - ev.nifty_3d.to_numpy()).max()
assert d_n < 1e-9, d_n
P(f'F&O results {len(ev)}, stocks {ev.symbol.nunique()}, quarters {ev.qn.nunique()}; sector labels and three_day match '
  f'nifty_sector_3day/results_3day.csv; nifty_3d matches Nifty 50 closes (max abs diff {d_n:.1e})')
ev['td'] = ev.three_day * 100
ev['n3'] = ev.nifty_3d * 100

# ---------------------------------------------------------------- 1. quarter table
rows = []
for qn, g in ev.groupby('qn'):
    s = g.groupby('nifty_sector').td.agg(['mean', 'size'])
    big = s[s['size'] >= MIN_N]
    best, worst = big['mean'].idxmax(), big['mean'].idxmin()
    i0, i1 = int(g.i_cut.min()), int(g.i_p1.max())
    assert np.isfinite(C[[i0 - 60, i0 - 20, i0, i1]]).all() and np.isfinite(V[[i0 - 20, i0]]).all()
    Q, npart = g.td.mean(), g.n3.mean()
    rows.append(dict(qn=qn, period=g.period.iloc[0], quarter=g.quarter.iloc[0], results=len(g),
                     first_cutoff=ses.day[i0], last_day_p1=ses.day[i1], season_sessions=i1 - i0,
                     avg=Q, median=g.td.median(), up_pct=(g.td > 0).mean() * 100,
                     nifty_part=npart, stock_part=Q - npart, sd=g.td.std(ddof=1),
                     best=best, best_avg=big.loc[best, 'mean'], best_n=int(big.loc[best, 'size']),
                     worst=worst, worst_avg=big.loc[worst, 'mean'], worst_n=int(big.loc[worst, 'size']),
                     spread=big.loc[best, 'mean'] - big.loc[worst, 'mean'], ranked=len(big),
                     nifty_pre20=(C[i0] / C[i0 - 20] - 1) * 100, nifty_pre60=(C[i0] / C[i0 - 60] - 1) * 100,
                     vix=V[i0], vix_chg20=V[i0] - V[i0 - 20], nifty_season=(C[i1] / C[i0] - 1) * 100))
q = pd.DataFrame(rows)
assert list(q.qn) == list(range(22)) and q.results.sum() == 3278
q['best_excess'] = q.best_avg - q.avg
q['worst_excess'] = q.worst_avg - q.avg
lead = pd.read_csv(f'{NS}/quarter_leaders.csv')
assert (lead.best.to_numpy() == q.best.to_numpy()).all() and (lead.worst.to_numpy() == q.worst.to_numpy()).all()
assert np.allclose(lead.best_avg, q.best_avg.round(3), atol=1e-9) and np.allclose(lead.worst_avg, q.worst_avg.round(3), atol=1e-9)
assert np.allclose(lead.avg, q.avg.round(3), atol=1e-9) and (lead.results.to_numpy() == q.results.to_numpy()).all()
P(f'best / worst sector per quarter match nifty_sector_3day/quarter_leaders.csv (22 of 22)')
P('\nper quarter (%; vix in index points):')
P(show(q.drop(columns=['best', 'worst']).assign(best=q.best.map(SHORT), worst=q.worst.map(SHORT)), pct=PCT_Q,
       dec2=('sd', 'vix'), dec0=('up_pct',)).to_string(index=False))
Qv, Sv, Nv = q.avg.to_numpy(), q.stock_part.to_numpy(), q.nifty_part.to_numpy()
n = len(Qv)
P(f'\nQ over 22 quarters: mean {Qv.mean():+.2f}, sd {Qv.std(ddof=1):.2f}, min {Qv.min():+.2f} ({q.period[Qv.argmin()]}), '
  f'max {Qv.max():+.2f} ({q.period[Qv.argmax()]}), quarters with Q > 0: {(Qv > 0).sum()} of 22')
P(f'Nifty part: mean {Nv.mean():+.2f}, sd {Nv.std(ddof=1):.2f}; stock part: mean {Sv.mean():+.2f}, sd {Sv.std(ddof=1):.2f}')

tests = []
def add(section, test, stat, value, nn, p, question, null_txt, null_mean=np.nan, sign=1):
    """sign: +1 if the question's 'yes' is a value above the null mean, -1 if below, 0 if either."""
    tests.append(dict(section=section, test=test, statistic=stat, value=value, n=nn, p=p, null_mean=null_mean,
                      question=question, null_txt=null_txt, sign=sign))

# ---------------------------------------------------------------- 2. persistence
P('\n== 2. persistence of good and bad quarters ==')
P(f'null: {N_PERM:,} shuffles of the order of the 22 quarters, seed {SEED}; two-sided p = twice the smaller tail')
rng = np.random.default_rng(SEED)
perm = np.argsort(rng.random((N_PERM, n)), axis=1)
NULL2 = 'a random order of the 22 quarters'

def lag_sims(X, k, sp):
    A, B = X[:, :-k], X[:, k:]
    if sp:
        A, B = ranks_rows(A), ranks_rows(B)
    return rowcorr(A, B)

def follow(X):
    """Average next-quarter value after the TOPK best minus after the TOPK worst of the quarters with a next one."""
    o = X[:, :-1].argsort(axis=1)
    nxt = X[:, 1:]
    b = np.take_along_axis(nxt, o[:, -TOPK:], 1).mean(1)
    w = np.take_along_axis(nxt, o[:, :TOPK], 1).mean(1)
    return b - w, b, w

QP, SP = Qv[perm], Sv[perm]
acf_rows = []
for k in (1, 2, 3, 4):
    for meth, sp in (('Pearson', False), ('Spearman', True)):
        obs = (spearman if sp else pearson)(Qv[:-k], Qv[k:])
        sims = lag_sims(QP, k, sp)
        assert np.isclose(lag_sims(Qv[None, :], k, sp)[0], obs)
        p = p_two(obs, sims)
        acf_rows.append(dict(lag=k, method=meth, r=obs, pairs=n - k, null_mean=sims.mean(), p=p))
        add(2, f'Autocorrelation of Q, lag {k}, {meth}', 'r', obs, n - k, p,
            f'Is a good quarter followed by a good one {k} quarter{"s" if k > 1 else ""} later?', NULL2, sims.mean())
acf = pd.DataFrame(acf_rows)
P(show(acf, r=('r', 'null_mean'), pv=('p',)).to_string(index=False))
P(f'classic ACF of Q (overall mean, total variance), lags 1-4: '
  + ', '.join(f'{(np.sum((Qv[:-k] - Qv.mean()) * (Qv[k:] - Qv.mean())) / np.sum((Qv - Qv.mean()) ** 2)):+.2f}'
              for k in (1, 2, 3, 4)) + ' (descriptive)')

med = np.median(Qv)
assert not np.isclose(Qv, med).any()
above = Qv > med
runs_obs = int(1 + (above[1:] != above[:-1]).sum())
ab = QP > med
runs_sim = 1 + (ab[:, 1:] != ab[:, :-1]).sum(1)
n1, n2 = int(above.sum()), int((~above).sum())
e_runs = 1 + 2 * n1 * n2 / (n1 + n2)
p_runs = p_two(runs_obs, runs_sim)
seq = ''.join('+' if a else '-' for a in above)
P(f'\nruns test: median of Q {med:+.2f}; sequence above (+) / below (-) the median: {seq}')
P(f'runs {runs_obs} (expected {e_runs:.0f} for {n1} above / {n2} below; null mean {runs_sim.mean():.2f}), '
  f'p {fp(p_runs)}; fewer runs than expected would mean good and bad quarters come in streaks')
trans = pd.crosstab(pd.Series(np.where(above[:-1], 'above', 'below'), name='this quarter'),
                    pd.Series(np.where(above[1:], 'above', 'below'), name='next quarter'))
P('transitions (21 pairs):\n' + trans.to_string())
add(2, 'Runs of Q above / below its median', 'runs', runs_obs, n, p_runs,
    'Do good and bad quarters come in streaks (fewer runs than expected)?', NULL2, runs_sim.mean(), sign=-1)

f_obs, fb, fw = (v[0] for v in follow(Qv[None, :]))
f_sims = follow(QP)[0]
p_f = p_two(f_obs, f_sims)
o = np.argsort(Qv[:-1])
best5, worst5 = o[-TOPK:][::-1], o[:TOPK]
P(f'\nnext quarter after the {TOPK} best quarters (of the 21 with a next one; Q of the last quarter, '
  f'{q.period[21]}, is {Qv[21]:+.2f} and has no next one):')
for t in best5:
    P(f'  {q.period[t]} Q {Qv[t]:+.2f} -> {q.period[t + 1]} Q {Qv[t + 1]:+.2f}')
P(f'next quarter after the {TOPK} worst quarters:')
for t in worst5:
    P(f'  {q.period[t]} Q {Qv[t]:+.2f} -> {q.period[t + 1]} Q {Qv[t + 1]:+.2f}')
P(f'average next Q after best {TOPK}: {fb:+.2f}; after worst {TOPK}: {fw:+.2f}; difference {f_obs:+.2f} '
  f'(null mean {f_sims.mean():+.2f}), p {fp(p_f)}')
add(2, f'Next-quarter Q after the {TOPK} best minus after the {TOPK} worst quarters', 'difference (pp)', f_obs, 21, p_f,
    f'Is the quarter after a top-{TOPK} quarter better than the one after a bottom-{TOPK} quarter '
    f'({fpc(fb)}% vs {fpc(fw)}%)?', NULL2, f_sims.mean())

P('\nstock part (Q minus Nifty part), lag 1:')
for meth, sp in (('Pearson', False), ('Spearman', True)):
    obs = (spearman if sp else pearson)(Sv[:-1], Sv[1:])
    sims = lag_sims(SP, 1, sp)
    p = p_two(obs, sims)
    P(f'  lag 1 {meth}: r {fr(obs)}, pairs 21, null mean {sims.mean():+.3f}, p {fp(p)}')
    add(2, f'Autocorrelation of the stock part, lag 1, {meth}', 'r', obs, n - 1, p,
        'Is a quarter whose results beat Nifty followed by another that beats Nifty?', NULL2, sims.mean())
sf_obs, sfb, sfw = (v[0] for v in follow(Sv[None, :]))
sf_sims = follow(SP)[0]
p_sf = p_two(sf_obs, sf_sims)
P(f'  next stock part after the {TOPK} best stock-part quarters {sfb:+.2f}, after the {TOPK} worst {sfw:+.2f}, '
  f'difference {sf_obs:+.2f} (null mean {sf_sims.mean():+.2f}), p {fp(p_sf)}')
add(2, f'Next-quarter stock part after the {TOPK} best minus the {TOPK} worst stock-part quarters', 'difference (pp)',
    sf_obs, 21, p_sf, f'Is the stock part higher after the top-{TOPK} stock-part quarters than after the bottom '
    f'{TOPK} ({fpc(sfb)} vs {fpc(sfw)})?', NULL2, sf_sims.mean())
P(f'descriptive, Nifty part lag-1 Pearson r {fr(pearson(Nv[:-1], Nv[1:]))} (not tested)')

# ---------------------------------------------------------------- 3. seasonality
P('\n== 3. seasonality by results period ==')
rng3 = np.random.default_rng(SEED + 3)
perm3 = np.argsort(rng3.random((N_PERM, n)), axis=1)
q['pgroup'] = q.period.str[:7]
assert set(q.pgroup) == set(PERIODS)
G = (q.pgroup.to_numpy()[:, None] == np.array(PERIODS)[None, :]).astype(float)
cnt_g = G.sum(0)

def between_ss(X):
    X = np.atleast_2d(X)
    means = (X @ G) / cnt_g
    return (cnt_g * (means - X.mean(1, keepdims=True)) ** 2).sum(1)

seas = q.groupby('pgroup').agg(quarters=('avg', 'size'), results=('results', 'sum'), mean_Q=('avg', 'mean'),
                               median_Q=('avg', 'median'), q_pos=('avg', lambda v: int((v > 0).sum())),
                               nifty_part=('nifty_part', 'mean'), stock_part=('stock_part', 'mean'),
                               min_Q=('avg', 'min'), max_Q=('avg', 'max')).reindex(PERIODS)
P(show(seas, pct=PCT_Q).to_string())
seas_p = {}
for col, lab in (('avg', 'Q'), ('stock_part', 'stock part')):
    x = q[col].to_numpy()
    obs = between_ss(x)[0]
    sims = between_ss(x[perm3])
    eta = obs / ((x - x.mean()) ** 2).sum()
    p = p_upper(obs, sims)
    seas_p[col] = (eta, p)
    gm = (x @ G) / cnt_g
    P(f'{lab}: between-period sum of squares {obs:.3f}, share of variance (eta^2) {eta:.2f}, null mean eta^2 '
      f'{(sims / ((x - x.mean()) ** 2).sum()).mean():.2f}, upper-tail p {fp(p)}')
    add(3, f'Seasonality of {lab} by results period (4 periods)', 'eta^2', eta, n, p,
        f'Do the results periods differ (means ' + ', '.join(f'{pp} {fpc(m)}' for pp, m in zip(PERIODS, gm)) + ')?',
        'random period labels', (sims / ((x - x.mean()) ** 2).sum()).mean())

# ---------------------------------------------------------------- 4. what good and bad quarters share
P('\n== 4. what good and bad quarters have in common ==')
rng4 = np.random.default_rng(SEED + 4)
perm4 = np.argsort(rng4.random((N_PERM, n)), axis=1)
VARS = [('nifty_part', '(a) Nifty 50 three-day sum on the same sessions'),
        ('nifty_pre20', '(b) Nifty 50 return, 20 sessions before the first cutoff'),
        ('nifty_pre60', '(b) Nifty 50 return, 60 sessions before the first cutoff'),
        ('vix', '(c) India VIX at the first cutoff'),
        ('vix_chg20', '(c) India VIX change, 20 sessions before the first cutoff'),
        ('nifty_season', '(d) Nifty 50 return over the season'),
        ('sd', '(e) cross-sectional sd of the three-day sums'),
        ('results', '(f) number of results in the quarter')]
corr_rows = []
for tcol, tlab in (('avg', 'Q'), ('stock_part', 'stock part')):
    y = q[tcol].to_numpy()
    ry = stats.rankdata(y)
    for vcol, vlab in VARS:
        x = q[vcol].to_numpy(float)
        rx = stats.rankdata(x)
        for meth in ('Pearson', 'Spearman'):
            if meth == 'Pearson':
                obs, sims = pearson(x, y), rowcorr(x[None, :], y[perm4])
            else:
                obs, sims = spearman(x, y), rowcorr(rx[None, :], ry[perm4])
                assert np.isclose(obs, pearson(rx, ry))
            p = p_two(obs, sims)
            corr_rows.append(dict(target=tlab, variable=vlab, method=meth, r=obs, n=n, null_mean=sims.mean(), p=p))
            word = {'Q': 'Q (all-results average)', 'stock part': 'stock part (Q minus Nifty part)'}[tlab]
            add(4, f'{word} vs {vlab}, {meth}', 'r', obs, n, p,
                f'Is {"Q" if tlab == "Q" else "the stock part"} higher when the {vlab[4:]} is higher?',
                'random pairing of the 22 values', sims.mean())
cr = pd.DataFrame(corr_rows)
P(show(cr, r=('r', 'null_mean'), pv=('p',)).to_string(index=False))
r_a = pearson(Nv, Qv)
slope, icpt = np.polyfit(Nv, Qv, 1)
resid = Qv - (icpt + slope * Nv)
cov = np.cov(Nv, Sv, ddof=1)
vq = Qv.var(ddof=1)
P(f'\nR^2 of Q on (a) the Nifty part alone: {r_a ** 2:.2f} (r {fr(r_a)}); Q = {icpt:+.2f} + {slope:.2f} x Nifty part; '
  f'residual sd {resid.std(ddof=2):.2f} vs sd of Q {Qv.std(ddof=1):.2f}')
P(f'variance of Q {vq:.3f} = Nifty part {cov[0, 0]:.3f} ({cov[0, 0] / vq * 100:.0f}%) + stock part {cov[1, 1]:.3f} '
  f'({cov[1, 1] / vq * 100:.0f}%) + 2 x covariance {2 * cov[0, 1]:+.3f} ({2 * cov[0, 1] / vq * 100:+.0f}%)')
mk = q[[c for c, _ in VARS] + ['avg', 'stock_part']].corr()
P('Pearson correlations among the quarter variables (descriptive):\n' + mk.map(fr).to_string())

# ---------------------------------------------------------------- 5. best vs worst sector
P('\n== 5. best vs worst sector ==')
P(f'null: {N_SHUF:,} within-quarter shuffles of the three-day sums across the sector labels (cell sizes kept, '
  f'Q unchanged), best / worst recomputed among sectors with >= {MIN_N} results; seed {SEED + 5}')
rng5 = np.random.default_rng(SEED + 5)
best_sim, worst_sim = np.zeros((N_SHUF, n)), np.zeros((N_SHUF, n))
for t, (qn, g) in enumerate(ev.groupby('qn')):
    codes, uniq = pd.factorize(g.nifty_sector)
    cnts = np.bincount(codes)
    elig = cnts >= MIN_N
    OH = np.zeros((len(g), len(uniq)))
    OH[np.arange(len(g)), codes] = 1.0
    td = g.td.to_numpy()
    m0 = (td @ OH) / cnts
    assert np.isclose(m0[elig].max(), q.best_avg[t]) and np.isclose(m0[elig].min(), q.worst_avg[t])
    pm = np.argsort(rng5.random((N_SHUF, len(td))), axis=1)
    means = (td[pm] @ OH)[:, elig] / cnts[elig]
    best_sim[:, t], worst_sim[:, t] = means.max(1), means.min(1)
q['best_null_mean'], q['worst_null_mean'] = best_sim.mean(0), worst_sim.mean(0)
q['spread_null_mean'] = (best_sim - worst_sim).mean(0)
B, W = q.best_avg.to_numpy(), q.worst_avg.to_numpy()
NULL5 = 'random sector labels within each quarter'
S5 = [('Best sector avg vs worst sector avg', 'r', pearson(B, W), rowcorr(best_sim, worst_sim),
       'Do the best and the worst sector rise and fall together beyond the mechanical link?', 1),
      ('Best sector excess vs worst sector excess (both minus Q)', 'r', pearson(B - Qv, W - Qv),
       rowcorr(best_sim - Qv, worst_sim - Qv), 'Are the best sector\'s lead and the worst sector\'s gap linked?', 0),
      ('Q vs best-minus-worst spread', 'r', pearson(Qv, B - W), rowcorr(Qv[None, :], best_sim - worst_sim),
       'Do good quarters have a wider best-worst spread than chance gives?', 1),
      ('Q vs best sector avg', 'r', pearson(Qv, B), rowcorr(Qv[None, :], best_sim),
       'Does the best sector follow Q more closely than chance gives?', 1),
      ('Q vs worst sector avg', 'r', pearson(Qv, W), rowcorr(Qv[None, :], worst_sim),
       'Does the worst sector follow Q more closely than chance gives?', 1),
      ('Average best-minus-worst spread over 22 quarters', 'spread (pp)', (B - W).mean(), (best_sim - worst_sim).mean(1),
       'Is the gap between best and worst sector wider than random sector labels give?', 1)]
s5_rows = []
for name, stat, obs, sims, question, sign in S5:
    p = p_two(obs, sims)
    lo, hi = np.percentile(sims, [2.5, 97.5])
    s5_rows.append(dict(test=name, observed=obs, null_mean=sims.mean(), null_lo=lo, null_hi=hi, p=p))
    add(5, name, stat, obs, n, p, question, NULL5, sims.mean(), sign=sign)
s5 = pd.DataFrame(s5_rows)
s5_show = s5.copy()
for c in ('observed', 'null_mean', 'null_lo', 'null_hi'):
    s5_show[c] = [fpc(v) for v in s5[c]]       # correlations and the spread (pp), all signed 2 decimals
P(show(s5_show, pv=('p',)).to_string(index=False))
P(f'\naverage over the 22 quarters: best sector {B.mean():+.2f} (null {best_sim.mean():+.2f}), worst sector '
  f'{W.mean():+.2f} (null {worst_sim.mean():+.2f}), Q {Qv.mean():+.2f}')
P(f'best sector excess over Q: avg {(B - Qv).mean():+.2f}; worst: {(W - Qv).mean():+.2f}')
P(f'Spearman, descriptive: best vs worst {fr(spearman(B, W))}, best excess vs worst excess {fr(spearman(B - Qv, W - Qv))}, '
  f'Q vs spread {fr(spearman(Qv, B - W))}')

# ---------------------------------------------------------------- Holm, test table
T = pd.DataFrame(tests)
T['holm'] = np.nan
for s_, idx in T.groupby('section').groups.items():
    T.loc[idx, 'holm'] = holm(T.loc[idx, 'p'].to_numpy())

def answer(r):
    up = r.value > r.null_mean
    if r.holm < 0.05:
        if r.sign == 0:
            return f'Yes ({"above" if up else "below"} chance), holds after Holm.'
        return ('Yes' if (up == (r.sign > 0)) else 'The reverse') + ', holds after Holm.'
    if r.p < 0.05:
        return 'Only a hint: p < 0.05 before Holm, not after.'
    return f'No: within what {r.null_txt} gives.'
T['meaning'] = [f'{r.question} {answer(r)}' for _, r in T.iterrows()]
FAM = {2: f'Section 2, persistence of good and bad quarters',
       3: 'Section 3, seasonality by results period',
       4: 'Section 4, what good and bad quarters have in common',
       5: 'Section 5, best vs worst sector'}
NULLDOC = {2: f'{N_PERM:,} shuffles of the order of the 22 quarters; two-sided (twice the smaller tail).',
           3: f'{N_PERM:,} shuffles of the period labels across the 22 quarters; upper tail (between-period sum of '
              'squares, reported as eta^2 = its share of the total).',
           4: f'{N_PERM:,} shuffles of the 22 values of Q (or of the stock part) against the variable; two-sided.',
           5: f'{N_SHUF:,} within-quarter shuffles of the three-day sums across the NSE sector labels (every '
              f'sector-quarter cell keeps its size, Q unchanged), best / worst recomputed among sectors with at '
              f'least {MIN_N} results; two-sided (twice the smaller tail of the shuffled values, which are not '
              'centred on 0).'}

def fstat(r):
    if r.statistic == 'r':
        s = f'r = {fr(r.value)}'
    elif r.statistic == 'runs':
        s = f'runs = {int(r.value)} (expected {e_runs:.0f})'
    elif r.statistic == 'eta^2':
        s = f'eta^2 = {r.value:.2f}'
    else:
        s = f'{fpc(r.value)} pp'
    if r.section in (2, 5) and np.isfinite(r.null_mean) and r.statistic != 'runs':
        s += f' (null {fr(r.null_mean) if r.statistic == "r" else fpc(r.null_mean)})'
    if r.section == 3:
        s += f' (null {r.null_mean:.2f})'
    return s

md = ['# Quarter-level tests', '', 'Every test of quarter_level.py. p: permutation p; Holm p: Holm adjustment within '
      'the section (the family named in the heading). n: quarters (or quarter pairs) used. Null in brackets: the '
      'average of the statistic over the shuffles.', '']
for s_ in (2, 3, 4, 5):
    t = T[T.section == s_]
    md += [f'## {FAM[s_]} (family: {len(t)} tests)', '', 'Null: ' + NULLDOC[s_], '',
           '| Test | Statistic | n | p | Holm p | Meaning |', '|---|---|---:|---:|---:|---|']
    for _, r in t.iterrows():
        md.append(f'| {r.test} | {fstat(r)} | {r.n} | {fp(r.p)} | {fp(r.holm)} | {r.meaning} |')
    md.append('')
    if s_ == 2:
        md += [f'Runs: the 22 quarters in order, above (+) or below (-) the median Q ({fpc(med)}%): `{seq}`. '
               f'Next-quarter check: of the 21 quarters that have a next one, the {TOPK} best and the {TOPK} worst; '
               f'Q of the last quarter ({q.period[21]}, {fpc(Qv[21])}%) is mid-table, so leaving it out changes no '
               'pick.', '',
               'For comparison, stock level (docs/PAST_PERFORMANCE.md, trade A, same three-day window): stocks whose '
               'last 4 results windows averaged in the top tenth of the quarter made +1.07% over 292 trades against '
               '+0.04% for all F&O results (after-the-fact pick, expect about half). A stock\'s own results-window '
               'record carries a little; this section asks the same of the whole quarter.', '']
    if s_ == 4:
        md += [f'R^2 of Q on (a), the Nifty 50 three-day sum on the same sessions, alone: {r_a ** 2:.2f} '
               f'(Q = {fpc(icpt)} + {slope:.2f} x Nifty part). Variance of Q: Nifty part {cov[0, 0] / vq * 100:.0f}%, '
               f'stock part {cov[1, 1] / vq * 100:.0f}%, twice their covariance {2 * cov[0, 1] / vq * 100:+.0f}%. '
               'Q = Nifty part + stock part by construction, so Q vs (a) is partly mechanical; the stock-part rows '
               'say whether the excess over Nifty also moves with the market. (f) number of results rises over time '
               '(98 to 206), so it is close to a time trend.', '']
open(f'{OUT}/q_table_tests.md', 'w').write('\n'.join(md))
T.drop(columns=['question', 'null_txt', 'sign']).round(4).to_csv(f'{OUT}/q_tests.csv', index=False)
P('\n== all tests, Holm within each section ==')
with pd.option_context('display.max_colwidth', 200, 'display.width', 250):
    P(show(T[['section', 'test', 'value', 'n', 'null_mean', 'p', 'holm']], pv=('p', 'holm'),
           r=('value', 'null_mean')).to_string(index=False))
for s_ in (2, 3, 4, 5):
    t = T[T.section == s_]
    P(f'section {s_} ({len(t)} tests): p < 0.05 before Holm: {int((t.p < 0.05).sum())}; after Holm: '
      f'{int((t.holm < 0.05).sum())}' + ('' if not (t.holm < 0.05).any() else ' -> ' + '; '.join(t[t.holm < 0.05].test)))

# ---------------------------------------------------------------- quarter csv and markdown
qcols = ['qn', 'period', 'quarter', 'results', 'first_cutoff', 'last_day_p1', 'season_sessions', 'avg', 'median',
         'up_pct', 'nifty_part', 'stock_part', 'sd', 'best', 'best_avg', 'best_n', 'worst', 'worst_avg', 'worst_n',
         'spread', 'ranked', 'best_excess', 'worst_excess', 'best_null_mean', 'worst_null_mean', 'spread_null_mean',
         'nifty_pre20', 'nifty_pre60', 'vix', 'vix_chg20', 'nifty_season']
q[qcols].round(3).to_csv(f'{OUT}/q_quarters.csv', index=False)
out = ['# Results quarters: average three-day sum, market part and best / worst sector', '',
       '| Results for | Quarter | Results | Avg (Q) | Median | Up | Nifty part | Stock part | Sd | Best sector | '
       'Worst sector | Best - worst |',
       '|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---:|']
for _, r in q.iterrows():
    out.append(f'| {r.period} | {r.quarter} | {r.results} | {fpc(r.avg)}% | {fpc(r["median"])}% | {r.up_pct:.0f}% | '
               f'{fpc(r.nifty_part)}% | {fpc(r.stock_part)} | {r.sd:.2f} | {SHORT[r.best]} {fpc(r.best_avg)}% ({r.best_n}) | '
               f'{SHORT[r.worst]} {fpc(r.worst_avg)}% ({r.worst_n}) | {fpc(r.spread)} |')
out.append(f'| All 22 quarters | | {q.results.sum():,} | {fpc(Qv.mean())}% | '
           f'{fpc(q["median"].mean())}% | {q.up_pct.mean():.0f}% | {fpc(Nv.mean())}% | {fpc(Sv.mean())} | '
           f'{q.sd.mean():.2f} | {fpc(B.mean())}% | {fpc(W.mean())}% | {fpc((B - W).mean())} |')
out += ['', 'Avg (Q): average three-day sum (Day-1 + Result day + Day+1 daily returns, summed) of all F&O results of the '
        'quarter. Up: share of results with a positive sum. Nifty part: Nifty 50 three-day sum on the same three '
        'sessions as each result, averaged over the quarter\'s results. Stock part: Q minus the Nifty part, in '
        'percentage points. Sd: cross-sectional standard deviation of the three-day sums. Best / worst sector: highest '
        f'/ lowest NSE index sector average among sectors with at least {MIN_N} results that quarter (number of results '
        'in brackets), as in docs/NIFTY_SECTOR_3DAY.md. Best - worst: their difference, percentage points. All 22 '
        'quarters: total results; every other column is the average of the 22 quarter values.', '',
        '## Market around each season', '',
        '| Results for | Quarter | First cutoff | Last Day+1 | Nifty 20 sessions before | Nifty 60 sessions before | '
        'VIX at first cutoff | VIX change, 20 sessions | Nifty over the season |',
        '|---|---|---|---|---:|---:|---:|---:|---:|']
for _, r in q.iterrows():
    out.append(f'| {r.period} | {r.quarter} | {r.first_cutoff} | {r.last_day_p1} | {fpc(r.nifty_pre20)}% | '
               f'{fpc(r.nifty_pre60)}% | {r.vix:.2f} | {fpc(r.vix_chg20)} | {fpc(r.nifty_season)}% |')
out += ['', 'First cutoff: the season\'s earliest cutoff session (2 sessions before the result session; the three-day '
        'window starts at its close). Last Day+1: the season\'s latest Day+1 session. Nifty k sessions before: Nifty 50 '
        'close at the first cutoff over its close k sessions earlier, minus 1. VIX: India VIX close at the first cutoff '
        '(index points) and its change in points over the 20 sessions before. Nifty over the season: first cutoff close '
        'to last Day+1 close.', '',
        '## Q by results period', '',
        '| Results for | Quarters | Results | Mean Q | Median Q | Quarters with Q > 0 | Nifty part | Stock part | Lowest / highest Q |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---|']
for pp, r in seas.iterrows():
    out.append(f'| {pp} | {int(r.quarters)} | {int(r.results):,} | {fpc(r.mean_Q)}% | {fpc(r.median_Q)}% | '
               f'{int(r.q_pos)} of {int(r.quarters)} | '
               f'{fpc(r.nifty_part)}% | {fpc(r.stock_part)} | {fpc(r.min_Q)}% / {fpc(r.max_Q)}% |')
out += ['', f'Between-period share of the variance of Q: eta^2 {seas_p["avg"][0]:.2f}, permutation p '
        f'{fp(seas_p["avg"][1])}; of the stock part: {seas_p["stock_part"][0]:.2f}, p {fp(seas_p["stock_part"][1])} '
        '(see q_table_tests.md).', '',
        'Short sector names (NSE Nifty index sector): ' + '; '.join(f'{v} = {k}' for k, v in SHORT.items()
                                                                    if k in set(q.best) | set(q.worst)) + '.']
open(f'{OUT}/q_table_quarters.md', 'w').write('\n'.join(out) + '\n')

text = '\n'.join(log) + '\n'
assert '/tmp/' not in text and '/home/' not in text
open(f'{OUT}/q_run.log', 'w').write(text)
