import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

response = supabase.table('gains_with_stocks').select('ticker, name, sector, market_cap, pct_change').eq('period', '1D').limit(5).execute()
print(response.data)
