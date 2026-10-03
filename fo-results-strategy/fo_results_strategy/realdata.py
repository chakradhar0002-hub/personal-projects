"""Build a real-market dataset for the backtester.

Sources (all free, no API key):
  * Yahoo Finance  - daily OHLCV (SYMBOL.NS) and past results dates with release time
                     (its calendar currently ends in May 2025: add later seasons with your own
                     file of results dates, see load_results_file)
  * NSE archives   - daily F&O bhavcopy: closing prices of every stock option contract

Output, in `out_dir`:
  prices.csv  date,symbol,open,high,low,close,volume
  events.csv  symbol,announce_date,timing,front_iv,front_days,back_iv,back_days,post_iv,
              lot_size,strike_step,front_expiry,announce_time,base_iv,price_factor
  quotes.csv  symbol,date,expiry,kind,strike,close,settle,volume   (front expiry, both event sessions)

IVs are backed out of the ATM straddle's closing prices. Downloads are cached in
`cache_dir`, so a rerun only fetches what is missing. Both sites change their
endpoints from time to time; if a download fails the event is skipped and counted.
"""
from __future__ import annotations

import csv
import http.cookiejar
import io
import json
import math
import time as _time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional, Sequence

from .config import StrategyConfig
from .metrics import base_vol_from_term_structure
from .pricing import implied_vol, straddle_implied_vol, years
from .timeline import Timing

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
IST = timezone(timedelta(hours=5, minutes=30))
MARKET_OPEN, MARKET_CLOSE = time(9, 15), time(15, 30)
UDIFF_START = date(2024, 7, 8)   # NSE switched the F&O bhavcopy to the UDiFF format

# Liquid NSE F&O stocks across sectors (NSE symbols).
DEFAULT_UNIVERSE = (
    "RELIANCE TCS INFY HDFCBANK ICICIBANK SBIN AXISBANK KOTAKBANK INDUSINDBK BAJFINANCE BAJAJFINSV "
    "HCLTECH WIPRO TECHM LTIM PERSISTENT COFORGE MPHASIS LT MARUTI M&M TATAMOTORS BAJAJ-AUTO "
    "HEROMOTOCO EICHERMOT TVSMOTOR ASIANPAINT HINDUNILVR ITC NESTLEIND BRITANNIA TITAN TATACONSUM "
    "DABUR GODREJCP SUNPHARMA DRREDDY CIPLA DIVISLAB LUPIN APOLLOHOSP TATASTEEL JSWSTEEL HINDALCO "
    "VEDL COALINDIA ONGC NTPC POWERGRID BHARTIARTL ADANIENT ADANIPORTS ULTRACEMCO GRASIM DLF "
    "BANKBARODA PNB CANBK FEDERALBNK CHOLAFIN SHRIRAMFIN HDFCLIFE SBILIFE BEL HAL SIEMENS "
    "HAVELLS PIDILITIND TRENT DMART POLYCAB DIXON INDIGO NAUKRI"
).split()


@dataclass(frozen=True)
class OptionQuote:
    symbol: str
    day: date
    expiry: date
    kind: str        # CE / PE
    strike: float
    close: float
    settle: float
    volume: float    # contracts traded

    @property
    def traded(self) -> bool:
        return self.volume > 0 and self.close > 0


def timing_from_ist(ts: datetime) -> Timing:
    """Release time (IST) -> BMO / DURING / AMC. Midnight stamps mean 'time unknown'."""
    t = ts.time()
    if t == time(5, 30):          # 00:00 UTC: date only
        return Timing.UNKNOWN
    if t < MARKET_OPEN:
        return Timing.BMO
    if t <= MARKET_CLOSE:
        return Timing.DURING
    return Timing.AMC


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

class Http:
    def __init__(self, pause: float = 0.25, retries: int = 3):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.opener.addheaders = [("User-Agent", UA), ("Accept", "*/*")]
        self.pause, self.retries = pause, retries

    def get(self, url: str, data: Optional[bytes] = None, headers: Optional[dict] = None,
            timeout: float = 30) -> Optional[bytes]:
        """Body, or None on 404. Retries other failures with backoff."""
        for attempt in range(self.retries):
            try:
                req = urllib.request.Request(url, data=data, headers=headers or {})
                with self.opener.open(req, timeout=timeout) as resp:
                    body = resp.read()
                _time.sleep(self.pause)
                return body
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None
                if attempt == self.retries - 1:
                    raise
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                if attempt == self.retries - 1:
                    raise
            _time.sleep(2 ** (attempt + 1))
        return None


class Yahoo:
    def __init__(self, http: Http):
        self.http = http
        self._crumb: Optional[str] = None

    def crumb(self) -> str:
        if self._crumb is None:
            try:
                self.http.get("https://fc.yahoo.com")
            except Exception:
                pass   # only sets the cookie; it answers 404
            self._crumb = self.http.get("https://query1.finance.yahoo.com/v1/test/getcrumb").decode().strip()
        return self._crumb

    def results_dates(self, symbol: str) -> list[datetime]:
        """Past results release times (IST) for an NSE symbol."""
        body = {
            "size": 100, "sortField": "startdatetime", "sortType": "ASC", "entityIdType": "earnings",
            "query": {"operator": "and", "operands": [
                {"operator": "eq", "operands": ["ticker", f"{symbol}.NS"]},
                {"operator": "eq", "operands": ["eventtype", "2"]}]},
            "includeFields": ["startdatetime", "timeZoneShortName", "eventtype"],
        }
        url = ("https://query1.finance.yahoo.com/v1/finance/visualization?lang=en-US&region=US&crumb="
               + urllib.parse.quote(self.crumb()))
        raw = self.http.get(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
        if not raw:
            return []
        docs = json.loads(raw)["finance"]["result"][0]["documents"]
        rows = docs[0]["rows"] if docs else []
        out = []
        for row in rows:
            utc = datetime.fromisoformat(row[0].replace("Z", "+00:00"))
            out.append(utc.astimezone(IST).replace(tzinfo=None))
        return sorted(out)

    def daily_bars(self, symbol: str, start: date, end: date) -> list[tuple]:
        """[(date, open, high, low, close, volume)] in IST trading dates."""
        p1 = int(datetime.combine(start, time()).replace(tzinfo=timezone.utc).timestamp())
        p2 = int(datetime.combine(end, time()).replace(tzinfo=timezone.utc).timestamp())
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol + '.NS')}"
               f"?period1={p1}&period2={p2}&interval=1d")
        raw = self.http.get(url)
        if not raw:
            return []
        res = json.loads(raw)["chart"]["result"]
        if not res or "timestamp" not in res[0]:
            return []
        q = res[0]["indicators"]["quote"][0]
        out = []
        for i, ts in enumerate(res[0]["timestamp"]):
            vals = [q[k][i] for k in ("open", "high", "low", "close", "volume")]
            if None in vals or vals[3] <= 0:
                continue
            d = datetime.fromtimestamp(ts, IST).date()
            out.append((d, *[float(v) for v in vals]))
        return out


# ---------------------------------------------------------------------------
# NSE F&O bhavcopy
# ---------------------------------------------------------------------------

def bhavcopy_urls(day: date) -> list[str]:
    mon = day.strftime("%b").upper()
    old = (f"https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{day:%Y}/{mon}/"
           f"fo{day:%d}{mon}{day:%Y}bhav.csv.zip")
    new = f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{day:%Y%m%d}_F_0000.csv.zip"
    return [new, old] if day >= UDIFF_START else [old, new]


def parse_bhavcopy(text: str, day: date, symbols: Optional[set] = None) -> list[OptionQuote]:
    """Stock-option rows of either bhavcopy format."""
    reader = csv.DictReader(io.StringIO(text))
    out = []
    udiff = "TckrSymb" in (reader.fieldnames or [])
    for r in reader:
        if udiff:
            if r["FinInstrmTp"] != "STO":
                continue
            sym, kind = r["TckrSymb"].strip(), r["OptnTp"].strip()
            expiry = date.fromisoformat(r["XpryDt"].strip())
            strike, close, settle = float(r["StrkPric"]), float(r["ClsPric"] or 0), float(r["SttlmPric"] or 0)
            volume = float(r["TtlTradgVol"] or 0)
        else:
            if r["INSTRUMENT"].strip() != "OPTSTK":
                continue
            sym, kind = r["SYMBOL"].strip(), r["OPTION_TYP"].strip()
            expiry = datetime.strptime(r["EXPIRY_DT"].strip(), "%d-%b-%Y").date()
            strike, close, settle = float(r["STRIKE_PR"]), float(r["CLOSE"] or 0), float(r["SETTLE_PR"] or 0)
            volume = float(r["CONTRACTS"] or 0)
        if symbols is not None and sym not in symbols:
            continue
        out.append(OptionQuote(sym, day, expiry, kind, strike, close, settle, volume))
    return out


def fetch_bhavcopy(http: Http, day: date, cache_dir: Path, symbols: set) -> Optional[list[OptionQuote]]:
    """Option quotes for `symbols` on `day`; the filtered rows are cached, the zip is not kept."""
    cache = cache_dir / f"fo_{day:%Y%m%d}.csv"
    if cache.exists():
        with open(cache, newline="") as fh:
            rows = [OptionQuote(r["symbol"], day, date.fromisoformat(r["expiry"]), r["kind"], float(r["strike"]),
                                float(r["close"]), float(r["settle"]), float(r["volume"]))
                    for r in csv.DictReader(fh)]
        cached = {q.symbol for q in rows}
        marker = cache_dir / f"fo_{day:%Y%m%d}.symbols"
        wanted = set(marker.read_text().split()) if marker.exists() else cached
        if symbols <= wanted:
            return [q for q in rows if q.symbol in symbols]
    for url in bhavcopy_urls(day):
        raw = http.get(url)
        if raw is None or not raw.startswith(b"PK"):
            continue
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            text = z.read(z.namelist()[0]).decode("utf-8", "replace")
        keep = symbols | set(DEFAULT_UNIVERSE)      # cache the whole universe: later runs reuse it
        rows = parse_bhavcopy(text, day, keep)
        cache_dir.mkdir(parents=True, exist_ok=True)
        with open(cache, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["symbol", "expiry", "kind", "strike", "close", "settle", "volume"])
            for q in rows:
                w.writerow([q.symbol, q.expiry.isoformat(), q.kind, q.strike, q.close, q.settle, q.volume])
        (cache_dir / f"fo_{day:%Y%m%d}.symbols").write_text(" ".join(sorted(keep)))
        return [q for q in rows if q.symbol in symbols]
    return None


def current_lot_sizes(http: Http) -> dict[str, int]:
    """Today's market lots (lots change over time; used only to express P&L in rupees)."""
    raw = http.get("https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv")
    lots: dict[str, int] = {}
    if not raw:
        return lots
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8", "replace"))))
    for r in rows[1:]:
        if len(r) > 2 and r[2].strip().isdigit():
            lots[r[1].strip()] = int(r[2].strip())
    return lots


# ---------------------------------------------------------------------------
# IV from quotes
# ---------------------------------------------------------------------------

def strike_step(strikes: Iterable[float], spot: float) -> Optional[float]:
    near = sorted({s for s in strikes if abs(s / spot - 1) <= 0.15})
    gaps = [round(b - a, 4) for a, b in zip(near, near[1:]) if b > a]
    return min(gaps) if gaps else None


def _traded_pairs(quotes: Sequence[OptionQuote], expiry: date) -> dict[float, dict[str, OptionQuote]]:
    by_strike: dict[float, dict[str, OptionQuote]] = defaultdict(dict)
    for q in quotes:
        if q.expiry == expiry and q.traded:
            by_strike[q.strike][q.kind] = q
    return {k: v for k, v in by_strike.items() if len(v) == 2}


def parity_spot(quotes: Sequence[OptionQuote], day: date, rate: float) -> Optional[float]:
    """Underlying implied by put-call parity (S = C - P + K e^-rt), median over traded strikes.

    Used to line Yahoo's split/bonus-adjusted history up with the unadjusted option strikes.
    """
    expiries = sorted({q.expiry for q in quotes if q.expiry > day})
    for exp in expiries[:2]:
        t = max((exp - day).days, 1) / 365
        est = sorted(v["CE"].close - v["PE"].close + k * math.exp(-rate * t)
                     for k, v in _traded_pairs(quotes, exp).items())
        if len(est) >= 3:
            return est[len(est) // 2]
    return None


PRICE_FACTORS = (1.0, 1.25, 4 / 3, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 10.0)


def price_factor(parity: Optional[float], yahoo_close: float, tolerance: float = 0.03) -> Optional[float]:
    """Unadjusted / Yahoo price: 1 normally; 2, 5, 10, ... before a later split or bonus; None if unclear."""
    if not parity:
        return None
    raw = parity / yahoo_close
    best = min(PRICE_FACTORS, key=lambda f: abs(raw / f - 1))
    return best if abs(raw / best - 1) <= tolerance else None


def atm_straddle_iv(quotes: Sequence[OptionQuote], expiry: date, spot: float, sessions: int,
                    rate: float, max_tries: int = 3) -> Optional[float]:
    """IV of the traded straddle nearest the money (within 5% of spot) for one expiry."""
    if sessions <= 0:
        return None
    by_strike = _traded_pairs(quotes, expiry)
    pairs = sorted((k for k in by_strike if abs(k / spot - 1) <= 0.05), key=lambda k: abs(k - spot))
    for k in pairs[:max_tries]:
        prem = by_strike[k]["CE"].close + by_strike[k]["PE"].close
        iv = straddle_implied_vol(prem, spot, k, years(sessions), rate)
        if iv and 0.03 < iv < 3.0:
            return iv
    return None


def atm_iv(quotes: Sequence[OptionQuote], expiry: date, spot: float, sessions: int, rate: float) -> Optional[float]:
    """ATM IV: the straddle when one traded; otherwise the average IV of the nearest traded
    out-of-the-money call and put within 5% of spot (next-month stock options rarely trade both legs)."""
    iv = atm_straddle_iv(quotes, expiry, spot, sessions, rate)
    if iv or sessions <= 0:
        return iv
    found = []
    for kind, otm in (("CE", lambda k: k >= spot), ("PE", lambda k: k <= spot)):
        legs = sorted((q for q in quotes if q.expiry == expiry and q.kind == kind and q.traded
                       and otm(q.strike) and abs(q.strike / spot - 1) <= 0.05), key=lambda q: abs(q.strike - spot))
        for q in legs[:2]:
            v = implied_vol(kind, q.close, spot, q.strike, years(sessions), rate)
            if v and 0.03 < v < 3.0:
                found.append(v)
                break
    return sum(found) / len(found) if found else None


TIMING_CLOCK = {Timing.BMO: time(8, 0), Timing.DURING: time(12, 0), Timing.AMC: time(17, 0),
                Timing.UNKNOWN: time(5, 30)}


def load_results_file(path: "str | Path") -> dict[str, list[datetime]]:
    """Your own results calendar: CSV with symbol,announce_date and announce_time (HH:MM IST)
    or timing (BMO / DURING / AMC). Use it to add seasons Yahoo does not have."""
    out: dict[str, list[datetime]] = defaultdict(list)
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            d = date.fromisoformat(r["announce_date"].strip())
            if (r.get("announce_time") or "").strip():
                t = time.fromisoformat(r["announce_time"].strip())
            else:
                t = TIMING_CLOCK[Timing.parse(r.get("timing"))]
            out[r["symbol"].strip().upper()].append(datetime.combine(d, t))
    return dict(out)


def merge_events(yahoo: Sequence[datetime], own: Sequence[datetime]) -> list[datetime]:
    """Union by date; your own row wins when both have the same date."""
    by_day = {ts.date(): ts for ts in yahoo}
    by_day.update({ts.date(): ts for ts in own})
    return sorted(by_day.values())


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

def build_dataset(symbols: Sequence[str], out_dir: "str | Path", cache_dir: "str | Path",
                  cfg: Optional[StrategyConfig] = None, start: date = date(2022, 9, 1),
                  end: Optional[date] = None, log=print,
                  own_events: Optional[dict[str, list[datetime]]] = None) -> Counter:
    cfg = cfg or StrategyConfig()
    out, cache = Path(out_dir), Path(cache_dir)
    out.mkdir(parents=True, exist_ok=True)
    http = Http()
    yahoo = Yahoo(http)
    end = end or date.today()
    stats: Counter = Counter()
    lots = current_lot_sizes(http)

    prices: dict[str, list[tuple]] = {}
    events: dict[str, list[datetime]] = {}
    own_events = own_events or {}
    for sym in list(dict.fromkeys(list(symbols) + list(own_events))):
        try:
            ev = merge_events(yahoo.results_dates(sym), own_events.get(sym, []))
            ev = [e for e in ev if start + timedelta(days=45) <= e.date() <= end]
            bars = yahoo.daily_bars(sym, start, end) if ev else []
        except Exception as e:   # one bad symbol must not stop the run
            log(f"  {sym}: yahoo failed ({e})")
            stats["symbol: yahoo error"] += 1
            continue
        if not ev or len(bars) < 60:
            stats["symbol: no data"] += 1
            continue
        prices[sym], events[sym] = bars, ev
        stats["symbols"] += 1
        stats["events"] += len(ev)
    log(f"yahoo{' + your file' if own_events else ''}: {stats['symbols']} symbols, {stats['events']} results dates")

    # Sessions to fetch quotes for: the close before the numbers and the reaction session.
    need: dict[date, set] = defaultdict(set)
    plan: list[tuple] = []
    for sym, evs in events.items():
        dates = [b[0] for b in prices[sym]]
        for ts in evs:
            timing = timing_from_ist(ts)
            r = (bisect_right if timing is Timing.AMC else bisect_left)(dates, ts.date())
            if r <= 0 or r >= len(dates):
                stats["event: outside price data"] += 1
                continue
            plan.append((sym, ts, timing, dates[r - 1], dates[r]))
            need[dates[r - 1]].add(sym)
            need[dates[r]].add(sym)
    log(f"nse: {len(need)} bhavcopy sessions to load")

    quotes: dict[date, dict[str, list[OptionQuote]]] = {}
    for i, day in enumerate(sorted(need), 1):
        try:
            rows = fetch_bhavcopy(http, day, cache, need[day])
        except Exception as e:
            log(f"  {day}: bhavcopy failed ({e})")
            rows = None
        if rows is None:
            stats["session: bhavcopy missing"] += 1
            continue
        per: dict[str, list[OptionQuote]] = defaultdict(list)
        for q in rows:
            per[q.symbol].append(q)
        quotes[day] = per
        if i % 25 == 0:
            log(f"  {i}/{len(need)} sessions")

    with open(out / "prices.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
        for sym, bars in prices.items():
            for d, o, h, l, c, v in bars:
                w.writerow([d.isoformat(), sym, round(o, 2), round(h, 2), round(l, 2), round(c, 2), int(v)])

    ev_rows, q_rows = [], []
    for sym, ts, timing, pre, react in plan:
        dates = [b[0] for b in prices[sym]]
        close = {b[0]: b[4] for b in prices[sym]}
        row = [sym, ts.date().isoformat(), timing.value, "", "", "", "", "", lots.get(sym, ""), "", "",
               ts.strftime("%H:%M")]          # base_iv appended when known
        pre_q, react_q = quotes.get(pre, {}).get(sym), quotes.get(react, {}).get(sym)
        if not pre_q or not react_q:
            stats["event: no option quotes"] += 1
            ev_rows.append(row)
            continue
        factor = price_factor(parity_spot(pre_q, pre, cfg.risk_free_rate), close[pre])
        if factor is None:
            stats["event: option strikes don't match the price data"] += 1
            ev_rows.append(row)
            continue
        if factor != 1.0:
            stats["event: price un-adjusted for a later split/bonus"] += 1
        spot = close[pre] * factor

        def sessions_to(exp: date, frm: date) -> int:
            n = bisect_right(dates, exp) - bisect_right(dates, frm)
            if exp > dates[-1]:           # expiry beyond the price data: count weekdays
                d = dates[-1]
                while d < exp:
                    d += timedelta(days=1)
                    n += d.weekday() < 5
            return n

        # ATM IV of every expiry that includes the reaction session and has traded options near the money.
        liquid: dict[date, tuple[float, int]] = {}
        for e in sorted({q.expiry for q in pre_q if q.expiry >= react}):
            n = sessions_to(e, pre)
            iv = atm_iv(pre_q, e, spot, n, cfg.risk_free_rate) if n >= 2 else None
            if iv:
                liquid[e] = (iv, n)
        ordered = sorted(liquid)
        tradable = [e for e in ordered if sessions_to(e, react) >= cfg.min_sessions_to_expiry]
        if not tradable:
            stats["event: illiquid ATM options"] += 1
            ev_rows.append(row)
            continue
        front = tradable[0]
        f_iv, f_days = liquid[front]
        i = ordered.index(front)
        # Normal vol from two expiries that both contain the event: (front, next) or, when the
        # month after is illiquid, (the expiring month, front).
        if i + 1 < len(ordered):
            pair = (front, ordered[i + 1])
        elif i > 0:
            pair = (ordered[i - 1], front)
        else:
            pair = None
        base = None
        if pair:
            (iv1, d1), (iv2, d2) = liquid[pair[0]], liquid[pair[1]]
            base = base_vol_from_term_structure(iv1, d1, iv2, d2)
        post_iv = atm_straddle_iv(react_q, front, close[react] * factor, f_days - 1, cfg.risk_free_rate)
        step = strike_step([q.strike for q in pre_q if q.expiry == front], spot)
        if not (base and post_iv and step):
            stats["event: illiquid ATM options" if not post_iv or not step else "event: no term structure"] += 1
            ev_rows.append(row)
            continue
        back_iv, back_days = liquid[pair[1]] if pair[1] != front else ("", "")
        row[3:8] = [f"{f_iv * 100:.3f}", f_days, f"{back_iv * 100:.3f}" if back_iv else "", back_days,
                    f"{post_iv * 100:.3f}"]
        row[9:11] = [step, front.isoformat()]
        row += [f"{base * 100:.3f}", f"{factor:g}"]
        ev_rows.append(row)
        stats["event: with IVs"] += 1
        for q in pre_q + react_q:
            if q.expiry == front and abs(q.strike / spot - 1) <= 0.3:
                q_rows.append([q.symbol, q.day.isoformat(), q.expiry.isoformat(), q.kind, q.strike, q.close,
                               q.settle, int(q.volume)])

    with open(out / "events.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["symbol", "announce_date", "timing", "front_iv", "front_days", "back_iv", "back_days",
                    "post_iv", "lot_size", "strike_step", "front_expiry", "announce_time", "base_iv",
                    "price_factor"])
        w.writerows(sorted((r + [""] * (14 - len(r)) for r in ev_rows), key=lambda r: (r[0], r[1])))
    with open(out / "quotes.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["symbol", "date", "expiry", "kind", "strike", "close", "settle", "volume"])
        w.writerows(q_rows)
    return stats
