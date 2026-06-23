import os
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

supabase = create_client(url, key)

print("Fetching all stocks...")
all_stocks = []
page = 0
while True:
    res = supabase.table('stocks').select('ticker, name').range(page*1000, (page+1)*1000-1).execute()
    if not res.data:
        break
    all_stocks.extend(res.data)
    page += 1

bad_stocks = [r for r in all_stocks if r['name'] and ',' in r['name'] and ' ' not in r['name']]
print(f"Found {len(bad_stocks)} bad names out of {len(all_stocks)} total stocks.")

updates = [{'ticker': r['ticker'], 'name': r['ticker']} for r in bad_stocks]

if updates:
    print(f"Updating {len(updates)} names to fallback to ticker...")
    # Chunk updates
    chunk_size = 500
    for i in range(0, len(updates), chunk_size):
        chunk = updates[i:i+chunk_size]
        supabase.table('stocks').upsert(chunk).execute()
    print("Done!")
