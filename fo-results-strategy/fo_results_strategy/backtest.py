"""Event-study backtest of the event (volatility) trade and the follow-through trade on daily data.

Inputs are two CSVs (see examples/):
  prices.csv  date,symbol,open,high,low,close,volume
  events.csv  symbol,announce_date,timing[,front_iv,front_days,back_iv,back_days,post_iv,lot_size,strike_step]
IVs are in percent. Without front_iv/front_days/post_iv only the follow-through trade is tested.

Option legs are priced with Black-Scholes at one flat IV per expiry (no skew); that is a
model of the option P&L, not a replay of real quotes - see docs/STRATEGY.md, section 10.
"""
from __future__ import annotations

import csv
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional, Sequence

from .config import StrategyConfig
from .metrics import move_stats, realized_vol
from .pricing import bs_price, structure_value, years
from .strategy import EventInputs, TradePlan, plan_event_trade, plan_follow_through
from .timeline import Timing


@dataclass(frozen=True)
class DailyBar:
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class EventRow:
    symbol: str
    announce_date: date
    timing: Timing
    front_iv: Optional[float] = None    # fractions after loading
    front_days: Optional[int] = None
    back_iv: Optional[float] = None
    back_days: Optional[int] = None
    post_iv: Optional[float] = None
    lot_size: int = 1
    strike_step: Optional[float] = None


@dataclass
class TradeResult:
    symbol: str
    announce_date: date
    setup: str
    entry_date: date
    exit_date: date
    entry: float
    exit: float
    pnl_per_lot: float      # rupees per lot, after costs
    r_multiple: float       # pnl / planned max loss
    detail: str = ""


@dataclass
class SetupSummary:
    setup: str
    trades: int
    win_rate: float
    avg_r: float
    total_r: float
    profit_factor: float
    max_drawdown_r: float
    pnl_per_lot: float


@dataclass
class BacktestReport:
    trades: list[TradeResult]
    summaries: list[SetupSummary]
    counts: dict[str, Counter] = field(default_factory=dict)

    def render(self) -> str:
        out = []
        for name, counter in self.counts.items():
            out.append(f"{name}: " + (", ".join(f"{k} {v}" for k, v in sorted(counter.items())) or "none"))
        if not self.trades:
            out.append("no trades: each symbol needs price data around at least "
                       "min_history_events earlier results before it is traded")
        out.append("")
        head = f"{'setup':<22}{'trades':>7}{'win%':>7}{'avg R':>8}{'total R':>9}{'PF':>6}{'maxDD R':>9}{'Rs/lot':>12}"
        out.append(head)
        out.append("-" * len(head))
        for s in self.summaries:
            pf = f"{s.profit_factor:.2f}" if s.profit_factor != float("inf") else "inf"
            out.append(f"{s.setup:<22}{s.trades:>7}{s.win_rate:>7.0%}{s.avg_r:>8.2f}{s.total_r:>9.1f}"
                       f"{pf:>6}{s.max_drawdown_r:>9.1f}{s.pnl_per_lot:>12,.0f}")
        return "\n".join(out)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def _opt_float(v: Optional[str], scale: float = 1.0) -> Optional[float]:
    return float(v) / scale if v not in (None, "") else None


def _opt_int(v: Optional[str]) -> Optional[int]:
    return int(float(v)) if v not in (None, "") else None


def load_prices(path: "str | Path") -> dict[str, list[DailyBar]]:
    out: dict[str, list[DailyBar]] = defaultdict(list)
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            out[r["symbol"].strip().upper()].append(DailyBar(
                date.fromisoformat(r["date"]), float(r["open"]), float(r["high"]),
                float(r["low"]), float(r["close"]), float(r.get("volume") or 0)))
    for bars in out.values():
        bars.sort(key=lambda b: b.date)
    return dict(out)


def load_events(path: "str | Path") -> list[EventRow]:
    rows = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            rows.append(EventRow(
                symbol=r["symbol"].strip().upper(),
                announce_date=date.fromisoformat(r["announce_date"]),
                timing=Timing.parse(r.get("timing")),
                front_iv=_opt_float(r.get("front_iv"), 100),
                front_days=_opt_int(r.get("front_days")),
                back_iv=_opt_float(r.get("back_iv"), 100),
                back_days=_opt_int(r.get("back_days")),
                post_iv=_opt_float(r.get("post_iv"), 100),
                lot_size=_opt_int(r.get("lot_size")) or 1,
                strike_step=_opt_float(r.get("strike_step")),
            ))
    return sorted(rows, key=lambda e: (e.symbol, e.announce_date))


def write_trades(trades: Sequence[TradeResult], path: "str | Path") -> None:
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(TradeResult.__dataclass_fields__))
        w.writeheader()
        for t in trades:
            row = asdict(t)
            for k in ("entry", "exit", "pnl_per_lot", "r_multiple"):
                row[k] = round(row[k], 4)
            w.writerow(row)


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def reaction_index(dates: Sequence[date], announce: date, timing: Timing) -> int:
    """Index of the first session that trades the numbers."""
    return bisect_right(dates, announce) if timing is Timing.AMC else bisect_left(dates, announce)


def simulate_event_trade(plan: TradePlan, ev: EventRow, pre: DailyBar, reaction: DailyBar,
                         cfg: StrategyConfig) -> TradeResult:
    legs = plan.option_legs()
    t0 = years(ev.front_days)
    t1 = years(ev.front_days - 1)
    exit_spot = reaction.open if cfg.vol_exit_at == "open" else reaction.close
    entry_val = structure_value(legs, pre.close, t0, ev.front_iv, cfg.risk_free_rate)
    exit_val = structure_value(legs, exit_spot, t1, ev.post_iv, cfg.risk_free_rate)
    slip = sum(
        abs(l.qty) * (bs_price(l.kind, pre.close, l.strike, t0, ev.front_iv, cfg.risk_free_rate)
                      + bs_price(l.kind, exit_spot, l.strike, t1, ev.post_iv, cfg.risk_free_rate))
        for l in legs) * cfg.option_slippage_pct / 100
    pnl = (exit_val - entry_val - slip) * ev.lot_size - cfg.brokerage_per_order * 2 * len(legs)
    risk = plan.risk_per_lot
    return TradeResult(ev.symbol, ev.announce_date, plan.setup, pre.date, reaction.date,
                       entry_val, exit_val, pnl, pnl / risk if risk else 0.0,
                       f"IM/HM {plan.assessment.ratio:.2f}; spot {pre.close:.2f}->{exit_spot:.2f}")


def simulate_follow_through(plan: TradePlan, bars: Sequence[DailyBar], lot_size: int,
                            cfg: StrategyConfig) -> Optional[TradeResult]:
    """Stop-order entry on the first bar; stop checked before target inside a bar (conservative)."""
    if not bars:
        return None
    d, trigger, stop, target = plan.direction, plan.trigger, plan.stop, plan.target
    risk = abs(trigger - stop)
    first = bars[0]
    if d * (first.open - trigger) >= 0:          # opened at/through the trigger
        if d * (first.open - trigger) > cfg.max_chase_r * risk:
            return None                          # too far beyond: do not chase
        entry = first.open
    elif (first.high >= trigger) if d > 0 else (first.low <= trigger):
        entry = trigger
    else:
        return None                              # never triggered
    exit_px, exit_bar = None, bars[-1]
    for i, b in enumerate(bars):
        hit_stop = b.low <= stop if d > 0 else b.high >= stop
        hit_target = b.high >= target if d > 0 else b.low <= target
        if hit_stop:
            exit_px = stop if i == 0 else (min(stop, b.open) if d > 0 else max(stop, b.open))
        elif hit_target:
            exit_px = target if i == 0 else (max(target, b.open) if d > 0 else min(target, b.open))
        if exit_px is not None:
            exit_bar = b
            break
    if exit_px is None:
        exit_px = exit_bar.close
    costs = (entry + exit_px) * cfg.futures_cost_bps / 1e4 * lot_size + 2 * cfg.brokerage_per_order
    pnl = d * (exit_px - entry) * lot_size - costs
    actual_risk = abs(entry - stop) * lot_size
    return TradeResult("", date.min, plan.setup, first.date, exit_bar.date, entry, exit_px, pnl,
                       pnl / actual_risk if actual_risk else 0.0, plan.reaction.type.value)


def run_backtest(prices: dict[str, list[DailyBar]], events: Sequence[EventRow],
                 cfg: Optional[StrategyConfig] = None) -> BacktestReport:
    cfg = cfg or StrategyConfig()
    trades: list[TradeResult] = []
    views, reactions = Counter(), Counter()
    by_symbol: dict[str, list[EventRow]] = defaultdict(list)
    for ev in events:
        by_symbol[ev.symbol].append(ev)

    for symbol, evs in by_symbol.items():
        bars = prices.get(symbol)
        if not bars:
            continue
        dates = [b.date for b in bars]
        closes = [b.close for b in bars]
        history: list[float] = []            # only results already known at each event: no look-ahead
        for ev in sorted(evs, key=lambda e: e.announce_date):
            r = reaction_index(dates, ev.announce_date, ev.timing)
            if r <= 0 or r >= len(bars):
                continue
            pre, reaction = bars[r - 1], bars[r]
            hist = move_stats(history[-cfg.history_window:])
            if hist and hist.count >= cfg.min_history_events:
                # Event (volatility) trade: entered at the pre-event close.
                if ev.front_iv and ev.front_days and ev.post_iv:
                    lb = cfg.runup_lookback
                    inp = EventInputs(
                        symbol, pre.close, ev.front_iv, ev.front_days, history, ev.lot_size, ev.strike_step,
                        ev.back_iv, ev.back_days,
                        base_vol=None if ev.back_iv else realized_vol(closes[:r], 20),
                        run_up=pre.close / bars[r - 1 - lb].close - 1 if r - 1 - lb >= 0 else None,
                    )
                    plan = plan_event_trade(inp, cfg)
                    views[plan.assessment.view.value] += 1
                    if plan.is_trade:
                        trades.append(simulate_event_trade(plan, ev, pre, reaction, cfg))
                # Follow-through trade: entered the session after the reaction session.
                window = [b.volume for b in bars[max(0, r - 20):r]]
                avg_vol = sum(window) / len(window) if window else 0.0
                ft = plan_follow_through(symbol, pre.close, reaction.open, reaction.high, reaction.low,
                                         reaction.close, reaction.volume, avg_vol, hist.mean_abs,
                                         ev.lot_size, cfg)
                reactions[ft.reaction.type.value] += 1
                if ft.is_trade:
                    res = simulate_follow_through(ft, bars[r + 1:r + 1 + cfg.post_hold_sessions], ev.lot_size, cfg)
                    if res:
                        res.symbol, res.announce_date = symbol, ev.announce_date
                        trades.append(res)
            history.append(reaction.close / pre.close - 1)

    trades.sort(key=lambda t: (t.entry_date, t.symbol))
    return BacktestReport(trades, summarize(trades), {"event verdicts": views, "reaction types": reactions})


def summarize(trades: Sequence[TradeResult]) -> list[SetupSummary]:
    groups: dict[str, list[TradeResult]] = defaultdict(list)
    for t in trades:
        groups[t.setup].append(t)
    out = []
    for setup in sorted(groups):
        ts = groups[setup]
        rs = [t.r_multiple for t in ts]
        gains = sum(r for r in rs if r > 0)
        losses = -sum(r for r in rs if r < 0)
        equity = peak = dd = 0.0
        for r in rs:
            equity += r
            peak = max(peak, equity)
            dd = max(dd, peak - equity)
        out.append(SetupSummary(setup, len(ts), sum(r > 0 for r in rs) / len(ts), sum(rs) / len(rs), sum(rs),
                                gains / losses if losses else float("inf"), dd, sum(t.pnl_per_lot for t in ts)))
    return out
