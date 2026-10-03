import unittest

from fo_results_strategy.config import StrategyConfig
from fo_results_strategy.strategy import (EventInputs, ReactionType, VolView, assess_event, ceil_to_step,
                                          classify_reaction, floor_to_step, plan_event_trade, plan_follow_through)

from .test_metrics import ivs

HIST = [0.031, -0.024, 0.042, -0.018, 0.027, -0.035, 0.022, -0.033]   # HM = 2.9%


def inputs(event_sd, **kw):
    front, back = ivs(0.22, event_sd, 8, 29)
    base = dict(symbol="TEST", spot=1500, front_iv=front, front_days=8, hist_moves=HIST, lot_size=550,
                strike_step=10, back_iv=back, back_days=29)
    base.update(kw)
    return EventInputs(**base)


class AssessTest(unittest.TestCase):
    def test_rich_cheap_fair(self):
        self.assertEqual(assess_event(inputs(0.048)).view, VolView.RICH)    # IM 3.8% vs HM 2.9%
        self.assertEqual(assess_event(inputs(0.025)).view, VolView.CHEAP)   # IM 2.0%
        self.assertEqual(assess_event(inputs(0.037)).view, VolView.FAIR)    # IM 2.95%

    def test_tail_risk_blocks_short_vol(self):
        quiet_then_shock = [0.01, -0.01, 0.015, -0.012, 0.01, -0.011, 0.012, 0.08]   # HM 2.0%, max 8%
        a = assess_event(inputs(0.048, hist_moves=quiet_then_shock))   # IM 3.8%: rich, but 8% > 2x IM
        self.assertEqual(a.view, VolView.FAIR)
        self.assertIn("tail risk", a.reasons[0])

    def test_filters_skip(self):
        self.assertEqual(assess_event(inputs(0.048, mwpl_pct=90)).view, VolView.SKIP)
        self.assertEqual(assess_event(inputs(0.048, atm_spread_pct=9)).view, VolView.SKIP)
        self.assertEqual(assess_event(inputs(0.048, sessions_to_expiry_after_reaction=1)).view, VolView.SKIP)
        self.assertEqual(assess_event(inputs(0.048, hist_moves=HIST[:3])).view, VolView.SKIP)
        self.assertEqual(assess_event(inputs(0.048, back_iv=None)).view, VolView.SKIP)

    def test_explicit_base_vol_without_back_month(self):
        a = assess_event(inputs(0.048, back_iv=None, back_days=None, base_vol=0.22))
        self.assertEqual(a.view, VolView.RICH)
        self.assertAlmostEqual(a.event_sd, 0.048, places=9)


class EventPlanTest(unittest.TestCase):
    def test_condor_strikes_sit_outside_the_implied_move(self):
        cfg = StrategyConfig(capital=2_500_000)
        plan = plan_event_trade(inputs(0.048), cfg)
        self.assertEqual(plan.setup, "SHORT_IRON_CONDOR")
        im = plan.assessment.implied_move
        strikes = {(l.action, l.instrument): l.strike for l in plan.legs}
        self.assertGreaterEqual(strikes["SELL", "CE"], 1500 * (1 + 1.25 * im))
        self.assertLessEqual(strikes["SELL", "PE"], 1500 * (1 - 1.25 * im))
        self.assertGreater(strikes["BUY", "CE"], strikes["SELL", "CE"])
        self.assertLess(strikes["BUY", "PE"], strikes["SELL", "PE"])
        width = strikes["BUY", "CE"] - strikes["SELL", "CE"]
        self.assertAlmostEqual(plan.max_loss_per_unit, width + plan.net_premium, places=9)
        self.assertLessEqual(plan.lots * plan.risk_per_lot, cfg.capital * cfg.risk_per_event_pct / 100)
        self.assertGreater(plan.lots, 0)

    def test_run_up_widens_the_put_side(self):
        flat = plan_event_trade(inputs(0.048))
        stretched = plan_event_trade(inputs(0.048, run_up=0.06))
        put = lambda p: next(l.strike for l in p.legs if l.action == "SELL" and l.instrument == "PE")
        call = lambda p: next(l.strike for l in p.legs if l.action == "SELL" and l.instrument == "CE")
        self.assertLess(put(stretched), put(flat))
        self.assertEqual(call(stretched), call(flat))

    def test_cheap_buys_atm_straddle(self):
        plan = plan_event_trade(inputs(0.025))
        self.assertEqual(plan.setup, "LONG_STRADDLE")
        self.assertEqual({l.strike for l in plan.legs}, {1500})
        self.assertAlmostEqual(plan.max_loss_per_unit, plan.net_premium)

    def test_fair_is_no_trade(self):
        plan = plan_event_trade(inputs(0.037))
        self.assertFalse(plan.is_trade)
        self.assertEqual(plan.legs, [])

    def test_thin_credit_is_rejected(self):
        plan = plan_event_trade(inputs(0.048), StrategyConfig(min_credit_to_width=0.9))
        self.assertFalse(plan.is_trade)
        self.assertIn("too thin", plan.notes[-1])

    def test_rounding(self):
        self.assertEqual(ceil_to_step(1572.1, 10), 1580)
        self.assertEqual(ceil_to_step(1580.0, 10), 1580)
        self.assertEqual(floor_to_step(1427.9, 10), 1420)


class ReactionTest(unittest.TestCase):
    hm = 0.03

    def classify(self, o, h, l, c, vol=4e6):
        return classify_reaction(1000, o, h, l, c, vol, 1e6, self.hm).type

    def test_types(self):
        self.assertEqual(self.classify(1040, 1065, 1035, 1060), ReactionType.CONTINUATION_UP)
        self.assertEqual(self.classify(960, 965, 935, 940), ReactionType.CONTINUATION_DOWN)
        self.assertEqual(self.classify(1040, 1065, 1035, 1060, vol=1.2e6), ReactionType.MIXED)  # no volume
        self.assertEqual(self.classify(1045, 1050, 1005, 1012), ReactionType.FAILED_GAP_UP)
        self.assertEqual(self.classify(955, 995, 950, 990), ReactionType.FAILED_GAP_DOWN)
        self.assertEqual(self.classify(1005, 1012, 995, 1008), ReactionType.MUTED)
        self.assertEqual(self.classify(1030, 1040, 1010, 1025), ReactionType.MIXED)

    def test_follow_through_levels_and_sizing(self):
        cfg = StrategyConfig(capital=5_000_000)
        plan = plan_follow_through("TEST", 1000, 1040, 1065, 1035, 1060, 4e6, 1e6, self.hm, lot_size=500, cfg=cfg)
        self.assertEqual(plan.setup, "LONG_FUT")
        self.assertEqual((plan.trigger, plan.stop), (1065, 1050))
        self.assertAlmostEqual(plan.target, 1065 + 1.5 * 15)
        self.assertEqual(plan.lots, int(cfg.capital * cfg.risk_per_directional_pct / 100 // (15 * 500)))

    def test_fade_is_half_size_and_short(self):
        cfg = StrategyConfig(capital=5_000_000)
        plan = plan_follow_through("TEST", 1000, 1045, 1050, 1005, 1012, 4e6, 1e6, self.hm, lot_size=100, cfg=cfg)
        self.assertEqual(plan.setup, "SHORT_FUT")
        self.assertEqual(plan.trigger, 1005)
        self.assertGreater(plan.stop, plan.trigger)
        self.assertLess(plan.target, plan.trigger)
        full = cfg.capital * cfg.risk_per_directional_pct / 100
        self.assertEqual(plan.lots, int(full * 0.5 // plan.risk_per_lot))


if __name__ == "__main__":
    unittest.main()
