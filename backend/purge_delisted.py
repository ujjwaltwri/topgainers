import os
import yfinance as yf
from supabase import create_client
import pandas as pd

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
if not url or not key:
    from dotenv import load_dotenv
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

supabase = create_client(url, key)

print("Fetching all tickers from Supabase...")
res = supabase.table('stocks').select('ticker').execute()
tickers = [r['ticker'] for r in res.data]

print(f"Checking {len(tickers)} tickers for recent trading activity...")

# Download last 14 days of data. Any stock with 0 rows or all NaN is considered dead.
data = yf.download(tickers, period='14d', group_by='ticker', threads=True, show_errors=False)

to_delete = []

if len(tickers) == 1:
    # yfinance returns different structure for 1 ticker
    if data.empty or data['Close'].isna().all():
        to_delete.append(tickers[0])
else:
    for t in tickers:
        if t not in data.columns.levels[0]:
            to_delete.append(t)
        else:
            df = data[t]
            if df.empty or df['Close'].isna().all():
                to_delete.append(t)

print(f"Found {len(to_delete)} delisted/suspended/ghost stocks!")

if to_delete:
    print("Deleting from Supabase (this cascades to gains automatically)...")
    for i in range(0, len(to_delete), 500):
        chunk = to_delete[i:i+500]
        supabase.table('stocks').delete().in_('ticker', chunk).execute()
        print(f"Deleted {i + len(chunk)} / {len(to_delete)}")
    print("Database purged of dead stocks.")
else:
    print("Database is clean.")
