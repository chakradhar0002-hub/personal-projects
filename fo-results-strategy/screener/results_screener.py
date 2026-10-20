#!/usr/bin/env python3
"""F&O quarterly-results screener for the next few days.

For every F&O stock (today's NSE fo_mktlots.csv list) with a results board meeting from --start to --start + --days
(calendar days, both ends included) it writes:

  calendar.csv      meeting date, usual timing, the expected three-day window (project convention), entry status
  history.csv       every past result of these stocks in the project data: reported growth, Day-1 / Result day /
                    Day+1 moves, three-day sum, against Nifty, reaction-day move against Nifty, results winner
  summary.csv       one row per stock: how its three-day results move behaved, after good vs bad profit, and the
                    project's tested signals at the cutoff close (or the latest close if the cutoff is still ahead)
  screener.md       the main table plus dated actions
  stocks/<SYM>.md   one page per company: its past results quarter by quarter and its summary
  screener.json     all of the above for a web page
  notes.md          sources, as-of times, how to read it, what the research says, data checks

    python3 -P screener/results_screener.py --start 2026-10-20 --days 7

Environment:
  LAB_ROOT     the project's scratch data folder (sector_lab/data, ta/build, dl_nifty_sector_lists); default 'lab'
  SCREENER_DL  folder for downloads; default LAB_ROOT/dl_screener_<run date>
  OUT          output folder; default plans/screener_<start>_to_<end> in this repository

Downloads (NSE event calendar, board meetings, holidays, F&O lots, corporate actions, cash bhavcopies, index closes)
are untrusted data: they are saved in SCREENER_DL and only parsed with json / pandas, never executed.

Project convention (report_builder/analyze_events.py): the result session is the results date if it is a trading
session, else the next session; Day-1 / Result day / Day+1 are the sessions before, of and after it; the cutoff is 2
sessions before the result session; the three-day sum is Day-1 + Result day + Day+1 daily returns (= cutoff close to
Day+1 close). The reaction day is Day+1 for results after the close on a trading day, else the Result day.
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
import urllib.request
from bisect import bisect_left
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
IST = timezone(timedelta(hours=5, minutes=30))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")
LAG_CUT, VOL_CUT, VOL_STRICT, WIN_CUT = -10.0, 1.0, 1.3, 4.0
AUTO_NSE = "Automobile and Auto Components"
AUTO_CUSTOM = "Auto & auto parts"


# ------------------------------------------------------------------------------------------------ small helpers
def d(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def nse_d(s: str) -> date:
    return datetime.strptime(s.strip(), "%d-%b-%Y").date()


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
    return x is not None and not (isinstance(x, float) and math.isnan(x))


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

    def flag(self, sym, msg):
        self.flags.setdefault(sym, []).append(msg)

    def append_day(self, day: str, bhav: pd.DataFrame, nifty_close: float, ca: dict):
        """Append one session from the cash bhavcopy (series EQ). ca: {(sym, day): (kind, factor, subject)}."""
        b = bhav[bhav.SctySrs.astype(str).str.strip() == "EQ"].drop_duplicates("TckrSymb").set_index("TckrSymb")
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


# ------------------------------------------------------------------------------------------------ parsing NSE files
def parse_lots(path: Path) -> list[str]:
    import csv
    rows = list(csv.reader(open(path, newline="")))
    return [r[1].strip() for r in rows[1:] if len(r) > 2 and r[2].strip().isdigit() and "NIFTY" not in r[1]]


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


# ------------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--start", help="first meeting date, YYYY-MM-DD (default: today in IST)")
    ap.add_argument("--days", type=int, default=7, help="calendar days after --start to include (default 7)")
    ap.add_argument("--today", help="run date, YYYY-MM-DD (default: today in IST); entry status is relative to it")
    ap.add_argument("--offline", action="store_true", help="use only files already in SCREENER_DL")
    a = ap.parse_args()

    now = datetime.now(IST)
    today = d(a.today) if a.today else now.date()
    start = d(a.start) if a.start else today
    end = start + timedelta(days=a.days)
    LAB = Path(os.environ.get("LAB_ROOT", "lab"))
    DL = Path(os.environ.get("SCREENER_DL", str(LAB / f"dl_screener_{today:%Y%m%d}")))
    OUT = Path(os.environ.get("OUT", str(REPO / "plans" / f"screener_{start}_to_{end}")))
    (OUT / "stocks").mkdir(parents=True, exist_ok=True)
    print(f"screener: meetings {start} to {end}, run date {today}; outputs -> {OUT}", flush=True)

    # ---------------------------------------------------------------- downloads
    dl = Downloader(DL, a.offline)
    api = "https://www.nseindia.com/api/"
    p_cal = dl.get(api + "event-calendar?index=equities", "event_calendar.json", api=True)
    p_bm = dl.get(api + f"corporate-board-meetings?index=equities&from_date={start:%d-%m-%Y}&to_date={end:%d-%m-%Y}",
                  f"board_meetings_{start:%Y%m%d}_{end:%Y%m%d}.json", api=True)
    p_hol = dl.get(api + "holiday-master?type=trading", "holiday_trading.json", api=True)
    p_lots = dl.get("https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv", "fo_mktlots.csv")
    if not p_lots:
        sys.exit("no F&O list (fo_mktlots.csv): cannot continue")
    fo = parse_lots(p_lots)
    fo_set = set(fo)
    holidays, hol_years = parse_holidays(p_hol)

    panel = Panel(LAB)
    plast = d(panel.project_last)
    p_ca = dl.get(api + f"corporates-corporateActions?index=equities&from_date={plast + timedelta(days=1):%d-%m-%Y}"
                        f"&to_date={today:%d-%m-%Y}", f"corp_actions_{plast + timedelta(days=1):%Y%m%d}_{today:%Y%m%d}.json",
                  api=True)
    ca = {}
    ca_list = []
    if p_ca:
        for x in json.loads(p_ca.read_text()):
            s = str(x.get("symbol", "")).strip()
            try:
                ex = nse_d(x["exDate"]).isoformat()
            except (KeyError, ValueError):
                continue
            kind, factor = ca_factor(str(x.get("subject", "")))
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

    horizon = end + timedelta(days=50)          # room for Day+1, 20 sessions after the reaction day and the expiry
    cal = Calendar(panel.sessions, holidays, horizon)
    hol_warn = [] if {start.year, horizon.year} <= hol_years else \
        [f"NSE holiday list covers {sorted(hol_years)} only: later dates assume every weekday is a session"]
    today_is_session = today.weekday() < 5 and today.isoformat() not in holidays
    today_note = "" if today_is_session else \
        f"{today:%a %d-%b-%Y} is not a trading session ({holidays.get(today.isoformat(), 'weekend')})"

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

    calendar_rows, summary_rows, history_rows, per_stock = [], [], [], {}
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
        if n_t:
            ranked = sorted(cats.values(), reverse=True)
            if ranked[0] == ranked[1]:
                usual = "Mixed"
                usual_txt = "Mixed: " + ", ".join(f"{k.lower()} {v}" for k, v in cats.items() if v) + f" (of {n_t})"
            else:
                usual = max(cats, key=cats.get)
                others = ", ".join(f"{k.lower()} {v}" for k, v in cats.items() if k != usual and v)
                usual_txt = f"{usual} {cats[usual]}/{n_t}" + (f" ({others})" if others else "")
        else:
            usual, usual_txt = "Unknown", "no past results"
        td_usual = ("After close" if ac > dmb else "During market" if dmb > ac else "Mixed") if n_td else "Unknown"
        mixed = td_usual in ("Mixed", "Unknown") or max(ac, dmb) / n_td < 0.75
        md = m["meeting_date"]
        w = cal.window(md, "After close" if td_usual == "After close" else "During market")
        if not w:
            continue
        on_session = w["on_session"]
        split = f"{ac} after the close, {dmb} during market hours"
        if not on_session:
            react_short, react_basis = "Result day", "Result day: the meeting is on a non-trading day"
        elif td_usual == "After close":
            react_short = "Day+1" if not mixed else "Day+1 (or Result day)"
            react_basis = (f"Day+1: of its results on trading days, {split}"
                           + ("; mixed, it could be the Result day" if mixed else ""))
        elif td_usual == "During market":
            react_short = "Result day" if not mixed else "Result day (or Day+1)"
            react_basis = (f"Result day: of its results on trading days, {split}"
                           + ("; mixed, it could be Day+1" if mixed else ""))
        else:
            react_short = "Result day (or Day+1)"
            react_basis = ("Result day if the numbers come during market hours, Day+1 if after the close "
                           + (f"(trading-day history split: {split})" if n_td else "(no trading-day history)"))
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
        pre = w["result_day"] if (td_usual == "After close" and on_session) else w["day_m1"]
        ru_entry = cal.shift(pre, -5)
        fexp = cal.front_expiry(w["reaction_day"])
        ru_gap = (cal.pos[fexp] - cal.pos[pre]) if fexp else None
        ru_ok = ru_gap is not None and ru_gap <= 14
        if ru_entry and d(ru_entry) < today:
            ru_status = "entry passed"
        elif not ru_ok:
            ru_status = "skip (front expiry more than 14 sessions after the exit)"
        else:
            ru_status = "today" if ru_entry and d(ru_entry) == today else f"buy {short_lbl(ru_entry)}"
        t2_buy = cal.shift(w["reaction_day"], 1)
        t2_exit = cal.shift(w["reaction_day"], 20)

        # signals: at the cutoff close if it is in the data, else at the latest close
        in_data = cut in panel.pos
        ci = panel.pos[cut] if in_data else i_latest
        basis = f"at the cutoff close {short_lbl(cut)} (final)" if in_data else \
            f"at the latest close {short_lbl(latest)} (provisional: re-check at the cutoff close {short_lbl(cut)})"
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

        # history rows
        hrows = []
        for r in g.itertuples():
            react_on = "Day+1" if r.timing == "After close" else "Result day"
            rr = r.ret_dp1 if react_on == "Day+1" else r.ret_rd
            ir = int(r.i_react) if isnum(r.i_react) else None
            nr = panel.nifty_ret(ir) if ir is not None else np.nan
            rxn = 100 * (rr - nr) if isnum(rr) and isnum(nr) else np.nan
            py = r.pat_yoy
            numbers = "good (PAT YoY > 0)" if isnum(py) and py > 0 else ("bad (PAT YoY <= 0)" if isnum(py) else
                                                                       "unclassified (no PAT YoY)")
            hrows.append({
                "symbol": s, "company": r.company,
                "in_fo": {"True": "yes", "False": "no"}.get(str(r.in_fo), ""),
                "quarter": r.quarter, "qn": int(r.qn), "period": r.period, "results_date": r.results_date,
                "results_time": r.results_time, "timing": r.timing,
                "sales_yoy_pct": sp(100 * r.sales_yoy) if isnum(r.sales_yoy) else "",
                "pat_yoy_pct": sp(100 * r.pat_yoy) if isnum(r.pat_yoy) else "",
                "sales_qoq_pct": sp(100 * r.sales_qoq) if isnum(r.sales_qoq) else "",
                "pat_qoq_pct": sp(100 * r.pat_qoq) if isnum(r.pat_qoq) else "",
                "numbers": numbers.split(" ")[0],
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
            best = H.loc[H._td.idxmax()] if td_all.size else None
            worst = H.loc[H._td.idxmin()] if td_all.size else None
            last = H.iloc[-1]
            xn = H._xn.dropna()
            summ = {
                "n_past": len(H), "n_past_in_fo": int((H.in_fo == "yes").sum()),
                "first_period": H.period.iloc[0], "last_period": last.period,
                "avg_3d": td_all.mean(), "median_3d": td_all.median(), "share_up": 100 * (td_all > 0).mean(),
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
                                        "worst_3d", "last_3d", "good_avg", "bad_avg", "good_up", "bad_up", "avg_xn")}
            summ.update(n_past=0, n_past_in_fo=0, first_period="", last_period="", best_period="", worst_period="",
                        good_n=0, bad_n=0, unclassified_n=0, winners_n=0, losers_n=0, xn_n=0)
        l4 = L4.get(s, np.nan)
        l4_top = bool(isnum(l4) and L4_pct.get(s, 0) > 0.9)
        is_auto = s in auto_syms
        notes = [m["date_note"]] if m["date_note"] else []
        notes += panel.flags.get(s, [])
        if not len(H):
            notes.append("no past results in the project data (events.csv)")

        cal_row = {
            "meeting_date": md, "weekday": d(md).strftime("%a"), "symbol": s, "company": company,
            "purpose": m["purpose"], "source": m["source"], "sector": sector_of(s),
            "usual_timing": usual, "timing_history": usual_txt,
            "share_during_market_pct": f"{100 * dmb / n_t:.0f}" if n_t else "",
            "share_after_close_pct": f"{100 * ac / n_t:.0f}" if n_t else "",
            "share_non_trading_day_pct": f"{100 * nt / n_t:.0f}" if n_t else "",
            "past_results_with_timing": n_t,
            "trading_day_usual": td_usual,
            "cutoff": w["cutoff"], "day_m1": w["day_m1"], "result_day": w["result_day"], "day_p1": w["day_p1"],
            "meeting_on_trading_day": "yes" if on_session else "no",
            "expected_reaction_day": w["reaction_day"], "reaction_on": react_short, "reaction_basis": react_basis,
            "holiday_in_window": "; ".join(hol_in),
            "pre_results_entry": status, "pre_results_entry_note": status_txt,
            "signal_asof": panel.sessions[ci], "signal_basis": basis,
            "winners_trade_buy_next_open_if_winner": t2_buy or "", "winners_trade_exit_close": t2_exit or "",
            "runup_entry": ru_entry or "", "runup_exit_close": pre, "runup_front_expiry": fexp or "",
            "runup_sessions_exit_to_expiry": ru_gap if ru_gap is not None else "", "runup_status": ru_status,
            "notes": "; ".join(notes)}
        calendar_rows.append(cal_row)

        srow = {
            "results_date": md, "symbol": s, "company": company, "sector": sector_of(s),
            "auto_sector": "yes" if is_auto else "no", "usual_timing": usual_txt,
            "cutoff": w["cutoff"], "day_m1": w["day_m1"], "result_day": w["result_day"], "day_p1": w["day_p1"],
            "expected_reaction_day": w["reaction_day"], "holiday_in_window": "; ".join(hol_in),
            "pre_results_entry": status,
            "n_past": summ["n_past"], "n_past_in_fo": summ["n_past_in_fo"],
            "periods": f"{summ['first_period']} to {summ['last_period']}" if summ["n_past"] else "",
            "avg_3d_pct": sp(summ["avg_3d"]), "median_3d_pct": sp(summ["median_3d"]),
            "share_up_pct": f"{summ['share_up']:.0f}" if isnum(summ["share_up"]) else "",
            "avg_abs_3d_pct": f"{summ['avg_abs_3d']:.2f}" if isnum(summ["avg_abs_3d"]) else "",
            "avg_3d_vs_nifty_pct": sp(summ["avg_3d_vs_nifty"]),
            "best_period": summ["best_period"], "best_3d_pct": sp(summ["best_3d"]),
            "worst_period": summ["worst_period"], "worst_3d_pct": sp(summ["worst_3d"]),
            "last_period": summ["last_period"], "last_3d_pct": sp(summ["last_3d"]),
            "last4_avg_pct": sp(l4), "last4_rank": f"{L4_rank[s]} of {len(L4)}" if s in L4_rank else "",
            "last4_top_tenth": ("yes" if l4_top else "no") if isnum(l4) else "",
            "good_numbers_n": summ["good_n"], "good_numbers_avg_3d_pct": sp(summ["good_avg"]),
            "good_numbers_share_up_pct": f"{summ['good_up']:.0f}" if isnum(summ["good_up"]) else "",
            "bad_numbers_n": summ["bad_n"], "bad_numbers_avg_3d_pct": sp(summ["bad_avg"]),
            "bad_numbers_share_up_pct": f"{summ['bad_up']:.0f}" if isnum(summ["bad_up"]) else "",
            "unclassified_n": summ["unclassified_n"],
            "winners_n": summ["winners_n"], "losers_n": summ["losers_n"], "reactions_n": summ["xn_n"],
            "avg_reaction_vs_nifty_pct": sp(summ["avg_xn"]),
            "signal_asof": panel.sessions[ci], "signal_basis": basis,
            "lag_vs_nifty_21d_pct": sp(lag), "stock_21d_pct": sp(panel.stock21(s, ci)),
            "nifty_21d_pct": sp(panel.nifty21(ci)), "vol_ratio_5_60": f"{vr:.2f}" if isnum(vr) else "",
            "lag10_volume_rule": rule, "rsi14": f"{rs14:.1f}" if isnum(rs14) else "",
            "rsi14_above_50": ("yes" if rs14 > 50 else "no") if isnum(rs14) else "",
            "lag_latest_pct": sp(lag_l), "vol_ratio_latest": f"{vr_l:.2f}" if isnum(vr_l) else "",
            "rsi14_latest": f"{rs_l:.1f}" if isnum(rs_l) else "",
            "runup_status": ru_status, "notes": "; ".join(notes)}
        summary_rows.append(srow)
        per_stock[s] = {"cal": cal_row, "sum": srow, "summ": summ, "H": H, "rule_txt": rule_txt, "status_txt": status_txt,
                        "react_basis": react_basis, "react_short": react_short, "usual": usual,
                        "lag": lag, "vr": vr, "rsi": rs14, "l4": l4, "l4_top": l4_top,
                        "auto": is_auto, "in_data": in_data, "ci": ci, "t2_buy": t2_buy, "t2_exit": t2_exit,
                        "ru_entry": ru_entry, "pre": pre, "fexp": fexp, "ru_status": ru_status}

    # ---------------------------------------------------------------- write CSVs
    pd.DataFrame(calendar_rows).to_csv(OUT / "calendar.csv", index=False)
    pd.DataFrame(summary_rows).to_csv(OUT / "summary.csv", index=False)
    hist = pd.DataFrame(history_rows)
    hcols = [c for c in hist.columns if not c.startswith("_")]
    hist[hcols].to_csv(OUT / "history.csv", index=False)

    # history.csv three-day values against events.csv
    hb = pd.read_csv(OUT / "history.csv", usecols=["symbol", "qn", "three_day_pct"])
    mm = hb.merge(ev[["symbol", "qn", "three_day"]], on=["symbol", "qn"], how="left")
    ok = mm.three_day_pct.isna() & mm.three_day.isna() | ((mm.three_day_pct - 100 * mm.three_day).abs() < 0.0051)
    checks.append(f"history.csv: {len(mm)} rows; three-day % equal to events.csv three_day x 100 (2-decimal rounding) "
                  f"on {int(ok.sum())} of {len(mm)}; rows per stock equal to its events.csv results: "
                  f"{all((ev.symbol == s).sum() == (hb.symbol == s).sum() for s in per_stock)}")

    # ---------------------------------------------------------------- texts
    asof = {"latest_close": latest, "latest_close_label": day_lbl(latest),
            "project_data_to": panel.project_last,
            "appended_bhavcopy_days": panel.appended,
            "calendar_downloaded": dl.fetched("event_calendar.json"),
            "board_meetings_downloaded": dl.fetched(f"board_meetings_{start:%Y%m%d}_{end:%Y%m%d}.json"),
            "fo_list_downloaded": dl.fetched("fo_mktlots.csv"),
            "run_date": today.isoformat(), "generated_ist": now.strftime("%Y-%m-%d %H:%M IST")}
    research = research_lines()
    write_markdown(OUT, cal, start, end, today, today_note, latest, order, per_stock, asof, len(fo), L4, research,
                   checks, hol_warn, missing_days, ca_list)
    js = {"title": f"F&O results screener {start} to {end}", "data_as_of": asof,
          "window": {"start": start.isoformat(), "end": end.isoformat(), "days": a.days, "today": today.isoformat(),
                     "today_note": today_note},
          "fo_stocks": len(fo), "stocks_in_window": len(order),
          "conventions": CONVENTIONS, "calendar": calendar_rows, "summary": summary_rows,
          "history": {s: [{k: v for k, v in r.items() if not k.startswith("_")} for r in history_rows if r["symbol"] == s]
                      for s in per_stock},
          "research": [{"signal": x[0], "label": x[1], "finding": x[2], "source": x[3]} for x in research],
          "checks": checks, "warnings": hol_warn + [f"price data not available for {x}" for x in missing_days],
          "notes": NOTES}
    (OUT / "screener.json").write_text(json.dumps(js, indent=1, ensure_ascii=False, default=str))
    print("\n".join("check: " + c for c in checks))
    print(f"wrote {OUT}/calendar.csv, history.csv, summary.csv, screener.md, notes.md, screener.json, "
          f"stocks/*.md ({len(per_stock)})")


CONVENTIONS = {
    "result_session": "the results (board-meeting) date if it is a trading session, else the next session",
    "window": "cutoff = 2 sessions before the result session; Day-1, Result day, Day+1 = the sessions before, of and "
              "after the result session",
    "three_day": "Day-1 + Result day + Day+1 daily close-to-close returns (= cutoff close to Day+1 close), percent",
    "reaction_day": "Day+1 for results after the close on a trading day, else the Result day",
    "winner": "reaction-day return minus Nifty 50's return that day > +4%",
    "lag": "21-session return minus Nifty 50's 21-session return, at the close",
    "volume_ratio": "mean volume of the last 5 sessions / mean of the last 60 (split / bonus adjusted)",
    "rsi14": "Wilder RSI(14) on adjusted closes",
    "growth": "Sales / PAT growth in percent; PAT = profit attributable to owners (consolidated where filed; banks "
              "standalone); Sales = revenue from operations (banks: interest earned); blank when the base quarter "
              "was zero or a loss",
}

NOTES = [
    "Descriptive history: a stock's past three-day results moves do not predict the direction of its next one.",
    "Reported numbers are known only on the results day; the three-day window starts before them (Day-1).",
    "Only the lag 10% + volume rule (before results) and the results-winners trade (after results) held up in the "
    "project's tests, and both are to be paper-traded first.",
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
        ("Results winners (after results)", "TRADE (paper-trade)",
         "Reaction-day return beats Nifty by more than 4%: buy at the next open, hold 20 sessions against Nifty. All "
         "winners +1.45% a trade over Nifty (392 trades, 15 of 22 quarters); with RSI(14) > 50 at the cutoff +2.42% "
         "(232 trades, 17 of 22), +2.04% at the next open with 0.40% cost. Realistic about +1% over Nifty. Winners "
         "with RSI 50 or below: +0.04%, skip.", "docs/SUMMARY.md, docs/WINNERS_RSI50.md"),
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
         "Rank correlation with last quarter's move +0.005 (3,177 results); up after an up quarter 49%, after a down "
         "quarter 48%; no lag of 1-8 quarters and none of 84 pattern tests confirmed.",
         "results/prev_quarter_patterns/, docs/QUARTER_CORRELATION.md"),
        ("Size of a stock's earlier three-day moves -> size of its next one", "DESCRIPTIVE (options only)",
         "Persists a little (rank correlation about +0.05 with last quarter's absolute move), mostly because volatile "
         "stocks move more (60-day volatility alone +0.12). Says nothing about direction; no cash trade.",
         "results/prev_quarter_patterns/table_magnitude.md"),
        ("Last result a winner / a loser", "NOT PREDICTIVE",
         "Next three-day window -0.04% after a winner, +0.06% after a loser.", "docs/PAST_PERFORMANCE.md"),
        ("Good or bad reported numbers", "NOT PREDICTIVE (known only after the numbers)",
         "No fundamental screen before results works (44 screens within about +-0.3%); after results, strong numbers "
         "bought +0.52% over 20 sessions vs +0.43% for all results, and shorting bad numbers lost money. The per-stock "
         "'after good / bad numbers' columns here are descriptive.", "docs/FUNDAMENTAL_ANALYSIS.md"),
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


def write_markdown(OUT, cal, start, end, today, today_note, latest, order, per_stock, asof, n_fo, L4, research,
                   checks, hol_warn, missing_days, ca_list):
    head = [f"# F&O results screener: {day_lbl(start)} to {day_lbl(end)}", ""]
    head.append(f"Data as of the **{day_lbl(latest)} close** (NSE cash bhavcopy); results calendar downloaded "
                f"{asof['calendar_downloaded']}; run date {day_lbl(today)}." + (f" {today_note}." if today_note else ""))
    head.append("")
    head.append(f"{len(per_stock)} of today's {n_fo} F&O stocks have a results board meeting from {short_lbl(start)} to "
                f"{short_lbl(end)}. History columns describe each stock's past results windows; they do not predict "
                "the next one. Only the lag + volume rule (before results) and the winners trade (after results) are "
                "trades, both to paper-trade first. Read [notes.md](notes.md) before using any of it.")
    head.append("")

    tbl = ["| Results | Stock | Sector | Usual timing | Cutoff / Day-1 / Result day / Day+1 | Pre-results entry | "
           "Past results | Avg 3-day | Median | Up | Avg size | Best | Worst | Last | Last-4 avg (rank) | "
           "Good PAT: avg (n) | Bad PAT: avg (n) | Winners | Signals as of | Lag vs Nifty | Vol 5/60 | "
           "Lag 10% + vol | RSI(14) | Auto |",
           "|---|---|---|---|---|---|---:|---:|---:|---:|---:|---|---|---:|---|---|---|---:|---|---:|---:|---|---:|---|"]
    for m in order:
        s = m["symbol"]
        p = per_stock.get(s)
        if not p:
            continue
        c, r, su = p["cal"], p["sum"], p["summ"]
        win = " / ".join(x[8:10].lstrip("0") + "-" + d(x).strftime("%b") for x in (c["cutoff"], c["day_m1"],
                                                                                 c["result_day"], c["day_p1"]))
        if c["holiday_in_window"]:
            win += " (holiday inside)"
        timing = r["usual_timing"].replace(" of ", "/")
        entry = "missed" if c["pre_results_entry"] == "missed" else (
            "today" if c["pre_results_entry"] == "today" else short_lbl(c["pre_results_entry"]))
        best = f"{spc(su['best_3d'])} {su['best_period']}" if isnum(su["best_3d"]) else "-"
        worst = f"{spc(su['worst_3d'])} {su['worst_period']}" if isnum(su["worst_3d"]) else "-"
        l4 = (f"{spc(p['l4'])} ({r['last4_rank']}{', top tenth' if p['l4_top'] else ''})"
              if isnum(p["l4"]) else "-")
        good = f"{spc(su['good_avg'])} ({su['good_n']})" if su["good_n"] else "- (0)"
        bad = f"{spc(su['bad_avg'])} ({su['bad_n']})" if su["bad_n"] else "- (0)"
        wins = f"{su['winners_n']} of {su['xn_n']}" if su["xn_n"] else "-"
        sig_asof = short_lbl(r["signal_asof"]) + (" (cutoff)" if p["in_data"] else " (latest)")
        rule = p["rule_txt"]
        rsi_t = f"{p['rsi']:.1f}" if isnum(p["rsi"]) else "-"
        tbl.append(
            f"| {short_lbl(c['meeting_date'])} | {s} | {r['sector']} | {timing} | {win} | {entry} | {su['n_past']} | "
            f"{spc(su['avg_3d'])} | {spc(su['median_3d'])} | "
            f"{(str(r['share_up_pct']) + '%') if r['share_up_pct'] != '' else '-'} | "
            f"{(r['avg_abs_3d_pct'] + '%') if r['avg_abs_3d_pct'] else '-'} | {best} | {worst} | {spc(su['last_3d'])} | "
            f"{l4} | {good} | {bad} | {wins} | {sig_asof} | {spc(p['lag'])} | "
            f"{(format(p['vr'], '.2f') + 'x') if isnum(p['vr']) else '-'} | {rule} | {rsi_t} | "
            f"{'yes' if p['auto'] else 'no'} |")
    legend = [
        "",
        "Columns: **Usual timing** = how its past results came out (after close / during market, count of past "
        "results). **Cutoff / Day-1 / Result day / Day+1** = the project's three-day window for this meeting date "
        "(buy at the cutoff close, sell at the Day+1 close). **Pre-results entry** = missed (cutoff close already "
        "passed), today, or the cutoff date. **Past results** = results in the project data (Jan-Mar 2021 to Apr-Jun "
        "2026 results, any F&O status). **Avg / Median 3-day, Up, Avg size** = average, median, share positive and "
        "average absolute value of its past three-day sums. **Best / Worst / Last** = its best, worst and latest "
        "three-day sum. **Last-4 avg (rank)** = average of its last 4 three-day sums, ranked among all current F&O "
        "stocks with 4+ results (top tenth = the PAST_PERFORMANCE watch item). **Good / Bad PAT** = average three-day "
        "sum when PAT grew year on year / did not (results with no PAT YoY, e.g. a loss a year earlier, are in "
        "neither); descriptive only, the numbers come out inside the window. **Winners** = past reaction days that "
        "beat Nifty by more than 4%. **Signals as of** = the cutoff close if it is in the data, else the latest close "
        "(provisional: re-check at the cutoff close). **Lag vs Nifty** = 21-session return minus Nifty 50's. "
        "**Vol 5/60** = 5-session / 60-session average volume. **Lag 10% + vol** = Trade 1 (lag below -10% and "
        "volume >= 1.0x; 1.3x stricter). **RSI(14)** above 50 = the stronger version of Trade 2 if the stock then beats "
        "Nifty by more than 4% on its reaction day. **Auto** = auto / auto-parts watch item.",
    ]

    # dated actions, one line per kind of action per day
    acts: dict[str, dict[str, list[str]]] = {}

    def add(day, kind, txt):
        if day:
            acts.setdefault(day, {}).setdefault(kind, []).append(txt)

    for m in order:
        s = m["symbol"]
        p = per_stock.get(s)
        if not p:
            continue
        c = p["cal"]
        if c["pre_results_entry"] != "missed":
            add(c["cutoff"], "cutoff", s)
            if p["rule_txt"].startswith("fires"):
                add(c["cutoff"], "cutoff_fires", f"{s} (lag {spc(p['lag'])}, volume {p['vr']:.2f}x)")
        elif p["rule_txt"].startswith("fires"):
            add(c["cutoff"], "missed_fired", f"{s} (lag {spc(p['lag'])}, volume {p['vr']:.2f}x)")
        add(c["meeting_date"], "meeting", f"{s} ({p['usual'].lower()})")
        rs = f"RSI {p['rsi']:.1f}" if isnum(p["rsi"]) else "RSI n/a"
        alt = " or Day+1" if "(or Day+1)" in p["react_short"] else (" or Result day" if "(or Result day)" in
                                                                     p["react_short"] else "")
        add(c["expected_reaction_day"], "reaction", f"{s} ({rs}{'; reaction may be' + alt[3:] if alt else ''})")
        if p["ru_status"].startswith("buy") or p["ru_status"] == "today":
            add(p["ru_entry"], "runup", f"{s} ({short_lbl(p['fexp'])} expiry, sell at the {short_lbl(p['pre'])} close)")
    act_lines = ["", "## Dated actions", "",
                 "Only the lag 10% + volume trade is held across the numbers (cutoff close to Day+1 close). The winners "
                 "trade starts after the reaction-day close. Provisional signals must be re-checked at the cutoff close.",
                 ""]
    for day in sorted(acts):
        a = acts[day]
        nxt, ex20 = cal.shift(day, 1), cal.shift(day, 20)
        act_lines.append(f"**{day_lbl(day)}**" + (" (past)" if d(day) < today else ""))
        if "missed_fired" in a:
            act_lines.append(f"- Lag 10% + volume fired at this cutoff close, entry missed: {', '.join(a['missed_fired'])}.")
        if "cutoff" in a:
            fires = f" Fires on the latest close (provisional): {', '.join(a['cutoff_fires'])}." if "cutoff_fires" in a \
                else " None fires on the latest close."
            act_lines.append(f"- Cutoff close, check lag 10% + volume (buy at this close if it fires, sell at the Day+1 "
                             f"close): {', '.join(a['cutoff'])}.{fires}")
        if "meeting" in a:
            act_lines.append(f"- Results board meetings (usual timing): {', '.join(a['meeting'])}.")
        if "reaction" in a:
            act_lines.append(f"- Expected reaction day: a close more than 4% above Nifty's move makes a results winner; "
                             f"buy at the next open{(' ' + short_lbl(nxt)) if nxt else ''}, hold 20 sessions against "
                             f"Nifty{(' (to about ' + short_lbl(ex20) + ')') if ex20 else ''}; RSI(14) at the cutoff "
                             f"above 50 is the stronger version: {', '.join(a['reaction'])}.")
        if "runup" in a:
            act_lines.append(f"- Run-up straddle entry (marginal; price it live): {', '.join(a['runup'])}.")
        act_lines.append("")

    fired = [s for s in per_stock if per_stock[s]["rule_txt"].startswith("fires")]
    fired_txt = ", ".join(f"{s} ({per_stock[s]['rule_txt']}, lag {spc(per_stock[s]['lag'])}, volume "
                          f"{per_stock[s]['vr']:.2f}x)" for s in fired) or "fires for none"
    tops = [s for s in per_stock if per_stock[s]["l4_top"]]
    autos = [s for s in per_stock if per_stock[s]["auto"]]
    rsi50 = [s for s in per_stock if isnum(per_stock[s]["rsi"]) and per_stock[s]["rsi"] > 50]
    keys = ["", "## At a glance", "",
            f"- Lag 10% + volume (Trade 1): {fired_txt}.",
            f"- RSI(14) above 50 at the cutoff (winners-trade filter, only matters if the stock beats Nifty by more than "
            f"4% on its reaction day): {len(rsi50)} of {len(per_stock)}: {', '.join(rsi50) or 'none'}.",
            f"- Last-4 three-day average in the top tenth of current F&O stocks (watch item): {', '.join(tops) or 'none'}.",
            f"- Auto / auto-parts (watch item): {', '.join(autos) or 'none'}.",
            f"- Pre-results entries already missed: {sum(per_stock[s]['cal']['pre_results_entry'] == 'missed' for s in per_stock)}"
            f" of {len(per_stock)} (cutoff close before {day_lbl(today)})."]
    main_md = "\n".join(["## Main table", ""] + tbl + legend)
    (OUT / "screener.md").write_text("\n".join(head) + "\n" + main_md + "\n" + "\n".join(keys) + "\n" +
                                     "\n".join(act_lines) + "\nPer stock: " +
                                     ", ".join(f"[{s}](stocks/{safe_name(s)}.md)" for s in per_stock) + "\n")

    # per-stock pages
    for s, p in per_stock.items():
        c, r, su, H = p["cal"], p["sum"], p["summ"], p["H"]
        L = [f"# {s}: {c['company']}", "",
             f"**Results board meeting {day_lbl(c['meeting_date'])}** ({c['purpose']}; source: NSE {c['source']}). "
             f"Sector: {c['sector']}.{' Auto / auto-parts watch item.' if p['auto'] else ''}", "",
             f"- Timing of its past results: {c['timing_history']}. Expected reaction day: "
             f"{short_lbl(c['expected_reaction_day'])}, the {p['react_basis']}.",
             f"- Three-day window (project convention): cutoff {short_lbl(c['cutoff'])} close, Day-1 "
             f"{short_lbl(c['day_m1'])}, Result day {short_lbl(c['result_day'])}, Day+1 {short_lbl(c['day_p1'])}"
             + (f"; holiday inside: {c['holiday_in_window']}" if c["holiday_in_window"] else "") + ".",
             f"- Pre-results entry (cutoff close): {p['status_txt']}.", ""]
        L += ["## Signals", "",
              f"Measured {r['signal_basis']}.", "",
              f"- Lag 10% + volume (Trade 1, paper-trade): 21-session return "
              f"{(r['stock_21d_pct'] + '%') if r['stock_21d_pct'] else '-'} vs Nifty 50 "
              f"{(r['nifty_21d_pct'] + '%') if r['nifty_21d_pct'] else '-'}: lag {spc(p['lag'])}; "
              f"volume 5/60 {r['vol_ratio_5_60'] or '-'}x -> **{p['rule_txt']}**.",
              f"- RSI(14): {r['rsi14'] or '-'}. Winners trade (Trade 2, paper-trade): if the reaction-day return beats "
              f"Nifty's by more than 4%, buy at the next open ({short_lbl(p['t2_buy'])}) and hold 20 sessions against "
              f"Nifty (to about {short_lbl(p['t2_exit'])}); RSI above 50 at the cutoff is the stronger version.",
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
        L += ["## Summary of its past three-day results moves", ""]
        if su["n_past"]:
            L += [f"- {su['n_past']} results ({su['first_period']} to {su['last_period']}), {su['n_past_in_fo']} of them "
                  f"while in F&O.",
                  f"- Three-day sum: average {spc(su['avg_3d'])}, median {spc(su['median_3d'])}, up in "
                  f"{su['share_up']:.0f}% of results; average size (absolute) {su['avg_abs_3d']:.2f}%; average vs "
                  f"Nifty {spc(su['avg_3d_vs_nifty'])}.",
                  f"- Best {spc(su['best_3d'])} ({su['best_period']}), worst {spc(su['worst_3d'])} ({su['worst_period']}),"
                  f" last {spc(su['last_3d'])} ({su['last_period']}).",
                  f"- After good numbers (PAT YoY > 0): {su['good_n']} results, average {spc(su['good_avg'])}"
                  + (f", up {su['good_up']:.0f}%" if isnum(su['good_up']) else "") +
                  f". After bad numbers (PAT YoY <= 0): {su['bad_n']} results, average {spc(su['bad_avg'])}"
                  + (f", up {su['bad_up']:.0f}%" if isnum(su['bad_up']) else "") +
                  f". No PAT YoY: {su['unclassified_n']}. Descriptive: the numbers come out inside the window.",
                  f"- Reaction day vs Nifty: average {spc(su['avg_xn'])}; results winners (> +4%) {su['winners_n']} of "
                  f"{su['xn_n']}, losers (< -4%) {su['losers_n']}.",
                  "- Its earlier three-day moves do not predict the direction of the next one (project test: rank "
                  "correlation +0.005 with the previous quarter); bigger past moves go with somewhat bigger future "
                  "moves, mostly because the stock is volatile.", ""]
            L += ["## Past results, quarter by quarter (newest first)", "",
                  "Growth in percent (blank: no filing, or a zero / loss base a year or a quarter earlier). Moves in "
                  "percent; reaction = Result day for results during market hours or on a non-trading day, Day+1 for "
                  "results after the close.", "",
                  "| Period | Quarter | Results | Time | Timing | F&O | Sales YoY | PAT YoY | Sales QoQ | PAT QoQ | "
                  "Day-1 | Result day | Day+1 | 3-day | 3-day vs Nifty | Reaction vs Nifty | Winner |",
                  "|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
            for h in reversed(H.to_dict("records")):
                L.append(f"| {h['period']} | {h['quarter']} | {h['results_date']} | {h['results_time']} | {h['timing']} | "
                         f"{h['in_fo']} | {h['sales_yoy_pct'] or '-'} | {h['pat_yoy_pct'] or '-'} | "
                         f"{h['sales_qoq_pct'] or '-'} | {h['pat_qoq_pct'] or '-'} | {h['day_m1_pct'] or '-'} | "
                         f"{h['result_day_pct'] or '-'} | {h['day_p1_pct'] or '-'} | **{h['three_day_pct'] or '-'}** | "
                         f"{h['three_day_vs_nifty_pct'] or '-'} | {h['reaction_vs_nifty_pct'] or '-'} | "
                         f"{h['winner'] or '-'} |")
        else:
            L.append("No past results in the project data.")
        L += ["", "[Back to the screener](../screener.md)", ""]
        (OUT / "stocks" / f"{safe_name(s)}.md").write_text("\n".join(L))

    # notes
    N = ["# Notes: F&O results screener", "",
         f"Meetings {day_lbl(start)} to {day_lbl(end)}; run date {day_lbl(today)}"
         + (f" ({today_note})" if today_note else "") + ".", "",
         "## Data and as-of times", "",
         f"- Prices: the project's data pack (`LAB_ROOT/sector_lab/data`: returns.csv, index_close.csv, sessions.csv; "
         f"`LAB_ROOT/ta/build/adjusted_ohlcv.csv.gz` for adjusted closes and volumes) to {day_lbl(asof['project_data_to'])}, "
         f"then NSE cash bhavcopies (series EQ close and total traded quantity) and NSE index closes (Nifty 50) for "
         f"{', '.join(short_lbl(x) for x in asof['appended_bhavcopy_days']) or 'no further days'}. "
         f"**Latest close: {day_lbl(latest)}.**",
         f"- Results meetings: NSE event calendar (downloaded {asof['calendar_downloaded']}) and NSE board-meeting list "
         f"for the window (downloaded {asof['board_meetings_downloaded']}); only meetings whose purpose includes "
         "financial results. Dates can change: check the company's filing.",
         f"- F&O list: today's NSE fo_mktlots.csv (downloaded {asof['fo_list_downloaded']}), {n_fo} stocks.",
         "- Trading holidays: NSE holiday master (capital market). Corporate actions since the project data: NSE "
         "corporate actions list (splits / bonuses adjust earlier closes and volumes; demergers leave that day's return "
         "blank; moves beyond +-35% are flagged).",
         "- Past results: `LAB_ROOT/sector_lab/data/events.csv` (4,462 results, Jan-Mar 2021 to Apr-Jun 2026 results, "
         "NSE results times and XBRL filings). Sector: NSE index sector from results/nifty_sector_3day/results_3day.csv, "
         "else the Nifty 500 list.",
         "- Growth units: percent (events.csv stores fractions). PAT = profit attributable to owners (consolidated where "
         "filed; banks standalone); Sales = revenue from operations (banks: interest earned). YoY / QoQ growth is blank "
         "when the base quarter was zero or a loss, so those results count as neither good nor bad numbers.",
         "- Downloads are kept in SCREENER_DL and parsed as data only.", ""]
    if ca_list:
        N += ["Corporate actions listed by NSE since the project data (all symbols in the price data): "
              + "; ".join(ca_list) + ".", ""]
    if missing_days or hol_warn:
        N += ["Warnings: " + "; ".join(hol_warn + [f"no price data for {x}" for x in missing_days]) + ".", ""]
    N += ["## Conventions", ""] + [f"- **{k.replace('_', ' ')}**: {v}." for k, v in CONVENTIONS.items()] + [
        "- **Upcoming windows** assume the results come out on the meeting date. The window does not depend on the "
        "timing; the reaction day does (Day+1 if the company usually reports after the close, else the Result day).",
        "- **Entry status**: missed = the cutoff close is before the run date; today = the cutoff is the run date; "
        "otherwise the cutoff date. Signals are measured at the cutoff close when it is in the data (final), else at "
        "the latest close (provisional, must be re-checked at the cutoff close).",
        "- **Last-4 rank**: average of each current F&O stock's last 4 three-day sums in events.csv, ranked among all "
        f"{len(L4)} current F&O stocks with 4+ results (top tenth = rank percentile above 90%). Results reported in "
        "October 2026 by early reporters are not in events.csv and are not counted.",
        "- **Auto**: hand-made 'Auto & auto parts' sector or NSE 'Automobile and Auto Components'.",
        "- **Run-up straddle**: the last close before the numbers is the Result day for usual after-close reporters on a "
        "trading day, else Day-1; entry 5 sessions earlier; front expiry = last Tuesday of the month at least 3 sessions "
        "after the reaction day (as in fo_results_strategy/timeline.py); check the listed expiries and price it live.",
        "", "## How to read it", "",
        "1. The history (average, median, share up, best / worst, good vs bad numbers) shows how the stock has moved "
        "around its results. It is description, not a forecast: the project found no link between a stock's earlier "
        "three-day moves and the direction of its next one. The average size tells you how much it tends to move.",
        "2. The only pre-results trade is the lag 10% + volume rule. Check it at the cutoff close; a provisional "
        "'fires' on an earlier close can disappear, and a 'no' can turn into a 'fires'.",
        "3. After the numbers, watch the reaction day: a close more than 4% above Nifty's move makes a results winner "
        "(buy at the next open, hold 20 sessions against Nifty); RSI(14) above 50 at the cutoff is the stronger version.",
        "4. Watch items (last-4 top tenth, auto) are for paper-trading only.",
        "", "## What the research says", "",
        "| Signal | Label | Tested result | Source |", "|---|---|---|---|"]
    N += [f"| {a} | {b} | {c} | {e} |" for a, b, c, e in research]
    N += ["", "Key point: **a stock's past three-day results moves do not predict the direction of its next one.** The "
          "per-stock averages, best / worst quarters and good / bad numbers splits are a record, not a signal; with "
          "about 20 results per stock, a +1% or -1% average is well within chance.", "",
          "## Data checks", ""] + [f"- {x}" for x in checks] + [
          "- Validation detail for the latest project quarter: validation_qn_last.csv.", ""]
    (OUT / "notes.md").write_text("\n".join(N))


if __name__ == "__main__":
    main()
