"""Reaction-session opening-range rules on intraday bars (e.g. 5-minute candles)."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Optional, Sequence

from .config import StrategyConfig


@dataclass(frozen=True)
class IntradayBar:
    time: time
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class IntradayTrade:
    setup: str          # GAP_AND_GO or FAILED_GAP
    direction: int      # +1 long, -1 short
    entry_time: time
    entry: float
    stop: float
    target: float
    exit_time: time
    exit: float
    outcome: str        # STOP / TARGET / TIME

    @property
    def r_multiple(self) -> float:
        risk = abs(self.entry - self.stop)
        return self.direction * (self.exit - self.entry) / risk if risk else 0.0


def load_intraday(path: "str | Path") -> list[IntradayBar]:
    """CSV with columns time (HH:MM), open, high, low, close, volume."""
    with open(path, newline="") as fh:
        return [IntradayBar(time.fromisoformat(r["time"]), float(r["open"]), float(r["high"]),
                            float(r["low"]), float(r["close"]), float(r["volume"]))
                for r in csv.DictReader(fh)]


def _add_minutes(t: time, minutes: int) -> time:
    return (datetime.combine(datetime.min, t) + timedelta(minutes=minutes)).time()


def run_reaction_session(bars: Sequence[IntradayBar], prev_close: float, hm: float,
                         cfg: Optional[StrategyConfig] = None, start: time = time(9, 15)) -> Optional[IntradayTrade]:
    """At most one opening-range trade on the reaction session.

    `start` is the market open for BMO/AMC results, or the release time for results out
    during market hours. Bars are assumed sorted and stamped with their start time.
    """
    cfg = cfg or StrategyConfig()
    or_end = _add_minutes(start, cfg.opening_range_minutes)
    exit_at = time.fromisoformat(cfg.intraday_exit)
    in_range = [b for b in bars if start <= b.time < or_end]
    later = [b for b in bars if or_end <= b.time]
    if not in_range or not later or hm <= 0:
        return None
    or_high = max(b.high for b in in_range)
    or_low = min(b.low for b in in_range)
    gap = in_range[0].open / prev_close - 1

    pv = vol = 0.0
    seen: list[float] = []
    for b in bars:
        if b.time >= or_end:
            break
        pv += (b.high + b.low + b.close) / 3 * b.volume
        vol += b.volume
        seen.append(b.volume)

    trade = None
    for i, b in enumerate(later):
        if b.time >= exit_at:
            return None
        avg_vol = sum(seen) / len(seen)
        pv += (b.high + b.low + b.close) / 3 * b.volume
        vol += b.volume
        seen.append(b.volume)
        vwap = pv / vol if vol else b.close
        heavy = b.volume >= cfg.orb_volume_mult * avg_vol
        if gap >= cfg.orb_min_gap_hm * hm and b.close > or_high and b.close > vwap and heavy:
            trade = ("GAP_AND_GO", 1, or_low)
        elif gap <= -cfg.orb_min_gap_hm * hm and b.close < or_low and b.close < vwap and heavy:
            trade = ("GAP_AND_GO", -1, or_high)
        elif gap >= cfg.fade_gap_hm * hm and b.close < or_low and b.close < vwap:
            trade = ("FAILED_GAP", -1, or_high)
        elif gap <= -cfg.fade_gap_hm * hm and b.close > or_high and b.close > vwap:
            trade = ("FAILED_GAP", 1, or_low)
        if trade:
            setup, direction, stop = trade
            entry = b.close
            target = entry + direction * cfg.target_r * abs(entry - stop)
            return _walk(setup, direction, b.time, entry, stop, target, later[i + 1:], exit_at, b)
    return None


def _walk(setup, direction, entry_time, entry, stop, target, bars, exit_at, last) -> IntradayTrade:
    for b in bars:
        if b.time >= exit_at:
            return IntradayTrade(setup, direction, entry_time, entry, stop, target, b.time, b.open, "TIME")
        hit_stop = b.low <= stop if direction > 0 else b.high >= stop
        hit_target = b.high >= target if direction > 0 else b.low <= target
        if hit_stop:   # assume the worse fill when both are inside one bar; gaps fill at the open
            fill = min(stop, b.open) if direction > 0 else max(stop, b.open)
            return IntradayTrade(setup, direction, entry_time, entry, stop, target, b.time, fill, "STOP")
        if hit_target:
            fill = max(target, b.open) if direction > 0 else min(target, b.open)
            return IntradayTrade(setup, direction, entry_time, entry, stop, target, b.time, fill, "TARGET")
        last = b
    return IntradayTrade(setup, direction, entry_time, entry, stop, target, last.time, last.close, "TIME")
