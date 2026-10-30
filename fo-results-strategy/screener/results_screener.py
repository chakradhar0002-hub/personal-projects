#!/usr/bin/env python3
"""F&O quarterly-results screener for the next few days.

For every F&O stock (today's NSE fo_mktlots.csv list) with a results board meeting from --start to --start + --days
(calendar days, both ends included) it writes:

  calendar.csv      meeting date, likely reaction day (from the company's past board-meeting dates and release times),
                    the three-day window (project convention), the Trade 1 check (cutoff close) and its trigger levels,
                    the Trade 2 status, futures contracts, lot sizes and the F&O ban flag
  history.csv       every past result of these stocks in the project data: reported growth, Day-1 / Result day /
                    Day+1 moves, three-day sum, against Nifty, reaction-day move against Nifty, results winner, F&O
                    status at the time, the board-meeting date and when the stock reacted relative to it
  summary.csv       one row per stock: in-F&O and all-results history, the tested signals at the cutoff close (final)
                    or the latest close (provisional to the cutoff), single-day events inside the signal windows
  recent.csv        F&O results already announced in the --lookback days before --start whose winners-trade entry
                    (the open after the reaction day) is on or after the next session
  screener.md       risk box, actions by date, recent reporters, Trade 1 trigger levels, signals, history (a record)
  stocks/<SYM>.md   one page per company: its past results quarter by quarter and its summary
  screener.json     all of the above for a web page
  notes.md          sources, as-of times, conventions, what the research says, data checks

    python3 -P screener/results_screener.py --start 2026-10-20 --days 7 [--lookback 7] [--today 2026-10-20]

Environment:
  LAB_ROOT     the project's scratch data folder (sector_lab/data, ta/build, dl_nifty_sector_lists); default 'lab'
  SCREENER_DL  folder for downloads; default LAB_ROOT/dl_screener_<run date>
  OUT          output folder; default plans/screener_<start>_to_<end> in this repository

Downloads (NSE event calendar, board meetings, announcements, holidays, F&O lots, F&O ban list, corporate actions,
cash and F&O bhavcopies, index closes) are untrusted data: they are saved in SCREENER_DL and only parsed with json /
csv / pandas, never executed.

Project convention (report_builder/analyze_events.py): the result session is the results date if it is a trading
session, else the next session; Day-1 / Result day / Day+1 are the sessions before, of and after it; the cutoff is 2
sessions before the result session; the three-day sum is Day-1 + Result day + Day+1 daily returns (= cutoff close to
Day+1 close). The reaction day is Day+1 for results released after the close (15:30) on a trading day, else the
Result day (released before 09:15 or during market hours on a trading day, or on a non-trading day).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from bisect import bisect_left
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from datetime import time as dtime
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
IST = timezone(timedelta(hours=5, minutes=30))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")
LAG_CUT, VOL_CUT, VOL_STRICT, WIN_CUT, RSI_CUT = -10.0, 1.0, 1.3, 4.0, 50.0
MOVE_FLAG, VOL_FLAG = 8.0, 10.0          # single-day events: |daily move| > 8%, volume > 10x the 60-session median
MIN_N = 5                                # averages from fewer results are hidden
COST_T1, COST_T2 = 0.17, 0.40            # round-trip costs (docs/SUMMARY.md)
HELD_GAP, NEAR_GAP = 3, 5                # contract choice: expiry >= 3 sessions after the exit / >= 5 after the entry
AUTO_NSE = "Automobile and Auto Components"
AUTO_CUSTOM = "Auto & auto parts"


# ------------------------------------------------------------------------------------------------ small helpers
def d(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def nse_d(s: str) -> date:
    return datetime.strptime(s.strip(), "%d-%b-%Y").date()


def nse_dt(s: str) -> datetime:
    return datetime.strptime(s.strip(), "%d-%b-%Y %H:%M:%S")


def day_lbl(x) -> str:
    """Tue 20-Oct-2026"""
    if x is None or x == "":
        return ""
    x = d(x) if isinstance(x, str) else x
    return x.strftime("%a %d-%b-%Y")


def short_lbl(x) -> str:
    """Tue 20-Oct"""
    if x is None or x == "":
        return ""
    x = d(x) if isinstance(x, str) else x
    return x.strftime("%a %d-%b")


def isnum(x) -> bool:
    return x is not None and not isinstance(x, str) and not (isinstance(x, float) and math.isnan(x))


def sp(x, nd=2) -> str:
    """signed number for CSV ('' when missing)"""
    return f"{x:+.{nd}f}" if isnum(x) else ""


def spc(x, nd=2) -> str:
    """signed percent for markdown"""
    return f"{x:+.{nd}f}%" if isnum(x) else "-"


def jnum(x, nd=2):
    return round(float(x), nd) if isnum(x) else None


def safe_name(sym: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", sym)


def qty(x) -> str:
    """share counts: 11.40M, 473k"""
    if not isnum(x):
        return "-"
    x = float(x)
    return f"{x / 1e6:.2f}M" if x >= 1e6 else (f"{x / 1e3:.0f}k" if x >= 1e3 else f"{x:.0f}")


def rupees(x) -> str:
    if not isnum(x):
        return "-"
    return f"Rs {x / 1e7:.2f} crore" if x >= 1e7 else f"Rs {x / 1e5:.1f} lakh"


def price(x) -> str:
    return f"{x:,.2f}" if isnum(x) else "-"


# ------------------------------------------------------------------------------------------------ downloads
class Downloader:
    """Saves each response to SCREENER_DL; never executes anything; keeps a manifest of what was fetched when."""

    def __init__(self, folder: Path, offline: bool):
        self.dir, self.offline = folder, offline
        self.dir.mkdir(parents=True, exist_ok=True)
        self.mpath = self.dir / "_manifest.json"
        try:
            self.manifest = json.loads(self.mpath.read_text())
        except (OSError, ValueError):
            self.manifest = {}

    def get(self, url: str, name: str, api: bool = False, refresh: bool = True) -> Path | None:
        path = self.dir / name
        if self.offline or (path.exists() and not refresh):
            return path if path.exists() else None
        hdr = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
               "Accept": "application/json, text/plain, */*" if api else "*/*"}
        if api:
            hdr["Referer"] = "https://www.nseindia.com/"
        err = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=60) as r:
                    body = r.read()
                if api:
                    json.loads(body)                    # must be JSON, else treat as a failure
                tmp = path.with_name(path.name + ".part")
                tmp.write_bytes(body)
                tmp.replace(path)
                self.manifest[name] = {"url": url, "fetched_ist": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
                                       "bytes": len(body)}
                self.mpath.write_text(json.dumps(self.manifest, indent=1, sort_keys=True))
                time.sleep(0.3)
                return path
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return path if path.exists() else None
                err = e
            except Exception as e:                       # network / JSON error: retry, then fall back to a cache
                err = e
            time.sleep(2 * (attempt + 1))
        print(f"  download failed ({err}): {url}" + ("; using the cached file" if path.exists() else ""), flush=True)
        return path if path.exists() else None

    def fetched(self, name: str) -> str:
        m = self.manifest.get(name)
        if m:
            return m["fetched_ist"] + " IST"
        p = self.dir / name
        if p.exists():
            return datetime.fromtimestamp(p.stat().st_mtime, IST).strftime("%Y-%m-%d %H:%M:%S") + " IST (file time)"
        return "not available"


def load_json_list(path: Path | None) -> list | None:
    if not path:
        return None
    try:
        x = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if isinstance(x, dict):
        x = x.get("data", [])
    return x if isinstance(x, list) else None


# ------------------------------------------------------------------------------------------------ calendar
class Calendar:
    """Trading sessions: the project's sessions plus appended data days, then weekdays minus NSE holidays."""

    def __init__(self, data_sessions: list[str], holidays: dict[str, str], horizon_end: date):
        self.holidays = holidays
        self.data_sessions = list(data_sessions)
        last = d(self.data_sessions[-1])
        fut, x = [], last + timedelta(days=1)
        while x <= horizon_end:
            if x.weekday() < 5 and x.isoformat() not in holidays:
                fut.append(x.isoformat())
            x += timedelta(days=1)
        self.sessions = self.data_sessions + fut
        self.pos = {s: i for i, s in enumerate(self.sessions)}

    def is_session(self, s: str) -> bool:
        return s in self.pos

    def window(self, results_date: str, timing: str) -> dict:
        """The project's window for a result on `results_date` with `timing` (analyze_events.py)."""
        rs = bisect_left(self.sessions, results_date)
        if rs < 2 or rs + 1 >= len(self.sessions):
            return {}
        on_session = results_date in self.pos
        react = rs + 1 if (timing == "After close" and on_session) else rs
        return {"cutoff": self.sessions[rs - 2], "day_m1": self.sessions[rs - 1], "result_day": self.sessions[rs],
                "day_p1": self.sessions[rs + 1], "reaction_day": self.sessions[react], "i_rs": rs, "i_react": react,
                "on_session": on_session}

    def shift(self, s: str, k: int) -> str | None:
        i = self.pos.get(s)
        if i is None or not 0 <= i + k < len(self.sessions):
            return None
        return self.sessions[i + k]

    def next_after(self, x: date) -> str | None:
        i = bisect_left(self.sessions, (x + timedelta(days=1)).isoformat())
        return self.sessions[i] if i < len(self.sessions) else None

    def gap(self, a: str, b: str) -> int:
        """Sessions from a to b; a large number when b is past the calendar horizon and after a."""
        if a in self.pos and b in self.pos:
            return self.pos[b] - self.pos[a]
        return 10 ** 6 if b > a else -10 ** 6

    def holidays_between(self, a: str, b: str) -> list[str]:
        """Weekday holidays strictly between sessions a and b."""
        out, x = [], d(a) + timedelta(days=1)
        while x < d(b):
            if x.weekday() < 5 and x.isoformat() in self.holidays:
                out.append(f"{x:%a %d-%b} {self.holidays[x.isoformat()]}")
            x += timedelta(days=1)
        return out

    def monthly_expiry(self, y: int, m: int) -> str:
        """Last Tuesday of the month, moved to the previous session if that is a holiday (fo_results_strategy.timeline)."""
        x = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1))
        while x.weekday() != 1:
            x -= timedelta(days=1)
        while x.weekday() >= 5 or x.isoformat() in self.holidays:
            x -= timedelta(days=1)
        return x.isoformat()

    def front_expiry(self, reaction: str, min_after: int = 3) -> str | None:
        y, m = d(reaction).year, d(reaction).month
        for _ in range(3):
            e = self.monthly_expiry(y, m)
            if e >= reaction and e in self.pos and self.pos[e] - self.pos[reaction] >= min_after:
                return e
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        return None


def release_timing(t: datetime, cal: Calendar) -> str:
    """Project labels: before 09:15 / 09:15-15:29 / from 15:30 on a trading day; any time on a non-trading day."""
    if not cal.is_session(t.date().isoformat()):
        return "Non-trading day"
    if t.time() < dtime(9, 15):
        return "Before open"
    if t.time() < dtime(15, 30):
        return "During market"
    return "After close"


# ------------------------------------------------------------------------------------------------ indicators
def seeded(x: np.ndarray, n: int, alpha: float, start: int) -> np.ndarray:
    """Wilder RMA (alpha 1/n) of x[start:], seeded with the mean of its first n values (ta/build/build_panel.py)."""
    out = np.full(len(x), np.nan)
    if len(x) - start < n:
        return out
    y = x[start + n - 1:].astype(float).copy()
    y[0] = x[start:start + n].mean()
    out[start + n - 1:] = np.array(pd.Series(y).ewm(alpha=alpha, adjust=False).mean(), dtype=float)
    return out


def rsi(c: np.ndarray, n: int = 14) -> np.ndarray:
    dd = np.diff(c, prepend=np.nan)
    g, l_ = seeded(np.clip(dd, 0, None), n, 1 / n, 1), seeded(np.clip(-dd, 0, None), n, 1 / n, 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = 100 - 100 / (1 + g / l_)
    out[(l_ == 0) & (g > 0)] = 100
    out[(l_ == 0) & (g == 0)] = 50
    return out


def ratio_5_60(v: np.ndarray) -> float:
    """5/60 mean-volume ratio of the last values of v (sessions with a trade), as Panel.vol_ratio."""
    v5, v60 = v[-5:], v[-60:]
    v5, v60 = v5[np.isfinite(v5) & (v5 > 0)], v60[np.isfinite(v60) & (v60 > 0)]
    return v5.mean() / v60.mean() if len(v5) and len(v60) else np.nan


# ------------------------------------------------------------------------------------------------ price panel
class Panel:
    """Session x symbol returns, adjusted close and adjusted volume: the project's data (to its last session)
    plus cash-bhavcopy days appended after it; Nifty 50 closes likewise."""

    def __init__(self, lab: Path):
        pack = lab / "sector_lab" / "data"
        self.sessions = pd.read_csv(pack / "sessions.csv").day.tolist()
        R = pd.read_csv(pack / "returns.csv", index_col=0)
        assert R.index.tolist() == self.sessions
        self.syms = R.columns.tolist()
        self.col = {s: j for j, s in enumerate(self.syms)}
        self.R = R.to_numpy(float)
        nifty = pd.read_csv(pack / "index_close.csv", index_col=0, usecols=["day", "Nifty 50"])["Nifty 50"]
        assert nifty.index.tolist() == self.sessions
        self.N = nifty.to_numpy(float)
        oh = pd.read_csv(lab / "ta" / "build" / "adjusted_ohlcv.csv.gz", usecols=["day", "symbol", "close", "volume"])
        oh = oh[oh.symbol.isin(self.col)]
        self.C = oh.pivot(index="day", columns="symbol", values="close").reindex(index=self.sessions,
                                                                                columns=self.syms).to_numpy(float)
        self.V = oh.pivot(index="day", columns="symbol", values="volume").reindex(index=self.sessions,
                                                                                 columns=self.syms).to_numpy(float)
        self.project_last = self.sessions[-1]
        self.flags: dict[str, list[str]] = {}
        self.appended: list[str] = []
        self.checks: list[str] = []
        self.raw: dict[str, pd.DataFrame] = {}          # appended day -> bhavcopy close / previous close (EQ)

    def flag(self, sym, msg):
        self.flags.setdefault(sym, []).append(msg)

    def append_day(self, day: str, bhav: pd.DataFrame, nifty_close: float, ca: dict):
        """Append one session from the cash bhavcopy (series EQ). ca: {(sym, day): (kind, factor, subject)}."""
        b = bhav[bhav.SctySrs.astype(str).str.strip() == "EQ"].drop_duplicates("TckrSymb").set_index("TckrSymb")
        self.raw[day] = b[["ClsPric", "PrvsClsgPric", "TtlTradgVol"]].astype(float)
        T, N = self.R.shape
        r_new, c_new, v_new = np.full(N, np.nan), np.full(N, np.nan), np.full(N, np.nan)
        first_day = not self.appended
        n_pc_bad = 0
        for s, j in self.col.items():
            if s not in b.index:
                continue
            row = b.loc[s]
            c, pc, v = float(row.ClsPric), float(row.PrvsClsgPric), float(row.TtlTradgVol)
            prev_i = np.flatnonzero(np.isfinite(self.C[:, j]))
            prev = self.C[prev_i[-1], j] if len(prev_i) else np.nan
            kind, factor, subject = ca.get((s, day), (None, None, None))
            if kind in ("split", "bonus", "consolidation") and factor:
                self.C[:, j] /= factor                   # keep adj close = raw close on the newest day
                self.V[:, j] *= factor
                prev = prev / factor
                self.flag(s, f"{subject} (ex {day}): earlier closes and volumes adjusted by {factor:g}")
                ret = c / prev - 1 if prev else np.nan
            elif kind == "demerger":
                ret = np.nan
                self.flag(s, f"{subject} (ex {day}): return that day left blank (held flat)")
            else:
                ret = c / prev - 1 if prev else np.nan
                if prev and abs(pc / prev - 1) > 0.001 and len(prev_i) and prev_i[-1] == T - 1:
                    n_pc_bad += 1
                    self.flag(s, f"{day}: NSE previous close {pc:g} differs from the stored close {prev:g}")
                if kind:
                    self.flag(s, f"{subject} (ex {day}): no share multiplier applied; check the price move")
            if isnum(ret) and abs(ret) > 0.35:
                self.flag(s, f"{day}: close-to-close move {100 * ret:+.1f}% (beyond 35%): check for a corporate action")
            r_new[j], c_new[j], v_new[j] = ret, c, v
        if first_day:
            self.checks.append(f"first appended day {day}: NSE previous close differs from the project's last close "
                               f"for {n_pc_bad} symbols")
        self.R = np.vstack([self.R, r_new])
        self.C = np.vstack([self.C, c_new])
        self.V = np.vstack([self.V, v_new])
        self.N = np.append(self.N, nifty_close)
        self.sessions.append(day)
        self.appended.append(day)

    def finish(self):
        self.pos = {s: i for i, s in enumerate(self.sessions)}
        self.G = np.cumprod(1 + np.nan_to_num(self.R), axis=0)
        self.first = np.array([np.argmax(np.isfinite(self.R[:, j])) if np.isfinite(self.R[:, j]).any() else 10 ** 9
                               for j in range(self.R.shape[1])])
        self._rsi = {}

    def nifty_ret(self, i: int) -> float:
        return self.N[i] / self.N[i - 1] - 1 if i >= 1 else np.nan

    def lag_pct(self, sym: str, c: int) -> float:
        """(stock 21-session return - Nifty 50 21-session return) x 100 at the close of session c."""
        j = self.col.get(sym)
        if j is None or c < 21 or self.first[j] > c - 21:
            return np.nan
        return 100 * ((self.G[c, j] / self.G[c - 21, j] - 1) - (self.N[c] / self.N[c - 21] - 1))

    def stock21(self, sym: str, c: int) -> float:
        j = self.col.get(sym)
        if j is None or c < 21 or self.first[j] > c - 21:
            return np.nan
        return 100 * (self.G[c, j] / self.G[c - 21, j] - 1)

    def nifty21(self, c: int) -> float:
        return 100 * (self.N[c] / self.N[c - 21] - 1)

    def vol_ratio(self, sym: str, c: int) -> float:
        """Mean adjusted volume of the last 5 sessions / last 60 sessions (sessions with a trade), up to c."""
        j = self.col.get(sym)
        if j is None:
            return np.nan
        v5, v60 = self.V[max(c - 4, 0):c + 1, j], self.V[max(c - 59, 0):c + 1, j]
        v5, v60 = v5[np.isfinite(v5) & (v5 > 0)], v60[np.isfinite(v60) & (v60 > 0)]
        return v5.mean() / v60.mean() if len(v5) and len(v60) else np.nan

    def rsi14(self, sym: str, c: int) -> float:
        j = self.col.get(sym)
        if j is None:
            return np.nan
        if sym not in self._rsi:
            rows = np.flatnonzero(np.isfinite(self.C[:, j]))
            full = np.full(len(self.sessions), np.nan)
            full[rows] = rsi(self.C[rows, j], 14)
            self._rsi[sym] = full
        return self._rsi[sym][c]

    # ---- Trade 1 trigger levels for a cutoff k sessions after the latest close
    def trigger_levels(self, sym: str, k: int) -> dict | None:
        """Highest cutoff close keeping the 21-session lag below LAG_CUT (Nifty flat from the latest close, and the
        change per 1% Nifty move), and the volume needed on each of the k sessions up to the cutoff (equal volumes)
        for the 5/60 ratio to reach 1.0x and 1.3x. Exact for the lag; the volume assumes every session trades."""
        j, i = self.col.get(sym), len(self.sessions) - 1
        c = i + k
        b = c - 21
        if j is None or k < 1 or b < 0 or b > i or self.first[j] > b or not np.isfinite(self.C[i, j]):
            return None
        P, gb, gi, nb, ni = self.C[i, j], self.G[b, j], self.G[i, j], self.N[b], self.N[i]
        pmax = P * gb / gi * (ni / nb + LAG_CUT / 100)
        per1 = P * gb / gi * ni / nb * 0.01
        known5 = self.V[max(c - 4, 0):i + 1, j] if c - 4 <= i else np.array([])
        known60 = self.V[max(c - 59, 0):i + 1, j]
        v5k, v60k = float(np.nansum(known5)), float(np.nansum(known60))
        u5 = min(k, 5)
        need = {}
        for R in (VOL_CUT, VOL_STRICT):
            den = 12 * u5 - R * k
            need[R] = max((R * v60k - 12 * v5k) / den, 0.0) if den > 0 else np.nan
        avg5 = np.nanmean(self.V[i - 4:i + 1, j])
        # plug-back: the lag at pmax and the ratio with the needed volumes
        g_c = gi * pmax / P
        lag_at = 100 * ((g_c / gb - 1) - (ni / nb - 1))
        vr_at = {R: ratio_5_60(np.concatenate([self.V[:i + 1, j], np.full(k, max(need[R], 1.0))]))
                 if isnum(need[R]) else np.nan for R in need}         # 1 share stands in for 'any volume'
        return {"k": k, "base_day": self.sessions[b], "base_close": self.C[b, j], "latest_close": P,
                "close_max": pmax, "per_1pct_nifty": per1, "headroom_pct": 100 * (pmax / P - 1),
                "lag_now": self.lag_pct(sym, i), "vol_need_1": need[VOL_CUT], "vol_need_13": need[VOL_STRICT],
                "avg5": avg5, "mult_1": need[VOL_CUT] / avg5 if avg5 else np.nan,
                "mult_13": need[VOL_STRICT] / avg5 if avg5 else np.nan,
                "check_lag": lag_at, "check_vr_1": vr_at[VOL_CUT], "check_vr_13": vr_at[VOL_STRICT]}

    def single_day_events(self, sym: str, c_end: int) -> list[dict]:
        """Daily moves beyond +-MOVE_FLAG% inside the 21-session lag window and volumes above VOL_FLAG x the median of
        the 60-session volume base, for the windows ending at session c_end (only sessions already in the data)."""
        j, i = self.col.get(sym), len(self.sessions) - 1
        if j is None:
            return []
        lo_lag, lo_vol, hi = c_end - 20, max(c_end - 59, 0), min(c_end, i)
        v = self.V[lo_vol:hi + 1, j]
        med = float(np.nanmedian(v[np.isfinite(v) & (v > 0)])) if np.isfinite(v).any() else np.nan
        out = []
        for t in range(lo_vol, hi + 1):
            r, vol = self.R[t, j], self.V[t, j]
            mv = t >= lo_lag and isnum(r) and abs(r) > MOVE_FLAG / 100
            bv = isnum(vol) and isnum(med) and med > 0 and vol > VOL_FLAG * med
            if mv or bv:
                out.append({"day": self.sessions[t], "move_pct": 100 * r if isnum(r) else np.nan, "volume": vol,
                            "x_median": vol / med if isnum(vol) and med else np.nan, "big_move": bool(mv),
                            "big_volume": bool(bv), "in_lag_window": t >= lo_lag})
        return out


def event_txt(e: dict) -> str:
    where = "lag window and volume base" if e["in_lag_window"] else "volume base"
    return (f"{short_lbl(e['day'])} {spc(e['move_pct'])} on {qty(e['volume'])} shares "
            f"({e['x_median']:.0f}x the 60-session median; {where})")


# ------------------------------------------------------------------------------------------------ parsing NSE files
def parse_lots(path: Path) -> list[str]:
    import csv
    rows = list(csv.reader(open(path, newline="")))
    return [r[1].strip() for r in rows[1:] if len(r) > 2 and r[2].strip().isdigit() and "NIFTY" not in r[1]]


def parse_lot_table(path: Path) -> dict[str, dict[str, int]]:
    """{symbol: {'NOV-26': lot, ...}} from fo_mktlots.csv (index rows included)."""
    import csv
    rows = list(csv.reader(open(path, newline="")))
    head = [h.strip().upper() for h in rows[0]] if rows else []
    out = {}
    for r in rows[1:]:
        if len(r) < 3:
            continue
        out[r[1].strip()] = {head[k]: int(v.strip()) for k, v in enumerate(r) if k >= 2 and k < len(head)
                             and v.strip().isdigit()}
    return out


def parse_secban(path: Path | None) -> tuple[str | None, set[str]]:
    """fo_secban.csv: 'Securities in Ban For Trade Date 21-OCT-2026:' then 'n,SYMBOL' rows."""
    if not path:
        return None, set()
    lines = path.read_text(errors="replace").splitlines()
    m = re.search(r"(\d{1,2}-[A-Za-z]{3}-\d{4})", lines[0]) if lines else None
    td = datetime.strptime(m.group(1).title(), "%d-%b-%Y").date().isoformat() if m else None
    syms = set()
    for ln in lines[1:]:
        parts = [p.strip() for p in ln.split(",")]
        if len(parts) >= 2 and parts[1] and parts[0].isdigit():
            syms.add(parts[1])
    return td, syms


def parse_fo_bhav(path: Path | None) -> dict[str, dict[str, dict]]:
    """{symbol: {expiry: {'lot', 'close'}}} for stock (STF) and index (IDF) futures from the F&O bhavcopy."""
    if not path:
        return {}
    f = pd.read_csv(path, compression="zip", usecols=["FinInstrmTp", "TckrSymb", "XpryDt", "ClsPric", "NewBrdLotQty"])
    f = f[f.FinInstrmTp.astype(str).str.strip().isin(["STF", "IDF"])]
    out: dict[str, dict[str, dict]] = {}
    for r in f.itertuples():
        out.setdefault(str(r.TckrSymb).strip(), {})[str(r.XpryDt).strip()[:10]] = {
            "lot": int(r.NewBrdLotQty), "close": float(r.ClsPric), "kind": str(r.FinInstrmTp).strip()}
    return out


def parse_holidays(path: Path | None) -> tuple[dict[str, str], set[int]]:
    if not path:
        return {}, set()
    h = json.loads(path.read_text())
    out = {}
    for x in h.get("CM", []):
        try:
            out[nse_d(x["tradingDate"]).isoformat()] = str(x.get("description", "")).strip()
        except (KeyError, ValueError):
            continue
    return out, {d(k).year for k in out}


def ca_factor(subject: str) -> tuple[str | None, float | None]:
    s = subject.lower()
    m = re.search(r"from\s+r[se]\.?\s*([\d.]+).*?to\s+r[se]\.?\s*([\d.]+)", s)
    if "split" in s or "sub-division" in s:
        return ("split", float(m.group(1)) / float(m.group(2))) if m else ("split", None)
    if "consolidation" in s:
        return ("consolidation", float(m.group(1)) / float(m.group(2))) if m else ("consolidation", None)
    if "bonus" in s:
        m = re.search(r"bonus\s+(\d+)\s*:\s*(\d+)", s)
        return ("bonus", (int(m.group(1)) + int(m.group(2))) / int(m.group(2))) if m else ("bonus", None)
    if "demerger" in s or "scheme of arrangement" in s:
        return ("demerger", None)
    if "rights" in s:
        return ("rights", None)
    return (None, None)


def parse_meetings(cal_path: Path | None, bm_path: Path | None, fo: set[str], lo: date, hi: date) -> dict:
    """Results board meetings of F&O stocks dated lo..hi from the NSE event calendar and board-meeting list."""
    found: dict[str, dict] = {}
    other_dates: dict[str, set] = {}
    if cal_path:
        for e in json.loads(cal_path.read_text()):
            s, purpose = str(e.get("symbol", "")).strip(), str(e.get("purpose", ""))
            try:
                dt = nse_d(e["date"])
            except (KeyError, ValueError):
                continue
            if s not in fo or "financial result" not in purpose.lower():
                continue
            other_dates.setdefault(s, set()).add(dt.isoformat())
            if lo <= dt <= hi:
                x = found.setdefault(s, {"symbol": s, "dates": {}, "company": str(e.get("company", "")).strip()})
                x["dates"].setdefault(dt.isoformat(), {"purpose": purpose, "sources": set(), "stamp": ""})
                x["dates"][dt.isoformat()]["sources"].add("event calendar")
    resched = set()
    if bm_path:
        for e in json.loads(bm_path.read_text()):
            s, purpose = str(e.get("bm_symbol", "")).strip(), str(e.get("bm_purpose", ""))
            if s not in fo:
                continue
            if "reschedul" in purpose.lower():
                resched.add(s)
            try:
                dt = nse_d(e["bm_date"])
            except (KeyError, ValueError):
                continue
            if "financial result" not in purpose.lower():
                continue
            other_dates.setdefault(s, set()).add(dt.isoformat())
            if lo <= dt <= hi:
                x = found.setdefault(s, {"symbol": s, "dates": {}, "company": str(e.get("sm_name", "")).strip()})
                y = x["dates"].setdefault(dt.isoformat(), {"purpose": purpose, "sources": set(), "stamp": ""})
                y["sources"].add("board meetings")
                try:
                    stamp = datetime.strptime(str(e.get("bm_timestamp", "")), "%d-%b-%Y %H:%M:%S").isoformat()
                except ValueError:
                    stamp = ""
                y["stamp"] = max(y["stamp"], stamp)
                if len(purpose) > len(y["purpose"]):
                    y["purpose"] = purpose
    out = {}
    for s, x in found.items():
        # several dates: the one with the latest board-meeting intimation, else the earliest
        stamped = [(v["stamp"], k) for k, v in x["dates"].items() if v["stamp"]]
        best_date = max(stamped)[1] if stamped else min(x["dates"])
        best = (best_date, x["dates"][best_date])
        note = []
        alld = sorted(other_dates.get(s, set()))
        if len(alld) > 1:
            note.append("NSE lists more than one results date: " + ", ".join(alld))
        if s in resched:
            note.append("a 'board meeting rescheduled' notice exists: check the date")
        out[s] = {"symbol": s, "company": x["company"], "meeting_date": best[0], "purpose": best[1]["purpose"],
                  "source": " + ".join(sorted(best[1]["sources"])), "date_note": "; ".join(note)}
    return out


def fin_meeting_dates(rows: list | None) -> list[str] | None:
    """Dates of a company's past results board meetings (NSE corporate-board-meetings for one symbol)."""
    if rows is None:
        return None
    out = set()
    for e in rows:
        txt = f"{e.get('bm_purpose', '')} {e.get('bm_desc', '')}".lower()
        if "financial result" not in txt:
            continue
        try:
            out.add(nse_d(str(e["bm_date"])).isoformat())
        except (KeyError, ValueError):
            continue
    return sorted(out)


def meeting_timing(g: pd.DataFrame, mdates: list[str], cal: Calendar) -> dict:
    """Match each past result (events.csv release date) to the latest results board meeting 0-5 days before it and
    count when the stock reacted relative to the meeting date: on the meeting-date session or the next one."""
    rows = []
    for r in g.itertuples():
        rd = str(r.results_date)
        cand = [x for x in mdates if x <= rd and (d(rd) - d(x)).days <= 5]
        if not cand or not isinstance(r.reaction_day, str) or r.reaction_day not in cal.pos:
            continue
        mdate = max(cand)
        off = cal.pos[r.reaction_day] - bisect_left(cal.sessions, mdate)
        rows.append({"qn": int(r.qn), "period": r.period, "meeting": mdate, "release": f"{rd} {r.results_time}",
                     "timing": r.timing, "on_session": mdate in cal.pos, "offset": off,
                     "after_midnight": rd > mdate})
    td = [x for x in rows if x["on_session"]]
    nxt, same = sum(x["offset"] == 1 for x in td), sum(x["offset"] == 0 for x in td)
    rec = td[-8:]
    rn, rsm = sum(x["offset"] == 1 for x in rec), sum(x["offset"] == 0 for x in rec)
    if rn != rsm:
        likely, share = ("Day+1", rn / len(rec)) if rn > rsm else ("Result day", rsm / len(rec))
    elif nxt != same:
        likely, share = ("Day+1" if nxt > same else "Result day"), 0.5
    else:
        likely, share = "Mixed", 0.5
    return {"rows": rows, "n": len(rows), "n_td": len(td), "next": nxt, "same": same, "other": len(td) - nxt - same,
            "next_after_midnight": sum(x["after_midnight"] and x["offset"] == 1 for x in td),
            "recent_n": len(rec), "recent_next": rn, "recent_same": rsm, "likely": likely, "mixed": share < 0.75}


def find_results_filing(ann: list, meeting: date) -> dict | None:
    """Earliest NSE announcement from the meeting date to 3 days later that carries the financial results
    ('Outcome of Board Meeting', or a results filing / press release that names the financial results)."""
    best = None
    for e in ann:
        try:
            t = nse_dt(str(e.get("exchdisstime") or e.get("an_dt")))
        except ValueError:
            continue
        if not meeting <= t.date() <= meeting + timedelta(days=3):
            continue
        desc, txt = str(e.get("desc", "")).strip(), str(e.get("attchmntText", ""))
        dl, tl = desc.lower(), txt.lower()
        if any(x in dl for x in ("con. call", "analyst", "newspaper", "trading window", "intimation")):
            continue
        if dl == "outcome of board meeting" or "financial result" in dl or "financial result" in tl:
            if best is None or t < best["time"]:
                best = {"time": t, "desc": desc, "text": re.sub(r"\s+", " ", txt)[:160]}
    return best


def month_of(e: str) -> str:
    return d(e).strftime("%b")


def pick_contract(cal: Calendar, expiries: list[str], entry: str, exit_: str) -> dict:
    """Futures contract for a trade from `entry` to `exit_`: hold the first expiry at least HELD_GAP sessions after the
    exit (no physical settlement, out of the last days); if a nearer contract (at least NEAR_GAP sessions after the
    entry) expires first, the alternative is to trade it and roll before its expiry."""
    held = next((e for e in expiries if cal.gap(exit_, e) >= HELD_GAP), None)
    near = next((e for e in expiries if cal.gap(entry, e) >= NEAR_GAP), None)
    if held is None:
        return {"held": None, "near": near, "use": near, "roll": True,
                "txt": f"{month_of(near)} fut and roll (later contracts not listed yet)" if near else "-"}
    if near is None or near >= held:
        return {"held": held, "near": held, "use": held, "roll": False,
                "txt": f"{month_of(held)} fut (expires {short_lbl(held)})"}
    return {"held": held, "near": near, "use": near, "roll": True,
            "txt": f"{month_of(near)} fut, roll to {month_of(held)} before {short_lbl(near)} "
                   f"(or {month_of(held)} from the start)"}


# ------------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--start", help="first meeting date, YYYY-MM-DD (default: today in IST)")
    ap.add_argument("--days", type=int, default=7, help="calendar days after --start to include (default 7)")
    ap.add_argument("--today", help="run date, YYYY-MM-DD (default: today in IST); entry status is relative to it")
    ap.add_argument("--lookback", type=int, default=7,
                    help="calendar days before --start searched for results already announced whose winners-trade "
                         "entry is still ahead (default 7)")
    ap.add_argument("--offline", action="store_true", help="use only files already in SCREENER_DL")
    a = ap.parse_args()

    now = datetime.now(IST)
    today = d(a.today) if a.today else now.date()
    start = d(a.start) if a.start else today
    end = start + timedelta(days=a.days)
    lb_from, lb_to = start - timedelta(days=max(a.lookback, 0)), start - timedelta(days=1)
    LAB = Path(os.environ.get("LAB_ROOT", "lab"))
    DL = Path(os.environ.get("SCREENER_DL", str(LAB / f"dl_screener_{today:%Y%m%d}")))
    OUT = Path(os.environ.get("OUT", str(REPO / "plans" / f"screener_{start}_to_{end}")))
    (OUT / "stocks").mkdir(parents=True, exist_ok=True)
    print(f"screener: meetings {start} to {end}, recent reporters {lb_from} to {lb_to}, run date {today}; "
          f"outputs -> {OUT}", flush=True)

    # ---------------------------------------------------------------- downloads
    dl = Downloader(DL, a.offline)
    api = "https://www.nseindia.com/api/"
    p_cal = dl.get(api + "event-calendar?index=equities", "event_calendar.json", api=True)
    p_bm = dl.get(api + f"corporate-board-meetings?index=equities&from_date={start:%d-%m-%Y}&to_date={end:%d-%m-%Y}",
                  f"board_meetings_{start:%Y%m%d}_{end:%Y%m%d}.json", api=True)
    p_bm_lb = None
    if a.lookback > 0:
        p_bm_lb = dl.get(api + f"corporate-board-meetings?index=equities&from_date={lb_from:%d-%m-%Y}"
                               f"&to_date={lb_to:%d-%m-%Y}", f"board_meetings_{lb_from:%Y%m%d}_{lb_to:%Y%m%d}.json",
                         api=True)
    p_hol = dl.get(api + "holiday-master?type=trading", "holiday_trading.json", api=True)
    p_lots = dl.get("https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv", "fo_mktlots.csv")
    if not p_lots:
        sys.exit("no F&O list (fo_mktlots.csv): cannot continue")
    p_ban = dl.get("https://nsearchives.nseindia.com/content/fo/fo_secban.csv", "fo_secban.csv")
    fo = parse_lots(p_lots)
    fo_set = set(fo)
    lot_table = parse_lot_table(p_lots)
    ban_td, ban_syms = parse_secban(p_ban)
    holidays, hol_years = parse_holidays(p_hol)

    panel = Panel(LAB)
    plast = d(panel.project_last)
    ca_to = end + timedelta(days=45)            # corporate actions up to about the last winners-trade exit
    p_ca = dl.get(api + f"corporates-corporateActions?index=equities&from_date={plast + timedelta(days=1):%d-%m-%Y}"
                        f"&to_date={ca_to:%d-%m-%Y}", f"corp_actions_{plast + timedelta(days=1):%Y%m%d}_{ca_to:%Y%m%d}.json",
                  api=True)
    ca, ca_list, ca_future = {}, [], []
    if p_ca:
        for x in json.loads(p_ca.read_text()):
            s = str(x.get("symbol", "")).strip()
            try:
                ex = nse_d(x["exDate"]).isoformat()
            except (KeyError, ValueError):
                continue
            kind, factor = ca_factor(str(x.get("subject", "")))
            if d(ex) > today:
                ca_future.append({"symbol": s, "ex": ex, "subject": str(x.get("subject", "")).strip(), "kind": kind})
                continue
            if kind and s in panel.col:
                prev = ca.get((s, ex))
                if prev and prev[1] and factor:
                    factor *= prev[1]
                ca[(s, ex)] = (kind, factor, str(x.get("subject", "")).strip())
                ca_list.append(f"{s} {ex} {x.get('subject', '')}".strip())

    # append cash-bhavcopy days after the project's last session, up to the run date
    x = plast + timedelta(days=1)
    missing_days = []
    while x <= today:
        if x.weekday() < 5 and x.isoformat() not in holidays:
            pb = dl.get(f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{x:%Y%m%d}_F_0000.csv.zip",
                        f"BhavCopy_NSE_CM_{x:%Y%m%d}.csv.zip", refresh=False)
            pi = dl.get(f"https://nsearchives.nseindia.com/content/indices/ind_close_all_{x:%d%m%Y}.csv",
                        f"ind_close_all_{x:%d%m%Y}.csv", refresh=False)
            if pb and pi:
                bh = pd.read_csv(pb, compression="zip")
                ix = pd.read_csv(pi)
                nrow = ix[ix["Index Name"].astype(str).str.strip().str.lower() == "nifty 50"]
                if len(nrow):
                    panel.append_day(x.isoformat(), bh, float(nrow["Closing Index Value"].iloc[0]), ca)
                else:
                    missing_days.append(f"{x} (no Nifty 50 close)")
            else:
                missing_days.append(f"{x} ({'bhavcopy' if not pb else 'index file'} not available yet)")
        x += timedelta(days=1)
    panel.finish()
    latest = panel.sessions[-1]
    i_latest = len(panel.sessions) - 1
    print(f"price data: project to {panel.project_last}, appended {len(panel.appended)} bhavcopy days, latest close "
          f"{latest}; not available: {missing_days or 'none'}", flush=True)

    # F&O bhavcopy of the latest session (else the newest one available): futures expiries, lot sizes
    fo_bh, fo_bh_day = {}, None
    for k in range(0, 6):
        if i_latest - k < 0:
            break
        dday = d(panel.sessions[i_latest - k])
        pf = dl.get(f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{dday:%Y%m%d}_F_0000.csv.zip",
                    f"BhavCopy_NSE_FO_{dday:%Y%m%d}.csv.zip", refresh=False)
        if pf:
            fo_bh, fo_bh_day = parse_fo_bhav(pf), dday.isoformat()
            break

    horizon = end + timedelta(days=50)          # room for Day+1, 20 sessions after the reaction day and the expiry
    cal = Calendar(panel.sessions, holidays, horizon)
    hol_warn = [] if {start.year, horizon.year} <= hol_years else \
        [f"NSE holiday list covers {sorted(hol_years)} only: later dates assume every weekday is a session"]
    today_is_session = today.weekday() < 5 and today.isoformat() not in holidays
    today_note = "" if today_is_session else \
        f"{today:%a %d-%b-%Y} is not a trading session ({holidays.get(today.isoformat(), 'weekend')})"
    next_session = cal.next_after(today)

    # futures expiries listed in the F&O bhavcopy; later months by the monthly rule
    stf_exp = sorted({e for s, v in fo_bh.items() for e, r in v.items() if r["kind"] == "STF"})
    rule_exp = []
    y, mth = d(latest).year, d(latest).month
    for _ in range(5):
        rule_exp.append(cal.monthly_expiry(y, mth))
        y, mth = (y + 1, 1) if mth == 12 else (y, mth + 1)
    rule_exp = [e for e in rule_exp if e > latest]

    def expiries_for(sym: str) -> list[str]:
        listed = sorted(fo_bh.get(sym, {})) or stf_exp
        return listed + [e for e in rule_exp if listed and e > listed[-1]]

    def contract_info(sym: str, entry: str | None, exit_: str | None) -> dict:
        if not entry or not exit_:
            return {"txt": "-", "lot": None, "notional": None, "use": None}
        k = pick_contract(cal, expiries_for(sym), entry, exit_)
        lot = fo_bh.get(sym, {}).get(k["use"], {}).get("lot") if k["use"] else None
        if lot is None and k["use"]:
            lot = lot_table.get(sym, {}).get(d(k["use"]).strftime("%b-%y").upper())
        j = panel.col.get(sym)
        px = panel.C[i_latest, j] if j is not None else np.nan
        if sym == "NIFTY":
            px = panel.N[i_latest]
        k.update(lot=lot, close=px, notional=lot * px if lot and isnum(px) else None)
        return k

    # ---------------------------------------------------------------- project data
    ev = pd.read_csv(LAB / "sector_lab" / "data" / "events.csv")
    ev = ev.sort_values(["symbol", "qn"]).reset_index(drop=True)
    nsec = pd.read_csv(REPO / "results" / "nifty_sector_3day" / "results_3day.csv",
                       usecols=["symbol", "qn", "nifty_sector", "custom_sector"]).sort_values("qn")
    sector = nsec.groupby("symbol").nifty_sector.last().to_dict()
    custom = nsec.groupby("symbol").custom_sector.last().to_dict()
    n500 = {}
    p500 = LAB / "dl_nifty_sector_lists" / "ind_nifty500list.csv"
    if p500.exists():
        t = pd.read_csv(p500)
        n500 = dict(zip(t.Symbol.astype(str).str.strip(), t.Industry.astype(str).str.strip()))
    auto_syms = {s for s, v in custom.items() if v == AUTO_CUSTOM} | {s for s, v in sector.items() if v == AUTO_NSE} \
        | {s for s, v in n500.items() if v == AUTO_NSE}

    def sector_of(s):
        return sector.get(s) or n500.get(s) or (ev[ev.symbol == s].industry.iloc[-1] if (ev.symbol == s).any() else "")

    # ---------------------------------------------------------------- checks of the conventions on the project data
    checks = list(panel.checks)
    win_bad = 0
    pc = Calendar(pd.read_csv(LAB / "sector_lab" / "data" / "sessions.csv").day.tolist(), holidays, plast)
    for r in ev.itertuples():
        w = pc.window(r.results_date, r.timing)
        if not w or (w["cutoff"], w["day_m1"], w["result_day"], w["day_p1"], w["reaction_day"]) != \
                (r.cutoff, r.day_m1, r.result_day, r.day_p1, r.reaction_day):
            win_bad += 1
    checks.append(f"window convention: recomputed cutoff / Day-1 / Result day / Day+1 / reaction day from results date "
                  f"and timing for all {len(ev)} past results; mismatches with events.csv: {win_bad}")
    t_bad = 0
    for r in ev.itertuples():
        try:
            tt = datetime.strptime(f"{r.results_date} {r.results_time}", "%Y-%m-%d %H:%M")
        except (TypeError, ValueError):
            continue
        t_bad += release_timing(tt, pc) != r.timing
    checks.append(f"release-time rule (before 09:15 / to 15:29 / from 15:30 on a trading day; non-trading day) "
                  f"applied to the {len(ev)} past release times: labels different from events.csv timing: {t_bad}")
    td = []
    for r in ev.itertuples():
        j = panel.col.get(r.symbol)
        if j is None or not isnum(r.three_day):
            continue
        rr = [panel.R[int(k), j] for k in (r.i_m1, r.i_rd, r.i_p1)]
        td.append(abs(sum(rr) - r.three_day))
    checks.append(f"three-day sum: recomputed from returns.csv for {len(td)} results; max abs difference vs "
                  f"events.csv {max(td):.1e}")

    # signals vs the project's TA panel at the qn 21 cutoffs (same code path as for the upcoming results)
    pta = LAB / "ta" / "build" / "events_ta.csv"
    val_rows = []
    if pta.exists():
        ta = pd.read_csv(pta, usecols=["symbol", "qn", "cutoff", "i_cut", "lag_pct", "vol_ratio_5_60", "rsi14"])
        q21 = ta[ta.qn == ta.qn.max()]
        for r in q21.itertuples():
            c = int(r.i_cut)
            val_rows.append({"symbol": r.symbol, "cutoff": r.cutoff, "lag_project": r.lag_pct,
                             "lag_screener": panel.lag_pct(r.symbol, c), "vol_project": r.vol_ratio_5_60,
                             "vol_screener": panel.vol_ratio(r.symbol, c), "rsi_project": r.rsi14,
                             "rsi_screener": panel.rsi14(r.symbol, c)})
        V = pd.DataFrame(val_rows)
        for k in ("lag", "vol", "rsi"):
            dlt = (V[f"{k}_project"] - V[f"{k}_screener"]).abs()
            both = V[f"{k}_project"].notna() & V[f"{k}_screener"].notna()
            one = V[f"{k}_project"].notna() ^ V[f"{k}_screener"].notna()
            checks.append(f"{dict(lag='21-session lag vs Nifty', vol='5/60 volume ratio', rsi='RSI(14)')[k]} at the "
                          f"{len(V)} cutoffs of the latest project quarter (qn {int(q21.qn.max())}, cutoffs "
                          f"{q21.cutoff.min()} to {q21.cutoff.max()}): max abs difference vs events_ta.csv "
                          f"{dlt[both].max():.1e} on {int(both.sum())} values, {int(one.sum())} present in only one")
        V.sort_values(["cutoff", "symbol"]).to_csv(OUT / "validation_qn_last.csv", index=False, float_format="%.6g")
    # the bhavcopy and index file of the project's last session against the project's own close, volume and Nifty
    pb0 = dl.get(f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{plast:%Y%m%d}_F_0000.csv.zip",
                 f"BhavCopy_NSE_CM_{plast:%Y%m%d}.csv.zip", refresh=False)
    pi0 = dl.get(f"https://nsearchives.nseindia.com/content/indices/ind_close_all_{plast:%d%m%Y}.csv",
                 f"ind_close_all_{plast:%d%m%Y}.csv", refresh=False)
    if pb0 and pi0:
        b0 = pd.read_csv(pb0, compression="zip")
        b0 = b0[b0.SctySrs.astype(str).str.strip() == "EQ"].drop_duplicates("TckrSymb").set_index("TckrSymb")
        oh0 = pd.read_csv(LAB / "ta" / "build" / "adjusted_ohlcv.csv.gz", usecols=["day", "symbol", "raw_close", "volume",
                                                                                  "volume_factor"])
        oh0 = oh0[oh0.day == panel.project_last].set_index("symbol").join(b0[["ClsPric", "TtlTradgVol"]], how="inner")
        i0 = pd.read_csv(pi0)
        n0 = float(i0[i0["Index Name"].astype(str).str.strip().str.lower() == "nifty 50"]["Closing Index Value"].iloc[0])
        pidx = pd.read_csv(LAB / "sector_lab" / "data" / "index_close.csv", usecols=["day", "Nifty 50"]).set_index("day")
        checks.append(f"source check on {panel.project_last}: bhavcopy close equals the project's raw close for "
                      f"{int((oh0.raw_close - oh0.ClsPric).abs().lt(1e-6).sum())} of {len(oh0)} symbols, volume equals "
                      f"(to 1e-7, the project file keeps 8 digits) for "
                      f"{int((oh0.volume / oh0.volume_factor / oh0.TtlTradgVol - 1).abs().lt(1e-7).sum())}; Nifty 50 "
                      f"{n0:.2f} vs project {float(pidx.loc[panel.project_last, 'Nifty 50']):.2f}")
    if panel.appended:
        checks.append(f"appended {len(panel.appended)} bhavcopy sessions {panel.appended[0]} to {panel.appended[-1]} "
                      f"(series EQ close and total traded quantity); Nifty 50 from ind_close_all")
    for s in fo:
        if s not in panel.col:
            panel.flag(s, "not in the project's price data: no signals")

    # futures: listed expiries against the monthly rule, lot sizes against fo_mktlots.csv
    if fo_bh:
        rule_listed = [cal.monthly_expiry(d(e).year, d(e).month) for e in stf_exp]
        shifts = [f"{month_of(e)} {short_lbl(e)} (last Tuesday {short_lbl(_last_tuesday(e))} is a holiday)"
                  for e in stf_exp if _last_tuesday(e) != e]
        lot_bad, lot_n = [], 0
        for s, v in fo_bh.items():
            for e, r in v.items():
                mk = d(e).strftime("%b-%y").upper()
                ref = lot_table.get(s, {}).get(mk)
                if ref is not None:
                    lot_n += 1
                    if ref != r["lot"]:
                        lot_bad.append(f"{s} {mk} {r['lot']} vs {ref}")
        checks.append(f"F&O bhavcopy {fo_bh_day}: stock futures expiries {', '.join(stf_exp)}; equal to the monthly "
                      f"rule (last Tuesday, earlier if a holiday): {rule_listed == stf_exp}"
                      + (f"; holiday shifts: {'; '.join(shifts)}" if shifts else "")
                      + f"; lot sizes equal to fo_mktlots.csv for {lot_n - len(lot_bad)} of {lot_n} contracts"
                      + (f" (differ: {', '.join(lot_bad[:8])})" if lot_bad else ""))
        no_fut = [s for s in fo if s not in fo_bh]
        checks.append(f"stock futures listed for {len(fo) - len(no_fut)} of {len(fo)} F&O stocks"
                      + (f" (missing: {', '.join(no_fut[:10])})" if no_fut else ""))
    else:
        checks.append("F&O bhavcopy not available: contracts use the monthly expiry rule and fo_mktlots.csv lot sizes")
    checks.append(f"F&O ban list (fo_secban.csv): trade date {ban_td or 'not parsed'}, {len(ban_syms)} securities "
                  f"({', '.join(sorted(ban_syms)) or 'none'}); next session {next_session}"
                  + ("" if ban_td == next_session else " - the list is not for the next session: re-check it"))

    # ---------------------------------------------------------------- last-4 averages of all current F&O stocks
    last4 = {}
    for s, g in ev.groupby("symbol"):
        if s in fo_set and len(g) >= 4:
            last4[s] = 100 * g.tail(4).three_day.dropna().mean()
    L4 = pd.Series(last4).dropna()
    L4_pct = L4.rank(pct=True)
    L4_rank = L4.rank(ascending=False, method="min").astype(int)

    # ---------------------------------------------------------------- meetings in the window
    meet = parse_meetings(p_cal, p_bm, fo_set, start, end)
    order = sorted(meet.values(), key=lambda m: (m["meeting_date"], m["symbol"]))
    print(f"F&O stocks with a results meeting {start} to {end}: {len(order)}", flush=True)

    # each company's past results board meetings (NSE board-meeting list for one symbol)
    bm_dates: dict[str, list[str] | None] = {}
    for m in order:
        s = m["symbol"]
        pth = dl.get(api + f"corporate-board-meetings?index=equities&symbol={urllib.parse.quote(s)}",
                     f"bm_hist_{safe_name(s)}.json", api=True, refresh=False)
        bm_dates[s] = fin_meeting_dates(load_json_list(pth))
    n_hist = sum(v is not None for v in bm_dates.values())
    print(f"board-meeting histories available for {n_hist} of {len(order)}", flush=True)

    calendar_rows, summary_rows, history_rows, per_stock = [], [], [], {}
    trig_checks, mt_checks = [], {"rows": 0, "results": 0, "agree": 0, "same_day_release": 0, "changed": []}
    for m in order:
        s = m["symbol"]
        g = ev[ev.symbol == s].copy()
        company = m["company"] or (g.company.iloc[-1] if len(g) else s)
        # usual timing: all past results, and separately the ones announced on a trading day (they set the reaction day)
        tc = Counter(g.timing.dropna())
        ac, dmb, nt = (tc.get("After close", 0), tc.get("During market", 0) + tc.get("Before open", 0),
                       tc.get("Non-trading day", 0))
        n_t, n_td = ac + dmb + nt, ac + dmb
        cats = {"After close": ac, "During market": dmb, "Non-trading day": nt}
        # "Before open" reacts on the Result day like "During market" (analyze_events.py); name it in the labels
        bo = tc.get("Before open", 0)
        nm = {"During market": "During market or before open"} if bo else {}
        if n_t:
            ranked = sorted(cats.values(), reverse=True)
            if ranked[0] == ranked[1]:
                usual = "Mixed"
                usual_txt = "Mixed: " + ", ".join(f"{nm.get(k, k).lower()} {v}" for k, v in cats.items() if v) + f" (of {n_t})"
            else:
                usual = max(cats, key=cats.get)
                others = ", ".join(f"{nm.get(k, k).lower()} {v}" for k, v in cats.items() if k != usual and v)
                usual_txt = f"{nm.get(usual, usual)} {cats[usual]}/{n_t}" + (f" ({others})" if others else "")
                usual = nm.get(usual, usual)
        else:
            usual, usual_txt = "Unknown", "no past results"
        td_usual = ("After close" if ac > dmb else "During market" if dmb > ac else "Mixed") if n_td else "Unknown"
        mixed_t = td_usual in ("Mixed", "Unknown") or max(ac, dmb) / n_td < 0.75
        md = m["meeting_date"]
        on_session = cal.is_session(md)
        split = f"{ac} after the close, {dmb - bo} during market hours" + (f", {bo} before the open" if bo else "")

        # likely reaction day: from the company's past board-meeting dates when NSE has them, else from its timing
        mt = meeting_timing(g, bm_dates[s], cal) if bm_dates.get(s) is not None else None
        timing_react = "Day+1" if td_usual == "After close" else "Result day"
        if mt:
            mt_checks["rows"] += 1
            mt_checks["results"] += mt["n"]
            for x in mt["rows"]:
                if x["on_session"] and not x["after_midnight"]:
                    mt_checks["same_day_release"] += 1
                    mt_checks["agree"] += x["offset"] == (1 if x["timing"] == "After close" else 0)
        use_mt = bool(mt and mt["n_td"] >= 4 and mt["likely"] != "Mixed")
        if not on_session:
            likely, mixed, react_src = "Result day", False, "non-trading-day meeting"
            react_basis = "Result day: the meeting is on a non-trading day, so the first session after it reacts"
        elif use_mt:
            likely, mixed, react_src = mt["likely"], mt["mixed"], "board-meeting history"
            am = mt["next_after_midnight"]
            react_basis = (f"{likely}: of its {mt['n_td']} results matched to an NSE board-meeting date on a trading "
                           f"day, {mt['next']} reacted the session after the meeting (after the close"
                           + (f", {am} of them released after midnight" if am else "") + f"), {mt['same']} on the "
                           f"meeting day" + (f", {mt['other']} later" if mt["other"] else "")
                           + f"; the last {mt['recent_n']}: {mt['recent_next']} next session, {mt['recent_same']} "
                           f"meeting day" + ("; mixed, it could be the other day" if mixed else ""))
        else:
            likely, mixed, react_src = timing_react, mixed_t, "release-time history"
            why = ("NSE board-meeting history not available" if mt is None else
                   f"only {mt['n_td']} results matched to a board-meeting date" if mt["n_td"] < 4 else
                   "board-meeting history evenly split")
            if td_usual in ("After close", "During market"):
                react_basis = (f"{likely}: of its results on trading days, {split}" + (
                    "; mixed, it could be the other day" if mixed else "") + f" ({why})")
            else:
                react_basis = ("Result day if the numbers come before 15:30, Day+1 if after "
                               + (f"(trading-day history split: {split})" if n_td else "(no trading-day history)")
                               + f" ({why})")
        react_short = likely + ((" (or Day+1)" if likely == "Result day" else " (or Result day)") if mixed else "")
        w = cal.window(md, "After close" if likely == "Day+1" else "During market")
        if not w:
            continue
        w_t = cal.window(md, "After close" if td_usual == "After close" else "During market")
        if w_t and w_t["reaction_day"] != w["reaction_day"]:
            mt_checks["changed"].append(f"{s} {short_lbl(w_t['reaction_day'])} -> {short_lbl(w['reaction_day'])}")
        hol_in = cal.holidays_between(w["cutoff"], w["day_p1"])
        cut = w["cutoff"]
        if d(cut) < today:
            status = "missed"
            status_txt = f"missed (cutoff close {short_lbl(cut)} has passed)"
        elif d(cut) == today:
            status, status_txt = "today", "today (buy at today's close if the rule fires)"
        else:
            status, status_txt = cut, f"{short_lbl(cut)} close"
        # run-up straddle (marginal trade): buy 5 sessions before the last close before the numbers
        pre = w["result_day"] if (likely == "Day+1" and on_session) else w["day_m1"]
        ru_entry = cal.shift(pre, -5)
        fexp = cal.front_expiry(w["reaction_day"])
        ru_gap = (cal.pos[fexp] - cal.pos[pre]) if fexp else None
        ru_ok = ru_gap is not None and ru_gap <= 14
        if not ru_ok:
            ru_status = "skip (front expiry more than 14 sessions after the exit)"
        elif ru_entry and d(ru_entry) < today:
            ru_status = "entry passed"
        else:
            ru_status = "today" if ru_entry and d(ru_entry) == today else f"buy {short_lbl(ru_entry)}"
        t2_buy = cal.shift(w["reaction_day"], 1)
        t2_exit = cal.shift(w["reaction_day"], 20)

        # signals: at the cutoff close if it is in the data (final), else at the latest close (provisional)
        in_data = cut in panel.pos
        ci = panel.pos[cut] if in_data else i_latest
        sig_status = "final" if in_data else f"provisional to {short_lbl(cut)}"
        basis = f"at the cutoff close {short_lbl(cut)} (final)" if in_data else \
            f"at the latest close {short_lbl(latest)} (provisional to the {short_lbl(cut)} cutoff close: the values " \
            f"keep moving until then)"
        lag, vr, rs14 = panel.lag_pct(s, ci), panel.vol_ratio(s, ci), panel.rsi14(s, ci)
        lag_l, vr_l, rs_l = panel.lag_pct(s, i_latest), panel.vol_ratio(s, i_latest), panel.rsi14(s, i_latest)
        if not (isnum(lag) and isnum(vr)):
            rule = "n/a"
        elif lag < LAG_CUT and vr >= VOL_STRICT:
            rule = "fires (1.0x and 1.3x)"
        elif lag < LAG_CUT and vr >= VOL_CUT:
            rule = "fires (1.0x)"
        elif lag < LAG_CUT:
            rule = "no (lag yes, volume quiet)"
        else:
            rule = "no"
        if rule.startswith("fires"):
            rule_txt = rule + (" - entry missed" if status == "missed" else ("" if in_data else " - provisional"))
        else:
            rule_txt = rule + ("" if in_data or rule == "n/a" else " (provisional)")

        # Trade 2 (results winners): a conditional buy only with RSI(14) > 50 at the cutoff
        if not isnum(rs14):
            t2_short, t2_txt = "n/a (no RSI)", "no RSI(14): no Trade 2 call"
        elif rs14 > RSI_CUT:
            t2_short = f"buy if a winner (open {short_lbl(t2_buy)})"
            t2_txt = (f"conditional buy: if the reaction day ({short_lbl(w['reaction_day'])}) beats Nifty by more than "
                      f"4%, buy at the next open ({short_lbl(t2_buy)}) and hold 20 sessions against Nifty (to about "
                      f"{short_lbl(t2_exit)})")
        else:
            t2_short, t2_txt = "skip (RSI <= 50)", "skip (RSI <= 50): winners with RSI 50 or below made +0.04%"
        if isnum(rs14) and not in_data:
            t2_short += f", RSI provisional to {short_lbl(cut)}"
            t2_txt += f" (RSI provisional to the {short_lbl(cut)} cutoff close: re-check it then)"

        # Trade 1 trigger levels when the cutoff is still ahead
        trig = None
        if not in_data and cut in cal.pos and cal.pos[cut] > cal.pos[latest]:
            trig = panel.trigger_levels(s, cal.pos[cut] - cal.pos[latest])
            if trig:
                trig_checks.append(trig)
        # single-day events inside the windows that end at the cutoff
        c_end = panel.pos[cut] if in_data else i_latest + (cal.pos[cut] - cal.pos[latest] if cut in cal.pos else 0)
        events = panel.single_day_events(s, c_end)
        # contracts, lot, ban
        k1 = contract_info(s, cut, w["day_p1"])
        k2 = contract_info(s, t2_buy, t2_exit)
        kn = contract_info("NIFTY", t2_buy, t2_exit)
        banned = s in ban_syms

        # history rows
        mt_by_qn = {x["qn"]: x for x in mt["rows"]} if mt else {}
        flags_fo = [str(v) == "True" for v in g.in_fo.tolist()]
        first_fo = flags_fo.index(True) if True in flags_fo else None
        hrows = []
        for kq, r in enumerate(g.itertuples()):
            react_on = "Day+1" if r.timing == "After close" else "Result day"
            rr = r.ret_dp1 if react_on == "Day+1" else r.ret_rd
            ir = int(r.i_react) if isnum(r.i_react) else None
            nr = panel.nifty_ret(ir) if ir is not None else np.nan
            rxn = 100 * (rr - nr) if isnum(rr) and isnum(nr) else np.nan
            py = r.pat_yoy
            sign = "up" if isnum(py) and py > 0 else ("down" if isnum(py) else "n/a")
            fo_status = "yes" if flags_fo[kq] else ("no (before F&O entry)" if first_fo is None or kq < first_fo
                                                     else "no (out of F&O)")
            mx = mt_by_qn.get(int(r.qn))
            rvm = "" if not mx else {0: "meeting day", 1: "next session"}.get(mx["offset"], f"{mx['offset']:+d} sessions")
            hrows.append({
                "symbol": s, "company": r.company,
                "in_fo": {"True": "yes", "False": "no"}.get(str(r.in_fo), ""), "fo_status": fo_status,
                "quarter": r.quarter, "qn": int(r.qn), "period": r.period, "results_date": r.results_date,
                "results_time": r.results_time, "timing": r.timing,
                "meeting_date": mx["meeting"] if mx else "", "reaction_vs_meeting": rvm,
                "sales_yoy_pct": sp(100 * r.sales_yoy) if isnum(r.sales_yoy) else "",
                "pat_yoy_pct": sp(100 * r.pat_yoy) if isnum(r.pat_yoy) else "",
                "sales_qoq_pct": sp(100 * r.sales_qoq) if isnum(r.sales_qoq) else "",
                "pat_qoq_pct": sp(100 * r.pat_qoq) if isnum(r.pat_qoq) else "",
                "pat_yoy_sign": sign,
                "cutoff": r.cutoff, "day_m1": r.day_m1, "result_day": r.result_day, "day_p1": r.day_p1,
                "reaction_day": r.reaction_day, "reaction_on": react_on,
                "day_m1_pct": sp(100 * r.ret_dm1) if isnum(r.ret_dm1) else "",
                "result_day_pct": sp(100 * r.ret_rd) if isnum(r.ret_rd) else "",
                "day_p1_pct": sp(100 * r.ret_dp1) if isnum(r.ret_dp1) else "",
                "three_day_pct": sp(100 * r.three_day) if isnum(r.three_day) else "",
                "nifty_3d_pct": sp(100 * r.nifty_3d) if isnum(r.nifty_3d) else "",
                "three_day_vs_nifty_pct": sp(100 * r.excess_nifty) if isnum(r.excess_nifty) else "",
                "reaction_pct": sp(100 * rr) if isnum(rr) else "",
                "nifty_reaction_pct": sp(100 * nr) if isnum(nr) else "",
                "reaction_vs_nifty_pct": sp(rxn),
                "winner": ("yes" if rxn > WIN_CUT else "no") if isnum(rxn) else "",
                "_td": 100 * r.three_day if isnum(r.three_day) else np.nan, "_xn": rxn,
                "_ex": 100 * r.excess_nifty if isnum(r.excess_nifty) else np.nan, "_py": py})
        history_rows += hrows
        H = pd.DataFrame(hrows)

        def stat(mask=None):
            x = H._td if mask is None else H._td[mask]
            x = x.dropna()
            return x

        if len(H):
            td_all = stat()
            good, bad = H._py.notna() & (H._py > 0), H._py.notna() & (H._py <= 0)
            tg, tb = stat(good), stat(bad)
            tf = stat(H.in_fo == "yes")
            best = H.loc[H._td.idxmax()] if td_all.size else None
            worst = H.loc[H._td.idxmin()] if td_all.size else None
            last = H.iloc[-1]
            xn = H._xn.dropna()
            summ = {
                "n_past": len(H), "n_past_in_fo": int((H.in_fo == "yes").sum()),
                "n_before_fo": int((H.fo_status == "no (before F&O entry)").sum()),
                "first_period": H.period.iloc[0], "last_period": last.period,
                "n_3d": int(td_all.size),
                "avg_3d": td_all.mean(), "median_3d": td_all.median(), "share_up": 100 * (td_all > 0).mean(),
                "fo_n": int(tf.size), "fo_avg": tf.mean() if tf.size else np.nan,
                "fo_median": tf.median() if tf.size else np.nan, "fo_up": 100 * (tf > 0).mean() if tf.size else np.nan,
                "avg_abs_3d": td_all.abs().mean(), "avg_3d_vs_nifty": H._ex.dropna().mean(),
                "best_period": best.period if best is not None else "", "best_3d": best._td if best is not None else np.nan,
                "worst_period": worst.period if worst is not None else "",
                "worst_3d": worst._td if worst is not None else np.nan,
                "last_3d": last._td, "good_n": int(tg.size), "good_avg": tg.mean() if tg.size else np.nan,
                "good_up": 100 * (tg > 0).mean() if tg.size else np.nan,
                "bad_n": int(tb.size), "bad_avg": tb.mean() if tb.size else np.nan,
                "bad_up": 100 * (tb > 0).mean() if tb.size else np.nan,
                "unclassified_n": int((H._py.isna() & H._td.notna()).sum()),
                "winners_n": int((xn > WIN_CUT).sum()), "losers_n": int((xn < -WIN_CUT).sum()), "xn_n": int(xn.size),
                "avg_xn": xn.mean() if xn.size else np.nan,
            }
        else:
            summ = {k: np.nan for k in ("avg_3d", "median_3d", "share_up", "avg_abs_3d", "avg_3d_vs_nifty", "best_3d",
                                        "worst_3d", "last_3d", "good_avg", "bad_avg", "good_up", "bad_up", "avg_xn",
                                        "fo_avg", "fo_median", "fo_up")}
            summ.update(n_past=0, n_past_in_fo=0, n_before_fo=0, first_period="", last_period="", best_period="",
                        worst_period="", good_n=0, bad_n=0, unclassified_n=0, winners_n=0, losers_n=0, xn_n=0, fo_n=0,
                        n_3d=0)
        l4 = L4.get(s, np.nan)
        l4_top = bool(isnum(l4) and L4_pct.get(s, 0) > 0.9)
        is_auto = s in auto_syms
        notes = [m["date_note"]] if m["date_note"] else []
        notes += panel.flags.get(s, [])
        if not len(H):
            notes.append("no past results in the project data (events.csv)")
        cas = [f"{x['subject']} (ex {short_lbl(x['ex'])})" for x in ca_future if x["symbol"] == s
               and cut <= x["ex"] <= (t2_exit or x["ex"])]
        if cas:
            notes.append("corporate action inside the trade windows: " + "; ".join(cas))

        trig_cols = {
            "trade1_sessions_to_cutoff": trig["k"] if trig else "",
            "trade1_base_day": trig["base_day"] if trig else "",
            "trade1_close_max_nifty_flat": f"{trig['close_max']:.2f}" if trig else "",
            "trade1_close_change_needed_pct": sp(trig["headroom_pct"]) if trig else "",
            "trade1_close_max_change_per_1pct_nifty": f"{trig['per_1pct_nifty']:.2f}" if trig else "",
            "trade1_volume_needed_1x": f"{trig['vol_need_1']:.0f}" if trig and isnum(trig["vol_need_1"]) else "",
            "trade1_volume_needed_1_3x": f"{trig['vol_need_13']:.0f}" if trig and isnum(trig["vol_need_13"]) else "",
            "trade1_volume_avg5": f"{trig['avg5']:.0f}" if trig else ""}
        cal_row = {
            "meeting_date": md, "weekday": d(md).strftime("%a"), "symbol": s, "company": company,
            "purpose": m["purpose"], "source": m["source"], "sector": sector_of(s),
            "usual_timing": usual, "timing_history": usual_txt,
            "share_during_market_pct": f"{100 * dmb / n_t:.0f}" if n_t else "",
            "share_after_close_pct": f"{100 * ac / n_t:.0f}" if n_t else "",
            "share_non_trading_day_pct": f"{100 * nt / n_t:.0f}" if n_t else "",
            "past_results_with_timing": n_t,
            "trading_day_usual": td_usual,
            "meeting_history_results": mt["n_td"] if mt else "",
            "meeting_history_next_session": mt["next"] if mt else "",
            "meeting_history_meeting_day": mt["same"] if mt else "",
            "meeting_history_last8_next": mt["recent_next"] if mt else "",
            "meeting_history_last8_meeting_day": mt["recent_same"] if mt else "",
            "cutoff": w["cutoff"], "day_m1": w["day_m1"], "result_day": w["result_day"], "day_p1": w["day_p1"],
            "meeting_on_trading_day": "yes" if on_session else "no",
            "expected_reaction_day": w["reaction_day"], "reaction_on": react_short, "reaction_basis": react_basis,
            "reaction_rule_source": react_src,
            "reaction_day_by_timing_rule": w_t["reaction_day"] if w_t else "",
            "holiday_in_window": "; ".join(hol_in),
            "trade1_check_cutoff": status, "trade1_check_note": status_txt,
            "signal_asof": panel.sessions[ci], "signal_status": sig_status, "signal_basis": basis,
            **trig_cols,
            "trade1_contract": k1["txt"], "trade1_lot": k1["lot"] or "",
            "trade1_notional_rs": f"{k1['notional']:.0f}" if k1["notional"] else "",
            "trade2_status": t2_short,
            "winners_trade_buy_next_open_if_winner": t2_buy or "", "winners_trade_exit_close": t2_exit or "",
            "trade2_contract": k2["txt"], "trade2_lot": k2["lot"] or "",
            "trade2_notional_rs": f"{k2['notional']:.0f}" if k2["notional"] else "",
            "trade2_nifty_hedge": kn["txt"], "nifty_lot": kn["lot"] or "",
            "nifty_lot_notional_rs": f"{kn['notional']:.0f}" if kn["notional"] else "",
            "fo_ban": ("yes" if banned else "no") if ban_td else "", "fo_ban_list_date": ban_td or "",
            "runup_entry": ru_entry or "", "runup_exit_close": pre, "runup_front_expiry": fexp or "",
            "runup_sessions_exit_to_expiry": ru_gap if ru_gap is not None else "", "runup_status": ru_status,
            "single_day_events": "; ".join(event_txt(e) for e in events),
            "notes": "; ".join(notes)}
        calendar_rows.append(cal_row)

        srow = {
            "results_date": md, "symbol": s, "company": company, "sector": sector_of(s),
            "auto_sector": "yes" if is_auto else "no", "usual_timing": usual_txt,
            "cutoff": w["cutoff"], "day_m1": w["day_m1"], "result_day": w["result_day"], "day_p1": w["day_p1"],
            "expected_reaction_day": w["reaction_day"], "holiday_in_window": "; ".join(hol_in),
            "trade1_check_cutoff": status,
            "n_past": summ["n_past"], "n_past_in_fo": summ["n_past_in_fo"], "n_before_fo": summ["n_before_fo"],
            "periods": f"{summ['first_period']} to {summ['last_period']}" if summ["n_past"] else "",
            "in_fo_n_3d": summ["fo_n"], "in_fo_avg_3d_pct": sp(summ["fo_avg"]),
            "in_fo_median_3d_pct": sp(summ["fo_median"]),
            "in_fo_share_up_pct": f"{summ['fo_up']:.0f}" if isnum(summ["fo_up"]) else "",
            "all_n_3d": summ["n_3d"],
            "avg_3d_pct": sp(summ["avg_3d"]), "median_3d_pct": sp(summ["median_3d"]),
            "share_up_pct": f"{summ['share_up']:.0f}" if isnum(summ["share_up"]) else "",
            "avg_abs_3d_pct": f"{summ['avg_abs_3d']:.2f}" if isnum(summ["avg_abs_3d"]) else "",
            "avg_3d_vs_nifty_pct": sp(summ["avg_3d_vs_nifty"]),
            "best_period": summ["best_period"], "best_3d_pct": sp(summ["best_3d"]),
            "worst_period": summ["worst_period"], "worst_3d_pct": sp(summ["worst_3d"]),
            "last_period": summ["last_period"], "last_3d_pct": sp(summ["last_3d"]),
            "last4_avg_pct": sp(l4), "last4_rank": f"{L4_rank[s]} of {len(L4)}" if s in L4_rank else "",
            "last4_top_tenth": ("yes" if l4_top else "no") if isnum(l4) else "",
            "pat_up_yoy_n": summ["good_n"], "pat_up_yoy_avg_3d_pct": sp(summ["good_avg"]),
            "pat_up_yoy_share_up_pct": f"{summ['good_up']:.0f}" if isnum(summ["good_up"]) else "",
            "pat_down_yoy_n": summ["bad_n"], "pat_down_yoy_avg_3d_pct": sp(summ["bad_avg"]),
            "pat_down_yoy_share_up_pct": f"{summ['bad_up']:.0f}" if isnum(summ["bad_up"]) else "",
            "no_pat_yoy_n": summ["unclassified_n"],
            "winners_n": summ["winners_n"], "losers_n": summ["losers_n"], "reactions_n": summ["xn_n"],
            "avg_reaction_vs_nifty_pct": sp(summ["avg_xn"]),
            "signal_asof": panel.sessions[ci], "signal_status": sig_status, "signal_basis": basis,
            "lag_vs_nifty_21d_pct": sp(lag), "stock_21d_pct": sp(panel.stock21(s, ci)),
            "nifty_21d_pct": sp(panel.nifty21(ci)), "vol_ratio_5_60": f"{vr:.2f}" if isnum(vr) else "",
            "lag10_volume_rule": rule, "rsi14": f"{rs14:.1f}" if isnum(rs14) else "",
            "rsi14_above_50": ("yes" if rs14 > RSI_CUT else "no") if isnum(rs14) else "",
            "trade2_status": t2_short,
            "lag_latest_pct": sp(lag_l), "vol_ratio_latest": f"{vr_l:.2f}" if isnum(vr_l) else "",
            "rsi14_latest": f"{rs_l:.1f}" if isnum(rs_l) else "",
            **trig_cols,
            "fo_ban": cal_row["fo_ban"], "single_day_events": cal_row["single_day_events"],
            "runup_status": ru_status, "notes": "; ".join(notes)}
        summary_rows.append(srow)
        per_stock[s] = {"cal": cal_row, "sum": srow, "summ": summ, "H": H, "rule_txt": rule_txt, "status_txt": status_txt,
                        "react_basis": react_basis, "react_short": react_short, "usual": usual, "likely": likely,
                        "mixed": mixed, "react_src": react_src, "mt": mt,
                        "lag": lag, "vr": vr, "rsi": rs14, "l4": l4, "l4_top": l4_top, "sig_status": sig_status,
                        "auto": is_auto, "in_data": in_data, "ci": ci, "t2_buy": t2_buy, "t2_exit": t2_exit,
                        "t2_short": t2_short, "t2_txt": t2_txt, "trig": trig, "events": events, "k1": k1, "k2": k2,
                        "kn": kn, "banned": banned, "cut": cut,
                        "ru_entry": ru_entry, "pre": pre, "fexp": fexp, "ru_status": ru_status}

    # ---------------------------------------------------------------- recent reporters (Trade 2 entry still ahead)
    recent, recent_passed, recent_missing = [], [], []
    lb_meet = {}
    for e in (load_json_list(p_bm_lb) or []):
        s, purpose = str(e.get("bm_symbol", "")).strip(), str(e.get("bm_purpose", ""))
        if s not in fo_set or "financial result" not in f"{purpose} {e.get('bm_desc', '')}".lower():
            continue
        try:
            mdt = nse_d(e["bm_date"])
        except (KeyError, ValueError):
            continue
        if lb_from <= mdt <= lb_to:
            lb_meet.setdefault(s, {"company": str(e.get("sm_name", "")).strip(), "dates": set()})["dates"].add(mdt)
    rx_check = []
    for s in sorted(lb_meet):
        mdt = max(lb_meet[s]["dates"])
        if mdt > today:
            recent_missing.append(f"{s} (meeting {short_lbl(mdt)}, after the run date)")
            continue
        pth = dl.get(api + f"corporate-announcements?index=equities&symbol={urllib.parse.quote(s)}"
                           f"&from_date={lb_from:%d-%m-%Y}&to_date={today:%d-%m-%Y}",
                     f"ann_{safe_name(s)}_{lb_from:%Y%m%d}_{today:%Y%m%d}.json", api=True)
        ann = load_json_list(pth)
        if ann is None:
            recent_missing.append(f"{s} (announcements not available)")
            continue
        f = find_results_filing(ann, mdt)
        if not f:
            recent_missing.append(f"{s} (meeting {short_lbl(mdt)}: no results filing found yet)")
            continue
        timing = release_timing(f["time"], cal)
        w = cal.window(f["time"].date().isoformat(), timing)
        if not w:
            recent_missing.append(f"{s} (no window)")
            continue
        react = w["reaction_day"]
        entry, exit_ = cal.shift(react, 1), cal.shift(react, 20)
        rec = {"symbol": s, "company": lb_meet[s]["company"], "meeting_date": mdt.isoformat(),
               "release": f["time"].strftime("%Y-%m-%d %H:%M:%S"), "release_desc": f["desc"],
               "release_text": f["text"], "timing": timing, "result_session": w["result_day"], "cutoff": w["cutoff"],
               "reaction_day": react, "entry_open": entry or "", "exit_close": exit_ or ""}
        if not entry or not next_session or entry < next_session:
            recent_passed.append(f"{s} (released {f['time']:%d-%b %H:%M}, reaction {short_lbl(react)}, "
                                 f"entry {short_lbl(entry)})")
            continue
        j = panel.col.get(s)
        cut = w["cutoff"]
        rs_ = panel.rsi14(s, panel.pos[cut]) if cut in panel.pos else panel.rsi14(s, i_latest)
        rec["rsi14_cutoff"] = rs_
        rec["rsi_status"] = "final" if cut in panel.pos else f"provisional to {short_lbl(cut)}"
        if react in panel.pos and j is not None:
            ir = panel.pos[react]
            rr, nr = panel.R[ir, j], panel.nifty_ret(ir)
            rec.update(reaction_pct=100 * rr, nifty_pct=100 * nr, rxn=100 * (rr - nr))
            bday = panel.raw.get(react)
            if bday is not None and s in bday.index:
                rx_check.append(abs(100 * (bday.loc[s, "ClsPric"] / bday.loc[s, "PrvsClsgPric"] - 1) - 100 * rr))
            if not isnum(rec["rxn"]):
                verdict = "no price data"
            elif rec["rxn"] > WIN_CUT and isnum(rs_) and rs_ > RSI_CUT:
                verdict = f"buy at the {short_lbl(entry)} open"
            elif rec["rxn"] > WIN_CUT:
                verdict = "skip (RSI <= 50)"
            else:
                verdict = "not a winner"
        else:
            rec.update(reaction_pct=np.nan, nifty_pct=np.nan, rxn=np.nan)
            if j is None:
                verdict = "no price data"
            elif isnum(rs_) and rs_ > RSI_CUT:
                verdict = (f"pending: if the {short_lbl(react)} close beats Nifty by more than 4%, buy at the "
                           f"{short_lbl(entry)} open")
            else:
                verdict = f"pending, but skip even if a winner (RSI <= 50)"
        rec["verdict"] = verdict
        rec["contract"] = contract_info(s, entry, exit_)
        rec["hedge"] = contract_info("NIFTY", entry, exit_)
        rec["banned"] = s in ban_syms
        rec["events"] = panel.single_day_events(s, panel.pos[cut]) if cut in panel.pos else []
        recent.append(rec)
    recent.sort(key=lambda r: (r["entry_open"], {"b": 0, "p": 1, "s": 2, "n": 3}.get(r["verdict"][0], 4), r["symbol"]))
    print(f"recent reporters ({lb_from} to {lb_to}): {len(lb_meet)} F&O results meetings; entry still ahead: "
          f"{len(recent)}; entry passed: {len(recent_passed)}; not found: {len(recent_missing)}", flush=True)
    checks.append(f"recent reporters: {len(lb_meet)} F&O results board meetings {lb_from} to {lb_to}; results filing "
                  f"found in NSE announcements for {len(recent) + len(recent_passed)}"
                  + (f" (not found: {', '.join(recent_missing)})" if recent_missing else "")
                  + f"; winners-trade entry on or after {next_session}: {len(recent)}; reaction-day return from the "
                  f"panel vs the bhavcopy (close / previous close) max abs difference "
                  + (f"{max(rx_check):.1e} pp on {len(rx_check)}" if rx_check else "n/a"))
    rc_rows = []
    for r in recent:
        rc_rows.append({
            "symbol": r["symbol"], "company": r["company"], "meeting_date": r["meeting_date"], "release": r["release"],
            "release_filing": r["release_desc"], "timing": r["timing"], "result_session": r["result_session"],
            "cutoff": r["cutoff"], "reaction_day": r["reaction_day"], "reaction_pct": sp(r["reaction_pct"]),
            "nifty_pct": sp(r["nifty_pct"]), "reaction_vs_nifty_pct": sp(r["rxn"]),
            "winner": ("yes" if r["rxn"] > WIN_CUT else "no") if isnum(r["rxn"]) else "pending",
            "rsi14_cutoff": f"{r['rsi14_cutoff']:.1f}" if isnum(r["rsi14_cutoff"]) else "",
            "rsi_status": r["rsi_status"], "verdict": r["verdict"], "entry_open": r["entry_open"],
            "exit_close": r["exit_close"], "contract": r["contract"]["txt"], "lot": r["contract"]["lot"] or "",
            "notional_rs": f"{r['contract']['notional']:.0f}" if r["contract"]["notional"] else "",
            "nifty_hedge": r["hedge"]["txt"], "fo_ban": ("yes" if r["banned"] else "no") if ban_td else "",
            "single_day_events": "; ".join(event_txt(e) for e in r["events"])})
    pd.DataFrame(rc_rows, columns=None if rc_rows else ["symbol"]).to_csv(OUT / "recent.csv", index=False)

    # ---------------------------------------------------------------- checks of the new parts
    if trig_checks:
        e1 = [abs(t["check_vr_1"] - VOL_CUT) for t in trig_checks if t["vol_need_1"] > 0 and isnum(t["check_vr_1"])]
        e13 = [abs(t["check_vr_13"] - VOL_STRICT) for t in trig_checks
               if t["vol_need_13"] > 0 and isnum(t["check_vr_13"])]
        ok1 = sum(t["check_vr_1"] >= VOL_CUT - 1e-9 for t in trig_checks if t["vol_need_1"] <= 0)
        n1 = sum(t["vol_need_1"] <= 0 for t in trig_checks)
        checks.append(f"Trade 1 trigger levels for {len(trig_checks)} cutoffs still ahead: plugging the highest close "
                      f"back in gives a lag of {LAG_CUT:.0f}% to within "
                      f"{max(abs(t['check_lag'] - LAG_CUT) for t in trig_checks):.1e} pp; plugging the needed volumes "
                      f"back in gives 5/60 ratios within {max(e1) if e1 else 0:.1e} of 1.0x ({len(e1)} stocks) and "
                      f"{max(e13) if e13 else 0:.1e} of 1.3x ({len(e13)}); where no volume is needed ({n1}), the ratio "
                      f"with zero volume is still >= 1.0x for {ok1}")
    checks.append(f"board-meeting histories (NSE corporate-board-meetings per symbol): available for {n_hist} of "
                  f"{len(order)} stocks, {mt_checks['results']} past results matched to a meeting date; for the "
                  f"{mt_checks['same_day_release']} released on the meeting date of a trading-day meeting, the "
                  f"reaction session relative to the meeting agrees with the release-time rule for "
                  f"{mt_checks['agree']}; likely reaction day different from the release-time rule: "
                  f"{', '.join(mt_checks['changed']) or 'none'}")
    nev = sum(len(p["events"]) for p in per_stock.values())
    checks.append(f"single-day events (move beyond +-{MOVE_FLAG:.0f}% in the 21-session lag window or volume above "
                  f"{VOL_FLAG:.0f}x the 60-session median in the volume base, windows ending at the cutoff): {nev} "
                  f"days for {sum(bool(p['events']) for p in per_stock.values())} of {len(per_stock)} stocks")

    # ---------------------------------------------------------------- write CSVs
    pd.DataFrame(calendar_rows).to_csv(OUT / "calendar.csv", index=False)
    pd.DataFrame(summary_rows).to_csv(OUT / "summary.csv", index=False)
    hist = pd.DataFrame(history_rows)
    hcols = [c for c in hist.columns if not c.startswith("_")]
    hist[hcols].to_csv(OUT / "history.csv", index=False)

    # history.csv three-day values against events.csv
    hb = pd.read_csv(OUT / "history.csv", usecols=["symbol", "qn", "three_day_pct", "in_fo", "fo_status"])
    mm = hb.merge(ev[["symbol", "qn", "three_day", "in_fo"]], on=["symbol", "qn"], how="left", suffixes=("", "_ev"))
    ok = mm.three_day_pct.isna() & mm.three_day.isna() | ((mm.three_day_pct - 100 * mm.three_day).abs() < 0.0051)
    checks.append(f"history.csv: {len(mm)} rows; three-day % equal to events.csv three_day x 100 (2-decimal rounding) "
                  f"on {int(ok.sum())} of {len(mm)}; rows per stock equal to its events.csv results: "
                  f"{all((ev.symbol == s).sum() == (hb.symbol == s).sum() for s in per_stock)}")
    fo_ok = ((mm.fo_status == "yes") == (mm.in_fo_ev.astype(str) == "True")).all()
    pool = mm.assign(x=100 * mm.three_day)
    checks.append(f"F&O status: history.csv fo_status matches events.csv in_fo on every row: {bool(fo_ok)}; of "
                  f"{len(mm)} rows {int((mm.fo_status != 'yes').sum())} are from outside F&O "
                  f"({int((mm.fo_status == 'no (before F&O entry)').sum())} before F&O entry); pooled three-day "
                  f"average: all {pool.x.mean():+.2f}%, in F&O {pool.x[mm.fo_status == 'yes'].mean():+.2f}%, outside "
                  f"F&O {pool.x[mm.fo_status != 'yes'].mean():+.2f}%")

    # ---------------------------------------------------------------- texts
    asof = {"latest_close": latest, "latest_close_label": day_lbl(latest),
            "project_data_to": panel.project_last,
            "appended_bhavcopy_days": panel.appended,
            "next_session": next_session,
            "calendar_downloaded": dl.fetched("event_calendar.json"),
            "board_meetings_downloaded": dl.fetched(f"board_meetings_{start:%Y%m%d}_{end:%Y%m%d}.json"),
            "lookback_meetings_downloaded": dl.fetched(f"board_meetings_{lb_from:%Y%m%d}_{lb_to:%Y%m%d}.json"),
            "fo_list_downloaded": dl.fetched("fo_mktlots.csv"),
            "ban_list_downloaded": dl.fetched("fo_secban.csv"), "ban_list_trade_date": ban_td,
            "fo_bhavcopy_day": fo_bh_day,
            "run_date": today.isoformat(), "generated_ist": now.strftime("%Y-%m-%d %H:%M IST")}
    research = research_lines()
    ctx = dict(OUT=OUT, cal=cal, start=start, end=end, today=today, today_note=today_note, latest=latest,
               order=order, per_stock=per_stock, asof=asof, n_fo=len(fo), L4=L4, research=research, checks=checks,
               hol_warn=hol_warn, missing_days=missing_days, ca_list=ca_list, recent=recent,
               recent_passed=recent_passed, recent_missing=recent_missing, lb_from=lb_from, lb_to=lb_to,
               next_session=next_session, ban_td=ban_td, ban_syms=ban_syms, n_hist=n_hist,
               nifty_close=panel.N[i_latest], ca_future=ca_future)
    write_markdown(ctx)
    js = {"title": f"F&O results screener {start} to {end}", "data_as_of": asof,
          "window": {"start": start.isoformat(), "end": end.isoformat(), "days": a.days, "today": today.isoformat(),
                     "today_note": today_note, "lookback_from": lb_from.isoformat(), "lookback_to": lb_to.isoformat()},
          "fo_stocks": len(fo), "stocks_in_window": len(order),
          "conventions": CONVENTIONS, "risk": RISK, "calendar": calendar_rows, "summary": summary_rows,
          "recent_reporters": rc_rows,
          "recent_reporters_entry_passed": recent_passed, "recent_reporters_not_found": recent_missing,
          "ban_list": {"trade_date": ban_td, "symbols": sorted(ban_syms)},
          "history": {s: [{k: v for k, v in r.items() if not k.startswith("_")} for r in history_rows if r["symbol"] == s]
                      for s in per_stock},
          "research": [{"signal": x[0], "label": x[1], "finding": x[2], "source": x[3]} for x in research],
          "checks": checks, "warnings": hol_warn + [f"price data not available for {x}" for x in missing_days],
          "notes": NOTES}
    (OUT / "screener.json").write_text(json.dumps(js, indent=1, ensure_ascii=False, default=str))
    print("\n".join("check: " + c for c in checks))
    print(f"wrote {OUT}/calendar.csv, history.csv, summary.csv, recent.csv, screener.md, notes.md, screener.json, "
          f"stocks/*.md ({len(per_stock)})")


def _last_tuesday(e: str) -> str:
    x = date(d(e).year + (d(e).month == 12), d(e).month % 12 + 1, 1) - timedelta(days=1)
    while x.weekday() != 1:
        x -= timedelta(days=1)
    return x.isoformat()


CONVENTIONS = {
    "result_session": "the results date if it is a trading session, else the next session (for an upcoming result: "
                      "the board-meeting date)",
    "window": "cutoff = 2 sessions before the result session; Day-1, Result day, Day+1 = the sessions before, of and "
              "after the result session",
    "three_day": "Day-1 + Result day + Day+1 daily close-to-close returns (= cutoff close to Day+1 close), percent",
    "reaction_day": "Day+1 for results released after the close (from 15:30) on a trading day; the Result day for "
                    "results released before 09:15 or during market hours on a trading day, or on a non-trading day",
    "likely_reaction_day": "for an upcoming meeting: from the company's past results matched to its NSE board-meeting "
                           "dates (did it react on the meeting-date session or the next one; majority of the last 8, "
                           "mixed below 75%); else from its release times",
    "winner": "reaction-day return minus Nifty 50's return that day > +4%",
    "lag": "21-session return minus Nifty 50's 21-session return, at the close",
    "volume_ratio": "mean volume of the last 5 sessions / mean of the last 60 (split / bonus adjusted)",
    "rsi14": "Wilder RSI(14) on adjusted closes",
    "final_provisional": "final = measured at the cutoff close; provisional to <date> = measured at the latest close "
                         "while the cutoff is still ahead (the values keep moving until the cutoff close)",
    "growth": "Sales / PAT growth in percent; PAT = profit attributable to owners (consolidated where filed; banks "
              "standalone); Sales = revenue from operations (banks: interest earned); blank when the base quarter "
              "was zero or a loss",
}

RISK = [
    f"Costs: about {COST_T1:.2f}% a round trip for Trade 1 (cutoff close to Day+1 close) and about {COST_T2:.2f}% for "
    "Trade 2 entered at the next open.",
    "Trade 1 (lag 10% + volume): 85 trades, +2.13% before costs; single trades ranged from about -11% to +19%; without "
    "its best 5 trades +1.36%; some seasons have no trade. Realistic +1% to +1.5% a trade after costs.",
    "Trade 2 (winners with RSI > 50, next open, 0.40% cost): +2.04% over Nifty; it lost 3 seasons in a row in 2021-22, "
    "and 2023 gave 46% of its profit (without 2023 +1.54%). Realistic about +1% over Nifty.",
    "Survivorship: the stock list is today's F&O list, which flatters both trades (Trade 2 on stocks already in F&O in "
    "2021: +1.41%). The cut-offs were chosen after looking at the data.",
    "Position size: small. One trade can lose 10% or more; both trades are to be paper-traded first. The average F&O "
    "stock makes +0.04% in the three-day window, a loss after costs.",
]

NOTES = [
    "Descriptive history: a stock's past three-day results moves do not predict the direction of its next one.",
    "Reported numbers are known only on the results day; the three-day window starts before them (Day-1).",
    "Only the lag 10% + volume rule (before results) and the results-winners trade with RSI(14) > 50 (after results) "
    "held up in the project's tests, and both are to be paper-traded first.",
]


def research_lines() -> list[tuple[str, str, str, str]]:
    """(signal, label, tested finding, source doc) - figures from the project's docs."""
    return [
        ("Lag 10% + volume (before results)", "TRADE (paper-trade)",
         "21-session return minus Nifty's below -10% and 5/60 volume >= 1.0x at the cutoff close; buy at the cutoff "
         "close, sell at the Day+1 close: 85 trades, +2.13% (+1.96% after costs), 18 of 19 quarters with trades "
         "positive; 1.3x version 44 trades, +2.77%. Cut-offs chosen after looking; without the best 5 trades +1.36%. "
         "Realistic +1% to +1.5% a trade after costs.", "docs/SUMMARY.md, docs/LAG10_VOLUME.md"),
        ("Same lag on quiet volume (below 1.0x)", "NOT a trade",
         "109 trades, -0.37% over the three days.", "docs/LAG10_VOLUME.md"),
        ("Results winners (after results)", "TRADE (paper-trade), only with RSI(14) > 50",
         "Reaction-day return beats Nifty by more than 4%: buy at the next open, hold 20 sessions against Nifty. All "
         "winners +1.45% a trade over Nifty (392 trades, 15 of 22 quarters); with RSI(14) > 50 at the cutoff +2.42% "
         "(232 trades, 17 of 22), +2.04% at the next open with 0.40% cost. Realistic about +1% over Nifty. Winners "
         "with RSI 50 or below: +0.04%, and they lose money at the next-open entry: skip.",
         "docs/SUMMARY.md, docs/WINNERS_RSI50.md"),
        ("Hold results winners 60 sessions instead of 20", "WATCH",
         "+5.10% vs +1.85% on unseen quarters, but the same per day; not significant. About +2% per 60-session trade.",
         "docs/HIGHER_AVERAGE.md"),
        ("Pre-results IV run-up straddle", "MARGINAL",
         "Buy the ATM straddle 5 sessions before the last close before the numbers, sell at that close, only if the "
         "front expiry is within 14 sessions: +0.065R in 2023-25; +2.2% a trade out of sample (556 trades), two of "
         "five seasons slightly negative. Needs fills near mid.", "docs/SUMMARY.md, docs/REAL_DATA_RESULTS.md"),
        ("Last-4 three-day average in the top tenth", "WATCH",
         "Stocks that habitually rise into their results: 292 trades, +1.07% before costs (+0.90% after), found after "
         "the fact; five stocks give 60% of it. Realistic about +0.45% after costs.",
         "docs/PAST_PERFORMANCE.md, docs/QUARTER_CORRELATION.md"),
        ("Auto and auto-parts stocks (cutoff close to Day+1 close)", "WATCH",
         "+1.20% a result (264 results), above the quarter's average in 18 of 22 quarters; with NSE's auto sector "
         "+1.10%, resting on three stocks and on 2021-23 (adjusted p 0.06-0.23). Realistic well under +1%.",
         "docs/SECTOR_3DAY.md, docs/NIFTY_SECTOR_3DAY.md"),
        ("A stock's earlier three-day moves -> direction of its next one", "NOT PREDICTIVE",
         "Rank correlation with last quarter's move +0.005 (3,177 results); after an up quarter the next three days "
         "averaged +0.00%, after a down quarter +0.03% (docs/PREVIOUS_QUARTERS.md); share up 49% after an up quarter "
         "vs 48% after a down one (results/prev_quarter_patterns/table_lags.md, lag 1); no lag of 1-8 quarters and "
         "none of 84 pattern tests confirmed.",
         "docs/PREVIOUS_QUARTERS.md, results/prev_quarter_patterns/table_lags.md, docs/QUARTER_CORRELATION.md"),
        ("Size of a stock's earlier three-day moves -> size of its next one", "DESCRIPTIVE (options only)",
         "Persists a little (rank correlation about +0.05 with last quarter's absolute move), mostly because volatile "
         "stocks move more (60-day volatility alone +0.12). Says nothing about direction; no cash trade.",
         "results/prev_quarter_patterns/table_magnitude.md"),
        ("Last result a winner / a loser", "NOT PREDICTIVE",
         "Next three-day window -0.04% after a winner, +0.06% after a loser.", "docs/PAST_PERFORMANCE.md"),
        ("PAT up or down year on year", "NOT PREDICTIVE (known only after the numbers)",
         "No fundamental screen before results works (44 screens within about +-0.3%); after results, strong numbers "
         "bought +0.52% over 20 sessions vs +0.43% for all results, and shorting bad numbers lost money. The per-stock "
         "'PAT up / down YoY' columns here are descriptive, and say nothing about expectations.",
         "docs/FUNDAMENTAL_ANALYSIS.md"),
        ("Technical analysis, EMA / SMA at the cutoff", "NOT PREDICTIVE",
         "44 textbook signals and 59 EMA / SMA signals: none passes; the small negative EMA / SMA link is market "
         "timing and vanishes among results on the same day.", "docs/TECHNICAL_ANALYSIS.md, docs/EMA_SMA_3DAY.md"),
        ("Last season's best / worst sector", "NOT PREDICTIVE",
         "No memory between seasons; buying last quarter's best sector made -0.24% a result.",
         "docs/QUARTER_CORRELATION.md"),
        ("The average F&O stock in the three-day window", "BASELINE",
         "+0.04% a result (-0.05% vs Nifty), a loss after 0.17% round-trip costs; no short works.",
         "docs/SUMMARY.md, docs/NEGATIVE_AVERAGE.md"),
    ]


# ------------------------------------------------------------------------------------------------ markdown
def avg_cell(avg, med, up, n) -> str:
    """'avg / median / up (n)', hidden below MIN_N results"""
    if not n:
        return "- (0)"
    if n < MIN_N:
        return f"- (n<{MIN_N})"
    return f"{spc(avg)} / {spc(med)} / {up:.0f}% ({n})"


def one_avg(avg, n) -> str:
    if not n:
        return "- (0)"
    return f"- (n<{MIN_N})" if n < MIN_N else f"{spc(avg)} ({n})"


def ban_cell(ctx, syms: list[str], day: str | None) -> str:
    td, banned = ctx["ban_td"], ctx["ban_syms"]
    if not td:
        return "list not available: check"
    hit = [s for s in syms if s in banned]
    if day == td:
        return ("BANNED: " + ", ".join(hit)) if hit else "no"
    return (f"on the {short_lbl(td)} list: {', '.join(hit)}; re-check" if hit else
            f"not on the {short_lbl(td)} list; re-check on the day")


def contract_cell(k: dict, hedge: dict | None = None) -> str:
    if not k or k.get("txt", "-") == "-":
        return "-"
    out = k["txt"] + (f"; lot {k['lot']:,}" if k.get("lot") else "") + \
        (f", {rupees(k['notional'])}" if k.get("notional") else "")
    if hedge and hedge.get("txt", "-") != "-":
        out += f"; Nifty hedge: {hedge['txt']}" + (f", lot {hedge['lot']} ({rupees(hedge['notional'])})"
                                                   if hedge.get("lot") and hedge.get("notional") else "")
    return out


def trig_cell(t: dict | None, short: bool = False) -> str:
    if not t:
        return "-"
    v1 = "any volume" if t["vol_need_1"] <= 0 else f">= {qty(t['vol_need_1'])} ({t['mult_1']:.1f}x recent)"
    v13 = "any" if t["vol_need_13"] <= 0 else f">= {qty(t['vol_need_13'])}"
    per = "on the cutoff day" if t["k"] == 1 else f"a day over the {t['k']} sessions to the cutoff"
    head = (f"close <= {price(t['close_max'])} ({spc(t['headroom_pct'], 1)} vs {price(t['latest_close'])}; "
            f"+{t['per_1pct_nifty']:.2f} per 1% Nifty rise)")
    if short:
        return f"{head}; volume {v1} {per} (1.3x: {v13})"
    return f"{head}; volume {v1} {per}, 1.3x: {v13}"


def within_reach(t: dict | None) -> bool:
    """A cutoff still ahead where both conditions are plausible: the close needed is at most 6% below the latest
    close (or above it) and the volume needed is at most 3x the recent 5-session average."""
    if not t:
        return False
    return t["headroom_pct"] >= -6.0 and (t["vol_need_1"] <= 0 or (isnum(t["mult_1"]) and t["mult_1"] <= 3.0))


def write_markdown(ctx: dict):
    OUT, cal, start, end, today = ctx["OUT"], ctx["cal"], ctx["start"], ctx["end"], ctx["today"]
    latest, order, per_stock, asof = ctx["latest"], ctx["order"], ctx["per_stock"], ctx["asof"]
    nxt_s = ctx["next_session"]
    syms = [m["symbol"] for m in order if m["symbol"] in per_stock]

    head = [f"# F&O results screener: {day_lbl(start)} to {day_lbl(end)}", ""]
    head.append(f"Data as of the **{day_lbl(latest)} close** (NSE cash bhavcopy); results calendar downloaded "
                f"{asof['calendar_downloaded']}; run date {day_lbl(today)}; next session **{day_lbl(nxt_s)}**."
                + (f" {ctx['today_note']}." if ctx["today_note"] else ""))
    head.append("")
    head.append(f"{len(per_stock)} of today's {ctx['n_fo']} F&O stocks have a results board meeting from "
                f"{short_lbl(start)} to {short_lbl(end)}, plus results already announced from {short_lbl(ctx['lb_from'])}"
                f" to {short_lbl(ctx['lb_to'])} whose winners-trade entry is still ahead. Only two trades held up, both "
                "to paper-trade first: **Trade 1** (lag 10% + volume, buy at the cutoff close, sell at the Day+1 close) "
                "and **Trade 2** (results winners with RSI(14) > 50 at the cutoff, buy at the next open, hold 20 "
                "sessions against Nifty). Read [notes.md](notes.md) before using any of it.")
    head.append("")
    risk = ["> **Risk box** (docs/SUMMARY.md)", ">"] + [f"> - {x}" for x in RISK] + [
        f"> - Values marked *provisional to <date>* are measured at the {short_lbl(latest)} close; the lag, volume "
        "ratio and RSI keep moving until that cutoff close (each session the 21-session base day drops out). A "
        "signal is final only at the cutoff close, which is also the moment to buy: use the trigger levels at about "
        "15:20 on the cutoff day, not an evening re-run.",
        "> - Check the F&O ban list and the company's results date on every trade date.", ""]

    # ---------------- at a glance (every value tagged final / provisional)
    ps = per_stock
    fired = [s for s in syms if ps[s]["rule_txt"].startswith("fires")]
    reach = [s for s in syms if within_reach(ps[s]["trig"])]
    rsi50 = [s for s in syms if isnum(ps[s]["rsi"]) and ps[s]["rsi"] > 50]
    buys = [r for r in ctx["recent"] if r["verdict"].startswith("buy")]
    pend = [r for r in ctx["recent"] if r["verdict"].startswith("pending")]

    def tag(s):
        return "final" if ps[s]["in_data"] else ps[s]["sig_status"]

    glance = ["## At a glance", "",
              "- Trade 2 orders from results already out: " + (", ".join(
                  f"**{r['symbol']}** {r['verdict']} (reaction {short_lbl(r['reaction_day'])} {spc(r['rxn'])} vs "
                  f"Nifty, RSI {r['rsi14_cutoff']:.1f} {r['rsi_status']})" for r in buys) or "none") + "."
              + (" Reaction day still ahead: " + ", ".join(
                  f"{r['symbol']} ({short_lbl(r['reaction_day'])}, RSI {r['rsi14_cutoff']:.1f} {r['rsi_status']}"
                  f"{'' if r['rsi14_cutoff'] > 50 else ': skip even if a winner'})" for r in pend) + "." if pend else ""),
              "- Trade 1 fires on the latest close: " + (", ".join(
                  f"{s} (lag {spc(ps[s]['lag'])}, volume {ps[s]['vr']:.2f}x, {tag(s)})" for s in fired) or "none")
              + ". Within reach by the cutoff close (trigger levels below): " + (", ".join(
                  f"{s} ({short_lbl(ps[s]['cut'])})" for s in reach) or "none") + ".",
              f"- RSI(14) > 50 (Trade 2 is a conditional buy only for these, if the reaction day beats Nifty by more "
              f"than 4%): {len(rsi50)} of {len(syms)}: " + (", ".join(
                  f"{s} {ps[s]['rsi']:.1f} ({tag(s)})" for s in rsi50) or "none") + ". Just below 50: " + (", ".join(
                  f"{s} {ps[s]['rsi']:.1f} ({tag(s)})" for s in syms
                  if isnum(ps[s]["rsi"]) and 47.5 <= ps[s]["rsi"] <= 50) or "none") + ".",
              "- Single-day events inside the signal windows (check the cause): " + (", ".join(
                  f"{s} ({len(ps[s]['events'])})" for s in syms if ps[s]["events"]) or "none") + ".",
              f"- F&O ban list for {short_lbl(ctx['ban_td']) if ctx['ban_td'] else '-'}: "
              + (", ".join(sorted(ctx["ban_syms"])) or "none")
              + f"; of the stocks here: {', '.join(s for s in syms if s in ctx['ban_syms']) or 'none'}.",
              f"- Watch items only: last-4 top tenth {', '.join(s for s in syms if ps[s]['l4_top']) or 'none'}; auto / "
              f"auto parts {', '.join(s for s in syms if ps[s]['auto']) or 'none'}.", ""]

    # ---------------- (a) actions by date
    acts = []

    def act(day, order_k, stock, what, status, trig="-", contract="-", ban="-"):
        if day:
            acts.append({"day": day, "k": order_k, "stock": stock, "what": what, "status": status, "trig": trig,
                         "contract": contract, "ban": ban})

    for r in ctx["recent"]:
        rel = f"results {datetime.strptime(r['release'], '%Y-%m-%d %H:%M:%S'):%a %d-%b %H:%M} ({r['timing'].lower()})"
        if isnum(r["rxn"]):
            what = (f"Trade 2, results already out: {rel}; reaction {short_lbl(r['reaction_day'])} {spc(r['rxn'])} vs "
                    f"Nifty (stock {spc(r['reaction_pct'])}, Nifty {spc(r['nifty_pct'])})")
            day = r["entry_open"]
        else:
            what = (f"Trade 2, results already out: {rel}; reaction day {short_lbl(r['reaction_day'])}: a winner if "
                    f"its close beats Nifty's move by more than 4%")
            day = r["reaction_day"]
        st = (f"**{r['verdict']}**; RSI {r['rsi14_cutoff']:.1f} at the {short_lbl(r['cutoff'])} cutoff "
              f"({r['rsi_status']})" if isnum(r["rsi14_cutoff"]) else r["verdict"])
        if r["verdict"].startswith("buy"):
            st += f"; exit at the {short_lbl(r['exit_close'])} close"
        k_ = 0 if r["verdict"].startswith("buy") else (1 if r["verdict"].startswith("pending") else 2)
        act(day, k_, r["symbol"], what, st, "-",
            contract_cell(r["contract"], r["hedge"]) if not r["verdict"].startswith(("skip", "not")) else "-",
            ban_cell(ctx, [r["symbol"]], r["entry_open"] if isnum(r["rxn"]) else r["reaction_day"]))
    # Trade 1 checks (cutoff still ahead), one row each within reach, the rest grouped
    by_cut: dict[str, list[str]] = {}
    for s in syms:
        p = ps[s]
        c = p["cal"]
        if c["trade1_check_cutoff"] in ("missed",):
            continue
        cut = p["cut"]
        fires = p["rule_txt"].startswith("fires")
        if within_reach(p["trig"]) or fires:
            act(cut, 3, s, f"Trade 1 check (cutoff close; results {short_lbl(c['meeting_date'])}, sell at the "
                           f"{short_lbl(c['day_p1'])} close)",
                f"lag {spc(p['lag'])}, volume {p['vr']:.2f}x ({p['sig_status']}): {p['rule_txt']}",
                (trig_cell(p["trig"], short=True) + "; check at about 15:20") if p["trig"] else "-",
                contract_cell(p["k1"]), ban_cell(ctx, [s], cut))
        else:
            by_cut.setdefault(cut, []).append(s)
    for cut, ss in by_cut.items():
        act(cut, 4, ", ".join(ss), "Trade 1 check (cutoff close): out of reach on the latest close",
            "needs a fall of more than 6% or volume above 3x the recent average; lag / volume per stock in Signals "
            f"({ps[ss[0]]['sig_status']})", "-", "-", ban_cell(ctx, ss, cut))
    # Trade 2 reaction-day checks for the window stocks
    skip_by_day: dict[str, list[str]] = {}
    for s in syms:
        p = ps[s]
        c = p["cal"]
        rd = c["expected_reaction_day"]
        alt = ""
        if p["mixed"]:
            alt = f"; mixed: could be {short_lbl(c['day_p1'] if p['likely'] == 'Result day' else c['result_day'])}"
        if isnum(p["rsi"]) and p["rsi"] > 50:
            act(rd, 5, s, f"Trade 2 reaction day (results {short_lbl(c['meeting_date'])}; {p['likely']}{alt}): a "
                          f"winner if its close beats Nifty's move by more than 4%",
                f"conditional buy at the {short_lbl(p['t2_buy'])} open; RSI {p['rsi']:.1f} ({p['sig_status']}); "
                f"exit at the {short_lbl(p['t2_exit'])} close",
                "-", contract_cell(p["k2"], p["kn"]), ban_cell(ctx, [s], p["t2_buy"]))
        else:
            skip_by_day.setdefault(rd, []).append(
                f"{s} {p['rsi']:.1f}" + ("" if p["in_data"] else f" (prov. to {short_lbl(p['cut'])})")
                if isnum(p["rsi"]) else f"{s} n/a")
    for rd, ss in skip_by_day.items():
        act(rd, 6, ", ".join(x.split(" ")[0] for x in ss), "Trade 2 reaction day",
            "skip even if a winner (RSI <= 50): " + ", ".join(ss), "-", "-", "-")
    for s in syms:
        p = ps[s]
        if p["ru_status"].startswith("buy") or p["ru_status"] == "today":
            act(p["ru_entry"], 7, s, "Run-up straddle entry (marginal; price it live)",
                f"{short_lbl(p['fexp'])} expiry, sell at the {short_lbl(p['pre'])} close", "-", "-",
                ban_cell(ctx, [s], p["ru_entry"]))
    meet_by_day: dict[str, list[str]] = {}
    for s in syms:
        c = ps[s]["cal"]
        meet_by_day.setdefault(c["meeting_date"], []).append(
            f"{s} ({ps[s]['react_short'].lower()} {short_lbl(c['expected_reaction_day'])})")
    for md, ss in meet_by_day.items():
        act(md, 8, f"{len(ss)} stocks", "Results board meetings (likely reaction day)", ", ".join(ss))

    act_lines = ["## Actions by date", "",
                 "Dates from the next session on. Trade 1 is bought at the cutoff close and sold at the Day+1 close; "
                 "Trade 2 starts at the open after the reaction day. Reaction-day rule: results released after 15:30 "
                 "react the next session, otherwise the same session (the session after, on a non-trading day).", "",
                 "| Date | Stock | What to check | Status | Trigger levels | Contract | Ban |",
                 "|---|---|---|---|---|---|---|"]
    for x in sorted(acts, key=lambda z: (z["day"], z["k"], z["stock"])):
        if nxt_s and x["day"] < nxt_s:
            continue
        act_lines.append(f"| {short_lbl(x['day'])} | {x['stock']} | {x['what']} | {x['status']} | {x['trig']} | "
                         f"{x['contract']} | {x['ban']} |")
    past_buys = [x for x in acts if nxt_s and x["day"] < nxt_s and x["k"] in (0, 3)]
    if past_buys:
        act_lines += ["", "Already past: " + "; ".join(f"{x['stock']} {short_lbl(x['day'])}" for x in past_buys) + "."]
    missed_fired = [s for s in syms if ps[s]["cal"]["trade1_check_cutoff"] == "missed" and
                    ps[s]["rule_txt"].startswith("fires")]
    n_missed = sum(ps[s]["cal"]["trade1_check_cutoff"] == "missed" for s in syms)
    act_lines += ["", f"Trade 1 checks already missed (cutoff close before {short_lbl(today)}): {n_missed} of "
                  f"{len(syms)}" + (f"; fired at the cutoff: {', '.join(missed_fired)}" if missed_fired else
                                    "; none of them fired") + ".", ""]

    # ---------------- recent reporters
    rr_lines = [f"## Results already out ({short_lbl(ctx['lb_from'])} to {short_lbl(ctx['lb_to'])}): Trade 2 entries "
                f"still ahead", "",
                "Release time from the NSE announcement that carries the results (the earliest 'Outcome of Board "
                "Meeting' or results filing from the meeting date on). Reaction day: after 15:30 on a trading day -> "
                "the next session; before 09:15 or during market hours -> that session; non-trading day -> the next "
                "session. RSI(14) at the cutoff (2 sessions before the result session), the screener's own code.", ""]
    if ctx["recent"]:
        rr_lines += ["| Stock | Meeting | Released | Timing | Reaction day | Stock / Nifty | Vs Nifty | RSI(14) at "
                     "cutoff | Verdict | Entry / exit | Contract | Ban |",
                     "|---|---|---|---|---|---:|---:|---|---|---|---|---|"]
        for r in ctx["recent"]:
            rr_lines.append(
                f"| {r['symbol']} | {short_lbl(r['meeting_date'])} | "
                f"{datetime.strptime(r['release'], '%Y-%m-%d %H:%M:%S'):%a %d-%b %H:%M:%S} ({r['release_desc']}) | "
                f"{r['timing']} | {short_lbl(r['reaction_day'])} | "
                + (f"{spc(r['reaction_pct'])} / {spc(r['nifty_pct'])} | **{spc(r['rxn'])}** | " if isnum(r["rxn"])
                   else "pending | pending | ")
                + (f"{r['rsi14_cutoff']:.1f} ({short_lbl(r['cutoff'])}, {r['rsi_status']}) | " if isnum(
                    r["rsi14_cutoff"]) else "- | ")
                + f"{r['verdict']} | {short_lbl(r['entry_open'])} open / {short_lbl(r['exit_close'])} close | "
                f"{contract_cell(r['contract'], r['hedge'])} | "
                f"{ban_cell(ctx, [r['symbol']], r['entry_open'])} |")
    else:
        rr_lines.append("None.")
    if ctx["recent_passed"]:
        rr_lines += ["", f"Entry already passed ({len(ctx['recent_passed'])}): " + "; ".join(ctx["recent_passed"]) + "."]
    if ctx["recent_missing"]:
        rr_lines += ["", "Not classified: " + "; ".join(ctx["recent_missing"]) + "."]
    rr_lines.append("")

    # ---------------- trigger levels
    tl = ["## Trade 1 trigger levels (check at about 15:20 on the cutoff day)", "",
          f"For cutoffs still ahead, from the {short_lbl(latest)} close: the highest cutoff-day close that keeps the "
          "21-session lag below -10% if Nifty ends the cutoff day where it closed on the latest close (add the 'per 1%' "
          "amount for each 1% Nifty rise by then, subtract it for a fall), and the volume needed for the 5/60 ratio "
          "to reach 1.0x (and 1.3x). With more than one session to go the volume is a daily average over the "
          "sessions to the cutoff; re-run the evening before the cutoff for the exact cutoff-day figure. Both must "
          "hold at the close; at 15:20 compare the price with the level and the day's volume so far with the need. "
          "Shown: candidates within reach (needed close at most 6% below the latest close and volume at most 3x the "
          "recent average) and any that fire now; all are in calendar.csv.", "",
          "| Cutoff | Stock | Sessions to go | Lag now | Close now | Highest close (Nifty flat) | Change needed | Per 1% "
          "Nifty | Volume 1.0x | Volume 1.3x | 5-day avg volume | Base day | Contract (lot, notional) |",
          "|---|---|---:|---:|---:|---:|---:|---:|---|---|---:|---|---|"]
    shown = [s for s in syms if ps[s]["trig"] and (within_reach(ps[s]["trig"]) or ps[s]["rule_txt"].startswith("fires"))]
    for s in sorted(shown, key=lambda z: (ps[z]["cut"], z)):
        t = ps[s]["trig"]
        tl.append(
            f"| {short_lbl(ps[s]['cut'])} | {s} | {t['k']} | {spc(t['lag_now'])} | {price(t['latest_close'])} | "
            f"**{price(t['close_max'])}** | {spc(t['headroom_pct'], 1)} | {t['per_1pct_nifty']:.2f} | "
            + ("any" if t["vol_need_1"] <= 0 else f"**{qty(t['vol_need_1'])}** ({t['mult_1']:.1f}x)") + " | "
            + ("any" if t["vol_need_13"] <= 0 else f"{qty(t['vol_need_13'])} ({t['mult_13']:.1f}x)") + " | "
            f"{qty(t['avg5'])} | {short_lbl(t['base_day'])} | {contract_cell(ps[s]['k1'])} |")
    if not shown:
        tl.append("| - | none within reach | | | | | | | | | | | |")
    tl += ["", "Out of reach on the latest close: " + (", ".join(
        f"{s} ({spc(ps[s]['trig']['headroom_pct'], 1)}"
        + (f", volume {ps[s]['trig']['mult_1']:.1f}x" if ps[s]["trig"]["vol_need_1"] > 0 else "") + ")"
        for s in syms if ps[s]["trig"] and s not in shown) or "none") + ".", ""]

    # ---------------- (b) signals
    sig = ["## Signals", "",
           "Measured at the cutoff close when it is in the data (final), else at the latest close (provisional to the "
           "cutoff date). Trade 1 = lag below -10% and 5/60 volume >= 1.0x (1.3x stricter). Trade 2 = only with RSI(14) "
           "> 50 at the cutoff, and only if the reaction day beats Nifty by more than 4%.", "",
           "| Results | Stock | Trade 1 check (cutoff close) | Values | Lag vs Nifty | Vol 5/60 | Lag 10% + vol | "
           "RSI(14) | Trade 2 | Likely reaction day | Single-day events in the windows | Ban |",
           "|---|---|---|---|---:|---:|---|---:|---|---|---|---|"]
    for s in syms:
        p = ps[s]
        c = p["cal"]
        win = " / ".join(x[8:10].lstrip("0") + "-" + d(x).strftime("%b") for x in (c["cutoff"], c["day_m1"],
                                                                                 c["result_day"], c["day_p1"]))
        chk = ("missed (" + short_lbl(c["cutoff"]) + ")" if c["trade1_check_cutoff"] == "missed" else
               "today" if c["trade1_check_cutoff"] == "today" else short_lbl(c["cutoff"]) + " close")
        vals = f"final ({short_lbl(p['cut'])})" if p["in_data"] else f"provisional to {short_lbl(p['cut'])}"
        rsi_t = f"{p['rsi']:.1f}" if isnum(p["rsi"]) else "-"
        evs = "; ".join(event_txt(e) for e in p["events"]) or "-"
        sig.append(
            f"| {short_lbl(c['meeting_date'])} | [{s}](stocks/{safe_name(s)}.md) | {chk} (window {win}"
            f"{', holiday inside' if c['holiday_in_window'] else ''}) | {vals} | {spc(p['lag'])} | "
            f"{(format(p['vr'], '.2f') + 'x') if isnum(p['vr']) else '-'} | {p['rule_txt']} | {rsi_t} | "
            f"{p['t2_short'].split(', RSI provisional')[0]} | {short_lbl(c['expected_reaction_day'])} "
            f"({p['react_short']}; {p['react_src']}) | {evs} | {ban_cell(ctx, [s], ctx['next_session'])} |")
    sig += ["", "Single-day events: a daily move beyond +-8% inside the 21-session lag window, or volume above 10x the "
            "60-session median inside the 60-session volume base (windows ending at the cutoff). Such a day can make "
            "the lag or the volume ratio; check its cause (block deal, news, index change, corporate action) before "
            "acting on the signal.", ""]

    # ---------------- (c) history
    hist = ["## History (a record, not a forecast)", "",
            "How each stock moved around its past results. A stock's earlier three-day moves do not predict the "
            "direction of its next one (rank correlation +0.005 with the previous quarter). In-F&O results first: the "
            "trades only use stocks in F&O at the time, and results from before F&O entry flatter some averages. "
            f"Averages from fewer than {MIN_N} results are hidden.", "",
            "| Stock | Usual timing | In F&O: avg / median / up (n) | All results: avg / median / up (n) | Before F&O | "
            "Avg size | Best | Worst | Last (not predictive) | Last-4 avg (rank; watch item) | PAT up YoY: avg (n) | "
            "PAT down YoY: avg (n) | Winners (not predictive) | Auto |",
            "|---|---|---|---|---:|---:|---|---|---:|---|---|---|---:|---|"]
    for s in syms:
        p = ps[s]
        r, su = p["sum"], p["summ"]
        n3 = su.get("n_3d", 0)
        best = f"{spc(su['best_3d'])} {su['best_period']}" if isnum(su["best_3d"]) else "-"
        worst = f"{spc(su['worst_3d'])} {su['worst_period']}" if isnum(su["worst_3d"]) else "-"
        l4 = (f"{spc(p['l4'])} ({r['last4_rank']}{', top tenth' if p['l4_top'] else ''})" if isnum(p["l4"]) else "-")
        wins = f"{su['winners_n']} of {su['xn_n']}" if su["xn_n"] else "-"
        size = (r["avg_abs_3d_pct"] + "%") if r["avg_abs_3d_pct"] and n3 >= MIN_N else (f"- (n<{MIN_N})" if n3 else "-")
        hist.append(
            f"| {s} | {r['usual_timing'].replace(' of ', '/')} | "
            f"{avg_cell(su['fo_avg'], su['fo_median'], su['fo_up'], su['fo_n'])} | "
            f"{avg_cell(su['avg_3d'], su['median_3d'], su['share_up'], n3)} | {su['n_before_fo']} | {size} | {best} | "
            f"{worst} | {spc(su['last_3d'])} | {l4} | {one_avg(su['good_avg'], su['good_n'])} | "
            f"{one_avg(su['bad_avg'], su['bad_n'])} | {wins} | {'yes' if p['auto'] else 'no'} |")
    hist += ["", "Columns: **In F&O** = results while the stock was in F&O (the trades' universe); **All results** = "
             "every result in the project data (Jan-Mar 2021 to Apr-Jun 2026 results); **Before F&O** = results from "
             "before the stock entered F&O (marked in the stock pages). **Avg size** = average absolute three-day "
             "move. **Last** and **Winners** (past reaction days beating Nifty by more than 4%) do not predict the "
             "next window (after a winner the next window made -0.04%, docs/PAST_PERFORMANCE.md). **Last-4 avg** = "
             "average of the last 4 three-day sums, ranked among current F&O stocks (top tenth = a watch item). "
             "**PAT up / down YoY** = profit attributable to owners up or not on a year earlier; it is not 'vs "
             "expectations', it comes out inside the window, and it means little for insurers and similar books.", ""]

    links = "Per stock: " + ", ".join(f"[{s}](stocks/{safe_name(s)}.md)" for s in syms) + "\n"
    (OUT / "screener.md").write_text("\n".join(head + risk + glance + act_lines + rr_lines + tl + sig + hist) + "\n"
                                     + links)

    # ---------------- per-stock pages
    for s in syms:
        p = ps[s]
        c, r, su, H = p["cal"], p["sum"], p["summ"], p["H"]
        L = [f"# {s}: {c['company']}", "",
             f"**Results board meeting {day_lbl(c['meeting_date'])}** ({c['purpose']}; source: NSE {c['source']}). "
             f"Sector: {c['sector']}.{' Auto / auto-parts watch item.' if p['auto'] else ''}", "",
             f"- Timing of its past results: {c['timing_history']}.",
             f"- Likely reaction day: **{short_lbl(c['expected_reaction_day'])}** ({p['react_short']}), from its "
             f"{p['react_src']}: {p['react_basis']}."
             + (f" (Release-time rule alone: {short_lbl(c['reaction_day_by_timing_rule'])}.)"
                if c["reaction_day_by_timing_rule"] and c["reaction_day_by_timing_rule"] != c["expected_reaction_day"]
                else ""),
             f"- Three-day window (project convention, results on the meeting date): cutoff {short_lbl(c['cutoff'])} "
             f"close, Day-1 {short_lbl(c['day_m1'])}, Result day {short_lbl(c['result_day'])}, Day+1 "
             f"{short_lbl(c['day_p1'])}" + (f"; holiday inside: {c['holiday_in_window']}" if c["holiday_in_window"]
                                            else "") + ".",
             f"- Trade 1 check (cutoff close): {p['status_txt']}.", ""]
        if p["mt"] and p["mt"]["next_after_midnight"]:
            L.insert(-1, f"- {p['mt']['next_after_midnight']} of its past releases came after midnight following the "
                         f"meeting; under the project convention such a release makes the next day the result session "
                         f"(the window would start one session later).")
        trig = p["trig"]
        L += ["## Signals", "",
              f"Measured {r['signal_basis']}.", "",
              f"- Trade 1 (lag 10% + volume, paper-trade): 21-session return "
              f"{(r['stock_21d_pct'] + '%') if r['stock_21d_pct'] else '-'} vs Nifty 50 "
              f"{(r['nifty_21d_pct'] + '%') if r['nifty_21d_pct'] else '-'}: lag {spc(p['lag'])}; "
              f"volume 5/60 {r['vol_ratio_5_60'] or '-'}x ({p['sig_status']}) -> **{p['rule_txt']}**."]
        if trig:
            L.append(f"- Trade 1 trigger levels for the {short_lbl(p['cut'])} cutoff close ({trig['k']} session(s) "
                     f"after the {short_lbl(latest)} close): {trig_cell(trig)}. Check at about 15:20 on the cutoff "
                     f"day.")
        L += [f"- Trade 2 (results winners, paper-trade): RSI(14) {r['rsi14'] or '-'} ({p['sig_status']}): "
              f"**{p['t2_txt']}**.",
              f"- Contracts: Trade 1 {contract_cell(p['k1'])}; Trade 2 {contract_cell(p['k2'], p['kn'])}.",
              f"- F&O ban: {ban_cell(ctx, [s], ctx['next_session'])}.",
              "- Single-day events in the signal windows: " + ("; ".join(event_txt(e) for e in p["events"]) +
                                                              ". Check the cause before acting." if p["events"] else
                                                              "none."),
              f"- Last-4 three-day average: {spc(p['l4'])}" + (f" (rank {r['last4_rank']}; top tenth: "
                                                                f"{r['last4_top_tenth']})" if isnum(p['l4']) else "")
              + ". Watch item only.",
              f"- Run-up straddle (marginal): entry {short_lbl(p['ru_entry'])}, exit {short_lbl(p['pre'])} close, "
              f"front expiry {short_lbl(p['fexp']) or '-'}: {p['ru_status']}.",
              f"- Latest close {short_lbl(asof['latest_close'])}: lag "
              f"{(r['lag_latest_pct'] + '%') if r['lag_latest_pct'] else '-'}, "
              f"volume 5/60 {r['vol_ratio_latest'] or '-'}x, RSI(14) {r['rsi14_latest'] or '-'}.", ""]
        if c["notes"]:
            L += [f"Data notes: {c['notes']}.", ""]
        L += ["## Summary of its past three-day results moves (a record, not a forecast)", ""]
        if su["n_past"]:
            L += [f"- {su['n_past']} results ({su['first_period']} to {su['last_period']}), {su['n_past_in_fo']} of them "
                  f"while in F&O, {su['n_before_fo']} from before F&O entry.",
                  f"- **In F&O** (the trades' universe): average / median / up "
                  f"{avg_cell(su['fo_avg'], su['fo_median'], su['fo_up'], su['fo_n'])}.",
                  f"- All results: average / median / up {avg_cell(su['avg_3d'], su['median_3d'], su['share_up'], su['n_3d'])}"
                  + (f"; average size (absolute) {su['avg_abs_3d']:.2f}%; average vs Nifty {spc(su['avg_3d_vs_nifty'])}"
                     if su["n_3d"] >= MIN_N else "") + ".",
                  f"- Best {spc(su['best_3d'])} ({su['best_period']}), worst {spc(su['worst_3d'])} ({su['worst_period']}),"
                  f" last {spc(su['last_3d'])} ({su['last_period']}; not predictive).",
                  f"- PAT up YoY: {one_avg(su['good_avg'], su['good_n'])}"
                  + (f", up {su['good_up']:.0f}%" if su["good_n"] >= MIN_N else "")
                  + f". PAT down YoY: {one_avg(su['bad_avg'], su['bad_n'])}"
                  + (f", up {su['bad_up']:.0f}%" if su["bad_n"] >= MIN_N else "")
                  + f". No PAT YoY: {su['unclassified_n']}. Descriptive: the numbers come out inside the window, and "
                    "this is not 'vs expectations'.",
                  f"- Reaction day vs Nifty: average {spc(su['avg_xn']) if su['xn_n'] >= MIN_N else '- (n<5)'}; "
                  f"results winners (> +4%) {su['winners_n']} of {su['xn_n']}, losers (< -4%) {su['losers_n']} "
                  f"(not predictive).",
                  "- Its earlier three-day moves do not predict the direction of the next one (project test: rank "
                  "correlation +0.005 with the previous quarter); bigger past moves go with somewhat bigger future "
                  "moves, mostly because the stock is volatile.", ""]
            L += ["## Past results, quarter by quarter (newest first)", "",
                  "Growth in percent (blank: no filing, or a zero / loss base a year or a quarter earlier). Moves in "
                  "percent; reaction = Result day for results before 15:30 or on a non-trading day, Day+1 for results "
                  "after the close. *F&O: no (before F&O entry)* rows are outside the trades' universe. Meeting = the "
                  "NSE results board-meeting date matched to the release; Reacted = the session it reacted on, "
                  "relative to the meeting date.", "",
                  "| Period | Quarter | Meeting | Results | Time | Timing | Reacted | F&O | Sales YoY | PAT YoY | "
                  "Sales QoQ | PAT QoQ | Day-1 | Result day | Day+1 | 3-day | 3-day vs Nifty | Reaction vs Nifty | "
                  "Winner |",
                  "|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
            for h in reversed(H.to_dict("records")):
                fo_c = h["fo_status"] if h["fo_status"] == "yes" else f"*{h['fo_status']}*"
                L.append(f"| {h['period']} | {h['quarter']} | {h['meeting_date'] or '-'} | {h['results_date']} | "
                         f"{h['results_time']} | {h['timing']} | {h['reaction_vs_meeting'] or '-'} | {fo_c} | "
                         f"{h['sales_yoy_pct'] or '-'} | {h['pat_yoy_pct'] or '-'} | "
                         f"{h['sales_qoq_pct'] or '-'} | {h['pat_qoq_pct'] or '-'} | {h['day_m1_pct'] or '-'} | "
                         f"{h['result_day_pct'] or '-'} | {h['day_p1_pct'] or '-'} | **{h['three_day_pct'] or '-'}** | "
                         f"{h['three_day_vs_nifty_pct'] or '-'} | {h['reaction_vs_nifty_pct'] or '-'} | "
                         f"{h['winner'] or '-'} |")
        else:
            L.append("No past results in the project data.")
        L += ["", "[Back to the screener](../screener.md)", ""]
        (OUT / "stocks" / f"{safe_name(s)}.md").write_text("\n".join(L))

    # ---------------- notes
    N = ["# Notes: F&O results screener", "",
         f"Meetings {day_lbl(start)} to {day_lbl(end)}; recent reporters {day_lbl(ctx['lb_from'])} to "
         f"{day_lbl(ctx['lb_to'])}; run date {day_lbl(today)}" + (f" ({ctx['today_note']})" if ctx["today_note"] else "")
         + f"; next session {day_lbl(nxt_s)}.", "",
         "## Data and as-of times", "",
         f"- Prices: the project's data pack (`LAB_ROOT/sector_lab/data`: returns.csv, index_close.csv, sessions.csv; "
         f"`LAB_ROOT/ta/build/adjusted_ohlcv.csv.gz` for adjusted closes and volumes) to {day_lbl(asof['project_data_to'])}, "
         f"then NSE cash bhavcopies (series EQ close and total traded quantity) and NSE index closes (Nifty 50) for "
         f"{', '.join(short_lbl(x) for x in asof['appended_bhavcopy_days']) or 'no further days'}. "
         f"**Latest close: {day_lbl(latest)}.**",
         f"- Results meetings: NSE event calendar (downloaded {asof['calendar_downloaded']}) and NSE board-meeting list "
         f"for the window (downloaded {asof['board_meetings_downloaded']}); only meetings whose purpose includes "
         "financial results. Dates can change: check the company's filing. Both lists come from the same company "
         "notices, so their agreement is not an independent confirmation.",
         f"- Recent reporters: NSE board-meeting list for {short_lbl(ctx['lb_from'])} to {short_lbl(ctx['lb_to'])} "
         f"(downloaded {asof['lookback_meetings_downloaded']}) and each company's NSE corporate announcements; the "
         "release time is the dissemination time of the earliest announcement from the meeting date on that carries "
         "the results ('Outcome of Board Meeting' or a results filing).",
         f"- Likely reaction day: each company's past results board meetings (NSE corporate-board-meetings for the "
         f"symbol; available for {ctx['n_hist']} of {len(syms)} stocks) matched to its past release dates and times in "
         "events.csv.",
         f"- F&O list: today's NSE fo_mktlots.csv (downloaded {asof['fo_list_downloaded']}), {ctx['n_fo']} stocks. "
         f"Futures expiries and lot sizes: NSE F&O bhavcopy of {day_lbl(asof['fo_bhavcopy_day']) or 'n/a'}. F&O ban "
         f"list: fo_secban.csv (downloaded {asof['ban_list_downloaded']}) for trade date "
         f"{day_lbl(asof['ban_list_trade_date']) or 'n/a'}; re-check it on every trade date (a stock in the ban "
         "period takes no fresh futures positions).",
         "- Trading holidays: NSE holiday master (capital market). Corporate actions from the project data to about "
         "the last winners-trade exit: NSE corporate actions list (splits / bonuses adjust earlier closes and "
         "volumes; demergers leave that day's return blank; moves beyond +-35% are flagged).",
         "- Past results: `LAB_ROOT/sector_lab/data/events.csv` (4,462 results, Jan-Mar 2021 to Apr-Jun 2026 results, "
         "NSE results times and XBRL filings). Sector: NSE index sector from results/nifty_sector_3day/results_3day.csv, "
         "else the Nifty 500 list.",
         "- Growth units: percent (events.csv stores fractions). PAT = profit attributable to owners (consolidated where "
         "filed; banks standalone); Sales = revenue from operations (banks: interest earned). YoY / QoQ growth is blank "
         "when the base quarter was zero or a loss, so those results count as neither PAT up nor PAT down.",
         "- Downloads are kept in SCREENER_DL and parsed as data only.", ""]
    if ctx["ca_list"]:
        N += ["Corporate actions listed by NSE since the project data (all symbols in the price data): "
              + "; ".join(ctx["ca_list"]) + ".", ""]
    rel = set(syms) | {r["symbol"] for r in ctx["recent"]}
    fut = [f"{x['symbol']} ex {x['ex']}: {x['subject']}" for x in ctx["ca_future"] if x["symbol"] in rel]
    N += ["Corporate actions ahead (ex-date after the run date) for the stocks here: " + ("; ".join(fut) or "none")
          + ".", ""]
    if ctx["missing_days"] or ctx["hol_warn"]:
        N += ["Warnings: " + "; ".join(ctx["hol_warn"] + [f"no price data for {x}" for x in ctx["missing_days"]]) + ".",
              ""]
    N += ["## Conventions", ""] + [f"- **{k.replace('_', ' ')}**: {v}." for k, v in CONVENTIONS.items()] + [
        "- **Upcoming windows** assume the results come out on the meeting date (the window does not depend on the "
        "timing). A release after midnight following the meeting makes the next day the result session under the "
        "project convention, which moves the window one session later.",
        "- **Trade 1 check (cutoff close)**: missed = the cutoff close is before the run date; today = the cutoff is "
        "the run date; otherwise the cutoff date. Signals are final at the cutoff close and provisional before it. "
        "Trigger levels: the highest cutoff close keeping the lag below -10% (exact, Nifty flat from the latest close; "
        "per 1% Nifty move), and the volume needed on each remaining session (equal volumes) for 1.0x and 1.3x; both "
        "are plugged back in as a check.",
        "- **Trade 2**: a conditional buy only when RSI(14) at the cutoff is above 50; RSI 50 or below is a skip "
        "even for a winner.",
        "- **Contracts**: hold the first monthly stock future expiring at least 3 sessions after the exit (stock "
        "futures settle by physical delivery and margins rise in the last days); if a nearer month (at least 5 "
        "sessions after the entry) expires first, trade it and roll before its expiry, or use the later month from "
        "the start. Lot size from the F&O bhavcopy; notional = lot x the latest cash close. The Nifty hedge for "
        "Trade 2 follows the same rule with Nifty futures.",
        "- **Single-day events**: a daily move beyond +-8% inside the 21-session lag window, or volume above 10x the "
        "median of the 60-session volume base, for the windows ending at the cutoff (sessions already in the data).",
        "- **Last-4 rank**: average of each current F&O stock's last 4 three-day sums in events.csv, ranked among all "
        f"{len(ctx['L4'])} current F&O stocks with 4+ results (top tenth = rank percentile above 90%). Results reported "
        "in October 2026 by early reporters are not in events.csv and are not counted.",
        "- **Auto**: hand-made 'Auto & auto parts' sector or NSE 'Automobile and Auto Components'.",
        "- **Run-up straddle**: the last close before the numbers is the Result day when the likely reaction day is "
        "Day+1, else Day-1; entry 5 sessions earlier; front expiry = last Tuesday of the month at least 3 sessions "
        "after the reaction day (as in fo_results_strategy/timeline.py); skipped when that expiry is more than 14 "
        "sessions after the exit; check the listed expiries and price it live.",
        "", "## How to read it", "",
        "1. Start with **Actions by date** in screener.md: one line per check, with its status (final or provisional), "
        "trigger levels, contract and ban flag.",
        "2. The only pre-results trade is Trade 1 (lag 10% + volume). It is decided at the cutoff close: use the "
        "trigger levels at about 15:20 that day. A provisional 'fires' can disappear, and a 'no' can turn into a "
        "'fires'.",
        "3. After the numbers, Trade 2 applies only to stocks with RSI(14) > 50 at the cutoff: if the reaction day "
        "closes more than 4% above Nifty's move, buy at the next open and hold 20 sessions against Nifty.",
        "4. The history (in-F&O first) is a record, not a forecast. Watch items (last-4 top tenth, auto) are for "
        "paper-trading only.",
        "", "## What the research says", "",
        "| Signal | Label | Tested result | Source |", "|---|---|---|---|"]
    N += [f"| {a} | {b} | {c} | {e} |" for a, b, c, e in ctx["research"]]
    N += ["", "Key point: **a stock's past three-day results moves do not predict the direction of its next one.** The "
          "per-stock averages, best / worst quarters and PAT up / down splits are a record, not a signal; with "
          "about 20 results per stock, a +1% or -1% average is well within chance.", "",
          "## Data checks", ""] + [f"- {x}" for x in ctx["checks"]] + [
          "- Validation detail for the latest project quarter: validation_qn_last.csv.", ""]
    (OUT / "notes.md").write_text("\n".join(N))


if __name__ == "__main__":
    main()
