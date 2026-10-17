"""Claim 3: do members beat their own index around results? Mechanical self-inclusion, cap vs equal weight, placebo."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

pd.set_option('display.width', 300)
pd.set_option('display.max_columns', 40)
ap = all_placebo()
FOQI = pd.MultiIndex.from_frame(ap[['symbol', 'qn']])

rows, allr, allp = [], [], []
for fam, d in [('sectoral', SECTORAL), ('thematic', THEMATIC)]:
    for name in d.values():
        mem = MEM[name]
        if not mem:
            continue
        g = ev[ev.symbol.isin(mem)]
        gr = bench(g, name, mem)
        gp = bench(ap[ap.symbol.isin(mem)], name, mem)
        # self-weight estimate w: daily (index - EW other members) = w (stock - EW other members), all days in span
        ps, pc = peer_arrays(mem)
        ir = IR[name]
        wts = {}
        for s in mem:
            j = col[s]
            k = np.arange(LO, HI + 1)
            own = CLEAN[k, j]
            c = pc[k] - own
            peer = (ps[k] - np.where(own, R[k, j], 0)) / np.where(c > 0, c, np.nan)
            y, x = ir[k] - peer, R[k, j] - peer
            ok = ~np.isnan(y) & ~np.isnan(x)
            wts[s] = np.dot(x[ok], y[ok]) / np.dot(x[ok], x[ok])
        gr['w'] = gr.symbol.map(wts)
        gr['mech'] = gr.w / (1 - gr.w) * gr.ab_idx          # understatement of each result's excess from self-inclusion
        res = {}
        for c in ['ab_idx', 'ab_peer']:
            x = gr.dropna(subset=[c])
            t, tp, _ = qt(x, c)
            dm, dt, dp, nq = diff_q(x, gp.dropna(subset=[c]), c)
            res[c] = (x[c].mean(), t, tp, gp[c].mean(), dm, dt, dp)
        top = sorted(wts.items(), key=lambda kv: -kv[1])[:3]
        rows.append(dict(fam=fam, index=name, members=len(mem), n=len(gr), plac_n=len(gp),
                         ex_idx=res['ab_idx'][0], ex_idx_qp=res['ab_idx'][2], plac_ex_idx=res['ab_idx'][3],
                         rmp_idx=res['ab_idx'][4], rmp_idx_t=res['ab_idx'][5], rmp_idx_p=res['ab_idx'][6],
                         ex_peer=res['ab_peer'][0], ex_peer_qp=res['ab_peer'][2], plac_ex_peer=res['ab_peer'][3],
                         rmp_peer=res['ab_peer'][4], rmp_peer_p=res['ab_peer'][6],
                         w_mean=gr.w.mean(), mech=gr.mech.mean(),
                         top_w=', '.join(f'{s} {v:.2f}' for s, v in top),
                         stock_ex=gr.td.mean(), idx3=gr.idx.mean(), plac_idx3=gp.idx.mean(), plac_stock=gp.td.mean()))
        allr.append(gr.assign(index=name, fam=fam))
        allp.append(gp.assign(index=name, fam=fam))
T = pd.DataFrame(rows)
for fam in ['sectoral', 'thematic']:
    k = T.fam == fam
    T.loc[k, 'holm_ex_idx_qp'] = holm(T.loc[k, 'ex_idx_qp']).values
    T.loc[k, 'holm_rmp_idx_p'] = holm(T.loc[k, 'rmp_idx_p']).values
T.to_csv(os.path.join(SKOUT, 't3_index.csv'), index=False)
print(T[['fam', 'index', 'members', 'n', 'plac_n', 'stock_ex', 'idx3', 'ex_idx', 'ex_idx_qp', 'holm_ex_idx_qp',
         'plac_stock', 'plac_idx3', 'plac_ex_idx', 'rmp_idx', 'rmp_idx_t', 'rmp_idx_p', 'holm_rmp_idx_p']].round(4).to_string())
print()
print(T[['fam', 'index', 'ex_idx', 'ex_peer', 'ex_peer_qp', 'plac_ex_peer', 'rmp_peer', 'rmp_peer_p', 'w_mean', 'mech',
         'top_w']].round(4).to_string())

A, Pp = pd.concat(allr), pd.concat(allp)
print(f'\npooled over all {len(A)} member results: excess vs own index {A.ab_idx.mean():+.3f} (placebo windows '
      f'{Pp.ab_idx.mean():+.3f}, {len(Pp)}); vs EW other members {A.ab_peer.mean():+.3f} (placebo {Pp.ab_peer.mean():+.3f})')
for fam in ['sectoral', 'thematic']:
    a, p = A[A.fam == fam], Pp[Pp.fam == fam]
    print(f'  {fam}: results {a.ab_idx.mean():+.3f} vs placebo {p.ab_idx.mean():+.3f}; peers {a.ab_peer.mean():+.3f} vs '
          f'{p.ab_peer.mean():+.3f}; mean self-weight {a.w.mean():.3f}, mean mechanical understatement {a.mech.mean():+.3f}')
nonauto = A[(A.fam == 'sectoral') & (A['index'] != 'Nifty Auto')]
nonauto_p = Pp[(Pp.fam == 'sectoral') & (Pp['index'] != 'Nifty Auto')]
print(f'  sectoral without Nifty Auto: results {nonauto.ab_idx.mean():+.3f} (n {len(nonauto)}) vs placebo '
      f'{nonauto_p.ab_idx.mean():+.3f}')
# All F&O results vs Nifty 50, and vs EW universe, results vs placebo
allg = bench(ev)
allpl = bench(ap)
for c, lab in [('ab_n50', 'minus Nifty 50'), ('ab_ewu', 'minus EW F&O universe'), ('ab_mm', 'market model'),
               ('td', 'raw')]:
    dm, dt, dp, nq = diff_q(allg, allpl, c)
    print(f'all 3,278 F&O results {lab}: results {allg[c].mean():+.3f}, placebo {allpl[c].mean():+.3f}, '
          f'results-minus-placebo by quarter {dm:+.3f} t {dt:+.2f} p {dp:.3f}')

# heavyweights: how big is the gap between "vs index" and "vs other members" for the top-weight stocks
print('\nheavyweight members (estimated self-weight >= 0.15): result excess vs index and vs EW other members')
H = A[A.w >= 0.15].groupby(['index', 'symbol']).agg(n=('td', 'size'), w=('w', 'first'), ex_idx=('ab_idx', 'mean'),
                                                     ex_peer=('ab_peer', 'mean'), mech=('mech', 'mean'))
print(H.round(3).to_string())

# Commodities: is the shortfall vs index results-specific?
for name in ['Nifty Commodities', 'Nifty India Consumption', 'Nifty Energy', 'Nifty MNC', 'Nifty Auto']:
    a, p = A[A['index'] == name], Pp[Pp['index'] == name]
    sa = a.groupby('symbol').ab_idx.mean()
    sp = p.groupby('symbol').ab_idx.mean()
    both = pd.concat([sa.rename('res'), sp.rename('plac')], axis=1)
    print(f'{name}: members below index in results windows {(sa < 0).sum()} of {len(sa)}; in placebo windows '
          f'{(sp < 0).sum()} of {len(sp)}; corr(stock results excess, stock placebo excess) {both.corr().iloc[0, 1]:+.2f}')
