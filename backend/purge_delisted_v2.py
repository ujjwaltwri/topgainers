import os
import yfinance as yf
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
if not url or not key:
    from dotenv import load_dotenv
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

supabase = create_client(url, key)

print("Fetching all tickers from Supabase...")
all_tickers = []
start = 0
while True:
    res = supabase.table('stocks').select('ticker').range(start, start + 999).execute()
    data = res.data
    if not data:
        break
    all_tickers.extend([r['ticker'] for r in data])
    start += 1000

print(f"Checking {len(all_tickers)} tickers for recent trading activity...")

# Download in batches of 1000 to avoid yfinance getting overwhelmed
to_delete = []

for i in range(0, len(all_tickers), 1000):
    chunk = all_tickers[i:i+1000]
    print(f"Downloading batch {i} to {i+1000}...")
    data = yf.download(chunk, period='14d', group_by='ticker', threads=True)
    
    if len(chunk) == 1:
        if data.empty or data['Close'].isna().all():
            to_delete.append(chunk[0])
    else:
        for t in chunk:
            # Multi-level column if multiple tickers
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
        chunk_del = to_delete[i:i+500]
        supabase.table('stocks').delete().in_('ticker', chunk_del).execute()
        print(f"Deleted {i + len(chunk_del)} / {len(to_delete)}")
    print("Database purged of dead stocks.")
else:
    print("Database is clean.")
