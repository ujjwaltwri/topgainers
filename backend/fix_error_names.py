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

print("Fetching corrupted names...")
res = supabase.table('stocks').select('ticker').like('name', '%Error 500%').execute()
bad_stocks = res.data

print(f"Found {len(bad_stocks)} corrupted names.")

updates = []
for row in bad_stocks:
    ticker = row['ticker']
    try:
        info = yf.Ticker(ticker).info
        raw_name = info.get('longName') or info.get('shortName') or ticker
        print(f"Restoring {ticker} -> {raw_name}")
        updates.append({'ticker': ticker, 'name': raw_name})
    except Exception as e:
        print(f"Failed to fetch {ticker}: {e}")

if updates:
    print("Pushing fixes to Supabase...")
    for i in range(0, len(updates), 500):
        chunk = updates[i:i+500]
        supabase.table('stocks').upsert(chunk).execute()
    print("Success!")
else:
    print("No updates needed.")
