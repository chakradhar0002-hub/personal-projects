"""Synthetic prices + results calendar to exercise the backtester end to end.

The fake market is deliberately neutral: prices are a random walk with a jump on each
reaction session and NO post-result drift, and option IVs misprice the event at random
(fair on average). Backtest numbers on this data only prove the plumbing works - they
say nothing about the strategy's edge in the real market.
"""
from __future__ import annotations

import csv
import math
import random
from datetime import date
from pathlib import Path

from .timeline import Timing, TradingCalendar

SYMBOLS = ("ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOXTROT")


def generate(out_dir: "str | Path", seed: int = 7, start: date = date(2023, 1, 2),
             sessions: int = 900) -> tuple[Path, Path]:
    rng = random.Random(seed)
    cal = TradingCalendar()
    days = [cal.on_or_after(start)]
    while len(days) < sessions:
        days.append(cal.next_session(days[-1]))

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    prices_path, events_path = out / "prices.csv", out / "events.csv"
    price_rows, event_rows = [], []

    for sym in SYMBOLS:
        vol = rng.uniform(0.20, 0.35)                 # normal annualised vol
        event_sd = rng.uniform(0.025, 0.06)           # true 1-SD results move
        price = rng.uniform(200, 3000)
        lot = max(25, int(round(1_500_000 / price / 25)) * 25)
        base_volume = rng.uniform(1e6, 5e6)
        dsd = vol / math.sqrt(252)

        reaction_idx = {}
        i = rng.randint(30, 60)
        while i < sessions - 2:
            reaction_idx[i] = rng.choices([Timing.BMO, Timing.DURING, Timing.AMC], [0.15, 0.35, 0.5])[0]
            i += rng.randint(58, 68)

        for i, d in enumerate(days):
            prev = price
            if i in reaction_idx:
                jump = rng.gauss(0, event_sd) * (2.0 if rng.random() < 0.1 else 1.0)
                close = prev * math.exp(jump + rng.gauss(0, dsd))
                open_ = prev * (1 + jump * rng.uniform(0.4, 1.3))
                spread = abs(rng.gauss(0, 2 * dsd))
                volume = base_volume * (1.5 + 4 * abs(jump) / event_sd * rng.uniform(0.5, 1.0))
                timing = reaction_idx[i]
                announce = days[i - 1] if timing is Timing.AMC else d
                front_days = rng.randint(4, 18)
                back_days = front_days + 21
                base_iv = vol * rng.uniform(1.0, 1.15)
                priced_var = (event_sd * math.exp(rng.gauss(0, 0.25))) ** 2   # random mispricing
                front_iv = math.sqrt((base_iv ** 2 * (front_days - 1) / 252 + priced_var) * 252 / front_days)
                back_iv = math.sqrt((base_iv ** 2 * (back_days - 1) / 252 + priced_var) * 252 / back_days)
                post_iv = base_iv * rng.uniform(0.9, 1.05)
                event_rows.append([sym, announce.isoformat(), timing.value, f"{front_iv * 100:.2f}", front_days,
                                   f"{back_iv * 100:.2f}", back_days, f"{post_iv * 100:.2f}", lot, ""])
            else:
                close = prev * math.exp(rng.gauss(0, dsd))
                open_ = prev * (1 + rng.gauss(0, 0.25 * dsd))
                spread = abs(rng.gauss(0, 0.5 * dsd))
                volume = base_volume * math.exp(rng.gauss(0, 0.3))
            high = max(open_, close) * (1 + spread)
            low = min(open_, close) * (1 - spread)
            price_rows.append([d.isoformat(), sym, f"{open_:.2f}", f"{high:.2f}", f"{low:.2f}",
                               f"{close:.2f}", int(volume)])
            price = close

    with open(prices_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
        w.writerows(price_rows)
    with open(events_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["symbol", "announce_date", "timing", "front_iv", "front_days", "back_iv", "back_days",
                    "post_iv", "lot_size", "strike_step"])
        w.writerows(event_rows)
    return prices_path, events_path
