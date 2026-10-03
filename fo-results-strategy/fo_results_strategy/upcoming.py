"""Action calendar for the next few sessions: which run-up straddles to buy or sell, and which results land.

Data: Yahoo's next results date for each stock, the company's usual release timing (from past results),
and the latest NSE F&O bhavcopy for spot, listed expiries, strikes and ATM IV.
"""
from __future__ import annotations

import csv
import json
import urllib.parse
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Sequence

from .config import StrategyConfig
from .realdata import (IST, Http, OptionQuote, Yahoo, atm_iv, current_lot_sizes, fetch_bhavcopy, parity_spot,
                       strike_step)
from .strategy import TradePlan, plan_runup_trade
from .timeline import EventTimeline, Timing, TradingCalendar, build_timeline


@dataclass
class UpcomingEvent:
    symbol: str
    announce: date
    confirmed: bool
    timing: Timing
    timing_note: str
    timeline: EventTimeline
    runup_entry: date
    front_expiry: Optional[date] = None
    expiry_sessions_after_exit: Optional[int] = None
    spot: Optional[float] = None
    lot: Optional[int] = None
    front_iv: Optional[float] = None
    plan: Optional[TradePlan] = None
    notes: list[str] = field(default_factory=list)

    @property
    def last_close(self) -> date:
        return self.timeline.pre_event_session


def usual_timing(rows: Sequence[dict], min_share: float = 0.75) -> dict[str, tuple[Timing, str]]:
    """Each company's usual release timing from past results rows (symbol, timing).

    A timing seen in at least `min_share` of past results is used; otherwise UNKNOWN, which the
    playbook treats like 'during market hours' (exit on Day-1, never assume an extra session).
    """
    seen: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        if r.get("timing"):
            seen[r["symbol"].upper()][r["timing"].upper()] += 1
    out = {}
    for sym, c in seen.items():
        timing, n = c.most_common(1)[0]
        total = sum(c.values())
        if n / total >= min_share:
            out[sym] = (Timing.parse(timing), f"{timing} in {n} of {total} past results")
        else:
            mix = ", ".join(f"{k} {v}" for k, v in c.most_common())
            out[sym] = (Timing.UNKNOWN, f"mixed history ({mix}): treated as during market hours")
    return out


def shift_sessions(d: date, n: int, cal: TradingCalendar) -> date:
    """Session `n` sessions before (n > 0) the session `d`."""
    for _ in range(n):
        d = cal.prev_session(d)
    return d


def schedule_event(symbol: str, announce: date, confirmed: bool, timing: Timing, timing_note: str,
                   cal: TradingCalendar, cfg: StrategyConfig) -> UpcomingEvent:
    tl = build_timeline(announce, timing, cal)
    return UpcomingEvent(symbol, announce, confirmed, tl.timing, timing_note, tl,
                         shift_sessions(tl.pre_event_session, cfg.runup_entry_sessions, cal))


def price_event(ev: UpcomingEvent, quotes: Sequence[OptionQuote], quote_day: date, lot: Optional[int],
                cal: TradingCalendar, cfg: StrategyConfig, spot: Optional[float] = None) -> None:
    """Fill in the front expiry, ATM IV and the run-up plan from the latest option chain."""
    ev.lot = lot
    ev.spot = spot or parity_spot(quotes, quote_day, cfg.risk_free_rate)
    if not quotes or not ev.spot:
        ev.notes.append("no option prices in the latest bhavcopy")
        return
    reaction = ev.timeline.reaction_session
    expiries = sorted({q.expiry for q in quotes if q.expiry >= reaction
                       and cal.sessions_between(reaction, q.expiry) >= cfg.min_sessions_to_expiry})
    if not expiries:
        ev.notes.append("no listed expiry far enough after the results")
        return
    ev.front_expiry = expiries[0]
    ev.expiry_sessions_after_exit = cal.sessions_between(ev.last_close, ev.front_expiry)
    ev.front_iv = atm_iv(quotes, ev.front_expiry, ev.spot, cal.sessions_between(quote_day, ev.front_expiry),
                         cfg.risk_free_rate)
    step = strike_step([q.strike for q in quotes if q.expiry == ev.front_expiry], ev.spot)
    if ev.front_iv is None:
        ev.notes.append("ATM options of the front expiry did not trade: price it live")
        return
    ev.plan = plan_runup_trade(ev.symbol, ev.spot, ev.front_iv, ev.expiry_sessions_after_exit,
                               lot or 1, step, cfg=cfg)


def open_runups(events: Sequence[UpcomingEvent], day: date) -> list[str]:
    """Run-up straddles held over the close of `day` if every planned entry was taken."""
    return sorted(e.symbol for e in events if e.plan is not None and e.plan.is_trade
                  and e.runup_entry <= day < e.last_close)


def actions_by_day(events: Sequence[UpcomingEvent], days: Sequence[date],
                   cfg: Optional[StrategyConfig] = None) -> dict[date, list[str]]:
    cfg = cfg or StrategyConfig()
    out: dict[date, list[str]] = {d: [] for d in days}
    first, last = days[0], days[-1]
    for ev in sorted(events, key=lambda e: (e.runup_entry, e.symbol)):
        tl, p = ev.timeline, ev.plan
        unconfirmed = "" if ev.confirmed else " (date NOT confirmed - check the board-meeting filing)"
        if first <= ev.runup_entry <= last:
            if p is not None and p.is_trade:
                leg = p.legs[0]
                size = (f"{p.lots} lot(s)" if p.lots else
                        f"0 lots (1 lot needs capital >= Rs {p.risk_per_lot / (cfg.risk_per_runup_pct / 100):,.0f})")
                out[ev.runup_entry].append(
                    f"BUY  {ev.symbol} run-up straddle: {leg.strike:g} CE + {leg.strike:g} PE, "
                    f"{ev.front_expiry:%d-%b} expiry, 14:45-15:20, est. debit {p.net_premium:.2f} "
                    f"x lot {p.lot_size} = Rs {p.risk_per_lot:,.0f}/lot -> {size}; "
                    f"sell {ev.last_close:%a %d-%b}{unconfirmed}")
            else:
                why = "; ".join(p.notes if p is not None else ev.notes) or "not priced"
                out[ev.runup_entry].append(f"SKIP {ev.symbol} run-up: {why}")
        elif ev.runup_entry < first <= ev.last_close:
            out[first].append(f"MISSED {ev.symbol} run-up entry ({ev.runup_entry:%a %d-%b}): don't buy late - "
                              "entries 1-3 sessions before lost money after costs")
        if first <= ev.last_close <= last:
            out[ev.last_close].append(f"SELL {ev.symbol} run-up straddle at 15:00-15:25 if you hold it: last close "
                                      f"before the numbers{unconfirmed}")
        if first <= tl.reaction_session <= last:
            out[tl.reaction_session].append(
                f"RESULTS {ev.symbol} ({ev.timing.value}, announced {ev.announce:%a %d-%b}): reaction session - "
                "no trade across the numbers")
    return out


def render(events: Sequence[UpcomingEvent], days: Sequence[date], quote_day: date, cfg: StrategyConfig,
           horizon: int = 15) -> str:
    acts = actions_by_day(events, days, cfg)
    lines = [f"F&O RESULTS - ACTIONS FOR {days[0]:%a %d-%b} TO {days[-1]:%a %d-%b-%Y}",
             f"Option prices from the NSE bhavcopy of {quote_day:%a %d-%b-%Y}; re-price live before every order.",
             f"Capital Rs {cfg.capital:,.0f}: run-up debit <= {cfg.risk_per_runup_pct:g}% per stock, "
             f"<= {cfg.max_runup_positions} open at once.", ""]
    for d in days:
        lines.append(f"{d:%a %d-%b}")
        lines += [f"  [ ] {a}" for a in acts[d]] or ["  nothing to do"]
        held = [s for s in open_runups(events, d) if any(e.symbol == s and e.runup_entry >= days[0] for e in events)]
        if held:
            over = f" - over the cap of {cfg.max_runup_positions}: keep the nearest expiries" \
                if len(held) > cfg.max_runup_positions else ""
            lines.append(f"  open after the close: {len(held)} run-up straddle(s) ({', '.join(held)}){over}")
        lines.append("")
    upcoming = [e for e in events if days[-1] < e.runup_entry or days[-1] < e.last_close]
    upcoming = sorted(upcoming, key=lambda e: (e.runup_entry, e.symbol))[:horizon]
    if upcoming:
        lines.append("COMING UP (next run-up entries)")
        lines.append(f"  {'stock':<12}{'results':<12}{'timing':<9}{'buy on':<11}{'sell on':<11}{'expiry':<10}status")
        for e in upcoming:
            if e.runup_entry < days[0]:
                status = "entry passed - skip"
            elif e.plan is not None and e.plan.is_trade:
                status = "trade"
            else:
                status = "skip: " + "; ".join((e.plan.notes if e.plan is not None else e.notes) or ["not priced"])
            lines.append(f"  {e.symbol:<12}{e.announce:%a %d-%b} {e.timing.value:<9}{e.runup_entry:%a %d-%b} "
                         f"{e.last_close:%a %d-%b} {e.front_expiry.strftime('%d-%b') if e.front_expiry else '-':<10}"
                         f"{status}{'' if e.confirmed else ' [date unconfirmed]'}")
        lines.append("")
    lines.append("Timing used per stock: " + "; ".join(f"{e.symbol} {e.timing_note}" for e in
                                                        sorted(events, key=lambda e: e.announce)[:horizon]))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Network pieces
# ---------------------------------------------------------------------------

def next_results_dates(http: Http, yahoo: Yahoo, symbols: Sequence[str]) -> dict[str, tuple[date, bool]]:
    """Next results date per symbol from Yahoo, with whether Yahoo marks it confirmed."""
    crumb = urllib.parse.quote(yahoo.crumb())
    out = {}
    for sym in symbols:
        try:
            raw = http.get(f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/"
                           f"{urllib.parse.quote(sym + '.NS')}?modules=calendarEvents&crumb={crumb}")
            earnings = json.loads(raw)["quoteSummary"]["result"][0]["calendarEvents"]["earnings"]
        except Exception:
            continue
        dates = earnings.get("earningsDate") or []
        if dates:
            d = datetime.fromtimestamp(dates[0]["raw"], IST).date()
            out[sym] = (d, not earnings.get("isEarningsDateEstimate", True))
    return out


def latest_bhavcopy(http: Http, today: date, cache_dir: Path, symbols: set,
                    lookback: int = 10) -> tuple[Optional[date], dict[str, list[OptionQuote]]]:
    for back in range(lookback):
        d = today - timedelta(days=back)
        if d.weekday() >= 5:
            continue
        rows = fetch_bhavcopy(http, d, cache_dir, symbols)
        if rows:
            per: dict[str, list[OptionQuote]] = defaultdict(list)
            for q in rows:
                per[q.symbol].append(q)
            return d, per
    return None, {}


def build_upcoming(symbols: Sequence[str], today: date, n_days: int, cal: TradingCalendar,
                   cfg: StrategyConfig, cache_dir: Path, history_rows: Sequence[dict],
                   own_dates: Optional[dict[str, tuple[date, bool, Optional[Timing]]]] = None,
                   log=print) -> tuple[list[UpcomingEvent], list[date], Optional[date]]:
    http = Http()
    yahoo = Yahoo(http)
    days = [cal.on_or_after(today)]
    while len(days) < n_days:
        days.append(cal.next_session(days[-1]))
    window_end = days[-1]
    for _ in range(25):                      # results far enough ahead to have a run-up entry soon
        window_end = cal.next_session(window_end)

    dates = next_results_dates(http, yahoo, symbols)
    for sym, (d, confirmed, _) in (own_dates or {}).items():
        dates[sym] = (d, confirmed)
    log(f"yahoo: next results date for {len(dates)} of {len(symbols)} stocks")
    timing_of = usual_timing(history_rows)
    events = []
    for sym, (d, confirmed) in dates.items():
        if not (days[0] - timedelta(days=10) <= d <= window_end):
            continue
        timing, note = timing_of.get(sym, (Timing.UNKNOWN, "no history: treated as during market hours"))
        own = (own_dates or {}).get(sym)
        if own and own[2] is not None:
            timing, note = own[2], "from your file"
        ev = schedule_event(sym, d, confirmed, timing, note, cal, cfg)
        if ev.last_close >= days[0] or ev.timeline.reaction_session >= days[0]:
            events.append(ev)

    quote_day, chains = latest_bhavcopy(http, today, cache_dir, {e.symbol for e in events})
    lots = current_lot_sizes(http)
    log(f"nse: option prices from {quote_day}, {len(events)} upcoming results in range")
    for ev in events:
        spot = None
        try:
            bars = yahoo.daily_bars(ev.symbol, quote_day - timedelta(days=10), quote_day + timedelta(days=1))
            spot = next((b[4] for b in reversed(bars) if b[0] == quote_day), None)
        except Exception:
            pass
        price_event(ev, chains.get(ev.symbol, []), quote_day, lots.get(ev.symbol), cal, cfg, spot)
    return events, days, quote_day


def load_history_rows(path: "str | Path") -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    with open(p, newline="") as fh:
        return list(csv.DictReader(fh))
