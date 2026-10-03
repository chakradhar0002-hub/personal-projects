"""Turn the rules into a dated checklist for one stock: run-up entry, Day-1, Result Day, Day+1."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .config import StrategyConfig
from .strategy import EventInputs, TradePlan
from .timeline import EventTimeline, Timing

ENTRY_WINDOW = "14:45-15:20"
NOT_RECOMMENDED = "see docs/REAL_DATA_RESULTS.md"


@dataclass
class DayPlan:
    label: str
    day: date
    role: str
    tasks: list[str]


def _event_line(plan: TradePlan, cfg: StrategyConfig) -> str:
    a = plan.assessment
    verdict = f"verdict {a.view.value}" + (f", IM/HM {a.ratio:.2f}" if a and a.ratio is not None else "")
    if not cfg.recommend_event_trade:
        return (f"no trade across the numbers: condors/straddles held through results lost money after costs "
                f"({verdict}; {NOT_RECOMMENDED})")
    if not plan.is_trade:
        return "NO event trade - " + "; ".join(plan.notes)
    return (f"enter {plan.setup.replace('_', ' ').lower()} at {ENTRY_WINDOW} "
            f"(re-price with live quotes; {verdict})")


def _runup_exit(runup: Optional[TradePlan]) -> list[str]:
    if runup is None or not runup.is_trade:
        return []
    return ["SELL the IV run-up straddle at 15:00-15:25 - this close is the last one before the numbers"]


def build_playbook(timeline: EventTimeline, plan: TradePlan, cfg: Optional[StrategyConfig] = None,
                   runup: Optional[TradePlan] = None, runup_entry: Optional[date] = None) -> list[DayPlan]:
    cfg = cfg or StrategyConfig()
    tl = timeline
    entry_on_result_day = tl.pre_event_session == tl.result_day   # AMC on a trading day
    event_live = cfg.recommend_event_trade and plan.is_trade

    setup = [
        "confirm the board-meeting date and when results usually hit (before open / market hours / after close)",
        f"eligibility: not in F&O ban (MWPL < {cfg.max_mwpl_pct:.0f}%), ATM spread <= {cfg.max_atm_spread_pct:g}% of mid",
        "no futures or naked options for direction across the numbers",
    ]
    reaction_tasks = []
    if tl.timing is Timing.DURING:
        reaction_tasks.append("no new orders from 30 min before the board meeting until 15 min after the results hit")
    if event_live:
        reaction_tasks.append("manage the event trade by its exit rules - it must be flat by the close")
    if cfg.recommend_directional:
        reaction_tasks += [
            f"opening-range trade after the first {cfg.opening_range_minutes} min, out by {cfg.intraday_exit}",
            "after the close: run `classify` on the reaction candle for the follow-through plan",
        ]
        follow_tasks = ["execute the follow-through plan from `classify`; MUTED or MIXED: no trade"]
    else:
        reaction_tasks.append("no directional trade: the opening-range trade is untested - paper-trade it only")
        follow_tasks = [f"no trade: the Day+1 follow-through lost money even before costs ({NOT_RECOMMENDED})"]

    days: list[DayPlan] = []
    if runup_entry is not None and runup is not None:
        tasks = ([f"BUY the IV run-up straddle at {ENTRY_WINDOW} (see the trade below)"] if runup.is_trade
                 else ["no IV run-up trade - " + "; ".join(runup.notes)])
        days.append(DayPlan("RUN-UP ENTRY", runup_entry,
                            f"{cfg.runup_entry_sessions} sessions before the last close before the numbers", tasks))
    if entry_on_result_day:
        days.append(DayPlan("DAY-1", tl.day_minus_1, "Setup", setup))
        days.append(DayPlan("RESULT DAY", tl.result_day, "Last session before the numbers (results after the close)",
                            _runup_exit(runup) + [_event_line(plan, cfg)]))
        days.append(DayPlan("DAY+1", tl.day_plus_1, "Reaction session", reaction_tasks))
    else:
        days.append(DayPlan("DAY-1", tl.day_minus_1, "Setup; last session before the numbers",
                            setup + _runup_exit(runup) + [_event_line(plan, cfg)]))
        role = {Timing.BMO: "Reaction session (results before the open)",
                Timing.DURING: "Reaction session (results during market hours)"}.get(
                    tl.timing, "Reaction session")
        if tl.result_day != tl.announce_date:
            role = f"Reaction session (results on {tl.announce_date:%a %d-%b}, a non-trading day)"
        days.append(DayPlan("RESULT DAY", tl.result_day, role, reaction_tasks))
        days.append(DayPlan("DAY+1", tl.day_plus_1, "After the reaction", follow_tasks))
    return days


def render_playbook(inp: EventInputs, timeline: EventTimeline, front_expiry: Optional[date],
                    plan: TradePlan, cfg: Optional[StrategyConfig] = None,
                    runup: Optional[TradePlan] = None, runup_entry: Optional[date] = None) -> str:
    cfg = cfg or StrategyConfig()
    a = plan.assessment
    tl = timeline
    lines = [
        f"F&O RESULTS PLAYBOOK - {inp.symbol}",
        f"Results: {tl.announce_date:%a %d-%b-%Y} ({tl.timing.value}) | "
        f"last close before the numbers: {tl.pre_event_session:%a %d-%b-%Y}"
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
    for d in build_playbook(timeline, plan, cfg, runup, runup_entry):
        lines.append(f"{d.label} ({d.day:%a %d-%b}) - {d.role}")
        lines += [f"  [ ] {t}" for t in d.tasks]
        lines.append("")
    if runup is not None:
        lines.append(runup.render())
    if cfg.recommend_event_trade:
        lines += ["", plan.render()]
    return "\n".join(lines)
