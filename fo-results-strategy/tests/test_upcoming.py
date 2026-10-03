import unittest
from dataclasses import replace
from datetime import date

from fo_results_strategy.config import StrategyConfig
from fo_results_strategy.timeline import Timing, TradingCalendar
from fo_results_strategy.upcoming import actions_by_day, open_runups, price_event, schedule_event, usual_timing

from .test_realdata import chain

CAL = TradingCalendar([date(2026, 10, 2)])
CFG = StrategyConfig(capital=5_000_000)
DAYS = [date(2026, 10, 5), date(2026, 10, 6), date(2026, 10, 7)]
EXP = date(2026, 10, 27)


def event(symbol, announce, timing, spot=1000.0):
    ev = schedule_event(symbol, announce, True, timing, "test", CAL, CFG)
    quotes = [replace(q, symbol=symbol) for q in chain(date(2026, 10, 1), EXP, spot, 0.30, 18, range(900, 1110, 10))]
    price_event(ev, quotes, date(2026, 10, 1), 500, CAL, CFG, spot)
    return ev


class UpcomingTest(unittest.TestCase):
    def test_usual_timing(self):
        rows = [{"symbol": "A", "timing": "AMC"}] * 8 + [{"symbol": "A", "timing": "DURING"}] + \
               [{"symbol": "B", "timing": "AMC"}] * 5 + [{"symbol": "B", "timing": "DURING"}] * 4
        t = usual_timing(rows)
        self.assertIs(t["A"][0], Timing.AMC)
        self.assertIs(t["B"][0], Timing.UNKNOWN)     # mixed: treated as during market hours

    def test_dates(self):
        amc = event("HCL", date(2026, 10, 12), Timing.AMC)        # sell Mon 12, buy 5 sessions earlier
        self.assertEqual((amc.last_close, amc.runup_entry), (date(2026, 10, 12), date(2026, 10, 5)))
        during = event("NEST", date(2026, 10, 15), Timing.DURING)  # sell Wed 14 (Day-1)
        self.assertEqual((during.last_close, during.runup_entry), (date(2026, 10, 14), date(2026, 10, 7)))
        sat = event("AXIS", date(2026, 10, 17), Timing.AMC)        # Saturday results: sell Friday
        self.assertEqual((sat.last_close, sat.runup_entry), (date(2026, 10, 16), date(2026, 10, 9)))
        tcs = event("TCS", date(2026, 10, 8), Timing.AMC)          # entry across the 2-Oct holiday
        self.assertEqual(tcs.runup_entry, date(2026, 9, 30))
        self.assertEqual(amc.front_expiry, EXP)
        self.assertTrue(amc.plan.is_trade)

    def test_actions(self):
        evs = [event("HCL", date(2026, 10, 12), Timing.AMC), event("NEST", date(2026, 10, 15), Timing.DURING),
               event("TCS", date(2026, 10, 8), Timing.AMC)]
        acts = actions_by_day(evs, DAYS, CFG)
        self.assertTrue(acts[DAYS[0]][0].startswith("BUY  HCL") or acts[DAYS[0]][1].startswith("BUY  HCL"))
        self.assertTrue(any(a.startswith("MISSED TCS") for a in acts[DAYS[0]]))
        self.assertTrue(any(a.startswith("BUY  NEST") for a in acts[DAYS[2]]))
        self.assertEqual(acts[DAYS[1]], [])
        self.assertEqual(open_runups(evs, DAYS[2]), ["HCL", "NEST", "TCS"])

    def test_far_expiry_is_skipped(self):
        ev = schedule_event("X", date(2026, 10, 1), True, Timing.AMC, "test", CAL, CFG)
        quotes = [replace(q, symbol="X") for q in
                  chain(date(2026, 9, 24), date(2026, 10, 27), 1000, 0.3, 22, range(900, 1110, 10))]
        price_event(ev, quotes, date(2026, 9, 24), 500, CAL, CFG, 1000)
        self.assertFalse(ev.plan.is_trade)               # 17 sessions from the exit to expiry


if __name__ == "__main__":
    unittest.main()
