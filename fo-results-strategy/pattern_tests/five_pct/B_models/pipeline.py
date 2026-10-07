"""Walk-forward ML pipeline aimed at a +5% average 3-day results-window trade (see PLAN.txt).

usage: python3 pipeline.py real [fo|all]
       python3 pipeline.py shuffle [fo|all] SEED_START N_RUNS
"""
import os, sys, json, time
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, \
    RandomForestClassifier, ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import roc_auc_score

HERE = os.path.dirname(os.path.abspath(__file__))
COST = 0.0017
FIRST_PRED_Q, FIRST_OUTER_Q, SPLIT_Q, LAST_Q = 3, 6, 14, 21
KS = [1, 2, 3, 5, 10]
N_JOBS = int(os.environ.get('NJOBS', '3'))

NON_FEATURES = {'symbol', 'quarter', 'qn', 'results_date', 'cutoff', 'industry', 'fin_type', 'timing', 'three_day',
                'excess_nifty', 'in_fo', 'tp3', 'after_close'}


def load(universe):
    T = pd.read_csv(os.path.join(HERE, 'model_table.csv'))
    if universe == 'fo':
        T = T[T.in_fo].reset_index(drop=True)
    feats = [c for c in T.columns if c not in NON_FEATURES]
    X = T[feats].astype(float).values
    X[~np.isfinite(X)] = np.nan
    return T, feats, X


# ---------------------------------------------------------------- base models and configs
CONFIGS = {
    'hgb_gt': [dict(max_depth=2, max_iter=150, learning_rate=.05, min_samples_leaf=40),
               dict(max_depth=3, max_iter=150, learning_rate=.05, min_samples_leaf=40),
               dict(max_depth=3, max_iter=300, learning_rate=.03, min_samples_leaf=100, l2_regularization=1.0)],
    'rf_gt': [dict(n_estimators=200, min_samples_leaf=20, max_features=.3),
              dict(n_estimators=200, min_samples_leaf=60, max_features=.3)],
    'et_gt': [dict(n_estimators=200, min_samples_leaf=20, max_features=.5),
              dict(n_estimators=200, min_samples_leaf=60, max_features=.5)],
    'lr_gt': [dict(C=.003), dict(C=.03), dict(C=.3)],
    'ridge': [dict(alpha=10.), dict(alpha=100.), dict(alpha=1000.)],
}
CONFIGS['hgb_lt'] = CONFIGS['hgb_gt']; CONFIGS['hgb_reg'] = CONFIGS['hgb_gt']
CONFIGS['rf_lt'] = CONFIGS['rf_gt']; CONFIGS['et_lt'] = CONFIGS['et_gt']; CONFIGS['lr_lt'] = CONFIGS['lr_gt']


def prep_linear(Xtr, Xte):
    lo = np.nanpercentile(Xtr, 1, axis=0); hi = np.nanpercentile(Xtr, 99, axis=0)
    med = np.nanmedian(Xtr, axis=0)
    lo = np.where(np.isfinite(lo), lo, 0); hi = np.where(np.isfinite(hi), hi, 0); med = np.where(np.isfinite(med), med, 0)
    miss_cols = np.isnan(Xtr).mean(0) > 0.01

    def tf(X):
        M = np.isnan(X[:, miss_cols]).astype(float)
        Z = np.clip(np.where(np.isnan(X), med, X), lo, hi)
        return np.hstack([Z, M])
    A, B = tf(Xtr), tf(Xte)
    mu, sd = A.mean(0), A.std(0) + 1e-9
    return (A - mu) / sd, (B - mu) / sd


def fit_predict(base, cfg, Xtr, ytr, Xte, seed=0):
    # drop columns that are constant or (almost) all missing in this training set
    keep = []
    for j in range(Xtr.shape[1]):
        v = Xtr[:, j]; v = v[np.isfinite(v)]
        keep.append(len(v) >= 20 and np.unique(v[:2000]).size > 1)
    keep = np.array(keep)
    Xtr, Xte = Xtr[:, keep], Xte[:, keep]
    if base in ('hgb_gt', 'hgb_lt', 'rf_gt', 'rf_lt', 'et_gt', 'et_lt', 'lr_gt', 'lr_lt'):
        lab = (ytr > .05) if base.endswith('gt') else (ytr < -.05)
        lab = lab.astype(int)
    if base.startswith('hgb_') and base != 'hgb_reg':
        m = HistGradientBoostingClassifier(random_state=seed, **cfg).fit(Xtr, lab); return m.predict_proba(Xte)[:, 1]
    if base == 'hgb_reg':
        m = HistGradientBoostingRegressor(random_state=seed, **cfg).fit(Xtr, np.clip(ytr, -.15, .15)); return m.predict(Xte)
    if base.startswith('rf_') or base.startswith('et_'):
        A = np.where(np.isnan(Xtr), -999., Xtr); B = np.where(np.isnan(Xte), -999., Xte)
        M = RandomForestClassifier if base.startswith('rf_') else ExtraTreesClassifier
        m = M(random_state=seed, n_jobs=1, **cfg).fit(A, lab); return m.predict_proba(B)[:, 1]
    A, B = prep_linear(Xtr, Xte)
    if base.startswith('lr_'):
        m = LogisticRegression(max_iter=2000, **cfg).fit(A, lab); return m.predict_proba(B)[:, 1]
    if base == 'ridge':
        m = Ridge(**cfg).fit(A, np.clip(ytr, -.15, .15)); return m.predict(B)
    raise ValueError(base)


def task(base, ci, q, X, y, qn):
    tr = qn < q; te = qn >= q
    p = fit_predict(base, CONFIGS[base][ci], X[tr], y[tr], X[te])
    return base, ci, q, p


def all_predictions(X, y, qn):
    """pred[(base,ci)] = (one_step array over all rows: prediction made by model trained on quarters < row's quarter,
                          split array: prediction from the model trained on quarters < SPLIT_Q, rows qn>=SPLIT_Q)"""
    jobs = [(b, ci, q) for b in CONFIGS for ci in range(len(CONFIGS[b])) for q in range(FIRST_PRED_Q, LAST_Q + 1)]
    # schedule slow (forest) jobs first
    jobs.sort(key=lambda t: (0 if t[0][:2] in ('rf', 'et') else 1, -t[2]))
    res = Parallel(n_jobs=N_JOBS)(delayed(task)(b, ci, q, X, y, qn) for b, ci, q in jobs)
    pred = {}
    for b, ci, q, p in res:
        key = (b, ci)
        if key not in pred:
            pred[key] = [np.full(len(y), np.nan), np.full(len(y), np.nan)]
        idx = np.where(qn >= q)[0]
        one = qn[idx] == q
        pred[key][0][idx[one]] = p[one]
        if q == SPLIT_Q:
            pred[key][1][idx] = p
    return pred


# ---------------------------------------------------------------- families, selection, pick rules
LONG_FAM = {'HGBc+': ('hgb_gt', 1), 'RFc+': ('rf_gt', 1), 'ETc+': ('et_gt', 1), 'LR+': ('lr_gt', 1),
            'HGBr': ('hgb_reg', 1), 'RIDGE': ('ridge', 1)}
SHORT_FAM = {'HGBc-': ('hgb_lt', 1), 'RFc-': ('rf_lt', 1), 'ETc-': ('et_lt', 1), 'LR-': ('lr_lt', 1),
             '-HGBr': ('hgb_reg', -1), '-RIDGE': ('ridge', -1)}
FAMILIES = list(LONG_FAM) + ['HGBnet', 'ENS+'] + list(SHORT_FAM) + ['-HGBnet', 'ENS-']
DIRECTION = {f: (1 if f in LONG_FAM or f in ('HGBnet', 'ENS+') else -1) for f in FAMILIES}
RULES = [f'top{k}' for k in KS] + ['T2', 'T5', 'TE']


def topk_mean(score, s, qn, quarters, k):
    vals = []
    for v in quarters:
        m = np.where(qn == v)[0]
        if len(m) == 0: continue
        o = m[np.argsort(-score[m], kind='stable')[:k]]
        vals.extend(s[o])
    return np.mean(vals) if vals else -np.inf


def choose_config(pred, base, sign, y, qn, q):
    """config with best mean signed return of top-5 per quarter over validation quarters FIRST_PRED_Q..q-1"""
    vq = range(FIRST_PRED_Q, q)
    best, bv = 0, -np.inf
    for ci in range(len(CONFIGS[base])):
        sc = sign * pred[(base, ci)][0]
        v = topk_mean(sc, sign * y if base in ('hgb_reg', 'ridge') else (y if base.endswith('gt') else -y), qn, vq, 5)
        if v > bv: bv, best = v, ci
    return best


def family_scores(pred, y, qn, q, which):
    """score arrays (one-step and split) for every family using configs chosen with quarters < q."""
    sel = {}
    for b in CONFIGS:
        sign = 1
        sel[(b, 1)] = choose_config(pred, b, 1, y, qn, q)
    sel[('hgb_reg', -1)] = choose_config(pred, 'hgb_reg', -1, y, qn, q)
    sel[('ridge', -1)] = choose_config(pred, 'ridge', -1, y, qn, q)
    out = {}
    for f, (b, sg) in {**LONG_FAM, **SHORT_FAM}.items():
        out[f] = sg * pred[(b, sel[(b, sg)])][which]
    out['HGBnet'] = out['HGBc+'] - out['HGBc-']
    out['-HGBnet'] = -out['HGBnet']
    out['ENS+'] = (out['HGBc+'] + out['RFc+'] + out['ETc+'] + out['LR+']) / 4
    out['ENS-'] = (out['HGBc-'] + out['RFc-'] + out['ETc-'] + out['LR-']) / 4
    return out, sel


PCTS = [80, 85, 90, 92.5, 95, 97, 98, 99, 99.5]


def picks_for_quarter(score_q, score_hist, s_hist, rule):
    """indices (into score_q) picked. score_hist/s_hist: earlier OOS scores and signed returns (for cuts)."""
    if rule.startswith('top'):
        k = int(rule[3:])
        return np.argsort(-score_q, kind='stable')[:k]
    h = score_hist[np.isfinite(score_hist)]
    if len(h) < 50:
        return np.array([], int)
    if rule == 'T2':
        cut = np.percentile(h, 98)
    elif rule == 'T5':
        cut = np.percentile(h, 95)
    else:
        cut = None
        ok = np.isfinite(score_hist)
        for p in PCTS:
            c = np.percentile(h, p)
            sel = ok & (score_hist >= c)
            if sel.sum() >= 10 and s_hist[sel].mean() >= .05:
                cut = c; break
        if cut is None:
            return np.array([], int)
    return np.where(score_q >= cut)[0]


def run_pipeline(T, X, y, verbose=False):
    qn = T.qn.values
    t0 = time.time()
    pred = all_predictions(X, y, qn)
    if verbose: print(f'predictions done {time.time() - t0:.0f}s', flush=True)
    picks = {}          # (protocol, family, rule) -> list of row indices
    for f in FAMILIES:
        for r in RULES:
            picks[('WF', f, r)] = []; picks[('SPLIT', f, r)] = []
    sel_log = {}
    # walk-forward
    for q in range(FIRST_OUTER_Q, LAST_Q + 1):
        fs, sel = family_scores(pred, y, qn, q, 0)
        sel_log[q] = {f'{k[0]}{"" if k[1] == 1 else "_short"}': v for k, v in sel.items()}
        mq = np.where(qn == q)[0]
        mh = np.where((qn >= FIRST_PRED_Q) & (qn < q))[0]
        for f in FAMILIES:
            sh = DIRECTION[f] * y[mh]
            for r in RULES:
                p = picks_for_quarter(fs[f][mq], fs[f][mh], sh, r)
                picks[('WF', f, r)].extend(mq[p].tolist())
    # fixed split: configs chosen with quarters < SPLIT_Q, one model trained on < SPLIT_Q applied to all later quarters
    fs_split, _ = family_scores(pred, y, qn, SPLIT_Q, 1)
    fs_hist, _ = family_scores(pred, y, qn, SPLIT_Q, 0)
    mh = np.where((qn >= FIRST_PRED_Q) & (qn < SPLIT_Q))[0]
    for q in range(SPLIT_Q, LAST_Q + 1):
        mq = np.where(qn == q)[0]
        for f in FAMILIES:
            sh = DIRECTION[f] * y[mh]
            for r in RULES:
                p = picks_for_quarter(fs_split[f][mq], fs_hist[f][mh], sh, r)
                picks[('SPLIT', f, r)].extend(mq[p].tolist())
    if verbose: print(f'picks done {time.time() - t0:.0f}s', flush=True)
    return pred, picks, sel_log


# ---------------------------------------------------------------- metrics
def metrics(s_gross, qn_p):
    """s_gross: signed gross returns of picks (fractions). returns dict in PERCENT."""
    n = len(s_gross)
    if n == 0:
        return dict(n=0, quarters=0, avg_gross=np.nan, avg_net=np.nan, avg_qavg_net=np.nan, pct_win=np.nan,
                    median=np.nan, top5_share=np.nan, avg_wo_top5=np.nan)
    net = s_gross - COST
    qa = pd.Series(net).groupby(qn_p).mean()
    srt = np.sort(s_gross)[::-1]
    tot = s_gross.sum()
    return dict(n=n, quarters=int(len(qa)), avg_gross=100 * s_gross.mean(), avg_net=100 * net.mean(),
                avg_qavg_net=100 * qa.mean(), pct_win=100 * (net > 0).mean(), median=100 * np.median(s_gross),
                top5_share=(srt[:5].sum() / tot) if tot > 0 else np.nan,
                avg_wo_top5=100 * srt[5:].mean() if n > 5 else np.nan)


def summarize(T, y, picks):
    qn = T.qn.values
    rows = []
    for (proto, f, r), idx in picks.items():
        idx = np.array(idx, int)
        s = DIRECTION[f] * y[idx]
        q = qn[idx]
        if proto == 'WF':
            parts = {'is': q <= 13, 'oos': q >= 14, 'all': np.ones(len(q), bool)}
        else:
            parts = {'oos': np.ones(len(q), bool)}
        for pn, m in parts.items():
            d = metrics(s[m], q[m]); d.update(protocol=proto, family=f, rule=r, part=pn,
                                              side='long' if DIRECTION[f] > 0 else 'short')
            rows.append(d)
    return pd.DataFrame(rows)


def per_quarter(T, y, picks):
    """compact per-(setting, quarter) sums for nested selection: n, sum of signed gross returns."""
    qn = T.qn.values; rows = []
    for (proto, f, r), idx in picks.items():
        idx = np.array(idx, int)
        if len(idx) == 0: continue
        s = pd.Series(P_DIR(f) * y[idx]).groupby(qn[idx]).agg(['size', 'sum'])
        for q, (n, sm) in s.iterrows():
            rows.append((proto, f, r, int(q), int(n), float(sm)))
    return pd.DataFrame(rows, columns=['protocol', 'family', 'rule', 'qn', 'n', 'sum'])


def P_DIR(f):
    return DIRECTION[f]


def meta_select(PQ, min_n=10, first_q=8):
    """fully nested walk-forward of the setting choice: at quarter q choose the WF setting with the best pooled
    net average over quarters 6..q-1 (>= min_n trades) and take its picks in q. Returns per-quarter (n, sum)."""
    W = PQ[PQ.protocol == 'WF']
    out = []
    for q in range(first_q, LAST_Q + 1):
        h = W[W.qn < q].groupby(['family', 'rule'])[['n', 'sum']].sum()
        h = h[h.n >= min_n]
        if len(h) == 0: continue
        h['avg'] = h['sum'] / h['n'] - COST
        best = h['avg'].idxmax()
        cur = W[(W.qn == q) & (W.family == best[0]) & (W.rule == best[1])]
        n, sm = (int(cur.n.sum()), float(cur['sum'].sum()))
        out.append(dict(qn=q, setting='|'.join(best), hist_avg=100 * h.loc[best, 'avg'], n=n, sum=sm))
    return pd.DataFrame(out)


def meta_stats(M):
    d = {}
    for name, m in (('8_21', M.qn >= 8), ('14_21', M.qn >= 14)):
        n = M[m].n.sum(); d[f'meta_n_{name}'] = n
        d[f'meta_avg_net_{name}'] = 100 * (M[m]['sum'].sum() / n - COST) if n else np.nan
    return d


def key_stats(S):
    """numbers recorded for the luck check."""
    wf = S[S.protocol == 'WF'].pivot_table(index=['family', 'rule'], columns='part', values=['avg_net', 'n'])
    ok_is = wf[('n', 'is')] >= 10
    best = wf[ok_is][('avg_net', 'is')].idxmax()
    sp = S[(S.protocol == 'SPLIT')].set_index(['family', 'rule'])
    ok_all = wf[('n', 'all')] >= 10
    out = dict(best_is_setting='|'.join(best), best_is_avg_net=wf.loc[best, ('avg_net', 'is')],
               best_is_n=wf.loc[best, ('n', 'is')],
               best_is_oos_wf=wf.loc[best, ('avg_net', 'oos')], best_is_oos_wf_n=wf.loc[best, ('n', 'oos')],
               best_is_oos_split=sp.loc[best, 'avg_net'], best_is_oos_split_n=sp.loc[best, 'n'],
               max_all_wf=wf[ok_all][('avg_net', 'all')].max(),
               max_all_wf_n20=wf[wf[('n', 'all')] >= 20][('avg_net', 'all')].max(),
               max_all_wf_n30=wf[wf[('n', 'all')] >= 30][('avg_net', 'all')].max(),
               max_oos_wf=wf[wf[('n', 'oos')] >= 10][('avg_net', 'oos')].max(),
               max_oos_split=sp[sp.n >= 10].avg_net.max())
    for f in ('ENS+', 'ENS-'):
        out[f'{f}_top5_all_wf'] = wf.loc[(f, 'top5'), ('avg_net', 'all')]
        out[f'{f}_top5_oos_split'] = sp.loc[(f, 'top5'), 'avg_net']
    return out


def auc_table(T, y, pred):
    """AUC / precision of the walk-forward-selected classifiers for y>5% and y<-5% on quarters 6..21."""
    qn = T.qn.values
    rows = []
    sc = {f: np.full(len(y), np.nan) for f in FAMILIES}
    for q in range(FIRST_OUTER_Q, LAST_Q + 1):
        fs, _ = family_scores(pred, y, qn, q, 0)
        m = qn == q
        for f in FAMILIES:
            sc[f][m] = fs[f][m]
    m = qn >= FIRST_OUTER_Q
    for f in FAMILIES:
        lab = (y > .05) if DIRECTION[f] > 0 else (y < -.05)
        s = sc[f]
        for part, pm in (('6-13', m & (qn <= 13)), ('14-21', qn >= 14), ('6-21', m)):
            a = roc_auc_score(lab[pm], s[pm])
            row = dict(family=f, part=part, auc=a, base_rate=100 * lab[pm].mean())
            for k in (1, 3, 5, 10):
                hits = []
                for q in np.unique(qn[pm]):
                    mm = np.where(qn == q)[0]
                    o = mm[np.argsort(-s[mm], kind='stable')[:k]]
                    hits.extend(lab[o])
                row[f'prec_top{k}'] = 100 * np.mean(hits)
            rows.append(row)
    return pd.DataFrame(rows), sc


def main():
    mode = sys.argv[1]; universe = sys.argv[2] if len(sys.argv) > 2 else 'fo'
    T, feats, X = load(universe)
    y0 = T.three_day.values.astype(float)
    tag = universe
    if mode == 'real':
        print(f'universe={universe} rows={len(T)} features={len(feats)}', flush=True)
        pred, picks, sel_log = run_pipeline(T, X, y0, verbose=True)
        S = summarize(T, y0, picks)
        S.to_csv(os.path.join(HERE, f'settings_real_{tag}.csv'), index=False)
        PQ = per_quarter(T, y0, picks); PQ.to_csv(os.path.join(HERE, f'perquarter_real_{tag}.csv'), index=False)
        ks = key_stats(S)
        for mn in (10, 20, 30):
            M = meta_select(PQ, mn); M.to_csv(os.path.join(HERE, f'meta_select_real_{tag}_min{mn}.csv'), index=False)
            ks.update({k + f'_min{mn}': v for k, v in meta_stats(M).items()})
        print(json.dumps(ks, indent=1, default=float))
        json.dump(ks, open(os.path.join(HERE, f'keystats_real_{tag}.json'), 'w'), indent=1, default=float)
        A, sc = auc_table(T, y0, pred)
        A.to_csv(os.path.join(HERE, f'auc_real_{tag}.csv'), index=False)
        json.dump(sel_log, open(os.path.join(HERE, f'config_choices_{tag}.json'), 'w'), indent=1, default=int)
        # save picks and OOS scores for later inspection
        pk = [dict(protocol=p, family=f, rule=r, row=i, symbol=T.symbol[i], qn=int(T.qn[i]), three_day=y0[i])
              for (p, f, r), idx in picks.items() for i in idx]
        pd.DataFrame(pk).to_csv(os.path.join(HERE, f'picks_real_{tag}.csv'), index=False)
        np.save(os.path.join(HERE, f'pred_real_{tag}.npy'), {str(k): v for k, v in pred.items()}, allow_pickle=True)
        sc_df = pd.DataFrame(sc); sc_df[['symbol', 'qn', 'three_day']] = T[['symbol', 'qn', 'three_day']]
        sc_df.to_csv(os.path.join(HERE, f'wf_scores_real_{tag}.csv'), index=False)
    else:
        seed0, nrun = int(sys.argv[3]), int(sys.argv[4])
        out_rows = []; set_rows = []; pq_rows = []
        fn = os.path.join(HERE, f'keystats_shuffled_{tag}_{seed0}.csv')
        for s in range(seed0, seed0 + nrun):
            t0 = time.time()
            rng = np.random.default_rng(s)
            y = y0.copy()
            for q in np.unique(T.qn):
                m = np.where(T.qn.values == q)[0]
                y[m] = y0[rng.permutation(m)]
            pred, picks, _ = run_pipeline(T, X, y)
            S = summarize(T, y, picks)
            ks = key_stats(S); ks['seed'] = s
            PQ = per_quarter(T, y, picks); PQ['seed'] = s; pq_rows.append(PQ)
            for mn in (10, 20, 30):
                ks.update({k + f'_min{mn}': v for k, v in meta_stats(meta_select(PQ, mn)).items()})
            pd.concat(pq_rows).to_csv(os.path.join(HERE, f'perquarter_shuffled_{tag}_{seed0}.csv'), index=False)
            out_rows.append(ks)
            S['seed'] = s; set_rows.append(S)
            pd.DataFrame(out_rows).to_csv(fn, index=False)
            pd.concat(set_rows).to_csv(os.path.join(HERE, f'settings_shuffled_{tag}_{seed0}.csv'), index=False)
            print(f'seed {s} done {time.time() - t0:.0f}s best_is={ks["best_is_setting"]} {ks["best_is_avg_net"]:.2f} '
                  f'oos={ks["best_is_oos_wf"]:.2f} max_all={ks["max_all_wf"]:.2f}', flush=True)


if __name__ == '__main__':
    main()
