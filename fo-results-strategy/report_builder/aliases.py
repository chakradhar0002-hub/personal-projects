"""Old NSE symbols of today's F&O stocks (NSE's symbolchange.csv), so price and option files from before a rename
are stored under today's symbol, e.g. ZOMATO -> ETERNAL until 9-Apr-2025, TATAMOTORS -> TMPV until 24-Oct-2025."""
import csv
from datetime import datetime
from pathlib import Path

URL = "https://nsearchives.nseindia.com/content/equities/symbolchange.csv"


# Renames missing from NSE's list (checked in the bhavcopies: RUCHI until mid-2022, PATANJALI from late 2022)
EXTRA = {"RUCHI": ("PATANJALI", "2099-12-31")}


def load(sp, universe, http=None):
    """{old symbol: (today's symbol, first day of the new symbol as 'YYYY-MM-DD')}, following chains of renames."""
    path = Path(sp) / "symbolchange.csv"
    if not path.exists():
        if http is None:
            from fo_results_strategy.realdata import Http
            http = Http(pause=0.1)
        path.write_bytes(http.get(URL))
    changes = {}
    for row in csv.reader(open(path, encoding="utf-8", errors="replace")):
        if len(row) < 4:
            continue
        old, new = row[-3].strip(), row[-2].strip()
        try:
            day = datetime.strptime(row[-1].strip(), "%d-%b-%Y").date().isoformat()
        except ValueError:
            continue
        if old and new and old != new:
            changes[old] = (new, day)
    out = {}
    for old, (new, day) in changes.items():
        final, seen = new, {old}
        while final in changes and final not in universe and final not in seen:      # LTI -> LTIM -> LTM
            seen.add(final)
            final = changes[final][0]
        if final in universe and old not in universe:
            out[old] = (final, day)
    out.update({k: v for k, v in EXTRA.items() if v[0] in universe})
    return out


def resolve(sym, day, alias):
    """Today's symbol for a row of `sym` on `day` (ISO date); unchanged if `sym` is current or the row is after the rename."""
    a = alias.get(sym)
    return a[0] if a and day < a[1] else sym
