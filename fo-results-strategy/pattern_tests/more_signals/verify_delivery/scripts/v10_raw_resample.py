"""v10 - fresh raw re-download of NSE sec_bhavdata_full for a NEW random sample of candidate decision days
(days not used by the earlier v01 sample), parsed in memory; only compact universe rows are kept.
Compares raw DELIV_PER / DELIV_QTY / TTL_TRD_QNTY / CLOSE with the study's stored delivery_eq.csv.
usage: python3 -P v10_raw_resample.py <scratchpad> <out_dir>
"""
import sys, io, time, random
import numpy as np, pandas as pd, requests

SP, OUT = sys.argv[1], sys.argv[2]
DL = f'{OUT}/downloads_v10'
ST = f'{SP}/more_signals/delivery'
log = open(f'{OUT}/v10_raw_resample.log', 'a')
def P(*a):
    s = ' '.join(str(x) for x in a); print(s); log.write(s + '\n'); log.flush()

ses = pd.read_csv(f'{SP}/sector_lab/data/sessions.csv')
day_of = dict(zip(ses.i, ses.day))
fr = pd.read_csv(f'{ST}/feat_results.csv', usecols=['symbol', 'qn', 'i_cut', 'i_react'])
ta = pd.read_csv(f'{ST}/trades_A.csv', usecols=['test', 'symbol', 'qn'])
tb = pd.read_csv(f'{ST}/trades_B.csv', usecols=['test', 'symbol', 'qn'])
pts = []
for t in ['A10', 'A06', 'RA1']:
    m = ta[ta.test == t].merge(fr, on=['symbol', 'qn'])
    for r in m.itertuples():
        pts.append((t, r.symbol, day_of[r.i_cut - 1]))
for t in ['W_DQK_HI', 'WR_DQK_HI']:
    m = tb[tb.test == t].merge(fr, on=['symbol', 'qn'])
    for r in m.itertuples():
        pts.append((t, r.symbol, day_of[r.i_react]))
pts = pd.DataFrame(pts, columns=['cand', 'symbol', 'day']).drop_duplicates()
prev = set(pd.read_csv(f'{OUT}/downloads/raw_sample_log.csv').day)
cand_days = sorted(set(pts.day) - prev)
random.seed(424242)
days = sorted(random.sample(cand_days, 16))
P('new sample days (none in the earlier v01 sample):', days)

eq = pd.read_csv(f'{ST}/downloads/delivery_eq.csv')
universe = set(eq.symbol)
H = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
     'Accept': 'text/csv,*/*', 'Referer': 'https://www.nseindia.com/'}
sess = requests.Session(); sess.headers.update(H)
rows, status = [], []
CACHED = len(sys.argv) > 3 and sys.argv[3] == 'cached'
if CACHED:
    days = []   # reuse the compact rows saved by the first run (no re-download)
for d in days:
    dd = pd.Timestamp(d).strftime('%d%m%Y')
    url = f'https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{dd}.csv'
    txt = None
    for att in range(4):
        try:
            r = sess.get(url, timeout=30)
            if r.status_code == 200 and r.content[:6].upper().startswith(b'SYMBOL'):
                txt = r.content.decode('utf-8', 'replace'); break
            status.append((d, att, r.status_code, r.content[:20]))
        except Exception as ex:
            status.append((d, att, 'exc', str(ex)[:60]))
        time.sleep(2 * (att + 1))
    if txt is None:
        P(d, 'FAILED'); continue
    df = pd.read_csv(io.StringIO(txt))
    df.columns = [c.strip() for c in df.columns]
    for c in df.columns:
        if not pd.api.types.is_numeric_dtype(df[c]):
            df[c] = df[c].astype(str).str.strip()
    d1 = pd.to_datetime(df.DATE1.iloc[0]).strftime('%Y-%m-%d')
    keep = df[df.SYMBOL.isin(universe)].copy()
    keep['req_day'] = d; keep['date1'] = d1
    rows.append(keep[['req_day', 'date1', 'SYMBOL', 'SERIES', 'PREV_CLOSE', 'CLOSE_PRICE', 'TTL_TRD_QNTY',
                      'DELIV_QTY', 'DELIV_PER']])
    P(d, 'ok rows', len(df), 'universe rows', len(keep), 'DATE1', d1)
    time.sleep(1.0)
if CACHED:
    raw = pd.read_csv(f'{DL}/raw_rows_v10.csv', dtype=str)
    for c in raw.columns:
        raw[c] = raw[c].str.strip()
    days = sorted(set(raw.req_day))
else:
    raw = pd.concat(rows)
    raw.to_csv(f'{DL}/raw_rows_v10.csv', index=False)
P('fetch retries / non-200:', status)
P('days whose DATE1 differs from the requested day:', int((raw.req_day != raw.date1).sum()))

r = raw[raw.SERIES == 'EQ'].copy()
for c in ['TTL_TRD_QNTY', 'DELIV_QTY', 'DELIV_PER', 'CLOSE_PRICE', 'PREV_CLOSE']:
    r[c] = pd.to_numeric(r[c], errors='coerce')
m = r.merge(eq[eq.day.isin(days)], left_on=['req_day', 'SYMBOL'], right_on=['day', 'symbol'], how='outer',
            indicator=True)
P('raw EQ rows vs stored rows on these days:', m._merge.value_counts().to_dict())
b = m[m._merge == 'both']
for a, s in [('TTL_TRD_QNTY', 'ttl_trd_qnty'), ('DELIV_QTY', 'deliv_qty'), ('DELIV_PER', 'deliv_per'),
             ('CLOSE_PRICE', 'close'), ('PREV_CLOSE', 'prev_close')]:
    eqv = np.isclose(b[a], b[s], rtol=1e-9, atol=1e-6) | (b[a].isna() & b[s].isna())
    P(f'   {s}: equal on {int(eqv.sum())} / {len(b)}')
    if (~eqv).any():
        P(b.loc[~eqv, ['req_day', 'SYMBOL', a, s]].head(10).to_string())

# candidate points on the sample days
cp = pts[pts.day.isin(days)].copy()
# map current symbol -> ticker actually in the file that day (dated changes)
_l = [ln.rstrip('\n').rsplit(',', 3) for ln in open(f'{SP}/symbolchange.csv', encoding='utf-8', errors='replace')]
sc = pd.DataFrame([x for x in _l if len(x) == 4], columns=['name', 'old', 'new', 'date'])
sc['old'] = sc.old.str.strip(); sc['new'] = sc.new.str.strip()
sc['date'] = pd.to_datetime(sc.date.str.strip(), format='%d-%b-%Y', errors='coerce')
def ticker_on(cur, d):
    t = cur; d = pd.Timestamp(d)
    for _ in range(6):
        ch = sc[(sc.new == t) & (sc.date > d)]
        if len(ch) == 0: break
        t = ch.sort_values('date').old.iloc[0]
    return t
cp['ticker'] = [ticker_on(s, d) for s, d in zip(cp.symbol, cp.day)]
cm = cp.merge(r, left_on=['day', 'ticker'], right_on=['req_day', 'SYMBOL'], how='left')
cm = cm.merge(eq, left_on=['day', 'ticker'], right_on=['day', 'symbol'], how='left', suffixes=('', '_st'))
ok = (np.isclose(cm.DELIV_PER, cm.deliv_per) & np.isclose(cm.DELIV_QTY, cm.deliv_qty)
      & np.isclose(cm.TTL_TRD_QNTY, cm.ttl_trd_qnty))
P(f'candidate (symbol, decision day) points on the new days: {len(cm)}; by candidate {cm.cand.value_counts().to_dict()}')
P(f'   found in raw EQ: {int(cm.DELIV_PER.notna().sum())}; raw == stored on deliv %, deliv qty, traded qty: {int(ok.sum())}')
P(f'   tickers differing from the current symbol: {cm[cm.ticker != cm.symbol][["symbol", "ticker", "day"]].values.tolist()}')
P(cm[['cand', 'symbol', 'day', 'DELIV_PER', 'deliv_per', 'DELIV_QTY', 'deliv_qty']].head(60).to_string())
# compare with the study's delivery_panel (mapped, with volume_factor) on these points
dp = pd.read_csv(f'{ST}/delivery_panel.csv.gz')
P('delivery_panel columns:', list(dp.columns))
