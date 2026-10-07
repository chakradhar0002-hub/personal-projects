"""ROUND 2 - POST-HOC (written after round-1 results were seen; label everything from here as post-hoc).
Question: round 1 showed the oversold family is the only one consistently positive (+1.5..3%). How strict must
"oversold" be to average +5%, and does the strictness chosen on the first 14 quarters hold on the last 8?

Fixed design (no fitted weights):
  score = mean of four z-scores, each standardised with the mean/sd of in_fo rows in qn 0..13 only:
          -vs_nifty_1w, -vs_nifty_1m, -r3d, -vs_ma50     (higher = more oversold; needs all four)
  Grid of score thresholds: 1.0 1.25 1.5 1.75 2.0 2.25 2.5 3.0  x outcomes {3day, tp3}  = 16 variants.
  Selection: best in-sample (qn 0..13) pooled average with >= MIN trades over >= 5 quarters (MIN 10/20/30);
  walk-forward q=6..21 with >= MIN trades over >= 3 quarters; 500 within-quarter shuffles of the outcome rows.
  Placebo depth curve: same score (same constants) on F&O non-results windows.
Also prints the 'all stocks' depth curve and the pre-F&O share.
Outputs: round2_depth.csv, round2_selection.json"""
import numpy as np, pandas as pd, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
COST = 0.0017; SEED = 777; NSH = 500
F = pd.read_csv(os.path.join(HERE, 'events_feat.csv')); O = pd.read_csv(os.path.join(HERE, 'events_outcomes.csv'))
PL = pd.read_csv(os.path.join(HERE, 'placebo.csv.gz')); PL = PL[PL.in_fo == True].reset_index(drop=True)
COLS = ['vs_nifty_1w', 'vs_nifty_1m', 'r3d', 'vs_ma50']
ref = F[(F.in_fo == True) & (F.qn < 14)]
mu, sd = ref[COLS].mean(), ref[COLS].std()
def score(df):
    z = -(df[COLS] - mu) / sd
    return z.mean(axis=1, skipna=False).values
F['score'] = score(F); PL['score'] = score(PL)
TH = [1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 3.0]

def st(p, q):
    p = np.asarray(p); q = np.asarray(q)
    if len(p) == 0: return dict(n=0)
    s = np.sort(p)[::-1]; qm = pd.Series(p).groupby(q).mean(); tot = p.sum()
    return dict(n=len(p), nq=qm.size, avg=100 * p.mean(), net=100 * (p.mean() - COST), avg_q=100 * qm.mean(), win=100 * (p > 0).mean(),
                med=100 * np.median(p), top5_share=s[:5].sum() / tot if tot > 0 else np.nan, wo_top5=100 * s[5:].mean() if len(p) > 5 else np.nan,
                is_n=int((q < 14).sum()), is_avg=100 * p[q < 14].mean() if (q < 14).any() else np.nan,
                oos_n=int((q >= 14).sum()), oos_nq=len(np.unique(q[q >= 14])), oos_avg=100 * p[q >= 14].mean() if (q >= 14).any() else np.nan)
rows = []
for th in TH:
    for uni in ['F&O', 'all', 'preF&O']:
        sel = {'F&O': O.in_fo.values == True, 'all': np.ones(len(O), bool), 'preF&O': O.in_fo.values == False}[uni]
        m = sel & (F.score.values >= th)
        for oc in ['three_day', 'tp3']:
            rows.append(dict(th=th, universe=uni, outcome=oc, **st(O[oc].values[m], O.qn.values[m])))
    mp = PL.score.values >= th
    for oc in ['three_day', 'tp3']:
        p = PL[oc].values[mp]; q = PL.qn.values[mp]
        rows.append(dict(th=th, universe='placebo F&O', outcome=oc, n=int(mp.sum()), avg=100 * p.mean(), is_avg=100 * p[q < 14].mean(), oos_avg=100 * p[q >= 14].mean()))
dep = pd.DataFrame(rows); dep.to_csv(os.path.join(HERE, 'round2_depth.csv'), index=False)

# ---- selection on F&O ----
FO = O.in_fo.values == True
y3, yt = O.three_day.values[FO], O.tp3.values[FO]; qn = O.qn.values[FO]; sc = F.score.values[FO]
N = len(qn); Q1 = np.zeros((N, 22)); Q1[np.arange(N), qn] = 1
names = [(th, oc) for th in TH for oc in ['3day', 'tp']]
M = np.array([(np.nan_to_num(sc, nan=-9) >= th) for th, oc in names], float)
CQ = M @ Q1; IS = np.arange(22) < 14
groups = [np.where(qn == q)[0] for q in range(22)]
def SQ_of(pi):
    Y = np.array([(y3[pi] if oc == '3day' else yt[pi]) for th, oc in names])
    return (M * Y) @ Q1
def select(SQ, minT):
    c, s = CQ[:, IS].sum(1), SQ[:, IS].sum(1); el = (c >= minT) & ((CQ[:, IS] > 0).sum(1) >= 5)
    a = np.where(el, s / np.maximum(c, 1), -np.inf); v = int(np.argmax(a))
    co, so = CQ[v, ~IS].sum(), SQ[v, ~IS].sum()
    ws = wc = 0.0
    for q in range(6, 22):
        cc, ss = CQ[:, :q].sum(1), SQ[:, :q].sum(1); e2 = (cc >= minT) & ((CQ[:, :q] > 0).sum(1) >= 3)
        if not e2.any(): continue
        vq = int(np.argmax(np.where(e2, ss / np.maximum(cc, 1), -np.inf))); ws += SQ[vq, q]; wc += CQ[vq, q]
    return dict(best=names[v], is_avg=100 * a[v], is_n=int(c[v]), oos_avg=100 * so / co if co else np.nan, oos_n=int(co),
                oos_nq=int((CQ[v, ~IS] > 0).sum()), wf_avg=100 * ws / wc if wc else np.nan, wf_n=int(wc))
real = {m: select(SQ_of(np.arange(N)), m) for m in [10, 20, 30]}
rng = np.random.default_rng(SEED); sh = {m: [] for m in [10, 20, 30]}
for b in range(NSH):
    pi = np.empty(N, int)
    for g in groups: pi[g] = rng.permutation(g)
    SQ = SQ_of(pi)
    for m in sh: sh[m].append(select(SQ, m))
out = {}
for m in [10, 20, 30]:
    d = pd.DataFrame(sh[m]); r = real[m]
    out[m] = dict(real=r, frac_shuf_is_ge=float((d.is_avg >= r['is_avg']).mean()), shuf_is_median=d.is_avg.median(),
                  shuf_oos_mean=d.oos_avg.mean(), frac_shuf_oos_ge=float((d.oos_avg >= r['oos_avg']).mean()),
                  shuf_wf_mean=d.wf_avg.mean(), frac_shuf_wf_ge=float((d.wf_avg >= r['wf_avg']).mean()))
json.dump(out, open(os.path.join(HERE, 'round2_selection.json'), 'w'), indent=1, default=float)
pd.set_option('display.width', 250)
print(dep[dep.outcome == 'three_day'].round(2).to_string())
print(dep[(dep.outcome == 'tp3') & (dep.universe.isin(['F&O', 'placebo F&O']))].round(2).to_string())
print(json.dumps(out, indent=1, default=float))
