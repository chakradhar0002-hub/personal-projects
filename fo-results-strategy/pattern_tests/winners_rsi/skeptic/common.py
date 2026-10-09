"""Shared helpers for the skeptic checks (own code; reads only, writes only into this folder)."""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SP = os.environ.get('LAB_ROOT', os.path.abspath(os.path.join(HERE, '..', '..')))  # scratch data folder
DATA = f'{SP}/sector_lab/data'
TAFA = f'{SP}/tafa/C_post_results'
BUILD = f'{SP}/winners_rsi/build'
C_STK, C_HEDGE = 0.17, 0.02
COST = C_STK + C_HEDGE
pd.set_option('display.width', 250, 'display.max_rows', 500, 'display.max_columns', 80, 'display.max_colwidth', 200)


class Log:
    def __init__(self, name):
        self.f = open(f'{HERE}/{name}', 'w')

    def __call__(self, *a):
        s = ' '.join(str(x) for x in a)
        print(s)
        self.f.write(s + '\n')
        self.f.flush()


def sg(x, d=2):
    try:
        return 'n/a' if x is None or not np.isfinite(x) else f'{x:+.{d}f}'
    except TypeError:
        return str(x)


def ols(y, X, cl=None, fe=None, add_const=False):
    """OLS with optional absorbed fixed effects (within-demeaning) and CR1 cluster-robust SE.
    Returns beta, se, t, G."""
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    if X.ndim == 1:
        X = X[:, None]
    if fe is not None:
        fe = np.asarray(fe)
        y = y - pd.Series(y).groupby(fe).transform('mean').to_numpy()
        X = X - pd.DataFrame(X).groupby(fe).transform('mean').to_numpy()
    elif add_const:
        X = np.c_[np.ones(len(y)), X]
    XtX = np.linalg.pinv(X.T @ X)
    b = XtX @ X.T @ y
    e = y - X @ b
    n, k = X.shape
    if cl is None:
        s2 = (e @ e) / max(n - k, 1)
        V = XtX * s2
        G = n
    else:
        cl = np.asarray(cl)
        u = np.unique(cl)
        G = len(u)
        meat = np.zeros((k, k))
        codes = pd.factorize(cl)[0]
        S = np.zeros((G, k))
        np.add.at(S, codes, X * e[:, None])
        meat = S.T @ S
        V = XtX @ meat @ XtX * G / (G - 1) * (n - 1) / max(n - k, 1)
    se = np.sqrt(np.diag(V))
    return b, se, b / se, G


def winsor(x, lo=-10, hi=10):
    return np.clip(np.asarray(x, float), lo, hi)


def within_q_diff(df, sub, base, col='vsN_net', q='qn'):
    """Per-trade mean of (subset trade - mean of `base` trades of the same quarter) = the pre-registered d_W."""
    bm = df.loc[base].groupby(q)[col].mean()
    x = df.loc[sub]
    return (x[col] - x[q].map(bm)).mean()
