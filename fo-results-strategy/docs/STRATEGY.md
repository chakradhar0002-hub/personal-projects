# F&O Results Strategy: Day-1 · Result Day · Day+1

A rule-based playbook for NSE stocks in the F&O segment around quarterly results.
Every rule here is also coded in `fo_results_strategy/`, so you can turn a stock's
numbers into a dated checklist (`plan`), read the reaction candle (`classify`) and
backtest the rules on your own data (`backtest`).

> Educational material, not investment advice. The thresholds are starting points.
> Validate them on real data and paper-trade them before you put money in (section 10).

> **Real-data test (Apr 2024 – May 2025, 71 stocks, real option prices):** no edge after costs.
> The event trades were about break-even before costs, and the follow-through trade lost money.
> Use these rules to filter, size and limit risk, not as a source of profit.
> Details: [REAL_DATA_RESULTS.md](REAL_DATA_RESULTS.md).

---

## 1. The idea

A results announcement is a jump you know is coming. Options price that jump in
advance: implied volatility (IV) builds into the date and collapses right after it
(the "IV crush"). That gives three separate, testable edges, one for each day:

| Day | Edge | Instrument |
|---|---|---|
| **Day-1** (or Result Day for after-close results) | **Volatility.** Compare what options price for the results day (implied move, **IM**) with what the stock usually does (historical move, **HM**). Sell when options are rich, buy when they are cheap, stay flat otherwise. | Iron condor (sell) / ATM straddle (buy), defined risk only |
| **Reaction session** | **Opening range.** Once the first 15 minutes settle, real surprises tend to trend and failed gaps tend to fill. | Stock futures, or options bought *after* the crush |
| **Follow-through session** | **Drift / exhaustion.** A strong close on heavy volume tends to follow through (post-earnings drift). A big gap that closed weak tends to keep fading. | Stock futures or ITM debit spread |

The one rule that never changes: **no directional bet is carried across the announcement.**
Before the numbers come out, you only hold defined-risk volatility structures, or nothing.

---

## 2. Which day is which

When the numbers come out decides which session reacts. Get this right first.

| Results released | Day-1 | Result Day | Day+1 |
|---|---|---|---|
| **Before market open** (before 09:15) | Setup + **enter event trade** 14:45–15:20 | **Reaction session**: exit event trade, opening-range trade | **Follow-through** trade |
| **During market hours** | Setup + **enter event trade** 14:45–15:20 | Quiet until the release, then **reaction** from the release time | **Follow-through** trade |
| **After market close** (after 15:30) | Setup only | **Enter event trade** 14:45–15:20, when IV peaks and there is the least time to decay | **Reaction session**: exit event trade, opening-range trade. Follow-through moves to Day+2 |
| **Saturday / holiday** | Setup + enter on the last session before | Reaction (first session after) | Follow-through |
| **Timing unknown** | Treat as *during market hours*: enter on Day-1 and never assume you get an extra session | | |

Here, "Result Day" means the first trading session on or after the board-meeting date.

Look at the timestamps of the company's past results filings on the exchange website
to see its usual pattern. Many companies release mid-session or after the close, and
some release on Saturdays.

---

## 3. Eligibility: skip the stock if any of these fail

| Filter | Rule | Why |
|---|---|---|
| F&O ban | MWPL use below 80% (ban starts at 95%) | In a ban you can't open positions, and close to one you may not be able to adjust |
| Option liquidity | ATM bid-ask spread ≤ 5% of mid, with meaningful OI at the strikes you need | Entering and exiting four legs eats the edge |
| Expiry | Front monthly expiry at least **3 sessions after** the reaction session; otherwise use next month | Avoids expiry-week gamma and physical settlement of stock F&O |
| History | At least 4 past results with price data (8 preferred) | HM is meaningless on 1–2 samples |
| Data | Front and back ATM IV available, or a "normal-period" IV | Needed to separate the event from normal volatility |
| Other events | No ex-dividend, split, bonus, index inclusion or merger news inside the window | They distort both the option prices and the reaction |

---

## 4. The three numbers

### 4.1 Historical move (HM)

For each of the last 8 results:

```
reaction move = close of reaction session / last close before the numbers were public − 1
HM            = average of |reaction move|
```

Also note the **median**, the **largest** move (for the tail check) and how often
the stock closed up (for information only: past direction does not predict the next one).

### 4.2 Implied move (IM)

The ATM straddle price of the front expiry covers the results day **plus every normal
day until expiry**, so reading the straddle as "the expected move" overstates the event
when expiry is a week or more away. Strip out the normal days:

```
f, b      = sessions from entry close to front / back expiry (including the reaction session)
σf, σb    = ATM IV of front / back expiry
base²     = (σb²·b − σf²·f) / (b − f)          ← "normal" vol implied by the term structure
event SD  = √( σf²·f/252 − base²·(f−1)/252 )   ← 1-SD move priced for the reaction session
IM        = 0.798 × event SD                   ← expected absolute move, comparable to HM
```

If there is no back month, use the stock's IV from a quiet period (2–4 weeks before
results) as `base`. Both expiries must be after the reaction session.

### 4.3 The ratio and the verdict

| IM / HM | Verdict | Event trade |
|---|---|---|
| ≥ 1.20 | **RICH**: options overprice the event | Sell an iron condor |
| ≤ 0.85 | **CHEAP**: options underprice the event | Buy the ATM straddle |
| in between | **FAIR**: no edge | Stay flat through the numbers |

**Tail check:** if any of the last 8 reactions was larger than **2 × IM**, never sell
volatility on this stock, even if it looks rich. One such move wipes out many small credits.

### 4.4 Worked example

Stock XYZ, results after the close on Thursday. Spot 1,500, lot 550, strike step 10.
Front IV 34% (8 sessions to expiry), back IV 26% (29 sessions).
Last 8 reactions: +3.1, −2.4, +4.2, −1.8, +2.7, −3.5, +2.2, −3.3 %.

| | Value |
|---|---|
| HM | 2.90% (max 4.2%) |
| Naive straddle read | 72.5 / 1,500 = **4.83%**. This overstates the event because 7 normal sessions are included |
| base vol | 22.2% |
| event SD / **IM** | 4.80% / **3.83%** |
| IM / HM | **1.32 → RICH** (the max 4.2% is below 2 × IM, so the tail check passes) |

Using the straddle alone (4.83 / 2.90 = 1.67) would have overstated the edge by about 25%.

---

## 5. Day-1 playbook

Set up every stock, whatever its timing. Enter on Day-1 only when the reaction comes
on Result Day (results before the open, during market hours, or timing unknown).

1. **Confirm the date and timing** from the exchange's board-meeting filing, and check the company's past release times.
2. **Run the eligibility filters** (section 3).
3. **Record HM, IM and the verdict** (section 4). Re-check with live quotes at 14:30. Spreads in the morning are wider and IV can still climb.
4. **Build the event trade** (enter 14:45–15:20, as one multi-leg order at a limit near mid):

   **RICH → short iron condor (front expiry)**
   - Short call strike = spot × (1 + 1.25 × IM), rounded **up** to a listed strike. Short put = spot × (1 − 1.25 × IM), rounded **down**.
     1.25 × IM is about 1 SD of the event.
   - Wings: buy strikes `max(1 strike, spot × IM × 0.5)` further out.
   - **Skew for the run-up:** if the stock moved more than 1 × HM in the last 10 sessions *into* results, there is more risk of a "sell the news" drop.
     Widen the put side to 1.5 × IM. After a big fall into results, widen the call side instead.
   - Skip if the credit is less than 20% of the wing width. The reward is too thin for the gap risk.
   - Place the **buy legs first**. That gets you the hedge margin benefit and you are never naked short.

   **CHEAP → long ATM straddle (front expiry)**
   - Buy the call and the put at the strike nearest spot.

   **FAIR → nothing.** Most stocks land here, and doing nothing is a position.
5. **Close any earlier "IV run-up" longs** into the entry close (Day-1, or Result Day for after-close results). The IV build into results is over, so keep them only if the verdict is CHEAP.
6. **Don't** hold futures or naked options for direction into the numbers. Don't sell naked straddles or strangles.

Worked example (XYZ, RICH, small run-up), all prices estimated by the tool:

```
SELL 1580 CE  10.69      BUY 1610 CE  6.00
SELL 1420 PE   8.30      BUY 1390 PE  4.07
Net credit 8.91 | width 30 | max loss 21.09/share = Rs 11,598 per lot
Break-evens 1411 / 1589 (±5.9%) vs HM 2.9% and the largest past move 4.2%
Capital Rs 25 lakh, 1% risk → 2 lots
```

---

## 6. Result Day playbook

### 6A. Results after the close: this is the entry day

- The session before the numbers. IV usually peaks into this close.
- Repeat Day-1 step 3 with live quotes at 14:30. If the verdict changed, follow the new one.
- Enter the event trade 14:45–15:20, exactly as in Day-1 step 4. Entering a day later than Day-1 means one less day of time decay on the long straddle and the highest IV for the condor.

### 6B. Results before the open: this is the reaction session

| Time | Action |
|---|---|
| 09:00–09:15 | Note the pre-open indicative price: gap versus IM and HM |
| 09:15–09:30 | **No new trades.** Spreads are wide and the opening print is noisy |
| from 09:30 | **Manage the event trade** (below) |
| from 09:30 | **Opening-range trade** (below) |
| 15:15 | Square off intraday positions |
| after close | Run `classify` on the reaction candle → the follow-through plan for Day+1 |

**Exiting the event trade, in the reaction session only:**

| Position | Rule |
|---|---|
| Short iron condor | Buy back 09:30–10:30 once spreads normalise. The crush happens at the open. Take profit as soon as 50–60% of the credit can be bought back. If spot opens **beyond a short strike, close everything immediately**: the wing has capped the loss, so don't roll or adjust. Hard exit at the close. |
| Long straddle | If the opening move is **≥ IM**, sell within the first 30 minutes: the move's gain beats the IV crush. If the move is **< 0.5 × IM by 10:00**, close it, because the remaining time value bleeds all day. Hard exit at the close. |

**Opening-range trade (OR = first 15 minutes, on 5-minute candles), one trade per stock:**

| Setup | Condition | Entry | Stop | Target |
|---|---|---|---|---|
| **Gap-and-go long** | Gap up ≥ 0.5 × HM; a candle **closes** above the OR high, above VWAP, with volume ≥ 1.2 × the session's average candle | Candle close | OR low | 1.5R |
| **Gap-and-go short** | Mirror image for a gap down | Candle close | OR high | 1.5R |
| **Failed gap up** (fade) | Gap up ≥ 1 × HM; a candle closes **below** the OR low and below VWAP | Candle close | OR high | 1.5R (gap fill to the prior close is the stretch target) |
| **Failed gap down** | Mirror image | Candle close | OR low | 1.5R |

Use stock futures, or ATM options bought **after** 09:30 when the IV crush has already
happened. Never buy options for direction before the results: you pay the event premium
and then lose it in the crush.

### 6C. Results during market hours: quiet, then reaction

- Before the release: manage nothing new. **No orders from 30 minutes before the board meeting until 15 minutes after the results hit.** Prices move on rumours and spreads widen.
- The IV crush happens at the release. Exit the event trade by the 6B rules, counting from the release time instead of 09:15.
- Opening-range trade: the "opening range" is the **first 15 minutes after the release** (`orb --start HH:MM`).
- After the close, run `classify`.

---

## 7. Day+1 playbook

### 7A. Results before the open or during market hours: follow-through day

Read the reaction candle against the stock's own HM (`classify` does this):

```
move = reaction close / pre-results close − 1     gap = reaction open / pre-results close − 1
CLV  = (close − low) / (high − low)                volume ratio = reaction volume / 20-session average
```

| Reaction type | Conditions | Day+1 trade |
|---|---|---|
| **CONTINUATION_UP** | move ≥ +1 × HM, CLV ≥ 0.70, volume ≥ 2× | **Buy** on a break above the reaction-day **high** |
| **CONTINUATION_DOWN** | move ≤ −1 × HM, CLV ≤ 0.30, volume ≥ 2× | **Sell** on a break below the reaction-day **low** |
| **FAILED_GAP_UP** | gap ≥ +1 × HM, CLV ≤ 0.30, close < open | **Sell** below the reaction-day low, **half size** |
| **FAILED_GAP_DOWN** | gap ≤ −1 × HM, CLV ≥ 0.70, close > open | **Buy** above the reaction-day high, **half size** |
| **MUTED** | gap and move both < 0.5 × HM | No trade |
| **MIXED** | anything else | No trade |

Trade rules for every setup:
- **Entry:** stop order at the trigger, active only after 09:30. **Don't chase:** if the stock opens more than 0.5R beyond the trigger, skip the trade.
- **Stop:** the reaction-day midpoint, `(high + low) / 2`.
- **Target:** 1.5R. For fades, the pre-results close (gap fill) is a stretch target.
- **Time stop:** exit at the close of Day+1. If you want to test holding winners longer for the drift, change `post_hold_sessions` and backtest it first.
- **Instrument:** stock futures. If one lot risks more than your budget, use an ITM debit spread sized to the same rupee risk. IV is crushed by now, so option buying is cheaper than it was before the results.

### 7B. Results after the close: Day+1 is the reaction session

Apply the Result-Day reaction rules (6B) on Day+1. The follow-through rules (7A) then apply to Day+2.

---

## 8. Position sizing and risk

| Rule | Default |
|---|---|
| Max loss of one event trade (condor: width − credit; straddle: full debit) | **1% of capital** |
| Total event risk opened on one day | 3% of capital |
| Same sector, same day (results cluster by sector and surprises are correlated) | max 2 event trades |
| One directional trade (futures) | 0.75% of capital, fades 0.375% |
| Daily loss limit | 2% → stop trading for the day |

Lots = ⌊ risk budget ÷ (max loss per share × lot size) ⌋. If that is 0, skip the
trade or use a smaller structure. Don't round up.

Hard rules:
- Defined risk only across the announcement: no naked short options, no futures.
- Never average down, roll or "repair" a losing event trade. Its whole thesis was one day.
- Every event trade is flat by the reaction-session close. Every directional trade is flat by its time stop.
- Limit orders only. Work multi-leg orders at mid and improve one tick at a time.
- Statutory costs (STT, exchange charges, stamp duty, GST) on F&O have been revised several times.
  Check your broker's calculator and include costs in every R you record.

---

## 9. One-page cheat sheet

```
DAY-1        eligible?  →  HM (last 8)  →  IM (term structure)  →  IM/HM
             ≥1.20 & no past move > 2×IM  →  SHORT IRON CONDOR  (short ±1.25×IM, wings +0.5×IM)
             ≤0.85                        →  LONG ATM STRADDLE
             else                         →  FLAT
             results before open / intraday / unknown → enter 14:45–15:20 today
             results after close                     → enter tomorrow 14:45–15:20

RESULT DAY   after-close results → entry day (re-check, enter 14:45–15:20)
             otherwise reaction  → no trades 09:15–09:30; exit event trade by its rules;
                                   opening-range trade (gap-and-go / failed gap), out by 15:15;
                                   after close: classify

DAY+1        CONTINUATION → break of reaction high/low, stop mid-range, 1.5R, out by close
             FAILED GAP   → same mechanics, half size
             MUTED/MIXED  → nothing
             (after-close results: Day+1 is the reaction session → use the Result Day rules)
```

---

## 10. Validate before trading

**Journal every event**, traded or not: date, timing, HM, IM, ratio, verdict, structure,
the reaction move, the reaction type, and P&L in R. After two results seasons
(~100 events across your watchlist) check that:
- RICH condors made money on average and CHEAP straddles did too. If not, move `rich_ratio` / `cheap_ratio`.
- The tail check blocked the trades that would have hurt.
- CONTINUATION follow-throughs beat MIXED ones. If not, raise the volume and CLV bars.

**Backtester** (`fo-results backtest --prices prices.csv --events events.csv [--quotes quotes.csv]`):
- *Event trade with `--quotes`:* replayed at **real closing option prices** from the NSE bhavcopy. Entry at the
  pre-results close, exit at the reaction-session close (the bhavcopy has no 10:00 prices, so this is the
  "hard exit" of section 6B). Planned strikes are moved onto listed ones, and the credit rule is re-checked
  against the real credit. Legs that did not trade that day are priced at NSE's settlement price.
- *Event trade without quotes:* priced out at the reaction-session open (`vol_exit_at`) with Black-Scholes at one
  flat IV per expiry: `front_iv` at entry, `post_iv` at exit. There is no skew, so OTM puts are under-priced.
  This **models** option P&L.
- Either way, slippage is 2% of each leg's premium per side, plus brokerage.
- *Calibration table:* for every assessed event, traded or not, it shows by IM/HM bucket how big the move was
  relative to IM and what selling the ATM straddle would have made. This tells you whether the ratio sorts
  events by how expensive the options really were.
- *Follow-through:* daily bars. Stop-order entry; skips if the open is more than 0.5R past the trigger.
  If the stop and the target are both inside one bar, it assumes the stop hit first (conservative). Exit at the time-stop close.
- *No look-ahead:* HM uses only results that came before each event.
- *Reaction-session opening-range trades* need intraday bars and are tested separately with `fo-results orb`.

**Data you need:** daily OHLCV for each stock; results dates **with timing**, taken from the exchange's
financial-results filings (the filing timestamp tells you before the open / during market hours / after the close);
and for the event trade, front/back ATM IV at the entry close plus the front IV after the results.
`fo-results fetch` builds all of this from free sources: Yahoo Finance for prices and results dates with
release times, and the NSE F&O bhavcopy archive for option prices. It backs out ATM IVs from the straddles.
Yahoo's results calendar currently ends in May 2025. Add later seasons with `fetch --results-file` (columns `symbol,announce_date,announce_time` or `timing`).
The results of running it are in [REAL_DATA_RESULTS.md](REAL_DATA_RESULTS.md).

`fo-results demo` runs the whole pipeline on **synthetic** data. That fake market has no drift
and random option mispricing, so its numbers only show that the plumbing works.
They are **not** evidence that the strategy makes money.

---

## 11. Running the tool

```bash
# Dated 3-day plan + event trade for one stock (percent inputs)
fo-results plan --symbol XYZ --date 2026-10-15 --timing AMC --spot 1500 --lot-size 550 \
  --strike-step 10 --hist-moves 3.1,-2.4,4.2,-1.8,2.7,-3.5,2.2,-3.3 \
  --front-iv 34 --back-iv 26 --run-up 2 --capital 2500000

# After the reaction session: follow-through plan
fo-results classify --symbol XYZ --prev-close 1500 --open 1560 --high 1600 --low 1550 \
  --close 1592 --volume 5000000 --avg-volume 1500000 --hm 2.9 --lot-size 550

# Opening-range trade on 5-minute bars of the reaction session
fo-results orb --bars examples/reaction_5min_example.csv --prev-close 1000 --hm 3

# Real data (Yahoo + NSE archives), then backtest with real option prices
fo-results fetch --out-dir real_data
fo-results backtest --prices real_data/prices.csv --events real_data/events.csv \
  --quotes real_data/quotes.csv --out trades.csv
```

All thresholds are in `fo_results_strategy/config.py` (`StrategyConfig`).
