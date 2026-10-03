import unittest
from datetime import time

from fo_results_strategy.intraday import IntradayBar, run_reaction_session


def bars(rows, start=(9, 15)):
    out, h, m = [], *start
    for o, hi, lo, c, v in rows:
        out.append(IntradayBar(time(h, m), o, hi, lo, c, v))
        m += 5
        h, m = h + m // 60, m % 60
    return out


class OpeningRangeTest(unittest.TestCase):
    def test_gap_and_go_long_hits_target(self):
        day = bars([(1040, 1048, 1036, 1045, 900), (1045, 1047, 1038, 1042, 700), (1042, 1046, 1040, 1044, 500),
                    (1044, 1052, 1043, 1051, 900),     # 09:30 breakout above OR high 1048
                    (1051, 1060, 1050, 1058, 600), (1058, 1080, 1057, 1078, 800)])
        t = run_reaction_session(day, prev_close=1000, hm=0.03)
        self.assertEqual((t.setup, t.direction, t.entry, t.stop), ("GAP_AND_GO", 1, 1051, 1036))
        self.assertEqual(t.outcome, "TARGET")
        self.assertAlmostEqual(t.r_multiple, 1.5)

    def test_failed_gap_up_goes_short(self):
        day = bars([(1050, 1056, 1046, 1049, 900), (1049, 1052, 1044, 1046, 700), (1046, 1048, 1043, 1045, 500),
                    (1045, 1046, 1030, 1032, 400),     # breaks OR low 1043 and VWAP, light volume is fine for fades
                    (1032, 1060, 1031, 1058, 900)])    # squeezes through the stop
        t = run_reaction_session(day, prev_close=1000, hm=0.03)
        self.assertEqual((t.setup, t.direction, t.stop), ("FAILED_GAP", -1, 1056))
        self.assertEqual(t.outcome, "STOP")
        self.assertAlmostEqual(t.r_multiple, -1.0)

    def test_small_gap_no_trade(self):
        day = bars([(1003, 1006, 1001, 1004, 900), (1004, 1005, 1002, 1003, 700), (1003, 1004, 1002, 1003, 500),
                    (1003, 1010, 1003, 1009, 2000), (1009, 1012, 1008, 1011, 800)])
        self.assertIsNone(run_reaction_session(day, prev_close=1000, hm=0.03))

    def test_intraday_release_uses_release_time(self):
        day = bars([(1000, 1001, 999, 1000, 300)] * 6 + [(1040, 1048, 1036, 1045, 900), (1045, 1047, 1038, 1042, 700),
                    (1042, 1046, 1040, 1044, 500), (1044, 1052, 1043, 1051, 1500), (1051, 1080, 1050, 1078, 800)])
        t = run_reaction_session(day, prev_close=1000, hm=0.03, start=time(9, 45))
        self.assertEqual((t.entry_time, t.stop), (time(10, 0), 1036))


if __name__ == "__main__":
    unittest.main()
