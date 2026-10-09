"""Candidate entry filters ('signal strength' family). Pure feature logic - no outcomes.

Each function takes the features frame d (features_signal.csv) and returns a boolean mask.
Missing feature value -> filter fails (row excluded).
"""
import numpy as np

XN, RSI = 'XN', 'cut_rsi14'


def W(d, xn=4, rsi=50):
    return (d[XN] > xn) & (d[RSI] > rsi)


def vol(d, t):
    return d.rx_vol_ratio_50 >= t


def clv75(d):
    return d.rx_clv >= 0.75


def gaphold(d):
    return (d.rx_gap_pct > 2) & (d.rx_low_vs_prevclose_pct > 0)


def brk20(d):
    return d.rx_don20_break_up == 1


def brk52(d):
    return d.rx_brk52 == 1


def lag(d, t):
    return d.lag_pct > t


def secrel(d, t=0):
    return d.secrel21 > t


def good(d):
    return d.GOOD.astype(bool)


def strong(d):
    return (d.rq_pat_yoy_pct > 25) & (d.rq_sales_yoy_pct > 15)


def pat50(d):
    return d.rq_pat_yoy_pct > 50


def large(d):
    return d.mcap >= 100000


def small(d):
    return d.mcap < 50000


CANDS = [
    # ---- singles: stricter thresholds of the baseline itself
    ('C01_RSI55', 'XN>4 & cut RSI14>55', lambda d: W(d, 4, 55)),
    ('C02_RSI60', 'XN>4 & cut RSI14>60', lambda d: W(d, 4, 60)),
    ('C03_RSI65', 'XN>4 & cut RSI14>65', lambda d: W(d, 4, 65)),
    ('C04_RSI70', 'XN>4 & cut RSI14>70', lambda d: W(d, 4, 70)),
    ('C05_XN5', 'XN>5 & cut RSI14>50', lambda d: W(d, 5, 50)),
    ('C06_XN6', 'XN>6 & cut RSI14>50', lambda d: W(d, 6, 50)),
    ('C07_XN8', 'XN>8 & cut RSI14>50', lambda d: W(d, 8, 50)),
    # ---- singles: extra filter on the baseline (XN>4 & cut RSI14>50)
    ('C08_VOL1.5', 'base & rx_vol_ratio_50>=1.5', lambda d: W(d) & vol(d, 1.5)),
    ('C09_VOL2', 'base & rx_vol_ratio_50>=2', lambda d: W(d) & vol(d, 2)),
    ('C10_VOL3', 'base & rx_vol_ratio_50>=3', lambda d: W(d) & vol(d, 3)),
    ('C11_CLV75', 'base & (C-L)/(H-L) on day k >= 0.75', lambda d: W(d) & clv75(d)),
    ('C12_GAPHOLD', 'base & gap>2% & low(k)>close(k-1)', lambda d: W(d) & gaphold(d)),
    ('C13_BRK20', 'base & close(k) > highest high of prior 20 sessions', lambda d: W(d) & brk20(d)),
    ('C14_BRK52', 'base & close(k) > highest high of prior 250 sessions', lambda d: W(d) & brk52(d)),
    ('C15_LAG0', 'base & 21-session stock-minus-Nifty return to cutoff > 0', lambda d: W(d) & lag(d, 0)),
    ('C16_LAG10', 'base & 21-session stock-minus-Nifty return to cutoff > 10', lambda d: W(d) & lag(d, 10)),
    ('C17_SECREL0', 'base & 21-session stock-minus-own-sector-index return to cutoff > 0', lambda d: W(d) & secrel(d)),
    ('C18_GOOD', 'base & GOOD (PAT YoY>25 & sales YoY>15, or margin chg YoY>+2pp)', lambda d: W(d) & good(d)),
    ('C19_STRONG', 'base & rq PAT YoY>25 & rq sales YoY>15', lambda d: W(d) & strong(d)),
    ('C20_PAT50', 'base & rq PAT YoY>50', lambda d: W(d) & pat50(d)),
    ('C21_LARGE', 'base & mcap>=100,000 cr', lambda d: W(d) & large(d)),
    ('C22_SMALL', 'base & mcap<50,000 cr', lambda d: W(d) & small(d)),
    # ---- 2-way combinations
    ('C23_RSI60_XN6', 'XN>6 & cut RSI14>60', lambda d: W(d, 6, 60)),
    ('C24_RSI60_VOL2', 'XN>4 & cut RSI14>60 & vol>=2', lambda d: W(d, 4, 60) & vol(d, 2)),
    ('C25_XN6_VOL2', 'XN>6 & cut RSI14>50 & vol>=2', lambda d: W(d, 6, 50) & vol(d, 2)),
    ('C26_VOL2_CLV75', 'base & vol>=2 & CLV>=0.75', lambda d: W(d) & vol(d, 2) & clv75(d)),
    ('C27_BRK20_VOL1.5', 'base & BRK20 & vol>=1.5', lambda d: W(d) & brk20(d) & vol(d, 1.5)),
    ('C28_BRK52_VOL1.5', 'base & BRK52 & vol>=1.5', lambda d: W(d) & brk52(d) & vol(d, 1.5)),
    ('C29_GOOD_VOL1.5', 'base & GOOD & vol>=1.5', lambda d: W(d) & good(d) & vol(d, 1.5)),
    ('C30_GOOD_XN6', 'XN>6 & cut RSI14>50 & GOOD', lambda d: W(d, 6, 50) & good(d)),
    ('C31_RSI60_GOOD', 'XN>4 & cut RSI14>60 & GOOD', lambda d: W(d, 4, 60) & good(d)),
    ('C32_XN6_CLV75', 'XN>6 & cut RSI14>50 & CLV>=0.75', lambda d: W(d, 6, 50) & clv75(d)),
    ('C33_LAG0_VOL2', 'base & LAG0 & vol>=2', lambda d: W(d) & lag(d, 0) & vol(d, 2)),
    ('C34_RSI60_CLV75', 'XN>4 & cut RSI14>60 & CLV>=0.75', lambda d: W(d, 4, 60) & clv75(d)),
    ('C35_RSI60_BRK52', 'XN>4 & cut RSI14>60 & BRK52', lambda d: W(d, 4, 60) & brk52(d)),
    ('C36_GOOD_CLV75', 'base & GOOD & CLV>=0.75', lambda d: W(d) & good(d) & clv75(d)),
    ('C37_SECREL0_VOL2', 'base & SECREL0 & vol>=2', lambda d: W(d) & secrel(d) & vol(d, 2)),
    ('C38_LARGE_VOL2', 'base & LARGE & vol>=2', lambda d: W(d) & large(d) & vol(d, 2)),
]
