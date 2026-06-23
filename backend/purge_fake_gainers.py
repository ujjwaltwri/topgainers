import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

# Find all tickers where rsi_14 is null AND pct_change > 50 (illiquid/suspended jump)
response = supabase.table("gains").select("ticker, pct_change").gt("pct_change", 50).is_("rsi_14", "null").execute()
data1 = response.data

# Find all tickers where pct_change > 300 (massive reverse split or fake jump)
response2 = supabase.table("gains").select("ticker, pct_change").gt("pct_change", 300).execute()
data2 = response2.data

tickers_to_delete = set()
for d in data1:
    tickers_to_delete.add(d['ticker'])
for d in data2:
    tickers_to_delete.add(d['ticker'])

print(f"Found {len(tickers_to_delete)} completely broken/fake gainers (missing RSI or >300% gain).")

if tickers_to_delete:
    print(list(tickers_to_delete)[:20])
    
    # Delete them in batches
    tickers_list = list(tickers_to_delete)
    for i in range(0, len(tickers_list), 50):
        batch = tickers_list[i:i+50]
        supabase.table("stocks").delete().in_("ticker", batch).execute()
        print(f"Deleted batch {i//50 + 1}")

print("Purge complete!")
