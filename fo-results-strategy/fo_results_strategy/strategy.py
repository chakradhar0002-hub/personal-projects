"""Decision rules: the event (volatility) trade and the post-result directional trade."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Sequence

from .config import StrategyConfig
from .metrics import MoveStats, base_vol_from_term_structure, close_location, event_move_sd, move_stats
from .pricing import SQRT_2_OVER_PI, OptionLeg, bs_price, max_loss, years


class VolView(str, Enum):
    RICH = "RICH"    # options overprice the event -> sell defined-risk premium
    CHEAP = "CHEAP"  # options underprice the event -> buy the straddle
    FAIR = "FAIR"    # no edge -> stay flat through the numbers
    SKIP = "SKIP"    # fails an eligibility filter


class ReactionType(str, Enum):
    CONTINUATION_UP = "CONTINUATION_UP"      # big up move, strong close, heavy volume -> buy follow-through
    CONTINUATION_DOWN = "CONTINUATION_DOWN"  # mirror -> sell follow-through
    FAILED_GAP_UP = "FAILED_GAP_UP"          # big gap up sold into, weak close -> fade short
    FAILED_GAP_DOWN = "FAILED_GAP_DOWN"      # big gap down bought, strong close -> fade long
    MUTED = "MUTED"                          # move too small to matter -> no trade
    MIXED = "MIXED"                          # no clean signal -> no trade


def default_strike_step(spot: float) -> float:
    """Rough NSE stock-option strike interval; pass the real one when you know it."""
    for limit, step in ((100, 1.0), (250, 2.5), (500, 5.0), (1000, 10.0), (2500, 20.0), (5000, 50.0)):
        if spot < limit:
            return step
    return 100.0


def round_to_step(x: float, step: float) -> float:
    return round(round(x / step) * step, 4)


def ceil_to_step(x: float, step: float) -> float:
    return round(math.ceil(x / step - 1e-9) * step, 4)


def floor_to_step(x: float, step: float) -> float:
    return round(math.floor(x / step + 1e-9) * step, 4)


@dataclass
class EventInputs:
    """What you know at the event-trade entry (Day-1 close, or Result Day close for AMC results)."""
    symbol: str
    spot: float
    front_iv: float                    # ATM IV of the front expiry (fraction, 0.34 = 34%)
    front_days: int                    # sessions from entry close to front expiry, incl. reaction session
    hist_moves: Sequence[float]        # signed past reaction moves, oldest first (fractions)
    lot_size: int = 1
    strike_step: Optional[float] = None
    back_iv: Optional[float] = None    # ATM IV of the next monthly expiry
    back_days: Optional[int] = None
    base_vol: Optional[float] = None   # explicit "normal" vol; overrides the term-structure estimate
    run_up: Optional[float] = None     # return over the last `runup_lookback` sessions into entry
    mwpl_pct: Optional[float] = None
    atm_spread_pct: Optional[float] = None
    sessions_to_expiry_after_reaction: Optional[int] = None


@dataclass
class EventAssessment:
    view: VolView
    implied_move: Optional[float] = None   # IM: expected absolute move priced by options
    event_sd: Optional[float] = None
    base_vol: Optional[float] = None
    history: Optional[MoveStats] = None    # history.mean_abs is the historical move (HM)
    ratio: Optional[float] = None          # IM / HM
    reasons: list[str] = field(default_factory=list)


@dataclass
class Leg:
    action: str                  # "BUY" / "SELL"
    instrument: str              # "CE" / "PE" / "FUT"
    strike: Optional[float] = None
    est_price: Optional[float] = None

    @property
    def qty(self) -> int:
        return 1 if self.action == "BUY" else -1


@dataclass
class Reaction:
    type: ReactionType
    move: float            # close vs pre-event close
    gap: float             # open vs pre-event close
    clv: float             # close location in the day's range
    volume_ratio: float    # volume vs 20-session average
    move_hm: float         # |move| in multiples of the historical move


@dataclass
class TradePlan:
    symbol: str
    phase: str                         # "EVENT" or "FOLLOW_THROUGH"
    setup: str                         # SHORT_IRON_CONDOR / LONG_STRADDLE / LONG_FUT / SHORT_FUT / NO_TRADE
    legs: list[Leg] = field(default_factory=list)
    lot_size: int = 1
    lots: int = 0
    net_premium: Optional[float] = None       # per unit: + debit paid, - credit received
    max_loss_per_unit: Optional[float] = None
    trigger: Optional[float] = None
    stop: Optional[float] = None
    target: Optional[float] = None
    entry: str = ""
    exits: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    assessment: Optional[EventAssessment] = None
    reaction: Optional[Reaction] = None

    @property
    def is_trade(self) -> bool:
        return self.setup != "NO_TRADE"

    @property
    def direction(self) -> int:
        return {"LONG_FUT": 1, "SHORT_FUT": -1}.get(self.setup, 0)

    @property
    def risk_per_lot(self) -> Optional[float]:
        if self.max_loss_per_unit is None:
            return None
        return self.max_loss_per_unit * self.lot_size

    def option_legs(self) -> list[OptionLeg]:
        return [OptionLeg(l.instrument, l.strike, l.qty) for l in self.legs if l.instrument in ("CE", "PE")]

    def render(self) -> str:
        out = [f"{self.phase} trade: {self.setup}"]
        for leg in self.legs:
            strike = f" {leg.strike:g}" if leg.strike is not None else ""
            price = f"  (est. {leg.est_price:.2f})" if leg.est_price is not None else ""
            out.append(f"    {leg.action:<4} {leg.instrument}{strike}{price}")
        if self.net_premium is not None:
            kind = "debit" if self.net_premium > 0 else "credit"
            out.append(f"    Net {kind}: {abs(self.net_premium):.2f}/share")
        if self.trigger is not None:
            out.append(f"    Trigger {self.trigger:.2f} | Stop {self.stop:.2f} | Target {self.target:.2f}")
        if self.risk_per_lot is not None and self.is_trade:
            out.append(f"    Max loss per lot: Rs {self.risk_per_lot:,.0f} (lot {self.lot_size}) -> size {self.lots} lot(s)")
        if self.entry:
            out.append(f"    Entry: {self.entry}")
        for rule in self.exits:
            out.append(f"    Exit:  {rule}")
        for note in self.notes:
            out.append(f"    Note:  {note}")
        return "\n".join(out)


# ---------------------------------------------------------------------------
# Event (volatility) trade
# ---------------------------------------------------------------------------

def assess_event(inp: EventInputs, cfg: Optional[StrategyConfig] = None) -> EventAssessment:
    """Compare the implied move (IM) with the historical move (HM) and pick a volatility view."""
    cfg = cfg or StrategyConfig()
    reasons: list[str] = []
    if inp.mwpl_pct is not None and inp.mwpl_pct >= cfg.max_mwpl_pct:
        reasons.append(f"MWPL at {inp.mwpl_pct:.0f}% (limit {cfg.max_mwpl_pct:.0f}%): F&O ban risk")
    if inp.atm_spread_pct is not None and inp.atm_spread_pct > cfg.max_atm_spread_pct:
        reasons.append(f"ATM option spread {inp.atm_spread_pct:.1f}% of mid (limit {cfg.max_atm_spread_pct:.1f}%): illiquid")
    if (inp.sessions_to_expiry_after_reaction is not None
            and inp.sessions_to_expiry_after_reaction < cfg.min_sessions_to_expiry):
        reasons.append("front expiry too close to the reaction session: use next month")

    history = move_stats(list(inp.hist_moves)[-cfg.history_window:])
    if history is None or history.count < cfg.min_history_events or history.mean_abs <= 0:
        have = history.count if history else 0
        reasons.append(f"only {have} past results (need {cfg.min_history_events})")

    base = inp.base_vol
    if base is None and inp.back_iv is not None and inp.back_days is not None:
        base = base_vol_from_term_structure(inp.front_iv, inp.front_days, inp.back_iv, inp.back_days)
    if base is None:
        reasons.append("no baseline vol: give the back-month IV or a normal-period IV")

    if reasons:
        return EventAssessment(VolView.SKIP, base_vol=base, history=history, reasons=reasons)

    sd = event_move_sd(inp.front_iv, inp.front_days, base)
    im = SQRT_2_OVER_PI * sd
    if im <= 0:
        return EventAssessment(VolView.SKIP, base_vol=base, history=history,
                               reasons=["options price no event premium: check the IV inputs"])
    ratio = im / history.mean_abs
    a = EventAssessment(VolView.FAIR, im, sd, base, history, ratio)
    if ratio >= cfg.rich_ratio:
        if history.max_abs > cfg.tail_multiple * im:
            a.reasons.append(f"options rich (IM/HM {ratio:.2f}) but a past reaction of {history.max_abs:.1%} "
                             f"is > {cfg.tail_multiple:g}x IM: tail risk, no short vol")
        else:
            a.view = VolView.RICH
            a.reasons.append(f"IM/HM {ratio:.2f} >= {cfg.rich_ratio:g}: options overprice the event")
    elif ratio <= cfg.cheap_ratio:
        a.view = VolView.CHEAP
        a.reasons.append(f"IM/HM {ratio:.2f} <= {cfg.cheap_ratio:g}: options underprice the event")
    else:
        a.reasons.append(f"IM/HM {ratio:.2f} is fair: no volatility edge, stay flat through the numbers")
    return a


def _no_trade(symbol: str, phase: str, notes: list[str], **kw) -> TradePlan:
    return TradePlan(symbol, phase, "NO_TRADE", notes=notes, **kw)


def plan_event_trade(inp: EventInputs, cfg: Optional[StrategyConfig] = None) -> TradePlan:
    """Build the trade carried across the announcement (or NO_TRADE)."""
    cfg = cfg or StrategyConfig()
    a = assess_event(inp, cfg)
    if a.view in (VolView.SKIP, VolView.FAIR):
        return _no_trade(inp.symbol, "EVENT", list(a.reasons), assessment=a, lot_size=inp.lot_size)

    step = inp.strike_step or default_strike_step(inp.spot)
    t = years(inp.front_days)

    def priced(action: str, kind: str, strike: float) -> Leg:
        return Leg(action, kind, strike, bs_price(kind, inp.spot, strike, t, inp.front_iv, cfg.risk_free_rate))

    notes = list(a.reasons)
    if a.view is VolView.RICH:
        im, hm = a.implied_move, a.history.mean_abs
        call_k = put_k = cfg.condor_short_k
        stretched = cfg.runup_stretch_hm * hm
        if inp.run_up is not None and inp.run_up >= stretched:
            put_k = cfg.condor_skew_k
            notes.append(f"stock ran up {inp.run_up:+.1%} into results: extra room on the put side")
        elif inp.run_up is not None and inp.run_up <= -stretched:
            call_k = cfg.condor_skew_k
            notes.append(f"stock fell {inp.run_up:+.1%} into results: extra room on the call side")
        short_call = ceil_to_step(inp.spot * (1 + call_k * im), step)
        short_put = floor_to_step(inp.spot * (1 - put_k * im), step)
        width = max(step, ceil_to_step(inp.spot * im * cfg.condor_wing_k, step))
        if short_put - width <= 0:
            return _no_trade(inp.symbol, "EVENT", notes + ["put wing below zero"], assessment=a)
        legs = [priced("SELL", "CE", short_call), priced("BUY", "CE", short_call + width),
                priced("SELL", "PE", short_put), priced("BUY", "PE", short_put - width)]
        setup = "SHORT_IRON_CONDOR"
        entry_note = "sell the condor as one order (limit at mid, improve 1 tick at a time)"
        exits = [
            "reaction session 09:30-10:30: buy back once the IV crush is in (spreads normalise after the first 15 min)",
            "take profit as soon as 50-60% of the credit can be bought back",
            "spot opens beyond a short strike: close the whole condor at once - the wing caps the loss, do not roll",
            "hard exit at the reaction-session close; never carry it further",
        ]
    else:  # CHEAP
        k = round_to_step(inp.spot, step)
        legs = [priced("BUY", "CE", k), priced("BUY", "PE", k)]
        setup = "LONG_STRADDLE"
        entry_note = "buy the ATM straddle (front expiry) as one order"
        exits = [
            "reaction open move >= IM: sell within the first 30 min (delta gain beats the IV crush)",
            "move < 0.5x IM by 10:00: close - the leftover time value bleeds all day",
            "hard exit at the reaction-session close",
        ]

    net = sum(l.qty * l.est_price for l in legs)
    if a.view is VolView.RICH:
        credit = -net
        if credit < cfg.min_credit_to_width * width:
            return _no_trade(inp.symbol, "EVENT",
                             notes + [f"credit {credit:.2f} < {cfg.min_credit_to_width:.0%} of wing width {width:g}: too thin"],
                             assessment=a, lot_size=inp.lot_size)
    plan = TradePlan(inp.symbol, "EVENT", setup, legs, inp.lot_size, net_premium=net, entry=entry_note,
                     exits=exits, notes=notes, assessment=a)
    plan.max_loss_per_unit = max_loss(plan.option_legs(), net)
    budget = cfg.capital * cfg.risk_per_event_pct / 100
    plan.lots = int(budget // plan.risk_per_lot) if plan.risk_per_lot > 0 else 0
    if plan.lots == 0:
        plan.notes.append(f"one lot risks Rs {plan.risk_per_lot:,.0f} > budget Rs {budget:,.0f}: skip, or accept the larger risk knowingly")
    return plan


# ---------------------------------------------------------------------------
# Pre-results IV run-up
# ---------------------------------------------------------------------------

def plan_runup_trade(symbol: str, spot: float, front_iv: float, expiry_sessions_after_exit: int,
                     lot_size: int = 1, strike_step: Optional[float] = None, mwpl_pct: Optional[float] = None,
                     atm_spread_pct: Optional[float] = None, cfg: Optional[StrategyConfig] = None) -> TradePlan:
    """Long ATM straddle bought `runup_entry_sessions` before the pre-results close and sold at that close.

    Option prices build into results faster than they decay; the trade is out before the numbers,
    so it never takes the gap. `expiry_sessions_after_exit` counts sessions from the pre-results close
    to the front expiry (the expiry must include the results).
    """
    cfg = cfg or StrategyConfig()
    n = cfg.runup_entry_sessions
    reasons = []
    if mwpl_pct is not None and mwpl_pct >= cfg.max_mwpl_pct:
        reasons.append(f"MWPL at {mwpl_pct:.0f}% (limit {cfg.max_mwpl_pct:.0f}%): F&O ban risk")
    if atm_spread_pct is not None and atm_spread_pct > cfg.max_atm_spread_pct:
        reasons.append(f"ATM option spread {atm_spread_pct:.1f}% of mid: illiquid")
    if expiry_sessions_after_exit > cfg.runup_max_expiry_sessions:
        reasons.append(f"front expiry {expiry_sessions_after_exit} sessions after the exit "
                       f"(max {cfg.runup_max_expiry_sessions}): the results premium is too small a part of the price")
    if expiry_sessions_after_exit < 1:
        reasons.append("front expiry is before the results: it holds no results premium")
    if reasons:
        return _no_trade(symbol, "RUN_UP", reasons, lot_size=lot_size)

    step = strike_step or default_strike_step(spot)
    k = round_to_step(spot, step)
    t = years(expiry_sessions_after_exit + n)
    legs = [Leg("BUY", kind, k, bs_price(kind, spot, k, t, front_iv, cfg.risk_free_rate)) for kind in ("CE", "PE")]
    debit = sum(l.est_price for l in legs)
    plan = TradePlan(
        symbol, "RUN_UP", "LONG_STRADDLE_RUNUP", legs, lot_size, net_premium=debit, max_loss_per_unit=debit,
        entry=f"buy the ATM straddle (front expiry) at 14:45-15:20, {n} sessions before the pre-results close",
        exits=["sell at the pre-results close (15:00-15:25): always out BEFORE the numbers",
               "do not roll it into an event trade - holding straddles through results lost money"],
        notes=[f"front expiry {expiry_sessions_after_exit} sessions after the exit; IV usually builds into results"],
    )
    budget = cfg.capital * cfg.risk_per_runup_pct / 100
    plan.lots = int(budget // plan.risk_per_lot) if plan.risk_per_lot > 0 else 0
    if plan.lots == 0:
        plan.notes.append(f"one lot costs Rs {plan.risk_per_lot:,.0f} > budget Rs {budget:,.0f}: skip")
    return plan


# ---------------------------------------------------------------------------
# Post-result directional trade
# ---------------------------------------------------------------------------

def classify_reaction(prev_close: float, open_: float, high: float, low: float, close: float,
                      volume: float, avg_volume: float, hm: float,
                      cfg: Optional[StrategyConfig] = None) -> Reaction:
    """Read the reaction-session candle against the stock's own historical move (hm)."""
    cfg = cfg or StrategyConfig()
    move = close / prev_close - 1
    gap = open_ / prev_close - 1
    clv = close_location(high, low, close)
    vr = volume / avg_volume if avg_volume > 0 else 0.0
    size = abs(move) / hm if hm > 0 else 0.0

    if move >= cfg.continuation_move_hm * hm and clv >= cfg.continuation_clv and vr >= cfg.continuation_volume_ratio:
        kind = ReactionType.CONTINUATION_UP
    elif move <= -cfg.continuation_move_hm * hm and clv <= 1 - cfg.continuation_clv and vr >= cfg.continuation_volume_ratio:
        kind = ReactionType.CONTINUATION_DOWN
    elif gap >= cfg.fade_gap_hm * hm and clv <= cfg.fade_clv and close < open_:
        kind = ReactionType.FAILED_GAP_UP
    elif gap <= -cfg.fade_gap_hm * hm and clv >= 1 - cfg.fade_clv and close > open_:
        kind = ReactionType.FAILED_GAP_DOWN
    elif max(abs(move), abs(gap)) < cfg.muted_move_hm * hm:
        kind = ReactionType.MUTED
    else:
        kind = ReactionType.MIXED
    return Reaction(kind, move, gap, clv, vr, size)


def plan_follow_through(symbol: str, prev_close: float, open_: float, high: float, low: float, close: float,
                        volume: float, avg_volume: float, hm: float, lot_size: int = 1,
                        cfg: Optional[StrategyConfig] = None) -> TradePlan:
    """Trade for the session after the reaction session, using stock futures."""
    cfg = cfg or StrategyConfig()
    r = classify_reaction(prev_close, open_, high, low, close, volume, avg_volume, hm, cfg)
    direction = {ReactionType.CONTINUATION_UP: 1, ReactionType.FAILED_GAP_DOWN: 1,
                 ReactionType.CONTINUATION_DOWN: -1, ReactionType.FAILED_GAP_UP: -1}.get(r.type)
    summary = (f"{r.type.value}: move {r.move:+.1%} ({r.move_hm:.1f}x HM), gap {r.gap:+.1%}, "
               f"close at {r.clv:.0%} of range, volume {r.volume_ratio:.1f}x avg")
    if direction is None:
        return _no_trade(symbol, "FOLLOW_THROUGH", [summary, "no clean follow-through setup: stay flat"],
                         reaction=r, lot_size=lot_size)

    mid = (high + low) / 2
    trigger = high if direction > 0 else low
    risk = abs(trigger - mid)
    target = trigger + direction * cfg.target_r * risk
    side = "above the reaction-day high" if direction > 0 else "below the reaction-day low"
    plan = TradePlan(
        symbol, "FOLLOW_THROUGH", "LONG_FUT" if direction > 0 else "SHORT_FUT",
        [Leg("BUY" if direction > 0 else "SELL", "FUT")], lot_size,
        max_loss_per_unit=risk, trigger=trigger, stop=mid, target=target, reaction=r,
        entry=(f"after 09:30, stop-order {side} ({trigger:.2f}); if the open is already more than "
               f"{cfg.max_chase_r:g}R beyond it, skip - do not chase"),
        exits=[f"stop at the reaction-day midpoint {mid:.2f}",
               f"target {cfg.target_r:g}R = {target:.2f}",
               f"time stop: close of session {cfg.post_hold_sessions} after the reaction"],
        notes=[summary],
    )
    pct = cfg.risk_per_directional_pct
    if r.type in (ReactionType.FAILED_GAP_UP, ReactionType.FAILED_GAP_DOWN):
        pct *= cfg.fade_size_factor
        plan.notes.append(f"failed-gap fade: half size; prior close {prev_close:.2f} is the gap-fill stretch target")
    budget = cfg.capital * pct / 100
    plan.lots = int(budget // plan.risk_per_lot) if plan.risk_per_lot > 0 else 0
    if plan.lots == 0:
        plan.notes.append(f"one futures lot risks Rs {plan.risk_per_lot:,.0f} > budget Rs {budget:,.0f}: "
                          "use an ITM option debit spread sized to the budget instead (IV is crushed now)")
    return plan
