import os
import requests
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# Query gains where pct_change > 300 and ma_50 is null
url = f"{SUPABASE_URL}/rest/v1/gains?pct_change=gt.300&ma_50=is.null&select=ticker,period,pct_change"
response = requests.get(url, headers=headers)
data = response.json()

if isinstance(data, list):
    print(f"Found {len(data)} suspicious gain records with missing MA50.")
    tickers = list(set([r['ticker'] for r in data]))
    print(f"Unique tickers: {len(tickers)}")
    print("Sample:", tickers[:20])
else:
    print("Error:", data)

