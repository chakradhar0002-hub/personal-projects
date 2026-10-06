"""Read results XBRL facts by the dates of their contexts, not by context names.

Some filings put half-year, nine-month or full-year figures in the context NSE's tool usually uses for the
quarter ("OneD"), so the quarter is found from the dates: OneD = the 3-month quarter, FourD = 1 April to the
quarter end (not set for June quarters, where it equals the quarter), OneI = balance sheet at the quarter end.
"""
import re
from datetime import date

CONTEXT = re.compile(r'<(?:xbrli:)?context id="([^"]+)"[^>]*>(.*?)</(?:xbrli:)?context>', re.S)
START = re.compile(r"<(?:xbrli:)?startDate>\s*([0-9-]+)\s*<")
END = re.compile(r"<(?:xbrli:)?endDate>\s*([0-9-]+)\s*<")
INSTANT = re.compile(r"<(?:xbrli:)?instant>\s*([0-9-]+)\s*<")


def quarter_contexts(text, qend):
    """Context id -> set of keys (OneD / FourD / OneI) for dimension-free contexts that match the quarter."""
    q_start = date(qend.year, qend.month - 2, 1)
    fy_start = date(qend.year if qend.month >= 4 else qend.year - 1, 4, 1)
    out = {}
    for cid, body in CONTEXT.findall(text):
        if "explicitMember" in body or "typedMember" in body:
            continue
        s, e, i = START.search(body), END.search(body), INSTANT.search(body)
        keys = set()
        if i and i.group(1) == qend.isoformat():
            keys.add("OneI")
        if s and e and e.group(1) == qend.isoformat():
            if s.group(1) == q_start.isoformat():
                keys.add("OneD")
            if s.group(1) == fy_start.isoformat() and fy_start != q_start:
                keys.add("FourD")
        if keys:
            out[cid] = keys
    return out


def fact_patterns(tags):
    return {t: re.compile(rf'<(?:in-bse-fin|in-capmkt):{t} [^>]*contextRef="([^"]+)"[^>]*>([^<]+)<') for t in tags}


def parse(text, qend, patterns):
    """{tag: {OneD|FourD|OneI: value}} for the quarter ending qend."""
    ctx = quarter_contexts(text, qend)
    out = read(text, patterns, ctx)
    if not has_quarter(out) and "OneD" in dict(CONTEXT.findall(text)):
        # Some filings date the quarter context wrongly (e.g. 6 months) while the figures are the quarter's. Accept the
        # tool's usual quarter context only if it ends on the quarter end and its figures are well below year-to-date.
        body = dict(CONTEXT.findall(text))["OneD"]
        e = END.search(body)
        if e and e.group(1) == qend.isoformat():
            alt = dict(ctx)
            alt["OneD"] = {"OneD"}
            trial = read(text, patterns, alt)
            q = first(trial, "OneD")
            ytd = first(out, "FourD")
            if q is not None and (qend.month == 6 or (ytd and 0 < q / ytd < 0.7)):
                out = trial
    return out


def read(text, patterns, ctx):
    out = {}
    for t, rx in patterns.items():
        for cid, v in rx.findall(text):
            for key in ctx.get(cid, ()):
                try:
                    out.setdefault(t, {}).setdefault(key, float(v))
                except ValueError:
                    pass
    return out


def first(data, key):
    for t in ("RevenueFromOperations", "InterestEarned", "ProfitLossForPeriod", "ProfitLossForThePeriod"):
        if key in data.get(t, {}):
            return data[t][key]
    return None


def has_quarter(data):
    return any("OneD" in data.get(t, {}) for t in ("RevenueFromOperations", "InterestEarned", "ProfitLossForPeriod",
                                                   "ProfitLossForThePeriod"))
