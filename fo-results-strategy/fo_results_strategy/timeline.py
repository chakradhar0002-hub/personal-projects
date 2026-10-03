"""Map a results announcement to Day-1 / Result Day / Day+1, the reaction session and the expiry."""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from pathlib import Path
from typing import Iterable


class Timing(str, Enum):
    BMO = "BMO"          # results out before the 09:15 IST open
    DURING = "DURING"    # results released while the market is open
    AMC = "AMC"          # results after the 15:30 IST close
    UNKNOWN = "UNKNOWN"  # treated like DURING: enter on Day-1, never assume an extra session

    @classmethod
    def parse(cls, value: "str | Timing | None") -> "Timing":
        if isinstance(value, Timing):
            return value
        key = (value or "").strip().upper().replace("-", "_").replace(" ", "_")
        aliases = {
            "PRE": cls.BMO, "PRE_MARKET": cls.BMO, "BEFORE_OPEN": cls.BMO,
            "INTRADAY": cls.DURING, "MARKET_HOURS": cls.DURING, "LIVE": cls.DURING,
            "POST": cls.AMC, "POST_MARKET": cls.AMC, "AFTER_CLOSE": cls.AMC,
            "": cls.UNKNOWN,
        }
        if key in aliases:
            return aliases[key]
        return cls(key)


class TradingCalendar:
    """Weekdays minus exchange holidays (pass NSE's trading-holiday list)."""

    def __init__(self, holidays: Iterable[date] = ()):
        self.holidays = frozenset(holidays)

    def is_session(self, d: date) -> bool:
        return d.weekday() < 5 and d not in self.holidays

    def on_or_after(self, d: date) -> date:
        while not self.is_session(d):
            d += timedelta(days=1)
        return d

    def on_or_before(self, d: date) -> date:
        while not self.is_session(d):
            d -= timedelta(days=1)
        return d

    def next_session(self, d: date) -> date:
        return self.on_or_after(d + timedelta(days=1))

    def prev_session(self, d: date) -> date:
        return self.on_or_before(d - timedelta(days=1))

    def sessions_between(self, start: date, end: date) -> int:
        """Number of sessions in (start, end]."""
        count, d = 0, start
        while True:
            d = self.next_session(d)
            if d > end:
                return count
            count += 1


def load_holidays(path: "str | Path") -> list[date]:
    """One YYYY-MM-DD per line; blank lines and '#' comments ignored."""
    days = []
    for line in Path(path).read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            days.append(date.fromisoformat(line))
    return days


@dataclass(frozen=True)
class EventTimeline:
    announce_date: date
    timing: Timing
    day_minus_1: date
    result_day: date          # first session on/after the announcement date
    day_plus_1: date
    pre_event_session: date   # last close before the numbers are public: event-trade entry
    reaction_session: date    # first session that trades the numbers: event-trade exit

    @property
    def reaction_is_result_day(self) -> bool:
        return self.reaction_session == self.result_day


def build_timeline(announce_date: date, timing: "Timing | str", cal: TradingCalendar) -> EventTimeline:
    timing = Timing.parse(timing)
    result_day = cal.on_or_after(announce_date)
    day_minus_1 = cal.prev_session(result_day)
    day_plus_1 = cal.next_session(result_day)
    if timing is Timing.AMC and cal.is_session(announce_date):
        pre, reaction = result_day, day_plus_1
    else:
        # BMO / DURING / UNKNOWN, or any announcement on a weekend or holiday.
        pre, reaction = day_minus_1, result_day
    return EventTimeline(announce_date, timing, day_minus_1, result_day, day_plus_1, pre, reaction)


def monthly_expiry(year: int, month: int, cal: TradingCalendar, weekday: int = 1) -> date:
    """Last `weekday` of the month, moved to the previous session if that day is a holiday."""
    d = date(year, month, calendar.monthrange(year, month)[1])
    while d.weekday() != weekday:
        d -= timedelta(days=1)
    return cal.on_or_before(d)


def choose_expiries(reaction: date, cal: TradingCalendar, min_sessions_after: int = 3,
                    weekday: int = 1) -> tuple[date, date]:
    """(front, back) monthly expiries to trade: the front must leave `min_sessions_after`
    sessions after the reaction session (avoids expiry-week gamma and physical settlement)."""
    found: list[date] = []
    year, month = reaction.year, reaction.month
    while len(found) < 2:
        exp = monthly_expiry(year, month, cal, weekday)
        if found or (exp >= reaction and cal.sessions_between(reaction, exp) >= min_sessions_after):
            found.append(exp)
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return found[0], found[1]
