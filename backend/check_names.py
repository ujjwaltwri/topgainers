import os
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

supabase = create_client(url, key)

res = supabase.table('stocks').select('ticker, name').eq('country', 'South Korea').limit(10).execute()
print(res.data)
