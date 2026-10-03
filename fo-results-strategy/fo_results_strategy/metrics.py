"""The key numbers: historical move, implied (event) move, reaction-candle shape."""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Optional, Sequence

from .pricing import SQRT_2_OVER_PI, TRADING_DAYS


@dataclass(frozen=True)
class MoveStats:
    """Stats of past reaction moves (fractions, e.g. 0.034 = 3.4%)."""
    count: int
    mean_abs: float     # the "historical move" (HM)
    median_abs: float
    max_abs: float
    up_ratio: float     # share of reactions that closed up


def move_stats(moves: Sequence[float]) -> Optional[MoveStats]:
    moves = [m for m in moves if m is not None]
    if not moves:
        return None
    absolute = [abs(m) for m in moves]
    return MoveStats(
        count=len(moves),
        mean_abs=sum(absolute) / len(absolute),
        median_abs=statistics.median(absolute),
        max_abs=max(absolute),
        up_ratio=sum(1 for m in moves if m > 0) / len(moves),
    )


def base_vol_from_term_structure(front_iv: float, front_days: int,
                                 back_iv: float, back_days: int) -> Optional[float]:
    """'Normal' (ex-event) vol implied by two expiries that both include the event.

    front_iv^2 * f = base^2 * (f-1) + event_var * 252   (same for the back month), so
    base^2 = (back_iv^2 * b - front_iv^2 * f) / (b - f).
    """
    if back_days <= front_days:
        return None
    var = (back_iv ** 2 * back_days - front_iv ** 2 * front_days) / (back_days - front_days)
    return math.sqrt(var) if var > 0 else None


def event_move_sd(front_iv: float, front_days: int, base_vol: float) -> float:
    """One-SD move the options price for the reaction session (fraction).

    Total variance to the front expiry minus normal diffusion on the other sessions.
    `front_days` = sessions from the entry close to expiry, including the reaction session.
    """
    total = front_iv ** 2 * front_days / TRADING_DAYS
    other = base_vol ** 2 * max(front_days - 1, 0) / TRADING_DAYS
    return math.sqrt(max(total - other, 0.0))


def implied_move(front_iv: float, front_days: int, base_vol: float) -> float:
    """Expected absolute reaction move priced by options (IM) - comparable to the historical move."""
    return SQRT_2_OVER_PI * event_move_sd(front_iv, front_days, base_vol)


def realized_vol(closes: Sequence[float], window: int = 20) -> Optional[float]:
    """Annualised close-to-close vol of the last `window` returns."""
    if len(closes) < window + 1:
        return None
    tail = closes[-(window + 1):]
    rets = [math.log(b / a) for a, b in zip(tail[:-1], tail[1:])]
    return statistics.stdev(rets) * math.sqrt(TRADING_DAYS)


def close_location(high: float, low: float, close: float) -> float:
    """Where the close sits in the day's range: 0 = low, 1 = high."""
    if high <= low:
        return 0.5
    return min(max((close - low) / (high - low), 0.0), 1.0)
