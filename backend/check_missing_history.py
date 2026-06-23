import os
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
if not url or not key:
    from dotenv import load_dotenv
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

supabase = create_client(url, key)

print("Fetching total stocks...")
res = supabase.table('stocks').select('ticker', count='exact').execute()
total = res.count

print("Fetching stocks with history...")
res = supabase.table('stocks').select('ticker', count='exact').neq('price_history', '[]').execute()
with_history = res.count

print(f"Total stocks: {total}")
print(f"Stocks with history: {with_history}")
print(f"Stocks missing history: {total - with_history}")

