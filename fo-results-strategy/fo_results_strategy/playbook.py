"""Turn the rules into a dated Day-1 / Result Day / Day+1 checklist for one stock."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .config import StrategyConfig
from .strategy import EventInputs, TradePlan, VolView
from .timeline import EventTimeline, Timing

ENTRY_WINDOW = "14:45-15:20"


@dataclass
class DayPlan:
    label: str
    day: date
    role: str
    tasks: list[str]


def _event_line(plan: TradePlan) -> str:
    a = plan.assessment
    if not plan.is_trade:
        return "NO event trade - " + "; ".join(plan.notes)
    return (f"enter {plan.setup.replace('_', ' ').lower()} at {ENTRY_WINDOW} "
            f"(re-price with live quotes; verdict {a.view.value}, IM/HM {a.ratio:.2f})")


def build_playbook(timeline: EventTimeline, plan: TradePlan,
                   cfg: Optional[StrategyConfig] = None) -> list[DayPlan]:
    cfg = cfg or StrategyConfig()
    tl = timeline
    entry_on_result_day = tl.pre_event_session == tl.result_day   # AMC on a trading day
    vol_trade = plan.is_trade

    setup = [
        "confirm the board-meeting date and when results usually hit (before open / market hours / after close)",
        f"eligibility: not in F&O ban (MWPL < {cfg.max_mwpl_pct:.0f}%), ATM spread <= {cfg.max_atm_spread_pct:g}% of mid, "
        f">= {cfg.min_sessions_to_expiry} sessions from the reaction to expiry",
        "note the historical move (last 8 reactions), front/back ATM IV, 10-session run-up",
        "no fresh futures or naked options for direction across the numbers",
    ]
    reaction_tasks = []
    if tl.timing is Timing.DURING:
        reaction_tasks.append("no new orders from 30 min before the board meeting until 15 min after the results hit")
    if vol_trade:
        reaction_tasks.append("manage the event trade by its exit rules - it must be flat by the close")
    reaction_tasks += [
        f"opening-range trade: after the first {cfg.opening_range_minutes} min "
        f"(from the release time for intraday results), trade a break of the range in the gap's direction "
        "above/below VWAP, or a failed big gap back through the range",
        f"intraday exit by {cfg.intraday_exit}",
        "after the close: run `classify` on the reaction candle for the follow-through plan",
    ]
    follow_tasks = [
        "execute the follow-through plan (trigger / stop / target / time stop) from `classify`",
        "MUTED or MIXED reaction: no trade",
    ]

    cheap = plan.assessment is not None and plan.assessment.view is VolView.CHEAP
    runup_exit = ("close any earlier pre-result IV run-up longs into this close"
                  + (" (verdict CHEAP: they may be held through)" if cheap else " - the IV build is done"))

    days: list[DayPlan] = []
    if entry_on_result_day:
        days.append(DayPlan("DAY-1", tl.day_minus_1, "Setup", setup))
        days.append(DayPlan("RESULT DAY", tl.result_day, "Pre-event entry (results after the close)",
                            ["IV peaks into this close - re-check IM/HM with live quotes at 14:30",
                             _event_line(plan), runup_exit]))
        days.append(DayPlan("DAY+1", tl.day_plus_1, "Reaction session", reaction_tasks))
    else:
        days.append(DayPlan("DAY-1", tl.day_minus_1, "Setup + pre-event entry",
                            setup + [_event_line(plan), runup_exit]))
        role = {Timing.BMO: "Reaction session (results before the open)",
                Timing.DURING: "Reaction session (results during market hours)"}.get(
                    tl.timing, "Reaction session")
        if tl.result_day != tl.announce_date:
            role = f"Reaction session (results on {tl.announce_date:%a %d-%b}, a non-trading day)"
        days.append(DayPlan("RESULT DAY", tl.result_day, role, reaction_tasks))
        days.append(DayPlan("DAY+1", tl.day_plus_1, "Follow-through", follow_tasks))
    return days


def render_playbook(inp: EventInputs, timeline: EventTimeline, front_expiry: Optional[date],
                    plan: TradePlan, cfg: Optional[StrategyConfig] = None) -> str:
    cfg = cfg or StrategyConfig()
    a = plan.assessment
    tl = timeline
    lines = [
        f"F&O RESULTS PLAYBOOK - {inp.symbol}",
        f"Results: {tl.announce_date:%a %d-%b-%Y} ({tl.timing.value}) | "
        f"reaction session: {tl.reaction_session:%a %d-%b-%Y}"
        + (f" | front expiry: {front_expiry:%d-%b-%Y}" if front_expiry else ""),
        "",
        "KEY NUMBERS",
        f"  Spot {inp.spot:,.2f} | lot {inp.lot_size} | front IV {inp.front_iv:.1%} ({inp.front_days} sessions)"
        + (f" | back IV {inp.back_iv:.1%} ({inp.back_days} sessions)" if inp.back_iv else ""),
    ]
    if a and a.history:
        h = a.history
        lines.append(f"  Historical move (HM, last {h.count}): {h.mean_abs:.2%} | median {h.median_abs:.2%} | "
                     f"max {h.max_abs:.2%} | up {h.up_ratio:.0%}")
    if a and a.implied_move is not None:
        lines.append(f"  Implied move (IM): {a.implied_move:.2%} (1-SD {a.event_sd:.2%}, base vol {a.base_vol:.1%}) "
                     f"| IM/HM {a.ratio:.2f} -> {a.view.value}")
    elif a:
        lines.append(f"  Verdict: {a.view.value}")
    if inp.run_up is not None:
        lines.append(f"  Run-up into results ({cfg.runup_lookback} sessions): {inp.run_up:+.2%}")
    lines.append("")
    for d in build_playbook(timeline, plan, cfg):
        lines.append(f"{d.label} ({d.day:%a %d-%b}) - {d.role}")
        lines += [f"  [ ] {t}" for t in d.tasks]
        lines.append("")
    lines.append(plan.render())
    return "\n".join(lines)
