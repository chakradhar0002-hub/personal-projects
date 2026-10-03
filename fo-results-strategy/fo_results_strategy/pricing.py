"""Black-Scholes pricing for European options (NSE stock options are European)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Iterable, Optional

TRADING_DAYS = 252
SQRT_2_OVER_PI = math.sqrt(2.0 / math.pi)  # E|Z| for standard normal Z: expected abs move = 0.798 x SD


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def years(sessions: float) -> float:
    """Trading sessions -> year fraction."""
    return max(sessions, 0.0) / TRADING_DAYS


def bs_price(kind: str, spot: float, strike: float, t: float, vol: float, rate: float = 0.0) -> float:
    """Price of a European call ("CE") or put ("PE"). `t` in years, `vol` annualised."""
    kind = kind.upper()
    if kind not in ("CE", "PE"):
        raise ValueError(f"kind must be CE or PE, got {kind!r}")
    t = max(t, 0.0)
    df = math.exp(-rate * t)
    if t == 0.0 or vol <= 0.0:
        fwd_intrinsic = spot - strike * df
        return max(fwd_intrinsic, 0.0) if kind == "CE" else max(-fwd_intrinsic, 0.0)
    sd = vol * math.sqrt(t)
    d1 = (math.log(spot / strike) + (rate + 0.5 * vol * vol) * t) / sd
    d2 = d1 - sd
    if kind == "CE":
        return spot * norm_cdf(d1) - strike * df * norm_cdf(d2)
    return strike * df * norm_cdf(-d2) - spot * norm_cdf(-d1)


def _solve_vol(price_of_vol: Callable[[float], float], target: float,
               lo: float = 1e-4, hi: float = 5.0, tol: float = 1e-8) -> Optional[float]:
    """Bisection on a price that increases with vol; None if target is out of range."""
    if not price_of_vol(lo) - tol <= target <= price_of_vol(hi) + tol:
        return None
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if price_of_vol(mid) < target:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return 0.5 * (lo + hi)


def implied_vol(kind: str, price: float, spot: float, strike: float, t: float,
                rate: float = 0.0) -> Optional[float]:
    if t <= 0:
        return None
    return _solve_vol(lambda v: bs_price(kind, spot, strike, t, v, rate), price)


def straddle_implied_vol(straddle: float, spot: float, strike: float, t: float,
                         rate: float = 0.0) -> Optional[float]:
    """IV that reproduces an ATM straddle premium (call + put at `strike`)."""
    if t <= 0:
        return None
    return _solve_vol(
        lambda v: bs_price("CE", spot, strike, t, v, rate) + bs_price("PE", spot, strike, t, v, rate),
        straddle,
    )


@dataclass(frozen=True)
class OptionLeg:
    kind: str     # "CE" or "PE"
    strike: float
    qty: int      # +n long, -n short


def structure_value(legs: Iterable[OptionLeg], spot: float, t: float, vol: float, rate: float = 0.0) -> float:
    """Net value per unit: positive = net debit (you pay), negative = net credit."""
    return sum(leg.qty * bs_price(leg.kind, spot, leg.strike, t, vol, rate) for leg in legs)


def expiry_payoff(legs: Iterable[OptionLeg], spot: float) -> float:
    total = 0.0
    for leg in legs:
        intrinsic = max(spot - leg.strike, 0.0) if leg.kind == "CE" else max(leg.strike - spot, 0.0)
        total += leg.qty * intrinsic
    return total


def max_loss(legs: Iterable[OptionLeg], net_debit: float) -> float:
    """Worst expiry loss per unit for a structure entered at `net_debit` (negative for a credit).

    Returns math.inf when the structure is net short calls (unbounded upside loss).
    """
    legs = list(legs)
    if sum(leg.qty for leg in legs if leg.kind == "CE") < 0:
        return math.inf
    # Payoff is piecewise linear with kinks at the strikes; beyond the top strike the
    # slope is the net call quantity (>= 0 here), so the worst case is at 0 or a strike.
    points = [0.0] + sorted({leg.strike for leg in legs})
    worst = min(expiry_payoff(legs, s) - net_debit for s in points)
    return max(0.0, -worst)
