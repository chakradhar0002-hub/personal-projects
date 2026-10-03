"""Command line: plan / classify / orb / backtest / demo.

All percentages on the command line are in percent (34 = 34%).
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from datetime import date
from typing import Optional, Sequence

from .backtest import load_events, load_prices, run_backtest, write_trades
from .config import StrategyConfig
from .intraday import load_intraday, run_reaction_session
from .playbook import render_playbook
from .pricing import straddle_implied_vol, years
from .strategy import EventInputs, default_strike_step, plan_event_trade, plan_follow_through, round_to_step
from .synthetic import generate
from .timeline import Timing, TradingCalendar, build_timeline, choose_expiries, load_holidays


def _pct(v: Optional[float]) -> Optional[float]:
    return None if v is None else v / 100


def _pct_list(text: str) -> list[float]:
    return [float(x) / 100 for x in text.replace(";", ",").split(",") if x.strip()]


def _cmd_plan(args, cfg: StrategyConfig) -> int:
    cal = TradingCalendar(load_holidays(args.holidays) if args.holidays else ())
    tl = build_timeline(date.fromisoformat(args.date), args.timing, cal)
    front, back = choose_expiries(tl.reaction_session, cal, cfg.min_sessions_to_expiry, cfg.expiry_weekday)
    front_days = args.front_days or cal.sessions_between(tl.pre_event_session, front)
    back_days = args.back_days or cal.sessions_between(tl.pre_event_session, back)
    step = args.strike_step or default_strike_step(args.spot)

    front_iv = _pct(args.front_iv)
    if front_iv is None:
        if args.straddle is None:
            print("give --front-iv or --straddle", file=sys.stderr)
            return 2
        front_iv = straddle_implied_vol(args.straddle, args.spot, round_to_step(args.spot, step),
                                        years(front_days), cfg.risk_free_rate)
        if front_iv is None:
            print("straddle premium is outside no-arbitrage bounds", file=sys.stderr)
            return 2

    inp = EventInputs(
        symbol=args.symbol.upper(), spot=args.spot, front_iv=front_iv, front_days=front_days,
        hist_moves=_pct_list(args.hist_moves), lot_size=args.lot_size, strike_step=step,
        back_iv=_pct(args.back_iv), back_days=back_days if args.back_iv is not None else None,
        base_vol=_pct(args.base_iv), run_up=_pct(args.run_up), mwpl_pct=args.mwpl,
        atm_spread_pct=args.atm_spread,
        sessions_to_expiry_after_reaction=cal.sessions_between(tl.reaction_session, front),
    )
    plan = plan_event_trade(inp, cfg)
    print(render_playbook(inp, tl, front, plan, cfg))
    return 0


def _cmd_classify(args, cfg: StrategyConfig) -> int:
    plan = plan_follow_through(args.symbol.upper(), args.prev_close, args.open, args.high, args.low, args.close,
                               args.volume, args.avg_volume, args.hm / 100, args.lot_size, cfg)
    print(plan.render())
    return 0


def _cmd_orb(args, cfg: StrategyConfig) -> int:
    from datetime import time
    trade = run_reaction_session(load_intraday(args.bars), args.prev_close, args.hm / 100, cfg,
                                 time.fromisoformat(args.start))
    if trade is None:
        print("no opening-range setup")
    else:
        side = "LONG" if trade.direction > 0 else "SHORT"
        print(f"{trade.setup} {side}: entry {trade.entry:.2f} @ {trade.entry_time:%H:%M}, stop {trade.stop:.2f}, "
              f"target {trade.target:.2f} -> exit {trade.exit:.2f} @ {trade.exit_time:%H:%M} "
              f"({trade.outcome}, {trade.r_multiple:+.2f}R)")
    return 0


def _cmd_backtest(args, cfg: StrategyConfig) -> int:
    report = run_backtest(load_prices(args.prices), load_events(args.events), cfg)
    print(report.render())
    if args.out:
        write_trades(report.trades, args.out)
        print(f"\ntrades written to {args.out}")
    return 0


def _cmd_demo(args, cfg: StrategyConfig) -> int:
    prices, events = generate(args.out_dir, seed=args.seed)
    print(f"synthetic data: {prices}, {events}")
    print("NOTE: a neutral fake market - this checks the mechanics, not the edge.\n")
    report = run_backtest(load_prices(prices), load_events(events), cfg)
    print(report.render())
    return 0


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--capital", type=float, help="trading capital in rupees (default 10,00,000)")
    p = argparse.ArgumentParser(prog="fo-results", description="F&O results strategy: Day-1 / Result Day / Day+1")
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("plan", parents=[common], help="dated 3-day playbook and event trade for one stock")
    pl.add_argument("--symbol", required=True)
    pl.add_argument("--date", required=True, help="results (board meeting) date, YYYY-MM-DD")
    pl.add_argument("--timing", default="UNKNOWN", type=Timing.parse, help="BMO, DURING, AMC or UNKNOWN")
    pl.add_argument("--spot", type=float, required=True)
    pl.add_argument("--lot-size", type=int, required=True)
    pl.add_argument("--strike-step", type=float)
    pl.add_argument("--hist-moves", required=True, help="past reaction moves in %%, e.g. 3.1,-2.4,5.0,-1.8")
    pl.add_argument("--front-iv", type=float, help="front-expiry ATM IV in %%")
    pl.add_argument("--straddle", type=float, help="front-expiry ATM straddle premium (instead of --front-iv)")
    pl.add_argument("--back-iv", type=float, help="next-month ATM IV in %%")
    pl.add_argument("--base-iv", type=float, help="normal-period IV in %% if no back month")
    pl.add_argument("--front-days", type=int, help="override: sessions from entry close to front expiry")
    pl.add_argument("--back-days", type=int, help="override: sessions from entry close to back expiry")
    pl.add_argument("--run-up", type=float, help="return over the last 10 sessions in %%")
    pl.add_argument("--mwpl", type=float, help="MWPL utilisation %%")
    pl.add_argument("--atm-spread", type=float, help="ATM option bid-ask spread, %% of mid")
    pl.add_argument("--holidays", help="file of exchange holidays, one YYYY-MM-DD per line")

    cl = sub.add_parser("classify", parents=[common], help="read the reaction candle -> follow-through plan")
    cl.add_argument("--symbol", required=True)
    cl.add_argument("--prev-close", type=float, required=True, help="close before the numbers were public")
    for name in ("open", "high", "low", "close", "volume"):
        cl.add_argument(f"--{name}", type=float, required=True, help=f"reaction-session {name}")
    cl.add_argument("--avg-volume", type=float, required=True, help="20-session average volume before results")
    cl.add_argument("--hm", type=float, required=True, help="historical move in %%")
    cl.add_argument("--lot-size", type=int, default=1)

    ob = sub.add_parser("orb", parents=[common], help="opening-range trade on reaction-session intraday bars")
    ob.add_argument("--bars", required=True, help="CSV: time,open,high,low,close,volume")
    ob.add_argument("--prev-close", type=float, required=True)
    ob.add_argument("--hm", type=float, required=True, help="historical move in %%")
    ob.add_argument("--start", default="09:15", help="09:15, or the release time for intraday results")

    bt = sub.add_parser("backtest", parents=[common], help="backtest on your prices.csv + events.csv")
    bt.add_argument("--prices", required=True)
    bt.add_argument("--events", required=True)
    bt.add_argument("--out", help="write the trade list to this CSV")

    dm = sub.add_parser("demo", parents=[common], help="generate synthetic data and backtest it")
    dm.add_argument("--out-dir", default="demo_data")
    dm.add_argument("--seed", type=int, default=7)
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = StrategyConfig()
    if args.capital:
        cfg = replace(cfg, capital=args.capital)
    handler = {"plan": _cmd_plan, "classify": _cmd_classify, "orb": _cmd_orb,
               "backtest": _cmd_backtest, "demo": _cmd_demo}[args.cmd]
    return handler(args, cfg)
