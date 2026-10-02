import argparse
import concurrent.futures
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd

DATES=('2024-09-17','2024-09-19')
EXPIRY='2024-10-18'


def query(database,sql,ref='master'):
    url=f'https://www.dolthub.com/api/v1alpha1/post-no-preference/{database}/{urllib.parse.quote(ref,safe="")}?'+urllib.parse.urlencode({'q':sql})
    for attempt in range(3):
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'event-volatility-research/1.0'})
            raw=urllib.request.urlopen(request,timeout=45).read()
            obj=json.loads(raw)
            if obj.get('query_execution_status')!='Success':
                raise RuntimeError('DoltHub query failed: '+obj.get('query_execution_message','unknown'))
            if obj.get('next_page_url'):raise RuntimeError('Unexpected pagination: narrow the query')
            return obj['rows'],raw,url
        except Exception:
            if attempt==2:raise
            time.sleep(1+attempt)


def download(directory=Path('data/raw'),ref='master'):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    tasks=[]
    for day in DATES:
        tasks.append(('options',day,f"SELECT * FROM option_chain WHERE date='{day}' AND act_symbol='SPY' AND expiration='{EXPIRY}' LIMIT 1000"))
        tasks.append(('stocks',day,f"SELECT * FROM ohlcv WHERE date='{day}' AND act_symbol='SPY' LIMIT 2"))
    def fetch(task):
        db,day,sql=task;rows,raw,url=query(db,sql,ref)
        if not rows or len(rows)>=1000:raise RuntimeError(f'Missing/truncated data for {db} {day}; no synthetic fallback')
        path=directory/f'{db}-{day}.json';path.write_bytes(raw)
        return db,day,rows,dict(database=db,date=day,query=sql,url=url,rows=len(rows),sha256=hashlib.sha256(raw).hexdigest())
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        fetched=list(pool.map(fetch,tasks))
    stock={day:float(rows[0]['close']) for db,day,rows,_ in fetched if db=='stocks'}
    frames=[]
    for db,day,rows,_ in fetched:
        if db=='options':
            frame=pd.DataFrame(rows);frame['spot']=stock[day];frames.append(frame)
    combined=pd.concat(frames,ignore_index=True);combined.to_csv(directory/'options.csv',index=False)
    manifest=dict(provider='DoltHub post-no-preference/options and stocks; third-party daily snapshots',
                  retrieved_utc=datetime.now(timezone.utc).isoformat(),ref=ref,
                  event='FOMC September 18, 2024, 14:00 America/New_York',
                  event_source='https://www.federalreserve.gov/newsevents/pressreleases/monetary20240918a.htm',
                  symbol='SPY',dates=DATES,expiry=EXPIRY,
                  normalized_sha256=hashlib.sha256((directory/'options.csv').read_bytes()).hexdigest(),
                  sources=[m for _,_,_,m in fetched],
                  caveats=['No intraday quote timestamps in this source','No volume/open interest fields',
                           'Sparse selected strikes, not a complete exchange chain','master can change; raw response hashes identify this run'])
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(f'Downloaded {len(combined)} real option quotes across {len(frames)} dates')
    return combined


def snapshot_yahoo(symbol,expiry,output):
    """Collect a CURRENT chain only. Does not claim historical retrieval."""
    import yfinance as yf
    captured=datetime.now(timezone.utc)
    ticker=yf.Ticker(symbol)
    if expiry not in ticker.options:raise ValueError('Expiration not currently available on Yahoo')
    chain=ticker.option_chain(expiry)
    frame=pd.concat([chain.calls.assign(call_put='Call'),chain.puts.assign(call_put='Put')])
    frame['captured_utc']=captured.isoformat();frame['expiration']=expiry
    path=Path(output);path.mkdir(parents=True,exist_ok=True)
    filename=path/f'{symbol}-{expiry}-{captured.strftime("%Y%m%dT%H%M%S%fZ")}.csv'
    frame.to_csv(filename,index=False)
    print(f'Saved {filename}. Retrieval time is not the exchange quote time; lastTradeDate can be stale.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--ref',default='master')
    p.add_argument('--snapshot-symbol');p.add_argument('--expiry');p.add_argument('--output',default='data/snapshots')
    a=p.parse_args()
    if a.snapshot_symbol:
        if not a.expiry:p.error('--expiry is required with --snapshot-symbol')
        snapshot_yahoo(a.snapshot_symbol,a.expiry,a.output)
    else:download(ref=a.ref)
