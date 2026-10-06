"""Second-source data for the cross-check: BSE daily closes (Yahoo Finance .BO tickers, exchange = BSE) and Yahoo's
quarterly revenue / net income. bseindia.com itself is not reachable from the build machine.

    python3 bse_check_fetch.py DATA/report/events.json DATA/report/yahoo_bse.json
"""
import json, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

EVENTS, OUT = sys.argv[1], sys.argv[2]
syms = sorted({r["symbol"] for r in json.load(open(EVENTS))})
UA = {"User-Agent": "Mozilla/5.0"}


def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.load(r)
        except Exception as e:
            err = e
            time.sleep(1.5 * (i + 1))
    return {"_error": str(err)}


def closes(sym):
    t = urllib.parse.quote(f"{sym}.BO")
    best = {}
    for url in (f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=5y&interval=1d",
                f"https://query2.finance.yahoo.com/v8/finance/chart/{t}?period1=1640995200&period2=1791331200&interval=1d"):
        d = get(url)
        res = (d.get("chart") or {}).get("result") or []
        if not res:
            continue
        r = res[0]
        off = r["meta"].get("gmtoffset", 19800)
        q = r["indicators"]["quote"][0]
        out = {}
        for ts, c, v in zip(r.get("timestamp", []), q.get("close", []), q.get("volume", [])):
            if c:
                out[(datetime.fromtimestamp(ts + off, timezone.utc)).date().isoformat()] = (c, v)
        if len(out) > len(best):
            best = out
        if len(best) > 1000:
            break
    return best


def fundamentals(sym):
    t = urllib.parse.quote(f"{sym}.NS")
    types = "quarterlyTotalRevenue,quarterlyOperatingRevenue,quarterlyNetIncome,quarterlyNetIncomeCommonStockholders"
    d = get(f"https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{t}?type={types}"
            f"&period1=1640995200&period2=1791331200")
    out = {}
    for res in (d.get("timeseries") or {}).get("result") or []:
        typ = res["meta"]["type"][0]
        for x in res.get(typ) or []:
            if x and x.get("reportedValue"):
                out.setdefault(x["asOfDate"], {})[typ] = x["reportedValue"]["raw"]
                out[x["asOfDate"]]["currency"] = x.get("currencyCode")
    return out


def one(sym):
    return sym, {"bse": closes(sym), "fin": fundamentals(sym)}


with ThreadPoolExecutor(8) as ex:
    data = dict(ex.map(one, syms))
json.dump(data, open(OUT, "w"))
print("symbols", len(data), "with BSE prices", sum(1 for v in data.values() if len(v["bse"]) > 100),
      "with fundamentals", sum(1 for v in data.values() if v["fin"]))
