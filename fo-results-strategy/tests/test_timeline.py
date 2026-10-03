import unittest
from datetime import date

from fo_results_strategy.timeline import Timing, TradingCalendar, build_timeline, choose_expiries, monthly_expiry


class TimelineTest(unittest.TestCase):
    def setUp(self):
        self.cal = TradingCalendar()

    def test_after_close_reacts_next_session(self):
        tl = build_timeline(date(2026, 10, 15), "AMC", self.cal)        # Thursday
        self.assertEqual(tl.day_minus_1, date(2026, 10, 14))
        self.assertEqual(tl.pre_event_session, date(2026, 10, 15))
        self.assertEqual(tl.reaction_session, date(2026, 10, 16))
        self.assertEqual(tl.day_plus_1, date(2026, 10, 16))
        self.assertFalse(tl.reaction_is_result_day)

    def test_before_open_and_intraday_react_same_day(self):
        for timing in ("BMO", "during", "intraday", ""):
            tl = build_timeline(date(2026, 10, 15), timing, self.cal)
            self.assertEqual(tl.pre_event_session, date(2026, 10, 14))
            self.assertEqual(tl.reaction_session, date(2026, 10, 15))

    def test_saturday_results_react_monday(self):
        tl = build_timeline(date(2026, 10, 17), Timing.AMC, self.cal)
        self.assertEqual(tl.result_day, date(2026, 10, 19))
        self.assertEqual(tl.pre_event_session, date(2026, 10, 16))
        self.assertEqual(tl.reaction_session, date(2026, 10, 19))

    def test_holidays_are_skipped(self):
        cal = TradingCalendar([date(2026, 10, 16)])
        tl = build_timeline(date(2026, 10, 15), "AMC", cal)
        self.assertEqual(tl.reaction_session, date(2026, 10, 19))
        self.assertEqual(cal.sessions_between(date(2026, 10, 15), date(2026, 10, 20)), 2)

    def test_monthly_expiry_last_tuesday_and_holiday(self):
        self.assertEqual(monthly_expiry(2026, 10, self.cal), date(2026, 10, 27))
        cal = TradingCalendar([date(2026, 10, 27)])
        self.assertEqual(monthly_expiry(2026, 10, cal), date(2026, 10, 26))

    def test_expiry_rolls_when_reaction_is_in_expiry_week(self):
        self.assertEqual(choose_expiries(date(2026, 10, 16), self.cal), (date(2026, 10, 27), date(2026, 11, 24)))
        self.assertEqual(choose_expiries(date(2026, 10, 23), self.cal), (date(2026, 11, 24), date(2026, 12, 29)))


if __name__ == "__main__":
    unittest.main()
