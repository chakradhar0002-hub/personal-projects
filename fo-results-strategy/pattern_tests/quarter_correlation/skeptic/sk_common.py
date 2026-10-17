"""Shared loader for the skeptic checks (read-only inputs). Reads LAB_ROOT and REPO_ROOT; outputs go to SKOUT
(default REPO_ROOT/results/quarter_correlation/skeptic)."""
import os
import numpy as np
import pandas as pd

REPO = os.environ.get('REPO_ROOT', '.')
LAB = os.environ.get('LAB_ROOT', 'lab')
D = f'{LAB}/sector_lab/data'
NS = os.path.join(REPO, 'results', 'nifty_sector_3day')
QC = os.path.join(REPO, 'results', 'quarter_correlation')
SKOUT = os.environ.get('SKOUT', os.path.join(QC, 'skeptic'))
os.makedirs(SKOUT, exist_ok=True)
COST = 0.17

def fp(v):
    return '-' if v is None or pd.isna(v) else f'{v:+.2f}'

def fpv(p):
    return '-' if p is None or pd.isna(p) else ('<0.001' if p < 0.001 else f'{p:.3f}')

def holm(ps):
    ps = np.asarray(ps, float)
    adj, run = np.empty(len(ps)), 0.0
    for k, i in enumerate(np.argsort(ps, kind='stable')):
        run = max(run, (len(ps) - k) * ps[i])
        adj[i] = min(1.0, run)
    return adj

def p2c(obs, null):
    """two-sided around null mean"""
    null = np.asarray(null, float); null = null[~np.isnan(null)]
    c = null.mean()
    return (1 + np.sum(np.abs(null - c) >= abs(obs - c) - 1e-12)) / (len(null) + 1)

def p2t(obs, null):
    """twice the smaller tail"""
    null = np.asarray(null, float); null = null[~np.isnan(null)]
    lo = (1 + np.sum(null <= obs + 1e-12)) / (len(null) + 1)
    hi = (1 + np.sum(null >= obs - 1e-12)) / (len(null) + 1)
    return min(1.0, 2 * min(lo, hi))

def rk(v):
    return pd.Series(v).rank().to_numpy()

def pear(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    m = ~(np.isnan(a) | np.isnan(b))
    return np.corrcoef(a[m], b[m])[0, 1]

def spear(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    m = ~(np.isnan(a) | np.isnan(b))
    return np.corrcoef(rk(a[m]), rk(b[m]))[0, 1]

def load():
    ev = pd.read_csv(f'{D}/events.csv')
    allev = ev.copy()
    ev = ev[ev.in_fo == True].copy()
    assert len(ev) == 3278 and ev.symbol.nunique() == 206
    lab = pd.read_csv(f'{NS}/results_3day.csv')
    ev = ev.merge(lab[['symbol', 'qn', 'nifty_sector', 'custom_sector']], on=['symbol', 'qn'], how='left', validate='1:1')
    assert ev.nifty_sector.notna().all()
    ev = ev.sort_values(['qn', 'symbol']).reset_index(drop=True)
    ev['td'] = ev.three_day * 100
    ev['n3'] = ev.nifty_3d * 100
    Q = ev.groupby('qn').td.mean()
    ev['x'] = ev.td - ev.qn.map(Q)
    qq = pd.read_csv(f'{QC}/q_quarters.csv')
    assert np.allclose(qq.avg, Q.to_numpy(), atol=6e-4)
    qq['Q'] = Q.to_numpy()
    qq['N'] = ev.groupby('qn').n3.mean().to_numpy()
    qq['S'] = qq.Q - qq.N
    return ev, allev, qq
