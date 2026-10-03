import unittest
from datetime import date, datetime

from fo_results_strategy.backtest import (DailyBar, EventRow, OptionQuotes, replay_event_trade, replay_runup,
                                          short_straddle_pct, snap_to_listed)
from fo_results_strategy.config import StrategyConfig
from fo_results_strategy.pricing import bs_price, years
from fo_results_strategy.realdata import (OptionQuote, atm_iv, atm_straddle_iv, bhavcopy_urls, load_results_file,
                                          merge_events, parity_spot, parse_bhavcopy, price_factor, strike_step,
                                          timing_from_ist)
from fo_results_strategy.strategy import EventInputs, plan_event_trade
from fo_results_strategy.timeline import Timing

from .test_metrics import ivs

OLD = """INSTRUMENT,SYMBOL,EXPIRY_DT,STRIKE_PR,OPTION_TYP,OPEN,HIGH,LOW,CLOSE,SETTLE_PR,CONTRACTS,VAL_INLAKH,OPEN_INT,CHG_IN_OI,TIMESTAMP,
FUTSTK,XYZ,25-Jan-2024,0,XX,1,1,1,1500,1500,10,1,1,1,01-JAN-2024,
OPTSTK,XYZ,25-Jan-2024,1500,CE,30,35,28,31.5,31.5,120,1,1,1,01-JAN-2024,
OPTSTK,XYZ,25-Jan-2024,1500,PE,30,35,28,29,29,0,1,1,1,01-JAN-2024,
OPTSTK,ABC,25-Jan-2024,100,CE,3,3,3,3,3,5,1,1,1,01-JAN-2024,
"""
NEW = """TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,FininstrmActlXpryDt,StrkPric,OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,LastPric,PrvsClsgPric,UndrlygPric,SttlmPric,OpnIntrst,ChngInOpnIntrst,TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd,SsnId,NewBrdLotQty,Rmks,Rsvd1,Rsvd2,Rsvd3,Rsvd4
2025-01-02,2025-01-02,FO,NSE,STF,1,,XYZ,,2025-01-30,2025-01-30,,,XYZ25JANFUT,1,1,1,1500,1,1,1500,1500,1,1,1,1,1,F1,500,,,,,
2025-01-02,2025-01-02,FO,NSE,STO,2,,XYZ,,2025-01-30,2025-01-30,1520.00,PE,XYZ25JAN1520PE,1,1,1,40.5,1,1,1500,40.5,1,1,7,1,1,F1,500,,,,,
"""


class ParsingTest(unittest.TestCase):
    def test_old_format_options_only(self):
        rows = parse_bhavcopy(OLD, date(2024, 1, 1), {"XYZ"})
        self.assertEqual(len(rows), 2)
        ce = rows[0]
        self.assertEqual((ce.kind, ce.strike, ce.close, ce.expiry), ("CE", 1500, 31.5, date(2024, 1, 25)))
        self.assertTrue(ce.traded)
        self.assertFalse(rows[1].traded)   # zero contracts

    def test_udiff_format(self):
        rows = parse_bhavcopy(NEW, date(2025, 1, 2))
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0].symbol, rows[0].kind, rows[0].strike, rows[0].volume), ("XYZ", "PE", 1520, 7))

    def test_urls_switch_format(self):
        self.assertIn("fo01JAN2024bhav", bhavcopy_urls(date(2024, 1, 1))[0])
        self.assertIn("BhavCopy_NSE_FO_0_0_0_20250102", bhavcopy_urls(date(2025, 1, 2))[0])

    def test_timing_from_release_time(self):
        self.assertIs(timing_from_ist(datetime(2025, 4, 10, 16, 6)), Timing.AMC)
        self.assertIs(timing_from_ist(datetime(2025, 1, 22, 14, 15)), Timing.DURING)
        self.assertIs(timing_from_ist(datetime(2023, 4, 24, 7, 16)), Timing.BMO)
        self.assertIs(timing_from_ist(datetime(2025, 1, 22, 5, 30)), Timing.UNKNOWN)


def chain(day, expiry, spot, iv, sessions, strikes, volume=10):
    out = []
    for k in strikes:
        for kind in ("CE", "PE"):
            px = round(bs_price(kind, spot, k, years(sessions), iv, 0.06), 2)
            out.append(OptionQuote("XYZ", day, expiry, kind, k, px, px, volume))
    return out


class ResultsFileTest(unittest.TestCase):
    def test_load_and_merge(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "results.csv")
            path.write_text("symbol,announce_date,announce_time,timing\n"
                            "tcs,2025-07-10,16:05,\n"
                            "sbin,2025-08-08,,DURING\n"
                            "infy,2025-07-17,,\n")
            own = load_results_file(path)
        self.assertIs(timing_from_ist(own["TCS"][0]), Timing.AMC)
        self.assertIs(timing_from_ist(own["SBIN"][0]), Timing.DURING)
        self.assertIs(timing_from_ist(own["INFY"][0]), Timing.UNKNOWN)
        yahoo = [datetime(2025, 4, 10, 16, 6), datetime(2025, 7, 10, 9, 0)]
        merged = merge_events(yahoo, own["TCS"])
        self.assertEqual(merged, [datetime(2025, 4, 10, 16, 6), datetime(2025, 7, 10, 16, 5)])


class PriceFactorTest(unittest.TestCase):
    def test_parity_spot_and_factor(self):
        q = chain(date(2025, 1, 2), date(2025, 1, 30), 1503, 0.31, 19, range(1400, 1610, 10))
        s = parity_spot(q, date(2025, 1, 2), 0.06)
        self.assertAlmostEqual(s, 1503, delta=3)
        self.assertEqual(price_factor(s, 1500), 1.0)
        self.assertEqual(price_factor(s, 1503 / 10), 10.0)    # history adjusted for a later 1:10 change
        self.assertEqual(price_factor(s, 1503 / 2), 2.0)
        self.assertIsNone(price_factor(s, 1300))               # unexplained mismatch (ratio 1.16)
        self.assertIsNone(price_factor(None, 1500))


class IvAndReplayTest(unittest.TestCase):
    def test_atm_straddle_iv_and_step(self):
        q = chain(date(2025, 1, 2), date(2025, 1, 30), 1503, 0.31, 19, range(1400, 1610, 10))
        self.assertAlmostEqual(atm_straddle_iv(q, date(2025, 1, 30), 1503, 19, 0.06), 0.31, places=2)
        self.assertEqual(strike_step([q_.strike for q_ in q], 1503), 10)
        untraded = [OptionQuote(x.symbol, x.day, x.expiry, x.kind, x.strike, x.close, x.settle, 0) for x in q]
        self.assertIsNone(atm_straddle_iv(untraded, date(2025, 1, 30), 1503, 19, 0.06))
        # Only an OTM call and an OTM put traded (different strikes): single-leg fallback.
        legs = [x for x in untraded if (x.kind, x.strike) not in (("CE", 1510), ("PE", 1490))]
        legs += [x for x in q if (x.kind, x.strike) in (("CE", 1510), ("PE", 1490))]
        self.assertIsNone(atm_straddle_iv(legs, date(2025, 1, 30), 1503, 19, 0.06))
        self.assertAlmostEqual(atm_iv(legs, date(2025, 1, 30), 1503, 19, 0.06), 0.31, places=2)

    def test_replay_condor_at_quotes(self):
        pre_d, rx_d, exp = date(2025, 1, 15), date(2025, 1, 16), date(2025, 1, 30)
        front, back = ivs(0.22, 0.048, 8, 29)
        hist = [0.031, -0.024, 0.042, -0.018, 0.027, -0.035, 0.022, -0.033]
        plan = plan_event_trade(EventInputs("XYZ", 1500, front, 8, hist, 550, 10, back, 29))
        self.assertEqual(plan.setup, "SHORT_IRON_CONDOR")
        listed = [k for k in range(1300, 1710, 20)]           # only 20-wide strikes listed
        quotes = OptionQuotes()
        for q in chain(pre_d, exp, 1500, front, 8, listed) + chain(rx_d, exp, 1510, 0.22, 7, listed):
            quotes.add(q.symbol, q.day, q.expiry, q.kind, q.strike, q.close, q.settle, q.volume)
        snapped = snap_to_listed(plan, quotes.strikes("XYZ", pre_d, exp))
        self.assertTrue(all(k % 20 == 0 for k in snapped))
        self.assertGreater(snapped[1], snapped[0])
        self.assertLess(snapped[3], snapped[2])
        ev = EventRow("XYZ", pre_d, Timing.AMC, front, 8, back, 29, 0.22, 550, 10, exp)
        pre = DailyBar(pre_d, 1495, 1505, 1490, 1500, 1e6)
        rx = DailyBar(rx_d, 1508, 1520, 1500, 1510, 3e6)
        res, status = replay_event_trade(plan, ev, pre, rx, quotes, StrategyConfig())
        self.assertEqual(status, "replayed")
        self.assertGreater(res.pnl_per_lot, 0)                # small move + IV crush
        self.assertLess(res.entry, 0)                         # credit
        self.assertGreater(short_straddle_pct(ev, pre, rx, quotes), 0)

    def test_replay_runup_buys_before_and_sells_before_the_numbers(self):
        exp = date(2025, 1, 30)
        days = [date(2025, 1, d) for d in (6, 7, 8, 9, 10, 13, 14, 15, 16)]
        bars = [DailyBar(d, 1500, 1505, 1495, 1500, 1e6) for d in days]
        r = 8                                    # reaction session index; pre-results close = days[7]
        quotes = OptionQuotes()
        # IV 24% five sessions before (13 sessions to expiry), 36% at the pre-results close (8 sessions)
        for q in chain(days[2], exp, 1500, 0.24, 13, range(1450, 1560, 10)) + \
                chain(days[7], exp, 1500, 0.36, 8, range(1450, 1560, 10)):
            quotes.add(q.symbol, q.day, q.expiry, q.kind, q.strike, q.close, q.settle, q.volume)
        ev = EventRow("XYZ", days[8], Timing.BMO, 0.34, 8, None, None, 0.22, 550, 10, exp)
        res, status = replay_runup(ev, bars, r, quotes, StrategyConfig())
        self.assertEqual(status, "replayed")
        self.assertEqual((res.entry_date, res.exit_date), (days[2], days[7]))
        self.assertGreater(res.r_multiple, 0.05)          # IV build beats five sessions of decay
        far = EventRow("XYZ", days[8], Timing.BMO, 0.34, 20, None, None, 0.22, 550, 10, exp)
        self.assertEqual(replay_runup(far, bars, r, quotes, StrategyConfig())[1], "front expiry too far")

    def test_replay_skips_unlisted(self):
        hist = [0.031, -0.024, 0.042, -0.018, 0.027, -0.035, 0.022, -0.033]
        front, back = ivs(0.22, 0.048, 8, 29)
        plan = plan_event_trade(EventInputs("XYZ", 1500, front, 8, hist, 550, 10, back, 29))
        self.assertIsNone(snap_to_listed(plan, [1500.0]))


if __name__ == "__main__":
    unittest.main()
