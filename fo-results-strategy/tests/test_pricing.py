import math
import unittest

from fo_results_strategy.pricing import (OptionLeg, bs_price, implied_vol, max_loss, straddle_implied_vol,
                                         structure_value)


class PricingTest(unittest.TestCase):
    def test_known_value(self):
        self.assertAlmostEqual(bs_price("CE", 100, 100, 1.0, 0.2), 7.9656, places=4)

    def test_put_call_parity(self):
        s, k, t, v, r = 1520, 1500, 0.05, 0.31, 0.06
        lhs = bs_price("CE", s, k, t, v, r) - bs_price("PE", s, k, t, v, r)
        self.assertAlmostEqual(lhs, s - k * math.exp(-r * t), places=8)

    def test_expired_is_intrinsic(self):
        self.assertEqual(bs_price("CE", 110, 100, 0, 0.3), 10)
        self.assertEqual(bs_price("PE", 110, 100, 0, 0.3), 0)

    def test_implied_vol_round_trip(self):
        price = bs_price("PE", 980, 1000, 10 / 252, 0.42, 0.06)
        self.assertAlmostEqual(implied_vol("PE", price, 980, 1000, 10 / 252, 0.06), 0.42, places=5)
        straddle = bs_price("CE", 1000, 1000, 0.04, 0.37) + bs_price("PE", 1000, 1000, 0.04, 0.37)
        self.assertAlmostEqual(straddle_implied_vol(straddle, 1000, 1000, 0.04), 0.37, places=5)

    def test_implied_vol_rejects_impossible_price(self):
        self.assertIsNone(implied_vol("CE", 0.5, 120, 100, 0.1))   # below intrinsic

    def test_iron_condor_max_loss_is_width_minus_credit(self):
        legs = [OptionLeg("CE", 110, -1), OptionLeg("CE", 115, 1), OptionLeg("PE", 90, -1), OptionLeg("PE", 85, 1)]
        net = structure_value(legs, 100, 0.03, 0.5)
        self.assertLess(net, 0)
        self.assertAlmostEqual(max_loss(legs, net), 5 + net, places=9)

    def test_straddle_max_loss_is_debit_and_naked_call_unbounded(self):
        legs = [OptionLeg("CE", 100, 1), OptionLeg("PE", 100, 1)]
        self.assertAlmostEqual(max_loss(legs, 7.0), 7.0)
        self.assertEqual(max_loss([OptionLeg("CE", 100, -1)], -3.0), math.inf)


if __name__ == "__main__":
    unittest.main()
