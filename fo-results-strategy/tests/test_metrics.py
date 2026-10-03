import math
import unittest

from fo_results_strategy.metrics import (base_vol_from_term_structure, close_location, event_move_sd, implied_move,
                                         move_stats, realized_vol)


def ivs(base, event_sd, f, b):
    """Front/back IVs a market would quote for a given base vol and event SD."""
    front = math.sqrt((base ** 2 * (f - 1) / 252 + event_sd ** 2) * 252 / f)
    back = math.sqrt((base ** 2 * (b - 1) / 252 + event_sd ** 2) * 252 / b)
    return front, back


class MetricsTest(unittest.TestCase):
    def test_term_structure_recovers_base_and_event(self):
        front, back = ivs(0.22, 0.05, 8, 29)
        base = base_vol_from_term_structure(front, 8, back, 29)
        self.assertAlmostEqual(base, 0.22, places=9)
        self.assertAlmostEqual(event_move_sd(front, 8, base), 0.05, places=9)
        self.assertAlmostEqual(implied_move(front, 8, base), 0.05 * math.sqrt(2 / math.pi), places=9)

    def test_term_structure_needs_later_back_month(self):
        self.assertIsNone(base_vol_from_term_structure(0.3, 10, 0.25, 10))

    def test_no_event_premium_gives_zero(self):
        self.assertEqual(event_move_sd(0.20, 10, 0.25), 0.0)

    def test_move_stats(self):
        s = move_stats([0.02, -0.04, 0.03, -0.01])
        self.assertAlmostEqual(s.mean_abs, 0.025)
        self.assertAlmostEqual(s.max_abs, 0.04)
        self.assertAlmostEqual(s.up_ratio, 0.5)
        self.assertIsNone(move_stats([]))

    def test_close_location_and_realized_vol(self):
        self.assertEqual(close_location(110, 100, 110), 1.0)
        self.assertEqual(close_location(100, 100, 100), 0.5)
        self.assertIsNone(realized_vol([100, 101], window=20))
        closes = [100 + i % 2 for i in range(30)]
        self.assertGreater(realized_vol(closes, 20), 0)


if __name__ == "__main__":
    unittest.main()
