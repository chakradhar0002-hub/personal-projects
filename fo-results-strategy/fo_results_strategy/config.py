"""All tunable thresholds of the results strategy in one place.

Every number here is a starting point, not a law: journal your trades and
re-fit these on your own data (see docs/STRATEGY.md, section 10).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyConfig:
    # --- Eligibility -------------------------------------------------------
    max_mwpl_pct: float = 80.0           # skip if market-wide position limit use is this high (ban at 95%)
    max_atm_spread_pct: float = 5.0      # skip if ATM option bid-ask spread > this % of mid
    min_history_events: int = 4          # past results needed before trusting the historical move
    history_window: int = 8              # last N results (2 years) used for the historical move
    min_sessions_to_expiry: int = 3      # sessions between reaction session and expiry (else next month)
    expiry_weekday: int = 1              # NSE monthly stock F&O expiry: last Tuesday (Mon=0); verify current rule

    # --- Event (volatility) trade: Day-1 / Result Day entry -----------------
    rich_ratio: float = 1.20             # implied/historical move >= this -> options rich -> sell (defined risk)
    cheap_ratio: float = 0.85            # implied/historical move <= this -> options cheap -> buy straddle
    tail_multiple: float = 2.0           # no short vol if any past reaction > tail_multiple x implied move
    condor_short_k: float = 1.25         # short strikes at spot x (1 +/- k x implied move)  (~1 SD of the event)
    condor_skew_k: float = 1.5           # wider k on the side at risk after a big pre-result run-up/run-down
    condor_wing_k: float = 0.5           # wing width = spot x implied move x wing_k (min one strike)
    min_credit_to_width: float = 0.20    # skip the condor if credit < this fraction of wing width
    runup_lookback: int = 10             # sessions used to measure the pre-result run-up
    runup_stretch_hm: float = 1.0        # run-up beyond this x historical move counts as stretched
    risk_free_rate: float = 0.06

    # --- Reaction / follow-through (directional) ---------------------------
    continuation_move_hm: float = 1.0    # |reaction move| >= this x historical move
    continuation_clv: float = 0.70       # close in the top 30% of the day's range (bottom 30% for shorts)
    continuation_volume_ratio: float = 2.0  # reaction volume vs 20-session average
    fade_gap_hm: float = 1.0             # gap >= this x historical move ...
    fade_clv: float = 0.30               # ... that closes in the bottom 30% of the range = failed gap
    muted_move_hm: float = 0.5           # gap and move both below this x historical move = no reaction
    target_r: float = 1.5                # profit target in multiples of initial risk
    max_chase_r: float = 0.5             # skip if the next open is already this many R beyond the trigger
    post_hold_sessions: int = 1          # time stop: exit at the close of the follow-through session
    fade_size_factor: float = 0.5        # failed-gap fades get half size

    # --- Reaction-session opening-range trade (intraday bars) ---------------
    opening_range_minutes: int = 15
    orb_min_gap_hm: float = 0.5          # gap-and-go needs a gap of at least this x historical move
    orb_volume_mult: float = 1.2         # breakout bar volume vs average bar volume so far
    intraday_exit: str = "15:15"

    # --- Risk -------------------------------------------------------------
    capital: float = 1_000_000.0
    risk_per_event_pct: float = 1.0      # max loss of one event (options) trade, % of capital
    risk_per_directional_pct: float = 0.75
    max_event_risk_per_day_pct: float = 3.0
    daily_loss_limit_pct: float = 2.0

    # --- Costs (backtest; approximate, check your broker's calculator) ------
    brokerage_per_order: float = 20.0
    option_slippage_pct: float = 2.0     # % of each option leg's premium, per side (spread + charges)
    futures_cost_bps: float = 5.0        # per side, all-in (STT, exchange, stamp, slippage)
    vol_exit_at: str = "open"            # event trades priced out at the reaction "open" or "close"
