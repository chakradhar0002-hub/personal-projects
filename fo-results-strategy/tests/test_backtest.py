import contextlib
import io
import tempfile
import unittest
from datetime import date
from pathlib import Path

from fo_results_strategy.backtest import (DailyBar, EventRow, load_events, load_prices, reaction_index,
                                          run_backtest, simulate_follow_through)
from fo_results_strategy.cli import main
from fo_results_strategy.config import StrategyConfig
from fo_results_strategy.strategy import plan_follow_through
from fo_results_strategy.synthetic import generate
from fo_results_strategy.timeline import Timing

CFG = StrategyConfig()


def bar(d, o, h, l, c):
    return DailyBar(date(2026, 1, d), o, h, l, c, 1e6)


def long_plan():
    # trigger 1065, stop 1050, target 1087.5
    return plan_follow_through("T", 1000, 1040, 1065, 1035, 1060, 4e6, 1e6, 0.03, lot_size=100)


class FollowThroughSimTest(unittest.TestCase):
    def test_trigger_then_target(self):
        r = simulate_follow_through(long_plan(), [bar(5, 1062, 1090, 1058, 1085)], 100, CFG)
        self.assertEqual((r.entry, r.exit), (1065, 1087.5))
        self.assertGreater(r.r_multiple, 1.4)

    def test_stop_checked_before_target(self):
        r = simulate_follow_through(long_plan(), [bar(5, 1062, 1090, 1049, 1085)], 100, CFG)
        self.assertEqual(r.exit, 1050)
        self.assertLess(r.r_multiple, -1)

    def test_not_triggered_and_no_chase(self):
        self.assertIsNone(simulate_follow_through(long_plan(), [bar(5, 1055, 1064, 1050, 1060)], 100, CFG))
        self.assertIsNone(simulate_follow_through(long_plan(), [bar(5, 1075, 1080, 1070, 1078)], 100, CFG))

    def test_small_gap_through_fills_at_open_and_time_exit(self):
        r = simulate_follow_through(long_plan(), [bar(5, 1069, 1075, 1066, 1072)], 100, CFG)
        self.assertEqual((r.entry, r.exit), (1069, 1072))


class BacktestTest(unittest.TestCase):
    def test_reaction_index(self):
        dates = [date(2026, 1, d) for d in (5, 6, 7, 8, 9)]
        self.assertEqual(reaction_index(dates, date(2026, 1, 7), Timing.AMC), 3)
        self.assertEqual(reaction_index(dates, date(2026, 1, 7), Timing.BMO), 2)
        self.assertEqual(reaction_index(dates, date(2026, 1, 10), Timing.BMO), 5)   # no data yet

    def test_end_to_end_on_synthetic_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            prices, events = generate(tmp, seed=3, sessions=500)
            px, evs = load_prices(prices), load_events(events)
            report = run_backtest(px, evs, CFG)
        self.assertTrue(report.trades)
        self.assertEqual({s.setup for s in report.summaries} - {"SHORT_IRON_CONDOR", "LONG_STRADDLE", "LONG_FUT",
                                                                 "SHORT_FUT"}, set())
        # No look-ahead: nothing trades before a symbol has min_history_events past results.
        for sym in px:
            first_dates = sorted(e.announce_date for e in evs if e.symbol == sym)[:CFG.min_history_events]
            for t in report.trades:
                if t.symbol == sym:
                    self.assertNotIn(t.announce_date, first_dates)
        self.assertIn("avg R", report.render())

    def test_events_parse_expiry_and_base_iv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "events.csv")
            path.write_text("symbol,announce_date,timing,front_iv,front_days,post_iv,front_expiry,base_iv\n"
                            "xyz,2025-01-15,AMC,34,8,22,2025-01-30,21.5\n")
            ev = load_events(path)[0]
        self.assertEqual((ev.symbol, ev.front_expiry, ev.base_iv), ("XYZ", date(2025, 1, 30), 0.215))

    def test_events_without_ivs_only_test_follow_through(self):
        with tempfile.TemporaryDirectory() as tmp:
            prices, events = generate(tmp, seed=3, sessions=500)
            evs = [EventRow(e.symbol, e.announce_date, e.timing, lot_size=e.lot_size) for e in load_events(events)]
            report = run_backtest(load_prices(prices), evs, CFG)
        self.assertTrue(all(t.setup.endswith("_FUT") for t in report.trades))


class CliTest(unittest.TestCase):
    def run_cli(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(main(list(argv)), 0)
        return buf.getvalue()

    def test_plan(self):
        out = self.run_cli("plan", "--symbol", "demo", "--date", "2026-10-15", "--timing", "AMC", "--spot", "1500",
                           "--lot-size", "550", "--strike-step", "10", "--hist-moves", "3.1,-2.4,4.2,-1.8,2.7,-3.5,2.2,-3.3",
                           "--front-iv", "34", "--back-iv", "26", "--capital", "2500000")
        self.assertIn("RUN-UP ENTRY (Thu 08-Oct)", out)
        self.assertIn("RESULT DAY (Thu 15-Oct) - Last session before the numbers", out)
        self.assertIn("SELL the IV run-up straddle", out)
        self.assertIn("LONG_STRADDLE_RUNUP", out)
        self.assertIn("no trade across the numbers", out)        # event trade tested negative
        self.assertNotIn("SHORT_IRON_CONDOR", out)

    def test_plan_from_straddle(self):
        out = self.run_cli("plan", "--symbol", "demo", "--date", "2026-10-15", "--timing", "BMO", "--spot", "1500",
                           "--lot-size", "550", "--hist-moves", "3.1,-2.4,4.2,-1.8", "--straddle", "75", "--back-iv", "26")
        self.assertIn("DAY-1 (Wed 14-Oct) - Setup; last session before the numbers", out)
        self.assertIn("RUN-UP ENTRY (Wed 07-Oct)", out)

    def test_classify_and_demo(self):
        out = self.run_cli("classify", "--symbol", "x", "--prev-close", "1000", "--open", "1040", "--high", "1065",
                           "--low", "1035", "--close", "1060", "--volume", "4000000", "--avg-volume", "1000000",
                           "--hm", "3")
        self.assertIn("LONG_FUT", out)
        with tempfile.TemporaryDirectory() as tmp:
            out = self.run_cli("demo", "--out-dir", tmp)
            self.assertTrue(Path(tmp, "prices.csv").exists())
        self.assertIn("event verdicts", out)


if __name__ == "__main__":
    unittest.main()
